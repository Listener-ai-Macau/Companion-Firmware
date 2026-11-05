#!/usr/bin/env python3
"""Board-mic AIR recording -> meeting minutes, FULLY LOCAL (no OpenAI).

Why this exists (2026-08-05):
  * tools/companion_recording_to_minutes.py drives companion-type.exe ASR, which
    hardcodes https://api.openai.com/v1/audio/transcriptions -- firewalled on this
    network (curl times out), so ASR silently returns empty. This script uses local
    faster_whisper instead (cached models/Systran/faster-whisper-base).
  * tools/companion_flash_recording_chain.pull_recording parses a 56-byte chunk
    header that the device does NOT send; the real header is 20 bytes <BBHIIII>.
    This script pulls with the correct header.
  * The stored opus is wrapped in a "COP1" container (magic 0x434f5031) that must be
    parsed before decode. This script decodes via PyAV's bundled libopus.

Pipeline: BLE pull (latest recording) -> COP1 decode -> PCM16 WAV -> faster_whisper ASR
          -> deterministic build_meeting_minutes. Optionally triggers a fresh capture
          (--capture) first. Prints crest/peak/clip level stats (AGC validation harness).

Real air path only (speaker -> SPH0655 board mic -> CIC3 -> Opus16 -> NOR). No host mic,
no file-fed stim, no cloud ASR.

Exit 0 with minutes if ASR non-empty; non-zero otherwise.
"""
from __future__ import annotations
# PRELOAD torch before av/PyAV touches DLL state. faster_whisper lazily imports
# ctranslate2 -> torch -> c10.dll. If av decodes first, c10.dll fails to init
# (WinError 1114) due to DLL-hell. Importing torch here in clean process state
# makes c10.dll load once and stay valid. (Proven 2026-08-05.)
import torch  # noqa: F401
import argparse, asyncio, binascii, json, pathlib, struct, sys, wave

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))                       # app.companion_pendant...
sys.path.insert(0, str(REPO / "tools"))             # companion_flash_recording_chain
import companion_flash_recording_chain as C          # noqa: E402
from app.companion_pendant.postprocess.meeting_minutes import (  # noqa: E402
    build_meeting_minutes, render_minutes_markdown,
)
from bleak import BleakClient, BleakScanner          # noqa: E402

ADDR_DEFAULT = "00:80:E1:27:B8:EA"
HDR = "<BBHIIII"            # schema,flags,payload_length,recording_id,packet_sequence,byte_offset,total_length
HDR_SIZE = struct.calcsize(HDR)   # 20
REQ_FMT = "<BBHIII"         # SCHEMA_VERSION,0,req_len,recording_id,offset,0  (16 B)


# --------------------------------------------------------------------------- pull
async def pull_recording(addr: str, out_raw: pathlib.Path, chunk: int, timeout: float) -> dict:
    device = await BleakScanner.find_device_by_address(addr, timeout=timeout)
    if not device:
        raise RuntimeError(f"BLE device {addr} not found (scan {timeout}s)")
    async with BleakClient(device, timeout=timeout) as client:
        table = C.load_uuid_table(); uuids = C.build_uuid_index(table)
        rl = await C.read_recording_list(client, uuids["recording_list"])
        if int(rl["count"]) == 0:
            raise RuntimeError("no recording on device")
        entry = rl["entries"][0]
        rid = int(entry["recording_id"]); total = int(entry["total_length"])
        crc_expect = int(str(entry["content_crc32"]), 16)
        print(f"[pull] id={rid} total={total} codec={entry['codec']} crc=0x{crc_expect:08x}", flush=True)

        cu = uuids["recording_chunk_pull"]
        q: asyncio.Queue = asyncio.Queue()
        await client.start_notify(cu, lambda _s, raw: q.put_nowait(bytes(raw)))
        await asyncio.sleep(0.2)

        data = bytearray(); offset = 0
        while offset < total:
            req_len = min(chunk, total - offset)
            req = struct.pack(REQ_FMT, C.SCHEMA_VERSION, 0, req_len, rid, offset, 0)
            got = None
            for _attempt in range(8):  # device drops every-other write; re-write on miss
                while not q.empty():
                    st = q.get_nowait()
                    if len(st) >= HDR_SIZE:
                        _sv, _fl, _pl, _rid, _seq, _off, _tot = struct.unpack(HDR, st[:HDR_SIZE])
                        if _rid == rid and _off == offset:
                            got = st[HDR_SIZE:HDR_SIZE + _pl]
                if got is not None:
                    break
                await client.write_gatt_char(cu, req, response=True)
                try:
                    raw = await asyncio.wait_for(q.get(), timeout=2.5)
                except asyncio.TimeoutError:
                    continue
                if len(raw) >= HDR_SIZE:
                    sv, fl, pl, prid, pseq, poff, ptot = struct.unpack(HDR, raw[:HDR_SIZE])
                    if prid == rid and poff == offset:
                        got = raw[HDR_SIZE:HDR_SIZE + pl]; break
                    q.put_nowait(raw)  # lagging chunk; re-check next loop
                await asyncio.sleep(0.15)
            if got is None:
                raise RuntimeError(f"no chunk at offset={offset} (have {len(data)} B)")
            data += got; offset += len(got)
        await client.stop_notify(cu)
    out_raw.write_bytes(bytes(data))
    crc = binascii.crc32(bytes(data)) & 0xFFFFFFFF
    return {"raw_path": str(out_raw), "bytes": len(data), "crc": crc,
            "crc_match": crc == crc_expect, "codec": entry["codec"],
            "recording_id": rid, "duration_ms": int(entry.get("duration_ms", 0))}


# ------------------------------------------------------------------ COP1 decode
def decode_cop1(raw: bytes, out_wav: pathlib.Path, out_rate: int = 16000) -> dict:
    import av, numpy as np
    assert raw[:4] == b"COP1", f"not COP1: {raw[:4]!r}"
    ver = struct.unpack("<H", raw[4:6])[0]
    frame_ms = struct.unpack("<H", raw[6:8])[0]
    bitrate = struct.unpack("<I", raw[8:12])[0]
    off = 12; frames = []
    while off + 2 <= len(raw):
        n = struct.unpack("<H", raw[off:off+2])[0]; off += 2
        if n == 0 or n > 4000 or off + n > len(raw):
            if 0 < len(raw) - off <= 400:        # best-effort tail frame
                frames.append(raw[off:off + min(n, len(raw) - off)] or raw[off:])
            break
        frames.append(raw[off:off+n]); off += n

    cc = av.CodecContext.create("opus", "r")     # channels/rate/format not writable here
    chunks = []; native = None; decoded = 0
    for fb in frames:
        try:
            outs = cc.decode(av.Packet(fb))
        except Exception:
            continue
        for f in outs:
            if native is None:
                native = f.sample_rate
            arr = f.to_ndarray()
            chunks.append(arr.mean(axis=0) if arr.ndim == 2 else arr)
            decoded += 1
    if native is None:
        raise RuntimeError("no opus frames decoded")
    cat = np.concatenate(chunks)
    if native != out_rate:
        if native % out_rate == 0:
            cat = cat[:: native // out_rate]
        else:
            idx = np.linspace(0, len(cat) - 1, int(round(len(cat) * out_rate / native)))
            cat = np.interp(idx, np.arange(len(cat)), cat)
    s16 = (cat * 32767.0).clip(-32768, 32767).astype("<i2")
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(out_rate)
        w.writeframes(s16.tobytes())
    return {"ver": ver, "frame_ms": frame_ms, "bitrate": bitrate,
            "frames": len(frames), "decoded": decoded, "native_rate": native,
            "samples": int(len(s16)), "duration_s": round(len(s16) / out_rate, 2)}


# ----------------------------------------------------------------- level stats
def level_stats(wav_path: pathlib.Path) -> dict:
    import numpy as np
    with wave.open(str(wav_path), "rb") as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    if len(x) < 2:
        return {}
    peak = float(np.max(np.abs(x))); rms = float(np.sqrt(np.mean(x**2)))
    crest = peak / (rms + 1e-12)
    return {"peak": round(peak, 3), "rms": round(rms, 4), "crest": round(crest, 1),
            "clip_pct": round(100 * float(np.mean(np.abs(x) > 0.99)), 3),
            "crest_ok": crest >= 12, "no_clip": peak <= 0.76}


# ------------------------------------------------------------------------ ASR
# Domain initial_prompt for faster_whisper zh. Board-mic ADPCM audio is lossy, so
# the LM benefits from generic meeting/firmware vocabulary priming — proven
# (2026-08-07) to clean key terms on real air-path captures (e.g. "GC"->"AGC",
# "决定这版默认" recovered) without leaking specific content (no proper nouns /
# decisions are in the prompt, so the test stays fair and the audio still drives
# the output). vad_filter MUST stay False: VAD strips quiet board speech
# (132c->48c, confirmed).
_ASR_DOMAIN_PROMPT_ZH = "会议纪要。固件版本。录音稳定性。单声道。默认。决定。待办。实测。准确率。零。必须。"


def local_asr(wav_path: pathlib.Path, model: str, language: str | None,
              initial_prompt: str | None = None) -> str:
    from faster_whisper import WhisperModel
    m = WhisperModel(model, device="cpu", compute_type="int8")
    prompt = initial_prompt
    if prompt is None and (language is None or language.startswith("zh")):
        prompt = _ASR_DOMAIN_PROMPT_ZH
    segs, info = m.transcribe(str(wav_path), beam_size=5, vad_filter=False,
                              language=language, condition_on_previous_text=False,
                              initial_prompt=prompt)
    text = "".join(s.text for s in segs).strip()
    print(f"[asr] model={model} lang={info.language}({info.language_probability:.2f}) chars={len(text)}", flush=True)
    return text


# ------------------------------------------------------------------------ main
async def amain(args) -> int:
    out_dir = pathlib.Path(args.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    raw_p = out_dir / "recording.bin"; wav_p = out_dir / "recording.wav"

    if args.capture:
        raise SystemExit("--capture not implemented in this host-side helper; trigger the "
                         "capture with codex's air_record_with_stim.py (or the chain), then "
                         "re-run without --capture to pull+decode+ASR+minutes.")

    pul = await pull_recording(args.address, raw_p, args.chunk, args.timeout)
    print(f"[pull] {pul['bytes']} B crc=0x{pul['crc']:08x} match={pul['crc_match']}", flush=True)

    dec = decode_cop1(raw_p.read_bytes(), wav_p, args.rate)
    print(f"[decode] COP1 frames={dec['frames']} decoded={dec['decoded']} "
          f"native={dec['native_rate']}Hz dur={dec['duration_s']}s -> {wav_p}", flush=True)

    ls = level_stats(wav_p)
    print(f"[level] {ls}  (crest_ok+no_clip are PASS preconditions)", flush=True)

    raw_transcript = local_asr(wav_p, args.model, args.language)
    (out_dir / "asr-transcript-raw.txt").write_text(raw_transcript, encoding="utf-8")
    # Post-ASR domain-term normalization: board-mic ADPCM lossy audio garbles the
    # English technical terms (proven unfixable at the recognizer, regardless of
    # prompt/language). Normalize the known consistent mis-recognitions back to
    # canonical terms so a domain reader can recover the content (owner's "usable"
    # bar). RAW is preserved above; the glossed transcript feeds the minutes
    # builder; the changelog audits every change. See companion_asr_glossary.py.
    import json
    from companion_asr_glossary import normalize
    transcript, glossary_changelog = normalize(raw_transcript)
    (out_dir / "asr-transcript.txt").write_text(transcript, encoding="utf-8")
    (out_dir / "asr-glossary-changelog.json").write_text(
        json.dumps(glossary_changelog, ensure_ascii=False, indent=2), encoding="utf-8")
    if glossary_changelog:
        print(f"[glossary] {sum(e['count'] for e in glossary_changelog)} domain-term "
              f"corrections -> asr-glossary-changelog.json", flush=True)

    minutes = build_meeting_minutes(
        audio_path=wav_p, transcript_text=transcript,
        transcript_provider="local_faster_whisper" if transcript else "pending",
        recording_chain=None, source_artifact=None,
        meeting_title=args.title or None, wake_phrases=args.wake_phrase)
    mj = out_dir / "minutes.json"; mj.write_text(
        json.dumps(minutes, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    (out_dir / "minutes.md").write_text(render_minutes_markdown(minutes), encoding="utf-8")

    state = minutes.get("postprocess_state")
    print(f"[minutes] state={state} decisions={len(minutes.get('decisions', []))} "
          f"actions={len(minutes.get('action_items', []))} -> {mj}", flush=True)
    if transcript:
        print("=== TRANSCRIPT ===\n" + transcript[:400], flush=True)
    return 0 if transcript else 2


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--address", default=ADDR_DEFAULT)
    p.add_argument("--out-dir", default=r"C:\Users\Billy\AppData\Local\Temp\air_minutes")
    p.add_argument("--chunk", type=int, default=160)
    p.add_argument("--timeout", type=float, default=30.0)
    p.add_argument("--rate", type=int, default=16000)
    p.add_argument("--model", default="medium",
                   help="faster_whisper model; medium is REQUIRED for board-mic ADPCM audio "
                        "(base/small are too weak -> garbled, proven 2026-08-07). base only for "
                        "clean host-mic sources.")
    p.add_argument("--language", default="zh", help="force language code; ''=auto")
    p.add_argument("--title", default="")
    p.add_argument("--wake-phrase", action="append", default=None)
    p.add_argument("--capture", action="store_true", help="(reserved) trigger fresh capture first")
    return p.parse_args(argv)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    args.language = args.language or None
    raise SystemExit(asyncio.run(amain(args)))
