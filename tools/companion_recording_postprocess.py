#!/usr/bin/env python3
"""Generate host-side meeting minutes from a Companion pulled recording."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
from typing import Any


sys.dont_write_bytecode = True
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.companion_pendant.postprocess.meeting_minutes import (  # noqa: E402
    build_meeting_minutes,
    render_minutes_markdown,
)


class PostprocessError(RuntimeError):
    """Operator-facing validation failure."""


def utc_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise PostprocessError(f"cannot read JSON artifact {path}: {exc}") from exc


def find_audio_from_chain(chain: dict[str, Any], chain_path: pathlib.Path) -> pathlib.Path | None:
    artifacts = chain.get("artifacts", {})
    for key in ("wav_path", "pcm_path"):
        value = artifacts.get(key) if isinstance(artifacts, dict) else None
        if value:
            path = pathlib.Path(str(value))
            return path if path.is_absolute() else (chain_path.parent / path)
    for operation in chain.get("operations", []):
        for key in ("wav_path", "pcm_path"):
            value = operation.get(key)
            if value:
                path = pathlib.Path(str(value))
                return path if path.is_absolute() else (chain_path.parent / path)
    return None


def load_transcript(args: argparse.Namespace) -> tuple[str, str]:
    if args.transcript_text and args.transcript_file:
        raise PostprocessError("choose either --transcript-text or --transcript-file, not both")
    if args.transcript_file:
        return args.transcript_file.read_text(encoding="utf-8"), f"file:{args.transcript_file}"
    if args.transcript_text:
        return args.transcript_text, "provided_text"
    return "", "pending_transcription"


def resolve_audio(args: argparse.Namespace) -> tuple[pathlib.Path, dict[str, Any] | None, str | None]:
    chain = None
    source_artifact = None
    if args.recording_chain:
        chain = load_json(args.recording_chain)
        source_artifact = str(args.recording_chain)
    if args.audio_path:
        audio_path = args.audio_path
    elif chain:
        audio_path = find_audio_from_chain(chain, args.recording_chain)
        if audio_path is None:
            raise PostprocessError(f"recording chain artifact has no wav_path or pcm_path: {args.recording_chain}")
    else:
        raise PostprocessError("provide --audio-path or --recording-chain")
    if not audio_path.exists():
        raise PostprocessError(f"audio path does not exist: {audio_path}")
    return audio_path, chain, source_artifact


def write_report(report: dict[str, Any], out_dir: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "companion-meeting-minutes.json"
    md_path = out_dir / "companion-meeting-minutes.md"
    report = dict(report)
    report["artifacts"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(render_minutes_markdown(report), encoding="utf-8")
    return json_path, md_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recording-chain", type=pathlib.Path, default=None, help="Companion recording chain JSON artifact")
    parser.add_argument("--audio-path", type=pathlib.Path, default=None, help="Pulled WAV or PCM file")
    parser.add_argument("--transcript-file", type=pathlib.Path, default=None, help="UTF-8 transcript text")
    parser.add_argument("--transcript-text", default="", help="Inline transcript text for simulation/fixtures")
    parser.add_argument("--meeting-title", default="", help="Optional minutes title override")
    parser.add_argument(
        "--wake-phrase",
        action="append",
        default=None,
        help="Wake phrase to detect in transcript text; repeat for multiple phrases.",
    )
    parser.add_argument(
        "--output-dir",
        type=pathlib.Path,
        default=None,
        help="Output directory; defaults to .cache/validation/companion-recording-postprocess-<timestamp>",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON report to stdout.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        audio_path, chain, source_artifact = resolve_audio(args)
        transcript, provider = load_transcript(args)
        report = build_meeting_minutes(
            audio_path=audio_path,
            transcript_text=transcript,
            transcript_provider=provider,
            recording_chain=chain,
            source_artifact=source_artifact,
            meeting_title=args.meeting_title or None,
            wake_phrases=args.wake_phrase,
        )
        out_dir = args.output_dir or (REPO_ROOT / ".cache" / "validation" / f"companion-recording-postprocess-{utc_stamp()}")
        json_path, md_path = write_report(report, out_dir)
        report["artifacts"] = {"json_path": str(json_path), "markdown_path": str(md_path)}
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
        else:
            print(
                "PASS: Companion recording postprocess complete; "
                f"state={report['postprocess_state']}; json={json_path}; markdown={md_path}"
            )
        return 0
    except PostprocessError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
