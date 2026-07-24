param(
    [string]$ImagePath,
    [switch]$ScreenAssetProvision,
    [switch]$CheckOnly,
    [ValidateRange(30, 600)]
    [int]$FlashTimeoutSeconds = 120,
    [string]$ProgrammerRoot = 'C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins'
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'companion_wb55_lock.ps1')
$normalImagePath = Join-Path $PSScriptRoot '..\cubeide\Companion_Nucleo_WB55RG_Bringup\build\Companion_Nucleo_WB55RG_Bringup.hex'
$provisionImagePath = Join-Path $PSScriptRoot '..\cubeide\Companion_Nucleo_WB55RG_Bringup\build_screen_asset_provision\Companion_Nucleo_WB55RG_ScreenAssetProvision.hex'

function Invoke-ProgrammerWithTimeout {
    param(
        [Parameter(Mandatory = $true)][string]$Programmer,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][int]$TimeoutSeconds
    )

    $logDir = Join-Path $repoRoot '.cache\validation\flash-nucleo'
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $stdoutPath = Join-Path $logDir "stm32-programmer-$stamp-$PID.stdout.log"
    $stderrPath = Join-Path $logDir "stm32-programmer-$stamp-$PID.stderr.log"
    # Keep diagnostics off the success stream: callers capture this function's only
    # success-stream value as the programmer process exit code.
    Write-Host "RUN: $Programmer $($Arguments -join ' ')"
    Write-Host "RUN: flash_timeout_seconds=$TimeoutSeconds"
    $process = Start-Process `
        -FilePath $Programmer `
        -ArgumentList $Arguments `
        -RedirectStandardOutput $stdoutPath `
        -RedirectStandardError $stderrPath `
        -WindowStyle Hidden `
        -PassThru
    $completed = $process.WaitForExit($TimeoutSeconds * 1000)
    if (-not $completed) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        if (Test-Path -LiteralPath $stdoutPath) {
            Get-Content -LiteralPath $stdoutPath | ForEach-Object { Write-Host $_ }
        }
        if (Test-Path -LiteralPath $stderrPath) {
            Get-Content -LiteralPath $stderrPath | ForEach-Object { Write-Host $_ }
        }
        throw "flash timed out after $TimeoutSeconds second(s). stdout=$stdoutPath stderr=$stderrPath"
    }
    $process.WaitForExit()
    if (Test-Path -LiteralPath $stdoutPath) {
        Get-Content -LiteralPath $stdoutPath | ForEach-Object { Write-Host $_ }
    }
    if (Test-Path -LiteralPath $stderrPath) {
        Get-Content -LiteralPath $stderrPath | ForEach-Object { Write-Host $_ }
    }
    Write-Host "RUN: stdout=$stdoutPath"
    Write-Host "RUN: stderr=$stderrPath"
    return [int]$process.ExitCode
}

if ($ScreenAssetProvision -and -not [string]::IsNullOrWhiteSpace($ImagePath)) {
    throw "Use either -ScreenAssetProvision or -ImagePath, not both."
}

if ($ScreenAssetProvision) {
    throw "Screen asset provisioning is blocked by the active Companion Goal: the v9 CEMP is machine-only and runtime-inactive until its source/activation gate passes."
}

if ([string]::IsNullOrWhiteSpace($ImagePath)) {
    $ImagePath = if ($ScreenAssetProvision) { $provisionImagePath } else { $normalImagePath }
}

if (-not (Test-Path -LiteralPath $ImagePath)) {
    throw "Image not found: $ImagePath"
}

$programmer = Get-ChildItem -LiteralPath $ProgrammerRoot -Recurse -Filter STM32_Programmer_CLI.exe |
    Select-Object -First 1 -ExpandProperty FullName
if (-not $programmer) {
    throw "STM32_Programmer_CLI.exe not found under $ProgrammerRoot"
}

if ($CheckOnly) {
    Write-Output "CHECK: mode=$(if ($ScreenAssetProvision) { 'screen_asset_provision' } else { 'normal' })"
    Write-Output "CHECK: image=$((Resolve-Path -LiteralPath $ImagePath).Path)"
    Write-Output "CHECK: programmer=$programmer"
    Write-Output "CHECK: flash_timeout_seconds=$FlashTimeoutSeconds"
    exit 0
}

$programmerArgs = @("-c", "port=SWD", "mode=UR", "reset=HWrst", "freq=4000", "-w", $ImagePath, "-v", "-rst")
$hardwareLock = $null
try {
    $hardwareLock = Enter-CompanionWb55Lock -Purpose "flash $([System.IO.Path]::GetFileName($ImagePath))"
    Write-Host "LOCK: Companion-WB55 $($hardwareLock.mode) run=$($hardwareLock.run_id)"
    $flashExitCode = Invoke-ProgrammerWithTimeout -Programmer $programmer -Arguments $programmerArgs -TimeoutSeconds $FlashTimeoutSeconds
    if ($flashExitCode -ne 0) {
        throw "flash failed with exit code $flashExitCode"
    }
} finally {
    if ($hardwareLock) {
        Exit-CompanionWb55Lock
    }
}
