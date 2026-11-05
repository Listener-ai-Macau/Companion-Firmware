from array import array
from pathlib import Path
import hashlib
import importlib.util
import io
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
import wave

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import calibrate_wba_dual_mic as calibration
import process_wba_dual_mic_pair as pair_tool


def wav_bytes(values, channels=2):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav:
        wav.setnchannels(channels); wav.setsampwidth(2); wav.setframerate(16000)
        wav.writeframes(array('h', values).tobytes())
    return buf.getvalue()


class PairArtifacts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='companion-dual-pair-')
        self.root = Path(self.temp.name)
        self.probe = self.root / 'probe.log'
        self.probe.write_bytes(Path(os.environ['DUAL_SYNTHETIC_PROBE']).read_bytes())
        p = calibration.parse_probe(self.probe.read_text(), 77)
        self.cal = calibration.estimate(p, known_single_source=True, max_delay_samples=2)
        self.cal.update(deviceUid='000000000000000000000123', firmwareSource='1' * 40, recordingToken=77,
            knownSingleSourceCallerDeclared=True, probeLogSha256=pair_tool.sha(self.probe.read_bytes()))
        self.calibration = self.root / 'calibration.json'
        self.calibration.write_text(json.dumps(self.cal))
        rng = random.Random(641)
        self.samples = array('h', [rng.randrange(-32000, 32000) for _ in range(64000)])
        self.pair = self.root / 'pair.wav'
        self.pair.write_bytes(wav_bytes(self.samples))
        self.evidence = self.root / 'capture.json'
        self.evidence.write_text(json.dumps({'result': 'SYNTHETIC_FIXTURE_NOT_HARDWARE', 'frames': 32000}))
        self.manifest = dict(schema=1, sourceKind='SYNCHRONOUS_DUAL_PCM', channels=['left', 'right'],
            processingStage=pair_tool.STAGE, pairWavSha256=pair_tool.sha(self.pair.read_bytes()),
            sampleRateHz=16000, sampleCount=32000, continuityVerified=True, synthetic=True,
            recordingId=1, recordingToken=78, sourceSampleOffset=160,
            deviceUid=self.cal['deviceUid'], firmwareSource=self.cal['firmwareSource'],
            useCase='FRONT_CLOSE_TALK_CANDIDATE', captureEvidenceSha256=pair_tool.sha(self.evidence.read_bytes()))
        self.source = self.root / 'source.json'
        self.source.write_text(json.dumps(self.manifest))

    def tearDown(self):
        self.temp.cleanup()

    def bundle(self, name='result'):
        return pair_tool.create_bundle(self.pair, self.source, self.calibration,
            self.probe, self.evidence, self.root / name)

    def test_separate_bundle_retains_original_and_exact_processing_identity(self):
        paths = [self.pair, self.source, self.calibration, self.probe, self.evidence]
        before = [x.read_bytes() for x in paths]
        result = self.bundle()
        self.assertEqual([x.read_bytes() for x in paths], before)
        self.assertEqual((self.root / 'result/original-pair.wav').read_bytes(), before[0])
        self.assertEqual(result['inputPairSha256'], pair_tool.sha(before[0]))
        self.assertEqual(result['outputSha256'], pair_tool.sha((self.root / 'result/enhanced-candidate.wav').read_bytes()))
        self.assertEqual(result['parameters'], {k: self.cal[k] for k in ['delayQ8', 'rightGainQ15', 'invertRight']})
        self.assertEqual(result['withheldHistorySamples'], 2)
        self.assertEqual(result['outputSourceSampleOffset'], 162)
        self.assertEqual(result['outputSamples'], 31998)
        self.assertFalse(result['physicalNoiseReductionQualified'])
        self.assertTrue(result['synthetic'])
        self.assertFalse(result['automaticallyApplied'])
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.bundle()
        self.assertEqual([x.read_bytes() for x in paths], before)

    def test_refuse_wrong_identity_order_history_and_hidden_meeting_filter(self):
        baseline = self.source.read_bytes()
        for key, value in [('deviceUid', 'f' * 24), ('firmwareSource', 'f' * 40),
            ('channels', ['right', 'left']), ('continuityVerified', False),
            ('sampleCount', 31999), ('pairWavSha256', 'a' * 64),
            ('useCase', 'ALL_PARTICIPANT_MEETING'), ('captureEvidenceSha256', 'b' * 64)]:
            with self.subTest(field=key):
                changed = dict(self.manifest); changed[key] = value
                self.source.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):
                    self.bundle()
                self.assertFalse((self.root / 'result').exists())
                self.assertEqual(list(self.root.glob('*.partial-*')), [])
        self.source.write_bytes(baseline)

    def test_calibration_is_recomputed_not_trusted_or_given_default_bound(self):
        for key, value in [('delayQ8', 0), ('rightGainQ15', 32768), ('invertRight', True),
            ('recordingToken', 99), ('knownSingleSourceCallerDeclared', False),
            ('probeLogSha256', '0' * 64), ('maxDelaySamples', None)]:
            with self.subTest(field=key):
                changed = dict(self.cal); changed[key] = value
                self.calibration.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):
                    self.bundle()
                self.assertFalse((self.root / 'result').exists())

    def test_clip_mono_and_truncated_cannot_be_a_pair(self):
        variants = [wav_bytes([0] * 32000, 1), wav_bytes([32767, 0] * 160), self.pair.read_bytes()[:-2]]
        for raw in variants:
            with self.subTest(size=len(raw)):
                with self.assertRaises(ValueError):
                    pair_tool.read_pair(raw)

    def test_input_race_leaves_no_published_or_partial_bundle(self):
        original = pair_tool.process_samples
        def changed(*args):
            result = original(*args)
            self.evidence.write_text('changed during processing')
            return result
        pair_tool.process_samples = changed
        try:
            with self.assertRaisesRegex(ValueError, 'Input changed'):
                self.bundle()
        finally:
            pair_tool.process_samples = original
        self.assertFalse((self.root / 'result').exists())
        self.assertEqual(list(self.root.glob('*.partial-*')), [])

    def test_python_samples_match_existing_production_c_with_signed_truncation(self):
        raw = self.root / 'input.pcm'; raw.write_bytes(self.samples.tobytes())
        for delay, gain, invert in [(0, 32768, False), (384, 45638, False), (-384, 45638, False),
            (1, 65535, True), (-639, 16384, True), (512, 65535, False), (2048, 32768, True), (-2048, 32768, False)]:
            with self.subTest(delay=delay, gain=gain, invert=invert):
                dest = self.root / 'c-output.pcm'
                subprocess.run([os.environ['DUAL_C_DRIVER'], str(raw), str(dest), str(delay), str(gain), str(int(invert))], check=True)
                expected, withheld = pair_tool.process_samples(self.samples, delay, gain, invert)
                self.assertEqual(dest.read_bytes(), expected.tobytes())
                self.assertEqual(len(expected), 32000 - withheld)

    def test_actual680_mono_original_is_refused_without_rewriting(self):
        original = Path(os.environ['DUAL_ACTUAL680_MONO'])
        raw = original.read_bytes()
        with self.assertRaisesRegex(ValueError, 'stereo PCM16'):
            pair_tool.read_pair(raw)
        self.assertEqual(original.read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()
