# Portable host check for the production-off black-ball orbit diagnostic.
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) {
    throw "Visual Studio vswhere.exe is required for the native ball-motion test."
}

$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) {
    throw "Visual Studio C++ Build Tools are required for the native ball-motion test."
}

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$testSource = Join-Path $epaperRoot "tests\test_ball_motion_diagnostic.c"
$outDir = Join-Path $repoRoot ".cache\host-tests\ball-motion-diagnostic"
$exePath = Join-Path $outDir "test_ball_motion_diagnostic.exe"
foreach ($required in @($vsDevCmd, $testSource)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing host ball-motion dependency: $required"
    }
}
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$compileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /I"{1}" "{2}" /Fe:"{3}"' -f `
    $vsDevCmd, $epaperRoot, $testSource, $exePath
Push-Location $outDir
try {
    & $env:ComSpec /d /s /c $compileCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Native ball-motion compile failed with exit code $LASTEXITCODE."
    }
    & $exePath
    if ($LASTEXITCODE -ne 0) {
        throw "Native ball-motion test failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
