#!/usr/bin/env python3
"""Fail-closed source and evidence gate for the accepted browser replay."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


CANDIDATE_COMMIT = "0f8fb928a726d99b4a6dacff2b59cc5f1c0caea9"
REVIEW_URL = (
    "http://127.0.0.1:4173/docs/art/iterations/"
    "companion-pet-expression-v9-two-track-rig-v7/candidate/"
    "wb55-browser-parity-attempt-01/index.html"
)
PAGE_PATH = (
    "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/"
    "candidate/wb55-browser-parity-attempt-01/index.html"
)
PAGE_SHA256 = "BAE21BCCC7BB5FAD4A0922D5E9C42FCB25EF58DD7B8102A7C72656F7B700CF5E"
PAGE_CANDIDATE_TREE_SHA256 = (
    "696B68E440E12427A49D089AE3A2EEB1BB713C08671B94050349C2B1A1CD25A2"
)
VALIDATION_DIR = "docs/validation/companion-browser-owner-review-ready-comp-req-471"
CLEAN_REPLAY_RECEIPT_PATH = (
    "docs/validation/companion-browser-owner-review-source-bound-comp-req-504/"
    "clean-replay-determinism.json"
)
CLEAN_REPLAY_RECEIPT_SHA256 = (
    "AD6E1E39E31F68DED4FA00DFC074772994B5EED2C4E62BFC6CB80BF81FBB7A7E"
)

BOUND_FILES = {
    "accepted_page": (PAGE_PATH, PAGE_SHA256, None),
    "replay_tool": (
        "tools/faraday_upper_art/replay_companion_browser_owner_review_ready.mjs",
        "259CB0D0D914A882634F2B37A05C6AAF5CD4413DAD766A98B997B7B7649C9E6D",
        "6F3C58A3F2DFD47717ABFCA040467870DAF48F47ED0999EF26955E0DAD4B56BA",
    ),
    "prior_checkonly_verifier": (
        "tools/faraday_upper_art/"
        "verify_companion_browser_owner_review_ready_checkonly.py",
        "33581C21402DDD7591B364F8BEB32E710585CEA7C1DC8C27A615F440FF86D44D",
        "33581C21402DDD7591B364F8BEB32E710585CEA7C1DC8C27A615F440FF86D44D",
    ),
    "replay_result": (
        f"{VALIDATION_DIR}/browser-replay-result.json",
        "71C23ECF69CE759BAD8D328946385A82ABFA5F09D5AE14C109D3EBBB505F3B8D",
        "65ADEF4F50D1BB5A3635835F63AD9D353337F4684DFA7610E975AB022A22DD26",
    ),
    "pixel_dom_route": (
        f"{VALIDATION_DIR}/pixel-dom-route-artifact.json",
        "670E41E6D928AD6FFAF50D580D87EC2FA19DD8507D0513375B7259BE9375C2FA",
        "670E41E6D928AD6FFAF50D580D87EC2FA19DD8507D0513375B7259BE9375C2FA",
    ),
    "screenshot_manifest": (
        f"{VALIDATION_DIR}/screenshot-manifest.json",
        "83B9EB8239D34CB772A1E85DC717DF2674C85960D63ACE81797D029CA697E823",
        "DE6E009B1676E525BF1860EDB67E09F46A7B1E085380F426E7507049663688C5",
    ),
    "browser_owner_review_ready": (
        f"{VALIDATION_DIR}/BROWSER_OWNER_REVIEW_READY.json",
        "166FEC2E69BDF17D1EA9D398964AF146DE9EB9CC589797CE84DD03299876A7E8",
        "BBEB0766ED8D9202207F5043815CB142CE9015A500F0FBDF5321307B75315515",
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
    "microphone_requests": 0,
    "out_of_bounds_count": 0,
    "outside_black_pixel_count": 0,
    "page_error_count": 0,
    "replay_combinations": 6,
    "route_menu_entries": 6,
    "route_recording_entries": 6,
    "scenario_count": 42,
    "snapshot_count": 192,
    "stale_layer_count": 0,
}
VIEWPORTS = ("desktop", "mobile")
POINTER_TYPES = ("mouse", "touch", "pen")
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
    ).encode("utf-8")


def read_bytes(
    repo_root: Path, relative_path: str, overlay: dict[str, bytes] | None
) -> bytes:
    normalized = relative_path.replace("\\", "/")
    if overlay is not None and normalized in overlay:
        return overlay[normalized]
    return (repo_root / normalized).read_bytes()


def run_git(repo_root: Path, *args: str) -> tuple[int, bytes, bytes]:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    return completed.returncode, completed.stdout, completed.stderr


def git_blob(repo_root: Path, commit: str, relative_path: str) -> bytes | None:
    code, stdout, _ = run_git(repo_root, "show", f"{commit}:{relative_path}")
    return stdout if code == 0 else None


def parse_json_bytes(
    label: str, data: bytes, failures: list[str]
) -> dict[str, Any] | None:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        failures.append(f"{label}: invalid JSON: {exc.__class__.__name__}")
        return None
    if not isinstance(value, dict):
        failures.append(f"{label}: root must be an object")
        return None
    return value


def png_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def require_equal(
    failures: list[str], label: str, observed: Any, expected: Any
) -> None:
    if observed != expected:
        failures.append(f"{label}: expected {expected!r}, observed {observed!r}")


def validate_replay(replay: dict[str, Any], failures: list[str]) -> None:
    require_equal(
        failures,
        "replay schema",
        replay.get("schema"),
        "companion.browser-owner-review-replay.v1",
    )
    require_equal(
        failures,
        "replay status",
        replay.get("status"),
        "PASS_BROWSER_OWNER_REVIEW_MACHINE_REPLAY",
    )
    require_equal(
        failures,
        "replay requirements",
        replay.get("requirements"),
        ["COMP-REQ-440", "COMP-REQ-441", "COMP-REQ-442", "COMP-REQ-471"],
    )
    page = replay.get("page", {})
    for key in ("accepted_sha256", "observed_sha256"):
        require_equal(failures, f"replay page {key}", page.get(key), PAGE_SHA256)
    require_equal(failures, "replay page path", page.get("repo_path"), PAGE_PATH)
    require_equal(failures, "replay URL", page.get("url"), REVIEW_URL)
    require_equal(failures, "replay totals", replay.get("totals"), EXPECTED_TOTALS)

    checks = replay.get("checks")
    if not isinstance(checks, dict) or not checks or not all(checks.values()):
        failures.append("replay checks: every recorded check must be true")

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
        require_equal(failures, f"replay side effect {key}", side_effects.get(key), 0)


def expected_matrix_ids() -> set[str]:
    return {
        f"{viewport}-{pointer_type}-{scenario}"
        for viewport in VIEWPORTS
        for pointer_type in POINTER_TYPES
        for scenario in SCENARIOS
    }


def validate_matrix_row(row: dict[str, Any], failures: list[str]) -> None:
    row_id = str(row.get("id", ""))
    parts = row_id.split("-", 2)
    if len(parts) != 3:
        failures.append(f"matrix row id malformed: {row_id!r}")
        return
    viewport, pointer_type, scenario = parts
    require_equal(failures, f"{row_id} viewport", row.get("viewport"), viewport)
    require_equal(
        failures, f"{row_id} pointer type", row.get("pointer_type"), pointer_type
    )
    require_equal(failures, f"{row_id} status", row.get("status"), "PASS")
    require_equal(failures, f"{row_id} document requests", row.get("document_requests"), 1)
    require_equal(failures, f"{row_id} errors", row.get("errors"), [])
    result = row.get("result", {})
    if scenario == "drag":
        require_equal(failures, f"{row_id} direction count", result.get("direction_count"), 5)
        require_equal(
            failures, f"{row_id} unique gaze", result.get("unique_gaze_sources"), 5
        )
        require_equal(
            failures, f"{row_id} unique pixels", result.get("unique_pixel_signatures"), 5
        )
        require_equal(
            failures, f"{row_id} layer count", result.get("layer_count_constant"), True
        )
    elif scenario == "hold-menu-return":
        require_equal(failures, f"{row_id} menu entries", result.get("menu_entries"), 1)
        require_equal(failures, f"{row_id} root visits", result.get("root_visits"), 4)
        require_equal(failures, f"{row_id} UI assets", result.get("ui_asset_states"), 3)
        require_equal(
            failures,
            f"{row_id} return identity",
            result.get("return_equals_fresh_centered_rest"),
            True,
        )
    elif scenario == "recording-return":
        require_equal(
            failures, f"{row_id} recording entries", result.get("recording_entries"), 1
        )
        require_equal(
            failures, f"{row_id} microphone requests", result.get("microphone_requests"), 0
        )
        require_equal(
            failures,
            f"{row_id} return identity",
            result.get("return_equals_fresh_centered_rest"),
            True,
        )
    elif scenario == "single-tap":
        require_equal(failures, f"{row_id} committed once", result.get("committed_once"), True)
        require_equal(failures, f"{row_id} gaze replaced", result.get("gaze_replaced"), True)
        require_equal(
            failures, f"{row_id} route activations", result.get("route_activations"), 0
        )
    else:
        require_equal(
            failures, f"{row_id} route activations", result.get("route_activations"), 0
        )
        if scenario == "early-up":
            require_equal(failures, f"{row_id} hold canceled", result.get("hold_canceled"), True)


def validate_pixel_dom_route(pixel: dict[str, Any], failures: list[str]) -> None:
    require_equal(
        failures,
        "pixel schema",
        pixel.get("schema"),
        "companion.browser-owner-review-pixel-dom-route.v1",
    )
    require_equal(failures, "pixel status", pixel.get("status"), "PASS")
    expected_invariants = {
        "accepted_centered_rest_png_sha256": (
            "3269679155DE09F2FCEDFF3DC059DE4C9AC1E811400258B3B110F839646A0E31"
        ),
        "conflicting_surface_overlap_count": 0,
        "debug_visible_count": 0,
        "document_route_per_scenario": 1,
        "http_404_count": 0,
        "microphone_request_count": 0,
        "out_of_bounds_count": 0,
        "outside_black_pixel_count": 0,
        "primary_screen_count": 1,
        "stale_layer_count": 0,
    }
    require_equal(failures, "pixel invariants", pixel.get("invariants"), expected_invariants)

    matrix = pixel.get("matrix")
    if not isinstance(matrix, list):
        failures.append("pixel matrix must be an array")
        matrix = []
    ids = [row.get("id") for row in matrix if isinstance(row, dict)]
    require_equal(failures, "matrix row count", len(matrix), 42)
    require_equal(failures, "matrix unique id count", len(set(ids)), len(ids))
    require_equal(failures, "matrix exact id set", set(ids), expected_matrix_ids())
    for row in matrix:
        if not isinstance(row, dict):
            failures.append("matrix row must be an object")
            continue
        validate_matrix_row(row, failures)

    states = pixel.get("states")
    if not isinstance(states, list):
        failures.append("pixel states must be an array")
        states = []
    state_ids = [row.get("id") for row in states if isinstance(row, dict)]
    require_equal(failures, "state count", len(states), 192)
    require_equal(failures, "state unique id count", len(set(state_ids)), len(state_ids))
    allowed_hashes = {"#expression", "#menu", "#recording"}
    for state in states:
        if not isinstance(state, dict):
            failures.append("state row must be an object")
            continue
        state_id = str(state.get("id", ""))
        dom = state.get("dom", {})
        expected = dom.get("expected", {})
        for actual_key, expected_key in (
            ("face_count", "face"),
            ("gaze_count", "gaze"),
            ("highlight_layer_count", "highlight"),
            ("menu_count", "menu"),
        ):
            require_equal(
                failures,
                f"{state_id} {actual_key}",
                dom.get(actual_key),
                expected.get(expected_key),
            )
        require_equal(failures, f"{state_id} primary screen count", dom.get("primary_screen_count"), 1)
        require_equal(failures, f"{state_id} stage width", dom.get("stage_width"), 200)
        require_equal(failures, f"{state_id} stage height", dom.get("stage_height"), 200)
        require_equal(failures, f"{state_id} conflict count", dom.get("conflict_count"), 0)
        require_equal(failures, f"{state_id} out of bounds", dom.get("out_of_bounds"), [])
        require_equal(
            failures,
            f"{state_id} outside black pixels",
            state.get("pixel", {}).get("outside_black_pixels"),
            0,
        )
        route = state.get("route", {})
        require_equal(failures, f"{state_id} route path", route.get("pathname"), "/" + PAGE_PATH)
        if route.get("hash") not in allowed_hashes:
            failures.append(f"{state_id} route hash is not an accepted exclusive route")


def validate_screenshots(
    repo_root: Path,
    screenshot_manifest: dict[str, Any],
    overlay: dict[str, bytes] | None,
    failures: list[str],
    observations: list[dict[str, Any]],
) -> None:
    require_equal(
        failures,
        "screenshot schema",
        screenshot_manifest.get("schema"),
        "companion.browser-owner-review-screenshots.v1",
    )
    require_equal(failures, "screenshot status", screenshot_manifest.get("status"), "PASS")
    require_equal(
        failures,
        "screenshot accepted page",
        screenshot_manifest.get("accepted_page_sha256"),
        PAGE_SHA256,
    )
    screenshots = screenshot_manifest.get("screenshots")
    if not isinstance(screenshots, list):
        failures.append("screenshots must be an array")
        return
    require_equal(failures, "screenshot count", len(screenshots), 50)
    ids = [entry.get("id") for entry in screenshots if isinstance(entry, dict)]
    paths = [entry.get("path") for entry in screenshots if isinstance(entry, dict)]
    require_equal(failures, "screenshot unique id count", len(set(ids)), len(ids))
    require_equal(failures, "screenshot unique path count", len(set(paths)), len(paths))
    for entry in screenshots:
        if not isinstance(entry, dict):
            failures.append("screenshot entry must be an object")
            continue
        relative_path = str(entry.get("path", ""))
        screenshot_id = str(entry.get("id", ""))
        try:
            data = read_bytes(repo_root, relative_path, overlay)
        except OSError:
            failures.append(f"screenshot missing: {screenshot_id}")
            continue
        observed_hash = sha256_bytes(data)
        expected_hash = entry.get("sha256")
        dimensions = png_dimensions(data)
        if observed_hash != expected_hash:
            failures.append(f"screenshot SHA mismatch: {screenshot_id}")
        if len(data) != entry.get("bytes"):
            failures.append(f"screenshot byte count mismatch: {screenshot_id}")
        if dimensions is None:
            failures.append(f"screenshot is not PNG: {screenshot_id}")
        elif entry.get("kind") != "layout" and dimensions != (200, 200):
            failures.append(f"screenshot is not 200x200: {screenshot_id}")
        observations.append(
            {
                "id": screenshot_id,
                "path": relative_path,
                "sha256": observed_hash,
                "bytes": len(data),
                "dimensions": list(dimensions) if dimensions else None,
                "match": observed_hash == expected_hash,
            }
        )


def validate_candidate_screenshot_tree(
    repo_root: Path, failures: list[str]
) -> tuple[int, str | None]:
    manifest_path = BOUND_FILES["screenshot_manifest"][0]
    manifest_data = git_blob(repo_root, CANDIDATE_COMMIT, manifest_path)
    if manifest_data is None:
        failures.append("candidate screenshot manifest blob missing")
        return 1, None
    manifest_hash = sha256_bytes(manifest_data)
    if manifest_hash != BOUND_FILES["screenshot_manifest"][2]:
        failures.append("candidate screenshot manifest blob mismatch")
        return 1, manifest_hash
    try:
        manifest = json.loads(manifest_data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        failures.append("candidate screenshot manifest is invalid JSON")
        return 1, manifest_hash
    screenshots = manifest.get("screenshots", [])
    if len(screenshots) != 50:
        failures.append("candidate screenshot manifest count mismatch")
    query_count = 1
    for entry in screenshots:
        tree_data = git_blob(repo_root, CANDIDATE_COMMIT, entry.get("path", ""))
        query_count += 1
        if tree_data is None or sha256_bytes(tree_data) != entry.get("sha256"):
            failures.append(f"candidate screenshot blob mismatch: {entry.get('id')}")
    return query_count, manifest_hash


def validate_ready(
    repo_root: Path,
    ready: dict[str, Any],
    overlay: dict[str, bytes] | None,
    failures: list[str],
) -> None:
    require_equal(
        failures,
        "ready schema",
        ready.get("schema"),
        "companion.browser-owner-review-ready-checkonly.v1",
    )
    require_equal(failures, "ready status", ready.get("status"), "BROWSER_OWNER_REVIEW_READY")
    require_equal(failures, "ready default off", ready.get("default_off"), True)
    require_equal(failures, "ready URL", ready.get("url"), REVIEW_URL)
    checks = ready.get("checks")
    if not isinstance(checks, dict) or not checks or not all(checks.values()):
        failures.append("ready checks: every recorded check must be true")
    side_effects = ready.get("side_effect_counters", {})
    for key, value in side_effects.items():
        expected = 1 if key == "evidence_artifact_write" else 0
        require_equal(failures, f"ready side effect {key}", value, expected)
    owner = ready.get("owner_boundary", {})
    require_equal(failures, "ready owner pass claimed", owner.get("owner_pass_claimed"), False)
    require_equal(failures, "ready owner prompt invoked", owner.get("owner_prompt_invoked"), False)
    require_equal(failures, "ready owner result exists", owner.get("owner_result_exists"), False)

    bindings = ready.get("bindings", {})
    for group in ("accepted_identities", "accepted_source_assets"):
        entries = bindings.get(group)
        if not isinstance(entries, list) or not entries:
            failures.append(f"ready {group} must be a nonempty array")
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                failures.append(f"ready {group} entry must be an object")
                continue
            relative_path = str(entry.get("path", ""))
            try:
                observed_hash = sha256_bytes(read_bytes(repo_root, relative_path, overlay))
            except OSError:
                failures.append(f"ready bound file missing: {relative_path}")
                continue
            if observed_hash != entry.get("expected_sha256"):
                failures.append(f"ready bound file SHA mismatch: {relative_path}")
            require_equal(failures, f"ready binding match {relative_path}", entry.get("match"), True)


def evaluate(
    repo_root: Path,
    candidate_commit: str,
    overlay: dict[str, bytes] | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    failures: list[str] = []
    file_identities: list[dict[str, Any]] = []
    screenshot_observations: list[dict[str, Any]] = []
    git_query_count = 0

    code, stdout, _ = run_git(repo_root, "rev-parse", f"{candidate_commit}^{{commit}}")
    git_query_count += 1
    resolved_commit = stdout.decode("ascii", errors="replace").strip() if code == 0 else None
    require_equal(failures, "candidate commit argument", candidate_commit, CANDIDATE_COMMIT)
    require_equal(failures, "candidate commit object", resolved_commit, CANDIDATE_COMMIT)

    fixed_code, fixed_stdout, _ = run_git(
        repo_root, "rev-parse", f"{CANDIDATE_COMMIT}^{{commit}}"
    )
    git_query_count += 1
    fixed_resolved = (
        fixed_stdout.decode("ascii", errors="replace").strip()
        if fixed_code == 0
        else None
    )
    require_equal(failures, "fixed candidate object", fixed_resolved, CANDIDATE_COMMIT)

    parsed: dict[str, dict[str, Any] | None] = {}
    for file_id, (
        relative_path,
        expected_hash,
        candidate_tree_expected_hash,
    ) in BOUND_FILES.items():
        try:
            data = read_bytes(repo_root, relative_path, overlay)
            observed_hash = sha256_bytes(data)
            exists = True
        except OSError:
            data = b""
            observed_hash = None
            exists = False
        match = exists and observed_hash == expected_hash
        if not exists:
            failures.append(f"bound file missing: {file_id}")
        elif not match:
            failures.append(f"bound file SHA mismatch: {file_id}")
        tree_hash = None
        tree_match = None
        if candidate_tree_expected_hash is not None:
            tree_data = git_blob(repo_root, CANDIDATE_COMMIT, relative_path)
            git_query_count += 1
            tree_hash = sha256_bytes(tree_data) if tree_data is not None else None
            tree_match = tree_hash == candidate_tree_expected_hash
            if not tree_match:
                failures.append(f"candidate tree blob mismatch: {file_id}")
        file_identities.append(
            {
                "id": file_id,
                "path": relative_path,
                "expected_sha256": expected_hash,
                "observed_sha256": observed_hash,
                "match": match,
                "candidate_tree_bound": candidate_tree_expected_hash is not None,
                "candidate_tree_expected_sha256": candidate_tree_expected_hash,
                "candidate_tree_sha256": tree_hash,
                "candidate_tree_match": tree_match,
            }
        )
        if file_id in {
            "replay_result",
            "pixel_dom_route",
            "screenshot_manifest",
            "browser_owner_review_ready",
        }:
            parsed[file_id] = parse_json_bytes(file_id, data, failures) if exists else None

    page_tree_data = git_blob(repo_root, CANDIDATE_COMMIT, PAGE_PATH)
    git_query_count += 1
    page_tree_hash = sha256_bytes(page_tree_data) if page_tree_data is not None else None
    require_equal(
        failures,
        "candidate historical page blob",
        page_tree_hash,
        PAGE_CANDIDATE_TREE_SHA256,
    )

    replay = parsed.get("replay_result")
    pixel = parsed.get("pixel_dom_route")
    screenshot_manifest = parsed.get("screenshot_manifest")
    ready = parsed.get("browser_owner_review_ready")
    if replay is not None:
        validate_replay(replay, failures)
    if pixel is not None:
        validate_pixel_dom_route(pixel, failures)
    if screenshot_manifest is not None:
        validate_screenshots(
            repo_root,
            screenshot_manifest,
            overlay,
            failures,
            screenshot_observations,
        )
        candidate_screenshot_queries, candidate_screenshot_manifest_hash = (
            validate_candidate_screenshot_tree(repo_root, failures)
        )
        git_query_count += candidate_screenshot_queries
    else:
        candidate_screenshot_manifest_hash = None
    if ready is not None:
        validate_ready(repo_root, ready, overlay, failures)

    clean_receipt_identity: dict[str, Any]
    try:
        clean_receipt_bytes = read_bytes(
            repo_root, CLEAN_REPLAY_RECEIPT_PATH, overlay
        )
        clean_receipt_hash = sha256_bytes(clean_receipt_bytes)
        clean_receipt = parse_json_bytes(
            "clean replay receipt", clean_receipt_bytes, failures
        )
        clean_receipt_identity = {
            "path": CLEAN_REPLAY_RECEIPT_PATH,
            "expected_sha256": CLEAN_REPLAY_RECEIPT_SHA256,
            "observed_sha256": clean_receipt_hash,
            "match": clean_receipt_hash == CLEAN_REPLAY_RECEIPT_SHA256,
        }
        if clean_receipt_hash != CLEAN_REPLAY_RECEIPT_SHA256:
            failures.append("clean replay receipt SHA mismatch")
        if clean_receipt is not None:
            require_equal(
                failures,
                "clean replay status",
                clean_receipt.get("status"),
                "PASS_TWO_CLEAN_REPLAYS_BYTE_IDENTICAL",
            )
            require_equal(
                failures,
                "clean replay candidate",
                clean_receipt.get("candidate_commit"),
                CANDIDATE_COMMIT,
            )
            require_equal(
                failures,
                "clean replay page SHA",
                clean_receipt.get("page_sha256"),
                PAGE_SHA256,
            )
            require_equal(
                failures,
                "clean replay byte identity",
                clean_receipt.get("byte_identical"),
                True,
            )
    except OSError:
        clean_receipt_identity = {
            "path": CLEAN_REPLAY_RECEIPT_PATH,
            "expected_sha256": CLEAN_REPLAY_RECEIPT_SHA256,
            "observed_sha256": None,
            "match": False,
        }
        failures.append("clean replay receipt missing")

    owner_result_paths = [
        "docs/validation/companion-browser-visual-contract-comp-req-471/owner-review.json",
        f"{VALIDATION_DIR}/owner-review.json",
    ]
    owner_result_exists = [
        relative_path
        for relative_path in owner_result_paths
        if (repo_root / relative_path).is_file()
    ]
    if owner_result_exists:
        failures.append("owner result already exists; this machine gate cannot claim review readiness")

    failures = sorted(set(failures))
    return {
        "schema": "companion.browser-source-bound-tamper-gate.v1",
        "requirements": ["COMP-REQ-440", "COMP-REQ-441", "COMP-REQ-442", "COMP-REQ-471", "COMP-REQ-504"],
        "status": "PASS_SOURCE_BOUND_TAMPER_GATE" if not failures else "NO_GO",
        "candidate_commit": {
            "expected": CANDIDATE_COMMIT,
            "argument": candidate_commit,
            "resolved": resolved_commit,
            "match": candidate_commit == resolved_commit == CANDIDATE_COMMIT,
        },
        "accepted_page_binding": {
            "path": PAGE_PATH,
            "accepted_worktree_sha256": PAGE_SHA256,
            "candidate_tree_historical_sha256": PAGE_CANDIDATE_TREE_SHA256,
            "binding_policy": (
                "The accepted page predates the evidence commit as an owner dirty-tree "
                "source. The gate pins both the historical candidate blob and the exact "
                "accepted worktree content SHA; the page is never staged by this task."
            ),
        },
        "candidate_screenshot_manifest_sha256": candidate_screenshot_manifest_hash,
        "url": REVIEW_URL,
        "file_identities": file_identities,
        "clean_replay_receipt": clean_receipt_identity,
        "semantic_counts": {
            "matrix_rows": len(pixel.get("matrix", [])) if pixel else 0,
            "state_snapshots": len(pixel.get("states", [])) if pixel else 0,
            "screenshots": len(screenshot_observations),
            "unique_pointer_records": (
                len({row.get("id") for row in pixel.get("matrix", [])})
                if pixel
                else 0
            ),
            "active_200x200_surfaces": (
                pixel.get("invariants", {}).get("primary_screen_count")
                if pixel
                else None
            ),
            "route_menu_entries": (
                replay.get("totals", {}).get("route_menu_entries")
                if replay
                else None
            ),
            "route_recording_entries": (
                replay.get("totals", {}).get("route_recording_entries")
                if replay
                else None
            ),
            "http_404": (
                replay.get("totals", {}).get("http_404_count")
                if replay
                else None
            ),
            "stale_layers": (
                replay.get("totals", {}).get("stale_layer_count")
                if replay
                else None
            ),
            "conflicting_overlap": (
                replay.get("totals", {}).get("conflicting_surface_overlap_count")
                if replay
                else None
            ),
            "out_of_bounds": (
                replay.get("totals", {}).get("out_of_bounds_count")
                if replay
                else None
            ),
            "microphone_requests": (
                replay.get("totals", {}).get("microphone_requests")
                if replay
                else None
            ),
        },
        "screenshot_observations": screenshot_observations,
        "owner_boundary": {
            "owner_prompt_invoked": False,
            "owner_pass_claimed": False,
            "owner_result_exists": bool(owner_result_exists),
            "owner_result_paths_checked": owner_result_paths,
        },
        "failed_checks": failures,
        "side_effect_counters": {
            "server_start": 0,
            "browser_start": 0,
            "popup": 0,
            "operator_prompt": 0,
            "microphone_permission_request": 0,
            "hardware": 0,
            "lower_write": 0,
            "platform_write": 0,
            "production_write": 0,
            "registry_write": 0,
            "persistent_process_start": 0,
            "read_only_git_queries": git_query_count,
            "evidence_artifact_write": 0,
        },
    }


def write_result(path: Path, result: dict[str, Any]) -> None:
    output = copy.deepcopy(result)
    output["side_effect_counters"]["evidence_artifact_write"] = 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(output))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--candidate-commit", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = evaluate(Path(args.repo_root), args.candidate_commit)
    write_result(Path(args.output), result)
    print(result["status"])
    return 0 if result["status"] == "PASS_SOURCE_BOUND_TAMPER_GATE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
