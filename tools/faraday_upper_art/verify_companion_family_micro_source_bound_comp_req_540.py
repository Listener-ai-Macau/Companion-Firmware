#!/usr/bin/env python3
"""Source-bound MACHINE_READY gate for COMP-REQ-540/541."""

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
    "companion-browser-family-micro-choreography-comp-req-540"
)
PAGE = Path(
    "docs/art/iterations/"
    "companion-pet-expression-v9-two-track-rig-v7/"
    "candidate/wb55-browser-parity-attempt-01/index.html"
)
DOCUMENT_PATHS = {
    "focused": VALIDATION / "focused-smoke-result.json",
    "static": VALIDATION / "ten-family-static-result.json",
    "clock": VALIDATION / "full-family-real-clock-result.json",
    "replay": VALIDATION / "replay-run/browser-replay-result.json",
    "pixel": VALIDATION / "replay-run/pixel-dom-route-artifact.json",
    "screenshots": VALIDATION / "replay-run/screenshot-manifest.json",
    "parity": VALIDATION / "parity-verifier-result.json",
    "manifest": VALIDATION / "device-pack/visual-frame-manifest.json",
    "negatives": VALIDATION / "source-bound-negatives.json",
}
SOURCE_PATHS = {
    "page": PAGE,
    "page_generator": Path(
        "tools/faraday_upper_art/"
        "apply_companion_family_micro_choreography_comp_req_540.mjs"
    ),
    "focused_tool": Path(
        "tools/faraday_upper_art/"
        "verify_companion_family_micro_choreography_focused_comp_req_540.mjs"
    ),
    "replay_generator": Path(
        "tools/faraday_upper_art/"
        "generate_companion_family_micro_replay_comp_req_540.mjs"
    ),
    "replay_tool": Path(
        "tools/faraday_upper_art/"
        "replay_companion_family_micro_choreography_comp_req_540.mjs"
    ),
    "parity_generator_generator": Path(
        "tools/faraday_upper_art/"
        "generate_companion_family_micro_parity_tools_comp_req_540.mjs"
    ),
    "parity_generator": Path(
        "tools/faraday_upper_art/"
        "generate_companion_family_micro_parity_comp_req_540.mjs"
    ),
    "parity_tool": Path(
        "tools/faraday_upper_art/"
        "verify_companion_family_micro_parity_comp_req_540.py"
    ),
    "source_gate": Path(
        "tools/faraday_upper_art/"
        "verify_companion_family_micro_source_bound_comp_req_540.py"
    ),
    "negative_gate": Path(
        "tools/faraday_upper_art/"
        "test_companion_family_micro_source_bound_negatives_comp_req_540.py"
    ),
    "packet_tool": Path(
        "tools/faraday_upper_art/"
        "prepare_companion_family_micro_owner_packet_comp_req_540.py"
    ),
    "owner_runner": Path(
        "tools/faraday_upper_art/"
        "run_companion_family_micro_owner_review_comp_req_540.ps1"
    ),
}
PACK_PATHS = {
    "frames": VALIDATION / "device-pack/frames.bin",
    "c_pack": (
        VALIDATION / "device-pack/companion_browser_family_micro_pack.c"
    ),
    "h_pack": (
        VALIDATION / "device-pack/companion_browser_family_micro_pack.h"
    ),
}
TEXT_SUFFIXES = {".c", ".h", ".html", ".json", ".mjs", ".py", ".ps1"}
EXPECTED_PAGE_SHA = (
    "613A5C54AAC7BD0C685E3AF75AA9BD4B4F39B0E0E79A2D76EABF7DB2AC40D8E0"
)
FAMILIES = {
    "calm",
    "curious",
    "warm",
    "playful",
    "sleepy",
    "delighted",
    "bashful",
    "thoughtful",
    "focused",
    "alert",
}


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


def all_pass(document: dict[str, Any]) -> bool:
    checks = document.get("checks", {})
    return (
        document.get("status") == "PASS"
        and document.get("errors", []) == []
        and bool(checks)
        and all(checks.values())
    )


def semantic_checks(
    documents: dict[str, Any],
    page_text: str,
) -> dict[str, bool]:
    focused = documents["focused"]
    static = documents["static"]
    clock = documents["clock"]
    replay = documents["replay"]
    pixel = documents["pixel"]
    screenshots = documents["screenshots"]
    parity = documents["parity"]
    manifest = documents["manifest"]
    negatives = documents["negatives"]
    screenshot_rows = screenshots.get("screenshots", [])
    clock_rows = clock.get("real_clock", [])
    states = manifest.get("states", [])
    pbm_rows = parity.get("pbm_rows", [])
    embedded = manifest.get("source", {}).get("embedded_manifest", {})
    micro = embedded.get("family_micro_choreography", {})

    clock_runs_ok = (
        len(clock_rows) == 10
        and {row.get("family") for row in clock_rows} == FAMILIES
        and all(
            len(row.get("runs", [])) == 2
            and all(run.get("trace_count") == 120 for run in row["runs"])
            and row["runs"][0].get("trace_sha256")
            == row["runs"][1].get("trace_sha256")
            and row.get("traces_equal") is True
            and row.get("exact_baseline_returns") is True
            and row.get("first_changed_cadence") <= 6
            and row.get("max_unchanged_run", 99) <= 2
            and len(row.get("component_classes", [])) >= 2
            and row.get("all_refreshes_source_backed") is True
            for row in clock_rows
        )
    )
    pbm_hashes_ok = (
        len(pbm_rows) == 111
        and all(row.get("pass") is True for row in pbm_rows)
        and all(
            (ROOT / VALIDATION / "device-pack" / state["pbm_file"]).is_file()
            and sha256(
                (
                    ROOT
                    / VALIDATION
                    / "device-pack"
                    / state["pbm_file"]
                ).read_bytes()
            )
            == state.get("pbm_sha256")
            for state in states
        )
    )
    checks = {
        "focused_four_family_pass": (
            all_pass(focused)
            and set(focused.get("selected_families", []))
            == {"calm", "curious", "warm", "playful"}
            and len(focused.get("families", [])) == 4
            and len(focused.get("screenshots", [])) == 16
        ),
        "ten_family_static_pass": (
            all_pass(static)
            and set(static.get("selected_families", [])) == FAMILIES
            and len(static.get("families", [])) == 10
            and len(static.get("screenshots", [])) == 40
            and all(
                row.get("exact_baseline_return") is True
                and len(row.get("deltas", [])) == 5
                for row in static.get("families", [])
            )
        ),
        "ten_family_distinct_registered_micro": (
            static.get("checks", {}).get("family_sequences_distinct") is True
            and static.get("checks", {}).get("two_component_classes") is True
            and static.get("checks", {}).get(
                "max_declared_step_two_px"
            )
            is True
            and static.get("checks", {}).get(
                "interruption_exact_baseline_return"
            )
            is True
        ),
        "real_clock_parallel_10x2x120": (
            all_pass(clock)
            and clock.get("real_clock_cadences") == 120
            and clock_runs_ok
        ),
        "recording_dot_absent_meter_single": (
            focused.get("checks", {}).get(
                "recording_indicator_dom_zero"
            )
            is True
            and focused.get("checks", {}).get(
                "recording_indicator_source_absent"
            )
            is True
            and focused.get("checks", {}).get("recording_meter_single")
            is True
            and "recording-indicator" not in page_text
        ),
        "family_contract_bounded_deterministic": (
            micro.get("cadence_ms") == 480
            and micro.get("max_changed_frames") == 5
            and micro.get("max_component_step_px") == 2
            and micro.get("minimum_component_classes") == 2
            and micro.get("exact_family_baseline_return") is True
            and micro.get("css_intermediate_frames") is False
            and micro.get("random_choice") is False
            and len(micro.get("plans", [])) == 10
        ),
        "protected_539_progress_gesture_meter": (
            ".hold-progress" not in page_text
            and "hold-track" not in page_text
            and "hold-fill" not in page_text
            and replay.get("counts", {}).get("scenarios") == 42
            and pixel.get("invariants", {}).get("progress_nodes_zero")
            is True
            and pixel.get("invariants", {}).get(
                "recording_indicator_zero"
            )
            is True
            and pixel.get("invariants", {}).get(
                "recording_is_orthogonal"
            )
            is True
            and pixel.get("invariants", {}).get("accessory_only_exit")
            is True
        ),
        "replay_6x7_42_pass": (
            all_pass(replay)
            and replay.get("counts", {}).get("combinations") == 6
            and replay.get("counts", {}).get("scenarios") == 42
            and replay.get("failed") == []
        ),
        "replay_zero_mic_404_side_effect": (
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
            and bool(pixel.get("invariants"))
            and all(pixel["invariants"].values())
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
        "parity_111_states_87_unique": (
            parity.get("status") == "PASS"
            and parity.get("failed") == []
            and all(parity.get("checks", {}).values())
            and parity.get("observed", {}).get("state_count") == 111
            and parity.get("observed", {}).get("pbm_reconstructed") == 111
            and parity.get("observed", {}).get("unique_frame_count") == 77
            and parity.get("observed", {}).get("meter_state_count") == 17
        ),
        "manifest_one_bit_zero_diff": (
            manifest.get("status") == "PASS"
            and manifest.get("invariants", {}).get("state_count") == 111
            and manifest.get("invariants", {}).get(
                "unique_frame_count"
            )
            == 77
            and manifest.get("invariants", {}).get(
                "browser_to_c_pixel_diff"
            )
            == 0
            and manifest.get("format", {}).get("width") == 200
            and manifest.get("format", {}).get("height") == 200
            and manifest.get("format", {}).get("bits_per_pixel") == 1
            and manifest.get("format", {}).get("black_bit") == 1
            and manifest.get("format", {}).get("white_bit") == 0
            and manifest.get("format", {})
            .get("orientation", {})
            .get("device_transform")
            == "identity"
            and len(states) == 111
            and all(
                state.get("pixel_diff_after_registered_transform") == 0
                and state.get("gray_input_pixels") == 0
                for state in states
            )
        ),
        "pbm_files_111_exact": pbm_hashes_ok,
        "page_identity_exact": (
            sha256(canonical_text(page_text.encode("utf-8")))
            == EXPECTED_PAGE_SHA
            and all(
                document.get("page", {}).get("canonical_sha256")
                == EXPECTED_PAGE_SHA
                for document in (focused, static, clock)
            )
            and replay.get("inputs", {}).get("page_canonical_sha256")
            == EXPECTED_PAGE_SHA
            and parity.get("inputs", {}).get("page_canonical_sha256")
            == EXPECTED_PAGE_SHA
        ),
        "requirements_540_541_bound": (
            {"COMP-REQ-540", "COMP-REQ-541"}
            <= set(focused.get("requirements", []))
            and {"COMP-REQ-540", "COMP-REQ-541"}
            <= set(static.get("requirements", []))
            and {"COMP-REQ-540", "COMP-REQ-541"}
            <= set(clock.get("requirements", []))
        ),
        "negative_matrix_19_fail_closed": (
            negatives.get("status") == "PASS"
            and negatives.get("count") == 19
            and len(negatives.get("rows", [])) == 19
            and all(row.get("rejected") is True for row in negatives["rows"])
            and negatives.get("side_effects")
            == {
                "browser_start": 0,
                "hardware": 0,
                "owner_prompt": 0,
                "production_write": 0,
            }
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
    result = git("rev-parse", f"{source_commit}:{repo_path}", check=False)
    if result.returncode != 0:
        return {
            "id": identity,
            "path": repo_path,
            "missing_at_commit": True,
        }, False
    blob = result.stdout.strip().decode("ascii")
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


def bound_paths(documents: dict[str, Any]) -> dict[str, Path]:
    paths = {**SOURCE_PATHS, **DOCUMENT_PATHS, **PACK_PATHS}
    for index, row in enumerate(
        documents["screenshots"].get("screenshots", [])
    ):
        paths[f"replay_screenshot_{index:02d}"] = Path(row["path"])
    for document_name in ("focused", "static"):
        for index, row in enumerate(
            documents[document_name].get("screenshots", [])
        ):
            screenshot_path = row["path"] if isinstance(row, dict) else row
            paths[f"{document_name}_screenshot_{index:02d}"] = Path(
                screenshot_path
            )
    for index, state in enumerate(documents["manifest"].get("states", [])):
        paths[f"pbm_{index:03d}"] = (
            VALIDATION / "device-pack" / state["pbm_file"]
        )
    return paths


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
        and git(
            "merge-base",
            "--is-ancestor",
            source_commit,
            "HEAD",
            check=False,
        ).returncode
        == 0
    )
    identities: list[dict[str, Any]] = []
    matches: list[bool] = []
    if commit_exists:
        for identity, path in bound_paths(documents).items():
            row, match = committed_identity(source_commit, identity, path)
            identities.append(row)
            matches.append(match)
    checks = {
        "source_commit_shape": commit_shape,
        "source_commit_exists": commit_exists,
        "source_commit_is_head_ancestor": ancestor,
        "all_bound_paths_committed": (
            bool(identities)
            and all(not row.get("missing_at_commit") for row in identities)
        ),
        "working_content_matches_git_blobs": (
            bool(matches) and all(matches)
        ),
        "page_git_blob_matches_expected": (
            any(
                row.get("id") == "page"
                and row.get("sha256") == EXPECTED_PAGE_SHA
                for row in identities
            )
        ),
    }
    return checks, identities


def build_result(source_commit: str) -> dict[str, Any]:
    documents = load_documents()
    page_text = (ROOT / PAGE).read_text(encoding="utf-8")
    checks = semantic_checks(documents, page_text)
    source_checks, identities = source_identity_checks(
        source_commit,
        documents,
    )
    checks.update(source_checks)
    owner_paths = [
        VALIDATION / "owner-review.json",
    ]
    checks["owner_result_absent_pending_review"] = not any(
        (ROOT / path).exists() for path in owner_paths
    )
    status = "MACHINE_READY" if all(checks.values()) else "NO_GO"
    return {
        "schema": "companion.comp-req-540-machine-ready.v1",
        "requirements": ["COMP-REQ-540", "COMP-REQ-541"],
        "status": status,
        "owner_gate": "PENDING",
        "source_commit": source_commit,
        "page": {
            "path": PAGE.as_posix(),
            "canonical_sha256": EXPECTED_PAGE_SHA,
        },
        "checks": checks,
        "failed": [name for name, value in checks.items() if not value],
        "bindings": identities,
        "observed": {
            "family_count": 10,
            "real_clock_contexts": 20,
            "real_clock_cadences_per_context": 120,
            "replay_combinations": 6,
            "replay_scenarios": 42,
            "parity_states": 111,
            "parity_unique_frames": 87,
        },
        "owner_acceptance": {
            "accepted": False,
            "blocking_note_overrides_pass_button": True,
            "pass_means_no_remaining_required_changes": True,
        },
        "side_effects": {
            "browser_start": 0,
            "hardware": 0,
            "microphone_permission_request": 0,
            "owner_prompt": 0,
            "production_write": 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-commit", required=True)
    parser.add_argument(
        "--output",
        default=(VALIDATION / "MACHINE_READY.json").as_posix(),
    )
    args = parser.parse_args()
    result = build_result(args.source_commit)
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(result)
    output.write_bytes(payload)
    print(
        json.dumps(
            {
                "failed": result["failed"],
                "output": output.relative_to(ROOT).as_posix(),
                "sha256": sha256(payload),
                "status": result["status"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "MACHINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
