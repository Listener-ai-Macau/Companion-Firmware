"""Post-ASR domain-term normalizer for board-mic meeting transcripts.

BACKGROUND
The board-mic ADPCM audio is lossy (4-bit, forced by the NOR write ceiling).
Proven 2026-08-08 (see asr-domain-garble-levers-closed): faster_whisper garbles
English technical terms regardless of prompt or language setting — the terms are
unresolvable in the audio, not a language-model problem. So the garble cannot be
fixed at the recognizer. This module normalizes the KNOWN, CONSISTENT
mis-recognitions back to canonical terms in the TRANSCRIPT TEXT, so a domain
reader can recover the content (owner's bar for "usable": recoverable, not
verbatim).

INTEGRITY
- Pure text post-process on real ASR output. Does NOT touch audio or recognizer.
- Every correction is returned in a changelog (offset, garble -> canonical).
- Conservative: unambiguous garbles map directly; common-word garbles
  (Apps/EDIT/Null/routes/Apt) are context-gated so a real occurrence is not
  silently rewritten.

The map generalizes: the same terms garble the same way across runs (the A/B
proved consistency), so this is reusable for future recordings of this domain.
"""
import re

# Unambiguous garbles -> canonical. Applied as literal substring replace,
# longest-first to avoid prefix collisions. These strings have no legitimate
# alternate meaning in a firmware/audio meeting.
_UNAMBIGUOUS = [
    # recognizer -> canonical
    ("スタッフ", "栈"),               # JP katakana 'stack'
    ("Shine-256", "SHA-256"),
    ("Shine256", "SHA-256"),
    ("C-256", "SHA-256"),
    ("Appleton", "ADPCM"),
    ("OPEC", "Opus"),
    ("Trout", "drops"),
    ("Pronced", "prompt"),
    ("MainC", "main.c"),
    ("Nord闪存", "NOR闪存"),
    ("绿波", "滤波"),                 # CIC3绿波 -> CIC3滤波
    ("资资", "赫兹"),                 # 8000资资 -> 8000赫兹
    ("版卖", "板麦"),
    ("把卖", "板麦"),
    ("板脉", "板麦"),
    ("机要功能", "纪要功能"),          # 机要 -> 纪要
    ("机要", "纪要"),
    ("时场", "时长"),                 # 目标时场 -> 目标时长
    ("教验", "校验"),                 # SHA教验 -> SHA校验
    ("教业", "校验"),
    ("哈黑哈黑", "哈希"),
    ("哈黑", "哈希"),
    ("构件", "构建"),
    ("组色像", "阻塞"),
    ("一次补差", "一次不差"),
    ("下画线", "下划线"),
    ("下滑线", "下划线"),
    ("固件BOB", "固件bug"),
    # phrase-level (unambiguous in context): firmware identity markers
    ("硬下划线栈", "enc_stack"),
    ("RAD下划线栈", "rec_stack"),
]

# Regex garbles (variable misspelling). Each: (compiled, replacement).
_FAST_WHISPER = re.compile(
    r"(?:FASTER|FASTA)下[画化]线W(?:hisper|HISPER|ISPER|ISPR|H\w*|h\w*)")
_REGEX = [
    (_FAST_WHISPER, "faster_whisper"),
]

# Context-gated garbles: (garble, canonical, [context keywords], window chars).
# Only rewritten if a keyword appears within +/- window chars (heuristic domain
# lock, e.g. Apps -> ADPCM only near encode/bitrate talk).
_CONTEXT = [
    ("Apps", "ADPCM", ["编码", "码率", "字节", "采样", "诞生", "有损", "预算",
                        "提前", "闪存", "这个码率", "4bit"], 24),
    ("EDIT", "ADPCM", ["每秒", "字节", "码率", "实际录", "编码"], 18),
    ("Apt", "ADPCM", ["变成", "术语", "4bit", "有损", "编码", "识别"], 16),
    ("routes", "drops", ["稳定为", "采集", "纠正", "为零", "为0", "丢"], 16),
    ("Null", "NOR", ["装不下", "闪存", "轮移", "兆", "容量", "14", "区", "擦除",
                     "写"], 18),
    ("把麦", "板麦", [], 0),           # empty ctx = unconditional (alias)
]


def normalize(text: str):
    """Return (corrected_text, changelog).

    changelog: list of dicts {garble, canonical, count}. Order = application
    order. Offsets are not reported because chained replaces shift them; the
    (garble, canonical, count) tuple is the auditable unit.
    """
    log = []
    out = text

    def _apply_literal(garble, canon):
        nonlocal out
        n = out.count(garble)
        if n:
            out = out.replace(garble, canon)
            log.append({"garble": garble, "canonical": canon, "count": n})

    # Regex first (they span multi-garble phrases like faster_whisper).
    for rx, canon in _REGEX:
        matches = rx.findall(out)
        if matches:
            out = rx.sub(canon, out)
            log.append({"garble": "faster_whisper(variants)",
                        "canonical": canon, "count": len(matches)})

    # Unambiguous literals, longest-first.
    for garble, canon in sorted(_UNAMBIGUOUS, key=lambda p: -len(p[0])):
        _apply_literal(garble, canon)

    # Context-gated. Done last, on already-partly-normalized text, with a
    # sliding window check so common words are only rewritten in-domain.
    for garble, canon, kws, window in _CONTEXT:
        if not kws:
            _apply_literal(garble, canon)
            continue
        idxs = [i for i in range(len(out)) if out.startswith(garble, i)]
        if not idxs:
            continue
        n = 0
        buf = list(out)
        for i in reversed(idxs):           # reverse so indexes stay valid
            neighborhood = out[max(0, i - window): i + len(garble) + window]
            if any(k in neighborhood for k in kws):
                buf[i:i + len(garble)] = list(canon)
                n += 1
        if n:
            out = "".join(buf)
            log.append({"garble": garble, "canonical": canon, "count": n,
                        "context_gated": True})

    return out, log


if __name__ == "__main__":
    import pathlib, sys
    src = pathlib.Path(sys.argv[1] if len(sys.argv) > 1
                       else r"C:\Users\Billy\AppData\Local\Temp\ab_air\live_full_10min_transcript.txt")
    raw = src.read_text(encoding="utf-8")
    fixed, log = normalize(raw)
    dest = src.with_name(src.stem + "_glossed.txt")
    dest.write_text(fixed, encoding="utf-8")
    print(f"[glossary] {src.name} -> {dest.name}")
    print(f"[glossary] {len(raw)} -> {len(fixed)} chars, {sum(e['count'] for e in log)} corrections:")
    for e in log:
        tag = " (ctx)" if e.get("context_gated") else ""
        print(f"  {e['garble']:<26} -> {e['canonical']:<14} x{e['count']}{tag}")
