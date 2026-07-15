# Portable pet-performance regression test. It intentionally has no target
# HAL dependency so WB55 and WBA use the same scene and keyframe semantics.
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) {
    throw "Visual Studio vswhere.exe is required for the native pet-performance test."
}

$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) {
    throw "Visual Studio C++ Build Tools are required for the native pet-performance test."
}

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$testSource = Join-Path $epaperRoot "tests\test_pet_performance.c"
$performanceSource = Join-Path $epaperRoot "pet_performance.c"
$bridgeSource = Join-Path $epaperRoot "pet_performance_event_bridge.c"
$outDir = Join-Path $repoRoot ".cache\host-tests\pet-performance"
$exePath = Join-Path $outDir "test_pet_performance.exe"
foreach ($required in @($vsDevCmd, $testSource, $performanceSource, $bridgeSource)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing host pet-performance dependency: $required"
    }
}
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$compileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /I"{1}" "{2}" "{3}" "{4}" /Fe:"{5}"' -f `
    $vsDevCmd, $epaperRoot, $testSource, $performanceSource, $bridgeSource, $exePath
Push-Location $outDir
try {
    & $env:ComSpec /d /s /c $compileCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Native pet-performance compile failed with exit code $LASTEXITCODE."
    }
    & $exePath
    if ($LASTEXITCODE -ne 0) {
        throw "Native pet-performance test failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
