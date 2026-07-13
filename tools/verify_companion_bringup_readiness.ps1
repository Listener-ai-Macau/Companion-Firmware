param(
    [string] $PackagePath,
    [string] $TypeRepoRoot = (Join-Path $PSScriptRoot "..\..\..\Listener\Listener-Type"),
    [switch] $Full,
    [switch] $SkipTypeBuild,
    [switch] $SkipRustChecks,
    [switch] $SkipA1A2DryRun,
    [switch] $SkipTypeCompanionVisual,
    [switch] $IncludeTypeHarness,
    [switch] $StaticOnly
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if ($StaticOnly -and $Full) {
    throw "-StaticOnly cannot be combined with -Full; run one readiness mode at a time."
}
if ($StaticOnly -and $IncludeTypeHarness) {
    throw "-StaticOnly cannot be combined with -IncludeTypeHarness; use fast or full mode for package/Type harness checks."
}
if ($StaticOnly -and -not [string]::IsNullOrWhiteSpace($PackagePath)) {
    throw "-StaticOnly does not consume -PackagePath; use fast or full mode when package validation is needed."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$typeRoot = $null
if ($IncludeTypeHarness) {
    $typeRoot = (Resolve-Path $TypeRepoRoot).Path
}
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outDir = Join-Path $repoRoot ".cache\validation\companion-bringup-readiness-$stamp"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$steps = [System.Collections.Generic.List[object]]::new()
$manualGates = [System.Collections.Generic.List[object]]::new()
$requiredFailureCount = 0

function ConvertTo-CommandLine {
    param(
        [Parameter(Mandatory = $true)][string] $FilePath,
        [string[]] $Arguments = @()
    )

    $parts = @($FilePath) + $Arguments
    return ($parts | ForEach-Object {
        $text = [string] $_
        if ($text -match '[\s"`]' -or $text -eq "") {
            '"' + ($text -replace '"', '\"') + '"'
        } else {
            $text
        }
    }) -join " "
}

function Get-SafeLogName {
    param([Parameter(Mandatory = $true)][string] $Name)
    return (($Name.ToLowerInvariant() -replace '[^a-z0-9_.-]+', '-') -replace '^-|-$', '') + ".log"
}

function Resolve-CompanionPackage {
    param([string] $Path)

    if (-not [string]::IsNullOrWhiteSpace($Path)) {
        return (Resolve-Path $Path).Path
    }

    $packageRoot = Join-Path $repoRoot ".cache\ota_firmware"
    $latest = Get-ChildItem -LiteralPath $packageRoot -Filter "companion-ota-*.zip" -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $latest) {
        throw "No Companion OTA package found under $packageRoot. Run with -Full or run tools\package_ota_firmware.ps1 first."
    }
    return $latest.FullName
}

function Invoke-ReadinessStep {
    param(
        [Parameter(Mandatory = $true)][string] $Name,
        [Parameter(Mandatory = $true)][string] $WorkingDirectory,
        [Parameter(Mandatory = $true)][string] $FilePath,
        [string[]] $Arguments = @(),
        [bool] $Required = $true
    )

    $logPath = Join-Path $outDir (Get-SafeLogName $Name)
    $commandLine = ConvertTo-CommandLine -FilePath $FilePath -Arguments $Arguments
    $started = Get-Date
    $status = "PASS"
    $message = "ok"
    $exitCode = 0

    Write-Output ""
    Write-Output "== $Name =="
    Write-Output $commandLine

    Push-Location $WorkingDirectory
    try {
        & $FilePath @Arguments 2>&1 | Tee-Object -FilePath $logPath
        $exitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int] $LASTEXITCODE }
        if ($exitCode -ne 0) {
            throw "$Name failed with exit code $exitCode."
        }
    } catch {
        $status = "FAIL"
        $message = $_.Exception.Message
        if ($Required) {
            $script:requiredFailureCount += 1
        }
        Write-Output "FAIL: $message"
    } finally {
        Pop-Location
    }

    $ended = Get-Date
    $steps.Add([ordered]@{
        name = $Name
        status = $status
        required = $Required
        command = $commandLine
        working_directory = $WorkingDirectory
        exit_code = $exitCode
        log = $logPath
        started_at = $started.ToString("o")
        ended_at = $ended.ToString("o")
        duration_ms = [int64]($ended - $started).TotalMilliseconds
        message = $message
    }) | Out-Null
}

function Add-ManualGate {
    param(
        [Parameter(Mandatory = $true)][string] $Name,
        [Parameter(Mandatory = $true)][string] $Evidence,
        [Parameter(Mandatory = $true)][string] $Command
    )

    $manualGates.Add([ordered]@{
        name = $Name
        status = "MANUAL_REQUIRED"
        evidence = $Evidence
        command = $Command
    }) | Out-Null
}

function ConvertTo-ReadinessMarkdown {
    param(
        [Parameter(Mandatory = $true)] $Report,
        [Parameter(Mandatory = $true)] $StepItems,
        [Parameter(Mandatory = $true)] $GateItems
    )

    $lines = @(
        "# Companion Bring-Up Readiness Report",
        "",
        "- Status: $($Report["status"])",
        "- Mode: $($Report["mode"])",
        "- Generated: $($Report["generated_at"])",
        "- Package: ``$($Report["package_path"])``",
        "- Output dir: ``$($Report["output_dir"])``",
        "",
        "## Static Steps"
    )

    foreach ($step in $StepItems) {
        $lines += "- $($step["name"]): $($step["status"]) (required=$($step["required"]), exit=$($step["exit_code"]))"
        $lines += "  - Command: ``$($step["command"])``"
        $lines += "  - Log: ``$($step["log"])``"
        if ($step["message"] -and $step["message"] -ne "ok") {
            $lines += "  - Message: $($step["message"])"
        }
    }

    $lines += ""
    $lines += "## Manual Gates Remaining"
    $lines += ""
    $lines += "These gates intentionally require real Companion hardware/operator evidence and are not executed by the no-hardware readiness preflight."
    $lines += ""
    $lines += "To run the listed hardware gates in one locked operator flow:"
    $lines += ""
    $lines += "``````powershell"
    $lines += $Report["hardware_acceptance_runner"]
    $lines += "``````"
    $lines += ""
    $lines += "After collecting the real-device evidence, run:"
    $lines += ""
    $lines += "``````powershell"
    $lines += $Report["manual_evidence_verifier"]
    $lines += "``````"

    foreach ($gate in $GateItems) {
        $lines += ""
        $lines += "### $($gate["name"])"
        $lines += ""
        $lines += "- Status: $($gate["status"])"
        $lines += "- Evidence required: $($gate["evidence"])"
        $lines += "- Command/action:"
        $lines += ""
        $lines += "``````powershell"
        $lines += $gate["command"]
        $lines += "``````"
    }

    return $lines
}

if ($Full -and -not $StaticOnly) {
    Invoke-ReadinessStep -Name "build OTA loader" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments @("-NoProfile", "-File", ".\tools\build_companion_ota_loader.ps1", "-Force")
    Invoke-ReadinessStep -Name "build NUCLEO bringup" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments @("-NoProfile", "-File", ".\tools\build_nucleo_bringup.ps1", "-Force")
    Invoke-ReadinessStep -Name "build NUCLEO OTA app" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments @("-NoProfile", "-File", ".\tools\build_nucleo_bringup.ps1", "-OtaApp", "-Force")
    Invoke-ReadinessStep -Name "package Companion OTA and wired factory" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments @("-NoProfile", "-File", ".\tools\package_ota_firmware.ps1", "-Channel", "development", "-BoardTarget", "NUCLEO-WB55RG")
}

$resolvedPackagePath = if ($StaticOnly) { "<static-only-no-package>" } else { Resolve-CompanionPackage -Path $PackagePath }
$typeUiManualDryRunSummary = $null
$hardwareAcceptanceDryRunSummary = $null

Invoke-ReadinessStep -Name "Companion build environment check" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments @("-NoProfile", "-File", ".\tools\build.ps1", "-CheckOnly")
Invoke-ReadinessStep -Name "Companion workspace submodule policy" -WorkingDirectory $repoRoot -FilePath "python" -Arguments @(".\tools\verify_workspace_submodule_policy.py")
Invoke-ReadinessStep -Name "Companion devboard IOC import" -WorkingDirectory $repoRoot -FilePath "python" -Arguments @(".\tools\verify_devboard_ioc_import.py")
Invoke-ReadinessStep -Name "verify Companion OTA static contract" -WorkingDirectory $repoRoot -FilePath "python" -Arguments @(".\tools\verify_ota_contract_static.py")
Invoke-ReadinessStep -Name "Companion BLE probe self-test" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments @("-NoProfile", "-File", ".\tools\companion_ble_probe.ps1", "-SelfTest")
Invoke-ReadinessStep -Name "Companion recording cache model" -WorkingDirectory $repoRoot -FilePath "python" -Arguments @(".\tools\verify_recording_cache_model.py")
Invoke-ReadinessStep -Name "Companion recording FSM static" -WorkingDirectory $repoRoot -FilePath "python" -Arguments @(".\tools\verify_recording_fsm_static.py")
Invoke-ReadinessStep -Name "Companion diagnostics static" -WorkingDirectory $repoRoot -FilePath "python" -Arguments @(".\tools\verify_companion_diagnostics_static.py")
$screenAcceptanceArgs = @(".\tools\run_expression_acceptance.py", "--skip-build", "--output", (Join-Path $outDir "companion-screen-acceptance-run.json"))
if ($StaticOnly) {
    $screenAcceptanceArgs += "--pass-only"
}
Invoke-ReadinessStep -Name "Companion screen software acceptance" -WorkingDirectory $repoRoot -FilePath "python" -Arguments $screenAcceptanceArgs

if ($IncludeTypeHarness) {
    Invoke-ReadinessStep -Name "verify Listener VKA1 static contract" -WorkingDirectory $repoRoot -FilePath "python" -Arguments @(".\tools\verify_listener_vka1_static.py")

    $typePackageArgs = @("-NoProfile", "-File", ".\tools\verify_type_companion_package_static.ps1", "-PackagePath", $resolvedPackagePath)
    if ((-not $Full) -or $SkipRustChecks) {
        $typePackageArgs += "-SkipTypeRust"
    }
    Invoke-ReadinessStep -Name "verify Type Companion package integration" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments $typePackageArgs

    if (-not $SkipTypeCompanionVisual) {
        Invoke-ReadinessStep -Name "Type temporary Companion visual smoke" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments @("-NoProfile", "-File", ".\tools\capture_type_companion_visual.ps1", "-TypeRepoRoot", $typeRoot, "-OutputDir", (Join-Path $outDir "type-companion-visual"))
    }

    if ($Full -and -not $SkipTypeBuild) {
        Invoke-ReadinessStep -Name "Type firmware OTA frontend tests" -WorkingDirectory $typeRoot -FilePath "npm.cmd" -Arguments @("run", "test:firmware-ota")
        Invoke-ReadinessStep -Name "Type production build" -WorkingDirectory $typeRoot -FilePath "npm.cmd" -Arguments @("run", "build")
    }

    if ($Full -and -not $SkipRustChecks) {
        Invoke-ReadinessStep -Name "Type firmware_ota rust tests" -WorkingDirectory (Join-Path $typeRoot "src-tauri") -FilePath "cargo" -Arguments @("test", "--lib", "firmware_ota")
        Invoke-ReadinessStep -Name "Type stm32wb_st_ota rust tests" -WorkingDirectory (Join-Path $typeRoot "src-tauri") -FilePath "cargo" -Arguments @("test", "--lib", "stm32wb_st_ota")
    }

    if (-not $SkipA1A2DryRun) {
        Invoke-ReadinessStep -Name "Companion Type A1 A2 dry run" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments @("-NoProfile", "-File", ".\tools\verify_companion_type_a1_a2.ps1", "-TypeRepoRoot", $typeRoot)
    }

    $typeUiManualDryRunDir = Join-Path $outDir "type-ui-manual-dry-run"
    $typeUiManualDryRunSummary = Join-Path $typeUiManualDryRunDir "companion-type-ui-manual-summary.json"
    Invoke-ReadinessStep -Name "Companion Type UI manual dry run" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments @("-NoProfile", "-File", ".\tools\verify_companion_type_ui_manual.ps1", "-PackagePath", $resolvedPackagePath, "-TypeRepoRoot", $typeRoot, "-OutDir", $typeUiManualDryRunDir)
}

if (-not $StaticOnly) {
    Invoke-ReadinessStep -Name "Companion BLE OTA dry run" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments @("-NoProfile", "-File", ".\tools\verify_companion_ble_ota.ps1", "-PackagePath", $resolvedPackagePath)
    Invoke-ReadinessStep -Name "Companion wired flash dry run" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments @("-NoProfile", "-File", ".\tools\verify_companion_wired_flash.ps1", "-PackagePath", $resolvedPackagePath)
    $hardwareAcceptanceDryRunDir = Join-Path $outDir "hardware-acceptance-dry-run"
    $hardwareAcceptanceDryRunSummary = Join-Path $hardwareAcceptanceDryRunDir "companion-hardware-acceptance-summary.json"
    $hardwareAcceptanceDryRunArgs = @("-NoProfile", "-File", ".\tools\verify_companion_hardware_acceptance.ps1", "-PackagePath", $resolvedPackagePath, "-OutDir", $hardwareAcceptanceDryRunDir)
    if ($IncludeTypeHarness) {
        $hardwareAcceptanceDryRunArgs += @("-TypeRepoRoot", $typeRoot, "-IncludeTypeHarness", "-IncludeTypeUiGate")
    }
    Invoke-ReadinessStep -Name "Companion hardware acceptance dry run" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments $hardwareAcceptanceDryRunArgs
    Invoke-ReadinessStep -Name "Companion manual gate evidence checklist" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments @("-NoProfile", "-File", ".\tools\verify_companion_manual_gate_evidence.ps1", "-ChecklistOnly", "-PackagePath", $resolvedPackagePath)
}
Invoke-ReadinessStep -Name "Companion git diff check" -WorkingDirectory $repoRoot -FilePath "git" -Arguments @("diff", "--check")
if ($IncludeTypeHarness) {
    Invoke-ReadinessStep -Name "Type git diff check" -WorkingDirectory $typeRoot -FilePath "git" -Arguments @("diff", "--check")
}

$aiw = "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1"
$hardwareAcceptanceCommand = if ($StaticOnly) { "<static-only-no-hardware-command>" } else { "pwsh -NoProfile -File $aiw with-lock -Resource Companion-WB55,BLE-Companion -Purpose `"Companion hardware acceptance`" -Run pwsh -NoProfile -File .\tools\verify_companion_hardware_acceptance.ps1 -Execute -WorkflowLockHeld -PackagePath `"$resolvedPackagePath`"" }
$manualEvidenceCommand = if ($StaticOnly) { "<static-only-no-manual-evidence-command>" } else { "pwsh -NoProfile -File .\tools\verify_companion_manual_gate_evidence.ps1 -PackagePath '$resolvedPackagePath' -NativeBleBenchPath <companion-ble-real-bench.json> -BleOtaEvidencePath <companion-ble-ota-summary.json> -WiredFlashEvidencePath <companion-wired-flash-summary.json>" }
if (-not $StaticOnly) {
    if ($IncludeTypeHarness) {
        $hardwareAcceptanceCommand += " -IncludeTypeHarness -IncludeTypeUiGate -EvidencePath <companion_ui_screenshot_or_log>"
    }
    $nativeBleCommand = "pwsh -NoProfile -File $aiw with-lock -Resource Companion-WB55,BLE-Companion -Purpose `"Companion native BLE GATT bench validation`" -Run python .\tools\companion_ble_real_bench.py --name companion --timeout 20 --notify-timeout 10 --output .\.cache\validation\companion-real-ble-gatt-<timestamp>\companion-ble-real-bench.json --json"
    $a1a2Command = "pwsh -NoProfile -File $aiw with-lock -Resource Companion-WB55,BLE-Companion -Purpose `"Companion legacy Type A1/A2 bench validation`" -Run pwsh -NoProfile -File .\tools\verify_companion_type_a1_a2.ps1 -Execute -WorkflowLockHeld"
    $bleOtaCommand = "pwsh -NoProfile -File $aiw with-lock -Resource Companion-WB55,BLE-Companion -Purpose `"Companion BLE OTA validation`" -Run pwsh -NoProfile -File .\tools\verify_companion_ble_ota.ps1 -Execute -WorkflowLockHeld -PackagePath `"$resolvedPackagePath`""
    $wiredCommand = "pwsh -NoProfile -File $aiw with-lock -Resource Companion-WB55 -Purpose `"Companion wired factory flash validation`" -Run pwsh -NoProfile -File .\tools\verify_companion_wired_flash.ps1 -Execute -WorkflowLockHeld -PackagePath `"$resolvedPackagePath`""
    $typeUiCommand = "pwsh -NoProfile -File $aiw with-lock -Resource Companion-WB55,BLE-Companion -Purpose `"Companion Type UI validation`" -Run pwsh -NoProfile -File .\tools\verify_companion_type_ui_manual.ps1 -Execute -WorkflowLockHeld -PackagePath `"$resolvedPackagePath`" -EvidencePath <companion_ui_screenshot_or_log>"
    if ($IncludeTypeHarness) {
        $manualEvidenceCommand += " -A1A2SummaryPath <companion-type-a1-a2-summary.json> -IncludeTypeHarness -TypeUiEvidencePath <companion-type-ui-manual-summary.json> -IncludeTypeUiGate"
    }

    Add-ManualGate -Name "real Companion-native BLE GATT bench validation" -Evidence "tools\companion_ble_real_bench.py writes companion-ble-real-bench.json with status PASS after scan, service discovery, native GATT reads/writes, diagnostics, privacy refusal, and OTA readiness." -Command $nativeBleCommand
    if ($IncludeTypeHarness) {
        Add-ManualGate -Name "legacy Type A1/A2 bench validation" -Evidence "Compatibility JSON and Markdown under .cache\validation\companion-type-a1-a2-* with status PASS." -Command $a1a2Command
    }
    Add-ManualGate -Name "real Companion BLE OTA bench validation" -Evidence "tools\verify_companion_ble_ota.ps1 writes companion_ble_ota_result_json with status PASS, versionConfirmed=true, and transport=denzic_ota_v1." -Command $bleOtaCommand
    Add-ManualGate -Name "real Companion wired flash from same package" -Evidence "tools\verify_companion_wired_flash.ps1 writes wired_firmware_result_json with status PASS, mode=flash, port=SWD, and STM32CubeProgrammer verification." -Command $wiredCommand
    if ($IncludeTypeHarness) {
        Add-ManualGate -Name "Type temporary Companion debug page" -Evidence "tools\verify_companion_type_ui_manual.ps1 writes companion_type_ui_manual_result_json with status PASS after the operator confirms BLE subscription, A1, A2, BLE OTA entry, wired flash entry, and 总体验收 entry." -Command $typeUiCommand
    }
}

$status = if ($requiredFailureCount -gt 0) {
    "FAIL"
} elseif ($manualGates.Count -gt 0) {
    "PASS_STATIC_MANUAL_GATES_REMAIN"
} else {
    "PASS"
}

$report = [ordered]@{
    schema = "companion.bringup_readiness.v1"
    status = $status
    mode = if ($StaticOnly) { "static-only" } elseif ($Full) { "full" } else { "fast" }
    generated_at = (Get-Date).ToString("o")
    repo_root = $repoRoot
    independent_release_gate = -not [bool]$IncludeTypeHarness
    type_harness_included = [bool]$IncludeTypeHarness
    type_repo_root = $typeRoot
    package_path = $resolvedPackagePath
    output_dir = $outDir
    type_visual_summary = if ($IncludeTypeHarness) { Join-Path $outDir "type-companion-visual\type-companion-visual-summary.json" } else { $null }
    hardware_acceptance_dry_run = $hardwareAcceptanceDryRunSummary
    hardware_acceptance_runner = $hardwareAcceptanceCommand
    manual_evidence_verifier = $manualEvidenceCommand
    full_static_note = if ($StaticOnly) { "Static-only mode skips package, OTA dry-run, wired flash dry-run, and hardware manual-gate emission; use fast or full mode before hardware acceptance." } elseif ($Full) { "Full independent Companion rebuild/check path was requested. Pass -IncludeTypeHarness only for legacy Listener-Type bench integration checks." } else { "Fast mode reuses the latest package and skips firmware rebuilds. Run with -Full before final static signoff; pass -IncludeTypeHarness only for legacy Listener-Type bench integration checks." }
    steps = @($steps)
    manual_gates = @($manualGates)
}

$reportPath = Join-Path $outDir "summary.json"
$reportMdPath = Join-Path $outDir "summary.md"
$report["summary_markdown"] = $reportMdPath
$report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $reportPath -Encoding utf8
ConvertTo-ReadinessMarkdown -Report $report -StepItems $steps -GateItems $manualGates |
    Set-Content -LiteralPath $reportMdPath -Encoding utf8

Write-Output ""
Write-Output "$status`: Companion bring-up readiness preflight complete."
Write-Output "Report: $reportPath"
Write-Output "Markdown: $reportMdPath"
Write-Output "Package: $resolvedPackagePath"
Write-Output "Manual gates remaining: $($manualGates.Count)"

if ($requiredFailureCount -gt 0) {
    throw "Companion bring-up readiness preflight failed with $requiredFailureCount required failure(s). See $reportPath"
}
