#!/usr/bin/env python3
"""Archive the owner-authorized replacement-display-FPC evidence for White only."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/validation/companion-screen-wb55-replacement-fpc-evidence-20260720.json"
SCHEMA_ID = "companion.wb55.display_fpc_replacement_evidence.v1"


def build_report() -> dict[str, Any]:
    checks = {
        "owner_photo_observed_in_conversation": True,
        "panel_back_marking_visible": True,
        "display_fpc_replaced": True,
        "current_dynamic_expressions_visible": True,
        "logic_input_is_3v3_only": True,
        "one_second_lut_remains_prohibited": True,
        "authorization_is_white_official_path_only": True,
    }
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS_OWNER_REPORTED_REPLACEMENT_FPC_CURRENT_PANEL_VISIBLE",
        "claim_scope": "owner_photo_and_owner_statement_only_authorizes_one_official_white_retest_not_panel_or_lut_acceptance",
        "target": "NUCLEO-WB55RG + ESP32-FTS02 + GDEY0154D67-T03",
        "owner_observation": {
            "observation_date": "2026-07-20",
            "panel_back_marking": "0154BN-D67-D2 N524110506",
            "photo_observed_in_conversation": True,
            "raw_photo_archived_locally": False,
            "historical_failure_cause": "old display FPC was broken",
            "replacement_display_fpc_installed": True,
            "current_dynamic_expressions_visible": True,
            "adapter_logic_supply": "3.3V only",
        },
        "checks": checks,
        "authorization": {
            "allowed_stage": "White",
            "allowed_path": "existing matched official 0x24 one-plane then 0x22=0xF7, 0x20, BUSY",
            "black_requires": "PASS_MACHINE_AND_RAILS_ESTABLISHED_WHITE",
            "prohibited": [
                "0xC7 or one-second LUT load",
                "production refresh-policy modification",
                "custom or guessed waveform",
                "Black before new White rail evidence",
                "physical success claim before source-bound trace and canonical White review",
            ],
        },
        "historical_evidence": {
            "old_white_failure": "docs/validation/companion-screen-wb55-white-recovery-failure-20260719.json",
            "disposition": "retained_history_for_old_broken_fpc_not_current_fts02_or_panel_diagnosis",
        },
        "failures": [],
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=pathlib.Path, default=OUTPUT)
    args = parser.parse_args(argv)
    output = args.write if args.write.is_absolute() else ROOT / args.write
    report = build_report()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PASS: replacement display-FPC evidence -> {output.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
