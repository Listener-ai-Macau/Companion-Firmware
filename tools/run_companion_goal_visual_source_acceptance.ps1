#requires -Version 7.0
<#
.SYNOPSIS
Runs one G2 Companion visual-source acceptance item from its manifest card.

.DESCRIPTION
CheckOnly and SelfTest never open a prompt. Execute requires explicit owner-start
acknowledgement and records a result beside the reviewed source evidence. It never
imports PBM/CEMP, writes Flash, flashes firmware, or changes a manifest decision.
#>

param(
    [ValidateSet("menu-v6-four-root", "special-system-v1", "special-journey-v1")]
    [string] $ItemId = "menu-v6-four-root",
    [ValidateRange(1, 16)]
    [int] $ArtifactIndex = 1,
    [switch] $CheckOnly,
    [switch] $Execute,
    [switch] $SelfTest,
    [switch] $OwnerStartAcknowledged,
    [ValidateSet("通过", "失败", "跳过", "中止")]
    [string] $SelfTestSelection = "通过",
    [ValidateRange(60, 3600)]
    [int] $OperatorTimeoutSeconds = 900,
    [string] $OutRoot = "docs\\validation\\companion-g2-owner-visual-reviews"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$manifestPath = Join-Path $repoRoot "docs\validation\companion-ui-visual-acceptance-manifest-20260717.json"
$readinessVerifier = Join-Path $PSScriptRoot "verify_companion_ui_visual_acceptance_readiness.py"
$orderedIds = @("menu-v6-four-root", "special-system-v1", "special-journey-v1")
$promptFields = @("target", "operator_action", "success_signal", "failure_rule", "continue_condition", "recovery_condition", "record_fields")

function Resolve-WorkflowAiwPath {
    $roots = @()
    if ($env:AI_WORKFLOW_REPO) {
        $roots += $env:AI_WORKFLOW_REPO
    }
    $roots += "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow"
    foreach ($root in $roots | Select-Object -Unique) {
        if ([string]::IsNullOrWhiteSpace($root)) {
            continue
        }
        $candidate = Join-Path $root "scripts\aiw.ps1"
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    throw "Canonical aiw operator-prompt helper was not found."
}

function Get-RelativePath {
    param([Parameter(Mandatory = $true)][string] $Path)

    return [System.IO.Path]::GetRelativePath($repoRoot, [System.IO.Path]::GetFullPath($Path)).Replace("\", "/")
}

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string] $Path)

    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
}

function Join-Lines {
    param([string[]] $Lines)

    return ($Lines -join [Environment]::NewLine)
}

function Build-OperatorSpec {
    param(
        [Parameter(Mandatory = $true)] $Item,
        [Parameter(Mandatory = $true)][int] $Position,
        [Parameter(Mandatory = $true)] $Artifact,
        [Parameter(Mandatory = $true)][int] $ArtifactCount
    )

    $card = $Item.operator_prompt
    $successLines = @($card.success_signal | ForEach-Object -Begin { $index = 0 } -Process {
        $index += 1
        "$index. $_"
    })
    $recordFields = @($card.record_fields | ForEach-Object { "- $_" })
    $displayName = switch ([string]$Item.id) {
        "menu-v6-four-root" { "四根菜单视觉源" }
        "special-system-v1" { "特殊系统状态视觉源" }
        "special-journey-v1" { "特殊旅程状态视觉源" }
        default { [string]$Item.id }
    }
    return [ordered]@{
        title = "Companion 视觉源验收 $Position/3 · 原图 $($Artifact.index)/$ArtifactCount：$displayName"
        progress_text = "$Position/3 · 图 $($Artifact.index)/$ArtifactCount（本次 1/1）"
        scope_text = "G2 顺序视觉源决定；已在系统图片查看器打开本张原图。当前只审这一张原图与对应 200x200 预览，不会导入 PBM/CEMP、写 Flash、刷固件或启用运行时资源。"
        message = Join-Lines @(
            "当前原图 $($Artifact.index)/$ArtifactCount：$($Artifact.label)",
            "文件：$($Artifact.path)",
            "",
            "目标：$($card.target)",
            "",
            "请这样检查：$($card.operator_action)",
            "",
            "通过信号：",
            $successLines,
            "",
            "失败规则：$($card.failure_rule)"
        )
        expected_text = Join-Lines @(
            "选择 '通过' 仅记录本项视觉源决定：$($card.continue_condition)",
            "",
            "失败后的处理：$($card.recovery_condition)",
            "",
            "备注至少记录：",
            $recordFields
        )
        observation_label = "备注（可留空；失败时必须写状态/行号与可见问题，通过时也可记录细节）"
    }
}

function Test-ArtifactAccepted {
    param(
        [Parameter(Mandatory = $true)][string] $ReviewRoot,
        [Parameter(Mandatory = $true)][string] $ReviewItemId,
        [Parameter(Mandatory = $true)] $Artifact
    )

    if (-not (Test-Path -LiteralPath $ReviewRoot -PathType Container)) {
        return $false
    }
    foreach ($path in Get-ChildItem -LiteralPath $ReviewRoot -Recurse -File -Filter "operator-review.json" -ErrorAction SilentlyContinue) {
        try {
            $record = Get-Content -LiteralPath $path.FullName -Raw | ConvertFrom-Json
        } catch {
            continue
        }
        if ($record.schema -ne "companion.g2_visual_artifact_operator_review.v1") {
            continue
        }
        if ($record.item_id -ne $ReviewItemId -or $record.artifact.index -ne $Artifact.index -or $record.artifact.sha256 -ne $Artifact.sha256) {
            continue
        }
        if ($record.operator_result.selected -eq "通过" -and [string]::IsNullOrWhiteSpace([string]$record.operator_result.note) -and $record.execution.canonical_aiw_operator_prompt_opened -eq $true) {
            return $true
        }
    }
    return $false
}

function Write-ReviewRecord {
    param(
        [Parameter(Mandatory = $true)] $Item,
        [Parameter(Mandatory = $true)] $Artifact,
        [Parameter(Mandatory = $true)] $Spec,
        [Parameter(Mandatory = $true)] $Result,
        [Parameter(Mandatory = $true)][string] $RecordPath,
        [Parameter(Mandatory = $true)][string] $NotePath,
        [Parameter(Mandatory = $true)][bool] $PromptOpened,
        [Parameter(Mandatory = $true)][bool] $OriginalImageOpened,
        [Parameter(Mandatory = $true)][bool] $SelfTestMode
    )

    $selection = [string]$Result.selected
    $status = switch ($selection) {
        "通过" { "OWNER_ARTIFACT_SELECTION_CAPTURED_TRIAGE_REQUIRED" }
        "失败" { "OWNER_ARTIFACT_REJECTION_CAPTURED_TRIAGE_REQUIRED" }
        default { "OWNER_ARTIFACT_REVIEW_NOT_DECIDED" }
    }
    $record = [ordered]@{
        schema = "companion.g2_visual_artifact_operator_review.v1"
        status = $status
        recorded_at = (Get-Date).ToString("o")
        item_id = [string]$Item.id
        source_sha256 = [string]$Item.source_sha256
        machine_evidence = [string]$Item.machine_evidence
        artifact = $Artifact
        operator_prompt = $Item.operator_prompt
        rendered_prompt = $Spec
        operator_result = [ordered]@{
            selected = $selection
            note = [string]$Result.text
            note_path = Get-RelativePath -Path $NotePath
        }
        execution = [ordered]@{
            canonical_aiw_operator_prompt_opened = $PromptOpened
            original_image_opened = $OriginalImageOpened
            self_test = $SelfTestMode
            owner_start_acknowledged = $OwnerStartAcknowledged.IsPresent
        }
        boundary = [ordered]@{
            manifest_owner_decision_changed = $false
            pbm_imported = $false
            cemp_packed = $false
            external_flash_provisioned = $false
            firmware_flashed = $false
            runtime_resource_activated = $false
        }
        next_step = "Agent must triage this result before changing the manifest decision or opening another G2 item."
    }
    $record | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $RecordPath -Encoding UTF8
}

$selectedModes = @($CheckOnly.IsPresent, $Execute.IsPresent, $SelfTest.IsPresent)
$modeCount = @($selectedModes | Where-Object { $_ }).Count
if ($modeCount -ne 1) {
    throw "Use exactly one of -CheckOnly, -Execute, or -SelfTest."
}
if ($Execute -and -not $OwnerStartAcknowledged) {
    throw "Refusing to open a G2 operator prompt until the owner explicitly says 开始验收 and -OwnerStartAcknowledged is supplied."
}
foreach ($path in @($manifestPath, $readinessVerifier)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required acceptance artifact is missing: $path"
    }
}

& python $readinessVerifier
if ($LASTEXITCODE -ne 0) {
    throw "Visual acceptance readiness is not machine-ready."
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
$reviewRoot = if ($SelfTest) {
    Join-Path $repoRoot ".cache\selftests\companion-g2-visual-source-review\runs\$stamp"
} elseif ([System.IO.Path]::IsPathRooted($OutRoot)) {
    [System.IO.Path]::GetFullPath($OutRoot)
} else {
    [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutRoot))
}

$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$items = @($manifest.items)
$manifestIds = @($items | ForEach-Object { [string]$_.id })
if (($manifestIds -join "|") -ne ($orderedIds -join "|")) {
    throw "Visual acceptance manifest order drifted."
}
$item = @($items | Where-Object { $_.id -eq $ItemId })
if ($item.Count -ne 1) {
    throw "Visual acceptance item was not found exactly once: $ItemId"
}
$item = $item[0]
$pending = @($items | Where-Object { $_.owner_decision -eq "PENDING_OWNER_VISUAL_DECISION" })
if ($pending.Count -eq 0) {
    throw "No pending G2 item remains; do not reopen a completed visual-source review."
}
if ([string]$pending[0].id -ne $ItemId) {
    throw "G2 is sequential: the next eligible item is $($pending[0].id), not $ItemId."
}
foreach ($field in $promptFields) {
    if (-not $item.operator_prompt.$field) {
        throw "Visual acceptance item $ItemId is missing operator prompt field: $field"
    }
}
$artifactReview = $item.artifact_review
if ($artifactReview.mode -ne "original_image_one_at_a_time") {
    throw "Visual acceptance item $ItemId must retain original-image review mode."
}
$images = @($artifactReview.images)
if ($images.Count -eq 0) {
    throw "Visual acceptance item $ItemId has no original images to review."
}
for ($index = 0; $index -lt $images.Count; $index += 1) {
    $image = $images[$index]
    if ($image.index -ne ($index + 1) -or [string]::IsNullOrWhiteSpace([string]$image.path) -or [string]::IsNullOrWhiteSpace([string]$image.sha256)) {
        throw "Visual acceptance item $ItemId original-image metadata is invalid at index $($index + 1)."
    }
    $imagePath = Join-Path $repoRoot ([string]$image.path)
    if (-not (Test-Path -LiteralPath $imagePath -PathType Leaf) -or (Get-Sha256 -Path $imagePath) -ne $image.sha256) {
        throw "Visual acceptance item $ItemId original image hash drifted: $($image.path)"
    }
}
$nextArtifactIndex = 1
foreach ($image in $images) {
    if (Test-ArtifactAccepted -ReviewRoot $reviewRoot -ReviewItemId $ItemId -Artifact $image) {
        $nextArtifactIndex += 1
        continue
    }
    break
}
if ($nextArtifactIndex -gt $images.Count) {
    throw "All original images for $ItemId already have no-note pass records; triage the group decision before opening another G2 item."
}
if ($ArtifactIndex -ne $nextArtifactIndex) {
    throw "Original images are sequential: the next eligible image is $nextArtifactIndex/$($images.Count), not $ArtifactIndex/$($images.Count)."
}
$artifact = $images[$ArtifactIndex - 1]
$artifactPath = Join-Path $repoRoot ([string]$artifact.path)
$position = [array]::IndexOf($orderedIds, $ItemId) + 1
$spec = Build-OperatorSpec -Item $item -Position $position -Artifact $artifact -ArtifactCount $images.Count

if ($CheckOnly) {
    Write-Output "CHECK: G2 item=$ItemId position=$position/3 original_image=$ArtifactIndex/$($images.Count)"
    Write-Output "CHECK: Canonical operator prompt=$(Resolve-WorkflowAiwPath)"
    Write-Output "CHECK: Source SHA256=$($item.source_sha256)"
    Write-Output "CHECK: Machine evidence=$($item.machine_evidence)"
    Write-Output "CHECK: Original image=$($artifact.path) sha256=$($artifact.sha256)"
    Write-Output "CHECK: No image viewer or operator prompt is opened; use -Execute -OwnerStartAcknowledged only after the owner says 开始验收."
    exit 0
}

$reviewDir = Join-Path $reviewRoot "$stamp-$ItemId-artifact$ArtifactIndex"
$notePath = Join-Path $reviewDir "operator-note.txt"
$recordPath = Join-Path $reviewDir "operator-review.json"
New-Item -ItemType Directory -Force -Path $reviewDir | Out-Null

if ($SelfTest) {
    $result = [pscustomobject][ordered]@{
        selected = $SelfTestSelection
        text = "SELFTEST: $SelfTestSelection"
    }
    Set-Content -LiteralPath $notePath -Value $result.text -Encoding UTF8
    Write-ReviewRecord -Item $item -Artifact $artifact -Spec $spec -Result $result -RecordPath $recordPath -NotePath $notePath -PromptOpened $false -OriginalImageOpened $false -SelfTestMode $true
    Write-Output "PASS: G2 original-image runner self-test -> $(Get-RelativePath -Path $recordPath)"
    exit 0
}

$null = Start-Process -FilePath $artifactPath -PassThru
Start-Sleep -Milliseconds 500
$aiw = Resolve-WorkflowAiwPath
$promptOutput = & pwsh -NoProfile -File $aiw operator-prompt `
    -Title $spec.title `
    -ProgressText $spec.progress_text `
    -ScopeText $spec.scope_text `
    -Message $spec.message `
    -ExpectedText $spec.expected_text `
    -ObservationLabel $spec.observation_label `
    -ReviewStyle -Input -Buttons "通过,失败,跳过,中止" `
    -OutputPath $notePath -TimeoutSeconds $OperatorTimeoutSeconds -Json
if ($LASTEXITCODE -ne 0) {
    throw "Canonical operator prompt failed with exit code $LASTEXITCODE."
}
try {
    $result = ($promptOutput -join [Environment]::NewLine) | ConvertFrom-Json
} catch {
    throw "Canonical operator prompt returned malformed JSON: $($_.Exception.Message)"
}
if ([string]::IsNullOrWhiteSpace([string]$result.selected)) {
    throw "Canonical operator prompt returned no selected button."
}
Write-ReviewRecord -Item $item -Artifact $artifact -Spec $spec -Result $result -RecordPath $recordPath -NotePath $notePath -PromptOpened $true -OriginalImageOpened $true -SelfTestMode $false
Write-Output "RESULT: G2 original-image review -> $(Get-RelativePath -Path $recordPath)"
