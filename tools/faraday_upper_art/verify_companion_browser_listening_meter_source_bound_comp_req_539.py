#!/usr/bin/env python3
"""Source-bound MACHINE_READY gate for the COMP-REQ-539 browser successor."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
VALIDATION = Path(
    "docs/validation/"
    "companion-browser-listening-meter-successor-comp-req-539"
)
EXPORT = Path(
    "docs/art/exports/companion-browser-listening-meter-comp-req-539"
)
PAGE = Path(
    "docs/art/iterations/"
    "companion-pet-expression-v9-two-track-rig-v7/"
    "candidate/wb55-browser-parity-attempt-01/index.html"
)
DOCUMENT_PATHS = {
    "focused": VALIDATION / "focused-oracle.json",
    "replay": VALIDATION / "replay-run/browser-replay-result.json",
    "pixel": VALIDATION / "replay-run/pixel-dom-route-artifact.json",
    "screenshots": VALIDATION / "replay-run/screenshot-manifest.json",
    "parity": VALIDATION / "parity-verifier.json",
    "manifest": EXPORT / "visual-frame-manifest.json",
}
SOURCE_PATHS = {
    "page": PAGE,
    "focused_tool": Path(
        "tools/faraday_upper_art/"
        "verify_companion_browser_listening_meter_comp_req_539.mjs"
    ),
    "replay_tool": Path(
        "tools/faraday_upper_art/"
        "replay_companion_browser_listening_meter_comp_req_539.mjs"
    ),
    "generator": Path(
        "tools/faraday_upper_art/"
        "generate_companion_browser_listening_meter_parity_comp_req_539.mjs"
    ),
    "parity_tool": Path(
        "tools/faraday_upper_art/"
        "verify_companion_browser_listening_meter_parity_comp_req_539.py"
    ),
    "source_gate": Path(
        "tools/faraday_upper_art/"
        "verify_companion_browser_listening_meter_source_bound_comp_req_539.py"
    ),
    "negative_gate": Path(
        "tools/faraday_upper_art/"
        "test_companion_browser_listening_meter_source_bound_negatives_comp_req_539.py"
    ),
    "packet_tool": Path(
        "tools/faraday_upper_art/"
        "prepare_companion_browser_listening_meter_owner_packet_comp_req_539.py"
    ),
    "owner_runner": Path(
        "tools/faraday_upper_art/"
        "run_companion_browser_listening_meter_owner_review_comp_req_539.ps1"
    ),
}
PACK_PATHS = {
    "frames": EXPORT / "frames.bin",
    "c_pack": EXPORT / "companion_browser_listening_meter_pack.c",
    "h_pack": EXPORT / "companion_browser_listening_meter_pack.h",
}
TEXT_SUFFIXES = {".c", ".h", ".html", ".json", ".mjs", ".py", ".ps1"}


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def canonical_text(value: bytes) -> bytes:
    return value.decode("utf-8").replace("\r\n", "\n").encode("utf-8")


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=check,
        capture_output=True,
    )


def load_documents() -> dict[str, Any]:
    return {
        name: json.loads((ROOT / path).read_text(encoding="utf-8"))
        for name, path in DOCUMENT_PATHS.items()
    }


def semantic_checks(
    documents: dict[str, Any],
    page_text: str,
) -> dict[str, bool]:
    focused = documents["focused"]
    replay = documents["replay"]
    pixel = documents["pixel"]
    screenshots = documents["screenshots"]
    parity = documents["parity"]
    manifest = documents["manifest"]
    idle = focused.get("observed", {}).get("idle", {})
    runs = idle.get("runs", [])
    meter_rows = focused.get("observed", {}).get("meter", {}).get("rows", [])
    hold = focused.get("observed", {}).get("hold", {})
    hold_rows = hold.get("rows", [])
    full_hold = hold.get("full_hold", {})
    recording = focused.get("observed", {}).get("recording", {})
    embedded = manifest.get("source", {}).get("embedded_manifest", {})
    render_contract = embedded.get("rendering", {})
    screenshot_rows = screenshots.get("screenshots", [])
    normalized_runs = [
        [
            {
                key: row.get(key)
                for key in (
                    "changed",
                    "cycle",
                    "key",
                    "previous_key",
                    "refresh_requested",
                    "source",
                    "step",
                )
            }
            for row in run
        ]
        for run in runs
    ]
    checks = {
        "focused_all_checks_true": (
            focused.get("status") == "PASS"
            and focused.get("failed") == []
            and bool(focused.get("checks"))
            and all(focused["checks"].values())
        ),
        "idle_real_clock_60x2_deterministic": (
            len(runs) == 2
            and all(len(run) == 60 for run in runs)
            and normalized_runs[0] == normalized_runs[1]
            and len(set(idle.get("run_sha256", []))) == 1
            and len(idle.get("run_sha256", [])) == 2
        ),
        "idle_scheduler_live_and_bounded": (
            idle.get("cadence_ms") == 480
            and idle.get("first_changed_within_960ms") is True
            and all(
                any(row.get("changed") for row in run)
                and all(row.get("source") == "scheduler" for row in run)
                for run in runs
            )
        ),
        "idle_returns_to_baseline_and_repeats": (
            all(
                any(
                    row.get("step") == 3
                    and row.get("key") == "1,0,1,0"
                    for row in run
                )
                and sum(row.get("step") == 1 for row in run) >= 5
                for run in runs
            )
        ),
        "hold_progress_absent_all_paths": (
            embedded.get("recording_accessory") is not None
            and all(row.get("nodes") == 0 for row in hold_rows)
            and full_hold.get("progress_nodes") == 0
            and ".hold-progress" not in page_text
            and "hold-track" not in page_text
            and "hold-fill" not in page_text
        ),
        "hold_3000_direct_menu_once": (
            hold.get("menu_hold_ms") == 3000
            and full_hold.get("mode") == "menu"
            and full_hold.get("menu_entries") == 1
        ),
        "meter_three_equal_discrete_columns": (
            len(meter_rows) == 8
            and all(
                row.get("column_count") == 3
                and row.get("gray_pixels") == 0
                and {
                    column.get("geometry", {}).get("width")
                    for column in row.get("columns", [])
                }
                == {4}
                for row in meter_rows
            )
        ),
        "meter_shift_inward_outer_insert": (
            all(
                row["samples"][0] == meter_rows[index]["samples"][1]
                and row["samples"][1] == meter_rows[index]["samples"][2]
                and row["transition"]["inserted"]["slot"] == 2
                and [
                    (item["from"], item["to"])
                    for item in row["transition"]["shifted"]
                ]
                == [(1, 0), (2, 1)]
                for index, row in enumerate(meter_rows[1:])
            )
        ),
        "no_arc_or_legacy_renderer": (
            focused["checks"].get("no_arc_pixels") is True
            and focused["checks"].get("no_legacy_recording_renderer") is True
            and "recording-waves" not in page_text
            and "drawBinaryWaveFront" not in page_text
            and "recordingWaveContract" not in page_text
        ),
        "recording_accessory_orthogonal_exit_only": (
            focused["checks"].get("accessory_does_not_replace_affect") is True
            and focused["checks"].get("accessory_does_not_replace_gaze") is True
            and focused["checks"].get("accessory_only_exit") is True
            and recording.get("entered", {}).get("orthogonal_to_expression")
            is True
            and recording.get("exited", {}).get("accessory_active") is False
        ),
        "committed_480ms_no_intermediate": (
            embedded.get("cadence_ms") == 480
            and render_contract.get("committed_frames_only") is True
            and render_contract.get("css_interpolation") == "none"
            and render_contract.get("opacity_tween") is False
            and render_contract.get("subpixel_motion") is False
            and focused["checks"].get("no_browser_interpolation") is True
        ),
        "replay_6x7_42_pass": (
            replay.get("status") == "PASS"
            and replay.get("counts", {}).get("combinations") == 6
            and replay.get("counts", {}).get("scenarios") == 42
            and replay.get("failed") == []
            and all(replay.get("checks", {}).values())
        ),
        "replay_zero_mic_404_and_side_effects": (
            replay.get("counts", {}).get("microphone_requests") == 0
            and replay.get("counts", {}).get("errors") == 0
            and replay.get("side_effects")
            == {
                "hardware": 0,
                "owner_prompt": 0,
                "production_write": 0,
            }
        ),
        "pixel_dom_route_pass": (
            pixel.get("status") == "PASS"
            and pixel.get("scenario_count") == 42
            and all(pixel.get("invariants", {}).values())
        ),
        "screenshots_12_exact": (
            screenshots.get("status") == "PASS"
            and screenshots.get("count") == 12
            and len(screenshot_rows) == 12
            and len({row.get("path") for row in screenshot_rows}) == 12
            and all(
                (ROOT / row["path"]).is_file()
                and sha256((ROOT / row["path"]).read_bytes())
                == row.get("sha256")
                for row in screenshot_rows
            )
        ),
        "parity_independently_passes": (
            parity.get("status") == "PASS"
            and parity.get("failed") == []
            and all(parity.get("checks", {}).values())
            and parity.get("observed", {}).get("state_count") == 82
            and parity.get("observed", {}).get("pbm_reconstructed") == 82
            and parity.get("observed", {}).get("meter_state_count") == 17
        ),
        "manifest_82_states_59_unique": (
            manifest.get("status") == "PASS"
            and manifest.get("invariants", {}).get("state_count") == 82
            and manifest.get("invariants", {}).get("unique_frame_count") == 59
            and manifest.get("invariants", {}).get("meter_state_count") == 8
            and manifest.get("invariants", {}).get(
                "browser_to_c_pixel_diff"
            )
            == 0
        ),
        "one_bit_identity_orientation": (
            manifest.get("format", {}).get("width") == 200
            and manifest.get("format", {}).get("height") == 200
            and manifest.get("format", {}).get("bits_per_pixel") == 1
            and manifest.get("format", {}).get("black_bit") == 1
            and manifest.get("format", {}).get("white_bit") == 0
            and manifest.get("format", {}).get("orientation", {}).get(
                "device_transform"
            )
            == "identity"
            and all(
                state.get("pixel_diff_after_registered_transform") == 0
                and state.get("gray_input_pixels") == 0
                for state in manifest.get("states", [])
            )
        ),
    }
    return checks


def committed_identity(
    source_commit: str,
    identity: str,
    path: Path,
) -> tuple[dict[str, Any], bool]:
    repo_path = path.as_posix()
    current_path = ROOT / path
    if not current_path.is_file():
        return {"id": identity, "path": repo_path, "missing": True}, False
    blob_result = git("rev-parse", f"{source_commit}:{repo_path}", check=False)
    if blob_result.returncode != 0:
        return {"id": identity, "path": repo_path, "missing_at_commit": True}, False
    blob = blob_result.stdout.strip().decode("ascii")
    committed = git("cat-file", "blob", blob).stdout
    current = current_path.read_bytes()
    is_text = path.suffix.lower() in TEXT_SUFFIXES
    committed_value = canonical_text(committed) if is_text else committed
    current_value = canonical_text(current) if is_text else current
    row = {
        "canonical_lf": is_text,
        "git_blob": blob,
        "id": identity,
        "path": repo_path,
        "sha256": sha256(committed_value),
    }
    return row, current_value == committed_value


def source_identity_checks(
    source_commit: str,
    documents: dict[str, Any],
) -> tuple[dict[str, bool], list[dict[str, Any]]]:
    commit_shape = bool(re.fullmatch(r"[0-9a-f]{40}", source_commit))
    commit_exists = (
        commit_shape
        and git("cat-file", "-e", f"{source_commit}^{{commit}}", check=False)
        .returncode
        == 0
    )
    ancestor = (
        commit_exists
        and git("merge-base", "--is-ancestor", source_commit, "HEAD", check=False)
        .returncode
        == 0
    )
    paths = {
        **SOURCE_PATHS,
        **DOCUMENT_PATHS,
        **PACK_PATHS,
    }
    for index, row in enumerate(
        documents.get("screenshots", {}).get("screenshots", [])
    ):
        paths[f"screenshot_{index:02d}"] = Path(row["path"])
    identities = []
    content_matches = []
    if commit_exists:
        for identity, path in paths.items():
            row, passed = committed_identity(source_commit, identity, path)
            identities.append(row)
            content_matches.append(passed)
    checks = {
        "source_commit_exact_40_hex": commit_shape,
        "source_commit_exists": commit_exists,
        "source_commit_is_head_ancestor": ancestor,
        "all_bound_paths_committed": (
            commit_exists and len(identities) == len(paths)
        ),
        "worktree_content_matches_git_blobs": (
            bool(content_matches) and all(content_matches)
        ),
    }
    return checks, identities


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = (ROOT / args.output).resolve()
    output_path.relative_to(ROOT)
    documents = load_documents()
    page_text = (ROOT / PAGE).read_text(encoding="utf-8")
    checks = semantic_checks(documents, page_text)
    identity_checks, identities = source_identity_checks(
        args.source_commit,
        documents,
    )
    checks.update(identity_checks)
    failed = sorted(name for name, passed in checks.items() if not passed)
    result = {
        "schema": "companion.comp-req-539-source-bound-machine-ready.v1",
        "status": "MACHINE_READY" if not failed else "NO_GO",
        "requirements": ["COMP-REQ-539"],
        "source_commit": args.source_commit,
        "checks": checks,
        "failed_checks": failed,
        "identities": identities,
        "owner_gate": "PENDING",
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
        "failed": failed,
        "output": output_path.relative_to(ROOT).as_posix(),
        "sha256": sha256(output),
        "status": result["status"],
    }, sort_keys=True))
    return 0 if result["status"] == "MACHINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
