#!/usr/bin/env python3
"""Seal the deterministic, no-hardware R10 MACHINE_READY evidence."""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
import shutil
from pathlib import Path
from verify_wb55_ssd1681_r10_ball_pixel_oracle import parse_c_array, LUT_SHA256

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/validation/companion-ssd1681-r10-r2-finalization-machine-ready-20260722.json"
BUILD = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r10_ball"
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
TOOLS = {
    "runner": ROOT / "tools/run_wb55_ssd1681_phase_parallel_r10_ball.ps1",
    "monitor": ROOT / "tools/monitor_wb55_ssd1681_phase_parallel_r10_ball.ps1",
    "supervisor": ROOT / "tools/supervise_wb55_ssd1681_phase_parallel_r10_ball_prompt.ps1",
    "launcher": ROOT / "tools/start_wb55_ssd1681_phase_parallel_r10_ball.ps1",
}
ORACLE = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r10-ball-pixel-oracle-20260722.json"
STATIC = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r10-ball-static-20260722.json"
PARSER = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r10-ball-log-parser-20260722.json"
PARSER_TOOL = ROOT / "tools/verify_wb55_ssd1681_r10_ball_log.py"
LIFECYCLE = ROOT / "docs/validation/companion-ssd1681-r10-ball-lifecycle-static-20260722.json"
CHECK_ROOT = ROOT / ".cache/validation/r10-ball-machine-ready-rework-checkonly-20260722"
LUT = bytes(parse_c_array(DRIVER.read_text(encoding="utf-8"), "ssd1681_phase_parallel_r9_lut"))

def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def run(command: list[str]) -> None:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, encoding="utf-8", timeout=180)
    if result.returncode: raise RuntimeError(f"command failed: {' '.join(command)}\n{result.stdout}\n{result.stderr}")
def checkonly() -> dict:
    expected_parent = ROOT / ".cache/validation"
    if CHECK_ROOT.parent != expected_parent or CHECK_ROOT.name != "r10-ball-machine-ready-rework-checkonly-20260722":
        raise RuntimeError("refusing to recreate an unexpected CheckOnly root")
    if CHECK_ROOT.exists():
        shutil.rmtree(CHECK_ROOT)
    launch = CHECK_ROOT / "persistent-launch.json"
    run(["pwsh", "-NoProfile", "-File", str(TOOLS["launcher"]), "-CheckOnly", "-OutRoot", str(CHECK_ROOT)])
    data = json.loads(launch.read_text(encoding="utf-8-sig")); stage = json.loads((CHECK_ROOT / "stage-run.json").read_text(encoding="utf-8-sig"))
    required = data.get("status") == "READY_NO_HARDWARE_CONTACT" and data.get("hardware_contact") == 0 and data.get("write_counter_sum") == 0 and data.get("popup_count") == 0 and data.get("retry_count") == 0 and data.get("child_exited") is True and stage.get("checkonly", {}).get("telemetry_ring_bytes") == 65536 and stage.get("checkonly", {}).get("telemetry_ring_fixed") is True and all(c.get("child_exited") is True and c.get("exit_code") == 0 for c in stage.get("checkonly", {}).get("children", []))
    if not required: raise RuntimeError("R10 CheckOnly counters or child-exit evidence failed")
    return {"status": data["status"], "hardware_contact": 0, "writes": 0, "popup": 0, "retry": 0, "fixed_ring_bytes": 65536, "child_exited": True, "children": stage["checkonly"]["children"], "durable_stdout_stderr": True, "evidence_root": str(CHECK_ROOT.relative_to(ROOT)).replace("\\", "/")}
def build() -> dict:
    run([sys.executable, "tools/verify_wb55_ssd1681_r10_ball_pixel_oracle.py"])
    run([sys.executable, "tools/verify_wb55_ssd1681_r10_ball_static.py"])
    run([sys.executable, "tools/verify_wb55_ssd1681_r10_ball_log.py"])
    run([sys.executable, "tools/verify_wb55_ssd1681_r10_ball_lifecycle_static.py", "--write"])
    run([sys.executable, "tools/verify_companion_product_requirements.py"])
    run([sys.executable, "tools/verify_companion_current_goal_audit_r10.py"])
    if sha(BUILD / "Companion_Nucleo_WB55RG_Ssd1681R10Ball.elf") == "" or not (BUILD / "Companion_Nucleo_WB55RG_Ssd1681R10Ball.hex").is_file(): raise RuntimeError("R10 ELF/HEX missing")
    if hashlib.sha256(LUT).hexdigest().upper() != LUT_SHA256: raise RuntimeError("R9 LUT hash drift")
    return {"schema_id": "companion.wb55.ssd1681.r10_ball.machine_ready.v4", "status": "MACHINE_READY_R10_BALL_HOST_FINALIZATION_ONLY", "authority": "COMP-REQ-331", "host_finalization_only": True, "hardware_contact": 0, "execute_authorized": False, "authorization_created": False, "protected": {"lut_sha256": LUT_SHA256, "tail_hex": "221741A83258", "restore_application_sha256": "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C"}, "finalization_contract": {"trailing_partial": "ignore at most one final unterminated fragment only when input lacks CR/LF; record bytes", "complete_malformed": "reject", "post_stop_exception_status": "NO_GO_FINALIZATION", "candidate_elf_hex_lut_unchanged": True}, "evidence": {"pixel_oracle": {"path": str(ORACLE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(ORACLE)}, "static": {"path": str(STATIC.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(STATIC)}, "log_parser": {"path": str(PARSER.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(PARSER)}, "parser_tool": {"path": str(PARSER_TOOL.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(PARSER_TOOL)}, "lifecycle_static": {"path": str(LIFECYCLE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(LIFECYCLE)}, "checkonly": checkonly()}, "artifacts": {**{name: sha(path) for name, path in TOOLS.items()}, "parser_sha256": sha(PARSER_TOOL), "elf": sha(BUILD / "Companion_Nucleo_WB55RG_Ssd1681R10Ball.elf"), "hex": sha(BUILD / "Companion_Nucleo_WB55RG_Ssd1681R10Ball.hex")}, "future_execute_command": None}
def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--write", action="store_true"); ap.add_argument("--artifact", type=Path, default=OUT); args = ap.parse_args()
    try: report = build()
    except (OSError, RuntimeError, ValueError) as error: print(f"FAIL: R10 MACHINE_READY: {error}"); return 1
    rendered = (json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    if args.write: args.artifact.write_bytes(rendered)
    elif not args.artifact.exists() or args.artifact.read_bytes() != rendered: print("FAIL: stale R10 MACHINE_READY artifact"); return 1
    print(f"PASS: R10 MACHINE_READY hardware_contact=0 writes=0 popup=0 retry=0 artifact_sha256={sha(args.artifact)}"); return 0
if __name__ == "__main__": raise SystemExit(main())
