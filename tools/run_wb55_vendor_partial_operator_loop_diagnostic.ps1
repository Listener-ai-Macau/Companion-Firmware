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
    [string] $NormalImagePath,
    [string] $StaticContractPath,
    [string] $RecoveryGatePath,
    [string] $ProgrammerRoot = "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$flashRunner = Join-Path $PSScriptRoot "flash_nucleo_bringup.ps1"
$serialRunner = Join-Path $PSScriptRoot "capture_nucleo_serial.ps1"
$traceVerifier = Join-Path $PSScriptRoot "verify_wb55_vendor_partial_operator_loop_log.py"
$defaultDiagnosticImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_vendor_partial_operator_loop_diagnostic\Companion_Nucleo_WB55RG_VendorPartialOperatorLoopDiagnostic.hex"
$defaultNormalImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build\Companion_Nucleo_WB55RG_Bringup.hex"
$defaultStaticContract = Join-Path $repoRoot "docs\validation\companion-gdey0154d67-t03-vendor-partial-operator-loop-static-20260720.json"
$defaultRecoveryGate = Join-Path $repoRoot "docs\validation\companion-screen-wb55-hardware-recovery-gate.json"
$runRoot = if ([string]::IsNullOrWhiteSpace($OutRoot)) {
    Join-Path $repoRoot ".cache\validation\wb55-vendor-partial-operator-loop-current"
} else {
    [System.IO.Path]::GetFullPath($OutRoot)
}
$runReportPath = Join-Path $runRoot "stage-run.json"
$captureRoot = Join-Path $runRoot "capture"
$rawLog = Join-Path $captureRoot "nucleo-serial-raw.log"
$traceReportPath = Join-Path $runRoot "vendor-partial-trace.json"
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
    param([string] $StaticPath, [string] $GatePath)
    $static = Read-RequiredJson -Path $StaticPath -Label "vendor partial static contract"
    $gate = Read-RequiredJson -Path $GatePath -Label "current FPC White/Black recovery gate"
    if ($static.schema_id -ne "companion.wb55.gdey0154d67_t03.vendor_partial_operator_loop_static.v1" -or
        $static.status -ne "PASS_STATIC_OWNER_AUTHORIZED_PRODUCTION_OFF_VENDOR_PARTIAL_OPERATOR_LOOP") {
        throw "Vendor partial static contract is not passed."
    }
    if ($gate.status -ne "PASS_CURRENT_FPC_OFFICIAL_WHITE_BLACK_RETEST") {
        throw "Current-FPC official White/Black recovery gate is not passed."
    }
    return [ordered]@{
        static_contract = [ordered]@{ path = RelPath $StaticPath; sha256 = (Get-FileHash -LiteralPath $StaticPath -Algorithm SHA256).Hash; status = $static.status }
        recovery_gate = [ordered]@{ path = RelPath $GatePath; sha256 = (Get-FileHash -LiteralPath $GatePath -Algorithm SHA256).Hash; status = $gate.status }
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
        -Title "Companion 原厂局刷快刷诊断验收" `
        -ProgressText "1/1（持续局部更新，最多 360 帧）" `
        -ScopeText "本次只验证 Good Display 原厂局刷路径。第一帧会建立基图；之后只写变化区域。不会启用产品动态表情，结束后将恢复正常固件。" `
        -Message "黑色圆点会在六个位置持续循环。首次基图后，观察圆点移动时屏幕是否避免整屏闪动；旧位置不应残留灰点、黑影、白洞或前一帧轮廓。" `
        -ExpectedText "请选择通过仅当后续移动不再出现整屏闪动，且你观察不到旧位置残影；备注必须写明局刷速度、整屏闪动和残影。温度范围尚未由供应商提供，本次不作全温度结论。" `
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
    Write-Output "Vendor partial operator-loop stage report: $(RelPath $runReportPath)"
}

$modeCount = @($CheckOnly.IsPresent, $Execute.IsPresent | Where-Object { $_ }).Count
if ($modeCount -ne 1) { throw "Use exactly one of -CheckOnly or -Execute." }
if ($Execute -and -not $WorkflowLockHeld) { throw "Refusing vendor partial hardware execution without workflow lock acknowledgement." }

$diagnosticImage = Resolve-ConfiguredPath -Override $DiagnosticImagePath -Default $defaultDiagnosticImage
$normalImage = Resolve-ConfiguredPath -Override $NormalImagePath -Default $defaultNormalImage
$staticContract = Resolve-ConfiguredPath -Override $StaticContractPath -Default $defaultStaticContract
$recoveryGate = Resolve-ConfiguredPath -Override $RecoveryGatePath -Default $defaultRecoveryGate
$requiredFiles = @($flashRunner, $serialRunner, $traceVerifier, $diagnosticImage, $normalImage, $staticContract, $recoveryGate)
foreach ($path in $requiredFiles) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required vendor partial diagnostic input is missing: $path" }
}
$prerequisites = Assert-StaticAndRecoveryGate -StaticPath $staticContract -GatePath $recoveryGate
$steps = @(
    [ordered]@{ id = "flash_vendor_partial_operator_loop"; command = "pwsh"; arguments = @("-NoProfile", "-File", $flashRunner, "-ImagePath", $diagnosticImage, "-ProgrammerRoot", $ProgrammerRoot) },
    [ordered]@{ id = "capture_vendor_partial_operator_loop"; command = "pwsh"; arguments = @("-NoProfile", "-File", $serialRunner, "-Execute", "-WorkflowLockHeld", "-Seconds", "$CaptureSeconds", "-ResetAfterOpen", "-OutDir", $captureRoot) },
    [ordered]@{ id = "parse_vendor_partial_operator_loop"; command = "python"; arguments = @($traceVerifier, "--log", $rawLog, "--out", $traceReportPath, "--static-contract", $staticContract) },
    [ordered]@{ id = "flash_vendor_partial_operator_loop_for_review"; command = "pwsh"; arguments = @("-NoProfile", "-File", $flashRunner, "-ImagePath", $diagnosticImage, "-ProgrammerRoot", $ProgrammerRoot) },
    [ordered]@{ id = "flash_normal_restore"; command = "pwsh"; arguments = @("-NoProfile", "-File", $flashRunner, "-ImagePath", $normalImage, "-ProgrammerRoot", $ProgrammerRoot) }
)
if (-not [string]::IsNullOrWhiteSpace($Port)) { $steps[1].arguments += @("-Port", $Port) }

$report = [ordered]@{
    schema_id = "companion.wb55.gdey0154d67_t03.vendor_partial_operator_loop_stage_run.v1"
    status = if ($CheckOnly) { "DRY_RUN" } else { "RUNNING" }
    claim_scope = "owner-authorized production-off supplier partial-refresh comparator; no ghosting, temperature-range or production claim"
    target = "NUCLEO-WB55RG + ESP32-FTS02 + GDEY0154D67-T03"
    generated_at = (Get-Date).ToString("o")
    capture_seconds = $CaptureSeconds
    images = [ordered]@{
        diagnostic = [ordered]@{ path = RelPath $diagnosticImage; sha256 = (Get-FileHash -LiteralPath $diagnosticImage -Algorithm SHA256).Hash; maximum_frames = 360 }
        normal_restore = [ordered]@{ path = RelPath $normalImage; sha256 = (Get-FileHash -LiteralPath $normalImage -Algorithm SHA256).Hash }
    }
    prerequisites = $prerequisites
    output = [ordered]@{ root = RelPath $runRoot; trace = RelPath $traceReportPath; run_report = RelPath $runReportPath }
    operator_review = [ordered]@{ required = $true; invoked = $false; style = "aiw_operator_prompt_v1"; output_path = RelPath $operatorResultPath; selected = $null; note = $null }
    safety = [ordered]@{ default_disabled_diagnostic = $true; machine_pass_then_bounded_360_frame_source_partial_operator_loop = $true; review_start_delay_ms = 5000; normal_firmware_restore_required = $true; no_temperature_claim = $true; no_production_promotion = $true }
    steps = $steps
    results = @()
    normal_firmware_restored = $false
}

if ($CheckOnly) {
    $report.completed_at = (Get-Date).ToString("o")
    Write-RunReport -Report $report
    Write-Output "CHECK: vendor partial operator-loop diagnostic is preflight-valid and will not touch hardware."
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
        if ($step.id -eq "flash_vendor_partial_operator_loop") { $diagnosticFlashed = $true }
    }
    $review = $steps[3]
    $started = Get-Date
    & $review.command @($review.arguments)
    $reviewExit = $LASTEXITCODE
    $results += [ordered]@{ id = $review.id; status = if ($reviewExit -eq 0) { "PASS" } else { "FAIL" }; exit_code = $reviewExit; started_at = $started.ToString("o"); ended_at = (Get-Date).ToString("o") }
    if ($reviewExit -ne 0) { throw "Vendor partial operator review flash failed with exit code $reviewExit." }
    $diagnosticFlashed = $true
    $report.operator_review.invoked = $true
    $operator = Invoke-OperatorReview
    $report.operator_review.selected = [string]$operator.selected
    $report.operator_review.note = [string]$operator.text
    if ($report.operator_review.selected -ne "通过") { throw "Operator did not pass vendor partial operator-loop diagnostic." }
    if ([string]::IsNullOrWhiteSpace($report.operator_review.note)) { throw "Operator passed vendor partial operator-loop diagnostic without a physical observation note." }
    $restore = $steps[4]
    $started = Get-Date
    & $restore.command @($restore.arguments)
    $restoreExit = $LASTEXITCODE
    $normalRestored = $restoreExit -eq 0
    $results += [ordered]@{ id = $restore.id; status = if ($normalRestored) { "PASS" } else { "FAIL" }; exit_code = $restoreExit; started_at = $started.ToString("o"); ended_at = (Get-Date).ToString("o") }
    if (-not $normalRestored) { throw "Normal firmware restore after vendor partial operator-loop diagnostic failed." }
    $report.status = "PASS_MACHINE_AND_OPERATOR_VENDOR_PARTIAL_OPERATOR_LOOP_NORMAL_RESTORED"
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
