#!/usr/bin/env python3
"""Focused no-hardware regression for the R4 fixed-corridor telemetry repair."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
sys.path.insert(0, str(ROOT / "tools"))
import verify_wb55_ssd1681_r10_ball_log as parser  # noqa: E402

EXPECTED = {
    "white": "51CFA32FECE0135F38198DA2529E7C6A0C1F53747984D55705077B7F6920CC76",
    "32": "51ECCB35B2C3D9CA78D193482D623F0809D1F094D0804E10ABE677C11D0BC930",
    "40": "B96DFF5E9B1B552B49C7B3A0DE5228A2761319007565E807B610785A5D7B1B06",
    "48": "82D7C8ED67824AEDF8DD7E0DE02B5C7D375A5F11AD9731B24C87E063221416BB",
    "56": "933CD8FFC54D7BB04C3EB45460303613D3860EADDC959A5D117196ED4B467862",
    "64": "5740CC300E6C89757B0588D495F2C2943917933FCBC9190B5432E9D126F160F8",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    driver = DRIVER.read_text(encoding="utf-8")
    source_checks = {
        "position_keyed_helper": "static const char *ssd1681_r10_payload_sha256(uint8_t x)" in driver,
        "all_six_constants": all(value in driver for value in EXPECTED.values()),
        "previous_and_current_use_same_helper": "ssd1681_r10_payload_sha256(previous_x)" in driver and "ssd1681_r10_payload_sha256(current_x)" in driver,
        "direction_only_reporters_removed": "ssd1681_r10_previous_payload_sha256" not in driver and "ssd1681_r10_current_payload_sha256" not in driver and "CEA57CB2BAD8C7E416FACB829DC10D78BF8D6A7E9702A085868BBB2B131D2079" not in driver and "E3A7157D2E4A9C6E8E9EDDAC812F52551959574F23784425614C23318FE6B1AC" not in driver,
    }
    corrected = parser.r4_frame_line("loop_iteration", 1, 40, 32, busy=599)
    parser.validate_loop_line(corrected, 1, 40, 32)
    stale = corrected.replace(EXPECTED["40"], "E3A7157D2E4A9C6E8E9EDDAC812F52551959574F23784425614C23318FE6B1AC", 1).replace(EXPECTED["32"], "CEA57CB2BAD8C7E416FACB829DC10D78BF8D6A7E9702A085868BBB2B131D2079", 1)
    try:
        parser.validate_loop_line(stale, 1, 40, 32)
    except parser.LogFailure:
        stale_outcome = "REJECTED"
    else:
        raise SystemExit("R4b stale captured payload hashes were accepted")
    corrected_from_stale = stale.replace("E3A7157D2E4A9C6E8E9EDDAC812F52551959574F23784425614C23318FE6B1AC", EXPECTED["40"], 1).replace("CEA57CB2BAD8C7E416FACB829DC10D78BF8D6A7E9702A085868BBB2B131D2079", EXPECTED["32"], 1)
    parser.validate_loop_line(corrected_from_stale, 1, 40, 32)
    additional = corrected_from_stale.replace("busy_elapsed_ms=599", "busy_elapsed_ms=601", 1)
    try:
        parser.validate_loop_line(additional, 1, 40, 32)
    except parser.LogFailure:
        additional_outcome = "REJECTED"
    else:
        raise SystemExit("R4b additional mutation was accepted")
    result = {
        "schema_id": "companion.wb55.ssd1681.r10_r4b.telemetry_repair.v1",
        "status": "PASS_R10_R4B_TELEMETRY_REPAIR_FOCUSED",
        "authority": "COMP-REQ-339",
        "source_checks": source_checks,
        "captured_loop_iteration_1": {"status": "PASS_R10_LOOP_FRAME", "previous_x": 40, "current_x": 32, "busy_elapsed_ms": 599, "previous_payload_sha256": EXPECTED["40"], "current_payload_sha256": EXPECTED["32"]},
        "focused_outcomes": {"corrected_schema_v3_loop_iteration_1": "PASS", "stale_captured_shape": stale_outcome, "only_two_hash_corrections": "PASS", "additional_mutation": additional_outcome},
        "driver_sha256": sha(DRIVER),
        "lut_sha256": parser.oracle.LUT_SHA256,
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if all(source_checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
