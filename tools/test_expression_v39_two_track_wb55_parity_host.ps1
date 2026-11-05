# Rebuild every V39 browser preview frame through the WB55 two-track upper path.
param([string]$EvidencePath = "")

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$trace = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-two-track-rig-v1\candidate\target-score-attempt-01\two-track-wb55-target-profile-plan.json"
$specialLayout = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-function-state-decoration-rig-v1\candidate\function-state-component-layout.json"
$frameDir = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-two-track-rig-v1\candidate\wb55-browser-parity-attempt-01"
$preview = Join-Path $repoRoot "docs\validation\companion-v39-two-track-browser-wb55-preview-20260720.json"
if (-not $EvidencePath) { $EvidencePath = Join-Path $repoRoot "docs\validation\companion-v39-two-track-wb55-component-parity-host-20260720.json" }
if (-not [System.IO.Path]::IsPathRooted($EvidencePath)) { $EvidencePath = Join-Path $repoRoot $EvidencePath }
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) { throw "Visual Studio vswhere.exe is required for the native V39 parity test." }
$installPath = [string](& $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) { throw "Visual Studio C++ Build Tools are required for the native V39 parity test." }
& python (Join-Path $PSScriptRoot "verify_companion_v39_two_track_layout.py")
if ($LASTEXITCODE -ne 0) { throw "V39 two-track layout gate failed." }
& python (Join-Path $PSScriptRoot "generate_companion_v39_two_track_target_profile.py") --check
if ($LASTEXITCODE -ne 0) { throw "V39 target profile check failed." }
& python (Join-Path $PSScriptRoot "render_companion_v34_v35_special_decoration_wb55_parity.py") --trace $trace --special-layout $specialLayout --candidate-label v39_two_track --output-dir $frameDir --report $preview
if ($LASTEXITCODE -ne 0) { throw "V39 browser component render failed." }
$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$sources = @((Join-Path $epaperRoot "tests\test_expression_v39_two_track_wb55_parity.c"), (Join-Path $epaperRoot "asset_store.c"), (Join-Path $epaperRoot "expression_rig_asset_pack.c"), (Join-Path $epaperRoot "expression_rig_asset_pack_set.c"), (Join-Path $epaperRoot "expression_rig.c"), (Join-Path $epaperRoot "expression_rig_performance_score.c"), (Join-Path $epaperRoot "expression_rig_track_composer.c"), (Join-Path $epaperRoot "generated\expression_rig_v39_two_track_candidate_profile.c"))
$outDir = Join-Path $repoRoot ".cache\host-tests\v39-two-track-parity"
$exePath = Join-Path $outDir "test_expression_v39_two_track_wb55_parity.exe"
$v22Pack = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-extension-v22-emotion-separation-source\candidate\target-rig-attempt-01\companion-v22-emotion-separation-rig-candidate-200x200.crig"
$v38Pack = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-function-state-decoration-rig-v1\candidate\companion-v9-function-state-rig-candidate-200x200.crig"
foreach ($required in @($vsDevCmd, $trace, $specialLayout, $v22Pack, $v38Pack) + $sources) { if (-not (Test-Path -LiteralPath $required)) { throw "Missing native V39 parity dependency: $required" } }
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $EvidencePath) | Out-Null
$quotedSources = ($sources | ForEach-Object { '"{0}"' -f $_ }) -join ' '
$compileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /I"{1}" {2} /Fe:"{3}"' -f $vsDevCmd, $epaperRoot, $quotedSources, $exePath
Push-Location $outDir
try {
    & $env:ComSpec /d /s /c $compileCommand
    if ($LASTEXITCODE -ne 0) { throw "Native V39 parity compile failed with exit code $LASTEXITCODE." }
    & $exePath $v22Pack $v38Pack $frameDir $EvidencePath
    if ($LASTEXITCODE -ne 0) { throw "Native V39 parity replay failed with exit code $LASTEXITCODE." }
} finally { Pop-Location }
