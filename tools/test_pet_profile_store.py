"""Check real portable pet profile persistence with faulted NOR; no hardware/cloud."""
from pathlib import Path
import argparse, hashlib, json, subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT = Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    runtime=ROOT/'app/companion_pendant/runtime'
    sources=[runtime/'companion_pet_profile.c',runtime/'companion_pet_profile_store.c',runtime/'companion_pet_profile_wire.c',
             runtime/'tests/test_pet_profile_store.c']
    exe=out/'test.exe'
    args=['cl.exe','/nologo','/std:c11','/W4','/WX',f'/I{runtime}',
          f'/I{ROOT/"app/companion_pendant/storage"}',*(str(x)for x in sources),f'/Fe:{exe}']
    script=out/'build.cmd'
    script.write_text(f'@echo off\ncall "{find_vsdevcmd()}" -arch=amd64 -host_arch=amd64 >nul\n'
        'if errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n',encoding='utf-8')
    result={'result':'PREPARING','hardware':False,'runtimeIntegration':False,'cloudCalls':0}
    try:
        q=subprocess.run(['cmd.exe','/d','/c',str(script)],cwd=out,capture_output=True)
        (out/'build.log').write_bytes(q.stdout+q.stderr);result['buildExit']=q.returncode
        assert q.returncode==0,(q.stdout+q.stderr).decode(errors='replace')
        q=subprocess.run([str(exe)],cwd=out,capture_output=True)
        (out/'test.log').write_bytes(q.stdout+q.stderr);result['testExit']=q.returncode
        assert q.returncode==0,(q.stdout+q.stderr).decode(errors='replace')
        result.update(result='PASS_PORTABLE_STORE_ONLY',output=q.stdout.decode())
    except Exception as error:
        result.update(result='FAILED_PORTABLE_STORE_CHECK',error=str(error));raise
    finally:
        inputs=[*sources,runtime/'companion_pet_profile.h',runtime/'companion_pet_profile_store.h',runtime/'companion_pet_profile_wire.h',
                ROOT/'app/companion_pendant/storage/companion_crc32.h',Path(__file__)]
        result['sourceSha256']={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest()for x in inputs}
        (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps({k:v for k,v in result.items()if k!='sourceSha256'}))

if __name__=='__main__':main()
