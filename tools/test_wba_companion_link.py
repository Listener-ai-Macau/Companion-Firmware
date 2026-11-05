#!/usr/bin/env python3
"""Host lifecycle/security tests and Cortex-M33 compile for companion_link."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from verify_wba_spi_nor_adapter import find_vsdevcmd


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app" / "companion_pendant"
RUNTIME = APP / "runtime"
RECORDING = APP / "recording"
OUT = ROOT / ".cache" / "wba-companion-link-host"

INCLUDES = [
    OUT / "host-sdk",
    RUNTIME,
    RECORDING,
    APP / "gatt",
    APP / "v1_features",
    APP / "playback",
    APP / "touch",
    APP / "epaper",
    APP / "imu",
    APP / "power",
    APP / "storage",
    ROOT / "third_party" / "denzic-platform" / "audio" / "embedded" / "c" / "include",
]
SOURCES = [
    RUNTIME / "companion_link.c",
    RECORDING / "wba_recording_transfer.c",
    RECORDING / "companion_recording_journal.c",
    *(RECORDING / (name + '.c') for name in (
        'wba_recording_radio','wba_segment_pull','wba_segment_directory',
        'wba_recording_pipeline','wba_segment_storage','companion_continuous_recording',
        'companion_segment_audio','companion_segment_catalog','companion_segment_reserve',
        'companion_opus16_rt')),
]
TEST = RUNTIME / "tests" / "test_companion_link.c"
HEADERS = [
    RUNTIME / "companion_link.h",
    RECORDING / "wba_recording_transfer.h",
    RECORDING / "companion_recording_wire.h",
    RECORDING / "companion_recording_journal.h",
    RECORDING / "wba_recording_service.h",
    APP / "gatt" / "companion_gatt_stm32wb.h",
    APP / "v1_features" / "companion_wire_v1.h",
]


def run(command: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True,
                            check=False)
    if result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return result


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def write_host_headers() -> None:
    include = INCLUDES[0]
    include.mkdir(parents=True, exist_ok=True)
    (include / "ble_types.h").write_text(
        "#ifndef TEST_BLE_TYPES_H\n#define TEST_BLE_TYPES_H\n"
        "#include <stdint.h>\ntypedef uint8_t tBleStatus;\n#endif\n",
        encoding="ascii",
    )
    (include / "stm32_wpan_common.h").write_text(
        "#ifndef TEST_STM32_WPAN_COMMON_H\n"
        "#define TEST_STM32_WPAN_COMMON_H\n#endif\n",
        encoding="ascii",
    )


def native_compile() -> tuple[Path, str]:
    vsdevcmd = find_vsdevcmd()
    if vsdevcmd is None:
        raise RuntimeError("MSVC environment unavailable")
    executable = OUT / "wba-companion-link-test.exe"
    command = [
        "cl.exe", "/nologo", "/TC", "/std:c11", "/O2", "/W4", "/WX",
        "/MD", "/DCOMPANION_OPUS16_WBA_LOWDELAY=1", "/DCOMPANION_OPUS16_ENCODER_BYTES=65536",
        f'/I{ROOT / "third_party/opus/include"}',
        *(f"/I{path}" for path in INCLUDES),
        *(str(path) for path in [*SOURCES, TEST]),
        f"/Fe:{executable}", "/link", str(ROOT / '.cache/opus-host-fixed/opus.lib'),
    ]
    script = OUT / "compile.cmd"
    script.write_text(
        f'@call "{vsdevcmd}" -arch=amd64 -host_arch=amd64 >nul\n'
        '@if errorlevel 1 exit /b %errorlevel%\n'
        + subprocess.list2cmdline(command) + "\n",
        encoding="utf-8",
    )
    result = run(["cmd.exe", "/d", "/c", str(script)])
    return executable, (result.stdout + result.stderr).strip()


def m33_compile() -> dict[str, str]:
    compiler = shutil.which("arm-none-eabi-gcc")
    if compiler is None:
        raise RuntimeError("arm-none-eabi-gcc unavailable")
    objects: dict[str, str] = {}
    for source in SOURCES:
        output = OUT / f"m33-{source.stem}.o"
        run([
            compiler, "-std=c11", "-mcpu=cortex-m33", "-mthumb", "-Os",
            "-Wall", "-Wextra", "-Werror", "-Wconversion", "-Wshadow",
            "-Wformat=2", "-pedantic",
            '-DCOMPANION_OPUS16_WBA_LOWDELAY=1', f'-I{ROOT / "third_party/opus/include"}',
            *(f"-I{path}" for path in INCLUDES),
            "-c", str(source), "-o", str(output),
        ])
        objects[output.name] = sha256(output)
    return objects


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    write_host_headers()
    executable, compile_log = native_compile()
    test = run([str(executable)], cwd=OUT)
    if (not test.stdout.startswith("PASS_WBA_COMPANION_LINK_HOST_ONLY")
        or "PASS_CONFIRMED_UNSYNCED_DISCARD_HOST_ONLY" not in test.stdout):
        raise RuntimeError(f"unexpected host output: {test.stdout}")
    objects = m33_compile()
    result = {
        "schema": "companion.wba_companion_link.prehardware.v1",
        "status": "PASS_HOST_ONLY",
        "hardware_status": "NOT_RUN",
        "coverage": [
            "pre-encryption CCCD and writes rejected",
            "pre-encryption recording pull has no journal or transfer side effect",
            "periodic values suppressed outside encrypted connection",
            "recording start profile 2 and profile-independent stop",
            "Type meeting control waits for real capture and durable finalize",
            "meeting retries are idempotent, argument collisions reject, and terminal retries stay correlated",
            "new request retries a failed meeting without inheriting the old recorder fault",
            "cancel before capture terminates without claiming a saved file and permits a new meeting",
            "live read defers to queued PCM, pending NOR pages and maintenance",
            "remote duration bound to recording request token",
            "finalized journal pull through portable transfer",
            "malformed pull length, schema, flags, and offset fail without journal mutation",
            "storage-full has distinct RecordingControl and MeetingStatus wire evidence",
            "capture blocks speaker command",
            "unconfirmed delete rejects without ACK or erase",
            "exact consume GATT dispatch has zero NOR I/O; ACK and ERASING persist in separate foreground polls",
            "reset before queued ACK retains UNSYNCED original; capture and OTA defer the ACK commit itself",
            "verified delete erases one sector per poll before success echo",
            "duplicate verified delete does not ACK or mutate the journal twice",
            "delete pauses for capture and retries an erase fault with backoff",
            "disconnect retains completion echo and reconnect publishes it",
            "power loss remount resumes durable ERASING from a safe zero cursor",
            "ACKED commit gap recovers automatically offline after reboot or a live marker failure",
            "recovery chooses oldest fully consumed identity and preserves UNSYNCED and WRITING bytes",
            "capture, pending preparation, OTA and active/backpressured pulls defer recovery",
            "transfer completion, durable marker, payload sectors and final catalog removal use separate polls",
            "torn recovery marker and repeated reboot retain durable identity before erasing",
            "marker retry backoff remains exact when a millisecond deadline wraps to zero",
            "exact host retry joins automatic recovery without double ACK or a premature success echo",
            "torn final removal and notification backpressure retain the exact completion response",
            "pending exact completion excludes recovery of another consumed identity until published",
            "partial ACK catalog write stays UNSYNCED after reboot and is never automatically erased",
            "exact Type retry during multi-record local clear cannot expose an early idle/completion gap",
            "disconnect clears subscriptions and transient pull",
            "explicit oldest UNSYNCED discard uses a read-only generation/nonce-bound proposal",
            "every proposal identity byte is checked; cancel, disconnect, timeout, concurrent catalog and busy operations reject",
            "RNG failure and torn intent do not erase; durable intent recovers without fabricating a host ACK",
            "bounded exact discard preserves newer originals and succeeds only after physical erase and durable removal",
        ],
        "test_stdout": test.stdout.strip(),
        "compile_log": compile_log,
        "m33_objects": objects,
        "discard_wire": {
            name: {"path": (OUT / name).relative_to(ROOT).as_posix(),
                   "bytes": (OUT / name).stat().st_size, "sha256": sha256(OUT / name)}
            for name in ("discard-preview.bin", "discard-completed.bin")
        },
        "source_sha256": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in [*SOURCES, TEST, *HEADERS, Path(__file__)]
        },
    }
    result_path = OUT / "result.json"
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("PASS_WBA_COMPANION_LINK_PREHARDWARE")
    print(result_path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"NO_GO_WBA_COMPANION_LINK: {exc}", file=sys.stderr)
        raise SystemExit(2)
