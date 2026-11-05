import unittest

from tools.verify_comp_req_775_repeat_blink_runtime import recording_window_lines


class RecordingBlinkRuntimeWindowTest(unittest.TestCase):
    def test_post_stop_maintenance_full_is_excluded(self) -> None:
        lines = [
            "[record-visual] action=overlay_start result=1",
            "[epaper] accepted_product_driver control=0xCF result=1",
            "[record] gatt_recording_stop action=sync_complete state=idle",
            "[epaper] accepted_product_driver control=0xC7 result=1",
            "[epaper] maintenance_single_full settle_after=0",
        ]
        active = recording_window_lines(lines)
        self.assertEqual(3, len(active))
        self.assertNotIn("control=0xC7", "\n".join(active))

    def test_full_before_stop_remains_in_window(self) -> None:
        lines = [
            "[record-visual] action=overlay_start result=1",
            "[epaper] accepted_product_driver control=0xF7 result=1",
            "[record] touch_double_tap action=sync_complete state=idle",
        ]
        active = recording_window_lines(lines)
        self.assertIn("control=0xF7", "\n".join(active))


if __name__ == "__main__":
    unittest.main()
