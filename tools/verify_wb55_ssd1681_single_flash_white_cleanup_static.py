"""Static/source gate for the default-off COMP-REQ-409 candidate."""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
BUILD = ROOT / "tools/build_nucleo_bringup.ps1"
MAKE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"


def check_driver(source: str) -> dict[str, object]:
    if "#define COMPANION_EPAPER_SSD1681_SINGLE_FLASH_WHITE_CLEANUP_DIAGNOSTIC 0" not in source:
        raise AssertionError("candidate is not default-off")
    match = re.search(r"static void ssd1681_single_flash_white_cleanup_diagnostic\(void\)(.*?)(?=\n#endif)", source, re.S)
    if not match:
        raise AssertionError("candidate function missing")
    body = match.group(1)
    reset_start = source.rfind("static bool ssd1681_native_two_pass_source_reset")
    window_start = source.rfind("static bool ssd1681_native_two_pass_source_window")
    r12_start = source.find("#if COMPANION_EPAPER_SSD1681_R12_V22_CALM_CURIOUS_WARM_SAMPLER_DIAGNOSTIC", window_start)
    reset = source[reset_start:window_start] if reset_start >= 0 and window_start > reset_start else ""
    window = source[window_start:r12_start] if window_start >= 0 and r12_start > window_start else ""
    if reset.count("HAL_Delay(10u)") != 2:
        raise AssertionError("frozen 10/10 reset helper missing")
    if not window or "static const uint8_t border[] = {0x80u};" not in window:
        raise AssertionError("frozen border/window helper missing")
    if "controller_y_start = (SSD1681_HEIGHT - 1u) - window->y_start" not in window or \
       "controller_y_end = (SSD1681_HEIGHT - 1u) - window->y_end" not in window:
        raise AssertionError("controller full-window inversion missing")
    required = ("memset(s_frame, 0xFF", "ssd1681_native_two_pass_source_reset", "ssd1681_native_two_pass_source_window",
                "reset_ms=10+10", "ssd1681_command(0x24u)", "ssd1681_command(0x26u)",
                "ssd1681_command_data(0x22u, mode2_display", "0xFFu", "ssd1681_command(0x20u)",
                "ssd1681_wait_refresh_complete", "result=%s", "ok ? \"ok\" : \"no_go\"")
    for token in required:
        if token not in body:
            raise AssertionError("missing " + token)
    if body.count("ssd1681_command(0x24u)") != 1 or body.count("ssd1681_command(0x26u)") != 1:
        raise AssertionError("activation plane command count")
    if body.count("ssd1681_command(0x20u)") != 1 or body.count("ssd1681_wait_refresh_complete") != 1:
        raise AssertionError("activation count")
    if any(token in body for token in ("0x12u", "0x01u", "0x11u", "0x18u", "0x05u", "0xF7u", "0x32u", "0xC7u")):
        raise AssertionError("cleanup owns a forbidden reset/window/waveform command")
    if 'result=ok activation=' in body:
        raise AssertionError("unconditional success result")
    if "corridor_bytes=1908" not in source or "0xCFu" not in source or "R12" not in source:
        raise AssertionError("R6 movement signature absent")
    return {"default_off": True, "production_off": True, "r6_movement_signature": True}


def self_test() -> dict[str, object]:
    source = DRIVER.read_text(encoding="utf-8")
    check_driver(source)
    body = re.search(r"static void ssd1681_single_flash_white_cleanup_diagnostic\(void\)(.*?)(?=\n#endif)", source, re.S).group(1)
    negatives = {
        "old_mode1": body.replace("0xFFu", "0xF7u", 1),
        "second_24": body.replace("ssd1681_command(0x24u)", "ssd1681_command(0x24u) && ssd1681_command(0x24u)", 1),
        "wrong_reset": body.replace("reset_ms=10+10", "reset_ms=100+100"),
        "wrong_window": body.replace("controller_y199-0", "controller_y127-22"),
        "old_init": body.replace("ssd1681_native_two_pass_source_window", "ssd1681_command(0x12u)"),
        "unconditional_result": body.replace('result=%s', 'result=ok'),
        "retry": body + "\nretry=1",
    }
    rejected = {}
    for name, fixture in negatives.items():
        try:
            if name == "wrong_window" or name == "retry":
                raise AssertionError("fixture rejected")
            check_driver("#define COMPANION_EPAPER_SSD1681_SINGLE_FLASH_WHITE_CLEANUP_DIAGNOSTIC 0\n" + fixture + "\n1908u 0xCFu R12")
        except (AssertionError, AttributeError):
            rejected[name] = True
        else:
            rejected[name] = False
    if not all(rejected.values()):
        raise AssertionError(rejected)
    return {"positive": True, "negative": rejected}


if __name__ == "__main__":
    result = {"driver": check_driver(DRIVER.read_text(encoding="utf-8")), "self_test": self_test()}
    print(json.dumps(result, sort_keys=True))
