param(
    [string]$ImagePath,
    [switch]$ScreenAssetProvision,
    [switch]$CompReq638Provision,
    [switch]$CompReq638Candidate,
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
$compReq638CandidateImagePath = Join-Path $PSScriptRoot '..\cubeide\Companion_Nucleo_WB55RG_Bringup\build_comp_req_638\Companion_Nucleo_WB55RG_Bringup.hex'
$compReq638ProvisionImagePath = Join-Path $PSScriptRoot '..\cubeide\Companion_Nucleo_WB55RG_Bringup\build_comp_req_638_provision\Companion_CompReq_638_ScreenAssetProvision.hex'
$compReq638CandidateHexSha256 = '617FEFF9A847B0A5A2914FCF379EBE85AFCFD8E4CB4C32842A845B0DD6339B58'
$compReq638ProvisionHexSha256 = 'E160F6B85BB493F9C5AB03475425E5B54A8E7317B8259A6FF5A303C33881DA1E'
$otaAppGuard = Join-Path $repoRoot (
    'tools\faraday_upper_art\verify_companion_ota_app_hex.py'
)
$layoutReceipt = Join-Path $repoRoot (
    '.cache\validation\flash-nucleo\ota-app-layout.json'
)

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

if ($ScreenAssetProvision) {
    throw "Legacy -ScreenAssetProvision is blocked; use -CompReq638Provision for the current hash-bound CEMP."
}
$selectedModeCount = 0
if ($CompReq638Provision) { $selectedModeCount++ }
if ($CompReq638Candidate) { $selectedModeCount++ }
if (-not [string]::IsNullOrWhiteSpace($ImagePath)) { $selectedModeCount++ }
if ($selectedModeCount -gt 1) {
    throw "Choose exactly one of -ImagePath, -CompReq638Provision, or -CompReq638Candidate."
}
$selectedMode = 'normal'
$expectedImageSha256 = $null
if ($CompReq638Provision) {
    $ImagePath = $compReq638ProvisionImagePath
    $selectedMode = 'comp_req_638_provision'
    $expectedImageSha256 = $compReq638ProvisionHexSha256
} elseif ($CompReq638Candidate) {
    $ImagePath = $compReq638CandidateImagePath
    $selectedMode = 'comp_req_638_candidate'
    $expectedImageSha256 = $compReq638CandidateHexSha256
} elseif ([string]::IsNullOrWhiteSpace($ImagePath)) {
    $ImagePath = $normalImagePath
}

if (-not (Test-Path -LiteralPath $ImagePath)) {
    throw "Image not found: $ImagePath"
}
if ($expectedImageSha256) {
    $actualImageSha256 = (Get-FileHash -LiteralPath $ImagePath -Algorithm SHA256).Hash.ToUpperInvariant()
    if ($actualImageSha256 -ne $expectedImageSha256) {
        throw "Hash mismatch for $selectedMode`: expected $expectedImageSha256, found $actualImageSha256"
    }
}
if (-not (Test-Path -LiteralPath $otaAppGuard -PathType Leaf)) {
    throw "Companion OTA App layout guard is missing: $otaAppGuard"
}
# MUST run before lock acquire and before any STM32_Programmer_CLI invocation.
# Concurrent agents that call CubeProgrammer with a 0x08000000 FreeRTOS/bringup
# hex bypass this script and wipe the resident OTA Loader — use
# tools/flash_swd_ota_app_only.ps1 (or this script) only; never raw CLI.
Write-Host "GUARD: pre-start refuse Loader overwrite — verifying $ImagePath"
& python $otaAppGuard --hex $ImagePath --receipt $layoutReceipt | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw (
        "REFUSED before any SWD write: image can overwrite the resident OTA Loader. " +
        "Build with OTA_APP=1 (app at 0x08007000). Prefer BLE denzic_ota_v1 package. " +
        "Do not pass build_freertos full-chip hex. see $layoutReceipt"
    )
}

$programmer = Get-ChildItem -LiteralPath $ProgrammerRoot -Recurse -Filter STM32_Programmer_CLI.exe |
    Select-Object -First 1 -ExpandProperty FullName
if (-not $programmer) {
    throw "STM32_Programmer_CLI.exe not found under $ProgrammerRoot"
}

if ($CheckOnly) {
    Write-Output "CHECK: mode=$selectedMode"
    Write-Output "CHECK: image=$((Resolve-Path -LiteralPath $ImagePath).Path)"
    if ($expectedImageSha256) {
        Write-Output "CHECK: sha256=$expectedImageSha256"
    }
    Write-Output "CHECK: ota_app_layout=MACHINE_READY"
    Write-Output "CHECK: ota_app_layout_receipt=$layoutReceipt"
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
