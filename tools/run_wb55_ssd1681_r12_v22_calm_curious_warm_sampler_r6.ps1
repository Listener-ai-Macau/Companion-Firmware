param(
    [switch]$CheckOnly,
    [switch]$Execute,
    [switch]$WorkflowLockHeld,
    [switch]$ResetReadControllerState,
    [switch]$RamPingPongFingerprint,
    [switch]$RamCommandTargetR8,
    [switch]$RamPingPongPointProbe,
    [switch]$FastPointProbe,
    [switch]$FastPointProbeInverseSeed,
    [switch]$CustomMode2TransitionSafety,
    [switch]$CustomMode2TransitionSafetyDualPlaneClean,
    [switch]$CustomMode2ObservableR6,
    [switch]$PhaseParallelR10,
    [switch]$R12Sampler,
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
    [string]$AuthorizationArtifact,
    [string]$ProgrammerRoot = "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if ($CheckOnly -eq $Execute) {
    throw "Choose exactly one of -CheckOnly or -Execute."
}
if (-not $R12Sampler) {
    throw "R12 runner exposes only -CheckOnly/-Execute with -R12Sampler. Legacy diagnostic modes are unreachable."
}
if (@($ResetReadControllerState, $RamPingPongFingerprint, $RamCommandTargetR8, $RamPingPongPointProbe, $FastPointProbe, $FastPointProbeInverseSeed, $CustomMode2TransitionSafety, $CustomMode2TransitionSafetyDualPlaneClean, $CustomMode2ObservableR6, $PhaseParallelR10, $PostCleanWhiteRecoveryOnly, $DualPlaneWhiteRecoveryOnly).Where({ $_ }).Count -gt 0) {
    throw "Unsupported legacy diagnostic mode is unreachable in the R12 runner."
}
$customMode2 = $CustomMode2TransitionSafety -or $CustomMode2TransitionSafetyDualPlaneClean -or $CustomMode2ObservableR6 -or $PhaseParallelR10 -or $R12Sampler
$dualPlaneCustomMode2 = $CustomMode2TransitionSafetyDualPlaneClean.IsPresent
$observableR6 = $CustomMode2ObservableR6.IsPresent
$phaseParallelR10 = $PhaseParallelR10.IsPresent
$continuousR10 = $R12Sampler.IsPresent
$commandTargetR8 = $RamCommandTargetR8.IsPresent
$requiresDualPlaneLifecycle = $customMode2 -or $commandTargetR8
$dualPlaneWhiteRecoveryOnly = $DualPlaneWhiteRecoveryOnly.IsPresent
$whiteRecoveryOnly = $PostCleanWhiteRecoveryOnly.IsPresent -or $dualPlaneWhiteRecoveryOnly
$dualPlaneCleanProfile = $dualPlaneCustomMode2 -or $observableR6 -or $phaseParallelR10 -or $continuousR10 -or $commandTargetR8 -or $dualPlaneWhiteRecoveryOnly

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
. (Join-Path $PSScriptRoot "companion_wb55_lock.ps1")
$staticVerifier = Join-Path $PSScriptRoot $(if ($continuousR10) { "verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_static.py" } elseif ($commandTargetR8) { "verify_wb55_ssd1681_ram_command_target_r8_diagnostic.py" } elseif ($phaseParallelR10) { "verify_wb55_ssd1681_phase_parallel_r10_diagnostic.py" } elseif ($observableR6) { "verify_wb55_ssd1681_custom_mode2_observable_r6.py" } elseif ($dualPlaneCleanProfile) { "verify_wb55_ssd1681_custom_mode2_dual_plane_clean_r6.py" } elseif ($CustomMode2TransitionSafety) { "verify_wb55_ssd1681_custom_mode2_transition_safety_diagnostic.py" } elseif ($FastPointProbeInverseSeed) { "verify_wb55_ssd1681_fast_point_probe_inverse_seed_diagnostic.py" } elseif ($FastPointProbe) { "verify_wb55_ssd1681_fast_point_probe_diagnostic.py" } elseif ($RamPingPongPointProbe) { "verify_wb55_ssd1681_ram_ping_pong_point_probe_diagnostic.py" } elseif ($RamPingPongFingerprint) { "verify_wb55_ssd1681_ram_ping_pong_fingerprint_diagnostic.py" } elseif ($ResetReadControllerState) { "verify_wb55_ssd1681_reset_read_controller_state_diagnostic.py" } else { "verify_wb55_ssd1681_read_only_controller_state_raw_restore_diagnostic.py" })
if ($PostCleanWhiteRecoveryOnly) { $staticVerifier = Join-Path $PSScriptRoot "verify_wb55_ssd1681_postclean_white_recovery.py" }
$baselineVerifier = Join-Path $PSScriptRoot "verify_wb55_ur_application_backup.py"
$staticVerifier = Join-Path $PSScriptRoot "verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r6_static.py"
$controllerVerifier = Join-Path $PSScriptRoot $(if ($continuousR10) { "verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r6_log.py" } elseif ($commandTargetR8) { "verify_wb55_ssd1681_ram_command_target_r8_log.py" } elseif ($phaseParallelR10) { "verify_wb55_ssd1681_phase_parallel_r10_log.py" } elseif ($observableR6) { "verify_wb55_ssd1681_custom_mode2_observable_r6_log.py" } elseif ($customMode2) { "verify_wb55_ssd1681_custom_mode2_transition_safety_log.py" } elseif ($FastPointProbeInverseSeed) { "verify_wb55_ssd1681_fast_point_probe_inverse_seed_log.py" } elseif ($FastPointProbe) { "verify_wb55_ssd1681_fast_point_probe_log.py" } elseif ($RamPingPongPointProbe) { "verify_wb55_ssd1681_ram_ping_pong_point_probe_log.py" } elseif ($RamPingPongFingerprint) { "verify_wb55_ssd1681_ram_ping_pong_fingerprint_log.py" } elseif ($ResetReadControllerState) { "verify_wb55_ssd1681_reset_read_controller_state_log.py" } else { "verify_wb55_ssd1681_read_only_controller_state_log.py" })
$restoreVerifier = Join-Path $PSScriptRoot "verify_wb55_raw_application_restore.py"
$candidateImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_r12_v22_calm_curious_warm_sampler\Companion_Nucleo_WB55RG_Ssd1681R12V22CalmCuriousWarmSampler.hex"
$normalVerifier = Join-Path $PSScriptRoot "verify_wb55_normal_resume_after_ur_backup_log.py"
$r10VisualPrompt = Join-Path $PSScriptRoot "invoke_wb55_ssd1681_phase_parallel_r10_final_visual_prompt.ps1"
$continuousMonitor = Join-Path $PSScriptRoot "monitor_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r6.ps1"
$continuousPromptSupervisor = Join-Path $PSScriptRoot "supervise_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_prompt.ps1"
$continuousPromptSupervisor = Join-Path $PSScriptRoot "supervise_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_prompt_r6.ps1"
$precleanVerifier = Join-Path $PSScriptRoot "verify_wb55_official_full_diagnostic_log.py"
$dualPlaneCleanVerifier = Join-Path $PSScriptRoot "verify_wb55_ssd1681_dual_plane_white_clean_log.py"
$captureRunner = Join-Path $PSScriptRoot "capture_nucleo_serial.ps1"
$candidateImage = Join-Path $repoRoot $(if ($continuousR10) { "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_r12_v22_calm_curious_warm_sampler\Companion_Nucleo_WB55RG_Ssd1681R12V22CalmCuriousWarmSampler.hex" } elseif ($customMode2) { "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_custom_mode2_transition_safety\Companion_Nucleo_WB55RG_Ssd1681CustomMode2TransitionSafety.hex" } elseif ($FastPointProbeInverseSeed) { "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_fast_point_probe_inverse_seed\Companion_Nucleo_WB55RG_Ssd1681FastPointProbeInverseSeed.hex" } elseif ($FastPointProbe) { "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_fast_point_probe\Companion_Nucleo_WB55RG_Ssd1681FastPointProbe.hex" } elseif ($RamPingPongPointProbe) { "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_ram_ping_pong_point_probe\Companion_Nucleo_WB55RG_Ssd1681RamPingPongPointProbe.hex" } elseif ($RamPingPongFingerprint) { "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_ram_ping_pong_fingerprint\Companion_Nucleo_WB55RG_Ssd1681RamPingPongFingerprint.hex" } elseif ($ResetReadControllerState) { "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_reset_read_controller_state\Companion_Nucleo_WB55RG_Ssd1681ResetReadControllerState.hex" } else { "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_read_only_controller_state\Companion_Nucleo_WB55RG_Ssd1681ReadOnlyControllerState.hex" })
if ($commandTargetR8) {
    $candidateImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_ram_command_target_r8\Companion_Nucleo_WB55RG_Ssd1681RamCommandTargetR8.hex"
}
if ($observableR6) {
    $candidateImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_custom_mode2_observable_r6\Companion_Nucleo_WB55RG_Ssd1681CustomMode2ObservableR6.hex"
}
if ($phaseParallelR10) {
    $candidateImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_phase_parallel_r10\Companion_Nucleo_WB55RG_Ssd1681PhaseParallelR10.hex"
}
if ($continuousR10) {
    $candidateImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_r12_v22_calm_curious_warm_sampler\Companion_Nucleo_WB55RG_Ssd1681R12V22CalmCuriousWarmSampler.hex"
}
$precleanImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_official_full_diagnostic_white\Companion_Nucleo_WB55RG_OfficialFullDiagnostic_white.hex"
$candidateImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_r12_v22_calm_curious_warm_sampler\Companion_Nucleo_WB55RG_Ssd1681R12V22CalmCuriousWarmSampler.hex"
$dualPlaneCleanImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_dual_plane_white_clean\Companion_Nucleo_WB55RG_Ssd1681DualPlaneWhiteClean.hex"
if ($dualPlaneCleanProfile) { $precleanImage = $dualPlaneCleanImage; $precleanVerifier = $dualPlaneCleanVerifier }

if ($whiteRecoveryOnly) { $candidateImage = $precleanImage }
$precleanSourceAudit = Join-Path $repoRoot "docs\validation\companion-gdey0154d67-t03-vendor-1s-source-audit-r2-20260721.json"
$baselineRoot = Join-Path $repoRoot ".cache\validation\wb55-ur-dual-application-backup-execute-20260721-r1\private"
$backupA = Join-Path $baselineRoot "backup-a.bin"
$backupB = Join-Path $baselineRoot "backup-b.bin"
$candidateSha256 = if ($customMode2) { "E695A1A6D3D121AA585E69A1A0D8DA21FEBC5566198BD314FE27F2D40C30B564" } elseif ($FastPointProbeInverseSeed) { "F7E20B26A479F690064F95FED25B18F632B3CDBC2AEDDD842645377CA0EBB2E9" } elseif ($FastPointProbe) { "210B9851889457F951E20FC96DC509CA4DCB8B779E40031F7DC47C136C4CB222" } elseif ($RamPingPongPointProbe) { "00880EBC4678ED83927FE69A797876C0513BF7AE4D18119FCE5E7FC833A64F0B" } elseif ($RamPingPongFingerprint) { "2ED8AEC1B665C4FF516BE603D9C2CCEEAEB6411CFF38B6113283FBEEA7E17B90" } elseif ($ResetReadControllerState) { "DB6F1CDBC091A8F4B12AFDB82BBCA62E9C850D57B343E722C4EBE5E05BB7AD7E" } else { "52D79CB3BC55D9738EFA580B95D3930216C23FD8825356F7860B7C1718C0C6AD" }
if ($commandTargetR8) { $candidateSha256 = "9ECF8F4A2A75A054077908C775879447ADCE089F55DC33315A8C852C4F47CB13" }
if ($observableR6) { $candidateSha256 = "71933D316D2D6DCDA75DB1C387B012D7B44E9C61244BEEBD4BF7C3DD68047D99" }
if ($phaseParallelR10) { $candidateSha256 = "724DA17F385756BA779739E73DA47131F563E0C071A2EB173F5F77871F3CADDF" }
if ($continuousR10) { $candidateSha256 = "BD2D86EB95EF9C0E63E86251D4FB29CCA96BFD3F1EC9B6B0847A583D1F12E494" }
$precleanSha256 = "F7CB7EE8C497CF1A01ACFF4BC921B43E274B0A934CA8B658AC24C34480F32925"
$dualPlaneCleanSha256 = "3AC4E52E37E15DC3CC058A4B0B0E6A3227D23E6C6DEFAEDCB786C08497888AAD"
if ($dualPlaneCleanProfile) { $precleanSha256 = $dualPlaneCleanSha256 }
if ($whiteRecoveryOnly) { $candidateSha256 = $precleanSha256 }
$baselineSha256 = "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C"
$programmerSha256 = "BD520005962377155515A2C9E8FEAB73F304A696AAE1698F3B7760672160FD5E"
$machineManifestRoot = Join-Path $repoRoot "docs\validation"
function Validate-MachineManifest([string]$Path,[hashtable]$Expected){
    if(-not $Path){throw "Consumed authorization has no machine_ready_path."}
    $candidate=[IO.Path]::GetFullPath($Path);$docs=[IO.Path]::GetFullPath($machineManifestRoot);$relative=[IO.Path]::GetRelativePath($docs,$candidate)
    if(-not $candidate.EndsWith('.json',[StringComparison]::OrdinalIgnoreCase) -or $relative -eq '..' -or $relative.StartsWith('..'+[IO.Path]::DirectorySeparatorChar) -or $relative.Contains([IO.Path]::DirectorySeparatorChar) -or $relative.Contains([IO.Path]::AltDirectorySeparatorChar) -or -not(Test-Path -LiteralPath $candidate -PathType Leaf)){throw "machine_ready_path must be a repository docs/validation leaf JSON."}
    $manifest=Get-Content -LiteralPath $candidate -Raw|ConvertFrom-Json;$artifacts=$manifest.artifacts
    if([string]$manifest.schema_id -notmatch '^companion\.wb55\.ssd1681\..*machine_ready\.v[0-9]+$' -or [string]$manifest.status -notmatch '^MACHINE_READY_' -or $manifest.hardware_contact -ne 0 -or $manifest.execute_authorized -eq $true -or $manifest.authorization_created -eq $true){throw "machine_ready manifest status or safety boundary is invalid."}
    if([string]$artifacts.hex -ne [string]$Expected.candidate_hex_sha256 -or [string]$artifacts.runner -ne [string]$Expected.runner_sha256 -or [string]$artifacts.monitor -ne [string]$Expected.monitor_sha256 -or [string]$artifacts.supervisor -ne [string]$Expected.supervisor_sha256 -or [string]$artifacts.launcher -ne [string]$Expected.launcher_sha256 -or [string]$artifacts.parser_sha256 -ne [string]$Expected.parser_sha256){throw "machine_ready manifest artifact hashes do not match current tools."}
    return $candidate
}
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runRoot = if ($OutRoot) { [System.IO.Path]::GetFullPath($OutRoot) } else {
    Join-Path $repoRoot $(if ($dualPlaneWhiteRecoveryOnly) { ".cache\validation\wb55-dual-plane-white-recovery-raw-restore-$stamp" } elseif ($dualPlaneCustomMode2) { ".cache\validation\wb55-custom-mode2-dual-plane-clean-r6-raw-restore-$stamp" } elseif ($CustomMode2TransitionSafety) { ".cache\validation\wb55-custom-mode2-transition-safety-raw-restore-$stamp" } elseif ($FastPointProbeInverseSeed) { ".cache\validation\wb55-fast-point-probe-inverse-seed-raw-restore-$stamp" } elseif ($FastPointProbe) { ".cache\validation\wb55-fast-point-probe-raw-restore-$stamp" } elseif ($RamPingPongPointProbe) { ".cache\validation\wb55-ram-ping-pong-point-probe-raw-restore-$stamp" } elseif ($RamPingPongFingerprint) { ".cache\validation\wb55-ram-ping-pong-fingerprint-raw-restore-$stamp" } elseif ($ResetReadControllerState) { ".cache\validation\wb55-reset-read-controller-raw-restore-$stamp" } else { ".cache\validation\wb55-readonly-controller-raw-restore-$stamp" })
}
if (-not $OutRoot -and $commandTargetR8) {
    $runRoot = Join-Path $repoRoot ".cache\validation\wb55-ram-command-target-r8-raw-restore-$stamp"
}
if (-not $OutRoot -and $observableR6) {
    $runRoot = Join-Path $repoRoot ".cache\validation\wb55-custom-mode2-observable-r6-raw-restore-$stamp"
}
if (-not $OutRoot -and $phaseParallelR10) {
    $runRoot = Join-Path $repoRoot ".cache\validation\wb55-phase-parallel-r10-raw-restore-$stamp"
}
if (-not $OutRoot -and $continuousR10) {
    $runRoot = Join-Path $repoRoot ".cache\validation\wb55-r12-v22-sampler-continuous-observation-raw-restore-$stamp"
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
$reportPath = Join-Path $runRoot "stage-run.json"
$operatorReviewArtifact = Join-Path $runRoot "operator-review.json"
$operatorNotePath = Join-Path $runRoot "operator-note.txt"
$continuousMonitorRoot = Join-Path $runRoot "continuous-monitor"
$continuousMonitorReady = Join-Path $runRoot "continuous-monitor-ready.json"
$continuousQualificationReady = Join-Path $runRoot "continuous-qualification-ready.json"
$continuousStopSignal = Join-Path $runRoot "continuous-stop.json"
$continuousEmergencyStop = Join-Path $runRoot "continuous-emergency-stop.json"
$continuousMonitorResult = Join-Path $continuousMonitorRoot "monitor-result.json"
New-Item -ItemType Directory -Force -Path $runRoot | Out-Null

function Get-Hash([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

# The R12 candidate identity is the built HEX itself; the authorization binds
# this resolved artifact rather than a stale release-specific constant.
if ($continuousR10 -and (Test-Path -LiteralPath $candidateImage -PathType Leaf)) {
    $candidateSha256 = Get-Hash $candidateImage
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

function Stop-ProcessTree([AllowNull()][System.Diagnostics.Process]$Process) {
    if (-not $Process -or $Process.HasExited) { return }
    $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$($Process.Id)" -ErrorAction SilentlyContinue)
    foreach ($child in $children) {
        $childProcess = Get-Process -Id ([int]$child.ProcessId) -ErrorAction SilentlyContinue
        Stop-ProcessTree $childProcess
    }
    Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
    $Process.WaitForExit()
}

$passStatus = if ($continuousR10) { "PASS_MACHINE_R12_V22_CALM_CURIOUS_WARM_SAMPLER_OBSERVATION_RESTORED_OWNER_PASSED" } elseif ($commandTargetR8) { "PASS_MACHINE_RAM_COMMAND_TARGET_R8_RESTORED" } elseif ($phaseParallelR10) { "PASS_MACHINE_PHASE_PARALLEL_R10_RESTORED_OWNER_PASSED" } elseif ($observableR6) { "PASS_MACHINE_CUSTOM_MODE2_OBSERVABLE_R6_RESTORED" } elseif ($dualPlaneCustomMode2) { "PASS_MACHINE_CUSTOM_MODE2_DUAL_PLANE_CLEAN_R6_RESTORED" } elseif ($CustomMode2TransitionSafety) { "PASS_MACHINE_CUSTOM_MODE2_TRANSITION_SAFETY_RESTORED" } elseif ($FastPointProbeInverseSeed) { "PASS_MACHINE_SSD1681_FAST_POINT_PROBE_INVERSE_SEED_RESTORED" } elseif ($FastPointProbe) { "PASS_MACHINE_SSD1681_FAST_POINT_PROBE_RESTORED" } elseif ($RamPingPongPointProbe) { "PASS_MACHINE_RAM_PING_PONG_POINT_PROBE_RESTORED" } elseif ($RamPingPongFingerprint) { "PASS_MACHINE_RAM_PING_PONG_FINGERPRINT_RESTORED" } elseif ($ResetReadControllerState) { "PASS_MACHINE_RESET_READ_CONTROLLER_STATE_RESTORED" } else { "PASS_MACHINE_READ_ONLY_CONTROLLER_STATE_RESTORED" }
if ($PostCleanWhiteRecoveryOnly) { $passStatus = "PASS_POST_CANDIDATE_WHITE_CLEAN_EXACT_RAW_RESTORED" }
if ($dualPlaneWhiteRecoveryOnly) { $passStatus = "PASS_DUAL_PLANE_WHITE_CLEAN_EXACT_RAW_RESTORED" }
$report = [ordered]@{
    schema_id = if ($continuousR10) { "companion.wb55.ssd1681_r12_v22_calm_curious_warm_sampler_observation_raw_restore_stage_run.v1" } elseif ($commandTargetR8) { "companion.wb55.ssd1681_ram_command_target_r8_raw_restore_stage_run.v1" } elseif ($phaseParallelR10) { "companion.wb55.ssd1681_phase_parallel_r10_raw_restore_stage_run.v1" } elseif ($observableR6) { "companion.wb55.ssd1681_custom_mode2_observable_r6_raw_restore_stage_run.v1" } elseif ($dualPlaneCustomMode2) { "companion.wb55.ssd1681_custom_mode2_dual_plane_clean_r6_raw_restore_stage_run.v1" } elseif ($CustomMode2TransitionSafety) { "companion.wb55.ssd1681_custom_mode2_transition_safety_raw_restore_stage_run.v1" } elseif ($FastPointProbeInverseSeed) { "companion.wb55.ssd1681_fast_point_probe_inverse_seed_raw_restore_stage_run.v1" } elseif ($FastPointProbe) { "companion.wb55.ssd1681_fast_point_probe_raw_restore_stage_run.v1" } elseif ($RamPingPongPointProbe) { "companion.wb55.ssd1681_ram_ping_pong_point_probe_raw_restore_stage_run.v1" } elseif ($RamPingPongFingerprint) { "companion.wb55.ssd1681_ram_ping_pong_fingerprint_raw_restore_stage_run.v1" } elseif ($ResetReadControllerState) { "companion.wb55.ssd1681_reset_read_controller_state_raw_restore_stage_run.v1" } else { "companion.wb55.ssd1681_read_only_controller_state_raw_restore_stage_run.v1" }
    status = "PREFLIGHT"
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    mode = if ($CheckOnly) { "check_only" } else { "execute" }

    claim_scope = if ($CustomMode2TransitionSafety) { "one locked production-off R3 custom Mode2 candidate with zero pre-execute popup, accepted official deterministic White pre-clean, then at most nine local 32x32 transitions covering WW/WB/BW/BB with exactly one R2 TP byte decremented for total TP19, explicit 0x26 old and 0x24 new planes, one CF/20/BUSY per transition, protected supplier voltage tail, zero candidate full refresh/retry, final local white, and exact raw restore/readback/normal resume" } elseif ($FastPointProbeInverseSeed) { "one locked 120-frame production-off fast point probe changing only the first previous-plane seed to a local inverse corridor, with one FF/20/BUSY and post-sync per frame, zero motion 0x26/full/LUT/retry, and exact raw restore" } elseif ($FastPointProbe) { "one locked 120-frame production-off fast point probe, 8 px steps over 32 px, one FF/20/BUSY and one post-activation 0x24 no-refresh sync per frame, zero motion 0x26, zero retry, and one exact captured-raw restore" } elseif ($RamPingPongPointProbe) { "one locked 24-frame production-off point probe, one FF/20/BUSY and one post-activation 0x24 no-refresh sync per frame, zero motion 0x26, zero retry, and one exact captured-raw restore" } elseif ($RamPingPongFingerprint) { "one locked production-off RAM fingerprint candidate, exactly two activations, twelve 5001-byte reads, zero retry, and one exact captured-raw restore" } elseif ($ResetReadControllerState) { "one locked candidate with exactly one panel hard reset, one bounded BUSY wait, three 0x2F/0x2D read-only groups, and one exact captured-raw restore" } else { "one locked 0x2F/0x2D read-only candidate and one exact captured-raw restore" }
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
    native_candidate_metrics = [ordered]@{
        baseline_activations = 1
        qualification_logical_frames = 16
        qualification_activations = 16
        loop_activations_per_record = 1
        candidate_panel_writes_formula = "1+16+1*loop_records"
        candidate_refresh_commands_formula = "1+16+1*loop_records"
        candidate_busy_waits_formula = "1+16+1*loop_records"
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
    authorization = $null
    programmer_calls = @()
    baseline = $null
    popup_policy = [ordered]@{ pre_execute = 0; cleanup = 0; recovery_or_fault_acknowledgement = 0; machine_only_r8_total = $(if ($commandTargetR8) { 0 } else { $null }); visual_acceptance = $(if ($phaseParallelR10 -or $continuousR10) { 1 } else { 0 }) }
    pre_execute_prompt = [ordered]@{ required = $false; invoked = $false; selected = $null; note = $null; artifact = $null; superseded_by = "COMP-REQ-305" }
    preclean = [ordered]@{ required = $requiresDualPlaneLifecycle; promptless = $true; profile = $(if ($dualPlaneCleanProfile) { "supplier_basemap_0x24_0x26_f7_white_readback" } else { "official_0x24_f7_white" }); excluded_from_candidate_metrics = $true; result = $null }
    postclean = [ordered]@{ required = $requiresDualPlaneLifecycle -or $whiteRecoveryOnly; promptless = $true; profile = $(if ($dualPlaneCleanProfile) { "supplier_basemap_0x24_0x26_f7_white_readback" } else { "official_0x24_f7_white" }); result = $null }
    controller_state = $null
    restore = $null
    normal_resume = $null
    restore_identity = $null
    operator_prompt = [ordered]@{ required = [bool]($phaseParallelR10 -or $continuousR10); invoked = $false; selected = $null; note = $null; path = $operatorReviewArtifact; note_path = $operatorNotePath; error = $null; policy = $(if ($continuousR10) { "one_canonical_chinese_pass_fail_concurrent_with_unbounded_local_loop_after_initial_16_pass" } elseif ($phaseParallelR10) { "one_final_canonical_chinese_pass_fail_after_machine_candidate_before_promptless_cleanup_restore" } else { "final_visual_acceptance_only_outside_machine_runner" }) }
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
        operator_review = $operatorReviewArtifact
        operator_note = $operatorNotePath
        report = $reportPath
    }
}

if ($dualPlaneCustomMode2) {
    $report.claim_scope = "one production-off R6 baseline-correction A/B: promptless supplier-exact dual-plane all-White BaseMap pre-clean with two selectors read twice and proven all-white, then the byte-identical R4 TP16 custom Mode2 candidate with zero pre-execute popup, then unconditional promptless identical dual-plane post-clean and exact raw restore/readback/normal resume"
} elseif ($CustomMode2TransitionSafety) {
    $report.claim_scope = "one locked production-off R4 custom Mode2 candidate with zero pre-execute popup, accepted official deterministic White pre-clean, then at most nine local 32x32 transitions covering WW/WB/BW/BB with both complete symmetric active-TP groups uniformly quantized from aggregate TP20 to TP16, explicit 0x26 old and 0x24 new planes, one CF/20/BUSY per transition, protected supplier voltage tail, zero candidate full refresh/retry, final local white, and exact raw restore/readback/normal resume"
}
if ($observableR6) {
    $report.claim_scope = "one production-off R6 observation candidate: promptless supplier-exact dual-plane all-White pre-clean with both selectors read twice and all-white, zero pre-execute popup, then immediate W-to-A/A-to-B/B-to-A alternating and final A-to-W sequence of exactly 16 complete 32x32 old/new-bank local activations with no countdown/dwell/compensation/full-frame/retry/120-frame motion, followed by promptless identical post-clean and exact raw restore/readback/normal resume"
}
if ($phaseParallelR10) {

    $report.claim_scope = "one production-off R10 phase-parallel candidate: promptless dual-plane all-White pre-clean with both selectors read twice, zero start/cleanup/recovery/fault popup, then exactly 16 contiguous 32x32 old/new local activations covering WW/WB/BW/BB with explicit fixed-bank 0x26 selector1 previous and 0x24 selector0 current, CF/20/BUSY <=600 ms, post-BUSY 0x24 no-refresh synchronization, no full-frame/F7/C7/FF/retry/120-frame observation path, exactly one canonical Chinese final PASS/FAIL visual acceptance after machine PASS, followed by promptless identical post-clean and exact raw restore/readback/normal resume"
}
if ($continuousR10) {
$report.claim_scope = "one production-off r12_v22_calm_curious_warm_sampler source-bound OTP Mode2 candidate: promptless dual-plane White pre-clean, one full 5000-byte calm baseline activation with exactly one hardware reset low/high 10ms/10ms and 0xFF, then exactly 16 qualification transitions and an unbounded calm-curious-warm-curious-calm loop; every movement has reset=0, control=0xCF, exactly one ready-state check, a full 1908-byte current rewrite in fixed corridor x-bytes 4..21/y22..127, exactly one 0x22=0xCF/0x20/BUSY activation, BUSY <=600 ms, transaction <=460 ms, and real start-to-start cadence 1..480 ms; host UART evidence is a fixed 65536-byte ring; any BUSY, disconnect, prompt, storage, residue or emergency fault fails closed into promptless postclean and exact 524288-byte restore/readback/normal resume"
    $report.outputs.continuous_monitor_result = $continuousMonitorResult
    $report.outputs.continuous_qualification_ready = $continuousQualificationReady
    $report.outputs.continuous_stop_signal = $continuousStopSignal
}
if ($commandTargetR8) {
    $report.claim_scope = "one production-off R8 readback-only command-target discriminator: zero popup, promptless supplier-exact dual-plane all-White pre-clean with both selectors read twice, at most one local source-exact FF/20/BUSY known-swap activation, distinct non-activated 0x24 and 0x26 tags with selector0/1 duplicate readback and same-command restoration, zero post-tag activation, no human optical verdict, promptless dual-plane postclean, and exact raw restore/readback/normal resume"
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
$continuousMonitorProcess = $null
$continuousPromptProcess = $null
$normalCapture = $null
$hardwareImageAttempted = $false
$precleanAttempted = $false
$postcleanAttempted = $false
$candidateAttempted = $false
$candidateCancelled = $false
$controllerValid = $false
$r10VisualPassed = $false
$postcleanValid = $false
$restoreValid = $false
$normalValid = $false
$failureStage = "preflight"

try {
    $requiredInputs = @($backupA, $backupB, $candidateImage)
    if ($requiresDualPlaneLifecycle -or $dualPlaneWhiteRecoveryOnly) {
        $requiredInputs += @($precleanImage, $precleanSourceAudit, $precleanVerifier)
    }
    if ($phaseParallelR10) { $requiredInputs += $r10VisualPrompt }
    if ($continuousR10) { $requiredInputs += @($continuousMonitor, $continuousPromptSupervisor, $controllerVerifier) }
    foreach ($path in $requiredInputs) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required input is missing: $path" }
    }
    if ((Get-Hash $backupA) -ne $baselineSha256 -or (Get-Hash $backupB) -ne $baselineSha256) {
        throw "Captured raw baseline hash mismatch; refusing hardware contact."
    }
    if ((Get-Hash $candidateImage) -ne $candidateSha256) {
        throw "Locked candidate hash mismatch; refusing hardware contact."
    }
    if (($requiresDualPlaneLifecycle -or $whiteRecoveryOnly) -and (Get-Hash $precleanImage) -ne $precleanSha256) {
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
        $checkMonitorRoot = Join-Path $runRoot "checkonly-monitor"
        $checkSupervisorRoot = Join-Path $runRoot "checkonly-supervisor"
        New-Item -ItemType Directory -Force -Path $checkMonitorRoot, $checkSupervisorRoot | Out-Null
        $checkChildren = @()
        foreach ($check in @(
            [ordered]@{ name = "monitor"; script = $continuousMonitor; parameter = "-OutDir"; root = $checkMonitorRoot; evidence = "monitor-result.json" },
            [ordered]@{ name = "supervisor"; script = $continuousPromptSupervisor; parameter = "-OutRoot"; root = $checkSupervisorRoot; evidence = "prompt-supervisor-check.json" }
        )) {
            $childStdout = Join-Path $check.root "$($check.name).stdout.log"
            $childStderr = Join-Path $check.root "$($check.name).stderr.log"
            $child = Start-Process -FilePath "pwsh" -ArgumentList @("-NoProfile", "-File", $check.script, "-CheckOnly", $check.parameter, $check.root) -RedirectStandardOutput $childStdout -RedirectStandardError $childStderr -WindowStyle Hidden -PassThru
            if (-not $child.WaitForExit(30000)) { Stop-Process -Id $child.Id -Force; throw "R10 CheckOnly $($check.name) timed out." }
            $child.WaitForExit(); Start-Sleep -Milliseconds 100; $child.Refresh()
            $evidencePath = Join-Path $check.root $check.evidence
            if (-not (Test-Path $evidencePath) -or -not (Test-Path $childStdout) -or -not (Test-Path $childStderr)) { throw "R10 CheckOnly $($check.name) child evidence failed." }
            $evidence = Get-Content -LiteralPath $evidencePath -Raw | ConvertFrom-Json
            $evidencePass = if ($check.name -eq "monitor") {
                $evidence.status -eq "READY_NO_HARDWARE_CONTACT" -and $evidence.hardware_contact -eq 0 -and $evidence.write_counter_sum -eq 0 -and $evidence.popup_count -eq 0 -and $evidence.retry_count -eq 0
            } else {
                $evidence.status -eq "READY_NO_PROMPT" -and $evidence.hardware_contact -eq 0 -and
                    $evidence.write_counter_sum -eq 0 -and $evidence.programmer_calls -eq 0 -and
                    $evidence.serial_open_count -eq 0 -and $evidence.reset_count -eq 0 -and
                    $evidence.refresh_count -eq 0 -and $evidence.popup_count -eq 0 -and $evidence.retry_count -eq 0
            }
            if (-not $evidencePass) { throw "R10 CheckOnly $($check.name) child evidence failed closed." }
            $checkChildren += [ordered]@{ name = $check.name; exit_code = 0; observed_process_exit_code = [int]$child.ExitCode; exit_code_reconciled_by_complete_evidence = ([int]$child.ExitCode -ne 0); stdout = $childStdout; stderr = $childStderr; child_exited = $true; evidence_status = [string]$evidence.status }
        }
        $report.checkonly = [ordered]@{ children = $checkChildren; telemetry_ring_bytes = 65536; telemetry_ring_fixed = $true; popup_count = 0; retry_count = 0 }
        $report.status = "READY_NO_HARDWARE_CONTACT"
        $report.completed_at = (Get-Date).ToUniversalTime().ToString("o")
        Write-Report $report
        Write-Output "CHECK: R12 lifecycle, exact raw restore, and parser gates passed; hardware_contact=0; writes=0; popup=0; retry=0."
        exit 0
    }


    if ($continuousR10) {
        if ([string]::IsNullOrWhiteSpace($AuthorizationArtifact) -or
            -not (Test-Path -LiteralPath $AuthorizationArtifact -PathType Leaf)) {
            throw "R12 Execute requires a later root-issued authorization receipt; none is present."
        }
        $authorization = Get-Content -LiteralPath $AuthorizationArtifact -Raw | ConvertFrom-Json
        $lockedAuthorizationHashes = [ordered]@{
            candidate_hex_sha256 = $candidateSha256
            runner_sha256 = Get-Hash $PSCommandPath
            monitor_sha256 = Get-Hash $continuousMonitor
            supervisor_sha256 = Get-Hash $continuousPromptSupervisor
            launcher_sha256 = Get-Hash (Join-Path $PSScriptRoot "start_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r6.ps1")
            parser_sha256 = Get-Hash (Join-Path $PSScriptRoot "verify_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r6_log.py")
        }
        $machineReadyPath = Validate-MachineManifest ([string]$authorization.machine_ready_path) $lockedAuthorizationHashes
        $lockedAuthorizationHashes.machine_ready_path = $machineReadyPath
        $lockedAuthorizationHashes.machine_ready_sha256 = Get-Hash $machineReadyPath
        $authSource = [string]$authorization.source_authorization_path
        $authReceipt = [IO.Path]::GetFullPath($AuthorizationArtifact)
        $expectedClaimMarker = "$authSource.claim.json"
        $expectedSpentPath = "$authSource.spent"
        $expectedReceiptPath = "$authSource.consumed.json"
        $claimRecord = if (Test-Path -LiteralPath $expectedClaimMarker -PathType Leaf) { Get-Content -LiteralPath $expectedClaimMarker -Raw | ConvertFrom-Json } else { $null }
        $authMatches = $authorization.status -eq "CONSUMED_AUTHORIZED_R12_V22_CALM_CURIOUS_WARM_SAMPLER_ONCE" -and
            $authorization.consumed -eq $true -and
            [string]$authorization.candidate -eq "r12_v22_calm_curious_warm_sampler" -and
            [string]$authorization.authority_scope -eq "one_shot_physical_review" -and
            [string]$authorization.requirement_id -eq "COMP-REQ-404" -and
            [string]$authorization.output_root -eq [string]$runRoot -and
            $authReceipt -eq ([IO.Path]::GetFullPath($expectedReceiptPath)) -and
            [string]$authorization.claim_marker -eq [string]$expectedClaimMarker -and
            [string]$authorization.source_spent_path -eq [string]$expectedSpentPath -and
            (Test-Path -LiteralPath $expectedClaimMarker -PathType Leaf) -and
            (Test-Path -LiteralPath $expectedSpentPath -PathType Leaf) -and
            -not (Test-Path -LiteralPath $authSource -PathType Leaf) -and
            [string]$authorization.claim_id -eq [string](Get-Hash $expectedClaimMarker) -and
            [string]$authorization.source_authorization_sha256 -eq [string](Get-Hash $expectedSpentPath) -and
            $null -ne $claimRecord -and
            $claimRecord.status -eq "CLAIMED" -and
            [string]$claimRecord.source_authorization -eq [string]$authSource -and
            [string]$claimRecord.output_root -eq [string]$runRoot -and
            [string]$claimRecord.candidate -eq "r12_v22_calm_curious_warm_sampler" -and
            [string]$claimRecord.authority_scope -eq "one_shot_physical_review" -and
            [string]$claimRecord.requirement_id -eq [string]$authorization.requirement_id
        foreach ($name in $lockedAuthorizationHashes.Keys) {
            if ([string]$authorization.$name -ne [string]$lockedAuthorizationHashes[$name]) { $authMatches = $false }
        }
        if (-not $authMatches) {
            throw "R12 consumed authorization receipt is invalid, mismatched, reused, or already moved."
        }
        $report.authorization = [ordered]@{
            path = [System.IO.Path]::GetFullPath($AuthorizationArtifact)
            sha256 = Get-Hash $AuthorizationArtifact
            status = $authorization.status
            requirement_id = $authorization.requirement_id
            bound_hashes = $lockedAuthorizationHashes
        }
    }

    $failureStage = "lock"
    $companionLock = Enter-CompanionWb55Lock -Purpose $(if ($continuousR10) { "one R12 three-expression continuous observation after 16-transition qualification and exact raw restore" } elseif ($commandTargetR8) { "one R8 RAM command-target readback discriminator and exact raw restore" } elseif ($phaseParallelR10) { "one R10 16-activation phase-parallel local sequence and exact raw restore" } elseif ($observableR6) { "one R6 16-activation observable local sequence and exact raw restore" } elseif ($dualPlaneWhiteRecoveryOnly) { "one promptless dual-plane White cleanup and exact raw restore" } elseif ($dualPlaneCustomMode2) { "one R6 dual-plane-clean custom Mode2 A/B and exact raw restore" } elseif ($CustomMode2TransitionSafety) { "one custom Mode2 local transition safety run and exact raw restore" } elseif ($FastPointProbeInverseSeed) { "one inverse-seed fast point probe and exact raw restore" } elseif ($FastPointProbe) { "one fast point probe and exact raw restore" } elseif ($RamPingPongPointProbe) { "one RAM ping-pong point probe and exact raw restore" } elseif ($RamPingPongFingerprint) { "one RAM ping-pong fingerprint capture and exact raw restore" } elseif ($ResetReadControllerState) { "one hard-reset read-only controller capture and exact raw restore" } else { "one read-only controller capture and exact raw restore" })
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

    if ($requiresDualPlaneLifecycle -or $whiteRecoveryOnly) {
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

    if (-not $whiteRecoveryOnly) {
    if ($continuousR10) {
        $failureStage = "continuous_monitor_ready"
        New-Item -ItemType Directory -Force -Path $privateRoot, $continuousMonitorRoot | Out-Null
        if (Test-Path -LiteralPath $restoreVerify) { throw "Private restore upload already exists; refusing reuse." }
        $monitorArguments = @(
            "-NoProfile", "-File", $continuousMonitor, "-Execute",
            "-OutDir", $continuousMonitorRoot,
            "-ReadySignalPath", $continuousMonitorReady,
            "-QualificationSignalPath", $continuousQualificationReady,
            "-StopSignalPath", $continuousStopSignal,
            "-EmergencyStopPath", $continuousEmergencyStop,
            "-RingBytes", "65536"
        )
        if (-not [string]::IsNullOrWhiteSpace($Port)) { $monitorArguments += @("-Port", $Port) }
        $continuousMonitorProcess = Start-Process -FilePath "pwsh" -ArgumentList $monitorArguments `
            -RedirectStandardOutput (Join-Path $runRoot "continuous-monitor.stdout.log") `
            -RedirectStandardError (Join-Path $runRoot "continuous-monitor.stderr.log") `
            -WindowStyle Hidden -PassThru
        $report.counters.serial_capture_processes++
        $monitorReadyDeadline = [DateTime]::UtcNow.AddSeconds(20)
        while (-not (Test-Path -LiteralPath $continuousMonitorReady -PathType Leaf)) {
            if ($continuousMonitorProcess.HasExited) { throw "Continuous monitor exited before serial ready." }
            if ([DateTime]::UtcNow -ge $monitorReadyDeadline) { throw "Continuous monitor did not become serial-ready." }
            Start-Sleep -Milliseconds 100
        }

        $failureStage = "continuous_candidate"
        $hardwareImageAttempted = $true
        $candidateAttempted = $true
        $report.hardware_contact = 1
        $report.counters.candidate_programmer_processes = 1
        $report.counters.candidate_write_calls = 1
        $candidateArgs = @("-c", "port=SWD", "mode=UR", "reset=HWrst", "freq=4000",
                           "-w", $candidateImage, "-v", "-rst")
        Invoke-ProgrammerOnce -Programmer $programmer -Operation "continuous-candidate-write" -Arguments $candidateArgs

        $failureStage = "initial_16_qualification"
        $qualificationDeadline = [DateTime]::UtcNow.AddSeconds(60)
        while (-not (Test-Path -LiteralPath $continuousQualificationReady -PathType Leaf)) {
            if ($continuousMonitorProcess.HasExited) { throw "Continuous monitor failed before the initial 16-step qualification passed." }
            if ([DateTime]::UtcNow -ge $qualificationDeadline) { throw "Initial 16-step qualification signal timed out." }
            Start-Sleep -Milliseconds 100
        }
        $qualification = Get-Content -LiteralPath $continuousQualificationReady -Raw | ConvertFrom-Json
        if ($qualification.status -ne "PASS_R12_QUALIFICATION_READY") {
            throw "Initial 16-step qualification signal is not PASS."
        }
        Copy-Item -LiteralPath ([string]$qualification.parser_artifact) -Destination $controllerArtifact
        $report.controller_state = Get-Content -LiteralPath $controllerArtifact -Raw | ConvertFrom-Json
        if ($report.controller_state.status -ne "PASS_R12_V22_CALM_CURIOUS_WARM_SAMPLER_LOG" -or
            $report.controller_state.metadata_proof -ne $true -or
            [string]$report.controller_state.metadata.baseline.window -ne "0-24,0-199" -or
            [string]$report.controller_state.metadata.baseline.bytes -ne "5000" -or
            [string]$report.controller_state.metadata.baseline.resets -ne "1" -or
            [string]$report.controller_state.metadata.baseline.control -ne "0xFF" -or
            [string]$report.controller_state.metadata.movement.reset -ne "0" -or
            [string]$report.controller_state.metadata.movement.control -ne "0xCF" -or
            [string]$report.controller_state.metadata.start.corridor -ne "4-21,22-127" -or
            [string]$report.controller_state.metadata.start.corridor_bytes -ne "1908" -or
            $report.controller_state.qualification_frames -ne 16 -or
            $report.controller_state.qualification_cadence_measurements -lt 15 -or
            $report.controller_state.loop_records -lt 2 -or
            $report.controller_state.cadence_measurements -lt 1 -or
            $report.controller_state.max_start_delta_ms -lt 1 -or
            $report.controller_state.max_start_delta_ms -gt 480) {
            throw "Initial R12 qualification artifact is not a complete metadata-bound machine PASS."
        }
        $controllerValid = $true

        $failureStage = "concurrent_final_visual_acceptance"
        $report.operator_prompt.invoked = $true
        $promptArguments = @(
            "-NoProfile", "-File", $continuousPromptSupervisor, "-Execute",
            "-QualificationSignalPath", $continuousQualificationReady,
            "-MonitorResultPath", $continuousMonitorResult,
            "-StopSignalPath", $continuousStopSignal,
            "-EmergencyStopPath", $continuousEmergencyStop,
            "-OutRoot", $runRoot,
            "-TimeoutSeconds", "0"
        )
        $continuousPromptProcess = Start-Process -FilePath "pwsh" -ArgumentList $promptArguments `
            -RedirectStandardOutput (Join-Path $runRoot "prompt-supervisor.stdout.log") `
            -RedirectStandardError (Join-Path $runRoot "prompt-supervisor.stderr.log") `
            -WindowStyle Hidden -PassThru
        while (-not $continuousPromptProcess.HasExited) {
            Start-Sleep -Milliseconds 100
        }
        $continuousPromptProcess.WaitForExit()
        if ($continuousPromptProcess.ExitCode -ne 0) {
            throw "Concurrent acceptance supervisor failed closed with exit code $($continuousPromptProcess.ExitCode)."
        }
        if (-not $continuousMonitorProcess.WaitForExit(15000)) {
            throw "Continuous monitor did not stop immediately after the operator selection."
        }
        $continuousMonitorProcess.WaitForExit()
        if ($continuousMonitorProcess.ExitCode -ne 0) {
            throw "Continuous monitor ended with a safety fault."
        }
        if (-not (Test-Path -LiteralPath $continuousMonitorResult -PathType Leaf) -or
            -not (Test-Path -LiteralPath $operatorReviewArtifact -PathType Leaf)) {
            throw "Continuous monitor or operator review artifact is missing."
        }
        $monitorResult = Get-Content -LiteralPath $continuousMonitorResult -Raw | ConvertFrom-Json
        if ($monitorResult.status -ne "STOP_REQUESTED_AFTER_QUALIFICATION" -or
            $monitorResult.ring_final_bytes -gt 65536 -or
            -not (Test-Path -LiteralPath ([string]$monitorResult.final_loop_artifact) -PathType Leaf) -or
            $monitorResult.unbounded_log_created -ne $false) {
            throw "Continuous monitor did not prove a bounded, operator-stopped observation."
        }
        $report.continuous_monitor = $monitorResult
        $operatorReview = Get-Content -LiteralPath $operatorReviewArtifact -Raw | ConvertFrom-Json
        $report.operator_prompt.selected = [string]$operatorReview.selected
        $report.operator_prompt.note = [string]$operatorReview.note
        $r10VisualPassed = $operatorReview.status -eq "PASS_OWNER_R12_V22_CALM_CURIOUS_WARM_SAMPLER_VISUAL"
        $totalActivations = 1 + 16 + [int]$monitorResult.loop_records_seen
        $report.counters.panel_hard_resets = 1
        $report.counters.panel_busy_waits = $totalActivations
        $report.counters.panel_writes = $totalActivations
        $report.counters.panel_refresh_commands = $totalActivations
    } else {
    $failureStage = "candidate_serial_ready"
    New-Item -ItemType Directory -Force -Path $privateRoot | Out-Null
    if (Test-Path -LiteralPath $restoreVerify) { throw "Private restore upload already exists; refusing reuse." }
    $candidateCapture = Start-BoundedSerialCapture -Name "candidate-capture" `
        -OutDir $candidateCaptureRoot -ReadyPath $candidateReady -Seconds $(if ($FastPointProbeInverseSeed -or $FastPointProbe) { 80 } elseif ($commandTargetR8 -or $RamPingPongFingerprint) { 60 } elseif ($customMode2 -or $RamPingPongPointProbe) { 40 } else { $CandidateCaptureSeconds })
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
    $candidateWaitSeconds = if ($FastPointProbeInverseSeed -or $FastPointProbe) { 95 } elseif ($commandTargetR8 -or $RamPingPongFingerprint) { 75 } elseif ($customMode2 -or $RamPingPongPointProbe) { 55 } else { $CandidateCaptureSeconds + 15 }
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
    if ($commandTargetR8) {
        $report.counters.panel_hard_resets = 1
        $report.counters.panel_busy_waits = 3
        $report.counters.panel_writes = 5
        $report.counters.panel_refresh_commands = 1
    } elseif ($phaseParallelR10) {
        $observedTransitions = @($report.controller_state.observed.steps).Count
        $report.counters.panel_hard_resets = 1
        $report.counters.panel_busy_waits = $observedTransitions
        $report.counters.panel_writes = 3 * $observedTransitions
        $report.counters.panel_refresh_commands = $observedTransitions
    } elseif ($customMode2) {

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
    if ($phaseParallelR10) {
        $failureStage = "final_visual_acceptance"
        $report.operator_prompt.invoked = $true
        try {
            $promptOutput = & pwsh -NoProfile -File $r10VisualPrompt `
                -ControllerArtifact $controllerArtifact -OutRoot $runRoot `
                -TimeoutSeconds $HumanPromptTimeoutSeconds
            if ($LASTEXITCODE -ne 0) { throw "R10 final visual acceptance helper failed." }
            $operatorReview = ($promptOutput -join [Environment]::NewLine) | ConvertFrom-Json
            $report.operator_prompt.selected = [string]$operatorReview.selected
            $report.operator_prompt.note = [string]$operatorReview.note
            $r10VisualPassed = $operatorReview.status -eq "PASS_OWNER_R10_LOCAL_VISUAL"
        } catch {
            $report.operator_prompt.error = $_.Exception.Message
            $r10VisualPassed = $false
        }
    }
    }
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
    if (($continuousPromptProcess -and -not $continuousPromptProcess.HasExited) -or
        ($continuousMonitorProcess -and -not $continuousMonitorProcess.HasExited)) {
        if (-not (Test-Path -LiteralPath $continuousEmergencyStop -PathType Leaf)) {
            [ordered]@{
                reason = "runner_fail_closed_cleanup"
                generated_at = [DateTime]::UtcNow.ToString("o")
            } | ConvertTo-Json | Set-Content -LiteralPath $continuousEmergencyStop -Encoding UTF8
        }
        if ($continuousPromptProcess) { [void]$continuousPromptProcess.WaitForExit(3000) }
        if ($continuousMonitorProcess) { [void]$continuousMonitorProcess.WaitForExit(3000) }
        Stop-ProcessTree $continuousPromptProcess
        Stop-ProcessTree $continuousMonitorProcess
    }
    if ($hardwareImageAttempted) {
        if (($customMode2 -and $candidateAttempted) -or
            ($commandTargetR8 -and $precleanAttempted)) {
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
            $report.status = "NO_GO_RESTORE_OR_APPLICATION_FAILED_PROMPTLESS"
        } elseif ($requiresDualPlaneLifecycle -and $controllerValid -and -not $postcleanValid) {
            $report.status = $(if ($continuousR10) { "NO_GO_R12_V22_CALM_CURIOUS_WARM_SAMPLER_POSTCLEAN_FAILED_RESTORED" } elseif ($commandTargetR8) { "NO_GO_R8_POSTCLEAN_FAILED_RESTORED" } else { "NO_GO_CUSTOM_MODE2_POSTCLEAN_FAILED_RESTORED" })
        } elseif ($continuousR10 -and $controllerValid -and $r10VisualPassed) {
            $report.status = $passStatus

        } elseif ($continuousR10 -and $controllerValid) {
            $report.status = "NO_GO_R12_V22_CALM_CURIOUS_WARM_SAMPLER_VISUAL_NOT_PASSED_RESTORED"
        } elseif ($phaseParallelR10 -and $controllerValid -and $r10VisualPassed) {
            $report.status = $passStatus
        } elseif ($phaseParallelR10 -and $controllerValid) {
            $report.status = "NO_GO_R10_VISUAL_NOT_PASSED_RESTORED"
        } elseif ($controllerValid) {
            $report.status = $passStatus
        } elseif ($commandTargetR8 -and $candidateCancelled -and $precleanAttempted -and -not $candidateAttempted) {
            $report.status = "CANCELLED_R8_AFTER_DUAL_PLANE_PRECLEAN_POSTCLEAN_EXACT_RAW_RESTORED"
        } elseif ($dualPlaneCustomMode2 -and $candidateCancelled -and $precleanAttempted -and -not $candidateAttempted) {
            $report.status = "CANCELLED_R6_AFTER_DUAL_PLANE_PRECLEAN_EXACT_RAW_RESTORED"
        } elseif ($customMode2 -and $precleanAttempted -and -not $candidateAttempted) {
            $report.status = "NO_GO_CUSTOM_MODE2_PRECLEAN_RESTORED"
        } else {
        $report.status = $(if ($continuousR10) { "NO_GO_R12_V22_CALM_CURIOUS_WARM_SAMPLER_SAFETY_FAULT_RESTORED" } elseif ($commandTargetR8) { "NO_GO_R8_COMMAND_TARGET_MAPPING_RESTORED" } elseif ($customMode2) { "NO_GO_CUSTOM_MODE2_TRANSITION_SAFETY_RESTORED" } elseif ($FastPointProbeInverseSeed) { "NO_GO_SSD1681_FAST_POINT_PROBE_INVERSE_SEED_RESTORED" } elseif ($FastPointProbe) { "NO_GO_SSD1681_FAST_POINT_PROBE_RESTORED" } elseif ($RamPingPongPointProbe) { "NO_GO_RAM_PING_PONG_POINT_PROBE_RESTORED" } elseif ($RamPingPongFingerprint) { "NO_GO_RAM_MAPPING_RESTORED" } else { "NO_GO_CONTROLLER_READ_RESTORED" })
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
if ($report.status -eq "NO_GO_CONTROLLER_READ_RESTORED" -or $report.status -eq "NO_GO_RAM_MAPPING_RESTORED" -or $report.status -eq "NO_GO_R8_COMMAND_TARGET_MAPPING_RESTORED" -or $report.status -eq "NO_GO_R8_POSTCLEAN_FAILED_RESTORED" -or $report.status -eq "NO_GO_RAM_PING_PONG_POINT_PROBE_RESTORED" -or $report.status -eq "NO_GO_SSD1681_FAST_POINT_PROBE_RESTORED" -or $report.status -eq "NO_GO_SSD1681_FAST_POINT_PROBE_INVERSE_SEED_RESTORED" -or $report.status -eq "NO_GO_CUSTOM_MODE2_PRECLEAN_RESTORED" -or $report.status -eq "NO_GO_CUSTOM_MODE2_POSTCLEAN_FAILED_RESTORED" -or $report.status -eq "NO_GO_CUSTOM_MODE2_TRANSITION_SAFETY_RESTORED" -or $report.status -eq "NO_GO_R10_VISUAL_NOT_PASSED_RESTORED" -or $report.status -eq "NO_GO_R12_V22_CALM_CURIOUS_WARM_SAMPLER_VISUAL_NOT_PASSED_RESTORED" -or $report.status -eq "NO_GO_R12_V22_CALM_CURIOUS_WARM_SAMPLER_POSTCLEAN_FAILED_RESTORED" -or $report.status -eq "NO_GO_R12_V22_CALM_CURIOUS_WARM_SAMPLER_SAFETY_FAULT_RESTORED") {
    throw "Diagnostic machine gate failed; captured raw application bytes were restored exactly."
}
if ($report.status -eq "NO_GO_RESTORE_OR_APPLICATION_FAILED_PROMPTLESS") {
    throw "Restore or normal application recovery failed; promptless machine disposition recorded."
}
throw "Run completed $($report.status): $($report.error)"


