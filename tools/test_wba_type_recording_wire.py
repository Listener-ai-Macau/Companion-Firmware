#!/usr/bin/env python3
"""Parse WBA recording exports with Type's actual Rust wire parser.

HOST_ONLY: the producer artifacts come from the real-Opus/NOR host fixture.
This catches drift between the firmware notifier and the Windows consumer; it
does not exercise BLE radio timing or physical flash/audio hardware.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import shutil
import struct
import subprocess
import sys
import zlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
TYPE_BRIDGE = ROOT.parent / "Companion-Type" / "apps" / "windows" / "src-tauri" / "src" / "backend" / "ble_bridge.rs"
TYPE_LEGACY = TYPE_BRIDGE.parent / "recording_wire" / "legacy.rs"
FIXTURE = ROOT / ".cache" / "wba-recording-service-host"
OUT = ROOT / ".cache" / "host-tests" / "wba-type-recording-wire"
RESULT = OUT / "result.json"

ACTIVE_LIST = FIXTURE / "real-opus.cop1.active-list.bin"
FINAL_LIST = FIXTURE / "real-opus.cop1.final-list.bin"
LIVE_WIRE = FIXTURE / "real-opus.cop1.live-wire.bin"
FINAL_WIRE = FIXTURE / "real-opus.cop1.wire.bin"
LIVE_EXPECTED = FIXTURE / "real-opus.cop1.prefix.cop1"
FINAL_EXPECTED = FIXTURE / "real-opus.cop1"

CONSTANTS = (
    "RECORDING_CHUNK_FINAL_FLAG",
    "RECORDING_CHUNK_COMPACT_FLAG",
    "RECORDING_CHUNK_SLIM_FLAG",
    "RECORDING_CHUNK_ERROR_FLAG",
    "RECORDING_LIST_ENTRY_BYTES",
    "RECORDING_CHUNK_HEADER_COMPACT_BYTES",
    "RECORDING_CHUNK_HEADER_SLIM_BYTES",
    "RECORDING_CHUNK_HEADER_LEGACY_BASE_BYTES",
    "RECORDING_CHUNK_HEADER_FULL_BYTES",
)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_label(path: pathlib.Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return pathlib.PurePosixPath("..", *path.relative_to(ROOT.parent).parts).as_posix()


def rust_item(source: str, marker: str, *, include_attribute: bool = False) -> str:
    start = source.index(marker)
    if include_attribute:
        attribute = source.rfind("#[derive", 0, start)
        if attribute >= 0 and source[attribute:start].strip().endswith("]"):
            start = attribute
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise RuntimeError(f"unterminated Rust item: {marker}")


def rust_constant(source: str, name: str) -> str:
    match = re.search(rf"(?m)^const {re.escape(name)}:[^;]+;$", source)
    if match is None:
        raise RuntimeError(f"missing Type constant {name}")
    return match.group(0)


def build_harness() -> pathlib.Path:
    source = TYPE_BRIDGE.read_text(encoding="utf-8")
    extracted = [rust_constant(source, name) for name in CONSTANTS]
    extracted.extend([
        rust_item(source, "struct RecordingEntry", include_attribute=True),
        rust_item(source, "struct RecordingChunk", include_attribute=True),
        rust_item(source, "fn parse_recording_list").replace("super::recording_wire::decode_v1", "recording_wire::decode_v1"),
        rust_item(source, "fn parse_recording_chunk"),
        rust_item(source, "fn le_u16"),
        rust_item(source, "fn le_u32"),
        rust_item(source, "fn hex_lower"),
    ])
    harness = """
#![allow(dead_code)]
use std::env;
use std::fs::{self, File};
use std::io::Write;
use std::path::{Path, PathBuf};

""" + 'mod recording_wire {\n' + TYPE_LEGACY.read_text(encoding="utf-8") + '\n}\n' + "\n\n".join(extracted) + r'''

fn require(condition: bool, message: &str) -> Result<(), String> {
    if condition { Ok(()) } else { Err(message.to_string()) }
}

fn one_entry(path: &Path, state: u8) -> Result<RecordingEntry, String> {
    let data = fs::read(path).map_err(|e| format!("read {}: {e}", path.display()))?;
    let mut entries = parse_recording_list(&data)?;
    require(entries.len() == 1, &format!("{} entry count {}", path.display(), entries.len()))?;
    let entry = entries.remove(0);
    require(entry.sync_state == state, &format!("{} sync_state {} != {state}", path.display(), entry.sync_state))?;
    require(entry.recording_id != 0 && entry.total_length != 0, "list identity/length is zero")?;
    require(entry.codec == 3 && entry.source_mode == 1, "list is not codec=3 SAI microphone")?;
    Ok(entry)
}

fn parse_container(path: &Path, expected: &RecordingEntry, live: bool,
                   recovered_path: &Path, meta_path: &Path,
                   sha_path: &Path) -> Result<usize, String> {
    let bytes = fs::read(path).map_err(|e| format!("read {}: {e}", path.display()))?;
    let mut cursor = 0usize;
    let mut recovered = Vec::<u8>::new();
    let mut meta = File::create(meta_path).map_err(|e| format!("create meta: {e}"))?;
    let mut packets = 0usize;
    let mut saw_final = false;
    let mut final_sha = [0u8; 32];
    while cursor < bytes.len() {
        require(cursor + 2 <= bytes.len(), "wire container has truncated length")?;
        let length = u16::from_le_bytes([bytes[cursor], bytes[cursor + 1]]) as usize;
        cursor += 2;
        require(length != 0 && cursor + length <= bytes.len(), "wire container has bad record length")?;
        let chunk = parse_recording_chunk(&bytes[cursor..cursor + length])?;
        cursor += length;
        require(chunk.recording_id == expected.recording_id, "chunk recording_id drift")?;
        require(chunk.byte_offset as usize == recovered.len(), "chunk offset is not contiguous")?;
        if live {
            /* Sparse directory reads and START windows are separate snapshots.
             * The packet carries the CRC domain that Type actually consumes. */
            require(chunk.total_length >= chunk.byte_offset + u32::from(chunk.payload_length),
                    "live packet exceeds its own durable snapshot")?;
        } else {
            require(chunk.total_length == expected.total_length, "final chunk/list length mismatch")?;
        }
        require(chunk.payload_length as usize == chunk.payload.len(), "parsed payload length mismatch")?;
        require(!saw_final, "packet appeared after FINAL")?;
        if chunk.flags & RECORDING_CHUNK_FINAL_FLAG != 0 {
            require(!live, "live snapshot incorrectly carries FINAL")?;
            saw_final = true;
            final_sha = chunk.final_sha256;
        }
        writeln!(meta, "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}",
                 chunk.recording_id, chunk.packet_sequence, chunk.byte_offset,
                 chunk.total_length, chunk.flags, chunk.payload_length,
                 chunk.packet_crc32, hex_lower(&chunk.final_sha256))
            .map_err(|e| format!("write meta: {e}"))?;
        recovered.extend_from_slice(&chunk.payload);
        packets += 1;
    }
    if !live {
        require(recovered.len() == expected.total_length as usize, "final recovered/list length mismatch")?;
    }
    require(live || saw_final, "finalized transfer has no FINAL packet")?;
    fs::write(recovered_path, &recovered).map_err(|e| format!("write recovered: {e}"))?;
    if !live {
        fs::write(sha_path, final_sha).map_err(|e| format!("write final SHA: {e}"))?;
    }
    Ok(packets)
}

fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().collect();
    require(args.len() == 7, "usage: harness ACTIVE FINAL LIVE_WIRE FINAL_WIRE OLD56 OUT")?;
    let out = PathBuf::from(&args[6]);
    let active = one_entry(Path::new(&args[1]), 1)?;
    let final_entry = one_entry(Path::new(&args[2]), 0)?;
    require(active.recording_id == final_entry.recording_id, "active/final recording id drift")?;
    require(active.total_length <= final_entry.total_length, "durable prefix regressed")?;
    require(final_entry.sha256_prefix.iter().any(|b| *b != 0), "final list SHA prefix is empty")?;
    require(active.sha256_prefix.iter().all(|b| *b == 0), "live list must not claim final SHA")?;
    let live_packets = parse_container(Path::new(&args[3]), &active, true,
        &out.join("live.recovered.cop1"), &out.join("live.meta.tsv"), &out.join("unused.sha"))?;
    let final_packets = parse_container(Path::new(&args[4]), &final_entry, false,
        &out.join("final.recovered.cop1"), &out.join("final.meta.tsv"), &out.join("final.device-sha.bin"))?;
    let old56_packets = parse_container(Path::new(&args[5]), &final_entry, false,
        &out.join("old56.recovered.cop1"), &out.join("old56.meta.tsv"), &out.join("old56.device-sha.bin"))?;
    require(fs::read(out.join("old56.recovered.cop1")).map_err(|e| e.to_string())? !=
            fs::read(out.join("final.recovered.cop1")).map_err(|e| e.to_string())?,
            "legacy flags=0 parser unexpectedly accepted old 56-byte intermediate payload alignment")?;
    println!("PASS_TYPE_RUST_PARSER recording_id={} live_bytes={} final_bytes={} live_packets={} final_packets={} final_crc32={} final_sha_prefix={}",
        final_entry.recording_id, active.total_length, final_entry.total_length,
        live_packets, final_packets, final_entry.content_crc32,
        hex_lower(&final_entry.sha256_prefix));
    println!("PASS_OLD56_NEGATIVE packets={} payload_compare=rejected", old56_packets);
    Ok(())
}

fn main() {
    if let Err(error) = run() { eprintln!("FAIL: {error}"); std::process::exit(1); }
}
'''
    path = OUT / "type_recording_wire_harness.rs"
    path.write_text(harness, encoding="utf-8")
    return path


def parse_meta(path: pathlib.Path) -> list[dict[str, int | str]]:
    packets: list[dict[str, int | str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split("\t")
        if len(fields) != 8:
            raise RuntimeError(f"bad metadata line in {path}: {line!r}")
        packets.append({
            "recording_id": int(fields[0]), "sequence": int(fields[1]),
            "offset": int(fields[2]), "total": int(fields[3]),
            "flags": int(fields[4]), "length": int(fields[5]),
            "crc32": int(fields[6]), "sha256": fields[7],
        })
    return packets


def make_old56_negative(source: pathlib.Path, destination: pathlib.Path) -> None:
    data = source.read_bytes()
    cursor = 0
    output = bytearray()
    changed = False
    while cursor < len(data):
        if cursor + 2 > len(data):
            raise RuntimeError("final wire has truncated record length")
        length = int.from_bytes(data[cursor:cursor + 2], "little")
        cursor += 2
        if length == 0 or cursor + length > len(data):
            raise RuntimeError("final wire has invalid record length")
        record = data[cursor:cursor + length]
        cursor += length
        if not changed and len(record) >= 24 and record[1] & 0x81 == 0:
            record = record[:24] + bytes(32) + record[24:]
            changed = True
        output.extend(len(record).to_bytes(2, "little"))
        output.extend(record)
    if not changed:
        raise RuntimeError("final wire has no intermediate packet for old56 regression")
    destination.write_bytes(output)


def verify_crc(recovered: bytes, packets: list[dict[str, int | str]]) -> None:
    for packet in packets:
        offset = int(packet["offset"])
        length = int(packet["length"])
        fields = struct.pack("<IIII", int(packet["recording_id"]),
                             int(packet["sequence"]), offset,
                             int(packet["total"]))
        crc = zlib.crc32(fields)
        crc = zlib.crc32(recovered[offset:offset + length], crc) & 0xFFFFFFFF
        if crc != int(packet["crc32"]):
            raise RuntimeError(
                f"packet CRC mismatch at {offset}: {crc:#010x} != {int(packet['crc32']):#010x}")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    RESULT.unlink(missing_ok=True)
    required = [TYPE_BRIDGE, ACTIVE_LIST, FINAL_LIST, LIVE_WIRE, FINAL_WIRE,
                LIVE_EXPECTED, FINAL_EXPECTED]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        print("FAIL: missing recording wire fixture(s): " + ", ".join(missing), file=sys.stderr)
        return 2
    rustc = shutil.which("rustc")
    if rustc is None:
        print("FAIL: rustc is required to compile Type's parser", file=sys.stderr)
        return 2
    try:
        harness = build_harness()
        old56 = OUT / "old56-intermediate-negative.wire.bin"
        make_old56_negative(FINAL_WIRE, old56)
    except (ValueError, RuntimeError) as error:
        print(f"FAIL: cannot extract Type parser: {error}", file=sys.stderr)
        return 2
    executable = OUT / ("type_recording_wire_harness.exe" if sys.platform == "win32" else "type_recording_wire_harness")
    built = subprocess.run([rustc, "--edition=2021", "-Dwarnings", str(harness), "-o", str(executable)],
                           cwd=ROOT, text=True, capture_output=True)
    if built.returncode != 0:
        print(built.stdout, end="")
        print(built.stderr, end="", file=sys.stderr)
        return built.returncode
    tested = subprocess.run([str(executable), str(ACTIVE_LIST), str(FINAL_LIST),
                             str(LIVE_WIRE), str(FINAL_WIRE), str(old56), str(OUT)],
                            cwd=ROOT, text=True, capture_output=True)
    print(tested.stdout, end="")
    print(tested.stderr, end="", file=sys.stderr)
    if tested.returncode != 0:
        return tested.returncode
    try:
        live = (OUT / "live.recovered.cop1").read_bytes()
        final = (OUT / "final.recovered.cop1").read_bytes()
        device_sha = (OUT / "final.device-sha.bin").read_bytes()
        if live != LIVE_EXPECTED.read_bytes():
            raise RuntimeError("Type parser live payload differs from exported durable COP1 prefix")
        if final != FINAL_EXPECTED.read_bytes():
            raise RuntimeError("Type parser final payload differs from real Opus COP1")
        if len(device_sha) != 32 or hashlib.sha256(final).digest() != device_sha:
            raise RuntimeError("final Type payload SHA does not match firmware FINAL SHA")
        live_meta = parse_meta(OUT / "live.meta.tsv")
        final_meta = parse_meta(OUT / "final.meta.tsv")
        verify_crc(live, live_meta)
        verify_crc(final, final_meta)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    stdout = tested.stdout + (
        f"PASS_HOST_ONLY: Type parser recovered exact live/final COP1; "
        f"packet_crc32=verified final_sha256={hashlib.sha256(final).hexdigest()}\n"
    )
    print(stdout[len(tested.stdout):], end="")
    source_paths = [
        pathlib.Path(__file__).resolve(), TYPE_BRIDGE, TYPE_LEGACY,
        ROOT / "app" / "companion_pendant" / "recording" / "companion_recording_wire.h",
        ROOT / "app" / "companion_pendant" / "recording" / "wba_recording_transfer.h",
        ROOT / "app" / "companion_pendant" / "recording" / "wba_recording_transfer.c",
        ROOT / "app" / "companion_pendant" / "recording" / "wba_recording_service.h",
        ROOT / "app" / "companion_pendant" / "recording" / "wba_recording_service.c",
        ROOT / "app" / "companion_pendant" / "recording" / "tests" / "test_wba_recording_service_real_opus.c",
        ROOT / "tools" / "test_wba_recording_service.py",
    ]
    hashes = {relative_label(path): sha256(path) for path in source_paths}
    artifacts = {path.name: sha256(path) for path in
                 [ACTIVE_LIST, FINAL_LIST, LIVE_WIRE, FINAL_WIRE, LIVE_EXPECTED, FINAL_EXPECTED]}
    result = {
        "status": "PASS_HOST_ONLY",
        "hardware_status": "NOT_RUN",
        "scope": "Type Rust parser + host NOR/real Opus exported notifications; no BLE radio or board hardware",
        "source_sha256": hashes,
        "artifact_sha256": artifacts,
        "stdout": stdout,
    }
    temporary = RESULT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    temporary.replace(RESULT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
