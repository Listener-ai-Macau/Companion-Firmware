param(
    [switch] $CheckOnly,
    [switch] $Execute,
    [switch] $SelfTestRecovery,
    [switch] $WorkflowLockHeld,
    [ValidateSet("White", "Black", "RestoreNormal")]
    [string] $Stage,
    [ValidateRange(10, 120)]
    [int] $CaptureSeconds = 15,
    [string] $Port,
    [string] $OutRoot,
    [string] $NormalImagePath,
    [string] $WhiteImagePath,
    [string] $BlackImagePath,
    [string] $ProgrammerRoot = "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$flashRunner = Join-Path $PSScriptRoot "flash_nucleo_bringup.ps1"
$serialRunner = Join-Path $PSScriptRoot "capture_nucleo_serial.ps1"
$logVerifier = Join-Path $PSScriptRoot "verify_wb55_official_full_diagnostic_log.py"
$normalImageDefault = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build\Companion_Nucleo_WB55RG_Bringup.hex"
$whiteImageDefault = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_official_full_diagnostic_white\Companion_Nucleo_WB55RG_OfficialFullDiagnostic_white.hex"
$blackImageDefault = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_official_full_diagnostic_black\Companion_Nucleo_WB55RG_OfficialFullDiagnostic_black.hex"
$defaultOutRoot = Join-Path $repoRoot ".cache\validation\wb55-fts02-recovery-current"
$runRoot = if ([string]::IsNullOrWhiteSpace($OutRoot)) { $defaultOutRoot } else { $OutRoot }
$stageKey = if ([string]::IsNullOrWhiteSpace($Stage)) { "selftest" } else { $Stage.ToLowerInvariant() }
$stageRoot = Join-Path $runRoot $stageKey
$runReport = Join-Path $stageRoot "stage-run.json"

function Resolve-ImagePath {
    param(
        [string] $Override,
        [string] $Default
    )

    if ([string]::IsNullOrWhiteSpace($Override)) {
        return $Default
    }
    if ([System.IO.Path]::IsPathRooted($Override)) {
        return [System.IO.Path]::GetFullPath($Override)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $repoRoot $Override))
}

$normalImage = Resolve-ImagePath -Override $NormalImagePath -Default $normalImageDefault
$whiteImage = Resolve-ImagePath -Override $WhiteImagePath -Default $whiteImageDefault
$blackImage = Resolve-ImagePath -Override $BlackImagePath -Default $blackImageDefault

function RelPath {
    param([string] $Path)

    return [System.IO.Path]::GetRelativePath($repoRoot, [System.IO.Path]::GetFullPath($Path)).Replace("\", "/")
}

function Build-Step {
    param(
        [string] $Id,
        [string] $Command,
        [string[]] $Arguments,
        [string] $Purpose
    )

    return [ordered]@{
        id = $Id
        command = $Command
        arguments = @($Arguments)
        purpose = $Purpose
    }
}

function Write-RunReport {
    param([object] $Report)

    New-Item -ItemType Directory -Force -Path $stageRoot | Out-Null
    $Report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $runReport -Encoding UTF8
    Write-Output "FTS02 recovery stage report: $(RelPath $runReport)"
}

$selectedModes = @($CheckOnly.IsPresent, $Execute.IsPresent, $SelfTestRecovery.IsPresent) |
    Where-Object { $_ }
if (@($selectedModes).Count -ne 1) {
    throw "Use exactly one of -CheckOnly, -Execute, or -SelfTestRecovery."
}
if (-not $SelfTestRecovery -and [string]::IsNullOrWhiteSpace($Stage)) {
    throw "-Stage White, Black, or RestoreNormal is required."
}
if ($Execute -and -not $WorkflowLockHeld) {
    throw "Refusing WB55 FTS02 recovery execution without workflow lock acknowledgement."
}

$image = switch ($Stage) {
    "White" { $whiteImage }
    "Black" { $blackImage }
    "RestoreNormal" { $normalImage }
    default { $whiteImage }
}

if (-not $SelfTestRecovery) {
    $required = @($flashRunner, $normalImage, $image)
    if ($Stage -ne "RestoreNormal") {
        $required += @($serialRunner, $logVerifier)
    }
    foreach ($path in $required | Select-Object -Unique) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Required FTS02 recovery artifact is missing: $path"
        }
    }
}

$portArgs = @()
if (-not [string]::IsNullOrWhiteSpace($Port)) {
    $portArgs = @("-Port", $Port)
}
$steps = @()
$normalRestoreStep = Build-Step -Id "flash_normal_restore" -Command "pwsh" -Arguments @(
    "-NoProfile", "-File", $flashRunner,
    "-ImagePath", $normalImage,
    "-ProgrammerRoot", $ProgrammerRoot
) -Purpose "Restore the normal quiet production firmware."

if ($Stage -eq "RestoreNormal") {
    $steps += $normalRestoreStep
} elseif (-not $SelfTestRecovery) {
    $pattern = $Stage.ToLowerInvariant()
    $captureDir = Join-Path $stageRoot "capture"
    $rawLog = Join-Path $captureDir "nucleo-serial-raw.log"
    $parsedLog = Join-Path $stageRoot "official-full-result.json"
    $steps += Build-Step -Id "flash_$pattern" -Command "pwsh" -Arguments @(
        "-NoProfile", "-File", $flashRunner,
        "-ImagePath", $image,
        "-ProgrammerRoot", $ProgrammerRoot
    ) -Purpose "Flash the official one-plane $pattern diagnostic."
    $captureArguments = @(
        "-NoProfile", "-File", $serialRunner,
        "-Execute", "-WorkflowLockHeld",
        "-Seconds", "$CaptureSeconds",
        "-ResetAfterOpen",
        "-OutDir", $captureDir
    ) + $portArgs
    $steps += Build-Step -Id "capture_$pattern" -Command "pwsh" -Arguments $captureArguments -Purpose "Capture one reset-bounded $pattern diagnostic trace."
    $steps += Build-Step -Id "parse_$pattern" -Command "python" -Arguments @(
        $logVerifier,
        "--pattern", $pattern,
        "--log", $rawLog,
        "--out", $parsedLog
    ) -Purpose "Require the selected pattern marker, official 0x24 path, BUSY assertion, and one completed plane."
}

if ($SelfTestRecovery) {
    $Stage = "White"
    $stageKey = "selftest"
    $steps = @(
        Build-Step -Id "flash_white" -Command "pwsh" -Arguments @(
            "-NoProfile", "-Command", "Write-Output 'SELFTEST: flash_white'; exit 0"
        ) -Purpose "Stub-only diagnostic flash."
        Build-Step -Id "capture_white" -Command "pwsh" -Arguments @(
            "-NoProfile", "-Command", "Write-Output 'SELFTEST: capture_white failure'; exit 7"
        ) -Purpose "Stub-only capture failure."
    )
    $normalRestoreStep = Build-Step -Id "flash_normal_restore" -Command "pwsh" -Arguments @(
        "-NoProfile", "-Command", "Write-Output 'SELFTEST: flash_normal_restore'; exit 0"
    ) -Purpose "Stub-only normal firmware recovery."
}

$report = [ordered]@{
    schema_id = "companion.wb55.fts02_recovery_stage_run.v1"
    status = if ($CheckOnly) { "DRY-RUN" } elseif ($SelfTestRecovery) { "SELFTEST_RUNNING" } else { "RUNNING" }
    claim_scope = if ($CheckOnly) { "preflight_only_no_hardware_claim" } elseif ($SelfTestRecovery) { "stubbed_failure_recovery_no_hardware_claim" } else { "machine_digital_trace_pending_operator_visual_gate" }
    generated_at = (Get-Date).ToString("o")
    target = "NUCLEO-WB55RG + replacement/cross-swapped ESP32-FTS02 + GDEY0154D67-T03"
    stage = $Stage
    capture_seconds = $CaptureSeconds
    image = RelPath $image
    output = [ordered]@{
        root = RelPath $stageRoot
        run_report = RelPath $runReport
    }
    steps = @($steps)
    safety = [ordered]@{
        execute_requires_companion_wb55_lock = $true
        diagnostic_failure_restores_normal = $true
        successful_diagnostic_waits_for_focused_operator_visual_result = $true
        machine_pass_is_not_visual_or_voltage_acceptance = $true
    }
    notes = @(
        "Run a diagnostic stage only after FTS02 replacement/cross-swap and explicit owner acceptance start.",
        "White and Black stages leave the selected diagnostic installed only after machine PASS so the operator can inspect that one frame.",
        "Run RestoreNormal after each stopped or completed visual session before resuming product behavior.",
        "A machine PASS proves only the digital command/BUSY trace; PREVGH/PREVGL and visible-frame acceptance remain physical gates."
    )
}

if ($CheckOnly) {
    $report.completed_at = (Get-Date).ToString("o")
    $report.results = @()
    Write-Output "CHECK: WB55 FTS02 recovery stage=$Stage capture_seconds=$CaptureSeconds"
    foreach ($step in $steps) {
        Write-Output "CHECK: $($step.id): $($step.command) $($step.arguments -join ' ')"
    }
    Write-RunReport -Report $report
    Write-Output ($report | ConvertTo-Json -Depth 12)
    exit 0
}

$results = @()
$diagnosticFlashed = $false
$normalRestored = $false
try {
    foreach ($step in $steps) {
        $started = Get-Date
        Write-Output "RUN: $($step.id)"
        & $step.command @($step.arguments)
        $exitCode = $LASTEXITCODE
        $ended = Get-Date
        $results += [ordered]@{
            id = $step.id
            status = if ($exitCode -eq 0) { "PASS" } else { "FAIL" }
            exit_code = $exitCode
            started_at = $started.ToString("o")
            ended_at = $ended.ToString("o")
        }
        if ($exitCode -ne 0) {
            throw "$($step.id) failed with exit code $exitCode"
        }
        if ($step.id -in @("flash_white", "flash_black")) {
            $diagnosticFlashed = $true
        }
        if ($step.id -eq "flash_normal_restore") {
            $normalRestored = $true
        }
    }
    $report.status = "PASS_MACHINE_DIGITAL_PENDING_OPERATOR_VISUAL"
    if ($Stage -eq "RestoreNormal") {
        $report.status = "PASS_NORMAL_FIRMWARE_RESTORED"
    }
} catch {
    $report.status = "FAIL"
    $report.error = $_.Exception.Message
    if ($diagnosticFlashed -and -not $normalRestored) {
        $restoreStarted = Get-Date
        Write-Output "RECOVERY: flash_normal_restore_after_failure"
        & $normalRestoreStep.command @($normalRestoreStep.arguments)
        $restoreExitCode = $LASTEXITCODE
        $restoreEnded = Get-Date
        $normalRestored = $restoreExitCode -eq 0
        $results += [ordered]@{
            id = "flash_normal_restore_after_failure"
            status = if ($normalRestored) { "PASS" } else { "FAIL" }
            exit_code = $restoreExitCode
            started_at = $restoreStarted.ToString("o")
            ended_at = $restoreEnded.ToString("o")
        }
    }
    throw
} finally {
    $report.normal_firmware_restored = [bool]$normalRestored
    $report.diagnostic_left_installed = [bool]($diagnosticFlashed -and -not $normalRestored -and $report.status -like "PASS_*")
    $report.completed_at = (Get-Date).ToString("o")
    $report.results = @($results)
    Write-RunReport -Report $report
}
