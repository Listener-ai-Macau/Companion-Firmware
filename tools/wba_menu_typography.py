"""Native 1-bit menu typography helpers for the 200 x 200 WBA display.

Chinese text uses Microsoft YaHei's native raster at the reviewed
11/12/14/15/24 pixel sizes. Latin-only text uses Segoe UI. These are Windows
system glyphs selected for the WBA menu; they are not hand-edited artwork.

Keep layout hierarchy primarily in the reviewed sizes: 14 px for child labels,
12 px for subordinate current values, 15 px for categories/titles,
11 px for position indicators, and 24 px for confirmation counts. Other positive sizes remain
accepted so existing generators can migrate without an artificial scale.
"""

from functools import lru_cache
import math
from pathlib import Path

from PIL import ImageFont


_FONT_DIR = Path("C:/Windows/Fonts")
_CJK_REGULAR = _FONT_DIR / "msyh.ttc"
_CJK_BOLD = _FONT_DIR / "msyhbd.ttc"
_LATIN_REGULAR = _FONT_DIR / "segoeui.ttf"
_LATIN_BOLD = _FONT_DIR / "segoeuib.ttf"
_SUBMENU_CJK = _FONT_DIR / "simhei.ttf"

REVIEWED_SIZES = (11, 12, 14, 15, 16, 24)


def _contains_cjk(text):
    return any(
        0x2E80 <= ord(char) <= 0x9FFF or 0xF900 <= ord(char) <= 0xFAFF
        for char in str(text)
    )


class _MenuFont:
    """Pillow-compatible font that selects a face for the complete string.

    Mixed Chinese/value strings intentionally use the CJK face for one
    baseline and stable full-width cells.  Pure Latin and numeric strings use
    Segoe UI.  Pillow calls the delegated methods from text, textbbox, and
    textlength, which keeps measurement and rasterization on the same face.
    """

    def __init__(self, size, bold, cjk_path=None):
        cjk_path = cjk_path or (_CJK_BOLD if bold else _CJK_REGULAR)
        latin_path = _LATIN_BOLD if bold else _LATIN_REGULAR
        for path in (cjk_path, latin_path):
            if not path.exists():
                raise FileNotFoundError("Required WBA menu font is missing: " + str(path))
        self.size = size
        self._cjk = ImageFont.truetype(str(cjk_path), size)
        self._latin = ImageFont.truetype(str(latin_path), size)

    def _face(self, text):
        return self._cjk if _contains_cjk(text) else self._latin

    def getbbox(self, text, *args, **kwargs):
        return self._face(text).getbbox(text, *args, **kwargs)

    def getlength(self, text, *args, **kwargs):
        return self._face(text).getlength(text, *args, **kwargs)

    def getmask(self, text, *args, **kwargs):
        return self._face(text).getmask(text, *args, **kwargs)

    def getmask2(self, text, *args, **kwargs):
        return self._face(text).getmask2(text, *args, **kwargs)

    def getmetrics(self):
        # Return a conservative common line box for callers that lay out a
        # locale before they know which script a value will use.
        ca, cd = self._cjk.getmetrics()
        la, ld = self._latin.getmetrics()
        return max(ca, la), max(cd, ld)


@lru_cache(maxsize=None)
def font(size, bold=False):
    """Return a Pillow-compatible CJK/Latin menu font.

    YaHei provides full native CJK strokes across the three locales.
    ``bold=True`` is explicit opt-in to YaHei/Segoe UI Bold for a title,
    category, action or value; subordinate field labels remain regular.
    """

    size = int(size)
    if size <= 0:
        raise ValueError("Menu font size must be positive")
    return _MenuFont(size, bool(bold))


@lru_cache(maxsize=None)
def submenu_font(size, bold=False):
    """Native monochrome SimHei for child pages; preserve accepted root art."""
    return _MenuFont(int(size), bool(bold), _SUBMENU_CJK)


def submenu_value_size(text):
    return 14 if _contains_cjk(str(text)) else 12


def text_width(text, size, bold=False, *, submenu=False):
    """Return the integer pixel advance required for ``text``."""

    text = str(text)
    if not text:
        return 0
    selected = (submenu_font if submenu else font)(size, bold)
    box = selected.getbbox(text)
    ink_width = box[2] - min(0, box[0])
    return max(int(math.ceil(selected.getlength(text))), int(ink_width))


def draw_text(draw, xy, text, size=12, bold=False, width=178, fill=0, *, submenu=False):
    """Draw native 1-bit text with ``xy`` denoting the top-left ink pixel.

    The function rejects horizontal overflow instead of silently clipping it.
    It does not antialias, scale, dither, or claim to replace the source system
    glyphs with hand-tuned artwork.
    """

    text = str(text)
    if not text:
        return
    selected = (submenu_font if submenu else font)(size, bold)
    required = text_width(text, size, bold, submenu=submenu)
    if required > int(width):
        raise ValueError(
            f"WBA menu text overflow: {text!r} needs {required}px, limit is {width}px"
        )
    box = selected.getbbox(text)
    if round(xy[1]) + box[3] - box[1] > 200:
        raise ValueError(f"WBA menu text clipped below screen: {text!r}")
    draw.fontmode = "1"
    draw.text(
        (round(xy[0]) - min(0, box[0]), round(xy[1]) - box[1]),
        text,
        font=selected,
        fill=fill,
    )


__all__ = ["REVIEWED_SIZES", "draw_text", "font", "text_width", "submenu_font", "submenu_value_size"]
