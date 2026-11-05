#!/usr/bin/env python3
"""Create a Type-compatible, signed WBA app OTA package from an exact build.

This never flashes a device. The build version is signed verbatim; rebuild with
an increased --firmware-version for an upgrade. Private keys are never copied.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from cryptography.hazmat.primitives import serialization
from wba_flash_geometry import from_receipt

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--private-key',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--source-root',type=Path,help='Exact frozen source root recorded by this build; output-generated sources are resolved inside --build')
    selection=p.add_mutually_exclusive_group()
    selection.add_argument('--resource-image',type=Path,help='Package the UI bank bound to this app instead of the app payload')
    selection.add_argument('--system-resource-image',type=Path,help='Create one signed matched firmware+resource bundle; requires the future atomic device installer, never send through two independent OTA activations')
    args=p.parse_args()
    if args.system_resource_image:
        package_system(args)
        return
    build=args.build.resolve();out=args.output.resolve()
    source_root=(args.source_root or ROOT).resolve()
    receipt=json.loads((build/'result.json').read_text())
    geometry=from_receipt(receipt)
    image=build/'companion-v11-board-bringup.bin';payload=image.read_bytes()
    sha=hashlib.sha256(payload).hexdigest()
    if receipt.get('result') not in ('PASS_PREHARDWARE_SOFTWARE_ONLY','COMPILED_BUILD_ONLY') or not receipt.get('product_ble_linked') or \
       int(receipt.get('load_address','0'),16)!=geometry.app_address or receipt.get('bin_sha256')!=sha or len(payload)>geometry.app_bytes:
        raise RuntimeError('Need a successful, exact relocated WBA product build')
    trust=receipt['update_trust_anchor']
    key=serialization.load_pem_private_key(args.private_key.read_bytes(),password=None)
    pub=key.public_key().public_numbers()
    xy=pub.x.to_bytes(32,'big')+pub.y.to_bytes(32,'big')
    if not trust['enabled'] or hashlib.sha256(xy).hexdigest()!=trust['public_key_sha256']:
        raise RuntimeError('Signing key does not match this build trust anchor')
    for source,expected in receipt['source_sha256'].items():
        source_path = build/source.split('/',1)[1] if source.startswith('_external-build-output/') else source_root/source
        if hashlib.sha256(source_path.read_bytes()).hexdigest()!=expected:
            raise RuntimeError(f'Build source changed: {source}')
    resource=args.resource_image is not None
    version=receipt['firmware_version']
    if resource:
        profile=receipt['ui_resource_profile']
        image=args.resource_image.resolve();payload=image.read_bytes();sha=hashlib.sha256(payload).hexdigest()
        if len(payload)!=profile['uiPartitionBytes'] or sha.upper()!=profile['uiPartitionSha256'].upper():
            raise RuntimeError('UI image does not match this app resource contract')
        version=profile['generation']
    if out.exists() and any(out.iterdir()):raise RuntimeError('Output must be new or empty')
    out.mkdir(parents=True,exist_ok=True)
    binary=out/('ui-partition.bin' if resource else 'firmware_ota.bin');shutil.copy2(image,binary)
    wire=out/'wba_manifest.bin'
    subprocess.run([sys.executable,str(ROOT/'tools/sign_wba_update_manifest.py'),'sign',
        '--payload',str(binary),'--private-key',str(args.private_key.resolve()),'--output',str(wire),
        '--public-xy',str(out/'update-public.xy'),'--target','ui-assets' if resource else 'firmware','--format-version','2' if resource else '1',
        '--target-family','0x41425743','--board-target',hex(geometry.board_target),
        '--component-version',str(version),'--key-id',str(trust['key_id']),
        *(['--minimum-app-version',str(receipt['firmware_version']),'--maximum-app-version',str(receipt['firmware_version'])] if resource else [])],check=True)
    signing=json.loads(wire.with_suffix('.bin.json').read_text())
    manifest={'schema_version':1,'package_type':'companion-resource-ota' if resource else 'companion-firmware-ota',
        'hardware_revision':geometry.hardware_revision,'mcu':geometry.mcu,
        'internal_flash_geometry':geometry.receipt(),
        'dev_only':signing['dev_only'] or receipt.get('development_ota_power_unrestricted',False),
        'development_overrides':{'ota_power_unrestricted':receipt.get('development_ota_power_unrestricted',False)},
        'flash_geometry':receipt.get('flash_geometry'),
        'component_version':version,'wba_manifest_hex':wire.read_bytes().hex(),
        'file':{'name':binary.name,'size_bytes':len(payload),'sha256':sha},
        'protocol':{'name':'denzic_ota_v1','version':1,'firmware_capability':'denzic_ota_v1',
            'gatt':{'service_uuid':'1b55f597-f09c-4c7f-9529-adfa64983b06',
                'control_uuid':'206c5e29-c64d-4392-8180-66463788533c',
                'data_uuid':'fbc4b0fb-6102-4bd1-abe4-e5e90a9a7e12',
                'status_uuid':'e571544a-7c41-4650-b0d6-ccebfe1db489','chunk_bytes':240}},
        'hardwareAcceptance':'NOT_RUN','fullChainAcceptance':'NOT_RUN'}
    (out/'ota_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(out/'ota_manifest.json')

def package_system(args):
    from wba_system_bundle import sign_descriptor, sign_device_wire, verify_bundle, sha, SCHEMA, CAPABILITY, ACTIVATION_CONTRACT, DEVICE_WIRE_CONTRACT
    from cryptography.hazmat.primitives.asymmetric import ec
    out=args.output.resolve()
    if out.exists() and any(out.iterdir()):raise RuntimeError('Output must be new or empty')
    out.mkdir(parents=True,exist_ok=True)
    manifests={}
    for name in ('firmware','resources'):
        command=[sys.executable,str(Path(__file__).resolve()),'--build',str(args.build.resolve()),'--private-key',str(args.private_key.resolve()),'--output',str(out/name)]
        if args.source_root:command+=['--source-root',str(args.source_root.resolve())]
        if name=='resources':command+=['--resource-image',str(args.system_resource_image.resolve())]
        subprocess.run(command,check=True)
        manifests[name]=json.loads((out/name/'ota_manifest.json').read_bytes())
    fw,ui=manifests['firmware'],manifests['resources']
    if fw['internal_flash_geometry']!=ui['internal_flash_geometry'] or fw['flash_geometry']!=ui['flash_geometry']:raise RuntimeError('Components use different layouts')
    key=serialization.load_pem_private_key(args.private_key.read_bytes(),password=None)
    if not isinstance(key,ec.EllipticCurvePrivateKey) or not isinstance(key.curve,ec.SECP256R1):raise RuntimeError('System bundle requires the existing P-256 key')
    numbers=key.public_key().public_numbers();xy=numbers.x.to_bytes(32,'big')+numbers.y.to_bytes(32,'big')
    build=json.loads((args.build/'result.json').read_bytes())
    profile=dict(build['ui_resource_profile'],storageLayoutVersion=3,flashGeometry=build['flash_geometry'])
    components={}
    for name,m in manifests.items():
        file=m['file'];shutil.copy2(out/name/file['name'],out/file['name'])
        components[name]=dict(file=file['name'],bytes=file['size_bytes'],sha256=file['sha256'],version=m['component_version'],wba_manifest_hex=m['wba_manifest_hex'])
    descriptor=dict(schema=SCHEMA,package_type='companion-system-ota',requires_device_capability=CAPABILITY,
        mcu=fw['mcu'],hardware_revision=fw['hardware_revision'],internal_flash_geometry=fw['internal_flash_geometry'],flash_geometry=fw['flash_geometry'],
        key_id=build['update_trust_anchor']['key_id'],public_key_sha256=sha(xy),dev_only=fw['dev_only'] or ui['dev_only'],
        resource_contract=profile,components=components,
        development_overrides=fw.get('development_overrides',{}),
        activation_contract=dict(ACTIVATION_CONTRACT),device_wire_contract=dict(DEVICE_WIRE_CONTRACT))
    path=out/'system_bundle.json';path.write_text(json.dumps(sign_descriptor(descriptor,key),indent=2)+'\n',encoding='utf-8')
    (out/DEVICE_WIRE_CONTRACT['file']).write_bytes(sign_device_wire(descriptor,key))
    report=verify_bundle(path,xy);report.update(host_verification='PASS_SOFTWARE_ONLY',hardwareAcceptance='NOT_RUN',fullChainAcceptance='NOT_RUN')
    (out/'bundle-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(path)

if __name__=='__main__':main()
