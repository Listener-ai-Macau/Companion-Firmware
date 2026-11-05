#!/usr/bin/env python3
"""Generate the default-off COMP-REQ-616 native frame asset.

The payload is compressed with a tiny PackBits-style codec so the isolated
runner does not need a multi-megabyte C initializer.  The generator still
checks every uncompressed frame byte and records any evidence-hash drift as a
NO_GO condition; it never silently changes the source identity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / ".cache/validation/comp-req-616-ten-family-choreography"
PAGE = ART / "index.html"
EVIDENCE = ART / "verification.json"
PLAN = ART / "canonical-frame-plan.json"
PAYLOAD = ART / "wb55-frame-plan.bin"

PAGE_SHA = "ECCC8D27A31209150B9EEBF8AB25CEB08708B32BBA00541E033C8378E5B77E73"
EVIDENCE_SHA = "12E924C86A4A6787D2502ABE1F6D1DF278200FF9AC0E330CC002088144FEA76D"
PLAN_SHA = "2A0DE4F6296BEAA18606E0AE40AB41F008D0DBE1CB9E668067A49DDB6D95046F"
PAYLOAD_SHA = "087654306CFC0ECA07BEE9F270DAF72C0DB269E3CF39C6D4D6098BB96EA137DC"
FRAME_COUNT = 182
FRAME_BYTES = 5000
CADENCE_MS = 480


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def packbits(data: bytes) -> bytes:
    """Encode literals/runs with one control byte per block.

    A high control bit denotes a repeated byte; the low seven bits store
    length-1.  A clear high bit denotes a literal block of length 1..128.
    """
    out = bytearray()
    index = 0
    while index < len(data):
        run_end = index + 1
        while (run_end < len(data) and data[run_end] == data[index] and
               run_end - index < 128):
            run_end += 1
        if run_end - index >= 3:
            out.extend((0x80 | (run_end - index - 1), data[index]))
            index = run_end
            continue
        literal_start = index
        index += 1
        while index < len(data) and index - literal_start < 128:
            run_end = index + 1
            while (run_end < len(data) and data[run_end] == data[index] and
                   run_end - index < 128):
                run_end += 1
            if run_end - index >= 3:
                break
            index = run_end
        out.append(index - literal_start - 1)
        out.extend(data[literal_start:index])
    return bytes(out)


def unpackbits(data: bytes, expected_length: int) -> bytes:
    out = bytearray()
    index = 0
    while index < len(data) and len(out) < expected_length:
        control = data[index]
        index += 1
        length = (control & 0x7F) + 1
        if control & 0x80:
            if index >= len(data):
                raise RuntimeError("compressed header ends inside a run")
            out.extend([data[index]] * length)
            index += 1
        else:
            if index + length > len(data):
                raise RuntimeError("compressed header ends inside a literal")
            out.extend(data[index:index + length])
            index += length
        if len(out) > expected_length:
            raise RuntimeError("compressed header expands beyond the payload")
    if index != len(data) or len(out) != expected_length:
        raise RuntimeError("compressed header length does not close exactly")
    return bytes(out)


def unpackbits_frame(data: bytes, start: int, expected_length: int) -> tuple[bytes, int]:
    """Decode one self-contained frame stream and return its closing cursor."""
    out = bytearray()
    index = start
    while index < len(data) and len(out) < expected_length:
        control = data[index]
        index += 1
        length = (control & 0x7F) + 1
        if control & 0x80:
            if index >= len(data):
                raise RuntimeError("compressed frame ends inside a run")
            out.extend([data[index]] * length)
            index += 1
        else:
            if index + length > len(data):
                raise RuntimeError("compressed frame ends inside a literal")
            out.extend(data[index:index + length])
            index += length
        if len(out) > expected_length:
            raise RuntimeError("compressed frame expands beyond its boundary")
    if len(out) != expected_length:
        raise RuntimeError("compressed frame does not close at its byte boundary")
    return bytes(out), index


def verify_header_roundtrip(header: Path, payload: bytes) -> dict:
    text = header.read_text(encoding="ascii")
    marker = "static const uint8_t comp_req_616_packed_payload"
    start = text.index(marker)
    body = text[text.index("{", start):text.index("};", start)]
    values = bytes(int(value, 16) for value in re.findall(r"0x([0-9A-Fa-f]{2})u", body))
    decoded_frames = bytearray()
    cursor = 0
    for _ in range(FRAME_COUNT):
        frame, cursor = unpackbits_frame(values, cursor, FRAME_BYTES)
        decoded_frames.extend(frame)
    if cursor != len(values):
        raise RuntimeError("compressed frame streams do not consume the header exactly")
    decoded = bytes(decoded_frames)
    if decoded != payload:
        raise RuntimeError("generated header round-trip differs from the native payload")
    return {
        "compressed_bytes": len(values),
        "decoded_bytes": len(decoded),
        "decoded_payload_sha256": sha(decoded),
        "matches_native_payload": True,
    }


def validate() -> tuple[dict, bytes, bytes, dict]:
    page_bytes = PAGE.read_bytes()
    plan_bytes = PLAN.read_bytes()
    payload = PAYLOAD.read_bytes()
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    observed = {
        "page": sha(page_bytes),
        "evidence": sha(EVIDENCE.read_bytes()),
        "plan": sha(plan_bytes),
        "payload": sha(payload),
    }
    if observed["page"] != PAGE_SHA or observed["plan"] != PLAN_SHA or observed["payload"] != PAYLOAD_SHA:
        raise RuntimeError(f"immutable page/plan/payload identity mismatch: {observed}")
    if evidence.get("schema") != "companion.comp_req_616.ten_family_choreography.verification.v1":
        raise RuntimeError("unexpected evidence schema")
    if evidence.get("status") != "PASS_OWNER_REVIEW_READY":
        raise RuntimeError("upper evidence is not PASS_OWNER_REVIEW_READY")
    checks = evidence.get("checks")
    if not isinstance(checks, dict) or not checks or any(value is not True for value in checks.values()):
        raise RuntimeError("upper evidence checks are not all true")
    plan = json.loads(plan_bytes.decode("utf-8"))
    entries = plan.get("entries")
    if (plan.get("schema") != "companion.canonical_1bit_frame_plan.comp_req_616.ten_family.v1" or
            plan.get("pixel_format") != "row_major_msb_first_1_is_white" or
            plan.get("width") != 200 or plan.get("height") != 200 or
            plan.get("bytes_per_frame") != FRAME_BYTES or
            plan.get("cadence_ms") != CADENCE_MS or
            not isinstance(entries, list) or len(entries) != FRAME_COUNT or
            len(payload) != FRAME_COUNT * FRAME_BYTES):
        raise RuntimeError("plan shape, polarity, cadence, count, or size mismatch")
    ids: list[str] = []
    hashes: list[str] = []
    dwell: list[int] = []
    for index, entry in enumerate(entries):
        frame = payload[index * FRAME_BYTES:(index + 1) * FRAME_BYTES]
        frame_sha = sha(frame)
        if (entry.get("payload_offset") != index * FRAME_BYTES or
                entry.get("payload_bytes") != FRAME_BYTES or
                entry.get("cadence_ms") != CADENCE_MS or
                not isinstance(entry.get("dwell_commits"), int) or
                entry.get("dwell_commits") not in (1, 2) or
                entry.get("framebuffer_sha256", "").upper() != frame_sha):
            raise RuntimeError(f"frame {index} identity or dwell mismatch")
        ids.append(str(entry["id"]))
        hashes.append(frame_sha)
        dwell.append(int(entry["dwell_commits"]))
    if len(set(ids)) != FRAME_COUNT:
        raise RuntimeError("frame IDs are not unique")
    # Keep each frame's PackBits stream self-contained.  The firmware decoder
    # advances one compressed stream per 5000-byte frame; packing the entire
    # payload as one stream can place a run across a frame boundary and makes
    # the first physical decode fail even though whole-payload roundtrip
    # succeeds.
    compressed = b"".join(
        packbits(payload[index * FRAME_BYTES:(index + 1) * FRAME_BYTES])
        for index in range(FRAME_COUNT)
    )
    return evidence, payload, compressed, {
        "observed": observed, "ids": ids, "hashes": hashes, "dwell": dwell,
    }


def emit(header: Path, compressed: bytes, metadata: dict) -> None:
    header.parent.mkdir(parents=True, exist_ok=True)
    with header.open("w", encoding="ascii", newline="\n") as out:
        out.write("/* Generated from the immutable COMP-REQ-616 native payload. */\n")
        out.write("#ifndef COMP_REQ_616_CANONICAL_FRAMES_H\n#define COMP_REQ_616_CANONICAL_FRAMES_H\n\n")
        out.write("#include <stdbool.h>\n#include <stddef.h>\n#include <stdint.h>\n\n")
        out.write(f"#define COMP_REQ_616_FRAME_COUNT {FRAME_COUNT}u\n")
        out.write(f"#define COMP_REQ_616_FRAME_BYTES {FRAME_BYTES}u\n")
        out.write(f"#define COMP_REQ_616_FRAME_CADENCE_MS {CADENCE_MS}u\n")
        out.write(f"#define COMP_REQ_616_COMPRESSED_BYTES {len(compressed)}u\n\n")
        out.write("static const uint16_t comp_req_616_dwell_commits[COMP_REQ_616_FRAME_COUNT] = {\n    ")
        out.write(", ".join(f"{item}u" for item in metadata["dwell"]))
        out.write("\n};\n\n")
        for label, values in (("ids", metadata["ids"]), ("sha256", metadata["hashes"])):
            out.write(f"static const char *const comp_req_616_frame_{label}[COMP_REQ_616_FRAME_COUNT] = {{\n")
            for value in values:
                out.write(f'    "{value}",\n')
            out.write("};\n\n")
        out.write("static const uint8_t comp_req_616_packed_payload[COMP_REQ_616_COMPRESSED_BYTES] = {\n")
        for start in range(0, len(compressed), 16):
            out.write("    " + ", ".join(f"0x{value:02X}u" for value in compressed[start:start + 16]) + ",\n")
        out.write("};\n\n#endif\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--header", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    evidence, payload, compressed, metadata = validate()
    emit(args.header, compressed, metadata)
    roundtrip = verify_header_roundtrip(args.header, payload)
    evidence_plan = evidence.get("canonical_frame_plan", {})
    evidence_identity = {
        "page_sha256": evidence.get("page", {}).get("sha256"),
        "plan_sha256": evidence_plan.get("sha256"),
        "payload_sha256": evidence_plan.get("wb55_payload_sha256"),
        "frame_count": evidence_plan.get("entries"),
        "payload_bytes": evidence_plan.get("wb55_payload_bytes"),
    }
    evidence_identity["all_deterministic_bindings_match"] = (
        evidence_identity["page_sha256"] == PAGE_SHA and
        evidence_identity["plan_sha256"] == PLAN_SHA and
        evidence_identity["payload_sha256"] == PAYLOAD_SHA and
        evidence_identity["frame_count"] == FRAME_COUNT and
        evidence_identity["payload_bytes"] == len(payload)
    )
    observed = metadata["observed"]
    manifest = {
        "schema": "companion.comp_req_616.lower_canonical_sync_asset.v1",
        "requirement": "COMP-REQ-617",
        # The registry freezes the browser evidence identity.  Runtime
        # telemetry may be volatile, but a drifted artifact is not an
        # executable physical candidate until the exact frozen evidence is
        # recovered or regenerated.
        "status": "READY" if observed["evidence"] == EVIDENCE_SHA else "NO_GO_EVIDENCE_HASH_DRIFT",
        "hardware_contact": 0,
        "page_sha256": PAGE_SHA,
        "expected_evidence_sha256": EVIDENCE_SHA,
        "observed_evidence_sha256": observed["evidence"],
        "evidence_sha256_informational": False,
        "evidence_hash_matches_registry": observed["evidence"] == EVIDENCE_SHA,
        "canonical_plan_sha256": PLAN_SHA,
        "canonical_payload_sha256": PAYLOAD_SHA,
        "frame_count": FRAME_COUNT,
        "frame_bytes": FRAME_BYTES,
        "payload_bytes": len(payload),
        "compressed_bytes": len(compressed),
        "pixel_format": "row_major_msb_first_1_is_white",
        "cadence_ms": CADENCE_MS,
        "generated_header_sha256": sha(args.header.read_bytes()),
        "header_roundtrip": roundtrip,
        "evidence_identity": evidence_identity,
        "all_semantic_checks_true": True,
        "physical_execute_authorized": False,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
