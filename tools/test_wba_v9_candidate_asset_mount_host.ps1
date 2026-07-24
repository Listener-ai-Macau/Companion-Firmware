# Native host replay of the WBA callback-only assets adapter. It reads the
# non-activated v9 candidate CEMP from disk and never calls a target HAL.
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) {
    throw "Visual Studio vswhere.exe is required for the WBA CEMP host test."
}
$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) {
    throw "Visual Studio C++ Build Tools are required for the WBA CEMP host test."
}

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$testSource = Join-Path $epaperRoot "tests\test_wba_v9_candidate_asset_mount.c"
$assetStoreSource = Join-Path $epaperRoot "asset_store.c"
$assetPackSource = Join-Path $epaperRoot "emote_asset_pack.c"
$playerSource = Join-Path $epaperRoot "emote_player.c"
$wbaAssetsSource = Join-Path $epaperRoot "screen_assets_stm32wba.c"
$candidatePack = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9\rendered-200x200\companion-v9-expression-candidate-200x200.cemp"
$outDir = Join-Path $repoRoot ".cache\host-tests\wba-v9-cemp-replay"
$exePath = Join-Path $outDir "test_wba_v9_candidate_asset_mount.exe"
foreach ($required in @($vsDevCmd, $testSource, $assetStoreSource, $assetPackSource, $playerSource, $wbaAssetsSource, $candidatePack)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing WBA CEMP host-test dependency: $required"
    }
}
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$compileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /utf-8 /std:c11 /I"{1}" "{2}" "{3}" "{4}" "{5}" "{6}" /Fe:"{7}"' -f `
    $vsDevCmd, $epaperRoot, $testSource, $assetStoreSource, $assetPackSource, $playerSource, $wbaAssetsSource, $exePath
Push-Location $outDir
try {
    & $env:ComSpec /d /s /c $compileCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Native WBA CEMP replay compile failed with exit code $LASTEXITCODE."
    }
    & $exePath $candidatePack "companion-v9-expression-candidate-200x200" 90 13 39
    if ($LASTEXITCODE -ne 0) {
        throw "Native WBA CEMP replay test failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
