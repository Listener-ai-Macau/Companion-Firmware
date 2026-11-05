"""Explicit image/profile identity for recorded audio; file-only build input.

This validates provenance/parameters, not physical denoising or calibration.
No hardware, network, record, playback or implicit profile enable occurs.
"""
from __future__ import annotations
import hashlib,json,math,re
from pathlib import Path
from dual_mic_calibration_stability import validate as validate_temporal_stability

def hex_value(value,n,name):
    if not isinstance(value,str)or not re.fullmatch(r'[0-9a-f]{'+str(n)+'}',value)or set(value)=={'0'}:
        raise ValueError('Invalid '+name)
    return value
def integer(value,lo,hi,name):
    if type(value)is not int or not lo<=value<=hi:raise ValueError('Invalid '+name)
    return value
def unique(pairs):
    out={}
    for key,value in pairs:
        if key in out:raise ValueError('Duplicate calibration field')
        out[key]=value
    return out
def resolve(args):
    source=args.recording_audio_provenance_source
    if source is not None:hex_value(source,40,'firmware source')
    if source and args.microphone_dual_pair_source and source!=args.microphone_dual_pair_source:
        raise ValueError('Audio-profile and paired-capture image source must match')
    result=dict(enabled=source is not None,firmwareSource=source,calibrationSha256=None,calibrationDeviceUid=None,
        normalPhysicalCalibrationQualified=False,noiseReductionQualified=False,automaticEnable=False)
    path=args.microphone_dual_calibration
    if path is not None:
        if not source:raise ValueError('Calibration requires explicit recorded-audio source identity')
        path=Path(path)
        if not path.is_file()or path.stat().st_size>2_000_000:raise ValueError('Finite calibration JSON file required')
        raw=path.read_bytes();c=json.loads(raw,object_pairs_hook=unique)
        if not isinstance(c,dict)or c.get('result')!='FIXED_FRONT_END_CALIBRATION_CANDIDATE_ONLY'or c.get('automaticApply')is not False or c.get('synthetic')is not False or c.get('knownSingleSourceCallerDeclared')is not True:
            raise ValueError('Need the explicit non-synthetic known-source candidate; no assumed calibration')
        uid=hex_value(c.get('deviceUid'),24,'calibration UID');hex_value(c.get('firmwareSource'),40,'calibration source image')
        for field in ['probeLogSha256','sourceStreamSha256','knownSourceSetupSha256']:hex_value(c.get(field),64,field)
        integer(c.get('recordingToken'),1,0xffffffff,'calibration recording token')
        integer(c.get('sampleRate'),16000,16000,'calibration sample rate')
        integer(c.get('synchronousSamples'),8006,32000,'calibration samples')
        bound=c.get('maxDelaySamples')
        if type(bound)not in(int,float)or not math.isfinite(bound)or not 0<bound<=2.5:raise ValueError('Actual calibration geometry bound required')
        delay=integer(c.get('delayQ8'),-2048,2048,'delay');gain=integer(c.get('rightGainQ15'),16384,65535,'right gain')
        invert=c.get('invertRight')
        if type(invert)is not bool or abs(delay)>bound*256:raise ValueError('Invalid calibration polarity/geometry')
        validate_temporal_stability(c)
        if args.microphone_dual_delay_q8 is not None and args.microphone_dual_delay_q8!=delay:raise ValueError('Delay contradicts calibration')
        if args.microphone_dual_right_gain_q15 is not None and args.microphone_dual_right_gain_q15!=gain:raise ValueError('Gain contradicts calibration')
        if args.microphone_dual_invert_right and not invert:raise ValueError('Polarity contradicts calibration')
        args.microphone_dual_delay_q8=delay;args.microphone_dual_right_gain_q15=gain;args.microphone_dual_invert_right=invert
        result.update(calibrationSha256=hashlib.sha256(raw).hexdigest(),calibrationDeviceUid=uid,
            calibrationSourceImage=c['firmwareSource'],calibrationPath=str(path.absolute()),parameters=dict(delayQ8=delay,rightGainQ15=gain,invertRight=invert))
    if source and args.microphone_dual_delay_q8 is not None and path is None:
        raise ValueError('Directional recorded audio requires its exact calibration file, not loose parameters')
    if args.microphone_dual_right_gain_q15 is None:args.microphone_dual_right_gain_q15=32768
    return result

def write_identity(out:Path,profile:dict):
    if not profile['enabled']:return None
    def data(value,n):
        value=value or '00'*n
        return '{'+','.join('0x'+value[i:i+2]for i in range(0,2*n,2))+'}'
    path=out/'wba_recording_audio_identity.h'
    text='/* Generated exact image/calibration identity, not acoustic qualification. */\n'
    text+='#define COMP_WBA_AUDIO_SOURCE_BYTES '+data(profile['firmwareSource'],20)+'\n'
    text+='#define COMP_WBA_AUDIO_CALIBRATION_SHA_BYTES '+data(profile['calibrationSha256'],32)+'\n'
    text+='#define COMP_WBA_AUDIO_CALIBRATION_UID_BYTES '+data(profile['calibrationDeviceUid'],12)+'\n'
    text+='#define COMP_WBA_AUDIO_CALIBRATION_PRESENT '+str(int(profile['calibrationSha256']is not None))+'\n'
    path.write_text(text,encoding='ascii');return path
