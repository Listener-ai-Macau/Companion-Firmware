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
import importlib.util
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
SPI_NOR_HEADER = REPO_ROOT / "app" / "companion_pendant" / "storage" / "spi_nor_stm32wba.h"
SPI_NOR_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "storage" / "spi_nor_stm32wba.c"
NORMALIZED_REPO_ROOT = "<repo>"


def load_cli_module() -> Any:
    spec = importlib.util.spec_from_file_location("companion_recording_to_minutes_under_test", CLI)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {CLI}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    spi_nor_text = SPI_NOR_HEADER.read_text(encoding="utf-8") + "\n" + SPI_NOR_SOURCE.read_text(encoding="utf-8")
    docs = "\n".join(path.read_text(encoding="utf-8") for path in (DOC, BRINGUP_DOC, GATT_DOC))

    for token in [
        "FLASH_RECORDING_DEV_MAX_SECONDS 60u",
        "FLASH_RECORDING_BYTES_PER_SECOND",
        "recording_flash_begin_capture(uint16_t max_seconds)",
        "recording_flash_limit_bytes_for_seconds",
        "uint64_t duration_ms",
        "comp_spi_nor_erase_64k",
        "fallback=4k",
    ]:
        require(token in main_source, f"main.c missing long-recording token {token}", errors)

    for token in [
        "NOR_CMD_BLOCK_ERASE_64K",
        "NOR_DEFAULT_ERASE_TIMEOUT_MS",
        "companion_spi_nor_stm32wba_erase_64k",
    ]:
        require(token in spi_nor_text, f"shared SPI NOR core missing block erase token {token}", errors)

    for token in [
        "companion-type",
        '"Companion-Type" / "apps" / "windows" / "src-tauri"',
        "listener-type",
        "--submit-embedded-audio-wav-stream",
        "COMPANION_TYPE_DEBUG_TRANSCRIPT_FILE",
        "LISTENER_TYPE_DEBUG_TRANSCRIPT_FILE",
        "TYPE_POST_EXIT_TRANSCRIPT_GRACE_S",
        "type_empty_transcript_seen",
        "one-hour meetings need streaming, compression, or larger storage",
    ]:
        require(token in cli_text, f"recording-to-minutes CLI missing {token}", errors)

    for token in [
        "60 seconds",
        "1,920,000",
        "115,200,000",
        "companion_recording_to_minutes.py",
        "--asr-provider companion-type",
        "Companion Type",
        "Listener-Type",
    ]:
        require(token in docs, f"docs missing recording-to-minutes/capacity token {token}", errors)


def check_transcript_parser(errors: list[str]) -> None:
    module = load_cli_module()
    final_text = "这次需要确认 V K A E 和 Audio data 没有被重新解释。"
    log_text = "\n".join(
        [
            '[asr] server JSON: {"result":{"text":"这次","utterances":[{"definite":false,"text":"这次"}]}}',
            "source=backend.capsule event=emit_request state=Recording message=这次",
            '[asr] server JSON: {"result":{"text":"这次需要确认 VKA1和 Audio data 没有被重新解释","utterances":[{"definite":false,"text":"这次需要确认 VKA1和 Audio data 没有被重新解释"}]}}',
            f'[asr] server JSON: {{"result":{{"text":"{final_text}","utterances":[{{"definite":true,"text":"{final_text}"}}]}}}}',
            "source=backend.embedded_ble_session_actor event=asr_final transcript_empty=false",
            "submit-embedded-audio-streaming-file done: pcm_bytes=180000 missing_packets=0",
        ]
    )
    transcript = module.transcript_from_result_lines(log_text)
    require(transcript == final_text, f"ASR parser should prefer final transcript, got {transcript!r}", errors)

    final_server_json_log = "\n".join(
        [
            '[asr] preview server JSON: {"result":{"text":"这次","utterances":[{"definite":false,"text":"这次"}]}}',
            f'[asr] final server JSON: {{"result":{{"text":"{final_text}","utterances":[{{"definite":true,"text":"{final_text}"}}]}}}}',
        ]
    )
    transcript = module.transcript_from_result_lines(final_server_json_log)
    require(transcript == final_text, f"ASR parser should read final server JSON, got {transcript!r}", errors)

    truncated_json_log = "\n".join(
        [
            '[asr] server JSON: {"result":{"text":"这次需要","utterances":[{"definite":false,"text":"这次需要"}]}}',
            '[asr] server JSON: {"result":{"text":"这次需要确认 V K A E 和 Audio data 没有被重新解释。","utterances":[{"definite":true,',
            f"source=backend.capsule event=emit_request state=Polishing message={final_text}",
            "submit-embedded-audio-streaming-file done: pcm_bytes=180000 missing_packets=0",
        ]
    )
    transcript = module.transcript_from_result_lines(truncated_json_log)
    require(transcript == final_text, f"ASR parser should use final message fallback, got {transcript!r}", errors)

    empty_diagnostic_log = "\n".join(
        [
            "source=backend.capsule event=emit_request state=Done message=ASR returned empty transcript",
            "submit-embedded-audio-streaming-file done: pcm_bytes=51520 missing_packets=0",
        ]
    )
    transcript = module.transcript_from_result_lines(empty_diagnostic_log)
    require(transcript == "", f"ASR empty diagnostic must not become transcript, got {transcript!r}", errors)
    require(
        module.type_empty_transcript_seen(empty_diagnostic_log),
        "ASR empty diagnostic should end Type wait loop",
        errors,
    )

    chinese_empty_log = "source=backend.capsule event=emit_request state=Done message=没有识别到语音"
    transcript = module.transcript_from_result_lines(chinese_empty_log)
    require(transcript == "", f"Chinese ASR empty diagnostic must not become transcript, got {transcript!r}", errors)
    require(
        module.type_empty_transcript_seen(chinese_empty_log),
        "Chinese ASR empty diagnostic should end Type wait loop",
        errors,
    )

    type_busy_log = "source=backend.capsule event=emit_request state=Done message=当前已有听写会话在运行，暂不能提交嵌入式音频"
    transcript = module.transcript_from_result_lines(type_busy_log)
    require(transcript == "", f"Type busy diagnostic must not become transcript, got {transcript!r}", errors)
    transcript = module.prefer_transcript("", "当前已有听写会话在运行，暂不能提交嵌入式音频")
    require(transcript == "", f"Type busy debug file must not become transcript, got {transcript!r}", errors)

    type_status_log = "Listener BLE 已重连，音频通道已恢复。"
    transcript = module.prefer_transcript("", type_status_log)
    require(transcript == "", f"Type audio status must not become transcript, got {transcript!r}", errors)

    type_pairing_status_log = "Type 已完成本机自动配对，正在恢复音频通道..."
    transcript = module.transcript_from_result_lines(
        f"source=backend.capsule event=emit_request state=Done message={type_pairing_status_log}"
    )
    require(
        transcript == "",
        f"Type pairing/audio restore status must not become transcript, got {transcript!r}",
        errors,
    )
    transcript = module.prefer_transcript("", type_pairing_status_log)
    require(
        transcript == "",
        f"Type pairing/audio restore debug file must not become transcript, got {transcript!r}",
        errors,
    )


def check_type_cli_candidates_prefer_companion_type(errors: list[str]) -> None:
    module = load_cli_module()
    candidates = module.type_cli_candidates("companion-type")
    companion_index = next(
        (
            index
            for index, candidate in enumerate(candidates)
            if "Companion-Type" in candidate and "apps" in candidate and "windows" in candidate
        ),
        -1,
    )
    listener_index = next((index for index, candidate in enumerate(candidates) if "Listener-Type" in candidate), -1)
    require(companion_index >= 0, "Companion-Type apps/windows CLI candidate is missing", errors)
    require(listener_index >= 0, "Listener-Type compatibility candidate is missing", errors)
    if companion_index >= 0 and listener_index >= 0:
        require(
            companion_index < listener_index,
            "companion-type ASR must prefer Companion-Type apps/windows before Listener-Type fallback",
            errors,
        )


def check_type_asr_cli_uses_absolute_paths(errors: list[str]) -> None:
    module = load_cli_module()
    bundle_dir = WORKDIR / "type-asr-path-contract"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    audio_path = pathlib.Path(".cache") / "validation" / "listener-simulated.wav"
    captured: dict[str, Any] = {}

    original_type_cli_path = module.type_cli_path
    original_run_type_process = module.run_type_process

    def fake_run_type_process(
        command: list[str],
        env: dict[str, str],
        timeout_s: float,
        stdout_path: pathlib.Path,
        stderr_path: pathlib.Path,
        debug_transcript: pathlib.Path,
    ) -> tuple[str, str, dict[str, Any]]:
        captured["command"] = command
        captured["env"] = env
        captured["debug_transcript"] = debug_transcript
        return "模拟麦克风转写", "process_exited_with_transcript", {"timed_out": False}

    try:
        module.type_cli_path = lambda requested: "listener-type.exe"
        module.run_type_process = fake_run_type_process
        args = type(
            "Args",
            (),
            {
                "asr_provider": "listener-type",
                "type_cli": "listener-type",
                "type_timeout": 1.0,
                "require_transcript": True,
            },
        )()
        transcript, provider, result = module.run_type_asr(args, audio_path, bundle_dir)
    finally:
        module.type_cli_path = original_type_cli_path
        module.run_type_process = original_run_type_process

    require(transcript == "模拟麦克风转写", f"unexpected fake transcript: {transcript!r}", errors)
    require(provider == "listener_type", f"unexpected provider: {provider!r}", errors)
    require(result.get("status") == "PASS", f"unexpected fake Type ASR status: {result.get('status')}", errors)

    command = captured.get("command", [])
    require(bool(command), "Type ASR command was not captured", errors)
    if command:
        require(
            pathlib.Path(command[-1]).is_absolute(),
            f"Type ASR audio path must be absolute for single-instance desktop dispatch: {command[-1]!r}",
            errors,
        )

    env = captured.get("env", {})
    for key in ("LISTENER_TYPE_DEBUG_TRANSCRIPT_FILE", "COMPANION_TYPE_DEBUG_TRANSCRIPT_FILE"):
        value = str(env.get(key, ""))
        require(pathlib.Path(value).is_absolute(), f"{key} must be absolute, got {value!r}", errors)


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
    check_transcript_parser(errors)
    check_type_cli_candidates_prefer_companion_type(errors)
    check_type_asr_cli_uses_absolute_paths(errors)

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
