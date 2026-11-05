#!/usr/bin/env python3
"""Verify browser-native tap frames and the WB55 runtime binding."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / ".cache/validation/comp-req-628-status-bar/index.html"
PACK = (
    ROOT
    / ".cache/validation/comp-req-775-browser-device-single-source-final"
    / "source-pack-ten-family-v2"
)
SOURCE = PACK / "source-pack-manifest.json"
CEMP_ROOT = (
    ROOT
    / ".cache/validation/comp-req-775-menu-hold-milestone-source-pack-v3"
    / "cemp"
)
CEMP = CEMP_ROOT / "manifest.json"
CEMP_VERIFY = CEMP_ROOT / "verification.json"
RUNTIME = (
    ROOT
    / ".cache/validation/comp-req-775-browser-device-single-source-final"
    / "generation-14"
)
GENERATION = RUNTIME / "generation-14.json"
GENERATION_VERIFY = RUNTIME / "verification.json"
BUNDLE_RECEIPT = RUNTIME / "bundle-receipt.json"
APP_BLE = (
    ROOT
    / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
)
EMOTE_ASSET_PACK = (
    ROOT
    / "app/companion_pendant/epaper/emote_asset_pack.c"
)
MAIN = (
    ROOT
    / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"
)
APP_ENTRY = (
    ROOT
    / "third_party/STM32CubeWB/Projects/P-NUCLEO-WB55.Nucleo/"
    "Applications/BLE/BLE_p2pServer/Core/Src/app_entry.c"
)
OUTPUT = RUNTIME / "TOUCH_CHOREOGRAPHY_MACHINE_READY.json"

PAGE_SHA256 = (
    "D308CB63D287EFADC6DAC70F5E0DDE1BCA3AD13803B5A93E625BBB8505A7DAAE"
)
CENTER_TAP_SHA256 = (
    "85D7A14658096BC74C1ACBB5B86ABCEBE6BCAD96942878C766E7C2B2FD763DE4"
)
PHASES = ("orient", "anticipate", "accent", "follow", "settle")
ZONES = ("center", "up", "down", "left", "right")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def function_body(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise ValueError(f"unterminated function: {signature}")


def main() -> int:
    source = load(SOURCE)
    cemp = load(CEMP)
    cemp_verify = load(CEMP_VERIFY)
    generation = load(GENERATION)
    generation_verify = load(GENERATION_VERIFY)
    bundle = load(BUNDLE_RECEIPT)
    app = APP_BLE.read_text(encoding="utf-8")
    emote_asset_pack = EMOTE_ASSET_PACK.read_text(encoding="utf-8")
    main_source = MAIN.read_text(encoding="utf-8")
    app_entry = APP_ENTRY.read_text(encoding="utf-8")
    tap_body = function_body(app, "bool Companion_Screen_DailyTapAt(")
    frame_read_body = function_body(
        emote_asset_pack, "bool comp_emote_asset_pack_read_frame("
    )
    touch_idle_body = function_body(
        main_source, "int Companion_TouchWorkPendingForSeqIdle(void)"
    )
    low_power_body = function_body(
        main_source, "static void update_low_power_policy(void)\n{"
    )
    wait_buffer_body = function_body(
        main_source,
        "static void buffer_touch_sample_during_panel_wait(\n"
        "    const comp_ft6336_touch_sample_t *sample,\n"
        "    uint32_t now_ms)\n{",
    )
    wait_buffer_selftest = function_body(
        main_source, "static bool touch_wait_buffer_self_test(void)\n{"
    )
    seq_idle_body = function_body(app_entry, "void UTIL_SEQ_Idle(void)")
    states = {state["id"]: state for state in source["states"]}
    clips = {clip["name"]: clip for clip in cemp["clips"]}

    transition_states = [
        state for state in source["states"]
        if state["kind"] == "tap_transition"
    ]
    transition_durations_match = True
    for zone in ZONES:
        ordered = sorted(
            (state for state in transition_states if state["zone"] == zone),
            key=lambda state: (
                int(state["route_index"]),
                PHASES.index(state["phase"]),
            ),
        )
        clip = clips.get(f"tap.transition.{zone}", {})
        frames = clip.get("frames", [])
        transition_durations_match &= (
            len(frames) == len(ordered)
            and all(
                frame["duration_ms"] == state["dwell_commits"] * 480
                and frame["source"].endswith(state["pbm_file"])
                for frame, state in zip(frames, ordered, strict=True)
            )
        )

    center = states.get("tap_local_calm_center", {})
    checks = {
        "fixed_page_identity": (
            hashlib.sha256(PAGE.read_bytes()).hexdigest().upper()
            == PAGE_SHA256
            and source["source"]["page_sha256"] == PAGE_SHA256
        ),
        "tap_states_are_appended_complete": (
            source["invariants"]["state_count"] == 3091
            and source["invariants"]["unique_frame_count"] == 1390
            and source["invariants"]["pointer_follow_state_count"] == 250
            and len(source["invariants"]["life_families"]) == 10
            and sum(
                state["kind"] == "tap_local"
                for state in source["states"]
            ) == 50
            and len(transition_states) == 45
        ),
        "center_tap_exact_browser_bytes": (
            center.get("browser_frame_sha256") == CENTER_TAP_SHA256
            and center.get("unique_frame_index") == 1055
            and center.get("life_action") == "small_breath"
        ),
        "transition_clips_preserve_browser_dwell": (
            transition_durations_match
            and cemp["source"]["tap_transition_clip_count"] == 5
        ),
        "cemp_roundtrip_exact": (
            cemp_verify["status"] == "PASS_CEMP_EXTERNAL_SOURCE_BOUND"
            and all(cemp_verify["checks"].values())
        ),
        "frame_read_hot_path_does_not_revalidate_whole_catalog": (
            "comp_emote_asset_pack_validate(" not in frame_read_body
            and "frame < pack->catalog->frames" in frame_read_body
            and "frame >= pack->catalog->frames + pack->catalog->frame_count"
            in frame_read_body
            and "frame->data_offset" in frame_read_body
            and "frame->data_size" in frame_read_body
        ),
        "generation_exact_and_bounded": (
            generation_verify["status"]
            == "PASS_UI_ASSET_GENERATION_EQUIVALENT"
            and generation_verify["states_checked"] == 3091
            and generation_verify["strict_1bpp"] is True
            and generation["state_count"] == 3091
            and generation["generation"] == 14
            and generation["resource_id"] == generation_verify["resource_id"]
            and generation["planned_blob_offset"] == 1732608
            and generation["blob_bytes"] == 213732
            and all(
                generation["entries_by_id"][state["id"]]["duration_ms"]
                == state["dwell_commits"] * 480
                for state in transition_states
            )
        ),
        "cuot_targets_generation_14_atomically": (
            bundle["status"] == "MACHINE_READY"
            and bundle["generation"]["expected_active_generation"] == 13
            and bundle["generation"]["resource_id"]
            == generation["resource_id"]
            and bundle["activation"]["commit"] == "inactive_root_last"
            and bundle["activation"]["abort_preserves_active_generation"]
        ),
        "firmware_uses_browser_state_not_attention_alias": (
            "comp_browser_interaction_tap("
            in tap_body
            and "Companion_CompReq775BrowserTapLocalClip("
            in tap_body
            and "Companion_CompReq775BrowserTapTransitionClip("
            in tap_body
            and "browser_result.local_zone"
            in tap_body
            and "browser_event=single_tap_commit immediate=1"
            in tap_body
            and "comp_pet_attention_clip_name(direction)" not in tap_body[
                tap_body.index(
                    "#if COMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK",
                    tap_body.index(
                        "comp_pet_behavior_note_touch("
                    ),
                ):
                tap_body.index(
                    "#else",
                    tap_body.index(
                        "comp_pet_behavior_note_touch("
                    ),
                )
            ]
            and "browser_state=%s family_before=%s target=%s family_after=%s"
            in tap_body
        ),
        "sequencer_cannot_strand_buffered_pointer_lifecycle": (
            "s_touch_irq_count != s_touch_irq_consumed_count"
            in touch_idle_body
            and "s_touch_refresh_capture_active" in touch_idle_body
            and "s_touch_refresh_buffer_count != 0u" in touch_idle_body
            and "s_touch_refresh_latest_contact_valid" in touch_idle_body
            and "s_touch_contact_active" in touch_idle_body
            and "s_touch_gesture.active" in touch_idle_body
            and "s_touch_gesture.tap_pending" in touch_idle_body
            and "Companion_TouchWorkPendingForSeqIdle() != 0"
            in seq_idle_body
            and seq_idle_body.index(
                "Companion_TouchWorkPendingForSeqIdle() != 0"
            )
            < seq_idle_body.index("UTIL_LPM_EnterLowPower()")
        ),
        "awake_ui_keeps_pointer_sampler_running": (
            "Companion_Screen_IsReady() && !s_low_power_idle_pose_visible"
            in low_power_body
            and "awake_touch_polling" in low_power_body
            and "stop_allowed = false;" in low_power_body
            and "awake_touch_poll=%u" in low_power_body
        ),
        "release_bounce_preserves_one_pointer_lifecycle": (
            "#define TOUCH_RELEASE_DEBOUNCE_SAMPLES 2u" in main_source
            and "s_touch_refresh_release_samples == 0u"
            in wait_buffer_body
            and "++s_touch_refresh_release_samples >="
            in wait_buffer_body
            and "TOUCH_RELEASE_DEBOUNCE_SAMPLES" in wait_buffer_body
            and "buffer_touch_sample_during_panel_wait(&idle, 120u);"
            in wait_buffer_selftest
            and (
                "buffer_touch_sample_during_panel_wait("
                "&bounce_contact_latest, 125u);"
            )
            in wait_buffer_selftest
            and "buffer_touch_sample_during_panel_wait(&idle, 145u);"
            in wait_buffer_selftest
            and "s_touch_refresh_buffer_count == 6u"
            in wait_buffer_selftest
            and (
                "comp_touch_gesture_init(&gesture_state, "
                "&s_touch_gesture.config);"
            )
            in wait_buffer_selftest
            and "gesture_event_count == 1u"
            in wait_buffer_selftest
            and "tap_event_count == 1u"
            in wait_buffer_selftest
        ),
        "touch_frame_completion_preserves_browser_clip_tail": (
            "const bool automatic_request =" in app
            and (
                "request.display_flags & "
                "COMP_EPAPER_DISPLAY_FLAG_AUTO_MOTION"
            )
            in app
            and "const bool automatic_cancelled =" in app
            and "automatic_request &&" in app
            and "if (automatic_cancelled)" in app
            and "auto_cancelled=%u" in app
        ),
        "touch_cadence_counts_panel_transaction_without_frame_skip": (
            "s_companion_touch_frame_request_id = request_id;" in app
            and (
                "s_companion_touch_frame_duration_ms = "
                "player_frame.frame.duration_ms;"
            )
            in app
            and (
                "request.request_id == "
                "s_companion_touch_frame_request_id"
            )
            in app
            and "Companion_Display_ScheduleExpressionTick(HAL_GetTick());"
            in app
            and "panel_transaction_started_ms = HAL_GetTick();" in app
            and "transport_credit_ms" in app
            and "visible_dwell_ms - 1u" in app
            and "comp_emote_player_tick_sequential(" in app
            and "cadence_origin=panel_transaction_start" in app
        ),
        "firmware_plays_native_cemp_transition_catalog": (
            "Companion_CompReq775RegisterBrowserTapTransitions" not in app
            and "tap_transition_%s_e%u_%s" not in app
            and "Companion_CompReq775BrowserTapTransitionClip(" in tap_body
            and "Companion_CompReq775BrowserTapLocalClip(" in tap_body
            and "source=cemp_catalog" in app
            and '"cemp_catalog_native"' in app
            and "bool browser_touch_clip_active;" in app
            and "if (!browser_touch_clip_active &&" in app
            and "comp_emote_player_tick_sequential(" in app
        ),
    }
    ready = all(checks.values())
    receipt = {
        "schema": "companion.comp_req_775.touch_resource_contract.v1",
        "status": "MACHINE_READY" if ready else "NO_GO",
        "checks": checks,
        "page_sha256": PAGE_SHA256,
        "center_tap_browser_frame_sha256": CENTER_TAP_SHA256,
        "source_pack_manifest_sha256": hashlib.sha256(
            SOURCE.read_bytes()
        ).hexdigest().upper(),
        "resource_id": generation["resource_id"],
        "bundle_sha256": bundle["bundle"]["sha256"],
        "app_ble_sha256": hashlib.sha256(
            APP_BLE.read_bytes()
        ).hexdigest().upper(),
        "hardware_contact": 0,
    }
    OUTPUT.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
