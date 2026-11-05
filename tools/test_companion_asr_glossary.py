#!/usr/bin/env python3
"""Unit tests for the post-ASR domain-term glossary (companion_asr_glossary).

The glossary is wired into both production ASR paths (companion_air_local_minutes
and companion_recording_to_minutes run_local_asr), so a silent regression would
corrupt real board-mic meeting transcripts. These guard:

  1. Every rule (unambiguous + regex + context-gated) actually fires.
  2. Context-gated rules do NOT fire out-of-domain (the false-correction guard:
     a real "Apps" / "Null" / "routes" in unrelated text must be left alone).
  3. Already-correct canonical terms pass through untouched (a clean transcript
     is not rewritten) and normalization is idempotent.

The garble map was validated on the real 10-min board-mic baseline (53
corrections, 31 rules fired). These tests are portable (no Temp-file dependency):
they drive the rule tables directly and use synthetic in/out-of-domain strings.

Run directly or via pytest:

    python tools/test_companion_asr_glossary.py
    pytest tools/test_companion_asr_glossary.py
"""
from __future__ import annotations

import pathlib
import sys

# Make companion_asr_glossary importable when run directly. parents[0] == tools/.
_TOOLS = pathlib.Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from companion_asr_glossary import (  # noqa: E402
    normalize,
    _UNAMBIGUOUS,
    _REGEX,
    _CONTEXT,
)


# ----------------------------------------------------------------------- helpers
def _fix(text: str) -> str:
    return normalize(text)[0]


def _count(text: str) -> int:
    return sum(e["count"] for e in normalize(text)[1])


# ------------------------------------------------------- 1. every rule fires
def test_unambiguous_rules_all_fire():
    """Each unambiguous garble -> canonical, wrapped in a neutral sentence so
    edge effects can't mask a broken rule."""
    for garble, canon in _UNAMBIGUOUS:
        text = f"前文 {garble} 后文"
        fixed = _fix(text)
        assert canon in fixed, f"rule {garble!r}->{canon!r} did not apply: got {fixed!r}"
        assert garble not in fixed, f"rule {garble!r}->{canon!r} left garble behind: {fixed!r}"


def test_regex_rules_fire():
    """The faster_whisper recognizer variants all collapse to faster_whisper."""
    variants = [
        "FASTA下画线Whisper",
        "FASTER下化线WISPER",
        "FASTA下画线WISPR",
        "FASTER下化线WHISPER",
    ]
    for v in variants:
        fixed = _fix(v)
        assert fixed == "faster_whisper", f"regex did not normalize {v!r}: got {fixed!r}"


def test_context_rules_fire_in_domain():
    """Each context-gated rule fires when a domain keyword is within window."""
    in_domain = {
        "Apps": "Apps 编码码率采样",
        "EDIT": "EDIT 每秒字节码率",
        "Apt": "Apt 变成术语4bit",
        "routes": "routes 稳定为零采集",
        "Null": "Null 闪存装不下兆",
    }
    for garble, sentence in in_domain.items():
        canon = next(c for g, c, *_ in _CONTEXT if g == garble)
        fixed = _fix(sentence)
        assert canon in fixed and garble not in fixed, (
            f"context rule {garble!r}->{canon!r} failed in-domain: {fixed!r}")


# ----------------------------------------------- 2. context-gating is safe
def test_context_rules_do_not_fire_out_of_domain():
    """CRITICAL false-correction guard: a legitimate common word with no domain
    keyword nearby must pass through unchanged. Without this the glossary would
    silently corrupt clean transcripts."""
    out_of_domain = {
        "Apps": "Apps 是手机软件我们下载来用",
        "EDIT": "EDIT 是编辑菜单的意思",
        "Apt": "Apt 是个打包工具",
        "routes": "routes 是网络路由路径",
        "Null": "Null 指针表示空值",
    }
    for garble, sentence in out_of_domain.items():
        fixed = _fix(sentence)
        assert fixed == sentence, (
            f"context rule {garble!r} wrongly fired out-of-domain: {sentence!r} -> {fixed!r}")


# ------------------------------------------- 3. canonical stability + idempotent
_CANONICALS = [
    "栈", "SHA-256", "ADPCM", "Opus", "drops", "prompt", "main.c", "NOR闪存",
    "滤波", "赫兹", "板麦", "纪要", "时长", "校验", "哈希", "构建", "阻塞",
    "一次不差", "下划线", "固件bug", "enc_stack", "rec_stack", "faster_whisper",
]


def test_canonicals_pass_through_untouched():
    """A transcript that already has the correct terms is NOT rewritten. This is
    the no-false-positive guarantee on good/clean audio (and after glossing)."""
    text = " ".join(_CANONICALS)
    fixed, log = normalize(text)
    assert fixed == text, f"canonicals were rewritten: {text!r} -> {fixed!r} ({log})"
    assert log == [], f"changelog non-empty on canonical-only input: {log}"


def test_idempotent():
    """Running normalize twice == once (the glossed output is a fixed point).
    Guards against rule chaining that could drift on re-runs."""
    rich = ("板麦的ADPCM编码 drops为零 faster_whisper转写 SHA-256校验 哈希 "
            " NOR闪存装不下 栈溢出 滤波 赫兹 纪要 时长 构建 阻塞 一次不差 下划线 固件bug "
            "enc_stack rec_stack Opus prompt main.c 把卖版卖板脉 组色像 构件 教验教业 时场 "
            "Appleton OPEC Trout Pronced MainC Nord闪存 绿波 资资 机要 哈黑 一次补差 下画线下滑线 "
            "スタッフ 固件BOB 硬下划线栈 RAD下划线栈 Apps编码 EDIT每秒 Apt术语 routes为零 Null闪存")
    once = _fix(rich)
    twice = _fix(once)
    assert once == twice, f"not idempotent:\n once={once!r}\ntwice={twice!r}"


def test_regression_known_garbles_recovered():
    """Synthetic regression: the representative garbles from the validated
    baseline all recover their canonical terms."""
    text = "用スタッフ 分析Appleton 查drops 跑faster_whisper 算SHA-256 NOR闪存 板麦纪要"
    fixed = _fix(text)
    for term in ("栈", "ADPCM", "drops", "faster_whisper", "SHA-256", "NOR闪存", "板麦", "纪要"):
        assert term in fixed, f"regression: {term!r} missing from {fixed!r}"


# ------------------------------------------------------------------- edge cases
def test_empty_input():
    fixed, log = normalize("")
    assert fixed == "" and log == []


def test_whitespace_only():
    fixed, log = normalize("   \n\t  ")
    assert fixed == "   \n\t  " and log == []


def test_changelog_structure():
    """Every changelog entry has the auditable fields the production emit relies
    on (garble, canonical, count) and counts are >= 1."""
    text = "スタッフ Appleton drops"
    _, log = normalize(text)
    assert log, "expected a non-empty changelog"
    for e in log:
        assert {"garble", "canonical", "count"} <= set(e), f"entry missing fields: {e}"
        assert e["count"] >= 1


def test_known_baseline_correction_count_shape():
    """Sanity: a string with N distinct garbles yields >= N corrections (context
    rules may add more). Guards against rules silently no-opping."""
    n = len(_UNAMBIGUOUS)
    text = " ".join(g for g, _ in _UNAMBIGUOUS)
    assert _count(text) >= n, (
        f"expected >= {n} corrections from all unambiguous garbles, got {_count(text)}")


# ------------------------------------------------------------- standalone runner
if __name__ == "__main__":
    # No pytest in this environment; discover and run each test_* directly.
    import traceback
    fns = sorted((k, v) for k, v in sorted(globals().items()) if k.startswith("test_"))
    passed = failed = 0
    for name, fn in fns:
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except AssertionError as exc:
            print(f"  FAIL  {name}: {exc}")
            traceback.print_exc()
            failed += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR {name}: {exc!r}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {passed + failed} total")
    sys.exit(1 if failed else 0)
