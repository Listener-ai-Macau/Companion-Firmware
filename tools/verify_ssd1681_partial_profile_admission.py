#!/usr/bin/env python3
"""Fail closed until a local SSD1681 optical profile is bound to the panel."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
VENDOR_EPAPER = pathlib.Path(
    r"C:\Users\Billy\Desktop\GDEH0154D67-20211203-P-LUT(1s) -1s快刷\EPD_W21\EPAPER.c"
)
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
REQUIREMENTS = ROOT / "docs/companion_product_requirements.md"
SOURCE_RESEARCH = ROOT / "docs/validation/companion-ssd1681-local-update-research-20260720.md"
VENDOR_PARTIAL_NO_GO = ROOT / (
    "docs/validation/companion-gdey0154d67-t03-vendor-partial-slow-motion-residue-triage-20260720.json"
)
MICRO_DELTA_NO_GO = ROOT / "docs/validation/companion-wb55-micro-delta-visual-no-go-20260720.json"
VENDOR_1S_NO_GO = ROOT / (
    "docs/validation/companion-gdey0154d67-t03-vendor-1s-final-disposition-20260720.json"
)
DEFAULT_OUT = ROOT / "docs/validation/companion-ssd1681-partial-profile-admission-20260720.json"
SCHEMA_ID = "companion.ssd1681.partial_profile_admission.v1"


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def relative(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{relative(path)} is not a JSON object")
    return value


def evaluate() -> tuple[dict[str, Any], bool]:
    inputs = (
        VENDOR_EPAPER,
        DRIVER,
        REQUIREMENTS,
        SOURCE_RESEARCH,
        VENDOR_PARTIAL_NO_GO,
        MICRO_DELTA_NO_GO,
        VENDOR_1S_NO_GO,
    )
    missing = [relative(path) for path in inputs if not path.is_file()]
    if missing:
        return (
            {
                "schema_id": SCHEMA_ID,
                "status": "FAIL_INPUT_MISSING",
                "failures": missing,
            },
            False,
        )

    vendor_source = VENDOR_EPAPER.read_text(encoding="utf-8", errors="replace")
    driver_source = DRIVER.read_text(encoding="utf-8-sig", errors="replace")
    requirements = REQUIREMENTS.read_text(encoding="utf-8-sig", errors="replace")
    research = SOURCE_RESEARCH.read_text(encoding="utf-8-sig", errors="replace")
    partial_no_go = load_json(VENDOR_PARTIAL_NO_GO)
    micro_delta_no_go = load_json(MICRO_DELTA_NO_GO)
    vendor_1s_no_go = load_json(VENDOR_1S_NO_GO)

    checks = {
        "supplier_partial_route_is_distinct_from_159_byte_full_lut": all(
            token in vendor_source
            for token in (
                "void EPD_Dis_Part_myself",
                "Epaper_Write_Data(0xFF)",
                "void EPD_Update_LUT",
                "Epaper_Write_Data(0xC7)",
                "for(i=0;i<5000;i++)",
            )
        ),
        "driver_preserves_byte_aligned_changed_window_transport": all(
            token in driver_source
            for token in (
                "static ssd1681_window_t ssd1681_window_from_difference(void)",
                "ssd1681_write_plane_region(0x26u, s_previous_frame, &window)",
                "ssd1681_write_plane_region(0x24u, s_frame, &window)",
            )
        ),
        "supplier_partial_physical_result_is_no_go": partial_no_go.get("status")
        == "NO_GO_PHYSICAL_CONTINUOUS_PARTIAL_RESIDUE",
        "minimum_payload_physical_result_is_no_go": micro_delta_no_go.get("status")
        == "NO_GO_VISIBLE_GLOBAL_FLUSH_OR_DIRTYING",
        "full_frame_159_byte_lut_visual_result_is_no_go": vendor_1s_no_go.get("status")
        == "FAIL_OWNER_REJECTED_SINGLE_FLASH_VENDOR_1S_LUT",
        "registry_forbids_repeating_payload_or_cadence_experiments": "COMP-REQ-222" in requirements
        and "do not re-run the four-byte `0xFC` motion image" in requirements,
        "registry_records_no_repeated_rail_or_white_black_runs": "COMP-REQ-226" in requirements
        and "Do not re-run rail, White/Black" in requirements,
        "research_states_ram_local_is_not_optically_local": "**RAM\nwrite** mechanism" in research
        and "clean\nlocal **optical** refresh" in research,
    }
    failures = [name for name, passed in checks.items() if not passed]
    audited = not failures
    status = "NO_GO_UNBOUND_PANEL_PARTIAL_PROFILE" if audited else "FAIL_AUDIT_DRIFT"
    report = {
        "schema_id": SCHEMA_ID,
        "status": status,
        "machine_status": "PASS_AUDIT_FAIL_CLOSED" if audited else "FAIL_AUDIT_DRIFT",
        "claim_scope": "no-hardware lower-driver profile admission audit; not a waveform, panel identity, temperature, or production claim",
        "hardware_action": "none; duplicate White/Black and rail measurement were explicitly stopped",
        "source_manifest": {
            "supplier_epaper_c": {
                "path": relative(VENDOR_EPAPER),
                "sha256": digest(VENDOR_EPAPER),
            },
            "current_driver": {"path": relative(DRIVER), "sha256": digest(DRIVER)},
            "input_artifacts": [
                {"path": relative(path), "sha256": digest(path)}
                for path in (SOURCE_RESEARCH, VENDOR_PARTIAL_NO_GO, MICRO_DELTA_NO_GO, VENDOR_1S_NO_GO)
            ],
        },
        "checks": checks,
        "failures": failures,
        "admission": {
            "production_profile_allowed": False,
            "new_diagnostic_allowed": False,
            "reason": (
                "Local RAM transport is proven, but every available optical route is rejected: "
                "supplier 0xFF local motion leaves residue, four-byte 0xFC motion still looks broad/dirty, "
                "and the source-bound 159-byte C7 route flashes black per full frame."
            ),
            "forbidden_actions": [
                "Repeat White, Black, or rail measurement as a waveform substitute.",
                "Repeat payload-size, cadence, or existing local-motion diagnostics.",
                "Promote 0xFC, 0xFF, or the 159-byte LUT into production as a clean local optical profile.",
                "Invent, tune, interpolate, or import a LUT or waveform.",
            ],
        },
        "required_vendor_evidence_for_reconsideration": [
            "Written mapping from physical FPC marking 0154BN-D67-D2 to the exact panel/module and controller profile.",
            "Exact residue-controlled partial-refresh profile for that marking: external LUT bytes and load order, or a complete OTP/profile-selection flow.",
            "Temperature envelope, thresholds or sensor-selection rules, and behavior outside the supported range.",
            "Required base-map sequence, including 0x24 and 0x26 plane roles, data polarity, reset duration, border setting, RAM orientation, and 0x22 control.",
            "Maximum consecutive local updates and the required cleanup behavior, including whether a no-black-flash cleanup exists.",
        ],
    }
    return report, audited


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report, audited = evaluate()
    rendered = json.dumps(report, ensure_ascii=True, indent=2) + "\n"
    if args.write:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="ascii")
    print(rendered, end="")
    return 0 if audited else 1


if __name__ == "__main__":
    sys.exit(main())
