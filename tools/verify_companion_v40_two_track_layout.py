#!/usr/bin/env python3
"""Gate the versioned V40 expression/function two-track source authority."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v2/candidate/two-track-layout.json"
V39_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v1/candidate/two-track-layout.json"
V40_EXPORT = ROOT / "docs/art/iterations/companion-pet-expression-v9-functional-decoration-rig-v2/candidate/functional-decoration-component-layout.json"
REPORT = ROOT / "docs/validation/companion-v40-two-track-layout-gate-20260720.json"
LOCKED = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
V22_IDS = set(range(1, 38))
FUNCTIONAL_IDS = set(range(557, 569))
MENU_IDS = {545, 546, 547}
SLEEP_IDS = {539, 540, 541, 542, 543, 544, 531, 532}
EXPRESSION_ACCENT_IDS = {512, 513, 514, 521, 522, 523}
QUARANTINED = {554, 555, 556}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path} must be an object")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def source_component_ids(layout: dict[str, Any], expected: int) -> set[int]:
    components = layout.get("components")
    require(isinstance(components, list) and len(components) == expected, "source component count drifted")
    ids = {entry.get("component_id") for entry in components if isinstance(entry, dict)}
    require(len(ids) == expected and all(isinstance(component_id, int) for component_id in ids),
            "source component namespace drifted")
    return {int(component_id) for component_id in ids}


def ids_from_frames(value: Any) -> set[int]:
    require(isinstance(value, list) and value, "track frames must be present")
    result: set[int] = set()
    for frame in value:
        require(isinstance(frame, list) and frame and all(isinstance(component_id, int) for component_id in frame),
                "track frame uses invalid component ids")
        result.update(frame)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--layout", type=Path, default=LAYOUT)
    parser.add_argument("--write", type=Path, default=REPORT)
    args = parser.parse_args()
    layout_path = args.layout.resolve()
    layout = load(layout_path)
    require(layout.get("schema") == "companion.v40_two_track_rig_layout.v1" and
            layout.get("status") == "CANDIDATE_TRACK_MODEL_VERSIONED_RUNTIME_INACTIVE" and
            layout.get("revision") == 40 and
            layout.get("locked_v9_source", {}).get("sha256") == LOCKED,
            "V40 identity or locked V9 authority drifted")

    authority = layout.get("source_authority")
    inherited = layout.get("inherited_expression_track")
    require(isinstance(authority, dict) and isinstance(inherited, dict), "source or inherited expression authority is missing")
    require(inherited.get("layout") == V39_LAYOUT.relative_to(ROOT).as_posix() and
            inherited.get("sha256") == sha256(V39_LAYOUT) and
            inherited.get("reuse_rule") == "V39 expression-track authority is byte-for-byte retained; V40 changes only functional decoration source masks.",
            "V40 must retain the V39 expression authority byte-for-byte")
    v22_authority = authority.get("v22_face_layout")
    v40_authority = authority.get("v40_special_source_layout")
    require(isinstance(v22_authority, dict) and isinstance(v40_authority, dict), "track source authority is incomplete")
    v22_path = ROOT / str(v22_authority.get("path", ""))
    v40_path = ROOT / str(v40_authority.get("path", ""))
    crig_path = ROOT / str(v40_authority.get("crig", ""))
    require(v22_path.is_file() and v40_path.is_file() and crig_path.is_file() and
            sha256(v22_path) == v22_authority.get("sha256") and
            sha256(v40_path) == v40_authority.get("sha256") and
            sha256(crig_path) == v40_authority.get("crig_sha256") and
            v40_path == V40_EXPORT,
            "V40 source authority hash drifted")
    require(source_component_ids(load(v22_path), 37) == V22_IDS and
            source_component_ids(load(v40_path), 69) == set(range(500, 569)),
            "V40 source component namespace changed")

    composition = layout.get("composition")
    require(isinstance(composition, dict) and composition.get("canvas") == "200x200_1bpp_white_is_one_msb" and
            composition.get("final_plan") == "deterministic_union(expression_track, functional_decoration_track)" and
            composition.get("maximum_layers") == 16 and composition.get("no_mask_synthesis") is True and
            composition.get("runtime_binding") == "forbidden_until_v40_machine_audit_and_owner_review",
            "V40 component-only composition contract drifted")

    expression = load(V39_LAYOUT).get("expression_track")
    require(isinstance(expression, dict) and expression.get("driven_only_by") ==
            ["emotion", "attention", "energy", "interaction_memory"] and set(expression.get("face_component_ids", [])) == V22_IDS,
            "retained V39 expression track must own only face-state inputs and V22 face components")
    performances = expression.get("performances")
    require(isinstance(performances, dict) and set(performances) ==
            {"calm_presence", "warm_presence", "curious_question", "alert_exclamation", "playful_presence", "sleepy_presence"},
            "retained expression performance vocabulary drifted")
    expression_ids: set[int] = set()
    for name, performance in performances.items():
        require(isinstance(performance, dict), "expression performance is invalid")
        if name == "sleepy_presence":
            used = ids_from_frames(performance.get("base_face_steps"))
            require(used == SLEEP_IDS | {1, 2, 3, 4, 5, 6, 7, 13, 14, 15, 16, 17},
                    "sleepy expression must reuse only registered locked-V9/V22 source components")
        else:
            base = performance.get("base_face")
            require(isinstance(base, list) and set(base).issubset(V22_IDS) and 4 in base,
                    "expression base face must keep V22 source identity and fixed nose")
            used = set(base)
            accents = performance.get("expression_owned_accent_steps", [])
            if accents:
                accent_ids = ids_from_frames(accents)
                require(accent_ids.issubset(EXPRESSION_ACCENT_IDS),
                        "expression accent cannot be a functional decoration")
                used.update(accent_ids)
        expression_ids.update(used)
    require(not expression_ids & QUARANTINED and not expression_ids & FUNCTIONAL_IDS,
            "expression track cannot inherit rejected V38 face mutation or V40 functional markers")

    functional = layout.get("functional_decoration_track")
    require(isinstance(functional, dict) and functional.get("driven_only_by") == ["functional_event"] and
            set(functional.get("allowed_component_ids", [])) == FUNCTIONAL_IDS,
            "functional track must be event-only and source-mask-only")
    events = functional.get("events")
    expected_events = {
        "recording_input": ({557, 558, 559}, [700, 420, 420]),
        "bottom_connector_charging": ({560, 561, 562}, [700, 420, 420]),
        "upgrade_progress": ({563, 564, 565}, [700, 420, 900]),
        "error_caution": ({566, 567, 568}, [260, 260, 1200]),
    }
    require(isinstance(events, dict) and set(events) == set(expected_events), "functional event vocabulary drifted")
    for name, (expected_ids, expected_durations) in expected_events.items():
        event = events[name]
        require(isinstance(event, dict) and ids_from_frames(event.get("frames")) == expected_ids and
                event.get("durations_ms") == expected_durations,
                f"functional event {name} drifted")
    require(not FUNCTIONAL_IDS & V22_IDS and not FUNCTIONAL_IDS & QUARANTINED,
            "functional track must not change face component selection")

    menu = layout.get("menu_entry_exception")
    require(isinstance(menu, dict) and menu.get("event") == "menu_entry_notice" and
            menu.get("state_scene") == "touch" and ids_from_frames(menu.get("frames")) == MENU_IDS and
            menu.get("durations_ms") == [140, 140, 180] and sum(menu["durations_ms"]) <= 500 and
            menu.get("after_last_cue") == "withdraw_expression_and_functional_tracks_then_show_menu_ui",
            "Menu must stay a finite pre-UI two-track withdrawal cue")
    require(set(layout.get("quarantined_rejected_v38_face_components", [])) == QUARANTINED,
            "rejected V38 function-driven face components must remain quarantined")
    unassigned = set(layout.get("unassigned_carried_v38_components_require_explicit_future_authority", []))
    known = expression_ids | FUNCTIONAL_IDS | MENU_IDS | QUARANTINED
    require(unassigned == set(range(500, 557)) - known and not unassigned & known,
            "every carried special source component needs explicit retained ownership or quarantine")

    report = {
        "schema": "companion.v40_two_track_layout_gate.v1",
        "status": "PASS_V40_TWO_TRACK_LAYOUT_RUNTIME_INACTIVE",
        "layout": layout_path.relative_to(ROOT).as_posix(),
        "locked_v9_source_sha256": LOCKED,
        "source_components": {"v22_face": 37, "v40_special_source": 69},
        "tracks": {"expression": sorted(expression_ids), "functional": sorted(FUNCTIONAL_IDS), "menu_entry": sorted(MENU_IDS)},
        "quarantined_rejected_v38_face_components": sorted(QUARANTINED),
        "menu_entry": "touch / three frames / 460ms / withdraw both tracks before Menu UI",
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden_until_v40_machine_audit_and_owner_review",
        "non_claims": ["no_v38_profile_promotion", "no_runtime_binding", "no_firmware_flash", "no_panel_or_driver_change", "no_human_acceptance"]
    }
    output = args.write.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("PASS: V40 retains the V39 expression track and replaces only functional decoration source masks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
