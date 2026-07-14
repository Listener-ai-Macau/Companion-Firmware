#!/usr/bin/env python3
"""Validate reset-bounded WB55 external-Flash serial evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any


SCHEMA_ID = "companion.wb55_external_flash_log.v1"
EXPECTED_MAPPING = "flash=QSPI-2IO PA2/PA3/PB9/PB8"
INVALID_JEDEC_IDS = {"000000", "FFFFFF"}
REJECTED_TOKENS = (
    "external_store=unavailable",
    "store=fallback_internal",
    "fallback=rescue_ui",
    "[rec-flash] probe=error",
)


def search(pattern: str, text: str) -> re.Match[str] | None:
    return re.search(pattern, text, flags=re.MULTILINE)


def validate_log(text: str, source: str) -> dict[str, Any]:
    errors: list[str] = []
    rejected = [token for token in REJECTED_TOKENS if token in text]
    if "[stage] qspi ok" not in text:
        errors.append("QUADSPI peripheral initialization token is missing")
    if EXPECTED_MAPPING not in text:
        errors.append(f"expected devboard mapping is missing: {EXPECTED_MAPPING}")
    if rejected:
        errors.append(f"fallback or probe-error token present: {', '.join(rejected)}")

    store = search(
        r"^\[screen-assets\] external_store=ready kind=qspi_nor "
        r"base=(0x[0-9A-Fa-f]+) bytes=(\d+)$",
        text,
    )
    mount = search(
        r"^\[screen-assets\] policy=external_first store=ready "
        r"prefix=read:([0-9A-Fa-f]{8}) mount=ok$",
        text,
    )
    pack = search(
        r"^\[screen-assets\] pack=(\S+) revision=(\d+) clips=(\d+) "
        r"frames=(\d+) profile=(\d+)x(\d+) stride=(\d+) encoding=(\d+)$",
        text,
    )
    renderer_ready = (
        "[screen-assets] expression_renderer=external_pack player=ready fallback=none"
        in text
    )
    recording = search(
        r"^\[rec-flash\] ready=1 jedec=0x([0-9A-Fa-f]{6}) "
        r"base=(0x[0-9A-Fa-f]+) data=(0x[0-9A-Fa-f]+) capacity=(\d+)$",
        text,
    )

    if store is None:
        errors.append("external asset store did not report ready")
    if mount is None:
        errors.append("CEMP resource pack did not mount from external Flash")
    elif mount.group(1).upper() != "43454D50":
        errors.append(f"unexpected external resource prefix: {mount.group(1)}")
    if pack is None:
        errors.append("external expression pack metadata is missing")
    if not renderer_ready:
        errors.append("expression renderer is not using the external pack")
    if recording is None:
        errors.append("external recording store did not report a valid ready line")

    jedec = recording.group(1).upper() if recording else None
    capacity = int(recording.group(4)) if recording else 0
    asset_bytes = int(store.group(2)) if store else 0
    if jedec in INVALID_JEDEC_IDS:
        errors.append(f"invalid JEDEC ID: 0x{jedec}")
    if asset_bytes <= 0:
        errors.append("external asset capacity must be positive")
    if capacity <= 0:
        errors.append("external recording capacity must be positive")

    pack_fields: dict[str, Any] | None = None
    if pack:
        pack_fields = {
            "name": pack.group(1),
            "revision": int(pack.group(2)),
            "clips": int(pack.group(3)),
            "frames": int(pack.group(4)),
            "profile": f"{pack.group(5)}x{pack.group(6)}",
            "stride": int(pack.group(7)),
            "encoding": int(pack.group(8)),
        }

    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS" if not errors else "FAIL",
        "source": source,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "observed": {
            "mapping": EXPECTED_MAPPING if EXPECTED_MAPPING in text else None,
            "asset_base": store.group(1) if store else None,
            "asset_bytes": asset_bytes,
            "cemp_prefix": mount.group(1).upper() if mount else None,
            "pack": pack_fields,
            "jedec": f"0x{jedec}" if jedec else None,
            "recording_base": recording.group(2) if recording else None,
            "recording_data": recording.group(3) if recording else None,
            "recording_capacity": capacity,
        },
        "rejected_tokens": rejected,
        "errors": errors,
    }


PASS_SAMPLE = """[stage] qspi ok
[boot] flash=QSPI-2IO PA2/PA3/PB9/PB8
[screen-assets] external_store=ready kind=qspi_nor base=0x00200000 bytes=2097152
[screen-assets] policy=external_first store=ready prefix=read:43454D50 mount=ok
[screen-assets] pack=emote-matrix-white-200x200-v1 revision=53 clips=33 frames=75 profile=200x200 stride=25 encoding=2
[screen-assets] expression_renderer=external_pack player=ready fallback=none
[rec-flash] ready=1 jedec=0x0B4018 base=0x00010000 data=0x00010044 capacity=1920000
"""


def run_self_test() -> dict[str, Any]:
    cases = {
        "connected_pass": validate_log(PASS_SAMPLE, "self-test-pass")["status"] == "PASS",
        "peripheral_only_rejected": validate_log(
            "[stage] qspi ok\n[boot] flash=QSPI-2IO PA2/PA3/PB9/PB8\n",
            "self-test-peripheral-only",
        )["status"] == "FAIL",
        "invalid_jedec_rejected": validate_log(
            PASS_SAMPLE.replace("0x0B4018", "0xFFFFFF"),
            "self-test-invalid-jedec",
        )["status"] == "FAIL",
        "fallback_rejected": validate_log(
            PASS_SAMPLE + "[screen-assets] store=fallback_internal\n",
            "self-test-fallback",
        )["status"] == "FAIL",
        "zero_capacity_rejected": validate_log(
            PASS_SAMPLE.replace("capacity=1920000", "capacity=0"),
            "self-test-zero-capacity",
        )["status"] == "FAIL",
    }
    return {
        "schema_id": f"{SCHEMA_ID}.self_test",
        "status": "PASS" if all(cases.values()) else "FAIL",
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=pathlib.Path, help="reset-bounded serial log")
    parser.add_argument("--json-out", type=pathlib.Path, help="optional JSON output path")
    parser.add_argument("--self-test", action="store_true", help="run synthetic PASS/FAIL checks")
    args = parser.parse_args()

    if args.self_test:
        result = run_self_test()
    else:
        if args.log is None:
            parser.error("--log is required unless --self-test is used")
        raw = args.log.read_bytes()
        text = raw.decode("utf-8", errors="replace").replace("\r\n", "\n")
        result = validate_log(text, args.log.as_posix())
        result["source_bytes_sha256"] = hashlib.sha256(raw).hexdigest()

    rendered = json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
