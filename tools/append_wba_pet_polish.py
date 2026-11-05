#!/usr/bin/env python3
"""Bind selected original-style pet faces and ornaments into a NEW resource bank.

This offline producer keeps all existing state pixels and atlas bytes. Its
profile/headers require a matching App+Boot and media geometry installation;
it is never an ordinary resource update for an already formatted older board.
"""
import argparse
import copy
import hashlib
import json
import re
import shutil
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/faraday_upper_art'))
from build_ui_asset_generation import encode_packbits, fnv1a32
from wba_resource_geometry import geometry, choose_static_bytes

FACES = ('dejected', 'protest', 'nervous', 'proud')
CHARMS = ('double-heart', 'music-note', 'sprout', 'flower-r3', 'little-puff')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode())


def replace_number(text, name, value):
    text, count = re.subn(r'(' + re.escape(name) + r' )\d+u', r'\g<1>' + str(value) + 'u', text)
    if count != 1:
        raise ValueError('Missing or ambiguous contract constant: ' + name)
    return text


def build(base, emotion_art, charm_art, puff_art, out, generation, direction_art=None):
    if out.exists():
        raise ValueError('Use a fresh candidate directory; never overwrite an earlier bank')
    profile = json.loads((base / 'profile.json').read_bytes())
    bank = (base / 'ui-partition.bin').read_bytes()
    if generation <= profile['generation'] or sha(bank).upper() != profile['uiPartitionSha256'].upper():
        raise ValueError('Base identity or generation mismatch')
    old_geometry = geometry(len(bank), profile['flashGeometry']['norBytes'])
    if old_geometry != profile['flashGeometry']:
        raise ValueError('Base geometry mismatch')
    root = bytearray(bank[old_geometry['rootA']:old_geometry['rootA'] + 128])
    if root[:4] != b'CUIR' or zlib.crc32(root[:124]) != struct.unpack_from('<I', root, 124)[0]:
        raise ValueError('Invalid base resource root')
    bo, bs = struct.unpack_from('<II', root, 16)
    mo, ms, mc = struct.unpack_from('<III', root, 28)
    old_blob = bank[bo:bo + bs]
    manifest = bytearray(old_blob[:ms])
    if mo or manifest[:4] != b'CUIM' or zlib.crc32(manifest) != mc or zlib.crc32(old_blob) != struct.unpack_from('<I', root, 24)[0]:
        raise ValueError('Invalid base manifest/blob')
    count, row_bytes = struct.unpack_from('<HH', manifest, 8)
    if row_bytes != 24 or ms != 32 + count * row_bytes or count != profile['stateCount']:
        raise ValueError('Unsupported manifest layout')
    old_rows = [list(struct.unpack_from('<IHHIIHHI', manifest, 32 + i * 24)) for i in range(count)]
    if any(a[0] >= b[0] for a, b in zip(old_rows, old_rows[1:])):
        raise ValueError('Unsorted/duplicate source states')
    face_sources = [(name, emotion_art / (name + '-frame.bin')) for name in FACES]
    if direction_art is not None:
        face_sources += [(name+'_'+direction, direction_art/(name+'-'+direction+'-frame.bin'))
            for name in FACES for direction in ('left','right')]
    shift = 24 * len(face_sources)
    rows = copy.deepcopy(old_rows)
    for row in rows:
        if row[2]:
            if not (bo + ms <= row[4] and row[4] + row[5] <= bo + bs):
                raise ValueError('Original payload outside resource blob')
            if zlib.crc32(bank[row[4]:row[4] + row[5]]) != row[7]:
                raise ValueError('Original payload CRC mismatch')
            row[4] += shift
    face_bytes = bytearray()
    additions = []
    hashes = {row[0] for row in rows}
    for name, source_frame in face_sources:
        state = 'pet_emotion_' + name
        h = fnv1a32(state)
        frame = source_frame.read_bytes()
        if h in hashes or len(frame) != 5000 or frame[:400] != b'\xff' * 400:
            raise ValueError('Invalid/duplicate whole-face candidate: ' + name)
        packed = encode_packbits(frame)
        offset = bo + bs + shift + len(face_bytes)
        rows.append([h, 65535, 2, zlib.crc32(frame), offset, len(packed), 1000, zlib.crc32(packed)])
        face_bytes.extend(packed)
        hashes.add(h)
        additions.append(dict(state=state, frameSha256=sha(frame), payloadBytes=len(packed),
            payloadOffset=offset, closedEyesMask=1 if name.startswith('proud') else 0))

    old_external = profile['externalUi']
    old_ao = old_external['extensionOffset']
    ao = old_ao + shift
    selected = json.loads((charm_art / 'selected-payloads.json').read_bytes())
    selected_by_id = {row['id']: row for row in selected['selectedCandidates']}
    charm_bytes = bytearray()
    charm_rows = []
    refs = []
    for index, name in enumerate(CHARMS, 1):
        if name == 'little-puff':
            source = puff_art / 'little-puff-ornament-spans.bin'
        else:
            source = charm_art / selected_by_id[name]['payload']
        data = source.read_bytes()
        if not data or len(data) % 3 or len(data) > 256:
            raise ValueError('Unsupported ornament payload: ' + name)
        for x, y, width in zip(data[::3], data[1::3], data[2::3]):
            if not width or x < 112 or x + width > 191 or not 20 <= y <= 64:
                raise ValueError('Ornament outside canonical dock: ' + name)
        absolute = bo + bs + shift + len(face_bytes) + len(charm_bytes)
        relative = absolute - ao
        if relative + len(data) > 65535:
            raise ValueError('External UI reference exceeds16-bit format')
        refs.append('{%du,%du,0x%08Xu}' % (relative, len(data), zlib.crc32(data)))
        charm_rows.append(dict(id=name, catalogId=index, source=str(source), bytes=len(data),
            sha256=sha(data), relativeOffset=relative, absoluteOffset=absolute))
        charm_bytes.extend(data)

    rows.sort(key=lambda row: row[0])
    struct.pack_into('<H', manifest, 8, count + len(face_sources))
    struct.pack_into('<I', manifest, 12, ms + shift)
    new_manifest = bytes(manifest[:32]) + b''.join(struct.pack('<IHHIIHHI', *row) for row in rows)
    blob = new_manifest + old_blob[ms:] + face_bytes + charm_bytes
    used = bo + len(blob)
    geo = geometry(choose_static_bytes(used, old_geometry['norBytes']), old_geometry['norBytes'])
    identity = sha(bytes.fromhex(profile['resourceId']) + b'Companion pet polish P105\0' + blob).upper()
    struct.pack_into('<I', root, 8, generation)
    struct.pack_into('<II', root, 20, len(blob), zlib.crc32(blob))
    struct.pack_into('<II', root, 32, len(new_manifest), zlib.crc32(new_manifest))
    struct.pack_into('<I', root, 40, (used + 4095) & ~4095)
    root[44:76] = bytes.fromhex(identity)
    struct.pack_into('<I', root, 124, zlib.crc32(root[:124]))
    new_bank = bytearray(b'\xff' * geo['staticBytes'])
    new_bank[:bo] = bank[:bo]
    new_bank[bo:used] = blob
    new_bank[geo['rootA']:geo['rootA'] + 128] = root
    external = bytes(new_bank[ao:used])
    if new_bank[:bo] != bank[:bo] or new_bank[bo + ms + shift:bo + bs + shift] != old_blob[ms:]:
        raise ValueError('Existing resource bytes changed during production')
    indexed = {row[0]: row for row in rows}
    for before in old_rows:
        after = indexed[before[0]]
        if before[:4] != after[:4] or before[5:] != after[5:]:
            raise ValueError('Original state contract changed')
        if before[2] and new_bank[after[4]:after[4] + after[5]] != bank[before[4]:before[4] + before[5]]:
            raise ValueError('Original state pixels changed')

    out.mkdir(parents=True)
    for p in base.glob('*.h'):
        shutil.copyfile(p, out / p.name)
    header = (base / 'companion_wba_external_ui.h').read_text(encoding='utf8')
    header = replace_number(header, 'COMP_WBA_EXTERNAL_UI_OFFSET', ao)
    header = replace_number(header, 'COMP_WBA_EXTERNAL_UI_BYTES', len(external))
    header, n = re.subn(r'(COMP_WBA_EXTERNAL_UI_CRC32 )0x[0-9A-Fa-f]+u',
        r'\g<1>0x%08Xu' % zlib.crc32(external), header)
    if n != 1:
        raise ValueError('Missing external UI CRC contract')
    old_max = int(re.search(r'COMP_WBA_EXTERNAL_MAX_ACCESSORY_BYTES (\d+)u', header)[1])
    maximum = max(old_max, *(row['bytes'] for row in charm_rows))
    header = replace_number(header, 'COMP_WBA_EXTERNAL_MAX_ACCESSORY_BYTES', maximum)
    (out / 'companion_wba_external_ui.h').write_text(header, encoding='utf8', newline='\n')
    catalog = ('/* Generated P105 charm references, bound to this resource bank only. */\n'
        '#ifndef COMPANION_PET_CHARM_CATALOG_H\n#define COMPANION_PET_CHARM_CATALOG_H\n'
        '#define COMP_PET_CHARM_NONE 0u\n#define COMP_PET_CHARM_HEARTS 1u\n'
        '#define COMP_PET_CHARM_NOTE 2u\n#define COMP_PET_CHARM_SPROUT 3u\n'
        '#define COMP_PET_CHARM_FLOWER 4u\n#define COMP_PET_CHARM_PUFF 5u\n'
        '#define COMP_PET_CHARM_COUNT 5u\n'
        'static const comp_wba_external_bitmap_t comp_pet_charms[COMP_PET_CHARM_COUNT]={' + ','.join(refs) + '};\n#endif\n')
    (out / 'companion_pet_charm_catalog.h').write_text(catalog, encoding='ascii', newline='\n')
    contract = (base / 'companion_wba_resource_contract.h').read_text(encoding='utf8')
    contract = replace_number(contract, 'COMPANION_WBA_RESOURCE_GENERATION', generation)
    contract = replace_number(contract, 'COMPANION_WBA_RESOURCE_STATE_COUNT', count + len(face_sources))
    contract = contract.replace(profile['resourceId'], identity)
    for name in ('COMPANION_WBA_PET_EMOTION_ACCENTS_V2', 'COMPANION_WBA_PET_PROUD_ACCENT_V3', 'COMPANION_WBA_PET_CHARMS_V1'):
        if name in contract:
            raise ValueError('Base already advertises this addition: ' + name)
    contract = contract.replace('#include <stdint.h>', '#include <stdint.h>\n'
        '#define COMPANION_WBA_PET_EMOTION_ACCENTS_V2 1\n'
        '#define COMPANION_WBA_PET_PROUD_ACCENT_V3 1\n'
        '#define COMPANION_WBA_PET_CHARMS_V1 1')
    if direction_art is not None:
        contract = contract.replace('#include <stdint.h>', '#include <stdint.h>\n'
            '#define COMPANION_WBA_PET_EMOTION_DIRECTIONS_V4 1')
    (out / 'companion_wba_resource_contract.h').write_text(contract, encoding='utf8', newline='\n')
    (out / 'ui-partition.bin').write_bytes(new_bank)
    result = dict(schema='companion.pet-polish-resource.v1', generation=generation,
        baseGeneration=profile['generation'], oldStateCount=count, newStateCount=len(rows),
        faces=additions, charms=charm_rows, originalStatePixelsPreserved=True,
        originalAtlasAndPayloadBytesPreserved=True, cempUnchanged=True,
        addedFramePayloadBytes=len(face_bytes), addedOrnamentBytes=len(charm_bytes),
        oldGeometry=old_geometry, newGeometry=geo, geometryChanged=geo != old_geometry,
        pairedAppBootGeometryRequired=True, ordinaryOldGeometryOtaAllowed=False,
        resourceArenaUsedBytes=used, arenaFreeBytes=geo['rootA'] - used,
        maxAccessoryBytes=maximum, imageSha256=sha(new_bank),
        fullFirmwareBuilt=False, installed=False, physicalQualified=False, testsRun=False)
    updated_external = copy.deepcopy(old_external)
    updated_external.update(extensionOffset=ao, extensionBytes=len(external),
        headerSha256=sha((out / 'companion_wba_external_ui.h').read_bytes()),
        maxAccessoryBytes=maximum, generation=generation, newBankSha256=sha(new_bank))
    if 'addedOffset' in updated_external:
        updated_external['addedOffset'] += shift
    profile.update(generation=generation, resourceId=identity,
        uiPartitionBytes=len(new_bank), uiPartitionSha256=sha(new_bank).upper(),
        resourceArenaUsedBytes=used, resourceBudgetBytes=len(new_bank), flashGeometry=geo,
        stateCount=len(rows), generationBytes=len(blob), externalUi=updated_external,
        generationPatchBytes=profile.get('generationPatchBytes', 0) + len(face_bytes),
        petPolish=result, recordingRegionPreserved=False, dynamicRegionIncluded=False,
        hardwareAcceptance='NOT_RUN', fullChainAcceptance='NOT_RUN', result='RESOURCE_CANDIDATE_BUILT')
    for p in [Path(__file__), *(out.glob('*.h'))]:
        profile.setdefault('sourceSha256', {})[str(p)] = sha(p.read_bytes()).upper()
    dump(out / 'profile.json', profile)
    dump(out / 'pet-polish.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('base', 'emotion-art', 'charm-art', 'puff-art', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--generation', required=True, type=int)
    parser.add_argument('--direction-art', type=Path)
    args = parser.parse_args()
    result = build(args.base.resolve(), args.emotion_art.resolve(), args.charm_art.resolve(),
        args.puff_art.resolve(), args.output.resolve(), args.generation,
        args.direction_art.resolve() if args.direction_art else None)
    print(json.dumps({k: result[k] for k in ('generation', 'newStateCount', 'addedFramePayloadBytes',
        'addedOrnamentBytes', 'newGeometry', 'imageSha256', 'installed')}, ensure_ascii=False))
