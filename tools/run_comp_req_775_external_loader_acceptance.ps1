#requires -Version 7.0
param(
    [switch]$Execute,
    [string]$PortName = "COM13",
    [string]$ProgrammerSerial = "066EFF535570514867221931",
    [ValidateSet("initial", "probe", "restore", "noop", "menu")]
    [string]$ResumePhase = "initial"
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$root = Join-Path $repo (
    ".cache\validation\comp-req-775-incremental-sync"
)
$runRoot = Join-Path $root "hardware-external-loader-acceptance"
$runner = Join-Path $repo "tools\run_comp_req_775_external_loader_sync.ps1"
$summaryVerifier = Join-Path $repo (
    "tools\faraday_upper_art\verify_comp_req_775_hardware_summary.py"
)
$summaryPath = Join-Path $runRoot "MACHINE_SUMMARY.json"
$bundleRoot = Join-Path $root "resource-ota"
$bootstrapImage = Join-Path $root (
    "stlink-sync\synthetic-generation-1.bin"
)
$offlinePath = Join-Path $root "OFFLINE_READY.json"
$offline = Get-Content -LiteralPath $offlinePath -Raw |
    ConvertFrom-Json -AsHashtable

$stages = [ordered]@{
    initial = [ordered]@{
        bundle = Join-Path $bundleRoot "generation-1.cuot"
        receipt = Join-Path $runRoot "01-initial-fixed.json"
        switches = @()
    }
    probe = [ordered]@{
        bundle = Join-Path $bundleRoot "generation-2.cuot"
        receipt = Join-Path $runRoot "02-one-frame-probe.json"
        switches = @("-PerformanceProbe")
    }
    restore = [ordered]@{
        bundle = Join-Path $bundleRoot "generation-3-restore.cuot"
        receipt = Join-Path $runRoot "03-fixed-restore.json"
        switches = @("-CaptureMenuBoundary")
    }
    noop = [ordered]@{
        bundle = Join-Path $bundleRoot "generation-3-noop.cuot"
        receipt = Join-Path $runRoot "04-final-noop.json"
        switches = @()
    }
    menu = [ordered]@{
        bundle = Join-Path $bundleRoot "generation-5-noop.cuot"
        receipt = Join-Path $runRoot "04-final-noop.json"
        switches = @("-CaptureMenuBoundary")
    }
}

foreach ($required in @(
    $runner,
    $summaryVerifier,
    $bootstrapImage,
    $offlinePath,
    $stages.initial.bundle,
    $stages.probe.bundle,
    $stages.restore.bundle,
    $stages.noop.bundle,
    $stages.menu.bundle
)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Missing acceptance input: $required"
    }
}

function Get-StageNames {
    switch ($ResumePhase) {
        "initial" { return @("initial", "probe", "restore", "noop") }
        "probe" { return @("probe", "restore", "noop") }
        "restore" { return @("restore", "noop") }
        "noop" { return @("noop") }
        "menu" { return @("menu") }
    }
}

function Invoke-Stage {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [switch]$Bootstrap
    )
    $stage = $stages[$Name]
    $arguments = @(
        "-NoProfile",
        "-File", $runner,
        "-PortName", $PortName,
        "-ProgrammerSerial", $ProgrammerSerial,
        "-ReceiptPath", $stage.receipt
    )
    if ($Bootstrap) {
        $arguments += @("-BootstrapImage", $bootstrapImage)
    } else {
        $arguments += @("-BundlePath", $stage.bundle)
    }
    $arguments += @($stage.switches)
    if ($Execute) {
        $arguments += "-Execute"
    }
    $output = & pwsh @arguments 2>&1
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        $detail = $output -join "`n"
        throw "Stage $Name failed ($exitCode): $detail"
    }
    if ($Execute) {
        return Get-Content -LiteralPath $stage.receipt -Raw |
            ConvertFrom-Json -AsHashtable
    }
    return ($output -join "`n") | ConvertFrom-Json -AsHashtable
}

if (-not $Execute) {
    $preflight = [ordered]@{}
    foreach ($name in Get-StageNames) {
        $preflight[$name] = Invoke-Stage -Name $name
    }
    [ordered]@{
        schema = "companion.comp_req_775.external_loader_acceptance.v1"
        status = "CHECK_ONLY"
        resume_phase = $ResumePhase
        stages = $preflight
        summary = $summaryPath
        execute_command = (
            "pwsh -NoProfile -File .\tools\" +
            "run_comp_req_775_external_loader_acceptance.ps1 -Execute" +
            $(if ($ResumePhase -ne "initial") {
                " -ResumePhase $ResumePhase"
            } else {
                ""
            })
        )
        hardware_contact = 0
    } | ConvertTo-Json -Depth 12
    exit 0
}

. (Join-Path $repo "tools\companion_wb55_lock.ps1")
$lockContext = $null
$results = [ordered]@{}
$hardwareContact = 0
try {
    $lockContext = Enter-CompanionWb55Lock -Purpose (
        "COMP-REQ-775 complete External Loader acceptance"
    )
    New-Item -ItemType Directory -Force -Path $runRoot | Out-Null
    foreach ($name in Get-StageNames) {
        try {
            $hardwareContact = 1
            $results[$name] = Invoke-Stage -Name $name
        } catch {
            if ($name -ne "initial") {
                throw
            }
            $failed = $null
            if (Test-Path -LiteralPath $stages.initial.receipt -PathType Leaf) {
                $failed = Get-Content -LiteralPath $stages.initial.receipt -Raw |
                    ConvertFrom-Json -AsHashtable
            }
            $errorText = $(if ($null -ne $failed) {
                [string]$failed.error
            } else {
                $_.Exception.Message
            })
            if ($errorText -notmatch (
                    "base identity does not match|no supported CEMP"
                )) {
                throw
            }
            $results.initial = Invoke-Stage -Name "initial" -Bootstrap
            $results.initial.bootstrap_used = $true
        }
    }
    if ($results.Contains("menu")) {
        $results["noop"] = $results.menu
    }

    if ($results.Contains("noop") -and
        -not [bool]$results.noop.noop -and
        $null -eq $results.noop.inactive_root_last -and
        [int]$results.noop.active_generation_before -eq
            [int]$results.noop.active_generation_after -and
        [int]$results.noop.recording_resource_pack.changed_sector_count -gt 0) {
        $staticInstallPath = Join-Path $runRoot (
            "04-static-resource-install.json"
        )
        Copy-Item -LiteralPath $stages.noop.receipt `
            -Destination $staticInstallPath -Force
        $results["static_install"] = $results.noop
        $results["noop"] = Invoke-Stage -Name "noop"
    }

    foreach ($requiredStage in @("probe", "restore", "noop")) {
        if (-not $results.Contains($requiredStage)) {
            $path = $stages[$requiredStage].receipt
            if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
                throw "Resume is missing receipt for stage $requiredStage."
            }
            $results[$requiredStage] = Get-Content -LiteralPath $path -Raw |
                ConvertFrom-Json -AsHashtable
        }
    }
    $probe = $results.probe
    $restore = $results.restore
    $noop = $results.noop
    $menuStage = $(if (
        $restore.Contains("menu_boundary") -and
        $restore.menu_boundary.Contains("evidence")
    ) {
        $restore
    } elseif (
        $noop.Contains("menu_boundary") -and
        $noop.menu_boundary.Contains("evidence")
    ) {
        $noop
    } else {
        $null
    })
    $fixedResource = [string]$offline.resource_id
    $checks = [ordered]@{
        one_frame_under_30s = (
            [int]$probe.timing_ms.total -le 30000 -and
            [bool]$probe.performance_contract.changed_resource_under_30s
        )
        one_frame_ten_data_sectors = (
            @($probe.changed_data_sectors).Count -eq 10
        )
        one_frame_root_last = (
            [string]$probe.inactive_root_last -eq "0x1FF000"
        )
        one_frame_internal_flash_zero = (
            [int]$probe.internal_flash_write_bytes -eq 0
        )
        probe_requires_restore = (
            [string]$probe.status -eq "MACHINE_READY_RESTORE_REQUIRED"
        )
        restore_fixed_resource = (
            [string]$restore.target_root.resource_id -eq $fixedResource
        )
        restore_partition_readback = (
            [bool]$restore.partition_readback_verified
        )
        restore_ordinary_reset_all = (
            $restore.Contains("ordinary_reset") -and
            $restore.ordinary_reset.Contains("checks") -and
            $restore.ordinary_reset.checks.Values -notcontains $false
        )
        menu_boundary_all = (
            $null -ne $menuStage -and
            $menuStage.menu_boundary.evidence.Contains("checks") -and
            $menuStage.menu_boundary.evidence.checks.Values -notcontains $false
        )
        final_noop_under_10s = (
            [int]$noop.timing_ms.total -le 10000 -and
            [bool]$noop.performance_contract.same_resource_under_10s
        )
        final_noop_external_zero = (
            [int]$noop.external_flash_write_bytes -eq 0
        )
        final_noop_internal_zero = (
            [int]$noop.internal_flash_write_bytes -eq 0
        )
        final_resource_fixed = (
            [string]$noop.target_root.resource_id -eq $fixedResource
        )
        final_recording_resources_fixed = (
            [bool]$noop.recording_resource_pack.current_match -and
            [int]$noop.recording_resource_pack.changed_sector_count -eq 0
        )
        final_readback_verified = [bool]$noop.partition_readback_verified
        protected_partitions_zero = (
            [int]$probe.recording_partition_write_bytes -eq 0 -and
            [int]$restore.recording_partition_write_bytes -eq 0 -and
            [int]$noop.recording_partition_write_bytes -eq 0 -and
            [int]$probe.protected_partitions.loader_internal_flash_write_bytes -eq 0 -and
            [int]$restore.protected_partitions.ota_app_internal_flash_write_bytes -eq 0 -and
            [int]$noop.protected_partitions.other_internal_flash_write_bytes -eq 0
        )
    }
    if ($checks.Values -contains $false) {
        throw "Final External Loader acceptance checks failed."
    }
    & python $summaryVerifier `
        --initial $stages.initial.receipt `
        --probe $stages.probe.receipt `
        --restore $stages.restore.receipt `
        --noop $stages.noop.receipt `
        --offline $offlinePath `
        --output $summaryPath | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Final hardware-summary verifier rejected the stage receipts."
    }
    $summary = Get-Content -LiteralPath $summaryPath -Raw |
        ConvertFrom-Json -AsHashtable
    $summary.workflow_lock = Get-CompanionWb55LockEvidenceSummary $lockContext
    if ($results.Contains("static_install")) {
        $summary.static_resource_install = $results.static_install
    }
    $summary.controller = (
        "tools/run_comp_req_775_external_loader_acceptance.ps1"
    )
    $summary | ConvertTo-Json -Depth 20 |
        Set-Content -LiteralPath $summaryPath -Encoding utf8
    Write-Output (
        (
            "MACHINE_READY_COMP_REQ_775 one_frame_ms={0} " +
            "final_noop_ms={1} final_resource_fixed=1"
        ) -f [int]$probe.timing_ms.total, [int]$noop.timing_ms.total
    )
} catch {
    $failedSummary = [ordered]@{
        schema = "companion.comp_req_775.external_loader_acceptance.v1"
        status = "FAILED"
        error = $_.Exception.Message
        stages = $results
        hardware_contact = $hardwareContact
    }
    New-Item -ItemType Directory -Force -Path $runRoot | Out-Null
    $failedSummary | ConvertTo-Json -Depth 20 |
        Set-Content -LiteralPath $summaryPath -Encoding utf8
    throw
} finally {
    if ($null -ne $lockContext) {
        Exit-CompanionWb55Lock
    }
}
