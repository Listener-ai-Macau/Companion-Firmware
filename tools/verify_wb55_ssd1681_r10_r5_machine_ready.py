#!/usr/bin/env python3
"""Generate the reproducible offline-only R10 R5 MACHINE_READY manifest."""

from __future__ import annotations

import hashlib
import json
import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/validation/companion-ssd1681-r10-r5-polarity-direction-machine-ready-20260722.json"
STATIC_VERIFIER = ROOT / "tools/verify_wb55_ssd1681_r10_r4_corridor_static.py"
R4B_MR_SHA = "F4C1EE53AB729F2817CF7A963F48D9F4D5B48D8C1C208C4093DDA21229C5A8E8"
R9_LUT_SHA = "9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD"
R5_LUT_SHA = "447FB169543F3E33EA6080607B685E2ADB8F38066952FCDF020882359BA94E89"
RESTORE_SHA = "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    arguments = argparse.ArgumentParser()
    arguments.add_argument("--rewrite", action="store_true", help="replace a stale checked-in manifest once")
    args = arguments.parse_args()
    build = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r10_ball"
    paths = {
        "elf": build / "Companion_Nucleo_WB55RG_Ssd1681R10Ball.elf",
        "hex": build / "Companion_Nucleo_WB55RG_Ssd1681R10Ball.hex",
        "driver": ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c",
        "lut": ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c",
        "parser": ROOT / "tools/verify_wb55_ssd1681_r10_ball_log.py",
        "monitor": ROOT / "tools/monitor_wb55_ssd1681_phase_parallel_r10_ball.ps1",
        "launcher": ROOT / "tools/start_wb55_ssd1681_phase_parallel_r10_ball.ps1",
        "runner": ROOT / "tools/run_wb55_ssd1681_phase_parallel_r10_ball.ps1",
        "supervisor": ROOT / "tools/supervise_wb55_ssd1681_phase_parallel_r10_ball_prompt.ps1",
        "focused": ROOT / "tools/verify_wb55_ssd1681_r10_r5_polarity.py",
        "focused_artifact": ROOT / "docs/validation/companion-ssd1681-r10-r5-polarity-focused-20260722.json",
        "work_package": ROOT / "docs/validation/companion-ssd1681-r10-r5-polarity-direction-work-package-20260722.md",
        "static_verifier": STATIC_VERIFIER,
    }
    static_run = subprocess.run([sys.executable, str(paths["static_verifier"])], cwd=ROOT, capture_output=True, text=True, check=True)
    static_result = json.loads(static_run.stdout.strip().splitlines()[-1])
    focused = json.loads(paths["focused_artifact"].read_text(encoding="utf-8"))
    artifacts = {
        # These six names are the stable generic launcher contract.
        "hex": sha(paths["hex"]),
        "runner": sha(paths["runner"]),
        "monitor": sha(paths["monitor"]),
        "supervisor": sha(paths["supervisor"]),
        "launcher": sha(paths["launcher"]),
        "parser_sha256": sha(paths["parser"]),
        "elf": sha(paths["elf"]),
        "driver": sha(paths["driver"]),
        "r5_lut": R5_LUT_SHA,
        "focused_regression": sha(paths["focused"]),
        "focused_artifact": sha(paths["focused_artifact"]),
        "work_package": sha(paths["work_package"]),
        "r4_corridor_static_verifier": sha(paths["static_verifier"]),
    }
    manifest = {
        "schema_id": "companion.wb55.ssd1681.r10_r5_polarity_direction.machine_ready.v1",
        "status": "MACHINE_READY_R10_R5_POLARITY_DIRECTION_OFFLINE_ONLY",
        "authority": "COMP-REQ-343",
        "hardware_contact": 0,
        "execute_authorized": False,
        "authorization_created": False,
        "artifacts": artifacts,
        "protected": {
            "historical_r9_lut_sha256": R9_LUT_SHA,
            "r5_lut_sha256": R5_LUT_SHA,
            "tail_hex": "221741A83258",
            "restore_application_sha256": RESTORE_SHA,
            "r5_changed_offsets": [12, 13, 14, 15, 24, 25, 26, 27],
            "r5_shared_bytes_preserved": 151,
        },
        "r4b_disposition": {
            "output_root": ".cache/validation/wb55-r10-r4b-corridor-execute-20260722-r1",
            "qualification_frames": 16,
            "loop_iterations": 68,
            "busy_max_ms": 597,
            "popup_count": 1,
            "popup_selected": "失败",
            "popup_note": "还是跟以前的那个效果是一样的，没有丝毫的改变。\r\n",
            "popup_note_sha256": "A4F368D7D4B670CF48F39642327F68DC01DA9240612573BA8DFC42BDF12562A",
            "visual_verdict": "FAIL_FIXED_CORRIDOR_NOT_A_VISUAL_REPAIR",
            "postclean": "PASS",
            "restore_sha256": RESTORE_SHA,
            "normal_resume": "PASS",
            "retry_count": 0,
            "authorization_consumed": True,
        },
        "r5_variable": {
            "description": "only R5 polarity-direction reversal in the dedicated 159-byte LUT",
            "old_lut_sha256": R9_LUT_SHA,
            "new_lut_sha256": R5_LUT_SHA,
            "changed_offsets": [12, 13, 14, 15, 24, 25, 26, 27],
            "direction": "BW_VSH1_to_VSL_and_WB_VSL_to_VSH1",
            "non_lut_contract_unchanged": True,
        },
        "focused_evidence": {
            "status": focused["status"],
            "r4_corridor_static_verifier_status": static_result["status"],
            "r4_corridor_static_verifier_sha256": sha(paths["static_verifier"]),
            "positive_schema_v4_busy_599": focused["parser"]["positive_schema_v4"],
            "negative_cases": focused["parser"]["negative_fixtures"] + [focused["direction_negative"]],
        },
        "cached_gates": {
            "r4b_machine_ready_sha256": R4B_MR_SHA,
            "unchanged_host_lifecycle_reused_by_sha": True,
            "checkonly_reused_by_exact_sha": True,
            "no_checkonly_rerun": True,
            "no_hardware_contact": True,
        },
    }
    rendered = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if OUT.exists() and OUT.read_bytes() != rendered and not args.rewrite:
        raise RuntimeError("R5 MACHINE_READY exists with non-canonical bytes")
    if not OUT.exists() or args.rewrite:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        temporary = OUT.with_name(OUT.name + ".tmp")
        temporary.write_bytes(rendered)
        temporary.replace(OUT)
    print(json.dumps({"status": manifest["status"], "path": str(OUT), "sha256": sha(OUT), "artifacts": artifacts, "hardware_contact": 0, "execute_authorized": False, "authorization_created": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
