from array import array
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_process_wba_dual_mic_pair import PairArtifacts,wav_bytes


class ClippedArtifact(PairArtifacts):
    def test_clipped_candidate_keeps_raw_audio_and_an_explicit_per_record_failure_flag(self):
        from process_wba_dual_mic_pair import sha
        self.pair.write_bytes(wav_bytes(array('h',[30000,30000]*32000)))
        self.manifest['pairWavSha256']=sha(self.pair.read_bytes())
        self.source.write_text(json.dumps(self.manifest))
        before=self.pair.read_bytes()
        receipt=self.bundle()
        folder=self.root/'result'
        self.assertEqual((folder/'original-pair.wav').read_bytes(),before)
        self.assertEqual(self.pair.read_bytes(),before)
        self.assertTrue(receipt['candidateHasClipping'])
        self.assertEqual(receipt['outputClippedSamples'],receipt['outputSamples'])
        self.assertFalse(receipt['automaticallyApplied'])
        self.assertFalse(receipt['physicalNoiseReductionQualified'])
        saved=json.loads((folder/'processing.json').read_bytes())
        self.assertEqual(saved['outputClippedSamples'],receipt['outputSamples'])
        self.assertEqual(saved['recordingId'],self.manifest['recordingId'])
        self.assertEqual(saved['recordingToken'],self.manifest['recordingToken'])


if __name__=='__main__':
    unittest.main(defaultTest='ClippedArtifact.test_clipped_candidate_keeps_raw_audio_and_an_explicit_per_record_failure_flag')
