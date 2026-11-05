# Portable four-root menu contract test. It deliberately does not render,
# generate a PBM/CEMP asset, write external Flash, or touch hardware.
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) {
    throw "Visual Studio vswhere.exe is required for the menu-v5 host test."
}
$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) {
    throw "Visual Studio C++ Build Tools are required for the menu-v5 host test."
}

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$testSource = Join-Path $epaperRoot "tests\test_menu_v5_contract.c"
$contractSource = Join-Path $epaperRoot "menu_v5_contract.c"
$localizationSource = Join-Path $epaperRoot "menu_v5_localization.c"
$outDir = Join-Path $repoRoot ".cache\host-tests\menu-v5-contract"
$exePath = Join-Path $outDir "test_menu_v5_contract.exe"
foreach ($required in @($vsDevCmd, $testSource, $contractSource, $localizationSource)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing menu-v5 host-test dependency: $required"
    }
}
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$compileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /utf-8 /std:c11 /I"{1}" "{2}" "{3}" "{4}" /Fe:"{5}"' -f `
    $vsDevCmd, $epaperRoot, $testSource, $contractSource, $localizationSource, $exePath
Push-Location $outDir
try {
    & $env:ComSpec /d /s /c $compileCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Native menu-v5 contract compile failed with exit code $LASTEXITCODE."
    }
    & $exePath
    if ($LASTEXITCODE -ne 0) {
        throw "Native menu-v5 contract test failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
