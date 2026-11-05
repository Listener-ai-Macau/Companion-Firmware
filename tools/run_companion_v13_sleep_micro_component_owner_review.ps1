#requires -Version 7.0
[CmdletBinding()]
param(
    [switch]$DryRun,
    [ValidateRange(1, 840)]
    [int]$TimeoutSeconds = 840,
    [string]$WorkflowRepo = "",
    [string]$ResultPath = "docs\validation\companion-v9-extension-v13-sleep-micro-component-repair-owner-art-review-20260719.json",
    [string]$NotePath = "docs\validation\companion-v9-extension-v13-sleep-micro-component-repair-owner-art-review-20260719.note.txt",
    [string]$SummaryPath = "docs\validation\companion-v9-extension-v13-sleep-micro-component-repair-owner-art-review-summary-20260719.json"
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

$candidate = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-extension-v13-sleep-micro-component-repair\generated_pet_expression_extension_v13_sleep_micro_component_repair_candidate.png"
$reassembledPreview = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-extension-v13-sleep-micro-component-repair\candidate\reassembled-sleep-micro-component-source-contact.png"
$requestPath = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-extension-v13-sleep-micro-component-repair\generation-request.json"
$sourceGatePath = Join-Path $repoRoot "docs\validation\companion-v9-extension-v13-sleep-micro-component-repair-machine-20260719.json"
$exportGatePath = Join-Path $repoRoot "docs\validation\companion-v9-extension-v13-sleep-micro-component-repair-export-20260719.json"
$lockedSource = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9\generated_pet_expression_sheet_v9_candidate.png"
$protectedAcceptance = Join-Path $repoRoot "docs\validation\companion-pet-special-system-owner-acceptance-20260717.json"
foreach ($path in @($candidate, $reassembledPreview, $requestPath, $sourceGatePath, $exportGatePath,
        $lockedSource, $protectedAcceptance)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing V13 sleep review evidence: $path" }
}

$request = Get-Content -LiteralPath $requestPath -Raw | ConvertFrom-Json
$sourceGate = Get-Content -LiteralPath $sourceGatePath -Raw | ConvertFrom-Json
$exportGate = Get-Content -LiteralPath $exportGatePath -Raw | ConvertFrom-Json
$lockedHash = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
$protectedHash = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"
Require-Equal $request.status "MACHINE_SOURCE_COMPONENT_GATES_PASS_PENDING_OWNER_ART_REVIEW_V13_20260719" "V13 request status"
Require-Equal $sourceGate.status "PASS_V13_SLEEP_MICRO_COMPONENT_SOURCE_GATE" "V13 source gate"
Require-Equal $sourceGate.source_component_count 10 "V13 source component count"
Require-Equal $exportGate.status "PASS_V13_SLEEP_MICRO_COMPONENT_SOURCE_EXPORT_GATE" "V13 source-mask export gate"
Require-Equal $exportGate.component_count 10 "V13 export component count"
Require-Equal $sourceGate.runtime_resource_activated $false "V13 source gate runtime state"
Require-Equal $exportGate.runtime_resource_activated $false "V13 export gate runtime state"
Require-Equal $exportGate.active_candidate_binding "forbidden" "V13 active binding state"
Require-Equal (Get-FileHash -Algorithm SHA256 -LiteralPath $candidate).Hash.ToUpperInvariant() $request.generated_output.sha256 "V13 candidate hash"
Require-Equal (Get-FileHash -Algorithm SHA256 -LiteralPath $lockedSource).Hash.ToUpperInvariant() $lockedHash "Locked V9 source hash"
Require-Equal (Get-FileHash -Algorithm SHA256 -LiteralPath $protectedAcceptance).Hash.ToUpperInvariant() $protectedHash "Protected prior owner-acceptance hash"

$resultAbsolutePath = Join-Path $repoRoot $ResultPath
$noteAbsolutePath = Join-Path $repoRoot $NotePath
$summaryAbsolutePath = Join-Path $repoRoot $SummaryPath
$summary = [ordered]@{
    schema = "companion.v13_sleep_micro_component_owner_art_review_summary.v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    dry_run = [bool]$DryRun
    candidate = $candidate
    candidate_sha256 = $request.generated_output.sha256
    source_only_reassembly_preview = $reassembledPreview
    source_only_reassembly_preview_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $reassembledPreview).Hash.ToUpperInvariant()
    request = $requestPath
    source_gate = $sourceGatePath
    export_gate = $exportGatePath
    source_component_count = $sourceGate.source_component_count
    runtime_resource_activated = $false
    active_candidate_binding = "forbidden"
    sleep_runtime_restore = "forbidden_pending_owner_art_acceptance"
    locked_v9_sha256 = $lockedHash
    protected_prior_owner_acceptance_sha256 = $protectedHash
    prompt_style = "aiw_operator_prompt_v1"
}
if ($DryRun) {
    $summary.status = "READY_FOR_OWNER_V13_SLEEP_MICRO_COMPONENT_ART_REVIEW"
    Write-JsonFile $summary $summaryAbsolutePath
    Write-Output "READY_FOR_OWNER_V13_SLEEP_MICRO_COMPONENT_ART_REVIEW: $candidate"
    exit 0
}

Start-Process -FilePath $candidate
Start-Sleep -Milliseconds 600
Start-Process -FilePath $reassembledPreview
Start-Sleep -Seconds 2
$message = @"
请验收刚打开的两张 V13 睡眠美术证据：第一张是只引用锁定 V9 母图生成的单一完整睡眠源图；第二张是从同一张图拆出的 10 个登记组件重新组合后的 200x200 墨水屏构图。V12 已是拒绝证据，未参与这张图的参考或像素来源；当前 Sleep 仍 fail-closed，尚未绑定运行时。

重点看：它是否明确是非 Daily 的安静睡眠脸；闭眼、柔和眉、腮点、鼻子和小嘴是否仍为同一角色；两颗低于腮点、位于脸外侧的呼吸小圆点是否自然、克制且成对；是否没有月亮、弯月、Z 或任何头顶装饰。机器已证明这 10 个组件都来自同一张 V13 生图并能像素级重组；这不是整脸贴图动画。
"@
$expected = @"
通过：授权把这张 V13 源图作为 Sleep 的唯一新增组件来源；下一步才可做 source-only Rig 接入、逐相位防遮挡和浏览器/目标端机器预览，仍保持 runtime inactive。
需修改：V13 图和其组件导出均保留为拒绝证据，Sleep 继续 fail-closed；下一轮仍只引用锁定 V9 母图重新生成。
"@
$promptJsonText = & pwsh -NoProfile -File $aiw operator-prompt `
    -Title "Companion V13 睡眠组件美术验收" `
    -ProgressText "1/1" `
    -ScopeText "单一 V13 睡眠源图和 10 个来源组件重组；机器门通过；runtime inactive" `
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
    "通过" { $summary.status = "PASS_OWNER_V13_SLEEP_MICRO_COMPONENT_ART_REVIEW" }
    "需修改" { $summary.status = "FAIL_OWNER_V13_SLEEP_MICRO_COMPONENT_ART_REVIEW" }
    "跳过" { $summary.status = "SKIPPED_BY_OWNER" }
    "中止" { $summary.status = "ABORTED_BY_OWNER" }
    "Timeout" { $summary.status = "NO_OWNER_SELECTION_TIMEOUT" }
    default { $summary.status = "NO_OWNER_APPROVAL" }
}
Write-JsonFile $summary $summaryAbsolutePath
Write-Output ("{0}: selection={1}" -f $summary.status, $selection)
