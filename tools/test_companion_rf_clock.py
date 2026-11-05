"""Regression for the real 483 capture crossing the receiver's 71.6-minute wrap."""
import unittest
from companion_rf_clock import ReceiverClock


class ReceiverClockChecks(unittest.TestCase):
    def clock(self, timestamps):
        return ReceiverClock(dict(deviceTimestampUs=x, unchanged='packet') for x in timestamps)

    def test_cross_wrap_keeps_positive_packet_and_window_order(self):
        c = self.clock([2**32-100, 2**32-1, 25, 100])
        self.assertEqual(c.summary['observedWraps'], 1)
        self.assertEqual(c.summary['spanUs'], 200)
        self.assertEqual(c.normalize({'firstUs':2**32-100, 'lastUs':100}),
                         {'firstUs':2**32-100, 'lastUs':2**32+100})
        self.assertEqual(c.rows[-1]['unchanged'], 'packet')

    def test_no_wrap_exactly_preserves_metadata_and_non_time_counters(self):
        c = self.clock([50, 60, 60, 70])
        data = dict(firstUs=50, lastUs=70, offset=60, counter=50, instant=70,
                    nested=[dict(deviceUs=60, us=70)])
        self.assertEqual(c.normalize(data), data)
        self.assertEqual(c.summary['observedWraps'], 0)

    def test_unobserved_timestamp_cannot_be_filled_or_inferred(self):
        with self.assertRaises(ValueError): self.clock([10,20]).normalize({'lastUs':15})

    def test_small_regression_is_not_relabelled_as_wrap(self):
        with self.assertRaises(ValueError): self.clock([1000,900])

    def test_multiple_epochs_with_ambiguous_raw_identity_rejected(self):
        with self.assertRaises(ValueError): self.clock([1,2**32-1,1])


if __name__ == '__main__': unittest.main()
