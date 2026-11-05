param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) {
    throw "Visual Studio vswhere.exe is required for the native touch replay."
}

$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) {
    throw "Visual Studio C++ Build Tools are required for the native touch replay."
}

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$touchRoot = Join-Path $repoRoot "app\companion_pendant\touch"
$testSource = Join-Path $touchRoot "tests\test_touch_gesture.c"
$visualReleaseTestSource = Join-Path $touchRoot "tests\test_touch_visual_release.c"
$gestureSource = Join-Path $touchRoot "touch_gesture.c"
$visualSource = Join-Path $touchRoot "touch_visual_decision.c"
$screenMenuSource = Join-Path $repoRoot "app\companion_pendant\epaper\screen_menu.c"
$screenFramebufferSource = Join-Path $repoRoot "app\companion_pendant\epaper\screen_framebuffer.c"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$generatedRoot = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_freertos\generated"
$outDir = Join-Path $repoRoot ".cache\host-tests\touch-gesture"
$exePath = Join-Path $outDir "test_touch_gesture.exe"
$visualReleaseExePath = Join-Path $outDir "test_touch_visual_release.exe"
foreach ($required in @($vsDevCmd, $testSource, $visualReleaseTestSource,
                         $gestureSource, $visualSource, $screenMenuSource,
                         $screenFramebufferSource)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing host touch-test dependency: $required"
    }
}
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$compileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /I"{1}" "{2}" "{3}" /Fe:"{4}"' -f `
    $vsDevCmd, $touchRoot, $testSource, $gestureSource, $exePath
Push-Location $outDir
try {
    & $env:ComSpec /d /s /c $compileCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Native touch replay compile failed with exit code $LASTEXITCODE."
    }
    & $exePath
    if ($LASTEXITCODE -ne 0) {
        throw "Native touch replay failed with exit code $LASTEXITCODE."
    }
    $visualCompileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /DCOMPANION_VISUAL_ASSET_PACK_ENABLE=0 /DCOMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK=1 /I"{1}" /I"{2}" /I"{3}" "{4}" "{5}" "{6}" "{7}" "{8}" /Fe:"{9}"' -f `
        $vsDevCmd, $touchRoot, $epaperRoot, $generatedRoot, $visualReleaseTestSource,
        $gestureSource, $visualSource, $screenMenuSource,
        $screenFramebufferSource, $visualReleaseExePath
    & $env:ComSpec /d /s /c $visualCompileCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Native touch visual release compile failed with exit code $LASTEXITCODE."
    }
    & $visualReleaseExePath
    if ($LASTEXITCODE -ne 0) {
        throw "Native touch visual release replay failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
