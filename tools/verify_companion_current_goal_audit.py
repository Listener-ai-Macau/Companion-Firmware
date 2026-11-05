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
    "visual_comparison_pages": ROOT / "docs/validation/companion-ui-visual-comparison-pages-20260717.json",
    "goal_acceptance_readiness": ROOT / "docs/validation/companion-goal-acceptance-readiness-20260717.json",
    "g2_group_triage": ROOT / "docs/validation/companion-g2-menu-group-review-triage-20260717.json",
    "g2_home_context_triage": ROOT / "docs/validation/companion-g2-home-artifact1-triage-20260717.json",
    "g2_home_anchor_triage": ROOT / "docs/validation/companion-g2-home-artifact1-anchor-triage-20260717.json",
    "wba_boundary": ROOT / "docs/validation/companion-v9-wba-visual-boundary-20260717.json",
    "waveform_freeze": ROOT / "docs/companion_ssd1681_vendor_waveform_freeze.md",
    "r8_incident": ROOT / "docs/validation/companion-ssd1681-ram-command-target-r8-launch-transport-incident-20260721.json",
    "r8_launcher_static": ROOT / "docs/validation/companion-ssd1681-ram-command-target-r8-persistent-launcher-static-20260721.json",
    "r8_static": ROOT / "docs/validation/companion-ssd1681-ram-command-target-r8-r2-static-20260721.json",
    "r8_checkonly_launch": ROOT / ".cache/validation/wb55-ram-command-target-r8-r2-persistent-checkonly-20260721-r1/persistent-launch.json",
    "r8_checkonly_stage": ROOT / ".cache/validation/wb55-ram-command-target-r8-r2-persistent-checkonly-20260721-r1/stage-run.json",
    "r8_runtime": ROOT / "docs/validation/companion-ssd1681-ram-command-target-r8-r2-runtime-20260721.json",
    "r9_runtime_disposition": ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-runtime-disposition-20260721.json",
    "r9_continuous_r1_incident": ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-runtime-disposition-20260721.json",
    "r9_continuous_prompt_r2": ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-r2-prompt-supervisor-regression-20260721.json",
    "r9_continuous_static": ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-r2-observation-static-20260721.json",
    "r9_continuous_launcher_static": ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-r2-launcher-static-20260721.json",
    "r9_continuous_checkonly_launch": ROOT / ".cache/validation/wb55-r9-continuous-r2-persistent-checkonly-20260721-r1/persistent-launch.json",
    "r9_continuous_checkonly_stage": ROOT / ".cache/validation/wb55-r9-continuous-r2-persistent-checkonly-20260721-r1/stage-run.json",
    "r9_continuous_r2_runtime": ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-continuous-r2-runtime-disposition-20260721.json",
    "r10_r1_runtime": ROOT / "docs/validation/companion-ssd1681-r10-r1-runtime-disposition-20260722.json",
    "r10_r2_runtime": ROOT / "docs/validation/companion-ssd1681-r10-r2-runtime-disposition-20260722.json",
    "r10_log_parser": ROOT / "docs/validation/companion-ssd1681-phase-parallel-r10-ball-log-parser-20260722.json",
    "r10_lifecycle": ROOT / "docs/validation/companion-ssd1681-r10-ball-lifecycle-static-20260722.json",
    "r10_machine_ready": ROOT / "docs/validation/companion-ssd1681-r10-r2-machine-ready-20260722.json",
    "r10_finalization_machine_ready": ROOT / "docs/validation/companion-ssd1681-r10-r2-finalization-machine-ready-20260722.json",
    "r10_r3_oracle": ROOT / "docs/validation/companion-ssd1681-r10-r3-ball-pixel-oracle-20260722.json",
    "r10_r3_static": ROOT / "docs/validation/companion-ssd1681-r10-r3-ball-static-20260722.json",
    "r10_r3_parser": ROOT / "docs/validation/companion-ssd1681-r10-r3-ball-log-parser-20260722.json",
    "r10_r3_lifecycle": ROOT / "docs/validation/companion-ssd1681-r10-r3-ball-lifecycle-static-20260722.json",
    "r10_r3_machine_ready": ROOT / "docs/validation/companion-ssd1681-r10-r3-execute-ready-machine-ready-20260722.json",
    "r10_r3_pre_auth": ROOT / "docs/validation/companion-ssd1681-r10-r3-preauthorization-disposition-20260722.json",
    "r10_r4b_machine_ready": ROOT / "docs/validation/companion-ssd1681-r10-r4b-corridor-telemetry-repair-machine-ready-20260722.json",
    "r10_r4b_auth": ROOT / ".cache/validation/wb55-r10-r4b-corridor-execute-20260722-r1-authorization.json",
    "r10_r5_machine_ready": ROOT / "docs/validation/companion-ssd1681-r10-r5-polarity-direction-machine-ready-20260722.json",
    "r10_r5_auth": ROOT / ".cache/validation/wb55-r10-r5-polarity-execute-20260722-r2-authorization.json",
    "r10_r6_machine_ready": ROOT / "docs/validation/companion-ssd1681-r10-r6-target-unipolar-machine-ready-20260722.json",
    "r10_r6_auth": ROOT / ".cache/validation/wb55-r10-r6-target-unipolar-execute-20260722-r1-authorization.json",
    "r10_r6_r2_auth": ROOT / ".cache/validation/wb55-r10-r6-target-unipolar-execute-20260722-r2-authorization.json",
    "r10_r6_r2_work_package": ROOT / "docs/validation/companion-ssd1681-r10-r6-target-unipolar-r2-execute-work-package-20260722.md",
    "r10_r6_r2_runtime_disposition": ROOT / "docs/validation/companion-ssd1681-r10-r6-r2-runtime-disposition-20260722.json",
    "r10_native_oracle": ROOT / "docs/validation/companion-ssd1681-r10-native-two-pass-fine-stride-oracle-20260722.json",
    "r10_native_static": ROOT / "docs/validation/companion-ssd1681-r10-native-two-pass-fine-stride-static-20260722.json",
    "r10_native_machine_ready": ROOT / "docs/validation/companion-ssd1681-r10-native-two-pass-fine-stride-machine-ready-20260722.json",
    "r10_native_work_package": ROOT / "docs/validation/companion-ssd1681-r10-native-two-pass-fine-stride-work-package-20260722.md",
    "r10_cadence_oracle": ROOT / "docs/validation/companion-ssd1681-r10-native-single-union-large-cadence-oracle-20260722.json",
    "r10_cadence_static": ROOT / "docs/validation/companion-ssd1681-r10-native-single-union-large-cadence-static-20260722.json",
    "r10_cadence_machine_ready": ROOT / "docs/validation/companion-ssd1681-r10-native-single-union-large-cadence-machine-ready-20260722.json",
    "r10_cadence_checkonly": ROOT / ".cache/validation/wb55-r10-native-single-union-large-cadence-checkonly-20260722-r14/persistent-launch.json",
    "r10_cadence_work_package": ROOT / "docs/validation/companion-ssd1681-r10-native-single-union-large-cadence-work-package-20260722.md",
    "r10_guarded_oracle": ROOT / "docs/validation/companion-ssd1681-r10-native-guarded-corridor-large-cadence-oracle-20260722.json",
    "r10_guarded_static": ROOT / "docs/validation/companion-ssd1681-r10-native-guarded-corridor-large-cadence-static-20260722.json",
    "r10_guarded_machine_ready": ROOT / "docs/validation/companion-ssd1681-r10-native-guarded-corridor-large-cadence-machine-ready-20260722.json",
    "r10_guarded_checkonly": ROOT / ".cache/validation/wb55-r10-native-guarded-corridor-large-cadence-checkonly-20260722-r1/persistent-launch.json",
    "r10_guarded_work_package": ROOT / "docs/validation/companion-ssd1681-r10-native-guarded-corridor-large-cadence-work-package-20260722.md",
    "r10_no_reset_oracle": ROOT / "docs/validation/companion-ssd1681-r10-native-guarded-corridor-no-reset-cadence-oracle-20260722.json",
    "r10_no_reset_static": ROOT / "docs/validation/companion-ssd1681-r10-native-guarded-corridor-no-reset-cadence-static-20260722.json",
    "r10_no_reset_machine_ready": ROOT / "docs/validation/companion-ssd1681-r10-native-guarded-corridor-no-reset-cadence-machine-ready-20260722.json",
    "r10_no_reset_checkonly": ROOT / ".cache/validation/wb55-r10-native-guarded-corridor-no-reset-cadence-checkonly-20260722/persistent-launch.json",
    "r10_no_reset_work_package": ROOT / "docs/validation/companion-ssd1681-r10-native-guarded-corridor-no-reset-cadence-work-package-20260722.md",
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
    visual_comparison_pages = load_json("visual_comparison_pages")
    goal_acceptance_readiness = load_json("goal_acceptance_readiness")
    g2_group_triage = load_json("g2_group_triage")
    g2_home_context_triage = load_json("g2_home_context_triage")
    g2_home_anchor_triage = load_json("g2_home_anchor_triage")
    wba_boundary = load_json("wba_boundary")
    waveform_freeze = ARTIFACTS["waveform_freeze"].read_text(encoding="utf-8")
    waveform_freeze_normalized = waveform_freeze.lower()
    r8_incident = load_json("r8_incident")
    r8_launcher_static = load_json("r8_launcher_static")
    r8_static = load_json("r8_static")
    r8_checkonly_launch = load_json("r8_checkonly_launch")
    r8_checkonly_stage = load_json("r8_checkonly_stage")
    r8_runtime = load_json("r8_runtime")
    r9_runtime_disposition = load_json("r9_runtime_disposition")
    r9_continuous_r1_incident = load_json("r9_continuous_r1_incident")
    r9_continuous_prompt_r2 = load_json("r9_continuous_prompt_r2")
    r9_continuous_static = load_json("r9_continuous_static")
    r9_continuous_launcher_static = load_json("r9_continuous_launcher_static")
    r9_continuous_checkonly_launch = load_json("r9_continuous_checkonly_launch")
    r9_continuous_checkonly_stage = load_json("r9_continuous_checkonly_stage")
    r9_continuous_r2_runtime = load_json("r9_continuous_r2_runtime")
    r10_r1_runtime = load_json("r10_r1_runtime")
    r10_r2_runtime = load_json("r10_r2_runtime")
    r10_log_parser = load_json("r10_log_parser")
    r10_lifecycle = load_json("r10_lifecycle")
    r10_machine_ready = load_json("r10_machine_ready")
    r10_finalization_machine_ready = load_json("r10_finalization_machine_ready")
    r10_r3_oracle = load_json("r10_r3_oracle")
    r10_r3_static = load_json("r10_r3_static")
    r10_r3_parser = load_json("r10_r3_parser")
    r10_r3_lifecycle = load_json("r10_r3_lifecycle")
    r10_r3_machine_ready = load_json("r10_r3_machine_ready")
    r10_r3_pre_auth = load_json("r10_r3_pre_auth")
    r10_r4b_machine_ready = load_json("r10_r4b_machine_ready")
    r10_r4b_auth_path = ARTIFACTS["r10_r4b_auth"]
    r10_r4b_auth = load_json("r10_r4b_auth") if r10_r4b_auth_path.exists() else {
        "status": "HISTORICAL_CONSUMED_SOURCE_ABSENT",
        "consumed": True,
        "source_absent_after_consumption": True,
    }
    r10_r5_machine_ready = load_json("r10_r5_machine_ready")
    r10_r5_auth_path = ARTIFACTS["r10_r5_auth"]
    r10_r5_auth_consumed = not r10_r5_auth_path.exists()
    r10_r5_auth = load_json("r10_r5_auth") if not r10_r5_auth_consumed else json.loads(Path(str(r10_r5_auth_path) + ".consumed.json").read_text(encoding="utf-8"))
    r10_r6_machine_ready = load_json("r10_r6_machine_ready")
    r10_r6_auth_path = ARTIFACTS["r10_r6_auth"]
    r10_r6_auth_consumed = not r10_r6_auth_path.exists()
    r10_r6_auth = load_json("r10_r6_auth") if not r10_r6_auth_consumed else json.loads(Path(str(r10_r6_auth_path) + ".consumed.json").read_text(encoding="utf-8"))
    r10_r6_r2_auth_path = ARTIFACTS["r10_r6_r2_auth"]
    r10_r6_r2_auth = load_json("r10_r6_r2_auth") if r10_r6_r2_auth_path.exists() else json.loads(Path(str(r10_r6_r2_auth_path) + ".consumed.json").read_text(encoding="utf-8"))
    r10_r6_r2_runtime_disposition = load_json("r10_r6_r2_runtime_disposition")
    r10_native_oracle = load_json("r10_native_oracle")
    r10_native_static = load_json("r10_native_static")
    r10_native_machine_ready = load_json("r10_native_machine_ready")
    r10_cadence_oracle = load_json("r10_cadence_oracle")
    r10_cadence_static = load_json("r10_cadence_static")
    r10_cadence_machine_ready = load_json("r10_cadence_machine_ready")
    r10_cadence_checkonly = load_json("r10_cadence_checkonly")
    r10_guarded_oracle = load_json("r10_guarded_oracle")
    r10_guarded_static = load_json("r10_guarded_static")
    r10_guarded_machine_ready = load_json("r10_guarded_machine_ready")
    r10_guarded_checkonly = load_json("r10_guarded_checkonly")
    r10_no_reset_oracle = load_json("r10_no_reset_oracle")
    r10_no_reset_static = load_json("r10_no_reset_static")
    r10_no_reset_machine_ready = load_json("r10_no_reset_machine_ready")
    r10_no_reset_checkonly = load_json("r10_no_reset_checkonly")
    product_registry = (ROOT / "docs/companion_product_requirements.md").read_text(encoding="utf-8")
    lower_driver_source = (ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c").read_text(encoding="utf-8")

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
    check(errors, mapped_v9.get("frame_count") == 39 and
          isinstance(mapped_v9.get("minimum_mapped_edge_clearance_px"), int) and
          mapped_v9.get("minimum_mapped_edge_clearance_px") >= 4,
          "SSD1681 mapped v9 frame safety fell below the 4 px threshold")
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
    check(errors, visual_comparison_pages.get("status") == "PASS_PAIRED_ART_BASELINE_AND_DESKTOP_OUTPUT_READY" and visual_comparison_pages.get("page_total") == 78, "paired art/output comparison pages are not PASS")
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
        paired_pages = next((entry.get("pages", []) for entry in visual_comparison_pages.get("items", []) if entry.get("id") == item.get("id")), [])
        check(errors, len(paired_pages) == expected_count and all(image.get("comparison", {}).get("comparison_page", {}).get("sha256") == paired_pages[index].get("comparison_page", {}).get("sha256") for index, image in enumerate(images)), f"{item.get('id')} paired comparison binding drifted")
    check(errors, goal_acceptance_readiness.get("status") == "PASS_ACCEPTANCE_CONTRACT_READY_OWNER_AND_HARDWARE_GATED", "detailed Goal acceptance readiness is not PASS")
    check(errors, goal_acceptance_readiness.get("machine_preflight_opens_operator_prompt") is False, "detailed Goal machine preflight must not open a popup")
    check(errors, r8_incident.get("status") == "R8_CANDIDATE_NOT_EXECUTED_CLEAN_RESTORE_RESUME_PASS_LAUNCH_TRANSPORT_FAILED", "R8 launch incident disposition differs")
    check(errors, r8_incident.get("candidate_boundary", {}).get("candidate_write_calls") == 0, "R8 incident overclaims a candidate run")
    check(errors, r8_incident.get("superseded_non_acceptance_prompt", {}).get("selected") is None, "R8 incident fabricates a popup selection")
    check(errors, r8_launcher_static.get("status") == "PASS_R8_PERSISTENT_LAUNCHER_STATIC_AND_NEGATIVE_FIXTURES", "R8 persistent launcher fixtures are not PASS")
    check(errors, r8_static.get("status") == "MACHINE_READY_R8_R2_NO_HARDWARE_CONTACT_EXECUTE_FORBIDDEN_PENDING_ROOT", "R8-R2 static gate is not machine-ready")
    check(errors, r8_checkonly_launch.get("status") == "READY_NO_HARDWARE_CONTACT", "R8-R2 persistent CheckOnly launcher is not ready")
    check(errors, r8_checkonly_launch.get("exit_code") == 0 and r8_checkonly_launch.get("hardware_contact") == 0 and r8_checkonly_launch.get("write_counter_sum") == 0, "R8-R2 persistent CheckOnly did not prove zero contact/writes")
    check(errors, r8_checkonly_launch.get("durable_stdout_redirected") is True and r8_checkonly_launch.get("durable_stderr_redirected") is True, "R8-R2 child streams are not durable")
    check(errors, r8_checkonly_stage.get("status") == "READY_NO_HARDWARE_CONTACT" and r8_checkonly_stage.get("hardware_contact") == 0, "R8-R2 child stage is not zero-contact ready")
    check(errors, r8_checkonly_stage.get("popup_policy", {}).get("machine_only_r8_total") == 0, "R8-R2 machine-only popup count is not zero")
    check(errors, r8_checkonly_stage.get("pre_execute_prompt", {}).get("invoked") is False and r8_checkonly_stage.get("operator_prompt", {}).get("invoked") is False, "R8-R2 CheckOnly opened or claims an operator popup")
    check(errors, r8_runtime.get("status") == "PASS_MACHINE_R8_R2_FIXED_BANK_MAPPING_CLEANED_RESTORED", "R8-R2 runtime disposition is not PASS")
    check(errors, r8_runtime.get("classification", {}).get("selected_mapping") == "fixed_bank", "R8-R2 did not prove fixed-bank command mapping")
    check(errors, r8_runtime.get("classification", {}).get("target_selector") == {"0x24": 0, "0x26": 1}, "R8-R2 command-to-selector mapping differs")
    check(errors, len(r8_runtime.get("selector_responses", [])) == 28, "R8-R2 does not archive all 28 selector response hashes")
    check(errors, r8_runtime.get("popup_count") == 0 and r8_runtime.get("automatic_retries") == 0, "R8-R2 popup/retry count differs")
    check(errors, "| COMP-REQ-313 |" in product_registry and "你现在就是需要无限自动刷屏。" in product_registry, "owner-authorized continuous-observation exception is absent from registry")
    check(errors, "| COMP-REQ-315 |" in product_registry and "| COMP-REQ-316 |" in product_registry, "R1 incident or R2 repair contract is absent from registry")
    check(errors, r9_runtime_disposition.get("status") == "NO_GO_R9_OWNER_VISUAL_FAILED_RESTORED_STOP_NO_MOTION", "historical R9 runtime/owner disposition changed")
    check(errors, r9_continuous_r1_incident.get("status") == "NO_GO_R9_CONTINUOUS_PROMPT_SUPERVISOR_PRE_GUARD_FAILED_RESTORED_NO_RETRY", "R9 continuous R1 incident disposition differs")
    check(errors, r9_continuous_r1_incident.get("acceptance", {}).get("popup_opened") is False and r9_continuous_r1_incident.get("acceptance", {}).get("visual_verdict") is None, "R9 continuous R1 invents a popup or visual verdict")
    check(errors, r9_continuous_r1_incident.get("authorization", {}).get("consumed") is True and r9_continuous_r1_incident.get("authorization", {}).get("retry_allowed") is False, "R9 continuous R1 authorization/retry boundary differs")
    check(errors, r9_continuous_prompt_r2.get("status") == "PASS_R9_CONTINUOUS_R2_REAL_SUPERVISOR_PATH_NO_HARDWARE" and r9_continuous_prompt_r2.get("hardware_contact") == 0 and r9_continuous_prompt_r2.get("actual_popup_count") == 0, "R9 continuous R2 real supervisor-path regression is not PASS")
    check(errors, r9_continuous_prompt_r2.get("positive_proof") == {"guard_created": True, "prompt_process_start_count": 1, "actual_popup_count": 0}, "R9 continuous R2 did not prove one guard/process with zero actual popup")
    check(errors, r9_continuous_static.get("status") == "PASS_STATIC_R9_CONTINUOUS_R2_OBSERVATION" and r9_continuous_static.get("hardware_contact") == 0, "R9 continuous R2 implementation static gate is not zero-contact PASS")
    check(errors, r9_continuous_static.get("checks", {}).get("historical_r9_function_unchanged") is True and r9_continuous_static.get("checks", {}).get("initial_gate_exactly_16") is True, "R9 continuous extension changed or replaced the original 16-step qualification boundary")
    check(errors, r9_continuous_launcher_static.get("status") == "PASS_STATIC_R9_CONTINUOUS_R2_LAUNCHER" and r9_continuous_launcher_static.get("hardware_contact") == 0, "R9 continuous R2 launcher static/negative gate is not PASS")
    check(errors, r9_continuous_checkonly_launch.get("status") == "READY_NO_HARDWARE_CONTACT" and r9_continuous_checkonly_launch.get("hardware_contact") == 0 and r9_continuous_checkonly_launch.get("write_counter_sum") == 0 and r9_continuous_checkonly_launch.get("popup_count") == 0, "R9 continuous persistent CheckOnly is not zero-contact/zero-write/zero-popup")
    check(errors, r9_continuous_checkonly_stage.get("status") == "READY_NO_HARDWARE_CONTACT" and r9_continuous_checkonly_stage.get("hardware_contact") == 0, "R9 continuous inner CheckOnly stage is not ready")
    check(errors, r9_continuous_checkonly_stage.get("operator_prompt", {}).get("required") is True and r9_continuous_checkonly_stage.get("operator_prompt", {}).get("invoked") is False, "R9 continuous CheckOnly prompt boundary differs")
    check(errors, r9_continuous_r2_runtime.get("status") == "NO_GO_R9_CONTINUOUS_R2_OWNER_VISUAL_FAILED_RESTORED_NO_RETRY", "R9 continuous R2 runtime/owner disposition differs")
    check(errors, r9_continuous_r2_runtime.get("qualification") == {"activations": 16, "busy_max_ms": 599}, "R9 continuous R2 qualification differs")
    check(errors, r9_continuous_r2_runtime.get("loop", {}).get("records") == 1060 and r9_continuous_r2_runtime.get("loop", {}).get("ring_bytes") == 65536, "R9 continuous R2 loop/ring evidence differs")
    check(errors, r9_continuous_r2_runtime.get("operator", {}).get("selected") == "失败" and r9_continuous_r2_runtime.get("operator", {}).get("note_sha256") == "30DDA3C9CC92110E636C9954652716EA805086DD15E889ED26B4F88D720B5698", "R9 continuous R2 owner result/note differs")
    check(errors, r9_continuous_r2_runtime.get("restore", {}).get("sha256") == "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C" and r9_continuous_r2_runtime.get("restore", {}).get("normal_resume_status") == "PASS_APPLICATION_RESUMED_AFTER_BACKUP", "R9 continuous R2 restore/normal resume differs")
    check(errors, r9_continuous_r2_runtime.get("authorization", {}).get("consumed") is True and r9_continuous_r2_runtime.get("authorization", {}).get("retry_allowed") is False, "R9 continuous R2 authorization/retry boundary differs")
    check(errors, r9_continuous_r2_runtime.get("process_matches") == [], "R9 continuous R2 archived process-exit audit differs")
    check(errors, "| COMP-REQ-318 |" in product_registry and "| COMP-REQ-319 |" in product_registry and "| COMP-REQ-320 |" in product_registry, "historical R9 disposition or R10 planning record is absent from registry")
    check(errors, all(f"| COMP-REQ-{number} |" in product_registry for number in range(322, 360)), "COMP-REQ-322..359 current R10 evidence boundary is absent from registry")
    check(errors, "R10 remains planned but NOT STARTED" in product_registry, "historical R10 NOT STARTED fact is not preserved")
    check(errors, "r10_actual_solid_ball" in lower_driver_source and "ssd1681_phase_parallel_r9_lut" in lower_driver_source, "current R10 candidate source evidence is absent")
    check(errors, r10_r1_runtime.get("status") == "NO_GO_R1_HOST_EVIDENCE_PERSISTENCE" and r10_r1_runtime.get("qualification", {}).get("captured_frames") == 16, "R10 R1 host persistence incident evidence differs")
    check(errors, r10_r1_runtime.get("qualification", {}).get("post_run_direct_parser", {}).get("status") == "PASS_R10_BALL_LOG", "R10 R1 post-run diagnostic parser evidence differs")
    check(errors, r10_r1_runtime.get("lifecycle", {}).get("postclean") == "PASS" and r10_r1_runtime.get("lifecycle", {}).get("restore_sha256") == "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C" and r10_r1_runtime.get("lifecycle", {}).get("normal_resume") == "PASS", "R10 R1 cleanup/restore/resume evidence differs")
    check(errors, r10_r2_runtime.get("status") == "NO_GO_R10_R2_OWNER_VISUAL_FAIL_FINALIZATION_PARTIAL_LINE", "R10 R2 disposition status differs")
    check(errors, r10_r2_runtime.get("machine_qualification", {}).get("qualification_frames") == 16 and r10_r2_runtime.get("machine_qualification", {}).get("busy_max_ms") == 599, "R10 R2 qualification evidence differs")
    check(errors, r10_r2_runtime.get("live_loop", {}).get("complete_live_validated_records") == 160 and r10_r2_runtime.get("live_loop", {}).get("partial_uart_record") == "loop_iteration=161" and r10_r2_runtime.get("live_loop", {}).get("partial_record_complete") is False, "R10 R2 complete/partial loop boundary differs")
    check(errors, r10_r2_runtime.get("owner_acceptance", {}).get("selected") == "失败" and r10_r2_runtime.get("owner_acceptance", {}).get("note_sha256") == "35B06B7587CDA2E4AE084CBA8206D79D4A6C9AF556347A08D1E081B5242C2C65", "R10 R2 owner visual FAIL evidence differs")
    check(errors, r10_r2_runtime.get("lifecycle", {}).get("postclean") == "PASS" and r10_r2_runtime.get("lifecycle", {}).get("restore_sha256") == "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C" and r10_r2_runtime.get("lifecycle", {}).get("normal_resume") == "PASS", "R10 R2 cleanup/restore/resume evidence differs")
    check(errors, r10_r2_runtime.get("next_boundary") == "COMP-REQ-331 offline finalization repair only; no driver variable chosen and no next hardware authority", "R10 R2 next boundary permits unauthorized work")
    check(errors, r10_log_parser.get("status") == "PASS_R10_BALL_LOG_PARSER" and len(r10_log_parser.get("negative_fixtures", [])) == 36, "R10 parser artifact is not the current 36-case PASS")
    check(errors, r10_lifecycle.get("status") == "PASS_R10_REAL_EXECUTE_LIFECYCLE_STATIC" and r10_lifecycle.get("parser_finalization_fixtures", {}).get("passed") is True and r10_lifecycle.get("monitor_finalization_fixture", {}).get("record", {}).get("status") == "NO_GO_FINALIZATION", "R10 finalization lifecycle evidence is incomplete")
    check(errors, r10_machine_ready.get("hardware_contact") == 0 and r10_machine_ready.get("execute_authorized") is False, "R10 machine-ready boundary permits hardware")
    check(errors, r10_finalization_machine_ready.get("status") == "MACHINE_READY_R10_BALL_HOST_FINALIZATION_ONLY" and r10_finalization_machine_ready.get("authority") == "COMP-REQ-331" and r10_finalization_machine_ready.get("host_finalization_only") is True and r10_finalization_machine_ready.get("hardware_contact") == 0 and r10_finalization_machine_ready.get("execute_authorized") is False and r10_finalization_machine_ready.get("authorization_created") is False, "R10 host-finalization successor is not offline-only")
    check(errors, r10_finalization_machine_ready.get("finalization_contract", {}).get("candidate_elf_hex_lut_unchanged") is True, "R10 host-finalization successor does not protect candidate ELF/HEX/LUT")
    check(errors, "| COMP-REQ-332 |" in product_registry, "COMP-REQ-332 R3 stable-hold decision is absent from registry")
    check(errors, r10_r3_oracle.get("schema_id") == "companion.wb55.ssd1681.r10_r3_ball_pixel_oracle.v2" and r10_r3_oracle.get("r2_payload_hash_identity", {}).get("frame_and_payload_hashes_match") is True, "R10 R3 oracle does not prove R2 frame/payload hash identity")
    check(errors, r10_r3_static.get("status") == "PASS_R10_BALL_STATIC" and r10_r3_static.get("authority") == "COMP-REQ-332" and "one_400_to_410ms_post_sync_stable_hold_in_qualification_and_loop" in r10_r3_static.get("proved", []), "R10 R3 stable-hold static evidence differs")
    check(errors, r10_r3_parser.get("schema_id") == "companion.wb55.ssd1681.r10_r3_ball_log_parser.v2" and r10_r3_parser.get("status") == "PASS_R10_BALL_LOG_PARSER" and len(r10_r3_parser.get("negative_fixtures", [])) >= 44, "R10 R3 hold-aware parser evidence is incomplete")
    check(errors, r10_r3_lifecycle.get("schema_id") == "companion.wb55.ssd1681.r10_r3_ball.lifecycle_static.v8" and r10_r3_lifecycle.get("status") == "PASS_R10_R3_REAL_EXECUTE_LIFECYCLE_STATIC" and r10_r3_lifecycle.get("checks", {}).get("r3_stable_hold_source") is True and r10_r3_lifecycle.get("checks", {}).get("r3_hold_parser_contract") is True and r10_r3_lifecycle.get("authorization_positive", {}).get("actual_popup_count", 0) == 0, "R10 R3 lifecycle hold evidence differs")
    check(errors, r10_r3_machine_ready.get("status") == "MACHINE_READY_R10_R3_EXECUTE_READY_HOST_BINDING_SUCCESSOR" and r10_r3_machine_ready.get("authority") == "COMP-REQ-335" and r10_r3_machine_ready.get("binding_successor") is True and r10_r3_machine_ready.get("hardware_contact") == 0 and r10_r3_machine_ready.get("execute_authorized") is False and r10_r3_machine_ready.get("authorization_created") is False, "R10 R3 execute-ready successor is not offline-only")
    check(errors, r10_r3_pre_auth.get("status") == "NO_GO_R3_BIND_REPAIR_REQUIRED" and r10_r3_pre_auth.get("historical_authorization", {}).get("sha256") == "886E53989D6A2C4504D15DE316C7EBAA29AAA3D945F9B594C9DB249EE4E6FCDA" and r10_r3_pre_auth.get("historical_authorization", {}).get("consumed") is False and r10_r3_pre_auth.get("preparation_hardware_contact") == 0, "R10 R3 historical NO_GO disposition differs")
    check(errors, r10_r3_machine_ready.get("canonical_audit_invocation") == "python tools/verify_companion_current_goal_audit.py" and r10_r3_machine_ready.get("canonical_audit_required") is True, "R10 R3 MACHINE_READY did not bind the canonical audit invocation")
    check(errors, r10_r4b_machine_ready.get("status") == "MACHINE_READY_R10_R4B_TELEMETRY_REPAIR_OFFLINE_ONLY" and r10_r4b_machine_ready.get("authority") == "COMP-REQ-339" and r10_r4b_machine_ready.get("hardware_contact") == 0 and r10_r4b_machine_ready.get("execute_authorized") is False, "R10 R4b MACHINE_READY is not offline-only")
    r4_disposition = r10_r4b_machine_ready.get("r4_disposition", {})
    check(errors, r4_disposition.get("authorization_consumed") is True and r4_disposition.get("status") == "MACHINE_NO_GO_TELEMETRY_PERSISTENCE" and r4_disposition.get("popup_invoked") is False and r4_disposition.get("visual_verdict") is None and r4_disposition.get("postclean") == "PASS" and r4_disposition.get("restore_sha256") == "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C" and r4_disposition.get("normal_resume") == "PASS" and r4_disposition.get("retry_count") == 0, "R10 R4 consumed MACHINE_NO_GO disposition differs")
    check(errors, r10_r4b_machine_ready.get("r4b_repair", {}).get("cached_checkonly_reused_by_sha") is True and r10_r4b_machine_ready.get("r4b_repair", {}).get("unchanged_host_hashes_reused") is True, "R10 R4b cached host gate reuse is not recorded")
    if r10_r4b_auth_path.exists():
        check(errors, r10_r4b_auth.get("status") == "AUTHORIZED_R10_BALL_ONCE" and r10_r4b_auth.get("consumed") is False and r10_r4b_auth.get("requirement_id") == "COMP-REQ-323" and r10_r4b_auth.get("authorization_requirement_id") == "COMP-REQ-340" and r10_r4b_auth.get("attempt_limit") == 1 and r10_r4b_auth.get("automatic_retries") == 0, "R10 R4b authorization preparation is not fresh one-shot COMP-REQ-340")
        check(errors, r10_r4b_auth.get("machine_ready_sha256") == "F4C1EE53AB729F2817CF7A963F48D9F4D5B48D8C1C208C4093DDA21229C5A8E8" and r10_r4b_auth.get("candidate_hex_sha256") == "F861956CCE8DF648300BEAB3CA4179E9BBC108E98A2949FA21D98FD03C9DD764" and r10_r4b_auth.get("candidate_elf_sha256") == "114C1C0A0FBDD70F6119C2EFF35F9F8279E0A73734C4E959C97EE9EBAAB16211" and r10_r4b_auth.get("lut_sha256") == "9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD" and r10_r4b_auth.get("restore_application_sha256") == "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C", "R10 R4b authorization candidate binding drifted")
        r10_r4b_root = Path(str(r10_r4b_auth.get("output_root")))
        check(errors, not r10_r4b_root.exists() and not Path(str(r10_r4b_auth_path) + ".claim.json").exists() and not Path(str(r10_r4b_auth_path) + ".spent").exists() and not Path(str(r10_r4b_auth_path) + ".consumed.json").exists(), "R10 R4b authorization root or claim artifacts already exist")
    else:
        check(errors, r10_r4b_auth.get("status") == "HISTORICAL_CONSUMED_SOURCE_ABSENT" and r10_r4b_auth.get("consumed") is True, "R10 R4b consumed authorization source absence is not archived")
    check(errors, "| COMP-REQ-341 |" in product_registry and "| COMP-REQ-343 |" in product_registry and "| COMP-REQ-344 |" in product_registry and "| COMP-REQ-345 |" in product_registry and "| COMP-REQ-346 |" in product_registry and "| COMP-REQ-347 |" in product_registry and "| COMP-REQ-348 |" in product_registry, "COMP-REQ-341/343/344/345/346/347/348 R5/R6 evidence boundary is absent from registry")
    check(errors, r10_r5_machine_ready.get("status") == "MACHINE_READY_R10_R5_POLARITY_DIRECTION_OFFLINE_ONLY" and r10_r5_machine_ready.get("authority") == "COMP-REQ-343" and r10_r5_machine_ready.get("hardware_contact") == 0 and r10_r5_machine_ready.get("execute_authorized") is False and r10_r5_machine_ready.get("authorization_created") is False, "R10 R5 MACHINE_READY is not offline-only")
    r5_protected = r10_r5_machine_ready.get("protected", {})
    check(errors, r5_protected.get("historical_r9_lut_sha256") == "9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD" and r5_protected.get("r5_lut_sha256") == "447FB169543F3E33EA6080607B685E2ADB8F38066952FCDF020882359BA94E89" and r5_protected.get("r5_changed_offsets") == [12, 13, 14, 15, 24, 25, 26, 27], "R10 R5 polarity LUT evidence drifted")
    check(errors, r10_r5_machine_ready.get("focused_evidence", {}).get("status") == "PASS_R10_R5_POLARITY_FOCUSED" and r10_r5_machine_ready.get("focused_evidence", {}).get("r4_corridor_static_verifier_status") == "PASS_R10_R4_CORRIDOR_STATIC" and r10_r5_machine_ready.get("artifacts", {}).get("r4_corridor_static_verifier") == "95D180FC743D0DD28D1337BFDC2B6D101F891E9777AFD617BD55B79160395D5D" and r10_r5_machine_ready.get("cached_gates", {}).get("checkonly_reused_by_exact_sha") is True, "R10 R5 focused/static evidence or cached-gate lineage is incomplete")
    if r10_r5_auth_consumed:
        check(errors, r10_r5_auth.get("status") == "CONSUMED_AUTHORIZED_R10_BALL_ONCE" and r10_r5_auth.get("consumed") is True and r10_r5_auth.get("requirement_id") == "COMP-REQ-323", "R10 R5 consumed authorization receipt is not archived")
        check(errors, r10_r5_auth.get("machine_ready_sha256") == "B5535BCAB604D0E127E1BEDC72F822520F1A61DDF8DB4CF2C5B7EDBEB0BB5166" and r10_r5_auth.get("candidate_hex_sha256") == "37768F04A444BB9B9F4C15D4B0DE4AD8517D48F65C462D3F952D28A70F5CDD71" and r10_r5_auth.get("parser_sha256") == "CE8FE4210808797CF24B4177E59306B9DAC5BA14AEA898EB73AF2FBC257EA254", "R10 R5 consumed candidate binding drifted")
        r10_r5_root = Path(str(r10_r5_auth.get("output_root")))
        check(errors, r10_r5_root.exists() and Path(str(r10_r5_auth_path) + ".claim.json").exists() and Path(str(r10_r5_auth_path) + ".spent").exists() and Path(str(r10_r5_auth_path) + ".consumed.json").exists(), "R10 R5 consumed authorization evidence is incomplete")
    else:
        check(errors, r10_r5_auth.get("status") == "AUTHORIZED_R10_BALL_ONCE" and r10_r5_auth.get("consumed") is False and r10_r5_auth.get("requirement_id") == "COMP-REQ-323" and r10_r5_auth.get("authorization_requirement_id") == "COMP-REQ-344" and r10_r5_auth.get("attempt_limit") == 1 and r10_r5_auth.get("automatic_retries") == 0, "R10 R5 authorization is not fresh one-shot COMP-REQ-344")
        check(errors, not Path(str(r10_r5_auth.get("output_root"))).exists() and not Path(str(r10_r5_auth_path) + ".claim.json").exists() and not Path(str(r10_r5_auth_path) + ".spent").exists() and not Path(str(r10_r5_auth_path) + ".consumed.json").exists(), "R10 R5 fresh authorization root or claim artifacts already exist")
    check(errors, r10_r6_machine_ready.get("status") == "MACHINE_READY_R10_R6_TARGET_UNIPOLAR_OFFLINE_ONLY" and r10_r6_machine_ready.get("authority") == "COMP-REQ-345" and r10_r6_machine_ready.get("hardware_contact") == 0 and r10_r6_machine_ready.get("execute_authorized") is False and r10_r6_machine_ready.get("authorization_created") is False, "R10 R6 MACHINE_READY is not offline-only")
    check(errors, r10_r6_machine_ready.get("focused_evidence", {}).get("status") == "PASS_R10_R6_TARGET_UNIPOLAR_FOCUSED" and r10_r6_machine_ready.get("focused_evidence", {}).get("static_verifier_status") == "PASS_R10_R4_CORRIDOR_STATIC", "R10 R6 focused/static evidence is incomplete")
    if r10_r6_auth_consumed:
        r10_r6_root = Path(str(r10_r6_auth.get("output_root")))
        r10_r6_monitor = json.loads((r10_r6_root / "continuous-monitor/monitor-result.json").read_text(encoding="utf-8"))
        r10_r6_stage = json.loads((r10_r6_root / "stage-run.json").read_text(encoding="utf-8"))
        r10_r6_restore = r10_r6_stage.get("restore", {})
        r10_r6_resume = r10_r6_stage.get("normal_resume", {})
        check(errors, r10_r6_auth.get("status") == "CONSUMED_AUTHORIZED_R10_BALL_ONCE" and r10_r6_auth.get("consumed") is True and r10_r6_auth.get("requirement_id") == "COMP-REQ-323", "R10 R6 consumed authorization receipt is invalid")
        check(errors, r10_r6_root.exists() and Path(str(r10_r6_auth_path) + ".claim.json").exists() and Path(str(r10_r6_auth_path) + ".spent").exists() and Path(str(r10_r6_auth_path) + ".consumed.json").exists(), "R10 R6 consumed authorization evidence is incomplete")
        check(errors, r10_r6_monitor.get("status") == "NO_GO_EMERGENCY_STOP" and r10_r6_monitor.get("qualified") is True and r10_r6_monitor.get("loop_records_seen") == 823 and r10_r6_monitor.get("hardware_contact") == 1 and r10_r6_monitor.get("popup_count") == 0 and r10_r6_monitor.get("retry_count") == 0, "R10 R6 monitor disposition differs")
        check(errors, r10_r6_stage.get("status") == "NO_GO_R10_BALL_VISUAL_NOT_PASSED_RESTORED" and r10_r6_stage.get("operator_prompt", {}).get("selected") is None and r10_r6_stage.get("operator_prompt", {}).get("note") is None, "R10 R6 operator disposition is not NOT OBSERVED")
        check(errors, r10_r6_stage.get("postclean", {}).get("result", {}).get("status") == "PASS_MACHINE_DUAL_PLANE_WHITE_CLEAN_BOTH_BANKS_READBACK_WHITE" and r10_r6_restore.get("restore_sha256") == "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C" and r10_r6_restore.get("byte_identical") is True and r10_r6_resume.get("status") == "PASS_APPLICATION_RESUMED_AFTER_BACKUP", "R10 R6 cleanup/restore/resume disposition differs")
    else:
        check(errors, r10_r6_auth.get("status") == "AUTHORIZED_R10_BALL_ONCE" and r10_r6_auth.get("consumed") is False and r10_r6_auth.get("requirement_id") == "COMP-REQ-323" and r10_r6_auth.get("authorization_requirement_id") == "COMP-REQ-346" and r10_r6_auth.get("attempt_limit") == 1 and r10_r6_auth.get("automatic_retries") == 0, "R10 R6 authorization is not fresh one-shot COMP-REQ-346")
        check(errors, not Path(str(r10_r6_auth.get("output_root"))).exists() and not Path(str(r10_r6_auth_path) + ".claim.json").exists() and not Path(str(r10_r6_auth_path) + ".spent").exists() and not Path(str(r10_r6_auth_path) + ".consumed.json").exists(), "R10 R6 fresh authorization root or claim artifacts already exist")
    r10_r6_r2_root = Path(str(r10_r6_r2_auth.get("output_root")))
    check(errors, r10_r6_r2_auth.get("status") == "CONSUMED_AUTHORIZED_R10_BALL_ONCE" and r10_r6_r2_auth.get("consumed") is True and r10_r6_r2_auth.get("requirement_id") == "COMP-REQ-323", "R10 R6 R2 consumed authorization receipt is not archived")
    check(errors, r10_r6_r2_root.exists() and Path(str(r10_r6_r2_auth_path) + ".claim.json").exists() and Path(str(r10_r6_r2_auth_path) + ".spent").exists() and Path(str(r10_r6_r2_auth_path) + ".consumed.json").exists(), "R10 R6 R2 consumed runtime evidence is incomplete")
    check(errors, r10_r6_r2_runtime_disposition.get("machine_qualification") == {"status": "PASS", "frames": 16, "busy_max_ms": 599} and r10_r6_r2_runtime_disposition.get("observation", {}).get("loop_records") == 52 and r10_r6_r2_runtime_disposition.get("observation", {}).get("status") == "NO_GO_FINALIZATION" and r10_r6_r2_runtime_disposition.get("observation", {}).get("visual_verdict") == "FAIL", "R6 R2 runtime disposition is not archived with separate finalization fault")
    check(errors, r10_native_oracle.get("status") == "PASS" and r10_native_oracle.get("qualification_frames") == 16 and r10_native_oracle.get("loop_frames") == 32, "native two-pass oracle is not PASS")
    check(errors, r10_native_static.get("status") == "PASS", "native two-pass static evidence is not PASS")
    check(errors, r10_native_machine_ready.get("status") == "MACHINE_READY_R10_NATIVE_TWO_PASS_FINE_STRIDE_OFFLINE_ONLY" and r10_native_machine_ready.get("authority") == "COMP-REQ-349" and r10_native_machine_ready.get("hardware_contact") == 0 and r10_native_machine_ready.get("execute_authorized") is False and r10_native_machine_ready.get("authorization_created") is False, "native two-pass MACHINE_READY is not offline-only")
    check(errors, r10_native_machine_ready.get("checkonly") == {"hardware_contact": 0, "writes": 0, "popup_count": 0, "retry_count": 0, "child_exit_code": 0, "durable_stdout_stderr": True}, "native two-pass CheckOnly boundary drifted")
    check(errors, "| COMP-REQ-349 |" in product_registry, "COMP-REQ-349 native two-pass authority is absent from registry")
    check(errors, "| COMP-REQ-353 |" in product_registry, "COMP-REQ-353 cadence authority is absent from registry")
    check(errors, r10_cadence_oracle.get("status") == "PASS" and r10_cadence_oracle.get("geometry", {}).get("black_pixels") == 448 and r10_cadence_oracle.get("loop_transitions") == 32 and r10_cadence_oracle.get("activations_per_movement") == 1, "R10 cadence oracle is not PASS")
    check(errors, r10_cadence_static.get("status") == "PASS" and r10_cadence_static.get("checks", {}).get("one_activation") is True and r10_cadence_static.get("checks", {}).get("union_reused") is True, "R10 cadence static evidence is not PASS")
    check(errors, r10_cadence_machine_ready.get("status") == "MACHINE_READY_R10_NATIVE_SINGLE_UNION_LARGE_CADENCE_OFFLINE_ONLY" and r10_cadence_machine_ready.get("authority") == "COMP-REQ-353" and r10_cadence_machine_ready.get("hardware_contact") == 0 and r10_cadence_machine_ready.get("execute_authorized") is False and r10_cadence_machine_ready.get("authorization_created") is False, "R10 cadence MACHINE_READY is not offline-only")
    check(errors, r10_cadence_machine_ready.get("transport", {}).get("physical_start_to_start_cadence") == "UNPROVEN_UNTIL_EXECUTE" and r10_cadence_machine_ready.get("transport", {}).get("compact_loop_record_max_bytes") == 320 and r10_cadence_machine_ready.get("transport", {}).get("qualification_loop_minimum") == 2 and r10_cadence_machine_ready.get("transport", {}).get("qualification_cadence_measurements_minimum") == 1 and r10_cadence_machine_ready.get("transport", {}).get("finalization_loop_minimum") == 2, "R10 cadence runtime evidence boundary drifted")
    check(errors, r10_cadence_machine_ready.get("checkonly", {}).get("hardware_contact") == 0 and r10_cadence_machine_ready.get("checkonly", {}).get("writes") == 0 and r10_cadence_machine_ready.get("checkonly", {}).get("popup_count") == 0 and r10_cadence_machine_ready.get("checkonly", {}).get("retry_count") == 0, "R10 cadence CheckOnly boundary drifted")
    check(errors, r10_cadence_checkonly.get("status") == "READY_NO_HARDWARE_CONTACT" and r10_cadence_checkonly.get("hardware_contact") == 0 and r10_cadence_checkonly.get("write_counter_sum") == 0 and r10_cadence_checkonly.get("popup_count") == 0 and r10_cadence_checkonly.get("retry_count") == 0 and r10_cadence_checkonly.get("child_exited") is True, "R10 cadence persistent CheckOnly is not zero-contact")
    check(errors, "| COMP-REQ-357 |" in product_registry, "COMP-REQ-357 guarded-corridor authority is absent from registry")
    check(errors, r10_guarded_oracle.get("status") == "PASS" and r10_guarded_oracle.get("geometry", {}).get("black_pixels") == 448 and r10_guarded_oracle.get("loop_transitions") == 32 and r10_guarded_oracle.get("activations_per_movement") == 1 and all(item.get("union_window") == "3-11,80-103" and item.get("omitted_columns") == 0 for item in r10_guarded_oracle.get("records", [])), "R10 guarded-corridor oracle is not PASS")
    check(errors, r10_guarded_static.get("status") == "PASS" and r10_guarded_static.get("checks", {}).get("fixed_guarded_corridor") is True and r10_guarded_static.get("checks", {}).get("one_activation") is True, "R10 guarded-corridor static evidence is not PASS")
    check(errors, r10_guarded_machine_ready.get("status") == "MACHINE_READY_R10_NATIVE_GUARDED_CORRIDOR_LARGE_CADENCE_OFFLINE_ONLY" and r10_guarded_machine_ready.get("authority") == "COMP-REQ-357" and r10_guarded_machine_ready.get("hardware_contact") == 0 and r10_guarded_machine_ready.get("execute_authorized") is False and r10_guarded_machine_ready.get("authorization_created") is False, "R10 guarded-corridor MACHINE_READY is not offline-only")
    check(errors, r10_guarded_machine_ready.get("transport", {}).get("diff_window") == "fixed_guarded_corridor_x_bytes_3_11_y_80_103_216_bytes" and r10_guarded_machine_ready.get("transport", {}).get("prior_position_rewhitened") is True, "R10 guarded-corridor transport boundary drifted")
    check(errors, r10_guarded_machine_ready.get("checkonly", {}).get("hardware_contact") == 0 and r10_guarded_machine_ready.get("checkonly", {}).get("writes") == 0 and r10_guarded_machine_ready.get("checkonly", {}).get("popup_count") == 0 and r10_guarded_machine_ready.get("checkonly", {}).get("retry_count") == 0, "R10 guarded-corridor CheckOnly boundary drifted")
    check(errors, r10_guarded_checkonly.get("status") == "READY_NO_HARDWARE_CONTACT" and r10_guarded_checkonly.get("hardware_contact") == 0 and r10_guarded_checkonly.get("write_counter_sum") == 0 and r10_guarded_checkonly.get("popup_count") == 0 and r10_guarded_checkonly.get("retry_count") == 0 and r10_guarded_checkonly.get("child_exited") is True, "R10 guarded-corridor persistent CheckOnly is not zero-contact")
    check(errors, "| COMP-REQ-359 |" in product_registry, "COMP-REQ-359 no-reset cadence authority is absent from registry")
    check(errors, r10_no_reset_oracle.get("status") == "PASS" and r10_no_reset_oracle.get("geometry", {}).get("black_pixels") == 448 and r10_no_reset_oracle.get("activations_per_movement") == 1, "R10 no-reset cadence oracle is not PASS")
    check(errors, r10_no_reset_static.get("status") == "PASS" and r10_no_reset_static.get("checks", {}).get("movement_no_reset_fields") is True and r10_no_reset_static.get("checks", {}).get("one_activation") is True, "R10 no-reset cadence static evidence is not PASS")
    check(errors, r10_no_reset_machine_ready.get("status") == "MACHINE_READY_R10_NATIVE_GUARDED_CORRIDOR_NO_RESET_CADENCE_OFFLINE_ONLY" and r10_no_reset_machine_ready.get("authority") == "COMP-REQ-359" and r10_no_reset_machine_ready.get("hardware_contact") == 0 and r10_no_reset_machine_ready.get("execute_authorized") is False and r10_no_reset_machine_ready.get("authorization_created") is False, "R10 no-reset cadence MACHINE_READY is not offline-only")
    check(errors, r10_no_reset_machine_ready.get("transport", {}).get("baseline_source_resets") == 1 and r10_no_reset_machine_ready.get("transport", {}).get("movement_source_resets") == 0 and r10_no_reset_machine_ready.get("transport", {}).get("start_to_start_target_ms") == 490, "R10 no-reset source/cadence boundary drifted")
    check(errors, r10_no_reset_machine_ready.get("checkonly", {}).get("hardware_contact") == 0 and r10_no_reset_machine_ready.get("checkonly", {}).get("writes") == 0 and r10_no_reset_machine_ready.get("checkonly", {}).get("popup_count") == 0 and r10_no_reset_machine_ready.get("checkonly", {}).get("retry_count") == 0, "R10 no-reset cadence CheckOnly boundary drifted")
    check(errors, r10_no_reset_checkonly.get("status") == "READY_NO_HARDWARE_CONTACT" and r10_no_reset_checkonly.get("hardware_contact") == 0 and r10_no_reset_checkonly.get("write_counter_sum") == 0 and r10_no_reset_checkonly.get("popup_count") == 0 and r10_no_reset_checkonly.get("retry_count") == 0 and r10_no_reset_checkonly.get("child_exited") is True, "R10 no-reset cadence persistent CheckOnly is not zero-contact")
    check(errors, goal_acceptance_readiness.get("physical_acceptance", {}).get("lower_edge_truncation") == "must be checked during G5 before any visual pass", "lower-edge truncation gate is missing")
    check(errors, g2_group_triage.get("status") == "OPEN_REVIEW_FLOW_REWORK_REQUIRED", "G2 original-image review rework is not open")
    check(errors, g2_group_triage.get("requirement") == "COMP-REQ-079", "G2 original-image review rework lost its requirement")
    check(errors, g2_group_triage.get("resolution", {}).get("group_selection_applied") is False, "G2 grouped visual selection was incorrectly applied")
    check(errors, g2_home_context_triage.get("status") == "NOT_APPLIED_OWNER_CONTEXT_MISMATCH", "G2 home observation must remain unapplied for context mismatch")
    check(errors, g2_home_context_triage.get("requirement") == "COMP-REQ-083" and g2_home_context_triage.get("decision", {}).get("selection_applied") is False, "G2 home context triage drifted")
    check(errors, g2_home_anchor_triage.get("status") == "OPEN_ANCHOR_NORMALIZATION_REWORK_REQUIRED", "G2 home anchor rework must remain open")
    check(errors, g2_home_anchor_triage.get("requirement") == "COMP-REQ-085" and g2_home_anchor_triage.get("decision", {}).get("selection_applied") is False, "G2 home anchor triage drifted")

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
            "id": "ssd1681_r10_r5_polarity_direction_offline_machine_ready",
            "status": "r5_single_lut_direction_discriminator_offline_only",
            "requirement": "COMP-REQ-341 archives the R4b visual FAIL and authorizes only the R5 dedicated-LUT polarity-direction discriminator. The historical R9 LUT remains unchanged; R5 changes exactly eight bytes, preserves the ball/corridor/command/hold/lifecycle contract, accepts schema v4 while retaining v2/v3, and stops at default-off MACHINE_READY with no authorization or hardware contact.",
            "evidence": [
                evidence("r10_r5_machine_ready", str(r10_r5_machine_ready.get("status")), "R5 binds the new ELF/HEX/driver and focused schema-v4 waveform/parser evidence while reusing unchanged host gates by exact SHA."),
            ],
        },
        {
            "id": "ssd1681_r10_r5_physical_execute_preparation",
            "status": "r5_exactly_one_execute_pending_unconsumed",
            "requirement": "COMP-REQ-344 authorizes exactly one fresh R5 r2 physical closure after the COMP-REQ-343 zero-write preflight repair. The source remains consumed=false, with fresh root and claim/spent/receipt absence; no ClaimOnly or Execute has occurred.",
            "evidence": [evidence("r10_r5_auth", str(r10_r5_auth.get("status")), "R5 authorization is hash-bound to the regenerated MR and exact candidate/tool identities while remaining unconsumed.")],
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
                evidence("visual_comparison_pages", str(visual_comparison_pages.get("status")), "All 78 G2 observations show the locked generated-art baseline beside the deterministic desktop output."),
                evidence("special_crop_preflight", str(special_crop_preflight.get("status")), "The exact 200x200 source-crop previews retain >=4 px clearance and remain review-only."),
                evidence("special_mapping", str(special_mapping.get("status")), "All 22 uncovered families map to exact pending sources with no fallback."),
                evidence("visual_readiness", str(visual_readiness.get("status")), "Four sequential Chinese owner-review families retain 78 machine-locked paired source/output observations and non-activation boundaries."),
                evidence("goal_acceptance_readiness", str(goal_acceptance_readiness.get("status")), "Goal-scoped acceptance has explicit machine, owner, hardware and lower-edge-truncation gates."),
                evidence("g2_group_triage", str(g2_group_triage.get("status")), "The first grouped menu selection remains unapplied because the owner required locked originals one image at a time."),
                evidence("g2_home_context_triage", str(g2_home_context_triage.get("status")), "The first homepage observation remains unapplied because computer-source and physical-panel scope was unclear."),
                evidence("g2_home_anchor_triage", str(g2_home_anchor_triage.get("status")), "The next homepage observation remains closed until the owner-requested whole-expression anchor normalization has machine evidence."),
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
        {
            "id": "ssd1681_r8_transport_recovery",
            "status": "r8_r2_machine_pass_fixed_bank_mapping_restored_stop",
            "requirement": "R8 remains production-off and machine-only. The direct-launch incident executed no candidate and recovered exact raw bytes. The sole later persistent run proved fixed-bank command targeting (`0x24 -> selector0`, `0x26 -> selector1`), archived all 28 response hashes, then completed promptless cleanup and exact restore. Its one-shot authorization is consumed and no successor experiment is authorized.",
            "evidence": [
                evidence("r8_incident", str(r8_incident.get("status")), "Inner artifacts prove dual-plane cleanup, exact restore and normal resume; candidate writes stayed zero and the empty non-acceptance popup is not a verdict."),
                evidence("r8_launcher_static", str(r8_launcher_static.get("status")), "Static and no-hardware negative fixtures reject missing redirects/PID/hidden launch, hash drift, output reuse, child failure and mixed modes."),
                evidence("r8_static", str(r8_static.get("status")), "The unchanged R8 candidate and zero-popup runner pass static/parser gates."),
                evidence("r8_checkonly_launch", str(r8_checkonly_launch.get("status")), "Persistent child exited zero with durable logs, hardware_contact=0 and write_counter_sum=0."),
                evidence("r8_checkonly_stage", str(r8_checkonly_stage.get("status")), "The inner stage proves zero writes, zero panel commands and zero popup invocation."),
                evidence("r8_runtime", str(r8_runtime.get("status")), "The sole Execute proves fixed-bank command mapping, 28 selector response hashes, zero post-tag activation, promptless dual-plane cleanup, exact restore and normal resume."),
            ],
        },
        {
            "id": "ssd1681_r9_continuous_observation_exception",
            "status": "r2_owner_visual_failed_restored_historical_boundary",
            "requirement": "COMP-REQ-313 preserves the completed historical R9 16-step qualification and separate no-preset-limit observation loop. R1 remains a zero-popup supervisor incident. The sole later COMP-REQ-317 R2 Execute passed its 16-step qualification, looped W/A/B/A 1060 times, then received the owner's final visual FAIL because it did not read as one continuously moving ball; it cleaned both planes, restored exact raw bytes and resumed the normal application. COMP-REQ-320 and the former R10 NOT STARTED pause remain historical facts; current successor boundaries are recorded by COMP-REQ-322..331.",
            "evidence": [
                evidence("r9_runtime_disposition", str(r9_runtime_disposition.get("status")), "The historical sealed R9 run remains 16/16 machine PASS, owner FAIL, promptless cleanup and exact restore; its qualification result is unchanged."),
                evidence("r9_continuous_r1_incident", str(r9_continuous_r1_incident.get("status")), "The consumed R1 attempt archives 16-step max 599 ms, one loop max 597 ms, bounded telemetry, exact restore, zero popup/selection/note and no retry."),
                evidence("r9_continuous_prompt_r2", str(r9_continuous_prompt_r2.get("status")), "The real no-hardware supervisor path creates one guard, starts exactly one process and opens zero actual popups; missing qualification and duplicate guard/result fail before process start."),
                evidence("r9_continuous_static", str(r9_continuous_static.get("status")), "The R2 repair preserves the default-off build, candidate HEX, LUT and initial 16-step gate while fixing only prompt supervision and adding real-path regression."),
                evidence("r9_continuous_launcher_static", str(r9_continuous_launcher_static.get("status")), "Static and negative fixtures prove consumed authorization rejection, fail-closed child handling and output-reuse rejection."),
                evidence("r9_continuous_checkonly_launch", str(r9_continuous_checkonly_launch.get("status")), "Persistent CheckOnly exited zero with durable streams, zero hardware contact, zero writes and zero popup invocation."),
                evidence("r9_continuous_checkonly_stage", str(r9_continuous_checkonly_stage.get("status")), "The inner stage retains one eligible acceptance popup only after future machine qualification while invoking none during CheckOnly."),
                evidence("r9_continuous_r2_runtime", str(r9_continuous_r2_runtime.get("status")), "The sole R2 Execute qualified 16/16, looped 1060 contiguous iterations with a bounded 65536-byte ring, recorded one owner visual FAIL, then completed promptless cleanup, exact restore, normal resume and process exit; no retry is allowed."),
            ],
        },
        {
            "id": "ssd1681_r10_r1_r2_and_finalization_boundary",
            "status": "r2_machine_pass_owner_visual_fail_offline_finalization_only",
            "requirement": "COMP-REQ-322..331 record the R10 R1 host evidence-persistence incident, R2's 16-frame machine PASS, 599 ms BUSY maximum, 160 complete live-validated loop records, one canonical owner FAIL, promptless cleanup, exact 524288-byte restore and normal resume, plus the completed offline finalization repair. COMP-REQ-329 preserves the durable single-low-level-variable owner workflow. COMP-REQ-332 then authorizes only the primary-selected R3 stable-hold cadence discriminator for offline MACHINE_READY; no additional variable or hardware authority is implied.",
            "evidence": [
                evidence("r10_r1_runtime", str(r10_r1_runtime.get("status")), "R1 is archived as a host evidence-persistence incident, not a driver or visual verdict; post-run diagnostic parsing is not retroactively treated as the original gate."),
                evidence("r10_r2_runtime", str(r10_r2_runtime.get("status")), "R2 archives 16/16 qualification, 160 complete records plus partial 161, the verbatim owner FAIL and cleanup/restore/resume evidence."),
                evidence("r10_log_parser", str(r10_log_parser.get("status")), "The parser rejects 36 executed negative fixtures and owns the bounded trailing-partial rule."),
                evidence("r10_lifecycle", str(r10_lifecycle.get("status")), "No-hardware lifecycle evidence executes the parser write contract, trailing-partial positives/negatives and monitor NO_GO_FINALIZATION regression."),
                evidence("r10_machine_ready", str(r10_machine_ready.get("status")), "Existing R2 MACHINE_READY remains a zero-contact, production-off historical artifact."),
                evidence("r10_finalization_machine_ready", str(r10_finalization_machine_ready.get("status")), "The new successor binds current parser/monitor/lifecycle hashes while remaining COMP-REQ-331 host-finalization-only with no authorization."),
            ],
        },
        {
            "id": "ssd1681_r10_r3_stable_hold_cadence_discriminator",
            "status": "r3_machine_ready_offline_only_cadence_discriminator",
            "requirement": "COMP-REQ-332 records the primary-selected single R3 variable: one measured 400-410 ms stable hold after every successful post-sync 0x24 and before the next frame, in both qualification and unlimited loop. R2 frame/payload hashes, geometry, command topology, LUT/tail/mapping and finalization rules remain protected. R3 is a cadence discriminator only and claims no final visual repair or hardware authority.",
            "evidence": [
                evidence("r10_r3_oracle", str(r10_r3_oracle.get("status")), "R3 independently proves the solid disk and exact R2 frame/payload hash identity."),
                evidence("r10_r3_static", str(r10_r3_static.get("status")), "Static source evidence proves exactly one measured post-sync stable hold with 400-410 ms bounds and no second dwell."),
                evidence("r10_r3_parser", str(r10_r3_parser.get("status")), "The v2 parser executes hold timing/order/count negatives while retaining the R2 finalization rule."),
                evidence("r10_r3_lifecycle", str(r10_r3_lifecycle.get("status")), "No-hardware lifecycle and CheckOnly regression remain production-off."),
                evidence("r10_r3_machine_ready", str(r10_r3_machine_ready.get("status")), "Distinct R3 MACHINE_READY binds the current ELF/HEX/LUT and all tool hashes, and directly invokes the canonical audit."),
            ],
        },
        {
            "id": "ssd1681_incremental_shutter_validation_and_generic_mr_manifest",
            "status": "incremental_shutter_targeted_gates_sha_reuse_and_one_closure",
            "requirement": "COMP-REQ-336 establishes the durable owner workflow: future SSD1681 human iterations use an incremental shutter, run targeted oracle/parser/build only for affected inputs, reuse unchanged gates by input SHA, avoid repeated unchanged full negatives/CheckOnly/MACHINE_READY/docs, and run exactly one complete closure before each hardware candidate. Fresh one-shot authorization, candidate/tool hashes, dual-plane White pre/post-clean, BUSY/command safety, one canonical popup, exact restore/readback, normal resume and final process audit remain mandatory; the launcher is to evolve toward a generic authorization-bound MACHINE_READY manifest.",
            "evidence": [
                {"path": "docs/companion_product_requirements.md", "status": "REGISTERED", "detail": "Owner's latest 2026-07-22 incremental-shutter and generic-MR-manifest steering is registered without selecting a new driver variable or authorizing hardware."}
            ],
        },
        {
            "id": "ssd1681_r10_r4_corridor_execute_preparation",
            "status": "r4_machine_no_go_consumed_r4b_offline_repair",
            "requirement": "COMP-REQ-338's R4 physical run consumed its one-shot authorization but stopped at MACHINE_NO_GO before popup because telemetry persisted the obsolete compact-window payload hashes. COMP-REQ-339 permits only the R4b offline telemetry repair and fresh zero-contact MACHINE_READY.",
            "evidence": [evidence("r10_r4b_machine_ready", str(r10_r4b_machine_ready.get("status")), "R4 disposition is restored with no visual verdict; R4b binds only the position-keyed telemetry repair and reuses unchanged host gates by SHA.")],
        },
        {
            "id": "ssd1681_r10_r4b_corridor_execute_preparation",
            "status": "r4b_exactly_one_execute_pending_unconsumed",
            "requirement": "COMP-REQ-340 authorizes exactly one sealed R4b physical run with requirement_id COMP-REQ-323, a fresh output root and atomic one-shot consumption; no ClaimOnly or Execute occurred during preparation.",
            "evidence": [evidence("r10_r4b_auth", str(r10_r4b_auth.get("status")), "The fresh R4b auth is consumed=false, hash-bound to the accepted MR and has no root, claim, spent or receipt artifact.")],
        },
        {
            "id": "ssd1681_r10_r6_target_unipolar_physical_disposition",
            "status": "r6_machine_pass_not_observed_emergency_stopped_restored",
            "requirement": "COMP-REQ-347 archives R6 machine qualification and 823 observed loop records, but the canonical supervisor timed out and failed closed before operator review; the visual verdict is NOT OBSERVED. Cleanup, exact restore and normal resume passed, and no successor variable or authorization is allowed until direct owner visual feedback.",
            "evidence": [
                {"path": "docs/companion_product_requirements.md", "status": "REGISTERED", "detail": "R6 physical disposition is recorded as machine evidence plus NO_GO_EMERGENCY_STOP with no popup/selection/note; it is not a visual verdict."},
            ],
        },
        {
            "id": "ssd1681_r10_r6_r2_reobservation_preparation",
            "status": "r2_consumed_visual_fail_finalization_fault_archived",
            "requirement": "COMP-REQ-349 archives the consumed R6-R2 runtime: 16 qualification PASS, BUSY max599, 52 loop records, canonical owner FAIL, and a separate NO_GO_FINALIZATION host fault. Promptless postclean, exact restore and normal resume passed with retry0 and no live process.",
            "evidence": [
                evidence("r10_r6_r2_auth", str(r10_r6_r2_auth.get("status")), "R2 authorization is consumed history and its runtime root, claim, spent and receipt evidence remain archived."),
                evidence("r10_r6_r2_runtime_disposition", str(r10_r6_r2_runtime_disposition.get("status")), "The human FAIL is valid visual evidence; NO_GO_FINALIZATION is separately classified as a host finalization fault."),
            ],
        },
        {
            "id": "ssd1681_r10_native_two_pass_fine_stride",
            "status": "native_otp_mode2_two_pass_machine_ready_offline_only",
            "requirement": "COMP-REQ-349 archives the R6-R2 human FAIL and separate NO_GO_FINALIZATION host fault, then defines the owner-accepted COMP-REQ-236 native OTP Mode2 baseline: one x32 baseline activation followed by 16 qualification movement frames using 32 activations and the same path for an unlimited loop. This candidate is default-off, production-off and not hardware-authorized.",
            "evidence": [
                evidence("r10_r6_r2_runtime_disposition", str(r10_r6_r2_runtime_disposition.get("status")), "R6-R2 records 16 qualification, BUSY max599, 52 loops, human FAIL, finalization fault, cleanup, exact restore and normal resume."),
                evidence("r10_native_oracle", str(r10_native_oracle.get("status")), "The oracle proves 112-pixel disk geometry, 2px ping-pong path, previous-black/full-diff windows, 16 qualification frames and 32 activations."),
                evidence("r10_native_static", str(r10_native_static.get("status")), "Static evidence proves the native source-bound 0xFF/0x24/0x20 path and forbidden-command zeros."),
                evidence("r10_native_machine_ready", str(r10_native_machine_ready.get("status")), "MACHINE_READY is production-off with hardware_contact=0, execute_authorized=false, authorization_created=false and CheckOnly 0/0/0/0."),
            ],
        },
        {
            "id": "ssd1681_r10_native_single_union_large_cadence",
            "status": "native_otp_mode2_single_union_large_cadence_machine_ready_offline_only",
            "requirement": "COMP-REQ-353 preserves the r2 current-best visual floor and implements only the refresh-cadence discriminator: a 24x24/448-pixel disk, 2px ping-pong, one exact source-bound activation per movement, 16-frame qualification and 32-transition unbounded loop. Physical residue, dirty-white flash or missing edge remains an owner NO_GO boundary.",
            "evidence": [
                evidence("r10_cadence_oracle", str(r10_cadence_oracle.get("status")), "The oracle exhaustively proves 448 black pixels, exact 2px path, union windows, full current payload hashes and zero omitted columns."),
                evidence("r10_cadence_static", str(r10_cadence_static.get("status")), "Static evidence proves one source-bound activation, 0xFF/0x24/0x20 transport, cadence target and forbidden-command zeros."),
                evidence("r10_cadence_machine_ready", str(r10_cadence_machine_ready.get("status")), "MACHINE_READY is default-off with hardware_contact=0, execute_authorized=false, authorization_created=false and CheckOnly 0/0/0/0."),
                evidence("r10_cadence_checkonly", str(r10_cadence_checkonly.get("status")), "Persistent CheckOnly child exited 0 with hardware_contact=0, writes=0, popup=0 and retry=0."),
            ],
        },
        {
            "id": "ssd1681_r10_native_guarded_corridor_large_cadence",
            "status": "guarded_corridor_offline_machine_ready_visual_residue_unproven",
            "requirement": "COMP-REQ-357 preserves the COMP-REQ-356 r2 current-best floor and records the latest owner steering about black line residue. The offline-only successor changes only the write topology to a fixed x-byte 3..11/y80..103 guarded corridor that rewrites full current-frame bytes once per source-bound native activation; optical residue remains an owner hardware boundary.",
            "evidence": [
                evidence("r10_guarded_oracle", str(r10_guarded_oracle.get("status")), "The oracle proves 448 black pixels, exact 2px/32px ping-pong, fixed 216-byte corridor payloads and omitted_columns=0 for every transition."),
                evidence("r10_guarded_static", str(r10_guarded_static.get("status")), "Static evidence proves the new default-off macro/header, one source-bound activation, exact corridor, frame SHA binding and forbidden-command zeros."),
                evidence("r10_guarded_machine_ready", str(r10_guarded_machine_ready.get("status")), "MACHINE_READY is production-off with execute_authorized=false, authorization_created=false and physical residue explicitly unproven."),
                evidence("r10_guarded_checkonly", str(r10_guarded_checkonly.get("status")), "Persistent CheckOnly child exited 0 with hardware_contact=0, writes=0, popup=0 and retry=0."),
            ],
        },
        {
            "id": "ssd1681_r10_native_guarded_corridor_no_reset_cadence",
            "status": "no_reset_cadence_machine_ready_offline_only_visual_latency_unproven",
            "requirement": "COMP-REQ-359 preserves the accepted guarded-corridor visual floor and authorizes only offline implementation of the no-reset cadence discriminator: one baseline hardware reset, movement ready-state checks without reset, one official OTP Mode2 activation per 24x24/448-pixel movement, and unchanged owner/hardware boundaries.",
            "evidence": [
                evidence("r10_no_reset_oracle", str(r10_no_reset_oracle.get("status")), "The focused oracle proves the accepted 24x24/448-pixel geometry, fixed corridor and 32-transition path."),
                evidence("r10_no_reset_static", str(r10_no_reset_static.get("status")), "Static evidence proves default-off selector, v11 no-reset telemetry fields, one activation and forbidden-command zeros."),
                evidence("r10_no_reset_machine_ready", str(r10_no_reset_machine_ready.get("status")), "MACHINE_READY remains production-off, execute unauthorized and explicitly unproven for physical cadence/optical quality."),
                evidence("r10_no_reset_checkonly", str(r10_no_reset_checkonly.get("status")), "Persistent CheckOnly exited with hardware_contact=0, writes=0, popup=0 and retry=0."),
            ],
        },
    ]

    return {
        "schema": "companion.current_goal_audit.v1",
        "status": "GOAL_ACTIVE_MACHINE_EVIDENCE_PROVED_EXTERNAL_GATES_PENDING" if not errors else "GOAL_AUDIT_INVALID",
        "codex_goal_status": "active",
        "external_gates": "Owner visual decisions, remaining real hardware evidence and a selected WBA target remain required before their respective acceptance items can pass. R8-R2, R9 one-shot, R9 continuous R1/R2 and R10 R1/R2/R4b/R6-R1 authorizations are historical/consumed as recorded. R4b was an owner visual FAIL; R6-R1 is NOT OBSERVED after NO_GO_EMERGENCY_STOP, while COMP-REQ-348 permits only the fresh unconsumed R6-R2 re-observation package. R5 is offline-only MACHINE_READY and future SSD1681 human iterations follow COMP-REQ-336 incremental-shutter targeted gates.",
        "active_goal_boundary": "Only current v9/companion-menu-v7-screen-family v7.3 sources may be considered; root-only v6 and historical v5/v6/v7/v8/v10+ art and six-root menus are not active inputs. For SSD1681 R10, driver, candidate and existing R3 evidence remain unchanged; R6-R1 has no visual verdict, and COMP-REQ-348 permits only one byte-identical R6-R2 re-observation. Future human iterations are constrained by COMP-REQ-336 incremental-shutter SHA reuse and generic authorization-bound MACHINE_READY manifest steering.",
        "daily_visual_validation": "deterministic source/PBM/CEMP/render evidence; camera is final physical preflight only, never daily art development",
        "post_safety_observation_exception": "COMP-REQ-313 preserves the historical 16-step qualification cap as the gate. COMP-REQ-315 closes R1 as restored with zero popup and no visual verdict. COMP-REQ-318 closes R2 as 16/16 machine PASS plus 1060-loop HUMAN FAIL, exact restore and no retry. COMP-REQ-330 records R10 R2's 16/160 machine evidence and owner visual FAIL; COMP-REQ-332 records R3's single 400-410 ms post-sync hold discriminator. COMP-REQ-339 records R4's consumed MACHINE_NO_GO telemetry incident with no visual verdict; COMP-REQ-341 records R4b's owner visual FAIL and R5's offline-only polarity discriminator. COMP-REQ-347 records R6-R1's machine qualification and 823 loop records followed by NO_GO_EMERGENCY_STOP before operator review, with NOT OBSERVED visual status and restored completion. COMP-REQ-348 permits one fresh byte-identical R6-R2 re-observation source only; it is not consumed here. COMP-REQ-336 preserves incremental-shutter SHA reuse and one-closure human iteration.",
        "requirements": requirements,
        "open_gates": [
            "78 sequential owner visual observations: 39 v9 home keyframes, 15 v7.3 menu pages, 12 system pages and 12 journey pages",
            "separate approved-source PBM/CEMP import and runtime activation proposal",
            "WB55 FTS02/panel recovery, real touch/Stop/current and physical visual acceptance",
            "real WBA project, board and panel/resource parity",
            "matching vendor CWF1 waveform package before any new waveform candidate",
            "no retry of any consumed R8/R9/R10 authorization; R3 stable-hold MACHINE_READY is offline-only and no future Execute authorization is created here",
        ],
        "errors": errors,
        "validation_commands": [
            "python .\\tools\\verify_companion_current_goal_audit.py",
            "python .\\tools\\verify_wb55_ssd1681_ram_command_target_r8_launcher.py",
            "python .\\tools\\verify_wb55_ssd1681_ram_command_target_r8_diagnostic.py",
            "python .\\tools\\verify_wb55_ssd1681_ram_command_target_r8_r2_runtime.py",
            "python .\\tools\\verify_wb55_ssd1681_phase_parallel_r9_continuous_observation.py",
            "python .\\tools\\verify_wb55_ssd1681_phase_parallel_r9_continuous_launcher.py",
            "python .\\tools\\verify_wb55_ssd1681_phase_parallel_r9_continuous_prompt_supervisor_r2.py",
            "python .\\tools\\verify_wb55_ssd1681_phase_parallel_r9_continuous_runtime_disposition.py",
            "python .\\tools\\verify_wb55_ssd1681_phase_parallel_r9_continuous_r2_runtime_disposition.py",
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
            "python .\\tools\\render_companion_visual_comparison_pages.py --write",
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
