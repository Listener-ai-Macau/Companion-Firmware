#!/usr/bin/env python3
"""Static fail-closed gate for the production-off SSD1681 R9 diagnostic."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
BUILDER = ROOT / "tools/build_nucleo_bringup.ps1"
RUNNER = ROOT / "tools/run_wb55_ssd1681_custom_mode2_observable_r6_raw_restore.ps1"
LAUNCHER = ROOT / "tools/start_wb55_ssd1681_phase_parallel_r9.ps1"
LAUNCHER_VERIFIER = ROOT / "tools/verify_wb55_ssd1681_phase_parallel_r9_launcher.py"
PROMPT = ROOT / "tools/invoke_wb55_ssd1681_phase_parallel_r9_final_visual_prompt.ps1"
PARSER = ROOT / "tools/verify_wb55_ssd1681_phase_parallel_r9_log.py"
WORKBENCH_TOOL = ROOT / "tools/verify_wb55_ssd1681_phase_parallel_r9_workbench.py"
WORKBENCH = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-workbench-20260721.json"
LAUNCHER_STATIC = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-persistent-launcher-static-20260721.json"
DUAL_PARSER = ROOT / "tools/verify_wb55_ssd1681_dual_plane_white_clean_log.py"
RESTORE = ROOT / "tools/verify_wb55_raw_application_restore.py"
NORMAL = ROOT / "tools/verify_wb55_normal_resume_after_ur_backup_log.py"
REGISTRY = ROOT / "docs/companion_product_requirements.md"
OWNER = ROOT / "docs/validation/companion-pet-special-system-owner-acceptance-20260717.json"
V9 = ROOT / "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png"
R8_RUNTIME = ROOT / "docs/validation/companion-ssd1681-ram-command-target-r8-r2-runtime-20260721.json"
SUPPLIER = Path(r"C:\Users\Billy\Desktop\GDEH0154D67-20211203-P-LUT(1s) -1s快刷\EPD_W21\EPAPER.c")
BASELINE_A = ROOT / ".cache/validation/wb55-ur-dual-application-backup-execute-20260721-r1/private/backup-a.bin"
BASELINE_B = ROOT / ".cache/validation/wb55-ur-dual-application-backup-execute-20260721-r1/private/backup-b.bin"
BUILD = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_phase_parallel_r9"
R9_HEX = BUILD / "Companion_Nucleo_WB55RG_Ssd1681PhaseParallelR9.hex"
R9_ELF = R9_HEX.with_suffix(".elf")
DUAL_BUILD = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_dual_plane_white_clean"
DUAL_HEX = DUAL_BUILD / "Companion_Nucleo_WB55RG_Ssd1681DualPlaneWhiteClean.hex"
DUAL_ELF = DUAL_HEX.with_suffix(".elf")
OUT = ROOT / "docs/validation/companion-ssd1681-phase-parallel-r9-static-20260721.json"

LUT_SHA = "9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD"
WORKBENCH_SHA = "E7311523D6FE571434F0C1F2D5EC76B7ED9B64DC725B0726DDEC023421D7E4EF"
SUPPLIER_SHA = "7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896"
SUPPLIER_LUT_SHA = "F83EA7360CFFF04FE9D004A75858A46213CBD710AAA2F0C4A62597E3EA176D15"
R8_RUNTIME_SHA = "BAD97BBABFD2E1B515A2E1D1A45EE3C4E68EF3FFC167D03468E1859659C07FF5"
BASELINE_SHA = "223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C"
OWNER_SHA = "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"
V9_SHA = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
R9_HEX_SHA = "724DA17F385756BA779739E73DA47131F563E0C071A2EB173F5F77871F3CADDF"
R9_ELF_SHA = "777A1288A0E6FC83373602F9895B07AA08F31269AB68B7EB1699723583D03485"
DUAL_HEX_SHA = "3AC4E52E37E15DC3CC058A4B0B0E6A3227D23E6C6DEFAEDCB786C08497888AAD"
DUAL_ELF_SHA = "1AE76AB804D81E828A2B3AA700821CBD69AF79561CE72E612872F1FAC8550DB0"
RUNNER_SHA = "0B0A536E7B03DD5F2A4F9CF7B2B76A1B0DB3F34745172E352CB0B4726011B34B"
LAUNCHER_SHA = "7B5080DC29D45169A7CE513E88861840FCB24CBCB41A82675884FF9C72B4A124"
PROMPT_SHA = "56794D5856248E1D868DEF23DC9CE983F7069CF4C15A59308F2F011BC9164E15"
PARSER_SHA = "F13A58941390688EDB68B71C2148343E11C6569D128FF4D353E0DB76BC6844EC"
PHASES = "ABCD"
TRANSITIONS = (("BB", 0), ("BW", 1), ("WB", 2), ("WW", 3))
VOLTAGES = {0: ("VSS", 0), 1: ("VSH1", 15), 2: ("VSL", -15), 3: ("VSH2", 5)}


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def parse_supplier_lut(source: str) -> bytes:
    match = re.search(
        r"const\s+unsigned\s+char\s+LUT_DATA\[159\]\s*=\s*\{(.*?)\};",
        source,
        re.DOTALL,
    )
    if not match:
        return b""
    return bytes(int(value, 16) for value in re.findall(r"0x([0-9A-Fa-f]{1,2})", match.group(1)))


def parse_driver_lut(source: str) -> bytes:
    match = re.search(
        r"static const uint8_t ssd1681_phase_parallel_r9_lut\[159\]\s*=\s*\{(.*?)\};",
        source,
        re.DOTALL,
    )
    if not match:
        return b""
    return bytes(int(value, 16) for value in re.findall(r"0x([0-9A-Fa-f]{2})u?", match.group(1)))


def unpack_tables(values: bytes) -> list[list[int]]:
    tables: list[list[int]] = []
    for lut in range(5):
        fields: list[int] = []
        for packed in values[lut * 12 : (lut + 1) * 12]:
            fields.extend(((packed >> 6) & 3, (packed >> 4) & 3, (packed >> 2) & 3, packed & 3))
        tables.append(fields)
    return tables


def unpack_timing(values: bytes) -> list[dict[str, Any]]:
    result = []
    for group in range(12):
        base = 60 + group * 7
        result.append(
            {
                "tp": [values[base], values[base + 1], values[base + 3], values[base + 4]],
                "sr_ab": values[base + 2],
                "sr_cd": values[base + 5],
                "rp": values[base + 6],
            }
        )
    return result


def transition_oracle(values: bytes) -> dict[str, Any]:
    tables = unpack_tables(values)
    timing = unpack_timing(values)
    result: dict[str, Any] = {
        "shared_timing_frames": sum(sum(group["tp"]) for group in timing),
        "active_phases": [],
        "transitions": {},
    }
    for group, item in enumerate(timing):
        for phase, duration in enumerate(item["tp"]):
            if duration:
                result["active_phases"].append(
                    {
                        "slot": f"{group}{PHASES[phase]}",
                        "duration_frames": duration,
                        **{
                            name: {
                                "code": tables[lut][group * 4 + phase],
                                "voltage": VOLTAGES[tables[lut][group * 4 + phase]][0],
                            }
                            for name, lut in TRANSITIONS
                        },
                    }
                )
    for name, lut in TRANSITIONS:
        counts: Counter[str] = Counter()
        impulse = 0
        sequence = []
        for group, item in enumerate(timing):
            for phase, duration in enumerate(item["tp"]):
                if not duration:
                    continue
                code = tables[lut][group * 4 + phase]
                voltage, volts = VOLTAGES[code]
                counts[voltage] += duration
                impulse += volts * duration
                sequence.append(
                    {
                        "slot": f"{group}{PHASES[phase]}",
                        "code": code,
                        "voltage": voltage,
                        "duration_frames": duration,
                    }
                )
        result["transitions"][name] = {
            "effective_drive_frames": counts["VSH1"] + counts["VSL"] + counts["VSH2"],
            "positive_drive_frames": counts["VSH1"] + counts["VSH2"],
            "negative_drive_frames": counts["VSL"],
            "zero_drive_frames": counts["VSS"],
            "source_volt_frame_impulse": impulse,
            "sequence": sequence,
        }
    return result


def byte_field(index: int) -> str:
    if index < 60:
        return f"VS[LUT{index // 12}][group{index % 12}:A-D packed]"
    if index < 144:
        names = ("TP-A", "TP-B", "SR-AB", "TP-C", "TP-D", "SR-CD", "RP")
        return f"{names[(index - 60) % 7]}[group{(index - 60) // 7}]"
    names = {
        144: "FR[0]", 145: "FR[1]", 146: "FR[2]", 147: "FR[3]", 148: "FR[4]",
        149: "FR[5]", 150: "XON[0]", 151: "XON[1]", 152: "XON[2]", 153: "EOPT",
        154: "VGH", 155: "VSH1", 156: "VSH2", 157: "VSL", 158: "VCOM",
    }
    return names[index]


def modified_manifest(
    supplier: bytes, candidate: bytes, lineage: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    manifest = []
    for index, (source_value, candidate_value) in enumerate(zip(supplier, candidate)):
        if source_value == candidate_value:
            continue
        sources: list[str] = []
        derivation = "delete complete supplier fields to VSS/zero timing"
        if index < 60 and candidate_value:
            lut = index // 12
            group = index % 12
            label = "BW" if lut == 1 else "WB" if lut == 2 else None
            if label:
                sources = [
                    item[label]["source_field"]
                    for item in lineage
                    if int(item["destination"][0:-1]) == group
                ]
                derivation = "repack complete supplier VS fields into admitted destination phases"
        elif 60 <= index < 144 and candidate_value:
            group = (index - 60) // 7
            offset = (index - 60) % 7
            phase_by_offset = {0: "A", 1: "B", 3: "C", 4: "D"}
            phase = phase_by_offset.get(offset)
            sources = [
                item["duration"]["source_field"]
                for item in lineage
                if int(item["destination"][0:-1]) == group
                and item["destination"][-1] == phase
            ]
            derivation = "retain one complete supplier TP field; delete other timing fields"
        manifest.append(
            {
                "index": index,
                "field": byte_field(index),
                "supplier_hex": f"{source_value:02X}",
                "candidate_hex": f"{candidate_value:02X}",
                "derivation": derivation,
                "supplier_source_fields": sources,
            }
        )
    return manifest


def r9_body(source: str) -> str:
    start = source.find("static void ssd1681_phase_parallel_r9_diagnostic")
    end = source.find("\n}\n#endif", start)
    return "" if start < 0 or end < 0 else source[start : end + 2]


def driver_errors(source: str, expected_lut: bytes) -> list[str]:
    errors: list[str] = []
    values = parse_driver_lut(source)
    body = r9_body(source)
    loop_start = body.find("for (uint8_t step = 0u;")
    loop_end = body.find("const uint32_t observation_elapsed_ms", loop_start)
    loop = body[loop_start:loop_end] if loop_start >= 0 and loop_end >= 0 else ""
    expected_previous = "0u, 1u, 2u, 1u, 2u, 1u, 2u, 1u, 2u, 1u, 2u, 1u, 2u, 1u, 2u, 1u"
    expected_current = "1u, 2u, 1u, 2u, 1u, 2u, 1u, 2u, 1u, 2u, 1u, 2u, 1u, 2u, 1u, 0u"
    checks = {
        "lut_exact": len(values) == 159 and values == expected_lut and sha_bytes(values) == LUT_SHA,
        "tail_exact": values[153:159].hex().upper() == "221741A83258" if len(values) == 159 else False,
        "default_off": "#define COMPANION_EPAPER_SSD1681_PHASE_PARALLEL_R9_DIAGNOSTIC 0" in source,
        "software_spi_busy": "phase-parallel R9 diagnostic requires software SPI and BUSY" in source,
        "isolated_guard": "phase-parallel R9 diagnostic excludes every waveform/read diagnostic" in source,
        "constants": all(
            token in source
            for token in (
                "SSD1681_PHASE_PARALLEL_R9_ACTIVATIONS 16u",
                "SSD1681_PHASE_PARALLEL_R9_WINDOW_X_START_BYTE 1u",
                "SSD1681_PHASE_PARALLEL_R9_WINDOW_X_END_BYTE 4u",
                "SSD1681_PHASE_PARALLEL_R9_WINDOW_Y_START 8u",
                "SSD1681_PHASE_PARALLEL_R9_WINDOW_Y_END 39u",
                "SSD1681_PHASE_PARALLEL_R9_WINDOW_BYTES 128u",
            )
        ),
        "patterns": expected_previous in body and expected_current in body,
        "fixed_banks": (
            "ssd1681_custom_mode2_write_plane(&window, 0x26u, previous)" in loop
            and loop.count("ssd1681_custom_mode2_write_plane(&window, 0x24u, current)") == 2
        ),
        "single_activation_per_step": (
            loop.count("ssd1681_command_data(0x22u, mode2_display, sizeof(mode2_display))") == 1
            and loop.count("ssd1681_command(0x20u)") == 1
            and loop.count("ssd1681_wait_refresh_complete(0u, 600u)") == 1
        ),
        "no_loop_delay_or_uart": "HAL_Delay" not in loop and "printf" not in loop,
        "local_only": "SSD1681_FRAME_BYTES" not in body and "s_frame" not in body,
        "forbidden_controls": all(token not in body for token in ("0xF7u", "0xC7u", "0xFFu", "0x37u")),
        "no_retry_or_motion": all(token not in body for token in ("120u", "automatic_retry", "second_activation")),
        "lut_register_split": (
            body.count("ssd1681_command_data(0x32u, ssd1681_phase_parallel_r9_lut, 153u)") == 1
            and body.count("ssd1681_command_data(0x3Fu, &ssd1681_phase_parallel_r9_lut[153], 1u)") == 1
            and body.count("ssd1681_command_data(0x03u, &ssd1681_phase_parallel_r9_lut[154], 1u)") == 1
            and body.count("ssd1681_command_data(0x04u, &ssd1681_phase_parallel_r9_lut[155], 3u)") == 1
            and body.count("ssd1681_command_data(0x2Cu, &ssd1681_phase_parallel_r9_lut[158], 1u)") == 1
        ),
        "reset_before_lut_only": (
            body.count("ssd1681_point_probe_hard_reset();") == 1
            and body.find("ssd1681_point_probe_hard_reset();") < body.find("ssd1681_command_data(0x32u")
        ),
        "verbose_after_observation": (
            body.find("phase_parallel_r9 observation_complete") >= 0
            and body.find("phase_parallel_r9 step=") > body.find("phase_parallel_r9 observation_complete")
        ),
        "entry_isolated": (
            "#if COMPANION_EPAPER_SSD1681_PHASE_PARALLEL_R9_DIAGNOSTIC" in source
            and "ssd1681_phase_parallel_r9_diagnostic();\n    return;" in source
        ),
    }
    errors.extend(name for name, passed in checks.items() if not passed)
    return errors


def runner_errors(source: str) -> list[str]:
    errors: list[str] = []
    static_gate = source.find("& python $staticVerifier")
    check_only = source.find("if ($CheckOnly) {", static_gate)
    lock = source.find('$failureStage = "lock"', check_only)
    preclean = source.find('Operation "preclean-white-write"', lock)
    candidate = source.find('Operation "candidate-write"', preclean)
    parser = source.find("& python $controllerVerifier", candidate)
    prompt = source.find("$promptOutput = & pwsh -NoProfile -File $r9VisualPrompt", parser)
    postclean = source.find('Operation "postclean-white-write"', prompt)
    restore = source.find('Operation "restore-write-verify-upload"', postclean)
    checks = {
        "ordered_lifecycle": 0 <= static_gate < check_only < lock < preclean < candidate < parser < prompt < postclean < restore,
        "r9_mode": "[switch]$PhaseParallelR9" in source,
        "static_parser_binding": all(
            token in source
            for token in (
                "verify_wb55_ssd1681_phase_parallel_r9_diagnostic.py",
                "verify_wb55_ssd1681_phase_parallel_r9_log.py",
                "invoke_wb55_ssd1681_phase_parallel_r9_final_visual_prompt.ps1",
            )
        ),
        "candidate_hash": R9_HEX_SHA in source and "__R9_HEX_SHA256__" not in source,
        "dual_clean": (
            "$dualPlaneCleanProfile = $dualPlaneCustomMode2 -or $observableR6 -or $phaseParallelR9" in source
            and DUAL_HEX_SHA in source
            and "supplier_basemap_0x24_0x26_f7_white_readback" in source
        ),
        "promptless_machine_popups": (
            "pre_execute = 0; cleanup = 0; recovery_or_fault_acknowledgement = 0" in source
            and "operator-prompt" not in source
            and "MessageBox" not in source
            and "Read-Host" not in source
        ),
        "one_final_visual_contract": (
            "visual_acceptance = $(if ($phaseParallelR9) { 1 } else { 0 })" in source
            and "one_final_canonical_chinese_pass_fail_after_machine_candidate_before_promptless_cleanup_restore" in source
            and "$report.operator_prompt.invoked = $true" in source
            and "$r9VisualPassed = $operatorReview.status -eq \"PASS_OWNER_R9_LOCAL_VISUAL\"" in source
        ),
        "restored_pass_requires_owner_pass": (
            "PASS_MACHINE_PHASE_PARALLEL_R9_RESTORED_OWNER_PASSED" in source
            and "NO_GO_R9_VISUAL_NOT_PASSED_RESTORED" in source
        ),
        "no_retry": "automatic_retries = 0" in source and "no retry is allowed" in source,
        "single_operations": all(
            source.count(token) == 1
            for token in (
                'Operation "preclean-white-write"',
                'Operation "candidate-write"',
                'Operation "postclean-white-write"',
                'Operation "restore-write-verify-upload"',
            )
        ),
    }
    errors.extend(name for name, passed in checks.items() if not passed)
    return errors


def prompt_errors(source: str) -> list[str]:
    errors: list[str] = []
    machine_gate = source.find('$controller.status -ne "PASS_MACHINE_PHASE_PARALLEL_R9"')
    prompt = source.find("$promptOutput = & $pwsh -NoProfile -File $aiw operator-prompt")
    checks = {
        "machine_gate_before_prompt": 0 <= machine_gate < prompt,
        "single_canonical_prompt": source.count("-File $aiw operator-prompt") == 1,
        "pass_fail_only": '-Buttons "通过,失败"' in source,
        "review_input": "-Input" in source and "-ReviewStyle" in source,
        "chinese_visual_scope": all(
            token in source for token in ("最终视觉验收", "整屏黑闪", "局部黑白都可逆", "每个落点完整")
        ),
        "result_next_to_machine": (
            '"operator-review.json"' in source
            and '"operator-note.txt"' in source
            and "controller_sha256" in source
            and "note_sha256" in source
        ),
        "no_other_popup": "MessageBox" not in source and "Read-Host" not in source,
        "no_second_result": "a second acceptance prompt is forbidden" in source,
    }
    errors.extend(name for name, passed in checks.items() if not passed)
    return errors


def waveform_errors(values: bytes, supplier: bytes, workbench: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if len(values) != 159:
        return ["candidate_length"]
    oracle = transition_oracle(values)
    expected = {
        "BB": (0, 0, 0, 16, 0),
        "BW": (16, 8, 8, 0, 0),
        "WB": (16, 8, 8, 0, 0),
        "WW": (0, 0, 0, 16, 0),
    }
    if sha_bytes(values) != LUT_SHA:
        errors.append("candidate_hash")
    if values.hex().upper() != workbench.get("candidate", {}).get("lut_hex"):
        errors.append("workbench_candidate_identity")
    if values[144:159] != supplier[144:159] or values[153:159].hex().upper() != "221741A83258":
        errors.append("supplier_fr_xon_tail")
    if oracle["shared_timing_frames"] != 16:
        errors.append("shared_timing")
    if [item["slot"] for item in oracle["active_phases"]] != ["0A", "1A", "2A", "3A"]:
        errors.append("active_phase_order")
    if [item["duration_frames"] for item in oracle["active_phases"]] != [5, 3, 5, 3]:
        errors.append("active_phase_duration")
    for name, expected_values in expected.items():
        item = oracle["transitions"][name]
        actual = (
            item["effective_drive_frames"],
            item["positive_drive_frames"],
            item["negative_drive_frames"],
            item["zero_drive_frames"],
            item["source_volt_frame_impulse"],
        )
        if actual != expected_values:
            errors.append(f"transition_{name}")
    for phase in oracle["active_phases"]:
        if {phase["BW"]["code"], phase["WB"]["code"]} != {1, 2}:
            errors.append(f"parallel_polarity_{phase['slot']}")
    lineage = workbench.get("candidate", {}).get("field_lineage", [])
    if len(lineage) != 4 or [item.get("destination") for item in lineage] != ["0A", "1A", "2A", "3A"]:
        errors.append("field_lineage")
    manifest = modified_manifest(supplier, values, lineage)
    if not manifest or any(not item["derivation"] for item in manifest):
        errors.append("modified_byte_manifest")
    for item in manifest:
        if item["candidate_hex"] != "00" and int(item["index"]) < 144 and not item["supplier_source_fields"]:
            errors.append(f"missing_source_lineage_index_{item['index']}")
    return errors


def mutate_block(source: str, old: str, new: str) -> str:
    marker = "static void ssd1681_phase_parallel_r9_diagnostic"
    start = source.find(marker)
    if start < 0:
        return source
    return source[:start] + source[start:].replace(old, new, 1)


def main() -> int:
    failures: list[str] = []
    checks: dict[str, bool] = {}

    def require(name: str, condition: bool, detail: str) -> None:
        checks[name] = bool(condition)
        if not condition:
            failures.append(detail)

    required = [
        DRIVER, MAKEFILE, BUILDER, RUNNER, LAUNCHER, LAUNCHER_VERIFIER, PROMPT, PARSER,
        WORKBENCH_TOOL, WORKBENCH, DUAL_PARSER, RESTORE, NORMAL, REGISTRY, OWNER, V9,
        R8_RUNTIME, SUPPLIER, BASELINE_A, BASELINE_B, R9_HEX, R9_ELF, DUAL_HEX, DUAL_ELF,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    require("required_inputs", not missing, f"missing inputs: {missing}")
    if missing:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({"status": "NO_GO_STATIC_R9", "failures": failures}, indent=2) + "\n")
        return 1

    driver = DRIVER.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    builder = BUILDER.read_text(encoding="utf-8")
    runner = RUNNER.read_text(encoding="utf-8")
    launcher = LAUNCHER.read_text(encoding="utf-8")
    prompt = PROMPT.read_text(encoding="utf-8")
    registry = REGISTRY.read_text(encoding="utf-8")
    workbench = json.loads(WORKBENCH.read_text(encoding="utf-8"))
    r8 = json.loads(R8_RUNTIME.read_text(encoding="utf-8"))
    supplier = parse_supplier_lut(SUPPLIER.read_text(encoding="latin-1"))
    candidate = parse_driver_lut(driver)

    locked = {
        WORKBENCH: WORKBENCH_SHA,
        SUPPLIER: SUPPLIER_SHA,
        R8_RUNTIME: R8_RUNTIME_SHA,
        BASELINE_A: BASELINE_SHA,
        BASELINE_B: BASELINE_SHA,
        OWNER: OWNER_SHA,
        V9: V9_SHA,
        R9_HEX: R9_HEX_SHA,
        R9_ELF: R9_ELF_SHA,
        DUAL_HEX: DUAL_HEX_SHA,
        DUAL_ELF: DUAL_ELF_SHA,
        RUNNER: RUNNER_SHA,
        LAUNCHER: LAUNCHER_SHA,
        PROMPT: PROMPT_SHA,
        PARSER: PARSER_SHA,
    }
    for path, expected in locked.items():
        require(f"hash_{path.name}_{len(checks)}", sha(path) == expected, f"hash drift: {path}")
    require("supplier_lut", len(supplier) == 159 and sha_bytes(supplier) == SUPPLIER_LUT_SHA, "supplier LUT identity differs")
    require(
        "registry_comp_req_309",
        registry.count("| COMP-REQ-309 |") == 1
        and "MACHINE_READY evidence only; no Execute or hardware contact is authorized" in registry
        and "only the final canonical Chinese PASS/FAIL visual acceptance window may appear" in registry,
        "COMP-REQ-309 contract is missing or duplicate",
    )
    require(
        "workbench_admission",
        workbench.get("status") == "ADMIT_ONE_VARIABLE_R9"
        and workbench.get("candidate", {}).get("lut_sha256") == LUT_SHA,
        "R9 workbench admission differs",
    )
    require(
        "r8_fixed_bank",
        r8.get("classification", {}).get("selected_mapping") == "fixed_bank"
        and r8.get("classification", {}).get("target_selector") == {"0x24": 0, "0x26": 1},
        "R8 fixed-bank mapping is not preserved",
    )
    require("waveform", not waveform_errors(candidate, supplier, workbench), f"waveform errors: {waveform_errors(candidate, supplier, workbench)}")
    require("driver", not driver_errors(driver, candidate), f"driver errors: {driver_errors(driver, candidate)}")
    require(
        "isolated_build",
        all(
            token in makefile + builder
            for token in (
                "EPAPER_SSD1681_PHASE_PARALLEL_R9_DIAGNOSTIC",
                "EpaperSsd1681PhaseParallelR9Diagnostic",
                "build_ssd1681_phase_parallel_r9",
                "Companion_Nucleo_WB55RG_Ssd1681PhaseParallelR9",
            )
        ),
        "isolated default-off R9 build path differs",
    )
    elf_text = R9_ELF.read_bytes().decode("latin1", errors="ignore")
    require(
        "elf_markers",
        all(
            marker in elf_text
            for marker in (
                "phase_parallel_r9 start candidate=source_field_reorder_phase_parallel_r9",
                "old_command=0x26 old_selector=1 new_command=0x24 new_selector=0",
                "post_sync_24=%u post_sync_refresh=0",
                LUT_SHA,
            )
        ),
        "R9 ELF lacks sealed candidate markers",
    )
    require("runner", not runner_errors(runner), f"runner errors: {runner_errors(runner)}")
    require("prompt", not prompt_errors(prompt), f"prompt errors: {prompt_errors(prompt)}")
    require(
        "launcher",
        all(
            token in launcher
            for token in (
                RUNNER_SHA, R9_HEX_SHA, WORKBENCH_SHA, PROMPT_SHA, '"-PhaseParallelR9"',
                "READY_NO_HARDWARE_CONTACT", "durable_stdout_redirected = $true",
            )
        ),
        "R9 persistent launcher identity/lifecycle differs",
    )

    # Source and waveform mutation fixtures prove the static predicates fail closed.
    negative: dict[str, bool] = {}
    mutated = bytearray(candidate)
    mutated[153] ^= 1
    negative["tail_drift"] = bool(waveform_errors(bytes(mutated), supplier, workbench))
    mutated = bytearray(candidate)
    mutated[67] = 4
    negative["invented_timing"] = bool(waveform_errors(bytes(mutated), supplier, workbench))
    mutated = bytearray(candidate)
    mutated[0] = 0x40
    negative["stationary_drive"] = bool(waveform_errors(bytes(mutated), supplier, workbench))
    negative["activation_17"] = bool(
        driver_errors(driver.replace("SSD1681_PHASE_PARALLEL_R9_ACTIVATIONS 16u", "SSD1681_PHASE_PARALLEL_R9_ACTIVATIONS 17u", 1), candidate)
    )
    loop_anchor = "ssd1681_custom_mode2_fill_pattern(previous, previous_patterns[step]);"
    negative["loop_dwell"] = bool(driver_errors(mutate_block(driver, loop_anchor, "HAL_Delay(800u);\n        " + loop_anchor), candidate))
    negative["early_uart"] = bool(driver_errors(mutate_block(driver, loop_anchor, 'printf("early");\n        ' + loop_anchor), candidate))
    negative["forbidden_f7"] = bool(driver_errors(mutate_block(driver, loop_anchor, "ssd1681_command(0xF7u);\n        " + loop_anchor), candidate))
    negative["missing_post_sync"] = bool(driver_errors(mutate_block(driver, "ok = ssd1681_custom_mode2_write_plane(&window, 0x24u, current);", "ok = true;"), candidate))
    negative["fixed_bank_swap"] = bool(driver_errors(mutate_block(driver, "0x26u, previous", "0x24u, previous"), candidate))
    negative["lut_payload_152"] = bool(driver_errors(mutate_block(driver, "ssd1681_phase_parallel_r9_lut, 153u", "ssd1681_phase_parallel_r9_lut, 152u"), candidate))
    negative["runner_hash"] = bool(runner_errors(runner.replace(R9_HEX_SHA, "0" * 64, 1)))
    negative["runner_missing_postclean"] = bool(runner_errors(runner.replace('Operation "postclean-white-write"', 'Operation "postclean-disabled"', 1)))
    negative["runner_machine_popup"] = bool(runner_errors(runner.replace("pre_execute = 0; cleanup = 0", "pre_execute = 0; cleanup = 1", 1)))
    negative["runner_missing_prompt"] = bool(runner_errors(runner.replace("$promptOutput = & pwsh -NoProfile -File $r9VisualPrompt", "$promptOutput = $null", 1)))
    negative["prompt_wrong_buttons"] = bool(prompt_errors(prompt.replace('-Buttons "通过,失败"', '-Buttons "确定"', 1)))
    negative["prompt_before_machine"] = bool(prompt_errors(prompt.replace('$controller.status -ne "PASS_MACHINE_PHASE_PARALLEL_R9"', '$controller.status -ne "UNVERIFIED"', 1)))
    negative["prompt_second_popup"] = bool(prompt_errors(prompt + "\n$again = & $pwsh -NoProfile -File $aiw operator-prompt\n"))
    for name, rejected in negative.items():
        require(f"negative_{name}", rejected, f"negative fixture accepted: {name}")

    host_tests: dict[str, dict[str, Any]] = {}
    commands = {
        "r9_log_parser": [sys.executable, str(PARSER), "--self-test"],
        "r9_workbench": [sys.executable, str(WORKBENCH_TOOL), "--self-test"],
        "dual_plane_parser": [sys.executable, str(DUAL_PARSER), "--self-test"],
        "restore": [sys.executable, str(RESTORE), "--self-test"],
        "normal_resume": [sys.executable, str(NORMAL), "--self-test"],
        "launcher": [sys.executable, str(LAUNCHER_VERIFIER)],
    }
    for name, command in commands.items():
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120)
        output = (proc.stdout + proc.stderr).strip()
        host_tests[name] = {"returncode": proc.returncode, "output": output[-2000:]}
        require(f"host_{name}", proc.returncode == 0, f"{name} failed: {output}")
    for name, path in {"runner": RUNNER, "launcher": LAUNCHER, "prompt": PROMPT, "builder": BUILDER}.items():
        proc = subprocess.run(
            [
                "pwsh", "-NoProfile", "-Command",
                f"$null=[scriptblock]::Create((Get-Content -LiteralPath '{path}' -Raw)); 'PASS'",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        host_tests[f"powershell_{name}"] = {"returncode": proc.returncode, "output": (proc.stdout + proc.stderr).strip()}
        require(f"powershell_{name}", proc.returncode == 0 and "PASS" in proc.stdout, f"PowerShell parse failed: {path}")

    oracle = transition_oracle(candidate)
    manifest = modified_manifest(supplier, candidate, workbench["candidate"]["field_lineage"])
    report = {
        "schema_id": "companion.wb55.ssd1681_phase_parallel_r9_static.v1",
        "status": "PASS_STATIC_PHASE_PARALLEL_R9" if not failures else "NO_GO_STATIC_PHASE_PARALLEL_R9",
        "hardware_contact": 0,
        "execute_invoked": False,
        "popup_count": 0,
        "requirement": "COMP-REQ-309",
        "checks": checks,
        "failures": failures,
        "candidate": {
            "name": "source_field_reorder_phase_parallel_r9",
            "production_enabled": False,
            "default_enabled": False,
            "lut_byte_count": len(candidate),
            "lut_hex": candidate.hex().upper(),
            "lut_sha256": sha_bytes(candidate),
            "supplier_lut_sha256": sha_bytes(supplier),
            "workbench_sha256": sha(WORKBENCH),
            "tail_hex": candidate[153:159].hex().upper(),
            "fr_xon_tail_hex": candidate[144:159].hex().upper(),
            "modified_byte_count": len(manifest),
            "modified_byte_manifest": manifest,
            "field_lineage": workbench["candidate"]["field_lineage"],
        },
        "transition_oracle": oracle,
        "command_oracle": {
            "activations_max": 16,
            "window": {"x_bytes": [1, 4], "y": [8, 39], "width": 32, "height": 32, "bytes_per_plane": 128},
            "previous": {"command": "0x26", "selector": 1, "writes_per_step": 1},
            "current": {"command": "0x24", "selector": 0, "stage_writes_per_step": 1},
            "post_sync": {"command": "0x24", "selector": 0, "writes_per_step": 1, "activation": 0},
            "activation": {"control": "0xCF", "refresh": "0x20", "busy_limit_ms": 600, "per_step": 1},
            "observation_forbidden": {
                "full_frame_writes": 0, "full_refreshes": 0, "0xF7": 0, "0xC7": 0,
                "0xFF": 0, "0x37": 0, "automatic_retries": 0, "motion_120_frame": 0,
            },
        },
        "lifecycle": {
            "preclean": "promptless supplier-exact dual-plane White; selector0/1 each read twice",
            "visual_popup": "exactly one canonical Chinese PASS/FAIL after candidate machine PASS only",
            "postclean": "promptless identical dual-plane White",
            "restore": {"bytes": 524288, "sha256": BASELINE_SHA, "normal_resume_required": True},
            "start_cleanup_recovery_fault_popup_count": 0,
        },
        "images": {
            "r9_hex_sha256": sha(R9_HEX),
            "r9_elf_sha256": sha(R9_ELF),
            "dual_clean_hex_sha256": sha(DUAL_HEX),
            "dual_clean_elf_sha256": sha(DUAL_ELF),
        },
        "negative_fixtures": negative,
        "host_tests": host_tests,
        "protected_hashes": {
            "locked_v9_source_sha256": sha(V9),
            "owner_acceptance_sha256": sha(OWNER),
            "supplier_source_sha256": sha(SUPPLIER),
            "r8_runtime_sha256": sha(R8_RUNTIME),
        },
        "source_hashes": {
            str(path.relative_to(ROOT)): sha(path)
            for path in (DRIVER, MAKEFILE, BUILDER, RUNNER, LAUNCHER, PROMPT, PARSER, WORKBENCH_TOOL, WORKBENCH)
        },
        "production_allowed": False,
        "hardware_execute_allowed": False,
        "machine_ready_boundary": "persistent CheckOnly plus registry/current-goal/diff closure still required; no Execute",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(report["status"])
    for failure in failures:
        print(f"FAIL: {failure}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
