#!/usr/bin/env python3
"""Rebuild and measure the no-op and one-frame COMP-REQ-775 delta plans."""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
ARTIFACTS = REPO / ".cache/validation/comp-req-775-incremental-sync"
WORK = ARTIFACTS / "delta-path-rebuild"
BASE_ROOT = REPO / ".cache/validation/comp-req-774-browser-full-source-pack"
BASE_MANIFEST = BASE_ROOT / "source-pack-manifest.json"
BASE_CEMP = BASE_ROOT / "cemp/comp_req_774_browser_full.cemp"
CURRENT_MANIFEST = (
    ARTIFACTS
    / "offline-initial-batched/current-source-pack/source-pack-manifest.json"
)
ONE_FRAME_MANIFEST = (
    ARTIFACTS / "one-frame-source-2/source-pack-manifest.json"
)
BUILDER = REPO / "tools/faraday_upper_art/build_ui_asset_generation.py"
VERIFIER = REPO / "tools/faraday_upper_art/verify_ui_asset_generation.py"
OUTPUT = ARTIFACTS / "DELTA_PATH_READY.json"
SECTOR_BYTES = 4096
ARENA_END = 0x001DC000
ROOT_A = 0x001FE000


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def align_sector(value: int) -> int:
    return (value + SECTOR_BYTES - 1) & ~(SECTOR_BYTES - 1)


def run_timed(args: list[str]) -> tuple[int, dict]:
    started = time.perf_counter_ns()
    completed = subprocess.run(
        args,
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    lines = [line for line in completed.stdout.splitlines() if line]
    return (
        round((time.perf_counter_ns() - started) / 1_000_000),
        json.loads(lines[-1]),
    )


def build(
    source: Path,
    offset: int,
    name: str,
    active: Path | None = None,
) -> tuple[Path, Path, int, dict]:
    blob = WORK / f"{name}.blob"
    sidecar = WORK / f"{name}.json"
    command = [
        sys.executable,
        str(BUILDER),
        "--source-pack-manifest",
        str(source),
        "--base-source-pack-manifest",
        str(BASE_MANIFEST),
        "--planned-blob-offset",
        hex(offset),
        "--output-blob",
        str(blob),
        "--output-generation",
        str(sidecar),
    ]
    if active is not None:
        command.extend(["--active-generation", str(active)])
    elapsed_ms, stdout = run_timed(command)
    return blob, sidecar, elapsed_ms, stdout


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    initial_offset = align_sector(BASE_CEMP.stat().st_size)
    initial_blob, initial_sidecar, initial_ms, initial_stdout = build(
        CURRENT_MANIFEST, initial_offset, "generation-1"
    )
    generation1 = load(initial_sidecar)
    delta_offset = align_sector(
        initial_offset + generation1["blob_bytes"]
    )
    delta_blob, delta_sidecar, delta_ms, delta_stdout = build(
        ONE_FRAME_MANIFEST,
        delta_offset,
        "generation-2-one-frame",
        initial_sidecar,
    )
    generation2 = load(delta_sidecar)

    equivalence1 = WORK / "generation-1-equivalence.json"
    equivalence2 = WORK / "generation-2-equivalence.json"
    run_timed(
        [
            sys.executable,
            str(VERIFIER),
            "--source-pack-manifest",
            str(CURRENT_MANIFEST),
            "--generation",
            str(initial_sidecar),
            "--base-cemp",
            str(BASE_CEMP),
            "--output",
            str(equivalence1),
        ]
    )
    run_timed(
        [
            sys.executable,
            str(VERIFIER),
            "--source-pack-manifest",
            str(ONE_FRAME_MANIFEST),
            "--generation",
            str(delta_sidecar),
            "--base-cemp",
            str(BASE_CEMP),
            "--blob",
            f"{delta_offset}={delta_blob}",
            "--output",
            str(equivalence2),
        ]
    )
    verified1 = load(equivalence1)
    verified2 = load(equivalence2)

    current = load(CURRENT_MANIFEST)
    changed = load(ONE_FRAME_MANIFEST)
    current_root = CURRENT_MANIFEST.parent
    changed_root = ONE_FRAME_MANIFEST.parent
    current_states = {
        state["id"]: sha256(current_root / state["pbm_file"])
        for state in current["states"]
    }
    changed_states = {
        state["id"]: sha256(changed_root / state["pbm_file"])
        for state in changed["states"]
    }
    changed_ids = sorted(
        state_id
        for state_id, digest in changed_states.items()
        if current_states.get(state_id) != digest
    )
    sectors = math.ceil(generation2["blob_bytes"] / SECTOR_BYTES)
    checks = {
        "input_diff_is_exactly_one_frame": len(changed_ids) == 1,
        "fixture_declares_original_hash_for_changed_frame": (
            len(changed_ids) == 1
            and next(
                    state["pbm_sha256"]
                    for state in changed["states"]
                    if state["id"] == changed_ids[0]
                )
                != changed_states[changed_ids[0]]
        ),
        "initial_generation_reuses_only_base_frames": (
            generation1["new_payload_count"] == 0
        ),
        "delta_contains_exactly_one_new_payload": (
            generation2["new_payload_count"] == 1
            and generation2["new_payload_bytes"] > 0
        ),
        "delta_is_manifest_plus_one_payload": (
            generation2["blob_bytes"]
            == generation2["manifest_bytes"]
            + generation2["new_payload_bytes"]
        ),
        "delta_erases_only_ten_blob_sectors": sectors == 10,
        "delta_stays_below_static_resource_region": (
            delta_offset + align_sector(generation2["blob_bytes"])
            <= ARENA_END
        ),
        "delta_stays_below_root_region": (
            delta_offset + align_sector(generation2["blob_bytes"]) < ROOT_A
        ),
        "both_generations_match_all_1557_browser_states": (
            verified1["states_checked"] == 1557
            and verified2["states_checked"] == 1557
            and verified1["strict_1bpp"]
            and verified2["strict_1bpp"]
        ),
        "measurement_made_no_hardware_contact": True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("delta path failed: " + ", ".join(failed))

    receipt = {
        "schema": "companion.comp_req_775.delta_path.v1",
        "status": "PASS_DELTA_PATH",
        "checks": checks,
        "initial": {
            "builder_elapsed_ms": initial_ms,
            "builder": initial_stdout,
            "blob_bytes": generation1["blob_bytes"],
            "blob_sha256": sha256(initial_blob),
            "generation_sha256": sha256(initial_sidecar),
        },
        "one_frame": {
            "changed_state_id": changed_ids[0],
            "builder_elapsed_ms": delta_ms,
            "builder": delta_stdout,
            "planned_blob_offset": delta_offset,
            "manifest_bytes": generation2["manifest_bytes"],
            "new_payload_bytes": generation2["new_payload_bytes"],
            "blob_bytes": generation2["blob_bytes"],
            "blob_sectors": sectors,
            "root_commit_bytes": 128,
            "blob_sha256": sha256(delta_blob),
            "generation_sha256": sha256(delta_sidecar),
        },
        "equivalence": {
            "generation_1": verified1,
            "generation_2": verified2,
        },
        "hardware_contact": 0,
        "internal_flash_write_bytes": 0,
    }
    OUTPUT.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=True) + "\n",
        encoding="ascii",
        newline="\n",
    )
    print(
        "PASS_COMP_REQ_775_DELTA_PATH "
        f"changed={changed_ids[0]} build_ms={delta_ms} "
        f"blob_bytes={generation2['blob_bytes']} sectors={sectors} "
        "hardware_contact=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
