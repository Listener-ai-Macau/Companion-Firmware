#!/usr/bin/env python3
"""Seal the offline, no-hardware R10 R3 stable-hold MACHINE_READY evidence."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from verify_wb55_ssd1681_r10_ball_pixel_oracle import LUT_SHA256, parse_c_array


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/validation/companion-ssd1681-r10-r3-execute-ready-machine-ready-20260722.json"
BUILD = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r10_ball"
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
TOOLS = {
    "runner": ROOT / "tools/run_wb55_ssd1681_phase_parallel_r10_ball.ps1",
    "monitor": ROOT / "tools/monitor_wb55_ssd1681_phase_parallel_r10_ball.ps1",
    "supervisor": ROOT / "tools/supervise_wb55_ssd1681_phase_parallel_r10_ball_prompt.ps1",
    "launcher": ROOT / "tools/start_wb55_ssd1681_phase_parallel_r10_ball.ps1",
}
ORACLE = ROOT / "docs/validation/companion-ssd1681-r10-r3-ball-pixel-oracle-20260722.json"
STATIC = ROOT / "docs/validation/companion-ssd1681-r10-r3-ball-static-20260722.json"
PARSER = ROOT / "docs/validation/companion-ssd1681-r10-r3-ball-log-parser-20260722.json"
PARSER_TOOL = ROOT / "tools/verify_wb55_ssd1681_r10_ball_log.py"
LIFECYCLE = ROOT / "docs/validation/companion-ssd1681-r10-r3-ball-lifecycle-static-20260722.json"
CANONICAL = ROOT / "docs/validation/companion-current-goal-audit-20260717.json"
R10_AUDIT = ROOT / "docs/validation/companion-current-goal-audit-r10-20260722.json"
CHECK_ROOT = ROOT / ".cache/validation/r10-r3-stable-hold-machine-ready-checkonly-20260722"
RESTORE_SHA256 = "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C"


class ReadyFailure(RuntimeError):
    pass


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def run(command: list[str], timeout: int = 240) -> None:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                            encoding="utf-8", errors="replace", timeout=timeout)
    if result.returncode:
        raise ReadyFailure(f"command failed: {' '.join(command)}\n{result.stdout}\n{result.stderr}")


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def checkonly() -> dict[str, object]:
    expected_parent = ROOT / ".cache/validation"
    if CHECK_ROOT.parent != expected_parent or CHECK_ROOT.name != "r10-r3-stable-hold-machine-ready-checkonly-20260722":
        raise ReadyFailure("refusing to recreate an unexpected R3 CheckOnly root")
    if CHECK_ROOT.exists():
        shutil.rmtree(CHECK_ROOT)
    launch = CHECK_ROOT / "persistent-launch.json"
    run(["pwsh", "-NoProfile", "-File", str(TOOLS["launcher"]), "-CheckOnly", "-OutRoot", str(CHECK_ROOT)])
    data = json.loads(launch.read_text(encoding="utf-8-sig"))
    stage = json.loads((CHECK_ROOT / "stage-run.json").read_text(encoding="utf-8-sig"))
    children = stage.get("checkonly", {}).get("children", [])
    required = (
        data.get("status") == "READY_NO_HARDWARE_CONTACT" and
        data.get("hardware_contact") == 0 and data.get("write_counter_sum") == 0 and
        data.get("popup_count") == 0 and data.get("retry_count") == 0 and
        data.get("child_exited") is True and
        stage.get("checkonly", {}).get("telemetry_ring_bytes") == 65536 and
        stage.get("checkonly", {}).get("telemetry_ring_fixed") is True and
        all(child.get("child_exited") is True and child.get("exit_code") == 0 for child in children)
    )
    if not required:
        raise ReadyFailure("R3 CheckOnly counters or child-exit evidence failed")
    return {"status": data["status"], "hardware_contact": 0, "writes": 0,
            "popup": 0, "retry": 0, "fixed_ring_bytes": 65536,
            "child_exited": True, "children": children,
            "durable_stdout_stderr": True,
            "evidence_root": str(CHECK_ROOT.relative_to(ROOT)).replace("\\", "/")}


def base_report(checkonly_report: dict[str, object]) -> dict[str, object]:
    hex_path = BUILD / "Companion_Nucleo_WB55RG_Ssd1681R10Ball.hex"
    elf_path = BUILD / "Companion_Nucleo_WB55RG_Ssd1681R10Ball.elf"
    lut = bytes(parse_c_array(DRIVER.read_text(encoding="utf-8"), "ssd1681_phase_parallel_r9_lut"))
    if hashlib.sha256(lut).hexdigest().upper() != LUT_SHA256:
        raise ReadyFailure("R9 LUT hash drift")
    return {
        "schema_id": "companion.wb55.ssd1681.r10_r3_execute_ready.machine_ready.v1",
        "status": "MACHINE_READY_R10_R3_EXECUTE_READY_HOST_BINDING_SUCCESSOR",
        "authority": "COMP-REQ-335",
        "binding_successor": True,
        "supersedes_machine_ready": "docs/validation/companion-ssd1681-r10-r3-stable-hold-machine-ready-20260722.json",
        "hardware_contact": 0,
        "execute_authorized": False,
        "authorization_created": False,
        "r3_variable": {"name": "post_sync_stable_hold", "target_ms": 400,
                        "accepted_range_ms": [400, 410], "hold_count_per_frame": 1,
                        "qualification_and_loop_same": True, "cadence_discriminator_only": True},
        "protected": {"lut_sha256": LUT_SHA256, "tail_hex": "221741A83258",
                       "restore_application_sha256": RESTORE_SHA256,
                       "r2_payload_hashes_preserved": True},
        "evidence": {
            "pixel_oracle": {"path": str(ORACLE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(ORACLE)},
            "static": {"path": str(STATIC.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(STATIC)},
            "log_parser": {"path": str(PARSER.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(PARSER)},
            "parser_tool": {"path": str(PARSER_TOOL.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(PARSER_TOOL)},
            "lifecycle_static": {"path": str(LIFECYCLE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(LIFECYCLE)},
            "checkonly": checkonly_report,
        },
        "artifacts": {**{name: sha(path) for name, path in TOOLS.items()},
                      "parser_sha256": sha(PARSER_TOOL), "elf": sha(elf_path), "hex": sha(hex_path)},
        "canonical_audit_invocation": "python tools/verify_companion_current_goal_audit.py",
        "canonical_audit_required": True,
        "future_execute_command": None,
    }


def build() -> dict[str, object]:
    generator_source = Path(__file__).read_text(encoding="utf-8")
    if "verify_companion_current_goal_audit.py" not in generator_source:
        raise ReadyFailure("R3 generator lacks canonical current-goal audit invocation")
    run(["pwsh", "-NoProfile", "-File", "tools/build_nucleo_bringup.ps1", "-EpaperSsd1681R10BallDiagnostic", "-Force"])
    run([sys.executable, "tools/verify_wb55_ssd1681_r10_ball_pixel_oracle.py", "--write"])
    run([sys.executable, "tools/verify_wb55_ssd1681_r10_ball_static.py", "--write"])
    run([sys.executable, "tools/verify_wb55_ssd1681_r10_ball_log.py", "--write"])
    run([sys.executable, "tools/verify_companion_product_requirements.py"])
    preliminary = base_report(checkonly())
    write_json(OUT, preliminary)
    run([sys.executable, "tools/verify_wb55_ssd1681_r10_ball_lifecycle_static.py", "--write"])
    run([sys.executable, "tools/verify_companion_current_goal_audit.py", "--write"])
    final = base_report(checkonly())
    final["canonical_audit_sha256"] = sha(CANONICAL)
    final["r10_audit_sha256"] = sha(R10_AUDIT)
    return final


def main() -> int:
    try:
        report = build()
        write_json(OUT, report)
        # Re-read after writing so the report's own identity is externally observable.
        print(f"PASS: R10 R3 execute-ready MACHINE_READY hardware_contact=0 writes=0 popup=0 retry=0 artifact_sha256={sha(OUT)}")
        return 0
    except (OSError, ReadyFailure, ValueError, subprocess.SubprocessError) as error:
        print(f"FAIL: R10 R3 MACHINE_READY: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
