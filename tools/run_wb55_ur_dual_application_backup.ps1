param(
    [switch]$CheckOnly,
    [switch]$Execute,
    [switch]$WorkflowLockHeld,
    [ValidateRange(10, 30)]
    [int]$CaptureSeconds = 30,
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

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
. (Join-Path $PSScriptRoot "companion_wb55_lock.ps1")
$staticVerifier = Join-Path $PSScriptRoot "verify_wb55_ur_dual_application_backup_diagnostic.py"
$backupVerifier = Join-Path $PSScriptRoot "verify_wb55_ur_application_backup.py"
$resumeVerifier = Join-Path $PSScriptRoot "verify_wb55_normal_resume_after_ur_backup_log.py"
$captureRunner = Join-Path $PSScriptRoot "capture_nucleo_serial.ps1"
$programmerSha256 = "BD520005962377155515A2C9E8FEAB73F304A696AAE1698F3B7760672160FD5E"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runRoot = if ($OutRoot) { [System.IO.Path]::GetFullPath($OutRoot) } else {
    Join-Path $repoRoot ".cache\validation\wb55-ur-dual-application-backup-$stamp"
}
$privateRoot = Join-Path $runRoot "private"
$captureRoot = Join-Path $runRoot "capture"
$backupA = Join-Path $privateRoot "backup-a.bin"
$backupB = Join-Path $privateRoot "backup-b.bin"
$backupArtifact = Join-Path $runRoot "backup-gate.json"
$resumeArtifact = Join-Path $runRoot "normal-resume.json"
$rawLog = Join-Path $captureRoot "nucleo-serial-raw.log"
$serialReady = Join-Path $runRoot "serial-ready.json"
$lockArtifact = Join-Path $runRoot "swd-com-lock.json"
$operatorArtifact = Join-Path $runRoot "normal-resume-operator.json"
$programmerStdout = Join-Path $runRoot "programmer.stdout.log"
$programmerStderr = Join-Path $runRoot "programmer.stderr.log"
$reportPath = Join-Path $runRoot "stage-run.json"
New-Item -ItemType Directory -Force -Path $runRoot | Out-Null

function Get-Hash([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

function Write-Report([System.Collections.IDictionary]$Report) {
    $Report | ConvertTo-Json -Depth 15 | Set-Content -LiteralPath $reportPath -Encoding UTF8
}

function Find-Programmer {
    $matches = @(Get-ChildItem -LiteralPath $ProgrammerRoot -Recurse -Filter STM32_Programmer_CLI.exe | Sort-Object FullName -Descending)
    if ($matches.Count -eq 0) { throw "STM32_Programmer_CLI.exe not found under $ProgrammerRoot" }
    $exact = @($matches | Where-Object { (Get-Hash $_.FullName) -eq $programmerSha256 })
    if ($exact.Count -ne 1) { throw "Exactly one hash-bound STM32CubeProgrammer v2.22 executable is required." }
    return $exact[0].FullName
}

function Invoke-SoleProgrammerProcess {
    param(
        [Parameter(Mandatory = $true)][string]$Programmer,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [ValidateRange(30, 300)][int]$TimeoutSeconds = 180
    )
    $process = Start-Process -FilePath $Programmer -ArgumentList $Arguments `
        -RedirectStandardOutput $programmerStdout -RedirectStandardError $programmerStderr `
        -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        throw "The sole programmer process timed out; no retry or second connection is allowed."
    }
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) {
        throw "The sole programmer process failed with exit code $($process.ExitCode); no retry or second connection is allowed."
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

function Invoke-ResumeFailurePrompt([string]$Reason) {
    $aiw = Resolve-Aiw
    $null = & pwsh -NoProfile -File $aiw operator-prompt `
        -Title "Companion 应用恢复状态未证实" `
        -ProgressText "只读备份已保存，等待人工处理" `
        -ScopeText "本次仅报告 under-reset 双备份后正常应用启动证据不足；不会再次复位、连接、烧录或操作屏幕。" `
        -Message "两份应用区备份已经通过机器校验，但 30 秒内未能证明原有正常应用完整恢复。请保持开发板供电和连接，不要手动复位、拔线或烧录。原因：$Reason" `
        -ExpectedText "请选择已知悉，并在备注中记录当前供电、串口和屏幕状态；后续动作必须另行受控。" `
        -Input -ReviewStyle -Buttons "已知悉" -OutputPath $operatorArtifact `
        -TimeoutSeconds $HumanPromptTimeoutSeconds -Json
}

$report = [ordered]@{
    schema_id = "companion.wb55.ur_dual_application_backup_stage_run.v1"
    status = "PREFLIGHT"
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    mode = if ($CheckOnly) { "check_only" } else { "execute" }
    claim_scope = "one UR/HWrst connection, two read-only 512KiB application uploads, one reset, and bounded normal-resume evidence"
    hardware_contact = 0
    error = $null
    counters = [ordered]@{
        serial_capture_processes = 0
        programmer_connection_processes = 0
        under_reset_connections = 0
        upload_arguments = 0
        successful_backup_files = 0
        explicit_reset_arguments = 0
        application_write_commands = 0
        erase_commands = 0
        panel_commands = 0
        automatic_retries = 0
    }
    locks = [ordered]@{
        companion_wb55 = $null
        swd_com = [ordered]@{ mechanism = "Local\\Companion-WB55-SWD-COM-Exclusive-v1"; acquired = $false; evidence = $lockArtifact }
    }
    programmer = [ordered]@{
        executable = $null
        sha256 = $null
        arguments = @()
        stdout = $programmerStdout
        stderr = $programmerStderr
        st_link_serial = $null
        st_link_firmware = $null
        board = $null
        voltage_v = $null
        device_id = $null
        device_name = $null
        connect_mode = $null
        reset_mode = $null
    }
    backup = [ordered]@{
        valid = $false
        shared_sha256 = $null
        bytes_each = $null
        vector = $null
        programmed_content = $null
        raw_files_private = $true
    }
    normal_resume = $null
    operator_prompt = [ordered]@{ required = $false; invoked = $false; path = $operatorArtifact; error = $null }
    outputs = [ordered]@{
        backup_gate = $backupArtifact
        normal_resume = $resumeArtifact
        raw_serial = $rawLog
        report = $reportPath
    }
}

$programmer = $null
$companionLock = $null
$swdMutex = $null
$swdAcquired = $false
$captureProcess = $null
$backupValid = $false
$failureStage = "preflight"

try {
    $programmer = Find-Programmer
    $report.programmer.executable = $programmer
    $report.programmer.sha256 = Get-Hash $programmer
    & python $staticVerifier
    if ($LASTEXITCODE -ne 0) { throw "Static UR backup gate failed before hardware contact." }
    if ($CheckOnly) {
        $report.status = "READY_NO_HARDWARE_CONTACT"
        $report.completed_at = (Get-Date).ToUniversalTime().ToString("o")
        Write-Report $report
        Write-Output "CHECK: UR dual application backup gates passed; hardware_contact=0."
        exit 0
    }

    $failureStage = "lock"
    $companionLock = Enter-CompanionWb55Lock -Purpose "one UR dual read-only application backup"
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

    $failureStage = "serial_ready"
    New-Item -ItemType Directory -Force -Path $privateRoot, $captureRoot | Out-Null
    foreach ($path in @($backupA, $backupB)) {
        if (Test-Path -LiteralPath $path) { throw "Private backup output already exists; refusing reuse: $path" }
    }
    $captureArgs = @("-NoProfile", "-File", $captureRunner, "-Execute", "-WorkflowLockHeld",
                     "-Seconds", "$CaptureSeconds", "-OutDir", $captureRoot,
                     "-ReadySignalPath", $serialReady, "-ProgrammerRoot", $ProgrammerRoot)
    if (-not [string]::IsNullOrWhiteSpace($Port)) { $captureArgs += @("-Port", $Port) }
    $captureProcess = Start-Process -FilePath "pwsh" -ArgumentList $captureArgs `
        -RedirectStandardOutput (Join-Path $runRoot "capture.stdout.log") `
        -RedirectStandardError (Join-Path $runRoot "capture.stderr.log") `
        -WindowStyle Hidden -PassThru
    $report.counters.serial_capture_processes = 1
    $readyDeadline = [DateTime]::UtcNow.AddSeconds(20)
    while (-not (Test-Path -LiteralPath $serialReady -PathType Leaf)) {
        if ($captureProcess.HasExited) { throw "Serial capture exited before ready; programmer was not started." }
        if ([DateTime]::UtcNow -ge $readyDeadline) { throw "Serial capture did not become ready; programmer was not started." }
        Start-Sleep -Milliseconds 100
    }
    $report.hardware_contact = 1

    $failureStage = "programmer"
    $programmerArgs = @("-c", "port=SWD", "mode=UR", "reset=HWrst", "freq=4000",
                        "-u", "0x08000000", "0x80000", $backupA,
                        "-u", "0x08000000", "0x80000", $backupB, "-rst")
    $report.programmer.arguments = @($programmerArgs)
    $report.counters.programmer_connection_processes = 1
    $report.counters.under_reset_connections = 1
    $report.counters.upload_arguments = 2
    $report.counters.explicit_reset_arguments = 1
    Invoke-SoleProgrammerProcess -Programmer $programmer -Arguments $programmerArgs

    $failureStage = "backup_validation"
    & python $backupVerifier --backup-a $backupA --backup-b $backupB --out $backupArtifact
    if ($LASTEXITCODE -ne 0) { throw "Dual UR application backup validation failed." }
    $backupGate = Get-Content -LiteralPath $backupArtifact -Raw | ConvertFrom-Json
    $backupValid = $true
    $report.backup.valid = $true
    $report.backup.shared_sha256 = $backupGate.shared_sha256
    $report.backup.bytes_each = $backupGate.length_bytes
    $report.backup.vector = $backupGate.backup_a.vector
    $report.backup.programmed_content = $backupGate.backup_a.programmed_content
    $report.counters.successful_backup_files = 2

    $failureStage = "normal_resume"
    if (-not $captureProcess.WaitForExit(($CaptureSeconds + 10) * 1000)) {
        Stop-Process -Id $captureProcess.Id -Force -ErrorAction SilentlyContinue
        throw "Bounded normal serial capture timed out."
    }
    $captureProcess.WaitForExit()
    if ($captureProcess.ExitCode -ne 0) { throw "Bounded normal serial capture failed." }
    & python $resumeVerifier --log $rawLog --out $resumeArtifact
    if ($LASTEXITCODE -ne 0) { throw "Normal application resumption was not proven by the bounded serial log." }
    $report.normal_resume = Get-Content -LiteralPath $resumeArtifact -Raw | ConvertFrom-Json
    $report.status = "PASS_MACHINE_UR_DUAL_APPLICATION_BACKUP_NORMAL_RESUMED_ZERO_WRITES"
} catch {
    $reason = $_.Exception.Message
    $report.error = $reason
    if ($backupValid) {
        $report.status = "NEED_HUMAN_APPLICATION_RESUME_UNPROVEN"
        $report.operator_prompt.required = $true
        try {
            $report.operator_prompt.invoked = $true
            Invoke-ResumeFailurePrompt -Reason $reason
        } catch {
            $report.operator_prompt.error = $_.Exception.Message
        }
    } else {
        $report.status = "NO_GO_$($failureStage.ToUpperInvariant())_ZERO_WRITES"
    }
} finally {
    if ($captureProcess -and -not $captureProcess.HasExited) {
        Stop-Process -Id $captureProcess.Id -Force -ErrorAction SilentlyContinue
        $captureProcess.WaitForExit()
    }
    if (Test-Path -LiteralPath $programmerStdout -PathType Leaf) {
        $programmerText = Get-Content -LiteralPath $programmerStdout -Raw
        $patterns = [ordered]@{
            st_link_serial = "ST-LINK SN\s*:\s*(.+)"
            st_link_firmware = "ST-LINK FW\s*:\s*(.+)"
            board = "Board\s*:\s*(.+)"
            voltage_v = "Voltage\s*:\s*([0-9.]+)V"
            device_id = "Device ID\s*:\s*(.+)"
            device_name = "Device name\s*:\s*(.+)"
            connect_mode = "Connect mode\s*:\s*(.+)"
            reset_mode = "Reset mode\s*:\s*(.+)"
        }
        foreach ($name in $patterns.Keys) {
            $match = [regex]::Match($programmerText, $patterns[$name])
            if ($match.Success) {
                $value = $match.Groups[1].Value.Trim()
                $report.programmer[$name] = if ($name -eq "voltage_v") { [double]$value } else { $value }
            }
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

if ($report.status -eq "PASS_MACHINE_UR_DUAL_APPLICATION_BACKUP_NORMAL_RESUMED_ZERO_WRITES") {
    Write-Output $report.status
    exit 0
}
if ($report.status -eq "NEED_HUMAN_APPLICATION_RESUME_UNPROVEN") {
    throw "Valid backups were captured but normal application resumption is unproven; human assistance is required."
}
throw "Run completed $($report.status): $($report.error)"
