#!/usr/bin/env python3
"""Verify COMP-REQ-789 component-staggered life frames from the final PBM pack."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


FAMILIES = (
    "calm", "curious", "delighted", "warm", "playful",
    "sleepy", "bashful", "thoughtful", "focused", "alert",
)
NON_SLEEPY_FAMILIES = tuple(family for family in FAMILIES if family != "sleepy")
PBM_HEADER = b"P4\n200 200\n"
EXPECTED_CHOREOGRAPHY = (
    "eyes_lead_then_brows_then_lower_face_then_ornament_then_authored_settle"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-pack-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def read_frame(path: Path) -> bytes:
    value = path.read_bytes()
    if not value.startswith(PBM_HEADER) or len(value) != len(PBM_HEADER) + 5000:
        raise ValueError(f"invalid 200x200 P4 PBM: {path}")
    return value[len(PBM_HEADER):]


def pixel(frame: bytes, x: int, y: int) -> int:
    return (frame[y * 25 + x // 8] >> (7 - x % 8)) & 1


def component_at(x: int, y: int) -> str:
    if 30 <= x < 175 and 60 <= y < 93:
        return "brows"
    if 35 <= x < 165 and 93 <= y < 145:
        return "eyes"
    if 25 <= x < 181 and 145 <= y < 190:
        return "lower_face"
    if 16 <= y < 93 and (y < 60 or x < 36 or x >= 164):
        return "ornament"
    return "outside"


def frame_diff(previous: bytes, current: bytes) -> dict[str, int]:
    counts = {
        "brows": 0,
        "eyes": 0,
        "lower_face": 0,
        "ornament": 0,
        "outside": 0,
    }
    for y in range(200):
        for x in range(200):
            if pixel(previous, x, y) != pixel(current, x, y):
                counts[component_at(x, y)] += 1
    return counts


def is_isolated(diff: dict[str, int], component: str) -> bool:
    return diff[component] > 0 and all(
        count == 0 for name, count in diff.items() if name != component
    )


def main() -> int:
    args = parse_args()
    manifest_bytes = args.source_pack_manifest.read_bytes()
    manifest = json.loads(manifest_bytes)
    source_root = args.source_pack_manifest.resolve().parent
    life_states = [state for state in manifest["states"] if state.get("kind") == "life"]
    rows: dict[str, dict[str, object]] = {}

    for family in FAMILIES:
        states = [state for state in life_states if state.get("family") == family]
        previous = None
        elapsed_ms = 0
        events: list[dict[str, object]] = []
        for state in states:
            frame = read_frame(source_root / state["pbm_file"])
            if previous is not None:
                diff = frame_diff(previous, frame)
                if any(diff.values()):
                    events.append({
                        "at_ms": elapsed_ms,
                        "episode": state["action_episode"],
                        "action": state["life_action"],
                        "phase": state["phase"],
                        "stage": state.get("component_stage"),
                        "diff": diff,
                    })
            elapsed_ms += int(state.get("dwell_commits", 1)) * 480
            previous = frame

        first_60s = [event for event in events if int(event["at_ms"]) < 60_000]
        isolated = {
            component: sum(
                is_isolated(event["diff"], component) for event in first_60s
            )
            for component in ("brows", "eyes", "lower_face", "ornament")
        }
        stage_isolation_failures = []
        expected_by_stage = {
            "eyes_lead": "eyes",
            "brows_reply": "brows",
            "lower_face_reply": "lower_face",
            "ornament_follow": "ornament",
        }
        for event in events:
            component = expected_by_stage.get(event["stage"])
            if component and not is_isolated(event["diff"], component):
                stage_isolation_failures.append({
                    "episode": event["episode"],
                    "phase": event["phase"],
                    "stage": event["stage"],
                    "diff": event["diff"],
                })
        rows[family] = {
            "state_count": len(states),
            "timeline_ms": elapsed_ms,
            "events_first_60s": len(first_60s),
            "isolated_events_first_60s": isolated,
            "stage_isolation_failure_count": len(stage_isolation_failures),
            "stage_isolation_failures": stage_isolation_failures[:8],
            "sample_events": first_60s[:12],
        }

    checks = {
        "source_pack_pass": manifest.get("status") == "PASS",
        "strict_200x200_1bpp": all(
            state.get("gray_input_pixels") == 0 for state in manifest["states"]
        ),
        "component_choreography_declared": (
            manifest.get("invariants", {}).get("life_component_choreography")
            == EXPECTED_CHOREOGRAPHY
        ),
        "ten_families_present": all(rows[family]["state_count"] > 0 for family in FAMILIES),
        "non_sleepy_timelines_cover_60s": all(
            rows[family]["timeline_ms"] >= 60_000 for family in NON_SLEEPY_FAMILIES
        ),
        "eyes_brows_lower_each_move_twice_in_60s": all(
            rows[family]["isolated_events_first_60s"]["eyes"] >= 2
            and rows[family]["isolated_events_first_60s"]["brows"] >= 2
            and rows[family]["isolated_events_first_60s"]["lower_face"] >= 2
            for family in NON_SLEEPY_FAMILIES
        ),
        "ornament_moves_independently_in_60s": all(
            rows[family]["isolated_events_first_60s"]["ornament"] >= 1
            for family in NON_SLEEPY_FAMILIES
        ),
        "all_staged_events_are_component_isolated": all(
            rows[family]["stage_isolation_failure_count"] == 0 for family in FAMILIES
        ),
    }
    status = "MACHINE_READY" if all(checks.values()) else "NO_GO"
    result = {
        "schema": "companion.comp_req_789.component_life.v1",
        "status": status,
        "source_pack_manifest": str(args.source_pack_manifest),
        "source_pack_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest().upper(),
        "choreography": EXPECTED_CHOREOGRAPHY,
        "checks": checks,
        "families": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if status == "MACHINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
