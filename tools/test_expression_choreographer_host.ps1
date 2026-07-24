# Native regression for the source-derived v9 expression choreographer.
param(
    [string]$EvidencePath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $EvidencePath) {
    $EvidencePath = Join-Path $repoRoot "docs\validation\companion-v9-expression-choreographer-20260717.json"
}
if (-not [System.IO.Path]::IsPathRooted($EvidencePath)) {
    $EvidencePath = Join-Path $repoRoot $EvidencePath
} else {
    $EvidencePath = [System.IO.Path]::GetFullPath($EvidencePath)
}

$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) {
    throw "Visual Studio vswhere.exe is required for the native expression-choreographer test."
}
$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) {
    throw "Visual Studio C++ Build Tools are required for the native expression-choreographer test."
}

& python (Join-Path $PSScriptRoot "generate_companion_v9_expression_rig_profile.py") --check
if ($LASTEXITCODE -ne 0) {
    throw "Generated v9 Rig profile check failed."
}

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$testSource = Join-Path $epaperRoot "tests\test_expression_choreographer.c"
$choreographerSource = Join-Path $epaperRoot "expression_choreographer.c"
$rigSource = Join-Path $epaperRoot "expression_rig.c"
$scoreSource = Join-Path $epaperRoot "expression_rig_performance_score.c"
$profileSource = Join-Path $epaperRoot "generated\expression_rig_v9_candidate_profile.c"
$outDir = Join-Path $repoRoot ".cache\host-tests\expression-choreographer"
$exePath = Join-Path $outDir "test_expression_choreographer.exe"
foreach ($required in @($vsDevCmd, $testSource, $choreographerSource, $rigSource, $scoreSource, $profileSource)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing host expression-choreographer dependency: $required"
    }
}
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $EvidencePath) | Out-Null

$compileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /I"{1}" "{2}" "{3}" "{4}" "{5}" "{6}" /Fe:"{7}"' -f `
    $vsDevCmd, $epaperRoot, $testSource, $choreographerSource, $rigSource, $scoreSource, $profileSource, $exePath
Push-Location $outDir
try {
    & $env:ComSpec /d /s /c $compileCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Native expression-choreographer compile failed with exit code $LASTEXITCODE."
    }
    & $exePath $EvidencePath
    if ($LASTEXITCODE -ne 0) {
        throw "Native expression-choreographer test failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
