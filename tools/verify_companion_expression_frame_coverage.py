"""Prove browser base frames survive CEMP decode, row mapping, and staging."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / (
    ".cache/validation/comp775-r33-expression-coverage-audit/"
    "source-pack/source-pack-manifest.json"
)
DEFAULT_GENERATION = ROOT / (
    ".cache/validation/comp775-r33-expression-coverage-audit/"
    "generation-18-compact/generation-verification.json"
)
DEFAULT_OUTPUT = ROOT / (
    ".cache/validation/comp775-r38-blink-browser-parity/"
    "EXPRESSION_FRAME_COVERAGE.json"
)
BASE_KINDS = {
    "blink",
    "expression",
    "life",
    "pointer_follow",
    "tap_edge",
    "tap_local",
    "tap_transition",
}
WIDTH = 200
HEIGHT = 200
ROW_BYTES = WIDTH // 8
FRAME_BYTES = ROW_BYTES * HEIGHT


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def read_p4(path: Path) -> bytes:
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
    return frame


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


def stage(
    previous: bytes,
    current: bytes,
    window: tuple[int, int, int, int],
) -> bytes:
    result = bytearray(previous)
    x0, x1, y0, y1 = window
    for y in range(y0, y1 + 1):
        start = y * ROW_BYTES + x0
        end = y * ROW_BYTES + x1 + 1
        result[start:end] = current[start:end]
    return bytes(result)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--generation", type=Path, default=DEFAULT_GENERATION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    source = json.loads(args.source.read_text(encoding="utf-8"))
    generation = json.loads(args.generation.read_text(encoding="utf-8"))
    source_dir = args.source.parent
    states = [row for row in source["states"] if row.get("kind") in BASE_KINDS]
    previous = bytes([0xFF]) * FRAME_BYTES
    coverage = None
    failures: list[dict[str, object]] = []
    kind_counts: dict[str, int] = {}
    unique_frames: set[str] = set()
    unchanged = 0

    for state in states:
        frame = read_p4(source_dir / state["pbm_file"])
        unique_frames.add(sha256(frame))
        kind = str(state["kind"])
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
        mapped = map_controller_rows(frame)
        if map_controller_rows(mapped) != frame:
            failures.append({"id": state["id"], "reason": "row_map_not_reversible"})
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
                    "id": state["id"],
                    "reason": "source_complete_stage_mismatch",
                    "byte": mismatch,
                    "x_byte": mismatch % ROW_BYTES,
                    "mapped_y": mismatch // ROW_BYTES,
                }
            )
        previous = mapped

    checks = {
        "fixed_browser_source_pack_pass": source.get("status") == "PASS",
        "all_browser_inputs_strict_1bpp": source.get("invariants", {}).get("all_inputs_binary") is True,
        "generation_reconstructs_every_browser_state_bit_exact": (
            generation.get("status") == "PASS_UI_ASSET_GENERATION_EQUIVALENT"
            and generation.get("states_checked") == len(source["states"])
            and generation.get("strict_1bpp") is True
            and generation.get("page_sha256") == source.get("source", {}).get("page_sha256")
        ),
        "controller_row_map_is_lossless": not any(row["reason"] == "row_map_not_reversible" for row in failures),
        "every_base_state_is_exact_after_source_complete_staging": not any(
            row["reason"] == "source_complete_stage_mismatch" for row in failures
        ),
        "all_required_base_kinds_were_audited": BASE_KINDS == set(kind_counts),
    }
    ready = all(checks.values()) and not failures
    report = {
        "schema": "companion.expression_frame_coverage.v1",
        "status": "MACHINE_READY" if ready else "NO_GO",
        "checks": checks,
        "browser_page_sha256": source.get("source", {}).get("page_sha256"),
        "resource_id": generation.get("resource_id"),
        "source_states": len(source["states"]),
        "base_states_audited": len(states),
        "unique_base_frames": len(unique_frames),
        "unchanged_transitions": unchanged,
        "kind_counts": dict(sorted(kind_counts.items())),
        "failures": failures[:20],
        "hardware_contact": 0,
        "external_resource_write_bytes": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
