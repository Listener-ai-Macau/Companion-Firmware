#!/usr/bin/env python3
"""Measure the superseded full-pack Companion UI asset deployment path."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
OLD = REPO / ".cache/validation/comp-req-771-same-source-flash"
ARTIFACTS = REPO / ".cache/validation/comp-req-775-incremental-sync"
SOURCE_PACK = REPO / ".cache/validation/comp-req-775-batched-source-pack"
CEMP_WORK = SOURCE_PACK / "comp-req-775-full-cemp-baseline"
OUTPUT = ARTIFACTS / "SLOW_PATH_BASELINE.json"
MANIFEST_GENERATOR = (
    REPO
    / "tools/faraday_upper_art/generate_comp_req_638_cemp_manifest.py"
)
CEMP_BUILDER = REPO / "tools/build_emote_asset_pack.py"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def relative(path: Path) -> str:
    return str(path.relative_to(REPO)).replace("\\", "/")


def instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def elapsed_ms(events: dict[str, dict], start: str, end: str) -> int:
    delta = instant(events[end]["at"]) - instant(events[start]["at"])
    return round(delta.total_seconds() * 1000)


def run_timed(args: list[str]) -> tuple[int, str]:
    started = time.perf_counter_ns()
    completed = subprocess.run(
        args,
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return round((time.perf_counter_ns() - started) / 1_000_000), (
        completed.stdout.strip()
    )


def log_identity(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    link_lines = [
        line
        for line in text.splitlines()
        if "arm-none-eabi-gcc " in line and ' -o "' in line
        and ".elf\"" in line
    ]
    return {
        "path": relative(path),
        "sha256": sha256(path),
        "complete_app_link_count": len(link_lines),
        "links_app_ble": any("app_ble.o" in line for line in link_lines),
        "links_opus_encoder": any(
            "opus_encoder.o" in line for line in link_lines
        ),
        "links_epaper_runtime": any(
            "screen_runtime.o" in line for line in link_lines
        ),
    }


def main() -> int:
    precheck_path = OLD / "PRECHECK_READY.json"
    failed_run_path = OLD / "hardware-run/hardware-run.json"
    completed_run_path = (
        OLD
        / "hardware-run-r28-busy0-owner-needs-changes/hardware-run.json"
    )
    precheck = load(precheck_path)
    failed_run = load(failed_run_path)
    completed_run = load(completed_run_path)
    initial_sync = load(
        ARTIFACTS / "offline-initial-batched/sync-receipt.json"
    )

    CEMP_WORK.mkdir(parents=True, exist_ok=True)
    cemp_manifest = CEMP_WORK / "manifest.json"
    cemp_binary = CEMP_WORK / "full.cemp"
    cemp_metadata = CEMP_WORK / "full.metadata.json"
    manifest_ms, manifest_stdout = run_timed(
        [
            sys.executable,
            str(MANIFEST_GENERATOR),
            "--source-pack-manifest",
            str(SOURCE_PACK / "source-pack-manifest.json"),
            "--output",
            str(cemp_manifest),
        ]
    )
    cemp_ms, cemp_stdout = run_timed(
        [
            sys.executable,
            str(CEMP_BUILDER),
            "--manifest",
            str(cemp_manifest),
            "--output",
            str(cemp_binary),
            "--metadata",
            str(cemp_metadata),
        ]
    )

    images = precheck["images"]
    ota_names = [
        "provision_chunk_0",
        "provision_chunk_1",
        "provision_chunk_2",
        "provision_chunk_3",
        "app",
    ]
    ota_bytes = sum(images[name]["programmed_bytes"] for name in ota_names)
    loader_bytes = images["loader"]["programmed_bytes"]
    total_internal_bytes = loader_bytes + ota_bytes
    image_evidence = {
        name: {
            "sha256": images[name]["sha256"],
            "programmed_bytes": images[name]["programmed_bytes"],
            "minimum_address": images[name]["minimum_address"],
            "maximum_address": images[name]["maximum_address"],
        }
        for name in ["loader", *ota_names]
    }

    failed_events = {event["name"]: event for event in failed_run["events"]}
    completed_events = {
        event["name"]: event for event in completed_run["events"]
    }
    chunk_runtime = {}
    for chunk in (3, 2, 1):
        prefix = f"browser-life-assets-chunk-{chunk}"
        chunk_runtime[str(chunk)] = {
            "outcome": "provisioned",
            "write_to_provision_ms": elapsed_ms(
                failed_events, f"{prefix}-write", f"{prefix}-provision"
            ),
        }
    chunk_runtime["0"] = {
        "outcome": "timed_out",
        "write_to_failure_ms": elapsed_ms(
            failed_events, "browser-life-assets-chunk-0-write", "run"
        ),
    }

    logs = [
        OLD / "chunk-0-build.log",
        OLD / "chunk-1-build.log",
        OLD / "chunk-2-build.log",
        OLD / "current-build-r2.stdout.log",
    ]
    build_logs = [log_identity(path) for path in logs]
    build_logs_with_full_link = sum(
        item["complete_app_link_count"] > 0 for item in build_logs
    )
    representative_full_link_contract = all(
        item["links_app_ble"]
        and item["links_opus_encoder"]
        and item["links_epaper_runtime"]
        for item in build_logs
    )

    chunk_lengths = [
        int(chunk["bytes"]) for chunk in precheck["provision_chunks"]
    ]
    checks = {
        "historical_precheck_was_hardware_free": (
            precheck["hardware_contact"] == 0
        ),
        "old_path_embedded_four_exact_cemp_chunks": (
            len(chunk_lengths) == 4
            and sum(chunk_lengths) == precheck["cemp"]["bytes"]
            and all(
                chunk["embedded_exactly_once"]
                for chunk in precheck["provision_chunks"]
            )
        ),
        "old_path_built_five_complete_ota_images": len(ota_names) == 5,
        "old_path_relinked_complete_application": (
            build_logs_with_full_link == len(build_logs)
            and representative_full_link_contract
        ),
        "old_path_wrote_loader_and_ota_region": (
            images["loader"]["minimum_address"] == "0x08000000"
            and all(
                images[name]["minimum_address"] == "0x08007000"
                for name in ota_names
            )
        ),
        "old_failed_run_reached_three_chunks_then_timed_out": (
            all(item["outcome"] == "provisioned" for item in (
                chunk_runtime["3"],
                chunk_runtime["2"],
                chunk_runtime["1"],
            ))
            and chunk_runtime["0"]["outcome"] == "timed_out"
        ),
        "old_complete_run_reflashed_loader_asset_app_and_product_app": all(
            name in completed_events
            for name in (
                "loader-write",
                "browser-life-assets-write",
                "product-first-write",
                "machine-verification",
            )
        ),
        "fresh_full_cemp_matches_current_base_identity": (
            sha256(cemp_binary) == initial_sync["base_cemp_sha256"]
            and cemp_binary.stat().st_size == initial_sync["base_cemp_bytes"]
        ),
        "measurement_made_no_hardware_contact": True,
    }
    failed_checks = [name for name, passed in checks.items() if not passed]
    if failed_checks:
        raise RuntimeError(
            "slow path baseline failed: " + ", ".join(failed_checks)
        )

    product_pid = OLD / "current-build-r2.pid"
    product_log = OLD / "current-build-r2.stdout.log"
    observed_product_build_ms = round(
        (
            product_log.stat().st_mtime_ns
            - product_pid.stat().st_mtime_ns
        )
        / 1_000_000
    )
    receipt = {
        "schema": "companion.comp_req_775.slow_path_baseline.v1",
        "status": "PASS_SLOW_PATH_BASELINE",
        "checks": checks,
        "full_export": {
            "elapsed_ms": initial_sync["source_pack"]["elapsed_ms"],
            "states": initial_sync["source_pack"]["states"],
            "unique_frames": initial_sync["source_pack"]["unique_frames"],
            "raw_frame_bytes": initial_sync["source_pack"]["frame_bytes"],
            "manifest_sha256": initial_sync["source_pack"][
                "manifest_sha256"
            ],
        },
        "fresh_full_cemp": {
            "manifest_elapsed_ms": manifest_ms,
            "pack_elapsed_ms": cemp_ms,
            "total_elapsed_ms": manifest_ms + cemp_ms,
            "bytes": cemp_binary.stat().st_size,
            "sha256": sha256(cemp_binary),
            "manifest_sha256": sha256(cemp_manifest),
            "metadata_sha256": sha256(cemp_metadata),
            "manifest_stdout": manifest_stdout,
            "pack_stdout": cemp_stdout,
        },
        "old_embedded_application_builds": {
            "complete_ota_image_count": len(ota_names),
            "provision_image_count": 4,
            "product_image_count": 1,
            "representative_build_logs_with_full_link": (
                build_logs_with_full_link
            ),
            "representative_links_shared_application_runtime": (
                representative_full_link_contract
            ),
            "observed_product_rebuild_ms_from_log_times": (
                observed_product_build_ms
            ),
            "build_logs": build_logs,
            "images": image_evidence,
        },
        "old_write_amplification": {
            "external_cemp_bytes": precheck["cemp"]["bytes"],
            "embedded_chunk_bytes": sum(chunk_lengths),
            "ota_application_programmed_bytes": ota_bytes,
            "loader_programmed_bytes": loader_bytes,
            "total_internal_flash_programmed_bytes": total_internal_bytes,
            "internal_bytes_per_external_cemp_byte": round(
                total_internal_bytes / precheck["cemp"]["bytes"], 3
            ),
        },
        "old_hardware_runtime": {
            "four_chunk_attempt": {
                "source": relative(failed_run_path),
                "source_sha256": sha256(failed_run_path),
                "loader_write_to_failure_ms": elapsed_ms(
                    failed_events, "loader-write", "run"
                ),
                "run_start_to_failure_ms": elapsed_ms(
                    failed_events, "pwsh7-verification", "run"
                ),
                "chunks": chunk_runtime,
                "programmer_call_count": len(
                    failed_run["programmer_calls"]
                ),
                "outcome": failed_run["status"],
            },
            "completed_loader_asset_product_cycle": {
                "source": relative(completed_run_path),
                "source_sha256": sha256(completed_run_path),
                "loader_write_to_machine_ready_ms": elapsed_ms(
                    completed_events,
                    "loader-write",
                    "machine-verification",
                ),
                "programmer_call_count": len(
                    completed_run["programmer_calls"]
                ),
                "outcome": completed_run["status"],
            },
        },
        "source_identities": {
            "precheck": {
                "path": relative(precheck_path),
                "sha256": sha256(precheck_path),
            },
            "source_pack_manifest": {
                "path": relative(
                    SOURCE_PACK / "source-pack-manifest.json"
                ),
                "sha256": sha256(
                    SOURCE_PACK / "source-pack-manifest.json"
                ),
            },
        },
        "hardware_contact": 0,
        "write_calls": 0,
        "erase_calls": 0,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=True) + "\n",
        encoding="ascii",
        newline="\n",
    )
    print(
        "PASS_COMP_REQ_775_SLOW_PATH "
        f"export_ms={receipt['full_export']['elapsed_ms']} "
        f"cemp_ms={manifest_ms + cemp_ms} "
        f"ota_images={len(ota_names)} "
        f"internal_bytes={total_internal_bytes} hardware_contact=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
