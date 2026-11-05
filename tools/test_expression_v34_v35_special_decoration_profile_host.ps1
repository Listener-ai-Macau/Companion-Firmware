# Native regression for the inactive STM32WB55 V34/V35 special-decoration score profile.
param(
    [string]$EvidencePath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $EvidencePath) {
    $EvidencePath = Join-Path $repoRoot "docs\validation\companion-v34-v35-special-decoration-wb55-profile-host-20260720.json"
}
if (-not [System.IO.Path]::IsPathRooted($EvidencePath)) {
    $EvidencePath = Join-Path $repoRoot $EvidencePath
}

$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) {
    throw "Visual Studio vswhere.exe is required for the native WB55 special-decoration profile test."
}
$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) {
    throw "Visual Studio C++ Build Tools are required for the native WB55 special-decoration profile test."
}

& python (Join-Path $PSScriptRoot "generate_companion_v34_v35_special_decoration_target_profile.py") --check
if ($LASTEXITCODE -ne 0) {
    throw "Generated V34/V35 WB55 candidate profile check failed."
}

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$sources = @(
    (Join-Path $epaperRoot "tests\test_expression_v34_v35_special_decoration_profile.c"),
    (Join-Path $epaperRoot "expression_rig.c"),
    (Join-Path $epaperRoot "expression_rig_performance_score.c"),
    (Join-Path $epaperRoot "generated\expression_rig_v34_v35_special_decoration_candidate_profile.c")
)
$outDir = Join-Path $repoRoot ".cache\host-tests\v34-v35-special-decoration-wb55-profile"
$exePath = Join-Path $outDir "test_expression_v34_v35_special_decoration_profile.exe"
foreach ($required in @($vsDevCmd) + $sources) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing host WB55 special-decoration profile dependency: $required"
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
        throw "Native WB55 special-decoration profile compile failed with exit code $LASTEXITCODE."
    }
    & $exePath $EvidencePath
    if ($LASTEXITCODE -ne 0) {
        throw "Native WB55 special-decoration profile test failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
