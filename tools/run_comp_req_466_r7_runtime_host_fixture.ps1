param(
    [string]$OutRoot = '.cache/validation/comp-req-466-r7-runtime-host',
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$out = Join-Path $root $OutRoot
New-Item -ItemType Directory -Force -Path $out | Out-Null
$resultPath = Join-Path $out 'host-result.json'
$runnerPath = Join-Path $PSScriptRoot 'run_comp_req_466_r7_runtime_host_fixture.ps1'
$runnerSha = (Get-FileHash $runnerPath -Algorithm SHA256).Hash

function Write-CheckOnlyResult {
    $counters = [ordered]@{
        hardware_contact = 0; programmer = 0; serial = 0; write = 0
        reset = 0; refresh = 0; popup = 0; retry = 0
    }
    $result = [ordered]@{
        status = 'CHECK_ONLY_PASS'; checkonly = $counters; runner_sha256 = $runnerSha
        compiled = $false; executed = $false
    }
    $result | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 $resultPath
    Write-Output ($result | ConvertTo-Json -Compress)
}

if ($CheckOnly) {
    Write-CheckOnlyResult
    exit 0
}

function Find-MsvcVcvars {
    $vswhereCandidates = @(
        (Get-Command vswhere.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1),
        (Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'),
        (Join-Path $env:ProgramFiles 'Microsoft Visual Studio/Installer/vswhere.exe')
    ) | Where-Object { $_ -and (Test-Path $_) }
    foreach ($vswhere in $vswhereCandidates) {
        $install = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2>$null | Select-Object -First 1
        if ($install) {
            $candidate = Get-ChildItem (Join-Path $install 'VC/Auxiliary/Build') -Filter vcvars64.bat -File -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($candidate) { return $candidate.FullName }
        }
    }
    $roots = @(${env:ProgramFiles(x86)}, $env:ProgramFiles) | Where-Object { $_ -and (Test-Path (Join-Path $_ 'Microsoft Visual Studio')) }
    foreach ($rootPath in $roots) {
        $candidate = Get-ChildItem (Join-Path $rootPath 'Microsoft Visual Studio') -Recurse -Filter vcvars64.bat -File -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($candidate) { return $candidate.FullName }
    }
    return $null
}

function Invoke-MsvcBuild($mode, $vcvars, $exe, $log) {
    $include = Join-Path $root 'app/companion_pendant/epaper'
    $bridge = Join-Path $root 'app/companion_pendant/epaper/r7_runtime_bridge_stm32wb.c'
    $fixture = Join-Path $root 'tools/comp_req_466_r7_runtime_host_fixture.c'
    $defs = '/DCOMPANION_R7_RUNTIME_HOST_TEST=1 /DCOMPANION_EPAPER_SSD1681_HAS_BUSY=1'
    if ($mode -eq 'continuous') { $defs += ' /DCOMPANION_EPAPER_SSD1681_R7_RUNTIME_CONTINUOUS_DIAGNOSTIC=1' }
    $command = 'call "' + $vcvars + '" >nul && cl.exe /nologo /TC /std:c11 /W4 /WX ' + $defs +
        ' /I"' + $include + '" "' + $fixture + '" "' + $bridge + '" /Fe:"' + $exe + '"'
    cmd.exe /d /s /c $command 2>&1 | Set-Content -Encoding utf8 $log
    if ($LASTEXITCODE -ne 0) { throw "MSVC host compile failed: $mode" }
}

$cl = Get-Command cl.exe -ErrorAction SilentlyContinue
$vcvars = $null
$compilerKind = $null
if ($cl) { $compilerKind = 'cl-path' }
else { $vcvars = Find-MsvcVcvars; if ($vcvars) { $compilerKind = 'msvc-vcvars' } }
if (-not $compilerKind) {
    $result = [ordered]@{ status='NO_GO'; reason='native host C compiler unavailable'; compiled=$false; executed=$false; runner_sha256=$runnerSha }
    $result | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 $resultPath
    Write-Output ($result | ConvertTo-Json -Compress)
    exit 1
}

$bridge = Join-Path $root 'app/companion_pendant/epaper/r7_runtime_bridge_stm32wb.c'
$fixture = Join-Path $root 'tools/comp_req_466_r7_runtime_host_fixture.c'
$include = Join-Path $root 'app/companion_pendant/epaper'
$runs = @()
foreach ($mode in @('bounded','continuous')) {
    $exe = Join-Path $out ("r7-runtime-host-" + $mode + ".exe")
    $log = Join-Path $out ("compile-" + $mode + ".log")
    if ($cl) {
        $defs = '/DCOMPANION_R7_RUNTIME_HOST_TEST=1 /DCOMPANION_EPAPER_SSD1681_HAS_BUSY=1'
        if ($mode -eq 'continuous') { $defs += ' /DCOMPANION_EPAPER_SSD1681_R7_RUNTIME_CONTINUOUS_DIAGNOSTIC=1' }
        & $cl.Source /nologo /TC /std:c11 /W4 /WX $defs (('/I' + $include)) $fixture $bridge (('/Fe:' + $exe)) 2>&1 | Set-Content -Encoding utf8 $log
        if ($LASTEXITCODE -ne 0) { throw "host compile failed: $mode" }
    } else {
        Invoke-MsvcBuild $mode $vcvars $exe $log
    }
    $stdout = & $exe 2>&1 | Out-String
    $code = $LASTEXITCODE
    $runs += [ordered]@{ mode=$mode; exit_code=$code; stdout=$stdout.Trim() }
    if ($code -ne 0) { throw "host fixture failed: $mode" }
}
$checkonlyRoot = '.cache/validation/comp-req-466-r7-runtime-checkonly'
$result = [ordered]@{ status='PASS'; compiled=$true; executed=$true; compiler=$compilerKind; runner_sha256=$runnerSha; runs=$runs; checkonly_artifact=$checkonlyRoot }
$result | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 $resultPath
Write-Output ($result | ConvertTo-Json -Compress)
