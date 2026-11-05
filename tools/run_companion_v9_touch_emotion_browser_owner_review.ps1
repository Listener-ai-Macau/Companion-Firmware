#requires -Version 7.0
[CmdletBinding()]
param(
    [switch]$DryRun,
    [ValidateRange(1, 840)]
    [int]$TimeoutSeconds = 840,
    [string]$WorkflowRepo = "",
    [string]$ResultPath = "docs\validation\companion-v9-rig-touch-emotion-browser-owner-review-20260720.json",
    [string]$NotePath = "docs\validation\companion-v9-rig-touch-emotion-browser-owner-review-20260720.note.txt"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $repoRoot

function Resolve-WorkflowRepo {
    param([string]$Requested)

    $candidate = if (-not [string]::IsNullOrWhiteSpace($Requested)) {
        $Requested
    } elseif (-not [string]::IsNullOrWhiteSpace($env:AI_WORKFLOW_REPO)) {
        $env:AI_WORKFLOW_REPO
    } else {
        "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $candidate "docs\agent_quickstart.md"))) {
        $candidate = "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $candidate "docs\agent_quickstart.md"))) {
        throw "Cannot resolve ai-collaboration-workflow repo with docs\agent_quickstart.md."
    }
    return (Resolve-Path -LiteralPath $candidate).Path
}

function Get-JsonFile {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) { throw "Missing review evidence: $Path" }
    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Write-JsonFile {
    param([string]$Path, [object]$Value)

    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    $Value | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $Path -Encoding UTF8
}

$workflow = Resolve-WorkflowRepo -Requested $WorkflowRepo
$closurePath = "docs\validation\companion-v9-rig-touch-emotion-machine-closure-20260720.json"
$previewPath = "docs\validation\companion-v9-rig-touch-emotion-machine-preview-20260719.json"
$parityPath = "docs\validation\companion-v9-rig-touch-emotion-machine-parity-20260719.json"
$baselinePath = "docs\validation\companion-v9-rig-touch-emotion-browser-accepted-baseline-20260720.json"
$baselineArtifactDir = "docs\validation\artifacts\companion-v9-rig-touch-emotion-browser-accepted-baseline-20260720"
$closure = Get-JsonFile -Path $closurePath
$preview = Get-JsonFile -Path $previewPath
$parity = Get-JsonFile -Path $parityPath

if ($closure.status -ne "PASS_TOUCH_EMOTION_MACHINE_CLOSURE_RUNTIME_INACTIVE") {
    throw "Touch/emotion machine closure is not PASS: $($closure.status)"
}
if ($preview.status -ne "PASS_BROWSER_COMPONENT_PREVIEW_FROM_TARGET_TRACE" -or
    $preview.runtime_resource_activated -ne $false) {
    throw "Browser preview is not a runtime-inactive PASS."
}
if ($parity.status -ne "PASS_TOUCH_EMOTION_BROWSER_TARGET_PARITY_RUNTIME_INACTIVE") {
    throw "Browser/target parity is not PASS."
}
$playerRelative = [string]$preview.browser_player.path
$playerPath = Join-Path $repoRoot $playerRelative
if (-not (Test-Path -LiteralPath $playerPath)) { throw "Browser component player is missing: $playerRelative" }
$playerHash = (Get-FileHash -LiteralPath $playerPath -Algorithm SHA256).Hash.ToUpperInvariant()
if ($playerHash -ne [string]$preview.browser_player.sha256) {
    throw "Browser component player hash differs from its machine preview record."
}

if ($DryRun) {
    [ordered]@{
        schema = "companion.v9_rig_touch_emotion_browser_owner_review_dry_run.v1"
        status = "PASS_READY_FOR_BROWSER_ONLY_OWNER_REVIEW"
        closure = $closurePath
        preview = $previewPath
        parity = $parityPath
        browser_player = $playerRelative
        browser_player_sha256 = $playerHash
        result_path = $ResultPath
        note_path = $NotePath
        runtime_resource_activated = $false
        physical_panel_acceptance = $false
        prompt_would_launch = $false
    } | ConvertTo-Json -Depth 8
    exit 0
}

& pwsh -NoProfile -File (Join-Path $workflow "scripts\verify_pwsh7.ps1")
if ($LASTEXITCODE -ne 0) { throw "PowerShell 7 verification failed before owner review." }
$playerUri = "file:///" + ((Resolve-Path -LiteralPath $playerPath).Path -replace "\\", "/")
Start-Process -FilePath $playerUri
Start-Sleep -Seconds 2

$message = @"
已打开浏览器组件 player。请点击 Play，让一次完整触摸编舞自然结束。

验收范围仅是电脑侧 V9 组件级动态预览，候选仍 runtime inactive，不是物理墨水屏验收。

本次复验已修正上一轮的风格断裂：未验收的 question 特殊脸已解除绑定，画面始终保持已确认的 V9 Daily 视觉语法。触摸仍是因果输入，但在没有完整、经过美术确认的专用姿态前，不把新特殊脸伪装成完成品。

重点判断：高光先对右侧触摸做注意反应，眉、嘴鼻、腮点和小挂件随后回应；然后是否自然走到 curious，再到 affectionate，最后 calm。它必须始终像同一个 V9 角色，不能像整脸贴图轮播、PPT、旧工程脸或随机切换。
"@
$expected = @"
选择通过：这条浏览器预览可冻结为 V9 触摸情绪组件编舞的回归基线。
选择需修改：在备注中写出具体帧、部件或节奏问题；该结果会阻止基线冻结并回到编舞修复。
"@
$aiw = Join-Path $workflow "scripts\aiw.ps1"
$promptJsonText = & pwsh -NoProfile -File $aiw operator-prompt `
    -Title "Companion V9 触摸情绪组件编舞验收" `
    -ProgressText "1/1 浏览器组件预览" `
    -ScopeText "V9 同源组件 Rig；浏览器专用；非物理屏；runtime inactive" `
    -Message $message `
    -ExpectedText $expected `
    -Input `
    -ReviewStyle `
    -OutputPath $NotePath `
    -TimeoutSeconds $TimeoutSeconds `
    -Json
if ($LASTEXITCODE -ne 0) { throw "Canonical operator-prompt failed with exit code $LASTEXITCODE." }

$promptResult = $promptJsonText | ConvertFrom-Json
$note = if (Test-Path -LiteralPath $NotePath) { Get-Content -LiteralPath $NotePath -Raw } else { "" }
$accepted = $promptResult.selected -eq "通过"
$record = [ordered]@{
    schema = "companion.v9_rig_touch_emotion_browser_owner_review.v1"
    status = if ($accepted) { "PASS_OWNER_TOUCH_EMOTION_BROWSER_PREVIEW_ACCEPTED_RUNTIME_INACTIVE" } else { "FAIL_OWNER_TOUCH_EMOTION_BROWSER_PREVIEW_REVIEW" }
    selected = $promptResult.selected
    operator_note = $note
    closure = [ordered]@{ path = $closurePath; sha256 = (Get-FileHash -LiteralPath $closurePath -Algorithm SHA256).Hash.ToUpperInvariant() }
    preview = [ordered]@{ path = $previewPath; sha256 = (Get-FileHash -LiteralPath $previewPath -Algorithm SHA256).Hash.ToUpperInvariant() }
    parity = [ordered]@{ path = $parityPath; sha256 = (Get-FileHash -LiteralPath $parityPath -Algorithm SHA256).Hash.ToUpperInvariant() }
    browser_player = [ordered]@{ path = $playerRelative; sha256 = $playerHash }
    source_sha256 = $preview.source_sha256
    runtime_resource_activated = $false
    physical_panel_acceptance = $false
    physical_dynamic_flash_authorized = $false
    special_state_fallback = "fail_closed"
    accepted_regression_baseline = $null
}
Write-JsonFile -Path $ResultPath -Value $record

if ($accepted) {
    & python tools\promote_companion_v9_touch_emotion_browser_baseline.py `
        --closure $closurePath `
        --preview $previewPath `
        --parity $parityPath `
        --owner-review $ResultPath `
        --write $baselinePath `
        --artifact-dir $baselineArtifactDir
    if ($LASTEXITCODE -ne 0) { throw "Accepted browser preview baseline promotion failed." }
    $baseline = Get-JsonFile -Path $baselinePath
    $record.accepted_regression_baseline = [ordered]@{
        path = $baselinePath
        sha256 = (Get-FileHash -LiteralPath $baselinePath -Algorithm SHA256).Hash.ToUpperInvariant()
        status = $baseline.status
    }
    Write-JsonFile -Path $ResultPath -Value $record
}

Write-Output "TOUCH_EMOTION_BROWSER_OWNER_REVIEW=$($record.status)"
