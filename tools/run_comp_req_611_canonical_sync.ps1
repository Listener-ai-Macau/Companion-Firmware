param(
    [switch]$CheckOnly,
    [switch]$Execute,
    [string]$MainReviewArtifact,
    [string]$Port,
    [string]$OutRoot,
    [string]$ProgrammerRoot = 'C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [Text.Encoding]::UTF8
if ($CheckOnly -eq $Execute) { throw 'Choose exactly one of -CheckOnly or -Execute.' }

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'companion_wb55_lock.ps1')
$machineReady = Join-Path $repoRoot 'docs\validation\comp-req-611-lower-sync\MACHINE_READY.json'
$staticVerifier = Join-Path $PSScriptRoot 'verify_comp_req_611_lower_sync.py'
$monitorScript = Join-Path $PSScriptRoot 'monitor_comp_req_611_canonical_sync.ps1'
$supervisorScript = Join-Path $PSScriptRoot 'supervise_comp_req_611_canonical_sync_prompt.ps1'
$logParser = Join-Path $PSScriptRoot 'verify_comp_req_611_canonical_sync_log.py'
$backupVerifier = Join-Path $PSScriptRoot 'verify_wb55_ur_application_backup.py'
$restoreVerifier = Join-Path $PSScriptRoot 'verify_wb55_raw_application_restore.py'
$normalVerifier = Join-Path $PSScriptRoot 'verify_wb55_normal_resume_after_ur_backup_log.py'
$whiteVerifier = Join-Path $PSScriptRoot 'verify_wb55_official_full_diagnostic_log.py'
$sourceAudit = Join-Path $repoRoot 'docs\validation\companion-gdey0154d67-t03-vendor-1s-source-audit-r2-20260721.json'
$buildDir = Join-Path $repoRoot 'cubeide\Companion_Nucleo_WB55RG_Bringup\build_comp_req_611_canonical_sync'
$candidateHex = Join-Path $buildDir 'Companion_Nucleo_WB55RG_Bringup.hex'
$cleanupHex = Join-Path $repoRoot 'cubeide\Companion_Nucleo_WB55RG_Bringup\build_official_full_diagnostic_white\Companion_Nucleo_WB55RG_OfficialFullDiagnostic_white.hex'
$backupRoot = Join-Path $repoRoot '.cache\validation\wb55-ur-dual-application-backup-execute-20260721-r1\private'
$backupA = Join-Path $backupRoot 'backup-a.bin'
$backupB = Join-Path $backupRoot 'backup-b.bin'
$baselineSha = '223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C'
$programmerSha = 'BD520005962377155515A2C9E8FEAB73F304A696AAE1698F3B7760672160FD5E'

function Get-Hash([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()
}
function Write-Json([string]$Path,[object]$Value) {
    $parent = Split-Path -Parent ([IO.Path]::GetFullPath($Path))
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    $tmp = "$Path.tmp"
    [IO.File]::WriteAllText($tmp,(($Value | ConvertTo-Json -Depth 20) + "`n"),[Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $tmp -Destination $Path -Force
}
function Stop-ProcessTree([System.Diagnostics.Process]$Process) {
    if (-not $Process) { return }
    $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$($Process.Id)" -ErrorAction SilentlyContinue)
    foreach ($child in $children) { Stop-ProcessTree (Get-Process -Id ([int]$child.ProcessId) -ErrorAction SilentlyContinue) }
    if (-not $Process.HasExited) { Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue }
}
function Find-Programmer {
    $matches = @(Get-ChildItem -LiteralPath $ProgrammerRoot -Recurse -Filter STM32_Programmer_CLI.exe -File -ErrorAction SilentlyContinue)
    $exact = @($matches | Where-Object { (Get-Hash $_.FullName) -eq $programmerSha })
    if ($exact.Count -ne 1) { throw 'Exactly one hash-bound STM32CubeProgrammer executable is required.' }
    return $exact[0].FullName
}
function Invoke-ProgrammerOnce([string]$Programmer,[string]$Operation,[string[]]$Arguments,[string]$RunRoot,[int]$TimeoutSeconds = 180) {
    $stdout = Join-Path $RunRoot "$Operation.stdout.log"
    $stderr = Join-Path $RunRoot "$Operation.stderr.log"
    $process = Start-Process -FilePath $Programmer -ArgumentList $Arguments -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue; throw "$Operation timed out; no retry is allowed." }
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) { throw "$Operation failed with exit code $($process.ExitCode); no retry is allowed." }
    return [ordered]@{operation=$Operation;arguments=$Arguments;stdout=$stdout;stderr=$stderr;exit_code=[int]$process.ExitCode}
}
function Start-Capture([string]$Name,[string]$CaptureRoot,[int]$Seconds,[string]$RunRoot) {
    New-Item -ItemType Directory -Force -Path $CaptureRoot | Out-Null
    $ready = Join-Path $CaptureRoot 'ready.json'
    $args = @('-NoProfile','-File',(Join-Path $PSScriptRoot 'capture_nucleo_serial.ps1'),'-Execute','-WorkflowLockHeld','-Seconds',"$Seconds",'-OutDir',$CaptureRoot,'-ReadySignalPath',$ready,'-ProgrammerRoot',$ProgrammerRoot)
    if ($Port) { $args += @('-Port',$Port) }
    $process = Start-Process -FilePath 'pwsh' -ArgumentList $args -RedirectStandardOutput (Join-Path $RunRoot "$Name.stdout.log") -RedirectStandardError (Join-Path $RunRoot "$Name.stderr.log") -WindowStyle Hidden -PassThru
    $deadline = [DateTime]::UtcNow.AddSeconds(20)
    while (-not (Test-Path -LiteralPath $ready -PathType Leaf)) {
        if ($process.HasExited) { throw "$Name serial capture exited before ready." }
        if ([DateTime]::UtcNow -ge $deadline) { throw "$Name serial capture did not become ready." }
        Start-Sleep -Milliseconds 100
    }
    return $process
}
function Wait-Child([System.Diagnostics.Process]$Process,[int]$Seconds,[string]$Name) {
    if (-not $Process.WaitForExit($Seconds * 1000)) { Stop-ProcessTree $Process; throw "$Name timed out." }
    $Process.WaitForExit()
    if ($Process.ExitCode -ne 0) { throw "$Name exited with code $($Process.ExitCode)." }
}
function Assert-File([string]$Path,[int64]$Length = -1,[string]$Hash = $null) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Required file is missing: $Path" }
    if ($Length -ge 0 -and (Get-Item -LiteralPath $Path).Length -ne $Length) { throw "Length mismatch: $Path" }
    if ($Hash -and (Get-Hash $Path) -ne $Hash) { throw "Hash mismatch: $Path" }
}

if ($CheckOnly) {
    & python $staticVerifier --refresh
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & python $logParser --self-test
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & python $backupVerifier --self-test
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & python $restoreVerifier --self-test
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & python $whiteVerifier --self-test
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $checkRoot = Join-Path $repoRoot '.cache\validation\comp-req-611-lower-sync\checkonly-execution'
    Remove-Item -LiteralPath $checkRoot -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force -Path $checkRoot | Out-Null
    $monitorRoot = Join-Path $checkRoot 'monitor'; $supervisorRoot = Join-Path $checkRoot 'supervisor'
    $monitor = Start-Process -FilePath 'pwsh' -ArgumentList @('-NoProfile','-File',$monitorScript,'-CheckOnly','-OutDir',$monitorRoot) -RedirectStandardOutput (Join-Path $checkRoot 'monitor.stdout.log') -RedirectStandardError (Join-Path $checkRoot 'monitor.stderr.log') -WindowStyle Hidden -PassThru
    Wait-Child $monitor 30 '611 monitor CheckOnly'
    $monitorEvidence = Get-Content -LiteralPath (Join-Path $monitorRoot 'monitor-result.json') -Raw | ConvertFrom-Json
    if ($monitorEvidence.status -ne 'READY_NO_HARDWARE_CONTACT' -or $monitorEvidence.hardware_contact -ne 0 -or $monitorEvidence.write_counter_sum -ne 0 -or $monitorEvidence.serial_open_count -ne 0) { throw '611 monitor CheckOnly was not zero-contact.' }
    $supervisor = Start-Process -FilePath 'pwsh' -ArgumentList @('-NoProfile','-File',$supervisorScript,'-CheckOnly','-OutRoot',$supervisorRoot) -RedirectStandardOutput (Join-Path $checkRoot 'supervisor.stdout.log') -RedirectStandardError (Join-Path $checkRoot 'supervisor.stderr.log') -WindowStyle Hidden -PassThru
    Wait-Child $supervisor 30 '611 supervisor CheckOnly'
    $supervisorEvidence = Get-Content -LiteralPath (Join-Path $supervisorRoot 'prompt-supervisor-check.json') -Raw | ConvertFrom-Json
    if ($supervisorEvidence.status -ne 'READY_NO_PROMPT' -or $supervisorEvidence.hardware_contact -ne 0 -or $supervisorEvidence.popup_count -ne 0 -or $supervisorEvidence.prompt_process_start_count -ne 0) { throw '611 supervisor CheckOnly was not zero-prompt.' }
    $manifest = Get-Content -LiteralPath $machineReady -Raw | ConvertFrom-Json
    if ($manifest.hardware_contact -ne 0 -or $manifest.execute_authorized -eq $true -or $manifest.checkonly.flash -ne 0 -or $manifest.checkonly.write -ne 0 -or $manifest.checkonly.reset -ne 0 -or $manifest.checkonly.popup -ne 0) { throw '611 MACHINE_READY safety counters are not zero.' }
    Write-Output "CHECKONLY_READY: $machineReady"
    Write-Output "CHECKONLY_EXECUTION_CHILDREN: $checkRoot"
    exit 0
}

if ([string]::IsNullOrWhiteSpace($MainReviewArtifact) -or -not (Test-Path -LiteralPath $MainReviewArtifact -PathType Leaf)) { throw 'Execute requires a main-review authorization artifact; no hardware action started.' }
if ([string]::IsNullOrWhiteSpace($OutRoot)) { throw 'Execute requires an explicit -OutRoot bound by the authorization artifact.' }
$runRoot = [IO.Path]::GetFullPath($OutRoot)
if (Test-Path -LiteralPath $runRoot) { throw 'Execute output root already exists; refusing authorization reuse.' }
$manifest = Get-Content -LiteralPath $machineReady -Raw | ConvertFrom-Json
$auth = Get-Content -LiteralPath $MainReviewArtifact -Raw | ConvertFrom-Json
$expectedLauncher = Get-Hash $PSCommandPath
$expectedHashes = [ordered]@{
    machine_ready_sha256 = Get-Hash $machineReady
    candidate_hex_sha256 = [string]$manifest.artifacts.hex_sha256
    cleanup_hex_sha256 = Get-Hash $cleanupHex
    launcher_sha256 = $expectedLauncher
    monitor_sha256 = Get-Hash $monitorScript
    supervisor_sha256 = Get-Hash $supervisorScript
    log_parser_sha256 = Get-Hash $logParser
}
foreach ($key in $expectedHashes.Keys) { if ([string]$auth.$key -ne [string]$expectedHashes[$key]) { throw "Authorization hash mismatch: $key" } }
if ([string]$auth.status -ne 'AUTHORIZED_ONCE' -or [string]$auth.requirement_id -ne 'COMP-REQ-616' -or [string]$auth.output_root -ne $runRoot -or $auth.execute -ne $true) { throw 'Authorization scope/status/output_root is invalid.' }
if (Test-Path -LiteralPath "$MainReviewArtifact.spent" -PathType Leaf) { throw 'Authorization artifact has already been spent.' }
Assert-File $candidateHex -1 $expectedHashes.candidate_hex_sha256
Assert-File $cleanupHex
Assert-File $backupA 524288 $baselineSha; Assert-File $backupB 524288 $baselineSha
Assert-File $sourceAudit
$programmer = Find-Programmer
New-Item -ItemType Directory -Force -Path $runRoot | Out-Null
$candidateMonitorRoot = Join-Path $runRoot 'candidate-monitor'; $cleanupRoot = Join-Path $runRoot 'cleanup-capture'; $normalRoot = Join-Path $runRoot 'normal-capture'
$candidateReady = Join-Path $candidateMonitorRoot 'monitor-ready.json'; $qualificationReady = Join-Path $candidateMonitorRoot 'qualification-ready.json'; $stopSignal = Join-Path $candidateMonitorRoot 'operator-stop.json'; $emergencyStop = Join-Path $candidateMonitorRoot 'emergency-stop.json'; $monitorResult = Join-Path $candidateMonitorRoot 'monitor-result.json'; $reviewPath = Join-Path $runRoot 'operator-review.json'; $reportPath = Join-Path $runRoot 'stage-run.json'; $cleanupArtifact = Join-Path $runRoot 'cleanup-white.json'; $restoreUpload = Join-Path $runRoot 'private\restore-verify.bin'; $restoreArtifact = Join-Path $runRoot 'restore-gate.json'; $normalArtifact = Join-Path $runRoot 'normal-resume.json'
$lock = $null; $monitor = $null; $supervisor = $null; $cleanupCapture = $null; $normalCapture = $null; $hardwareImageAttempted = $false; $cleanupAttempted = $false; $cleanupObserved = $false; $cleanupValid = $false; $restoreValid = $false; $normalValid = $false; $operatorStatus = $null; $failure = $null
$report = [ordered]@{schema='companion.comp_req_611.physical_stage_run.v1';status='NO_GO_UNSTARTED';hardware_contact=0;programmer_calls=@();prompt_count=0;cleanup_count=0;restore_count=0;normal_resume=$null;operator_review=$null;artifacts=[ordered]@{machine_ready=$machineReady;candidate_hex=$candidateHex;cleanup_hex=$cleanupHex;monitor=$monitorScript;supervisor=$supervisorScript;log_parser=$logParser;programmer=$programmer}}
try {
    $lock = Enter-CompanionWb55Lock -Purpose 'one COMP-REQ-611 browser/e-paper parity review with exact restore'
    $monitorArgs = @('-NoProfile','-File',$monitorScript,'-Execute','-OutDir',$candidateMonitorRoot,'-ReadySignalPath',$candidateReady,'-QualificationSignalPath',$qualificationReady,'-StopSignalPath',$stopSignal,'-EmergencyStopPath',$emergencyStop,'-RingBytes','65536')
    if ($Port) { $monitorArgs += @('-Port',$Port) }
    $monitor = Start-Process -FilePath 'pwsh' -ArgumentList $monitorArgs -RedirectStandardOutput (Join-Path $runRoot 'monitor.stdout.log') -RedirectStandardError (Join-Path $runRoot 'monitor.stderr.log') -WindowStyle Hidden -PassThru
    $deadline = [DateTime]::UtcNow.AddSeconds(20); while (-not (Test-Path -LiteralPath $candidateReady -PathType Leaf)) { if ($monitor.HasExited) { throw '611 monitor exited before ready.' }; if ([DateTime]::UtcNow -ge $deadline) { throw '611 monitor ready timeout.' }; Start-Sleep -Milliseconds 100 }
    $hardwareImageAttempted = $true; $report.hardware_contact = 1
    $report.programmer_calls += Invoke-ProgrammerOnce $programmer 'candidate-write' @('-c','port=SWD','mode=UR','reset=HWrst','freq=4000','-w',$candidateHex,'-v','-rst') $runRoot
    $deadline = [DateTime]::UtcNow.AddSeconds(90); while (-not (Test-Path -LiteralPath $qualificationReady -PathType Leaf)) { if ($monitor.HasExited) { throw '611 monitor exited before qualification.' }; if ([DateTime]::UtcNow -ge $deadline) { throw '611 first-cycle qualification timeout.' }; Start-Sleep -Milliseconds 100 }
    $qualification = Get-Content -LiteralPath $qualificationReady -Raw | ConvertFrom-Json
    if ($qualification.status -ne 'PASS_COMP_REQ_611_QUALIFICATION_READY' -or $qualification.qualification_frames -ne 50) { throw '611 qualification did not prove one complete cycle.' }
    $supervisorArgs = @('-NoProfile','-File',$supervisorScript,'-Execute','-QualificationSignalPath',$qualificationReady,'-MonitorResultPath',$monitorResult,'-StopSignalPath',$stopSignal,'-EmergencyStopPath',$emergencyStop,'-OutRoot',$runRoot,'-TimeoutSeconds','0')
    $supervisor = Start-Process -FilePath 'pwsh' -ArgumentList $supervisorArgs -RedirectStandardOutput (Join-Path $runRoot 'supervisor.stdout.log') -RedirectStandardError (Join-Path $runRoot 'supervisor.stderr.log') -WindowStyle Hidden -PassThru
    Wait-Child $supervisor 3600 '611 canonical operator prompt'
    $reviewPath = Join-Path $runRoot 'operator-review.json'; $review = Get-Content -LiteralPath $reviewPath -Raw | ConvertFrom-Json; $operatorStatus = [string]$review.status; $report.prompt_count = 1; $report.operator_review = $review
    if (-not (Test-Path -LiteralPath $stopSignal -PathType Leaf)) { throw 'Operator prompt completed without a stop signal.' }
    if (-not $monitor.WaitForExit(15000)) { Stop-ProcessTree $monitor; throw '611 monitor did not stop after operator selection.' }
    $monitor.WaitForExit(); if ($monitor.ExitCode -ne 0) { throw '611 monitor ended with a fault after operator selection.' }
    if (-not (Test-Path -LiteralPath $monitorResult -PathType Leaf)) { throw '611 monitor result is missing after cleanup.' }
    $monitorEvidence = Get-Content -LiteralPath $monitorResult -Raw | ConvertFrom-Json
    if ($monitorEvidence.status -ne 'STOP_REQUESTED_AFTER_CLEANUP' -or $monitorEvidence.cleanup_seen -ne $true -or -not (Test-Path -LiteralPath ([string]$monitorEvidence.qualification_artifact) -PathType Leaf)) { throw '611 monitor did not prove the single in-firmware cleanup.' }
    $cleanupObserved = $true; $cleanupValid = $true; $report.cleanup_count = 1; $report.cleanup = Get-Content -LiteralPath ([string]$monitorEvidence.qualification_artifact) -Raw | ConvertFrom-Json
} catch { $failure = $_.Exception.Message; $report.error = $failure; if ($supervisor -and -not $supervisor.HasExited) { Stop-ProcessTree $supervisor }; if ($monitor -and -not $monitor.HasExited -and -not (Test-Path $emergencyStop)) { Write-Json $emergencyStop ([ordered]@{schema='companion.comp_req_611.emergency_stop.v1';reason='launcher_failure';detail=$failure}); Stop-ProcessTree $monitor } }
finally {
    if ($hardwareImageAttempted) {
        try {
            if ($cleanupObserved) { throw 'SKIP_CLEANUP_FALLBACK' }
            $cleanupAttempted = $true; $cleanupCapture = Start-Capture 'cleanup-capture' $cleanupRoot 35 $runRoot
            $report.programmer_calls += Invoke-ProgrammerOnce $programmer 'single-fast-white-cleanup' @('-c','port=SWD','mode=UR','reset=HWrst','freq=4000','-w',$cleanupHex,'-v','-rst') $runRoot
            Wait-Child $cleanupCapture 50 'single-fast-white cleanup capture'
            $cleanupLog = Join-Path $cleanupRoot 'nucleo-serial-raw.log'
            & python $whiteVerifier --pattern white --log $cleanupLog --out $cleanupArtifact --source-audit $sourceAudit
            if ($LASTEXITCODE -ne 0) { throw 'single-fast-white cleanup parser rejected the serial trace.' }
            $cleanupValid = $true; $report.cleanup_count = 1; $report.cleanup = Get-Content -LiteralPath $cleanupArtifact -Raw | ConvertFrom-Json
        } catch { if ($_.Exception.Message -ne 'SKIP_CLEANUP_FALLBACK') { $report.cleanup_error = $_.Exception.Message } }
        try {
            $normalCapture = Start-Capture 'normal-capture' $normalRoot 30 $runRoot
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $restoreUpload) | Out-Null
            $report.programmer_calls += Invoke-ProgrammerOnce $programmer 'restore-write-verify-upload' @('-c','port=SWD','mode=UR','reset=HWrst','freq=4000','-w',$backupA,'0x08000000','-v',$backupA,'0x08000000','-u','0x08000000','0x80000',$restoreUpload,'-rst') $runRoot
            & python $restoreVerifier --backup-a $backupA --backup-b $backupB --restore-verify $restoreUpload --out $restoreArtifact
            if ($LASTEXITCODE -ne 0) { throw 'Exact raw restore upload did not match the captured application.' }
            $restoreValid = $true; $report.restore_count = 1; $report.restore = Get-Content -LiteralPath $restoreArtifact -Raw | ConvertFrom-Json
            Wait-Child $normalCapture 45 'normal resume capture'
            & python $normalVerifier --log (Join-Path $normalRoot 'nucleo-serial-raw.log') --out $normalArtifact
            if ($LASTEXITCODE -ne 0) { throw 'Normal application resume was not proven.' }
            $normalValid = $true; $report.normal_resume = Get-Content -LiteralPath $normalArtifact -Raw | ConvertFrom-Json
        } catch { $report.restore_error = $_.Exception.Message }
        if ($cleanupCapture) { Stop-ProcessTree $cleanupCapture }; if ($normalCapture) { Stop-ProcessTree $normalCapture }
    }
    if ($lock) { Exit-CompanionWb55Lock }
    $report.completed_at = [DateTime]::UtcNow.ToString('o')
    if ($failure -or -not $restoreValid -or -not $normalValid -or -not $cleanupValid) { $report.status = 'NO_GO_COMP_REQ_611_PHYSICAL_RUN_RESTORED' }
    elseif ($operatorStatus -eq 'PASS_OWNER_COMP_REQ_611_JOINT_PARITY') { $report.status = 'PASS_COMP_REQ_611_JOINT_PARITY_RECORDED' }
    else { $report.status = 'NO_GO_OWNER_COMP_REQ_611_JOINT_PARITY_RESTORED' }
    Write-Json $reportPath $report
    if ($hardwareImageAttempted) { Write-Json "$MainReviewArtifact.spent" ([ordered]@{schema='companion.comp_req_611.authorization_spent.v1';status='SPENT';authorization=$MainReviewArtifact;run_root=$runRoot;report=$reportPath;spent_at=$report.completed_at}) }
}
if ($report.status -like 'PASS_*') { $report | ConvertTo-Json -Depth 12; exit 0 }
throw "COMP-REQ-611 run completed $($report.status): $($report.error)"
