# Rebuild every V44 browser frame through the WB55 upper component path.
param(
    [string]$EvidencePath = "",
    [string]$PreviewEvidencePath = "",
    [string]$FrameDir = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$trace = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-two-track-rig-v6\candidate\target-score-attempt-01\v44-wb55-target-profile-plan.json"
$specialLayout = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-two-track-rig-v6\candidate\v44-special-component-layout.json"
if (-not $FrameDir) { $FrameDir = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-two-track-rig-v6\candidate\wb55-browser-parity-attempt-01" }
if (-not [System.IO.Path]::IsPathRooted($FrameDir)) { $FrameDir = Join-Path $repoRoot $FrameDir }
if (-not $PreviewEvidencePath) { $PreviewEvidencePath = Join-Path $repoRoot "docs\validation\companion-v44-blink-stable-center-browser-wb55-preview-20260721.json" }
if (-not [System.IO.Path]::IsPathRooted($PreviewEvidencePath)) { $PreviewEvidencePath = Join-Path $repoRoot $PreviewEvidencePath }
if (-not $EvidencePath) { $EvidencePath = Join-Path $repoRoot "docs\validation\companion-v44-blink-stable-center-wb55-component-parity-host-20260721.json" }
if (-not [System.IO.Path]::IsPathRooted($EvidencePath)) { $EvidencePath = Join-Path $repoRoot $EvidencePath }
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) { throw "Visual Studio vswhere.exe is required for the native V44 parity test." }
$installPath = [string](& $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) { throw "Visual Studio C++ Build Tools are required for the native V44 parity test." }
& python (Join-Path $PSScriptRoot "export_companion_v44_blink_recording_components.py") --check
if ($LASTEXITCODE -ne 0) { throw "V44 source-component export check failed." }
& python (Join-Path $PSScriptRoot "generate_companion_v44_blink_stable_center_target_profile.py") --check
if ($LASTEXITCODE -ne 0) { throw "V44 target profile check failed." }
& python (Join-Path $PSScriptRoot "render_companion_v34_v35_special_decoration_wb55_parity.py") --trace $trace --special-layout $specialLayout --candidate-label v44_blink_stable_center --output-dir $FrameDir --report $PreviewEvidencePath
if ($LASTEXITCODE -ne 0) { throw "V44 browser component render failed." }
$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$sources = @((Join-Path $epaperRoot "tests\test_expression_v44_blink_stable_center_wb55_parity.c"), (Join-Path $epaperRoot "asset_store.c"), (Join-Path $epaperRoot "expression_rig_asset_pack.c"), (Join-Path $epaperRoot "expression_rig_asset_pack_set.c"), (Join-Path $epaperRoot "expression_rig.c"), (Join-Path $epaperRoot "expression_rig_performance_score.c"), (Join-Path $epaperRoot "expression_rig_track_composer.c"), (Join-Path $epaperRoot "generated\expression_rig_v44_blink_stable_center_candidate_profile.c"))
$outDir = Join-Path $repoRoot ".cache\host-tests\v44-blink-stable-center-parity"
$exePath = Join-Path $outDir "test_expression_v44_blink_stable_center_wb55_parity.exe"
$v22Pack = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-extension-v22-emotion-separation-source\candidate\target-rig-attempt-01\companion-v22-emotion-separation-rig-candidate-200x200.crig"
$v44Pack = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-two-track-rig-v6\candidate\companion-v9-v44-blink-recording-special-components-candidate-200x200.crig"
foreach ($required in @($vsDevCmd, $trace, $specialLayout, $v22Pack, $v44Pack) + $sources) { if (-not (Test-Path -LiteralPath $required)) { throw "Missing native V44 parity dependency: $required" } }
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $EvidencePath) | Out-Null
$quotedSources = ($sources | ForEach-Object { '"{0}"' -f $_ }) -join ' '
$compileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /I"{1}" {2} /Fe:"{3}"' -f $vsDevCmd, $epaperRoot, $quotedSources, $exePath
Push-Location $outDir
try {
    & $env:ComSpec /d /s /c $compileCommand
    if ($LASTEXITCODE -ne 0) { throw "Native V44 parity compile failed with exit code $LASTEXITCODE." }
    & $exePath $v22Pack $v44Pack $FrameDir $EvidencePath
    if ($LASTEXITCODE -ne 0) { throw "Native V44 parity replay failed with exit code $LASTEXITCODE." }
} finally { Pop-Location }
