param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) {
    throw "Visual Studio vswhere.exe is required for the native diagnostics replay."
}

$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) {
    throw "Visual Studio C++ Build Tools are required for the native diagnostics replay."
}

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$diagRoot = Join-Path $repoRoot "app\companion_pendant\diag_log"
$testSource = Join-Path $diagRoot "tests\test_diag_log_export.c"
$logSource = Join-Path $diagRoot "diag_log.c"
$exportSource = Join-Path $diagRoot "diag_log_export.c"
$outDir = Join-Path $repoRoot ".cache\host-tests\diag-log-export-$PID"
$exePath = Join-Path $outDir "test_diag_log_export.exe"
foreach ($required in @($vsDevCmd, $testSource, $logSource, $exportSource)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing host diagnostics-test dependency: $required"
    }
}
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$compileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /I"{1}" "{2}" "{3}" "{4}" /Fe:"{5}"' -f `
    $vsDevCmd, $diagRoot, $testSource, $logSource, $exportSource, $exePath
Push-Location $outDir
try {
    & $env:ComSpec /d /s /c $compileCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Native diagnostics replay compile failed with exit code $LASTEXITCODE."
    }
    & $exePath
    if ($LASTEXITCODE -ne 0) {
        throw "Native diagnostics replay failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
