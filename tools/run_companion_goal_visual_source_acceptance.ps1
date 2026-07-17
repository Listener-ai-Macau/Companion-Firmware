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
    [ValidatePattern("^[a-z0-9-]+$")]
    [string] $ItemId = "home-v9-daily-storyboard",
    [ValidateRange(1, 128)]
    [int] $ArtifactIndex = 1,
    [switch] $CheckOnly,
    [switch] $Execute,
    [switch] $SelfTest,
    [switch] $OwnerStartAcknowledged,
    [ValidateSet("已执行", "需修改", "跳过", "中止")]
    [string] $SelfTestSelection = "已执行",
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

function Format-ReviewValue {
    param([Parameter(Mandatory = $false)] $Value)

    if ($null -eq $Value) {
        return ""
    }
    if ($Value -is [System.Array]) {
        return (($Value | ForEach-Object { [string]$_ }) -join "、")
    }
    if ($Value -is [System.Management.Automation.PSCustomObject]) {
        return ($Value | ConvertTo-Json -Compress -Depth 8)
    }
    return [string]$Value
}

function Build-OperatorSpec {
    param(
        [Parameter(Mandatory = $true)] $Item,
        [Parameter(Mandatory = $true)][int] $Position,
        [Parameter(Mandatory = $true)][int] $ItemCount,
        [Parameter(Mandatory = $true)] $Artifact,
        [Parameter(Mandatory = $true)][int] $ArtifactCount
    )

    $card = $Item.operator_prompt
    $successLines = @($card.success_signal | ForEach-Object -Begin { $index = 0 } -Process {
        $index += 1
        "$index. $_"
    })
    $recordFields = @($card.record_fields | ForEach-Object { "- $_" })
    $contextLines = @()
    if ($null -ne $Artifact.context) {
        foreach ($property in $Artifact.context.PSObject.Properties) {
            $value = Format-ReviewValue -Value $property.Value
            if (-not [string]::IsNullOrWhiteSpace($value)) {
                $contextLines += "$($property.Name)：$value"
            }
        }
    }
    $displayName = if ([string]::IsNullOrWhiteSpace([string]$Item.display_name)) { [string]$Item.id } else { [string]$Item.display_name }
    return [ordered]@{
        title = "Companion 电脑端美术对照验收 $Position/$ItemCount · 图 $($Artifact.index)/$ArtifactCount：$displayName"
        progress_text = "$Position/$ItemCount · 基线/输出 $($Artifact.index)/$ArtifactCount（本次 1/1）"
        scope_text = "G2 电脑端美术对照观察；系统图片查看器已打开左侧锁定生图基线与右侧 200x200 电脑端输出。本页不是开发板上的电子纸实物屏，不能证明方向、裁切、残影、刷新或触控。当前不会导入 PBM/CEMP、写 Flash、刷固件或启用运行时资源。"
        message = Join-Lines @(
            "当前对照 $($Artifact.index)/$ArtifactCount：$($Artifact.label)",
            "基线：$($Artifact.comparison.baseline.path)",
            "电脑输出：$($Artifact.comparison.desktop_output.path)",
            "机器关系：$($Artifact.comparison.relation) / $($Artifact.comparison.machine_result.status)",
            "对照页：$($Artifact.comparison.comparison_page.path)",
            $(if ($contextLines.Count -gt 0) { ""; "本页语义："; $contextLines }),
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
            "选择 已执行 仅记录本页观察：$($card.continue_condition)",
            "",
            "失败后的处理：$($card.recovery_condition)",
            "",
            "备注至少记录：",
            $recordFields
        )
        observation_label = "备注（可留空；选择 需修改 时必须写状态/行号与可见问题，选择 已执行 时也可记录细节）"
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
        if ($record.artifact.PSObject.Properties.Name -notcontains "comparison") {
            continue
        }
        if ($record.item_id -ne $ReviewItemId -or $record.artifact.index -ne $Artifact.index -or $record.artifact.sha256 -ne $Artifact.sha256 -or $record.artifact.comparison.comparison_page.sha256 -ne $Artifact.comparison.comparison_page.sha256) {
            continue
        }
        if (Test-ReviewInvalidated -ReviewPath $path.FullName -Record $record) {
            continue
        }
        if ($record.operator_result.selected -eq "已执行" -and [string]::IsNullOrWhiteSpace([string]$record.operator_result.note) -and $record.execution.canonical_aiw_operator_prompt_opened -eq $true) {
            return $true
        }
    }
    return $false
}

function Test-ReviewInvalidated {
    param(
        [Parameter(Mandatory = $true)][string] $ReviewPath,
        [Parameter(Mandatory = $true)] $Record
    )

    $triageRoot = Join-Path $repoRoot "docs\validation"
    if (-not (Test-Path -LiteralPath $triageRoot -PathType Container)) {
        return $false
    }
    $relativeReviewPath = Get-RelativePath -Path $ReviewPath
    $reviewHash = Get-Sha256 -Path $ReviewPath
    foreach ($triagePath in Get-ChildItem -LiteralPath $triageRoot -File -Filter "companion-g2-*-triage-*.json" -ErrorAction SilentlyContinue) {
        try {
            $triage = Get-Content -LiteralPath $triagePath.FullName -Raw | ConvertFrom-Json
        } catch {
            continue
        }
        $raw = $triage.raw_review
        $selectionApplied = $triage.decision.selection_applied
        if ($selectionApplied -is [bool] -and -not $selectionApplied -and ([string]$raw.path -eq $relativeReviewPath -or [string]$raw.sha256 -eq $reviewHash)) {
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
        [Parameter(Mandatory = $true)][bool] $ComparisonImageOpened,
        [Parameter(Mandatory = $true)][bool] $SelfTestMode
    )

    $selection = [string]$Result.selected
    $status = switch ($selection) {
        "已执行" { "OWNER_ARTIFACT_OBSERVATION_CAPTURED" }
        "需修改" { "OWNER_ARTIFACT_REWORK_CAPTURED_TRIAGE_REQUIRED" }
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
            comparison_image_opened = $ComparisonImageOpened
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
        next_step = $(if ($selection -eq "已执行" -and [string]::IsNullOrWhiteSpace([string]$Result.text)) { "The next locked original image may be reviewed. This observation does not authorize visual-resource import or runtime activation." } else { "Agent must triage this result before changing the source, opening another G2 image, or changing any manifest decision." })
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
$orderedIds = $manifestIds
$duplicateIds = @($manifestIds | Group-Object | Where-Object { $_.Count -ne 1 })
if ($manifestIds.Count -eq 0 -or $duplicateIds.Count -ne 0) { throw "Visual acceptance manifest has no items or duplicate ids." }
$item = @($items | Where-Object { $_.id -eq $ItemId })
if ($item.Count -ne 1) {
    throw "Visual acceptance item was not found exactly once: $ItemId"
}
$item = $item[0]
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
    foreach ($role in @("baseline", "desktop_output", "comparison_page")) {
        $comparisonSide = $image.comparison.$role
        if ($null -eq $comparisonSide -or [string]::IsNullOrWhiteSpace([string]$comparisonSide.path) -or [string]::IsNullOrWhiteSpace([string]$comparisonSide.sha256)) {
            throw "Visual acceptance item $ItemId comparison metadata is invalid at index $($index + 1): $role"
        }
        $comparisonPath = Join-Path $repoRoot ([string]$comparisonSide.path)
        if (-not (Test-Path -LiteralPath $comparisonPath -PathType Leaf) -or (Get-Sha256 -Path $comparisonPath) -ne $comparisonSide.sha256) {
            throw "Visual acceptance item $ItemId comparison hash drifted at index $($index + 1): $role"
        }
    }
}
$nextItemId = $null
$nextArtifactIndex = 0
foreach ($candidateItem in $items) {
    $candidateImages = @($candidateItem.artifact_review.images)
    foreach ($candidateImage in $candidateImages) {
        if (-not (Test-ArtifactAccepted -ReviewRoot $reviewRoot -ReviewItemId ([string]$candidateItem.id) -Artifact $candidateImage)) {
            $nextItemId = [string]$candidateItem.id
            $nextArtifactIndex = [int]$candidateImage.index
            break
        }
    }
    if ($null -ne $nextItemId) { break }
}
if ($null -eq $nextItemId) { throw "All locked original images have no-note 已执行 records; perform the separate source-import proposal only after audit." }
if ($ItemId -ne $nextItemId -or $ArtifactIndex -ne $nextArtifactIndex) {
    throw "G2 is sequential: the next eligible original image is $nextItemId $nextArtifactIndex, not $ItemId $ArtifactIndex."
}
$artifact = $images[$ArtifactIndex - 1]
$artifactPath = Join-Path $repoRoot ([string]$artifact.path)
$comparisonPagePath = Join-Path $repoRoot ([string]$artifact.comparison.comparison_page.path)
$position = [array]::IndexOf($orderedIds, $ItemId) + 1
$spec = Build-OperatorSpec -Item $item -Position $position -ItemCount $items.Count -Artifact $artifact -ArtifactCount $images.Count

if ($CheckOnly) {
    Write-Output "CHECK: G2 item=$ItemId position=$position/$($items.Count) paired_comparison=$ArtifactIndex/$($images.Count)"
    Write-Output "CHECK: Canonical operator prompt=$(Resolve-WorkflowAiwPath)"
    Write-Output "CHECK: Source SHA256=$($item.source_sha256)"
    Write-Output "CHECK: Machine evidence=$($item.machine_evidence)"
    Write-Output "CHECK: Original image=$($artifact.path) sha256=$($artifact.sha256)"
    Write-Output "CHECK: Baseline=$($artifact.comparison.baseline.path) sha256=$($artifact.comparison.baseline.sha256)"
    Write-Output "CHECK: Desktop output=$($artifact.comparison.desktop_output.path) sha256=$($artifact.comparison.desktop_output.sha256)"
    Write-Output "CHECK: Comparison page=$($artifact.comparison.comparison_page.path) sha256=$($artifact.comparison.comparison_page.sha256)"
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
    Write-ReviewRecord -Item $item -Artifact $artifact -Spec $spec -Result $result -RecordPath $recordPath -NotePath $notePath -PromptOpened $false -OriginalImageOpened $false -ComparisonImageOpened $false -SelfTestMode $true
    Write-Output "PASS: G2 paired-comparison runner self-test -> $(Get-RelativePath -Path $recordPath)"
    exit 0
}

$null = Start-Process -FilePath $comparisonPagePath -PassThru
Start-Sleep -Milliseconds 500
$aiw = Resolve-WorkflowAiwPath
$promptOutput = & pwsh -NoProfile -File $aiw operator-prompt `
    -Title $spec.title `
    -ProgressText $spec.progress_text `
    -ScopeText $spec.scope_text `
    -Message $spec.message `
    -ExpectedText $spec.expected_text `
    -ObservationLabel $spec.observation_label `
    -ReviewStyle -Input -Buttons "已执行,需修改,跳过,中止" `
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
Write-ReviewRecord -Item $item -Artifact $artifact -Spec $spec -Result $result -RecordPath $recordPath -NotePath $notePath -PromptOpened $true -OriginalImageOpened $true -ComparisonImageOpened $true -SelfTestMode $false
if ($result.selected -eq "需修改" -and [string]::IsNullOrWhiteSpace([string]$result.text)) {
    throw "A 需修改 visual result requires an operator note; the raw record was retained for triage."
}
Write-Output "RESULT: G2 paired-comparison review -> $(Get-RelativePath -Path $recordPath)"
