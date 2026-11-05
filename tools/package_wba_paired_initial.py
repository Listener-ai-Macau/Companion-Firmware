"""Prepare a matched CE Boot/App/UI and signed initial CFC2 receipt, offline.

The receipt authorizes the exact signed pair; resident Boot still verifies the
actual destinations before jumping. Provisioners must verify both destinations
before publishing CFC2, preserve settings/NVM and hold the shared board lease.
This tool never opens a probe, formats media, or copies a private key.
"""
from pathlib import Path
import argparse, hashlib, json, shutil, struct, zlib
from wba_flash_geometry import from_receipt
from wba_system_bundle import verify_bundle, CAPABILITY

def sha(data):
    return hashlib.sha256(data).hexdigest()

def confirmed_sector(wire: bytes, sequence: int = 1) -> bytes:
    if len(wire) != 452 or wire[:6] != b'WSB2\x02\x01' or not 0 < sequence < 1 << 64:
        raise ValueError('A signed v2 pair and nonzero sequence are required')
    if struct.unpack_from('<I', wire, 448)[0] != zlib.crc32(wire[:448]):
        raise ValueError('Pair wire CRC differs')
    record = b'CFC2\x01\x01\xd8\x01' + struct.pack('<Q', sequence) + wire
    record += struct.pack('<I', zlib.crc32(record))
    assert len(record) == 472
    return record.ljust(4096, b'\xff')

def workspace_sector(geometry: dict) -> bytes:
    record = bytearray(64)
    record[:4] = b'CFL3'
    struct.pack_into('<7I', record, 4, 3, 64, geometry['staticBytes'],
                     geometry['dynamicBase'], geometry['recordingCatalog'],
                     geometry['payloadBase'], geometry['payloadBytes'])
    struct.pack_into('<I', record, 60, zlib.crc32(record[:60]))
    return bytes(record).ljust(4096, b'\xff')

def package(app_dir: Path, boot_dir: Path, bundle_path: Path, output: Path, sequence: int = 1):
    app = json.loads((app_dir/'result.json').read_bytes())
    boot = json.loads((boot_dir/'result.json').read_bytes())
    envelope = json.loads(bundle_path.read_bytes())
    d = envelope['descriptor']
    geometry = from_receipt(app)
    xy = (bundle_path.parent/'firmware/update-public.xy').read_bytes()
    verify_bundle(bundle_path, xy)
    if geometry.flash_kib != 512 or from_receipt(boot) != geometry or from_receipt(d) != geometry:
        raise ValueError('All components must target the same physical CE layout')
    if app.get('result') != 'COMPILED_BUILD_ONLY' or app.get('error') or boot.get('result') != 'PASS':
        raise ValueError('Exact successful App and Boot builds are required')
    if not all(x.get('sram_inspection', {}).get('writableSectionAddressesValid') for x in (app, boot)):
        raise ValueError('Allocated sections escape physical CE SRAM')
    if (boot.get('system_pair_protocol') != CAPABILITY or
        not boot.get('requires_initial_signed_pair_receipt') or
        not boot.get('requires_matched_paired_receiver_app')):
        raise ValueError('Use the new paired Boot, not a legacy single-component Boot')
    image = (app_dir/'companion-v11-board-bringup.bin').read_bytes()
    resident = (boot_dir/'companion_wba55_v11_boot.bin').read_bytes()
    if (sha(image) != app['bin_sha256'] or sha(resident) != boot['bin_sha256'] or
        len(resident) > geometry.boot_bytes or len(image) > geometry.app_bytes or
        boot['installed_image_size'] != len(image) or
        app['firmware_version'] != boot['firmware_version'] or
        d['components']['firmware']['sha256'] != sha(image) or
        d['components']['firmware']['version'] != app['firmware_version']):
        raise ValueError('Boot, App and signed pair identities differ')
    if (app['update_trust_anchor']['public_key_sha256'] != sha(xy) or
        boot['public_key_sha256'] != sha(xy) or
        boot['key_id'] != app['update_trust_anchor']['key_id'] or
        boot['flash_geometry'] != app['flash_geometry'] or
        d['flash_geometry'] != app['flash_geometry']):
        raise ValueError('Trust anchor or resource geometry differs')
    ui = (bundle_path.parent/d['components']['resources']['file']).read_bytes()
    profile = app['ui_resource_profile']
    if (len(ui) != profile['uiPartitionBytes'] or
        sha(ui).upper() != profile['uiPartitionSha256'].upper() or
        d['resource_contract']['resourceId'] != profile['resourceId']):
        raise ValueError('App/UI resource identity differs')
    combined = resident.ljust(geometry.boot_bytes, b'\xff') + image
    for offset, size in ((0, len(resident)), (geometry.boot_bytes, len(image))):
        sp, reset = struct.unpack_from('<II', combined, offset)
        if not (geometry.valid_stack_pointer(sp) and reset & 1 and
                geometry.flash_base+offset <= reset & ~1 < geometry.flash_base+offset+size):
            raise ValueError('Invalid physical CE vector')
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output must be new or empty')
    output.mkdir(parents=True, exist_ok=True)
    wire = (bundle_path.parent/'system-transaction.wsb').read_bytes()
    payloads = {'initial-boot-and-app.bin': combined, 'app.bin': image,
                'boot.bin': resident, 'ui-partition.bin': ui,
                'confirmed-sector.bin': confirmed_sector(wire,sequence),
                'workspace-sector.bin': workspace_sector(app['flash_geometry'])}
    for name, data in payloads.items():
        (output/name).write_bytes(data)
    for name, path in (('app-build.json', app_dir/'result.json'),
                       ('boot-build.json', boot_dir/'result.json')):
        shutil.copy2(path, output/name)
    shutil.copytree(bundle_path.parent, output/'signed-pair')
    receipt = dict(schema='companion.wba.paired-initial.v1',
        result='MATCHED_INITIAL_PACKAGE_SOFTWARE_ONLY', mcu=geometry.mcu,
        internal_flash_geometry=geometry.receipt(), flash_geometry=app['flash_geometry'],
        firmware_version=app['firmware_version'], resource_generation=profile['generation'],
        bundle_id=envelope['bundle_id'], confirmed_sequence=sequence,
        files={name:dict(bytes=len(data),sha256=sha(data)) for name,data in payloads.items()},
        confirmed_offsets=[app['flash_geometry']['staticBytes']+0xA000, app['flash_geometry']['staticBytes']+0xB000],
        layout_offsets=[app['flash_geometry']['staticBytes']+0x8000, app['flash_geometry']['staticBytes']+0x9000],
        initial_receipt_publish_requires_full_destination_readback=True,
        preserve_settings=True, preserve_pairing_nvm=True,
        board_recordings='Development clear only under explicit Owner authorization; no automatic production discard',
        installed=False, physicalQualified=False, hardwareOperations=0)
    (output/'manifest.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return receipt

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('app','boot','bundle','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--confirmed-sequence',type=int,default=1,
                   help='Provisioner must verify any existing signed receipt and require monotonic sequence/components')
    a=p.parse_args()
    receipt=package(a.app.resolve(),a.boot.resolve(),a.bundle.resolve(),a.output.resolve(),a.confirmed_sequence)
    print(json.dumps(dict(result=receipt['result'],bundleId=receipt['bundle_id'],output=str(a.output))))

if __name__ == '__main__':
    main()
