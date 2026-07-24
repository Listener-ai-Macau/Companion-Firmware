#!/usr/bin/env python3
"""Static/build gate for the SSD1681 controller-state read-only image."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
DECODER = ROOT / "app/companion_pendant/epaper/ssd1681_read_only_controller_state.c"
HEADER = ROOT / "app/companion_pendant/epaper/ssd1681_read_only_controller_state.h"
HOST_TEST = ROOT / "tools/test_ssd1681_read_only_controller_state.c"
PARSER = ROOT / "tools/verify_wb55_ssd1681_read_only_controller_state_log.py"
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
BUILDER = ROOT / "tools/build_nucleo_bringup.ps1"
RUNNER = ROOT / "tools/run_wb55_ssd1681_read_only_controller_state.ps1"
CAPTURE = ROOT / "tools/capture_nucleo_serial.ps1"
REGISTRY = ROOT / "docs/companion_product_requirements.md"
RESEARCH = ROOT / "docs/validation/companion-ssd1681-read-only-controller-state-research-source-hash-20260721.json"
OUT = ROOT / "docs/validation/companion-ssd1681-read-only-controller-state-static-20260721.json"
CANDIDATE_ELF = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_read_only_controller_state/Companion_Nucleo_WB55RG_Ssd1681ReadOnlyControllerState.elf"
CANDIDATE_HEX = CANDIDATE_ELF.with_suffix(".hex")
NORMAL_ELF = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build/Companion_Nucleo_WB55RG_Bringup.elf"
NORMAL_HEX = NORMAL_ELF.with_suffix(".hex")
EXPECTED_NORMAL_HEX_SHA256 = "E1997F29DCB8735899B4BC0B9012CF75025F3CA8D21250485BCC21E4C4691B46"
ARM_GCC = Path(r"C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.14.3.rel1.win32_1.0.100.202602081740\tools\bin\arm-none-eabi-gcc.exe")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def strings(path: Path) -> str:
    return path.read_bytes().decode("latin1", errors="ignore")


def main() -> int:
    failures: list[str] = []
    checks: dict[str, bool] = {}

    required = [DRIVER, DECODER, HEADER, HOST_TEST, PARSER, MAKEFILE, BUILDER, RUNNER, CAPTURE,
                REGISTRY, RESEARCH, CANDIDATE_ELF, CANDIDATE_HEX, NORMAL_ELF, NORMAL_HEX]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    checks["required_sources_and_images_exist"] = not missing
    failures.extend(f"missing: {item}" for item in missing)
    if missing:
        result = {"schema_id": "companion.wb55.ssd1681.read_only_controller_state_static.v1",
                  "status": "NO_GO_STATIC_READ_ONLY_CONTROLLER_STATE", "checks": checks,
                  "failures": failures}
        OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return 1

    driver = DRIVER.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    builder = BUILDER.read_text(encoding="utf-8")
    runner = RUNNER.read_text(encoding="utf-8")
    capture = CAPTURE.read_text(encoding="utf-8")
    registry = REGISTRY.read_text(encoding="utf-8")
    research = json.loads(RESEARCH.read_text(encoding="utf-8"))

    def require(name: str, condition: bool, detail: str) -> None:
        checks[name] = bool(condition)
        if not condition:
            failures.append(detail)

    require("registry_comp_req_257", "| COMP-REQ-257 |" in registry,
            "registry does not contain COMP-REQ-257")
    require("research_authorizes_only_read_capture",
            research.get("status") == "PASS_RESEARCH_AUTHORIZES_ONE_READ_ONLY_0X2F_0X2D_CAPTURE",
            "research status is not the exact read-only authorization")
    require("macro_default_off",
            "#define COMPANION_EPAPER_SSD1681_READ_ONLY_CONTROLLER_STATE_DIAGNOSTIC 0" in driver,
            "diagnostic macro is not default zero")
    require("early_return_before_normal_init",
            driver.index("#if COMPANION_EPAPER_SSD1681_READ_ONLY_CONTROLLER_STATE_DIAGNOSTIC\n    (void)expression_assets;") <
            driver.index("s_target_context.expression_assets = expression_assets;"),
            "read-only image does not return before normal panel initialization")

    start = driver.index("static void ssd1681_read_only_gpio_init")
    end = driver.index("#endif", driver.index("static void ssd1681_read_only_controller_state_diagnostic", start))
    diagnostic = driver[start:end]
    require("only_2f_and_2d_register_reads",
            diagnostic.count("ssd1681_read_only_register(0x2Fu") == 1 and
            diagnostic.count("ssd1681_read_only_register(0x2Du") == 1,
            "diagnostic does not contain exactly one loop call site for each 0x2F and 0x2D")
    forbidden_literals = ["0x20u", "0x22u", "0x24u", "0x26u", "0x30u", "0x31u",
                          "0x32u", "0x36u", "0x37u", "0x39u"]
    require("forbidden_commands_absent", not any(item in diagnostic for item in forbidden_literals),
            "read-only diagnostic contains a forbidden command literal")
    require("reset_absent", "RST_GPIO" not in diagnostic and "ssd1681_reset" not in diagnostic,
            "read-only diagnostic touches display reset")
    require("three_fixed_groups", "group < COMP_SSD1681_CONTROLLER_STATE_GROUPS" in diagnostic and
            "#define COMP_SSD1681_CONTROLLER_STATE_GROUPS 3u" in HEADER.read_text(encoding="utf-8"),
            "group count is not fixed at three")
    require("bounded_lengths", "COMP_SSD1681_DISPLAY_OPTION_BYTES" in diagnostic and
            "#define COMP_SSD1681_DISPLAY_OPTION_BYTES 11u" in HEADER.read_text(encoding="utf-8"),
            "0x2D response is not fixed at eleven bytes")
    require("gpio_restore_contract", all(token in diagnostic for token in (
                "ssd1681_read_only_sda_input", "ssd1681_read_only_restore_bus",
                "GPIO_PIN_RESET", "GPIO_PIN_SET", "ssd1681_read_only_bus_restored")),
            "bounded SDA input and restored bus contract is incomplete")
    require("build_profile_isolated", all(token in builder for token in (
                "EpaperSsd1681ReadOnlyControllerStateDiagnostic",
                "build_ssd1681_read_only_controller_state",
                "Companion_Nucleo_WB55RG_Ssd1681ReadOnlyControllerState",
                "allowedReadOnlyArguments")),
            "build wrapper lacks isolated read-only profile")
    require("make_profile_links_decoder", all(token in makefile for token in (
                "EPAPER_SSD1681_READ_ONLY_CONTROLLER_STATE_DIAGNOSTIC",
                "ssd1681_read_only_controller_state.c")),
            "Makefile does not bind the decoder only to the diagnostic profile")
    require("runner_hashes_before_hardware_and_restores_finally", all(token in runner for token in (
                "Normal restore image hash mismatch; refusing all hardware contact.",
                "Enter-CompanionWb55Lock",
                "serial_open_before_candidate_flash",
                "finally {",
                "normal_firmware_restored",
                "automatic_retries = 0")),
            "runner does not fail closed on images, lock, one boot, no retry, and finally restore")
    require("serial_ready_precedes_flash", "ReadySignalPath" in capture and
            runner.index("Test-Path -LiteralPath $readySignal") < runner.index("-ImagePath $candidateImage"),
            "runner does not wait for serial ready before candidate flash")

    parser_test = subprocess.run([sys.executable, str(PARSER), "--self-test"],
                                 cwd=ROOT, capture_output=True, text=True)
    require("host_parser_negative_matrix", parser_test.returncode == 0,
            f"parser host self-test failed: {parser_test.stderr.strip()}")
    syntax = subprocess.run([str(ARM_GCC), "-std=c11", "-Wall", "-Wextra", "-Werror",
                             "-I", str(HEADER.parent), "-fsyntax-only", str(DECODER), str(HOST_TEST)],
                            cwd=ROOT, capture_output=True, text=True)
    require("decoder_and_c_negative_test_compile_clean", syntax.returncode == 0,
            f"decoder/test compile failed: {syntax.stderr.strip()}")

    candidate_strings = strings(CANDIDATE_ELF)
    normal_strings = strings(NORMAL_ELF)
    require("candidate_contains_read_only_trace", "[epaper] readonly_state start" in candidate_strings,
            "candidate ELF lacks read-only trace marker")
    require("normal_excludes_read_only_trace", "[epaper] readonly_state start" not in normal_strings,
            "normal ELF contains read-only trace marker")
    normal_hash = sha(NORMAL_HEX)
    require("normal_restore_hash_exact", normal_hash == EXPECTED_NORMAL_HEX_SHA256,
            f"normal HEX hash is {normal_hash}, expected {EXPECTED_NORMAL_HEX_SHA256}")

    manifest = {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path) for path in required}
    result = {
        "schema_id": "companion.wb55.ssd1681.read_only_controller_state_static.v1",
        "status": "PASS_STATIC_READ_ONLY_CONTROLLER_STATE_DEFAULT_OFF" if not failures else "NO_GO_STATIC_READ_ONLY_CONTROLLER_STATE",
        "claim_scope": "default-off read-only controller-state evidence only; no display write, refresh, waveform, visual, temperature, or production claim",
        "checks": checks,
        "failures": failures,
        "images": {
            "candidate_hex_sha256": sha(CANDIDATE_HEX),
            "candidate_elf_sha256": sha(CANDIDATE_ELF),
            "normal_hex_sha256": normal_hash,
            "required_normal_hex_sha256": EXPECTED_NORMAL_HEX_SHA256,
        },
        "source_manifest": manifest,
        "host_test_stdout": parser_test.stdout.strip(),
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
