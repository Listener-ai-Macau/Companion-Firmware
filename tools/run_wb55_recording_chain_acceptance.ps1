param(
    [switch] $Execute,
    [switch] $WorkflowLockHeld,
    [ValidateRange(45, 120)]
    [int] $CaptureSeconds = 65,
    [ValidateRange(18, 35)]
    [int] $LowPowerSettleSeconds = 24,
    [ValidateRange(20, 120)]
    [int] $OperatorTimeoutSeconds = 60,
    [string] $Port = "COM13",
    [string] $OutDir = ".cache\validation\shared-recording-chain-acceptance"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$workflowRoot = if ($env:AI_WORKFLOW_REPO) {
    $env:AI_WORKFLOW_REPO
} else {
    "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow"
}
$aiw = Join-Path $workflowRoot "scripts\aiw.ps1"
$traceImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_verbose_trace\Companion_Nucleo_WB55RG_VerboseTrace.hex"
$flashScript = Join-Path $repoRoot "tools\flash_nucleo_bringup.ps1"
$captureScript = Join-Path $repoRoot "tools\capture_nucleo_serial.ps1"
$verifier = Join-Path $repoRoot "tools\verify_wb55_touch_wake_log.py"
$resolvedOutDir = if ([System.IO.Path]::IsPathRooted($OutDir)) {
    $OutDir
} else {
    Join-Path $repoRoot $OutDir
}
$rawLogPath = Join-Path $resolvedOutDir "nucleo-serial-raw.log"
$summaryPath = Join-Path $resolvedOutDir "nucleo-serial-summary.json"
$operatorResultPath = Join-Path $resolvedOutDir "operator-result.txt"
$verificationPath = Join-Path $resolvedOutDir "double-tap-recording-verification.json"
$reportPath = Join-Path $resolvedOutDir "recording-chain-acceptance-report.json"

if (-not $Execute) {
    throw "Refusing recording acceptance without -Execute. Run through aiw with-lock."
}
if (-not $WorkflowLockHeld) {
    throw "Refusing recording acceptance without workflow lock acknowledgement."
}
foreach ($required in @($aiw, $traceImage, $flashScript, $captureScript, $verifier)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing recording acceptance dependency: $required"
    }
}

New-Item -ItemType Directory -Force -Path $resolvedOutDir | Out-Null
$report = [ordered]@{
    schema = "companion.wb55_recording_chain_acceptance.v1"
    status = "RUNNING"
    generated_at = (Get-Date).ToString("o")
    target = "NUCLEO-WB55RG + FT6336U + SPH0655-compatible PDM"
    trace_image = [System.IO.Path]::GetRelativePath($repoRoot, $traceImage).Replace("\", "/")
    capture_seconds = $CaptureSeconds
    low_power_settle_seconds = $LowPowerSettleSeconds
    operator_timeout_seconds = $OperatorTimeoutSeconds
    operator_result = [System.IO.Path]::GetRelativePath($repoRoot, $operatorResultPath).Replace("\", "/")
    machine_verification = [System.IO.Path]::GetRelativePath($repoRoot, $verificationPath).Replace("\", "/")
    operator_selected = $null
    operator_note = ""
    capture_status = $null
    machine_status = $null
    normal_firmware_restored = $false
    error = $null
}

$captureJob = $null
try {
    & pwsh -NoProfile -File $flashScript -ImagePath $traceImage
    if ($LASTEXITCODE -ne 0) {
        throw "Verbose recording trace flash failed with exit code $LASTEXITCODE."
    }

    $captureJob = Start-Job -ScriptBlock {
        param($WorkingRoot, $CapturePath, $Destination, $Seconds, $CapturePort)
        Set-Location $WorkingRoot
        & pwsh -NoProfile -File $CapturePath `
            -Execute -WorkflowLockHeld -Port $CapturePort `
            -Seconds $Seconds -ResetAfterOpen -OutDir $Destination
        if ($LASTEXITCODE -ne 0) {
            throw "capture_nucleo_serial failed with exit code $LASTEXITCODE"
        }
    } -ArgumentList $repoRoot, $captureScript, $resolvedOutDir, $CaptureSeconds, $Port

    Start-Sleep -Seconds $LowPowerSettleSeconds
    $promptOutput = & pwsh -NoProfile -File $aiw operator-prompt `
        -Title "Companion 共享录音链路验收 4/13" `
        -ProgressText "4/13（本次 1/1）" `
        -ScopeText "设备已进入低功耗；串口正在连续抓取。本项只验双击录音，电子纸不参与判定。" `
        -Message "现在在触摸屏任意位置快速双击一次，连续说『你好，小伴录音测试』约 3 秒，再快速双击一次结束。完成后点击通过；任一步无响应请点击失败并备注。" `
        -ExpectedText "机器证据必须同时包含 STOP 后麦克风时钟恢复、两个 double_tap、持续 PCM 帧、停止录音和外部 Flash 保存成功。" `
        -ReviewStyle -Input -Buttons "通过,失败,跳过,中止" `
        -OutputPath $operatorResultPath -TimeoutSeconds $OperatorTimeoutSeconds -Json
    if ($LASTEXITCODE -ne 0) {
        throw "Canonical operator prompt failed with exit code $LASTEXITCODE."
    }
    $promptResult = ($promptOutput -join [Environment]::NewLine) | ConvertFrom-Json
    $report.operator_selected = [string]$promptResult.selected
    $report.operator_note = [string]$promptResult.text

    Wait-Job -Job $captureJob -Timeout ($CaptureSeconds + 20) | Out-Null
    $captureOutput = Receive-Job -Job $captureJob -Keep -ErrorAction SilentlyContinue
    if ($captureJob.State -ne "Completed") {
        throw "Serial capture did not complete: state=$($captureJob.State) output=$($captureOutput -join ' ')"
    }
    if (-not (Test-Path -LiteralPath $summaryPath)) {
        throw "Serial capture did not write $summaryPath."
    }
    $summary = Get-Content -LiteralPath $summaryPath -Raw | ConvertFrom-Json
    $report.capture_status = [string]$summary.status
    if ($report.capture_status -ne "PASS") {
        throw "Serial capture status is $($report.capture_status)."
    }

    & python $verifier --log $rawLogPath --scope double-tap-recording --out $verificationPath | Out-Host
    $verificationExit = $LASTEXITCODE
    if (-not (Test-Path -LiteralPath $verificationPath)) {
        throw "Recording verifier did not write $verificationPath."
    }
    $verification = Get-Content -LiteralPath $verificationPath -Raw | ConvertFrom-Json
    $report.machine_status = [string]$verification.status
    if ($verificationExit -ne 0 -or $report.machine_status -ne "PASS") {
        throw "Recording machine verification failed: status=$($report.machine_status) exit=$verificationExit."
    }
    if ($report.operator_selected -ne "通过") {
        throw "Operator did not pass the recording item: selected=$($report.operator_selected)."
    }
} catch {
    $report.error = $_.Exception.Message
} finally {
    if ($captureJob) {
        Stop-Job -Job $captureJob -ErrorAction SilentlyContinue
        Remove-Job -Job $captureJob -Force -ErrorAction SilentlyContinue
    }
    & pwsh -NoProfile -File $flashScript
    $report.normal_firmware_restored = $LASTEXITCODE -eq 0
    if (-not $report.normal_firmware_restored -and -not $report.error) {
        $report.error = "Normal firmware restore failed."
    }
    $report.status = if ($report.error) { "FAIL" } else { "PASS" }
    $report.completed_at = (Get-Date).ToString("o")
    $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8
}

if ($report.status -ne "PASS") {
    throw "WB55 recording-chain acceptance failed: $($report.error)"
}
Write-Output "PASS: WB55 shared recording chain -> $reportPath"
