#!/usr/bin/env python3
"""Joint offline gate for real FT6336 report/gesture processing through R7 BUSY callbacks."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOUCH_RUNNER = ROOT / "tools/run_comp_req_466_r7_touch_integration_fixture.ps1"
TOUCH_RESULT = ROOT / ".cache/validation/comp-req-466-r7-touch-integration/touch-integration-result.json"
TOUCH_MACHINE_READY = ROOT / ".cache/validation/comp-req-466-r7-touch-integration/MACHINE_READY.json"
BRIDGE_MACHINE_READY = ROOT / ".cache/validation/comp-req-466-r7-runtime-machine-ready.json"
COMP460 = ROOT / "docs/validation/companion-ft6336-r460-offline-harness-evidence.json"

EXPECTED_COMP460_SHA = "0A3A78D1B6447E0E15746364A76BEF0741E73C4D731015BDD8545B9E0E9AC272"
EXPECTED_DRIVER_BLOB = "f856d7ce0b8915e5059620c3faa97aa06b06eb4e"
EXPECTED_HEADER_BLOB = "2220da0c1113a5cdad7028aeae578d9fe26e936f"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def blob(path: Path) -> str:
    return subprocess.check_output(["git", "ls-files", "-s", path.as_posix()], cwd=ROOT, text=True).split()[1]


def stable_path(path: Path) -> str:
    try:
        relative = path.resolve().relative_to(ROOT).as_posix()
        parts = relative.split("/")
        for index, part in enumerate(parts):
            if part.startswith("comp-528-evidence-fix-"):
                return "/".join(parts[index + 1:]) or parts[-1]
        return relative
    except ValueError:
        return path.as_posix().replace("\\", "/")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--touch-result", default=os.environ.get("COMP_REQ_466_TOUCH_RESULT"))
    parser.add_argument("--touch-machine-ready", default=os.environ.get("COMP_REQ_466_TOUCH_MACHINE_READY"))
    parser.add_argument("--bridge-evidence", default=os.environ.get("COMP_REQ_466_BRIDGE_EVIDENCE"))
    parser.add_argument("--runner-out-root", default=os.environ.get("COMP_REQ_466_RUNNER_OUT_ROOT"))
    args = parser.parse_args()
    touch_result_path = Path(args.touch_result) if args.touch_result else TOUCH_RESULT
    touch_machine_ready_path = Path(args.touch_machine_ready) if args.touch_machine_ready else TOUCH_MACHINE_READY
    bridge_machine_ready_path = Path(args.bridge_evidence) if args.bridge_evidence else BRIDGE_MACHINE_READY

    runner_command = ["pwsh", "-NoProfile", "-File", str(TOUCH_RUNNER)]
    if args.runner_out_root:
        runner_command.extend(["-OutRoot", args.runner_out_root])
    run = subprocess.run(
        runner_command,
        cwd=touch_result_path.parent, capture_output=True, text=True, timeout=60, check=False,
    )
    result = json.loads(touch_result_path.read_text(encoding="utf-8")) if touch_result_path.is_file() else None
    bridge = json.loads(bridge_machine_ready_path.read_text(encoding="utf-8")) if bridge_machine_ready_path.is_file() else None
    comp460_ok = COMP460.is_file() and sha(COMP460) == EXPECTED_COMP460_SHA
    runner_sha = sha(TOUCH_RUNNER)
    output = result.get("stdout", "") if result else ""
    counters = result.get("checkonly") if result else None
    required_tokens = (
        "touch integration PASS", "scenarios=3", "aggregate_reports=24",
        "expected_inputs=24", "consumed=24", "sequence_bitmap=0x00FFFFFF",
        "phases=before,during,after", "double=1", "hold=1", "menu=1",
        "drag_gaze=1", "implicit_down=1", "first_tap_provisional=1",
        "consumed_until_release=1", "release_cancel=1", "explicit_cancel=1",
        "phantom_hold=0", "phantom_menu=0", "phantom_recording=0",
        "action_once=1", "busy_touch=1",
    )
    input_records = re.findall(
        r"touch_input sequence=(\d+) scenario=([^ ]+) phase=(before|during|after) event=([^ ]+) action=([^\r\n]+)",
        output,
    )
    sequence_ids = [int(record[0]) for record in input_records]
    p95_match = re.search(r"p95_ms=(\d+)", output)
    p95_ok = bool(p95_match and int(p95_match.group(1)) <= 20)
    records_ok = (
        len(input_records) == 24 and sequence_ids == list(range(24)) and
        len(set(sequence_ids)) == 24 and
        {record[1] for record in input_records} == {
            "double_tap_implicit_down", "hold_menu_cancel", "drag_gaze_only"
        } and {record[2] for record in input_records} == {"before", "during", "after"}
    )
    touch_ok = bool(
        run.returncode == 0 and result and result.get("status") == "PASS" and
        result.get("runner_sha256", "").upper() == runner_sha and
        all(token in output for token in required_tokens) and p95_ok and records_ok and
        counters and set(counters) == {"hardware_contact", "programmer", "serial", "write", "reset", "refresh", "popup", "retry"} and
        all(value == 0 for value in counters.values())
    )
    bridge_ok = bool(
        bridge and bridge.get("status") == "PASS" and
        bridge.get("build", {}).get("bounded_and_continuous") is True and
        bridge.get("protected", {}).get("driver_git_blob") == EXPECTED_DRIVER_BLOB and
        bridge.get("protected", {}).get("header_git_blob") == EXPECTED_HEADER_BLOB and
        all(value == 0 for value in bridge.get("checkonly", {}).values())
    )
    report = {
        "requirement_id": "COMP-REQ-466",
        "status": "PASS" if touch_ok and bridge_ok and comp460_ok else "NO_GO",
        "touch_integration": result,
        "touch_runner_sha256": runner_sha,
        "touch_evidence": {
            "records": [
                {"sequence": int(sequence), "scenario": scenario, "phase": phase,
                 "event": event, "action": action}
                for sequence, scenario, phase, event, action in input_records
            ],
            "sequence_ids_exact_once": records_ok,
            "p95_ms": int(p95_match.group(1)) if p95_match else None,
        },
        "comp_req_460": {"path": str(COMP460), "sha256": sha(COMP460) if COMP460.is_file() else None, "bound": comp460_ok},
        "bridge_machine_ready": {"path": stable_path(bridge_machine_ready_path), "sha256": sha(bridge_machine_ready_path) if bridge_machine_ready_path.is_file() else None, "bound": bridge_ok},
        "protected_blobs": {"driver": blob(ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"), "header": blob(ROOT / "app/companion_pendant/epaper/companion_r7_locked_v9_frames.h")},
        "hardware_contact": 0,
        "popup": 0,
    }
    touch_machine_ready_path.parent.mkdir(parents=True, exist_ok=True)
    touch_machine_ready_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
