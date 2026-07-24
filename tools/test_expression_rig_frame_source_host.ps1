# Native parity export for the exact external-NOR Rig frame source used by the Daily screen demo.
param(
    [string]$OutputDir = "",
    [string]$Pack = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $OutputDir) {
    $OutputDir = Join-Path $repoRoot "docs\validation\artifacts\companion-v9-expression-rig-target-frame-parity-20260718\target-raw-pbm"
}
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) {
    throw "Visual Studio vswhere.exe is required for the native Rig frame-source test."
}
$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) {
    throw "Visual Studio C++ Build Tools are required for the native Rig frame-source test."
}

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$testSource = Join-Path $epaperRoot "tests\test_expression_rig_frame_source.c"
$sources = @(
    $testSource,
    (Join-Path $epaperRoot "asset_store.c"),
    (Join-Path $epaperRoot "expression_rig.c"),
    (Join-Path $epaperRoot "expression_rig_asset_pack.c"),
    (Join-Path $epaperRoot "expression_rig_frame_source.c"),
    (Join-Path $epaperRoot "expression_rig_performance_score.c"),
    (Join-Path $epaperRoot "expression_choreographer.c"),
    (Join-Path $epaperRoot "generated\expression_rig_v9_candidate_profile.c")
)
if (-not $Pack) {
    $Pack = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-rig-v1\candidate\rendered-200x200\companion-v9-expression-rig-candidate-200x200.crig"
}
$pack = (Resolve-Path -LiteralPath $Pack).Path
$outDir = Join-Path $repoRoot ".cache\host-tests\expression-rig-frame-source"
$exePath = Join-Path $outDir "test_expression_rig_frame_source.exe"
foreach ($required in @($vsDevCmd, $pack) + $sources) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing host Rig frame-source dependency: $required"
    }
}
New-Item -ItemType Directory -Force -Path $outDir, $OutputDir | Out-Null
$OutputDir = (Resolve-Path -LiteralPath $OutputDir).Path
Get-ChildItem -LiteralPath $OutputDir -Filter "daily_*.pbm" -File -ErrorAction SilentlyContinue |
    Remove-Item -Force

$quotedSources = ($sources | ForEach-Object { '"{0}"' -f $_ }) -join " "
$compileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /I"{1}" {2} /Fe:"{3}"' -f `
    $vsDevCmd, $epaperRoot, $quotedSources, $exePath
Push-Location $outDir
try {
    & $env:ComSpec /d /s /c $compileCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Native Rig frame-source compile failed with exit code $LASTEXITCODE."
    }
    & $exePath $pack $OutputDir
    if ($LASTEXITCODE -ne 0) {
        throw "Native Rig frame-source test failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
