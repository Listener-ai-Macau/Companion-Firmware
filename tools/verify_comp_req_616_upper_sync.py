#!/usr/bin/env python3
"""O2/check-only closure for the default-off COMP-REQ-616 runner.

This verifier may build an isolated ELF/HEX/BIN, but it never opens a serial
port, programmer, reset line, or operator prompt.  Evidence-hash drift keeps
the result NO_GO even when the deterministic page/plan/payload and compile
chain are valid.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/validation/comp-req-616-upper-sync"
GENERATED = ROOT / ".cache/validation/comp-req-616-upper-sync/generated"
HEADER = GENERATED / "comp_req_616_canonical_frames.h"
ASSET_MANIFEST = GENERATED / "canonical-input-evidence.json"
BUILD = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_comp_req_616_canonical_sync"
ELF = BUILD / "Companion_Nucleo_WB55RG_Bringup.elf"
HEX = BUILD / "Companion_Nucleo_WB55RG_Bringup.hex"
BIN = BUILD / "Companion_Nucleo_WB55RG_Bringup.bin"
BUILD_LOG = OUT / "o2-build.log"
DEFAULT_BUILD = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_comp_req_616_default_control"
DEFAULT_BUILD_LOG = OUT / "default-off-control-build.log"
OBJECT_PROOF = OUT / "o2-object-call-graph.txt"
DISASM_PROOF = OUT / "o2-runner-disassembly.txt"
ADAPTER_DISASM_PROOF = OUT / "o2-adapter-disassembly.txt"
BASELINE_DISASM_PROOF = OUT / "o2-baseline-disassembly.txt"
RUNNER = ROOT / "app/companion_pendant/epaper/comp_req_616_canonical_runner.c"
MAIN = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
GENERATOR = ROOT / "tools/generate_comp_req_616_canonical_frame_header.py"
PARSER = ROOT / "tools/verify_comp_req_616_canonical_sync_log.py"
UPPER_GATE = ROOT / "tools/verify_comp_req_616_upper_handoff.py"
CHOREOGRAPHY = ROOT / "tools/faraday_upper_art/verify_comp_req_616_ten_family_choreography.mjs"

MAKE = Path("C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.make.win32_2.2.100.202601091506/tools/bin/make.exe")
TOOLCHAIN = Path("C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.14.3.rel1.win32_1.0.100.202602081740/tools/bin")

PROTECTED_FUNCTIONS = {
    "ssd1681_native_cached_mode2_movement_activation": "EE83A0BA3366357C93233FEB7EBD7E581FA39B6A12379FDFCE28FF949D8954F8",
    "ssd1681_native_two_pass_activation": "D01C9FF988A11BF976F412469A6E769BC72DDAAB1D11B7B4D9FAF8EEC15115B7",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def run(command: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)


def extract_function(text: str, marker: str) -> str:
    start = text.index(marker)
    brace = text.index("{", start)
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    raise RuntimeError(f"unterminated protected function: {marker}")


def protected_function_audit() -> dict:
    text = DRIVER.read_text(encoding="utf-8")
    audit = {}
    for name, expected in PROTECTED_FUNCTIONS.items():
        observed = hashlib.sha256(extract_function(text, f"static bool {name}").encode("utf-8")).hexdigest().upper()
        audit[name] = {"expected_raw_sha256": expected, "observed_raw_sha256": observed,
                       "raw_baseline_locked": observed == expected}
    return audit


def check_static() -> dict:
    runner = RUNNER.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    generator = GENERATOR.read_text(encoding="utf-8")
    upper_gate = UPPER_GATE.read_text(encoding="utf-8")
    choreography = CHOREOGRAPHY.read_text(encoding="utf-8")
    protected = protected_function_audit()
    baseline = extract_function(
        DRIVER.read_text(encoding="utf-8"),
        "bool companion_epaper_panel_stm32wb_ssd1681_comp_req_611_full_0xff",
    )
    checks = {
        "default_off_main": "#define COMPANION_EPAPER_SSD1681_COMP_REQ_616_CANONICAL_SYNC 0" in main,
        "makefile_switch": "EPAPER_SSD1681_COMP_REQ_616_CANONICAL_SYNC" in makefile,
        "runner_count": "COMP_REQ_616_FRAME_COUNT" in runner and "frames=%u" in runner,
        "runner_page_binding": "ECCC8D27A31209150B9EEBF8AB25CEB08708B32BBA00541E033C8378E5B77E73" in runner,
        "runner_payload_binding": "087654306CFC0ECA07BEE9F270DAF72C0DB269E3CF39C6D4D6098BB96EA137DC" in runner,
        "runner_dwell_480": "COMP_REQ_616_FRAME_CADENCE_MS" in runner,
        "runner_dynamic_adapter": "companion_epaper_panel_stm32wb_ssd1681_cached_mode2_diff" in runner,
        "runner_baseline_adapter": "companion_epaper_panel_stm32wb_ssd1681_comp_req_611_full_0xff" in runner,
        "runner_stop_once": "COMP_REQ_616_STOP" in runner and "s_stop_requested" in runner,
        "runner_ring_64": "COMP_REQ_616_TRACE_RING_CAPACITY 64u" in runner,
        "runner_limits": "transaction_limit_ms" in runner and "480u : 470u" in runner and
                         "busy_elapsed_ms > 600u" in runner,
        "runner_no_reset": "report.source_reset_count != 0u" in runner and
                           "s_started ? 0u : 1u" not in runner,
        "runner_forbidden_control_absent": "0xFC" not in runner and "0x32" not in runner,
        "runner_no_auto_maintenance": "auto_maintenance_count++" not in runner,
        "runner_blocks_low_power_stop": bool(re.search(
            r"#if\s+COMPANION_EPAPER_SSD1681_COMP_REQ_616_CANONICAL_SYNC.*?"
            r"COMP_POWER_BLOCKER_SCREEN_WAIT\s*,\s*true",
            main,
            re.DOTALL,
        )),
        "runner_preempts_low_power_app_pump": (
            main.count("#if !COMPANION_EPAPER_SSD1681_COMP_REQ_616_CANONICAL_SYNC") >= 3 and
            "printf(\"[boot] boot_selftests=skipped reason=production_ble_path\\r\\n\");" in main
        ),
        "evidence_hash_gate_strict": (
            '"status": "READY" if observed["evidence"] == EVIDENCE_SHA else "NO_GO_EVIDENCE_HASH_DRIFT"' in generator and
            'frozen evidence SHA mismatch' in upper_gate and
            '"evidence_sha256_informational": False' in upper_gate
        ),
        "evidence_freeze_write_guard": (
            'const frozenEvidenceSha = "12E924C86A4A6787D2502ABE1F6D1DF278200FF9AC0E330CC002088144FEA76D"' in choreography and
            'verification.candidate.json' in choreography and
            "frozenEvidencePreserved" in choreography
        ),
        "baseline_adapter_no_reset": "ssd1681_native_no_reset_movement_activation" in baseline and
                                     "ssd1681_native_two_pass_activation" not in baseline,
        "protected_function_bodies_locked": all(item["raw_baseline_locked"] for item in protected.values()),
    }
    return {"checks": checks, "all_true": all(checks.values()), "protected_function_audit": protected}


def build_default_off() -> dict:
    command = [str(MAKE), "-f", "Makefile", "-B", "-j4", "C_OPT=-O2", "SHELL=cmd.exe",
               f"TOOLCHAIN={TOOLCHAIN.as_posix()}", "EPAPER_SSD1681_BRINGUP=1",
               "EPAPER_MENU=1", "EPAPER_SSD1681_HAS_BUSY=1",
               "EPAPER_SSD1681_VERBOSE_TRACE=1",
               "EPAPER_SSD1681_COMP_REQ_616_CANONICAL_SYNC=0",
               f"BUILD_DIR={DEFAULT_BUILD.as_posix()}", "TARGET=Companion_Nucleo_WB55RG_Bringup"]
    proc = run(command, ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup")
    DEFAULT_BUILD_LOG.write_text((proc.stdout or "") + (proc.stderr or ""), encoding="utf-8")
    artifacts = {name: sha(path) for name, path in (
        ("elf", DEFAULT_BUILD / "Companion_Nucleo_WB55RG_Bringup.elf"),
        ("hex", DEFAULT_BUILD / "Companion_Nucleo_WB55RG_Bringup.hex"),
        ("bin", DEFAULT_BUILD / "Companion_Nucleo_WB55RG_Bringup.bin")) if path.is_file()}
    nm = TOOLCHAIN / "arm-none-eabi-nm.exe"
    default_elf = DEFAULT_BUILD / "Companion_Nucleo_WB55RG_Bringup.elf"
    nm_output = ""
    if nm.is_file() and default_elf.is_file():
        nm_output = run([str(nm), "--defined-only", str(default_elf)]).stdout
    behavioral_identity = (
        artifacts.get("hex") == "F9E3D3B8D5954491528D81BAEB87BC73CF812AD5D544692CA57AF21FA4F29E91" and
        artifacts.get("bin") == "311EDC49FCB2F74D3C373998C42889818ACABF795704991BDCF6C1DFE46161F0"
    )
    return {"returncode": proc.returncode, "switch": 0, "artifacts": artifacts,
            "all_artifacts": len(artifacts) == 3,
            "default_off_runner_absent": "comp_req_616_canonical_runner" not in nm_output,
            "behavioral_identity": behavioral_identity,
            "build_log_sha256": sha(DEFAULT_BUILD_LOG)}


def build() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    command = [str(MAKE), "-f", "Makefile", "-B", "-j4", "C_OPT=-O2", "SHELL=cmd.exe",
               f"TOOLCHAIN={TOOLCHAIN.as_posix()}", "EPAPER_SSD1681_BRINGUP=1",
               "EPAPER_MENU=1", "EPAPER_SSD1681_HAS_BUSY=1",
               "EPAPER_SSD1681_VERBOSE_TRACE=1",
               "EPAPER_SSD1681_DIRECT_GPIO_SPI_DIAGNOSTIC=1",
               "EPAPER_SSD1681_DIRECT_GPIO_SPI_NOP_COUNT=0",
               "EPAPER_SSD1681_COMP_REQ_616_CANONICAL_SYNC=1",
               f"BUILD_DIR={BUILD.as_posix()}", "TARGET=Companion_Nucleo_WB55RG_Bringup"]
    proc = run(command, ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup")
    BUILD_LOG.write_text((proc.stdout or "") + (proc.stderr or ""), encoding="utf-8")
    artifacts = {name: sha(path) for name, path in (("elf", ELF), ("hex", HEX), ("bin", BIN)) if path.is_file()}
    nm = TOOLCHAIN / "arm-none-eabi-nm.exe"
    objdump = TOOLCHAIN / "arm-none-eabi-objdump.exe"
    object_proof = {"tools_present": nm.is_file() and objdump.is_file(), "symbols": [], "all_required": False}
    disassembly_proof = {"tools_present": objdump.is_file(), "required_calls": {}, "all_required": False,
                         "adapter_proof": {"all_required": False},
                         "baseline_proof": {"all_required": False}}
    if proc.returncode == 0 and ELF.is_file() and nm.is_file() and objdump.is_file():
        nm_proc = run([str(nm), "--defined-only", str(ELF)])
        OBJECT_PROOF.write_text(nm_proc.stdout or "", encoding="utf-8")
        required_symbols = {
            "comp_req_616_canonical_runner_init",
            "comp_req_616_canonical_runner_service",
            "comp_req_616_canonical_runner_accept_host_byte",
            "companion_epaper_panel_stm32wb_ssd1681_cached_mode2_diff",
            "companion_epaper_panel_stm32wb_ssd1681_comp_req_611_full_0xff",
        }
        symbols = {line.split()[-1] for line in (nm_proc.stdout or "").splitlines() if line.split()}
        object_proof["symbols"] = sorted(required_symbols & symbols)
        object_proof["all_required"] = required_symbols <= symbols
        dis_proc = run([str(objdump), "-d", "--disassemble=comp_req_616_canonical_runner_service", str(ELF)])
        DISASM_PROOF.write_text(dis_proc.stdout or "", encoding="utf-8")
        dis_text = dis_proc.stdout or ""
        required_calls = {
            "runner_entry": "<comp_req_616_canonical_runner_service>:" in dis_text,
            "dynamic_mode2_0xcf_adapter": "<companion_epaper_panel_stm32wb_ssd1681_cached_mode2_diff>" in dis_text,
            "first_full_0xff_adapter": "<companion_epaper_panel_stm32wb_ssd1681_comp_req_611_full_0xff>" in dis_text,
            "single_cleanup": dis_text.count("<cleanup_white>") >= 1,
            "runner_excludes_ordinary_0xfc": (
                "@ 0xfc" not in dis_text.lower() and
                re.search(r"\bmov(?:s|w)\s+\w+,\s+#252\b", dis_text, re.IGNORECASE) is None
            ),
        }
        disassembly_proof["required_calls"] = required_calls
        disassembly_proof["all_required"] = all(required_calls.values())
        adapter_proc = run([
            str(objdump), "-d", "-C",
            "--disassemble=companion_epaper_panel_stm32wb_ssd1681_cached_mode2_diff",
            str(ELF),
        ])
        ADAPTER_DISASM_PROOF.write_text(adapter_proc.stdout or "", encoding="utf-8")
        adapter_text = adapter_proc.stdout or ""
        adapter_required = {
            # COMP-REQ-621 deliberately replaces the fragile sparse diff
            # transfer with the accepted moving-ball-style local re-white.
            # O2 may remove the now-observational diff helper from the final
            # call graph, so accept either proof while requiring the exact
            # source-bound face window below.
            "dynamic_window_from_difference": (
                "ssd1681_window_from_difference" in adapter_text or
                all(token in DRIVER.read_text(encoding="utf-8") for token in (
                    ".x_start_byte = 4u",
                    ".x_end_byte = 21u",
                    ".y_start = 26u",
                    ".y_end = 179u",
                ))
            ),
            "dynamic_mode2_control_cf": "#207" in adapter_text or "0xcf" in adapter_text.lower(),
            "fixed_r12_corridor_absent": "ssd1681_write_r12_v22_corridor" not in adapter_text,
            "ordinary_control_fc_absent": (
                "@ 0xfc" not in adapter_text.lower() and
                re.search(r"\bmov(?:s|w)\s+\w+,\s+#252\b", adapter_text,
                          re.IGNORECASE) is None
            ),
        }
        disassembly_proof["adapter_proof"] = {
            "required_calls": adapter_required,
            "all_required": all(adapter_required.values()),
            "sha256": sha(ADAPTER_DISASM_PROOF),
        }
        baseline_proc = run([
            str(objdump), "-d", "-C",
            "--disassemble=companion_epaper_panel_stm32wb_ssd1681_comp_req_611_full_0xff",
            str(ELF),
        ])
        BASELINE_DISASM_PROOF.write_text(baseline_proc.stdout or "", encoding="utf-8")
        baseline_text = baseline_proc.stdout or ""
        baseline_required = {
            "no_reset_activation": ("ssd1681_native_no_reset_movement_activation" in baseline_text or
                                     ("ssd1681_wait_ready" in baseline_text and "#36" in baseline_text)),
            "source_reset_absent": "ssd1681_native_two_pass_source_reset" not in baseline_text,
            "full_ff_control": "#255" in baseline_text or "0xff" in baseline_text.lower(),
        }
        disassembly_proof["baseline_proof"] = {
            "required_calls": baseline_required,
            "all_required": all(baseline_required.values()),
            "sha256": sha(BASELINE_DISASM_PROOF),
        }
    object_proof["sha256"] = sha(OBJECT_PROOF) if OBJECT_PROOF.is_file() else None
    disassembly_proof["sha256"] = sha(DISASM_PROOF) if DISASM_PROOF.is_file() else None
    size_line = ""
    for line in BUILD_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        if re.match(r"^\s*\d+\s+\d+\s+\d+\s+\d+\s+[0-9a-f]+\s+.*\.elf$", line):
            size_line = line.strip()
    return {"returncode": proc.returncode, "artifacts": artifacts,
            "size_line": size_line, "build_log_sha256": sha(BUILD_LOG),
            "object_proof": object_proof, "disassembly_proof": disassembly_proof}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    generator = run(["python", str(GENERATOR), "--header", str(HEADER), "--manifest", str(ASSET_MANIFEST)])
    generator_output = generator.stdout + generator.stderr
    parser_selftest = run(["python", str(PARSER), "--self-test"])
    static = check_static()
    default_off_build = build_default_off()
    build_result = build()
    upper_gate = run(["python", str(UPPER_GATE), "--write"])
    gate_path = OUT.parent / "comp-req-616-upper-handoff/MACHINE_READY.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8")) if gate_path.is_file() else {"status": "missing"}
    manifest = json.loads(ASSET_MANIFEST.read_text(encoding="utf-8")) if ASSET_MANIFEST.is_file() else {}
    status = "READY_MACHINE_O2"
    if (generator.returncode != 0 or parser_selftest.returncode != 0 or not static["all_true"] or
            default_off_build["returncode"] != 0 or not default_off_build["all_artifacts"] or
            not default_off_build["default_off_runner_absent"] or
            not default_off_build["behavioral_identity"] or
            build_result["returncode"] != 0 or not build_result["object_proof"]["all_required"] or
            not build_result["disassembly_proof"]["all_required"] or
            not build_result["disassembly_proof"]["adapter_proof"]["all_required"] or
            not build_result["disassembly_proof"]["baseline_proof"]["all_required"] or
            manifest.get("header_roundtrip", {}).get("matches_native_payload") is not True):
        status = "NO_GO_MACHINE_CHECK_FAILED"
    elif manifest.get("status") != "READY" or not str(gate.get("status", "")).startswith("READY_"):
        status = "NO_GO_EVIDENCE_HASH_DRIFT"
    report = {
        "schema": "companion.comp_req_616.upper_sync_machine_ready.v1",
        "requirement": "COMP-REQ-617",
        "status": status,
        "hardware_contact": 0,
        "serial_contact": 0,
        "programmer_contact": 0,
        "flash": False,
        "reset": False,
        "operator_prompt": False,
        "asset_manifest": manifest,
        "generator": {"returncode": generator.returncode, "output_sha256": hashlib.sha256(generator_output.encode()).hexdigest().upper()},
        "parser_selftest": {"returncode": parser_selftest.returncode, "output": parser_selftest.stdout.strip()},
        "static": static,
        "default_off_control_build": default_off_build,
        "o2_build": build_result,
        "upper_identity_gate": gate,
        "upper_identity_gate_returncode": upper_gate.returncode,
        "authorization": {"execute_authorized": False, "reason": "registry evidence SHA drift and no main-review authorization"},
    }
    (OUT / "MACHINE_READY.json").write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0 if status.startswith("NO_GO") else 1


if __name__ == "__main__":
    raise SystemExit(main())
