"""Normalize one bounded passive capture's 32-bit receiver microsecond clock.

Only offline copies change. Raw bytes, CRC/MIC proofs and source SHA stay exact.
The capture must preserve receiver order and span less than one counter period.
"""
import json


class ReceiverClock:
    _fields = frozenset(('us', 'deviceUs', 'deviceTimestampUs', 'firstUs', 'lastUs',
                         'requestFirstUs', 'requestLastUs', 'responseFirstUs', 'responseLastUs'))

    def __init__(self, rows):
        self.rows = []
        self._timestamps = {}
        wraps = 0
        previous = None
        first = None
        for original in rows:
            value = original['deviceTimestampUs']
            if not isinstance(value, int) or not 0 <= value < 2**32:
                raise ValueError('Receiver timestamp is not a raw uint32')
            if previous is not None and value < previous:
                if previous - value <= 2**31:
                    raise ValueError('Receiver order regressed without an unambiguous counter wrap')
                wraps += 1
            extended = value + wraps * 2**32
            if first is None:
                first = extended
            if extended - first >= 2**32:
                raise ValueError('Capture spans a whole receiver period; raw timestamp association ambiguous')
            if value in self._timestamps and self._timestamps[value] != extended:
                raise ValueError('Raw timestamp belongs to multiple receiver epochs')
            self._timestamps[value] = extended
            self.rows.append(dict(original, deviceTimestampUs=extended))
            previous = value
        self.summary = dict(rawCounterBits=32, observedWraps=wraps, packets=len(self.rows),
                            spanUs=self.rows[-1]['deviceTimestampUs']-first if self.rows else 0,
                            sourceRewritten=False, absoluteHostClockFitted=False)

    @classmethod
    def read(cls, path):
        return cls(json.loads(line) for line in path.read_text().splitlines())

    def normalize(self, value):
        if isinstance(value, list):
            return [self.normalize(item) for item in value]
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                if key in self._fields and isinstance(item, int):
                    if item not in self._timestamps:
                        raise ValueError('Authenticated timestamp is absent from exact raw receiver capture')
                    result[key] = self._timestamps[item]
                else:
                    result[key] = self.normalize(item)
            return result
        return value
