#!/usr/bin/env python3
"""Fail-closed final machine gate for COMP-REQ-789 emotion autonomy."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


RESOURCE_ID = "B07892037FF33928733ECE88E1080C4D30F4A592F003F46C0F613E29FF85E202"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def all_checks_pass(document: dict) -> bool:
    checks = document.get("checks", {})
    return bool(checks) and all(checks.values())


def run_gate(command: list[str], cwd: Path) -> dict:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "passed": completed.returncode == 0,
        "exit_code": completed.returncode,
        "output_tail": (completed.stdout + completed.stderr)[-2000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", required=True, type=Path)
    parser.add_argument("--app-bin", required=True, type=Path)
    parser.add_argument("--app-hex", required=True, type=Path)
    parser.add_argument("--previous-app-bin", required=True, type=Path)
    parser.add_argument("--layout", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    artifact = args.artifact_dir.resolve()
    repo = Path(__file__).resolve().parents[1]
    component = load(artifact / "component-life-machine.json")
    generation = load(artifact / "generation/generation-verification.json")
    sync = load(artifact / "hardware-sync/SYNC_RECEIPT.json")
    emotion = load(artifact / "hardware-emotion-machine.json")
    layout = load(args.layout)
    idle = (artifact / "machine-idle/nucleo-serial-raw.log").read_text(
        encoding="utf-8", errors="replace"
    )
    recording = (
        artifact / "machine-recording/nucleo-serial-raw.log"
    ).read_text(encoding="utf-8", errors="replace")
    ble = (artifact / "machine-recording/ble-trigger.log").read_text(
        encoding="utf-8", errors="replace"
    )

    old_app = args.previous_app_bin.read_bytes()
    new_app = args.app_bin.read_bytes()
    changed_offsets = [
        index
        for index, (old, new) in enumerate(zip(old_app, new_app))
        if old != new
    ]
    expected_resource_bytes = bytes.fromhex(RESOURCE_ID)
    identity_only_delta = (
        len(old_app) == len(new_app)
        and len(changed_offsets) == 32
        and changed_offsets == list(
            range(changed_offsets[0], changed_offsets[0] + 32)
        )
        and new_app[
            changed_offsets[0] : changed_offsets[0] + 32
        ] == expected_resource_bytes
    ) if changed_offsets else False

    duration_matches = [
        int(value)
        for value in re.findall(r'"dur_ms":\s*(\d+).*?"codec":\s*3', ble)
    ]
    fault_tokens = (
        "HardFault",
        "BUSY timeout",
        "watchdog] healthy=0",
        "stalled_mask=0x01",
        "stalled_mask=0x02",
        "stalled_mask=0x04",
        "stalled_mask=0x08",
        "stalled_mask=0x10",
    )
    host_gates = {
        "display_transaction_arbiter": run_gate(
            ["pwsh", "-NoProfile", "-File", "tools/test_display_transaction_arbiter_host.ps1"],
            repo,
        ),
        "overlay_commit_scheduler": run_gate(
            ["pwsh", "-NoProfile", "-File", "tools/test_overlay_commit_scheduler_host.ps1"],
            repo,
        ),
        "stlink_generation_transaction": run_gate(
            [sys.executable, "tools/faraday_upper_art/test_sync_companion_ui_assets_stlink.py"],
            repo,
        ),
    }

    checks = {
        "final_pbm_component_gate": (
            component.get("status") == "MACHINE_READY"
            and all_checks_pass(component)
        ),
        "all_5059_states_reconstruct_exactly": (
            generation.get("status") == "PASS_UI_ASSET_GENERATION_EQUIVALENT"
            and generation.get("states_checked") == 5059
            and generation.get("strict_1bpp") is True
            and generation.get("resource_id") == RESOURCE_ID
        ),
        "resource_transaction_readback_exact": (
            sync.get("active_generation_before") == 20
            and sync.get("active_generation_after") == 21
            and sync.get("partition_readback_verified") is True
            and sync.get("readback_partition_sha256")
            == sync.get("desired_partition_sha256")
            and sync.get("target_root", {}).get("resource_id") == RESOURCE_ID
        ),
        "resource_sync_preserved_internal_and_recording_flash": (
            sync.get("internal_flash_write_bytes") == 0
            and sync.get("recording_partition_write_bytes") == 0
            and sync.get("protected_partitions", {}).get(
                "ota_app_internal_flash_write_bytes"
            ) == 0
            and sync.get("protected_partitions", {}).get(
                "loader_internal_flash_write_bytes"
            ) == 0
        ),
        "ordinary_boot_activates_generation_21": (
            "ui_generation=active generation=21 resource_id=B0789203 entries=5059"
            in idle
        ),
        "hardware_idle_and_recording_emotion_gate": (
            emotion.get("status") == "MACHINE_READY"
            and all_checks_pass(emotion)
        ),
        "real_codec3_sixty_second_recording": (
            "AUTO_RECORD True" in ble
            and any(duration >= 60000 for duration in duration_matches)
        ),
        "recording_wave_and_face_are_independent": (
            recording.count("carrier=pure_wave face_clock_advanced=0") >= 20
            and "wave_drives_face=0" in recording
            and recording.count("track=wave") >= 40
            and recording.count("track=face") >= 8
        ),
        "no_copaint_or_softadvance_recording_path": (
            "life_wave_copaint" not in recording
            and "SoftAdvance" not in recording
        ),
        "watchdog_busy_and_capture_healthy": (
            "[watchdog] healthy=1 stalled_mask=0x00" in idle
            and "[watchdog] healthy=1 stalled_mask=0x00" in recording
            and "drops=0" in recording
            and not any(token in idle + recording for token in fault_tokens)
        ),
        "ota_app_layout_guard": (
            layout.get("status") == "MACHINE_READY"
            and all_checks_pass(layout)
            and int(layout["maximum_address_exclusive"], 16) <= 0x08080000
        ),
        "app_change_is_exact_32_byte_resource_binding": identity_only_delta,
        "targeted_host_regressions": all(
            gate["passed"] for gate in host_gates.values()
        ),
    }
    result = {
        "schema": "companion.comp_req_789.acceptance.v1",
        "status": "MACHINE_READY_HUMAN_VISUAL_PENDING"
        if all(checks.values())
        else "FAILED",
        "checks": checks,
        "identity": {
            "resource_id": RESOURCE_ID,
            "app_bin_sha256": sha256(args.app_bin),
            "app_hex_sha256": sha256(args.app_hex),
            "previous_app_bin_sha256": sha256(args.previous_app_bin),
            "app_changed_bytes": len(changed_offsets),
            "app_first_changed_offset": changed_offsets[0]
            if changed_offsets
            else None,
        },
        "hardware": {
            "idle_capture_seconds": 95,
            "recording_duration_ms_max": max(duration_matches, default=0),
            "idle_families": emotion.get("counts", {}).get("idle_families", []),
            "recording_wave_events": emotion.get("counts", {}).get(
                "recording_wave_events", 0
            ),
            "recording_face_events": emotion.get("counts", {}).get(
                "recording_face_events", 0
            ),
        },
        "host_gates": host_gates,
        "hardware_contact": 1,
        "owner_gate": (
            "Judge physical independence, cleanliness, emotion correctness, and "
            "whether wave remains perceptually fastest."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "MACHINE_READY_HUMAN_VISUAL_PENDING" else 2


if __name__ == "__main__":
    raise SystemExit(main())
