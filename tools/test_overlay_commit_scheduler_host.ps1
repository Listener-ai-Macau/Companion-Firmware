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
$testSource = Join-Path $epaperRoot "tests\test_overlay_commit_scheduler.c"
$schedulerSource = Join-Path $epaperRoot "overlay_commit_scheduler.c"
$outDir = Join-Path $repoRoot ".cache\host-tests\overlay-commit-scheduler"
$normalExe = Join-Path $outDir "overlay-commit-normal.exe"
$mutantSource = Join-Path $outDir "overlay-commit-failure-promoted.c"
$mutantExe = Join-Path $outDir "overlay-commit-mutant.exe"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

function Invoke-Compile([string] $source, [string] $exe) {
    $command = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /I"{1}" "{2}" "{3}" /Fe:"{4}"' -f `
        $vsDevCmd, $epaperRoot, $testSource, $source, $exe
    & $env:ComSpec /d /s /c $command
    if ($LASTEXITCODE -ne 0) {
        throw "Overlay commit scheduler compile failed with exit code $LASTEXITCODE."
    }
}

Invoke-Compile $schedulerSource $normalExe
& $normalExe
if ($LASTEXITCODE -ne 0) {
    throw "Normal overlay commit scheduler contract failed."
}

$sourceText = [IO.File]::ReadAllText($schedulerSource)
$guard = 'if (visible) {'
$mutated = 'if (true) {'
if (-not $sourceText.Contains($guard)) {
    throw "Visible-commit mutation anchor is missing."
}
[IO.File]::WriteAllText($mutantSource, $sourceText.Replace($guard, $mutated))
Invoke-Compile $mutantSource $mutantExe
$mutantError = Join-Path $outDir "overlay-commit-mutant.stderr.txt"
$mutantProcess = Start-Process -FilePath $mutantExe -Wait -PassThru `
    -NoNewWindow -RedirectStandardError $mutantError
if ($mutantProcess.ExitCode -eq 0) {
    throw "Promoting a failed transaction to visible did not fail the contract test."
}

Write-Output "MACHINE_READY: commit-driven overlay mutant was rejected."
