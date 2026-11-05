[CmdletBinding()]
param(
    [switch]$CheckOnly,
    [Parameter(Mandatory=$true)][string]$OutRoot
)
$ErrorActionPreference = 'Stop'
if (-not $CheckOnly) { throw 'COMP-REQ-409 launcher is CheckOnly-only; physical authorization is intentionally absent.' }
$runner = Join-Path $PSScriptRoot 'run_wb55_ssd1681_single_flash_white_cleanup.ps1'
& $runner -CheckOnly -OutRoot $OutRoot
