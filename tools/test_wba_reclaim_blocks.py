#!/usr/bin/env python3
"""Run production NOR/catalogue/allocator block-reclaim ownership regressions.

Uses the command-level NOR model; no hardware timing qualification.
Output is an explicit new cache directory, with frozen inputs and logs.
"""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'app/companion_pendant'
REC=APP/'recording'
out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=False)
source=out/'source'
names=['companion_range_receipt','companion_range_reclaim','companion_segment_catalog','companion_segment_reserve','companion_segment_audio','wba_segment_storage',
       'wba_recording_recovery','wba_segment_discard_preview','wba_segment_discard_worker',
       'wba_segment_discard_control','wba_segment_discard_wire']
sources=[*[REC/(n+'.c')for n in names],APP/'storage/spi_nor_stm32wba.c']
cases=['wba_reclaim_blocks','companion_segment_reclaim_prefix','companion_segment_rotated','companion_range_receipt','companion_range_reclaim','companion_segment_catalog','wba_segment_storage','companion_segment_reserve_blank']
if len(sys.argv)>2:
    requested=sys.argv[2:];assert all(c in cases for c in requested);cases=requested
(out/'.cache/segmented-discard-20261029/candidate').mkdir(parents=True)
files=set(sources)|set(APP.rglob('*.h'))|set(REC.glob('tests/*.c'))|{ROOT/'tools/fixtures/wba_nor_suspend_test.c',Path(__file__)}
hashes={}
for p in files:
    rel=p.relative_to(ROOT);q=source/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes());hashes[rel.as_posix()]=hashlib.sha256(q.read_bytes()).hexdigest()
(out/'source.json').write_text(json.dumps(hashes,indent=2)+'\n')
includes=[source/'app/companion_pendant'/n for n in ['recording','storage','runtime','gatt','v1_features','update']]
def run(name,args):
    p=subprocess.run(args,cwd=out,capture_output=True,text=True,encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
    (out/(name+'.log')).write_text(p.stdout+p.stderr,encoding='utf-8')
    print(name,p.returncode,(p.stdout+p.stderr)[-1600:],flush=True);p.check_returncode()
for case in cases:
    case_sources=sources
    if case=='companion_segment_catalog':
        keep={'companion_range_receipt','companion_range_reclaim','companion_segment_audio','companion_segment_catalog','wba_recording_recovery','wba_segment_discard_preview',
              'wba_segment_discard_worker','wba_segment_discard_control','wba_segment_discard_wire'}
        case_sources=[p for p in sources if p.stem in keep]
    args=['cl.exe','/nologo','/W4','/WX','/std:c11','/TC','/O2','/MD',*['/I'+str(p)for p in includes],
          str(source/'app/companion_pendant/recording/tests'/('test_'+case+'.c')),
          *[str(source/p.relative_to(ROOT))for p in case_sources],'/Fe:'+str(out/(case+'.exe'))]
    cmd=out/(case+'.cmd');cmd.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n',encoding='ascii')
    run(case+'-compile',['cmd.exe','/d','/c',str(cmd)]);run(case,[str(out/(case+'.exe'))])
gcc=shutil.which('arm-none-eabi-gcc');assert gcc
for p in sources:
    run(p.stem+'-m33',[gcc,'-std=c11','-mcpu=cortex-m33','-mthumb','-Os','-Wall','-Wextra','-Werror','-Wconversion','-Wshadow','-pedantic',*['-I'+str(i)for i in includes],'-c',str(source/p.relative_to(ROOT)),'-o',str(out/(p.stem+'.o'))])
(out/'result.json').write_text(json.dumps({'result':'PASS_AFFECTED_RECLAIM_BLOCKS_SOFTWARE','cases':cases,'physicalTimingQualified':False,'installed':False},indent=2)+'\n')
