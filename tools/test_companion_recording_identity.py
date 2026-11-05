#!/usr/bin/env python3
"""Actual CSI1 allocator + NOR fault model; no board/erase/flash operations."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd
ROOT=Path(__file__).resolve().parents[1];REC=ROOT/'app/companion_pendant/recording'
def run(cmd,cwd):
 r=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True)
 if r.returncode:raise RuntimeError(r.stdout+r.stderr)
 return r.stdout+r.stderr
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ROOT/'.cache/recording-identity-host');ap.add_argument('--case',choices=['legacy','logical'],default='legacy');args=ap.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
 src=[REC/'tests/test_companion_recording_identity.c',REC/'companion_recording_identity.c'];headers=[REC/'companion_recording_identity.h',REC/'companion_recording_wire.h']
 exe=out/'identity-test.exe';cmd=out/'compile.cmd'
 cmd.write_text(f'@call "{find_vsdevcmd()}" -arch=x64 >nul\n@if errorlevel 1 exit /b %errorlevel%\n@cd /d "{out}"\n@cl /nologo /TC /std:c11 /O2 /W4 /WX /I"{REC}" '+ ' '.join(f'"{p}"' for p in src)+f' /Fe:"{exe}"\n',encoding='utf-8')
 build=run(['cmd','/d','/c',str(cmd)],out);tested=run([str(exe),*(['logical'] if args.case=='logical' else [])],out);assert tested.startswith('PASS logical-session CSI1 allocation' if args.case=='logical' else 'PASS_RECORDING_IDENTITY_SOFTWARE_ONLY')
 cc=shutil.which('arm-none-eabi-gcc');assert cc
 obj=out/'identity.o';run([cc,'-std=c11','-mcpu=cortex-m33','-mthumb','-Wall','-Wextra','-Werror','-Wconversion','-Wshadow','-pedantic',f'-I{REC}','-c',str(src[1]),'-o',str(obj)],out)
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 report=dict(schema='companion.recording-identity.software.v1',case=args.case,result='PASS_SOFTWARE_FAULT_MODEL_ONLY',hardwareAcceptance='NOT_RUN',fullChainAcceptance='NOT_RUN',testStdout=tested,compileLog=build,m33ObjectSha256=sha(obj),source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in [*src,*headers,Path(__file__).resolve()]})
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(tested.strip());print(out/'result.json')
if __name__=='__main__':main()
