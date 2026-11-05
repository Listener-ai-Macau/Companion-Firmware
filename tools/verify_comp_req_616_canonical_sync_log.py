#!/usr/bin/env python3
"""Verify one bounded COMP-REQ-616 182-frame serial observation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / ".cache/validation/comp-req-616-ten-family-choreography"
PLAN = ART / "canonical-frame-plan.json"
PAYLOAD = ART / "wb55-frame-plan.bin"
PAGE_SHA = "ECCC8D27A31209150B9EEBF8AB25CEB08708B32BBA00541E033C8378E5B77E73"
PAYLOAD_SHA = "087654306CFC0ECA07BEE9F270DAF72C0DB269E3CF39C6D4D6098BB96EA137DC"
FRAME_BYTES = 5000
FRAME_COUNT = 182
FRAME_RE = re.compile(
    r"^\[comp-req-616\] frame=(?P<frame>\d+) id=(?P<id>\S+) "
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
    r"^\[comp-req-616\] init=(?P<init>[01]) partial_limit=(?P<limit>\d+) "
    r"bound=(?P<bound>[01]) baseline_full_expected=(?P<baseline>\d+) "
    r"auto_maintenance=(?P<auto>\d+) explicit_cleanup=(?P<cleanup>\d+) "
    r"pixel_format=(?P<format>\S+) frames=(?P<frames>\d+) bytes=(?P<bytes>\d+) "
    r"cadence_ms=(?P<cadence>\d+) page_sha256=(?P<page>[0-9A-Fa-f]{64}) "
    r"payload_sha256=(?P<payload>[0-9A-Fa-f]{64}) packed_bytes=(?P<packed>\d+)$"
)
READY_RE = re.compile(
    r"^\[comp-req-616\] observation_ready cycles=(?P<cycles>\d+) "
    r"frames=(?P<frames>\d+) baseline_full=(?P<baseline>\d+) "
    r"normal_partial=(?P<partial>\d+) auto_maintenance=(?P<auto>\d+) "
    r"explicit_cleanup=(?P<cleanup>\d+) ring_capacity=(?P<capacity>\d+) "
    r"ring_count=(?P<count>\d+) decoded_bytes=(?P<decoded>\d+) continue=1$"
)
CLEANUP_RE = re.compile(
    r"^\[comp-req-616\] cleanup=single_fast_white reason=(?P<reason>\S+) "
    r"result=(?P<result>\d+) window=(?P<x_start>\d+)-(?P<x_end>\d+),"
    r"(?P<y_start>\d+)-(?P<y_end>\d+) bytes=(?P<bytes>\d+) "
    r"transaction_ms=(?P<transaction>\d+) busy_ms=(?P<busy>\d+) "
    r"control=(?P<control>0x[0-9A-Fa-f]{2}) activation=(?P<activation>\d+) "
    r"source_reset=(?P<reset>\d+) explicit_cleanup=(?P<cleanup>\d+)$"
)


class LogError(ValueError):
    pass


def _plan_and_payload() -> tuple[list[dict], bytes]:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))["entries"]
    payload = PAYLOAD.read_bytes()
    if len(plan) != FRAME_COUNT or len(payload) != FRAME_COUNT * FRAME_BYTES:
        raise LogError("immutable 182-frame source is incomplete")
    if hashlib.sha256(payload).hexdigest().upper() != PAYLOAD_SHA:
        raise LogError("immutable payload SHA mismatch")
    return plan, payload


def _int(fields: dict[str, str], key: str) -> int:
    try:
        return int(fields[key], 10)
    except (KeyError, ValueError) as exc:
        raise LogError(f"invalid {key}") from exc


def parse_text(text: str, *, require_cleanup: bool = False,
              hardware_contact: int = 1) -> dict:
    plan, payload = _plan_and_payload()
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
            init = match.groupdict()
            continue
        match = FRAME_RE.match(line)
        if match:
            fields = match.groupdict()
            index = _int(fields, "frame")
            if index >= FRAME_COUNT or _int(fields, "order") != index:
                raise LogError(f"frame order/index mismatch at {index}")
            if _int(fields, "result") != 0:
                raise LogError(f"frame {index} returned result != 0")
            dwell = _int(fields, "dwell")
            if _int(fields, "dwell_ms") != dwell * 480:
                raise LogError(f"frame {index} dwell is not commits * 480ms")
            expected = plan[index]
            current = payload[index * FRAME_BYTES:(index + 1) * FRAME_BYTES]
            previous = bytes(FRAME_BYTES) if index == 0 else payload[(index - 1) * FRAME_BYTES:index * FRAME_BYTES]
            changed = index == 0 or current != previous
            # COMP-REQ-621 deliberately re-whitens the complete local face
            # window even when two adjacent source frames are identical.
            # Recognize that bounded transport shape without weakening the
            # ordinary sparse-diff parser for other logs.
            face_rewhite = (
                index > 0 and
                _int(fields, "x_start") == 4 and
                _int(fields, "x_end") == 21 and
                _int(fields, "y_start") == 26 and
                _int(fields, "y_end") == 179
            )
            effective_changed = changed or face_rewhite
            if _int(fields, "changed") != int(effective_changed):
                raise LogError(f"frame {index} changed flag mismatch")
            if _int(fields, "bytes") > FRAME_BYTES:
                raise LogError(f"frame {index} transfers too many bytes")
            transaction_limit = 480 if index == 0 else 470
            if _int(fields, "transaction") > transaction_limit or _int(fields, "busy") > 600:
                raise LogError(f"frame {index} transport timing exceeds bound")
            expected_control = "0xff" if index == 0 else "0xcf"
            if fields["control"].lower() != expected_control:
                raise LogError(f"frame {index} control mismatch")
            expected_activation = 1 if effective_changed else 0
            expected_reset = 0
            if (_int(fields, "activation") != expected_activation or
                    _int(fields, "reset") != expected_reset):
                raise LogError(f"frame {index} activation/reset mismatch")
            expected_transport = "baseline_full_0xff" if index == 0 else "cached_mode2_0xcf_face_rewhite"
            if fields["transport"] != expected_transport:
                raise LogError(f"frame {index} transport mismatch")
            if fields["id"] != expected["id"] or fields["sha"].upper() != expected["framebuffer_sha256"].upper():
                raise LogError(f"frame {index} identity mismatch")
            frames.append({
                "frame": index, "id": fields["id"], "sha256": fields["sha"].upper(),
                "dwell_commits": dwell, "dwell_ms": _int(fields, "dwell_ms"),
                "changed": effective_changed, "bytes": _int(fields, "bytes"),
                "window": [_int(fields, "x_start"), _int(fields, "x_end"),
                           _int(fields, "y_start"), _int(fields, "y_end")],
                "transaction_ms": _int(fields, "transaction"),
                "busy_ms": _int(fields, "busy"), "control": fields["control"].upper(),
                "activation": _int(fields, "activation"),
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
        if line.startswith("[comp-req-616]") and ("fault" in line or "result=" in line):
            faults.append(line)
    if init is None:
        raise LogError("init record is missing")
    if (init["init"] != "1" or init["limit"] != "255" or init["bound"] != "1" or
            init["baseline"] != "1" or init["auto"] != "0" or init["cleanup"] != "1" or
            init["format"] != "row_major_msb_first_1_is_white" or
            int(init["frames"]) != FRAME_COUNT or int(init["bytes"]) != FRAME_BYTES or
            int(init["cadence"]) != 480 or init["page"].upper() != PAGE_SHA or
            init["payload"].upper() != PAYLOAD_SHA):
        raise LogError("init identity or runtime contract mismatch")
    if len(frames) != FRAME_COUNT or [item["frame"] for item in frames] != list(range(FRAME_COUNT)):
        raise LogError(f"expected one complete ordered cycle, observed {len(frames)} frames")
    if ready is None:
        raise LogError("observation_ready record is missing")
    if (ready["cycles"] < 1 or ready["frames"] != FRAME_COUNT or ready["baseline"] != 1 or
            ready["partial"] < 1 or ready["auto"] != 0 or ready["cleanup"] != 0 or
            ready["capacity"] != 64 or not 1 <= ready["count"] <= 64 or
            ready["decoded"] != FRAME_COUNT * FRAME_BYTES):
        raise LogError("observation_ready contract mismatch")
    if faults:
        raise LogError(f"fault record present: {faults[0]}")
    if require_cleanup:
        if len(cleanups) != 1:
            raise LogError("exactly one cleanup record is required")
        cleanup = cleanups[0]
        if (cleanup["reason"] != "operator_stop" or cleanup["result"] != 0 or
                cleanup["bytes"] != FRAME_BYTES or cleanup["control"].upper() != "0XFF" or
                cleanup["activation"] != 1 or cleanup["reset"] != 0 or cleanup["cleanup"] != 1):
            raise LogError("cleanup record is not the accepted single-fast-white operation")
    elif len(cleanups) > 1:
        raise LogError("duplicate cleanup record")
    return {
        "schema": "companion.comp_req_616.canonical_sync.log.v1",
        "status": "PASS_COMP_REQ_616_CANONICAL_SYNC_LOG",
        "hardware_contact": hardware_contact, "page_sha256": PAGE_SHA,
        "payload_sha256": PAYLOAD_SHA, "frame_count": FRAME_COUNT,
        "frames": frames, "observation_ready": ready,
        "cleanup": cleanups[0] if cleanups else None,
        "cleanup_required": require_cleanup,
        "fixed_telemetry_ring": True,
        "transport": "baseline_full_then_cached_mode2_0xcf_face_rewhite",
    }


def self_test() -> dict:
    plan, payload = _plan_and_payload()
    lines = [
        f"[comp-req-616] init=1 partial_limit=255 bound=1 baseline_full_expected=1 auto_maintenance=0 explicit_cleanup=1 pixel_format=row_major_msb_first_1_is_white frames=182 bytes=5000 cadence_ms=480 page_sha256={PAGE_SHA} payload_sha256={PAYLOAD_SHA} packed_bytes=180654"
    ]
    for index, entry in enumerate(plan):
        previous = bytes(FRAME_BYTES) if index == 0 else payload[(index - 1) * FRAME_BYTES:index * FRAME_BYTES]
        current = payload[index * FRAME_BYTES:(index + 1) * FRAME_BYTES]
        changed = index == 0 or current != previous
        transport = "baseline_full_0xff" if index == 0 else "cached_mode2_0xcf_face_rewhite"
        control = "0xFF" if index == 0 else "0xCF"
        face_rewhite = index > 0
        effective_changed = changed or face_rewhite
        activation = 1 if effective_changed else 0
        reset = 0
        window = "0-24,0-199" if index == 0 else "4-21,26-179"
        transfer_bytes = 5000 if index == 0 else 2772
        lines.append(f"[comp-req-616] frame={index} id={entry['id']} sha256={entry['framebuffer_sha256']} order={index} dwell_commits=1 dwell_ms=480 window={window} changed={int(effective_changed)} bytes={transfer_bytes if effective_changed else 0} transaction_ms={100 if effective_changed else 0} busy_ms={200 if effective_changed else 0} control={control} activation={activation} source_reset={reset} result=0 transport={transport}")
    lines.append("[comp-req-616] observation_ready cycles=1 frames=182 baseline_full=1 normal_partial=181 auto_maintenance=0 explicit_cleanup=0 ring_capacity=64 ring_count=64 decoded_bytes=910000 continue=1")
    lines.append("[comp-req-616] cleanup=single_fast_white reason=operator_stop result=0 window=0-24,0-199 bytes=5000 transaction_ms=100 busy_ms=200 control=0xFF activation=1 source_reset=0 explicit_cleanup=1")
    valid = parse_text("\r\n".join(lines), require_cleanup=True, hardware_contact=0)
    negative = lines.copy()
    negative[2] = negative[2].replace("transport=cached_mode2_0xcf_face_rewhite", "transport=ordinary_0xfc")
    try:
        parse_text("\n".join(negative), require_cleanup=True, hardware_contact=0)
    except LogError:
        rejected = True
    else:
        rejected = False
    return {"status": "PASS_SELFTEST", "valid": valid["status"] == "PASS_COMP_REQ_616_CANONICAL_SYNC_LOG", "transport_negative_rejected": rejected}


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
        result = self_test() if args.self_test else parse_text(
            args.log.read_text(encoding="utf-8", errors="replace"),
            require_cleanup=args.require_cleanup, hardware_contact=args.hardware_contact)
        encoded = json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
        if args.out and args.write:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            Path(str(args.out) + ".tmp").write_text(encoded, encoding="utf-8")
            Path(str(args.out) + ".tmp").replace(args.out)
        print(encoded, end="")
        return 0
    except (OSError, LogError, AttributeError) as exc:
        print(f"COMP-REQ-616 parser reject: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
