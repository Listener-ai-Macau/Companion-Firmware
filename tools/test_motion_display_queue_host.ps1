# Native regression for selective automatic-expression queue cancellation.
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) {
    throw "Visual Studio vswhere.exe is required for the native display-queue test."
}

$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) {
    throw "Visual Studio C++ Build Tools are required for the native display-queue test."
}

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$testSource = Join-Path $epaperRoot "tests\test_motion_display_queue.c"
$queueSource = Join-Path $epaperRoot "display_queue.c"
$expressionSource = Join-Path $epaperRoot "expression_state.c"
$outDir = Join-Path $repoRoot ".cache\host-tests\motion-display-queue"
$exePath = Join-Path $outDir "test_motion_display_queue.exe"
foreach ($required in @($vsDevCmd, $testSource, $queueSource, $expressionSource)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing host display-queue dependency: $required"
    }
}
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$compileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /I"{1}" "{2}" "{3}" "{4}" /Fe:"{5}"' -f `
    $vsDevCmd, $epaperRoot, $testSource, $queueSource, $expressionSource, $exePath
Push-Location $outDir
try {
    & $env:ComSpec /d /s /c $compileCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Native display-queue compile failed with exit code $LASTEXITCODE."
    }
    & $exePath
    if ($LASTEXITCODE -ne 0) {
        throw "Native display-queue test failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
