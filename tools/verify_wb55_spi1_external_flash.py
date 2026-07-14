#!/usr/bin/env python3
"""Verify two reset-bounded WB55 SPI1 external-Flash boot logs."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any


BOOT_IDENTITY = (
    "flash=SPI1-1IO sck=PA1 mosi=PA7 miso=PB4 cs=PA2 hz=2000000 "
    "epaper=SPI2 PA9/PC1/PC2 cs=PA6 hz=2000000"
)

REQUIRED_TOKENS = (
    "[stage] uart ok",
    "[stage] sai1 ok",
    BOOT_IDENTITY,
    "[touch] ft6336 decoder=pass gesture=pass addr=0x38 probe=present",
    "irq=PC6 wired=1",
    "[flash-spi1] source=screen_assets probe=ok raw_jedec=0x0B4018 id_transfer=1",
    "hal=0 hal_error=0x00000000",
    "[screen-assets] external_store=ready kind=spi1_nor base=0x00200000 bytes=2097152",
    "[screen-assets] policy=external_first store=ready prefix=read:43454D50 mount=ok",
    "[screen-assets] pack=emote-matrix-white-200x200-v1 revision=53 clips=33 frames=75",
    "[screen-assets] expression_renderer=external_pack player=ready fallback=none",
    "[rec-flash] ready=1 jedec=0x0B4018",
    "capacity=1920000",
)

REJECTED_TOKENS = (
    "[flash-bb]",
    "raw_jedec=0x000000",
    "raw_jedec=0xFFFFFF",
    "external_store=unavailable",
    "store=fallback_internal",
    "fallback=rescue_ui",
    "[rec-flash] probe=error",
    "flash=QSPI-2IO",
    "kind=qspi_nor",
)


def canonical_bytes(text: str) -> bytes:
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def validate_reset_log(text: str, label: str) -> dict[str, Any]:
    errors: list[str] = []
    for token in REQUIRED_TOKENS:
        if token not in text:
            errors.append(f"{label}: missing {token}")
    for token in REJECTED_TOKENS:
        if token in text:
            errors.append(f"{label}: rejected token present {token}")

    probes = re.findall(
        r"^\[flash-spi1\] source=(\S+) probe=(\S+) raw_jedec=0x([0-9A-Fa-f]{6}) "
        r"id_transfer=(\d+).*?hal=(\d+) hal_error=0x([0-9A-Fa-f]{8})",
        text,
        flags=re.MULTILINE,
    )
    screen_probes = [probe for probe in probes if probe[0] == "screen_assets"]
    if len(screen_probes) != 1:
        errors.append(f"{label}: expected one hardware screen-assets probe, got {len(screen_probes)}")
    recording_probes = [probe for probe in probes if probe[0] == "recording"]
    if len(recording_probes) != 1:
        errors.append(f"{label}: expected one hardware recording probe, got {len(recording_probes)}")
    for probe in screen_probes + recording_probes:
        source, status, jedec, completed, hal_status, hal_error = probe
        if (status, jedec.upper(), completed, hal_status, hal_error.upper()) != (
            "ok",
            "0B4018",
            "1",
            "0",
            "00000000",
        ):
            errors.append(f"{label}: invalid {source} probe tuple {probe}")

    digest = hashlib.sha256(canonical_bytes(text)).hexdigest()
    return {
        "label": label,
        "status": "PASS" if not errors else "FAIL",
        "sha256_lf": digest,
        "bytes": len(canonical_bytes(text)),
        "hardware_probes": len(screen_probes) + len(recording_probes),
        "jedec": "0x0B4018" if not errors else None,
        "errors": errors,
    }


def validate_pair(paths: list[pathlib.Path]) -> dict[str, Any]:
    if len(paths) != 2:
        return {
            "schema_id": "companion.wb55_spi1_external_flash.v1",
            "status": "FAIL",
            "errors": [f"expected exactly two reset logs, got {len(paths)}"],
            "captures": [],
        }

    captures: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, path in enumerate(paths, start=1):
        if not path.exists():
            errors.append(f"reset{index}: missing log {path}")
            continue
        result = validate_reset_log(path.read_text(encoding="utf-8", errors="replace"), f"reset{index}")
        result["path"] = path.as_posix()
        captures.append(result)
        errors.extend(result["errors"])

    hashes = [capture["sha256_lf"] for capture in captures]
    if len(hashes) == 2 and hashes[0] == hashes[1]:
        errors.append("two reset captures are byte-identical; independent reset evidence required")

    return {
        "schema_id": "companion.wb55_spi1_external_flash.v1",
        "status": "PASS" if not errors and len(captures) == 2 else "FAIL",
        "transport": {
            "protocol": "SPI-1-1-1",
            "instance": "SPI1",
            "mode": 0,
            "hz": 2_000_000,
            "sck": "PA1/CN7-32",
            "mosi": "PA7/CN10-15",
            "miso": "PB4/CN10-4",
            "cs": "PA2/CN10-35",
            "epaper_instance": "SPI2",
        },
        "captures": captures,
        "acceptance": {
            "two_independent_resets": len(hashes) == 2 and len(set(hashes)) == 2,
            "hardware_spi_only": not any("[flash-bb]" in path.read_text(encoding="utf-8", errors="replace") for path in paths if path.exists()),
            "jedec": "0x0B4018",
            "external_cemp_mounted": not errors,
            "recording_store_ready": not errors,
            "touch_and_sai_preserved": not errors,
        },
        "errors": errors,
    }


PASS_SAMPLE = """[stage] uart ok
[touch] ft6336 decoder=pass gesture=pass addr=0x38 probe=present probes=1 irq=PC6 wired=1
[stage] sai1 ok
[boot] uart=USART1 PB6/PB7 115200 flash=SPI1-1IO sck=PA1 mosi=PA7 miso=PB4 cs=PA2 hz=2000000 epaper=SPI2 PA9/PC1/PC2 cs=PA6 hz=2000000
[flash-spi1] source=screen_assets probe=ok raw_jedec=0x0B4018 id_transfer=1 transactions=3 bytes=9 hal=0 hal_error=0x00000000 idle_cs=1 idle_sck=0 idle_mosi=1 idle_miso=0 hz=2000000
[screen-assets] external_store=ready kind=spi1_nor base=0x00200000 bytes=2097152
[screen-assets] policy=external_first store=ready prefix=read:43454D50 mount=ok
[screen-assets] pack=emote-matrix-white-200x200-v1 revision=53 clips=33 frames=75 profile=200x200 stride=25 encoding=2
[screen-assets] expression_renderer=external_pack player=ready fallback=none
[flash-spi1] source=recording probe=ok raw_jedec=0x0B4018 id_transfer=1 transactions=3 bytes=9 hal=0 hal_error=0x00000000 idle_cs=1 idle_sck=0 idle_mosi=1 idle_miso=0 hz=2000000
[rec-flash] ready=1 jedec=0x0B4018 base=0x00010000 data=0x00010044 capacity=1920000
"""


def self_test() -> list[str]:
    failures: list[str] = []
    if validate_reset_log(PASS_SAMPLE, "pass")["status"] != "PASS":
        failures.append("valid SPI1 sample rejected")
    for name, mutation in (
        ("invalid_jedec", PASS_SAMPLE.replace("0x0B4018", "0xFFFFFF")),
        ("fallback", PASS_SAMPLE.replace("store=ready", "store=fallback_internal", 1)),
        ("software_probe", PASS_SAMPLE + "[flash-bb] cfg=normal valid=1\n"),
        ("qspi_identity", PASS_SAMPLE.replace("flash=SPI1-1IO", "flash=QSPI-2IO")),
        ("missing_recording", PASS_SAMPLE.replace("[rec-flash] ready=1", "[rec-flash] probe=error")),
    ):
        if validate_reset_log(mutation, name)["status"] != "FAIL":
            failures.append(f"{name} mutation was not rejected")
    return failures


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", action="append", type=pathlib.Path, default=[])
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    failures = self_test() if args.self_test else []
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    if args.self_test:
        print("PASS: WB55 SPI1 external-Flash verifier self-test")
    if not args.log:
        return 0 if args.self_test else 2

    report = validate_pair(args.log)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
