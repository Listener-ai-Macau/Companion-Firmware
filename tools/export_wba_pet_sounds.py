#!/usr/bin/env python3
"""Audition production PCM synthesis; no playback, device use or hardware test."""
from pathlib import Path
import argparse,hashlib,json,subprocess,wave
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    source=ROOT/'app/companion_pendant/playback/speaker_playback.c'
    adapter=source.parent/'tests/export_speaker_cues.c'
    header=source.with_suffix('.h');exe=out/'speaker-audition.exe'
    tracked=[source,adapter,header,Path(__file__)];before={str(path.relative_to(ROOT)):sha(path) for path in tracked}
    command=['cl.exe','/nologo','/std:c11','/W4','/WX',f'/I{source.parent}',str(source),str(adapter),f'/Fe:{exe}']
    script=out/'build-audition.cmd'
    script.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(command)+'\n',encoding='utf-8')
    result=subprocess.run(['cmd.exe','/d','/c',str(script)],cwd=out,capture_output=True,text=True)
    (out/'build-audition.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    result.check_returncode();subprocess.run([str(exe)],cwd=out,check=True)
    names=('confirm','record-start','record-stop','error','pet-greeting','pet-content','pet-playful','pet-shy')
    sounds=[];combined=bytearray()
    for name in names:
        raw=(out/(name+'.pcm')).read_bytes();path=out/(name+'.wav')
        with wave.open(str(path),'wb') as audio:
            audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(16000);audio.writeframes(raw)
        sounds.append({'file':path.name,'sha256':sha(path),'seconds':len(raw)/32000})
        if name.startswith('pet-'):combined.extend(raw+b'\0'*16000)
    with wave.open(str(out/'pet-sounds-audition.wav'),'wb') as audio:
        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(16000);audio.writeframes(combined)
    if before!={str(path.relative_to(ROOT)):sha(path) for path in tracked}:raise RuntimeError('PCM source changed during export')
    receipt={'scope':'PRODUCTION_PCM_DESIGN_AUDITION','volumePercent':25,'sampleRate':16000,
        'hardwareListening':'NOT_RUN','flashed':False,'sounds':sounds,'sourceSha256':before,
        'order':['迎接','舒服','俏皮','害羞'],'mixFile':'pet-sounds-audition.wav','mixSha256':sha(out/'pet-sounds-audition.wav')}
    (out/'sound-design.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('PRODUCTION_PCM_AUDITION_EXPORTED',out/'pet-sounds-audition.wav')
if __name__=='__main__':main()
