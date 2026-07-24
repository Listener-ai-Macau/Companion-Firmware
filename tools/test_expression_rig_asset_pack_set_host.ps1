# Native regression for candidate multi-pack source-mask routing.
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
$installPath = [string](& $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath | Select-Object -First 1)
if (-not $installPath.Trim()) { throw "Visual Studio C++ Build Tools are required." }
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$outDir = Join-Path $repoRoot ".cache\host-tests\expression-rig-asset-pack-set"
$exe = Join-Path $outDir "test_expression_rig_asset_pack_set.exe"
$vsDevCmd = Join-Path $installPath.Trim() "Common7\Tools\VsDevCmd.bat"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$compile = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /utf-8 /std:c11 /I"{1}" "{2}" "{3}" "{4}" "{5}" /Fe:"{6}"' -f $vsDevCmd, $epaperRoot, (Join-Path $epaperRoot "tests\test_expression_rig_asset_pack_set.c"), (Join-Path $epaperRoot "asset_store.c"), (Join-Path $epaperRoot "expression_rig_asset_pack.c"), (Join-Path $epaperRoot "expression_rig_asset_pack_set.c"), $exe
Push-Location $outDir
try { & $env:ComSpec /d /s /c $compile; if ($LASTEXITCODE -ne 0) { throw "Native asset-pack-set compile failed." }; & $exe; if ($LASTEXITCODE -ne 0) { throw "Native asset-pack-set test failed." } } finally { Pop-Location }
