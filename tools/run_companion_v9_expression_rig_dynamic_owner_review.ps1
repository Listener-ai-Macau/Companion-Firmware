#requires -Version 7.0
[CmdletBinding()]
param(
    [switch]$DryRun,
    [int]$TimeoutSeconds = 840,
    [string]$WorkflowRepo = "",
    [string]$ResultPath = "docs\validation\companion-v9-expression-rig-dynamic-owner-review-20260717.json",
    [string]$NotePath = "docs\validation\companion-v9-expression-rig-dynamic-owner-review-20260717.note.txt",
    [string]$SummaryPath = "docs\validation\companion-v9-expression-rig-dynamic-owner-review-summary-20260717.json",
    [string]$DryRunSummaryPath = "docs\validation\companion-v9-expression-rig-dynamic-owner-review-launch-dry-run-20260717.json",
    [string]$AcceptedBaselinePath = "docs\validation\companion-v9-expression-rig-accepted-dynamic-baseline.json",
    [string]$AcceptedBaselineArtifactDir = "docs\validation\artifacts\companion-v9-expression-rig-accepted-dynamic-baseline"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Leave a margin below the 900-second command supervisor so the canonical prompt
# can persist its selected result and cleanly exit before its parent is reaped.
if ($TimeoutSeconds -lt 1 -or $TimeoutSeconds -gt 840) {
    throw "TimeoutSeconds must be between 1 and 840 so operator-prompt can archive its result before the command deadline."
}

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $repoRoot

function Resolve-WorkflowRepo {
    param([string]$Requested)

    if (-not [string]::IsNullOrWhiteSpace($Requested)) {
        $candidate = $Requested
    } elseif (-not [string]::IsNullOrWhiteSpace($env:AI_WORKFLOW_REPO)) {
        $candidate = $env:AI_WORKFLOW_REPO
    } else {
        $candidate = "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow"
    }

    $quickstart = Join-Path $candidate "docs\agent_quickstart.md"
    if (-not (Test-Path -LiteralPath $quickstart)) {
        $candidate = "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow"
        $quickstart = Join-Path $candidate "docs\agent_quickstart.md"
    }
    if (-not (Test-Path -LiteralPath $quickstart)) {
        throw "Cannot resolve ai-collaboration-workflow repo with docs\agent_quickstart.md."
    }
    return (Resolve-Path -LiteralPath $candidate).Path
}

function Invoke-RepoCommand {
    param(
        [string]$Exe,
        [string[]]$Arguments
    )

    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $Exe $($Arguments -join ' ')"
    }
}

function Write-JsonFile {
    param(
        [string]$Path,
        [object]$Value
    )

    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    $Value | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Path -Encoding UTF8
}

$workflow = Resolve-WorkflowRepo -Requested $WorkflowRepo
$verifyPwsh = Join-Path $workflow "scripts\verify_pwsh7.ps1"
$aiw = Join-Path $workflow "scripts\aiw.ps1"

Invoke-RepoCommand -Exe "pwsh" -Arguments @("-NoProfile", "-File", $verifyPwsh)
Invoke-RepoCommand -Exe "python" -Arguments @(
    "tools\render_companion_v9_expression_rig_review.py",
    "--write",
    "docs\validation\companion-v9-expression-rig-review-readiness-20260717.json"
)
Invoke-RepoCommand -Exe "python" -Arguments @(
    "tools\verify_companion_v9_expression_rig_dynamic_preview.py",
    "--preview-report",
    "docs\validation\companion-v9-expression-rig-dynamic-preview-20260717.json",
    "--render-report",
    "docs\validation\companion-v9-expression-rig-render-20260717.json",
    "--write",
    "docs\validation\companion-v9-expression-rig-preview-distance-20260717.json"
)

$readinessPath = "docs\validation\companion-v9-expression-rig-review-readiness-20260717.json"
$distancePath = "docs\validation\companion-v9-expression-rig-preview-distance-20260717.json"
$readiness = Get-Content -Raw -LiteralPath $readinessPath | ConvertFrom-Json
$distance = Get-Content -Raw -LiteralPath $distancePath | ConvertFrom-Json

if ($readiness.status -ne "PASS_DYNAMIC_REVIEW_READY") {
    throw "Review readiness is not PASS_DYNAMIC_REVIEW_READY."
}
if ($distance.status -ne "PASS_PREVIEW_DISTANCE_READY_FOR_OWNER_PROMPT") {
    throw "Preview distance is not PASS_PREVIEW_DISTANCE_READY_FOR_OWNER_PROMPT."
}
if ($readiness.runtime_resource_activated -ne $false -or $distance.runtime_resource_activated -ne $false) {
    throw "Candidate review must remain runtime inactive."
}

$reviewPage = (Resolve-Path -LiteralPath $readiness.review_page).Path
$message = @"
请查看已经打开的浏览器页面：Companion v9 组件级动态 Rig player。

验收范围：电脑侧 200x200 动态预览，不是物理 e-paper 面板验收；候选 runtime 仍 inactive。

请重点看：
1. 仍然是同一个已锁定 V9 角色身份。
2. 动态来自组件级变化：眼睛/高光、眉、鼻嘴/嘴唇、腮点、左右侧边细节线/胡须感、小挂件。
3. 看起来不像一组整脸贴图轮播，也不像静态矩阵或 PPT 三帧。
4. entry -> sustain -> settle 的顺序自然，settle 回到 V9 calm baseline。
5. 没有旧工程脸、legacy 美术、代码绘制五官、球形诊断或 custom LUT 的感觉。

机器前置证据已 PASS：render/CEMP/choreographer/WBA mount/motion/static/pipeline/preview-distance。
"@
$expected = @"
通过标准：动态预览可接受为 V9 source-derived component Rig 候选；如果失败，请在备注里写出具体不像动态、像贴图、身份偏离或组件不自然的位置。
"@

if ($DryRun) {
    $dryRunReport = [ordered]@{
        schema = "companion.v9_expression_rig_owner_review_launch_dry_run.v1"
        status = "PASS_DRY_RUN_READY_TO_PROMPT"
        review_page = $readiness.review_page
        review_page_sha256 = $readiness.review_page_sha256
        preview_distance = $distancePath
        preview_distance_status = $distance.status
        result_path = $ResultPath
        note_path = $NotePath
        summary_path = $SummaryPath
        accepted_dynamic_baseline_path = $AcceptedBaselinePath
        accepted_dynamic_baseline_artifact_dir = $AcceptedBaselineArtifactDir
        accepted_dynamic_baseline = $distance.accepted_dynamic_baseline
        timeout_seconds = $TimeoutSeconds
        source_sha256 = $readiness.source_sha256
        runtime_resource_activated = $false
        prompt_would_launch = $false
    }
    Write-JsonFile -Path $DryRunSummaryPath -Value $dryRunReport
    Write-Output ($dryRunReport | ConvertTo-Json -Depth 8)
    exit 0
}

Start-Process -FilePath $reviewPage
Start-Sleep -Seconds 3

$promptJsonText = & pwsh -NoProfile -File $aiw operator-prompt `
    -Title "Companion v9 Rig 动态表情验收" `
    -ProgressText "v9 Rig dynamic preview" `
    -ScopeText "电脑侧动态 Rig；非物理屏；runtime inactive" `
    -Message $message `
    -ExpectedText $expected `
    -Input `
    -ReviewStyle `
    -OutputPath $NotePath `
    -TimeoutSeconds $TimeoutSeconds `
    -Json
if ($LASTEXITCODE -ne 0) {
    throw "operator-prompt failed with exit code $LASTEXITCODE"
}

$promptJsonText | Set-Content -LiteralPath $ResultPath -Encoding UTF8
$promptResult = $promptJsonText | ConvertFrom-Json

$status = switch ($promptResult.selected) {
    "通过" { "PASS_OWNER_REVIEW" }
    "失败" { "FAIL_OWNER_REVIEW" }
    "Timeout" { "NO_OWNER_SELECTION_TIMEOUT" }
    "跳过" { "SKIPPED_BY_OWNER" }
    "中止" { "ABORTED_BY_OWNER" }
    default { "NO_OWNER_APPROVAL" }
}

$summary = [ordered]@{
    schema = "companion.v9_expression_rig_owner_review_summary.v1"
    status = $status
    selected = $promptResult.selected
    text = $promptResult.text
    result_path = $ResultPath
    note_path = $NotePath
    review_page = $readiness.review_page
    preview_distance = $distancePath
    preview_distance_status = $distance.status
    accepted_dynamic_baseline_path = $AcceptedBaselinePath
    accepted_dynamic_baseline_status = $distance.accepted_dynamic_baseline.status
    accepted_dynamic_baseline_promotion_status = "not_applicable"
    source_sha256 = $readiness.source_sha256
    runtime_resource_activated = $false
    goal_complete = $false
    goal_completion_candidate = ($status -eq "PASS_OWNER_REVIEW")
    goal_completion_requires_codex_audit = $true
}
Write-JsonFile -Path $SummaryPath -Value $summary

if ($status -eq "PASS_OWNER_REVIEW") {
    Invoke-RepoCommand -Exe "python" -Arguments @(
        "tools\promote_companion_v9_expression_rig_dynamic_baseline.py",
        "--owner-summary",
        $SummaryPath,
        "--owner-result",
        $ResultPath,
        "--preview-report",
        "docs\validation\companion-v9-expression-rig-dynamic-preview-20260717.json",
        "--distance-report",
        $distancePath,
        "--render-report",
        "docs\validation\companion-v9-expression-rig-render-20260717.json",
        "--write",
        $AcceptedBaselinePath,
        "--artifact-dir",
        $AcceptedBaselineArtifactDir
    )
    $baseline = Get-Content -Raw -LiteralPath $AcceptedBaselinePath | ConvertFrom-Json
    $summary["accepted_dynamic_baseline_status"] = $baseline.status
    $summary["accepted_dynamic_baseline_promotion_status"] = "PASS_PROMOTED"
    $summary["accepted_dynamic_baseline_artifact_dir"] = $AcceptedBaselineArtifactDir
    $summary["accepted_dynamic_baseline_story_count"] = $baseline.story_count
    $summary["accepted_dynamic_baseline_dynamic_groups"] = $baseline.dynamic_groups
    Write-JsonFile -Path $SummaryPath -Value $summary
}
Write-Output ($summary | ConvertTo-Json -Depth 8)
