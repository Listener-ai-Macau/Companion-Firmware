#!/usr/bin/env python3
"""Bind the r66 LP delta to current artifacts and the unchanged r65 full chain."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ready(receipt: dict) -> bool:
    checks = receipt.get("checks", {})
    return receipt.get("status") == "MACHINE_READY" and bool(checks) and all(checks.values())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--r65", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()

    package = args.package.resolve()
    r65 = args.r65.resolve()
    repo = args.repo.resolve()
    paths = {
        "bin": package / "Companion_Nucleo_WB55RG_FreeRTOS.bin",
        "hex": package / "Companion_Nucleo_WB55RG_FreeRTOS.hex",
        "lp_static": package / "lp-static.json",
        "lp_runtime": package / "lp-runtime.json",
        "recording_static": package / "recording-independence-static.json",
        "recording_runtime": package / "recording-runtime.json",
        "r65_acceptance": r65 / "MACHINE_ACCEPTANCE.json",
        "r65_recording_static": r65 / "r51-static.json",
        "type": package / "Companion-Type-r13.exe",
    }
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise SystemExit(f"missing required artifacts: {missing}")

    lp_static = load(paths["lp_static"])
    lp_runtime = load(paths["lp_runtime"])
    recording_static = load(paths["recording_static"])
    recording_runtime = load(paths["recording_runtime"])
    r65_acceptance = load(paths["r65_acceptance"])
    r65_static = load(paths["r65_recording_static"])
    app_ble = repo / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
    driver = repo / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
    app_sha = digest(app_ble)
    driver_sha = digest(driver)
    checks = {
        "r66_lp_static_ready": ready(lp_static),
        "r66_lp_runtime_ready": ready(lp_runtime),
        "r66_recording_independence_static_ready": ready(recording_static),
        "current_firmware_recording_runtime_ready": ready(recording_runtime),
        "driver_build_snapshot_consistent": (
            lp_static.get("identity", {}).get("driver_sha256")
            == recording_static.get("source", {}).get("driver_sha256")
        ),
        "app_build_snapshot_consistent": (
            lp_static.get("identity", {}).get("app_ble_sha256")
            == recording_static.get("source", {}).get("app_sha256")
        ),
        "r65_complete_codec3_dual_minutes_chain_passed": (
            str(r65_acceptance.get("result", "")).startswith("PASS_MACHINE_CODEC3")
            and not r65_acceptance.get("failedChecks")
            and r65_acceptance.get("disconnectResume") is True
            and r65_acceptance.get("minutesAccuracy", {}).get("pass") is True
        ),
        "type_identity_unchanged": (
            digest(paths["type"])
            == r65_acceptance.get("type", {}).get("exeSha256")
        ),
        "lp_one_visible_activation": (
            lp_runtime.get("metrics", {}).get("lp_visible_activations") == 1
            and lp_runtime.get("metrics", {}).get("post_freeze_display_commits") == 0
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "schema": "companion.comp775_r68_lp_recording_acceptance.v1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "result": ("PASS_MACHINE_R68_LP_SINGLE_C7_RECORDING_INDEPENDENT_OWNER_OPTICAL_PENDING"
                   if not failed else "NO_GO"),
        "checks": checks,
        "failedChecks": failed,
        "firmware": {
            "bin": str(paths["bin"]),
            "binSha256": digest(paths["bin"]),
            "hexSha256": digest(paths["hex"]),
            "appBleBuildSnapshotSha256": recording_static.get("source", {}).get("app_sha256"),
            "appBleCurrentWorkspaceSha256": app_sha,
            "workspaceDriftAfterFlash": (
                recording_static.get("source", {}).get("app_sha256") != app_sha
            ),
            "driverBuildSnapshotSha256": recording_static.get("source", {}).get("driver_sha256"),
            "driverCurrentWorkspaceSha256": driver_sha,
        },
        "type": {"exe": str(paths["type"]), "exeSha256": digest(paths["type"])},
        "lowPower": lp_runtime,
        "recordingDisplay": recording_runtime,
        "inheritedFullChain": {
            "acceptance": str(paths["r65_acceptance"]),
            "acceptanceSha256": digest(paths["r65_acceptance"]),
            "result": r65_acceptance.get("result"),
            "reason": "Prior durable pull/resume/ASR/dual-minutes evidence; r68 separately re-proves current codec3 recording display runtime",
        },
        "claimBoundary": (
            "Machine PASS proves the flashed r68 one-activation C7 low-power transaction, "
            "30-second post-freeze quiescence/watchdog health, and current codec3 recording display runtime. "
            "Optical background cleanliness plus perceived post-wake face/wave independence remain for the "
            "single blocking Owner review."
        ),
    }
    output = package / "MACHINE_ACCEPTANCE.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
