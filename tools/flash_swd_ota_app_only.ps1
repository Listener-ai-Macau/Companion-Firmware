<#
.SYNOPSIS
  SWD-flash ONLY an OTA App image (0x08007000..). Refuses anything that can
  overwrite the resident OTA Loader.

.DESCRIPTION
  Product board layout:
    - OTA Loader lives below 0x08007000
    - App must be built with OTA_APP=1 (vector + magic at 0x08007000)

  NEVER call STM32_Programmer_CLI with a 0x08000000 full-chip bringup/FreeRTOS
  hex. That path is what wiped Loader+App when a concurrent agent direct-flashed.

  Preferred product update: BLE denzic_ota_v1 package (Type --firmware-ota-transfer).
  This script is the only allowed SWD app write for agents/tools on NUCLEO-WB55.

.EXAMPLE
  pwsh -NoProfile -File .\tools\flash_swd_ota_app_only.ps1 `
    -ImagePath .\cubeide\Companion_Nucleo_WB55RG_Bringup\build_ota\Companion_Nucleo_WB55RG_Bringup_ota_app.hex
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$ImagePath,
    [switch]$CheckOnly,
    [ValidateRange(30, 600)]
    [int]$FlashTimeoutSeconds = 120,
    [string]$ProgrammerRoot = 'C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins',
    [string]$Purpose = 'flash OTA App only (SWD)'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'companion_wb55_lock.ps1')

$otaAppGuard = Join-Path $repoRoot 'tools\faraday_upper_art\verify_companion_ota_app_hex.py'
$layoutReceipt = Join-Path $repoRoot '.cache\validation\flash-nucleo\ota-app-layout-swd-only.json'

if (-not (Test-Path -LiteralPath $ImagePath -PathType Leaf)) {
    throw "Image not found: $ImagePath"
}
if (-not (Test-Path -LiteralPath $otaAppGuard -PathType Leaf)) {
    throw "OTA App layout guard missing: $otaAppGuard"
}

Write-Host "GUARD: pre-start refuse Loader overwrite — verifying $ImagePath"
& python $otaAppGuard --hex $ImagePath --receipt $layoutReceipt | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw (
        "REFUSED before any SWD write: image is not a valid Companion OTA App " +
        "(must be OTA_APP=1 at 0x08007000). Do NOT pass FreeRTOS/bringup hex " +
        "built at 0x08000000. receipt=$layoutReceipt"
    )
}
Write-Host "GUARD: ota_app_layout=MACHINE_READY (safe to write app region only)"

if ($CheckOnly) {
    Write-Output "CHECK: image=$((Resolve-Path -LiteralPath $ImagePath).Path)"
    Write-Output "CHECK: ota_app_layout=MACHINE_READY"
    Write-Output "CHECK: ota_app_layout_receipt=$layoutReceipt"
    Write-Output "CHECK: next_step=flash under Companion-WB55 lock (not run)"
    exit 0
}

$programmer = Get-ChildItem -LiteralPath $ProgrammerRoot -Recurse -Filter STM32_Programmer_CLI.exe |
    Select-Object -First 1 -ExpandProperty FullName
if (-not $programmer) {
    throw "STM32_Programmer_CLI.exe not found under $ProgrammerRoot"
}

$logDir = Join-Path $repoRoot '.cache\validation\flash-nucleo'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$stdoutPath = Join-Path $logDir "stm32-programmer-ota-app-$stamp-$PID.stdout.log"
$stderrPath = Join-Path $logDir "stm32-programmer-ota-app-$stamp-$PID.stderr.log"

$programmerArgs = @(
    '-c', 'port=SWD', 'mode=UR', 'reset=HWrst', 'freq=4000',
    '-w', (Resolve-Path -LiteralPath $ImagePath).Path,
    '-v', '-rst'
)

$hardwareLock = $null
try {
    $hardwareLock = Enter-CompanionWb55Lock -Purpose $Purpose
    Write-Host "LOCK: Companion-WB55 $($hardwareLock.mode) run=$($hardwareLock.run_id)"
    Write-Host "RUN: $programmer $($programmerArgs -join ' ')"
    $process = Start-Process `
        -FilePath $programmer `
        -ArgumentList $programmerArgs `
        -RedirectStandardOutput $stdoutPath `
        -RedirectStandardError $stderrPath `
        -WindowStyle Hidden `
        -PassThru
    $completed = $process.WaitForExit($FlashTimeoutSeconds * 1000)
    if (-not $completed) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        throw "flash timed out after $FlashTimeoutSeconds s. stdout=$stdoutPath"
    }
    $process.WaitForExit()
    if (Test-Path -LiteralPath $stdoutPath) {
        Get-Content -LiteralPath $stdoutPath | ForEach-Object { Write-Host $_ }
    }
    if (Test-Path -LiteralPath $stderrPath) {
        Get-Content -LiteralPath $stderrPath | ForEach-Object { Write-Host $_ }
    }
    if ([int]$process.ExitCode -ne 0) {
        throw "flash failed exit=$($process.ExitCode) stdout=$stdoutPath"
    }
    Write-Host "OK: OTA App SWD flash finished under lock; Loader region not targeted by layout guard."
} finally {
    if ($hardwareLock) {
        Exit-CompanionWb55Lock
    }
}
