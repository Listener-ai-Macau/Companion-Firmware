#!/usr/bin/env python3
"""Static and fixture checks for the Companion recording FSM."""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys
import zlib


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
RECORDING_DIR = REPO_ROOT / "app/companion_pendant/recording"
FSM_HEADER = RECORDING_DIR / "recording_fsm.h"
FSM_SOURCE = RECORDING_DIR / "recording_fsm.c"
MIC_HEADER = RECORDING_DIR / "microphone.h"
MIC_SOURCE = RECORDING_DIR / "microphone.c"
README = RECORDING_DIR / "README.md"
DIAG_EVENTS = REPO_ROOT / "app/companion_pendant/diag_log/diag_log_events.h"
BLE_CONTRACT = REPO_ROOT / "docs/ble_gatt_contract.md"
FIXTURE = REPO_ROOT / "docs/validation/companion-pendant-firmware-bringup-1.5-synthetic-recording.json"

REQUIRED_STATES = [
    "COMP_RECORDING_STATE_IDLE",
    "COMP_RECORDING_STATE_PENDING_START",
    "COMP_RECORDING_STATE_RECORDING",
    "COMP_RECORDING_STATE_STOPPING",
    "COMP_RECORDING_STATE_CANCELED",
    "COMP_RECORDING_STATE_TRANSFER_READY",
    "COMP_RECORDING_STATE_TRANSFER_ACTIVE",
    "COMP_RECORDING_STATE_TRANSFERRED",
    "COMP_RECORDING_STATE_ERROR_RECOVERY",
]

REQUIRED_EVENTS = [
    "COMP_RECORDING_EVENT_START_REQUEST",
    "COMP_RECORDING_EVENT_MIC_READY",
    "COMP_RECORDING_EVENT_STOP_REQUEST",
    "COMP_RECORDING_EVENT_CANCEL_REQUEST",
    "COMP_RECORDING_EVENT_SESSION_FINISHED",
    "COMP_RECORDING_EVENT_TRANSFER_BEGIN",
    "COMP_RECORDING_EVENT_TRANSFER_FINISHED",
    "COMP_RECORDING_EVENT_ERROR_DETECTED",
    "COMP_RECORDING_EVENT_RECOVERY_COMPLETE",
]

EXPECTED_CASES = {
    "start_idle_to_recording": [
        "COMP_RECORDING_STATE_IDLE",
        "COMP_RECORDING_EVENT_START_REQUEST",
        "COMP_RECORDING_EFFECT_START_CAPTURE",
        "COMP_RECORDING_STATE_RECORDING",
    ],
    "start_idle_to_pending_start": [
        "COMP_RECORDING_STATE_IDLE",
        "COMP_RECORDING_EVENT_START_REQUEST",
        "COMP_RECORDING_EFFECT_ENTER_PENDING_START",
        "pending_start_mic_not_ready",
    ],
    "mic_ready_pending_start": [
        "COMP_RECORDING_STATE_PENDING_START",
        "COMP_RECORDING_EVENT_MIC_READY",
        "COMP_RECORDING_EFFECT_START_CAPTURE",
    ],
    "reject_start_while_recording": [
        "COMP_RECORDING_STATE_RECORDING",
        "COMP_RECORDING_EFFECT_REJECT",
        "start_rejected_recording_active",
    ],
    "reject_start_while_stopping": [
        "COMP_RECORDING_STATE_STOPPING",
        "COMP_RECORDING_EFFECT_REJECT",
        "start_rejected_stop_in_progress",
    ],
    "stop_recording_to_stopping": [
        "COMP_RECORDING_EVENT_STOP_REQUEST",
        "COMP_RECORDING_EFFECT_STOP_CAPTURE",
        "COMP_RECORDING_STATE_STOPPING",
    ],
    "session_finished_after_stop": [
        "COMP_RECORDING_EVENT_SESSION_FINISHED",
        "COMP_RECORDING_EFFECT_MARK_TRANSFER_READY",
        "COMP_RECORDING_STATE_TRANSFER_READY",
    ],
    "cancel_pending_start": [
        "COMP_RECORDING_STATE_PENDING_START",
        "COMP_RECORDING_EVENT_CANCEL_REQUEST",
        "COMP_RECORDING_STATE_CANCELED",
    ],
    "cancel_recording": [
        "COMP_RECORDING_STATE_RECORDING",
        "COMP_RECORDING_EVENT_CANCEL_REQUEST",
        "recording_canceled",
    ],
    "transfer_ready_to_active": [
        "COMP_RECORDING_STATE_TRANSFER_READY",
        "COMP_RECORDING_EVENT_TRANSFER_BEGIN",
        "COMP_RECORDING_STATE_TRANSFER_ACTIVE",
    ],
    "transfer_active_to_transferred": [
        "COMP_RECORDING_STATE_TRANSFER_ACTIVE",
        "COMP_RECORDING_EVENT_TRANSFER_FINISHED",
        "COMP_RECORDING_STATE_TRANSFERRED",
    ],
    "error_during_recording": [
        "COMP_RECORDING_EVENT_ERROR_DETECTED",
        "COMP_RECORDING_EFFECT_ENTER_ERROR_RECOVERY",
        "COMP_RECORDING_STATE_ERROR_RECOVERY",
    ],
    "recovery_complete_to_idle": [
        "COMP_RECORDING_EVENT_RECOVERY_COMPLETE",
        "COMP_RECORDING_EFFECT_RECOVER_TO_IDLE",
        "COMP_RECORDING_STATE_IDLE",
    ],
}

FORBIDDEN_APP_PATTERNS = {
    r"\bi2s_channel_init_pdm_rx_mode\b": "ESP audio PDM channel API",
    r"\besp_codec_dev\b": "ESP codec device API",
    r"\besp_err_t\b": "ESP error type",
    r"\bESP_LOG\b": "ESP logging macro",
    r"#include\s+\"driver/": "ESP driver include",
    r"#include\s+<driver/": "ESP driver include",
}

DECISION_EFFECT_TOKENS = [
    "comp_diag_log_record",
    "comp_microphone_",
    "memset(",
    "metadata.",
]


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def read(path: pathlib.Path) -> str:
    if not path.exists():
        fail(f"missing required file: {path.relative_to(REPO_ROOT)}")
    return path.read_text(encoding="utf-8")


def extract_function(source: str, name: str) -> str:
    marker = f"{name}("
    start = source.find(marker)
    if start < 0:
        fail(f"missing function {name}()")
    brace = source.find("{", start)
    if brace < 0:
        fail(f"missing body for {name}()")
    depth = 0
    for index in range(brace, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[brace : index + 1]
    fail(f"unterminated function {name}()")
    return ""


def extract_transition_cases(source: str) -> dict[str, str]:
    match = re.search(
        r"COMP_RECORDING_FSM_ARTIFACT\[\]\s*=\s*\{(?P<body>.*?)\n\};",
        source,
        re.S,
    )
    if not match:
        fail("missing COMP_RECORDING_FSM_ARTIFACT table")
    cases: dict[str, str] = {}
    for entry in re.finditer(r"\{\s*\"(?P<id>[^\"]+)\"(?P<body>.*?)\n\s*\},", match.group("body"), re.S):
        cases[entry.group("id")] = entry.group(0)
    return cases


def check_static_surface(errors: list[str]) -> None:
    texts = {
        "recording_fsm.h": read(FSM_HEADER),
        "recording_fsm.c": read(FSM_SOURCE),
        "microphone.h": read(MIC_HEADER),
        "microphone.c": read(MIC_SOURCE),
        "README.md": read(README),
    }
    joined = "\n".join(texts.values())

    for token in REQUIRED_STATES + REQUIRED_EVENTS:
        require(token in joined, f"missing token {token}", errors)

    for pattern, label in FORBIDDEN_APP_PATTERNS.items():
        for name, text in texts.items():
            if re.search(pattern, text):
                errors.append(f"{name} contains forbidden {label}: {pattern}")

    for token in [
        "COMPANION_MIC_BACKEND_SPH0645_I2S",
        "COMPANION_MIC_BACKEND_SPH0655_PDM",
        "COMP_MIC_SOURCE_SPH0645_I2S_COMPATIBLE",
        "COMP_MIC_SOURCE_SPH0655_PDM_COMPATIBLE",
        "COMP_MIC_STM32_INGRESS_SAI_I2S_PCM",
        "COMP_MIC_STM32_INGRESS_SAI_PDM",
        "COMP_MIC_STM32_INGRESS_I2S_PDM",
        "COMP_MIC_STM32_INGRESS_DFSDM_PDM",
        "COMP_MIC_STM32_INGRESS_SOFTWARE_FIXTURE",
        "SPH0645-compatible I2S source",
        "SPH0655-compatible PDM source",
    ]:
        require(token in joined, f"microphone abstraction missing {token}", errors)

    for token in [
        "recording_id",
        "duration_ms",
        "total_length",
        "content_crc32",
        "sha256_prefix_words",
        "packet_sequence_next",
        "byte_offset_ready",
        "sync_state",
    ]:
        require(token in joined, f"BLE recording metadata missing {token}", errors)

    diag = read(DIAG_EVENTS)
    for token in [
        "COMP_DIAG_EVT_RECORDING_FSM_START_REQUEST",
        "COMP_DIAG_EVT_RECORDING_FSM_STOP_REQUEST",
        "COMP_DIAG_EVT_RECORDING_FSM_CANCEL_REQUEST",
        "COMP_DIAG_EVT_RECORDING_FSM_SESSION_FINISHED",
        "COMP_DIAG_EVT_RECORDING_FSM_ERROR",
        "COMP_DIAG_EVT_RECORDING_FSM_REJECTED",
        "COMP_DIAG_EVT_MICROPHONE_CAPTURE_START",
        "COMP_DIAG_EVT_MICROPHONE_CAPTURE_DROP",
    ]:
        require(token in joined or token in diag, f"diag event coverage missing {token}", errors)

    contract = read(BLE_CONTRACT)
    for token in ["recording_control", "recording_list", "recording chunk pull", "CRC", "hash"]:
        require(token in contract, f"BLE contract missing recording token {token}", errors)


def check_fsm_artifact(errors: list[str]) -> None:
    source = read(FSM_SOURCE)
    cases = extract_transition_cases(source)
    missing = sorted(set(EXPECTED_CASES) - set(cases))
    require(not missing, f"transition artifact missing cases: {missing}", errors)
    for case_id, tokens in EXPECTED_CASES.items():
        body = cases.get(case_id, "")
        for token in tokens:
            require(token in body, f"{case_id} missing {token}", errors)

    decision_body = extract_function(source, "comp_recording_fsm_decide_transition")
    for token in DECISION_EFFECT_TOKENS:
        require(token not in decision_body, f"decision function contains effect token {token}", errors)

    for token in [
        "comp_recording_apply_decision",
        "comp_recording_fsm_feed_microphone_frames",
        "comp_diag_log_record_code",
        "COMP_DIAG_EVT_RECORDING_FSM_REJECTED",
        "COMP_DIAG_EVT_RECORDING_FSM_SESSION_FINISHED",
        "COMP_DIAG_EVT_RECORDING_FSM_ERROR",
        "COMP_DIAG_EVT_MICROPHONE_CAPTURE_DROP",
    ]:
        require(token in source, f"runtime path missing {token}", errors)


def synthetic_pcm_bytes(duration_ms: int = 5000, sample_rate_hz: int = 16000) -> tuple[bytes, dict[str, int]]:
    sample_count = sample_rate_hz * duration_ms // 1000
    out = bytearray()
    peak = 0
    for index in range(sample_count):
        # Deterministic low-amplitude pseudo voice envelope, little-endian PCM16.
        value = ((index * 73) % 2048) - 1024
        if (index // 1600) % 2:
            value = -value
        peak = max(peak, abs(value))
        out.extend(int(value).to_bytes(2, byteorder="little", signed=True))
    return bytes(out), {"sample_count": sample_count, "peak_abs": peak}


def write_fixture(errors: list[str]) -> None:
    pcm, stats = synthetic_pcm_bytes()
    frame_samples = 160
    sample_rate_hz = 16000
    frame_count = stats["sample_count"] // frame_samples
    frame_bytes = frame_samples * 2
    total_length = len(pcm)
    fixture = {
        "schema_version": 1,
        "mode": "synthetic-no-hardware-recording-fixture",
        "duration_ms": 5000,
        "sample_format": {
            "codec": "pcm16",
            "source_family": "SPH0655-compatible PDM digital MEMS",
            "stm32_ingress": "software_fixture_for_HAL_LL_SAI_PDM_to_PCM_boundary",
            "sample_rate_hz": sample_rate_hz,
            "bits_per_sample": 16,
            "channels": 1,
            "frame_samples": frame_samples,
        },
        "recording_metadata": {
            "recording_id": 1,
            "frame_count": frame_count,
            "packet_sequence_first": 0,
            "packet_sequence_last": frame_count - 1,
            "byte_offset_first": 0,
            "byte_offset_final": total_length,
            "total_length": total_length,
            "crc32": f"0x{zlib.crc32(pcm) & 0xFFFFFFFF:08x}",
            "sha256": hashlib.sha256(pcm).hexdigest(),
            "sync_state": "transfer_ready",
            "delete_after_sync_requested": False,
        },
        "fsm_trace": [
            ["idle", "start_request", "recording"],
            ["recording", "stop_request", "stopping"],
            ["stopping", "session_finished", "transfer_ready"],
            ["transfer_ready", "transfer_begin", "transfer_active"],
            ["transfer_active", "transfer_finished", "transferred"],
        ],
        "negative_cases": [
            "reject_start_while_recording",
            "reject_start_while_stopping",
            "cancel_pending_start",
            "error_during_recording",
            "recovery_complete_to_idle",
        ],
        "diag_events": [
            "recording_fsm.start_request",
            "microphone.capture_start",
            "recording_fsm.stop_request",
            "recording_fsm.session_finished",
            "recording_fsm.rejected",
            "recording_fsm.error",
        ],
        "quality_claim": "fixture metadata only; real microphone audio quality remains a later hardware gate",
    }
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(fixture, indent=2, sort_keys=True) + "\n"
    previous = FIXTURE.read_text(encoding="utf-8") if FIXTURE.exists() else None
    if previous != text:
        FIXTURE.write_text(text, encoding="utf-8")

    require(fixture["duration_ms"] >= 5000, "fixture shorter than 5 seconds", errors)
    require(fixture["duration_ms"] <= 10000, "fixture longer than 10 seconds", errors)
    require(fixture["recording_metadata"]["total_length"] == 160000, "fixture total_length mismatch", errors)
    require(fixture["recording_metadata"]["byte_offset_final"] == 160000, "fixture offset mismatch", errors)
    require(not fixture["recording_metadata"]["delete_after_sync_requested"], "fixture requested delete-after-sync", errors)


def main() -> int:
    errors: list[str] = []
    check_static_surface(errors)
    check_fsm_artifact(errors)
    write_fixture(errors)
    if errors:
        print("FAIL: Companion recording FSM static checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(
        "PASS: Companion recording FSM static checks passed; synthetic fixture "
        f"written to {FIXTURE.relative_to(REPO_ROOT)}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
