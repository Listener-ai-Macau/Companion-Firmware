param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) { throw "Visual Studio C++ Build Tools are required." }

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$playback = Join-Path $repoRoot "app\companion_pendant\playback"
$feedbackSource = Join-Path $playback "audio_feedback.c"
$speakerSource = Join-Path $playback "speaker_playback.c"
$testSource = Join-Path $playback "tests\test_audio_feedback.c"
$outDir = Join-Path $repoRoot ".cache\wba-audio-feedback-host"
$exe = Join-Path $outDir "test_audio_feedback.exe"
$m33Feedback = Join-Path $outDir "audio_feedback_m33.o"
$result = Join-Path $outDir "result.json"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$command = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /I"{1}" "{2}" "{3}" "{4}" /Fe:"{5}"' -f `
    $vsDevCmd, $playback, $feedbackSource, $speakerSource, $testSource, $exe
& $env:ComSpec /d /s /c $command
if ($LASTEXITCODE -ne 0) { throw "Audio feedback host compile failed." }
$output = (& $exe | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $output -notlike "PASS:*") {
    throw "Audio feedback host test failed: $output"
}
Write-Host $output

$arm = Get-Command arm-none-eabi-gcc -ErrorAction Stop
& $arm.Source -std=c11 -mcpu=cortex-m33 -mthumb -mfloat-abi=soft `
    -ffreestanding -fno-common -Wall -Wextra -Werror -Wconversion -Wshadow `
    -Wdouble-promotion -Wformat=2 -pedantic -I$playback `
    -c $feedbackSource -o $m33Feedback
if ($LASTEXITCODE -ne 0) { throw "Audio feedback Cortex-M33 compile failed." }
$m33Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $m33Feedback).Hash

[ordered]@{
    schema_id = "companion.wba_audio_feedback_host.v1"
    status = "PASS_HOST_ONLY"
    hardware = "NOT_RUN"
    output = $output
    m33_object_sha256 = $m33Hash
    sources = [ordered]@{
        audio_feedback_c = (Get-FileHash -Algorithm SHA256 -LiteralPath $feedbackSource).Hash
        audio_feedback_h = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $playback "audio_feedback.h")).Hash
        test = (Get-FileHash -Algorithm SHA256 -LiteralPath $testSource).Hash
    }
} | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -LiteralPath $result
Write-Host "m33_object_sha256=$m33Hash"
Write-Host "result=$result"
