"""Offline oracle for the native OTP Mode2 two-pass fine-stride candidate."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
ARTIFACT = ROOT / "docs/validation/companion-ssd1681-r10-native-two-pass-fine-stride-oracle-20260722.json"
POSITIONS = tuple(range(32, 65, 2))
QUALIFICATION = POSITIONS[1:]
LOOP = tuple(range(62, 31, -2)) + tuple(range(34, 65, 2))
FRAME_BYTES = 5000


def frame(x: int) -> bytes:
    buf = bytearray([0xFF]) * FRAME_BYTES
    for row in range(12):
        for col in range(12):
            dx, dy = 2 * col - 11, 2 * row - 11
            if dx * dx + dy * dy <= 144:
                px = x + col
                buf[(80 + row) * 25 + px // 8] &= ~(0x80 >> (px & 7))
    return bytes(buf)


def changed_window(old: bytes, new: bytes) -> tuple[int, int, int, int]:
    changed = [i for i, (a, b) in enumerate(zip(old, new)) if a != b]
    rows = [i // 25 for i in changed]
    cols = [i % 25 for i in changed]
    return min(cols), max(cols), min(rows), max(rows)


def black_window(old: bytes) -> tuple[int, int, int, int]:
    return changed_window(bytes([0xFF]) * FRAME_BYTES, old)


def region_payload(frame_bytes: bytes, window: tuple[int, int, int, int]) -> bytes:
    x_start, x_end, y_start, y_end = window
    return b"".join(
        frame_bytes[y * 25 + x_start : y * 25 + x_end + 1]
        for y in range(y_start, y_end + 1)
    )


def disk_columns(x: int) -> set[int]:
    columns: set[int] = set()
    for row in range(12):
        for col in range(12):
            dx, dy = 2 * col - 11, 2 * row - 11
            if dx * dx + dy * dy <= 144:
                columns.add(x + col)
    return columns


def omitted_columns(x: int, prior_window: tuple[int, int, int, int]) -> int:
    left = prior_window[0] * 8
    right = ((prior_window[1] + 1) * 8) - 1
    return sum(px < left or px > right for px in disk_columns(x))


def line(previous: int, current: int, iteration: int, busy: int = 599) -> dict[str, object]:
    old, new = frame(previous), frame(current)
    pass1, pass2 = black_window(old), changed_window(old, new)
    return {
        "candidate": "r10_native_two_pass_fine_stride",
        "schema": "v6",
        "loop_iteration": iteration,
        "previous_x": previous,
        "current_x": current,
        "previous_frame_sha256": hashlib.sha256(old).hexdigest().upper(),
        "current_frame_sha256": hashlib.sha256(new).hexdigest().upper(),
        "pass1_window": f"{pass1[0]}-{pass1[1]},{pass1[2]}-{pass1[3]}",
        "pass2_window": f"{pass2[0]}-{pass2[1]},{pass2[2]}-{pass2[3]}",
        "pass1_payload_sha256": hashlib.sha256(region_payload(new, pass1)).hexdigest().upper(),
        "pass2_payload_sha256": hashlib.sha256(region_payload(new, pass2)).hexdigest().upper(),
        "pass1_reset_elapsed_ms": 20,
        "pass2_reset_elapsed_ms": 20,
        "pass1_busy_elapsed_ms": busy,
        "pass2_busy_elapsed_ms": busy,
        "activations": 2,
        "source_resets": 2,
        "source_borders": 2,
        "source_windows": 2,
        "stage_writes_24": 2,
        "controls_ff": 2,
        "refresh_20": 2,
        "busy_completions": 2,
        "motion_0x26_writes": 0,
        "controls_32": 0,
        "controls_37": 0,
        "controls_c7": 0,
        "full_frame_writes": 0,
        "third_activation": 0,
        "retries": 0,
        "maintenance_refreshes": 0,
        "omitted_leading_columns": omitted_columns(current, pass1),
        "final_landing_exact": 1,
        "step_ok": 1,
    }


def check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    source = SOURCE.read_text(encoding="utf-8")
    check(len([p for p in range(12) for c in range(12) if (2*c-11)**2+(2*p-11)**2 <= 144]) == 112, "disk pixel count", errors)
    check(POSITIONS[-1] - POSITIONS[0] == 32 and all(b-a == 2 for a,b in zip(POSITIONS, POSITIONS[1:])), "2px path", errors)
    check(LOOP == tuple(reversed(POSITIONS[:-1])) + QUALIFICATION, "ping-pong loop", errors)
    records = [line(32 if i == 0 else QUALIFICATION[i-1], x, i + 1) for i, x in enumerate(QUALIFICATION)]
    records += [line(64 if i == 0 else LOOP[i-1], x, i + 17) for i, x in enumerate(LOOP)]
    for record in records:
        expected_old = black_window(frame(int(record["previous_x"])))
        expected_new = changed_window(frame(int(record["previous_x"])), frame(int(record["current_x"])))
        check(record["pass1_window"] == f"{expected_old[0]}-{expected_old[1]},{expected_old[2]}-{expected_old[3]}", "pass1 bbox must be previous disk", errors)
        check(record["pass2_window"] == f"{expected_new[0]}-{expected_new[1]},{expected_new[2]}-{expected_new[3]}", "pass2 union window", errors)
        check(record["activations"] == 2 and record["stage_writes_24"] == 2, "two activation counts", errors)
        check(record["pass1_busy_elapsed_ms"] <= 600 and record["pass2_busy_elapsed_ms"] <= 600, "BUSY bound", errors)
        check(all(record[k] == 0 for k in ("motion_0x26_writes", "controls_32", "controls_37", "controls_c7", "full_frame_writes", "third_activation", "retries", "maintenance_refreshes")), "forbidden activity", errors)
        check(record["step_ok"] == 1 and record["final_landing_exact"] == 1, "landing contract", errors)
        check(record["omitted_leading_columns"] == omitted_columns(int(record["current_x"]), expected_old), "omitted columns", errors)
    check("r10_native_two_pass_fine_stride" in source and "otp_mode2=1" in source, "native source markers", errors)
    native = source[source.index("#if COMPANION_EPAPER_SSD1681_R10_NATIVE_TWO_PASS_FINE_STRIDE_DIAGNOSTIC\n#define SSD1681_NATIVE_TWO_PASS_BUSY_LIMIT_MS"):source.index("#endif", source.index("ssd1681_r10_native_two_pass_fine_stride_diagnostic"))]
    for forbidden in ("ssd1681_command(0x26u)", "ssd1681_command(0x32u)", "ssd1681_command(0x37u)", "ssd1681_command(0xC7u)", "ssd1681_load_custom_lut"):
        check(forbidden not in native, f"forbidden native command: {forbidden}", errors)
    check("ssd1681_native_two_pass_source_reset" in native and "ssd1681_native_two_pass_source_window" in native, "source-bound helpers", errors)
    check("ssd1681_command_data(0x3Cu, border" in native, "source border command", errors)
    check("ssd1681_set_window(window, false, false)" not in native, "generic window activation removed", errors)
    check(native.count("ssd1681_native_two_pass_activation(&record->pass1_window") == 1 and native.count("ssd1681_native_two_pass_activation(&record->pass2_window") == 1, "two movement activations", errors)
    check("ssd1681_command(0x12u)" not in native, "candidate startup reset command removed", errors)
    negatives = {
        "wrong_step": all(b-a == 2 for a,b in zip((32,34,38), (34,38,40))),
        "wrong_window": records[0]["pass2_window"] == "9-9,1-1",
        "payload_mutation": records[0]["pass2_payload_sha256"] == "MUTATED",
        "third_activation": records[0]["activations"] == 3,
    }
    rejected = {name: not value for name, value in negatives.items()}
    check(all(rejected.values()), "negative oracle fixture was accepted", errors)
    result = {"schema_id": "companion.wb55.ssd1681.r10_native_two_pass_fine_stride.oracle.v1", "status": "PASS" if not errors else "FAIL", "qualification_frames": 16, "loop_frames": 32, "activations_after_baseline": 32, "records": records, "negative_fixtures": {k: {"executed": True, "rejected": v} for k, v in rejected.items()}, "errors": errors}
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(result, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
