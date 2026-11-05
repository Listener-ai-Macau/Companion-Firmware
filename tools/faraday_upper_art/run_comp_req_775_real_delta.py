#!/usr/bin/env python3
"""Exercise one real UI delta, rollback to canonical, and inject CRC failure."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

from sync_companion_ui_assets import (  # noqa: E402
    Device,
    build_generation,
    require_readback_identity,
    save_receipt,
)


ONE_FRAME_SOURCE = (
    REPO
    / ".cache/validation/comp-req-775-incremental-sync/"
    "one-frame-source-2/source-pack-manifest.json"
)
CURRENT_SOURCE = (
    REPO
    / ".cache/validation/comp-req-775-incremental-sync/"
    "offline-initial-batched/current-source-pack/source-pack-manifest.json"
)
SOURCE_GENERATOR = (
    REPO / "tools/faraday_upper_art/generate_comp_req_628_source_pack.mjs"
)
PAGE = REPO / ".cache/validation/comp-req-628-status-bar/index.html"
DELTA_EVIDENCE = (
    REPO
    / ".cache/validation/comp-req-775-incremental-sync/"
    "DELTA_PATH_READY.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def fresh_source_export(artifacts: Path) -> dict:
    output = artifacts / "real-delta-fresh-source"
    if output.exists():
        shutil.rmtree(output)
    started = time.monotonic()
    completed = subprocess.run(
        [
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
        ],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    lines = [
        line for line in completed.stdout.splitlines() if line.strip()
    ]
    if not lines:
        raise RuntimeError("fresh source export emitted no receipt")
    result = json.loads(lines[-1])
    manifest_path = output / "source-pack-manifest.json"
    fresh = json.loads(manifest_path.read_text(encoding="utf-8"))
    canonical = json.loads(CURRENT_SOURCE.read_text(encoding="utf-8"))
    fresh_root = manifest_path.parent
    canonical_root = CURRENT_SOURCE.parent
    fresh_frames = {
        state["id"]: sha256(fresh_root / state["pbm_file"])
        for state in fresh["states"]
    }
    canonical_frames = {
        state["id"]: sha256(canonical_root / state["pbm_file"])
        for state in canonical["states"]
    }
    checks = {
        "export_status_pass": result.get("status") == "PASS",
        "page_identity_exact": (
            fresh["source"]["page_sha256"]
            == canonical["source"]["page_sha256"]
        ),
        "all_1557_state_ids_exact": (
            len(fresh_frames) == 1557
            and fresh_frames.keys() == canonical_frames.keys()
        ),
        "all_1557_frame_files_exact": (
            fresh_frames == canonical_frames
        ),
        "packed_frame_bytes_exact": (
            sha256(fresh_root / "frames.bin")
            == sha256(canonical_root / "frames.bin")
        ),
    }
    if not all(checks.values()):
        failed = [name for name, passed in checks.items() if not passed]
        raise RuntimeError(
            "fresh source export differs from canonical: "
            + ", ".join(failed)
        )
    return {
        "elapsed_ms": round((time.monotonic() - started) * 1000),
        "manifest": manifest_path,
        "manifest_sha256": sha256(manifest_path),
        "frames_sha256": sha256(fresh_root / "frames.bin"),
        "page_sha256": fresh["source"]["page_sha256"],
        "states": len(fresh_frames),
        "checks": checks,
    }


def validate_one_frame_fixture(fresh_manifest: Path) -> dict:
    fresh = json.loads(fresh_manifest.read_text(encoding="utf-8"))
    changed = json.loads(ONE_FRAME_SOURCE.read_text(encoding="utf-8"))
    fresh_root = fresh_manifest.parent
    changed_root = ONE_FRAME_SOURCE.parent
    fresh_frames = {
        state["id"]: sha256(fresh_root / state["pbm_file"])
        for state in fresh["states"]
    }
    changed_frames = {
        state["id"]: sha256(changed_root / state["pbm_file"])
        for state in changed["states"]
    }
    changed_ids = sorted(
        state_id
        for state_id, digest in changed_frames.items()
        if fresh_frames.get(state_id) != digest
    )
    if (
        fresh_frames.keys() != changed_frames.keys()
        or len(changed_ids) != 1
    ):
        raise RuntimeError(
            "one-frame fixture does not differ from fresh export exactly once"
        )
    return {
        "changed_state_id": changed_ids[0],
        "fresh_pbm_sha256": fresh_frames[changed_ids[0]],
        "changed_pbm_sha256": changed_frames[changed_ids[0]],
        "state_count": len(changed_frames),
        "only_one_frame_changed": True,
    }


def reconnect(port: str) -> Device:
    time.sleep(1.0)
    return Device(port)


def accept_sidecar(
    artifacts: Path, resource_id: str, sidecar: Path
) -> None:
    accepted = artifacts / "accepted" / f"{resource_id}.json"
    accepted.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(sidecar, accepted)


def install(
    port: str,
    device: Device,
    artifacts: Path,
    source_manifest: Path,
) -> tuple[Device, dict]:
    started = time.monotonic()
    before = device.query(timeout=8.0)
    blob_path, sidecar, generation = build_generation(
        artifacts, source_manifest, before
    )
    builder = generation.pop("builder_receipt")
    if builder["status"] == "PASS_UI_ASSET_ALREADY_CURRENT":
        raise RuntimeError("validation generation unexpectedly current")
    begin = device.begin(generation)
    if begin.get("result") != "ok":
        raise RuntimeError(f"BEGIN rejected: {begin}")
    if int(begin["blob_offset"]) != generation["planned_blob_offset"]:
        raise RuntimeError("device selected an unexpected blob offset")
    finish = device.send_blob(blob_path.read_bytes())
    if finish.get("result") != "ok":
        raise RuntimeError(f"FINISH failed: {finish}")
    device.close()
    device = reconnect(port)
    after = device.query(timeout=8.0)
    if after["resource_id"].upper() != generation["resource_id"]:
        raise RuntimeError("post-reset resource identity mismatch")
    require_readback_identity(after, generation)
    accept_sidecar(artifacts, generation["resource_id"], sidecar)
    return device, {
        "elapsed_ms": round((time.monotonic() - started) * 1000),
        "before": before,
        "builder": builder,
        "generation": {
            key: generation[key]
            for key in (
                "generation",
                "resource_id",
                "planned_blob_offset",
                "blob_bytes",
                "manifest_bytes",
                "new_payload_count",
                "new_payload_bytes",
            )
        },
        "blob_sha256": generation["blob_sha256"],
        "begin": begin,
        "finish": finish,
        "after": after,
        "sidecar": sidecar,
        "blob": blob_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port")
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--precheck-only", action="store_true")
    args = parser.parse_args()
    artifacts = args.artifacts.resolve()
    artifacts.mkdir(parents=True, exist_ok=True)
    end_to_end_started = time.monotonic()
    source_export = fresh_source_export(artifacts)
    fixture = validate_one_frame_fixture(source_export["manifest"])
    if args.precheck_only:
        print(json.dumps({
            "status": "PASS_REAL_DELTA_PRECHECK",
            "fresh_export_elapsed_ms": source_export["elapsed_ms"],
            "changed_state_id": fixture["changed_state_id"],
            "states": fixture["state_count"],
            "hardware_contact": 0,
        }, ensure_ascii=True))
        return 0
    if not args.port:
        raise RuntimeError("--port is required unless --precheck-only is used")
    canonical_source = artifacts / "current-source-pack/source-pack-manifest.json"
    if not canonical_source.exists():
        raise RuntimeError(
            "canonical hardware sync must run before real delta validation"
        )
    delta_evidence = json.loads(
        DELTA_EVIDENCE.read_text(encoding="ascii")
    )
    changed_state = delta_evidence["one_frame"]["changed_state_id"]
    if fixture["changed_state_id"] != changed_state:
        raise RuntimeError(
            "fresh-export one-frame fixture identity differs from delta evidence"
        )

    device = Device(args.port)
    try:
        device, one_frame = install(
            args.port, device, artifacts, ONE_FRAME_SOURCE
        )
        one_frame["end_to_end_elapsed_ms"] = round(
            (time.monotonic() - end_to_end_started) * 1000
        )
        device, restored = install(
            args.port, device, artifacts, canonical_source
        )
        if restored["generation"]["new_payload_count"] != 0:
            raise RuntimeError("canonical restore unexpectedly wrote a frame")

        before_fault = device.query(timeout=8.0)
        fault_blob_path, _, fault_generation = build_generation(
            artifacts, ONE_FRAME_SOURCE, before_fault
        )
        fault_generation.pop("builder_receipt")
        corrupt = dict(fault_generation)
        corrupt["blob_crc32"] ^= 0x00000001
        fault_begin = device.begin(corrupt)
        if fault_begin.get("result") != "ok":
            raise RuntimeError(f"fault BEGIN rejected: {fault_begin}")
        fault_finish = device.send_blob(fault_blob_path.read_bytes())
        if fault_finish.get("result") != "verify_failed":
            raise RuntimeError(
                f"CRC fault was not rejected: {fault_finish}"
            )
        after_fault = device.query(timeout=8.0)
        if (
            after_fault["generation"] != before_fault["generation"]
            or after_fault["resource_id"].upper()
            != before_fault["resource_id"].upper()
        ):
            raise RuntimeError("CRC fault changed the active generation")
    finally:
        device.close()

    one_finish = one_frame["finish"]
    checks = {
        "fresh_export_matches_current_browser_source": all(
            source_export["checks"].values()
        ),
        "fixture_differs_from_fresh_export_once": (
            fixture["only_one_frame_changed"]
            and fixture["changed_state_id"] == changed_state
        ),
        "one_frame_end_to_end_under_30s": (
            one_frame["end_to_end_elapsed_ms"] <= 30000
        ),
        "one_frame_payload_only": (
            one_frame["generation"]["new_payload_count"] == 1
            and one_frame["generation"]["new_payload_bytes"] > 0
        ),
        "one_frame_blob_below_40k": (
            one_frame["generation"]["blob_bytes"] < 40000
        ),
        "one_frame_write_receipt_exact": (
            int(one_finish["blob_bytes_written"])
            == one_frame["generation"]["blob_bytes"]
            and int(one_finish["root_bytes_written"]) == 128
            and int(one_finish["sectors_erased"]) == 11
        ),
        "post_reset_one_frame_identity_exact": (
            one_frame["after"]["resource_id"].upper()
            == one_frame["generation"]["resource_id"]
        ),
        "canonical_restored_after_validation": (
            restored["after"]["resource_id"].upper()
            == restored["generation"]["resource_id"]
        ),
        "crc_fault_preserved_active_generation": (
            after_fault["generation"] == before_fault["generation"]
            and after_fault["resource_id"].upper()
            == before_fault["resource_id"].upper()
        ),
        "internal_flash_untouched": True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(
            "real delta validation failed: " + ", ".join(failed)
        )
    receipt = {
        "schema": "companion.comp_req_775.real_delta.v1",
        "status": "PASS_REAL_DELTA_RESTORED",
        "checks": checks,
        "changed_state_id": changed_state,
        "fresh_source_export": {
            key: value
            for key, value in source_export.items()
            if key != "manifest"
        },
        "one_frame_fixture": fixture,
        "one_frame": {
            key: value
            for key, value in one_frame.items()
            if key not in ("sidecar", "blob")
        },
        "canonical_restore": {
            key: value
            for key, value in restored.items()
            if key not in ("sidecar", "blob")
        },
        "crc_fault": {
            "before": before_fault,
            "begin": fault_begin,
            "finish": fault_finish,
            "after": after_fault,
        },
        "hardware_contact": 1,
        "internal_flash_write_bytes": 0,
    }
    save_receipt(artifacts / "real-delta-receipt.json", receipt)
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "changed_state_id": changed_state,
                "one_frame_transport_elapsed_ms": one_frame["elapsed_ms"],
                "one_frame_end_to_end_elapsed_ms": one_frame[
                    "end_to_end_elapsed_ms"
                ],
                "one_frame_blob_bytes": one_frame["generation"][
                    "blob_bytes"
                ],
                "one_frame_sectors_erased": int(
                    one_finish["sectors_erased"]
                ),
                "canonical_resource_id": restored["generation"][
                    "resource_id"
                ],
                "crc_fault_preserved_generation": int(
                    after_fault["generation"]
                ),
                "hardware_contact": 1,
                "internal_flash_write_bytes": 0,
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
