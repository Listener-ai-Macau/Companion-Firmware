# Native STM32WB55 upper-path replay for the inactive V34/V35 browser component preview.
param(
    [string]$EvidencePath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $EvidencePath) {
    $EvidencePath = Join-Path $repoRoot "docs\validation\companion-v34-v35-special-decoration-wb55-component-parity-host-20260720.json"
}
if (-not [System.IO.Path]::IsPathRooted($EvidencePath)) {
    $EvidencePath = Join-Path $repoRoot $EvidencePath
}

$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) {
    throw "Visual Studio vswhere.exe is required for the native WB55 special-decoration parity test."
}
$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) {
    throw "Visual Studio C++ Build Tools are required for the native WB55 special-decoration parity test."
}

& python (Join-Path $PSScriptRoot "generate_companion_v34_v35_special_decoration_target_profile.py")
if ($LASTEXITCODE -ne 0) {
    throw "Generated V34/V35 WB55 candidate profile failed."
}
& python (Join-Path $PSScriptRoot "render_companion_v34_v35_special_decoration_wb55_parity.py")
if ($LASTEXITCODE -ne 0) {
    throw "Component-only V34/V35 browser preview render failed."
}

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$v22Pack = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-extension-v22-emotion-separation-source\candidate\target-rig-attempt-01\companion-v22-emotion-separation-rig-candidate-200x200.crig"
$specialPack = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-special-decoration-rig-v1\candidate\companion-v9-special-decoration-rig-candidate-200x200.crig"
$frameDir = Join-Path $repoRoot "docs\art\iterations\companion-pet-expression-v9-special-decoration-rig-v1\candidate\wb55-browser-parity-attempt-01"
$sources = @(
    (Join-Path $epaperRoot "tests\test_expression_v34_v35_special_decoration_wb55_parity.c"),
    (Join-Path $epaperRoot "asset_store.c"),
    (Join-Path $epaperRoot "expression_rig_asset_pack.c"),
    (Join-Path $epaperRoot "expression_rig_asset_pack_set.c"),
    (Join-Path $epaperRoot "expression_rig.c"),
    (Join-Path $epaperRoot "expression_rig_performance_score.c"),
    (Join-Path $epaperRoot "generated\expression_rig_v34_v35_special_decoration_candidate_profile.c")
)
$outDir = Join-Path $repoRoot ".cache\host-tests\v34-v35-special-decoration-wb55-parity"
$exePath = Join-Path $outDir "test_expression_v34_v35_special_decoration_wb55_parity.exe"
foreach ($required in @($vsDevCmd, $v22Pack, $specialPack, $frameDir) + $sources) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing native WB55 special-decoration parity dependency: $required"
    }
}
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $EvidencePath) | Out-Null

$quotedSources = ($sources | ForEach-Object { '"{0}"' -f $_ }) -join ' '
$compileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /I"{1}" {2} /Fe:"{3}"' -f `
    $vsDevCmd, $epaperRoot, $quotedSources, $exePath
Push-Location $outDir
try {
    & $env:ComSpec /d /s /c $compileCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Native WB55 special-decoration parity compile failed with exit code $LASTEXITCODE."
    }
    & $exePath $v22Pack $specialPack $frameDir $EvidencePath
    if ($LASTEXITCODE -ne 0) {
        throw "Native WB55 special-decoration parity replay failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
