param(
    [switch]$Execute,
    [string]$ProbeSerial,
    [switch]$NrstConnected,
    [ValidateSet(50, 1000, 4000, 8000)]
    [int]$SwdFrequency = 1000,
    [string]$OutputDirectory,
    [string]$ResumeDirectory,
    [string]$Programmer = 'C:\ST\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe'
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
# Distributed at the root of the factory kit. Default runs offline preflight.
$python = Get-Command python -ErrorAction Stop
$arguments = @((Join-Path $PSScriptRoot 'tools\provision_wba_v11.py'),
    '--package', (Join-Path $PSScriptRoot 'firmware'),
    '--loader-dir', (Join-Path $PSScriptRoot 'loader'), '--swd-frequency', $SwdFrequency)
if ($OutputDirectory) { $arguments += @('--output', $OutputDirectory) }
if ($ResumeDirectory) { $arguments += @('--resume', $ResumeDirectory) }
if ($NrstConnected) { $arguments += '--nrst-connected' }
if ($Execute) {
    if (-not $ProbeSerial) { throw 'Specify the ST-LINK serial with -ProbeSerial. No board has been accessed.' }
    $arguments += @('--execute', '--board', 'companion-v1.1-wba55',
        '--probe-serial', $ProbeSerial, '--programmer', $Programmer)
}
& $python.Source @arguments
exit $LASTEXITCODE
