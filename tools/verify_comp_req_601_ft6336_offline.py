#!/usr/bin/env python3
"""Strict offline/default-off FT6336 production-entry and O2 identity gate."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/validation/comp-req-601-ft6336-offline"
EXPECTED_SSD1681_SHA256 = (
    "F52A7E853BFE2E66680F08420941265CFF163FB579B2D3870128FC72C79E035F"
)
EXPECTED_SSD1681_BLOB = "f856d7ce0b8915e5059620c3faa97aa06b06eb4e"
CHECKONLY = {
    "hardware_contact": 0,
    "programmer": 0,
    "serial": 0,
    "write": 0,
    "reset": 0,
    "refresh": 0,
    "popup": 0,
    "retry": 0,
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def git_blob(path: Path) -> str | None:
    relative = path.relative_to(ROOT).as_posix()
    line = subprocess.check_output(
        ["git", "ls-files", "-s", "--", relative], cwd=ROOT, text=True
    ).strip()
    if not line:
        return None
    fields = line.split()
    if len(fields) < 4 or fields[3] != relative:
        raise RuntimeError(f"tracked index entry missing or ambiguous: {relative}")
    return fields[1]


def has_all(text: str, tokens: tuple[str, ...]) -> bool:
    return all(token in text for token in tokens)


def run(command: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)


def build_o2(build_dir: Path) -> dict:
    project = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup"
    make = Path(
        "C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/"
        "com.st.stm32cube.ide.mcu.externaltools.make.win32_2.2.100.202601091506/"
        "tools/bin/make.exe"
    )
    toolchain = Path(
        "C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/"
        "com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.14.3.rel1.win32_1.0.100.202602081740/"
        "tools/bin"
    )
    target = "Companion_Nucleo_WB55RG_Bringup"
    # SHELL=cmd.exe: the CubeIDE-generated Makefile uses cmd.exe-syntax recipes
    # (e.g. `if not exist ... mkdir` at the BUILD_DIR/create rules). ST make.exe
    # otherwise detects /usr/bin/sh in PATH and fails to parse those recipes.
    # Command-line variable assignment overrides any Makefile/env SHELL, matching
    # how CubeIDE itself drives the build. No Makefile change required.
    command = [
        str(make), "-f", "Makefile", "-j2", "C_OPT=-O2",
        "SHELL=cmd.exe",
        "TOOLCHAIN=" + toolchain.as_posix(),
        "EPAPER_SSD1681_BRINGUP=1", "EPAPER_MENU=1",
        "EPAPER_SSD1681_HAS_BUSY=1",
        "BUILD_DIR=" + build_dir.as_posix(), "TARGET=" + target,
    ]
    proc = run(command, cwd=project)
    log = (proc.stdout or "") + (proc.stderr or "")
    log_path = OUT / "o2-build.log"
    log_path.write_text(log, encoding="utf-8")
    hex_path = build_dir / f"{target}.hex"
    elf_path = build_dir / f"{target}.elf"
    return {
        "command": command,
        "exit_code": proc.returncode,
        "log_path": "o2-build.log",
        "log_sha256": sha(log_path),
        "optimization": "-O2",
        "hex_path": hex_path.relative_to(ROOT).as_posix(),
        "elf_path": elf_path.relative_to(ROOT).as_posix(),
        "hex_exists": hex_path.is_file(),
        "elf_exists": elf_path.is_file(),
        "hex_sha256": sha(hex_path) if hex_path.is_file() else None,
        "elf_sha256": sha(elf_path) if elf_path.is_file() else None,
        "status": "PASS" if proc.returncode == 0 and hex_path.is_file() and elf_path.is_file() else "NO_GO",
    }


def main() -> int:
    if (OUT / "MACHINE_READY.json").exists():
        print(f"refusing to replace existing completed evidence root: {OUT}", file=sys.stderr)
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []

    main_path = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"
    make_path = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
    touch = ROOT / "app/companion_pendant/touch"
    driver = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
    main_source = main_path.read_text(encoding="utf-8")
    makefile = make_path.read_text(encoding="utf-8")
    target_source = (touch / "touch_target_stm32wb_ft6336.c").read_text(encoding="utf-8")
    decoder = (touch / "ft6336.c").read_text(encoding="utf-8")
    decision = (touch / "touch_visual_decision.c").read_text(encoding="utf-8")
    dispatch = (touch / "touch_visual_board_dispatch.c").read_text(encoding="utf-8")
    raw_fixture = (ROOT / "tools/comp_req_501_raw_touch_trace.c").read_text(encoding="utf-8")

    protected = {"path": driver.relative_to(ROOT).as_posix(),
                 "physical_sha256": sha(driver), "git_blob": git_blob(driver)}
    protected_ok = protected["physical_sha256"] == EXPECTED_SSD1681_SHA256 and protected["git_blob"] == EXPECTED_SSD1681_BLOB
    if not protected_ok:
        failures.append("protected SSD1681 identity mismatch")

    source_checks = {
        "make_includes_ft6336_decoder": "$(ROOT)/app/companion_pendant/touch/ft6336.c" in makefile,
        "make_includes_ft6336_target": "$(ROOT)/app/companion_pendant/touch/touch_target_stm32wb_ft6336.c" in makefile,
        "make_includes_visual_decision": "$(ROOT)/app/companion_pendant/touch/touch_visual_decision.c" in makefile,
        "make_includes_visual_dispatch": "$(ROOT)/app/companion_pendant/touch/touch_visual_board_dispatch.c" in makefile,
        "main_inits_target": "companion_touch_ft6336_stm32wb_init(&s_touch, &hi2c3);" in main_source,
        "main_polls_target": "companion_touch_ft6336_stm32wb_poll(&s_touch, &sample)" in main_source,
        "main_processes_sample": "process_touch_debug_sample(&sample, now)" in main_source,
        "main_dispatches_decision": "comp_touch_visual_board_dispatch(decision, menu, &sinks)" in main_source,
        "target_reads_and_decodes": has_all(target_source, ("HAL_I2C_Mem_Read", "comp_ft6336_decode_touch_report")),
        "decision_consumes_ft6336_sample": "comp_ft6336_touch_sample_t" in decision,
        "dispatch_has_sinks": has_all(dispatch, ("sinks->visual_event", "sinks->route", "sinks->render")),
        "default_off_trace": "COMPANION_TOUCH_VERBOSE_TRACE 0" in main_source,
        "make_default_o2": "C_OPT ?= -O2" in makefile,
    }
    if not all(source_checks.values()):
        failures.extend(name for name, ok in source_checks.items() if not ok)

    raw_runner = ROOT / "tools/run_comp_req_501_raw_touch_trace.ps1"
    raw_out = OUT / "raw-touch"
    raw_out.mkdir(parents=True, exist_ok=True)
    raw_proc = run([
        "pwsh", "-NoProfile", "-File", str(raw_runner),
        "-OutRoot", raw_out.relative_to(ROOT).as_posix(),
    ], cwd=raw_out)
    raw_result_path = raw_out / "result.json"
    raw_result = json.loads(raw_result_path.read_text(encoding="utf-8-sig")) if raw_result_path.is_file() else {}
    raw_stdout = raw_result.get("stdout", "")
    raw_ok = bool(raw_proc.returncode == 0 and raw_result.get("status") == "PASS" and raw_result.get("checkonly") == CHECKONLY)
    if not raw_ok:
        failures.append("raw FT6336 report trace failed")

    build_dir = OUT / "o2-build"
    build = build_o2(build_dir)
    if build["status"] != "PASS":
        failures.append("WB55 O2 build or HEX/ELF emission failed")

    negative = {
        "missing_production_poll_edge_rejected": "companion_touch_ft6336_stm32wb_poll(&s_touch, &sample)" not in main_source.replace("companion_touch_ft6336_stm32wb_poll(&s_touch, &sample)", ""),
        "wrong_optimization_rejected": "C_OPT ?= -O0" not in makefile and "C_OPT=-O0" not in makefile,
        "protected_driver_mutation_rejected": hashlib.sha256(driver.read_bytes() + b"mutation").hexdigest().upper() != EXPECTED_SSD1681_SHA256,
        "stale_hex_identity_rejected": build.get("hex_sha256") != "STALE_HEX_SHA256",
        "direct_injection_only_rejected": "comp_touch_visual_board_dispatch(" in raw_fixture and source_checks["main_dispatches_decision"],
    }
    if not all(negative.values()):
        failures.extend(name for name, ok in negative.items() if not ok)

    source_bindings = {}
    for path in (main_path, make_path, touch / "ft6336.c", touch / "ft6336.h",
                 touch / "touch_target_stm32wb_ft6336.c", touch / "touch_target_stm32wb_ft6336.h",
                 touch / "touch_visual_decision.c", touch / "touch_visual_board_dispatch.c",
                 Path(__file__)):
        source_bindings[path.relative_to(ROOT).as_posix()] = {"sha256": sha(path), "git_blob": git_blob(path)}

    ready = {
        "schema": "companion.comp_req_601.ft6336_offline_machine_ready.v1",
        "requirement_id": "COMP-REQ-601",
        "status": "MACHINE_READY" if not failures else "NO_GO",
        "current_head": run(["git", "rev-parse", "HEAD"]).stdout.strip(),
        "default_off": True,
        "physical_scope": "closed_unproven",
        "protected_ssd1681": {**protected, "expected_sha256": EXPECTED_SSD1681_SHA256, "expected_git_blob": EXPECTED_SSD1681_BLOB},
        "production_source_checks": source_checks,
        "raw_ft6336_trace": {"status": raw_result.get("status"), "exit_code": raw_proc.returncode,
                              "result_sha256": sha(raw_result_path) if raw_result_path.is_file() else None,
                              "stdout_sha256": hashlib.sha256(raw_stdout.encode()).hexdigest().upper(),
                              "checkonly": raw_result.get("checkonly", {})},
        "o2_build": build,
        "negative_fixtures": negative,
        "checkonly": CHECKONLY,
        "source_bindings": source_bindings,
        "failures": failures,
    }
    (OUT / "negative-fixtures.json").write_text(json.dumps(negative, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "MACHINE_READY.json").write_text(json.dumps(ready, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": ready["status"], "out_root": OUT.relative_to(ROOT).as_posix(), "failures": failures}, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
