param(
    [string]$Output = ".cache/validation/comp-req-775-browser-device-single-source-final/64-life-trace-100-commits/MACHINE_READY.json"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$manifestPath = Join-Path $repoRoot ".cache\validation\comp-req-775-browser-device-single-source-final\97-recording-browser-timeline\source-pack-full\source-pack-manifest.json"
$epaperRoot = Join-Path $repoRoot "app\companion_pendant\epaper"
$traceSource = Join-Path $epaperRoot "tests\trace_motion_coordinator.c"
$coordinatorSource = Join-Path $epaperRoot "motion_coordinator.c"
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
$outDir = Join-Path $repoRoot ".cache\host-tests\comp-req-775-life-trace"
$exePath = Join-Path $outDir "trace_motion_coordinator.exe"
$tracePath = Join-Path $outDir "trace.txt"
$outputPath = if ([IO.Path]::IsPathRooted($Output)) { $Output } else { Join-Path $repoRoot $Output }

foreach ($required in @($manifestPath, $traceSource, $coordinatorSource, $vswhere)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing life-trace dependency: $required"
    }
}

$installPath = [string](& $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath | Select-Object -First 1)
$installPath = $installPath.Trim()
if (-not $installPath) {
    throw "Visual Studio C++ Build Tools are required for the life-trace test."
}
$vsDevCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $outputPath) | Out-Null

$compileCommand = 'call "{0}" -arch=x64 -host_arch=x64 >nul && cl.exe /nologo /W4 /WX /std:c11 /I"{1}" "{2}" "{3}" /Fe:"{4}"' -f `
    $vsDevCmd, $epaperRoot, $traceSource, $coordinatorSource, $exePath
Push-Location $outDir
try {
    & $env:ComSpec /d /s /c $compileCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Native life-trace compile failed with exit code $LASTEXITCODE."
    }
    & $exePath | Set-Content -LiteralPath $tracePath -Encoding ascii
    if ($LASTEXITCODE -ne 0) {
        throw "Native life-trace replay failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}

$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$families = @("calm", "curious", "delighted", "warm", "playful", "sleepy", "bashful", "thoughtful", "focused", "alert")
$rows = @(Get-Content -LiteralPath $tracePath | Where-Object { $_ })
$cursor = 0
$checks = [ordered]@{}
$observed = [ordered]@{}
$failures = [Collections.Generic.List[string]]::new()

foreach ($family in $families) {
    $expected = @($manifest.states | Where-Object { $_.kind -eq "life" -and $_.family -eq $family })
    $commits = 0
    $beats = 0
    $familyPass = $true
    while ($commits -lt 100) {
        if ($cursor -ge $rows.Count -or $beats -ge $expected.Count) {
            $familyPass = $false
            $failures.Add("$family trace ended before 100 commits") | Out-Null
            break
        }
        $fields = $rows[$cursor] -split '\|'
        $state = $expected[$beats]
        $actual = @(
            $fields[0], $fields[1], [int]$fields[2], [int]$fields[3],
            $fields[4], [int]$fields[5], [int]$fields[6], [int]$fields[7],
            $fields[8]
        )
        $wanted = @(
            [string]$state.family, [string]$state.life_action,
            [int]$state.action_episode, [int]$state.phrase,
            [string]$state.phase, [int]$state.variation,
            [int]$state.action_step, [int]$state.dwell_commits,
            [string]$state.id
        )
        if (($actual -join '|') -cne ($wanted -join '|')) {
            $familyPass = $false
            $failures.Add("$family beat $beats mismatch actual=$($actual -join '|') expected=$($wanted -join '|')") | Out-Null
            break
        }
        $commits += [int]$fields[7]
        $beats++
        $cursor++
    }
    $checks["${family}_first_100_commits_exact"] = $familyPass -and $commits -ge 100
    $observed[$family] = [ordered]@{ beats = $beats; commits = $commits }
    if (-not $familyPass) { break }
}

$checks["all_trace_rows_consumed"] = $cursor -eq $rows.Count
$checks["browser_seed_constant_bound"] = @(
    Select-String -LiteralPath $coordinatorSource -SimpleMatch "#define MOTION_LIVING_SEED 0x4d3c2b1au"
).Count -eq 1
$ready = @($checks.Values | Where-Object { -not $_ }).Count -eq 0
$receipt = [ordered]@{
    schema = "companion.comp_req_775.life_trace_100_commits.v1"
    status = if ($ready) { "MACHINE_READY" } else { "NO_GO" }
    checks = $checks
    failed_checks = @($checks.Keys | Where-Object { -not $checks[$_] })
    mismatches = @($failures)
    observed = $observed
    source = [ordered]@{
        page_sha256 = [string]$manifest.source.page_sha256
        manifest = $manifestPath
        trace = $tracePath
    }
}
$receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outputPath -Encoding utf8
$receipt | ConvertTo-Json -Depth 8
if (-not $ready) { exit 1 }
