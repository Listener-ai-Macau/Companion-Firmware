#!/usr/bin/env python3
"""Fresh, source-bound, production-off BLE/device-control host closure."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".cache/validation/comp-req-562-ble-device-control"
RUNNER = ROOT / "tools/run_comp_req_562_ble_device_control.ps1"
HOST = ROOT / "tools/comp_req_562_ble_device_control_host.c"
APP = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
NAME = ROOT / "app/companion_pendant/platform/companion_ble_name.c"
ENTRY = ROOT / "app/companion_pendant/platform/companion_ble_name_entry.c"
GLUE = ROOT / "app/companion_pendant/platform/companion_product_entry_glue.c"
ADAPTER = ROOT / "app/companion_pendant/platform/companion_platform_adapters.c"
REPAIR = ROOT / "app/companion_pendant/platform/companion_ble_repair.c"
REPAIR_HEADER = ROOT / "app/companion_pendant/platform/companion_ble_repair.h"
GATT_HEADER = ROOT / "app/companion_pendant/gatt/companion_gatt_stm32wb.h"
GATT_SOURCE = ROOT / "app/companion_pendant/gatt/companion_gatt_stm32wb.c"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def source_contract(text: str) -> bool:
    required = (
        "companion_ble_name_product_entry(",
        "companion_platform_device_control_settings_event(",
        "companion_platform_device_control_invoke_event(",
        "companion_ble_repair_product_entry(",
        "REPAIR_COMMAND",
        "repair_product_entry",
        "repair_duplicate_replay",
        "repair_invalid_window",
        "same_operation_different_key",
        'device_settings_duplicate");',
        "device.writes == writes, \"malformed_no_transport\"",
        "device.invokes == failed_invokes",
        "failed_duplicate_replay",
        "deadline_fail_closed",
        "COMPANION_BLE_NAME_REPLAY_CAPACITY",
        "repair_calls=",
        "hardware=0 ble_write=0 bond_erase=0 radio=0",
    )
    return all(item in text for item in required)


def mutation_negative(text: str, needle: str, replacement: str) -> bool:
    mutated = text.replace(needle, replacement, 1)
    return mutated != text and not source_contract(mutated)


def run_mutation(name: str, source: Path, needle: str, replacement: str,
                 oracle: str) -> dict[str, object]:
    mutation_root = OUT / "mutations" / name
    mutation_root.mkdir(parents=True, exist_ok=True)
    mutated_source = mutation_root / source.name
    original = source.read_text(encoding="utf-8")
    mutated = original.replace(needle, replacement, 1)
    if mutated == original:
        return {"status": "NO_GO_MUTATION_NOT_APPLIED", "oracle": oracle}
    mutated_source.write_text(mutated, encoding="utf-8")
    command = ["pwsh", "-NoProfile", "-File", str(RUNNER),
               "-OutputDirectory", str(mutation_root / "run"),
               "-MutationLabel", name]
    override = {NAME: "-NameSource", REPAIR: "-RepairSource", GATT_SOURCE: "-GattSource"}
    command.extend([override.get(source, "-HostSource"), str(mutated_source)])
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    nested_path = mutation_root / "run" / "result.json"
    nested: dict[str, object] = {}
    if nested_path.exists():
        nested = json.loads(nested_path.read_text(encoding="utf-8-sig"))
    stderr = str(nested.get("stderr", ""))
    return {
        "source_path": str(mutated_source.relative_to(ROOT)),
        "source_sha256": sha(mutated_source),
        "executable_sha256": nested.get("executable_sha256"),
        "compile_log_sha256": nested.get("compile_log_sha256"),
        "runner_exit_code": proc.returncode,
        "compile_exit": nested.get("compile_exit"),
        "run_exit": nested.get("run_exit"),
        "oracle": oracle,
        "oracle_triggered": oracle in stderr,
        "status": "PASS_NEGATIVE" if proc.returncode != 0 and oracle in stderr else "NO_GO",
        "stderr_sha256": nested.get("stderr_sha256"),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    result: dict[str, object] = {
        "schema": "companion.comp_req_562.ble_device_control.v1",
        "source_commit": git("rev-parse", "HEAD"),
        "platform_pin": git("ls-tree", "HEAD", "third_party/denzic-platform").split()[2],
        "physical_gates": {
            "hardware": 0, "ble_write": 0, "advertising_restart": 0,
            "bond_erase": 0, "radio_commands": 0, "serial": 0,
            "ota_transfer": 0, "ota_apply": 0, "push": 0,
        },
        "source_sha256": {
            str(p.relative_to(ROOT)): sha(p)
            for p in (HOST, APP, NAME, ENTRY, GLUE, ADAPTER, REPAIR, REPAIR_HEADER, GATT_HEADER)
        },
        "production_route": {
            "gate_default_zero": "#define COMPANION_BLE_NAME_PLATFORM_GATE 0" in APP.read_text(),
            "gatt_name_product_entry": "companion_ble_name_product_entry(" in APP.read_text(),
            "legacy_name_route_preserved": "companion_v1_apply_ble_name_config" in APP.read_text(),
            "settings_product_entry": "companion_product_entry_settings(" in APP.read_text(),
            "meeting_product_entry": "companion_product_entry_meeting(" in APP.read_text(),
            "repair_gate_default_zero": "#define COMPANION_BLE_REPAIR_PLATFORM_GATE 0" in APP.read_text(),
            "repair_gatt_case": "case COMPANION_GATT_CHAR_REPAIR_CONTROL:" in APP.read_text(),
            "repair_product_entry": "companion_ble_repair_product_entry(" in APP.read_text(),
            "pinned_device_control_events": all(x in APP.read_text() for x in (
                "companion_platform_device_control_settings_event(",
                "companion_platform_device_control_invoke_event(")),
        },
        "source_mutation_negatives": {},
        "side_effects": {"hardware": 0, "ble_write": 0, "bond_erase": 0,
                          "radio": 0, "popup": 0},
    }
    host_text = HOST.read_text(encoding="utf-8")
    if not source_contract(host_text):
        result["status"] = "NO_GO_SOURCE_CONTRACT"
        (OUT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 2
    command = ["pwsh", "-NoProfile", "-File", str(RUNNER)]
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    result["runner_command"] = "pwsh -NoProfile -File tools/run_comp_req_562_ble_device_control.ps1"
    result["runner_exit"] = proc.returncode
    result["runner_stdout_sha256"] = hashlib.sha256(proc.stdout.encode()).hexdigest().upper()
    result["runner_stderr_sha256"] = hashlib.sha256(proc.stderr.encode()).hexdigest().upper()
    nested = OUT / "result.json"
    nested_data: dict[str, object] = {}
    if nested.exists():
        nested_data = json.loads(nested.read_text(encoding="utf-8-sig"))
    result["runner_result"] = nested_data
    result["source_mutation_negatives"] = {
        "dedupe_bypass": run_mutation(
            "dedupe_bypass", NAME, "if (found) {", "if (false) {",
            "FAIL duplicate_replay"),
        "duplicate_transport_invocation": run_mutation(
            "duplicate_transport_invocation", REPAIR, "if (found) {", "if (false) {",
            "FAIL repair_duplicate_replay"),
        "fail_open_invalid_input": run_mutation(
            "fail_open_invalid_input",
            GATT_SOURCE,
            "out->pairing_window_ms > 120000u", "false",
            "FAIL repair_invalid_window"),
    }
    stdout = str(nested_data.get("stdout", ""))
    result["observed"] = {
        "runner_status": nested_data.get("status"),
        "compile_exit": nested_data.get("compile_exit"),
        "run_exit": nested_data.get("run_exit"),
        "pass_marker": "COMP_REQ_562_BLE PASS" in stdout,
        "exact_once_name_target": "name_target_calls=3" in stdout,
        "fixed_capacity": "replay_capacity=8 trace_capacity=32" in stdout,
        "all_zero_effects": all(str(nested_data.get(k, 0)) in ("0", "0.0")
                                  for k in ("hardware_contact", "ble_write", "bond_erase", "radio_commands")),
    }
    result["artifact_sha256"] = {
        str(p.relative_to(ROOT)): sha(p)
        for p in (RUNNER, HOST, APP, NAME, ENTRY, GLUE, ADAPTER)
        if p.exists()
    }
    ok = (
        proc.returncode == 0 and nested_data.get("status") == "PASS" and
        result["observed"]["pass_marker"] and
        result["observed"]["exact_once_name_target"] and
        result["observed"]["fixed_capacity"] and
        result["observed"]["all_zero_effects"] and
        all(result["source_mutation_negatives"].values()) and
        result["production_route"]["gate_default_zero"] and
        result["production_route"]["legacy_name_route_preserved"] and
        result["production_route"]["settings_product_entry"] and
        result["production_route"]["meeting_product_entry"] and
        result["production_route"]["repair_gate_default_zero"] and
        result["production_route"]["repair_gatt_case"] and
        result["production_route"]["repair_product_entry"] and
        all(item.get("status") == "PASS_NEGATIVE" and item.get("oracle_triggered")
            for item in result["source_mutation_negatives"].values()) and
        result["platform_pin"] == "d311af3db60e118a6d2c6e68873b2d00f2647a96"
    )
    result["status"] = "PASS" if ok else "NO_GO"
    artifact = OUT / "comp-req-562-ble-device-control.json"
    artifact.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "artifact": str(artifact),
                      "artifact_sha256": sha(artifact)}, sort_keys=True))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
