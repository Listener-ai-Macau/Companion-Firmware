#!/usr/bin/env python3
"""Verify gradual external-pack expression timelines and preview wiring."""

from __future__ import annotations

import json
import pathlib
import sys

from PIL import Image


ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "app/companion_pendant/epaper/assets/emote_matrix_white_200x200.json"
FIXTURES = ROOT / "docs/validation/epaper"
FEATURE_DIRTY = [8, 18, 184, 166]


def raster(path: pathlib.Path) -> bytes:
    with Image.open(path) as image:
        if image.size != (200, 200):
            raise ValueError(f"invalid 200x200 P4 asset: {path.name}")
        data = image.convert("1").tobytes()
    if len(data) != 5000:
        raise ValueError(f"invalid 200x200 P4 asset: {path.name}")
    return data


def main() -> int:
    errors: list[str] = []
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    clips = {clip["name"]: clip for clip in manifest["clips"]}
    idle = clips.get("idle", {})
    listening = clips.get("listening", {})
    thinking = clips.get("thinking", {})
    speaking = clips.get("speaking", {})
    happy = clips.get("happy", {})
    sleepy = clips.get("sleepy", {})
    recording = clips.get("recording", {})
    frames = idle.get("frames", [])
    if manifest.get("revision", 0) < 22:
        errors.append("resource revision must use the directional electronic-pet rig")
    idle_sources = (
        "expression_idle_1_54in.pbm",
        "expression_idle_glance_left_1_54in.pbm",
        "expression_idle_1_54in.pbm",
    )
    if len(frames) != 3 or idle.get("loop_start") != 1 or idle.get("loop_end") != 2:
        errors.append("idle must use one slow glance and settle without repeating")
    if len(frames) == len(idle_sources):
        for index, (frame, expected) in enumerate(zip(frames, idle_sources)):
            if pathlib.Path(frame.get("source", "")).name != expected:
                errors.append(f"idle frame {index} must use {expected}")
            if frame.get("duration_ms", 0) < 1000:
                errors.append(f"idle frame {index} is faster than the e-paper budget")
            if frame.get("dirty") != FEATURE_DIRTY:
                errors.append(f"idle frame {index} lost the feature dirty rectangle")

    expected_sources = (
        "expression_idle_1_54in.pbm",
        "expression_idle_blink_half_1_54in.pbm",
        "expression_idle_blink_closed_1_54in.pbm",
    )

    try:
        open_frame = raster(FIXTURES / expected_sources[0])
        half_frame = raster(FIXTURES / expected_sources[1])
        closed_frame = raster(FIXTURES / expected_sources[2])
        if open_frame == half_frame or half_frame == closed_frame or open_frame == closed_frame:
            errors.append("blink frames are not visually distinct")
    except (OSError, ValueError) as exc:
        errors.append(str(exc))

    sleepy_frames = sleepy.get("frames", [])
    sleepy_sources = (
        "expression_sleepy_1_54in.pbm",
        "expression_sleepy_drift_1_54in.pbm",
        "expression_sleepy_yawn_1_54in.pbm",
        "expression_sleepy_drift_1_54in.pbm",
        "expression_sleepy_1_54in.pbm",
    )
    if (len(sleepy_frames) != 5 or sleepy.get("loop_start") != 1 or
            sleepy.get("loop_end") != 4):
        errors.append("sleepy must preserve intro + three-frame loop + tail")
    if len(sleepy_frames) == len(sleepy_sources):
        for index, (frame, expected) in enumerate(zip(sleepy_frames, sleepy_sources)):
            if pathlib.Path(frame.get("source", "")).name != expected:
                errors.append(f"sleepy frame {index} must use {expected}")
            if frame.get("duration_ms", 0) < 850:
                errors.append(f"sleepy frame {index} is faster than the e-paper budget")
            if frame.get("dirty") != FEATURE_DIRTY:
                errors.append(f"sleepy frame {index} lost the feature dirty rectangle")
    try:
        sleepy_base = raster(FIXTURES / sleepy_sources[0])
        sleepy_drift = raster(FIXTURES / sleepy_sources[1])
        sleepy_yawn = raster(FIXTURES / sleepy_sources[2])
        if (sleepy_base == sleepy_drift or sleepy_drift == sleepy_yawn or
                sleepy_base == sleepy_yawn):
            errors.append("sleepy frames are not visually distinct")
    except (OSError, ValueError) as exc:
        errors.append(str(exc))

    happy_frames = happy.get("frames", [])
    happy_sources = (
        "expression_happy_attention_1_54in.pbm",
        "expression_happy_bright_1_54in.pbm",
        "expression_happy_1_54in.pbm",
    )
    if (len(happy_frames) != 3 or happy.get("loop_start") != 1 or
            happy.get("loop_end") != 2):
        errors.append("happy must acknowledge, brighten, and settle in three frames")
    if len(happy_frames) == len(happy_sources):
        for index, (frame, expected) in enumerate(zip(happy_frames, happy_sources)):
            if pathlib.Path(frame.get("source", "")).name != expected:
                errors.append(f"happy frame {index} must use {expected}")
            if frame.get("duration_ms", 0) < 900:
                errors.append(f"happy frame {index} is faster than the e-paper budget")
            if frame.get("dirty") != FEATURE_DIRTY:
                errors.append(f"happy frame {index} lost the feature dirty rectangle")
    try:
        happy_base = raster(FIXTURES / happy_sources[2])
        happy_attention = raster(FIXTURES / happy_sources[0])
        happy_bright = raster(FIXTURES / happy_sources[1])
        if (happy_base == happy_attention or happy_attention == happy_bright or
                happy_base == happy_bright):
            errors.append("happy frames are not visually distinct")
    except (OSError, ValueError) as exc:
        errors.append(str(exc))

    attention_directions = (
        "center", "up_left", "up", "up_right", "left", "right",
        "down_left", "down", "down_right",
    )
    attention_rasters: list[bytes] = []
    for direction in attention_directions:
        clip = clips.get(f"attention.{direction}", {})
        attention_frames = clip.get("frames", [])
        if (len(attention_frames) != 3 or clip.get("loop_start") != 1 or
                clip.get("loop_end") != 2):
            errors.append(f"attention.{direction} must use notice + respond + settle")
            continue
        for frame in attention_frames:
            if frame.get("duration_ms", 0) < 800 or frame.get("dirty") != FEATURE_DIRTY:
                errors.append(f"attention.{direction} violates the e-paper timing or dirty contract")
        try:
            attention_rasters.append(raster(FIXTURES / pathlib.Path(
                attention_frames[0].get("source", "")).name))
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
    if len(attention_rasters) == len(attention_directions) and len(set(attention_rasters)) != len(attention_rasters):
        errors.append("directional attention notice frames must remain visually distinct")

    recording_frames = recording.get("frames", [])
    recording_sources = (
        "expression_recording_1_54in.pbm",
        "expression_recording_soft_1_54in.pbm",
        "expression_recording_pulse_1_54in.pbm",
        "expression_recording_soft_1_54in.pbm",
        "expression_recording_1_54in.pbm",
    )
    if (len(recording_frames) != 5 or recording.get("loop_start") != 1 or
            recording.get("loop_end") != 4):
        errors.append("recording must preserve intro + three-frame loop + tail")
    if len(recording_frames) == len(recording_sources):
        for index, (frame, expected) in enumerate(zip(recording_frames, recording_sources)):
            if pathlib.Path(frame.get("source", "")).name != expected:
                errors.append(f"recording frame {index} must use {expected}")
            if frame.get("duration_ms", 0) < 750:
                errors.append(f"recording frame {index} is faster than the e-paper budget")
            if frame.get("dirty") != FEATURE_DIRTY:
                errors.append(f"recording frame {index} lost the feature dirty rectangle")
    try:
        recording_base = raster(FIXTURES / recording_sources[0])
        recording_soft = raster(FIXTURES / recording_sources[1])
        recording_pulse = raster(FIXTURES / recording_sources[2])
        if (recording_base == recording_soft or recording_soft == recording_pulse or
                recording_base == recording_pulse):
            errors.append("recording frames are not visually distinct")
    except (OSError, ValueError) as exc:
        errors.append(str(exc))

    thinking_frames = thinking.get("frames", [])
    thinking_sources = (
        "expression_thinking_1_54in.pbm",
        "expression_thinking_inward_1_54in.pbm",
        "expression_thinking_outward_1_54in.pbm",
        "expression_thinking_inward_1_54in.pbm",
        "expression_thinking_1_54in.pbm",
    )
    if (len(thinking_frames) != 5 or thinking.get("loop_start") != 1 or
            thinking.get("loop_end") != 4):
        errors.append("thinking must preserve intro + three-frame loop + tail")
    if len(thinking_frames) == len(thinking_sources):
        for index, (frame, expected) in enumerate(zip(thinking_frames, thinking_sources)):
            if pathlib.Path(frame.get("source", "")).name != expected:
                errors.append(f"thinking frame {index} must use {expected}")
            if frame.get("duration_ms", 0) < 750:
                errors.append(f"thinking frame {index} is faster than the e-paper budget")
            if frame.get("dirty") != FEATURE_DIRTY:
                errors.append(f"thinking frame {index} lost the feature dirty rectangle")
    try:
        thinking_base = raster(FIXTURES / thinking_sources[0])
        thinking_inward = raster(FIXTURES / thinking_sources[1])
        thinking_outward = raster(FIXTURES / thinking_sources[2])
        if (thinking_base == thinking_inward or thinking_inward == thinking_outward or
                thinking_base == thinking_outward):
            errors.append("thinking frames are not visually distinct")
    except (OSError, ValueError) as exc:
        errors.append(str(exc))

    speaking_frames = speaking.get("frames", [])
    speaking_sources = (
        "expression_speaking_1_54in.pbm",
        "expression_speaking_soft_1_54in.pbm",
        "expression_speaking_open_1_54in.pbm",
        "expression_speaking_soft_1_54in.pbm",
        "expression_speaking_1_54in.pbm",
    )
    if (len(speaking_frames) != 5 or speaking.get("loop_start") != 1 or
            speaking.get("loop_end") != 4):
        errors.append("speaking must preserve intro + three-frame loop + tail")
    if len(speaking_frames) == len(speaking_sources):
        for index, (frame, expected) in enumerate(zip(speaking_frames, speaking_sources)):
            if pathlib.Path(frame.get("source", "")).name != expected:
                errors.append(f"speaking frame {index} must use {expected}")
            if frame.get("duration_ms", 0) < 650:
                errors.append(f"speaking frame {index} is faster than the e-paper budget")
            if frame.get("dirty") != FEATURE_DIRTY:
                errors.append(f"speaking frame {index} lost the feature dirty rectangle")
    try:
        speaking_base = raster(FIXTURES / speaking_sources[0])
        speaking_soft = raster(FIXTURES / speaking_sources[1])
        speaking_open = raster(FIXTURES / speaking_sources[2])
        if (speaking_base == speaking_soft or speaking_soft == speaking_open or
                speaking_base == speaking_open):
            errors.append("speaking frames are not visually distinct")
    except (OSError, ValueError) as exc:
        errors.append(str(exc))

    listening_frames = listening.get("frames", [])
    listening_sources = (
        "expression_listening_1_54in.pbm",
        "expression_listening_focus_1_54in.pbm",
        "expression_listening_wave_1_54in.pbm",
        "expression_listening_focus_1_54in.pbm",
        "expression_listening_1_54in.pbm",
    )
    if (len(listening_frames) != 5 or listening.get("loop_start") != 1 or
            listening.get("loop_end") != 4):
        errors.append("listening must preserve intro + three-frame loop + tail")
    if len(listening_frames) == len(listening_sources):
        for index, (frame, expected) in enumerate(zip(listening_frames, listening_sources)):
            if pathlib.Path(frame.get("source", "")).name != expected:
                errors.append(f"listening frame {index} must use {expected}")
            if frame.get("duration_ms", 0) < 650:
                errors.append(f"listening frame {index} is faster than the e-paper budget")
            if frame.get("dirty") != FEATURE_DIRTY:
                errors.append(f"listening frame {index} lost the feature dirty rectangle")
    try:
        listening_base = raster(FIXTURES / listening_sources[0])
        listening_focus = raster(FIXTURES / listening_sources[1])
        listening_wave = raster(FIXTURES / listening_sources[2])
        if (listening_base == listening_focus or listening_focus == listening_wave or
                listening_base == listening_wave):
            errors.append("listening frames are not visually distinct")
    except (OSError, ValueError) as exc:
        errors.append(str(exc))

    player = (ROOT / "app/companion_pendant/epaper/emote_player.c").read_text(encoding="utf-8")
    app = (ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c").read_text(encoding="utf-8")
    main_source = (ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c").read_text(encoding="utf-8")
    required = {
        "player": (player, "comp_emote_player_stop", "COMP_EMOTE_PLAYER_PHASE_STOPPED"),
        "app": (app, "Companion_Screen_ExpressionPreview", "Companion_Display_EmitEmoteFrame(false)"),
        "main": (main_source, "COMP_TOUCH_GESTURE_HOLD", "daily_hold_tease"),
    }
    for label, values in required.items():
        content, *tokens = values
        for token in tokens:
            if token not in content:
                errors.append(f"{label} missing {token}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: revision 22 directional electronic-pet rig, event timelines, and portable preview wiring verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
