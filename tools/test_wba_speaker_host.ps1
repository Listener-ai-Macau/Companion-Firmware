param(
    [string]$Root,
    [string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not $Root) { $Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path }
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $Root '.cache\wba-speaker-host' }
New-Item -ItemType Directory -Force $OutputDirectory | Out-Null

$vcvars = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
if (-not (Test-Path -LiteralPath $vcvars)) { throw 'MSVC vcvars64 unavailable' }

$playback = Join-Path $Root 'app\companion_pendant\playback'
$testSource = Join-Path $playback 'tests\test_speaker_playback.c'
$source = Join-Path $playback 'speaker_playback.c'
$exe = Join-Path $OutputDirectory 'test_wba_speaker.exe'
$compileLog = Join-Path $OutputDirectory 'compile.log'
$runLog = Join-Path $OutputDirectory 'run.log'
$command = 'call "' + $vcvars + '" >nul && cl /nologo /std:c11 /W4 /WX /utf-8 /I"' + $playback + '" "' + $source + '" "' + $testSource + '" /Fe:"' + $exe + '"'

& $env:ComSpec /d /s /c $command 2>&1 | Set-Content -Encoding utf8 $compileLog
if ($LASTEXITCODE -ne 0) { throw "speaker host compile failed; see $compileLog" }
& $exe 2>&1 | Tee-Object -FilePath $runLog
if ($LASTEXITCODE -ne 0) { throw "speaker host test failed; see $runLog" }

$arm = Get-Command arm-none-eabi-gcc -ErrorAction SilentlyContinue
if ($arm) {
    $object = Join-Path $OutputDirectory 'speaker_playback_m33.o'
    & $arm.Source -std=c11 -mcpu=cortex-m33 -mthumb -mfloat-abi=soft -ffreestanding -fno-common -Wall -Wextra -Werror -Wconversion -Wshadow -Wdouble-promotion -Wformat=2 -pedantic -I$playback -c $source -o $object 2>&1 | Add-Content -Encoding utf8 $compileLog
    if ($LASTEXITCODE -ne 0) { throw "speaker Cortex-M33 compile failed; see $compileLog" }
}

[ordered]@{
    result = 'PASS_PREHARDWARE_SOFTWARE_ONLY'
    hardware_playback = 'NOT_RUN_HARDWARE_NOT_AVAILABLE'
    max98357a = 'callback contract only; SD_MODE and I2S owned by CubeWBA/TCA6408 board glue'
    host_test_sha256 = (Get-FileHash $exe -Algorithm SHA256).Hash.ToUpperInvariant()
    m33_compile = [bool]$arm
} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $OutputDirectory 'result.json')
