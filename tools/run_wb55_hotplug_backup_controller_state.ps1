param(
    [switch]$CheckOnly,
    [switch]$Execute,
    [switch]$WorkflowLockHeld,
    [ValidateRange(10, 60)]
    [int]$CaptureSeconds = 20,
    [ValidateRange(60, 1800)]
    [int]$RestoreFailurePromptTimeoutSeconds = 900,
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
$staticVerifier = Join-Path $PSScriptRoot "verify_wb55_hotplug_backup_controller_state_diagnostic.py"
$backupVerifier = Join-Path $PSScriptRoot "verify_wb55_hotplug_application_backup.py"
$logVerifier = Join-Path $PSScriptRoot "verify_wb55_ssd1681_read_only_controller_state_log.py"
$captureRunner = Join-Path $PSScriptRoot "capture_nucleo_serial.ps1"
$candidateImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_read_only_controller_state\Companion_Nucleo_WB55RG_Ssd1681ReadOnlyControllerState.hex"
$candidateSha256 = "52D79CB3BC55D9738EFA580B95D3930216C23FD8825356F7860B7C1718C0C6AD"
$programmerSha256 = "BD520005962377155515A2C9E8FEAB73F304A696AAE1698F3B7760672160FD5E"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runRoot = if ($OutRoot) { [System.IO.Path]::GetFullPath($OutRoot) } else {
    Join-Path $repoRoot ".cache\validation\wb55-hotplug-backup-controller-state-$stamp"
}
$privateRoot = Join-Path $runRoot "private"
$captureRoot = Join-Path $runRoot "capture"
$backupA = Join-Path $privateRoot "backup-a.bin"
$backupB = Join-Path $privateRoot "backup-b.bin"
$restoreVerify = Join-Path $privateRoot "restore-verify.bin"
$backupArtifact = Join-Path $runRoot "backup-gate.json"
$decodedArtifact = Join-Path $runRoot "controller-state.json"
$rawLog = Join-Path $captureRoot "nucleo-serial-raw.log"
$serialReady = Join-Path $runRoot "serial-ready.json"
$lockArtifact = Join-Path $runRoot "swd-com-lock.json"
$operatorArtifact = Join-Path $runRoot "restore-failure-operator.json"
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

function Invoke-ProgrammerOnce {
    param(
        [Parameter(Mandatory = $true)][string]$Programmer,
        [Parameter(Mandatory = $true)][string]$Operation,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [ValidateRange(30, 300)][int]$TimeoutSeconds = 120
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
        throw "$Operation timed out after $TimeoutSeconds seconds; no retry is allowed."
    }
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) {
        throw "$Operation failed with exit code $($process.ExitCode); no retry is allowed."
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
        -Title "Companion 固件恢复失败" `
        -ProgressText "恢复保护已停止" `
        -ScopeText "只报告本次 NUCLEO-WB55RG 应用区恢复失败；不会执行第二次写入，也不会触碰屏幕波形或上层资源。" `
        -Message "备份后的唯一恢复写入或回读比对失败。请保持开发板供电和连接，不要手动复位、拔线或再次烧录。原因：$Reason" `
        -ExpectedText "请选择已知悉，并在备注中记录当前连接状态；后续恢复必须另行受控处理。" `
        -Input -ReviewStyle -Buttons "已知悉" -OutputPath $operatorArtifact `
        -TimeoutSeconds $RestoreFailurePromptTimeoutSeconds -Json
}

$report = [ordered]@{
    schema_id = "companion.wb55.hotplug_backup_controller_state_stage_run.v1"
    status = "PREFLIGHT"
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    mode = if ($CheckOnly) { "check_only" } else { "execute" }
    claim_scope = "dual HOTPLUG 512KiB application-byte backup, one production-off controller-state capture, and restore to captured bytes only"
    hardware_contact = 0
    error = $null
    counters = [ordered]@{
        hotplug_backup_upload_calls = 0
        candidate_write_calls = 0
        restore_write_calls = 0
        post_restore_hotplug_upload_calls = 0
        display_write_commands = 0
        display_refresh_commands = 0
        display_hard_resets = 0
        automatic_retries = 0
    }
    images = [ordered]@{
        candidate = [ordered]@{ path = $candidateImage; sha256 = Get-Hash $candidateImage; required_sha256 = $candidateSha256 }
        backup_a = [ordered]@{ private_path = $backupA; bytes = $null; sha256 = $null }
        backup_b = [ordered]@{ private_path = $backupB; bytes = $null; sha256 = $null }
        restore_verify = [ordered]@{ private_path = $restoreVerify; bytes = $null; sha256 = $null }
    }
    locks = [ordered]@{
        companion_wb55 = $null
        swd_com = [ordered]@{ mechanism = "Local\\Companion-WB55-SWD-COM-Exclusive-v1"; acquired = $false; evidence = $lockArtifact }
    }
    programmer_calls = @()
    controller_state = $null
    restore_identity = $null
    operator_prompt = [ordered]@{ required = $false; invoked = $false; path = $operatorArtifact; error = $null }
    outputs = [ordered]@{
        backup_gate = $backupArtifact
        raw_log = $rawLog
        controller_state = $decodedArtifact
        report = $reportPath
    }
}

$programmer = $null
$companionLock = $null
$swdMutex = $null
$swdAcquired = $false
$captureProcess = $null
$candidateAttempted = $false
$restoreSucceeded = $false
$failure = $null
$failureStage = "preflight"

try {
    if (-not (Test-Path -LiteralPath $candidateImage -PathType Leaf) -or (Get-Hash $candidateImage) -ne $candidateSha256) {
        throw "Candidate image is missing or its SHA-256 is not the locked 52D79C... value."
    }
    $programmer = Find-Programmer
    & python $staticVerifier
    if ($LASTEXITCODE -ne 0) { throw "Static recovery/diagnostic gate failed before hardware contact." }
    if ($CheckOnly) {
        $report.status = "READY_NO_HARDWARE_CONTACT"
        $report.completed_at = (Get-Date).ToUniversalTime().ToString("o")
        Write-Report $report
        Write-Output "CHECK: all recovery and diagnostic gates passed; hardware_contact=0."
        exit 0
    }

    $failureStage = "lock"
    $companionLock = Enter-CompanionWb55Lock -Purpose "dual HOTPLUG backup, controller-state capture, one restore"
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

    $failureStage = "dual_backup"
    New-Item -ItemType Directory -Force -Path $privateRoot | Out-Null
    foreach ($path in @($backupA, $backupB, $restoreVerify)) {
        if (Test-Path -LiteralPath $path) { throw "Private output already exists; refusing reuse: $path" }
    }
    $report.hardware_contact = 1
    $backupArgsA = @("-c", "port=SWD", "mode=HOTPLUG", "-u", "0x08000000", "0x80000", $backupA)
    Invoke-ProgrammerOnce -Programmer $programmer -Operation "backup-a" -Arguments $backupArgsA
    $report.counters.hotplug_backup_upload_calls++
    $backupArgsB = @("-c", "port=SWD", "mode=HOTPLUG", "-u", "0x08000000", "0x80000", $backupB)
    Invoke-ProgrammerOnce -Programmer $programmer -Operation "backup-b" -Arguments $backupArgsB
    $report.counters.hotplug_backup_upload_calls++
    & python $backupVerifier --backup-a $backupA --backup-b $backupB --out $backupArtifact
    if ($LASTEXITCODE -ne 0) { throw "Dual HOTPLUG backup admission failed; zero writes were performed and no retry is allowed." }
    $backupGate = Get-Content -LiteralPath $backupArtifact -Raw | ConvertFrom-Json
    $report.images.backup_a.bytes = [int64](Get-Item -LiteralPath $backupA).Length
    $report.images.backup_a.sha256 = Get-Hash $backupA
    $report.images.backup_b.bytes = [int64](Get-Item -LiteralPath $backupB).Length
    $report.images.backup_b.sha256 = Get-Hash $backupB

    $failureStage = "serial_ready"
    New-Item -ItemType Directory -Force -Path $captureRoot | Out-Null
    $captureArgs = @("-NoProfile", "-File", $captureRunner, "-Execute", "-WorkflowLockHeld",
                     "-Seconds", "$CaptureSeconds", "-OutDir", $captureRoot,
                     "-ReadySignalPath", $serialReady, "-ProgrammerRoot", $ProgrammerRoot)
    if (-not [string]::IsNullOrWhiteSpace($Port)) { $captureArgs += @("-Port", $Port) }
    $captureProcess = Start-Process -FilePath "pwsh" -ArgumentList $captureArgs `
        -RedirectStandardOutput (Join-Path $runRoot "capture.stdout.log") `
        -RedirectStandardError (Join-Path $runRoot "capture.stderr.log") `
        -WindowStyle Hidden -PassThru
    $readyDeadline = [DateTime]::UtcNow.AddSeconds(20)
    while (-not (Test-Path -LiteralPath $serialReady -PathType Leaf)) {
        if ($captureProcess.HasExited) { throw "Serial capture exited before ready; candidate was not written." }
        if ([DateTime]::UtcNow -ge $readyDeadline) { throw "Serial capture did not become ready; candidate was not written." }
        Start-Sleep -Milliseconds 100
    }

    $failureStage = "candidate"
    $candidateAttempted = $true
    $report.counters.candidate_write_calls = 1
    $candidateArgs = @("-c", "port=SWD", "mode=UR", "reset=HWrst", "freq=4000",
                       "-w", $candidateImage, "-v", $candidateImage, "-rst")
    Invoke-ProgrammerOnce -Programmer $programmer -Operation "candidate-write" -Arguments $candidateArgs
    if (-not $captureProcess.WaitForExit(($CaptureSeconds + 15) * 1000)) {
        Stop-Process -Id $captureProcess.Id -Force -ErrorAction SilentlyContinue
        throw "Serial capture timed out after the sole candidate write."
    }
    $captureProcess.WaitForExit()
    if ($captureProcess.ExitCode -ne 0) { throw "Serial capture failed after the sole candidate write." }
    $failureStage = "controller_parser"
    & python $logVerifier --log $rawLog --out $decodedArtifact
    if ($LASTEXITCODE -ne 0) { throw "Controller-state parser gate failed; candidate will not be retried." }
    $report.controller_state = Get-Content -LiteralPath $decodedArtifact -Raw | ConvertFrom-Json
    $report.status = "PASS_MACHINE_READ_ONLY_CONTROLLER_STATE_PENDING_RESTORE"
} catch {
    $failure = $_.Exception.Message
    if (-not $candidateAttempted) {
        $report.status = "NO_GO_$($failureStage.ToUpperInvariant())_ZERO_WRITES"
    } else {
        $report.status = "NO_GO_$($failureStage.ToUpperInvariant())_PENDING_RESTORE"
    }
} finally {
    if ($captureProcess -and -not $captureProcess.HasExited) {
        Stop-Process -Id $captureProcess.Id -Force -ErrorAction SilentlyContinue
        $captureProcess.WaitForExit()
    }
    if ($candidateAttempted) {
        $failureStage = "restore"
        try {
            $report.counters.restore_write_calls = 1
            $restoreArgs = @("-c", "port=SWD", "mode=UR", "reset=HWrst", "freq=4000",
                             "-w", $backupA, "0x08000000", "-v", $backupA, "0x08000000", "-rst")
            Invoke-ProgrammerOnce -Programmer $programmer -Operation "restore-write" -Arguments $restoreArgs
            $report.counters.post_restore_hotplug_upload_calls = 1
            $restoreUploadArgs = @("-c", "port=SWD", "mode=HOTPLUG", "-u", "0x08000000", "0x80000", $restoreVerify)
            Invoke-ProgrammerOnce -Programmer $programmer -Operation "restore-verify-upload" -Arguments $restoreUploadArgs
            & python $backupVerifier --backup-a $backupA --backup-b $backupB --restore-verify $restoreVerify --out $backupArtifact
            if ($LASTEXITCODE -ne 0) { throw "Post-restore upload differs from the captured pre-run application bytes." }
            $report.images.restore_verify.bytes = [int64](Get-Item -LiteralPath $restoreVerify).Length
            $report.images.restore_verify.sha256 = Get-Hash $restoreVerify
            $report.restore_identity = "RESTORED_TO_CAPTURED_PRE_RUN_APPLICATION_BYTES"
            $restoreSucceeded = $true
            if ($report.status -eq "PASS_MACHINE_READ_ONLY_CONTROLLER_STATE_PENDING_RESTORE") {
                $report.status = "PASS_MACHINE_READ_ONLY_CONTROLLER_STATE_RESTORED"
            } else {
                $report.status = "$($report.status)_RESTORED"
            }
        } catch {
            $restoreReason = $_.Exception.Message
            $report.status = "NEED_HUMAN_RESTORE_FAILED"
            $report.operator_prompt.required = $true
            $report.error = $restoreReason
            try {
                $report.operator_prompt.invoked = $true
                Invoke-RestoreFailurePrompt -Reason $restoreReason
            } catch {
                $report.operator_prompt.error = $_.Exception.Message
            }
        }
    }
    if ($failure -and -not $report.error) { $report.error = $failure }
    if ($swdAcquired -and $swdMutex) {
        try {
            $lockEvidence = Get-Content -LiteralPath $lockArtifact -Raw | ConvertFrom-Json -AsHashtable
            $lockEvidence.status = "RELEASED"
            $lockEvidence.released_at = (Get-Date).ToUniversalTime().ToString("o")
            $lockEvidence | ConvertTo-Json | Set-Content -LiteralPath $lockArtifact -Encoding UTF8
        } finally {
            $swdMutex.ReleaseMutex()
            $swdMutex.Dispose()
        }
    }
    if ($companionLock) { Exit-CompanionWb55Lock }
    $report.completed_at = (Get-Date).ToUniversalTime().ToString("o")
    Write-Report $report
}

if ($report.status -eq "PASS_MACHINE_READ_ONLY_CONTROLLER_STATE_RESTORED") {
    Write-Output $report.status
    exit 0
}
if ($report.status -eq "NEED_HUMAN_RESTORE_FAILED") {
    throw "Restore failed after the sole write; human assistance is required and no second write was attempted."
}
throw "Run completed $($report.status): $($report.error)"
