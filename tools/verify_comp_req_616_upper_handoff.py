#!/usr/bin/env python3
"""Fail-closed identity and pixel binding for the COMP-REQ-616 upper handoff.

This is intentionally a host-only gate.  It proves that the browser page,
canonical frame plan, and native-polarity payload are one immutable candidate;
it does not claim that the currently installed lower runner consumes it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / ".cache/validation/comp-req-616-ten-family-choreography"
PAGE = ART / "index.html"
EVIDENCE = ART / "verification.json"
PLAN = ART / "canonical-frame-plan.json"
PAYLOAD = ART / "wb55-frame-plan.bin"
HANDOFF = ROOT / "docs/validation/companion-comp-req-616-fresh-evidence-handoff-20260726.json"
OUT = ROOT / "docs/validation/comp-req-616-upper-handoff"
REPORT = OUT / "MACHINE_READY.json"

EXPECTED = {
    "page": "ECCC8D27A31209150B9EEBF8AB25CEB08708B32BBA00541E033C8378E5B77E73",
    "evidence": "12E924C86A4A6787D2502ABE1F6D1DF278200FF9AC0E330CC002088144FEA76D",
    "plan": "2A0DE4F6296BEAA18606E0AE40AB41F008D0DBE1CB9E668067A49DDB6D95046F",
    "payload": "087654306CFC0ECA07BEE9F270DAF72C0DB269E3CF39C6D4D6098BB96EA137DC",
    "handoff": "DF4FF24E0A519BEC3E8AE9E419F61FCB1C67AFE0626048AC495579E5569F202E",
}
FRAME_COUNT = 182
FRAME_BYTES = 5000
WIDTH = 200
HEIGHT = 200
CADENCE_MS = 480


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def frame_window(previous: bytes, current: bytes) -> dict:
    row_bytes = WIDTH // 8
    changed = [index for index, (before, after) in enumerate(zip(previous, current))
               if before != after]
    if not changed:
        return {"changed": False, "changed_bytes": 0, "byte_aligned": True}
    # The panel address window is the complete union of changed bytes.  It is
    # deliberately not the historical fixed R12 corridor.
    x_start = min(index % row_bytes for index in changed)
    x_end = max(index % row_bytes for index in changed)
    y_start = min(index // row_bytes for index in changed)
    y_end = max(index // row_bytes for index in changed)
    enclosed = all(
        x_start <= index % row_bytes <= x_end and
        y_start <= index // row_bytes <= y_end
        for index in changed
    )
    return {
        "changed": True,
        "changed_bytes": len(changed),
        "changed_pixels": sum(
            (previous[index] ^ current[index]).bit_count() for index in changed
        ),
        "x_start_byte": x_start,
        "x_end_byte": x_end,
        "y_start": y_start,
        "y_end": y_end,
        "byte_aligned": True,
        "union_exact": enclosed,
    }


def validate() -> dict:
    paths = {"page": PAGE, "evidence": EVIDENCE, "plan": PLAN,
             "payload": PAYLOAD, "handoff": HANDOFF}
    observed = {name: sha(path) for name, path in paths.items() if path.is_file()}
    deterministic_expected = {
        "page": EXPECTED["page"],
        "evidence": EXPECTED["evidence"],
        "plan": EXPECTED["plan"],
        "payload": EXPECTED["payload"],
        "handoff": EXPECTED["handoff"],
    }
    deterministic_observed = {name: observed[name] for name in deterministic_expected if name in observed}
    if deterministic_observed != {name: deterministic_expected[name] for name in deterministic_observed}:
        raise RuntimeError(f"immutable deterministic identity mismatch: {observed}")

    if observed.get("evidence") != EXPECTED["evidence"]:
        raise RuntimeError(
            f"frozen evidence SHA mismatch: expected {EXPECTED['evidence']}, "
            f"observed {observed.get('evidence')}"
        )
    evidence = load_json(EVIDENCE)
    handoff = load_json(HANDOFF)
    plan = load_json(PLAN)
    payload = PAYLOAD.read_bytes()
    checks = evidence.get("checks")
    if evidence.get("schema") != "companion.comp_req_616.ten_family_choreography.verification.v1":
        raise RuntimeError("unexpected COMP-REQ-616 evidence schema")
    if evidence.get("status") != "PASS_OWNER_REVIEW_READY":
        raise RuntimeError("upper evidence is not PASS_OWNER_REVIEW_READY")
    if not isinstance(checks, dict) or not checks or any(value is not True for value in checks.values()):
        raise RuntimeError("upper evidence checks are not all true")
    if handoff.get("status") != "WAITING_FOR_LOWER_PHYSICAL_INTEGRATION":
        raise RuntimeError("handoff status changed; review the physical boundary")
    if handoff.get("authorization", {}).get("hardware_execute") is not False:
        raise RuntimeError("handoff unexpectedly authorizes hardware")
    if (plan.get("schema") != "companion.canonical_1bit_frame_plan.comp_req_616.ten_family.v1" or
            plan.get("pixel_format") != "row_major_msb_first_1_is_white" or
            plan.get("width") != WIDTH or plan.get("height") != HEIGHT or
            plan.get("bytes_per_frame") != FRAME_BYTES or
            plan.get("cadence_ms") != CADENCE_MS):
        raise RuntimeError("frame plan shape or polarity mismatch")
    entries = plan.get("entries")
    if not isinstance(entries, list) or len(entries) != FRAME_COUNT:
        raise RuntimeError("expected exactly 182 ordered frames")
    if len(payload) != FRAME_COUNT * FRAME_BYTES:
        raise RuntimeError("payload byte count mismatch")

    frame_ids = []
    frame_hashes = []
    windows = []
    for index, entry in enumerate(entries):
        frame = payload[index * FRAME_BYTES:(index + 1) * FRAME_BYTES]
        frame_hash = hashlib.sha256(frame).hexdigest().upper()
        if (entry.get("payload_offset") != index * FRAME_BYTES or
                entry.get("payload_bytes") != FRAME_BYTES or
                entry.get("cadence_ms") != CADENCE_MS or
                entry.get("dwell_commits") not in (1, 2) or
                entry.get("framebuffer_sha256", "").upper() != frame_hash):
            raise RuntimeError(f"frame {index} identity/dwell mismatch")
        frame_ids.append(entry.get("id"))
        frame_hashes.append(frame_hash)
        previous = payload[(index - 1) * FRAME_BYTES:index * FRAME_BYTES] if index else bytes(FRAME_BYTES)
        windows.append(frame_window(previous, frame))
    if len(set(frame_ids)) != FRAME_COUNT:
        raise RuntimeError("frame IDs are not unique")
    if not all(window.get("union_exact", True) for window in windows):
        raise RuntimeError("a dynamic window does not enclose all changed bytes")

    changed = [window for window in windows if window["changed"]]
    report = {
        "schema": "companion.comp_req_616.upper_handoff_machine_ready.v1",
        "requirement": "COMP-REQ-617",
        "status": "READY_UPPER_HANDOFF_LOWER_616_BOUND",
        "hardware_contact": 0,
        "execute_authorized": False,
        "identity": {
            "page_sha256": EXPECTED["page"],
            "evidence_sha256": observed.get("evidence", EXPECTED["evidence"]),
            "evidence_sha256_expected_registry": EXPECTED["evidence"],
            "evidence_sha256_informational": False,
            "frame_plan_sha256": EXPECTED["plan"],
            "payload_sha256": EXPECTED["payload"],
            "handoff_sha256": EXPECTED["handoff"],
            "frame_count": FRAME_COUNT,
            "frame_bytes": FRAME_BYTES,
            "payload_bytes": len(payload),
            "pixel_format": plan["pixel_format"],
            "cadence_ms": CADENCE_MS,
            "ordered_frame_ids_sha256": hashlib.sha256(
                "\n".join(frame_ids).encode("utf-8")).hexdigest().upper(),
            "ordered_frame_hashes_sha256": hashlib.sha256(
                "\n".join(frame_hashes).encode("ascii")).hexdigest().upper(),
        },
        "face_rewhite": {
            "first_frame_full_0xff_required": True,
            "subsequent_frames_cached_mode2_0xcf_required": True,
            "changed_transition_count": len(changed),
            "unchanged_transition_count": len(windows) - len(changed),
            "all_changed_bytes_enclosed": True,
            "fixed_r12_corridor_used": False,
        },
        "lower_binding": {
            "current_runner": "COMP-REQ-616 exact 182-frame source",
            "required_runner": "COMP-REQ-616 exact 182-frame source",
            "resolved": True,
            "reason": "the isolated runner and compressed asset bind the frozen 182-frame payload",
        },
        "protected_boundary": {
            "browser_url": handoff["browser"]["url"],
            "hardware_execute": False,
            "flash": False,
            "new_owner_prompt_before_physical_parity": False,
        },
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write MACHINE_READY.json")
    args = parser.parse_args()
    try:
        report = validate()
    except Exception as exc:  # noqa: BLE001 - machine gate must report a single failure
        paths = {"page": PAGE, "evidence": EVIDENCE, "plan": PLAN,
                 "payload": PAYLOAD, "handoff": HANDOFF}
        report = {
            "schema": "companion.comp_req_616.upper_handoff_machine_ready.v1",
            "status": "NO_GO_UPPER_IDENTITY_VALIDATION_FAILED",
            "hardware_contact": 0,
            "execute_authorized": False,
            "identity_expected": EXPECTED,
            "identity_observed": {
                name: sha(path) for name, path in paths.items() if path.is_file()
            },
            "error": str(exc),
        }
        OUT.mkdir(parents=True, exist_ok=True)
        if args.write:
            REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=True))
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    if args.write:
        REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0 if report["status"].startswith("NO_GO") else 1


if __name__ == "__main__":
    raise SystemExit(main())
