#!/usr/bin/env python3
"""Synchronize the fixed Companion browser frame resource to external UI NOR."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import time
import urllib.request
import zlib
from pathlib import Path

import serial
from serial.tools import list_ports


REPO = Path(__file__).resolve().parents[1]
FIXED_URL = (
    "http://127.0.0.1:4185/"
    ".cache/validation/comp-req-628-status-bar/index.html"
)
PAGE = REPO / ".cache/validation/comp-req-628-status-bar/index.html"
BASE_ROOT = (
    REPO / ".cache/validation/comp-req-774-browser-full-source-pack"
)
BASE_MANIFEST = BASE_ROOT / "source-pack-manifest.json"
BASE_CEMP = BASE_ROOT / "cemp/comp_req_774_browser_full.cemp"
SOURCE_GENERATOR = (
    REPO / "tools/faraday_upper_art/generate_comp_req_628_source_pack.mjs"
)
GENERATION_BUILDER = (
    REPO / "tools/faraday_upper_art/build_ui_asset_generation.py"
)
RECORDING_RESOURCE_BUILDER = (
    REPO / "tools/build_companion_recording_resources.py"
)
RECORDING_RESOURCE_PACK = (
    REPO
    / ".cache/validation/comp-req-775-recording-resources/"
    "companion_recording_resources.crrp"
)
DEFAULT_ARTIFACTS = (
    REPO / ".cache/validation/comp-req-775-incremental-sync/direct"
)
SECTOR_BYTES = 4096
CHUNK_BYTES = 256


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def page_sha256(data: bytes) -> str:
    return sha256_bytes(data.decode("utf-8").replace("\r\n", "\n").encode())


def align_sector(value: int) -> int:
    return (value + SECTOR_BYTES - 1) & ~(SECTOR_BYTES - 1)


def base_cemp_identity() -> dict[str, int]:
    header = BASE_CEMP.read_bytes()[:80]
    magic, version, header_size = struct.unpack_from("<4sHH", header)
    if magic != b"CEMP" or version != 1 or header_size != 80:
        raise RuntimeError("local base CEMP header is invalid")
    return {
        "base_pack_size": struct.unpack_from("<I", header, 8)[0],
        "base_payload_crc32": struct.unpack_from("<I", header, 56)[0],
        "base_index_crc32": struct.unpack_from("<I", header, 60)[0],
    }


def run(command: list[str]) -> dict:
    completed = subprocess.run(
        command,
        cwd=REPO,
        check=True,
        text=True,
        encoding="utf-8",
        capture_output=True,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f"command emitted no receipt: {command[0]}")
    return json.loads(lines[-1])


def check_fixed_url(url: str) -> tuple[int, bytes]:
    with urllib.request.urlopen(url, timeout=4) as response:
        body = response.read()
        return response.status, body


def auto_port() -> str:
    matches = [
        port.device
        for port in list_ports.comports()
        if "STLink Virtual COM Port" in (port.description or "")
    ]
    if len(matches) != 1:
        raise RuntimeError(
            "expected exactly one STLink Virtual COM Port; use --port"
        )
    return matches[0]


def parse_sync_line(line: str, phase: str) -> dict[str, str] | None:
    prefix = f"~UI_SYNC:{phase} "
    if not line.startswith(prefix):
        return None
    result: dict[str, str] = {}
    for field in line[len(prefix):].strip().split():
        if "=" in field:
            key, value = field.split("=", 1)
            result[key] = value
    return result


class Device:
    def __init__(self, port: str):
        self.serial = serial.Serial(
            port=port,
            baudrate=115200,
            timeout=0.2,
            write_timeout=3,
        )
        self.serial.reset_input_buffer()

    def close(self) -> None:
        self.serial.close()

    def write_paced_ascii(self, command: bytes) -> None:
        for byte in command:
            self.serial.write(bytes((byte,)))
            self.serial.flush()
            time.sleep(0.005)

    def wait_phase(self, phase: str, timeout: float) -> dict[str, str]:
        deadline = time.monotonic() + timeout
        seen: list[str] = []
        while time.monotonic() < deadline:
            raw = self.serial.readline()
            if not raw:
                continue
            line = raw.decode("ascii", errors="replace").strip()
            if line:
                seen.append(line)
            parsed = parse_sync_line(line, phase)
            if parsed is not None:
                return parsed
        tail = "\n".join(seen[-8:])
        raise TimeoutError(f"no {phase} receipt from device; tail:\n{tail}")

    def wait_read_only_query(
        self,
        command: bytes,
        phase: str,
        timeout: float,
    ) -> dict[str, str]:
        self.write_paced_ascii(command)
        return self.wait_phase(phase, timeout)

    def query(self, timeout: float = 30.0) -> dict[str, str]:
        result = self.wait_read_only_query(b"UIQ\n", "QUERY", timeout)
        if result.get("result") != "ready":
            raise RuntimeError(f"device query failed: {result}")
        return result

    def query_resource(self, timeout: float = 8.0) -> dict[str, str]:
        result = self.wait_read_only_query(
            b"UIRQ\n", "RESOURCE_QUERY", timeout
        )
        if result.get("result") != "ready":
            raise RuntimeError(f"device resource query failed: {result}")
        return result

    def begin_resource(
        self, pack_bytes: int, pack_crc32: int
    ) -> dict[str, str]:
        command = f"UIRB {pack_bytes} 0x{pack_crc32:08X}\n"
        self.serial.write(command.encode("ascii"))
        self.serial.flush()
        return self.wait_phase("RESOURCE_BEGIN", 12.0)

    def send_resource(self, pack: bytes) -> dict[str, str]:
        offset = 0
        while offset < len(pack):
            chunk = pack[offset:offset + CHUNK_BYTES]
            self.serial.write(chunk)
            self.serial.flush()
            offset += len(chunk)
            chunk_receipt = self.wait_phase("RESOURCE_CHUNK", 6.0)
            if int(chunk_receipt.get("received", "-1")) != offset:
                raise RuntimeError(
                    f"resource chunk receipt drift: expected {offset}, "
                    f"got {chunk_receipt}"
                )
        return self.wait_phase("RESOURCE_FINISH", 15.0)

    def begin(self, generation: dict) -> dict[str, str]:
        command = (
            "UIB "
            f"{generation['expected_active_generation']} "
            f"{generation['base_pack_size']} "
            f"{generation['blob_bytes']} "
            f"0x{generation['blob_crc32']:08X} "
            "0 "
            f"{generation['manifest_bytes']} "
            f"0x{generation['manifest_crc32']:08X} "
            f"{generation['resource_id']}\n"
        )
        self.serial.write(command.encode("ascii"))
        self.serial.flush()
        return self.wait_phase("BEGIN", 8.0)

    def send_blob(self, blob: bytes) -> dict[str, str]:
        offset = 0
        final: dict[str, str] | None = None
        while offset < len(blob):
            chunk = blob[offset:offset + CHUNK_BYTES]
            self.serial.write(chunk)
            self.serial.flush()
            offset += len(chunk)
            chunk_receipt = self.wait_phase("CHUNK", 6.0)
            if int(chunk_receipt.get("received", "-1")) != offset:
                raise RuntimeError(
                    f"chunk receipt drift: expected {offset}, "
                    f"got {chunk_receipt}"
                )
        final = self.wait_phase("FINISH", 12.0)
        return final


def source_pack(artifacts: Path) -> tuple[Path, dict]:
    output = artifacts / "current-source-pack"
    manifest_path = output / "source-pack-manifest.json"
    if manifest_path.exists():
        cached = json.loads(manifest_path.read_text(encoding="utf-8"))
        cached_source = cached.get("source", {})
        cached_invariants = cached.get("invariants", {})
        cached_frames = cached.get("files", {}).get("frames", {})
        expected_page_sha = page_sha256(PAGE.read_bytes())
        frames_path = output / "frames.bin"
        cache_files_match = (
            frames_path.exists()
            and sha256_bytes(frames_path.read_bytes())
            == cached_frames.get("sha256")
            and all(
                (output / state["pbm_file"]).exists()
                and sha256_bytes((output / state["pbm_file"]).read_bytes())
                == state["pbm_sha256"]
                for state in cached.get("states", [])
            )
        )
        if (
            cached.get("status") == "PASS"
            and cached_source.get("page_sha256") == expected_page_sha
            and cached_invariants.get("all_states_are_5000_bytes") is True
            and cached_invariants.get("all_inputs_binary") is True
            and cache_files_match
        ):
            return manifest_path, {
                "status": "PASS_CACHED_SOURCE_PACK",
                "page_sha256": expected_page_sha,
                "manifest_sha256": sha256_bytes(
                    manifest_path.read_bytes()
                ),
                "states": cached_invariants.get("state_count"),
                "unique_frames": cached_invariants.get("unique_frame_count"),
            }
    result = run([
        "node",
        str(SOURCE_GENERATOR),
        "--output",
        str(output.relative_to(REPO)).replace("\\", "/"),
        "--page",
        str(PAGE.relative_to(REPO)).replace("\\", "/"),
        "--life-families",
        "calm,curious,warm,delighted,thoughtful,alert",
        "--life-episodes",
        "32",
    ])
    if result.get("status") != "PASS":
        raise RuntimeError(f"source pack failed: {result}")
    return manifest_path, result


def active_sidecar(
    artifacts: Path,
    query: dict[str, str],
) -> Path | None:
    generation = int(query["generation"])
    if generation == 0:
        return None
    resource_id = query["resource_id"].upper()
    cached = artifacts / "accepted" / f"{resource_id}.json"
    if cached.exists():
        return cached
    fallback = artifacts / "active-board-stub.json"
    fallback.write_text(
        json.dumps(
            {
                "schema": "companion.ui_asset_generation.v1",
                "generation": generation,
                "resource_id": resource_id,
                "entries_by_id": {},
            },
            indent=2,
        ) + "\n",
        encoding="ascii",
        newline="\n",
    )
    return fallback


def build_generation(
    artifacts: Path,
    source_manifest: Path,
    query: dict[str, str],
) -> tuple[Path, Path, dict]:
    generation = int(query["generation"])
    base_identity = base_cemp_identity()
    if (
        int(query["base_pack_size"]) != base_identity["base_pack_size"]
        or int(query["base_payload_crc32"], 16)
        != base_identity["base_payload_crc32"]
        or int(query["base_index_crc32"], 16)
        != base_identity["base_index_crc32"]
    ):
        raise RuntimeError("device base CEMP identity differs from local base")
    arena_next = int(query["arena_next"])
    planned_offset = (
        align_sector(BASE_CEMP.stat().st_size)
        if generation == 0
        else arena_next
    )
    blob = artifacts / "pending-generation.blob"
    sidecar = artifacts / "pending-generation.json"
    command = [
        sys.executable,
        str(GENERATION_BUILDER),
        "--source-pack-manifest",
        str(source_manifest),
        "--base-source-pack-manifest",
        str(BASE_MANIFEST),
        "--planned-blob-offset",
        hex(planned_offset),
        "--output-blob",
        str(blob),
        "--output-generation",
        str(sidecar),
    ]
    active = active_sidecar(artifacts, query)
    if active is not None:
        command.extend(["--active-generation", str(active)])
    result = run(command)
    generation_data = json.loads(sidecar.read_text(encoding="ascii"))
    generation_data["expected_active_generation"] = generation
    generation_data["base_pack_size"] = base_identity["base_pack_size"]
    return blob, sidecar, generation_data | {"builder_receipt": result}


def require_readback_identity(
    query: dict[str, str],
    generation: dict,
) -> None:
    expected = {
        "blob_size": int(generation["blob_bytes"]),
        "blob_crc32": int(generation["blob_crc32"]),
        "manifest_size": int(generation["manifest_bytes"]),
        "manifest_crc32": int(generation["manifest_crc32"]),
    }
    actual = {
        "blob_size": int(query.get("blob_size", "-1")),
        "blob_crc32": int(query.get("blob_crc32", "-1"), 16),
        "manifest_size": int(query.get("manifest_size", "-1")),
        "manifest_crc32": int(
            query.get("manifest_crc32", "-1"), 16
        ),
    }
    if actual != expected:
        raise RuntimeError(
            "post-reset generation readback identity mismatch: "
            f"expected={expected} actual={actual}"
        )


def save_receipt(path: Path, receipt: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=True) + "\n",
        encoding="ascii",
        newline="\n",
    )

def recording_resource_pack() -> tuple[bytes, dict]:
    subprocess.run(
        [sys.executable, str(RECORDING_RESOURCE_BUILDER)],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    pack = RECORDING_RESOURCE_PACK.read_bytes()
    manifest = json.loads(
        RECORDING_RESOURCE_PACK.with_suffix(".json").read_text(
            encoding="utf-8"
        )
    )
    if (
        manifest.get("status") != "MACHINE_READY_OFFLINE"
        or manifest.get("pack", {}).get("sha256") != sha256_bytes(pack)
        or int(manifest.get("pack", {}).get("bytes", 0)) != len(pack)
    ):
        raise RuntimeError("recording resource pack identity mismatch")
    return pack, manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port")
    parser.add_argument("--url", default=FIXED_URL)
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument(
        "--offline-query",
        type=Path,
        help="Build and verify a plan from a saved QUERY JSON without hardware",
    )
    args = parser.parse_args()
    started = time.monotonic()
    artifacts = args.artifacts.resolve()
    artifacts.mkdir(parents=True, exist_ok=True)

    http_status, page_body = check_fixed_url(args.url)
    if http_status != 200:
        raise RuntimeError(f"fixed URL returned HTTP {http_status}")
    local_page = PAGE.read_bytes()
    if page_sha256(page_body) != page_sha256(local_page):
        raise RuntimeError("fixed URL body differs from canonical page file")
    source_manifest, source_result = source_pack(artifacts)
    recording_pack, recording_manifest = recording_resource_pack()
    recording_crc32 = zlib.crc32(recording_pack) & 0xFFFFFFFF
    recording_write_bytes = 0
    recording_begin: dict[str, str] | None = None
    recording_finish: dict[str, str] | None = None
    recording_after: dict[str, str] | None = None

    device: Device | None = None
    if args.offline_query:
        query = json.loads(args.offline_query.read_text(encoding="ascii"))
        port = None
        recording_before = {"result": "offline_unknown"}
    else:
        port = args.port or auto_port()
        device = Device(port)
        query = device.query()
        recording_before = device.query_resource()
        recording_current = (
            recording_before.get("present") == "1"
            and int(recording_before.get("pack_bytes", "0"))
            == len(recording_pack)
            and int(recording_before.get("crc32", "0"), 16)
            == recording_crc32
        )
        if not recording_current:
            recording_begin = device.begin_resource(
                len(recording_pack), recording_crc32
            )
            if recording_begin.get("result") != "ok":
                raise RuntimeError(
                    f"device rejected resource BEGIN: {recording_begin}"
                )
            recording_finish = device.send_resource(recording_pack)
            if recording_finish.get("result") != "ok":
                raise RuntimeError(
                    f"device failed resource FINISH: {recording_finish}"
                )
            recording_write_bytes = int(
                recording_finish["bytes_written"]
            )
            device.close()
            device = None
            time.sleep(1.0)
            device = Device(port)
            recording_after = device.query_resource(timeout=8.0)
            if (
                recording_after.get("present") != "1"
                or int(recording_after.get("pack_bytes", "0"))
                != len(recording_pack)
                or int(recording_after.get("crc32", "0"), 16)
                != recording_crc32
            ):
                raise RuntimeError(
                    "post-reset recording resource identity mismatch: "
                    f"{recording_after}"
                )
            query = device.query(timeout=8.0)

    blob_path, sidecar_path, generation = build_generation(
        artifacts, source_manifest, query
    )
    builder = generation.pop("builder_receipt")
    resource_id = generation["resource_id"]
    receipt = {
        "schema": "companion.ui_asset_sync_receipt.v1",
        "status": "PENDING",
        "fixed_url": args.url,
        "http_status": http_status,
        "page_sha256": source_result["page_sha256"],
        "base_cemp_sha256": sha256_bytes(BASE_CEMP.read_bytes()),
        "base_cemp_bytes": BASE_CEMP.stat().st_size,
        "port": port,
        "before": query,
        "resource_id": resource_id,
        "source_pack": source_result,
        "builder": builder,
        "blob_sha256": sha256_bytes(blob_path.read_bytes()),
        "recording_resources": {
            "pack_sha256": sha256_bytes(recording_pack),
            "pack_crc32": f"{recording_crc32:08X}",
            "pack_bytes": len(recording_pack),
            "placement": recording_manifest["placement"][
                "recording_resources"
            ],
            "before": recording_before,
            "begin": recording_begin,
            "finish": recording_finish,
            "after": recording_after,
        },
        "external_flash_write_bytes": recording_write_bytes,
        "internal_flash_write_bytes": 0,
        "hardware_contact": 0 if args.offline_query else 1,
    }

    if builder["status"] == "PASS_UI_ASSET_ALREADY_CURRENT":
        receipt.update({
            "status": (
                "PASS_ALREADY_CURRENT"
                if recording_write_bytes == 0
                else "PASS_RESOURCE_UPDATED_UI_ALREADY_CURRENT"
            ),
            "active_generation": int(query["generation"]),
            "external_flash_write_bytes": recording_write_bytes,
            "internal_flash_write_bytes": 0,
            "elapsed_ms": round((time.monotonic() - started) * 1000),
        })
        save_receipt(artifacts / "sync-receipt.json", receipt)
        if device is not None:
            device.close()
        print(json.dumps(receipt, ensure_ascii=True))
        return 0

    if args.offline_query:
        receipt.update({
            "status": "PASS_OFFLINE_PLAN",
            "planned_recording_resource_bytes": len(recording_pack),
            "planned_recording_resource_crc32": (
                f"{recording_crc32:08X}"
            ),
            "planned_blob_offset": generation["planned_blob_offset"],
            "planned_blob_bytes": generation["blob_bytes"],
            "planned_manifest_bytes": generation["manifest_bytes"],
            "planned_new_payload_count": generation["new_payload_count"],
            "elapsed_ms": round((time.monotonic() - started) * 1000),
        })
        save_receipt(artifacts / "sync-receipt.json", receipt)
        print(json.dumps(receipt, ensure_ascii=True))
        return 0

    assert device is not None
    try:
        begin = device.begin(generation)
        if begin.get("result") != "ok":
            raise RuntimeError(f"device rejected BEGIN: {begin}")
        if int(begin["blob_offset"]) != generation["planned_blob_offset"]:
            raise RuntimeError(
                "device blob offset differs from manifest payload offsets"
            )
        finish = device.send_blob(blob_path.read_bytes())
        if finish.get("result") != "ok":
            raise RuntimeError(f"device failed FINISH: {finish}")
        receipt["external_flash_write_bytes"] += (
            int(finish["blob_bytes_written"]) +
            int(finish["root_bytes_written"])
        )
        receipt["begin"] = begin
        receipt["finish"] = finish
        device.close()
        device = None

        time.sleep(1.0)
        verify_device = Device(port)
        after = verify_device.query(timeout=8.0)
        verify_device.close()
        if after["resource_id"].upper() != resource_id:
            raise RuntimeError(f"post-reset identity mismatch: {after}")
        require_readback_identity(after, generation)
        receipt.update({
            "status": "PASS",
            "active_generation": int(after["generation"]),
            "after": after,
            "readback_identity_match": True,
            "readback_crc_match": True,
            "internal_flash_write_bytes": 0,
            "elapsed_ms": round((time.monotonic() - started) * 1000),
        })
        accepted = artifacts / "accepted" / f"{resource_id}.json"
        accepted.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(sidecar_path, accepted)
        save_receipt(artifacts / "sync-receipt.json", receipt)
        print(json.dumps(receipt, ensure_ascii=True))
        return 0
    finally:
        if device is not None:
            device.close()


if __name__ == "__main__":
    raise SystemExit(main())
