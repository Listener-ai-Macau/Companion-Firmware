param(
    [Parameter(Mandatory = $true)]
    [string]$KitRoot,
    [switch]$ExecuteInstall,
    [string]$ProbeSerial,
    [switch]$NrstConnected,
    [string]$InstallOutput,
    [string]$ResumeDirectory,
    [string]$Programmer = 'C:\ST\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe',
    [string]$InstallResult,
    [string]$TypeDeviceCheck,
    [string]$FullChainAcceptance,
    [string]$StateOutput
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$kit = (Resolve-Path -LiteralPath $KitRoot).Path
$installEntry = Join-Path $kit 'Install-WBA.ps1'
$verifierCandidates = @(
    (Join-Path $kit 'tools\verify_wba_v11_board_arrival.py'),
    (Join-Path $PSScriptRoot '..\..\..\tools\verify_wba_v11_board_arrival.py')
)
$verifier = $verifierCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if (-not $verifier) { throw 'verify_wba_v11_board_arrival.py was not found in the kit or source tree.' }
if (-not (Test-Path -LiteralPath $installEntry -PathType Leaf)) { throw "Factory entry is missing: $installEntry" }

if ($ExecuteInstall) {
    if ([string]::IsNullOrWhiteSpace($ProbeSerial)) { throw '-ExecuteInstall requires -ProbeSerial.' }
    if ([string]::IsNullOrWhiteSpace($InstallOutput)) { throw '-ExecuteInstall requires a new, explicit -InstallOutput directory.' }
    $installArgs = @('-NoProfile', '-File', $installEntry, '-Execute', '-ProbeSerial', $ProbeSerial,
        '-OutputDirectory', $InstallOutput, '-Programmer', $Programmer)
    if (-not [string]::IsNullOrWhiteSpace($ResumeDirectory)) {
        $installArgs += @('-ResumeDirectory', $ResumeDirectory)
    }
    if ($NrstConnected) { $installArgs += '-NrstConnected' }
    & pwsh @installArgs
    if ($LASTEXITCODE -ne 0) { throw "WBA initial installation failed with exit code $LASTEXITCODE." }
    $InstallResult = Join-Path $InstallOutput 'result.json'
}

$python = (Get-Command python -ErrorAction Stop).Source
$verifyArgs = @($verifier, '--kit', $kit)
if (-not [string]::IsNullOrWhiteSpace($InstallResult)) {
    $verifyArgs += @('--install-result', ([System.IO.Path]::GetFullPath($InstallResult)))
}
if (-not [string]::IsNullOrWhiteSpace($TypeDeviceCheck)) {
    $verifyArgs += @('--type-device-check', ([System.IO.Path]::GetFullPath($TypeDeviceCheck)))
}
if (-not [string]::IsNullOrWhiteSpace($FullChainAcceptance)) {
    $verifyArgs += @('--full-chain-acceptance', ([System.IO.Path]::GetFullPath($FullChainAcceptance)))
}
if (-not [string]::IsNullOrWhiteSpace($StateOutput)) {
    $verifyArgs += @('--output', ([System.IO.Path]::GetFullPath($StateOutput)))
}
& $python @verifyArgs
if ($LASTEXITCODE -ne 0) { throw "WBA board-arrival evidence gate failed with exit code $LASTEXITCODE." }

Write-Output ''
Write-Output 'Next stage is determined by the result field above.'
Write-Output 'READY_FOR_TYPE_DEVICE_CHECK: run the installed Companion Type device check and save its JSON artifact.'
Write-Output 'READY_FOR_FULL_CHAIN: run real board codec=3 capture, disconnect/resume, Type pull, real ASR and both minutes modes.'
Write-Output 'BLOCKED_HARDWARE_IDENTITY_BINDING: app GATT identity is valid but cannot yet be bound to the installer MCU UID; do not edit the JSON to bypass it.'
Write-Output 'READY_FOR_MANUAL_HARDWARE_CHECKS: machine evidence is complete; display, touch and power still require physical checks.'
Write-Output 'READY_FOR_OWNER_REVIEW: machine evidence is complete; the final blocking Owner window is still required and was not opened here.'
