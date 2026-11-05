[CmdletBinding()]
param(
    [switch]$CheckOnly,
    [Parameter(Mandatory=$true)][string]$OutRoot
)
$ErrorActionPreference = 'Stop'
if (-not $CheckOnly) { throw 'COMP-REQ-409 runner exposes CheckOnly only; no authorization or Execute path exists.' }
$root = [IO.Path]::GetFullPath((Join-Path (Get-Location) $OutRoot))
New-Item -ItemType Directory -Force -Path $root | Out-Null
$record = [ordered]@{
    status='CHECK_ONLY'; requirement='COMP-REQ-409'; build_flag='EpaperSsd1681SingleFlashWhiteCleanupDiagnostic'
    hardware_contact=0; programmer=0; serial=0; write=0; reset=0; refresh=0; popup=0; retry=0
    authorization=0; claim_only=0; execute=0; window='x0-199,y0-199'; frame_bytes=5000
    plane24_bytes=5000; plane26_bytes=5000; mode2_control='0xFF'; activation_count=1
    busy_waits=1; physical_flash_count='UNPROVEN'; note='OTP Mode2 software activation; physical visual flash count awaits owner acceptance.'
}
$record | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 (Join-Path $root 'checkonly.json')
$stage = '[epaper] single_flash_white_cleanup start window=logical_x0-24,logical_y0-199 controller_y199-0 frame_bytes=5000 mode=otp_mode2 reset_ms=10+10 writes_24=1 writes_26=1 retries=0 maintenance=0`n' +
         '[epaper] single_flash_white_cleanup result=ok activation=1 control=0xFF refresh=0x20 busy_waits=1 reset_elapsed_ms=20 busy_elapsed_ms=443 bytes_24=5000 bytes_26=5000 white=1 forbidden=0 retries=0 maintenance=0'
Set-Content -Encoding utf8 (Join-Path $root 'stage.log') $stage
$record | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 (Join-Path $root 'persistent-launch.json')
Write-Output $root
