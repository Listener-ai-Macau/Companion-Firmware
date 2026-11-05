"""Compose the generation-20 component-continuity repair into one machine gate."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / ".cache/validation/comp776-component-clip-fix-20260812"
BUILD = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_freertos"
PAGE = ROOT / ".cache/validation/comp-req-628-status-bar/index.html"
FILES = {
    "continuity": PACKAGE / "COMPONENT_CONTINUITY.json",
    "motion_integrity": PACKAGE / "MOTION_COMPONENT_INTEGRITY.json",
    "completeness": PACKAGE / "EXPRESSION_COMPLETENESS.json",
    "dom": PACKAGE / "DOM_LAYOUT.json",
    "pointer": PACKAGE / "pointer-current/MACHINE_READY.json",
    "generation": PACKAGE / "generation-20-compact/generation-verification.json",
    "sync": PACKAGE / "hardware-noop-final/SYNC_RECEIPT.json",
    "boot": PACKAGE / "hardware-noop-final/ordinary-reset-evidence.json",
    "interaction": BUILD / "generated/companion_browser_interaction_contract.json",
    "risk_gallery": PACKAGE / "expression-risk-and-ten-families.json",
    "motion_gallery": PACKAGE / "bashful-motion-before-after.json",
    "recording_entry_host": PACKAGE / "recording-entry-policy-host/result.json",
    "recording_entry_hardware": PACKAGE / "recording-entry-policy-hardware/MACHINE_READY.json",
}
HOST_COMMANDS = {
    "display_track_arbiter": ["pwsh", "-NoProfile", "-File", "tools/test_display_track_arbiter_host.ps1"],
    "overlay_commit_scheduler": ["pwsh", "-NoProfile", "-File", "tools/test_overlay_commit_scheduler_host.ps1"],
    "screen_composition": ["pwsh", "-NoProfile", "-File", "tools/test_screen_composition_journey_host.ps1"],
    "display_transaction_arbiter": ["pwsh", "-NoProfile", "-File", "tools/test_display_transaction_arbiter_host.ps1"],
    "refresh_coverage": ["pwsh", "-NoProfile", "-File", "tools/test_refresh_coverage_host.ps1"],
    "screen_lifecycle": ["pwsh", "-NoProfile", "-File", "tools/test_screen_lifecycle_journey_host.ps1"],
    "low_power_policy": ["python", "tools/verify_companion_low_power_requirements.py"],
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def intel_hex_range(path: Path) -> tuple[int, int, int]:
    upper = 0
    addresses: list[tuple[int, int]] = []
    for raw in path.read_text(encoding="ascii").splitlines():
        if not raw.startswith(":"):
            continue
        count = int(raw[1:3], 16)
        address = int(raw[3:7], 16)
        kind = int(raw[7:9], 16)
        payload = bytes.fromhex(raw[9:9 + count * 2])
        if kind == 4:
            upper = int.from_bytes(payload, "big") << 16
        elif kind == 0 and count:
            addresses.append((upper + address, count))
    return min(row[0] for row in addresses), max(a + n for a, n in addresses), sum(n for _, n in addresses)


def run_host_contracts() -> tuple[dict, bool]:
    results = {}
    for name, command in HOST_COMMANDS.items():
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                   encoding="utf-8", errors="replace")
        output = (completed.stdout + completed.stderr).strip().splitlines()
        results[name] = {
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "exit_code": completed.returncode,
            "output_tail": output[-8:],
        }
    return results, all(row["status"] == "PASS" for row in results.values())


def main() -> int:
    evidence = {name: load(path) for name, path in FILES.items()}
    continuity = evidence["continuity"]
    motion_integrity = evidence["motion_integrity"]
    completeness = evidence["completeness"]
    dom = evidence["dom"]
    pointer = evidence["pointer"]
    generation = evidence["generation"]
    sync = evidence["sync"]
    boot = evidence["boot"]
    interaction = evidence["interaction"]
    recording_entry_host = evidence["recording_entry_host"]
    recording_entry_hardware = evidence["recording_entry_hardware"]
    resource_id = generation["resource_id"]
    page_sha = sha256(PAGE)
    app_hex = BUILD / "Companion_Nucleo_WB55RG_FreeRTOS.hex"
    app_bin = BUILD / "Companion_Nucleo_WB55RG_FreeRTOS.bin"
    hex_start, hex_end, hex_bytes = intel_hex_range(app_hex)
    host, host_ready = run_host_contracts()
    protected = sync.get("protected_partitions", {})

    checks = {
        "reported_internal_component_truncation_reproduced_and_fixed": (
            continuity.get("status") == "MACHINE_READY"
            and all(continuity.get("checks", {}).values())
            and continuity.get("coverage", {}).get("bashful_states") == 101
        ),
        "all_motion_eye_highlight_and_ornament_components_are_complete": (
            motion_integrity.get("status") == "MACHINE_READY"
            and motion_integrity.get("coverage", {}).get("states") == 1587
            and motion_integrity.get("coverage", {}).get("failure_count") == 0
            and all(motion_integrity.get("checks", {}).values())
            and all(motion_integrity.get("mutation_tests", {}).values())
        ),
        "all_5059_states_and_staging_are_exact": (
            completeness.get("status") == "MACHINE_READY"
            and completeness.get("state_count") == 5059
            and completeness.get("failure_count") == 0
            and all(completeness.get("checks", {}).values())
        ),
        "unrelated_recording_menu_mode_and_low_power_frames_unchanged": (
            continuity.get("checks", {}).get("recording_menu_mode_and_low_power_frames_unchanged") is True
            and continuity.get("coverage", {}).get("unchanged_states") == 4614
        ),
        "browser_dom_and_pointer_contracts_pass": (
            dom.get("status") == "MACHINE_READY"
            and pointer.get("verdict") == "MACHINE_READY"
            and not dom.get("browser_errors") and not pointer.get("browser_errors")
        ),
        "page_generation_and_app_identity_agree": (
            page_sha == generation.get("page_sha256")
            == interaction.get("page_sha256") == interaction.get("resource_page_sha256")
            and resource_id == interaction.get("product_resource_id")
            and bytes.fromhex(resource_id) in app_bin.read_bytes()
        ),
        "generation_20_is_active_after_ordinary_reset": (
            sync.get("active_generation_before") == 20
            and sync.get("active_generation_after") == 20
            and sync.get("target_root", {}).get("generation") == 20
            and sync.get("target_root", {}).get("resource_id") == resource_id
            and sync.get("ordinary_reset_performed") is True
            and sync.get("partition_readback_verified") is True
            and boot.get("status") == "MACHINE_READY"
            and all(boot.get("checks", {}).values())
            and boot.get("initial_generation_refresh", {}).get("generation") == 20
        ),
        "final_identity_probe_writes_nothing": (
            sync.get("external_flash_write_bytes") == 0
            and sync.get("internal_flash_write_bytes") == 0
            and sync.get("recording_partition_write_bytes") == 0
            and sync.get("current_partition_sha256") == sync.get("desired_partition_sha256")
            == sync.get("readback_partition_sha256")
            and all(protected.get(name) == 0 for name in (
                "fus_write_bytes", "loader_internal_flash_write_bytes", "mass_erase_calls",
                "option_byte_write_bytes", "ota_app_internal_flash_write_bytes",
                "other_internal_flash_write_bytes", "otp_write_bytes",
                "recording_partition_write_bytes"))
        ),
        "app_hex_is_ota_app_only": hex_start == 0x08007000 and hex_end <= 0x08080000,
        "recording_and_low_power_host_contracts_pass": host_ready,
        "recording_entry_policy_passes_host_and_physical_board": (
            recording_entry_host.get("status") == "PASS"
            and recording_entry_host.get("exit_code") == 0
            and recording_entry_hardware.get("status") == "MACHINE_READY"
            and all(recording_entry_hardware.get("checks", {}).values())
            and recording_entry_hardware.get("observed", {}).get("center_rejected_rows", 0) > 0
            and recording_entry_hardware.get("observed", {}).get("corner_allowed_rows", 0) > 0
        ),
        "visual_review_galleries_are_current": (
            evidence["risk_gallery"].get("status") == "MACHINE_READY"
            and evidence["risk_gallery"].get("source_state_count") == 5059
            and sha256(ROOT / evidence["risk_gallery"]["png"]) == evidence["risk_gallery"].get("png_sha256")
            and evidence["motion_gallery"].get("status") == "MACHINE_READY"
            and sha256(ROOT / evidence["motion_gallery"]["png"]) == evidence["motion_gallery"].get("png_sha256")
        ),
    }
    ready = all(checks.values())
    report = {
        "schema": "companion.comp_req_776.component_fix_completion.v1",
        "status": "MACHINE_READY" if ready else "NO_GO",
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "identity": {
            "generation": 20,
            "resource_id": resource_id,
            "page_sha256": page_sha,
            "source_manifest_sha256": sha256(PACKAGE / "source-pack-5059/source-pack-manifest.json"),
            "external_partition_sha256": sync.get("readback_partition_sha256"),
            "base_cemp_sha256": sync.get("cemp", {}).get("current", {}).get("sha256"),
            "app_hex_sha256": sha256(app_hex),
            "app_bin_sha256": sha256(app_bin),
            "app_hex_range": [f"0x{hex_start:08X}", f"0x{hex_end:08X}"],
            "app_hex_defined_bytes": hex_bytes,
        },
        "coverage": continuity.get("coverage"),
        "host_contracts": host,
        "evidence": {name: {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(path)}
                     for name, path in FILES.items()},
        "human_boundary": {
            "status": "PENDING",
            "scope": "current physical panel motion, recording independence, and clean low-power appearance",
            "owner_result": "owner-result.txt",
        },
        "hardware_contact": 1,
    }
    output = PACKAGE / "MACHINE_READY.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
