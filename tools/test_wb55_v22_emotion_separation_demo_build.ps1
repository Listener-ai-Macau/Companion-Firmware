# Rebuild and verify the explicit production-off WB55 V22 directed-bridge demo.
param(
    [ValidateRange(0, 9)]
    [int]$Edge = 0,
    [string]$EvidencePath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $EvidencePath) {
    $EvidencePath = Join-Path $repoRoot "docs\validation\companion-v22-emotion-separation-wb55-demo-build-gate-20260719.json"
}

& python (Join-Path $PSScriptRoot "generate_companion_v22_emotion_separation_target_rig.py") --check
if ($LASTEXITCODE -ne 0) {
    throw "Generated V22 target Rig artifact check failed."
}

& pwsh -NoProfile -File (Join-Path $PSScriptRoot "build_nucleo_bringup.ps1") `
    -EpaperV22EmotionBridgeDemo `
    -EpaperV22EmotionBridgeDemoEdge $Edge `
    -ScreenAssetProvision `
    -Force
if ($LASTEXITCODE -ne 0) {
    throw "WB55 V22 emotion-bridge demo build failed."
}

$buildDirectory = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_v22_emotion_bridge_demo_$Edge"
$target = "Companion_Nucleo_WB55RG_V22EmotionBridgeDemo_$Edge"
& python (Join-Path $PSScriptRoot "verify_companion_v22_emotion_separation_wb55_demo.py") `
    --build-directory $buildDirectory `
    --target $target `
    --edge $Edge `
    --write $EvidencePath
if ($LASTEXITCODE -ne 0) {
    throw "WB55 V22 emotion-bridge demo identity gate failed."
}

Write-Output "PASS: WB55 V22 production-off directed-bridge demo build gate written to $EvidencePath"
