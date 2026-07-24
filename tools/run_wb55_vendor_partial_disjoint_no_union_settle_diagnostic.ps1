param(
    [switch]$CheckOnly,
    [switch]$Execute,
    [switch]$WorkflowLockHeld,
    [switch]$ReusePassedMachineTrace,
    [ValidateRange(75, 180)]
    [int]$CaptureSeconds = 90,
    [ValidateRange(60, 3600)]
    [int]$OperatorTimeoutSeconds = 900,
    [string]$Port,
    [string]$OutRoot,
    [string]$ProgrammerRoot = "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$staticVerifier = Join-Path $PSScriptRoot "verify_wb55_vendor_partial_disjoint_no_union_settle_diagnostic.py"
$hardwarePrerequisiteVerifier = Join-Path $PSScriptRoot "verify_wb55_vendor_partial_disjoint_no_union_settle_hardware_prerequisite.py"
$traceVerifier = Join-Path $PSScriptRoot "verify_wb55_vendor_partial_disjoint_no_union_settle_log.py"
$flashRunner = Join-Path $PSScriptRoot "flash_nucleo_bringup.ps1"
$serialRunner = Join-Path $PSScriptRoot "capture_nucleo_serial.ps1"
$staticContract = Join-Path $repoRoot "docs\validation\companion-gdey0154d67-t03-vendor-partial-disjoint-no-union-settle-static-20260721.json"
$hardwarePrerequisite = Join-Path $repoRoot "docs\validation\companion-gdey0154d67-t03-vendor-partial-disjoint-no-union-settle-r2-hardware-prerequisite-20260721.json"
$diagnosticImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_vendor_partial_disjoint_no_union_settle_diagnostic\Companion_Nucleo_WB55RG_VendorPartialDisjointNoUnionSettleDiagnostic.hex"
$observerImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_vendor_partial_disjoint_no_union_settle_operator_loop_diagnostic\Companion_Nucleo_WB55RG_VendorPartialDisjointNoUnionSettleOperatorLoopDiagnostic.hex"
$normalImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build\Companion_Nucleo_WB55RG_Bringup.hex"
$runRoot = if ([string]::IsNullOrWhiteSpace($OutRoot)) {
    Join-Path $repoRoot ".cache\validation\wb55-vendor-partial-disjoint-no-union-settle-current"
} else {
    [System.IO.Path]::GetFullPath($OutRoot)
}
$reportPath = Join-Path $runRoot $(if ($CheckOnly) { "preflight-stage-run.json" } else { "stage-run.json" })
$captureRoot = Join-Path $runRoot "capture"
$rawLog = Join-Path $captureRoot "nucleo-serial-raw.log"
$tracePath = Join-Path $runRoot "vendor-partial-disjoint-no-union-settle-trace.json"
$operatorPath = Join-Path $runRoot "operator-prompt-observation.txt"

function RelPath([string]$Path) {
    return [System.IO.Path]::GetRelativePath($repoRoot, [System.IO.Path]::GetFullPath($Path)).Replace("\", "/")
}

function Read-Json([string]$Path, [string]$Label) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing ${Label}: $Path" }
    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json -AsHashtable
}

function Resolve-Aiw {
    $roots = @()
    if ($env:AI_WORKFLOW_REPO) { $roots += $env:AI_WORKFLOW_REPO }
    $roots += "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow"
    foreach ($root in $roots | Select-Object -Unique) {
        $candidate = Join-Path $root "scripts\aiw.ps1"
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    throw "Canonical aiw operator-prompt helper was not found."
}

function Write-Report([hashtable]$Report) {
    New-Item -ItemType Directory -Force -Path $runRoot | Out-Null
    $Report | ConvertTo-Json -Depth 14 | Set-Content -LiteralPath $reportPath -Encoding UTF8
    Write-Output "Disjoint no-union settle report: $(RelPath $reportPath)"
}

function Assert-NoForeignOperatorPrompt {
    $foreignPrompts = @(
        Get-CimInstance Win32_Process |
            Where-Object {
                $_.ProcessId -ne $PID -and
                -not [string]::IsNullOrWhiteSpace($_.CommandLine) -and
                $_.CommandLine -match '(?i)operator_prompt\.ps1'
            }
    )
    if ($foreignPrompts.Count -ne 0) {
        $ids = ($foreignPrompts | ForEach-Object { $_.ProcessId }) -join ", "
        throw "Another canonical operator review window is already open (PID: $ids); refusing to flash this diagnostic."
    }
}

$modeCount = @($CheckOnly.IsPresent, $Execute.IsPresent | Where-Object { $_ }).Count
if ($modeCount -ne 1) { throw "Use exactly one of -CheckOnly or -Execute." }
if ($Execute -and -not $WorkflowLockHeld) {
    throw "Refusing hardware execution without -WorkflowLockHeld."
}
if ($CheckOnly -and $ReusePassedMachineTrace) {
    throw "-ReusePassedMachineTrace is an execution-only optimization."
}
if ($Execute) {
    Assert-NoForeignOperatorPrompt
}
foreach ($path in @($staticVerifier, $hardwarePrerequisiteVerifier, $traceVerifier, $flashRunner, $serialRunner, $hardwarePrerequisite, $diagnosticImage, $observerImage, $normalImage)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required diagnostic input is missing: $path" }
}

& python $staticVerifier
if ($LASTEXITCODE -ne 0) { throw "Static disjoint no-union settle verifier failed." }
& python $hardwarePrerequisiteVerifier
if ($LASTEXITCODE -ne 0) { throw "Replacement-FPC/White/Black/rail prerequisite verifier failed." }
$static = Read-Json $staticContract "static disjoint no-union settle contract"
$recovery = Read-Json $hardwarePrerequisite "versioned r2 hardware prerequisite"
if ($static.status -ne "PASS_STATIC_SOURCE_EXACT_DISJOINT_NO_UNION_SETTLE_DEFAULT_OFF") {
    throw "Static contract is not passed."
}
if ($recovery.status -ne "PASS_R2_HARDWARE_PREREQUISITE_DISJOINT_NO_UNION_SETTLE_UNPROVEN") {
    throw "Replacement-FPC/White/Black/rail prerequisite is not passed."
}

$report = [ordered]@{
    schema_id = "companion.wb55.gdey0154d67_t03.vendor_partial_disjoint_no_union_settle_stage_run.v1"
    status = if ($CheckOnly) { "READY_NO_HARDWARE_CONTACT" } else { "RUNNING" }
    claim_scope = "production-off two-pass erase-then-disjoint-draw supplier-topology diagnostic only; no temperature, residue-free, production, or OLED-like continuity claim"
    target = "NUCLEO-WB55RG + ESP32-FTS02 + GDEY0154D67-T03"
    generated_at = (Get-Date).ToString("o")
    prerequisite = [ordered]@{
        static_contract = [ordered]@{ path = RelPath $staticContract; sha256 = (Get-FileHash -LiteralPath $staticContract -Algorithm SHA256).Hash; status = $static.status }
        r2_hardware_prerequisite = [ordered]@{ path = RelPath $hardwarePrerequisite; sha256 = (Get-FileHash -LiteralPath $hardwarePrerequisite -Algorithm SHA256).Hash; status = $recovery.status }
    }
    images = [ordered]@{
        diagnostic = [ordered]@{ path = RelPath $diagnosticImage; sha256 = (Get-FileHash -LiteralPath $diagnosticImage -Algorithm SHA256).Hash; frame_count = 50; partial_steps = 48; identical_frame_steps = 1; probe_geometry = "single 12 px ball, five-anchor 42 px orbit, 8 steps per segment" }
        observer = [ordered]@{ path = RelPath $observerImage; sha256 = (Get-FileHash -LiteralPath $observerImage -Algorithm SHA256).Hash; diagnostic_repeats = 360; diagnostic_interval_ms = 250 }
        normal_restore = [ordered]@{ path = RelPath $normalImage; sha256 = (Get-FileHash -LiteralPath $normalImage -Algorithm SHA256).Hash }
    }
    safety = [ordered]@{
        default_disabled_diagnostic = $true
        exactly_two_source_completions_per_changed_partial = $true
        completion_order = "erase_old_then_draw_disjoint_current"
        current_0x24_only = $true
        no_0x26 = $true
        no_c7 = $true
        no_full_frame_after_baseline = $true
        historical_no_go_orders_excluded = $true
        normal_firmware_restore_required = $true
        production_promotion = "prohibited"
    }
    output = [ordered]@{ root = RelPath $runRoot; raw_log = RelPath $rawLog; trace = RelPath $tracePath; report = RelPath $reportPath }
    operator_review = [ordered]@{ required = $true; invoked = $false; style = "aiw_operator_prompt_v1"; output_path = RelPath $operatorPath; selected = $null; note = $null }
    machine_trace_reused = $ReusePassedMachineTrace.IsPresent
    normal_firmware_restored = $false
    results = @()
}

if ($CheckOnly) {
    $report.completed_at = (Get-Date).ToString("o")
    Write-Report $report
    Write-Output "CHECK: all gate checks passed; this command did not touch hardware."
    exit 0
}

$diagnosticFlashed = $false
$normalRestored = $false
try {
    if ($ReusePassedMachineTrace) {
        if (-not (Test-Path -LiteralPath $rawLog -PathType Leaf)) {
            throw "Cannot reuse a machine trace because the captured raw log is missing."
        }
        $report.results += [ordered]@{ id = "reuse_existing_raw_trace"; status = "RUNNING" }
    } else {
        $diagnosticFlashed = $true
        & pwsh -NoProfile -File $flashRunner -ImagePath $diagnosticImage -ProgrammerRoot $ProgrammerRoot
        if ($LASTEXITCODE -ne 0) { throw "Diagnostic flash failed." }
        $report.results += [ordered]@{ id = "flash_diagnostic"; status = "PASS" }

        $captureArgs = @("-NoProfile", "-File", $serialRunner, "-Execute", "-WorkflowLockHeld", "-Seconds", "$CaptureSeconds", "-ResetAfterOpen", "-OutDir", $captureRoot)
        if (-not [string]::IsNullOrWhiteSpace($Port)) { $captureArgs += @("-Port", $Port) }
        & pwsh @captureArgs
        if ($LASTEXITCODE -ne 0) { throw "Serial capture failed." }
    }
    & python $traceVerifier --log $rawLog --static-contract $staticContract --out $tracePath
    if ($LASTEXITCODE -ne 0) { throw "Machine trace gate failed; operator review is forbidden." }
    if ($ReusePassedMachineTrace) {
        $report.results[-1].status = "PASS"
    }
    $report.results += [ordered]@{ id = "capture_and_trace_gate"; status = "PASS" }

    $diagnosticFlashed = $true
    & pwsh -NoProfile -File $flashRunner -ImagePath $observerImage -ProgrammerRoot $ProgrammerRoot
    if ($LASTEXITCODE -ne 0) { throw "Review observer flash failed." }
    $report.results += [ordered]@{ id = "flash_observer_loop"; status = "PASS" }
    $aiw = Resolve-Aiw
    $prompt = & pwsh -NoProfile -File $aiw operator-prompt `
        -Title "Companion 离散局部刷新底层诊断" `
        -ProgressText "1/1（单个 12 px 黑色诊断球，沿 center/up/right/down/left 五锚点轨道连续移动）" `
        -ScopeText "本次只验证昨晚已接受的两段式方法：先单独擦旧，再用离散差异窗口画新；每个变化帧严格两次原厂 0xFF 局刷完成。单个 12 px 黑色诊断球仅为可见性 probe；波形、LUT、温度策略和产品动态表情均未改变；结束后恢复正常固件。" `
        -Message "请观察黑球沿五锚点轨道移动，并与昨晚 COMP-REQ-236 已接受效果比较：是否有旧位置条纹或残影、整屏黑闪、屏幕变脏、累计缺失；移动方向的领先边短暂缺口是否比昨晚更大或持续更久；整体连续感是否可接受。" `
        -ExpectedText "只有无旧位置残影、无整屏黑闪、无脏化或累计内容丢失，领先边短暂缺口不比昨晚更大或更久，且连续感可接受时才选通过；任何一项不满足请选择失败并写明现象。" `
        -Input -ReviewStyle -Buttons "通过,失败" -OutputPath $operatorPath -TimeoutSeconds $OperatorTimeoutSeconds -Json
    if ($LASTEXITCODE -ne 0) { throw "Canonical operator prompt failed." }
    $operator = ($prompt -join [Environment]::NewLine) | ConvertFrom-Json
    $report.operator_review.invoked = $true
    $report.operator_review.selected = [string]$operator.selected
    $report.operator_review.note = [string]$operator.text
    if ($report.operator_review.selected -ne "通过" -or [string]::IsNullOrWhiteSpace($report.operator_review.note)) {
        throw "Operator did not accept the diagnostic."
    }
    $report.status = "PENDING_NORMAL_RESTORE"
} catch {
    $report.status = "NO_GO"
    $report.error = $_.Exception.Message
    throw
} finally {
    if ($diagnosticFlashed) {
        & pwsh -NoProfile -File $flashRunner -ImagePath $normalImage -ProgrammerRoot $ProgrammerRoot
        $normalRestored = $LASTEXITCODE -eq 0
    }
    $report.normal_firmware_restored = $normalRestored
    if ($report.status -eq "PENDING_NORMAL_RESTORE") {
        $report.status = if ($normalRestored) {
            "PASS_MACHINE_AND_OPERATOR_DISJOINT_NO_UNION_SETTLE_NORMAL_RESTORED"
        } else {
            "NO_GO_NORMAL_RESTORE_FAILED"
        }
    }
    $report.completed_at = (Get-Date).ToString("o")
    Write-Report $report
}
if (-not $normalRestored) {
    throw "Normal firmware restore failed after the diagnostic session."
}
