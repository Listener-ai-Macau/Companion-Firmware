param(
    [Parameter(Mandatory = $true)][string]$RunRoot,
    [Parameter(Mandatory = $true)][string]$AuthorizationPath,
    [switch]$RecoverSpentAuthorization,
    [string]$Port = 'COM13',
    [string]$ProgrammerRoot = 'C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

. (Join-Path $PSScriptRoot 'companion_wb55_lock.ps1')

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runRoot = [IO.Path]::GetFullPath($RunRoot)
$authPath = [IO.Path]::GetFullPath($AuthorizationPath)
$cleanupHex = Join-Path $repoRoot 'cubeide\Companion_Nucleo_WB55RG_Bringup\build_official_full_diagnostic_white\Companion_Nucleo_WB55RG_OfficialFullDiagnostic_white.hex'
$backupRoot = Join-Path $repoRoot '.cache\validation\wb55-ur-dual-application-backup-execute-20260721-r1\private'
$backupA = Join-Path $backupRoot 'backup-a.bin'
$backupB = Join-Path $backupRoot 'backup-b.bin'
$whiteVerifier = Join-Path $PSScriptRoot 'verify_wb55_official_full_diagnostic_log.py'
$restoreVerifier = Join-Path $PSScriptRoot 'verify_wb55_raw_application_restore.py'
$normalVerifier = Join-Path $PSScriptRoot 'verify_wb55_normal_resume_after_ur_backup_log.py'
$machineReady = Join-Path $repoRoot 'docs\validation\comp-req-616-upper-sync\MACHINE_READY.json'
$programmerSha = 'BD520005962377155515A2C9E8FEAB73F304A696AAE1698F3B7760672160FD5E'
$baselineSha = '223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C'

function Hash([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant() }
function Write-JsonAtomic([string]$Path, [object]$Value) {
    $parent = Split-Path -Parent ([IO.Path]::GetFullPath($Path))
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $tmp = "$Path.tmp"
    [IO.File]::WriteAllText($tmp, (($Value | ConvertTo-Json -Depth 30) + "`n"), [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $tmp -Destination $Path -Force
}
function Stop-ProcessTree([System.Diagnostics.Process]$Process) {
    if (-not $Process) { return }
    $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$($Process.Id)" -ErrorAction SilentlyContinue)
    foreach ($child in $children) { Stop-ProcessTree (Get-Process -Id ([int]$child.ProcessId) -ErrorAction SilentlyContinue) }
    if (-not $Process.HasExited) { Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue }
}
function Find-Programmer {
    $matches = @(Get-ChildItem -LiteralPath $ProgrammerRoot -Recurse -Filter STM32_Programmer_CLI.exe -File -ErrorAction SilentlyContinue | Where-Object { (Hash $_.FullName) -eq $programmerSha })
    if ($matches.Count -ne 1) { throw 'Exactly one hash-bound STM32CubeProgrammer executable is required.' }
    return $matches[0].FullName
}
function Start-Capture([string]$Name, [string]$CaptureRoot, [int]$Seconds) {
    New-Item -ItemType Directory -Force -Path $CaptureRoot | Out-Null
    $ready = Join-Path $CaptureRoot 'ready.json'
    $args = @('-NoProfile','-File',(Join-Path $PSScriptRoot 'capture_nucleo_serial.ps1'),'-Execute','-WorkflowLockHeld','-Seconds',"$Seconds",'-OutDir',$CaptureRoot,'-ReadySignalPath',$ready,'-Port',$Port,'-ProgrammerRoot',$ProgrammerRoot)
    $process = Start-Process -FilePath 'pwsh' -ArgumentList $args -RedirectStandardOutput (Join-Path $runRoot "$Name.stdout.log") -RedirectStandardError (Join-Path $runRoot "$Name.stderr.log") -WindowStyle Hidden -PassThru
    $deadline = [DateTime]::UtcNow.AddSeconds(20)
    while (-not (Test-Path -LiteralPath $ready -PathType Leaf)) {
        if ($process.HasExited) { throw "$Name serial capture exited before ready." }
        if ([DateTime]::UtcNow -ge $deadline) { throw "$Name serial capture did not become ready." }
        Start-Sleep -Milliseconds 100
    }
    return $process
}
function Wait-Capture([System.Diagnostics.Process]$Process, [int]$Seconds, [string]$Name) {
    if (-not $Process.WaitForExit($Seconds * 1000)) { Stop-ProcessTree $Process; throw "$Name timed out." }
    $Process.WaitForExit()
    if ($Process.ExitCode -ne 0) { throw "$Name exited with code $($Process.ExitCode)." }
}
function Invoke-Programmer([string]$Programmer, [string]$Name, [string[]]$Arguments) {
    $stdout = Join-Path $runRoot "$Name.stdout.log"
    $stderr = Join-Path $runRoot "$Name.stderr.log"
    $p = Start-Process -FilePath $Programmer -ArgumentList $Arguments -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WindowStyle Hidden -PassThru
    if (-not $p.WaitForExit(180000)) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; throw "$Name timed out; no retry." }
    $p.WaitForExit()
    if ($p.ExitCode -ne 0) { throw "$Name failed with exit code $($p.ExitCode); no retry." }
    return [ordered]@{ operation = $Name; stdout = $stdout; stderr = $stderr; exit_code = [int]$p.ExitCode }
}

if (-not (Test-Path -LiteralPath $authPath -PathType Leaf)) { throw 'authorization artifact is missing' }
if (-not (Test-Path -LiteralPath (Join-Path $runRoot 'candidate-monitor\qualification-ready.json') -PathType Leaf)) { throw 'candidate qualification evidence is missing' }
$auth = Get-Content -LiteralPath $authPath -Raw | ConvertFrom-Json
if ($auth.status -ne 'AUTHORIZED_ONCE' -or $auth.requirement_id -ne 'COMP-REQ-616') { throw 'authorization is not the fresh COMP-REQ-616 authorization' }
$spentAuthorization = Test-Path -LiteralPath "$authPath.spent" -PathType Leaf
if ($spentAuthorization -and -not $RecoverSpentAuthorization) { throw 'authorization artifact is already spent' }
if (-not $spentAuthorization -and (Hash $machineReady) -ne [string]$auth.machine_ready_sha256) { throw 'MACHINE_READY hash drifted' }
if (-not $spentAuthorization -and (Hash $cleanupHex) -ne [string]$auth.cleanup_hex_sha256) { throw 'cleanup HEX hash drifted' }
if ((Get-Item -LiteralPath $backupA).Length -ne 524288 -or (Hash $backupA) -ne $baselineSha) { throw 'backup-a is not the exact baseline capture' }
if ((Get-Item -LiteralPath $backupB).Length -ne 524288 -or (Hash $backupB) -ne $baselineSha) { throw 'backup-b is not the exact baseline capture' }

$programmer = Find-Programmer
$cleanupRoot = Join-Path $runRoot 'cleanup-capture'
$normalRoot = Join-Path $runRoot 'normal-capture'
$cleanupArtifact = Join-Path $runRoot 'cleanup-white.json'
$restoreUpload = Join-Path $runRoot 'private\restore-verify.bin'
$restoreArtifact = Join-Path $runRoot 'restore-gate.json'
$normalArtifact = Join-Path $runRoot 'normal-resume.json'
$lock = $null
$cleanupCapture = $null
$normalCapture = $null
$calls = @()
$cleanupEvidence = $null
$restoreEvidence = $null
$normalEvidence = $null
$errorText = $null

try {
    $lock = Enter-CompanionWb55Lock -Purpose 'recover interrupted COMP-REQ-616 run; cleanup and exact restore only'

    $cleanupCapture = Start-Capture 'cleanup-capture' $cleanupRoot 35
    $calls += Invoke-Programmer $programmer 'single-fast-white-cleanup' @('-c','port=SWD','mode=UR','reset=HWrst','freq=4000','-w',$cleanupHex,'-v','-rst')
    Wait-Capture $cleanupCapture 50 'single-fast-white cleanup capture'
    & python $whiteVerifier --pattern white --log (Join-Path $cleanupRoot 'nucleo-serial-raw.log') --out $cleanupArtifact --without-source-audit
    $whiteExit = $LASTEXITCODE
    if ($whiteExit -ne 0) { throw 'cleanup serial parser rejected the trace' }
    $cleanupEvidence = Get-Content -LiteralPath $cleanupArtifact -Raw | ConvertFrom-Json

    $normalCapture = Start-Capture 'normal-capture' $normalRoot 30
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $restoreUpload) | Out-Null
    $calls += Invoke-Programmer $programmer 'restore-write-verify-upload' @('-c','port=SWD','mode=UR','reset=HWrst','freq=4000','-w',$backupA,'0x08000000','-v',$backupA,'0x08000000','-u','0x08000000','0x80000',$restoreUpload,'-rst')
    & python $restoreVerifier --backup-a $backupA --backup-b $backupB --restore-verify $restoreUpload --out $restoreArtifact
    $restoreExit = $LASTEXITCODE
    if ($restoreExit -ne 0) { throw 'exact raw restore verifier rejected the upload' }
    $restoreEvidence = Get-Content -LiteralPath $restoreArtifact -Raw | ConvertFrom-Json
    Wait-Capture $normalCapture 45 'normal resume capture'
    & python $normalVerifier --log (Join-Path $normalRoot 'nucleo-serial-raw.log') --out $normalArtifact
    $normalExit = $LASTEXITCODE
    if ($normalExit -eq 0) { $normalEvidence = Get-Content -LiteralPath $normalArtifact -Raw | ConvertFrom-Json }
    else { $normalEvidence = [ordered]@{ status = 'NO_GO_NORMAL_RESUME_NOT_PROVEN'; source_log = (Join-Path $normalRoot 'nucleo-serial-raw.log') } }
} catch {
    $errorText = $_.Exception.Message
} finally {
    if ($cleanupCapture) { Stop-ProcessTree $cleanupCapture }
    if ($normalCapture) { Stop-ProcessTree $normalCapture }
    if ($lock) { Exit-CompanionWb55Lock }
}

$monitorPath = Join-Path $runRoot 'candidate-monitor\monitor-result.json'
$qualification = Get-Content -LiteralPath (Join-Path $runRoot 'candidate-monitor\qualification-ready.json') -Raw | ConvertFrom-Json
$monitorEvidence = [ordered]@{
    schema = 'companion.comp_req_616.monitor_result.v1'
    status = 'NO_GO_INTERRUPTED_AFTER_QUALIFICATION'
    hardware_contact = 1
    qualification_completed = $true
    qualification_frames_seen = [int]$qualification.qualification_frames
    cleanup_seen = $false
    prompt_opened = (Test-Path -LiteralPath (Join-Path $runRoot 'acceptance-prompt-invoked.json') -PathType Leaf)
    reason = 'outer launcher terminated after candidate qualification and before the owner prompt; recovery performed without candidate retry'
    completed_at = [DateTime]::UtcNow.ToString('o')
}
Write-JsonAtomic $monitorPath $monitorEvidence

$report = [ordered]@{
    schema = 'companion.comp_req_616.physical_stage_run.v1'
    status = 'NO_GO_COMP_REQ_616_PHYSICAL_RUN_RESTORED'
    hardware_contact = 1
    programmer_calls = $calls
    prompt_count = 0
    cleanup_count = if ($cleanupEvidence) { 1 } else { 0 }
    restore_count = if ($restoreEvidence) { 1 } else { 0 }
    qualification = $qualification
    cleanup = $cleanupEvidence
    restore = $restoreEvidence
    normal_resume = $normalEvidence
    error = $errorText
    recovery = 'interrupted-after-qualification; cleanup and exact restore only; no candidate retry'
    completed_at = [DateTime]::UtcNow.ToString('o')
    artifacts = [ordered]@{ authorization = $authPath; monitor = $monitorPath; cleanup = $cleanupArtifact; restore = $restoreArtifact; normal_resume = $normalArtifact }
}
Write-JsonAtomic (Join-Path $runRoot 'stage-run.json') $report
Write-JsonAtomic "$authPath.spent" ([ordered]@{
    schema = 'companion.comp_req_616.authorization_spent.v1'
    status = 'SPENT'
    authorization = $authPath
    run_root = $runRoot
    report = (Join-Path $runRoot 'stage-run.json')
    reason = 'candidate was already flashed; interrupted after qualification; cleanup and exact restore completed or attempted; no retry'
    spent_at = $report.completed_at
})
$report | ConvertTo-Json -Depth 30
if ($errorText -or -not $restoreEvidence) { exit 1 }
