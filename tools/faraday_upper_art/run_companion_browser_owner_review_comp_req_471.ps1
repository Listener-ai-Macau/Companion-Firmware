#requires -Version 7.0
<#
.SYNOPSIS
Validates or executes the COMP-REQ-471 browser owner review.

.DESCRIPTION
Default-off. CheckOnly is filesystem-only and launches no process, server,
browser, prompt, or hardware operation. Execute is accepted only through the
matching supervisor after explicit owner acknowledgement.
#>

[CmdletBinding()]
param(
    [switch] $CheckOnly,
    [switch] $Execute,
    [switch] $OwnerStartAcknowledged,
    [switch] $Supervised,
    [ValidateRange(60, 3600)]
    [int] $OperatorTimeoutSeconds = 1800,
    [string] $WorkflowRepo = "",
    [string] $FixturePath = "",
    [string] $FixtureId = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$modeCount = @($CheckOnly.IsPresent, $Execute.IsPresent).Where({ $_ }).Count
if ($modeCount -ne 1) {
    throw "Default-off: choose exactly one of -CheckOnly or -Execute."
}
if ($Execute -and (-not $OwnerStartAcknowledged -or -not $Supervised)) {
    throw "Execute requires -OwnerStartAcknowledged and the canonical supervisor."
}
if ($Execute -and
    (-not [string]::IsNullOrWhiteSpace($FixturePath) -or
     -not [string]::IsNullOrWhiteSpace($FixtureId))) {
    throw "Fixtures are CheckOnly-only."
}

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$validationRelative = "docs\validation\companion-browser-visual-contract-comp-req-471"
$validationDir = Join-Path $repoRoot $validationRelative
$exportRelative = "docs\art\exports\companion-browser-visual-contract-comp-req-471"
$pageRelative = "docs\art\iterations\companion-pet-expression-v9-two-track-rig-v7\candidate\wb55-browser-parity-attempt-01\index.html"
$reviewUrl = "http://127.0.0.1:4173/docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html"
$promptSentinelPath = Join-Path $validationDir ".owner-review.prompt-active.lock"
$ownerResultPath = Join-Path $validationDir "owner-review.json"
$ownerRawPath = Join-Path $validationDir "owner-review.raw.json"
$ownerNotePath = Join-Path $validationDir "owner-review.note.txt"

$promptContract = [ordered]@{
    instance_count = 1
    title = "Companion 浏览器总体体验验收"
    buttons = @("通过", "失败")
    note_allowed = $true
    progress_text = "1/1 浏览器总体体验"
    scope_text = "仅验收同一 4173 总体页面中的表情、菜单与录音预览；browser-only，不接触硬件或 production。"
    message = @"
请在已打开的总体页面实际操作：
1. 单点屏幕，确认表情与眼神朝触点做一次响应且仍在表情页。
2. 向左、右、上、下连续拖动并回中心，确认始终只有一套脸、眼睛、眼珠和高光，没有旧 gaze 残留。
3. 原地长按直到进入菜单，依次点击四根菜单、Device > UI assets，再返回表情页。
4. 双击进入录音预览并返回，再次长按进入菜单，确认各路径可重复。
5. 判断 200x200 屏幕方向与居中正确，无叠加、无丢眼珠、无 404、无多余调试参数。
"@
    expected_text = "选择通过表示上述 browser-only 总体体验可作为 COMP-REQ-471 的人工回归合同；选择失败会保留机器 PASS 原样并返回上层页面迭代。备注允许留空。"
}

$fileSpecs = [ordered]@{
    page = [ordered]@{
        relative_path = $pageRelative
        sha256 = "BAE21BCCC7BB5FAD4A0922D5E9C42FCB25EF58DD7B8102A7C72656F7B700CF5E"
    }
    machine_result = [ordered]@{
        relative_path = "$validationRelative\machine-result.json"
        sha256 = "6A7EDAC4A9624842B154B717C090441E745AC6F65F8E73BC235E8E3C16D11EBD"
    }
    measured_diagnostic = [ordered]@{
        relative_path = "$validationRelative\measured-diagnostic.json"
        sha256 = "652C33E7BFB155974FD369DB069800E14595C26F5F1D7B6A7322ED30320CCA76"
    }
    capture_manifest = [ordered]@{
        relative_path = "$validationRelative\browser-capture\capture-manifest.json"
        sha256 = "1BEA10C8B988F72F48886012859F1D6C8801B15AFA18E89171235B7E33D2C815"
    }
    pointer_result = [ordered]@{
        relative_path = "$validationRelative\pointer-contract\touch-pointer-contract-result.json"
        sha256 = "082344F03017DC54E0A385E5CFF8BB7F4031889A602476FFD2589B130CFFE09F"
    }
    c_pack_result = [ordered]@{
        relative_path = "$exportRelative\c-asset-pack-machine-result.json"
        sha256 = "17B71D7AC5FC777FEB301EED39E70431CC65BEFF8CC25FD7EEC613206280CD1E"
    }
    frames_bin = [ordered]@{
        relative_path = "$exportRelative\frames.bin"
        sha256 = "D4DA2FCA6863C1B8F5DD28D70566712DCD91AB7383CA486735DFD253F7361E6D"
    }
    visual_contract = [ordered]@{
        relative_path = "$exportRelative\visual-contract.json"
        sha256 = "E5C6B30D8BF317FC8321D82E087D3B46552B4523FD8B67FFF3E6ABA89AAE4260"
    }
    state_transitions = [ordered]@{
        relative_path = "$exportRelative\state-transitions.json"
        sha256 = "442F5A9E87988A3F8BE15ECC2A2500CA64537FA2B6DBD96F6FFDDD070DD7F918"
    }
    handoff_manifest = [ordered]@{
        relative_path = "$exportRelative\handoff-manifest.json"
        sha256 = "E89E3E40EF9DE9466CFBC9664AD16E49E36747F8A600966A6CF0D640EFED1468"
    }
    c_pack_manifest = [ordered]@{
        relative_path = "$exportRelative\c-asset-pack-manifest.json"
        sha256 = "0F0FE7B91707F20CF942A0B994BD776B69D404A004D9985B98EC6838CA752DBA"
    }
    c_pack_header = [ordered]@{
        relative_path = "$exportRelative\companion_visual_asset_pack.h"
        sha256 = "2180FE281AFF31C8688BCB290740F898CF7E032C90D97FFE679F535689A814F9"
    }
    c_pack_source = [ordered]@{
        relative_path = "$exportRelative\companion_visual_asset_pack.c"
        sha256 = "1EE7BD5DDB210A3C3F90ADB607BA317CF2F00127099B876C9DB5948C7A5D03A0"
    }
    c_pack_handoff = [ordered]@{
        relative_path = "$exportRelative\c-asset-pack-handoff.json"
        sha256 = "982B582FAEDDF956AF8557A9A333362A0D91DD7CA92FB3E0E7A37FC3D79F14D9"
    }
}

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string] $Path)

    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
}

function Resolve-WorkflowRoot {
    param([string] $Requested)

    $candidate = if (-not [string]::IsNullOrWhiteSpace($Requested)) {
        $Requested
    } elseif (-not [string]::IsNullOrWhiteSpace($env:AI_WORKFLOW_REPO)) {
        $env:AI_WORKFLOW_REPO
    } else {
        "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $candidate "docs\agent_quickstart.md") -PathType Leaf)) {
        $candidate = "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $candidate "docs\agent_quickstart.md") -PathType Leaf)) {
        throw "Canonical workflow repo with docs/agent_quickstart.md was not found."
    }
    return (Resolve-Path -LiteralPath $candidate).Path
}

function Get-Override {
    param(
        [hashtable] $Fixture,
        [string] $Group,
        [string] $Key,
        $Default
    )

    if ($Fixture.ContainsKey("overrides") -and
        $Fixture.overrides.ContainsKey($Group) -and
        $Fixture.overrides[$Group].ContainsKey($Key)) {
        return $Fixture.overrides[$Group][$Key]
    }
    return $Default
}

function Read-JsonFile {
    param([string] $Path)

    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Get-Readiness {
    param([string] $FixtureFile = "")

    $fixture = @{}
    if (-not [string]::IsNullOrWhiteSpace($FixtureFile)) {
        $resolvedFixture = if ([System.IO.Path]::IsPathRooted($FixtureFile)) {
            $FixtureFile
        } else {
            Join-Path $repoRoot $FixtureFile
        }
        if (-not (Test-Path -LiteralPath $resolvedFixture -PathType Leaf)) {
            throw "Fixture file missing: $FixtureFile"
        }
        $fixture = Get-Content -LiteralPath $resolvedFixture -Raw -Encoding UTF8 |
            ConvertFrom-Json -AsHashtable
        if ($fixture.ContainsKey("fixtures")) {
            if ([string]::IsNullOrWhiteSpace($FixtureId)) {
                throw "FixtureId is required for a fixture manifest."
            }
            $matches = @($fixture.fixtures | Where-Object { [string]$_.id -eq $FixtureId })
            if ($matches.Count -ne 1) {
                throw "FixtureId must resolve exactly once: $FixtureId"
            }
            $fixture = $matches[0]
        } elseif (-not [string]::IsNullOrWhiteSpace($FixtureId) -and
            [string]$fixture.id -ne $FixtureId) {
            throw "FixtureId does not match fixture document: $FixtureId"
        }
    }

    $failures = [System.Collections.Generic.List[string]]::new()
    $identities = [System.Collections.Generic.List[object]]::new()
    $resolvedPaths = @{}
    foreach ($entry in $fileSpecs.GetEnumerator()) {
        $key = [string]$entry.Key
        $relativePath = [string]$entry.Value.relative_path
        $fullPath = Join-Path $repoRoot $relativePath
        $resolvedPaths[$key] = $fullPath
        $actualExists = Test-Path -LiteralPath $fullPath -PathType Leaf
        $observedExists = [bool](Get-Override -Fixture $fixture -Group "file_exists" -Key $key -Default $actualExists)
        $actualHash = if ($actualExists) { Get-Sha256 -Path $fullPath } else { $null }
        $observedHash = Get-Override -Fixture $fixture -Group "sha256" -Key $key -Default $actualHash
        $match = $observedExists -and $observedHash -eq [string]$entry.Value.sha256
        $identities.Add([ordered]@{
            id = $key
            path = $relativePath.Replace("\", "/")
            expected_sha256 = [string]$entry.Value.sha256
            observed_sha256 = $observedHash
            exists = $observedExists
            match = $match
        })
        if (-not $observedExists) {
            $failures.Add("required page/artifact file missing: $key")
        } elseif ($observedHash -ne [string]$entry.Value.sha256) {
            $failures.Add("artifact SHA mismatch: $key")
        }
    }

    $requiredJsonKeys = @(
        "machine_result",
        "measured_diagnostic",
        "capture_manifest",
        "pointer_result",
        "c_pack_result",
        "visual_contract",
        "c_pack_manifest"
    )
    foreach ($key in $requiredJsonKeys) {
        if (-not (Test-Path -LiteralPath $resolvedPaths[$key] -PathType Leaf)) {
            throw "Cannot parse missing JSON artifact: $key"
        }
    }
    $machine = Read-JsonFile -Path $resolvedPaths.machine_result
    $diagnostic = Read-JsonFile -Path $resolvedPaths.measured_diagnostic
    $capture = Read-JsonFile -Path $resolvedPaths.capture_manifest
    $pointer = Read-JsonFile -Path $resolvedPaths.pointer_result
    $cPackResult = Read-JsonFile -Path $resolvedPaths.c_pack_result
    $visualContract = Read-JsonFile -Path $resolvedPaths.visual_contract
    $cPackManifest = Read-JsonFile -Path $resolvedPaths.c_pack_manifest

    $machineStatus = [string](Get-Override -Fixture $fixture -Group "json" -Key "machine_status" -Default $machine.status)
    $cPackStatus = [string](Get-Override -Fixture $fixture -Group "json" -Key "c_pack_status" -Default $cPackResult.status)
    if ($machineStatus -ne "PASS") {
        $failures.Add("machine status must be PASS")
    }
    if ($cPackStatus -ne "PASS") {
        $failures.Add("C-pack machine status must be PASS")
    }
    foreach ($property in $machine.checks.PSObject.Properties) {
        if ($property.Value -ne $true) {
            $failures.Add("machine check is not true: $($property.Name)")
        }
    }
    foreach ($property in $cPackResult.checks.PSObject.Properties) {
        if ($property.Value -ne $true) {
            $failures.Add("C-pack check is not true: $($property.Name)")
        }
    }
    foreach ($artifact in @(
        @("frames_bin_sha256", "frames_bin"),
        @("visual_contract_sha256", "visual_contract"),
        @("state_transitions_sha256", "state_transitions"),
        @("handoff_manifest_sha256", "handoff_manifest"),
        @("capture_manifest_sha256", "capture_manifest")
    )) {
        if ([string]$machine.artifacts.($artifact[0]) -ne [string]$fileSpecs[$artifact[1]].sha256) {
            $failures.Add("machine artifact binding drift: $($artifact[0])")
        }
    }
    if ([string]$machine.source.page_sha256 -ne [string]$fileSpecs.page.sha256) {
        $failures.Add("machine page binding drift")
    }
    if ($diagnostic.status -ne "PASS" -or $capture.status -ne "PASS" -or $pointer.status -ne "PASS") {
        $failures.Add("browser capture, pointer, or measured diagnostic status is not PASS")
    }
    if ($visualContract.frame_count -ne 17 -or
        $visualContract.format.width -ne 200 -or
        $visualContract.format.height -ne 200 -or
        $visualContract.format.frame_bytes -ne 5000 -or
        [string]$visualContract.combined_sha256 -ne [string]$fileSpecs.frames_bin.sha256) {
        $failures.Add("17-frame visual contract geometry or frames.bin binding drift")
    }
    if ($cPackManifest.status -ne "PASS" -or
        $cPackManifest.capacity.state_count -ne 17 -or
        $cPackManifest.capacity.packed_payload_bytes -gt 85000 -or
        $cPackManifest.default_off.default -ne 0) {
        $failures.Add("C-pack manifest status, capacity, or default-off contract drift")
    }
    foreach ($artifact in @(
        @("companion_visual_asset_pack.h", "c_pack_header"),
        @("companion_visual_asset_pack.c", "c_pack_source"),
        @("c-asset-pack-manifest.json", "c_pack_manifest"),
        @("c-asset-pack-handoff.json", "c_pack_handoff")
    )) {
        if ([string]$cPackResult.artifact_sha256.($artifact[0]) -ne [string]$fileSpecs[$artifact[1]].sha256) {
            $failures.Add("C-pack artifact binding drift: $($artifact[0])")
        }
    }

    $observedUrls = @(
        [string]$capture.source.url,
        [string]$pointer.url,
        [string]$diagnostic.source.url
    )
    $urlOverride = Get-Override -Fixture $fixture -Group "contract" -Key "url" -Default $reviewUrl
    if ($urlOverride -ne $reviewUrl -or @($observedUrls | Where-Object { $_ -ne $reviewUrl }).Count -ne 0) {
        $failures.Add("4173 review URL string drift")
    }

    $plannedPromptCount = [int](Get-Override -Fixture $fixture -Group "contract" -Key "prompt_instance_count" -Default $promptContract.instance_count)
    $buttons = @(Get-Override -Fixture $fixture -Group "contract" -Key "buttons" -Default $promptContract.buttons)
    $activePromptCount = if (Test-Path -LiteralPath $promptSentinelPath -PathType Leaf) { 1 } else { 0 }
    $activePromptCount = [int](Get-Override -Fixture $fixture -Group "contract" -Key "active_prompt_count" -Default $activePromptCount)
    if ($plannedPromptCount -ne 1 -or $activePromptCount -ne 0) {
        $failures.Add("duplicate prompt contract detected")
    }
    if (($buttons -join ",") -ne "通过,失败" -or @($buttons | Select-Object -Unique).Count -ne 2) {
        $failures.Add("prompt buttons must be the unique Chinese contract 通过,失败")
    }
    foreach ($path in @($ownerResultPath, $ownerRawPath, $ownerNotePath)) {
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            $failures.Add("owner result already exists and is immutable: $([System.IO.Path]::GetFileName($path))")
        }
    }

    $workflowRoot = Resolve-WorkflowRoot -Requested $WorkflowRepo
    $aiwPath = Join-Path $workflowRoot "scripts\aiw.ps1"
    if (-not (Test-Path -LiteralPath $aiwPath -PathType Leaf)) {
        $failures.Add("canonical aiw.ps1 is missing")
    }

    $runnerSource = Get-Content -LiteralPath $PSCommandPath -Raw -Encoding UTF8
    $checkOnlyMarker = 'if ($CheckOnly) {'
    $checkOnlyOffset = $runnerSource.IndexOf($checkOnlyMarker, [System.StringComparison]::Ordinal)
    $checkOnlyReturnOffset = if ($checkOnlyOffset -ge 0) {
        $runnerSource.IndexOf("    return", $checkOnlyOffset, [System.StringComparison]::Ordinal)
    } else {
        -1
    }
    $executeSideEffectOffsets = @(
        $runnerSource.IndexOf("Invoke-WebRequest", [Math]::Max(0, $checkOnlyReturnOffset), [System.StringComparison]::Ordinal),
        $runnerSource.IndexOf("Start-Process", [Math]::Max(0, $checkOnlyReturnOffset), [System.StringComparison]::Ordinal),
        $runnerSource.IndexOf("operator-prompt", [Math]::Max(0, $checkOnlyReturnOffset), [System.StringComparison]::Ordinal)
    ) | Where-Object { $_ -ge 0 }
    $firstExecuteSideEffectOffset = if ($executeSideEffectOffsets.Count -gt 0) {
        ($executeSideEffectOffsets | Measure-Object -Minimum).Minimum
    } else {
        -1
    }
    $checkOnlyStaticNoProcess = $checkOnlyOffset -ge 0 -and
        $checkOnlyReturnOffset -gt $checkOnlyOffset -and
        $firstExecuteSideEffectOffset -gt $checkOnlyReturnOffset
    $cleanupTokens = @(
        'if ($serverStarted -and $null -ne $serverProcess)',
        'if ($serverProcess.Id -ne $serverPid)',
        'Stop-Process -Id $serverPid -Force',
        '$serverProcess.WaitForExit(5000)',
        'Write-PromptFaultArtifact',
        'owner-review-fault-',
        'finally'
    )
    $missingCleanupTokens = @(
        $cleanupTokens | Where-Object { -not $runnerSource.Contains($_) }
    )
    $executeCleanupBounded = $missingCleanupTokens.Count -eq 0
    $checkOnlyProcessCount = [int](Get-Override -Fixture $fixture -Group "contract" -Key "checkonly_process_count" -Default 0)
    $executeCleanupBounded = [bool](Get-Override -Fixture $fixture -Group "contract" -Key "execute_cleanup_bounded" -Default $executeCleanupBounded)
    if (-not $checkOnlyStaticNoProcess -or $checkOnlyProcessCount -ne 0) {
        $failures.Add("CheckOnly process counter must remain zero behind an early return")
    }
    if (-not $executeCleanupBounded) {
        $failures.Add("Execute cleanup path must be bounded and exact-PID")
    }

    if ($failures.Count -gt 0) {
        $fixtureId = if ($fixture.ContainsKey("id")) { [string]$fixture.id } else { "live" }
        throw "READINESS_FAIL_CLOSED[$fixtureId]: $($failures -join '; ')"
    }

    return [pscustomobject][ordered]@{
        schema = "companion.browser-owner-review-readiness.v1"
        requirement = "COMP-REQ-471"
        status = "PASS_READY_FOR_OWNER_BROWSER_REVIEW_CHECKONLY_NO_EXECUTE"
        mode = "CheckOnly"
        default_off = $true
        fixture_id = if ($fixture.ContainsKey("id")) { [string]$fixture.id } else { $null }
        identities = @($identities)
        machine = [ordered]@{
            result_status = $machineStatus
            all_checks_true = $true
            c_pack_result_status = $cPackStatus
            c_pack_all_checks_true = $true
            frame_reconstruction = [string]$cPackResult.frame_reconstruction.result
            frame_count = [int]$visualContract.frame_count
        }
        url = [ordered]@{
            value = $reviewUrl
            string_match_only = $true
            network_checked = $false
            server_checked = $false
        }
        prompt_contract = $promptContract
        canonical_aiw = [ordered]@{
            path = [System.IO.Path]::GetRelativePath($workflowRoot, $aiwPath).Replace("\", "/")
            sha256 = Get-Sha256 -Path $aiwPath
            invoked = $false
        }
        lifecycle_static = [ordered]@{
            checkonly_guard_offset = $checkOnlyOffset
            checkonly_return_offset = $checkOnlyReturnOffset
            first_execute_side_effect_offset = $firstExecuteSideEffectOffset
            checkonly_returns_before_process_network_browser_prompt = $checkOnlyStaticNoProcess
            checkonly_process_count = $checkOnlyProcessCount
            execute_cleanup_bounded_exact_pid = $executeCleanupBounded
            cleanup_tokens_missing = $missingCleanupTokens
            self_started_server_only = $true
            preexisting_4173_preserved = $true
            prompt_failure_fault_artifact = $true
        }
        counters = [ordered]@{
            process = 0
            browser = 0
            popup = 0
            hardware = 0
            write = 0
            server_probe = 0
            network_request = 0
            owner_result = 0
        }
        future_execute_command = "pwsh -NoProfile -File .\tools\faraday_upper_art\supervise_companion_browser_owner_review_comp_req_471.ps1 -Execute -OwnerStartAcknowledged"
    }
}

function Write-PromptFaultArtifact {
    param(
        [Parameter(Mandatory = $true)]
        [System.Management.Automation.ErrorRecord] $ErrorRecord,
        [Parameter(Mandatory = $true)]
        [string] $Stage,
        [string] $RawText = "",
        [Parameter(Mandatory = $true)]
        [hashtable] $Cleanup,
        [bool] $ServerStarted = $false,
        [int] $ServerPid = 0
    )

    $successfulOwnerResultExists = Test-Path -LiteralPath $ownerResultPath -PathType Leaf
    $partialRawExists = Test-Path -LiteralPath $ownerRawPath -PathType Leaf
    $partialNoteExists = Test-Path -LiteralPath $ownerNotePath -PathType Leaf
    $partialRawText = if ($partialRawExists) {
        Get-Content -LiteralPath $ownerRawPath -Raw -Encoding UTF8
    } else {
        $RawText
    }
    $partialNoteText = if ($partialNoteExists) {
        Get-Content -LiteralPath $ownerNotePath -Raw -Encoding UTF8
    } else {
        ""
    }
    $faultName = "owner-review-fault-$((Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmmss-fff'))-$PID.json"
    $faultPath = Join-Path $validationDir $faultName
    $fault = [ordered]@{
        schema = "companion.browser-owner-review-fault.v1"
        requirement = "COMP-REQ-471"
        status = "FAULT_OPERATOR_PROMPT_OR_LIFECYCLE"
        stage = $Stage
        error = [ordered]@{
            message = $ErrorRecord.Exception.Message
            type = $ErrorRecord.Exception.GetType().FullName
            fully_qualified_error_id = $ErrorRecord.FullyQualifiedErrorId
        }
        partial = [ordered]@{
            raw_present = $partialRawExists -or -not [string]::IsNullOrEmpty($RawText)
            raw_text = $partialRawText
            raw_sha256 = if ($partialRawExists) { Get-Sha256 -Path $ownerRawPath } else { $null }
            note_present = $partialNoteExists
            note_text = $partialNoteText
            note_sha256 = if ($partialNoteExists) { Get-Sha256 -Path $ownerNotePath } else { $null }
        }
        cleanup = $Cleanup
        server = [ordered]@{
            started_by_this_execute = $ServerStarted
            pid = if ($ServerStarted) { $ServerPid } else { $null }
            preexisting_4173_preserved = -not $ServerStarted
        }
        successful_owner_result_preserved = $successfulOwnerResultExists
        partial_files_removed_after_fault_archive = [ordered]@{
            raw = $false
            note = $false
        }
        next_step = "Inspect this fault artifact, then retry only after machine identities still match. It does not alter machine PASS or create an owner verdict."
    }
    $fault | ConvertTo-Json -Depth 16 |
        Set-Content -LiteralPath $faultPath -Encoding utf8NoBOM

    if (-not $successfulOwnerResultExists) {
        if (Test-Path -LiteralPath $ownerRawPath -PathType Leaf) {
            Remove-Item -LiteralPath $ownerRawPath -Force
            $fault.partial_files_removed_after_fault_archive.raw = $true
        }
        if (Test-Path -LiteralPath $ownerNotePath -PathType Leaf) {
            Remove-Item -LiteralPath $ownerNotePath -Force
            $fault.partial_files_removed_after_fault_archive.note = $true
        }
        $fault | ConvertTo-Json -Depth 16 |
            Set-Content -LiteralPath $faultPath -Encoding utf8NoBOM
    }
    return $faultPath
}

if ($CheckOnly) {
    Get-Readiness -FixtureFile $FixturePath
    return
}

function Test-ReviewUrl {
    try {
        $response = Invoke-WebRequest -Uri $reviewUrl -UseBasicParsing -TimeoutSec 3
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

$null = Get-Readiness
$processCount = 0
$browserCount = 0
$popupCount = 0
$serverStarted = $false
$serverProcess = $null
$serverPid = 0
$promptSentinel = $null
$promptSentinelCreated = $false
$promptAttempted = $false
$rawText = ""
$ownerRecord = $null
$executionError = $null
$executionStage = "server_preflight"
$cleanup = @{
    prompt_sentinel_removed = $false
    server_cleanup_attempted = $false
    server_pid_exact_match = $false
    server_stop_requested = $false
    server_exited_bounded = $false
    preexisting_4173_preserved = $true
}

try {
    if (-not (Test-ReviewUrl)) {
        $portInUse = @(
            [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() |
                Where-Object { $_.Port -eq 4173 }
        ).Count -gt 0
        if ($portInUse) {
            throw "Port 4173 is occupied but the exact review URL is not reachable; refusing a second server."
        }
        $python = Get-Command python -CommandType Application -ErrorAction Stop
        $serverProcess = Start-Process -FilePath $python.Source `
            -ArgumentList @("-m", "http.server", "4173", "--bind", "127.0.0.1", "--directory", $repoRoot) `
            -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru
        $serverPid = $serverProcess.Id
        $serverStarted = $true
        $cleanup.preexisting_4173_preserved = $false
        $processCount += 1
        $deadline = [DateTime]::UtcNow.AddSeconds(12)
        while ([DateTime]::UtcNow -lt $deadline -and -not (Test-ReviewUrl)) {
            Start-Sleep -Milliseconds 250
        }
        if (-not (Test-ReviewUrl)) {
            throw "The unique 4173 server did not make the exact review URL reachable."
        }
    }

    $executionStage = "browser_open"
    $null = Start-Process -FilePath $reviewUrl -PassThru
    $processCount += 1
    $browserCount += 1
    Start-Sleep -Milliseconds 700
    $null = Get-Readiness

    $executionStage = "prompt_lock"
    $promptSentinel = [System.IO.File]::Open(
        $promptSentinelPath,
        [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None
    )
    $promptSentinelCreated = $true
    $workflowRoot = Resolve-WorkflowRoot -Requested $WorkflowRepo
    $aiwPath = Join-Path $workflowRoot "scripts\aiw.ps1"

    $executionStage = "operator_prompt"
    $promptAttempted = $true
    $processCount += 1
    $popupCount += 1
    $promptOutput = & pwsh -NoProfile -File $aiwPath operator-prompt `
        -Title $promptContract.title `
        -ProgressText $promptContract.progress_text `
        -ScopeText $promptContract.scope_text `
        -Message $promptContract.message `
        -ExpectedText $promptContract.expected_text `
        -ObservationLabel "备注（可留空；失败时请尽量写出页面、手势和可见问题）" `
        -ReviewStyle -Input -Buttons "通过,失败" `
        -OutputPath $ownerNotePath `
        -TimeoutSeconds $OperatorTimeoutSeconds `
        -Json
    $rawText = $promptOutput -join [Environment]::NewLine
    if (-not [string]::IsNullOrEmpty($rawText)) {
        Set-Content -LiteralPath $ownerRawPath -Value $rawText -Encoding utf8NoBOM
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Canonical aiw operator-prompt failed with exit code $LASTEXITCODE."
    }
    $promptResult = $rawText | ConvertFrom-Json
    if (@("通过", "失败") -notcontains [string]$promptResult.selected) {
        throw "Canonical prompt returned an invalid selection or timeout."
    }
    $note = if (Test-Path -LiteralPath $ownerNotePath -PathType Leaf) {
        Get-Content -LiteralPath $ownerNotePath -Raw -Encoding UTF8
    } else {
        [string]$promptResult.text
    }
    $accepted = [string]$promptResult.selected -eq "通过"
    $ownerRecord = [ordered]@{
        schema = "companion.browser-owner-review.v1"
        requirement = "COMP-REQ-471"
        status = if ($accepted) {
            "PASS_OWNER_BROWSER_EXPERIENCE_ACCEPTED"
        } else {
            "FAIL_OWNER_BROWSER_EXPERIENCE_RETURN_TO_ITERATION"
        }
        selected = [string]$promptResult.selected
        note = $note
        raw_result = [ordered]@{
            path = "$validationRelative/owner-review.raw.json"
            sha256 = Get-Sha256 -Path $ownerRawPath
        }
        note_artifact = [ordered]@{
            path = "$validationRelative/owner-review.note.txt"
            sha256 = if (Test-Path -LiteralPath $ownerNotePath -PathType Leaf) {
                Get-Sha256 -Path $ownerNotePath
            } else {
                $null
            }
        }
        machine_result = [ordered]@{
            path = "$validationRelative/machine-result.json"
            sha256 = [string]$fileSpecs.machine_result.sha256
            status_preserved = "PASS"
        }
        page = [ordered]@{
            path = $pageRelative.Replace("\", "/")
            sha256 = [string]$fileSpecs.page.sha256
            url = $reviewUrl
        }
        prompt_contract = $promptContract
        execution = [ordered]@{
            server_started_by_this_execute = $serverStarted
            server_pid = if ($serverStarted) { $serverPid } else { $null }
            preexisting_4173_preserved = -not $serverStarted
            browser_opened = $true
            canonical_prompt_count = 1
            process_count = $processCount
            browser_count = $browserCount
            popup_count = $popupCount
            hardware_count = 0
        }
        next_step = if ($accepted) {
            "Preserve this accepted browser behavior as a regression contract."
        } else {
            "Return to upper browser/art iteration; do not alter the existing machine PASS."
        }
    }
} catch {
    $executionError = $_
} finally {
    try {
        if ($null -ne $promptSentinel) {
            $promptSentinel.Dispose()
        }
        if ($promptSentinelCreated -and
            (Test-Path -LiteralPath $promptSentinelPath -PathType Leaf)) {
            Remove-Item -LiteralPath $promptSentinelPath -Force
            $cleanup.prompt_sentinel_removed = $true
        }
    } catch {
        if ($null -eq $executionError) {
            $executionStage = "prompt_lock_cleanup"
            $executionError = $_
        }
    }

    try {
        if ($serverStarted -and $null -ne $serverProcess) {
            $cleanup.server_cleanup_attempted = $true
            if ($serverProcess.Id -ne $serverPid) {
                throw "Self-started 4173 server PID identity changed before cleanup."
            }
            $cleanup.server_pid_exact_match = $true
            if (-not $serverProcess.HasExited) {
                Stop-Process -Id $serverPid -Force
                $cleanup.server_stop_requested = $true
            }
            $cleanup.server_exited_bounded = $serverProcess.WaitForExit(5000)
            if (-not $cleanup.server_exited_bounded) {
                throw "Self-started 4173 server did not exit within 5000 ms."
            }
        }
    } catch {
        if ($null -eq $executionError) {
            $executionStage = "server_cleanup"
            $executionError = $_
        }
    }
}

if ($null -ne $executionError) {
    if ($promptAttempted -or $executionStage -match "cleanup") {
        try {
            $faultPath = Write-PromptFaultArtifact `
                -ErrorRecord $executionError `
                -Stage $executionStage `
                -RawText $rawText `
                -Cleanup $cleanup `
                -ServerStarted $serverStarted `
                -ServerPid $serverPid
            Write-Error "Owner-review fault retained at $faultPath" -ErrorAction Continue
        } catch {
            Write-Error "Owner-review fault artifact write failed: $($_.Exception.Message)" -ErrorAction Continue
        }
    }
    throw $executionError
}

$ownerRecord.execution["cleanup"] = $cleanup
$ownerRecord | ConvertTo-Json -Depth 16 |
    Set-Content -LiteralPath $ownerResultPath -Encoding utf8NoBOM
[pscustomobject]$ownerRecord
