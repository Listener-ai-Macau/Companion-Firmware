"""Fail-closed parser for compact R10 guarded-corridor cadence telemetry."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

PREFIX = "[epaper] r10_native_guarded_corridor_cached_mode2_cadence "
SCHEMA = "v13"
FRAME_BYTES = 5000
RING_BYTES = 65536
MAX_COMPACT_LINE_BYTES = 400
QUAL = (34, 36, 38, 40, 42, 44, 46, 48, 46, 44, 42, 40, 38, 36, 34, 32)
LOOP = tuple(range(34, 66, 2)) + tuple(range(62, 30, -2))
LOOP_NODES = (32,) + LOOP
CORRIDOR_WINDOW = (3, 11, 80, 103)


def frame(x: int) -> bytes:
    if not 32 <= x <= 64 or x % 2:
        raise ValueError("position outside 32..64 2px path")
    result = bytearray([0xFF]) * FRAME_BYTES
    for row in range(24):
        for col in range(24):
            if (2 * col - 23) ** 2 + (2 * row - 23) ** 2 <= 576:
                px = x + col
                result[(80 + row) * 25 + px // 8] &= ~(0x80 >> (px & 7))
    return bytes(result)


def changed_window(old: bytes, new: bytes) -> tuple[int, int, int, int]:
    changed = [i for i, (a, b) in enumerate(zip(old, new)) if a != b]
    if not changed:
        raise ValueError("empty union")
    return (min(i % 25 for i in changed), max(i % 25 for i in changed),
            min(i // 25 for i in changed), max(i // 25 for i in changed))


def region_payload(data: bytes, window: tuple[int, int, int, int]) -> bytes:
    x0, x1, y0, y1 = window
    return b"".join(data[y * 25 + x0:y * 25 + x1 + 1] for y in range(y0, y1 + 1))


def window_text(value: str) -> tuple[int, int, int, int]:
    match = re.fullmatch(r"(\d+)-(\d+),(\d+)-(\d+)", value or "")
    if not match:
        raise ValueError("invalid union window")
    result = tuple(int(x) for x in match.groups())
    if result[0] > result[1] or result[2] > result[3]:
        raise ValueError("reversed union window")
    return result  # type: ignore[return-value]


def fields(text: str) -> dict[str, str]:
    return {k: v for k, v in re.findall(r"([A-Za-z0-9_]+)=([^\s]+)", text)}


def integer(data: dict[str, str], key: str) -> int:
    try:
        return int(data[key], 0)
    except (KeyError, ValueError) as exc:
        raise ValueError(f"invalid {key}") from exc


def expected(sequence_key: str, sequence: int) -> tuple[int, int]:
    if sequence_key == "qualification_frame":
        if not 1 <= sequence <= 16:
            raise ValueError("qualification frame outside 1..16")
        return (32 if sequence == 1 else QUAL[sequence - 2], QUAL[sequence - 1])
    if sequence_key != "loop_iteration" or sequence < 1:
        raise ValueError("invalid sequence")
    index = (sequence - 1) % 32
    return LOOP_NODES[index], LOOP_NODES[index + 1]


def validate_transition(line: str, sequence_key: str, sequence: int | None = None,
                        previous: int | None = None, current: int | None = None) -> dict[str, str]:
    if not line.startswith(PREFIX):
        raise ValueError("wrong candidate prefix")
    line_limit = MAX_COMPACT_LINE_BYTES
    if len((line + "\r\n").encode("ascii")) > line_limit:
        raise ValueError("telemetry line exceeds its bounded record size")
    pairs = re.findall(r"([A-Za-z0-9_]+)=([^\s]+)", line[len(PREFIX):])
    data = dict(pairs)
    if len(pairs) != len(data):
        raise ValueError("duplicate compact telemetry field")
    allowed = {"schema", "qualification_frame", "loop_iteration", "prev", "cur", "window", "payload_sha256", "reset_elapsed_ms", "transaction_elapsed_ms", "busy_elapsed_ms", "start_delta_ms", "act", "source_resets", "ready_checks", "source_ff", "source_cf", "custom_lut_loads", "forbidden", "landing"}
    if set(data) - allowed:
        raise ValueError("unknown compact telemetry field")
    if data.get("schema") != SCHEMA:
        raise ValueError("wrong schema")
    other = "loop_iteration" if sequence_key == "qualification_frame" else "qualification_frame"
    if sequence_key not in data or other in data:
        raise ValueError("missing or mixed sequence key")
    seq = integer(data, sequence_key)
    if sequence is not None and seq != sequence:
        raise ValueError("sequence mismatch")
    old, new = integer(data, "prev"), integer(data, "cur")
    want_old, want_new = expected(sequence_key, seq)
    if ((old, new) != (want_old, want_new) or
            previous is not None and old != previous or current is not None and new != current):
        raise ValueError("position mismatch")
    if (integer(data, "act") != 1 or integer(data, "source_resets") != 0 or
            integer(data, "ready_checks") != 1 or integer(data, "source_ff") != 0 or
            integer(data, "source_cf") != 1 or integer(data, "custom_lut_loads") != 0):
        raise ValueError("single source activation contract")
    reset = integer(data, "reset_elapsed_ms")
    transaction = integer(data, "transaction_elapsed_ms")
    busy = integer(data, "busy_elapsed_ms")
    start_delta = integer(data, "start_delta_ms")
    if reset != 0 or transaction < busy or transaction > 455 or busy < 0 or busy > 600:
        raise ValueError("reset, transaction, or BUSY timing")
    if sequence_key == "loop_iteration":
        if seq == 1 and start_delta != 0:
            raise ValueError("loop iteration 1 must use start_delta_ms=0 warmup")
        if seq >= 2 and not 1 <= start_delta <= 490:
            raise ValueError("loop start-to-start cadence outside 1..490ms")
    elif seq == 1 and start_delta != 0:
        raise ValueError("qualification frame 1 must use start_delta_ms=0 warmup")
    elif seq >= 2 and not 1 <= start_delta <= 490:
        raise ValueError("qualification cadence outside 1..490ms")
    if integer(data, "forbidden") != 0 or integer(data, "landing") != 1:
        raise ValueError("forbidden activity or landing contract")
    old_frame, current_frame = frame(old), frame(new)
    union = changed_window(old_frame, current_frame)
    expected_payload = hashlib.sha256(region_payload(current_frame, CORRIDOR_WINDOW)).hexdigest().upper()
    if window_text(data.get("window", "")) != CORRIDOR_WINDOW:
        raise ValueError("guarded corridor window mismatch")
    if data.get("payload_sha256") != expected_payload:
        raise ValueError("current union payload hash mismatch")
    data = dict(data)
    data["computed_previous_frame_sha256"] = hashlib.sha256(old_frame).hexdigest().upper()
    data["computed_current_frame_sha256"] = hashlib.sha256(current_frame).hexdigest().upper()
    return data


def render_line(sequence_key: str, sequence: int, previous: int, current: int,
                busy: int = 447, start_delta: int = 520) -> str:
    old, new = frame(previous), frame(current)
    union = CORRIDOR_WINDOW
    payload = hashlib.sha256(region_payload(new, union)).hexdigest().upper()
    values = {
        "schema": SCHEMA, sequence_key: sequence, "prev": previous, "cur": current,
        "window": f"{union[0]}-{union[1]},{union[2]}-{union[3]}", "payload_sha256": payload,
        "reset_elapsed_ms": 0, "transaction_elapsed_ms": 450, "busy_elapsed_ms": busy,
        "start_delta_ms": start_delta, "act": 1, "source_resets": 0,
        "ready_checks": 1, "source_ff": 0, "source_cf": 1, "custom_lut_loads": 0,
        "forbidden": 0, "landing": 1,
    }
    line = PREFIX + " ".join(f"{k}={v}" for k, v in values.items())
    line_limit = MAX_COMPACT_LINE_BYTES
    if len((line + "\r\n").encode("ascii")) > line_limit:
        raise ValueError("self-test fixture exceeds bounded record size")
    return line


def split_records(raw: str) -> tuple[list[str], bool, int]:
    terminal = raw.endswith(("\n", "\r"))
    lines = raw.splitlines()
    if not terminal and lines:
        tail = lines.pop()
        return lines, True, len(tail.encode("utf-8"))
    return lines, False, 0


def validate_loop_sequence(records: list[dict[str, str]], require_first: bool = True) -> None:
    if not records:
        return
    first = integer(records[0], "loop_iteration")
    if first < 1:
        raise ValueError("loop records must start at iteration 1")
    if require_first and first != 1:
        raise ValueError("qualification loop records must start at iteration 1")
    for expected_iteration, record in enumerate(records, first):
        if integer(record, "loop_iteration") != expected_iteration:
            raise ValueError("non-contiguous loop records")


def cadence_summary(records: list[dict[str, str]], require_first: bool = True,
                    sequence_key: str = "loop_iteration") -> tuple[int, int]:
    if sequence_key == "loop_iteration":
        validate_loop_sequence(records, require_first=require_first)
    else:
        if not records:
            return 0, 0
        first = integer(records[0], sequence_key)
        if require_first and first != 1:
            raise ValueError("qualification records must start at 1")
        for expected_sequence, record in enumerate(records, first):
            if integer(record, sequence_key) != expected_sequence:
                raise ValueError("non-contiguous qualification records")
    deltas = [integer(record, "start_delta_ms") for record in records[1:]]
    return len(deltas), max(deltas) if deltas else 0


def parse_loop(raw: str, minimum: int = 2) -> dict[str, object]:
    lines, ignored, ignored_bytes = split_records(raw)
    records: list[dict[str, str]] = []
    for text in lines:
        line = text.strip()
        if not line:
            continue
        if line.startswith(PREFIX) and "loop_iteration=" in line:
            record = validate_transition(line, "loop_iteration")
            current = integer(record, "loop_iteration")
            records.append(record)
        elif line.startswith(PREFIX) and "qualification_frame=" in line:
            validate_transition(line, "qualification_frame")
        elif line.startswith(PREFIX) and any(token in line for token in ("fault", "qualification_result=no_go")):
            raise ValueError("fault or no_go record")
        elif not line.startswith(PREFIX) and ("loop_iteration=" in line or "qualification_frame=" in line):
            raise ValueError("wrong prefix")
    if len(records) < minimum:
        raise ValueError("insufficient loop records")
    cadence_measurements, max_start_delta_ms = cadence_summary(records, require_first=False)
    if cadence_measurements < 1:
        raise ValueError("at least one real cadence measurement is required")
    return {"status": "PASS_R10_NATIVE_GUARDED_CORRIDOR_CACHED_MODE2_CADENCE_LOG", "schema": SCHEMA,
            "qualification_frames": None, "activation_count": None, "loop_records": len(records),
            "cadence_measurements": cadence_measurements, "max_start_delta_ms": max_start_delta_ms,
            "ring_bytes": RING_BYTES, "ignored_trailing_partial_line": ignored,
            "ignored_trailing_partial_bytes": ignored_bytes, "records": records}


def parse_log(raw: str, minimum: int = 2) -> dict[str, object]:
    lines, ignored, ignored_bytes = split_records(raw)
    qualifications: list[dict[str, str]] = []
    loops: list[dict[str, str]] = []
    result_ok = observation = False
    for text in lines:
        line = text.strip()
        if not line:
            continue
        if line.startswith(PREFIX) and "qualification_frame=" in line:
            qualifications.append(validate_transition(line, "qualification_frame"))
        elif line.startswith(PREFIX) and "loop_iteration=" in line:
            loops.append(validate_transition(line, "loop_iteration"))
        elif line.startswith(PREFIX) and "qualification_result=" in line:
            result_ok = "qualification_result=ok" in line
        elif line.startswith(PREFIX) and "observation_ready" in line:
            observation = True
        elif "qualification_frame=" in line or "loop_iteration=" in line:
            raise ValueError("wrong prefix")
    if [integer(x, "qualification_frame") for x in qualifications] != list(range(1, 17)):
        raise ValueError("qualification must be exactly 1..16")
    qualification_cadence_measurements, qualification_max_start_delta_ms = cadence_summary(qualifications, require_first=True, sequence_key="qualification_frame")
    if qualification_cadence_measurements < 15:
        raise ValueError("qualification requires 15 real cadence measurements")
    if len(loops) < minimum or not result_ok or not observation:
        raise ValueError("qualification result, observation, or minimum loop missing")
    cadence_measurements, loop_max_start_delta_ms = cadence_summary(loops)
    if cadence_measurements < 1:
        raise ValueError("at least one real cadence measurement is required")
    max_start_delta_ms = max(qualification_max_start_delta_ms, loop_max_start_delta_ms)
    return {"status": "PASS_R10_NATIVE_GUARDED_CORRIDOR_CACHED_MODE2_CADENCE_LOG", "schema": SCHEMA,
            "qualification_frames": 16, "activation_count": 16, "qualification_cadence_measurements": qualification_cadence_measurements, "activation_count": 16, "loop_records": len(loops),
            "cadence_measurements": cadence_measurements, "max_start_delta_ms": max_start_delta_ms,
            "ring_bytes": RING_BYTES, "hardware_contact": 1, "qualification_result": "ok",
            "observation_ready": True, "ignored_trailing_partial_line": ignored,
            "ignored_trailing_partial_bytes": ignored_bytes, "qualification_records": qualifications,
            "records": loops}


def expect_rejected(name: str, line: str, sequence: int = 1, previous: int = 32, current: int = 34) -> dict[str, bool]:
    try:
        validate_transition(line, "loop_iteration", sequence, previous, current)
    except ValueError:
        return {"executed": True, "rejected": True}
    raise ValueError(f"negative accepted: {name}")


def self_test() -> dict[str, object]:
    sample = render_line("loop_iteration", 1, 32, 34, start_delta=0)
    if len((sample + "\r\n").encode("ascii")) > MAX_COMPACT_LINE_BYTES:
        raise ValueError("compact fixture exceeds 400 bytes")
    subprocess.run([sys.executable, str(Path(__file__)), "--validate-loop-line", sample,
                    "--sequence-key", "loop_iteration", "--sequence", "1", "--previous", "32", "--current", "34"],
                   check=True, capture_output=True, text=True)
    q16_old, q16_new = expected("qualification_frame", 16)
    q16 = render_line("qualification_frame", 16, q16_old, q16_new, start_delta=480)
    u32_old, u32_new = expected("loop_iteration", 0xFFFFFFFF)
    u32 = render_line("loop_iteration", 0xFFFFFFFF, u32_old, u32_new, start_delta=480)
    if len((q16 + "\r\n").encode("ascii")) > MAX_COMPACT_LINE_BYTES:
        raise ValueError("qualification_frame=16 worst-case fixture exceeds 400 bytes")
    if len((u32 + "\r\n").encode("ascii")) > MAX_COMPACT_LINE_BYTES:
        raise ValueError("loop_iteration=UINT32_MAX worst-case fixture exceeds 400 bytes")
    validate_transition(q16, "qualification_frame", 16, q16_old, q16_new)
    validate_transition(u32, "loop_iteration", 0xFFFFFFFF, u32_old, u32_new)
    q = "".join(render_line("qualification_frame", i, 32 if i == 1 else QUAL[i - 2], x, start_delta=0 if i == 1 else 480) + "\n" for i, x in enumerate(QUAL, 1))
    q += PREFIX + "qualification_result=ok logical_frames=16 activations=16\n"
    q += PREFIX + "observation_ready loop_limit=none next_previous_x=32 telemetry_storage=host_ring_65536\n"
    second = render_line("loop_iteration", 2, 34, 36, start_delta=480)
    parse_log(q + render_line("loop_iteration", 1, 32, 34, start_delta=0) + "\n" + second + "\n", 2)
    try:
        parse_log(q + render_line("loop_iteration", 1, 32, 34, start_delta=0) + "\n", 2)
    except ValueError:
        one_loop_only = {"executed": True, "rejected": True}
    else:
        raise ValueError("one-loop-only qualification fixture accepted")
    negatives = {
        "wrong_prefix": expect_rejected("wrong_prefix", sample.replace(PREFIX, "[epaper] wrong ", 1)),
        "wrong_schema": expect_rejected("wrong_schema", sample.replace("schema=v13", "schema=v10", 1)),
        "wrong_payload": expect_rejected("wrong_payload", sample.replace(fields(sample)["payload_sha256"], "E" * 64, 1)),
        "wrong_window": expect_rejected("wrong_window", sample.replace(fields(sample)["window"], "4-11,80-103", 1)),
        "busy_601": expect_rejected("busy_601", sample.replace("busy_elapsed_ms=447", "busy_elapsed_ms=601", 1)),
        "wrong_source_count": expect_rejected("wrong_source_count", sample.replace("source_resets=0", "source_resets=1", 1)),
        "reset_elapsed_one": expect_rejected("reset_elapsed_one", sample.replace("reset_elapsed_ms=0", "reset_elapsed_ms=1", 1)),
        "ready_checks_zero": expect_rejected("ready_checks_zero", sample.replace("ready_checks=1", "ready_checks=0", 1)),
        "source_ff_one": expect_rejected("source_ff_one", sample.replace("source_ff=0", "source_ff=1", 1)),
        "source_cf_zero": expect_rejected("source_cf_zero", sample.replace("source_cf=1", "source_cf=0", 1)),
        "source_cf_missing": expect_rejected("source_cf_missing", sample.replace(" source_cf=1", "", 1)),
        "source_cf_duplicate": expect_rejected("source_cf_duplicate", sample.replace(" source_cf=1", " source_cf=1 source_cf=1", 1)),
        "reset_one": expect_rejected("reset_one", sample.replace("source_resets=0", "source_resets=1", 1)),
        "ready_zero": expect_rejected("ready_zero", sample.replace("ready_checks=1", "ready_checks=0", 1)),
        "transaction_456": expect_rejected("transaction_456", sample.replace("transaction_elapsed_ms=450", "transaction_elapsed_ms=456", 1)),
        "transaction_elapsed_456": expect_rejected("transaction_elapsed_456", sample.replace("transaction_elapsed_ms=450", "transaction_elapsed_ms=456", 1)),
        "stale_omit_field": expect_rejected("stale_omit_field", sample + " omit=0"),
        "start_delta_zero_after_warmup": expect_rejected("start_delta_zero_after_warmup", second.replace("start_delta_ms=480", "start_delta_ms=0", 1), 2, 34, 36),
        "start_delta_491": expect_rejected("start_delta_491", second.replace("start_delta_ms=480", "start_delta_ms=491", 1), 2, 34, 36),
        "newline_complete_malformed": expect_rejected("newline_complete_malformed", sample + " malformed=1"),
    }
    try:
        parse_loop(sample + "\n" + second + "\n", 2)
    except ValueError as exc:
        raise ValueError(f"valid cadence sequence rejected: {exc}") from exc
    try:
        parse_loop(sample + "\n" + render_line("loop_iteration", 3, 36, 38, start_delta=520) + "\n", 2)
    except ValueError:
        negatives["duplicate_gap"] = {"executed": True, "rejected": True}
    else:
        raise ValueError("duplicate/gap loop fixture accepted")
    tail_first = render_line("loop_iteration", 17, 64, 62, start_delta=480)
    tail_second = render_line("loop_iteration", 18, 62, 60, start_delta=480)
    tail = parse_loop(tail_first + "\n" + tail_second + "\n", 2)
    if tail["loop_records"] != 2 or tail["cadence_measurements"] != 1:
        raise ValueError("positive ring tail did not preserve cadence")
    trailing = parse_loop(sample + "\n" + second + "\npartial", 2)
    if not trailing["ignored_trailing_partial_line"]:
        raise ValueError("trailing partial not recorded")
    return {"schema_id": "companion.wb55.ssd1681.r10_native_guarded_corridor_cached_mode2_cadence.parser.v3",
            "status": "PASS", "schema": SCHEMA, "max_compact_line_bytes": MAX_COMPACT_LINE_BYTES,
            "fixtures": {"validate_loop_line_subprocess": {"executed": True, "accepted": True},
            "compact_line_bytes": {"executed": True, "accepted": True, "max": len((sample + "\r\n").encode("ascii"))},
            "qualification_16": {"executed": True, "accepted": True},
            "qualification_frame_16_worst_case": {"executed": True, "accepted": True, "bytes_with_crlf": len((q16 + "\r\n").encode("ascii"))},
            "loop_uint32_max_worst_case": {"executed": True, "accepted": True, "bytes_with_crlf": len((u32 + "\r\n").encode("ascii"))},
            "one_loop_only_forbidden": one_loop_only,
            "loop_start_to_start": {"executed": True, "accepted": True},
            "trailing_partial": {"executed": True, "accepted": True}, **negatives}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-loop-line")
    parser.add_argument("--sequence-key", choices=("qualification_frame", "loop_iteration"), default="loop_iteration")
    parser.add_argument("--sequence", "--loop-sequence", dest="sequence", type=int)
    parser.add_argument("--previous", "--loop-previous-x", dest="previous", type=int)
    parser.add_argument("--current", "--loop-current-x", dest="current", type=int)
    parser.add_argument("--log"); parser.add_argument("--loop-log"); parser.add_argument("--minimum-loop-iterations", type=int, default=2)
    parser.add_argument("--hardware-contact", type=int, choices=(0, 1), default=1)
    parser.add_argument("--artifact"); parser.add_argument("--write", action="store_true"); parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.validate_loop_line is not None:
            if None in (args.sequence, args.previous, args.current):
                raise ValueError("--validate-loop-line requires sequence/previous/current")
            validate_transition(args.validate_loop_line, args.sequence_key, args.sequence, args.previous, args.current)
            result = {"status": "PASS_R10_NATIVE_GUARDED_CORRIDOR_CACHED_MODE2_CADENCE_LOOP_LINE", "schema": SCHEMA, "sequence_key": args.sequence_key, "sequence": args.sequence}
        elif args.self_test:
            result = self_test()
        else:
            if bool(args.log) == bool(args.loop_log):
                raise ValueError("exactly one of --log or --loop-log is required")
            result = parse_log(Path(args.log).read_text(encoding="utf-8"), args.minimum_loop_iterations) if args.log else parse_loop(Path(args.loop_log).read_text(encoding="utf-8"), args.minimum_loop_iterations)
            result["hardware_contact"] = args.hardware_contact
        output = json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
        if args.write and args.artifact:
            target = Path(args.artifact); target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(target.suffix + ".tmp"); temporary.write_text(output, encoding="utf-8"); temporary.replace(target)
        print(output, end="")
        return 0
    except Exception as exc:
        print(f"NO_GO_R10_NATIVE_GUARDED_CORRIDOR_CACHED_MODE2_CADENCE_LOG: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
