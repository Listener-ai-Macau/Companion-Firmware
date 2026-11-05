#!/usr/bin/env python3
"""COMP-REQ-666: offline half-rate+IMA roundtrip + optional ASR on ~10min meeting audio."""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import struct
import sys
import time
import wave

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from companion_ble_real_bench import decode_ima_adpcm_frame, upsample_pcm16_x2  # noqa: E402

STEP_TABLE = [
    7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45,
    50, 55, 60, 66, 73, 80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230,
    253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876, 963,
    1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327,
    3660, 4026, 4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493, 10442,
    11487, 12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767,
]
INDEX_TABLE = [-1, -1, -1, -1, 2, 4, 6, 8, -1, -1, -1, -1, 2, 4, 6, 8]


class Adpcm:
    def __init__(self) -> None:
        self.predictor = 0
        self.step_index = 0

    def encode_nibble(self, sample: int) -> int:
        step = STEP_TABLE[self.step_index]
        diff = sample - self.predictor
        nibble = 0
        if diff < 0:
            nibble = 8
            diff = -diff
        if diff >= step:
            nibble |= 4
            diff -= step
        if diff >= (step >> 1):
            nibble |= 2
            diff -= step >> 1
        if diff >= (step >> 2):
            nibble |= 1
        delta = step >> 3
        if nibble & 4:
            delta += step
        if nibble & 2:
            delta += step >> 1
        if nibble & 1:
            delta += step >> 2
        if nibble & 8:
            delta = -delta
        self.predictor = max(-32768, min(32767, self.predictor + delta))
        self.step_index = max(0, min(88, self.step_index + INDEX_TABLE[nibble & 0x0F]))
        return nibble & 0x0F

    def encode_frame(self, samples: list[int]) -> bytes:
        n = len(samples)
        out = bytearray(6 + (n + 1) // 2)
        out[0:2] = struct.pack("<h", self.predictor)
        out[2] = self.step_index & 0xFF
        out[3] = 0
        out[4:6] = struct.pack("<H", n)
        for i in range(0, n, 2):
            n0 = self.encode_nibble(samples[i])
            n1 = self.encode_nibble(samples[i + 1]) if i + 1 < n else 0
            out[6 + i // 2] = (n1 << 4) | n0
        return bytes(out)


def read_wav_mono_i16(path: pathlib.Path) -> tuple[int, list[int]]:
    with wave.open(str(path), "rb") as w:
        ch, sw, rate, nframes = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(nframes)
    if sw != 2:
        raise SystemExit(f"need 16-bit wav, got sampwidth={sw}")
    samples = list(struct.unpack(f"<{nframes * ch}h", raw))
    if ch == 2:
        samples = [((samples[i] + samples[i + 1]) // 2) for i in range(0, len(samples), 2)]
    elif ch != 1:
        raise SystemExit(f"unsupported channels={ch}")
    return rate, samples


def resample_linear(samples: list[int], src_rate: int, dst_rate: int) -> list[int]:
    if src_rate == dst_rate:
        return samples
    n_out = int(len(samples) * dst_rate / src_rate)
    out = [0] * n_out
    last = samples[-1] if samples else 0
    for i in range(n_out):
        x = i * src_rate / dst_rate
        j = int(x)
        f = x - j
        a = samples[j] if j < len(samples) else last
        b = samples[j + 1] if j + 1 < len(samples) else a
        out[i] = int(a * (1 - f) + b * f)
    return out


def write_wav(path: pathlib.Path, rate: int, samples: list[int]) -> None:
    raw = struct.pack(f"<{len(samples)}h", *samples)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(raw)


def rms(xs: list[int]) -> float:
    if not xs:
        return 0.0
    return math.sqrt(sum(x * x for x in xs) / len(xs))


def snr_db(ref: list[int], test: list[int]) -> float:
    n = min(len(ref), len(test))
    ref, test = ref[:n], test[:n]
    noise = [ref[i] - test[i] for i in range(n)]
    r, e = rms(ref), rms(noise)
    if e < 1e-9:
        return 99.0
    return 20 * math.log10(r / e)


def half_ima_roundtrip(pcm16: list[int]) -> tuple[list[int], int, int]:
    """Match COMP-REQ-666 IMA6 framing on 16k mono i16 samples."""
    pcm_bytes = len(pcm16) * 2
    pcm_u8 = struct.pack(f"<{len(pcm16)}h", *pcm16)
    PCM_PER_FRAME = 1744
    FINAL_PCM_MAX = 1456
    adpcm = Adpcm()
    wire = bytearray()
    restored = bytearray()
    off = 0
    frames = 0
    while off < pcm_bytes:
        rem = pcm_bytes - off
        want = min(PCM_PER_FRAME, rem)
        if rem <= PCM_PER_FRAME and rem > FINAL_PCM_MAX:
            head = (rem - FINAL_PCM_MAX) & ~1
            if head < 2:
                head = 2
            want = head
        want &= ~1
        if want < 2:
            break
        chunk = struct.unpack(f"<{want // 2}h", pcm_u8[off : off + want])
        s8 = []
        for i in range(0, len(chunk) - 1, 2):
            s8.append((chunk[i] + chunk[i + 1]) // 2)
        if not s8:
            break
        frame = adpcm.encode_frame(s8)
        wire.extend(frame)
        dec8 = decode_ima_adpcm_frame(frame)
        up = upsample_pcm16_x2(dec8)
        if len(up) > want:
            up = up[:want]
        elif len(up) < want:
            up = up + b"\x00" * (want - len(up))
        restored.extend(up)
        off += want
        frames += 1
    restored_samples = list(struct.unpack(f"<{len(restored) // 2}h", bytes(restored)))
    if len(restored_samples) < len(pcm16):
        restored_samples += [0] * (len(pcm16) - len(restored_samples))
    else:
        restored_samples = restored_samples[: len(pcm16)]
    return restored_samples, len(wire), frames


def asr_file(path: pathlib.Path, model_size: str = "base") -> str:
    from faster_whisper import WhisperModel

    print(f"[asr] loading model={model_size} for {path.name} ...", flush=True)
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        str(path),
        language="zh",
        beam_size=1,
        vad_filter=True,
    )
    parts = []
    for seg in segments:
        parts.append(seg.text.strip())
    text = "".join(parts)
    print(f"[asr] done lang={info.language} dur={info.duration:.1f}s chars={len(text)}", flush=True)
    return text


def keyword_hits(text: str, keywords: list[str]) -> dict[str, bool]:
    t = text.lower()
    out = {}
    for k in keywords:
        out[k] = k.lower() in t or k in text
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--src",
        default=str(
            ROOT
            / "docs/validation/comp-req-666-effective-500/meeting-10min-original.wav"
        ),
    )
    ap.add_argument(
        "--out-dir",
        default=str(ROOT / "docs/validation/comp-req-666-effective-500"),
    )
    ap.add_argument("--asr", action="store_true")
    ap.add_argument("--asr-model", default="base")
    ap.add_argument("--asr-max-sec", type=float, default=0.0, help="0=full file")
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    src = pathlib.Path(args.src)

    rate0, samp0 = read_wav_mono_i16(src)
    print(f"source rate={rate0} sec={len(samp0)/rate0:.1f}", flush=True)
    pcm16 = resample_linear(samp0, rate0, 16000)
    if args.asr_max_sec > 0:
        pcm16 = pcm16[: int(args.asr_max_sec * 16000)]
        print(f"trimmed to {len(pcm16)/16000:.1f}s for this run", flush=True)

    orig_path = out_dir / "meeting-10min-16k-original.wav"
    after_path = out_dir / "meeting-10min-16k-after-halfima.wav"
    write_wav(orig_path, 16000, pcm16)

    t0 = time.time()
    restored, wire_n, frames = half_ima_roundtrip(pcm16)
    enc_s = time.time() - t0
    write_wav(after_path, 16000, restored)

    pcm_bytes = len(pcm16) * 2
    ratio = pcm_bytes / max(1, wire_n)
    snr_full = snr_db(pcm16, restored)
    mid = len(pcm16) // 2
    w = min(len(pcm16) // 4, 16000 * 60)
    snr_mid = snr_db(pcm16[mid : mid + w], restored[mid : mid + w])

    gold_keywords = [
        "先压再传",
        "压缩",
        "蓝牙",
        "行动项",
        "会议",
        "等效",
        "五百",
        "八千",
        "IMA",
        "Billy",
        "小陈",
        "主路径",
        "CoC",
        "预建",
        "Wire",
        "wire",
        "决策",
        "风险",
        "Windows",
    ]
    # normalize: some keywords are english case-insensitive
    gold_keywords = list(dict.fromkeys(gold_keywords))

    gold_summary = {
        "meeting": "Companion产品周会 2026-07-28",
        "topic": "录音同步压缩与会议总结可行性",
        "decisions": [
            "采用16k→8k再IMA预压作为会议同步主路径",
            "CoC为备选",
            "UI必须区分空中wire与等效pcm_effective",
            "十分钟长录音为下一阶段容量目标（当前设备dev上限60s）",
        ],
        "action_items": [
            "A: 十分钟语音编解码往返与转写对比",
            "B: 文档默认显示wire，等效单独标注",
            "C: 评估4kHz或CoC",
            "D: Owner确认半率有损可接受性",
        ],
    }

    report: dict = {
        "source_wav": str(src),
        "duration_s": round(len(pcm16) / 16000, 2),
        "pcm_bytes_16k": pcm_bytes,
        "wire_bytes_ima": wire_n,
        "compression_ratio": round(ratio, 3),
        "frames": frames,
        "encode_wall_s": round(enc_s, 2),
        "snr_full_db": round(snr_full, 2),
        "snr_mid_db": round(snr_mid, 2),
        "codec": "half-rate 16k→8k average-pair + IMA-ADPCM (COMP-REQ-666 IMA6 framing)",
        "lossy_declaration": True,
        "ratio_breakdown": {
            "half_rate_factor": 2.0,
            "ima_on_8k_pcm_approx": round(ratio / 2.0, 2),
            "combined_on_16k_pcm": round(ratio, 3),
            "meaning": "Not lossless. Telephone-ish speech band + 4-bit ADPCM. Good for meeting notes; bad for music/hi-fi.",
        },
        "device_note": "Bringup FLASH_RECORDING_DEV_MAX_SECONDS=60; this probe is offline codec==host path, not on-device 10min NOR store.",
        "outputs": {
            "original_16k": str(orig_path.name),
            "after_codec_16k": str(after_path.name),
        },
        "gold_summary": gold_summary,
        "gold_keywords": gold_keywords,
    }

    if args.asr:
        try:
            text_orig = asr_file(orig_path, args.asr_model)
            text_after = asr_file(after_path, args.asr_model)
            hits_o = keyword_hits(text_orig, gold_keywords)
            hits_a = keyword_hits(text_after, gold_keywords)
            ko = sum(1 for v in hits_o.values() if v)
            ka = sum(1 for v in hits_a.values() if v)
            report["asr"] = {
                "model": args.asr_model,
                "original_chars": len(text_orig),
                "after_chars": len(text_after),
                "keyword_hits_original": hits_o,
                "keyword_hits_after": hits_a,
                "keyword_score_original": f"{ko}/{len(gold_keywords)}",
                "keyword_score_after": f"{ka}/{len(gold_keywords)}",
                "transcript_original_preview": text_orig[:800],
                "transcript_after_preview": text_after[:800],
                "can_summarize_heuristic": ka >= max(4, len(gold_keywords) // 3),
            }
            (out_dir / "meeting-10min-transcript-original.txt").write_text(
                text_orig, encoding="utf-8"
            )
            (out_dir / "meeting-10min-transcript-after-halfima.txt").write_text(
                text_after, encoding="utf-8"
            )
        except Exception as exc:  # noqa: BLE001
            report["asr"] = {"error": str(exc)}
    else:
        report["asr"] = {"status": "skipped", "hint": "pass --asr"}

    out = out_dir / "meeting-10min-codec-report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in report if k not in ("gold_summary",)}, ensure_ascii=False, indent=2))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
