param()

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) {
    throw "Visual Studio C++ Build Tools are required."
}

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$testSource = Join-Path $epaperRoot "tests\test_refresh_coverage.c"
$outDir = Join-Path $repoRoot ".cache\host-tests\refresh-coverage"
$exe = Join-Path $outDir "refresh-coverage.exe"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$command = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /I"{1}" "{2}" /Fe:"{3}"' -f `
    $vsDevCmd, $epaperRoot, $testSource, $exe
& $env:ComSpec /d /s /c $command
if ($LASTEXITCODE -ne 0) {
    throw "Refresh coverage compile failed with exit code $LASTEXITCODE."
}
& $exe
if ($LASTEXITCODE -ne 0) {
    throw "Refresh coverage contract failed."
}
