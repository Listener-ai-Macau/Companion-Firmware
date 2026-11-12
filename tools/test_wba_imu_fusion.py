from pathlib import Path
import subprocess,json,hashlib
root=Path(__file__).resolve().parents[1]
out=Path("E:/CodexData/Companion/.build-cache/imu-pointer20261112/fusion-host-test");out.mkdir(parents=True,exist_ok=True)
v=root/"third_party/imu-fusion/Fusion";imu=root/"app/companion_pendant/imu"
sources=[imu/"tests/test_imu_fusion.c",imu/"imu_fusion.c",*[v/n for n in ["FusionAhrs.c","FusionBias.c","FusionConvention.c"]]]
cmd=["cl.exe","/nologo","/std:c11","/O2","/W3","/I"+str(imu),*map(str,sources),"/Fe:"+str(out/"test.exe")]
script=out/"compile.cmd"
script.write_text('@echo off\ncall "C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Auxiliary/Build/vcvars64.bat" >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+"\n",encoding="utf-8")
result={}
for name,args in [("compile",["cmd.exe","/d","/c",str(script)]),("run",[str(out/"test.exe")])]:
    p=subprocess.run(args,cwd=out,capture_output=True,text=True)
    (out/(name+".log")).write_text(p.stdout+p.stderr,encoding="utf-8")
    print(p.stdout+p.stderr)
    p.check_returncode()
result={"result":"PASS_HOST_ONLY","stdout":p.stdout,"sourceSha256":{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sources}}
(out/"result.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
