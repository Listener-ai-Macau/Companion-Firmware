#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOADER = ROOT / "cubeide/Companion_BLE_Ota_Loader/build/Companion_BLE_Ota_Loader.hex"
APP = (
    ROOT
    / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_comp_req_771_current_ota_product"
    / "Companion_Nucleo_WB55RG_Bringup.hex"
)
CEMP = (
    ROOT
    / ".cache/validation/comp-req-771-browser-life-source-pack-auto/cemp"
    / "comp_req_771_browser_life.cemp"
)
CEMP_MANIFEST = (
    ROOT
    / ".cache/validation/comp-req-771-browser-life-source-pack-auto/cemp"
    / "manifest.json"
)
def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def parse_ihex(path: Path) -> dict[int, int]:
    memory: dict[int, int] = {}
    upper = 0
    for line in path.read_text(encoding="ascii").splitlines():
        if not line.startswith(":"):
            continue
        record = bytes.fromhex(line[1:])
        length = record[0]
        address = int.from_bytes(record[1:3], "big")
        kind = record[3]
        data = record[4 : 4 + length]
        if kind == 0:
            for offset, value in enumerate(data):
                memory[upper + address + offset] = value
        elif kind == 2:
            upper = int.from_bytes(data, "big") << 4
        elif kind == 4:
            upper = int.from_bytes(data, "big") << 16
    if not memory:
        raise RuntimeError(f"no data records: {path}")
    return memory


def compare_image(memory: dict[int, int], readback: bytes) -> dict:
    mismatches = []
    for address, expected in memory.items():
        offset = address - 0x08000000
        observed = readback[offset] if 0 <= offset < len(readback) else None
        if observed != expected:
            mismatches.append(
                {
                    "address": f"0x{address:08X}",
                    "expected": expected,
                    "observed": observed,
                }
            )
            if len(mismatches) >= 16:
                break
    return {
        "defined_bytes": len(memory),
        "mismatch_count_capped": len(mismatches),
        "first_mismatches": mismatches,
        "matches": not mismatches,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    args = parser.parse_args()
    run_root = Path(args.run_root).resolve()
    backup_a = run_root / "private/preflash-full-a.bin"
    backup_b = run_root / "private/preflash-full-b.bin"
    final_readback = run_root / "private/final-full-readback.bin"
    serial_log = run_root / "hardware-serial.log"
    programmer_calls_log = run_root / "programmer-calls.json"
    precheck = json.loads(
        (
            ROOT
            / ".cache/validation/comp-req-771-same-source-flash/PRECHECK_READY.json"
        ).read_text(encoding="utf-8")
    )
    serial = serial_log.read_text(encoding="utf-8-sig", errors="replace")
    post_reset_marker = "--- POST-READBACK PRODUCT BOOT ---"
    final_serial = serial.rsplit(post_reset_marker, 1)[-1]
    accepted_refreshes = re.findall(
        r"accepted_product_driver .*changed=1 control=0x([0-9A-Fa-f]+) "
        r"bytes=(\d+) transaction_ms=(\d+) busy_ms=(\d+) .*"
        r"transport=(\S+) has_busy=(\d+) result=1",
        final_serial,
    )
    accepted_controls = [match[0].upper() for match in accepted_refreshes]
    accepted_bytes = [int(match[1]) for match in accepted_refreshes]
    accepted_transactions = [int(match[2]) for match in accepted_refreshes]
    accepted_busy = [int(match[3]) for match in accepted_refreshes]
    accepted_transports = [match[4] for match in accepted_refreshes]
    accepted_has_busy = [int(match[5]) for match in accepted_refreshes]
    motion_matches = re.findall(
        r"\[screen-motion\] auto_complete .*interval_ms=(\d+).*phase=(\d+)",
        final_serial,
    )
    motion_intervals = [int(interval) for interval, _phase in motion_matches]
    motion_phases = [int(phase) for _interval, phase in motion_matches]
    life_matches = re.findall(
        r"\[screen-life\] family=(\w+) action=(\w+) episode=(\d+) "
        r"phrase=(\d+) phase=(\w+) variation=(\d+) dwell_commits=(\d+) "
        r"clip=(\S+) frame_index=(\d+)",
        final_serial,
    )
    life_beats = [
        {
            "family": match[0],
            "action": match[1],
            "episode": int(match[2]),
            "phrase": int(match[3]),
            "phase": match[4],
            "variation": int(match[5]),
            "dwell_commits": int(match[6]),
            "clip": match[7],
            "frame_index": int(match[8]),
        }
        for match in life_matches
    ]
    cemp_manifest = json.loads(CEMP_MANIFEST.read_text(encoding="utf-8"))
    life_frame_indices: dict[str, int] = {}
    frame_cursor = 0
    for clip in cemp_manifest["clips"]:
        if clip["name"].startswith("life_"):
            life_frame_indices[clip["name"]] = frame_cursor
        frame_cursor += len(clip["frames"])
    allowed_families = {
        "calm",
        "curious",
        "warm",
        "delighted",
        "thoughtful",
        "alert",
    }
    phase_indices = {
        "hold": 0,
        "orient": 1,
        "anticipate": 2,
        "accent": 3,
        "follow": 4,
        "settle": 5,
    }
    verified_life_prefix = life_beats[:6]
    life_semantics_exact = len(verified_life_prefix) == 6
    expected_motion_phases = []
    for beat in verified_life_prefix:
        clip_pattern = (
            rf"life_{re.escape(beat['family'])}_e{beat['episode']}_s\d+_"
            rf"{re.escape(beat['action'])}_{re.escape(beat['phase'])}"
        )
        if (
            beat["family"] not in allowed_families
            or not 0 <= beat["episode"] < 32
            or re.fullmatch(clip_pattern, beat["clip"]) is None
            or life_frame_indices.get(beat["clip"]) != beat["frame_index"]
            or beat["phase"] not in phase_indices
        ):
            life_semantics_exact = False
        else:
            expected_motion_phases.append(phase_indices[beat["phase"]])

    final = final_readback.read_bytes()
    loader_compare = compare_image(parse_ihex(LOADER), final)
    app_compare = compare_image(parse_ihex(APP), final)
    programmer_calls = json.loads(
        programmer_calls_log.read_text(encoding="utf-8-sig")
    )
    programmer_arguments = "\n".join(call["arguments"] for call in programmer_calls)
    pack = precheck["cemp"]
    pack_pattern = (
        rf"pack=comp_req_638_browser_epaper_external_nor "
        rf"revision=638 clips={pack['clip_count']} frames={pack['frame_count']}"
    )
    required_serial = {
        "application_booted": bool(re.search(r"\[stage\] uart ok", final_serial)),
        "external_store_ready": bool(
            re.search(
                r"\[screen-assets\].*store=ready.*identity=comp_req_638.*mount=ok",
                final_serial,
            )
        ),
        "exact_pack_mounted": bool(re.search(pack_pattern, final_serial)),
        "browser_life_cemp_provisioned": bool(
            re.search(
                r"\[screen-assets-provision\] result=pass "
                r"action=(?:already_current|erase_write_verify|"
                r"already_current_chunk|erase_write_verify_chunk)",
                serial,
            )
        ),
        "post_readback_reset_boot_captured": post_reset_marker in serial,
        "accepted_driver_refreshed_life_beats": (
            len(accepted_refreshes) >= 6
        ),
        "accepted_driver_matches_comp_req_616_baseline": (
            len(accepted_refreshes) >= 6
            and accepted_controls[0] == "FF"
            and accepted_bytes[0] == 5000
            and accepted_controls[1:6] == ["CF"] * 5
            and accepted_bytes[1:6] == [2772] * 5
        ),
        "accepted_driver_observed_real_panel_busy": (
            len(accepted_busy) >= 6
            and all(0 < elapsed <= 600 for elapsed in accepted_busy)
        ),
        "accepted_driver_within_physical_refresh_budget": (
            len(accepted_transactions) >= 6
            and all(0 < elapsed <= 700 for elapsed in accepted_transactions)
        ),
        "accepted_driver_restored_comp_req_616_transport": (
            len(accepted_transports) >= 6
            and all(
                transport == "software_direct_bsrr_diagnostic"
                for transport in accepted_transports
            )
            and all(has_busy == 1 for has_busy in accepted_has_busy)
        ),
        "automatic_motion_completed_life_beats": (
            len(motion_intervals) >= 6
        ),
        "browser_life_semantics_and_frame_indices_exact": life_semantics_exact,
        "automatic_motion_phase_order": (
            len(expected_motion_phases) == 6
            and motion_phases[:6] == expected_motion_phases
        ),
        "motion_intervals_within_contract": (
            len(motion_intervals) >= 6
            and all(
                interval in (480, 960, 1440, 1920)
                for interval in motion_intervals
            )
        ),
        "motion_intervals_non_equidistant": (
            len(motion_intervals) >= 6
            and len(set(motion_intervals)) >= 2
        ),
    }
    forbidden_serial = {
        "hardfault": bool(re.search(r"hard.?fault", final_serial, re.IGNORECASE)),
        "panel_error": bool(
            re.search(
                r"\[epaper\].*(?:error|result=0)", final_serial, re.IGNORECASE
            )
        ),
    }
    forbidden_programmer = {
        "mass_erase": bool(
            re.search(
                r"(?:^|\s)(?:-e\s+all|-massErase)(?:\s|$)",
                programmer_arguments,
                re.I,
            )
        ),
        "read_unprotect": bool(
            re.search(r"(?:^|\s)-rdu(?:\s|$)", programmer_arguments, re.I)
        ),
        "option_bytes": bool(
            re.search(r"(?:^|\s)-ob(?:\s|$)", programmer_arguments, re.I)
        ),
    }
    checks = {
        "offline_precheck_ready": (
            precheck["status"] == "PRECHECK_READY"
            and all(precheck["checks"].values())
        ),
        "dual_backup_524288": (
            backup_a.stat().st_size == 0x80000
            and backup_b.stat().st_size == 0x80000
        ),
        "dual_backup_identical": backup_a.read_bytes() == backup_b.read_bytes(),
        "final_readback_524288": len(final) == 0x80000,
        "loader_readback_matches": loader_compare["matches"],
        "app_readback_matches": app_compare["matches"],
        "all_required_serial_evidence": all(required_serial.values()),
        "no_forbidden_serial_evidence": not any(forbidden_serial.values()),
        "no_forbidden_programmer_operation": not any(
            forbidden_programmer.values()
        ),
        "same_cemp_identity": precheck["cemp"]["sha256"] == sha256(CEMP),
        "same_app_identity": (
            precheck["images"]["app"]["sha256"] == sha256(APP)
        ),
        "same_loader_identity": (
            precheck["images"]["loader"]["sha256"] == sha256(LOADER)
        ),
    }
    status = "MACHINE_READY" if all(checks.values()) else "NO_GO"
    artifact = {
        "schema": "companion.comp_req_771.hardware_result.v2",
        "requirement": "COMP-REQ-771",
        "status": status,
        "hardware_contact": 1,
        "flash": True,
        "reset": True,
        "backup": {
            "bytes": backup_a.stat().st_size,
            "sha256": sha256(backup_a),
            "dual_identical": backup_a.read_bytes() == backup_b.read_bytes(),
        },
        "final_readback": {
            "bytes": len(final),
            "sha256": sha256(final_readback),
            "loader": loader_compare,
            "app": app_compare,
        },
        "images": {
            "loader_sha256": sha256(LOADER),
            "app_sha256": sha256(APP),
            "cemp_sha256": precheck["cemp"]["sha256"],
            "cemp_bytes": pack["bytes"],
            "cemp_clip_count": pack["clip_count"],
            "cemp_frame_count": pack["frame_count"],
        },
        "serial": {
            "required": required_serial,
            "forbidden": forbidden_serial,
            "accepted_refresh_count": len(accepted_refreshes),
            "accepted_transaction_ms": accepted_transactions,
            "accepted_busy_ms": accepted_busy,
            "accepted_controls": accepted_controls,
            "accepted_transferred_bytes": accepted_bytes,
            "accepted_transports": accepted_transports,
            "accepted_has_busy": accepted_has_busy,
            "motion_intervals_ms": motion_intervals,
            "motion_phases": motion_phases,
            "life_beats": life_beats,
            "verified_life_prefix": verified_life_prefix,
            "expected_motion_phases": expected_motion_phases,
            "log_sha256": sha256(serial_log),
        },
        "programmer_forbidden": forbidden_programmer,
        "checks": checks,
    }
    output = run_root / "MACHINE_READY.json"
    output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "artifact": str(output)}))
    return 0 if status == "MACHINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
