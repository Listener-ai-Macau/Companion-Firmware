# Portable v9 candidate-binding regression. It has no WB55/WBA HAL dependency.
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) {
    throw "Visual Studio vswhere.exe is required for the native v9 candidate-binding test."
}

$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) {
    throw "Visual Studio C++ Build Tools are required for the native v9 candidate-binding test."
}

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$testSource = Join-Path $epaperRoot "tests\test_v9_candidate_resource_binding.c"
$performanceSource = Join-Path $epaperRoot "pet_performance.c"
$bindingSource = Join-Path $epaperRoot "v9_candidate_resource_binding.c"
$outDir = Join-Path $repoRoot ".cache\host-tests\v9-candidate-resource-binding"
$exePath = Join-Path $outDir "test_v9_candidate_resource_binding.exe"
foreach ($required in @($vsDevCmd, $testSource, $performanceSource, $bindingSource)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing host v9 candidate-binding dependency: $required"
    }
}
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$compileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /I"{1}" "{2}" "{3}" "{4}" /Fe:"{5}"' -f `
    $vsDevCmd, $epaperRoot, $testSource, $performanceSource, $bindingSource, $exePath
Push-Location $outDir
try {
    & $env:ComSpec /d /s /c $compileCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Native v9 candidate-binding compile failed with exit code $LASTEXITCODE."
    }
    & $exePath
    if ($LASTEXITCODE -ne 0) {
        throw "Native v9 candidate-binding test failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
