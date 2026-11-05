#!/usr/bin/env python3
"""Generate the exact upper contract for unresolved lower visual handoffs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


EXPORT_REL = Path(
    "docs/art/exports/companion-browser-visual-contract-comp-req-471"
)
VALIDATION_REL = Path(
    "docs/validation/companion-browser-visual-contract-comp-req-471"
)
PAGE_REL = Path(
    "docs/art/iterations/"
    "companion-pet-expression-v9-two-track-rig-v7/candidate/"
    "wb55-browser-parity-attempt-01/index.html"
)
PAGE_SHA = (
    "BAE21BCCC7BB5FAD4A0922D5E9C42FCB25EF58DD7B8102A7C72656F7B700CF5E"
)
STATE_TRANSITIONS_SHA = (
    "442F5A9E87988A3F8BE15ECC2A2500CA64537FA2B6DBD96F6FFDDD070DD7F918"
)
VISUAL_CONTRACT_SHA = (
    "E5C6B30D8BF317FC8321D82E087D3B46552B4523FD8B67FFF3E6ABA89AAE4260"
)
EXPANDED_ORACLE_SHA = (
    "20C270A332F7AD75FAED3C44C9AE3C1D789F7902ABA525C07B0B40F4266C5B2E"
)
UPPER_MACHINE_READY_SHA = (
    "EAD7000FEB32CD7915FEAD82A49D23FD66755412AEDFA53B4B7A264CABA3BB69"
)
LOWER_COMMIT = "4ddf9709034d307b333510c27e3e0a45c7ed6d15"
EXPECTED_GAPS = {
    "pointer_drag_center",
    "pointer_move",
    "early_up_cancel_blur_or_drag",
    "select_ui_assets",
}
DIRECTIONAL_GAZE_STATES = {
    "gaze_left",
    "gaze_up",
    "gaze_right",
    "gaze_down",
}
LOWER_SOURCE_PATHS = {
    "app/companion_pendant/epaper/companion_visual_runtime_adapter.c",
    "app/companion_pendant/epaper/r7_runtime_bridge_stm32wb.c",
    "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c",
    "tools/comp_req_472_visual_runtime_fixture.c",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes())


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not a JSON object")
    return value


def require_hash(
    path: Path,
    expected: str,
    repo_root: Path,
) -> dict[str, str]:
    observed = file_sha(path)
    if observed != expected:
        raise ValueError(
            f"hash mismatch for {path}: expected {expected}, observed {observed}"
        )
    return {
        "path": path.relative_to(repo_root).as_posix(),
        "sha256": observed,
    }


def transition_sources(index: int, event: str) -> list[dict[str, Any]]:
    page_sources = {
        "pointer_drag_center": [
            {
                "path": PAGE_REL.as_posix(),
                "line": 65,
                "symbol": "onUnifiedPointerMove",
                "evidence": (
                    "movement beyond 44 px cancels hold/tap and replaces the "
                    "single current expression gaze"
                ),
            }
        ],
        "pointer_move": [
            {
                "path": PAGE_REL.as_posix(),
                "line": 65,
                "symbol": "onUnifiedPointerMove",
                "evidence": (
                    "every active moved sample calls setExpressionGaze with "
                    "the current touch-derived direction"
                ),
            }
        ],
        "early_up_cancel_blur_or_drag": [
            {
                "path": PAGE_REL.as_posix(),
                "line": 63,
                "symbol": "cancelInteraction",
                "evidence": (
                    "cancel clears hold and returns the expression gaze to "
                    "the accepted center identity"
                ),
            },
            {
                "path": PAGE_REL.as_posix(),
                "line": 67,
                "symbol": "pointercancel/lostpointercapture/blur listeners",
                "evidence": "all cancellation surfaces converge on cleanup",
            },
        ],
        "select_ui_assets": [
            {
                "path": PAGE_REL.as_posix(),
                "line": 61,
                "symbol": "menuSelect",
                "evidence": (
                    "Device detail index 3 replaces the menu with the "
                    "accepted UI-assets expression surface"
                ),
            },
            {
                "path": PAGE_REL.as_posix(),
                "line": 57,
                "symbol": "renderIntegratedMenu",
                "evidence": (
                    "Device > UI assets exposes only Calm/Curious/Warm and "
                    "the menu return"
                ),
            },
        ],
    }
    return [
        {
            "path": (EXPORT_REL / "state-transitions.json").as_posix(),
            "json_pointer": f"/transitions/{index}",
            "event": event,
        },
        *page_sources[event],
    ]


def pair_contract(
    pair: dict[str, Any],
    frame_sha_by_state: dict[str, str],
    compatibility_by_pair: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    compatibility = compatibility_by_pair[pair["id"]]
    return {
        "id": pair["id"],
        "upper_source": {
            "path": (EXPORT_REL / "expanded-window-oracle.json").as_posix(),
            "json_pointer": f"/pairs/{pair['pair_index']}",
        },
        "from_state": pair["from_state"],
        "from_frame_sha256": frame_sha_by_state[pair["from_state"]],
        "to_state": pair["to_state"],
        "expected_next_frame_sha256": frame_sha_by_state[pair["to_state"]],
        "pixel_noop": bool(pair["pixel_noop"]),
        "classification": (
            "semantic_noop_state_commit"
            if pair["pixel_noop"]
            else "pixel_changing_transition"
        ),
        "expected_current_slice_sha256": pair["current_slice"]["sha256"],
        "expected_payload_bytes": pair["current_slice"]["payload_bytes"],
        "currently_realizable_lower_path": compatibility[
            "realizable_lower_path"
        ],
        "lower_mapping_evidence": compatibility[
            "pair_mapping_evidence"
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--compatibility", type=Path, required=True)
    parser.add_argument(
        "--expected-compatibility-sha256",
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    compatibility_path = (
        args.compatibility.resolve()
        if args.compatibility.is_absolute()
        else (repo_root / args.compatibility).resolve()
    )
    output_path = (
        args.output.resolve()
        if args.output.is_absolute()
        else (repo_root / args.output).resolve()
    )
    output_path.relative_to((repo_root / VALIDATION_REL).resolve())

    page_path = repo_root / PAGE_REL
    transitions_path = repo_root / EXPORT_REL / "state-transitions.json"
    visual_path = repo_root / EXPORT_REL / "visual-contract.json"
    oracle_path = repo_root / EXPORT_REL / "expanded-window-oracle.json"
    upper_ready_path = repo_root / VALIDATION_REL / "UPPER_MACHINE_READY.json"

    bindings = {
        "accepted_page": require_hash(page_path, PAGE_SHA, repo_root),
        "state_transitions": require_hash(
            transitions_path, STATE_TRANSITIONS_SHA, repo_root
        ),
        "visual_contract": require_hash(
            visual_path, VISUAL_CONTRACT_SHA, repo_root
        ),
        "expanded_oracle": require_hash(
            oracle_path, EXPANDED_ORACLE_SHA, repo_root
        ),
        "upper_machine_ready": require_hash(
            upper_ready_path, UPPER_MACHINE_READY_SHA, repo_root
        ),
        "compatibility": require_hash(
            compatibility_path,
            args.expected_compatibility_sha256.upper(),
            repo_root,
        ),
    }

    transitions = load_json(transitions_path)
    visual = load_json(visual_path)
    oracle = load_json(oracle_path)
    compatibility = load_json(compatibility_path)

    if compatibility.get("mode") != "comparison":
        raise ValueError("compatibility artifact is not comparison mode")
    if (
        compatibility.get("lower_binding", {}).get("resolved_commit")
        != LOWER_COMMIT
    ):
        raise ValueError("compatibility artifact lower commit mismatch")
    summary = compatibility.get("summary", {})
    if (
        summary.get("events", {}).get("realizable") != 17
        or summary.get("events", {}).get("mapping_missing") != 3
        or summary.get("events", {}).get("mapping_ambiguous") != 1
        or summary.get("pairs", {}).get("realizable") != 51
        or summary.get("pairs", {}).get("semantic_noop_realizable") != 8
        or summary.get("polarity_bridge_realizable") is not True
    ):
        raise ValueError("compatibility artifact corrected summary mismatch")

    transition_by_event = {
        item["event"]: (index, item)
        for index, item in enumerate(transitions["transitions"])
    }
    compatibility_by_event = {
        item["event"]: item
        for item in compatibility["event_compatibility"]
    }
    compatibility_by_pair = {
        item["id"]: item
        for item in compatibility["pair_compatibility"]
    }
    observed_gaps = {
        event
        for event, item in compatibility_by_event.items()
        if item["mapping_status"] != "mapped"
    }
    if observed_gaps != EXPECTED_GAPS:
        raise ValueError("compatibility event gap set mismatch")

    frame_sha_by_state = {
        item["id"]: item["raw_sha256"] for item in visual["frames"]
    }
    pairs_by_event: dict[str, list[dict[str, Any]]] = {}
    for item in oracle["pairs"]:
        pairs_by_event.setdefault(item["event"], []).append(item)

    specs = {
        "pointer_drag_center": {
            "why_unreachable": (
                "The adapter accepts POINTER_DRAG_CENTER at "
                "companion_visual_runtime_adapter.c:174, but exact production "
                "main.c:1789-1815 emits only left/right/up/down drag events; "
                "main.c:1839-1841 returns without enqueueing when the active "
                "contact resolves inside the center/slop region."
            ),
            "lower_evidence_locations": [
                "app/companion_pendant/epaper/"
                "companion_visual_runtime_adapter.c:170-177",
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/"
                "main.c:1789-1815",
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/"
                "main.c:1839-1841",
            ],
            "minimal_lower_mapping": (
                "On an active physical drag that has crossed the physical "
                "drag threshold and whose current target resolves to center, "
                "enqueue POINTER_DRAG_CENTER with GAZE_CENTER exactly once per "
                "replacement sample; do not import the browser 44 px guard."
            ),
        },
        "pointer_move": {
            "why_unreachable": (
                "Exact production main.c:1843-1860 continuously maps only four "
                "directional targets. Returning to center hits the early "
                "return at main.c:1839-1841, so all 20 directional-target "
                "pairs are realizable while all five center-target pairs are "
                "missing."
            ),
            "lower_evidence_locations": [
                "app/companion_pendant/epaper/"
                "companion_visual_runtime_adapter.c:166-169",
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/"
                "main.c:1823-1860",
            ],
            "minimal_lower_mapping": (
                "Resolve every active contact sample to one of five gaze "
                "states and enqueue POINTER_MOVE for that exact state. A "
                "center result must replace the previous direction, including "
                "the GAZE_CENTER -> GAZE_CENTER semantic no-op; preserve the "
                "existing physical threshold policy."
            ),
        },
        "early_up_cancel_blur_or_drag": {
            "why_unreachable": (
                "The adapter maps EARLY_UP_CANCEL_BLUR_OR_DRAG at "
                "companion_visual_runtime_adapter.c:179-185, but the exact "
                "production tree has no event-specific call site. Gesture "
                "NONE emits SETTLE at main.c:1782-1787 and directional "
                "release emits POINTER_UP_OR_CANCEL at main.c:1812-1815, "
                "neither proves hold-feedback cancellation identity."
            ),
            "lower_evidence_locations": [
                "app/companion_pendant/epaper/"
                "companion_visual_runtime_adapter.c:178-185",
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/"
                "main.c:1782-1787",
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/"
                "main.c:1812-1815",
            ],
            "minimal_lower_mapping": (
                "From physical HOLD_FEEDBACK_50, route early release, cancel, "
                "focus-loss equivalent, or drag cancellation to "
                "EARLY_UP_CANCEL_BLUR_OR_DRAG -> CENTERED_REST before menu "
                "completion. Use physical 650/3000 timing, not browser 700 ms."
            ),
        },
        "select_ui_assets": {
            "why_unreachable": (
                "The adapter accepts SELECT_UI_ASSETS at "
                "companion_visual_runtime_adapter.c:210-213, but the "
                "production menu switch at main.c:3024-3045 has Device, "
                "Preferences, Phone, Record, and Home only. No Device > UI "
                "assets action reaches MENU_DEVICE_UI_ASSETS."
            ),
            "lower_evidence_locations": [
                "app/companion_pendant/epaper/"
                "companion_visual_runtime_adapter.c:206-213",
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/"
                "main.c:3022-3049",
            ],
            "minimal_lower_mapping": (
                "Expose a deterministic Device > UI assets menu result and "
                "map it to SELECT_UI_ASSETS with "
                "MENU_DEVICE_UI_ASSETS; its return must use the existing menu "
                "return identity and must not create a second visual route."
            ),
        },
    }

    handoffs = []
    for event in (
        "pointer_drag_center",
        "pointer_move",
        "early_up_cancel_blur_or_drag",
        "select_ui_assets",
    ):
        transition_index, transition = transition_by_event[event]
        upper_pairs = pairs_by_event[event]
        contracts = [
            pair_contract(item, frame_sha_by_state, compatibility_by_pair)
            for item in upper_pairs
        ]
        compatible = compatibility_by_event[event]
        row: dict[str, Any] = {
            "event": event,
            "event_index": transition_index,
            "upper_source_locations": transition_sources(
                transition_index, event
            ),
            "precondition_states": transition.get(
                "from_any", [transition.get("from")]
            ),
            "expected_next_states": transition.get(
                "to_any", [transition.get("to")]
            ),
            "guard": transition.get("guard", "always"),
            "effect": transition["effect"],
            "mapping_status_at_lower_commit": compatible["mapping_status"],
            "currently_realizable_pair_count": compatible[
                "pair_realizable_count"
            ],
            "required_pair_count": compatible["pair_total_count"],
            "why_current_lower_is_unreachable": specs[event][
                "why_unreachable"
            ],
            "lower_evidence_locations": specs[event][
                "lower_evidence_locations"
            ],
            "minimal_lower_mapping": specs[event]["minimal_lower_mapping"],
            "pairs": contracts,
        }
        if event == "pointer_move":
            directional_pairs = [
                item
                for item in contracts
                if item["to_state"] in DIRECTIONAL_GAZE_STATES
            ]
            center_pairs = [
                item for item in contracts if item["to_state"] == "gaze_center"
            ]
            if (
                len(directional_pairs) != 20
                or not all(
                    item["currently_realizable_lower_path"]
                    for item in directional_pairs
                )
                or len(center_pairs) != 5
                or any(
                    item["currently_realizable_lower_path"]
                    for item in center_pairs
                )
            ):
                raise ValueError("pointer_move 20/25 split mismatch")
            row["pair_partition"] = {
                "directional_target_realizable": {
                    "count": len(directional_pairs),
                    "ids": [item["id"] for item in directional_pairs],
                    "pixel_noop_count": sum(
                        item["pixel_noop"] for item in directional_pairs
                    ),
                },
                "center_target_missing": {
                    "count": len(center_pairs),
                    "ids": [item["id"] for item in center_pairs],
                    "pixel_noop_count": sum(
                        item["pixel_noop"] for item in center_pairs
                    ),
                },
            }
        handoffs.append(row)

    lower_sources = [
        item
        for item in compatibility["lower_binding"]["source_blobs"]
        if item["path"] in LOWER_SOURCE_PATHS
    ]
    if {item["path"] for item in lower_sources} != LOWER_SOURCE_PATHS:
        raise ValueError("required lower source binding missing")

    artifact = {
        "schema": "companion.lower-handoff-upper-contract.v1",
        "requirements": ["COMP-REQ-477", "COMP-REQ-479", "COMP-REQ-488"],
        "status": "NO_GO_LOWER_HANDOFFS_REQUIRED",
        "scope": "upper_owned_read_only_lower_handoff",
        "accepted_upper_bindings": bindings,
        "lower_read_only_binding": {
            "commit": LOWER_COMMIT,
            "commit_object": compatibility["lower_binding"]["commit_object"],
            "source_blobs": lower_sources,
        },
        "contract_summary": {
            "handoff_count": 4,
            "event_rows_realizable": "17/21",
            "expanded_pairs_realizable": "51/59",
            "semantic_noops_realizable": "8/10",
            "polarity_bridge_realizable": True,
            "polarity_is_not_a_mapping_blocker": True,
            "missing_events": [
                "early_up_cancel_blur_or_drag",
                "pointer_drag_center",
                "select_ui_assets",
            ],
            "ambiguous_events": ["pointer_move"],
            "missing_pair_count": 8,
            "missing_pointer_move_center_pair_count": 5,
        },
        "browser_physical_boundary": {
            "browser_guards_are_authoring_only": {
                "double_tap_ms": 350,
                "hold_ms": 700,
                "drag_threshold_px": 44,
            },
            "physical_mapping_remains_owned_by_lower": {
                "double_tap_ms": 650,
                "double_tap_move_px_max": 40,
                "hold_feedback_ms": 650,
                "menu_entry_ms": 3000,
            },
        },
        "handoffs": handoffs,
        "completion_rule": (
            "The joint gate remains NO_GO until production call-edge evidence "
            "realizes all 21 events, all 59 pairs, and all 10 semantic no-ops. "
            "Adapter enum or fixture-only coverage is insufficient."
        ),
        "side_effect_counters": {
            "execute": 0,
            "server": 0,
            "browser": 0,
            "prompt": 0,
            "popup": 0,
            "hardware": 0,
            "lower_write": 0,
            "registry_write": 0,
            "platform_write": 0,
            "production_write": 0,
            "push": 0,
            "upper_artifact_write": 1,
        },
        "generator": {
            "path": Path(__file__).resolve().relative_to(repo_root).as_posix(),
            "sha256": file_sha(Path(__file__).resolve()),
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_bytes(artifact))
    print(
        json.dumps(
            {
                "status": artifact["status"],
                "handoffs": len(handoffs),
                "artifact_sha256": file_sha(output_path),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
