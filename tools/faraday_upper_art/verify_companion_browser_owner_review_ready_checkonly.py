#!/usr/bin/env python3
"""Offline CheckOnly gate for the accepted Companion browser overall page."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image


PAGE_REPO_PATH = (
    "docs/art/iterations/"
    "companion-pet-expression-v9-two-track-rig-v7/"
    "candidate/wb55-browser-parity-attempt-01/index.html"
)
PAGE_SHA256 = (
    "BAE21BCCC7BB5FAD4A0922D5E9C42FCB25EF58DD7B8102A7C72656F7B700CF5E"
)
OVERALL_URL = (
    "http://127.0.0.1:4173/"
    + PAGE_REPO_PATH
)
VALIDATION_REPO_PATH = (
    "docs/validation/"
    "companion-browser-owner-review-ready-comp-req-471"
)
ACCEPTED_BINDINGS = {
    (
        "docs/validation/companion-browser-visual-contract-comp-req-471/"
        "UPPER_MACHINE_READY.json"
    ): "EAD7000FEB32CD7915FEAD82A49D23FD66755412AEDFA53B4B7A264CABA3BB69",
    (
        "docs/validation/companion-browser-visual-contract-comp-req-471/"
        "machine-result.json"
    ): "6A7EDAC4A9624842B154B717C090441E745AC6F65F8E73BC235E8E3C16D11EBD",
    (
        "docs/validation/companion-browser-visual-contract-comp-req-471/"
        "measured-diagnostic.json"
    ): "652C33E7BFB155974FD369DB069800E14595C26F5F1D7B6A7322ED30320CCA76",
    (
        "docs/validation/companion-browser-visual-contract-comp-req-471/"
        "browser-capture/capture-manifest.json"
    ): "1BEA10C8B988F72F48886012859F1D6C8801B15AFA18E89171235B7E33D2C815",
    (
        "docs/validation/companion-browser-visual-contract-comp-req-471/"
        "pointer-contract/touch-pointer-contract-result.json"
    ): "082344F03017DC54E0A385E5CFF8BB7F4031889A602476FFD2589B130CFFE09F",
    (
        "docs/validation/companion-browser-visual-contract-comp-req-471/"
        "owner-review-checkonly.json"
    ): "21FCE148BBD11C68074F98EE10E8F1A75A0DD4D86FAC4F65EE7CB03CFFABDCC7",
    (
        "docs/validation/companion-browser-visual-contract-comp-req-471/"
        "owner-review-scope.json"
    ): "245B8BDB94A00A23224CF1E9A7F43CA65936CCC16518D3067D48BD98A5E61D80",
    (
        "docs/validation/"
        "companion-pet-special-system-owner-acceptance-20260717.json"
    ): "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes())


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not a JSON object")
    return value


def resolve_inside(root: Path, value: Path) -> Path:
    path = value.resolve() if value.is_absolute() else (root / value).resolve()
    path.relative_to(root)
    return path


def identity(
    repo_root: Path,
    repo_path: str,
    expected_sha256: str,
) -> dict[str, Any]:
    path = resolve_inside(repo_root, Path(repo_path))
    observed = file_sha256(path) if path.is_file() else None
    return {
        "bytes": path.stat().st_size if path.is_file() else None,
        "exists": path.is_file(),
        "expected_sha256": expected_sha256.upper(),
        "match": observed == expected_sha256.upper(),
        "observed_sha256": observed,
        "path": repo_path,
    }


def png_metrics(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        composed = Image.alpha_composite(background, rgba).convert("RGB")
        width, height = composed.size
        pixels = composed.load()
        black = 0
        min_x = width
        min_y = height
        max_x = -1
        max_y = -1
        for y_value in range(height):
            for x_value in range(width):
                red, green, blue = pixels[x_value, y_value]
                if red >= 128 or green >= 128 or blue >= 128:
                    continue
                black += 1
                min_x = min(min_x, x_value)
                min_y = min(min_y, y_value)
                max_x = max(max_x, x_value)
                max_y = max(max_y, y_value)
    return {
        "black_bounds": (
            {
                "max_x": max_x,
                "max_y": max_y,
                "min_x": min_x,
                "min_y": min_y,
            }
            if black
            else None
        ),
        "black_pixels": black,
        "edge_touch": (
            {
                "bottom": max_y == height - 1,
                "left": min_x == 0,
                "right": max_x == width - 1,
                "top": min_y == 0,
            }
            if black
            else None
        ),
        "height": height,
        "width": width,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--replay-tool", type=Path, required=True)
    parser.add_argument("--expected-replay-tool-sha256", required=True)
    parser.add_argument("--replay-result", type=Path, required=True)
    parser.add_argument("--expected-replay-result-sha256", required=True)
    parser.add_argument("--pixel-dom-route", type=Path, required=True)
    parser.add_argument("--expected-pixel-dom-route-sha256", required=True)
    parser.add_argument("--screenshot-manifest", type=Path, required=True)
    parser.add_argument("--expected-screenshot-manifest-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    validation_root = resolve_inside(repo_root, Path(VALIDATION_REPO_PATH))
    replay_tool = resolve_inside(repo_root, args.replay_tool)
    replay_result_path = resolve_inside(repo_root, args.replay_result)
    pixel_dom_route_path = resolve_inside(repo_root, args.pixel_dom_route)
    screenshot_manifest_path = resolve_inside(
        repo_root, args.screenshot_manifest
    )
    output_path = resolve_inside(repo_root, args.output)
    for path in (
        replay_result_path,
        pixel_dom_route_path,
        screenshot_manifest_path,
        output_path,
    ):
        path.relative_to(validation_root)

    input_bindings = {
        replay_tool.relative_to(repo_root).as_posix(): (
            args.expected_replay_tool_sha256
        ),
        replay_result_path.relative_to(repo_root).as_posix(): (
            args.expected_replay_result_sha256
        ),
        pixel_dom_route_path.relative_to(repo_root).as_posix(): (
            args.expected_pixel_dom_route_sha256
        ),
        screenshot_manifest_path.relative_to(repo_root).as_posix(): (
            args.expected_screenshot_manifest_sha256
        ),
        **ACCEPTED_BINDINGS,
    }
    identity_rows = [
        identity(repo_root, repo_path, digest)
        for repo_path, digest in sorted(input_bindings.items())
    ]

    replay = load_json(replay_result_path)
    pixel_dom_route = load_json(pixel_dom_route_path)
    screenshot_manifest = load_json(screenshot_manifest_path)
    capture_manifest_path = resolve_inside(
        repo_root,
        Path(
            "docs/validation/"
            "companion-browser-visual-contract-comp-req-471/"
            "browser-capture/capture-manifest.json"
        ),
    )
    capture_manifest = load_json(capture_manifest_path)
    prior_checkonly_path = resolve_inside(
        repo_root,
        Path(
            "docs/validation/"
            "companion-browser-visual-contract-comp-req-471/"
            "owner-review-checkonly.json"
        ),
    )
    prior_checkonly = load_json(prior_checkonly_path)

    inherited_identity_rows = []
    for row in prior_checkonly.get("readiness", {}).get("identities", []):
        inherited_identity_rows.append(
            identity(
                repo_root,
                str(row.get("path", "")),
                str(row.get("expected_sha256", "")),
            )
        )
    for script in prior_checkonly.get("scripts", {}).values():
        inherited_identity_rows.append(
            identity(
                repo_root,
                str(script.get("path", "")),
                str(script.get("sha256", "")),
            )
        )

    source_asset_rows = []
    for source in capture_manifest.get("source_assets", []):
        source_asset_rows.append(
            {
                "role": source.get("role"),
                **identity(
                    repo_root,
                    str(source.get("repo_path", "")),
                    str(source.get("sha256", "")),
                ),
            }
        )

    screenshot_rows = []
    screenshot_failures = []
    for row in screenshot_manifest.get("screenshots", []):
        repo_path = str(row.get("path", ""))
        path = resolve_inside(repo_root, Path(repo_path))
        observed_sha = file_sha256(path) if path.is_file() else None
        metrics = png_metrics(path) if path.is_file() else None
        expected_size = (
            {"width": 1280, "height": 900}
            if row.get("id") == "desktop-layout"
            else {"width": 390, "height": 844}
            if row.get("id") == "mobile-layout"
            else {"width": 200, "height": 200}
        )
        passed = bool(
            observed_sha == row.get("sha256")
            and metrics
            and metrics["width"] == expected_size["width"]
            and metrics["height"] == expected_size["height"]
            and metrics["black_pixels"] > 0
            and metrics["black_bounds"]
            and 0 <= metrics["black_bounds"]["min_x"]
            <= metrics["black_bounds"]["max_x"] < metrics["width"]
            and 0 <= metrics["black_bounds"]["min_y"]
            <= metrics["black_bounds"]["max_y"] < metrics["height"]
        )
        if not passed:
            screenshot_failures.append(repo_path)
        screenshot_rows.append(
            {
                "expected_sha256": row.get("sha256"),
                "id": row.get("id"),
                "match": passed,
                "observed_sha256": observed_sha,
                "path": repo_path,
                "pixel_measurement": metrics,
            }
        )

    matrix = pixel_dom_route.get("matrix", [])
    states = pixel_dom_route.get("states", [])
    matrix_exact = bool(
        len(matrix) == 42
        and all(
            row.get("status") == "PASS"
            and row.get("document_requests") == 1
            and row.get("errors") == []
            for row in matrix
        )
    )
    state_failures = []
    for row in states:
        contract = row.get("contract", {})
        dom = row.get("dom", {})
        pixel = row.get("pixel", {})
        route = row.get("route", {})
        mode = contract.get("mode")
        expected = (
            {"face": 0, "gaze": 0, "highlight": 0, "menu": 1}
            if mode == "menu"
            else {"face": 1, "gaze": 1, "highlight": 1, "menu": 0}
        )
        passed = bool(
            mode in {"expression", "menu", "recording"}
            and dom.get("expected") == expected
            and dom.get("face_count") == expected["face"]
            and dom.get("gaze_count") == expected["gaze"]
            and dom.get("highlight_layer_count") == expected["highlight"]
            and dom.get("menu_count") == expected["menu"]
            and dom.get("primary_screen_count") == 1
            and dom.get("gaze_node_count") == 1
            and dom.get("menu_node_count") == 1
            and dom.get("conflict_count") == 0
            and dom.get("debug_visible") == []
            and dom.get("out_of_bounds") == []
            and dom.get("stage_width") == 200
            and dom.get("stage_height") == 200
            and dom.get("stage_center_delta_px", 99) <= 1
            and pixel.get("black_pixels", 0) > 0
            and pixel.get("outside_black_pixels") == 0
            and route.get("pathname") == f"/{PAGE_REPO_PATH}"
            and route.get("hash")
            == ("#menu" if mode == "menu" else "#expression")
        )
        if not passed:
            state_failures.append(str(row.get("id")))

    totals = replay.get("totals", {})
    replay_counters_exact = totals == {
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
    replay_side_effects = replay.get("side_effect_counters", {})
    replay_side_effects_exact = bool(
        replay_side_effects.get("browser_processes") == 1
        and replay_side_effects.get("server_start") == 0
        and replay_side_effects.get("owner_prompt") == 0
        and replay_side_effects.get("owner_result_write") == 0
        and replay_side_effects.get("microphone_permission_requests") == 0
        and all(
            replay_side_effects.get(key) == 0
            for key in (
                "hardware",
                "lower_write",
                "platform_write",
                "production_write",
                "registry_write",
            )
        )
    )
    owner_result_candidates = [
        validation_root / "owner-review.json",
        resolve_inside(
            repo_root,
            Path(
                "docs/validation/"
                "companion-browser-visual-contract-comp-req-471/"
                "owner-review.json"
            ),
        ),
    ]
    checks = {
        "accepted_identity_chain_exact": all(
            row["match"] for row in identity_rows
        ),
        "inherited_owner_review_bindings_exact": bool(
            len(inherited_identity_rows) == 16
            and all(row["match"] for row in inherited_identity_rows)
        ),
        "accepted_source_assets_15_of_15": bool(
            len(source_asset_rows) == 15
            and all(row["match"] for row in source_asset_rows)
        ),
        "actual_single_overall_url_exact": (
            replay.get("page", {}).get("url") == OVERALL_URL
            and replay.get("page", {}).get("repo_path") == PAGE_REPO_PATH
            and replay.get("page", {}).get("observed_sha256") == PAGE_SHA256
        ),
        "replay_status_and_all_checks_pass": bool(
            replay.get("status")
            == "PASS_BROWSER_OWNER_REVIEW_MACHINE_REPLAY"
            and replay.get("checks")
            and all(replay["checks"].values())
        ),
        "replay_totals_exact": replay_counters_exact,
        "replay_side_effect_boundary_exact": replay_side_effects_exact,
        "pixel_dom_route_matrix_42_of_42": matrix_exact,
        "pixel_dom_route_states_192_of_192": bool(
            len(states) == 192 and not state_failures
        ),
        "screenshots_50_of_50_rehashed_and_nonblank": bool(
            len(screenshot_rows) == 50 and not screenshot_failures
        ),
        "screenshot_manifest_bound_to_page": (
            screenshot_manifest.get("accepted_page_sha256") == PAGE_SHA256
            and screenshot_manifest.get("status") == "PASS"
        ),
        "deterministic_rerun_exact_hashes": bool(
            file_sha256(replay_result_path)
            == args.expected_replay_result_sha256.upper()
            and file_sha256(pixel_dom_route_path)
            == args.expected_pixel_dom_route_sha256.upper()
            and file_sha256(screenshot_manifest_path)
            == args.expected_screenshot_manifest_sha256.upper()
        ),
        "prior_checkonly_was_zero_side_effect": (
            prior_checkonly.get("counters")
            == {
                "browser": 0,
                "hardware": 0,
                "popup": 0,
                "process": 0,
                "write": 0,
            }
        ),
        "owner_result_absent_and_owner_pass_not_claimed": all(
            not path.exists() for path in owner_result_candidates
        ),
    }
    status = (
        "BROWSER_OWNER_REVIEW_READY"
        if all(checks.values())
        else "NO_GO"
    )
    replay_tool_rel = replay_tool.relative_to(repo_root).as_posix()
    output_rel = output_path.relative_to(repo_root).as_posix()
    checkonly_rel = (
        Path(__file__).resolve().relative_to(repo_root).as_posix()
    )
    artifact = {
        "bindings": {
            "accepted_identities": identity_rows,
            "accepted_source_assets": source_asset_rows,
            "inherited_owner_review_identities": inherited_identity_rows,
            "replay_tool": {
                "expected_sha256": (
                    args.expected_replay_tool_sha256.upper()
                ),
                "observed_sha256": file_sha256(replay_tool),
                "path": replay_tool.relative_to(repo_root).as_posix(),
            },
        },
        "checks": checks,
        "commands": {
            "checkonly": [
                "python",
                "-B",
                checkonly_rel,
                "--repo-root",
                ".",
                "--replay-tool",
                replay_tool_rel,
                "--expected-replay-tool-sha256",
                args.expected_replay_tool_sha256.upper(),
                "--replay-result",
                replay_result_path.relative_to(repo_root).as_posix(),
                "--expected-replay-result-sha256",
                args.expected_replay_result_sha256.upper(),
                "--pixel-dom-route",
                pixel_dom_route_path.relative_to(repo_root).as_posix(),
                "--expected-pixel-dom-route-sha256",
                args.expected_pixel_dom_route_sha256.upper(),
                "--screenshot-manifest",
                screenshot_manifest_path.relative_to(repo_root).as_posix(),
                "--expected-screenshot-manifest-sha256",
                args.expected_screenshot_manifest_sha256.upper(),
                "--output",
                output_rel,
            ],
            "machine_replay": [
                "node",
                replay_tool_rel,
                VALIDATION_REPO_PATH,
            ],
        },
        "default_off": True,
        "failed_checks": sorted(
            name for name, passed in checks.items() if not passed
        ),
        "machine_replay": {
            "pixel_dom_route_sha256": file_sha256(pixel_dom_route_path),
            "replay_result_sha256": file_sha256(replay_result_path),
            "screenshot_manifest_sha256": file_sha256(
                screenshot_manifest_path
            ),
        },
        "owner_boundary": {
            "owner_pass_claimed": False,
            "owner_prompt_invoked": False,
            "owner_result_exists": any(
                path.exists() for path in owner_result_candidates
            ),
            "remaining_gate": (
                "One canonical browser owner review of the existing overall "
                "URL; this CheckOnly does not authorize or invoke it."
            ),
        },
        "pixel_dom_route_failures": state_failures,
        "requirements": [
            "COMP-REQ-440",
            "COMP-REQ-441",
            "COMP-REQ-442",
            "COMP-REQ-471",
        ],
        "schema": "companion.browser-owner-review-ready-checkonly.v1",
        "screenshot_failures": screenshot_failures,
        "screenshot_pixel_measurements": screenshot_rows,
        "side_effect_counters": {
            "browser": 0,
            "evidence_artifact_write": 1,
            "external_process": 0,
            "hardware": 0,
            "lower_write": 0,
            "microphone_permission_request": 0,
            "owner_prompt": 0,
            "owner_result_write": 0,
            "platform_write": 0,
            "production_write": 0,
            "registry_write": 0,
            "server_probe": 0,
            "server_start": 0,
        },
        "status": status,
        "url": OVERALL_URL,
        "verifier": {
            "path": checkonly_rel,
            "sha256": file_sha256(Path(__file__).resolve()),
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_bytes(artifact))
    print(
        json.dumps(
            {
                "artifact_sha256": file_sha256(output_path),
                "failed_checks": artifact["failed_checks"],
                "status": status,
            },
            sort_keys=True,
        )
    )
    return 0 if status == "BROWSER_OWNER_REVIEW_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
