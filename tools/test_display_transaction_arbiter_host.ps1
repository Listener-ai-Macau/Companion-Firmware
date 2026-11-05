param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) {
    throw "Visual Studio C++ Build Tools are required."
}

$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$testSource = Join-Path $epaperRoot "tests\test_motion_display_queue.c"
$queueSource = Join-Path $epaperRoot "display_queue.c"
$expressionSource = Join-Path $epaperRoot "expression_state.c"
$outDir = Join-Path $repoRoot ".cache\host-tests\display-transaction-arbiter"
$normalExe = Join-Path $outDir "arbiter-normal.exe"
$mutantSource = Join-Path $outDir "display_queue-boundary-guard-removed.c"
$mutantExe = Join-Path $outDir "arbiter-mutant.exe"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

function Invoke-Compile([string] $source, [string] $exe) {
    $command = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /I"{1}" "{2}" "{3}" "{4}" /Fe:"{5}"' -f `
        $vsDevCmd, $epaperRoot, $testSource, $source, $expressionSource, $exe
    & $env:ComSpec /d /s /c $command
    if ($LASTEXITCODE -ne 0) {
        throw "Display arbiter compile failed with exit code $LASTEXITCODE."
    }
}

Invoke-Compile $queueSource $normalExe
& $normalExe
if ($LASTEXITCODE -ne 0) {
    throw "Normal display arbiter contract failed."
}

$sourceText = [IO.File]::ReadAllText($queueSource)
$guard = '} else if (comp_epaper_display_queue_boundary_owned(queue)) {'
$mutated = '} else if (false) {'
if (-not $sourceText.Contains($guard)) {
    throw "Boundary guard mutation anchor is missing."
}
[IO.File]::WriteAllText($mutantSource, $sourceText.Replace($guard, $mutated))
Invoke-Compile $mutantSource $mutantExe
$mutantError = Join-Path $outDir "arbiter-mutant.stderr.txt"
$mutantProcess = Start-Process -FilePath $mutantExe -Wait -PassThru `
    -NoNewWindow -RedirectStandardError $mutantError
if ($mutantProcess.ExitCode -eq 0) {
    throw "Removing boundary ownership guard did not fail the contract test."
}

Write-Output "MACHINE_READY: boundary ownership mutant was rejected."
