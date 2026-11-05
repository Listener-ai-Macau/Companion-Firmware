param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) {
    throw "Visual Studio vswhere.exe is required."
}
$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) {
    throw "Visual Studio C++ Build Tools are required."
}

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$driver = Join-Path $epaperRoot "ssd1681_wba.c"
$header = Join-Path $epaperRoot "ssd1681_wba.h"
$refreshPolicy = Join-Path $epaperRoot "refresh_policy.c"
$test = Join-Path $epaperRoot "tests\test_ssd1681_wba.c"
$outDir = Join-Path $repoRoot ".cache\wba-ssd1681-host"
$exe = Join-Path $outDir "test_wba_ssd1681.exe"
$result = Join-Path $outDir "result.json"
$m33Object = Join-Path $outDir "ssd1681_wba_m33.o"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$command = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /I"{1}" "{2}" "{3}" "{4}" /Fe:"{5}"' -f `
    $vsDevCmd, $epaperRoot, $driver, $refreshPolicy, $test, $exe
& $env:ComSpec /d /s /c $command
if ($LASTEXITCODE -ne 0) {
    throw "WBA SSD1681 host compile failed with exit code $LASTEXITCODE."
}
$output = (& $exe | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $output -notlike "PASS:*") {
    throw "WBA SSD1681 host test failed: $output"
}
Write-Host $output

$armGcc = Get-Command arm-none-eabi-gcc -ErrorAction SilentlyContinue
if ($null -eq $armGcc) {
    throw "arm-none-eabi-gcc is required for the Cortex-M33 compile check."
}
& $armGcc.Source -std=c11 -mcpu=cortex-m33 -mthumb -Wall -Wextra -Werror `
    -I $epaperRoot -c $driver -o $m33Object
if ($LASTEXITCODE -ne 0) {
    throw "WBA SSD1681 Cortex-M33 compile failed with exit code $LASTEXITCODE."
}
$m33Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $m33Object).Hash
Write-Host "m33_object_sha256=$m33Hash"

$hashes = [ordered]@{}
foreach ($path in @($driver, $header, $test)) {
    $name = [IO.Path]::GetFileName($path)
    $hashes[$name] = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash
}
[ordered]@{
    schema_id = "companion.wba_ssd1681_host.v1"
    status = "PASS_HOST_ONLY"
    hardware = "NOT_RUN"
    reset_net = "HARDWARE_CALLBACK_REQUIRED_OR_EXPLICIT_SOFTWARE_ONLY"
    output = $output
    m33_object_sha256 = $m33Hash
    hashes = $hashes
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $result -Encoding UTF8
Write-Host "result=$result"
