"""Audit every active browser-authored e-paper state for truncation and staging loss.

The top status bar intentionally reaches the top, left, and right panel edges.
Below that declared 16-pixel strip, no face, ornament, menu, waveform, or other
body content may touch either side or the bottom edge.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / (
    ".cache/validation/comp776-component-clip-fix-20260812/"
    "source-pack-5059/source-pack-manifest.json"
)
DEFAULT_GENERATION = ROOT / (
    ".cache/validation/comp776-component-clip-fix-20260812/"
    "generation-20-compact/generation-verification.json"
)
DEFAULT_PAGE = ROOT / ".cache/validation/comp-req-628-status-bar/index.html"
DEFAULT_OUTPUT = ROOT / (
    ".cache/validation/comp776-component-clip-fix-20260812/"
    "EXPRESSION_COMPLETENESS.json"
)

WIDTH = 200
HEIGHT = 200
STATUS_BAR_HEIGHT = 16
ROW_BYTES = WIDTH // 8
FRAME_BYTES = ROW_BYTES * HEIGHT
EXPECTED_KINDS = {
    "blink",
    "expression",
    "life",
    "menu_progress",
    "menu_ui",
    "mode",
    "pointer_follow",
    "recording_timeline",
    "tap_edge",
    "tap_local",
    "tap_transition",
    "upgrade_progress",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def read_p4(path: Path) -> tuple[bytes, bytes]:
    data = path.read_bytes()
    first = data.find(b"\n")
    second = data.find(b"\n", first + 1)
    if first < 0 or second < 0 or data[:first] != b"P4":
        raise ValueError(f"not a binary PBM: {path}")
    if data[first + 1 : second].split() != [b"200", b"200"]:
        raise ValueError(f"unexpected PBM geometry: {path}")
    frame = data[second + 1 :]
    if len(frame) != FRAME_BYTES:
        raise ValueError(f"unexpected PBM payload: {path} ({len(frame)})")
    return data, frame


def is_black(frame: bytes, x: int, y: int) -> bool:
    # Netpbm P4 is row-major MSB-first with 1=black, 0=white.  Confirm this
    # against the manifest's per-frame black_pixels rather than trusting the
    # older source metadata string, which describes the panel plane polarity.
    return bool(frame[y * ROW_BYTES + x // 8] & (0x80 >> (x & 7)))


def black_geometry(frame: bytes) -> tuple[list[int] | None, int, dict[str, int | None]]:
    xs: list[int] = []
    ys: list[int] = []
    body_xs: list[int] = []
    body_ys: list[int] = []
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if not is_black(frame, x, y):
                continue
            xs.append(x)
            ys.append(y)
            if y >= STATUS_BAR_HEIGHT:
                body_xs.append(x)
                body_ys.append(y)
    bounds = [min(xs), min(ys), max(xs), max(ys)] if xs else None
    margins: dict[str, int | None] = {
        "top_below_status": min(body_ys) - STATUS_BAR_HEIGHT if body_ys else None,
        "left": min(body_xs) if body_xs else None,
        "right": WIDTH - 1 - max(body_xs) if body_xs else None,
        "bottom": HEIGHT - 1 - max(body_ys) if body_ys else None,
    }
    return bounds, len(xs), margins


def map_controller_rows(frame: bytes) -> bytes:
    rows = [frame[index : index + ROW_BYTES] for index in range(0, FRAME_BYTES, ROW_BYTES)]
    return b"".join(reversed(rows))


def difference_window(previous: bytes, current: bytes) -> tuple[int, int, int, int] | None:
    changed = [index for index, pair in enumerate(zip(previous, current)) if pair[0] != pair[1]]
    if not changed:
        return None
    rows = [index // ROW_BYTES for index in changed]
    columns = [index % ROW_BYTES for index in changed]
    return min(columns), max(columns), min(rows), max(rows)


def expand(
    coverage: tuple[int, int, int, int] | None,
    delta: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    if coverage is None:
        return delta
    return (
        min(coverage[0], delta[0]),
        max(coverage[1], delta[1]),
        min(coverage[2], delta[2]),
        max(coverage[3], delta[3]),
    )


def stage(previous: bytes, current: bytes, window: tuple[int, int, int, int]) -> bytes:
    result = bytearray(previous)
    x0, x1, y0, y1 = window
    for y in range(y0, y1 + 1):
        start = y * ROW_BYTES + x0
        end = y * ROW_BYTES + x1 + 1
        result[start:end] = current[start:end]
    return bytes(result)


def close_family_guard(page_text: str) -> dict[str, bool]:
    close_match = re.search(
        r"function applyCloseFamilyVisualIdentity\(frame, familyName, cheekOffsets = null\) \{(.*?)\n\}",
        page_text,
        flags=re.DOTALL,
    )
    morph_match = re.search(
        r"function morphComponent\(points, profile\) \{(.*?)\n\}",
        page_text,
        flags=re.DOTALL,
    )
    close_block = close_match.group(1) if close_match else ""
    morph_block = morph_match.group(1) if morph_match else ""
    return {
        "close_family_function_present": bool(close_match),
        "component_morph_function_present": bool(morph_match),
        "close_family_targets_cheeks_only": (
            "const cheeks" in close_block
            and "frame.eyes" not in close_block
            and "roles?.eyes" not in close_block
            and "const eyes" not in close_block
        ),
        "historical_eye_erasure_is_documented_removed": (
            "Keep the generated eye bodies intact" in close_block
            and "erased the top 2/4 rows" in close_block
        ),
        "close_family_erases_exact_cheek_pixels_only": (
            "points.forEach(([x, y]) => context.fillRect(x, y, 1, 1))" in close_block
            and "fillRect(bounds." not in close_block
        ),
        "motion_erases_exact_component_pixels_only": (
            "points.forEach(([x, y]) => context.fillRect(x, y, 1, 1))" in morph_block
            and "context.fillRect(bx - 3" not in morph_block
            and "width + 6" not in morph_block
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--generation", type=Path, default=DEFAULT_GENERATION)
    parser.add_argument("--page", type=Path, default=DEFAULT_PAGE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    source = json.loads(args.source.read_text(encoding="utf-8"))
    generation = json.loads(args.generation.read_text(encoding="utf-8"))
    source_dir = args.source.parent
    states = source.get("states", [])
    kind_counts: Counter[str] = Counter()
    unique_payloads: set[str] = set()
    failures: list[dict[str, object]] = []
    risk_rows: list[dict[str, object]] = []
    previous = bytes([0xFF]) * FRAME_BYTES
    coverage = None
    unchanged = 0

    for state in states:
        state_id = str(state.get("id"))
        kind = str(state.get("kind"))
        kind_counts[kind] += 1
        try:
            pbm_data, frame = read_p4(source_dir / str(state["pbm_file"]))
        except (OSError, KeyError, ValueError) as exc:
            failures.append({"id": state_id, "reason": "pbm_read", "detail": str(exc)})
            continue
        payload_sha = sha256(frame)
        unique_payloads.add(payload_sha)
        bounds, black_pixels, margins = black_geometry(frame)
        if sha256(pbm_data) != state.get("pbm_sha256"):
            failures.append({"id": state_id, "reason": "pbm_sha256_mismatch"})
        if bounds != state.get("black_bounds"):
            failures.append(
                {
                    "id": state_id,
                    "reason": "black_bounds_mismatch",
                    "expected": state.get("black_bounds"),
                    "actual": bounds,
                }
            )
        if black_pixels != state.get("black_pixels"):
            failures.append({"id": state_id, "reason": "black_pixel_count_mismatch"})
        if any(margins[name] == 0 for name in ("left", "right", "bottom")):
            failures.append(
                {
                    "id": state_id,
                    "reason": "body_touches_forbidden_panel_edge",
                    "margins": margins,
                }
            )
        risk_rows.append({"id": state_id, "kind": kind, "body_margins": margins})

        mapped = map_controller_rows(frame)
        if map_controller_rows(mapped) != frame:
            failures.append({"id": state_id, "reason": "row_map_not_reversible"})
            continue
        delta = difference_window(previous, mapped)
        if delta is None:
            unchanged += 1
            staged = previous
        else:
            coverage = expand(coverage, delta)
            staged = stage(previous, mapped, coverage)
        if staged != mapped:
            mismatch = next(index for index in range(FRAME_BYTES) if staged[index] != mapped[index])
            failures.append(
                {
                    "id": state_id,
                    "reason": "source_complete_stage_mismatch",
                    "byte": mismatch,
                    "x_byte": mismatch % ROW_BYTES,
                    "mapped_y": mismatch // ROW_BYTES,
                }
            )
        previous = mapped

    source_invariants = source.get("invariants", {})
    source_page_sha = source.get("source", {}).get("page_sha256")
    guard_checks = close_family_guard(args.page.read_text(encoding="utf-8"))
    checks = {
        "source_pack_pass": source.get("status") == "PASS",
        "all_5059_active_states_audited": len(states) == 5059,
        "all_declared_kinds_audited": set(kind_counts) == EXPECTED_KINDS,
        "all_inputs_strict_200x200_1bpp": (
            source_invariants.get("all_inputs_binary") is True
            and source_invariants.get("all_states_are_5000_bytes") is True
        ),
        "manifest_hash_bounds_and_pixel_counts_match": not any(
            row["reason"] in {
                "pbm_read",
                "pbm_sha256_mismatch",
                "black_bounds_mismatch",
                "black_pixel_count_mismatch",
            }
            for row in failures
        ),
        "status_bar_is_only_allowed_edge_contact": not any(
            row["reason"] == "body_touches_forbidden_panel_edge" for row in failures
        ),
        "controller_row_map_is_lossless": not any(
            row["reason"] == "row_map_not_reversible" for row in failures
        ),
        "all_states_are_exact_after_source_complete_staging": not any(
            row["reason"] == "source_complete_stage_mismatch" for row in failures
        ),
        "active_generation_reconstructs_all_states": (
            generation.get("status") == "PASS_UI_ASSET_GENERATION_EQUIVALENT"
            and generation.get("states_checked") == len(states)
            and generation.get("strict_1bpp") is True
            and generation.get("page_sha256") == source_page_sha
        ),
        "unique_frame_count_matches_manifest": (
            len(unique_payloads) == source_invariants.get("unique_frame_count")
        ),
        **guard_checks,
    }
    ready = all(checks.values()) and not failures
    closest = sorted(
        risk_rows,
        key=lambda row: (
            min(
                row["body_margins"][name]
                for name in ("left", "right", "bottom")
                if row["body_margins"][name] is not None
            ),
            row["id"],
        ),
    )[:36]
    report = {
        "schema": "companion.comp_req_776.expression_completeness.v1",
        "status": "MACHINE_READY" if ready else "NO_GO",
        "checks": checks,
        "policy": {
            "canvas": [WIDTH, HEIGHT],
        "pixel_format": "Netpbm P4 row-major MSB-first, 1=black, 0=white",
            "allowed_edge_contact": {"region": [0, 0, 199, 15], "owner": "status_bar"},
            "forbidden_edge_contact": [
                "x=0 for y>=16",
                "x=199 for y>=16",
                "y=199",
            ],
        },
        "identity": {
            "resource_page_sha256": source_page_sha,
            "current_behavior_page_sha256": sha256(args.page.read_bytes()),
            "resource_id": generation.get("resource_id"),
        },
        "state_count": len(states),
        "unique_frame_count": len(unique_payloads),
        "unchanged_transitions": unchanged,
        "kind_counts": dict(sorted(kind_counts.items())),
        "closest_body_edge_states": closest,
        "failure_count": len(failures),
        "failures": failures[:50],
        "hardware_contact": 0,
        "external_resource_write_bytes": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
