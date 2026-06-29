param(
    [string] $TypeRepoRoot = (Join-Path $PSScriptRoot "..\..\..\Listener\Listener-Type"),
    [string] $ListenerExe,
    [string] $ListenerLogPath,
    [string] $OutDir,
    [int] $ProbeTimeoutMs = 30000,
    [switch] $SkipInitialProbe,
    [int] $A1TimeoutMs = 45000,
    [int] $A1Rounds = 6,
    [int] $A2TimeoutMs = 120000,
    [int] $MaxMissingPackets = 0,
    [int] $CliRetries = 2,
    [int] $RetryDelayMs = 5000,
    [int] $BleCleanupStopTimeoutMs = 5000,
    [int] $BleRecoveryDelayMs = 8000,
    [int] $BleRecoveryProbeTimeoutMs = 30000,
    [int] $RoundCooldownMs = 5000,
    [bool] $RequireA1Text = $true,
    [bool] $RequireA2Text = $true,
    [int] $MinFinalTextChars = 1,
    [string] $A2PlaybackText = "明天下午两点提醒我检查蓝牙音频丢包率。",
    [string] $TtsVoiceName = "",
    [double] $TtsGain = 4.0,
    [int] $TtsRate = 0,
    [double] $MinTranscriptAccuracy = 0.60,
    [switch] $GateA1TranscriptAccuracy,
    [switch] $GateA2TranscriptAccuracy,
    [string] $A1PlaybackTextList = "",
    [int] $PrePlaybackDelayMs = 300,
    [ValidateSet("wav", "speech")]
    [string] $PlaybackMode = "wav",
    [int] $PlaybackVolumePercent = 90,
    [switch] $KeepPlaybackVolume,
    [switch] $DisableTtsPlayback,
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

    # Listener-Type's debug CLI writes to lib::log_dir_path(), which is still
    # %LOCALAPPDATA%\Listener Type\Logs even when the Companion BLE target is set.
    $defaultPath = Join-Path $env:LOCALAPPDATA "Listener Type\Logs\listener-type.log"
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
    $env:LISTENER_TYPE_DISABLE_EMBEDDED_BLE_PROCESSING_SYNC = "1"
    $env:LISTENER_TYPE_EMBEDDED_BLE_READY_COMMAND = $ReadyCommand
    $env:LISTENER_TYPE_RECORD_EMBEDDED_AUDIO_FOR_DEBUG = "1"
    $env:LISTENER_TYPE_EXTRA_ASR_HOTWORDS = Get-CompanionExtraAsrHotwords
    if ($StatsOnly) {
        $env:LISTENER_TYPE_EMBEDDED_BLE_STATS_ONLY = "1"
        Remove-Item Env:\LISTENER_TYPE_FORCE_RAW_OUTPUT -ErrorAction SilentlyContinue
    } else {
        Remove-Item Env:\LISTENER_TYPE_EMBEDDED_BLE_STATS_ONLY -ErrorAction SilentlyContinue
        $env:LISTENER_TYPE_FORCE_RAW_OUTPUT = "1"
    }
}

function Initialize-CompanionPlaybackVolumeApi {
    if ("CompanionPlaybackAudioEndpoint" -as [type]) {
        return
    }

    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

[ComImport]
[Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
internal class CompanionMMDeviceEnumerator
{
}

internal enum CompanionEDataFlow
{
    eRender = 0,
    eCapture = 1,
    eAll = 2
}

internal enum CompanionERole
{
    eConsole = 0,
    eMultimedia = 1,
    eCommunications = 2
}

[ComImport]
[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
internal interface ICompanionMMDeviceEnumerator
{
    int EnumAudioEndpoints();

    [PreserveSig]
    int GetDefaultAudioEndpoint(CompanionEDataFlow dataFlow, CompanionERole role, out ICompanionMMDevice ppDevice);
}

[ComImport]
[Guid("D666063F-1587-4E43-81F1-B948E807363F")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
internal interface ICompanionMMDevice
{
    [PreserveSig]
    int Activate(ref Guid iid, int dwClsCtx, IntPtr pActivationParams, out ICompanionAudioEndpointVolume ppInterface);
}

[ComImport]
[Guid("5CDF2C82-841E-4546-9722-0CF74078229A")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
internal interface ICompanionAudioEndpointVolume
{
    int RegisterControlChangeNotify(IntPtr pNotify);
    int UnregisterControlChangeNotify(IntPtr pNotify);
    int GetChannelCount(out uint pnChannelCount);
    int SetMasterVolumeLevel(float fLevelDB, Guid pguidEventContext);
    int SetMasterVolumeLevelScalar(float fLevel, Guid pguidEventContext);
    int GetMasterVolumeLevel(out float pfLevelDB);
    int GetMasterVolumeLevelScalar(out float pfLevel);
    int SetChannelVolumeLevel(uint nChannel, float fLevelDB, Guid pguidEventContext);
    int SetChannelVolumeLevelScalar(uint nChannel, float fLevel, Guid pguidEventContext);
    int GetChannelVolumeLevel(uint nChannel, out float pfLevelDB);
    int GetChannelVolumeLevelScalar(uint nChannel, out float pfLevel);
    int SetMute([MarshalAs(UnmanagedType.Bool)] bool bMute, Guid pguidEventContext);
    int GetMute(out bool pbMute);
}

public sealed class CompanionPlaybackAudioEndpoint
{
    public float Volume;
    public bool Muted;

    private static ICompanionAudioEndpointVolume GetEndpoint()
    {
        var enumerator = (ICompanionMMDeviceEnumerator)(new CompanionMMDeviceEnumerator());
        ICompanionMMDevice device;
        int hr = enumerator.GetDefaultAudioEndpoint(CompanionEDataFlow.eRender, CompanionERole.eMultimedia, out device);
        if (hr != 0)
        {
            Marshal.ThrowExceptionForHR(hr);
        }

        Guid iid = typeof(ICompanionAudioEndpointVolume).GUID;
        ICompanionAudioEndpointVolume endpoint;
        hr = device.Activate(ref iid, 23, IntPtr.Zero, out endpoint);
        if (hr != 0)
        {
            Marshal.ThrowExceptionForHR(hr);
        }
        return endpoint;
    }

    public static CompanionPlaybackAudioEndpoint Snapshot()
    {
        var endpoint = GetEndpoint();
        float volume;
        bool muted;
        endpoint.GetMasterVolumeLevelScalar(out volume);
        endpoint.GetMute(out muted);
        return new CompanionPlaybackAudioEndpoint { Volume = volume, Muted = muted };
    }

    public static void Set(float volume, bool muted)
    {
        var endpoint = GetEndpoint();
        var context = Guid.Empty;
        endpoint.SetMute(muted, context);
        endpoint.SetMasterVolumeLevelScalar(volume, context);
    }
}
'@
}

function Set-CompanionPlaybackVolume {
    param([int] $Percent)

    if ($Percent -lt 0) {
        Write-Host "PLAYBACK_VOLUME: skipped"
        return $null
    }

    try {
        Initialize-CompanionPlaybackVolumeApi
        $snapshot = [CompanionPlaybackAudioEndpoint]::Snapshot()
        $target = [Math]::Max(0.01, [Math]::Min(1.0, [double]$Percent / 100.0))
        [CompanionPlaybackAudioEndpoint]::Set([single]$target, $false)
        Write-Host ("PLAYBACK_VOLUME: set target={0} previous={1:0.###} muted={2}" -f $Percent, [double]$snapshot.Volume, [bool]$snapshot.Muted)
        return $snapshot
    } catch {
        Write-Warning "Failed to set playback volume before Companion audio validation: $($_.Exception.Message)"
        return $null
    }
}

function Restore-CompanionPlaybackVolume {
    param($Snapshot)

    if ($KeepPlaybackVolume -or $null -eq $Snapshot) {
        return
    }

    try {
        [CompanionPlaybackAudioEndpoint]::Set([single]$Snapshot.Volume, [bool]$Snapshot.Muted)
        Write-Host ("PLAYBACK_VOLUME: restored volume={0:0.###} muted={1}" -f [double]$Snapshot.Volume, [bool]$Snapshot.Muted)
    } catch {
        Write-Warning "Failed to restore playback volume after Companion audio validation: $($_.Exception.Message)"
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

$DefaultA1PlaybackTexts = @(
    "打开设置",
    "新建文件",
    "保存文件",
    "撤销操作",
    "关闭窗口",
    "复制内容",
    "粘贴内容",
    "全部选中"
)
$A1PlaybackTexts = @($A1PlaybackTextList -split "\|" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | ForEach-Object { $_.Trim() })
if ($A1PlaybackTexts.Count -eq 0) {
    $A1PlaybackTexts = @($DefaultA1PlaybackTexts)
}
if ($A1PlaybackTexts.Count -eq 0) {
    throw "A1 playback text list must not be empty."
}

function Get-CompanionExtraAsrHotwords {
    $extra = @(
        "Companion",
        "蓝牙音频",
        "音频链路",
        "丢包率",
        "完整上传",
        "正确识别"
    )
    return (@($A1PlaybackTexts + $extra) | Select-Object -Unique) -join "|"
}

function Get-A1PlaybackText {
    param([Parameter(Mandatory = $true)][int] $Round)
    $index = ($Round - 1) % $A1PlaybackTexts.Count
    return $A1PlaybackTexts[$index]
}

function Normalize-TranscriptAccuracyText {
    param([string] $Text)
    if ($null -eq $Text) {
        return ""
    }
    $normalized = $Text.Normalize([System.Text.NormalizationForm]::FormKC).ToLowerInvariant()
    $builder = [System.Text.StringBuilder]::new()
    foreach ($ch in $normalized.ToCharArray()) {
        if ([char]::IsLetterOrDigit($ch)) {
            [void] $builder.Append($ch)
        }
    }
    return $builder.ToString()
}

function Get-TranscriptEditDistance {
    param(
        [string] $Expected,
        [string] $Actual
    )

    if ($Expected -eq $Actual) {
        return 0
    }

    $previous = New-Object int[] ($Actual.Length + 1)
    for ($i = 0; $i -le $Actual.Length; $i++) {
        $previous[$i] = $i
    }
    for ($i = 1; $i -le $Expected.Length; $i++) {
        $current = New-Object int[] ($Actual.Length + 1)
        $current[0] = $i
        for ($j = 1; $j -le $Actual.Length; $j++) {
            $cost = if ($Expected[$i - 1] -eq $Actual[$j - 1]) { 0 } else { 1 }
            $insertCost = $current[$j - 1] + 1
            $deleteCost = $previous[$j] + 1
            $replaceCost = $previous[$j - 1] + $cost
            $current[$j] = [Math]::Min([Math]::Min($insertCost, $deleteCost), $replaceCost)
        }
        $previous = $current
    }
    return $previous[$Actual.Length]
}

function Measure-TranscriptAccuracy {
    param(
        [string] $Expected,
        [string] $Transcript
    )

    $expectedNormalized = Normalize-TranscriptAccuracyText -Text $Expected
    $transcriptNormalized = Normalize-TranscriptAccuracyText -Text $Transcript
    $distance = Get-TranscriptEditDistance -Expected $expectedNormalized -Actual $transcriptNormalized
    if ($expectedNormalized.Length -eq 0) {
        $cer = if ($transcriptNormalized.Length -eq 0) { 0.0 } else { 1.0 }
    } else {
        $cer = $distance / [double] $expectedNormalized.Length
    }
    $accuracy = [Math]::Max(0.0, 1.0 - $cer)
    return [ordered]@{
        normalized_expected = $expectedNormalized
        normalized_transcript = $transcriptNormalized
        edit_distance = $distance
        reference_length = $expectedNormalized.Length
        cer = [Math]::Round($cer, 6)
        accuracy = [Math]::Round($accuracy, 6)
    }
}

function New-TtsWav {
    param(
        [Parameter(Mandatory = $true)][string] $Text,
        [Parameter(Mandatory = $true)][string] $Path,
        [string] $VoiceName = "",
        [int] $Rate = 0
    )

    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }

    Add-Type -AssemblyName System.Speech
    $synth = [System.Speech.Synthesis.SpeechSynthesizer]::new()
    try {
        $synth.Volume = 100
        $synth.Rate = [Math]::Max(-10, [Math]::Min(10, $Rate))
        $voices = @($synth.GetInstalledVoices())
        $selectedVoice = $null
        if (-not [string]::IsNullOrWhiteSpace($VoiceName)) {
            $selectedVoice = $voices |
                Where-Object {
                    $_.VoiceInfo.Name -eq $VoiceName -or
                    $_.VoiceInfo.Name.IndexOf($VoiceName, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
                } |
                Select-Object -First 1
            if ($null -eq $selectedVoice) {
                throw "TTS voice not found: $VoiceName"
            }
        } else {
            $selectedVoice = $voices |
                Where-Object { $_.VoiceInfo.Culture.Name -like "zh-*" } |
                Select-Object -First 1
        }
        if ($null -ne $selectedVoice) {
            $synth.SelectVoice($selectedVoice.VoiceInfo.Name)
        }
        $format = [System.Speech.AudioFormat.SpeechAudioFormatInfo]::new(
            16000,
            [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,
            [System.Speech.AudioFormat.AudioChannel]::Mono
        )
        $synth.SetOutputToWaveFile($Path, $format)
        $synth.Speak($Text) | Out-Null
        return $synth.Voice.Name
    } finally {
        $synth.Dispose()
    }
}

function Boost-WavPcm16 {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [double] $Gain
    )

    if ($Gain -le 1.0) {
        return
    }

    $bytes = [System.IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -lt 44) {
        return
    }
    $riff = [System.Text.Encoding]::ASCII.GetString($bytes, 0, 4)
    $wave = [System.Text.Encoding]::ASCII.GetString($bytes, 8, 4)
    if ($riff -ne "RIFF" -or $wave -ne "WAVE") {
        return
    }

    $offset = 12
    $bitsPerSample = $null
    $dataOffset = $null
    $dataSize = $null
    while ($offset + 8 -le $bytes.Length) {
        $chunkId = [System.Text.Encoding]::ASCII.GetString($bytes, $offset, 4)
        $chunkSize = [BitConverter]::ToInt32($bytes, $offset + 4)
        $chunkDataOffset = $offset + 8
        if ($chunkSize -lt 0 -or $chunkDataOffset + $chunkSize -gt $bytes.Length) {
            break
        }
        if ($chunkId -eq "fmt " -and $chunkSize -ge 16) {
            $audioFormat = [BitConverter]::ToInt16($bytes, $chunkDataOffset)
            $bitsPerSample = [BitConverter]::ToInt16($bytes, $chunkDataOffset + 14)
            if ($audioFormat -ne 1) {
                return
            }
        } elseif ($chunkId -eq "data") {
            $dataOffset = $chunkDataOffset
            $dataSize = $chunkSize
        }
        $offset = $chunkDataOffset + $chunkSize
        if (($chunkSize % 2) -eq 1) {
            $offset += 1
        }
    }
    if ($bitsPerSample -ne 16 -or $null -eq $dataOffset -or $null -eq $dataSize) {
        return
    }

    $peak = 0
    for ($i = $dataOffset; $i + 1 -lt ($dataOffset + $dataSize); $i += 2) {
        $sample = [BitConverter]::ToInt16($bytes, $i)
        $abs = [Math]::Abs([int]$sample)
        if ($abs -gt $peak) {
            $peak = $abs
        }
    }
    if ($peak -le 0) {
        return
    }

    $targetPeak = 26000.0
    $effectiveGain = [Math]::Min($Gain, $targetPeak / [double]$peak)
    if ($effectiveGain -le 0.0) {
        return
    }
    Write-Host ("TTS_GAIN: requested={0:0.###} effective={1:0.###} peak={2} target_peak={3}" -f $Gain, $effectiveGain, $peak, [int]$targetPeak)

    for ($i = $dataOffset; $i + 1 -lt ($dataOffset + $dataSize); $i += 2) {
        $sample = [BitConverter]::ToInt16($bytes, $i)
        $scaled = [int][Math]::Round($sample * $effectiveGain)
        if ($scaled -gt [int16]::MaxValue) {
            $scaled = [int16]::MaxValue
        } elseif ($scaled -lt [int16]::MinValue) {
            $scaled = [int16]::MinValue
        }
        [BitConverter]::GetBytes([int16]$scaled).CopyTo($bytes, $i)
    }
    [System.IO.File]::WriteAllBytes($Path, $bytes)
}

function Invoke-TtsPlaybackSync {
    param(
        [Parameter(Mandatory = $true)][string] $Text,
        [string] $PreferredVoice,
        [int] $Rate = 0
    )

    Add-Type -AssemblyName System.Speech
    $synth = [System.Speech.Synthesis.SpeechSynthesizer]::new()
    try {
        $synth.Volume = 100
        $synth.Rate = [Math]::Max(-10, [Math]::Min(10, $Rate))
        if (-not [string]::IsNullOrWhiteSpace($PreferredVoice)) {
            $voices = @($synth.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name })
            if ($voices -contains $PreferredVoice) {
                $synth.SelectVoice($PreferredVoice)
            }
        }
        $synth.SetOutputToDefaultAudioDevice()
        $synth.Speak($Text) | Out-Null
    } finally {
        $synth.Dispose()
    }
}

function Start-WavPlaybackOnce {
    param([string] $Path)
    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $null
    }

    Add-Type -AssemblyName System.Windows.Extensions -ErrorAction SilentlyContinue
    $player = [System.Media.SoundPlayer]::new($Path)
    $player.Load()
    $player.PlaySync()
    return $player
}

function Stop-WavPlaybackLoop {
    param($Player)
    if ($null -eq $Player) {
        return
    }
    try {
        $Player.Stop()
    } finally {
        $Player.Dispose()
    }
}

function New-PlaybackFixture {
    param(
        [Parameter(Mandatory = $true)][string] $CaseId,
        [Parameter(Mandatory = $true)][int] $Round,
        [Parameter(Mandatory = $true)][string] $Text
    )

    $wavPath = Join-Path $outputDir ("{0}-round{1}-tts.wav" -f $CaseId.ToLowerInvariant(), $Round)
    $voiceName = $null
    if (-not $DisableTtsPlayback) {
        $voiceName = New-TtsWav -Text $Text -Path $wavPath -VoiceName $TtsVoiceName -Rate $TtsRate
        Boost-WavPcm16 -Path $wavPath -Gain $TtsGain
    }

    [pscustomobject]@{
        expected_text = $Text
        playback_wav = if ($DisableTtsPlayback) { $null } else { $wavPath }
        playback_text = $Text
        tts_voice = $voiceName
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

function Wait-ListenerLogPattern {
    param(
        [Parameter(Mandatory = $true)][string] $Label,
        [Parameter(Mandatory = $true)][string] $LogPath,
        [Parameter(Mandatory = $true)][int64] $StartOffset,
        [Parameter(Mandatory = $true)][string] $Pattern,
        [Parameter(Mandatory = $true)][int] $TimeoutMs
    )

    $deadline = [DateTime]::UtcNow.AddMilliseconds($TimeoutMs)
    $latest = ""
    while ([DateTime]::UtcNow -lt $deadline) {
        $latest = Read-LogTail -Path $LogPath -Offset $StartOffset
        $match = [regex]::Match($latest, $Pattern, [System.Text.RegularExpressions.RegexOptions]::Singleline)
        if ($match.Success) {
            return $match
        }
        Start-Sleep -Milliseconds 200
    }

    $snippet = $latest
    if ($snippet.Length -gt 2000) {
        $snippet = $snippet.Substring($snippet.Length - 2000)
    }
    throw "$Label timed out waiting for BLE ready before playback after $TimeoutMs ms. Log tail:`n$snippet"
}

function Invoke-CompanionBleRecovery {
    param(
        [Parameter(Mandatory = $true)][string] $Label,
        [Parameter(Mandatory = $true)][string] $ListenerExePath
    )

    if ($BleCleanupStopTimeoutMs -gt 0) {
        try {
            Write-Host "RECOVERY: $Label sending embedded BLE control stop timeout_ms=$BleCleanupStopTimeoutMs"
            Set-CompanionTypeEnvironment -ReadyCommand "TYPE:READY" -StatsOnly $true
            & $ListenerExePath --send-embedded-audio-control-stop ([string]$BleCleanupStopTimeoutMs) | Out-Host
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "$Label recovery control stop exited with code $LASTEXITCODE"
            }
        } catch {
            Write-Warning "$Label recovery control stop failed: $($_.Exception.Message)"
        }
    }

    if ($BleRecoveryDelayMs -gt 0) {
        Start-Sleep -Milliseconds $BleRecoveryDelayMs
    }

    if ($BleRecoveryProbeTimeoutMs -gt 0) {
        try {
            Write-Host "RECOVERY: $Label probing embedded BLE notify timeout_ms=$BleRecoveryProbeTimeoutMs"
            Set-CompanionTypeEnvironment -ReadyCommand "TYPE:HB" -StatsOnly $true
            & $ListenerExePath --probe-embedded-audio-ble-subscription ([string]$BleRecoveryProbeTimeoutMs) | Out-Host
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "$Label recovery probe exited with code $LASTEXITCODE"
            }
        } catch {
            Write-Warning "$Label recovery probe failed: $($_.Exception.Message)"
        }
    }
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
        [bool] $StatsOnly = $true,
        [string] $PlaybackWav,
        [string] $PlaybackText,
        [string] $TtsVoice
    )

    $offset = Get-LogOffset -Path $LogPath
    $argumentList = $Arguments -join " "
    Write-Host "RUN: $ListenerExePath $argumentList"
    Set-CompanionTypeEnvironment -ReadyCommand $ReadyCommand -StatsOnly $StatsOnly
    $player = $null
    $playbackVolumeSnapshot = $null
    $process = Start-Process -FilePath $ListenerExePath -ArgumentList $Arguments -PassThru -WindowStyle Hidden
    try {
        if (-not [string]::IsNullOrWhiteSpace($PlaybackWav)) {
            $readyTimeoutMs = [Math]::Min([Math]::Max($TimeoutMs, 10000), 30000)
            [void](Wait-ListenerLogPattern `
                -Label "$Label playback gate" `
                -LogPath $LogPath `
                -StartOffset $offset `
                -Pattern "Type heartbeat ready sent" `
                -TimeoutMs $readyTimeoutMs)
            if ($PrePlaybackDelayMs -gt 0) {
                Start-Sleep -Milliseconds $PrePlaybackDelayMs
            }
            Write-Host "PLAY: mode=$PlaybackMode wav=$PlaybackWav text=$PlaybackText"
            $playbackVolumeSnapshot = Set-CompanionPlaybackVolume -Percent $PlaybackVolumePercent
            if ($PlaybackMode -eq "speech") {
                Invoke-TtsPlaybackSync -Text $PlaybackText -PreferredVoice $TtsVoice -Rate $TtsRate
            } else {
                $player = Start-WavPlaybackOnce -Path $PlaybackWav
            }
        }
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
    } finally {
        Stop-WavPlaybackLoop -Player $player
        Restore-CompanionPlaybackVolume -Snapshot $playbackVolumeSnapshot
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
        [bool] $StatsOnly = $true,
        [string] $PlaybackWav,
        [string] $PlaybackText,
        [string] $TtsVoice
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
                -StatsOnly $StatsOnly `
                -PlaybackWav $PlaybackWav `
                -PlaybackText $PlaybackText `
                -TtsVoice $TtsVoice
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
            Invoke-CompanionBleRecovery -Label "$Label attempt $attempt" -ListenerExePath $ListenerExePath | Out-Null
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
        [bool] $RequireText = $false,
        [bool] $GateTranscriptAccuracy = $false,
        [string] $ExpectedText,
        [string] $PlaybackWav,
        [string] $TtsVoice
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
        $transcript = $null
        if ($json.PSObject.Properties.Name -contains "transcript") {
            $transcript = $json.transcript
        }
        $finalText = if ($transcript) { [string] $transcript.finalText } else { "" }
        $rawTranscript = if ($transcript) { [string] $transcript.rawTranscript } else { "" }
        $transcriptError = if ($transcript) { $transcript.errorCode } else { $null }
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
    $accuracyReport = if (-not [string]::IsNullOrWhiteSpace($ExpectedText)) {
        Measure-TranscriptAccuracy -Expected $ExpectedText -Transcript $finalText
    } else {
        $null
    }
    $accuracy = if ($accuracyReport) { [double] $accuracyReport.accuracy } else { $null }
    $accuracyOk = $null -eq $accuracy -or $accuracy -ge $MinTranscriptAccuracy
    $textOk = -not $RequireText -or (
        $finalTextChars -ge $MinFinalTextChars -and
        (-not $GateTranscriptAccuracy -or $accuracyOk)
    )
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
        expected_text = $ExpectedText
        normalized_expected = if ($accuracyReport) { [string] $accuracyReport.normalized_expected } else { "" }
        normalized_transcript = if ($accuracyReport) { [string] $accuracyReport.normalized_transcript } else { "" }
        transcript_accuracy = $accuracy
        transcript_accuracy_gate = $GateTranscriptAccuracy
        transcript_accuracy_pass = $accuracyOk
        transcript_cer = if ($accuracyReport) { [double] $accuracyReport.cer } else { $null }
        playback_wav = $PlaybackWav
        tts_voice = $TtsVoice
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
    $probeLabel = if ($SkipInitialProbe) { "skipped" } else { "$ProbeTimeoutMs ms" }
    Write-Host "This script will run probe=$probeLabel, A1=$A1Rounds rounds x $A1TimeoutMs ms, A2=$A2TimeoutMs ms."
    Write-Host "A1 text gate: $RequireA1Text; A2 text gate: $RequireA2Text (min final chars: $MinFinalTextChars)."
    Write-Host "BLE failure recovery: stop_timeout=$BleCleanupStopTimeoutMs ms, delay=$BleRecoveryDelayMs ms, probe=$BleRecoveryProbeTimeoutMs ms."
    Write-Host "Automatic TTS playback: $(-not [bool]$DisableTtsPlayback). A2 text: $A2PlaybackText"
    $ttsVoiceLabel = if ([string]::IsNullOrWhiteSpace($TtsVoiceName)) { "auto zh" } else { $TtsVoiceName }
    Write-Host "TTS voice/gain/rate: voice=$ttsVoiceLabel, gain=$TtsGain, rate=$TtsRate; min transcript accuracy=$MinTranscriptAccuracy."
    Write-Host "Transcript accuracy gates: A1=$([bool]$GateA1TranscriptAccuracy), A2=$([bool]$GateA2TranscriptAccuracy)."
    Write-Host "Playback mode: $PlaybackMode; pre-playback delay: $PrePlaybackDelayMs ms."
    Write-Host "Playback volume percent: $PlaybackVolumePercent (restored after each run unless -KeepPlaybackVolume)."
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
        -Message "请把电脑扬声器靠近 Companion 麦克风，保持周围安静。点击 OK 后会自动播放几段中文，并通过 Companion 蓝牙上传识别；过程中不要按键、不要拔线、不要关闭 Listener Type。若没有听到声音、设备断开或灯效异常，等脚本结束后告诉 Codex。"
}

$startedAt = (Get-Date).ToUniversalTime().ToString("o")
$results = [System.Collections.Generic.List[object]]::new()
$retries = [System.Collections.Generic.List[object]]::new()
$errors = [System.Collections.Generic.List[string]]::new()
$warnings = [System.Collections.Generic.List[string]]::new()

try {
    $probePass = "probe-embedded-audio-ble-subscription PASS"
    $probeFail = "probe-embedded-audio-ble-subscription failed: (?<error>.*)"
    if ($SkipInitialProbe) {
        $warnings.Add("Initial BLE notify probe skipped; A1/A2 streams perform the real scan/connect path.") | Out-Null
        Write-Host "SKIP: initial BLE notify probe skipped; A1/A2 streams will validate scan/connect."
    } else {
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
            -RetryRecords $retries `
            -ReadyCommand "TYPE:HB" `
            -StatsOnly $true)
    }

    $streamPass = "embedded_audio_ble_(?:stream|once)_result_json=(?<json>\{[^\r\n]*\})|submit-embedded-audio-ble-(?:stream|once) done: pcm_bytes=(?<pcm>\d+) missing_packets=(?<missing>\d+)"
    $streamFail = "submit-embedded-audio-ble-(?:stream|once) failed: (?<error>.*)"

    for ($round = 1; $round -le $A1Rounds; $round++) {
        if ($round -gt 1 -and $RoundCooldownMs -gt 0) {
            Start-Sleep -Milliseconds $RoundCooldownMs
        }
        $fixture = if ($RequireA1Text) {
            New-PlaybackFixture -CaseId "A1" -Round $round -Text (Get-A1PlaybackText -Round $round)
        } else {
            $null
        }
        $a1BleCommand = if ($RequireA1Text) { "--submit-embedded-audio-ble-once" } else { "--submit-embedded-audio-ble-stream" }
        $attempt = Invoke-ListenerCliWithRetry `
            -Label "A1 round $round" `
            -Arguments @($a1BleCommand, [string]$A1TimeoutMs) `
            -TimeoutMs $A1TimeoutMs `
            -PassPattern $streamPass `
            -FailPattern $streamFail `
            -ListenerExePath $listenerExePath `
            -LogPath $logPath `
            -MaxRetries $CliRetries `
            -DelayMs $RetryDelayMs `
            -RetryRecords $retries `
            -ReadyCommand $(if ($RequireA1Text) { "TYPE:READY:A1" } else { "TYPE:READY" }) `
            -StatsOnly (-not $RequireA1Text) `
            -PlaybackWav $(if ($fixture) { $fixture.playback_wav } else { $null }) `
            -PlaybackText $(if ($fixture) { $fixture.playback_text } else { $null }) `
            -TtsVoice $(if ($fixture) { $fixture.tts_voice } else { $null })
        $result = New-StreamResult `
            -CaseId "A1" `
            -Round $round `
            -Match $attempt.match `
            -Attempts $attempt.attempts `
            -RequireText $RequireA1Text `
            -GateTranscriptAccuracy ([bool]$GateA1TranscriptAccuracy) `
            -ExpectedText $(if ($fixture) { $fixture.expected_text } else { $null }) `
            -PlaybackWav $(if ($fixture) { $fixture.playback_wav } else { $null }) `
            -TtsVoice $(if ($fixture) { $fixture.tts_voice } else { $null })
        $results.Add($result) | Out-Null
        if ($result.status -ne "PASS") {
            if ($result.missing_packets -gt $MaxMissingPackets) {
                $errors.Add("A1 round $round missing_packets=$($result.missing_packets) > $MaxMissingPackets") | Out-Null
            }
            if ($RequireA1Text -and $result.final_text_chars -lt $MinFinalTextChars) {
                $errors.Add("A1 round $round final_text_chars=$($result.final_text_chars) < $MinFinalTextChars") | Out-Null
            }
            if ($RequireA1Text -and [bool]$GateA1TranscriptAccuracy -and ($null -ne $result.transcript_accuracy) -and $result.transcript_accuracy -lt $MinTranscriptAccuracy) {
                $errors.Add("A1 round $round transcript_accuracy=$($result.transcript_accuracy) < $MinTranscriptAccuracy expected=`"$($result.expected_text)`" final=`"$($result.final_text)`"") | Out-Null
            }
        }
        if ($RequireA1Text -and -not [bool]$GateA1TranscriptAccuracy -and ($null -ne $result.transcript_accuracy) -and $result.transcript_accuracy -lt $MinTranscriptAccuracy) {
            $warnings.Add("A1 round $round transcript_accuracy=$($result.transcript_accuracy) < $MinTranscriptAccuracy expected=`"$($result.expected_text)`" final=`"$($result.final_text)`"") | Out-Null
        }
    }

    if ($RoundCooldownMs -gt 0) {
        Start-Sleep -Milliseconds $RoundCooldownMs
    }
    $a2Fixture = if ($RequireA2Text) {
        New-PlaybackFixture -CaseId "A2" -Round 1 -Text $A2PlaybackText
    } else {
        $null
    }
    $a2BleCommand = if ($RequireA2Text) { "--submit-embedded-audio-ble-once" } else { "--submit-embedded-audio-ble-stream" }
    $a2Attempt = Invoke-ListenerCliWithRetry `
        -Label "A2" `
        -Arguments @($a2BleCommand, [string]$A2TimeoutMs) `
        -TimeoutMs $A2TimeoutMs `
        -PassPattern $streamPass `
        -FailPattern $streamFail `
        -ListenerExePath $listenerExePath `
        -LogPath $logPath `
        -MaxRetries $CliRetries `
        -DelayMs $RetryDelayMs `
        -RetryRecords $retries `
        -ReadyCommand $(if ($RequireA2Text) { "TYPE:READY:A2" } else { "TYPE:READY" }) `
        -StatsOnly (-not $RequireA2Text) `
        -PlaybackWav $(if ($a2Fixture) { $a2Fixture.playback_wav } else { $null }) `
        -PlaybackText $(if ($a2Fixture) { $a2Fixture.playback_text } else { $null }) `
        -TtsVoice $(if ($a2Fixture) { $a2Fixture.tts_voice } else { $null })
    $a2Result = New-StreamResult `
        -CaseId "A2" `
        -Round 1 `
        -Match $a2Attempt.match `
        -Attempts $a2Attempt.attempts `
        -RequireText $RequireA2Text `
        -GateTranscriptAccuracy ([bool]$GateA2TranscriptAccuracy) `
        -ExpectedText $(if ($a2Fixture) { $a2Fixture.expected_text } else { $null }) `
        -PlaybackWav $(if ($a2Fixture) { $a2Fixture.playback_wav } else { $null }) `
        -TtsVoice $(if ($a2Fixture) { $a2Fixture.tts_voice } else { $null })
    $results.Add($a2Result) | Out-Null
    if ($a2Result.status -ne "PASS") {
        if ($a2Result.missing_packets -gt $MaxMissingPackets) {
            $errors.Add("A2 missing_packets=$($a2Result.missing_packets) > $MaxMissingPackets") | Out-Null
        }
        if ($RequireA2Text -and $a2Result.final_text_chars -lt $MinFinalTextChars) {
            $errors.Add("A2 final_text_chars=$($a2Result.final_text_chars) < $MinFinalTextChars") | Out-Null
        }
        if ($RequireA2Text -and [bool]$GateA2TranscriptAccuracy -and ($null -ne $a2Result.transcript_accuracy) -and $a2Result.transcript_accuracy -lt $MinTranscriptAccuracy) {
            $errors.Add("A2 transcript_accuracy=$($a2Result.transcript_accuracy) < $MinTranscriptAccuracy expected=`"$($a2Result.expected_text)`" final=`"$($a2Result.final_text)`"") | Out-Null
        }
    }
    if ($RequireA2Text -and -not [bool]$GateA2TranscriptAccuracy -and ($null -ne $a2Result.transcript_accuracy) -and $a2Result.transcript_accuracy -lt $MinTranscriptAccuracy) {
        $warnings.Add("A2 transcript_accuracy=$($a2Result.transcript_accuracy) < $MinTranscriptAccuracy expected=`"$($a2Result.expected_text)`" final=`"$($a2Result.final_text)`"") | Out-Null
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
    skip_initial_probe = [bool]$SkipInitialProbe
    a1_rounds = $A1Rounds
    a1_timeout_ms = $A1TimeoutMs
    a2_timeout_ms = $A2TimeoutMs
    max_missing_packets = $MaxMissingPackets
    cli_retries = $CliRetries
    retry_delay_ms = $RetryDelayMs
    ble_cleanup_stop_timeout_ms = $BleCleanupStopTimeoutMs
    ble_recovery_delay_ms = $BleRecoveryDelayMs
    ble_recovery_probe_timeout_ms = $BleRecoveryProbeTimeoutMs
    round_cooldown_ms = $RoundCooldownMs
    pre_playback_delay_ms = $PrePlaybackDelayMs
    playback_mode = $PlaybackMode
    require_a1_text = $RequireA1Text
    require_a2_text = $RequireA2Text
    min_final_text_chars = $MinFinalTextChars
    min_transcript_accuracy = $MinTranscriptAccuracy
    gate_a1_transcript_accuracy = [bool]$GateA1TranscriptAccuracy
    gate_a2_transcript_accuracy = [bool]$GateA2TranscriptAccuracy
    automatic_tts_playback = -not [bool]$DisableTtsPlayback
    tts_voice_requested = $TtsVoiceName
    tts_gain = $TtsGain
    tts_rate = $TtsRate
    playback_volume_percent = $PlaybackVolumePercent
    keep_playback_volume = [bool]$KeepPlaybackVolume
    text_ble_mode = "batch-once"
    a1_playback_texts = @($A1PlaybackTexts)
    a2_playback_text = $A2PlaybackText
    prompt_operator = [bool]$PromptOperator
    results = @($results)
    retries = @($retries)
    warnings = @($warnings)
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
    "- BLE failure recovery: stop_timeout=$BleCleanupStopTimeoutMs ms, delay=$BleRecoveryDelayMs ms, probe=$BleRecoveryProbeTimeoutMs ms",
    "- Min transcript accuracy: $MinTranscriptAccuracy",
    "- Transcript accuracy gates: A1=$([bool]$GateA1TranscriptAccuracy), A2=$([bool]$GateA2TranscriptAccuracy)",
    "- Playback mode: $PlaybackMode",
    "- Pre-playback delay: $PrePlaybackDelayMs ms",
    "- Automatic TTS playback: $(-not [bool]$DisableTtsPlayback)",
    "- TTS voice requested: $TtsVoiceName",
    "- TTS gain: $TtsGain",
    "- TTS rate: $TtsRate",
    "",
    "## Results"
)
foreach ($item in $results) {
    $textPart = if ($item.final_text_chars -gt 0) { ", final_text_chars=$($item.final_text_chars), final_text=`"$($item.final_text)`"" } else { "" }
    $expectedPart = if (-not [string]::IsNullOrWhiteSpace($item.expected_text)) { ", expected_text=`"$($item.expected_text)`"" } else { "" }
    $accuracyPart = if ($null -ne $item.transcript_accuracy) { ", accuracy=$($item.transcript_accuracy)" } else { "" }
    $accuracyGatePart = if ($null -ne $item.transcript_accuracy) { ", accuracy_gate=$($item.transcript_accuracy_gate)" } else { "" }
    $md += "- $($item.case) round $($item.round): $($item.status), pcm=$($item.pcm_bytes), missing=$($item.missing_packets), attempts=$($item.attempts)$textPart$expectedPart$accuracyPart$accuracyGatePart"
}
if ($retries.Count -gt 0) {
    $md += ""
    $md += "## Retries"
    foreach ($retryItem in $retries) {
        $md += "- $($retryItem.label) attempt $($retryItem.attempt): retry_after_ms=$($retryItem.retry_after_ms)"
    }
}
if ($warnings.Count -gt 0) {
    $md += ""
    $md += "## Warnings"
    foreach ($warningItem in $warnings) {
        $md += "- $warningItem"
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
