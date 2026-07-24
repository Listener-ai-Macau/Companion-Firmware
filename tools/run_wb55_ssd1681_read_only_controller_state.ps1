param(
    [switch]$CheckOnly,
    [switch]$Execute,
    [switch]$WorkflowLockHeld,
    [ValidateRange(10, 60)]
    [int]$CaptureSeconds = 20,
    [string]$Port,
    [string]$OutRoot,
    [string]$ProgrammerRoot = "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if ($CheckOnly -eq $Execute) {
    throw "Choose exactly one of -CheckOnly or -Execute."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
. (Join-Path $PSScriptRoot "companion_wb55_lock.ps1")
$staticVerifier = Join-Path $PSScriptRoot "verify_wb55_ssd1681_read_only_controller_state_diagnostic.py"
$logVerifier = Join-Path $PSScriptRoot "verify_wb55_ssd1681_read_only_controller_state_log.py"
$captureRunner = Join-Path $PSScriptRoot "capture_nucleo_serial.ps1"
$flashRunner = Join-Path $PSScriptRoot "flash_nucleo_bringup.ps1"
$staticArtifact = Join-Path $repoRoot "docs\validation\companion-ssd1681-read-only-controller-state-static-20260721.json"
$candidateImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_read_only_controller_state\Companion_Nucleo_WB55RG_Ssd1681ReadOnlyControllerState.hex"
$normalImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build\Companion_Nucleo_WB55RG_Bringup.hex"
$requiredNormalSha256 = "E1997F29DCB8735899B4BC0B9012CF75025F3CA8D21250485BCC21E4C4691B46"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runRoot = if ($OutRoot) { [System.IO.Path]::GetFullPath($OutRoot) } else {
    Join-Path $repoRoot ".cache\validation\wb55-ssd1681-read-only-controller-state-$stamp"
}
$captureRoot = Join-Path $runRoot "capture"
$readySignal = Join-Path $runRoot "serial-ready.json"
$rawLog = Join-Path $captureRoot "nucleo-serial-raw.log"
$decodedArtifact = Join-Path $runRoot "controller-state.json"
$reportPath = Join-Path $runRoot "stage-run.json"
New-Item -ItemType Directory -Force -Path $runRoot | Out-Null

function Hash([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

function Write-Report([System.Collections.IDictionary]$Report) {
    $Report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $reportPath -Encoding UTF8
}

$report = [ordered]@{
    schema_id = "companion.wb55.ssd1681.read_only_controller_state_stage_run.v1"
    status = "PREFLIGHT"
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    mode = if ($CheckOnly) { "check_only" } else { "execute" }
    hardware_contact = 0
    automatic_retries = 0
    images = [ordered]@{
        candidate = [ordered]@{ path = $candidateImage; sha256 = Hash $candidateImage }
        normal_restore = [ordered]@{ path = $normalImage; sha256 = Hash $normalImage; required_sha256 = $requiredNormalSha256 }
    }
    safety = [ordered]@{
        serial_open_before_candidate_flash = $true
        post_flash_reset = $false
        expected_boots = 1
        expected_read_groups = 3
        display_writes = 0
        refresh_commands = 0
        hard_resets = 0
        restore_in_finally = $true
    }
    output = [ordered]@{ raw_log = $rawLog; decoded = $decodedArtifact; report = $reportPath }
    normal_firmware_restored = $false
}

try {
    foreach ($path in @($candidateImage, $normalImage)) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Required image is missing: $path"
        }
    }
    if ((Hash $normalImage) -ne $requiredNormalSha256) {
        throw "Normal restore image hash mismatch; refusing all hardware contact."
    }
    & python $staticVerifier
    if ($LASTEXITCODE -ne 0) { throw "Static gate failed; refusing all hardware contact." }
    $static = Get-Content -LiteralPath $staticArtifact -Raw | ConvertFrom-Json
    if ($static.status -ne "PASS_STATIC_READ_ONLY_CONTROLLER_STATE_DEFAULT_OFF") {
        throw "Static artifact is not PASS."
    }
    if ($CheckOnly) {
        $report.status = "READY_NO_HARDWARE_CONTACT"
        $report.completed_at = (Get-Date).ToUniversalTime().ToString("o")
        Write-Report $report
        Write-Output "CHECK: all read-only gates passed; no hardware contact."
        exit 0
    }

    $lock = Enter-CompanionWb55Lock -Purpose "one SSD1681 read-only controller-state capture"
    $candidateAttempted = $false
    $captureProcess = $null
    try {
        if ($WorkflowLockHeld -and $lock.mode -ne "inherited") {
            throw "-WorkflowLockHeld was requested without an inherited lock grant."
        }
        New-Item -ItemType Directory -Force -Path $captureRoot | Out-Null
        $captureArgs = @("-NoProfile", "-File", $captureRunner, "-Execute", "-WorkflowLockHeld",
                         "-Seconds", "$CaptureSeconds", "-OutDir", $captureRoot,
                         "-ReadySignalPath", $readySignal, "-ProgrammerRoot", $ProgrammerRoot)
        if (-not [string]::IsNullOrWhiteSpace($Port)) { $captureArgs += @("-Port", $Port) }
        $captureStdout = Join-Path $runRoot "capture.stdout.log"
        $captureStderr = Join-Path $runRoot "capture.stderr.log"
        $captureProcess = Start-Process -FilePath "pwsh" -ArgumentList $captureArgs `
            -RedirectStandardOutput $captureStdout -RedirectStandardError $captureStderr `
            -WindowStyle Hidden -PassThru
        $readyDeadline = [DateTime]::UtcNow.AddSeconds(20)
        while (-not (Test-Path -LiteralPath $readySignal -PathType Leaf)) {
            if ($captureProcess.HasExited) { throw "Serial capture exited before ready." }
            if ([DateTime]::UtcNow -ge $readyDeadline) { throw "Serial capture did not become ready before timeout." }
            Start-Sleep -Milliseconds 100
        }

        $report.hardware_contact = 1
        $candidateAttempted = $true
        & pwsh -NoProfile -File $flashRunner -ImagePath $candidateImage -ProgrammerRoot $ProgrammerRoot
        if ($LASTEXITCODE -ne 0) { throw "Candidate flash failed." }
        if (-not $captureProcess.WaitForExit(($CaptureSeconds + 15) * 1000)) {
            Stop-Process -Id $captureProcess.Id -Force -ErrorAction SilentlyContinue
            throw "Serial capture timed out."
        }
        $captureProcess.WaitForExit()
        if ($captureProcess.ExitCode -ne 0) { throw "Serial capture failed." }
        & python $logVerifier --log $rawLog --out $decodedArtifact
        if ($LASTEXITCODE -ne 0) { throw "Read-only controller-state parser gate failed." }
        $report.status = "PASS_MACHINE_READ_ONLY_CONTROLLER_STATE_PENDING_RESTORE"
    } finally {
        if ($captureProcess -and -not $captureProcess.HasExited) {
            Stop-Process -Id $captureProcess.Id -Force -ErrorAction SilentlyContinue
            $captureProcess.WaitForExit()
        }
        $restored = $false
        if ($candidateAttempted) {
            & pwsh -NoProfile -File $flashRunner -ImagePath $normalImage -ProgrammerRoot $ProgrammerRoot
            $restored = $LASTEXITCODE -eq 0 -and (Hash $normalImage) -eq $requiredNormalSha256
        }
        $report.normal_firmware_restored = $restored
        if ($candidateAttempted -and -not $restored) {
            $report.status = "NO_GO_NORMAL_RESTORE_FAILED"
        } elseif ($report.status -eq "PASS_MACHINE_READ_ONLY_CONTROLLER_STATE_PENDING_RESTORE") {
            $report.status = "PASS_MACHINE_READ_ONLY_CONTROLLER_STATE_NORMAL_RESTORED"
        }
        Exit-CompanionWb55Lock
    }
    if ($candidateAttempted -and -not $report.normal_firmware_restored) {
        throw "Normal firmware restore failed."
    }
} catch {
    if ($report.status -ne "NO_GO_NORMAL_RESTORE_FAILED") {
        $report.status = "NO_GO"
    }
    $report.error = $_.Exception.Message
    throw
} finally {
    $report.completed_at = (Get-Date).ToUniversalTime().ToString("o")
    Write-Report $report
}
