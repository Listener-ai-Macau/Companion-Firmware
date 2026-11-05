#!/usr/bin/env python3
"""Import the owner-accepted menu-v3 sheet into 200x200 CEMP menu assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re

from PIL import Image, ImageDraw, ImageFont


ROOT = pathlib.Path(__file__).resolve().parents[1]
WIDTH = 200
HEIGHT = 200
SOURCE = ROOT / "docs/art/generated_companion_menu_reference_v3.png"
SOURCE_SHA256 = "D87E45A49AA623552B867C9EDAADB906CA282DF2C2C062D3A127A277920F9F81"
SOURCE_SIZE = (1640, 959)
ASSET_REVISION = 53

MENU_V3_STYLE = {
    "name": "menu-v3-2026-07-13",
    "source": "docs/art/generated_companion_menu_reference_v3.png",
    "source_sha256": "D87E45A49AA623552B867C9EDAADB906CA282DF2C2C062D3A127A277920F9F81",
    "source_size": [1640, 959],
    "external_flash_only": True,
    "home_frame_count_per_language": 1,
    "detail_page_count_per_language": 6,
}

# Each crop is a square design viewport from the accepted sheet.  The source
# geometry, icons, line rhythm, and visual hierarchy come from this table;
# no implementation-side menu illustration is permitted here.
SCREEN_CROPS = {
    "home": (34, 70, 384, 420),
    "record": (435, 70, 785, 420),
    "status": (825, 70, 1175, 420),
    "phone": (1224, 70, 1574, 420),
    "device": (204, 515, 554, 865),
    "preferences": (600, 515, 950, 865),
    "about": (1020, 515, 1370, 865),
}
VIEWS = tuple(SCREEN_CROPS)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def find_font(bold: bool) -> pathlib.Path:
    candidates = (
        pathlib.Path(r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc"),
        pathlib.Path(r"C:\Windows\Fonts\simhei.ttf"),
        pathlib.Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else
                     "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No CJK menu-localization font was found")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(find_font(bold)), size)


def clear(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: int = 255) -> None:
    draw.rectangle(box, fill=fill)


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, *,
         size: int = 10, fill: int = 0, bold: bool = False) -> None:
    draw.text(xy, value, font=font(size, bold), fill=fill)


def localize_home(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)
    labels = ("语音与录音", "状态", "手机连接", "设备", "偏好", "关于")
    for item, label in enumerate(labels):
        row_top = 35 + item * 26
        if item == 0:
            clear(draw, (42, row_top + 2, 169, row_top + 24), 0)
            text(draw, (48, row_top + 6), label, size=10, fill=255, bold=True)
        else:
            clear(draw, (42, row_top + 2, 169, row_top + 24))
            text(draw, (48, row_top + 6), label, size=10, bold=True)


def localize_record(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)
    clear(draw, (47, 36, 160, 53))
    text(draw, (50, 38), "准备好", size=11, bold=True)
    clear(draw, (47, 54, 156, 70))
    text(draw, (50, 56), "轻点开始", size=9)
    clear(draw, (61, 103, 181, 122), 0)
    text(draw, (77, 106), "开始录音", size=10, fill=255, bold=True)
    clear(draw, (7, 140, 133, 156))
    text(draw, (9, 142), "最近录音", size=9)
    clear(draw, (164, 140, 190, 156))
    text(draw, (169, 142), "--", size=9)
    clear(draw, (7, 166, 132, 183))
    text(draw, (9, 168), "唤醒词", size=9)
    clear(draw, (137, 166, 190, 183))
    text(draw, (144, 168), "计划中", size=9)


def localize_status(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)
    labels = ("显示（电子纸）", "触摸面板", "蓝牙（BLE）", "录音状态")
    for row, label in enumerate(labels):
        y = 41 + row * 39
        clear(draw, (78, y, 169, y + 19))
        text(draw, (80, y + 2), label, size=9, bold=True)
        # Values are populated by the runtime overlay.  The source's example
        # values must not masquerade as device telemetry before that happens.
        clear(draw, (140, y, 199, y + 19))


def localize_phone(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)
    labels = ("广播", "已配对设备", "连接状态", "重新连接")
    for row, label in enumerate(labels):
        y = 41 + row * 39
        clear(draw, (40, y, 164, y + 19))
        text(draw, (42, y + 2), label, size=9, bold=True)
        if row < 3:
            # The reference's sample live values begin slightly before 145px
            # after the source crop is resized.  Clear from 130px so a partial
            # "Connected" cannot survive beside the localized label.
            clear(draw, (130, y, 199, y + 19))


def localize_device(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)
    rows = ("电子纸配置", "触摸健康", "外部资源", "电池")
    for row, label in enumerate(rows):
        y = 42 + row * 38
        clear(draw, (47, y, 157, y + 19))
        text(draw, (48, y + 2), label, size=9, bold=True)
        # The C runtime owns all values here.  The source's A2/Fast, Good, and
        # OK(8) examples are visual placeholders, not proven device telemetry.
        clear(draw, (136, y, 199, y + 19))


def localize_preferences(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)
    rows = (("语言", 42), ("手势行为", 82), ("刷新清理", 122))
    for label, y in rows:
        clear(draw, (46, y, 128, y + 20))
        text(draw, (48, y + 2), label, size=10, bold=True)
    # The accepted layout owns the selector position.  Only its language
    # content changes; it remains a real choice rather than a decorative pill.
    clear(draw, (130, 41, 190, 66), 0)
    text(draw, (145, 44), "中文", size=10, fill=255, bold=True)
    clear(draw, (153, 82, 199, 102))
    text(draw, (158, 84), "滑动", size=8)
    clear(draw, (148, 122, 199, 142))
    text(draw, (154, 124), "保留", size=8)


def localize_about(image: Image.Image, revision: int) -> None:
    draw = ImageDraw.Draw(image)
    rows = (("固件版本", "v1.0.0"), ("界面资源版本", f"rev {revision}"),
            ("OTA 更新", "冻结"), ("诊断", ""))
    for row, (label, value) in enumerate(rows):
        y = 42 + row * 38
        clear(draw, (50, y, 157, y + 19))
        text(draw, (52, y + 2), label, size=9, bold=True)
        if value:
            clear(draw, (157, y, 199, y + 19))
            text(draw, (159, y + 2), value, size=8)


LOCALIZERS = {
    "home": localize_home,
    "record": localize_record,
    "status": localize_status,
    "phone": localize_phone,
    "device": localize_device,
    "preferences": localize_preferences,
}


def make_view(source: Image.Image, view: str, language: str, revision: int) -> Image.Image:
    crop = source.crop(SCREEN_CROPS[view])
    image = crop.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS).convert("L")
    if language == "zh":
        if view == "about":
            localize_about(image, revision)
        else:
            LOCALIZERS[view](image)
    elif view == "status":
        # Strip sample values from the accepted source.  The C runtime writes
        # live WB55 values into these fixed source-layout cells.
        draw = ImageDraw.Draw(image)
        for row in range(4):
            y = 41 + row * 39
            clear(draw, (140, y, 199, y + 19))
    elif view == "phone":
        draw = ImageDraw.Draw(image)
        for row in range(3):
            y = 41 + row * 39
            clear(draw, (130, y, 199, y + 19))
    elif view == "device":
        draw = ImageDraw.Draw(image)
        for row in range(4):
            y = 42 + row * 38
            clear(draw, (136, y, 199, y + 19))
    elif view == "record":
        draw = ImageDraw.Draw(image)
        clear(draw, (164, 140, 190, 156))
        text(draw, (169, 142), "--", size=9)
    elif view == "about":
        draw = ImageDraw.Draw(image)
        clear(draw, (157, 80, 199, 99))
        text(draw, (159, 82), f"rev {revision}", size=8)
    return image.point(lambda pixel: 0 if pixel < 176 else 255, mode="1")


def write_p4(path: pathlib.Path, image: Image.Image) -> None:
    payload = bytearray()
    pixels = image.convert("1").load()
    for y in range(HEIGHT):
        for byte_x in range(WIDTH // 8):
            value = 0
            for bit in range(8):
                if pixels[byte_x * 8 + bit, y] == 0:
                    value |= 0x80 >> bit
            payload.append(value)
    path.write_bytes(f"P4\n{WIDTH} {HEIGHT}\n".encode("ascii") + payload)


def output_name(view: str, language: str) -> str:
    return f"menu_{view}_{language}_1_54in.pbm"


def legacy_home_frames(output_dir: pathlib.Path) -> list[str]:
    retired: list[str] = []
    pattern = re.compile(r"menu_home[1-9][0-9]*_(?:en|zh)_1_54in\.pbm$")
    for path in output_dir.iterdir():
        if path.is_file() and pattern.fullmatch(path.name):
            retired.append(path.name)
    return sorted(retired)


def update_manifest(path: pathlib.Path, revision: int) -> None:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    source_prefix = "../../../../docs/validation/epaper/"
    retained = [clip for clip in manifest["clips"]
                if not str(clip.get("name", "")).startswith("menu.")]
    menu_clips: list[dict[str, object]] = []
    for language in ("en", "zh"):
        for view in VIEWS:
            menu_clips.append({
                "name": f"menu.{view}.{language}",
                "loop_start": 0,
                "loop_end": 1,
                "frames": [{
                    "source": source_prefix + output_name(view, language),
                    "duration_ms": 1000,
                }],
            })
    manifest["clips"] = retained + menu_clips
    manifest["revision"] = revision
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_preview(preview_dir: pathlib.Path, language: str,
                  frames: dict[str, Image.Image]) -> pathlib.Path:
    preview_dir.mkdir(parents=True, exist_ok=True)
    cell = 240
    sheet = Image.new("1", (cell * 4, cell * 2), 1)
    draw = ImageDraw.Draw(sheet)
    for index, view in enumerate(VIEWS):
        x = (index % 4) * cell
        y = (index // 4) * cell
        sheet.paste(frames[view].resize((200, 200), Image.Resampling.NEAREST), (x + 20, y + 28))
        draw.text((x + 8, y + 8), view.upper(), fill=0)
    path = preview_dir / f"menu-v3-{language}-preview.png"
    sheet.save(path)
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    parser.add_argument("--manifest", type=pathlib.Path)
    parser.add_argument("--asset-revision", type=int, default=ASSET_REVISION)
    parser.add_argument("--source", type=pathlib.Path, default=SOURCE)
    parser.add_argument("--preview-dir", type=pathlib.Path)
    parser.add_argument("--report", type=pathlib.Path)
    args = parser.parse_args()

    source = args.source.resolve()
    if sha256(source) != SOURCE_SHA256:
        raise ValueError("menu-v3 source hash differs from the owner-accepted reference")
    with Image.open(source) as opened:
        reference = opened.convert("L")
    if reference.size != SOURCE_SIZE:
        raise ValueError(f"menu-v3 source must be {SOURCE_SIZE}, found {reference.size}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    retired = legacy_home_frames(args.output_dir)
    outputs: list[dict[str, object]] = []
    previews: list[str] = []
    for language in ("en", "zh"):
        frames: dict[str, Image.Image] = {}
        for view in VIEWS:
            frame = make_view(reference, view, language, args.asset_revision)
            target = args.output_dir / output_name(view, language)
            write_p4(target, frame)
            frames[view] = frame
            outputs.append({
                "view": view,
                "language": language,
                "path": str(target.resolve().relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256(target),
            })
        if args.preview_dir is not None:
            preview = write_preview(args.preview_dir, language, frames)
            previews.append(str(preview.resolve().relative_to(ROOT)).replace("\\", "/"))
    if args.manifest is not None:
        update_manifest(args.manifest, args.asset_revision)
    if args.report is not None:
        report = {
            "schema_id": "companion.screen.menu_v3_import.v1",
            "status": "PASS_STATIC_IMPORT_PENDING_HARDWARE",
            "source": str(source.relative_to(ROOT)).replace("\\", "/"),
            "source_sha256": SOURCE_SHA256,
            "source_size": list(SOURCE_SIZE),
            "crop_boxes": {name: list(box) for name, box in SCREEN_CROPS.items()},
            "asset_revision": args.asset_revision,
            "legacy_home_frames_not_referenced": retired,
            "outputs": outputs,
            "previews": previews,
        }
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Imported menu-v3 {args.asset_revision}: {len(outputs)} external-Flash PBM resources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
