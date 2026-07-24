# Native regression for the runtime-inactive touch-to-emotion-to-Rig session.
param(
    [string]$EvidencePath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $EvidencePath) {
    $EvidencePath = Join-Path $repoRoot "docs\validation\companion-v9-rig-touch-emotion-machine-20260719.json"
}
if (-not [System.IO.Path]::IsPathRooted($EvidencePath)) {
    $EvidencePath = Join-Path $repoRoot $EvidencePath
} else {
    $EvidencePath = [System.IO.Path]::GetFullPath($EvidencePath)
}

$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) {
    throw "Visual Studio vswhere.exe is required for the native expression-interaction test."
}
$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) {
    throw "Visual Studio C++ Build Tools are required for the native expression-interaction test."
}

& python (Join-Path $PSScriptRoot "generate_companion_v9_expression_rig_profile.py") --check
if ($LASTEXITCODE -ne 0) {
    throw "Generated v9 Rig profile check failed."
}

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$touchRoot = Join-Path $repoRoot "app\companion_pendant\touch"
$sources = @(
    (Join-Path $epaperRoot "tests\test_expression_interaction_session.c"),
    (Join-Path $epaperRoot "expression_interaction_session.c"),
    (Join-Path $epaperRoot "expression_choreographer.c"),
    (Join-Path $epaperRoot "expression_rig.c"),
    (Join-Path $epaperRoot "expression_rig_performance_score.c"),
    (Join-Path $epaperRoot "generated\expression_rig_v9_candidate_profile.c"),
    (Join-Path $touchRoot "touch_gesture.c")
)
$outDir = Join-Path $repoRoot ".cache\host-tests\expression-interaction-session"
$exePath = Join-Path $outDir "test_expression_interaction_session.exe"
foreach ($required in @($vsDevCmd) + $sources) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing host expression-interaction dependency: $required"
    }
}
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $EvidencePath) | Out-Null

$quotedSources = ($sources | ForEach-Object { '"{0}"' -f $_ }) -join ' '
$compileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /I"{1}" /I"{2}" {3} /Fe:"{4}"' -f `
    $vsDevCmd, $epaperRoot, $touchRoot, $quotedSources, $exePath
Push-Location $outDir
try {
    & $env:ComSpec /d /s /c $compileCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Native expression-interaction compile failed with exit code $LASTEXITCODE."
    }
    & $exePath $EvidencePath
    if ($LASTEXITCODE -ne 0) {
        throw "Native expression-interaction test failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
