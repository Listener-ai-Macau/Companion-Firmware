param(
    [switch] $CheckOnly,
    [switch] $Execute,
    [switch] $SelfTestRecovery,
    [ValidateSet("通过", "失败")]
    [string] $SelfTestOperatorSelection,
    [switch] $WorkflowLockHeld,
    [ValidateSet("White", "Black", "RestoreNormal")]
    [string] $Stage,
    [ValidateRange(10, 120)]
    [int] $CaptureSeconds = 15,
    [ValidateRange(60, 3600)]
    [int] $OperatorTimeoutSeconds = 900,
    [string] $Port,
    [string] $OutRoot,
    [string] $NormalImagePath,
    [string] $WhiteImagePath,
    [string] $BlackImagePath,
    [string] $DisplayFpcReplacementEvidencePath,
    [string] $WhiteRailArtifactPath,
    [string] $VendorSourceAuditPath,
    [string] $ProgrammerRoot = "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
. (Join-Path $PSScriptRoot "companion_wb55_lock.ps1")
$flashRunner = Join-Path $PSScriptRoot "flash_nucleo_bringup.ps1"
$serialRunner = Join-Path $PSScriptRoot "capture_nucleo_serial.ps1"
$logVerifier = Join-Path $PSScriptRoot "verify_wb55_official_full_diagnostic_log.py"
$normalImageDefault = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build\Companion_Nucleo_WB55RG_Bringup.hex"
$whiteImageDefault = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_official_full_diagnostic_white\Companion_Nucleo_WB55RG_OfficialFullDiagnostic_white.hex"
$blackImageDefault = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_official_full_diagnostic_black\Companion_Nucleo_WB55RG_OfficialFullDiagnostic_black.hex"
$vendorSourceAuditDefault = Join-Path $repoRoot "docs\validation\companion-gdey0154d67-t03-vendor-1s-source-audit-20260720.json"
$displayFpcEvidenceDefault = Join-Path $repoRoot "docs\validation\companion-screen-wb55-replacement-fpc-evidence-20260720.json"
$defaultOutRoot = Join-Path $repoRoot ".cache\validation\wb55-screen-recovery-current"
$runRoot = if ([string]::IsNullOrWhiteSpace($OutRoot)) { $defaultOutRoot } else { $OutRoot }
$stageKey = if ([string]::IsNullOrWhiteSpace($Stage)) { "selftest" } else { $Stage.ToLowerInvariant() }
$stageRoot = Join-Path $runRoot $stageKey
$runReport = Join-Path $stageRoot "stage-run.json"
$operatorResultPath = Join-Path $stageRoot "operator-prompt-observation.txt"

function Resolve-ImagePath {
    param(
        [string] $Override,
        [string] $Default
    )

    if ([string]::IsNullOrWhiteSpace($Override)) {
        return $Default
    }
    if ([System.IO.Path]::IsPathRooted($Override)) {
        return [System.IO.Path]::GetFullPath($Override)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $repoRoot $Override))
}

function Resolve-OptionalPath {
    param([string] $Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $null
    }
    if ([System.IO.Path]::IsPathRooted($Value)) {
        return [System.IO.Path]::GetFullPath($Value)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $repoRoot $Value))
}

function Read-JsonEvidence {
    param(
        [string] $Path,
        [string] $Label
    )

    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing $Label evidence file."
    }
    try {
        return Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json -AsHashtable
    } catch {
        throw "$Label evidence is not valid JSON: $($_.Exception.Message)"
    }
}

function Assert-DisplayFpcReplacementEvidence {
    param([string] $Path)

    $evidence = Read-JsonEvidence -Path $Path -Label "replacement display-FPC"
    $observation = $evidence.owner_observation
    $authorization = $evidence.authorization
    $errors = @()
    if ($evidence.schema_id -ne "companion.wb55.display_fpc_replacement_evidence.v1") {
        $errors += "schema_id"
    }
    if ($evidence.status -ne "PASS_OWNER_REPORTED_REPLACEMENT_FPC_CURRENT_PANEL_VISIBLE") {
        $errors += "status"
    }
    if ($evidence.target -ne "NUCLEO-WB55RG + ESP32-FTS02 + GDEY0154D67-T03") {
        $errors += "target"
    }
    foreach ($field in @("replacement_display_fpc_installed", "current_dynamic_expressions_visible", "photo_observed_in_conversation")) {
        if ($null -eq $observation -or $observation[$field] -ne $true) {
            $errors += "owner_observation.$field"
        }
    }
    if ($null -eq $authorization -or $authorization.allowed_stage -ne "White") {
        $errors += "authorization.allowed_stage"
    }
    if ($errors.Count -gt 0) {
        throw "Replacement display-FPC evidence is incomplete: $($errors -join ', ')."
    }
    return $evidence
}

function Assert-WhiteRailEvidence {
    param([string] $Path)

    $evidence = Read-JsonEvidence -Path $Path -Label "post-White rail"
    $checks = $evidence.checks
    $measurement = $evidence.measurement
    $errors = @()
    if ($evidence.schema_id -ne "companion.wb55.official_full_rail_measurement.v1") {
        $errors += "schema_id"
    }
    if ($evidence.status -ne "PASS_MACHINE_AND_RAILS_ESTABLISHED_WHITE") {
        $errors += "status"
    }
    foreach ($field in @("official_current_plane_only", "every_observed_cycle_transfers_one_5000_byte_plane", "refresh_within_5000_ms", "activation_0x20_sent", "source_audit_bound", "no_panel_error_marker", "operator_selected_pass", "screen_observation_declares_uniform_white", "positive_and_negative_refresh_rails_established")) {
        if ($null -eq $checks -or $checks[$field] -ne $true) {
            $errors += "checks.$field"
        }
    }
    if ($null -eq $measurement -or $measurement.operator_selected -ne "通过" -or $measurement.screen_observation -ne "uniform_white") {
        $errors += "measurement.white_operator_observation"
    }
    if ($errors.Count -gt 0) {
        throw "Post-White rail evidence is incomplete: $($errors -join ', ')."
    }
    return $evidence
}

function Assert-VendorSourceAudit {
    param([string] $Path)

    $evidence = Read-JsonEvidence -Path $Path -Label "vendor source audit"
    $commandEvidence = $evidence.command_evidence
    $criticalSources = $evidence.source_manifest.critical_sources
    $errors = @()
    if ($evidence.schema_id -ne "companion.gdey0154d67_t03.vendor_1s_source_audit.v1") {
        $errors += "schema_id"
    }
    if ($evidence.machine_status -ne "PASS_AUDIT_COMPLETE") {
        $errors += "machine_status"
    }
    if ($evidence.promotion_status -ne "NO_GO_PANEL_IDENTITY_UNPROVEN") {
        $errors += "promotion_status"
    }
    if ($null -eq $commandEvidence -or $commandEvidence.production_lut_reference_absent -ne $true) {
        $errors += "command_evidence.production_lut_reference_absent"
    }
    foreach ($field in @("epaper_c", "current_ssd1681_target")) {
        $source = if ($null -eq $criticalSources) { $null } else { $criticalSources[$field] }
        if ($null -eq $source -or [string]::IsNullOrWhiteSpace([string]$source.sha256) -or [string]::IsNullOrWhiteSpace([string]$source.path)) {
            $errors += "source_manifest.critical_sources.$field"
            continue
        }
        $sourcePath = [string]$source.path
        if (-not [System.IO.Path]::IsPathRooted($sourcePath)) {
            $sourcePath = Join-Path $repoRoot $sourcePath
        }
        if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
            $errors += "source_manifest.critical_sources.$field.path"
            continue
        }
        $actualHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash.ToUpperInvariant()
        if ($actualHash -ne ([string]$source.sha256).ToUpperInvariant()) {
            $errors += "source_manifest.critical_sources.$field.sha256_drift"
        }
    }
    if ($errors.Count -gt 0) {
        throw "Vendor source audit is incomplete or permits LUT promotion: $($errors -join ', ')."
    }
    return $evidence
}

$normalImage = Resolve-ImagePath -Override $NormalImagePath -Default $normalImageDefault
$whiteImage = Resolve-ImagePath -Override $WhiteImagePath -Default $whiteImageDefault
$blackImage = Resolve-ImagePath -Override $BlackImagePath -Default $blackImageDefault
$displayFpcReplacementEvidence = Resolve-ImagePath -Override $DisplayFpcReplacementEvidencePath -Default $displayFpcEvidenceDefault
$whiteRailArtifact = Resolve-OptionalPath -Value $WhiteRailArtifactPath
$vendorSourceAudit = Resolve-ImagePath -Override $VendorSourceAuditPath -Default $vendorSourceAuditDefault

function RelPath {
    param([string] $Path)

    return [System.IO.Path]::GetRelativePath($repoRoot, [System.IO.Path]::GetFullPath($Path)).Replace("\", "/")
}

function Build-Step {
    param(
        [string] $Id,
        [string] $Command,
        [string[]] $Arguments,
        [string] $Purpose
    )

    return [ordered]@{
        id = $Id
        command = $Command
        arguments = @($Arguments)
        purpose = $Purpose
    }
}

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

function Build-OperatorReviewSpec {
    param([string] $ReviewStage)

    switch ($ReviewStage) {
        "White" {
            return [ordered]@{
                title = "Companion 屏幕纯白复测验收"
                progress_text = "1/2（本次 1/1）"
                scope_text = "更换显示 FPC 后的官方复测共 2 项；当前只验纯白画面。机器已确认官方单平面路径和 BUSY 完成。"
                message = "请观察 GDEY0154D67-T03：整个有效显示区域应稳定、均匀地呈纯白色。不要把黑白颗粒、局部脏块、旧图残留或没有变化判为通过。"
                expected_text = "通过标准：全屏纯白、无黑白颗粒、无明显旧图残留，并且确实发生过本次刷新。任何异常请选择失败并完整备注。"
                default_note = "全白均匀；无黑白颗粒、无旧图残留。"
            }
        }
        "Black" {
            return [ordered]@{
                title = "Companion 屏幕纯黑复测验收"
                progress_text = "2/2（本次 1/1）"
                scope_text = "更换显示 FPC 后的官方复测共 2 项；当前只验纯黑画面。机器已确认官方单平面路径和 BUSY 完成。"
                message = "请观察 GDEY0154D67-T03：整个有效显示区域应稳定、均匀地呈纯黑色。不要把黑白颗粒、局部灰白、旧图残留或没有变化判为通过。"
                expected_text = "通过标准：全屏纯黑、无黑白颗粒、无明显旧图残留，并且确实发生过本次刷新。任何异常请选择失败并完整备注。"
                default_note = "全黑均匀；无灰白颗粒、无旧图残留。"
            }
        }
        default {
            return $null
        }
    }
}

function Invoke-OperatorReview {
    param(
        [Parameter(Mandatory = $true)][string] $ReviewStage,
        [Parameter(Mandatory = $true)] $Spec
    )

    if ($SelfTestRecovery -and -not [string]::IsNullOrWhiteSpace($SelfTestOperatorSelection)) {
        $mock = [ordered]@{
            selected = $SelfTestOperatorSelection
            text = "SELFTEST operator selection: $SelfTestOperatorSelection"
        }
        New-Item -ItemType Directory -Force -Path $stageRoot | Out-Null
        $mock | ConvertTo-Json | Set-Content -LiteralPath $operatorResultPath -Encoding UTF8
        return [pscustomobject]$mock
    }

    $aiw = Resolve-WorkflowAiwPath
    $promptOutput = & pwsh -NoProfile -File $aiw operator-prompt `
        -Title $Spec.title `
        -ProgressText $Spec.progress_text `
        -ScopeText $Spec.scope_text `
        -Message $Spec.message `
        -ExpectedText $Spec.expected_text `
        -DefaultText $Spec.default_note `
        -ReviewStyle -Input -Buttons "通过,失败,跳过,中止" `
        -OutputPath $operatorResultPath `
        -TimeoutSeconds $OperatorTimeoutSeconds -Json
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
    return $result
}

function Write-RunReport {
    param([object] $Report)

    New-Item -ItemType Directory -Force -Path $stageRoot | Out-Null
    $Report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $runReport -Encoding UTF8
    Write-Output "Screen recovery stage report: $(RelPath $runReport)"
}

function Assert-CheckOnlyWillNotOverwriteCompletedEvidence {
    if (-not $CheckOnly -or -not (Test-Path -LiteralPath $runReport -PathType Leaf)) {
        return
    }
    try {
        $existing = Get-Content -Raw -LiteralPath $runReport | ConvertFrom-Json -AsHashtable
    } catch {
        throw "Refusing CheckOnly to overwrite an unreadable existing stage report: $runReport"
    }
    if ($existing.status -ne "DRY-RUN" -or
        $existing.claim_scope -ne "preflight_only_no_hardware_claim") {
        throw "Refusing CheckOnly to overwrite completed or non-preflight stage evidence: $runReport"
    }
}

$selectedModes = @($CheckOnly.IsPresent, $Execute.IsPresent, $SelfTestRecovery.IsPresent) |
    Where-Object { $_ }
if (@($selectedModes).Count -ne 1) {
    throw "Use exactly one of -CheckOnly, -Execute, or -SelfTestRecovery."
}
if (-not $SelfTestRecovery -and [string]::IsNullOrWhiteSpace($Stage)) {
    throw "-Stage White, Black, or RestoreNormal is required."
}
if (-not $SelfTestRecovery -and -not [string]::IsNullOrWhiteSpace($SelfTestOperatorSelection)) {
    throw "-SelfTestOperatorSelection is valid only with -SelfTestRecovery."
}
Assert-CheckOnlyWillNotOverwriteCompletedEvidence

$prerequisites = [ordered]@{
    replacement_display_fpc_required = $Stage -eq "White"
    replacement_display_fpc_path = if ($Stage -eq "White") { RelPath $displayFpcReplacementEvidence } else { $null }
    replacement_display_fpc_validated = $false
    post_white_rail_required = $Stage -eq "Black"
    post_white_rail_path = if ($whiteRailArtifact) { RelPath $whiteRailArtifact } else { $null }
    post_white_rail_validated = $false
    vendor_source_audit_required = $Stage -in @("White", "Black")
    vendor_source_audit_path = if ($Stage -in @("White", "Black")) { RelPath $vendorSourceAudit } else { $null }
    vendor_source_audit_validated = $false
}
if ($Execute -and -not $SelfTestRecovery -and $Stage -in @("White", "Black")) {
    if ($Stage -eq "White") {
        $null = Assert-DisplayFpcReplacementEvidence -Path $displayFpcReplacementEvidence
        $prerequisites.replacement_display_fpc_validated = $true
    }
    if ($Stage -eq "Black") {
        $null = Assert-WhiteRailEvidence -Path $whiteRailArtifact
        $prerequisites.post_white_rail_validated = $true
    }
    $null = Assert-VendorSourceAudit -Path $vendorSourceAudit
    $prerequisites.vendor_source_audit_validated = $true
}

$image = switch ($Stage) {
    "White" { $whiteImage }
    "Black" { $blackImage }
    "RestoreNormal" { $normalImage }
    default { $whiteImage }
}

if (-not $SelfTestRecovery) {
    $required = @($flashRunner, $normalImage, $image)
    if ($Stage -ne "RestoreNormal") {
        $required += @($serialRunner, $logVerifier, $vendorSourceAudit)
    }
    foreach ($path in $required | Select-Object -Unique) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Required screen recovery artifact is missing: $path"
        }
    }
}

$portArgs = @()
if (-not [string]::IsNullOrWhiteSpace($Port)) {
    $portArgs = @("-Port", $Port)
}
$steps = @()
$normalRestoreStep = Build-Step -Id "flash_normal_restore" -Command "pwsh" -Arguments @(
    "-NoProfile", "-File", $flashRunner,
    "-ImagePath", $normalImage,
    "-ProgrammerRoot", $ProgrammerRoot
) -Purpose "Restore the normal quiet production firmware."

if ($Stage -eq "RestoreNormal") {
    $steps += $normalRestoreStep
} elseif (-not $SelfTestRecovery) {
    $pattern = $Stage.ToLowerInvariant()
    $captureDir = Join-Path $stageRoot "capture"
    $rawLog = Join-Path $captureDir "nucleo-serial-raw.log"
    $parsedLog = Join-Path $stageRoot "official-full-result.json"
    $steps += Build-Step -Id "flash_$pattern" -Command "pwsh" -Arguments @(
        "-NoProfile", "-File", $flashRunner,
        "-ImagePath", $image,
        "-ProgrammerRoot", $ProgrammerRoot
    ) -Purpose "Flash the official one-plane $pattern diagnostic."
    $captureArguments = @(
        "-NoProfile", "-File", $serialRunner,
        "-Execute",
        "-Seconds", "$CaptureSeconds",
        "-ResetAfterOpen",
        "-OutDir", $captureDir
    ) + $portArgs
    $steps += Build-Step -Id "capture_$pattern" -Command "pwsh" -Arguments $captureArguments -Purpose "Capture one reset-bounded $pattern diagnostic trace."
    $steps += Build-Step -Id "parse_$pattern" -Command "python" -Arguments @(
        $logVerifier,
        "--pattern", $pattern,
        "--log", $rawLog,
        "--out", $parsedLog,
        "--source-audit", $vendorSourceAudit
    ) -Purpose "Require source-hash binding, selected pattern, official 0x24 path, 0x20 activation, BUSY assertion, elapsed time, and one completed plane."
}

if ($SelfTestRecovery) {
    $Stage = "White"
    $stageKey = "selftest"
    if ([string]::IsNullOrWhiteSpace($SelfTestOperatorSelection)) {
        $steps = @(
            Build-Step -Id "flash_white" -Command "pwsh" -Arguments @(
                "-NoProfile", "-Command", "Write-Output 'SELFTEST: flash_white'; exit 0"
            ) -Purpose "Stub-only diagnostic flash."
            Build-Step -Id "capture_white" -Command "pwsh" -Arguments @(
                "-NoProfile", "-Command", "Write-Output 'SELFTEST: capture_white failure'; exit 7"
            ) -Purpose "Stub-only capture failure."
        )
    } else {
        $steps = @(
            Build-Step -Id "flash_white" -Command "pwsh" -Arguments @(
                "-NoProfile", "-Command", "Write-Output 'SELFTEST: flash_white'; exit 0"
            ) -Purpose "Stub-only diagnostic flash."
            Build-Step -Id "capture_white" -Command "pwsh" -Arguments @(
                "-NoProfile", "-Command", "Write-Output 'SELFTEST: capture_white'; exit 0"
            ) -Purpose "Stub-only diagnostic capture."
            Build-Step -Id "parse_white" -Command "pwsh" -Arguments @(
                "-NoProfile", "-Command", "Write-Output 'SELFTEST: parse_white'; exit 0"
            ) -Purpose "Stub-only diagnostic parser."
        )
    }
    $normalRestoreStep = Build-Step -Id "flash_normal_restore" -Command "pwsh" -Arguments @(
        "-NoProfile", "-Command", "Write-Output 'SELFTEST: flash_normal_restore'; exit 0"
    ) -Purpose "Stub-only normal firmware recovery."
}

$operatorReviewSpec = Build-OperatorReviewSpec -ReviewStage $Stage
$operatorReviewRequired = $Stage -in @("White", "Black")

$report = [ordered]@{
    schema_id = "companion.wb55.screen_recovery_stage_run.v2"
    status = if ($CheckOnly) { "DRY-RUN" } elseif ($SelfTestRecovery) { "SELFTEST_RUNNING" } else { "RUNNING" }
    claim_scope = if ($CheckOnly) { "preflight_only_no_hardware_claim" } elseif ($SelfTestRecovery) { "stubbed_failure_recovery_no_hardware_claim" } else { "machine_digital_trace_pending_operator_visual_gate" }
    generated_at = (Get-Date).ToString("o")
    target = "NUCLEO-WB55RG + ESP32-FTS02 + replacement display FPC + GDEY0154D67-T03"
    stage = $Stage
    capture_seconds = $CaptureSeconds
    image = RelPath $image
    output = [ordered]@{
        root = RelPath $stageRoot
        run_report = RelPath $runReport
    }
    operator_review = [ordered]@{
        required = [bool]$operatorReviewRequired
        invoked = $false
        style = if ($operatorReviewRequired) { "aiw_operator_prompt_v1" } else { $null }
        output_path = if ($operatorReviewRequired) { RelPath $operatorResultPath } else { $null }
        title = if ($operatorReviewSpec) { $operatorReviewSpec.title } else { $null }
        progress_text = if ($operatorReviewSpec) { $operatorReviewSpec.progress_text } else { $null }
        scope_text = if ($operatorReviewSpec) { $operatorReviewSpec.scope_text } else { $null }
        message = if ($operatorReviewSpec) { $operatorReviewSpec.message } else { $null }
        expected_text = if ($operatorReviewSpec) { $operatorReviewSpec.expected_text } else { $null }
        selected = $null
        note = $null
    }
    prerequisites = $prerequisites
    source_audit = [ordered]@{
        path = if ($Stage -in @("White", "Black")) { RelPath $vendorSourceAudit } else { $null }
        promotion_status_required = "NO_GO_PANEL_IDENTITY_UNPROVEN"
        production_lut_reference_required_absent = $true
    }
    steps = @($steps)
    safety = [ordered]@{
        execute_requires_companion_wb55_lock = $true
        execute_uses_firmware_owned_exclusive_mutex = $true
        legacy_workflow_lock_boolean_is_not_authority = $true
        diagnostic_failure_restores_normal = $true
        successful_diagnostic_waits_for_focused_operator_visual_result = $true
        successful_review_restores_normal_firmware = $true
        machine_pass_is_not_visual_or_voltage_acceptance = $true
    }
    notes = @(
        "Run a diagnostic stage only after the owner-authorized replacement display-FPC evidence and explicit owner acceptance start.",
        "White Execute requires validated replacement display-FPC evidence; Black Execute additionally requires a PASS post-White rail artifact.",
        "The installed AIW exposes the canonical operator-prompt but no with-lock command. This runner holds the Companion-WB55 firmware mutex across flash, capture, parser, review and normal restore; child flash/capture processes verify its inherited grant.",
        "White and Black stages open exactly one focused operator review only after machine PASS.",
        "Every completed or rejected review attempts to restore the normal firmware before returning.",
        "A machine PASS proves only the source-bound digital command/BUSY trace; PREVGH/PREVGL and visible-frame acceptance remain physical gates.",
        "The audited one-second LUT remains identity-NO_GO and absent from production; this runner only binds its source audit while exercising the existing matched official full path."
    )
}

if ($CheckOnly) {
    $report.completed_at = (Get-Date).ToString("o")
    $report.results = @()
    Write-Output "CHECK: WB55 screen recovery stage=$Stage capture_seconds=$CaptureSeconds"
    foreach ($step in $steps) {
        Write-Output "CHECK: $($step.id): $($step.command) $($step.arguments -join ' ')"
    }
    Write-RunReport -Report $report
    Write-Output ($report | ConvertTo-Json -Depth 12)
    exit 0
}

$results = @()
$diagnosticFlashed = $false
$normalRestored = $false
$hardwareLock = $null
try {
    if ($Execute) {
        $hardwareLock = Enter-CompanionWb55Lock -Purpose "official full $Stage recovery"
        $report.execution_lock = Get-CompanionWb55LockEvidenceSummary -Context $hardwareLock
        Write-Output "LOCK: Companion-WB55 $($hardwareLock.mode) run=$($hardwareLock.run_id)"
    }
    foreach ($step in $steps) {
        $started = Get-Date
        Write-Output "RUN: $($step.id)"
        & $step.command @($step.arguments)
        $exitCode = $LASTEXITCODE
        $ended = Get-Date
        $results += [ordered]@{
            id = $step.id
            status = if ($exitCode -eq 0) { "PASS" } else { "FAIL" }
            exit_code = $exitCode
            started_at = $started.ToString("o")
            ended_at = $ended.ToString("o")
        }
        if ($exitCode -ne 0) {
            throw "$($step.id) failed with exit code $exitCode"
        }
        if ($step.id -in @("flash_white", "flash_black")) {
            $diagnosticFlashed = $true
        }
        if ($step.id -eq "flash_normal_restore") {
            $normalRestored = $true
        }
    }
    if ($operatorReviewRequired) {
        $report.operator_review.invoked = $true
        $promptResult = Invoke-OperatorReview -ReviewStage $Stage -Spec $operatorReviewSpec
        $report.operator_review.selected = [string]$promptResult.selected
        $report.operator_review.note = [string]$promptResult.text
        if ($report.operator_review.selected -ne "通过") {
            throw "Operator did not pass the $Stage frame: selected=$($report.operator_review.selected)."
        }
        if ([string]::IsNullOrWhiteSpace($report.operator_review.note)) {
            throw "Operator passed the $Stage frame without the required physical observation note."
        }

        $restoreStarted = Get-Date
        Write-Output "RECOVERY: flash_normal_restore_after_review"
        & $normalRestoreStep.command @($normalRestoreStep.arguments)
        $restoreExitCode = $LASTEXITCODE
        $restoreEnded = Get-Date
        $normalRestored = $restoreExitCode -eq 0
        $results += [ordered]@{
            id = "flash_normal_restore_after_review"
            status = if ($normalRestored) { "PASS" } else { "FAIL" }
            exit_code = $restoreExitCode
            started_at = $restoreStarted.ToString("o")
            ended_at = $restoreEnded.ToString("o")
        }
        if (-not $normalRestored) {
            throw "Normal firmware restore after operator review failed with exit code $restoreExitCode."
        }
    }
    $report.status = "PASS_MACHINE_AND_VISIBLE_FRAME_NORMAL_RESTORED_PENDING_VOLTAGE_RAILS"
    if ($Stage -eq "RestoreNormal") {
        $report.status = "PASS_NORMAL_FIRMWARE_RESTORED"
    }
} catch {
    $report.status = "FAIL"
    $report.error = $_.Exception.Message
    if ($diagnosticFlashed -and -not $normalRestored) {
        $restoreStarted = Get-Date
        Write-Output "RECOVERY: flash_normal_restore_after_failure"
        & $normalRestoreStep.command @($normalRestoreStep.arguments)
        $restoreExitCode = $LASTEXITCODE
        $restoreEnded = Get-Date
        $normalRestored = $restoreExitCode -eq 0
        $results += [ordered]@{
            id = "flash_normal_restore_after_failure"
            status = if ($normalRestored) { "PASS" } else { "FAIL" }
            exit_code = $restoreExitCode
            started_at = $restoreStarted.ToString("o")
            ended_at = $restoreEnded.ToString("o")
        }
    }
    throw
} finally {
    if ($hardwareLock) {
        try {
            Exit-CompanionWb55Lock
        } catch {
            $report.lock_release_error = $_.Exception.Message
            if ($report.status -like "PASS_*") {
                $report.status = "FAIL"
            }
        }
    }
    $report.normal_firmware_restored = [bool]$normalRestored
    $report.diagnostic_left_installed = [bool]($diagnosticFlashed -and -not $normalRestored -and $report.status -like "PASS_*")
    $report.completed_at = (Get-Date).ToString("o")
    $report.results = @($results)
    Write-RunReport -Report $report
}
