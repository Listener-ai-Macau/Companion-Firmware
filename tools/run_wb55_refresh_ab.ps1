param(
    [switch] $CheckOnly,
    [switch] $Execute,
    [switch] $SelfTestRecovery,
    [switch] $HardwareAcknowledged,
    [ValidateSet("all", "differential", "direct_bsrr", "vendor_partial")]
    [string] $Profile = "all",
    [ValidateRange(1, 40)]
    [int] $CadenceGroups = 1,
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
$cadenceBuildDir = if ($CadenceGroups -eq 1) {
    "build_refresh_cadence_diagnostic"
} else {
    "build_refresh_cadence_diagnostic_g$CadenceGroups"
}
$cadenceTarget = if ($CadenceGroups -eq 1) {
    "Companion_Nucleo_WB55RG_RefreshCadenceDiagnostic"
} else {
    "Companion_Nucleo_WB55RG_RefreshCadenceDiagnosticG$CadenceGroups"
}
$cadenceImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\$cadenceBuildDir\$cadenceTarget.hex"
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
if ($Execute -and -not $HardwareAcknowledged) {
    throw "Refusing WB55 refresh A/B execution without explicit hardware acknowledgement. Pass -HardwareAcknowledged only after the owner has started this physical diagnostic."
}

$allProfiles = @(
    [ordered]@{
        id = "differential"
        label = "verified two-plane differential"
        image = $cadenceImage
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

$profiles = if ($Profile -eq "all") {
    $allProfiles
} else {
    @($allProfiles | Where-Object { $_.id -eq $Profile })
}

if (-not $SelfTestRecovery -and -not $CheckOnly) {
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
foreach ($entry in $profiles) {
    $captureDir = Join-Path $runRoot $entry.id
    $rawLog = Join-Path $captureDir "nucleo-serial-raw.log"
    $parsedResult = Join-Path $captureDir "refresh-cadence-result.json"
    $entryCadenceGroups = if ($entry.id -eq "differential") { $CadenceGroups } else { 1 }
    $parseArguments = @(
        $logVerifier,
        "--partial-profile", $entry.partial_profile,
        "--transport-profile", $entry.transport_profile,
        "--groups", "$entryCadenceGroups",
        "--log", $rawLog,
        "--out", $parsedResult
    )
    if ($entry.id -eq "differential") {
        $parseArguments += "--micro-motion"
    }
    $steps += Build-Step -Id "flash_$($entry.id)" -Command "pwsh" -Arguments @(
        "-NoProfile", "-File", $flashRunner,
        "-ImagePath", $entry.image,
        "-ProgrammerRoot", $ProgrammerRoot
    ) -Purpose "Flash the $($entry.label) image."
    $captureArgs = @(
        "-NoProfile", "-File", $serialRunner,
        "-Execute",
        "-Seconds", "$CaptureSeconds",
        "-ResetAfterOpen",
        "-OutDir", $captureDir
    ) + $portArgs
    $steps += Build-Step -Id "capture_$($entry.id)" -Command "pwsh" -Arguments $captureArgs -Purpose "Capture one reset-bounded trace for $($entry.id)."
    $steps += Build-Step -Id "parse_$($entry.id)" -Command "python" -Arguments $parseArguments -Purpose "Reject an incomplete waveform, wrong transport, stale trace, or non-local micro-motion window."
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
    cadence_groups = $CadenceGroups
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
        "Run only after the owner explicitly starts hardware acceptance; every flash and capture independently acquires the Companion-WB55 mutex.",
        "The selected differential diagnostic uses $CadenceGroups bounded six-frame cadence group(s); parser success is required before comparing timing or visible residuals.",
        "The direct-BSRR and vendor-partial images are diagnostic-only and must not become production behavior from serial timing alone.",
        "Any failure after a diagnostic flash attempts to restore the normal quiet production image before the lock is released.",
        "This runner collects machine traces only. It does not replace the focused ACPT-01 visual and touch review."
    )
}

if ($CheckOnly) {
    $report.completed_at = (Get-Date).ToString("o")
    $report.results = @()
    Write-Output "CHECK: WB55 refresh A/B sequence profile=$Profile selected=$($profiles.id -join ',') cadence_groups=$CadenceGroups capture_seconds=$CaptureSeconds"
    foreach ($step in $steps) {
        Write-Output "CHECK: $($step.id): $($step.command) $($step.arguments -join ' ')"
    }
    Write-Output "CHECK: execute after explicit owner-started hardware acknowledgement:"
    Write-Output "  pwsh -NoProfile -File .\tools\run_wb55_refresh_ab.ps1 -Execute -HardwareAcknowledged -Profile differential -CadenceGroups $CadenceGroups"
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
