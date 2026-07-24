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
$gatePath = "docs\validation\companion-v21-everyday-emotion-distinction-source-gate-20260719.json"
$imagePath = "docs\art\iterations\companion-pet-expression-v9-extension-v21-everyday-emotion-distinction-source\candidate\attempt-01-generated-everyday-emotion-distinction.png"
$resultPath = "docs\validation\companion-v21-everyday-emotion-distinction-owner-art-review-20260719.json"
$notePath = "docs\validation\companion-v21-everyday-emotion-distinction-owner-art-review-20260719.note.txt"
$gate = Get-Content -LiteralPath $gatePath -Raw | ConvertFrom-Json
if ($gate.status -ne "PASS_V21_EVERYDAY_EMOTION_DISTINCTION_SOURCE_GATE_PENDING_OWNER_ART_REVIEW") {
    throw "V21 source gate is not ready for owner art review: $($gate.status)"
}
if (-not (Test-Path -LiteralPath $imagePath)) { throw "V21 candidate image is missing: $imagePath" }
if ($DryRun) {
    Write-Output "PASS: V21 owner art review is ready; source gate is PASS and candidate image exists."
    exit 0
}

Start-Process -FilePath (Resolve-Path $imagePath)
Remove-Item -LiteralPath $notePath -Force -ErrorAction SilentlyContinue
$prompt = Join-Path $workflowRoot "scripts\aiw.ps1"
$promptResult = & pwsh -NoProfile -File $prompt operator-prompt `
    -Title "V21 日常情绪源姿态美术审阅" `
    -ProgressText "1/1" `
    -ScopeText "仅审阅 V21 六个日常情绪源姿态；尚未拆组件、绑定或启用 runtime。" `
    -Message "请看已打开的六姿态候选图。重点判断：是否仍是同一 V9 角色，以及 Calm / Curious / Warm / Playful / Puzzled / Alert 是否一眼可区分。" `
    -ExpectedText "通过：眼型和角色身份保持 V9，六种情绪可读且有明确差别；需修改：写下需要拉开的具体情绪或五官差异。" `
    -Input -ReviewStyle -Buttons "通过,需修改,中止" -OutputPath $notePath -Json | ConvertFrom-Json
$note = if (Test-Path -LiteralPath $notePath) { Get-Content -LiteralPath $notePath -Raw } else { "" }
$accepted = $promptResult.selected -eq "通过"
$record = [ordered]@{
    schema = "companion.v21_everyday_emotion_distinction_owner_art_review.v1"
    status = if ($accepted) { "PASS_OWNER_V21_EVERYDAY_EMOTION_ART_ACCEPTED_PENDING_COMPONENT_EXPORT" } else { "FAIL_OWNER_V21_EVERYDAY_EMOTION_ART_REVIEW" }
    source_gate = $gatePath
    candidate_image = $imagePath
    selected = $promptResult.selected
    operator_note = $note
    component_export = if ($accepted) { "pending_machine_component_export" } else { "forbidden_pending_owner_refinement" }
    runtime_resource_activated = $false
    active_candidate_binding = "forbidden"
}
$record | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $resultPath -Encoding utf8
Write-Output "V21_OWNER_ART_REVIEW=$($record.status)"
