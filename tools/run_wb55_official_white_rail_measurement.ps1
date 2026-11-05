param(
    [switch]$CheckOnly,
    [switch]$Execute,
    [switch]$WorkflowLockHeld,
    [string]$Port,
    [ValidateRange(180, 300)]
    [int]$CaptureSeconds = 210,
    [ValidateRange(60, 900)]
    [int]$OperatorTimeoutSeconds = 600,
    [string]$ProgrammerRoot = 'C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins',
    [string]$RailProbeImagePath,
    [string]$RailProbeBuildArtifactPath,
    [string]$NormalImagePath,
    [string]$SourceAuditPath,
    [string]$DisplayFpcEvidencePath,
    [string]$RailArtifactPath,
    [string]$OutRoot
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'companion_wb55_lock.ps1')
$railProbeImageDefault = Join-Path $repoRoot 'cubeide\Companion_Nucleo_WB55RG_Bringup\build_official_full_rail_probe_white\Companion_Nucleo_WB55RG_OfficialFullRailProbeWhite.hex'
$railProbeBuildArtifactDefault = Join-Path $repoRoot 'docs\validation\companion-screen-wb55-official-white-rail-probe-build-20260720.json'
$normalImageDefault = Join-Path $repoRoot 'cubeide\Companion_Nucleo_WB55RG_Bringup\build\Companion_Nucleo_WB55RG_Bringup.hex'
$sourceAuditDefault = Join-Path $repoRoot 'docs\validation\companion-gdey0154d67-t03-vendor-1s-source-audit-20260720.json'
$displayFpcEvidenceDefault = Join-Path $repoRoot 'docs\validation\companion-screen-wb55-replacement-fpc-evidence-20260720.json'
$railArtifactDefault = Join-Path $repoRoot 'docs\validation\companion-screen-wb55-white-rail-measurement-current-source-20260720.json'
$outRootDefault = Join-Path $repoRoot '.cache\validation\wb55-official-white-rail-current-source-20260720'

function Resolve-RequiredPath {
    param([AllowNull()][string]$Override, [Parameter(Mandatory = $true)][string]$Default)

    $candidate = if ([string]::IsNullOrWhiteSpace($Override)) { $Default } else { $Override }
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
        throw "Required file is missing: $candidate"
    }
    return (Resolve-Path -LiteralPath $candidate).Path
}

function Resolve-OutputPath {
    param([AllowNull()][string]$Override, [Parameter(Mandatory = $true)][string]$Default)

    $candidate = if ([string]::IsNullOrWhiteSpace($Override)) { $Default } else { $Override }
    return [System.IO.Path]::GetFullPath($candidate)
}

function RelPath {
    param([Parameter(Mandatory = $true)][string]$Path)

    return [System.IO.Path]::GetRelativePath($repoRoot, [System.IO.Path]::GetFullPath($Path)).Replace('\', '/')
}

function Get-JsonFile {
    param([Parameter(Mandatory = $true)][string]$Path)

    return Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
}

function Get-SourceAuditBinding {
    param([Parameter(Mandatory = $true)][string]$Path)

    $audit = Get-JsonFile -Path $Path
    $errors = @()
    if ([string]$audit.schema_id -ne 'companion.gdey0154d67_t03.vendor_1s_source_audit.v1') { $errors += 'schema_id' }
    if ([string]$audit.machine_status -ne 'PASS_AUDIT_COMPLETE') { $errors += 'machine_status' }
    if ([string]$audit.promotion_status -ne 'NO_GO_PANEL_IDENTITY_UNPROVEN') { $errors += 'promotion_status' }
    if ($audit.command_evidence.production_lut_reference_absent -ne $true) { $errors += 'production_lut_reference_absent' }
    $targetHash = [string]$audit.source_manifest.critical_sources.current_ssd1681_target.sha256
    $vendorHash = [string]$audit.source_manifest.critical_sources.epaper_c.sha256
    if ([string]::IsNullOrWhiteSpace($targetHash)) { $errors += 'current_ssd1681_target.sha256' }
    if ([string]::IsNullOrWhiteSpace($vendorHash)) { $errors += 'epaper_c.sha256' }
    if ($errors.Count -gt 0) {
        throw "Vendor source audit is not safe to bind: $($errors -join ', ')."
    }
    return [ordered]@{
        current_ssd1681_target_sha256 = $targetHash.ToUpperInvariant()
        vendor_epaper_c_sha256 = $vendorHash.ToUpperInvariant()
    }
}

function Assert-ReplacementFpcEvidence {
    param([Parameter(Mandatory = $true)][string]$Path)

    $evidence = Get-JsonFile -Path $Path
    if ([string]$evidence.schema_id -ne 'companion.wb55.display_fpc_replacement_evidence.v1' -or
        [string]$evidence.status -ne 'PASS_OWNER_REPORTED_REPLACEMENT_FPC_CURRENT_PANEL_VISIBLE' -or
        [string]$evidence.authorization.allowed_stage -ne 'White') {
        throw 'Replacement display-FPC evidence does not authorize the current White rail measurement.'
    }
}

function Assert-RailProbeBuild {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$ImagePath,
        [Parameter(Mandatory = $true)][System.Collections.IDictionary]$SourceBinding
    )

    $build = Get-JsonFile -Path $Path
    if ([string]$build.schema_id -ne 'companion.wb55.official_white_rail_probe_build.v1' -or
        [string]$build.status -ne 'PASS_BUILD_ONLY_OFFICIAL_WHITE_RAIL_PROBE_NOT_FLASHED') {
        throw 'Official White rail-probe build contract does not pass.'
    }
    $imageHash = (Get-FileHash -LiteralPath $ImagePath -Algorithm SHA256).Hash.ToUpperInvariant()
    if ($imageHash -ne ([string]$build.image.sha256).ToUpperInvariant()) {
        throw 'Rail-probe image SHA-256 differs from its build artifact.'
    }
    if (([string]$build.sources.panel_target.sha256).ToUpperInvariant() -ne $SourceBinding.current_ssd1681_target_sha256) {
        throw 'Rail-probe build is bound to a stale SSD1681 target source hash.'
    }
    foreach ($field in @('official_full_current_plane', 'data_planes', 'bytes_per_plane', 'refresh_control', 'repeats', 'interval_ms')) {
        if ($null -eq $build.build_contract.$field) { throw "Rail-probe build contract is missing $field." }
    }
    if ([string]$build.build_contract.official_full_current_plane -ne '0x24_only' -or
        [int]$build.build_contract.data_planes -ne 1 -or
        [int]$build.build_contract.bytes_per_plane -ne 5000 -or
        [string]$build.build_contract.refresh_control -ne '0xF7' -or
        [int]$build.build_contract.repeats -ne 30 -or
        [int]$build.build_contract.interval_ms -ne 5000) {
        throw 'Rail-probe build contract drifted from the bounded official White profile.'
    }
}

function Resolve-AiwPath {
    $roots = @($env:AI_WORKFLOW_REPO, 'C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow') | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    foreach ($root in $roots | Select-Object -Unique) {
        $candidate = Join-Path $root 'scripts\aiw.ps1'
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return (Resolve-Path -LiteralPath $candidate).Path }
    }
    throw 'Canonical aiw operator-prompt helper was not found.'
}

function Read-RailMeasurement {
    param([Parameter(Mandatory = $true)][string]$Text)

    $positive = [regex]::Match($Text, '(?i)PREVGH1\s*=\s*\+?(?<value>\d+(?:\.\d+)?)\s*V')
    $negative = [regex]::Match($Text, '(?i)PREVGL1\s*=\s*(?<value>-\d+(?:\.\d+)?)\s*V')
    if (-not $positive.Success -or -not $negative.Success) {
        throw 'Rail note must contain PREVGH1=+<voltage>V and PREVGL1=-<voltage>V.'
    }
    return [ordered]@{
        prevgh1_max_v = [double]::Parse($positive.Groups['value'].Value, [Globalization.CultureInfo]::InvariantCulture)
        prevgl1_min_v = [double]::Parse($negative.Groups['value'].Value, [Globalization.CultureInfo]::InvariantCulture)
    }
}

$selectedModes = @(@($CheckOnly.IsPresent, $Execute.IsPresent) | Where-Object { $_ })
if ($selectedModes.Count -ne 1) { throw 'Use exactly one of -CheckOnly or -Execute.' }

$railProbeImage = Resolve-RequiredPath -Override $RailProbeImagePath -Default $railProbeImageDefault
$railProbeBuildArtifact = Resolve-RequiredPath -Override $RailProbeBuildArtifactPath -Default $railProbeBuildArtifactDefault
$normalImage = Resolve-RequiredPath -Override $NormalImagePath -Default $normalImageDefault
$sourceAudit = Resolve-RequiredPath -Override $SourceAuditPath -Default $sourceAuditDefault
$displayFpcEvidence = Resolve-RequiredPath -Override $DisplayFpcEvidencePath -Default $displayFpcEvidenceDefault
$railArtifact = Resolve-OutputPath -Override $RailArtifactPath -Default $railArtifactDefault
$runRoot = Resolve-OutputPath -Override $OutRoot -Default $outRootDefault
$captureDir = Join-Path $runRoot 'capture'
$captureRawLog = Join-Path $captureDir 'nucleo-serial-raw.log'
$captureSummary = Join-Path $captureDir 'nucleo-serial-summary.json'
$promptResultPath = Join-Path $runRoot 'operator-prompt-observation.json'
$measurementNotePath = Join-Path $runRoot 'operator-measurement.txt'
$runReportPath = Join-Path $runRoot 'rail-run.json'
$flashRunner = Join-Path $PSScriptRoot 'flash_nucleo_bringup.ps1'
$serialRunner = Join-Path $PSScriptRoot 'capture_nucleo_serial.ps1'
$railVerifier = Join-Path $PSScriptRoot 'verify_wb55_official_full_rail_measurement.py'

$sourceBinding = Get-SourceAuditBinding -Path $sourceAudit
Assert-ReplacementFpcEvidence -Path $displayFpcEvidence
Assert-RailProbeBuild -Path $railProbeBuildArtifact -ImagePath $railProbeImage -SourceBinding $sourceBinding

$report = [ordered]@{
    schema_id = 'companion.wb55.official_white_rail_runner.v1'
    status = if ($CheckOnly) { 'DRY-RUN' } else { 'RUNNING' }
    claim_scope = 'bounded_official_white_rail_measurement_not_lut_or_dynamic_expression_acceptance'
    target = 'NUCLEO-WB55RG + ESP32-FTS02 + replacement display FPC + GDEY0154D67-T03'
    source_audit = [ordered]@{
        path = RelPath $sourceAudit
        current_ssd1681_target_sha256 = $sourceBinding.current_ssd1681_target_sha256
        vendor_epaper_c_sha256 = $sourceBinding.vendor_epaper_c_sha256
    }
    inputs = [ordered]@{
        rail_probe_image = RelPath $railProbeImage
        rail_probe_build_artifact = RelPath $railProbeBuildArtifact
        normal_image = RelPath $normalImage
        replacement_display_fpc_evidence = RelPath $displayFpcEvidence
        capture_seconds = $CaptureSeconds
        rail_artifact = RelPath $railArtifact
    }
    output = [ordered]@{ root = RelPath $runRoot; report = RelPath $runReportPath }
    safety = [ordered]@{
        execute_requires_companion_wb55_lock = $true
        execute_uses_firmware_owned_exclusive_mutex = $true
        legacy_workflow_lock_boolean_is_not_authority = $true
        source_audit_and_fpc_checked_before_flash = $true
        exact_30_cycle_official_white_image_required = $true
        operator_measurement_occurs_during_active_refresh = $true
        normal_firmware_restored = $false
    }
    operator_measurement = [ordered]@{
        required = $true
        style = 'aiw_operator_prompt_v1'
        expected_format = 'PREVGH1=+20V; PREVGL1=-20V; 白屏均匀'
        selected = $null
        note = $null
    }
    results = @()
    execution_lock = $null
}

function Write-RunReport {
    New-Item -ItemType Directory -Force -Path $runRoot | Out-Null
    $report.completed_at = (Get-Date).ToString('o')
    $report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $runReportPath -Encoding UTF8
    Write-Output "White rail measurement report: $(RelPath $runReportPath)"
}

if ($CheckOnly) {
    $report.steps = @(
        "flash exact rail probe: $(RelPath $railProbeImage)",
        "capture reset-bounded serial for $CaptureSeconds seconds",
        'open canonical Chinese rail prompt while the probe cycles',
        'parse 30 official White cycles plus rail values',
        "restore normal firmware: $(RelPath $normalImage)"
    )
    Write-RunReport
    Write-Output "CHECK: White rail runner is preflight only; no hardware was touched."
    exit 0
}

$lockContext = Enter-CompanionWb55Lock -Purpose 'official White rail measurement'
$report.execution_lock = Get-CompanionWb55LockEvidenceSummary -Context $lockContext
$captureProcess = $null
$normalRestored = $false
try {
    New-Item -ItemType Directory -Force -Path $runRoot, $captureDir | Out-Null
    $flashStarted = Get-Date
    & pwsh -NoProfile -File $flashRunner -ImagePath $railProbeImage -ProgrammerRoot $ProgrammerRoot
    $flashExit = $LASTEXITCODE
    $report.results += [ordered]@{ id = 'flash_official_white_rail_probe'; status = if ($flashExit -eq 0) { 'PASS' } else { 'FAIL' }; exit_code = $flashExit; started_at = $flashStarted.ToString('o'); ended_at = (Get-Date).ToString('o') }
    if ($flashExit -ne 0) { throw "rail-probe flash failed with exit code $flashExit" }

    $captureArgs = @('-NoProfile', '-File', $serialRunner, '-Execute', '-WorkflowLockHeld', '-Seconds', "$CaptureSeconds", '-ResetAfterOpen', '-OutDir', $captureDir)
    if (-not [string]::IsNullOrWhiteSpace($Port)) { $captureArgs += @('-Port', $Port) }
    $captureStdout = Join-Path $captureDir 'capture-runner.stdout.log'
    $captureStderr = Join-Path $captureDir 'capture-runner.stderr.log'
    $captureStarted = Get-Date
    $captureProcess = Start-Process -FilePath pwsh -ArgumentList $captureArgs -RedirectStandardOutput $captureStdout -RedirectStandardError $captureStderr -WindowStyle Hidden -PassThru
    Start-Sleep -Seconds 8
    if ($captureProcess.HasExited) { throw "serial capture terminated before the physical rail window. stdout=$captureStdout stderr=$captureStderr" }

    $aiw = Resolve-AiwPath
    $promptOutput = & pwsh -NoProfile -File $aiw operator-prompt `
        -Title 'Companion 白屏刷新电压轨量测' `
        -ProgressText '当前正在执行 30 次官方白屏刷新' `
        -ScopeText '这是 active refresh 内的物理量测，不是快刷或波形调参；结束后会自动恢复正常固件。' `
        -Message '现在白屏会每约 5 秒刷新一次。黑表笔接 GND1，红表笔依次测 PREVGH1 和 PREVGL1；在输入框按固定格式填写：PREVGH1=+20V; PREVGL1=-20V; 白屏均匀。若任一电压未出现、白屏不均匀或不确定，请选失败并说明。' `
        -ExpectedText '通过要求：本次激活窗口内 PREVGH1 为正且高于 3.3V，PREVGL1 为负，白屏均匀；输入必须带两个实测值。' `
        -DefaultText 'PREVGH1=+20V; PREVGL1=-20V; 白屏均匀。' `
        -ReviewStyle -Input -Buttons '通过,失败,跳过,中止' `
        -OutputPath $promptResultPath `
        -TimeoutSeconds $OperatorTimeoutSeconds -Json
    if ($LASTEXITCODE -ne 0) { throw "Canonical operator prompt failed with exit code $LASTEXITCODE." }
    $promptResult = ($promptOutput -join [Environment]::NewLine) | ConvertFrom-Json
    $report.operator_measurement.selected = [string]$promptResult.selected
    $report.operator_measurement.note = [string]$promptResult.text
    $report.operator_measurement | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $measurementNotePath -Encoding UTF8
    if ($report.operator_measurement.selected -ne '通过') { throw "operator did not pass rail measurement: selected=$($report.operator_measurement.selected)" }
    if ([string]::IsNullOrWhiteSpace($report.operator_measurement.note)) { throw 'operator passed rail measurement without a note.' }
    $measurement = Read-RailMeasurement -Text $report.operator_measurement.note

    $captureProcess.WaitForExit(($CaptureSeconds + 60) * 1000)
    if (-not $captureProcess.HasExited) { throw "serial capture did not finish within the bounded window; stdout=$captureStdout stderr=$captureStderr" }
    $report.results += [ordered]@{ id = 'capture_white_rail'; status = if ($captureProcess.ExitCode -eq 0) { 'PASS' } else { 'FAIL' }; exit_code = $captureProcess.ExitCode; started_at = $captureStarted.ToString('o'); ended_at = (Get-Date).ToString('o') }
    if ($captureProcess.ExitCode -ne 0) { throw "serial capture failed with exit code $($captureProcess.ExitCode). stdout=$captureStdout stderr=$captureStderr" }
    if (-not (Test-Path -LiteralPath $captureRawLog) -or -not (Test-Path -LiteralPath $captureSummary)) { throw 'serial capture did not produce the required raw log and summary.' }

    $verifyStarted = Get-Date
    & python $railVerifier --log $captureRawLog --image $railProbeImage --prevgl-min-v $measurement.prevgl1_min_v --prevgh-max-v $measurement.prevgh1_max_v --operator-selected '通过' --screen-observation uniform_white --operator-note $measurementNotePath --source-audit $sourceAudit --min-cycles 30 --write $railArtifact
    $verifyExit = $LASTEXITCODE
    $report.results += [ordered]@{ id = 'verify_official_white_rail'; status = if ($verifyExit -eq 0) { 'PASS' } else { 'FAIL' }; exit_code = $verifyExit; started_at = $verifyStarted.ToString('o'); ended_at = (Get-Date).ToString('o') }
    if ($verifyExit -ne 0) { throw "official White rail verifier failed with exit code $verifyExit" }
    $report.status = 'PASS_MACHINE_AND_RAILS_ESTABLISHED_WHITE_PENDING_NORMAL_RESTORE'
} catch {
    $report.status = 'FAIL'
    $report.error = $_.Exception.Message
    if ($captureProcess -and -not $captureProcess.HasExited) { Stop-Process -Id $captureProcess.Id -Force -ErrorAction SilentlyContinue }
    throw
} finally {
    try {
        $restoreStarted = Get-Date
        & pwsh -NoProfile -File $flashRunner -ImagePath $normalImage -ProgrammerRoot $ProgrammerRoot
        $restoreExit = $LASTEXITCODE
        $normalRestored = $restoreExit -eq 0
        $report.results += [ordered]@{ id = 'flash_normal_restore'; status = if ($normalRestored) { 'PASS' } else { 'FAIL' }; exit_code = $restoreExit; started_at = $restoreStarted.ToString('o'); ended_at = (Get-Date).ToString('o') }
        $report.safety.normal_firmware_restored = [bool]$normalRestored
        if ($report.status -like 'PASS_*' -and -not $normalRestored) { $report.status = 'FAIL'; $report.error = 'normal firmware restore failed after rail measurement.' }
        Write-RunReport
    } finally {
        Exit-CompanionWb55Lock
    }
}

if ($report.status -notlike 'PASS_*') { throw 'Official White rail measurement did not close.' }
