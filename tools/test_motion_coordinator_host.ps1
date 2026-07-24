# Portable host replay for the automatic daily-expression coordinator.
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) {
    throw "Visual Studio vswhere.exe is required for the native motion-coordinator test."
}

$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) {
    throw "Visual Studio C++ Build Tools are required for the native motion-coordinator test."
}

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$testSource = Join-Path $epaperRoot "tests\test_motion_coordinator.c"
$coordinatorSource = Join-Path $epaperRoot "motion_coordinator.c"
$outDir = Join-Path $repoRoot ".cache\host-tests\motion-coordinator"
$exePath = Join-Path $outDir "test_motion_coordinator.exe"
foreach ($required in @($vsDevCmd, $testSource, $coordinatorSource)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing host motion-coordinator dependency: $required"
    }
}
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$compileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /I"{1}" "{2}" "{3}" /Fe:"{4}"' -f `
    $vsDevCmd, $epaperRoot, $testSource, $coordinatorSource, $exePath
Push-Location $outDir
try {
    & $env:ComSpec /d /s /c $compileCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Native motion-coordinator compile failed with exit code $LASTEXITCODE."
    }
    & $exePath
    if ($LASTEXITCODE -ne 0) {
        throw "Native motion-coordinator test failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
