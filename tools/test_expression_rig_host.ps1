# Native regression for the portable source-derived expression Rig core.
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) {
    throw "Visual Studio vswhere.exe is required for the native expression-Rig test."
}
$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) {
    throw "Visual Studio C++ Build Tools are required for the native expression-Rig test."
}

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$testSource = Join-Path $epaperRoot "tests\test_expression_rig.c"
$scoreTestSource = Join-Path $epaperRoot "tests\test_expression_rig_performance_score.c"
$rigSource = Join-Path $epaperRoot "expression_rig.c"
$scoreSource = Join-Path $epaperRoot "expression_rig_performance_score.c"
$generatedProfileSource = Join-Path $epaperRoot "generated\expression_rig_v9_candidate_profile.c"
$outDir = Join-Path $repoRoot ".cache\host-tests\expression-rig"
$exePath = Join-Path $outDir "test_expression_rig.exe"
$scoreExePath = Join-Path $outDir "test_expression_rig_performance_score.exe"
foreach ($required in @($vsDevCmd, $testSource, $scoreTestSource, $rigSource, $scoreSource, $generatedProfileSource)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing host expression-Rig dependency: $required"
    }
}
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$compileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /I"{1}" "{2}" "{3}" /Fe:"{4}"' -f `
    $vsDevCmd, $epaperRoot, $testSource, $rigSource, $exePath
$scoreCompileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /I"{1}" "{2}" "{3}" "{4}" "{5}" /Fe:"{6}"' -f `
    $vsDevCmd, $epaperRoot, $scoreTestSource, $rigSource, $scoreSource, $generatedProfileSource, $scoreExePath
Push-Location $outDir
try {
    & $env:ComSpec /d /s /c $compileCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Native expression-Rig compile failed with exit code $LASTEXITCODE."
    }
    & $exePath
    if ($LASTEXITCODE -ne 0) {
        throw "Native expression-Rig test failed with exit code $LASTEXITCODE."
    }
    & $env:ComSpec /d /s /c $scoreCompileCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Native expression-Rig performance-score compile failed with exit code $LASTEXITCODE."
    }
    & $scoreExePath
    if ($LASTEXITCODE -ne 0) {
        throw "Native expression-Rig performance-score test failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
