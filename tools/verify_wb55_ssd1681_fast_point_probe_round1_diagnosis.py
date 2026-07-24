#!/usr/bin/env python3
"""Diagnose round-1 serial motion versus the no-visible-change observation."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from verify_wb55_ssd1681_fast_point_probe_log import FRAME_RE, draw, expected_frames


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / ".cache/validation/wb55-fast-point-probe-execute-20260721-r1"
LOG = RUN / "candidate-capture/nucleo-serial-raw.log"
STAGE = RUN / "stage-run.json"
CONTROLLER = RUN / "controller-state.json"
OPERATOR = RUN / "visual-operator.json"
HEX = RUN / "candidate-image/Companion_Nucleo_WB55RG_Ssd1681FastPointProbe.hex"
ELF = RUN / "candidate-image/Companion_Nucleo_WB55RG_Ssd1681FastPointProbe.elf"
PHASE_A = ROOT / "docs/validation/companion-ssd1681-ram-ping-pong-fingerprint-machine-20260721.json"
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
OUT = ROOT / "docs/validation/companion-ssd1681-fast-point-probe-round1-diagnosis-20260721.json"

EXPECTED_HASHES = {
    STAGE: "AAAF6B4C51C89E12038D3938DAB9CD348BBB3BAAE50DD8635A46769DE061558C",
    CONTROLLER: "FBD5EE6781F8EEB6A142BC7553F7A8567E0D286472732B3E5CC42D266900BD9A",
    OPERATOR: "5203C644434173CE4C97489A20A8D85DEA1DD6BABF2B0D169935315F901E7E73",
    HEX: "210B9851889457F951E20FC96DC509CA4DCB8B779E40031F7DC47C136C4CB222",
    ELF: "38B1DC3942624F3DF5FF28CEB5A47E21F12584B6160A315B77F5EE88465E24B1",
    PHASE_A: "5D3DE03A707BA7FB6AD17CDE1361448DFF8087B9E4A7205A18B5CD7D4FB915FE",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def bit_transitions(previous: bytes, current: bytes) -> tuple[int, int]:
    white_to_black = 0
    black_to_white = 0
    for old, new in zip(previous, current):
        white_to_black += (old & ~new & 0xFF).bit_count()
        black_to_white += (~old & new & 0xFF).bit_count()
    return white_to_black, black_to_white


def main() -> int:
    errors: list[str] = []
    for path, expected in EXPECTED_HASHES.items():
        if not path.is_file() or sha(path) != expected:
            errors.append(f"locked input missing or hash mismatch: {path}")

    text = LOG.read_text(encoding="utf-8", errors="ignore")
    stage = json.loads(STAGE.read_text(encoding="utf-8"))
    controller = json.loads(CONTROLLER.read_text(encoding="utf-8"))
    operator_note = OPERATOR.read_text(encoding="utf-8").strip()
    phase_a = json.loads(PHASE_A.read_text(encoding="utf-8"))
    driver = DRIVER.read_text(encoding="utf-8")
    frames = [tuple(int(value) for value in match.groups()) for match in FRAME_RE.finditer(text)]
    expected = expected_frames()

    if stage.get("status") != "PASS_MACHINE_SSD1681_FAST_POINT_PROBE_RESTORED":
        errors.append("round-1 stage did not pass machine plus restore")
    if controller.get("status") != "PASS_MACHINE_SSD1681_FAST_POINT_PROBE" or len(frames) != 120:
        errors.append("round-1 controller trace is not exactly 120 passing frames")
    if "没看出来有移动" not in operator_note:
        errors.append("canonical no-visible-motion observation drifted")
    mapping = phase_a.get("fingerprint", {}).get("unique_mapping")
    if mapping != "activation_swapped_banks_selector0_base_selector1_current":
        errors.append("RAM phase mapping is not the proved unique mapping")

    polarity_ok = all(token in driver for token in (
        "memset(s_frame, 0xFF, sizeof(s_frame));",
        "(uint8_t)~(0x80u >> (x & 7u))",
        "memset(s_frame, 0x00, sizeof(s_frame));",
    ))
    if not polarity_ok:
        errors.append("white=0xFF / black=cleared-bit polarity evidence is absent")
    address_ok = all(token in driver for token in (
        "static const uint8_t data_entry[] = {0x01u};",
        "(SSD1681_HEIGHT - 1u) - window->y_start",
        "(SSD1681_HEIGHT - 1u) - window->y_end",
    ))
    if not address_ok:
        errors.append("data-entry/window address evidence is absent")

    transitions = []
    previous = bytes([0xFF]) * 5000
    for index, oracle in enumerate(expected):
        current = draw(oracle["x"])
        white_to_black, black_to_white = bit_transitions(previous, current)
        actual = frames[index] if index < len(frames) else None
        if actual is not None:
            dirty_bytes = actual[8]
            stage_bytes = actual[10]
            sync_bytes = actual[14]
            if dirty_bytes != oracle["changed"] or stage_bytes != oracle["oracle"] or sync_bytes != oracle["oracle"]:
                errors.append(f"frame {index + 1} dirty/stage/sync differs from framebuffer oracle")
        transitions.append({
            "frame": index + 1,
            "x": oracle["x"],
            "dirty_bytes": oracle["changed"],
            "window_bytes": oracle["oracle"],
            "white_to_black_pixels": white_to_black,
            "black_to_white_pixels": black_to_white,
        })
        previous = current
    if transitions[0]["white_to_black_pixels"] != 144 or transitions[0]["black_to_white_pixels"] != 0:
        errors.append("frame-1 transition oracle differs")
    if any(item["white_to_black_pixels"] != 96 or item["black_to_white_pixels"] != 96
           for item in transitions[1:]):
        errors.append("motion transition oracle differs from 96 white->black and 96 black->white")

    sequence = {
        "countdown_3": text.find("fast_probe countdown=3"),
        "start_signal": text.find("fast_probe start_signal=1"),
        "seed": text.find("fast_probe seed banks=0x24,0x26 bytes_each=5000 activation=0 ok=1"),
        "frame_1": text.find("fast_probe frame=1 "),
    }
    if not (sequence["countdown_3"] < sequence["start_signal"] < sequence["seed"] < sequence["frame_1"]):
        errors.append("review/start/seed/frame sequencing differs")

    result = {
        "schema_id": "companion.wb55.ssd1681_fast_point_probe_round1_diagnosis.v1",
        "status": "PASS_DIAGNOSIS_PREVIOUS_PLANE_NOT_PHYSICALLY_SYNCHRONIZED" if not errors else "NO_GO_DIAGNOSIS",
        "errors": errors,
        "locked_round1": {str(path.relative_to(ROOT)): expected for path, expected in EXPECTED_HASHES.items()},
        "checks": {
            "framebuffer_polarity": "0xFF=white; cleared bit=black",
            "cpu_window": {"x_byte_range": [6, 11], "y_range": [94, 105]},
            "controller_window_y": {"start": 105, "end": 94, "data_entry": "0x01 (X increment, Y decrement)"},
            "frame_1": transitions[0],
            "frames_2_to_120": {"dirty_bytes": 36, "window_bytes": 36, "white_to_black_pixels_each": 96, "black_to_white_pixels_each": 96},
            "ram_phase": mapping,
            "post_activation_sync": "0x24 current-only, no second activation",
            "review_sequence_offsets": sequence,
        },
        "root_cause_boundary": {
            "proved": "The firmware transmitted valid changing bytes and completed 120 bounded activations, but the controller RAM seed was not activated before observation and therefore did not synchronize the electrophoretic pixels to the assumed all-white previous framebuffer.",
            "inference": "The first local frame only drives the 12x12 white-to-black dot against an assumed-white previous plane; it cannot establish a clean, known local physical baseline when the restored product image is already on glass. This explains how transport can pass while a small motion is not visibly distinguishable.",
            "not_proved": "No electrical panel readback proves pixel color; the no-visible-change observation remains the physical authority.",
        },
        "next_single_variable": {
            "name": "first_frame_previous_plane_seed",
            "from": "all-white previous plane",
            "to": "local inverse of frame 1 across the trajectory corridor",
            "unchanged": "120 frames, 500 ms pacing, one FF/20/BUSY per frame, post-activation 0x24 sync, zero motion 0x26, no full refresh, no LUT",
            "reason": "An inverse old-plane seed makes every corridor pixel transition exactly once to the first desired local image within frame 1, without an extra activation or whole-screen refresh.",
        },
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
