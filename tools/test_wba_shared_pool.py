#!/usr/bin/env python3
"""Actual C Flash V2 allocator with simulated NOR; no device operations."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd
ROOT=Path(__file__).resolve().parents[1]
def run(cmd,cwd):
 r=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True)
 name='compile' if cmd[0]=='cmd' else 'm33' if 'gcc' in cmd[0] else 'host-test'
 log=cwd/(name+'.log');log.write_text(r.stdout+r.stderr,encoding='utf-8')
 if r.returncode:raise RuntimeError('\n'.join((r.stdout+r.stderr).splitlines()[:18])+f'\nsee {log}')
 return r.stdout+r.stderr
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ROOT/'.cache/wba-shared-pool-host');a=ap.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
 storage=ROOT/'app/companion_pendant/storage';recording=ROOT/'app/companion_pendant/recording';update=ROOT/'app/companion_pendant/update'
 platform=ROOT/'third_party/denzic-platform/ota/embedded/c'
 sources=[storage/'tests/test_wba_shared_pool.c',storage/'wba_shared_pool.c',storage/'wba_shared_pool_guard.c',update/'wba_update_service.c',platform/'src/denzic_ota_v1.c']
 headers=[storage/'wba_shared_pool.h',storage/'wba_flash_migration.h',recording/'companion_recording_wire.h',update/'wba_update_service.h',update/'wba_storage_layout.h',update/'wba_flash_geometry.h']
 exe=out/'pool-test.exe';cmd=out/'compile.cmd'
 includes=[storage,recording,update,platform/'include']
 # C4295 is the existing upstream four-byte protocol magic literal, without
 # a C string terminator. Suppress it only for that unchanged dependency.
 include_flags=' '.join(f'/I"{p}"' for p in includes)
 cmd.write_text(f'@call "{find_vsdevcmd()}" -arch=x64 >nul\n@if errorlevel 1 exit /b %errorlevel%\n@cd /d "{out}"\n'+
  f'@cl /nologo /TC /std:c11 /O2 /W4 /WX /wd4295 /c {include_flags} "{sources[-1]}" /Fo:"{out / "denzic_ota_v1.obj"}"\n@if errorlevel 1 exit /b %errorlevel%\n'+
  f'@cl /nologo /TC /std:c11 /O2 /W4 /WX {include_flags} '+ ' '.join(f'"{p}"' for p in sources[:-1])+f' /Fe:"{exe}" /link "{out / "denzic_ota_v1.obj"}" /INCREMENTAL:NO /OPT:REF\n',encoding='utf-8')
 build=run(['cmd','/d','/c',str(cmd)],out);tested=run([str(exe)],out);assert tested.startswith('PASS_SHARED_POOL_SOFTWARE_ONLY')
 cc=shutil.which('arm-none-eabi-gcc');assert cc;obj=out/'pool.o'
 run([cc,'-std=c11','-mcpu=cortex-m33','-mthumb','-Wall','-Wextra','-Werror','-Wconversion','-Wshadow','-pedantic',*[f'-I{p}' for p in includes],'-fstack-usage','-c',str(sources[1]),'-o',str(obj)],out)
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 report=dict(schema='companion.shared-pool.software.v1',result='PASS_SOFTWARE_FAULT_MODEL_ONLY',hardwareAcceptance='NOT_RUN',fullChainAcceptance='NOT_RUN',flashV2Enabled=False,
  testStdout=tested,compileLog=build,m33ObjectSha256=sha(obj),m33StaticStack= (out/'pool.su').read_text(),source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in [*sources,*headers,Path(__file__).resolve()]})
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(tested.strip());print(out/'result.json')
if __name__=='__main__':main()
