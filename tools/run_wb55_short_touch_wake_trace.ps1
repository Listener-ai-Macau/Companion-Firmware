param(
    [switch] $Execute,
    [switch] $WorkflowLockHeld,
    [ValidateRange(45, 150)]
    [int] $CaptureSeconds = 120,
    [ValidateRange(18, 30)]
    [int] $SleepySettleSeconds = 22,
    [ValidateRange(20, 90)]
    [int] $OperatorTimeoutSeconds = 75,
    [string] $OutDir = ".cache\validation\short-touch-wake-trace"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$workflowRoot = "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow"
$aiw = Join-Path $workflowRoot "scripts\aiw.ps1"
$traceImage = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_verbose_trace\Companion_Nucleo_WB55RG_VerboseTrace.hex"
$flashScript = Join-Path $repoRoot "tools\flash_nucleo_bringup.ps1"
$captureScript = Join-Path $repoRoot "tools\capture_nucleo_serial.ps1"
$shortTapVerifier = Join-Path $repoRoot "tools\verify_wb55_touch_wake_log.py"
$resolvedOutDir = if ([System.IO.Path]::IsPathRooted($OutDir)) { $OutDir } else { Join-Path $repoRoot $OutDir }
$operatorResultPath = Join-Path $resolvedOutDir "operator-result.txt"
$reportPath = Join-Path $resolvedOutDir "short-touch-wake-trace-report.json"
$summaryPath = Join-Path $resolvedOutDir "nucleo-serial-summary.json"
$rawLogPath = Join-Path $resolvedOutDir "nucleo-serial-raw.log"
$shortTapParserPath = Join-Path $resolvedOutDir "short-tap-parser.json"

if (-not $Execute) {
    throw "Refusing short-touch trace without -Execute. Run through aiw with-lock -Resource Companion-WB55."
}
if (-not $WorkflowLockHeld) {
    throw "Refusing short-touch trace without workflow lock acknowledgement."
}
if (-not (Test-Path -LiteralPath $traceImage)) {
    throw "Missing verbose trace image: $traceImage. Build it with -EpaperSsd1681VerboseTrace first."
}
if (-not (Test-Path -LiteralPath $shortTapVerifier)) {
    throw "Missing short-tap verifier: $shortTapVerifier."
}
if ($CaptureSeconds -lt ($SleepySettleSeconds + $OperatorTimeoutSeconds + 3)) {
    throw "CaptureSeconds must leave room for sleepy settle and operator action. Need at least $($SleepySettleSeconds + $OperatorTimeoutSeconds + 3), got $CaptureSeconds."
}

New-Item -ItemType Directory -Force -Path $resolvedOutDir | Out-Null

$report = [ordered]@{
    schema = "companion.wb55_short_touch_wake_trace.v1"
    status = "RUNNING"
    generated_at = (Get-Date).ToString("o")
    target = "NUCLEO-WB55RG + GDEY0154D67-T03 + FT6336U"
    trace_image = [System.IO.Path]::GetRelativePath($repoRoot, $traceImage).Replace("\", "/")
    capture_seconds = $CaptureSeconds
    sleepy_settle_seconds = $SleepySettleSeconds
    operator_timeout_seconds = $OperatorTimeoutSeconds
    output_dir = [System.IO.Path]::GetRelativePath($repoRoot, $resolvedOutDir).Replace("\", "/")
    operator_result = [System.IO.Path]::GetRelativePath($repoRoot, $operatorResultPath).Replace("\", "/")
    normal_firmware_restored = $false
    capture_summary_status = $null
    short_tap_parser_report = [System.IO.Path]::GetRelativePath($repoRoot, $shortTapParserPath).Replace("\", "/")
    short_tap_parser_status = $null
    operator_prompt_exit_code = $null
    operator_result_selected = $null
    operator_note = ""
    error = $null
}

$captureJob = $null
$normalRestoreExit = -1
try {
    & pwsh -NoProfile -File $flashScript -ImagePath $traceImage
    if ($LASTEXITCODE -ne 0) {
        throw "Trace image flash failed with exit code $LASTEXITCODE."
    }

    $captureJob = Start-Job -ScriptBlock {
        param($WorkingRoot, $CapturePath, $Destination, $Seconds)
        Set-Location $WorkingRoot
        & pwsh -NoProfile -File $CapturePath -Execute -WorkflowLockHeld -Seconds $Seconds -ResetAfterOpen -OutDir $Destination
        if ($LASTEXITCODE -ne 0) {
            throw "capture_nucleo_serial failed with exit code $LASTEXITCODE"
        }
    } -ArgumentList $repoRoot, $captureScript, $resolvedOutDir, $CaptureSeconds

    # The normal idle one-shot needs 15 seconds plus the single differential
    # sleepy-face update. Keep this bounded trace window open before asking
    # for the one real short touch, so action and serial evidence align.
    Start-Sleep -Seconds $SleepySettleSeconds
    $promptOutput = & pwsh -NoProfile -File $aiw operator-prompt `
        -Title "Companion 低功耗唤醒验收" `
        -ProgressText "1/1" `
        -ScopeText "本轮聚焦 1 项：已等待休眠稳定；trace 串口正在捕获，结束后自动恢复 normal 镜像。" `
        -Message "现在轻触屏幕中央后立刻抬手，整个触点少于 0.5 秒；不要按住等屏幕变化、不要滑动、不要长按。" `
        -ExpectedText "抬手后应判为 tap 并显示一次日常表情反馈；不能先闪 idle、不能全刷，也不能需要第二次按压。" `
        -ReviewStyle -Input -Buttons "通过,失败,跳过,中止" `
        -OutputPath $operatorResultPath -TimeoutSeconds $OperatorTimeoutSeconds -Json
    $report.operator_prompt_exit_code = $LASTEXITCODE
    if ($report.operator_prompt_exit_code -ne 0) {
        throw "Canonical operator prompt failed with exit code $($report.operator_prompt_exit_code)."
    }
    $promptResult = ($promptOutput -join [Environment]::NewLine) | ConvertFrom-Json
    $report.operator_result_selected = [string]$promptResult.selected
    $report.operator_note = [string]$promptResult.text
    if ([string]::IsNullOrWhiteSpace($report.operator_result_selected) -or
        $report.operator_result_selected -in @("Timeout", "Cancel")) {
        throw "Operator action was not completed: selected=$($report.operator_result_selected)."
    }

    Wait-Job -Job $captureJob -Timeout ($CaptureSeconds + 20) | Out-Null
    $captureOutput = Receive-Job -Job $captureJob -Keep -ErrorAction SilentlyContinue
    if ($captureJob.State -ne "Completed") {
        throw "Serial capture job did not complete: state=$($captureJob.State) output=$($captureOutput -join ' ')"
    }
    if (-not (Test-Path -LiteralPath $summaryPath)) {
        throw "Serial capture did not write $summaryPath."
    }
    $summary = Get-Content -LiteralPath $summaryPath -Raw | ConvertFrom-Json
    $report.capture_summary_status = [string]$summary.status
    if ($report.capture_summary_status -ne "PASS") {
        throw "Serial capture summary status is $($report.capture_summary_status)."
    }
    if (-not (Test-Path -LiteralPath $rawLogPath)) {
        throw "Serial capture did not write $rawLogPath."
    }
    & python $shortTapVerifier --log $rawLogPath --scope short-tap --out $shortTapParserPath | Out-Host
    $parserExit = $LASTEXITCODE
    if (-not (Test-Path -LiteralPath $shortTapParserPath)) {
        throw "Short-tap verifier did not write $shortTapParserPath."
    }
    $shortTapReport = Get-Content -LiteralPath $shortTapParserPath -Raw | ConvertFrom-Json
    $report.short_tap_parser_status = [string]$shortTapReport.status
    if ($parserExit -ne 0 -or $report.short_tap_parser_status -ne "PASS") {
        throw "Short-tap trace verification failed: status=$($report.short_tap_parser_status) exit=$parserExit."
    }
} catch {
    $report.error = $_.Exception.Message
} finally {
    if ($captureJob) {
        Remove-Job -Job $captureJob -Force -ErrorAction SilentlyContinue
    }
    & pwsh -NoProfile -File $flashScript
    $normalRestoreExit = $LASTEXITCODE
    $report.normal_firmware_restored = $normalRestoreExit -eq 0
    if (-not $report.normal_firmware_restored -and -not $report.error) {
        $report.error = "Normal firmware restore failed with exit code $normalRestoreExit."
    }
    $report.status = if ($report.error) {
        "FAIL"
    } elseif ($report.operator_result_selected -eq "失败") {
        "OPERATOR_FAILED_MACHINE_EVIDENCE_CAPTURED"
    } elseif ($report.operator_result_selected -in @("跳过", "中止")) {
        "OPERATOR_INCOMPLETE"
    } elseif ($report.normal_firmware_restored) {
        "PASS"
    } else {
        "FAIL"
    }
    $report.completed_at = (Get-Date).ToString("o")
    $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8
}

if ($report.status -ne "PASS") {
    throw "Short-touch wake trace failed: $($report.error)"
}

Write-Output "PASS: short-touch wake trace -> $reportPath"
