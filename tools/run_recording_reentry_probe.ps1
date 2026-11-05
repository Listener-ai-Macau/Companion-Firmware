param(
    [string] $OutDir = ".cache/validation/comp775-repeat-blink-r6-20260819/machine-reentry-probe",
    [string] $Port = "COM13",
    [int] $CaptureSeconds = 52
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
. (Join-Path $PSScriptRoot "companion_wb55_lock.ps1")

$output = New-Item -ItemType Directory -Force -Path (Join-Path $repoRoot $OutDir)
$ready = Join-Path $output.FullName "serial-ready.json"
$captureStdout = Join-Path $output.FullName "capture.stdout.log"
$captureStderr = Join-Path $output.FullName "capture.stderr.log"
$probeLog = Join-Path $output.FullName "ble-reentry.log"
Remove-Item -LiteralPath $ready -Force -ErrorAction SilentlyContinue

$lock = $null
$capture = $null
try {
    $lock = Enter-CompanionWb55Lock -Purpose "recording finalize reentry probe"
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

    & python (Join-Path $PSScriptRoot "companion_ble_recording_reentry_probe.py") `
        2>&1 | Tee-Object -FilePath $probeLog | Out-Host
    $probeExit = $LASTEXITCODE
    $capture.WaitForExit()
    if ($capture.ExitCode -ne 0) {
        throw "Serial capture failed exit=$($capture.ExitCode); see $captureStderr"
    }
    if ($probeExit -ne 0) {
        throw "BLE reentry probe failed exit=$probeExit; see $probeLog"
    }
    Write-Output "PASS: finalize/reentry pressure completed without link loss."
} finally {
    if ($capture -and -not $capture.HasExited) {
        Stop-Process -Id $capture.Id -Force -ErrorAction SilentlyContinue
    }
    if ($lock) {
        Exit-CompanionWb55Lock
    }
}
