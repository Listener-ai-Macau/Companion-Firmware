#!/usr/bin/env python3
"""Generate the immutable COMP-REQ-609 lower-consumer frame header."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PLAN_SHA = "126443C878AAE6AEE09BBE5CABFA7B4C5C963C5B8533451B91403D466214A913"
PAYLOAD_SHA = "5C0D18DB7F7A9452309475D3DEE3AE1412ABA385946BF333C7A0CB0F0DBB0E07"
PAGE_SHA = "B47FC91BCFC7F746012CCFCE4DDF50C34215347A4944E63FA9A348A0901FC5FF"
COUNT = 56
BYTES = 5000
CADENCE = 480


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def validate(plan_path: Path, payload_path: Path) -> tuple[dict, bytes]:
    plan_bytes = plan_path.read_bytes()
    payload = payload_path.read_bytes()
    if digest(plan_bytes) != PLAN_SHA:
        raise ValueError("COMP-REQ-609 plan identity mismatch")
    if digest(payload) != PAYLOAD_SHA:
        raise ValueError("COMP-REQ-609 payload identity mismatch")
    plan = json.loads(plan_bytes.decode("utf-8"))
    entries = plan.get("entries")
    if (plan.get("schema") != "companion.canonical_1bit_frame_plan.comp_req_608.v1" or
            plan.get("width") != 200 or plan.get("height") != 200 or
            plan.get("bytes_per_frame") != BYTES or plan.get("cadence_ms") != CADENCE or
            not isinstance(entries, list) or len(entries) != COUNT or
            len(payload) != COUNT * BYTES):
        raise ValueError("COMP-REQ-609 frame-plan shape/cadence mismatch")
    for index, entry in enumerate(entries):
        frame = payload[index * BYTES:(index + 1) * BYTES]
        if (entry.get("payload_offset") != index * BYTES or
                entry.get("payload_bytes") != BYTES or
                entry.get("cadence_ms") != CADENCE or
                entry.get("dwell_commits") != 1 or
                entry.get("framebuffer_sha256", "").upper() != digest(frame)):
            raise ValueError(f"COMP-REQ-609 frame {index} parity/order/dwell mismatch")
    return plan, payload


def emit(path: Path, plan: dict, payload: bytes) -> None:
    entries = plan["entries"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="ascii", newline="\n") as out:
        out.write("/* Generated; source is the immutable COMP-REQ-609 frame plan. */\n")
        out.write("#ifndef COMP_REQ_609_CANONICAL_FRAMES_H\n#define COMP_REQ_609_CANONICAL_FRAMES_H\n\n#include <stdint.h>\n\n")
        out.write("#define COMP_REQ_609_FRAME_COUNT 56u\n#define COMP_REQ_609_FRAME_BYTES 5000u\n#define COMP_REQ_609_FRAME_CADENCE_MS 480u\n\n")
        for kind, key in (("sha256", "framebuffer_sha256"), ("ids", "id")):
            out.write(f"static const char *const comp_req_609_frame_{kind}[COMP_REQ_609_FRAME_COUNT] = {{\n")
            for entry in entries:
                out.write(f'    "{str(entry[key]).upper() if kind == "sha256" else entry[key]}",\n')
            out.write("};\n\n")
        out.write("static const uint8_t comp_req_609_canonical_frames[COMP_REQ_609_FRAME_COUNT][COMP_REQ_609_FRAME_BYTES] = {\n")
        for index in range(COUNT):
            out.write(f"    /* {index}: {entries[index]['id']} */\n    {{\n")
            frame = payload[index * BYTES:(index + 1) * BYTES]
            for start in range(0, BYTES, 16):
                out.write("        " + ", ".join(f"0x{value:02X}u" for value in frame[start:start + 16]) + ",\n")
            out.write("    },\n")
        out.write("};\n\n#endif\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--header", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    plan, payload = validate(args.plan, args.payload)
    emit(args.header, plan, payload)
    evidence = {
        "schema": "companion.comp_req_609.lower_canonical_sync.v1",
        "requirement": "COMP-REQ-609",
        "source_requirement": "COMP-REQ-608",
        "page_sha256": PAGE_SHA,
        "canonical_plan_sha256": PLAN_SHA,
        "canonical_payload_sha256": PAYLOAD_SHA,
        "frame_count": COUNT,
        "frame_bytes": BYTES,
        "payload_bytes": len(payload),
        "cadence_ms": CADENCE,
        "dwell_commits": [entry["dwell_commits"] for entry in plan["entries"]],
        "ordered_frame_ids": [entry["id"] for entry in plan["entries"]],
        "frame_sha256": [entry["framebuffer_sha256"].upper() for entry in plan["entries"]],
        "generated_header_sha256": digest(args.header.read_bytes()),
    }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
