#!/usr/bin/env python3
"""Guard the accepted single-plane Mode-2 product path."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
DRIVER = (
    REPO
    / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
)
DISPLAY_QUEUE = REPO / "app/companion_pendant/epaper/display_queue.h"
ASSET_SOURCE = REPO / "app/companion_pendant/epaper/expression_asset_source.c"
APP_BLE = (
    REPO
    / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
)
SOURCE_PACK = (
    REPO
    / ".cache/validation/comp-req-775-incremental-sync/direct/current-source-pack"
)
OUTPUT = (
    REPO
    / ".cache/validation/comp-req-775-incremental-sync"
    / "ONE_PLANE_CHOREOGRAPHY_READY.json"
)


def function_body(source: str, signature: str) -> str:
    start = source.find(signature)
    if start < 0:
        return ""
    brace = source.find("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    return ""


def read_p4(path: Path) -> bytes:
    data = path.read_bytes()
    position = 0
    tokens: list[bytes] = []
    while len(tokens) < 3:
        while position < len(data) and data[position] in b" \t\r\n":
            position += 1
        if position < len(data) and data[position] == ord("#"):
            position = data.index(b"\n", position) + 1
            continue
        end = position
        while end < len(data) and data[end] not in b" \t\r\n":
            end += 1
        tokens.append(data[position:end])
        position = end
    while position < len(data) and data[position] in b" \t\r\n":
        position += 1
    if tokens != [b"P4", b"200", b"200"] or len(data) - position != 5000:
        raise ValueError(f"unexpected PBM contract: {path}")
    return data[position:]


def main() -> int:
    source = DRIVER.read_text(encoding="utf-8")
    display_queue = DISPLAY_QUEUE.read_text(encoding="utf-8")
    asset_source = ASSET_SOURCE.read_text(encoding="utf-8")
    app_ble = APP_BLE.read_text(encoding="utf-8")
    product = function_body(
        source, "ssd1681_accepted_cached_mode2_product_refresh("
    )
    cached = function_body(
        source,
        "companion_epaper_panel_stm32wb_ssd1681_cached_mode2_diff(",
    )
    stable_window = function_body(source, "ssd1681_product_stable_window(")
    activation = function_body(
        source, "ssd1681_native_cached_mode2_movement_activation("
    )
    fast_full = function_body(
        source, "ssd1681_accepted_fast_full_activation("
    )
    battery_signature = (
        "static void Companion_Display_ApplyBatteryExpressionHint("
    )
    battery_hint = function_body(
        app_ble[app_ble.rfind(battery_signature) :], battery_signature
    )
    tick_signature = "static void Companion_Display_ProcessExpressionTick("
    expression_tick = function_body(
        app_ble[app_ble.rfind(tick_signature) :], tick_signature
    )
    source_manifest = json.loads(
        (SOURCE_PACK / "source-pack-manifest.json").read_text(encoding="utf-8")
    )
    states = source_manifest["states"]
    charging_states = [
        next(state for state in states if state["id"] == f"charging_{index}")
        for index in range(3)
    ]
    charging_frames = [
        read_p4(SOURCE_PACK / state["pbm_file"])
        for state in charging_states
    ]
    life_states = [state for state in states if state["kind"] == "life"][:32]
    overlay_x_byte = 72 // 8
    overlay_width_bytes = 56 // 8
    overlay_rows = range(168, 200)
    overlay_bytes_by_frame = [
        b"".join(
            charging_frame[row * 25 + overlay_x_byte :
                           row * 25 + overlay_x_byte + overlay_width_bytes]
            for row in overlay_rows
        )
        for charging_frame in charging_frames
    ]
    overlay_hashes: set[str] = set()
    outside_unchanged = True
    overlay_changed_life_frames = 0
    for state in life_states:
        life_frame = read_p4(SOURCE_PACK / state["pbm_file"])
        for charging_frame in charging_frames:
            composed = bytearray(life_frame)
            overlay_changed = False
            for row in overlay_rows:
                start = row * 25 + overlay_x_byte
                end = start + overlay_width_bytes
                if composed[start:end] != charging_frame[start:end]:
                    overlay_changed = True
                composed[start:end] = charging_frame[start:end]
            if overlay_changed:
                overlay_changed_life_frames += 1
            overlay_hashes.add(
                hashlib.sha256(
                    b"".join(
                        composed[row * 25 + overlay_x_byte :
                                 row * 25 + overlay_x_byte + overlay_width_bytes]
                        for row in overlay_rows
                    )
                ).hexdigest().upper()
            )
            for row in range(200):
                row_start = row * 25
                if row in overlay_rows:
                    before = life_frame[row_start : row_start + overlay_x_byte]
                    after = life_frame[
                        row_start + overlay_x_byte + overlay_width_bytes : row_start + 25
                    ]
                    if composed[row_start : row_start + overlay_x_byte] != before or composed[
                        row_start + overlay_x_byte + overlay_width_bytes : row_start + 25
                    ] != after:
                        outside_unchanged = False
                elif composed[row_start : row_start + 25] != life_frame[
                    row_start : row_start + 25
                ]:
                    outside_unchanged = False
    full = function_body(
        source,
        "companion_epaper_panel_stm32wb_ssd1681_comp_req_611_full_0xff(",
    )
    true_full = function_body(
        source,
        "ssd1681_accepted_true_full_activation(",
    )
    checks = {
        "initial_and_boundary_full_refresh_retained": (
            "first_frame = !s_controller_initialized" in product
            and "requested_mode == COMP_EPAPER_REFRESH_MAINTENANCE" in product
            and "ssd1681_accepted_fast_full_activation(" in product
            and "ssd1681_accepted_true_full_activation(" in product
            and all(
                token in fast_full
                for token in (
                    "companion_epaper_panel_stm32wb_ssd1681_comp_req_611_full_0xff(",
                    "profile=accepted_cached_mode2",
                    "control=0xFF",
                    "window=200x200 bytes_each=5000 data_planes=2",
                    "rearm_activation=0",
                )
            )
            and "0xC7" not in fast_full
            and all(
                token in true_full
                for token in (
                    "control=0xC7",
                    "window=200x200 bytes_each=5000 data_planes=2",
                    "activation_count=%u",
                    "mode2_rearm=0x99",
                    "rearm_display_activation=0",
                )
            )
        ),
        "boundary_full_preseeds_both_banks_before_single_activation": (
            "ssd1681_write_plane_region(0x26u, s_frame, &window)" in full
            and "ssd1681_native_no_reset_movement_activation(" in full
            and full.index("ssd1681_write_plane_region(0x26u, s_frame, &window)")
            < full.index("ssd1681_native_no_reset_movement_activation(")
            and full.count("ssd1681_native_no_reset_movement_activation(") == 1
            and "Seeding 0x26 after BUSY is too late" in full
        ),
        "home_uses_cached_mode2_diff": (
            "companion_epaper_panel_stm32wb_ssd1681_cached_mode2_diff("
            in product
            and "UINT8_MAX" in source
        ),
        "product_uses_source_complete_stable_window_tiers": (
            "window = ssd1681_window_from_difference();" in cached
            and "window = ssd1681_product_stable_window("
            in cached
            and all(
                token in stable_window
                for token in (
                    ".x_start_byte = 0u",
                    ".x_end_byte = 21u",
                    ".y_start = 46u",
                    ".y_end = 171u",
                    ".x_end_byte = 24u",
                    ".y_start = 4u",
                    "ssd1681_window_contains(&home, difference)",
                    "ssd1681_window_contains(&content, difference)",
                    "if (persistent_content_window)",
                    "return content;",
                    "return ssd1681_window_full();",
                )
            )
        ),
        "charger_updates_each_ping_pong_bank_via_content_window": (
            "bool persistent_content_window" in cached
            and "&window, persistent_content_window" in cached
            and "COMP_EPAPER_DISPLAY_FLAG_CHARGER_PRESENT" in product
            and "charger_window=%u" in product
            and "ssd1681_write_plane_region(0x26u" not in cached
            and activation.count("ssd1681_command(0x20u)") == 1
        ),
        "current_frame_staged_to_0x24": (
            "ssd1681_write_plane_region(0x24u, s_frame, window)"
            in activation
        ),
        "cached_waveform_activation_is_single_current_plane": (
            "ssd1681_write_plane_region(0x26u" not in activation
            and activation.count("ssd1681_command(0x20u)") == 1
        ),
        "partials_keep_controller_old_plane_untouched": (
            "ssd1681_write_plane_region(0x26u" not in cached
            and "ssd1681_write_plane_region(0x26u" not in fast_full
            and "previous_plane_sync=%u" in product
            and "post_sync_command=0x%02X" in product
            and "post_sync_refresh=0" in product
            and cached.count("ssd1681_command(0x20u)") == 0
        ),
        "controller_ram_audit_is_not_in_product_build": (
            "#define COMPANION_EPAPER_SSD1681_PRODUCT_RAM_AUDIT 0" in source
        ),
        "home_automatic_full_maintenance_disabled": (
            "comp_epaper_refresh_policy_init(&s_target_context.refresh_policy,"
            in source
            and "UINT8_MAX);" in source
            and "legacy FULL/AUTO callers cannot insert one" in product
            and (
                "selection.decision = COMP_EPAPER_REFRESH_DECISION_PARTIAL"
                in product
            )
        ),
        "completed_partial_keeps_product_baseline": (
            "#if COMPANION_EPAPER_SSD1681_ACCEPTED_CACHED_MODE2_PRODUCT"
            in activation
            and "SSD1681_NATIVE_TWO_PASS_BUSY_LIMIT_MS + 100u"
            in activation
            and "does not invalidate the" in activation
            and "return ok;" in activation
        ),
        "charger_is_persistent_composited_device_state": (
            "COMP_EPAPER_DISPLAY_FLAG_CHARGER_PRESENT 0x2000u"
            in display_queue
            and "display_flags |= COMP_EPAPER_DISPLAY_FLAG_CHARGER_PRESENT"
            in app_ble
            and "comp_epaper_expression_asset_source_copy_clip_frame"
            in asset_source
            and "COMP_EPAPER_DISPLAY_FLAG_AUTO_ACCESSORY 0x1000u"
            in display_queue
            and all(
                token in source
                for token in (
                    "ssd1681_compose_charger_overlay(",
                    "SSD1681_CHARGER_OVERLAY_X 72u",
                    "SSD1681_CHARGER_OVERLAY_Y 168u",
                    "SSD1681_CHARGER_OVERLAY_WIDTH 56u",
                    "SSD1681_CHARGER_OVERLAY_HEIGHT 32u",
                    '"charging",',
                    "source=cemp_clip_frame",
                    "persistent=1",
                )
            )
            and "Companion_Screen_StartNamedClip" not in battery_hint
            and "charging_event_complete" not in expression_tick
            and "charging_event complete=1" not in expression_tick
            and "charger_overlay latch=1" in battery_hint
            and "charger_overlay latch=0" in battery_hint
        ),
        "browser_overlay_frames_are_authored_and_bounded": (
            len(life_states) == 32
            and all(len(overlay_bytes) == 224
                    for overlay_bytes in overlay_bytes_by_frame)
            and len({hashlib.sha256(overlay_bytes).hexdigest().upper()
                     for overlay_bytes in overlay_bytes_by_frame}) == 3
            and len(overlay_hashes) == 3
            and outside_unchanged
            and overlay_changed_life_frames > 0
        ),
    }
    ready = all(checks.values())
    receipt = {
        "schema": "companion.comp_req_775.dual_preseed_persistent_status_overlay.v13",
        "status": "MACHINE_READY" if ready else "FAILED",
        "checks": checks,
        "driver_sha256": hashlib.sha256(DRIVER.read_bytes()).hexdigest().upper(),
        "protected_owner_result": (
            ".cache/validation/comp-req-771-accepted-path-comparison/"
            "hardware-run/operator-result.json"
        ),
        "protected_firmware_sha256": (
            "FC282F45B15D856BD85C4D22CF653976455F960A644F836EC59CD5C2D2D9063A"
        ),
        "protected_transition_envelope_pixels": {
            "black_to_white_max": 2548,
            "white_to_black_max": 2123,
            "xor_max": 4319,
        },
        "current_generation_7_transition_envelope_pixels": {
            "black_to_white_max": 538,
            "white_to_black_max": 576,
            "xor_max": 969,
        },
        "generation_7_pixels_clipped_by_legacy_corridor": {
            "tap_phase_pair_min": 66,
            "tap_phase_pair_max": 151,
            "minimum_source_x": 8,
            "legacy_minimum_source_x": 32,
        },
        "hardware_contact": 0,
        "charging_overlay_pixel_evidence": {
            "browser_states": [state["id"] for state in charging_states],
            "bounds": {"x": 72, "y": 168, "width": 56, "height": 32},
            "bytes_per_frame": [len(frame) for frame in overlay_bytes_by_frame],
            "sha256": [
                hashlib.sha256(frame).hexdigest().upper()
                for frame in overlay_bytes_by_frame
            ],
            "life_frames_checked": len(life_states),
            "life_frames_changed_by_overlay": overlay_changed_life_frames,
            "outside_bounds_unchanged": outside_unchanged,
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
