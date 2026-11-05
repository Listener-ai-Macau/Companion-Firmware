#requires -Version 7.0
[CmdletBinding()]
param(
    [switch]$DryRun,
    [ValidateRange(1, 840)]
    [int]$TimeoutSeconds = 840,
    [string]$WorkflowRepo = "",
    [string]$ResultPath = "docs\validation\companion-v9-extension-v17-functional-context-owner-art-review-20260719.json",
    [string]$NotePath = "docs\validation\companion-v9-extension-v17-functional-context-owner-art-review-20260719.note.txt",
    [string]$SummaryPath = "docs\validation\companion-v9-extension-v17-functional-context-owner-art-review-summary-20260719.json"
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

$v17Root = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-extension-v17-functional-context-accents"
$requestPath = Join-Path $v17Root "generation-request.json"
$sourcePanel = Join-Path $v17Root "candidate\attempt-01-generated-functional-context-accent-panel.png"
$attemptPath = Join-Path $v17Root "candidate\attempt-01-generated-functional-context-accent-panel.json"
$contactSheet = Join-Path $v17Root "candidate\component-export-attempt-01\functional-context-source-only-contact-sheet.png"
$layoutPath = Join-Path $v17Root "candidate\component-export-attempt-01\v17-functional-context-component-layout.json"
$sourceGatePath = Join-Path $repoRoot "docs\validation\companion-v9-extension-v17-functional-context-source-20260719.json"
$componentGatePath = Join-Path $repoRoot "docs\validation\companion-v9-extension-v17-functional-context-components-20260719.json"
$lockedSource = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9\generated_pet_expression_sheet_v9_candidate.png"
foreach ($path in @($requestPath, $sourcePanel, $attemptPath, $contactSheet, $layoutPath, $sourceGatePath, $componentGatePath, $lockedSource)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing V17 functional-context art review evidence: $path" }
}

$request = Get-Content -LiteralPath $requestPath -Raw | ConvertFrom-Json
$attempt = Get-Content -LiteralPath $attemptPath -Raw | ConvertFrom-Json
$layout = Get-Content -LiteralPath $layoutPath -Raw | ConvertFrom-Json
$sourceGate = Get-Content -LiteralPath $sourceGatePath -Raw | ConvertFrom-Json
$componentGate = Get-Content -LiteralPath $componentGatePath -Raw | ConvertFrom-Json
$lockedHash = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
Require-Equal $request.status "PROMPT_VERSIONED_PENDING_GENERATION" "V17 generation request"
Require-Equal $attempt.status "PASS_MACHINE_SOURCE_GATE_PENDING_COMPONENT_EXPORT" "V17 generation attempt"
Require-Equal $sourceGate.status "PASS_V17_FUNCTIONAL_CONTEXT_SOURCE_GATE" "V17 source machine gate"
Require-Equal $componentGate.status "PASS_V17_FUNCTIONAL_CONTEXT_COMPONENT_EXPORT_UNBOUND" "V17 component export machine gate"
Require-Equal $layout.status "UNBOUND_PENDING_OWNER_ART_REVIEW" "V17 component layout"
Require-Equal $layout.runtime_resource_activated $false "V17 runtime state"
Require-Equal $layout.active_candidate_binding "forbidden" "V17 active candidate binding"
Require-Equal @($layout.components.psobject.Properties).Count 11 "V17 source component count"
Require-Equal (Get-FileHash -Algorithm SHA256 -LiteralPath $lockedSource).Hash.ToUpperInvariant() $lockedHash "locked V9 source hash"
if (@(Get-ChildItem -LiteralPath (Join-Path $v17Root "candidate") -Recurse -File -Filter *.crig).Count -ne 0) {
    throw "V17 source-art candidate must not contain a CRIG package before owner art acceptance."
}

$resultAbsolutePath = Join-Path $repoRoot $ResultPath
$noteAbsolutePath = Join-Path $repoRoot $NotePath
$summaryAbsolutePath = Join-Path $repoRoot $SummaryPath
$summary = [ordered]@{
    schema = "companion.v17_functional_context_owner_art_review_summary.v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    dry_run = [bool]$DryRun
    locked_v9_source = $lockedSource
    locked_v9_sha256 = $lockedHash
    source_panel = $sourcePanel
    source_panel_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourcePanel).Hash.ToUpperInvariant()
    source_only_contact_sheet = $contactSheet
    source_only_contact_sheet_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $contactSheet).Hash.ToUpperInvariant()
    source_component_count = 11
    component_groups = @("menu_active", "recording_active", "upgrade_active")
    active_candidate_binding = "forbidden"
    runtime_resource_activated = $false
    prompt_style = "aiw_operator_prompt_v1"
}
if ($DryRun) {
    $summary.status = "READY_FOR_OWNER_V17_FUNCTIONAL_CONTEXT_ART_REVIEW"
    Write-JsonFile $summary $summaryAbsolutePath
    Write-Output "READY_FOR_OWNER_V17_FUNCTIONAL_CONTEXT_ART_REVIEW: $sourcePanel"
    exit 0
}

Start-Process -FilePath $lockedSource
Start-Sleep -Milliseconds 700
Start-Process -FilePath $sourcePanel
Start-Sleep -Milliseconds 700
Start-Process -FilePath $contactSheet
Start-Sleep -Seconds 2
$message = @"
请验收刚打开的 V17 功能上下文美术源件。第一个窗口是锁定 V9 参考；第二个是这次新生成的三组独立小组件源图；第三个是从源图阈值裁切后的 200x200 空白画布重组，仅用于检查组件形状和间距，不是完整表情或运行时画面。

本轮只确认三组小组件的美术方向：菜单使用安静的三点选择提示；录音使用左右对称的聆听波纹；升级使用四段可逐段出现的进度环。它们都没有脸、文字、UI、旧美术或代码绘制像素。

通过只允许这些源掩码进入下一步的“同一 V9 脸组件绑定与事件编舞”机器验证。它不会激活 runtime、不会生成 CRIG、不会让升级借用日常脸，也不会放宽睡眠、充电、错误的 fail-closed 规则。
"@
$expected = @"
通过：确认三组 V9-only 源组件的风格、克制程度和语义方向可保留，允许继续做 unbound 的菜单/录音/升级组件编舞机器验证；仍不得直接激活 runtime。
需修改：按备注新建后续版本化 V9-only prompt/source 图；现有 V17 组件保持 unbound，不能用旧图、日常脸、整脸切换或代码符号替代。
"@
$promptJsonText = & pwsh -NoProfile -File $aiw operator-prompt `
    -Title "Companion V17 功能上下文美术源件验收" `
    -ProgressText "1/1" `
    -ScopeText "菜单/录音/升级的 11 个 source-mask；runtime inactive，未绑定" `
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
$summary.status = if ($selection -eq "通过") { "PASS_OWNER_V17_FUNCTIONAL_CONTEXT_ART_REVIEW" } elseif ($selection -eq "需修改") { "FAIL_OWNER_V17_FUNCTIONAL_CONTEXT_ART_REVIEW" } else { "NO_OWNER_SELECTION" }
Write-JsonFile $summary $summaryAbsolutePath
Write-Output "$($summary.status): $sourcePanel"
