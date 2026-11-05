param(
    [string]$OutRoot = '.cache/validation/comp-req-466-r7-touch-integration'
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$out = Join-Path $root $OutRoot
New-Item -ItemType Directory -Force -Path $out | Out-Null
$runnerPath = Join-Path $PSScriptRoot 'run_comp_req_466_r7_touch_integration_fixture.ps1'
$runnerSha = (Get-FileHash $runnerPath -Algorithm SHA256).Hash
$include = Join-Path $root 'app/companion_pendant/epaper'
$touch = Join-Path $root 'app/companion_pendant/touch'
$sources = @(
    (Join-Path $root 'tools/comp_req_466_r7_touch_integration_fixture.c'),
    (Join-Path $root 'app/companion_pendant/epaper/r7_runtime_bridge_stm32wb.c'),
    (Join-Path $touch 'ft6336.c'),
    (Join-Path $touch 'touch_gesture.c'),
    (Join-Path $touch 'touch_tap_arbiter.c')
)
function Find-Vcvars {
    $candidates = @((Get-Command vswhere.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1),
        (Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'),
        (Join-Path $env:ProgramFiles 'Microsoft Visual Studio/Installer/vswhere.exe')) | Where-Object { $_ -and (Test-Path $_) }
    foreach ($vswhere in $candidates) {
        $install = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2>$null | Select-Object -First 1
        if ($install) {
            $candidate = Get-ChildItem (Join-Path $install 'VC/Auxiliary/Build') -Filter vcvars64.bat -File -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($candidate) { return $candidate.FullName }
        }
    }
    return $null
}
$vcvars = Find-Vcvars
if (-not $vcvars) { throw 'MSVC vcvars64.bat unavailable' }
$exe = Join-Path $out 'r7-touch-integration.exe'
$log = Join-Path $out 'compile.log'
$sourceArgs = ($sources | ForEach-Object { '"' + $_ + '"' }) -join ' '
$command = 'call "' + $vcvars + '" >nul && cl.exe /nologo /TC /std:c11 /W4 /WX /DCOMPANION_R7_RUNTIME_HOST_TEST=1 /DCOMPANION_EPAPER_SSD1681_HAS_BUSY=1 /I"' + $include + '" /I"' + $touch + '" ' + $sourceArgs + ' /Fe:"' + $exe + '"'
cmd.exe /d /s /c $command 2>&1 | Set-Content -Encoding utf8 $log
if ($LASTEXITCODE -ne 0) { throw 'touch integration compile failed' }
$stdout = & $exe 2>&1 | Out-String
$code = $LASTEXITCODE
$result = [ordered]@{
    status = if ($code -eq 0) { 'PASS' } else { 'NO_GO' }
    exit_code = $code
    runner_sha256 = $runnerSha
    source_paths = $sources
    source_sha256 = [ordered]@{}
    stdout = $stdout.Trim()
    hardware_contact = 0
    popup = 0
    checkonly = @{ hardware_contact=0; programmer=0; serial=0; write=0; reset=0; refresh=0; popup=0; retry=0 }
}
foreach ($source in $sources) {
    $result.source_sha256[$source] = (Get-FileHash $source -Algorithm SHA256).Hash
}
$result | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 (Join-Path $out 'touch-integration-result.json')
$result | ConvertTo-Json -Compress
if ($code -ne 0) { exit $code }
