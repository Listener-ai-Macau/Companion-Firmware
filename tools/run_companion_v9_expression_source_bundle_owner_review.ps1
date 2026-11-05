#requires -Version 7.0
[CmdletBinding()]
param(
    [switch]$DryRun,
    [ValidateRange(1, 840)]
    [int]$TimeoutSeconds = 840,
    [string]$WorkflowRepo = "",
    [string]$ResultPath = "docs\validation\companion-v9-expression-source-bundle-owner-art-review-20260718.json",
    [string]$NotePath = "docs\validation\companion-v9-expression-source-bundle-owner-art-review-20260718.note.txt",
    [string]$SummaryPath = "docs\validation\companion-v9-expression-source-bundle-owner-art-review-summary-20260718.json"
)

$ErrorActionPreference = "Stop"

function Resolve-WorkflowRepo {
    param([string]$RequestedPath)
    foreach ($candidate in @($RequestedPath, $env:AI_WORKFLOW_REPO, "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow") |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) {
        $resolved = [System.IO.Path]::GetFullPath($candidate)
        if (Test-Path -LiteralPath (Join-Path $resolved "docs\agent_quickstart.md")) { return $resolved }
    }
    throw "Unable to resolve AI workflow repository with docs\agent_quickstart.md."
}

function Require-Equal {
    param($Actual, $Expected, [string]$Description)
    if ($Actual -ne $Expected) { throw "$Description expected '$Expected' but found '$Actual'." }
}

function Write-JsonFile {
    param($Value, [string]$Path)
    $directory = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($directory)) {
        New-Item -ItemType Directory -Force -Path $directory | Out-Null
    }
    $Value | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $Path -Encoding utf8
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot
$workflowRoot = Resolve-WorkflowRepo -RequestedPath $WorkflowRepo
$aiw = Join-Path $workflowRoot "scripts\aiw.ps1"
& pwsh -NoProfile -File (Join-Path $workflowRoot "scripts\verify_pwsh7.ps1")
if ($LASTEXITCODE -ne 0) { throw "PowerShell 7 verification failed." }

$lockedSource = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9\generated_pet_expression_sheet_v9_candidate.png"
$dailyCandidate = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-extension-v7-daily-direction-strip\generated_pet_expression_extension_v7_daily_direction_strip_candidate.png"
$emotionCandidate = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-extension-v8-emotion-anchor-panel\generated_pet_expression_extension_v8_emotion_anchor_panel_candidate.png"
$dailyRequestPath = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-extension-v7-daily-direction-strip\generation-request.json"
$emotionRequestPath = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-extension-v8-emotion-anchor-panel\generation-request.json"
$bundleManifestPath = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-extension-v8-emotion-anchor-panel\source-bundle-manifest.json"
$bundleMachinePath = Join-Path $repoRoot "docs\validation\companion-v9-expression-source-bundle-machine-20260718.json"
$lineagePath = Join-Path $repoRoot "docs\validation\companion-v9-art-lineage-machine-20260718.json"
$protectedAcceptance = Join-Path $repoRoot "docs\validation\companion-pet-special-system-owner-acceptance-20260717.json"
foreach ($path in @($lockedSource, $dailyCandidate, $emotionCandidate, $dailyRequestPath, $emotionRequestPath,
        $bundleManifestPath, $bundleMachinePath, $lineagePath, $protectedAcceptance)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing complete source-bundle review evidence: $path" }
}

$lockedHash = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
$protectedHash = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"
$dailyRequest = Get-Content -LiteralPath $dailyRequestPath -Raw | ConvertFrom-Json
$emotionRequest = Get-Content -LiteralPath $emotionRequestPath -Raw | ConvertFrom-Json
$manifest = Get-Content -LiteralPath $bundleManifestPath -Raw | ConvertFrom-Json
$bundleMachine = Get-Content -LiteralPath $bundleMachinePath -Raw | ConvertFrom-Json
$lineage = Get-Content -LiteralPath $lineagePath -Raw | ConvertFrom-Json
Require-Equal $lineage.status "PASS_ART_LINEAGE" "Art lineage machine closure"
Require-Equal $bundleMachine.status "PASS_COMPLETE_EXPRESSION_SOURCE_BUNDLE_GATE" "Complete source-bundle machine closure"
Require-Equal $manifest.status "MACHINE_COMPLETE_SOURCE_BUNDLE_PASS_PENDING_OWNER_REVIEW" "Source-bundle manifest state"
Require-Equal $dailyRequest.status "MACHINE_COMPLETE_SOURCE_BUNDLE_PASS_PENDING_OWNER_REVIEW_V7_20260718" "V7 Daily request state"
Require-Equal $emotionRequest.status "MACHINE_COMPLETE_SOURCE_BUNDLE_PASS_PENDING_OWNER_REVIEW_V8_20260718" "V8 emotion request state"
Require-Equal $dailyRequest.generated_output.status "machine_complete_source_bundle_pass_pending_owner_review" "V7 output state"
Require-Equal $emotionRequest.generated_output.status "machine_complete_source_bundle_pass_pending_owner_review" "V8 output state"
Require-Equal (Get-FileHash -Algorithm SHA256 -LiteralPath $lockedSource).Hash.ToUpperInvariant() $lockedHash "Locked V9 source hash"
Require-Equal (Get-FileHash -Algorithm SHA256 -LiteralPath $protectedAcceptance).Hash.ToUpperInvariant() $protectedHash "Protected prior acceptance hash"
Require-Equal (Get-FileHash -Algorithm SHA256 -LiteralPath $dailyCandidate).Hash.ToUpperInvariant() $dailyRequest.generated_output.sha256 "V7 Daily candidate hash"
Require-Equal (Get-FileHash -Algorithm SHA256 -LiteralPath $emotionCandidate).Hash.ToUpperInvariant() $emotionRequest.generated_output.sha256 "V8 emotion candidate hash"

$resultAbsolutePath = Join-Path $repoRoot $ResultPath
$noteAbsolutePath = Join-Path $repoRoot $NotePath
$summaryAbsolutePath = Join-Path $repoRoot $SummaryPath
$summary = [ordered]@{
    schema = "companion.v9_expression_source_bundle_owner_art_review_summary.v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    dry_run = [bool]$DryRun
    locked_v9_sha256 = $lockedHash
    daily_source_path = $dailyCandidate
    daily_source_sha256 = $dailyRequest.generated_output.sha256
    emotion_source_path = $emotionCandidate
    emotion_source_sha256 = $emotionRequest.generated_output.sha256
    bundle_manifest_path = $bundleManifestPath
    bundle_machine_report_path = $bundleMachinePath
    lineage_report_path = $lineagePath
    protected_prior_owner_acceptance_sha256 = $protectedHash
    runtime_resource_activated = $false
    component_export = "forbidden_pending_owner_art_review"
    full_face_source_card_playback = "forbidden"
    goal_complete = $false
    prompt_style = "aiw_operator_prompt_v1"
}
if ($DryRun) {
    $summary.status = "READY_FOR_OWNER_COMPLETE_EXPRESSION_SOURCE_BUNDLE_REVIEW"
    Write-JsonFile $summary $summaryAbsolutePath
    Write-Output "READY_FOR_OWNER_COMPLETE_EXPRESSION_SOURCE_BUNDLE_REVIEW: $dailyCandidate; $emotionCandidate"
    exit 0
}

Start-Process -FilePath $dailyCandidate
Start-Sleep -Milliseconds 700
Start-Process -FilePath $emotionCandidate
Start-Sleep -Seconds 2
$message = @"
请验收刚打开的 V9 完整动态美术源包：第一张是日常注意力左/右/上/下，第二张是好奇、警觉、喜悦、亲昵、记录、聆听、菜单思考、无月亮休息。它们是同一角色的静态组件来源，不是运行时整脸轮播；所有机器门槛已通过，后续才会从这些图拆眼睛/高光、眉、鼻嘴、腮点和挂件做 entry-hold-settle 动态。

重点看：12 个状态是否仍是同一个 V9 角色和同一种眼型；日常四向的高光方向是否清楚自然；八种情绪是否真的不同且不奇怪；休息是否没有月亮、Z 或额外顶端装饰。通过只授权后续组件导出和动态预览，绝不授权整脸贴图播放、runtime 激活、充电/错误借脸。
"@
$expected = @"
通过：允许仅从这两张已登记源图拆已批准组件，做状态驱动的 entry-hold-settle 动态预览；仍保持 runtime inactive，充电/错误 fail-closed。
需修改：两张源图仅保留为拒绝证据；不得导出组件、不得作为新生图参考，下一轮仍只引用锁定 V9 母图。
"@
$promptJsonText = & pwsh -NoProfile -File $aiw operator-prompt `
    -Title "Companion V9 完整动态美术源包验收" `
    -ProgressText "1/1" `
    -ScopeText "12 状态静态组件源图；完整机器闭环通过；runtime inactive；非整脸播放" `
    -Message $message `
    -ExpectedText $expected `
    -Input `
    -ReviewStyle `
    -Buttons "通过,需修改,跳过,中止" `
    -OutputPath $noteAbsolutePath `
    -TimeoutSeconds $TimeoutSeconds `
    -Json
if ($LASTEXITCODE -ne 0) { throw "Canonical aiw operator-prompt failed." }
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resultAbsolutePath) | Out-Null
Set-Content -LiteralPath $resultAbsolutePath -Value $promptJsonText -Encoding utf8
$promptResult = $promptJsonText | ConvertFrom-Json
$selection = [string]$promptResult.selected
if ([string]::IsNullOrWhiteSpace($selection)) { $selection = [string]$promptResult.selection }
$summary.selection = $selection
$summary.selection_text = [string]$promptResult.text
$summary.operator_note_present = (Test-Path -LiteralPath $noteAbsolutePath) -and
    -not [string]::IsNullOrWhiteSpace((Get-Content -LiteralPath $noteAbsolutePath -Raw))
switch ($selection) {
    "通过" { $summary.status = "PASS_OWNER_COMPLETE_EXPRESSION_SOURCE_BUNDLE_REVIEW" }
    "需修改" { $summary.status = "FAIL_OWNER_COMPLETE_EXPRESSION_SOURCE_BUNDLE_REVIEW" }
    "跳过" { $summary.status = "SKIPPED_BY_OWNER" }
    "中止" { $summary.status = "ABORTED_BY_OWNER" }
    "Timeout" { $summary.status = "NO_OWNER_SELECTION_TIMEOUT" }
    default { $summary.status = "NO_OWNER_APPROVAL" }
}
Write-JsonFile $summary $summaryAbsolutePath
Write-Output ("{0}: selection={1}" -f $summary.status, $selection)
