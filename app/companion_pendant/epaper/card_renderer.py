#!/usr/bin/env python3
"""No-hardware Companion pendant e-paper card renderer."""

from __future__ import annotations

import hashlib
import textwrap
from dataclasses import asdict, dataclass
from typing import Any, Iterable


CARD_TYPES = {
    "boot",
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
    "recording",
    "sync_complete",
    "low_battery",
    "error",
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
    elif card.card_type == "mood":
        fb.stroke_rect(x + size // 4, y + size // 4, size // 2, size // 2, 1)
        fb.set_pixel(cx - size // 8, cy - size // 10, True)
        fb.set_pixel(cx + size // 8, cy - size // 10, True)
        fb.fill_rect(cx - size // 8, cy + size // 8, size // 4, 2, True)
    else:
        draw_text(fb, x + size // 5, cy - 4, "C", max(1, size // 18))


def render_card(card: CardModel, variant: DisplayVariant) -> bytes:
    if card.card_type not in CARD_TYPES:
        raise ValueError(f"unsupported card_type: {card.card_type}")
    if card.state not in CARD_STATES:
        raise ValueError(f"unsupported state: {card.state}")

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
    fb.fill_rect_gray(0, variant.height - footer_h, variant.width, footer_h, 14)
    fb.fill_rect(0, variant.height - footer_h, variant.width, 1, True)
    draw_text(
        fb,
        margin,
        variant.height - footer_h + 5,
        state_label.upper(),
        1,
        variant.width - 2 * margin,
    )
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


def default_fixture_cards() -> list[CardModel]:
    return [
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


def required_state_cards() -> Iterable[CardModel]:
    yield from default_fixture_cards()
    yield CardModel("mood", "mood", "idle", "Mood", "Calm focus", "MOOD")
    yield CardModel("name", "name", "idle", "Denzic", "Pendant owner card", "NAME")
    yield CardModel("event", "event", "idle", "Event", "Lab bring-up at 14:30", "EVENT")
    yield CardModel("reminder", "reminder", "idle", "Reminder", "Charge after test", "REMINDER")
    yield CardModel("low_battery", "low_battery", "low_battery", "Battery", "12 percent", "LOW BATTERY")
    yield CardModel("error", "error", "error", "Error", "Display queue busy", "ERROR")
