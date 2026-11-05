param(
    [switch]$CheckOnly,
    [switch]$Execute,
    [string]$OutRoot,
    [string]$Port,
    [ValidateRange(10, 60)][int]$CaptureSeconds = 30,
    [string]$ProgrammerRoot = "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
if ($CheckOnly -eq $Execute) { throw "Choose exactly one of -CheckOnly or -Execute." }

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
. (Join-Path $PSScriptRoot "companion_wb55_lock.ps1")
$baselineRoot = Join-Path $repoRoot ".cache\validation\wb55-ur-dual-application-backup-execute-20260721-r1\private"
$backupA = Join-Path $baselineRoot "backup-a.bin"
$backupB = Join-Path $baselineRoot "backup-b.bin"
$expectedSha = "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C"
$programmerSha = "BD520005962377155515A2C9E8FEAB73F304A696AAE1698F3B7760672160FD5E"
$captureRunner = Join-Path $PSScriptRoot "capture_nucleo_serial.ps1"
$restoreVerifier = Join-Path $PSScriptRoot "verify_wb55_raw_application_restore.py"
$normalVerifier = Join-Path $PSScriptRoot "verify_wb55_normal_resume_after_ur_backup_log.py"
$runRoot = if ($OutRoot) { [IO.Path]::GetFullPath($OutRoot) } else { Join-Path $repoRoot ".cache\validation\wb55-exact-raw-readback-resume" }
$privateRoot = Join-Path $runRoot "private"
$captureRoot = Join-Path $runRoot "normal-capture"
$readyPath = Join-Path $runRoot "normal-serial-ready.json"
$rawLog = Join-Path $captureRoot "nucleo-serial-raw.log"
$upload = Join-Path $privateRoot "application-readback.bin"
$restoreArtifact = Join-Path $runRoot "readback-gate.json"
$normalArtifact = Join-Path $runRoot "normal-resume.json"
$reportPath = Join-Path $runRoot "stage-run.json"
New-Item -ItemType Directory -Force -Path $privateRoot | Out-Null

function Hash([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

$programmers = @(Get-ChildItem -LiteralPath $ProgrammerRoot -Recurse -Filter STM32_Programmer_CLI.exe |
    Where-Object { (Hash $_.FullName) -eq $programmerSha })
if ($programmers.Count -ne 1) { throw "Exactly one hash-bound STM32CubeProgrammer v2.22 is required." }
$programmer = $programmers[0].FullName
foreach ($path in @($backupA, $backupB, $captureRunner, $restoreVerifier, $normalVerifier)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing input: $path" }
}
if ((Hash $backupA) -ne $expectedSha -or (Hash $backupB) -ne $expectedSha) {
    throw "Captured raw baselines differ from the locked application hash."
}
$report = [ordered]@{
    schema_id = "companion.wb55.exact_raw_readback_resume.v1"
    status = if ($CheckOnly) { "READY_NO_HARDWARE_CONTACT" } else { "RUNNING" }
    hardware_contact = 0
    write_calls = 0
    upload_calls = 0
    reset_arguments = 0
    expected_bytes = 524288
    expected_sha256 = $expectedSha
    readback = $null
    normal_resume = $null
}
if ($CheckOnly) {
    $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8
    Write-Output $report.status
    exit 0
}

$companionLock = $null
$mutex = $null
$acquired = $false
$capture = $null
try {
    if (Test-Path -LiteralPath $upload) { throw "Refusing to reuse an existing readback file." }
    $companionLock = Enter-CompanionWb55Lock -Purpose "exact raw application readback and normal resume proof"
    $mutex = [Threading.Mutex]::new($false, "Local\Companion-WB55-SWD-COM-Exclusive-v1")
    try { $acquired = $mutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $acquired = $true }
    if (-not $acquired) { throw "SWD/COM lock is already held." }

    New-Item -ItemType Directory -Force -Path $captureRoot | Out-Null
    $captureArgs = @("-NoProfile", "-File", $captureRunner, "-Execute", "-WorkflowLockHeld",
        "-Seconds", "$CaptureSeconds", "-OutDir", $captureRoot, "-ReadySignalPath", $readyPath,
        "-ProgrammerRoot", $ProgrammerRoot)
    if ($Port) { $captureArgs += @("-Port", $Port) }
    $capture = Start-Process pwsh -ArgumentList $captureArgs -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $runRoot "capture.stdout.log") `
        -RedirectStandardError (Join-Path $runRoot "capture.stderr.log")
    $deadline = [DateTime]::UtcNow.AddSeconds(20)
    while (-not (Test-Path -LiteralPath $readyPath -PathType Leaf)) {
        if ($capture.HasExited) { throw "Serial capture exited before ready." }
        if ([DateTime]::UtcNow -ge $deadline) { throw "Serial capture did not become ready." }
        Start-Sleep -Milliseconds 100
    }

    $stdout = Join-Path $runRoot "readback.stdout.log"
    $stderr = Join-Path $runRoot "readback.stderr.log"
    $args = @("-c", "port=SWD", "mode=UR", "reset=HWrst", "freq=4000",
        "-u", "0x08000000", "0x80000", $upload, "-rst")
    $process = Start-Process $programmer -ArgumentList $args -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if (-not $process.WaitForExit(180000)) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        throw "Readback timed out; no retry is allowed."
    }
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) { throw "Readback failed; no retry is allowed." }
    $report.hardware_contact = 1
    $report.upload_calls = 1
    $report.reset_arguments = 1

    & python $restoreVerifier --backup-a $backupA --backup-b $backupB --restore-verify $upload --out $restoreArtifact
    if ($LASTEXITCODE -ne 0) { throw "Readback differs from captured pre-run application bytes." }
    $report.readback = Get-Content -LiteralPath $restoreArtifact -Raw | ConvertFrom-Json
    if (-not $capture.WaitForExit(($CaptureSeconds + 10) * 1000)) {
        Stop-Process -Id $capture.Id -Force -ErrorAction SilentlyContinue
        throw "Normal capture timed out."
    }
    $capture.WaitForExit()
    if ($capture.ExitCode -ne 0) { throw "Normal capture failed." }
    & python $normalVerifier --log $rawLog --out $normalArtifact
    if ($LASTEXITCODE -ne 0) { throw "Normal application resume was not proven." }
    $report.normal_resume = Get-Content -LiteralPath $normalArtifact -Raw | ConvertFrom-Json
    $report.status = "PASS_EXACT_RAW_APPLICATION_READBACK_AND_NORMAL_RESUME"
} finally {
    if ($capture -and -not $capture.HasExited) { Stop-Process -Id $capture.Id -Force -ErrorAction SilentlyContinue }
    if ($acquired -and $mutex) { $mutex.ReleaseMutex(); $mutex.Dispose() }
    if ($companionLock) { Exit-CompanionWb55Lock }
    $report.completed_at = (Get-Date).ToUniversalTime().ToString("o")
    $report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $reportPath -Encoding UTF8
}
Write-Output $report.status
