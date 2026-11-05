param(
    [Parameter(Mandatory = $true)][string] $CempPath,
    [string] $OutputRoot = (Join-Path $PSScriptRoot "..\.cache\ota_resources"),
    [string] $Version = "ui-assets-dev",
    [string] $BoardTarget = "NUCLEO-WB55RG",
    [string] $ScreenProfile = "ssd1681-200x200",
    [string] $MinAppVersion = "0.1.0",
    [string] $MaxAppVersion = "99.0.0"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$cemp = (Resolve-Path -LiteralPath $CempPath).Path
if (-not (Test-Path -LiteralPath $cemp -PathType Leaf)) {
    throw "CEMP file missing: $cemp"
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outDir = Join-Path $OutputRoot "companion-ui-assets-$Version-$stamp"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$payloadName = "ui_assets.cemp"
$payloadPath = Join-Path $outDir $payloadName
Copy-Item -LiteralPath $cemp -Destination $payloadPath -Force

$sha = (Get-FileHash -LiteralPath $payloadPath -Algorithm SHA256).Hash.ToLowerInvariant()
$size = (Get-Item -LiteralPath $payloadPath).Length
$protocolPath = Join-Path $repoRoot "third_party\denzic-platform\ota\protocol\ota_v1.json"
$protocol = Get-Content -LiteralPath $protocolPath -Raw -Encoding UTF8 | ConvertFrom-Json

$manifest = [ordered]@{
    schema_version = 1
    package_type = "companion-resource-ota"
    created_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    channel = "development"
    project = "Companion-Firmware"
    version = $Version
    hardware_revision = $BoardTarget
    file = [ordered]@{
        name = $payloadName
        size_bytes = $size
        sha256 = $sha
    }
    components = @(
        [ordered]@{
            kind = "ui_assets"
            component_version = $Version
            format_version = 1
            target_family = "stm32wb"
            board_target = $BoardTarget
            file = $payloadName
            size_bytes = $size
            sha256 = $sha
            compatibility = [ordered]@{
                mcu = "STM32WB55"
                screen_profile = $ScreenProfile
                asset_format = "cemp"
                min_app_version = $MinAppVersion
                max_app_version = $MaxAppVersion
            }
            storage = "external_nor"
            download_target = "ui_assets_candidate"
            activation = "atomic_boot_meta"
            failure_policy = "keep_previous_active"
        }
    )
    protocol = [ordered]@{
        name = [string]$protocol.name
        version = [int]$protocol.version
        firmware_capability = [string]$protocol.name
        gatt = [ordered]@{
            service_uuid = [string]$protocol.gatt.service_uuid
            control_uuid = [string]$protocol.gatt.control_uuid
            data_uuid = [string]$protocol.gatt.data_uuid
            status_uuid = [string]$protocol.gatt.status_uuid
            chunk_bytes = 240
        }
        dual_lane = $protocol.dual_lane
    }
    notes = @(
        "Resource-only OTA package. Transfer uses denzic_ota_v1 opaque stream.",
        "Device app installer must verify CEMP + activate candidate; must not rewrite mcu_app."
    )
}

$manifestPath = Join-Path $outDir "ota_manifest.json"
($manifest | ConvertTo-Json -Depth 10) | Set-Content -LiteralPath $manifestPath -Encoding UTF8

Add-Type -AssemblyName System.IO.Compression.FileSystem
$zipPath = "$outDir.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
[System.IO.Compression.ZipFile]::CreateFromDirectory($outDir, $zipPath)

Write-Host "PASS: Companion ui_assets OTA package generated."
Write-Host "Package: $outDir"
Write-Host "Zip: $zipPath"
Write-Host "Manifest: $manifestPath"
Write-Host "Payload: $payloadName ($size bytes) sha256=$sha"
