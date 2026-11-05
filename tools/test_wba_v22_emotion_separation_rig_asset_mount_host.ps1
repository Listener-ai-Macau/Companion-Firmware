# Native WBA55/WBA65 replay of the owner-accepted V22 component bridge from external NOR.
param(
    [string]$EvidencePath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $EvidencePath) {
    $EvidencePath = Join-Path $repoRoot "docs\validation\companion-v22-emotion-separation-target-rig-wba-host-20260719.json"
}
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) {
    throw "Visual Studio vswhere.exe is required for the V22 WBA Rig host test."
}
$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) {
    throw "Visual Studio C++ Build Tools are required for the V22 WBA Rig host test."
}

& python (Join-Path $PSScriptRoot "generate_companion_v22_emotion_separation_target_rig.py") --check
if ($LASTEXITCODE -ne 0) {
    throw "Generated V22 target Rig artifact check failed."
}

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$testSource = Join-Path $epaperRoot "tests\test_wba_v22_emotion_separation_rig_asset_mount.c"
$assetStoreSource = Join-Path $epaperRoot "asset_store.c"
$scoreSource = Join-Path $epaperRoot "expression_rig_performance_score.c"
$rigSource = Join-Path $epaperRoot "expression_rig.c"
$rigPackSource = Join-Path $epaperRoot "expression_rig_asset_pack.c"
$profileSource = Join-Path $epaperRoot "generated\expression_rig_v22_emotion_separation_candidate_profile.c"
$wbaAssetsSource = Join-Path $epaperRoot "screen_assets_stm32wba.c"
$candidatePack = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-extension-v22-emotion-separation-source\candidate\target-rig-attempt-01\companion-v22-emotion-separation-rig-candidate-200x200.crig"
$frameDirectory = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-extension-v22-emotion-separation-source\candidate\component-bridge-attempt-01\bridge-frames-200x200"
$outDir = Join-Path $repoRoot ".cache\host-tests\wba-v22-emotion-separation-rig-replay"
$exePath = Join-Path $outDir "test_wba_v22_emotion_separation_rig_asset_mount.exe"
foreach ($required in @($vsDevCmd, $testSource, $assetStoreSource, $scoreSource, $rigSource, $rigPackSource, $profileSource, $wbaAssetsSource, $candidatePack, $frameDirectory)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing V22 WBA Rig host-test dependency: $required"
    }
}
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$compileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /utf-8 /std:c11 /I"{1}" "{2}" "{3}" "{4}" "{5}" "{6}" "{7}" "{8}" /Fe:"{9}"' -f `
    $vsDevCmd, $epaperRoot, $testSource, $assetStoreSource, $scoreSource, $rigSource, $rigPackSource, $profileSource, $wbaAssetsSource, $exePath
Push-Location $outDir
try {
    & $env:ComSpec /d /s /c $compileCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Native V22 WBA Rig replay compile failed with exit code $LASTEXITCODE."
    }
    & $exePath $candidatePack $frameDirectory
    if ($LASTEXITCODE -ne 0) {
        throw "Native V22 WBA Rig replay test failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}

$evidenceDirectory = Split-Path -Parent $EvidencePath
New-Item -ItemType Directory -Force -Path $evidenceDirectory | Out-Null
[ordered]@{
    schema = "companion.v22_emotion_separation_target_rig_wba_host.v1"
    status = "PASS_V22_EMOTION_SEPARATION_TARGET_RIG_WBA_EXTERNAL_NOR_PARITY"
    candidate_pack = "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/candidate/target-rig-attempt-01/companion-v22-emotion-separation-rig-candidate-200x200.crig"
    bridge_frames = "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/candidate/component-bridge-attempt-01/bridge-frames-200x200"
    targets = @("WBA55", "WBA65")
    bridge_count = 10
    runtime_resource_activated = $false
    special_event_fallback = "fail_closed"
    whole_face_source_card_playback = "forbidden"
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $EvidencePath -Encoding ascii

Write-Output "PASS: V22 WBA external-NOR bridge replay evidence written to $EvidencePath"
