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
$gatePath = "docs\validation\companion-v22-emotion-separation-component-bridge-gate-20260719.json"
$previewPath = "docs\art\iterations\companion-pet-expression-v9-extension-v22-emotion-separation-source\candidate\component-bridge-attempt-01\preview.html"
$resultPath = "docs\validation\companion-v22-emotion-separation-component-bridge-owner-art-screen-review-20260719.json"
$notePath = "docs\validation\companion-v22-emotion-separation-component-bridge-owner-art-screen-review-20260719.note.txt"
$gate = Get-Content -LiteralPath $gatePath -Raw | ConvertFrom-Json
if ($gate.status -ne "PASS_V22_EMOTION_SEPARATION_COMPONENT_BRIDGE_GATE") {
    throw "V22 component bridge gate is not ready for owner art/screen review: $($gate.status)"
}
if (-not (Test-Path -LiteralPath $previewPath)) { throw "V22 component bridge preview is missing: $previewPath" }
if ($DryRun) {
    Write-Output "PASS: V22 component bridge owner art/screen review is ready; all machine gates are PASS."
    exit 0
}

& pwsh -NoProfile -File (Join-Path $workflowRoot "scripts\verify_pwsh7.ps1")
if ($LASTEXITCODE -ne 0) { throw "PowerShell 7 verification failed before operator review" }
$previewAbsolute = (Resolve-Path $previewPath).Path -replace "\\", "/"
Start-Process -FilePath ("file:///" + $previewAbsolute + "?state=calm&target=curious")
Remove-Item -LiteralPath $notePath -Force -ErrorAction SilentlyContinue
$prompt = Join-Path $workflowRoot "scripts\aiw.ps1"
$promptResult = & pwsh -NoProfile -File $prompt operator-prompt `
    -Title "V22 日常情绪差异组件编舞 美术与屏幕审阅" `
    -ProgressText "1/1" `
    -ScopeText "审阅 V22 的锁定 V9 来源组件级情绪差异与定向转场；浏览器与 200x200 PBM 同计划，候选仍 runtime inactive。" `
    -Message "已打开 Calm -> Curious。请观察六种基础情绪是否仍是同一 V9 角色但可一眼分开；转场时主高光是否先表达注意，小 sparkle 是否随后跟上，眉与鼻嘴腮点是否依次回应；到目标情绪后页面应稳定停留而不是自行跳回来源。可改选其它合法目标。" `
    -ExpectedText "通过：六种情绪有清晰区分、转场自然且仍是同一 V9 角色；需修改：写下具体哪条边、哪个五官、哪种情绪或哪段节奏不自然。" `
    -Input -ReviewStyle -Buttons "通过,需修改,中止" -OutputPath $notePath -Json | ConvertFrom-Json
$note = if (Test-Path -LiteralPath $notePath) { Get-Content -LiteralPath $notePath -Raw } else { "" }
$accepted = $promptResult.selected -eq "通过"
$record = [ordered]@{
    schema = "companion.v22_emotion_separation_component_bridge_owner_art_screen_review.v1"
    status = if ($accepted) { "PASS_OWNER_V22_EMOTION_SEPARATION_COMPONENT_BRIDGE_ACCEPTED_RUNTIME_INACTIVE" } else { "FAIL_OWNER_V22_EMOTION_SEPARATION_COMPONENT_BRIDGE_REVIEW" }
    machine_bridge_gate = $gatePath
    preview = $previewPath
    selected = $promptResult.selected
    operator_note = $note
    component_choreography = if ($accepted) { "owner_accepted_v22_component_candidate_runtime_inactive" } else { "owner_refinement_required" }
    runtime_resource_activated = $false
    active_candidate_binding = "forbidden"
    special_event_fallback = "fail_closed"
}
$record | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $resultPath -Encoding utf8
Write-Output "V22_EMOTION_SEPARATION_COMPONENT_BRIDGE_OWNER_ART_SCREEN_REVIEW=$($record.status)"
