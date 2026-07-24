#!/usr/bin/env python3
"""Separate the moving V9 Daily preview from unbound special-pose art evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageSequence


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
DAILY_REPORT = ROOT / "docs/validation/companion-v9-expression-rig-daily-selected-state-current-moving-20260719.json"
DAILY_PLAYER = ROOT / (
    "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rendered-200x200/"
    "v9-expression-rig-daily-selected-state-player.html"
)
DAILY_GIF = ROOT / (
    "docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rendered-200x200/"
    "v9-expression-rig-daily-selected-state-preview.gif"
)
SPECIAL_EXPORT_GATE = ROOT / "docs/validation/companion-v18-v20-special-expression-component-export-gate-20260719.json"
SPECIAL_TRIAGE = ROOT / "docs/validation/companion-v18-v20-special-expression-owner-art-review-triage-20260719.json"
SPECIAL_FAIL_CLOSED = ROOT / "docs/validation/companion-v9-expression-choreographer-special-failclosed-20260719.json"
DEFAULT_WRITE = ROOT / "docs/validation/companion-v9-expression-preview-surfaces-20260719.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=Path, default=DEFAULT_WRITE)
    args = parser.parse_args()
    errors: list[str] = []

    add(errors, LOCKED_V9.is_file() and sha256(LOCKED_V9) == LOCKED_V9_SHA256,
        "locked V9 source hash drifted")
    daily = load_json(DAILY_REPORT)
    add(errors, daily.get("status") == "PASS_DYNAMIC_COMPONENT_PREVIEW_READY",
        "Daily preview report is not component-preview PASS")
    add(errors, daily.get("runtime_resource_activated") is False,
        "Daily preview must remain runtime inactive")
    choreography = daily.get("preview_choreography")
    add(errors, isinstance(choreography, dict) and choreography.get("scope") == "daily_selected_state",
        "Daily preview scope is not daily_selected_state")
    add(errors, isinstance(choreography, dict) and
        choreography.get("presentation_mode") == "state_bound_single_story_loop" and
        choreography.get("automatic_story_rotation") is False,
        "Daily preview rotates through state stories instead of holding the selected choreography")
    policy = choreography.get("intermediate_layer_policy") if isinstance(choreography, dict) else ""
    add(errors, isinstance(policy, str) and "registered component masks" in policy and
        "no full-face frame" in policy, "Daily preview does not prohibit whole-face animation")

    add(errors, DAILY_PLAYER.is_file(), "Daily component player is missing")
    player_text = DAILY_PLAYER.read_text(encoding="utf-8") if DAILY_PLAYER.is_file() else ""
    add(errors, "setTimeout" in player_text and '"stateBound": true' in player_text,
        "Daily player does not schedule state-bound animation")
    add(errors, "component" in player_text.lower(), "Daily player has no component-layer data")
    add(errors, "v9-expression-rig-state-matrix.png" not in player_text and ".pbm" not in player_text,
        "Daily player references an audit frame instead of component layers")

    add(errors, DAILY_GIF.is_file(), "Daily animated GIF is missing")
    gif_size = [0, 0]
    gif_frames = 0
    gif_loop: int | None = None
    if DAILY_GIF.is_file():
        with Image.open(DAILY_GIF) as image:
            gif_size = list(image.size)
            gif_frames = sum(1 for _ in ImageSequence.Iterator(image))
            raw_loop = image.info.get("loop")
            gif_loop = raw_loop if isinstance(raw_loop, int) else None
        add(errors, gif_size == [432, 470], "Daily GIF dimensions drifted")
        add(errors, gif_frames >= 14, "Daily GIF has too few frames to prove movement")
        add(errors, gif_loop == 0, "Daily GIF is not configured to replay continuously for review")

    special_export = load_json(SPECIAL_EXPORT_GATE)
    special_triage = load_json(SPECIAL_TRIAGE)
    special_fail_closed = load_json(SPECIAL_FAIL_CLOSED)
    add(errors, special_export.get("status") == "PASS_V18_V20_COMPLETE_SPECIAL_EXPRESSION_COMPONENT_EXPORT_GATE",
        "special-expression component source gate is not PASS")
    add(errors, special_export.get("runtime_resource_activated") is False and
        special_export.get("active_candidate_binding") == "forbidden",
        "special-expression components are unexpectedly bindable")
    add(errors, special_triage.get("status") == "OWNER_DIRECTION_RECORDED_PENDING_EXPLICIT_REFINEMENT" and
        special_triage.get("selection") == "需修改",
        "special-expression art review no longer records pending refinement")
    add(errors, special_triage.get("runtime_resource_activated") is False and
        special_triage.get("active_candidate_binding") == "forbidden",
        "special-expression owner triage permits a runtime binding")
    required_events = {"charging", "error", "menu_hold", "recording_active", "upgrade_active"}
    recorded_events = special_fail_closed.get("fail_closed_events")
    add(errors, special_fail_closed.get("status") == "PASS" and
        isinstance(recorded_events, list) and required_events <= set(recorded_events),
        "special-event fail-closed evidence is incomplete")
    add(errors, special_fail_closed.get("runtime_resource_activated") is False,
        "special-event fail-closed evidence claims a runtime activation")

    result = {
        "schema": "companion.v9_expression_preview_surfaces.v1",
        "status": "PASS_DYNAMIC_DAILY_PREVIEW_AND_STATIC_SPECIAL_ART_GATE" if not errors else
                  "FAIL_DYNAMIC_DAILY_PREVIEW_AND_STATIC_SPECIAL_ART_GATE",
        "locked_v9_source_sha256": LOCKED_V9_SHA256,
        "daily_preview": {
            "classification": "moving_component_preview",
            "report": rel(DAILY_REPORT),
            "player": rel(DAILY_PLAYER),
            "animated_gif": rel(DAILY_GIF),
            "gif_size": gif_size,
            "gif_frames": gif_frames,
            "gif_loop": gif_loop,
            "runtime_resource_activated": False,
            "whole_face_animation_forbidden": True,
        },
        "special_expression_art": {
            "classification": "static_source_art_pending_explicit_refinement",
            "component_export_gate": rel(SPECIAL_EXPORT_GATE),
            "owner_art_triage": rel(SPECIAL_TRIAGE),
            "event_fail_closed_evidence": rel(SPECIAL_FAIL_CLOSED),
            "owner_selection": "需修改",
            "active_candidate_binding": "forbidden",
            "runtime_resource_activated": False,
        },
        "errors": errors,
    }
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: Daily is a moving component preview; special poses remain static, unbound art evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
