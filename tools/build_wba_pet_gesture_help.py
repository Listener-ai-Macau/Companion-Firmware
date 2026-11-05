"""Build compact native gesture instructions; no pet artwork or resource-bank change."""
from pathlib import Path
import argparse
import hashlib
import json

from PIL import Image, ImageDraw, ImageFont
from build_wba_pet_help import packed


# Alternate rows describe the saved settings, not a gesture that is disabled.
LABELS = (
    ("FOLLOW", "Hold + move: follow", "按住移动 · 看手指", "按住移動 · 看手指"),
    ("TOUCH", "Tap my face: respond", "轻摸脸颊 · 回应", "輕摸臉頰 · 回應"),
    ("MENU", "Hold 3s menu; swipe right back", "长按3秒菜单，右滑返回", "長按3秒選單，右滑返回"),
    ("CORNER_RECORD", "2 taps lower left: record / stop", "左下双击：开录 / 停录", "左下雙擊：開錄 / 停錄"),
    ("EDGE_RECORD", "Lower left → record; 2 taps stop", "左下右滑开录，双击停录", "左下右滑開錄，雙擊停錄"),
    ("QUICK", "Top right, pull down: quick", "右上往下拉 · 快捷", "右上往下拉 · 快捷"),
    ("SHAKE", "Gently shake: play", "轻轻晃动 · 逗我", "輕輕晃動 · 逗我"),
)
WIDTH, HEIGHT, STRIDE = 168, 13, 21


def build(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    compact, raw_data = bytearray(), bytearray()
    compact_offsets, raw_offsets, glyphs, sources = [], [], [], {}
    unique, raw_unique = {}, {}
    for locale in range(3):
        packed_row, raw_row = [], []
        font_path = Path("C:/Windows/Fonts") / ("segoeui.ttf" if locale == 0 else "msyh.ttc")
        sources[str(font_path)] = hashlib.sha256(font_path.read_bytes()).hexdigest()
        font = ImageFont.truetype(str(font_path), 12)
        for name, *texts in LABELS:
            text = texts[locale]
            raster = Image.new("L", (WIDTH, HEIGHT), 255)
            draw = ImageDraw.Draw(raster)
            left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
            if right-left > WIDTH or bottom-top > HEIGHT:
                raise ValueError("Gesture instruction exceeds native line: " + text)
            draw.text((-left, (HEIGHT-bottom+top)//2-top), text, font=font, fill=0)
            raw = raster.point(lambda v: 255 if v >= 160 else 0).convert("1").tobytes()
            encoded = packed(raw)
            if encoded not in unique:
                unique[encoded] = len(compact)
                compact.extend(encoded)
            if raw not in raw_unique:
                raw_unique[raw] = len(raw_data)
                raw_data.extend(raw)
            packed_row.append(unique[encoded])
            raw_row.append(raw_unique[raw])
            glyphs.append(dict(locale=locale, name=name, text=text,
                               inkWidth=right-left, inkHeight=bottom-top))
        compact_offsets.append(packed_row)
        raw_offsets.append(raw_row)
    count = len(LABELS)
    header = ["/* Native 12px menu guidance only; original pet pixels are unchanged. */",
              "#ifndef COMPANION_PET_GESTURE_HELP_LABELS_H",
              "#define COMPANION_PET_GESTURE_HELP_LABELS_H", "#include <stdint.h>",
              f"#define COMP_PET_GESTURE_HELP_COUNT {count}u",
              f"#define COMP_PET_GESTURE_HELP_WIDTH {WIDTH}u",
              f"#define COMP_PET_GESTURE_HELP_HEIGHT {HEIGHT}u",
              f"#define COMP_PET_GESTURE_HELP_STRIDE {STRIDE}u"]
    header += [f"#define COMP_PET_GESTURE_HELP_{row[0]} {i}u" for i, row in enumerate(LABELS)]
    for condition, data, offsets in (("#if COMPANION_WBA_RECORDING_UI_PACKED", compact, compact_offsets),
                                      ("#else", raw_data, raw_offsets)):
        header += [condition, "static const uint8_t comp_pet_gesture_help_bits[] = {"]
        header += [",".join(f"0x{v:02x}" for v in data[i:i+24])+"," for i in range(0, len(data), 24)]
        header += ["};", f"static const uint16_t comp_pet_gesture_help_offsets[3][{count}] = {{"]
        header += ["{"+",".join(map(str, row))+"}," for row in offsets]
        header += ["};"]
    header += ["#endif", "#endif", ""]
    target = output / "companion_pet_gesture_help_labels.h"
    target.write_text("\n".join(header), encoding="ascii")
    return dict(packedBytes=len(compact), rawBytes=len(raw_data), rows=glyphs,
                fontSources=sources, headerSha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                faceChanged=False, resourceBankChanged=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parents[1] / "app/companion_pendant/runtime/generated")
    args = parser.parse_args()
    print(json.dumps(build(args.output), ensure_ascii=False))
