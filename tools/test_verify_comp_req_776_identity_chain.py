import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("verify_comp_req_776_identity_chain.py")
SPEC = importlib.util.spec_from_file_location("comp_req_776_identity", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class IdentityChainTests(unittest.TestCase):
    def test_define_reads_quoted_sha(self):
        header = '#define EXAMPLE "ABCDEF"\n'
        self.assertEqual("ABCDEF", MODULE.define(header, "EXAMPLE"))

    def test_define_does_not_match_prefix(self):
        header = '#define EXAMPLE_LONG "ABCDEF"\n'
        self.assertIsNone(MODULE.define(header, "EXAMPLE"))

    def test_three_layers_have_distinct_roles(self):
        self.assertNotEqual(MODULE.PAGE, MODULE.RESOURCE_MANIFEST)
        self.assertNotEqual(MODULE.RESOURCE_MANIFEST, MODULE.BASE_CEMP_JSON)


if __name__ == "__main__":
    unittest.main()
