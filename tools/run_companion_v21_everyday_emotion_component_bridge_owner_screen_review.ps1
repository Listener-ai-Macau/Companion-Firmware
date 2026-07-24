#requires -Version 7.0
[CmdletBinding()]
param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot
$workflowRoot = if ($env:AI_WORKFLOW_REPO -and (Test-Path (Join-Path $env:AI_WORKFLOW_REPO "docs\agent_quickstart.md"))) {
    $env:AI_WORKFLOW_REPO
} else {
    "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow"
}
$gatePath = "docs\validation\companion-v21-everyday-emotion-component-bridge-gate-20260719.json"
$previewPath = "docs\art\iterations\companion-pet-expression-v9-extension-v21-everyday-emotion-distinction-source\candidate\component-bridge-attempt-01\preview.html"
$resultPath = "docs\validation\companion-v21-everyday-emotion-component-bridge-owner-screen-review-20260719.json"
$notePath = "docs\validation\companion-v21-everyday-emotion-component-bridge-owner-screen-review-20260719.note.txt"
$gate = Get-Content -LiteralPath $gatePath -Raw | ConvertFrom-Json
if ($gate.status -ne "PASS_V21_EVERYDAY_EMOTION_COMPONENT_BRIDGE_GATE") {
    throw "V21 component bridge gate is not ready for owner screen review: $($gate.status)"
}
if (-not (Test-Path -LiteralPath $previewPath)) { throw "V21 component bridge preview is missing: $previewPath" }
if ($DryRun) {
    Write-Output "PASS: V21 component bridge owner screen review is ready; all machine gates are PASS."
    exit 0
}

& pwsh -NoProfile -File (Join-Path $workflowRoot "scripts\verify_pwsh7.ps1")
if ($LASTEXITCODE -ne 0) { throw "PowerShell 7 verification failed before operator review" }
$previewAbsolute = (Resolve-Path $previewPath).Path -replace "\\", "/"
Start-Process -FilePath ("file:///" + $previewAbsolute + "?state=calm&target=curious")
Remove-Item -LiteralPath $notePath -Force -ErrorAction SilentlyContinue
$prompt = Join-Path $workflowRoot "scripts\aiw.ps1"
$promptResult = & pwsh -NoProfile -File $prompt operator-prompt `
    -Title "V21 日常情绪组件编舞屏幕审阅" `
    -ProgressText "1/1" `
    -ScopeText "仅审阅 V21 日常情绪的组件级有向过渡；浏览器与 200x200 PBM 同计划，候选仍 runtime inactive。" `
    -Message "已打开 Calm -> Curious 动态预览。请让它完整往返一次，并切换其它可选目标查看。重点判断：高光先动、眉与鼻嘴腮点随后回应，六种情绪是否可读且仍像同一个 V9 角色；不应感觉成整张脸轮播。" `
    -ExpectedText "通过：组件级转场自然、有区分度且保留 V9 身份；需修改：写下具体哪条边、哪个五官或哪段节奏不自然。" `
    -Input -ReviewStyle -Buttons "通过,需修改,中止" -OutputPath $notePath -Json | ConvertFrom-Json
$note = if (Test-Path -LiteralPath $notePath) { Get-Content -LiteralPath $notePath -Raw } else { "" }
$accepted = $promptResult.selected -eq "通过"
$record = [ordered]@{
    schema = "companion.v21_everyday_emotion_component_bridge_owner_screen_review.v1"
    status = if ($accepted) { "PASS_OWNER_V21_COMPONENT_EMOTION_BRIDGE_ACCEPTED_RUNTIME_INACTIVE" } else { "FAIL_OWNER_V21_COMPONENT_EMOTION_BRIDGE_REVIEW" }
    machine_bridge_gate = $gatePath
    preview = $previewPath
    selected = $promptResult.selected
    operator_note = $note
    component_choreography = if ($accepted) { "owner_accepted_candidate_runtime_inactive" } else { "owner_refinement_required" }
    runtime_resource_activated = $false
    active_candidate_binding = "forbidden"
    special_event_fallback = "fail_closed"
}
$record | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $resultPath -Encoding utf8
Write-Output "V21_COMPONENT_BRIDGE_OWNER_SCREEN_REVIEW=$($record.status)"
