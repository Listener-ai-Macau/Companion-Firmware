"""Generate the immutable controller-polarity bytes for the R12 V22 sampler."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/candidate/component-export-attempt-03/reassembled-200x200"
OUT = ROOT / "app/companion_pendant/epaper/r12_v22_calm_curious_warm_sampler_assets.h"
NAMES = ("calm", "curious", "warm")


def parse_p4(data: bytes, label: str = "PBM") -> tuple[int, int, bytes]:
    index = 0

    def token() -> bytes:
        nonlocal index
        while index < len(data):
            if data[index] in b" \t\r\n":
                index += 1
                continue
            if data[index] == ord("#"):
                newline = data.find(b"\n", index)
                if newline < 0:
                    raise ValueError(f"unterminated PBM comment: {label}")
                index = newline + 1
                continue
            break
        start = index
        while index < len(data) and data[index] not in b" \t\r\n#":
            index += 1
        if start == index:
            raise ValueError(f"missing PBM token: {label}")
        return data[start:index]

    if token() != b"P4":
        raise ValueError(f"not a P4 PBM: {label}")
    try:
        width = int(token(), 10)
        height = int(token(), 10)
    except ValueError as exc:
        raise ValueError(f"invalid PBM dimensions: {label}") from exc
    if index >= len(data) or data[index] not in b" \t\r\n":
        raise ValueError(f"missing PBM raster separator: {label}")
    if data[index:index + 2] == b"\r\n":
        index += 2
    else:
        index += 1
    expected = ((width + 7) // 8) * height
    raster = data[index:]
    if width != 200 or height != 200 or len(raster) != expected:
        raise ValueError(f"unexpected PBM raster: {label}: {width}x{height}, {len(raster)} bytes")
    return width, height, raster


def controller_bytes(path: Path) -> bytes:
    _, _, raster = parse_p4(path.read_bytes(), str(path))
    return bytes(value ^ 0xFF for value in raster)


def render_header() -> bytes:
    lines = [
        "#ifndef COMPANION_R12_V22_CALM_CURIOUS_WARM_SAMPLER_ASSETS_H",
        "#define COMPANION_R12_V22_CALM_CURIOUS_WARM_SAMPLER_ASSETS_H",
        "",
        "#include <stdint.h>",
        "",
        "#define COMP_R12_V22_FRAME_BYTES 5000u",
        "",
    ]
    for name in NAMES:
        values = controller_bytes(SOURCE / f"{name}.pbm")
        lines.append(f"static const uint8_t comp_r12_v22_{name}_frame[COMP_R12_V22_FRAME_BYTES] = {{")
        for offset in range(0, len(values), 16):
            lines.append("    " + ", ".join(f"0x{value:02X}u" for value in values[offset:offset + 16]) + ",")
        lines.extend(["};", ""])
    lines.append("#endif")
    return ("\r\n".join(lines) + "\r\n").encode("ascii")


def main() -> None:
    OUT.write_bytes(render_header())


if __name__ == "__main__":
    main()
