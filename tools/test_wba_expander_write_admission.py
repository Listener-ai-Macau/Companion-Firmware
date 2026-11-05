"""Reproduce a not-sent output failure in actual WBA wrappers/TCA driver.

Declared HAL fault model only; no claim about physical I2C fault injection.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json, os, subprocess

MAIN = r'''
static void initialize(comp_tca6408_t *io, comp_v11_hal_t *board) {
    reset();
    assert(comp_tca6408_init(io,io_read,io_write,board,0x20,0x2d,0x50));
#if !EXPECT_BASELINE
    io->admit_write=io_admit_write;
#endif
}
int main(void) {
    comp_v11_hal_t b={0};comp_tca6408_t io;
    b.microphone.running=true;
    initialize(&io,&b);
    unsigned before=calls;i2c_io.busy=1;
    assert(!comp_tca6408_update(&io,0x40,0));
    assert(calls==before && io.outputs==0x50 && regs[1]==0x50 && io.errors==1);
#if EXPECT_BASELINE
    assert(!io.ready);i2c_io.busy=0;
    assert(!comp_tca6408_update(&io,0x80,0x80) && calls==before);
    puts("REPRODUCED740: zero HAL calls, but a not-sent write permanently locks every output owner");
#else
    assert(io.ready);i2c_io.busy=0;
    /* Recovery is a new explicit owner request, never a hidden retry. */
    assert(calls==before);
    assert(comp_tca6408_update(&io,0x80,0x80));
    assert(calls==before+1 && io.outputs==0xd0 && regs[1]==0xd0 && io.errors==1);
    assert(comp_tca6408_update(&io,0x40,0));
    assert(io.outputs==0x90 && regs[1]==0x90);
    for(unsigned fault=0;fault<4;fault++) {
        initialize(&io,&b);before=calls;
        if(fault==0)i2c_io.busy=1;
        if(fault==1)i2c_io.state=2;
        if(fault==2)i2c_io.Instance=NULL;
        if(fault==3)ipsr=4;
        assert(!comp_tca6408_update(&io,0x40,0));
        assert(io.ready && io.outputs==0x50 && regs[1]==0x50 && io.errors==1 && calls==before);
        /* A known no-op is allowed; an input pin cannot become an output. */
        assert(comp_tca6408_update(&io,0x40,0x40) && calls==before);
        assert(!comp_tca6408_update(&io,0x01,0) && calls==before && io.errors==1);
    }
    initialize(&io,&b);before=calls;fail_transfer=true;
    assert(!comp_tca6408_update(&io,0x40,0) && !io.ready && calls==before+1);
    assert(io.outputs==0x50 && regs[1]==0x50 && io.errors==1);
    fail_transfer=false;before=calls;
    assert(!comp_tca6408_update(&io,0x80,0x80) && calls==before);
    /* Lost ACK may change the real latch: never adopt the old shadow. */
    initialize(&io,&b);before=calls;fail_transfer=true;fail_after_write=true;
    assert(!comp_tca6408_update(&io,0x40,0) && !io.ready && calls==before+1);
    assert(io.outputs==0x50 && regs[1]==0x10);
    fail_transfer=false;before=calls;
    assert(!comp_tca6408_update(&io,0x80,0x80) && calls==before && regs[1]==0x10);
    /* A race after preflight remains conservative, even if wrapper rejects. */
    initialize(&io,&b);io.write=reject_write;before=calls;
    assert(!comp_tca6408_update(&io,0x40,0) && !io.ready && calls==before);
    /* Generic callers without a preflight retain existing semantics. */
    initialize(&io,&b);io.admit_write=NULL;i2c_io.busy=1;before=calls;
    assert(!comp_tca6408_update(&io,0x40,0) && !io.ready && calls==before);
    /* Failed initialization remains unready; installing hook cannot heal it. */
    reset();fail_transfer=true;
    assert(!comp_tca6408_init(&io,io_read,io_write,&b,0x20,0x2d,0x50));
    io.admit_write=io_admit_write;fail_transfer=false;before=calls;
    assert(!comp_tca6408_update(&io,0x80,0x80) && !io.ready && calls==before);
    puts("PASS: rejected-before-write preserves confirmed outputs; next explicit request works; busy/state/instance/ISR rejected; entered failure/lost ACK/race/init failure stay closed; no automatic retry");
#endif
    return 0;
}
'''

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--baseline',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
    root=Path(__file__).resolve().parents[1];base=Path(a.baseline).resolve();out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
    spec=importlib.util.spec_from_file_location('capture_guard',root/'tools/test_wba_expander_capture_guard.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    prefix=module.HARNESS.split('int main(void)')[0]
    prefix=prefix.replace('static bool fail_transfer;', 'static bool fail_transfer, fail_after_write;')
    prefix=prefix.replace('if(fail_transfer){model_ms', 'if(fail_transfer){if(write && fail_after_write)regs[reg]=*data;model_ms')
    prefix=prefix.replace('fail_transfer=false;', 'fail_transfer=fail_after_write=false;')
    prefix+='''\n#if !EXPECT_BASELINE
static bool reject_write(void *ctx,uint8_t a,uint8_t r,uint8_t v) {
    (void)ctx;(void)a;(void)r;(void)v;return false;
}
#endif
'''
    vc=Path(r'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat')
    rows=[];rel=Path('platform/stm32wba55_companion_v11/board_hal.c')
    for label,source,old in [('actual740',base,1),('candidate741',root,0)]:
        d=out/label;d.mkdir();text=(source/rel).read_text()
        if not old:
            assert ''.join(text.split()).count('b->io.admit_write=io_admit_write;')==1
        funcs=text[text.index('static bool io_bus_idle('):text.index('static bool touch_bus_idle(')]
        (d/'product_io_functions.inc').write_text(funcs);(d/'test.c').write_text(prefix+MAIN)
        drv=source/'app/companion_pendant/board'
        cmd=['cl.exe','/nologo','/std:c11','/W4','/WX',f'/DEXPECT_BASELINE={old}','/DMODEL_HAL_BUSY_TIMEOUT=25',f'/I{drv}',str(d/'test.c'),str(drv/'tca6408.c'),f'/Fe:{d/"test.exe"}']
        script=d/'build.cmd';script.write_text('@echo off\ncall "'+str(vc)+'" >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n')
        build=subprocess.run([os.environ.get('COMSPEC','cmd.exe'),'/d','/c',str(script)],cwd=d,capture_output=True)
        (d/'build.log').write_bytes(build.stdout+build.stderr);assert build.returncode==0,(build.stdout+build.stderr).decode(errors='replace')
        run=subprocess.run([str(d/'test.exe')],cwd=d,capture_output=True);(d/'run.log').write_bytes(run.stdout+run.stderr)
        assert run.returncode==0,(run.stdout+run.stderr).decode(errors='replace')
        rows.append(dict(label=label,stdout=run.stdout.decode(),functionsSha256=hashlib.sha256(funcs.encode()).hexdigest()))
    result=dict(result='PASS_WRITE_ADMISSION_FAULT_MODEL',runs=rows,hardware='NOT_RUN',speedExperiments=0,
        scope='Actual board wrappers and production driver; no physical fault injection qualification.')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
