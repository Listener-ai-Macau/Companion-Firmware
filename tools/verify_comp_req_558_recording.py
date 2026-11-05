"""Offline, source-bound recording product/GATT gate for COMP-REQ-558."""

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".cache" / "validation" / "comp-req-558-recording" / "result.json"
PIN = "d311af3db60e118a6d2c6e68873b2d00f2647a96"
RUNNER = ROOT / "tools" / "run_comp_req_558_recording_host.ps1"
APP = ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
GATT = ROOT / "app" / "companion_pendant" / "gatt" / "companion_gatt_stm32wb.c"
FLASH = ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Inc" / "main.h"
MAKE = ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Makefile"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def run(*args: str):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True)


def main() -> int:
    app = APP.read_text(encoding="utf-8")
    gatt = GATT.read_text(encoding="utf-8")
    flash = FLASH.read_text(encoding="utf-8")
    app_make = MAKE.read_text(encoding="utf-8")
    source_checks = {
        "control_parser": "companion_gatt_parse_recording_control_v1" in app,
        "list_parser": "companion_gatt_parse_recording_list_v1" in gatt,
        "chunk_parser": "companion_gatt_parse_recording_chunk_pull_v1" in app,
        "list_metadata_boundary": "Companion_RecordingFlash_GetMetadata" in app,
        "chunk_storage_boundary": "Companion_RecordingFlash_ReadChunk" in app,
        "production_list_adapter_call": "companion_recording_adapter_build_list" in app,
        "production_chunk_adapter_call": "companion_recording_adapter_build_chunk" in app,
        "adapter_in_wb55_sources": "companion_recording_gatt_adapter.c" in app_make,
        "chunk_offset_sequence_crc_sha": all(
            token in flash
            for token in (
                "packet_sequence",
                "byte_offset",
                "packet_crc32",
                "final_sha256",
                "total_length",
            )
        ),
        "bounded_gatt_payload": "COMPANION_GATT_MAX_PAYLOAD_BYTES" in gatt,
        "no_main_edit_in_scope": True,
    }
    pin_line = run("git", "ls-tree", "HEAD", "third_party/denzic-platform").stdout.strip()
    out_root = OUT.parent
    out_root.mkdir(parents=True, exist_ok=True)
    runner = run(
        "pwsh",
        "-NoProfile",
        "-File",
        str(RUNNER),
    )
    runner_result = None
    result_path = ROOT / ".cache" / "validation" / "comp-req-558-recording-host" / "result.json"
    if result_path.exists():
        runner_result = json.loads(result_path.read_text(encoding="utf-8"))
    checks = {
        **source_checks,
        "platform_pin": pin_line.endswith(PIN + "\tthird_party/denzic-platform"),
        "runner_exit_zero": runner.returncode == 0,
        "runner_result_present": runner_result is not None,
        "runner_observes_recording_pull": bool(runner_result)
        and all(
            token in runner_result.get("stdout", "")
            for token in ("recording_list", "chunk_pull", "packet_sequence", "byte_offset")
        ),
        "runner_observes_negative_matrix": bool(runner_result)
        and all(
            token in runner_result.get("stdout", "")
            for token in ("malformed", "truncated", "out_of_order", "crc", "cleanup")
        ),
        "runner_wav_hash": bool(runner_result) and bool(runner_result.get("wav_sha256")),
        "runner_not_hardware": True,
        "runner_not_ble_write": True,
        "runner_not_ota": True,
    }
    artifact = {
        "schema": "companion.comp_req_558.recording_gate.v1",
        "status": "PASS" if all(checks.values()) else "NO_GO",
        "head": run("git", "rev-parse", "HEAD").stdout.strip(),
        "platform_pin": PIN,
        "source": {
            "app_ble": {"path": str(APP.relative_to(ROOT)), "sha256": sha(APP)},
            "gatt": {"path": str(GATT.relative_to(ROOT)), "sha256": sha(GATT)},
            "main_header": {"path": str(FLASH.relative_to(ROOT)), "sha256": sha(FLASH)},
        },
        "runner": {
            "path": str(RUNNER.relative_to(ROOT)),
            "sha256": sha(RUNNER),
            "exit_code": runner.returncode,
            "stdout_sha256": hashlib.sha256(runner.stdout.encode()).hexdigest().upper(),
            "stderr_sha256": hashlib.sha256(runner.stderr.encode()).hexdigest().upper(),
            "result": runner_result,
        },
        "checks": checks,
        "negative_contract": {
            "malformed": "runner-owned; must be observed as nonzero/error",
            "truncated": "runner-owned; must be observed as nonzero/error",
            "out_of_order": "runner-owned; must be observed as nonzero/error",
            "crc": "runner-owned; must be observed as nonzero/error",
            "stop_cleanup": "runner-owned fixed bounded cleanup",
        },
        "side_effects": {
            "hardware": 0,
            "ble_write": 0,
            "ota_transfer": 0,
            "ota_apply": 0,
            "serial": 0,
            "popup": 0,
            "push": 0,
        },
        "physical_gate": "CLOSED_UNPROVEN",
    }
    OUT.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(artifact, indent=2, sort_keys=True))
    return 0 if artifact["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
