from array import array
from pathlib import Path
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
import zlib

TOOLS=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(TOOLS))
import decode_wba_dual_mic_stream as decoder
import process_wba_dual_mic_pair as processor
import calibrate_wba_dual_mic as calibration


def patched(packet, offset, fmt, value):
    result=bytearray(packet);struct.pack_into(fmt,result,offset,value)
    struct.pack_into('<I',result,len(result)-4,zlib.crc32(result[:-4]));return bytes(result)


class PairStream(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='companion-dmic-stream-')
        self.root=Path(self.tmp.name)
        self.raw,self.expected=self.produce('normal')
        self.stream=self.root/'source.dmp';self.stream.write_bytes(self.raw)
        self.evidence=self.root/'capture.json'
        self.receipt=dict(schema='companion.dual-mic-pair-capture.v1',streamSha256=decoder.sha(self.raw),
            deviceUid='120011000d50335754363720',firmwareSource='120828ead1f3352ebded9af72ea0883cf88a3540',
            recordingToken=78,recordingId=9,sourceSampleOffset=640,sampleRateHz=16000,
            sampleCount=32000,blockCount=200,clippedLeft=0,clippedRight=0,synthetic=True,
            processedChannelMask=3,sourcePositionFromCapture=True,captureKind='SOFTWARE_FIXTURE',
            processingStage='POST_CHANNEL_GAIN_DC_PRE_BEAMFORM_PCM16',completed=True,
            captureFaultCounters={key:0 for key in decoder.FAULT_COUNTERS})
        self.evidence.write_text(json.dumps(self.receipt))

    def tearDown(self):
        self.tmp.cleanup()

    def produce(self, mode):
        stream=self.root/(mode+'.dmp');expected=self.root/(mode+'.pcm')
        subprocess.run([os.environ['DUAL_STREAM_DRIVER'],mode,str(stream),str(expected)],check=True)
        return stream.read_bytes(),expected.read_bytes()

    def bundle(self,name='decoded',use_case='GENERAL_DUAL_MIC_CAPTURE'):
        return decoder.create_bundle(self.stream,self.evidence,self.root/name,use_case=use_case)

    def test_production_pdm_pair_roundtrip_preserves_each_channel_and_source_axis(self):
        pcm,identity=decoder.decode(self.raw)
        self.assertEqual(pcm,self.expected)
        values=array('h',pcm)
        self.assertNotEqual(values[::2],values[1::2])
        self.assertEqual(identity['sampleCount'],32000)
        self.assertEqual(identity['sourceSampleOffset'],640)
        self.assertTrue(identity['synthetic'])
        before=[p.read_bytes()for p in [self.stream,self.evidence]]
        result=self.bundle();dest=self.root/'decoded'
        self.assertEqual((dest/'original-pair.dmp').read_bytes(),self.raw)
        with wave.open(str(dest/'original-pair.wav'),'rb')as wav:
            self.assertEqual((wav.getnchannels(),wav.getsampwidth(),wav.getframerate(),wav.getnframes()),(2,2,16000,32000))
            self.assertEqual(wav.readframes(32000),self.expected)
        source=json.loads((dest/'source.json').read_bytes())
        self.assertEqual(source['captureEvidenceSha256'],decoder.sha(before[1]))
        self.assertEqual(source['useCase'],'GENERAL_DUAL_MIC_CAPTURE')
        self.assertFalse(result['authenticatedBoardTransport'])
        self.assertFalse(result['physicalNoiseReductionQualified'])
        self.assertEqual([p.read_bytes()for p in [self.stream,self.evidence]],before)

    def test_real_pdm_missing_rejected_stale_copy_and_sink_overflow_do_not_become_clean_audio(self):
        for mode in ['gap','readfail','reject','overflow']:
            with self.subTest(mode=mode):
                raw,_=self.produce(mode)
                with self.assertRaisesRegex(ValueError,'invalid capture'):
                    decoder.decode(raw)

    def test_dropped_duplicated_reordered_and_fabricated_source_indices_are_refused(self):
        h=self.raw[:80];packets=[self.raw[80+i*664:80+(i+1)*664]for i in range(200)];end=self.raw[-48:]
        variants=[h+b''.join(packets[1:])+end,h+packets[0]+b''.join(packets)+end,
            h+packets[1]+packets[0]+b''.join(packets[2:])+end,
            h+patched(packets[0],8,'<Q',800)+b''.join(packets[1:])+end]
        for raw in variants:
            with self.assertRaises(ValueError):decoder.decode(raw)

    def test_crc_terminal_count_and_trailing_data_fail_closed(self):
        changed=bytearray(self.raw);changed[110]^=1
        variants=[bytes(changed),self.raw[:-1],self.raw[:-48],self.raw+b'extra',
            self.raw[:-48]+patched(self.raw[-48:],4,'<I',199),
            self.raw[:-48]+patched(self.raw[-48:],28,'<I',123),
            self.raw[:-48]+patched(self.raw[-48:],36,'<I',123),
            self.raw[:-48]+patched(self.raw[-48:],16,'<I',8)]
        for raw in variants:
            with self.assertRaises(ValueError):decoder.decode(raw)

    def test_geometry_flags_origin_and_precision_are_explicit(self):
        h=self.raw[:80];rest=self.raw[80:]
        for offset,fmt,value in [(8,'<I',8000),(14,'<B',1),(15,'<B',1),(68,'<I',2),(72,'<I',1),(56,'<Q',1<<60)]:
            with self.subTest(offset=offset):
                with self.assertRaises(ValueError):decoder.decode(patched(h,offset,fmt,value)+rest)
        for key,value in [('deviceUid','0'*24),('recordingToken',79),('firmwareSource','1'*40),
            ('sampleCount',31999),('synthetic',False),('completed',False),('processedChannelMask',1),
            ('sourcePositionFromCapture',False),('captureKind','BOARD_SAI_PDM')]:
            bad=dict(self.receipt);bad[key]=value
            with self.subTest(key=key):
                with self.assertRaises(ValueError):decoder.validate_receipt(bad,self.raw,decoder.decode(self.raw)[1])

    def test_capture_fault_counters_missing_or_nonzero_cannot_be_omitted(self):
        for key in decoder.FAULT_COUNTERS:
            for value in [None,1,False]:
                bad=dict(self.receipt,captureFaultCounters=dict(self.receipt['captureFaultCounters']))
                if value is None:bad['captureFaultCounters'].pop(key)
                else:bad['captureFaultCounters'][key]=value
                with self.assertRaises(ValueError):decoder.validate_receipt(bad,self.raw,decoder.decode(self.raw)[1])
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            decoder.unique_json(b'{"completed":true,"completed":false}')

    def test_clipping_retains_true_original_and_is_not_eligible_for_unclipped_enhancement(self):
        raw,expected=self.produce('clip');pcm,identity=decoder.decode(raw)
        self.assertEqual(pcm,expected);self.assertEqual((identity['clippedLeft'],identity['clippedRight']),(200,200))
        self.stream.write_bytes(raw)
        receipt=dict(self.receipt,**identity);receipt['streamSha256']=decoder.sha(raw)
        self.evidence.write_text(json.dumps(receipt));self.bundle()
        source=json.loads((self.root/'decoded/source.json').read_bytes())
        self.assertEqual(source['processingStage'],'POST_CHANNEL_GAIN_DC_PRE_BEAMFORM_PCM16_CLIPPED')
        with self.assertRaisesRegex(ValueError,'Clipped'):
            processor.read_pair((self.root/'decoded/original-pair.wav').read_bytes())

    def test_bundle_does_not_replace_existing_output_or_publish_changed_inputs(self):
        self.bundle()
        before=(self.root/'decoded/original-pair.wav').read_bytes()
        with self.assertRaisesRegex(ValueError,'already exists'):self.bundle()
        self.assertEqual((self.root/'decoded/original-pair.wav').read_bytes(),before)
        original=decoder.validate_receipt
        def racing(*args):
            original(*args);self.evidence.write_text('changed')
        decoder.validate_receipt=racing
        try:
            with self.assertRaisesRegex(ValueError,'changed'):self.bundle('raced')
        finally:decoder.validate_receipt=original
        self.assertFalse((self.root/'raced').exists());self.assertEqual(list(self.root.glob('*.partial-*')),[])

    def test_new_stream_to_existing_processor_matches_production_beamformer_exactly(self):
        self.bundle(use_case='FRONT_CLOSE_TALK_CANDIDATE');dest=self.root/'decoded'
        probe=self.root/'probe.log';probe.write_bytes(Path(os.environ['DUAL_SYNTHETIC_PROBE']).read_bytes())
        cal=calibration.estimate(calibration.parse_probe(probe.read_text(),77),known_single_source=True,max_delay_samples=2)
        cal.update(deviceUid=self.receipt['deviceUid'],firmwareSource=self.receipt['firmwareSource'],recordingToken=77,
            knownSingleSourceCallerDeclared=True,probeLogSha256=decoder.sha(probe.read_bytes()))
        calibration_path=self.root/'calibration.json';calibration_path.write_text(json.dumps(cal))
        result=processor.create_bundle(dest/'original-pair.wav',dest/'source.json',calibration_path,
            probe,dest/'capture-evidence.json',self.root/'enhanced')
        inp=self.root/'input.pcm';inp.write_bytes(self.expected);output=self.root/'reference.pcm'
        subprocess.run([os.environ['DUAL_C_DRIVER'],str(inp),str(output),str(cal['delayQ8']),str(cal['rightGainQ15']),str(int(cal['invertRight']))],check=True)
        with wave.open(str(self.root/'enhanced/enhanced-candidate.wav'),'rb')as wav:
            self.assertEqual(wav.readframes(wav.getnframes()),output.read_bytes())
        self.assertEqual(result['outputSourceSampleOffset'],640+result['withheldHistorySamples'])
        self.assertTrue(result['synthetic']);self.assertFalse(result['automaticallyApplied'])


if __name__=='__main__':unittest.main()
