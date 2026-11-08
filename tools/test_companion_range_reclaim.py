"""Focused refactor-core verification. No firmware build/install or device I/O."""
from pathlib import Path
import hashlib,json,subprocess,sys
from verify_wba_spi_nor_adapter import find_vsdevcmd

root=Path(__file__).resolve().parents[1]
out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=False)
rec=root/'app/companion_pendant/recording'
sources=[rec/(n+'.c') for n in ['companion_range_receipt','companion_range_reclaim','companion_segment_audio','companion_segment_catalog']]
test=rec/'tests/test_companion_range_reclaim.c'
args=['cl.exe','/nologo','/W4','/WX','/std:c11','/TC','/O2','/MD','/I'+str(rec),str(test),*[str(p) for p in sources],'/Fe:'+str(out/'range_reclaim.exe')]
cmd=out/'compile.cmd'
cmd.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n',encoding='ascii')
for name,command in [('compile',['cmd.exe','/d','/c',str(cmd)]),('range_reclaim',[str(out/'range_reclaim.exe')])]:
    p=subprocess.run(command,cwd=out,capture_output=True,text=True,encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
    (out/(name+'.log')).write_text(p.stdout+p.stderr,encoding='utf-8');print(name,p.returncode,p.stdout,p.stderr,flush=True);p.check_returncode()
for source in sources[:2]:
    command=['arm-none-eabi-gcc','-std=c11','-mcpu=cortex-m33','-mthumb','-Os','-Wall','-Wextra','-Werror','-Wconversion','-Wshadow','-pedantic','-I'+str(rec),'-c',str(source),'-o',str(out/(source.stem+'.o'))]
    p=subprocess.run(command,cwd=out,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    (out/(source.stem+'-m33.log')).write_text(p.stdout+p.stderr,encoding='utf-8');print(source.stem,p.returncode,p.stdout,p.stderr,flush=True);p.check_returncode()
(out/'result.json').write_text(json.dumps({'result':'PASS_RANGE_RECLAIM_TRANSACTION_CORE','sourceSha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*sources,test,Path(__file__)]},'deviceAccessed':False,'installed':False,'physicalSpeedQualified':False,'catalogAndHostIntegrated':False},indent=2)+'\n')
