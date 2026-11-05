#!/usr/bin/env python3
"""Strictly bind the isolated COMP-REQ-611 lower runner to its source plan."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PLAN_SHA = "2085577BAEC872AFCF7105733E48B921EDA591ADE641F19C4BC42CC77C3D592F"
PAYLOAD_SHA = "5411FB50BC61BF3DC73EB7D0746C6C0E4DB56F7D552B6796BB3B7F6ED59AD5AD"
PAGE_SHA = "3B9C4B2D0D16964DBD64A68B804AA6AB3404237539F44C21F3FEFD0B32A1AA22"
VERIFIER_SHA = "6F400D2CD8FBB35C71A08BC038E38BBBE3CC042C423AAE7B1E36CD56E358456B"
COUNT = 50
BYTES = 5000
CADENCE_MS = 480


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def validate_evidence(evidence_path: Path) -> tuple[dict, str]:
    evidence_bytes = evidence_path.read_bytes()
    evidence = json.loads(evidence_bytes.decode("utf-8"))
    if evidence.get("schema") != "companion.comp_req_608.logical_choreography.verification.v1":
        raise ValueError("unexpected COMP-REQ-608 evidence schema")
    if evidence.get("status") != "PASS_OWNER_REVIEW_READY":
        raise ValueError("COMP-REQ-608 evidence is not PASS_OWNER_REVIEW_READY")
    checks = evidence.get("checks")
    if not isinstance(checks, dict) or not checks or any(value is not True for value in checks.values()):
        raise ValueError("COMP-REQ-608 evidence checks are not all true")
    page = evidence.get("page", {})
    plan = evidence.get("canonical_frame_plan", {})
    if (page.get("sha256", "").upper() != PAGE_SHA or
            plan.get("sha256", "").upper() != PLAN_SHA or
            plan.get("wb55_payload_sha256", "").upper() != PAYLOAD_SHA):
        raise ValueError("COMP-REQ-608 evidence deterministic identity mismatch")
    return evidence, sha(evidence_bytes)


def validate(plan_path: Path, payload_path: Path, evidence_path: Path) -> tuple[dict, bytes, dict, str]:
    upstream_evidence, runtime_evidence_sha = validate_evidence(evidence_path)
    plan_bytes = plan_path.read_bytes()
    payload = payload_path.read_bytes()
    if sha(plan_bytes) != PLAN_SHA:
        raise ValueError("stale or mutated COMP-REQ-611 plan")
    if sha(payload) != PAYLOAD_SHA:
        raise ValueError("stale or mutated COMP-REQ-611 payload")
    plan = json.loads(plan_bytes.decode("utf-8"))
    entries = plan.get("entries")
    if (plan.get("schema") != "companion.canonical_1bit_frame_plan.comp_req_608.v1" or
            plan.get("pixel_format") != "row_major_msb_first_1_is_white" or
            plan.get("width") != 200 or plan.get("height") != 200 or
            plan.get("bytes_per_frame") != BYTES or plan.get("cadence_ms") != CADENCE_MS or
            not isinstance(entries, list) or len(entries) != COUNT or
            len(payload) != COUNT * BYTES):
        raise ValueError("plan schema, pixel format, shape, cadence, or size mismatch")
    previous_hash = None
    previous_id = None
    for index, entry in enumerate(entries):
        frame = payload[index * BYTES:(index + 1) * BYTES]
        frame_hash = sha(frame)
        if (entry.get("payload_offset") != index * BYTES or
                entry.get("payload_bytes") != BYTES or
                entry.get("cadence_ms") != CADENCE_MS or
                not isinstance(entry.get("dwell_commits"), int) or
                entry["dwell_commits"] < 1 or
                entry.get("framebuffer_sha256", "").upper() != frame_hash):
            raise ValueError(f"frame {index} parity/offset/dwell mismatch")
        if previous_hash == frame_hash or previous_id == entry.get("id"):
            raise ValueError(f"adjacent duplicate frame/source at {index}")
        previous_hash = frame_hash
        previous_id = entry.get("id")
    return plan, payload, upstream_evidence, runtime_evidence_sha


def emit(header: Path, plan: dict, payload: bytes) -> None:
    entries = plan["entries"]
    header.parent.mkdir(parents=True, exist_ok=True)
    with header.open("w", encoding="ascii", newline="\n") as out:
        out.write("/* Generated from immutable COMP-REQ-611 upstream. */\n")
        out.write("#ifndef COMP_REQ_611_CANONICAL_FRAMES_H\n#define COMP_REQ_611_CANONICAL_FRAMES_H\n\n#include <stdint.h>\n\n")
        out.write("#define COMP_REQ_611_FRAME_COUNT 50u\n#define COMP_REQ_611_FRAME_BYTES 5000u\n#define COMP_REQ_611_FRAME_CADENCE_MS 480u\n\n")
        out.write("static const uint16_t comp_req_611_dwell_commits[COMP_REQ_611_FRAME_COUNT] = {\n    ")
        out.write(", ".join(f"{entry['dwell_commits']}u" for entry in entries))
        out.write("\n};\n\n")
        for label, key in (("sha256", "framebuffer_sha256"), ("ids", "id")):
            out.write(f"static const char *const comp_req_611_frame_{label}[COMP_REQ_611_FRAME_COUNT] = {{\n")
            for entry in entries:
                value = str(entry[key]).upper() if label == "sha256" else entry[key]
                out.write(f'    "{value}",\n')
            out.write("};\n\n")
        out.write("static const uint8_t comp_req_611_canonical_frames[COMP_REQ_611_FRAME_COUNT][COMP_REQ_611_FRAME_BYTES] = {\n")
        for index, entry in enumerate(entries):
            out.write(f"    /* {index}: {entry['id']} dwell={entry['dwell_commits']} */\n    {{\n")
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
    parser.add_argument("--upstream-evidence", type=Path, required=True)
    args = parser.parse_args()
    plan, payload, upstream_evidence, runtime_evidence_sha = validate(
        args.plan, args.payload, args.upstream_evidence)
    emit(args.header, plan, payload)
    result = {
        "schema": "companion.comp_req_611.lower_canonical_sync.v1",
        "requirement": "COMP-REQ-611",
        "upstream_requirement": "COMP-REQ-608",
        "page_sha256": PAGE_SHA,
        "upstream_evidence_sha256": runtime_evidence_sha,
        "upstream_evidence_sha256_role": "informational_latest_runtime_evidence",
        "upstream_evidence_gate": {
            "schema": upstream_evidence["schema"],
            "status": upstream_evidence["status"],
            "all_checks_true": True,
            "deterministic_identity": {
                "page_sha256": PAGE_SHA,
                "canonical_plan_sha256": PLAN_SHA,
                "canonical_payload_sha256": PAYLOAD_SHA,
            },
        },
        "upstream_verifier_sha256": VERIFIER_SHA,
        "canonical_plan_sha256": PLAN_SHA,
        "canonical_payload_sha256": PAYLOAD_SHA,
        "pixel_format": "row_major_msb_first_1_is_white",
        "frame_count": COUNT,
        "frame_bytes": BYTES,
        "payload_bytes": len(payload),
        "cadence_ms": CADENCE_MS,
        "dwell_commits": [entry["dwell_commits"] for entry in plan["entries"]],
        "ordered_frame_ids": [entry["id"] for entry in plan["entries"]],
        "frame_sha256": [entry["framebuffer_sha256"].upper() for entry in plan["entries"]],
        "generated_header_sha256": sha(args.header.read_bytes()),
    }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
