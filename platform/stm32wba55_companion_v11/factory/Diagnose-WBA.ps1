param(
    [string]$Port,
    [string]$InputLog,
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [ValidateRange(1,300)][int]$Seconds = 15,
    [switch]$ListenOnly,
    [string]$ExpectedUid
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ([bool]$Port -eq [bool]$InputLog) { throw 'Specify exactly one of -Port or -InputLog.' }
$python = Get-Command python -ErrorAction Stop
$arguments = @((Join-Path $PSScriptRoot 'tools\diagnose_wba_uart.py'), '--output', $OutputDirectory,
    '--seconds', $Seconds)
if ($Port) { $arguments += @('--port', $Port) } else { $arguments += @('--input-log', $InputLog) }
if ($ListenOnly) { $arguments += '--listen-only' }
if ($ExpectedUid) { $arguments += @('--expected-uid', $ExpectedUid) }
& $python.Source @arguments
exit $LASTEXITCODE
