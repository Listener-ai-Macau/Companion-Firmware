param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) {
    throw "Visual Studio vswhere.exe is required for the native emote asset pack test."
}

$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) {
    throw "Visual Studio C++ Build Tools are required for the native emote asset pack test."
}

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$testSource = Join-Path $epaperRoot "tests\test_emote_asset_pack_self_test.c"
$packSource = Join-Path $epaperRoot "emote_asset_pack.c"
$playerSource = Join-Path $epaperRoot "emote_player.c"
$storeSource = Join-Path $epaperRoot "asset_store.c"
$outDir = Join-Path $repoRoot ".cache\host-tests\emote-asset-pack"
$exePath = Join-Path $outDir "test_emote_asset_pack_self_test.exe"
foreach ($required in @($vsDevCmd, $testSource, $packSource, $playerSource, $storeSource)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing host emote asset pack dependency: $required"
    }
}
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$compileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /I"{1}" "{2}" "{3}" "{4}" "{5}" /Fe:"{6}"' -f `
    $vsDevCmd, $epaperRoot, $testSource, $packSource, $playerSource, $storeSource, $exePath
Push-Location $outDir
try {
    & $env:ComSpec /d /s /c $compileCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Native emote asset pack compile failed with exit code $LASTEXITCODE."
    }
    & $exePath
    if ($LASTEXITCODE -ne 0) {
        throw "Native emote asset pack test failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
