"""Host-only authenticated CE/CG delivery envelope gate. No target access."""
import argparse
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

from package_wba_v11_candidate import verify_ota_envelope
from sign_wba_update_manifest import public_xy, signed_prefix
from wba_flash_geometry import for_mcu


class CandidateEnvelopeTests(unittest.TestCase):
    def fixture(self, directory, geometry):
        payload=bytes(range(64));key=ec.generate_private_key(ec.SECP256R1())
        args=argparse.Namespace(target='firmware',format_version=1,target_family=0x41425743,
            board_target=geometry.board_target,component_version=0x10123,minimum_app_version=0,
            maximum_app_version=0xffffffff,key_id=0x12345678)
        prefix=signed_prefix(args,payload)
        r,s=decode_dss_signature(key.sign(prefix,ec.ECDSA(hashes.SHA256())))
        body=prefix+r.to_bytes(32,'big')+s.to_bytes(32,'big')
        wire=body+struct.pack('<I',zlib.crc32(body)&0xffffffff)
        xy=public_xy(key.public_key())
        (directory/'wba_manifest.bin').write_bytes(wire)
        (directory/'update-public.xy').write_bytes(xy)
        return payload,dict(wba_manifest_hex=wire.hex()),dict(key_id=args.key_id,public_key_sha256=hashlib.sha256(xy).hexdigest())

    def test_authentic_payloads_and_cross_capacity_rejection(self):
        for mcu in ('STM32WBA55CEU6','STM32WBA55CGU6'):
            with self.subTest(mcu=mcu),tempfile.TemporaryDirectory() as temporary:
                directory=Path(temporary);geometry=for_mcu(mcu)
                payload,manifest,trust=self.fixture(directory,geometry)
                verify_ota_envelope(directory,manifest,payload,geometry,trust,0x10123,0x10123,False)
                other=for_mcu('STM32WBA55CGU6' if geometry.flash_kib==512 else 'STM32WBA55CEU6')
                with self.assertRaisesRegex(RuntimeError,'target, bounds or payload'):
                    verify_ota_envelope(directory,manifest,payload,other,trust,0x10123,0x10123,False)

    def test_reserializing_signature_damage_does_not_authorize_the_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary);geometry=for_mcu('STM32WBA55CEU6')
            payload,manifest,trust=self.fixture(directory,geometry)
            wire=bytearray((directory/'wba_manifest.bin').read_bytes());wire[80]^=1
            struct.pack_into('<I',wire,140,zlib.crc32(wire[:140])&0xffffffff)
            (directory/'wba_manifest.bin').write_bytes(wire);manifest['wba_manifest_hex']=wire.hex()
            with self.assertRaises(InvalidSignature):
                verify_ota_envelope(directory,manifest,payload,geometry,trust,0x10123,0x10123,False)


if __name__=='__main__':unittest.main(verbosity=2)
