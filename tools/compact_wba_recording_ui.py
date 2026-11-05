#!/usr/bin/env python3
"""Losslessly pack the existing on-chip text atlases to leave CE room for recording.

The UI resource bank and authored headers are untouched. Generated pointer tables
keep the original locale/item indexing; only runs of white bytes are compressed.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]


def pack(data: bytes) -> bytes:
    out = bytearray()
    i = 0
    while i < len(data):
        if data[i] == 255:
            stop = i
            while stop < min(i + 128, len(data)) and data[stop] == 255:
                stop += 1
            if stop - i >= 2:
                out.append(128 | (stop - i - 1))
                i = stop
                continue
        stop = i + 1
        while stop < min(i + 128, len(data)):
            if data[stop:stop + 2] == b'\xff\xff':
                break
            stop += 1
        out.append(stop - i - 1)
        out.extend(data[i:stop])
        i = stop
    return bytes(out)


def unpack(data: bytes, expected: int) -> bytes:
    out = bytearray()
    i = 0
    while i < len(data):
        token = data[i]
        i += 1
        count = (token & 127) + 1
        if token & 128:
            out.extend(b'\xff' * count)
        else:
            assert i + count <= len(data), 'truncated literal'
            out.extend(data[i:i + count])
            i += count
        assert len(out) <= expected, 'invalid decoded extent'
    assert len(out) == expected, 'wrong decoded extent'
    return bytes(out)


def compact_header(source: Path, name: str) -> tuple[str, bytes, dict]:
    text = source.read_text(encoding='utf-8')
    pattern = rf'static const uint8_t {name}\[(\d+)\]\[(\d+)\]\[(\d+)\]\s*=\s*\{{(.*?)\}};'
    match = re.search(pattern, text, re.S)
    assert match, f'unsupported atlas declaration: {source}'
    locales, items, width = (int(match[i]) for i in (1, 2, 3))
    body = re.sub(r'/\*.*?\*/|//[^\n]*', '', match[4], flags=re.S)
    values = [int(v, 16 if v.lower().startswith('0x') else 10)
              for v in re.findall(r'0x[0-9a-fA-F]+|\b\d+\b', body)]
    assert len(values) == locales * items * width
    original = bytes(values)
    packed = bytearray()
    offsets = []
    for i in range(locales * items):
        glyph = original[i * width:(i + 1) * width]
        encoded = pack(glyph)
        assert unpack(encoded, width) == glyph
        offsets.append(len(packed))
        packed.extend(encoded)
    assert len(packed) < 65536
    lines = [f'static const uint8_t {name}_packed[] = {{']
    for i in range(0, len(packed), 24):
        lines.append('    ' + ','.join(f'0x{x:02x}' for x in packed[i:i + 24]) + ',')
    lines += ['};', f'static const uint8_t *const {name}[{locales}][{items}] = {{']
    for locale in range(locales):
        lines.append('    {' + ','.join(f'{name}_packed+{o}u' for o in offsets[locale * items:(locale + 1) * items]) + '},')
    lines.append('};')
    result = text[:match.start()] + '\n'.join(lines) + text[match.end():]
    info = dict(source=str(source), originalBytes=len(original), packedBytes=len(packed),
                pointerBytesM33=len(offsets) * 4, glyphs=len(offsets), glyphBytes=width,
                originalSha256=hashlib.sha256(original).hexdigest(),
                packedSha256=hashlib.sha256(packed).hexdigest(), decodedByteExact=True)
    return result, original, info


def generate(resource_dir: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    sources = [(ROOT / 'app/companion_pendant/runtime/generated/companion_wba_live_menu_values.h', 'comp_wba_live_values'),
               (ROOT / 'app/companion_pendant/runtime/generated/companion_wba_menu_feedback.h', 'comp_wba_menu_feedback')]
    caption = resource_dir / 'companion_pet_reply_captions.h'
    if caption.exists():
        sources.append((caption, 'comp_pet_reply_captions'))
    texts = ['/* Generated lossless white-run atlases; do not edit. */',
             '#ifndef COMPANION_WBA_RECORDING_UI_PACKED_H',
             '#define COMPANION_WBA_RECORDING_UI_PACKED_H']
    atlases = []
    original = bytearray()
    for source, name in sources:
        text, raw, info = compact_header(source, name)
        texts.append(text)
        original.extend(raw)
        atlases.append(dict(name=name, **info))
    texts.append('#endif')
    header = output / 'companion_wba_recording_ui_packed.h'
    header.write_text('\n'.join(texts) + '\n', encoding='utf-8', newline='\n')
    report = dict(schema='companion.recording-ui.lossless-pack.v1',
                  atlases=atlases, originalBytes=sum(a['originalBytes'] for a in atlases),
                  packedBytes=sum(a['packedBytes'] + a['pointerBytesM33'] for a in atlases),
                  originalConcatSha256=hashlib.sha256(original).hexdigest(),
                  generatedHeaderSha256=hashlib.sha256(header.read_bytes()).hexdigest(),
                  uiResourceBankModified=False, decodedByteExact=True)
    (output / 'recording-ui-pack.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resources', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = generate(args.resources.resolve(), args.output.resolve())
    print(json.dumps({k: report[k] for k in ('originalBytes', 'packedBytes', 'decodedByteExact', 'uiResourceBankModified')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
