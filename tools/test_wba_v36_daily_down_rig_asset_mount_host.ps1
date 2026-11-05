# Native WBA55/WBA65 replay of the inactive V36 Daily-down Rig from external NOR.
param(
    [ValidateSet(9, 10, 11)]
    [int]$Attempt = 9,
    [string]$EvidencePath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$attemptSuffix = if ($Attempt -eq 9) { "" } else { "-attempt-{0:D2}" -f $Attempt }
if (-not $EvidencePath) { $EvidencePath = Join-Path $repoRoot ("docs\validation\companion-v36-daily-down-target-rig-wba-host{0}-20260720.json" -f $attemptSuffix) }
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) { throw "Visual Studio vswhere.exe is required for the V36 WBA Rig host test." }
$installPath = [string](& $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) { throw "Visual Studio C++ Build Tools are required for the V36 WBA Rig host test." }

& python (Join-Path $PSScriptRoot "generate_companion_v36_daily_down_target_rig.py") --attempt $Attempt --check
if ($LASTEXITCODE -ne 0) { throw "Generated V36 target Rig artifact check failed." }

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$testSource = Join-Path $epaperRoot "tests\test_wba_v36_daily_down_rig_asset_mount.c"
$assetStoreSource = Join-Path $epaperRoot "asset_store.c"
$scoreSource = Join-Path $epaperRoot "expression_rig_performance_score.c"
$rigSource = Join-Path $epaperRoot "expression_rig.c"
$rigPackSource = Join-Path $epaperRoot "expression_rig_asset_pack.c"
$profileSource = if ($Attempt -eq 9) {
    Join-Path $epaperRoot "generated\expression_rig_v36_daily_down_candidate_profile.c"
} else {
    Join-Path $epaperRoot ("generated\expression_rig_v36_daily_down_attempt_{0:D2}_candidate_profile.c" -f $Attempt)
}
$wbaAssetsSource = Join-Path $epaperRoot "screen_assets_stm32wba.c"
$candidatePackName = if ($Attempt -eq 9) { "companion-v36-daily-down-rig-candidate-200x200.crig" } else { "companion-v36-daily-down-attempt-{0:D2}-rig-candidate-200x200.crig" -f $Attempt }
$candidatePack = Join-Path $repoRoot ("docs\art\iterations\companion-pet-expression-v9-extension-v36-directional-eye-gaze-source\candidate\target-rig-attempt-{0:D2}\{1}" -f $Attempt, $candidatePackName)
$frameDirectory = Join-Path $repoRoot ("docs\art\iterations\companion-pet-expression-v9-extension-v36-directional-eye-gaze-source\candidate\component-export-attempt-{0:D2}\preview\pbm" -f $Attempt)
$outDir = Join-Path $repoRoot (".cache\host-tests\wba-v36-daily-down-rig-replay-attempt-{0:D2}" -f $Attempt)
$exePath = Join-Path $outDir "test_wba_v36_daily_down_rig_asset_mount.exe"
foreach ($required in @($vsDevCmd, $testSource, $assetStoreSource, $scoreSource, $rigSource, $rigPackSource, $profileSource, $wbaAssetsSource, $candidatePack, $frameDirectory)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Missing V36 WBA Rig host-test dependency: $required" }
}
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$attemptDefine = if ($Attempt -eq 9) { "" } else { " /DV36_ATTEMPT_{0:D2}" -f $Attempt }
$compileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /utf-8 /std:c11{1} /I"{2}" "{3}" "{4}" "{5}" "{6}" "{7}" "{8}" "{9}" /Fe:"{10}"' -f $vsDevCmd, $attemptDefine, $epaperRoot, $testSource, $assetStoreSource, $scoreSource, $rigSource, $rigPackSource, $profileSource, $wbaAssetsSource, $exePath
Push-Location $outDir
try {
    & $env:ComSpec /d /s /c $compileCommand
    if ($LASTEXITCODE -ne 0) { throw "Native V36 WBA Rig replay compile failed with exit code $LASTEXITCODE." }
    & $exePath $candidatePack $frameDirectory
    if ($LASTEXITCODE -ne 0) { throw "Native V36 WBA Rig replay test failed with exit code $LASTEXITCODE." }
} finally {
    Pop-Location
}

$evidenceDirectory = Split-Path -Parent $EvidencePath
New-Item -ItemType Directory -Force -Path $evidenceDirectory | Out-Null
[ordered]@{
    schema = "companion.v36_daily_down_target_rig_wba_host.v1"
    status = "PASS_V36_DAILY_DOWN_TARGET_RIG_WBA_EXTERNAL_NOR_PARITY"
    attempt = $Attempt
    candidate_pack = $candidatePack.Substring($repoRoot.Length + 1).Replace("\", "/")
    browser_pbm_frames = $frameDirectory.Substring($repoRoot.Length + 1).Replace("\", "/")
    targets = @("WBA55", "WBA65")
    frame_count = 6
    runtime_resource_activated = $false
    special_event_fallback = "fail_closed"
    whole_face_source_card_playback = "forbidden"
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $EvidencePath -Encoding ascii
Write-Output "PASS: V36 WBA external-NOR component replay evidence written to $EvidencePath"
