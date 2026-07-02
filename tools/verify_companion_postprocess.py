#!/usr/bin/env python3
"""Verify Companion recording postprocess and meeting-minutes artifacts."""

from __future__ import annotations

import json
import math
import pathlib
import struct
import subprocess
import sys
import wave
from typing import Any


sys.dont_write_bytecode = True
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.companion_pendant.postprocess.meeting_minutes import (  # noqa: E402
    build_meeting_minutes,
    render_minutes_markdown,
)


WORKDIR = REPO_ROOT / "docs" / "validation" / ".companion-postprocess-workdir"
FIXTURE = REPO_ROOT / "docs" / "validation" / "companion-recording-postprocess-fixture.json"
DOC = REPO_ROOT / "docs" / "companion_recording_postprocess.md"
CLI = REPO_ROOT / "tools" / "companion_recording_postprocess.py"

TRANSCRIPT = """Billy: 你好 Companion，今天确认 Companion 录音先走 SW3 开始停止，录到外部 flash，再通过 BLE 拉取。
oai1: 会议结论是 MCU 只保存音频和元数据，转写摘要在电脑或手机端处理。
Billy: 待办：oai1 负责做后处理脚本，明天验证会议纪要导出。
oai1: 问题是以后要不要接云端 ASR？需要保留隐私删除和本地原始音频路径。
"""


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def write_fixture_wav(path: pathlib.Path, duration_s: float = 1.2, sample_rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()
        for index in range(int(duration_s * sample_rate)):
            sample = int(1200 * math.sin(2.0 * math.pi * 440.0 * index / sample_rate))
            frames.extend(struct.pack("<h", sample))
        wav.writeframes(bytes(frames))


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def check_report(report: dict[str, Any], markdown: str, errors: list[str]) -> None:
    require(report["schema_version"] == 1, "schema_version mismatch", errors)
    require(report["postprocess_state"] == "minutes_ready", "minutes state not ready", errors)
    require(report["source"]["audio"]["sample_rate_hz"] == 16000, "sample rate missing from audio metadata", errors)
    require(report["source"]["audio"]["channels"] == 1, "channel count missing from audio metadata", errors)
    require(len(report["transcript"]["segments"]) >= 4, "transcript segmentation missing", errors)
    require(report["summary"]["decisions"], "decision extraction missing", errors)
    require(report["summary"]["action_items"], "action item extraction missing", errors)
    require(report["summary"]["questions"], "question extraction missing", errors)
    require(report["wake_word"]["state"] == "detected", "wake word detection missing", errors)
    require(report["wake_word"]["detections"], "wake word detection details missing", errors)
    require("SW3" in markdown, "Markdown missing SW3 source text", errors)
    require("唤醒词" in markdown, "Markdown missing wake-word section", errors)
    require("隐私" in markdown, "Markdown missing privacy section", errors)
    require("会议纪要" in markdown or "后处理" in markdown, "Markdown missing minutes context", errors)


def run_cli(wav_path: pathlib.Path, transcript_path: pathlib.Path, errors: list[str]) -> dict[str, Any]:
    out_dir = WORKDIR / "cli-output"
    command = [
        sys.executable,
        str(CLI),
        "--audio-path",
        str(wav_path),
        "--transcript-file",
        str(transcript_path),
        "--meeting-title",
        "Companion 录音后处理验证",
        "--wake-phrase",
        "你好 companion",
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
    require(completed.returncode == 0, f"CLI failed: {completed.stderr.strip()}", errors)
    json_path = out_dir / "companion-meeting-minutes.json"
    md_path = out_dir / "companion-meeting-minutes.md"
    require(json_path.exists(), "CLI JSON artifact missing", errors)
    require(md_path.exists(), "CLI Markdown artifact missing", errors)
    if not json_path.exists():
        return {}
    cli_report = load_json(json_path)
    check_report(cli_report, md_path.read_text(encoding="utf-8"), errors)
    return cli_report


def check_docs(errors: list[str]) -> None:
    require(DOC.exists(), "postprocess documentation missing", errors)
    if not DOC.exists():
        return
    text = DOC.read_text(encoding="utf-8")
    for token in [
        "PLAUD",
        "Otter",
        "Zoom",
        "transcript",
        "action_items",
        "delete_after_sync",
        "tools\\companion_recording_postprocess.py",
    ]:
        require(token in text, f"documentation missing token {token}", errors)


def main() -> int:
    errors: list[str] = []
    if WORKDIR.exists():
        for item in sorted(WORKDIR.glob("**/*"), reverse=True):
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                item.rmdir()
    WORKDIR.mkdir(parents=True, exist_ok=True)
    wav_path = WORKDIR / "companion-postprocess-source.wav"
    transcript_path = WORKDIR / "transcript.txt"
    write_fixture_wav(wav_path)
    transcript_path.write_text(TRANSCRIPT, encoding="utf-8")

    report = build_meeting_minutes(
        audio_path=wav_path,
        transcript_text=TRANSCRIPT,
        transcript_provider="synthetic_fixture_text",
        meeting_title="Companion 录音后处理验证",
    )
    markdown = render_minutes_markdown(report)
    check_report(report, markdown, errors)
    cli_report = run_cli(wav_path, transcript_path, errors)
    check_docs(errors)

    fixture = {
        "schema_version": 1,
        "status": "PASS" if not errors else "FAIL",
        "mode": "synthetic-audio-with-provided-transcript",
        "source_wav": str(wav_path),
        "direct_report": report,
        "cli_report": cli_report,
        "checks": {
            "minutes_ready": report.get("postprocess_state") == "minutes_ready",
            "decision_extracted": bool(report.get("summary", {}).get("decisions")),
            "action_item_extracted": bool(report.get("summary", {}).get("action_items")),
            "question_extracted": bool(report.get("summary", {}).get("questions")),
            "wake_word_detected": report.get("wake_word", {}).get("state") == "detected",
            "markdown_generated": "# Companion" in markdown,
            "docs_updated": DOC.exists(),
        },
    }
    FIXTURE.write_text(json.dumps(fixture, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

    if errors:
        print("FAIL: Companion postprocess checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion postprocess verified; fixture written to {FIXTURE.relative_to(REPO_ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
