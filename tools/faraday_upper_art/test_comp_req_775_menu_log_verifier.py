#!/usr/bin/env python3
"""Offline fixtures for the COMP-REQ-775 menu-log verifier."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
ARTIFACTS = REPO / ".cache/validation/comp-req-775-incremental-sync"
VERIFIER = REPO / "tools/faraday_upper_art/verify_comp_req_775_menu_log.py"
OUTPUT = ARTIFACTS / "MENU_LOG_VERIFIER_OFFLINE_READY.json"


def load_verifier():
    spec = importlib.util.spec_from_file_location("menu_log_verifier", VERIFIER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load menu-log verifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    verifier = load_verifier()
    driver = (
        "[epaper] accepted_product_driver changed=1 ready_checks=3 "
        "maintenance=1 transport=software_direct_bsrr_diagnostic "
        "has_busy=1 result=1"
    )
    valid = "\n".join(
        [
            verifier.DAILY,
            verifier.ENTER,
            driver,
            verifier.RIGHT,
            verifier.EXIT,
            driver,
            "",
        ]
    ).encode()
    ready = verifier.verify(valid)
    wrong_order = verifier.verify(
        valid.replace(
            (verifier.RIGHT + "\n" + verifier.EXIT).encode(),
            (verifier.EXIT + "\n" + verifier.RIGHT).encode(),
        )
    )
    fault = verifier.verify(valid + b"[screen] fault terminal_fault=1\n")
    checks = {
        "valid_log_ready": ready["status"] == "MACHINE_READY",
        "valid_log_all_checks": all(ready["checks"].values()),
        "wrong_order_rejected": (
            wrong_order["status"] == "FAILED"
            and not wrong_order["checks"]["ordered_entry_then_exit"]
        ),
        "runtime_fault_rejected": (
            fault["status"] == "FAILED"
            and not fault["checks"]["no_runtime_fault"]
        ),
    }
    receipt = {
        "schema": "companion.comp_req_775.menu_log_test.v1",
        "status": "MACHINE_READY" if all(checks.values()) else "FAILED",
        "checks": checks,
        "valid_evidence": ready,
        "hardware_contact": 0,
    }
    OUTPUT.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    if receipt["status"] != "MACHINE_READY":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
