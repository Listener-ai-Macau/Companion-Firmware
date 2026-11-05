param(
    [string]$Root,
    [string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not $Root) { $Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path }
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $Root '.cache\wba-microphone-hal' }
New-Item -ItemType Directory -Force $OutputDirectory | Out-Null

$arm = Get-Command arm-none-eabi-gcc -ErrorAction Stop
$cube = Join-Path $Root '.cache\deps\STM32CubeWBA'
$platform = Join-Path $Root 'platform\stm32wba55_companion_v11'
$recording = Join-Path $Root 'app\companion_pendant\recording'
$source = Join-Path $platform 'microphone_hal.c'
$portableSource = Join-Path $recording 'wba_pdm_capture.c'
$compileLog = Join-Path $OutputDirectory 'compile.log'
$object = Join-Path $OutputDirectory 'microphone_hal.o'
$portableObject = Join-Path $OutputDirectory 'wba_pdm_capture.o'

$common = @(
    '-std=c11', '-mcpu=cortex-m33', '-mthumb', '-mfloat-abi=soft',
    '-DSTM32WBA55xx', '-DUSE_HAL_DRIVER', '-ffreestanding', '-fno-common',
    '-Wall', '-Wextra', '-Werror', '-Wconversion', '-Wshadow',
    '-Wdouble-promotion', '-Wformat=2', '-pedantic',
    "-I$platform", "-I$recording",
    '-isystem', (Join-Path $cube 'Drivers\STM32WBAxx_HAL_Driver\Inc'),
    '-isystem', (Join-Path $cube 'Drivers\CMSIS\Device\ST\STM32WBAxx\Include'),
    '-isystem', (Join-Path $cube 'Drivers\CMSIS\Include')
)

& $arm.Source @common -c $source -o $object 2>&1 | Set-Content -Encoding utf8 $compileLog
if ($LASTEXITCODE -ne 0) { throw "WBA microphone HAL compile failed; see $compileLog" }
& $arm.Source @common -c $portableSource -o $portableObject 2>&1 | Add-Content -Encoding utf8 $compileLog
if ($LASTEXITCODE -ne 0) { throw "portable PDM compile failed; see $compileLog" }

& (Join-Path $Root 'tools\test_wba_pdm_capture_host.ps1') -Root $Root -OutputDirectory (Join-Path $OutputDirectory 'processor')
if ($LASTEXITCODE -ne 0) { throw 'portable PDM host tests failed' }

[ordered]@{
    result = 'PASS_PREHARDWARE_SOFTWARE_ONLY'
    hardware_capture = 'NOT_RUN_BY_THIS_COMPILE_TEST'
    target = 'STM32WBA55xx SAI1A + GPDMA1 Channel1 linked-list circular'
    dma_geometry = '7680 bytes total; two 3840-byte/10ms halves; HAL size 3840 halfwords; guarded 256-byte copies'
    configured_sai_bit_clock_hz = 3071990
    configured_pdm_clock_hz = 1535995
    measured_pdm_clock_hz = $null
    raw_order = 'PENDING_FIRST_BOARD_PROBE'
    object_sha256 = (Get-FileHash $object -Algorithm SHA256).Hash.ToUpperInvariant()
} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $OutputDirectory 'result.json')
