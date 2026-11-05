#!/usr/bin/env python3
"""Generate and verify the COMP-REQ-472 expanded 1bpp window oracle."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any


WIDTH = 200
HEIGHT = 200
STRIDE = 25
FRAME_BYTES = 5000
STATE_COUNT = 17
TRANSITION_COUNT = 21
PAYLOAD_BUDGET = 85000
ORACLE_NAME = "expanded-window-oracle.json"
BOUNDARY_NAME = "physical-consumer-boundary.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes())


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, indent=2) + "\n").encode("ascii")


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def states_from_mask(mask: int, state_ids: list[str]) -> list[str]:
    unknown_bits = mask & ~((1 << len(state_ids)) - 1)
    if mask <= 0 or unknown_bits:
        raise ValueError(f"invalid state mask 0x{mask:08X}")
    return [state_id for index, state_id in enumerate(state_ids) if mask & (1 << index)]


def transition_states(item: dict[str, Any], key: str) -> list[str]:
    if key in item:
        return [item[key]]
    return list(item[f"{key}_any"])


def classify_pair(
    event: str,
    effect: str,
    from_state: str,
    to_state: str,
) -> list[str]:
    text = " ".join((event, effect, from_state, to_state))
    categories = []
    if "gaze" in text or event.startswith("pointer_"):
        categories.append("gaze")
    if "tap" in text or "single_tap" in text:
        categories.append("tap")
    if "recording" in text:
        categories.append("recording")
    if "menu" in text or event.startswith("select_"):
        categories.append("menu")
    if "hold" in text or "stationary_" in event:
        categories.append("hold")
    if event == "settle" or "settle" in effect:
        categories.append("settle")
    return categories or ["other"]


def changed_pixels(previous: bytes, current: bytes) -> tuple[dict[str, int] | None, int, int]:
    if len(previous) != FRAME_BYTES or len(current) != FRAME_BYTES:
        raise ValueError("frame length changed")
    x_min = WIDTH
    y_min = HEIGHT
    x_max = -1
    y_max = -1
    changed_pixel_count = 0
    changed_byte_count = 0
    for byte_index, (before, after) in enumerate(zip(previous, current)):
        different = before ^ after
        if not different:
            continue
        changed_byte_count += 1
        y = byte_index // STRIDE
        byte_x = byte_index % STRIDE
        for bit_index in range(8):
            mask = 1 << (7 - bit_index)
            if different & mask:
                x = byte_x * 8 + bit_index
                changed_pixel_count += 1
                x_min = min(x_min, x)
                x_max = max(x_max, x)
                y_min = min(y_min, y)
                y_max = max(y_max, y)
    if changed_pixel_count == 0:
        return None, 0, 0
    return (
        {
            "x_min": x_min,
            "y_min": y_min,
            "x_max": x_max,
            "y_max": y_max,
            "width": x_max - x_min + 1,
            "height": y_max - y_min + 1,
        },
        changed_pixel_count,
        changed_byte_count,
    )


def exact_window(bounds: dict[str, int] | None) -> dict[str, Any] | None:
    if bounds is None:
        return None
    x_byte_start = bounds["x_min"] // 8
    x_byte_end = bounds["x_max"] // 8
    y_start = bounds["y_min"]
    y_end = bounds["y_max"]
    row_bytes = x_byte_end - x_byte_start + 1
    rows = y_end - y_start + 1
    payload_bytes = row_bytes * rows
    return {
        "x_byte_start": x_byte_start,
        "x_byte_end": x_byte_end,
        "x_pixel_start": x_byte_start * 8,
        "x_pixel_end": min(WIDTH - 1, x_byte_end * 8 + 7),
        "y_start": y_start,
        "y_end": y_end,
        "row_bytes": row_bytes,
        "rows": rows,
        "payload_bytes": payload_bytes,
        "full_frame": payload_bytes == FRAME_BYTES,
    }


def slice_for_window(current: bytes, window: dict[str, Any] | None) -> bytes:
    if window is None:
        return b""
    payload = bytearray()
    for y in range(window["y_start"], window["y_end"] + 1):
        row_start = y * STRIDE + window["x_byte_start"]
        row_end = y * STRIDE + window["x_byte_end"] + 1
        payload.extend(current[row_start:row_end])
    return bytes(payload)


def apply_window(
    previous: bytes,
    payload: bytes,
    window: dict[str, Any] | None,
) -> bytes:
    if window is None:
        if payload:
            raise ValueError("no-op window has payload")
        return previous
    expected_bytes = window["row_bytes"] * window["rows"]
    if len(payload) != expected_bytes:
        raise ValueError("window payload length mismatch")
    result = bytearray(previous)
    cursor = 0
    for y in range(window["y_start"], window["y_end"] + 1):
        row_start = y * STRIDE + window["x_byte_start"]
        row_end = row_start + window["row_bytes"]
        result[row_start:row_end] = payload[cursor : cursor + window["row_bytes"]]
        cursor += window["row_bytes"]
    return bytes(result)


def outside_window_difference_count(
    previous: bytes,
    current: bytes,
    window: dict[str, Any] | None,
) -> tuple[int, int]:
    changed_bytes = 0
    changed_pixels_count = 0
    for byte_index, (before, after) in enumerate(zip(previous, current)):
        y = byte_index // STRIDE
        x_byte = byte_index % STRIDE
        inside = (
            window is not None
            and window["y_start"] <= y <= window["y_end"]
            and window["x_byte_start"] <= x_byte <= window["x_byte_end"]
        )
        if inside or before == after:
            continue
        changed_bytes += 1
        changed_pixels_count += (before ^ after).bit_count()
    return changed_bytes, changed_pixels_count


def pair_record(
    pair_index: int,
    transition_index: int,
    transition_pair_index: int,
    transition: dict[str, Any],
    from_state: str,
    to_state: str,
    previous: bytes,
    current: bytes,
) -> dict[str, Any]:
    bounds, changed_pixel_count, changed_byte_count = changed_pixels(previous, current)
    window = exact_window(bounds)
    payload = slice_for_window(current, window)
    reconstructed = apply_window(previous, payload, window)
    outside_bytes, outside_pixels = outside_window_difference_count(previous, current, window)
    categories = classify_pair(
        transition["event"],
        transition["effect"],
        from_state,
        to_state,
    )
    menu_related = "menu" in categories
    full_frame_allowed = bool(window and window["full_frame"] and menu_related)
    if window and window["full_frame"] and not menu_related:
        raise ValueError(f"non-menu pair requires a full frame: {from_state}->{to_state}")
    pair_id = (
        f"T{transition_index:02d}-P{transition_pair_index:02d}-"
        f"{from_state}--{to_state}"
    )
    return {
        "pair_index": pair_index,
        "id": pair_id,
        "transition_index": transition_index,
        "transition_pair_index": transition_pair_index,
        "from_state": from_state,
        "to_state": to_state,
        "from_mask": transition["from_mask"],
        "to_mask": transition["to_mask"],
        "event": transition["event"],
        "guard": transition["guard"],
        "effect": transition["effect"],
        "categories": categories,
        "menu_related": menu_related,
        "pixel_noop": previous == current,
        "state_identity_noop": from_state != to_state and previous == current,
        "previous_frame_bytes": len(previous),
        "current_frame_bytes": len(current),
        "previous_frame_sha256": sha256(previous),
        "current_frame_sha256": sha256(current),
        "changed_pixel_count": changed_pixel_count,
        "changed_byte_count": changed_byte_count,
        "changed_pixel_bounds": bounds,
        "transfer_window": window,
        "current_slice": {
            "payload_bytes": len(payload),
            "sha256": sha256(payload),
            "hex": payload.hex().upper(),
        },
        "outside_unchanged_oracle": {
            "outside_window_changed_byte_count": outside_bytes,
            "outside_window_changed_pixel_count": outside_pixels,
            "outside_window_unchanged": outside_bytes == 0 and outside_pixels == 0,
            "reconstructed_current_byte_equal": reconstructed == current,
            "reconstructed_current_sha256": sha256(reconstructed),
        },
        "full_frame_policy": {
            "payload_is_5000_bytes": len(payload) == FRAME_BYTES,
            "allowed_only_because_menu_related": full_frame_allowed,
            "legal": len(payload) != FRAME_BYTES or menu_related,
        },
    }


def category_statistics(pairs: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    categories = ("gaze", "tap", "recording", "menu", "hold", "settle", "other")
    for category in categories:
        members = [pair for pair in pairs if category in pair["categories"]]
        if not members:
            continue
        maximum = max(pair["current_slice"]["payload_bytes"] for pair in members)
        result[category] = {
            "pair_count": len(members),
            "max_payload_bytes": maximum,
            "max_payload_pair_ids": [
                pair["id"]
                for pair in members
                if pair["current_slice"]["payload_bytes"] == maximum
            ],
            "full_frame_pair_count": sum(
                pair["current_slice"]["payload_bytes"] == FRAME_BYTES for pair in members
            ),
            "pixel_noop_pair_count": sum(pair["pixel_noop"] for pair in members),
        }
    return result


def generate_oracle(input_dir: Path) -> tuple[dict[str, Any], dict[str, bytes]]:
    contract_path = input_dir / "visual-contract.json"
    transition_path = input_dir / "state-transitions.json"
    pack_manifest_path = input_dir / "c-asset-pack-manifest.json"
    contract = load_json(contract_path)
    raw_transitions = load_json(transition_path)
    pack_manifest = load_json(pack_manifest_path)

    fmt = contract["format"]
    if (
        contract["frame_count"] != STATE_COUNT
        or fmt["width"] != WIDTH
        or fmt["height"] != HEIGHT
        or fmt["row_stride_bytes"] != STRIDE
        or fmt["frame_bytes"] != FRAME_BYTES
        or fmt["bits_per_pixel"] != 1
    ):
        raise ValueError("source visual contract geometry/count changed")
    if len(pack_manifest["transitions"]) != TRANSITION_COUNT:
        raise ValueError("source transition count changed")

    state_ids = [item["id"] for item in pack_manifest["states"]]
    contract_ids = [item["id"] for item in contract["frames"]]
    if state_ids != contract_ids or len(set(state_ids)) != STATE_COUNT:
        raise ValueError("state identity/order changed")

    frames: dict[str, bytes] = {}
    for item in contract["frames"]:
        raw = (input_dir / item["raw_file"]).read_bytes()
        if len(raw) != FRAME_BYTES or sha256(raw) != item["raw_sha256"]:
            raise ValueError(f"source frame changed: {item['id']}")
        frames[item["id"]] = raw

    pairs: list[dict[str, Any]] = []
    pair_index = 0
    transition_expansion: list[dict[str, Any]] = []
    for transition_index, (masked, raw) in enumerate(
        zip(pack_manifest["transitions"], raw_transitions["transitions"])
    ):
        from_states = states_from_mask(masked["from_mask"], state_ids)
        to_states = states_from_mask(masked["to_mask"], state_ids)
        if (
            from_states != transition_states(raw, "from")
            or to_states != transition_states(raw, "to")
            or masked["event"] != raw["event"]
            or masked["guard"] != raw.get("guard", "always")
            or masked["effect"] != raw["effect"]
        ):
            raise ValueError(f"transition mask/source mismatch at {transition_index}")
        transition_expansion.append(
            {
                "transition_index": transition_index,
                "from_mask": masked["from_mask"],
                "to_mask": masked["to_mask"],
                "from_states": from_states,
                "to_states": to_states,
                "expanded_pair_count": len(from_states) * len(to_states),
            }
        )
        local_pair_index = 0
        for from_state in from_states:
            for to_state in to_states:
                pairs.append(
                    pair_record(
                        pair_index,
                        transition_index,
                        local_pair_index,
                        masked,
                        from_state,
                        to_state,
                        frames[from_state],
                        frames[to_state],
                    )
                )
                pair_index += 1
                local_pair_index += 1

    computed_count = sum(item["expanded_pair_count"] for item in transition_expansion)
    if computed_count != len(pairs):
        raise ValueError("expanded pair accounting mismatch")
    full_frame_pairs = [
        pair for pair in pairs if pair["current_slice"]["payload_bytes"] == FRAME_BYTES
    ]
    nonmenu_full_frame_pairs = [pair for pair in full_frame_pairs if not pair["menu_related"]]
    if nonmenu_full_frame_pairs:
        raise ValueError("non-menu full-frame transition detected")
    global_max = max(pair["current_slice"]["payload_bytes"] for pair in pairs)
    nonmenu_max = max(
        pair["current_slice"]["payload_bytes"] for pair in pairs if not pair["menu_related"]
    )
    oracle = {
        "schema": "companion.visual-expanded-window-oracle.v1",
        "requirement": "COMP-REQ-471/472",
        "status": "PASS",
        "source": {
            "visual_contract_file": "visual-contract.json",
            "visual_contract_sha256": file_sha(contract_path),
            "state_transitions_file": "state-transitions.json",
            "state_transitions_sha256": file_sha(transition_path),
            "c_asset_pack_manifest_file": "c-asset-pack-manifest.json",
            "c_asset_pack_manifest_sha256": file_sha(pack_manifest_path),
            "frames_bin_sha256": contract["combined_sha256"],
        },
        "format": {
            "width": WIDTH,
            "height": HEIGHT,
            "stride_bytes": STRIDE,
            "frame_bytes": FRAME_BYTES,
            "bits_per_pixel": 1,
            "bit_order": fmt["bit_order"],
            "row_order": fmt["row_order"],
            "window_x_alignment": "byte_aligned_8_pixels",
            "window_y_alignment": "exact_changed_rows",
        },
        "state_count": len(state_ids),
        "state_ids": state_ids,
        "transition_mask_count": len(transition_expansion),
        "transition_expansion": transition_expansion,
        "expanded_pair_count": len(pairs),
        "pair_count_note": {
            "owner_estimate": 54,
            "computed_from_input_masks": len(pairs),
            "estimate_is_not_a_gate": True,
            "pixel_noop_pairs_are_included": True,
            "gaze_self_pairs_included": sum(
                pair["from_state"] == pair["to_state"] and "gaze" in pair["categories"]
                for pair in pairs
            ),
        },
        "policy": {
            "complete_previous_and_current_frame_bytes_read_per_pair": FRAME_BYTES,
            "payload_must_equal_current_frame_window_slice": True,
            "outside_window_must_be_unchanged": True,
            "full_5000_bytes_allowed_only_for_menu_related_pair": True,
            "nonmenu_full_frame_is_no_go": True,
            "pixel_noop_retains_state_pair_identity": True,
        },
        "statistics": {
            "pair_count": len(pairs),
            "pixel_noop_pair_count": sum(pair["pixel_noop"] for pair in pairs),
            "state_identity_noop_pair_count": sum(
                pair["state_identity_noop"] for pair in pairs
            ),
            "same_state_pixel_noop_pair_count": sum(
                pair["pixel_noop"] and pair["from_state"] == pair["to_state"]
                for pair in pairs
            ),
            "full_frame_pair_count": len(full_frame_pairs),
            "nonmenu_full_frame_pair_count": len(nonmenu_full_frame_pairs),
            "max_payload_bytes": global_max,
            "max_nonmenu_payload_bytes": nonmenu_max,
            "category": category_statistics(pairs),
        },
        "pairs": pairs,
    }
    return oracle, frames


def generate_boundary(
    oracle: dict[str, Any],
    oracle_sha256: str,
) -> dict[str, Any]:
    return {
        "schema": "companion.physical-consumer-boundary.v1",
        "requirement": "COMP-REQ-471/472",
        "status": "PASS_BOUNDARY_ONLY_NOT_INTEGRATED",
        "default_off": True,
        "integration_authorized": False,
        "shared_contract": {
            "state_count": oracle["state_count"],
            "state_ids": oracle["state_ids"],
            "pixels": {
                "frames_bin_sha256": oracle["source"]["frames_bin_sha256"],
                "visual_contract_sha256": oracle["source"]["visual_contract_sha256"],
                "expanded_window_oracle_sha256": oracle_sha256,
                "width": WIDTH,
                "height": HEIGHT,
                "stride_bytes": STRIDE,
                "frame_bytes": FRAME_BYTES,
            },
            "only_shared_surface": "17 semantic state identities and their exact 200x200 1bpp pixels",
        },
        "browser_only_not_for_physical_firmware": {
            "double_tap_gap_ms": 350,
            "double_tap_move_px": 32,
            "hold_menu_ms": 700,
            "drag_move_px": 44,
            "source": "state-transitions.json accepted_gesture_constants and guards",
            "must_not_be_copied_to_physical_adapter": True,
        },
        "physical_comp_req_472_mapping": {
            "double_tap_gap_ms": 650,
            "double_tap_move_px_max": 40,
            "hold_feedback_ms": 650,
            "menu_entry_ms": 3000,
            "drag_cancel_consumed_until_release": "preserve existing COMP-REQ-472 semantics",
            "semantic_state_mapping": {
                "directional_gaze": [
                    "gaze_left",
                    "gaze_up",
                    "gaze_right",
                    "gaze_down",
                    "gaze_center",
                ],
                "single_tap": "single_tap_response",
                "hold_feedback": "hold_feedback_50",
                "stationary_hold_complete": "menu_roots",
                "double_tap": "recording_entry",
                "recording_return": "recording_return_rest",
                "menu_return": "menu_return_rest",
            },
        },
        "consumer_rules": [
            "derive the exact byte-aligned X and exact-row Y window from complete previous/current 5000-byte frames",
            "write only the oracle current slice for gaze, tap, and recording transitions",
            "allow a 5000-byte window only for a menu-related pair whose exact oracle window is full frame",
            "retain state identity for pixel no-op pairs; shared pixels do not erase semantic transitions",
            "do not use browser transition guards as physical gesture thresholds",
        ],
        "non_goals": [
            "no C asset pack modification",
            "no lower-driver or firmware integration",
            "no Platform, vendor, production, hardware, prompt, or acceptance change",
        ],
    }


def window_payload_from_artifact(pair: dict[str, Any]) -> bytes:
    raw = pair["current_slice"]["hex"]
    if not isinstance(raw, str) or len(raw) % 2 or not re.fullmatch(r"[0-9A-F]*", raw):
        raise ValueError("payload hex is malformed")
    return bytes.fromhex(raw)


def validate_oracle(
    artifact: dict[str, Any],
    expected: dict[str, Any],
    frames: dict[str, bytes],
    pair_previous_overrides: dict[str, bytes] | None = None,
) -> list[str]:
    errors: list[str] = []
    overrides = pair_previous_overrides or {}
    if artifact.get("status") != "PASS":
        errors.append("oracle status is not PASS")
    if artifact.get("expanded_pair_count") != expected["expanded_pair_count"]:
        errors.append("expanded pair count differs")
    actual_pairs = artifact.get("pairs", [])
    expected_pairs = expected["pairs"]
    if len(actual_pairs) != len(expected_pairs):
        errors.append("pair list length differs")
        return errors
    if len({pair.get("id") for pair in actual_pairs}) != len(actual_pairs):
        errors.append("pair identity is duplicated")

    for actual, expected_pair in zip(actual_pairs, expected_pairs):
        pair_id = expected_pair["id"]
        if actual.get("id") != pair_id:
            errors.append(f"{pair_id}: pair ordering/identity differs")
            continue
        previous = overrides.get(pair_id, frames[expected_pair["from_state"]])
        current = frames[expected_pair["to_state"]]
        declared_window = actual.get("transfer_window")
        outside_bytes, outside_pixels = outside_window_difference_count(
            previous, current, declared_window
        )
        if outside_bytes or outside_pixels:
            errors.append(f"{pair_id}: stale outside window changed")
        if (
            declared_window
            and declared_window.get("full_frame")
            and not actual.get("menu_related")
        ):
            errors.append(f"{pair_id}: non-menu full-frame window is forbidden")
        try:
            payload = window_payload_from_artifact(actual)
        except (ValueError, KeyError) as exc:
            errors.append(f"{pair_id}: {exc}")
            continue
        expected_payload_for_declared = slice_for_window(current, declared_window)
        if payload != expected_payload_for_declared:
            errors.append(f"{pair_id}: payload does not equal current slice")
        if sha256(payload) != actual["current_slice"].get("sha256"):
            errors.append(f"{pair_id}: payload SHA differs")
        if len(payload) != actual["current_slice"].get("payload_bytes"):
            errors.append(f"{pair_id}: payload byte count differs")
        bounds, changed_pixel_count, changed_byte_count = changed_pixels(previous, current)
        expected_window = exact_window(bounds)
        if actual.get("changed_pixel_bounds") != bounds:
            errors.append(f"{pair_id}: changed pixel bounds differ")
        if declared_window != expected_window:
            errors.append(f"{pair_id}: exact window differs")
        if actual.get("changed_pixel_count") != changed_pixel_count:
            errors.append(f"{pair_id}: changed pixel count differs")
        if actual.get("changed_byte_count") != changed_byte_count:
            errors.append(f"{pair_id}: changed byte count differs")
        try:
            reconstructed = apply_window(previous, payload, declared_window)
        except ValueError as exc:
            errors.append(f"{pair_id}: reconstruction failed: {exc}")
        else:
            if reconstructed != current:
                errors.append(f"{pair_id}: reconstructed current differs")
        if actual.get("previous_frame_sha256") != sha256(previous):
            errors.append(f"{pair_id}: previous full-frame SHA differs")
        if actual.get("current_frame_sha256") != sha256(current):
            errors.append(f"{pair_id}: current full-frame SHA differs")

    for key in (
        "transition_expansion",
        "statistics",
        "policy",
        "state_ids",
        "source",
        "format",
    ):
        if artifact.get(key) != expected.get(key):
            errors.append(f"top-level {key} differs")
    return errors


def set_custom_window_payload(
    pair: dict[str, Any],
    current: bytes,
    window: dict[str, Any],
) -> None:
    payload = slice_for_window(current, window)
    pair["transfer_window"] = window
    pair["current_slice"] = {
        "payload_bytes": len(payload),
        "sha256": sha256(payload),
        "hex": payload.hex().upper(),
    }


def mutation_suite(
    oracle: dict[str, Any],
    frames: dict[str, bytes],
) -> list[dict[str, Any]]:
    bounded = next(
        pair
        for pair in oracle["pairs"]
        if pair["transfer_window"]
        and 1 < pair["transfer_window"]["row_bytes"] < STRIDE
        and pair["transfer_window"]["x_byte_end"] < STRIDE - 1
        and not pair["menu_related"]
    )
    results = []

    shrink = copy.deepcopy(oracle)
    pair = shrink["pairs"][bounded["pair_index"]]
    window = copy.deepcopy(pair["transfer_window"])
    window["x_byte_end"] -= 1
    window["x_pixel_end"] -= 8
    window["row_bytes"] -= 1
    window["payload_bytes"] = window["row_bytes"] * window["rows"]
    window["full_frame"] = False
    set_custom_window_payload(pair, frames[pair["to_state"]], window)
    errors = validate_oracle(shrink, oracle, frames)
    results.append(
        {
            "id": "shrink_window",
            "expected_error": "exact window differs",
            "observed_errors": errors,
            "fail_closed": any("exact window differs" in error for error in errors),
        }
    )

    expand = copy.deepcopy(oracle)
    pair = expand["pairs"][bounded["pair_index"]]
    window = copy.deepcopy(pair["transfer_window"])
    window["x_byte_end"] += 1
    window["x_pixel_end"] = min(WIDTH - 1, window["x_pixel_end"] + 8)
    window["row_bytes"] += 1
    window["payload_bytes"] = window["row_bytes"] * window["rows"]
    window["full_frame"] = False
    set_custom_window_payload(pair, frames[pair["to_state"]], window)
    errors = validate_oracle(expand, oracle, frames)
    results.append(
        {
            "id": "expand_window",
            "expected_error": "exact window differs",
            "observed_errors": errors,
            "fail_closed": any("exact window differs" in error for error in errors),
        }
    )

    wrong_payload = copy.deepcopy(oracle)
    pair = wrong_payload["pairs"][bounded["pair_index"]]
    payload = bytearray(window_payload_from_artifact(pair))
    payload[0] ^= 0x01
    pair["current_slice"]["hex"] = bytes(payload).hex().upper()
    pair["current_slice"]["sha256"] = sha256(bytes(payload))
    errors = validate_oracle(wrong_payload, oracle, frames)
    results.append(
        {
            "id": "wrong_payload",
            "expected_error": "payload does not equal current slice",
            "observed_errors": errors,
            "fail_closed": any(
                "payload does not equal current slice" in error for error in errors
            ),
        }
    )

    nonmenu_full = copy.deepcopy(oracle)
    pair = nonmenu_full["pairs"][bounded["pair_index"]]
    window = {
        "x_byte_start": 0,
        "x_byte_end": STRIDE - 1,
        "x_pixel_start": 0,
        "x_pixel_end": WIDTH - 1,
        "y_start": 0,
        "y_end": HEIGHT - 1,
        "row_bytes": STRIDE,
        "rows": HEIGHT,
        "payload_bytes": FRAME_BYTES,
        "full_frame": True,
    }
    set_custom_window_payload(pair, frames[pair["to_state"]], window)
    pair["full_frame_policy"] = {
        "payload_is_5000_bytes": True,
        "allowed_only_because_menu_related": False,
        "legal": False,
    }
    errors = validate_oracle(nonmenu_full, oracle, frames)
    results.append(
        {
            "id": "nonmenu_fullframe",
            "expected_error": "non-menu full-frame window is forbidden",
            "observed_errors": errors,
            "fail_closed": any(
                "non-menu full-frame window is forbidden" in error for error in errors
            ),
        }
    )

    stale_previous = bytearray(frames[bounded["from_state"]])
    window = bounded["transfer_window"]
    outside_index = next(
        index
        for index in range(FRAME_BYTES)
        if not (
            window["y_start"] <= index // STRIDE <= window["y_end"]
            and window["x_byte_start"] <= index % STRIDE <= window["x_byte_end"]
        )
    )
    stale_previous[outside_index] ^= 0x01
    errors = validate_oracle(
        oracle,
        oracle,
        frames,
        pair_previous_overrides={bounded["id"]: bytes(stale_previous)},
    )
    results.append(
        {
            "id": "stale_outside",
            "expected_error": "stale outside window changed",
            "observed_errors": errors,
            "fail_closed": any(
                "stale outside window changed" in error for error in errors
            ),
        }
    )
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--rerun-dir", type=Path)
    parser.add_argument("--machine-result", type=Path)
    args = parser.parse_args()

    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    oracle, frames = generate_oracle(input_dir)
    oracle_data = json_bytes(oracle)
    boundary = generate_boundary(oracle, sha256(oracle_data))
    boundary_data = json_bytes(boundary)
    oracle_path = output_dir / ORACLE_NAME
    boundary_path = output_dir / BOUNDARY_NAME
    write_bytes(oracle_path, oracle_data)
    write_bytes(boundary_path, boundary_data)

    machine_status = None
    if args.machine_result:
        if not args.rerun_dir:
            raise ValueError("--machine-result requires --rerun-dir")
        rerun_dir = args.rerun_dir.resolve()
        rerun_oracle_path = rerun_dir / ORACLE_NAME
        rerun_boundary_path = rerun_dir / BOUNDARY_NAME
        deterministic_files = []
        deterministic_equal = True
        for canonical_path, rerun_path in (
            (oracle_path, rerun_oracle_path),
            (boundary_path, rerun_boundary_path),
        ):
            canonical_bytes = canonical_path.read_bytes()
            rerun_bytes = rerun_path.read_bytes()
            equal = canonical_bytes == rerun_bytes
            deterministic_equal &= equal
            deterministic_files.append(
                {
                    "file": canonical_path.name,
                    "canonical_sha256": sha256(canonical_bytes),
                    "rerun_sha256": sha256(rerun_bytes),
                    "byte_equal": equal,
                }
            )
        validation_errors = validate_oracle(oracle, oracle, frames)
        mutations = mutation_suite(oracle, frames)
        mutation_pass = all(item["fail_closed"] for item in mutations)
        machine_status = (
            "PASS"
            if deterministic_equal and not validation_errors and mutation_pass
            else "NO_GO"
        )
        result = {
            "schema": "companion.visual-expanded-window-oracle-machine-result.v1",
            "requirement": "COMP-REQ-471/472",
            "status": machine_status,
            "source": oracle["source"],
            "generator": {
                "file": "tools/faraday_upper_art/"
                "generate_companion_visual_expanded_window_oracle.py",
                "sha256": file_sha(Path(__file__).resolve()),
            },
            "artifacts": {
                ORACLE_NAME: file_sha(oracle_path),
                BOUNDARY_NAME: file_sha(boundary_path),
            },
            "computed": {
                "state_count": oracle["state_count"],
                "transition_mask_count": oracle["transition_mask_count"],
                "expanded_pair_count": oracle["expanded_pair_count"],
                "pixel_noop_pair_count": oracle["statistics"]["pixel_noop_pair_count"],
                "full_frame_pair_count": oracle["statistics"]["full_frame_pair_count"],
                "nonmenu_full_frame_pair_count": oracle["statistics"][
                    "nonmenu_full_frame_pair_count"
                ],
                "max_payload_bytes": oracle["statistics"]["max_payload_bytes"],
                "max_nonmenu_payload_bytes": oracle["statistics"][
                    "max_nonmenu_payload_bytes"
                ],
                "category": oracle["statistics"]["category"],
            },
            "checks": {
                "complete_5000_byte_previous_current_read": True,
                "all_mask_pairs_expanded": oracle["expanded_pair_count"]
                == sum(
                    item["expanded_pair_count"]
                    for item in oracle["transition_expansion"]
                ),
                "pixel_noop_pairs_included": oracle["statistics"][
                    "pixel_noop_pair_count"
                ]
                > 0,
                "exact_changed_bounds_and_windows": not validation_errors,
                "payload_current_slice_sha": not validation_errors,
                "outside_unchanged_oracle": not validation_errors,
                "nonmenu_fullframe_zero": oracle["statistics"][
                    "nonmenu_full_frame_pair_count"
                ]
                == 0,
                "deterministic_rerun_zero_diff": deterministic_equal,
                "mutation_negatives_fail_closed": mutation_pass,
                "physical_boundary_browser_guards_not_shared": True,
            },
            "validation_errors": validation_errors,
            "deterministic_rerun": {
                "result": "0 diff" if deterministic_equal else "DIFF",
                "files": deterministic_files,
            },
            "mutation_negatives": {
                "result": f"{sum(item['fail_closed'] for item in mutations)}/"
                f"{len(mutations)}",
                "fixtures": mutations,
            },
            "side_effect_counters": {
                "lower_driver_write": 0,
                "platform_write": 0,
                "firmware_write": 0,
                "hardware": 0,
                "prompt": 0,
                "push": 0,
            },
        }
        write_bytes(args.machine_result.resolve(), json_bytes(result))

    print(
        json.dumps(
            {
                "status": machine_status or "GENERATED",
                "state_count": oracle["state_count"],
                "transition_mask_count": oracle["transition_mask_count"],
                "expanded_pair_count": oracle["expanded_pair_count"],
                "pixel_noop_pair_count": oracle["statistics"]["pixel_noop_pair_count"],
                "full_frame_pair_count": oracle["statistics"]["full_frame_pair_count"],
                "nonmenu_full_frame_pair_count": oracle["statistics"][
                    "nonmenu_full_frame_pair_count"
                ],
                "max_payload_bytes": oracle["statistics"]["max_payload_bytes"],
                "max_nonmenu_payload_bytes": oracle["statistics"][
                    "max_nonmenu_payload_bytes"
                ],
                "oracle_sha256": file_sha(oracle_path),
                "boundary_sha256": file_sha(boundary_path),
            },
            indent=2,
        )
    )
    return 0 if machine_status in (None, "PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
