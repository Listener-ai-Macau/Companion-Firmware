param(
    [switch] $CheckOnly,
    [switch] $Execute,
    [switch] $WorkflowLockHeld,
    [ValidateRange(15, 90)]
    [int] $CaptureSeconds = 20,
    [ValidateRange(60, 3600)]
    [int] $OperatorTimeoutSeconds = 900,
    [string] $Port,
    [string] $OutRoot,
    [string] $DiagnosticImagePath,
    [string] $OperatorLoopImagePath,
    [string] $NormalImagePath,
    [string] $StaticContractPath,
    [string] $RecoveryGatePath,
    [string] $P0ClosurePath,
    [string] $SourceAuditPath,
    [string] $WhiteRailPath,
    [string] $ReplacementFpcPath,
    [string] $ProgrammerRoot = "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$flashRunner = Join-Path $PSScriptRoot "flash_nucleo_bringup.ps1"
$serialRunner = Join-Path $PSScriptRoot "capture_nucleo_serial.ps1"
$traceVerifier = Join-Path $PSScriptRoot "verify_wb55_vendor_1s_lut_diagnostic_log.py"
$defaultDiagnosticImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_vendor_1s_lut_diagnostic\Companion_Nucleo_WB55RG_Vendor1sLutDiagnostic.hex"
$defaultOperatorLoopImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_vendor_1s_lut_operator_loop_diagnostic\Companion_Nucleo_WB55RG_Vendor1sLutOperatorLoopDiagnostic.hex"
$defaultNormalImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build\Companion_Nucleo_WB55RG_Bringup.hex"
$defaultStaticContract = Join-Path $repoRoot "docs\validation\companion-gdey0154d67-t03-vendor-1s-diagnostic-static-20260720.json"
$defaultRecoveryGate = Join-Path $repoRoot "docs\validation\companion-screen-wb55-hardware-recovery-gate.json"
$defaultP0Closure = Join-Path $repoRoot "docs\validation\companion-gdey0154d67-t03-p0-closure-20260720.json"
$defaultSourceAudit = Join-Path $repoRoot "docs\validation\companion-gdey0154d67-t03-vendor-1s-source-audit-20260720.json"
$defaultWhiteRail = Join-Path $repoRoot "docs\validation\companion-screen-wb55-white-rail-measurement-current-source-20260720.json"
$defaultReplacementFpc = Join-Path $repoRoot "docs\validation\companion-screen-wb55-replacement-fpc-evidence-20260720.json"
$runRoot = if ([string]::IsNullOrWhiteSpace($OutRoot)) {
    Join-Path $repoRoot ".cache\validation\wb55-vendor-1s-lut-current"
} else {
    [System.IO.Path]::GetFullPath($OutRoot)
}
$runReportPath = Join-Path $runRoot "stage-run.json"
$captureRoot = Join-Path $runRoot "capture"
$rawLog = Join-Path $captureRoot "nucleo-serial-raw.log"
$traceReportPath = Join-Path $runRoot "vendor-1s-trace.json"
$operatorResultPath = Join-Path $runRoot "operator-prompt-observation.txt"

function Resolve-ConfiguredPath {
    param([string] $Override, [string] $Default)
    if ([string]::IsNullOrWhiteSpace($Override)) { return $Default }
    if ([System.IO.Path]::IsPathRooted($Override)) { return [System.IO.Path]::GetFullPath($Override) }
    return [System.IO.Path]::GetFullPath((Join-Path $repoRoot $Override))
}

function RelPath {
    param([string] $Path)
    return [System.IO.Path]::GetRelativePath($repoRoot, [System.IO.Path]::GetFullPath($Path)).Replace("\", "/")
}

function Read-RequiredJson {
    param([string] $Path, [string] $Label)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing ${Label}: $Path" }
    try { return Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json -AsHashtable }
    catch { throw "$Label is not valid JSON: $($_.Exception.Message)" }
}

function Assert-StaticAndRecoveryGate {
    param([string] $StaticPath, [string] $GatePath, [string] $P0Path, [string] $AuditPath, [string] $WhiteRailPath, [string] $ReplacementFpcPath, [string] $DiagnosticImagePath, [string] $OperatorLoopImagePath)
    $static = Read-RequiredJson -Path $StaticPath -Label "vendor one-second static contract"
    $gate = Read-RequiredJson -Path $GatePath -Label "current FPC White/Black recovery gate"
    $p0 = Read-RequiredJson -Path $P0Path -Label "current P0 official White/Black closure"
    $audit = Read-RequiredJson -Path $AuditPath -Label "vendor source audit"
    $whiteRail = Read-RequiredJson -Path $WhiteRailPath -Label "current official White rail measurement"
    $replacementFpc = Read-RequiredJson -Path $ReplacementFpcPath -Label "replacement display FPC evidence"
    if ($static.schema_id -ne "companion.wb55.gdey0154d67_t03.vendor_1s_lut_diagnostic_static.v1" -or
        $static.status -ne "PASS_STATIC_OWNER_AUTHORIZED_PRODUCTION_OFF_VENDOR_1S_LUT") {
        throw "Vendor one-second static contract is not passed."
    }
    if ($gate.status -ne "PASS_CURRENT_FPC_OFFICIAL_WHITE_BLACK_RETEST") {
        throw "Current-FPC official White/Black recovery gate is not passed."
    }
    if ($p0.status -ne "PASS_P0_OFFICIAL_FULL_RETEST_LUT_PROMOTION_NO_GO") {
        throw "Current P0 official White/Black closure is not passed."
    }
    if ($audit.machine_status -ne "PASS_AUDIT_COMPLETE" -or
        $audit.promotion_status -ne "NO_GO_PANEL_IDENTITY_UNPROVEN" -or
        $audit.production_off_diagnostic.allowed -ne $false -or
        $audit.command_evidence.production_lut_reference_absent -ne $true) {
        throw "Vendor source audit no longer proves the source-bound, non-production boundary."
    }
    if ($replacementFpc.status -ne "PASS_OWNER_REPORTED_REPLACEMENT_FPC_CURRENT_PANEL_VISIBLE" -or
        $replacementFpc.checks.display_fpc_replaced -ne $true -or
        $replacementFpc.checks.logic_input_is_3v3_only -ne $true) {
        throw "Replacement display FPC evidence is not passed for the current panel."
    }
    if ($whiteRail.status -ne "PASS_MACHINE_AND_RAILS_ESTABLISHED_WHITE" -or
        $whiteRail.checks.positive_and_negative_refresh_rails_established -ne $true -or
        $whiteRail.measurement.available -ne $true -or
        $whiteRail.measurement.prevgh1_max_v -ne 20.0 -or
        $whiteRail.measurement.prevgl1_min_v -ne -20.0) {
        throw "Current official White rail evidence does not prove PREVGH1=+20V and PREVGL1=-20V."
    }
    if ($static.authorization.white_rail.sha256 -ne (Get-FileHash -LiteralPath $WhiteRailPath -Algorithm SHA256).Hash -or
        $static.authorization.replacement_fpc.sha256 -ne (Get-FileHash -LiteralPath $ReplacementFpcPath -Algorithm SHA256).Hash) {
        throw "Vendor one-second static contract does not bind the current White-rail and replacement-FPC artifacts."
    }
    if ($static.images.diagnostic.sha256 -ne (Get-FileHash -LiteralPath $DiagnosticImagePath -Algorithm SHA256).Hash -or
        $static.images.operator_loop.sha256 -ne (Get-FileHash -LiteralPath $OperatorLoopImagePath -Algorithm SHA256).Hash) {
        throw "Vendor one-second diagnostic image hash does not match the source-bound static contract."
    }
    return [ordered]@{
        static_contract = [ordered]@{ path = RelPath $StaticPath; sha256 = (Get-FileHash -LiteralPath $StaticPath -Algorithm SHA256).Hash; status = $static.status }
        recovery_gate = [ordered]@{ path = RelPath $GatePath; sha256 = (Get-FileHash -LiteralPath $GatePath -Algorithm SHA256).Hash; status = $gate.status }
        p0_closure = [ordered]@{ path = RelPath $P0Path; sha256 = (Get-FileHash -LiteralPath $P0Path -Algorithm SHA256).Hash; status = $p0.status }
        source_audit = [ordered]@{ path = RelPath $AuditPath; sha256 = (Get-FileHash -LiteralPath $AuditPath -Algorithm SHA256).Hash; production_off_diagnostic_allowed_by_source_audit = $audit.production_off_diagnostic.allowed; current_room_diagnostic_authorization = "COMP-REQ-168/169/171" }
        white_rail = [ordered]@{ path = RelPath $WhiteRailPath; sha256 = (Get-FileHash -LiteralPath $WhiteRailPath -Algorithm SHA256).Hash; status = $whiteRail.status; prevgh1_max_v = $whiteRail.measurement.prevgh1_max_v; prevgl1_min_v = $whiteRail.measurement.prevgl1_min_v }
        replacement_fpc = [ordered]@{ path = RelPath $ReplacementFpcPath; sha256 = (Get-FileHash -LiteralPath $ReplacementFpcPath -Algorithm SHA256).Hash; status = $replacementFpc.status }
    }
}

function Resolve-Aiw {
    $roots = @()
    if ($env:AI_WORKFLOW_REPO) { $roots += $env:AI_WORKFLOW_REPO }
    $roots += "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow"
    foreach ($root in $roots | Select-Object -Unique) {
        $candidate = Join-Path $root "scripts\aiw.ps1"
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return (Resolve-Path -LiteralPath $candidate).Path }
    }
    throw "Canonical aiw operator-prompt helper was not found."
}

function Invoke-OperatorReview {
    $aiw = Resolve-Aiw
    $output = & pwsh -NoProfile -File $aiw operator-prompt `
        -Title "Companion 原厂 1 秒快刷诊断验收" `
        -ProgressText "1/1（持续循环，最多 360 帧）" `
        -ScopeText "本次仅验证 Good Display 原厂 1 秒 LUT 的独立诊断。不会启用产品动态表情，结束后将恢复正常固件。" `
        -Message "黑色圆点会在六个位置持续循环，你可以稍后再看。每次刷新应明显快于官方全刷；圆点离开后，旧位置不应残留灰点、黑影、白洞或前一帧轮廓。" `
        -ExpectedText "请选择通过仅当你已看清连续移动且没有旧位置残影；备注必须写明速度观感和是否存在残影。温度范围尚未由供应商提供，本次不作全温度结论。" `
        -Input `
        -ReviewStyle `
        -Buttons "通过,失败" `
        -OutputPath $operatorResultPath `
        -TimeoutSeconds $OperatorTimeoutSeconds `
        -Json
    if ($LASTEXITCODE -ne 0) { throw "Canonical operator-prompt failed with exit code $LASTEXITCODE." }
    $result = ($output -join [Environment]::NewLine) | ConvertFrom-Json
    if ([string]::IsNullOrWhiteSpace([string]$result.selected)) { throw "Canonical operator prompt returned no selection." }
    return $result
}

function Write-RunReport {
    param([object] $Report)
    New-Item -ItemType Directory -Force -Path $runRoot | Out-Null
    $Report | ConvertTo-Json -Depth 14 | Set-Content -LiteralPath $runReportPath -Encoding UTF8
    Write-Output "Vendor one-second LUT stage report: $(RelPath $runReportPath)"
}

$modeCount = @($CheckOnly.IsPresent, $Execute.IsPresent | Where-Object { $_ }).Count
if ($modeCount -ne 1) { throw "Use exactly one of -CheckOnly or -Execute." }
if ($Execute -and -not $WorkflowLockHeld) { throw "Refusing vendor one-second LUT hardware execution without workflow lock acknowledgement." }

$diagnosticImage = Resolve-ConfiguredPath -Override $DiagnosticImagePath -Default $defaultDiagnosticImage
$operatorLoopImage = Resolve-ConfiguredPath -Override $OperatorLoopImagePath -Default $defaultOperatorLoopImage
$normalImage = Resolve-ConfiguredPath -Override $NormalImagePath -Default $defaultNormalImage
$staticContract = Resolve-ConfiguredPath -Override $StaticContractPath -Default $defaultStaticContract
$recoveryGate = Resolve-ConfiguredPath -Override $RecoveryGatePath -Default $defaultRecoveryGate
$p0Closure = Resolve-ConfiguredPath -Override $P0ClosurePath -Default $defaultP0Closure
$sourceAudit = Resolve-ConfiguredPath -Override $SourceAuditPath -Default $defaultSourceAudit
$whiteRail = Resolve-ConfiguredPath -Override $WhiteRailPath -Default $defaultWhiteRail
$replacementFpc = Resolve-ConfiguredPath -Override $ReplacementFpcPath -Default $defaultReplacementFpc
$requiredFiles = @($flashRunner, $serialRunner, $traceVerifier, $diagnosticImage, $operatorLoopImage, $normalImage, $staticContract, $recoveryGate, $p0Closure, $sourceAudit, $whiteRail, $replacementFpc)
foreach ($path in $requiredFiles) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required vendor one-second diagnostic input is missing: $path" }
}
$prerequisites = Assert-StaticAndRecoveryGate -StaticPath $staticContract -GatePath $recoveryGate -P0Path $p0Closure -AuditPath $sourceAudit -WhiteRailPath $whiteRail -ReplacementFpcPath $replacementFpc -DiagnosticImagePath $diagnosticImage -OperatorLoopImagePath $operatorLoopImage
$steps = @(
    [ordered]@{ id = "flash_vendor_1s_lut"; command = "pwsh"; arguments = @("-NoProfile", "-File", $flashRunner, "-ImagePath", $diagnosticImage, "-ProgrammerRoot", $ProgrammerRoot) },
    [ordered]@{ id = "capture_vendor_1s_lut"; command = "pwsh"; arguments = @("-NoProfile", "-File", $serialRunner, "-Execute", "-WorkflowLockHeld", "-Seconds", "$CaptureSeconds", "-ResetAfterOpen", "-OutDir", $captureRoot) },
    [ordered]@{ id = "parse_vendor_1s_lut"; command = "python"; arguments = @($traceVerifier, "--log", $rawLog, "--out", $traceReportPath, "--static-contract", $staticContract) },
    [ordered]@{ id = "flash_vendor_1s_lut_operator_loop"; command = "pwsh"; arguments = @("-NoProfile", "-File", $flashRunner, "-ImagePath", $operatorLoopImage, "-ProgrammerRoot", $ProgrammerRoot) },
    [ordered]@{ id = "flash_normal_restore"; command = "pwsh"; arguments = @("-NoProfile", "-File", $flashRunner, "-ImagePath", $normalImage, "-ProgrammerRoot", $ProgrammerRoot) }
)
if (-not [string]::IsNullOrWhiteSpace($Port)) { $steps[1].arguments += @("-Port", $Port) }

$report = [ordered]@{
    schema_id = "companion.wb55.gdey0154d67_t03.vendor_1s_lut_stage_run.v1"
    status = if ($CheckOnly) { "DRY_RUN" } else { "RUNNING" }
    claim_scope = "owner-authorized production-off supplier one-second LUT diagnostic; no temperature-range or production claim"
    target = "NUCLEO-WB55RG + ESP32-FTS02 + GDEY0154D67-T03"
    generated_at = (Get-Date).ToString("o")
    capture_seconds = $CaptureSeconds
    images = [ordered]@{
        diagnostic = [ordered]@{ path = RelPath $diagnosticImage; sha256 = (Get-FileHash -LiteralPath $diagnosticImage -Algorithm SHA256).Hash }
        operator_loop = [ordered]@{ path = RelPath $operatorLoopImage; sha256 = (Get-FileHash -LiteralPath $operatorLoopImage -Algorithm SHA256).Hash; maximum_full_frames = 360 }
        normal_restore = [ordered]@{ path = RelPath $normalImage; sha256 = (Get-FileHash -LiteralPath $normalImage -Algorithm SHA256).Hash }
    }
    prerequisites = $prerequisites
    output = [ordered]@{ root = RelPath $runRoot; trace = RelPath $traceReportPath; run_report = RelPath $runReportPath }
    operator_review = [ordered]@{ required = $true; invoked = $false; style = "aiw_operator_prompt_v1"; output_path = RelPath $operatorResultPath; selected = $null; note = $null }
    safety = [ordered]@{ default_disabled_diagnostic = $true; machine_six_frame_pass_then_bounded_360_frame_operator_loop = $true; review_start_delay_ms = 5000; normal_firmware_restore_required = $true; no_temperature_claim = $true; no_production_promotion = $true }
    steps = $steps
    results = @()
    normal_firmware_restored = $false
}

if ($CheckOnly) {
    $report.completed_at = (Get-Date).ToString("o")
    Write-RunReport -Report $report
    Write-Output "CHECK: vendor one-second LUT diagnostic is preflight-valid and will not touch hardware."
    exit 0
}

$results = @()
$diagnosticFlashed = $false
$normalRestored = $false
try {
    foreach ($step in $steps[0..2]) {
        $started = Get-Date
        & $step.command @($step.arguments)
        $exitCode = $LASTEXITCODE
        $results += [ordered]@{ id = $step.id; status = if ($exitCode -eq 0) { "PASS" } else { "FAIL" }; exit_code = $exitCode; started_at = $started.ToString("o"); ended_at = (Get-Date).ToString("o") }
        if ($exitCode -ne 0) { throw "$($step.id) failed with exit code $exitCode." }
        if ($step.id -eq "flash_vendor_1s_lut") { $diagnosticFlashed = $true }
    }
    $operatorLoop = $steps[3]
    $started = Get-Date
    & $operatorLoop.command @($operatorLoop.arguments)
    $operatorLoopExit = $LASTEXITCODE
    $results += [ordered]@{ id = $operatorLoop.id; status = if ($operatorLoopExit -eq 0) { "PASS" } else { "FAIL" }; exit_code = $operatorLoopExit; started_at = $started.ToString("o"); ended_at = (Get-Date).ToString("o") }
    if ($operatorLoopExit -ne 0) { throw "Vendor one-second LUT operator loop flash failed with exit code $operatorLoopExit." }
    $diagnosticFlashed = $true
    $report.operator_review.invoked = $true
    $operator = Invoke-OperatorReview
    $report.operator_review.selected = [string]$operator.selected
    $report.operator_review.note = [string]$operator.text
    if ($report.operator_review.selected -ne "通过") { throw "Operator did not pass vendor one-second LUT diagnostic." }
    if ([string]::IsNullOrWhiteSpace($report.operator_review.note)) { throw "Operator passed vendor one-second LUT diagnostic without a physical observation note." }
    $restore = $steps[4]
    $started = Get-Date
    & $restore.command @($restore.arguments)
    $restoreExit = $LASTEXITCODE
    $normalRestored = $restoreExit -eq 0
    $results += [ordered]@{ id = $restore.id; status = if ($normalRestored) { "PASS" } else { "FAIL" }; exit_code = $restoreExit; started_at = $started.ToString("o"); ended_at = (Get-Date).ToString("o") }
    if (-not $normalRestored) { throw "Normal firmware restore after vendor one-second LUT diagnostic failed." }
    $report.status = "PASS_MACHINE_AND_OPERATOR_VENDOR_1S_LUT_DIAGNOSTIC_NORMAL_RESTORED"
} catch {
    $report.status = "FAIL"
    $report.error = $_.Exception.Message
    if ($diagnosticFlashed -and -not $normalRestored) {
        $restore = $steps[4]
        $started = Get-Date
        & $restore.command @($restore.arguments)
        $restoreExit = $LASTEXITCODE
        $normalRestored = $restoreExit -eq 0
        $results += [ordered]@{ id = "flash_normal_restore_after_failure"; status = if ($normalRestored) { "PASS" } else { "FAIL" }; exit_code = $restoreExit; started_at = $started.ToString("o"); ended_at = (Get-Date).ToString("o") }
    }
    throw
} finally {
    $report.results = @($results)
    $report.normal_firmware_restored = [bool]$normalRestored
    $report.completed_at = (Get-Date).ToString("o")
    Write-RunReport -Report $report
}
