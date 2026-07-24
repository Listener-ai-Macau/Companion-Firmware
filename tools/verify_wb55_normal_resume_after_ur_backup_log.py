#!/usr/bin/env python3
"""Verify bounded normal-application serial evidence after UR backup reset."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from pathlib import Path

BOOT_IDENTITY = "[boot] Companion NUCLEO-WB55RG bringup"
READY_MARKER = "[boot] boot_selftests=skipped reason=production_ble_path"
CONTROLLER_DIAGNOSTIC_MARKERS = (
    "readonly_state",
    "read_only_controller_state",
    "ssd1681 controller state",
    "controller-state diagnostic",
)
HARDFAULT_PATTERNS = (
    re.compile(r"hard\s*fault", re.IGNORECASE),
    re.compile(r"\bHardFault_Handler\b", re.IGNORECASE),
)
PANEL_ERROR_PATTERNS = (
    re.compile(r"\[panel\][^\r\n]*\berror\b", re.IGNORECASE),
    re.compile(r"\[epaper\][^\r\n]*\berror\b", re.IGNORECASE),
    re.compile(r"\bpanel_error(?:_count)?\s*[=:]\s*[1-9]\d*", re.IGNORECASE),
    re.compile(r"\bpanel\.error_count\s*[=:]\s*[1-9]\d*", re.IGNORECASE),
)


class ResumeError(ValueError):
    pass


def verify_text(text: str) -> dict:
    boot_positions = [match.start() for match in re.finditer(re.escape(BOOT_IDENTITY), text)]
    ready_positions = [match.start() for match in re.finditer(re.escape(READY_MARKER), text)]
    if not boot_positions:
        raise ResumeError("normal boot identity is missing")
    if not ready_positions:
        raise ResumeError("normal ready marker is missing")
    if not any(ready > boot_positions[0] for ready in ready_positions):
        raise ResumeError("normal ready marker does not follow the boot identity")

    lowered = text.lower()
    diagnostic_hits = [marker for marker in CONTROLLER_DIAGNOSTIC_MARKERS if marker in lowered]
    if diagnostic_hits:
        raise ResumeError(f"controller diagnostic marker present: {diagnostic_hits}")
    hardfault_hits = [pattern.pattern for pattern in HARDFAULT_PATTERNS if pattern.search(text)]
    if hardfault_hits:
        raise ResumeError(f"hardfault marker present: {hardfault_hits}")
    panel_error_hits = [pattern.pattern for pattern in PANEL_ERROR_PATTERNS if pattern.search(text)]
    if panel_error_hits:
        raise ResumeError(f"panel error marker present: {panel_error_hits}")

    encoded = text.encode("utf-8")
    return {
        "schema_id": "companion.wb55.normal_resume_after_ur_backup.v1",
        "status": "PASS_APPLICATION_RESUMED_AFTER_BACKUP",
        "bytes_utf8": len(encoded),
        "sha256_utf8": hashlib.sha256(encoded).hexdigest().upper(),
        "normal_boot_identity": BOOT_IDENTITY,
        "normal_boot_count": len(boot_positions),
        "normal_ready_marker": READY_MARKER,
        "normal_ready_count": len(ready_positions),
        "ready_after_boot": True,
        "controller_diagnostic_markers": [],
        "panel_error_markers": [],
        "hardfault_markers": [],
    }


def self_test() -> None:
    valid = f"noise\n{BOOT_IDENTITY}\n[stage] ble app init requested\n{READY_MARKER}\n"
    assert verify_text(valid)["status"] == "PASS_APPLICATION_RESUMED_AFTER_BACKUP"
    cases = {
        "missing_boot": READY_MARKER,
        "missing_ready": BOOT_IDENTITY,
        "ready_before_boot": f"{READY_MARKER}\n{BOOT_IDENTITY}\n",
        "controller_diagnostic": f"{valid}[epaper] readonly_state start\n",
        "panel_error": f"{valid}[panel] status=error\n",
        "panel_error_count": f"{valid}panel.error_count=2\n",
        "hardfault": f"{valid}HardFault_Handler\n",
    }
    for name, text in cases.items():
        try:
            verify_text(text)
        except ResumeError:
            continue
        raise AssertionError(f"negative fixture unexpectedly passed: {name}")

    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "empty.log"
        path.write_text("", encoding="utf-8")
        try:
            verify_text(path.read_text(encoding="utf-8"))
        except ResumeError:
            pass
        else:
            raise AssertionError("empty normal-resume log unexpectedly passed")
    print("PASS: WB55 normal-resume parser positive/negative self-test")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.log is None or args.out is None:
        parser.error("--log and --out are required unless --self-test is used")
    try:
        result = verify_text(args.log.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ResumeError) as exc:
        print(f"NO_GO: {exc}")
        return 1
    result["source_log"] = str(args.log)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
