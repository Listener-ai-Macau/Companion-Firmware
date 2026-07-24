#!/usr/bin/env python3
"""Fail-closed verifier for the COMP-REQ-540 browser/PBM/C frame pack."""

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
PBM_HEADER = b"P4\n200 200\n"
FRAME_BYTES = 5000


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def canonical_text(value: bytes) -> bytes:
    return value.decode("utf-8").replace("\r\n", "\n").encode("utf-8")


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def inside_root(value: str) -> Path:
    result = (ROOT / value).resolve()
    result.relative_to(ROOT)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-page-sha256")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pack_root = inside_root(args.pack)
    output_path = inside_root(args.output)
    manifest_path = pack_root / "visual-frame-manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    page_sha = sha256(canonical_text(PAGE.read_bytes()))
    expected_page = (args.expected_page_sha256 or page_sha).upper()
    frames = (pack_root / manifest["files"]["frames"]["path"]).read_bytes()
    c_bytes = (pack_root / manifest["files"]["c"]["path"]).read_bytes()
    h_bytes = (pack_root / manifest["files"]["h"]["path"]).read_bytes()
    c_payload = bytes(
        int(value, 16)
        for value in re.findall(rb"0x([0-9a-fA-F]{2})", c_bytes)
    )
    c_mapping = [
        (int(index), state.decode("ascii"))
        for index, state in re.findall(
            rb"^\s+(\d+), /\* ([a-z0-9_]+) \*/$",
            c_bytes,
            flags=re.MULTILINE,
        )
    ]
    states = manifest["states"]
    unique_count = manifest["invariants"]["unique_frame_count"]
    meter_states = [
        state for state in states if state["id"].startswith("recording_")
    ]
    checks = {
        "browser_to_c_pixel_diff_zero": all(
            state["pixel_diff_after_registered_transform"] == 0
            and state["browser_frame_sha256"]
            == state["c_reconstructed_sha256"]
            for state in states
        ),
        "c_payload_reconstructs_unique_frames": c_payload == frames,
        "c_state_mapping_exact": (
            len(c_mapping) == len(states)
            and all(
                c_mapping[index]
                == (state["unique_frame_index"], state["id"])
                for index, state in enumerate(states)
            )
        ),
        "default_off": (
            b"#define COMPANION_BROWSER_FAMILY_MICRO_PACK_ENABLED 0"
            in h_bytes
        ),
        "file_hashes_exact": (
            sha256(c_bytes) == manifest["files"]["c"]["sha256"]
            and sha256(frames) == manifest["files"]["frames"]["sha256"]
            and sha256(h_bytes) == manifest["files"]["h"]["sha256"]
        ),
        "format_exact": (
            manifest["format"]["width"] == 200
            and manifest["format"]["height"] == 200
            and manifest["format"]["bits_per_pixel"] == 1
            and manifest["format"]["row_stride_bytes"] == 25
            and manifest["format"]["frame_bytes"] == FRAME_BYTES
            and manifest["format"]["black_bit"] == 1
            and manifest["format"]["white_bit"] == 0
        ),
        "meter_contract_exact": (
            manifest["invariants"]["meter_state_count"] == 8
            and len(meter_states) == 17
            and all(
                state["meter"]["column_count"] == 3
                and state["meter"]["gray_pixels"] == 0
                and len(state["meter"]["columns"]) == 3
                and {
                    column["geometry"]["width"]
                    for column in state["meter"]["columns"]
                }
                == {4}
                for state in meter_states
            )
        ),
        "no_gray_input_pixels": all(
            state["gray_input_pixels"] == 0 for state in states
        ),
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
        "pack_capacity_exact": (
            len(frames) == unique_count * FRAME_BYTES
            and len(c_payload) == len(frames)
        ),
        "pbm_reconstructs_every_state": True,
        "source_manifest_pass": manifest["status"] == "PASS",
        "state_identity_exact": (
            len(states) == 111
            and manifest["invariants"]["state_count"] == 111
            and len({state["id"] for state in states}) == 111
            and manifest["invariants"]["emotion_count"] == 10
            and sum(
                state["id"].startswith("family_micro_")
                for state in states
            ) == 40
            and manifest["invariants"][
                "recording_composed_emotion_count"
            ]
            == 10
        ),
    }
    pbm_rows = []
    for state in states:
        pbm = (pack_root / state["pbm_file"]).read_bytes()
        index = state["unique_frame_index"]
        expected = frames[index * FRAME_BYTES : (index + 1) * FRAME_BYTES]
        passed = (
            pbm.startswith(PBM_HEADER)
            and len(pbm) == len(PBM_HEADER) + FRAME_BYTES
            and pbm[len(PBM_HEADER) :] == expected
            and sha256(pbm) == state["pbm_sha256"]
            and sha256(expected) == state["browser_frame_sha256"]
        )
        pbm_rows.append({"id": state["id"], "pass": passed})
        checks["pbm_reconstructs_every_state"] &= passed
    failed = sorted(name for name, passed in checks.items() if not passed)
    result = {
        "schema": "companion.comp-req-540-parity-verifier.v1",
        "status": "PASS" if not failed else "NO_GO",
        "checks": checks,
        "failed": failed,
        "inputs": {
            "manifest_repo_path": manifest_path.relative_to(ROOT).as_posix(),
            "manifest_sha256": sha256(manifest_bytes),
            "page_canonical_sha256": page_sha,
        },
        "observed": {
            "c_payload_bytes": len(c_payload),
            "meter_state_count": len(meter_states),
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
    print(json.dumps({
        "output": output_path.relative_to(ROOT).as_posix(),
        "sha256": sha256(output),
        "status": result["status"],
    }, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
