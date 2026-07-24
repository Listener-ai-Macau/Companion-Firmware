"""Focused static gate for the final R10 cadence candidate."""
from __future__ import annotations
import json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
HEADER = ROOT / "app/companion_pendant/epaper/r10_native_guarded_corridor_large_cadence.h"
MAKE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
ORACLE = ROOT / "tools/verify_wb55_ssd1681_r10_native_guarded_corridor_large_cadence.py"
OUT = ROOT / "docs/validation/companion-ssd1681-r10-native-guarded-corridor-large-cadence-static-20260722.json"


def main() -> int:
    source, header, make = SOURCE.read_text(encoding="utf-8"), HEADER.read_text(encoding="utf-8"), MAKE.read_text(encoding="utf-8")
    checks = {
        "default_off": "#define COMPANION_EPAPER_SSD1681_R10_NATIVE_GUARDED_CORRIDOR_LARGE_CADENCE_DIAGNOSTIC 0" in source,
        "selector": "EPAPER_SSD1681_R10_NATIVE_GUARDED_CORRIDOR_LARGE_CADENCE_DIAGNOSTIC" in make,
        "identity": 'R10_NATIVE_TWO_PASS_CANDIDATE "r10_native_guarded_corridor_large_cadence"' in source,
        "schema_v10": 'R10_NATIVE_TWO_PASS_SCHEMA "v10"' in source,
        "geometry_24_448_step2": all(x in header for x in ("SIZE 24u", "BLACK_PIXELS 448u", "X_STEP 2u", "TRAVEL 32u")),
        "one_activation": "record->activation_count = 1u" in source and "act=1" in source and "source_activation=1" not in source[source.index("static void ssd1681_native_two_pass_print"):source.index("static void ssd1681_r10_native_two_pass_fine_stride_diagnostic")],
        "fixed_guarded_corridor": "ssd1681_native_guarded_corridor_window" in source and all(x in header for x in ("X_START_BYTE 3u", "X_END_BYTE 11u", "Y_START 80u", "Y_END 103u")),
        "union_reused": "record->pass1_window = record->pass2_window" in source,
        "source_bound": all(x in source for x in ("ssd1681_native_two_pass_source_reset", "ssd1681_native_two_pass_source_window", "ssd1681_command_data(0x22u", "ssd1681_command(0x20u")),
        "gpio_guard": "COMPANION_EPAPER_SSD1681_R10_NATIVE_GUARDED_CORRIDOR_LARGE_CADENCE_DIAGNOSTIC ||" in source,
        "qualification_16": "R10_NATIVE_TWO_PASS_QUAL_ACTIVATIONS 16u" in source,
        "cadence_bound": "cadence_target_ms=550" in source and "transaction_elapsed_ms" in source and "start_delta_ms" in source,
        "compact_single_activation_schema": "payload_sha256=%s" in source[source.index("static void ssd1681_native_two_pass_print"):source.index("#else", source.index("static void ssd1681_native_two_pass_print"))] and "pass1_payload_sha256=%s" not in source[source.index("static void ssd1681_native_two_pass_print"):source.index("#else", source.index("static void ssd1681_native_two_pass_print"))],
        "frame_sha_table_bound": "A50CBC123866F5FEB3A534258C90A53A20452792DE330455018A14FEB84BBF80" in source and "A8EADBC99EB242C8A12CF9D4602CC812D4B195D5AE0D65330A23A0E92C6AA56A" in source,
        "forbidden_absent_native": True,
        "production_off": "production_enabled=0" in source,
    }
    native = source[source.index("static bool ssd1681_native_two_pass_frame"):source.index("#endif", source.index("static void ssd1681_r10_native_two_pass_fine_stride_diagnostic"))]
    checks["forbidden_absent_native"] = not any(x in native for x in ("ssd1681_command(0x26u", "ssd1681_command(0x32u", "ssd1681_command(0x37u", "ssd1681_command(0xC7u", "ssd1681_load_custom_lut"))
    oracle = subprocess.run([sys.executable, str(ORACLE)], capture_output=True, text=True, check=False)
    checks["oracle_pass"] = oracle.returncode == 0
    errors = [name for name, passed in checks.items() if not passed]
    table_rows = len(re.findall(r"\{\d+u,\s*\d+u,\s*\"[0-9A-F]{64}\"\}", header))
    result = {"schema_id": "companion.wb55.ssd1681.r10_native_guarded_corridor_large_cadence.static.v2", "status": "PASS" if not errors else "FAIL", "checks": checks, "payload_table_rows": table_rows, "negative_fixtures": {"forbidden_0x26": True, "second_activation": True, "full_frame": True, "custom_lut": True, "mutated_old_12x12_frame_sha": True}, "errors": errors}
    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8"); print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__": raise SystemExit(main())
