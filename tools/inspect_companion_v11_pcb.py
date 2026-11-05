#!/usr/bin/env python3
"""Read Altium PCB component/pad net assignments; never modify the PCB.

Uses olefile 0.47 installed in .cache/deps/altium-reader. Record offsets follow
KiCad's primary Altium parser (APAD6); this is a narrow reader, not a general
Altium importer or a copper-connectivity/DRC validator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.cache/deps/altium-reader'))
REFERENCE = 'https://raw.githubusercontent.com/KiCad/kicad-source-mirror/master/pcbnew/pcb_io/altium/altium_parser_pcb.cpp'


def block(data: bytes, offset: int) -> tuple[bytes, int]:
    if offset + 4 > len(data):
        raise ValueError('Truncated Altium subrecord length')
    size = struct.unpack_from('<I', data, offset)[0]
    end = offset + 4 + size
    if end > len(data):
        raise ValueError('Truncated Altium subrecord payload')
    return data[offset + 4:end], end


def properties(data: bytes) -> list[dict[str, str]]:
    rows, offset = [], 0
    while offset < len(data):
        row, offset = block(data, offset)
        text = row.rstrip(b'\0').decode('gb18030', errors='replace')
        rows.append(dict(field.split('=', 1) for field in text.split('|') if '=' in field))
    return rows


def inspect(path: Path) -> dict:
    import olefile
    with olefile.OleFileIO(path) as pcb:
        nets = properties(pcb.openstream('Nets6/Data').read())
        components = properties(pcb.openstream('Components6/Data').read())
        data = pcb.openstream('Pads6/Data').read()
    pads, offset = [], 0
    while offset < len(data):
        if data[offset] != 2:
            raise ValueError(f'Unsupported pad record type at byte {offset}')
        offset += 1
        subrecords = []
        for _ in range(6):
            record, offset = block(data, offset)
            subrecords.append(record)
        name, geometry = subrecords[0], subrecords[4]
        if not name or len(name) != name[0] + 1 or len(geometry) < 110:
            raise ValueError('Unsupported or truncated pad geometry/name')
        net_id = struct.unpack_from('<H', geometry, 3)[0]
        component_id = struct.unpack_from('<H', geometry, 7)[0]
        if net_id != 0xffff and net_id >= len(nets):
            raise ValueError('Pad refers to an absent net')
        if component_id != 0xffff and component_id >= len(components):
            raise ValueError('Pad refers to an absent component')
        component = components[component_id] if component_id != 0xffff else {}
        pads.append({'component': component.get('SOURCEDESIGNATOR'),
                     'pad': name[1:].decode('ascii'),
                     'net_index': net_id if net_id != 0xffff else None,
                     'net': nets[net_id].get('NAME') if net_id != 0xffff else None})
    model_properties = [
        {key: component.get(key) for key in
         ('SOURCEDESIGNATOR', 'SOURCELIBREFERENCE', 'PATTERN')}
        for component in components
        if any(part in component.get('SOURCELIBREFERENCE', '') for part in ('GDEY0154D67', 'STM32WBA'))]
    return {'schema': 'companion.altium.pcb-pad-net-evidence.v1',
            'source': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'reader_reference': REFERENCE,
            'scope': 'Logical pad-net assignments only; not copper continuity, DRC or assembled-board evidence',
            'net_count': len(nets), 'component_count': len(components), 'pad_count': len(pads),
            'model_properties': model_properties,
            'epd_reset_pads': [pad for pad in pads if pad['net'] == 'EPD_RES'],
            'nets': [{'index': i, 'name': net.get('NAME'),
                      'pads': [{'component': pad['component'], 'pad': pad['pad']}
                               for pad in pads if pad['net_index'] == i]}
                     for i, net in enumerate(nets)],
            'unconnected_pads': [pad for pad in pads if pad['net_index'] is None]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pcb', type=Path, default=Path(
        r'C:\Users\Billy\Desktop\Companion V1.1 2026_09_19\Companion V1.1\Companion V1.1.PcbDoc'))
    parser.add_argument('--output', type=Path, default=ROOT.parent /
                        'Companion-Hardware/electronics/companion-v1.1-2026-09-19/pcb-net-evidence.json')
    args = parser.parse_args()
    report = inspect(args.pcb)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in
          ('net_count', 'component_count', 'pad_count', 'model_properties', 'epd_reset_pads')}, ensure_ascii=False))
    print(args.output)


if __name__ == '__main__':
    main()
