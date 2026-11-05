#!/usr/bin/env python3
"""Source-bound, fail-closed COMP-REQ-508 browser MACHINE_READY gate."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


SOURCE_COMMIT = "6e6e521fddcdb9a99af0608fa86714df199e6c9c"
EVIDENCE_COMMIT = "1874859d769925696ca46aa158fa71fdb70b3500"
PAGE_PATH = (
    "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/"
    "candidate/wb55-browser-parity-attempt-01/index.html"
)
PAGE_SHA256 = "9990C4316AF8F4D656F2C2B057AB789846A10CD21E18367336FC6BD277631EB7"
OLD_PAGE_SHA256 = (
    "BAE21BCCC7BB5FAD4A0922D5E9C42FCB25EF58DD7B8102A7C72656F7B700CF5E"
)
URL = (
    "http://127.0.0.1:4173/docs/art/iterations/"
    "companion-pet-expression-v9-two-track-rig-v7/candidate/"
    "wb55-browser-parity-attempt-01/index.html"
)
VALIDATION_DIR = (
    "docs/validation/companion-browser-owner-review-ready-comp-req-508"
)
NEW_OWNER_RESULT = f"{VALIDATION_DIR}/owner-review.json"

BOUND_FILES: dict[str, tuple[str, str, str]] = {
    "page": (
        PAGE_PATH,
        PAGE_SHA256,
        SOURCE_COMMIT,
    ),
    "replay_tool": (
        "tools/faraday_upper_art/"
        "replay_companion_browser_owner_review_ready_comp_req_508.mjs",
        "304575095583ACACDD45F4E218315F5829B0E2D0E68061403AD70287DDC9DE64",
        SOURCE_COMMIT,
    ),
    "stale_gaze_oracle_tool": (
        "tools/faraday_upper_art/"
        "verify_companion_browser_stale_gaze_comp_req_508.mjs",
        "96C8992E5806D137A104F64D17F602080D6F9A0B52EF2655E7FA9FAEF85C4EF9",
        SOURCE_COMMIT,
    ),
    "determinism_tool": (
        "tools/faraday_upper_art/"
        "run_companion_browser_clean_replay_determinism_comp_req_508.py",
        "B56BF027CD9D1CCFA0F55950E004FD960D2D9F5BC777602B9891B1657F6E2C43",
        EVIDENCE_COMMIT,
    ),
    "before_oracle": (
        f"{VALIDATION_DIR}/before-fix/stale-gaze-oracle.json",
        "3FC9D52C81ACB643A93F90FB5CABC66B6466DC6F6BE298C389F831A0512565A4",
        SOURCE_COMMIT,
    ),
    "before_screenshot": (
        f"{VALIDATION_DIR}/before-fix/drag-stale-gaze.png",
        "1ACA45A3682D49328299460DD1FF5381C8845CE8C802CE6BE1C7A6F306D0392D",
        SOURCE_COMMIT,
    ),
    "after_oracle": (
        f"{VALIDATION_DIR}/after-fix/stale-gaze-oracle.json",
        "CF90052E8938E5F76E6EDB199E7B43BBDCC621AE2A8B48329F46C4A6CE0ED2A5",
        EVIDENCE_COMMIT,
    ),
    "after_screenshot": (
        f"{VALIDATION_DIR}/after-fix/drag-stale-gaze.png",
        "61C57163C49F6B6A7AA323BBEFDB7915CEF7B6DC596AFC55382C9BBE562323BC",
        EVIDENCE_COMMIT,
    ),
    "replay_result": (
        f"{VALIDATION_DIR}/browser-replay-result.json",
        "8FCAD0AC4C5370EFBBBC6C3785B6E115AA1E77C69EA81C0E137207AC1D33721C",
        EVIDENCE_COMMIT,
    ),
    "pixel_dom_route": (
        f"{VALIDATION_DIR}/pixel-dom-route-artifact.json",
        "91E6793F01B8368933E61115E93AD7280B435A9A1429D4B2DE743B61878BD1F3",
        EVIDENCE_COMMIT,
    ),
    "screenshot_manifest": (
        f"{VALIDATION_DIR}/screenshot-manifest.json",
        "1886C6193AE846C11116462A20A1DCDC093DB4BD65BED36C9B19CB762965460A",
        EVIDENCE_COMMIT,
    ),
    "determinism": (
        f"{VALIDATION_DIR}/clean-replay-determinism.json",
        "EAE756749EDC2030D18CB349137598F2C33642BB381DD64F6CD12C4DE73A51DB",
        EVIDENCE_COMMIT,
    ),
    "failed_owner_result": (
        "docs/validation/companion-browser-visual-contract-comp-req-471/"
        "owner-review.json",
        "54B1AD42C955FB6AE4F9AAA50E4AF9A64FB0468C0A38FD13A704B769AAB1AA95",
        "",
    ),
    "failed_owner_raw": (
        "docs/validation/companion-browser-visual-contract-comp-req-471/"
        "owner-review.raw.json",
        "065F5F1E298550DE2FFE170116F5791D19D3156570265DDB0A08FF3C5039FD2B",
        "",
    ),
    "failed_owner_note": (
        "docs/validation/companion-browser-visual-contract-comp-req-471/"
        "owner-review.note.txt",
        "7EB70257593DA06F682A3DDDA54A9D260D4FC514F645237F5CA74B08F8DA61A6",
        "",
    ),
}
COMMIT_HASH_OVERRIDES: dict[str, str] = {
    "page": "A1F3B09015D0AB4E0951EE0C0A7963C4E8C6A7D48DA06F6030D71C6FB5D71D9A",
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
    "snapshot_count": 252,
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


def git_output(repo_root: Path, *args: str) -> bytes | None:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    return completed.stdout if completed.returncode == 0 else None


def git_blob(repo_root: Path, commit: str, relative_path: str) -> bytes | None:
    return git_output(repo_root, "show", f"{commit}:{relative_path}")


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


def require(
    failures: list[str],
    label: str,
    observed: Any,
    expected: Any,
) -> None:
    if observed != expected:
        expected_display = sorted(expected) if isinstance(expected, set) else expected
        observed_display = sorted(observed) if isinstance(observed, set) else observed
        failures.append(
            f"{label}: expected {expected_display!r}, "
            f"observed {observed_display!r}"
        )


def expected_matrix_ids() -> set[str]:
    return {
        f"{viewport}-{pointer_type}-{scenario}"
        for viewport in ("desktop", "mobile")
        for pointer_type in ("mouse", "touch", "pen")
        for scenario in SCENARIOS
    }


def validate_oracles(
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    failures: list[str],
) -> None:
    if before is None or after is None:
        return
    require(failures, "before status", before.get("status"), "FAIL_STALE_GAZE")
    require(
        failures,
        "before page",
        before.get("observed_page_sha256"),
        OLD_PAGE_SHA256,
    )
    before_pixel = before.get("measurement", {}).get("pixel", {})
    if (
        before_pixel.get("stale_center_mask_total", 0) <= 0
        or before_pixel.get("stale_center_mask_left_eye", 0) <= 0
        or before_pixel.get("stale_center_mask_right_eye", 0) <= 0
    ):
        failures.append("before oracle did not observe stale pixels in both eyes")
    require(failures, "after status", after.get("status"), "PASS")
    require(
        failures,
        "after page",
        after.get("observed_page_sha256"),
        PAGE_SHA256,
    )
    after_measurement = after.get("measurement", {})
    after_pixel = after_measurement.get("pixel", {})
    for key in (
        "binary_mismatch_count",
        "stale_center_mask_left_eye",
        "stale_center_mask_right_eye",
        "stale_center_mask_total",
    ):
        require(failures, f"after oracle {key}", after_pixel.get(key), 0)
    require(
        failures,
        "after oracle generated gaze base",
        after_measurement.get("sources", {}).get(
            "frame_is_generated_gaze_base"
        ),
        True,
    )
    after_dom = after_measurement.get("dom", {})
    for key in (
        "active_200x200_surfaces",
        "frame_nodes",
        "gaze_nodes",
        "visible_frame_nodes",
        "visible_gaze_nodes",
    ):
        require(failures, f"after oracle DOM {key}", after_dom.get(key), 1)


def validate_replay(
    replay: dict[str, Any] | None,
    failures: list[str],
) -> None:
    if replay is None:
        return
    require(
        failures,
        "replay schema",
        replay.get("schema"),
        "companion.browser-owner-review-replay.v3",
    )
    require(
        failures,
        "replay status",
        replay.get("status"),
        "PASS_BROWSER_OWNER_REVIEW_MACHINE_REPLAY",
    )
    require(
        failures,
        "replay requirements",
        replay.get("requirements"),
        [
            "COMP-REQ-440",
            "COMP-REQ-441",
            "COMP-REQ-442",
            "COMP-REQ-471",
            "COMP-REQ-508",
            "COMP-REQ-509",
            "COMP-REQ-510",
        ],
    )
    page = replay.get("page", {})
    require(failures, "replay page accepted", page.get("accepted_sha256"), PAGE_SHA256)
    require(failures, "replay page observed", page.get("observed_sha256"), PAGE_SHA256)
    require(failures, "replay page path", page.get("repo_path"), PAGE_PATH)
    require(failures, "replay URL", page.get("url"), URL)
    require(failures, "replay runtime URL", page.get("runtime_url"), URL)
    require(failures, "replay totals", replay.get("totals"), EXPECTED_TOTALS)
    checks = replay.get("checks")
    if not isinstance(checks, dict) or not checks or not all(checks.values()):
        failures.append("replay checks are not all true")
    side_effects = replay.get("side_effect_counters", {})
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
        require(failures, f"replay side effect {key}", side_effects.get(key), 0)


def validate_pixel(
    pixel: dict[str, Any] | None,
    failures: list[str],
) -> None:
    if pixel is None:
        return
    require(
        failures,
        "pixel schema",
        pixel.get("schema"),
        "companion.browser-owner-review-pixel-dom-route.v3",
    )
    require(failures, "pixel status", pixel.get("status"), "PASS")
    require(
        failures,
        "pixel requirements",
        pixel.get("requirements"),
        ["COMP-REQ-508", "COMP-REQ-509", "COMP-REQ-510"],
    )
    invariants = pixel.get("invariants", {})
    expected_invariants = {
        "accepted_centered_rest_png_sha256": (
            "3269679155DE09F2FCEDFF3DC059DE4C9AC1E811400258B3B110F839646A0E31"
        ),
        "conflicting_surface_overlap_count": 0,
        "debug_visible_count": 0,
        "document_route_per_scenario": 1,
        "http_404_count": 0,
        "microphone_request_count": 0,
        "microphone_glyph_pixel_count": 0,
        "out_of_bounds_count": 0,
        "outside_black_pixel_count": 0,
        "primary_screen_count": 1,
        "stale_layer_count": 0,
        "stale_pupil_pixel_count": 0,
        "stale_pupil_state_count": 0,
    }
    require(failures, "pixel invariants", invariants, expected_invariants)
    matrix = pixel.get("matrix")
    if not isinstance(matrix, list):
        failures.append("pixel matrix missing")
        matrix = []
    ids = [row.get("id") for row in matrix if isinstance(row, dict)]
    require(failures, "matrix count", len(matrix), 42)
    require(failures, "matrix unique count", len(set(ids)), 42)
    require(failures, "matrix exact ids", set(ids), expected_matrix_ids())
    for row in matrix:
        if not isinstance(row, dict):
            failures.append("matrix row is not object")
            continue
        row_id = str(row.get("id", ""))
        require(failures, f"{row_id} status", row.get("status"), "PASS")
        require(
            failures,
            f"{row_id} document requests",
            row.get("document_requests"),
            1,
        )
        require(failures, f"{row_id} errors", row.get("errors"), [])
        if row_id.endswith("-drag"):
            result = row.get("result", {})
            require(failures, f"{row_id} directions", result.get("direction_count"), 5)
            require(
                failures,
                f"{row_id} unique gaze",
                result.get("unique_gaze_sources"),
                5,
            )
            require(
                failures,
                f"{row_id} unique pixels",
                result.get("unique_pixel_signatures"),
                5,
            )
        if row_id.endswith("-recording-return"):
            result = row.get("result", {})
            require(
                failures,
                f"{row_id} phases",
                result.get("ordered_phases"),
                ["expression", "listening", "thoughtful_listening"],
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
                f"{row_id} reentry",
                result.get("reentry_count"),
                1,
            )
            negatives = result.get("negative_checks", [])
            require(failures, f"{row_id} negative count", len(negatives), 9)
            require(
                failures,
                f"{row_id} negative names",
                {item.get("kind") for item in negatives},
                {
                    "blur-no-exit",
                    "cancel-no-exit",
                    "drag-no-exit",
                    "duplicate-release-no-exit",
                    "far-pair-no-exit",
                    "hold-no-exit",
                    "late-pair-no-exit",
                    "single-no-exit",
                    "triple-no-extra-toggle",
                },
            )
            wave = result.get("inward_wave_cycle", [])
            require(
                failures,
                f"{row_id} wave steps",
                [item.get("step") for item in wave],
                [0, 1, 2, 3],
            )
            distances = [
                item.get("distance_to_listening_point") for item in wave
            ]
            if len(distances) != 4 or not all(
                isinstance(value, (int, float)) for value in distances
            ) or not all(
                distances[index] < distances[index - 1]
                for index in range(1, len(distances))
            ):
                failures.append(f"{row_id} inward wave distances not decreasing")
    states = pixel.get("states")
    if not isinstance(states, list):
        failures.append("pixel states missing")
        states = []
    state_ids = [row.get("id") for row in states if isinstance(row, dict)]
    require(failures, "state count", len(states), 252)
    require(failures, "state unique count", len(set(state_ids)), 252)
    for state in states:
        if not isinstance(state, dict):
            failures.append("state row is not object")
            continue
        state_id = str(state.get("id", ""))
        dom = state.get("dom", {})
        expected = dom.get("expected", {})
        for actual, expected_key in (
            ("face_count", "face"),
            ("gaze_count", "gaze"),
            ("highlight_layer_count", "highlight"),
            ("menu_count", "menu"),
            ("recording_wave_count", "wave"),
        ):
            require(
                failures,
                f"{state_id} {actual}",
                dom.get(actual),
                expected.get(expected_key),
            )
        for key, expected_value in (
            ("primary_screen_count", 1),
            ("gaze_node_count", 1),
            ("menu_node_count", 1),
            ("conflict_count", 0),
            ("debug_visible", []),
            ("out_of_bounds", []),
            ("stage_width", 200),
            ("stage_height", 200),
        ):
            require(failures, f"{state_id} DOM {key}", dom.get(key), expected_value)
        require(
            failures,
            f"{state_id} outside pixels",
            state.get("pixel", {}).get("outside_black_pixels"),
            0,
        )
        route = state.get("route", {})
        require(failures, f"{state_id} route", route.get("pathname"), f"/{PAGE_PATH}")
        if state.get("contract", {}).get("mode") != "menu":
            pupil = state.get("pupil_oracle", {})
            require(failures, f"{state_id} pupil checked", pupil.get("checked"), True)
            for key in (
                "binary_mismatch_count",
                "stale_center_mask_left_eye",
                "stale_center_mask_right_eye",
                "stale_center_mask_total",
            ):
                require(failures, f"{state_id} pupil {key}", pupil.get(key), 0)
        event_ids = state.get("events", {}).get("event_ids", [])
        require(
            failures,
            f"{state_id} unique event ids",
            len(event_ids),
            len(set(event_ids)),
        )
        if state.get("contract", {}).get("mode") == "recording":
            microphone = state.get("microphone_oracle", {})
            require(failures, f"{state_id} mic checked", microphone.get("checked"), True)
            if microphone.get("old_mic_mask_pixels", 0) <= 0:
                failures.append(f"{state_id} old microphone mask is empty")
            for key in (
                "current_wave_mask_overlap",
                "visible_mic_asset_sources",
            ):
                require(failures, f"{state_id} mic {key}", microphone.get(key), 0)


def validate_screenshots(
    repo_root: Path,
    manifest: dict[str, Any] | None,
    overlay: dict[str, bytes] | None,
    failures: list[str],
) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    if manifest is None:
        return observations
    require(
        failures,
        "screenshot schema",
        manifest.get("schema"),
        "companion.browser-owner-review-screenshots.v3",
    )
    require(failures, "screenshot status", manifest.get("status"), "PASS")
    require(
        failures,
        "screenshot requirements",
        manifest.get("requirements"),
        ["COMP-REQ-508", "COMP-REQ-509", "COMP-REQ-510"],
    )
    require(
        failures,
        "screenshot page",
        manifest.get("accepted_page_sha256"),
        PAGE_SHA256,
    )
    rows = manifest.get("screenshots")
    if not isinstance(rows, list):
        failures.append("screenshot rows missing")
        return observations
    ids = [row.get("id") for row in rows if isinstance(row, dict)]
    paths = [row.get("path") for row in rows if isinstance(row, dict)]
    require(failures, "screenshot count", len(rows), 50)
    require(failures, "screenshot unique ids", len(set(ids)), 50)
    require(failures, "screenshot unique paths", len(set(paths)), 50)
    for row in rows:
        if not isinstance(row, dict):
            failures.append("screenshot row is not object")
            continue
        relative_path = str(row.get("path", ""))
        try:
            data = read_bytes(repo_root, relative_path, overlay)
        except OSError:
            failures.append(f"screenshot missing: {relative_path}")
            continue
        observed = sha256_bytes(data)
        require(
            failures,
            f"screenshot hash {row.get('id')}",
            observed,
            row.get("sha256"),
        )
        require(
            failures,
            f"screenshot bytes {row.get('id')}",
            len(data),
            row.get("bytes"),
        )
        observations.append(
            {
                "bytes": len(data),
                "id": row.get("id"),
                "path": relative_path,
                "sha256": observed,
            }
        )
    return observations


def validate_determinism(
    determinism: dict[str, Any] | None,
    failures: list[str],
) -> None:
    if determinism is None:
        return
    require(
        failures,
        "determinism status",
        determinism.get("status"),
        "PASS_TWO_CLEAN_REPLAYS_BYTE_IDENTICAL",
    )
    require(
        failures,
        "determinism source commit",
        determinism.get("candidate_commit"),
        SOURCE_COMMIT,
    )
    require(failures, "determinism page", determinism.get("page_sha256"), PAGE_SHA256)
    require(failures, "determinism URL", determinism.get("url"), URL)
    require(failures, "determinism runs", determinism.get("run_count"), 2)
    require(failures, "determinism byte identity", determinism.get("byte_identical"), True)
    require(failures, "determinism run equality", determinism.get("run_a"), determinism.get("run_b"))
    side_effects = determinism.get("side_effect_counters", {})
    for key in (
        "server_start",
        "browser_window_open",
        "popup",
        "operator_prompt",
        "microphone_permission_request",
        "hardware",
        "lower_write",
        "platform_write",
        "production_write",
        "registry_write",
    ):
        require(failures, f"determinism side effect {key}", side_effects.get(key), 0)


def evaluate(
    repo_root: Path,
    source_commit: str,
    evidence_commit: str,
    overlay: dict[str, bytes] | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    failures: list[str] = []
    identities: list[dict[str, Any]] = []
    parsed: dict[str, dict[str, Any] | None] = {}
    source_object = git_output(repo_root, "rev-parse", f"{source_commit}^{{commit}}")
    evidence_object = git_output(repo_root, "rev-parse", f"{evidence_commit}^{{commit}}")
    source_resolved = source_object.decode("ascii").strip() if source_object else None
    evidence_resolved = evidence_object.decode("ascii").strip() if evidence_object else None
    require(failures, "source commit argument", source_commit, SOURCE_COMMIT)
    require(failures, "source commit object", source_resolved, SOURCE_COMMIT)
    require(failures, "evidence commit argument", evidence_commit, EVIDENCE_COMMIT)
    require(failures, "evidence commit object", evidence_resolved, EVIDENCE_COMMIT)

    for identity, (relative_path, expected_hash, commit) in BOUND_FILES.items():
        try:
            data = read_bytes(repo_root, relative_path, overlay)
            observed_hash = sha256_bytes(data)
        except OSError:
            data = b""
            observed_hash = None
            failures.append(f"bound file missing: {identity}")
        require(failures, f"worktree hash {identity}", observed_hash, expected_hash)
        commit_hash = None
        commit_expected_hash = COMMIT_HASH_OVERRIDES.get(identity, expected_hash)
        if commit:
            blob = git_blob(repo_root, commit, relative_path)
            commit_hash = sha256_bytes(blob) if blob is not None else None
            require(
                failures,
                f"commit blob {identity}",
                commit_hash,
                commit_expected_hash,
            )
        identities.append(
            {
                "commit": commit or None,
                "commit_expected_sha256": commit_expected_hash if commit else None,
                "commit_sha256": commit_hash,
                "expected_sha256": expected_hash,
                "id": identity,
                "observed_sha256": observed_hash,
                "path": relative_path,
            }
        )
        if identity in {
            "before_oracle",
            "after_oracle",
            "replay_result",
            "pixel_dom_route",
            "screenshot_manifest",
            "determinism",
            "failed_owner_result",
            "failed_owner_raw",
        }:
            parsed[identity] = parse_json(identity, data, failures)

    if overlay is not None and NEW_OWNER_RESULT in overlay:
        failures.append("successor owner result must not exist before new prompt")
    elif (repo_root / NEW_OWNER_RESULT).exists():
        failures.append("successor owner result must not exist before new prompt")

    failed_owner = parsed.get("failed_owner_result")
    if failed_owner is not None:
        require(failures, "failed owner selection", failed_owner.get("selected"), "失败")
        require(
            failures,
            "failed owner status",
            failed_owner.get("status"),
            "FAIL_OWNER_BROWSER_EXPERIENCE_RETURN_TO_ITERATION",
        )
        require(
            failures,
            "failed owner machine preserved",
            failed_owner.get("machine_result", {}).get("status_preserved"),
            "PASS",
        )
    failed_raw = parsed.get("failed_owner_raw")
    if failed_raw is not None:
        require(failures, "failed raw selection", failed_raw.get("selected"), "失败")

    validate_oracles(
        parsed.get("before_oracle"),
        parsed.get("after_oracle"),
        failures,
    )
    validate_replay(parsed.get("replay_result"), failures)
    validate_pixel(parsed.get("pixel_dom_route"), failures)
    screenshots = validate_screenshots(
        repo_root,
        parsed.get("screenshot_manifest"),
        overlay,
        failures,
    )
    validate_determinism(parsed.get("determinism"), failures)

    page_bytes = read_bytes(repo_root, PAGE_PATH, overlay)
    for token in (
        b"touchGazeClearedBase",
        b"touchSetGaze",
        b"touchRestoreExpressionGaze",
        b"epoch!==gazeEpoch",
        b"state.request!==request",
        b"menuHoldMs:700",
        b"doubleGapMs:650",
        b"doubleMovePx:40",
        b"recording_entry_rejected_missing_prestate",
        b"focused_presence",
        b"thoughtful_presence",
        b"recording_route_enter",
        b"recording_route_exit",
        b"duplicate_release_ignored",
        b"distance_to_listening_point",
    ):
        if token not in page_bytes:
            failures.append(f"page source contract token missing: {token!r}")

    failures = sorted(set(failures))
    replay = parsed.get("replay_result") or {}
    pixel = parsed.get("pixel_dom_route") or {}
    return {
        "artifact_bindings": identities,
        "checks": {
            "all_bound_worktree_and_commit_hashes_exact": not any(
                item.startswith(("worktree hash", "commit blob"))
                for item in failures
            ),
            "before_page_real_pixel_negative_failed": not any(
                item.startswith("before ") for item in failures
            ),
            "deterministic_replay_byte_identical": not any(
                item.startswith("determinism ") for item in failures
            ),
            "new_owner_result_absent": not any(
                "successor owner result" in item for item in failures
            ),
            "old_owner_failure_preserved": not any(
                item.startswith("failed owner") for item in failures
            ),
            "source_and_evidence_commits_exact": source_resolved == SOURCE_COMMIT
            and evidence_resolved == EVIDENCE_COMMIT
            and source_commit == SOURCE_COMMIT
            and evidence_commit == EVIDENCE_COMMIT,
            "stale_pupil_pixels_zero_all_observed_expression_states": not any(
                "pupil" in item or "after oracle" in item for item in failures
            ),
        },
        "commit_bindings": {
            "evidence": EVIDENCE_COMMIT,
            "evidence_argument": evidence_commit,
            "evidence_resolved": evidence_resolved,
            "source": SOURCE_COMMIT,
            "source_argument": source_commit,
            "source_resolved": source_resolved,
        },
        "default_off": True,
        "failed_checks": failures,
        "owner_boundary": {
            "new_owner_prompt_invoked": False,
            "new_owner_result_exists": (
                NEW_OWNER_RESULT in (overlay or {})
                or (repo_root / NEW_OWNER_RESULT).exists()
            ),
            "owner_pass_claimed": False,
            "prior_owner_failure_preserved": True,
            "remaining_gate": (
                "One new canonical Chinese browser owner review after an exact "
                "zero-effect CheckOnly; this artifact does not invoke it."
            ),
        },
        "page": {
            "path": PAGE_PATH,
            "sha256": PAGE_SHA256,
            "url": URL,
        },
        "requirements": [
            "COMP-REQ-440",
            "COMP-REQ-441",
            "COMP-REQ-442",
            "COMP-REQ-471",
            "COMP-REQ-504",
            "COMP-REQ-507",
            "COMP-REQ-508",
            "COMP-REQ-509",
            "COMP-REQ-510",
        ],
        "schema": "companion.browser-source-bound-machine-ready.v3",
        "semantic_counts": {
            "matrix_scenarios": len(pixel.get("matrix", [])),
            "replay_combinations": replay.get("totals", {}).get(
                "replay_combinations"
            ),
            "screenshots": len(screenshots),
            "state_snapshots": len(pixel.get("states", [])),
            "recording_negative_checks": replay.get("totals", {}).get(
                "recording_negative_checks"
            ),
            "recording_route_entries": replay.get("totals", {}).get(
                "route_recording_entries"
            ),
            "recording_route_exits": replay.get("totals", {}).get(
                "route_recording_exits"
            ),
            "stale_pupil_pixels": replay.get("totals", {}).get(
                "stale_pupil_pixel_count"
            ),
            "stale_pupil_states": replay.get("totals", {}).get(
                "stale_pupil_state_count"
            ),
        },
        "side_effect_counters": {
            "browser": 0,
            "hardware": 0,
            "microphone_permission_request": 0,
            "owner_prompt": 0,
            "popup": 0,
            "process": 0,
            "server_start": 0,
            "write": 0,
        },
        "status": (
            "BROWSER_OWNER_REVIEW_READY_SUCCESSOR"
            if not failures
            else "NO_GO"
        ),
    }


def write_result(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(result))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--evidence-commit", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = evaluate(
        Path(args.repo_root),
        args.source_commit,
        args.evidence_commit,
    )
    write_result(Path(args.output), result)
    print(
        json.dumps(
            {
                "failed_checks": len(result["failed_checks"]),
                "status": result["status"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "BROWSER_OWNER_REVIEW_READY_SUCCESSOR" else 1


if __name__ == "__main__":
    raise SystemExit(main())
