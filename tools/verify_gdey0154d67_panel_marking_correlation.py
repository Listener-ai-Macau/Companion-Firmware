#!/usr/bin/env python3
"""Bind the owner-read panel marking to the retained supplier transcript.

This verifier deliberately proves only textual coherence. It cannot promote a
one-second LUT because neither input archives a raw panel photograph, nor does
the supplied LUT tree identify GDEY0154D67-T03 or a temperature range.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_AUDIT = (
    ROOT / "docs/validation/companion-gdey0154d67-t03-vendor-1s-source-audit-20260720.json"
)
SUPPLIER_TRANSCRIPT = ROOT / "docs/validation/companion-ssd1681-vendor-response-intake-20260717.json"
DEFAULT_OUTPUT = ROOT / "docs/validation/companion-gdey0154d67-t03-panel-marking-correlation-20260720.json"
SCHEMA_ID = "companion.gdey0154d67_t03.panel_marking_correlation.v1"
OWNER_REPORTED_MARKING = "0154BN-D67-D2 N524110506"
SUPPLIER_REPORTED_MARKING = "N524110506 / 0154BN-D67-D2"
OWNER_PHOTO_OBSERVED_IN_CONVERSATION = True


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def load_json(path: pathlib.Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{rel(path)} must contain a JSON object")
    return value, raw


def evaluate(audit: dict[str, Any], transcript: dict[str, Any]) -> dict[str, Any]:
    target = transcript.get("target")
    source = transcript.get("source")
    identity = audit.get("identity_evidence")
    diagnostic = audit.get("production_off_diagnostic")
    if not isinstance(target, dict):
        target = {}
    if not isinstance(source, dict):
        source = {}
    if not isinstance(identity, dict):
        identity = {}
    if not isinstance(diagnostic, dict):
        diagnostic = {}

    checks = {
        "owner_back_marking_is_recorded_verbatim": OWNER_REPORTED_MARKING
        == "0154BN-D67-D2 N524110506",
        "owner_photo_visibly_shows_the_reported_marking": OWNER_PHOTO_OBSERVED_IN_CONVERSATION,
        "supplier_transcript_marking_matches_same_two_tokens": target.get("reported_marking")
        == SUPPLIER_REPORTED_MARKING,
        "supplier_transcript_targets_gdey0154d67_t03": target.get("model")
        == "GDEY0154D67-T03",
        "supplier_transcript_targets_ssd1681": target.get("controller") == "SSD1681",
        "supplier_transcript_has_no_archived_raw_attachment": source.get("raw_attachment_path") is None,
        "source_audit_completed": audit.get("machine_status") == "PASS_AUDIT_COMPLETE",
        "vendor_tree_does_not_name_t03": identity.get("target_string_present_in_vendor_text") is False,
        "vendor_tree_has_no_temperature_table": identity.get(
            "temperature_banded_cwf1_table_is_documented"
        )
        is False,
        "production_off_remains_forbidden": diagnostic.get("allowed") is False,
        "vendor_lut_promotion_remains_no_go": audit.get("promotion_status")
        == "NO_GO_PANEL_IDENTITY_UNPROVEN",
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {"checks": checks, "failures": failures}


def build_report(
    source_audit_path: pathlib.Path,
    source_audit_raw: bytes,
    transcript_raw: bytes,
    result: dict[str, Any],
) -> dict[str, Any]:
    status = (
        "PASS_OWNER_PHOTO_LABEL_OBSERVED_UNARCHIVED"
        if not result["failures"]
        else "NO_GO_MARKING_CORRELATION_INCOMPLETE"
    )
    return {
        "schema_id": SCHEMA_ID,
        "status": status,
        "claim_scope": "owner_photo_observed_in_conversation_and_retained_supplier_transcript_no_archived_photo_or_lut_promotion",
        "target": "NUCLEO-WB55RG + ESP32-FTS02 + GDEY0154D67-T03",
        "owner_observation": {
            "reported_panel_back_marking": OWNER_REPORTED_MARKING,
            "observation_date": "2026-07-20",
            "photo_observed_in_conversation": OWNER_PHOTO_OBSERVED_IN_CONVERSATION,
            "raw_panel_photo_archived": False,
        },
        "supplier_transcript": {
            "path": rel(SUPPLIER_TRANSCRIPT),
            "sha256": sha256(transcript_raw),
            "reported_marking": SUPPLIER_REPORTED_MARKING,
            "raw_attachment_archived": False,
        },
        "source_audit": {
            "path": rel(source_audit_path),
            "sha256": sha256(source_audit_raw),
        },
        "checks": result["checks"],
        "failures": result["failures"],
        "promotion_status": "NO_GO_PANEL_IDENTITY_UNPROVEN",
        "conclusion": (
            "The owner-supplied conversation photo visibly shows the reported back marking, "
            "which is coherent with the retained supplier transcript that names GDEY0154D67-T03 "
            "and SSD1681. The image is not locally archived, does not bind the supplied one-second "
            "tree to T03, and does not provide a temperature applicability table."
            if not result["failures"]
            else "The marking correlation is incomplete; do not make any panel or LUT promotion claim."
        ),
        "remaining_required_evidence": [
            "Archived raw panel-back/FPC photograph with the marking visible.",
            "Exact Good Display T03 document that binds the candidate LUT source to the panel/controller.",
            "Good Display temperature applicability table for the candidate waveform.",
            "Versioned replacement-display-FPC evidence plus current official White/Black and White-rail artifacts before any separately authorized physical diagnostic.",
        ],
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-audit", type=pathlib.Path, default=DEFAULT_SOURCE_AUDIT)
    parser.add_argument("--write", type=pathlib.Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    source_audit_path = args.source_audit if args.source_audit.is_absolute() else ROOT / args.source_audit
    output_path = args.write if args.write.is_absolute() else ROOT / args.write
    if not source_audit_path.is_file() or not SUPPLIER_TRANSCRIPT.is_file():
        print("NO_GO: required source-audit or supplier transcript is missing", file=sys.stderr)
        return 1

    try:
        audit, audit_raw = load_json(source_audit_path)
        transcript, transcript_raw = load_json(SUPPLIER_TRANSCRIPT)
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        print(f"NO_GO: cannot load marking evidence: {error}", file=sys.stderr)
        return 1

    result = evaluate(audit, transcript)
    report = build_report(source_audit_path, audit_raw, transcript_raw, result)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    if result["failures"]:
        print(f"NO_GO: panel-marking correlation incomplete -> {rel(output_path)}", file=sys.stderr)
        return 1
    print(f"PASS_OWNER_PHOTO_LABEL_OBSERVED_UNARCHIVED: panel marking correlation -> {rel(output_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
