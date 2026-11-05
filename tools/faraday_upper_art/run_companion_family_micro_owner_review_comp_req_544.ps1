param(
  [switch]$CheckOnly,
  [string]$ExpectedPacketSha256
)
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '../..')
$validation = Join-Path $root 'docs/validation/companion-browser-family-micro-choreography-comp-req-544'
$packetPath = Join-Path $validation 'owner-review-packet.json'
$machinePath = Join-Path $validation 'MACHINE_READY.json'
if (-not $CheckOnly) { throw 'COMP-REQ-544 Execute is not authorized in this offline handoff' }
if (-not (Test-Path -LiteralPath $packetPath) -or -not (Test-Path -LiteralPath $machinePath)) { throw 'missing machine packet' }
$packetBytes = [IO.File]::ReadAllBytes($packetPath)
$packetSha = ([Security.Cryptography.SHA256]::Create().ComputeHash($packetBytes) | ForEach-Object ToString x2) -join ''
$packet = Get-Content -LiteralPath $packetPath -Raw | ConvertFrom-Json
$machine = Get-Content -LiteralPath $machinePath -Raw | ConvertFrom-Json
if ($ExpectedPacketSha256 -and $packetSha.ToUpperInvariant() -ne $ExpectedPacketSha256.ToUpperInvariant()) { throw 'packet hash mismatch' }
if ($packet.status -ne 'READY_DEFAULT_OFF' -or $packet.execute_authorized -ne $false) { throw 'packet is not default-off' }
if ($machine.status -ne 'MACHINE_READY' -or $machine.owner_gate -ne 'PENDING') { throw 'machine gate is not pending' }
Write-Output ('PASS_CHECKONLY_NO_EXECUTE ' + (@{process=0; browser=0; popup=0; hardware_contact=0; write=0; owner_prompt=0; microphone_permission_request=0} | ConvertTo-Json -Compress))
