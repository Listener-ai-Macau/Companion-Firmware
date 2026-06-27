param(
    [string]$ImagePath = (Join-Path $PSScriptRoot '..\cubeide\Companion_Nucleo_WB55RG_Bringup\build\Companion_Nucleo_WB55RG_Bringup.hex'),
    [string]$ProgrammerRoot = 'C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins'
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $ImagePath)) {
    throw "Image not found: $ImagePath"
}

$programmer = Get-ChildItem -LiteralPath $ProgrammerRoot -Recurse -Filter STM32_Programmer_CLI.exe |
    Select-Object -First 1 -ExpandProperty FullName
if (-not $programmer) {
    throw "STM32_Programmer_CLI.exe not found under $ProgrammerRoot"
}

& $programmer -c port=SWD mode=UR reset=HWrst freq=4000 -w $ImagePath -v -rst
if ($LASTEXITCODE -ne 0) {
    throw "flash failed with exit code $LASTEXITCODE"
}
