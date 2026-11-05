# COMP-REQ-602 host-side audio CODEC accuracy simulation.
#
# This is the ONLY recording/audio accuracy dimension that is machine-runnable
# OFFLINE. It compiles the canonical denzic-platform lossless codec test
# (third_party/denzic-platform/audio/embedded/c/tests/test_denzic_audio_lossless_v1.c)
# + the real codec sources with MSVC and RUNS it. The test feeds synthetic PCM
# ("machine sound": pinned i16 extremes, a speech-like polynomial, an LCG
# pseudo-random walk) through encode -> decode and asserts a byte-for-byte
# lossless round-trip (memcmp(decoded, pcm) == 0).
#
# IMPORTANT SCOPE: this proves the digital audio CODEC is bit-exact lossless.
# It is NOT "recording accuracy via the computer's sound" -- that test is
# tools/verify_companion_type_a1_a2.ps1 (PC-speaker TTS -> device PDM mic ->
# BLE pull -> ASR -> transcript accuracy), which is HARDWARE-only and stays
# CLOSED_UNPROVEN offline. No microphone, speaker, or ASR is exercised here.
#
# Compiled in an isolated cache dir; the denzic-platform submodule tree is not
# modified. No hardware, no flash, no real BLE/OTA.

param(
    [string]$Root,
    [string]$OutRoot = 'docs/validation/comp-req-602-platform-adapter-closure/transport-sim/audio_codec'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not $Root) { $Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path }
$Root = (Resolve-Path $Root).Path
# Honor an absolute OutRoot so the receipt can land in the 602 worktree while
# sources are read from a different checkout (e.g. the populated main checkout).
if ([System.IO.Path]::IsPathRooted($OutRoot)) { $Out = $OutRoot } else { $Out = Join-Path $Root $OutRoot }
New-Item -ItemType Directory -Force $Out | Out-Null

$vcvars = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
if (-not (Test-Path -LiteralPath $vcvars)) {
    $where = Get-Command vswhere.exe -ErrorAction SilentlyContinue
    if ($where) {
        $install = & $where.Source -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2>$null | Select-Object -First 1
        if ($install) { $vcvars = Join-Path $install 'VC\Auxiliary\Build\vcvars64.bat' }
    }
}
if (-not (Test-Path -LiteralPath $vcvars)) { throw 'MSVC vcvars64 unavailable' }

$audio = Join-Path $Root 'third_party\denzic-platform\audio\embedded\c'
$iso = Join-Path $Root '.cache\denzic-audio-lossless-test'
New-Item -ItemType Directory -Force $iso | Out-Null
$exe = Join-Path $iso 'test.exe'

$sources = @(
    (Join-Path $audio 'tests\test_denzic_audio_lossless_v1.c'),
    (Join-Path $audio 'src\denzic_audio_lossless_v1.c'),
    (Join-Path $audio 'src\denzic_audio_recording_v1.c'),
    (Join-Path $audio 'src\denzic_audio_transport_v1.c')
) | ForEach-Object { '"' + $_ + '"' }
$srcQuoted = $sources -join ' '
$cmd = 'call "' + $vcvars + '" >nul && cd /d "' + $iso + '" && cl /nologo /O2 /W4 /wd4100 /wd4244 /wd4245 /wd4701 /std:c11 /I"' + (Join-Path $audio 'include') + '" ' + $srcQuoted + ' /Fe:"test.exe"'
$compileLog = Join-Path $Out 'compile.log'
& $env:ComSpec /d /s /c $cmd 2>&1 | Set-Content -Encoding utf8 $compileLog
if ($LASTEXITCODE -ne 0) { throw "audio codec accuracy compile failed (exit $LASTEXITCODE); see $compileLog" }

$stdout = & $exe 2>&1 | Out-String
$code = $LASTEXITCODE

[ordered]@{
    status            = if ($code -eq 0) { 'MACHINE_PASS_PENDING_FOCUSED_HUMAN_RECORDING_ACCURACY' } else { 'NO_GO' }
    auto_pass_fail    = if ($code -eq 0) { 'PASS (exit 0 = every lossless round-trip assert held)' } else { 'FAIL (exit ' + $code + ')' }
    exit_code         = $code
    scenario          = 'audio codec bit-exact lossless round-trip (host simulation, synthetic PCM = machine sound)'
    scope_note        = 'Proves the digital audio CODEC is bit-exact lossless (encode->decode == original PCM). NOT recording accuracy: no microphone, speaker, or ASR. The PC-speaker TTS -> mic -> ASR transcript-accuracy test (verify_companion_type_a1_a2.ps1) is HARDWARE-only and CLOSED_UNPROVEN offline.'
    test_source       = 'third_party/denzic-platform/audio/embedded/c/tests/test_denzic_audio_lossless_v1.c'
    accuracy_claim    = 'memcmp(decoded, pcm, pcm_bytes) == 0 for all fixtures (assert-based; exit 0 = every round-trip held)'
    signals           = @('pinned i16 extremes', 'speech-like 112-sample polynomial', '200-sample LCG pseudo-random walk')
    must_not_claim    = @(
        'This is CODEC bit-exactness only; it is NOT recording or microphone accuracy.',
        'No microphone capture, no speaker playback, and no ASR transcript scoring happened here.',
        'The PC-speaker TTS -> device PDM mic -> BLE pull -> ASR transcript-accuracy gate (verify_companion_type_a1_a2.ps1, gate >=0.60) was NOT run; it is hardware-only and stays PENDING human.'
    )
    pending_human_acceptance = @(
        'Run tools\verify_companion_type_a1_a2.ps1 -Execute -WorkflowLockHeld: PC-speaker Chinese TTS -> device PDM mic -> BLE pull -> ASR -> transcript accuracy >=0.60 on real hardware (the real "电脑机械声音" recording-accuracy gate).'
    )
    stdout            = $stdout.Trim()
    root              = $Root
    executable_sha256 = (Get-FileHash $exe -Algorithm SHA256).Hash.ToUpper()
    compile_log_sha256 = (Get-FileHash $compileLog -Algorithm SHA256).Hash.ToUpper()
    runner_sha256     = (Get-FileHash $PSCommandPath -Algorithm SHA256).Hash.ToUpper()
    validation_commands = @(
        'pwsh -NoProfile -File tools\run_comp_req_602_audio_codec_accuracy_sim.ps1 -Root <firmware-root-with-denzic-platform-populated>'
    )
    checkonly         = [ordered]@{ hardware_contact=0; programmer=0; serial=0; write=0; reset=0; refresh=0; popup=0; retry=0 }
    side_effects      = [ordered]@{ hardware=0; ble_write=0; ota_transfer=0; ota_apply=0; popup=0; push=0 }
    physical_scope    = 'closed_unproven'
} | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 (Join-Path $Out 'result.json')

if ($code -ne 0) { exit 1 }
