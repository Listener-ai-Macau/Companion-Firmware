#!/usr/bin/env python3
"""Parse R10 qualification/loop telemetry and exercise negative fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Callable

import verify_wb55_ssd1681_r10_ball_pixel_oracle as oracle


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/validation/companion-ssd1681-r10-r3-ball-log-parser-20260722.json"
PREFIX = "[epaper] phase_parallel_r10_ball schema=v2"
R4_PREFIX = "[epaper] phase_parallel_r10_ball schema=v3"
R5_PREFIX = "[epaper] phase_parallel_r10_ball schema=v4"
R6_PREFIX = "[epaper] phase_parallel_r10_ball schema=v5"
R5_LUT_SHA256 = "447FB169543F3E33EA6080607B685E2ADB8F38066952FCDF020882359BA94E89"
R6_LUT_SHA256 = "8525533D1971CE99F46A1AD6580741920B7FA152D2A99632206BE0E17696A5E8"
STALE_PREFIX = "[epaper] phase_parallel_r9"


class LogFailure(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def write_artifact_atomic(path: Path, value: object) -> bytes:
    rendered = (json.dumps(value, sort_keys=True) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(rendered)
    temporary.replace(path)
    return rendered


def require(condition: bool, message: str) -> None:
    if not condition:
        raise LogFailure(message)


def fields(line: str) -> dict[str, str]:
    return dict(re.findall(r"\b([A-Za-z0-9_]+)=([^\s]+)", line))


def integer(record: dict[str, str], name: str) -> int:
    try:
        return int(record[name], 0)
    except (KeyError, ValueError) as error:
        raise LogFailure(f"missing or invalid integer field {name}") from error


def assert_equal(record: dict[str, str], expected: dict[str, str], context: str) -> None:
    for name, value in expected.items():
        require(record.get(name) == value, f"{context}: {name}={record.get(name)!r}, expected {value!r}")


def expected_transition(previous_x: int | None, current_x: int) -> dict[str, object]:
    return oracle.assert_transition(
        oracle.frame_for_position(previous_x),
        oracle.frame_for_position(current_x),
        previous_x,
        current_x,
    )


def r4_transition(previous_x: int | None, current_x: int) -> dict[str, object]:
    transition = dict(expected_transition(previous_x, current_x))
    previous = oracle.frame_for_position(previous_x)
    current = oracle.frame_for_position(current_x)
    window = {
        "x_start_byte": 4,
        "x_end_byte": 9,
        "y_start": 80,
        "y_end": 91,
        "bytes": 72,
        "changed": True,
    }
    transition["window"] = window
    transition["previous_payload_sha256"] = sha256(oracle.payload(previous, window))
    transition["current_payload_sha256"] = sha256(oracle.payload(current, window))
    transition["transition_classes"] = oracle.count_classes(previous, current, window)
    return transition


def validate_frame(line: str, event: str, sequence: int, previous_x: int | None, current_x: int) -> int:
    record = fields(line)
    schema = record.get("schema")
    require(schema in ("v2", "v3", "v4", "v5"), f"unsupported frame schema {schema!r}")
    corridor = schema in ("v3", "v4", "v5")
    transition = r4_transition(previous_x, current_x) if corridor else expected_transition(previous_x, current_x)
    window = transition["window"]
    classes = transition["transition_classes"]
    require(integer(record, event) == sequence, f"{event} sequence is not contiguous")
    assert_equal(
        record,
        {
            "schema": schema,
            "previous_x": "white" if previous_x is None else str(previous_x),
            "current_x": str(current_x),
            "previous_frame_sha256": str(transition["previous_frame_sha256"]),
            "current_frame_sha256": str(transition["current_frame_sha256"]),
            "previous_payload_sha256": str(transition["previous_payload_sha256"]),
            "current_payload_sha256": str(transition["current_payload_sha256"]),
            "window_x_bytes": f"{window['x_start_byte']}-{window['x_end_byte']}",
            "window_y": f"{window['y_start']}-{window['y_end']}",
            "window_bytes": str(window["bytes"]),
            "changed_pixels": str(transition["changed_pixels"]),
            "ww": str(classes["ww"]),
            "wb": str(classes["wb"]),
            "bw": str(classes["bw"]),
            "bb": str(classes["bb"]),
            "old_command": "0x26",
            "old_selector": "1",
            "old_writes": "1",
            "old_bytes": str(window["bytes"]),
            "new_command": "0x24",
            "new_selector": "0",
            "stage_writes_24": "1",
            "new_bytes": str(window["bytes"]),
            "control_22": "0xCF",
            "controls_cf": "1",
            "refresh": "0x20",
            "refresh_20": "1",
            "busy_complete": "1",
            "post_sync_command": "0x24",
            "post_sync_writes": "1",
            "post_sync_bytes": str(window["bytes"]),
            "post_sync_refresh": "0",
            "hold_count": "1",
            "full_frame_writes": "0",
            "full_refreshes": "0",
            "controls_ff": "0",
            "controls_f7": "0",
            "controls_c7": "0",
            "controls_37": "0",
            "second_activations": "0",
            "retries": "0",
            "maintenance_refreshes": "0",
            "step_ok": "1",
        },
        f"{event}={sequence}",
    )
    busy = integer(record, "busy_elapsed_ms")
    require(0 <= busy <= 600, f"{event}={sequence}: BUSY elapsed {busy} exceeds 600 ms")
    require(line.count("hold_elapsed_ms=") == 1, f"{event}={sequence}: expected exactly one stable hold")
    require(line.count("hold_count=") == 1, f"{event}={sequence}: expected exactly one hold count")
    require(line.index("busy_complete=1") < line.index("post_sync_command=0x24") < line.index("hold_elapsed_ms="),
            f"{event}={sequence}: stable hold is not after BUSY and post-sync 0x24")
    hold = integer(record, "hold_elapsed_ms")
    require(400 <= hold <= 410, f"{event}={sequence}: stable hold {hold} ms is outside 400-410 ms")
    return busy


def parse_log(text: str, minimum_loop_iterations: int = 1) -> dict[str, object]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    require(not any(STALE_PREFIX in line for line in lines), "stale R9 marker is not accepted")
    r10_lines = [line for line in lines if line.startswith(PREFIX) or line.startswith(R4_PREFIX) or line.startswith(R5_PREFIX) or line.startswith(R6_PREFIX)]
    require(r10_lines, "missing R10 telemetry")
    schemas = {fields(line).get("schema") for line in r10_lines}
    require(schemas in ({"v2"}, {"v3"}, {"v4"}, {"v5"}), "mixed R10 telemetry schemas are not accepted")
    schema = next(iter(schemas))
    corridor = schema in ("v3", "v4", "v5")
    lut_sha = R6_LUT_SHA256 if schema == "v5" else R5_LUT_SHA256 if schema == "v4" else oracle.LUT_SHA256

    for line in r10_lines:
        record = fields(line)
        for name in ("popup_commands", "popup_invocations", "popup_actual"):
            if name in record:
                require(integer(record, name) == 0, f"popup is forbidden on machine/routine/fault path: {name}")
        if "retries" in record:
            require(integer(record, "retries") == 0, "retry counter is nonzero")

    armed = [line for line in r10_lines if " armed " in f" {line} "]
    starts = [line for line in r10_lines if " start " in f" {line} "]
    lut_loads = [line for line in r10_lines if " lut_load " in f" {line} "]
    qualification = [line for line in r10_lines if "qualification_frame" in fields(line)]
    results = [line for line in r10_lines if "qualification_result" in fields(line)]
    ready = [line for line in r10_lines if " observation_ready " in f" {line} "]
    loops = [line for line in r10_lines if "loop_iteration" in fields(line)]
    faults = [line for line in r10_lines if " fault " in f" {line} "]

    require(len(armed) == 1, "expected exactly one armed record")
    require(len(starts) == 1, "expected exactly one start record")
    require(len(lut_loads) == 1, "expected exactly one LUT-load record")
    require(fields(armed[0]).get("telemetry_storage") == "host_ring_65536", "telemetry storage is not the fixed 65536-byte ring")
    assert_equal(
        fields(starts[0]),
        {
            "candidate": "r10_actual_solid_ball",
            "geometry": "12x12",
            "black_pixels": "112",
            "y": "80",
            "positions": "32,40,48,56,64",
            "step_px": "8",
            "travel_px": "32",
            "path": "ping_pong",
            "framebuffer": "200x200",
            "full_frame_bytes": "5000",
            "diff": "full_previous_current",
            "union_window": "exact_byte_aligned",
            "lut_sha256": lut_sha,
            "voltage_tail": oracle.TAIL_HEX,
            "busy_limit_ms": "600",
            "stable_hold_target_ms": "400-410",
            "full_frame_writes": "0",
            "full_refreshes": "0",
            "controls_ff": "0",
            "controls_f7": "0",
            "controls_c7": "0",
            "controls_37": "0",
            "second_activations": "0",
            "retries": "0",
            "maintenance_refreshes": "0",
            "production_enabled": "0",
        },
        "start",
    )
    if corridor:
        require(fields(starts[0]).get("corridor_window") == "x4-9,y80-91,bytes72", "R4 start corridor is not fixed at 4..9/80..91/72")
    assert_equal(
        fields(lut_loads[0]),
        {
            "command": "0x32",
            "payload_bytes": "153",
            "tails": "3F:22,03:17,04:41A832,2C:58",
            "candidate_sha256": lut_sha,
            "loads": "1",
            "loaded": "1",
        },
        "lut_load",
    )
    require(not faults, "fault record is present in a PASS log")
    require(len(qualification) == 16, f"expected 16 qualification frames, found {len(qualification)}")

    busy_values: list[int] = []
    previous_x: int | None = None
    for sequence, (line, current_x) in enumerate(zip(qualification, oracle.QUALIFICATION_POSITIONS), 1):
        busy_values.append(validate_frame(line, "qualification_frame", sequence, previous_x, current_x))
        previous_x = current_x

    require(len(results) == 1, "expected exactly one qualification result")
    result_expected = {
            "qualification_result": "ok",
            "activations_completed": "16",
            "controls_cf": "16",
            "refresh_20": "16",
            "busy_completions": "16",
            "writes_26": "16",
            "stage_writes_24": "16",
            "post_sync_24": "16",
            "post_sync_refresh": "0",
            "hold_count": "16",
            "stable_hold_target_ms": "400-410",
            "first_window_bytes": "72" if corridor else "24",
            "moving_window_bytes": "72" if corridor else "36",
            "full_frame_writes": "0",
            "full_refreshes": "0",
            "controls_ff": "0",
            "controls_f7": "0",
            "controls_c7": "0",
            "controls_37": "0",
            "second_activations": "0",
            "lut_loads": "1",
            "voltage_tail_changes": "0",
            "retries": "0",
            "maintenance_refreshes": "0",
            "bus_retained_for_loop": "1",
        }
    if corridor:
        result_expected.update({"corridor_window": "x4-9,y80-91,bytes72", "first_ww": "464", "first_wb": "112", "first_bw": "0", "first_bb": "0", "moving_ww": "376", "moving_wb": "88", "moving_bw": "88", "moving_bb": "24"})
    assert_equal(fields(results[0]), result_expected, "qualification_result")
    require(len(ready) == 1, "observation-ready marker requires one successful qualification")
    assert_equal(
        fields(ready[0]),
        {
            "loop_limit": "none",
            "next_previous_x": "40",
            "next_current_x": "32",
            "stable_hold_target_ms": "400-410",
            "telemetry_storage": "host_ring_65536",
            "popup_eligible": "1",
        },
        "observation_ready",
    )
    require(r10_lines.index(results[0]) < r10_lines.index(ready[0]), "observation started before qualification result")
    require(len(loops) >= minimum_loop_iterations, f"expected at least {minimum_loop_iterations} loop iterations")

    previous_x = 40
    for sequence, line in enumerate(loops, 1):
        current_x = oracle.LOOP_POSITIONS[(sequence - 1) % len(oracle.LOOP_POSITIONS)]
        busy_values.append(validate_frame(line, "loop_iteration", sequence, previous_x, current_x))
        previous_x = current_x

    return {
        "status": "PASS_R10_BALL_LOG",
        "hardware_contact": 0,
        "qualification_frames": len(qualification),
        "loop_iterations": len(loops),
        "busy_max_ms": max(busy_values),
        "busy_within_600_ms": True,
        "hold_min_ms": 400,
        "hold_max_ms": 410,
        "hold_within_400_410_ms": True,
        "hold_count": len(qualification) + len(loops),
        "ring_bytes": 65536,
        "popup_commands": 0,
        "retry_count": 0,
    }


def loop_positions(sequence: int) -> tuple[int, int]:
    require(sequence >= 1, "loop sequence must be positive")
    current = oracle.LOOP_POSITIONS[(sequence - 1) % len(oracle.LOOP_POSITIONS)]
    previous = 40 if sequence == 1 else oracle.LOOP_POSITIONS[(sequence - 2) % len(oracle.LOOP_POSITIONS)]
    return previous, current


def validate_loop_line(line: str, sequence: int | None = None,
                       previous_x: int | None = None, current_x: int | None = None) -> dict[str, object]:
    record = fields(line)
    actual_sequence = integer(record, "loop_iteration")
    require(sequence is None or actual_sequence == sequence,
            f"loop sequence {actual_sequence} does not match expected {sequence}")
    expected_previous, expected_current = loop_positions(actual_sequence)
    if previous_x is not None:
        expected_previous = previous_x
    if current_x is not None:
        expected_current = current_x
    busy = validate_frame(line, "loop_iteration", actual_sequence, expected_previous, expected_current)
    return {"status": "PASS_R10_LOOP_FRAME", "loop_iteration": actual_sequence, "busy_elapsed_ms": busy}


def validate_loop_preamble(lines: list[str], schema: str) -> int:
    """Validate only complete, known qualification/start lines retained before the loop."""
    qualification_sequence = 0
    for line in lines:
        record = fields(line)
        require(record.get("schema") == schema, "preamble schema drift")
        corridor = schema in ("v3", "v4", "v5")
        lut_sha = R6_LUT_SHA256 if schema == "v5" else R5_LUT_SHA256 if schema == "v4" else oracle.LUT_SHA256
        if " armed " in f" {line} ":
            assert_equal(record, {"qualification_activations": "16", "loop_limit": "none", "popup_commands": "0", "telemetry_storage": "host_ring_65536"}, "armed preamble")
        elif " start " in f" {line} ":
            require(record.get("candidate") == "r10_actual_solid_ball" and record.get("geometry") == "12x12" and record.get("diff") == "full_previous_current", "invalid start preamble")
            if corridor:
                require(record.get("corridor_window") == "x4-9,y80-91,bytes72", "invalid R4 corridor preamble")
        elif " lut_load " in f" {line} ":
            assert_equal(record, {"command": "0x32", "payload_bytes": "153", "candidate_sha256": lut_sha, "loads": "1", "loaded": "1"}, "lut preamble")
        elif "qualification_frame" in record:
            qualification_sequence += 1
            require(qualification_sequence <= 16, "too many qualification preamble frames")
            validate_frame(line, "qualification_frame", qualification_sequence, None if qualification_sequence == 1 else oracle.QUALIFICATION_POSITIONS[qualification_sequence - 2], oracle.QUALIFICATION_POSITIONS[qualification_sequence - 1])
        elif "qualification_result" in record:
            require(record.get("qualification_result") == "ok" and record.get("activations_completed") == "16", "qualification preamble is not PASS")
        elif " observation_ready " in f" {line} ":
            assert_equal(record, {"loop_limit": "none", "next_previous_x": "40", "next_current_x": "32", "telemetry_storage": "host_ring_65536", "popup_eligible": "1"}, "observation preamble")
        else:
            raise LogFailure("unknown or unsafe complete R10 preamble line")
    return len(lines)


def parse_loop_log(text: str, minimum_loop_iterations: int = 1) -> dict[str, object]:
    ended_with_line_ending = text.endswith(("\r", "\n"))
    raw_lines = text.splitlines(keepends=True)
    ignored_trailing_partial_line = False
    ignored_trailing_partial_bytes = 0
    if raw_lines and not ended_with_line_ending:
        ignored = raw_lines.pop()
        ignored_trailing_partial_line = True
        ignored_trailing_partial_bytes = len(ignored.encode("utf-8"))
    lines = [line.rstrip("\r\n").strip() for line in raw_lines if line.strip()]
    require(not any(STALE_PREFIX in line for line in lines), "stale R9 marker is not accepted")
    require(all(line.startswith(PREFIX) or line.startswith(R4_PREFIX) or line.startswith(R5_PREFIX) or line.startswith(R6_PREFIX) for line in lines), "malformed complete R10 loop line")
    schemas = {fields(line).get("schema") for line in lines}
    require(schemas in ({"v2"}, {"v3"}, {"v4"}, {"v5"}), "mixed R10 loop/preamble schemas are not accepted")
    schema = next(iter(schemas))
    first_loop = next((index for index, line in enumerate(lines) if "loop_iteration" in fields(line)), None)
    require(first_loop is not None, "missing loop records after R10 preamble")
    preamble = lines[:first_loop]
    validate_loop_preamble(preamble, schema)
    loops = lines[first_loop:]
    require(all("loop_iteration" in fields(line) for line in loops), "malformed complete R10 loop line")
    require(len(loops) >= minimum_loop_iterations,
            f"expected at least {minimum_loop_iterations} loop iterations")
    previous_sequence: int | None = None
    busy_values: list[int] = []
    for line in loops:
        sequence = integer(fields(line), "loop_iteration")
        if previous_sequence is not None:
            require(sequence == previous_sequence + 1,
                    f"non-contiguous loop iteration {sequence} after {previous_sequence}")
        busy_values.append(int(validate_loop_line(line)["busy_elapsed_ms"]))
        previous_sequence = sequence
    return {
        "status": "PASS_R10_LOOP_LOG",
        "loop_iterations": len(loops),
        "first_loop_iteration": integer(fields(loops[0]), "loop_iteration"),
        "last_loop_iteration": previous_sequence,
        "busy_max_ms": max(busy_values),
        "busy_within_600_ms": True,
        "ring_bytes": 65536,
        "ignored_trailing_partial_line": ignored_trailing_partial_line,
        "ignored_trailing_partial_bytes": ignored_trailing_partial_bytes,
        "ignored_preamble_lines": len(preamble),
    }


def frame_line(event: str, sequence: int, previous_x: int | None, current_x: int, busy: int = 500) -> str:
    transition = expected_transition(previous_x, current_x)
    window = transition["window"]
    classes = transition["transition_classes"]
    return (
        f"{PREFIX} {event}={sequence} previous_x={'white' if previous_x is None else previous_x} current_x={current_x} "
        f"previous_frame_sha256={transition['previous_frame_sha256']} current_frame_sha256={transition['current_frame_sha256']} "
        f"previous_payload_sha256={transition['previous_payload_sha256']} current_payload_sha256={transition['current_payload_sha256']} "
        f"window_x_bytes={window['x_start_byte']}-{window['x_end_byte']} window_y={window['y_start']}-{window['y_end']} "
        f"window_bytes={window['bytes']} changed_pixels={transition['changed_pixels']} "
        f"ww={classes['ww']} wb={classes['wb']} bw={classes['bw']} bb={classes['bb']} "
        f"old_command=0x26 old_selector=1 old_writes=1 old_bytes={window['bytes']} "
        f"new_command=0x24 new_selector=0 stage_writes_24=1 new_bytes={window['bytes']} "
        f"control_22=0xCF controls_cf=1 refresh=0x20 refresh_20=1 busy_complete=1 busy_elapsed_ms={busy} "
        f"post_sync_command=0x24 post_sync_writes=1 post_sync_bytes={window['bytes']} post_sync_refresh=0 hold_elapsed_ms=400 hold_count=1 "
        "full_frame_writes=0 full_refreshes=0 controls_ff=0 controls_f7=0 controls_c7=0 controls_37=0 "
        "second_activations=0 retries=0 maintenance_refreshes=0 step_ok=1"
    )


def r4_frame_line(event: str, sequence: int, previous_x: int | None, current_x: int, busy: int = 500) -> str:
    transition = r4_transition(previous_x, current_x)
    window = transition["window"]
    classes = transition["transition_classes"]
    return (
        f"{R4_PREFIX} {event}={sequence} previous_x={'white' if previous_x is None else previous_x} current_x={current_x} "
        f"previous_frame_sha256={transition['previous_frame_sha256']} current_frame_sha256={transition['current_frame_sha256']} "
        f"previous_payload_sha256={transition['previous_payload_sha256']} current_payload_sha256={transition['current_payload_sha256']} "
        f"window_x_bytes=4-9 window_y=80-91 window_bytes=72 changed_pixels={transition['changed_pixels']} "
        f"ww={classes['ww']} wb={classes['wb']} bw={classes['bw']} bb={classes['bb']} "
        "old_command=0x26 old_selector=1 old_writes=1 old_bytes=72 "
        "new_command=0x24 new_selector=0 stage_writes_24=1 new_bytes=72 "
        f"control_22=0xCF controls_cf=1 refresh=0x20 refresh_20=1 busy_complete=1 busy_elapsed_ms={busy} "
        "post_sync_command=0x24 post_sync_writes=1 post_sync_bytes=72 post_sync_refresh=0 hold_elapsed_ms=400 hold_count=1 "
        "full_frame_writes=0 full_refreshes=0 controls_ff=0 controls_f7=0 controls_c7=0 controls_37=0 "
        "second_activations=0 retries=0 maintenance_refreshes=0 step_ok=1"
    )


def r4_positive_log(loop_iterations: int = 3) -> str:
    lines = [
        f"{R4_PREFIX} armed qualification_activations=16 loop_limit=none popup_commands=0 telemetry_storage=host_ring_65536",
        f"{R4_PREFIX} start candidate=r10_actual_solid_ball geometry=12x12 black_pixels=112 y=80 positions=32,40,48,56,64 step_px=8 travel_px=32 path=ping_pong framebuffer=200x200 full_frame_bytes=5000 diff=full_previous_current union_window=exact_byte_aligned corridor_window=x4-9,y80-91,bytes72 lut_sha256={oracle.LUT_SHA256} voltage_tail=221741A83258 old_command=0x26 old_selector=1 new_command=0x24 new_selector=0 post_sync_command=0x24 control=0xCF refresh=0x20 busy_limit_ms=600 stable_hold_target_ms=400-410 full_frame_writes=0 full_refreshes=0 controls_ff=0 controls_f7=0 controls_c7=0 controls_37=0 second_activations=0 retries=0 maintenance_refreshes=0 production_enabled=0",
        f"{R4_PREFIX} lut_load command=0x32 payload_bytes=153 tails=3F:22,03:17,04:41A832,2C:58 candidate_sha256={oracle.LUT_SHA256} loads=1 loaded=1",
    ]
    previous_x: int | None = None
    for sequence, current_x in enumerate(oracle.QUALIFICATION_POSITIONS, 1):
        lines.append(r4_frame_line("qualification_frame", sequence, previous_x, current_x))
        previous_x = current_x
    lines.extend((
        f"{R4_PREFIX} qualification_result=ok activations_completed=16 controls_cf=16 refresh_20=16 busy_completions=16 writes_26=16 stage_writes_24=16 post_sync_24=16 post_sync_refresh=0 hold_count=16 stable_hold_target_ms=400-410 first_window_bytes=72 moving_window_bytes=72 corridor_window=x4-9,y80-91,bytes72 first_ww=464 first_wb=112 first_bw=0 first_bb=0 moving_ww=376 moving_wb=88 moving_bw=88 moving_bb=24 full_frame_writes=0 full_refreshes=0 controls_ff=0 controls_f7=0 controls_c7=0 controls_37=0 second_activations=0 lut_loads=1 voltage_tail_changes=0 retries=0 maintenance_refreshes=0 bus_retained_for_loop=1",
        f"{R4_PREFIX} observation_ready loop_limit=none next_previous_x=40 next_current_x=32 stable_hold_target_ms=400-410 corridor_window=x4-9,y80-91,bytes72 telemetry_storage=host_ring_65536 popup_eligible=1",
    ))
    previous_x = 40
    for sequence in range(1, loop_iterations + 1):
        current_x = oracle.LOOP_POSITIONS[(sequence - 1) % len(oracle.LOOP_POSITIONS)]
        lines.append(r4_frame_line("loop_iteration", sequence, previous_x, current_x))
        previous_x = current_x
    return "\n".join(lines) + "\n"


def r5_positive_log(loop_iterations: int = 3) -> str:
    """Produce the v4 R5 telemetry shape without changing the frame contract."""
    return r4_positive_log(loop_iterations).replace(R4_PREFIX, R5_PREFIX).replace(oracle.LUT_SHA256, R5_LUT_SHA256)


def r6_positive_log(loop_iterations: int = 3) -> str:
    """Produce the v5 R6 telemetry shape without changing the frame contract."""
    return r5_positive_log(loop_iterations).replace(R5_PREFIX, R6_PREFIX).replace(R5_LUT_SHA256, R6_LUT_SHA256)


def positive_log(loop_iterations: int = 8) -> str:
    lines = [
        f"{PREFIX} armed qualification_activations=16 loop_limit=none popup_commands=0 telemetry_storage=host_ring_65536",
        f"{PREFIX} start candidate=r10_actual_solid_ball geometry=12x12 black_pixels=112 y=80 positions=32,40,48,56,64 step_px=8 travel_px=32 path=ping_pong framebuffer=200x200 full_frame_bytes=5000 diff=full_previous_current union_window=exact_byte_aligned lut_sha256={oracle.LUT_SHA256} voltage_tail={oracle.TAIL_HEX} old_command=0x26 old_selector=1 new_command=0x24 new_selector=0 post_sync_command=0x24 control=0xCF refresh=0x20 busy_limit_ms=600 busy_target_ms=475-550 stable_hold_target_ms=400-410 full_frame_writes=0 full_refreshes=0 controls_ff=0 controls_f7=0 controls_c7=0 controls_37=0 second_activations=0 retries=0 maintenance_refreshes=0 production_enabled=0",
        f"{PREFIX} lut_load command=0x32 payload_bytes=153 tails=3F:22,03:17,04:41A832,2C:58 candidate_sha256={oracle.LUT_SHA256} loads=1 loaded=1",
    ]
    previous_x: int | None = None
    for sequence, current_x in enumerate(oracle.QUALIFICATION_POSITIONS, 1):
        lines.append(frame_line("qualification_frame", sequence, previous_x, current_x))
        previous_x = current_x
    lines.extend(
        (
            f"{PREFIX} qualification_result=ok activations_completed=16 controls_cf=16 refresh_20=16 busy_completions=16 writes_26=16 stage_writes_24=16 post_sync_24=16 post_sync_refresh=0 hold_count=16 stable_hold_target_ms=400-410 first_window_bytes=24 moving_window_bytes=36 full_frame_writes=0 full_refreshes=0 controls_ff=0 controls_f7=0 controls_c7=0 controls_37=0 second_activations=0 lut_loads=1 voltage_tail_changes=0 retries=0 maintenance_refreshes=0 qualification_elapsed_ms=14400 bus_retained_for_loop=1",
            f"{PREFIX} observation_ready loop_limit=none next_previous_x=40 next_current_x=32 stable_hold_target_ms=400-410 telemetry_storage=host_ring_65536 popup_eligible=1",
        )
    )
    previous_x = 40
    for sequence in range(1, loop_iterations + 1):
        current_x = oracle.LOOP_POSITIONS[(sequence - 1) % len(oracle.LOOP_POSITIONS)]
        lines.append(frame_line("loop_iteration", sequence, previous_x, current_x))
        previous_x = current_x
    return "\n".join(lines) + "\n"


def replace_once(old: str, new: str) -> Callable[[str], str]:
    def mutate(text: str) -> str:
        require(old in text, f"fixture source token is missing: {old}")
        return text.replace(old, new, 1)

    return mutate


def remove_line_containing(token: str) -> Callable[[str], str]:
    def mutate(text: str) -> str:
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if token in line:
                del lines[index]
                return "\n".join(lines) + "\n"
        raise LogFailure(f"fixture line is missing: {token}")

    return mutate


def duplicate_line_containing(token: str) -> Callable[[str], str]:
    def mutate(text: str) -> str:
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if token in line:
                lines.insert(index + 1, line)
                return "\n".join(lines) + "\n"
        raise LogFailure(f"fixture line is missing: {token}")

    return mutate


def remove_last_token(token: str) -> Callable[[str], str]:
    def mutate(text: str) -> str:
        index = text.rfind(token)
        require(index >= 0, f"fixture token is missing: {token}")
        return text[:index] + text[index + len(token):]
    return mutate


def negative_fixtures(base: str) -> list[dict[str, str]]:
    fixtures: list[tuple[str, Callable[[str], str]]] = [
        ("missing_frame", remove_line_containing("qualification_frame=16")),
        ("extra_frame", duplicate_line_containing("qualification_frame=16")),
        ("wrong_position", replace_once("qualification_frame=1 previous_x=white current_x=32", "qualification_frame=1 previous_x=white current_x=40")),
        ("wrong_step", replace_once("qualification_frame=2 previous_x=32 current_x=40", "qualification_frame=2 previous_x=32 current_x=48")),
        ("wrong_window", replace_once("window_x_bytes=4-5", "window_x_bytes=4-4")),
        ("clipped_disk", replace_once("changed_pixels=112", "changed_pixels=111")),
        ("square_payload", replace_once("current_payload_sha256=15C1A7E76242A2D1A91BAB445FF2CB7669A9776E22E6281D99ED01A327384763", "current_payload_sha256=" + "0" * 64)),
        ("wrong_previous_frame_hash", replace_once("previous_frame_sha256=D41BF2913D4C6ED6E9EF11EB8B9064AC3125A7A95B48F60E305DACF048D15C2B", "previous_frame_sha256=" + "0" * 64)),
        ("wrong_current_frame_hash", replace_once("current_frame_sha256=FD4063FBC8A62425D84B9D04E8E1DE703C97F9175E98057B5B80C6FBFBD0D7C8", "current_frame_sha256=" + "0" * 64)),
        ("wrong_previous_payload_hash", replace_once("previous_payload_sha256=44A5F7891570E5631E8C91C85186E6633F4AB5364F644040B2A00126A07985B6", "previous_payload_sha256=" + "0" * 64)),
        ("wrong_current_payload_hash", replace_once("current_payload_sha256=15C1A7E76242A2D1A91BAB445FF2CB7669A9776E22E6281D99ED01A327384763", "current_payload_sha256=" + "F" * 64)),
        ("wrong_class_count", replace_once("ww=80 wb=112", "ww=81 wb=111")),
        ("missing_0x26", replace_once("old_writes=1", "old_writes=0")),
        ("extra_0x26", replace_once("old_writes=1", "old_writes=2")),
        ("missing_staged_0x24", replace_once("stage_writes_24=1", "stage_writes_24=0")),
        ("extra_staged_0x24", replace_once("stage_writes_24=1", "stage_writes_24=2")),
        ("missing_post_sync_0x24", replace_once("post_sync_writes=1", "post_sync_writes=0")),
        ("extra_post_sync_0x24", replace_once("post_sync_writes=1", "post_sync_writes=2")),
        ("missing_cf", replace_once("controls_cf=1", "controls_cf=0")),
        ("extra_cf", replace_once("controls_cf=1", "controls_cf=2")),
        ("missing_0x20", replace_once("refresh_20=1", "refresh_20=0")),
        ("extra_0x20", replace_once("refresh_20=1", "refresh_20=2")),
        ("busy_over_600", replace_once("busy_elapsed_ms=500", "busy_elapsed_ms=601")),
        ("second_activation", replace_once("second_activations=0", "second_activations=1")),
        ("full_frame_write", replace_once("full_frame_writes=0", "full_frame_writes=1")),
        ("control_f7", replace_once("controls_f7=0", "controls_f7=1")),
        ("control_c7", replace_once("controls_c7=0", "controls_c7=1")),
        ("control_ff", replace_once("controls_ff=0", "controls_ff=1")),
        ("control_37", replace_once("controls_37=0", "controls_37=1")),
        ("retry", replace_once("retries=0", "retries=1")),
        ("non_contiguous_loop", replace_once("loop_iteration=2", "loop_iteration=3")),
        ("qualification_failure_followed_by_observation", replace_once("qualification_result=ok", "qualification_result=no_go")),
        ("unbounded_storage", replace_once("telemetry_storage=host_ring_65536", "telemetry_storage=unbounded")),
        ("popup_on_routine_path", replace_once("popup_commands=0", "popup_commands=1")),
        ("popup_on_fault_path", lambda text: text + f"{PREFIX} fault phase=loop popup_commands=1 retries=0\n"),
        ("stale_r9_marker", lambda text: text + "[epaper] phase_parallel_r9_continuous observation_ready\n"),
        ("hold_zero", replace_once("hold_elapsed_ms=400", "hold_elapsed_ms=0")),
        ("hold_399", replace_once("hold_elapsed_ms=400", "hold_elapsed_ms=399")),
        ("hold_411", replace_once("hold_elapsed_ms=400", "hold_elapsed_ms=411")),
        ("missing_qualification_hold", replace_once("hold_elapsed_ms=400 ", "")),
        ("missing_loop_hold", remove_last_token("hold_elapsed_ms=400 ")),
        ("double_hold", replace_once("hold_elapsed_ms=400", "hold_elapsed_ms=400 hold_elapsed_ms=400")),
        ("hold_before_busy", replace_once("busy_complete=1 busy_elapsed_ms=500 post_sync_command=0x24 post_sync_writes=1 post_sync_bytes=24 post_sync_refresh=0 hold_elapsed_ms=400 hold_count=1", "hold_elapsed_ms=400 hold_count=1 busy_complete=1 busy_elapsed_ms=500 post_sync_command=0x24 post_sync_writes=1 post_sync_bytes=24 post_sync_refresh=0")),
        ("hold_before_post_sync", replace_once("busy_complete=1 busy_elapsed_ms=500 post_sync_command=0x24 post_sync_writes=1 post_sync_bytes=24 post_sync_refresh=0 hold_elapsed_ms=400 hold_count=1", "busy_complete=1 busy_elapsed_ms=500 hold_elapsed_ms=400 hold_count=1 post_sync_command=0x24 post_sync_writes=1 post_sync_bytes=24 post_sync_refresh=0")),
    ]
    results = []
    for name, mutate in fixtures:
        try:
            parse_log(mutate(base), minimum_loop_iterations=8)
        except LogFailure as error:
            results.append({"name": name, "result": "rejected", "reason": str(error)})
        else:
            raise LogFailure(f"negative fixture was accepted: {name}")
    return results


def build_artifact() -> dict[str, object]:
    positive = positive_log()
    parsed = parse_log(positive, minimum_loop_iterations=8)
    negatives = negative_fixtures(positive)
    return {
        "schema_id": "companion.wb55.ssd1681.r10_r3_ball_log_parser.v2",
        "status": "PASS_R10_BALL_LOG_PARSER",
        "authority": "COMP-REQ-332",
        "positive": {**parsed, "log_sha256": sha256(positive.encode("utf-8"))},
        "negative_fixtures": negatives,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path)
    parser.add_argument("--loop-log", type=Path)
    parser.add_argument("--validate-loop-line")
    parser.add_argument("--loop-sequence", type=int)
    parser.add_argument("--loop-previous-x", type=int)
    parser.add_argument("--loop-current-x", type=int)
    parser.add_argument("--minimum-loop-iterations", type=int, default=1)
    parser.add_argument("--hardware-contact", type=int, choices=(0, 1), default=0)
    parser.add_argument("--artifact", type=Path, default=ARTIFACT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        if args.log is not None:
            result = parse_log(args.log.read_text(encoding="utf-8", errors="replace"), args.minimum_loop_iterations)
            result["hardware_contact"] = args.hardware_contact
            rendered = write_artifact_atomic(args.artifact, result) if args.write else (json.dumps(result, sort_keys=True) + "\n").encode("utf-8")
            print(rendered.decode("utf-8"), end="")
            return 0
        if args.loop_log is not None:
            result = parse_loop_log(args.loop_log.read_text(encoding="utf-8", errors="replace"), args.minimum_loop_iterations)
            result["hardware_contact"] = args.hardware_contact
            if args.write:
                rendered = write_artifact_atomic(args.artifact, result)
            else:
                rendered = (json.dumps(result, sort_keys=True) + "\n").encode("utf-8")
            print(rendered.decode("utf-8"), end="")
            return 0
        if args.validate_loop_line is not None:
            result = validate_loop_line(args.validate_loop_line, args.loop_sequence,
                                        args.loop_previous_x, args.loop_current_x)
            print(json.dumps(result, sort_keys=True))
            return 0
        artifact = build_artifact()
    except (OSError, oracle.OracleFailure, LogFailure) as error:
        print(f"FAIL: R10 ball log parser: {error}")
        return 1
    rendered = (json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if args.write:
        args.artifact.parent.mkdir(parents=True, exist_ok=True)
        args.artifact.write_bytes(rendered)
    elif not args.artifact.exists() or args.artifact.read_bytes() != rendered:
        print(f"FAIL: stale R10 ball log-parser artifact: {args.artifact.relative_to(ROOT).as_posix()}")
        return 1
    print(f"PASS: R10 ball log parser negative_fixtures={len(artifact['negative_fixtures'])}")
    print(f"artifact={args.artifact.relative_to(ROOT).as_posix()} sha256={sha256(args.artifact.read_bytes())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
