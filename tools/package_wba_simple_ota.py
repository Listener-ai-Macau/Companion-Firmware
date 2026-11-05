#!/usr/bin/env python3
"""One signed CE App+UI file. No flashing, private-key copies or layout migration."""
from __future__ import annotations
import argparse, hashlib, json, struct, zlib
from pathlib import Path
from types import SimpleNamespace
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, encode_dss_signature
from sign_wba_update_manifest import load_private, public_xy, signed_prefix
from wba_flash_geometry import from_receipt

def sha(data): return hashlib.sha256(data).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--resource-image',type=Path,required=True)
    p.add_argument('--private-key',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build=a.build.resolve();source=a.source_root.resolve();out=a.output.resolve()
    r=json.loads((build/'result.json').read_bytes());g=from_receipt(r)
    app=(build/'companion-v11-board-bringup.bin').read_bytes();ui=a.resource_image.read_bytes()
    if (r.get('result')!='COMPILED_BUILD_ONLY' or not r.get('product_ble_linked') or
        r.get('ota_protocol')!='companion_simple_ota_v3' or g.mcu!='STM32WBA55CEU6' or
        g.boot_bytes not in (24576,32768) or int(r['load_address'],16)!=g.app_address or
        sha(app)!=r['bin_sha256'] or not 8<=len(app)<=g.app_bytes):
        raise ValueError('Need an exact minimal-OTA CE build and matched geometry')
    if not g.nvm_bytes and r.get('ble_bond_persistence',{}).get('backend')!='EXTERNAL_NOR_ONLY':
        raise ValueError('NVM0 App must use NOR-only pairing persistence')
    for name,wanted in r['source_sha256'].items():
        path=build/name.split('/',1)[1] if name.startswith('_external-build-output/') else source/name
        if name.startswith('_external-build-output/') and not path.exists():
            # Resource inputs may remain beside the explicitly supplied bank.
            # Verify their recorded hashes in place; do not copy them into the
            # build or rewrite its provenance receipt to satisfy packaging.
            leaf=name.split('/',1)[1]
            if leaf not in {'companion_wba_resource_contract.h','profile.json','ui-partition.bin'}:
                raise ValueError('Unknown external build input: '+name)
            path=a.resource_image.resolve().parent/leaf
        if sha(path.read_bytes())!=wanted:raise ValueError('Build source changed: '+name)
    profile=r['ui_resource_profile'];nor=r['flash_geometry'];static=nor['staticBytes']
    if len(ui)!=static or profile['uiPartitionBytes']!=static or sha(ui).upper()!=profile['uiPartitionSha256'].upper():
        raise ValueError('App/UI contract differs')
    key=load_private(a.private_key);xy=public_xy(key.public_key());trust=r['update_trust_anchor']
    if not trust['enabled'] or sha(xy)!=trust['public_key_sha256']:raise ValueError('Existing trust anchor differs')
    descriptor=struct.pack('<4sHH6I',b'CUP3',3,32,r['firmware_version'],profile['generation'],len(app),len(ui),static,g.app_address)
    body=descriptor+app+ui
    if 144+len(body)>nor['payloadBytes']:raise ValueError('Full package exceeds dynamic payload arena')
    args=SimpleNamespace(target='firmware',format_version=3,target_family=0x41425743,
        board_target=g.board_target,component_version=r['firmware_version'],minimum_app_version=0,
        maximum_app_version=0,key_id=trust['key_id'])
    prefix=signed_prefix(args,body);der=key.sign(prefix,ec.ECDSA(hashes.SHA256()));rv,sv=decode_dss_signature(der)
    key.public_key().verify(encode_dss_signature(rv,sv),prefix,ec.ECDSA(hashes.SHA256()))
    signed=prefix+rv.to_bytes(32,'big')+sv.to_bytes(32,'big');header=signed+struct.pack('<I',zlib.crc32(signed))
    file=header+body;assert len(header)==144
    if out.exists() and any(out.iterdir()):raise ValueError('Output must be new or empty')
    out.mkdir(parents=True,exist_ok=True);(out/'companion-update.cup').write_bytes(file)
    # The only transferred file carries its own signature. JSON is a host
    # locator/consistency description, not another cryptographic envelope.
    dev=(a.private_key.parent/'DEV_ONLY.txt').exists() or a.private_key.name=='wba-update-dev-private.pem'
    manifest=dict(schema='companion.wba.simple-ota.v3',package_type='companion-system-ota',
        capability='companion_simple_ota_v3',mcu=g.mcu,hardware_revision=g.hardware_revision,
        internal_flash_geometry=g.receipt(),board_target=g.board_target,app_address=g.app_address,
        file='companion-update.cup',bytes=len(file),sha256=sha(file),payload_sha256=sha(body),
        firmware_version=r['firmware_version'],resource_version=profile['generation'],
        firmware_bytes=len(app),resource_bytes=len(ui),static_bytes=static,
        key_id=trust['key_id'],public_key_sha256=sha(xy),dev_only=dev or r.get('development_ota_power_unrestricted',False),
        download_resume=False,interrupted_install='restart_from_retained_full_package',
        hardwareAcceptance='NOT_RUN',fullChainAcceptance='NOT_RUN')
    (out/'ota_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    # Factory initial provisioning uses this same signed header after exact
    # destination readback. The file itself remains the future OTA input.
    (out/'current-package-header.bin').write_bytes(file[:176])
    print(out/'ota_manifest.json')
if __name__=='__main__':main()
