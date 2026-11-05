# Native host replay of every expanded V9 source-mask Rig state through external NOR.
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) {
    throw "Visual Studio vswhere.exe is required for the expanded WBA Rig host test."
}
$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) {
    throw "Visual Studio C++ Build Tools are required for the expanded WBA Rig host test."
}

& python (Join-Path $PSScriptRoot "generate_companion_v9_expanded_expression_rig_profile.py") --check
if ($LASTEXITCODE -ne 0) {
    throw "Generated expanded V9 Rig profile check failed."
}

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$testSource = Join-Path $epaperRoot "tests\test_wba_v9_expanded_expression_rig_asset_mount.c"
$assetStoreSource = Join-Path $epaperRoot "asset_store.c"
$choreographerSource = Join-Path $epaperRoot "expression_choreographer.c"
$scoreSource = Join-Path $epaperRoot "expression_rig_performance_score.c"
$rigSource = Join-Path $epaperRoot "expression_rig.c"
$rigPackSource = Join-Path $epaperRoot "expression_rig_asset_pack.c"
$profileSource = Join-Path $epaperRoot "generated\expression_rig_v9_expanded_candidate_profile.c"
$wbaAssetsSource = Join-Path $epaperRoot "screen_assets_stm32wba.c"
$candidatePack = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-rig-v2-expanded-source\candidate\companion-v9-expanded-expression-rig-candidate-200x200.crig"
$renderedDirectory = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-rig-v2-expanded-source\candidate\rendered-200x200"
$performanceDirectory = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-rig-v2-expanded-source\candidate\performance-frames-200x200"
$presenceDirectory = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-rig-v2-expanded-source\candidate\presence-frames-200x200"
$bridgeDirectory = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-rig-v2-expanded-source\candidate\emotion-bridge-frames-200x200"
$outDir = Join-Path $repoRoot ".cache\host-tests\wba-v9-expanded-expression-rig-replay"
$exePath = Join-Path $outDir "test_wba_v9_expanded_expression_rig_asset_mount.exe"
foreach ($required in @($vsDevCmd, $testSource, $assetStoreSource, $choreographerSource, $scoreSource, $rigSource, $rigPackSource, $profileSource, $wbaAssetsSource, $candidatePack, $renderedDirectory, $performanceDirectory, $presenceDirectory, $bridgeDirectory)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing expanded WBA Rig host-test dependency: $required"
    }
}
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$compileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /utf-8 /std:c11 /I"{1}" "{2}" "{3}" "{4}" "{5}" "{6}" "{7}" "{8}" "{9}" /Fe:"{10}"' -f `
    $vsDevCmd, $epaperRoot, $testSource, $assetStoreSource, $choreographerSource, $scoreSource, $rigSource, $rigPackSource, $profileSource, $wbaAssetsSource, $exePath
Push-Location $outDir
try {
    & $env:ComSpec /d /s /c $compileCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Native expanded WBA Rig replay compile failed with exit code $LASTEXITCODE."
    }
    & $exePath $candidatePack $renderedDirectory $performanceDirectory $presenceDirectory $bridgeDirectory
    if ($LASTEXITCODE -ne 0) {
        throw "Native expanded WBA Rig replay test failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
