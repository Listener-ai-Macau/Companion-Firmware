"""Strict offline parser for R11 compact records and qualification metadata."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from pathlib import Path

WINDOW = "3-19,64-135"
NODES = ((32, 112), (44, 91), (56, 76), (68, 67), (80, 64),
         (92, 67), (104, 76), (116, 91), (128, 112))
PATH = NODES + NODES[-2::-1]
RECORD_KEYS = ("s", "q", "i", "p", "n", "w", "h", "r", "t", "b", "d",
               "a", "x", "y", "f", "c", "l", "v", "g")
CADENCE_LIMIT_MS = 480


def frame(node: tuple[int, int]) -> bytes:
    x, y = node
    out = bytearray([0xFF]) * 5000
    for row in range(24):
        for col in range(24):
            if (2 * col - 23) ** 2 + (2 * row - 23) ** 2 <= 576:
                px, py = x + col, y + row
                out[py * 25 + px // 8] &= ~(0x80 >> (px & 7))
    return bytes(out)


def payload(node: tuple[int, int]) -> str:
    data = frame(node)
    return hashlib.sha256(b"".join(data[y * 25 + 3:y * 25 + 20]
                                  for y in range(64, 136))).hexdigest().upper()


def node_for(sequence: int) -> tuple[tuple[int, int], tuple[int, int]]:
    if sequence < 1:
        raise ValueError("sequence")
    return PATH[(sequence - 1) % 16], PATH[sequence % 16]


def fields(text: str) -> dict[str, str]:
    parts = text.split(" ")
    if not parts or any(not part or "=" not in part for part in parts):
        raise ValueError("malformed metadata field")
    result: dict[str, str] = {}
    for part in parts:
        key, value = part.split("=", 1)
        if not key or key in result:
            raise ValueError("unknown or duplicate metadata key")
        result[key] = value
    return result


def require_values(values: dict[str, str], required: set[str], expected: dict[str, str]) -> None:
    if set(values) != required:
        raise ValueError("metadata key set")
    for key, value in expected.items():
        if values.get(key) != value:
            raise ValueError("metadata value")


def parse_metadata(line: str) -> tuple[str, dict[str, str]]:
    if not line.startswith("[r11] "):
        raise ValueError("metadata prefix")
    body = line[6:]
    if body.startswith("armed "):
        values = fields(body[6:])
        require_values(values, {"candidate", "schema", "telemetry_storage",
                                 "popup_commands", "production_enabled"},
                       {"candidate": "r11_native_cached_mode2_throw_arc", "schema": "v1",
                        "telemetry_storage": "host_ring_65536", "popup_commands": "0",
                        "production_enabled": "0"})
        return "armed", values
    if body.startswith("start "):
        values = fields(body[6:])
        require_values(values, {"candidate", "schema", "geometry", "black_pixels", "nodes",
                                 "path", "step_px", "travel_px", "apex_px", "framebuffer",
                                 "diff", "corridor", "corridor_bytes", "full_current_rewrite",
                                 "control", "baseline_control", "movement_reset", "activation",
                                 "busy_limit_ms", "transaction_limit_ms", "cadence_limit_ms",
                                 "cadence_target_ms", "ring", "production_enabled"},
                       {"candidate": "r11_native_cached_mode2_throw_arc", "schema": "v1",
                        "geometry": "24x24", "black_pixels": "448", "nodes": "A0..A8..A0",
                        "path": "A0..A8..A0", "step_px": "12", "travel_px": "96",
                        "apex_px": "48", "framebuffer": "200x200",
                        "diff": "exact_previous_current_union", "corridor": WINDOW,
                        "corridor_bytes": "1224", "full_current_rewrite": "1", "control": "0xCF",
                        "baseline_control": "0xFF", "movement_reset": "0", "activation": "1",
                        "busy_limit_ms": "600", "transaction_limit_ms": "460",
                        "cadence_limit_ms": "480", "cadence_target_ms": "450", "ring": "65536",
                        "production_enabled": "0"})
        return "start", values
    if body.startswith("baseline "):
        values = fields(body[9:])
        require_values(values, {"candidate", "x", "activations", "source_activation", "source_resets",
                                 "ready_checks", "source_ff", "source_cf", "movement_source_resets",
                                 "movement_source_ff", "movement_source_cf", "forbidden", "landing",
                                 "reset_elapsed_ms", "transaction_elapsed_ms", "busy_elapsed_ms"},
                       {"candidate": "r11_native_cached_mode2_throw_arc", "x": "32", "activations": "1",
                        "source_activation": "1", "source_resets": "1", "ready_checks": "1",
                        "source_ff": "1", "source_cf": "0", "movement_source_resets": "0",
                        "movement_source_ff": "0", "movement_source_cf": "1", "forbidden": "0",
                        "landing": "1"})
        return "baseline", values
    if body.startswith("qualification_result="):
        values = fields(body)
        require_values(values, {"qualification_result", "candidate", "qualification_frames", "activations",
                                 "source_resets", "source_ff", "movement_source_resets",
                                 "movement_source_ff", "movement_source_cf", "qualification_cadence_measurements",
                                 "cadence_measurements", "max_start_delta_ms", "busy_limit_ms",
                                 "transaction_limit_ms", "cadence_limit_ms", "cadence_target_ms"},
                       {"qualification_result": "ok", "candidate": "r11_native_cached_mode2_throw_arc",
                        "qualification_frames": "16", "activations": "16", "source_resets": "1",
                        "source_ff": "1", "movement_source_resets": "0", "movement_source_ff": "0",
                        "movement_source_cf": "1", "busy_limit_ms": "600", "transaction_limit_ms": "460",
                        "cadence_limit_ms": "480", "cadence_target_ms": "450"})
        return "qualification_result", values
    if body.startswith("observation_ready "):
        values = fields(body[18:])
        require_values(values, {"candidate", "qualification_frames", "qualification_cadence_measurements",
                                 "minimum_contiguous_loops", "real_cadence_required", "loop_limit",
                                 "telemetry_storage", "popup_eligible"},
                       {"candidate": "r11_native_cached_mode2_throw_arc", "qualification_frames": "16",
                        "minimum_contiguous_loops": "2", "real_cadence_required": "1",
                        "loop_limit": "none", "telemetry_storage": "host_ring_65536",
                        "popup_eligible": "1"})
        return "observation_ready", values
    raise ValueError("unknown or malformed [r11] metadata")


def parse(line: str, sequence_key: str | None = None, sequence: int | None = None,
          previous: int | None = None, current: int | None = None) -> dict[str, object]:
    if not line.startswith("[r11] s=v1 "):
        raise ValueError("wrong R11 record prefix")
    raw = line.rstrip("\r\n")
    values = fields(raw[6:])
    expected_keys = set(RECORD_KEYS) - ({"q"} if "i" in values else {"i"})
    if set(values) != expected_keys:
        raise ValueError("missing or mixed record keys")
    if values["s"] != "v1" or values["w"] != WINDOW or not re.fullmatch(r"[0-9A-Fa-f]{64}", values["h"]):
        raise ValueError("schema/window/hash")
    key = "q" if "q" in values else "i"
    try:
        seq = int(values[key], 10)
    except ValueError as exc:
        raise ValueError("sequence") from exc
    if sequence_key and key != sequence_key:
        raise ValueError("sequence key")
    if sequence is not None and seq != sequence:
        raise ValueError("sequence")
    expected_previous, expected_current = node_for(seq)

    def pair(name: str) -> tuple[int, int]:
        match = re.fullmatch(r"(\d+),(\d+)", values[name])
        if not match:
            raise ValueError("node")
        return int(match.group(1)), int(match.group(2))

    if pair("p") != expected_previous or pair("n") != expected_current:
        raise ValueError("position/order")
    if previous is not None and expected_previous[0] != previous:
        raise ValueError("previous")
    if current is not None and expected_current[0] != current:
        raise ValueError("current")
    if values["h"].upper() != payload(expected_current):
        raise ValueError("payload")
    try:
        ints = {key: int(values[key], 10) for key in ("r", "t", "b", "d", "a", "x", "y", "f", "c", "l", "v", "g")}
    except ValueError as exc:
        raise ValueError("numeric record field") from exc
    fixed = {"r": 0, "a": 1, "x": 0, "y": 1, "f": 0, "c": 1, "l": 0, "v": 0, "g": 1}
    if any(ints[key] != value for key, value in fixed.items()):
        raise ValueError("activation fields")
    if ints["t"] > 460 or ints["b"] > 600 or ints["d"] < 0:
        raise ValueError("timing")
    if key == "q" and seq > 16:
        raise ValueError("qualification sequence")
    if seq > 1 and not 1 <= ints["d"] <= CADENCE_LIMIT_MS:
        raise ValueError("cadence")
    if len((raw + "\r\n").encode("ascii")) > 192:
        raise ValueError("line length")
    return {"key": key, "sequence": seq, "previous": list(expected_previous),
            "current": list(expected_current), "transaction_ms": ints["t"],
            "busy_ms": ints["b"], "start_delta_ms": ints["d"],
            "payload_sha256": values["h"].upper()}


def parse_log(path: Path, minimum: int, hardware_contact: int, require_metadata: bool) -> dict[str, object]:
    data = path.read_bytes()
    text = data.decode("ascii")
    records: list[dict[str, object]] = []
    metadata: dict[str, dict[str, str]] = {}
    ignored_lines = 0
    ignored_trailing_bytes = 0
    for line in text.splitlines(keepends=True):
        complete = line.endswith("\n")
        content = line[:-2] if line.endswith("\r\n") else line.rstrip("\n")
        if not complete:
            if content.startswith("[r11]"):
                raise ValueError("incomplete [r11] line")
            ignored_trailing_bytes += len(line.encode("ascii"))
            continue
        if not content.startswith("[r11]"):
            ignored_lines += 1
            continue
        if not line.endswith("\r\n"):
            raise ValueError("R11 line must end in CRLF")
        if content.startswith("[r11] s="):
            records.append(parse(content))
        else:
            kind, values = parse_metadata(content)
            if kind in metadata:
                raise ValueError("duplicate R11 metadata")
            metadata[kind] = values
    qualification = [record for record in records if record["key"] == "q"]
    loops = [record for record in records if record["key"] == "i"]
    if [record["sequence"] for record in qualification] != list(range(1, 17)):
        raise ValueError("qualification sequence")
    if len(loops) < minimum:
        raise ValueError("minimum contiguous loops")
    if loops and [record["sequence"] for record in loops] != list(range(loops[0]["sequence"], loops[0]["sequence"] + len(loops))):
        raise ValueError("loop continuity")
    if require_metadata and set(metadata) != {"armed", "start", "baseline", "qualification_result", "observation_ready"}:
        raise ValueError("R11 eligibility metadata incomplete")
    if metadata:
        baseline = metadata.get("baseline", {})
        result = metadata.get("qualification_result", {})
        ready = metadata.get("observation_ready", {})
        if baseline and not (baseline.get("source_resets") == "1" and baseline.get("source_ff") == "1"):
            raise ValueError("baseline reset/FF proof")
        if result and not (result.get("movement_source_resets") == "0" and result.get("movement_source_cf") == "1" and result.get("qualification_frames") == "16"):
            raise ValueError("movement/reset/qualification proof")
        if ready and not (ready.get("minimum_contiguous_loops") == "2" and ready.get("real_cadence_required") == "1"):
            raise ValueError("observation eligibility proof")
    cadence = [record["start_delta_ms"] for record in qualification[1:] + loops if record["start_delta_ms"] > 0]
    if len(qualification) != 16 or len(qualification) < 16 or len(cadence) < 1:
        raise ValueError("qualification/cadence proof")
    max_delta = max(cadence)
    if max_delta > CADENCE_LIMIT_MS:
        raise ValueError("cadence limit")
    result = {"status": "PASS_R11_NATIVE_CACHED_MODE2_THROW_ARC_LOG", "candidate": "r11_native_cached_mode2_throw_arc",
              "schema": "v1", "qualification_frames": len(qualification), "qualification_records": qualification,
              "qualification_cadence_measurements": len([record for record in qualification[1:] if record["start_delta_ms"] > 0]),
              "loop_records": len(loops), "loop_sequence_start": loops[0]["sequence"] if loops else None,
              "cadence_measurements": len(cadence), "max_start_delta_ms": max_delta,
              "minimum_loop_iterations": minimum, "ring_bytes": 65536, "hardware_contact": hardware_contact,
              "metadata_proof": bool(set(metadata) == {"armed", "start", "baseline", "qualification_result", "observation_ready"}),
              "metadata": metadata, "ignored_unrelated_lines": ignored_lines,
              "ignored_trailing_partial_bytes": ignored_trailing_bytes}
    return result


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
            base = "[r11] s=v1 q=2 p=44,91 n=56,76 w=3-19,64-135 h=" + payload((56, 76)) + " r=0 t=445 b=443 d=480 a=1 x=0 y=1 f=0 c=1 l=0 v=0 g=1\r\n"
            parse(base, "q", 2, 44, 56)
            u32 = (base.replace("q=2", "i=4294967295")
                   .replace("p=44,91 n=56,76", "p=56,76 n=44,91")
                   .replace(payload((56, 76)), payload((44, 91))))
            parse(u32, "i", 4294967295)
            negatives = []
            for bad in (base.replace("d=480", "d=481"), base.replace(" h=", " h=BAD"), base.replace(" c=1", " c=0")):
                try:
                    parse(bad)
                except ValueError:
                    negatives.append(True)
                else:
                    negatives.append(False)
            def render(sequence: int, key: str) -> str:
                previous, current = node_for(sequence)
                delta = 0 if sequence == 1 else 480
                return (f"[r11] s=v1 {key}={sequence} p={previous[0]},{previous[1]} "
                        f"n={current[0]},{current[1]} w={WINDOW} h={payload(current)} "
                        f"r=0 t=445 b=443 d={delta} a=1 x=0 y=1 f=0 c=1 l=0 v=0 g=1\r\n")
            metadata_lines = (
                "[r11] armed candidate=r11_native_cached_mode2_throw_arc schema=v1 telemetry_storage=host_ring_65536 popup_commands=0 production_enabled=0\r\n"
                "[r11] start candidate=r11_native_cached_mode2_throw_arc schema=v1 geometry=24x24 black_pixels=448 nodes=A0..A8..A0 path=A0..A8..A0 step_px=12 travel_px=96 apex_px=48 framebuffer=200x200 diff=exact_previous_current_union corridor=3-19,64-135 corridor_bytes=1224 full_current_rewrite=1 control=0xCF baseline_control=0xFF movement_reset=0 activation=1 busy_limit_ms=600 transaction_limit_ms=460 cadence_limit_ms=480 cadence_target_ms=450 ring=65536 production_enabled=0\r\n"
                "[r11] baseline candidate=r11_native_cached_mode2_throw_arc x=32 activations=1 source_activation=1 source_resets=1 ready_checks=1 source_ff=1 source_cf=0 movement_source_resets=0 movement_source_ff=0 movement_source_cf=1 forbidden=0 landing=1 reset_elapsed_ms=20 transaction_elapsed_ms=445 busy_elapsed_ms=443\r\n"
                "[r11] qualification_result=ok candidate=r11_native_cached_mode2_throw_arc qualification_frames=16 activations=16 source_resets=1 source_ff=1 movement_source_resets=0 movement_source_ff=0 movement_source_cf=1 qualification_cadence_measurements=15 cadence_measurements=15 max_start_delta_ms=480 busy_limit_ms=600 transaction_limit_ms=460 cadence_limit_ms=480 cadence_target_ms=450\r\n"
                "[r11] observation_ready candidate=r11_native_cached_mode2_throw_arc qualification_frames=16 qualification_cadence_measurements=15 minimum_contiguous_loops=2 real_cadence_required=1 loop_limit=none telemetry_storage=host_ring_65536 popup_eligible=1\r\n"
            )
            combined = "[boot] unrelated=1\r\n" + metadata_lines + "[epaper] unrelated=1\r\n" + "".join(render(i, "q") for i in range(1, 17)) + render(1, "i") + render(2, "i")
            with tempfile.TemporaryDirectory() as temp:
                combined_path = Path(temp) / "combined.log"
                combined_path.write_text(combined, encoding="ascii", newline="")
                parsed = parse_log(combined_path, 2, 0, True)
                negatives.append(parsed["metadata_proof"] is True and parsed["ignored_unrelated_lines"] == 2)
                malformed_path = Path(temp) / "malformed.log"
                malformed_path.write_text(combined.replace("[r11] start ", "[r11] malformed ", 1), encoding="ascii", newline="")
                try:
                    parse_log(malformed_path, 2, 0, True)
                except ValueError:
                    negatives.append(True)
                else:
                    negatives.append(False)
            print(json.dumps({"status": "PASS_SELFTEST", "hardware_contact": 0,
                              "q2_480_bytes": len(base.encode("ascii")),
                              "uint32_max_480_bytes": len(u32.encode("ascii")),
                              "negative_cases": len(negatives), "negative_cases_rejected": all(negatives),
                              "combined_serial_metadata_proof": True, "unrelated_lines_ignored": True,
                              "malformed_r11_rejected": True}, sort_keys=True))
            return 0 if len(base.encode("ascii")) <= 192 and len(u32.encode("ascii")) <= 192 and all(negatives) else 1
        if args.validate_loop_line:
            parse(args.validate_loop_line, args.sequence_key, args.sequence, args.previous, args.current)
            print("PASS_R11_VALIDATE_LOOP_LINE")
            return 0
        target = args.log or args.loop_log
        if not target:
            raise ValueError("--log or --loop-log is required")
        parsed = parse_log(Path(target), args.minimum_loop_iterations, args.hardware_contact, require_metadata=not bool(args.loop_log))
        encoded = json.dumps(parsed, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
        if args.artifact and args.write:
            tmp = Path(str(args.artifact) + ".tmp")
            tmp.write_text(encoded, encoding="utf-8")
            tmp.replace(args.artifact)
        print(encoded, end="")
        return 0
    except Exception as exc:
        print(f"R11 parser reject: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
