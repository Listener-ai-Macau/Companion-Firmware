param(
    [string] $BuildDir = (Join-Path $PSScriptRoot "..\cubeide\Companion_Nucleo_WB55RG_Bringup\build"),
    [string] $OtaBuildDir = (Join-Path $PSScriptRoot "..\cubeide\Companion_Nucleo_WB55RG_Bringup\build_ota"),
    [string] $LoaderBuildDir = (Join-Path $PSScriptRoot "..\cubeide\Companion_BLE_Ota_Loader\build"),
    [string] $OutputRoot = (Join-Path $PSScriptRoot "..\.cache\ota_firmware"),
    [ValidateSet("development", "stable")]
    [string] $Channel = "development",
    [ValidateSet("NUCLEO-WB55RG", "COMPANION-PENDANT-CE")]
    [string] $BoardTarget = "NUCLEO-WB55RG",
    [string] $Version,
    [string] $MinDesktopVersion = "0.1.0",
    [ValidateRange(30, 100)]
    [int] $MinBatteryPercent = 40
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$denzicProtocolPath = Join-Path $repoRoot "third_party\denzic-platform\ota\protocol\ota_v1.json"
if (-not (Test-Path -LiteralPath $denzicProtocolPath -PathType Leaf)) {
    throw "Denzic Platform OTA submodule is not initialized: $denzicProtocolPath"
}
$denzicProtocol = Get-Content -LiteralPath $denzicProtocolPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($denzicProtocol.name -ne "denzic_ota_v1" -or [int]$denzicProtocol.version -ne 1) {
    throw "Unsupported Denzic OTA protocol identity in $denzicProtocolPath"
}
$buildPath = (Resolve-Path $BuildDir).Path
$otaBuildPath = (Resolve-Path $OtaBuildDir).Path
$loaderBuildPath = (Resolve-Path $LoaderBuildDir).Path
$outputRootPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputRoot)
$targetName = "Companion_Nucleo_WB55RG_Bringup"
$otaTargetName = "Companion_Nucleo_WB55RG_Bringup_ota_app"
$loaderTargetName = "Companion_BLE_Ota_Loader"
$binSource = Join-Path $buildPath "$targetName.bin"
$hexSource = Join-Path $buildPath "$targetName.hex"
$otaBinSource = Join-Path $otaBuildPath "$otaTargetName.bin"
$otaHexSource = Join-Path $otaBuildPath "$otaTargetName.hex"
$loaderHexSource = Join-Path $loaderBuildPath "$loaderTargetName.hex"

$requiredBlockers = @(
    "recording_active",
    "transfer_active",
    "diag_export_active",
    "low_battery",
    "wrong_board_target",
    "invalid_hash",
    "interrupted_transfer"
)

$requiredBlockerBits = [ordered]@{
    recording_active = 0
    transfer_active = 1
    diag_export_active = 2
    low_battery = 3
    wrong_board_target = 4
    invalid_hash = 5
    interrupted_transfer = 6
}

$hostActionMessages = [ordered]@{
    recording_active = [ordered]@{
        message = "Recording is active."
        action = "Stop or save the current recording before starting OTA."
        retryable = $true
    }
    transfer_active = [ordered]@{
        message = "A large transfer is active."
        action = "Wait for the current recording or diagnostics transfer to finish, then retry OTA."
        retryable = $true
    }
    diag_export_active = [ordered]@{
        message = "Diagnostics export is active."
        action = "Let diagnostics export finish before offering OTA."
        retryable = $true
    }
    low_battery = [ordered]@{
        message = "Battery is below the OTA safety threshold."
        action = "Charge the pendant above the package battery and voltage minimum before retrying."
        retryable = $true
    }
    wrong_board_target = [ordered]@{
        message = "The package targets a different Companion board."
        action = "Choose a package whose board target and MCU match the connected Companion."
        retryable = $false
    }
    invalid_hash = [ordered]@{
        message = "The package image hash or size does not match the manifest."
        action = "Download or rebuild the package and retry only after the SHA-256 check passes."
        retryable = $false
    }
    interrupted_transfer = [ordered]@{
        message = "A previous OTA transfer was interrupted."
        action = "Resume or discard the interrupted transfer from the host before starting a new OTA."
        retryable = $true
    }
}

$requiredSelfChecks = @(
    "boot_version_reported",
    "ble_advertising",
    "ota_readiness_notify",
    "diag_log_tail"
)

function Assert-File {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $Label
    )
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing $Label`: $Path. Run tools\build_nucleo_bringup.ps1 first."
    }
}

function Get-SourceVersion {
    if ($Version) { return $Version.Trim() }
    $versionPath = Join-Path $repoRoot "VERSION"
    if (Test-Path -LiteralPath $versionPath -PathType Leaf) {
        $text = (Get-Content -LiteralPath $versionPath -Raw).Trim()
        if (-not [string]::IsNullOrWhiteSpace($text)) { return $text }
    }
    $describe = (& git -C $repoRoot describe --tags --always --dirty 2>$null)
    if ($describe) { return [string] $describe }
    return "0.1.0-nucleo-bench"
}

function Test-ReleaseVersionString {
    param(
        [Parameter(Mandatory = $true)][string] $Text,
        [Parameter(Mandatory = $true)][string] $ReleaseChannel
    )
    if ($ReleaseChannel -eq "development") { return }
    if ($Text -match '(?i)(^|[._+-])(dirty|dev|bench)([._+-]|$)') {
        throw "Stable packages require a clean release version; got '$Text'. Use -Channel development for bench packages."
    }
}

Assert-File -Path $binSource -Label "NUCLEO direct-run binary"
Assert-File -Path $hexSource -Label "NUCLEO direct-run hex"
Assert-File -Path $otaBinSource -Label "NUCLEO OTA app binary"
Assert-File -Path $otaHexSource -Label "NUCLEO OTA app hex"
Assert-File -Path $loaderHexSource -Label "Companion BLE OTA loader hex"

$gitCommit = (& git -C $repoRoot rev-parse HEAD 2>$null)
if (-not $gitCommit) { $gitCommit = "unknown" }
$gitStatus = @(& git -C $repoRoot status --porcelain 2>$null)
$gitDirty = $gitStatus.Count -gt 0
if ($gitDirty -and $Channel -eq "stable") {
    throw "Stable packages require a clean working tree. Use -Channel development for local bring-up packages."
}

$packageVersion = Get-SourceVersion
Test-ReleaseVersionString -Text $packageVersion -ReleaseChannel $Channel
$safeVersion = $packageVersion -replace '[^A-Za-z0-9_.-]', '_'
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$packageName = "companion-ota-$($BoardTarget.ToLowerInvariant())-$safeVersion-$timestamp"
$packageDir = Join-Path $outputRootPath $packageName
New-Item -ItemType Directory -Force -Path $packageDir | Out-Null

$otaBinName = "firmware_ota.bin"
$otaBinDest = Join-Path $packageDir $otaBinName
Copy-Item -LiteralPath $otaBinSource -Destination $otaBinDest -Force
$otaHash = (Get-FileHash -LiteralPath $otaBinDest -Algorithm SHA256).Hash.ToLowerInvariant()
$otaSize = (Get-Item -LiteralPath $otaBinDest).Length
$companionOtaV1ChunkBytes = 240
$chunkOverride = [Environment]::GetEnvironmentVariable("COMPANION_OTA_V1_CHUNK_BYTES")
if (-not [string]::IsNullOrWhiteSpace($chunkOverride)) {
    $parsedChunk = 0
    if (-not [int]::TryParse($chunkOverride.Trim(), [ref] $parsedChunk) -or $parsedChunk -lt 1 -or $parsedChunk -gt 244) {
        throw "Unsupported COMPANION_OTA_V1_CHUNK_BYTES=$chunkOverride; use a chunk size from 1 to 244 bytes."
    }
    $companionOtaV1ChunkBytes = $parsedChunk
}

$mcu = if ($BoardTarget -eq "NUCLEO-WB55RG") { "STM32WB55" } else { "STM32WB55CEUx" }
$hardwareRevision = $BoardTarget
$otaAppBaseAddress = "0x08007000"
$otaAppStartSector = 7
$minimumRequiredMv = if ($BoardTarget -eq "NUCLEO-WB55RG") { 3600 } else { 3700 }

$manifest = [ordered]@{
    schema_version = 1
    package_type = "companion-firmware-ota"
    created_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    channel = $Channel
    project = "Companion-Firmware"
    version = $packageVersion
    hardware_revision = $hardwareRevision
    min_desktop_version = $MinDesktopVersion
    file = [ordered]@{
        name = $otaBinName
        size_bytes = $otaSize
        sha256 = $otaHash
    }
    components = @(
        [ordered]@{
            kind = "mcu_app"
            component_version = $packageVersion
            format_version = 1
            target_family = "stm32wb"
            board_target = $BoardTarget
            file = $otaBinName
            size_bytes = $otaSize
            sha256 = $otaHash
            compatibility = [ordered]@{
                mcu = $mcu
                app_base_address = $otaAppBaseAddress
            }
        }
    )
    protocol = [ordered]@{
        name = [string]$denzicProtocol.name
        version = [int]$denzicProtocol.version
        firmware_capability = [string]$denzicProtocol.name
        app_base_address = $otaAppBaseAddress
        app_start_sector = $otaAppStartSector
        gatt = [ordered]@{
            service_uuid = [string]$denzicProtocol.gatt.service_uuid
            control_uuid = [string]$denzicProtocol.gatt.control_uuid
            data_uuid = [string]$denzicProtocol.gatt.data_uuid
            status_uuid = [string]$denzicProtocol.gatt.status_uuid
            chunk_bytes = $companionOtaV1ChunkBytes
        }
    }
    firmware = [ordered]@{
        project = "Companion-Firmware"
        version = $packageVersion
        git_commit = $gitCommit
        git_dirty = $gitDirty
        board_target = $BoardTarget
        mcu = $mcu
    }
    image = [ordered]@{
        file = $otaBinName
        base_address = $otaAppBaseAddress
        start_sector = $otaAppStartSector
        size_bytes = $otaSize
        sha256 = $otaHash
    }
    compatibility = [ordered]@{
        platform_adapter = "stm32wb_denzic_ota_v1"
        st_reference = "Denzic OTA v1 Companion loader on STM32WB"
        stm32cube_wb = "v1.24.0"
        gatt_contract = "denzic_ota_v1"
        min_desktop_version = $MinDesktopVersion
    }
    bootloader = [ordered]@{
        kind = "denzic_ota_v1_stm32wb_loader"
        recovery = "ROM DFU or SWD via STM32CubeProgrammer"
        internal_flash_policy = "single_runnable_app_no_dual_internal_slots"
        vector_table_policy = "app_base_linker_offset_with_bootloader_jump"
    }
    external_flash = [ordered]@{
        kind = "external_qspi_nor"
        ota_staging = "single_ota_staging_partition"
        partition_policy = "boot_meta_a_b + ota_staging + ui_assets_active_candidate + recording_cache + diag_log_mirror"
        dual_ota_partitions = $false
    }
    guards = [ordered]@{
        min_battery_percent = $MinBatteryPercent
        minimum_required_mv = $minimumRequiredMv
        charger_required = $false
        blockers = $requiredBlockers
        blocker_bitmap = $requiredBlockerBits
    }
    host_messages = $hostActionMessages
    rollback = [ordered]@{
        strategy = "stm32wb_reference_ota_pending_verify"
        notes = "Resident bootloader verifies external QSPI ota_staging before installing the single runnable CPU1 app."
        instructions = @(
            "If the Denzic OTA v1 transfer is interrupted before reboot, retry from the Companion loader.",
            "If the app does not boot, use the wired factory path in the same package to restore the Denzic OTA v1 loader plus the app."
        )
    }
    recovery = [ordered]@{
        factory_reflash = "Use STM32CubeProgrammer or tools/flash.ps1 -FlashPackage with the package factory manifest."
        interrupted_transfer = "Report interrupted_transfer and require host recovery before accepting new OTA data."
        instructions = @(
            "Use the package factory directory or Type wired flashing to restore both the Denzic OTA v1 loader and Companion app over SWD.",
            "If Windows cannot see Companion advertising the Denzic OTA v1 service, reset the board into the wired factory image first."
        )
    }
    post_update_self_checks = $requiredSelfChecks
}

$manifestPath = Join-Path $packageDir "ota_manifest.json"
$manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $manifestPath -Encoding utf8

$factoryRoot = Join-Path $packageDir "factory"
$factoryPackageName = "companion-factory-$($BoardTarget.ToLowerInvariant())-$safeVersion-$timestamp"
$factoryPackageDir = Join-Path $factoryRoot $factoryPackageName
New-Item -ItemType Directory -Force -Path $factoryPackageDir | Out-Null

$factoryLoaderName = "$loaderTargetName.hex"
$factoryLoaderDest = Join-Path $factoryPackageDir $factoryLoaderName
Copy-Item -LiteralPath $loaderHexSource -Destination $factoryLoaderDest -Force
$factoryLoaderHash = (Get-FileHash -LiteralPath $factoryLoaderDest -Algorithm SHA256).Hash.ToLowerInvariant()
$factoryLoaderSize = (Get-Item -LiteralPath $factoryLoaderDest).Length

$factoryHexName = "$otaTargetName.hex"
$factoryHexDest = Join-Path $factoryPackageDir $factoryHexName
Copy-Item -LiteralPath $otaHexSource -Destination $factoryHexDest -Force
$factoryHash = (Get-FileHash -LiteralPath $factoryHexDest -Algorithm SHA256).Hash.ToLowerInvariant()
$factorySize = (Get-Item -LiteralPath $factoryHexDest).Length

$factoryManifest = [ordered]@{
    schema_version = 1
    package_type = "companion-wired-factory"
    created_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    project = "Companion-Firmware"
    version = $packageVersion
    target = $BoardTarget
    git_commit = $gitCommit
    firmware = [ordered]@{
        project = "Companion-Firmware"
        version = $packageVersion
        git_commit = $gitCommit
        git_dirty = $gitDirty
        board_target = $BoardTarget
        mcu = $mcu
    }
    image = [ordered]@{
        file = $factoryHexName
        format = "intel_hex"
        base_address = $otaAppBaseAddress
        size_bytes = $factorySize
        sha256 = $factoryHash
    }
    flash = [ordered]@{
        tool = "STM32CubeProgrammer"
        port = "SWD"
        repository_command = "tools/flash.ps1 -Execute -WorkflowLockHeld -FlashPackage -PackagePath <package>\factory\$factoryPackageName\manifest.json"
    }
    artifacts = @(
        [ordered]@{
            role = "ota_loader"
            file = $factoryLoaderName
            offset = "0x08000000"
            format = "intel_hex"
            size_bytes = $factoryLoaderSize
            sha256 = $factoryLoaderHash
        },
        [ordered]@{
            role = "app"
            file = $factoryHexName
            offset = $otaAppBaseAddress
            format = "intel_hex"
            size_bytes = $factorySize
            sha256 = $factoryHash
        }
    )
}
$factoryManifestPath = Join-Path $factoryPackageDir "manifest.json"
$factoryManifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $factoryManifestPath -Encoding utf8

$flashingText = @"
# Companion Wired Flash Package

Loader: $factoryLoaderName
Image: $factoryHexName
Target: $BoardTarget / $mcu

Run real flashing from the repository root inside the workflow hardware lock:

````powershell
pwsh -NoProfile -File <ai-collaboration-workflow>\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose "flash Companion package" -Run pwsh -NoProfile -Command "& { Set-Location '<Companion-Firmware>'; .\tools\flash.ps1 -Execute -WorkflowLockHeld -FlashPackage -PackagePath '$factoryManifestPath' }"
````

For a dry check:

````powershell
pwsh -NoProfile -File .\tools\flash.ps1 -CheckOnly
````
"@
$flashingPath = Join-Path $factoryPackageDir "FLASHING.md"
$flashingText | Set-Content -LiteralPath $flashingPath -Encoding utf8

& pwsh -NoProfile -File (Join-Path $PSScriptRoot "check_ota_manifest.ps1") -ManifestPath $manifestPath | Write-Output
if ($LASTEXITCODE -ne 0) {
    throw "Generated OTA manifest did not pass validation."
}

$zipPath = "$packageDir.zip"
if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}
Compress-Archive -LiteralPath @($manifestPath, $otaBinDest, $factoryRoot) -DestinationPath $zipPath -Force

Write-Output "PASS: Companion OTA package generated."
Write-Output "Package: $packageDir"
Write-Output "Zip: $zipPath"
Write-Output "OTA manifest: $manifestPath"
Write-Output "OTA binary: $otaBinName ($otaSize bytes) sha256=$otaHash"
Write-Output "Factory package: $factoryPackageDir"
Write-Output "Factory loader: $factoryLoaderName ($factoryLoaderSize bytes) sha256=$factoryLoaderHash"
Write-Output "Factory app: $factoryHexName ($factorySize bytes) sha256=$factoryHash"
Write-Output "Channel: $Channel  Version: $packageVersion  Git dirty: $gitDirty"
