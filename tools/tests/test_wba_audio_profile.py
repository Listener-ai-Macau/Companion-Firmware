import copy,hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
spec=importlib.util.spec_from_file_location('wba_audio_profile',Path(__file__).resolve().parents[1]/'wba_audio_profile.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def args(**extra):
 d=dict(recording_audio_provenance_source=None,microphone_dual_pair_source=None,microphone_dual_calibration=None,microphone_dual_delay_q8=None,microphone_dual_right_gain_q15=None,microphone_dual_invert_right=False);d.update(extra);return SimpleNamespace(**d)
class BuildIdentity(unittest.TestCase):
 def test_legacy_and_explicit_baseline(self):
  a=args();self.assertFalse(m.resolve(a)['enabled']);self.assertEqual(a.microphone_dual_right_gain_q15,32768)
  with tempfile.TemporaryDirectory()as d:
   p=m.resolve(args(recording_audio_provenance_source='1'*40,microphone_dual_pair_source='1'*40));h=m.write_identity(Path(d),p)
   self.assertIn('CALIBRATION_PRESENT 0',h.read_text());self.assertIn('0x11',h.read_text());self.assertFalse(p['automaticEnable'])
 def test_source_and_loose_direction_refusal(self):
  for a in [args(recording_audio_provenance_source='0'*40),args(recording_audio_provenance_source='1'*40,microphone_dual_pair_source='2'*40),args(recording_audio_provenance_source='1'*40,microphone_dual_delay_q8=0)]:
   with self.assertRaises(ValueError):m.resolve(a)
 def test_exact_calibration_file_binding_and_refusals(self):
  # Explicit synthetic TEST fixture of the input contract, never a measured
  # calibration or installation input; the validation only describes metadata.
  c=dict(result='FIXED_FRONT_END_CALIBRATION_CANDIDATE_ONLY',automaticApply=False,synthetic=False,knownSingleSourceCallerDeclared=True,deviceUid='120011000d50335754363720',firmwareSource='2'*40,probeLogSha256='3'*64,sourceStreamSha256='4'*64,knownSourceSetupSha256='5'*64,recordingToken=7,sampleRate=16000,synchronousSamples=31994,maxDelaySamples=2,delayQ8=128,rightGainQ15=40000,invertRight=True)
  c['temporalStability']=dict(schema=1,result='TWO_DISJOINT_WINDOWS_AGREE_WITH_FULL_PAIR',
   windows=[dict(firstSample=a,endSample=b,probeLogSha256='6'*64,delayQ8=128,rightGainQ15=40000,invertRight=True)for a,b in [(0,16000),(16000,32000)]],
   maximumDelaySpreadQ8=64,maximumGainSpreadDb=1.0,delaySpreadQ8=0,gainSpreadDb=0.0,sourceSamplesDiscarded=0)
  with tempfile.TemporaryDirectory()as d:
   f=Path(d)/'test-only.json';f.write_text(json.dumps(c));a=args(recording_audio_provenance_source='1'*40,microphone_dual_calibration=f);p=m.resolve(a)
   self.assertEqual(p['calibrationSha256'],hashlib.sha256(f.read_bytes()).hexdigest());self.assertEqual((a.microphone_dual_delay_q8,a.microphone_dual_right_gain_q15,a.microphone_dual_invert_right),(128,40000,True));self.assertFalse(p['noiseReductionQualified'])
   self.assertIn('CALIBRATION_PRESENT 1',m.write_identity(Path(d),p).read_text())
   for key,value in [('synthetic',True),('automaticApply',True),('knownSingleSourceCallerDeclared',False),('deviceUid','0'*24),('synchronousSamples',32001),('maxDelaySamples',float('nan')),('delayQ8',2048),('rightGainQ15',1),('recordingToken',0)]:
    v=copy.deepcopy(c);v[key]=value;f.write_text(json.dumps(v))
    with self.subTest(key=key),self.assertRaises(ValueError):m.resolve(args(recording_audio_provenance_source='1'*40,microphone_dual_calibration=f))
   for change in ['missing','overlap','drifting_gain','altered_limits']:
    v=copy.deepcopy(c)
    if change=='missing':v.pop('temporalStability')
    elif change=='overlap':v['temporalStability']['windows'][1]['firstSample']=15999
    elif change=='drifting_gain':v['temporalStability']['windows'][1]['rightGainQ15']=32768
    else:v['temporalStability']['maximumGainSpreadDb']=9.0
    f.write_text(json.dumps(v))
    with self.subTest(temporal=change),self.assertRaisesRegex(ValueError,'Temporal calibration'):
     m.resolve(args(recording_audio_provenance_source='1'*40,microphone_dual_calibration=f))
   f.write_text(json.dumps(c)[:-1]+',"delayQ8":0}')
   with self.assertRaises(ValueError):m.resolve(args(recording_audio_provenance_source='1'*40,microphone_dual_calibration=f))
if __name__=='__main__':unittest.main()
