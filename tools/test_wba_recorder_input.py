"""Exercise the real button replay and shared recorder/desktop gesture state."""
from pathlib import Path
import hashlib,json,subprocess,sys
root=Path(__file__).resolve().parents[1]
app=root/'app/companion_pendant';out=root/'.cache/host-tests/wba-recorder-input';out.mkdir(parents=True,exist_ok=True)
files=[app/'power/tests/test_recorder_input.c',app/'power/wba_button.c',app/'power/wba_button.h',app/'power/recorder_input.h']
vc=Path('C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Auxiliary/Build/vcvars64.bat')
exe=out/'test.exe';script=out/'compile.cmd'
args=['cl.exe','/nologo','/std:c11','/W4','/WX','/utf-8',*['/I'+str(app/p) for p in ['power','imu','storage']],str(files[0]),str(files[1]),'/Fe:'+str(exe)]
script.write_text('@echo off\ncall "'+str(vc)+'" >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n',encoding='utf-8')
for command,label in [(['cmd.exe','/d','/c',str(script)],'compile'),([str(exe)],'run')]:
    p=subprocess.run(command,cwd=out,capture_output=True,text=True)
    (out/(label+'.log')).write_text(p.stdout+p.stderr,encoding='utf-8')
    if p.returncode:print(p.stdout+p.stderr);raise SystemExit(p.returncode)
result={'result':'PASS_HOST_ONLY','hardwareAccess':False,'stdout':p.stdout,
    'sourceSha256':{str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(p.stdout)
