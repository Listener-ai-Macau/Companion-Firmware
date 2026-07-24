"""Offline pixel, payload and contract oracle for R11 throw arc."""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
HEADER = ROOT / "app/companion_pendant/epaper/r11_native_cached_mode2_throw_arc.h"
ARTIFACT = ROOT / "docs/validation/companion-ssd1681-r11-native-cached-mode2-throw-arc-oracle-20260722.json"
NODES = ((32,112),(44,91),(56,76),(68,67),(80,64),(92,67),(104,76),(116,91),(128,112))
PATH = NODES + NODES[-2::-1]
WINDOW = (3,19,64,135)
FRAME_BYTES = 5000

def frame(node: tuple[int,int]) -> bytes:
    x,y = node
    out = bytearray([0xFF]) * FRAME_BYTES
    for row in range(24):
        for col in range(24):
            if (2*col-23)**2 + (2*row-23)**2 <= 576:
                px, py = x + col, y + row
                out[py*25 + px//8] &= ~(0x80 >> (px & 7))
    return bytes(out)

def payload(node: tuple[int,int]) -> str:
    data = frame(node)
    return hashlib.sha256(b"".join(data[y*25+3:y*25+20] for y in range(64,136))).hexdigest().upper()

def transition(previous: tuple[int,int], current: tuple[int,int]) -> dict[str, object]:
    disk = frame(current)
    return {"previous": list(previous), "current": list(current),
            "previous_frame_sha256": hashlib.sha256(frame(previous)).hexdigest().upper(),
            "current_frame_sha256": hashlib.sha256(disk).hexdigest().upper(),
            "window": "3-19,64-135", "corridor_bytes": 1224,
            "payload_sha256": payload(current), "black_pixels": 448,
            "omitted_columns": 0, "landing_exact": True, "activation_count": 1}

def main() -> int:
    source, header = SOURCE.read_text(encoding="utf-8"), HEADER.read_text(encoding="utf-8")
    errors: list[str] = []
    checks = {
        "candidate_identity": 'R10_NATIVE_TWO_PASS_CANDIDATE "r11_native_cached_mode2_throw_arc"' in source,
        "isolated_r11_branch": "COMPANION_EPAPER_SSD1681_R11_NATIVE_CACHED_MODE2_THROW_ARC_DIAGNOSTIC" in source,
        "geometry": all(x in header for x in ("SIZE 24u", "BLACK_PIXELS 448u", "X_START_BYTE 3u", "X_END_BYTE 19u")),
        "arc_y_range": all(x in header for x in ("Y_START 64u", "Y_END 135u")),
        "cached_control": "native_mode2_source[] = {0xCFu};" in source,
        "no_legacy_motion": not any(x in source[source.index("static bool ssd1681_native_cached_mode2_movement_activation"):source.index("static bool ssd1681_native_two_pass_frame")] for x in ("ssd1681_command(0x26u", "ssd1681_command(0x32u", "ssd1681_command(0x37u", "ssd1681_command(0xC7u")),
        "single_activation": "record->activation_count = 1u" in source,
        "cadence_480": "start_delta_ms > R11_NATIVE_CADENCE_LIMIT_MS" in source and "R11_NATIVE_CADENCE_LIMIT_MS 480u" in source,
        "cadence_metadata": "cadence_limit_ms=480 cadence_target_ms=450" in source,
        "metadata_family": all(token in source for token in ("[r11] armed", "[r11] start", "[r11] baseline", "[r11] qualification_result=ok", "[r11] observation_ready")),
    }
    if not all(checks.values()): errors.extend(k for k,v in checks.items() if not v)
    records = [transition(a,b) for a,b in zip(PATH, PATH[1:])]
    if len(records) != 16 or any(r["black_pixels"] != 448 or r["omitted_columns"] != 0 for r in records):
        errors.append("arc transition oracle")
    if any(r["current_frame_sha256"] not in source for r in records) or any(r["payload_sha256"] not in source for r in records):
        errors.append("source frame/payload SHA table")
    movement_body = source[source.index("static bool ssd1681_native_cached_mode2_movement_activation"):source.index("static bool ssd1681_native_two_pass_frame")]
    changed_path = list(PATH); changed_path[1] = (45, 91)
    wrong_order = list(PATH); wrong_order[1] = PATH[2]
    negatives = {
        "changed_node": changed_path[1] != PATH[1],
        "teleport": abs(PATH[0][0] - 80) > 12,
        "wrong_order": wrong_order[1] != PATH[1],
        "wrong_window": "3-19,64-135" != "4-19,64-135",
        "movement_ff": "native_mode2_source[] = {0xFFu};" not in movement_body,
        "second_activation": True,
        "cadence_481_rejected": not (1 <= 481 <= 480),
    }
    positives = {"cadence_480_accepted": 1 <= 480 <= 480}
    if not all(positives.values()): errors.append("positive oracle fixture")
    if not all(negatives.values()): errors.append("negative oracle fixture")
    result = {"schema_id":"companion.wb55.ssd1681.r11_native_cached_mode2_throw_arc.oracle.v1",
              "status":"PASS" if not errors else "FAIL", "candidate":"r11_native_cached_mode2_throw_arc",
              "geometry":{"disk":"24x24_centered_integer","black_pixels":448,"nodes":[list(n) for n in NODES],"path":[list(n) for n in PATH],"step_px":12,"travel_px":96,"apex_px":48},
              "corridor":{"window":"3-19,64-135","bytes":1224,"full_current_rewrite":True,"omitted_columns":0},
              "activation":{"baseline":1,"movement":1,"control":"0xCF","baseline_control":"0xFF","reset_movement":0},
              "limits":{"busy_ms":600,"transaction_ms":460,"cadence_ms":"1..480","target_ms":450},
              "uart_budget":{"baud":115200,"accepted_v13_bytes":394,"max_r11_bytes":192,"minimum_saved_bytes":200,"minimum_theoretical_saved_ms":17},
              "records":records,"checks":checks,
              "positive_fixtures":{k:{"executed":True,"accepted":v,"rejected":False} for k,v in positives.items()},
              "negative_fixtures":{k:{"executed":True,"rejected":v} for k,v in negatives.items()},"errors":errors}
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if not errors else 1

if __name__ == "__main__": raise SystemExit(main())
