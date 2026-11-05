#!/usr/bin/env python3
"""Actual C V1 relocation and journal, simulated NOR only; never touches a board."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd
ROOT=Path(__file__).resolve().parents[1]

def run(command,out,name):
 r=subprocess.run(command,cwd=out,capture_output=True,text=True)
 log=out/(name+'.log');log.write_text(r.stdout+r.stderr,encoding='utf-8')
 if r.returncode:raise RuntimeError('\n'.join((r.stdout+r.stderr).splitlines()[:18])+f'\nsee {log}')
 return r.stdout+r.stderr

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ROOT/'.cache/wba-flash-migration-host');ap.add_argument('--ui',type=Path,default=ROOT/'.cache/wba-product-resources/ui-partition.bin');a=ap.parse_args()
 out=a.output.resolve();out.mkdir(parents=True,exist_ok=True);ui=a.ui.resolve()
 storage=ROOT/'app/companion_pendant/storage';recording=ROOT/'app/companion_pendant/recording';update=ROOT/'app/companion_pendant/update';epaper=ROOT/'app/companion_pendant/epaper'
 upstream=ROOT/'third_party/denzic-platform/ota/embedded/c'
 sources=[storage/'tests/test_wba_flash_migration.c',storage/'wba_flash_migration.c',storage/'wba_shared_pool.c',storage/'wba_shared_pool_guard.c',recording/'companion_recording_journal.c',recording/'companion_recording_resource_pack.c',epaper/'asset_store.c',update/'wba_update_service.c',upstream/'src/denzic_ota_v1.c']
 headers=[storage/'wba_flash_migration.h',storage/'wba_shared_pool.h',recording/'companion_recording_journal.h',recording/'companion_recording_wire.h',recording/'companion_recording_resource_pack.h',update/'wba_storage_layout.h',update/'wba_update_service.h',epaper/'asset_store.h']
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 frozen={p.relative_to(ROOT).as_posix():sha(p) for p in [*sources,*headers,Path(__file__).resolve()]};ui_sha=sha(ui)
 include=[storage,recording,update,epaper,upstream/'include'];flags=' '.join(f'/I"{p}"' for p in include);exe=out/'migration-test.exe';cmd=out/'compile.cmd'
 cmd.write_text(f'@call "{find_vsdevcmd()}" -arch=x64 >nul\n@if errorlevel 1 exit /b %errorlevel%\n@cd /d "{out}"\n'+
  f'@cl /nologo /TC /std:c11 /O2 /W4 /WX /wd4295 /c {flags} "{sources[-1]}" /Fo:"{out / "denzic_ota_v1.obj"}"\n@if errorlevel 1 exit /b %errorlevel%\n'+
  f'@cl /nologo /TC /std:c11 /O2 /W4 /WX {flags} '+' '.join(f'"{p}"' for p in sources[:-1])+f' /Fe:"{exe}" /link "{out / "denzic_ota_v1.obj"}" /INCREMENTAL:NO /OPT:REF\n',encoding='utf-8')
 run(['cmd','/d','/c',str(cmd)],out,'compile');tested=run([str(exe),str(ui)],out,'host-test');assert tested.startswith('PASS_FLASH_MIGRATION_SOFTWARE_ONLY')
 cc=shutil.which('arm-none-eabi-gcc');assert cc;obj=out/'migration.o'
 run([cc,'-std=c11','-mcpu=cortex-m33','-mthumb','-Os','-Wall','-Wextra','-Werror','-Wconversion','-Wshadow','-pedantic',*[f'-I{p}' for p in include],'-fstack-usage','-c',str(sources[1]),'-o',str(obj)],out,'m33')
 assert all(sha(ROOT/p)==h for p,h in frozen.items()),'source changed during test'
 assert sha(ui)==ui_sha,'UI fixture changed during test'
 report=dict(schema='companion.flash-migration.software.v1',result='PASS_SOFTWARE_FAULT_MODEL_ONLY',hardwareAcceptance='NOT_RUN',fullChainAcceptance='NOT_RUN',flashV2Enabled=False,relocationOnly=True,
  testStdout=tested,m33ObjectSha256=sha(obj),m33StaticStack=(out/'migration.su').read_text(),uiFixture=dict(path=str(ui),sha256=ui_sha),source_sha256=frozen)
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(tested.strip());print(out/'result.json')
if __name__=='__main__':main()
