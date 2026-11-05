"""Compare fixed-point codec bytes under MSVC speed/size optimizations.

This tests the real codec sources with deterministic digital PCM, not a board
microphone. MSVC allocation compatibility is isolated to a cache config. It
does not execute the ARM GCC/LTO binary or establish physical 20ms timing.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.cache/ce-geometry-20261005/opus-optimization'


def main():
    opus=ROOT/'third_party/opus';recording=ROOT/'app/companion_pendant/recording'
    manifest=opus/'companion_opus_encode_sources.mk'
    sources=[opus/name for name in re.findall(r'\$\(OPUS_ROOT\)/([^\s]+\.c)',manifest.read_text())]
    sources += [recording/'companion_opus16_rt.c',recording/'companion_silk_live_fast.c',
                ROOT/'tools/fixtures/wba_opus_optimization_test.c']
    OUT.mkdir(parents=True,exist_ok=True)
    config=(opus/'config.h').read_text().replace('#define VAR_ARRAYS 1','/* MSVC lacks C VLA; use the existing USE_ALLOCA path. */')
    (OUT/'config.h').write_text(config)
    includes=[OUT,recording,opus,*(opus/name for name in ('include','celt','silk','silk/fixed','src'))]
    dev=find_vsdevcmd()
    if not dev:raise RuntimeError('MSVC unavailable for codec comparison')
    results={}
    for name,option in [('speed','/O2 /Ot /Ob2'),('size','/O1 /Os /Ob1')]:
        out=OUT/name;out.mkdir(exist_ok=True)
        # Use 32-bit pointers like Cortex-M33. On x64 the same encoder struct
        # needs 36 extra bytes and cannot fit the unchanged product arena.
        objects=[];commands=[f'@echo off\ncall "{dev}" -arch=x86 -host_arch=amd64 >nul',
                            'if errorlevel 1 exit /b %errorlevel%']
        common='/nologo /TC /std:c11 /utf-8 /D_CRT_SECURE_NO_WARNINGS /DOPUS_BUILD /DFIXED_POINT /DDISABLE_FLOAT_API /DHAVE_CONFIG_H /DCOMPANION_SILK_LIVE_FAST=1 '
        common+=' '.join(f'/I"{p}"' for p in includes)
        for index,source in enumerate(sources):
            obj=out/f'{index:03d}.obj';objects.append(obj)
            commands += [f'cl.exe {common} {option} /c "{source}" /Fo:"{obj}"',
                         'if errorlevel 1 exit /b %errorlevel%']
        exe=out/'encode.exe';response=out/'link.rsp'
        response.write_text('\n'.join(f'"{obj}"' for obj in objects)+f'\n/OUT:"{exe}"\n')
        commands += [f'link.exe /NOLOGO "@{response}"','if errorlevel 1 exit /b %errorlevel%']
        script=out/'build.cmd';script.write_text('\n'.join(commands)+'\n')
        build=subprocess.run(['cmd.exe','/d','/c',str(script)],cwd=out,text=True,capture_output=True)
        (out/'build.log').write_text(build.stdout+build.stderr)
        if build.returncode:raise RuntimeError(f'{name} compilation failed; see {out / "build.log"}')
        payload=out/'packets.bin'
        ran=subprocess.run([str(exe),str(payload)],cwd=out,text=True,capture_output=True)
        (out/'encode.log').write_text(ran.stdout+ran.stderr)
        if ran.returncode:raise RuntimeError(f'{name} encoding failed; see {out / "encode.log"}')
        results[name]={'bytes':payload.stat().st_size,'sha256':hashlib.sha256(payload.read_bytes()).hexdigest(),
                       'output':ran.stdout.strip(),'compiler_flags':option}
    identical=(OUT/'speed/packets.bin').read_bytes()==(OUT/'size/packets.bin').read_bytes()
    report={'schema':'companion.wba.opus-optimization.host.v1',
            'result':'PASS_HOST_CODEC_BITEXACT' if identical else 'FAIL_CODEC_OPTIMIZATION_DRIFT',
            'compiler':'MSVC x86; speed /O2 vs size /O1, not ARM GCC execution',
            'digital_pcm_frames_per_variant':2880,'results':results,
            'hardwareAcceptance':'NOT_RUN','physical_realtime_timing':'NOT_RUN',
            'fullChainAcceptance':'NOT_RUN','arm_binary_executed':False,
            'sourceSha256':{source.relative_to(ROOT).as_posix():hashlib.sha256(source.read_bytes()).hexdigest()
                            for source in [*sources,manifest,opus/'config.h',Path(__file__)]}}
    (OUT/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'result':report['result'],'results':results,'report':str(OUT/'result.json')}))
    return 0 if identical else 1


if __name__=='__main__':raise SystemExit(main())
