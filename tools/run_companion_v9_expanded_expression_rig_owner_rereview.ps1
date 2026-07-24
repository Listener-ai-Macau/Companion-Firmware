#requires -Version 7.0
[CmdletBinding()]
param(
    [switch]$DryRun,
    [ValidateRange(1, 840)]
    [int]$TimeoutSeconds = 840,
    [string]$WorkflowRepo = "",
    [string]$ResultPath = "docs\validation\companion-v9-expanded-expression-rig-owner-rereview-20260719.json",
    [string]$NotePath = "docs\validation\companion-v9-expanded-expression-rig-owner-rereview-20260719.note.txt",
    [string]$SummaryPath = "docs\validation\companion-v9-expanded-expression-rig-owner-rereview-summary-20260719.json"
)

$ErrorActionPreference = "Stop"

function Resolve-WorkflowRepo {
    param([string]$RequestedPath)
    foreach ($candidate in @($RequestedPath, $env:AI_WORKFLOW_REPO, "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow") |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) {
        $resolved = [System.IO.Path]::GetFullPath($candidate)
        if (Test-Path -LiteralPath (Join-Path $resolved "docs\agent_quickstart.md")) { return $resolved }
    }
    throw "Unable to resolve AI workflow repository."
}

function Require-Equal {
    param($Actual, $Expected, [string]$Description)
    if ($Actual -ne $Expected) { throw "$Description expected '$Expected' but found '$Actual'." }
}

function Write-JsonFile {
    param($Value, [string]$Path)
    $directory = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($directory)) { New-Item -ItemType Directory -Force -Path $directory | Out-Null }
    $Value | ConvertTo-Json -Depth 14 | Set-Content -LiteralPath $Path -Encoding utf8
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot
$workflowRoot = Resolve-WorkflowRepo -RequestedPath $WorkflowRepo
$aiw = Join-Path $workflowRoot "scripts\aiw.ps1"
& pwsh -NoProfile -File (Join-Path $workflowRoot "scripts\verify_pwsh7.ps1")
if ($LASTEXITCODE -ne 0) { throw "PowerShell 7 verification failed." }

$candidate = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-rig-v2-expanded-source\candidate"
$layoutPath = Join-Path $candidate "rig-layout.json"
$preview = Join-Path $candidate "preview.html"
$playfulSheet = Join-Path $candidate "performance-contact-sheets\playful_bright.png"
$allStatesSheet = Join-Path $candidate "expanded-component-rig-contact-sheet.png"
$performanceDirectory = Join-Path $candidate "performance-contact-sheets"
$closurePath = Join-Path $repoRoot "docs\validation\companion-v9-expression-rig-goal-machine-closure-20260719.json"
$machineGatePath = Join-Path $repoRoot "docs\validation\companion-v9-expanded-expression-rig-export-20260719.json"
$previousReviewPath = Join-Path $repoRoot "docs\validation\companion-v9-expanded-expression-rig-owner-screen-review-final-20260719.json"
$lockedSource = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9\generated_pet_expression_sheet_v9_candidate.png"
$protectedAcceptance = Join-Path $repoRoot "docs\validation\companion-pet-special-system-owner-acceptance-20260717.json"
foreach ($path in @($layoutPath, $preview, $playfulSheet, $allStatesSheet, $performanceDirectory, $closurePath, $machineGatePath,
        $previousReviewPath, $lockedSource, $protectedAcceptance)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing expanded Rig re-review evidence: $path" }
}

$layout = Get-Content -LiteralPath $layoutPath -Raw | ConvertFrom-Json
$closure = Get-Content -LiteralPath $closurePath -Raw | ConvertFrom-Json
$machineGate = Get-Content -LiteralPath $machineGatePath -Raw | ConvertFrom-Json
$previousReview = Get-Content -LiteralPath $previousReviewPath -Raw | ConvertFrom-Json
$lockedHash = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
$protectedHash = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"
Require-Equal $closure.status "PASS_GOAL_MACHINE_CLOSURE_OWNER_SCREEN_REVIEW_PENDING" "active Goal machine closure"
Require-Equal $machineGate.status "PASS_EXPANDED_COMPONENT_RIG_MACHINE_GATE" "expanded Rig machine gate"
Require-Equal $layout.status "CANDIDATE_MACHINE_EXPORT_PENDING" "expanded Rig candidate status"
Require-Equal $layout.runtime_resource_activated $false "expanded Rig runtime state"
Require-Equal @($layout.state_matrix).Count 15 "expanded active state count"
Require-Equal ($layout.unsupported_events_fail_closed -contains "sleep") $true "expanded Sleep fail-closed contract"
Require-Equal $previousReview.selected "失败" "previous expanded Rig review disposition"
Require-Equal (@($previousReview.rejected_states) -contains "playful_bright") $true "previous Playful rejection evidence"
Require-Equal (@($previousReview.rejected_states) -contains "sleep_rest_no_moon") $true "previous Sleep rejection evidence"
$playful = @($layout.state_matrix | Where-Object { $_.name -eq "playful_bright" })
Require-Equal $playful.Count 1 "active Playful state count"
$playfulComponents = @($layout.state_component_sets.playful_bright)
foreach ($rejected in @("cheek_detail_left", "cheek_detail_right", "charm_sparkle")) {
    if ($playfulComponents -contains $rejected) { throw "Playful still binds owner-rejected decoration: $rejected" }
}
Require-Equal @($layout.performances.playful_bright.steps).Count 7 "Playful component performance phase count"
Require-Equal (@($layout.performances.playful_bright.steps | ForEach-Object { $_.phase }) -join ",") "entry,lead,response,accent,hold,return,settle" "Playful component performance order"
Require-Equal (Get-FileHash -Algorithm SHA256 -LiteralPath $lockedSource).Hash.ToUpperInvariant() $lockedHash "locked V9 source hash"
Require-Equal (Get-FileHash -Algorithm SHA256 -LiteralPath $protectedAcceptance).Hash.ToUpperInvariant() $protectedHash "protected prior owner acceptance hash"

$resultAbsolutePath = Join-Path $repoRoot $ResultPath
$noteAbsolutePath = Join-Path $repoRoot $NotePath
$summaryAbsolutePath = Join-Path $repoRoot $SummaryPath
$summary = [ordered]@{
    schema = "companion.v9_expanded_expression_rig_owner_rereview_summary.v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    dry_run = [bool]$DryRun
    candidate = $candidate
    layout = $layoutPath
    layout_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $layoutPath).Hash.ToUpperInvariant()
    preview = $preview
    preview_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $preview).Hash.ToUpperInvariant()
    playful_contact_sheet = $playfulSheet
    playful_contact_sheet_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $playfulSheet).Hash.ToUpperInvariant()
    all_states_contact_sheet = $allStatesSheet
    all_states_contact_sheet_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $allStatesSheet).Hash.ToUpperInvariant()
    active_state_count = 15
    performance_frame_count = 105
    repaired_state = "playful_bright"
    sleep_state = "fail_closed_unbound_pending_separate_v15_binding_contract"
    runtime_resource_activated = $false
    active_candidate_binding = "forbidden"
    crig_mount = "candidate_not_runtime_active"
    locked_v9_sha256 = $lockedHash
    protected_prior_owner_acceptance_sha256 = $protectedHash
    prompt_style = "aiw_operator_prompt_v1"
}
if ($DryRun) {
    $summary.status = "READY_FOR_OWNER_EXPANDED_RIG_REREVIEW"
    Write-JsonFile $summary $summaryAbsolutePath
    Write-Output "READY_FOR_OWNER_EXPANDED_RIG_REREVIEW: $preview"
    exit 0
}

$previewUrl = "file:///" + ($preview -replace "\\", "/") + "?state=playful_bright"
Start-Process -FilePath $previewUrl
Start-Sleep -Milliseconds 700
Start-Process -FilePath $playfulSheet
Start-Sleep -Milliseconds 700
Start-Process -FilePath $allStatesSheet
Start-Sleep -Milliseconds 700
Start-Process -FilePath $performanceDirectory
Start-Sleep -Seconds 2
$message = @"
请验收刚打开的修后 Expanded V9 Rig 候选。第一个窗口会直接播放 `playful_bright` 的完整七相组件表演；第二个窗口是它的逐相联系表；第三个是 15 个 active 状态的总表；第四个文件夹含每个 active 状态的七相联系表，可逐张检查。

本次只修复上一轮被点名的 Playful：已移除腮边细节和 sparkle/charm 装饰绑定，保留同一 V9 眼睛与已接受的 Playful 脸部组件。睡眠旧脸仍完全 fail-closed，未借用日常脸；V15 睡眠仅是另行通过的未绑定候选，不在本候选里播放。

重点看：Playful 是否终于是一张完整、干净的角色脸；每个 active 状态的眼睛、眉、鼻嘴、腮和允许的小装饰是否始终不遮住彼此；点击预览中的状态卡时是否播放该状态自己的组件表演，而不是整脸卡片或随机轮播。
"@
$expected = @"
通过：确认当前 15 个 active V9 状态的组件组合、Playful 修复和 Sleep fail-closed 方向可保留为 runtime-inactive 候选；后续仍需独立 runtime/物理屏幕接入门，不能直接默认激活。
需修改：保留本次机器证据并按备注修复来源组件的绑定、锚点或时序；不得回退到整脸贴图、日常脸替代 Sleep、旧/拒绝美术或代码绘制五官。
"@
$promptJsonText = & pwsh -NoProfile -File $aiw operator-prompt `
    -Title "Companion Expanded V9 Rig 修后组件屏幕复验" `
    -ProgressText "1/1" `
    -ScopeText "15 个 active source-mask 状态、105 相位、Playful 修复、Sleep fail-closed；runtime inactive" `
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
$summary.selection_text = [string]$promptResult.selection_text
$summary.note_path = $noteAbsolutePath
$summary.result_path = $resultAbsolutePath
$summary.status = if ($selection -eq "通过") { "PASS_OWNER_EXPANDED_RIG_REREVIEW" } elseif ($selection -eq "需修改") { "FAIL_OWNER_EXPANDED_RIG_REREVIEW" } else { "NO_OWNER_SELECTION" }
Write-JsonFile $summary $summaryAbsolutePath
Write-Output "$($summary.status): $preview"
