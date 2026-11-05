"""Exercise actual control entry and original audio gates; no hardware claims."""
from pathlib import Path
import argparse,hashlib,json,subprocess
from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd
ROOT=Path(__file__).resolve().parents[1]
def function(text,name):
    start=text.index(name+'(');start=text.rfind('\n',0,start)+1
    end=text.index('\n}',text.index('{',start))+2
    body=text[start:end];assert body.count('{')==body.count('}')
    return body+'\n'
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);base=ROOT/'platform/stm32wba55_companion_v11/ble'
    app=base/'app_ble.c';product=base/'ble_product.c';fixture=base/'tests/test_ble_peer_indication_recording.c'
    text=product.read_text();gates=function(app.read_text(),'APP_BLE_HostNvmStore')+function(app.read_text(),'comp_v11_ble_nvm_control_blocked')+function(text,'stack_writes_allowed')+function(text,'advertising_commands_allowed')
    (out/'production_gates.inc').write_text(gates)
    body=function(app.read_text(),'comp_v11_ble_advertise_poll');prefix=body.split('    /* Bounded retry: stack busy never causes a tight ACI loop. */')[0]
    assert 'aci_gatt_confirm_indication' in prefix
    (out/'production_control_prefix.inc').write_text(prefix+'    ++advertising_body_calls; /* unrelated advertising body stub */\n}\n')
    exe=out/'recording-indication.exe';cmd=['cl.exe','/nologo','/TC','/std:c11','/Zc:preprocessor','/O2','/W4','/WX',f'/I{out}',str(fixture),f'/Fe:{exe}']
    script=out/'build.cmd';script.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n')
    run(['cmd.exe','/d','/c',str(script)],out,out/'build.log');result=run([str(exe)],out,out/'build.log')
    (out/'result.json').write_text(json.dumps(dict(result=result,physicalRecordingQualified=False,scope='Exact production recording/maintenance gates and advertise_poll entry through indication confirmation; unrelated advertising body and hardware APIs stubbed',sourceSha256={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [app,product,fixture,Path(__file__)]}),indent=2)+'\n')
    print(result,end='')
if __name__=='__main__':main()
