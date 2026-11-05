#!/usr/bin/env python3
"""Read-only fail-closed boot-chain preflight for COMP-REQ-775."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


# Exact, previously installed product Loader identities.  The second identity is
# the COMP-REQ-785 RTC-preserving Loader; accepting it here is required so a UI
# resource-only update does not roll the board back to the pre-RTC Loader.
REGISTERED_LOADER_SHA256 = {
    "7AF74009DCDCC82601DE1F04BEC94248FC5CE48C9B44F6298A44B0763FBD8324": (
        "comp_req_771_formal"
    ),
    "9DB1BBF53DD938F61A74E8FFB61C1506B8315E685A0A84EC4C8856FC5A826E9E": (
        "comp_req_785_rtc_preserving"
    ),
}
APP_BASE = 0x08007000
APP_END = 0x08080000
PREFIX_BYTES = 0x7144
OTA_MAGIC = 0x94448A29


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def parse_ihex(path: Path) -> dict[int, int]:
    memory: dict[int, int] = {}
    upper = 0
    for line in path.read_text(encoding="ascii").splitlines():
        if not line.startswith(":"):
            continue
        record = bytes.fromhex(line[1:])
        count = record[0]
        address = int.from_bytes(record[1:3], "big")
        kind = record[3]
        data = record[4 : 4 + count]
        if kind == 0:
            for offset, value in enumerate(data):
                memory[upper + address + offset] = value
        elif kind == 2:
            upper = int.from_bytes(data, "big") << 4
        elif kind == 4:
            upper = int.from_bytes(data, "big") << 16
    if not memory:
        raise ValueError(f"Intel HEX has no data: {path}")
    return memory


def run_upload(
    programmer: Path,
    serial: str,
    address: int,
    size: int,
    output: Path,
) -> list[str]:
    command = [
        str(programmer),
        "-c",
        "port=SWD",
        f"sn={serial}",
        "mode=UR",
        "reset=HWrst",
        "freq=4000",
        "-u",
        f"0x{address:08X}",
        f"0x{size:X}",
        str(output),
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output.with_suffix(output.suffix + ".log").write_text(
        completed.stdout + completed.stderr,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"read-only CubeProgrammer upload failed: {completed.returncode}"
        )
    return command


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--programmer", type=Path, required=True)
    parser.add_argument("--programmer-serial", required=True)
    parser.add_argument("--loader-hex", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--allow-hardware", action="store_true")
    parser.add_argument("--workflow-lock-held", action="store_true")
    parser.add_argument("--swd-mutex-held", action="store_true")
    args = parser.parse_args()
    if not (
        args.allow_hardware
        and args.workflow_lock_held
        and args.swd_mutex_held
    ):
        raise SystemExit("hardware preflight requires both repository locks")
    loader_sha256 = sha256(args.loader_hex)
    if loader_sha256 not in REGISTERED_LOADER_SHA256:
        raise SystemExit("formal Loader source identity mismatch")

    args.workspace.mkdir(parents=True, exist_ok=True)
    prefix_path = args.workspace / "boot-chain-prefix.bin"
    magic_path = args.workspace / "boot-chain-magic.bin"
    commands = [
        run_upload(
            args.programmer,
            args.programmer_serial,
            0x08000000,
            PREFIX_BYTES,
            prefix_path,
        )
    ]
    prefix = prefix_path.read_bytes()
    loader = parse_ihex(args.loader_hex)
    mismatches = []
    for address, expected in loader.items():
        observed = prefix[address - 0x08000000]
        if observed != expected:
            mismatches.append(
                {
                    "address": f"0x{address:08X}",
                    "expected": expected,
                    "observed": observed,
                }
            )
            if len(mismatches) >= 16:
                break

    app_offset = APP_BASE - 0x08000000
    msp = int.from_bytes(prefix[app_offset : app_offset + 4], "little")
    reset = int.from_bytes(prefix[app_offset + 4 : app_offset + 8], "little")
    magic_pointer = int.from_bytes(
        prefix[app_offset + 0x140 : app_offset + 0x144], "little"
    )
    pointer_in_app = APP_BASE <= magic_pointer <= APP_END - 4
    magic_value = None
    if pointer_in_app:
        commands.append(
            run_upload(
                args.programmer,
                args.programmer_serial,
                magic_pointer,
                4,
                magic_path,
            )
        )
        magic_value = int.from_bytes(magic_path.read_bytes(), "little")

    checks = {
        "formal_loader_defined_bytes_exact": not mismatches,
        "app_msp_in_sram": 0x20000000 <= msp < 0x20040000,
        "app_reset_thumb_in_app": (
            reset & 1 == 1 and APP_BASE <= (reset & ~1) < APP_END
        ),
        "ota_magic_pointer_in_app": pointer_in_app,
        "ota_magic_value_exact": magic_value == OTA_MAGIC,
        "read_only": True,
    }
    evidence = {
        "schema": "companion.comp_req_775.boot_chain_preflight.v1",
        "status": "MACHINE_READY" if all(checks.values()) else "FAILED",
        "checks": checks,
        "loader": {
            "hex_sha256": loader_sha256,
            "registered_identity": REGISTERED_LOADER_SHA256[loader_sha256],
            "defined_bytes": len(loader),
            "first_mismatches": mismatches,
        },
        "app": {
            "base": f"0x{APP_BASE:08X}",
            "msp": f"0x{msp:08X}",
            "reset_handler": f"0x{reset:08X}",
            "magic_pointer": f"0x{magic_pointer:08X}",
            "magic_value": (
                None if magic_value is None else f"0x{magic_value:08X}"
            ),
        },
        "commands": commands,
        "internal_flash_write_bytes": 0,
        "external_flash_write_bytes": 0,
        "hardware_contact": 1,
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(evidence, indent=2, sort_keys=True))
    if evidence["status"] != "MACHINE_READY":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
