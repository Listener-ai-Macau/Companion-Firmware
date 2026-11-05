"""Bind the current COMP-REQ-776 machine gate to the owner's panel verdict."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / ".cache/validation/comp776-component-clip-fix-20260812"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    machine_path = PACKAGE / "MACHINE_READY.json"
    identity_path = PACKAGE / "CURRENT_IDENTITY_CHAIN.json"
    motion_path = PACKAGE / "MOTION_COMPONENT_INTEGRITY.json"
    selection_path = PACKAGE / "owner-selection.json"
    owner_path = PACKAGE / "owner-result.txt"
    machine = load(machine_path)
    identity = load(identity_path)
    motion = load(motion_path)
    selection = load(selection_path)
    serial_path = Path(selection["serial_summary"])
    raw_path = Path(selection["serial_log"])
    serial = load(serial_path)
    raw = raw_path.read_text(encoding="utf-8", errors="replace")
    product = machine["identity"]

    checks = {
        "machine_gate_is_current_and_complete": (
            machine.get("status") == "MACHINE_READY"
            and not machine.get("failed_checks")
            and all(machine.get("checks", {}).values())
        ),
        "current_identity_chain_is_complete": (
            identity.get("status") == "MACHINE_READY"
            and not identity.get("failed_checks")
            and all(identity.get("checks", {}).values())
        ),
        "all_motion_components_and_mutants_pass": (
            motion.get("status") == "MACHINE_READY"
            and motion.get("coverage", {}).get("states") == 1587
            and motion.get("coverage", {}).get("failure_count") == 0
            and all(motion.get("checks", {}).values())
            and all(motion.get("mutation_tests", {}).values())
        ),
        "owner_selected_pass_and_result_is_materialized": (
            selection.get("selected") == "通过"
            and owner_path.read_text(encoding="utf-8-sig").strip() == "selection=通过"
            and selection.get("owner_result_sha256") == sha256(owner_path)
        ),
        "serial_prompt_is_bound_and_clean": (
            selection.get("serial_summary_sha256") == sha256(serial_path)
            and serial.get("status") == "PASS"
            and serial.get("prompt_selection") == "通过"
            and serial.get("prompt_result_path") == str(owner_path)
            and serial.get("bytes_read", 0) > 0
            and serial.get("errors") == []
        ),
        "owner_selection_matches_current_product_identity": (
            selection.get("generation") == product.get("generation") == 20
            and selection.get("resource_id") == product.get("resource_id")
            and selection.get("page_sha256") == product.get("page_sha256")
            and selection.get("app_hex_sha256") == product.get("app_hex_sha256")
            and selection.get("app_bin_sha256") == product.get("app_bin_sha256")
        ),
        "captured_runtime_remained_watchdog_healthy": (
            "[watchdog] healthy=1 stalled_mask=0x00" in raw
            and "errors=0 recoveries=0 failure_streak=0" in raw
        ),
    }
    ready = all(checks.values())
    report = {
        "schema": "companion.comp_req_776.final_acceptance.v1",
        "status": "PASS" if ready else "NO_GO",
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "identity": product,
        "owner_selection": selection.get("selected"),
        "serial_bytes": serial.get("bytes_read"),
        "evidence": {
            "machine": {"path": str(machine_path.relative_to(ROOT)), "sha256": sha256(machine_path)},
            "identity": {"path": str(identity_path.relative_to(ROOT)), "sha256": sha256(identity_path)},
            "motion": {"path": str(motion_path.relative_to(ROOT)), "sha256": sha256(motion_path)},
            "owner_result": {"path": str(owner_path.relative_to(ROOT)), "sha256": sha256(owner_path)},
            "owner_selection": {"path": str(selection_path.relative_to(ROOT)), "sha256": sha256(selection_path)},
            "serial_summary": {"path": str(serial_path.relative_to(ROOT)), "sha256": sha256(serial_path)},
            "serial_log": {"path": str(raw_path.relative_to(ROOT)), "sha256": sha256(raw_path)},
        },
        "hardware_contact": 1,
    }
    output = PACKAGE / "FINAL_ACCEPTANCE.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
