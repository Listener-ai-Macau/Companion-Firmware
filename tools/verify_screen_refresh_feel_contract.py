#!/usr/bin/env python3
"""Verify the product-level e-paper refresh feel contract for SCR-16."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "docs/validation/companion-screen-refresh-feel-contract.json"

PLAN = ROOT / "docs/companion_screen_project_plan.md"
STYLE_CONTRACT = ROOT / "docs/validation/companion-screen-generated-art-style-contract.md"
GENERATION_RESEARCH = ROOT / "docs/validation/companion-screen-generation-swap-research.md"
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
REFRESH_POLICY_C = ROOT / "app/companion_pendant/epaper/refresh_policy.c"
REFRESH_POLICY_H = ROOT / "app/companion_pendant/epaper/refresh_policy.h"
DISPLAY_QUEUE_C = ROOT / "app/companion_pendant/epaper/display_queue.c"
DISPLAY_QUEUE_H = ROOT / "app/companion_pendant/epaper/display_queue.h"
MAIN_C = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"
APP_BLE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
RESOURCE_POLICY = ROOT / "docs/validation/companion-screen-resource-memory-policy.json"
V9_CEMP = ROOT / "docs/validation/companion-v9-expression-cemp-20260716.json"
V9_BINDING = ROOT / "docs/validation/companion-v9-candidate-resource-binding-20260717.json"
BOUNDARY_WAVEFORM_RESEARCH = ROOT / "docs/validation/companion-screen-menu-boundary-waveform-research.md"
def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def has(text: str, *needles: str) -> bool:
    return all(needle in text for needle in needles)


def build_contract() -> dict[str, Any]:
    plan = read(PLAN)
    style = read(STYLE_CONTRACT)
    generation_research = read(GENERATION_RESEARCH)
    driver = read(DRIVER)
    policy_c = read(REFRESH_POLICY_C)
    policy_h = read(REFRESH_POLICY_H)
    queue_c = read(DISPLAY_QUEUE_C)
    queue_h = read(DISPLAY_QUEUE_H)
    main_c = read(MAIN_C)
    app_ble = read(APP_BLE)
    resource_policy = json.loads(RESOURCE_POLICY.read_text(encoding="utf-8"))
    v9_cemp = json.loads(V9_CEMP.read_text(encoding="utf-8"))
    v9_binding = json.loads(V9_BINDING.read_text(encoding="utf-8"))
    boundary_research = read(BOUNDARY_WAVEFORM_RESEARCH)

    checks = {
        "vendor_ghosting_research_recorded": has(
            plan,
            "Good Display/EPD",
            "局刷和快刷用于交互响应",
            "会累积残影",
            "全屏清残只作为低频维护或恢复动作",
        ),
        "new_old_generation_interleave_rules_recorded": has(
            plan,
            "SCR-17 输入",
            "资源代际切换",
            "CEMP 资源包",
            "按 revision 原子激活",
            "drain/丢弃旧 revision 的待刷帧",
            "不得把旧 procedural 脸、旧菜单 PBM、旧 sheet 裁切或旧 framebuffer 作为过渡",
        )
        and has(
            generation_research,
            "software generation interleaving",
            "CEMP activation is atomic at the revision level",
            "display queue carries the active resource revision",
            "Pervasive Displays",
            "Good Display",
            "Version-based invalidation",
        ),
        "mature_product_generation_triage_recorded": has(
            plan,
            "physical afterimage",
            "stale queued frame",
            "stale asset revision",
            "rescue/procedural fallback leakage",
            "stale_generation_content",
            "P0 产品问题",
            "产品 backlog/release item",
        )
        and has(
            generation_research,
            "content-specific refresh modes",
            "manual/full refresh triggers",
            "firmware waveform improvements",
            "physical afterimage",
            "stale queued frame",
            "stale asset revision",
            "rescue/procedural fallback leakage",
            "stale_generation_content",
            "product backlog item",
        ),
        "scr17_release_ledger_recorded": has(
            plan,
            "release ledger",
            "source art",
            "CEMP revision",
            "CRC",
            "兼容 profile",
            "manifest/外部 Flash 激活",
            "旧队列丢弃计数",
            "首帧 coherent marker",
            "资源 manifest、payload、CRC/签名、active revision、显示队列和首帧提交",
        )
        and has(
            generation_research,
            "Release ledger entry required",
            "Source art identity",
            "Activation evidence",
            "First-frame evidence",
            "`coherent_generation=1`",
            "Panel evidence",
            "Human/visual note",
        ),
        "display_queue_tracks_resource_generation": has(
            queue_h,
            "uint32_t resource_revision",
            "uint32_t active_resource_revision",
            "uint32_t generation_switch_count",
            "uint32_t last_stale_generation_discarded",
            "uint32_t stale_generation_discard_count",
            "comp_epaper_display_queue_set_resource_revision",
        )
        and has(
            queue_c,
            "(*out_request)->resource_revision = queue->active_resource_revision",
            "queue->last_stale_generation_discarded = (uint32_t)discarded",
            "queue->generation_switch_count++",
            "queue->stale_generation_discard_count += (uint32_t)discarded",
            "memset(queue->items, 0, sizeof(queue->items))",
        ),
        "wb55_sets_and_logs_resource_generation": has(
            app_ble,
            "comp_epaper_display_queue_set_resource_revision(",
            "s_companion_screen_asset_mount.pack.revision",
            "queue_generation revision=",
            "coherent_generation=%u",
            "display_result id=%lu kind=%u resource_revision=%lu active_revision=%lu coherent_generation=%u",
        ),
        "menu_entry_discards_all_stale_external_expression_frames": has(
            app_ble,
            "COMP_EPAPER_DISPLAY_REQUEST_EXPRESSION",
            "discarded_expression_frames",
        ) and not has(
            app_ble,
            "COMP_EPAPER_DISPLAY_REQUEST_PET_EXPRESSION",
        ) and "discarded_pet_expression_frames" not in app_ble,
        "screen_interaction_success_logs_are_trace_gated": has(
            app_ble,
            "COMPANION_TOUCH_VERBOSE_TRACE 0",
            "#define SCREEN_INTERACTION_TRACE(...) printf(__VA_ARGS__)",
            "#define SCREEN_INTERACTION_TRACE(...) do { if (0) { printf(__VA_ARGS__); } } while (0)",
            "SCREEN_INTERACTION_TRACE(\"[screen] menu enqueue",
            "SCREEN_INTERACTION_TRACE(\"[screen] display_result",
            "SCREEN_INTERACTION_TRACE(\"[pet-renderer]",
            "SCREEN_INTERACTION_TRACE(\"[pet-attention]",
            "SCREEN_INTERACTION_TRACE(\"[pet-stroke]",
            "SCREEN_INTERACTION_TRACE(\"[pet-emotion]",
        ),
        "coherent_generation_runtime_marker_is_one_shot": has(
            app_ble,
            "static bool s_companion_screen_coherent_generation_marker_logged = false;",
            "s_companion_screen_coherent_generation_marker_logged = false;",
            "if (!s_companion_screen_coherent_generation_marker_logged &&",
            "panel_result == COMP_EPAPER_PANEL_RESULT_OK",
            "printf(\"[screen] coherent_generation=1 resource_revision=",
            "s_companion_screen_coherent_generation_marker_logged = true;",
        ),
        "interactive_uses_differential_waveform": has(
            driver,
            "? 0xFCu",
            'mode = decision == COMP_EPAPER_REFRESH_DECISION_PARTIAL',
            '"differential"',
            "ssd1681_window_from_difference",
        ),
        "maintenance_uses_single_low_flicker_waveform": has(
            driver,
            "? 0xC7u",
            '"maintenance"',
            "COMP_EPAPER_REFRESH_DECISION_FAST",
            "SSD1681_VENDOR_FAST_PROFILE_NAME",
            "ssd1681_prepare_vendor_fast_profile",
            "0xB1u",
            "0x91u",
            "expected_visible_flicker",
            '"single"',
        ),
        "boundary_waveform_research_recorded": has(
            boundary_research,
            "GDEY0154D67-T03",
            "SSD1681",
            "multiple times",
            "once",
            "five consecutive",
            "operations",
            "Implementation Decision",
        ),
        "full_refresh_reserved_for_baseline_or_fault": has(
            policy_c,
            "COMP_EPAPER_REFRESH_REASON_BASELINE_REQUIRED",
            "COMP_EPAPER_REFRESH_REASON_REQUESTED_FULL",
            "policy->baseline_valid = false",
        )
        and has(driver, ": 0xF7u", '"full"')
        and has(
            app_ble,
            "Companion_Screen_MenuRequestClean",
            "Companion_Screen_ShowDailyClean",
            "menu_boundary=enter",
            "menu_boundary=exit",
            "refresh=fast_if_baseline",
            "COMP_EPAPER_REFRESH_MAINTENANCE",
        ),
        "menu_boundaries_request_single_flicker_fast_path": has(
            app_ble,
            "Companion_Screen_MenuRequestClean",
            "Companion_Screen_ShowDailyClean",
            "Companion_Screen_StartExpressionMode",
            "COMP_EPAPER_REFRESH_MAINTENANCE",
            "menu_exit_clean",
        ),
        "ordinary_touch_has_no_delayed_maintenance": not any(
            marker in main_c
            for marker in (
                "TOUCH_SCREEN_MAINTENANCE_QUIET_MS",
                "schedule_touch_screen_maintenance",
                "process_touch_screen_maintenance",
                "s_screen_maintenance_pending",
            )
        ),
        "interactive_cleanup_is_coalesced_at_five_partials": has(
            policy_h,
            "COMP_EPAPER_REFRESH_DEFAULT_PARTIAL_LIMIT 5u",
        ) and has(
            policy_c,
            "requested_mode == COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE",
            "policy->partial_count >= policy->partial_limit",
            "COMP_EPAPER_REFRESH_REASON_PARTIAL_LIMIT",
        ),
        "menu_drag_coalesces_to_latest_frame": has(
            queue_c,
            "replace_pending_menu",
            "queue->items[latest].request_kind ==",
            "COMP_EPAPER_DISPLAY_REQUEST_MENU",
            "memset(request, 0, sizeof(*request))",
            "request->resource_revision = queue->active_resource_revision",
        ),
        "interactive_modes_are_portable": has(
            queue_h,
            "COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE",
            "COMP_EPAPER_REFRESH_MAINTENANCE",
            "uint16_t dirty_width",
            "uint16_t dirty_height",
        ),
        "identical_frame_suppression": has(
            driver,
            "if (partial && !window.changed)",
            "differential_skip identical_frame",
            "transferred_bytes = 0u",
        ),
        "policy_limits_are_bounded": has(
            policy_h,
            "COMP_EPAPER_REFRESH_DEFAULT_PARTIAL_LIMIT 5u",
        )
        and has(policy_c, "COMP_EPAPER_REFRESH_REASON_MAINTENANCE_BOUNDARY"),
        "art_and_refresh_axes_separate": has(
            style,
            "Art changes and refresh changes are separate axes",
            "the panel target chooses how often to refresh it",
        ),
        "current_v9_candidate_is_explicitly_inactive": (
            v9_cemp.get("status") == "PASS_MACHINE_ONLY_CEMP_NOT_ACTIVATED"
            and v9_cemp.get("runtime_resource_activated") is False
            and v9_binding.get("status") == "PASS_MACHINE_ONLY_INACTIVE"
            and v9_binding.get("candidate_pack", {}).get("revision") == 90
            and v9_binding.get("candidate_pack", {}).get("runtime_resource_activated") is False
            and resource_policy.get("current_goal_visual_boundary", {}).get("candidate_pack", {}).get("revision") == 90
            and resource_policy.get("current_goal_visual_boundary", {}).get("candidate_pack", {}).get("status")
            == "machine_proved_not_runtime_activated"
        ),
    }

    return {
        "schema_id": "companion.screen.refresh_feel_contract.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "scope": "SCR-16 screen feel and ghosting control; the v9 candidate remains machine-only and inactive until separate owner, integration and physical gates pass",
        "candidate": {
            "name": "companion-v9-expression-candidate-200x200",
            "revision": v9_binding.get("candidate_pack", {}).get("revision"),
            "pack_sha256": v9_cemp.get("pack_sha256"),
            "runtime_resource_activated": v9_binding.get("candidate_pack", {}).get("runtime_resource_activated"),
        },
        "sources": {
            "project_plan": rel(PLAN),
            "style_contract": rel(STYLE_CONTRACT),
            "generation_swap_research": rel(GENERATION_RESEARCH),
            "driver": rel(DRIVER),
            "refresh_policy": rel(REFRESH_POLICY_C),
            "display_queue": rel(DISPLAY_QUEUE_C),
            "main": rel(MAIN_C),
            "app_ble": rel(APP_BLE),
            "resource_policy": rel(RESOURCE_POLICY),
            "v9_cemp": rel(V9_CEMP),
            "v9_binding": rel(V9_BINDING),
            "boundary_waveform_research": rel(BOUNDARY_WAVEFORM_RESEARCH),
        },
        "product_rules": {
            "interactive": "Use differential 0xFC dirty-window refresh; coalesce queued menu drag frames to the latest request.",
            "interaction_serial": "Production reuses the touch trace switch to remove successful screen enqueue, frame, pet-attention, and stroke UART serialization; failures and one reset-bounded coherent-generation marker remain visible for runtime evidence.",
            "maintenance": "Ordinary touch never schedules a delayed cleanup. Five completed differential interactions are allowed; the sixth selects one Good Display Mode 1 / 0xC7 cleanup. Explicit menu enter/exit boundaries each request one Mode-1 cleanup.",
            "full_refresh": "Use 0xF7 only for an unknown baseline or a transport/fault recovery. A normal menu boundary requests the vendor Mode 1 / 0xC7 fast path when the baseline is valid, with full as the policy fallback only when that baseline is unknown.",
            "menu_boundary": "Enter and exit request one vendor-profiled Mode 1 / 0xC7 fast waveform when the panel baseline is valid. The target logs the profile, activation count, and expected visible phase model; physical one-flicker confirmation remains a focused hardware gate.",
            "ghosting": "Partial/fast refresh can accumulate ghosting; tune refresh profile/cadence rather than blending old art.",
            "generation_swap": "Treat visual ghosting and old/new resource interleaving as separate failures: atomically activate one CEMP revision, drain stale queued frames, then refresh/maintain the panel baseline.",
            "generation_triage": "Classify visible old content as physical afterimage, stale queued frame, stale asset revision, or rescue/procedural fallback leakage; only physical afterimage belongs to refresh-profile tuning.",
            "generation_backlog": "SCR-17 remains a named product backlog/release item; recognizable old faces, menus, prompt crops, fallback renderers, or framebuffer content are stale_generation_content until proven physical afterimage only. The current v9 candidate is not activated by this static contract.",
            "portability": "Scene/player use portable refresh intents; WB55/WBA panel targets choose waveform details.",
        },
        "checks": checks,
        "validation_commands": [
            "python .\\tools\\verify_screen_refresh_feel_contract.py",
            "python .\\tools\\verify_display_queue_generation_hygiene.py",
            "python .\\tools\\verify_epaper_refresh_policy.py",
            "python .\\tools\\verify_companion_runtime_visual_boundary.py",
            "pwsh .\\tools\\test_companion_v9_expression_render_pipeline.ps1",
        ],
    }


def verify(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("schema_id") != "companion.screen.refresh_feel_contract.v1":
        errors.append("unexpected schema_id")
    checks = contract.get("checks", {})
    for key, value in checks.items():
        if value is not True:
            errors.append(f"checks.{key} is not true")
    candidate = contract.get("candidate", {})
    if not isinstance(candidate.get("revision"), int) or candidate.get("revision", 0) < 1:
        errors.append("candidate revision must be a positive integer")
    if candidate.get("name") != "companion-v9-expression-candidate-200x200":
        errors.append("candidate must be the locked v9 expression pack")
    if len(str(candidate.get("pack_sha256"))) != 64:
        errors.append("candidate must record the v9 CEMP SHA-256")
    if candidate.get("runtime_resource_activated") is not False:
        errors.append("candidate must remain runtime inactive")
    return errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", type=pathlib.Path, default=DEFAULT_JSON)
    args = parser.parse_args(argv)
    output = args.json if args.json.is_absolute() else ROOT / args.json

    contract = build_contract()
    errors = verify(contract)
    rendered = json.dumps(contract, indent=2, ensure_ascii=False, sort_keys=True) + "\n"

    if args.write and not errors:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    elif not args.write:
        if not output.exists():
            errors.append(f"missing {rel(output)}")
        elif output.read_text(encoding="utf-8") != rendered:
            errors.append(f"stale {rel(output)}; rerun with --write")

    if errors:
        print("FAIL: screen refresh feel contract failed", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: screen refresh feel contract verified -> {rel(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
