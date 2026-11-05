"""Inspect CE ELF writable sections against documented physical SRAM banks.

This is a host-only image check. It never opens a probe or changes a device.
DS14127 Table3 specifies WBA55CE SRAM1=32KiB and SRAM2=64KiB.
The WBA5 SRAM2 bank begins at0x20010000; these banks are not contiguous
on the512KiB CE part. A successful link into a128KiB RAM region is not
evidence that the intervening32KiB is supported.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

CE_BANKS = ((0x20000000, 0x20008000), (0x20010000, 0x20020000))
REFERENCES = (
    'https://www.st.com/resource/en/datasheet/stm32wba52ce.pdf',
    'https://www.st.com/resource/en/application_note/an6329-migrating-from-stm32wba5-to-stm32wba2-mcus-stmicroelectronics.pdf',
    'https://wiki.st.com/stm32mcu/wiki/Connectivity%3ASTM32WBA_Zigbee_memory_requirements',
)


def inspect_elf(path: Path) -> dict:
    """Return physical section coverage; malformed images raise ValueError.

    SHF_ALLOC|SHF_WRITE includes initialized data, NOBITS zero-fill and the
    reserved stack section. Disjoint valid sections are accepted; one section
    may not bridge the CE hole. No device memory is read to guess extra RAM.
    """
    data = path.read_bytes()
    if len(data) < 52 or data[:7] != b'\x7fELF\x01\x01\x01':
        raise ValueError('Expected ELF32 little-endian image')
    header = struct.unpack_from('<16sHHIIIIIHHHHHH', data)
    if header[2] != 40:
        raise ValueError('Expected ARM ELF machine40')
    shoff, shentsize, shnum, shstrndx = header[6], header[11], header[12], header[13]
    if not shnum or shentsize != 40 or shoff + shnum * shentsize > len(data):
        raise ValueError('Invalid or unsupported section table')
    sections = [struct.unpack_from('<10I', data, shoff + n * shentsize) for n in range(shnum)]
    if shstrndx >= shnum:
        raise ValueError('Invalid section string table')
    strings_section = sections[shstrndx]
    begin, length = strings_section[4:6]
    if begin + length > len(data):
        raise ValueError('Truncated section string table')
    strings = data[begin:begin + length]
    rows = []
    for section in sections:
        name_offset, kind, flags, address, offset, size = section[:6]
        if flags & 3 != 3 or not size:
            continue
        if name_offset >= len(strings):
            raise ValueError('Invalid section name')
        name_end = strings.find(b'\0', name_offset)
        if name_end < 0:
            raise ValueError('Unterminated section name')
        if kind != 8 and offset + size > len(data):
            raise ValueError('Truncated initialized section')
        end = address + size
        if end > 0x100000000:
            raise ValueError('Address overflow')
        covered = sum(max(0, min(end, hi) - max(address, lo)) for lo, hi in CE_BANKS)
        rows.append(dict(name=strings[name_offset:name_end].decode('ascii'),
                         address=address, end=end, bytes=size,
                         supportedBytes=covered, unsupportedBytes=size - covered,
                         whollyInsideOneBank=any(lo <= address < end <= hi for lo, hi in CE_BANKS)))
    if not rows:
        raise ValueError('No allocated writable sections')
    invalid = [row for row in rows if not row['whollyInsideOneBank']]
    return dict(result='CE_SRAM_LAYOUT_REJECTED' if invalid else 'CE_SRAM_SECTION_ADDRESSES_VALID',
                elf=str(path.resolve()), elfSha256=hashlib.sha256(data).hexdigest(),
                mcu='STM32WBA55CEU6', physicalSramBytes=98304,
                banks=[dict(begin=lo, end=hi, bytes=hi - lo) for lo, hi in CE_BANKS],
                sections=rows, invalidSections=invalid,
                writableSectionAddressesValid=not invalid,
                references=list(REFERENCES), hardwareOperations=0,
                limitations=['Address coverage does not prove startup zero/copy tables, retention, DMA access, stack headroom, shared-buffer lifetime or hardware behavior.',
                             'A valid result alone is not installation authorization; normal UART, identity, joint version, recording/BLE idle and image/NVM protections remain required.'])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('elf', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = inspect_elf(args.elf)
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        if args.output.exists():
            raise FileExistsError('Refuse to overwrite prior inspection')
        args.output.write_text(encoded, encoding='utf8')
    print(encoded, end='')
    return 0 if report['writableSectionAddressesValid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
