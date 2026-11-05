from array import array
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest
import wave

sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_calibrate_wba_dual_mic_pair import PairCalibration


class Comparison(PairCalibration):
    def read_mono(self,path):
        with wave.open(str(path),'rb') as w:
            self.assertEqual((w.getnchannels(),w.getsampwidth(),w.getframerate()),(1,2,16000))
            values=array('h',w.readframes(w.getnframes()))
        if sys.byteorder!='little':values.byteswap()
        return values

    def test_same_take_references_share_output_window_without_gain_normalization(self):
        from process_wba_dual_mic_pair import sha
        result=self.run_bundle()
        folder=self.root/'comparison/comparison'
        receipt=json.loads((folder/'processing.json').read_bytes())
        source=array('h',self.pcm)
        if sys.byteorder!='little':source.byteswap()
        skip=receipt['withheldHistorySamples']
        self.assertEqual(self.read_mono(folder/'comparison-left.wav'),source[2*skip::2])
        self.assertEqual(self.read_mono(folder/'comparison-right.wav'),source[2*skip+1::2])
        self.assertGreater(skip,0)
        comparison=receipt['comparison']
        self.assertEqual(comparison['normalization'],'NONE')
        self.assertFalse(comparison['acousticTimeAlignmentQualified'])
        self.assertEqual(comparison['sourceSampleOffset'],640+skip)
        self.assertEqual(comparison['sampleCount'],32000-skip)
        roles=receipt['artifacts']
        for name in ['comparison-left.wav','comparison-right.wav','enhanced-candidate.wav']:
            self.assertEqual(roles[name]['sha256'],sha((folder/name).read_bytes()))
            self.assertEqual(roles[name]['sourceSampleOffset'],640+skip)
            self.assertEqual(roles[name]['sampleCount'],32000-skip)
        self.assertEqual(roles['original-pair.wav']['sourceSampleOffset'],640)
        self.assertEqual(roles['original-pair.wav']['sampleCount'],32000)
        self.assertEqual(roles['original-pair.wav']['channels'],['left','right'])
        self.assertFalse(result['physicalNoiseReductionQualified'])

    def test_gain_overload_is_counted_in_published_samples_not_hidden_in_saturation(self):
        from process_wba_dual_mic_pair import process_samples
        for sign in [1,-1]:
            for delay in [0,384,-384]:
                with self.subTest(sign=sign,delay=delay):
                    info={}
                    samples=array('h',[sign*30000,sign*30000]*160)
                    output,skip=process_samples(samples,delay,65535,False,info)
                    self.assertEqual(skip,(abs(delay)+255)//256)
                    self.assertEqual(info['outputClippedSamples'],len(output))
                    self.assertTrue(all(x==(32767 if sign>0 else -32768) for x in output))
                    clean={}
                    original,_=process_samples(array('h',[1000,-1000]*160),delay,32768,False,clean)
                    self.assertEqual(clean['outputClippedSamples'],0)
                    # Instrumentation never changes original production arithmetic.
                    self.assertEqual(original,process_samples(array('h',[1000,-1000]*160),delay,32768,False)[0])

    def test_processing_lineage_never_promotes_a_candidate_to_normal_product_audio(self):
        result=self.run_bundle()
        receipt=json.loads((self.root/'comparison/comparison/processing.json').read_bytes())
        self.assertEqual(receipt['artifacts']['comparison-left.wav']['role'],'UNPROCESSED_LEFT_REFERENCE')
        self.assertEqual(receipt['artifacts']['comparison-right.wav']['role'],'UNPROCESSED_RIGHT_REFERENCE')
        self.assertEqual(receipt['artifacts']['enhanced-candidate.wav']['role'],'DERIVED_FIXED_BEAMFORMER_CANDIDATE')
        self.assertEqual(receipt['outputClippedSamples'],0)
        self.assertFalse(receipt['candidateHasClipping'])
        self.assertFalse(receipt['automaticallyApplied'])
        self.assertFalse(receipt['speakerIdentityExtraction'])
        self.assertFalse(receipt['speechIntelligibilityQualified'])
        self.assertEqual(result['processingManifestSha256'],hashlib.sha256((self.root/'comparison/comparison/processing.json').read_bytes()).hexdigest())


if __name__=='__main__':unittest.main(defaultTest='Comparison')
