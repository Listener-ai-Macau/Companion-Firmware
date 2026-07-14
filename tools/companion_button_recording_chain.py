#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate SW3 physical button recording -> QSPI flash -> BLE pull."""

from __future__ import annotations

import argparse
import asyncio
import binascii
import ctypes
import datetime as dt
import glob
import hashlib
import json
import math
import os
import pathlib
import shutil
import struct
import subprocess
import sys
import time
import wave
from typing import Any

from companion_flash_recording_chain import (
    ChainError,
    RECORDING_ERROR_FLAG,
    RECORDING_FINAL_FLAG,
    RECORDING_SOURCE_MIC_SAI,
    SCHEMA_VERSION,
    build_uuid_index,
    control_payload,
    git_commit,
    load_uuid_table,
    notify_write_wait,
    parse_delete_privacy,
    parse_struct,
    parse_recording_chunk,
    parse_recording_control,
    parse_recording_list,
    read_recording_list,
    required_services,
    scan_for_companion,
    utc_now,
    verify_packet_crc,
)
from verify_companion_button_input import (
    SerialMonitor,
    drain_until_release,
    resolve_serial_port,
    wait_for_button_with_popup,
)


sys.dont_write_bytecode = True
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
PCM_SAMPLE_RATE = 16000
PCM_CHANNELS = 1
PCM_WIDTH_BYTES = 2
DELETE_REFUSED_FLAG = 0x0001


def button_detect_pattern(button: str) -> Any:
    import re

    return re.compile(
        rf"\[(?:button|button-raw)\]\s+(?P<button>{re.escape(button)})\s+"
        r"(?:pressed\b|active_low=1\b)",
        re.IGNORECASE,
    )


def wait_for_physical_button(
    monitor: SerialMonitor | None,
    args: argparse.Namespace,
    press_index: int,
    title: str,
    message: str,
) -> dict[str, Any]:
    if monitor is None:
        show_operator_prompt(title, message, no_prompts=args.no_prompts)
        return {
            "operation": f"button_prompt_{press_index}",
            "status": "MANUAL_ACK",
            "button": args.button,
            "serial_detected": False,
        }

    prompt_args = argparse.Namespace(
        button=args.button,
        button_alias=args.button_alias,
        pin=args.pin,
        press_count=2,
        timeout=args.button_timeout,
        no_gui=args.no_prompts,
        prompt_title=title,
        prompt_message=message,
    )
    detection = wait_for_button_with_popup(
        monitor,
        prompt_args,
        press_index,
        button_detect_pattern(args.button),
    )
    detection["release"] = drain_until_release(monitor, args.button)
    return {
        "operation": f"button_press_{press_index}",
        "status": "PASS",
        "button": args.button,
        "button_alias": args.button_alias,
        "pin": args.pin,
        "serial_detected": True,
        "detection": detection,
    }


def show_operator_prompt(title: str, message: str, *, no_prompts: bool = False) -> None:
    if no_prompts:
        print(f"operator_prompt_title={title}")
        print(f"operator_prompt_message={message}")
        return

    if os.name == "nt":
        mb_ok_cancel = 0x00000001
        mb_icon_info = 0x00000040
        mb_set_foreground = 0x00010000
        mb_topmost = 0x00040000
        ctypes.windll.user32.MessageBeep(0xFFFFFFFF)
        result = ctypes.windll.user32.MessageBoxW(
            None,
            message,
            title,
            mb_ok_cancel | mb_icon_info | mb_set_foreground | mb_topmost,
        )
        if result != 1:
            raise ChainError(f"operator cancelled prompt: {title}")
        return

    print(f"\n{title}\n{message}\nPress Enter to continue, Ctrl+C to cancel.", flush=True)
    input()


def write_wav(path: pathlib.Path, pcm_bytes: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(PCM_CHANNELS)
        wav_file.setsampwidth(PCM_WIDTH_BYTES)
        wav_file.setframerate(PCM_SAMPLE_RATE)
        wav_file.writeframes(pcm_bytes)


def analyze_pcm16(pcm_bytes: bytes, args: argparse.Namespace) -> dict[str, Any]:
    if len(pcm_bytes) % PCM_WIDTH_BYTES != 0:
        raise ChainError(f"PCM16 payload length is not even: {len(pcm_bytes)}")

    sample_count = len(pcm_bytes) // PCM_WIDTH_BYTES
    if sample_count == 0:
        raise ChainError("PCM16 payload is empty")

    samples = struct.unpack("<" + "h" * sample_count, pcm_bytes)
    peak = max(abs(value) for value in samples)
    rms = math.sqrt(sum(float(value) * float(value) for value in samples) / sample_count)
    zero_count = sum(1 for value in samples if value == 0)
    clipping_count = sum(1 for value in samples if abs(value) >= 32760)
    window = 320
    envelope = []
    for start in range(0, sample_count, window):
        chunk = samples[start : start + window]
        if not chunk:
            continue
        envelope.append(math.sqrt(sum(float(value) * float(value) for value in chunk) / len(chunk)))
    active_threshold = max(float(args.min_peak) * 0.25, 80.0)
    active_windows = sum(1 for value in envelope if value >= active_threshold)
    duration_s = sample_count / float(PCM_SAMPLE_RATE)
    zero_ratio = zero_count / float(sample_count)
    clipping_ratio = clipping_count / float(sample_count)
    checks = {
        "duration_ok": duration_s >= float(args.min_duration_s),
        "peak_ok": peak >= int(args.min_peak),
        "rms_ok": rms >= float(args.min_rms),
        "zero_ratio_ok": zero_ratio <= float(args.max_zero_ratio),
        "clipping_ratio_ok": clipping_ratio <= float(args.max_clipping_ratio),
        "active_windows_ok": active_windows >= int(args.min_active_windows),
    }
    return {
        "operation": "audio_quality",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "sample_rate_hz": PCM_SAMPLE_RATE,
        "channels": PCM_CHANNELS,
        "sample_width_bytes": PCM_WIDTH_BYTES,
        "sample_count": sample_count,
        "duration_s": round(duration_s, 4),
        "peak": peak,
        "rms": round(rms, 2),
        "zero_ratio": round(zero_ratio, 6),
        "clipping_ratio": round(clipping_ratio, 6),
        "active_windows": active_windows,
        "active_threshold": active_threshold,
        "checks": checks,
    }


def find_cube_programmer_cli(requested: str | None) -> str:
    candidates: list[pathlib.Path] = []
    if requested:
        candidates.append(pathlib.Path(requested))
    for env_name in ("STM32CUBEPROGRAMMER_CLI", "STM32CUBE_PROGRAMMER_CLI"):
        value = os.environ.get(env_name)
        if value:
            candidates.append(pathlib.Path(value))
    for env_name in ("STM32CUBEPROGRAMMER_PATH", "STM32CUBE_PROGRAMMER_PATH"):
        value = os.environ.get(env_name)
        if value:
            candidates.append(pathlib.Path(value) / "STM32_Programmer_CLI.exe")
            candidates.append(pathlib.Path(value) / "bin" / "STM32_Programmer_CLI.exe")
    which = shutil.which("STM32_Programmer_CLI.exe") or shutil.which("STM32_Programmer_CLI")
    if which:
        candidates.append(pathlib.Path(which))
    candidates.extend(
        [
            pathlib.Path(r"C:\ST\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe"),
            pathlib.Path(
                r"C:\Program Files\STMicroelectronics\STM32Cube\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe"
            ),
        ]
    )
    for pattern in (
        r"C:\ST\STM32CubeIDE_*\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_*\tools\bin\STM32_Programmer_CLI.exe",
        r"C:\Program Files\STMicroelectronics\STM32CubeIDE_*\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_*\tools\bin\STM32_Programmer_CLI.exe",
    ):
        candidates.extend(pathlib.Path(path) for path in sorted(glob.glob(pattern)))

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    raise ChainError("STM32_Programmer_CLI.exe not found; install STM32CubeProgrammer or pass --programmer")


def hard_reset_target(args: argparse.Namespace) -> dict[str, Any]:
    programmer = find_cube_programmer_cli(args.programmer)
    command = [
        programmer,
        "-c",
        f"port={args.swd_port}",
        "mode=UR",
        "reset=HWrst",
        f"freq={args.swd_freq}",
        "-rst",
    ]
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    operation = {
        "operation": "swd_hard_reset",
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "programmer": programmer,
        "command": command,
        "exit_code": completed.returncode,
        "duration_s": round(time.monotonic() - started, 3),
        "output_tail": "\n".join(completed.stdout.splitlines()[-30:]),
    }
    if completed.returncode != 0:
        raise ChainError(f"STM32CubeProgrammer reset failed with exit code {completed.returncode}")
    time.sleep(float(args.reset_settle_s))
    return operation


async def send_recording_control(
    client: Any,
    uuids: dict[str, str],
    command: int,
    request_id: int,
    max_seconds: int,
    args: argparse.Namespace,
) -> dict[str, Any]:
    echo = await notify_write_wait(
        client,
        uuids["recording_control"],
        uuids["recording_control"],
        control_payload(command, request_id, max_seconds),
        parse_recording_control,
        lambda parsed: int(parsed["request_id"]) == request_id,
        args.notify_timeout,
    )
    return echo


async def clear_existing_recording(client: Any, uuids: dict[str, str], args: argparse.Namespace) -> dict[str, Any]:
    before = await read_recording_list(client, uuids["recording_list"])
    return {
        "operation": "preflight_recording_list",
        "status": "PASS",
        "before": before,
        "action": "none" if int(before["count"]) == 0 else "sw3_start_will_overwrite_existing_flash_recording",
    }


async def wait_for_one_recording(
    client: Any,
    uuids: dict[str, str],
    args: argparse.Namespace,
) -> dict[str, Any]:
    deadline = time.monotonic() + float(args.recording_list_timeout)
    last: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        listing = await read_recording_list(client, uuids["recording_list"])
        last = listing
        if int(listing["count"]) == 1:
            entry = listing["entries"][0]
            if int(entry["total_length"]) > 0:
                return listing
        await asyncio.sleep(0.35)
    raise ChainError(f"timed out waiting for one stored recording; last={last}")


async def pull_recording_bytes(
    client: Any,
    uuids: dict[str, str],
    entry: dict[str, Any],
    args: argparse.Namespace,
) -> tuple[dict[str, Any], bytes]:
    offset = 0
    expected_sequence = 0
    total_length = int(entry["total_length"])
    recording_id = int(entry["recording_id"])
    data = bytearray()
    packets: list[dict[str, Any]] = []
    final_sha256 = ""

    queue: asyncio.Queue[bytes] = asyncio.Queue()

    def callback(_sender: Any, raw: bytearray) -> None:
        queue.put_nowait(bytes(raw))

    await client.start_notify(uuids["recording_chunk_pull"], callback)
    try:
        await asyncio.sleep(0.15)
        while offset < total_length:
            request_length = min(int(args.chunk_bytes), total_length - offset)
            request = struct.pack("<BBHIII", SCHEMA_VERSION, 0, request_length, recording_id, offset, 0)
            await client.write_gatt_char(uuids["recording_chunk_pull"], request, response=True)
            deadline = time.monotonic() + float(args.notify_timeout)
            packet: dict[str, Any] | None = None
            last: dict[str, Any] | None = None
            while time.monotonic() < deadline:
                try:
                    raw = await asyncio.wait_for(queue.get(), timeout=max(0.1, deadline - time.monotonic()))
                except asyncio.TimeoutError as exc:
                    raise ChainError(f"recording chunk notify timeout at offset={offset}; last={last}") from exc
                parsed = parse_recording_chunk(raw)
                last = parsed
                if int(parsed["byte_offset"]) == offset:
                    packet = parsed
                    break
            if packet is None:
                raise ChainError(f"recording chunk notify predicate not satisfied at offset={offset}; last={last}")
            if int(packet["flags"]) & RECORDING_ERROR_FLAG:
                raise ChainError(f"recording chunk error flag at offset={offset}: {packet}")
            if int(packet["packet_sequence"]) != expected_sequence:
                raise ChainError(
                    f"packet sequence mismatch: got {packet['packet_sequence']} expected {expected_sequence}"
                )
            if int(packet["total_length"]) != total_length:
                raise ChainError("recording total_length changed during transfer")
            payload = bytes(packet["payload"])
            if len(payload) != int(packet["payload_length"]):
                raise ChainError("recording payload_length mismatch")
            packet_crc = verify_packet_crc(packet)
            data.extend(payload)
            packets.append(
                {
                    "packet_sequence": int(packet["packet_sequence"]),
                    "byte_offset": int(packet["byte_offset"]),
                    "payload_length": int(packet["payload_length"]),
                    "packet_crc32": packet_crc,
                    "flags": int(packet["flags"]),
                }
            )
            offset += len(payload)
            expected_sequence += 1
            if int(packet["flags"]) & RECORDING_FINAL_FLAG:
                final_sha256 = str(packet["final_sha256"])
                break
    finally:
        await client.stop_notify(uuids["recording_chunk_pull"])

    if len(data) != total_length:
        raise ChainError(f"recording byte count mismatch: got {len(data)}, expected {total_length}")
    host_sha256 = hashlib.sha256(data).hexdigest()
    if not final_sha256:
        raise ChainError("final recording packet did not include SHA-256")
    if final_sha256 != host_sha256:
        raise ChainError(f"final SHA mismatch: device={final_sha256} host={host_sha256}")
    if not host_sha256.startswith(str(entry["sha256_prefix"])):
        raise ChainError("recording_list sha256_prefix did not match pulled object")
    host_crc32 = f"0x{binascii.crc32(data) & 0xFFFFFFFF:08x}"
    if host_crc32.lower() != str(entry["content_crc32"]).lower():
        raise ChainError(f"recording_list CRC mismatch: list={entry['content_crc32']} host={host_crc32}")

    return (
        {
            "operation": "recording_pull",
            "status": "PASS",
            "recording_id": recording_id,
            "total_length": total_length,
            "packet_count": len(packets),
            "host_sha256": host_sha256,
            "device_final_sha256": final_sha256,
            "host_crc32": host_crc32,
            "packets": packets,
        },
        bytes(data),
    )


async def verify_bad_offset(
    client: Any,
    uuids: dict[str, str],
    entry: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    bad_offset = int(entry["total_length"]) + 4
    request = struct.pack("<BBHIII", SCHEMA_VERSION, 0, 16, int(entry["recording_id"]), bad_offset, 0)
    packet = await notify_write_wait(
        client,
        uuids["recording_chunk_pull"],
        uuids["recording_chunk_pull"],
        request,
        parse_recording_chunk,
        lambda parsed: int(parsed["byte_offset"]) == bad_offset,
        args.notify_timeout,
    )
    if not (int(packet["flags"]) & RECORDING_ERROR_FLAG):
        raise ChainError(f"bad offset pull was not rejected: {packet}")
    return {
        "operation": "bad_offset_rejected",
        "status": "PASS",
        "request_offset": bad_offset,
        "response": {
            "flags": int(packet["flags"]),
            "payload_length": int(packet["payload_length"]),
            "recording_id": int(packet["recording_id"]),
            "byte_offset": int(packet["byte_offset"]),
        },
    }


def parse_diag_log_pull(payload: bytes) -> dict[str, Any]:
    header_format = "<BBHIIHHI"
    event_format = "<IIBBBBIIII"
    header_bytes = struct.calcsize(header_format)
    event_bytes = struct.calcsize(event_format)
    parsed = parse_struct(
        header_format,
        (
            "schema_version",
            "flags",
            "event_count",
            "request_cursor",
            "next_cursor",
            "total_available",
            "payload_bytes",
            "payload_crc32",
        ),
        payload,
    )
    expected_payload_bytes = int(parsed["event_count"]) * event_bytes
    if int(parsed["payload_bytes"]) != expected_payload_bytes:
        raise ChainError(
            "diagnostics payload/event count mismatch: "
            f"payload_bytes={parsed['payload_bytes']} event_count={parsed['event_count']}"
        )
    packet_bytes = header_bytes + expected_payload_bytes
    if len(payload) < packet_bytes:
        raise ChainError(f"diagnostics packet truncated: got {len(payload)}, need {packet_bytes}")
    event_payload = payload[header_bytes:packet_bytes]
    crc32 = binascii.crc32(event_payload) & 0xFFFFFFFF
    if int(parsed["payload_crc32"]) != crc32:
        raise ChainError(
            f"diagnostics CRC mismatch: got 0x{int(parsed['payload_crc32']):08x}, "
            f"expected 0x{crc32:08x}"
        )
    events = []
    event_names = (
        "sequence",
        "t_ms",
        "source",
        "event_id",
        "severity",
        "event_flags",
        "arg0",
        "arg1",
        "arg2",
        "arg3",
    )
    for offset in range(0, expected_payload_bytes, event_bytes):
        values = struct.unpack(event_format, event_payload[offset : offset + event_bytes])
        events.append(dict(zip(event_names, values, strict=True)))
    parsed["events"] = events
    parsed["packet_bytes"] = packet_bytes
    parsed["crc_valid"] = True
    return parsed


async def pull_bounded_diagnostics(client: Any, uuids: dict[str, str], args: argparse.Namespace) -> dict[str, Any]:
    payload = struct.pack("<BBHIHH", SCHEMA_VERSION, 0, 0xFFFF, 0, 4, 64)
    response = await notify_write_wait(
        client,
        uuids["diagnostics_log_pull"],
        uuids["diagnostics_log_pull"],
        payload,
        parse_diag_log_pull,
        lambda parsed: int(parsed["request_cursor"]) == 0,
        args.notify_timeout,
    )
    if int(response["packet_bytes"]) > 64:
        raise ChainError(f"diagnostics response exceeded requested bound: {response}")
    if not (1 <= int(response["event_count"]) <= 4):
        raise ChainError(f"diagnostics response event count is invalid: {response}")
    if int(response["total_available"]) < int(response["event_count"]):
        raise ChainError(f"diagnostics available count is inconsistent: {response}")
    if not response["crc_valid"]:
        raise ChainError(f"diagnostics response CRC was not verified: {response}")
    return {
        "operation": "bounded_diagnostics_log_pull",
        "status": "PASS",
        "diagnostics": response,
        "bound": {"max_events": 4, "max_bytes": 64, "source_mask": 0, "severity_mask": "0xffff"},
    }


async def write_delete_privacy(
    client: Any,
    uuids: dict[str, str],
    request_id: int,
    entry: dict[str, Any],
    sha256_hex: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    payload = struct.pack(
        "<BBHIII32s",
        SCHEMA_VERSION,
        1,
        0,
        request_id,
        int(entry["recording_id"]),
        int(entry["total_length"]),
        bytes.fromhex(sha256_hex),
    )
    return await notify_write_wait(
        client,
        uuids["delete_privacy"],
        uuids["delete_privacy"],
        payload,
        parse_delete_privacy,
        lambda parsed: int(parsed["request_id"]) == request_id,
        args.notify_timeout,
    )


async def verify_bad_delete_refused(
    client: Any,
    uuids: dict[str, str],
    entry: dict[str, Any],
    good_sha256: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    bad_sha = "00" + good_sha256[2:]
    if bad_sha == good_sha256:
        bad_sha = "ff" + good_sha256[2:]
    response = await write_delete_privacy(client, uuids, 703, entry, bad_sha, args)
    if not (int(response["flags"]) & DELETE_REFUSED_FLAG):
        raise ChainError(f"bad delete SHA was not refused: {response}")
    listing = await read_recording_list(client, uuids["recording_list"])
    if int(listing["count"]) != 1:
        raise ChainError(f"bad delete changed recording_list unexpectedly: {listing}")
    return {
        "operation": "bad_delete_sha_refused",
        "status": "PASS",
        "delete_privacy": response,
        "recording_list_after_refusal": listing,
    }


async def delete_after_sync(
    client: Any,
    uuids: dict[str, str],
    entry: dict[str, Any],
    sha256_hex: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    response = await write_delete_privacy(client, uuids, 704, entry, sha256_hex, args)
    if int(response["flags"]) & DELETE_REFUSED_FLAG:
        raise ChainError(f"delete-after-sync was refused: {response}")
    listing = await read_recording_list(client, uuids["recording_list"])
    if int(listing["count"]) != 0:
        raise ChainError(f"recording_list not empty after delete: {listing}")
    return {
        "operation": "delete_after_sync",
        "status": "PASS",
        "delete_privacy": response,
        "recording_list_after_delete": listing,
    }


async def connect_companion(args: argparse.Namespace, uuids_table: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    device, scan = await scan_for_companion(args, required_services(uuids_table))
    return device, scan


async def run_chain(args: argparse.Namespace) -> dict[str, Any]:
    try:
        from bleak import BleakClient
    except Exception as exc:  # noqa: BLE001
        raise ChainError(f"bleak import failed: {exc}") from exc

    started = utc_now()
    monotonic_start = time.monotonic()
    artifact_dir = resolve_artifact_dir(args.artifact_dir)
    operations: list[dict[str, Any]] = []
    table = load_uuid_table()
    uuids = build_uuid_index(table)
    monitor: SerialMonitor | None = None
    serial_raw_log = artifact_dir / "button-recording-serial.log"
    try:
        if not args.no_serial_button_monitor:
            port, present_ports = resolve_serial_port(args.serial_port)
            monitor = SerialMonitor(port, int(args.baud), serial_raw_log)
            monitor.start()
            operations.append(
                {
                    "operation": "serial_button_monitor_start",
                    "status": "PASS",
                    "port": port,
                    "baud": int(args.baud),
                    "raw_log": str(serial_raw_log),
                    "present_ports": present_ports,
                }
            )

        operations.append(
            {
                "operation": "offline_button_recording_preflight",
                "status": "PASS",
                "action": "physical_button_start_will_overwrite_existing_flash_recording",
            }
        )
        operations.append(
            wait_for_physical_button(
                monitor,
                args,
                1,
                "Companion SW3 开始录音",
                "现在短按一下 NUCLEO-WB55RG 开发板上的 SW3/B3 用户按钮（PD1），按下后马上松开，不要长按。"
                "窗口检测到按下会自动关闭。窗口关闭后立刻对麦克风说话或拍手；"
                f"脚本会继续录约 {args.record_seconds:.1f} 秒再提示停止。不要按 B4/RESET。",
            )
        )
        await asyncio.sleep(float(args.record_seconds))
        operations.append(
            wait_for_physical_button(
                monitor,
                args,
                2,
                "Companion SW3 停止录音",
                "现在短按一下同一个 SW3/B3 用户按钮（PD1），按下后马上松开，不要长按。窗口检测到按下会自动关闭。"
                "脚本随后会通过 BLE 检查录音是否已经落到外部 flash。不要按 B4/RESET。",
            )
        )
    finally:
        if monitor is not None:
            monitor.stop()

    device, scan = await connect_companion(args, table)
    operations.append(scan)
    async with BleakClient(device, timeout=args.timeout) as client:
            operations.append(await clear_existing_recording(client, uuids, args))
            listing = await wait_for_one_recording(client, uuids, args)
            entry = listing["entries"][0]
            if int(entry["source_mode"]) != RECORDING_SOURCE_MIC_SAI:
                raise ChainError(f"recording was not sourced from SAI microphone path: {entry}")
            operations.append({"operation": "recording_list_after_sw3_stop", "status": "PASS", "recording_list": listing})
            pull, pcm_bytes = await pull_recording_bytes(client, uuids, entry, args)
            operations.append(pull)
            operations.append(await verify_bad_offset(client, uuids, entry, args))
            operations.append(await verify_bad_delete_refused(client, uuids, entry, str(pull["host_sha256"]), args))

    pcm_path = artifact_dir / "sw3-button-recording.pcm"
    wav_path = artifact_dir / "sw3-button-recording-16k-mono.wav"
    pcm_path.write_bytes(pcm_bytes)
    write_wav(wav_path, pcm_bytes)
    quality = analyze_pcm16(pcm_bytes, args)
    quality["pcm_path"] = str(pcm_path)
    quality["wav_path"] = str(wav_path)
    operations.append(quality)
    if quality["status"] != "PASS":
        raise ChainError(f"audio quality gate failed: {quality}")

    reset_operation = hard_reset_target(args)
    operations.append(reset_operation)

    device_after_reset, scan_after_reset = await connect_companion(args, table)
    operations.append({**scan_after_reset, "operation": "scan_after_reset"})
    async with BleakClient(device_after_reset, timeout=args.timeout) as client:
        persisted_list = await wait_for_one_recording(client, uuids, args)
        persisted_entry = persisted_list["entries"][0]
        for key in ("recording_id", "total_length", "content_crc32", "sha256_prefix"):
            if persisted_entry[key] != entry[key]:
                raise ChainError(f"persisted entry changed for {key}: before={entry[key]} after={persisted_entry[key]}")
        operations.append(
            {
                "operation": "recording_list_after_reset",
                "status": "PASS",
                "recording_list": persisted_list,
            }
        )
        persisted_pull, persisted_pcm = await pull_recording_bytes(client, uuids, persisted_entry, args)
        persisted_pull["operation"] = "recording_pull_after_reset"
        operations.append(persisted_pull)
        if persisted_pcm != pcm_bytes:
            raise ChainError("recording bytes changed across reset")
        operations.append(
            {
                "operation": "reset_persistence_compare",
                "status": "PASS",
                "host_sha256": persisted_pull["host_sha256"],
                "bytes_match": True,
            }
        )
        operations.append(await pull_bounded_diagnostics(client, uuids, args))
        if args.keep_recording_after_sync:
            operations.append(
                {
                    "operation": "keep_recording_after_sync",
                    "status": "PASS",
                    "recording_id": int(persisted_entry["recording_id"]),
                    "reason": "left recording in flash for Companion-Type native BLE sync validation",
                }
            )
        else:
            operations.append(await delete_after_sync(client, uuids, persisted_entry, str(persisted_pull["host_sha256"]), args))

    return {
        "schema_version": 1,
        "status": "PASS",
        "started_at": started,
        "finished_at": utc_now(),
        "duration_s": round(time.monotonic() - monotonic_start, 3),
        "git_commit": git_commit(),
        "mode": "real_sw3_button_recording_to_qspi_flash_ble_pull_reset_delete_chain"
        if not args.keep_recording_after_sync
        else "real_sw3_button_recording_to_qspi_flash_ble_pull_keep_for_type_sync_chain",
        "manual_source_reference": {
            "board": "NUCLEO-WB55RG / MB1355",
            "official_manual": "ST UM2435 P-NUCLEO-WB55 Nucleo pack user manual",
            "button_under_test": "SW3/B3 user button on PD1",
        },
        "artifacts": {
            "artifact_dir": str(artifact_dir),
            "pcm_path": str(pcm_path),
            "wav_path": str(wav_path),
            "button_serial_log": str(serial_raw_log),
        },
        "operations": operations,
    }


def resolve_artifact_dir(artifact_dir: pathlib.Path | None) -> pathlib.Path:
    if artifact_dir is not None:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        return artifact_dir
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = REPO_ROOT / ".cache" / "validation" / f"companion-button-recording-chain-{stamp}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_artifact(result: dict[str, Any], artifact_dir: pathlib.Path | None) -> pathlib.Path:
    path_dir = resolve_artifact_dir(artifact_dir)
    path = path_dir / "companion-button-recording-chain.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="companion", help="BLE local name substring")
    parser.add_argument("--address", default="", help="Optional BLE address")
    parser.add_argument("--timeout", type=float, default=8.0, help="BLE scan/connect timeout")
    parser.add_argument("--notify-timeout", type=float, default=20.0, help="GATT notify timeout")
    parser.add_argument("--record-seconds", type=float, default=1.2, help="Dwell after first SW3 press before stop prompt")
    parser.add_argument("--recording-list-timeout", type=float, default=12.0, help="Wait for stored recording")
    parser.add_argument("--chunk-bytes", type=int, default=180, help="Requested recording bytes per BLE pull")
    parser.add_argument("--artifact-dir", type=pathlib.Path, default=None, help="Directory for JSON/WAV/PCM evidence")
    parser.add_argument("--programmer", default="", help="Optional STM32_Programmer_CLI.exe path")
    parser.add_argument("--serial-port", default="", help="Optional ST-LINK VCP serial port")
    parser.add_argument("--baud", type=int, default=115200, help="ST-LINK VCP baud rate")
    parser.add_argument("--button", default="SW3", help="NUCLEO user button to use for start/stop")
    parser.add_argument("--button-alias", default="B3", help="Board silkscreen alias for --button")
    parser.add_argument("--pin", default="PD1", help="MCU pin for --button")
    parser.add_argument("--button-timeout", type=float, default=90.0, help="Per-button prompt timeout")
    parser.add_argument("--swd-port", default="SWD", help="STM32CubeProgrammer port name")
    parser.add_argument("--swd-freq", type=int, default=4000, help="SWD frequency in kHz")
    parser.add_argument("--reset-settle-s", type=float, default=6.0, help="BLE settle time after hard reset")
    parser.add_argument("--min-duration-s", type=float, default=0.4, help="Minimum PCM duration for quality gate")
    parser.add_argument("--min-peak", type=int, default=120, help="Minimum absolute PCM peak")
    parser.add_argument("--min-rms", type=float, default=8.0, help="Minimum PCM RMS")
    parser.add_argument("--max-zero-ratio", type=float, default=0.98, help="Maximum exact-zero sample ratio")
    parser.add_argument("--max-clipping-ratio", type=float, default=0.02, help="Maximum clipped sample ratio")
    parser.add_argument("--min-active-windows", type=int, default=1, help="Minimum active 20 ms windows")
    parser.add_argument("--no-prompts", action="store_true", help="Log prompts instead of showing desktop dialogs")
    parser.add_argument("--no-serial-button-monitor", action="store_true", help="Use manual OK prompts instead of serial auto-close prompts")
    parser.add_argument(
        "--keep-recording-after-sync",
        action="store_true",
        help="Do not delete the flash recording after validation; leave it for Companion-Type native BLE sync handoff",
    )
    return parser


async def async_main(args: argparse.Namespace) -> int:
    args.artifact_dir = resolve_artifact_dir(args.artifact_dir)
    try:
        result = await run_chain(args)
    except Exception as exc:  # noqa: BLE001
        result = {
            "schema_version": 1,
            "status": "FAIL",
            "finished_at": utc_now(),
            "git_commit": git_commit(),
            "mode": "real_sw3_button_recording_to_qspi_flash_ble_pull_reset_delete_chain"
            if not args.keep_recording_after_sync
            else "real_sw3_button_recording_to_qspi_flash_ble_pull_keep_for_type_sync_chain",
            "error": str(exc),
            "error_type": type(exc).__name__,
            "error_repr": repr(exc),
        }
        path = write_artifact(result, args.artifact_dir)
        print(f"FAIL: Companion SW3 button recording chain failed; artifact={path}")
        print(str(exc))
        return 1

    path = write_artifact(result, args.artifact_dir)
    print(f"PASS: Companion SW3 button recording chain passed; artifact={path}")
    return 0


def main() -> int:
    args = build_arg_parser().parse_args()
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
