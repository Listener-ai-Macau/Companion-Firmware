#!/usr/bin/env python3
"""Render review PNGs through the mounted production WBA resource/runtime path.

The C harness mounts the requested UI partition with
``comp_runtime_resources_mount`` and renders every frame through
``comp_runtime_renderer_render``.  Python only wraps each returned 5000-byte
1bpp framebuffer in a PNG; it never redraws menu text, icons, status, or live
values.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess

from PIL import Image

from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app/companion_pendant"
HARNESS = APP / "runtime/tests/render_wba_menu_review.c"
FRAME_BYTES = 5000
WIDTH = HEIGHT = 200

SOURCES = [
    HARNESS,
    APP / "runtime/companion_resources.c",
    APP / "runtime/companion_renderer.c",
    APP / "epaper/asset_store.c",
    APP / "epaper/emote_asset_pack.c",
    APP / "epaper/emote_player.c",
    APP / "epaper/ui_asset_generation.c",
    APP / "epaper/screen_menu.c",
    APP / "epaper/screen_framebuffer.c",
    APP / "epaper/motion_coordinator.c",
    APP / "touch/browser_interaction_runtime.c",
]

INCLUDES = [
    APP / "runtime",
    APP / "runtime/generated",
    APP / "epaper",
    APP / "touch",
    APP / "playback",
    APP / "power",
    APP / "imu",
    ROOT / "third_party/denzic-platform/audio/embedded/c/include",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_harness(output: Path, log: Path) -> Path:
    executable = output / ("render_wba_menu_review.exe" if os.name == "nt" else "render_wba_menu_review")
    if os.name == "nt":
        devcmd = find_vsdevcmd()
        if devcmd is None:
            raise RuntimeError("Visual Studio C++ Build Tools not found")
        arguments = [
            "cl.exe",
            "/nologo",
            "/std:c11",
            "/W4",
            "/WX",
            "/utf-8",
            "/D_CRT_SECURE_NO_WARNINGS",
            "/DCOMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK=1",
            "/DCOMPANION_WBA_RESOURCE_PROFILE=1",
            *(f"/I{path}" for path in INCLUDES),
            *(str(path) for path in SOURCES),
            f"/Fe:{executable}",
        ]
        command_file = output / "build.cmd"
        command_file.write_text(
            f'@echo off\ncall "{devcmd}" -arch=amd64 -host_arch=amd64 >nul\n'
            "if errorlevel 1 exit /b %errorlevel%\n"
            + subprocess.list2cmdline(arguments)
            + "\n",
            encoding="utf-8",
        )
        run(["cmd.exe", "/d", "/c", str(command_file)], output, log)
    else:
        compiler = shutil.which("cc") or shutil.which("clang")
        if compiler is None:
            raise RuntimeError("Native C compiler not found")
        run(
            [
                compiler,
                "-std=c11",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-D_CRT_SECURE_NO_WARNINGS",
                "-DCOMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK=1",
                "-DCOMPANION_WBA_RESOURCE_PROFILE=1",
                *(f"-I{path}" for path in INCLUDES),
                *(str(path) for path in SOURCES),
                "-o",
                str(executable),
            ],
            output,
            log,
        )
    return executable


def parse_identity(output: str) -> dict[str, object]:
    line = next((row for row in output.splitlines() if row.startswith("IDENTITY\t")), None)
    if line is None:
        raise RuntimeError("native renderer did not report mounted identity")
    values: dict[str, object] = {}
    for field in line.split("\t")[1:]:
        key, value = field.split("=", 1)
        values[key] = value if key == "resource_id" else int(value)
    return values


def bit_difference(left: bytes, right: bytes) -> int:
    if len(left) != len(right):
        raise ValueError("frame length mismatch")
    return sum((a ^ b).bit_count() for a, b in zip(left, right))


def render_png(raw_path: Path, png_path: Path) -> None:
    raw = raw_path.read_bytes()
    if len(raw) != FRAME_BYTES:
        raise ValueError(f"{raw_path.name}: expected {FRAME_BYTES} bytes, got {len(raw)}")
    image = Image.frombytes("1", (WIDTH, HEIGHT), raw)
    if image.tobytes() != raw:
        raise ValueError(f"{raw_path.name}: Pillow changed framebuffer bytes before save")
    image.save(png_path, format="PNG")
    check = Image.open(png_path)
    if check.mode != "1" or check.size != (WIDTH, HEIGHT) or check.tobytes() != raw:
        raise ValueError(f"{png_path.name}: PNG round trip changed native pixels")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ui-partition", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--expect-generation", type=int)
    parser.add_argument("--expect-ui-sha256")
    args = parser.parse_args()

    partition = args.ui_partition.resolve()
    output = args.out.resolve()
    if not partition.is_file():
        raise FileNotFoundError(partition)
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"output directory is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    raw_directory = output / "raw"
    png_directory = output / "png"
    raw_directory.mkdir()
    png_directory.mkdir()
    log = output / "build-and-render.log"
    log.write_text("", encoding="utf-8")

    partition_sha = sha256(partition)
    if args.expect_ui_sha256 is not None and partition_sha.lower() != args.expect_ui_sha256.lower():
        raise RuntimeError(
            f"UI partition SHA mismatch: expected {args.expect_ui_sha256.lower()}, got {partition_sha}"
        )

    executable = build_harness(output, log)
    native_output = run(
        [str(executable), str(partition), str(raw_directory)], output, log
    )
    if "PASS_NATIVE_WBA_MENU_REVIEW" not in native_output:
        raise RuntimeError("native renderer completion marker missing")
    identity = parse_identity(native_output)
    if args.expect_generation is not None and identity["generation"] != args.expect_generation:
        raise RuntimeError(
            f"UI generation mismatch: expected {args.expect_generation}, got {identity['generation']}"
        )

    frames_tsv = raw_directory / "frames.tsv"
    with frames_tsv.open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if not rows:
        raise RuntimeError("native renderer produced no fixtures")

    frames: list[dict[str, object]] = []
    raw_by_name: dict[str, bytes] = {}
    for row in rows:
        name = row["name"]
        raw_path = raw_directory / f"{name}.bin"
        png_path = png_directory / f"{name}.png"
        render_png(raw_path, png_path)
        raw = raw_path.read_bytes()
        raw_by_name[name] = raw
        packed = int(row["status_packed"], 16)
        locale_id = int(row["locale"])
        try:
            locale_name = {0: "en", 1: "zh_cn", 2: "zh_tw"}[locale_id]
        except KeyError as error:
            raise RuntimeError(f"unknown native renderer locale: {locale_id}") from error
        frame = {
            "name": name,
            "purpose": row["purpose"],
            "locale": locale_name,
            "screen": int(row["screen"]),
            "page": int(row["page"]),
            "variant": int(row["variant"]),
            "feedbackItem": int(row["feedback_item"]),
            "feedbackPhase": int(row["feedback_phase"]),
            "rendererRequestedState": row["requested_state"],
            "resourceStateRead": row["rendered_state"],
            "pathClassification": (
                "productionNormal"
                if int(row["feedback_phase"]) == 0
                else "authoredResourceOnlyFeedback"
            ),
            "productionRuntimeRequestedThisState": int(row["feedback_phase"]) == 0,
            "statusFixture": {
                "packed": f"0x{packed:08X}",
                "clockValid": bool(packed & 0x8000),
                "clock": f"{(packed >> 8) & 31:02d}:{packed & 63:02d}"
                if packed & 0x8000
                else None,
                "bleConnected": bool(packed & (1 << 16)),
                "batteryValid": bool(int(row["battery_valid"])),
                "batteryPercentRaw": int(row["battery_percent_raw"]),
                "unknownBatteryPolicy": "unfilled icon with dash; no fabricated percentage"
                if not int(row["battery_valid"])
                else None,
            },
            "dynamicFixture": {
                "recordingCount": int(row["recording_count"]),
                "recordingStorageKiB": int(row["recording_storage_kib"]),
                "recordingState": int(row["recording_state"]),
                "recordingElapsedSeconds": int(row["recording_elapsed_seconds"]),
            },
            "raw": {
                "path": raw_path.relative_to(output).as_posix(),
                "bytes": len(raw),
                "sha256": sha256(raw_path),
            },
            "png": {
                "path": png_path.relative_to(output).as_posix(),
                "width": WIDTH,
                "height": HEIGHT,
                "mode": "1",
                "sha256": sha256(png_path),
            },
        }
        frames.append(frame)

    locales = {frame["locale"] for frame in frames}
    screen_coverage = {
        locale: sorted(
            {frame["screen"] for frame in frames if frame["locale"] == locale}
        )
        for locale in sorted(locales)
    }
    home_pages = {
        locale: sorted(
            {
                frame["page"]
                for frame in frames
                if frame["locale"] == locale and frame["screen"] == 0
            }
        )
        for locale in sorted(locales)
    }
    feedback = [frame for frame in frames if frame["feedbackPhase"] != 0]
    if locales != {"en", "zh_cn", "zh_tw"}:
        raise RuntimeError(f"locale coverage incomplete: {locales}")
    if any(screens != list(range(13)) for screens in screen_coverage.values()):
        raise RuntimeError(f"screen coverage incomplete: {screen_coverage}")
    if any(pages != [0, 4] for pages in home_pages.values()):
        raise RuntimeError(f"home page coverage incomplete: {home_pages}")
    contract_path = APP / "runtime/generated/companion_browser_interaction_contract.h"
    count_block = re.search(
        r"companion_browser_menu_item_counts[^=]*=\s*\{([^}]+)\}",
        contract_path.read_text(encoding="utf-8"),
    )
    if count_block is None:
        raise RuntimeError("menu item counts missing from the compiled contract")
    item_counts = [int(value) for value in re.findall(r"(\d+)u", count_block[1])]
    if len(item_counts) != 13:
        raise RuntimeError(f"menu item count contract changed: {item_counts}")
    normal_pages = {
        locale: {
            str(screen): sorted({frame["page"] for frame in frames
                                if frame["locale"] == locale and frame["screen"] == screen
                                and frame["feedbackPhase"] == 0 and frame["variant"] == 0})
            for screen in range(1, 13)
        } for locale in sorted(locales)
    }
    geometry_path = APP / "runtime/generated/companion_wba_menu_geometry.h"
    geometry = geometry_path.read_text(encoding="ascii")
    visible_match = re.search(r"#define COMP_WBA_MENU_VISIBLE_ROWS (\d+)u", geometry)
    if visible_match is None:
        raise RuntimeError("generated visible row geometry missing")
    visible_rows = int(visible_match[1])
    expected_pages = {str(screen): list(range(0, item_counts[screen], visible_rows))
                      for screen in range(1, 13)}
    if any(pages != expected_pages for pages in normal_pages.values()):
        raise RuntimeError(f"default submenu whole-page coverage incomplete: {normal_pages}")
    if {frame["feedbackPhase"] for frame in feedback} != {1, 2, 3}:
        raise RuntimeError("feedback phase coverage incomplete")
    if not any(frame["purpose"] == "dynamic-storage-overlay" for frame in frames):
        raise RuntimeError("storage overlay fixture missing")
    if not any(frame["purpose"] == "measured-battery-overlay" for frame in frames):
        raise RuntimeError("measured battery fixture missing")
    if not any(
        not frame["statusFixture"]["batteryValid"] for frame in frames
    ):
        raise RuntimeError("unknown battery fixture missing")

    comparisons: dict[str, int] = {}
    for locale in ("en", "zh_cn", "zh_tw"):
        pairs = {
            f"{locale}.recordingDynamic": (
                f"{locale}-01-recording-p0",
                f"{locale}-recording-active",
            ),
            f"{locale}.storageDynamic": (
                f"{locale}-09-storage-p0",
                f"{locale}-storage-live-values",
            ),
            f"{locale}.powerKnownVsUnknown": (
                f"{locale}-10-power-p0",
                f"{locale}-power-measured",
            ),
            f"{locale}.clearAckVsNormal": (
                f"{locale}-11-clear-recordings-p0",
                f"{locale}-clear-ack",
            ),
            f"{locale}.restoreAckVsNormal": (
                f"{locale}-12-restore-defaults-p0",
                f"{locale}-restore-ack",
            ),
        }
        for label, (left, right) in pairs.items():
            comparisons[label] = bit_difference(raw_by_name[left], raw_by_name[right])
    if any(value == 0 for value in comparisons.values()):
        raise RuntimeError(f"representative dynamic/feedback fixture did not change pixels: {comparisons}")

    identity_report = {
        "schema": "companion.wba-menu-review-identity.v1",
        "uiPartition": {
            "path": str(partition),
            "bytes": partition.stat().st_size,
            "sha256": partition_sha,
        },
        "mounted": identity,
        "compileDefines": [
            "COMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK=1",
            "COMPANION_WBA_RESOURCE_PROFILE=1",
        ],
    }
    (output / "identity.json").write_text(
        json.dumps(identity_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output / "frames.json").write_text(
        json.dumps(frames, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    source_paths = sorted({Path(__file__), *SOURCES, contract_path, geometry_path,
                           *(path for directory in INCLUDES for path in directory.glob('*.h'))})
    result = {
        "schema": "companion.wba-menu-native-review.v1",
        "result": "PASS_SOFTWARE_NATIVE_MENU_RENDER_ONLY",
        "hardwareAcceptance": "NOT_RUN",
        "rendererPath": [
            "comp_asset_store_init_memory",
            "comp_runtime_resources_mount",
            "comp_runtime_renderer_render",
            "comp_runtime_renderer_complete",
        ],
        "feedbackBoundary": (
            "Frames classified productionNormal are requested directly by the production "
            "renderer (item=255, phase=0). Frames classified authoredResourceOnlyFeedback "
            "use an explicitly recorded read-state override so the same renderer compositor "
            "adds live status and dynamic overlays to authored ack/processing/result resources. "
            "The product renderer does not schedule those authored phases. Actual operation "
            "outcomes use token-bound native message overlays, exercised separately by "
            "tools/test_wba_menu_feedback.py; these catalog fixtures keep menu_feedback=NONE."
        ),
        "pngBoundary": (
            "PNG conversion wraps the exact native 5000-byte 200x200 1bpp framebuffer; "
            "round-trip bytes must match. No Pillow text/icon/menu drawing is used."
        ),
        "identity": identity_report,
        "coverage": {
            "frameCount": len(frames),
            "locales": sorted(locales),
            "screensByLocale": screen_coverage,
            "homePagesByLocale": home_pages,
            "defaultSubmenuPagesByLocale": normal_pages,
            "visibleSubmenuRows": visible_rows,
            "feedbackPhases": sorted({frame["feedbackPhase"] for frame in feedback}),
            "productionNormalFrameCount": sum(
                frame["pathClassification"] == "productionNormal" for frame in frames
            ),
            "authoredResourceOnlyFeedbackFrameCount": sum(
                frame["pathClassification"] == "authoredResourceOnlyFeedback"
                for frame in frames
            ),
            "representativePixelDifferences": comparisons,
            "unknownBatteryPreserved": True,
            "unknownBatteryDisplay": "unfilled battery with dash",
        },
        "artifacts": {
            "identity": "identity.json",
            "frames": "frames.json",
            "nativeManifest": "raw/frames.tsv",
            "rawDirectory": "raw",
            "pngDirectory": "png",
            "log": "build-and-render.log",
        },
        "sourceSha256": {
            str(path.relative_to(ROOT)): sha256(path) for path in source_paths
        },
    }
    (output / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"PASS_SOFTWARE_NATIVE_MENU_RENDER_ONLY: {len(frames)} frames, "
        f"generation={identity['generation']} -> {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
