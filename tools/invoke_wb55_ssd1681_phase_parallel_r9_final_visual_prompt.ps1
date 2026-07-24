param(
    [Parameter(Mandatory = $true)]
    [string]$ControllerArtifact,
    [Parameter(Mandatory = $true)]
    [string]$OutRoot,
    [ValidateRange(60, 1800)]
    [int]$TimeoutSeconds = 900
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Get-Sha256([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

function Resolve-WorkflowAiwPath {
    $roots = @()
    if ($env:AI_WORKFLOW_REPO) { $roots += $env:AI_WORKFLOW_REPO }
    $roots += "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow"
    foreach ($root in $roots) {
        $candidate = Join-Path $root "scripts\aiw.ps1"
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    throw "The canonical aiw operator-prompt helper was not found."
}

$controllerPath = [System.IO.Path]::GetFullPath($ControllerArtifact)
$outputRoot = [System.IO.Path]::GetFullPath($OutRoot)
if (-not (Test-Path -LiteralPath $controllerPath -PathType Leaf)) {
    throw "R9 controller artifact is missing; final visual prompt is forbidden."
}
$controller = Get-Content -LiteralPath $controllerPath -Raw | ConvertFrom-Json
$steps = @($controller.observed.steps)
if ($controller.status -ne "PASS_MACHINE_PHASE_PARALLEL_R9" -or
    $steps.Count -ne 16 -or
    @($steps | Where-Object { $_.busy_ms -lt 1 -or $_.busy_ms -gt 600 }).Count -ne 0) {
    throw "R9 machine result is not a complete 16-step <=600 ms PASS; final visual prompt is forbidden."
}

New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null
$notePath = Join-Path $outputRoot "operator-note.txt"
$reviewPath = Join-Path $outputRoot "operator-review.json"
if (Test-Path -LiteralPath $reviewPath) {
    throw "R9 final visual result already exists; a second acceptance prompt is forbidden."
}

$aiw = Resolve-WorkflowAiwPath
$pwsh = (Get-Command pwsh -ErrorAction Stop).Source
$promptOutput = & $pwsh -NoProfile -File $aiw operator-prompt `
    -Title "Companion R9 局部刷新视觉验收" `
    -ProgressText "最终视觉验收" `
    -ScopeText "只判断刚完成的 16 次 32×32 局部黑白切换。" `
    -Message "请看屏幕刚才的局部切换结果，并直接选择通过或失败。" `
    -ExpectedText "通过：运动期没有整屏黑闪，局部黑白都可逆，没有不可恢复脏块，每个落点完整。任一项不符合请选择失败。" `
    -ObservationLabel "备注（失败时请写下看到的黑闪、残影、缺口或脏块）" `
    -Input `
    -ReviewStyle `
    -Buttons "通过,失败" `
    -OutputPath $notePath `
    -TimeoutSeconds $TimeoutSeconds `
    -Json
if ($LASTEXITCODE -ne 0) {
    throw "Canonical R9 final visual acceptance prompt failed."
}
$result = ($promptOutput -join [Environment]::NewLine) | ConvertFrom-Json
$note = if (Test-Path -LiteralPath $notePath -PathType Leaf) {
    Get-Content -LiteralPath $notePath -Raw
} else {
    [string]$result.text
}
$review = [ordered]@{
    schema_id = "companion.wb55.ssd1681_phase_parallel_r9.operator_review.v1"
    status = if ($result.selected -eq "通过") {
        "PASS_OWNER_R9_LOCAL_VISUAL"
    } elseif ($result.selected -eq "失败") {
        "NO_GO_OWNER_R9_LOCAL_VISUAL"
    } else {
        "NO_GO_R9_VISUAL_NO_PASS_FAIL_SELECTION"
    }
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    style = "aiw_operator_prompt_v1"
    selected = [string]$result.selected
    note = $note
    note_path = $notePath
    note_sha256 = if (Test-Path -LiteralPath $notePath -PathType Leaf) { Get-Sha256 $notePath } else { $null }
    controller_artifact = $controllerPath
    controller_sha256 = Get-Sha256 $controllerPath
    candidate_lut_sha256 = "9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD"
    machine_steps = 16
    machine_busy_max_ms = ($steps | Measure-Object -Property busy_ms -Maximum).Maximum
    popup_counts = [ordered]@{
        start = 0
        cleanup = 0
        recovery = 0
        fault = 0
        final_visual_acceptance = 1
    }
}
$review | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reviewPath -Encoding UTF8
$review | ConvertTo-Json -Depth 8 -Compress
