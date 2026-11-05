$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$out = Join-Path $root '.cache/validation/comp-req-558-recording-host'
New-Item -ItemType Directory -Force $out | Out-Null
$vcvars = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/2022/BuildTools/VC/Auxiliary/Build/vcvars64.bat'
if (-not (Test-Path $vcvars)) { throw 'MSVC vcvars64.bat unavailable' }
$exe = Join-Path $out 'comp-req-558-recording-host.exe'
$wav = Join-Path $root 'comp-req-558-recording.wav'
if (Test-Path $exe) { Remove-Item -LiteralPath $exe -Force }
if (Test-Path $wav) { Remove-Item -LiteralPath $wav -Force }
$sources = @(
  'tools/comp_req_558_recording_host.c',
  'app/companion_pendant/recording/companion_recording_gatt_product.c'
  ,'app/companion_pendant/recording/companion_recording_gatt_adapter.c'
)
$args = ($sources | ForEach-Object { '"' + (Join-Path $root $_) + '"' }) -join ' '
$cmd = 'call "' + $vcvars + '" >nul && cl.exe /nologo /Brepro /TC /std:c11 /O2 /W4 /WX /I"' + (Join-Path $root 'app/companion_pendant/recording') + '" ' + $args + ' /Fe:"' + $exe + '"'
$compileLog = Join-Path $out 'compile.log'
cmd /d /s /c $cmd *> $compileLog
$compileExit = $LASTEXITCODE
if ($compileExit -ne 0) { throw "recording host compile failed: $compileExit" }
$stdout = (& $exe 2>&1 | Out-String).Trim()
$exitCode = $LASTEXITCODE
$pcmSha = $null
$metadataSha = $null
if (Test-Path $wav) {
  $wavBytes = [IO.File]::ReadAllBytes($wav)
  if ($wavBytes.Length -ge 44) { $pcmSha = (Get-FileHash -InputStream ([IO.MemoryStream]::new($wavBytes[44..($wavBytes.Length - 1)])) -Algorithm SHA256).Hash.ToUpper() }
  if ($stdout -match 'metadata_sha256=([0-9A-Fa-f]{64})') { $metadataSha = $Matches[1].ToUpper() }
}
$result = [ordered]@{
  schema = 'companion.comp_req_558.recording.host.v1'
  status = if ($exitCode -eq 0) { 'PASS' } else { 'NO_GO' }
  compile_command = $cmd
  compile_log_sha256 = (Get-FileHash $compileLog -Algorithm SHA256).Hash.ToUpper()
  executable_sha256 = (Get-FileHash $exe -Algorithm SHA256).Hash.ToUpper()
  exit_code = $exitCode
  stdout = $stdout
  stdout_sha256 = [BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($stdout))).Replace('-', '')
  wav_sha256 = if (Test-Path $wav) { (Get-FileHash $wav -Algorithm SHA256).Hash.ToUpper() } else { $null }
  pcm_sha256 = $pcmSha
  metadata_sha256 = $metadataSha
  pcm_matches_metadata = ($null -ne $pcmSha -and $pcmSha -eq $metadataSha)
  source_sha256 = [ordered]@{}
}
foreach ($source in $sources) { $result.source_sha256[$source] = (Get-FileHash (Join-Path $root $source) -Algorithm SHA256).Hash.ToUpper() }
$result | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 (Join-Path $out 'result.json')
if ($exitCode -ne 0 -or -not $result.pcm_matches_metadata) { exit 2 }
