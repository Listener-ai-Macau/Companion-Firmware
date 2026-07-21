#!/usr/bin/env python3
"""Verify the production-off WB55 build for one V22 component bridge."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import zlib
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from generate_companion_v22_emotion_separation_target_rig import (  # noqa: E402
    OUTPUT as TARGET_RIG_OUTPUT,
    build_artifacts,
)


BUILD_ROOT = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup"
DEFAULT_BUILD_DIRECTORY = BUILD_ROOT / "build_v22_emotion_bridge_demo_0"
DEFAULT_TARGET = "Companion_Nucleo_WB55RG_V22EmotionBridgeDemo_0"
DEFAULT_WRITE = ROOT / "docs/validation/companion-v22-emotion-separation-wb55-demo-build-gate-20260719.json"
PACK = TARGET_RIG_OUTPUT / "companion-v22-emotion-separation-rig-candidate-200x200.crig"
PROFILE_SOURCE = ROOT / "app/companion_pendant/epaper/generated/expression_rig_v22_emotion_separation_candidate_profile.c"
APP_BLE_SOURCE = BUILD_ROOT / "Core/Src/app_ble.c"
MAKEFILE = BUILD_ROOT / "Makefile"
BUILD_SCRIPT = ROOT / "tools/build_nucleo_bringup.ps1"
MAKE = pathlib.Path(
    "C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/"
    "com.st.stm32cube.ide.mcu.externaltools.make.win32_2.2.100.202601091506/"
    "tools/bin/make.exe"
)
NM = pathlib.Path(
    "C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/"
    "com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.14.3.rel1.win32_1.0.100.202602081740/"
    "tools/bin/arm-none-eabi-nm.exe"
)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def relative(path: pathlib.Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def load_header_blob(path: pathlib.Path) -> tuple[int, int, bytes]:
    source = path.read_text(encoding="ascii")
    size_match = re.search(r"BLOB_SIZE\s+(\d+)u", source)
    crc_match = re.search(r"BLOB_CRC32\s+0x([0-9A-Fa-f]{8})u", source)
    if size_match is None or crc_match is None:
        raise ValueError("provision header is missing size or CRC macros")
    blob = bytes(int(value, 16) for value in re.findall(r"0x([0-9A-Fa-f]{2})u", source))
    return int(size_match.group(1)), int(crc_match.group(1), 16), blob


def command_text(command: list[str], cwd: pathlib.Path) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=30,
    )
    if completed.returncode != 0:
        raise ValueError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n{completed.stdout}"
        )
    return completed.stdout


def verify(build_directory: pathlib.Path, target: str, edge: int) -> dict[str, Any]:
    errors: list[str] = []
    expected = build_artifacts()
    expected_files = {
        "pack": expected["pack"],
        "layout": expected["layout"],
        "header": expected["header"],
        "source": expected["source"],
        "pack metadata": expected["pack_metadata"],
    }
    for label, (content, path) in expected_files.items():
        if not path.is_file() or path.read_bytes() != content:
            errors.append(f"generated V22 target {label} drifted")

    elf = build_directory / f"{target}.elf"
    hex_file = build_directory / f"{target}.hex"
    bin_file = build_directory / f"{target}.bin"
    map_file = build_directory / f"{target}.map"
    provision_pack = build_directory / "generated/companion-v22-emotion-separation-rig-candidate-200x200.crig"
    provision_header = build_directory / "generated/companion_screen_asset_provision_blob.h"
    artifacts = (elf, hex_file, bin_file, map_file, provision_pack, provision_header)
    for artifact in artifacts:
        if not artifact.is_file() or artifact.stat().st_size == 0:
            errors.append(f"missing WB55 demo artifact: {artifact.name}")

    candidate_pack = PACK.read_bytes() if PACK.is_file() else b""
    if provision_pack.is_file() and provision_pack.read_bytes() != candidate_pack:
        errors.append("provisioned WB55 CRIG is not byte-identical to the V22 target candidate")
    if provision_header.is_file():
        try:
            header_size, header_crc32, header_blob = load_header_blob(provision_header)
            if header_size != len(candidate_pack) or header_crc32 != zlib.crc32(candidate_pack):
                errors.append("provision header size or CRC does not identify the V22 CRIG")
            if header_blob != candidate_pack:
                errors.append("provision header payload is not byte-identical to the V22 CRIG")
        except ValueError as exc:
            errors.append(str(exc))

    symbols: list[str] = []
    if elf.is_file():
        if not NM.is_file():
            errors.append("STM32 ARM nm tool is unavailable")
        else:
            try:
                symbols = command_text([str(NM), "-g", "--defined-only", str(elf)], ROOT).splitlines()
                required_symbols = (
                    "Companion_Screen_PlayV22EmotionBridgeDemo",
                    "comp_v22_emotion_separation_rig_candidate_profile",
                    "comp_v22_emotion_separation_rig_candidate_bridge",
                    "comp_v22_emotion_separation_rig_candidate_runtime_activation_allowed",
                )
                for symbol in required_symbols:
                    if not any(line.rstrip().endswith(symbol) for line in symbols):
                        errors.append(f"WB55 demo ELF is missing required V22 symbol: {symbol}")
            except ValueError as exc:
                errors.append(str(exc))

    makefile = MAKEFILE.read_text(encoding="utf-8") if MAKEFILE.is_file() else ""
    build_script = BUILD_SCRIPT.read_text(encoding="utf-8") if BUILD_SCRIPT.is_file() else ""
    app_ble = APP_BLE_SOURCE.read_text(encoding="utf-8") if APP_BLE_SOURCE.is_file() else ""
    profile_source = PROFILE_SOURCE.read_text(encoding="utf-8") if PROFILE_SOURCE.is_file() else ""
    if "ifeq ($(EPAPER_V22_EMOTION_BRIDGE_DEMO),1)\nC_SOURCES += $(ROOT)/app/companion_pendant/epaper/generated/expression_rig_v22_emotion_separation_candidate_profile.c" not in makefile:
        errors.append("V22 profile source is not guarded by the explicit demo build flag")
    for required_text in (
        "[switch]$EpaperV22EmotionBridgeDemo",
        "EPAPER_V22_EMOTION_BRIDGE_DEMO=1",
        "EPAPER_V22_EMOTION_BRIDGE_DEMO_EDGE=$EpaperV22EmotionBridgeDemoEdge",
        "-not $ScreenAssetProvision",
        "build_v22_emotion_bridge_demo_$EpaperV22EmotionBridgeDemoEdge",
    ):
        if required_text not in build_script:
            errors.append(f"WB55 build entrypoint policy marker is missing: {required_text}")
    v22_function = app_ble[app_ble.find("bool Companion_Screen_PlayV22EmotionBridgeDemo(void)"):]
    for required_text in (
        "#if COMPANION_SCREEN_V22_EMOTION_BRIDGE_DEMO",
        "comp_v22_emotion_separation_rig_candidate_runtime_activation_allowed()",
        ".refresh_mode = COMP_EPAPER_REFRESH_FULL",
        "refresh=full_only",
        "reverse=disabled",
        "next_auto_frame=none",
        "report.transferred_bytes < 10000u",
    ):
        if required_text not in v22_function:
            errors.append(f"V22 WB55 demo policy marker is missing: {required_text}")
    if not re.search(
        r"comp_v22_emotion_separation_rig_candidate_runtime_activation_allowed\s*\(void\)\s*\{\s*return false;\s*\}",
        profile_source,
    ):
        errors.append("V22 candidate profile no longer declares runtime activation false")

    normal_dry_run_profile_linked = None
    if not MAKE.is_file():
        errors.append("STM32 make tool is unavailable")
    else:
        try:
            normal_dry_run = command_text(
                [str(MAKE), "-n", "-B", "BUILD_DIR=.cache/v22-normal-product-dry-run", "TARGET=normal-product-dry-run", "all"],
                BUILD_ROOT,
            )
            normal_dry_run_profile_linked = "expression_rig_v22_emotion_separation_candidate_profile.c" in normal_dry_run
            if normal_dry_run_profile_linked:
                errors.append("normal product dry-run would compile the V22 candidate profile")
        except ValueError as exc:
            errors.append(str(exc))

    return {
        "schema": "companion.v22_emotion_separation_wb55_demo_build_gate.v1",
        "status": "PASS_V22_EMOTION_SEPARATION_WB55_PRODUCTION_OFF_DEMO_BUILD_GATE" if not errors else
                  "FAIL_V22_EMOTION_SEPARATION_WB55_PRODUCTION_OFF_DEMO_BUILD_GATE",
        "build_target": target,
        "bridge_edge": edge,
        "artifacts": {
            relative(path): sha256(path) if path.is_file() else None for path in artifacts
        },
        "candidate_pack": relative(PACK),
        "candidate_pack_sha256": sha256(PACK) if PACK.is_file() else None,
        "candidate_pack_bytes": len(candidate_pack),
        "provision_blob_crc32": f"0x{zlib.crc32(candidate_pack):08X}" if candidate_pack else None,
        "elf_required_symbols": [line.strip() for line in symbols if "v22_emotion" in line or "PlayV22Emotion" in line],
        "normal_product_v22_profile_linked": normal_dry_run_profile_linked,
        "same_browser_target_component_plan": "V22 profile replay is already exact against the accepted browser/PBM plan; this build links that same profile only in the explicit demo.",
        "refresh_policy": "every directed-bridge frame is COMP_EPAPER_REFRESH_FULL pending the vendor CWF1 waveform gate",
        "end_behavior": "settled target remains static; automatic reverse and playlist are disabled",
        "runtime_resource_activated": False,
        "firmware_flashed": False,
        "panel_observed": False,
        "special_event_fallback": "fail_closed",
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-directory", type=pathlib.Path, default=DEFAULT_BUILD_DIRECTORY)
    parser.add_argument("--target", default=DEFAULT_TARGET)
    parser.add_argument("--edge", type=int, choices=range(10), default=0)
    parser.add_argument("--write", type=pathlib.Path, default=DEFAULT_WRITE)
    args = parser.parse_args()
    result = verify(args.build_directory.resolve(), args.target, args.edge)
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if result["status"] != "PASS_V22_EMOTION_SEPARATION_WB55_PRODUCTION_OFF_DEMO_BUILD_GATE":
        for error in result["errors"]:
            print(f"ERROR: {error}")
        return 1
    print("PASS: explicit WB55 V22 demo embeds the exact inactive CRIG and keeps full-refresh-only, no-reverse behavior.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
