param(
    [string] $TypeRepoRoot = (Join-Path $PSScriptRoot "..\..\..\Listener\Listener-Type"),
    [string] $ListenerExe,
    [string] $ListenerLogPath,
    [string] $OutDir,
    [int] $ProbeTimeoutMs = 30000,
    [int] $A1TimeoutMs = 45000,
    [int] $A1Rounds = 6,
    [int] $A2TimeoutMs = 120000,
    [int] $MaxMissingPackets = 0,
    [int] $CliRetries = 2,
    [int] $RetryDelayMs = 5000,
    [int] $RoundCooldownMs = 5000,
    [bool] $RequireA1Text = $true,
    [bool] $RequireA2Text = $true,
    [int] $MinFinalTextChars = 1,
    [switch] $PromptOperator,
    [switch] $Execute,
    [switch] $WorkflowLockHeld
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$typeRoot = (Resolve-Path $TypeRepoRoot).Path

function Resolve-ListenerExe {
    param([string] $Requested)

    $candidates = @()
    if ($Requested) { $candidates += $Requested }
    $candidates += @(
        (Join-Path $typeRoot "src-tauri\target\debug\listener-type.exe"),
        (Join-Path $typeRoot "src-tauri\target\release\listener-type.exe"),
        (Join-Path $typeRoot "src-tauri\target\debug\listener-type"),
        (Join-Path $typeRoot "src-tauri\target\release\listener-type")
    )

    foreach ($candidate in $candidates) {
        if ([string]::IsNullOrWhiteSpace($candidate)) { continue }
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    throw "listener-type executable not found. Build Listener-Type first or pass -ListenerExe."
}

function Resolve-ListenerLogPath {
    param([string] $Requested)

    if ($Requested) {
        $parent = Split-Path -Parent $Requested
        if ($parent -and -not (Test-Path -LiteralPath $parent)) {
            New-Item -ItemType Directory -Force -Path $parent | Out-Null
        }
        if (-not (Test-Path -LiteralPath $Requested -PathType Leaf)) {
            New-Item -ItemType File -Force -Path $Requested | Out-Null
        }
        return (Resolve-Path -LiteralPath $Requested).Path
    }

    $defaultPath = Join-Path $env:LOCALAPPDATA "Listener Type Companion\Logs\listener-type.log"
    $parentPath = Split-Path -Parent $defaultPath
    if (-not (Test-Path -LiteralPath $parentPath)) {
        New-Item -ItemType Directory -Force -Path $parentPath | Out-Null
    }
    if (-not (Test-Path -LiteralPath $defaultPath -PathType Leaf)) {
        New-Item -ItemType File -Force -Path $defaultPath | Out-Null
    }
    return (Resolve-Path -LiteralPath $defaultPath).Path
}

function Set-CompanionTypeEnvironment {
    param(
        [string] $ReadyCommand = "TYPE:READY",
        [bool] $StatsOnly = $true
    )

    $env:LISTENER_TYPE_APP_PROFILE = "companion"
    $env:LISTENER_TYPE_BLE_TARGET_NAME = "companion"
    $env:LISTENER_TYPE_HIDE_MAIN_ON_START = "1"
    $env:LISTENER_TYPE_DISABLE_BACKGROUND_BLE = "1"
    $env:LISTENER_TYPE_EMBEDDED_BLE_READY_COMMAND = $ReadyCommand
    if ($StatsOnly) {
        $env:LISTENER_TYPE_EMBEDDED_BLE_STATS_ONLY = "1"
        Remove-Item Env:\LISTENER_TYPE_FORCE_RAW_OUTPUT -ErrorAction SilentlyContinue
    } else {
        Remove-Item Env:\LISTENER_TYPE_EMBEDDED_BLE_STATS_ONLY -ErrorAction SilentlyContinue
        $env:LISTENER_TYPE_FORCE_RAW_OUTPUT = "1"
    }
}

function New-ValidationOutputDir {
    param([string] $Requested)

    if ($Requested) {
        New-Item -ItemType Directory -Force -Path $Requested | Out-Null
        return (Resolve-Path -LiteralPath $Requested).Path
    }

    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $path = Join-Path $repoRoot ".cache\validation\companion-type-a1-a2-$stamp"
    New-Item -ItemType Directory -Force -Path $path | Out-Null
    return (Resolve-Path -LiteralPath $path).Path
}

function Show-OperatorPrompt {
    param(
        [Parameter(Mandatory = $true)][string] $Title,
        [Parameter(Mandatory = $true)][string] $Message
    )

    try {
        [System.Media.SystemSounds]::Exclamation.Play()
        [Console]::Beep(880, 220)
    } catch {
        Write-Warning "Could not play operator prompt sound: $($_.Exception.Message)"
    }

    try {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show(
            $Message,
            $Title,
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Information
        ) | Out-Null
    } catch {
        Write-Host ""
        Write-Host "=== $Title ==="
        Write-Host $Message
        Write-Host ""
    }
}

function Get-LogOffset {
    param([Parameter(Mandatory = $true)][string] $Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return 0L }
    return [int64](Get-Item -LiteralPath $Path).Length
}

function Read-LogTail {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][int64] $Offset
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return "" }
    $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
    try {
        if ($Offset -gt $stream.Length) { $Offset = 0 }
        [void] $stream.Seek($Offset, [System.IO.SeekOrigin]::Begin)
        $memory = [System.IO.MemoryStream]::new()
        try {
            $stream.CopyTo($memory)
            return [System.Text.Encoding]::UTF8.GetString($memory.ToArray())
        } finally {
            $memory.Dispose()
        }
    } finally {
        $stream.Dispose()
    }
}

function Wait-ListenerLogResult {
    param(
        [Parameter(Mandatory = $true)][string] $Label,
        [Parameter(Mandatory = $true)][string] $LogPath,
        [Parameter(Mandatory = $true)][int64] $StartOffset,
        [Parameter(Mandatory = $true)][string] $PassPattern,
        [Parameter(Mandatory = $true)][string] $FailPattern,
        [Parameter(Mandatory = $true)][int] $TimeoutMs
    )

    $deadline = [DateTime]::UtcNow.AddMilliseconds($TimeoutMs + 10000)
    $latest = ""
    while ([DateTime]::UtcNow -lt $deadline) {
        $latest = Read-LogTail -Path $LogPath -Offset $StartOffset
        $fail = [regex]::Match($latest, $FailPattern, [System.Text.RegularExpressions.RegexOptions]::Singleline)
        if ($fail.Success) {
            throw "$Label failed: $($fail.Groups['error'].Value.Trim())"
        }
        $pass = [regex]::Match($latest, $PassPattern, [System.Text.RegularExpressions.RegexOptions]::Singleline)
        if ($pass.Success) {
            return $pass
        }
        Start-Sleep -Milliseconds 500
    }

    $snippet = $latest
    if ($snippet.Length -gt 2000) {
        $snippet = $snippet.Substring($snippet.Length - 2000)
    }
    throw "$Label timed out after $($TimeoutMs + 10000) ms. Log tail:`n$snippet"
}

function Invoke-ListenerCli {
    param(
        [Parameter(Mandatory = $true)][string] $Label,
        [Parameter(Mandatory = $true)][string[]] $Arguments,
        [Parameter(Mandatory = $true)][int] $TimeoutMs,
        [Parameter(Mandatory = $true)][string] $PassPattern,
        [Parameter(Mandatory = $true)][string] $FailPattern,
        [Parameter(Mandatory = $true)][string] $ListenerExePath,
        [Parameter(Mandatory = $true)][string] $LogPath,
        [string] $ReadyCommand = "TYPE:READY",
        [bool] $StatsOnly = $true
    )

    $offset = Get-LogOffset -Path $LogPath
    $argumentList = $Arguments -join " "
    Write-Host "RUN: $ListenerExePath $argumentList"
    Set-CompanionTypeEnvironment -ReadyCommand $ReadyCommand -StatsOnly $StatsOnly
    $process = Start-Process -FilePath $ListenerExePath -ArgumentList $Arguments -PassThru -WindowStyle Hidden
    try {
        if ($process.WaitForExit(3000) -and $process.ExitCode -ne 0) {
            $latest = Read-LogTail -Path $LogPath -Offset $offset
            $fail = [regex]::Match($latest, $FailPattern, [System.Text.RegularExpressions.RegexOptions]::Singleline)
            if ($fail.Success) {
                throw "$Label failed: $($fail.Groups['error'].Value.Trim())"
            }
            $snippet = $latest
            if ($snippet.Length -gt 2000) {
                $snippet = $snippet.Substring($snippet.Length - 2000)
            }
            throw "$Label launcher exited with code $($process.ExitCode). Log tail:`n$snippet"
        }
        $match = Wait-ListenerLogResult -Label $Label -LogPath $LogPath -StartOffset $offset -PassPattern $PassPattern -FailPattern $FailPattern -TimeoutMs $TimeoutMs
        if (-not $process.WaitForExit(5000)) {
            throw "$Label logged PASS but listener-type process did not exit within 5000 ms."
        }
        if ($process.ExitCode -ne 0) {
            throw "$Label logged PASS but listener-type exited with code $($process.ExitCode)."
        }
        return $match
    } catch {
        if ($process -and -not $process.HasExited) {
            try {
                $process.Kill()
                $process.WaitForExit(5000) | Out-Null
            } catch {
                Write-Warning "$Label cleanup could not stop listener-type process $($process.Id): $($_.Exception.Message)"
            }
        }
        throw
    }
}

function Invoke-ListenerCliWithRetry {
    param(
        [Parameter(Mandatory = $true)][string] $Label,
        [Parameter(Mandatory = $true)][string[]] $Arguments,
        [Parameter(Mandatory = $true)][int] $TimeoutMs,
        [Parameter(Mandatory = $true)][string] $PassPattern,
        [Parameter(Mandatory = $true)][string] $FailPattern,
        [Parameter(Mandatory = $true)][string] $ListenerExePath,
        [Parameter(Mandatory = $true)][string] $LogPath,
        [Parameter(Mandatory = $true)][int] $MaxRetries,
        [Parameter(Mandatory = $true)][int] $DelayMs,
        [Parameter(Mandatory = $true)] $RetryRecords,
        [string] $ReadyCommand = "TYPE:READY",
        [bool] $StatsOnly = $true
    )

    $maxAttempts = 1 + [Math]::Max(0, $MaxRetries)
    for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
        try {
            $match = Invoke-ListenerCli `
                -Label "$Label attempt $attempt" `
                -Arguments $Arguments `
                -TimeoutMs $TimeoutMs `
                -PassPattern $PassPattern `
                -FailPattern $FailPattern `
                -ListenerExePath $ListenerExePath `
                -LogPath $LogPath `
                -ReadyCommand $ReadyCommand `
                -StatsOnly $StatsOnly
            return [pscustomobject]@{
                match = $match
                attempts = $attempt
            }
        } catch {
            $message = $_.Exception.Message
            if ($attempt -ge $maxAttempts) {
                throw $message
            }
            $RetryRecords.Add([pscustomobject]@{
                label = $Label
                attempt = $attempt
                retry_after_ms = $DelayMs
                error = $message
            }) | Out-Null
            Write-Warning "$Label attempt $attempt failed; retrying in $DelayMs ms: $message"
            Start-Sleep -Milliseconds $DelayMs
        }
    }

    throw "$Label retry loop exited unexpectedly."
}

function New-StreamResult {
    param(
        [Parameter(Mandatory = $true)][string] $CaseId,
        [Parameter(Mandatory = $true)][int] $Round,
        [Parameter(Mandatory = $true)] $Match,
        [Parameter(Mandatory = $true)][int] $Attempts,
        [bool] $RequireText = $false
    )

    $json = $null
    $jsonText = $Match.Groups["json"].Value
    if (-not [string]::IsNullOrWhiteSpace($jsonText)) {
        $json = $jsonText | ConvertFrom-Json
    }

    if ($json) {
        $pcm = [int64] $json.reconstructedPcmBytes
        $missing = [int] $json.stats.missingPacketCount
        $asrPcm = [int64] $json.stats.asrBoundaryPcmBytes
        $duration = [double] $json.stats.asrBoundaryDurationSeconds
        $finalText = if ($json.transcript) { [string] $json.transcript.finalText } else { "" }
        $rawTranscript = if ($json.transcript) { [string] $json.transcript.rawTranscript } else { "" }
        $transcriptError = if ($json.transcript) { $json.transcript.errorCode } else { $null }
    } else {
        $pcm = [int64] $Match.Groups["pcm"].Value
        $missing = [int] $Match.Groups["missing"].Value
        $asrPcm = $pcm
        $duration = [Math]::Round($pcm / 32000.0, 3)
        $finalText = ""
        $rawTranscript = ""
        $transcriptError = $null
    }

    $finalTextChars = $finalText.Trim().Length
    $textOk = -not $RequireText -or $finalTextChars -ge $MinFinalTextChars
    $packetOk = $missing -le $MaxMissingPackets
    [pscustomobject]@{
        case = $CaseId
        round = $Round
        status = if ($packetOk -and $textOk) { "PASS" } else { "FAIL" }
        pcm_bytes = $pcm
        asr_boundary_pcm_bytes = $asrPcm
        asr_boundary_duration_seconds = $duration
        missing_packets = $missing
        final_text_chars = $finalTextChars
        final_text = $finalText
        raw_transcript = $rawTranscript
        transcript_error_code = $transcriptError
        attempts = $Attempts
    }
}

$listenerExePath = Resolve-ListenerExe -Requested $ListenerExe
$logPath = Resolve-ListenerLogPath -Requested $ListenerLogPath
$outputDir = New-ValidationOutputDir -Requested $OutDir
$summaryJson = Join-Path $outputDir "companion-type-a1-a2-summary.json"
$summaryMd = Join-Path $outputDir "companion-type-a1-a2-summary.md"

$lockCommand = "pwsh -NoProfile -File <ai-collaboration-workflow>\scripts\aiw.ps1 with-lock -Resource Companion-WB55,BLE-Companion -Purpose `"Companion Type A1/A2 validation`" -Run pwsh -NoProfile -File .\tools\verify_companion_type_a1_a2.ps1 -Execute -WorkflowLockHeld"

if (-not $Execute) {
    Write-Host "DRY-RUN: Companion Type A1/A2 validation is ready."
    Write-Host "ListenerExe: $listenerExePath"
    Write-Host "ListenerLog: $logPath"
    Write-Host "OutDir: $outputDir"
    Write-Host "Run with workflow hardware lock:"
    Write-Host "  $lockCommand"
    Write-Host "This script will run probe=$ProbeTimeoutMs ms, A1=$A1Rounds rounds x $A1TimeoutMs ms, A2=$A2TimeoutMs ms."
    Write-Host "A1 text gate: $RequireA1Text; A2 text gate: $RequireA2Text (min final chars: $MinFinalTextChars)."
    Write-Host "Blocking operator prompt: $([bool]$PromptOperator). Add -PromptOperator only for real-time human action or observation."
    exit 0
}

if (-not $WorkflowLockHeld) {
    Write-Host "Use the workflow hardware lock before executing:"
    Write-Host "  $lockCommand"
    throw "Refusing to run Companion A1/A2 hardware validation without -WorkflowLockHeld."
}

if ($PromptOperator) {
    Show-OperatorPrompt `
        -Title "Companion A1/A2 验证即将开始" `
        -Message "请确认 Companion NUCLEO 已刷入统一 Companion app 或同一个 Companion package，设备蓝牙名为 companion，Listener Type 可运行，电脑声音/蓝牙处于测试状态。点击 OK 后脚本会自动执行 BLE 订阅探测、A1 六轮短链路、A2 长窗口，并把证据写入：$outputDir"
}

$startedAt = (Get-Date).ToUniversalTime().ToString("o")
$results = [System.Collections.Generic.List[object]]::new()
$retries = [System.Collections.Generic.List[object]]::new()
$errors = [System.Collections.Generic.List[string]]::new()

try {
    $probePass = "probe-embedded-audio-ble-subscription PASS"
    $probeFail = "probe-embedded-audio-ble-subscription failed: (?<error>.*)"
    [void](Invoke-ListenerCliWithRetry `
        -Label "probe" `
        -Arguments @("--probe-embedded-audio-ble-subscription", [string]$ProbeTimeoutMs) `
        -TimeoutMs $ProbeTimeoutMs `
        -PassPattern $probePass `
        -FailPattern $probeFail `
        -ListenerExePath $listenerExePath `
        -LogPath $logPath `
        -MaxRetries $CliRetries `
        -DelayMs $RetryDelayMs `
        -RetryRecords $retries)

    $streamPass = "embedded_audio_ble_stream_result_json=(?<json>\{[^\r\n]*\})|submit-embedded-audio-ble-stream done: pcm_bytes=(?<pcm>\d+) missing_packets=(?<missing>\d+)"
    $streamFail = "submit-embedded-audio-ble-stream failed: (?<error>.*)"

    for ($round = 1; $round -le $A1Rounds; $round++) {
        if ($round -gt 1 -and $RoundCooldownMs -gt 0) {
            Start-Sleep -Milliseconds $RoundCooldownMs
        }
        if ($RequireA1Text -and $PromptOperator) {
            Show-OperatorPrompt `
                -Title "Companion A1 文字识别 $round/$A1Rounds" `
                -Message "点击 OK 后请马上对着 Companion 麦克风说一句清晰的话。脚本会为 A1 第 $round/$A1Rounds 轮打开真实麦克风语音窗口，并要求 Type 返回 ASR final text。"
        }
        $attempt = Invoke-ListenerCliWithRetry `
            -Label "A1 round $round" `
            -Arguments @("--submit-embedded-audio-ble-stream", [string]$A1TimeoutMs) `
            -TimeoutMs $A1TimeoutMs `
            -PassPattern $streamPass `
            -FailPattern $streamFail `
            -ListenerExePath $listenerExePath `
            -LogPath $logPath `
            -MaxRetries $CliRetries `
            -DelayMs $RetryDelayMs `
            -RetryRecords $retries `
            -ReadyCommand $(if ($RequireA1Text) { "TYPE:READY:A2" } else { "TYPE:READY" }) `
            -StatsOnly (-not $RequireA1Text)
        $result = New-StreamResult -CaseId "A1" -Round $round -Match $attempt.match -Attempts $attempt.attempts -RequireText $RequireA1Text
        $results.Add($result) | Out-Null
        if ($result.status -ne "PASS") {
            if ($result.missing_packets -gt $MaxMissingPackets) {
                $errors.Add("A1 round $round missing_packets=$($result.missing_packets) > $MaxMissingPackets") | Out-Null
            }
            if ($RequireA1Text -and $result.final_text_chars -lt $MinFinalTextChars) {
                $errors.Add("A1 round $round final_text_chars=$($result.final_text_chars) < $MinFinalTextChars") | Out-Null
            }
        }
    }

    if ($RoundCooldownMs -gt 0) {
        Start-Sleep -Milliseconds $RoundCooldownMs
    }
    if ($RequireA2Text -and $PromptOperator) {
        Show-OperatorPrompt `
            -Title "Companion A2 文字识别" `
            -Message "点击 OK 后请马上对着 Companion 麦克风说一句清晰的话。脚本会用 TYPE:READY:A2 打开长录音窗口，并要求 Type 返回 ASR final text。"
    }
    $a2Attempt = Invoke-ListenerCliWithRetry `
        -Label "A2" `
        -Arguments @("--submit-embedded-audio-ble-stream", [string]$A2TimeoutMs) `
        -TimeoutMs $A2TimeoutMs `
        -PassPattern $streamPass `
        -FailPattern $streamFail `
        -ListenerExePath $listenerExePath `
        -LogPath $logPath `
        -MaxRetries $CliRetries `
        -DelayMs $RetryDelayMs `
        -RetryRecords $retries `
        -ReadyCommand $(if ($RequireA2Text) { "TYPE:READY:A2" } else { "TYPE:READY" }) `
        -StatsOnly (-not $RequireA2Text)
    $a2Result = New-StreamResult -CaseId "A2" -Round 1 -Match $a2Attempt.match -Attempts $a2Attempt.attempts -RequireText $RequireA2Text
    $results.Add($a2Result) | Out-Null
    if ($a2Result.status -ne "PASS") {
        if ($a2Result.missing_packets -gt $MaxMissingPackets) {
            $errors.Add("A2 missing_packets=$($a2Result.missing_packets) > $MaxMissingPackets") | Out-Null
        }
        if ($RequireA2Text -and $a2Result.final_text_chars -lt $MinFinalTextChars) {
            $errors.Add("A2 final_text_chars=$($a2Result.final_text_chars) < $MinFinalTextChars") | Out-Null
        }
    }
} catch {
    $errors.Add($_.Exception.Message) | Out-Null
}

$finishedAt = (Get-Date).ToUniversalTime().ToString("o")
$status = if ($errors.Count -eq 0) { "PASS" } else { "FAIL" }
$summary = [ordered]@{
    schema = "companion.type_a1_a2.validation.v1"
    status = $status
    started_at_utc = $startedAt
    finished_at_utc = $finishedAt
    listener_exe = $listenerExePath
    listener_log = $logPath
    probe_timeout_ms = $ProbeTimeoutMs
    a1_rounds = $A1Rounds
    a1_timeout_ms = $A1TimeoutMs
    a2_timeout_ms = $A2TimeoutMs
    max_missing_packets = $MaxMissingPackets
    cli_retries = $CliRetries
    retry_delay_ms = $RetryDelayMs
    round_cooldown_ms = $RoundCooldownMs
    require_a1_text = $RequireA1Text
    require_a2_text = $RequireA2Text
    min_final_text_chars = $MinFinalTextChars
    prompt_operator = [bool]$PromptOperator
    results = @($results)
    retries = @($retries)
    errors = @($errors)
}

$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryJson -Encoding UTF8
$md = @(
    "# Companion Type A1/A2 Validation",
    "",
    "- Status: $status",
    "- Started UTC: $startedAt",
    "- Finished UTC: $finishedAt",
    "- Listener exe: ``$listenerExePath``",
    "- Listener log: ``$logPath``",
    "- A1 rounds: $A1Rounds x $A1TimeoutMs ms",
    "- A2 timeout: $A2TimeoutMs ms",
    "- Max missing packets: $MaxMissingPackets",
    "",
    "## Results"
)
foreach ($item in $results) {
    $textPart = if ($item.final_text_chars -gt 0) { ", final_text_chars=$($item.final_text_chars), final_text=`"$($item.final_text)`"" } else { "" }
    $md += "- $($item.case) round $($item.round): $($item.status), pcm=$($item.pcm_bytes), missing=$($item.missing_packets), attempts=$($item.attempts)$textPart"
}
if ($retries.Count -gt 0) {
    $md += ""
    $md += "## Retries"
    foreach ($retryItem in $retries) {
        $md += "- $($retryItem.label) attempt $($retryItem.attempt): retry_after_ms=$($retryItem.retry_after_ms)"
    }
}
if ($errors.Count -gt 0) {
    $md += ""
    $md += "## Errors"
    foreach ($errorItem in $errors) {
        $md += "- $errorItem"
    }
}
$md | Set-Content -LiteralPath $summaryMd -Encoding UTF8

Write-Host "companion_type_a1_a2_result_json=$($summary | ConvertTo-Json -Depth 8 -Compress)"
Write-Host "Summary: $summaryJson"

if ($status -ne "PASS") {
    throw "Companion Type A1/A2 validation failed. See $summaryJson"
}
