param()

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$out = Join-Path $repo ".cache\host-tests\screen-lifecycle-journey"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$exe = Join-Path $out "test_screen_lifecycle_journey.exe"
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) {
  throw "Visual Studio vswhere.exe is required for the lifecycle journey."
}
$installPath = [string](& $vswhere -latest -products * `
  -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
  -property installationPath | Select-Object -First 1)
$vsDevCmd = Join-Path $installPath.Trim() "Common7\Tools\VsDevCmd.bat"
$epaper = Join-Path $repo "app\companion_pendant\epaper"
$test = Join-Path $epaper "tests\test_screen_lifecycle_journey.c"
$source = Join-Path $epaper "screen_lifecycle.c"
$compile = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /I"{1}" "{2}" "{3}" /Fe:"{4}"' -f `
  $vsDevCmd, $epaper, $test, $source, $exe

& $env:ComSpec /d /s /c $compile
if ($LASTEXITCODE -ne 0) { throw "Lifecycle journey compile failed." }

& $exe
exit $LASTEXITCODE
