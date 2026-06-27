param(
    [string] $PackagePath,
    [string] $TypeRepoRoot = (Join-Path $PSScriptRoot "..\..\..\Listener\Listener-Type"),
    [switch] $SkipTypeFrontend,
    [switch] $SkipTypeRust
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$typeRoot = (Resolve-Path $TypeRepoRoot).Path
$typeFirmwareOtaPanel = Join-Path $typeRoot "src\pages\settings\FirmwareOtaPanel.tsx"
$typeCompanionSection = Join-Path $typeRoot "src\pages\settings\CompanionSection.tsx"
$typeMain = Join-Path $typeRoot "src\main.tsx"
$typeIpc = Join-Path $typeRoot "src\lib\ipc.ts"
$typeEmbeddedBle = Join-Path $typeRoot "src-tauri\src\embedded_ble.rs"
$typeFirmwareOtaRust = Join-Path $typeRoot "src-tauri\src\firmware_ota.rs"

$stm32ProtocolName = "stm32wb_st_ble_ota"
$stm32Capability = "stm32wb_st_ble_ota_v1"
$stm32ServiceUuid = "8f7a0007-7b7d-4f3d-9d6f-6c2d1b7c0000"
$stm32ControlUuid = "8f7a7002-7b7d-4f3d-9d6f-6c2d1b7c0000"
$stm32DataUuid = "8f7a7004-7b7d-4f3d-9d6f-6c2d1b7c0000"
$stm32ConfirmUuid = "8f7a7003-7b7d-4f3d-9d6f-6c2d1b7c0000"
$stm32ChunkBytes = 248

function Resolve-PackagePath {
    param([string] $Path)

    if (-not [string]::IsNullOrWhiteSpace($Path)) {
        return (Resolve-Path $Path).Path
    }

    $packageRoot = Join-Path $repoRoot ".cache\ota_firmware"
    $latest = Get-ChildItem -LiteralPath $packageRoot -Filter "companion-ota-*.zip" -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $latest) {
        throw "No Companion OTA zip package found under $packageRoot. Run tools\package_ota_firmware.ps1 first."
    }
    return $latest.FullName
}

function Assert-Equal {
    param(
        [Parameter(Mandatory = $true)] $Actual,
        [Parameter(Mandatory = $true)] $Expected,
        [Parameter(Mandatory = $true)][string] $Label
    )

    if ($Actual -ne $Expected) {
        throw "$Label mismatch: expected '$Expected', got '$Actual'."
    }
}

function Assert-True {
    param(
        [Parameter(Mandatory = $true)][bool] $Condition,
        [Parameter(Mandatory = $true)][string] $Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

function ConvertTo-NormalizedZipName {
    param([Parameter(Mandatory = $true)][string] $Name)
    return ($Name -replace "\\", "/").TrimStart("/")
}

function Get-ZipEntry {
    param(
        [Parameter(Mandatory = $true)] $Archive,
        [Parameter(Mandatory = $true)][string] $Name
    )

    $normalizedName = ConvertTo-NormalizedZipName $Name
    $matches = @($Archive.Entries | Where-Object {
            -not $_.FullName.EndsWith("/") -and
            (ConvertTo-NormalizedZipName $_.FullName) -eq $normalizedName
        })
    if ($matches.Count -ne 1) {
        throw "Expected exactly one zip entry '$normalizedName', found $($matches.Count)."
    }
    return $matches[0]
}

function Get-ZipEntryBytes {
    param([Parameter(Mandatory = $true)] $Entry)

    $stream = $Entry.Open()
    try {
        $memory = [System.IO.MemoryStream]::new()
        try {
            $stream.CopyTo($memory)
            return $memory.ToArray()
        } finally {
            $memory.Dispose()
        }
    } finally {
        $stream.Dispose()
    }
}

function Get-ZipEntryText {
    param([Parameter(Mandatory = $true)] $Entry)

    $bytes = Get-ZipEntryBytes -Entry $Entry
    return [System.Text.Encoding]::UTF8.GetString($bytes)
}

function Get-Sha256Hex {
    param([Parameter(Mandatory = $true)][byte[]] $Bytes)

    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        return -join ($sha.ComputeHash($Bytes) | ForEach-Object { $_.ToString("x2") })
    } finally {
        $sha.Dispose()
    }
}

function Assert-ExitCode {
    param(
        [Parameter(Mandatory = $true)][int] $Code,
        [Parameter(Mandatory = $true)][string] $Label
    )

    if ($Code -ne 0) {
        throw "$Label failed with exit code $Code."
    }
}

function Invoke-TypeFrontendCheck {
    param(
        [Parameter(Mandatory = $true)][string] $ManifestPath,
        [Parameter(Mandatory = $true)][string] $FirmwarePath
    )

    $nodeScript = @'
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  STM32WB_ST_OTA_TRANSPORT_BOUNDARY,
  evaluateFirmwareOtaPreflight,
  validateFirmwareOtaPackage,
} from './src/lib/firmwareOta.ts';

const manifestText = readFileSync(process.env.COMPANION_OTA_MANIFEST_PATH, 'utf8');
const firmwareBytes = new Uint8Array(readFileSync(process.env.COMPANION_OTA_FIRMWARE_PATH));
const validation = await validateFirmwareOtaPackage(manifestText, firmwareBytes, {
  desktopVersion: '1.0.0',
  expectedHardwareRevision: 'LISTENER-KEYBOARD',
  currentFirmwareVersion: null,
});
assert.equal(validation.ok, true, validation.errors.join('\n'));
assert.equal(validation.manifest.protocolName, STM32WB_ST_OTA_TRANSPORT_BOUNDARY.protocolName);
assert.equal(validation.manifest.firmwareCapability, STM32WB_ST_OTA_TRANSPORT_BOUNDARY.firmwareCapability);
assert.equal(validation.manifest.gattServiceUuid, STM32WB_ST_OTA_TRANSPORT_BOUNDARY.gatt.serviceUuid);
assert.equal(validation.manifest.gattControlUuid, STM32WB_ST_OTA_TRANSPORT_BOUNDARY.gatt.controlUuid);
assert.equal(validation.manifest.gattDataUuid, STM32WB_ST_OTA_TRANSPORT_BOUNDARY.gatt.dataUuid);
assert.equal(validation.manifest.gattConfirmUuid, STM32WB_ST_OTA_TRANSPORT_BOUNDARY.gatt.confirmUuid);
assert.equal(validation.manifest.gattChunkBytes, STM32WB_ST_OTA_TRANSPORT_BOUNDARY.gatt.maxChunkBytes);

const preflight = evaluateFirmwareOtaPreflight({
  manifest: validation.manifest,
  device: {
    connected: false,
    hardwareRevision: null,
    firmwareVersion: null,
    capabilities: [],
    batteryPercent: null,
    usbPowered: null,
    detail: 'No Listener snapshot; STM32WB backend owns target discovery.',
  },
  desktopVersion: '1.0.0',
  recordingActive: false,
  transferActive: false,
});
assert.equal(preflight.ok, true, JSON.stringify(preflight.blockers));
console.log('PASS: Type frontend accepts Companion STM32WB OTA manifest and preflight.');
'@

    $oldManifest = $env:COMPANION_OTA_MANIFEST_PATH
    $oldFirmware = $env:COMPANION_OTA_FIRMWARE_PATH
    $env:COMPANION_OTA_MANIFEST_PATH = $ManifestPath
    $env:COMPANION_OTA_FIRMWARE_PATH = $FirmwarePath
    Push-Location $typeRoot
    try {
        & node --experimental-strip-types --input-type=module --eval $nodeScript
        Assert-ExitCode -Code $LASTEXITCODE -Label "Type frontend Companion package check"
    } finally {
        Pop-Location
        $env:COMPANION_OTA_MANIFEST_PATH = $oldManifest
        $env:COMPANION_OTA_FIRMWARE_PATH = $oldFirmware
    }
}

function Invoke-TypeRustWiredCheck {
    param([Parameter(Mandatory = $true)][string] $ResolvedPackagePath)

    Push-Location (Join-Path $typeRoot "src-tauri")
    try {
        & cargo run --locked -- --wired-firmware-check $ResolvedPackagePath
        Assert-ExitCode -Code $LASTEXITCODE -Label "Type wired firmware package check"
    } finally {
        Pop-Location
    }
}

function Assert-TextContains {
    param(
        [Parameter(Mandatory = $true)][string] $Text,
        [Parameter(Mandatory = $true)][string] $Needle,
        [Parameter(Mandatory = $true)][string] $Label
    )

    if (-not $Text.Contains($Needle)) {
        throw "$Label missing expected token: $Needle"
    }
}

function Invoke-TypeUiSamePackageCheck {
    $panel = Get-Content -LiteralPath $typeFirmwareOtaPanel -Raw -Encoding UTF8
    $companion = Get-Content -LiteralPath $typeCompanionSection -Raw -Encoding UTF8
    $main = Get-Content -LiteralPath $typeMain -Raw -Encoding UTF8
    $ipc = Get-Content -LiteralPath $typeIpc -Raw -Encoding UTF8

    foreach ($token in @(
        "const [firmwareMode, setFirmwareMode] = useState<'ble' | 'wired'>('ble')",
        "const startSelectedFirmwareAction = () =>",
        "firmwareMode === 'ble'",
        "void wiredRef.current?.flash();",
        "selectedFirmwareActionLabel",
        "settings.recording.firmwareStartSelected",
        "settings.recording.firmwareModeBleOta",
        "settings.recording.firmwareModeWired",
        "transferFirmwareOtaBle({",
        "isStm32wbStBleOtaManifest(selectedPackage.manifest)",
        "transferResult?.transport === selectedPackage.manifest.protocolName",
        "FirmwareWiredFlashPanel ref={wiredRef} packagePath={selectedPackage?.path ?? null}",
        "loadWiredFirmwarePackage(packagePath)",
        "flashWiredFirmwarePackage({",
        "path: selection.path",
        "selectedPayload?.supportsBootRepair",
        "isStm32WbSwdTarget(selectedPayload?.target)",
        "const activeWiredPort = stm32WbSwd ? 'SWD' : port",
        "const activeWiredBaud = stm32WbSwd ? null : parseBaud(baud) ?? 460800",
        "const activePreserveOtaData = stm32WbSwd ? false : preserveOtaData",
        "setPort('SWD')",
        "settings.recording.wiredFirmwareStm32Desc",
        "settings.recording.wiredFirmwareInterface",
        "settings.recording.wiredFirmwareProgrammer",
        "settings.recording.wiredFirmwareStm32NoBootRepair",
        "settings.recording.wiredFirmwareProgressPackageLoadedSwd",
        "settings.recording.wiredFirmwareProgressConnectingSwd",
        "function isStm32WbSwdTarget",
        "nucleowb55rg",
        "stm32wb55ceux"
    )) {
        Assert-TextContains -Text $panel -Needle $token -Label "Type FirmwareOtaPanel same-package UI check"
    }

    foreach ($token in @(
        'params.get("visual") === "settings-companion"',
        "initialSection={isSettingsCompanionVisual ? `"companion`" : `"device`"}"
    )) {
        Assert-TextContains -Text $main -Needle $token -Label "Type Companion visual route check"
    }

    foreach ($token in @(
        "FIRMWARE_OTA_TRANSPORT_BOUNDARY,",
        "STM32WB_ST_OTA_TRANSPORT_BOUNDARY,",
        "loadFirmwareOtaPackage(path: string)",
        "export type FirmwareOtaBleTransferTransport =",
        "| typeof FIRMWARE_OTA_TRANSPORT_BOUNDARY.protocolName",
        "| typeof STM32WB_ST_OTA_TRANSPORT_BOUNDARY.protocolName",
        "transport: FirmwareOtaBleTransferTransport;",
        "transferFirmwareOtaBle(",
        "request.manifest.protocolName === STM32WB_ST_OTA_TRANSPORT_BOUNDARY.protocolName",
        "loadWiredFirmwarePackage(path: string)",
        "flashWiredFirmwarePackage(options:",
        "WiredFirmwarePackagePayload"
    )) {
        Assert-TextContains -Text $ipc -Needle $token -Label "Type ipc package command check"
    }

    foreach ($token in @(
        "import { FirmwareOtaPanel } from './FirmwareOtaPanel';",
        "COMPANION_FIRMWARE_PANEL_BLE_STATUS",
        "<FirmwareOtaPanel",
        "supported",
        "bleStatus={COMPANION_FIRMWARE_PANEL_BLE_STATUS}",
        "settings.companion.readinessCommand",
        "tools\\verify_companion_bringup_readiness.ps1",
        "settings.companion.packageCommand",
        "tools\\package_ota_firmware.ps1 -Channel development -BoardTarget NUCLEO-WB55RG",
        "settings.companion.verifyPackageCommand",
        "tools\\verify_type_companion_package_static.ps1",
        "settings.companion.hardwareAcceptanceCommand",
        "Companion hardware acceptance",
        "tools\\verify_companion_hardware_acceptance.ps1",
        "-EvidencePath <companion_ui_screenshot_or_log>",
        "settings.companion.flashPackageCommand",
        "Companion wired factory flash validation",
        "tools\\verify_companion_wired_flash.ps1",
        "-PackagePath <companion-package.zip>",
        "settings.companion.samePackageLabel",
        "settings.companion.samePackageValue",
        "stm32wb_st_ble_ota",
        "ST-LINK / SWD"
    )) {
        Assert-TextContains -Text $companion -Needle $token -Label "Type Companion temporary debug page same-package check"
    }

    Write-Output "PASS: Type firmware UI keeps one selected package path for BLE OTA and wired flashing."
}

function Invoke-TypeStm32OtaConfirmCheck {
    $embedded = Get-Content -LiteralPath $typeEmbeddedBle -Raw -Encoding UTF8
    $firmwareOta = Get-Content -LiteralPath $typeFirmwareOtaRust -Raw -Encoding UTF8

    foreach ($token in @(
        "let use_confirm = stm32wb_st_ota_use_confirm_indication();",
        "STM32WB ST OTA confirmation indication is required before transfer",
        "Set COMPANION_STM32WB_ST_OTA_CONFIRM=0 only when testing the legacy no-confirm loader.",
        '"0" | "false" | "no" | "off"',
        ".unwrap_or(true)",
        "stm32wb_st_ota_confirm_indication_defaults_on_and_accepts_explicit_opt_out"
    )) {
        Assert-TextContains -Text $embedded -Needle $token -Label "Type STM32WB ST OTA confirmation check"
    }

    foreach ($token in @(
        "if properties.contains(GattCharacteristicProperties::Write)",
        "Ok(GattWriteOption::WriteWithResponse)",
        "STM32WB ST OTA raw characteristic is not writable",
        ".min(ATT_DEFAULT_PAYLOAD_BYTES)",
        ".min(STM32WB_ST_OTA_RAW_DATA_SIZE)",
        "stm32wb_st_ota_raw_chunk_bytes_from_payload",
        "stm32wb_st_ota_prefers_with_response_when_available",
        "stm32wb_st_ota_uses_large_confirmed_chunks_and_caps_no_response"
    )) {
        Assert-TextContains -Text $embedded -Needle $token -Label "Type STM32WB ST OTA stable raw write check"
    }

    if ($embedded.Contains("set COMPANION_STM32WB_ST_OTA_CONFIRM=1 to test ST indication confirm")) {
        throw "Type embedded BLE must not default STM32WB ST OTA to the old no-confirm path."
    }

    foreach ($token in @(
        "pub gatt_confirm_uuid: Option<String>,",
        'optional_gatt_optional_string(gatt, "confirm_uuid", "confirmUuid")',
        "STM32WB_ST_OTA_CONFIRM_UUID",
        ".gatt_confirm_uuid",
        "stm32wb_st_manifest_requires_confirm_gatt_boundary"
    )) {
        Assert-TextContains -Text $firmwareOta -Needle $token -Label "Type STM32WB ST OTA manifest confirmation check"
    }

    Write-Output "PASS: Type STM32WB ST OTA enables ST confirmation indication, large write-response raw chunks, and 20-byte no-response fallback chunks."
}

Add-Type -AssemblyName System.IO.Compression.FileSystem

$resolvedPackagePath = Resolve-PackagePath -Path $PackagePath
Assert-True -Condition ($resolvedPackagePath.EndsWith(".zip", [System.StringComparison]::OrdinalIgnoreCase)) -Message "PackagePath must point to a .zip file."

$archive = [System.IO.Compression.ZipFile]::OpenRead($resolvedPackagePath)
try {
    $manifestEntry = Get-ZipEntry -Archive $archive -Name "ota_manifest.json"
    $firmwareEntry = Get-ZipEntry -Archive $archive -Name "firmware_ota.bin"
    $manifestText = Get-ZipEntryText -Entry $manifestEntry
    $firmwareBytes = Get-ZipEntryBytes -Entry $firmwareEntry
    $manifest = $manifestText | ConvertFrom-Json
    $firmwareHash = Get-Sha256Hex -Bytes $firmwareBytes

    Assert-Equal -Actual $manifest.package_type -Expected "companion-firmware-ota" -Label "OTA package_type"
    Assert-Equal -Actual $manifest.project -Expected "Companion-Firmware" -Label "OTA project"
    Assert-Equal -Actual $manifest.file.name -Expected "firmware_ota.bin" -Label "OTA file.name"
    Assert-Equal -Actual ([int64] $manifest.file.size_bytes) -Expected ([int64] $firmwareBytes.Length) -Label "OTA file.size_bytes"
    Assert-Equal -Actual ([string] $manifest.file.sha256).ToLowerInvariant() -Expected $firmwareHash -Label "OTA file.sha256"
    Assert-Equal -Actual $manifest.protocol.name -Expected $stm32ProtocolName -Label "OTA protocol.name"
    Assert-Equal -Actual $manifest.protocol.firmware_capability -Expected $stm32Capability -Label "OTA protocol.firmware_capability"
    Assert-Equal -Actual $manifest.protocol.gatt.service_uuid -Expected $stm32ServiceUuid -Label "OTA protocol.gatt.service_uuid"
    Assert-Equal -Actual $manifest.protocol.gatt.control_uuid -Expected $stm32ControlUuid -Label "OTA protocol.gatt.control_uuid"
    Assert-Equal -Actual $manifest.protocol.gatt.data_uuid -Expected $stm32DataUuid -Label "OTA protocol.gatt.data_uuid"
    Assert-Equal -Actual $manifest.protocol.gatt.confirm_uuid -Expected $stm32ConfirmUuid -Label "OTA protocol.gatt.confirm_uuid"
    Assert-Equal -Actual ([int] $manifest.protocol.gatt.chunk_bytes) -Expected $stm32ChunkBytes -Label "OTA protocol.gatt.chunk_bytes"

    $factoryManifestEntries = @($archive.Entries | Where-Object {
            $name = ConvertTo-NormalizedZipName $_.FullName
            -not $_.FullName.EndsWith("/") -and $name -match '^factory/[^/]+/manifest\.json$'
        })
    if ($factoryManifestEntries.Count -ne 1) {
        throw "Expected exactly one factory manifest under factory/<package>/manifest.json, found $($factoryManifestEntries.Count)."
    }

    $factoryManifestEntry = $factoryManifestEntries[0]
    $factoryManifestName = ConvertTo-NormalizedZipName $factoryManifestEntry.FullName
    $factoryDir = $factoryManifestName.Substring(0, $factoryManifestName.LastIndexOf("/") + 1)
    $factoryManifest = (Get-ZipEntryText -Entry $factoryManifestEntry) | ConvertFrom-Json
    Assert-Equal -Actual $factoryManifest.package_type -Expected "companion-wired-factory" -Label "Factory package_type"
    Assert-Equal -Actual $factoryManifest.project -Expected "Companion-Firmware" -Label "Factory project"
    Assert-Equal -Actual $factoryManifest.target -Expected $manifest.hardware_revision -Label "Factory target"
    Assert-Equal -Actual $factoryManifest.flash.port -Expected "SWD" -Label "Factory flash.port"

    $artifacts = @($factoryManifest.artifacts)
    $roles = @($artifacts | ForEach-Object { $_.role })
    Assert-True -Condition ($roles -contains "ota_loader") -Message "Factory manifest missing ota_loader artifact."
    Assert-True -Condition ($roles -contains "app") -Message "Factory manifest missing app artifact."

    foreach ($artifact in $artifacts) {
        $artifactEntryName = "$factoryDir$($artifact.file)"
        $artifactEntry = Get-ZipEntry -Archive $archive -Name $artifactEntryName
        $artifactBytes = Get-ZipEntryBytes -Entry $artifactEntry
        Assert-Equal -Actual ([int64] $artifact.size_bytes) -Expected ([int64] $artifactBytes.Length) -Label "Factory artifact $($artifact.role) size_bytes"
        Assert-Equal -Actual ([string] $artifact.sha256).ToLowerInvariant() -Expected (Get-Sha256Hex -Bytes $artifactBytes) -Label "Factory artifact $($artifact.role) sha256"
        if ($artifact.role -eq "ota_loader") {
            Assert-Equal -Actual $artifact.offset -Expected "0x08000000" -Label "Factory ota_loader offset"
        } elseif ($artifact.role -eq "app") {
            Assert-Equal -Actual $artifact.offset -Expected $manifest.protocol.app_base_address -Label "Factory app offset"
        }
    }
} finally {
    $archive.Dispose()
}

Write-Output "PASS: Companion zip manifest, firmware hash, and factory artifacts are internally consistent."

$cacheDir = Join-Path $repoRoot ".cache\validation\type_companion_package_static\$([System.IO.Path]::GetFileNameWithoutExtension($resolvedPackagePath))"
New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null
$manifestCachePath = Join-Path $cacheDir "ota_manifest.json"
$firmwareCachePath = Join-Path $cacheDir "firmware_ota.bin"
[System.IO.File]::WriteAllText($manifestCachePath, $manifestText, [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllBytes($firmwareCachePath, $firmwareBytes)

if (-not $SkipTypeFrontend) {
    Invoke-TypeFrontendCheck -ManifestPath $manifestCachePath -FirmwarePath $firmwareCachePath
}

Invoke-TypeUiSamePackageCheck
Invoke-TypeStm32OtaConfirmCheck

if (-not $SkipTypeRust) {
    Invoke-TypeRustWiredCheck -ResolvedPackagePath $resolvedPackagePath
}

Write-Output "PASS: Companion package is accepted by Type Companion OTA/wired static integration checks."
Write-Output "Package: $resolvedPackagePath"
