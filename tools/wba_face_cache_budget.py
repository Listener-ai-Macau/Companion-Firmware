"""Bind the exact UI bank to the renderer's bounded lossless face caches.

This is a build-time resource-capacity check, with no device access. It covers
all states rather than relying on names to guess which can become a pet face.
It does not qualify C decoding, visual equivalence or real-time execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import zlib

from faraday_upper_art.build_ui_asset_generation import encode_packbits

FRAME_BYTES = 5000


def capacity_from_header(path: Path) -> int:
    values = re.findall(r'^#define COMP_RUNTIME_WBA_FACE_CACHE_BYTES (\d+)u\s*$',
                        path.read_text(encoding='utf8'), re.MULTILINE)
    if len(values) != 1 or not 0 < int(values[0]) <= FRAME_BYTES:
        raise ValueError('Renderer must declare one literal WBA face-cache capacity')
    return int(values[0])


def _slice(data: bytes, at: int, size: int) -> bytes:
    if at < 0 or size < 0 or at > len(data) or size > len(data) - at:
        raise ValueError('UI resource range outside its actual bank')
    return data[at:at + size]


def _packbits(encoded: bytes) -> bytes:
    output = bytearray()
    at = 0
    while at < len(encoded):
        control = encoded[at]
        at += 1
        if control == 128:
            raise ValueError('Forbidden PackBits NOP')
        count = control + 1 if control < 128 else 257 - control
        if count > FRAME_BYTES - len(output):
            raise ValueError('PackBits exceeds native frame size')
        if control < 128:
            output.extend(_slice(encoded, at, count))
            at += count
        else:
            output.extend(_slice(encoded, at, 1) * count)
            at += 1
    if len(output) != FRAME_BYTES:
        raise ValueError('PackBits does not decode one complete native frame')
    return bytes(output)


def _xor(base: bytes, encoded: bytes) -> bytes:
    output = bytearray(base)
    at = previous_end = 0
    while at < len(encoded):
        offset, count = struct.unpack('<HB', _slice(encoded, at, 3))
        at += 3
        if not count or offset < previous_end or offset + count > FRAME_BYTES:
            raise ValueError('Malformed XOR patch range')
        for index, value in enumerate(_slice(encoded, at, count)):
            output[offset + index] ^= value
        at += count
        previous_end = offset + count
    return bytes(output)


def inspect_bank(path: Path, capacity: int, expected_generation: int) -> dict:
    if not 0 < capacity <= FRAME_BYTES:
        raise ValueError('Invalid cache capacity')
    bank = path.read_bytes()
    if len(bank) < 8192 or len(bank) % 4096:
        raise ValueError('UI bank must include its two aligned resource roots')
    roots = []
    for at in (len(bank) - 8192, len(bank) - 4096):
        root = _slice(bank, at, 128)
        if root[:4] == b'CUIR' and struct.unpack_from('<HH', root, 4) == (1, 128) and \
                zlib.crc32(root[:124]) == struct.unpack_from('<I', root, 124)[0]:
            roots.append(root)
    if not roots:
        raise ValueError('UI has no valid resource root')
    root = max(roots, key=lambda row: struct.unpack_from('<I', row, 8)[0])
    generation, base_size, blob, blob_size = struct.unpack_from('<IIII', root, 8)
    if generation != expected_generation:
        raise ValueError('Actual resource-root generation differs from build profile')
    manifest_offset, manifest_size = struct.unpack_from('<II', root, 28)
    if manifest_offset > blob_size or manifest_size > blob_size - manifest_offset:
        raise ValueError('Manifest outside committed resource blob')
    manifest = _slice(bank, blob + manifest_offset, manifest_size)
    if manifest[:4] != b'CUIM' or len(manifest) < 32:
        raise ValueError('Missing complete state manifest')
    count, entry_size = struct.unpack_from('<HH', manifest, 8)
    if not count or entry_size != 24 or len(manifest) != 32 + count * 24:
        raise ValueError('Invalid complete state-manifest extent')
    cemp = _slice(bank, 0, base_size)
    if len(cemp) < 80 or cemp[:4] != b'CEMP' or struct.unpack_from('<I', cemp, 8)[0] != len(cemp):
        raise ValueError('Invalid base CEMP')
    if struct.unpack_from('<HHH', cemp, 20) != (200, 200, 25) or cemp[26:28] != bytes((1, 2)):
        raise ValueError('Expected native200x200 mono PackBits CEMP')
    base_count = struct.unpack_from('<H', cemp, 30)[0]
    table = struct.unpack_from('<I', cemp, 36)[0]
    payload, payload_size = struct.unpack_from('<II', cemp, 48)
    _slice(cemp, payload, payload_size)
    bases = []
    for index in range(base_count):
        offset, size = struct.unpack('<II', _slice(cemp, table + index * 20, 8))
        if offset > payload_size or size > payload_size - offset:
            raise ValueError('Base frame outside CEMP payload')
        bases.append(_packbits(_slice(cemp, payload + offset, size)))
    maximum = 0
    largest_state = None
    measured = {}
    for index in range(count):
        state, base_index, flags, crc, offset, size, _, _ = struct.unpack_from('<IHHIIHHI', manifest, 32 + index * 24)
        key = (base_index, flags, crc, offset, size)
        if key in measured:
            length = measured[key]
        else:
            if flags in (0, 4) and base_index >= len(bases):
                raise ValueError('State refers to absent base frame')
            if flags == 0:
                frame = bases[base_index]
            elif flags == 1:
                frame = _slice(bank, offset, size)
            elif flags == 2:
                frame = _packbits(_slice(bank, offset, size))
            elif flags == 4:
                frame = _xor(bases[base_index], _slice(bank, offset, size))
            else:
                raise ValueError('Unsupported state encoding')
            if len(frame) != FRAME_BYTES or zlib.crc32(frame) != crc:
                raise ValueError('State native pixels differ from committed CRC')
            length = len(encode_packbits(frame))
            measured[key] = length
        if length > maximum:
            maximum, largest_state = length, state
    return dict(result='FACE_CACHE_BANK_FITS' if maximum <= capacity else 'FACE_CACHE_BANK_TOO_LARGE',
                uiSha256=hashlib.sha256(bank).hexdigest(), generation=generation,
                states=count, distinctStoredRepresentations=len(measured),
                nativeFrameBytes=FRAME_BYTES, cacheBytes=capacity,
                maximumEncodedBytes=maximum, largestStateHash=largest_state,
                cacheCapacityFits=maximum <= capacity,
                hardwareOperations=0, cCodecQualified=False, physicalQualified=False,
                scope='Complete exact UI bank capacity only; not C round-trip, runtime timing, stack, art acceptance or SRAM-layout qualification')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('--renderer-header', required=True, type=Path)
    parser.add_argument('--generation', required=True, type=int)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = inspect_bank(args.image, capacity_from_header(args.renderer_header), args.generation)
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        if args.output.exists():
            raise FileExistsError('Refuse to overwrite earlier resource evidence')
        args.output.write_text(encoded, encoding='utf8')
    print(encoded, end='')
    return 0 if report['cacheCapacityFits'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
