#!/usr/bin/env python3
"""Run Companion recording source audio through ASR and meeting-minutes export."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import threading
import time
from typing import Any


sys.dont_write_bytecode = True
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.companion_pendant.postprocess.meeting_minutes import (  # noqa: E402
    build_meeting_minutes,
    render_minutes_markdown,
)


RAW_PCM_BYTES_PER_SECOND = 16000 * 2
NUCLEO_RAW_FLASH_MAX_SECONDS = 60


class ChainToMinutesError(RuntimeError):
    """Operator-facing chain failure."""


def utc_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ChainToMinutesError(f"cannot read JSON artifact {path}: {exc}") from exc


def resolve_chain_artifact_path(value: str, chain_path: pathlib.Path) -> pathlib.Path:
    path = pathlib.Path(str(value))
    if path.is_absolute():
        return path

    candidates = [
        chain_path.parent / path,
        REPO_ROOT / path,
        pathlib.Path.cwd() / path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def find_audio_from_chain(chain: dict[str, Any], chain_path: pathlib.Path) -> pathlib.Path | None:
    artifacts = chain.get("artifacts", {})
    if isinstance(artifacts, dict):
        for key in ("wav_path", "pcm_path"):
            value = artifacts.get(key)
            if value:
                return resolve_chain_artifact_path(str(value), chain_path)

    for operation in chain.get("operations", []):
        if not isinstance(operation, dict):
            continue
        for key in ("wav_path", "pcm_path"):
            value = operation.get(key)
            if value:
                return resolve_chain_artifact_path(str(value), chain_path)
    return None


def resolve_bundle_dir(output_dir: pathlib.Path | None) -> pathlib.Path:
    out_dir = output_dir or (REPO_ROOT / ".cache" / "validation" / f"companion-recording-to-minutes-{utc_stamp()}")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def run_command(command: list[str], cwd: pathlib.Path, timeout_s: float, log_prefix: pathlib.Path) -> dict[str, Any]:
    stdout_path = log_prefix.with_suffix(".stdout.log")
    stderr_path = log_prefix.with_suffix(".stderr.log")
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_s,
            check=False,
        )
        stdout_path.write_text(completed.stdout, encoding="utf-8", errors="replace")
        stderr_path.write_text(completed.stderr, encoding="utf-8", errors="replace")
        return {
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "command": command,
            "exit_code": completed.returncode,
            "duration_s": round(time.monotonic() - started, 3),
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "stdout_tail": "\n".join(completed.stdout.splitlines()[-20:]),
            "stderr_tail": "\n".join(completed.stderr.splitlines()[-20:]),
        }
    except subprocess.TimeoutExpired as exc:
        stdout_text = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr_text = exc.stderr if isinstance(exc.stderr, str) else ""
        stdout_path.write_text(stdout_text, encoding="utf-8", errors="replace")
        stderr_path.write_text(stderr_text, encoding="utf-8", errors="replace")
        return {
            "status": "TIMEOUT",
            "command": command,
            "exit_code": None,
            "duration_s": round(time.monotonic() - started, 3),
            "timeout_s": timeout_s,
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "stdout_tail": "\n".join(stdout_text.splitlines()[-20:]),
            "stderr_tail": "\n".join(stderr_text.splitlines()[-20:]),
        }


def run_recording_source(args: argparse.Namespace, bundle_dir: pathlib.Path) -> tuple[pathlib.Path, dict[str, Any] | None, str | None, dict[str, Any]]:
    selected = [bool(args.audio_path), bool(args.recording_chain), bool(args.ble_auto), bool(args.sw3)]
    if sum(1 for value in selected if value) != 1:
        raise ChainToMinutesError("choose exactly one source: --audio-path, --recording-chain, --ble-auto, or --sw3")

    if (args.ble_auto or args.sw3) and float(args.record_seconds) > NUCLEO_RAW_FLASH_MAX_SECONDS:
        raw_bytes = int(float(args.record_seconds) * RAW_PCM_BYTES_PER_SECOND)
        raise ChainToMinutesError(
            "current NUCLEO raw PCM flash cap is 60 seconds; "
            f"{args.record_seconds:g}s would need {raw_bytes} bytes before headers. "
            "Use streaming, compression, or larger storage for one-hour meetings."
        )

    if args.audio_path:
        audio_path = args.audio_path
        if not audio_path.exists():
            raise ChainToMinutesError(f"audio path does not exist: {audio_path}")
        return audio_path, None, None, {"source_mode": "audio_path", "status": "PASS"}

    if args.recording_chain:
        chain = load_json(args.recording_chain)
        audio_path = find_audio_from_chain(chain, args.recording_chain)
        if audio_path is None:
            raise ChainToMinutesError(f"recording chain artifact has no wav_path or pcm_path: {args.recording_chain}")
        if not audio_path.exists():
            raise ChainToMinutesError(f"audio path from chain does not exist: {audio_path}")
        return audio_path, chain, str(args.recording_chain), {
            "source_mode": "recording_chain",
            "status": "PASS",
            "chain_artifact": str(args.recording_chain),
        }

    if args.ble_auto:
        chain_dir = bundle_dir / "recording-chain"
        command = [
            sys.executable,
            str(REPO_ROOT / "tools" / "companion_flash_recording_chain.py"),
            "--name",
            args.name,
            "--timeout",
            str(args.timeout),
            "--notify-timeout",
            str(args.notify_timeout),
            "--record-seconds",
            str(args.record_seconds),
            "--chunk-bytes",
            str(args.chunk_bytes),
            "--artifact-dir",
            str(chain_dir),
        ]
        if args.address:
            command.extend(["--address", args.address])
        command_result = run_command(command, REPO_ROOT, args.source_timeout, bundle_dir / "recording-chain")
        chain_path = chain_dir / "companion-flash-recording-chain.json"
        if command_result["status"] != "PASS" or not chain_path.exists():
            raise ChainToMinutesError(f"BLE recording chain failed; log={command_result}")
        chain = load_json(chain_path)
        audio_path = find_audio_from_chain(chain, chain_path)
        if audio_path is None or not audio_path.exists():
            raise ChainToMinutesError(f"BLE recording chain did not export audio; artifact={chain_path}")
        return audio_path, chain, str(chain_path), {
            "source_mode": "ble_auto",
            "status": "PASS",
            "chain_artifact": str(chain_path),
            "command_result": command_result,
        }

    chain_dir = bundle_dir / "sw3-button-recording-chain"
    command = [
        sys.executable,
        str(REPO_ROOT / "tools" / "companion_button_recording_chain.py"),
        "--name",
        args.name,
        "--timeout",
        str(args.timeout),
        "--notify-timeout",
        str(args.notify_timeout),
        "--record-seconds",
        str(args.record_seconds),
        "--chunk-bytes",
        str(args.chunk_bytes),
        "--artifact-dir",
        str(chain_dir),
        "--button-timeout",
        str(args.button_timeout),
    ]
    if args.address:
        command.extend(["--address", args.address])
    if args.programmer:
        command.extend(["--programmer", args.programmer])
    if args.serial_port:
        command.extend(["--serial-port", args.serial_port])
    if args.no_prompts:
        command.append("--no-prompts")
    if args.no_serial_button_monitor:
        command.append("--no-serial-button-monitor")
    command_result = run_command(command, REPO_ROOT, args.source_timeout, bundle_dir / "sw3-button-recording-chain")
    chain_path = chain_dir / "companion-button-recording-chain.json"
    if command_result["status"] != "PASS" or not chain_path.exists():
        raise ChainToMinutesError(f"SW3 recording chain failed; log={command_result}")
    chain = load_json(chain_path)
    audio_path = find_audio_from_chain(chain, chain_path)
    if audio_path is None or not audio_path.exists():
        raise ChainToMinutesError(f"SW3 recording chain did not export audio; artifact={chain_path}")
    return audio_path, chain, str(chain_path), {
        "source_mode": "sw3",
        "status": "PASS",
        "chain_artifact": str(chain_path),
        "command_result": command_result,
    }


def transcript_from_json(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("final_text", "raw_transcript", "text"):
            found = value.get(key)
            if isinstance(found, str) and found.strip():
                return found.strip()
        for key in ("transcript", "result", "data"):
            found = transcript_from_json(value.get(key))
            if found:
                return found
    if isinstance(value, list):
        pieces = [transcript_from_json(item) for item in value]
        return " ".join(piece for piece in pieces if piece).strip()
    return ""


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)


def transcript_from_result_lines(text: str) -> str:
    for line in text.splitlines():
        line = strip_ansi(line)
        if "result_json=" not in line:
            continue
        _, raw_json = line.split("result_json=", 1)
        try:
            transcript = transcript_from_json(json.loads(raw_json))
        except json.JSONDecodeError:
            continue
        if transcript:
            return transcript

    patterns = [
        r"final_text(?:=|:)\s*(?P<value>.+)$",
        r"raw_transcript(?:=|:)\s*(?P<value>.+)$",
    ]
    for line in text.splitlines():
        line = strip_ansi(line)
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                value = match.group("value").strip().strip('"')
                if value:
                    return value

        if "[asr] server JSON:" in line:
            _, raw_json = line.split("[asr] server JSON:", 1)
            try:
                transcript = transcript_from_json(json.loads(raw_json.strip()))
            except json.JSONDecodeError:
                match = re.search(r'"text"\s*:\s*"(?P<value>[^"]+)"', raw_json)
                transcript = match.group("value").strip() if match else ""
            if transcript:
                return transcript

        match = re.search(r"\bmessage=(?P<value>.+)$", line)
        if match:
            value = match.group("value").strip()
            if value and value != "-" and "失败" not in value:
                return value
    return ""


def run_listener_type_process(
    command: list[str],
    env: dict[str, str],
    timeout_s: float,
    stdout_path: pathlib.Path,
    stderr_path: pathlib.Path,
    debug_transcript: pathlib.Path,
) -> tuple[str, str, dict[str, Any]]:
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    started = time.monotonic()
    app_log_path = pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "Listener Type" / "Logs" / "listener-type.log"
    app_log_start = app_log_path.stat().st_size if app_log_path.exists() else 0
    app_log_capture_path = stdout_path.with_name("listener-type-app.log")

    def read_app_log_delta() -> str:
        if not app_log_path.exists():
            return ""
        try:
            with app_log_path.open("r", encoding="utf-8", errors="replace") as handle:
                if app_log_path.stat().st_size >= app_log_start:
                    handle.seek(app_log_start)
                return handle.read()
        except OSError:
            return ""

    process = subprocess.Popen(
        command,
        cwd=REPO_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
    )

    def read_lines(stream: Any, bucket: list[str]) -> None:
        try:
            for line in iter(stream.readline, ""):
                bucket.append(line)
        finally:
            try:
                stream.close()
            except Exception:
                pass

    threads = [
        threading.Thread(target=read_lines, args=(process.stdout, stdout_lines), daemon=True),
        threading.Thread(target=read_lines, args=(process.stderr, stderr_lines), daemon=True),
    ]
    for thread in threads:
        thread.start()

    completion_reason = ""
    transcript = ""
    process_exited_at: float | None = None
    deadline = time.monotonic() + float(timeout_s)
    while time.monotonic() < deadline:
        app_log_text = read_app_log_delta()
        combined = "".join(stdout_lines) + "\n" + "".join(stderr_lines) + "\n" + app_log_text
        transcript = debug_transcript.read_text(encoding="utf-8").strip() if debug_transcript.exists() else ""
        if not transcript:
            transcript = transcript_from_result_lines(combined)
        if transcript and "submit-embedded-audio-streaming-file done" in combined:
            completion_reason = "listener_type_cli_done"
            break
        if transcript and "event=asr_final" in combined:
            completion_reason = "listener_type_asr_final"
            break
        if process.poll() is not None:
            if transcript:
                completion_reason = "process_exited_with_transcript"
                break
            if process_exited_at is None:
                process_exited_at = time.monotonic()
            if time.monotonic() - process_exited_at > 10:
                completion_reason = "process_exited"
                break
        time.sleep(0.2)

    timed_out = not completion_reason and process.poll() is None
    terminated_after_completion = False
    killed_after_timeout = False
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
            terminated_after_completion = bool(completion_reason)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
            killed_after_timeout = True

    for thread in threads:
        thread.join(timeout=1)

    stdout_text = "".join(stdout_lines)
    stderr_text = "".join(stderr_lines)
    app_log_text = read_app_log_delta()
    stdout_path.write_text(stdout_text, encoding="utf-8", errors="replace")
    stderr_path.write_text(stderr_text, encoding="utf-8", errors="replace")
    app_log_capture_path.write_text(app_log_text, encoding="utf-8", errors="replace")
    if not transcript:
        transcript = debug_transcript.read_text(encoding="utf-8").strip() if debug_transcript.exists() else ""
    if not transcript:
        transcript = transcript_from_result_lines(stdout_text + "\n" + stderr_text + "\n" + app_log_text)

    return transcript, completion_reason, {
        "command": command,
        "exit_code": process.returncode,
        "duration_s": round(time.monotonic() - started, 3),
        "timeout_s": timeout_s,
        "timed_out": timed_out,
        "completion_reason": completion_reason,
        "terminated_after_completion": terminated_after_completion,
        "killed_after_timeout": killed_after_timeout,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "app_log_path": str(app_log_capture_path),
        "app_log_source": str(app_log_path),
        "stdout_tail": "\n".join(stdout_text.splitlines()[-20:]),
        "stderr_tail": "\n".join(stderr_text.splitlines()[-20:]),
        "app_log_tail": "\n".join(app_log_text.splitlines()[-20:]),
    }


def listener_type_cli_path(requested: str) -> str | None:
    requested_path = pathlib.Path(requested)
    if requested_path.exists():
        return str(requested_path)
    found = shutil.which(requested)
    if found:
        return found
    if not requested.lower().endswith(".exe"):
        found = shutil.which(requested + ".exe")
        if found:
            return found
    return None


def listener_type_flag_for_audio(audio_path: pathlib.Path) -> str:
    suffix = audio_path.suffix.lower()
    if suffix == ".wav":
        return "--submit-embedded-audio-wav-stream"
    if suffix in {".pcm", ".raw"}:
        return "--submit-embedded-audio-pcm16le-stream"
    return "--submit-embedded-audio-stream"


def run_listener_type_asr(args: argparse.Namespace, audio_path: pathlib.Path, bundle_dir: pathlib.Path) -> tuple[str, str, dict[str, Any]]:
    cli_path = listener_type_cli_path(args.listener_type_cli)
    debug_transcript = bundle_dir / "listener-type-transcript.txt"
    if cli_path is None:
        result = {
            "provider": "listener_type",
            "status": "SKIPPED",
            "reason": f"listener-type CLI not found: {args.listener_type_cli}",
            "transcript_debug_file": str(debug_transcript),
        }
        if args.require_transcript:
            raise ChainToMinutesError(result["reason"])
        return "", "listener_type_pending", result

    command = [cli_path, listener_type_flag_for_audio(audio_path), str(audio_path)]
    env = os.environ.copy()
    env.setdefault("LISTENER_TYPE_HIDE_MAIN_ON_START", "1")
    env.setdefault("LISTENER_TYPE_DISABLE_BACKGROUND_BLE", "1")
    env["LISTENER_TYPE_DEBUG_TRANSCRIPT_FILE"] = str(debug_transcript)

    stdout_path = bundle_dir / "listener-type-asr.stdout.log"
    stderr_path = bundle_dir / "listener-type-asr.stderr.log"
    transcript, completion_reason, process_result = run_listener_type_process(
        command,
        env,
        args.listener_type_timeout,
        stdout_path,
        stderr_path,
        debug_transcript,
    )
    status = "PASS" if transcript and completion_reason else "NO_TRANSCRIPT"
    if process_result["timed_out"] and not transcript:
        status = "TIMEOUT"
    result = {
        "provider": "listener_type",
        "status": status,
        "transcript_debug_file": str(debug_transcript),
        **process_result,
    }
    if args.require_transcript and not transcript:
        raise ChainToMinutesError(f"listener-type ASR did not produce transcript; result={result}")
    if args.require_transcript and status == "TIMEOUT":
        raise ChainToMinutesError(f"listener-type ASR timed out before transcript; result={result}")
    return transcript, "listener_type" if transcript else "listener_type_pending", result


def resolve_transcript(args: argparse.Namespace, audio_path: pathlib.Path, bundle_dir: pathlib.Path) -> tuple[str, str, dict[str, Any]]:
    if args.transcript_text and args.transcript_file:
        raise ChainToMinutesError("choose either --transcript-text or --transcript-file, not both")
    if args.transcript_file:
        text = args.transcript_file.read_text(encoding="utf-8")
        return text, f"file:{args.transcript_file}", {
            "provider": "provided_file",
            "status": "PASS",
            "transcript_file": str(args.transcript_file),
        }
    if args.transcript_text:
        return args.transcript_text, "provided_text", {"provider": "provided_text", "status": "PASS"}
    if args.asr_provider == "listener-type":
        return run_listener_type_asr(args, audio_path, bundle_dir)
    return "", "pending_transcription", {
        "provider": args.asr_provider,
        "status": "SKIPPED",
        "reason": "no transcript was provided and no ASR provider was requested",
    }


def write_minutes(report: dict[str, Any], bundle_dir: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    json_path = bundle_dir / "companion-meeting-minutes.json"
    markdown_path = bundle_dir / "companion-meeting-minutes.md"
    report = dict(report)
    report["artifacts"] = {
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
    }
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(render_minutes_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def write_chain_report(report: dict[str, Any], bundle_dir: pathlib.Path) -> pathlib.Path:
    path = bundle_dir / "companion-recording-to-minutes.json"
    report = dict(report)
    report.setdefault("artifacts", {})["report_json"] = str(path)
    path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_argument_group("source")
    source.add_argument("--audio-path", type=pathlib.Path, default=None, help="Existing WAV/PCM file")
    source.add_argument("--recording-chain", type=pathlib.Path, default=None, help="Existing Companion recording-chain JSON")
    source.add_argument("--ble-auto", action="store_true", help="Run BLE recording_control start/stop/pull before minutes")
    source.add_argument("--sw3", action="store_true", help="Run physical SW3 button recording chain before minutes")
    source.add_argument("--name", default="companion", help="BLE local name substring")
    source.add_argument("--address", default="", help="Optional BLE address")
    source.add_argument("--timeout", type=float, default=8.0, help="BLE scan/connect timeout")
    source.add_argument("--notify-timeout", type=float, default=20.0, help="GATT notify timeout")
    source.add_argument("--record-seconds", type=float, default=10.0, help="BLE/SW3 capture dwell; current raw flash cap is 60 seconds")
    source.add_argument("--chunk-bytes", type=int, default=180, help="Requested recording bytes per BLE pull")
    source.add_argument("--source-timeout", type=float, default=300.0, help="Timeout for nested recording-chain command")
    source.add_argument("--programmer", default="", help="Optional STM32_Programmer_CLI.exe path for --sw3 reset")
    source.add_argument("--serial-port", default="", help="Optional ST-LINK VCP serial port for --sw3 button monitor")
    source.add_argument("--button-timeout", type=float, default=90.0, help="Per-button prompt timeout for --sw3")
    source.add_argument("--no-prompts", action="store_true", help="Pass --no-prompts to --sw3 chain")
    source.add_argument("--no-serial-button-monitor", action="store_true", help="Pass --no-serial-button-monitor to --sw3 chain")

    transcript = parser.add_argument_group("transcript")
    transcript.add_argument("--transcript-file", type=pathlib.Path, default=None, help="UTF-8 transcript text")
    transcript.add_argument("--transcript-text", default="", help="Inline transcript text for simulation/fixtures")
    transcript.add_argument(
        "--asr-provider",
        choices=("none", "listener-type"),
        default="none",
        help="Optional ASR provider when no transcript is supplied",
    )
    transcript.add_argument("--listener-type-cli", default="listener-type", help="Listener-Type CLI path/name")
    transcript.add_argument("--listener-type-timeout", type=float, default=180.0, help="Listener-Type ASR timeout")
    transcript.add_argument("--require-transcript", action="store_true", help="Fail if ASR/provided transcript is empty")

    output = parser.add_argument_group("output")
    output.add_argument("--meeting-title", default="", help="Optional minutes title override")
    output.add_argument("--wake-phrase", action="append", default=None, help="Wake phrase to detect; repeatable")
    output.add_argument("--output-dir", type=pathlib.Path, default=None, help="Bundle output directory")
    output.add_argument("--json", action="store_true", help="Print JSON report to stdout")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    bundle_dir = resolve_bundle_dir(args.output_dir)
    try:
        audio_path, chain, source_artifact, source_result = run_recording_source(args, bundle_dir)
        transcript_text, transcript_provider, asr_result = resolve_transcript(args, audio_path, bundle_dir)
        minutes = build_meeting_minutes(
            audio_path=audio_path,
            transcript_text=transcript_text,
            transcript_provider=transcript_provider,
            recording_chain=chain,
            source_artifact=source_artifact,
            meeting_title=args.meeting_title or None,
            wake_phrases=args.wake_phrase,
        )
        if args.require_transcript and minutes["postprocess_state"] != "minutes_ready":
            raise ChainToMinutesError("transcript is required but the minutes output still needs transcription")
        minutes_json, minutes_markdown = write_minutes(minutes, bundle_dir)
        status = "PASS" if minutes["postprocess_state"] == "minutes_ready" else "PASS_NEEDS_TRANSCRIPTION"
        report = {
            "schema_version": 1,
            "status": status,
            "mode": "companion_recording_to_minutes",
            "started_at": utc_now(),
            "bundle_dir": str(bundle_dir),
            "source": {
                "audio_path": str(audio_path),
                "recording_chain_artifact": source_artifact,
                "result": source_result,
            },
            "asr": asr_result,
            "minutes": minutes,
            "capacity": {
                "raw_pcm_bytes_per_second": RAW_PCM_BYTES_PER_SECOND,
                "nucleo_raw_flash_max_seconds": NUCLEO_RAW_FLASH_MAX_SECONDS,
                "nucleo_raw_flash_max_bytes": RAW_PCM_BYTES_PER_SECOND * NUCLEO_RAW_FLASH_MAX_SECONDS,
                "one_hour_raw_pcm_bytes": RAW_PCM_BYTES_PER_SECOND * 3600,
                "one_hour_note": "raw 16 kHz mono PCM16 one-hour meetings need streaming, compression, or larger storage",
            },
            "artifacts": {
                "minutes_json": str(minutes_json),
                "minutes_markdown": str(minutes_markdown),
            },
        }
        report_path = write_chain_report(report, bundle_dir)
        report["artifacts"]["report_json"] = str(report_path)
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
        else:
            print(
                "PASS: Companion recording-to-minutes chain complete; "
                f"status={status}; report={report_path}; minutes={minutes_markdown}"
            )
        return 0
    except ChainToMinutesError as exc:
        report = {
            "schema_version": 1,
            "status": "FAIL",
            "mode": "companion_recording_to_minutes",
            "finished_at": utc_now(),
            "bundle_dir": str(bundle_dir),
            "error": str(exc),
        }
        report_path = write_chain_report(report, bundle_dir)
        print(f"FAIL: Companion recording-to-minutes chain failed; report={report_path}", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
