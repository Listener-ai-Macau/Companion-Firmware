#!/usr/bin/env python3
"""Fail-closed source/artifact gate for the COMP-REQ-533/534 successor."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


MAIN_BASE_COMMIT = "4338f0c1614a58a334008c992c9bb61a73071718"
SOURCE_COMMIT = MAIN_BASE_COMMIT
TOOL_COMMIT = MAIN_BASE_COMMIT
PAGE_PATH = (
    "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/"
    "candidate/wb55-browser-parity-attempt-01/index.html"
)
PAGE_SHA256 = "8F8FC05C5DAA3A95C7A2E80D677B56A831CF620A752EABB1DCB535F01705AB9D"
PAGE_COMMITTED_SHA256 = PAGE_SHA256
PAGE_GIT_BLOB = "fdf6c7c8e9ad7293dfd1115e7f42cca015d9a15e"
URL = "http://127.0.0.1:4173/" + PAGE_PATH
VALIDATION_DIR = (
    "docs/validation/"
    "companion-browser-three-wave-state-view-successor-comp-req-533-534"
)
OWNER_RESULT_PATH = f"{VALIDATION_DIR}/owner-review.json"

BOUND_FILES = {
    "focused_tool": (
        "tools/faraday_upper_art/"
        "verify_companion_browser_three_wave_state_view_comp_req_533_534.mjs",
        "F6C43D2D4C7F893D5B59013A3FB4FB679C7F3ED3448D7290EC2202C3E5FA21D4",
        "00e9fabe1eb3fba01a886016d282debf30bb5b83",
    ),
    "replay_tool": (
        "tools/faraday_upper_art/"
        "replay_companion_browser_three_wave_state_view_comp_req_533_534.mjs",
        "17BEF0230EA0E0FD715A6B0212BCF5A421BA5041AC950DA4EE6F525999783ACD",
        "b3d83b5e085c4e765fc763c9f799b4ff2fc35a5c",
    ),
    "determinism_tool": (
        "tools/faraday_upper_art/"
        "run_companion_browser_three_wave_state_view_determinism_comp_req_533_534.py",
        "40FBE5CC57CBC5ECAF84EB0A311D7FE7AAD5203CE82CF8F6BBF64E346145147A",
        "0e18d6b78682cc07085f92283fd4f871d0be0db2",
    ),
    "before_oracle": (
        f"{VALIDATION_DIR}/before-fix/geometry-temporal-state-oracle.json",
        "D6C6D0952BD7E985467E629F17AECEE216C23E46BDED86ACC1419B16EAE6F356",
        "3fa1c51c049516ab6d098da85ec48d9579f3d45c",
    ),
    "after_oracle": (
        f"{VALIDATION_DIR}/after-fix/geometry-temporal-state-oracle.json",
        "9FC4A390A71A431029A3B50E6DC117D441D832694E7BDEA5E53A11A306DE7626",
        "7797edcfc3bba8fd7679e60bc2e3fe496cc4bf0b",
    ),
    "replay": (
        f"{VALIDATION_DIR}/determinism-run/browser-replay-result.json",
        "842073FF357B7ADF03775B432E87C67B45824F6EC271FE59D5B7CE46A05CF94C",
        "6ebbf0882fcc794562d1f5d07e29aae894b15b8d",
    ),
    "pixel": (
        f"{VALIDATION_DIR}/determinism-run/pixel-dom-route-artifact.json",
        "21CA3E864CE8523C497F38ABC758B1ADE34BB92EF755F63D9DFA2FC7A4F5B4F6",
        "f29e86ebbe53e1e27759be65d5c3cfa5743f2b4b",
    ),
    "screenshots": (
        f"{VALIDATION_DIR}/determinism-run/screenshot-manifest.json",
        "4806A36D7E0BA0C456CA588888E237911D8D5B46B55F0B9E1B6DA238976A8BC5",
        "bbe8db4070b82a1c034d98e0e3edf55b37d16e62",
    ),
    "determinism": (
        f"{VALIDATION_DIR}/deterministic-replay-receipt.json",
        "7A65317B4FF4296543AF94D0D16662C6D4464726328BB9F172BE0ACFEA3674A7",
        "4554fc310726fadd567d98606b5f206ff4500810",
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


def canonical_lf_bytes(data: bytes) -> bytes:
    normalized = data.replace(b"\r\n", b"\n")
    if b"\r" in normalized:
        raise ValueError("text contains a bare carriage return")
    return normalized


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")


def read_bytes(
    root: Path,
    relative: str,
    overlay: dict[str, bytes] | None,
) -> bytes:
    key = relative.replace("\\", "/")
    if overlay is not None and key in overlay:
        return overlay[key]
    return (root / key).read_bytes()


def parse_json(
    failures: list[str],
    label: str,
    data: bytes,
) -> dict[str, Any] | None:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        failures.append(f"{label}: invalid JSON ({exc.__class__.__name__})")
        return None
    if not isinstance(value, dict):
        failures.append(f"{label}: root is not an object")
        return None
    return value


def git_text(root: Path, *args: str) -> str | None:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip() if result.returncode == 0 else None


def git_bytes(root: Path, *args: str) -> bytes | None:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
    )
    return result.stdout if result.returncode == 0 else None


def git_ok(root: Path, *args: str) -> bool:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
    ).returncode == 0


def require(
    failures: list[str],
    label: str,
    observed: Any,
    expected: Any,
) -> None:
    if observed != expected:
        stable_expected = sorted(expected) if isinstance(expected, set) else expected
        stable_observed = sorted(observed) if isinstance(observed, set) else observed
        failures.append(
            f"{label}: expected {stable_expected!r}, "
            f"observed {stable_observed!r}"
        )


def expected_matrix_ids() -> set[str]:
    return {
        f"{viewport}-{pointer}-{scenario}"
        for viewport in ("desktop", "mobile")
        for pointer in ("mouse", "touch", "pen")
        for scenario in SCENARIOS
    }


def evaluate(
    root: Path,
    overlay: dict[str, bytes] | None = None,
    source_commit: str = SOURCE_COMMIT,
    tool_commit: str = TOOL_COMMIT,
) -> dict[str, Any]:
    failures: list[str] = []
    identities: list[dict[str, Any]] = []

    require(
        failures,
        "main source commit",
        git_text(root, "rev-parse", f"{source_commit}^{{commit}}"),
        MAIN_BASE_COMMIT,
    )
    require(
        failures,
        "main tool commit",
        git_text(root, "rev-parse", f"{tool_commit}^{{commit}}"),
        MAIN_BASE_COMMIT,
    )
    if not git_ok(root, "merge-base", "--is-ancestor", MAIN_BASE_COMMIT, "HEAD"):
        failures.append("exact main base is not an ancestor of HEAD")
    require(
        failures,
        "page git blob",
        git_text(root, "rev-parse", f"{source_commit}:{PAGE_PATH}"),
        PAGE_GIT_BLOB,
    )
    committed_page = git_bytes(root, "cat-file", "blob", PAGE_GIT_BLOB)
    require(
        failures,
        "committed page sha256",
        sha256_bytes(committed_page) if committed_page is not None else None,
        PAGE_COMMITTED_SHA256,
    )
    page_raw = read_bytes(root, PAGE_PATH, overlay)
    try:
        page = canonical_lf_bytes(page_raw)
    except ValueError as exc:
        failures.append(f"page canonical LF: {exc}")
        page = page_raw
    require(failures, "page canonical sha256", sha256_bytes(page), PAGE_SHA256)
    require(
        failures,
        "page checkout git blob",
        git_text(root, "hash-object", "--path", PAGE_PATH, PAGE_PATH),
        PAGE_GIT_BLOB,
    )
    page_text = page.decode("utf-8", errors="replace")
    for token in (
        "stepMs:480",
        "arcIds:['wave_a','wave_b','wave_c']",
        "scheduler:'bounded_setTimeout'",
        "interpolation:'none'",
        "dataset.stateSource='naturalState'",
        "__expressionStateEdgeAudit",
        "__expressionOpticalContractState",
    ):
        if token not in page_text:
            failures.append(f"page contract token missing: {token}")
    if "getUserMedia(" in page_text:
        failures.append("page contains microphone request")

    parsed: dict[str, dict[str, Any]] = {}
    for name, (relative, expected_sha, expected_blob) in BOUND_FILES.items():
        raw_data = read_bytes(root, relative, overlay)
        try:
            data = canonical_lf_bytes(raw_data)
        except ValueError as exc:
            failures.append(f"{name} canonical LF: {exc}")
            data = raw_data
        observed_sha = sha256_bytes(data)
        require(failures, f"{name} canonical sha256", observed_sha, expected_sha)
        require(
            failures,
            f"{name} main git blob",
            git_text(root, "rev-parse", f"{MAIN_BASE_COMMIT}:{relative}"),
            expected_blob,
        )
        require(
            failures,
            f"{name} checkout git blob",
            git_text(root, "hash-object", "--path", relative, relative),
            expected_blob,
        )
        blob_data = git_bytes(root, "cat-file", "blob", expected_blob)
        require(
            failures,
            f"{name} git blob canonical sha256",
            sha256_bytes(blob_data) if blob_data is not None else None,
            expected_sha,
        )
        if relative.endswith(".json"):
            value = parse_json(failures, name, data)
            if value is not None:
                parsed[name] = value
        identities.append(
            {
                "canonical_bytes": len(data),
                "checkout_bytes": len(raw_data),
                "git_blob": expected_blob,
                "identity_basis": "git_blob_plus_canonical_lf_sha256",
                "id": name,
                "path": relative,
                "canonical_sha256": observed_sha,
            }
        )

    before = parsed.get("before_oracle", {})
    after = parsed.get("after_oracle", {})
    require(failures, "before status", before.get("status"), "NO_GO")
    before_failed = set(before.get("failed_checks", []))
    for check in (
        "exactly_three_pixel_arcs_every_step",
        "every_arc_convex_toward_listening_point",
        "physical_step_contract_480_ms",
        "state_view_uses_single_runtime_source",
    ):
        if check not in before_failed:
            failures.append(f"before oracle did not fail {check}")
    require(failures, "after status", after.get("status"), "PASS")
    require(failures, "after failed checks", after.get("failed_checks"), [])
    after_checks = after.get("checks", {})
    if not after_checks or not all(after_checks.values()):
        failures.append("after focused checks are not all true")
    require(failures, "focused check count", len(after_checks), 23)
    observed = after.get("observed", {})
    require(failures, "observed wave step", observed.get("contractStepMs"), 480)
    require(
        failures,
        "observed arc identities",
        observed.get("arcIdentities"),
        ["wave_a", "wave_b", "wave_c"],
    )
    steps = observed.get("steps", [])
    require(failures, "observed wave state count", len(steps), 4)
    for index, step in enumerate(steps):
        require(
            failures,
            f"wave state {index} runtime arc count",
            step.get("runtime", {}).get("arc_count"),
            3,
        )
        components = step.get("components", [])
        require(
            failures,
            f"wave state {index} pixel component count",
            len(components),
            3,
        )
        if not all(row.get("convex_toward_listening") is True for row in components):
            failures.append(f"wave state {index} contains outward pixel arc")
    transitions = observed.get("identityTransitions", [])
    require(failures, "wave identity transition count", len(transitions), 9)
    if any(
        row.get("kind") not in ("inward", "spawn_after_absorption")
        for row in transitions
    ):
        failures.append("wave identity transition contains outward/wrap motion")
    state_view = observed.get("stateView", {})
    require(
        failures,
        "state view source identity",
        state_view.get("source_identity"),
        "naturalState",
    )
    require(failures, "state view outside screen", state_view.get("outside_screen"), True)
    edges = observed.get("edgeChecks", {})
    require(failures, "legal edge count", len(edges.get("legal", [])), 7)
    require(failures, "forged edge count", len(edges.get("forged", [])), 5)
    if not all(row.get("allowed") is True for row in edges.get("legal", [])):
        failures.append("legal edge rejected")
    if not all(row.get("allowed") is False for row in edges.get("forged", [])):
        failures.append("forged edge accepted")
    optical = observed.get("optical", {})
    require(failures, "optical sample count", len(optical.get("samples", [])), 7)
    require(failures, "optical anchor", optical.get("anchor"), {"x": 100, "y": 135})
    boundary = observed.get("firstObservedChangeMs")
    if not isinstance(boundary, (int, float)) or not 430 <= boundary <= 650:
        failures.append(f"observed 480ms boundary out of range: {boundary!r}")

    replay = parsed.get("replay", {})
    require(
        failures,
        "replay status",
        replay.get("status"),
        "PASS_BROWSER_THREE_WAVE_STATE_VIEW_MACHINE_REPLAY",
    )
    require(failures, "replay totals", replay.get("totals"), EXPECTED_TOTALS)
    replay_checks = replay.get("checks", {})
    if len(replay_checks) != 25 or not all(replay_checks.values()):
        failures.append("replay checks are not 25/25 true")

    pixel = parsed.get("pixel", {})
    require(failures, "pixel status", pixel.get("status"), "PASS")
    matrix = pixel.get("matrix", [])
    require(failures, "matrix row count", len(matrix), 42)
    matrix_ids = {row.get("id") for row in matrix if isinstance(row, dict)}
    require(failures, "matrix identities", matrix_ids, expected_matrix_ids())
    if any(row.get("status") != "PASS" for row in matrix if isinstance(row, dict)):
        failures.append("matrix contains non-PASS row")
    states = pixel.get("states", [])
    require(failures, "state snapshot count", len(states), 258)
    invariants = pixel.get("invariants", {})
    for name in (
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
        require(failures, f"pixel invariant {name}", invariants.get(name), 0)
    require(failures, "primary screen count", invariants.get("primary_screen_count"), 1)

    screenshots = parsed.get("screenshots", {})
    require(failures, "screenshot status", screenshots.get("status"), "PASS")
    rows = screenshots.get("screenshots", [])
    require(failures, "screenshot count", len(rows), 50)
    seen_paths: set[str] = set()
    for row in rows:
        relative = row.get("path", "")
        if relative in seen_paths:
            failures.append(f"duplicate screenshot path: {relative}")
            continue
        seen_paths.add(relative)
        data = read_bytes(root, relative, overlay)
        require(
            failures,
            f"screenshot {relative}",
            sha256_bytes(data),
            row.get("sha256"),
        )

    determinism = parsed.get("determinism", {})
    require(
        failures,
        "determinism status",
        determinism.get("status"),
        "PASS_TWO_CLEAN_REPLAYS_BYTE_IDENTICAL",
    )
    require(failures, "determinism flag", determinism.get("byte_identical"), True)
    require(
        failures,
        "determinism run equality",
        determinism.get("run_a"),
        determinism.get("run_b"),
    )
    require(failures, "determinism run count", determinism.get("run_count"), 2)

    for relative in (
        OWNER_RESULT_PATH,
        f"{VALIDATION_DIR}/owner-review.raw.json",
        f"{VALIDATION_DIR}/owner-review.note.txt",
        f"{VALIDATION_DIR}/.owner-review.prompt-active.lock",
    ):
        if (overlay and relative in overlay) or (root / relative).exists():
            failures.append(f"owner lifecycle file exists before review: {relative}")

    return {
        "schema": "companion.browser-three-wave-state-view-source-bound.v1",
        "requirements": ["COMP-REQ-521", "COMP-REQ-533", "COMP-REQ-534"],
        "status": "MACHINE_READY" if not failures else "NO_GO",
        "failed_checks": failures,
        "source": {
            "main_base_commit": MAIN_BASE_COMMIT,
            "identity_basis": "git_blob_plus_canonical_lf_sha256",
            "page_path": PAGE_PATH,
            "page_canonical_sha256": PAGE_SHA256,
            "page_git_blob": PAGE_GIT_BLOB,
        },
        "url": URL,
        "identities": identities,
        "proof": {
            "focused_checks": len(after_checks),
            "matrix_rows": len(matrix),
            "state_snapshots": len(states),
            "screenshots": len(rows),
            "natural_bridge_commits": replay.get("totals", {}).get(
                "natural_bridge_commits"
            ),
            "natural_bridge_ordered": replay.get("totals", {}).get(
                "natural_bridge_ordered"
            ),
            "clean_replays": determinism.get("run_count"),
            "byte_identical": determinism.get("byte_identical"),
        },
        "owner_gate": {
            "status": "PENDING",
            "result_path": OWNER_RESULT_PATH,
            "may_claim_owner_pass": False,
        },
        "side_effect_counters": {
            "server_start": 0,
            "visible_browser": 0,
            "popup": 0,
            "operator_prompt": 0,
            "microphone_permission_request": 0,
            "hardware": 0,
            "lower_write": 0,
            "platform_write": 0,
            "production_write": 0,
            "registry_write": 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    output = (root / args.output).resolve()
    output.relative_to(root / VALIDATION_DIR)
    result = evaluate(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_bytes(result))
    print(json.dumps({
        "output": output.relative_to(root).as_posix(),
        "canonical_sha256": sha256_bytes(
            canonical_lf_bytes(output.read_bytes())
        ),
        "status": result["status"],
        "failed_check_count": len(result["failed_checks"]),
    }))
    return 0 if result["status"] == "MACHINE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
