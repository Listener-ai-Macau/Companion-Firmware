param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) { throw "Visual Studio C++ Build Tools are required." }

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$testSource = Join-Path $epaperRoot "tests\test_display_track_arbiter.c"
$arbiterSource = Join-Path $epaperRoot "display_track_arbiter.c"
$outDir = Join-Path $repoRoot ".cache\host-tests\display-track-arbiter"
$exePath = Join-Path $outDir "test_display_track_arbiter.exe"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$command = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /I"{1}" "{2}" "{3}" /Fe:"{4}"' -f `
    $vsDevCmd, $epaperRoot, $testSource, $arbiterSource, $exePath
& $env:ComSpec /d /s /c $command
if ($LASTEXITCODE -ne 0) { throw "Display track arbiter compile failed." }
& $exePath
if ($LASTEXITCODE -ne 0) { throw "Display track arbiter contract failed." }

Write-Output "MACHINE_READY: independent track deadlines and fallback ordering passed."
