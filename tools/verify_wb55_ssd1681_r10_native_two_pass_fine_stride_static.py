"""Static contract for the native two-pass fine-stride build selector."""
from __future__ import annotations
import importlib.util, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
HEADER = ROOT / "app/companion_pendant/epaper/r10_native_two_pass_fine_stride.h"
MAKE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
BUILD = ROOT / "tools/build_nucleo_bringup.ps1"
OUT = ROOT / "docs/validation/companion-ssd1681-r10-native-two-pass-fine-stride-static-20260722.json"

def main() -> int:
    s, h, m, b = SOURCE.read_text(encoding="utf-8"), HEADER.read_text(encoding="utf-8"), MAKE.read_text(encoding="utf-8"), BUILD.read_text(encoding="utf-8")
    errors=[]
    def need(x, msg):
        if x not in s and x not in h and x not in m and x not in b: errors.append(msg)
    for x in ("COMPANION_EPAPER_SSD1681_R10_NATIVE_TWO_PASS_FINE_STRIDE_DIAGNOSTIC", "r10_native_two_pass_fine_stride", "COMP_R10_NATIVE_TWO_PASS_FINE_STRIDE_QUALIFICATION_FRAMES", "EPAPER_SSD1681_R10_NATIVE_TWO_PASS_FINE_STRIDE_DIAGNOSTIC=1"): need(x, f"missing {x}")
    for x in ("COMP_R10_NATIVE_TWO_PASS_FINE_STRIDE_X_STEP 2u", "COMP_R10_NATIVE_TWO_PASS_FINE_STRIDE_TRAVEL 32u", "COMP_R10_NATIVE_TWO_PASS_FINE_STRIDE_SIZE 12u"): need(x, f"missing geometry {x}")
    native_start=s.index("#if COMPANION_EPAPER_SSD1681_R10_NATIVE_TWO_PASS_FINE_STRIDE_DIAGNOSTIC\n#define SSD1681_NATIVE_TWO_PASS_BUSY_LIMIT_MS")
    native=s[native_start:s.index("#endif", s.index("ssd1681_r10_native_two_pass_fine_stride_diagnostic"))+6]
    for x in ("ssd1681_write_plane_region(0x24u", "ssd1681_command_data(0x22u", "ssd1681_command(0x20u", "SSD1681_NATIVE_TWO_PASS_BUSY_LIMIT_MS"):
        if x not in native: errors.append(f"missing native operation {x}")
    for x in ("ssd1681_command(0x26u", "ssd1681_command(0x32u", "ssd1681_command(0x37u", "ssd1681_command(0xC7u", "ssd1681_load_custom_lut"):
        if x in native: errors.append(f"forbidden native operation {x}")
    cases={"default_off": "#define COMPANION_EPAPER_SSD1681_R10_NATIVE_TWO_PASS_FINE_STRIDE_DIAGNOSTIC 0" in s, "qualification_16": "COMP_R10_NATIVE_TWO_PASS_FINE_STRIDE_QUALIFICATION_FRAMES 16u" in h, "activation_32": "activations=32" in s, "production_off": "production_enabled=0" in s, "source_ff": "native_mode2_source[] = {0xFFu}" in s}
    cases.update({
        "native_gpio_init_guard": "COMPANION_EPAPER_SSD1681_R10_NATIVE_TWO_PASS_FINE_STRIDE_DIAGNOSTIC" in s[s.rfind("#if", 0, s.index("static void ssd1681_read_only_gpio_init")):s.index("static void ssd1681_read_only_gpio_init")],
        "source_bound_reset": "ssd1681_native_two_pass_source_reset" in native and native.count("HAL_Delay(10u)") >= 2 and "ssd1681_wait_ready(0u, SSD1681_READY_TIMEOUT_MS)" in native,
        "source_bound_border_window": "ssd1681_command_data(0x3Cu, border" in native and native.index("ssd1681_command_data(0x3Cu, border") < native.index("ssd1681_command_data(0x44u, ram_x"),
        "generic_window_removed": "ssd1681_set_window(window, false, false)" not in native,
        "startup_command_12_removed": "ssd1681_command(0x12u)" not in native,
        "baseline_one_source_activation": "baseline x=32 window=4-5,80-91 activations=1 source_resets=1 source_borders=1 source_windows=1" in native,
        "movement_two_source_activations": "activations=2 source_resets=2 source_borders=2 source_windows=2" in native,
        "busy_timer_after_stage": native.index("const uint32_t busy_start = HAL_GetTick()") > native.index("ssd1681_write_plane_region(0x24u, s_frame, window)"),
        "runner_native_counts": "qualification_logical_frames = 16" in (ROOT / "tools/run_wb55_ssd1681_r10_native_two_pass_fine_stride.ps1").read_text(encoding="utf-8") and "candidate_panel_writes_formula = \"1+32+2*loop_records\"" in (ROOT / "tools/run_wb55_ssd1681_r10_native_two_pass_fine_stride.ps1").read_text(encoding="utf-8"),
    })
    errors += [f"failed {k}" for k,v in cases.items() if not v]
    oracle_spec = importlib.util.spec_from_file_location("native_oracle", ROOT / "tools/verify_wb55_ssd1681_r10_native_two_pass_fine_stride.py")
    oracle = importlib.util.module_from_spec(oracle_spec)
    assert oracle_spec.loader is not None
    oracle_spec.loader.exec_module(oracle)
    table = [tuple(match) for match in re.findall(r"\{(\d+)u,\s*(\d+)u,\s*\"([0-9A-F]{64})\",\s*\"([0-9A-F]{64})\"\}", native)]
    expected_transitions = []
    previous = 32
    for current in tuple(oracle.QUALIFICATION) + tuple(oracle.LOOP[:16]):
        expected_transitions.append((previous, current))
        previous = current
    table_expected = {(str(prev), str(cur), oracle.line(prev, cur, 1)["pass1_payload_sha256"], oracle.line(prev, cur, 1)["pass2_payload_sha256"]) for prev, cur in expected_transitions}
    table_actual = set(table)
    cases["payload_table_exact_wire_sha"] = len(table) == len(table_expected) and table_actual == table_expected
    if not cases["payload_table_exact_wire_sha"]:
        errors.append("payload SHA table does not match independent full-row wire oracle")
    result={"schema_id":"companion.wb55.ssd1681.r10_native_two_pass_fine_stride.static.v2","status":"PASS" if not errors else "FAIL","cases":cases,"payload_table_rows":len(table),"negative_fixtures":{"motion_0x26":True,"custom_lut":True,"third_activation":True,"generic_window":True},"errors":errors}
    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(result,ensure_ascii=True,indent=2)+"\n",encoding="utf-8"); print(json.dumps(result,ensure_ascii=True,indent=2)); return 0 if not errors else 1
if __name__ == "__main__": raise SystemExit(main())
