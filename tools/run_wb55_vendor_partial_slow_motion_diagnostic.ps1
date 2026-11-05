param(
    [switch] $CheckOnly,
    [switch] $Execute,
    [switch] $WorkflowLockHeld,
    [switch] $OldNewRam,
    [switch] $T03FastState,
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
$traceVerifier = Join-Path $PSScriptRoot $(if ($T03FastState) { "verify_wb55_vendor_t03_fast_state_log.py" } elseif ($OldNewRam) { "verify_wb55_vendor_partial_old_new_ram_log.py" } else { "verify_wb55_vendor_partial_slow_motion_log.py" })
$defaultDiagnosticImage = Join-Path $repoRoot $(if ($T03FastState) { "cubeide\Companion_Nucleo_WB55RG_Bringup\build_vendor_t03_fast_state_diagnostic\Companion_Nucleo_WB55RG_VendorT03FastStateDiagnostic.hex" } elseif ($OldNewRam) { "cubeide\Companion_Nucleo_WB55RG_Bringup\build_vendor_partial_old_new_ram_diagnostic\Companion_Nucleo_WB55RG_VendorPartialOldNewRamDiagnostic.hex" } else { "cubeide\Companion_Nucleo_WB55RG_Bringup\build_vendor_partial_slow_motion_diagnostic\Companion_Nucleo_WB55RG_VendorPartialSlowMotionDiagnostic.hex" })
$defaultNormalImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build\Companion_Nucleo_WB55RG_Bringup.hex"
$defaultStaticContract = Join-Path $repoRoot $(if ($T03FastState) { "docs\validation\companion-gdey0154d67-t03-vendor-t03-fast-state-static-20260720.json" } elseif ($OldNewRam) { "docs\validation\companion-gdey0154d67-t03-vendor-partial-old-new-ram-static-20260720.json" } else { "docs\validation\companion-gdey0154d67-t03-vendor-partial-slow-motion-static-20260720.json" })
$defaultRecoveryGate = Join-Path $repoRoot "docs\validation\companion-screen-wb55-hardware-recovery-gate.json"
$runRoot = if ([string]::IsNullOrWhiteSpace($OutRoot)) {
    Join-Path $repoRoot ".cache\validation\wb55-vendor-partial-slow-motion-current"
} else {
    [System.IO.Path]::GetFullPath($OutRoot)
}
$runReportPath = Join-Path $runRoot $(if ($CheckOnly) { "preflight-stage-run.json" } else { "stage-run.json" })
$captureRoot = Join-Path $runRoot "capture"
$rawLog = Join-Path $captureRoot "nucleo-serial-raw.log"
$traceReportPath = Join-Path $runRoot $(if ($T03FastState) { "vendor-t03-fast-state-trace.json" } else { "vendor-partial-slow-motion-trace.json" })
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
    param([string] $StaticPath, [string] $GatePath, [switch] $OldNewRam, [switch] $T03FastState)
    $static = Read-RequiredJson -Path $StaticPath -Label "vendor partial slow-motion static contract"
    $gate = Read-RequiredJson -Path $GatePath -Label "current FPC White/Black recovery gate"
    $expectedSchema = if ($T03FastState) { "companion.wb55.gdey0154d67_t03.vendor_t03_fast_state_static.v1" } elseif ($OldNewRam) { "companion.wb55.gdey0154d67_t03.vendor_partial_old_new_ram_static.v1" } else { "companion.wb55.gdey0154d67_t03.vendor_partial_slow_motion_static.v1" }
    $expectedStatus = if ($T03FastState) { "PASS_STATIC_OWNER_AUTHORIZED_VENDOR_T03_FAST_STATE_AB" } elseif ($OldNewRam) { "PASS_STATIC_OWNER_AUTHORIZED_VENDOR_PARTIAL_OLD_NEW_RAM_AB" } else { "PASS_STATIC_OWNER_AUTHORIZED_PRODUCTION_OFF_VENDOR_PARTIAL_SLOW_MOTION" }
    if ($static.schema_id -ne $expectedSchema -or $static.status -ne $expectedStatus) {
        throw "Vendor partial slow-motion static contract is not passed."
    }
    $maximumRegionBytes = if ($T03FastState -or $OldNewRam) { $static.controlled_behavior.maximum_region_bytes_per_plane } else { $static.accepted_single_region_comparator.maximum_accepted_region_bytes }
    if ($maximumRegionBytes -ne 567) {
        throw "Slow-motion comparator must retain the accepted 567-byte region ceiling."
    }
    if ($gate.status -ne "PASS_CURRENT_FPC_OFFICIAL_WHITE_BLACK_RETEST") {
        throw "Current-FPC official White/Black recovery gate is not passed."
    }
    return [ordered]@{
        static_contract = [ordered]@{ path = RelPath $StaticPath; sha256 = (Get-FileHash -LiteralPath $StaticPath -Algorithm SHA256).Hash; status = $static.status }
        recovery_gate = [ordered]@{ path = RelPath $GatePath; sha256 = (Get-FileHash -LiteralPath $GatePath -Algorithm SHA256).Hash; status = $gate.status }
        maximum_accepted_region_bytes_per_plane = 567
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
    param([switch] $OldNewRam, [switch] $T03FastState)
    $aiw = Resolve-Aiw
    $title = if ($T03FastState) { "Companion T03 原厂快状态局刷诊断" } elseif ($OldNewRam) { "Companion 局刷旧新 RAM 对比诊断" } else { "Companion 原厂局刷连续移动诊断" }
    $scope = if ($T03FastState) { "本次只比较 Good Display 精确 T03 STM32 样例的内建温度/OTP 快状态基图与原厂 0x24-only 局刷。局刷期间不会执行全刷；结束后恢复正常固件。不会启用产品动态表情。" } elseif ($OldNewRam) { "本次只比较 Good Display 官方方法的旧帧 0x26 与新帧 0x24 局部 RAM 同步。波形控制字不变，结束后恢复正常固件。不会启用产品动态表情。" } else { "本次只验证 Good Display 原厂局刷的慢位移传输。第一帧建立基图；后续每帧只写旧/新位置区域，结束后恢复正常固件。不会启用产品动态表情。" }
    $output = & pwsh -NoProfile -File $aiw operator-prompt `
        -Title $title `
        -ProgressText "1/1（48 个中间位置，持续局刷）" `
        -ScopeText $scope `
        -Message "黑色圆点将沿一段路径一点点移动并持续循环。请看移动是否连续、是否仍有整屏闪动，以及旧位置残影、黑影或白洞会不会累积到干扰观看。" `
        -ExpectedText "通过仅表示连续小步移动可观察且后续无整屏闪动；残影不是自动忽略项，必须在备注写明有无、程度及是否累积或干扰运动。失败表示运动断跳、整屏闪动或残影已不能接受。供应商未提供温度分档，本次不作全温度或产品结论。" `
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
    Write-Output "Vendor partial slow-motion stage report: $(RelPath $runReportPath)"
}

$modeCount = @($CheckOnly.IsPresent, $Execute.IsPresent | Where-Object { $_ }).Count
if ($modeCount -ne 1) { throw "Use exactly one of -CheckOnly or -Execute." }
if ($OldNewRam -and $T03FastState) { throw "Use only one vendor partial comparator at a time." }
if ($Execute -and -not $WorkflowLockHeld) { throw "Refusing vendor partial slow-motion hardware execution without workflow lock acknowledgement." }

$diagnosticImage = Resolve-ConfiguredPath -Override $DiagnosticImagePath -Default $defaultDiagnosticImage
$normalImage = Resolve-ConfiguredPath -Override $NormalImagePath -Default $defaultNormalImage
$staticContract = Resolve-ConfiguredPath -Override $StaticContractPath -Default $defaultStaticContract
$recoveryGate = Resolve-ConfiguredPath -Override $RecoveryGatePath -Default $defaultRecoveryGate
$requiredFiles = @($flashRunner, $serialRunner, $traceVerifier, $diagnosticImage, $normalImage, $staticContract, $recoveryGate)
foreach ($path in $requiredFiles) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required vendor partial slow-motion input is missing: $path" }
}
$prerequisites = Assert-StaticAndRecoveryGate -StaticPath $staticContract -GatePath $recoveryGate -OldNewRam:$OldNewRam -T03FastState:$T03FastState
$steps = @(
    [ordered]@{ id = "flash_vendor_partial_slow_motion"; command = "pwsh"; arguments = @("-NoProfile", "-File", $flashRunner, "-ImagePath", $diagnosticImage, "-ProgrammerRoot", $ProgrammerRoot) },
    [ordered]@{ id = "capture_vendor_partial_slow_motion"; command = "pwsh"; arguments = @("-NoProfile", "-File", $serialRunner, "-Execute", "-WorkflowLockHeld", "-Seconds", "$CaptureSeconds", "-ResetAfterOpen", "-OutDir", $captureRoot) },
    [ordered]@{ id = "parse_vendor_partial_slow_motion"; command = "python"; arguments = @($traceVerifier, "--log", $rawLog, "--out", $traceReportPath, "--static-contract", $staticContract) },
    [ordered]@{ id = "flash_vendor_partial_slow_motion_for_review"; command = "pwsh"; arguments = @("-NoProfile", "-File", $flashRunner, "-ImagePath", $diagnosticImage, "-ProgrammerRoot", $ProgrammerRoot) },
    [ordered]@{ id = "flash_normal_restore"; command = "pwsh"; arguments = @("-NoProfile", "-File", $flashRunner, "-ImagePath", $normalImage, "-ProgrammerRoot", $ProgrammerRoot) }
)
if (-not [string]::IsNullOrWhiteSpace($Port)) { $steps[1].arguments += @("-Port", $Port) }

$report = [ordered]@{
    schema_id = if ($T03FastState) { "companion.wb55.gdey0154d67_t03.vendor_t03_fast_state_stage_run.v1" } elseif ($OldNewRam) { "companion.wb55.gdey0154d67_t03.vendor_partial_old_new_ram_stage_run.v1" } else { "companion.wb55.gdey0154d67_t03.vendor_partial_slow_motion_stage_run.v1" }
    status = if ($CheckOnly) { "DRY_RUN" } else { "RUNNING" }
    claim_scope = if ($T03FastState) { "owner-authorized production-off exact-T03 fast-state A/B; no external LUT, residue-free, temperature-range or production claim" } elseif ($OldNewRam) { "owner-authorized production-off old/new RAM A/B; no LUT, residue-free, temperature-range or production claim" } else { "owner-authorized production-off source-partial slow-position comparator; no ghosting, temperature-range or production claim" }
    target = "NUCLEO-WB55RG + ESP32-FTS02 + GDEY0154D67-T03"
    generated_at = (Get-Date).ToString("o")
    capture_seconds = $CaptureSeconds
    images = [ordered]@{
        diagnostic = [ordered]@{ path = RelPath $diagnosticImage; sha256 = (Get-FileHash -LiteralPath $diagnosticImage -Algorithm SHA256).Hash; maximum_frames = 360; intermediate_positions = 48 }
        normal_restore = [ordered]@{ path = RelPath $normalImage; sha256 = (Get-FileHash -LiteralPath $normalImage -Algorithm SHA256).Hash }
    }
    prerequisites = $prerequisites
    output = [ordered]@{ root = RelPath $runRoot; trace = RelPath $traceReportPath; run_report = RelPath $runReportPath }
    operator_review = [ordered]@{ required = $true; invoked = $false; style = "aiw_operator_prompt_v1"; output_path = RelPath $operatorResultPath; selected = $null; note = $null; residue_observed = $null; residue_accumulates_or_disrupts = $null }
    safety = [ordered]@{ default_disabled_diagnostic = $true; machine_trace_must_not_exceed_accepted_567_byte_region_limit = $true; old_new_ram_ab = [bool]$OldNewRam; t03_fast_state_ab = [bool]$T03FastState; source_reset_bounded_one_or_two_region_update_only = $true; normal_firmware_restore_required = $true; no_temperature_claim = $true; no_production_promotion = $true }
    steps = $steps
    results = @()
    normal_firmware_restored = $false
}

if ($CheckOnly) {
    $report.completed_at = (Get-Date).ToString("o")
    Write-RunReport -Report $report
    Write-Output "CHECK: vendor partial slow-motion diagnostic is preflight-valid and will not touch hardware."
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
        if ($step.id -eq "flash_vendor_partial_slow_motion") { $diagnosticFlashed = $true }
    }
    $review = $steps[3]
    $started = Get-Date
    & $review.command @($review.arguments)
    $reviewExit = $LASTEXITCODE
    $results += [ordered]@{ id = $review.id; status = if ($reviewExit -eq 0) { "PASS" } else { "FAIL" }; exit_code = $reviewExit; started_at = $started.ToString("o"); ended_at = (Get-Date).ToString("o") }
    if ($reviewExit -ne 0) { throw "Vendor partial slow-motion review flash failed with exit code $reviewExit." }
    $diagnosticFlashed = $true
    $report.operator_review.invoked = $true
    $operator = Invoke-OperatorReview -OldNewRam:$OldNewRam -T03FastState:$T03FastState
    $report.operator_review.selected = [string]$operator.selected
    $report.operator_review.note = [string]$operator.text
    $report.operator_review.residue_observed = [bool]($report.operator_review.note -match "残影|拖尾|黑影|白洞|灰影|以前的现象|和以前一样")
    $report.operator_review.residue_accumulates_or_disrupts = [bool]($report.operator_review.note -match "累积|加重|干扰|明显")
    if ($report.operator_review.selected -ne "通过") { throw "Operator did not pass vendor partial slow-motion diagnostic." }
    if ([string]::IsNullOrWhiteSpace($report.operator_review.note)) { throw "Operator passed vendor partial slow-motion diagnostic without a physical observation note." }
    $restore = $steps[4]
    $started = Get-Date
    & $restore.command @($restore.arguments)
    $restoreExit = $LASTEXITCODE
    $normalRestored = $restoreExit -eq 0
    $results += [ordered]@{ id = $restore.id; status = if ($normalRestored) { "PASS" } else { "FAIL" }; exit_code = $restoreExit; started_at = $started.ToString("o"); ended_at = (Get-Date).ToString("o") }
    if (-not $normalRestored) { throw "Normal firmware restore after vendor partial slow-motion diagnostic failed." }
    $report.status = if ($T03FastState -and $report.operator_review.residue_observed) {
        "PASS_MACHINE_AND_OPERATOR_VENDOR_T03_FAST_STATE_RESIDUE_OBSERVED_NORMAL_RESTORED"
    } elseif ($T03FastState) {
        "PASS_MACHINE_AND_OPERATOR_VENDOR_T03_FAST_STATE_NORMAL_RESTORED"
    } elseif ($OldNewRam -and $report.operator_review.residue_observed) {
        "PASS_MACHINE_AND_OPERATOR_VENDOR_PARTIAL_OLD_NEW_RAM_RESIDUE_OBSERVED_NORMAL_RESTORED"
    } elseif ($OldNewRam) {
        "PASS_MACHINE_AND_OPERATOR_VENDOR_PARTIAL_OLD_NEW_RAM_NORMAL_RESTORED"
    } elseif ($report.operator_review.residue_observed) {
        "PASS_MACHINE_AND_OPERATOR_VENDOR_PARTIAL_SLOW_MOTION_RESIDUE_OBSERVED_NORMAL_RESTORED"
    } else {
        "PASS_MACHINE_AND_OPERATOR_VENDOR_PARTIAL_SLOW_MOTION_NORMAL_RESTORED"
    }
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
