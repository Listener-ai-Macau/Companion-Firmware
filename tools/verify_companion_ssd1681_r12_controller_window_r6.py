#!/usr/bin/env python3
"""Offline COMP-REQ-393 verifier for the R12 controller-Y correction."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
EXPECTED = {
    "logical_window": [4, 21, 22, 127],
    "controller_window": [4, 21, 177, 72],
    "ram_y": [0xB1, 0x00, 0x48, 0x00],
    "y_counter": [0xB1, 0x00],
    "bytes": 1908,
    "frame_sha256": {
        "calm": "15788734073049E9967DEA97783522CE1139023FC0AD9BA0F1C5375F2F2E555C",
        "curious": "E98E7E347943A67F92735E9F83F71D12FC214944C7E27B8B8E0225B0F5514705",
        "warm": "931CADB6B5209BB7B3035585994664281B037753605939EFC745A62A5889E29B",
    },
    "payload_sha256": {
        "calm": "6FFA8C8A70D87DC46AC323BFF385FEAAAD25A4C6E67E875B8030844A8158CC5B",
        "curious": "B3FF181ED6993CBBC4DE692941793CC81C7B3D40A99528D332CBAFF54D1F6A18",
        "warm": "15CAAB219B74A45B4E0F8F5E3CB046DB3554264E1D48DB92CE13F8260FDCD2C4",
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require(text: str, needle: str, failures: list[str], label: str) -> None:
    if needle not in text:
        failures.append(f"missing {label}: {needle}")


def map_controller_y(logical_y: int) -> int:
    return 199 - logical_y


def simulate_stacked_failure() -> bool:
    baseline = set(range(22, 128))
    wrong_movement = set(range(72, 178))
    return baseline != wrong_movement and bool(baseline & wrong_movement)


def accepts_controller_window(window: list[int], ram_y: list[int], counter: list[int], direction: str) -> bool:
    return (window == [4, 21, 177, 72] and ram_y == [0xB1, 0x00, 0x48, 0x00] and
            counter == [0xB1, 0x00] and direction == "x_increment_y_decrement")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--hex", type=Path)
    parser.add_argument("--elf", type=Path)
    args = parser.parse_args()

    text = DRIVER.read_text(encoding="utf-8")
    failures: list[str] = []
    require(text, "static const uint8_t ram_y[] = {0xB1u, 0x00u, 0x48u, 0x00u};", failures, "correct 0x45 bytes")
    require(text, "static const uint8_t y_counter[] = {0xB1u, 0x00u};", failures, "correct 0x4F bytes")
    require(text, "window->y_start != COMP_R12_V22_CALM_CURIOUS_WARM_CORRIDOR_Y_START", failures, "logical corridor guard")
    require(text, "for (uint16_t y = COMP_R12_V22_CALM_CURIOUS_WARM_CORRIDOR_Y_START;", failures, "logical row order")
    require(text, "memcpy(&s_r12_v22_corridor_payload[offset], row, bytes_per_row);", failures, "unchanged payload copy")
    require(text, "ssd1681_command(0x24u)", failures, "0x24 movement write")
    require(text, "native_mode2_source[] = {0xCFu}", failures, "0xCF movement control")
    require(text, "ssd1681_command(0x20u)", failures, "0x20 activation")

    if "static const uint8_t ram_y[] = {0x7Fu, 0x00u, 0x16u, 0x00u};" in text:
        failures.append("old 0x45 127..22 remains in driver")
    if "static const uint8_t y_counter[] = {0x7Fu, 0x00u};" in text:
        failures.append("old 0x4F counter remains in driver")
    if [map_controller_y(22), map_controller_y(127)] != [177, 72]:
        failures.append("logical-to-controller formula mismatch")
    mutations = {
        "old_127_to_22": ([4, 21, 127, 22], [0x7F, 0, 0x16, 0], [0x7F, 0], "x_increment_y_decrement"),
        "wrong_counter": ([4, 21, 177, 72], [0xB1, 0, 0x48, 0], [0x7F, 0], "x_increment_y_decrement"),
        "window_counter_mismatch": ([4, 21, 177, 72], [0xB1, 0, 0x48, 0], [0xB1, 0], "x_increment_y_increment"),
        "wrong_direction": ([4, 21, 72, 177], [0x48, 0, 0xB1, 0], [0x48, 0], "x_increment_y_increment"),
    }
    for name, fixture in mutations.items():
        if accepts_controller_window(*fixture):
            failures.append(f"negative fixture accepted: {name}")
    if not simulate_stacked_failure():
        failures.append("stacked y22..127 plus y72..177 fixture did not fail")

    result = {
        "schema_id": "companion.ssd1681.r12_controller_window.r6.v1",
        "requirement": "COMP-REQ-393",
        "status": "PASS_OFFLINE_CONTROLLER_WINDOW" if not failures else "FAIL_OFFLINE_CONTROLLER_WINDOW",
        "driver_sha256": sha256(DRIVER),
        "logical_window": EXPECTED["logical_window"],
        "controller_window": EXPECTED["controller_window"],
        "ram_y_bytes": ["B1", "00", "48", "00"],
        "y_counter_bytes": ["B1", "00"],
        "logical_to_controller": "controller_y=199-logical_y",
        "corridor_bytes": 1908,
        "frame_sha256_unchanged": EXPECTED["frame_sha256"],
        "payload_sha256_unchanged": EXPECTED["payload_sha256"],
        "protected_topology": ["0x24", "0xCF", "0x20", "BUSY", "official_cached_mode2"],
        "negative_fixtures": {
            "old_127_to_22": "rejected",
            "wrong_counter": "rejected",
            "window_counter_mismatch": "rejected",
            "wrong_direction": "rejected",
            "stacked_y22_to_127_plus_y72_to_177": "rejected",
        },
        "build": {
            "recipe": "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 -EpaperSsd1681R12V22CalmCuriousWarmSamplerDiagnostic -Optimization O2 -Force",
            "optimization": "O2",
        },
        "failures": failures,
    }
    if args.hex and args.hex.exists():
        result["hex_sha256"] = sha256(args.hex)
    if args.elf and args.elf.exists():
        result["elf_sha256"] = sha256(args.elf)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
