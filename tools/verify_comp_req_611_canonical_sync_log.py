#!/usr/bin/env python3
"""Parse and verify one bounded COMP-REQ-611 serial observation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / ".cache/validation/comp-req-608-logical-choreography/canonical-frame-plan.json"
PAYLOAD = ROOT / ".cache/validation/comp-req-608-logical-choreography/wb55-frame-plan.bin"
PAGE_SHA = "3B9C4B2D0D16964DBD64A68B804AA6AB3404237539F44C21F3FEFD0B32A1AA22"
PAYLOAD_SHA = "5411FB50BC61BF3DC73EB7D0746C6C0E4DB56F7D552B6796BB3B7F6ED59AD5AD"
FRAME_RE = re.compile(
    r"^\[comp-req-611\] frame=(?P<frame>\d+) id=(?P<id>\S+) "
    r"sha256=(?P<sha>[0-9A-Fa-f]{64}) order=(?P<order>\d+) "
    r"dwell_commits=(?P<dwell>\d+) dwell_ms=(?P<dwell_ms>\d+) "
    r"window=(?P<x_start>\d+)-(?P<x_end>\d+),(?P<y_start>\d+)-(?P<y_end>\d+) "
    r"changed=(?P<changed>[01]) bytes=(?P<bytes>\d+) "
    r"transaction_ms=(?P<transaction>\d+) busy_ms=(?P<busy>\d+) "
    r"control=(?P<control>0x[0-9A-Fa-f]{2}) activation=(?P<activation>\d+) "
    r"source_reset=(?P<reset>\d+) result=(?P<result>\d+) "
    r"transport=(?P<transport>\S+)$"
)
INIT_RE = re.compile(
    r"^\[comp-req-611\] init=(?P<init>[01]) partial_limit=(?P<limit>\d+) "
    r"bound=(?P<bound>[01]) baseline_full_expected=(?P<baseline>\d+) "
    r"auto_maintenance=(?P<auto>\d+) explicit_cleanup=(?P<cleanup>\d+) "
    r"pixel_format=(?P<format>\S+) frames=(?P<frames>\d+) bytes=(?P<bytes>\d+) "
    r"cadence_ms=(?P<cadence>\d+) page_sha256=(?P<page>[0-9A-Fa-f]{64}) "
    r"payload_sha256=(?P<payload>[0-9A-Fa-f]{64})$"
)
READY_RE = re.compile(
    r"^\[comp-req-611\] observation_ready cycles=(?P<cycles>\d+) "
    r"frames=(?P<frames>\d+) baseline_full=(?P<baseline>\d+) "
    r"normal_partial=(?P<partial>\d+) auto_maintenance=(?P<auto>\d+) "
    r"explicit_cleanup=(?P<cleanup>\d+) ring_capacity=(?P<capacity>\d+) "
    r"ring_count=(?P<count>\d+) continue=1$"
)
CLEANUP_RE = re.compile(
    r"^\[comp-req-611\] cleanup=single_fast_white reason=(?P<reason>\S+) "
    r"result=(?P<result>\d+) window=(?P<x_start>\d+)-(?P<x_end>\d+),"
    r"(?P<y_start>\d+)-(?P<y_end>\d+) bytes=(?P<bytes>\d+) "
    r"transaction_ms=(?P<transaction>\d+) busy_ms=(?P<busy>\d+) "
    r"control=(?P<control>0x[0-9A-Fa-f]{2}) activation=(?P<activation>\d+) "
    r"source_reset=(?P<reset>\d+) explicit_cleanup=(?P<cleanup>\d+)$"
)


class LogError(ValueError):
    pass


def _plan() -> list[dict]:
    data = json.loads(PLAN.read_text(encoding="utf-8"))
    return data["entries"]


def _parse_u32(fields: dict[str, str], key: str) -> int:
    try:
        return int(fields[key], 10)
    except (KeyError, ValueError) as exc:
        raise LogError(f"invalid {key}") from exc


def parse_text(text: str, *, require_cleanup: bool = False,
              hardware_contact: int = 1) -> dict:
    plan = _plan()
    init = None
    frames: list[dict] = []
    ready = None
    cleanups: list[dict] = []
    faults: list[str] = []
    for raw in text.replace("\r\n", "\n").splitlines():
        line = raw.strip()
        if not line:
            continue
        match = INIT_RE.match(line)
        if match:
            if init is not None:
                raise LogError("duplicate init record")
            init = {key: value for key, value in match.groupdict().items()}
            continue
        match = FRAME_RE.match(line)
        if match:
            fields = match.groupdict()
            index = _parse_u32(fields, "frame")
            if index >= len(plan):
                raise LogError(f"frame index out of range: {index}")
            if _parse_u32(fields, "order") != index:
                raise LogError(f"frame order mismatch at {index}")
            if _parse_u32(fields, "result") != 0:
                raise LogError(f"frame {index} returned result != 0")
            if _parse_u32(fields, "dwell_ms") != _parse_u32(fields, "dwell") * 480:
                raise LogError(f"frame {index} dwell is not commits * 480ms")
            if _parse_u32(fields, "bytes") > 5000:
                raise LogError(f"frame {index} transferred too many bytes")
            if _parse_u32(fields, "changed") != (0 if index == 0 else 1):
                raise LogError(f"frame {index} changed flag mismatch")
            if _parse_u32(fields, "transaction") > 480 or _parse_u32(fields, "busy") > 600:
                raise LogError(f"frame {index} transport timing exceeds bound")
            expected_control = "0xff" if index == 0 else "0xcf"
            if fields["control"].lower() != expected_control:
                raise LogError(f"frame {index} control mismatch")
            expected_reset = 1 if index == 0 else 0
            if _parse_u32(fields, "activation") != 1 or _parse_u32(fields, "reset") != expected_reset:
                raise LogError(f"frame {index} activation/reset mismatch")
            expected = plan[index]
            if fields["id"] != expected["id"]:
                raise LogError(f"frame {index} id mismatch")
            if fields["sha"].upper() != expected["framebuffer_sha256"].upper():
                raise LogError(f"frame {index} framebuffer hash mismatch")
            expected_transport = "baseline_full_0xff" if index == 0 else "cached_mode2_0xcf_dynamic_diff"
            if fields["transport"] != expected_transport:
                raise LogError(f"frame {index} transport mismatch")
            frames.append({
                "frame": index,
                "id": fields["id"],
                "sha256": fields["sha"].upper(),
                "dwell_commits": _parse_u32(fields, "dwell"),
                "dwell_ms": _parse_u32(fields, "dwell_ms"),
                "next_due_delta_ms": _parse_u32(fields, "dwell_ms"),
                "bytes": _parse_u32(fields, "bytes"),
                "window": [int(fields["x_start"]), int(fields["x_end"]), int(fields["y_start"]), int(fields["y_end"])],
                "transaction_ms": _parse_u32(fields, "transaction"),
                "busy_ms": _parse_u32(fields, "busy"),
                "control": fields["control"].upper(),
                "transport": fields["transport"],
            })
            continue
        match = READY_RE.match(line)
        if match:
            if ready is not None:
                raise LogError("duplicate observation_ready record")
            ready = {key: int(value, 10) for key, value in match.groupdict().items()}
            continue
        match = CLEANUP_RE.match(line)
        if match:
            fields = match.groupdict()
            cleanups.append({key: (value if key in {"reason", "control"} else int(value, 10))
                             for key, value in fields.items()})
            continue
        if line.startswith("[comp-req-611]") and ("fault" in line or "result=" in line):
            faults.append(line)

    if init is None:
        raise LogError("init record is missing")
    if (init["init"] != "1" or init["limit"] != "255" or init["bound"] != "1" or
            init["baseline"] != "1" or init["auto"] != "0" or init["cleanup"] != "1" or
            init["format"] != "row_major_msb_first_1_is_white" or
            int(init["frames"]) != len(plan) or int(init["bytes"]) != 5000 or
            int(init["cadence"]) != 480 or init["page"].upper() != PAGE_SHA or
            init["payload"].upper() != PAYLOAD_SHA):
        raise LogError("init identity or runtime contract mismatch")
    if len(frames) != len(plan):
        raise LogError(f"expected one complete first cycle, observed {len(frames)} frames")
    if [item["frame"] for item in frames] != list(range(len(plan))):
        raise LogError("first-cycle frame order is not contiguous 0..49")
    if ready is None:
        raise LogError("observation_ready record is missing")
    if (ready["cycles"] < 1 or ready["frames"] != 50 or ready["baseline"] != 1 or
            ready["partial"] < 49 or ready["auto"] != 0 or ready["cleanup"] != 0 or
            ready["capacity"] != 64 or not 1 <= ready["count"] <= 64):
        raise LogError("observation_ready contract mismatch")
    if faults:
        raise LogError(f"fault record present: {faults[0]}")
    if require_cleanup:
        if len(cleanups) != 1:
            raise LogError("exactly one cleanup record is required")
        cleanup = cleanups[0]
        if (cleanup["reason"] not in {"operator_stop", "frame_fault"} or
                cleanup["result"] != 0 or cleanup["bytes"] != 5000 or
                cleanup["control"].upper() != "0XFF" or cleanup["activation"] != 1 or
                cleanup["reset"] != 0 or cleanup["cleanup"] != 1):
            raise LogError("cleanup record is not the accepted single-fast-white operation")
    elif len(cleanups) > 1:
        raise LogError("duplicate cleanup record")
    return {
        "schema": "companion.comp_req_611.canonical_sync.log.v1",
        "status": "PASS_COMP_REQ_611_CANONICAL_SYNC_LOG",
        "hardware_contact": hardware_contact,
        "page_sha256": PAGE_SHA,
        "payload_sha256": PAYLOAD_SHA,
        "frame_count": len(frames),
        "frames": frames,
        "observation_ready": ready,
        "cleanup": cleanups[0] if cleanups else None,
        "cleanup_required": require_cleanup,
        "fixed_telemetry_ring": True,
        "transport": "baseline_full_then_cached_mode2_0xcf_dynamic_diff",
    }


def self_test() -> dict:
    plan = _plan()
    lines = [
        "[comp-req-611] init=1 partial_limit=255 bound=1 baseline_full_expected=1 auto_maintenance=0 explicit_cleanup=1 pixel_format=row_major_msb_first_1_is_white frames=50 bytes=5000 cadence_ms=480 page_sha256=" + PAGE_SHA + " payload_sha256=" + PAYLOAD_SHA
    ]
    for index, entry in enumerate(plan):
        dwell = entry["dwell_commits"]
        transport = "baseline_full_0xff" if index == 0 else "cached_mode2_0xcf_dynamic_diff"
        control = "0xFF" if index == 0 else "0xCF"
        changed = 0 if index == 0 else 1
        reset = 1 if index == 0 else 0
        lines.append(f"[comp-req-611] frame={index} id={entry['id']} sha256={entry['framebuffer_sha256']} order={index} dwell_commits={dwell} dwell_ms={dwell * 480} window=0-24,0-199 changed={changed} bytes=5000 transaction_ms=100 busy_ms=200 control={control} activation=1 source_reset={reset} result=0 transport={transport}")
    lines.append("[comp-req-611] observation_ready cycles=1 frames=50 baseline_full=1 normal_partial=49 auto_maintenance=0 explicit_cleanup=0 ring_capacity=64 ring_count=50 continue=1")
    lines.append("[comp-req-611] cleanup=single_fast_white reason=operator_stop result=0 window=0-24,0-199 bytes=5000 transaction_ms=100 busy_ms=200 control=0xFF activation=1 source_reset=0 explicit_cleanup=1")
    valid = parse_text("\r\n".join(lines), require_cleanup=True, hardware_contact=0)
    negative = lines.copy()
    negative[2] = negative[2].replace("transport=cached_mode2_0xcf_dynamic_diff", "transport=ordinary_0xfc")
    rejected = False
    try:
        parse_text("\n".join(negative), require_cleanup=True, hardware_contact=0)
    except LogError:
        rejected = True
    return {"status": "PASS_SELFTEST", "valid": valid["status"] == "PASS_COMP_REQ_611_CANONICAL_SYNC_LOG", "transport_negative_rejected": rejected}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--require-cleanup", action="store_true")
    parser.add_argument("--hardware-contact", type=int, default=1)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            result = self_test()
        else:
            if args.log is None:
                parser.error("--log is required")
            result = parse_text(args.log.read_text(encoding="utf-8", errors="replace"),
                                require_cleanup=args.require_cleanup,
                                hardware_contact=args.hardware_contact)
        encoded = json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
        if args.out and args.write:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            tmp = Path(str(args.out) + ".tmp")
            tmp.write_text(encoded, encoding="utf-8")
            tmp.replace(args.out)
        print(encoded, end="")
        return 0
    except (OSError, LogError) as exc:
        print(f"COMP-REQ-611 parser reject: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
