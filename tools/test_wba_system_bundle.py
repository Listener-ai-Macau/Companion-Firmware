"""Only the new paired OTA package's authentication and layout boundaries."""
from pathlib import Path
import json, struct, tempfile, unittest, zlib
from argparse import Namespace
from copy import deepcopy
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ec
from sign_wba_update_manifest import signed_prefix
from wba_flash_geometry import for_mcu
from wba_resource_geometry import geometry as nor_geometry
from wba_system_bundle import sha, sign_descriptor, sign_device_wire, device_wire_signed_bytes, verify_bundle, verify_component, SCHEMA, CAPABILITY, ACTIVATION_CONTRACT, DEVICE_WIRE_CONTRACT

class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.key=ec.generate_private_key(ec.SECP256R1());pub=self.key.public_key().public_numbers()
        self.xy=pub.x.to_bytes(32,'big')+pub.y.to_bytes(32,'big')
        self.g=for_mcu(layout='compact24')
        fw=struct.pack('<II',0x20020000,self.g.app_address+9)+b'F'*120;ui=b'U'*8192
        self.d=dict(schema=SCHEMA,package_type='companion-system-ota',requires_device_capability=CAPABILITY,mcu=self.g.mcu,hardware_revision=self.g.hardware_revision,activation_contract=dict(ACTIVATION_CONTRACT),device_wire_contract=dict(DEVICE_WIRE_CONTRACT),internal_flash_geometry=self.g.receipt(),key_id=1,public_key_sha256=sha(self.xy),
            components={},flash_geometry=nor_geometry(len(ui)),resource_contract=dict(storageLayoutVersion=3,uiPartitionBytes=len(ui),uiPartitionSha256=sha(ui),generation=69,flashGeometry=nor_geometry(len(ui))))
        for name,target,version,payload in [('firmware','firmware',315,fw),('resources','ui-assets',69,ui)]:
            args=Namespace(target=target,format_version=1 if target=='firmware' else 2,target_family=0x41425743,board_target=self.g.board_target,component_version=version,minimum_app_version=315 if name=='resources' else 0,maximum_app_version=315 if name=='resources' else 0,key_id=1)
            prefix=signed_prefix(args,payload)
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
            r,s=decode_dss_signature(self.key.sign(prefix,ec.ECDSA(hashes.SHA256())))
            body=prefix+r.to_bytes(32,'big')+s.to_bytes(32,'big')
            wire=body+struct.pack('<I',zlib.crc32(body)&0xffffffff)
            file=name+'.bin';(self.root/file).write_bytes(payload)
            self.d['components'][name]=dict(file=file,bytes=len(payload),sha256=sha(payload),version=version,wba_manifest_hex=wire.hex())
        self.path=self.root/'system_bundle.json'
        self.write(self.d)
    def tearDown(self):self.temp.cleanup()
    def write(self,d):
        self.path.write_text(json.dumps(sign_descriptor(d,self.key)),encoding='utf-8')
        if set(d['components'])=={'firmware','resources'}:
            (self.root/DEVICE_WIRE_CONTRACT['file']).write_bytes(sign_device_wire(d,self.key))
    def test_matched_pair_verified_without_claiming_activation(self):
        report=verify_bundle(self.path,self.xy)
        self.assertEqual(report['internal_flash_geometry']['app_bytes'],483328)
        self.assertEqual(report['device_activation'],'NOT_IMPLEMENTED_NOT_QUALIFIED')
        self.assertEqual(report['device_wire_bytes'],452)
        self.assertFalse(self.d['activation_contract']['backup_both_before_install'])
        self.assertFalse(self.d['activation_contract']['rollback_matched_pair'])
        self.assertTrue(self.d['activation_contract']['retain_verified_candidate_until_joint_confirm'])
    def test_authenticated_ce_component_rejects_stack_in_the_sram_hole(self):
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
        component=self.d['components']['firmware']
        for sp,accepted in ((0x20020000,True),(0x20008008,False),(0x20010000,False)):
            with self.subTest(stack=hex(sp)):
                payload=bytearray((self.root/component['file']).read_bytes())
                struct.pack_into('<I',payload,0,sp);payload=bytes(payload)
                args=Namespace(target='firmware',format_version=1,target_family=0x41425743,board_target=self.g.board_target,
                    component_version=315,minimum_app_version=0,maximum_app_version=0,key_id=1)
                prefix=signed_prefix(args,payload)
                r,s=decode_dss_signature(self.key.sign(prefix,ec.ECDSA(hashes.SHA256())))
                body=prefix+r.to_bytes(32,'big')+s.to_bytes(32,'big')
                component['wba_manifest_hex']=(body+struct.pack('<I',zlib.crc32(body)&0xffffffff)).hex()
                component['sha256']=sha(payload);(self.root/component['file']).write_bytes(payload)
                if accepted:self.assertEqual(verify_component(component,self.root,self.xy,self.g,1,1),payload)
                else:
                    with self.assertRaisesRegex(ValueError,'Firmware vector'):
                        verify_component(component,self.root,self.xy,self.g,1,1)
    def test_swapped_resource_or_unsigned_descriptor_rejected(self):
        e=json.loads(self.path.read_bytes());e['descriptor']['components']['resources']['sha256']='0'*64
        self.path.write_text(json.dumps(e))
        with self.assertRaises((ValueError,InvalidSignature)):verify_bundle(self.path,self.xy)
        self.write(self.d);(self.root/'resources.bin').write_bytes(b'V'*8192)
        with self.assertRaisesRegex(ValueError,'payload mismatch'):verify_bundle(self.path,self.xy)
    def test_missing_half_and_wrong_layout_rejected_even_signed(self):
        d=deepcopy(self.d);del d['components']['resources'];self.write(d)
        with self.assertRaisesRegex(ValueError,'both components'):verify_bundle(self.path,self.xy)
        d=deepcopy(self.d);d['internal_flash_geometry']=for_mcu().receipt();d['hardware_revision']=for_mcu().hardware_revision;self.write(d)
        with self.assertRaisesRegex(ValueError,'payload mismatch'):verify_bundle(self.path,self.xy)
    def test_resource_contract_and_file_traversal_rejected(self):
        d=deepcopy(self.d);d['resource_contract']['generation']=68;self.write(d)
        with self.assertRaisesRegex(ValueError,'application contract'):verify_bundle(self.path,self.xy)
        d=deepcopy(self.d);d['components']['resources']['file']='../resources.bin';self.write(d)
        with self.assertRaisesRegex(ValueError,'file name'):verify_bundle(self.path,self.xy)
    def test_wrong_trust_anchor_rejected(self):
        key=ec.generate_private_key(ec.SECP256R1()).public_key().public_numbers()
        with self.assertRaises(InvalidSignature):verify_bundle(self.path,key.x.to_bytes(32,'big')+key.y.to_bytes(32,'big'))
    def test_independent_activation_rejected_even_with_valid_signature(self):
        d=deepcopy(self.d);d['activation_contract']['independent_component_reboots_allowed']=True;self.write(d)
        with self.assertRaisesRegex(ValueError,'atomic paired'):verify_bundle(self.path,self.xy)
    def test_paired_device_signature_and_exact_descriptor_binding(self):
        path=self.root/DEVICE_WIRE_CONTRACT['file']
        raw=bytearray(path.read_bytes());raw[384]^=1
        struct.pack_into('<I',raw,448,zlib.crc32(raw[:448])&0xffffffff);path.write_bytes(raw)
        with self.assertRaises(InvalidSignature):verify_bundle(self.path,self.xy)
        self.write(self.d);raw=bytearray(path.read_bytes());raw[64]^=1
        struct.pack_into('<I',raw,448,zlib.crc32(raw[:448])&0xffffffff);path.write_bytes(raw)
        with self.assertRaisesRegex(ValueError,'differs from signed descriptor'):verify_bundle(self.path,self.xy)
    def test_joint_capacity_counts_both_images_not_each_individually(self):
        d=deepcopy(self.d);static=8*1024*1024
        d['flash_geometry']=nor_geometry(static)
        d['resource_contract']['uiPartitionBytes']=static
        d['resource_contract']['flashGeometry']=nor_geometry(static)
        d['components']['resources']['bytes']=static
        with self.assertRaisesRegex(ValueError,'does not fit'):device_wire_signed_bytes(d)
    def test_temporary_recovery_extent_is_signed_inside_dynamic_claim(self):
        raw=device_wire_signed_bytes(self.d)
        self.assertEqual(raw[4],2)
        self.assertEqual(struct.unpack_from('<I',raw,52)[0],4096+8192+131072+8192)
        self.assertEqual(self.d['device_wire_contract']['recovery_metadata_bytes'],131072)
        d=deepcopy(self.d);d['device_wire_contract']['recovery_anchor_bytes']=0
        with self.assertRaisesRegex(ValueError,'wire contract'):device_wire_signed_bytes(d)

if __name__=='__main__':unittest.main(verbosity=2)
