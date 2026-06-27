param(
    [string]$ProjectDir = (Join-Path $PSScriptRoot '..\cubeide\Companion_BLE_Audio_Fixture'),
    [string]$MakePath = 'C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.make.win32_2.2.100.202601091506\tools\bin\make.exe',
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $MakePath)) {
    throw "make.exe not found: $MakePath"
}
if (-not (Test-Path -LiteralPath $ProjectDir)) {
    throw "Project directory not found: $ProjectDir"
}

$makeArgs = @("-C", $ProjectDir)
if ($Force) {
    $makeArgs += "-B"
}

& $MakePath @makeArgs
if ($LASTEXITCODE -ne 0) {
    throw "Companion BLE audio fixture build failed with exit code $LASTEXITCODE"
}
