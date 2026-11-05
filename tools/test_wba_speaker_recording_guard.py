"""Run the production late-recording guard with a prepared writer and speaker fault."""
from pathlib import Path
import subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(r"E:/CodexData/Companion/speaker-shutdown-fault-20261030/recording-guard")

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    product=(ROOT/"platform/stm32wba55_companion_v11/product_app.c").read_text(encoding="utf-8")
    body=product[product.index("static bool recording_control(void *c,bool start,uint32_t token)\n{"):product.index("bool comp_v11_product_recording_bookmark(")]
    fixture=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
enum {COMP_WBA_RECORDING_FAULT=7, DENZIC_AUDIO_RECORDING_STATE_CANCELED=9,
 COMP_RECORD_STOP_LOW_BATTERY=1, COMP_RECORD_STOP_DURATION_LIMIT=2, COMP_RECORD_STOP_SILENCE=3,
 COMP_CONT_STOP_LOW_BATTERY=1,COMP_CONT_STOP_LIMIT=2,COMP_CONT_STOP_SILENCE=3,COMP_CONT_STOP_USER=4,
 COMP_V11_FAULT_SPEAKER_SHUTDOWN=1024};
typedef int comp_cont_stop_t;
typedef struct {bool running;} mic_t;
typedef struct {uint32_t faults;mic_t microphone;} board_t;
typedef struct {bool engine_bound;} pipeline_t;
typedef struct {bool last_fault;pipeline_t pipeline;} recording_t;
typedef struct {uint32_t record_token;int record_stop_reason;} runtime_t;
typedef struct {board_t *board;bool recording_ready;recording_t recording;runtime_t runtime;} comp_v11_product_app_t;
static int starts,cancels;static bool allowed=true;
static bool recording_power_allowed(comp_v11_product_app_t *a){(void)a;return allowed;}
static bool comp_wba_recording_product_control(recording_t *r,bool start,uint32_t token)
{(void)r;assert(token==42u);if(start)starts++;else cancels++;return true;}
static int comp_wba_recording_product_state(recording_t *r){(void)r;return 0;}
static uint32_t HAL_GetTick(void){return 0u;}
static bool comp_runtime_recording_update(runtime_t *r,uint32_t t,int s,bool v,uint32_t tick)
{(void)r;(void)t;(void)s;(void)v;(void)tick;return true;}
static bool comp_wba_recording_product_stop_reason(recording_t *r,uint32_t t,comp_cont_stop_t s)
{(void)r;(void)t;(void)s;return true;}
'''
    check=r'''
int main(void){board_t b={0};comp_v11_product_app_t a={0};a.board=&b;a.recording_ready=true;
 b.faults=COMP_V11_FAULT_SPEAKER_SHUTDOWN;assert(!recording_control(&a,true,42u));
 assert(starts==0 && cancels==1);b.faults=0;
 assert(recording_control(&a,true,42u));assert(starts==1 && cancels==1);
 allowed=false;assert(!recording_control(&a,true,42u));assert(starts==1 && cancels==2);
 puts("PASS production late recording control: reject uncertain speaker, cancel reservation, preserve normal start");return 0;}
'''
    test=OUT/"test.c";test.write_text(fixture+body+check,encoding="utf-8")
    exe=OUT/"test.exe";cmd=OUT/"build.cmd"
    args=["cl.exe","/nologo","/std:c11","/W4","/WX",str(test),f"/Fe:{exe}"]
    cmd.write_text(f'@call "{find_vsdevcmd()}" -arch=amd64 -host_arch=amd64 >nul\n'
                   '@if errorlevel 1 exit /b %errorlevel%\n@'+subprocess.list2cmdline(args)+'\n')
    logs=[]
    for command in (["cmd.exe","/d","/c",str(cmd)],[str(exe)]):
        result=subprocess.run(command,cwd=OUT,text=True,capture_output=True);logs.append(result.stdout+result.stderr)
        (OUT/"test.log").write_text("\n".join(logs),encoding="utf-8")
        if result.returncode:raise RuntimeError(f'exit {result.returncode}: {OUT/"test.log"}')
    print(logs[-1].strip())

if __name__=="__main__":main()
