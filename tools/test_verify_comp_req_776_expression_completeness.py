import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("verify_comp_req_776_expression_completeness.py")
SPEC = importlib.util.spec_from_file_location("comp_req_776_expression", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ExpressionCompletenessTests(unittest.TestCase):
    def test_row_map_is_an_involution(self):
        frame = bytes(index & 0xFF for index in range(MODULE.FRAME_BYTES))
        self.assertEqual(frame, MODULE.map_controller_rows(MODULE.map_controller_rows(frame)))

    def test_status_bar_edge_is_allowed_but_not_reported_as_body_margin(self):
        frame = bytearray([0x00] * MODULE.FRAME_BYTES)
        frame[0] = 0xFF
        _, pixels, margins = MODULE.black_geometry(bytes(frame))
        self.assertEqual(8, pixels)
        self.assertEqual(
            {"top_below_status": None, "left": None, "right": None, "bottom": None},
            margins,
        )

    def test_body_edge_contact_is_visible_in_margin(self):
        frame = bytearray([0x00] * MODULE.FRAME_BYTES)
        frame[MODULE.STATUS_BAR_HEIGHT * MODULE.ROW_BYTES] |= 0x80
        _, _, margins = MODULE.black_geometry(bytes(frame))
        self.assertEqual(0, margins["left"])

    def test_source_complete_stage_copies_changed_window(self):
        previous = bytes([0xFF]) * MODULE.FRAME_BYTES
        current = bytearray(previous)
        current[47] = 0x01
        current[4040] = 0x7F
        current = bytes(current)
        window = MODULE.difference_window(previous, current)
        self.assertIsNotNone(window)
        self.assertEqual(current, MODULE.stage(previous, current, window))

    def test_close_family_guard_rejects_eye_mutation(self):
        text = """function morphComponent(points, profile) {
context.fillRect(bx - 3, by - 3, width + 6, height + 6);
}
function applyCloseFamilyVisualIdentity(frame, familyName, cheekOffsets = null) {
const cheeks = frame.cheeks; const eyes = frame.eyes;
/* Keep the generated eye bodies intact; erased the top 2/4 rows */
}
"""
        checks = MODULE.close_family_guard(text)
        self.assertFalse(checks["close_family_targets_cheeks_only"])
        self.assertFalse(checks["motion_erases_exact_component_pixels_only"])

    def test_close_family_guard_accepts_exact_component_erasure(self):
        text = """function morphComponent(points, profile) {
points.forEach(([x, y]) => context.fillRect(x, y, 1, 1));
}
function applyCloseFamilyVisualIdentity(frame, familyName, cheekOffsets = null) {
const cheeks = frame.cheeks;
/* Keep the generated eye bodies intact; erased the top 2/4 rows */
points.forEach(([x, y]) => context.fillRect(x, y, 1, 1));
}
"""
        self.assertTrue(all(MODULE.close_family_guard(text).values()))


if __name__ == "__main__":
    unittest.main()
