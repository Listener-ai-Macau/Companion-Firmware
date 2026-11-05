#!/usr/bin/env python3
"""Deterministic host-side meeting minutes model for Companion recordings."""

from __future__ import annotations

import hashlib
import pathlib
import re
import wave
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any


SUMMARY_SCHEMA_VERSION = 1
DEFAULT_WAKE_PHRASES = ("你好 companion", "hello companion", "hi companion", "小伴")

DECISION_CUES = (
    "决定",
    "确认",
    "结论",
    "同意",
    "定下来",
    "默认",  # "默认X" = a settled default choice (survives ASR garbling)
    "这版",  # "这版默认/这版用X" = a version decision (trad 這版 -> 这版 via norm)
    "approved",
    "agreed",
    "decide",
    "decision",
)
ACTION_CUES = (
    "待办",
    "负责",
    "跟进",
    "需要",
    "必须",  # commitment signal ("必须Fail Closed") — trad 必須 -> 必须 via norm
    "马上",
    "明天",
    "今天",
    "下周",
    "本周",  # owner/timeframe commitment ("Billy本周完成")
    "todo",
    "action",
    "owner",
    "follow up",
    "will ",
)
QUESTION_CUES = ("?", "？", "问题", "是否", "要不要", "怎么", "why", "how")
# Negations that turn the "问题" cue into a non-question ("没问题" = "no problem",
# "长度没问题" is a reassurance, not a question). Excluded before cue matching.
QUESTION_NEGATIONS = ("没问题", "无问题", "没有问题", "不是问题")
# Traditional -> Simplified Chinese map for cue matching. faster_whisper (zh)
# frequently emits traditional characters (決定/確認/問題/必須/這版) while the
# cue words above are simplified. Without normalization, real decisions/action
# items go unmatched even when the transcript clearly contains them. This covers
# the cue characters plus the highest-frequency trad chars seen in real board-mic
# transcripts. opencc is intentionally not a dependency of this host tool.
_TRAD_TO_SIMP = str.maketrans({
    "決": "决", "確": "确", "認": "认", "結": "结", "論": "论", "來": "来",
    "辦": "办", "負": "负", "責": "责", "進": "进", "問": "问", "題": "题",
    "錄": "录", "穩": "稳", "訊": "讯", "這": "这", "個": "个", "點": "点",
    "繼": "继", "續": "续", "為": "为", "調": "调", "長": "长", "實": "实",
    "測": "测", "圍": "围", "編": "编", "單": "单", "體": "体", "網": "网",
    "應": "应", "當": "当", "從": "从", "還": "还", "過": "过", "給": "给",
    "讓": "让", "說": "说", "話": "话", "見": "见", "現": "现", "時": "时",
    "業": "业", "區": "区", "員": "员", "號": "号", "經": "经", "電": "电",
    "試": "试", "發": "发", "關": "关", "開": "开", "間": "间", "後": "后",
    "對": "对", "頭": "头", "邊": "边", "際": "际", "壓": "压", "務": "务",
    "會": "会", "議": "议", "義": "义", "雙": "双", "觀": "观", "備": "备",
    "機": "机", "動": "动", "場": "场", "處": "处", "帶": "带", "達": "达",
    "類": "类", "寫": "写", "學": "学", "舊": "旧", "記": "记", "報": "报",
    "導": "导", "兩": "两", "萬": "万", "無": "无", "與": "与", "於": "于",
    "產": "产", "專": "专", "營": "营", "環": "环", "畫": "画", "設": "设",
    "計": "计", "劃": "划", "製": "制", "較": "较", "車": "车", "總": "总",
    "錢": "钱", "買": "买", "賣": "卖", "讀": "读", "聽": "听", "覺": "觉",
    "視": "视", "親": "亲", "愛": "爱", "鐘": "钟", "構": "构", "極": "极",
    "語": "语", "請": "请", "幫": "帮", "紀": "纪", "廠": "厂", "變": "变",
    "廣": "广", "慶": "庆", "鐵": "铁", "銀": "银", "銅": "铜", "務": "务",
    "須": "须", "沒": "没", "敗": "败", "認": "认", "證": "证", "驗": "验",
    "測": "测", "確": "确", "應": "应", "當": "当", "盡": "尽", "獲": "获", "週": "周",
})


def to_simplified(text: str) -> str:
    """Best-effort traditional -> simplified normalization for cue matching."""
    return text.translate(_TRAD_TO_SIMP)
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "录音",
    "会议",
    "今天",
    "需要",
    "确认",
    "我们",
    "这个",
    "一个",
}


@dataclass(frozen=True)
class TranscriptSegment:
    speaker: str
    start_s: float
    end_s: float
    text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audio_metadata(path: pathlib.Path) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "path": str(path),
        "byte_count": path.stat().st_size,
        "sha256": file_sha256(path),
    }
    if path.suffix.lower() == ".wav":
        with wave.open(str(path), "rb") as wav:
            frames = wav.getnframes()
            sample_rate = wav.getframerate()
            metadata.update(
                {
                    "container": "wav",
                    "channels": wav.getnchannels(),
                    "sample_rate_hz": sample_rate,
                    "sample_width_bytes": wav.getsampwidth(),
                    "frame_count": frames,
                    "duration_s": round(frames / sample_rate, 3) if sample_rate else 0.0,
                }
            )
    else:
        metadata.update({"container": path.suffix.lower().lstrip(".") or "binary"})
    return metadata


def normalize_transcript_text(text: str | None) -> str:
    if not text:
        return ""
    lines = [line.strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return "\n".join(line for line in lines if line)


def split_sentence_text(text: str) -> list[str]:
    normalized = normalize_transcript_text(text)
    if not normalized:
        return []
    parts: list[str] = []
    for line in normalized.split("\n"):
        expanded = re.sub(r"\s+([^:：\s]{1,32}[:：]\s*)", r"\n\1", line)
        for speaker_line in expanded.split("\n"):
            if re.match(r"^.{1,32}[:：]\s*.+", speaker_line):
                parts.append(speaker_line)
                continue
            for part in re.split(r"(?<=[。！？!?])\s+|[。；;，,]\s*", speaker_line):
                cleaned = part.strip()
                if cleaned:
                    parts.append(cleaned)
    return parts


def split_transcript(text: str | None, duration_s: float | None) -> list[TranscriptSegment]:
    sentences = split_sentence_text(text or "")
    if not sentences:
        return []
    total_chars = max(1, sum(len(item) for item in sentences))
    fallback_duration = duration_s if duration_s and duration_s > 0 else max(1.0, len(sentences) * 8.0)
    cursor = 0.0
    segments: list[TranscriptSegment] = []
    for item in sentences:
        speaker = "unknown"
        body = item
        match = re.match(r"^([^:：]{1,32})[:：]\s*(.+)$", item)
        if match:
            speaker = match.group(1).strip()
            body = match.group(2).strip()
        span = max(0.5, fallback_duration * len(item) / total_chars)
        start = cursor
        end = min(fallback_duration, cursor + span)
        segments.append(TranscriptSegment(speaker=speaker, start_s=round(start, 3), end_s=round(end, 3), text=body))
        cursor = end
    if segments:
        last = segments[-1]
        segments[-1] = TranscriptSegment(last.speaker, last.start_s, round(fallback_duration, 3), last.text)
    return segments


def sentence_contains(sentence: str, cues: tuple[str, ...], excludes: tuple[str, ...] = ()) -> bool:
    # Normalize to simplified + lowercase so traditional ASR output (決定/必須/
    # 這版) matches the simplified cue words (决定/必须/这版).
    normalized = to_simplified(sentence.lower())
    if excludes and any(to_simplified(ex) in normalized for ex in excludes):
        return False
    return any(to_simplified(cue) in normalized for cue in cues)


def extract_keywords(sentences: list[str], limit: int = 8) -> list[str]:
    words: list[str] = []
    for sentence in sentences:
        words.extend(re.findall(r"[A-Za-z][A-Za-z0-9_+-]{2,}", sentence.lower()))
        words.extend(re.findall(r"[\u4e00-\u9fff]{2,}", sentence))
    counts = Counter(word for word in words if word not in STOPWORDS and len(word) >= 2)
    return [word for word, _count in counts.most_common(limit)]


def trim_text(text: str, limit: int) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 3)].rstrip() + "..."


def build_action_item(segment: TranscriptSegment, index: int) -> dict[str, Any]:
    return {
        "id": f"A{index:02d}",
        "owner": segment.speaker if segment.speaker != "unknown" else "unassigned",
        "text": segment.text,
        "due": "unspecified",
        "source_start_s": segment.start_s,
        "source_end_s": segment.end_s,
    }


def build_meeting_minutes(
    audio_path: pathlib.Path,
    transcript_text: str | None = None,
    transcript_provider: str = "provided_text",
    recording_chain: dict[str, Any] | None = None,
    source_artifact: str | None = None,
    meeting_title: str | None = None,
    wake_phrases: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    audio = audio_metadata(audio_path)
    duration_s = audio.get("duration_s") if isinstance(audio.get("duration_s"), (int, float)) else None
    normalized_transcript = normalize_transcript_text(transcript_text)
    segments = split_transcript(normalized_transcript, duration_s)
    sentences = [segment.text for segment in segments]
    state = "minutes_ready" if normalized_transcript else "needs_transcription"

    decisions = [
        {"text": segment.text, "source_start_s": segment.start_s, "source_end_s": segment.end_s}
        for segment in segments
        if sentence_contains(segment.text, DECISION_CUES)
    ]
    action_segments = [segment for segment in segments if sentence_contains(segment.text, ACTION_CUES)]
    questions = [
        {"text": segment.text, "source_start_s": segment.start_s, "source_end_s": segment.end_s}
        for segment in segments
        if sentence_contains(segment.text, QUESTION_CUES, QUESTION_NEGATIONS)
    ]
    bullets = [trim_text(sentence, 140) for sentence in sentences[:5]]
    keywords = extract_keywords(sentences)
    if meeting_title:
        title = meeting_title
    elif decisions:
        title = decisions[0]["text"]
    elif sentences:
        title = sentences[0]
    else:
        title = "Companion 录音纪要"
    title = trim_text(title, 48)
    wake_word = detect_wake_word(segments, wake_phrases or DEFAULT_WAKE_PHRASES)

    summary = {
        "title": title,
        "overview": (
            trim_text(" ".join(sentences[:3]), 260)
            if sentences
            else "录音已经保存并完成音频资产校验，等待转写提供方生成文本。"
        ),
        "bullets": bullets,
        "decisions": decisions,
        "action_items": [build_action_item(segment, index + 1) for index, segment in enumerate(action_segments)],
        "questions": questions,
        "keywords": keywords,
    }

    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "postprocess_state": state,
        "source": {
            "audio": audio,
            "recording_chain_artifact": source_artifact,
            "recording_chain_status": recording_chain.get("status") if recording_chain else None,
            "recording_id": find_recording_id(recording_chain) if recording_chain else None,
        },
        "transcript": {
            "provider": transcript_provider,
            "language_hint": "zh-CN",
            "text": normalized_transcript,
            "segments": [segment.to_dict() for segment in segments],
        },
        "summary": summary,
        "wake_word": wake_word,
        "privacy": {
            "raw_audio_delete_policy": "delete_after_sync_only_after_host_sha256_verification",
            "local_minutes_delete_policy": "host_owned; delete JSON/Markdown and cached WAV together on privacy erase",
            "consent_note": "recording UI must make capture state visible before real user deployment",
        },
        "next_processing": next_processing_steps(state),
    }


def find_recording_id(recording_chain: dict[str, Any] | None) -> int | None:
    if not recording_chain:
        return None
    for operation in recording_chain.get("operations", []):
        if operation.get("operation") in {"recording_pull", "ble_pull_recording"}:
            value = operation.get("recording_id")
            if isinstance(value, int):
                return value
        listing = operation.get("recording_list") or operation.get("recording_list_after_recording")
        entries = listing.get("entries", []) if isinstance(listing, dict) else []
        if entries and isinstance(entries[0].get("recording_id"), int):
            return entries[0]["recording_id"]
    return None


def detect_wake_word(
    segments: list[TranscriptSegment],
    wake_phrases: list[str] | tuple[str, ...],
) -> dict[str, Any]:
    normalized_phrases = [phrase.strip().lower() for phrase in wake_phrases if phrase.strip()]
    detections: list[dict[str, Any]] = []
    for segment in segments:
        lowered = segment.text.lower()
        for phrase in normalized_phrases:
            if phrase and phrase in lowered:
                detections.append(
                    {
                        "phrase": phrase,
                        "speaker": segment.speaker,
                        "source_start_s": segment.start_s,
                        "source_end_s": segment.end_s,
                        "mode": "transcript_postprocess",
                    }
                )
    return {
        "state": "detected" if detections else "not_detected",
        "phrases": normalized_phrases,
        "detections": detections,
        "device_control_surface": "wake_word_control/status arm/disarm/simulate_detect",
        "production_note": "transcript detection is not always-on local keyword spotting; production wake requires an on-device or companion-host KWS engine with power and false-trigger validation",
    }


def next_processing_steps(state: str) -> list[str]:
    if state == "needs_transcription":
        return [
            "run ASR/transcription provider against the WAV",
            "rerun postprocess with --transcript-file or --transcript-text",
            "delete raw audio only after the host has verified SHA-256 and user policy permits",
        ]
    return [
        "show summary, decisions, action items, and questions in the host app",
        "allow user edits before export/share",
        "keep source SHA-256 attached so minutes can be traced back to the verified recording",
    ]


def render_minutes_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    transcript = report["transcript"]
    source = report["source"]
    audio = source["audio"]
    lines = [
        f"# {summary['title']}",
        "",
        f"- 状态: `{report['postprocess_state']}`",
        f"- 音频: `{audio.get('path')}`",
        f"- 时长: `{audio.get('duration_s', 'unknown')}` 秒",
        f"- SHA-256: `{audio.get('sha256')}`",
        f"- 转写提供方: `{transcript.get('provider')}`",
        "",
        "## 摘要",
        "",
        summary["overview"],
        "",
    ]

    if summary["bullets"]:
        lines.extend(["## 要点", ""])
        lines.extend(f"- {item}" for item in summary["bullets"])
        lines.append("")

    lines.extend(["## 决策", ""])
    if summary["decisions"]:
        lines.extend(f"- {item['text']}" for item in summary["decisions"])
    else:
        lines.append("- 无明确决策")
    lines.append("")

    lines.extend(["## 待办", ""])
    if summary["action_items"]:
        for item in summary["action_items"]:
            lines.append(f"- `{item['id']}` {item['owner']}: {item['text']}")
    else:
        lines.append("- 无明确待办")
    lines.append("")

    lines.extend(["## 问题", ""])
    if summary["questions"]:
        lines.extend(f"- {item['text']}" for item in summary["questions"])
    else:
        lines.append("- 无明确问题")
    lines.append("")

    if summary["keywords"]:
        lines.extend(["## 关键词", "", ", ".join(summary["keywords"]), ""])

    wake_word = report.get("wake_word", {})
    lines.extend(["## 唤醒词", ""])
    if wake_word.get("detections"):
        for item in wake_word["detections"]:
            lines.append(f"- `{item['phrase']}` at `{item['source_start_s']:0.3f}-{item['source_end_s']:0.3f}s`")
    else:
        lines.append("- 未检测到配置的唤醒词")
    lines.append("")

    lines.extend(["## 转写", ""])
    if transcript["segments"]:
        for segment in transcript["segments"]:
            lines.append(
                f"- `{segment['start_s']:0.3f}-{segment['end_s']:0.3f}s` "
                f"{segment['speaker']}: {segment['text']}"
            )
    else:
        lines.append("- 转写待处理")
    lines.append("")

    lines.extend(["## 隐私", ""])
    lines.extend(f"- {item}" for item in report["next_processing"])
    lines.append("")
    return "\n".join(lines)
