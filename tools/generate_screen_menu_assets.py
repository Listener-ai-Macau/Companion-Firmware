#!/usr/bin/env python3
"""Generate separate Chinese and English 200x200 Companion menu PBM assets."""

from __future__ import annotations

import argparse
import json
import pathlib

from PIL import Image, ImageDraw, ImageFont


WIDTH = 200
HEIGHT = 200
SCROLL_QUANTUM_PX = 2
SCROLL_MAX_PX = 84
SCROLL_FRAME_COUNT = (SCROLL_MAX_PX + SCROLL_QUANTUM_PX - 1) // SCROLL_QUANTUM_PX + 1
HEADER_HEIGHT = 30
HOME_CONTENT_TOP = 38
HOME_SCROLLBAR_TOP = HOME_CONTENT_TOP + 1
HOME_SCROLLBAR_BOTTOM = HEIGHT - 5
HOME_SCROLLBAR_THUMB_HEIGHT = 106
HOME_SCROLLBAR_TRAVEL = HOME_SCROLLBAR_BOTTOM - HOME_SCROLLBAR_TOP - HOME_SCROLLBAR_THUMB_HEIGHT + 1
HOME_PET_PANEL_HEIGHT = 48
HOME_ITEM_STEP = 34
VIEWS = ("record", "status", "phone", "device", "preferences", "about")

HOME_ITEMS = (
    ("record", "记录", "RECORD"),
    ("status", "状态", "STATUS"),
    ("phone", "手机", "PHONE"),
    ("device", "设备", "DEVICE"),
    ("preferences", "偏好", "PREFERENCES"),
    ("about", "关于", "ABOUT"),
)

MENU_STYLE = {
    "name": "genref_sheet_12_inner_faces_v5",
    "inner_face_only": True,
    "header_pet_chip": (8, 5, 35, 24, 6),
    "home_card": (8, 2, 188, 38, 8),
    "home_key_spark": (151, 14),
    "detail_badge_x": 84,
}


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
    raise FileNotFoundError("No Microsoft YaHei, SimHei, or Noto CJK font was found")


class MenuPainter:
    def __init__(self, language: str, asset_revision: int) -> None:
        self.language = language
        self.asset_revision = asset_revision
        self.image = Image.new("1", (WIDTH, HEIGHT), 1)
        self.draw = ImageDraw.Draw(self.image)
        normal = find_font(False)
        bold = find_font(True)
        self.fonts = {
            "header": ImageFont.truetype(str(bold), 16),
            "primary": ImageFont.truetype(str(bold), 15),
            "secondary": ImageFont.truetype(str(normal), 9),
            "body": ImageFont.truetype(str(normal), 13),
            "small": ImageFont.truetype(str(normal), 9),
            "micro": ImageFont.truetype(str(normal), 7),
        }

    def centered(self, text: str, y: int, font: str, fill: int = 0) -> None:
        box = self.draw.textbbox((0, 0), text, font=self.fonts[font])
        x = (WIDTH - (box[2] - box[0])) // 2
        self.draw.text((x, y), text, font=self.fonts[font], fill=fill)

    def header(self, zh: str, en: str, back: bool = True) -> None:
        self.draw.rectangle((0, 0, WIDTH - 1, HEADER_HEIGHT - 1), fill=1)
        self.draw.line((0, HEADER_HEIGHT - 1, WIDTH - 1, HEADER_HEIGHT - 1), fill=0, width=1)
        title = zh if self.language == "zh" else en
        self.centered(title, 5, "header", 0)
        for dot in range(5):
            self.draw.rectangle((158 + dot * 5, 4, 161 + dot * 5, 7), fill=0)
        self.draw.rectangle((181, 17, 194, 23), outline=0, width=1)
        self.draw.rectangle((195, 19, 197, 21), fill=0)
        self.draw.rectangle((183, 19, 188, 21), fill=0)
        if back:
            self.draw.line((19, 8, 10, 15, 19, 22), fill=0, width=2)
            self.draw.line((10, 15, 27, 15), fill=0, width=2)

    def tiny_status(self, y: int = 6) -> None:
        for dot in range(5):
            self.draw.rectangle((161 + dot * 5, y, 164 + dot * 5, y + 3), fill=0)
        self.draw.rectangle((183, y + 13, 195, y + 18), outline=0, width=1)
        self.draw.rectangle((196, y + 15, 197, y + 16), fill=0)
        self.draw.rectangle((185, y + 15, 190, y + 16), fill=0)

    def header_pet_chip(self) -> None:
        x0, y0, x1, y1, radius = MENU_STYLE["header_pet_chip"]
        self.draw.rounded_rectangle((x0, y0, x1, y1), radius=radius, outline=0, width=2)
        self.draw.ellipse((13, 10, 20, 21), fill=0)
        self.draw.ellipse((23, 10, 30, 21), fill=0)
        self.draw.ellipse((15, 12, 17, 15), fill=1)
        self.draw.ellipse((25, 12, 27, 15), fill=1)
        self.draw.line((20, 22, 22, 24, 25, 22), fill=0, width=2)

    def spark(self, x: int, y: int, fill: int = 0) -> None:
        self.draw.line((x, y - 5, x, y + 5), fill=fill, width=1)
        self.draw.line((x - 5, y, x + 5, y), fill=fill, width=1)
        self.draw.line((x - 3, y - 3, x + 3, y + 3), fill=fill, width=1)
        self.draw.line((x + 3, y - 3, x - 3, y + 3), fill=fill, width=1)

    def cat_badge(self, x: int, y: int, mood: str) -> None:
        """Only inner face marks are drawn; the physical shell owns the outline."""
        if not MENU_STYLE["inner_face_only"]:
            raise ValueError("menu style must keep the shell outline out of firmware assets")
        if mood == "listen":
            self.draw.ellipse((x + 5, y + 14, x + 15, y + 30), fill=0)
            self.draw.ellipse((x + 21, y + 14, x + 31, y + 30), fill=0)
            self.draw.ellipse((x + 7, y + 16, x + 10, y + 21), fill=1)
            self.draw.ellipse((x + 23, y + 16, x + 26, y + 21), fill=1)
            self.draw.ellipse((x + 17, y + 31, x + 20, y + 34), fill=0)
            self.spark(x + 32, y + 18, 0)
        elif mood == "curious":
            self.draw.arc((x + 7, y + 14, x + 19, y + 20), 195, 345, fill=0, width=2)
            self.draw.arc((x + 20, y + 13, x + 32, y + 19), 195, 345, fill=0, width=2)
            self.draw.ellipse((x + 6, y + 18, x + 16, y + 34), fill=0)
            self.draw.ellipse((x + 22, y + 18, x + 32, y + 34), fill=0)
            self.draw.ellipse((x + 8, y + 20, x + 11, y + 25), fill=1)
            self.draw.ellipse((x + 24, y + 20, x + 27, y + 25), fill=1)
            self.draw.ellipse((x + 18, y + 31, x + 21, y + 34), fill=0)
        elif mood == "content":
            self.draw.arc((x + 5, y + 15, x + 17, y + 25), 190, 350, fill=0, width=3)
            self.draw.arc((x + 20, y + 15, x + 32, y + 25), 190, 350, fill=0, width=3)
            self.draw.line((x + 16, y + 27, x + 12, y + 30), fill=0, width=2)
            self.draw.line((x + 16, y + 27, x + 20, y + 30), fill=0, width=2)
        else:
            self.draw.ellipse((x + 8, y + 13, x + 14, y + 23), fill=0)
            self.draw.ellipse((x + 22, y + 13, x + 28, y + 23), fill=0)
            self.draw.line((x + 14, y + 27, x + 18, y + 27), fill=0, width=2)
        self.draw.ellipse((x + 1, y + 28, x + 5, y + 31), fill=0)
        self.draw.ellipse((x + 33, y + 28, x + 37, y + 31), fill=0)

    def bilingual_label(self, xy: tuple[int, int], zh: str, en: str,
                        fill: int = 0) -> None:
        x, y = xy
        if self.language == "zh":
            self.draw.text((x, y + 5), zh, font=self.fonts["primary"], fill=fill)
        else:
            self.draw.text((x, y + 7), en, font=self.fonts["body"], fill=fill)

    def icon(self, kind: str, x: int, y: int, fill: int = 0) -> None:
        if kind == "record":
            self.draw.rounded_rectangle((x + 8, y, x + 20, y + 21), radius=5, outline=fill, width=2)
            self.draw.arc((x + 3, y + 7, x + 25, y + 27), 0, 180, fill=fill, width=2)
            self.draw.line((x + 14, y + 25, x + 14, y + 30), fill=fill, width=2)
            self.draw.line((x + 8, y + 30, x + 20, y + 30), fill=fill, width=2)
        elif kind == "status":
            self.draw.rectangle((x + 2, y + 2, x + 28, y + 28), outline=fill, width=2)
            self.draw.line((x + 7, y + 23, x + 7, y + 17), fill=fill, width=3)
            self.draw.line((x + 14, y + 23, x + 14, y + 11), fill=fill, width=3)
            self.draw.line((x + 21, y + 23, x + 21, y + 7), fill=fill, width=3)
        elif kind == "preferences":
            self.draw.ellipse((x + 4, y + 4, x + 26, y + 26), outline=fill, width=3)
            self.draw.ellipse((x + 11, y + 11, x + 19, y + 19), outline=fill, width=2)
            self.draw.line((x + 15, y, x + 15, y + 5), fill=fill, width=3)
            self.draw.line((x + 15, y + 25, x + 15, y + 30), fill=fill, width=3)
            self.draw.line((x, y + 15, x + 5, y + 15), fill=fill, width=3)
            self.draw.line((x + 25, y + 15, x + 30, y + 15), fill=fill, width=3)
        elif kind == "phone":
            self.draw.arc((x + 3, y + 3, x + 27, y + 27), 205, 350,
                          fill=fill, width=3)
            self.draw.polygon(((x + 25, y + 4), (x + 29, y + 11),
                               (x + 21, y + 11)), fill=fill)
            self.draw.arc((x + 3, y + 3, x + 27, y + 27), 25, 170,
                          fill=fill, width=3)
            self.draw.polygon(((x + 5, y + 26), (x + 1, y + 19),
                               (x + 9, y + 19)), fill=fill)
        elif kind == "device":
            self.draw.rounded_rectangle((x + 5, y + 1, x + 25, y + 29),
                                        radius=3, outline=fill, width=2)
            self.draw.rectangle((x + 8, y + 5, x + 22, y + 22),
                                outline=fill, width=2)
            self.draw.ellipse((x + 14, y + 25, x + 16, y + 27), fill=fill)
        elif kind == "about":
            self.draw.ellipse((x + 2, y + 2, x + 28, y + 28),
                              outline=fill, width=2)
            self.draw.ellipse((x + 13, y + 7, x + 17, y + 11), fill=fill)
            self.draw.rectangle((x + 13, y + 14, x + 17, y + 23), fill=fill)
        else:
            raise ValueError(f"unknown menu icon: {kind}")

    def detail_shell(self, mood: str, y: int = 82, badge_y: int = 41) -> None:
        self.cat_badge(MENU_STYLE["detail_badge_x"], badge_y, mood)
        self.draw.rounded_rectangle((14, y, 186, 178), radius=10, outline=0, width=2)
        self.draw.line((29, y + 13, 171, y + 13), fill=0, width=1)
        self.draw.line((29, y + 72, 171, y + 72), fill=0, width=1)
        self.spark(24, y + 12, 0)
        self.spark(176, y + 12, 0)

    def pill(self, box: tuple[int, int, int, int], text: str, selected: bool = False) -> None:
        x0, y0, x1, y1 = box
        self.draw.rounded_rectangle(box, radius=7, outline=0, fill=0 if selected else 1, width=2)
        text_box = self.draw.textbbox((0, 0), text, font=self.fonts["small"])
        self.draw.text(
            (x0 + (x1 - x0 - (text_box[2] - text_box[0])) // 2, y0 + 5),
            text,
            font=self.fonts["small"],
            fill=1 if selected else 0,
        )

    def progress(self, x: int, y: int, width: int, value: int) -> None:
        self.draw.rounded_rectangle((x, y, x + width, y + 8), radius=4, outline=0, width=1)
        fill_width = max(4, width * value // 100)
        self.draw.rounded_rectangle((x + 2, y + 2, x + fill_width - 2, y + 6), radius=2, fill=0)

    def menu_dots(self, y: int, active: int) -> None:
        for index in range(4):
            x = 84 + index * 9
            if index == active:
                self.draw.rounded_rectangle((x, y, x + 12, y + 4), radius=2, fill=0)
            else:
                self.draw.ellipse((x + 4, y, x + 8, y + 4), outline=0, fill=1)

    def mini_pet_panel(self, y: int, offset: int) -> None:
        self.draw.rounded_rectangle((9, y, 191, y + 46), radius=10, outline=0, width=2)
        self.draw.ellipse((58, y + 10, 75, y + 34), fill=0)
        self.draw.ellipse((90, y + 10, 107, y + 34), fill=0)
        self.draw.ellipse((62, y + 13, 67, y + 21), fill=1)
        self.draw.ellipse((94, y + 13, 99, y + 21), fill=1)
        if offset < 30:
            self.draw.line((78, y + 35, 83, y + 40, 90, y + 35), fill=0, width=2)
        else:
            self.draw.arc((76, y + 31, 91, y + 41), 15, 165, fill=0, width=2)
        self.draw.ellipse((48, y + 31, 53, y + 35), fill=0)
        self.draw.ellipse((113, y + 31, 118, y + 35), fill=0)
        label = "摸摸我 3s 进设置" if self.language == "zh" else "HOLD 3S FOR MENU"
        self.draw.text((121, y + 9), label, font=self.fonts["micro"], fill=0)
        for dot in range(4):
            self.draw.rectangle((123 + dot * 8, y + 25, 128 + dot * 8, y + 28), fill=0)
        self.spark(32, y + 16, 0)
        self.spark(173, y + 31, 0)

    def home(self, scroll_frame: int) -> None:
        offset = min(scroll_frame * SCROLL_QUANTUM_PX, SCROLL_MAX_PX)
        content = Image.new("1", (WIDTH, HEIGHT), 1)
        original_image = self.image
        original_draw = self.draw
        self.image = content
        self.draw = ImageDraw.Draw(content)
        self.mini_pet_panel(39 - offset // 4, offset)
        for item, (icon, zh, en) in enumerate(HOME_ITEMS):
            y = HOME_CONTENT_TOP + HOME_PET_PANEL_HEIGHT + item * HOME_ITEM_STEP - offset
            card_x0, card_y0, card_x1, card_y1, card_radius = MENU_STYLE["home_card"]
            selected = item == min(len(HOME_ITEMS) - 1, max(0, round(offset / 34)))
            self.draw.rounded_rectangle((card_x0, y + card_y0, card_x1, y + card_y1),
                                        radius=card_radius, outline=0,
                                        fill=0 if selected else 1, width=2)
            self.draw.rounded_rectangle((14, y + 7, 45, y + 32), radius=6,
                                        outline=1 if selected else 0,
                                        fill=1 if selected else 1, width=2)
            self.icon(icon, 18, y + 5, 0)
            item_fill = 1 if selected else 0
            self.bilingual_label((58, y + 1), zh, en, item_fill)
            for dot in range(6):
                self.draw.rectangle((58 + dot * 6, y + 27, 61 + dot * 6, y + 29),
                                    fill=item_fill)
            if icon in ("record", "preferences"):
                spark_x, spark_y = MENU_STYLE["home_key_spark"]
                self.spark(spark_x, y + spark_y, item_fill)
            self.draw.line((175, y + 12, 183, y + 19, 175, y + 26),
                           fill=item_fill, width=2)
            if selected:
                self.draw.ellipse((48, y + 15, 52, y + 19), fill=1)
                self.draw.ellipse((165, y + 16, 169, y + 20), fill=1)
                self.draw.line((21, y + 34, 38, y + 34), fill=1, width=2)
                self.draw.line((153, y + 34, 170, y + 34), fill=1, width=2)
        self.image = original_image
        self.draw = original_draw
        self.image.paste(content.crop((0, HOME_CONTENT_TOP, WIDTH, HEIGHT)),
                         (0, HOME_CONTENT_TOP))
        thumb_y = HOME_SCROLLBAR_TOP + offset * HOME_SCROLLBAR_TRAVEL // SCROLL_MAX_PX
        self.draw.rectangle((196, HOME_CONTENT_TOP, 198, HOME_SCROLLBAR_BOTTOM),
                            outline=0, fill=1)
        self.draw.rectangle((196, thumb_y, 198,
                             thumb_y + HOME_SCROLLBAR_THUMB_HEIGHT - 1), fill=0)
        self.header("伴侣", "COMPANION", back=False)
        self.header_pet_chip()
        self.draw.rectangle((0, HEADER_HEIGHT, WIDTH - 1, HOME_CONTENT_TOP - 1),
                            fill=1)
        self.menu_dots(188, 0)

    def record(self) -> None:
        self.header("记录", "RECORD")
        self.detail_shell("listen", badge_y=38)
        self.centered("轻点开始" if self.language == "zh" else "TAP TO REC", 87, "small")
        self.pill((31, 104, 79, 122), "MIC", True)
        self.pill((121, 104, 169, 122), "QSPI", False)
        for index, height in enumerate((8, 18, 32, 23, 14, 27)):
            x = 61 + index * 13
            self.draw.rounded_rectangle((x, 150 - height, x + 7, 150), radius=2, fill=0)
        self.draw.ellipse((39, 132, 51, 144), fill=0)
        self.progress(52, 159, 96, 68)
        self.menu_dots(190, 0)

    def status(self) -> None:
        self.header("状态", "STATUS")
        self.detail_shell("content", badge_y=39)
        rows = ((92, "屏幕", "DISPLAY", 83), (112, "触摸", "TOUCH", 90),
                (132, "蓝牙", "BLE", 78), (152, "录音", "RECORD", 56))
        for y, zh, en, value in rows:
            label = zh if self.language == "zh" else en
            self.draw.text((28, y), label, font=self.fonts["small"], fill=0)
            self.progress(88, y + 4, 70, value)
            self.draw.ellipse((166, y + 3, 172, y + 9), fill=0)
        self.menu_dots(190, 1)

    def phone(self) -> None:
        self.header("手机", "PHONE")
        self.detail_shell("curious", badge_y=45)
        self.centered("蓝牙连接" if self.language == "zh" else "BLE LINK", 89, "small")
        self.draw.arc((50, 113, 150, 157), 205, 335, fill=0, width=4)
        self.draw.polygon(((146, 112), (158, 120), (143, 126)), fill=0)
        for index in range(5):
            self.draw.rectangle((61 + index * 15, 143, 70 + index * 15, 149), fill=0)
        self.draw.ellipse((138, 132, 150, 144), fill=0)
        self.pill((48, 157, 95, 175), "BLE", True)
        self.pill((104, 157, 151, 175), "APP", False)
        self.menu_dots(190, 2)

    def device(self) -> None:
        self.header("设备", "DEVICE")
        self.detail_shell("content", badge_y=43)
        self.draw.rounded_rectangle((57, 98, 143, 146), radius=8, outline=0, width=3)
        self.draw.rectangle((68, 109, 132, 134), outline=0, width=2)
        self.draw.ellipse((97, 139, 103, 144), fill=0)
        lines = ("200 x 200", "电子纸触摸") if self.language == "zh" else (
            "200 x 200", "E-PAPER")
        self.centered(lines[0], 151, "body")
        self.centered(lines[1], 168, "small")
        self.menu_dots(190, 3)

    def preferences(self) -> None:
        self.header("偏好", "PREFERENCES")
        primary = "语言" if self.language == "zh" else "LANGUAGE"
        self.detail_shell("curious", y=78, badge_y=35)
        self.draw.text((26, 89), primary, font=self.fonts["small"], fill=0)
        self.draw.rounded_rectangle((100, 84, 178, 116), radius=7, outline=0, width=2)
        self.draw.line((139, 84, 139, 116), fill=0, width=2)
        if self.language == "en":
            self.draw.rectangle((102, 86, 137, 114), fill=0)
        else:
            self.draw.rectangle((141, 86, 176, 114), fill=0)
        self.draw.text((111, 93), "EN", font=self.fonts["small"], fill=1 if self.language == "en" else 0)
        self.draw.text((147, 91), "中文", font=self.fonts["small"], fill=1 if self.language == "zh" else 0)
        rows = ((125, "屏幕", "DISPLAY", 68),
                (145, "刷新", "REFRESH", 54),
                (165, "资源", "ASSETS", 85))
        for y, zh, en, value in rows:
            label = zh if self.language == "zh" else en
            self.draw.text((28, y), label, font=self.fonts["small"], fill=0)
            self.progress(86, y + 4, 72, value)
        self.menu_dots(190, 0)

    def info_page(self, zh_title: str, en_title: str,
                  zh_lines: tuple[str, ...], en_lines: tuple[str, ...]) -> None:
        self.header(zh_title, en_title)
        lines = zh_lines if self.language == "zh" else en_lines
        y = 55
        for line in lines:
            self.centered(line, y, "primary" if y == 55 else "body")
            y += 39

    def about(self) -> None:
        self.header("关于", "ABOUT")
        self.detail_shell("content", badge_y=45)
        self.spark(53, 109, 0)
        self.spark(148, 109, 0)
        self.centered("COMPANION", 104, "body")
        self.centered(f"REV {self.asset_revision}", 133, "small")
        self.progress(53, 153, 94, 72)
        self.centered("WB55 / WBA", 169, "small")
        self.menu_dots(190, 1)


def write_p4(path: pathlib.Path, image: Image.Image) -> None:
    payload = bytearray()
    pixels = image.load()
    for y in range(HEIGHT):
        for byte_x in range(WIDTH // 8):
            value = 0
            for bit in range(8):
                if pixels[byte_x * 8 + bit, y] == 0:
                    value |= 0x80 >> bit
            payload.append(value)
    path.write_bytes(f"P4\n{WIDTH} {HEIGHT}\n".encode("ascii") + payload)


def home_frame_name(language: str, frame: int) -> str:
    suffix = "" if frame == 0 else str(frame)
    return f"menu_home{suffix}_{language}_1_54in.pbm"


def update_manifest(path: pathlib.Path, revision: int) -> None:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    source_prefix = "../../../../docs/validation/epaper/"
    retained_clips = [
        clip for clip in manifest["clips"]
        if not str(clip.get("name", "")).startswith("menu.")
    ]
    menu_clips: list[dict[str, object]] = []

    for language in ("en", "zh"):
        menu_clips.append({
            "name": f"menu.home.{language}",
            "loop_start": 0,
            "loop_end": SCROLL_FRAME_COUNT,
            "frames": [
                {
                    "source": source_prefix + home_frame_name(language, frame),
                    "duration_ms": 1000,
                }
                for frame in range(SCROLL_FRAME_COUNT)
            ],
        })
        for view in VIEWS:
            menu_clips.append({
                "name": f"menu.{view}.{language}",
                "loop_start": 0,
                "loop_end": 1,
                "frames": [{
                    "source": source_prefix + f"menu_{view}_{language}_1_54in.pbm",
                    "duration_ms": 1000,
                }],
            })

    manifest["clips"] = retained_clips + menu_clips
    manifest["revision"] = revision
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    parser.add_argument("--asset-revision", type=int, default=32)
    parser.add_argument("--manifest", type=pathlib.Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for language in ("en", "zh"):
        for selection in range(SCROLL_FRAME_COUNT):
            painter = MenuPainter(language, args.asset_revision)
            painter.home(selection)
            output = args.output_dir / home_frame_name(language, selection)
            write_p4(output, painter.image)
            print(output)
        for view in VIEWS:
            painter = MenuPainter(language, args.asset_revision)
            getattr(painter, view)()
            output = args.output_dir / f"menu_{view}_{language}_1_54in.pbm"
            write_p4(output, painter.image)
            print(output)
    if args.manifest is not None:
        update_manifest(args.manifest, args.asset_revision)
        print(args.manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
