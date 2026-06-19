param(
    [switch] $SelfTest,
    [switch] $Json,
    [string] $ContractPath,
    [string] $UuidTablePath,
    [string] $FixturePath,
    [string] $OutputPath
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if (-not $ContractPath) {
    $ContractPath = Join-Path $repoRoot "docs\ble_gatt_contract.md"
}
if (-not $UuidTablePath) {
    $UuidTablePath = Join-Path $repoRoot "docs\ble_uuid_table.json"
}

function Resolve-InputPath {
    param([Parameter(Mandatory = $true)][string] $Path)

    if ([System.IO.Path]::IsPathRooted($Path)) {
        return (Resolve-Path -LiteralPath $Path).Path
    }

    return (Resolve-Path -LiteralPath (Join-Path $repoRoot $Path)).Path
}

function Get-DisplayPath {
    param([Parameter(Mandatory = $true)][string] $Path)

    $resolved = (Resolve-Path -LiteralPath $Path).Path
    if ($resolved.StartsWith($repoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $resolved.Substring($repoRoot.Length).TrimStart([char[]]@("\", "/"))
    }

    return $resolved
}

function Assert-Contains {
    param(
        [Parameter(Mandatory = $true)][string] $Text,
        [Parameter(Mandatory = $true)][string] $Needle,
        [Parameter(Mandatory = $true)][string] $Label
    )

    if (-not $Text.Contains($Needle)) {
        throw "Missing '$Needle' in $Label."
    }
}

function Get-Crc32Hex {
    param([Parameter(Mandatory = $true)][byte[]] $Bytes)

    [uint32] $crc = [uint32]::MaxValue
    [uint32] $polynomial = 3988292384
    foreach ($byte in $Bytes) {
        $crc = $crc -bxor [uint32] $byte
        for ($i = 0; $i -lt 8; $i++) {
            if (($crc -band 1) -ne 0) {
                $crc = ($crc -shr 1) -bxor $polynomial
            } else {
                $crc = $crc -shr 1
            }
        }
    }

    $crc = $crc -bxor [uint32]::MaxValue
    return ("0x{0:x8}" -f $crc)
}

function Get-Sha256Hex {
    param([Parameter(Mandatory = $true)][byte[]] $Bytes)

    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([System.BitConverter]::ToString($sha256.ComputeHash($Bytes))).Replace("-", "").ToLowerInvariant()
    } finally {
        $sha256.Dispose()
    }
}

function New-RecordingFixture {
    param([string] $FixturePath)

    if ($FixturePath) {
        $path = Resolve-InputPath -Path $FixturePath
        return Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
    }

    $payloadText = "companion-fixture-pcm-window-0001"
    $payloadBytes = [System.Text.Encoding]::UTF8.GetBytes($payloadText)
    $firstLength = 16
    $secondLength = $payloadBytes.Length - $firstLength
    $firstBytes = New-Object byte[] $firstLength
    [Array]::Copy($payloadBytes, 0, $firstBytes, 0, $firstLength)
    $secondBytes = New-Object byte[] $secondLength
    [Array]::Copy($payloadBytes, $firstLength, $secondBytes, 0, $secondLength)

    return [pscustomobject]@{
        recording_id = "0000002a"
        total_length = $payloadBytes.Length
        sha256 = Get-Sha256Hex -Bytes $payloadBytes
        delete_after_sync_requested = $false
        packets = @(
            [pscustomobject]@{
                packet_sequence = 0
                byte_offset = 0
                total_length = $payloadBytes.Length
                payload_length = $firstBytes.Length
                crc32 = Get-Crc32Hex -Bytes $firstBytes
                resume = $false
            },
            [pscustomobject]@{
                packet_sequence = 1
                byte_offset = $firstBytes.Length
                total_length = $payloadBytes.Length
                payload_length = $secondBytes.Length
                crc32 = Get-Crc32Hex -Bytes $secondBytes
                resume = $true
            }
        )
    }
}

function Assert-RecordingFixture {
    param([Parameter(Mandatory = $true)] $Fixture)

    $packets = @($Fixture.packets)
    if ($packets.Count -lt 2) {
        throw "Fixture must include at least two recording chunk pull packets."
    }
    if ($Fixture.total_length -le 0) {
        throw "Fixture total_length must be positive."
    }
    if ($Fixture.sha256.Length -ne 64) {
        throw "Fixture final hash must be a 64-character SHA-256 hex value."
    }
    if ($Fixture.delete_after_sync_requested) {
        throw "Fixture must prove delete-after-sync stays false before host verification."
    }

    $nextOffset = 0
    for ($i = 0; $i -lt $packets.Count; $i++) {
        $packet = $packets[$i]
        if ($packet.packet_sequence -ne $i) {
            throw "Packet sequence mismatch at index $i."
        }
        if ($packet.byte_offset -ne $nextOffset) {
            throw "Byte offset mismatch at packet $i."
        }
        if ($packet.total_length -ne $Fixture.total_length) {
            throw "Total length changed at packet $i."
        }
        if (-not ($packet.crc32 -match "^0x[0-9a-fA-F]{8}$")) {
            throw "CRC32 format mismatch at packet $i."
        }
        $nextOffset += $packet.payload_length
    }
    if ($nextOffset -ne $Fixture.total_length) {
        throw "Packet payload lengths do not add up to total_length."
    }
}

if (-not $SelfTest) {
    Write-Output "Companion BLE probe hardware mode is intentionally not enabled in this step."
    Write-Output "Run: pwsh -NoProfile -File .\tools\companion_ble_probe.ps1 -SelfTest -Json"
    exit 0
}

$contractPathResolved = Resolve-InputPath -Path $ContractPath
$uuidTablePathResolved = Resolve-InputPath -Path $UuidTablePath
$contractText = Get-Content -LiteralPath $contractPathResolved -Raw
$uuidTable = Get-Content -LiteralPath $uuidTablePathResolved -Raw | ConvertFrom-Json

$anchors = @(
    "| service | characteristic | direction | payload | validation |",
    "| error | trigger | device behavior | host behavior |",
    "recording chunk pull",
    "packet sequence",
    "CRC",
    "delete-after-sync",
    "diagnostics/log pull",
    "OTA readiness",
    "STM32_WPAN"
)
foreach ($anchor in $anchors) {
    Assert-Contains -Text $contractText -Needle $anchor -Label (Get-DisplayPath -Path $contractPathResolved)
}

$requiredCharacteristics = @(
    "device_status",
    "battery_charge",
    "e_paper_card_write",
    "e_paper_card_status",
    "recording_control",
    "recording_list",
    "recording_chunk_pull",
    "settings",
    "diagnostics_log_pull",
    "delete_privacy",
    "ota_readiness"
)

$seen = @{}
foreach ($service in @($uuidTable.services)) {
    foreach ($characteristic in @($service.characteristics)) {
        $name = [string] $characteristic.name
        if ($seen.ContainsKey($name)) {
            throw "Duplicate characteristic in UUID table: $name"
        }
        if (-not ([string] $characteristic.uuid -match "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")) {
            throw "Invalid UUID for characteristic: $name"
        }
        $seen[$name] = $true
    }
}

foreach ($name in $requiredCharacteristics) {
    if (-not $seen.ContainsKey($name)) {
        throw "Missing required characteristic in UUID table: $name"
    }
}

$fixture = New-RecordingFixture -FixturePath $FixturePath
Assert-RecordingFixture -Fixture $fixture

$result = [ordered]@{
    probe = "companion_ble_probe"
    mode = "fixture-self-test"
    status = "PASS"
    contract = Get-DisplayPath -Path $contractPathResolved
    uuid_table = Get-DisplayPath -Path $uuidTablePathResolved
    anchors_checked = $anchors
    required_characteristics_checked = $requiredCharacteristics
    recording_fixture = $fixture
    stm32_surface = "STM32_WPAN GATT server via aci_gatt_add_service, aci_gatt_add_char, aci_gatt_update_char_value, and SVCCTL_App_Notification"
}

$jsonText = $result | ConvertTo-Json -Depth 8
if ($OutputPath) {
    $outputFullPath = if ([System.IO.Path]::IsPathRooted($OutputPath)) {
        $OutputPath
    } else {
        Join-Path $repoRoot $OutputPath
    }
    $outputDir = Split-Path -Parent $outputFullPath
    if ($outputDir) {
        New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
    }
    $jsonText | Out-File -LiteralPath $outputFullPath -Encoding utf8
}

if ($Json) {
    Write-Output $jsonText
} else {
    Write-Output "PASS: Companion BLE contract and fixture probe self-test passed."
    Write-Output "Contract: $(Get-DisplayPath -Path $contractPathResolved)"
    Write-Output "UUID table: $(Get-DisplayPath -Path $uuidTablePathResolved)"
    Write-Output "Characteristics checked: $($requiredCharacteristics.Count)"
}
