param(
    [string] $PackagePath,
    [string] $TypeRepoRoot = (Join-Path $PSScriptRoot "..\..\Companion-Type"),
    [switch] $SkipTypeFrontend,
    [switch] $SkipTypeRust
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if ($PSVersionTable.PSVersion.Major -lt 7) {
    throw "PowerShell 7 or newer is required. Run with pwsh -NoProfile -File."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$typeRoot = (Resolve-Path $TypeRepoRoot).Path
$protocolName = "denzic_ota_v1"
$serviceUuid = "8f7a8007-7b7d-4f3d-9d6f-6c2d1b7c0000"
$controlUuid = "8f7a8002-7b7d-4f3d-9d6f-6c2d1b7c0000"
$dataUuid = "8f7a8004-7b7d-4f3d-9d6f-6c2d1b7c0000"
$statusUuid = "8f7a8005-7b7d-4f3d-9d6f-6c2d1b7c0000"
$expectedChunkBytes = 240
$chunkOverride = [Environment]::GetEnvironmentVariable("COMPANION_OTA_V1_CHUNK_BYTES")
if (-not [string]::IsNullOrWhiteSpace($chunkOverride)) {
    $parsedChunk = 0
    if (-not [int]::TryParse($chunkOverride.Trim(), [ref] $parsedChunk) -or $parsedChunk -lt 1 -or $parsedChunk -gt 244) {
        throw "Unsupported COMPANION_OTA_V1_CHUNK_BYTES=$chunkOverride; use 1..244."
    }
    $expectedChunkBytes = $parsedChunk
}

function Resolve-PackagePath {
    param([string] $Path)
    if (-not [string]::IsNullOrWhiteSpace($Path)) {
        return (Resolve-Path $Path).Path
    }
    $latest = Get-ChildItem -LiteralPath (Join-Path $repoRoot ".cache\ota_firmware") -Filter "companion-ota-*.zip" -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $latest) {
        throw "No Companion OTA package found. Run tools\package_ota_firmware.ps1 first."
    }
    return $latest.FullName
}

function Assert-Equal {
    param($Actual, $Expected, [string] $Label)
    if ($Actual -ne $Expected) {
        throw "$Label mismatch: expected '$Expected', got '$Actual'."
    }
}

function Assert-Contains {
    param([string] $Text, [string] $Needle, [string] $Label)
    if (-not $Text.Contains($Needle)) {
        throw "$Label missing expected token: $Needle"
    }
}

function Assert-NotContains {
    param([string] $Text, [string] $Needle, [string] $Label)
    if ($Text.Contains($Needle)) {
        throw "$Label still contains obsolete OTA token: $Needle"
    }
}

function Get-ZipEntry {
    param($Archive, [string] $Name)
    $entry = @($Archive.Entries | Where-Object {
            -not $_.FullName.EndsWith("/") -and $_.FullName.Replace("\", "/").TrimStart("/") -eq $Name
        })
    if ($entry.Count -ne 1) {
        throw "Expected one zip entry '$Name', found $($entry.Count)."
    }
    return $entry[0]
}

function Get-ZipBytes {
    param($Entry)
    $inputStream = $Entry.Open()
    try {
        $outputStream = [System.IO.MemoryStream]::new()
        try {
            $inputStream.CopyTo($outputStream)
            return $outputStream.ToArray()
        } finally {
            $outputStream.Dispose()
        }
    } finally {
        $inputStream.Dispose()
    }
}

function Get-ZipText {
    param($Entry)
    return [System.Text.Encoding]::UTF8.GetString((Get-ZipBytes -Entry $Entry))
}

function Get-Sha256Hex {
    param([byte[]] $Bytes)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        return -join ($sha.ComputeHash($Bytes) | ForEach-Object { $_.ToString("x2") })
    } finally {
        $sha.Dispose()
    }
}

function Assert-HostAdapter {
    $cargo = Get-Content -LiteralPath (Join-Path $typeRoot "apps\windows\src-tauri\Cargo.toml") -Raw
    $adapter = Get-Content -LiteralPath (Join-Path $typeRoot "apps\windows\src-tauri\src\backend\firmware_ota.rs") -Raw
    $ble = Get-Content -LiteralPath (Join-Path $typeRoot "apps\windows\src-tauri\src\backend\ble_bridge.rs") -Raw
    $commands = Get-Content -LiteralPath (Join-Path $typeRoot "apps\windows\src-tauri\src\commands.rs") -Raw
    $lib = Get-Content -LiteralPath (Join-Path $typeRoot "apps\windows\src-tauri\src\lib.rs") -Raw

    foreach ($pair in @(
            @($cargo, 'denzic-ota-core = { path = "../../../third_party/denzic-platform/ota/host/rust" }'),
            @($adapter, 'const PACKAGE_TYPE: &str = "companion-firmware-ota";'),
            @($adapter, 'denzic_ota_core::PROTOCOL_NAME'),
            @($adapter, 'file.sha256'),
            @($adapter, $serviceUuid),
            @($adapter, $controlUuid),
            @($adapter, $dataUuid),
            @($adapter, $statusUuid),
            @($ble, 'impl denzic_ota_core::OtaV1Transport for CompanionOtaV1Transport'),
            @($ble, 'denzic_ota_core::transfer('),
            @($ble, 'WriteType::WithoutResponse'),
            @($commands, 'transfer_companion_firmware_ota'),
            @($lib, 'commands::transfer_companion_firmware_ota'),
            @($lib, '"--firmware-ota-transfer"'),
            @($lib, 'firmware_ota_result_json=')
        )) {
        Assert-Contains -Text $pair[0] -Needle $pair[1] -Label "Companion-Type host adapter"
    }

    $platformRoot = Join-Path $typeRoot "third_party\denzic-platform\ota"
    foreach ($relative in @(
            "protocol\ota_v1.json",
            "host\rust\src\lib.rs",
            "host\typescript\src\index.ts",
            "embedded\c\src\denzic_ota_v1.c"
        )) {
        if (-not (Test-Path -LiteralPath (Join-Path $platformRoot $relative) -PathType Leaf)) {
            throw "Companion-Type Denzic-Platform submodule missing $relative"
        }
    }

    foreach ($obsolete in @("companion_ota_v2", "companion_ble_ota_v2", "stm32wb_st_ble_ota", "STM32WB_ST_OTA")) {
        Assert-NotContains -Text ($adapter + $ble + $commands + $lib) -Needle $obsolete -Label "Companion-Type OTA runtime"
    }
}

function Assert-EmbeddedAdapter {
    $makefile = Get-Content -LiteralPath (Join-Path $repoRoot "cubeide\Companion_BLE_Ota_Loader\Makefile") -Raw
    $adapter = Get-Content -LiteralPath (Join-Path $repoRoot "cubeide\Companion_BLE_Ota_Loader\Src\companion_ota_v1.c") -Raw
    $packageTool = Get-Content -LiteralPath (Join-Path $repoRoot "tools\package_ota_firmware.ps1") -Raw

    foreach ($token in @(
            'Src/companion_ota_v1.c',
            '$(DENZIC_OTA)/src/denzic_ota_v1.c',
            '$(DENZIC_OTA)/include'
        )) {
        Assert-Contains -Text $makefile -Needle $token -Label "Companion embedded build"
    }
    foreach ($token in @(
            'void SVCCTL_SvcInit(void)',
            'denzic_ota_v1_handle_control',
            'denzic_ota_v1_handle_data',
            'denzic_ota_v1_encode_status',
            'COMPANION_OTA_V1_REBOOT_GRACE_MS'
        )) {
        Assert-Contains -Text $adapter -Needle $token -Label "Companion embedded adapter"
    }
    foreach ($oldFile in @("otas_app.c", "otas_stm.c", "companion_ota_v2.c", "companion_ota_v2.h")) {
        if (Test-Path -LiteralPath (Join-Path $repoRoot "cubeide\Companion_BLE_Ota_Loader\Src\$oldFile")) {
            throw "Obsolete OTA runtime file still exists: $oldFile"
        }
        Assert-NotContains -Text $makefile -Needle $oldFile -Label "Companion embedded build"
    }
    foreach ($obsolete in @("companion_ota_v2", "companion_ble_ota_v2", "stm32wb_st_ble_ota", "STM32WB_ST_OTA")) {
        Assert-NotContains -Text ($makefile + $adapter + $packageTool) -Needle $obsolete -Label "Companion embedded OTA runtime"
    }
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
$resolvedPackagePath = Resolve-PackagePath -Path $PackagePath
if (-not $resolvedPackagePath.EndsWith(".zip", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "PackagePath must point to a zip file."
}

$archive = [System.IO.Compression.ZipFile]::OpenRead($resolvedPackagePath)
try {
    $manifestText = Get-ZipText -Entry (Get-ZipEntry -Archive $archive -Name "ota_manifest.json")
    $firmwareBytes = Get-ZipBytes -Entry (Get-ZipEntry -Archive $archive -Name "firmware_ota.bin")
    $manifest = $manifestText | ConvertFrom-Json
    Assert-Equal $manifest.schema_version 1 "schema_version"
    Assert-Equal $manifest.package_type "companion-firmware-ota" "package_type"
    Assert-Equal $manifest.hardware_revision "NUCLEO-WB55RG" "hardware_revision"
    Assert-Equal $manifest.file.name "firmware_ota.bin" "file.name"
    Assert-Equal ([int64] $manifest.file.size_bytes) ([int64] $firmwareBytes.Length) "file.size_bytes"
    Assert-Equal ([string] $manifest.file.sha256).ToLowerInvariant() (Get-Sha256Hex $firmwareBytes) "file.sha256"
    Assert-Equal $manifest.protocol.name $protocolName "protocol.name"
    Assert-Equal ([int] $manifest.protocol.version) 1 "protocol.version"
    Assert-Equal $manifest.protocol.firmware_capability $protocolName "protocol.firmware_capability"
    Assert-Equal $manifest.protocol.gatt.service_uuid $serviceUuid "protocol.gatt.service_uuid"
    Assert-Equal $manifest.protocol.gatt.control_uuid $controlUuid "protocol.gatt.control_uuid"
    Assert-Equal $manifest.protocol.gatt.data_uuid $dataUuid "protocol.gatt.data_uuid"
    Assert-Equal $manifest.protocol.gatt.status_uuid $statusUuid "protocol.gatt.status_uuid"
    Assert-Equal ([int] $manifest.protocol.gatt.chunk_bytes) $expectedChunkBytes "protocol.gatt.chunk_bytes"

    $factoryManifestEntries = @($archive.Entries | Where-Object {
            $_.FullName.Replace("\", "/") -match '^factory/[^/]+/manifest\.json$'
        })
    Assert-Equal $factoryManifestEntries.Count 1 "factory manifest count"
    $factoryManifest = (Get-ZipText $factoryManifestEntries[0]) | ConvertFrom-Json
    Assert-Equal $factoryManifest.package_type "companion-wired-factory" "factory package_type"
    $roles = @($factoryManifest.artifacts | ForEach-Object role)
    if (-not ($roles -contains "ota_loader") -or -not ($roles -contains "app")) {
        throw "Factory package must contain ota_loader and app artifacts."
    }
} finally {
    $archive.Dispose()
}

Assert-HostAdapter
Assert-EmbeddedAdapter

$cacheDir = Join-Path $repoRoot ".cache\validation\companion_ota_dual_side\$([IO.Path]::GetFileNameWithoutExtension($resolvedPackagePath))"
New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null
$manifestCachePath = Join-Path $cacheDir "ota_manifest.json"
$firmwareCachePath = Join-Path $cacheDir "firmware_ota.bin"
[IO.File]::WriteAllText($manifestCachePath, $manifestText, [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllBytes($firmwareCachePath, $firmwareBytes)

if (-not $SkipTypeRust) {
    $oldManifest = $env:COMPANION_TYPE_OTA_TEST_MANIFEST
    $oldFirmware = $env:COMPANION_TYPE_OTA_TEST_FIRMWARE
    $env:COMPANION_TYPE_OTA_TEST_MANIFEST = $manifestCachePath
    $env:COMPANION_TYPE_OTA_TEST_FIRMWARE = $firmwareCachePath
    try {
        Push-Location $typeRoot
        try {
            & cargo test --manifest-path apps/windows/src-tauri/Cargo.toml backend::firmware_ota::tests::validates_external_package_when_requested -- --exact
            if ($LASTEXITCODE -ne 0) {
                throw "Companion-Type real package validator failed with exit code $LASTEXITCODE."
            }
        } finally {
            Pop-Location
        }
    } finally {
        $env:COMPANION_TYPE_OTA_TEST_MANIFEST = $oldManifest
        $env:COMPANION_TYPE_OTA_TEST_FIRMWARE = $oldFirmware
    }
}

if ($SkipTypeFrontend) {
    Write-Output "INFO: -SkipTypeFrontend is retained for caller compatibility; OTA host validation is native Rust."
}
Write-Output "PASS: Companion OTA v1 package is implemented and validated on both host and embedded sides."
Write-Output "Package: $resolvedPackagePath"
