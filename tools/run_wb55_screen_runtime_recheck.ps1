param(
    [switch] $CheckOnly,
    [switch] $Execute,
    [switch] $SelfTestRecovery,
    [switch] $WorkflowLockHeld,
    [string] $Port,
    [int] $CaptureSeconds = 25,
    [string] $OutRoot,
    [string] $ProgrammerRoot = "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$menuEvidencePath = Join-Path $repoRoot "docs\validation\companion-screen-bilingual-menu-wb55.json"
$buildMatrixPath = Join-Path $repoRoot "docs\validation\companion-screen-wb55-build-matrix.json"
$provisionDir = $null
$normalDir = $null
$runReport = $null

function RelPath {
    param([string] $Path)
    $resolved = (Resolve-Path -LiteralPath $Path -ErrorAction SilentlyContinue)
    if ($resolved) {
        return [System.IO.Path]::GetRelativePath($repoRoot, $resolved.Path).Replace("\", "/")
    }
    return [System.IO.Path]::GetRelativePath($repoRoot, $Path).Replace("\", "/")
}

function Build-Step {
    param(
        [string] $Id,
        [string] $Command,
        [string[]] $Arguments
    )
    [ordered]@{
        id = $Id
        command = $Command
        arguments = @($Arguments)
    }
}

function Write-RunReport {
    param([object] $Report)
    $runRoot = Split-Path -Parent $runReport
    New-Item -ItemType Directory -Force -Path $runRoot | Out-Null
    $Report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $runReport -Encoding UTF8
    Write-Output "Runtime recheck report: $(RelPath $runReport)"
}

$selectedModes = @($CheckOnly.IsPresent, $Execute.IsPresent, $SelfTestRecovery.IsPresent) | Where-Object { $_ }
$selectedModeCount = @($selectedModes).Count
if ($selectedModeCount -gt 1) {
    throw "Use only one of -CheckOnly, -Execute, or -SelfTestRecovery."
}
if (-not $CheckOnly -and -not $Execute -and -not $SelfTestRecovery) {
    throw "Refusing to run without -CheckOnly, -Execute, or -SelfTestRecovery."
}
if ($Execute -and -not $WorkflowLockHeld) {
    throw "Refusing WB55 runtime recheck without workflow lock acknowledgement. Run through aiw with-lock -Resource Companion-WB55 and pass -WorkflowLockHeld inside the locked command."
}
if ($CaptureSeconds -lt 5 -or $CaptureSeconds -gt 120) {
    throw "CaptureSeconds must be between 5 and 120."
}
if (-not (Test-Path -LiteralPath $menuEvidencePath)) {
    throw "Missing menu evidence: $menuEvidencePath"
}
if (-not (Test-Path -LiteralPath $buildMatrixPath)) {
    throw "Missing WB55 build matrix evidence: $buildMatrixPath"
}

$menuEvidence = Get-Content -LiteralPath $menuEvidencePath -Raw | ConvertFrom-Json
$buildMatrix = Get-Content -LiteralPath $buildMatrixPath -Raw | ConvertFrom-Json
$resource = $menuEvidence.resource_pack
$runtime = $menuEvidence.runtime_evidence
$runtimeStatus = [string]$runtime.status
$revision = [int]$resource.revision
$crc32 = [string]$resource.pack_crc32
$pendingStatus = "REVISION_${revision}_RUNTIME_RECHECK_PENDING"
$passStatus = "REVISION_${revision}_RUNTIME_PASS_HUMAN_VISUAL_PENDING"
if ($revision -le 0 -or $crc32 -notmatch '^0x[0-9A-F]{8}$' -or $runtimeStatus -notin @($pendingStatus, $passStatus)) {
    throw "Expected a positive resource revision, uppercase CEMP CRC, and matching pending or promoted runtime status before running this recheck."
}
$defaultRunRoot = Join-Path $repoRoot ".cache\validation\rev$revision-runtime-current"
$runRoot = if ($OutRoot) { $OutRoot } else { $defaultRunRoot }
$provisionDir = Join-Path $runRoot "provision"
$normalDir = Join-Path $runRoot "normal"
$runReport = Join-Path $runRoot "runtime-recheck-run.json"
if ($runtimeStatus -eq $passStatus -and $Execute) {
    throw "Revision $revision runtime evidence is already promoted. Refusing to rerun the hardware recheck without first resetting the evidence state by an explicit maintenance task."
}
if ([string]$buildMatrix.status -ne "PASS") {
    throw "Expected WB55 build matrix PASS before runtime recheck."
}
$buildVariants = @($buildMatrix.build_variants.PSObject.Properties.Name)
foreach ($requiredVariant in @("dry_run_default", "ssd1681_real_panel", "screen_asset_provision")) {
    if ($buildVariants -notcontains $requiredVariant) {
        throw "Expected WB55 build matrix variant '$requiredVariant' before runtime recheck."
    }
}
$buildContracts = $buildMatrix.contracts
foreach ($requiredContract in @("build_logs_prove_all_variants", "queue_generation_compiles_in_all_variants", "screen_asset_provision_builds_current_external_assets")) {
    if ($buildContracts.$requiredContract -ne $true) {
        throw "Expected WB55 build matrix contract '$requiredContract' before runtime recheck."
    }
}
$provisionBuildSize = $buildMatrix.build_log_evidence.screen_asset_provision.size
if ($provisionBuildSize.text -le 0 -or $provisionBuildSize.data -lt 0 -or $provisionBuildSize.bss -lt 0 -or $provisionBuildSize.dec -le 0 -or [string]::IsNullOrWhiteSpace([string]$provisionBuildSize.hex)) {
    throw "Expected a valid current ScreenAssetProvision build size before runtime recheck."
}

$portArgs = @()
if (-not [string]::IsNullOrWhiteSpace($Port)) {
    $portArgs = @("-Port", $Port)
}

$steps = @(
    Build-Step -Id "flash_provision" -Command "pwsh" -Arguments @(
        "-NoProfile", "-File", ".\tools\flash_nucleo_bringup.ps1",
        "-ScreenAssetProvision", "-ProgrammerRoot", $ProgrammerRoot
    )
    Build-Step -Id "capture_provision" -Command "pwsh" -Arguments @(
        "-NoProfile", "-File", ".\tools\capture_nucleo_serial.ps1",
        "-Execute", "-WorkflowLockHeld", "-Seconds", "$CaptureSeconds",
        "-ResetAfterOpen", "-OutDir", $provisionDir
    ) + $portArgs
    Build-Step -Id "flash_normal" -Command "pwsh" -Arguments @(
        "-NoProfile", "-File", ".\tools\flash_nucleo_bringup.ps1",
        "-ProgrammerRoot", $ProgrammerRoot
    )
    Build-Step -Id "capture_normal" -Command "pwsh" -Arguments @(
        "-NoProfile", "-File", ".\tools\capture_nucleo_serial.ps1",
        "-Execute", "-WorkflowLockHeld", "-Seconds", "$CaptureSeconds",
        "-ResetAfterOpen", "-OutDir", $normalDir
    ) + $portArgs
)
if ($SelfTestRecovery) {
    $steps = @(
        Build-Step -Id "flash_provision" -Command "pwsh" -Arguments @(
            "-NoProfile", "-Command", "Write-Output 'SELFTEST: flash_provision'; exit 0"
        )
        Build-Step -Id "capture_provision" -Command "pwsh" -Arguments @(
            "-NoProfile", "-Command", "Write-Output 'SELFTEST: capture_provision failure'; exit 7"
        )
        Build-Step -Id "flash_normal" -Command "pwsh" -Arguments @(
            "-NoProfile", "-Command", "Write-Output 'SELFTEST: flash_normal'; exit 0"
        )
        Build-Step -Id "capture_normal" -Command "pwsh" -Arguments @(
            "-NoProfile", "-Command", "Write-Output 'SELFTEST: capture_normal'; exit 0"
        )
    )
}

$report = [ordered]@{
    schema = "companion.wb55_screen_runtime_recheck_run.v1"
    status = if ($CheckOnly) { "DRY-RUN" } elseif ($SelfTestRecovery) { "SELFTEST_RUNNING" } else { "RUNNING" }
    generated_at = (Get-Date).ToString("o")
    target = "NUCLEO-WB55RG + GDEY0154D67-T03 + FT6336U"
    resource = [ordered]@{
        revision = [int]$resource.revision
        total_bytes = [int]$resource.total_bytes
        pack_crc32 = [string]$resource.pack_crc32
        runtime_status = [string]$runtime.status
    }
    build_matrix = [ordered]@{
        path = RelPath $buildMatrixPath
        status = [string]$buildMatrix.status
        variants = @($buildVariants)
        screen_asset_provision_size = [ordered]@{
            text = [int]$provisionBuildSize.text
            data = [int]$provisionBuildSize.data
            bss = [int]$provisionBuildSize.bss
            dec = [int]$provisionBuildSize.dec
            hex = [string]$provisionBuildSize.hex
        }
    }
    output = [ordered]@{
        root = RelPath ((Split-Path -Parent $runReport))
        provision_dir = RelPath $provisionDir
        normal_dir = RelPath $normalDir
        run_report = RelPath $runReport
    }
    steps = @($steps)
    expected_runtime_markers = @(
        "mount=ok",
        "revision=$revision",
        "clips=33 frames=159",
        "expression_renderer=external_pack",
        "source=external_flash",
        "pet_behavior_selftest=pass failure_code=0",
        "touch-health] detected=1 identity=1 addr=0x38",
        "queue_generation revision=$revision",
        "coherent_generation=1",
        "generation_switches=",
        "last_stale_discarded=",
        "refresh mode=full",
        "complete=1"
    )
    notes = @(
        "Run only while holding the Companion-WB55 workflow hardware lock.",
        "SelfTestRecovery uses stub commands only and must never be treated as hardware evidence.",
        "Provision firmware writes the external CEMP asset pack, then normal firmware must be restored.",
        "This runner does not ask for human visual acceptance; it only collects machine runtime evidence.",
        "After Execute, run verify_wb55_screen_runtime_recheck_logs.py before promotion.",
        "Only after the log verifier reports PASS may promote_wb55_screen_runtime_recheck.py --apply update the runtime evidence.",
        "After promotion, rerun verify_companion_screen_pre_acceptance_health.py and verify_companion_screen_goal_audit.py before any human touch/visual acceptance."
        "Before hardware execution, verify_wb55_screen_build_matrix.py must prove dry_run_default, ssd1681_real_panel, and screen_asset_provision builds."
    )
}

if ($CheckOnly) {
    $report.completed_at = (Get-Date).ToString("o")
    $report.results = @()
    if ($runtimeStatus -eq $passStatus) {
        Write-Output "CHECK: rev$revision WB55 runtime evidence is already promoted"
        Write-Output "CHECK: resource revision=$($resource.revision) bytes=$($resource.total_bytes) crc=$($resource.pack_crc32)"
        Write-Output "CHECK: runtime_status=$runtimeStatus"
        Write-RunReport -Report $report
        Write-Output ($report | ConvertTo-Json -Depth 8)
        exit 0
    }
    Write-Output "CHECK: rev$revision WB55 runtime recheck sequence"
    Write-Output "CHECK: resource revision=$($resource.revision) bytes=$($resource.total_bytes) crc=$($resource.pack_crc32)"
    Write-Output "CHECK: build_matrix status=$($buildMatrix.status) variants=$($buildVariants -join ',')"
    Write-Output "CHECK: screen_asset_provision size=text:$($provisionBuildSize.text) data:$($provisionBuildSize.data) bss:$($provisionBuildSize.bss) dec:$($provisionBuildSize.dec) hex:$($provisionBuildSize.hex)"
    Write-Output "CHECK: output root=$((Split-Path -Parent $runReport))"
    foreach ($step in $steps) {
        Write-Output "CHECK: $($step.id): $($step.command) $($step.arguments -join ' ')"
    }
    Write-Output "CHECK: execute with workflow lock:"
    Write-Output "  pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose `"Companion WB55 rev$revision screen runtime recheck`" -Run pwsh -NoProfile -File .\tools\run_wb55_screen_runtime_recheck.ps1 -Execute -WorkflowLockHeld"
    Write-RunReport -Report $report
    Write-Output ($report | ConvertTo-Json -Depth 8)
    exit 0
}

if ($SelfTestRecovery) {
    Write-Output "SELFTEST: simulating provision success, capture failure, and normal firmware recovery without hardware"
}

$runRoot = Split-Path -Parent $runReport
New-Item -ItemType Directory -Force -Path $provisionDir | Out-Null
New-Item -ItemType Directory -Force -Path $normalDir | Out-Null
New-Item -ItemType Directory -Force -Path $runRoot | Out-Null

$results = @()
$provisionFlashed = $false
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
        if ($step.id -eq "flash_provision") {
            $provisionFlashed = $true
        } elseif ($step.id -eq "flash_normal") {
            $normalRestored = $true
        }
    }
    $report.status = "PASS"
} catch {
    $report.status = "FAIL"
    $report.error = $_.Exception.Message
    if ($provisionFlashed -and -not $normalRestored) {
        $restoreStarted = Get-Date
        Write-Output "RECOVERY: flash_normal_after_failure"
        try {
            $normalStep = $steps | Where-Object { $_.id -eq "flash_normal" } | Select-Object -First 1
            & $normalStep.command @($normalStep.arguments)
            $restoreExitCode = $LASTEXITCODE
            $restoreEnded = Get-Date
            $normalRestored = $restoreExitCode -eq 0
            $results += [ordered]@{
                id = "flash_normal_after_failure"
                status = if ($restoreExitCode -eq 0) { "PASS" } else { "FAIL" }
                exit_code = $restoreExitCode
                started_at = $restoreStarted.ToString("o")
                ended_at = $restoreEnded.ToString("o")
            }
        } catch {
            $restoreEnded = Get-Date
            $results += [ordered]@{
                id = "flash_normal_after_failure"
                status = "FAIL"
                exit_code = $LASTEXITCODE
                started_at = $restoreStarted.ToString("o")
                ended_at = $restoreEnded.ToString("o")
                error = $_.Exception.Message
            }
        }
    }
    $report.normal_firmware_restored = [bool]$normalRestored
    throw
} finally {
    if (-not $report.Contains("normal_firmware_restored")) {
        $report.normal_firmware_restored = [bool]$normalRestored
    }
    $report.completed_at = (Get-Date).ToString("o")
    $report.results = @($results)
    Write-RunReport -Report $report
}
