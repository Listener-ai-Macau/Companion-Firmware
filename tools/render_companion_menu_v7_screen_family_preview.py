#!/usr/bin/env python3
"""Split the generated Companion v7 menu storyboard into owner-review pages only."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
ITERATION = ROOT / "docs/art/iterations/companion-menu-v7-screen-family"
SOURCE = ITERATION / "generated_menu_screen_family_v7_3_candidate.png"
OUT = ITERATION / "review-200x200"
REPORT = ROOT / "docs/validation/companion-menu-v7-screen-family-preview-20260717.json"
FONT = Path(r"C:\Windows\Fonts\msyh.ttc")


SCREENS = (
    {
        "order": 1,
        "id": "home",
        "title": "Home",
        "title_labels": {"en": None, "zh_cn": None},
        "crop": (92, 158, 575, 634),
        "labels": {"en": ("Voice", "Device", "Connection", "Preferences"), "zh_cn": ("语音", "设备", "连接", "偏好设置")},
        "slots": ((64, 28), (64, 76), (64, 124), (64, 172)),
    },
    {
        "order": 2,
        "id": "voice",
        "title": "Voice",
        "title_labels": {"en": "Voice", "zh_cn": "语音"},
        "crop": (680, 158, 1162, 634),
        "labels": {"en": ("Recording", "History", "Wake word", "Feedback"), "zh_cn": ("录音状态", "录音历史", "唤醒词", "语音反馈")},
        "slots": ((62, 54), (62, 92), (62, 130), (62, 168)),
    },
    {
        "order": 3,
        "id": "device",
        "title": "Device",
        "title_labels": {"en": "Device", "zh_cn": "设备"},
        "crop": (40, 754, 408, 1143),
        "labels": {"en": ("E-paper", "Touch", "Battery", "UI assets"), "zh_cn": ("电子纸", "触控", "电池", "界面资源")},
        "slots": ((65, 63), (65, 98), (65, 133), (65, 168)),
    },
    {
        "order": 4,
        "id": "connection",
        "title": "Connection",
        "title_labels": {"en": "Connection", "zh_cn": "连接"},
        "crop": (442, 754, 809, 1143),
        "labels": {"en": ("Pair device", "Link status", "Reconnect"), "zh_cn": ("配对设备", "连接状态", "重新连接")},
        "slots": ((65, 54), (65, 108), (65, 164)),
    },
    {
        "order": 5,
        "id": "preferences",
        "title": "Preferences",
        "title_labels": {"en": "Preferences", "zh_cn": "偏好设置"},
        "crop": (846, 754, 1215, 1143),
        "labels": {"en": ("Language", "Interaction", "Diagnostics", "About"), "zh_cn": ("语言", "交互", "诊断", "关于")},
        "slots": ((65, 63), (65, 98), (65, 133), (65, 168)),
    },
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT), size=size)


def normalized_crop(source: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    crop = source.crop(box)
    return ImageOps.pad(crop, (200, 200), method=Image.Resampling.LANCZOS, color=255, centering=(0.5, 0.5)).convert("L")


def localize(page: Image.Image, labels: tuple[str, ...], slots: tuple[tuple[int, int], ...], title: str | None) -> Image.Image:
    image = page.copy().convert("L")
    draw = ImageDraw.Draw(image)
    if title is not None:
        draw.rectangle((48, 4, 165, 25), fill=255)
        draw.text((56, 7), title, fill=0, font=font(11))
    for text, (x, y) in zip(labels, slots, strict=True):
        # Remove generator guide strokes while preserving row icons and chevrons.
        draw.rectangle((x - 3, y - 5, 166, y + 17), fill=255)
        draw.text((x, y - 2), text, fill=0, font=font(11))
    return image.point(lambda value: 255 if value >= 160 else 0, mode="1")


def write_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("1").save(path, format="PNG")


def build_report(write: bool) -> dict[str, object]:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    source = Image.open(SOURCE).convert("L")
    if source.size != (1254, 1254):
        raise ValueError(f"unexpected generated source dimensions: {source.size}")
    pages: list[dict[str, object]] = []
    for screen in SCREENS:
        page = normalized_crop(source, screen["crop"])
        raw_path = OUT / "source" / f"{screen['order']:02d}-{screen['id']}.png"
        en_path = OUT / "en" / f"{screen['order']:02d}-{screen['id']}.png"
        zh_path = OUT / "zh_cn" / f"{screen['order']:02d}-{screen['id']}.png"
        if write:
            write_png(page, raw_path)
            write_png(localize(page, screen["labels"]["en"], screen["slots"], screen["title_labels"]["en"]), en_path)
            write_png(localize(page, screen["labels"]["zh_cn"], screen["slots"], screen["title_labels"]["zh_cn"]), zh_path)
        pages.append({
            "order": screen["order"],
            "id": screen["id"],
            "title": screen["title"],
            "source_crop": list(screen["crop"]),
            "review_pages": {
                "source": {"path": raw_path.relative_to(ROOT).as_posix(), "sha256": digest(raw_path) if raw_path.is_file() else None},
                "en": {"path": en_path.relative_to(ROOT).as_posix(), "sha256": digest(en_path) if en_path.is_file() else None, "labels": list(screen["labels"]["en"])},
                "zh_cn": {"path": zh_path.relative_to(ROOT).as_posix(), "sha256": digest(zh_path) if zh_path.is_file() else None, "labels": list(screen["labels"]["zh_cn"])},
            },
        })
    report = {
        "schema": "companion.menu_v7_screen_family_preview.v1",
        "status": "PASS_MACHINE_SCREEN_FAMILY_PREVIEW_PENDING_OWNER",
        "source": {"path": SOURCE.relative_to(ROOT).as_posix(), "sha256": digest(SOURCE), "dimensions_px": [1254, 1254]},
        "screen_order": [screen["id"] for screen in SCREENS],
        "pages": pages,
        "runtime_boundary": {"pbm_imported": False, "cemp_packed": False, "external_flash_provisioned": False, "firmware_flashed": False, "runtime_resource_activated": False},
        "review_rule": "Each source, English and zh-CN page must be opened alone in order. The raw storyboard and its crops are review artifacts only.",
    }
    if write:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    report = build_report(args.write)
    expected = ["home", "voice", "device", "connection", "preferences"]
    if report["screen_order"] != expected or any(value is None for page in report["pages"] for value in (page["review_pages"]["source"]["sha256"], page["review_pages"]["en"]["sha256"], page["review_pages"]["zh_cn"]["sha256"])):
        raise SystemExit("FAIL: v7 screen-family review pages are incomplete")
    print(f"PASS: v7 source split to {len(report['pages'])} ordered single-page 200x200 review groups -> {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
