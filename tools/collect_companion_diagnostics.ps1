param(
    [switch] $Fixture,
    [string] $OutputDir = "docs\validation\companion-diagnostics-fixture",
    [int] $MaxDiagEvents = 8,
    [int] $MaxDiagBytes = 1024,
    [string] $SourceFilter = "all",
    [string] $SeverityMask = "info|warn|error"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if (-not $Fixture) {
    throw "Only fixture/no-hardware Companion diagnostics are implemented. Pass -Fixture to avoid touching hardware."
}

if ($MaxDiagEvents -lt 1 -or $MaxDiagEvents -gt 64) {
    throw "MaxDiagEvents must be 1..64 for bounded diagnostics export."
}

if ($MaxDiagBytes -lt 128 -or $MaxDiagBytes -gt 4096) {
    throw "MaxDiagBytes must be 128..4096 for bounded diagnostics export."
}

$outputPath = if ([System.IO.Path]::IsPathRooted($OutputDir)) {
    $OutputDir
} else {
    Join-Path $repoRoot $OutputDir
}
$outputDirResolved = (New-Item -ItemType Directory -Force -Path $outputPath).FullName
$rawJsonl = Join-Path $outputDirResolved "diag_tail_raw.jsonl"
$decodedJson = Join-Path $outputDirResolved "diag_tail_decoded.json"
$summaryJson = Join-Path $outputDirResolved "summary.json"
$summaryMd = Join-Path $outputDirResolved "summary.md"

function New-DiagEvent {
    param(
        [int] $Sequence,
        [int] $TimeMs,
        [string] $Source,
        [int] $EventId,
        [string] $Severity,
        [int] $Arg0 = 0,
        [int] $Arg1 = 0,
        [int] $Arg2 = 0,
        [int] $Arg3 = 0
    )

    [ordered]@{
        sequence = $Sequence
        t_ms = $TimeMs
        source = $Source
        event_id = $EventId
        severity = $Severity
        arg0 = $Arg0
        arg1 = $Arg1
        arg2 = $Arg2
        arg3 = $Arg3
    }
}

function Write-JsonFile {
    param(
        [Parameter(Mandatory = $true)] $Value,
        [Parameter(Mandatory = $true)][string] $Path,
        [int] $Depth = 16
    )

    $Value | ConvertTo-Json -Depth $Depth | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Get-DisplayPath {
    param([Parameter(Mandatory = $true)][string] $Path)

    $resolved = if (Test-Path -LiteralPath $Path) {
        (Resolve-Path -LiteralPath $Path).Path
    } else {
        [System.IO.Path]::GetFullPath($Path)
    }
    if ($resolved.StartsWith($repoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        return [System.IO.Path]::GetRelativePath($repoRoot, $resolved).Replace("\", "/")
    }
    return $resolved
}

$rawEvents = @()
$rawEvents += New-DiagEvent -Sequence 101 -TimeMs 10 -Source "boot" -EventId 1 -Severity "info" -Arg0 1
$rawEvents += New-DiagEvent -Sequence 102 -TimeMs 45 -Source "ble" -EventId 1 -Severity "info" -Arg0 1 -Arg1 -47
$rawEvents += New-DiagEvent -Sequence 103 -TimeMs 88 -Source "gatt" -EventId 2 -Severity "info" -Arg0 0 -Arg1 $MaxDiagEvents -Arg2 $MaxDiagBytes
$rawEvents += New-DiagEvent -Sequence 104 -TimeMs 130 -Source "recording_fsm" -EventId 1 -Severity "info" -Arg0 1 -Arg1 2
$rawEvents += New-DiagEvent -Sequence 105 -TimeMs 160 -Source "spi_flash_cache" -EventId 1 -Severity "info" -Arg0 32768 -Arg1 2400
$rawEvents += New-DiagEvent -Sequence 106 -TimeMs 190 -Source "e_paper" -EventId 2 -Severity "info" -Arg0 17 -Arg1 0
$rawEvents += New-DiagEvent -Sequence 107 -TimeMs 220 -Source "ota" -EventId 1 -Severity "info" -Arg0 1 -Arg1 94032
$rawEvents += New-DiagEvent -Sequence 108 -TimeMs 240 -Source "ota" -EventId 3 -Severity "info" -Arg0 1 -Arg1 0
$rawEvents += New-DiagEvent -Sequence 109 -TimeMs 260 -Source "battery_charging" -EventId 1 -Severity "info" -Arg0 84 -Arg1 4012
$rawEvents += New-DiagEvent -Sequence 110 -TimeMs 290 -Source "power_lpm" -EventId 2 -Severity "warn" -Arg0 2 -Arg1 1
$rawEvents += New-DiagEvent -Sequence 111 -TimeMs 310 -Source "warnings" -EventId 2 -Severity "info" -Arg0 1
$rawEvents += New-DiagEvent -Sequence 112 -TimeMs 340 -Source "errors" -EventId 1 -Severity "error" -Arg0 0
$rawEvents += New-DiagEvent -Sequence 113 -TimeMs 360 -Source "meeting" -EventId 1 -Severity "info" -Arg0 1
$rawEvents += New-DiagEvent -Sequence 114 -TimeMs 390 -Source "meeting" -EventId 3 -Severity "info" -Arg0 1 -Arg1 2400
$rawEvents += New-DiagEvent -Sequence 115 -TimeMs 420 -Source "imu" -EventId 3 -Severity "warn" -Arg0 1
$rawEvents += New-DiagEvent -Sequence 116 -TimeMs 450 -Source "speaker" -EventId 1 -Severity "info" -Arg0 7
$rawEvents += New-DiagEvent -Sequence 117 -TimeMs 480 -Source "wake_word" -EventId 1 -Severity "info" -Arg0 50
$rawEvents += New-DiagEvent -Sequence 118 -TimeMs 510 -Source "device_settings" -EventId 1 -Severity "info" -Arg0 12
$rawEvents += New-DiagEvent -Sequence 119 -TimeMs 540 -Source "e_paper" -EventId 3 -Severity "warn" -Arg0 327683 -Arg1 131076 -Arg2 1 -Arg3 458753

$rawEvents |
    ForEach-Object { $_ | ConvertTo-Json -Compress -Depth 8 } |
    Set-Content -LiteralPath $rawJsonl -Encoding UTF8

Push-Location $repoRoot
try {
    & python ".\tools\decode_diag_log.py" --input $rawJsonl --output $decodedJson
    if ($LASTEXITCODE -ne 0) {
        throw "decode_diag_log.py failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}

$decoded = Get-Content -LiteralPath $decodedJson -Raw -Encoding UTF8 | ConvertFrom-Json
$decodedEvents = @($decoded.events)
$tailEvents = @($decodedEvents | Select-Object -Last $MaxDiagEvents)
$lastSequence = if ($tailEvents.Count -gt 0) { [int]$tailEvents[-1].sequence } else { 0 }

$summary = [ordered]@{
    schema_id = "companion.pendant.diagnostics_bundle.v1"
    schema_version = 1
    mode = "fixture"
    generated_at = "fixture-deterministic"
    bounded = $true
    hardware_action = $false
    source_refs = @(
        "app/companion_pendant/diag_log/diag_log_events.h",
        "docs/ble_gatt_contract.md",
        "tools/decode_diag_log.py"
    )
    privacy = [ordered]@{
        private_audio_payload_exported = $false
        raw_recording_payload_exported = $false
        no_unbounded_full_dumps = $true
        fixture_contains_synthetic_metadata_only = $true
    }
    device_status = [ordered]@{
        product = "companion"
        board_target = "NUCLEO-WB55RG"
        mcu = "STM32WB55RG"
        firmware_semver = "0.1.0-fixture"
        build_id = "diagnostics-fixture"
        active_mode = "idle"
        fault_bitmap = 0
        uptime_ms = 540
    }
    ble = [ordered]@{
        backend = "fixture-no-hardware"
        selected_device = [ordered]@{
            name = "Companion Pendant Dev"
            address = "F1:E2:D3:C4:B5:A6"
            service_uuid = "8f7a0001-7b7d-4f3d-9d6f-6c2d1b7c0000"
            rssi = -47
        }
        scan_summary = [ordered]@{
            scanned_devices = 2
            matched_companion_devices = 1
            ignored_devices = 1
        }
    }
    recording = [ordered]@{
        fsm_state = "stored"
        session_id = "fixture-rec-0001"
        last_transition = "recording_fsm.transition"
        active = $false
        transfer_active = $false
    }
    recording_cache = [ordered]@{
        backend = "external_spi_nor_contract_fixture"
        count = 1
        total_bytes = 32768
        entries = @(
            [ordered]@{
                recording_id = 1
                duration_ms = 2400
                codec = "pcm16"
                sample_rate_hz = 16000
                total_length = 32768
                sha256_prefix = "fixture_sha256_0001"
                sync_state = "unsynced"
                delete_state = "stored"
            }
        )
    }
    last_transfer_result = [ordered]@{
        operation = "recording_chunk_pull"
        status = "fixture_not_started"
        byte_offset = 0
        requested_length = 0
        final_sha256_verified = $false
    }
    meeting = [ordered]@{
        state = "finalized"
        meeting_id = 1
        duration_ms = 2400
        segment_count = 1
        summary_state = "pending_host_summary"
        sync_state = "ready_for_host_sync"
    }
    imu = [ordered]@{
        sensor_state = "not_populated_on_current_dev_board"
        motion_flags = @()
        sample_rate_hz = 0
        calibration_state = "pending_hardware"
    }
    speaker = [ordered]@{
        state = "prompt_contract_ready_pending_hardware"
        prompt_id = 7
        volume_percent = 50
        played_count = 1
    }
    voice_wake = [ordered]@{
        armed = $true
        engine_state = "armed_fixture"
        sensitivity = 50
        detection_count = 0
        rejected_count = 0
    }
    ble_name_config = [ordered]@{
        active_name = "companion"
        staged_name = "companion-v1"
        max_len = 29
        policy = "printable_ascii_1_29_no_quotes_semicolon_equals_backslash"
        apply = "restart_ble_or_reboot_required"
    }
    epaper = [ordered]@{
        last_card_slot = 0
        last_card_type = "status"
        render_state = "rendered"
        content_crc32 = "0x00000011"
        refresh_count = 1
        runtime_snapshot_decoded = [ordered]@{
            expression_current = 5
            expression_last_signal = 3
            display_queue_pending_count = 2
            display_queue_high_water_count = 4
            display_queue_dropped_count = 1
            panel_deferred_count = 7
            panel_error_count = 1
        }
    }
    ota = [ordered]@{
        manifest = [ordered]@{
            version = "0.1.0-fixture"
            board_target = "NUCLEO-WB55RG"
            image_size = 94032
            sha256_prefix = "fixture_ota_hash"
        }
        readiness = [ordered]@{
            ready_state = "ready"
            blocker_bitmap = 0
            minimum_required_mv = 3600
            charger_required = $false
        }
        blockers = @()
    }
    battery = [ordered]@{
        percent = 84
        millivolts = 4012
        charge_state = "discharging"
        charger_present = $false
        temperature_c_x10 = 261
    }
    diag_tail = [ordered]@{
        bounded = $true
        contract = "diagnostics/log pull cursor/source/severity model"
        request = [ordered]@{
            cursor = 0
            max_events = $MaxDiagEvents
            max_bytes = $MaxDiagBytes
            source = $SourceFilter
            severity_mask = $SeverityMask
        }
        total_available = $decodedEvents.Count
        returned_count = $tailEvents.Count
        next_cursor = $lastSequence
        decoded_path = Get-DisplayPath -Path $decodedJson
        raw_path = Get-DisplayPath -Path $rawJsonl
        events = $tailEvents
    }
    artifacts = [ordered]@{
        summary_json = Get-DisplayPath -Path $summaryJson
        summary_md = Get-DisplayPath -Path $summaryMd
        diag_tail_raw_jsonl = Get-DisplayPath -Path $rawJsonl
        diag_tail_decoded_json = Get-DisplayPath -Path $decodedJson
    }
}

Write-JsonFile -Value $summary -Path $summaryJson -Depth 24

$md = @(
    "# Companion Diagnostics Fixture",
    "",
    "- Status: PASS",
    "- Mode: fixture/no-hardware",
    "- Bounded: true",
    "- Hardware action: false",
    "- Private audio payload exported: false",
    "- Device: companion / NUCLEO-WB55RG",
    "- BLE selected device: Companion Pendant Dev",
    "- Recording cache entries: 1",
    "- OTA readiness: ready",
    "- Battery: 84 percent / 4012 mV",
    "- Diag tail: $($tailEvents.Count) of $($decodedEvents.Count) events, cursor $lastSequence",
    "- Summary JSON: $(Get-DisplayPath -Path $summaryJson)",
    "- Decoded tail: $(Get-DisplayPath -Path $decodedJson)"
)
$md | Set-Content -LiteralPath $summaryMd -Encoding UTF8

Write-Output "PASS: Companion diagnostics fixture bundle -> $summaryJson"
Write-Output "companion_diagnostics_result_json=$($summary | ConvertTo-Json -Depth 24 -Compress)"
