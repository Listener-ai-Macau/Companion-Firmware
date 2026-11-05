param(
    [string] $OutDir = ".cache/validation/comp-req-775-browser-device-single-source-final/131-commit-driven-recording-overlay/generation-state-ble-roundtrip",
    [string] $Port = "COM13",
    [int] $CaptureSeconds = 32,
    [int] $RecordingSeconds = 8,
    [int] $MaxRecordingSeconds = 20,
    [ValidateRange(0, 255)]
    # GATT control profile 2 selects the product real-mic codec=3 path.
    [int] $ProfileId = 2,
    [int] $WarmupSeconds = 0,
    [switch] $ResetAfterOpen
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
. (Join-Path $PSScriptRoot "companion_wb55_lock.ps1")

$output = New-Item -ItemType Directory -Force -Path (Join-Path $repoRoot $OutDir)
$ready = Join-Path $output.FullName "serial-ready.json"
$captureStdout = Join-Path $output.FullName "capture.stdout.log"
$captureStderr = Join-Path $output.FullName "capture.stderr.log"
$bleLog = Join-Path $output.FullName "ble-trigger.log"
Remove-Item -LiteralPath $ready -Force -ErrorAction SilentlyContinue

$lock = $null
$capture = $null
try {
    $lock = Enter-CompanionWb55Lock -Purpose "COMP-REQ-775 recording overlay BLE roundtrip"
    $captureArgs = @(
        "-NoProfile",
        "-File", (Join-Path $PSScriptRoot "capture_nucleo_serial.ps1"),
        "-Execute",
        "-WorkflowLockHeld",
        "-Port", $Port,
        "-Seconds", [string]$CaptureSeconds,
        "-OutDir", $output.FullName,
        "-ReadySignalPath", $ready
    )
    if ($ResetAfterOpen) {
        $captureArgs += "-ResetAfterOpen"
    }
    $capture = Start-Process pwsh `
        -ArgumentList $captureArgs `
        -RedirectStandardOutput $captureStdout `
        -RedirectStandardError $captureStderr `
        -WindowStyle Hidden `
        -PassThru

    $deadline = [DateTime]::UtcNow.AddSeconds(15)
    while (-not (Test-Path -LiteralPath $ready -PathType Leaf)) {
        if ([DateTime]::UtcNow -ge $deadline) {
            throw "Serial capture did not become ready."
        }
        Start-Sleep -Milliseconds 100
    }
    if ($WarmupSeconds -gt 0) {
        Write-Output "WAIT: reset/wake settle ${WarmupSeconds}s before BLE START"
        Start-Sleep -Seconds $WarmupSeconds
    }

    & python (Join-Path $PSScriptRoot "companion_ble_auto_record.py") `
        $MaxRecordingSeconds $RecordingSeconds $ProfileId 2>&1 | Tee-Object -FilePath $bleLog | Out-Host
    $bleExit = $LASTEXITCODE
    $capture.WaitForExit()
    if ($capture.ExitCode -ne 0) {
        throw "Serial capture failed exit=$($capture.ExitCode); see $captureStderr"
    }
    if ($bleExit -ne 0 -and $bleExit -ne 3) {
        throw "BLE recording trigger failed exit=$bleExit; see $bleLog"
    }
    Write-Output "PASS: recording overlay roundtrip captured under WB55 lock run=$($lock.run_id) ble_exit=$bleExit"
} finally {
    if ($capture -and -not $capture.HasExited) {
        Stop-Process -Id $capture.Id -Force -ErrorAction SilentlyContinue
    }
    if ($lock) {
        Exit-CompanionWb55Lock
    }
}
