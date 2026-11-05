#!/usr/bin/env python3
"""Generate the reproducible generic-launcher-compatible R6 MACHINE_READY."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/validation/companion-ssd1681-r10-r6-target-unipolar-machine-ready-20260722.json"
STATIC = ROOT / "tools/verify_wb55_ssd1681_r10_r4_corridor_static.py"
R6_FOCUSED = ROOT / "docs/validation/companion-ssd1681-r10-r6-target-unipolar-focused-20260722.json"
R6_SHA = "8525533D1971CE99F46A1AD6580741920B7FA152D2A99632206BE0E17696A5E8"
R9_SHA = "9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD"
RESTORE_SHA = "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    args = argparse.ArgumentParser()
    args.add_argument("--rewrite", action="store_true")
    options = args.parse_args()
    build = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r10_ball"
    paths = {
        "elf": build / "Companion_Nucleo_WB55RG_Ssd1681R10Ball.elf",
        "hex": build / "Companion_Nucleo_WB55RG_Ssd1681R10Ball.hex",
        "driver": ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c",
        "parser": ROOT / "tools/verify_wb55_ssd1681_r10_ball_log.py",
        "monitor": ROOT / "tools/monitor_wb55_ssd1681_phase_parallel_r10_ball.ps1",
        "launcher": ROOT / "tools/start_wb55_ssd1681_phase_parallel_r10_ball.ps1",
        "runner": ROOT / "tools/run_wb55_ssd1681_phase_parallel_r10_ball.ps1",
        "supervisor": ROOT / "tools/supervise_wb55_ssd1681_phase_parallel_r10_ball_prompt.ps1",
        "focused": ROOT / "tools/verify_wb55_ssd1681_r10_r6_target_unipolar.py",
        "work_package": ROOT / "docs/validation/companion-ssd1681-r10-r6-target-unipolar-work-package-20260722.md",
    }
    static_run = subprocess.run([sys.executable, str(STATIC)], cwd=ROOT, capture_output=True, text=True, check=True)
    static_result = json.loads(static_run.stdout.strip().splitlines()[-1])
    focused = json.loads(R6_FOCUSED.read_text(encoding="utf-8"))
    artifacts = {
        "hex": sha(paths["hex"]), "runner": sha(paths["runner"]), "monitor": sha(paths["monitor"]),
        "supervisor": sha(paths["supervisor"]), "launcher": sha(paths["launcher"]),
        "parser_sha256": sha(paths["parser"]), "elf": sha(paths["elf"]),
        "driver": sha(paths["driver"]), "r6_lut": R6_SHA,
        "focused_regression": sha(paths["focused"]), "focused_artifact": sha(R6_FOCUSED),
        "static_verifier": sha(STATIC), "work_package": sha(paths["work_package"]),
    }
    manifest = {
        "schema_id": "companion.wb55.ssd1681.r10_r6_target_unipolar.machine_ready.v1",
        "status": "MACHINE_READY_R10_R6_TARGET_UNIPOLAR_OFFLINE_ONLY",
        "authority": "COMP-REQ-345", "hardware_contact": 0,
        "execute_authorized": False, "authorization_created": False,
        "artifacts": artifacts,
        "protected": {"historical_r9_lut_sha256": R9_SHA, "r6_lut_sha256": R6_SHA, "tail_hex": "221741A83258", "restore_application_sha256": RESTORE_SHA, "r6_vs_r9_changed_offsets": [12, 13, 24, 25], "r6_vs_r5_changed_offsets": [14, 15, 26, 27], "shared_tp_frames": 16, "timing_bytes_60_143_preserved": True},
        "r5_r2_disposition": {"qualification_frames": 16, "loop_iterations": 132, "busy_max_ms": 599, "popup_selected": "失败", "popup_note": "还是一样，就是它移动的时候，屏幕会变成黑白相间的脏，然后再变白。然后呢在不停的移动。但是感觉还是有残留。\r\n", "popup_note_sha256": "59F9E2FB6B5FD9C3F05750D0FD98653ECB90668AA65CC1B342B52693DC8C312B", "postclean": "PASS", "restore_sha256": RESTORE_SHA, "normal_resume": "PASS", "retry_count": 0, "authorization_consumed": True},
        "r6_variable": {"description": "target-unipolar BW/WB with all 16 shared TP frames retained", "bw_net": -16, "wb_net": 16, "ww_net": 0, "bb_net": 0, "non_lut_contract_unchanged": True},
        "focused_evidence": {"status": focused["status"], "static_verifier_status": static_result["status"], "static_verifier_sha256": sha(STATIC), "parser": focused["parser"]},
        "cached_gates": {"unchanged_host_lifecycle_reused_by_sha": True, "checkonly_reused_by_exact_sha": True, "no_checkonly_rerun": True, "no_hardware_contact": True},
    }
    rendered = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if OUT.exists() and OUT.read_bytes() != rendered and not options.rewrite:
        raise RuntimeError("R6 MACHINE_READY exists with non-canonical bytes")
    if not OUT.exists() or options.rewrite:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        temp = OUT.with_name(OUT.name + ".tmp")
        temp.write_bytes(rendered); temp.replace(OUT)
    print(json.dumps({"status": manifest["status"], "sha256": sha(OUT), "artifacts": artifacts, "hardware_contact": 0, "execute_authorized": False, "authorization_created": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
