# UTF-8 BOM required. Loads Chinese from a UTF-8 JSON step file and shows operator_prompt.
param(
    [Parameter(Mandatory = $true)]
    [string]$StepJsonPath
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

if (-not (Test-Path -LiteralPath $StepJsonPath)) {
    throw "Step json not found: $StepJsonPath"
}

$step = Get-Content -LiteralPath $StepJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
$workflow = "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\operator_prompt.ps1"
if (-not (Test-Path -LiteralPath $workflow)) {
    throw "operator_prompt.ps1 missing: $workflow"
}

$outPath = [string]$step.output_path
$parent = Split-Path -Parent $outPath
if ($parent -and -not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
}

$args = @{
    Title           = [string]$step.title
    ProgressText    = [string]$step.progress
    ScopeText       = [string]$step.scope
    Message         = [string]$step.message
    ExpectedText    = [string]$step.expected
    Buttons         = if ($step.buttons) { [string]$step.buttons } else { "通过,失败,跳过,中止" }
    OutputPath      = $outPath
    Width           = if ($step.width) { [int]$step.width } else { 820 }
    Height          = if ($step.height) { [int]$step.height } else { 500 }
    Position        = if ($step.position) { [string]$step.position } else { "Center" }
    ReviewStyle     = $true
    TextInput       = $true
    Json            = $true
}

& $workflow @args
exit $LASTEXITCODE
