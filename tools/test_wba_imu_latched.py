"""Old/current real drivers against ST-documented clear-on-read tap behavior."""
from pathlib import Path
import argparse,hashlib,json,subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[1];imu=root/'app/companion_pendant/imu';out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
rows={}
for label,fixed in [('baseline784',False),('candidate',True)]:
    folder=out/label;folder.mkdir()
    for name in ['lsm6dso.c','lsm6dso.h']:
        data=(imu/name).read_bytes() if fixed else subprocess.check_output(['git','show','e5995244ea044073722f8363af51207fc9a1114a:app/companion_pendant/imu/'+name],cwd=root)
        (folder/name).write_bytes(data)
    (folder/'test.c').write_bytes((imu/'tests/test_lsm6dso_latched.c').read_bytes())
    exe=folder/'test.exe';args=['cl.exe','/nologo','/std:c11','/W4','/WX',f'/DCOMP_TEST_IRQ_LATCH={int(fixed)}','/I'+str(folder),str(folder/'test.c'),str(folder/'lsm6dso.c'),'/Fe:'+str(exe)]
    batch=folder/'compile.cmd';batch.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
    for stage,cmd in [('compile',['cmd.exe','/d','/c',str(batch)]),('run',[str(exe)])]:
        r=subprocess.run(cmd,cwd=folder,capture_output=True,text=True);(folder/(stage+'.log')).write_text(r.stdout+r.stderr);r.check_returncode()
        if stage=='run':rows[label]=r.stdout.strip();print(label,r.stdout.strip(),flush=True)
result={'result':'PASS_ST_CLEAR_ON_READ_MODEL_SOFTWARE_ONLY','runs':rows,'physicalTapQualified':False,'hardwareAccess':False,
        'candidateSourceSha256':{n:hashlib.sha256((imu/n).read_bytes()).hexdigest() for n in ['lsm6dso.c','lsm6dso.h']}}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
