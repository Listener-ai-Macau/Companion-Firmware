from array import array
from pathlib import Path
import copy
import hashlib
import json
import os
import random
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
import zlib

TOOLS=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(TOOLS))
import calibrate_wba_dual_mic_pair as pair


def packet(raw):
    struct.pack_into('<I',raw,len(raw)-4,zlib.crc32(raw[:-4]))
    return bytes(raw)


class PairCalibration(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='companion-pair-calibration-')
        self.root=Path(self.tmp.name)
        self.uid='120011000d50335754363720';self.source='fbbbf3f59624139440be6b5139d83474a079e1de'
        self.setup=dict(schema='companion.dual-mic-known-source.v1',deviceUid=self.uid,firmwareSource=self.source,
            knownSingleBroadbandSourceConfirmed=True,useCase='FRONT_CLOSE_TALK_CANDIDATE',
            sourceDescription='Deterministic SOFTWARE broadband fixture; no physical source.',maxDelaySamples=1.5)
        self.setup_path=self.root/'setup.json';self.setup_path.write_text(json.dumps(self.setup))
        self.make_source()

    def tearDown(self):
        self.tmp.cleanup()

    def make_source(self,delay=1,invert=False,silent=False,startup_only=False,gain_drift=False):
        rng=random.Random(61)
        base=[rng.randint(-3000,3000) for _ in range(32008)]
        values=[]
        for i in range(32000):
            left=base[i+4] if not silent else 0
            right=int(base[i+4-delay]*.8)*(-1 if invert else 1) if not silent else 0
            if startup_only:
                # A short shared broad-band onset dominates whole-file sums;
                # the remaining independent channels contain no steering proof.
                common=int(base[i+4]*4*(max(0,2400-i)/2400)**0.5) if i<2400 else 0
                left=common+rng.randint(-600,600)
                right=int(common*.8)+rng.randint(-600,600)
            if gain_drift:
                right=int(base[i+4-delay]*(.8 if i<16000 else 1.2))
            values.extend([left,right])
        pcm=struct.pack('<64000h',*values)
        h=bytearray(80);h[:4]=b'DMP1'
        struct.pack_into('<HHIHBB',h,4,1,80,16000,160,2,2)
        h[16:28]=bytes.fromhex(self.uid);h[28:48]=bytes.fromhex(self.source)
        struct.pack_into('<IIQIII',h,48,77,9,640,200,1,0)
        h=packet(h);parts=[h]
        for i in range(200):
            b=bytearray(664);b[:4]=b'DMPF'
            struct.pack_into('<IQHH',b,4,i,640+i*160,160,0)
            b[20:660]=pcm[i*640:(i+1)*640];parts.append(packet(b))
        end=bytearray(48);end[:4]=b'DMPE'
        struct.pack_into('<IQIIIIIII',end,4,200,32000,0,0,0,zlib.crc32(pcm),0,struct.unpack_from('<I',h,76)[0],0)
        raw=b''.join(parts)+packet(end)
        _,identity=pair.decoder.decode(raw)
        self.evidence=dict(schema='companion.dual-mic-pair-capture.v1',streamSha256=pair.sha(raw),**identity,
            processedChannelMask=3,sourcePositionFromCapture=True,captureKind='SOFTWARE_FIXTURE',
            processingStage='POST_CHANNEL_GAIN_DC_PRE_BEAMFORM_PCM16',completed=True,
            captureFaultCounters={k:0 for k in pair.decoder.FAULT_COUNTERS},knownFrontSourceConfirmed=True,
            knownSourceSetupSha256=pair.sha(self.setup_path.read_bytes()))
        self.stream=self.root/'source.dmp';self.stream.write_bytes(raw)
        self.evidence_path=self.root/'capture.json';self.evidence_path.write_text(json.dumps(self.evidence))
        self.pcm=pcm

    def run_bundle(self,name='comparison'):
        return pair.create_bundle(self.stream,self.evidence_path,self.setup_path,self.root/name)

    def test_same_saved_pair_calibrates_both_delay_directions_and_polarity_without_reopening_device(self):
        for delay,invert in [(1,False),(-1,True),(0,False)]:
            self.make_source(delay,invert)
            inputs=[p.read_bytes()for p in [self.stream,self.evidence_path,self.setup_path]]
            result=self.run_bundle(f'comparison-{delay}')
            self.assertTrue(result['synthetic'])
            self.assertAlmostEqual(result['parameters']['delayQ8'],delay*256,delta=1)
            self.assertAlmostEqual(result['parameters']['rightGainQ15'],40960,delta=16)
            self.assertEqual(result['parameters']['invertRight'],invert)
            self.assertFalse(result['automaticallyApplied']);self.assertFalse(result['physicalNoiseReductionQualified'])
            self.assertEqual(inputs,[p.read_bytes()for p in [self.stream,self.evidence_path,self.setup_path]])
            dest=self.root/f'comparison-{delay}'
            self.assertEqual((dest/'independent-source/original-pair.dmp').read_bytes(),inputs[0])
            with wave.open(str(dest/'comparison/enhanced-candidate.wav'),'rb')as wav:
                self.assertEqual(wav.getnchannels(),1)
                self.assertEqual(wav.getnframes(),result['outputSamples'])

    def test_shared_startup_cannot_publish_parameters_unsupported_by_later_audio(self):
        self.make_source(startup_only=True)
        probe=pair.estimator.parse_probe(pair.probe_from_pcm(self.pcm,77).decode(),77)
        legacy=pair.estimator.estimate(probe,known_single_source=True,max_delay_samples=1.5)
        self.assertEqual(legacy['result'],'FIXED_FRONT_END_CALIBRATION_CANDIDATE_ONLY')
        inputs=[p.read_bytes()for p in [self.stream,self.evidence_path,self.setup_path]]
        with self.assertRaisesRegex(ValueError,'Temporal calibration'):
            self.run_bundle('startup-dominated')
        self.assertFalse((self.root/'startup-dominated').exists())
        self.assertEqual(inputs,[p.read_bytes()for p in [self.stream,self.evidence_path,self.setup_path]])

    def test_gain_drift_cannot_publish_a_whole_file_average_as_fixed_calibration(self):
        self.make_source(gain_drift=True)
        probe=pair.estimator.parse_probe(pair.probe_from_pcm(self.pcm,77).decode(),77)
        legacy=pair.estimator.estimate(probe,known_single_source=True,max_delay_samples=1.5)
        self.assertEqual(legacy['result'],'FIXED_FRONT_END_CALIBRATION_CANDIDATE_ONLY')
        with self.assertRaisesRegex(ValueError,'Temporal calibration'):
            self.run_bundle('changing-gain')
        self.assertFalse((self.root/'changing-gain').exists())

    def test_pair_statistics_are_exactly_the_unchanged_production_c_probe(self):
        driver=os.environ['DUAL_PROBE_REFERENCE']
        p=self.root/'input.pcm';p.write_bytes(self.pcm)
        reference=json.loads(subprocess.check_output([driver,str(p)]))
        probe=pair.estimator.parse_probe(pair.probe_from_pcm(self.pcm,77).decode(),77)
        h=probe['header'];self.assertEqual(int(h['samples']),reference['samples']);self.assertEqual(int(h['count']),reference['count'])
        for key,signed in [('ls',True),('lss',False)]:
            self.assertEqual(pair.estimator.wide(h,key,signed),reference[key])
        for index,lag in enumerate(pair.estimator.LAGS):
            for key,signed in [('rs',True),('rss',False),('cross',True)]:
                self.assertEqual(pair.estimator.wide(probe['lags'][lag],key,signed),reference['lags'][index][key])

    def test_unlabelled_take_and_retrospective_changed_setup_cannot_be_calibrated(self):
        original=copy.deepcopy(self.evidence)
        for change in [dict(knownFrontSourceConfirmed=False),dict(knownSourceSetupSha256='0'*64)]:
            self.evidence_path.write_text(json.dumps(dict(original,**change)))
            with self.assertRaisesRegex(ValueError,'bound at capture'):self.run_bundle()
            self.assertFalse((self.root/'comparison').exists())
        self.evidence_path.write_text(json.dumps(original))
        changed=dict(self.setup,sourceDescription='A different source after capture')
        self.setup_path.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError,'bound at capture'):self.run_bundle()

    def test_bad_capture_and_silent_source_cannot_publish_an_enhanced_candidate(self):
        self.evidence['captureFaultCounters']['budgetViolations']=1
        self.evidence_path.write_text(json.dumps(self.evidence))
        with self.assertRaisesRegex(ValueError,'counters'):self.run_bundle()
        self.make_source(silent=True)
        with self.assertRaisesRegex(ValueError,'energy insufficient'):self.run_bundle()
        self.assertFalse((self.root/'comparison').exists())
        self.assertEqual(list(self.root.glob('*.partial-*')),[])

    def test_existing_bundle_is_immutable_and_changed_input_is_not_published(self):
        self.run_bundle();original=(self.root/'comparison/result.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'already exists'):self.run_bundle()
        self.assertEqual((self.root/'comparison/result.json').read_bytes(),original)
        create=pair.processor.create_bundle
        def racing(*args,**kw):
            value=create(*args,**kw);self.setup_path.write_text('changed');return value
        pair.processor.create_bundle=racing
        try:
            with self.assertRaisesRegex(ValueError,'changed during'):self.run_bundle('raced')
        finally:pair.processor.create_bundle=create
        self.assertFalse((self.root/'raced').exists());self.assertEqual(list(self.root.glob('*.partial-*')),[])

    def test_setup_requires_actual_intent_identity_and_geometry_before_capture(self):
        for key,value in [('deviceUid','0'*24),('firmwareSource','0'*40),('knownSingleBroadbandSourceConfirmed',False),
            ('useCase','ALL_PARTICIPANT_MEETING'),('sourceDescription',' '),('maxDelaySamples',True),('maxDelaySamples',float('nan'))]:
            with self.subTest(key=key):
                raw=json.dumps(dict(self.setup,**{key:value})).encode()
                with self.assertRaises(ValueError):pair.validate_setup(raw,self.uid,self.source)
        raw=json.dumps(dict(self.setup,useCase='ALL_PARTICIPANT_MEETING')).encode();self.setup_path.write_bytes(raw)
        command=[sys.executable,str(TOOLS/'capture_wba_dual_mic_pair.py'),'--project-root',os.environ['COMPANION_PROJECT_ROOT'],
            '--expected-source',self.source,'--expected-version','66487','--output',str(self.root/'not-created'),
            '--known-source-setup',str(self.setup_path)]
        # Invalid setup must be rejected before serial imports, endpoint selection
        # or creating a capture directory. No hardware is touched by this test.
        invalid=subprocess.run(command,capture_output=True,text=True)
        self.assertNotEqual(invalid.returncode,0)
        self.assertIn('steer general/meeting',invalid.stderr)
        self.assertFalse((self.root/'not-created').exists())


if __name__=='__main__':unittest.main()
