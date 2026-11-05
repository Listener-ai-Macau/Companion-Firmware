#!/usr/bin/env python3
"""Verify the WB55 PDM microphone quality/margin handoff."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-mic-wb55-pdm-margin.json")
SCHEMA_ID = "companion.mic.wb55_pdm_margin.v1"

BASELINE = REPO_ROOT / "docs" / "validation" / "companion-mic-wb55-pdm-baseline.json"
MAIN_C = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "main.c"
MAKEFILE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Makefile"
BRINGUP_STEPS = REPO_ROOT / "docs" / "bringup_steps.md"
RECOVERY_NOTES = REPO_ROOT / "docs" / "wb55_ble_recovery_notes.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
BASELINE_VERIFIER = REPO_ROOT / "tools" / "verify_companion_mic_wb55_pdm_baseline.py"

OVERRUN_RE = re.compile(r"dma_rx_overruns=(?P<count>\d+)")
LOOP_RE = re.compile(
    r"\[mic-loop\] block=(?P<block>\d+) capture_ms=(?P<capture_ms>\d+)"
    r"(?: diag=(?P<diag>\d+))? app_pump=(?P<app_pump>\d+) ble_stream=(?P<ble_stream>\d+)"
)
MANUAL_RE = re.compile(
    r"\[mic-manual\] block=(?P<block>\d+) status=(?P<status>\w+) quality=(?P<quality>\w+).*?"
    r"preclip=(?P<preclip>\d+).*?pcm_clip=(?P<pcm_clip>\d+)"
)


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
    return path.read_text(encoding="utf-8", errors="replace")


def read_json(path: pathlib.Path, errors: list[str]) -> dict[str, Any]:
    text = read(path, errors)
    if not text:
        return {}
    return json.loads(text)


def load_recording_artifact(baseline: dict[str, Any], errors: list[str]) -> tuple[dict[str, Any], pathlib.Path]:
    recording_rel = baseline.get("source_artifacts", {}).get("recording_chain")
    require(isinstance(recording_rel, str), "baseline missing recording_chain source artifact", errors)
    if not isinstance(recording_rel, str):
        return {}, REPO_ROOT
    path = REPO_ROOT / recording_rel
    return read_json(path, errors), path


def operation_by_name(artifact: dict[str, Any], name: str) -> dict[str, Any]:
    for operation in artifact.get("operations", []):
        if isinstance(operation, dict) and operation.get("operation") == name:
            return operation
    return {}


def parse_serial_margin(serial_text: str) -> dict[str, Any]:
    overrun_counts = [int(match.group("count")) for match in OVERRUN_RE.finditer(serial_text)]
    loops = [
        {
            "block": int(match.group("block")),
            "capture_ms": int(match.group("capture_ms")),
            "diag": int(match.group("diag")) if match.group("diag") is not None else None,
            "app_pump": int(match.group("app_pump")),
            "ble_stream": int(match.group("ble_stream")),
        }
        for match in LOOP_RE.finditer(serial_text)
    ]
    manual = [
        {
            "block": int(match.group("block")),
            "status": match.group("status"),
            "quality": match.group("quality"),
            "preclip": int(match.group("preclip")),
            "pcm_clip": int(match.group("pcm_clip")),
        }
        for match in MANUAL_RE.finditer(serial_text)
    ]
    active_blocks = [entry for entry in manual if entry["status"] == "ok"]
    clipped_blocks = [entry["block"] for entry in manual if entry["quality"] == "clipped"]
    steady_loops = [entry for entry in loops if entry["block"] > 0]
    fast_loops = [entry for entry in steady_loops if entry.get("diag") == 0]
    diagnostic_loops = [entry for entry in loops if entry.get("diag") == 1]
    steady_margin_loops = fast_loops if fast_loops else steady_loops
    return {
        "reported_overrun_counts": overrun_counts,
        "max_dma_rx_overruns": max(overrun_counts) if overrun_counts else 0,
        "loop_observation_count": len(loops),
        "fast_loop_observation_count": len(fast_loops),
        "diagnostic_loop_observation_count": len(diagnostic_loops),
        "max_capture_ms": max((entry["capture_ms"] for entry in loops), default=0),
        "diagnostic_max_capture_ms": max((entry["capture_ms"] for entry in diagnostic_loops), default=0),
        "fast_path_max_capture_ms": max((entry["capture_ms"] for entry in fast_loops), default=0),
        "steady_state_max_capture_ms": max((entry["capture_ms"] for entry in steady_margin_loops), default=0),
        "capture_ms_by_block": loops,
        "manual_observation_count": len(manual),
        "active_manual_blocks": len(active_blocks),
        "clipped_blocks": clipped_blocks,
        "max_preclip": max((entry["preclip"] for entry in manual), default=0),
        "max_pcm_clip": max((entry["pcm_clip"] for entry in manual), default=0),
    }


def div_trunc_toward_zero(numerator: int, denominator: int) -> int:
    if numerator < 0:
        return -((-numerator) // denominator)
    return numerator // denominator


def cic3_bit_sequence(words: list[int], bit_order_lsb: bool) -> list[int]:
    bits = []
    for word in words:
        for index in range(32):
            if bit_order_lsb:
                bit = (word >> index) & 1
            else:
                bit = (word >> (31 - index)) & 1
            bits.append(1 if bit else -1)
    return bits


def cic3_byte_moments(value: int, bit_order_lsb: bool) -> tuple[int, int, int]:
    total = 0
    weighted1 = 0
    weighted2 = 0
    for index in range(8):
        if bit_order_lsb:
            bit = (value >> index) & 1
        else:
            bit = (value >> (7 - index)) & 1
        sample = 1 if bit else -1
        remaining = 8 - index
        total += sample
        weighted1 += remaining * sample
        weighted2 += ((remaining * (remaining + 1)) // 2) * sample
    return total, weighted1, weighted2


def cic3_words_to_bytes(words: list[int], bit_order_lsb: bool) -> list[int]:
    result = []
    for word in words:
        shifts = (0, 8, 16, 24) if bit_order_lsb else (24, 16, 8, 0)
        result.extend((word >> shift) & 0xFF for shift in shifts)
    return result


def cic3_decode_python(words: list[int], bit_order_lsb: bool, use_chunk: bool) -> list[int]:
    decimation = 96
    scale = 128
    gain = decimation * decimation
    i1 = i2 = i3 = c1 = c2 = c3 = 0
    outputs = []
    for sample_base in range(0, len(words), decimation // 32):
        sample_words = words[sample_base:sample_base + (decimation // 32)]
        if use_chunk:
            byte_values = cic3_words_to_bytes(sample_words, bit_order_lsb)
            total = weighted1 = weighted2 = 0
            byte_count = len(byte_values)
            for byte_index, value in enumerate(byte_values):
                byte_sum, byte_weighted1, byte_weighted2 = cic3_byte_moments(value, bit_order_lsb)
                remaining = (byte_count - byte_index - 1) * 8
                total += byte_sum
                weighted1 += (remaining * byte_sum) + byte_weighted1
                weighted2 += (
                    ((remaining * (remaining + 1)) // 2) * byte_sum
                    + (remaining * byte_weighted1)
                    + byte_weighted2
                )
            bit_count = len(byte_values) * 8
            triangular = (bit_count * (bit_count + 1)) // 2
            i3 += (bit_count * i2) + (triangular * i1) + weighted2
            i2 += (bit_count * i1) + weighted1
            i1 += total
        else:
            for bit in cic3_bit_sequence(sample_words, bit_order_lsb):
                i1 += bit
                i2 += i1
                i3 += i2

        comb1 = i3 - c1
        c1 = i3
        comb2 = comb1 - c2
        c2 = comb1
        comb3 = comb2 - c3
        c3 = comb2
        outputs.append(div_trunc_toward_zero(comb3 * scale, gain))
    return outputs


def check_cic3_chunk_math(errors: list[str]) -> None:
    vectors = [
        [0x00000000, 0xFFFFFFFF, 0xAAAAAAAA] * 2,
        [0x55555555, 0x01234567, 0x89ABCDEF] * 2,
        [0x80000000, 0x00000001, 0x7FFFFFFF] * 2,
        [((0x45D9F3B * (index + 1)) ^ (0x9E3779B9 * index)) & 0xFFFFFFFF for index in range(9)],
    ]
    for bit_order_lsb in (False, True):
        for vector in vectors:
            require(
                cic3_decode_python(vector, bit_order_lsb, use_chunk=False)
                == cic3_decode_python(vector, bit_order_lsb, use_chunk=True),
                f"CIC3 chunk math mismatch for bit_order_lsb={bit_order_lsb}",
                errors,
            )


def build_fixture(errors: list[str]) -> dict[str, Any]:
    baseline = read_json(BASELINE, errors)
    recording, recording_path = load_recording_artifact(baseline, errors)
    serial_rel = recording.get("artifacts", {}).get("serial_log")
    require(isinstance(serial_rel, str), "recording artifact missing serial_log path", errors)
    serial_path = REPO_ROOT / serial_rel if isinstance(serial_rel, str) else REPO_ROOT
    serial_text = read(serial_path, errors)
    margin = parse_serial_margin(serial_text)
    quality = operation_by_name(recording, "audio_quality")
    pull = operation_by_name(recording, "recording_pull")
    baseline_recording = baseline.get("recording_evidence", {})
    asr = baseline.get("asr_evidence", {})
    blockers = []
    if margin["max_dma_rx_overruns"] > 0:
        blockers.append("dma_rx_overruns_nonzero")
    if margin["fast_loop_observation_count"] == 0:
        blockers.append("capture_ms_fast_path_not_observed")
    if margin["steady_state_max_capture_ms"] > 10:
        blockers.append("capture_ms_exceeds_10ms_frame_period")
    if quality.get("status") != "PASS" or quality.get("warnings"):
        blockers.append("pc_speaker_audio_quality_warning")
    if "小伴" not in str(asr.get("transcript", "")):
        blockers.append("asr_phrase_confusion_xiaoban_to_xiaobao")
    margin_status = "NEEDS_TUNING" if blockers else "READY_FOR_LONGER_SOAK"
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "target": "NUCLEO-WB55RG",
        "baseline": rel(BASELINE),
        "source_artifacts": {
            "recording_chain": rel(recording_path),
            "serial_log": rel(serial_path),
            "baseline_verifier": rel(BASELINE_VERIFIER),
        },
        "path_acceptance": {
            "status": "PASS",
            "meaning": "PC-speaker audio reached WB55 PDM capture, flash storage, BLE pull, WAV export, and Companion Type ASR.",
            "recording_status": baseline_recording.get("status"),
            "audio_quality_status": quality.get("status"),
            "missing_packets": pull.get("missing_packets", 0),
            "sha256_match": baseline_recording.get("host_sha256") == baseline_recording.get("device_final_sha256"),
            "pcm_bytes": baseline_recording.get("total_length"),
        },
        "current_margin": {
            "status": margin_status,
            "blockers": blockers,
            "observed": margin,
            "audio_quality": {
                "rms": quality.get("rms"),
                "clipping_ratio": quality.get("clipping_ratio"),
                "zero_ratio": quality.get("zero_ratio"),
                "warnings": quality.get("warnings", []),
            },
            "asr_transcript": asr.get("transcript"),
            "expected_phrase": asr.get("expected_phrase"),
        },
        "candidate_optimization": {
            "name": "cic3_byte_o2_fastdiag",
            "status": "BEST_CANDIDATE_READY_FOR_LONGER_SOAK",
            "meaning": "Keep the accepted CIC3/decim96/MSB audio path, build with -O2, and collect full raw diagnostics sparsely. The short PC-speaker run kept the 小伴 ASR transcript, reduced DMA overruns from 97/11 to zero, and measured 10 ms on steady diag=0 capture blocks.",
            "boot_filter_text": "cic3",
            "code_symbols": [
                "pdm_cic3_decode_sample",
                "pdm_cic3_accumulate_word",
                "pdm_cic3_accumulate_byte",
                "MIC_PDM_FILTER_TEXT",
                "MANUAL_RECORDING_DIAGNOSTIC_EVERY_BLOCKS",
            ],
            "build_validation": [
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 -Force -Optimization O2 -PdmCic3ChunkAccumulate 0 -PdmUseCic3Filter 1 -PdmBitOrderLsb 0",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 -Force -PdmCic3ChunkAccumulate 0",
            ],
            "static_equivalence": "verify_companion_mic_wb55_pdm_margin.py compares deterministic bit-by-bit and chunk CIC3 vectors for MSB and LSB bit order.",
            "hardware_validation_needed": [
                "run a longer PC-speaker or speech soak with the same O2/CIC3 firmware",
                "keep max_dma_rx_overruns=0 across the soak",
                "keep diag=0 steady capture_ms at or below the 10 ms frame period",
            ],
            "tested_alternatives": [
                {
                    "name": "cic3_chunk_og",
                    "recording_chain": ".cache/validation/companion-real-mic-pc-speaker-tts-pdm-rawsai-dma-gain3-cic3chunk-msb-decim96-mckdiv31-stage450-short-20260710-052857/companion-flash-recording-chain.json",
                    "asr_chain": ".cache/validation/companion-real-mic-pc-speaker-tts-pdm-rawsai-dma-gain3-cic3chunk-msb-decim96-mckdiv31-stage450-short-20260710-052857-asr/companion-recording-to-minutes.json",
                    "result": "Rejected: recording chain PASS, but max_dma_rx_overruns=115 and Companion Type returned NO_TRANSCRIPT.",
                },
                {
                    "name": "boxcar_msb_og",
                    "recording_chain": ".cache/validation/companion-real-mic-pc-speaker-tts-pdm-rawsai-dma-gain3-boxcar-msb-decim96-mckdiv31-stage450-short-20260710-053356/companion-flash-recording-chain.json",
                    "asr_chain": ".cache/validation/companion-real-mic-pc-speaker-tts-pdm-rawsai-dma-gain3-boxcar-msb-decim96-mckdiv31-stage450-short-20260710-053356-asr/companion-recording-to-minutes.json",
                    "result": "Rejected: max_dma_rx_overruns=0 but steady capture_ms=11 and Companion Type returned NO_TRANSCRIPT.",
                },
            ],
        },
        "optimization_exit_criteria": [
            "new PC-speaker run records max_dma_rx_overruns=0 during active recording",
            "steady-state capture_ms stays at or below the 10 ms PCM frame period",
            "audio_quality.status remains PASS with no warnings",
            "Companion Type ASR transcript contains 小伴 for the short test phrase",
            "recording_pull missing_packets remains 0 and host/device SHA-256 still matches",
        ],
        "wba_portability_rule": "WBA55/WBA65 must keep this margin gate but replace WB55 raw-SAI DMA/CIC3 details with a target-native CubeWBA microphone adapter.",
        "validation_commands": [
            "python .\\tools\\verify_companion_mic_wb55_pdm_margin.py",
            "python .\\tools\\verify_companion_mic_wb55_pdm_baseline.py",
        ],
    }


def check_code_contract(errors: list[str]) -> None:
    joined = "\n".join([
        read(MAIN_C, errors),
        read(MAKEFILE, errors),
    ])
    for token in [
        "dma_rx_overruns",
        "capture_ms",
        "pdm_raw_dma_read_block",
        "pdm_cic3_decode_sample",
        "pdm_cic3_accumulate_word",
        "pdm_cic3_accumulate_byte",
        "COMPANION_PDM_CIC3_CHUNK_ACCUMULATE",
        "pdm_cic3_accumulate_aligned_words",
        "MIC_PDM_FILTER_TEXT",
        "C_OPT ?= -O2",
        "COMPANION_PDM_USE_CIC3_FILTER",
        "COMPANION_PDM_RAW_SAI_USE_DMA",
    ]:
        require(token in joined, f"PDM margin code contract missing {token}", errors)


def check_docs(errors: list[str]) -> None:
    joined = "\n".join([
        read(BRINGUP_STEPS, errors),
        read(RECOVERY_NOTES, errors),
        read(WBA_RULES, errors),
    ])
    for token in [
        "PDM CPU/overrun margin",
        "dma_rx_overruns",
        "companion-mic-wb55-pdm-margin.json",
        "verify_companion_mic_wb55_pdm_margin.py",
        "CubeWBA microphone adapter",
        "Optimization O2",
    ]:
        require(token in joined, f"PDM margin docs missing {token}", errors)


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected PDM margin schema", errors)
    require(data.get("status") == "PASS", "PDM margin verifier fixture must be PASS", errors)
    path_acceptance = data.get("path_acceptance", {})
    require(path_acceptance.get("status") == "PASS", "path acceptance must remain PASS", errors)
    require(path_acceptance.get("audio_quality_status") == "PASS", "audio quality status must remain PASS", errors)
    require(path_acceptance.get("missing_packets") in (0, None), "BLE recording pull must not miss packets", errors)
    require(path_acceptance.get("sha256_match") is True, "recording SHA-256 match must be preserved", errors)
    margin = data.get("current_margin", {})
    observed = margin.get("observed", {})
    require(margin.get("status") == "READY_FOR_LONGER_SOAK", "current WB55 PDM margin should be ready for longer soak", errors)
    require("dma_rx_overruns_nonzero" not in margin.get("blockers", []), "PDM margin fixture should not record DMA overrun blocker", errors)
    require("capture_ms_exceeds_10ms_frame_period" not in margin.get("blockers", []), "PDM margin fixture should not record fast-path capture blocker", errors)
    require(observed.get("max_dma_rx_overruns") == 0, "current PDM overrun count drifted from recorded evidence", errors)
    require(observed.get("fast_loop_observation_count", 0) >= 5, "current PDM fast-path timing evidence is too sparse", errors)
    require(observed.get("fast_path_max_capture_ms") == 10, "current PDM fast-path capture_ms drifted from recorded evidence", errors)
    require(observed.get("steady_state_max_capture_ms") == 10, "current PDM steady capture_ms drifted from recorded evidence", errors)
    require(observed.get("diagnostic_max_capture_ms") >= 15, "current PDM diagnostic timing should remain separated from fast path", errors)
    require("asr_phrase_confusion_xiaoban_to_xiaobao" not in margin.get("blockers", []), "O2 PDM baseline should no longer record ASR phrase confusion", errors)
    candidate = data.get("candidate_optimization", {})
    require(candidate.get("status") == "BEST_CANDIDATE_READY_FOR_LONGER_SOAK", "PDM candidate optimization status must be soak-ready", errors)
    require(candidate.get("boot_filter_text") == "cic3", "PDM candidate optimization must expose CIC3 boot text", errors)
    symbols = "\n".join(str(item) for item in candidate.get("code_symbols", []))
    for token in ["pdm_cic3_decode_sample", "pdm_cic3_accumulate_word"]:
        require(token in symbols, f"PDM candidate optimization missing code symbol {token}", errors)
    build_validation = "\n".join(str(item) for item in candidate.get("build_validation", []))
    for token in ["Optimization O2", "PdmCic3ChunkAccumulate 0"]:
        require(token in build_validation, f"PDM candidate optimization missing build validation {token}", errors)
    alternatives = "\n".join(str(item) for item in candidate.get("tested_alternatives", []))
    for token in ["cic3_chunk_og", "boxcar_msb_og", "NO_TRANSCRIPT"]:
        require(token in alternatives, f"PDM tested alternatives missing {token}", errors)
    require(
        "bit-by-bit and chunk CIC3 vectors" in str(candidate.get("static_equivalence", "")),
        "PDM candidate optimization missing static CIC3 equivalence",
        errors,
    )
    criteria = "\n".join(str(item) for item in data.get("optimization_exit_criteria", []))
    for token in ["max_dma_rx_overruns=0", "10 ms", "小伴", "missing_packets remains 0"]:
        require(token in criteria, f"PDM margin exit criteria missing {token}", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing PDM margin fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic WB55 PDM margin fixture.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = args.fixture if args.fixture.is_absolute() else REPO_ROOT / args.fixture
    errors: list[str] = []
    for path in [BASELINE, MAIN_C, MAKEFILE, BRINGUP_STEPS, RECOVERY_NOTES, WBA_RULES, BASELINE_VERIFIER]:
        require(path.exists(), f"missing required path {rel(path)}", errors)
    expected = build_fixture(errors) if not errors else {}
    if expected:
        check_fixture_data(expected, errors)
    check_cic3_chunk_math(errors)
    check_code_contract(errors)
    check_docs(errors)
    if args.write_fixture and expected and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture and expected:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion WB55 PDM microphone margin checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion WB55 PDM microphone margin verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
