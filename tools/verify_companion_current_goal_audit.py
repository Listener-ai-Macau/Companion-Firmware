#!/usr/bin/env python3
"""Keep the active Companion Goal boundary auditable without hardware access."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "docs/validation/companion-current-goal-audit-20260717.json"
DEFAULT_MD = ROOT / "docs/validation/companion-current-goal-audit-20260717.md"

ARTIFACTS = {
    "historical": ROOT / "docs/validation/companion-historical-branch-audit-20260717.json",
    "low_power": ROOT / "docs/validation/companion-low-power-requirements.json",
    "wb55_build_receipt": ROOT / "docs/validation/companion-wb55-current-build-receipt-20260717.json",
    "runtime_visual_boundary": ROOT / "docs/validation/companion-runtime-visual-boundary-20260717.json",
    "external_expression_system": ROOT / "docs/validation/companion-screen-pet-expression-system.json",
    "refresh_feel": ROOT / "docs/validation/companion-screen-refresh-feel-contract.json",
    "queue_generation_hygiene": ROOT / "docs/validation/companion-screen-display-queue-generation-hygiene.json",
    "resource_memory_policy": ROOT / "docs/validation/companion-screen-resource-memory-policy.json",
    "wba_m33_compile": ROOT / "docs/validation/companion-screen-wba-adapter-m33-compile.json",
    "wba_spi_nor": ROOT / "docs/validation/companion-wba-spi-nor-adapter.json",
    "wba_port_contract": ROOT / "docs/validation/companion-screen-wba-port-contract.json",
    "wba_v9_callback_replay": ROOT / "docs/validation/companion-wba-v9-cemp-callback-replay-20260717.json",
    "v9_baseline": ROOT / "docs/art/iterations/companion-pet-expression-v9/baseline-lock.json",
    "v9_cemp": ROOT / "docs/validation/companion-v9-expression-cemp-20260716.json",
    "v9_coverage": ROOT / "docs/validation/companion-v9-scene-coverage-20260716.json",
    "v9_binding": ROOT / "docs/validation/companion-v9-candidate-resource-binding-20260717.json",
    "visual_reference_ledger": ROOT / "docs/validation/companion-visual-reference-evidence.json",
    "v9_safe_area": ROOT / "docs/validation/companion-v9-frame-safe-area-20260717.json",
    "special_crop_preflight": ROOT / "docs/validation/companion-pet-special-state-crop-preflight-20260717.json",
    "ssd1681_frame_mapping": ROOT / "docs/validation/companion-ssd1681-frame-mapping-20260717.json",
    "menu_function_receipt": ROOT / "docs/validation/companion-menu-v6-function-receipt-20260717.json",
    "menu_source": ROOT / "docs/validation/companion-menu-v6-source-review-20260717.json",
    "menu_localization": ROOT / "docs/validation/companion-menu-v6-localization-preview-20260717.json",
    "v9_home_storyboard": ROOT / "docs/validation/companion-v9-home-storyboard-review-20260717.json",
    "menu_v7_screen_family": ROOT / "docs/validation/companion-menu-v7-screen-family-preview-20260717.json",
    "special_one_page_review": ROOT / "docs/validation/companion-pet-special-state-one-page-review-20260717.json",
    "special_system": ROOT / "docs/validation/companion-pet-special-system-source-review-20260717.json",
    "special_journey": ROOT / "docs/validation/companion-pet-special-journey-source-review-20260717.json",
    "special_mapping": ROOT / "docs/validation/companion-pending-special-source-mapping-20260717.json",
    "visual_readiness": ROOT / "docs/validation/companion-ui-visual-acceptance-readiness-20260717.json",
    "goal_acceptance_readiness": ROOT / "docs/validation/companion-goal-acceptance-readiness-20260717.json",
    "g2_group_triage": ROOT / "docs/validation/companion-g2-menu-group-review-triage-20260717.json",
    "g2_home_context_triage": ROOT / "docs/validation/companion-g2-home-artifact1-triage-20260717.json",
    "wba_boundary": ROOT / "docs/validation/companion-v9-wba-visual-boundary-20260717.json",
    "waveform_freeze": ROOT / "docs/companion_ssd1681_vendor_waveform_freeze.md",
}

V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
MENU_SHA256 = "07D791A898FABE6E558686F6A4B4CC86094541C6B5116D6E0A3D263930DAA868"
MENU_V7_SHA256 = "D2D36B1CD51D153758E64C4DCBE0E0B7192F2E3F895D62CD3C432DDFA8476C37"
SYSTEM_SHA256 = "AF9ADFD49C47C89DF674726D7201CC49C61ED636306013697822BB42FB1A9C82"
JOURNEY_SHA256 = "95CC749134F169E73A2E2A99FA2B6F08AABDFE78D218677C347D2D687EA4B17F"


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(name: str) -> dict[str, Any]:
    path = ARTIFACTS[name]
    return json.loads(path.read_text(encoding="utf-8"))


def check(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def evidence(name: str, status: str, detail: str) -> dict[str, str]:
    return {"path": rel(ARTIFACTS[name]), "status": status, "detail": detail}


def build_audit() -> dict[str, Any]:
    errors: list[str] = []
    historical = load_json("historical")
    low_power = load_json("low_power")
    wb55_build_receipt = load_json("wb55_build_receipt")
    runtime_visual_boundary = load_json("runtime_visual_boundary")
    external_expression_system = load_json("external_expression_system")
    refresh_feel = load_json("refresh_feel")
    queue_generation_hygiene = load_json("queue_generation_hygiene")
    resource_memory_policy = load_json("resource_memory_policy")
    wba_m33_compile = load_json("wba_m33_compile")
    wba_spi_nor = load_json("wba_spi_nor")
    wba_port_contract = load_json("wba_port_contract")
    wba_v9_callback_replay = load_json("wba_v9_callback_replay")
    baseline = load_json("v9_baseline")
    cemp = load_json("v9_cemp")
    coverage = load_json("v9_coverage")
    binding = load_json("v9_binding")
    visual_reference_ledger = load_json("visual_reference_ledger")
    safe_area = load_json("v9_safe_area")
    special_crop_preflight = load_json("special_crop_preflight")
    ssd1681_frame_mapping = load_json("ssd1681_frame_mapping")
    menu_function_receipt = load_json("menu_function_receipt")
    menu_source = load_json("menu_source")
    menu_localization = load_json("menu_localization")
    v9_home_storyboard = load_json("v9_home_storyboard")
    menu_v7_screen_family = load_json("menu_v7_screen_family")
    special_one_page_review = load_json("special_one_page_review")
    special_system = load_json("special_system")
    special_journey = load_json("special_journey")
    special_mapping = load_json("special_mapping")
    visual_readiness = load_json("visual_readiness")
    goal_acceptance_readiness = load_json("goal_acceptance_readiness")
    g2_group_triage = load_json("g2_group_triage")
    g2_home_context_triage = load_json("g2_home_context_triage")
    wba_boundary = load_json("wba_boundary")
    waveform_freeze = ARTIFACTS["waveform_freeze"].read_text(encoding="utf-8")
    waveform_freeze_normalized = waveform_freeze.lower()

    check(errors, historical.get("status") == "PASS_PRESERVED_AND_CLASSIFIED", "historical branches are not classified")
    protections = historical.get("current_main_protections", {})
    for key in (
        "double_tap_only_recording_menu_policy",
        "first_tap_blocks_stop_until_double_tap_decision",
        "rejected_renderable_art_stays_retired",
        "three_minute_idle_default",
    ):
        check(errors, protections.get(key) is True, f"historical protection missing: {key}")

    check(errors, low_power.get("status") == "PASS", "low-power static contract is not PASS")
    check(errors, low_power.get("target") == "final product-board LP-01 standby average <= 1 mA over >= 60 s", "low-power target drifted")
    check(errors, "3-minute" in str(low_power.get("low_power_visual")), "three-minute sleepy policy drifted")

    check(errors, wb55_build_receipt.get("status") == "PASS_CURRENT_SOURCE_BUILD_NO_HARDWARE", "current WB55 build receipt is not PASS")
    build_commit = wb55_build_receipt.get("source_commit", "")
    check(errors, isinstance(build_commit, str) and len(build_commit) == 40, "current WB55 build receipt has no full source commit")
    for name in ("dry_run_default", "ssd1681_real_panel", "screen_asset_provision"):
        variant = wb55_build_receipt.get("variants", {}).get(name, {})
        check(errors, variant.get("returncode") == 0, f"current WB55 build variant failed: {name}")
        check(errors, isinstance(variant.get("size", {}).get("dec"), int), f"current WB55 build variant has no size: {name}")
    check(errors, runtime_visual_boundary.get("status") == "PASS_CURRENT_SOURCE_NO_PROCEDURAL_VISUAL_FALLBACK", "runtime visual boundary is not PASS")
    runtime_commit = runtime_visual_boundary.get("source_commit", "")
    check(errors, isinstance(runtime_commit, str) and len(runtime_commit) == 40, "runtime visual boundary has no full source commit")
    runtime_policy = runtime_visual_boundary.get("runtime_policy", {})
    check(errors, runtime_policy.get("active_expression_maintenance") == "external CEMP frame replay only", "runtime expression maintenance drifted from external CEMP")
    check(errors, runtime_policy.get("menu_visual_base") == "external CEMP base required; no complete code-rendered fallback", "runtime menu visual base drifted from external CEMP")
    check(errors, runtime_policy.get("unavailable_visual_source") == "return transport error; do not draw a procedural or test substitute", "runtime visual fallback policy drifted")
    check(errors, runtime_policy.get("retired_procedural_face_linked") is False, "retired procedural face is linked into runtime")
    check(errors, runtime_visual_boundary.get("elf", {}).get("forbidden_symbol_matches") == 0, "runtime ELF contains a retired visual symbol")
    for key in ("firmware_flashed", "panel_command", "camera_or_human_visual_pass"):
        check(errors, runtime_visual_boundary.get("hardware_boundary", {}).get(key) is False, f"runtime visual-boundary hardware claim drifted: {key}")
    check(errors, external_expression_system.get("schema_id") == "companion.screen.external_expression_system.v2", "external expression system schema drifted")
    check(errors, external_expression_system.get("status") == "PASS", "external expression system is not PASS")
    visual_baseline = external_expression_system.get("visual_baseline", {})
    check(errors, visual_baseline.get("iteration") == "companion-pet-expression-v9" and visual_baseline.get("source_sha256") == V9_SHA256, "external expression system v9 baseline drifted")
    check(errors, visual_baseline.get("runtime_resource_activated") is False, "external expression system permits v9 runtime activation")
    check(errors, external_expression_system.get("runtime_guard", {}).get("expression_maintenance") == "replay the last external CEMP frame only", "external expression maintenance boundary drifted")
    check(errors, refresh_feel.get("status") == "PASS", "screen refresh feel contract is not PASS")
    refresh_candidate = refresh_feel.get("candidate", {})
    check(errors, refresh_candidate.get("name") == "companion-v9-expression-candidate-200x200" and refresh_candidate.get("revision") == 90, "screen refresh candidate drifted from v9")
    check(errors, refresh_candidate.get("runtime_resource_activated") is False, "screen refresh contract permits runtime activation")
    check(errors, all(value is True for value in refresh_feel.get("checks", {}).values()), "screen refresh feel contract contains a failed check")
    check(errors, queue_generation_hygiene.get("status") == "PASS", "display queue generation hygiene is not PASS")
    queue_scenario = queue_generation_hygiene.get("scenario", {})
    check(errors, queue_scenario.get("before_switch", {}).get("pending") == 3, "queue generation scenario lost its pending-frame precondition")
    check(errors, queue_scenario.get("after_switch", {}).get("pending") == 0 and queue_scenario.get("after_switch", {}).get("last_stale_discarded") == 3, "queue generation scenario no longer discards stale frames")
    check(errors, queue_scenario.get("first_current_request", {}).get("resource_revision") == 51, "queue generation scenario no longer starts with a coherent current frame")
    resource_goal_boundary = resource_memory_policy.get("current_goal_visual_boundary", {})
    resource_v9_candidate = resource_goal_boundary.get("candidate_pack", {})
    check(errors, resource_memory_policy.get("status") == "PASS", "resource memory policy is not PASS")
    check(errors, resource_goal_boundary.get("active_inner_face_source") == "companion-pet-expression-v9", "resource policy current visual source drifted")
    check(errors, resource_goal_boundary.get("active_inner_face_sha256") == V9_SHA256, "resource policy v9 source hash drifted")
    check(errors, resource_v9_candidate.get("name") == "companion-v9-expression-candidate-200x200" and resource_v9_candidate.get("revision") == 90 and resource_v9_candidate.get("clips") == 13 and resource_v9_candidate.get("frames") == 39, "resource policy v9 candidate geometry drifted")
    check(errors, resource_v9_candidate.get("status") == "machine_proved_not_runtime_activated", "resource policy permits v9 runtime activation")
    check(errors, "prohibited" in str(resource_goal_boundary.get("legacy_r53", "")), "resource policy permits r53 as a current visual source")
    check(errors, "external CEMP base only" in str(resource_goal_boundary.get("product_runtime", "")), "resource policy permits an internal visual fallback")
    check(errors, wba_m33_compile.get("status") == "PASS_STATIC_M33_COMPILE_CONTRACT", "WBA Cortex-M33 adapter compile is not PASS")
    wba_claims = wba_m33_compile.get("claims", {})
    check(errors, wba_claims.get("cube_wba_project_claimed") is False and wba_claims.get("wba_hardware_parity_claimed") is False, "WBA compile evidence overclaims target parity")
    check(errors, wba_spi_nor.get("status") == "PASS_NATIVE_BEHAVIOR_AND_PORTABLE_CONTRACT", "WBA SPI-NOR contract is not PASS")
    wba_targets = wba_spi_nor.get("targets", {})
    check(errors, wba_targets.get("transport") == "spi_nor_1_1_1" and wba_targets.get("hardware_parity_claimed") is False, "WBA SPI-NOR transport boundary drifted")
    check(errors, wba_port_contract.get("status") == "PASS", "WBA port contract is not PASS")
    wba_port_goal = wba_port_contract.get("current_goal_visual_boundary", {})
    check(errors, wba_port_goal.get("active_inner_face_source") == "companion-pet-expression-v9" and wba_port_goal.get("active_inner_face_sha256") == V9_SHA256, "WBA port contract v9 baseline drifted")
    check(errors, wba_port_goal.get("runtime_resource_activation_allowed") is False and wba_port_goal.get("real_wba_panel_parity_claimed") is False, "WBA port contract permits activation or parity claim")
    check(errors, "external CEMP" in str(wba_port_goal.get("visual_runtime", "")) and "ordinary 1-1-1 SPI NOR" in str(wba_port_goal.get("visual_runtime", "")), "WBA port contract resource boundary drifted")
    check(errors, wba_v9_callback_replay.get("status") == "PASS_CURRENT_SOURCE_MACHINE_ONLY_CALLBACK_REPLAY", "WBA v9 callback replay is not PASS")
    wba_v9_candidate = wba_v9_callback_replay.get("candidate", {})
    check(errors, wba_v9_candidate.get("name") == "companion-v9-expression-candidate-200x200", "WBA v9 callback replay candidate name drifted")
    check(errors, wba_v9_candidate.get("revision") == 90 and wba_v9_candidate.get("clips") == 13 and wba_v9_candidate.get("frames") == 39, "WBA v9 callback replay candidate geometry drifted")
    check(errors, wba_v9_candidate.get("runtime_resource_activated") is False, "WBA v9 callback replay permits runtime activation")
    check(errors, wba_v9_callback_replay.get("targets") == ["WBA55", "WBA65"], "WBA v9 callback replay target set drifted")
    check(errors, wba_v9_callback_replay.get("host_test", {}).get("returncode") == 0, "WBA v9 callback replay host test failed")
    for key in ("real_wba_board", "external_flash_provisioned", "firmware_flashed", "panel_command", "owner_visual_pass", "runtime_resource_activation"):
        check(errors, wba_v9_callback_replay.get("boundary", {}).get(key) is False, f"WBA v9 callback replay boundary drifted: {key}")

    accepted_source = baseline.get("accepted_source", {})
    check(errors, baseline.get("status") == "OWNER_APPROVED_SOURCE_LOCKED_MACHINE_RENDER_AUTHORIZED", "v9 baseline is not owner locked")
    check(errors, accepted_source.get("sha256") == V9_SHA256, "v9 source hash drifted")
    check(errors, baseline.get("machine_candidate_scope", {}).get("forbidden") is not None, "v9 machine-only boundary missing")

    check(errors, cemp.get("status") == "PASS_MACHINE_ONLY_CEMP_NOT_ACTIVATED", "v9 CEMP evidence is not machine-only PASS")
    check(errors, cemp.get("frame_count") == 39 and cemp.get("clip_count") == 13, "v9 CEMP frame coverage drifted")
    for key in ("runtime_resource_activated", "external_flash_provisioned", "firmware_flashed", "physical_or_owner_visual_pass"):
        check(errors, cemp.get(key) is False, f"v9 CEMP boundary drifted: {key}")

    check(errors, coverage.get("status") == "PASS_MACHINE_ONLY_NO_LEGACY_FALLBACK", "v9 no-fallback coverage is not PASS")
    check(errors, coverage.get("portable_resource_family_count") == 40, "scene family count drifted")
    check(errors, coverage.get("candidate_mapping_count") == 18 and coverage.get("pending_no_fallback_count") == 22, "scene mapping boundary drifted")
    check(errors, binding.get("status") == "PASS_MACHINE_ONLY_INACTIVE", "v9 selector is not inactive machine-only PASS")
    check(errors, binding.get("candidate_pack", {}).get("runtime_resource_activated") is False, "v9 selector permits runtime activation")
    check(errors, visual_reference_ledger.get("status") == "PASS_LEDGER_INTEGRITY", "visual iteration ledger audit is not PASS")
    check(errors, visual_reference_ledger.get("ledger_count") == 4, "visual iteration ledger count drifted")
    check(errors, visual_reference_ledger.get("features") == ["companion-four-root-menu", "companion-menu-screen-family", "companion-pet-expression", "companion-pet-special-states"], "visual iteration ledger coverage drifted")
    check(errors, safe_area.get("status") == "PASS_MACHINE_SAFE_AREA_PHYSICAL_REVIEW_PENDING", "v9 safe-area report is not machine-only PASS")
    check(errors, safe_area.get("frame_count") == 39, "v9 safe-area report does not cover 39 frames")
    check(errors, safe_area.get("frame_profile", {}).get("minimum_edge_clearance_px") == 4, "v9 safe-area margin drifted")
    check(errors, safe_area.get("runtime_resource_activated") is False, "v9 safe-area report permits runtime activation")
    check(errors, all(frame.get("minimum_clearance_px", 0) >= 4 for frame in safe_area.get("frames", [])), "v9 frame ink reaches the protected edge margin")
    check(errors, ssd1681_frame_mapping.get("status") == "PASS_MACHINE_EXHAUSTIVE_FRAME_MAPPING_PHYSICAL_REVIEW_PENDING", "SSD1681 transform/window mapping is not machine-only PASS")
    geometry = ssd1681_frame_mapping.get("geometry", {})
    check(errors, geometry == {"width": 200, "height": 200, "bytes_per_row": 25}, "SSD1681 transform geometry drifted")
    configurations = ssd1681_frame_mapping.get("supported_build_configurations", [])
    check(errors, len(configurations) == 4, "SSD1681 mapping must cover all four supported orientation configurations")
    for configuration in configurations:
        check(errors, configuration.get("logical_pixels") == 40000, "SSD1681 mapping no longer covers all logical pixels")
        check(errors, configuration.get("framebuffer_unique_pixels") == 40000, "SSD1681 frame transform is no longer one-to-one")
        check(errors, configuration.get("controller_unique_bits") == 40000, "SSD1681 controller map is no longer one-to-one")
    product_orientation = ssd1681_frame_mapping.get("product_build_orientation", {})
    check(errors, product_orientation.get("rotation_degrees") == 180 and product_orientation.get("mirror_x") == 1, "WB55 product orientation mapping drifted")
    mapped_v9 = ssd1681_frame_mapping.get("v9_source", {})
    check(errors, mapped_v9.get("frame_count") == 39 and mapped_v9.get("minimum_mapped_edge_clearance_px") == 4, "SSD1681 mapped v9 frame safety drifted")
    for key in ("external_flash_provisioned", "firmware_flashed", "panel_command", "camera_or_human_visual_pass", "physical_panel_viewport_proved"):
        check(errors, ssd1681_frame_mapping.get("hardware_boundary", {}).get(key) is False, f"SSD1681 mapping overclaims hardware: {key}")

    check(errors, menu_function_receipt.get("status") == "PASS_CURRENT_SOURCE_MENU_FUNCTION_PENDING_OWNER_VISUAL", "four-root menu function receipt is not PASS")
    menu_commit = menu_function_receipt.get("source_commit", "")
    check(errors, isinstance(menu_commit, str) and len(menu_commit) == 40, "four-root menu receipt has no full source commit")
    menu_contract = menu_function_receipt.get("function_contract", {})
    check(errors, menu_contract.get("roots") == ["Voice", "Device", "Connection", "Preferences"], "four-root menu order drifted")
    check(errors, menu_contract.get("language_support") == ["en", "zh_cn"], "four-root menu language support drifted")
    visual_source = menu_function_receipt.get("visual_source", {})
    check(errors, visual_source.get("source_sha256") == MENU_SHA256, "historical four-root menu receipt hash drifted")
    check(errors, visual_source.get("runtime_activation") is False, "historical four-root menu receipt must remain non-activated")
    for name in ("contract", "action_journey", "navigation", "target_bridge", "view_model"):
        check(errors, menu_function_receipt.get("host_tests", {}).get(name, {}).get("returncode") == 0, f"four-root menu host test failed: {name}")

    for name, data, expected_sha in (
        ("special_system", special_system, SYSTEM_SHA256),
        ("special_journey", special_journey, JOURNEY_SHA256),
    ):
        check(errors, data.get("status") == "PASS_MACHINE_PREVIEW_PENDING_OWNER", f"{name} preview status drifted")
        source_sha = json.dumps(data, sort_keys=True)
        check(errors, expected_sha in source_sha, f"{name} source hash missing")

    check(errors, special_crop_preflight.get("status") == "PASS_MACHINE_SAFE_CROP_PREVIEW_NOT_IMPORTABLE", "special-state crop preflight is not PASS")
    special_preflight_sources = {item.get("id"): item for item in special_crop_preflight.get("sources", [])}
    for identifier, expected_sha in (("special-system-v1", SYSTEM_SHA256), ("special-journey-v1", JOURNEY_SHA256)):
        preflight = special_preflight_sources.get(identifier, {})
        check(errors, preflight.get("source_sha256") == expected_sha, f"{identifier} preflight source hash drifted")
        frames = preflight.get("frames", [])
        check(errors, len(frames) == 12, f"{identifier} preflight frame count drifted")
        for frame in frames:
            check(errors, frame.get("edge_ink_pixels") == 0, f"{identifier} preflight has edge ink")
            check(errors, frame.get("minimum_clearance_px", 0) >= 4, f"{identifier} preflight clearance is below 4 px")
    preflight_boundary = special_crop_preflight.get("runtime_boundary", {})
    for key in ("pbm_imported", "cemp_packed", "external_flash_provisioned", "firmware_flashed", "ota_behavior_changed", "owner_visual_pass"):
        check(errors, preflight_boundary.get(key) is False, f"special crop preflight activation boundary drifted: {key}")

    check(errors, special_mapping.get("status") == "PASS_EXACT_PENDING_SOURCE_MAPPING_NO_RUNTIME", "special scene mapping is not pending/no-runtime PASS")
    check(errors, special_mapping.get("mapped_family_count") == 22 and special_mapping.get("pending_family_count") == 22, "special scene mapping count drifted")
    mapping_boundary = special_mapping.get("runtime_boundary", {})
    for key in ("cemp_packed", "external_flash_provisioned", "firmware_flashed", "owner_visual_pass", "pbm_imported"):
        check(errors, mapping_boundary.get(key) is False, f"special scene activation boundary drifted: {key}")

    check(errors, v9_home_storyboard.get("status") == "PASS_MACHINE_ONE_PAGE_PER_KEYFRAME_PENDING_OWNER" and len(v9_home_storyboard.get("states", [])) == 13, "v9 home storyboard is not machine-ready")
    check(errors, menu_v7_screen_family.get("status") == "PASS_MACHINE_SCREEN_FAMILY_PREVIEW_PENDING_OWNER" and menu_v7_screen_family.get("source", {}).get("sha256") == MENU_V7_SHA256, "v7.3 menu family is not machine-ready")
    check(errors, special_one_page_review.get("status") == "PASS_MACHINE_ONE_PAGE_PER_SPECIAL_STATE_PENDING_OWNER", "special-state one-page review is not machine-ready")
    check(errors, visual_readiness.get("status") == "PASS_READY_FOR_SEQUENTIAL_OWNER_REVIEW", "visual review readiness is not PASS")
    readiness_items = visual_readiness.get("items", [])
    expected_review_items = {
        "home-v9-daily-storyboard": (V9_SHA256, 39),
        "menu-v7-screen-family": (MENU_V7_SHA256, 15),
        "special-system-v1": (SYSTEM_SHA256, 12),
        "special-journey-v1": (JOURNEY_SHA256, 12),
    }
    check(errors, len(readiness_items) == 4 and {item.get("id") for item in readiness_items} == set(expected_review_items), "visual review must retain exactly four sequential source families")
    for item in readiness_items:
        prompt = item.get("operator_prompt", {})
        check(errors, all(prompt.get(key) for key in ("target", "operator_action", "success_signal", "failure_rule", "continue_condition", "recovery_condition", "record_fields")), f"{item.get('id')} lacks detailed operator-prompt fields")
        check(errors, isinstance(prompt.get("success_signal"), list) and len(prompt.get("success_signal", [])) >= 2, f"{item.get('id')} lacks multiple success signals")
        artifact_review = item.get("artifact_review", {})
        images = artifact_review.get("images", [])
        check(errors, artifact_review.get("mode") == "original_image_one_at_a_time", f"{item.get('id')} lost original-image review mode")
        expected_sha, expected_count = expected_review_items.get(item.get("id"), (None, 0))
        check(errors, item.get("source_sha256") == expected_sha, f"{item.get('id')} source hash drifted")
        check(errors, len(images) == expected_count and [image.get("index") for image in images] == list(range(1, expected_count + 1)), f"{item.get('id')} original-image sequence drifted")
    check(errors, goal_acceptance_readiness.get("status") == "PASS_ACCEPTANCE_CONTRACT_READY_OWNER_AND_HARDWARE_GATED", "detailed Goal acceptance readiness is not PASS")
    check(errors, goal_acceptance_readiness.get("machine_preflight_opens_operator_prompt") is False, "detailed Goal machine preflight must not open a popup")
    check(errors, goal_acceptance_readiness.get("physical_acceptance", {}).get("lower_edge_truncation") == "must be checked during G5 before any visual pass", "lower-edge truncation gate is missing")
    check(errors, g2_group_triage.get("status") == "OPEN_REVIEW_FLOW_REWORK_REQUIRED", "G2 original-image review rework is not open")
    check(errors, g2_group_triage.get("requirement") == "COMP-REQ-079", "G2 original-image review rework lost its requirement")
    check(errors, g2_group_triage.get("resolution", {}).get("group_selection_applied") is False, "G2 grouped visual selection was incorrectly applied")
    check(errors, g2_home_context_triage.get("status") == "NOT_APPLIED_OWNER_CONTEXT_MISMATCH", "G2 home observation must remain unapplied for context mismatch")
    check(errors, g2_home_context_triage.get("requirement") == "COMP-REQ-083" and g2_home_context_triage.get("decision", {}).get("selection_applied") is False, "G2 home context triage drifted")

    check(errors, wba_boundary.get("status") == "PASS_V9_WBA_VISUAL_BOUNDARY_PENDING_OWNER", "WBA visual boundary is not PASS")
    wba_resource = wba_boundary.get("wba_resource_boundary", {})
    check(errors, wba_resource.get("runtime_activation_allowed") is False, "WBA resource activation is enabled")
    check(errors, wba_resource.get("storage") == "external CEMP through callback-only external NOR adapter", "WBA external resource boundary drifted")
    check(errors, wba_resource.get("transport") == "ordinary 1-1-1 SPI NOR", "WBA SPI-NOR boundary drifted")

    for token in ("frozen", "cwf1", "gdey0154d67-t03", "do not use generic", "no panel command"):
        check(errors, token in waveform_freeze_normalized, f"vendor waveform freeze document missing: {token}")

    requirements = [
        {
            "id": "historical_behavior_protection",
            "status": "proved_machine",
            "requirement": "Historical branches remain protected and only their classified double-tap, first-tap Stop blocker, three-minute idle and external-resource evidence are current behavior inputs.",
            "evidence": [evidence("historical", str(historical.get("status")), "No bulk merge; protected branch tips and useful behavior classification are verified.")],
        },
        {
            "id": "touch_low_power_policy",
            "status": "proved_machine_hardware_current_pending",
            "requirement": "Daily double tap is the only manual recording start/stop; first tap blocks Stop, and the visible sleepy transition defaults to three minutes.",
            "evidence": [evidence("low_power", str(low_power.get("status")), "HAL-free policy passes; Stop wake and <=1 mA physical measurement remain hardware gates.")],
        },
        {
            "id": "current_wb55_build_and_wba_adapter",
            "status": "proved_machine_real_wba_pending",
            "requirement": "The current WB55 source builds in dry-run, real SSD1681 and asset-provision variants; WBA55/WBA65 callback adapters compile as Cortex-M33 and preserve ordinary SPI-NOR behavior without claiming a real WBA board.",
            "evidence": [
                evidence("wb55_build_receipt", str(wb55_build_receipt.get("status")), f"Three WB55 variants built from source commit {build_commit}; the receipt invalidates when listed build inputs change."),
                evidence("wba_m33_compile", str(wba_m33_compile.get("status")), "Eight callback-only target adapters compile with strict Cortex-M33 flags."),
                evidence("wba_spi_nor", str(wba_spi_nor.get("status")), "Ordinary 1-1-1 SPI NOR behavior passes without WBA hardware parity claim."),
                evidence("wba_port_contract", str(wba_port_contract.get("status")), "The historical WBA portability contract is explicitly overridden by the v9 external-CEMP, inactive visual boundary."),
                evidence("wba_v9_callback_replay", str(wba_v9_callback_replay.get("status")), "The inactive 39-frame v9 CEMP mounts and reads through the WBA55/WBA65 callback-only external-NOR adapter."),
                evidence("runtime_visual_boundary", str(runtime_visual_boundary.get("status")), f"Current WB55 source commit {runtime_commit} excludes retired procedural-face symbols and fails closed when a visual resource is unavailable."),
            ],
        },
        {
            "id": "v9_expression_renderer",
            "status": "proved_machine_inactive",
            "requirement": "Only the owner-approved v9 inner-face sheet supplies the 39-frame, 13-clip renderer-first candidate; no retired or procedural visual fallback is allowed.",
            "evidence": [
                evidence("v9_baseline", str(baseline.get("status")), "Locked v9 source hash is the sole current inner-face baseline."),
                evidence("v9_cemp", str(cemp.get("status")), "39/39 PBM-to-CEMP decode comparison passes without activation."),
                evidence("v9_coverage", str(coverage.get("status")), "40 scene families are explicit: 18 available candidates and 22 no-fallback pending sources."),
                evidence("v9_binding", str(binding.get("status")), "Portable selector remains AVAILABLE_NOT_ACTIVE."),
                evidence("visual_reference_ledger", str(visual_reference_ledger.get("status")), "Every current visual candidate has an exact prompt, references, output hash, request record, review state and next-prompt delta; rejected special metadata stays non-reusable."),
                evidence("v9_safe_area", str(safe_area.get("status")), "All 39 inactive v9 frames retain a >=4 px canvas margin; real-panel truncation remains a separate gate."),
                evidence("special_crop_preflight", str(special_crop_preflight.get("status")), "Both pending special-state sheets have twelve locked-source 200x200 review crops with >=4 px clearance; no PBM/CEMP import is implied."),
                evidence("ssd1681_frame_mapping", str(ssd1681_frame_mapping.get("status")), "All 40,000 logical pixels remain one-to-one and in-bounds through the actual 180-degree/mirror and descending-Y driver path; real-panel viewport remains a separate gate."),
                evidence("runtime_visual_boundary", str(runtime_visual_boundary.get("status")), "The runtime cannot substitute a procedural or test face when an external visual asset is unavailable."),
                evidence("external_expression_system", str(external_expression_system.get("status")), "Portable mood behavior selects semantic states while only external CEMP supplies product pixels."),
                evidence("resource_memory_policy", str(resource_memory_policy.get("status")), "The current resource contract accepts only v9 external CEMP candidates and prohibits legacy r53 as a visual fallback."),
            ],
        },
        {
            "id": "screen_refresh_generation_hygiene",
            "status": "proved_machine_hardware_waveform_frozen",
            "requirement": "Refresh scheduling must keep one coherent external visual generation, use bounded differential/maintenance decisions, and never reactivate a retired visual fallback; no new waveform candidate is allowed before matching vendor CWF1 evidence.",
            "evidence": [
                evidence("refresh_feel", str(refresh_feel.get("status")), "Static refresh/generation contract binds to the inactive v9 candidate and rejects stale procedural request routes."),
                evidence("queue_generation_hygiene", str(queue_generation_hygiene.get("status")), "Generation switches discard only stale external expression/menu work before the coherent next frame."),
                evidence("runtime_visual_boundary", str(runtime_visual_boundary.get("status")), "Unavailable visual resources fail closed rather than drawing a test, procedural, or code-menu substitute."),
                evidence("waveform_freeze", "FROZEN", "No generic, nearby-panel, or guessed waveform trial is authorized."),
            ],
        },
        {
            "id": "four_root_menu_function_contract",
            "status": "proved_machine_visual_import_pending_owner",
            "requirement": "Voice, Device, Connection and Preferences remain the sole menu roots in both languages; every row is a truthful action, live datum, planned or deferred state, while daily manual recording remains double-tap only.",
            "evidence": [evidence("menu_function_receipt", str(menu_function_receipt.get("status")), f"Five host replays passed from source commit {menu_commit}; this preserves menu behavior only while v6 visual art remains rejected and runtime activation remains false.")],
        },
        {
            "id": "four_root_menu_and_special_scene_sources",
            "status": "machine_previews_pass_owner_decision_pending",
            "requirement": "The v9 homepage storyboard, the no-face v7.3 four-root menu family and both special-scene sheets have deterministic one-page previews only; a complete triaged observation sequence and separate source-import proposal must precede PBM/CEMP import or runtime activation.",
            "evidence": [
                evidence("v9_home_storyboard", str(v9_home_storyboard.get("status")), "All 39 daily keyframes are individually reviewable in trigger order."),
                evidence("menu_v7_screen_family", str(menu_v7_screen_family.get("status")), "Five no-face menu screens each retain raw, English and zh-CN 200x200 pages."),
                evidence("special_system", str(special_system.get("status")), "System sheet is pending owner decision."),
                evidence("special_journey", str(special_journey.get("status")), "Journey sheet is pending owner decision."),
                evidence("special_one_page_review", str(special_one_page_review.get("status")), "All 24 special scenes are individually reviewable and remain review-only."),
                evidence("special_crop_preflight", str(special_crop_preflight.get("status")), "The exact 200x200 source-crop previews retain >=4 px clearance and remain review-only."),
                evidence("special_mapping", str(special_mapping.get("status")), "All 22 uncovered families map to exact pending sources with no fallback."),
                evidence("visual_readiness", str(visual_readiness.get("status")), "Four sequential Chinese owner-review families retain 78 machine-locked originals and non-activation boundaries."),
                evidence("goal_acceptance_readiness", str(goal_acceptance_readiness.get("status")), "Goal-scoped acceptance has explicit machine, owner, hardware and lower-edge-truncation gates."),
                evidence("g2_group_triage", str(g2_group_triage.get("status")), "The first grouped menu selection remains unapplied because the owner required locked originals one image at a time."),
                evidence("g2_home_context_triage", str(g2_home_context_triage.get("status")), "The first homepage observation remains unapplied because computer-source and physical-panel scope was unclear."),
            ],
        },
        {
            "id": "wba_resource_portability",
            "status": "pre_port_proved_real_wba_pending",
            "requirement": "WBA55/WBA65 adapters accept only v9-era external CEMP over callback-only ordinary SPI NOR; the inactive v9 pack mounts and replays through each target callback, while no WBA visual or panel parity is claimed.",
            "evidence": [
                evidence("wba_boundary", str(wba_boundary.get("status")), "WBA target boundary forbids retired visual inputs and runtime activation."),
                evidence("wba_v9_callback_replay", str(wba_v9_callback_replay.get("status")), "Host-only replay proves CEMP mount, CRC validation and all 39 reads for both targets without external Flash provisioning."),
            ],
        },
        {
            "id": "ssd1681_waveform_freeze",
            "status": "frozen_waiting_vendor_evidence",
            "requirement": "No generic, adjacent-panel or guessed SSD1681 LUT may be tried. A candidate requires a matching CWF1 vendor package before a bounded hardware session.",
            "evidence": [evidence("waveform_freeze", "FROZEN", "Vendor package requirements and fail-closed parser boundary are recorded; no panel command is authorized.")],
        },
    ]

    return {
        "schema": "companion.current_goal_audit.v1",
        "status": "GOAL_ACTIVE_MACHINE_EVIDENCE_PROVED_EXTERNAL_GATES_PENDING" if not errors else "GOAL_AUDIT_INVALID",
        "codex_goal_status": "active",
        "external_gates": "Owner visual decisions, real hardware evidence, a selected WBA target and a matching vendor CWF1 waveform package remain required before their respective acceptance items can pass.",
        "active_goal_boundary": "Only current v9/companion-menu-v7-screen-family v7.3 sources may be considered; root-only v6 and historical v5/v6/v7/v8/v10+ art and six-root menus are not active inputs.",
        "daily_visual_validation": "deterministic source/PBM/CEMP/render evidence; camera is final physical preflight only, never daily art development",
        "requirements": requirements,
        "open_gates": [
            "78 sequential owner visual observations: 39 v9 home keyframes, 15 v7.3 menu pages, 12 system pages and 12 journey pages",
            "separate approved-source PBM/CEMP import and runtime activation proposal",
            "WB55 FTS02/panel recovery, real touch/Stop/current and physical visual acceptance",
            "real WBA project, board and panel/resource parity",
            "matching vendor CWF1 waveform package before any new waveform candidate",
        ],
        "errors": errors,
        "validation_commands": [
            "python .\\tools\\verify_companion_current_goal_audit.py",
            "pwsh .\\tools\\test_companion_v9_expression_render_pipeline.ps1",
            "python .\\tools\\verify_companion_v9_wba_visual_boundary.py",
            "python .\\tools\\verify_companion_v9_frame_safe_area.py",
            "python .\\tools\\render_companion_pet_special_state_crop_preflight.py",
            "python .\\tools\\verify_companion_ssd1681_frame_mapping.py",
        "python .\\tools\\verify_companion_goal_acceptance_contract.py",
        "pwsh .\\tools\\test_companion_goal_visual_source_acceptance.ps1",
        "python .\\tools\\verify_companion_historical_branch_audit.py",
            "python .\\tools\\verify_companion_low_power_requirements.py",
            "pwsh .\\tools\\test_power_policy_host.ps1",
            "python .\\tools\\capture_wb55_current_build_receipt.py",
            "python .\\tools\\verify_companion_runtime_visual_boundary.py",
            "python .\\tools\\verify_pet_expression_system.py",
            "python .\\tools\\verify_screen_refresh_feel_contract.py",
            "python .\\tools\\verify_display_queue_generation_hygiene.py",
            "python .\\tools\\verify_screen_resource_architecture.py",
            "python .\\tools\\verify_display_queue_static.py",
            "python .\\tools\\verify_wba_adapter_m33_compile.py --self-test",
            "python .\\tools\\verify_wba_spi_nor_adapter.py --self-test",
            "python .\\tools\\verify_expression_wba_portability.py",
            "python .\\tools\\capture_wba_v9_candidate_asset_replay_receipt.py",
            "python .\\tools\\capture_companion_menu_v6_function_receipt.py",
            "python .\\tools\\render_companion_v9_home_storyboard_review.py --write",
            "python .\\tools\\render_companion_menu_v7_screen_family_preview.py --write",
            "python .\\tools\\render_companion_special_state_review_pages.py --write",
            "python .\\tools\\build_companion_ui_visual_acceptance_manifest.py --write",
        ],
    }


def render_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Companion Current Goal Audit",
        "",
        "Generated by `python .\\tools\\verify_companion_current_goal_audit.py --write`.",
        "",
        f"- Status: `{audit['status']}`",
        f"- Codex Goal lifecycle: `{audit['codex_goal_status']}`",
        f"- Current visual boundary: {audit['active_goal_boundary']}",
        f"- Daily visual validation: {audit['daily_visual_validation']}",
        "",
        "## Current Requirements",
        "",
    ]
    for requirement in audit["requirements"]:
        lines.extend((
            f"### {requirement['id']}",
            "",
            f"- Status: `{requirement['status']}`",
            f"- Requirement: {requirement['requirement']}",
            "- Evidence:",
        ))
        for item in requirement["evidence"]:
            lines.append(f"  - `{item['path']}`: `{item['status']}` - {item['detail']}")
        lines.append("")
    lines.extend(("## Open Gates", ""))
    lines.extend(f"- {item}" for item in audit["open_gates"])
    lines.extend(("", "## Validation Commands", ""))
    lines.extend(f"- `{command}`" for command in audit["validation_commands"])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    audit = build_audit()
    rendered_json = json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    rendered_md = render_markdown(audit)
    errors = list(audit["errors"])

    if args.write:
        DEFAULT_JSON.write_text(rendered_json, encoding="utf-8")
        DEFAULT_MD.write_text(rendered_md, encoding="utf-8")
    else:
        for path, expected in ((DEFAULT_JSON, rendered_json), (DEFAULT_MD, rendered_md)):
            if not path.exists():
                errors.append(f"missing {rel(path)}")
            elif path.read_text(encoding="utf-8") != expected:
                errors.append(f"stale {rel(path)}")

    if errors:
        print("FAIL: current Companion Goal audit checks failed:")
        for error in errors:
            print(f" - {error}")
        return 1
    print(f"PASS: current Companion Goal audit -> {rel(DEFAULT_JSON)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
