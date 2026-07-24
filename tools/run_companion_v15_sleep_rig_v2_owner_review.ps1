#requires -Version 7.0
[CmdletBinding()]
param(
    [switch]$DryRun,
    [ValidateRange(1, 840)]
    [int]$TimeoutSeconds = 840,
    [string]$WorkflowRepo = "",
    [string]$ResultPath = "docs\validation\companion-v9-extension-v15-sleep-rig-v2-owner-review-20260719.json",
    [string]$NotePath = "docs\validation\companion-v9-extension-v15-sleep-rig-v2-owner-review-20260719.note.txt",
    [string]$SummaryPath = "docs\validation\companion-v9-extension-v15-sleep-rig-v2-owner-review-summary-20260719.json"
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

function Require-AtLeast {
    param([int]$Actual, [int]$Expected, [string]$Description)
    if ($Actual -lt $Expected) { throw "$Description must be at least $Expected but was $Actual." }
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

$v15Root = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-extension-v15-sleep-rig-pose-source"
$requestPath = Join-Path $v15Root "candidate\sleep-v15-component-choreography-v2-request.json"
$sourceContact = Join-Path $v15Root "candidate\component-export-attempt-01\normalized-source-pose-contact-sheet.png"
$preview = Join-Path $v15Root "candidate\dynamic-proof-attempt-02\preview.html"
$dynamicContact = Join-Path $v15Root "candidate\dynamic-proof-attempt-02\sleep-v15-dynamic-contact-sheet.png"
$dynamicApng = Join-Path $v15Root "candidate\dynamic-proof-attempt-02\sleep-v15-dynamic-preview.apng"
$sourcePreflightPath = Join-Path $repoRoot "docs\validation\companion-v9-extension-v15-sleep-rig-pose-request-preflight-20260719.json"
$sourceGatePath = Join-Path $repoRoot "docs\validation\companion-v9-extension-v15-sleep-rig-pose-attempt-01-20260719.json"
$componentExportPath = Join-Path $v15Root "candidate\component-export-attempt-01\export-report.json"
$dynamicGatePath = Join-Path $repoRoot "docs\validation\companion-v9-extension-v15-sleep-rig-component-choreography-v2-20260719.json"
$browserCapturePath = Join-Path $v15Root "candidate\dynamic-proof-attempt-02\browser-capture-report.json"
$lockedSource = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9\generated_pet_expression_sheet_v9_candidate.png"
$protectedAcceptance = Join-Path $repoRoot "docs\validation\companion-pet-special-system-owner-acceptance-20260717.json"
foreach ($path in @($requestPath, $sourceContact, $preview, $dynamicContact, $dynamicApng, $sourcePreflightPath, $sourceGatePath,
        $componentExportPath, $dynamicGatePath, $browserCapturePath, $lockedSource, $protectedAcceptance)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing V15 v2 owner-review evidence: $path" }
}

$request = Get-Content -LiteralPath $requestPath -Raw | ConvertFrom-Json
$sourcePreflight = Get-Content -LiteralPath $sourcePreflightPath -Raw | ConvertFrom-Json
$sourceGate = Get-Content -LiteralPath $sourceGatePath -Raw | ConvertFrom-Json
$componentExport = Get-Content -LiteralPath $componentExportPath -Raw | ConvertFrom-Json
$dynamicGate = Get-Content -LiteralPath $dynamicGatePath -Raw | ConvertFrom-Json
$browserCapture = Get-Content -LiteralPath $browserCapturePath -Raw | ConvertFrom-Json
$lockedHash = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
$protectedHash = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"
Require-Equal $request.schema "companion.v15_sleep_rig_component_choreography_request.v2" "V15 v2 choreography schema"
Require-Equal $request.status "MACHINE_DYNAMIC_PROOF_PASS_PENDING_OWNER_REVIEW" "V15 v2 choreography request status"
Require-Equal $request.runtime_resource_activated $false "V15 v2 request runtime state"
Require-Equal $request.active_candidate_binding "forbidden" "V15 v2 request binding state"
Require-Equal $sourcePreflight.status "PASS_V15_VERSIONED_PROMPT_PREFLIGHT" "V15 prompt preflight"
Require-Equal $sourceGate.status "PASS_V15_SLEEP_RIG_POSE_SOURCE_GATE" "V15 source gate"
Require-Equal $componentExport.status "PASS_V15_SOURCE_MASK_EXPORT" "V15 component export"
Require-Equal $dynamicGate.status "PASS_V15_UNBOUND_DYNAMIC_PROOF_GATE" "V15 v2 dynamic gate"
Require-Equal $dynamicGate.phase_count 7 "V15 v2 dynamic phase count"
Require-AtLeast ([int]$dynamicGate.motion_readability_audit.entry_to_first_visible_ms) 0 "V15 v2 first motion time"
if ([int]$dynamicGate.motion_readability_audit.entry_to_first_visible_ms -gt 1500) { throw "V15 v2 first visible motion exceeded 1500 ms." }
Require-AtLeast ([int]$dynamicGate.motion_readability_audit.response_difference_pixels) 300 "V15 v2 response difference"
Require-AtLeast ([int]$dynamicGate.motion_readability_audit.accent_difference_pixels) 300 "V15 v2 accent difference"
Require-AtLeast ([int]$dynamicGate.motion_readability_audit.breath_travel_px) 3 "V15 v2 breath travel"
Require-AtLeast ([int]$dynamicGate.motion_readability_audit.zzz_travel_px) 3 "V15 v2 zzz travel"
Require-Equal $browserCapture.status "PASS_V15_SLEEP_COMPONENT_CHOREOGRAPHY_BROWSER_CAPTURE" "V15 v2 browser evidence"
Require-Equal @($browserCapture.captures).Count 3 "V15 v2 browser capture count"
Require-Equal (Get-FileHash -Algorithm SHA256 -LiteralPath $lockedSource).Hash.ToUpperInvariant() $lockedHash "Locked V9 source hash"
Require-Equal (Get-FileHash -Algorithm SHA256 -LiteralPath $protectedAcceptance).Hash.ToUpperInvariant() $protectedHash "Protected prior owner-acceptance hash"

$resultAbsolutePath = Join-Path $repoRoot $ResultPath
$noteAbsolutePath = Join-Path $repoRoot $NotePath
$summaryAbsolutePath = Join-Path $repoRoot $SummaryPath
$summary = [ordered]@{
    schema = "companion.v15_sleep_rig_v2_owner_review_summary.v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    dry_run = [bool]$DryRun
    source_contact_sheet = $sourceContact
    source_contact_sheet_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourceContact).Hash.ToUpperInvariant()
    preview = $preview
    preview_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $preview).Hash.ToUpperInvariant()
    dynamic_contact_sheet = $dynamicContact
    dynamic_contact_sheet_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $dynamicContact).Hash.ToUpperInvariant()
    dynamic_apng = $dynamicApng
    dynamic_apng_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $dynamicApng).Hash.ToUpperInvariant()
    source_component_count = $componentExport.component_count
    phase_count = $dynamicGate.phase_count
    timeline_frame_count = 17
    motion_readability = $dynamicGate.motion_readability_audit
    runtime_resource_activated = $false
    active_candidate_binding = "forbidden"
    crig_mount = "forbidden"
    sleep_runtime_restore = "forbidden_pending_owner_acceptance"
    locked_v9_sha256 = $lockedHash
    protected_prior_owner_acceptance_sha256 = $protectedHash
    prompt_style = "aiw_operator_prompt_v1"
}
if ($DryRun) {
    $summary.status = "READY_FOR_OWNER_V15_SLEEP_RIG_V2_REVIEW"
    Write-JsonFile $summary $summaryAbsolutePath
    Write-Output "READY_FOR_OWNER_V15_SLEEP_RIG_V2_REVIEW: $preview"
    exit 0
}

Start-Process -FilePath $sourceContact
Start-Sleep -Milliseconds 700
Start-Process -FilePath $preview
Start-Sleep -Milliseconds 700
Start-Process -FilePath $dynamicApng
Start-Sleep -Milliseconds 700
Start-Process -FilePath $dynamicContact
Start-Sleep -Seconds 2
$message = @"
请验收刚打开的 V15 v2 睡眠组件动态证据。第二个窗口是可播放的预览；它按 17 个、每个 500ms 的组件合成时刻循环。浏览器和 200x200 PBM 使用同一份时间表，来源只允许 V15 生图导出的 15 个登记组件；没有播放完整姿态格，也没有 CRIG、active state 或 runtime 绑定。

重点请只看播放中的感觉：是否清楚看出同一张睡眠脸先轻微松眉，再做一次嘴/腮的呼吸回应；闭眼和鼻子是否稳定；近腮的一对呼吸线与一个紧凑 zzz 组是否统一地后随并回落；整体是否仍是一张完整角色脸，而不是整脸换图或一堆贴图各自轮播。
"@
$expected = @"
通过：确认 V15 同角色睡眠源和可见组件动态方向可继续；后续仍需独立 Sleep Rig 接入与机器门，不能直接 runtime 激活。
需修改：V15 v2 保留为拒绝候选，Sleep 继续 fail-closed；按备注重新修正美术源或组件轨道，不得回退到整脸贴图、多个漂浮贴纸或旧版本素材。
"@
$promptJsonText = & pwsh -NoProfile -File $aiw operator-prompt `
    -Title "Companion V15 v2 睡眠组件动态验收" `
    -ProgressText "1/1" `
    -ScopeText "V15 V9-only 来源、15 个登记组件、17 帧同计划浏览器/200x200 PBM；runtime inactive" `
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
$summary.status = if ($selection -eq "通过") { "PASS_OWNER_V15_SLEEP_RIG_V2_REVIEW" } elseif ($selection -eq "需修改") { "FAIL_OWNER_V15_SLEEP_RIG_V2_REVIEW" } else { "NO_OWNER_SELECTION" }
Write-JsonFile $summary $summaryAbsolutePath
Write-Output "$($summary.status): $preview"
