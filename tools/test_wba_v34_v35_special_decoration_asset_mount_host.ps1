# Native WBA55/WBA65 replay for the inactive V34/V35 source-decoration CRIG.
param(
    [string]$CandidatePack = "",
    [string]$Evidence = "docs\validation\companion-v34-v35-special-decoration-target-asset-mount-20260720.json"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) {
    throw "Visual Studio vswhere.exe is required for the special-decoration WBA host test."
}
$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) {
    throw "Visual Studio C++ Build Tools are required for the special-decoration WBA host test."
}
if (-not $CandidatePack) {
    $CandidatePack = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-special-decoration-rig-v1\candidate\companion-v9-special-decoration-rig-candidate-200x200.crig"
}
$candidatePack = (Resolve-Path -LiteralPath $CandidatePack).Path
$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$testSource = Join-Path $epaperRoot "tests\test_wba_v34_v35_special_decoration_asset_mount.c"
$assetStoreSource = Join-Path $epaperRoot "asset_store.c"
$rigPackSource = Join-Path $epaperRoot "expression_rig_asset_pack.c"
$rigPackSetSource = Join-Path $epaperRoot "expression_rig_asset_pack_set.c"
$wbaAssetsSource = Join-Path $epaperRoot "screen_assets_stm32wba.c"
$outDir = Join-Path $repoRoot ".cache\host-tests\wba-v34-v35-special-decoration-asset-mount"
$exePath = Join-Path $outDir "test_wba_v34_v35_special_decoration_asset_mount.exe"
foreach ($required in @($vsDevCmd, $testSource, $assetStoreSource, $rigPackSource, $rigPackSetSource, $wbaAssetsSource, $candidatePack)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing special-decoration WBA host-test dependency: $required"
    }
}
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$compileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /utf-8 /std:c11 /I"{1}" "{2}" "{3}" "{4}" "{5}" "{6}" "{7}" /Fe:"{8}"' -f `
    $vsDevCmd, $epaperRoot, $testSource, $assetStoreSource, $rigPackSource, $rigPackSetSource, $wbaAssetsSource, $exePath
Push-Location $outDir
try {
    & $env:ComSpec /d /s /c $compileCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Native special-decoration WBA replay compile failed with exit code $LASTEXITCODE."
    }
    & $exePath $candidatePack
    if ($LASTEXITCODE -ne 0) {
        throw "Native special-decoration WBA replay failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
$evidencePath = Join-Path $repoRoot $Evidence
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $evidencePath) | Out-Null
@{
    schema = "companion.v34_v35_special_decoration_target_asset_mount.v1"
    status = "PASS_TARGET_ASSET_MOUNT_RUNTIME_INACTIVE"
    candidate_pack = (Resolve-Path -LiteralPath $candidatePack).Path.Substring($repoRoot.Length + 1).Replace('\', '/')
    candidate_pack_sha256 = (Get-FileHash -LiteralPath $candidatePack -Algorithm SHA256).Hash
    targets = @("WBA55", "WBA65")
    component_count = 39
    component_id_range = @(500, 538)
    runtime_resource_activated = $false
    active_candidate_binding = "forbidden"
    non_claims = @("no_special_event_runtime_binding", "no_firmware_flash", "no_panel_or_driver_change")
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $evidencePath -Encoding utf8
