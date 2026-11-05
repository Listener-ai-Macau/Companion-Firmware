"""Cover optimized GCC reports and reused link output directories; no board I/O."""
import os
from pathlib import Path
import tempfile
import unittest

from wba_stack_usage import collect_stack_usage, fresh_lto_reports, lto_report_stamps


class StackUsageTests(unittest.TestCase):
    def test_lto_functions_are_included_beside_non_lto_objects(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            obj, elf = root/'syscalls.o', root/'app.elf'
            obj.with_suffix('.su').write_text('syscalls.c:6:5:_fstat\t8\tstatic\n')
            before = lto_report_stamps(elf)
            lto = root/'app.elf.ltrans0.ltrans.su'
            lto.write_text('E:\\source\\opus.c:90:1:celt_encode.constprop.0\t1536\tstatic\n'
                           'record.c:22:4:record_poll\t96\tdynamic,bounded\n')
            report = collect_stack_usage([obj, root/'no-report.o'], fresh_lto_reports(elf, before))
            self.assertEqual(report['functionCount'], 3)
            self.assertTrue(report['ltoReportsIncluded'])
            self.assertEqual([row['bytes'] for row in report['functions']], [1536, 96, 8])
            self.assertIn('E:\\source\\opus.c', report['functions'][0]['function'])
            self.assertEqual(report['functions'][1]['kind'], 'dynamic,bounded')
            self.assertIn('not maximum call-chain/IRQ stack proof', report['scope'])

    def test_old_workers_and_other_elf_reports_do_not_leak_into_new_link(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            elf = root/'app.elf'
            old = root/'app.elf.ltrans7.ltrans.su'
            old.write_text('old.c:1:1:retired\t8192\tstatic\n')
            before = lto_report_stamps(elf)
            new = root/'app.elf.ltrans0.ltrans.su'
            new.write_text('current.c:1:1:current\t64\tstatic\n')
            other = root/'other.elf.ltrans0.ltrans.su'
            other.write_text('other.c:1:1:other\t4096\tstatic\n')
            self.assertEqual(fresh_lto_reports(elf, before), [new])
            self.assertTrue(old.exists())
            # A reused worker filename is fresh when GCC rewrites its report.
            old.write_text('current.c:2:1:rebuilt\t80\tstatic\n')
            os.utime(old, ns=(before[old]+1_000_000_000, before[old]+1_000_000_000))
            self.assertEqual(set(fresh_lto_reports(elf, before)), {old, new})

    def test_empty_output_does_not_claim_lto_coverage(self):
        report = collect_stack_usage([], [])
        self.assertFalse(report['ltoReportsIncluded'])
        self.assertEqual(report['functionCount'], 0)


if __name__ == '__main__':
    unittest.main()
