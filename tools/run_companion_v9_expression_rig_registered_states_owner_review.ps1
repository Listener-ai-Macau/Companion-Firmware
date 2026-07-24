#requires -Version 7.0
[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$RecoverExistingResult,
    [ValidateRange(1, 840)]
    [int]$TimeoutSeconds = 840,
    [string]$WorkflowRepo = "",
    [string]$ResultPath = "docs\\validation\\companion-v9-expression-rig-registered-states-owner-review-20260718.json",
    [string]$NotePath = "docs\\validation\\companion-v9-expression-rig-registered-states-owner-review-20260718.note.txt",
    [string]$SummaryPath = "docs\\validation\\companion-v9-expression-rig-registered-states-owner-review-summary-20260718.json"
)

$ErrorActionPreference = "Stop"

function Resolve-WorkflowRepo {
    param([string]$RequestedPath)

    $candidates = @(
        $RequestedPath,
        $env:AI_WORKFLOW_REPO,
        "C:\\Users\\Billy\\Desktop\\Denzic\\ai-collaboration-workflow"
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

    foreach ($candidate in $candidates) {
        $resolved = [System.IO.Path]::GetFullPath($candidate)
        if (Test-Path -LiteralPath (Join-Path $resolved "docs\\agent_quickstart.md")) {
            return $resolved
        }
    }

    throw "Unable to resolve AI workflow repository with docs\\agent_quickstart.md."
}

function Write-JsonFile {
    param(
        [Parameter(Mandatory = $true)]$Value,
        [Parameter(Mandatory = $true)][string]$Path
    )

    $directory = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($directory)) {
        New-Item -ItemType Directory -Force -Path $directory | Out-Null
    }
    $Value | ConvertTo-Json -Depth 16 | Set-Content -LiteralPath $Path -Encoding utf8
}

function Get-RequiredProperty {
    param(
        [Parameter(Mandatory = $true)]$Object,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Context
    )

    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property -or $null -eq $property.Value) {
        throw "$Context is missing required property '$Name'."
    }
    return $property.Value
}

function Assert-Equal {
    param(
        [Parameter(Mandatory = $true)]$Actual,
        [Parameter(Mandatory = $true)]$Expected,
        [Parameter(Mandatory = $true)][string]$Description
    )

    if ($Actual -ne $Expected) {
        throw "$Description expected '$Expected' but found '$Actual'."
    }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot
$workflowRoot = Resolve-WorkflowRepo -RequestedPath $WorkflowRepo
$aiw = Join-Path $workflowRoot "scripts\\aiw.ps1"
$pwshCheck = Join-Path $workflowRoot "scripts\\verify_pwsh7.ps1"

& pwsh -NoProfile -File $pwshCheck
if ($LASTEXITCODE -ne 0) {
    throw "PowerShell 7 verification failed."
}

$machineReportPath = Join-Path $repoRoot "docs\\validation\\companion-v9-expression-rig-registered-states-machine-20260718.json"
$previewReportPath = Join-Path $repoRoot "docs\\validation\\companion-v9-expression-rig-registered-states-preview-20260718.json"
$reviewPagePath = Join-Path $repoRoot "docs\\art\\iterations\\companion-pet-expression-v9-rig-v1\\candidate\\rendered-200x200\\v9-expression-rig-registered-states-owner-review.html"
$sourcePath = Join-Path $repoRoot "docs\\art\\iterations\\companion-pet-expression-v9\\generated_pet_expression_sheet_v9_candidate.png"
$protectedAcceptancePath = Join-Path $repoRoot "docs\\validation\\companion-pet-special-system-owner-acceptance-20260717.json"

foreach ($path in @($machineReportPath, $previewReportPath, $reviewPagePath, $sourcePath, $protectedAcceptancePath)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required review evidence is missing: $path"
    }
}

$machine = Get-Content -LiteralPath $machineReportPath -Raw | ConvertFrom-Json
$preview = Get-Content -LiteralPath $previewReportPath -Raw | ConvertFrom-Json
$lockedSourceSha256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
$protectedAcceptanceSha256 = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"

Assert-Equal (Get-RequiredProperty $machine "status" "machine report") "PASS_REGISTERED_STATE_PREVIEW_MACHINE" "Registered-state machine closure"
Assert-Equal (Get-RequiredProperty $preview "status" "preview report") "PASS_DYNAMIC_COMPONENT_PREVIEW_READY" "Registered-state preview render"
Assert-Equal (Get-RequiredProperty $preview "preview_scope" "preview report") "registered_states" "Preview scope"
Assert-Equal (Get-RequiredProperty $machine "runtime_resource_activated" "machine report") $false "Device runtime activation"
Assert-Equal (Get-RequiredProperty $preview "runtime_resource_activated" "preview report") $false "Preview runtime activation"
Assert-Equal (Get-RequiredProperty $machine "charging_error" "machine report") "fail_closed_no_registered_components" "Charging/error fail-closed proof"
Assert-Equal (Get-RequiredProperty $machine "source_sha256" "machine report") $lockedSourceSha256 "Machine source hash"
Assert-Equal (Get-RequiredProperty $preview "source_sha256" "preview report") $lockedSourceSha256 "Preview source hash"

$actualSourceSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourcePath).Hash.ToUpperInvariant()
$actualProtectedSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $protectedAcceptancePath).Hash.ToUpperInvariant()
$actualReviewPageSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $reviewPagePath).Hash.ToUpperInvariant()
Assert-Equal $actualSourceSha256 $lockedSourceSha256 "Frozen v9 source hash"
Assert-Equal $actualProtectedSha256 $protectedAcceptanceSha256 "Protected prior owner-acceptance hash"
Assert-Equal (Get-RequiredProperty $preview "owner_review_page_sha256" "preview report") $actualReviewPageSha256 "Owner review page hash"

$machineReportSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $machineReportPath).Hash.ToUpperInvariant()
$previewReportSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $previewReportPath).Hash.ToUpperInvariant()
$scoreContractPath = Join-Path $repoRoot (Get-RequiredProperty $machine "score_contract" "machine report")
if (-not (Test-Path -LiteralPath $scoreContractPath)) {
    throw "Score contract is missing: $scoreContractPath"
}
$scoreContractSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $scoreContractPath).Hash.ToUpperInvariant()
Assert-Equal (Get-RequiredProperty $machine "score_contract_sha256" "machine report") $scoreContractSha256 "Score contract hash"

$resultAbsolutePath = Join-Path $repoRoot $ResultPath
$noteAbsolutePath = Join-Path $repoRoot $NotePath
$summaryAbsolutePath = Join-Path $repoRoot $SummaryPath

$summary = [ordered]@{
    schema = "companion.v9_expression_rig_registered_state_preview_owner_review_summary.v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    dry_run = [bool]$DryRun
    result_path = $ResultPath
    note_path = $NotePath
    review_page_path = (Resolve-Path -LiteralPath $reviewPagePath).Path
    review_page_sha256 = $actualReviewPageSha256
    machine_report_path = $machineReportPath
    machine_report_sha256 = $machineReportSha256
    preview_report_path = $previewReportPath
    preview_report_sha256 = $previewReportSha256
    score_contract_path = $scoreContractPath
    score_contract_sha256 = $scoreContractSha256
    source_path = $sourcePath
    source_sha256 = $actualSourceSha256
    protected_prior_owner_acceptance_path = $protectedAcceptancePath
    protected_prior_owner_acceptance_sha256 = $actualProtectedSha256
    runtime_active = $false
    charging_error_fail_closed = $true
    baseline_promotion = "forbidden"
    device_flash = "forbidden"
    goal_complete = $false
    prompt_style = "aiw_operator_prompt_v1"
    recovered_existing_result = [bool]$RecoverExistingResult
}

if ($DryRun) {
    $summary.status = "READY_FOR_OWNER_BROWSER_REVIEW"
    $summary.selection = ""
    $summary.selection_text = ""
    $summary.operator_note_present = $false
    Write-JsonFile -Value $summary -Path $summaryAbsolutePath
    Write-Output ("READY_FOR_OWNER_BROWSER_REVIEW: {0}" -f $reviewPagePath)
    exit 0
}

if ($RecoverExistingResult) {
    if (-not (Test-Path -LiteralPath $resultAbsolutePath)) {
        throw "Cannot recover a missing canonical operator result: $resultAbsolutePath"
    }
    $promptJsonText = Get-Content -LiteralPath $resultAbsolutePath -Raw
} else {
    Start-Process -FilePath $reviewPagePath
    Start-Sleep -Seconds 3

    $message = @"
请在刚打开的浏览器页面验收 v9 已登记状态动态预览。逐一点击 8 个状态；每次只循环当前选择的一个状态，不会自动轮播其他表情，也不会写入设备。

重点看：v9 角色身份是否稳定；动作是否像有意图的状态反应而不是随机抖动；眼神/高光先导、眉鼻嘴腮点和挂件随后回应、停留、恢复是否自然；是否仍完全由同一角色的来源组件组合，而非整脸换图、程序绘制或 legacy 美术。
"@
$expected = @"
通过：8 个状态的浏览器动态预览可以作为后续屏幕 1:1 引擎验收基线。
需修改：请在备注中写明具体状态、阶段和组件，以及哪里显得太小、奇怪、随机或不自然。
"@

    $promptJsonText = & pwsh -NoProfile -File $aiw operator-prompt `
        -Title "Companion v9 已登记状态动态预览验收" `
        -ProgressText "1/1" `
        -ScopeText "电脑侧组件 Rig；只循环当前选择状态；runtime inactive" `
        -Message $message `
        -ExpectedText $expected `
        -Input `
        -ReviewStyle `
        -Buttons "通过,需修改,跳过,中止" `
        -OutputPath $noteAbsolutePath `
        -TimeoutSeconds $TimeoutSeconds `
        -Json
    if ($LASTEXITCODE -ne 0) {
        throw "Canonical aiw operator-prompt failed."
    }

    $resultDirectory = Split-Path -Parent $resultAbsolutePath
    if (-not [string]::IsNullOrWhiteSpace($resultDirectory)) {
        New-Item -ItemType Directory -Force -Path $resultDirectory | Out-Null
    }
    Set-Content -LiteralPath $resultAbsolutePath -Value $promptJsonText -Encoding utf8
}
$selection = ""
$selectionText = ""
try {
    $promptResult = $promptJsonText | ConvertFrom-Json
    $selection = [string]$promptResult.selected
    if ([string]::IsNullOrWhiteSpace($selection)) {
        $selection = [string]$promptResult.selection
    }
    $selectionText = [string]$promptResult.text
} catch {
    throw "Canonical aiw operator-prompt did not return valid JSON: $($_.Exception.Message)"
}

$notePresent = (Test-Path -LiteralPath $noteAbsolutePath) -and ((Get-Item -LiteralPath $noteAbsolutePath).Length -gt 0)
$summary.selection = $selection
$summary.selection_text = $selectionText
$summary.operator_note_present = $notePresent
switch ($selection) {
    "通过" { $summary.status = "PASS_OWNER_BROWSER_REVIEW" }
    "需修改" { $summary.status = "FAIL_OWNER_BROWSER_REVIEW" }
    "跳过" { $summary.status = "SKIPPED_BY_OWNER" }
    "中止" { $summary.status = "ABORTED_BY_OWNER" }
    "Timeout" { $summary.status = "NO_OWNER_SELECTION_TIMEOUT" }
    default { $summary.status = "NO_OWNER_APPROVAL" }
}
$summary.goal_completion_candidate = ($summary.status -eq "PASS_OWNER_BROWSER_REVIEW")
Write-JsonFile -Value $summary -Path $summaryAbsolutePath

Write-Output ("{0}: selection={1}" -f $summary.status, $selection)
exit 0
