#!/usr/bin/env python3
"""Verify the one-command Companion recording-to-meeting-minutes chain."""

from __future__ import annotations

import json
import math
import pathlib
import shutil
import struct
import subprocess
import sys
import wave
from typing import Any


sys.dont_write_bytecode = True
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKDIR = REPO_ROOT / ".cache" / "validation" / "companion-recording-to-minutes-fixture-workdir"
FIXTURE = REPO_ROOT / "docs" / "validation" / "companion-recording-to-minutes-fixture.json"
CLI = REPO_ROOT / "tools" / "companion_recording_to_minutes.py"
DOC = REPO_ROOT / "docs" / "companion_recording_postprocess.md"
BRINGUP_DOC = REPO_ROOT / "docs" / "bringup_steps.md"
GATT_DOC = REPO_ROOT / "docs" / "ble_gatt_contract.md"
MAIN_SOURCE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "main.c"
QSPI_HEADER = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Inc" / "comp_qspi_nor.h"
QSPI_SOURCE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "comp_qspi_nor.c"
NORMALIZED_REPO_ROOT = "<repo>"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def write_fixture_wav(path: pathlib.Path, duration_s: float = 2.0, sample_rate: int = 16000) -> None:
    sample_count = int(duration_s * sample_rate)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(sample_count):
            envelope = 0.35 + 0.65 * ((index // 1600) % 2)
            value = int(1200 * envelope * math.sin(2 * math.pi * 440 * index / sample_rate))
            wav_file.writeframesraw(struct.pack("<h", value))


def normalize_fixture_value(value: Any) -> Any:
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if key in {"started_at", "finished_at"} and isinstance(item, str):
                normalized[key] = "<validation-time>"
            else:
                normalized[key] = normalize_fixture_value(item)
        return normalized
    if isinstance(value, list):
        return [normalize_fixture_value(item) for item in value]
    if isinstance(value, str):
        text = value.replace(str(REPO_ROOT), NORMALIZED_REPO_ROOT)
        text = text.replace(str(REPO_ROOT).replace("\\", "/"), NORMALIZED_REPO_ROOT)
        text = text.replace(str(sys.executable), "<python>")
        text = text.replace(str(sys.executable).replace("\\", "/"), "<python>")
        return text
    return value


def run_cli(wav_path: pathlib.Path, errors: list[str]) -> dict[str, Any]:
    transcript = (
        "Billy: 你好 Companion，听到了吗？\n"
        "oai1: 决定把 Companion 录音链路做成录音到会议纪要的一键命令。\n"
        "Billy: oai1 的待办是接入 Type ASR provider，并写清楚一小时会议容量限制。\n"
        "oai1: 当前问题是 16MiB flash 是否能保存一小时 raw PCM？"
    )
    out_dir = WORKDIR / "cli-output"
    command = [
        sys.executable,
        str(CLI),
        "--audio-path",
        str(wav_path),
        "--transcript-text",
        transcript,
        "--meeting-title",
        "Companion 录音到会议纪要验证",
        "--wake-phrase",
        "你好 companion",
        "--require-transcript",
        "--output-dir",
        str(out_dir),
        "--json",
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        errors.append(
            "recording-to-minutes CLI failed: "
            f"exit={completed.returncode}; stdout={completed.stdout}; stderr={completed.stderr}"
        )
        return {}
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        errors.append(f"recording-to-minutes CLI did not print JSON: {exc}; stdout={completed.stdout}")
        return {}
    report["validation_command"] = command
    return report


def check_report(report: dict[str, Any], errors: list[str]) -> None:
    require(report.get("status") == "PASS", f"unexpected chain status: {report.get('status')}", errors)
    minutes = report.get("minutes", {})
    require(minutes.get("postprocess_state") == "minutes_ready", "minutes were not ready", errors)
    require(minutes.get("wake_word", {}).get("state") == "detected", "wake word was not detected", errors)
    require(minutes.get("transcript", {}).get("provider") == "provided_text", "transcript provider mismatch", errors)
    summary = minutes.get("summary", {})
    require(bool(summary.get("decisions")), "decision extraction missing", errors)
    require(bool(summary.get("action_items")), "action item extraction missing", errors)
    require(bool(summary.get("questions")), "question extraction missing", errors)
    audio = minutes.get("source", {}).get("audio", {})
    require(audio.get("sample_rate_hz") == 16000, "audio sample rate missing", errors)
    require(audio.get("duration_s", 0) >= 1.9, "audio duration too short", errors)

    capacity = report.get("capacity", {})
    require(capacity.get("raw_pcm_bytes_per_second") == 32000, "raw PCM rate should be 32000 B/s", errors)
    require(capacity.get("nucleo_raw_flash_max_seconds") == 60, "NUCLEO max seconds should be 60", errors)
    require(capacity.get("nucleo_raw_flash_max_bytes") == 1_920_000, "NUCLEO max raw bytes should be 1920000", errors)
    require(capacity.get("one_hour_raw_pcm_bytes") == 115_200_000, "one-hour raw PCM byte math mismatch", errors)

    artifacts = report.get("artifacts", {})
    for key in ("minutes_json", "minutes_markdown", "report_json"):
        path = pathlib.Path(str(artifacts.get(key, "")))
        require(path.exists(), f"missing artifact {key}: {path}", errors)


def check_static_contract(errors: list[str]) -> None:
    cli_text = CLI.read_text(encoding="utf-8")
    main_source = MAIN_SOURCE.read_text(encoding="utf-8")
    qspi_text = QSPI_HEADER.read_text(encoding="utf-8") + "\n" + QSPI_SOURCE.read_text(encoding="utf-8")
    docs = "\n".join(path.read_text(encoding="utf-8") for path in (DOC, BRINGUP_DOC, GATT_DOC))

    for token in [
        "FLASH_RECORDING_DEV_MAX_SECONDS 60u",
        "FLASH_RECORDING_BYTES_PER_SECOND",
        "recording_flash_begin_capture(uint16_t max_seconds)",
        "recording_flash_limit_bytes_for_seconds",
        "uint64_t duration_ms",
        "comp_qspi_nor_erase_64k",
        "fallback=4k",
    ]:
        require(token in main_source, f"main.c missing long-recording token {token}", errors)

    for token in [
        "NOR_CMD_BLOCK_ERASE_64K",
        "NOR_BLOCK_ERASE_TIMEOUT_MS",
        "comp_qspi_nor_erase_64k",
    ]:
        require(token in qspi_text, f"QSPI NOR driver missing block erase token {token}", errors)

    for token in [
        "listener-type",
        "--submit-embedded-audio-wav-stream",
        "LISTENER_TYPE_DEBUG_TRANSCRIPT_FILE",
        "one-hour meetings need streaming, compression, or larger storage",
    ]:
        require(token in cli_text, f"recording-to-minutes CLI missing {token}", errors)

    for token in [
        "60 seconds",
        "1,920,000",
        "115,200,000",
        "companion_recording_to_minutes.py",
        "Listener-Type",
    ]:
        require(token in docs, f"docs missing recording-to-minutes/capacity token {token}", errors)


def main() -> int:
    errors: list[str] = []
    if WORKDIR.exists():
        shutil.rmtree(WORKDIR)
    WORKDIR.mkdir(parents=True, exist_ok=True)
    wav_path = WORKDIR / "companion-recording-to-minutes-source.wav"
    write_fixture_wav(wav_path)

    report = run_cli(wav_path, errors)
    if report:
        check_report(report, errors)
    check_static_contract(errors)

    fixture = {
        "schema_version": 1,
        "mode": "synthetic_no_hardware_recording_to_minutes_fixture",
        "source_wav": str(wav_path),
        "chain_report": report,
        "checks": {
            "minutes_ready": report.get("minutes", {}).get("postprocess_state") == "minutes_ready" if report else False,
            "wake_word_detected": report.get("minutes", {}).get("wake_word", {}).get("state") == "detected" if report else False,
            "one_hour_raw_pcm_bytes": 115_200_000,
            "nucleo_raw_flash_max_bytes": 1_920_000,
        },
    }
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    fixture = normalize_fixture_value(fixture)
    FIXTURE.write_text(json.dumps(fixture, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

    if errors:
        print("FAIL: Companion recording-to-minutes checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1

    print(f"PASS: Companion recording-to-minutes verified; fixture written to {FIXTURE.relative_to(REPO_ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
