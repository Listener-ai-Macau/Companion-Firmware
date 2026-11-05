#!/usr/bin/env python3
"""Exercise the WBA product button/audio/recording chain on a fake board.

This is host-only integration evidence.  It uses the real product runtime,
recording service, journal, and fixed-point Opus encoder while replacing the
physical board, NOR transport, and display assets with deterministic fakes.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import struct
import subprocess
import sys
import wave


ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / ".cache" / "wba-product-recording-integration-host"
APP = ROOT / "app" / "companion_pendant"
PLATFORM = ROOT / "platform" / "stm32wba55_companion_v11"
WIRE = ROOT / "third_party" / "denzic-platform" / "audio" / "embedded" / "c" / "include"
OPUS = ROOT / "third_party" / "opus"


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return result


def run_vc(command: str) -> subprocess.CompletedProcess[str]:
    vcvars = pathlib.Path(os.environ.get("ProgramFiles(x86)", "")) / (
        "Microsoft Visual Studio/2022/BuildTools/VC/Auxiliary/Build/vcvars64.bat"
    )
    if not vcvars.exists():
        raise RuntimeError(f"MSVC environment not found: {vcvars}")
    script = OUT / "vc-command.cmd"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(
        f'@call "{vcvars}" >nul\n@if errorlevel 1 exit /b %errorlevel%\n@{command}\n',
        encoding="utf-8",
    )
    return run(["cmd", "/d", "/c", str(script)])


def quote(path: pathlib.Path) -> str:
    return f'"{path}"'


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def decode_cop1(source: pathlib.Path, wav_path: pathlib.Path) -> dict[str, int]:
    import av
    import numpy as np

    raw = source.read_bytes()
    if len(raw) < 12 or raw[:4] != b"COP1" or raw[4:8] != bytes((1, 1, 20, 0)):
        raise RuntimeError("product artifact has an invalid COP1 header")
    if struct.unpack_from("<I", raw, 8)[0] != 16000:
        raise RuntimeError("product artifact sample rate is not 16 kHz")
    decoder = av.CodecContext.create("opus", "r")
    offset = 12
    packets = 0
    samples = []
    sample_rate = 0
    while offset + 2 <= len(raw):
        length = struct.unpack_from("<H", raw, offset)[0]
        offset += 2
        if length == 0 or length > 400 or offset + length > len(raw):
            raise RuntimeError(f"invalid packet at offset {offset - 2}")
        frames = decoder.decode(av.Packet(raw[offset : offset + length]))
        offset += length
        packets += 1
        for frame in frames:
            sample_rate = frame.sample_rate
            array = frame.to_ndarray()
            if array.ndim == 2:
                array = array.mean(axis=0)
            samples.append(array)
    if offset != len(raw) or packets == 0 or not samples:
        raise RuntimeError("independent decoder did not consume product artifact")
    pcm = np.concatenate(samples)
    if np.issubdtype(pcm.dtype, np.floating):
        pcm16 = (pcm * 32767.0).clip(-32768, 32767).astype("<i2")
    else:
        pcm16 = pcm.clip(-32768, 32767).astype("<i2")
    with wave.open(str(wav_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm16.tobytes())
    return {
        "packets": packets,
        "samples": int(len(pcm16)),
        "sample_rate_hz": sample_rate,
        "duration_ms": int(round(len(pcm16) * 1000 / sample_rate)),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    exe = OUT / "wba-product-recording-integration.exe"
    cop1 = OUT / "retry-recording.cop1"
    wav = OUT / "retry-recording-decoded.wav"
    opus_lib = ROOT / ".cache" / "opus-host-fixed" / "opus.lib"
    if not opus_lib.exists():
        raise RuntimeError(
            "fixed-point host Opus library missing; run tools/test_wba_recording_service.py first"
        )

    sources = [
        PLATFORM / "tests" / "test_product_recording_integration.c",
        PLATFORM / "product_app.c",
        APP / "runtime" / "companion_runtime.c",
        APP / "runtime" / "companion_preferences.c",
        APP / "recording" / "wba_silence_stop.c",
        APP / "playback" / "audio_feedback.c",
        APP / "playback" / "speaker_playback.c",
        APP / "touch" / "touch_gesture.c",
        APP / "touch" / "touch_tap_arbiter.c",
        APP / "touch" / "browser_interaction_runtime.c",
        APP / "epaper" / "screen_menu.c",
        APP / "epaper" / "screen_framebuffer.c",
        APP / "epaper" / "motion_coordinator.c",
        APP / "power" / "power_settings_store.c",
        APP / "power" / "power_policy.c",
        APP / "power" / "wba_power_monitor.c",
        APP / "power" / "wba_button.c",
        APP / "board" / "companion_v11_board.c",
        APP / "board" / "tca6408.c",
        APP / "recording" / "wba_recording_service.c",
        APP / "recording" / "companion_recording_journal.c",
        APP / "recording" / "companion_recording_identity.c",
        APP / "storage" / "wba_shared_pool_guard.c",
        APP / "recording" / "companion_opus16_rt.c",
    ]
    includes = [
        PLATFORM / "tests" / "fakes",
        PLATFORM,
        *(APP / name for name in (
            "board", "imu", "playback", "storage", "v1_features", "power",
            "touch", "recording", "epaper", "runtime", "runtime/generated", "update",
        )),
        WIRE,
        OPUS / "include",
    ]
    command = " ".join([
        "cl", "/nologo", "/TC", "/std:c11", "/O2", "/W4", "/WX", "/utf-8",
        "/MD", "/D_CRT_SECURE_NO_WARNINGS",
        "/DCOMPANION_OPUS16_ENCODER_BYTES=65536",
        *(f"/I{quote(path)}" for path in includes),
        *(quote(path) for path in sources),
        f"/Fe:{quote(exe)}", "/link", quote(opus_lib),
    ])
    compile_result = run_vc(command)
    execution = run([str(exe), str(cop1)])
    if not execution.stdout.startswith("PASS_WBA_PRODUCT_RECORDING_INTEGRATION_HOST_ONLY"):
        raise RuntimeError(f"integration fixture did not pass: {execution.stdout}")
    decoded = decode_cop1(cop1, wav)
    if decoded["duration_ms"] < 400 or decoded["sample_rate_hz"] != 48000:
        raise RuntimeError(f"unexpected independent decode result: {decoded}")

    result = {
        "schema": "companion.wba_v11.product_recording_integration.host.v1",
        "status": "PASS_HOST_ONLY",
        "hardware_status": "NOT_RUN",
        "claims": {
            "real_product_app": True,
            "real_runtime": True,
            "real_recording_service": True,
            "real_fixed_point_opus": True,
            "physical_microphone": False,
            "physical_nor": False,
            "physical_speaker": False,
            "display_assets": False,
        },
        "journey": [
            "button-only wake readiness and visible-sleep commit gate",
            "transfer/storage/OTA/NVM/ADC/prepare/finalize sleep blockers",
            "first long sleeping press wakes without recording",
            "qualified battery to status/menu and unavailable-data reset",
            "button long press",
            "NOR reserve and pre-erase",
            "recording-start cue completes before microphone enable",
            "PCM to codec=3 COP1 journal",
            "normal stop and UNSYNCED finalize",
            "HAL capture counter fault retains partial",
            "ERROR_RECOVERY retry",
            "second normal stop and independent decode",
            "full seven-slot catalog rejects another prepare without eviction",
            "both namespace snapshots durable before microphone enable",
            "namespace writes and erases stay outside capture",
            "reboot preserves format epoch and monotonic next session",
            "missing entropy and namespace I/O refuse before journal allocation",
            "unknown namespace and old 14MiB CRJ1/CRJ2 remain read only",
        ],
        "stdout": execution.stdout.strip(),
        "decode": decoded,
        "cop1_path": str(cop1),
        "cop1_sha256": sha256(cop1),
        "decoded_wav_path": str(wav),
        "compile_log": (compile_result.stdout + compile_result.stderr).strip(),
        "source_sha256": {
            str(path.relative_to(ROOT).as_posix()): sha256(path)
            for path in [
                *sources,
                APP / "recording" / "companion_recording_identity.h",
                APP / "storage" / "wba_shared_pool.h",
                APP / "recording" / "companion_recording_wire.h",
                PLATFORM / "product_app.h",
                APP / "update" / "wba_storage_layout.h",
                PLATFORM / "tests" / "fakes" / "stm32wbaxx_hal.h",
                pathlib.Path(__file__).resolve(),
            ]
        },
    }
    result_path = OUT / "result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS_WBA_PRODUCT_RECORDING_INTEGRATION_PREHARDWARE")
    print(result_path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"NO_GO_WBA_PRODUCT_RECORDING_INTEGRATION: {exc}", file=sys.stderr)
        raise SystemExit(2)
