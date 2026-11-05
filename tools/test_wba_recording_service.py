#!/usr/bin/env python3
"""Build and validate the WBA recording service without claiming board proof."""

from __future__ import annotations

import hashlib
import argparse
import json
import os
import pathlib
import shutil
import struct
import subprocess
import sys
import wave
import zlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / ".cache" / "wba-recording-service-host"
REC = ROOT / "app" / "companion_pendant" / "recording"
WIRE = ROOT / "third_party" / "denzic-platform" / "audio" / "embedded" / "c" / "include"
OPUS = ROOT / "third_party" / "opus"


def run(command: list[str], *, capture: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command, cwd=ROOT, text=True, capture_output=capture, check=False
    )
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
        f'@call "{vcvars}" >nul\n@if errorlevel 1 exit /b %errorlevel%\n'
        f'@cd /d "{OUT}"\n@if errorlevel 1 exit /b %errorlevel%\n'
        f'@{command}\n',
        encoding="utf-8",
    )
    return run(["cmd", "/d", "/c", str(script)])


def quote(path: pathlib.Path) -> str:
    return f'"{path}"'


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def decode_cop1(source: pathlib.Path, wav_path: pathlib.Path, *, prefix: bool = False) -> dict[str, object]:
    import av
    import numpy as np

    raw = source.read_bytes()
    if len(raw) < 12 or raw[:4] != b"COP1":
        raise RuntimeError("real codec output has no COP1 header")
    if raw[4:8] != bytes((1, 1, 20, 0)) or struct.unpack_from("<I", raw, 8)[0] != 16000:
        raise RuntimeError("unexpected COP1 codec contract")
    decoder = av.CodecContext.create("opus", "r")
    offset = 12
    packets = 0
    chunks = []
    native_rate = 0
    while offset + 2 <= len(raw):
        length = struct.unpack_from("<H", raw, offset)[0]
        offset += 2
        if prefix and offset + length > len(raw) and 0 < length <= 400:
            offset -= 2
            break
        if length == 0 or length > 400 or offset + length > len(raw):
            raise RuntimeError(f"invalid COP1 packet at {offset - 2}")
        frames = decoder.decode(av.Packet(raw[offset : offset + length]))
        offset += length
        packets += 1
        for frame in frames:
            native_rate = frame.sample_rate
            array = frame.to_ndarray()
            if array.ndim == 2:
                array = array.mean(axis=0)
            chunks.append(array)
    if (not prefix and offset != len(raw)) or not chunks:
        raise RuntimeError("COP1 decode did not consume a nonempty stream")
    pcm = np.concatenate(chunks)
    if np.issubdtype(pcm.dtype, np.floating):
        pcm16 = (pcm * 32767.0).clip(-32768, 32767).astype("<i2")
    else:
        pcm16 = pcm.clip(-32768, 32767).astype("<i2")
    with wave.open(str(wav_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(native_rate)
        wav.writeframes(pcm16.tobytes())
    return {
        "packets": packets,
        "decoded_samples": int(len(pcm16)),
        "native_rate_hz": native_rate,
        "decoded_duration_ms": int(round(len(pcm16) * 1000 / native_rate)),
        "complete_packet_bytes": offset,
        "pending_prefix_bytes": len(raw) - offset,
    }


def verify_live_artifacts(cop1: pathlib.Path) -> dict[str, object]:
    prefix = pathlib.Path(str(cop1) + ".prefix.cop1")
    active_path = pathlib.Path(str(cop1) + ".active-list.bin")
    final_path = pathlib.Path(str(cop1) + ".final-list.bin")
    raw, live = cop1.read_bytes(), prefix.read_bytes()
    active, final = active_path.read_bytes(), final_path.read_bytes()
    # Type's public list layout: 4-byte header and 32-byte entries. Internal
    # journal enums are deliberately not imported into this wire check.
    for wire, state in ((active, 1), (final, 0)):
        if len(wire) != 36 or wire[:4] != bytes((1, 1, 32, 0)) or wire[16:19] != bytes((3, state, 1)):
            raise RuntimeError("Type codec/source/list state mismatch")
    if active[4:8] != final[4:8] or not raw.startswith(live) or len(live) < 1024:
        raise RuntimeError("live recording identity/prefix mismatch")
    if struct.unpack_from("<I", active, 20)[0] < len(live) or active[24:36] != bytes(12):
        raise RuntimeError("live metadata claims final integrity or omits durable bytes")
    if struct.unpack_from("<I", final, 20)[0] != len(raw) or final[24:32] != hashlib.sha256(raw).digest()[:8] or struct.unpack_from("<I", final, 32)[0] != zlib.crc32(raw):
        raise RuntimeError("final metadata integrity mismatch")
    decoded = decode_cop1(prefix, OUT / "live-prefix-decoded.wav", prefix=True)
    if decoded["packets"] < 1 or decoded["packets"] >= 200:
        raise RuntimeError("prefix did not independently decode before completion")
    return {
        "status": "PASS_HOST_REAL_OPUS_TRANSFER", "type_ui_run": False,
        "active_wire_state": 1, "finalized_wire_state": 0,
        "prefix_decode": decoded,
        "coverage": ["durable pages only", "frozen live window", "audio read-budget deferral",
                     "notify backpressure", "absolute-offset reconnect during capture",
                     "finalize during live window without final flag", "active ACK rejected",
                     "final pull CRC/content/SHA"],
        "artifacts": {p.name: sha256(p) for p in (prefix, active_path, final_path,
            pathlib.Path(str(cop1) + ".wire.bin"), pathlib.Path(str(cop1) + ".live-wire.bin"))},
        "hardware_and_full_meeting_acceptance": "NOT_RUN",
    }


def main() -> int:
    global OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wba-lowdelay',action='store_true')
    parser.add_argument('--output',type=pathlib.Path)
    parser.add_argument('--unit-only',action='store_true',help='Only affected recording service/journal checks; do not rerun real Opus/transfer checks')
    parser.add_argument('--ui-resource-bytes',type=lambda value:int(value,0),default=0x100000)
    args=parser.parse_args()
    if args.output:OUT=args.output.resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    unit_exe = OUT / "wba-recording-service-unit.exe"
    real_exe = OUT / "wba-recording-service-real-opus.exe"
    cop1 = OUT / "real-opus.cop1"
    wav = OUT / "real-opus-decoded.wav"
    opus_build = ROOT / ".cache" / "opus-host-fixed"
    opus_lib = opus_build / "opus.lib"

    unit_sources = [
        REC / "tests" / "test_wba_recording_service.c",
        REC / "wba_recording_service.c",
        REC / "companion_recording_journal.c",
    ]
    from wba_resource_geometry import geometry
    selected_geometry = geometry(args.ui_resource_bytes)
    common = (f'/nologo /TC /std:c11 /O2 /W4 /WX /I{quote(REC)} /I{quote(WIRE)} '
              f'/DCOMP_WBA_NOR_UI_BYTES={selected_geometry["staticBytes"]}u ')
    unit_source_args = " ".join(quote(p) for p in unit_sources)
    unit_cmd = f'cl {common} {unit_source_args} /Fe:{quote(unit_exe)}'
    unit_compile = run_vc(unit_cmd)
    if args.unit_only:
        unit_run = subprocess.run([str(unit_exe)], cwd=ROOT, text=True, capture_output=True, check=False)
        (OUT / 'unit.log').write_text(unit_compile.stdout + unit_compile.stderr + unit_run.stdout + unit_run.stderr, encoding='utf-8')
        result = {'scope': 'RECORDING_SERVICE_FAULT_RECOVERY_SOFTWARE_ONLY',
                  'status': 'PASS_SOFTWARE_ONLY' if unit_run.returncode == 0 else 'FAIL_SOFTWARE_ONLY',
                  'exitCode': unit_run.returncode, 'stdout': unit_run.stdout, 'stderr': unit_run.stderr,
                  'hardwareAcceptance': 'NOT_RUN', 'realOpusTransfer': 'NOT_RUN_UNCHANGED',
                  'source_sha256': {str(p.relative_to(ROOT)): sha256(p) for p in unit_sources}}
        (OUT / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(json.dumps({k: result[k] for k in ('status','stdout','stderr')}, ensure_ascii=False))
        return unit_run.returncode
    unit_run = run([str(unit_exe)])
    if not unit_run.stdout.startswith("PASS_"):
        raise RuntimeError(f"unit test did not pass: {unit_run.stdout}")

    if not opus_lib.exists():
        run_vc(
            f'cmake -S {quote(OPUS)} -B {quote(opus_build)} -G Ninja '
            "-DCMAKE_BUILD_TYPE=Release -DOPUS_FIXED_POINT=ON "
            "-DOPUS_ENABLE_FLOAT_API=OFF -DOPUS_DISABLE_INTRINSICS=ON "
            "-DOPUS_BUILD_PROGRAMS=OFF -DOPUS_BUILD_TESTING=OFF"
        )
        run_vc(f'cmake --build {quote(opus_build)} -j 6')

    real_sources = [
        REC / "tests" / "test_wba_recording_service_real_opus.c",
        REC / "wba_recording_service.c",
        REC / "companion_recording_journal.c",
        REC / "companion_opus16_rt.c",
        REC / "wba_recording_transfer.c",
    ]
    real_source_args = " ".join(quote(p) for p in real_sources)
    real_cmd = (
        f'cl {common} /MD /D_CRT_SECURE_NO_WARNINGS '
        + ('/DCOMPANION_OPUS16_WBA_LOWDELAY=1 ' if args.wba_lowdelay else '') +
        "/DCOMPANION_OPUS16_ENCODER_BYTES=65536 "
        f'/I{quote(OPUS / "include")} '
        f'{real_source_args} /Fe:{quote(real_exe)} '
        f'/link {quote(opus_lib)}'
    )
    real_compile = run_vc(real_cmd)
    real_run = run([str(real_exe), str(cop1)])
    if not real_run.stdout.startswith("PASS_"):
        raise RuntimeError(f"real Opus test did not pass: {real_run.stdout}")
    printed_sha = real_run.stdout.strip().split("sha256=", 1)[1].upper()
    actual_sha = sha256(cop1)
    if printed_sha != actual_sha:
        raise RuntimeError("journal SHA does not match exported COP1 bytes")
    decode = decode_cop1(cop1, wav)
    if decode["packets"] != 200 or decode["decoded_duration_ms"] != 4000:
        raise RuntimeError(f"decoded duration mismatch: {decode}")
    live_transfer = verify_live_artifacts(cop1)

    arm_gcc = shutil.which("arm-none-eabi-gcc")
    if not arm_gcc:
        raise RuntimeError("arm-none-eabi-gcc unavailable")
    arm_objects = []
    for source in (REC / "wba_recording_service.c", REC / "companion_recording_journal.c"):
        obj = OUT / f"{source.stem}.o"
        run(
            [
                arm_gcc, "-std=c11", "-mcpu=cortex-m33", "-mthumb",
                "-Wall", "-Wextra", "-Werror", "-Wconversion", "-Wshadow",
                "-Wformat=2", "-pedantic", f"-I{REC}", f"-I{WIRE}",
                "-c", str(source), "-o", str(obj),
            ]
        )
        arm_objects.append(obj)

    sources = unit_sources + real_sources + [REC / "companion_recording_journal.h", REC / "wba_recording_service.h", REC / "wba_recording_transfer.h", REC / "companion_recording_wire.h", pathlib.Path(__file__)]
    result = {
        "schema": "companion.wba_recording_service.prehardware.v1",
        "status": "PASS_HOST_ONLY",
        "hardware_status": "NOT_RUN",
        "timing_on_stm32wba55": "NOT_RUN",
        "codec": 3,
        "container": "COP1",
        "sample_rate_hz": 16000,
        "frame_ms": 20,
        "opus_application": "RESTRICTED_LOWDELAY" if args.wba_lowdelay else "VOIP",
        "unit_stdout": unit_run.stdout.strip(),
        "real_opus_stdout": real_run.stdout.strip(),
        "decode": decode,
        "live_transfer": live_transfer,
        "cop1_sha256": actual_sha,
        "cop1_path": str(cop1),
        "decoded_wav_path": str(wav),
        "host_encoder_note": "real fixed-point libopus; host-only encoder storage override is 65536 bytes",
        "m33_objects": {obj.name: sha256(obj) for obj in arm_objects},
        "compile_logs": {
            "unit": (unit_compile.stdout + unit_compile.stderr).strip(),
            "real_opus": (real_compile.stdout + real_compile.stderr).strip(),
        },
        "source_sha256": {str(path.relative_to(ROOT)): sha256(path) for path in dict.fromkeys(sources)},
    }
    (OUT / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("PASS_WBA_RECORDING_SERVICE_PREHARDWARE")
    print(OUT / "result.json")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"NO_GO_WBA_RECORDING_SERVICE: {exc}", file=sys.stderr)
        raise SystemExit(2)
