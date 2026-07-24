param(
    [Parameter(Mandatory = $true)]
    [int] $OperatorPromptProcessId,
    [Parameter(Mandatory = $true)]
    [string] $OperatorResultPath,
    [Parameter(Mandatory = $true)]
    [string] $NormalImagePath,
    [Parameter(Mandatory = $true)]
    [string] $RunRoot,
    [string] $ProgrammerRoot = "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$flashRunner = Join-Path $PSScriptRoot "flash_nucleo_bringup.ps1"
$reportPath = Join-Path $RunRoot "normal-restore-supervisor.json"

if (-not (Test-Path -LiteralPath $flashRunner -PathType Leaf)) { throw "Flash runner missing: $flashRunner" }
if (-not (Test-Path -LiteralPath $NormalImagePath -PathType Leaf)) { throw "Normal image missing: $NormalImagePath" }

while ($null -ne (Get-Process -Id $OperatorPromptProcessId -ErrorAction SilentlyContinue)) {
    Start-Sleep -Seconds 1
}

Start-Sleep -Seconds 1
$selection = $null
$note = $null
if (Test-Path -LiteralPath $OperatorResultPath -PathType Leaf) {
    try {
        $rawReview = Get-Content -Raw -LiteralPath $OperatorResultPath
        if ([string]::IsNullOrWhiteSpace($rawReview)) {
            $note = "operator window ended without a selection"
        } else {
            $review = $rawReview | ConvertFrom-Json
            $selectionProperty = $review.PSObject.Properties["selected"]
            $noteProperty = $review.PSObject.Properties["text"]
            $selection = if ($null -ne $selectionProperty) { [string]$selectionProperty.Value } else { $null }
            $note = if ($null -ne $noteProperty) { [string]$noteProperty.Value } else { "operator result has no observation note" }
        }
    } catch {
        $note = "operator result parse failed: $($_.Exception.Message)"
    }
}

& pwsh -NoProfile -File $flashRunner -ImagePath $NormalImagePath -ProgrammerRoot $ProgrammerRoot
$restoreExit = $LASTEXITCODE
$report = [ordered]@{
    schema_id = "companion.wb55.gdey0154d67_t03.vendor_partial_slow_motion_restore_supervisor.v1"
    status = if ($restoreExit -eq 0) { "PASS_NORMAL_RESTORED_AFTER_ORPHANED_OPERATOR_WINDOW" } else { "FAIL_NORMAL_RESTORE_AFTER_ORPHANED_OPERATOR_WINDOW" }
    completed_at = (Get-Date).ToString("o")
    operator_prompt_process_id = $OperatorPromptProcessId
    operator_result_path = $OperatorResultPath
    operator_selected = $selection
    operator_note = $note
    normal_image = [ordered]@{ path = $NormalImagePath; sha256 = (Get-FileHash -LiteralPath $NormalImagePath -Algorithm SHA256).Hash }
    restore_exit_code = $restoreExit
}
New-Item -ItemType Directory -Force -Path $RunRoot | Out-Null
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8
exit $restoreExit
