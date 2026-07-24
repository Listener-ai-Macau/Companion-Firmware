#!/usr/bin/env python3
"""Fail-closed verifier for the COMP-REQ-536/537/538 browser C/PBM pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PAGE = (
    ROOT
    / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7"
    / "candidate/wb55-browser-parity-attempt-01/index.html"
)


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def canonical_text(value: bytes) -> bytes:
    return value.decode("utf-8").replace("\r\n", "\n").encode("utf-8")


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-page-sha256")
    return parser.parse_args()


def inside_root(value: str) -> Path:
    result = (ROOT / value).resolve()
    result.relative_to(ROOT)
    return result


def main() -> int:
    args = parse_args()
    pack_root = inside_root(args.pack)
    output_path = inside_root(args.output)
    manifest_path = pack_root / "visual-frame-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    page_sha = sha256(canonical_text(PAGE.read_bytes()))
    expected_page = (args.expected_page_sha256 or page_sha).upper()
    frames = (pack_root / manifest["files"]["frames"]["path"]).read_bytes()
    c_path = pack_root / manifest["files"]["c"]["path"]
    h_path = pack_root / manifest["files"]["h"]["path"]
    c_bytes = c_path.read_bytes()
    h_bytes = h_path.read_bytes()
    c_hex = bytes(
        int(value, 16)
        for value in re.findall(rb"0x([0-9a-fA-F]{2})", c_bytes)
    )
    states = manifest["states"]
    unique_count = manifest["invariants"]["unique_frame_count"]
    expected_pack_bytes = unique_count * 5000
    checks = {
        "browser_to_c_pixel_diff_zero": all(
            state["pixel_diff_after_registered_transform"] == 0
            and state["browser_frame_sha256"]
            == state["c_reconstructed_sha256"]
            for state in states
        ),
        "c_bytes_reconstruct_frames_exact": c_hex == frames,
        "c_hash_exact": sha256(c_bytes)
        == manifest["files"]["c"]["sha256"],
        "default_off": (
            b"#define COMPANION_BROWSER_EPAPER_VISUAL_PACK_ENABLED 0"
            in h_bytes
        ),
        "embedded_manifest_contract": (
            manifest["source"]["embedded_manifest"]["cadence_ms"] == 480
            and manifest["source"]["embedded_manifest"]["format"][
                "bits_per_pixel"
            ]
            == 1
        ),
        "emotion_catalog_complete": (
            manifest["invariants"]["emotion_count"] == 10
            and manifest["invariants"]["recording_composed_emotion_count"]
            == 10
        ),
        "frame_pack_bytes_exact": (
            len(frames) == expected_pack_bytes
            and len(frames) % 5000 == 0
        ),
        "frames_hash_exact": sha256(frames)
        == manifest["files"]["frames"]["sha256"],
        "header_hash_exact": sha256(h_bytes)
        == manifest["files"]["h"]["sha256"],
        "orientation_identity": (
            manifest["format"]["orientation"]["device_transform"] == "identity"
            and all(
                state["orientation_transform"] == "identity"
                for state in states
            )
        ),
        "page_identity_exact": (
            page_sha == expected_page
            and manifest["source"]["page_canonical_sha256"] == expected_page
        ),
        "pbm_reconstructs_every_state": True,
        "source_manifest_pass": manifest["status"] == "PASS",
        "state_count_exact": (
            manifest["invariants"]["state_count"] == 71
            and len(states) == 71
        ),
    }
    pbm_rows = []
    for state in states:
        pbm = (pack_root / state["pbm_file"]).read_bytes()
        header = b"P4\n200 200\n"
        index = state["unique_frame_index"]
        expected = frames[index * 5000 : (index + 1) * 5000]
        passed = (
            pbm.startswith(header)
            and len(pbm) == len(header) + 5000
            and pbm[len(header) :] == expected
            and sha256(pbm) == state["pbm_sha256"]
            and sha256(expected) == state["browser_frame_sha256"]
        )
        pbm_rows.append({"id": state["id"], "pass": passed})
        checks["pbm_reconstructs_every_state"] &= passed
    failed = sorted(name for name, passed in checks.items() if not passed)
    result = {
        "schema": "companion.comp-req-536-538-parity-verifier.v1",
        "status": "PASS" if not failed else "NO_GO",
        "checks": checks,
        "failed": failed,
        "inputs": {
            "manifest_repo_path": manifest_path.relative_to(ROOT).as_posix(),
            "manifest_sha256": sha256(manifest_path.read_bytes()),
            "page_canonical_sha256": page_sha,
        },
        "observed": {
            "c_payload_bytes": len(c_hex),
            "pack_bytes": len(frames),
            "pbm_reconstructed": sum(row["pass"] for row in pbm_rows),
            "state_count": len(states),
            "unique_frame_count": unique_count,
        },
        "pbm_rows": pbm_rows,
        "side_effects": {
            "browser": 0,
            "hardware": 0,
            "owner_prompt": 0,
            "production_write": 0,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output = canonical_bytes(result)
    output_path.write_bytes(output)
    print(
        json.dumps(
            {
                "output": output_path.relative_to(ROOT).as_posix(),
                "sha256": sha256(output),
                "status": result["status"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
