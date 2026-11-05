"""Export four actual firmware cues at the runtime's default 25% digital gain."""
from pathlib import Path
import hashlib
import json
import struct
import subprocess
import wave
from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT = Path(__file__).resolve().parents[1]

def main():
    out = ROOT / '.cache/wba-audio-preview'
    out.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'app/companion_pendant/playback'
    log = out / 'build.log'
    log.write_text('')
    compiler_env = find_vsdevcmd()
    if not compiler_env:
        raise RuntimeError('MSVC unavailable')
    exe = out / 'export-cues.exe'
    sources = [source / 'speaker_playback.c', source / 'tests/export_speaker_cues.c']
    args = ['cl.exe', '/nologo', '/std:c11', '/W4', '/WX', f'/I{source}',
            *(str(p) for p in sources), f'/Fe:{exe}']
    command = out / 'build.cmd'
    command.write_text(f'@echo off\ncall "{compiler_env}" -arch=amd64 -host_arch=amd64 >nul\n'
                       'if errorlevel 1 exit /b %errorlevel%\n' + subprocess.list2cmdline(args) + '\n')
    run(['cmd.exe', '/d', '/c', str(command)], out, log)
    run([str(exe)], out, log)
    combined = bytearray(16000)  # half-second introduction silence
    cues = []
    labels=('light pet chirp','two rising chirps','low contented purr','two soft questioning chirps')
    for index,name in enumerate(('confirm', 'record-start', 'record-stop', 'error')):
        pcm = (out / (name + '.pcm')).read_bytes()
        samples = struct.unpack('<' + 'h' * (len(pcm) // 2), pcm)
        if not samples or max(abs(v) for v in samples) == 0:
            raise RuntimeError('Silent cue: ' + name)
        # Endpoints and bounded digital gain catch envelope/indexing failures;
        # these checks do not judge how appealing the sound is to a listener.
        peak=max(abs(v) for v in samples)
        step=max(abs(a-b) for a,b in zip(samples,samples[1:]))
        if peak>1750 or samples[0]!=0 or samples[-1]!=0 or step>1200:
            raise RuntimeError('Pet cue envelope/gain discontinuity: '+name)
        with wave.open(str(out / (name + '.wav')), 'wb') as wav:
            wav.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
            wav.writeframes(pcm)
        cues.append({'cue': name, 'sound':labels[index], 'duration_ms': len(samples) / 16,
                     'peak_pcm': peak,'max_adjacent_step':step})
        combined.extend(pcm)
        combined.extend(bytes(24000))  # 750 ms between cues
    with wave.open(str(out / 'companion-cues.wav'), 'wb') as wav:
        wav.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
        wav.writeframes(combined)
    (out / 'manifest.json').write_text(json.dumps({
        'purpose': 'digital audition only; actual speaker loudness/timbre NOT_RUN',
        'volume_percent': 25, 'voice':'nonverbal_pet_v1', 'speech':False,'cues_in_order': cues,
        'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [*sources,source/'speaker_playback.h',Path(__file__)]},
        'wav_sha256': hashlib.sha256((out / 'companion-cues.wav').read_bytes()).hexdigest(),
    }, indent=2) + '\n')
    print(out / 'companion-cues.wav')

if __name__ == '__main__':
    main()
