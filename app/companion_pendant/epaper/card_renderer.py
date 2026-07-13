#!/usr/bin/env python3
"""No-hardware Companion pendant e-paper card renderer."""

from __future__ import annotations

import hashlib
import math
import pathlib
import textwrap
from dataclasses import asdict, dataclass
from typing import Any, Iterable


CARD_TYPES = {
    "boot",
    "expression",
    "mood",
    "name",
    "event",
    "reminder",
    "recording",
    "sync_complete",
    "low_battery",
    "error",
}
CARD_STATES = {
    "default",
    "idle",
    "listening",
    "thinking",
    "speaking",
    "happy",
    "sleepy",
    "recording",
    "sync_complete",
    "low_battery",
    "error",
}
EXPRESSION_KINDS = {
    "idle",
    "listening",
    "thinking",
    "speaking",
    "happy",
    "sleepy",
    "recording",
    "sync_complete",
    "low_battery",
    "error",
}

EXPRESSION_COPY = {
    "idle": ("Idle", "Soft awake face", "EXPR IDLE"),
    "listening": ("Listening", "Ears open for the wake path", "EXPR LISTEN"),
    "thinking": ("Thinking", "Processing the last prompt", "EXPR THINK"),
    "speaking": ("Speaking", "Response audio is active", "EXPR SPEAK"),
    "happy": ("Happy", "Positive acknowledgement", "EXPR HAPPY"),
    "sleepy": ("Sleepy", "Low attention idle mode", "EXPR SLEEP"),
    "recording": ("Recording", "Capture indicator stays visible", "EXPR REC"),
    "sync_complete": ("Synced", "Transfer finished cleanly", "EXPR SYNC"),
    "low_battery": ("Battery", "Charge soon", "EXPR LOW"),
    "error": ("Error", "Needs user or host recovery", "EXPR ERROR"),
}


@dataclass(frozen=True)
class DisplayVariant:
    key: str
    width: int
    height: int
    label: str


DISPLAY_VARIANTS = {
    "2.13in": DisplayVariant("2.13in", 250, 122, "2.13 inch landscape"),
    "1.54in": DisplayVariant("1.54in", 200, 200, "1.54 inch square"),
}

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
APPROVED_EXPRESSION_ASSET_DIR = REPO_ROOT / "docs" / "validation" / "epaper"


@dataclass(frozen=True)
class CardModel:
    card_id: str
    card_type: str
    state: str
    title: str
    body: str
    footer: str = ""
    locale: str = "en"
    request_id: int = 0
    card_slot: int = 0
    display_flags: int = 0

    def as_manifest(self) -> dict[str, Any]:
        return asdict(self)


FONT_5X7: dict[str, tuple[str, ...]] = {
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    "/": ("00001", "00010", "00100", "01000", "10000", "00000", "00000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "%": ("11001", "11010", "00100", "01000", "10110", "00110", "00000"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "11100"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10011", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
}

BAYER_4X4 = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)


class Framebuffer:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.pixels = bytearray(width * height)

    def set_pixel(self, x: int, y: int, black: bool = True) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.pixels[y * self.width + x] = 1 if black else 0

    def fill_rect(self, x: int, y: int, width: int, height: int, black: bool) -> None:
        for yy in range(y, y + height):
            for xx in range(x, x + width):
                self.set_pixel(xx, yy, black)

    def fill_rect_gray(self, x: int, y: int, width: int, height: int, black_percent: int) -> None:
        percent = max(0, min(100, black_percent))
        for yy in range(y, y + height):
            for xx in range(x, x + width):
                threshold = (BAYER_4X4[yy % 4][xx % 4] + 0.5) * 100 / 16
                self.set_pixel(xx, yy, percent >= threshold)

    def stroke_rect(self, x: int, y: int, width: int, height: int, thickness: int = 1) -> None:
        for i in range(thickness):
            self.fill_rect(x + i, y + i, width - 2 * i, 1, True)
            self.fill_rect(x + i, y + height - 1 - i, width - 2 * i, 1, True)
            self.fill_rect(x + i, y + i, 1, height - 2 * i, True)
            self.fill_rect(x + width - 1 - i, y + i, 1, height - 2 * i, True)

    def fill_circle(self, cx: int, cy: int, radius: int, black: bool = True) -> None:
        r2 = radius * radius
        for yy in range(cy - radius, cy + radius + 1):
            for xx in range(cx - radius, cx + radius + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r2:
                    self.set_pixel(xx, yy, black)

    def stroke_circle(
        self,
        cx: int,
        cy: int,
        radius: int,
        thickness: int = 1,
        black: bool = True,
    ) -> None:
        outer = radius * radius
        inner_radius = max(0, radius - max(1, thickness))
        inner = inner_radius * inner_radius
        for yy in range(cy - radius, cy + radius + 1):
            for xx in range(cx - radius, cx + radius + 1):
                distance = (xx - cx) ** 2 + (yy - cy) ** 2
                if inner <= distance <= outer:
                    self.set_pixel(xx, yy, black)

    def fill_ellipse(self, cx: int, cy: int, rx: int, ry: int, black: bool = True) -> None:
        rx = max(1, rx)
        ry = max(1, ry)
        rx2 = rx * rx
        ry2 = ry * ry
        limit = rx2 * ry2
        for yy in range(cy - ry, cy + ry + 1):
            dy2 = (yy - cy) * (yy - cy)
            for xx in range(cx - rx, cx + rx + 1):
                dx2 = (xx - cx) * (xx - cx)
                if dx2 * ry2 + dy2 * rx2 <= limit:
                    self.set_pixel(xx, yy, black)

    def stroke_ellipse(
        self,
        cx: int,
        cy: int,
        rx: int,
        ry: int,
        thickness: int = 1,
        black: bool = True,
    ) -> None:
        self.fill_ellipse(cx, cy, rx, ry, black)
        inner_rx = max(0, rx - max(1, thickness))
        inner_ry = max(0, ry - max(1, thickness))
        if inner_rx > 0 and inner_ry > 0:
            self.fill_ellipse(cx, cy, inner_rx, inner_ry, not black)

    def draw_arc(
        self,
        cx: int,
        cy: int,
        rx: int,
        ry: int,
        start_degrees: int,
        end_degrees: int,
        thickness: int = 1,
        black: bool = True,
    ) -> None:
        span = max(1, end_degrees - start_degrees)
        steps = max(8, span // 3)
        previous: tuple[int, int] | None = None
        for step in range(steps + 1):
            angle = math.radians(start_degrees + span * step / steps)
            point = (
                int(round(cx + rx * math.cos(angle))),
                int(round(cy + ry * math.sin(angle))),
            )
            if previous is not None:
                self.draw_line(
                    previous[0], previous[1], point[0], point[1], thickness, black
                )
            previous = point

    def draw_line(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        thickness: int = 1,
        black: bool = True,
    ) -> None:
        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        radius = max(0, thickness // 2)
        while True:
            self.fill_rect(
                x0 - radius,
                y0 - radius,
                max(1, thickness),
                max(1, thickness),
                black,
            )
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def to_pbm(self, comment: str) -> bytes:
        header = f"P4\n# {comment}\n{self.width} {self.height}\n".encode("ascii")
        row_bytes = (self.width + 7) // 8
        data = bytearray(row_bytes * self.height)
        for y in range(self.height):
            for x in range(self.width):
                if self.pixels[y * self.width + x]:
                    data[y * row_bytes + (x // 8)] |= 0x80 >> (x % 8)
        return header + bytes(data)


def _glyph_for(char: str) -> tuple[str, ...] | None:
    if char in FONT_5X7:
        return FONT_5X7[char]
    upper = char.upper()
    return FONT_5X7.get(upper)


def draw_glyph(fb: Framebuffer, x: int, y: int, char: str, scale: int = 1) -> int:
    glyph = _glyph_for(char)
    if glyph is None:
        return draw_fallback_glyph(fb, x, y, char, scale)
    for row, bits in enumerate(glyph):
        for col, bit in enumerate(bits):
            if bit == "1":
                fb.fill_rect(x + col * scale, y + row * scale, scale, scale, True)
    return 6 * scale


def draw_fallback_glyph(fb: Framebuffer, x: int, y: int, char: str, scale: int = 1) -> int:
    codepoint = ord(char)
    width = 5 * scale
    height = 7 * scale
    fb.stroke_rect(x, y, width, height, max(1, scale))
    for bit_index in range(6):
        if codepoint & (1 << bit_index):
            px = x + (1 + (bit_index % 3)) * scale
            py = y + (2 + (bit_index // 3) * 2) * scale
            fb.fill_rect(px, py, scale, scale, True)
    return 6 * scale


def draw_text(fb: Framebuffer, x: int, y: int, text: str, scale: int = 1, max_width: int | None = None) -> int:
    cursor = x
    drawn = 0
    for char in text:
        glyph_width = 6 * scale
        if max_width is not None and cursor + glyph_width > x + max_width:
            break
        cursor += draw_glyph(fb, cursor, y, char, scale)
        drawn += 1
    return drawn


def wrap_text(text: str, max_chars: int, max_lines: int) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    lines = textwrap.wrap(
        normalized,
        width=max(1, max_chars),
        break_long_words=True,
        replace_whitespace=True,
    )
    return lines[:max_lines]


def resolve_expression_key(card: CardModel) -> str:
    if card.card_type == "expression" and card.state in EXPRESSION_KINDS:
        return card.state
    if card.state in EXPRESSION_KINDS:
        return card.state
    if card.card_type == "recording":
        return "recording"
    if card.card_type == "sync_complete":
        return "sync_complete"
    if card.card_type == "low_battery":
        return "low_battery"
    if card.card_type == "error":
        return "error"
    if card.card_type == "mood":
        return "happy"
    return "idle"


def _draw_generated_reference_face(
    fb: Framebuffer,
    expression: str,
    x: int,
    y: int,
    size: int,
    phase: str = "base",
) -> None:
    """Draw the shipped one-bit face from the generated sticker-sheet target."""
    expression_key = expression if expression in EXPRESSION_KINDS else "idle"
    cx = x + size // 2
    cy = y + size // 2
    unit = max(2, size // 96)
    stroke = max(3, size // 52)
    fine = max(2, size // 72)

    def sx(percent: int) -> int:
        return x + size * percent // 100

    def sy(percent: int) -> int:
        return y + size * percent // 100

    def direction_from_phase() -> str:
        if phase.startswith("attention_"):
            return phase.removeprefix("attention_")
        if phase.startswith("look_"):
            return phase.removeprefix("look_")
        if phase == "glance_left":
            return "left"
        if phase == "glance_right":
            return "right"
        if phase == "attention":
            return "center"
        return "center"

    def gaze_for(direction: str) -> tuple[int, int]:
        step = size * 6 // 100
        horizontal = -step if "left" in direction else step if "right" in direction else 0
        vertical = -step if "up" in direction else step if "down" in direction else 0
        return horizontal, vertical

    def erase_box(cx0: int, cy0: int, rx: int, ry: int) -> None:
        fb.fill_rect(cx0 - rx, cy0 - ry, rx * 2 + 1, ry * 2 + 1, False)

    def bean_eye(
        eye_x: int,
        eye_y: int,
        rx: int,
        ry: int,
        gaze_x: int = 0,
        gaze_y: int = 0,
        lid: int = 0,
        highlight: bool = True,
    ) -> None:
        fb.fill_ellipse(eye_x, eye_y, rx, ry, True)
        if lid > 0:
            fb.fill_rect(eye_x - rx - 2, eye_y - ry - 2,
                         rx * 2 + 5, min(ry * 2, lid), False)
            fb.draw_arc(eye_x, eye_y - ry + lid,
                        rx, max(5, ry // 3), 188, 352, fine)
        if highlight:
            fb.fill_ellipse(eye_x - rx // 3 + gaze_x,
                            eye_y - ry // 3 + gaze_y,
                            max(5, rx // 3),
                            max(8, ry // 3),
                            False)
            fb.fill_circle(eye_x + rx // 3 + gaze_x,
                           eye_y + ry // 4 + gaze_y,
                           max(2, rx // 8),
                           False)

    def tiny_eye(eye_x: int, eye_y: int, gaze_x: int = 0,
                 gaze_y: int = 0) -> None:
        bean_eye(eye_x, eye_y, size * 7 // 100, size * 14 // 100,
                 gaze_x, gaze_y)

    def closed_eye(eye_x: int, eye_y: int, happy: bool = True) -> None:
        start, end = (198, 342) if happy else (18, 162)
        fb.draw_arc(eye_x, eye_y, size * 13 // 100, size * 5 // 100,
                    start, end, stroke)

    def flat_eye(eye_x: int, eye_y: int, width_percent: int = 18) -> None:
        half = size * width_percent // 200
        fb.draw_line(eye_x - half, eye_y, eye_x + half, eye_y, stroke)
        fb.fill_circle(eye_x - half, eye_y, max(1, stroke // 2), True)
        fb.fill_circle(eye_x + half, eye_y, max(1, stroke // 2), True)

    def brow(eye_x: int, eye_y: int, mood: str, side: int) -> None:
        y0 = eye_y - size * 24 // 100
        half = size * 8 // 100
        if mood == "curious":
            offset = -size * 3 // 100 if side > 0 else size * 1 // 100
            fb.draw_arc(eye_x, y0 + offset, half, size * 3 // 100,
                        205, 335, fine)
        elif mood == "surprise":
            fb.draw_line(eye_x - half, y0 + side * unit,
                         eye_x + half, y0 - side * unit, fine)
        elif mood == "worried":
            fb.draw_line(eye_x - half, y0 - side * unit,
                         eye_x + half, y0 + side * unit, fine)
        elif mood == "sleepy":
            fb.draw_arc(eye_x, y0 + size * 2 // 100, half,
                        size * 3 // 100, 205, 335, fine)
        else:
            fb.draw_arc(eye_x, y0, half, size * 3 // 100, 205, 335, fine)

    def nose_mouth(kind: str = "cat", lift: int = 0, scale: int = 100) -> None:
        nose_y = sy(56) + lift
        mouth_y = sy(62) + lift
        half = size * 10 * scale // 10000
        nose_rx = max(3, size * 2 // 100)
        nose_ry = max(2, size * 1 // 100)
        if kind != "o":
            fb.fill_ellipse(cx, nose_y, nose_rx, nose_ry, True)
            fb.draw_line(cx, nose_y + nose_ry, cx, mouth_y - size * 2 // 100, fine)
        if kind == "smile":
            fb.draw_arc(cx, mouth_y - size * 4 // 100,
                        max(12, half * 2), size * 8 // 100, 18, 162, stroke)
        elif kind == "wide":
            fb.draw_arc(cx, mouth_y - size * 2 // 100,
                        max(15, half * 2), size * 11 // 100, 18, 162, stroke)
            fb.fill_ellipse(cx, mouth_y, max(5, size * 4 // 100),
                            max(3, size * 3 // 100), True)
        elif kind == "o":
            fb.stroke_ellipse(cx, mouth_y - size * 3 // 100,
                              max(7, size * 6 // 100),
                              max(9, size * 8 // 100), stroke)
        elif kind == "flat":
            fb.draw_line(cx - half, mouth_y, cx + half, mouth_y, stroke)
        elif kind == "pout":
            fb.draw_arc(cx, mouth_y + size * 5 // 100,
                        max(10, half * 2), size * 7 // 100, 200, 340, stroke)
        else:
            lcx = cx - half * 5 // 10
            rcx = cx + half * 5 // 10
            fb.draw_arc(lcx, mouth_y - size * 1 // 100,
                        max(6, half), size * 6 // 100, 20, 150, fine)
            fb.draw_arc(rcx, mouth_y - size * 1 // 100,
                        max(6, half), size * 6 // 100, 30, 160, fine)

    def cheeks(strength: int = 2, blush: bool = False) -> None:
        for side, cheek_x in ((-1, sx(24)), (1, sx(76))):
            for index in range(strength):
                yy = sy(66) + index * max(4, unit * 2)
                xx = cheek_x + side * index * max(4, unit * 2)
                if blush:
                    fb.draw_line(xx - unit * 2, yy + unit * 2,
                                 xx + unit * 2, yy - unit * 2, fine)
                else:
                    fb.fill_ellipse(xx, yy, max(3, unit * 2), max(2, unit), True)

    def sticker_accents(mood: str = "soft") -> None:
        """Small inner-face marks from the generated sticker sheet target."""
        dot_r = max(2, unit)
        fb.fill_ellipse(sx(30), sy(58), dot_r, dot_r, True)
        fb.fill_ellipse(sx(70), sy(58), dot_r, dot_r, True)
        if mood == "curious":
            question(sx(56), sy(9))
            fb.fill_circle(sx(49), sy(57), dot_r, True)
        elif mood == "bright":
            sparkle(sx(22), sy(22), 1)
            sparkle(sx(80), sy(18), 1)
        elif mood == "thinking":
            fb.fill_circle(sx(58), sy(57), dot_r, True)
            fb.stroke_circle(sx(74), sy(18), max(3, unit * 3), fine)
        else:
            fb.fill_circle(sx(50), sy(71), max(1, unit), True)

    def sparkle(mark_x: int, mark_y: int, scale: int = 1) -> None:
        short = max(3, unit * 2 * scale)
        long = max(6, unit * 4 * scale)
        fb.draw_line(mark_x - long, mark_y, mark_x + long, mark_y, fine)
        fb.draw_line(mark_x, mark_y - long, mark_x, mark_y + long, fine)
        fb.draw_line(mark_x - short, mark_y - short,
                     mark_x + short, mark_y + short, max(1, fine - 1))
        fb.draw_line(mark_x - short, mark_y + short,
                     mark_x + short, mark_y - short, max(1, fine - 1))

    def heart(mark_x: int, mark_y: int) -> None:
        r = max(3, unit * 2)
        fb.fill_circle(mark_x - r, mark_y, r, True)
        fb.fill_circle(mark_x + r, mark_y, r, True)
        fb.draw_line(mark_x - 2 * r, mark_y + r, mark_x, mark_y + 4 * r, fine)
        fb.draw_line(mark_x + 2 * r, mark_y + r, mark_x, mark_y + 4 * r, fine)

    def question(mark_x: int, mark_y: int) -> None:
        draw_text(fb, mark_x, mark_y, "?", max(2, size // 54))

    def thought_bubble(mark_x: int, mark_y: int) -> None:
        fb.stroke_circle(mark_x + size * 5 // 100, mark_y, size * 6 // 100, fine)
        fb.stroke_circle(mark_x - size * 1 // 100, mark_y + size * 7 // 100,
                         size * 3 // 100, fine)
        fb.stroke_circle(mark_x - size * 6 // 100, mark_y + size * 12 // 100,
                         size * 2 // 100, fine)

    def listening_waves() -> None:
        for side, anchor in ((-1, sx(23)), (1, sx(77))):
            for radius in (size * 5 // 100, size * 9 // 100):
                if side < 0:
                    fb.draw_arc(anchor - radius // 2, sy(45), radius,
                                size * 12 // 100, 90, 270, fine)
                else:
                    fb.draw_arc(anchor + radius // 2, sy(45), radius,
                                size * 12 // 100, 270, 450, fine)

    def motion_marks(direction: str) -> None:
        if "left" in direction:
            side_x, start, end = sx(14), 92, 268
        elif "right" in direction:
            side_x, start, end = sx(86), 272, 448
        elif "up" in direction:
            draw_text(fb, sx(18), sy(16), "!!", max(2, size // 62))
            return
        elif "down" in direction:
            heart(sx(50), sy(18))
            return
        else:
            return
        for index, radius in enumerate((size * 5 // 100, size * 8 // 100)):
            fb.draw_arc(side_x, sy(45) + index * size * 8 // 100,
                        radius, size * 7 // 100, start, end, fine)

    left_eye_x = sx(36)
    right_eye_x = sx(64)
    eye_y = sy(41)
    direction = direction_from_phase()
    gaze_x, gaze_y = gaze_for(direction)
    face_shift_x = gaze_x // 2
    face_shift_y = gaze_y // 3
    if phase == "closed":
        closed_eye(left_eye_x, eye_y)
        closed_eye(right_eye_x, eye_y)
        brow(left_eye_x, eye_y, "sleepy", -1)
        brow(right_eye_x, eye_y, "sleepy", 1)
        nose_mouth("cat", size * 2 // 100)
        cheeks(1)
        return
    if phase == "half":
        bean_eye(left_eye_x, eye_y + size * 3 // 100, size * 12 // 100,
                 size * 18 // 100, 0, 0, size * 16 // 100)
        bean_eye(right_eye_x, eye_y + size * 3 // 100, size * 12 // 100,
                 size * 18 // 100, 0, 0, size * 16 // 100)
        brow(left_eye_x, eye_y, "sleepy", -1)
        brow(right_eye_x, eye_y, "sleepy", 1)
        nose_mouth("cat")
        cheeks(1)
        return

    if expression_key in {"happy", "sync_complete"}:
        lift = -size * (4 if phase == "bright" else 2) // 100
        if phase == "attention":
            bean_eye(left_eye_x, eye_y + lift, size * 9 // 100, size * 15 // 100)
            bean_eye(right_eye_x, eye_y + lift, size * 9 // 100, size * 15 // 100)
        else:
            closed_eye(left_eye_x, eye_y + lift)
            closed_eye(right_eye_x, eye_y + lift)
        brow(left_eye_x, eye_y + lift, "soft", -1)
        brow(right_eye_x, eye_y + lift, "soft", 1)
        nose_mouth("wide" if phase == "bright" else "smile", lift)
        cheeks(3, blush=True)
        sticker_accents("bright")
        sparkle(sx(78), sy(19), 1)
        if expression_key == "sync_complete":
            sparkle(sx(22), sy(24), 1)
        else:
            heart(sx(50), sy(16))
        return

    if expression_key == "sleepy":
        drift = size * (4 if phase == "drift" else 1) // 100
        closed_eye(left_eye_x, eye_y + drift)
        closed_eye(right_eye_x, eye_y + drift)
        brow(left_eye_x, eye_y + drift, "sleepy", -1)
        brow(right_eye_x, eye_y + drift, "sleepy", 1)
        nose_mouth("o" if phase == "yawn" else "cat", drift)
        cheeks(1)
        draw_text(fb, sx(76), sy(13), "Z", max(2, size // 58))
        draw_text(fb, sx(84), sy(7), "Z", max(1, size // 70))
        return

    if expression_key == "thinking":
        bean_eye(left_eye_x - size * 3 // 100, eye_y,
                 size * 10 // 100, size * 18 // 100,
                 -size * 2 // 100 if phase == "inward" else size * 2 // 100)
        bean_eye(right_eye_x + size * 3 // 100, eye_y,
                 size * 10 // 100, size * 18 // 100,
                 size * 2 // 100 if phase == "outward" else -size * 2 // 100)
        brow(left_eye_x, eye_y, "curious", -1)
        brow(right_eye_x, eye_y, "curious", 1)
        nose_mouth("cat", 0, 80)
        thought_bubble(sx(78), sy(22))
        cheeks(1)
        sticker_accents("thinking")
        return

    if expression_key == "speaking":
        closed_eye(left_eye_x, eye_y - size * 2 // 100)
        closed_eye(right_eye_x, eye_y - size * 2 // 100)
        brow(left_eye_x, eye_y, "soft", -1)
        brow(right_eye_x, eye_y, "soft", 1)
        nose_mouth("o" if phase == "open" else "cat" if phase == "soft" else "smile")
        for index, width in enumerate((size * 18 // 100, size * 12 // 100, size * 8 // 100)):
            yy = sy(76) + index * size * 5 // 100
            fb.draw_line(cx - width // 2, yy, cx + width // 2, yy, fine)
        return

    if expression_key == "listening":
        bean_eye(left_eye_x - size * 1 // 100, eye_y,
                 size * 12 // 100, size * 20 // 100, 0,
                 -size * 2 // 100 if phase == "focus" else 0)
        bean_eye(right_eye_x + size * 1 // 100, eye_y,
                 size * 12 // 100, size * 20 // 100, 0,
                 -size * 2 // 100 if phase == "focus" else 0)
        brow(left_eye_x, eye_y, "curious", -1)
        brow(right_eye_x, eye_y, "curious", 1)
        nose_mouth("o")
        listening_waves()
        if phase == "wave":
            for side, anchor in ((-1, sx(18)), (1, sx(82))):
                fb.draw_arc(anchor, sy(45), size * 15 // 100,
                            size * 18 // 100,
                            88 if side < 0 else 272,
                            272 if side < 0 else 448,
                            fine)
        cheeks(1)
        sticker_accents("curious")
        return

    if expression_key == "recording":
        bean_eye(left_eye_x, eye_y, size * 9 // 100, size * 17 // 100, 0, 0,
                 size * (4 if phase == "soft" else 1) // 100)
        bean_eye(right_eye_x, eye_y, size * 9 // 100, size * 17 // 100, 0, 0,
                 size * (4 if phase == "soft" else 1) // 100)
        brow(left_eye_x, eye_y, "soft", -1)
        brow(right_eye_x, eye_y, "soft", 1)
        nose_mouth("o")
        radius = size * (7 if phase == "pulse" else 5) // 100
        fb.fill_circle(sx(18), sy(20), max(4, radius // 2), True)
        fb.stroke_circle(sx(18), sy(20), radius, fine)
        return

    if expression_key == "low_battery":
        flat_eye(left_eye_x, eye_y + size * 3 // 100, 18)
        flat_eye(right_eye_x, eye_y + size * 3 // 100, 18)
        brow(left_eye_x, eye_y, "worried", -1)
        brow(right_eye_x, eye_y, "worried", 1)
        nose_mouth("pout", size * 5 // 100)
        fb.stroke_rect(sx(76), sy(20), size * 13 // 100, size * 8 // 100, fine)
        fb.fill_rect(sx(89), sy(22), max(2, fine), size * 4 // 100, True)
        fb.fill_rect(sx(78), sy(22), size * 4 // 100, size * 4 // 100, True)
        return

    if expression_key == "error":
        bean_eye(left_eye_x, eye_y, size * 10 // 100, size * 17 // 100, 0, 0,
                 size * 6 // 100)
        bean_eye(right_eye_x, eye_y, size * 10 // 100, size * 17 // 100, 0, 0,
                 size * 6 // 100)
        brow(left_eye_x, eye_y, "worried", -1)
        brow(right_eye_x, eye_y, "worried", 1)
        nose_mouth("pout", size * 4 // 100)
        draw_text(fb, sx(80), sy(16), "!", max(2, size // 62))
        return

    if direction != "center":
        bean_eye(left_eye_x + face_shift_x, eye_y + face_shift_y,
                 size * 12 // 100, size * 20 // 100, gaze_x, gaze_y)
        bean_eye(right_eye_x + face_shift_x, eye_y + face_shift_y,
                 size * 12 // 100, size * 20 // 100, gaze_x, gaze_y)
        brow(left_eye_x + face_shift_x, eye_y + face_shift_y, "curious", -1)
        brow(right_eye_x + face_shift_x, eye_y + face_shift_y, "curious", 1)
        nose_mouth("cat", face_shift_y, 95)
        cheeks(2)
        sticker_accents("curious")
        motion_marks(direction)
        return

    if phase == "attention":
        bean_eye(left_eye_x, eye_y, size * 10 // 100, size * 18 // 100)
        bean_eye(right_eye_x, eye_y, size * 10 // 100, size * 18 // 100)
        brow(left_eye_x, eye_y, "curious", -1)
        brow(right_eye_x, eye_y, "curious", 1)
        nose_mouth("cat")
        question(sx(57), sy(10))
        cheeks(2)
        sticker_accents("curious")
        return

    bean_eye(left_eye_x, eye_y, size * 11 // 100, size * 20 // 100)
    bean_eye(right_eye_x, eye_y, size * 11 // 100, size * 20 // 100)
    brow(left_eye_x, eye_y, "soft", -1)
    brow(right_eye_x, eye_y, "soft", 1)
    nose_mouth("cat")
    cheeks(2)
    sticker_accents("soft")


def _draw_generated_reference_sheet_face(
    fb: Framebuffer,
    expression: str,
    x: int,
    y: int,
    size: int,
    phase: str = "base",
) -> None:
    """One-bit inner-face rig matching the generated pet-expression sheet."""
    expression_key = expression if expression in EXPRESSION_KINDS else "idle"
    unit = max(2, size // 96)
    stroke = max(3, size // 44)
    fine = max(2, size // 72)

    def sx(percent: int) -> int:
        return x + size * percent // 100

    def sy(percent: int) -> int:
        return y + size * percent // 100

    def direction_from_phase() -> str:
        if phase.startswith("attention_"):
            return phase.removeprefix("attention_")
        if phase.startswith("look_"):
            return phase.removeprefix("look_")
        if phase == "glance_left":
            return "left"
        if phase == "glance_right":
            return "right"
        if phase == "attention":
            return "center"
        return "center"

    def gaze_for(direction: str) -> tuple[int, int]:
        step = size * 6 // 100
        return (
            -step if "left" in direction else step if "right" in direction else 0,
            -step if "up" in direction else step if "down" in direction else 0,
        )

    def sparkle(mark_x: int, mark_y: int, scale: int = 1) -> None:
        short = max(3, unit * 2 * scale)
        long = max(7, unit * 4 * scale)
        fb.draw_line(mark_x - long, mark_y, mark_x + long, mark_y, fine)
        fb.draw_line(mark_x, mark_y - long, mark_x, mark_y + long, fine)
        fb.draw_line(mark_x - short, mark_y - short,
                     mark_x + short, mark_y + short, max(1, fine - 1))
        fb.draw_line(mark_x - short, mark_y + short,
                     mark_x + short, mark_y - short, max(1, fine - 1))

    def heart(mark_x: int, mark_y: int) -> None:
        r = max(3, unit * 2)
        fb.fill_circle(mark_x - r, mark_y, r, True)
        fb.fill_circle(mark_x + r, mark_y, r, True)
        fb.draw_line(mark_x - 2 * r, mark_y + r, mark_x, mark_y + 4 * r, fine)
        fb.draw_line(mark_x + 2 * r, mark_y + r, mark_x, mark_y + 4 * r, fine)

    def question(mark_x: int, mark_y: int) -> None:
        draw_text(fb, mark_x, mark_y, "?", max(2, size // 52))

    def brow(eye_x: int, eye_y: int, mood: str, side: int) -> None:
        brow_y = eye_y - size * 24 // 100
        half = size * 8 // 100
        if mood == "curious":
            offset = -size * 4 // 100 if side > 0 else size * 1 // 100
            fb.draw_arc(eye_x, brow_y + offset, half, size * 3 // 100,
                        205, 335, fine)
        elif mood == "excited":
            fb.draw_line(eye_x - half, brow_y + side * unit,
                         eye_x + half, brow_y - side * unit, fine)
        elif mood == "worried":
            fb.draw_line(eye_x - half, brow_y - side * unit,
                         eye_x + half, brow_y + side * unit, fine)
        elif mood == "sleepy":
            fb.draw_arc(eye_x, brow_y + size * 4 // 100, half,
                        size * 3 // 100, 205, 335, fine)
        else:
            fb.draw_arc(eye_x, brow_y, half, size * 3 // 100, 205, 335, fine)

    def eye(
        eye_x: int,
        eye_y: int,
        style: str,
        gaze_x: int = 0,
        gaze_y: int = 0,
        scale: int = 100,
    ) -> None:
        rx = max(9, size * 10 * scale // 10000)
        ry = max(15, size * 18 * scale // 10000)
        if style == "closed":
            fb.draw_arc(eye_x, eye_y, size * 13 // 100, size * 5 // 100,
                        198, 342, stroke)
            return
        if style == "wink":
            fb.draw_arc(eye_x, eye_y, size * 12 // 100, size * 4 // 100,
                        198, 342, stroke)
            fb.fill_circle(eye_x - size * 11 // 100, eye_y, max(1, fine), True)
            fb.fill_circle(eye_x + size * 11 // 100, eye_y, max(1, fine), True)
            return
        if style == "flat":
            half = size * 10 // 100
            fb.draw_line(eye_x - half, eye_y, eye_x + half, eye_y, stroke)
            fb.fill_circle(eye_x - half, eye_y, max(1, stroke // 2), True)
            fb.fill_circle(eye_x + half, eye_y, max(1, stroke // 2), True)
            return
        if style == "drowsy":
            lid = size * 12 // 100
            fb.fill_ellipse(eye_x, eye_y, rx, ry, True)
            fb.fill_rect(eye_x - rx - 2, eye_y - ry - 2, rx * 2 + 5, lid, False)
            fb.draw_arc(eye_x, eye_y - ry + lid, rx, max(5, ry // 3),
                        188, 352, stroke)
        else:
            fb.fill_ellipse(eye_x, eye_y, rx, ry, True)
        fb.fill_ellipse(eye_x - rx // 3 + gaze_x,
                        eye_y - ry // 3 + gaze_y,
                        max(5, rx // 3),
                        max(8, ry // 3),
                        False)
        fb.fill_circle(eye_x + rx // 3 + gaze_x,
                       eye_y + ry // 4 + gaze_y,
                       max(2, rx // 8),
                       False)

    def mouth(kind: str, lift: int = 0, scale: int = 100) -> None:
        cx = sx(50)
        nose_y = sy(56) + lift
        mouth_y = sy(63) + lift
        half = max(9, size * 10 * scale // 10000)
        if kind != "o":
            fb.fill_ellipse(cx, nose_y, max(3, size * 2 // 100),
                            max(2, size * 1 // 100), True)
            fb.draw_line(cx, nose_y + max(2, size // 100),
                         cx, mouth_y - size * 2 // 100, fine)
        if kind == "smile":
            fb.draw_arc(cx, mouth_y - size * 3 // 100,
                        max(14, half * 2), size * 8 // 100, 18, 162, stroke)
        elif kind == "wide":
            fb.draw_arc(cx, mouth_y - size * 2 // 100,
                        max(18, half * 2), size * 11 // 100, 18, 162, stroke)
            fb.fill_ellipse(cx, mouth_y + size * 1 // 100,
                            max(5, size * 4 // 100),
                            max(3, size * 3 // 100), True)
        elif kind == "o":
            fb.stroke_ellipse(cx, mouth_y - size * 3 // 100,
                              max(7, size * 6 // 100),
                              max(9, size * 8 // 100), stroke)
        elif kind == "pout":
            fb.draw_arc(cx, mouth_y + size * 5 // 100,
                        max(12, half * 2), size * 7 // 100, 200, 340, stroke)
        elif kind == "flat":
            fb.draw_line(cx - half, mouth_y, cx + half, mouth_y, stroke)
        else:
            left = cx - half * 6 // 10
            right = cx + half * 6 // 10
            fb.draw_arc(left, mouth_y - size * 1 // 100,
                        max(6, half), size * 6 // 100, 20, 150, fine)
            fb.draw_arc(right, mouth_y - size * 1 // 100,
                        max(6, half), size * 6 // 100, 30, 160, fine)

    def cheeks(kind: str = "dots", strength: int = 2) -> None:
        for side, cheek_x in ((-1, sx(24)), (1, sx(76))):
            for index in range(strength):
                yy = sy(67) + index * max(4, unit * 2)
                xx = cheek_x + side * index * max(5, unit * 2)
                if kind == "blush":
                    fb.draw_line(xx - unit, yy + unit,
                                 xx + unit, yy - unit, max(1, fine - 1))
                else:
                    fb.fill_ellipse(xx, yy, max(3, unit * 2), max(2, unit), True)

    def listening_waves() -> None:
        for side, anchor in ((-1, sx(18)), (1, sx(82))):
            for radius in (size * 5 // 100, size * 9 // 100):
                fb.draw_arc(anchor, sy(44), radius, size * 12 // 100,
                            88 if side < 0 else 272,
                            272 if side < 0 else 448,
                            fine)

    def motion(direction: str) -> None:
        if "left" in direction:
            anchor, start, end = sx(15), 92, 268
        elif "right" in direction:
            anchor, start, end = sx(85), 272, 448
        elif "up" in direction:
            draw_text(fb, sx(18), sy(14), "!!", max(2, size // 62))
            return
        elif "down" in direction:
            heart(sx(50), sy(17))
            return
        else:
            return
        for index, radius in enumerate((size * 5 // 100, size * 8 // 100)):
            fb.draw_arc(anchor, sy(44) + index * size * 8 // 100,
                        radius, size * 7 // 100, start, end, fine)

    left_x = sx(34)
    right_x = sx(66)
    eye_y = sy(42)
    direction = direction_from_phase()
    gaze_x, gaze_y = gaze_for(direction)
    shift_x = gaze_x // 2
    shift_y = gaze_y // 3

    if phase == "closed":
        brow(left_x, eye_y, "sleepy", -1)
        brow(right_x, eye_y, "sleepy", 1)
        eye(left_x, eye_y, "closed")
        eye(right_x, eye_y, "closed")
        mouth("cat", size * 2 // 100, 80)
        cheeks("dots", 1)
        return

    if phase == "half":
        brow(left_x, eye_y, "soft", -1)
        brow(right_x, eye_y, "soft", 1)
        eye(left_x, eye_y + size * 2 // 100, "drowsy", 0, 0, 105)
        eye(right_x, eye_y + size * 2 // 100, "drowsy", 0, 0, 105)
        mouth("cat", 0, 85)
        cheeks("dots", 1)
        return

    if expression_key in {"happy", "sync_complete"}:
        lift = -size * (5 if phase == "bright" else 3) // 100
        if phase == "attention" or phase.startswith("attention_"):
            brow(left_x + shift_x, eye_y + shift_y, "curious", -1)
            brow(right_x + shift_x, eye_y + shift_y, "curious", 1)
            eye(left_x + shift_x, eye_y + shift_y + lift, "open", gaze_x, gaze_y, 108)
            eye(right_x + shift_x, eye_y + shift_y + lift, "open", gaze_x, gaze_y, 108)
            mouth("cat", lift, 90)
            question(sx(55), sy(9))
            motion(direction)
        elif expression_key == "sync_complete":
            brow(left_x, eye_y + lift, "soft", -1)
            brow(right_x, eye_y + lift, "soft", 1)
            eye(left_x, eye_y + lift, "open", 0, 0, 94)
            eye(right_x, eye_y + lift, "open", 0, 0, 94)
            mouth("smile", lift, 100)
            fb.draw_line(sx(44), sy(65) + lift, sx(49), sy(70) + lift, stroke)
            fb.draw_line(sx(49), sy(70) + lift, sx(58), sy(58) + lift, stroke)
        else:
            brow(left_x, eye_y + lift, "soft", -1)
            brow(right_x, eye_y + lift, "soft", 1)
            eye(left_x, eye_y + lift, "closed")
            eye(right_x, eye_y + lift, "closed")
            mouth("wide" if phase == "bright" else "smile", lift, 120)
            heart(sx(50), sy(15))
        cheeks("blush", 2)
        sparkle(sx(80), sy(18), 1)
        if expression_key == "sync_complete":
            sparkle(sx(22), sy(22), 1)
        return

    if expression_key == "sleepy":
        drift = size * (5 if phase == "drift" else 2) // 100
        brow(left_x, eye_y + drift, "sleepy", -1)
        brow(right_x, eye_y + drift, "sleepy", 1)
        eye(left_x, eye_y + drift, "closed")
        eye(right_x, eye_y + drift, "closed")
        mouth("o" if phase == "yawn" else "cat", drift, 75)
        draw_text(fb, sx(76), sy(12), "Z", max(2, size // 56))
        draw_text(fb, sx(84), sy(6), "Z", max(1, size // 70))
        cheeks("dots", 1)
        return

    if expression_key == "thinking":
        gaze = -size * 3 // 100 if phase == "inward" else size * 3 // 100 if phase == "outward" else 0
        brow(left_x, eye_y, "curious", -1)
        brow(right_x, eye_y, "curious", 1)
        eye(left_x - size * 2 // 100, eye_y, "open", -gaze, 0, 95)
        eye(right_x + size * 2 // 100, eye_y, "open", gaze, 0, 95)
        mouth("cat", 0, 80)
        fb.stroke_circle(sx(78), sy(20), max(6, size * 5 // 100), fine)
        fb.stroke_circle(sx(72), sy(28), max(3, size * 3 // 100), fine)
        fb.stroke_circle(sx(67), sy(34), max(2, size * 2 // 100), fine)
        question(sx(56), sy(9))
        cheeks("dots", 1)
        return

    if expression_key == "speaking":
        lift = -size * (2 if phase == "open" else 0) // 100
        brow(left_x, eye_y + lift, "soft", -1)
        brow(right_x, eye_y + lift, "soft", 1)
        eye(left_x, eye_y + lift, "closed")
        eye(right_x, eye_y + lift, "closed")
        if phase == "open":
            mouth("o", lift, 110)
            bars = (size * 20 // 100, size * 14 // 100, size * 9 // 100)
        elif phase == "soft":
            mouth("cat", lift, 75)
            bars = (size * 12 // 100, size * 8 // 100)
        else:
            mouth("smile", lift, 105)
            bars = (size * 16 // 100,)
        for index, width in enumerate(bars):
            yy = sy(77) + index * size * 5 // 100
            fb.draw_line(sx(50) - width // 2, yy, sx(50) + width // 2, yy, fine)
        cheeks("dots", 2)
        return

    if expression_key == "listening":
        scale = 112 if phase == "focus" else 104
        brow(left_x, eye_y, "curious", -1)
        brow(right_x, eye_y, "curious", 1)
        eye(left_x, eye_y, "open", 0, -size * 2 // 100 if phase == "focus" else 0, scale)
        eye(right_x, eye_y, "open", 0, -size * 2 // 100 if phase == "focus" else 0, scale)
        mouth("o", 0, 100)
        if phase == "wave":
            listening_waves()
            fb.draw_arc(sx(50), sy(77), size * 18 // 100,
                        size * 5 // 100, 20, 160, fine)
        elif phase == "focus":
            fb.draw_line(sx(25), sy(46), sx(29), sy(46), fine)
            fb.draw_line(sx(71), sy(46), sx(75), sy(46), fine)
        else:
            motion("left")
            motion("right")
        cheeks("dots", 1)
        return

    if expression_key == "recording":
        compact = 92 if phase == "soft" else 100
        brow(left_x, eye_y, "soft", -1)
        brow(right_x, eye_y, "soft", 1)
        eye(left_x, eye_y, "open", 0, 0, compact)
        eye(right_x, eye_y, "open", 0, 0, compact)
        mouth("o", 0, 90)
        radius = size * (8 if phase == "pulse" else 5) // 100
        fb.fill_circle(sx(18), sy(20), max(4, radius // 2), True)
        fb.stroke_circle(sx(18), sy(20), radius, fine)
        return

    if expression_key == "low_battery":
        brow(left_x, eye_y, "worried", -1)
        brow(right_x, eye_y, "worried", 1)
        eye(left_x, eye_y + size * 3 // 100, "flat")
        eye(right_x, eye_y + size * 3 // 100, "flat")
        mouth("pout", size * 5 // 100, 100)
        fb.stroke_rect(sx(76), sy(20), size * 13 // 100, size * 8 // 100, fine)
        fb.fill_rect(sx(89), sy(22), max(2, fine), size * 4 // 100, True)
        fb.fill_rect(sx(78), sy(22), size * 4 // 100, size * 4 // 100, True)
        return

    if expression_key == "error":
        brow(left_x, eye_y, "worried", -1)
        brow(right_x, eye_y, "worried", 1)
        eye(left_x, eye_y + size * 2 // 100, "drowsy", 0, 0, 95)
        eye(right_x, eye_y + size * 2 // 100, "drowsy", 0, 0, 95)
        mouth("pout", size * 4 // 100, 100)
        draw_text(fb, sx(80), sy(16), "!", max(2, size // 62))
        return

    if direction != "center":
        brow(left_x + shift_x, eye_y + shift_y, "curious", -1)
        brow(right_x + shift_x, eye_y + shift_y, "curious", 1)
        eye(left_x + shift_x, eye_y + shift_y, "open", gaze_x, gaze_y, 108)
        eye(right_x + shift_x, eye_y + shift_y, "open", gaze_x, gaze_y, 108)
        mouth("cat", shift_y, 90)
        motion(direction)
        cheeks("dots", 2)
        return

    if phase == "attention":
        brow(left_x, eye_y, "curious", -1)
        brow(right_x, eye_y, "curious", 1)
        eye(left_x, eye_y, "open", 0, 0, 108)
        eye(right_x, eye_y, "open", 0, 0, 108)
        mouth("cat", 0, 90)
        question(sx(56), sy(9))
        cheeks("dots", 2)
        return

    brow(left_x, eye_y, "soft", -1)
    brow(right_x, eye_y, "soft", 1)
    eye(left_x, eye_y, "open", 0, 0, 104)
    eye(right_x, eye_y, "open", 0, 0, 104)
    mouth("cat", 0, 95)
    cheeks("dots", 2)


def _draw_generated_reference_sheet_face_v5(
    fb: Framebuffer,
    expression: str,
    x: int,
    y: int,
    size: int,
    phase: str = "base",
) -> None:
    """Spec-driven inner-face art matching the generated 12-pose target sheet."""
    expression_key = expression if expression in EXPRESSION_KINDS else "idle"
    unit = max(2, size // 76)
    stroke = max(5, size // 30)
    fine = max(2, size // 48)

    def sx(percent: int) -> int:
        return x + size * percent // 100

    def sy(percent: int) -> int:
        return y + size * percent // 100

    def phase_direction() -> str:
        if phase.startswith("attention_"):
            return phase.removeprefix("attention_")
        if phase.startswith("look_"):
            return phase.removeprefix("look_")
        if phase == "glance_left":
            return "left"
        if phase == "glance_right":
            return "right"
        if phase == "attention":
            return "center"
        return "center"

    def gaze(direction: str) -> tuple[int, int]:
        step = size * 6 // 100
        return (
            -step if "left" in direction else step if "right" in direction else 0,
            -step if "up" in direction else step if "down" in direction else 0,
        )

    def eye(cx: int, cy: int, kind: str = "open", scale: int = 100,
            gx: int = 0, gy: int = 0) -> None:
        rx = max(10, size * 10 * scale // 10000)
        ry = max(18, size * 18 * scale // 10000)
        if kind == "closed":
            fb.draw_arc(cx, cy, rx + unit * 5, max(6, ry // 3), 198, 342, stroke)
            return
        if kind == "wink":
            fb.draw_arc(cx, cy, rx + unit * 5, max(6, ry // 3), 198, 342, stroke)
            fb.fill_circle(cx - rx - unit, cy, max(1, fine), True)
            fb.fill_circle(cx + rx + unit, cy, max(1, fine), True)
            return
        if kind == "flat":
            fb.draw_line(cx - rx - unit, cy, cx + rx + unit, cy, stroke)
            fb.fill_circle(cx - rx - unit, cy, max(1, stroke // 2), True)
            fb.fill_circle(cx + rx + unit, cy, max(1, stroke // 2), True)
            return
        fb.fill_ellipse(cx, cy, rx, ry, True)
        if kind in {"half", "drowsy"}:
            lid = ry if kind == "half" else ry * 6 // 5
            fb.fill_rect(cx - rx - 3, cy - ry - 3, rx * 2 + 7, lid, False)
            fb.draw_arc(cx, cy - ry + lid, rx, max(4, ry // 3), 188, 352, stroke)
        fb.fill_ellipse(cx - rx // 3 + gx, cy - ry // 3 + gy,
                        max(4, rx // 3), max(6, ry // 3), False)
        fb.fill_circle(cx + rx // 3 + gx, cy + ry // 4 + gy,
                       max(2, rx // 6), False)

    def brow(cx: int, cy: int, kind: str = "soft", side: int = -1) -> None:
        by = cy - size * 26 // 100
        half = size * 8 // 100
        if kind == "curious":
            fb.draw_arc(cx, by + (-unit * 2 if side > 0 else unit),
                        half, unit * 2, 205, 335, fine)
        elif kind == "alert":
            fb.draw_line(cx - half, by + side * unit,
                         cx + half, by - side * unit, fine)
        elif kind == "worried":
            fb.draw_line(cx - half, by - side * unit,
                         cx + half, by + side * unit, fine)
        elif kind == "sleepy":
            fb.draw_arc(cx, by + unit * 2, half, unit * 2, 205, 335, fine)
        else:
            fb.draw_arc(cx, by, half, unit * 2, 205, 335, fine)

    def nose_mouth(kind: str = "cat", lift: int = 0, scale: int = 100) -> None:
        cx = sx(50)
        nose_y = sy(59) + lift
        mouth_y = sy(68) + lift
        half = max(10, size * 11 * scale // 10000)
        if kind != "o":
            fb.fill_ellipse(cx, nose_y, max(3, unit), max(2, unit // 2), True)
            fb.draw_line(cx, nose_y + unit, cx, mouth_y - unit * 2, fine)
        if kind == "cat":
            fb.draw_arc(cx - half // 2, mouth_y - unit,
                        max(6, half), max(6, unit * 4), 20, 150, fine)
            fb.draw_arc(cx + half // 2, mouth_y - unit,
                        max(6, half), max(6, unit * 4), 30, 160, fine)
        elif kind == "smile":
            fb.draw_arc(cx, mouth_y - unit * 2,
                        max(14, half * 2), max(7, unit * 5), 18, 162, stroke)
        elif kind == "open_smile":
            fb.draw_arc(cx, mouth_y - unit * 2,
                        max(15, half * 2), max(8, unit * 5), 18, 162, stroke)
            fb.fill_ellipse(cx, mouth_y + unit, max(5, unit * 3), max(4, unit * 2), True)
        elif kind == "o":
            fb.stroke_ellipse(cx, mouth_y - unit,
                              max(6, size * 5 // 100),
                              max(8, size * 7 // 100), stroke)
        elif kind == "pout":
            fb.draw_arc(cx, mouth_y + unit * 2,
                        max(12, half * 2), max(7, unit * 5), 200, 340, stroke)
        elif kind == "flat":
            fb.draw_line(cx - half, mouth_y, cx + half, mouth_y, stroke)

    def cheeks(kind: str = "dot", count: int = 2) -> None:
        for side, base_x in ((-1, sx(21)), (1, sx(79))):
            for index in range(count):
                px = base_x + side * index * unit * 3
                py = sy(69) + index * unit * 2
                if kind == "blush":
                    fb.draw_line(px - unit, py + unit, px + unit, py - unit, fine)
                else:
                    fb.fill_ellipse(px, py, max(4, unit * 2), max(2, unit), True)

    def sparkle(cx: int, cy: int, scale: int = 1) -> None:
        long = unit * 4 * scale
        short = unit * 2 * scale
        fb.draw_line(cx - long, cy, cx + long, cy, fine)
        fb.draw_line(cx, cy - long, cx, cy + long, fine)
        fb.draw_line(cx - short, cy - short, cx + short, cy + short, max(1, fine - 1))
        fb.draw_line(cx - short, cy + short, cx + short, cy - short, max(1, fine - 1))

    def heart(cx: int, cy: int) -> None:
        r = max(3, unit * 2)
        fb.fill_circle(cx - r, cy, r, True)
        fb.fill_circle(cx + r, cy, r, True)
        fb.draw_line(cx - 2 * r, cy + r, cx, cy + 4 * r, fine)
        fb.draw_line(cx + 2 * r, cy + r, cx, cy + 4 * r, fine)

    def question(cx: int, cy: int) -> None:
        draw_text(fb, cx, cy, "?", max(2, size // 50))

    def exclaim(cx: int, cy: int) -> None:
        draw_text(fb, cx, cy, "!!", max(2, size // 58))

    def thought(cx: int, cy: int) -> None:
        fb.stroke_circle(cx + unit * 4, cy, unit * 5, fine)
        fb.stroke_circle(cx - unit, cy + unit * 5, unit * 3, fine)
        fb.stroke_circle(cx - unit * 6, cy + unit * 9, unit * 2, fine)

    def waves(left: bool = True, right: bool = True) -> None:
        for side, anchor in ((-1, sx(14)), (1, sx(86))):
            if (side < 0 and not left) or (side > 0 and not right):
                continue
            for radius in (size * 5 // 100, size * 9 // 100):
                fb.draw_arc(anchor, sy(43), radius, size * 12 // 100,
                            88 if side < 0 else 272,
                            272 if side < 0 else 448,
                            fine)

    def motion_marks(direction: str) -> None:
        if "left" in direction:
            waves(left=True, right=False)
        elif "right" in direction:
            waves(left=False, right=True)
        elif "up" in direction:
            exclaim(sx(16), sy(14))
        elif "down" in direction:
            heart(sx(50), sy(16))

    left_x = sx(32)
    right_x = sx(68)
    eye_y = sy(43)
    direction = phase_direction()
    gx, gy = gaze(direction)
    shift_x = gx // 2
    shift_y = gy // 3

    if phase == "closed":
        brow(left_x, eye_y, "sleepy", -1)
        brow(right_x, eye_y, "sleepy", 1)
        eye(left_x, eye_y, "closed")
        eye(right_x, eye_y, "closed")
        nose_mouth("cat", unit * 2, 75)
        cheeks("dot", 1)
        return

    if phase == "half":
        brow(left_x, eye_y, "sleepy", -1)
        brow(right_x, eye_y, "sleepy", 1)
        eye(left_x, eye_y + unit * 2, "half", 104)
        eye(right_x, eye_y + unit * 2, "half", 104)
        nose_mouth("flat", unit, 80)
        cheeks("dot", 1)
        return

    if expression_key == "listening":
        brow(left_x, eye_y, "curious", -1)
        brow(right_x, eye_y, "curious", 1)
        focus_lift = -unit * 2 if phase == "focus" else 0
        eye(left_x, eye_y + focus_lift, "open", 118 if phase == "focus" else 108, 0, focus_lift)
        eye(right_x, eye_y + focus_lift, "open", 118 if phase == "focus" else 108, 0, focus_lift)
        nose_mouth("o", -unit if phase == "focus" else 0, 95)
        if phase == "wave":
            waves()
            fb.draw_arc(sx(50), sy(77), size * 17 // 100, unit * 3, 18, 162, fine)
        elif phase == "focus":
            fb.draw_line(sx(23), sy(46), sx(29), sy(46), fine)
            fb.draw_line(sx(71), sy(46), sx(77), sy(46), fine)
        else:
            fb.draw_line(sx(23), sy(46), sx(27), sy(46), fine)
            fb.draw_line(sx(73), sy(46), sx(77), sy(46), fine)
        cheeks("dot", 2)
        return

    if expression_key == "thinking":
        inward = phase == "inward"
        outward = phase == "outward"
        brow(left_x, eye_y, "curious", -1)
        brow(right_x, eye_y, "curious", 1)
        eye(left_x - unit, eye_y, "open", 106,
            unit * 3 if inward else -unit * 3 if outward else 0, 0)
        eye(right_x + unit, eye_y, "open", 106,
            -unit * 3 if inward else unit * 3 if outward else 0, 0)
        nose_mouth("cat", 0, 72)
        thought(sx(75), sy(21))
        if inward:
            fb.fill_circle(sx(49), sy(60), unit, True)
            fb.fill_circle(sx(54), sy(60), unit, True)
        elif outward:
            sparkle(sx(24), sy(24), 1)
            fb.fill_circle(sx(69), sy(60), unit, True)
        else:
            question(sx(56), sy(14))
        cheeks("dot", 2)
        return

    if expression_key == "speaking":
        open_phase = phase == "open"
        soft_phase = phase == "soft"
        brow(left_x, eye_y, "soft", -1)
        brow(right_x, eye_y, "soft", 1)
        eye(left_x, eye_y - unit * 2, "open" if open_phase else "closed" if not soft_phase else "wink", 102)
        eye(right_x, eye_y - unit * 2, "closed")
        nose_mouth("o" if open_phase else "cat" if soft_phase else "smile",
                   -unit if open_phase else 0, 110 if not soft_phase else 80)
        for index, width in enumerate((size * 20 // 100, size * 14 // 100, size * 9 // 100)):
            if not open_phase and not soft_phase and index > 0:
                continue
            if soft_phase and index > 1:
                continue
            yy = sy(77) + index * unit * 3
            fb.draw_line(sx(50) - width // 2, yy, sx(50) + width // 2, yy, fine)
        cheeks("dot", 2)
        return

    if expression_key in {"happy", "sync_complete"}:
        bright = phase in {"bright", "attention"} or phase.startswith("attention_")
        lift = -unit * (3 if bright else 2)
        if expression_key == "sync_complete":
            brow(left_x, eye_y + lift, "soft", -1)
            brow(right_x, eye_y + lift, "soft", 1)
            eye(left_x, eye_y + lift, "open", 100)
            eye(right_x, eye_y + lift, "open", 100)
            nose_mouth("smile", lift, 100)
            fb.draw_line(sx(44), sy(66) + lift, sx(49), sy(71) + lift, stroke)
            fb.draw_line(sx(49), sy(71) + lift, sx(59), sy(58) + lift, stroke)
            sparkle(sx(23), sy(24), 1)
        elif bright:
            brow(left_x + shift_x, eye_y + shift_y, "curious", -1)
            brow(right_x + shift_x, eye_y + shift_y, "curious", 1)
            eye(left_x + shift_x, eye_y + shift_y + lift, "open", 112, gx, gy)
            eye(right_x + shift_x, eye_y + shift_y + lift, "wink" if phase == "attention" else "open", 112, gx, gy)
            nose_mouth("open_smile", lift, 115)
            motion_marks(direction)
        else:
            brow(left_x, eye_y + lift, "soft", -1)
            brow(right_x, eye_y + lift, "soft", 1)
            eye(left_x, eye_y + lift, "closed")
            eye(right_x, eye_y + lift, "closed")
            nose_mouth("smile", lift, 115)
            heart(sx(50), sy(19))
        cheeks("blush", 3)
        sparkle(sx(80), sy(22), 1)
        return

    if expression_key == "sleepy":
        drift = unit * (4 if phase == "drift" else 2)
        brow(left_x, eye_y + drift, "sleepy", -1)
        brow(right_x, eye_y + drift, "sleepy", 1)
        eye(left_x, eye_y + drift, "closed")
        eye(right_x, eye_y + drift, "closed")
        nose_mouth("o" if phase == "yawn" else "cat", drift, 75)
        draw_text(fb, sx(76), sy(15), "Z", max(2, size // 56))
        draw_text(fb, sx(84), sy(10), "Z", max(1, size // 70))
        cheeks("dot", 1)
        return

    if expression_key == "recording":
        soft_phase = phase == "soft"
        pulse_phase = phase == "pulse"
        brow(left_x, eye_y, "soft", -1)
        brow(right_x, eye_y, "soft", 1)
        eye(left_x, eye_y + (unit if soft_phase else 0), "half" if soft_phase else "open", 94 if soft_phase else 108)
        eye(right_x, eye_y + (unit if soft_phase else 0), "half" if soft_phase else "open", 94 if soft_phase else 108)
        nose_mouth("o" if not soft_phase else "flat", 0, 90)
        radius = size * (9 if pulse_phase else 5) // 100
        fb.fill_circle(sx(18), sy(22), max(4, radius // 2), True)
        fb.stroke_circle(sx(18), sy(22), radius, fine)
        if pulse_phase:
            fb.stroke_circle(sx(18), sy(22), radius + unit * 3, fine)
        if soft_phase:
            fb.draw_line(sx(42), sy(76), sx(58), sy(76), fine)
        return

    if expression_key == "low_battery":
        brow(left_x, eye_y, "worried", -1)
        brow(right_x, eye_y, "worried", 1)
        eye(left_x, eye_y + unit * 2, "flat")
        eye(right_x, eye_y + unit * 2, "flat")
        nose_mouth("pout", unit * 4, 100)
        fb.stroke_rect(sx(76), sy(20), size * 13 // 100, size * 8 // 100, fine)
        fb.fill_rect(sx(89), sy(22), max(2, fine), size * 4 // 100, True)
        fb.fill_rect(sx(78), sy(22), size * 4 // 100, size * 4 // 100, True)
        return

    if expression_key == "error":
        brow(left_x, eye_y, "worried", -1)
        brow(right_x, eye_y, "worried", 1)
        eye(left_x, eye_y + unit, "half", 95)
        eye(right_x, eye_y + unit, "half", 95)
        nose_mouth("pout", unit * 3, 100)
        draw_text(fb, sx(80), sy(18), "!", max(2, size // 62))
        return

    if direction != "center":
        brow(left_x + shift_x, eye_y + shift_y, "curious", -1)
        brow(right_x + shift_x, eye_y + shift_y, "curious", 1)
        eye(left_x + shift_x, eye_y + shift_y, "open", 112, gx, gy)
        eye(right_x + shift_x, eye_y + shift_y, "open", 112, gx, gy)
        nose_mouth("cat", shift_y, 88)
        motion_marks(direction)
        cheeks("dot", 2)
        return

    if phase == "attention":
        brow(left_x, eye_y, "curious", -1)
        brow(right_x, eye_y, "curious", 1)
        eye(left_x, eye_y, "open", 118)
        eye(right_x, eye_y, "open", 118)
        nose_mouth("cat", 0, 88)
        question(sx(56), sy(14))
        cheeks("dot", 2)
        return

    brow(left_x, eye_y, "soft", -1)
    brow(right_x, eye_y, "soft", 1)
    eye(left_x, eye_y, "open", 110)
    eye(right_x, eye_y, "open", 110)
    nose_mouth("cat", 0, 92)
    cheeks("dot", 2)


def _draw_generated_image_baseline_face(
    fb: Framebuffer,
    expression: str,
    x: int,
    y: int,
    size: int,
    phase: str = "base",
) -> None:
    """Generated-image baseline rig: sheet-like parts, not old template faces."""
    expression_key = expression if expression in EXPRESSION_KINDS else "idle"
    unit = max(2, size // 80)
    stroke = max(4, size // 38)
    detail = max(2, stroke - 1)

    def sx(percent: int) -> int:
        return x + size * percent // 100

    def sy(percent: int) -> int:
        return y + size * percent // 100

    def direction_from_phase() -> str:
        if phase.startswith("attention_"):
            return phase.removeprefix("attention_")
        if phase.startswith("look_"):
            return phase.removeprefix("look_")
        if phase == "glance_left":
            return "left"
        if phase == "glance_right":
            return "right"
        return "center"

    def gaze_for(direction: str) -> tuple[int, int]:
        step = size * 6 // 100
        return (
            -step if "left" in direction else step if "right" in direction else 0,
            -step if "up" in direction else step if "down" in direction else 0,
        )

    def eye(cx: int, cy: int, kind: str = "bean", scale: int = 100,
            gx: int = 0, gy: int = 0) -> None:
        rx = max(10, size * 11 * scale // 10000)
        ry = max(17, size * 19 * scale // 10000)
        if kind == "closed":
            fb.draw_arc(cx, cy, rx + unit * 5, max(5, ry // 3), 198, 342, stroke)
            return
        if kind == "wink":
            fb.draw_arc(cx, cy, rx + unit * 5, max(5, ry // 3), 198, 342, stroke)
            fb.fill_circle(cx + rx + unit, cy, max(1, unit), True)
            return
        if kind == "flat":
            fb.draw_line(cx - rx - unit, cy, cx + rx + unit, cy, stroke)
            fb.fill_circle(cx - rx - unit, cy, max(1, stroke // 2), True)
            fb.fill_circle(cx + rx + unit, cy, max(1, stroke // 2), True)
            return
        fb.fill_ellipse(cx, cy, rx, ry, True)
        if kind == "half":
            fb.fill_rect(cx - rx - 3, cy - ry - 3, rx * 2 + 7, ry + unit * 2, False)
            fb.draw_arc(cx, cy, rx, max(5, ry // 3), 190, 350, stroke)
        fb.fill_ellipse(cx - rx // 3 + gx, cy - ry // 3 + gy,
                        max(5, rx // 3), max(8, ry // 3), False)
        fb.fill_circle(cx + rx // 3 + gx, cy + ry // 4 + gy,
                        max(2, rx // 5), False)

    def brow(cx: int, cy: int, kind: str = "soft", side: int = -1) -> None:
        by = cy - size * 25 // 100
        half = size * 9 // 100
        if kind == "none":
            return
        if kind == "raised":
            fb.draw_arc(cx, by - unit * (1 if side > 0 else 0), half, unit * 3, 205, 335, stroke)
        elif kind == "alert":
            fb.draw_line(cx - half, by + side * unit, cx + half, by - side * unit, stroke)
        elif kind == "worried":
            fb.draw_line(cx - half, by - side * unit, cx + half, by + side * unit, stroke)
        elif kind == "sleepy":
            fb.draw_arc(cx, by + unit * 2, half, unit * 3, 205, 335, stroke)
        else:
            fb.draw_arc(cx, by, half, unit * 3, 205, 335, stroke)

    def mouth(kind: str = "cat", lift: int = 0, scale: int = 100) -> None:
        cx = sx(50)
        nose_y = sy(59) + lift
        mouth_y = sy(68) + lift
        half = max(9, size * 9 * scale // 10000)
        if kind != "o":
            fb.fill_ellipse(cx, nose_y, max(4, unit * 2), max(2, unit), True)
            fb.draw_line(cx, nose_y + unit, cx, mouth_y - unit * 2, detail)
        if kind == "cat":
            fb.draw_arc(cx - half // 2, mouth_y - unit, half, unit * 5, 24, 152, detail)
            fb.draw_arc(cx + half // 2, mouth_y - unit, half, unit * 5, 28, 156, detail)
        elif kind == "smile":
            fb.draw_arc(cx, mouth_y - unit * 2, half * 2, unit * 5, 18, 162, stroke)
        elif kind == "open_smile":
            fb.draw_arc(cx, mouth_y - unit * 2, half * 2, unit * 6, 18, 162, stroke)
            fb.fill_ellipse(cx, mouth_y + unit, max(7, unit * 4), max(6, unit * 3), True)
            fb.fill_rect(cx - max(5, unit * 3), mouth_y - unit * 2,
                         max(10, unit * 6), max(4, unit * 2), False)
        elif kind == "o":
            fb.stroke_ellipse(cx, mouth_y - unit, max(7, unit * 4), max(9, unit * 5), stroke)
        elif kind == "flat":
            fb.draw_line(cx - half, mouth_y, cx + half, mouth_y, stroke)
        elif kind == "pout":
            fb.draw_arc(cx, mouth_y + unit, half * 2, unit * 4, 200, 340, stroke)

    def cheeks(kind: str = "dots", count: int = 2) -> None:
        if count <= 0:
            return
        for side, base_x in ((-1, sx(21)), (1, sx(79))):
            for index in range(count):
                px = base_x + side * index * unit * 3
                py = sy(64) + index * unit * 2
                if kind == "blush":
                    fb.draw_line(px - unit * 2, py + unit, px + unit * 2, py - unit, detail)
                else:
                    fb.fill_ellipse(px, py, max(5, unit * 2), max(3, unit), True)

    def sparkle(cx: int, cy: int, scale: int = 1) -> None:
        long = unit * 4 * scale
        short = unit * 2 * scale
        fb.draw_line(cx - long, cy, cx + long, cy, detail)
        fb.draw_line(cx, cy - long, cx, cy + long, detail)
        fb.draw_line(cx - short, cy - short, cx + short, cy + short, 1)
        fb.draw_line(cx - short, cy + short, cx + short, cy - short, 1)

    def heart(cx: int, cy: int) -> None:
        r = max(3, unit * 2)
        fb.fill_circle(cx - r, cy, r, True)
        fb.fill_circle(cx + r, cy, r, True)
        fb.draw_line(cx - 2 * r, cy + r, cx, cy + 4 * r, max(1, stroke - 1))
        fb.draw_line(cx + 2 * r, cy + r, cx, cy + 4 * r, max(1, stroke - 1))

    def question(cx: int, cy: int) -> None:
        draw_text(fb, cx, cy, "?", max(2, size // 58))

    def exclaim(cx: int, cy: int) -> None:
        draw_text(fb, cx, cy, "!!", max(2, size // 64))

    def zzz(cx: int, cy: int) -> None:
        draw_text(fb, cx, cy, "Z", max(2, size // 66))
        draw_text(fb, cx + unit * 7, cy - unit * 4, "z", max(1, size // 78))

    def thought(cx: int, cy: int) -> None:
        fb.stroke_circle(cx + unit * 5, cy, unit * 5, max(1, stroke - 1))
        fb.stroke_circle(cx - unit, cy + unit * 5, unit * 3, max(1, stroke - 1))
        fb.stroke_circle(cx - unit * 6, cy + unit * 9, unit * 2, max(1, stroke - 1))

    def waves() -> None:
        for side, anchor in ((-1, sx(18)), (1, sx(82))):
            for radius in (size * 4 // 100, size * 7 // 100):
                fb.draw_arc(anchor, sy(45), radius, size * 10 // 100,
                            90 if side < 0 else 270,
                            270 if side < 0 else 450,
                            detail)

    direction = direction_from_phase()
    gx, gy = gaze_for(direction)
    left_x = sx(29) + gx // 2
    right_x = sx(71) + gx // 2
    eye_y = sy(43) + gy // 3

    if phase == "closed":
        brow(left_x, eye_y, "sleepy", -1)
        brow(right_x, eye_y, "sleepy", 1)
        eye(left_x, eye_y, "closed")
        eye(right_x, eye_y, "closed")
        mouth("cat", unit * 2, 80)
        cheeks("dots", 1)
        return
    if phase == "half":
        brow(left_x, eye_y, "sleepy", -1)
        brow(right_x, eye_y, "sleepy", 1)
        eye(left_x, eye_y + unit, "half", 100)
        eye(right_x, eye_y + unit, "half", 100)
        mouth("flat", unit, 80)
        cheeks("dots", 1)
        return

    if phase == "attention":
        brow(left_x, eye_y, "raised", -1)
        brow(right_x, eye_y, "raised", 1)
        eye(left_x - unit, eye_y - unit, "bean", 118)
        eye(right_x + unit, eye_y - unit, "bean", 118)
        mouth("o", unit * 3, 126)
        question(sx(56), sy(13))
        sparkle(sx(72), sy(19), 1)
        cheeks("dots", 2)
        return

    if direction != "center" and expression_key in {"idle", "happy"}:
        brow(left_x, eye_y, "raised", -1)
        brow(right_x, eye_y, "raised", 1)
        eye(left_x, eye_y, "bean", 106, gx, gy)
        if "left" in direction:
            eye(right_x, eye_y - unit, "wink", 100, gx, gy)
        elif "right" in direction:
            eye(right_x, eye_y, "bean", 106, gx, gy)
            eye(left_x, eye_y - unit, "wink", 100, gx, gy)
        else:
            eye(right_x, eye_y, "bean", 106, gx, gy)
        mouth("cat" if expression_key == "idle" else "open_smile", gy // 4, 92)
        if "up" in direction:
            exclaim(sx(16), sy(14))
        elif "down" in direction:
            heart(sx(50), sy(16))
        elif "left" in direction or "right" in direction:
            sparkle(sx(76 if "right" in direction else 24), sy(18), 1)
        cheeks("dots", 2)
        return

    if expression_key == "listening":
        brow(left_x, eye_y, "raised", -1)
        brow(right_x, eye_y, "raised", 1)
        eye(left_x - unit, eye_y - unit, "bean", 112)
        eye(right_x + unit, eye_y - unit, "bean", 112)
        mouth("cat", unit, 96)
        waves()
        cheeks("dots", 2)
        return
    if expression_key == "thinking":
        brow(left_x, eye_y, "raised", -1)
        brow(right_x, eye_y, "raised", 1)
        eye(left_x, eye_y, "bean", 100, -unit * 3 if phase == "outward" else unit * 2, 0)
        eye(right_x, eye_y, "bean", 100, unit * 3 if phase == "outward" else -unit * 2, 0)
        mouth("cat", unit, 70)
        thought(sx(78), sy(15))
        if phase == "inward":
            fb.fill_circle(sx(49), sy(62), unit, True)
            fb.fill_circle(sx(54), sy(62), unit, True)
        else:
            question(sx(56), sy(13))
        cheeks("dots", 1)
        return
    if expression_key == "speaking":
        brow(left_x, eye_y, "soft", -1)
        brow(right_x, eye_y, "soft", 1)
        eye(left_x, eye_y - unit, "bean", 104)
        eye(right_x, eye_y - unit, "bean", 104)
        mouth("open_smile" if phase == "open" else "smile", unit * 2, 126)
        fb.draw_line(sx(23), sy(61), sx(13), sy(58), detail)
        fb.draw_line(sx(23), sy(66), sx(13), sy(67), detail)
        cheeks("dots", 2)
        return
    if expression_key in {"happy", "sync_complete"}:
        brow(left_x, eye_y - unit * 2, "soft", -1)
        brow(right_x, eye_y - unit * 2, "soft", 1)
        eye(left_x, eye_y - unit * 2, "closed")
        eye(right_x, eye_y - unit * 2, "closed")
        mouth("open_smile" if phase in {"bright", "attention"} else "smile", -unit, 112)
        heart(sx(50), sy(15)) if expression_key == "happy" else sparkle(sx(72), sy(18), 1)
        cheeks("blush", 3)
        return
    if expression_key == "sleepy":
        brow(left_x, eye_y + unit * 2, "sleepy", -1)
        brow(right_x, eye_y + unit * 2, "sleepy", 1)
        eye(left_x, eye_y + unit * 2, "closed")
        eye(right_x, eye_y + unit * 2, "closed")
        mouth("o" if phase == "yawn" else "cat", unit * 3, 72)
        zzz(sx(67), sy(17))
        cheeks("dots", 1)
        return
    if expression_key == "recording":
        brow(left_x, eye_y, "raised", -1)
        brow(right_x, eye_y, "raised", 1)
        eye(left_x, eye_y, "bean", 100)
        eye(right_x, eye_y, "bean", 100)
        mouth("o", unit * 3, 118)
        fb.fill_circle(sx(18), sy(21), max(5, unit * 4), True)
        if phase == "pulse":
            fb.stroke_circle(sx(18), sy(21), unit * 7, max(1, stroke - 1))
            exclaim(sx(26), sy(13))
        fb.draw_arc(sx(50), sy(76), size * 16 // 100, unit * 2, 200, 340, max(1, stroke - 1))
        cheeks("dots", 1)
        return
    if expression_key in {"low_battery", "error"}:
        brow(left_x, eye_y, "worried" if expression_key == "low_battery" else "alert", -1)
        brow(right_x, eye_y, "worried" if expression_key == "low_battery" else "alert", 1)
        eye(left_x, eye_y + unit, "half" if expression_key == "low_battery" else "bean", 96)
        eye(right_x, eye_y + unit, "half" if expression_key == "low_battery" else "bean", 96)
        mouth("pout", unit * 3, 88)
        exclaim(sx(70), sy(15))
        return

    brow(left_x, eye_y, "soft", -1)
    brow(right_x, eye_y, "soft", 1)
    eye(left_x, eye_y, "bean", 110)
    eye(right_x, eye_y, "bean", 110)
    mouth("cat", 0, 92)
    cheeks("dots", 2)


def draw_expression_face(
    fb: Framebuffer,
    expression: str,
    x: int,
    y: int,
    size: int,
    phase: str = "base",
) -> None:
    """Draw a generated-reference-style face inside the physical shell only."""
    _draw_generated_image_baseline_face(fb, expression, x, y, size, phase)
    return

    expression_key = expression if expression in EXPRESSION_KINDS else "idle"
    cx = x + size // 2
    line = max(4, size // 30)
    detail = max(3, size // 58)
    left_eye_x = x + size * 32 // 100
    right_eye_x = x + size * 68 // 100
    eye_y = y + size * 38 // 100
    mouth_y = y + size * 64 // 100
    eye_rx = max(18, size * 13 // 100)
    eye_ry = max(24, size * 18 // 100)

    def gaze_vector(direction: str) -> tuple[int, int]:
        # Directional attention must remain legible at 200x200 after the
        # e-paper settles, so use a deliberate but still in-eye movement.
        step = max(5, size * 7 // 100)
        horizontal = -step if "left" in direction else step if "right" in direction else 0
        vertical = -step if "up" in direction else step if "down" in direction else 0
        return horizontal, vertical

    def open_eye(eye_x: int, eye_cy: int, rx: int, ry: int,
                 gaze_x: int = 0, lid: int = 0, gaze_y: int = 0) -> None:
        """Soft bean eye with a two-point, directional eye-light rig."""
        fb.fill_ellipse(eye_x, eye_cy, rx, ry, True)
        shine = max(6, size * 6 // 100)
        fb.fill_ellipse(eye_x - rx // 3 + gaze_x,
                        eye_cy - ry // 3 + gaze_y,
                        max(4, shine * 4 // 5),
                        shine,
                        False)
        fb.fill_circle(eye_x + rx // 3 + gaze_x,
                       eye_cy + ry // 4 + gaze_y,
                       max(1, shine // 3),
                       False)
        if lid > 0:
            lid_height = min(ry + 2, lid)
            fb.fill_rect(eye_x - rx - 2, eye_cy - ry - 2,
                         rx * 2 + 5, lid_height, False)
            fb.draw_arc(eye_x, eye_cy - ry + lid_height,
                        rx, max(4, ry // 3), 190, 350, line)

    def crescent_eye(eye_x: int, eye_cy: int, lifted: int = 0,
                     worried: bool = False) -> None:
        if worried:
            fb.draw_arc(eye_x, eye_cy + lifted, eye_rx,
                        max(5, eye_ry // 3), 18, 162, line)
        else:
            fb.draw_arc(eye_x, eye_cy + lifted, eye_rx,
                        max(5, eye_ry // 3), 198, 342, line)
        fb.fill_circle(eye_x - eye_rx + detail, eye_cy + lifted,
                       max(1, detail // 2), True)
        fb.fill_circle(eye_x + eye_rx - detail, eye_cy + lifted,
                       max(1, detail // 2), True)

    def w_mouth(width_percent: int = 13, lift: int = 0) -> None:
        """Minimal cat mouth: a small nose anchors the shared character rig."""
        half = size * width_percent // 100
        top = mouth_y - size * 3 // 100 + lift
        low = mouth_y + size * 2 // 100 + lift
        nose_y = mouth_y - size * 8 // 100 + lift
        nose_rx = max(3, size * 3 // 100)
        nose_ry = max(2, size * 2 // 100)
        fb.fill_ellipse(cx, nose_y, nose_rx, nose_ry, True)
        fb.draw_line(cx, nose_y + nose_ry, cx, top, max(2, detail))
        fb.draw_line(cx, top, cx - half // 2, low, detail)
        fb.draw_line(cx - half // 2, low, cx - half, top, detail)
        fb.draw_line(cx, top, cx + half // 2, low, detail)
        fb.draw_line(cx + half // 2, low, cx + half, top, detail)

    def cheek_marks(strength: int = 1) -> None:
        strength = max(1, min(3, strength))
        for cheek_x, direction in (
                (x + size * 20 // 100, 1),
                (x + size * 80 // 100, -1)):
            for mark in range(strength):
                mark_y = mouth_y - size * 2 // 100 + mark * (detail + 4)
                mark_x = cheek_x + direction * mark * (detail + 3)
                fb.fill_ellipse(mark_x, mark_y,
                                max(3, detail + 1),
                                max(1, detail // 2 + 1),
                                True)

    def brow_pair(mood: str = "soft", lift: int = 0) -> None:
        brow_y = eye_y - eye_ry - size * 7 // 100 + lift
        brow_rx = max(7, eye_rx * 3 // 5)
        if mood == "curious":
            fb.draw_arc(left_eye_x, brow_y + detail, brow_rx, detail * 2, 200, 340, detail)
            fb.draw_arc(right_eye_x, brow_y - detail, brow_rx, detail * 2, 200, 340, detail)
        elif mood == "worried":
            fb.draw_line(left_eye_x - brow_rx, brow_y,
                         left_eye_x + brow_rx, brow_y + detail * 2, detail)
            fb.draw_line(right_eye_x - brow_rx, brow_y + detail * 2,
                         right_eye_x + brow_rx, brow_y, detail)
        elif mood == "sleepy":
            fb.draw_arc(left_eye_x, brow_y + detail, brow_rx, detail * 2, 205, 335, detail)
            fb.draw_arc(right_eye_x, brow_y + detail, brow_rx, detail * 2, 205, 335, detail)
        else:
            fb.draw_arc(left_eye_x, brow_y, brow_rx, detail * 2, 200, 340, detail)
            fb.draw_arc(right_eye_x, brow_y, brow_rx, detail * 2, 200, 340, detail)

    def tiny_question() -> None:
        draw_text(fb, x + size * 58 // 100, y + size * 9 // 100, "?", max(2, size // 50))

    def tiny_heart() -> None:
        hx = x + size * 50 // 100
        hy = y + size * 12 // 100
        r = max(2, size * 2 // 100)
        fb.fill_circle(hx - r, hy, r, True)
        fb.fill_circle(hx + r, hy, r, True)
        fb.draw_line(hx - 2 * r, hy + r, hx, hy + 4 * r, max(2, detail))
        fb.draw_line(hx + 2 * r, hy + r, hx, hy + 4 * r, max(2, detail))

    def tiny_sparkle(sparkle_x: int, sparkle_y: int, scale: int = 1) -> None:
        short = max(3, size * 2 // 100 * scale)
        long = max(7, size * 4 // 100 * scale)
        fb.draw_line(sparkle_x - long, sparkle_y, sparkle_x + long, sparkle_y, detail)
        fb.draw_line(sparkle_x, sparkle_y - long, sparkle_x, sparkle_y + long, detail)
        fb.draw_line(sparkle_x - short, sparkle_y - short,
                     sparkle_x + short, sparkle_y + short, detail)
        fb.draw_line(sparkle_x - short, sparkle_y + short,
                     sparkle_x + short, sparkle_y - short, detail)

    def sleepy_z() -> None:
        draw_text(fb, x + size * 76 // 100, y + size * 12 // 100, "Z", max(2, size // 56))
        draw_text(fb, x + size * 84 // 100, y + size * 6 // 100, "Z", max(1, size // 70))

    def open_mouth(rx_percent: int, ry_percent: int, lift: int = 0,
                   filled: bool = False) -> None:
        mouth_rx = max(5, size * rx_percent // 100)
        mouth_ry = max(6, size * ry_percent // 100)
        if filled:
            fb.fill_ellipse(cx, mouth_y + lift, mouth_rx, mouth_ry, True)
        else:
            fb.stroke_ellipse(cx, mouth_y + lift, mouth_rx, mouth_ry, line)

    def motion_marks(side: str) -> None:
        if side == "left":
            start = x + size * 13 // 100
            sign = -1
        else:
            start = x + size * 87 // 100
            sign = 1
        for index, length in enumerate((10, 15)):
            yy = eye_y - size * 4 // 100 + index * size * 8 // 100
            fb.draw_arc(start, yy, length, length // 2,
                        270 if sign > 0 else 90,
                        450 if sign > 0 else 270,
                        detail)

    def celebration_sparkle() -> None:
        sparkle_x = x + size * 80 // 100
        sparkle_y = y + size * 22 // 100
        short = max(3, size * 3 // 100)
        long = max(6, size * 6 // 100)
        tiny_sparkle(sparkle_x, sparkle_y)

    def worried_brow(eye_x: int, direction: int) -> None:
        fb.draw_line(eye_x - eye_rx, eye_y - eye_ry - detail,
                     eye_x + direction * eye_rx // 2, eye_y - eye_ry - 2 * detail,
                     line)

    # The enclosure is the cat silhouette. The display deliberately contains
    # only a reusable eyes/mouth rig and compact state marks.
    if expression_key in {"happy", "sync_complete"}:
        if expression_key == "happy" and (
                phase == "attention" or phase.startswith("attention_")):
            # A short direct gaze is the pet's acknowledgement of a touch.
            # The physical enclosure remains the cat silhouette; this only
            # changes the reusable internal eye and mouth features.
            attention_lift = -size * 2 // 100
            direction = phase.removeprefix("attention_")
            gaze_x, gaze_y = gaze_vector(direction)
            eye_shift_x = gaze_x // 2
            eye_shift_y = gaze_y // 2
            open_eye(left_eye_x + eye_shift_x,
                     eye_y + attention_lift + eye_shift_y,
                     eye_rx + size * 2 // 100,
                     eye_ry + size * 1 // 100,
                     gaze_x,
                     0,
                     gaze_y)
            open_eye(right_eye_x + eye_shift_x,
                     eye_y + attention_lift + eye_shift_y,
                     eye_rx + size * 2 // 100,
                     eye_ry + size * 1 // 100,
                     gaze_x,
                     0,
                     gaze_y)
            brow_pair("curious", attention_lift)
            w_mouth(12, attention_lift)
            cheek_marks(2)
            if "left" in direction:
                motion_marks("left")
            elif "right" in direction:
                motion_marks("right")
            elif "up" in direction:
                draw_text(fb, x + size * 21 // 100, y + size * 10 // 100, "!!", max(2, size // 62))
            elif "down" in direction:
                tiny_heart()
            return
        lift = -size * (3 if phase == "bright" else 1 if phase == "soft" else 0) // 100
        brow_pair("soft", lift)
        crescent_eye(left_eye_x, eye_y, lift)
        crescent_eye(right_eye_x, eye_y, lift)
        w_mouth(19 if phase == "bright" else 17 if phase == "soft" else 15, lift)
        cheek_marks(3 if phase == "bright" else 2)
        if expression_key == "sync_complete":
            celebration_sparkle()
        else:
            tiny_heart()
            tiny_sparkle(x + size * 77 // 100, y + size * 18 // 100)
    elif expression_key == "sleepy":
        drift = size * (3 if phase == "drift" else 1) // 100
        brow_pair("sleepy", drift)
        crescent_eye(left_eye_x, eye_y + drift, size * 3 // 100)
        crescent_eye(right_eye_x, eye_y + drift, size * 3 // 100)
        open_mouth(10 if phase == "yawn" else 6,
                   13 if phase == "yawn" else 8,
                   drift,
                   False)
        sleepy_z()
        cheek_marks(1)
    elif expression_key == "thinking":
        gaze = (-size * 3 // 100 if phase == "inward"
                else size * 3 // 100 if phase == "outward" else 0)
        brow_pair("curious")
        crescent_eye(left_eye_x, eye_y + size * 1 // 100, 0)
        open_eye(right_eye_x, eye_y - size * 2 // 100, eye_rx, eye_ry,
                 gaze, size * 3 // 100)
        w_mouth(10, size * 1 // 100)
        dot_x = cx + size * (12 if phase == "inward"
                             else 16 if phase == "outward" else 14) // 100
        fb.fill_circle(dot_x, mouth_y - size * 1 // 100, max(2, detail), True)
        fb.fill_circle(dot_x + size * 8 // 100, mouth_y - size * 7 // 100,
                       max(2, detail), True)
        fb.fill_circle(dot_x + size * 15 // 100, mouth_y - size * 14 // 100,
                       max(1, detail // 2), True)
        tiny_question()
        cheek_marks(1)
    elif expression_key == "speaking":
        lift = -size * (1 if phase == "open" else 0) // 100
        brow_pair("soft", lift)
        crescent_eye(left_eye_x, eye_y, lift)
        crescent_eye(right_eye_x, eye_y, lift)
        open_mouth(13 if phase == "open" else 8 if phase == "soft" else 10,
                   12 if phase == "open" else 7 if phase == "soft" else 9,
                   lift,
                   False)
        cheek_marks(2)
    elif expression_key == "listening":
        scale = size * (2 if phase == "focus" else 1) // 100
        gaze_y = -size * 2 // 100 if phase == "focus" else 0
        brow_pair("curious", -scale)
        open_eye(left_eye_x, eye_y, eye_rx + scale, eye_ry + scale,
                 size * 1 // 100, 0, gaze_y)
        open_eye(right_eye_x, eye_y, eye_rx + scale, eye_ry + scale,
                 size * 1 // 100, 0, gaze_y)
        open_mouth(4, 6, 0, True)
        if phase == "wave":
            for radius in (size * 5 // 100, size * 9 // 100):
                fb.draw_arc(right_eye_x + eye_rx + radius // 2, eye_y,
                            radius, size * 12 // 100, 275, 445, detail)
        else:
            motion_marks("right")
            motion_marks("left")
    elif expression_key == "recording":
        compact = size * (3 if phase == "soft" else 1) // 100
        brow_pair("soft")
        open_eye(left_eye_x, eye_y, eye_rx - compact, eye_ry - compact, 0,
                 size * 2 // 100)
        open_eye(right_eye_x, eye_y, eye_rx - compact, eye_ry - compact, 0,
                 size * 2 // 100)
        open_mouth(4, 6, 0, True)
        badge_x = x + size * 83 // 100
        badge_y = y + size * 24 // 100
        badge_radius = size * (8 if phase == "pulse" else 5 if phase == "soft" else 6) // 100
        fb.stroke_circle(badge_x, badge_y, badge_radius, detail)
        fb.fill_circle(badge_x, badge_y, max(2, badge_radius // 2), True)
        cheek_marks(1)
    elif expression_key == "low_battery":
        brow_pair("worried", size * 5 // 100)
        open_eye(left_eye_x, eye_y + size * 4 // 100, eye_rx, eye_ry,
                 0, eye_ry * 2 // 3)
        open_eye(right_eye_x, eye_y + size * 4 // 100, eye_rx, eye_ry,
                 0, eye_ry * 2 // 3)
        fb.draw_arc(cx, mouth_y + size * 7 // 100,
                    size * 10 // 100, size * 6 // 100, 198, 342, line)
        bx = x + size * 76 // 100
        by = y + size * 20 // 100
        fb.stroke_rect(bx, by, size * 14 // 100, size * 8 // 100, detail)
        fb.fill_rect(bx + size * 14 // 100, by + size * 2 // 100,
                     detail, size * 4 // 100, True)
        fb.fill_rect(bx + detail, by + detail, max(2, size * 3 // 100),
                     max(2, size * 8 // 100 - 2 * detail), True)
        cheek_marks(1)
    elif expression_key == "error":
        brow_pair("worried")
        worried_brow(left_eye_x, 1)
        worried_brow(right_eye_x, -1)
        open_eye(left_eye_x, eye_y + size * 2 // 100,
                 eye_rx - detail, eye_ry - detail, 0, size * 4 // 100)
        open_eye(right_eye_x, eye_y + size * 2 // 100,
                 eye_rx - detail, eye_ry - detail, 0, size * 4 // 100)
        fb.draw_arc(cx, mouth_y + size * 7 // 100,
                    size * 12 // 100, size * 7 // 100, 198, 342, line)
        fb.fill_circle(x + size * 84 // 100, y + size * 22 // 100,
                       max(2, detail), True)
        fb.draw_line(x + size * 84 // 100, y + size * 27 // 100,
                     x + size * 84 // 100, y + size * 34 // 100, detail)
    else:
        if phase == "closed":
            brow_pair("sleepy")
            crescent_eye(left_eye_x, eye_y)
            crescent_eye(right_eye_x, eye_y)
        elif phase == "half":
            brow_pair("soft")
            open_eye(left_eye_x, eye_y + eye_ry // 5, eye_rx, eye_ry,
                     0, eye_ry // 2)
            open_eye(right_eye_x, eye_y + eye_ry // 5, eye_rx, eye_ry,
                     0, eye_ry // 2)
        else:
            direction = phase.removeprefix("look_")
            if phase == "glance_left":
                direction = "left"
            elif phase == "glance_right":
                direction = "right"
            gaze_x, gaze_y = gaze_vector(direction)
            eye_shift_x = gaze_x // 2
            eye_shift_y = gaze_y // 2
            brow_pair("curious" if direction != phase else "soft", eye_shift_y // 2)
            open_eye(left_eye_x + eye_shift_x, eye_y + eye_shift_y,
                     eye_rx, eye_ry, gaze_x, 0, gaze_y)
            open_eye(right_eye_x + eye_shift_x, eye_y + eye_shift_y,
                     eye_rx, eye_ry, gaze_x, 0, gaze_y)
            if direction == "left":
                motion_marks("left")
            elif direction == "right":
                motion_marks("right")
            elif direction == "up":
                draw_text(fb, x + size * 22 // 100, y + size * 12 // 100, "!!", max(1, size // 62))
            elif direction == "down":
                tiny_heart()
        w_mouth(14 if phase == "base" else 12)
        cheek_marks(2 if phase == "base" else 1)


def clear_expression_shell_guard(fb: Framebuffer, x: int, y: int, size: int) -> None:
    guard = max(1, size * 5 // 100)
    fb.fill_rect(x, y, size, guard, False)
    fb.fill_rect(x, y + size - guard, size, guard, False)
    fb.fill_rect(x, y, guard, size, False)
    fb.fill_rect(x + size - guard, y, guard, size, False)


def draw_icon(fb: Framebuffer, card: CardModel, x: int, y: int, size: int) -> None:
    fb.stroke_rect(x, y, size, size, 2)
    cx = x + size // 2
    cy = y + size // 2
    if card.state == "recording" or card.card_type == "recording":
        radius = max(4, size // 5)
        for yy in range(cy - radius, cy + radius + 1):
            for xx in range(cx - radius, cx + radius + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= radius * radius:
                    fb.set_pixel(xx, yy, True)
    elif card.state == "sync_complete" or card.card_type == "sync_complete":
        for step in range(size // 3):
            fb.fill_rect(x + size // 5 + step, y + size // 2 + step, 3, 3, True)
        for step in range(size // 2):
            fb.fill_rect(cx + step // 2, y + size - size // 4 - step, 3, 3, True)
    elif card.state == "low_battery" or card.card_type == "low_battery":
        fb.stroke_rect(x + size // 5, y + size // 3, size * 3 // 5, size // 3, 2)
        fb.fill_rect(x + size * 4 // 5, y + size // 2 - 3, 4, 6, True)
        fb.fill_rect(x + size // 5 + 4, y + size // 3 + 4, size // 5, size // 3 - 8, True)
    elif card.state == "error" or card.card_type == "error":
        draw_text(fb, cx - 3, y + size // 4, "!", max(1, size // 18))
    elif card.card_type == "reminder":
        fb.stroke_rect(x + size // 4, y + size // 5, size // 2, size * 3 // 5, 2)
        fb.fill_rect(x + size // 3, y + size // 6, size // 3, 3, True)
    elif card.card_type == "event":
        fb.stroke_rect(x + size // 5, y + size // 4, size * 3 // 5, size // 2, 2)
        fb.fill_rect(x + size // 4, y + size // 3, size // 2, 2, True)
    elif card.card_type in {"expression", "mood"}:
        draw_expression_face(fb, resolve_expression_key(card), x + size // 8, y + size // 8, size * 3 // 4)
    else:
        draw_text(fb, x + size // 5, cy - 4, "C", max(1, size // 18))


def draw_footer(fb: Framebuffer, variant: DisplayVariant, margin: int, footer_h: int, label: str) -> None:
    fb.fill_rect_gray(0, variant.height - footer_h, variant.width, footer_h, 14)
    fb.fill_rect(0, variant.height - footer_h, variant.width, 1, True)
    draw_text(
        fb,
        margin,
        variant.height - footer_h + 5,
        label.upper(),
        1,
        variant.width - 2 * margin,
    )


def render_expression_card(card: CardModel, variant: DisplayVariant) -> bytes:
    fb = Framebuffer(variant.width, variant.height)
    fb.fill_rect(0, 0, variant.width, variant.height, False)
    expression = resolve_expression_key(card)
    if variant.key == "1.54in" and expression in EXPRESSION_KINDS:
        approved = APPROVED_EXPRESSION_ASSET_DIR / f"expression_{expression}_1_54in.pbm"
        if approved.exists():
            return approved.read_bytes()
    if variant.height <= 130:
        face_size = variant.height - 32
        face_x = (variant.width - face_size) // 2
        face_y = 16
    else:
        face_size = min(variant.width, variant.height) - 36
        face_x = (variant.width - face_size) // 2
        face_y = (variant.height - face_size) // 2
    draw_expression_face(fb, expression, face_x, face_y, face_size)
    clear_expression_shell_guard(fb, face_x, face_y, face_size)
    return fb.to_pbm(f"companion emote matrix white background {card.card_id} {variant.key}")


def render_card(card: CardModel, variant: DisplayVariant) -> bytes:
    if card.card_type not in CARD_TYPES:
        raise ValueError(f"unsupported card_type: {card.card_type}")
    if card.state not in CARD_STATES:
        raise ValueError(f"unsupported state: {card.state}")
    if card.card_type == "expression":
        return render_expression_card(card, variant)

    fb = Framebuffer(variant.width, variant.height)
    fb.fill_rect(0, 0, variant.width, variant.height, False)
    fb.fill_rect_gray(0, 0, variant.width, variant.height, 4)

    margin = 8 if variant.width <= 200 else 7
    header_h = 25 if variant.height <= 130 else 32
    footer_h = 17 if variant.height <= 130 else 22
    icon_size = 34 if variant.height <= 130 else 48

    fb.fill_rect_gray(0, 0, variant.width, header_h, 22)
    fb.fill_rect(0, header_h - 2, variant.width, 2, True)
    fb.stroke_rect(0, 0, variant.width, variant.height, 2)

    title_scale = 2 if variant.height <= 130 else 3
    body_scale = 1 if variant.height <= 130 else 2
    title_max = max(4, (variant.width - 2 * margin) // (6 * title_scale))
    title = card.title.upper()[:title_max]
    draw_text(fb, margin, 6, title, title_scale, variant.width - 2 * margin)

    icon_x = margin
    icon_y = header_h + margin
    draw_icon(fb, card, icon_x, icon_y, icon_size)

    body_x = icon_x + icon_size + margin
    body_y = header_h + margin + 1
    body_width = variant.width - body_x - margin
    max_chars = max(8, body_width // (6 * body_scale))
    max_lines = 4 if variant.height > 130 else 3
    for index, line in enumerate(wrap_text(card.body, max_chars, max_lines)):
        draw_text(fb, body_x, body_y + index * (8 * body_scale + 2), line, body_scale, body_width)

    state_label = card.footer or card.state.replace("_", " ").upper()
    draw_footer(fb, variant, margin, footer_h, state_label)
    return fb.to_pbm(f"companion {card.card_id} {variant.key}")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode_ble_text(value: Any, length_key: str | None = None, payload: dict[str, Any] | None = None) -> str:
    if value is None:
        return ""
    byte_length: int | None = None
    if length_key and payload and isinstance(payload.get(length_key), int):
        byte_length = max(0, int(payload[length_key]))
    if isinstance(value, bytes):
        raw = value
    elif isinstance(value, list):
        raw = bytes(int(item) & 0xFF for item in value)
    elif isinstance(value, bytearray):
        raw = bytes(value)
    else:
        raw = str(value).encode("utf-8")
    if byte_length is not None:
        raw = raw[:byte_length]
    return raw.decode("utf-8", errors="replace")


def card_from_ble_write(payload: dict[str, Any]) -> CardModel:
    """Map the 1.3 BLE CardWriteV1 shape into the renderer model."""

    flags = int(payload.get("display_flags", 0))
    slot = int(payload.get("card_slot", 0))
    title = decode_ble_text(payload.get("title", payload.get("utf8_title")), "utf8_title_len", payload)
    body = decode_ble_text(payload.get("body", payload.get("utf8_body")), "utf8_body_len", payload)

    if flags & 0x04:
        card_type = "mood"
    elif flags & 0x08:
        card_type = "name"
    elif flags & 0x02 or slot == 2:
        card_type = "event"
    elif flags & 0x01 or slot == 1:
        card_type = "reminder"
    else:
        card_type = "name"

    return CardModel(
        card_id="ble_card_write",
        card_type=card_type,
        state="idle",
        title=title or "Companion",
        body=body or "BLE card update",
        footer=f"REQ {int(payload.get('request_id', 0))}",
        request_id=int(payload.get("request_id", 0)),
        card_slot=slot,
        display_flags=flags,
    )


def expression_fixture_cards() -> list[CardModel]:
    cards: list[CardModel] = []
    for expression in sorted(EXPRESSION_KINDS):
        title, body, footer = EXPRESSION_COPY[expression]
        cards.append(
            CardModel(
                card_id=f"expression_{expression}",
                card_type="expression",
                state=expression,
                title=title,
                body=body,
                footer=footer,
            )
        )
    return cards


def default_fixture_cards() -> list[CardModel]:
    cards = [
        CardModel(
            card_id="boot_default",
            card_type="boot",
            state="default",
            title="Companion",
            body="Ready for BLE card write. Meeting fallback: \u4f1a\u8bae",
            footer="BOOT DEFAULT",
        ),
        CardModel(
            card_id="recording",
            card_type="recording",
            state="recording",
            title="Recording",
            body="00:12 captured locally. BLE pull will verify length and hash.",
            footer="REC ACTIVE",
        ),
        CardModel(
            card_id="sync_complete",
            card_type="sync_complete",
            state="sync_complete",
            title="Synced",
            body="Recording transferred. Delete needs validated length and SHA.",
            footer="SYNC COMPLETE",
        ),
    ]
    cards.extend(expression_fixture_cards())
    return cards


def required_state_cards() -> Iterable[CardModel]:
    yield from default_fixture_cards()
    yield CardModel("mood", "mood", "idle", "Mood", "Calm focus", "MOOD")
    yield CardModel("name", "name", "idle", "Denzic", "Pendant owner card", "NAME")
    yield CardModel("event", "event", "idle", "Event", "Lab bring-up at 14:30", "EVENT")
    yield CardModel("reminder", "reminder", "idle", "Reminder", "Charge after test", "REMINDER")
    yield CardModel("low_battery", "low_battery", "low_battery", "Battery", "12 percent", "LOW BATTERY")
    yield CardModel("error", "error", "error", "Error", "Display queue busy", "ERROR")
