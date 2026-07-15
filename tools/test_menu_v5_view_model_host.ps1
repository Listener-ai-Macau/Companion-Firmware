# Renderer-input contract test. It has no target renderer or asset side effect.
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) {
    throw "Visual Studio vswhere.exe is required for the menu-v5 view-model host test."
}
$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) {
    throw "Visual Studio C++ Build Tools are required for the menu-v5 view-model host test."
}

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$sources = @(
    (Join-Path $epaperRoot "tests\test_menu_v5_view_model.c"),
    (Join-Path $epaperRoot "menu_v5_view_model.c"),
    (Join-Path $epaperRoot "menu_v5_navigation.c"),
    (Join-Path $epaperRoot "menu_v5_action_journey.c"),
    (Join-Path $epaperRoot "menu_v5_localization.c"),
    (Join-Path $epaperRoot "menu_v5_contract.c"),
    (Join-Path $epaperRoot "pet_performance.c"),
    (Join-Path $epaperRoot "pet_performance_event_bridge.c")
)
$outDir = Join-Path $repoRoot ".cache\host-tests\menu-v5-view-model"
$exePath = Join-Path $outDir "test_menu_v5_view_model.exe"
foreach ($required in @($vsDevCmd) + $sources) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing menu-v5 view-model host-test dependency: $required"
    }
}
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$compileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /utf-8 /std:c11 /I"{1}" "{2}" "{3}" "{4}" "{5}" "{6}" "{7}" "{8}" "{9}" /Fe:"{10}"' -f `
    $vsDevCmd, $epaperRoot, $sources[0], $sources[1], $sources[2], $sources[3], $sources[4], $sources[5], $sources[6], $sources[7], $exePath
Push-Location $outDir
try {
    & $env:ComSpec /d /s /c $compileCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Native menu-v5 view-model compile failed with exit code $LASTEXITCODE."
    }
    & $exePath
    if ($LASTEXITCODE -ne 0) {
        throw "Native menu-v5 view-model test failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
