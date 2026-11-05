#!/usr/bin/env python3
"""Unit tests for the deterministic meeting-minutes extractor.

These guard the board-mic air-path extraction logic that was hardened on
2026-08-07 (traditional->simplified normalization, stronger decision/action
cues, the 没问题 question-negation exclusion, and Chinese-comma splitting).
Without these, a future edit to the cue tables or the trad->simp map silently
regresses real transcripts (e.g. a missing 須->须 once let "必須" miss the
action-item cue). Run directly or via pytest:

    python app/companion_pendant/postprocess/tests/test_meeting_minutes.py
    pytest app/companion_pendant/postprocess/tests/test_meeting_minutes.py

The regression transcript below is the real faster_whisper medium+vad0+prompt
output from board-mic capture id=3 (minutes_id3.md), including the traditional
characters and the ASR word errors the extractor must still route around.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile
import wave

# Make app.companion_pendant.postprocess.meeting_minutes importable when run
# directly (no pytest). parents[4] == Companion-Firmware repo root.
_REPO = pathlib.Path(__file__).resolve().parents[4]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from app.companion_pendant.postprocess.meeting_minutes import (  # noqa: E402
    build_meeting_minutes,
    render_minutes_markdown,
    sentence_contains,
    split_sentence_text,
    to_simplified,
)

# Decision/action cues live in meeting_minutes; import for direct assertions.
from app.companion_pendant.postprocess.meeting_minutes import (  # noqa: E402
    ACTION_CUES,
    DECISION_CUES,
    QUESTION_CUES,
    QUESTION_NEGATIONS,
)


def _make_tiny_wav(path: pathlib.Path, seconds: float = 1.0) -> None:
    """Write a minimal valid mono PCM16 16 kHz WAV so audio_metadata() works."""
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * int(16000 * seconds))


# Real board-mic air-path transcript (faster_whisper medium, vad0, zh domain
# prompt, id=3). Traditional chars + ASR word errors intact on purpose.
REGRESSION_TRANSCRIPT = (
    "这个版本重点把录音稳定性搞定,Draw必须为零。固件被G3调好了,长度没问题。"
    "決定這版默認Opus16單聲道,失敗必須Fail Closed行動,留意本周五說明"
)


# ---------------------------------------------------------------- to_simplified
def test_to_simplified_covers_cue_chars():
    # Every character these tests rely on must actually normalize.
    assert to_simplified("決定這版默認必須沒問題單") == "决定这版默认必须没问题单"


def test_to_simplified_passes_simplified_through():
    assert to_simplified("决定默认") == "决定默认"
    assert to_simplified("english OK 123") == "english OK 123"


# --------------------------------------------------------- sentence_contains
def test_sentence_contains_matches_simplified_cue():
    assert sentence_contains("决定用Opus16", DECISION_CUES) is True


def test_sentence_contains_matches_traditional_cue():
    # 決定/默認/這版 are traditional but must still hit the simplified cues.
    assert sentence_contains("決定這版默認Opus16", DECISION_CUES) is True


def test_sentence_contains_action_traditional_must():
    # 必須 -> 必须, 本週 -> 本周 must both match the action cue set.
    assert sentence_contains("失敗必須Fail Closed", ACTION_CUES) is True
    assert sentence_contains("留意本週五說明", ACTION_CUES) is True


def test_sentence_contains_excludes_question_negation():
    # "長度沒問題" contains the 問題/问题 cue but is a reassurance, not a
    # question. The negation exclusion must fire on the traditional form too.
    assert sentence_contains("長度沒問題", QUESTION_CUES, QUESTION_NEGATIONS) is False
    assert sentence_contains("长度没问题", QUESTION_CUES, QUESTION_NEGATIONS) is False


def test_sentence_contains_real_question_still_matches():
    assert sentence_contains("是否要上线?", QUESTION_CUES, QUESTION_NEGATIONS) is True


def test_sentence_contains_no_cue_returns_false():
    assert sentence_contains("固件被调好了", DECISION_CUES) is False


# -------------------------------------------------------- split_sentence_text
def test_split_chinese_comma():
    parts = split_sentence_text("这个版本重点,Draw必须为零,固件被调好了")
    # Chinese full-width commas must split; each non-empty piece survives.
    assert "这个版本重点" in parts
    assert "Draw必须为零" in parts
    assert "固件被调好了" in parts


def test_split_period_and_comma_mix():
    parts = split_sentence_text("先决定。然后,执行")
    assert "先决定" in parts
    assert "然后" in parts or "然后,执行" in parts


# ------------------------------------------------------- build_meeting_minutes
def test_build_minutes_extracts_traditional_decision(tmp_path: pathlib.Path):
    wav = tmp_path / "clip.wav"
    _make_tiny_wav(wav)
    report = build_meeting_minutes(audio_path=wav, transcript_text=REGRESSION_TRANSCRIPT)
    decisions = report["summary"]["decisions"]
    assert len(decisions) == 1, f"expected the Opus16 decision, got {decisions}"
    assert "默认" in to_simplified(decisions[0]["text"]) or "这版" in to_simplified(decisions[0]["text"])


def test_build_minutes_extracts_actions_including_traditional(tmp_path: pathlib.Path):
    wav = tmp_path / "clip.wav"
    _make_tiny_wav(wav)
    report = build_meeting_minutes(audio_path=wav, transcript_text=REGRESSION_TRANSCRIPT)
    actions = report["summary"]["action_items"]
    action_texts = "".join(to_simplified(a["text"]) for a in actions)
    # Must catch the simplified "必须为零", traditional "失败必须Fail Closed",
    # and the 本周 timeframe commitment.
    assert "必须为零" in action_texts
    assert "失败必须" in action_texts and "fail closed" in action_texts.lower()
    assert "本周" in action_texts
    assert len(actions) == 3, f"expected 3 actions, got {actions}"


def test_build_minutes_excludes_no_problem_question(tmp_path: pathlib.Path):
    wav = tmp_path / "clip.wav"
    _make_tiny_wav(wav)
    report = build_meeting_minutes(audio_path=wav, transcript_text=REGRESSION_TRANSCRIPT)
    questions = report["summary"]["questions"]
    # "長度沒問題" must NOT become a question despite containing 問題.
    assert all("问题" not in to_simplified(q["text"]) for q in questions), questions
    assert questions == [], f"expected no questions, got {questions}"


def test_build_minutes_markdown_renders_sections(tmp_path: pathlib.Path):
    wav = tmp_path / "clip.wav"
    _make_tiny_wav(wav)
    report = build_meeting_minutes(audio_path=wav, transcript_text=REGRESSION_TRANSCRIPT)
    md = render_minutes_markdown(report)
    assert "## 决策" in md
    assert "## 待办" in md
    assert "## 转写" in md
    # The decision text (traditional in source) must appear in the rendered body.
    assert "默認" in md or "默认" in md


def test_build_minutes_state_needs_transcription_when_empty(tmp_path: pathlib.Path):
    wav = tmp_path / "clip.wav"
    _make_tiny_wav(wav)
    report = build_meeting_minutes(audio_path=wav, transcript_text=None)
    assert report["postprocess_state"] == "needs_transcription"
    assert report["summary"]["decisions"] == []


# --------------------------------------------------------------------- runner
def _run_all() -> int:
    failures: list[str] = []
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="mm_test_"))
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            # Tests declared with tmp_path take a Path; synthesize one each.
            import inspect
            if "tmp_path" in inspect.signature(fn).parameters:
                d = tmp / name
                d.mkdir(parents=True, exist_ok=True)
                fn(tmp_path=d)
            else:
                fn()
        except AssertionError as exc:
            failures.append(f"{name}: FAIL ({exc})")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{name}: ERROR {type(exc).__name__}: {exc}")
    passed = sum(1 for n in globals() if n.startswith("test_") and callable(globals()[n])) - len(failures)
    for f in failures:
        print(f"  {f}")
    print(f"\n{passed} passed, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
