"""Read this board's saved SNVMA snapshot for subsequent offline BLE MIC analysis.

No device access, key printing, Windows credential access or NVM modification.
The host buffer is opaque; a candidate is never called a bond key until actual
target RF independently authenticates it. The SDK CRC is not that MIC proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

NVM_OFFSET = 0x7C000
BANK_BYTES = 8192
HEADER = struct.Struct('<BBHBHBHBHBH')


def crc_words(data: bytes, crc: int = 0xFFFF) -> int:
    """ST crc_ctrl_conf.c: 16-bit poly7607, no inversion, WORDS input."""
    if len(data) % 4:
        raise ValueError('SNVMA buffer must contain whole uint32 words')
    for start in range(0, len(data), 4):
        # STM32 CRC_DR consumes each little-endian uint32 most-significant bit first.
        for value in data[start:start + 4][::-1]:
            crc ^= value << 8
            for _ in range(8):
                crc = ((crc << 1) ^ (7607 if crc & 0x8000 else 0)) & 0xFFFF
    return crc


def bank(data: bytes, index: int) -> tuple[dict, list[bytes] | None]:
    raw = data[index * BANK_BYTES:(index + 1) * BANK_BYTES]
    if len(raw) != BANK_BYTES:
        raise ValueError('Incomplete SNVMA bank')
    if raw[:16] == b'\xff' * 16:
        return {'index': index, 'erased': True, 'valid': False}, None
    _, counter, stored_crc, *fields = HEADER.unpack_from(raw)
    pairs = list(zip(fields[::2], fields[1::2]))
    if [x[0] for x in pairs] != [0, 1, 2, 3]:
        raise ValueError('SNVMA IDs differ from this WBA configuration')
    cursor, crc, buffers = 16, 0xFFFF, []
    for _, words in pairs:
        size = words * 4
        if cursor + size > BANK_BYTES:
            raise ValueError('SNVMA buffer exceeds its actual bank')
        buffer = raw[cursor:cursor + size]
        if words:
            crc = crc_words(buffer, crc)
        buffers.append(buffer)
        cursor += (size + 15) & ~15
    row = dict(index=index, erased=False, counter=counter,
               bufferBytes=[len(x) for x in buffers], crcVerified=crc == stored_crc,
               valid=crc == stored_crc)
    return row, buffers if row['valid'] else None


def load_owned_snapshot(directory: Path, expected_uid: str) -> tuple[bytes, dict]:
    directory = directory.resolve()
    result = json.loads((directory / 'result.json').read_text(encoding='utf-8-sig'))
    uid = (directory / 'uid.bin').read_bytes().hex()
    if len(expected_uid) != 24 or uid != expected_uid.lower() or result['requiredUid'] != uid:
        raise ValueError('Saved installation UID is not the explicitly requested board')
    if result['result'] != 'MINIMAL_INITIAL_INSTALLED_NORMAL_NOT_WIRELESS_OTA':
        raise ValueError('Installation snapshot has no verified completed provenance')
    before = (directory / 'private-internal-before.bin').read_bytes()
    after = (directory / 'private-internal-after.bin').read_bytes()
    if len(before) != 524288 or len(after) != 524288:
        raise ValueError('Expected exact CE internal Flash images')
    nvm = before[NVM_OFFSET:]
    digest = hashlib.sha256(nvm).hexdigest()
    if after[NVM_OFFSET:] != nvm or digest != result['liveNvmSha256']:
        raise ValueError('NVM does not match the preserved installation snapshot')
    banks = [bank(nvm, i) for i in range(2)]
    valid = [(row, buffers) for row, buffers in banks if buffers is not None]
    if not valid:
        raise ValueError('No SDK-CRC-qualified SNVMA bank in this snapshot')
    chosen = valid[0]
    for candidate in valid[1:]:
        a, b = chosen[0]['counter'], candidate[0]['counter']
        # Match pinned SDK simple_nvm_arbiter.c:GetNewestBank exactly.
        if a < b and b - a != 0xFF:
            chosen = candidate
    host = chosen[1][0]
    if len(host) != 2032 or len(chosen[1][1]) != 48:
        raise ValueError('Host/identity buffer sizes differ from the installed source')
    identity = chosen[1][1]
    if int.from_bytes(identity[:4], 'little') != 0x31494243 or identity[41] & 0xC0 != 0xC0:
        raise ValueError('Saved application BLE identity is not initialized')
    address = ':'.join(f'{x:02X}' for x in identity[36:42][::-1])
    report = dict(schema='companion.wba.saved_nvm_air_analysis.v1',
                  deviceUid=uid, deviceAddress=address, installedFirmware=result['targetFirmware'],
                  sourceCommit=result['sourceCommit'], nvmSha256=digest,
                  banks=[x[0] for x in banks], selectedBank=chosen[0]['index'],
                  hostBufferBytes=len(host), hostBufferSha256=hashlib.sha256(host).hexdigest(),
                  sdkCrcQualified=True, independentlyRfMicQualified=False,
                  keyMaterialExported=False, deviceOperations=0,
                  scope='Opaque host buffer from this board only. Actual RF/MIC proof is required before admitting any key or decrypted throughput.')
    return host, report


def candidates(host: bytes):
    """Bounded candidate representations, used only against saved target RF.

    Host-stack record offsets are proprietary, so no guessed offset is trusted.
    Reject erased/constant material, deduplicate and require actual MIC later.
    The board identity/root-key buffer is deliberately outside this search.
    """
    seen = set()
    for offset in range(len(host) - 15):
        value = host[offset:offset + 16]
        if len(set(value)) < 8:
            continue
        for reverse in (False, True):
            key = value[::-1] if reverse else value
            if key not in seen:
                seen.add(key)
                yield offset, reverse, key


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--installation-dir', type=Path, required=True)
    p.add_argument('--uid', required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    host, report = load_owned_snapshot(args.installation_dir, args.uid)
    report['untrustedCandidateRepresentations'] = sum(1 for _ in candidates(host))
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
