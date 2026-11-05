"""Package a deliberately authored short WAV for the finite speaker cue library.

No resampling, pitch change, denoising, loudness normalization or approval is
performed here. The input must already be mastered16kHz monoPCM16. PCM is the
lossless default; optional IMA4bit output includes its reconstructed audition
and quantitative error. Neither encoding establishes subjective sound quality.
"""
from pathlib import Path
import argparse,hashlib,json,re,warnings,wave
from datetime import datetime
import numpy as np

MIN_FRAMES=128;MAX_FRAMES=8000

def prepare(input_path,output,name,codec,source_url,license_name):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',name):raise ValueError('Invalid C symbol')
    with wave.open(str(input_path),'rb') as source:
        if (source.getnchannels(),source.getsampwidth(),source.getframerate(),source.getcomptype())!=(1,2,16000,'NONE'):
            raise ValueError('Input must be mastered16kHz monoPCM16 WAV')
        frames=source.getnframes();pcm=source.readframes(frames)
    if not MIN_FRAMES<=frames<=MAX_FRAMES or len(pcm)!=frames*2:
        raise ValueError('Finite clip requires128..8000 complete frames (8..500ms)')
    if not source_url.strip() or not license_name.strip():raise ValueError('Source and license provenance required')
    if codec=='pcm16':encoded=pcm;decoded=pcm;format_name='COMP_SPEAKER_CLIP_PCM16_LE'
    elif codec=='ima':
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',DeprecationWarning)
            import audioop
        encoded,_=audioop.lin2adpcm(pcm+(b'\0\0' if frames&1 else b''),2,(0,0))
        decoded,_=audioop.adpcm2lin(encoded,2,(0,0));decoded=decoded[:frames*2]
        format_name='COMP_SPEAKER_CLIP_IMA_ADPCM'
    else:raise ValueError('Unknown codec')
    output.mkdir(parents=True,exist_ok=False)
    (output/'payload.bin').write_bytes(encoded)
    with wave.open(str(output/'decoded.wav'),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(decoded)
    lines=['/* Authored source; not an automatic approval of license or sound quality. */',
           '#include "speaker_playback.h"',f'static const uint8_t {name}_data[{len(encoded)}] = {{']
    for offset in range(0,len(encoded),24):lines.append('    '+','.join(f'0x{b:02x}' for b in encoded[offset:offset+24])+',')
    lines+=['};',f'static const comp_speaker_clip_t {name} = {{',
            f'    {name}_data,{frames}u,{len(encoded)}u,0,0,{format_name}', '};','']
    (output/(name+'.h')).write_text('\n'.join(lines),encoding='utf-8')
    before=np.frombuffer(pcm,'<i2').astype(float);after=np.frombuffer(decoded,'<i2').astype(float);error=before-after
    power=float(np.dot(before,before));noise=float(np.dot(error,error))
    manifest=dict(schema='companion.authored_pet_clip.v1',createdAtLocal=datetime.now().astimezone().isoformat(timespec='seconds'),
        input=str(input_path.resolve()),inputSha256=hashlib.sha256(input_path.read_bytes()).hexdigest(),source=source_url,license=license_name,
        symbol=name,codec=codec,rate=16000,channels=1,frames=frames,durationMs=frames/16,bytes=len(encoded),
        initialPredictor=0,initialStepIndex=0,payloadSha256=hashlib.sha256(encoded).hexdigest(),decodedPcmSha256=hashlib.sha256(decoded).hexdigest(),
        lossless=(pcm==decoded),snrDb=(10*float(np.log10(power/noise)) if noise>0 and power>0 else None),
        sourcePeak=int(abs(before).max()),decodedPeak=int(abs(after).max()),maxAbsoluteError=int(abs(error).max()),
        ownerAccepted=None,subjectiveQualityQualified=False,installed=False,
        storageContract='Immutable directly memory-readable data for bound lifetime. Not a NOR/SPI reader, not arbitrary wire PCM or runtimeTTS.',
        noSignalProcessingApartFromChosenCodec=True)
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--name',required=True);parser.add_argument('--codec',choices=['pcm16','ima'],default='pcm16')
    parser.add_argument('--source',required=True);parser.add_argument('--license',required=True)
    a=parser.parse_args();result=prepare(a.input,a.output,a.name,a.codec,a.source,a.license)
    print(json.dumps(result,ensure_ascii=False,indent=2))
