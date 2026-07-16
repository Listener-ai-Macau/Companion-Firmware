#!/usr/bin/env python3
"""Verify the immutable Companion v9 art baseline before any renderer runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import struct
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
ART_DIR = ROOT / "docs/art/iterations/companion-pet-expression-v9"
SOURCE = ART_DIR / "generated_pet_expression_sheet_v9_candidate.png"
EXPECTED_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
EXPECTED_SIZE = (1254, 1254)
REPORT = ROOT / "docs/validation/companion-v9-art-baseline-20260716.json"


def png_size(path: pathlib.Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError("source is not a PNG with an IHDR header")
    return struct.unpack(">II", data[16:24])


def read_json(path: pathlib.Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    errors: list[str] = []
    source_sha256 = hashlib.sha256(SOURCE.read_bytes()).hexdigest().upper()
    try:
        source_size = png_size(SOURCE)
    except (OSError, ValueError) as exc:
        source_size = (0, 0)
        errors.append(str(exc))
    if source_sha256 != EXPECTED_SHA256:
        errors.append("v9 source SHA-256 does not match the owner-approved lock")
    if source_size != EXPECTED_SIZE:
        errors.append("v9 source dimensions do not match the owner-approved lock")

    generation = read_json(ART_DIR / "generation-request.json")
    ledger = read_json(ART_DIR / "iteration-ledger.json")
    lock = read_json(ART_DIR / "baseline-lock.json")
    source_path = "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"

    if generation.get("status") != "OWNER_APPROVED_BASELINE_LOCKED":
        errors.append("generation request is not owner-approved baseline locked")
    if generation.get("generated_output", {}).get("sha256", "").upper() != EXPECTED_SHA256:
        errors.append("generation output hash does not match the baseline")
    if ledger.get("baseline", {}).get("accepted_source") != source_path:
        errors.append("iteration ledger accepted source drifted")
    if ledger.get("baseline", {}).get("sha256", "").upper() != EXPECTED_SHA256:
        errors.append("iteration ledger source hash drifted")
    if ledger.get("baseline", {}).get("comparison_artifact") != (
        "docs/art/iterations/companion-pet-expression-v9/baseline-lock.json"
    ):
        errors.append("iteration ledger does not point to the retained baseline lock")
    accepted = lock.get("accepted_source", {})
    if accepted.get("path") != source_path or accepted.get("sha256", "").upper() != EXPECTED_SHA256:
        errors.append("baseline lock source identity drifted")
    if tuple(accepted.get("dimensions_px", ())) != EXPECTED_SIZE:
        errors.append("baseline lock dimensions drifted")
    if lock.get("status") != "OWNER_APPROVED_SOURCE_LOCKED_MACHINE_RENDER_AUTHORIZED":
        errors.append("baseline lock does not authorize only the machine render scope")

    report = {
        "schema": "companion.v9_art_baseline_verification.v1",
        "status": "PASS_SOURCE_INTEGRITY_MACHINE_RENDER_PENDING" if not errors else "FAIL",
        "source": source_path,
        "source_sha256": source_sha256,
        "source_dimensions_px": list(source_size),
        "machine_render_authorized": not errors,
        "runtime_resource_activated": False,
        "physical_or_owner_visual_pass": False,
        "errors": errors,
    }
    if args.write:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: v9 owner-approved source, lock, prompt record, and ledger agree.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
