#!/usr/bin/env python3
"""Decode Companion diagnostic raw JSONL into named JSON or JSONL."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from dataclasses import dataclass
from typing import Any


DEFAULT_HEADER = pathlib.Path("app/companion_pendant/diag_log/diag_log_events.h")
DEFAULT_FIXTURE_RAW = pathlib.Path(
    "docs/validation/companion-pendant-firmware-bringup-1.4-diag-log-raw.jsonl"
)
DEFAULT_FIXTURE_DECODED = pathlib.Path(
    "docs/validation/companion-pendant-firmware-bringup-1.4-diag-log-decoded.json"
)
SCHEMA_ID = "companion.pendant.diag_log.v1"

SOURCE_RE = re.compile(
    r"X\(\s*([A-Z0-9_]+)\s*,\s*(0x[0-9A-Fa-f]+|\d+)u?\s*,\s*\"([^\"]+)\"\s*\)"
)
EVENT_RE = re.compile(
    r"X\(\s*([A-Z0-9_]+)\s*,\s*([A-Z0-9_]+)\s*,\s*"
    r"(0x[0-9A-Fa-f]+|\d+)u?\s*,\s*(COMP_DIAG_SEV_[A-Z]+)\s*,\s*\"([^\"]+)\"\s*\)"
)
SEVERITY_RE = re.compile(r"^\s*#define\s+(COMP_DIAG_SEV_[A-Z]+)\s+(\d+)u?\b", re.MULTILINE)


@dataclass(frozen=True)
class SourceDef:
    symbol: str
    value: int
    name: str


@dataclass(frozen=True)
class EventDef:
    source_symbol: str
    event_symbol: str
    value: int
    severity_macro: str
    name: str


@dataclass(frozen=True)
class DiagSchema:
    header_path: pathlib.Path
    severities_by_macro: dict[str, int]
    severities_by_value: dict[int, str]
    sources_by_symbol: dict[str, SourceDef]
    sources_by_name: dict[str, SourceDef]
    sources_by_value: dict[int, SourceDef]
    events_by_key: dict[tuple[int, int], EventDef]
    events_by_name: dict[str, EventDef]


def parse_int(token: str) -> int:
    return int(token.rstrip("uU"), 0)


def load_schema(header_path: pathlib.Path = DEFAULT_HEADER) -> DiagSchema:
    text = header_path.read_text(encoding="utf-8")

    severities_by_macro = {
        match.group(1): parse_int(match.group(2))
        for match in SEVERITY_RE.finditer(text)
    }
    severities_by_value = {
        value: macro.removeprefix("COMP_DIAG_SEV_").lower()
        for macro, value in severities_by_macro.items()
    }

    sources: list[SourceDef] = [
        SourceDef(match.group(1), parse_int(match.group(2)), match.group(3))
        for match in SOURCE_RE.finditer(text)
    ]
    events: list[EventDef] = [
        EventDef(match.group(1), match.group(2), parse_int(match.group(3)), match.group(4), match.group(5))
        for match in EVENT_RE.finditer(text)
    ]

    sources_by_symbol = {source.symbol: source for source in sources}
    sources_by_name = {source.name: source for source in sources}
    sources_by_value = {source.value: source for source in sources}

    events_by_key: dict[tuple[int, int], EventDef] = {}
    events_by_name: dict[str, EventDef] = {}
    for event in events:
        source = sources_by_symbol[event.source_symbol]
        events_by_key[(source.value, event.value)] = event
        events_by_name[event.name] = event

    return DiagSchema(
        header_path=header_path,
        severities_by_macro=severities_by_macro,
        severities_by_value=severities_by_value,
        sources_by_symbol=sources_by_symbol,
        sources_by_name=sources_by_name,
        sources_by_value=sources_by_value,
        events_by_key=events_by_key,
        events_by_name=events_by_name,
    )


def normalize_source(raw: Any, schema: DiagSchema) -> SourceDef | None:
    if isinstance(raw, str):
        return schema.sources_by_name.get(raw.lower()) or schema.sources_by_symbol.get(raw.upper())
    if isinstance(raw, int):
        return schema.sources_by_value.get(raw)
    return None


def normalize_severity(raw: Any, schema: DiagSchema) -> tuple[int | None, str]:
    if isinstance(raw, str):
        key = raw.upper()
        if not key.startswith("COMP_DIAG_SEV_"):
            key = f"COMP_DIAG_SEV_{key}"
        value = schema.severities_by_macro.get(key)
        return value, key.removeprefix("COMP_DIAG_SEV_").lower()
    if isinstance(raw, int):
        return raw, schema.severities_by_value.get(raw, f"unknown_{raw}")
    return None, "unknown"


def uint32(value: Any) -> int:
    if isinstance(value, str):
        return parse_int(value) & 0xFFFFFFFF
    if isinstance(value, int):
        return value & 0xFFFFFFFF
    return 0


def u16_high(value: Any) -> int:
    return (uint32(value) >> 16) & 0xFFFF


def u16_low(value: Any) -> int:
    return uint32(value) & 0xFFFF


def decode_event_args(event_name: str | None, args: dict[str, Any]) -> dict[str, Any] | None:
    if event_name == "e_paper.runtime_snapshot":
        return {
            "payload": "screen_runtime_snapshot",
            "expression": {
                "current": u16_high(args["arg0"]),
                "last_signal": u16_low(args["arg0"]),
            },
            "display_queue": {
                "pending_count": u16_high(args["arg1"]),
                "high_water_count": u16_low(args["arg1"]),
                "dropped_count": uint32(args["arg2"]),
            },
            "panel": {
                "deferred_count": u16_high(args["arg3"]),
                "error_count": u16_low(args["arg3"]),
            },
        }
    return None


def decode_raw_event(raw: dict[str, Any], index: int, schema: DiagSchema) -> dict[str, Any]:
    source = normalize_source(raw.get("source"), schema)
    source_value = source.value if source else raw.get("source")
    event_id = raw.get("event_id", raw.get("event"))
    if isinstance(event_id, str):
        event_id = parse_int(event_id)
    event_def = (
        schema.events_by_key.get((source.value, event_id))
        if source is not None and isinstance(event_id, int)
        else None
    )
    sev_value, sev_name = normalize_severity(raw.get("severity"), schema)
    args = {
        "arg0": raw.get("arg0", 0),
        "arg1": raw.get("arg1", 0),
        "arg2": raw.get("arg2", 0),
        "arg3": raw.get("arg3", 0),
    }

    decoded = {
        "index": index,
        "sequence": raw.get("sequence"),
        "t_ms": raw.get("t_ms"),
        "source": {
            "raw": raw.get("source"),
            "id": source_value,
            "name": source.name if source else f"unknown_{source_value}",
            "symbol": source.symbol if source else None,
        },
        "event": {
            "raw": event_id,
            "name": event_def.name if event_def else f"unknown_{event_id}",
            "symbol": event_def.event_symbol if event_def else None,
            "severity_default": (
                event_def.severity_macro.removeprefix("COMP_DIAG_SEV_").lower()
                if event_def
                else None
            ),
        },
        "severity": {"raw": raw.get("severity"), "level": sev_value, "name": sev_name},
        "args": args,
        "raw_event": raw,
    }
    decoded_args = decode_event_args(event_def.name if event_def else None, args)
    if decoded_args is not None:
        decoded["decoded_args"] = decoded_args
    return decoded


def read_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        parsed = json.loads(line)
        if not isinstance(parsed, dict):
            raise ValueError(f"{path}:{line_number}: expected object")
        events.append(parsed)
    return events


def decode_events(raw_events: list[dict[str, Any]], schema: DiagSchema) -> dict[str, Any]:
    events = [decode_raw_event(raw, index, schema) for index, raw in enumerate(raw_events)]
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": 1,
        "source": {
            "header": str(schema.header_path),
            "decoder": "tools/decode_diag_log.py",
        },
        "definitions": {
            "sources": {
                source.name: {"id": source.value, "symbol": source.symbol}
                for source in schema.sources_by_value.values()
            },
            "events": {
                event.name: {
                    "source": schema.sources_by_symbol[event.source_symbol].name,
                    "event_id": event.value,
                    "symbol": event.event_symbol,
                    "default_severity": event.severity_macro.removeprefix("COMP_DIAG_SEV_").lower(),
                }
                for event in schema.events_by_name.values()
            },
        },
        "summary": {
            "event_count": len(events),
            "sources_seen": sorted({event["source"]["name"] for event in events}),
            "warnings_or_errors": [
                event
                for event in events
                if event["severity"]["name"] in ("warn", "error")
            ],
        },
        "events": events,
    }


def write_json(path: pathlib.Path, value: Any, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=None if compact else 2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: pathlib.Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def run_self_test(header: pathlib.Path) -> None:
    raw_events = [
        {
            "sequence": 1,
            "t_ms": 10,
            "source": "boot",
            "event_id": 1,
            "severity": "info",
            "arg0": 1,
            "arg1": 0,
            "arg2": 0,
            "arg3": 0,
        },
        {
            "sequence": 2,
            "t_ms": 20,
            "source": "gatt",
            "event_id": 2,
            "severity": "info",
            "arg0": 16,
            "arg1": 4,
            "arg2": 0,
            "arg3": 0,
        },
        {
            "sequence": 3,
            "t_ms": 30,
            "source": "spi_flash_cache",
            "event_id": 1,
            "severity": "info",
            "arg0": 4096,
            "arg1": 64,
            "arg2": 0,
            "arg3": 0,
        },
        {
            "sequence": 4,
            "t_ms": 40,
            "source": "e_paper",
            "event_id": 3,
            "severity": "warn",
            "arg0": (5 << 16) | 3,
            "arg1": (2 << 16) | 4,
            "arg2": 1,
            "arg3": (7 << 16) | 1,
        },
        {
            "sequence": 5,
            "t_ms": 50,
            "source": "errors",
            "event_id": 1,
            "severity": "error",
            "arg0": 3735928559,
            "arg1": 0,
            "arg2": 0,
            "arg3": 0,
        },
    ]
    schema = load_schema(header)
    decoded = decode_events(raw_events, schema)
    event_names = {event["event"]["name"] for event in decoded["events"]}
    required = {
        "boot.start",
        "gatt.log_export_request",
        "spi_flash_cache.write",
        "e_paper.runtime_snapshot",
        "errors.assert",
    }
    missing = required - event_names
    if missing:
        raise AssertionError(f"self-test decoder missing events: {sorted(missing)}")
    runtime_event = next(
        event for event in decoded["events"] if event["event"]["name"] == "e_paper.runtime_snapshot"
    )
    if runtime_event.get("decoded_args", {}).get("panel", {}).get("error_count") != 1:
        raise AssertionError("self-test decoder did not unpack runtime panel error_count")
    if runtime_event.get("decoded_args", {}).get("display_queue", {}).get("pending_count") != 2:
        raise AssertionError("self-test decoder did not unpack runtime queue pending_count")

    write_jsonl(DEFAULT_FIXTURE_RAW, raw_events)
    write_json(DEFAULT_FIXTURE_DECODED, decoded)
    print(
        "PASS: decoded Companion diag log fixture -> "
        f"{DEFAULT_FIXTURE_DECODED.as_posix()}"
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=pathlib.Path, help="Raw Companion diagnostic JSONL.")
    parser.add_argument("--output", type=pathlib.Path, help="Decoded output path. Defaults to stdout.")
    parser.add_argument("--header", type=pathlib.Path, default=DEFAULT_HEADER)
    parser.add_argument("--jsonl", action="store_true", help="Write decoded events as JSONL instead of a bundle.")
    parser.add_argument("--compact", action="store_true", help="Compact JSON output.")
    parser.add_argument("--self-test", action="store_true", help="Generate and decode a fixture artifact.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.self_test:
        run_self_test(args.header)
        return 0
    if args.input is None:
        raise SystemExit("--input is required unless --self-test is used")

    schema = load_schema(args.header)
    decoded = decode_events(read_jsonl(args.input), schema)
    if args.jsonl:
        rows = decoded["events"]
        text = "\n".join(json.dumps(row, sort_keys=False) for row in rows) + "\n"
    else:
        text = json.dumps(decoded, indent=None if args.compact else 2, sort_keys=False) + "\n"

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
