"""Active-fault recovery using the real board sample helper and TCA driver.

Declared port model: no physical I2C injection or timing qualification.
"""
from pathlib import Path
import argparse, hashlib, json, os, re, subprocess

HARNESS=r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "tca6408.h"
enum {COMP_V11_FAULT_IO=2u,COMP_V11_FAULT_IMU=4u,COMP_V11_FAULT_TOUCH=32u};
typedef struct {comp_tca6408_t io;uint8_t expander_inputs;uint32_t faults;} comp_v11_hal_t;
static uint8_t regs[4];
static unsigned reads,writes;
static bool read_fails,write_fails,lost_ack,admitted;
static bool rd(void*c,uint8_t address,uint8_t reg,uint8_t*value) {
    (void)c;assert(address==0x20u&&reg<4u);++reads;
    if(read_fails)return false;
    *value=regs[reg];return true;
}
static bool wr(void*c,uint8_t address,uint8_t reg,uint8_t value) {
    (void)c;assert(address==0x20u&&reg<4u);++writes;
    if(!write_fails||lost_ack)regs[reg]=value;
    return !write_fails;
}
static bool admit(void*c) {(void)c;return admitted;}
static void initialize(comp_v11_hal_t*b) {
    memset(b,0,sizeof(*b));memset(regs,0,sizeof(regs));
    read_fails=write_fails=lost_ack=false;admitted=true;reads=writes=0;
    assert(comp_tca6408_init(&b->io,rd,wr,NULL,0x20u,0x2du,0x50u));
    b->io.admit_write=admit;b->faults=COMP_V11_FAULT_TOUCH|COMP_V11_FAULT_IMU;
    b->expander_inputs=0x20u;regs[0]=0x0du;
}
#include "actual_sample.inc"
int main(void) {
    comp_v11_hal_t b;initialize(&b);
    unsigned w=writes,r=reads;
    read_fails=true;
    assert(!io_sample_inputs(&b)&&b.io.ready&&b.io.errors==1u);
    assert(b.expander_inputs==0x20u&&b.io.outputs==0x50u&&writes==w&&reads==r+1u);
    assert(b.faults==(COMP_V11_FAULT_IO|COMP_V11_FAULT_IMU|COMP_V11_FAULT_TOUCH));
    read_fails=false;
    assert(io_sample_inputs(&b)&&b.expander_inputs==0x0du&&b.io.errors==1u);
#if EXPECT_BASELINE
    assert(b.faults&COMP_V11_FAULT_IO);
    puts("REPRODUCED743: successful fresh input with trusted outputs leaves active IO fault permanently set");
#else
    assert(b.faults==(COMP_V11_FAULT_IMU|COMP_V11_FAULT_TOUCH));
    assert(writes==w&&b.io.outputs==0x50u&&regs[1]==0x50u);
    /* Repeated real recovery keeps all historical error evidence. */
    for(unsigned n=0;n<3u;++n) {
        read_fails=true;assert(!io_sample_inputs(&b));
        assert(b.faults&COMP_V11_FAULT_IO);
        read_fails=false;assert(io_sample_inputs(&b));
        assert(!(b.faults&COMP_V11_FAULT_IO)&&b.io.errors==n+2u);
    }
    /* A rejected preflight sends nothing. It does not poison the shadow. */
    initialize(&b);admitted=false;w=writes;
    assert(!comp_tca6408_update(&b.io,0x40u,0u)&&b.io.ready&&writes==w);
    b.faults|=COMP_V11_FAULT_IO;assert(io_sample_inputs(&b));
    assert(!(b.faults&COMP_V11_FAULT_IO)&&b.io.errors==1u&&writes==w);
    /* An actual uncertain write cannot be healed by an input read. */
    for(unsigned uncertain=0;uncertain<2u;++uncertain) {
        initialize(&b);write_fails=true;lost_ack=uncertain!=0u;
        assert(!comp_tca6408_update(&b.io,0x40u,0u)&&!b.io.ready);
        assert(regs[1]==(lost_ack?0x10u:0x50u));
        write_fails=false;r=reads;w=writes;
        assert(!io_sample_inputs(&b)&&(b.faults&COMP_V11_FAULT_IO));
        assert(reads==r&&writes==w&&!b.io.ready&&b.io.outputs==0x50u&&b.io.errors==1u);
    }
    /* Failed init remains closed. A healthy input wire alone is no proof. */
    initialize(&b);read_fails=true;
    assert(!comp_tca6408_init(&b.io,rd,wr,NULL,0x20u,0x2du,0x50u));
    read_fails=false;r=reads;w=writes;
    assert(!io_sample_inputs(&b)&&(b.faults&COMP_V11_FAULT_IO)&&reads==r&&writes==w);
    puts("PASS: fresh input clears only active IO fault with trusted shadow; errors/other faults persist; uncertain write/init stay closed; no reset or replay");
#endif
    return 0;
}
'''

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--baseline',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    root=Path(__file__).resolve().parents[1];out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    rel=Path('platform/stm32wba55_companion_v11/board_hal.c')
    vc=Path(r'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat')
    rows=[]
    for name,src,old in [('actual743',a.baseline.resolve(),1),('candidate744',root,0)]:
        d=out/name;d.mkdir();text=(src/rel).read_text()
        if old:
            sample=re.search(r'io_sample_ok = comp_tca6408_sample[^;]+;',text).group(0)
            fault=re.search(r'if \(!io_sample_ok\) \{ b->faults \|= COMP_V11_FAULT_IO; \}',text).group(0)
            helper='static bool io_sample_inputs(comp_v11_hal_t*b) {bool io_sample_ok;'+sample+fault+'return io_sample_ok;}\n'
        else:
            assert text.count('io_sample_ok = io_sample_inputs(b);')==1
            helper=text[text.index('static bool io_sample_inputs('):text.index('static bool touch_bus_idle(')]
        (d/'actual_sample.inc').write_text(helper);(d/'test.c').write_text(HARNESS)
        drv=src/'app/companion_pendant/board'
        cmd=['cl.exe','/nologo','/std:c11','/W4','/WX',f'/DEXPECT_BASELINE={old}',f'/I{drv}',str(d/'test.c'),str(drv/'tca6408.c'),f'/Fe:{d/"test.exe"}']
        script=d/'build.cmd';script.write_text('@echo off\ncall "'+str(vc)+'" >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n')
        build=subprocess.run([os.environ.get('COMSPEC','cmd.exe'),'/d','/c',str(script)],cwd=d,capture_output=True)
        (d/'build.log').write_bytes(build.stdout+build.stderr);assert build.returncode==0,(build.stdout+build.stderr).decode(errors='replace')
        run=subprocess.run([str(d/'test.exe')],cwd=d,capture_output=True);(d/'run.log').write_bytes(run.stdout+run.stderr)
        assert run.returncode==0,(run.stdout+run.stderr).decode(errors='replace')
        rows.append(dict(label=name,stdout=run.stdout.decode(),helperSha256=hashlib.sha256(helper.encode()).hexdigest()))
    result=dict(result='PASS_ACTIVE_IO_HEALTH_RECOVERY_MODEL',runs=rows,physicalFaultInjection='NOT_RUN',deviceOperations=0,speedExperiments=0)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
