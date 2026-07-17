#requires -Version 7.0
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $PSScriptRoot "run_companion_goal_visual_source_acceptance.ps1"

$tokens = $null
$parseErrors = $null
[void][System.Management.Automation.Language.Parser]::ParseFile($runner, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -ne 0) {
    throw "G2 visual-source runner PowerShell parse failed: $($parseErrors[0].Message)"
}

& pwsh -NoProfile -File $runner -CheckOnly
if ($LASTEXITCODE -ne 0) {
    throw "G2 visual-source runner check-only failed."
}
& pwsh -NoProfile -File $runner -CheckOnly -ItemId "special-system-v1" 2>$null
if ($LASTEXITCODE -eq 0) {
    throw "G2 visual-source runner must reject an out-of-order item."
}
& pwsh -NoProfile -File $runner -CheckOnly -SelfTest 2>$null
if ($LASTEXITCODE -eq 0) {
    throw "G2 visual-source runner must reject multiple execution modes."
}
& pwsh -NoProfile -File $runner -Execute 2>$null
if ($LASTEXITCODE -eq 0) {
    throw "G2 visual-source runner must require explicit owner-start acknowledgement."
}
& pwsh -NoProfile -File $runner -SelfTest -SelfTestSelection "通过"
if ($LASTEXITCODE -ne 0) {
    throw "G2 visual-source runner self-test failed."
}

$latest = Get-ChildItem -LiteralPath (Join-Path $repoRoot ".cache\selftests\companion-g2-visual-source-review") -Directory |
    Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
if ($null -eq $latest) {
    throw "G2 visual-source runner self-test did not write a review directory."
}
$recordPath = Join-Path $latest.FullName "operator-review.json"
$record = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
$manifest = Get-Content -LiteralPath (Join-Path $repoRoot "docs\validation\companion-ui-visual-acceptance-manifest-20260717.json") -Raw | ConvertFrom-Json
$item = @($manifest.items | Where-Object { $_.id -eq "menu-v6-four-root" })[0]
if ($record.schema -ne "companion.g2_visual_source_operator_review.v1") {
    throw "G2 review schema drifted."
}
if ($record.status -ne "OWNER_VISUAL_SELECTION_CAPTURED_TRIAGE_REQUIRED") {
    throw "G2 self-test selection status drifted."
}
if ($record.item_id -ne "menu-v6-four-root" -or $record.execution.canonical_aiw_operator_prompt_opened -ne $false -or $record.execution.self_test -ne $true) {
    throw "G2 self-test must preserve the first sequential item without opening the prompt."
}
if ($record.source_sha256 -ne $item.source_sha256 -or $record.machine_evidence -ne $item.machine_evidence) {
    throw "G2 self-test record drifted from the manifest source or evidence identity."
}
$rendered = $record.rendered_prompt
if ([string]$rendered.title -notlike "*1/3*" -or [string]$rendered.scope_text -notlike "*不会导入 PBM/CEMP*" ) {
    throw "G2 rendered prompt lost its sequential or non-activation scope."
}
foreach ($field in @("target", "operator_action", "success_signal", "failure_rule", "continue_condition", "recovery_condition", "record_fields")) {
    if (-not $record.operator_prompt.$field) {
        throw "G2 self-test record is missing manifest prompt field: $field"
    }
    if (($record.operator_prompt.$field | ConvertTo-Json -Depth 8 -Compress) -ne ($item.operator_prompt.$field | ConvertTo-Json -Depth 8 -Compress)) {
        throw "G2 self-test record drifted from manifest prompt field: $field"
    }
}
foreach ($text in @($item.operator_prompt.target, $item.operator_prompt.operator_action, $item.operator_prompt.failure_rule) + @($item.operator_prompt.success_signal)) {
    if ([string]$rendered.message -notlike "*$text*") {
        throw "G2 rendered message is missing manifest text: $text"
    }
}
foreach ($text in @($item.operator_prompt.continue_condition, $item.operator_prompt.recovery_condition) + @($item.operator_prompt.record_fields)) {
    if ([string]$rendered.expected_text -notlike "*$text*") {
        throw "G2 rendered expected text is missing manifest text: $text"
    }
}
if (-not (Test-Path -LiteralPath (Join-Path $latest.FullName "operator-note.txt"))) {
    throw "G2 self-test did not retain the matching operator-note path."
}
foreach ($key in @("manifest_owner_decision_changed", "pbm_imported", "cemp_packed", "external_flash_provisioned", "firmware_flashed", "runtime_resource_activated")) {
    if ($record.boundary.$key -ne $false) {
        throw "G2 self-test boundary drifted: $key"
    }
}
Write-Output "PASS: manifest-backed G2 operator prompt is detailed, sequential, and non-activating."
