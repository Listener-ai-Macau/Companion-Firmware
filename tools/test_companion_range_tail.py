"""Affected catalogue tail/reboot checks, not physical speed qualification."""
from pathlib import Path
import hashlib,json,subprocess,sys
from verify_wba_spi_nor_adapter import find_vsdevcmd
root=Path(__file__).resolve().parents[1];rec=root/'app/companion_pendant/recording'
out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=False)
sources=[rec/(n+'.c')for n in ['companion_range_receipt','companion_range_reclaim','companion_segment_audio','companion_segment_catalog']]
files=[*sources,rec/'tests/test_companion_segment_reclaim_prefix.c',rec/'tests/test_companion_range_tail.c',rec/'tests/test_companion_unaligned_tail.c',rec/'tests/test_companion_short_unaligned_tail.c',rec/'tests/test_companion_short_block_tail.c',Path(__file__)]
report={'physicalSpeedQualified':False,'deviceAccessed':False,'sourceSha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()for p in files}}
try:
    for name,test in [('legacy-prefix','test_companion_segment_reclaim_prefix.c'),('range-tail','test_companion_range_tail.c'),('unaligned-tail','test_companion_unaligned_tail.c'),('short-unaligned-tail','test_companion_short_unaligned_tail.c'),('short-block-tail','test_companion_short_block_tail.c')]:
        args=['cl.exe','/nologo','/W4','/WX','/std:c11','/TC','/O2','/MD','/I'+str(rec),str(rec/'tests'/test),*map(str,sources),'/Fe:'+str(out/(name+'.exe'))]
        cmd=out/(name+'.cmd');cmd.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n',encoding='ascii')
        for stage,command in [('compile',['cmd.exe','/d','/c',str(cmd)]),('run',[str(out/(name+'.exe'))])]:
            p=subprocess.run(command,cwd=out,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
            (out/(name+'-'+stage+'.log')).write_text(p.stdout+p.stderr,encoding='utf-8');print(name,stage,p.returncode,p.stdout,p.stderr,flush=True);p.check_returncode()
    p=subprocess.run(['arm-none-eabi-gcc','-std=c11','-mcpu=cortex-m33','-mthumb','-Os','-Wall','-Wextra','-Werror','-Wconversion','-Wshadow','-pedantic','-I'+str(rec),'-c',str(rec/'companion_segment_catalog.c'),'-o',str(out/'catalog.o')],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    (out/'catalog-m33.log').write_text(p.stdout+p.stderr,encoding='utf-8');p.check_returncode()
    report['result']='PASS_RANGE_TAIL_BLOCK_AND_LEGACY_POWER_LOSS'
except BaseException as error:
    report.update(result='FAILED',error=repr(error));raise
finally:
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
