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
$epaper = Join-Path $repoRoot "app\companion_pendant\epaper"
$runtime = Join-Path $repoRoot "app\companion_pendant\runtime"
$playback = Join-Path $repoRoot "app\companion_pendant\playback"
$touch = Join-Path $repoRoot "app\companion_pendant\touch"
$imu = Join-Path $repoRoot "app\companion_pendant\imu"
$audioContract = Join-Path $repoRoot "third_party\denzic-platform\audio\embedded\c\include"
$presenterSource = Join-Path $epaper "screen_presenter_wba.c"
$presenterHeader = Join-Path $epaper "screen_presenter_wba.h"
$panelSource = Join-Path $epaper "ssd1681_wba.c"
$policySource = Join-Path $epaper "refresh_policy.c"
$testSource = Join-Path $epaper "tests\test_screen_presenter_wba.c"
$outDir = Join-Path $repoRoot ".cache\wba-screen-presenter-host"
$exe = Join-Path $outDir "test_screen_presenter_wba.exe"
$m33Object = Join-Path $outDir "screen_presenter_wba_m33.o"
$result = Join-Path $outDir "result.json"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$includeArgs = '/I"{0}" /I"{1}" /I"{2}" /I"{3}" /I"{4}" /I"{5}"' -f `
    $epaper, $runtime, $playback, $touch, $imu, $audioContract
$command = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 {1} "{2}" "{3}" "{4}" "{5}" /Fe:"{6}"' -f `
    $vsDevCmd, $includeArgs, $presenterSource, $panelSource, $policySource, $testSource, $exe
& $env:ComSpec /d /s /c $command
if ($LASTEXITCODE -ne 0) { throw "WBA screen presenter host compile failed." }
$output = (& $exe | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $output -notlike "PASS:*") {
    throw "WBA screen presenter host test failed: $output"
}
Write-Host $output

$arm = Get-Command arm-none-eabi-gcc -ErrorAction Stop
$armArgs = @(
    "-std=c11", "-mcpu=cortex-m33", "-mthumb", "-mfloat-abi=soft",
    "-ffreestanding", "-fno-common", "-Wall", "-Wextra", "-Werror",
    "-Wconversion", "-Wshadow", "-Wdouble-promotion", "-Wformat=2",
    "-pedantic", "-I$epaper", "-I$runtime", "-I$playback", "-I$touch",
    "-I$imu", "-I$audioContract", "-c", $presenterSource, "-o", $m33Object
)
& $arm.Source @armArgs
if ($LASTEXITCODE -ne 0) { throw "WBA screen presenter Cortex-M33 compile failed." }
$m33Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $m33Object).Hash

[ordered]@{
    schema_id = "companion.wba_screen_presenter_host.v1"
    status = "PASS_HOST_ONLY"
    hardware = "NOT_RUN"
    output = $output
    physical_mapping = "ACCEPTED_WB_VERTICAL_ROW_FLIP_PENDING_V11_HARDWARE"
    reset_net = "HARDWARE_CALLBACK_REQUIRED_OR_EXPLICIT_SOFTWARE_ONLY"
    m33_object_sha256 = $m33Hash
    sources = [ordered]@{
        presenter_c = (Get-FileHash -Algorithm SHA256 -LiteralPath $presenterSource).Hash
        presenter_h = (Get-FileHash -Algorithm SHA256 -LiteralPath $presenterHeader).Hash
        test = (Get-FileHash -Algorithm SHA256 -LiteralPath $testSource).Hash
    }
} | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -LiteralPath $result
Write-Host "m33_object_sha256=$m33Hash"
Write-Host "result=$result"
