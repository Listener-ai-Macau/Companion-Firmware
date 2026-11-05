#!/usr/bin/env python3
"""Static gate for WB55 menu values that must come from live product state."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MENU = ROOT / "app/companion_pendant/epaper/screen_menu.c"
BLE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
MAIN = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"
PANEL = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
ACTIVE_SOURCE = (
    ROOT
    / ".cache/validation/comp776-component-clip-fix-20260812"
    / "source-pack-5059/source-pack-manifest.json"
)

FONT = {
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F),
    "3": (0x1E, 0x01, 0x01, 0x0E, 0x01, 0x01, 0x1E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    "5": (0x1F, 0x10, 0x10, 0x1E, 0x01, 0x01, 0x1E),
    "6": (0x0E, 0x10, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    "7": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    "8": (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    "9": (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x01, 0x0E),
    "B": (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    "K": (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
}


def has(text: str, *needles: str) -> bool:
    return all(needle in text for needle in needles)


def read_pbm(path: Path) -> tuple[int, int, list[list[bool]]]:
    raw = path.read_bytes()
    lines = raw.splitlines(keepends=True)
    assert lines[0].strip() == b"P4"
    offset = len(lines[0])
    dimensions = None
    for line in lines[1:]:
        offset += len(line)
        stripped = line.strip()
        if stripped and not stripped.startswith(b"#"):
            dimensions = tuple(map(int, stripped.split()))
            break
    assert dimensions is not None
    width, height = dimensions
    stride = (width + 7) // 8
    payload = raw[offset : offset + stride * height]
    assert len(payload) == stride * height
    pixels = [
        [bool(payload[y * stride + x // 8] & (0x80 >> (x & 7))) for x in range(width)]
        for y in range(height)
    ]
    return width, height, pixels


def write_pbm(path: Path, width: int, height: int, pixels: list[list[bool]]) -> str:
    stride = (width + 7) // 8
    payload = bytearray(stride * height)
    for y in range(height):
        for x in range(width):
            if pixels[y][x]:
                payload[y * stride + x // 8] |= 0x80 >> (x & 7)
    encoded = f"P4\n{width} {height}\n".encode() + payload
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)
    return hashlib.sha256(encoded).hexdigest().upper()


def fill_white(pixels: list[list[bool]], x: int, y: int, w: int, h: int) -> None:
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            pixels[yy][xx] = False


def draw_text(pixels: list[list[bool]], x: int, y: int, value: str) -> None:
    for character in value:
        rows = FONT[character]
        for yy, row in enumerate(rows):
            for xx in range(5):
                if row & (1 << (4 - xx)):
                    pixels[y + yy][x + xx] = True
        x += 6


def diff_bbox(a: list[list[bool]], b: list[list[bool]], y_range: range) -> tuple[int, int, int, int]:
    points = [
        (x, y)
        for y in y_range
        for x in range(len(a[y]))
        if a[y][x] != b[y][x]
    ]
    return (
        min(x for x, _ in points), min(y for _, y in points),
        max(x for x, _ in points) + 1, max(y for _, y in points) + 1,
    )


def contained(box: tuple[int, int, int, int], wipe: tuple[int, int, int, int]) -> bool:
    return box[0] >= wipe[0] and box[1] >= wipe[1] and box[2] <= wipe[2] and box[3] <= wipe[3]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--preview-dir", type=Path)
    args = parser.parse_args()
    menu = MENU.read_text(encoding="utf-8")
    ble = BLE.read_text(encoding="utf-8")
    target = MAIN.read_text(encoding="utf-8")
    panel = PANEL.read_text(encoding="utf-8")
    source = json.loads(ACTIVE_SOURCE.read_text(encoding="utf-8"))
    states = {state["id"]: state for state in source["states"]}
    source_root = ACTIVE_SOURCE.parent
    s9 = states["menu_ui_zh_cn_s9_o0_normal"]
    s9_empty = states["menu_ui_zh_cn_s9_o0_normal_v1"]
    s11 = states["menu_ui_zh_cn_s11_o0_normal"]
    s11_empty = states["menu_ui_zh_cn_s11_o0_normal_v1"]
    width, height, s9_pixels = read_pbm(source_root / s9["pbm_file"])
    _, _, s9_empty_pixels = read_pbm(source_root / s9_empty["pbm_file"])
    _, _, s11_pixels = read_pbm(source_root / s11["pbm_file"])
    _, _, s11_empty_pixels = read_pbm(source_root / s11_empty["pbm_file"])
    count_wipe = (168, 48, 177, 59)
    usage_wipe = (124, 86, 194, 102)
    s9_count_delta = diff_bbox(s9_pixels, s9_empty_pixels, range(0, 70))
    s9_usage_delta = diff_bbox(s9_pixels, s9_empty_pixels, range(70, height))
    s11_count_delta = diff_bbox(s11_pixels, s11_empty_pixels, range(0, 70))

    # Replay the exact C coordinates/font against the active baked source.
    preview_hashes = {}
    for name, pixels, view in (
        ("storage-live-7-915", s9_pixels, "storage"),
        ("clear-live-7", s11_pixels, "clear"),
    ):
        rendered = [row[:] for row in pixels]
        fill_white(rendered, 168, 48, 9, 11)
        draw_text(rendered, 170, 50, "7")
        if view == "storage":
            value = "915KB"
            fill_white(rendered, 124, 86, 70, 16)
            draw_text(rendered, 194 - len(value) * 6, 90, value)
        if args.preview_dir is not None:
            preview_hashes[name] = write_pbm(
                args.preview_dir / f"{name}.pbm", width, height, rendered
            )

    checks = {
        "defaults_disconnected": "link_connected = initialize ? false" in menu,
        "defaults_empty_catalog": has(
            menu,
            "recording_count = initialize ? 0u",
            "recording_storage_kb = initialize ? 0u",
        ),
        "battery_unavailable_without_gauge": "battery_percent = initialize ? 0xFFu" in menu,
        "connection_variant_uses_live_ble": has(
            ble,
            "view == COMP_SCREEN_MENU_VIEW_BROWSER_CONNECTION",
            "s_companion_ble_connected ? 0u : 2u",
        ),
        "connection_screen_refreshes_on_link_change": has(
            ble,
            "Companion_Screen_RefreshBleStatus",
            "COMP_SCREEN_MENU_VIEW_BROWSER_CONNECTION",
        ),
        "catalog_scans_bounded_journal": has(
            target,
            "index < COMP_RECORDING_JOURNAL_MAX_ENTRIES",
            "&s_recording_journal.catalog.entries[index]",
        ),
        "catalog_excludes_in_progress_writes": (
            "entry->sync_state >= COMP_RECORDING_JOURNAL_UNSYNCED" in target
        ),
        "catalog_reports_count_and_ceil_kib": has(
            target,
            "recording_count++",
            "recording_bytes += entry->total_length",
            "(recording_bytes + 1023u) / 1024u",
        ),
        "catalog_change_invalidates_menu_revision": has(
            target,
            "s_screen_menu.browser.recording_count = recording_count",
            "s_screen_menu.browser.recording_storage_kb = recording_storage_kb",
            "s_screen_menu.revision++",
        ),
        "active_pixel_source_is_known_baked_input": (
            s9["practical_state"] == {
                "menuRecordingCount": 1,
                "menuRecordingStorageKb": 384,
            }
            and s11["practical_state"] == {
                "menuRecordingCount": 1,
                "menuRecordingStorageKb": 384,
            }
        ),
        "catalog_snapshot_attached_to_source_frame": has(
            ble,
            "s_companion_browser_catalog_overlay_view = (uint8_t)view",
            "Companion_Screen_RuntimeMenuCatalogPacked()",
            "charger_frame_index = s_companion_browser_catalog_overlay_view",
            "recording_overlay_frame_index =",
            "s_companion_browser_catalog_overlay_packed",
        ),
        "panel_overlays_after_external_frame_copy": has(
            panel,
            "comp_epaper_expression_asset_source_copy_frame_index(",
            "comp_screen_menu_render_browser_catalog(",
            "request->charger_frame_index",
            "request->recording_overlay_frame_index",
        ),
        "overlay_erases_full_baked_value_fields": has(
            menu,
            "fill_rect(&framebuffer, 168, 48, 9u, 11u, false)",
            "fill_rect(&framebuffer, 124, 86, 70u, 16u",
            "snprintf(value, sizeof(value), \"%uKB\"",
        ),
        "wipe_rectangles_cover_every_baked_delta": (
            contained(s9_count_delta, count_wipe)
            and contained(s9_usage_delta, usage_wipe)
            and contained(s11_count_delta, count_wipe)
        ),
    }
    status = "MACHINE_READY" if all(checks.values()) else "NO_GO"
    result = {
        "schema": "companion.comp_req_784.menu_runtime_truth.v2",
        "status": status,
        "checks": checks,
        "pixel_audit": {
            "active_source_manifest": str(ACTIVE_SOURCE),
            "source_baked_values": "1 recording / 384KB",
            "s9_count_delta_bbox": s9_count_delta,
            "s9_usage_delta_bbox": s9_usage_delta,
            "s11_count_delta_bbox": s11_count_delta,
            "count_wipe_bbox": count_wipe,
            "usage_wipe_bbox": usage_wipe,
            "replay_values": "7 recordings / 915KB",
            "preview_sha256": preview_hashes,
        },
        "hardware_contact": 0,
    }
    encoded = json.dumps(result, indent=2) + "\n"
    if args.receipt is not None:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if status == "MACHINE_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
