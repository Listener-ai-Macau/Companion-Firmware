# Native STM32WB55 upper-profile test for the inactive V38 function-state candidate.
param([string]$EvidencePath = "")

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $EvidencePath) { $EvidencePath = Join-Path $repoRoot "docs\validation\companion-v38-function-state-wb55-profile-host-20260720.json" }
if (-not [System.IO.Path]::IsPathRooted($EvidencePath)) { $EvidencePath = Join-Path $repoRoot $EvidencePath }
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) { throw "Visual Studio vswhere.exe is required for the native V38 profile test." }
$installPath = [string](& $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) { throw "Visual Studio C++ Build Tools are required for the native V38 profile test." }
& python (Join-Path $PSScriptRoot "export_companion_v38_function_state_rig.py") --check
if ($LASTEXITCODE -ne 0) { throw "V38 source pack check failed." }
& python (Join-Path $PSScriptRoot "generate_companion_v38_function_state_target_profile.py") --check
if ($LASTEXITCODE -ne 0) { throw "V38 target profile check failed." }
$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$sources = @((Join-Path $epaperRoot "tests\test_expression_v38_function_state_profile.c"), (Join-Path $epaperRoot "expression_rig.c"), (Join-Path $epaperRoot "expression_rig_performance_score.c"), (Join-Path $epaperRoot "generated\expression_rig_v38_function_state_candidate_profile.c"))
$outDir = Join-Path $repoRoot ".cache\host-tests\v38-function-state-profile"
$exePath = Join-Path $outDir "test_expression_v38_function_state_profile.exe"
foreach ($required in @($vsDevCmd) + $sources) { if (-not (Test-Path -LiteralPath $required)) { throw "Missing native V38 profile dependency: $required" } }
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $EvidencePath) | Out-Null
$quotedSources = ($sources | ForEach-Object { '"{0}"' -f $_ }) -join ' '
$compileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /I"{1}" {2} /Fe:"{3}"' -f $vsDevCmd, $epaperRoot, $quotedSources, $exePath
Push-Location $outDir
try {
    & $env:ComSpec /d /s /c $compileCommand
    if ($LASTEXITCODE -ne 0) { throw "Native V38 profile compile failed with exit code $LASTEXITCODE." }
    & $exePath $EvidencePath
    if ($LASTEXITCODE -ne 0) { throw "Native V38 profile replay failed with exit code $LASTEXITCODE." }
} finally { Pop-Location }
