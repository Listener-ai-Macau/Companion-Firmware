param(
    [switch]$CheckOnly,
    [switch]$Execute,
    [switch]$WorkflowLockHeld,
    [switch]$ResetReadControllerState,
    [switch]$RamPingPongFingerprint,
    [switch]$RamPingPongPointProbe,
    [switch]$FastPointProbe,
    [switch]$FastPointProbeInverseSeed,
    [switch]$CustomMode2TransitionSafety,
    [switch]$CustomMode2TransitionSafetyDualPlaneClean,
    [switch]$PostCleanWhiteRecoveryOnly,
    [switch]$DualPlaneWhiteRecoveryOnly,
    [ValidateRange(10, 60)]
    [int]$CandidateCaptureSeconds = 20,
    [ValidateRange(10, 30)]
    [int]$NormalCaptureSeconds = 30,
    [ValidateRange(60, 1800)]
    [int]$HumanPromptTimeoutSeconds = 900,
    [string]$Port,
    [string]$OutRoot,
    [string]$ProgrammerRoot = "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if ($CheckOnly -eq $Execute) {
    throw "Choose exactly one of -CheckOnly or -Execute."
}
if (@($ResetReadControllerState, $RamPingPongFingerprint, $RamPingPongPointProbe, $FastPointProbe, $FastPointProbeInverseSeed, $CustomMode2TransitionSafety, $CustomMode2TransitionSafetyDualPlaneClean, $PostCleanWhiteRecoveryOnly, $DualPlaneWhiteRecoveryOnly).Where({ $_ }).Count -gt 1) {
    throw "Choose exactly one controller diagnostic."
}
$customMode2 = $CustomMode2TransitionSafety -or $CustomMode2TransitionSafetyDualPlaneClean
$dualPlaneCustomMode2 = $CustomMode2TransitionSafetyDualPlaneClean.IsPresent
$dualPlaneWhiteRecoveryOnly = $DualPlaneWhiteRecoveryOnly.IsPresent
$whiteRecoveryOnly = $PostCleanWhiteRecoveryOnly.IsPresent -or $dualPlaneWhiteRecoveryOnly
$dualPlaneCleanProfile = $dualPlaneCustomMode2 -or $dualPlaneWhiteRecoveryOnly

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
. (Join-Path $PSScriptRoot "companion_wb55_lock.ps1")
$staticVerifier = Join-Path $PSScriptRoot $(if ($dualPlaneCleanProfile) { "verify_wb55_ssd1681_custom_mode2_dual_plane_clean_r5.py" } elseif ($CustomMode2TransitionSafety) { "verify_wb55_ssd1681_custom_mode2_transition_safety_diagnostic.py" } elseif ($FastPointProbeInverseSeed) { "verify_wb55_ssd1681_fast_point_probe_inverse_seed_diagnostic.py" } elseif ($FastPointProbe) { "verify_wb55_ssd1681_fast_point_probe_diagnostic.py" } elseif ($RamPingPongPointProbe) { "verify_wb55_ssd1681_ram_ping_pong_point_probe_diagnostic.py" } elseif ($RamPingPongFingerprint) { "verify_wb55_ssd1681_ram_ping_pong_fingerprint_diagnostic.py" } elseif ($ResetReadControllerState) { "verify_wb55_ssd1681_reset_read_controller_state_diagnostic.py" } else { "verify_wb55_ssd1681_read_only_controller_state_raw_restore_diagnostic.py" })
if ($PostCleanWhiteRecoveryOnly) { $staticVerifier = Join-Path $PSScriptRoot "verify_wb55_ssd1681_postclean_white_recovery.py" }
$baselineVerifier = Join-Path $PSScriptRoot "verify_wb55_ur_application_backup.py"
$controllerVerifier = Join-Path $PSScriptRoot $(if ($customMode2) { "verify_wb55_ssd1681_custom_mode2_transition_safety_log.py" } elseif ($FastPointProbeInverseSeed) { "verify_wb55_ssd1681_fast_point_probe_inverse_seed_log.py" } elseif ($FastPointProbe) { "verify_wb55_ssd1681_fast_point_probe_log.py" } elseif ($RamPingPongPointProbe) { "verify_wb55_ssd1681_ram_ping_pong_point_probe_log.py" } elseif ($RamPingPongFingerprint) { "verify_wb55_ssd1681_ram_ping_pong_fingerprint_log.py" } elseif ($ResetReadControllerState) { "verify_wb55_ssd1681_reset_read_controller_state_log.py" } else { "verify_wb55_ssd1681_read_only_controller_state_log.py" })
$restoreVerifier = Join-Path $PSScriptRoot "verify_wb55_raw_application_restore.py"
$normalVerifier = Join-Path $PSScriptRoot "verify_wb55_normal_resume_after_ur_backup_log.py"
$precleanVerifier = Join-Path $PSScriptRoot "verify_wb55_official_full_diagnostic_log.py"
$dualPlaneCleanVerifier = Join-Path $PSScriptRoot "verify_wb55_ssd1681_dual_plane_white_clean_log.py"
$captureRunner = Join-Path $PSScriptRoot "capture_nucleo_serial.ps1"
$candidateImage = Join-Path $repoRoot $(if ($customMode2) { "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_custom_mode2_transition_safety\Companion_Nucleo_WB55RG_Ssd1681CustomMode2TransitionSafety.hex" } elseif ($FastPointProbeInverseSeed) { "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_fast_point_probe_inverse_seed\Companion_Nucleo_WB55RG_Ssd1681FastPointProbeInverseSeed.hex" } elseif ($FastPointProbe) { "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_fast_point_probe\Companion_Nucleo_WB55RG_Ssd1681FastPointProbe.hex" } elseif ($RamPingPongPointProbe) { "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_ram_ping_pong_point_probe\Companion_Nucleo_WB55RG_Ssd1681RamPingPongPointProbe.hex" } elseif ($RamPingPongFingerprint) { "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_ram_ping_pong_fingerprint\Companion_Nucleo_WB55RG_Ssd1681RamPingPongFingerprint.hex" } elseif ($ResetReadControllerState) { "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_reset_read_controller_state\Companion_Nucleo_WB55RG_Ssd1681ResetReadControllerState.hex" } else { "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_read_only_controller_state\Companion_Nucleo_WB55RG_Ssd1681ReadOnlyControllerState.hex" })
$precleanImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_official_full_diagnostic_white\Companion_Nucleo_WB55RG_OfficialFullDiagnostic_white.hex"
$dualPlaneCleanImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_dual_plane_white_clean\Companion_Nucleo_WB55RG_Ssd1681DualPlaneWhiteClean.hex"
if ($dualPlaneCleanProfile) { $precleanImage = $dualPlaneCleanImage; $precleanVerifier = $dualPlaneCleanVerifier }
if ($whiteRecoveryOnly) { $candidateImage = $precleanImage }
$precleanSourceAudit = Join-Path $repoRoot "docs\validation\companion-gdey0154d67-t03-vendor-1s-source-audit-r2-20260721.json"
$baselineRoot = Join-Path $repoRoot ".cache\validation\wb55-ur-dual-application-backup-execute-20260721-r1\private"
$backupA = Join-Path $baselineRoot "backup-a.bin"
$backupB = Join-Path $baselineRoot "backup-b.bin"
$candidateSha256 = if ($customMode2) { "E695A1A6D3D121AA585E69A1A0D8DA21FEBC5566198BD314FE27F2D40C30B564" } elseif ($FastPointProbeInverseSeed) { "F7E20B26A479F690064F95FED25B18F632B3CDBC2AEDDD842645377CA0EBB2E9" } elseif ($FastPointProbe) { "210B9851889457F951E20FC96DC509CA4DCB8B779E40031F7DC47C136C4CB222" } elseif ($RamPingPongPointProbe) { "00880EBC4678ED83927FE69A797876C0513BF7AE4D18119FCE5E7FC833A64F0B" } elseif ($RamPingPongFingerprint) { "2ED8AEC1B665C4FF516BE603D9C2CCEEAEB6411CFF38B6113283FBEEA7E17B90" } elseif ($ResetReadControllerState) { "DB6F1CDBC091A8F4B12AFDB82BBCA62E9C850D57B343E722C4EBE5E05BB7AD7E" } else { "52D79CB3BC55D9738EFA580B95D3930216C23FD8825356F7860B7C1718C0C6AD" }
$precleanSha256 = "F7CB7EE8C497CF1A01ACFF4BC921B43E274B0A934CA8B658AC24C34480F32925"
$dualPlaneCleanSha256 = "3AC4E52E37E15DC3CC058A4B0B0E6A3227D23E6C6DEFAEDCB786C08497888AAD"
if ($dualPlaneCleanProfile) { $precleanSha256 = $dualPlaneCleanSha256 }
if ($whiteRecoveryOnly) { $candidateSha256 = $precleanSha256 }
$baselineSha256 = "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C"
$programmerSha256 = "BD520005962377155515A2C9E8FEAB73F304A696AAE1698F3B7760672160FD5E"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runRoot = if ($OutRoot) { [System.IO.Path]::GetFullPath($OutRoot) } else {
    Join-Path $repoRoot $(if ($dualPlaneWhiteRecoveryOnly) { ".cache\validation\wb55-dual-plane-white-recovery-raw-restore-$stamp" } elseif ($dualPlaneCustomMode2) { ".cache\validation\wb55-custom-mode2-dual-plane-clean-r5-raw-restore-$stamp" } elseif ($CustomMode2TransitionSafety) { ".cache\validation\wb55-custom-mode2-transition-safety-raw-restore-$stamp" } elseif ($FastPointProbeInverseSeed) { ".cache\validation\wb55-fast-point-probe-inverse-seed-raw-restore-$stamp" } elseif ($FastPointProbe) { ".cache\validation\wb55-fast-point-probe-raw-restore-$stamp" } elseif ($RamPingPongPointProbe) { ".cache\validation\wb55-ram-ping-pong-point-probe-raw-restore-$stamp" } elseif ($RamPingPongFingerprint) { ".cache\validation\wb55-ram-ping-pong-fingerprint-raw-restore-$stamp" } elseif ($ResetReadControllerState) { ".cache\validation\wb55-reset-read-controller-raw-restore-$stamp" } else { ".cache\validation\wb55-readonly-controller-raw-restore-$stamp" })
}
$privateRoot = Join-Path $runRoot "private"
$precleanCaptureRoot = Join-Path $runRoot "preclean-capture"
$postcleanCaptureRoot = Join-Path $runRoot "postclean-capture"
$candidateCaptureRoot = Join-Path $runRoot "candidate-capture"
$normalCaptureRoot = Join-Path $runRoot "normal-capture"
$precleanReady = Join-Path $runRoot "preclean-serial-ready.json"
$postcleanReady = Join-Path $runRoot "postclean-serial-ready.json"
$candidateReady = Join-Path $runRoot "candidate-serial-ready.json"
$normalReady = Join-Path $runRoot "normal-serial-ready.json"
$precleanRawLog = Join-Path $precleanCaptureRoot "nucleo-serial-raw.log"
$postcleanRawLog = Join-Path $postcleanCaptureRoot "nucleo-serial-raw.log"
$candidateRawLog = Join-Path $candidateCaptureRoot "nucleo-serial-raw.log"
$normalRawLog = Join-Path $normalCaptureRoot "nucleo-serial-raw.log"
$precleanArtifact = Join-Path $runRoot "preclean-white.json"
$postcleanArtifact = Join-Path $runRoot "postclean-white.json"
$controllerArtifact = Join-Path $runRoot "controller-state.json"
$baselineArtifact = Join-Path $runRoot "baseline-gate.json"
$restoreVerify = Join-Path $privateRoot "restore-verify.bin"
$restoreArtifact = Join-Path $runRoot "restore-gate.json"
$normalArtifact = Join-Path $runRoot "normal-resume.json"
$lockArtifact = Join-Path $runRoot "swd-com-lock.json"
$operatorArtifact = Join-Path $runRoot "restore-or-app-failure-operator.json"
$startPromptNote = Join-Path $runRoot "candidate-start-note.txt"
$startPromptArtifact = Join-Path $runRoot "candidate-start-decision.json"
$reportPath = Join-Path $runRoot "stage-run.json"
New-Item -ItemType Directory -Force -Path $runRoot | Out-Null

function Get-Hash([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

function Write-Report([System.Collections.IDictionary]$Report) {
    $Report | ConvertTo-Json -Depth 18 | Set-Content -LiteralPath $reportPath -Encoding UTF8
}

function Find-Programmer {
    $matches = @(Get-ChildItem -LiteralPath $ProgrammerRoot -Recurse -Filter STM32_Programmer_CLI.exe | Sort-Object FullName -Descending)
    if ($matches.Count -eq 0) { throw "STM32_Programmer_CLI.exe not found under $ProgrammerRoot" }
    $exact = @($matches | Where-Object { (Get-Hash $_.FullName) -eq $programmerSha256 })
    if ($exact.Count -ne 1) { throw "Exactly one hash-bound STM32CubeProgrammer v2.22 executable is required." }
    return $exact[0].FullName
}

function Invoke-ProgrammerOnce {
    param(
        [Parameter(Mandatory = $true)][string]$Programmer,
        [Parameter(Mandatory = $true)][string]$Operation,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [ValidateRange(30, 300)][int]$TimeoutSeconds = 180
    )
    $stdout = Join-Path $runRoot "$Operation.stdout.log"
    $stderr = Join-Path $runRoot "$Operation.stderr.log"
    $script:report.programmer_calls += [ordered]@{
        operation = $Operation
        arguments = @($Arguments)
        stdout = $stdout
        stderr = $stderr
    }
    $process = Start-Process -FilePath $Programmer -ArgumentList $Arguments `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr `
        -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        throw "$Operation timed out; no retry is allowed."
    }
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) {
        throw "$Operation failed with exit code $($process.ExitCode); no retry is allowed."
    }
}

function Start-BoundedSerialCapture {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$OutDir,
        [Parameter(Mandatory = $true)][string]$ReadyPath,
        [Parameter(Mandatory = $true)][int]$Seconds
    )
    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
    $arguments = @("-NoProfile", "-File", $captureRunner, "-Execute", "-WorkflowLockHeld",
                   "-Seconds", "$Seconds", "-OutDir", $OutDir,
                   "-ReadySignalPath", $ReadyPath, "-ProgrammerRoot", $ProgrammerRoot)
    if (-not [string]::IsNullOrWhiteSpace($Port)) { $arguments += @("-Port", $Port) }
    $process = Start-Process -FilePath "pwsh" -ArgumentList $arguments `
        -RedirectStandardOutput (Join-Path $runRoot "$Name.stdout.log") `
        -RedirectStandardError (Join-Path $runRoot "$Name.stderr.log") `
        -WindowStyle Hidden -PassThru
    $deadline = [DateTime]::UtcNow.AddSeconds(20)
    while (-not (Test-Path -LiteralPath $ReadyPath -PathType Leaf)) {
        if ($process.HasExited) { throw "$Name serial capture exited before ready." }
        if ([DateTime]::UtcNow -ge $deadline) { throw "$Name serial capture did not become ready." }
        Start-Sleep -Milliseconds 100
    }
    return $process
}

function Stop-Capture([AllowNull()][System.Diagnostics.Process]$Process) {
    if ($Process -and -not $Process.HasExited) {
        Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
        $Process.WaitForExit()
    }
}

function Resolve-Aiw {
    $roots = @()
    if ($env:AI_WORKFLOW_REPO) { $roots += $env:AI_WORKFLOW_REPO }
    $roots += "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow"
    foreach ($root in $roots) {
        $path = Join-Path $root "scripts\aiw.ps1"
        if (Test-Path -LiteralPath $path -PathType Leaf) { return $path }
    }
    throw "Canonical aiw operator-prompt helper was not found."
}

function Invoke-RestoreFailurePrompt([string]$Reason) {
    $aiw = Resolve-Aiw
    $null = & pwsh -NoProfile -File $aiw operator-prompt `
        -Title "Companion 固件恢复或启动未证实" `
        -ProgressText "恢复保护已停止" `
        -ScopeText "只报告本次只读控制器诊断后的唯一 raw-baseline 恢复或正常启动失败；不会执行第二次写入、复位、连接或屏幕操作。" `
        -Message "请保持开发板供电和连接，不要手动复位、拔线或再次烧录。失败原因：$Reason" `
        -ExpectedText "请选择已知悉，并在备注中记录当前供电、串口和屏幕状态；后续恢复必须另行受控。" `
        -Input -ReviewStyle -Buttons "已知悉" -OutputPath $operatorArtifact `
        -TimeoutSeconds $HumanPromptTimeoutSeconds -Json
}

function Invoke-CandidateStartPrompt {
    $aiw = Resolve-Aiw
    $title = if ($dualPlaneCustomMode2) { "Companion R5 双平面基线局刷实验开始确认" } else { "Companion R4 局刷实验开始确认" }
    $scope = if ($dualPlaneCustomMode2) {
        "production-off 底层诊断；供应商原样双平面全白清理和两 bank 双重复读回已先机器完成，本窗口只授权随后同一 R4 TP16 候选的 9 次 32x32 局部转移。"
    } else {
        "production-off 底层诊断；先做已验收的确定性纯白清洁，再做 9 次 32x32 局部转移，随后恢复并读回原应用。"
    }
    $message = if ($dualPlaneCustomMode2) {
        "继续后才会写入候选镜像。候选 HEX、TP16 LUT、0xCF、九步 payload、窗口、时序和电压尾与 R4 字节一致；唯一变量是已完成的 0x24+0x26 双平面全白基线。候选结束后会无弹窗再次做同样双平面清理，再恢复原应用。不要断电、拔线或手动复位。"
    } else {
        "点击开始后会接触硬件。纯白前置使用已验收的官方单平面 0x24/F7/20/BUSY 路径，不使用自定义 LUT；前置清洁机器失败会立即禁止 R4。R4 对两组完整且对称的活动 TP 字段做同一 4/5 缩放，使总 frame-counts 20 变 16；保留静止像素抑制、波形电平、供应商电压尾和显式旧/新 RAM。不要断电、拔线或手动复位。"
    }
    $raw = & pwsh -NoProfile -File $aiw operator-prompt `
        -Title $title `
        -ProgressText "执行前 1/1" `
        -ScopeText $scope `
        -Message $message `
        -ExpectedText "只有确认开发板供电和连接稳定，并愿意观察随后单独弹出的白/黑洁净度、残影、整屏闪烁和缺口验收时，才选择开始实验。" `
        -Input -ReviewStyle -Buttons "开始实验,取消" -OutputPath $startPromptNote `
        -TimeoutSeconds $HumanPromptTimeoutSeconds -Json
    if ($LASTEXITCODE -ne 0) { throw "Canonical candidate start prompt failed." }
    $result = (($raw | Out-String).Trim() | ConvertFrom-Json)
    [ordered]@{
        style = "aiw_operator_prompt_v1"
        selected = $result.selected
        note = $result.text
        note_path = $startPromptNote
        shown_before_hardware_contact = $true
    } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $startPromptArtifact -Encoding UTF8
    return $result
}

$passStatus = if ($dualPlaneCustomMode2) { "PASS_MACHINE_CUSTOM_MODE2_DUAL_PLANE_CLEAN_R5_RESTORED" } elseif ($CustomMode2TransitionSafety) { "PASS_MACHINE_CUSTOM_MODE2_TRANSITION_SAFETY_RESTORED" } elseif ($FastPointProbeInverseSeed) { "PASS_MACHINE_SSD1681_FAST_POINT_PROBE_INVERSE_SEED_RESTORED" } elseif ($FastPointProbe) { "PASS_MACHINE_SSD1681_FAST_POINT_PROBE_RESTORED" } elseif ($RamPingPongPointProbe) { "PASS_MACHINE_RAM_PING_PONG_POINT_PROBE_RESTORED" } elseif ($RamPingPongFingerprint) { "PASS_MACHINE_RAM_PING_PONG_FINGERPRINT_RESTORED" } elseif ($ResetReadControllerState) { "PASS_MACHINE_RESET_READ_CONTROLLER_STATE_RESTORED" } else { "PASS_MACHINE_READ_ONLY_CONTROLLER_STATE_RESTORED" }
if ($PostCleanWhiteRecoveryOnly) { $passStatus = "PASS_POST_CANDIDATE_WHITE_CLEAN_EXACT_RAW_RESTORED" }
if ($dualPlaneWhiteRecoveryOnly) { $passStatus = "PASS_DUAL_PLANE_WHITE_CLEAN_EXACT_RAW_RESTORED" }
$report = [ordered]@{
    schema_id = if ($dualPlaneCustomMode2) { "companion.wb55.ssd1681_custom_mode2_dual_plane_clean_r5_raw_restore_stage_run.v1" } elseif ($CustomMode2TransitionSafety) { "companion.wb55.ssd1681_custom_mode2_transition_safety_raw_restore_stage_run.v1" } elseif ($FastPointProbeInverseSeed) { "companion.wb55.ssd1681_fast_point_probe_inverse_seed_raw_restore_stage_run.v1" } elseif ($FastPointProbe) { "companion.wb55.ssd1681_fast_point_probe_raw_restore_stage_run.v1" } elseif ($RamPingPongPointProbe) { "companion.wb55.ssd1681_ram_ping_pong_point_probe_raw_restore_stage_run.v1" } elseif ($RamPingPongFingerprint) { "companion.wb55.ssd1681_ram_ping_pong_fingerprint_raw_restore_stage_run.v1" } elseif ($ResetReadControllerState) { "companion.wb55.ssd1681_reset_read_controller_state_raw_restore_stage_run.v1" } else { "companion.wb55.ssd1681_read_only_controller_state_raw_restore_stage_run.v1" }
    status = "PREFLIGHT"
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    mode = if ($CheckOnly) { "check_only" } else { "execute" }
    claim_scope = if ($CustomMode2TransitionSafety) { "one locked production-off R3 custom Mode2 candidate: canonical pre-execute start gate, accepted official deterministic White pre-clean, then at most nine local 32x32 transitions covering WW/WB/BW/BB with exactly one R2 TP byte decremented for total TP19, explicit 0x26 old and 0x24 new planes, one CF/20/BUSY per transition, protected supplier voltage tail, zero candidate full refresh/retry, final local white, and exact raw restore/readback/normal resume" } elseif ($FastPointProbeInverseSeed) { "one locked 120-frame production-off fast point probe changing only the first previous-plane seed to a local inverse corridor, with one FF/20/BUSY and post-sync per frame, zero motion 0x26/full/LUT/retry, and exact raw restore" } elseif ($FastPointProbe) { "one locked 120-frame production-off fast point probe, 8 px steps over 32 px, one FF/20/BUSY and one post-activation 0x24 no-refresh sync per frame, zero motion 0x26, zero retry, and one exact captured-raw restore" } elseif ($RamPingPongPointProbe) { "one locked 24-frame production-off point probe, one FF/20/BUSY and one post-activation 0x24 no-refresh sync per frame, zero motion 0x26, zero retry, and one exact captured-raw restore" } elseif ($RamPingPongFingerprint) { "one locked production-off RAM fingerprint candidate, exactly two activations, twelve 5001-byte reads, zero retry, and one exact captured-raw restore" } elseif ($ResetReadControllerState) { "one locked candidate with exactly one panel hard reset, one bounded BUSY wait, three 0x2F/0x2D read-only groups, and one exact captured-raw restore" } else { "one locked 0x2F/0x2D read-only candidate and one exact captured-raw restore" }
    hardware_contact = 0
    error = $null
    controller_error = $null
    restore_error = $null
    counters = [ordered]@{
        serial_capture_processes = 0
        preclean_programmer_processes = 0
        preclean_write_calls = 0
        preclean_panel_writes = 0
        preclean_panel_refresh_commands = 0
        preclean_panel_busy_waits = 0
        postclean_programmer_processes = 0
        postclean_write_calls = 0
        postclean_panel_writes = 0
        postclean_panel_refresh_commands = 0
        postclean_panel_busy_waits = 0
        candidate_programmer_processes = 0
        candidate_write_calls = 0
        restore_programmer_processes = 0
        restore_write_calls = 0
        restore_verify_operations = 0
        restore_upload_calls = 0
        restore_reset_arguments = 0
        panel_writes = 0
        panel_refresh_commands = 0
        panel_hard_resets = 0
        panel_busy_waits = 0
        automatic_retries = 0
    }
    images = [ordered]@{
        preclean = [ordered]@{ path = $precleanImage; sha256 = Get-Hash $precleanImage; required_sha256 = $precleanSha256; profile = $(if ($dualPlaneCleanProfile) { "supplier_basemap_0x24_0x26_f7_white_readback" } else { "official_0x24_f7_white" }); custom_lut_used = $false }
        candidate = [ordered]@{ path = $candidateImage; sha256 = Get-Hash $candidateImage; required_sha256 = $candidateSha256 }
        baseline_a = [ordered]@{ bytes = if (Test-Path $backupA) { [int64](Get-Item $backupA).Length } else { $null }; sha256 = Get-Hash $backupA }
        baseline_b = [ordered]@{ bytes = if (Test-Path $backupB) { [int64](Get-Item $backupB).Length } else { $null }; sha256 = Get-Hash $backupB }
        restore_verify = [ordered]@{ bytes = $null; sha256 = $null; private = $true }
    }
    locks = [ordered]@{
        companion_wb55 = $null
        swd_com = [ordered]@{ mechanism = "Local\\Companion-WB55-SWD-COM-Exclusive-v1"; acquired = $false; evidence = $lockArtifact }
    }
    programmer = [ordered]@{ executable = $null; sha256 = $null }
    programmer_calls = @()
    baseline = $null
    pre_execute_prompt = [ordered]@{ required = $customMode2; invoked = $false; selected = $null; note = $null; artifact = $startPromptArtifact }
    preclean = [ordered]@{ required = $customMode2; promptless = $true; profile = $(if ($dualPlaneCleanProfile) { "supplier_basemap_0x24_0x26_f7_white_readback" } else { "official_0x24_f7_white" }); excluded_from_candidate_metrics = $true; result = $null }
    postclean = [ordered]@{ required = $customMode2 -or $whiteRecoveryOnly; promptless = $true; profile = $(if ($dualPlaneCleanProfile) { "supplier_basemap_0x24_0x26_f7_white_readback" } else { "official_0x24_f7_white" }); result = $null }
    controller_state = $null
    restore = $null
    normal_resume = $null
    restore_identity = $null
    operator_prompt = [ordered]@{ required = $false; invoked = $false; path = $operatorArtifact; error = $null }
    outputs = [ordered]@{
        baseline_gate = $baselineArtifact
        preclean_raw_log = $precleanRawLog
        preclean_result = $precleanArtifact
        postclean_raw_log = $postcleanRawLog
        postclean_result = $postcleanArtifact
        candidate_raw_log = $candidateRawLog
        controller_state = $controllerArtifact
        restore_gate = $restoreArtifact
        normal_raw_log = $normalRawLog
        normal_resume = $normalArtifact
        report = $reportPath
    }
}

if ($dualPlaneCustomMode2) {
    $report.claim_scope = "one production-off R5 baseline-correction A/B: promptless supplier-exact dual-plane all-White BaseMap pre-clean with two selectors read twice and proven all-white, then the byte-identical R4 TP16 custom Mode2 candidate after one canonical start prompt, then unconditional promptless identical dual-plane post-clean and exact raw restore/readback/normal resume"
} elseif ($CustomMode2TransitionSafety) {
    $report.claim_scope = "one locked production-off R4 custom Mode2 candidate: canonical pre-execute start gate, accepted official deterministic White pre-clean, then at most nine local 32x32 transitions covering WW/WB/BW/BB with both complete symmetric active-TP groups uniformly quantized from aggregate TP20 to TP16, explicit 0x26 old and 0x24 new planes, one CF/20/BUSY per transition, protected supplier voltage tail, zero candidate full refresh/retry, final local white, and exact raw restore/readback/normal resume"
}
if ($PostCleanWhiteRecoveryOnly) {
    $report.schema_id = "companion.wb55.ssd1681_post_candidate_white_clean_raw_restore_stage_run.v1"
    $report.claim_scope = "one official 5000-byte 0x24/F7/20/BUSY physical White cleanup followed by exact captured-raw restore/readback/normal resume; no custom candidate or LUT"
    $report.pre_execute_prompt.required = $false
    $report.preclean.required = $false
}
if ($dualPlaneWhiteRecoveryOnly) {
    $report.schema_id = "companion.wb55.ssd1681_dual_plane_white_clean_raw_restore_stage_run.v1"
    $report.claim_scope = "one promptless supplier-exact dual-plane all-White BaseMap cleanup with both selectors read twice and proven all-white, followed by exact captured-raw restore/readback/normal resume; no custom candidate or LUT"
    $report.pre_execute_prompt.required = $false
    $report.preclean.required = $false
}

$programmer = $null
$companionLock = $null
$swdMutex = $null
$swdAcquired = $false
$precleanCapture = $null
$postcleanCapture = $null
$candidateCapture = $null
$normalCapture = $null
$hardwareImageAttempted = $false
$precleanAttempted = $false
$postcleanAttempted = $false
$candidateAttempted = $false
$candidateCancelled = $false
$controllerValid = $false
$postcleanValid = $false
$restoreValid = $false
$normalValid = $false
$failureStage = "preflight"

try {
    $requiredInputs = @($backupA, $backupB, $candidateImage)
    if ($customMode2 -or $dualPlaneWhiteRecoveryOnly) {
        $requiredInputs += @($precleanImage, $precleanSourceAudit, $precleanVerifier)
    }
    foreach ($path in $requiredInputs) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required input is missing: $path" }
    }
    if ((Get-Hash $backupA) -ne $baselineSha256 -or (Get-Hash $backupB) -ne $baselineSha256) {
        throw "Captured raw baseline hash mismatch; refusing hardware contact."
    }
    if ((Get-Hash $candidateImage) -ne $candidateSha256) {
        throw "Locked candidate hash mismatch; refusing hardware contact."
    }
    if (($customMode2 -or $whiteRecoveryOnly) -and (Get-Hash $precleanImage) -ne $precleanSha256) {
        throw "Locked deterministic White pre-clean hash mismatch; refusing hardware contact."
    }
    & python $baselineVerifier --backup-a $backupA --backup-b $backupB --out $baselineArtifact
    if ($LASTEXITCODE -ne 0) { throw "Captured raw baseline validation failed before hardware contact." }
    $report.baseline = Get-Content -LiteralPath $baselineArtifact -Raw | ConvertFrom-Json
    $programmer = Find-Programmer
    $report.programmer.executable = $programmer
    $report.programmer.sha256 = Get-Hash $programmer
    & python $staticVerifier
    if ($LASTEXITCODE -ne 0) { throw "Static controller/restore gate failed before hardware contact." }
    if ($CheckOnly) {
        $report.status = "READY_NO_HARDWARE_CONTACT"
        $report.completed_at = (Get-Date).ToUniversalTime().ToString("o")
        Write-Report $report
        Write-Output "CHECK: controller read and exact raw restore gates passed; hardware_contact=0."
        exit 0
    }

    if ($CustomMode2TransitionSafety) {
        $failureStage = "pre_execute_prompt"
        $report.pre_execute_prompt.invoked = $true
        $startDecision = Invoke-CandidateStartPrompt
        $report.pre_execute_prompt.selected = $startDecision.selected
        $report.pre_execute_prompt.note = $startDecision.text
        if ($startDecision.selected -ne "开始实验") {
            $report.status = "CANCELLED_BEFORE_HARDWARE_CONTACT"
            $report.completed_at = (Get-Date).ToUniversalTime().ToString("o")
            Write-Report $report
            Write-Output $report.status
            exit 2
        }
    }
    $failureStage = "lock"
    $companionLock = Enter-CompanionWb55Lock -Purpose $(if ($dualPlaneWhiteRecoveryOnly) { "one promptless dual-plane White cleanup and exact raw restore" } elseif ($dualPlaneCustomMode2) { "one R5 dual-plane-clean custom Mode2 A/B and exact raw restore" } elseif ($CustomMode2TransitionSafety) { "one custom Mode2 local transition safety run and exact raw restore" } elseif ($FastPointProbeInverseSeed) { "one inverse-seed fast point probe and exact raw restore" } elseif ($FastPointProbe) { "one fast point probe and exact raw restore" } elseif ($RamPingPongPointProbe) { "one RAM ping-pong point probe and exact raw restore" } elseif ($RamPingPongFingerprint) { "one RAM ping-pong fingerprint capture and exact raw restore" } elseif ($ResetReadControllerState) { "one hard-reset read-only controller capture and exact raw restore" } else { "one read-only controller capture and exact raw restore" })
    if ($WorkflowLockHeld -and $companionLock.mode -ne "inherited") {
        throw "-WorkflowLockHeld was requested without an inherited Companion-WB55 grant."
    }
    $report.locks.companion_wb55 = Get-CompanionWb55LockEvidenceSummary -Context $companionLock
    $swdMutex = [System.Threading.Mutex]::new($false, "Local\Companion-WB55-SWD-COM-Exclusive-v1")
    try { $swdAcquired = $swdMutex.WaitOne(0) } catch [System.Threading.AbandonedMutexException] { $swdAcquired = $true }
    if (-not $swdAcquired) { throw "SWD/COM exclusive lock is already held; no hardware contact started." }
    $report.locks.swd_com.acquired = $true
    [ordered]@{
        schema_id = "companion.wb55.swd_com_lock.v1"
        status = "HELD"
        process_id = $PID
        acquired_at = (Get-Date).ToUniversalTime().ToString("o")
        mechanism = "Local\\Companion-WB55-SWD-COM-Exclusive-v1"
    } | ConvertTo-Json | Set-Content -LiteralPath $lockArtifact -Encoding UTF8

    if ($customMode2 -or $whiteRecoveryOnly) {
        $failureStage = "preclean_serial_ready"
        New-Item -ItemType Directory -Force -Path $privateRoot | Out-Null
        if (Test-Path -LiteralPath $restoreVerify) { throw "Private restore upload already exists; refusing reuse." }
        $precleanCapture = Start-BoundedSerialCapture -Name "preclean-capture" `
            -OutDir $precleanCaptureRoot -ReadyPath $precleanReady -Seconds 20
        $report.counters.serial_capture_processes++

        $failureStage = "preclean"
        $hardwareImageAttempted = $true
        $precleanAttempted = $true
        $report.hardware_contact = 1
        $report.counters.preclean_programmer_processes = 1
        $report.counters.preclean_write_calls = 1
        $precleanArgs = @("-c", "port=SWD", "mode=UR", "reset=HWrst", "freq=4000",
                          "-w", $precleanImage, "-v", "-rst")
        Invoke-ProgrammerOnce -Programmer $programmer -Operation "preclean-white-write" -Arguments $precleanArgs
        if (-not $precleanCapture.WaitForExit(35000)) {
            Stop-Capture $precleanCapture
            throw "Deterministic White pre-clean serial capture timed out."
        }
        $precleanCapture.WaitForExit()
        if ($precleanCapture.ExitCode -ne 0) { throw "Deterministic White pre-clean serial capture failed." }
        & python $precleanVerifier --pattern white --log $precleanRawLog --out $precleanArtifact --source-audit $precleanSourceAudit
        if ($LASTEXITCODE -ne 0) { throw "Deterministic White pre-clean machine gate failed; candidate is forbidden." }
        if ($whiteRecoveryOnly) {
            New-Item -ItemType Directory -Force -Path $postcleanCaptureRoot | Out-Null
            Copy-Item -LiteralPath $precleanRawLog -Destination $postcleanRawLog
            Copy-Item -LiteralPath $precleanArtifact -Destination $postcleanArtifact
            $report.postclean.result = Get-Content -LiteralPath $postcleanArtifact -Raw | ConvertFrom-Json
            $report.counters.preclean_programmer_processes = 0
            $report.counters.preclean_write_calls = 0
            $report.counters.postclean_programmer_processes = 1
            $report.counters.postclean_write_calls = 1
            $report.counters.postclean_panel_writes = $(if ($dualPlaneCleanProfile) { 2 } else { 1 })
            $report.counters.postclean_panel_refresh_commands = 1
            $report.counters.postclean_panel_busy_waits = 1
            $postcleanAttempted = $true
            $postcleanValid = $true
            $controllerValid = $true
        } else {
            $report.preclean.result = Get-Content -LiteralPath $precleanArtifact -Raw | ConvertFrom-Json
            $report.counters.preclean_panel_writes = $(if ($dualPlaneCleanProfile) { 2 } else { 1 })
            $report.counters.preclean_panel_refresh_commands = 1
            $report.counters.preclean_panel_busy_waits = 1
        }
    }

    if ($dualPlaneCustomMode2 -and -not $whiteRecoveryOnly) {
        $failureStage = "pre_execute_prompt"
        $report.pre_execute_prompt.invoked = $true
        $startDecision = Invoke-CandidateStartPrompt
        $report.pre_execute_prompt.selected = $startDecision.selected
        $report.pre_execute_prompt.note = $startDecision.text
        if ($startDecision.selected -ne "开始实验") {
            $candidateCancelled = $true
            throw "R5 candidate cancelled after promptless dual-plane pre-clean; candidate write is forbidden."
        }
    }

    if (-not $whiteRecoveryOnly) {
    $failureStage = "candidate_serial_ready"
    New-Item -ItemType Directory -Force -Path $privateRoot | Out-Null
    if (Test-Path -LiteralPath $restoreVerify) { throw "Private restore upload already exists; refusing reuse." }
    $candidateCapture = Start-BoundedSerialCapture -Name "candidate-capture" `
        -OutDir $candidateCaptureRoot -ReadyPath $candidateReady -Seconds $(if ($FastPointProbeInverseSeed -or $FastPointProbe) { 80 } elseif ($customMode2 -or $RamPingPongPointProbe) { 40 } elseif ($RamPingPongFingerprint) { 60 } else { $CandidateCaptureSeconds })
    $report.counters.serial_capture_processes++
    $report.hardware_contact = 1

    $failureStage = "candidate"
    $hardwareImageAttempted = $true
    $candidateAttempted = $true
    $report.counters.candidate_programmer_processes = 1
    $report.counters.candidate_write_calls = 1
    $candidateArgs = @("-c", "port=SWD", "mode=UR", "reset=HWrst", "freq=4000",
                       "-w", $candidateImage, "-v", "-rst")
    Invoke-ProgrammerOnce -Programmer $programmer -Operation "candidate-write" -Arguments $candidateArgs
    $candidateWaitSeconds = if ($FastPointProbeInverseSeed -or $FastPointProbe) { 95 } elseif ($RamPingPongFingerprint) { 75 } elseif ($customMode2 -or $RamPingPongPointProbe) { 55 } else { $CandidateCaptureSeconds + 15 }
    if (-not $candidateCapture.WaitForExit($candidateWaitSeconds * 1000)) {
        Stop-Capture $candidateCapture
        throw "Candidate serial capture timed out."
    }
    $candidateCapture.WaitForExit()
    if ($candidateCapture.ExitCode -ne 0) { throw "Candidate serial capture failed." }
    $failureStage = "controller_parser"
    & python $controllerVerifier --log $candidateRawLog --out $controllerArtifact
    $controllerParserExit = $LASTEXITCODE
    if (Test-Path -LiteralPath $controllerArtifact -PathType Leaf) {
        $report.controller_state = Get-Content -LiteralPath $controllerArtifact -Raw | ConvertFrom-Json
    }
    if ($customMode2) {
        $observedTransitions = @($report.controller_state.observed.steps).Count
        $report.counters.panel_hard_resets = 1
        $report.counters.panel_busy_waits = $observedTransitions
        $report.counters.panel_writes = 2 * $observedTransitions
        $report.counters.panel_refresh_commands = $observedTransitions
    } elseif ($FastPointProbeInverseSeed -or $FastPointProbe) {
        $report.counters.panel_hard_resets = 121
        $report.counters.panel_busy_waits = 120
        $report.counters.panel_writes = 242
        $report.counters.panel_refresh_commands = 120
    } elseif ($RamPingPongPointProbe) {
        $report.counters.panel_hard_resets = 25
        $report.counters.panel_busy_waits = 24
        $report.counters.panel_writes = 50
        $report.counters.panel_refresh_commands = 24
    } elseif ($RamPingPongFingerprint) {
        $report.counters.panel_hard_resets = 2
        $report.counters.panel_busy_waits = 4
        $report.counters.panel_writes = 3
        $report.counters.panel_refresh_commands = 2
    } elseif ($ResetReadControllerState) {
        $report.counters.panel_hard_resets = 1
        $report.counters.panel_busy_waits = 1
    }
    if ($controllerParserExit -ne 0) { throw "Read-only controller-state parser gate failed." }
    $controllerValid = $true
    }
} catch {
    $reason = $_.Exception.Message
    $report.error = $reason
    if ($hardwareImageAttempted) {
        $report.controller_error = $reason
    } else {
        $report.status = "NO_GO_$($failureStage.ToUpperInvariant())_ZERO_WRITES"
    }
} finally {
    Stop-Capture $precleanCapture
    Stop-Capture $candidateCapture
    if ($hardwareImageAttempted) {
        if ($customMode2 -and $candidateAttempted) {
            $postcleanAttempted = $true
            try {
                $failureStage = "postclean"
                $postcleanCapture = Start-BoundedSerialCapture -Name "postclean-capture" `
                    -OutDir $postcleanCaptureRoot -ReadyPath $postcleanReady -Seconds 20
                $report.counters.serial_capture_processes++
                $report.counters.postclean_programmer_processes = 1
                $report.counters.postclean_write_calls = 1
                $postcleanArgs = @("-c", "port=SWD", "mode=UR", "reset=HWrst", "freq=4000",
                                   "-w", $precleanImage, "-v", "-rst")
                Invoke-ProgrammerOnce -Programmer $programmer -Operation "postclean-white-write" -Arguments $postcleanArgs
                if (-not $postcleanCapture.WaitForExit(35000)) {
                    Stop-Capture $postcleanCapture
                    throw "Mandatory post-candidate White cleanup serial capture timed out."
                }
                $postcleanCapture.WaitForExit()
                if ($postcleanCapture.ExitCode -ne 0) { throw "Mandatory post-candidate White cleanup serial capture failed." }
                & python $precleanVerifier --pattern white --log $postcleanRawLog --out $postcleanArtifact --source-audit $precleanSourceAudit
                if ($LASTEXITCODE -ne 0) { throw "Mandatory post-candidate White cleanup machine gate failed." }
                $report.postclean.result = Get-Content -LiteralPath $postcleanArtifact -Raw | ConvertFrom-Json
                $report.counters.postclean_panel_writes = $(if ($dualPlaneCleanProfile) { 2 } else { 1 })
                $report.counters.postclean_panel_refresh_commands = 1
                $report.counters.postclean_panel_busy_waits = 1
                $postcleanValid = $true
            } catch {
                $report.controller_error = "Post-candidate physical White cleanup failed: $($_.Exception.Message)"
                $postcleanValid = $false
            } finally {
                Stop-Capture $postcleanCapture
            }
        }
        $normalCaptureReady = $false
        try {
            $normalCapture = Start-BoundedSerialCapture -Name "normal-capture" `
                -OutDir $normalCaptureRoot -ReadyPath $normalReady -Seconds $NormalCaptureSeconds
            $normalCaptureReady = $true
            $report.counters.serial_capture_processes++
        } catch {
            $report.restore_error = "Normal serial capture was not ready before the mandatory restore: $($_.Exception.Message)"
        }

        try {
            $report.counters.restore_programmer_processes = 1
            $report.counters.restore_write_calls = 1
            $report.counters.restore_verify_operations = 1
            $report.counters.restore_upload_calls = 1
            $report.counters.restore_reset_arguments = 1
            $restoreArgs = @("-c", "port=SWD", "mode=UR", "reset=HWrst", "freq=4000",
                             "-w", $backupA, "0x08000000",
                             "-v", $backupA, "0x08000000",
                             "-u", "0x08000000", "0x80000", $restoreVerify, "-rst")
            Invoke-ProgrammerOnce -Programmer $programmer -Operation "restore-write-verify-upload" -Arguments $restoreArgs
            & python $restoreVerifier --backup-a $backupA --backup-b $backupB `
                --restore-verify $restoreVerify --out $restoreArtifact
            if ($LASTEXITCODE -ne 0) { throw "Post-restore upload differs from captured pre-run application bytes." }
            $report.restore = Get-Content -LiteralPath $restoreArtifact -Raw | ConvertFrom-Json
            $report.images.restore_verify.bytes = [int64](Get-Item $restoreVerify).Length
            $report.images.restore_verify.sha256 = Get-Hash $restoreVerify
            $report.restore_identity = "RESTORED_TO_CAPTURED_PRE_RUN_APPLICATION_BYTES"
            $restoreValid = $true
        } catch {
            $report.restore_error = $_.Exception.Message
        }

        if ($normalCaptureReady) {
            try {
                if (-not $normalCapture.WaitForExit(($NormalCaptureSeconds + 10) * 1000)) {
                    Stop-Capture $normalCapture
                    throw "Post-restore normal serial capture timed out."
                }
                $normalCapture.WaitForExit()
                if ($normalCapture.ExitCode -ne 0) { throw "Post-restore normal serial capture failed." }
                & python $normalVerifier --log $normalRawLog --out $normalArtifact
                if ($LASTEXITCODE -ne 0) { throw "Post-restore normal application resumption was not proven." }
                $report.normal_resume = Get-Content -LiteralPath $normalArtifact -Raw | ConvertFrom-Json
                $normalValid = $true
            } catch {
                if (-not $report.restore_error) { $report.restore_error = $_.Exception.Message }
            }
        }
        Stop-Capture $normalCapture

        if (-not $restoreValid -or -not $normalValid) {
            $report.status = "NEED_HUMAN_RESTORE_OR_APPLICATION_FAILED"
            $report.operator_prompt.required = $true
            $promptReason = if ($report.restore_error) { $report.restore_error } else { "Restore or normal application gate failed." }
            try {
                $report.operator_prompt.invoked = $true
                Invoke-RestoreFailurePrompt -Reason $promptReason
            } catch {
                $report.operator_prompt.error = $_.Exception.Message
            }
        } elseif ($customMode2 -and $controllerValid -and -not $postcleanValid) {
            $report.status = "NO_GO_CUSTOM_MODE2_POSTCLEAN_FAILED_RESTORED"
        } elseif ($controllerValid) {
            $report.status = $passStatus
        } elseif ($dualPlaneCustomMode2 -and $candidateCancelled -and $precleanAttempted -and -not $candidateAttempted) {
            $report.status = "CANCELLED_R5_AFTER_DUAL_PLANE_PRECLEAN_EXACT_RAW_RESTORED"
        } elseif ($customMode2 -and $precleanAttempted -and -not $candidateAttempted) {
            $report.status = "NO_GO_CUSTOM_MODE2_PRECLEAN_RESTORED"
        } else {
        $report.status = $(if ($customMode2) { "NO_GO_CUSTOM_MODE2_TRANSITION_SAFETY_RESTORED" } elseif ($FastPointProbeInverseSeed) { "NO_GO_SSD1681_FAST_POINT_PROBE_INVERSE_SEED_RESTORED" } elseif ($FastPointProbe) { "NO_GO_SSD1681_FAST_POINT_PROBE_RESTORED" } elseif ($RamPingPongPointProbe) { "NO_GO_RAM_PING_PONG_POINT_PROBE_RESTORED" } elseif ($RamPingPongFingerprint) { "NO_GO_RAM_MAPPING_RESTORED" } else { "NO_GO_CONTROLLER_READ_RESTORED" })
        }
    }

    if ($swdAcquired -and $swdMutex) {
        try {
            if (Test-Path -LiteralPath $lockArtifact -PathType Leaf) {
                $lockEvidence = Get-Content -LiteralPath $lockArtifact -Raw | ConvertFrom-Json -AsHashtable
                $lockEvidence.status = "RELEASED"
                $lockEvidence.released_at = (Get-Date).ToUniversalTime().ToString("o")
                $lockEvidence | ConvertTo-Json | Set-Content -LiteralPath $lockArtifact -Encoding UTF8
            }
        } finally {
            $swdMutex.ReleaseMutex()
            $swdMutex.Dispose()
        }
    }
    if ($companionLock) { Exit-CompanionWb55Lock }
    $report.completed_at = (Get-Date).ToUniversalTime().ToString("o")
    Write-Report $report
}

if ($report.status -eq $passStatus) {
    Write-Output $report.status
    exit 0
}
if ($report.status -eq "NO_GO_CONTROLLER_READ_RESTORED" -or $report.status -eq "NO_GO_RAM_MAPPING_RESTORED" -or $report.status -eq "NO_GO_RAM_PING_PONG_POINT_PROBE_RESTORED" -or $report.status -eq "NO_GO_SSD1681_FAST_POINT_PROBE_RESTORED" -or $report.status -eq "NO_GO_SSD1681_FAST_POINT_PROBE_INVERSE_SEED_RESTORED" -or $report.status -eq "NO_GO_CUSTOM_MODE2_PRECLEAN_RESTORED" -or $report.status -eq "NO_GO_CUSTOM_MODE2_POSTCLEAN_FAILED_RESTORED" -or $report.status -eq "NO_GO_CUSTOM_MODE2_TRANSITION_SAFETY_RESTORED") {
    throw "Diagnostic machine gate failed; captured raw application bytes were restored exactly."
}
if ($report.status -eq "NEED_HUMAN_RESTORE_OR_APPLICATION_FAILED") {
    throw "Restore or normal application recovery failed; human assistance is required."
}
throw "Run completed $($report.status): $($report.error)"
