param(
    [string] $ManifestPath,
    [switch] $Fixture,
    [switch] $Json
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$fixtureDir = Join-Path $repoRoot "docs\validation\ota"
$reportPath = Join-Path $repoRoot "docs\validation\companion-pendant-firmware-bringup-1.8-ota-manifest-fixtures.json"

$requiredBlockers = @(
    "recording_active",
    "transfer_active",
    "diag_export_active",
    "low_battery",
    "wrong_board_target",
    "invalid_hash",
    "interrupted_transfer"
)

$requiredSelfChecks = @(
    "boot_version_reported",
    "ble_advertising",
    "ota_readiness_notify",
    "diag_log_tail"
)

$acceptedTargets = @{
    "COMPANION-PENDANT-CE" = @("STM32WB55CEUx", "STM32WB55CE", "STM32WB55")
    "NUCLEO-WB55RG" = @("STM32WB55RGVX", "STM32WB55")
}

function Get-JsonValue {
    param(
        [Parameter(Mandatory = $true)][AllowNull()] $Object,
        [Parameter(Mandatory = $true)][string] $Path
    )

    $current = $Object
    foreach ($part in ($Path -split "\.")) {
        if ($null -eq $current -or -not ($current.PSObject.Properties.Name -contains $part)) {
            return [pscustomobject]@{ Exists = $false; Value = $null }
        }
        $current = $current.$part
    }
    return [pscustomobject]@{ Exists = $true; Value = $current }
}

function Add-Error {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][System.Collections.Generic.List[string]] $Errors,
        [Parameter(Mandatory = $true)][string] $Message
    )
    $Errors.Add($Message) | Out-Null
}

function Require-String {
    param(
        [Parameter(Mandatory = $true)] $Manifest,
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][System.Collections.Generic.List[string]] $Errors
    )

    $value = Get-JsonValue -Object $Manifest -Path $Path
    if (-not $value.Exists -or [string]::IsNullOrWhiteSpace([string] $value.Value)) {
        Add-Error -Errors $Errors -Message "Missing $Path"
        return $null
    }
    return [string] $value.Value
}

function Require-Int {
    param(
        [Parameter(Mandatory = $true)] $Manifest,
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][System.Collections.Generic.List[string]] $Errors,
        [int64] $Minimum = 1
    )

    $value = Get-JsonValue -Object $Manifest -Path $Path
    [int64] $parsed = 0
    if (-not $value.Exists -or -not [Int64]::TryParse([string] $value.Value, [ref] $parsed) -or $parsed -lt $Minimum) {
        Add-Error -Errors $Errors -Message "Missing or invalid $Path"
        return $null
    }
    return $parsed
}

function ConvertTo-StringArray {
    param([AllowNull()] $Value)

    if ($null -eq $Value) {
        return @()
    }
    return @($Value | ForEach-Object { [string] $_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
}

function Test-Manifest {
    param([Parameter(Mandatory = $true)][string] $Path)

    $errors = [System.Collections.Generic.List[string]]::new()
    if (-not (Test-Path -LiteralPath $Path)) {
        Add-Error -Errors $errors -Message "Manifest not found: $Path"
        return [pscustomobject]@{ ok = $false; errors = @($errors); manifest = $null }
    }

    $manifestText = Get-Content -LiteralPath $Path -Raw
    try {
        $manifest = $manifestText | ConvertFrom-Json
    } catch {
        Add-Error -Errors $errors -Message "Invalid JSON: $($_.Exception.Message)"
        return [pscustomobject]@{ ok = $false; errors = @($errors); manifest = $null }
    }

    if ($manifest.schema_version -ne 1) {
        Add-Error -Errors $errors -Message "Unexpected schema_version: $($manifest.schema_version)"
    }

    Require-String -Manifest $manifest -Path "firmware.version" -Errors $errors | Out-Null
    Require-String -Manifest $manifest -Path "firmware.board_target" -Errors $errors | Out-Null
    Require-String -Manifest $manifest -Path "firmware.mcu" -Errors $errors | Out-Null
    $imageFile = Require-String -Manifest $manifest -Path "image.file" -Errors $errors
    $imageSize = Require-Int -Manifest $manifest -Path "image.size_bytes" -Errors $errors
    $imageSha = Require-String -Manifest $manifest -Path "image.sha256" -Errors $errors
    Require-String -Manifest $manifest -Path "compatibility.st_reference" -Errors $errors | Out-Null
    Require-String -Manifest $manifest -Path "compatibility.gatt_contract" -Errors $errors | Out-Null
    Require-String -Manifest $manifest -Path "bootloader.kind" -Errors $errors | Out-Null
    Require-String -Manifest $manifest -Path "bootloader.recovery" -Errors $errors | Out-Null
    Require-String -Manifest $manifest -Path "bootloader.internal_flash_policy" -Errors $errors | Out-Null
    Require-String -Manifest $manifest -Path "bootloader.vector_table_policy" -Errors $errors | Out-Null
    Require-String -Manifest $manifest -Path "external_flash.kind" -Errors $errors | Out-Null
    Require-String -Manifest $manifest -Path "external_flash.ota_staging" -Errors $errors | Out-Null
    Require-String -Manifest $manifest -Path "external_flash.partition_policy" -Errors $errors | Out-Null
    Require-String -Manifest $manifest -Path "rollback.strategy" -Errors $errors | Out-Null
    Require-String -Manifest $manifest -Path "rollback.notes" -Errors $errors | Out-Null
    Require-String -Manifest $manifest -Path "recovery.factory_reflash" -Errors $errors | Out-Null
    Require-String -Manifest $manifest -Path "recovery.interrupted_transfer" -Errors $errors | Out-Null

    $boardTarget = (Get-JsonValue -Object $manifest -Path "firmware.board_target").Value
    $boardKey = [string] $boardTarget
    if (-not $acceptedTargets.ContainsKey($boardKey)) {
        Add-Error -Errors $errors -Message "wrong_board_target: expected COMPANION-PENDANT-CE or NUCLEO-WB55RG"
    }
    $mcu = (Get-JsonValue -Object $manifest -Path "firmware.mcu").Value
    if ($acceptedTargets.ContainsKey($boardKey) -and ([string] $mcu) -notin $acceptedTargets[$boardKey]) {
        Add-Error -Errors $errors -Message "wrong_board_target: MCU $mcu does not match $boardKey"
    }

    $bootloaderKind = [string] (Get-JsonValue -Object $manifest -Path "bootloader.kind").Value
    if ($bootloaderKind -and $bootloaderKind -notmatch "resident|st_reference|stm32wb") {
        Add-Error -Errors $errors -Message "bootloader.kind must name the STM32WB resident bootloader policy"
    }
    $externalKind = [string] (Get-JsonValue -Object $manifest -Path "external_flash.kind").Value
    if ($externalKind -and $externalKind -notmatch "qspi|nor") {
        Add-Error -Errors $errors -Message "external_flash.kind must describe QSPI NOR"
    }
    $otaStaging = [string] (Get-JsonValue -Object $manifest -Path "external_flash.ota_staging").Value
    if ($otaStaging -and $otaStaging -notmatch "single|ota_staging") {
        Add-Error -Errors $errors -Message "external_flash.ota_staging must describe the single ota_staging partition"
    }
    $dualExternal = Get-JsonValue -Object $manifest -Path "external_flash.dual_ota_partitions"
    if (-not $dualExternal.Exists) {
        Add-Error -Errors $errors -Message "Missing external_flash.dual_ota_partitions"
    } elseif ([bool] $dualExternal.Value) {
        Add-Error -Errors $errors -Message "external_flash.dual_ota_partitions must be false for the first CE layout"
    }

    if ($imageSha -and $imageSha -cnotmatch "^[0-9a-f]{64}$") {
        Add-Error -Errors $errors -Message "invalid_hash: expected lowercase SHA-256"
    }
    if ($imageFile) {
        if ([System.IO.Path]::IsPathRooted($imageFile) -or $imageFile -like "*..*") {
            Add-Error -Errors $errors -Message "image.file must be package-local"
        } else {
            $imagePath = Join-Path (Split-Path -Parent (Resolve-Path -LiteralPath $Path)) $imageFile
            if (-not (Test-Path -LiteralPath $imagePath)) {
                Add-Error -Errors $errors -Message "image.file not found: $imageFile"
            } else {
                $actualHash = (Get-FileHash -LiteralPath $imagePath -Algorithm SHA256).Hash.ToLowerInvariant()
                $actualSize = (Get-Item -LiteralPath $imagePath).Length
                if ($imageSha -and $actualHash -ne $imageSha) {
                    Add-Error -Errors $errors -Message "invalid_hash: manifest hash does not match image"
                }
                if ($imageSize -and $actualSize -ne $imageSize) {
                    Add-Error -Errors $errors -Message "image.size_bytes does not match image"
                }
            }
        }
    }

    $minBattery = Require-Int -Manifest $manifest -Path "guards.min_battery_percent" -Errors $errors -Minimum 1
    if ($minBattery -and ($minBattery -lt 30 -or $minBattery -gt 100)) {
        Add-Error -Errors $errors -Message "low-battery guard must be 30..100 percent"
    }

    $blockers = ConvertTo-StringArray -Value (Get-JsonValue -Object $manifest -Path "guards.blockers").Value
    foreach ($blocker in $requiredBlockers) {
        if ($blocker -notin $blockers) {
            Add-Error -Errors $errors -Message "Missing blocker: $blocker"
        }
    }

    $selfChecks = ConvertTo-StringArray -Value (Get-JsonValue -Object $manifest -Path "post_update_self_checks").Value
    foreach ($check in $requiredSelfChecks) {
        if ($check -notin $selfChecks) {
            Add-Error -Errors $errors -Message "Missing post-update self-check: $check"
        }
    }

    foreach ($forbidden in @("esp_idf", "esp_partition", "nvs_flash", "nimble")) {
        if ($manifestText.ToLowerInvariant().Contains($forbidden)) {
            Add-Error -Errors $errors -Message "Manifest contains forbidden ESP-specific token: $forbidden"
        }
    }

    return [pscustomobject]@{
        ok = [bool]($errors.Count -eq 0)
        errors = @($errors)
        manifest = $manifest
    }
}

function New-FixtureFiles {
    New-Item -ItemType Directory -Force -Path $fixtureDir | Out-Null
    [byte[]] $imageBytes = 0..127 | ForEach-Object { [byte] (($_ * 17 + 3) -band 0xFF) }
    $imagePath = Join-Path $fixtureDir "companion_ota_good.bin"
    [System.IO.File]::WriteAllBytes($imagePath, $imageBytes)
    $sha = (Get-FileHash -LiteralPath $imagePath -Algorithm SHA256).Hash.ToLowerInvariant()
    $size = (Get-Item -LiteralPath $imagePath).Length

    $good = [ordered]@{
        schema_version = 1
        created_at_utc = "2026-06-19T00:00:00Z"
        firmware = [ordered]@{
            project = "Companion-Firmware"
            version = "0.1.0-companion-ota"
            git_commit = "0000000000000000000000000000000000000000"
            board_target = "COMPANION-PENDANT-CE"
            mcu = "STM32WB55CEUx"
        }
        image = [ordered]@{
            file = "companion_ota_good.bin"
            size_bytes = $size
            sha256 = $sha
        }
        compatibility = [ordered]@{
            st_reference = "BLE_Ota or BLE_p2pServer_ota"
            stm32cube_wb = "v1.24.0"
            gatt_contract = "companion_ble_gatt_v1"
        }
        bootloader = [ordered]@{
            kind = "stm32wb_resident_bootloader"
            recovery = "ROM DFU or SWD via STM32CubeProgrammer"
            internal_flash_policy = "single_runnable_app_no_dual_internal_slots"
            vector_table_policy = "app_base_linker_offset_with_bootloader_jump"
        }
        external_flash = [ordered]@{
            kind = "external_qspi_nor"
            ota_staging = "single_ota_staging_partition"
            partition_policy = "boot_meta_a_b + ota_staging + recording_cache + diag_log_mirror"
            dual_ota_partitions = $false
        }
        guards = [ordered]@{
            min_battery_percent = 40
            minimum_required_mv = 3700
            blockers = $requiredBlockers
        }
        rollback = [ordered]@{
            strategy = "stm32wb_reference_ota_pending_verify"
            notes = "rollback is selected with the later ST OTA reference and must not copy ESP bootloader rollback"
        }
        recovery = [ordered]@{
            factory_reflash = "Use STM32CubeProgrammer with the accepted Companion image."
            interrupted_transfer = "Report interrupted_transfer and require host recovery before accepting new data."
        }
        post_update_self_checks = $requiredSelfChecks
    }

    $goodPath = Join-Path $fixtureDir "good_manifest.json"
    $good | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $goodPath -Encoding utf8

    $goodNucleo = $good | ConvertTo-Json -Depth 12 | ConvertFrom-Json
    $goodNucleo.firmware.version = "0.1.0-nucleo-bench-ota"
    $goodNucleo.firmware.board_target = "NUCLEO-WB55RG"
    $goodNucleo.firmware.mcu = "STM32WB55"
    $goodNucleoPath = Join-Path $fixtureDir "good_nucleo_manifest.json"
    $goodNucleo | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $goodNucleoPath -Encoding utf8

    $invalidHash = $good | ConvertTo-Json -Depth 12 | ConvertFrom-Json
    $invalidHash.image.sha256 = ("0" * 64)
    $invalidHashPath = Join-Path $fixtureDir "bad_invalid_hash_manifest.json"
    $invalidHash | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $invalidHashPath -Encoding utf8

    $wrongBoard = $good | ConvertTo-Json -Depth 12 | ConvertFrom-Json
    $wrongBoard.firmware.board_target = "LISTENER-ESP32S3"
    $wrongBoardPath = Join-Path $fixtureDir "bad_wrong_board_manifest.json"
    $wrongBoard | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $wrongBoardPath -Encoding utf8

    $missingGuard = $good | ConvertTo-Json -Depth 12 | ConvertFrom-Json
    $missingGuard.guards.blockers = @("recording_active", "transfer_active")
    $missingGuardPath = Join-Path $fixtureDir "bad_missing_blockers_manifest.json"
    $missingGuard | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $missingGuardPath -Encoding utf8

    return @(
        [pscustomobject]@{ path = $goodPath; expected = $true; case = "good" },
        [pscustomobject]@{ path = $goodNucleoPath; expected = $true; case = "good_nucleo_bringup" },
        [pscustomobject]@{ path = $invalidHashPath; expected = $false; case = "bad_invalid_hash" },
        [pscustomobject]@{ path = $wrongBoardPath; expected = $false; case = "bad_wrong_board" },
        [pscustomobject]@{ path = $missingGuardPath; expected = $false; case = "bad_missing_blockers" }
    )
}

if ($Fixture) {
    $cases = New-FixtureFiles
    $results = @()
    $failed = $false
    foreach ($case in $cases) {
        $result = Test-Manifest -Path $case.path
        $passed = [bool]($result.ok -eq $case.expected)
        if (-not $passed) {
            $failed = $true
        }
        $results += [ordered]@{
            case = $case.case
            manifest = (Resolve-Path -LiteralPath $case.path).Path.Substring($repoRoot.Length).TrimStart("\", "/")
            expected_valid = $case.expected
            actual_valid = $result.ok
            status = if ($passed) { "PASS" } else { "FAIL" }
            errors = @($result.errors)
        }
    }
    $report = [ordered]@{
        schema_id = "companion.pendant.ota_manifest_fixture_report.v1"
        status = if ($failed) { "FAIL" } else { "PASS" }
        required_blockers = $requiredBlockers
        required_post_update_self_checks = $requiredSelfChecks
        cases = $results
    }
    $report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $reportPath -Encoding utf8
    if ($Json) {
        $report | ConvertTo-Json -Depth 12
    } else {
        Write-Output "$($report.status): Companion OTA manifest fixture validation -> docs/validation/companion-pendant-firmware-bringup-1.8-ota-manifest-fixtures.json"
    }
    if ($failed) { exit 1 }
    exit 0
}

if ([string]::IsNullOrWhiteSpace($ManifestPath)) {
    throw "Pass -ManifestPath <path> or -Fixture."
}

$single = Test-Manifest -Path $ManifestPath
if ($Json) {
    [ordered]@{ status = if ($single.ok) { "PASS" } else { "FAIL" }; errors = @($single.errors) } | ConvertTo-Json -Depth 6
} elseif ($single.ok) {
    Write-Output "PASS: Companion OTA manifest valid."
} else {
    Write-Output "FAIL: Companion OTA manifest invalid:"
    $single.errors | ForEach-Object { Write-Output "  - $_" }
}
if (-not $single.ok) { exit 1 }
