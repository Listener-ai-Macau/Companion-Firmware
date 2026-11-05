#!/usr/bin/env python3
"""Move the existing recording-reason glyphs into a matched UI bank.

This only creates a candidate; it does not install firmware or move the
recording/OTA boundary. The original glyphs and the original bank are inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import struct
import zlib
from pathlib import Path

from compact_wba_recording_ui import unpack

ROOT = Path(__file__).resolve().parents[1]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def values(section: str, name: str) -> list[int]:
    match = re.search(r'static const uint(?:8|16)_t\s+' + re.escape(name)
                      + r'(?:\[\d*\])+\s*=\s*\{(.*?)\};', section, re.S)
    if not match:
        raise ValueError('missing glyph array: ' + name)
    return [int(v, 0) for v in re.findall(r'0x[0-9a-fA-F]+|\b\d+\b', match[1])]


def generate(base: Path, out: Path, generation: int) -> dict:
    profile = json.loads((base / 'profile.json').read_bytes())
    bank = (base / 'ui-partition.bin').read_bytes()
    if profile['generation'] != 84 or generation != 85:
        raise ValueError('candidate requires exactly UI84 input and UI85 output')
    if digest(bank).upper() != profile['uiPartitionSha256'].upper():
        raise ValueError('resource bank does not match profile')
    geo = profile['flashGeometry']
    ext = profile['externalUi']
    start = ext['extensionOffset']
    end = start + ext['extensionBytes']
    if end != profile['resourceArenaUsedBytes'] or end > geo['rootA']:
        raise ValueError('resource extension does not match its live arena')
    header = (base / 'companion_wba_external_ui.h').read_text(encoding='utf-8')
    crc = re.search(r'COMP_WBA_EXTERNAL_UI_CRC32 0x([0-9A-Fa-f]+)u', header)
    if not crc or zlib.crc32(bank[start:end]) != int(crc[1], 16):
        raise ValueError('existing external atlas CRC differs')

    native = (ROOT / 'app/companion_pendant/runtime/generated/companion_recording_reason_labels.h').read_text(encoding='ascii')
    packed, uncompressed = native.split('#else', 1)
    compressed = bytes(values(packed, 'comp_record_reason_bits'))
    offsets = values(packed, 'comp_record_reason_offsets')
    original = bytes(values(uncompressed, 'comp_record_reason_bits'))
    if len(offsets) != 12 or len(original) != 12 * 16 * 14 or offsets[0] != 0:
        raise ValueError('unexpected original recording labels')
    if offsets != sorted(set(offsets)):
        raise ValueError('recording-label offsets must be distinct and increasing')
    boundaries = offsets[1:] + [len(compressed)]
    maximum = ext['maxGlyphBytes']
    refs = []
    for i, (lo, hi) in enumerate(zip(offsets, boundaries)):
        encoded = compressed[lo:hi]
        if not encoded or len(encoded) > maximum:
            raise ValueError('glyph exceeds existing bounded read buffer')
        if unpack(encoded, 16 * 14) != original[i * 224:(i + 1) * 224]:
            raise ValueError('packed label differs from original pixels')
        refs.append('{%du,%du,0x%08Xu}' % (end - start + lo, len(encoded), zlib.crc32(encoded)))
    if end + len(compressed) > geo['rootA']:
        raise ValueError('insufficient static arena; refusing to shift dynamic data')
    if bank[end:end + len(compressed)] != b'\xff' * len(compressed):
        raise ValueError('unused resource padding is not erased')
    rows = ['{' + ','.join(refs[i:i + 4]) + '}' for i in range(0, 12, 4)]
    declaration = ('#define COMP_WBA_EXTERNAL_RECORD_REASON 1\n'
                   'static const comp_wba_external_bitmap_t comp_record_reason_external[3][4] = {'
                   + ','.join(rows) + '};\n')
    merged = bank[start:end] + compressed
    header = re.sub(r'(COMP_WBA_EXTERNAL_UI_BYTES )\d+u', r'\g<1>' + str(len(merged)) + 'u', header)
    header = re.sub(r'(COMP_WBA_EXTERNAL_UI_CRC32 )0x[0-9A-Fa-f]+u',
                    r'\g<1>0x%08Xu' % zlib.crc32(merged), header)
    header = header.rsplit('#endif', 1)[0] + declaration + '#endif\n'
    contract = (base / 'companion_wba_resource_contract.h').read_text(encoding='utf-8')
    identity = digest(bytes.fromhex(profile['resourceId']) + b'Companion record reasons v1\0' + compressed).upper()
    if 'COMPANION_WBA_RESOURCE_GENERATION 84u' not in contract or profile['resourceId'] not in contract:
        raise ValueError('resource contract does not match UI84')
    contract = contract.replace('COMPANION_WBA_RESOURCE_GENERATION 84u', 'COMPANION_WBA_RESOURCE_GENERATION 85u').replace(profile['resourceId'], identity)

    result = bytearray(bank)
    root = bytearray(bank[geo['rootA']:geo['rootA'] + 128])
    if root[:4] != b'CUIR' or zlib.crc32(root[:124]) != struct.unpack_from('<I', root, 124)[0]:
        raise ValueError('resource root is invalid')
    blob_offset, blob_size = struct.unpack_from('<II', root, 16)
    if blob_offset + blob_size != end or zlib.crc32(bank[blob_offset:end]) != struct.unpack_from('<I', root, 24)[0]:
        raise ValueError('resource root does not bind current bank')
    result[end:end + len(compressed)] = compressed
    whole_blob = bank[blob_offset:end] + compressed
    struct.pack_into('<I', root, 8, generation)
    struct.pack_into('<II', root, 20, len(whole_blob), zlib.crc32(whole_blob))
    struct.pack_into('<I', root, 40, (end + len(compressed) + 4095) & ~4095)
    root[44:76] = bytes.fromhex(identity)
    struct.pack_into('<I', root, 124, zlib.crc32(root[:124]))
    result[geo['rootA']:geo['rootA'] + 128] = root
    result[geo['rootB']:] = b'\xff' * (len(result) - geo['rootB'])
    if bytes(result[:end]) != bank[:end] or len(result) != len(bank):
        raise ValueError('existing resource data or static boundary changed')

    out.mkdir(parents=True, exist_ok=False)
    for item in base.glob('*.h'):
        shutil.copyfile(item, out / item.name)
    (out / 'companion_wba_external_ui.h').write_text(header, encoding='utf-8', newline='\n')
    (out / 'companion_wba_resource_contract.h').write_text(contract, encoding='utf-8', newline='\n')
    (out / 'ui-partition.bin').write_bytes(result)
    profile.update(generation=generation, resourceId=identity,
                   uiPartitionSha256=digest(result).upper(),
                   resourceArenaUsedBytes=end + len(compressed), generationBytes=len(whole_blob),
                   result='RESOURCE_CANDIDATE_BUILT', hardwareAcceptance='NOT_RUN', fullChainAcceptance='NOT_RUN')
    ext.update(generation=generation, extensionBytes=len(merged),
               headerSha256=digest((out / 'companion_wba_external_ui.h').read_bytes()),
               newBankSha256=digest(result), arenaFreeBytes=geo['rootA'] - end - len(compressed))
    ext['recordReasonBytes'] = len(compressed)
    ext['atlas'] = ext['atlas'] + [dict(name='comp_record_reason_external', shape=[3, 4],
        glyphs=12, decodedBytes=len(original), encodedBytes=len(compressed),
        originalSha256=digest(original), lossless=True)]
    (out / 'profile.json').write_text(json.dumps(profile, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return dict(generation=generation, addedBytes=len(compressed), remainingArenaBytes=ext['arenaFreeBytes'],
                originalPixelsSha256=digest(original), bankSha256=digest(result), dynamicBoundaryUnchanged=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--generation', type=int, default=85)
    args = parser.parse_args()
    print(json.dumps(generate(args.base.resolve(), args.output.resolve(), args.generation), ensure_ascii=False))
