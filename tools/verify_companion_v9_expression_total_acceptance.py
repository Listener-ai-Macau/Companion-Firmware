#!/usr/bin/env python3
"""Self-audit the upper V9 expression system before human acceptance opens.

This report is deliberately conservative: an unbound special-decoration asset
is evidence of source export, not evidence of a complete special expression.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
PROTECTED_OWNER_ACCEPTANCE = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
PROTECTED_OWNER_ACCEPTANCE_SHA256 = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"
V22_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/candidate/target-rig-attempt-01/v22-emotion-separation-target-rig-layout.json"
V22_TARGET_GATE = ROOT / "docs/validation/companion-v22-emotion-separation-target-rig-gate-20260719.json"
V22_ROUTER = ROOT / "docs/validation/companion-v22-everyday-bridge-router-r2-20260720.json"
UPPER_GATE = ROOT / "docs/validation/companion-v9-v22-expression-upper-gate-r5-20260720.json"
SPECIAL_EXPORT_GATE = ROOT / "docs/validation/companion-v34-v35-special-decoration-component-export-gate-20260720.json"
SPECIAL_TARGET_MOUNT = ROOT / "docs/validation/companion-v34-v35-special-decoration-target-asset-mount-20260720.json"
SPECIAL_WB55_PROFILE_TRACE = ROOT / "docs/art/iterations/companion-pet-expression-v9-special-decoration-rig-v1/candidate/target-score-attempt-01/special-decoration-wb55-target-profile-plan.json"
SPECIAL_BROWSER_PREVIEW = ROOT / "docs/validation/companion-v34-v35-special-decoration-browser-wb55-preview-20260720.json"
SPECIAL_WB55_PARITY = ROOT / "docs/validation/companion-v34-v35-special-decoration-wb55-component-parity-host-20260720.json"
V37_EXPORT_GATE = ROOT / "docs/validation/companion-v37-sleepy-dream-component-export-gate-20260720.json"
V37_WB55_PROFILE_TRACE = ROOT / "docs/art/iterations/companion-pet-expression-v9-sleepy-dream-rig-v1/candidate/target-score-attempt-01/sleepy-dream-wb55-target-profile-plan.json"
V37_WB55_PROFILE_HOST = ROOT / "docs/validation/companion-v37-sleepy-dream-wb55-profile-host-20260720.json"
V37_BROWSER_PREVIEW = ROOT / "docs/validation/companion-v37-sleepy-dream-browser-wb55-preview-20260720.json"
V37_WB55_PARITY = ROOT / "docs/validation/companion-v37-sleepy-dream-wb55-component-parity-host-20260720.json"
V38_EXPORT_GATE = ROOT / "docs/validation/companion-v38-function-state-component-export-gate-20260720.json"
V38_WB55_PROFILE_TRACE = ROOT / "docs/art/iterations/companion-pet-expression-v9-function-state-decoration-rig-v1/candidate/target-score-attempt-01/function-state-wb55-target-profile-plan.json"
V38_WB55_PROFILE_HOST = ROOT / "docs/validation/companion-v38-function-state-wb55-profile-host-20260720.json"
V38_BROWSER_PREVIEW = ROOT / "docs/validation/companion-v38-function-state-browser-wb55-preview-20260720.json"
V38_WB55_PARITY = ROOT / "docs/validation/companion-v38-function-state-wb55-component-parity-host-20260720.json"
WBA_ASSET_ADAPTER = ROOT / "app/companion_pendant/epaper/screen_assets_stm32wba.c"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise ValueError(f"missing required evidence: {rel(path)}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def pass_status(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict) or not str(value.get("status", "")).startswith("PASS"):
        raise ValueError(f"{name} is not a PASS artifact")
    return {"artifact": rel(Path(value["_path"])), "status": value["status"]}


def evidence(path: Path) -> dict[str, object]:
    value = read_json(path)
    value["_path"] = str(path)
    return value


def v22_component_choreography(layout: dict[str, object]) -> dict[str, object]:
    components = layout.get("components")
    bridges = layout.get("bridges")
    if not isinstance(components, list) or not isinstance(bridges, list):
        raise ValueError("V22 target layout lacks components or bridges")
    roles = {component.get("role") for component in components if isinstance(component, dict)}
    required_roles = {"left_eye", "right_eye", "left_highlight", "right_highlight", "left_sparkle",
                      "right_sparkle", "left_brow", "right_brow", "left_cheek", "right_cheek", "mouth", "nose"}
    if not required_roles.issubset(roles) or layout.get("component_count") != len(components) or len(bridges) != 10:
        raise ValueError("V22 does not cover every required daily facial component or bridge")
    nose_ids = {component.get("component_id") for component in components if component.get("role") == "nose"}
    if len(nose_ids) != 1:
        raise ValueError("V22 nose identity component is ambiguous")
    nose_id = next(iter(nose_ids))
    bridge_records = []
    total_frames = 0
    for bridge in bridges:
        frames = bridge.get("frames") if isinstance(bridge, dict) else None
        if not isinstance(frames, list) or len(frames) < 7:
            raise ValueError("V22 bridge has too few component score frames")
        cues = [frame.get("cue") for frame in frames]
        required_cues = ["source_hold", "primary_highlight_lead", "sparkle_arrive", "brow_apex", "lower_face_apex",
                          "target_hold", "highlight_settle"]
        if any(cue not in cues for cue in required_cues) or cues.index("primary_highlight_lead") > cues.index("brow_apex") or \
                cues.index("brow_apex") > cues.index("lower_face_apex") or cues.index("lower_face_apex") > cues.index("target_hold"):
            raise ValueError(f"V22 bridge violates eye -> brow -> lower-face choreography: {bridge.get('name')}")
        for frame in frames:
            nose_layers = [layer for layer in frame.get("layers", []) if layer.get("component_id") == nose_id]
            if len(nose_layers) != 1 or nose_layers[0].get("offset") != [0, 0]:
                raise ValueError(f"V22 bridge moves or omits locked nose identity: {bridge.get('name')}")
        total_frames += len(frames)
        bridge_records.append({"name": bridge.get("name"), "source": bridge.get("source"), "target": bridge.get("target"),
                               "frame_count": len(frames), "cues": cues})
    if total_frames != layout.get("bridge_frame_count") or total_frames != 72:
        raise ValueError("V22 total bridge frame coverage drifted")
    special_fallback = layout.get("special_event_fallback")
    expected_special_fallback = {"menu", "recording", "upgrade", "sleep", "charging", "error"}
    if layout.get("whole_source_pose_playback") not in (False, "forbidden") or \
            layout.get("full_face_replacement") not in (False, "forbidden") or \
            not isinstance(special_fallback, dict) or set(special_fallback) != expected_special_fallback or \
            any(value != "fail_closed" for value in special_fallback.values()):
        raise ValueError("V22 layout permits a forbidden fallback path")
    return {"component_count": len(components), "required_roles": sorted(required_roles), "nose_component_id": nose_id,
            "nose_policy": "identity_only_fixed_offset", "bridge_count": len(bridge_records),
            "frame_count": total_frames, "bridges": bridge_records}


def v37_wb55_component_parity(export_gate: dict[str, object],
                              profile_trace: dict[str, object],
                              profile_host: dict[str, object],
                              browser_preview: dict[str, object],
                              wb55_parity: dict[str, object]) -> dict[str, object]:
    scores = profile_trace.get("scores")
    browser_frames = browser_preview.get("frames")
    target_frames = wb55_parity.get("frames")
    export_lineage = export_gate.get("source_component_lineage")
    if export_gate.get("runtime", {}).get("resource_activated") is not False or \
            export_gate.get("runtime", {}).get("active_candidate_binding") != "forbidden" or \
            not isinstance(export_lineage, dict) or \
            len(export_lineage.get("v34_v35_carried_forward", [])) != 39 or \
            len(export_lineage.get("locked_v9_sleep", [])) != 6 or \
            export_gate.get("crig", {}).get("revision") != 37 or export_gate.get("crig", {}).get("component_count") != 45 or \
            profile_trace.get("runtime_resource_activated") is not False or \
            profile_trace.get("active_candidate_binding") != "forbidden_until_total_machine_audit_and_owner_review" or \
            profile_trace.get("component_sources") != {"v22_face": 37, "v37_merged_special": 45} or \
            profile_trace.get("max_component_mask_bytes") != 506 or \
            profile_host.get("component_count") != 82 or profile_host.get("score_count") != 5 or \
            profile_host.get("replayed_score_steps") != 17 or profile_host.get("max_component_mask_bytes") != 506 or \
            profile_host.get("runtime_resource_activated") is not False or \
            not isinstance(scores, list) or len(scores) != 5 or \
            not isinstance(browser_frames, list) or not isinstance(target_frames, list):
        raise ValueError("V37 WB55 profile, source export or preview activation boundary drifted")
    expected_counts = {"recording_input": 3, "bottom_connector_charging": 3,
                       "curious_question": 3, "alert_exclamation": 3, "sleepy_dream_cloud": 5}
    expected = []
    for score in scores:
        steps = score.get("steps") if isinstance(score, dict) else None
        name = score.get("name") if isinstance(score, dict) else None
        if not isinstance(name, str) or not isinstance(steps, list) or len(steps) != expected_counts.get(name):
            raise ValueError("V37 WB55 score no longer has its registered candidate steps")
        for index, step in enumerate(steps):
            layers = step.get("layers") if isinstance(step, dict) else None
            if not isinstance(layers, list) or not layers or len(layers) > 16:
                raise ValueError("V37 WB55 score layer count drifted")
            if not any(layer.get("component_id") == 4 and layer.get("offset") == [0, 0]
                       for layer in layers if isinstance(layer, dict)):
                raise ValueError("V37 WB55 score lost the fixed V9 nose identity")
            has_special = any(isinstance(layer, dict) and layer.get("component_id", 0) >= 500 for layer in layers)
            if (name == "sleepy_dream_cloud" and index == 0 and has_special) or \
                    (not (name == "sleepy_dream_cloud" and index == 0) and not has_special):
                raise ValueError("V37 score violates its registered component-entry choreography")
            expected.append((name, step.get("cue"), f"{name}-{index:02d}-{step.get('cue')}.pbm", step.get("duration_ms")))
    browser = [(frame.get("score"), frame.get("cue"), frame.get("pbm"), frame.get("duration_ms"))
               for frame in browser_frames if isinstance(frame, dict)]
    target = [(frame.get("score"), frame.get("cue"), frame.get("pbm"), frame.get("duration_ms"))
              for frame in target_frames if isinstance(frame, dict)]
    if len(expected) != 17 or browser != expected or target != expected or \
            browser_preview.get("frame_count") != 17 or wb55_parity.get("replayed_frame_count") != 17 or \
            wb55_parity.get("component_count") != 82 or wb55_parity.get("source_packs") != ["v22_face", "v37_merged_special"] or \
            wb55_parity.get("runtime_resource_activated") is not False or \
            wb55_parity.get("special_event_binding") != "forbidden_until_total_machine_audit_and_owner_review" or \
            browser_preview.get("active_candidate_binding") != "forbidden_until_total_machine_audit_and_owner_review":
        raise ValueError("browser/WB55 V37 component plan frame identity drifted")
    return {"score_count": len(scores), "frame_count": len(expected),
            "source_components": 82, "max_component_mask_bytes": 506,
            "comparison": "exact score/cue/PBM/duration sequence and host pixel replay",
            "sleepy_dream_cloud": "locked_v9_source_components_candidate_only"}


def v38_wb55_component_parity(export_gate: dict[str, object],
                              profile_trace: dict[str, object],
                              profile_host: dict[str, object],
                              browser_preview: dict[str, object],
                              wb55_parity: dict[str, object]) -> dict[str, object]:
    scores = profile_trace.get("scores")
    browser_frames = browser_preview.get("frames")
    target_frames = wb55_parity.get("frames")
    generated = export_gate.get("generated_function_state_components")
    menu_policy = profile_trace.get("menu_entry_policy")
    expected_counts = {"recording_input": 3, "bottom_connector_charging": 3, "curious_question": 3,
                       "alert_exclamation": 3, "sleepy_dream_cloud": 5, "menu_entry_notice": 3,
                       "upgrade_progress": 3, "error_caution": 3}
    if export_gate.get("runtime", {}).get("resource_activated") is not False or \
            export_gate.get("runtime", {}).get("active_candidate_binding") != "forbidden" or \
            len(export_gate.get("carried_v37_components", [])) != 45 or \
            not isinstance(generated, dict) or \
            [entry.get("component_id") for entry in generated.get("menu_entry", [])] != [545, 546, 547] or \
            [entry.get("component_id") for entry in generated.get("upgrade", [])] != [548, 549, 550] or \
            [entry.get("component_id") for entry in generated.get("error", [])] != [551, 552, 553, 554, 555, 556] or \
            export_gate.get("crig", {}).get("revision") != 38 or export_gate.get("crig", {}).get("component_count") != 57 or \
            export_gate.get("menu_entry_policy", {}).get("maximum_expression_duration_ms") != 500 or \
            export_gate.get("menu_entry_policy", {}).get("after_last_cue") != "withdraw_expression_rig_then_show_menu_ui" or \
            export_gate.get("menu_entry_policy", {}).get("persistent_menu_score") != "forbidden" or \
            profile_trace.get("runtime_resource_activated") is not False or \
            profile_trace.get("active_candidate_binding") != "forbidden_until_total_machine_audit_and_owner_review" or \
            profile_trace.get("component_sources") != {"v22_face": 37, "v38_merged_special": 57} or \
            profile_trace.get("max_component_mask_bytes") != 506 or \
            not isinstance(menu_policy, dict) or menu_policy.get("maximum_expression_duration_ms") != 500 or \
            menu_policy.get("after_last_cue") != "withdraw_expression_rig_then_show_menu_ui" or \
            menu_policy.get("persistent_menu_score") != "forbidden" or \
            menu_policy.get("entry_cue_state_scene") != "touch" or \
            menu_policy.get("menu_ui_owns_screen_after_last_cue") is not True or \
            profile_host.get("component_count") != 94 or profile_host.get("score_count") != 8 or \
            profile_host.get("replayed_score_steps") != 26 or profile_host.get("max_component_mask_bytes") != 506 or \
            profile_host.get("runtime_resource_activated") is not False or \
            not isinstance(scores, list) or len(scores) != 8 or \
            not isinstance(browser_frames, list) or not isinstance(target_frames, list):
        raise ValueError("V38 WB55 profile, source export or preview activation boundary drifted")
    expected = []
    for score in scores:
        name = score.get("name") if isinstance(score, dict) else None
        steps = score.get("steps") if isinstance(score, dict) else None
        withdraw = score.get("withdraw_expression_rig_after_last_cue") if isinstance(score, dict) else None
        if not isinstance(name, str) or not isinstance(steps, list) or len(steps) != expected_counts.get(name) or \
                withdraw is not (name == "menu_entry_notice"):
            raise ValueError("V38 score descriptor or Menu withdrawal policy drifted")
        total_duration = 0
        for index, step in enumerate(steps):
            layers = step.get("layers") if isinstance(step, dict) else None
            if not isinstance(layers, list) or not layers or len(layers) > 16 or \
                    not any(isinstance(layer, dict) and layer.get("component_id") == 4 and layer.get("offset") == [0, 0]
                            for layer in layers):
                raise ValueError("V38 score lost legal layers or the fixed V9 nose")
            has_special = any(isinstance(layer, dict) and layer.get("component_id", 0) >= 500 for layer in layers)
            if (name == "sleepy_dream_cloud" and index == 0 and has_special) or \
                    (not (name == "sleepy_dream_cloud" and index == 0) and not has_special):
                raise ValueError("V38 score violates registered source-component entry choreography")
            if name == "menu_entry_notice" and (step.get("cue") not in {"menu_grid_arrive", "menu_selection_confirm", "menu_entry_commit"} or
                                                 step.get("state_scene") != "touch"):
                raise ValueError("V38 Menu entry became a persistent menu expression")
            if name == "error_caution" and not {554, 555, 556}.issubset({layer.get("component_id") for layer in layers if isinstance(layer, dict)}):
                raise ValueError("V38 Error score lost source-derived brow or mouth components")
            total_duration += step.get("duration_ms", 0)
            expected.append((name, step.get("cue"), f"{name}-{index:02d}-{step.get('cue')}.pbm", step.get("duration_ms")))
        if name == "menu_entry_notice" and total_duration > 500:
            raise ValueError("V38 Menu entry exceeds the finite pre-UI cue budget")
    browser = [(frame.get("score"), frame.get("cue"), frame.get("pbm"), frame.get("duration_ms"))
               for frame in browser_frames if isinstance(frame, dict)]
    target = [(frame.get("score"), frame.get("cue"), frame.get("pbm"), frame.get("duration_ms"))
              for frame in target_frames if isinstance(frame, dict)]
    if len(expected) != 26 or browser != expected or target != expected or \
            browser_preview.get("frame_count") != 26 or wb55_parity.get("replayed_frame_count") != 26 or \
            wb55_parity.get("component_count") != 94 or wb55_parity.get("source_packs") != ["v22_face", "v38_merged_special"] or \
            wb55_parity.get("runtime_resource_activated") is not False or \
            wb55_parity.get("special_event_binding") != "forbidden_until_total_machine_audit_and_owner_review" or \
            browser_preview.get("active_candidate_binding") != "forbidden_until_total_machine_audit_and_owner_review":
        raise ValueError("browser/WB55 V38 component plan frame identity drifted")
    return {"score_count": len(scores), "frame_count": len(expected), "source_components": 94,
            "max_component_mask_bytes": 506, "comparison": "exact score/cue/PBM/duration sequence and host pixel replay",
            "menu_entry_notice": "three finite frames / 460ms / withdraws before Menu UI",
            "upgrade_progress": "source-derived arrow/progress components", "error_caution": "source-derived caution, brows and mouth"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", default="docs/validation/companion-v9-expression-total-machine-audit-20260720.json")
    args = parser.parse_args()

    if sha256(LOCKED_V9) != LOCKED_V9_SHA256:
        raise ValueError("locked V9 identity source hash drifted")
    if sha256(PROTECTED_OWNER_ACCEPTANCE) != PROTECTED_OWNER_ACCEPTANCE_SHA256:
        raise ValueError("protected owner acceptance hash drifted")
    v22_layout = read_json(V22_LAYOUT)
    if (v22_layout.get("locked_v9_source_sha256") != LOCKED_V9_SHA256 or
            v22_layout.get("runtime_resource_activated") is not False or
            v22_layout.get("active_candidate_binding") != "forbidden"):
        raise ValueError("V22 layout activation or lineage contract drifted")

    v22_target_gate = evidence(V22_TARGET_GATE)
    v22_router = evidence(V22_ROUTER)
    upper_gate = evidence(UPPER_GATE)
    special_export_gate = evidence(SPECIAL_EXPORT_GATE)
    special_target_mount = evidence(SPECIAL_TARGET_MOUNT)
    special_wb55_profile_trace = evidence(SPECIAL_WB55_PROFILE_TRACE)
    special_browser_preview = evidence(SPECIAL_BROWSER_PREVIEW)
    special_wb55_parity = evidence(SPECIAL_WB55_PARITY)
    v37_export_gate = evidence(V37_EXPORT_GATE)
    v37_wb55_profile_trace = evidence(V37_WB55_PROFILE_TRACE)
    v37_wb55_profile_host = evidence(V37_WB55_PROFILE_HOST)
    v37_browser_preview = evidence(V37_BROWSER_PREVIEW)
    v37_wb55_parity = evidence(V37_WB55_PARITY)
    v38_export_gate = evidence(V38_EXPORT_GATE)
    v38_wb55_profile_trace = evidence(V38_WB55_PROFILE_TRACE)
    v38_wb55_profile_host = evidence(V38_WB55_PROFILE_HOST)
    v38_browser_preview = evidence(V38_BROWSER_PREVIEW)
    v38_wb55_parity = evidence(V38_WB55_PARITY)
    router_steps = v22_router.get("session_visible_step_count")
    special_events = v22_router.get("unbound_product_states")
    if router_steps != 72 or v22_router.get("session_requires_visible_acknowledgement") is not True or \
            v22_router.get("session_min_post_refresh_hold_ms") != 750 or \
            v22_router.get("ordinary_affect_only") is not True or v22_router.get("bridge_count") != 10 or \
            not isinstance(special_events, list):
        raise ValueError("V22 refresh-acknowledged session evidence drifted")
    required_special_fail_closed = {"menu", "recording", "upgrade", "sleep", "charging", "error"}
    if set(special_events) != required_special_fail_closed:
        raise ValueError("V22 special fail-closed coverage drifted")
    if special_export_gate.get("runtime", {}).get("special_event_binding") != "forbidden_until_later_browser_target_component_plan_gate" or \
            special_target_mount.get("active_candidate_binding") != "forbidden":
        raise ValueError("special-decoration candidate is not fail-closed")
    special_parity = v37_wb55_component_parity(v37_export_gate, v37_wb55_profile_trace, v37_wb55_profile_host,
                                                v37_browser_preview, v37_wb55_parity)
    function_state_parity = v38_wb55_component_parity(v38_export_gate, v38_wb55_profile_trace, v38_wb55_profile_host,
                                                       v38_browser_preview, v38_wb55_parity)

    blockers = [
        "All candidate art and browser/WB55 component-plan/pixel gates pass, but no special candidate has human semantic or screen acceptance yet; runtime remains inactive until that review records an accepted result.",
    ]
    status = "GO_HUMAN_ACCEPTANCE_MACHINE_CLOSURE_COMPLETE"
    wba_portability = {
        "target": "future STM32WBA portability only; not the active STM32WB55 expression path",
        "adapter": rel(WBA_ASSET_ADAPTER),
        "state": "available" if WBA_ASSET_ADAPTER.is_file() else "unavailable_current_worktree_adapter_deleted",
        "blocking": False,
        "follow_up": "Replay the WBA portability host regression after the WBA adapter owning workstream restores or replaces its source.",
    }
    output = {
        "schema": "companion.v9_expression_total_machine_audit.v1",
        "status": status,
        "authority": ["COMP-REQ-187", "COMP-REQ-189", "COMP-REQ-190", "COMP-REQ-198", "COMP-REQ-229", "COMP-REQ-233", "COMP-REQ-239", "COMP-REQ-240"],
        "scope": "upper V9 expression system only; no panel target, driver, LUT, refresh, flash, or hardware claim",
        "protected": {
            "locked_v9": {"path": rel(LOCKED_V9), "sha256": LOCKED_V9_SHA256},
            "owner_acceptance": {"path": rel(PROTECTED_OWNER_ACCEPTANCE), "sha256": PROTECTED_OWNER_ACCEPTANCE_SHA256},
        },
        "daily_v22": {
            "target_gate": pass_status(v22_target_gate, "V22 target gate"),
            "router_session": pass_status(v22_router, "V22 router session"),
            "upper_gate": pass_status(upper_gate, "V22 upper gate"),
            "component_choreography": v22_component_choreography(v22_layout),
            "same_emotion_presence": {"refresh_acknowledged": True, "minimum_post_refresh_hold_ms": 750,
                                       "visible_component_steps": 72},
        },
        "special_candidate_sources": {
            "v34_v35_export_foundation": pass_status(special_export_gate, "V34/V35 special decoration export gate"),
            "v34_v35_target_asset_mount": pass_status(special_target_mount, "V34/V35 special decoration target asset mount"),
            "v34_v35_wb55_candidate_profile": pass_status(special_wb55_profile_trace, "V34/V35 special WB55 candidate profile"),
            "v34_v35_browser_component_preview": pass_status(special_browser_preview, "V34/V35 special browser component preview"),
            "v34_v35_wb55_component_pixel_parity": pass_status(special_wb55_parity, "V34/V35 special WB55 component parity"),
            "v37_sleep_export_gate": pass_status(v37_export_gate, "V37 sleepy-dream export gate"),
            "v37_wb55_candidate_profile": pass_status(v37_wb55_profile_trace, "V37 WB55 candidate profile"),
            "v37_wb55_profile_host": pass_status(v37_wb55_profile_host, "V37 WB55 profile host"),
            "v37_browser_component_preview": pass_status(v37_browser_preview, "V37 browser component preview"),
            "v37_wb55_component_pixel_parity": pass_status(v37_wb55_parity, "V37 WB55 component parity"),
            "v37_component_plan_parity": special_parity,
            "v38_function_state_export_gate": pass_status(v38_export_gate, "V38 function-state export gate"),
            "v38_wb55_candidate_profile": pass_status(v38_wb55_profile_trace, "V38 WB55 candidate profile"),
            "v38_wb55_profile_host": pass_status(v38_wb55_profile_host, "V38 WB55 profile host"),
            "v38_browser_component_preview": pass_status(v38_browser_preview, "V38 browser component preview"),
            "v38_wb55_component_pixel_parity": pass_status(v38_wb55_parity, "V38 WB55 component parity"),
            "v38_component_plan_parity": function_state_parity,
            "component_count": 57,
            "runtime_resource_activated": False,
            "active_candidate_binding": "forbidden",
        },
        "wba_portability_regression": wba_portability,
        "fail_closed": {"all_special_runtime_events": sorted(required_special_fail_closed),
                        "missing_source_score_events": [],
                        "candidate_only_unaccepted_events": ["recording", "charging", "sleep", "menu_entry", "upgrade", "error"],
                        "daily_substitution": "forbidden", "whole_face_card": "forbidden", "code_drawn_face": "forbidden"},
        "machine_checks_passed": [
            "locked V9 and protected acceptance hashes",
            "V22 eye/highlight/brow/mouth/cheek/nose component coverage",
            "V22 eye -> brow -> lower-face causal bridge ordering",
            "V22 nose identity-only fixed offset",
            "V22 10 directed bridges / 72 frames / refresh acknowledgement",
            "V34/V35 source component export, native-200 reassembly parity, CRIG CRC and recorded WBA55/WBA65 portability asset mount evidence",
            "V37 merges 39 byte-identical V34/V35 source masks with six registered locked-V9 sleepy components in a 45-mask external-NOR CRIG",
            "V37 inactive WB55 profile: 82 registered source components / five scores / seventeen browser-WB55 pixel-identical candidate frames / 506-byte source-mask scratch requirement",
            "V38 merges 45 byte-identical V37 source masks with twelve versioned imagegen Menu-entry/Upgrade/Error masks in a 57-mask external-NOR CRIG",
            "V38 inactive WB55 profile: 94 registered source components / eight scores / twenty-six browser-WB55 pixel-identical candidate frames / 506-byte source-mask scratch requirement",
            "Menu is a finite 460ms entry notice that withdraws before the actual Menu UI; generic MENU-state Rig synthesis remains fail-closed",
            "special fail-closed boundary",
        ],
        "machine_check_blockers": blockers,
        "human_acceptance_eligible": True,
        "next_required_machine_work": "Open the canonical Chinese aiw operator-prompt review for the native-200 component previews, with special attention to Menu entry withdrawing into the Menu UI, Upgrade readability, Error readability, source-preserved eye identity and absence of whole-face swaps. Keep all runtime bindings inactive until the selected human result is stored.",
        "non_claims": ["no_special_runtime_binding", "no_firmware_flash", "no_panel_or_driver_change", "no_human_acceptance"],
    }
    output_path = (ROOT / args.write).resolve()
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
