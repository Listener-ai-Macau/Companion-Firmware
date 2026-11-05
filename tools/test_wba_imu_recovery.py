"""Replay transient IMU faults through real driver + extracted board functions.

Declared register/bus model only. No serial, BLE, reset or hardware access.
"""
from pathlib import Path
import argparse, hashlib, json, os, subprocess

def function(text, signature):
    begin=text.index(signature);brace=text.index('{',begin);depth=1;i=brace+1
    while depth:
        depth+=(text[i]=='{')-(text[i]=='}');i+=1
    return text[begin:i]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--baseline',required=True)
    ap.add_argument('--output',required=True);a=ap.parse_args()
    root=Path(__file__).resolve().parents[1];base=Path(a.baseline).resolve();out=Path(a.output).resolve()
    out.mkdir(parents=True,exist_ok=False)
    imu=Path('app/companion_pendant/imu');power=base/'app/companion_pendant/power'
    board=Path('platform/stm32wba55_companion_v11/board_hal.c')
    vc=Path(r'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat')
    assert vc.is_file()
    original=(base/board).read_text();candidate=(root/board).read_text()
    harness=(root/imu/'tests/test_lsm6dso_recovery.c').read_text()
    rows=[]
    for label,source in [('baseline',base),('candidate',root)]:
        d=out/label;d.mkdir()
        code=original if label=='baseline' else candidate
        functions=function(code,'bool comp_v11_hal_set_idle_peripherals(')
        if label=='candidate': functions+='\n'+function(code,'static void imu_poll_with_recovery(')
        (d/'product_imu_functions.inc').write_text(functions+'\n')
        if label=='baseline':
            test=harness[:harness.index('static void recover_sample(')]+'''
int main(void) {
    comp_v11_hal_t b={0};bus_t bus;comp_imu_sample_t sample;
    ready(&b.imu,&bus);bus.fail_at=1;
    assert(comp_lsm6dso_poll(&b.imu,10,&sample)==COMP_IMU_IO_ERROR);
    bus.fail_at=0;unsigned ops=bus.ops;
    for(unsigned i=0;i<100;i++) assert(comp_lsm6dso_poll(&b.imu,100+i*1000,&sample)==COMP_IMU_NO_SAMPLE);
    assert(b.imu.state==COMP_IMU_FAULT&&bus.ops==ops);
    b.idle_peripherals=true;b.power.button_wake_ready=true;
    assert(comp_v11_hal_set_idle_peripherals(&b,true));
    puts("REPRODUCED: transient bus fault remains permanent, stale idle returns success with IMU still FAULT");
    return 0;
}
'''
        else: test=harness
        (d/'test.c').write_text(test)
        cmd=['cl.exe','/nologo','/std:c11','/W4','/WX',f'/I{source/imu}',f'/I{base/imu}',f'/I{power}',
             str(d/'test.c'),str(source/imu/'lsm6dso.c'),str(base/imu/'motion_events.c'),
             str(power/'power_policy.c'),f'/Fe:{d/"test.exe"}']
        script=d/'build.cmd';script.write_text('@echo off\ncall "'+str(vc)+'" >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n')
        result=subprocess.run([os.environ.get('COMSPEC','cmd.exe'),'/d','/c',str(script)],cwd=d,capture_output=True)
        (d/'build.log').write_bytes(result.stdout+result.stderr)
        assert result.returncode==0,result.stdout.decode(errors='replace')+result.stderr.decode(errors='replace')
        result=subprocess.run([str(d/'test.exe')],cwd=d,capture_output=True)
        (d/'run.log').write_bytes(result.stdout+result.stderr)
        assert result.returncode==0,result.stdout.decode(errors='replace')+result.stderr.decode(errors='replace')
        text=result.stdout.decode(errors='replace');print(label+':\n'+text)
        rows.append({'label':label,'result':text})
    paths=[p for p in root.rglob('*') if p.is_file() and p.suffix in ('.c','.h','.py')]
    receipt={'result':'PASS_SOFTWARE_ONLY','runs':rows,'hardware':'NOT_RUN','installed':False,
             'source_sha256':{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
    (out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')

if __name__=='__main__': main()
