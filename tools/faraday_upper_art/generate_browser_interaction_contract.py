#!/usr/bin/env python3
"""Generate the WB55 interaction constants from the fixed browser contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


FAMILIES = [
    "calm",
    "curious",
    "delighted",
    "warm",
    "playful",
    "sleepy",
    "bashful",
    "thoughtful",
    "focused",
    "alert",
]

MENU_KINDS = {
    "navigate": 1,
    "status": 2,
    "action": 3,
    "option": 4,
    "toggle": 5,
    "cycle": 6,
    "back": 7,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def scaled(value: object, scale: int) -> int:
    result = round(float(value) * scale)
    if abs(result / scale - float(value)) > 1e-9:
        raise ValueError(f"value is not exactly representable at scale {scale}: {value}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--cemp-manifest", type=Path)
    parser.add_argument("--source-pack-manifest", type=Path)
    parser.add_argument("--generation-manifest", type=Path)
    parser.add_argument("--expected-page-sha256", required=True)
    parser.add_argument("--expected-resource-page-sha256")
    parser.add_argument("--output-header", required=True, type=Path)
    parser.add_argument("--output-receipt", type=Path)
    args = parser.parse_args()

    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    source = contract.get("source", {})
    if contract.get("schema") != "companion.browser_interaction_contract.v1":
        raise ValueError("unsupported browser interaction contract")
    if contract.get("status") != "PASS":
        raise ValueError("browser interaction contract is not passing")
    if source.get("page_sha256", "").upper() != args.expected_page_sha256.upper():
        raise ValueError("browser interaction page identity changed")
    if contract.get("family_order") != FAMILIES:
        raise ValueError("browser/firmware family order differs")
    scoring = contract.get("scoring", {})
    if scoring.get("implementation") != "browser_affect_score_v1":
        raise ValueError("unsupported browser affect scorer")
    scale = int(scoring.get("scale", 0))
    if scale != 20:
        raise ValueError("browser affect score scale changed")

    gesture = contract["gesture"]
    menu_hold_milestones = gesture.get("menu_hold_milestones", [])
    if len(menu_hold_milestones) != 4:
        raise ValueError("browser menu-hold milestone coverage must contain four frames")
    menu_hold_ms = int(gesture["menu_hold_ms"])
    recognition_ms = int(gesture["menu_hold_recognition_ms"])
    fill_span_ms = menu_hold_ms - recognition_ms
    if fill_span_ms <= 0 or fill_span_ms % len(menu_hold_milestones) != 0:
        raise ValueError("browser menu-hold fill cadence is not evenly authored")
    fill_step_ms = fill_span_ms // len(menu_hold_milestones)
    for bucket, milestone in enumerate(menu_hold_milestones):
        held_ms = int(milestone.get("held_ms", -1))
        if milestone.get("bucket") != bucket:
            raise ValueError("browser menu-hold milestones are out of order")
        if milestone.get("state_id") != f"menu_hold_{held_ms}ms":
            raise ValueError("browser menu-hold state id does not bind held_ms")
        expected_held_ms = recognition_ms + (bucket + 1) * fill_step_ms
        if held_ms != expected_held_ms:
            raise ValueError("browser menu-hold milestone differs from authored fill cadence")
        if bucket > 0 and held_ms <= int(menu_hold_milestones[bucket - 1]["held_ms"]):
            raise ValueError("browser menu-hold milestones are not strictly increasing")
        if bucket + 1 == len(menu_hold_milestones) and held_ms != menu_hold_ms:
            raise ValueError("browser menu-hold final milestone must reach menu entry")
    tap = contract["tap"]
    zones = tap["local_zones"]
    expected_zones = ["up", "down", "left", "right", "center"]
    if [zone["name"] for zone in zones] != expected_zones:
        raise ValueError("browser local tap zone order changed")
    centers = contract["affect_centers"]
    graph = contract["affect_graph"]
    if set(centers) != set(FAMILIES) or set(graph) != set(FAMILIES):
        raise ValueError("browser affect family coverage changed")

    menu = contract.get("menu", {})
    menu_screens = menu.get("screens", [])
    menu_screen_names = menu.get("screen_names", [])
    if len(menu_screens) != len(menu_screen_names) or not menu_screens:
        raise ValueError("browser menu screen contract is incomplete")
    menu_rows: list[dict] = []
    menu_item_counts: list[int] = []
    menu_item_ids: list[str] = []
    for expected_screen, screen in enumerate(menu_screens):
        if screen.get("screen") != expected_screen:
            raise ValueError("browser menu screens are out of order")
        if screen.get("name") != menu_screen_names[expected_screen]:
            raise ValueError("browser menu screen name differs")
        rows = screen.get("rows", [])
        menu_item_counts.append(len(rows))
        for expected_index, row in enumerate(rows):
            kind = row.get("kind")
            target = row.get("target")
            if row.get("index") != expected_index or kind not in MENU_KINDS:
                raise ValueError("browser menu row contract is invalid")
            if kind == "navigate":
                if not isinstance(target, int) or not 0 <= target < len(menu_screens):
                    raise ValueError("browser menu navigation target is invalid")
            elif target is not None:
                raise ValueError("non-navigation browser menu row has a target")
            item_id = str(row.get("id", ""))
            if not re.fullmatch(r"[a-z][a-z0-9_]*", item_id):
                raise ValueError("browser menu row id is invalid")
            if item_id not in menu_item_ids:
                menu_item_ids.append(item_id)
            menu_rows.append({
                "screen": expected_screen,
                "index": expected_index,
                "kind": MENU_KINDS[kind],
                "target": 255 if target is None else target,
                "item": item_id,
            })
    menu_item_values = {name: index + 1 for index, name in enumerate(menu_item_ids)}
    menu_contract_rows = [
        "  {"
        f"{row['screen']}u, {row['index']}u, {row['kind']}u, "
        f"{row['target']}u, {menu_item_values[row['item']]}u"
        "},"
        for row in menu_rows
    ]
    menu_item_enum_rows = [
        f"  COMPANION_BROWSER_MENU_ITEM_{name.upper()} = {value}u,"
        for name, value in menu_item_values.items()
    ]

    zone_order = ["center", "up", "down", "left", "right"]
    cemp_clips: set[str] = set()
    cemp_states: set[str] = set()
    if args.cemp_manifest is not None:
        cemp_manifest = json.loads(
            args.cemp_manifest.read_text(encoding="utf-8")
        )
        cemp_clips = {
            clip["name"] for clip in cemp_manifest.get("clips", [])
        }
        cemp_states = set(
            cemp_manifest.get("source", {}).get(
                "state_to_canonical_frame", {}
            )
        )
    source_states = set(cemp_states)
    source_state_rows: list[dict] = []
    if args.source_pack_manifest is not None:
        source_pack = json.loads(
            args.source_pack_manifest.read_text(encoding="utf-8")
        )
        if source_pack.get("status") != "PASS":
            raise ValueError("browser source pack is not passing")
        expected_resource_page = (
            args.expected_resource_page_sha256 or source["page_sha256"]
        ).upper()
        if (
            source_pack.get("source", {}).get("page_sha256", "").upper()
            != expected_resource_page
        ):
            raise ValueError("browser resource page identity differs")
        source_state_rows = source_pack.get("states", [])
        source_states = {state["id"] for state in source_state_rows}
    menu_hold_states = {row["state_id"] for row in menu_hold_milestones}
    if source_states and not menu_hold_states.issubset(source_states):
        raise ValueError("browser source pack is missing menu-hold milestone states")
    menu_hold_rows = [
        "  {"
        f"{int(row['held_ms'])}u, {json.dumps(row['state_id'])}"
        "},"
        for row in menu_hold_milestones
    ]
    menu_phase = {"normal": 0, "ack": 1, "processing": 2, "result": 3}
    menu_state_count = 0
    menu_variant_counts: dict[int, int] = {}
    for state in source_state_rows:
        if state.get("kind") != "menu_ui":
            continue
        if state["locale"] not in ("en", "zh_cn"):
            raise ValueError(f"unsupported browser menu locale: {state['locale']}")
        if state["phase"] not in menu_phase:
            raise ValueError(f"unsupported browser menu phase: {state['phase']}")
        locale = 0 if state["locale"] == "en" else 1
        absolute_index = state.get("absolute_index")
        screen = int(state["screen"])
        variant = int(state.get("menu_variant", 0))
        menu_variant_counts[screen] = max(
            menu_variant_counts.get(screen, 0), variant + 1
        )
        menu_state_count += 1

    life_episode_sets = {family: set() for family in FAMILIES}
    life_commit_counts = {family: 0 for family in FAMILIES}
    for state in source_state_rows:
        if state.get("kind") != "life":
            continue
        family = state.get("family")
        episode = state.get("action_episode")
        if family not in life_episode_sets or not isinstance(episode, int):
            raise ValueError("browser life state metadata is incomplete")
        life_episode_sets[family].add(episode)
        life_commit_counts[family] += int(state.get("dwell_commits", 1))
    life_episode_limits = []
    for family in FAMILIES:
        episodes = life_episode_sets[family]
        if not episodes or episodes != set(range(max(episodes) + 1)):
            raise ValueError(f"browser life episode coverage is incomplete: {family}")
        life_episode_limits.append(max(episodes) + 1)
        if life_commit_counts[family] < 100:
            raise ValueError(f"browser life commit coverage is below 100: {family}")
    product_life_family_mask = sum(1 << index for index in range(len(FAMILIES)))
    living_motion = contract.get("living_motion", {})
    if (
        living_motion.get("scheduler") != "semantic_sparse_life_v3"
        or living_motion.get("low_power_sleep_exception")
        != "sleepy_stable_frame_stops_main_scheduler"
        or living_motion.get("awake_continuous") is not True
    ):
        raise ValueError("browser awake living-motion contract is incomplete")
    natural_blink = living_motion.get("natural_blink", {})
    blink_cadence_ms = int(natural_blink.get("cadence_ms", 0))
    blink_first_commits = int(natural_blink.get("first_interval_commits", 0))
    blink_intervals = [
        int(value) for value in natural_blink.get("interval_commits", [])
    ]
    if (
        blink_cadence_ms <= 0
        or blink_first_commits <= 0
        or not blink_intervals
        or len(blink_intervals) > 255
        or any(value <= 0 or value > 255 for value in blink_intervals)
        or natural_blink.get("closed_commits") != 1
        or natural_blink.get("exact_open_next_commit") is not True
        or natural_blink.get("nonperiodic") is not True
    ):
        raise ValueError("browser natural-blink contract is incomplete")
    blink_eye_bounds_by_family = natural_blink.get("eye_bounds_by_family", {})
    blink_authored_eye_bounds = natural_blink.get(
        "authored_closed_eye_bounds", []
    )
    blink_authored_eye_points = natural_blink.get(
        "authored_closed_eye_points", []
    )

    def blink_box(value: object, label: str) -> list[int]:
        if (
            not isinstance(value, list)
            or len(value) != 4
            or any(not isinstance(item, int) for item in value)
        ):
            raise ValueError(f"browser blink eye box is invalid: {label}")
        x, y, width, height = value
        if (
            x < 0
            or y < 0
            or width < 1
            or height < 1
            or x + width > 200
            or y + height > 200
        ):
            raise ValueError(f"browser blink eye box is outside the panel: {label}")
        return [x, y, width, height]

    awake_families = [family for family in FAMILIES if family != "sleepy"]
    if set(blink_eye_bounds_by_family) != set(awake_families):
        raise ValueError("browser blink eye family coverage is incomplete")
    blink_family_boxes: list[list[list[int]]] = []
    for family in FAMILIES:
        if family == "sleepy":
            blink_family_boxes.append([[0, 0, 0, 0], [0, 0, 0, 0]])
            continue
        boxes = blink_eye_bounds_by_family[family]
        if not isinstance(boxes, list) or len(boxes) != 2:
            raise ValueError(f"browser blink eye pair is invalid: {family}")
        blink_family_boxes.append(
            [blink_box(box, f"{family}/{side}") for side, box in enumerate(boxes)]
        )
    if not isinstance(blink_authored_eye_bounds, list) or len(blink_authored_eye_bounds) != 2:
        raise ValueError("browser authored closed-eye pair is invalid")
    blink_authored_eye_bounds = [
        blink_box(box, f"authored/{side}")
        for side, box in enumerate(blink_authored_eye_bounds)
    ]
    if not isinstance(blink_authored_eye_points, list) or len(blink_authored_eye_points) != 2:
        raise ValueError("browser authored closed-eye point pair is invalid")
    blink_authored_relative_points: list[list[list[int]]] = []
    for side, points in enumerate(blink_authored_eye_points):
        if not isinstance(points, list) or not points:
            raise ValueError(f"browser authored closed-eye points are missing: {side}")
        x, y, width, height = blink_authored_eye_bounds[side]
        center_x = x + width // 2
        center_y = y + height // 2
        normalized: list[list[int]] = []
        seen: set[tuple[int, int]] = set()
        for point in points:
            if (
                not isinstance(point, list)
                or len(point) != 2
                or any(not isinstance(value, int) for value in point)
            ):
                raise ValueError(f"browser authored closed-eye point is invalid: {side}")
            point_x, point_y = point
            if not (x <= point_x < x + width and y <= point_y < y + height):
                raise ValueError(f"browser authored closed-eye point is outside its box: {side}")
            if (point_x, point_y) in seen:
                raise ValueError(f"browser authored closed-eye point is duplicated: {side}")
            seen.add((point_x, point_y))
            relative = [point_x - center_x, point_y - center_y]
            if any(value < -128 or value > 127 for value in relative):
                raise ValueError(f"browser authored closed-eye point exceeds int8: {side}")
            normalized.append(relative)
        blink_authored_relative_points.append(normalized)
    blink_family_rows = [
        "  {" + ", ".join(
            "{" + ", ".join(f"{value}u" for value in box) + "}"
            for box in boxes
        ) + "},"
        for boxes in blink_family_boxes
    ]
    blink_authored_rows = [
        "  {" + ", ".join(f"{value}u" for value in box) + "},"
        for box in blink_authored_eye_bounds
    ]
    blink_pixel_offsets = [0]
    blink_pixel_rows: list[str] = []
    for points in blink_authored_relative_points:
        blink_pixel_rows.extend(
            f"  {{{point[0]}, {point[1]}}}," for point in points
        )
        blink_pixel_offsets.append(len(blink_pixel_rows))

    generation = {}
    pointer_state_grid = [
        [[None for _ in range(5)] for _ in range(5)] for _ in FAMILIES
    ]
    if args.generation_manifest is not None:
        generation = json.loads(
            args.generation_manifest.read_text(encoding="utf-8")
        )
        if generation.get("status") != "PASS":
            raise ValueError("browser product generation is not passing")
        expected_resource_page = (
            args.expected_resource_page_sha256 or source["page_sha256"]
        ).upper()
        if generation.get("page_sha256", "").upper() != expected_resource_page:
            raise ValueError("browser product generation page identity differs")
        pattern = re.compile(
            r"^pointer_follow_([a-z]+)_gx([02468])_gy([02468])$"
        )
        for state_id in generation.get("entries_by_id", {}):
            match = pattern.fullmatch(state_id)
            if match is None:
                continue
            family, gx, gy = match.groups()
            if family not in FAMILIES:
                raise ValueError(f"unknown pointer family: {family}")
            pointer_state_grid[FAMILIES.index(family)][int(gx) // 2][
                int(gy) // 2
            ] = state_id
        pointer_count = sum(
            state is not None
            for family in pointer_state_grid
            for gx in family
            for state in gx
        )
        if pointer_count != len(FAMILIES) * 25:
            raise ValueError("browser product generation pointer coverage is incomplete")
        resource_id = generation.get("resource_id", "")
        if not re.fullmatch(r"[0-9A-F]{64}", resource_id):
            raise ValueError("browser product generation resource id is invalid")
    else:
        pointer_count = 0
        resource_id = ""

    pointer_family_rows = []
    for family_index, family in enumerate(pointer_state_grid):
        gx_rows = []
        for gx in family:
            gx_rows.append(
                "{" + ", ".join(
                    json.dumps(state) if state is not None else "(const char *)0"
                    for state in gx
                ) + "}"
            )
        pointer_family_rows.append(
            "  {" + ", ".join(gx_rows) + f"}}, /* {FAMILIES[family_index]} */"
        )
    resource_id_bytes = [
        int(resource_id[index:index + 2], 16)
        for index in range(0, len(resource_id), 2)
    ]
    if not resource_id_bytes:
        resource_id_bytes = [0] * 32
    local_state_rows = []
    for family in FAMILIES:
        states = [f"tap_local_{family}_{zone}" for zone in zone_order]
        if cemp_states and not set(states).issubset(cemp_states):
            raise ValueError(
                f"CEMP is missing browser local tap states for {family}"
            )
        local_state_rows.append(
            "  {"
            + ", ".join(json.dumps(state) for state in states)
            + f"}}, /* {family} */"
        )

    legacy_transition_clips = [
        f"tap.transition.{zone}"
        if not cemp_clips or f"tap.transition.{zone}" in cemp_clips
        else None
        for zone in zone_order
    ]
    legacy_transition_row = ", ".join(
        json.dumps(name) if name is not None else "(const char *)0"
        for name in legacy_transition_clips
    )

    has_edge_clips = any(name.startswith("tap.edge.") for name in cemp_clips)
    edge_rows = []
    edge_state_rows = []
    edge_phases = ["orient", "anticipate", "accent", "follow", "settle"]
    for source_name in FAMILIES:
        for target_name in graph[source_name]:
            clips = [
                f"tap.edge.{source_name}.{target_name}.{zone}"
                for zone in zone_order
            ]
            if has_edge_clips and not set(clips).issubset(cemp_clips):
                raise ValueError(
                    "CEMP browser affect edge coverage is incomplete: "
                    f"{source_name}->{target_name}"
                )
            if has_edge_clips:
                edge_rows.append(
                    "  {"
                    f"{FAMILIES.index(source_name)}u, "
                    f"{FAMILIES.index(target_name)}u, "
                    + "{"
                    + ", ".join(json.dumps(clip) for clip in clips)
                    + "}"
                    + f"}}, /* {source_name}->{target_name} */"
                )
            state_grid = [
                [
                    f"tap_edge_{source_name}_{target_name}_{zone}_{phase}"
                    for phase in edge_phases
                ]
                for zone in zone_order
            ]
            edge_states = {
                state for zone_states in state_grid for state in zone_states
            }
            if edge_states.issubset(source_states):
                zone_rows = [
                    "{" + ", ".join(json.dumps(state) for state in states) + "}"
                    for states in state_grid
                ]
                edge_state_rows.append(
                    "  {"
                    f"{FAMILIES.index(source_name)}u, "
                    f"{FAMILIES.index(target_name)}u, "
                    + "{"
                    + ", ".join(zone_rows)
                    + "}"
                    + f"}}, /* {source_name}->{target_name} */"
                )
            elif any(state in source_states for state in edge_states):
                raise ValueError(
                    "browser affect edge state coverage is incomplete: "
                    f"{source_name}->{target_name}"
                )
    has_edge_states = len(edge_state_rows) == len(edge_rows) if edge_rows else (
        len(edge_state_rows) == sum(len(graph[name]) for name in FAMILIES)
    )

    center_rows = ",\n".join(
        f"  {{{int(centers[name][0])}, {int(centers[name][1])}}} /* {name} */"
        for name in FAMILIES
    )
    graph_rows = []
    for name in FAMILIES:
        mask = sum(1 << FAMILIES.index(target) for target in graph[name])
        graph_rows.append(f"  0x{mask:04X}u, /* {name} */")

    trace_rows = []
    for step in contract["trace"]:
        point = step["point"]
        trace_rows.append(
            "  {"
            f"{round(float(point[0]) * 200)}u, "
            f"{round(float(point[1]) * 200)}u, "
            f"{FAMILIES.index(step['target'])}u, "
            f"{FAMILIES.index(step['family_after'])}u, "
            f"{1 if step['transition'] else 0}u, "
            f"{int(step['evidence_after'])}u"
            f"}}, /* {step['index']} {step['zone']} */"
        )

    pointer_grid = gesture.get("pointer_grid")
    if pointer_grid != [9, 9]:
        raise ValueError("browser pointer grid must be the authored 9x9 grid")
    scalar_contract = {
        "COMPANION_BROWSER_INTERACTION_MENU_RIGHT_EXIT_THRESHOLD_200": scaled(
            gesture["menu_right_exit_threshold"], 200
        ),
        "COMPANION_BROWSER_INTERACTION_MENU_VERTICAL_SWIPE_THRESHOLD_200": scaled(
            gesture["menu_vertical_swipe_threshold"], 200
        ),
        "COMPANION_BROWSER_INTERACTION_MENU_SCROLL_CADENCE_MS": int(
            gesture["menu_scroll_cadence_ms"]
        ),
        "COMPANION_BROWSER_INTERACTION_MENU_SCROLL_QUANTUM_PX": int(
            gesture["menu_scroll_quantum_px"]
        ),
        "COMPANION_BROWSER_INTERACTION_MENU_ROW_HEIGHT_PX": int(
            gesture["menu_row_height_px"]
        ),
        "COMPANION_BROWSER_INTERACTION_POINTER_GRID_WIDTH": int(pointer_grid[0]),
        "COMPANION_BROWSER_INTERACTION_POINTER_GRID_HEIGHT": int(pointer_grid[1]),
        "COMPANION_BROWSER_INTERACTION_POINTER_FOLLOW_CADENCE_MS": int(
            gesture["pointer_follow_cadence_ms"]
        ),
        "COMPANION_BROWSER_INTERACTION_POINTER_FOLLOW_MAX_STEP_PX_PER_AXIS": int(
            gesture["pointer_follow_max_step_px_per_axis"]
        ),
        "COMPANION_BROWSER_INTERACTION_POINTER_FOLLOW_RELEASE_RETURN_COMMITS": int(
            gesture["pointer_follow_release_return_commits"]
        ),
        "COMPANION_BROWSER_INTERACTION_RECORDING_TRIGGER_DX_200": scaled(
            gesture["recording_trigger_dx"], 200
        ),
        "COMPANION_BROWSER_INTERACTION_RECORDING_MAX_DY_200": scaled(
            gesture["recording_max_dy"], 200
        ),
        "COMPANION_BROWSER_INTERACTION_RECORDING_MIN_HOLD_MS": int(
            gesture["recording_min_hold_ms"]
        ),
        "COMPANION_BROWSER_INTERACTION_RECORDING_VISIBLE_STAGES": int(
            gesture["recording_visible_stages"]
        ),
        "COMPANION_BROWSER_INTERACTION_RECORDING_VISIBLE_CADENCE_MS": int(
            gesture["recording_visible_cadence_ms"]
        ),
    }
    if any(value <= 0 for value in scalar_contract.values()):
        raise ValueError("browser gesture contract values must be positive")
    macros = {
        "COMPANION_BROWSER_INTERACTION_DOUBLE_TAP_GAP_MS": int(
            gesture["double_tap_gap_ms"]
        ),
        "COMPANION_BROWSER_INTERACTION_DOUBLE_TAP_MAX_DISTANCE_200": round(
            float(gesture["double_tap_max_distance"]) * 200
        ),
        "COMPANION_BROWSER_INTERACTION_MENU_HOLD_MS": int(gesture["menu_hold_ms"]),
        "COMPANION_BROWSER_INTERACTION_MENU_HOLD_RECOGNITION_MS": int(
            gesture["menu_hold_recognition_ms"]
        ),
        "COMPANION_BROWSER_INTERACTION_RECORDING_CORNER_MAX_X_200": round(
            float(gesture["recording_corner_max_x"]) * 200
        ),
        "COMPANION_BROWSER_INTERACTION_RECORDING_CORNER_MIN_Y_200": round(
            float(gesture["recording_corner_min_y"]) * 200
        ),
        "COMPANION_BROWSER_INTERACTION_EVIDENCE_WINDOW_MS": int(
            tap["evidence_window_ms"]
        ),
        "COMPANION_BROWSER_INTERACTION_SWITCH_THRESHOLD": int(
            tap["family_switch_threshold"]
        ),
        "COMPANION_BROWSER_BLINK_CADENCE_MS": blink_cadence_ms,
        "COMPANION_BROWSER_BLINK_FIRST_INTERVAL_COMMITS": blink_first_commits,
        "COMPANION_BROWSER_INTERACTION_ZONE_UP_Y_200": round(
            float(zones[0]["threshold"]) * 200
        ),
        "COMPANION_BROWSER_INTERACTION_ZONE_DOWN_Y_200": round(
            float(zones[1]["threshold"]) * 200
        ),
        "COMPANION_BROWSER_INTERACTION_ZONE_LEFT_X_200": round(
            float(zones[2]["threshold"]) * 200
        ),
        "COMPANION_BROWSER_INTERACTION_ZONE_RIGHT_X_200": round(
            float(zones[3]["threshold"]) * 200
        ),
        **scalar_contract,
    }
    macro_lines = [
        f"#define {name} {value}u" for name, value in macros.items()
    ]
    header = "\n".join(
        [
            "#ifndef COMPANION_BROWSER_INTERACTION_CONTRACT_H",
            "#define COMPANION_BROWSER_INTERACTION_CONTRACT_H",
            "",
            "#include <stdbool.h>",
            "#include <stddef.h>",
            "#include <stdint.h>",
            "#include <stdio.h>",
            "",
            "/* Generated from the fixed browser page. Do not edit. */",
            f'#define COMPANION_BROWSER_INTERACTION_PAGE_SHA256 '
            f'"{source["page_sha256"].upper()}"',
            f'#define COMPANION_BROWSER_INTERACTION_CONTRACT_SHA256 "{sha256(args.contract)}"',
            f'#define COMPANION_BROWSER_INTERACTION_SCORE_FUNCTION_SHA256 '
            f'"{scoring["score_function_sha256"]}"',
            f'#define COMPANION_BROWSER_INTERACTION_EVENT_FUNCTION_SHA256 '
            f'"{scoring["event_function_sha256"]}"',
            f'#define COMPANION_BROWSER_INTERACTION_PRODUCT_RESOURCE_ID '
            f'"{resource_id}"',
            *macro_lines,
            "#define COMPANION_BROWSER_INTERACTION_SCORE_SCALE 20",
            f"#define COMPANION_BROWSER_INTERACTION_HAS_EDGE_CLIPS "
            f"{1 if has_edge_clips else 0}",
            f"#define COMPANION_BROWSER_INTERACTION_EDGE_CLIP_COUNT "
            f"{len(edge_rows)}u",
            f"#define COMPANION_BROWSER_INTERACTION_HAS_EDGE_STATES "
            f"{1 if has_edge_states else 0}",
            f"#define COMPANION_BROWSER_INTERACTION_EDGE_STATE_COUNT "
            f"{len(edge_state_rows)}u",
            "#define COMPANION_BROWSER_INTERACTION_EDGE_PHASE_COUNT 5u",
            "#define COMPANION_BROWSER_INTERACTION_TRACE_COUNT "
            f"{len(trace_rows)}u",
            "#define COMPANION_BROWSER_INTERACTION_MENU_HOLD_MILESTONE_COUNT "
            f"{len(menu_hold_rows)}u",
            "#define COMPANION_BROWSER_INTERACTION_HAS_PRODUCT_GENERATION "
            f"{1 if generation else 0}",
            "#define COMPANION_BROWSER_INTERACTION_POINTER_STATE_COUNT "
            f"{pointer_count}u",
            "#define COMPANION_BROWSER_INTERACTION_MENU_STATE_COUNT "
            f"{menu_state_count}u",
            "#define COMPANION_BROWSER_MENU_SCREEN_COUNT "
            f"{len(menu_screens)}u",
            "#define COMPANION_BROWSER_MENU_ROW_COUNT "
            f"{len(menu_contract_rows)}u",
            "#define COMPANION_BROWSER_MENU_VISIBLE_ROWS "
            f"{int(menu['visible_rows'])}u",
            "#define COMPANION_BROWSER_MENU_ROW_HEIGHT_PX "
            f"{int(menu['row_height_px'])}u",
            "#define COMPANION_BROWSER_MENU_TAP_ACK_MS "
            f"{int(menu['tap_ack_ms'])}u",
            "#define COMPANION_BROWSER_MENU_ACTION_PROCESSING_MS "
            f"{int(menu['action_processing_ms'])}u",
            "#define COMPANION_BROWSER_INTERACTION_PRODUCT_LIFE_FAMILY_MASK "
            f"0x{product_life_family_mask:04X}u",
            "#define COMPANION_BROWSER_INTERACTION_AWAKE_LIFE_CONTINUOUS 1",
            "#define COMPANION_BROWSER_BLINK_INTERVAL_COUNT "
            f"{len(blink_intervals)}u",
            "",
            "typedef struct {",
            "  uint8_t x;",
            "  uint8_t y;",
            "  uint8_t width;",
            "  uint8_t height;",
            "} companion_browser_blink_eye_box_t;",
            "",
            "typedef struct {",
            "  int8_t x;",
            "  int8_t y;",
            "} companion_browser_blink_eye_pixel_t;",
            "",
            "typedef struct {",
            "  int8_t x;",
            "  int8_t y;",
            "} companion_browser_affect_center_t;",
            "",
            "typedef struct {",
            "  uint16_t x;",
            "  uint16_t y;",
            "  uint8_t target_family;",
            "  uint8_t family_after;",
            "  uint8_t transition;",
            "  uint8_t evidence_after;",
            "} companion_browser_interaction_trace_step_t;",
            "",
            "typedef struct {",
            "  uint16_t held_ms;",
            "  const char *state_id;",
            "} companion_browser_menu_hold_milestone_t;",
            "",
            "typedef enum {",
            "  COMPANION_BROWSER_MENU_KIND_NONE = 0u,",
            "  COMPANION_BROWSER_MENU_KIND_NAVIGATE = 1u,",
            "  COMPANION_BROWSER_MENU_KIND_STATUS = 2u,",
            "  COMPANION_BROWSER_MENU_KIND_ACTION = 3u,",
            "  COMPANION_BROWSER_MENU_KIND_OPTION = 4u,",
            "  COMPANION_BROWSER_MENU_KIND_TOGGLE = 5u,",
            "  COMPANION_BROWSER_MENU_KIND_CYCLE = 6u,",
            "  COMPANION_BROWSER_MENU_KIND_BACK = 7u,",
            "} companion_browser_menu_kind_t;",
            "",
            "typedef enum {",
            "  COMPANION_BROWSER_MENU_ITEM_NONE = 0u,",
            *menu_item_enum_rows,
            "} companion_browser_menu_item_t;",
            "",
            "typedef struct {",
            "  uint8_t screen;",
            "  uint8_t index;",
            "  uint8_t kind;",
            "  uint8_t target;",
            "  uint8_t item;",
            "} companion_browser_menu_row_t;",
            "",
            "typedef struct {",
            "  uint8_t source_family;",
            "  uint8_t target_family;",
            "  const char *zone_clips[5];",
            "} companion_browser_interaction_edge_clip_t;",
            "",
            "typedef struct {",
            "  uint8_t source_family;",
            "  uint8_t target_family;",
            "  const char *zone_phase_states[5][5];",
            "} companion_browser_interaction_edge_state_t;",
            "",
            "static const char *const companion_browser_tap_local_state_ids[10][5] = {",
            *local_state_rows,
            "};",
            "",
            "static const char *const companion_browser_legacy_transition_clips[5] = {",
            f"  {legacy_transition_row}",
            "};",
            "",
            "static const uint8_t companion_browser_generation_resource_id[32] = {",
            "  " + ", ".join(f"0x{value:02X}u" for value in resource_id_bytes),
            "};",
            "",
            "static const uint8_t companion_browser_life_episode_limits[10] = {",
            "  " + ", ".join(f"{limit}u" for limit in life_episode_limits),
            "};",
            "",
            "static const uint8_t companion_browser_blink_interval_commits",
            "    [COMPANION_BROWSER_BLINK_INTERVAL_COUNT] = {",
            "  " + ", ".join(f"{value}u" for value in blink_intervals),
            "};",
            "",
            "static const companion_browser_blink_eye_box_t",
            "    companion_browser_blink_eye_bounds[10][2] = {",
            *blink_family_rows,
            "};",
            "",
            "static const companion_browser_blink_eye_box_t",
            "    companion_browser_blink_authored_closed_eye_bounds[2] = {",
            *blink_authored_rows,
            "};",
            "",
            "static const uint16_t companion_browser_blink_authored_pixel_offsets[3] = {",
            "  " + ", ".join(f"{value}u" for value in blink_pixel_offsets),
            "};",
            "",
            "static const companion_browser_blink_eye_pixel_t",
            "    companion_browser_blink_authored_closed_eye_pixels",
            f"    [{len(blink_pixel_rows)}] = {{",
            *blink_pixel_rows,
            "};",
            "",
            "#if COMPANION_BROWSER_INTERACTION_HAS_PRODUCT_GENERATION",
            "static const char *const companion_browser_pointer_state_ids[10][5][5] = {",
            *pointer_family_rows,
            "};",
            "#endif",
            "",
            "static const uint8_t companion_browser_menu_variant_counts",
            "    [COMPANION_BROWSER_MENU_SCREEN_COUNT] = {",
            "  " + ", ".join(
                f"{menu_variant_counts.get(screen, 1)}u"
                for screen in range(len(menu_screens))
            ),
            "};",
            "",
            "static const uint8_t companion_browser_menu_item_counts",
            "    [COMPANION_BROWSER_MENU_SCREEN_COUNT] = {",
            "  " + ", ".join(f"{count}u" for count in menu_item_counts),
            "};",
            "",
            "static const companion_browser_menu_row_t companion_browser_menu_rows",
            "    [COMPANION_BROWSER_MENU_ROW_COUNT] = {",
            *menu_contract_rows,
            "};",
            "",
            "#if COMPANION_BROWSER_INTERACTION_HAS_EDGE_CLIPS",
            "static const companion_browser_interaction_edge_clip_t",
            "    companion_browser_interaction_edge_clips"
            "[COMPANION_BROWSER_INTERACTION_EDGE_CLIP_COUNT] = {",
            *edge_rows,
            "};",
            "#endif",
            "",
            "#if COMPANION_BROWSER_INTERACTION_HAS_EDGE_STATES",
            "static const companion_browser_interaction_edge_state_t",
            "    companion_browser_interaction_edge_states",
            "[COMPANION_BROWSER_INTERACTION_EDGE_STATE_COUNT] = {",
            *edge_state_rows,
            "};",
            "#endif",
            "",
            "static inline const char *companion_browser_tap_local_state_id(",
            "    uint8_t family, uint8_t zone)",
            "{",
            "  return family < 10u && zone < 5u",
            "      ? companion_browser_tap_local_state_ids[family][zone]",
            "      : (const char *)0;",
            "}",
            "",
            "static inline const char *companion_browser_legacy_transition_clip(",
            "    uint8_t zone)",
            "{",
            "  return zone < 5u",
            "      ? companion_browser_legacy_transition_clips[zone]",
            "      : (const char *)0;",
            "}",
            "",
            "static inline const char *companion_browser_pointer_state_id(",
            "    uint8_t family, uint8_t grid_x, uint8_t grid_y)",
            "{",
            "#if COMPANION_BROWSER_INTERACTION_HAS_PRODUCT_GENERATION",
            "  if (family < 10u && grid_x <= 8u && grid_y <= 8u &&",
            "      (grid_x & 1u) == 0u && (grid_y & 1u) == 0u) {",
            "    return companion_browser_pointer_state_ids[family][grid_x / 2u]",
            "        [grid_y / 2u];",
            "  }",
            "#else",
            "  (void)family;",
            "  (void)grid_x;",
            "  (void)grid_y;",
            "#endif",
            "  return (const char *)0;",
            "}",
            "",
            "/* The validated product grid has canonical names. Format into the caller's",
            " * existing workspace so firmware need not retain 250 full strings/pointers.",
            " * Keep the table accessor above for callers that require stable pointers. */",
            "static inline const char *companion_browser_pointer_state_id_format(",
            "    char *destination, size_t destination_size,",
            "    uint8_t family, uint8_t grid_x, uint8_t grid_y)",
            "{",
            "#if COMPANION_BROWSER_INTERACTION_HAS_PRODUCT_GENERATION",
            "  static const char *const families[10] = {",
            "      \"calm\", \"curious\", \"delighted\", \"warm\", \"playful\",",
            "      \"sleepy\", \"bashful\", \"thoughtful\", \"focused\", \"alert\"};",
            "  int written;",
            "  if (destination == NULL || destination_size == 0u || family >= 10u ||",
            "      grid_x > 8u || grid_y > 8u || (grid_x & 1u) || (grid_y & 1u))",
            "    return (const char *)0;",
            "  written = snprintf(destination, destination_size,",
            "      \"pointer_follow_%s_gx%u_gy%u\", families[family],",
            "      (unsigned)grid_x, (unsigned)grid_y);",
            "  if (written >= 0 && (size_t)written < destination_size) return destination;",
            "#else",
            "  (void)destination;",
            "  (void)destination_size;",
            "  (void)family;",
            "  (void)grid_x;",
            "  (void)grid_y;",
            "#endif",
            "  return (const char *)0;",
            "}",
            "",
            "static inline uint8_t companion_browser_life_episode_limit(uint8_t family)",
            "{",
            "  return family < 10u ? companion_browser_life_episode_limits[family] : 0u;",
            "}",
            "",
            "static inline bool companion_browser_menu_state_id_format(",
            "    char *destination, size_t destination_size, uint8_t locale,",
            "    uint8_t screen, uint8_t scroll_row, uint8_t absolute_index,",
            "    uint8_t phase, uint8_t variant)",
            "{",
            "  static const char *const locales[2] = {\"en\", \"zh_cn\"};",
            "  static const char *const phases[4] =",
            "      {\"normal\", \"ack\", \"processing\", \"result\"};",
            "  int written;",
            "  if (destination == NULL || destination_size == 0u || locale >= 2u ||",
            "      screen >= COMPANION_BROWSER_MENU_SCREEN_COUNT || phase >= 4u ||",
            "      variant >= companion_browser_menu_variant_counts[screen] ||",
            "      ((phase == 0u) != (absolute_index == 255u))) return false;",
            "  if (phase == 0u) {",
            "    written = variant == 0u",
            "        ? snprintf(destination, destination_size,",
            "                   \"menu_ui_%s_s%u_o%u_normal\", locales[locale],",
            "                   (unsigned)screen, (unsigned)scroll_row)",
            "        : snprintf(destination, destination_size,",
            "                   \"menu_ui_%s_s%u_o%u_normal_v%u\", locales[locale],",
            "                   (unsigned)screen, (unsigned)scroll_row,",
            "                   (unsigned)variant);",
            "  } else {",
            "    written = variant == 0u",
            "        ? snprintf(destination, destination_size,",
            "                   \"menu_ui_%s_s%u_o%u_%s_i%u\", locales[locale],",
            "                   (unsigned)screen, (unsigned)scroll_row, phases[phase],",
            "                   (unsigned)absolute_index)",
            "        : snprintf(destination, destination_size,",
            "                   \"menu_ui_%s_s%u_o%u_%s_i%u_v%u\", locales[locale],",
            "                   (unsigned)screen, (unsigned)scroll_row, phases[phase],",
            "                   (unsigned)absolute_index, (unsigned)variant);",
            "  }",
            "  return written >= 0 && (size_t)written < destination_size;",
            "}",
            "",
            "static inline const companion_browser_menu_row_t *",
            "companion_browser_menu_row(uint8_t screen, uint8_t index)",
            "{",
            "  uint8_t row;",
            "  for (row = 0u; row < COMPANION_BROWSER_MENU_ROW_COUNT; ++row) {",
            "    if (companion_browser_menu_rows[row].screen == screen &&",
            "        companion_browser_menu_rows[row].index == index) {",
            "      return &companion_browser_menu_rows[row];",
            "    }",
            "  }",
            "  return (const companion_browser_menu_row_t *)0;",
            "}",
            "",
            "static inline const char *companion_browser_tap_edge_clip(",
            "    uint8_t source_family, uint8_t target_family, uint8_t zone)",
            "{",
            "#if COMPANION_BROWSER_INTERACTION_HAS_EDGE_CLIPS",
            "  uint16_t index;",
            "  if (zone >= 5u) return (const char *)0;",
            "  for (index = 0u;",
            "       index < COMPANION_BROWSER_INTERACTION_EDGE_CLIP_COUNT;",
            "       ++index) {",
            "    const companion_browser_interaction_edge_clip_t *const edge =",
            "        &companion_browser_interaction_edge_clips[index];",
            "    if (edge->source_family == source_family &&",
            "        edge->target_family == target_family) {",
            "      return edge->zone_clips[zone];",
            "    }",
            "  }",
            "#else",
            "  (void)source_family;",
            "  (void)target_family;",
            "  (void)zone;",
            "#endif",
            "  return (const char *)0;",
            "}",
            "",
            "static inline const char *companion_browser_tap_edge_state(",
            "    uint8_t source_family, uint8_t target_family,",
            "    uint8_t zone, uint8_t phase)",
            "{",
            "#if COMPANION_BROWSER_INTERACTION_HAS_EDGE_STATES",
            "  uint16_t index;",
            "  if (zone >= 5u || phase >= 5u) return (const char *)0;",
            "  for (index = 0u;",
            "       index < COMPANION_BROWSER_INTERACTION_EDGE_STATE_COUNT;",
            "       ++index) {",
            "    const companion_browser_interaction_edge_state_t *const edge =",
            "        &companion_browser_interaction_edge_states[index];",
            "    if (edge->source_family == source_family &&",
            "        edge->target_family == target_family) {",
            "      return edge->zone_phase_states[zone][phase];",
            "    }",
            "  }",
            "#else",
            "  (void)source_family;",
            "  (void)target_family;",
            "  (void)zone;",
            "  (void)phase;",
            "#endif",
            "  return (const char *)0;",
            "}",
            "",
            "static const companion_browser_affect_center_t",
            "    companion_browser_affect_centers[10] = {",
            center_rows,
            "};",
            "",
            "static const uint16_t companion_browser_affect_graph[10] = {",
            *graph_rows,
            "};",
            "",
            "static const companion_browser_interaction_trace_step_t",
            "    companion_browser_interaction_trace"
            "[COMPANION_BROWSER_INTERACTION_TRACE_COUNT] = {",
            *trace_rows,
            "};",
            "",
            "static const companion_browser_menu_hold_milestone_t",
            "    companion_browser_menu_hold_milestones",
            "[COMPANION_BROWSER_INTERACTION_MENU_HOLD_MILESTONE_COUNT] = {",
            *menu_hold_rows,
            "};",
            "",
            "#endif /* COMPANION_BROWSER_INTERACTION_CONTRACT_H */",
            "",
        ]
    )
    args.output_header.parent.mkdir(parents=True, exist_ok=True)
    args.output_header.write_text(header, encoding="ascii", newline="\n")
    receipt = {
        "status": "PASS",
        "contract_sha256": sha256(args.contract),
        "page_sha256": source["page_sha256"].upper(),
        "resource_page_sha256": (
            args.expected_resource_page_sha256 or source["page_sha256"]
        ).upper(),
        "score_function_sha256": scoring["score_function_sha256"],
        "event_function_sha256": scoring["event_function_sha256"],
        "trace_count": len(trace_rows),
        "menu_hold_milestone_count": len(menu_hold_rows),
        "menu_state_count": menu_state_count,
        "menu_variant_counts": {
            str(screen): menu_variant_counts.get(screen, 1)
            for screen in range(len(menu_screens))
        },
        "menu_screen_count": len(menu_screens),
        "menu_row_count": len(menu_contract_rows),
        "pointer_state_count": pointer_count,
        "product_resource_id": resource_id,
        "life_family_mask": product_life_family_mask,
        "life_episode_limits": dict(zip(FAMILIES, life_episode_limits)),
        "life_commit_counts": life_commit_counts,
        "blink_cadence_ms": blink_cadence_ms,
        "blink_first_interval_commits": blink_first_commits,
        "blink_interval_commits": blink_intervals,
        "blink_eye_bounds_by_family": dict(
            zip(FAMILIES, blink_family_boxes)
        ),
        "blink_authored_closed_eye_bounds": blink_authored_eye_bounds,
        "blink_authored_closed_eye_pixel_counts": [
            len(points) for points in blink_authored_relative_points
        ],
        "generation_manifest_sha256": (
            sha256(args.generation_manifest)
            if args.generation_manifest is not None else None
        ),
        "has_edge_clips": has_edge_clips,
        "edge_clip_count": len(edge_rows),
        "has_edge_states": has_edge_states,
        "edge_state_count": len(edge_state_rows),
    }
    if args.output_receipt:
        args.output_receipt.parent.mkdir(parents=True, exist_ok=True)
        args.output_receipt.write_text(
            json.dumps(receipt, indent=2) + "\n",
            encoding="ascii",
            newline="\n",
        )
    print(json.dumps(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
