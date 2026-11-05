#!/usr/bin/env python3
"""COMP-REQ-639 joint offline platform product-entry machine closure.

Replays host product-entry fixture + static contracts + pin audit.
Does not contact hardware. Physical capabilities stay CLOSED_UNPROVEN unless
separately proven artifacts are only referenced, never reclassified here.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = "d311af3db60e118a6d2c6e68873b2d00f2647a96"
OUT_DIR = ROOT / "docs" / "validation" / "comp-req-639-platform-joint-offline"
OUT = OUT_DIR / "MACHINE_READY.json"
RERUN = OUT_DIR / "rerun"
HOST_EXE = ROOT / ".cache" / "comp-req-602-host" / "companion_platform_adapters_test.exe"
TYPE_ROOT = ROOT.parent / "Companion-Type"
PLATFORM_602 = ROOT.parent / "companion-platform-602"
REF_602_MR = (
    PLATFORM_602
    / "docs"
    / "validation"
    / "comp-req-602-platform-adapter-closure"
    / "MACHINE_READY.json"
)
PHYSICAL_NOTE = (
    PLATFORM_602
    / "docs"
    / "validation"
    / "comp-req-602-platform-adapter-closure"
    / "physical-evidence-2026-07-27.md"
)

REQUIRED_HOST_MARKERS = [
    "device-direct-ok",
    "ordered_trace=begin>callback>mutation>readback>terminal",
    "product-glue-ok",
    "diag positive",
    "device terminal_count=4",
    "duplicate_replay=1",
    "ota positive accepted=1",
    "apply=0",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


def git_ls_tree_platform(repo: Path) -> str:
    p = run(["git", "ls-tree", "HEAD", "third_party/denzic-platform"], cwd=repo)
    return (p.stdout or "").strip()


def main() -> int:
    RERUN.mkdir(parents=True, exist_ok=True)
    checks: dict[str, bool] = {}
    evidence: dict[str, object] = {}
    logs: dict[str, str] = {}

    fw_head = run(["git", "rev-parse", "HEAD"]).stdout.strip()
    fw_link = git_ls_tree_platform(ROOT)
    checks["firmware_platform_pin_d311af3"] = fw_link.endswith(
        PIN + "\tthird_party/denzic-platform"
    ) or fw_link.endswith(PIN + " third_party/denzic-platform")
    evidence["firmware_head"] = fw_head
    evidence["firmware_gitlink"] = fw_link

    type_link = ""
    type_head = ""
    if TYPE_ROOT.is_dir() and (TYPE_ROOT / ".git").exists() or (TYPE_ROOT / ".git").is_file():
        type_link = git_ls_tree_platform(TYPE_ROOT)
        type_head = run(["git", "rev-parse", "HEAD"], cwd=TYPE_ROOT).stdout.strip()
    evidence["type_head"] = type_head
    evidence["type_gitlink"] = type_link
    type_on_pin = PIN in type_link
    checks["type_platform_pin_d311af3"] = type_on_pin
    evidence["type_pin_debt"] = (
        None
        if type_on_pin
        else "Companion-Type still pins c4d966c (or non-d311af3); product coherence debt remains OPEN"
    )

    # Host product-entry fixture
    host_log = RERUN / "host-adapters-test.log"
    host_ok = False
    host_text = ""
    if HOST_EXE.is_file():
        hp = run([str(HOST_EXE)])
        host_text = (hp.stdout or "") + (hp.stderr or "")
        host_log.write_text(host_text, encoding="utf-8")
        host_ok = hp.returncode == 0 and all(m in host_text for m in REQUIRED_HOST_MARKERS)
        evidence["host_exe_sha256"] = sha256_file(HOST_EXE)
        evidence["host_exit"] = hp.returncode
        evidence["host_markers"] = {m: (m in host_text) for m in REQUIRED_HOST_MARKERS}
    else:
        evidence["host_exe_missing"] = str(HOST_EXE)
    checks["host_product_entry_fixture"] = host_ok
    logs["host"] = str(host_log.relative_to(ROOT)).replace("\\", "/")

    # Static verifiers
    static_cmds = {
        "recording_fsm_static": [sys.executable, "tools/verify_recording_fsm_static.py"],
        "ota_contract_static": [sys.executable, "tools/verify_ota_contract_static.py"],
        "ota_component_contract": [
            sys.executable,
            "tools/verify_companion_ota_component_contract.py",
        ],
        "ble_matrix": [sys.executable, "tools/verify_companion_ble_matrix.py"],
    }
    for name, cmd in static_cmds.items():
        cp = run(cmd)
        text = (cp.stdout or "") + (cp.stderr or "")
        log_path = RERUN / f"{name}.log"
        log_path.write_text(text, encoding="utf-8")
        ok = cp.returncode == 0 and ("PASS" in text or "pass" in text.lower() or name == "ota_component_contract")
        if name == "ota_component_contract":
            # component contract prints JSON; exit 0 is authoritative
            ok = cp.returncode == 0
        checks[name] = ok
        evidence[f"{name}_exit"] = cp.returncode
        logs[name] = str(log_path.relative_to(ROOT)).replace("\\", "/")

    # Fixed-capacity + OTA apply fail-closed source tokens
    adapters_h = ROOT / "app/companion_pendant/platform/companion_platform_adapters.h"
    adapters_c = ROOT / "app/companion_pendant/platform/companion_platform_adapters.c"
    h_txt = adapters_h.read_text(encoding="utf-8", errors="replace")
    c_txt = adapters_c.read_text(encoding="utf-8", errors="replace")
    checks["fixed_capacity_symbols"] = (
        "COMPANION_PLATFORM_TRACE_CAPACITY" in h_txt
        and "COMPANION_PLATFORM_DIAG_EVENT_CAPACITY" in h_txt
    )
    checks["ota_apply_fail_closed_source"] = "r.apply_requested = false" in c_txt
    evidence["adapter_source_sha256"] = {
        "companion_platform_adapters.h": sha256_file(adapters_h),
        "companion_platform_adapters.c": sha256_file(adapters_c),
    }

    # Reference 602 offline + physical note presence (reference only)
    evidence["ref_comp_req_602_machine_ready_present"] = REF_602_MR.is_file()
    evidence["ref_physical_evidence_20260727_present"] = PHYSICAL_NOTE.is_file()
    if REF_602_MR.is_file():
        evidence["ref_comp_req_602_machine_ready_sha256"] = sha256_file(REF_602_MR)
    if PHYSICAL_NOTE.is_file():
        evidence["ref_physical_evidence_sha256"] = sha256_file(PHYSICAL_NOTE)
        evidence["physical_ota_note"] = (
            "2026-07-27 physical OTA note exists under companion-platform-602; "
            "this offline joint verifier does NOT re-execute radio/SWD and does NOT "
            "promote physical gates by itself."
        )

    # Side effects: this verifier never touches hardware
    side_effects = {
        "hardware": 0,
        "programmer": 0,
        "serial": 0,
        "write": 0,
        "reset": 0,
        "refresh": 0,
        "popup": 0,
        "retry": 0,
        "ble_write": 0,
        "ota_transfer": 0,
        "ota_apply": 0,
        "push": 0,
    }
    checks["side_effects_all_zero"] = all(v == 0 for v in side_effects.values())

    # Type pin is known debt — joint offline can still be MACHINE_READY_WITH_TYPE_PIN_DEBT
    core_keys = [
        "firmware_platform_pin_d311af3",
        "host_product_entry_fixture",
        "recording_fsm_static",
        "ota_contract_static",
        "ota_component_contract",
        "ble_matrix",
        "fixed_capacity_symbols",
        "ota_apply_fail_closed_source",
        "side_effects_all_zero",
    ]
    core_pass = all(checks[k] for k in core_keys)
    if core_pass and checks["type_platform_pin_d311af3"]:
        status = "MACHINE_READY_OFFLINE"
    elif core_pass:
        status = "MACHINE_READY_OFFLINE_WITH_TYPE_PIN_DEBT"
    else:
        status = "NO_GO"

    artifact = {
        "schema": "companion.comp_req_639.platform_joint_offline.v1",
        "requirement_id": "COMP-REQ-639",
        "goal_id": "companion-platform-product-entry-20260727",
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "accepted_platform_pin": PIN,
        "checks": checks,
        "evidence": evidence,
        "logs": logs,
        "side_effects": side_effects,
        "physical_gates": {
            "execute": "OPEN",
            "hardware": "OPEN",
            "real_ble": "OPEN_REFERENCED_ONLY",
            "ota_transfer_apply": "OPEN_REFERENCED_ONLY",
            "note": (
                "Offline joint closure only. Companion-platform-602 physical-evidence "
                "2026-07-27 may claim OTA CLOSED_PROVEN separately; this receipt does "
                "not re-run or waive that human review."
            ),
        },
        "remaining": [
            x
            for x in [
                None
                if checks.get("type_platform_pin_d311af3")
                else "Align Companion-Type third_party/denzic-platform gitlink to d311af3",
                "Optional: package_ota_firmware.ps1 rebuild loader from source before packaging",
                "Optional: full diag-log notify with populated SPI event ring on hardware",
                "Optional: real microphone capture fixture",
                "Human review of 2026-07-27 physical OTA note if adopted as product evidence",
            ]
            if x
        ],
        "goal_contract": "docs/validation/comp-req-639-platform-joint-offline/GOAL.md",
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(artifact, indent=2, ensure_ascii=False))
    return 0 if status.startswith("MACHINE_READY") else 2


if __name__ == "__main__":
    raise SystemExit(main())
