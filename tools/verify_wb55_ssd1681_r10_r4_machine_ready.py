#!/usr/bin/env python3
"""One-shot, offline R4 closure: targeted host checks and one CheckOnly."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import verify_wb55_ssd1681_r10_ball_log as parser  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def run(command: list[str], expect: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if result.returncode != expect:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(command)}\n{result.stdout}\n{result.stderr}")
    return result


def main() -> int:
    tools = {
        "parser": ROOT / "tools/verify_wb55_ssd1681_r10_ball_log.py",
        "monitor": ROOT / "tools/monitor_wb55_ssd1681_phase_parallel_r10_ball.ps1",
        "launcher": ROOT / "tools/start_wb55_ssd1681_phase_parallel_r10_ball.ps1",
        "runner": ROOT / "tools/run_wb55_ssd1681_phase_parallel_r10_ball.ps1",
        "supervisor": ROOT / "tools/supervise_wb55_ssd1681_phase_parallel_r10_ball_prompt.ps1",
        "static": ROOT / "tools/verify_wb55_ssd1681_r10_r4_corridor_static.py",
    }
    build = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r10_ball"
    elf = build / "Companion_Nucleo_WB55RG_Ssd1681R10Ball.elf"
    hex_image = build / "Companion_Nucleo_WB55RG_Ssd1681R10Ball.hex"
    mr = ROOT / "docs/validation/companion-ssd1681-r10-r4-corridor-machine-ready-20260722.json"
    check_root = ROOT / ".cache/validation/r10-r4-corridor-machine-ready-checkonly-20260722"
    if check_root.exists() or mr.exists():
        raise RuntimeError("R4 final artifact or CheckOnly root already exists; refusing reuse.")

    static = run([sys.executable, str(tools["static"])])
    static_record = json.loads(static.stdout)
    base = parser.r4_positive_log(3)
    parser.parse_log(base, 3)
    loop = parser.parse_loop_log(base, 2)
    parser_cases = {"positive_v3": "PASS"}
    negatives = {
        "wrong_corridor": parser.replace_once("window_x_bytes=4-9", "window_x_bytes=4-8"),
        "wrong_hash": parser.replace_once("current_payload_sha256=", "current_payload_sha256=" + "0" * 64),
        "busy_601": parser.replace_once("busy_elapsed_ms=500", "busy_elapsed_ms=601"),
        "unknown_preamble": lambda text: text.replace(
            "[epaper] phase_parallel_r10_ball schema=v3 observation_ready",
            "[epaper] phase_parallel_r10_ball schema=v3 unknown mode=1\n[epaper] phase_parallel_r10_ball schema=v3 observation_ready",
        ),
    }
    for name, mutation in negatives.items():
        try:
            parser.parse_loop_log(mutation(base), 2)
        except parser.LogFailure:
            parser_cases[name] = "REJECTED"
        else:
            raise RuntimeError(f"R4 parser negative accepted: {name}")

    transitions = [parser.r4_transition(None, 32)] + [parser.r4_transition(a, b) for a, b in ((32, 40), (40, 48), (48, 56), (56, 64))]
    frame_hashes = sorted({x[key] for x in transitions for key in ("previous_frame_sha256", "current_frame_sha256")})
    payload_hashes = sorted({x[key] for x in transitions for key in ("previous_payload_sha256", "current_payload_sha256")})

    expected = {
        "candidate_hex_sha256": sha(hex_image),
        "runner_sha256": sha(tools["runner"]),
        "monitor_sha256": sha(tools["monitor"]),
        "supervisor_sha256": sha(tools["supervisor"]),
        "launcher_sha256": sha(tools["launcher"]),
        "parser_sha256": sha(tools["parser"]),
    }
    machine_manifest = {
        "schema_id": "companion.wb55.ssd1681.r10_r4_corridor.machine_ready.v1",
        "status": "MACHINE_READY_R10_R4_CORRIDOR_OFFLINE_ONLY",
        "hardware_contact": 0,
        "execute_authorized": False,
        "authorization_created": False,
        "artifacts": {"elf": sha(elf), "hex": expected["candidate_hex_sha256"], "runner": expected["runner_sha256"], "monitor": expected["monitor_sha256"], "supervisor": expected["supervisor_sha256"], "launcher": expected["launcher_sha256"], "parser_sha256": expected["parser_sha256"]},
        "protected": {"lut_sha256": parser.oracle.LUT_SHA256, "tail_hex": "221741A83258", "restore_application_sha256": "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C"},
        "r4": {"corridor": "x4-9,y80-91,bytes72", "first_classes": {"ww": 464, "wb": 112, "bw": 0, "bb": 0}, "moving_classes": {"ww": 376, "wb": 88, "bw": 88, "bb": 24}, "frame_hashes": frame_hashes, "payload_hashes": payload_hashes, "r3_hold": "400-410ms after post-sync 0x24"},
        "evidence": {"r3_disposition": sha(ROOT / "docs/validation/companion-ssd1681-r10-r3-runtime-disposition-20260722.json"), "work_package": sha(ROOT / "docs/validation/companion-ssd1681-r10-r4-corridor-work-package-20260722.md"), "targeted_static": static_record, "targeted_parser": {"cases": parser_cases, "loop": loop}},
    }
    mr.write_text(json.dumps(machine_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    disposable = Path(tempfile.mkdtemp(prefix="r10-r4-claimonly-", dir=str(ROOT / ".cache/validation")))
    try:
        source = disposable / "auth.json"
        output_root = disposable / "positive-root"
        def auth(path: Path, root: Path, machine_hash: str) -> None:
            data = {"status": "AUTHORIZED_R10_BALL_ONCE", "consumed": False, "requirement_id": "COMP-REQ-323", "output_root": str(root), "machine_ready_path": str(mr), "machine_ready_sha256": machine_hash, "attempt_limit": 1, "automatic_retries": 0, **expected}
            path.write_text(json.dumps(data) + "\n", encoding="utf-8")
        auth(source, output_root, sha(mr))
        run(["pwsh", "-NoProfile", "-File", str(tools["launcher"]), "-ClaimOnly", "-OutRoot", str(output_root), "-AuthorizationArtifact", str(source)])
        positive = True
        reused = run(["pwsh", "-NoProfile", "-File", str(tools["launcher"]), "-ClaimOnly", "-OutRoot", str(disposable / "reuse-root"), "-AuthorizationArtifact", str(source)], expect=1)
        wrong = disposable / "wrong.json"
        auth(wrong, disposable / "wrong-root", "0" * 64)
        wrong_hash = run(["pwsh", "-NoProfile", "-File", str(tools["launcher"]), "-ClaimOnly", "-OutRoot", str(disposable / "wrong-root"), "-AuthorizationArtifact", str(wrong)], expect=1)

        run(["pwsh", "-NoProfile", "-File", str(tools["launcher"]), "-CheckOnly", "-OutRoot", str(check_root)])
        launch = json.loads((check_root / "persistent-launch.json").read_text(encoding="utf-8"))
        machine_manifest["evidence"]["host_targeted"] = {"claimonly_positive": positive, "wrong_machine_ready_hash_rejected": wrong_hash.returncode == 1, "reused_source_rejected": reused.returncode == 1}
        machine_manifest["evidence"]["checkonly"] = {"status": launch["status"], "hardware_contact": launch["hardware_contact"], "writes": launch["write_counter_sum"], "popup": launch["popup_count"], "retry": launch["retry_count"], "child_exited": launch["child_exited"]}
        if machine_manifest["evidence"]["checkonly"] != {"status": "READY_NO_HARDWARE_CONTACT", "hardware_contact": 0, "writes": 0, "popup": 0, "retry": 0, "child_exited": True}:
            raise RuntimeError("CheckOnly did not prove 0/0/0/0")
        mr.write_text(json.dumps(machine_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    finally:
        shutil.rmtree(disposable, ignore_errors=True)

    print(json.dumps({"status": "MACHINE_READY_R10_R4_CORRIDOR_OFFLINE_ONLY", "mr": str(mr), "mr_sha256": sha(mr), "checkonly": machine_manifest["evidence"]["checkonly"], "targeted_parser_cases": parser_cases, "targeted_host": machine_manifest["evidence"]["host_targeted"], "elf_sha256": sha(elf), "hex_sha256": sha(hex_image), "lut_sha256": parser.oracle.LUT_SHA256, "parser_sha256": expected["parser_sha256"], "monitor_sha256": expected["monitor_sha256"], "launcher_sha256": expected["launcher_sha256"], "runner_sha256": expected["runner_sha256"], "supervisor_sha256": expected["supervisor_sha256"]}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
