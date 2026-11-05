"""Exercise the actual board I2C wrappers and TCA driver against bus faults.

This is a declared HAL/bus model, not physical latency or current evidence.
The old pinned-HAL BUSY wait and capture timeout are reproduced separately.
"""
from pathlib import Path
import argparse,json,os,re,subprocess,hashlib

HARNESS=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include "tca6408.h"
typedef struct { void *Instance; unsigned state, busy; } I2C_HandleTypeDef;
typedef struct {
    struct { bool running; } microphone;
    bool expander_input_valid;
    uint8_t expander_raw_inputs;
} comp_v11_hal_t;
static I2C_HandleTypeDef i2c_io;
static unsigned ipsr, calls, model_ms, last_timeout;
static bool fail_transfer;
static uint8_t regs[4];
#define HAL_I2C_STATE_READY 1u
#define I2C_FLAG_BUSY 1u
#define I2C_MEMADD_SIZE_8BIT 1u
#define SET 1u
#define HAL_OK 0
#define HAL_ERROR 1
#define __get_IPSR() (ipsr)
#define HAL_I2C_GetState(bus) ((bus)->state)
#define __HAL_I2C_GET_FLAG(bus, flag) ((void)(flag),(bus)->busy)
static int transact(I2C_HandleTypeDef *bus,uint16_t addr,uint16_t reg,
                    uint16_t kind,uint8_t *data,uint16_t count,uint32_t timeout,bool write)
{
    assert(addr==0x40u && reg<4u && kind==1u && count==1u && data);
    ++calls;last_timeout=timeout;
    if(bus->state!=HAL_I2C_STATE_READY)return HAL_ERROR;
    /* Match the pinned HAL's separate BUSY limit, not its caller timeout. */
    if(bus->busy){model_ms+=MODEL_HAL_BUSY_TIMEOUT+1u;return HAL_ERROR;}
    if(fail_transfer){model_ms+=timeout+1u;if(!write)*data=0xcc;return HAL_ERROR;}
    if(write)regs[reg]=*data;else *data=regs[reg];
    return HAL_OK;
}
static int HAL_I2C_Mem_Read(I2C_HandleTypeDef *b,uint16_t a,uint16_t r,uint16_t k,uint8_t*d,uint16_t n,uint32_t t)
{return transact(b,a,r,k,d,n,t,false);}
static int HAL_I2C_Mem_Write(I2C_HandleTypeDef *b,uint16_t a,uint16_t r,uint16_t k,uint8_t*d,uint16_t n,uint32_t t)
{return transact(b,a,r,k,d,n,t,true);}
#include "product_io_functions.inc"
static void reset(void){i2c_io=(I2C_HandleTypeDef){(void*)1,1u,0u};ipsr=calls=model_ms=last_timeout=0;fail_transfer=false;}
int main(void)
{
    comp_v11_hal_t b={0};uint8_t sample=0x33;reset();regs[0]=0xa5;
    assert(io_read(&b,0x20,0,&sample)&&sample==0xa5&&b.expander_input_valid&&b.expander_raw_inputs==0xa5);
    assert(last_timeout==10&&calls==1);
    reset();b.microphone.running=true;i2c_io.busy=1;
    assert(!io_read(&b,0x20,0,&sample)&&!b.expander_input_valid&&b.expander_raw_inputs==0xa5);
    assert(!io_write(&b,0x20,1,0x40));
#if EXPECT_OLD
    assert(calls==2&&model_ms==2*(MODEL_HAL_BUSY_TIMEOUT+1u));
    printf("REPRODUCED old held-BUSY read+write enters fixed HAL waits: model_ms=%u\n",model_ms);
    reset();fail_transfer=true;assert(!io_read(&b,0x20,0,&sample));
    assert(last_timeout==10&&model_ms==11);
    puts("REPRODUCED old recording transaction retains10ms caller budget (model11ms)");
#else
    assert(calls==0&&model_ms==0);
    reset();i2c_io.state=2;assert(!io_read(&b,0x20,0,&sample));assert(!io_write(&b,0x20,1,0x40));assert(calls==0);
    reset();i2c_io.Instance=NULL;assert(!io_read(&b,0x20,0,&sample));assert(!io_write(&b,0x20,1,0x40));assert(calls==0);
    reset();ipsr=4;assert(!io_read(&b,0x20,0,&sample));assert(!io_write(&b,0x20,1,0x40));assert(calls==0);
    reset();fail_transfer=true;assert(!io_read(&b,0x20,0,&sample));
    assert(last_timeout==1&&model_ms==2&&!b.expander_input_valid&&b.expander_raw_inputs==0xa5);
    assert(!io_write(&b,0x20,1,0x40));assert(last_timeout==1&&model_ms==4);
    reset();b.microphone.running=false;fail_transfer=true;assert(!io_read(&b,0x20,0,&sample));assert(last_timeout==10);
    reset();b.microphone.running=true;
    comp_tca6408_t io;assert(comp_tca6408_init(&io,io_read,io_write,&b,0x20,0x2d,0x50));
    io.admit_write=io_admit_write;
    regs[0]=0xff;assert(comp_tca6408_sample(&io,&sample)&&sample==0x2d);
    i2c_io.busy=1;unsigned count=calls;sample=0x87;
    assert(!comp_tca6408_sample(&io,&sample)&&sample==0x87&&io.ready&&io.errors==1&&calls==count);
    i2c_io.busy=0;regs[0]=0x08;
    assert(comp_tca6408_sample(&io,&sample)&&sample==0x08&&b.expander_input_valid&&io.errors==1);
    fail_transfer=true;assert(!comp_tca6408_update(&io,0x40,0)&&!io.ready&&io.outputs==0x50);
    count=calls;fail_transfer=false;
    assert(!comp_tca6408_update(&io,0x80,0x80)&&calls==count&&regs[1]==0x50);
    puts("PASS: no HAL transaction for busy/unready/ISR; capture1ms vs idle10ms budget; invalid input preserves raw history; fresh recovered input accepted; uncertain output stays closed");
#endif
    return 0;
}
'''

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--baseline',required=True);ap.add_argument('--sdk',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
    root=Path(__file__).resolve().parents[1];base=Path(a.baseline).resolve();out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
    hal=Path(a.sdk).resolve()/'Drivers/STM32WBAxx_HAL_Driver/Src/stm32wbaxx_hal_i2c.c'
    ht=hal.read_text();busy=int(re.search(r'#define I2C_TIMEOUT_BUSY\s+\((\d+)U\)',ht)[1]);assert busy==25
    assert ht.count('I2C_FLAG_BUSY, SET, I2C_TIMEOUT_BUSY, tickstart')>=2
    vc=Path(r'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat');assert vc.is_file()
    rel=Path('platform/stm32wba55_companion_v11/board_hal.c'); rows=[]
    for label,source,old in [('baseline',base,1),('candidate',root,0)]:
        d=out/label;d.mkdir();text=(source/rel).read_text();first='static bool io_read('if old else'static bool io_bus_idle('
        funcs=text[text.index(first):text.index('static bool touch_bus_idle(')]
        (d/'product_io_functions.inc').write_text(funcs)
        (d/'test.c').write_text(HARNESS)
        drv=source/'app/companion_pendant/board'
        cmd=['cl.exe','/nologo','/std:c11','/W4','/WX',f'/DEXPECT_OLD={old}',f'/DMODEL_HAL_BUSY_TIMEOUT={busy}',f'/I{drv}',str(d/'test.c'),str(drv/'tca6408.c'),f'/Fe:{d/"test.exe"}']
        script=d/'build.cmd';script.write_text('@echo off\ncall "'+str(vc)+'" >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n')
        build=subprocess.run([os.environ.get('COMSPEC','cmd.exe'),'/d','/c',str(script)],cwd=d,capture_output=True)
        (d/'build.log').write_bytes(build.stdout+build.stderr);assert build.returncode==0,(build.stdout+build.stderr).decode(errors='replace')
        run=subprocess.run([str(d/'test.exe')],cwd=d,capture_output=True);(d/'run.log').write_bytes(run.stdout+run.stderr)
        assert run.returncode==0,(run.stdout+run.stderr).decode(errors='replace')
        rows.append(dict(label=label,stdout=run.stdout.decode(),functionsSha256=hashlib.sha256(funcs.encode()).hexdigest()))
    result=dict(result='PASS_AFFECTED_IO_FAULT_MODELS_ONLY',runs=rows,hardware='NOT_RUN',speedExperiments=0,sourceSha256=hashlib.sha256((root/rel).read_bytes()).hexdigest(),pinnedHalSha256=hashlib.sha256(hal.read_bytes()).hexdigest(),scope='Actual extracted board wrappers and production TCA driver; declared bus model. No physical fault latency or whole-product deadline qualification.')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
