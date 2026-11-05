$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$out = Join-Path $root '.cache/validation/comp-req-778-recording-journal-host'
New-Item -ItemType Directory -Force $out | Out-Null
$vcvars = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/2022/BuildTools/VC/Auxiliary/Build/vcvars64.bat'
if (-not (Test-Path $vcvars)) { throw 'MSVC vcvars64.bat unavailable' }
$exe = Join-Path $out 'comp-req-778-recording-journal-host.exe'
$sources = @(
    'app/companion_pendant/recording/tests/test_companion_recording_journal.c',
    'app/companion_pendant/recording/companion_recording_journal.c'
)
$args = ($sources | ForEach-Object { '"' + (Join-Path $root $_) + '"' }) -join ' '
$include = Join-Path $root 'app/companion_pendant/recording'
$cmd = 'call "' + $vcvars + '" >nul && cl.exe /nologo /Brepro /TC /std:c11 /O2 /W4 /WX /I"' + $include + '" ' + $args + ' /Fe:"' + $exe + '"'
$compileLog = Join-Path $out 'compile.log'
Push-Location -LiteralPath $out
try { cmd /d /s /c $cmd *> $compileLog }
finally { Pop-Location }
if ($LASTEXITCODE -ne 0) { throw "recording journal host compile failed: $LASTEXITCODE" }
$stdout = (& $exe 2>&1 | Out-String).Trim()
$exitCode = $LASTEXITCODE
$result = [ordered]@{
    schema = 'companion.comp_req_778.recording_journal.host.v1'
    status = if ($exitCode -eq 0 -and $stdout -match '^PASS_') { 'PASS' } else { 'NO_GO' }
    compile_command = $cmd
    compile_log_sha256 = (Get-FileHash $compileLog -Algorithm SHA256).Hash.ToUpper()
    executable_sha256 = (Get-FileHash $exe -Algorithm SHA256).Hash.ToUpper()
    exit_code = $exitCode
    stdout = $stdout
    source_sha256 = [ordered]@{}
}
foreach ($source in $sources) {
    $result.source_sha256[$source] = (Get-FileHash (Join-Path $root $source) -Algorithm SHA256).Hash.ToUpper()
}
$result | ConvertTo-Json -Depth 6 | Set-Content -Encoding utf8 (Join-Path $out 'result.json')
Write-Output $stdout
if ($result.status -ne 'PASS') { exit 2 }
