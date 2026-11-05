#!/usr/bin/env python3
"""Compile portable recording codecs; compare C-generated vectors to Type's fixture.

Host/M33 software contracts only. --write-golden initializes/updates reviewed
vectors explicitly; normal runs reject drift instead of silently refreshing.
"""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT=Path(__file__).resolve().parents[1]
REC=ROOT/'app/companion_pendant/recording'
TYPE=ROOT.parent/'Companion-Type/apps/windows/src-tauri/src/backend/recording_wire'

def run(command,cwd):
    r=subprocess.run(command,cwd=cwd,capture_output=True,text=True)
    if r.returncode: raise RuntimeError(r.stdout+r.stderr)
    return r.stdout+r.stderr

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output',type=Path,default=ROOT/'.cache/recording-wire-host'); ap.add_argument('--write-golden',action='store_true'); args=ap.parse_args()
    out=args.output.resolve(); out.mkdir(parents=True,exist_ok=True)
    source=REC/'tests/test_companion_recording_wire.c'
    payload=bytes.fromhex('434f503101011400803e00000100f8')
    fixture_sha='{'+','.join(f'0x{x:02x}' for x in hashlib.sha256(payload).digest())+'}'
    # Generated fixture digest only, never a trust key or production data.
    header=out/'wire-fixture.h'; header.write_text('#define WIRE_FIXTURE_SHA '+fixture_sha+'\n')
    exe=out/'recording-wire-test.exe'
    script=out/'compile.cmd'
    script.write_text(f'@call "{find_vsdevcmd()}" -arch=x64 >nul\n@if errorlevel 1 exit /b %errorlevel%\n@cd /d "{out}"\n@cl /nologo /TC /std:c11 /O2 /W4 /WX /I"{REC}" /FI"{header}" "{source}" /Fe:"{exe}"\n',encoding='utf-8')
    compile_log=run(['cmd','/d','/c',str(script)],out)
    vector=json.loads(run([str(exe)],out))
    golden=TYPE/'golden.json'
    if args.write_golden:
        TYPE.mkdir(exist_ok=True); golden.write_text(json.dumps(vector,indent=2)+'\n',encoding='utf-8')
    if vector!=json.loads(golden.read_text(encoding='utf-8')): raise RuntimeError('C/Type golden mismatch')
    cc=shutil.which('arm-none-eabi-gcc')
    if not cc: raise RuntimeError('Cortex-M33 compiler missing')
    obj=out/'recording-wire.o'
    run([cc,'-std=c11','-mcpu=cortex-m33','-mthumb','-Wall','-Wextra','-Werror','-Wconversion','-Wshadow','-pedantic',f'-I{REC}','-include',str(header),'-c',str(source),'-o',str(obj)],out)
    files=[source,REC/'companion_recording_wire.h',Path(__file__).resolve(),golden,TYPE/'legacy.rs']
    report=dict(schema='companion.recording-wire.host.v2',result='PASS_SOFTWARE_CONTRACT_ONLY',hardwareAcceptance='NOT_RUN',fullChainAcceptance='NOT_RUN',
        radioV2Enabled=False,journalV2Enabled=False,cGoldenMatchesType=True,compileLog=compile_log,
        source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},m33ObjectSha256=hashlib.sha256(obj.read_bytes()).hexdigest())
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n'); print('PASS_RECORDING_WIRE_SOFTWARE_CONTRACT_ONLY'); print(out/'result.json')

if __name__=='__main__': main()
