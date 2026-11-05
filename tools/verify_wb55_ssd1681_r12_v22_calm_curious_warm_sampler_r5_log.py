"""Strict offline parser for the R12 three-expression sampler telemetry."""
from __future__ import annotations

import argparse
import json
import re
import tempfile
from pathlib import Path

CANDIDATE = "r12_v22_calm_curious_warm_sampler"
SCHEMA = "v2"
WINDOW = "4-21,22-127"
BASELINE_WINDOW = "0-24,0-199"
TRANSITIONS = ((0, 1), (1, 2), (2, 1), (1, 0))
FRAME_NAMES = {0: "calm", 1: "curious", 2: "warm"}
SOURCE_SHA = {
    0: "DCDE74BE44CD33E881F33BC4FC6397D6269A4749BE90BCD7A1999A53D44D4B79",
    1: "C8D856E609C82AA88BF45EAC506BAC153AEF081A49289138F80E08813582F78F",
    2: "8A822CA758361B7956371C6DF7A750E5DFC01947E454F14B289AE5B1BA381356",
}
FRAME_SHA = {
    0: "15788734073049E9967DEA97783522CE1139023FC0AD9BA0F1C5375F2F2E555C",
    1: "E98E7E347943A67F92735E9F83F71D12FC214944C7E27B8B8E0225B0F5514705",
    2: "931CADB6B5209BB7B3035585994664281B037753605939EFC745A62A5889E29B",
}
PAYLOAD_SHA = {
    0: "6FFA8C8A70D87DC46AC323BFF385FEAAAD25A4C6E67E875B8030844A8158CC5B",
    1: "B3FF181ED6993CBBC4DE692941793CC81C7B3D40A99528D332CBAFF54D1F6A18",
    2: "15CAAB219B74A45B4E0F8F5E3CB046DB3554264E1D48DB92CE13F8260FDCD2C4",
}
RECORD_KEYS = ("s", "q", "i", "p", "n", "w", "h", "r", "t", "b", "d",
               "a", "x", "y", "f", "c", "l", "v", "g")
CADENCE_LIMIT_MS = 480
MAX_LINE_BYTES = 192
FAULT_REASONS = {"activation", "transaction", "busy", "cadence"}
REQUIRED_METADATA = {
    "armed", "start", "movement", "limits", "source0", "source1", "source2",
    "frame0", "frame1", "frame2", "baseline", "qualification_result",
    "observation_ready",
}


def payload(frame_id: int) -> str:
    try:
        return PAYLOAD_SHA[frame_id]
    except KeyError as exc:
        raise ValueError("frame id") from exc


def node_for(sequence: int) -> tuple[int, int]:
    if sequence < 1 or sequence > 0xFFFFFFFF:
        raise ValueError("sequence")
    return TRANSITIONS[(sequence - 1) % len(TRANSITIONS)]


def fields(text: str) -> dict[str, str]:
    parts = text.split(" ")
    if not parts or any(not part or "=" not in part for part in parts):
        raise ValueError("malformed metadata field")
    result: dict[str, str] = {}
    for part in parts:
        key, value = part.split("=", 1)
        if not key or not value or key in result:
            raise ValueError("empty or duplicate key")
        result[key] = value
    return result


def require_values(values: dict[str, str], required: set[str], expected: dict[str, str]) -> None:
    if set(values) != required:
        raise ValueError("metadata key set")
    for key, value in expected.items():
        if values.get(key) != value:
            raise ValueError(f"metadata value: {key}")


def _content(line: str) -> str:
    if "\n" in line[:-1] or "\r" in line[:-2]:
        raise ValueError("embedded line ending")
    raw = line[:-2] if line.endswith("\r\n") else line
    if raw.endswith("\r") or raw.endswith("\n"):
        raise ValueError("line must use CRLF")
    if len((raw + "\r\n").encode("ascii")) > MAX_LINE_BYTES:
        raise ValueError("line length")
    return raw


def parse_metadata(line: str) -> tuple[str, dict[str, str]]:
    line = _content(line)
    if not line.startswith("[r12] "):
        raise ValueError("metadata prefix")
    body = line[6:]
    if body.startswith("armed "):
        values = fields(body[6:])
        require_values(values, {"candidate", "schema", "ring", "popup_commands", "production_enabled"},
                       {"candidate": CANDIDATE, "schema": SCHEMA, "ring": "65536",
                        "popup_commands": "0", "production_enabled": "0"})
        return "armed", values
    if body.startswith("start "):
        values = fields(body[6:])
        require_values(values, {"schema", "format", "frames", "path", "baseline_window",
                                 "baseline_bytes", "corridor", "corridor_bytes"},
                       {"schema": SCHEMA, "format": "200x200_1bpp",
                        "frames": "calm,curious,warm", "path": "0-1-2-1-0",
                        "baseline_window": BASELINE_WINDOW, "baseline_bytes": "5000",
                        "corridor": WINDOW, "corridor_bytes": "1908"})
        return "start", values
    if body.startswith("movement "):
        values = fields(body[9:])
        require_values(values, {"reset", "ready", "command", "control", "refresh", "activation",
                                 "full_current_corridor", "retries", "maintenance_refreshes"},
                       {"reset": "0", "ready": "1", "command": "0x24", "control": "0xCF",
                        "refresh": "0x20", "activation": "1", "full_current_corridor": "1",
                        "retries": "0", "maintenance_refreshes": "0"})
        return "movement", values
    if body.startswith("limits "):
        values = fields(body[7:])
        require_values(values, {"busy_ms", "transaction_ms", "cadence_ms", "cadence_target_ms",
                                 "ring", "production_enabled"},
                       {"busy_ms": "600", "transaction_ms": "460", "cadence_ms": "480",
                        "cadence_target_ms": "450", "ring": "65536", "production_enabled": "0"})
        return "limits", values
    if body.startswith("source "):
        values = fields(body[7:])
        require_values(values, {"id", "name", "sha"}, {})
        frame_id = _frame_id(values["id"])
        if values["name"] != FRAME_NAMES[frame_id] or values["sha"] != SOURCE_SHA[frame_id]:
            raise ValueError("source identity")
        return f"source{frame_id}", values
    if body.startswith("frame "):
        values = fields(body[6:])
        require_values(values, {"id", "sha", "payload", "polarity"}, {})
        frame_id = _frame_id(values["id"])
        if (values["sha"] != FRAME_SHA[frame_id] or
                values["payload"] != PAYLOAD_SHA[frame_id] or values["polarity"] != "invert"):
            raise ValueError("polarity-derived frame identity")
        return f"frame{frame_id}", values
    if body.startswith("baseline "):
        values = fields(body[9:])
        require_values(values, {"frame", "window", "bytes", "resets", "ready_checks", "command",
                                 "control", "refresh", "activations", "t", "b"},
                       {"frame": "0", "window": BASELINE_WINDOW, "bytes": "5000", "resets": "1",
                        "ready_checks": "1", "command": "0x24", "control": "0xFF",
                        "refresh": "0x20", "activations": "1"})
        _timing(values, baseline=True)
        return "baseline", values
    if body.startswith("qualification_result="):
        values = fields(body)
        require_values(values, {"qualification_result", "frames", "activations", "cadence_measurements",
                                 "max_start_delta_ms", "busy_limit_ms", "transaction_limit_ms",
                                 "cadence_limit_ms"},
                       {"qualification_result": "ok", "frames": "16", "activations": "16",
                        "cadence_measurements": "15", "busy_limit_ms": "600",
                        "transaction_limit_ms": "460", "cadence_limit_ms": "480"})
        if not 1 <= _decimal(values["max_start_delta_ms"], "max cadence") <= CADENCE_LIMIT_MS:
            raise ValueError("qualification cadence")
        return "qualification_result", values
    if body.startswith("observation_ready "):
        values = fields(body[18:])
        require_values(values, {"frames", "cadence_measurements", "minimum_contiguous_loops",
                                 "real_cadence_required", "loop_limit", "ring", "popup_eligible"},
                       {"frames": "16", "cadence_measurements": "15", "minimum_contiguous_loops": "2",
                        "real_cadence_required": "1", "loop_limit": "none", "ring": "65536",
                        "popup_eligible": "1"})
        return "observation_ready", values
    if body.startswith("fault "):
        values = fields(body[6:])
        require_values(values, {"schema", "phase", "index", "reason", "t", "b", "d"},
                       {"schema": SCHEMA})
        if values["phase"] not in {"qualification", "loop"} or values["reason"] not in FAULT_REASONS:
            raise ValueError("fault identity")
        index = _bounded_decimal(values["index"], "fault index")
        transaction_ms = _bounded_decimal(values["t"], "fault transaction")
        busy_ms = _bounded_decimal(values["b"], "fault busy")
        delta_ms = _bounded_decimal(values["d"], "fault cadence")
        if index < 1:
            raise ValueError("fault index")
        cadence_invalid = delta_ms > CADENCE_LIMIT_MS or (index > 1 and delta_ms < 1)
        expected_reason = ("busy" if busy_ms > 600 else
                           "transaction" if transaction_ms > 460 else
                           "cadence" if cadence_invalid else "activation")
        if values["reason"] != expected_reason:
            raise ValueError("fault reason priority")
        return "fault", values
    raise ValueError("unknown or malformed [r12] metadata")


def _frame_id(value: str) -> int:
    frame_id = _decimal(value, "frame id")
    if frame_id not in FRAME_NAMES:
        raise ValueError("frame id")
    return frame_id


def _decimal(value: str, name: str) -> int:
    if not re.fullmatch(r"0|[1-9][0-9]*", value):
        raise ValueError(name)
    return int(value, 10)


def _bounded_decimal(value: str, name: str) -> int:
    parsed = _decimal(value, name)
    if parsed > 0xFFFFFFFF:
        raise ValueError(name)
    return parsed


def _timing(values: dict[str, str], baseline: bool = False) -> dict[str, int]:
    names = ("t", "b") if baseline else ("r", "t", "b", "d", "a", "x", "y", "f", "c", "l", "v", "g")
    parsed = {name: _decimal(values[name], f"numeric {name}") for name in names}
    if parsed["b"] > 600 or (not baseline and parsed["t"] > 460):
        raise ValueError("timing limit")
    return parsed


def parse(line: str, sequence_key: str | None = None, sequence: int | None = None,
          previous: int | None = None, current: int | None = None) -> dict[str, object]:
    raw = _content(line)
    if not raw.startswith(f"[r12] s={SCHEMA} "):
        raise ValueError("wrong R12 record prefix")
    values = fields(raw[6:])
    key = "q" if "q" in values else "i" if "i" in values else ""
    expected_keys = set(RECORD_KEYS) - ({"i"} if key == "q" else {"q"})
    if not key or set(values) != expected_keys:
        raise ValueError("unknown, missing, duplicate, or mixed record keys")
    if values["s"] != SCHEMA or values["w"] != WINDOW or not re.fullmatch(r"[0-9A-F]{64}", values["h"]):
        raise ValueError("schema/window/hash")
    seq = _decimal(values[key], "sequence")
    expected_previous, expected_current = node_for(seq)
    if sequence_key and key != sequence_key:
        raise ValueError("sequence key")
    if sequence is not None and seq != sequence:
        raise ValueError("sequence")
    if _frame_id(values["p"]) != expected_previous or _frame_id(values["n"]) != expected_current:
        raise ValueError("frame order")
    if previous is not None and expected_previous != previous:
        raise ValueError("previous")
    if current is not None and expected_current != current:
        raise ValueError("current")
    if values["h"] != PAYLOAD_SHA[expected_current]:
        raise ValueError("payload")
    ints = _timing(values)
    fixed = {"r": 0, "a": 1, "x": 0, "y": 1, "f": 0, "c": 1, "l": 0, "v": 0, "g": 1}
    if any(ints[name] != value for name, value in fixed.items()):
        raise ValueError("activation fields")
    if key == "q" and seq > 16:
        raise ValueError("qualification sequence")
    if seq == 1:
        if ints["d"] != 0:
            raise ValueError("first cadence")
    elif not 1 <= ints["d"] <= CADENCE_LIMIT_MS:
        raise ValueError("cadence")
    return {"key": key, "sequence": seq, "previous": expected_previous,
            "current": expected_current, "transaction_ms": ints["t"], "busy_ms": ints["b"],
            "start_delta_ms": ints["d"], "payload_sha256": values["h"]}


def parse_log(path: Path, minimum: int, hardware_contact: int, require_metadata: bool) -> dict[str, object]:
    data = path.read_bytes()
    text = data.decode("ascii")
    records: list[dict[str, object]] = []
    metadata: dict[str, dict[str, str]] = {}
    ignored_lines = 0
    ignored_trailing_bytes = 0
    fault: dict[str, str] | None = None
    terminal_fault = False
    for line in text.splitlines(keepends=True):
        complete = line.endswith("\n")
        content = line[:-2] if line.endswith("\r\n") else line.rstrip("\n")
        if not complete:
            if content.startswith("[r12]"):
                raise ValueError("incomplete [r12] line")
            ignored_trailing_bytes += len(line.encode("ascii"))
            continue
        if not content.startswith("[r12]"):
            ignored_lines += 1
            continue
        if terminal_fault:
            raise ValueError("R12 fault is terminal")
        if not line.endswith("\r\n"):
            raise ValueError("R12 line must end in CRLF")
        if content.startswith("[r12] s="):
            records.append(parse(content))
        else:
            kind, values = parse_metadata(content)
            if kind in metadata:
                raise ValueError("duplicate R12 metadata")
            metadata[kind] = values
            if kind == "fault":
                fault = values
                terminal_fault = True
    if fault is not None:
        return {
            "status": "NO_GO_R12_V22_CALM_CURIOUS_WARM_SAMPLER_FAULT",
            "candidate": CANDIDATE, "schema": SCHEMA, "fault": fault,
            "records_before_fault": len(records), "metadata": metadata,
            "metadata_proof": True, "ring_bytes": 65536,
            "hardware_contact": hardware_contact,
            "ignored_unrelated_lines": ignored_lines,
            "ignored_trailing_partial_bytes": ignored_trailing_bytes,
        }
    qualification = [record for record in records if record["key"] == "q"]
    loops = [record for record in records if record["key"] == "i"]
    if [record["sequence"] for record in qualification] != list(range(1, 17)):
        raise ValueError("qualification sequence")
    if len(loops) < minimum:
        raise ValueError("minimum contiguous loops")
    if loops and [record["sequence"] for record in loops] != list(
            range(loops[0]["sequence"], loops[0]["sequence"] + len(loops))):
        raise ValueError("loop continuity")
    if require_metadata and set(metadata) != REQUIRED_METADATA:
        raise ValueError("R12 eligibility metadata incomplete")
    loop_cadence_records = loops[1:] if loops and loops[0]["sequence"] == 1 else loops
    cadence = [record["start_delta_ms"] for record in qualification[1:] + loop_cadence_records]
    if len(qualification) != 16 or not cadence or any(not 1 <= value <= CADENCE_LIMIT_MS for value in cadence):
        raise ValueError("qualification/cadence proof")
    if metadata:
        result_meta = metadata.get("qualification_result", {})
        if result_meta and int(result_meta["max_start_delta_ms"]) != max(record["start_delta_ms"] for record in qualification[1:]):
            raise ValueError("qualification metadata mismatch")
    return {
        "status": "PASS_R12_V22_CALM_CURIOUS_WARM_SAMPLER_LOG", "candidate": CANDIDATE,
        "schema": SCHEMA, "qualification_frames": len(qualification),
        "qualification_records": qualification, "qualification_cadence_measurements": 15,
        "loop_records": len(loops), "loop_sequence_start": loops[0]["sequence"] if loops else None,
        "cadence_measurements": len(cadence), "max_start_delta_ms": max(cadence),
        "minimum_loop_iterations": minimum, "ring_bytes": 65536, "hardware_contact": hardware_contact,
        "metadata_proof": set(metadata) == REQUIRED_METADATA, "metadata": metadata,
        "ignored_unrelated_lines": ignored_lines, "ignored_trailing_partial_bytes": ignored_trailing_bytes,
    }


def render_record(sequence: int, key: str, delta: int | None = None) -> str:
    previous, current = node_for(sequence)
    cadence = (0 if sequence == 1 else 480) if delta is None else delta
    return (f"[r12] s={SCHEMA} {key}={sequence} p={previous} n={current} w={WINDOW} "
            f"h={payload(current)} r=0 t=460 b=600 d={cadence} "
            "a=1 x=0 y=1 f=0 c=1 l=0 v=0 g=1\r\n")


def metadata_lines(max_delta: int = 480) -> list[str]:
    lines = [
        f"[r12] armed candidate={CANDIDATE} schema={SCHEMA} ring=65536 popup_commands=0 production_enabled=0\r\n",
        f"[r12] start schema={SCHEMA} format=200x200_1bpp frames=calm,curious,warm path=0-1-2-1-0 baseline_window={BASELINE_WINDOW} baseline_bytes=5000 corridor={WINDOW} corridor_bytes=1908\r\n",
        "[r12] movement reset=0 ready=1 command=0x24 control=0xCF refresh=0x20 activation=1 full_current_corridor=1 retries=0 maintenance_refreshes=0\r\n",
        "[r12] limits busy_ms=600 transaction_ms=460 cadence_ms=480 cadence_target_ms=450 ring=65536 production_enabled=0\r\n",
    ]
    for frame_id in FRAME_NAMES:
        lines.append(f"[r12] source id={frame_id} name={FRAME_NAMES[frame_id]} sha={SOURCE_SHA[frame_id]}\r\n")
    for frame_id in FRAME_NAMES:
        lines.append(f"[r12] frame id={frame_id} sha={FRAME_SHA[frame_id]} payload={PAYLOAD_SHA[frame_id]} polarity=invert\r\n")
    lines.extend([
        "[r12] baseline frame=0 window=0-24,0-199 bytes=5000 resets=1 ready_checks=1 command=0x24 control=0xFF refresh=0x20 activations=1 t=500 b=500\r\n",
        f"[r12] qualification_result=ok frames=16 activations=16 cadence_measurements=15 max_start_delta_ms={max_delta} busy_limit_ms=600 transaction_limit_ms=460 cadence_limit_ms=480\r\n",
        "[r12] observation_ready frames=16 cadence_measurements=15 minimum_contiguous_loops=2 real_cadence_required=1 loop_limit=none ring=65536 popup_eligible=1\r\n",
    ])
    return lines


def _expect_reject(name: str, operation, results: dict[str, bool]) -> None:
    try:
        operation()
    except (ValueError, UnicodeError):
        results[name] = True
    else:
        results[name] = False


def self_test() -> dict[str, object]:
    accepted = render_record(2, "q", 480)
    parse(accepted, "q", 2, 1, 2)
    results: dict[str, bool] = {}
    mutations = {
        "reject_481": accepted.replace("d=480", "d=481"),
        "wrong_window": accepted.replace(WINDOW, "3-19,64-135"),
        "wrong_payload": accepted.replace(PAYLOAD_SHA[2], "0" * 64),
        "wrong_order": accepted.replace("p=1 n=2", "p=2 n=1"),
        "unknown_key": accepted.replace(" g=1", " z=1 g=1"),
        "duplicate_key": accepted.replace(" g=1", " g=1 g=1"),
        "missing_key": accepted.replace(" c=1", ""),
        "malformed_record": accepted.replace(" n=2", " n"),
        "overlong": accepted.replace(" g=1", " z=" + "A" * 193 + " g=1"),
    }
    for name, line in mutations.items():
        _expect_reject(name, lambda line=line: parse(line), results)
    _expect_reject("bad_source_hash", lambda: parse_metadata(metadata_lines()[4].replace(SOURCE_SHA[0], "0" * 64)), results)
    _expect_reject("bad_polarity", lambda: parse_metadata(metadata_lines()[7].replace("polarity=invert", "polarity=direct")), results)
    _expect_reject("bad_polarity_payload", lambda: parse_metadata(metadata_lines()[7].replace(PAYLOAD_SHA[0], PAYLOAD_SHA[1])), results)
    faults = {
        "activation": "[r12] fault schema=v2 phase=qualification index=1 reason=activation t=460 b=600 d=0\r\n",
        "transaction": "[r12] fault schema=v2 phase=qualification index=1 reason=transaction t=461 b=600 d=0\r\n",
        "busy": "[r12] fault schema=v2 phase=qualification index=1 reason=busy t=461 b=601 d=0\r\n",
        "cadence": "[r12] fault schema=v2 phase=loop index=2 reason=cadence t=460 b=600 d=481\r\n",
    }
    for reason, line in faults.items():
        parsed_fault_kind, parsed_fault = parse_metadata(line)
        if parsed_fault_kind != "fault" or parsed_fault["reason"] != reason:
            raise ValueError(f"fault reason acceptance: {reason}")
    fault = faults["transaction"]
    _expect_reject("fault_unknown_field", lambda: parse_metadata(fault.replace(" d=0", " d=0 extra=1")), results)
    _expect_reject("fault_missing_field", lambda: parse_metadata(fault.replace(" b=600", "")), results)
    _expect_reject("fault_duplicate_field", lambda: parse_metadata(fault.replace(" d=0", " d=0 d=0")), results)
    _expect_reject("fault_unknown_reason", lambda: parse_metadata(fault.replace("reason=transaction", "reason=other")), results)
    _expect_reject("fault_out_of_range_reason", lambda: parse_metadata(fault.replace("t=461", "t=460")), results)
    _expect_reject("fault_busy_priority_mismatch", lambda: parse_metadata(faults["transaction"].replace("b=600", "b=601")), results)
    _expect_reject("fault_cadence_priority_mismatch", lambda: parse_metadata(faults["transaction"].replace("t=461", "t=460").replace("b=600", "b=600").replace("d=0", "d=481")), results)

    combined = ("[boot] unrelated=1\r\n" + "".join(metadata_lines()) + "[epaper] unrelated=1\r\n" +
                "".join(render_record(i, "q") for i in range(1, 17)) +
                render_record(1, "i") + render_record(2, "i"))
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "combined.log"
        path.write_text(combined, encoding="ascii", newline="")
        parsed = parse_log(path, 2, 0, True)
        fault_path = Path(temp) / "fault.log"
        fault_path.write_text("".join(metadata_lines()[:10]) + fault, encoding="ascii", newline="")
        fault_result = parse_log(fault_path, 2, 1, True)
        if (fault_result["status"] != "NO_GO_R12_V22_CALM_CURIOUS_WARM_SAMPLER_FAULT" or
                fault_result["fault"]["reason"] != "transaction"):
            raise ValueError("terminal fault status")
        fault_not_terminal = Path(temp) / "fault-not-terminal.log"
        fault_not_terminal.write_text("".join(metadata_lines()[:10]) + fault +
                                      "[r12] armed candidate=bad schema=v2 ring=65536 popup_commands=0 production_enabled=0\r\n",
                                      encoding="ascii", newline="")
        _expect_reject("fault_not_terminal", lambda: parse_log(fault_not_terminal, 2, 1, True), results)
        late_path = Path(temp) / "late-loop.log"
        late_path.write_text("".join(metadata_lines()) +
                             "".join(render_record(i, "q") for i in range(1, 17)) +
                             render_record(100, "i") + render_record(101, "i"),
                             encoding="ascii", newline="")
        late = parse_log(late_path, 2, 0, True)
        malformed = Path(temp) / "malformed.log"
        malformed.write_text(combined.replace("[r12] start ", "[r12] malformed ", 1), encoding="ascii", newline="")
        _expect_reject("malformed_r12_metadata", lambda: parse_log(malformed, 2, 0, True), results)
        lf_only = Path(temp) / "lf.log"
        lf_only.write_bytes(combined.replace("\r\n", "\n").encode("ascii"))
        _expect_reject("lf_only", lambda: parse_log(lf_only, 2, 0, True), results)
    return {
        "status": "PASS_SELFTEST" if all(results.values()) else "FAIL_SELFTEST",
        "hardware_contact": 0, "accept_480": True, "reject_481": results["reject_481"],
        "maximum_record_bytes": max(len(render_record(i, "q").encode("ascii")) for i in (1, 16, 0xFFFFFFFF)),
        "maximum_metadata_bytes": max(len(line.encode("ascii")) for line in metadata_lines()),
        "negative_cases": results, "negative_cases_rejected": all(results.values()),
        "unrelated_lines_ignored": parsed["ignored_unrelated_lines"] == 2,
        "arbitrary_contiguous_loop_start_accepted": late["loop_sequence_start"] == 100,
        "metadata_proof": parsed["metadata_proof"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate-loop-line")
    ap.add_argument("--sequence-key")
    ap.add_argument("--sequence", type=int)
    ap.add_argument("--previous", type=int)
    ap.add_argument("--current", type=int)
    ap.add_argument("--log")
    ap.add_argument("--loop-log")
    ap.add_argument("--minimum-loop-iterations", type=int, default=2)
    ap.add_argument("--hardware-contact", type=int, choices=(0, 1), default=0)
    ap.add_argument("--artifact")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    try:
        if args.self_test:
            result = self_test()
            print(json.dumps(result, sort_keys=True))
            return 0 if result["status"] == "PASS_SELFTEST" else 1
        if args.validate_loop_line:
            parse(args.validate_loop_line, args.sequence_key, args.sequence, args.previous, args.current)
            print("PASS_R12_VALIDATE_LOOP_LINE")
            return 0
        target = args.log or args.loop_log
        if not target:
            raise ValueError("--log or --loop-log is required")
        parsed = parse_log(Path(target), args.minimum_loop_iterations, args.hardware_contact,
                           require_metadata=not bool(args.loop_log))
        encoded = json.dumps(parsed, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
        if args.artifact and args.write:
            tmp = Path(str(args.artifact) + ".tmp")
            tmp.write_text(encoded, encoding="utf-8")
            tmp.replace(args.artifact)
        print(encoded, end="")
        return 0
    except Exception as exc:
        print(f"R12 parser reject: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
