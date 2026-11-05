#!/usr/bin/env python3
"""Verify the accepted WB55 SPH0655/PDM microphone baseline evidence."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-mic-wb55-pdm-baseline.json")
SCHEMA_ID = "companion.mic.wb55_pdm_baseline.v1"

MAIN_C = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "main.c"
MAKEFILE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Makefile"
BRINGUP_README = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "README.md"
MICROPHONE_C = REPO_ROOT / "app" / "companion_pendant" / "recording" / "microphone.c"
MICROPHONE_H = REPO_ROOT / "app" / "companion_pendant" / "recording" / "microphone.h"
RECORDING_README = REPO_ROOT / "app" / "companion_pendant" / "recording" / "README.md"
BRINGUP_STEPS = REPO_ROOT / "docs" / "bringup_steps.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
RECOVERY_NOTES = REPO_ROOT / "docs" / "wb55_ble_recovery_notes.md"
IOC_DOC = REPO_ROOT / "docs" / "companion_pendant_ioc.md"
LEGACY_I2S_TUNING = REPO_ROOT / "docs" / "validation" / "companion-mic-wb55-sai-i2s-tuning.json"
RECORDING_FSM_VERIFIER = REPO_ROOT / "tools" / "verify_recording_fsm_static.py"
RECORDING_CACHE_VERIFIER = REPO_ROOT / "tools" / "verify_recording_cache_model.py"

def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def read(path: pathlib.Path, errors: list[str]) -> str:
    require(path.exists(), f"missing required path {rel(path)}", errors)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def read_json(path: pathlib.Path, errors: list[str]) -> dict[str, Any]:
    text = read(path, errors)
    if not text:
        return {}
    return json.loads(text)


def extract_function(source: str, signature: str) -> str:
    search_from = 0
    while True:
        start = source.find(signature, search_from)
        if start < 0:
            return ""
        brace = source.find("{", start)
        semicolon = source.find(";", start)
        if brace >= 0 and (semicolon < 0 or brace < semicolon):
            break
        search_from = start + len(signature)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    return ""


def build_fixture(errors: list[str]) -> dict[str, Any]:
    return read_json(REPO_ROOT / DEFAULT_FIXTURE, errors)


def check_code_contract(errors: list[str]) -> None:
    main = read(MAIN_C, errors)
    makefile = read(MAKEFILE, errors)
    mic_c = read(MICROPHONE_C, errors)
    mic_h = read(MICROPHONE_H, errors)
    joined = "\n".join([main, makefile, mic_c, mic_h])
    for token in [
        "COMPANION_MIC_BACKEND COMPANION_MIC_BACKEND_SPH0655_PDM",
        "#define COMPANION_PDM_DECIMATION_FACTOR 96u",
        "#define COMPANION_PDM_RAW_SAI_MCKDIV 31u",
        "#define COMPANION_PDM_USE_CIC3_FILTER 1",
        "#define COMPANION_PDM_BIT_ORDER_LSB 0",
        "#define COMPANION_MIC_PREAMP_SHIFT 3u",
        "#define FLASH_RECORDING_STAGE_BLOCKS 450u",
        "C_OPT ?= -O2",
        "#define COMPANION_PDM_RAW_SAI_USE_DMA (!COMPANION_PDM_USE_HARDWARE_INTERFACE)",
        "HAL_SAI_Receive_DMA",
        "pdm_raw_dma_restore_kernel_clock",
        "pdm_raw_dma_prepare_session",
        "MIC_CAPTURE_RESULT_PENDING",
        "[mic-session] action=prepare reused_dma=%u",
        "RCC_FLAG_PLLSAI1RDY",
        "RCC_SAI1CLKSOURCE_PLLSAI1",
        "pdm_cic3_decode_sample",
        "COMP_MIC_SOURCE_SPH0655_PDM_COMPATIBLE",
        "COMP_MIC_STM32_INGRESS_SAI_PDM",
        "COMP_MIC_ENCODING_PCM16_MONO",
    ]:
        require(token in joined, f"WB55 PDM code contract missing {token}", errors)
    for token in [
        "PDM_RAW_SAI_MCKDIV",
        "PDM_USE_CIC3_FILTER",
        "FLASH_RECORDING_STAGE_BLOCKS",
        "C_OPT",
    ]:
        require(token in makefile, f"WB55 bring-up Makefile missing override {token}", errors)

    prepare = extract_function(main, "static void pdm_raw_dma_prepare_session(void)")
    require(bool(prepare), "WB55 PDM session-prepare function is missing", errors)
    for forbidden in ["HAL_SAI_DMAStop", "__HAL_SAI_DISABLE", "SAI_xCR2_FFLUSH"]:
        require(
            forbidden not in prepare,
            f"WB55 PDM session prepare must reuse active DMA; found {forbidden}",
            errors,
        )
    require(
        "s_pdm_raw_dma_ready_mask = 0u" in prepare,
        "WB55 PDM session prepare must clear stale completed-half state",
        errors,
    )

    restore_clock = extract_function(main, "static HAL_StatusTypeDef pdm_raw_dma_restore_kernel_clock(void)")
    require(bool(restore_clock), "WB55 PDM kernel-clock restore function is missing", errors)
    for token in [
        "RCC_FLAG_PLLSAI1RDY",
        "HAL_RCCEx_PeriphCLKConfig",
        "RCC_SAI1CLKSOURCE_PLLSAI1",
        "__HAL_RCC_SAI1_CLK_ENABLE",
    ]:
        require(token in restore_clock, f"WB55 PDM clock restore missing {token}", errors)

    start_dma = extract_function(main, "static HAL_StatusTypeDef pdm_raw_dma_start_if_needed(void)")
    require(
        "pdm_raw_dma_restore_kernel_clock()" in start_dma,
        "WB55 PDM DMA start must restore PLLSAI1 after Stop wake",
        errors,
    )

    capture = extract_function(main, "static mic_capture_result_t capture_microphone_block(")
    require(bool(capture), "WB55 microphone capture function is missing", errors)
    require(
        "pdm_raw_dma_read_block(raw_words, timeout_ms" in capture,
        "WB55 PDM capture must forward the caller timeout",
        errors,
    )
    require(
        "timeout_ms == 0u" in capture and "return MIC_CAPTURE_RESULT_PENDING" in capture,
        "WB55 zero-timeout capture must report pending without a recording failure",
        errors,
    )
    require(
        re.search(
            r'capture_microphone_block\(block_index,\s*collect_diagnostics,\s*"mic-manual",\s*0u\)',
            main,
        )
        is not None,
        "manual recording must poll microphone DMA without blocking touch processing",
        errors,
    )
    require(
        re.search(
            r"capture_result == MIC_CAPTURE_RESULT_PENDING\)\s*\{\s*HAL_Delay\(1u\);\s*continue;",
            main,
        )
        is not None,
        "manual recording must keep servicing the main loop while the next DMA frame is pending",
        errors,
    )


def check_docs(errors: list[str]) -> None:
    texts = {
        "bringup_readme": read(BRINGUP_README, errors),
        "recording_readme": read(RECORDING_README, errors),
        "bringup_steps": read(BRINGUP_STEPS, errors),
        "wba_rules": read(WBA_RULES, errors),
        "recovery_notes": read(RECOVERY_NOTES, errors),
        "ioc_doc": read(IOC_DOC, errors),
    }
    joined = "\n".join(texts.values())
    for token in [
        "SPH0655-compatible PDM",
        "raw-SAI DMA",
        "MSB+CIC3",
        "MCKDIV 31",
        "decimation 96",
        "preamp shift 3",
        "450-block",
        "O2",
        "PC speaker",
        "Companion Type ASR",
        "CubeWBA microphone adapter",
        "16 kHz PCM16",
        "companion-mic-wb55-pdm-baseline.json",
        "verify_companion_mic_wb55_pdm_baseline.py",
    ]:
        require(token in joined, f"microphone docs missing {token}", errors)
    legacy = read_json(LEGACY_I2S_TUNING, errors)
    require(legacy.get("status") == "RETIRED", "legacy WB55 I2S tuning artifact must be retired", errors)
    require(
        legacy.get("current_baseline") == rel(DEFAULT_FIXTURE),
        "legacy WB55 I2S tuning artifact must point to the PDM baseline",
        errors,
    )


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected WB55 PDM baseline schema", errors)
    require(data.get("status") == "PASS", "WB55 PDM baseline must be PASS", errors)
    path = data.get("microphone_path", {})
    require(path.get("source_family") == "SPH0655-compatible PDM digital MEMS", "baseline source family drifted", errors)
    require(path.get("wb55_ingress") == "SAI1 Block A raw-PDM DMA", "baseline ingress drifted", errors)
    decode = path.get("decode", {})
    require(decode.get("bit_order") == "MSB", "baseline PDM bit order drifted", errors)
    require(decode.get("filter") == "CIC3", "baseline PDM filter drifted", errors)
    require(decode.get("decimation") == 96, "baseline PDM decimation drifted", errors)
    require(decode.get("mckdiv") == 31, "baseline PDM MCKDIV drifted", errors)
    require(decode.get("preamp_shift") == 3, "baseline PDM gain drifted", errors)
    require(decode.get("stage_blocks") == 450, "baseline PDM stage buffer drifted", errors)
    require(decode.get("build_optimization") == "O2", "baseline build optimization drifted", errors)
    recording = data.get("recording_evidence", {})
    require(recording.get("status") == "PASS", "recording chain evidence must be PASS", errors)
    require(recording.get("source_mode") == 1, "recording source mode must be SAI microphone", errors)
    require(recording.get("total_length") == 122880, "recording byte count drifted", errors)
    require(recording.get("duration_ms") == 3840, "recording duration drifted", errors)
    require(recording.get("host_sha256") == recording.get("device_final_sha256"), "recording SHA mismatch", errors)
    require(recording.get("missing_packets") in (0, None), "recording pull must not miss packets", errors)
    require(recording.get("audio_quality", {}).get("status") == "PASS", "audio quality must be PASS", errors)
    asr = data.get("asr_evidence", {})
    require(asr.get("status") == "PASS", "ASR chain evidence must be PASS", errors)
    require(asr.get("provider") == "companion_type", "ASR provider must be Companion Type", errors)
    require(asr.get("pcm_bytes") == 122880, "ASR PCM byte count drifted", errors)
    require(asr.get("missing_packets") == 0, "ASR evidence must not miss packets", errors)
    require("小伴录音测试" in str(asr.get("transcript", "")), "ASR transcript drifted from recorded evidence", errors)
    retention = data.get("evidence_retention", {})
    require(retention.get("status") == "DURABLE_SUMMARY", "baseline evidence retention status drifted", errors)
    require(retention.get("raw_cache_required") is False, "baseline verifier must not require worktree-local cache", errors)
    sources = data.get("source_artifacts", {})
    require(
        sources.get("verification_source") == DEFAULT_FIXTURE.as_posix(),
        "baseline verification source must be the tracked durable snapshot",
        errors,
    )
    require(
        str(sources.get("historical_recording_chain", "")).startswith(".cache/validation/"),
        "historical recording provenance path is missing",
        errors,
    )
    require(
        str(sources.get("historical_asr_chain", "")).startswith(".cache/validation/"),
        "historical ASR provenance path is missing",
        errors,
    )
    for command in data.get("validation_commands", []):
        if "\\tools\\" in str(command):
            tool = str(command).split("\\tools\\", 1)[1].split()[0]
            require((REPO_ROOT / "tools" / tool).exists(), f"validation command references missing tool {tool}", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing WB55 PDM baseline fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Copy the durable WB55 PDM baseline to a custom fixture path.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = args.fixture if args.fixture.is_absolute() else REPO_ROOT / args.fixture
    errors: list[str] = []
    required = [
        MAIN_C,
        MAKEFILE,
        MICROPHONE_C,
        MICROPHONE_H,
        REPO_ROOT / DEFAULT_FIXTURE,
        LEGACY_I2S_TUNING,
        RECORDING_FSM_VERIFIER,
        RECORDING_CACHE_VERIFIER,
    ]
    for path in required:
        require(path.exists(), f"missing required path {rel(path)}", errors)
    expected = build_fixture(errors) if not errors else {}
    if expected:
        check_fixture_data(expected, errors)
    check_code_contract(errors)
    check_docs(errors)
    if args.write_fixture and expected and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture and expected:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion WB55 PDM microphone baseline checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion WB55 PDM microphone baseline verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
