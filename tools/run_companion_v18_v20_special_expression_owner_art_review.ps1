#requires -Version 7.0
[CmdletBinding()]
param(
    [switch]$DryRun,
    [ValidateRange(1, 840)]
    [int]$TimeoutSeconds = 840,
    [string]$WorkflowRepo = "",
    [string]$ResultPath = "docs\validation\companion-v18-v20-special-expression-owner-art-review-20260719.json",
    [string]$NotePath = "docs\validation\companion-v18-v20-special-expression-owner-art-review-20260719.note.txt",
    [string]$SummaryPath = "docs\validation\companion-v18-v20-special-expression-owner-art-review-summary-20260719.json"
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

$lockedSource = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9\generated_pet_expression_sheet_v9_candidate.png"
$machineGatePath = Join-Path $repoRoot "docs\validation\companion-v18-v20-special-expression-component-export-gate-20260719.json"
$reviewSheet = Join-Path $repoRoot "docs\validation\companion-v18-v20-special-expression-owner-art-review-sheet-20260719.png"
$reviewSheetReport = Join-Path $repoRoot "docs\validation\companion-v18-v20-special-expression-owner-art-review-sheet-20260719.json"
$lockedHash = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
$poses = @(
    [ordered]@{ Function = "Menu"; Version = "V18"; Iteration = "companion-pet-expression-v9-extension-v18-menu-special-expression-source"; Source = "attempt-01-generated-menu-special-expression.png"; Preview = "menu_active-source-component-reassembly-preview.png" },
    [ordered]@{ Function = "Recording"; Version = "V19"; Iteration = "companion-pet-expression-v9-extension-v19-recording-special-expression-source"; Source = "attempt-01-generated-recording-special-expression.png"; Preview = "recording_active-source-component-reassembly-preview.png" },
    [ordered]@{ Function = "Upgrade"; Version = "V20"; Iteration = "companion-pet-expression-v9-extension-v20-upgrade-special-expression-source"; Source = "attempt-01-generated-upgrade-special-expression.png"; Preview = "upgrade_active-source-component-reassembly-preview.png" }
)

if (-not (Test-Path -LiteralPath $lockedSource)) { throw "Missing locked V9 source: $lockedSource" }
Require-Equal (Get-FileHash -Algorithm SHA256 -LiteralPath $lockedSource).Hash.ToUpperInvariant() $lockedHash "Locked V9 source hash"
if (-not (Test-Path -LiteralPath $machineGatePath)) { throw "Missing V18-V20 component export gate." }
$machineGate = Get-Content -LiteralPath $machineGatePath -Raw | ConvertFrom-Json
Require-Equal $machineGate.status "PASS_V18_V20_COMPLETE_SPECIAL_EXPRESSION_COMPONENT_EXPORT_GATE" "V18-V20 component export machine gate"
& python (Join-Path $repoRoot "tools\render_companion_v18_v20_special_expression_review_sheet.py") `
    --output $reviewSheet --write $reviewSheetReport
if ($LASTEXITCODE -ne 0) { throw "Could not render V18-V20 owner-art review sheet." }
if (-not (Test-Path -LiteralPath $reviewSheet) -or -not (Test-Path -LiteralPath $reviewSheetReport)) {
    throw "Missing V18-V20 owner-art review sheet evidence."
}
$reviewSheetEvidence = Get-Content -LiteralPath $reviewSheetReport -Raw | ConvertFrom-Json
Require-Equal $reviewSheetEvidence.status "PASS_REVIEW_ONLY_CONTACT_SHEET" "V18-V20 review sheet"

$reviewEvidence = @()
foreach ($pose in $poses) {
    $root = Join-Path $repoRoot ("docs\art\iterations\" + $pose.Iteration)
    $source = Join-Path $root ("candidate\" + $pose.Source)
    $exportRoot = Join-Path $root "candidate\component-export-attempt-01"
    $preview = Join-Path $exportRoot $pose.Preview
    $layoutPath = Join-Path $exportRoot "complete-special-expression-component-layout.json"
    foreach ($path in @($source, $preview, $layoutPath)) {
        if (-not (Test-Path -LiteralPath $path)) { throw "Missing $($pose.Version) owner-art review evidence: $path" }
    }
    $layout = Get-Content -LiteralPath $layoutPath -Raw | ConvertFrom-Json
    Require-Equal $layout.status "UNBOUND_PENDING_OWNER_ART_REVIEW" "$($pose.Version) component layout"
    Require-Equal $layout.runtime_resource_activated $false "$($pose.Version) runtime state"
    Require-Equal $layout.active_candidate_binding "forbidden" "$($pose.Version) active candidate binding"
    if (@(Get-ChildItem -LiteralPath (Join-Path $root "candidate") -Recurse -File -Filter *.crig).Count -ne 0) {
        throw "$($pose.Version) must not contain a CRIG package before owner art acceptance."
    }
    $reviewEvidence += [ordered]@{
        function = $pose.Function
        version = $pose.Version
        source_pose = $source
        source_pose_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash.ToUpperInvariant()
        v9_identity_reassembly_preview = $preview
        v9_identity_reassembly_preview_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $preview).Hash.ToUpperInvariant()
        special_component_count = @($layout.special_expression_components.psobject.Properties).Count
    }
}

$resultAbsolutePath = Join-Path $repoRoot $ResultPath
$noteAbsolutePath = Join-Path $repoRoot $NotePath
$summaryAbsolutePath = Join-Path $repoRoot $SummaryPath
$summary = [ordered]@{
    schema = "companion.v18_v20_special_expression_owner_art_review_summary.v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    dry_run = [bool]$DryRun
    locked_v9_source = $lockedSource
    locked_v9_sha256 = $lockedHash
    machine_gate = $machineGatePath
    review_sheet = $reviewSheet
    review_sheet_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $reviewSheet).Hash.ToUpperInvariant()
    poses = $reviewEvidence
    active_candidate_binding = "forbidden"
    runtime_resource_activated = $false
    prompt_style = "aiw_operator_prompt_v1"
}
if ($DryRun) {
    $summary.status = "READY_FOR_OWNER_V18_V20_SPECIAL_EXPRESSION_ART_REVIEW"
    Write-JsonFile $summary $summaryAbsolutePath
    Write-Output "READY_FOR_OWNER_V18_V20_SPECIAL_EXPRESSION_ART_REVIEW: $machineGatePath"
    exit 0
}

Start-Process -FilePath $lockedSource
Start-Sleep -Milliseconds 700
Start-Process -FilePath $reviewSheet
Start-Sleep -Seconds 2
$message = @"
请验收刚打开的 V18/V19/V20 完整特殊表情源姿态。第一个窗口是锁定 V9 原始基线；第二个窗口把 Menu、Recording、Upgrade 各自的完整候选源姿态和对应 200x200 V9 身份重组并排在一张图中。右侧重组只取该姿态的眉、嘴、腮与功能细节，同时固定复用 V9 Rig v1 的眼睛/高光/星点/鼻子。

本轮确认的是同一角色的三种特殊表情：Menu 应读作安静的导航/思考，Recording 应读作专注聆听/捕捉，Upgrade 应读作平静、受控的系统进度。请看角色身份是否统一、特殊语义是否成立、细节是否克制，以及重组后是否仍是一张完整的脸。

它们是源姿态，不是运行时贴图：通过只允许继续做下一步“组件级动态编舞”的机器验证。不会播放整张脸、不会接入 V17 小组件、不会生成 CRIG 或激活 runtime；Menu/Recording/Upgrade 在后续绑定门完成前仍 fail-closed。
"@
$expected = @"
通过：三种完整特殊表情源姿态和 V9 身份重组的美术方向成立，允许继续做未绑定的组件级动态编舞机器验证；仍不得直接启用 runtime。
需修改：按备注为对应功能创建新的版本化 V9-only prompt 和源姿态；当前候选保持未绑定，不能借用日常脸、V17、整脸切换或代码符号替代。
"@
$promptJsonText = & pwsh -NoProfile -File $aiw operator-prompt `
    -Title "Companion V18-V20 完整特殊表情源姿态验收" `
    -ProgressText "1/1" `
    -ScopeText "Menu / Recording / Upgrade 完整源姿态；runtime inactive，未绑定" `
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
$summary.status = if ($selection -eq "通过") { "PASS_OWNER_V18_V20_SPECIAL_EXPRESSION_ART_REVIEW" } elseif ($selection -eq "需修改") { "FAIL_OWNER_V18_V20_SPECIAL_EXPRESSION_ART_REVIEW" } else { "NO_OWNER_SELECTION" }
Write-JsonFile $summary $summaryAbsolutePath
Write-Output "$($summary.status): $machineGatePath"
