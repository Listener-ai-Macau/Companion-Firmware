#!/usr/bin/env python3
"""Prove that every native frame transition covers removed black pixels.

This is a source-bound host oracle. It does not claim to measure panel ink;
it catches the exact software failure mode where a driver sends only pixels
that become black and leaves old black pixels outside the update window.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / ".cache/validation/comp-req-616-ten-family-choreography/wb55-frame-plan.bin"
OUT = ROOT / "docs/validation/comp-req-620-residual-pixels/stale-pixel-oracle.json"
FRAME_COUNT = 182
FRAME_BYTES = 5000
PAYLOAD_SHA = "BA869E7A135E99FC12DB073B701B863E4E0B3D1DD31794134C5CC00BCD448F19"


def bounds(mask: bytes) -> tuple[int, int, int, int] | None:
    first_x, last_x = 200, -1
    first_y, last_y = 200, -1
    for index, value in enumerate(mask):
        if not value:
            continue
        y, x_byte = divmod(index, 25)
        first_x = min(first_x, x_byte * 8)
        last_x = max(last_x, x_byte * 8 + 7)
        first_y = min(first_y, y)
        last_y = max(last_y, y)
    return None if last_y < 0 else (first_x, first_y, last_x, last_y)


def outside(mask: bytes, window: tuple[int, int, int, int] | None) -> int:
    if window is None:
        return sum(value.bit_count() for value in mask)
    x0, y0, x1, y1 = window
    count = 0
    for index, value in enumerate(mask):
        y, x_byte = divmod(index, 25)
        allowed = x0 <= x_byte * 8 + 7 and x_byte * 8 <= x1 and y0 <= y <= y1
        if not allowed:
            count += value.bit_count()
    return count


def verify(payload: bytes) -> dict:
    if len(payload) != FRAME_COUNT * FRAME_BYTES:
        raise ValueError(f"payload length {len(payload)} != {FRAME_COUNT * FRAME_BYTES}")
    if hashlib.sha256(payload).hexdigest().upper() != PAYLOAD_SHA:
        raise ValueError("native payload identity drift")

    changed = 0
    unchanged = 0
    removed_bits = 0
    stale_bits = 0
    negative_stale_bits = 0
    for index in range(1, FRAME_COUNT):
        previous = payload[(index - 1) * FRAME_BYTES:index * FRAME_BYTES]
        current = payload[index * FRAME_BYTES:(index + 1) * FRAME_BYTES]
        removed = bytes((~old & new) & 0xFF for old, new in zip(previous, current))
        added = bytes((old & ~new) & 0xFF for old, new in zip(previous, current))
        changed_mask = bytes(old ^ new for old, new in zip(previous, current))
        if any(changed_mask):
            changed += 1
        else:
            unchanged += 1
        removed_bits += sum(value.bit_count() for value in removed)
        stale_bits += outside(removed, bounds(changed_mask))
        negative_stale_bits += outside(removed, bounds(added))

    return {
        "schema": "companion.comp_req_620.residual_pixel_oracle.v1",
        "status": "PASS_RESIDUAL_PIXEL_ORACLE",
        "claim_scope": "native-frame/window software oracle; not a visual panel acceptance",
        "payload_sha256": hashlib.sha256(payload).hexdigest().upper(),
        "frame_count": FRAME_COUNT,
        "frame_bytes": FRAME_BYTES,
        "changed_transition_count": changed,
        "unchanged_transition_count": unchanged,
        "removed_black_pixel_count": removed_bits,
        "stale_pixel_mask_count": stale_bits,
        "negative_added_only_stale_pixel_count": negative_stale_bits,
        "negative_added_only_rejected": negative_stale_bits > 0,
        "old_plane_contract": "old_plane=previous_native_frame; current_plane=current_native_frame",
        "checks": {
            "native_payload_identity": True,
            "dynamic_window_covers_removed_black": stale_bits == 0,
            "added_only_window_is_rejected": negative_stale_bits > 0,
        },
    }


def self_test() -> None:
    previous = bytes([0x00]) + bytes(FRAME_BYTES - 1)
    current = bytes([0x80]) + bytes(FRAME_BYTES - 1)
    removed = bytes((~old & new) & 0xFF for old, new in zip(previous, current))
    added = bytes((old & ~new) & 0xFF for old, new in zip(previous, current))
    assert sum(value.bit_count() for value in removed) == 1
    assert outside(removed, bounds(bytes(old ^ new for old, new in zip(previous, current)))) == 0
    assert outside(removed, bounds(added)) == 1
    print("PASS: COMP-REQ-620 residual-pixel oracle self-test")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--payload", type=Path, default=PAYLOAD)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    result = verify(args.payload.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    return 0 if all(result["checks"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
