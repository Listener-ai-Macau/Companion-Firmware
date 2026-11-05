"""Signed firmware/resource pairing contract. No device access or activation.

The bundle requires an atomic two-component device installer. Existing single
component OTA must reject it rather than simulate a transaction with two reboots.
"""
from __future__ import annotations
import hashlib, json, struct, zlib
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, encode_dss_signature
from wba_flash_geometry import from_receipt
from wba_resource_geometry import from_profile

SCHEMA = 'companion.wba.system-bundle.v3'
CAPABILITY = 'companion_system_bundle_new_only_v2'
DEVICE_WIRE_CONTRACT = dict(schema='companion.wba.system-wire.v2',
    file='system-transaction.wsb',wire_bytes=452,signed_bytes=384,
    recovery_metadata_bytes=131072,recovery_anchor_bytes=8192)
# Owner 2026-10-13: keep only the verified new pair, no old-image rollback.
# A distinct capability prevents an old installer interpreting the new policy.
ACTIVATION_CONTRACT = dict(verify_both_before_erase=True,backup_both_before_install=False,
    confirm_both_before_release=True,rollback_matched_pair=False,
    retain_verified_candidate_until_joint_confirm=True,
    recovery_mode='resume_verified_new_pair_or_reupload',
    layout_growth_requires_durable_old_geometry_anchor=True,independent_component_reboots_allowed=False)

def canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')

def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()

def public_key(xy: bytes):
    if len(xy) != 64: raise ValueError('Expected P-256 X||Y trust anchor')
    return ec.EllipticCurvePublicNumbers(int.from_bytes(xy[:32],'big'),int.from_bytes(xy[32:],'big'),ec.SECP256R1()).public_key()

def sign_descriptor(descriptor: dict, key) -> dict:
    r,s=decode_dss_signature(key.sign(canonical(descriptor),ec.ECDSA(hashes.SHA256())))
    return dict(descriptor=descriptor,bundle_id=sha(canonical(descriptor)),signature_p256=(r.to_bytes(32,'big')+s.to_bytes(32,'big')).hex())

def verify_descriptor(envelope: dict, xy: bytes) -> dict:
    d=envelope['descriptor'];raw=bytes.fromhex(envelope['signature_p256'])
    if len(raw)!=64 or envelope['bundle_id']!=sha(canonical(d)):
        raise ValueError('Bundle identity/signature length mismatch')
    public_key(xy).verify(encode_dss_signature(int.from_bytes(raw[:32],'big'),int.from_bytes(raw[32:],'big')),canonical(d),ec.ECDSA(hashes.SHA256()))
    if d['schema']!=SCHEMA or d['package_type']!='companion-system-ota' or d['requires_device_capability']!=CAPABILITY:
        raise ValueError('Unsupported system bundle')
    if d.get('activation_contract')!=ACTIVATION_CONTRACT:
        raise ValueError('System bundle must require atomic paired activation')
    if d.get('device_wire_contract')!=DEVICE_WIRE_CONTRACT:
        raise ValueError('System bundle requires the signed paired device wire')
    return d

def device_wire_signed_bytes(descriptor: dict) -> bytes:
    """Fixed MCU decoder representation; JSON never enters resident Boot.

    The outer wire signature binds the canonical JSON descriptor identity,
    both signed WUM1 components and geometry. There is no wire-SHA field in
    the JSON descriptor, avoiding a circular descriptor/wire identity.
    """
    if descriptor.get('device_wire_contract')!=DEVICE_WIRE_CONTRACT:
        raise ValueError('Missing paired device wire contract')
    g=from_receipt(descriptor)
    parts=descriptor['components']
    fw=bytes.fromhex(parts['firmware']['wba_manifest_hex'])
    ui=bytes.fromhex(parts['resources']['wba_manifest_hex'])
    if len(fw)!=144 or len(ui)!=144:
        raise ValueError('Both WUM1 component envelopes are required')
    static=descriptor['flash_geometry']['staticBytes']
    total=descriptor['flash_geometry']['norBytes']
    nor=from_profile(descriptor['resource_contract'],static)
    if descriptor['flash_geometry']!=nor:
        raise ValueError('Paired wire geometry differs from resource profile')
    firmware_size=parts['firmware']['bytes']
    if not 8<=firmware_size<=g.app_bytes or parts['resources']['bytes']!=static:
        raise ValueError('Paired device wire component size mismatch')
    resource_offset=(firmware_size+4095)//4096*4096
    staging=resource_offset+static+DEVICE_WIRE_CONTRACT['recovery_metadata_bytes']+DEVICE_WIRE_CONTRACT['recovery_anchor_bytes']
    if staging>nor['payloadBytes']:
        raise ValueError('New pair does not fit the dynamic staging arena')
    words=(0x41425743,g.board_target,descriptor['key_id'],g.app_address,
        g.app_bytes,g.app_end,total,static,nor['systemBytes'],0,resource_offset,
        staging,nor['rootA'],nor['rootB'])
    body=b'WSB2'+bytes([2,1])+struct.pack('<H',96)+struct.pack('<14I',*words)
    body+=hashlib.sha256(canonical(descriptor)).digest()+fw+ui
    if len(body)!=384:raise ValueError('Paired device wire size mismatch')
    return body

def sign_device_wire(descriptor: dict, key) -> bytes:
    body=device_wire_signed_bytes(descriptor)
    r,s=decode_dss_signature(key.sign(body,ec.ECDSA(hashes.SHA256())))
    wire=body+r.to_bytes(32,'big')+s.to_bytes(32,'big')
    return wire+struct.pack('<I',zlib.crc32(wire)&0xffffffff)

def verify_device_wire(wire: bytes, descriptor: dict, xy: bytes) -> None:
    if len(wire)!=452 or struct.unpack_from('<I',wire,448)[0]!=zlib.crc32(wire[:448])&0xffffffff:
        raise ValueError('Paired device wire length/CRC mismatch')
    if wire[:384]!=device_wire_signed_bytes(descriptor):
        raise ValueError('Paired device wire differs from signed descriptor/components')
    public_key(xy).verify(encode_dss_signature(int.from_bytes(wire[384:416],'big'),
        int.from_bytes(wire[416:448],'big')),wire[:384],ec.ECDSA(hashes.SHA256()))

def local_file(root: Path, name: str) -> Path:
    # Packages contain simple local files; no traversal/symlink/absolute paths.
    if not isinstance(name,str) or Path(name).name!=name or '/' in name or '\\' in name or ':' in name:
        raise ValueError('Invalid package file name')
    path=root/name
    if path.resolve().parent!=root.resolve(): raise ValueError('Package file escapes bundle directory')
    return path

def verify_component(component: dict, root: Path, xy: bytes, geometry, key_id: int, target: int) -> bytes:
    payload=local_file(root,component['file']).read_bytes()
    wire=bytes.fromhex(component['wba_manifest_hex'])
    if len(wire)!=144 or wire[:4]!=b'WUM1' or wire[4]!=1 or wire[5]!=target or struct.unpack_from('<H',wire,6)[0]!=(1 if target==1 else 2):
        raise ValueError('Component envelope format/target mismatch')
    words=struct.unpack_from('<7I',wire,8)
    family,board,version,minimum,maximum,size,crc=words
    if family!=0x41425743 or board!=geometry.board_target or version!=component['version'] or size!=len(payload) or size!=component['bytes'] or crc!=zlib.crc32(payload)&0xffffffff or wire[36:68].hex()!=sha(payload) or component['sha256']!=sha(payload):
        raise ValueError('Component identity/payload mismatch')
    if wire[68:72]!=bytes([1,0,0,0]) or struct.unpack_from('<I',wire,72)[0]!=key_id or struct.unpack_from('<I',wire,140)[0]!=zlib.crc32(wire[:140])&0xffffffff:
        raise ValueError('Component authentication metadata mismatch')
    public_key(xy).verify(encode_dss_signature(int.from_bytes(wire[76:108],'big'),int.from_bytes(wire[108:140],'big')),wire[:76],ec.ECDSA(hashes.SHA256()))
    if not payload or target==1 and len(payload)>geometry.app_bytes:raise ValueError('Component exceeds selected Flash layout')
    if target==1:
        sp,reset=struct.unpack_from('<II',payload)
        if not (geometry.valid_stack_pointer(sp) and reset&1 and geometry.app_address<=reset&~1<geometry.app_address+len(payload)):
            raise ValueError('Firmware vector differs from bundle Flash layout')
    return payload

def verify_bundle(path: Path, xy: bytes) -> dict:
    envelope=json.loads(path.read_bytes());d=verify_descriptor(envelope,xy)
    geometry=from_receipt(d)
    if d.get('hardware_revision')!=geometry.hardware_revision or not isinstance(d.get('key_id'),int) or not 0<d['key_id']<=0xffffffff:
        raise ValueError('Bundle hardware/key identity mismatch')
    if sha(xy)!=d['public_key_sha256']:raise ValueError('Bundle trust anchor differs')
    parts=d['components']
    if set(parts)!=set(['firmware','resources']):raise ValueError('System bundle needs both components')
    fw=verify_component(parts['firmware'],path.parent,xy,geometry,d['key_id'],1)
    ui=verify_component(parts['resources'],path.parent,xy,geometry,d['key_id'],2)
    profile=d['resource_contract']
    nor=from_profile(profile,len(ui))
    if profile['uiPartitionSha256'].lower()!=sha(ui) or profile['generation']!=parts['resources']['version'] or nor!=d['flash_geometry']:
        raise ValueError('Resource bank differs from matched application contract')
    wire=bytes.fromhex(parts['resources']['wba_manifest_hex'])
    if struct.unpack_from('<II',wire,20)!=(parts['firmware']['version'],parts['firmware']['version']):
        raise ValueError('Resources are not bound to this exact firmware version')
    paired_wire=local_file(path.parent,d['device_wire_contract']['file']).read_bytes()
    verify_device_wire(paired_wire,d,xy)
    return dict(bundle_id=envelope['bundle_id'],firmware_bytes=len(fw),resource_bytes=len(ui),internal_flash_geometry=geometry.receipt(),flash_geometry=nor,device_wire_bytes=len(paired_wire),device_activation='NOT_IMPLEMENTED_NOT_QUALIFIED')
