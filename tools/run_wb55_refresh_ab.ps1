param(
    [switch] $CheckOnly,
    [switch] $Execute,
    [switch] $SelfTestRecovery,
    [switch] $WorkflowLockHeld,
    [string] $Port,
    [ValidateRange(10, 120)]
    [int] $CaptureSeconds = 15,
    [string] $OutRoot,
    [string] $ProgrammerRoot = "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$flashRunner = Join-Path $PSScriptRoot "flash_nucleo_bringup.ps1"
$serialRunner = Join-Path $PSScriptRoot "capture_nucleo_serial.ps1"
$logVerifier = Join-Path $PSScriptRoot "verify_wb55_refresh_cadence_log.py"
$normalImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build\Companion_Nucleo_WB55RG_Bringup.hex"
$defaultOutRoot = Join-Path $repoRoot ".cache\validation\companion-performance\refresh-ab-current"
$runRoot = if ([string]::IsNullOrWhiteSpace($OutRoot)) { $defaultOutRoot } else { $OutRoot }
$runReport = Join-Path $runRoot "refresh-ab-run.json"

function RelPath {
    param([string] $Path)

    $resolved = Resolve-Path -LiteralPath $Path -ErrorAction SilentlyContinue
    if ($resolved) {
        return [System.IO.Path]::GetRelativePath($repoRoot, $resolved.Path).Replace("\", "/")
    }
    return [System.IO.Path]::GetRelativePath($repoRoot, $Path).Replace("\", "/")
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

    New-Item -ItemType Directory -Force -Path $runRoot | Out-Null
    $Report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $runReport -Encoding UTF8
    Write-Output "Refresh A/B report: $(RelPath $runReport)"
}

$selectedModes = @($CheckOnly.IsPresent, $Execute.IsPresent, $SelfTestRecovery.IsPresent) |
    Where-Object { $_ }
if (@($selectedModes).Count -ne 1) {
    throw "Use exactly one of -CheckOnly, -Execute, or -SelfTestRecovery."
}
if ($Execute -and -not $WorkflowLockHeld) {
    throw "Refusing WB55 refresh A/B execution without workflow lock acknowledgement. Run through aiw with-lock -Resource Companion-WB55 and pass -WorkflowLockHeld inside the locked command."
}

$profiles = @(
    [ordered]@{
        id = "differential"
        label = "verified two-plane differential"
        image = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_refresh_cadence_diagnostic\Companion_Nucleo_WB55RG_RefreshCadenceDiagnostic.hex"
        partial_profile = "differential"
        transport_profile = "vendor_edges"
        expected_control = "0xFC"
        expected_planes = 2
    },
    [ordered]@{
        id = "direct_bsrr"
        label = "direct-GPIO edge timing diagnostic"
        image = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_direct_gpio_spi_diagnostic\Companion_Nucleo_WB55RG_DirectGpioSpiDiagnostic.hex"
        partial_profile = "differential"
        transport_profile = "direct_bsrr"
        expected_control = "0xFC"
        expected_planes = 2
    },
    [ordered]@{
        id = "vendor_partial"
        label = "Good Display one-plane partial diagnostic"
        image = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_vendor_partial_diagnostic\Companion_Nucleo_WB55RG_VendorPartialDiagnostic.hex"
        partial_profile = "vendor_sample"
        transport_profile = "vendor_edges"
        expected_control = "0xFF"
        expected_planes = 1
    }
)

if (-not $SelfTestRecovery) {
    foreach ($path in @($flashRunner, $serialRunner, $logVerifier, $normalImage) + @($profiles | ForEach-Object { $_.image })) {
        if (-not (Test-Path -LiteralPath $path)) {
            throw "Required refresh A/B artifact is missing: $path. Rebuild the named diagnostic before opening a hardware lock."
        }
    }
}

$portArgs = @()
if (-not [string]::IsNullOrWhiteSpace($Port)) {
    $portArgs = @("-Port", $Port)
}

$steps = @()
foreach ($profile in $profiles) {
    $captureDir = Join-Path $runRoot $profile.id
    $rawLog = Join-Path $captureDir "nucleo-serial-raw.log"
    $parsedResult = Join-Path $captureDir "refresh-cadence-result.json"
    $steps += Build-Step -Id "flash_$($profile.id)" -Command "pwsh" -Arguments @(
        "-NoProfile", "-File", $flashRunner,
        "-ImagePath", $profile.image,
        "-ProgrammerRoot", $ProgrammerRoot
    ) -Purpose "Flash the $($profile.label) image."
    $captureArgs = @(
        "-NoProfile", "-File", $serialRunner,
        "-Execute", "-WorkflowLockHeld",
        "-Seconds", "$CaptureSeconds",
        "-ResetAfterOpen",
        "-OutDir", $captureDir
    ) + $portArgs
    $steps += Build-Step -Id "capture_$($profile.id)" -Command "pwsh" -Arguments $captureArgs -Purpose "Capture one reset-bounded trace for $($profile.id)."
    $steps += Build-Step -Id "parse_$($profile.id)" -Command "python" -Arguments @(
        $logVerifier,
        "--partial-profile", $profile.partial_profile,
        "--transport-profile", $profile.transport_profile,
        "--log", $rawLog,
        "--out", $parsedResult
    ) -Purpose "Reject an incomplete waveform, wrong transport, or stale diagnostic trace."
}

$normalRestoreStep = Build-Step -Id "flash_normal_restore" -Command "pwsh" -Arguments @(
    "-NoProfile", "-File", $flashRunner,
    "-ImagePath", $normalImage,
    "-ProgrammerRoot", $ProgrammerRoot
) -Purpose "Restore the normal quiet production firmware before the lock is released."
$steps += $normalRestoreStep

if ($SelfTestRecovery) {
    $steps = @(
        Build-Step -Id "flash_differential" -Command "pwsh" -Arguments @(
            "-NoProfile", "-Command", "Write-Output 'SELFTEST: flash_differential'; exit 0"
        ) -Purpose "Stub-only differential flash."
        Build-Step -Id "capture_differential" -Command "pwsh" -Arguments @(
            "-NoProfile", "-Command", "Write-Output 'SELFTEST: capture_differential failure'; exit 7"
        ) -Purpose "Stub-only capture failure."
    )
    $normalRestoreStep = Build-Step -Id "flash_normal_restore" -Command "pwsh" -Arguments @(
        "-NoProfile", "-Command", "Write-Output 'SELFTEST: flash_normal_restore'; exit 0"
    ) -Purpose "Stub-only normal firmware recovery."
}

$report = [ordered]@{
    schema_id = "companion.wb55.refresh_ab_run.v1"
    status = if ($CheckOnly) { "DRY-RUN" } elseif ($SelfTestRecovery) { "SELFTEST_RUNNING" } else { "RUNNING" }
    claim_scope = if ($CheckOnly) { "preflight_only_no_hardware_claim" } elseif ($SelfTestRecovery) { "stubbed_failure_recovery_no_hardware_claim" } else { "hardware_trace_pending_parser_results" }
    generated_at = (Get-Date).ToString("o")
    target = "NUCLEO-WB55RG + GDEY0154D67-T03 + FT6336U"
    capture_seconds = $CaptureSeconds
    output = [ordered]@{
        root = RelPath $runRoot
        run_report = RelPath $runReport
    }
    profiles = @($profiles | ForEach-Object {
        [ordered]@{
            id = $_.id
            label = $_.label
            image = RelPath $_.image
            partial_profile = $_.partial_profile
            transport_profile = $_.transport_profile
            expected_control = $_.expected_control
            expected_planes = $_.expected_planes
        }
    })
    steps = @($steps)
    notes = @(
        "Run only after the owner explicitly starts hardware acceptance and while the Companion-WB55 workflow lock is held.",
        "All three diagnostics use the same six-frame cadence; parser success is required before comparing timing or visible residuals.",
        "The direct-BSRR and vendor-partial images are diagnostic-only and must not become production behavior from serial timing alone.",
        "Any failure after a diagnostic flash attempts to restore the normal quiet production image before the lock is released.",
        "This runner collects machine traces only. It does not replace the focused ACPT-01 visual and touch review."
    )
}

if ($CheckOnly) {
    $report.completed_at = (Get-Date).ToString("o")
    $report.results = @()
    Write-Output "CHECK: WB55 refresh A/B sequence profiles=$($profiles.id -join ',') capture_seconds=$CaptureSeconds"
    foreach ($step in $steps) {
        Write-Output "CHECK: $($step.id): $($step.command) $($step.arguments -join ' ')"
    }
    Write-Output "CHECK: execute with workflow lock:"
    Write-Output "  pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose 'Companion WB55 refresh A/B' -Run pwsh -NoProfile -File .\tools\run_wb55_refresh_ab.ps1 -Execute -WorkflowLockHeld"
    Write-RunReport -Report $report
    Write-Output ($report | ConvertTo-Json -Depth 10)
    exit 0
}

if ($SelfTestRecovery) {
    Write-Output "SELFTEST: simulating a capture failure and normal firmware recovery without hardware"
}

New-Item -ItemType Directory -Force -Path $runRoot | Out-Null
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
        if ($step.id -like "flash_*") {
            $diagnosticFlashed = $true
        }
        if ($step.id -eq "flash_normal_restore") {
            $normalRestored = $true
        }
    }
    $report.status = "PASS"
} catch {
    $report.status = "FAIL"
    $report.error = $_.Exception.Message
    if ($diagnosticFlashed -and -not $normalRestored) {
        $restoreStarted = Get-Date
        Write-Output "RECOVERY: flash_normal_restore_after_failure"
        try {
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
        } catch {
            $restoreEnded = Get-Date
            $results += [ordered]@{
                id = "flash_normal_restore_after_failure"
                status = "FAIL"
                exit_code = $LASTEXITCODE
                started_at = $restoreStarted.ToString("o")
                ended_at = $restoreEnded.ToString("o")
                error = $_.Exception.Message
            }
        }
    }
    throw
} finally {
    $report.normal_firmware_restored = [bool]$normalRestored
    $report.completed_at = (Get-Date).ToString("o")
    $report.results = @($results)
    Write-RunReport -Report $report
}
