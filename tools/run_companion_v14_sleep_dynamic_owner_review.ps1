#requires -Version 7.0
[CmdletBinding()]
param(
    [switch]$DryRun,
    [ValidateRange(1, 840)]
    [int]$TimeoutSeconds = 840,
    [string]$WorkflowRepo = "",
    [string]$ResultPath = "docs\validation\companion-v9-extension-v14-sleep-zzz-component-repair-dynamic-owner-review-20260719.json",
    [string]$NotePath = "docs\validation\companion-v9-extension-v14-sleep-zzz-component-repair-dynamic-owner-review-20260719.note.txt",
    [string]$SummaryPath = "docs\validation\companion-v9-extension-v14-sleep-zzz-component-repair-dynamic-owner-review-summary-20260719.json"
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
    $Value | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $Path -Encoding utf8
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot
$workflowRoot = Resolve-WorkflowRepo -RequestedPath $WorkflowRepo
$aiw = Join-Path $workflowRoot "scripts\aiw.ps1"
& pwsh -NoProfile -File (Join-Path $workflowRoot "scripts\verify_pwsh7.ps1")
if ($LASTEXITCODE -ne 0) { throw "PowerShell 7 verification failed." }

$dynamicRoot = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-extension-v14-sleep-zzz-component-repair\candidate\dynamic-proof"
$preview = Join-Path $dynamicRoot "preview.html"
$contactSheet = Join-Path $dynamicRoot "sleep-v14-dynamic-contact-sheet.png"
$dynamicRequestPath = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-extension-v14-sleep-zzz-component-repair\candidate\sleep-v14-dynamic-proof-request.json"
$layoutPath = Join-Path $dynamicRoot "sleep-v14-dynamic-layout.json"
$exportPath = Join-Path $dynamicRoot "export-report.json"
$machineGatePath = Join-Path $repoRoot "docs\validation\companion-v9-extension-v14-sleep-zzz-component-repair-dynamic-20260719.json"
$browserCapturePath = Join-Path $dynamicRoot "browser-capture-report.json"
$lockedSource = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9\generated_pet_expression_sheet_v9_candidate.png"
$protectedAcceptance = Join-Path $repoRoot "docs\validation\companion-pet-special-system-owner-acceptance-20260717.json"
foreach ($path in @($preview, $contactSheet, $dynamicRequestPath, $layoutPath, $exportPath, $machineGatePath,
        $browserCapturePath, $lockedSource, $protectedAcceptance)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing V14 dynamic review evidence: $path" }
}

$request = Get-Content -LiteralPath $dynamicRequestPath -Raw | ConvertFrom-Json
$layout = Get-Content -LiteralPath $layoutPath -Raw | ConvertFrom-Json
$export = Get-Content -LiteralPath $exportPath -Raw | ConvertFrom-Json
$machineGate = Get-Content -LiteralPath $machineGatePath -Raw | ConvertFrom-Json
$browserCapture = Get-Content -LiteralPath $browserCapturePath -Raw | ConvertFrom-Json
$lockedHash = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
$protectedHash = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"
Require-Equal $request.status "MACHINE_DYNAMIC_PROOF_PASS_PENDING_OWNER_REVIEW" "V14 dynamic request status"
Require-Equal $layout.status "CANDIDATE_UNBOUND_DYNAMIC_PROOF_PENDING_OWNER_REVIEW" "V14 dynamic layout status"
Require-Equal $layout.runtime_resource_activated $false "V14 dynamic layout runtime state"
Require-Equal $layout.active_candidate_binding "forbidden" "V14 dynamic layout binding state"
Require-Equal $layout.crig_mount "forbidden" "V14 dynamic layout CRIG state"
Require-Equal $export.status "PASS_V14_UNBOUND_DYNAMIC_PROOF_EXPORT" "V14 dynamic export"
Require-Equal $machineGate.status "PASS_V14_UNBOUND_DYNAMIC_PROOF_GATE" "V14 dynamic machine gate"
Require-Equal $machineGate.phase_count 7 "V14 dynamic phase count"
Require-Equal $machineGate.component_count 13 "V14 dynamic component count"
Require-Equal $browserCapture.status "PASS_V14_SLEEP_DYNAMIC_BROWSER_CAPTURE" "V14 dynamic browser evidence"
Require-Equal $browserCapture.runtime_resource_activated $false "V14 browser runtime state"
Require-Equal (Get-FileHash -Algorithm SHA256 -LiteralPath $lockedSource).Hash.ToUpperInvariant() $lockedHash "Locked V9 source hash"
Require-Equal (Get-FileHash -Algorithm SHA256 -LiteralPath $protectedAcceptance).Hash.ToUpperInvariant() $protectedHash "Protected prior owner-acceptance hash"

$resultAbsolutePath = Join-Path $repoRoot $ResultPath
$noteAbsolutePath = Join-Path $repoRoot $NotePath
$summaryAbsolutePath = Join-Path $repoRoot $SummaryPath
$summary = [ordered]@{
    schema = "companion.v14_sleep_dynamic_owner_review_summary.v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    dry_run = [bool]$DryRun
    preview = $preview
    preview_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $preview).Hash.ToUpperInvariant()
    contact_sheet = $contactSheet
    contact_sheet_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $contactSheet).Hash.ToUpperInvariant()
    dynamic_request = $dynamicRequestPath
    machine_gate = $machineGatePath
    browser_capture = $browserCapturePath
    source_component_count = 13
    phase_count = 7
    runtime_resource_activated = $false
    active_candidate_binding = "forbidden"
    crig_mount = "forbidden"
    sleep_runtime_restore = "forbidden_pending_owner_dynamic_acceptance"
    locked_v9_sha256 = $lockedHash
    protected_prior_owner_acceptance_sha256 = $protectedHash
    prompt_style = "aiw_operator_prompt_v1"
}
if ($DryRun) {
    $summary.status = "READY_FOR_OWNER_V14_SLEEP_DYNAMIC_REVIEW"
    Write-JsonFile $summary $summaryAbsolutePath
    Write-Output "READY_FOR_OWNER_V14_SLEEP_DYNAMIC_REVIEW: $preview"
    exit 0
}

Start-Process -FilePath $preview
Start-Sleep -Milliseconds 700
Start-Process -FilePath $contactSheet
Start-Sleep -Seconds 2
$message = @"
请验收刚打开的两份 V14 睡眠动态证据：第一份是可播放的组件层预览，第二份是同一相位计划在 200x200 墨水屏 PBM 上的七相联系表。所有画面都只由同一张 V14 生图拆出的 13 个登记掩码组合；当前没有 CRIG、active state 或 runtime 绑定。

重点看：两颗下方呼吸点是否克制而同步；三颗右上 `Z` 是否按小到大、向外上方浮起再回落，且始终不压住脸；眉、闭眼、鼻嘴的一像素呼吸是否安静自然；整个节奏是否比静态图更有生命感，而不是整脸切换或三帧循环。浏览器和目标 PBM 已被机器证明使用同一相位计划。
"@
$expected = @"
通过：确认 V14 的 source-only 七相动态证明方向可继续；下一步才可做独立的 Sleep Rig 接入和机器门，仍不得直接 runtime 激活。
需修改：V14 保留为拒绝的动态证明，Sleep 继续 fail-closed；根据备注修正组件级编舞，不得回退到整脸贴图或旧版本素材。
"@
$promptJsonText = & pwsh -NoProfile -File $aiw operator-prompt `
    -Title "Companion V14 睡眠动态组件验收" `
    -ProgressText "1/1" `
    -ScopeText "V14 13 个来源掩码、七相组件编舞、浏览器与 200x200 PBM 同计划；runtime inactive" `
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
$summary.operator_note_present = (Test-Path -LiteralPath $noteAbsolutePath) -and -not [string]::IsNullOrWhiteSpace((Get-Content -LiteralPath $noteAbsolutePath -Raw))
switch ($selection) {
    "通过" { $summary.status = "PASS_OWNER_V14_SLEEP_DYNAMIC_REVIEW" }
    "需修改" { $summary.status = "FAIL_OWNER_V14_SLEEP_DYNAMIC_REVIEW" }
    "跳过" { $summary.status = "SKIPPED_BY_OWNER" }
    "中止" { $summary.status = "ABORTED_BY_OWNER" }
    "Timeout" { $summary.status = "NO_OWNER_SELECTION_TIMEOUT" }
    default { $summary.status = "NO_OWNER_APPROVAL" }
}
Write-JsonFile $summary $summaryAbsolutePath
Write-Output ("{0}: selection={1}" -f $summary.status, $selection)
