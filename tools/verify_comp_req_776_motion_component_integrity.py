"""Audit facial-component continuity across every expression and life frame.

This is intentionally a semantic audit.  The generic full-frame completeness
check catches byte/row/staging truncation; this verifier catches the subtler
failure seen by the owner where a motion transform erased part of an eye or
opened one of its white highlights to the background.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / (
    ".cache/validation/comp776-component-clip-fix-20260812/"
    "source-pack-5059/source-pack-manifest.json"
)
OUTPUT = ROOT / (
    ".cache/validation/comp776-component-clip-fix-20260812/"
    "MOTION_COMPONENT_INTEGRITY.json"
)
ROW_BYTES = 25
FRAME_BYTES = 5000
FAMILY_RE = re.compile(r"(?:expression|life)_([^_]+)")
AWAKE_FAMILIES = {
    "alert", "bashful", "calm", "curious", "delighted",
    "focused", "playful", "thoughtful", "warm",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def read_p4(root: Path, row: dict[str, object]) -> bytearray:
    data = (root / str(row["pbm_file"])).read_bytes()
    first = data.find(b"\n")
    second = data.find(b"\n", first + 1)
    frame = data[second + 1 :]
    if data[:first] != b"P4" or data[first + 1 : second].split() != [b"200", b"200"]:
        raise ValueError(f"invalid PBM geometry: {row['id']}")
    if len(frame) != FRAME_BYTES:
        raise ValueError(f"invalid PBM payload: {row['id']}")
    return bytearray(frame)


def black(frame: bytes | bytearray, x: int, y: int) -> bool:
    return bool(frame[y * ROW_BYTES + x // 8] & (0x80 >> (x & 7)))


def set_white(frame: bytearray, x: int, y: int) -> None:
    frame[y * ROW_BYTES + x // 8] &= ~(0x80 >> (x & 7))


def black_components(frame: bytes | bytearray) -> list[dict[str, object]]:
    seen: set[tuple[int, int]] = set()
    result: list[dict[str, object]] = []
    for y in range(16, 180):
        for x in range(10, 190):
            if not black(frame, x, y) or (x, y) in seen:
                continue
            pending = [(x, y)]
            seen.add((x, y))
            points: list[tuple[int, int]] = []
            while pending:
                cx, cy = pending.pop()
                points.append((cx, cy))
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    point = (cx + dx, cy + dy)
                    if (
                        10 <= point[0] < 190
                        and 16 <= point[1] < 180
                        and point not in seen
                        and black(frame, *point)
                    ):
                        seen.add(point)
                        pending.append(point)
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            result.append({
                "pixels": len(points),
                "bounds": [min(xs), min(ys), max(xs), max(ys)],
                "points": points,
            })
    return result


def eye_components(
    frame: bytes | bytearray,
    family: str,
    components: list[dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    candidates = []
    for component in components if components is not None else black_components(frame):
        x0, y0, x1, y1 = component["bounds"]
        if family == "sleepy":
            is_left = 45 <= x0 <= 50 and 75 <= x1 <= 80
            is_right = 120 <= x0 <= 125 and 150 <= x1 <= 155
            if (is_left or is_right) and 105 <= y0 <= 112 and 118 <= y1 <= 122:
                candidates.append(component)
        else:
            is_left = 40 <= x0 <= 45 and 72 <= x1 <= 77
            is_right = 123 <= x0 <= 128 and 156 <= x1 <= 160
            if (is_left or is_right) and 90 <= y0 <= 96 and 136 <= y1 <= 139:
                candidates.append(component)
    return sorted(candidates, key=lambda row: int(row["bounds"][0]))


def signature(eyes: list[dict[str, object]]) -> tuple[tuple[int, int, int, int, int], ...]:
    return tuple(
        (int(eye["pixels"]), *(int(value) for value in eye["bounds"]))
        for eye in eyes
    )


def enclosed_white_regions(
    frame: bytes | bytearray, bounds: list[int]
) -> list[list[tuple[int, int]]]:
    x0, y0, x1, y1 = (int(value) for value in bounds)
    seen: set[tuple[int, int]] = set()
    enclosed: list[list[tuple[int, int]]] = []
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if black(frame, x, y) or (x, y) in seen:
                continue
            pending = [(x, y)]
            seen.add((x, y))
            points: list[tuple[int, int]] = []
            touches_edge = False
            while pending:
                cx, cy = pending.pop()
                points.append((cx, cy))
                touches_edge |= cx in (x0, x1) or cy in (y0, y1)
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    point = (cx + dx, cy + dy)
                    if (
                        x0 <= point[0] <= x1
                        and y0 <= point[1] <= y1
                        and point not in seen
                        and not black(frame, *point)
                    ):
                        seen.add(point)
                        pending.append(point)
            if not touches_edge:
                enclosed.append(points)
    return enclosed


def analyze_frame(frame: bytearray, family: str) -> dict[str, object]:
    components = black_components(frame)
    eyes = eye_components(frame, family, components)
    eye_holes = [
        sorted(len(region) for region in enclosed_white_regions(frame, eye["bounds"]))
        for eye in eyes
    ]
    forbidden_panel_edge = any(
        black(frame, x, y)
        for y in range(16, 200)
        for x in (0, 199)
    ) or any(black(frame, x, 199) for x in range(200))
    return {
        "eye_signature": signature(eyes),
        "eye_holes": eye_holes,
        "forbidden_panel_edge": forbidden_panel_edge,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    rows = [row for row in manifest["states"] if row["kind"] in ("expression", "life")]
    signatures: dict[str, set[tuple[tuple[int, int, int, int, int], ...]]] = defaultdict(set)
    hole_signatures: dict[str, set[tuple[tuple[int, ...], ...]]] = defaultdict(set)
    state_failures: list[dict[str, object]] = []
    family_counts: dict[str, int] = defaultdict(int)
    frames: dict[str, bytearray] = {}

    for row in rows:
        match = FAMILY_RE.match(str(row["id"]))
        if not match:
            state_failures.append({"id": row["id"], "reason": "family_parse"})
            continue
        family = match.group(1)
        frame = read_p4(args.manifest.parent, row)
        frames[str(row["id"])] = frame
        result = analyze_frame(frame, family)
        family_counts[family] += 1
        signatures[family].add(result["eye_signature"])
        hole_signatures[family].add(tuple(tuple(holes) for holes in result["eye_holes"]))
        expected_eye_count = 2
        if len(result["eye_signature"]) != expected_eye_count:
            state_failures.append({"id": row["id"], "reason": "eye_count", "actual": len(result["eye_signature"])})
        if family in AWAKE_FAMILIES and (
            len(result["eye_holes"]) != 2
            or any(len(holes) != 2 for holes in result["eye_holes"])
        ):
            state_failures.append({"id": row["id"], "reason": "eye_highlights", "actual": result["eye_holes"]})
        if result["forbidden_panel_edge"]:
            state_failures.append({"id": row["id"], "reason": "component_touches_forbidden_panel_edge"})

    # Negative fixtures prove the audit rejects both failure shapes instead of
    # merely approving the current pack.
    fixture_id = "expression_bashful_v0_0_hold"
    fixture = bytearray(frames[fixture_id])
    fixture_eyes = eye_components(fixture, "bashful")
    for x, y in fixture_eyes[0]["points"]:
        if y == int(fixture_eyes[0]["bounds"][3]):
            set_white(fixture, x, y)
    row_cut_rejected = signature(eye_components(fixture, "bashful")) not in signatures["bashful"]

    opened = bytearray(frames[fixture_id])
    left_eye = eye_components(opened, "bashful")[0]
    primary = max(enclosed_white_regions(opened, left_eye["bounds"]), key=len)
    start = min(primary, key=lambda point: point[1])
    for y in range(int(left_eye["bounds"][1]), start[1] + 1):
        set_white(opened, start[0], y)
    opened_holes = analyze_frame(opened, "bashful")["eye_holes"]
    baseline_holes = analyze_frame(frames[fixture_id], "bashful")["eye_holes"]
    open_highlight_rejected = opened_holes != baseline_holes

    expected_families = AWAKE_FAMILIES | {"sleepy"}
    checks = {
        "all_expression_and_life_states_audited": len(rows) == 1587,
        "all_ten_families_present": set(family_counts) == expected_families,
        "two_complete_eye_components_in_every_state": not any(
            failure["reason"] == "eye_count" for failure in state_failures
        ),
        "awake_highlights_remain_enclosed_and_complete": not any(
            failure["reason"] == "eye_highlights" for failure in state_failures
        ),
        "highlight_shapes_are_stable_within_each_awake_family": all(
            len(hole_signatures[family]) == 1 for family in AWAKE_FAMILIES
        ),
        "eye_silhouette_is_stable_within_each_family": all(
            len(signatures[family]) == 1 for family in expected_families
        ),
        "ornaments_and_face_components_have_safe_crop_clearance": not any(
            failure["reason"] == "component_touches_forbidden_panel_edge"
            for failure in state_failures
        ),
        "negative_fixture_rejects_missing_eye_row": row_cut_rejected,
        "negative_fixture_rejects_open_highlight": open_highlight_rejected,
    }
    report = {
        "schema": "companion.comp_req_776.motion_component_integrity.v1",
        "status": "MACHINE_READY" if all(checks.values()) else "NO_GO",
        "checks": checks,
        "coverage": {
            "states": len(rows),
            "families": dict(sorted(family_counts.items())),
            "unique_eye_signatures_per_family": {
                family: len(values) for family, values in sorted(signatures.items())
            },
            "unique_highlight_signatures_per_awake_family": {
                family: len(hole_signatures[family]) for family in sorted(AWAKE_FAMILIES)
            },
            "failure_count": len(state_failures),
            "failures": state_failures[:25],
        },
        "identity": {
            "manifest_sha256": sha256(args.manifest),
            "page_sha256": manifest["source"]["page_sha256"],
        },
        "mutation_tests": {
            "missing_eye_row_rejected": row_cut_rejected,
            "open_highlight_rejected": open_highlight_rejected,
        },
        "hardware_contact": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "MACHINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
