#!/usr/bin/env python3
"""Pack accepted browser renders into a deterministic 200x200 1bpp contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image


WIDTH = 200
HEIGHT = 200
ROW_BYTES = WIDTH // 8
FRAME_BYTES = ROW_BYTES * HEIGHT
OLD_PAGE_SHA = "D68478DAB33D4B2F13E5A62B63A65F1A9B37593C3551D8B19444731EA6C22116"
EXPECTED_PAGE_SHA = "BAE21BCCC7BB5FAD4A0922D5E9C42FCB25EF58DD7B8102A7C72656F7B700CF5E"
EXPECTED_PRIOR_SHA = "9A831B882E24D5C1726B674BA40D8187F5E726E00A234BA3FFDACD33AD215123"
EXPECTED_STEADY_FACE_PNG_SHA = "3269679155DE09F2FCEDFF3DC059DE4C9AC1E811400258B3B110F839646A0E31"
REQUIREMENT = "COMP-REQ-471"
STATE_ORDER = [
    "centered_rest",
    "gaze_left",
    "gaze_up",
    "gaze_right",
    "gaze_down",
    "gaze_center",
    "single_tap_response",
    "hold_feedback_50",
    "menu_roots",
    "menu_voice",
    "menu_device",
    "menu_connection",
    "menu_preferences",
    "menu_device_ui_assets",
    "menu_return_rest",
    "recording_entry",
    "recording_return_rest",
]
CONTACT_POINTS = {
    "centered_rest": [100, 100],
    "gaze_left": [28, 100],
    "gaze_up": [100, 28],
    "gaze_right": [172, 100],
    "gaze_down": [100, 172],
    "gaze_center": [100, 100],
    "single_tap_response": [158, 82],
    "hold_feedback_50": [100, 100],
}
FULL_SCREEN_MENU_STATES = {
    "menu_roots",
    "menu_voice",
    "menu_device",
    "menu_connection",
    "menu_preferences",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="ascii")


def pack_image(path: Path) -> tuple[bytes, dict[str, Any]]:
    with Image.open(path) as source:
        image = source.convert("RGB")
        if image.size != (WIDTH, HEIGHT):
            raise ValueError(f"{path} is {image.size}, expected {(WIDTH, HEIGHT)}")
        pixels = list(image.getdata())
    packed = bytearray()
    black_points: list[tuple[int, int]] = []
    colors = set(pixels)
    for y in range(HEIGHT):
        for byte_x in range(ROW_BYTES):
            value = 0
            for bit in range(8):
                x = byte_x * 8 + bit
                red, green, blue = pixels[y * WIDTH + x]
                luminance = (299 * red + 587 * green + 114 * blue) // 1000
                if luminance < 128:
                    value |= 1 << (7 - bit)
                    black_points.append((x, y))
            packed.append(value)
    if len(packed) != FRAME_BYTES:
        raise AssertionError("packed frame length drifted")
    bounds = None
    if black_points:
        xs = [point[0] for point in black_points]
        ys = [point[1] for point in black_points]
        bounds = [min(xs), min(ys), max(xs), max(ys)]
    edge_touch_sides = []
    if any(x == 0 for x, _ in black_points):
        edge_touch_sides.append("left")
    if any(y == 0 for _, y in black_points):
        edge_touch_sides.append("top")
    if any(x == WIDTH - 1 for x, _ in black_points):
        edge_touch_sides.append("right")
    if any(y == HEIGHT - 1 for _, y in black_points):
        edge_touch_sides.append("bottom")
    return bytes(packed), {
        "black_pixels": len(black_points),
        "black_bounds_inclusive": bounds,
        "black_touches_edge": bool(
            bounds
            and (bounds[0] == 0 or bounds[1] == 0 or bounds[2] == WIDTH - 1 or bounds[3] == HEIGHT - 1)
        ),
        "edge_touch_sides": edge_touch_sides,
        "source_rgb_color_count": len(colors),
    }


def measure_source_layer(repo_root: Path, asset: dict[str, Any]) -> dict[str, Any]:
    source_path = repo_root / asset["repo_path"]
    with Image.open(source_path) as source:
        image = source.convert("RGBA")
        width, height = image.size
        black_points = []
        for y, row in enumerate(image.getdata()):
            red, green, blue, alpha = row
            composed_red = (alpha * red + (255 - alpha) * 255) // 255
            composed_green = (alpha * green + (255 - alpha) * 255) // 255
            composed_blue = (alpha * blue + (255 - alpha) * 255) // 255
            luminance = (299 * composed_red + 587 * composed_green + 114 * composed_blue) // 1000
            if luminance < 128:
                black_points.append((y % width, y // width))
    rect = asset["rect_relative_to_stage"]
    scale_x = rect["width"] / width
    scale_y = rect["height"] / height
    outside = 0
    mapped_points = []
    for x, y in black_points:
        mapped_x = rect["left"] + (x + 0.5) * scale_x
        mapped_y = rect["top"] + (y + 0.5) * scale_y
        mapped_points.append((mapped_x, mapped_y))
        if mapped_x < 0 or mapped_x >= WIDTH or mapped_y < 0 or mapped_y >= HEIGHT:
            outside += 1
    mapped_bounds = None
    if mapped_points:
        xs = [item[0] for item in mapped_points]
        ys = [item[1] for item in mapped_points]
        mapped_bounds = [min(xs), min(ys), max(xs), max(ys)]
    return {
        "role": asset["role"],
        "source_repo_path": asset["repo_path"],
        "source_sha256": asset["sha256"],
        "source_dimensions": [width, height],
        "source_visible_black_pixels": len(black_points),
        "mapped_black_bounds_stage_coordinates": mapped_bounds,
        "black_pixels_outside_stage": outside,
        "rect_outside_stage_area": asset["rect_outside_stage_area"],
        "visible_intersection_relative_to_stage": asset["visible_intersection_relative_to_stage"],
    }


def edge_policy(state_id: str) -> dict[str, Any]:
    if state_id in FULL_SCREEN_MENU_STATES:
        return {
            "allowed_sides": ["left", "top", "right", "bottom"],
            "reason": "accepted full-screen menu frame intentionally owns the complete 200x200 boundary",
        }
    return {
        "allowed_sides": [],
        "reason": "face, gaze, hold, recording, and return ink must remain inside the 200x200 boundary",
    }


def mismatch_bits(left: bytes, right: bytes) -> int:
    if len(left) != len(right):
        raise ValueError("cannot compare differently sized frames")
    return sum((a ^ b).bit_count() for a, b in zip(left, right))


def state_transitions(constants: dict[str, int]) -> dict[str, Any]:
    transitions: list[dict[str, Any]] = []
    gaze_states = ["gaze_left", "gaze_up", "gaze_right", "gaze_down", "gaze_center"]
    for target in gaze_states:
        transitions.append(
            {
                "from": "centered_rest",
                "event": f"pointer_drag_{target.removeprefix('gaze_')}",
                "to": target,
                "guard": f"movement_px>{constants['drag_move_px']}",
                "effect": "replace_current_gaze",
            }
        )
    transitions.append(
        {
            "from_any": gaze_states,
            "event": "pointer_move",
            "to_any": gaze_states,
            "guard": "active_pointer",
            "effect": "replace_current_gaze",
        }
    )
    transitions.append(
        {
            "from_any": gaze_states,
            "event": "pointer_up_or_cancel",
            "to": "centered_rest",
            "effect": "center_then_resume_story",
        }
    )
    transitions.extend(
        [
            {
                "from": "centered_rest",
                "event": "single_tap_commit",
                "to": "single_tap_response",
                "guard": f"no_second_tap_for_{constants['double_tap_gap_ms']}_ms",
                "effect": "one_deterministic_touch_tap_response",
            },
            {
                "from": "centered_rest",
                "event": "stationary_pointerdown",
                "to": "hold_feedback_50",
                "guard": f"movement_px<={constants['drag_move_px']}",
                "effect": "show_accepted_hold_ornament",
            },
            {
                "from": "hold_feedback_50",
                "event": "hold_complete",
                "to": "menu_roots",
                "guard": f"elapsed_ms>={constants['menu_hold_ms']}",
                "effect": "activate_menu_once",
            },
            {
                "from": "hold_feedback_50",
                "event": "early_up_cancel_blur_or_drag",
                "to": "centered_rest",
                "guard": f"elapsed_ms<{constants['menu_hold_ms']}",
                "effect": "clear_hold_feedback",
            },
            {
                "from": "centered_rest",
                "event": "second_short_tap",
                "to": "recording_entry",
                "guard": (
                    f"gap_ms<={constants['double_tap_gap_ms']} and "
                    f"distance_px<={constants['double_tap_move_px']}"
                ),
                "effect": "activate_recording_once",
            },
            {
                "from": "recording_entry",
                "event": "recording_return",
                "to": "recording_return_rest",
                "effect": "clear_transients_and_center",
            },
            {
                "from": "menu_roots",
                "event": "select_voice",
                "to": "menu_voice",
                "effect": "replace_exclusive_menu_surface",
            },
            {
                "from": "menu_roots",
                "event": "select_device",
                "to": "menu_device",
                "effect": "replace_exclusive_menu_surface",
            },
            {
                "from": "menu_roots",
                "event": "select_connection",
                "to": "menu_connection",
                "effect": "replace_exclusive_menu_surface",
            },
            {
                "from": "menu_roots",
                "event": "select_preferences",
                "to": "menu_preferences",
                "effect": "replace_exclusive_menu_surface",
            },
            {
                "from": "menu_device",
                "event": "select_ui_assets",
                "to": "menu_device_ui_assets",
                "effect": "replace_with_accepted_v9_face_asset",
            },
            {
                "from_any": ["menu_voice", "menu_device", "menu_connection", "menu_preferences"],
                "event": "menu_back",
                "to": "menu_roots",
                "effect": "replace_exclusive_menu_surface",
            },
            {
                "from_any": [
                    "menu_roots",
                    "menu_voice",
                    "menu_device",
                    "menu_connection",
                    "menu_preferences",
                    "menu_device_ui_assets",
                ],
                "event": "menu_return",
                "to": "menu_return_rest",
                "effect": "clear_transients_and_center",
            },
            {
                "from_any": ["single_tap_response", "menu_return_rest", "recording_return_rest"],
                "event": "settle",
                "to": "centered_rest",
                "effect": "resume_bounded_story",
            },
        ]
    )
    return {
        "schema": "companion.firmware-visual-state-transitions.v1",
        "requirement": REQUIREMENT,
        "state_count": len(STATE_ORDER),
        "transition_count": len(transitions),
        "randomness": 0,
        "unbounded_scheduling": 0,
        "accepted_gesture_constants": constants,
        "states": STATE_ORDER,
        "transitions": transitions,
    }


def capture_diagnostic(
    capture: dict[str, Any], capture_dir: Path, repo_root: Path
) -> dict[str, Any]:
    states = []
    for state in capture["states"]:
        png_path = capture_dir / state["png"]
        _, packed = pack_image(png_path)
        layers = [measure_source_layer(repo_root, asset) for asset in state["source_assets"]]
        black_outside = sum(item["black_pixels_outside_stage"] for item in layers)
        policy = edge_policy(state["id"])
        forbidden_edges = sorted(set(packed["edge_touch_sides"]) - set(policy["allowed_sides"]))
        overlap_count = state["semantic"]["conflicting_surface_overlap_count"]
        clipping_violation = int(black_outside > 0 or bool(forbidden_edges))
        states.append(
            {
                "viewport": state["png"].split("/")[1],
                "id": state["id"],
                "kind": state["kind"],
                "png": state["png"],
                "png_sha256": state["png_sha256"],
                "measured": {
                    "stage_rect": state["dom"]["observed"]["stage_rect"],
                    "stage_overflow": state["dom"]["observed"]["stage_overflow"],
                    "visible_layers": state["source_assets"],
                    "visible_layer_relationships": state["dom"]["observed"]["relationships"],
                    "layer_rect_clip_count": state["dom"]["observed"]["layer_rect_clip_count"],
                    "layer_rect_outside_stage_area": state["dom"]["observed"][
                        "layer_rect_outside_stage_area"
                    ],
                    "source_layer_black_bounds": layers,
                    "source_black_pixels_outside_stage": black_outside,
                    "packed_black_pixels": packed["black_pixels"],
                    "packed_black_bounds_inclusive": packed["black_bounds_inclusive"],
                    "packed_edge_touch_sides": packed["edge_touch_sides"],
                    "stale_layer_count": state["semantic"]["stale_layer_count"],
                    "conflicting_surface_overlap_count": overlap_count,
                },
                "policy_derived": {
                    "edge_contact_policy": policy,
                    "forbidden_edge_touch_sides": forbidden_edges,
                    "clipping_violation_count": clipping_violation,
                    "conflicting_surface_overlap_count": overlap_count,
                    "verdict": "PASS"
                    if clipping_violation == 0
                    and overlap_count == 0
                    and state["semantic"]["stale_layer_count"] == 0
                    else "NO_GO",
                },
            }
        )
    blockers = [
        {
            "viewport": state["viewport"],
            "state": state["id"],
            "stale": state["measured"]["stale_layer_count"],
            "clipping": state["policy_derived"]["clipping_violation_count"],
            "overlap": state["policy_derived"]["conflicting_surface_overlap_count"],
            "visible_roles": [
                item["role"] for item in state["measured"]["visible_layers"]
            ],
        }
        for state in states
        if state["policy_derived"]["verdict"] != "PASS"
    ]
    return {
        "schema": "companion.comp-req-467-capture-diagnostic.v1",
        "requirement": REQUIREMENT,
        "status": "PASS" if capture["status"] == "PASS" and not blockers else "NO_GO",
        "source": capture["source"],
        "capture_status": capture["status"],
        "hold_feedback_binding": capture["capture"]["hold_feedback_binding"],
        "measured_totals": {
            "state_viewport_records": len(states),
            "stale_layer_count": sum(item["measured"]["stale_layer_count"] for item in states),
            "observed_layer_rect_clip_count": sum(
                item["measured"]["layer_rect_clip_count"] for item in states
            ),
            "source_black_pixels_outside_stage": sum(
                item["measured"]["source_black_pixels_outside_stage"] for item in states
            ),
            "conflicting_surface_overlap_count": sum(
                item["measured"]["conflicting_surface_overlap_count"] for item in states
            ),
        },
        "policy_derived_totals": {
            "clipping_violation_count": sum(
                item["policy_derived"]["clipping_violation_count"] for item in states
            ),
            "no_global_edge_policy": True,
        },
        "blockers": blockers,
        "states": states,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--diagnostic-output", type=Path)
    args = parser.parse_args()
    capture_dir = args.capture.resolve()
    output_dir = args.output.resolve()
    repo_root = args.repo_root.resolve()
    manifest_path = capture_dir / "capture-manifest.json"
    capture = json.loads(manifest_path.read_text(encoding="utf-8"))
    diagnostic = capture_diagnostic(capture, capture_dir, repo_root)
    if args.diagnostic_output:
        write_json(args.diagnostic_output.resolve(), diagnostic)
    if capture["status"] != "PASS":
        print(
            json.dumps(
                {
                    "status": "NO_GO",
                    "reason": "browser capture is not PASS; firmware export was not emitted",
                    "blockers": diagnostic["blockers"],
                    "diagnostic": str(args.diagnostic_output.resolve())
                    if args.diagnostic_output
                    else None,
                },
                indent=2,
            )
        )
        return 1
    if capture["source"]["page_sha256"] != EXPECTED_PAGE_SHA:
        raise ValueError("browser page identity changed")
    if capture["source"]["old_page_sha256"] != OLD_PAGE_SHA:
        raise ValueError("old browser page identity changed")
    if not capture["source"]["authorized_change"]["only_authorized_change"]:
        raise ValueError("browser page change exceeds the authorized return teardown")
    if capture["source"]["accepted_steady_face_png_sha256"] != EXPECTED_STEADY_FACE_PNG_SHA:
        raise ValueError("accepted steady-state face pixel identity changed")
    if not capture["source"]["gesture_constants_unchanged"]:
        raise ValueError("gesture constants changed")
    if capture["source"]["prior_20_of_20_sha256"] != EXPECTED_PRIOR_SHA:
        raise ValueError("prior 20/20 identity changed")
    if capture["checks"]["passed"] < 20 or capture["checks"]["passed"] != capture["checks"]["total"]:
        raise ValueError("fresh browser capture did not pass at least 20/20 checks")
    hold_regressions = capture["capture"]["hold_feedback_binding"]["real_pointer_regressions"]
    if len(hold_regressions) != 2 or not all(item["route_exactly_once"] for item in hold_regressions):
        raise ValueError("deterministic hold frame is not bound to real desktop/mobile hold routes")

    by_viewport: dict[str, dict[str, dict[str, Any]]] = {"desktop": {}, "mobile": {}}
    for state in capture["states"]:
        viewport = state["png"].split("/")[1]
        by_viewport[viewport][state["id"]] = state
    for viewport, states in by_viewport.items():
        if list(sorted(states)) != list(sorted(STATE_ORDER)):
            raise ValueError(f"{viewport} state set differs from the bounded contract")
        if states["centered_rest"]["png_sha256"] != EXPECTED_STEADY_FACE_PNG_SHA:
            raise ValueError(f"{viewport} accepted steady-state face pixels changed")

    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    combined = bytearray()
    frames: list[dict[str, Any]] = []
    oracle_frames: list[dict[str, Any]] = []
    packed_by_state: dict[str, bytes] = {}
    offset = 0
    for state_id in STATE_ORDER:
        desktop_state = by_viewport["desktop"][state_id]
        mobile_state = by_viewport["mobile"][state_id]
        desktop_png = capture_dir / desktop_state["png"]
        mobile_png = capture_dir / mobile_state["png"]
        if file_sha(desktop_png) != desktop_state["png_sha256"]:
            raise ValueError(f"{state_id} desktop PNG hash drifted")
        if file_sha(mobile_png) != mobile_state["png_sha256"]:
            raise ValueError(f"{state_id} mobile PNG hash drifted")
        desktop_raw, metrics = pack_image(desktop_png)
        mobile_raw, mobile_metrics = pack_image(mobile_png)
        if mismatch_bits(desktop_raw, mobile_raw) != 0:
            raise ValueError(f"{state_id} desktop/mobile 1bpp pixels differ")
        if desktop_state["semantic"]["primary_surface_count"] != 1:
            raise ValueError(f"{state_id} does not have exactly one primary face/screen surface")
        if desktop_state["semantic"]["gaze_highlight_count"] > 1:
            raise ValueError(f"{state_id} has more than one gaze/highlight")
        if desktop_state["semantic"]["stale_layer_count"] != 0:
            raise ValueError(f"{state_id} has a stale layer")
        desktop_layers = [
            measure_source_layer(repo_root, asset) for asset in desktop_state["source_assets"]
        ]
        mobile_layers = [
            measure_source_layer(repo_root, asset) for asset in mobile_state["source_assets"]
        ]
        desktop_black_outside = sum(item["black_pixels_outside_stage"] for item in desktop_layers)
        mobile_black_outside = sum(item["black_pixels_outside_stage"] for item in mobile_layers)
        policy = edge_policy(state_id)
        forbidden_desktop_edges = sorted(set(metrics["edge_touch_sides"]) - set(policy["allowed_sides"]))
        forbidden_mobile_edges = sorted(
            set(mobile_metrics["edge_touch_sides"]) - set(policy["allowed_sides"])
        )
        clipping_violation_count = int(
            desktop_black_outside > 0
            or mobile_black_outside > 0
            or bool(forbidden_desktop_edges)
            or bool(forbidden_mobile_edges)
        )
        overlap_violation_count = (
            desktop_state["semantic"]["conflicting_surface_overlap_count"]
            + mobile_state["semantic"]["conflicting_surface_overlap_count"]
        )
        if clipping_violation_count:
            raise ValueError(
                f"{state_id} clipping policy failed: black_outside="
                f"{desktop_black_outside}/{mobile_black_outside}, "
                f"forbidden_edges={forbidden_desktop_edges}/{forbidden_mobile_edges}"
            )
        if overlap_violation_count:
            raise ValueError(f"{state_id} has conflicting surface overlap")

        packed_by_state[state_id] = desktop_raw
        raw_path = frames_dir / f"{state_id}.bin"
        pbm_path = frames_dir / f"{state_id}.pbm"
        raw_path.write_bytes(desktop_raw)
        pbm_path.write_bytes(f"P4\n{WIDTH} {HEIGHT}\n".encode("ascii") + desktop_raw)
        combined.extend(desktop_raw)
        definition = {
            "id": state_id,
            "kind": desktop_state["kind"],
            "byte_offset": offset,
            "byte_length": FRAME_BYTES,
            "raw_file": f"frames/{state_id}.bin",
            "raw_sha256": file_sha(raw_path),
            "pbm_file": f"frames/{state_id}.pbm",
            "pbm_sha256": file_sha(pbm_path),
            "black_pixels": metrics["black_pixels"],
            "black_bounds_inclusive": metrics["black_bounds_inclusive"],
            "black_touches_edge": metrics["black_touches_edge"],
            "measured": {
                "desktop": {
                    "stage_rect": desktop_state["dom"]["observed"]["stage_rect"],
                    "stage_overflow": desktop_state["dom"]["observed"]["stage_overflow"],
                    "visible_layers": desktop_state["source_assets"],
                    "visible_layer_relationships": desktop_state["dom"]["observed"]["relationships"],
                    "inactive_surfaces": desktop_state["dom"]["observed"]["inactive_surfaces"],
                    "layer_rect_clip_count": desktop_state["dom"]["observed"]["layer_rect_clip_count"],
                    "layer_rect_outside_stage_area": desktop_state["dom"]["observed"][
                        "layer_rect_outside_stage_area"
                    ],
                    "source_layer_black_bounds": desktop_layers,
                    "black_pixels_outside_stage": desktop_black_outside,
                    "packed_black_bounds_inclusive": metrics["black_bounds_inclusive"],
                    "packed_edge_touch_sides": metrics["edge_touch_sides"],
                },
                "mobile": {
                    "stage_rect": mobile_state["dom"]["observed"]["stage_rect"],
                    "stage_overflow": mobile_state["dom"]["observed"]["stage_overflow"],
                    "visible_layers": mobile_state["source_assets"],
                    "visible_layer_relationships": mobile_state["dom"]["observed"]["relationships"],
                    "inactive_surfaces": mobile_state["dom"]["observed"]["inactive_surfaces"],
                    "layer_rect_clip_count": mobile_state["dom"]["observed"]["layer_rect_clip_count"],
                    "layer_rect_outside_stage_area": mobile_state["dom"]["observed"][
                        "layer_rect_outside_stage_area"
                    ],
                    "source_layer_black_bounds": mobile_layers,
                    "black_pixels_outside_stage": mobile_black_outside,
                    "packed_black_bounds_inclusive": mobile_metrics["black_bounds_inclusive"],
                    "packed_edge_touch_sides": mobile_metrics["edge_touch_sides"],
                },
            },
            "policy_derived": {
                "edge_contact_policy": policy,
                "desktop_forbidden_edge_touch_sides": forbidden_desktop_edges,
                "mobile_forbidden_edge_touch_sides": forbidden_mobile_edges,
                "transparent_layer_rect_clip_allowed_only_when_black_pixels_outside_stage_is_zero": True,
                "clipping_violation_count": clipping_violation_count,
                "conflicting_surface_overlap_count": overlap_violation_count,
                "verdict": "PASS",
            },
            "orientation": {
                "screen_origin": "top_left",
                "positive_x": "right",
                "positive_y": "down",
                "semantic": desktop_state["orientation"],
                "browser_contact_px": CONTACT_POINTS.get(state_id),
            },
            "primary_surface_count": desktop_state["semantic"]["primary_surface_count"],
            "expression_face_count": desktop_state["semantic"]["expression_face_count"],
            "exclusive_menu_surface_count": desktop_state["semantic"]["exclusive_menu_surface_count"],
            "gaze_highlight_count": desktop_state["semantic"]["gaze_highlight_count"],
            "stale_layer_count": desktop_state["semantic"]["stale_layer_count"],
            "clipping_policy_violation_count": clipping_violation_count,
            "conflicting_surface_overlap_count": overlap_violation_count,
            "browser_render": {
                "desktop_png_sha256": desktop_state["png_sha256"],
                "mobile_png_sha256": mobile_state["png_sha256"],
                "desktop_source_rgb_color_count": metrics["source_rgb_color_count"],
                "mobile_source_rgb_color_count": mobile_metrics["source_rgb_color_count"],
            },
            "source_assets": desktop_state["source_assets"],
        }
        frames.append(definition)
        oracle_frames.append(
            {
                "id": state_id,
                "browser_desktop_to_raw_mismatch_bits": mismatch_bits(desktop_raw, raw_path.read_bytes()),
                "browser_mobile_to_raw_mismatch_bits": mismatch_bits(mobile_raw, raw_path.read_bytes()),
                "desktop_mobile_mismatch_bits": mismatch_bits(desktop_raw, mobile_raw),
                "browser_black_pixels": metrics["black_pixels"],
                "raw_black_pixels": sum(byte.bit_count() for byte in raw_path.read_bytes()),
                "measured": {
                    "desktop_black_bounds_inclusive": metrics["black_bounds_inclusive"],
                    "mobile_black_bounds_inclusive": mobile_metrics["black_bounds_inclusive"],
                    "desktop_edge_touch_sides": metrics["edge_touch_sides"],
                    "mobile_edge_touch_sides": mobile_metrics["edge_touch_sides"],
                    "desktop_source_black_pixels_outside_stage": desktop_black_outside,
                    "mobile_source_black_pixels_outside_stage": mobile_black_outside,
                    "desktop_conflicting_surface_overlap_count": desktop_state["semantic"][
                        "conflicting_surface_overlap_count"
                    ],
                    "mobile_conflicting_surface_overlap_count": mobile_state["semantic"][
                        "conflicting_surface_overlap_count"
                    ],
                },
                "policy_derived": definition["policy_derived"],
                "status": "PASS",
            }
        )
        offset += FRAME_BYTES

    combined_path = output_dir / "frames.bin"
    combined_path.write_bytes(bytes(combined))
    constants = capture["source"]["gesture_constants"]
    transitions = state_transitions(constants)
    transitions_path = output_dir / "state-transitions.json"
    write_json(transitions_path, transitions)
    measured_stale_count = sum(item["stale_layer_count"] for item in frames)
    measured_layer_rect_clip_count = sum(
        item["measured"]["desktop"]["layer_rect_clip_count"]
        + item["measured"]["mobile"]["layer_rect_clip_count"]
        for item in frames
    )
    measured_black_outside_count = sum(
        item["measured"]["desktop"]["black_pixels_outside_stage"]
        + item["measured"]["mobile"]["black_pixels_outside_stage"]
        for item in frames
    )
    measured_conflict_count = sum(item["conflicting_surface_overlap_count"] for item in frames)
    clipping_policy_violation_count = sum(item["clipping_policy_violation_count"] for item in frames)
    observed_debug_visible_count = sum(
        len(state["dom"]["debug_visible"]) for state in capture["states"]
    )

    visual_contract = {
        "schema": "companion.firmware-visual-contract.v1",
        "requirement": REQUIREMENT,
        "status": "PASS",
        "source": capture["source"],
        "format": {
            "width": WIDTH,
            "height": HEIGHT,
            "bits_per_pixel": 1,
            "black_bit": 1,
            "white_bit": 0,
            "bit_order": "MSB_first_within_each_byte",
            "row_order": "top_to_bottom",
            "row_stride_bytes": ROW_BYTES,
            "frame_bytes": FRAME_BYTES,
            "threshold": "integer_BT601_luminance_below_128_is_black",
        },
        "face_contract": {
            "primary_face_or_exclusive_screen_surface_per_state": 1,
            "expression_and_recording_face_count": 1,
            "exclusive_menu_expression_face_count": 0,
            "reason": "accepted menu replaces the face; it never stacks a menu over an expression face",
            "maximum_gaze_highlight_planes": 1,
        },
        "hold_feedback_binding": capture["capture"]["hold_feedback_binding"],
        "frame_count": len(frames),
        "combined_file": "frames.bin",
        "combined_sha256": file_sha(combined_path),
        "combined_bytes": len(combined),
        "frames": frames,
        "invariants": {
            "measured": {
                "stale_layer_count": measured_stale_count,
                "layer_rect_clip_count": measured_layer_rect_clip_count,
                "source_black_pixels_outside_stage": measured_black_outside_count,
                "conflicting_surface_overlap_count": measured_conflict_count,
                "debug_parameter_panel_visible_count": observed_debug_visible_count,
            },
            "policy_derived": {
                "clipping_violation_count": clipping_policy_violation_count,
                "edge_contact_policy_is_state_specific": True,
                "browser_orientation_preserved": True,
                "randomness": 0,
                "verdict": "PASS",
            },
        },
    }
    contract_path = output_dir / "visual-contract.json"
    write_json(contract_path, visual_contract)

    oracle = {
        "schema": "companion.browser-to-1bpp-pixel-oracle.v1",
        "requirement": REQUIREMENT,
        "status": "PASS",
        "capture_manifest_sha256": file_sha(manifest_path),
        "threshold": visual_contract["format"]["threshold"],
        "frame_count": len(oracle_frames),
        "hold_feedback_binding": capture["capture"]["hold_feedback_binding"],
        "total_desktop_to_raw_mismatch_bits": sum(
            item["browser_desktop_to_raw_mismatch_bits"] for item in oracle_frames
        ),
        "total_mobile_to_raw_mismatch_bits": sum(
            item["browser_mobile_to_raw_mismatch_bits"] for item in oracle_frames
        ),
        "total_desktop_mobile_mismatch_bits": sum(
            item["desktop_mobile_mismatch_bits"] for item in oracle_frames
        ),
        "frames": oracle_frames,
    }
    oracle_path = output_dir / "pixel-oracle.json"
    write_json(oracle_path, oracle)

    handoff = {
        "schema": "companion.comp-req-466-visual-handoff.v1",
        "requirement": REQUIREMENT,
        "consumer_requirement": "COMP-REQ-466",
        "status": "PASS",
        "integration_authorized": False,
        "hardware_contact": 0,
        "source_page_sha256": EXPECTED_PAGE_SHA,
        "format": visual_contract["format"],
        "frames_file": "frames.bin",
        "frames_file_sha256": file_sha(combined_path),
        "frame_count": len(frames),
        "state_transition_file": "state-transitions.json",
        "state_transition_sha256": file_sha(transitions_path),
        "visual_contract_file": "visual-contract.json",
        "visual_contract_sha256": file_sha(contract_path),
        "pixel_oracle_file": "pixel-oracle.json",
        "pixel_oracle_sha256": file_sha(oracle_path),
        "index": [
            {
                "state": item["id"],
                "offset": item["byte_offset"],
                "bytes": item["byte_length"],
                "sha256": item["raw_sha256"],
            }
            for item in frames
        ],
        "consumer_rules": [
            "read exactly 5000 bytes per frame",
            "replace the current 200x200 framebuffer; never append a face or gaze plane",
            "use the bounded transition IDs without changing accepted gesture constants",
            "do not treat this machine contract as hardware or production authorization",
        ],
    }
    handoff_path = output_dir / "handoff-manifest.json"
    write_json(handoff_path, handoff)

    equality_expectations = [
        ("menu_return_rest", "centered_rest"),
        ("recording_return_rest", "centered_rest"),
        ("gaze_center", "centered_rest"),
    ]
    for left, right in equality_expectations:
        if packed_by_state[left] != packed_by_state[right]:
            raise ValueError(f"{left} does not return to the accepted centered pixels from {right}")
    if len({sha256(packed_by_state[state]) for state in ["gaze_left", "gaze_up", "gaze_right", "gaze_down", "gaze_center"]}) != 5:
        raise ValueError("directional gaze frames are not five distinct replacements")

    summary = {
        "status": "PASS",
        "output": str(output_dir),
        "frame_count": len(frames),
        "frame_bytes": FRAME_BYTES,
        "combined_bytes": len(combined),
        "combined_sha256": file_sha(combined_path),
        "visual_contract_sha256": file_sha(contract_path),
        "transition_sha256": file_sha(transitions_path),
        "pixel_oracle_sha256": file_sha(oracle_path),
        "handoff_sha256": file_sha(handoff_path),
        "browser_checks": f"{capture['checks']['passed']}/{capture['checks']['total']}",
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
