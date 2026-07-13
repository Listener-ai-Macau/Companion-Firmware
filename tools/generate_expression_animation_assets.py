#!/usr/bin/env python3
"""Generate deterministic 200x200 monochrome cat expression frames."""

from __future__ import annotations

import argparse
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
EPAPER_APP = ROOT / "app" / "companion_pendant" / "epaper"
sys.path.insert(0, str(EPAPER_APP))

from card_renderer import Framebuffer, draw_expression_face  # noqa: E402


WIDTH = 200
HEIGHT = 200
FACE_MARGIN = 8
FACE_SIZE = 184
ATTENTION_DIRECTIONS = (
    "up_left", "up", "up_right",
    "left", "right",
    "down_left", "down", "down_right",
)


def render_features(expression: str, phase: str = "base") -> bytes:
    framebuffer = Framebuffer(WIDTH, HEIGHT)
    framebuffer.fill_rect(0, 0, WIDTH, HEIGHT, False)
    draw_expression_face(
        framebuffer,
        expression,
        FACE_MARGIN,
        FACE_MARGIN,
        FACE_SIZE,
        phase,
    )
    return framebuffer.to_pbm(
        f"companion enclosure-aware face features {expression} {phase} white background"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-dir", type=pathlib.Path, required=True)
    args = parser.parse_args()
    args.fixture_dir.mkdir(parents=True, exist_ok=True)

    outputs = {
        "expression_idle_glance_left_1_54in.pbm": ("idle", "glance_left"),
        "expression_idle_blink_half_1_54in.pbm": ("idle", "half"),
        "expression_idle_blink_closed_1_54in.pbm": ("idle", "closed"),
        "expression_listening_focus_1_54in.pbm": ("listening", "focus"),
        "expression_listening_wave_1_54in.pbm": ("listening", "wave"),
        "expression_thinking_inward_1_54in.pbm": ("thinking", "inward"),
        "expression_thinking_outward_1_54in.pbm": ("thinking", "outward"),
        "expression_speaking_soft_1_54in.pbm": ("speaking", "soft"),
        "expression_speaking_open_1_54in.pbm": ("speaking", "open"),
        "expression_happy_soft_1_54in.pbm": ("happy", "soft"),
        "expression_happy_attention_1_54in.pbm": ("happy", "attention"),
        "expression_happy_bright_1_54in.pbm": ("happy", "bright"),
        "expression_sleepy_drift_1_54in.pbm": ("sleepy", "drift"),
        "expression_sleepy_yawn_1_54in.pbm": ("sleepy", "yawn"),
        "expression_recording_soft_1_54in.pbm": ("recording", "soft"),
        "expression_recording_pulse_1_54in.pbm": ("recording", "pulse"),
    }
    for direction in ATTENTION_DIRECTIONS:
        outputs[f"expression_idle_look_{direction}_1_54in.pbm"] = (
            "idle", f"look_{direction}"
        )
        outputs[f"expression_happy_attention_{direction}_1_54in.pbm"] = (
            "happy", f"attention_{direction}"
        )
    for name, (expression, phase) in outputs.items():
        output = args.fixture_dir / name
        output.write_bytes(render_features(expression, phase))
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
