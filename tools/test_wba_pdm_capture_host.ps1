param(
    [string]$Root,
    [string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not $Root) { $Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path }
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $Root '.cache\wba-pdm-capture-host' }
New-Item -ItemType Directory -Force $OutputDirectory | Out-Null

$vcvars = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
if (-not (Test-Path -LiteralPath $vcvars)) { throw 'MSVC vcvars64 unavailable' }

$recording = Join-Path $Root 'app\companion_pendant\recording'
$testSource = Join-Path $recording 'tests\test_wba_pdm_capture.c'
$source = Join-Path $recording 'wba_pdm_capture.c'
$exe = Join-Path $OutputDirectory 'test_wba_pdm_capture.exe'
$compileLog = Join-Path $OutputDirectory 'compile.log'
$runLog = Join-Path $OutputDirectory 'run.log'
$command = 'call "' + $vcvars + '" >nul && cl /nologo /std:c11 /W4 /WX /utf-8 /I"' + $recording + '" "' + $source + '" "' + $testSource + '" /Fe:"' + $exe + '"'

& $env:ComSpec /d /s /c $command 2>&1 | Set-Content -Encoding utf8 $compileLog
if ($LASTEXITCODE -ne 0) { throw "PDM host compile failed; see $compileLog" }
& $exe 2>&1 | Tee-Object -FilePath $runLog
if ($LASTEXITCODE -ne 0) { throw "PDM host test failed; see $runLog" }

$forbidden = Select-String -LiteralPath $source -Pattern '\b(malloc|calloc|realloc|free)\s*\(' -AllMatches
if ($forbidden) { throw 'portable PDM capture layer must not allocate from the heap' }

$arm = Get-Command arm-none-eabi-gcc -ErrorAction SilentlyContinue
if ($arm) {
    $object = Join-Path $OutputDirectory 'wba_pdm_capture_m33.o'
    & $arm.Source -std=c11 -mcpu=cortex-m33 -mthumb -mfloat-abi=soft -ffreestanding -fno-common -Wall -Wextra -Werror -Wconversion -Wshadow -Wdouble-promotion -Wformat=2 -pedantic -I$recording -c $source -o $object 2>&1 | Add-Content -Encoding utf8 $compileLog
    if ($LASTEXITCODE -ne 0) { throw "PDM Cortex-M33 compile failed; see $compileLog" }
}

[ordered]@{
    result = 'PASS_PREHARDWARE_SOFTWARE_ONLY'
    hardware_capture = 'NOT_RUN_BY_THIS_HOST_TEST'
    sai_pdm = 'portable processing contract only; SAI1A, DMA, PA9 clock and PA10 data owned by CubeWBA board glue'
    raw_order = 'configurable; LEFT_RIGHT_BYTES versus RIGHT_LEFT_BYTES remains pending first-board probe'
    pdm_clock = 'processor supports 64/96/128; SPH0655 board uses normal-mode 1.536 MHz at decimation 96; physical clock not measured'
    host_test_sha256 = (Get-FileHash $exe -Algorithm SHA256).Hash.ToUpperInvariant()
    m33_compile = [bool]$arm
} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $OutputDirectory 'result.json')
