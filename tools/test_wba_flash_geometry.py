"""Host-only target/capacity contract; never opens ST-Link or writes a target."""
import argparse
from pathlib import Path
import tempfile
import unittest

import wba_flash_geometry as g
import sign_wba_update_manifest as signer


class GeometryTests(unittest.TestCase):
    def test_generated_header_matches_canonical_geometry(self):
        g.validate_generated_header()
        self.assertEqual(g.for_mcu().mcu, 'STM32WBA55CEU6')
        self.assertEqual(g.for_mcu().flash_kib, 512)

    def test_ce_and_cg_have_disjoint_signed_identities_and_preserve_boot_nvm(self):
        cg, ce = g.for_mcu('STM32WBA55CGU6'), g.for_mcu('STM32WBA55CEU6')
        self.assertNotEqual(cg.board_target, ce.board_target)
        self.assertNotEqual(cg.hardware_revision, ce.hardware_revision)
        self.assertEqual((cg.app_bytes, ce.app_bytes), (999424, 475136))
        self.assertEqual((cg.app_end, ce.app_end), (0x080FC000, 0x0807C000))
        for geometry in (cg, ce):
            self.assertEqual(geometry.boot_bytes, 32768)
            self.assertEqual(geometry.nvm_bytes, 16384)
            self.assertEqual(geometry.flash_page_bytes, 8192)
            geometry.validate_linker(g.ROOT / 'platform/stm32wba55_companion_v11' / (geometry.mcu + '_BLE.ld'))
            geometry.validate_linker(g.ROOT / 'platform/stm32wba55_companion_v11/STM32WBA55CGU6_BOOT.ld', boot=True)

    def test_ce_does_not_accept_a_cg_linker_or_a_larger_receipt(self):
        ce = g.for_mcu('STM32WBA55CEU6')
        with self.assertRaises(ValueError):
            ce.validate_linker(g.ROOT / 'platform/stm32wba55_companion_v11/STM32WBA55CGU6_BLE.ld')
        value = {'mcu': ce.mcu, 'internal_flash_geometry': ce.receipt()}
        value['internal_flash_geometry']['app_bytes'] = g.for_mcu('STM32WBA55CGU6').app_bytes
        with self.assertRaises(ValueError):
            g.from_receipt(value)

    def test_each_variant_oversize_signing_is_rejected_before_key_read_and_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for geometry in (g.for_mcu('STM32WBA55CGU6'), g.for_mcu('STM32WBA55CEU6')):
                with self.subTest(mcu=geometry.mcu):
                    payload = root / 'app.bin'
                    payload.write_bytes(b'\xff' * (geometry.app_bytes + 1))
                    args = argparse.Namespace(target='firmware', format_version=1, payload=str(payload),
                        output=str(root / 'app.wum'), private_key=str(root / 'missing-private-key.pem'),
                        target_family=0x41425743, board_target=geometry.board_target)
                    with self.assertRaisesRegex(SystemExit, 'payload size'):
                        signer.cmd_sign(args)
                    self.assertFalse((root / 'app.wum').exists())

    def test_standalone_diagnostics_use_selected_capacity_and_never_cg_for_ce(self):
        platform = g.ROOT / 'platform/stm32wba55_companion_v11'
        for mcu in g.MCUS:
            g.for_mcu(mcu).validate_linker(platform / (mcu + '.ld'), standalone=True)
        with self.assertRaisesRegex(ValueError, 'selected MCU geometry'):
            g.for_mcu().validate_linker(platform / 'STM32WBA55CGU6.ld', standalone=True)
        with self.assertRaisesRegex(ValueError, 'roles are distinct'):
            g.for_mcu().validate_linker(platform / 'STM32WBA55CEU6.ld', boot=True, standalone=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
