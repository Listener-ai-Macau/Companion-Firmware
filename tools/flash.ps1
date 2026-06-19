param(
    [switch] $CheckOnly,
    [switch] $Execute,
    [switch] $WorkflowLockHeld,
    [switch] $FlashReference,
    [string] $ProgrammerPath,
    [string] $Port = "SWD"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$referenceHexRelative = "third_party\STM32CubeWB\Projects\P-NUCLEO-WB55.Nucleo\Applications\BLE\BLE_p2pServer\Binary\BLE_p2pServer_reference.hex"
$bleStackRelative = "third_party\STM32CubeWB\Projects\STM32WB_Copro_Wireless_Binaries\STM32WB5x\stm32wb5x_BLE_Stack_full_fw.bin"
$referenceHex = Join-Path $repoRoot $referenceHexRelative
$bleStackBinary = Join-Path $repoRoot $bleStackRelative

function Assert-Path {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $Label
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing $Label`: $Path. Run tools\bootstrap_stm32cubewb.ps1 first."
    }
}

function Find-CubeProgrammerCli {
    param([string] $RequestedPath)

    $candidates = @()
    if ($RequestedPath) { $candidates += $RequestedPath }
    if ($env:STM32CUBEPROGRAMMER_CLI) { $candidates += $env:STM32CUBEPROGRAMMER_CLI }
    if ($env:STM32CUBEPROGRAMMER_PATH) { $candidates += (Join-Path $env:STM32CUBEPROGRAMMER_PATH "STM32_Programmer_CLI.exe") }

    foreach ($commandName in @("STM32_Programmer_CLI.exe", "STM32_Programmer_CLI")) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($command) { $candidates += $command.Source }
    }

    $candidates += @(
        "C:\Program Files\STMicroelectronics\STM32Cube\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe",
        "C:\ST\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe"
    )

    foreach ($candidate in $candidates) {
        if ([string]::IsNullOrWhiteSpace($candidate)) { continue }
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return (Resolve-Path -LiteralPath $candidate).Path }
    }

    return $null
}

Assert-Path -Path $referenceHex -Label "BLE_p2pServer reference hex"
Assert-Path -Path $bleStackBinary -Label "WB55 BLE full stack binary"

$programmer = Find-CubeProgrammerCli -RequestedPath $ProgrammerPath
$lockCommand = "pwsh -NoProfile -File <ai-collaboration-workflow>\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose `"flash Companion WB55 official BLE starter`" -Run pwsh -NoProfile -File .\tools\flash.ps1 -Execute -WorkflowLockHeld -FlashReference"

if ($CheckOnly) {
    if ($programmer) {
        Write-Output "CHECK: STM32CubeProgrammer CLI found: $programmer"
    } else {
        Write-Output "CHECK: STM32CubeProgrammer CLI not found. Install STM32CubeProgrammer or set -ProgrammerPath/STM32CUBEPROGRAMMER_CLI before real flashing."
    }
    Write-Output "CHECK: Reference hex exists: $referenceHexRelative"
    Write-Output "CHECK: BLE full stack binary exists: $bleStackRelative"
    Write-Output "CHECK: Real flash must run inside workflow lock:"
    Write-Output "  $lockCommand"
    exit 0
}

if (-not $Execute) {
    throw "Refusing to flash without -Execute. For a dry check, use -CheckOnly."
}

if (-not $WorkflowLockHeld) {
    throw "Refusing to flash without workflow lock acknowledgement. Run under aiw with-lock -Resource Companion-WB55 and pass -WorkflowLockHeld inside the locked command."
}

if (-not $FlashReference) {
    throw "No flash target selected. Pass -FlashReference to flash the official BLE_p2pServer reference image."
}

if (-not $programmer) {
    throw "STM32CubeProgrammer CLI not found. Install STM32CubeProgrammer, add STM32_Programmer_CLI.exe to PATH, or pass -ProgrammerPath."
}

$args = @(
    "-c", "port=$Port",
    "-w", $referenceHex,
    "-v",
    "-rst"
)

Write-Output "Flashing official BLE_p2pServer reference image with $programmer"
& $programmer @args
if ($LASTEXITCODE -ne 0) {
    throw "STM32CubeProgrammer flash failed with exit code $LASTEXITCODE."
}

Write-Output "PASS: Official BLE_p2pServer reference image flashed."
