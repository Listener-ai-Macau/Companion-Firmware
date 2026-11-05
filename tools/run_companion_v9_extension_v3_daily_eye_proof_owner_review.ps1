#requires -Version 7.0
[CmdletBinding()]
param(
    [switch]$DryRun,
    [ValidateRange(1, 840)]
    [int]$TimeoutSeconds = 840,
    [string]$WorkflowRepo = "",
    [string]$ResultPath = "docs\\validation\\companion-v9-extension-v3-daily-eye-proof-owner-review-20260718.json",
    [string]$NotePath = "docs\\validation\\companion-v9-extension-v3-daily-eye-proof-owner-review-20260718.note.txt",
    [string]$SummaryPath = "docs\\validation\\companion-v9-extension-v3-daily-eye-proof-owner-review-summary-20260718.json"
)

$ErrorActionPreference = "Stop"

function Resolve-WorkflowRepo {
    param([string]$RequestedPath)
    foreach ($candidate in @($RequestedPath, $env:AI_WORKFLOW_REPO, "C:\\Users\\Billy\\Desktop\\Denzic\\ai-collaboration-workflow") |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) {
        $resolved = [System.IO.Path]::GetFullPath($candidate)
        if (Test-Path -LiteralPath (Join-Path $resolved "docs\\agent_quickstart.md")) { return $resolved }
    }
    throw "Unable to resolve AI workflow repository with docs\\agent_quickstart.md."
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
$aiw = Join-Path $workflowRoot "scripts\\aiw.ps1"
& pwsh -NoProfile -File (Join-Path $workflowRoot "scripts\\verify_pwsh7.ps1")
if ($LASTEXITCODE -ne 0) { throw "PowerShell 7 verification failed." }

$source = Join-Path $repoRoot "docs\\art\\iterations\\companion-pet-expression-v9\\generated_pet_expression_sheet_v9_candidate.png"
$candidate = Join-Path $repoRoot "docs\\art\\iterations\\companion-pet-expression-v9-extension-v3-daily-eye-proof\\generated_pet_expression_extension_v3_daily_eye_proof_candidate.png"
$requestPath = Join-Path $repoRoot "docs\\art\\iterations\\companion-pet-expression-v9-extension-v3-daily-eye-proof\\generation-request.json"
$lineagePath = Join-Path $repoRoot "docs\\validation\\companion-v9-art-lineage-machine-20260718.json"
$eyePath = Join-Path $repoRoot "docs\\validation\\companion-v9-extension-v3-daily-eye-proof-open-eye-identity-20260718.json"
$attentionPath = Join-Path $repoRoot "docs\\validation\\companion-v9-extension-v3-daily-eye-proof-attention-20260718.json"
$protected = Join-Path $repoRoot "docs\\validation\\companion-pet-special-system-owner-acceptance-20260717.json"
foreach ($path in @($source, $candidate, $requestPath, $lineagePath, $eyePath, $attentionPath, $protected)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing V3 owner-review evidence: $path" }
}

$lockedHash = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
$protectedHash = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"
$lineage = Get-Content -LiteralPath $lineagePath -Raw | ConvertFrom-Json
$request = Get-Content -LiteralPath $requestPath -Raw | ConvertFrom-Json
$eye = Get-Content -LiteralPath $eyePath -Raw | ConvertFrom-Json
$attention = Get-Content -LiteralPath $attentionPath -Raw | ConvertFrom-Json
Require-Equal $lineage.status "PASS_ART_LINEAGE" "Art lineage machine closure"
Require-Equal $request.status "MACHINE_ART_DIRECTION_PASS_PENDING_OWNER_REVIEW" "V3 request state"
Require-Equal $request.generated_output.status "machine_contract_pass_pending_owner_review" "V3 output state"
Require-Equal $eye.status "PASS_OPEN_EYE_IDENTITY_GATE" "V3 open-eye identity gate"
Require-Equal $attention.status "PASS_DAILY_ATTENTION_PROOF_GATE" "V3 daily attention gate"
Require-Equal (Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash.ToUpperInvariant() $lockedHash "Locked V9 source hash"
Require-Equal (Get-FileHash -Algorithm SHA256 -LiteralPath $protected).Hash.ToUpperInvariant() $protectedHash "Protected prior acceptance hash"
Require-Equal (Get-FileHash -Algorithm SHA256 -LiteralPath $candidate).Hash.ToUpperInvariant() $request.generated_output.sha256 "V3 candidate hash"

$resultAbsolutePath = Join-Path $repoRoot $ResultPath
$noteAbsolutePath = Join-Path $repoRoot $NotePath
$summaryAbsolutePath = Join-Path $repoRoot $SummaryPath
$summary = [ordered]@{
    schema = "companion.v9_extension_v3_daily_eye_proof_owner_review_summary.v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    dry_run = [bool]$DryRun
    candidate_path = $candidate
    candidate_sha256 = $request.generated_output.sha256
    source_sha256 = $lockedHash
    protected_prior_owner_acceptance_sha256 = $protectedHash
    lineage_report_path = $lineagePath
    open_eye_identity_report_path = $eyePath
    daily_attention_report_path = $attentionPath
    runtime_resource_activated = $false
    component_export = "forbidden"
    goal_complete = $false
    prompt_style = "aiw_operator_prompt_v1"
}
if ($DryRun) {
    $summary.status = "READY_FOR_OWNER_V3_DAILY_EYE_PROOF_REVIEW"
    Write-JsonFile $summary $summaryAbsolutePath
    Write-Output "READY_FOR_OWNER_V3_DAILY_EYE_PROOF_REVIEW: $candidate"
    exit 0
}

Start-Process -FilePath $candidate
Start-Sleep -Seconds 2
$message = @"
请验收刚打开的 V9 日常视线小样。它只测试同一双 V9 黑色竖椭圆眼睛在左、右、上、下四种注意方向上的可读性，不是新的完整情绪表，也没有进入 Rig、组件导出或设备运行时。

重点看：四格是否仍是同一角色、同一眼型；高光方向是否自然且能读出左右上下；整体是否比 V2 的空心/白环眼更干净、有灵气。若不通过，请在备注指出具体方向和想要的感觉。
"@
$expected = @"
通过：可把这套眼睛身份与日常视线规则作为下一轮逐步扩展情绪的唯一基线，但仍需新一轮版本化生图和组件门槛。
需修改：这四格只作为拒绝证据；下一轮仍从锁定 V9 母版生成，不能引用此图或 V1/V2 作为视觉参考。
"@
$promptJsonText = & pwsh -NoProfile -File $aiw operator-prompt `
    -Title "Companion V9 日常视线小样验收" `
    -ProgressText "1/1" `
    -ScopeText "仅 2x2 日常视线美术候选；机器门槛已通过；runtime inactive" `
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
    "通过" { $summary.status = "PASS_OWNER_V3_DAILY_EYE_PROOF_REVIEW" }
    "需修改" { $summary.status = "FAIL_OWNER_V3_DAILY_EYE_PROOF_REVIEW" }
    "跳过" { $summary.status = "SKIPPED_BY_OWNER" }
    "中止" { $summary.status = "ABORTED_BY_OWNER" }
    "Timeout" { $summary.status = "NO_OWNER_SELECTION_TIMEOUT" }
    default { $summary.status = "NO_OWNER_APPROVAL" }
}
Write-JsonFile $summary $summaryAbsolutePath
Write-Output ("{0}: selection={1}" -f $summary.status, $selection)
