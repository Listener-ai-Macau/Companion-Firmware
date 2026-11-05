#requires -Version 7.0
[CmdletBinding()]
param(
    [switch]$DryRun,
    [ValidateRange(1, 840)]
    [int]$TimeoutSeconds = 840,
    [string]$WorkflowRepo = "",
    [string]$ResultPath = "docs\\validation\\companion-v9-expression-rig-expression-atlas-owner-review-20260718.json",
    [string]$NotePath = "docs\\validation\\companion-v9-expression-rig-expression-atlas-owner-review-20260718.note.txt",
    [string]$SummaryPath = "docs\\validation\\companion-v9-expression-rig-expression-atlas-owner-review-summary-20260718.json"
)

$ErrorActionPreference = "Stop"

function Resolve-WorkflowRepo {
    param([string]$RequestedPath)

    foreach ($candidate in @($RequestedPath, $env:AI_WORKFLOW_REPO, "C:\\Users\\Billy\\Desktop\\Denzic\\ai-collaboration-workflow") |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) {
        $resolved = [System.IO.Path]::GetFullPath($candidate)
        if (Test-Path -LiteralPath (Join-Path $resolved "docs\\agent_quickstart.md")) {
            return $resolved
        }
    }
    throw "Unable to resolve AI workflow repository with docs\\agent_quickstart.md."
}

function Require-Equal {
    param($Actual, $Expected, [string]$Description)
    if ($Actual -ne $Expected) {
        throw "$Description expected '$Expected' but found '$Actual'."
    }
}

function Require-Property {
    param($Object, [string]$Name, [string]$Context)
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property -or $null -eq $property.Value) {
        throw "$Context is missing required property '$Name'."
    }
    return $property.Value
}

function Write-JsonFile {
    param($Value, [string]$Path)
    $directory = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($directory)) {
        New-Item -ItemType Directory -Force -Path $directory | Out-Null
    }
    $Value | ConvertTo-Json -Depth 16 | Set-Content -LiteralPath $Path -Encoding utf8
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

$machinePath = Join-Path $repoRoot "docs\\validation\\companion-v9-expression-rig-expression-atlas-machine-20260718.json"
$previewPath = Join-Path $repoRoot "docs\\validation\\companion-v9-expression-rig-expression-atlas-preview-20260718.json"
$atlasContractPath = Join-Path $repoRoot "docs\\art\\iterations\\companion-pet-expression-v9-rig-v1\\candidate\\expression-atlas-v1.json"
$reviewPagePath = Join-Path $repoRoot "docs\\art\\iterations\\companion-pet-expression-v9-rig-v1\\candidate\\rendered-200x200\\v9-expression-rig-expression-atlas-owner-review.html"
$desktopScreenshotPath = Join-Path $repoRoot "docs\\validation\\companion-v9-expression-rig-expression-atlas-browser-desktop-20260718.png"
$narrowScreenshotPath = Join-Path $repoRoot "docs\\validation\\companion-v9-expression-rig-expression-atlas-browser-narrow-20260718.png"
$sourcePath = Join-Path $repoRoot "docs\\art\\iterations\\companion-pet-expression-v9\\generated_pet_expression_sheet_v9_candidate.png"
$protectedAcceptancePath = Join-Path $repoRoot "docs\\validation\\companion-pet-special-system-owner-acceptance-20260717.json"
foreach ($path in @($machinePath, $previewPath, $atlasContractPath, $reviewPagePath, $desktopScreenshotPath,
        $narrowScreenshotPath, $sourcePath, $protectedAcceptancePath)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required atlas review evidence is missing: $path"
    }
}

$machine = Get-Content -LiteralPath $machinePath -Raw | ConvertFrom-Json
$preview = Get-Content -LiteralPath $previewPath -Raw | ConvertFrom-Json
$lockedSourceSha256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
$protectedAcceptanceSha256 = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"

Require-Equal (Require-Property $machine "status" "atlas machine report") "PASS_EXPRESSION_ATLAS_MACHINE" "Expression atlas machine closure"
Require-Equal (Require-Property $preview "status" "atlas preview report") "PASS_DYNAMIC_COMPONENT_PREVIEW_READY" "Expression atlas preview render"
Require-Equal (Require-Property $preview "preview_scope" "atlas preview report") "expression_atlas" "Expression atlas scope"
Require-Equal (Require-Property $machine "runtime_resource_activated" "atlas machine report") $false "Device runtime activation"
Require-Equal (Require-Property $preview "runtime_resource_activated" "atlas preview report") $false "Preview runtime activation"
Require-Equal (Require-Property $machine "charging_error" "atlas machine report") "fail_closed_no_registered_components" "Charging/error fail-closed proof"
Require-Equal (Require-Property $machine "source_sha256" "atlas machine report") $lockedSourceSha256 "Machine source hash"
Require-Equal (Require-Property $preview "source_sha256" "atlas preview report") $lockedSourceSha256 "Preview source hash"
Require-Equal ([int](Require-Property $machine "family_count" "atlas machine report")) 5 "Expression atlas family count"
if ([int](Require-Property $machine "distinct_hold_pose_count" "atlas machine report") -lt 8) {
    throw "Expression atlas did not prove enough distinct source-component hold poses."
}
if (@(Require-Property $machine "stories" "atlas machine report").Count -ne 12) {
    throw "Expression atlas did not prove all twelve registered stories."
}

$actualSourceSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourcePath).Hash.ToUpperInvariant()
$actualProtectedSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $protectedAcceptancePath).Hash.ToUpperInvariant()
$actualReviewPageSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $reviewPagePath).Hash.ToUpperInvariant()
$actualAtlasContractSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $atlasContractPath).Hash.ToUpperInvariant()
Require-Equal $actualSourceSha256 $lockedSourceSha256 "Frozen v9 source hash"
Require-Equal $actualProtectedSha256 $protectedAcceptanceSha256 "Protected prior owner-acceptance hash"
Require-Equal $actualReviewPageSha256 (Require-Property $preview "owner_review_page_sha256" "atlas preview report") "Owner review page hash"
Require-Equal $actualAtlasContractSha256 (Require-Property $machine "atlas_contract_sha256" "atlas machine report") "Expression atlas contract hash"

$resultAbsolutePath = Join-Path $repoRoot $ResultPath
$noteAbsolutePath = Join-Path $repoRoot $NotePath
$summaryAbsolutePath = Join-Path $repoRoot $SummaryPath
$summary = [ordered]@{
    schema = "companion.v9_expression_rig_expression_atlas_owner_review_summary.v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    dry_run = [bool]$DryRun
    result_path = $ResultPath
    note_path = $NotePath
    review_page_path = (Resolve-Path -LiteralPath $reviewPagePath).Path
    review_page_sha256 = $actualReviewPageSha256
    desktop_screenshot_path = $desktopScreenshotPath
    desktop_screenshot_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $desktopScreenshotPath).Hash.ToUpperInvariant()
    narrow_screenshot_path = $narrowScreenshotPath
    narrow_screenshot_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $narrowScreenshotPath).Hash.ToUpperInvariant()
    machine_report_path = $machinePath
    machine_report_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $machinePath).Hash.ToUpperInvariant()
    preview_report_path = $previewPath
    preview_report_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $previewPath).Hash.ToUpperInvariant()
    atlas_contract_path = $atlasContractPath
    atlas_contract_sha256 = $actualAtlasContractSha256
    source_sha256 = $actualSourceSha256
    protected_prior_owner_acceptance_sha256 = $actualProtectedSha256
    runtime_resource_activated = $false
    charging_error = "fail_closed_no_registered_components"
    baseline_promotion = "forbidden"
    device_flash = "forbidden"
    goal_complete = $false
    prompt_style = "aiw_operator_prompt_v1"
}

if ($DryRun) {
    $summary.status = "READY_FOR_OWNER_EXPRESSION_ATLAS_REVIEW"
    $summary.selection = ""
    $summary.selection_text = ""
    $summary.operator_note_present = $false
    Write-JsonFile $summary $summaryAbsolutePath
    Write-Output ("READY_FOR_OWNER_EXPRESSION_ATLAS_REVIEW: {0}" -f $reviewPagePath)
    exit 0
}

Start-Process -FilePath $reviewPagePath
Start-Sleep -Seconds 3

$message = @"
请验收刚打开的 Companion v9 全部已登记表情图谱。首屏应同时看到 12 个 V9 状态，分为日常灵动、好奇回应、亲昵互动、专注活动、休息五类；选择任一项后，下面的大脸只循环该状态自己的组件动画。

重点看：它是否比之前的一张默认脸更完整、更紧凑，状态之间是否有清楚的来源姿态区分；Daily 四向是否被正确理解为日常注意力微动而非假装成四个大情绪；是否仍保持 V9 身份、组件来源和自然的准备、回应、停留、恢复。未获准的情绪不能被假装补上，充电和错误保持 fail-closed。
"@
$expected = @"
通过：现有 V9 的完整情绪图谱和单状态动态播放器可以作为后续屏幕 1:1 预览基线。
需修改：请备注具体家族或状态，以及希望新增或加强的情绪、姿态、组件或页面呈现；缺少的情绪会进入版本化 V9 参考生图扩展，不会手绘或替换锁定源图。
"@

$promptJsonText = & pwsh -NoProfile -File $aiw operator-prompt `
    -Title "Companion v9 全部表情图谱验收" `
    -ProgressText "1/1" `
    -ScopeText "电脑侧 V9 组件图谱；12 状态；所选状态独立循环；runtime inactive" `
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

$summary.selection = $selection
$summary.selection_text = $selectionText
$summary.operator_note_present = (Test-Path -LiteralPath $noteAbsolutePath) -and ((Get-Item -LiteralPath $noteAbsolutePath).Length -gt 0)
switch ($selection) {
    "通过" { $summary.status = "PASS_OWNER_EXPRESSION_ATLAS_REVIEW" }
    "需修改" { $summary.status = "FAIL_OWNER_EXPRESSION_ATLAS_REVIEW" }
    "跳过" { $summary.status = "SKIPPED_BY_OWNER" }
    "中止" { $summary.status = "ABORTED_BY_OWNER" }
    "Timeout" { $summary.status = "NO_OWNER_SELECTION_TIMEOUT" }
    default { $summary.status = "NO_OWNER_APPROVAL" }
}
$summary.goal_completion_candidate = ($summary.status -eq "PASS_OWNER_EXPRESSION_ATLAS_REVIEW")
Write-JsonFile $summary $summaryAbsolutePath

Write-Output ("{0}: selection={1}" -f $summary.status, $selection)
exit 0
