param(
    [string]$Root,
    [string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not $Root) { $Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path }
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $Root '.cache\wba-speaker-product-interfaces' }
New-Item -ItemType Directory -Force $OutputDirectory | Out-Null

$vcvars = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
if (-not (Test-Path -LiteralPath $vcvars)) { throw 'MSVC vcvars64 unavailable' }
$v1 = Join-Path $Root 'app\companion_pendant\v1_features'
$power = Join-Path $Root 'app\companion_pendant\power'
$source = Join-Path $v1 'companion_v1_features.c'
$powerSource = Join-Path $power 'power_policy.c'
$test = Join-Path $v1 'tests\test_companion_v1_peripherals.c'
$exe = Join-Path $OutputDirectory 'test_wba_speaker_product_interfaces.exe'
$compileLog = Join-Path $OutputDirectory 'compile.log'
$runLog = Join-Path $OutputDirectory 'run.log'
$command = 'call "' + $vcvars + '" >nul && cl /nologo /std:c11 /W4 /WX /utf-8 /I"' + $v1 + '" /I"' + $power + '" "' + $source + '" "' + $powerSource + '" "' + $test + '" /Fe:"' + $exe + '"'

& $env:ComSpec /d /s /c $command 2>&1 | Set-Content -Encoding utf8 $compileLog
if ($LASTEXITCODE -ne 0) { throw "V1 peripheral interface compile failed; see $compileLog" }
& $exe 2>&1 | Tee-Object -FilePath $runLog
if ($LASTEXITCODE -ne 0) { throw "V1 peripheral interface test failed; see $runLog" }

$arm = Get-Command arm-none-eabi-gcc -ErrorAction SilentlyContinue
if ($arm) {
    foreach ($item in @($source, $powerSource)) {
        $object = Join-Path $OutputDirectory ([IO.Path]::GetFileNameWithoutExtension($item) + '_m33.o')
        & $arm.Source -std=c11 -mcpu=cortex-m33 -mthumb -mfloat-abi=soft -ffreestanding -fno-common -Wall -Wextra -Werror -Wconversion -Wshadow -Wdouble-promotion -Wformat=2 -pedantic -I$v1 -I$power -c $item -o $object 2>&1 | Add-Content -Encoding utf8 $compileLog
        if ($LASTEXITCODE -ne 0) { throw "Cortex-M33 compile failed for $item; see $compileLog" }
    }
}

[ordered]@{
    result = 'PASS_PREHARDWARE_SOFTWARE_ONLY'
    host_contract = 'V1 backend/default/wire-layout/power independence'
    m33_compile = [bool]$arm
    hardware_gatt = 'NOT_RUN'
    executable_sha256 = (Get-FileHash $exe -Algorithm SHA256).Hash.ToUpperInvariant()
} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $OutputDirectory 'result.json')
