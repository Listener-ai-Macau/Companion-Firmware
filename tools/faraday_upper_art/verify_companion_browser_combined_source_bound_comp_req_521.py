#!/usr/bin/env python3
"""Fail-closed source/artifact gate for the COMP-REQ-518/520/521 successor."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


SOURCE_COMMIT = "119c0b8c873d7817c64edec31391b393e00b09ac"
TOOL_COMMIT = "a9753faab76048f3a350292cb61cbbff762ae32c"
PAGE_PATH = (
    "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/"
    "candidate/wb55-browser-parity-attempt-01/index.html"
)
PAGE_SHA256 = "24B5720F14B6793B201C4E74AD8BDB2219EE4F8CC941454983876979DA9ADAB1"
URL = (
    "http://127.0.0.1:4173/"
    + PAGE_PATH
)
VALIDATION_DIR = (
    "docs/validation/"
    "companion-browser-natural-expression-successor-comp-req-518-520-521"
)
OWNER_RESULT_PATH = f"{VALIDATION_DIR}/owner-review.json"

BOUND_FILES: dict[str, tuple[str, str, str | None]] = {
    "page": (PAGE_PATH, PAGE_SHA256, SOURCE_COMMIT),
    "natural_oracle_tool": (
        "tools/faraday_upper_art/"
        "verify_companion_browser_natural_expression_comp_req_521.mjs",
        "3E3ACBD6861D98ABC3665D39C62A6CF36FA8CC14809785F62982653B7A30C9A0",
        SOURCE_COMMIT,
    ),
    "replay_tool": (
        "tools/faraday_upper_art/"
        "replay_companion_browser_natural_expression_successor_comp_req_521.mjs",
        "3BF371C0684328D9B2259BE4420EC0329DEFC3C4B6B58251BAC0D0ADC2923AA7",
        TOOL_COMMIT,
    ),
    "determinism_tool": (
        "tools/faraday_upper_art/"
        "run_companion_browser_clean_replay_determinism_comp_req_521.py",
        "FB20136C3D424DA3C6719B1AB92BF6D411DAC3E4F981A390D5922C42CACC34D4",
        TOOL_COMMIT,
    ),
    "recording_temporal_tool": (
        "tools/faraday_upper_art/"
        "verify_companion_browser_recording_temporal_comp_req_518.mjs",
        "323571F845565038C33E10CD3EBE8E7D4B2398531088C9F8681109F5E24A9D6A",
        None,
    ),
    "research_contract": (
        "docs/validation/"
        "companion-natural-expression-transition-research-20260724.md",
        "6B81FE75B19082F0CC93078003CD16E8F0ED1AA231EBE47EB54083CDBAA66788",
        None,
    ),
    "v22_component_bridge": (
        "docs/art/iterations/"
        "companion-pet-expression-v9-extension-v22-emotion-separation-source/"
        "candidate/component-bridge-attempt-01/component-bridge-layout.json",
        "081967DF89E20790148052E518ADD69244C63D47F4BD07B862F6DAA84631C846",
        None,
    ),
    "r7_transition_graph": (
        "docs/art/iterations/"
        "companion-pet-expression-v9-two-track-rig-v7/"
        "r7-locked-v9-export-20260723/r7-transition-graph.json",
        "380F7D72450ACA7EC26D4694B0CC1AD18C66F51260DC7C30E5B1E4272CD55524",
        None,
    ),
    "v9_state_grammar": (
        "docs/art/iterations/"
        "companion-pet-expression-v9-emotion-decoration-kit-v1/"
        "state-grammar-v1.json",
        "2C111532CCB6C85AFD1A8AF16320BFCA3BCC02B7F765D85366FF2149EB277714",
        None,
    ),
    "replay_result": (
        f"{VALIDATION_DIR}/determinism-run/browser-replay-result.json",
        "50027010EC4923ADD5B73B71F56DFBEA48DF0268427955F34D48C1B368913B37",
        None,
    ),
    "pixel_dom_route": (
        f"{VALIDATION_DIR}/determinism-run/pixel-dom-route-artifact.json",
        "1688A1FF837A9F771E6950967F5891F5922D432180392863CAA431EAC8116382",
        None,
    ),
    "screenshot_manifest": (
        f"{VALIDATION_DIR}/determinism-run/screenshot-manifest.json",
        "4E577A7C4E65A5C349B88C887CC59BE7446B10B62EC06CE255D4F17BF5500651",
        None,
    ),
    "determinism_receipt": (
        f"{VALIDATION_DIR}/deterministic-replay-receipt.json",
        "FC290AAFB6CEB203F885B81992DE63895AD026A8F0B2BC6FCA6B6B41FF383330",
        None,
    ),
    "focused_recording": (
        f"{VALIDATION_DIR}/focused-recording-temporal.json",
        "60EF928EE104035F1DE7756A0600A499A6B9A84D28869BDB8AB9A1A1290C526E",
        None,
    ),
    "focused_natural": (
        f"{VALIDATION_DIR}/focused-natural-expression.json",
        "93A1D3BF6D701A74007CCE5E5F9C1556630D3AAA7BCD5DD16C63718593BD5A4A",
        None,
    ),
    "before_stale_pupil": (
        "docs/validation/"
        "companion-browser-owner-review-ready-comp-req-508/"
        "before-fix/stale-gaze-oracle.json",
        "3FC9D52C81ACB643A93F90FB5CABC66B6466DC6F6BE298C389F831A0512565A4",
        None,
    ),
    "before_recording": (
        "docs/validation/"
        "companion-browser-recording-successor-comp-req-518/"
        "before-fix/recording-temporal-oracle.json",
        "EEC0C1BBF97C25BF69111F75F3652B8A767576C4546EB8D73520EC415A0192D9",
        None,
    ),
    "failed_owner_result": (
        "docs/validation/"
        "companion-browser-owner-review-ready-comp-req-508/owner-review.json",
        "912890518A8C758B915F3DD674372FEBB642EF89996DACF9B1E06A587C519979",
        None,
    ),
    "failed_owner_raw": (
        "docs/validation/"
        "companion-browser-owner-review-ready-comp-req-508/"
        "owner-review.raw.json",
        "50C3563002CF4E81E84EA2344AEE1919D29A4F3854E663966451D602E6CF2DB3",
        None,
    ),
    "failed_owner_note": (
        "docs/validation/"
        "companion-browser-owner-review-ready-comp-req-508/"
        "owner-review.note.txt",
        "7EB70257593DA06F682A3DDDA54A9D260D4FC514F645237F5CA74B08F8DA61A6",
        None,
    ),
}

EXPECTED_TOTALS = {
    "browser_contexts": 44,
    "browser_pages": 44,
    "cancellation_scenarios": 18,
    "conflicting_surface_overlap_count": 0,
    "device_ui_assets_visits": 6,
    "directional_moves": 30,
    "document_requests": 44,
    "http_404_count": 0,
    "menu_root_visits": 24,
    "mic_glyph_pixel_count": 0,
    "microphone_requests": 0,
    "natural_bridge_commits": 6,
    "natural_bridge_ordered": 6,
    "out_of_bounds_count": 0,
    "outside_black_pixel_count": 0,
    "page_error_count": 0,
    "recording_negative_checks": 54,
    "recording_ordered_phase_traces": 12,
    "recording_reentries": 6,
    "recording_wave_cycles": 6,
    "replay_combinations": 6,
    "route_menu_entries": 6,
    "route_recording_entries": 12,
    "route_recording_exits": 12,
    "scenario_count": 42,
    "snapshot_count": 258,
    "stale_layer_count": 0,
    "stale_pupil_pixel_count": 0,
    "stale_pupil_state_count": 0,
}
SCENARIOS = (
    "blur",
    "drag",
    "early-up",
    "hold-menu-return",
    "pointercancel",
    "recording-return",
    "single-tap",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")


def read_bytes(
    repo_root: Path,
    relative_path: str,
    overlay: dict[str, bytes] | None,
) -> bytes:
    normalized = relative_path.replace("\\", "/")
    if overlay is not None and normalized in overlay:
        return overlay[normalized]
    return (repo_root / normalized).read_bytes()


def parse_json(
    label: str,
    data: bytes,
    failures: list[str],
) -> dict[str, Any] | None:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        failures.append(f"{label}: invalid JSON ({exc.__class__.__name__})")
        return None
    if not isinstance(value, dict):
        failures.append(f"{label}: root must be object")
        return None
    return value


def git_text(repo_root: Path, *args: str) -> str | None:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def require(
    failures: list[str],
    label: str,
    observed: Any,
    expected: Any,
) -> None:
    if observed != expected:
        failures.append(
            f"{label}: expected {expected!r}, observed {observed!r}"
        )


def expected_matrix_ids() -> set[str]:
    return {
        f"{viewport}-{pointer_type}-{scenario}"
        for viewport in ("desktop", "mobile")
        for pointer_type in ("mouse", "touch", "pen")
        for scenario in SCENARIOS
    }


def validate_replay(
    replay: dict[str, Any] | None,
    failures: list[str],
) -> None:
    if replay is None:
        return
    require(
        failures,
        "replay status",
        replay.get("status"),
        "PASS_BROWSER_NATURAL_EXPRESSION_MACHINE_REPLAY",
    )
    page = replay.get("page", {})
    require(failures, "replay page", page.get("observed_sha256"), PAGE_SHA256)
    require(failures, "replay URL", page.get("runtime_url"), URL)
    require(failures, "replay totals", replay.get("totals"), EXPECTED_TOTALS)
    require(
        failures,
        "replay requirement",
        "COMP-REQ-521" in replay.get("requirements", []),
        True,
    )
    counters = replay.get("side_effect_counters", {})
    for key in (
        "hardware",
        "lower_write",
        "microphone_permission_requests",
        "owner_prompt",
        "owner_result_write",
        "platform_write",
        "production_write",
        "registry_write",
        "server_start",
    ):
        require(failures, f"replay side effect {key}", counters.get(key), 0)


def validate_pixel(
    pixel: dict[str, Any] | None,
    failures: list[str],
) -> None:
    if pixel is None:
        return
    require(failures, "pixel status", pixel.get("status"), "PASS")
    matrix = pixel.get("matrix", [])
    matrix_ids = [row.get("id") for row in matrix if isinstance(row, dict)]
    require(failures, "matrix count", len(matrix_ids), 42)
    require(
        failures,
        "matrix IDs",
        sorted(matrix_ids),
        sorted(expected_matrix_ids()),
    )
    require(failures, "matrix IDs unique", len(set(matrix_ids)), 42)
    if any(row.get("status") != "PASS" for row in matrix):
        failures.append("matrix contains non-PASS row")
    invariants = pixel.get("invariants", {})
    for key in (
        "conflicting_surface_overlap_count",
        "debug_visible_count",
        "http_404_count",
        "microphone_glyph_pixel_count",
        "microphone_request_count",
        "out_of_bounds_count",
        "outside_black_pixel_count",
        "stale_layer_count",
        "stale_pupil_pixel_count",
        "stale_pupil_state_count",
    ):
        require(failures, f"pixel invariant {key}", invariants.get(key), 0)
    require(
        failures,
        "primary screen count",
        invariants.get("primary_screen_count"),
        1,
    )
    states = pixel.get("states", [])
    require(failures, "state count", len(states), 258)
    for index, state in enumerate(states):
        if not isinstance(state, dict):
            failures.append(f"state {index}: not an object")
            continue
        dom = state.get("dom", {})
        pupil = state.get("pupil_oracle", {})
        expected = dom.get("expected", {})
        require(
            failures,
            f"state {index} primary",
            dom.get("primary_screen_count"),
            1,
        )
        require(
            failures,
            f"state {index} conflict",
            dom.get("conflict_count"),
            0,
        )
        require(
            failures,
            f"state {index} debug",
            dom.get("debug_visible"),
            [],
        )
        require(
            failures,
            f"state {index} bounds",
            dom.get("out_of_bounds"),
            [],
        )
        for actual_key, expected_key in (
            ("face_count", "face"),
            ("gaze_count", "gaze"),
            ("highlight_layer_count", "highlight"),
            ("menu_count", "menu"),
            ("recording_indicator_count", "indicator"),
            ("recording_wave_count", "wave"),
        ):
            require(
                failures,
                f"state {index} {actual_key}",
                dom.get(actual_key),
                expected.get(expected_key),
            )
        require(
            failures,
            f"state {index} indicator node",
            dom.get("recording_indicator_node_count"),
            1,
        )
        microphone = state.get("microphone_oracle", {})
        recording = state.get("recording", {})
        require(
            failures,
            f"state {index} microphone asset",
            microphone.get("visible_mic_asset_sources"),
            0,
        )
        require(
            failures,
            f"state {index} microphone mask",
            microphone.get("current_wave_mask_overlap"),
            0,
        )
        require(
            failures,
            f"state {index} microphone glyph",
            recording.get("mic_glyph_present"),
            False,
        )
        if state.get("contract", {}).get("mode") != "menu":
            for key in (
                "binary_mismatch_count",
                "stale_center_mask_left_eye",
                "stale_center_mask_right_eye",
                "stale_center_mask_total",
            ):
                require(
                    failures,
                    f"state {index} pupil {key}",
                    pupil.get(key),
                    0,
                )
    recording_rows = [
        row for row in matrix_ids
        if isinstance(row, str) and row.endswith("-recording-return")
    ]
    single_rows = [
        row for row in matrix_ids
        if isinstance(row, str) and row.endswith("-single-tap")
    ]
    require(failures, "recording matrix rows", len(recording_rows), 6)
    require(failures, "single matrix rows", len(single_rows), 6)
    by_id = {row.get("id"): row for row in matrix if isinstance(row, dict)}
    for row_id in recording_rows:
        result = by_id[row_id].get("result", {})
        require(
            failures,
            f"{row_id} phases",
            result.get("ordered_phases"),
            ["expression", "listening", "listening_hold"],
        )
        require(
            failures,
            f"{row_id} entries",
            result.get("recording_entries"),
            2,
        )
        require(
            failures,
            f"{row_id} exits",
            result.get("recording_exits"),
            2,
        )
        require(
            failures,
            f"{row_id} negatives",
            len(result.get("negative_checks", [])),
            9,
        )
        distances = [
            item.get("distance_to_listening_point")
            for item in result.get("inward_wave_cycle", [])
        ]
        if (
            len(distances) < 4
            or any(value is None for value in distances)
            or any(
                distances[index] >= distances[index - 1]
                for index in range(1, len(distances))
            )
        ):
            failures.append(f"{row_id}: wave is not strictly inward")
    for row_id in single_rows:
        result = by_id[row_id].get("result", {})
        require(
            failures,
            f"{row_id} orient",
            result.get("first_release_orient_only"),
            True,
        )
        require(
            failures,
            f"{row_id} target",
            result.get("natural_target"),
            "curious",
        )
        require(
            failures,
            f"{row_id} order",
            result.get("ordered_route"),
            [
                "contextual_edge_selected",
                "brow_reply",
                "lower_face_reply",
                "target_hold",
            ],
        )


def validate_screenshots(
    repo_root: Path,
    manifest: dict[str, Any] | None,
    overlay: dict[str, bytes] | None,
    failures: list[str],
) -> None:
    if manifest is None:
        return
    require(failures, "screenshot status", manifest.get("status"), "PASS")
    rows = manifest.get("screenshots", [])
    require(failures, "screenshot count", len(rows), 50)
    paths = [row.get("path") for row in rows if isinstance(row, dict)]
    require(failures, "screenshot paths unique", len(set(paths)), 50)
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            failures.append(f"screenshot {index}: not an object")
            continue
        relative_path = row.get("path")
        if not isinstance(relative_path, str):
            failures.append(f"screenshot {index}: missing path")
            continue
        try:
            data = read_bytes(repo_root, relative_path, overlay)
        except OSError:
            failures.append(f"screenshot {index}: missing {relative_path}")
            continue
        require(
            failures,
            f"screenshot {index} SHA",
            sha256_bytes(data),
            row.get("sha256"),
        )
        require(
            failures,
            f"screenshot {index} bytes",
            len(data),
            row.get("bytes"),
        )


def validate_focused(
    natural: dict[str, Any] | None,
    recording: dict[str, Any] | None,
    failures: list[str],
) -> None:
    if natural is not None:
        require(failures, "natural status", natural.get("status"), "PASS")
        require(failures, "natural errors", natural.get("errors"), [])
        require(
            failures,
            "natural page",
            natural.get("page", {}).get("observed_sha256"),
            PAGE_SHA256,
        )
        contract = natural.get("observations", {}).get("contract", {}).get(
            "contract", {}
        )
        expected_contract = {
            "bridgeWindowMs": 480,
            "maxCoalescedPending": 1,
            "maxPostSourceChangedFrames": 3,
            "tapDiscriminatorMs": 650,
        }
        for key, value in expected_contract.items():
            require(failures, f"natural contract {key}", contract.get(key), value)
        require(
            failures,
            "natural priority",
            contract.get("priority"),
            [
                "error",
                "alert",
                "menu",
                "recording",
                "drag",
                "single_tap",
                "ambient",
            ],
        )
        active = natural.get("observations", {}).get("recording", {})
        phases = [
            row.get("phase")
            for row in active.get("recording", {}).get("phaseTrace", [])
            if row.get("sequence")
            == active.get("recording", {}).get("sequence")
        ]
        require(
            failures,
            "natural recording phases",
            phases,
            ["expression", "listening", "listening_hold"],
        )
        if any("thoughtful" in str(value) for value in phases):
            failures.append("natural recording contains thoughtful phase")
        require(
            failures,
            "natural media requests",
            active.get("mediaRequests"),
            0,
        )
    if recording is not None:
        require(failures, "recording status", recording.get("status"), "PASS")
        require(failures, "recording errors", recording.get("errors"), [])
        require(
            failures,
            "recording page",
            recording.get("observed_page_sha256"),
            PAGE_SHA256,
        )
        checks = recording.get("checks", {})
        if not checks or not all(value is True for value in checks.values()):
            failures.append("recording focused checks are not all true")
        observation = recording.get("observation", {})
        require(
            failures,
            "recording phase trace",
            observation.get("phase_trace"),
            ["expression", "listening", "listening_hold", "expression"],
        )
        require(
            failures,
            "recording unique face count",
            len(observation.get("unique_recording_face_sources", [])),
            1,
        )
        require(
            failures,
            "recording unique gaze count",
            len(observation.get("unique_recording_gaze_sources", [])),
            1,
        )
        require(
            failures,
            "recording outward transitions",
            observation.get("outward_transitions"),
            [],
        )
        require(
            failures,
            "recording exact restore",
            observation.get("restore", {}).get("exact"),
            True,
        )


def validate_determinism(
    receipt: dict[str, Any] | None,
    failures: list[str],
) -> None:
    if receipt is None:
        return
    require(
        failures,
        "determinism status",
        receipt.get("status"),
        "PASS_TWO_CLEAN_REPLAYS_BYTE_IDENTICAL",
    )
    require(failures, "determinism count", receipt.get("run_count"), 2)
    require(failures, "determinism equality", receipt.get("byte_identical"), True)
    require(failures, "determinism page", receipt.get("page_sha256"), PAGE_SHA256)
    require(failures, "determinism URL", receipt.get("url"), URL)
    require(
        failures,
        "determinism aggregate",
        receipt.get("run_a", {}).get("aggregate_sha256"),
        receipt.get("run_b", {}).get("aggregate_sha256"),
    )
    require(
        failures,
        "determinism files",
        receipt.get("run_a", {}).get("files"),
        receipt.get("run_b", {}).get("files"),
    )
    counters = receipt.get("side_effect_counters", {})
    for key in (
        "browser_window_open",
        "hardware",
        "lower_write",
        "microphone_permission_request",
        "operator_prompt",
        "platform_write",
        "popup",
        "production_write",
        "registry_write",
        "server_start",
    ):
        require(failures, f"determinism side effect {key}", counters.get(key), 0)


def evaluate(
    repo_root: Path,
    overlay: dict[str, bytes] | None = None,
    source_commit: str = SOURCE_COMMIT,
    tool_commit: str = TOOL_COMMIT,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    failures: list[str] = []
    identities: list[dict[str, Any]] = []
    require(
        failures,
        "source commit object",
        git_text(repo_root, "rev-parse", f"{source_commit}^{{commit}}"),
        source_commit,
    )
    require(
        failures,
        "tool commit object",
        git_text(repo_root, "rev-parse", f"{tool_commit}^{{commit}}"),
        tool_commit,
    )
    for label, (relative_path, expected_sha, commit) in BOUND_FILES.items():
        try:
            data = read_bytes(repo_root, relative_path, overlay)
            observed_sha = sha256_bytes(data)
            exists = True
        except OSError:
            data = b""
            observed_sha = None
            exists = False
        match = observed_sha == expected_sha
        identities.append(
            {
                "bytes": len(data) if exists else None,
                "commit": commit,
                "exists": exists,
                "expected_sha256": expected_sha,
                "label": label,
                "match": match,
                "observed_sha256": observed_sha,
                "path": relative_path,
            }
        )
        require(failures, f"{label} exists", exists, True)
        require(failures, f"{label} SHA", observed_sha, expected_sha)
        if commit is not None:
            expected_blob = git_text(
                repo_root, "rev-parse", f"{commit}:{relative_path}"
            )
            worktree_blob = git_text(
                repo_root,
                "hash-object",
                "--path",
                relative_path,
                relative_path,
            )
            require(
                failures,
                f"{label} committed blob",
                worktree_blob,
                expected_blob,
            )

    parsed: dict[str, dict[str, Any] | None] = {}
    for label in (
        "replay_result",
        "pixel_dom_route",
        "screenshot_manifest",
        "determinism_receipt",
        "focused_recording",
        "focused_natural",
        "before_stale_pupil",
        "before_recording",
        "failed_owner_result",
    ):
        relative_path = BOUND_FILES[label][0]
        try:
            parsed[label] = parse_json(
                label, read_bytes(repo_root, relative_path, overlay), failures
            )
        except OSError:
            parsed[label] = None

    validate_replay(parsed["replay_result"], failures)
    validate_pixel(parsed["pixel_dom_route"], failures)
    validate_screenshots(
        repo_root, parsed["screenshot_manifest"], overlay, failures
    )
    validate_focused(
        parsed["focused_natural"], parsed["focused_recording"], failures
    )
    validate_determinism(parsed["determinism_receipt"], failures)
    before_stale = parsed["before_stale_pupil"]
    before_recording = parsed["before_recording"]
    if before_stale is not None:
        require(
            failures,
            "predecessor stale status",
            before_stale.get("status"),
            "FAIL_STALE_GAZE",
        )
        if before_stale.get("measurement", {}).get(
            "pixel", {}
        ).get("stale_center_mask_total", 0) <= 0:
            failures.append("predecessor stale oracle has no observed stale pixels")
    if before_recording is not None:
        require(
            failures,
            "predecessor recording status",
            before_recording.get("status"),
            "FAIL_RECORDING_TEMPORAL_VISUAL",
        )
        if before_recording.get("observation", {}).get(
            "outward_transitions", []
        ) == []:
            failures.append("predecessor recording oracle has no outward motion")
    owner = parsed["failed_owner_result"]
    if owner is not None:
        require(failures, "protected owner selection", owner.get("selected"), "失败")
    owner_result_exists = (repo_root / OWNER_RESULT_PATH).is_file()
    if overlay is not None and OWNER_RESULT_PATH in overlay:
        owner_result_exists = True
    require(
        failures,
        "successor owner result absent",
        owner_result_exists,
        False,
    )
    return {
        "bound_commits": {
            "source": source_commit,
            "tooling": tool_commit,
        },
        "failed_checks": failures,
        "identities": identities,
        "owner_gate": {
            "owner_result_exists": owner_result_exists,
            "owner_result_path": OWNER_RESULT_PATH,
            "status": "PENDING_OWNER_REVIEW",
        },
        "requirements": [
            "COMP-REQ-508",
            "COMP-REQ-518",
            "COMP-REQ-520",
            "COMP-REQ-521",
        ],
        "schema": "companion.browser-combined-source-bound-machine-ready.v1",
        "side_effect_counters": {
            "browser": 0,
            "hardware": 0,
            "lower_write": 0,
            "microphone_permission_request": 0,
            "owner_prompt": 0,
            "platform_write": 0,
            "production_write": 0,
            "registry_write": 0,
            "server_start": 0,
        },
        "status": "MACHINE_READY" if not failures else "NO_GO",
        "url": URL,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    output = (
        args.output.resolve()
        if args.output.is_absolute()
        else (repo_root / args.output).resolve()
    )
    output.relative_to(repo_root / VALIDATION_DIR)
    result = evaluate(repo_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_bytes(result))
    print(json.dumps({
        "artifact_sha256": sha256_bytes(canonical_bytes(result)),
        "failed_check_count": len(result["failed_checks"]),
        "status": result["status"],
    }, sort_keys=True))
    return 0 if result["status"] == "MACHINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
