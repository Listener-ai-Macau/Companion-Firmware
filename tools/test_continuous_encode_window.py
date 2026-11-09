"""Compile the production core and real Opus against denied encode windows."""
from pathlib import Path
import argparse,json,subprocess,hashlib
from verify_wba_spi_nor_adapter import find_vsdevcmd
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
p.add_argument('--opus-lib',type=Path,required=True)
p.add_argument('--before-engine',action='store_true',help='Use HEAD core with candidate port header; expect regression reproduction')
a=p.parse_args();root=Path(__file__).resolve().parents[1];out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
rec=root/'app/companion_pendant/recording'
names=['companion_continuous_recording','companion_segment_audio','companion_segment_catalog','companion_segment_reserve','companion_opus16_rt','companion_range_receipt','companion_range_reclaim']
files=[rec/'tests/test_continuous_encode_window.c',*[rec/(n+'.c') for n in names]]
if a.before_engine:
    before=out/'before_engine.c';before.write_bytes(subprocess.check_output(['git','show','HEAD:app/companion_pendant/recording/companion_continuous_recording.c'],cwd=root));files[1]=before
args=['cl.exe','/nologo','/TC','/std:c11','/O2','/W4','/wd4100','/utf-8','/MD','/D_CRT_SECURE_NO_WARNINGS',
    '/DCOMPANION_OPUS16_WBA_LOWDELAY=1','/DCOMPANION_OPUS16_ENCODER_BYTES=65536','/DCOMPANION_OPUS16_STDIO_ERRORS=0',
    '/I'+str(rec),'/I'+str(root/'third_party/denzic-platform/audio/embedded/c/include'),'/I'+str(root/'third_party/opus/include'),
    *map(str,files),'/Fe:'+str(out/'test.exe'),'/link',str(a.opus_lib.resolve())]
if a.before_engine:args.insert(1,'/DCOMP_TEST_BEFORE_ENGINE=1')
batch=out/'compile.cmd';batch.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
results={}
for stage,cmd in [('compile',['cmd.exe','/d','/c',str(batch)]),('run',[str(out/'test.exe')])]:
    r=subprocess.run(cmd,cwd=out,capture_output=True,text=True,encoding='utf-8',errors='replace');(out/(stage+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8');results[stage]={'exitCode':r.returncode,'output':r.stdout+r.stderr};print(stage,r.returncode,r.stdout+r.stderr,flush=True)
    if stage=='compile' or not a.before_engine:r.check_returncode()
    elif r.returncode==0:raise AssertionError('old engine unexpectedly passed rejected-window check')
result={'beforeEngine':a.before_engine,'softwareOnly':True,'results':results,'sources':{str(f.relative_to(root) if f.is_relative_to(root) else f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}}
if not a.before_engine:
    platform=root/'platform/stm32wba55_companion_v11';raw=(platform/'product_app.c').read_text()
    begin=raw.index('static bool recording_encode_window(');end=raw.index('\nstatic bool recording_work_poll(',begin)
    model=out/'policy.c';model.write_text((platform/'tests/test_recording_encode_admission.c').read_text().replace('/* @PRODUCTION_ENCODE_ADMISSION@ */',raw[begin:end]))
    policy_args=['cl.exe','/nologo','/TC','/std:c11','/O2','/W4','/WX','/utf-8','/I'+str(platform),str(model),'/Fe:'+str(out/'policy.exe')]
    batch.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(policy_args)+'\n')
    for stage,cmd in [('policy-compile',['cmd.exe','/d','/c',str(batch)]),('policy-run',[str(out/'policy.exe')])]:
        r=subprocess.run(cmd,cwd=out,capture_output=True,text=True,encoding='utf-8',errors='replace');(out/(stage+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8');results[stage]={'exitCode':r.returncode,'output':r.stdout+r.stderr};print(stage,r.returncode,r.stdout+r.stderr,flush=True);r.check_returncode()
    result['productionAdmissionSha256']=hashlib.sha256(raw[begin:end].encode()).hexdigest()
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
