#!/usr/bin/env python3
"""Generate the inactive V44 V9 expression-extension profile with stable-center idle and blink."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import generate_companion_v40_two_track_target_profile as v40
import generate_companion_v41_directional_gaze_target_profile as v41


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v6/candidate"
LAYOUT = OUTPUT / "two-track-layout.json"
TRACE = OUTPUT / "target-score-attempt-01/v44-wb55-target-profile-plan.json"
HEADER = ROOT / "app/companion_pendant/epaper/generated/expression_rig_v44_blink_stable_center_candidate_profile.h"
SOURCE = ROOT / "app/companion_pendant/epaper/generated/expression_rig_v44_blink_stable_center_candidate_profile.c"
V41_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v3/candidate/two-track-layout.json"
V39_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v1/candidate/two-track-layout.json"
V22_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/candidate/target-rig-attempt-01/v22-emotion-separation-target-rig-layout.json"
V44_SPECIAL_LAYOUT = OUTPUT / "v44-special-component-layout.json"
LOCKED = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
NO_FUNCTIONAL = 0xFF
GAZE_ORDER = ("center", "left", "right", "up", "down")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path} must contain an object")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def build_layout(v41_layout: dict[str, Any], special: dict[str, Any]) -> dict[str, Any]:
    require(v41_layout.get("schema") == "companion.v41_two_track_directional_gaze_layout.v1" and
            v41_layout.get("locked_v9_source", {}).get("sha256") == LOCKED and
            special.get("schema") == "companion.v44_special_component_export.v1" and
            special.get("locked_v9_source", {}).get("sha256") == LOCKED and
            len(special.get("components", [])) == 50,
            "V42 inherited source authority drifted")
    preview_stories = {
        "calm_presence": {"label_zh": "日常平静", "summary_zh": "默认日常脸，眼神保持正中，停留时同步眨眼。", "overview_step": 2},
        "warm_presence": {"label_zh": "亲近温暖", "summary_zh": "互动记忆较高时的温和回应。", "overview_step": 2},
        "curious_question": {"label_zh": "好奇提问", "summary_zh": "眼神和眉毛先带动，再出现表情自有问号。", "overview_step": 2},
        "alert_exclamation": {"label_zh": "警觉提醒", "summary_zh": "眉眼先进入提醒，再出现表情自有感叹号。", "overview_step": 2},
        "playful_presence": {"label_zh": "活泼玩心", "summary_zh": "高光先活跃，随后回到轻快保持。", "overview_step": 2},
        "sleepy_presence": {"label_zh": "困倦入睡", "summary_zh": "困眼、眉和嘴依次进入，只有 ZZZ 轻轻上浮。", "overview_step": 2},
        "delighted_presence": {"label_zh": "开心雀跃", "summary_zh": "抬眉、开口笑和高腮点形成清楚的开心反应。", "overview_step": 2},
        "bashful_presence": {"label_zh": "害羞轻笑", "summary_zh": "收拢的眉、贴近嘴角的腮点和小笑意表达害羞。", "overview_step": 2},
        "thoughtful_presence": {"label_zh": "安静思考", "summary_zh": "一高一低眉与偏位思考嘴带出安静停顿。", "overview_step": 2},
        "focused_presence": {"label_zh": "认真专注", "summary_zh": "低而圆的收拢眉与短横嘴表达稳定专注。", "overview_step": 2},
        "recording_with_calm": {"label_zh": "录音输入中", "summary_zh": "日常脸旁边播放输入麦克风波纹，绝不覆盖脸。", "overview_step": 2},
        "recording_with_warm": {"label_zh": "录音输入中（温暖脸）", "summary_zh": "同一输入小饰件可与独立温暖表情同时存在。", "overview_step": 2},
        "charging_with_calm": {"label_zh": "无线机座充电", "summary_zh": "日常脸下方显示机座、接触垫和上升能量刻度，不替换脸。", "overview_step": 2},
        "upgrade_with_playful": {"label_zh": "升级进行中", "summary_zh": "活泼脸上叠加独立上行进度装饰。", "overview_step": 2},
        "error_with_calm": {"label_zh": "错误提醒", "summary_zh": "平静脸上叠加独立紧凑警示装饰。", "overview_step": 2},
        "menu_entry_notice": {"label_zh": "进入菜单提示", "summary_zh": "仅短暂显示；随后组件 Rig 完全撤出，菜单独占屏幕。", "overview_step": 2},
    }
    for direction in GAZE_ORDER:
        preview_stories[f"daily_attention_{direction}"] = {
            "label_zh": f"内部眼神-{direction}",
            "summary_zh": "仅作为机器可复现的注意力端点证据，不在人工总览或播放器中展示。",
            "owner_visible": False,
        }
    return {
        "schema": "companion.v44_expression_extension_two_track_layout.v1",
        "status": "CANDIDATE_TRACK_MODEL_VERSIONED_RUNTIME_INACTIVE",
        "revision": 44,
        "authority": ["COMP-REQ-093", "COMP-REQ-239", "COMP-REQ-240", "COMP-REQ-242", "COMP-REQ-243", "COMP-REQ-245", "COMP-REQ-246", "COMP-REQ-247", "COMP-REQ-248", "COMP-REQ-249", "COMP-REQ-250", "COMP-REQ-251", "COMP-REQ-253", "COMP-REQ-254", "COMP-REQ-256", "COMP-REQ-261", "COMP-REQ-263"],
        "locked_v9_source": {"path": "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png", "sha256": LOCKED},
        "inherited_v41": {"path": rel(V41_LAYOUT), "sha256": sha256(V41_LAYOUT),
                            "reuse_rule": "Retain V22 face components, V41 deterministic five-gaze machine endpoints, the dual-track separation rule, and menu withdrawal behavior."},
        "source_authority": {
            "v22_face_layout": {"path": rel(V22_LAYOUT), "sha256": sha256(V22_LAYOUT), "component_count": 37},
            "v44_special_layout": {"path": rel(V44_SPECIAL_LAYOUT), "sha256": sha256(V44_SPECIAL_LAYOUT), "component_count": 50},
        },
        "composition": {"canvas": "200x200_1bpp_white_is_one_msb", "final_plan": "deterministic_union(expression_track,functional_decoration_track)",
                        "ordering": "stable_ascending_z_index_then_expression_before_functional", "maximum_layers": 16,
                        "no_mask_synthesis": True, "runtime_binding": "forbidden_until_v44_machine_audit_and_owner_review"},
        "expression_track": {
            "driven_only_by": ["emotion", "attention", "energy", "interaction_memory"],
            "inherited_v22_performances": {"path": rel(V39_LAYOUT), "sha256": sha256(V39_LAYOUT)},
            "added_performances": {
                "delighted_presence": {"emotion": "affectionate", "base_face": [575, 576, 577, 578, 579, 2, 6, 1, 5, 3, 7, 4]},
                "bashful_presence": {"emotion": "affectionate", "base_face": [580, 581, 582, 583, 584, 2, 6, 1, 5, 3, 7, 4]},
                "thoughtful_presence": {"emotion": "focused", "base_face": [585, 586, 587, 588, 2, 6, 1, 5, 3, 7, 4]},
                "focused_presence": {"emotion": "focused", "base_face": [589, 590, 591, 592, 593, 2, 6, 1, 5, 3, 7, 4]},
            },
            "sleep_zzz_only": {"sleep_face": [539, 540, 541, 542, 14, 17, 4, 543], "zzz_components": [594, 595, 596],
                                "forbidden_components": [531, 532, 544], "forbidden_visuals": ["cloud", "moon", "crescent"]},
            "attention_demonstrations": v41_layout["expression_track"]["attention_demonstrations"],
            "forbidden": ["whole_face_card", "code_drawn_face", "functional_event_selects_emotion", "random_gaze"],
        },
        "functional_decoration_track": {
            "driven_only_by": ["functional_event"],
            "events": {
                "recording_input": {"frames": [[569], [570], [571], [570], [569]], "durations_ms": [260, 240, 520, 240, 680],
                                    "safe_zone": "right_of_face_only_no_eye_brow_mouth_nose_or_cheek_overlap"},
                "bottom_connector_charging": {"frames": [[572], [573], [574], [573], [574]], "durations_ms": [300, 260, 520, 260, 680],
                                                "safe_zone": "below_face_only_wireless_dock"},
                "upgrade_progress": {"frames": [[563], [564], [565], [564], [565]], "durations_ms": [420, 280, 520, 280, 680]},
                "error_caution": {"frames": [[566], [567], [568], [567], [568]], "durations_ms": [220, 220, 620, 220, 820]},
            },
            "forbidden": ["face_component_id", "functional_event_selects_emotion", "functional_event_mutates_brow_eye_mouth_or_cheek", "daily_face_substitution_when_source_missing"],
        },
        "menu_entry_exception": {"event": "menu_entry_notice", "frames": [[545], [546], [547]], "durations_ms": [140, 140, 180],
                                  "maximum_expression_duration_ms": 500, "after_last_cue": "withdraw_expression_and_functional_tracks_then_show_menu_ui",
                                  "forbidden": ["persistent_menu_score", "selection_loop", "expression_rig_behind_menu_ui", "functional_track_behind_menu_ui"]},
        "preview_zh": {"title": "V9 组件表情系统预览", "player_label": "播放编舞", "restart_label": "重新播放",
                       "atlas_title": "表情与状态总览", "atlas_summary": "每张图都是同一套 200x200 组件计划的真实帧；功能状态只叠加小饰件，不替换脸。",
                       "stories": preview_stories},
        "non_claims": ["no_runtime_binding", "no_firmware_flash", "no_panel_or_driver_change", "no_human_acceptance"],
    }


def normalize_components(v22: dict[str, Any], special: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for pack, source, count in (("v22_face", v22, 37), ("v44_special_source", special, 50)):
        raw_components = source.get("components")
        require(isinstance(raw_components, list) and len(raw_components) == count, f"V44 {pack} component count drifted")
        for raw in raw_components:
            component_id = raw.get("component_id")
            base = raw.get("base_position")
            offset = raw.get("offset_range")
            size = raw.get("mask_size") or ([raw.get("width"), raw.get("height")] if isinstance(raw.get("width"), int) and isinstance(raw.get("height"), int) else None)
            role = raw.get("role") or v40.SPECIAL_ROLE.get(component_id) or "charm"
            if role not in v40.ROLE_ENUM:
                role = v40.SPECIAL_ROLE.get(component_id) or "charm"
            mask = ROOT / str(raw.get("mask", ""))
            require(isinstance(component_id, int) and isinstance(raw.get("name"), str) and role in v40.ROLE_ENUM and
                    isinstance(base, list) and len(base) == 2 and isinstance(offset, dict) and
                    isinstance(offset.get("min"), list) and len(offset["min"]) == 2 and isinstance(offset.get("max"), list) and len(offset["max"]) == 2 and
                    isinstance(size, list) and len(size) == 2 and raw.get("composite_op") in {"ink", "erase"} and mask.is_file() and
                    sha256(mask) == str(raw.get("mask_sha256", "")).upper(), f"unregistered V44 {pack} component")
            result.append({"component_id": component_id, "name": raw["name"], "role": role, "base": base, "offset": offset,
                           "z": raw.get("z_index"), "op": raw["composite_op"], "pack": pack,
                           "mask_bytes": ((size[0] + 7) // 8) * size[1]})
    ids = [component["component_id"] for component in result]
    require(len(result) == 87 and len(ids) == len(set(ids)), "V44 component namespace drifted")
    return sorted(result, key=lambda component: component["component_id"])


def emotion_layers(components: dict[int, dict[str, Any]], base_face: list[int], endpoint: dict[str, list[int]],
                   brow_offset: tuple[int, int], mouth_override: int | None = None,
                   accent: list[int] | None = None) -> list[dict[str, Any]]:
    layers: list[dict[str, Any]] = []
    component_ids = [component_id for component_id in base_face
                     if mouth_override is None or components[component_id]["role"] != "mouth"]
    if mouth_override is not None:
        component_ids.append(mouth_override)
    component_ids.extend(accent or [])
    for component_id in component_ids:
        role = components[component_id]["role"]
        if component_id in {1, 5}:
            offset = tuple(endpoint["primary"])
        elif component_id in {3, 7}:
            offset = tuple(endpoint["sparkle"])
        elif role in {"left_brow", "right_brow"}:
            offset = brow_offset
        else:
            offset = (0, 0)
        layers.append(v40.make_layer(components, component_id, offset))
    return v40.sort_layers(components, layers)


def blink_layers(components: dict[int, dict[str, Any]], base_face: list[int]) -> list[dict[str, Any]]:
    """Replace the registered open-eye group with the paired source blink masks."""
    excluded_roles = {"left_eye", "right_eye", "left_highlight", "right_highlight",
                      "left_sparkle", "right_sparkle"}
    layers = [v40.make_layer(components, component_id)
              for component_id in base_face
              if components[component_id]["role"] not in excluded_roles]
    layers.extend([v40.make_layer(components, 597), v40.make_layer(components, 598)])
    return v40.sort_layers(components, layers)


def center_layers(components: dict[int, dict[str, Any]], layers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep automatic non-touch eye highlights at the registered center endpoint."""
    for layer in layers:
        if layer["component_id"] in {1, 5, 3, 7}:
            layer["offset"] = [1, 0]
    return v40.sort_layers(components, layers)


def inherited_expression_steps(components: dict[int, dict[str, Any]], inherited: dict[str, Any],
                               endpoints: dict[str, dict[str, list[int]]]) -> dict[str, dict[str, Any]]:
    performances = inherited["expression_track"]["performances"]
    specs = {
        "calm_presence": [("calm_entry", 220, "center", (0, 0), "entry", "base"), ("calm_blink_close", 110, "center", (0, 0), "lead", "base"), ("calm_blink_hold", 90, "center", (0, 0), "hold", "base"), ("calm_hold", 1800, "center", (0, 0), "hold", "base"), ("calm_settle", 360, "center", (0, 0), "accent", "base")],
        "warm_presence": [("warm_entry", 220, "center", (0, 0), "entry", "neutral"), ("warm_brow_lead", 180, "center", (0, 1), "lead", "neutral"), ("warm_smile_arrive", 260, "right", (0, 1), "response", "emotion"), ("warm_hold", 760, "right", (0, 1), "hold", "emotion"), ("warm_settle", 360, "center", (0, 0), "accent", "neutral")],
        "curious_question": [("question_entry", 180, "center", (0, 0), "entry", "neutral"), ("question_brow_lead", 180, "center", (0, -1), "lead", "neutral"), ("question_mouth_arrive", 260, "up", (0, -1), "response", "emotion"), ("question_hold", 760, "up", (0, -1), "hold", "emotion"), ("question_settle", 360, "center", (0, 0), "accent", "neutral")],
        "alert_exclamation": [("exclamation_entry", 180, "center", (0, 0), "entry", "neutral"), ("exclamation_brow_lead", 180, "center", (0, -1), "lead", "neutral"), ("exclamation_mouth_arrive", 260, "right", (0, -1), "response", "emotion"), ("exclamation_hold", 760, "right", (0, -1), "hold", "emotion"), ("exclamation_settle", 360, "center", (0, 0), "accent", "neutral")],
        "playful_presence": [("playful_entry", 220, "center", (0, 0), "entry", "neutral"), ("playful_brow_lead", 180, "center", (0, 1), "lead", "neutral"), ("playful_smile_arrive", 260, "left", (0, 1), "response", "emotion"), ("playful_hold", 760, "right", (0, 1), "hold", "emotion"), ("playful_settle", 360, "center", (0, 0), "accent", "neutral")],
    }
    result: dict[str, dict[str, Any]] = {}
    for name, rows in specs.items():
        performance = performances[name]
        if name != "calm_presence":
            rows = [(cue, duration, "center", brow, phase, mouth_state)
                    for cue, duration, _attention, brow, phase, mouth_state in rows]
        accents = performance.get("expression_owned_accent_steps", [])
        mouth = next(component_id for component_id in performance["base_face"] if components[component_id]["role"] == "mouth")
        accent_steps = [[], accents[0] if len(accents) > 0 else [], accents[1] if len(accents) > 1 else [],
                        accents[2] if len(accents) > 2 else [], []]
        steps = [
            {"cue": cue, "duration_ms": duration, "phase": phase, "scene": "daily", "emotion": performance["emotion"], "attention": attention,
             "layers": emotion_layers(components, performance["base_face"], endpoints[attention], brow_offset,
                                       15 if mouth_state == "neutral" else mouth, accent_steps[index])}
            for index, (cue, duration, attention, brow_offset, phase, mouth_state) in enumerate(rows)
        ]
        if name == "calm_presence":
            steps[1]["layers"] = blink_layers(components, performance["base_face"])
            steps[2]["layers"] = blink_layers(components, performance["base_face"])
            steps[1]["blink"] = "close"
            steps[2]["blink"] = "hold"
        result[name] = {"name": name, "steps": steps}
    return result


def added_expression_steps(components: dict[int, dict[str, Any]], layout: dict[str, Any],
                           endpoints: dict[str, dict[str, list[int]]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    specs = {
        "delighted_presence": [("delighted_entry", 220, "center", (0, 0), "entry", "neutral"), ("delighted_brow_lead", 180, "center", (0, -1), "lead", "neutral"), ("delighted_mouth_arrive", 260, "up", (0, -1), "response", "emotion"), ("delighted_hold", 760, "up", (0, -1), "hold", "emotion"), ("delighted_settle", 360, "center", (0, 0), "accent", "neutral")],
        "bashful_presence": [("bashful_entry", 220, "center", (0, 0), "entry", "neutral"), ("bashful_brow_lead", 180, "center", (0, 1), "lead", "neutral"), ("bashful_mouth_arrive", 260, "left", (0, 1), "response", "emotion"), ("bashful_hold", 760, "left", (0, 1), "hold", "emotion"), ("bashful_settle", 360, "center", (0, 0), "accent", "neutral")],
        "thoughtful_presence": [("thoughtful_entry", 220, "center", (0, 0), "entry", "neutral"), ("thoughtful_brow_lead", 180, "center", (0, -1), "lead", "neutral"), ("thoughtful_mouth_arrive", 260, "up", (0, -1), "response", "emotion"), ("thoughtful_hold", 760, "up", (0, -1), "hold", "emotion"), ("thoughtful_settle", 360, "center", (0, 0), "accent", "neutral")],
        "focused_presence": [("focused_entry", 220, "center", (0, 0), "entry", "neutral"), ("focused_brow_lead", 180, "center", (0, 1), "lead", "neutral"), ("focused_mouth_arrive", 260, "right", (0, 1), "response", "emotion"), ("focused_hold", 760, "right", (0, 1), "hold", "emotion"), ("focused_settle", 360, "center", (0, 0), "accent", "neutral")],
    }
    for name, rows in specs.items():
        rows = [(cue, duration, "center", brow, phase, mouth_state)
                for cue, duration, _attention, brow, phase, mouth_state in rows]
        performance = layout["expression_track"]["added_performances"][name]
        mouth = next(component_id for component_id in performance["base_face"] if components[component_id]["role"] == "mouth")
        result[name] = {"name": name, "steps": [
            {"cue": cue, "duration_ms": duration, "phase": phase, "scene": "daily", "emotion": performance["emotion"], "attention": attention,
             "layers": emotion_layers(components, performance["base_face"], endpoints[attention], brow_offset,
                                       15 if mouth_state == "neutral" else mouth)}
            for cue, duration, attention, brow_offset, phase, mouth_state in rows
        ]}
    return result


def sleepy_v42_steps(components: dict[int, dict[str, Any]], layout: dict[str, Any], inherited: dict[str, Any]) -> dict[str, Any]:
    calm_face = inherited["expression_track"]["performances"]["calm_presence"]["base_face"]
    sleep = layout["expression_track"]["sleep_zzz_only"]
    sets = [calm_face, sleep["sleep_face"], sleep["sleep_face"] + [594], sleep["sleep_face"] + [594, 595], sleep["sleep_face"] + [594, 595, 596]]
    rows = [("sleep_entry", 420, "daily", "calm", "entry"), ("eyes_soften", 360, "sleep", "sleepy", "lead"),
            ("zzz_arrive", 320, "sleep", "sleepy", "response"), ("zzz_rise", 420, "sleep", "sleepy", "accent"),
            ("sleep_hold", 1400, "sleep", "sleepy", "hold")]
    return {"name": "sleepy_presence", "steps": [
        {"cue": cue, "duration_ms": duration, "phase": phase, "scene": scene, "emotion": emotion, "attention": "center",
         "layers": center_layers(components, [v40.make_layer(components, component_id) for component_id in layer_set])}
        for (cue, duration, scene, emotion, phase), layer_set in zip(rows, sets)
    ]}


def functional_steps(components: dict[int, dict[str, Any]], layout: dict[str, Any]) -> dict[str, dict[str, Any]]:
    contexts = {"recording_input": ("recording", "focused"), "bottom_connector_charging": ("charging", "affectionate"),
                "upgrade_progress": ("touch", "calm"), "error_caution": ("error", "calm")}
    result: dict[str, dict[str, Any]] = {}
    for name, event in layout["functional_decoration_track"]["events"].items():
        scene, emotion = contexts[name]
        result[name] = {"name": name, "steps": [
            {"cue": f"{name}_{index}", "duration_ms": event["durations_ms"][index], "phase": ("entry", "lead", "response", "hold", "accent")[index],
             "scene": scene, "emotion": emotion, "attention": "center",
             "layers": v40.sort_layers(components, [v40.make_layer(components, component_id) for component_id in component_ids])}
            for index, component_ids in enumerate(event["frames"])
        ]}
    menu = layout["menu_entry_exception"]
    result["menu_entry_notice"] = {"name": "menu_entry_notice", "steps": [
        {"cue": cue, "duration_ms": menu["durations_ms"][index], "phase": ("entry", "lead", "hold")[index], "scene": "touch", "emotion": "curious", "attention": "center",
         "layers": v40.sort_layers(components, [v40.make_layer(components, component_id) for component_id in component_ids])}
        for index, (cue, component_ids) in enumerate(zip(("menu_grid_arrive", "menu_selection_confirm", "menu_entry_commit"), menu["frames"]))
    ]}
    return result


def add_story(components: dict[int, dict[str, Any]], stories: list[dict[str, Any]], name: str, expressions: dict[str, dict[str, Any]],
              expression_name: str, functional: dict[str, dict[str, Any]] | None = None, functional_name: str | None = None,
              withdraw: bool = False, expression_override: dict[str, Any] | None = None) -> None:
    expression = expression_override if expression_override is not None else expressions[expression_name]
    decoration = functional[functional_name] if functional and functional_name else None
    require(decoration is None or len(decoration["steps"]) == len(expression["steps"]), f"V42 story timing mismatch: {name}")
    steps: list[dict[str, Any]] = []
    for index, expression_step in enumerate(expression["steps"]):
        functional_step = decoration["steps"][index] if decoration else None
        final = v40.sort_layers(components, expression_step["layers"] + (functional_step["layers"] if functional_step else []))
        fixed_nose = [layer for layer in final if layer["component_id"] == 4]
        require(len(final) <= 16 and len(fixed_nose) == 1 and fixed_nose[0]["offset"] == [0, 0],
                f"V42 final plan must retain the fixed nose: {name}")
        steps.append({"cue": functional_step["cue"] if functional_step else expression_step["cue"],
                      "duration_ms": functional_step["duration_ms"] if functional_step else expression_step["duration_ms"],
                      "phase": functional_step.get("phase", expression_step.get("phase", "hold")) if functional_step else expression_step.get("phase", "hold"),
                      "state_scene": "touch" if withdraw else expression_step["scene"], "expression_track": expression_name,
                      "expression_step": index, "functional_decoration_track": functional_name, "functional_step": index if functional_step else None,
                      "expression_layers": expression_step["layers"], "functional_layers": functional_step["layers"] if functional_step else [], "layers": final})
    stories.append({"name": name, "expression_track": expression_name, "functional_decoration_track": functional_name,
                    "withdraw_all_tracks_after_last_cue": withdraw, "steps": steps})


def build_stories(components: dict[int, dict[str, Any]], expressions: dict[str, dict[str, Any]], functional: dict[str, dict[str, Any]],
                  gaze: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    stories: list[dict[str, Any]] = []
    for name in ("calm_presence", "warm_presence", "curious_question", "alert_exclamation", "playful_presence", "sleepy_presence",
                 "delighted_presence", "bashful_presence", "thoughtful_presence", "focused_presence"):
        add_story(components, stories, name, expressions, name)
    add_story(components, stories, "recording_with_calm", expressions, "calm_presence", functional, "recording_input")
    add_story(components, stories, "recording_with_warm", expressions, "warm_presence", functional, "recording_input")
    add_story(components, stories, "charging_with_calm", expressions, "calm_presence", functional, "bottom_connector_charging")
    add_story(components, stories, "upgrade_with_playful", expressions, "playful_presence", functional, "upgrade_progress")
    add_story(components, stories, "error_with_calm", expressions, "calm_presence", functional, "error_caution")
    add_story(components, stories, "menu_entry_notice", expressions, "calm_presence", functional, "menu_entry_notice", True,
              {"name": "calm_presence", "steps": expressions["calm_presence"]["steps"][:3]})
    gaze_scores = v41.gaze_stories(components, gaze)
    for story in gaze_scores:
        source_steps = gaze[story["name"]]["steps"]
        for index, step in enumerate(story["steps"]):
            step["phase"] = source_steps[index]["phase"]
    stories.extend(gaze_scores)
    require(len(stories) == 21 and sum(len(story["steps"]) for story in stories) == 93, "V44 story coverage drifted")
    return stories


def build_artifacts() -> dict[Path, str]:
    v41_layout = load(V41_LAYOUT)
    inherited = load(V39_LAYOUT)
    v22 = load(V22_LAYOUT)
    special = load(V44_SPECIAL_LAYOUT)
    layout = build_layout(v41_layout, special)
    v40.ATTENTION_ENUM.update({"up": "COMP_EXPRESSION_RIG_ATTENTION_UP", "down": "COMP_EXPRESSION_RIG_ATTENTION_DOWN"})
    components = normalize_components(v22, special)
    by_id = {component["component_id"]: component for component in components}
    endpoints = v41_layout["expression_track"]["attention_demonstrations"]["endpoint_offsets"]
    expressions = inherited_expression_steps(by_id, inherited, endpoints)
    expressions["sleepy_presence"] = sleepy_v42_steps(by_id, layout, inherited)
    expressions.update(added_expression_steps(by_id, layout, endpoints))
    gaze = v41.attention_tracks(by_id, inherited, v41_layout)
    expressions.update(gaze)
    functional = functional_steps(by_id, layout)
    stories = build_stories(by_id, expressions, functional, gaze)
    require(len(expressions) == 15 and len(functional) == 5 and max(component["mask_bytes"] for component in components) > 0,
            "V44 profile coverage drifted")
    for story in stories:
        if story["functional_decoration_track"] == "recording_input":
            require(all(all(layer["component_id"] >= 569 for layer in step["functional_layers"]) for step in story["steps"]),
                    "V44 recording must not reuse unclear V40 ornament components")
        if story["functional_decoration_track"] == "bottom_connector_charging":
            require(all(all(layer["component_id"] in {572, 573, 574} for layer in step["functional_layers"]) for step in story["steps"]),
                    "V44 charging must use the new wireless-dock components")
        if story["name"] == "sleepy_presence":
            require(all(not any(layer["component_id"] in {531, 532, 544} for layer in step["layers"]) for step in story["steps"]),
                    "V44 sleep must be ZZZ-only without cloud or moon")
    max_mask = max(component["mask_bytes"] for component in components)
    trace = {
        "schema": "companion.v44_expression_extension_wb55_target_profile_plan.v1", "status": "PASS_CANDIDATE_PROFILE_GENERATED_RUNTIME_INACTIVE",
        "authority": layout["authority"], "locked_v9_source_sha256": LOCKED, "track_layout": rel(LAYOUT), "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden_until_v44_machine_audit_and_owner_review", "component_sources": {"v22_face": 37, "v44_special_source": 50},
        "max_component_mask_bytes": max_mask, "two_track_contract": {"expression_driven_only_by": layout["expression_track"]["driven_only_by"],
            "functional_driven_only_by": ["functional_event"], "final_plan": "deterministic_union(expression_track,functional_decoration_track)",
            "owner_visible_overview_excludes": [f"daily_attention_{direction}" for direction in GAZE_ORDER]},
        "expression_tracks": list(expressions.values()), "functional_decoration_tracks": [functional[name] for name in ("recording_input", "bottom_connector_charging", "upgrade_progress", "error_caution")],
        "directional_gaze": {"states": list(GAZE_ORDER), "endpoint_offsets": layout["expression_track"]["attention_demonstrations"]["endpoint_offsets"],
                              "component_ids": layout["expression_track"]["attention_demonstrations"]["component_ids"], "fixed_nose": {"component_id": 4, "offset": [0, 0]},
                              "selection": "deterministic; no random gaze selection"},
        "menu_entry_track": functional["menu_entry_notice"], "scores": stories, "preview_zh": layout["preview_zh"],
        "menu_entry_policy": {"state_scene": "touch", "maximum_expression_duration_ms": 500,
                              "after_last_cue": "withdraw_expression_and_functional_tracks_then_show_menu_ui", "persistent_menu_score": "forbidden", "menu_ui_owns_screen_after_last_cue": True},
        "non_claims": ["no_whole_face_card", "no_code_drawn_face", "no_runtime_binding", "no_panel_or_driver_change"],
    }
    header = (v40.render_header(len(components), len(expressions), 4, len(stories), max_mask)
              .replace("tools/generate_companion_v40_two_track_target_profile.py", "tools/generate_companion_v44_blink_stable_center_target_profile.py")
              .replace("V40", "V44").replace("v40", "v44"))
    source = (v40.render_source(components, expressions, functional, stories)
              .replace("Generated from the versioned V39 two-track layout", "Generated from the versioned V44 expression-extension layout")
              .replace("V39", "V44").replace("v39", "v44")
              .replace("expression_rig_v44_two_track_candidate_profile.h", "expression_rig_v44_blink_stable_center_candidate_profile.h"))
    return {LAYOUT: json.dumps(layout, indent=2, ensure_ascii=False) + "\n", HEADER: header, SOURCE: source,
            TRACE: json.dumps(trace, indent=2, ensure_ascii=False) + "\n"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    artifacts = build_artifacts()
    drifted = [path for path, content in artifacts.items() if args.check and (not path.is_file() or path.read_text(encoding="utf-8") != content)]
    if drifted:
        for path in drifted:
            print(f"ERROR: generated artifact drifted: {rel(path)}")
        return 1
    if not args.check:
        for path, content in artifacts.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    print("PASS: generated inactive V44 profile with 87 source components, stable-center idle, synchronized blink, 21 stories, and 93 preview frames.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
