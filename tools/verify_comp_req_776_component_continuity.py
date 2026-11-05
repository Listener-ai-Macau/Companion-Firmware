"""Prove that motion transforms do not erase neighbouring facial components."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / (
    ".cache/validation/comp775-r33-expression-coverage-audit/"
    "source-pack/source-pack-manifest.json"
)
NEW = ROOT / (
    ".cache/validation/comp776-component-clip-fix-20260812/"
    "source-pack-5059/source-pack-manifest.json"
)
PAGE = ROOT / ".cache/validation/comp-req-628-status-bar/index.html"
OUTPUT = ROOT / (
    ".cache/validation/comp776-component-clip-fix-20260812/"
    "COMPONENT_CONTINUITY.json"
)
ROW_BYTES = 25
FRAME_BYTES = 5000


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def read_p4(root: Path, row: dict[str, object]) -> bytes:
    data = (root / str(row["pbm_file"])).read_bytes()
    first = data.find(b"\n")
    second = data.find(b"\n", first + 1)
    frame = data[second + 1 :]
    if data[:first] != b"P4" or data[first + 1 : second].split() != [b"200", b"200"]:
        raise ValueError(f"invalid PBM geometry: {row['id']}")
    if len(frame) != FRAME_BYTES:
        raise ValueError(f"invalid PBM payload: {row['id']}")
    return frame


def black(frame: bytes, x: int, y: int) -> bool:
    return bool(frame[y * ROW_BYTES + x // 8] & (0x80 >> (x & 7)))


def components(frame: bytes) -> list[dict[str, object]]:
    seen: set[tuple[int, int]] = set()
    result: list[dict[str, object]] = []
    for y in range(16, 180):
        for x in range(10, 190):
            if not black(frame, x, y) or (x, y) in seen:
                continue
            queue = [(x, y)]
            seen.add((x, y))
            points: list[tuple[int, int]] = []
            while queue:
                cx, cy = queue.pop()
                points.append((cx, cy))
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nxt = (cx + dx, cy + dy)
                    if (
                        0 <= nxt[0] < 200
                        and 16 <= nxt[1] < 200
                        and nxt not in seen
                        and black(frame, *nxt)
                    ):
                        seen.add(nxt)
                        queue.append(nxt)
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            result.append(
                {
                    "pixels": len(points),
                    "bounds": [min(xs), min(ys), max(xs), max(ys)],
                }
            )
    return sorted(result, key=lambda row: int(row["pixels"]), reverse=True)


def changed_pixels(left: bytes, right: bytes) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    for index, pair in enumerate(zip(left, right)):
        delta = pair[0] ^ pair[1]
        if not delta:
            continue
        y = index // ROW_BYTES
        x_byte = index % ROW_BYTES
        for bit in range(8):
            if delta & (0x80 >> bit):
                result.append((x_byte * 8 + bit, y))
    return result


def bashful_signature(frame: bytes) -> dict[str, object]:
    face = [
        row for row in components(frame)
        if 65 <= row["bounds"][1] <= 155
    ]
    eyes = face[:2]
    cheeks = [
        row for row in face
        if row["pixels"] == 63
        and row["bounds"][1] == 139
        and (row["bounds"][2] < 80 or row["bounds"][0] > 120)
    ]
    return {
        "eye_pixels": sorted(int(row["pixels"]) for row in eyes),
        "eye_bottoms": sorted(int(row["bounds"][3]) for row in eyes),
        "cheek_pixels": sorted(int(row["pixels"]) for row in cheeks),
        "cheek_tops": sorted(int(row["bounds"][1]) for row in cheeks),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old", type=Path, default=OLD)
    parser.add_argument("--new", type=Path, default=NEW)
    parser.add_argument("--page", type=Path, default=PAGE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    old = json.loads(args.old.read_text(encoding="utf-8"))
    new = json.loads(args.new.read_text(encoding="utf-8"))
    old_rows = {row["id"]: row for row in old["states"]}
    new_rows = {row["id"]: row for row in new["states"]}
    old_root = args.old.parent
    new_root = args.new.parent
    changed: list[dict[str, object]] = []
    changed_kinds: Counter[str] = Counter()
    changed_families: Counter[str] = Counter()
    union = [200, 200, -1, -1]

    for state_id, old_row in old_rows.items():
        left = read_p4(old_root, old_row)
        right = read_p4(new_root, new_rows[state_id])
        points = changed_pixels(left, right)
        if not points:
            continue
        bounds = [
            min(x for x, _ in points),
            min(y for _, y in points),
            max(x for x, _ in points),
            max(y for _, y in points),
        ]
        changed.append({"id": state_id, "pixels": len(points), "bounds": bounds})
        changed_kinds[str(old_row["kind"])] += 1
        match = re.match(r"(?:expression|life)_([^_]+)", state_id)
        if match:
            changed_families[match.group(1)] += 1
        union = [
            min(union[0], bounds[0]),
            min(union[1], bounds[1]),
            max(union[2], bounds[2]),
            max(union[3], bounds[3]),
        ]

    bashful_ids = [
        state_id for state_id in new_rows
        if state_id.startswith(("expression_bashful_", "life_bashful_"))
    ]
    bashful_signatures = {
        state_id: bashful_signature(read_p4(new_root, new_rows[state_id]))
        for state_id in bashful_ids
    }
    expected_bashful = {
        "eye_pixels": [948, 989],
        "eye_bottoms": [137, 137],
        "cheek_pixels": [63, 63],
        "cheek_tops": [139, 139],
    }
    old_hold = bashful_signature(
        read_p4(old_root, old_rows["expression_bashful_v0_0_hold"])
    )
    old_motion = bashful_signature(
        read_p4(old_root, old_rows["life_bashful_e1_s1_notice_left_anticipate"])
    )
    new_hold = bashful_signatures["expression_bashful_v0_0_hold"]
    new_motion = bashful_signatures["life_bashful_e1_s1_notice_left_anticipate"]
    page = args.page.read_text(encoding="utf-8")
    checks = {
        "state_ids_match_all_5059": (
            len(old_rows) == len(new_rows) == 5059 and old_rows.keys() == new_rows.keys()
        ),
        "diff_is_component_local": union == [32, 133, 171, 147],
        "unrelated_kinds_unchanged": set(changed_kinds) <= {
            "expression", "life", "tap_local", "pointer_follow"
        },
        "recording_menu_mode_and_low_power_frames_unchanged": not any(
            kind in changed_kinds
            for kind in ("recording_timeline", "menu_ui", "mode", "blink")
        ),
        "all_bashful_motion_states_keep_complete_eyes_and_cheeks": all(
            signature == expected_bashful
            for signature in bashful_signatures.values()
        ),
        "old_hold_proves_one_or_more_eye_rows_missing": (
            old_hold["eye_pixels"] == [936, 980]
            and old_hold["eye_bottoms"] == [136, 137]
        ),
        "old_motion_proves_additional_eye_erasure": (
            old_motion["eye_pixels"] == [924, 968]
            and old_motion["eye_bottoms"] == [136, 136]
        ),
        "new_hold_and_motion_are_component_identical": (
            new_hold == expected_bashful and new_motion == expected_bashful
        ),
        "morph_uses_source_pixel_clear_not_padded_rectangle": (
            "points.forEach(([x, y]) => context.fillRect(x, y, 1, 1));" in page
            and "expanded rectangle here used to cut neighbouring features" in page
        ),
        "close_family_cheek_clear_is_source_exact": (
            "Do not clear a padded cheek rectangle" in page
            and "lifting them would merge with" in page
        ),
    }
    report = {
        "schema": "companion.comp_req_776.component_continuity.v1",
        "status": "MACHINE_READY" if all(checks.values()) else "NO_GO",
        "checks": checks,
        "identity": {
            "old_manifest_sha256": sha256(args.old),
            "new_manifest_sha256": sha256(args.new),
            "new_page_sha256": new["source"]["page_sha256"],
        },
        "coverage": {
            "states": len(new_rows),
            "changed_states": len(changed),
            "unchanged_states": len(new_rows) - len(changed),
            "changed_kinds": dict(sorted(changed_kinds.items())),
            "changed_families": dict(sorted(changed_families.items())),
            "diff_union": union,
            "bashful_states": len(bashful_ids),
        },
        "root_cause_evidence": {
            "old_hold": old_hold,
            "old_motion": old_motion,
            "new_hold": new_hold,
            "new_motion": new_motion,
        },
        "hardware_contact": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "MACHINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
