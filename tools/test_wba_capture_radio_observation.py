from pathlib import Path
import sys,json,subprocess,hashlib,argparse
p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);a=p.parse_args();S=a.source_root.resolve();A=S/'platform/stm32wba55_companion_v11';sys.path.insert(0,str(S/'tools'))
from verify_wba_spi_nor_adapter import find_vsdevcmd
out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);src=(A/'ble/ble_product.c').read_text();block=src.split('/* CAPTURE_RADIO_MODEL_BEGIN */',1)[1].split('/* CAPTURE_RADIO_MODEL_END */',1)[0]
pre=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#define COMPANION_WBA_CPU_RESIDENCE_PROFILE 1
static struct {struct {bool running;} microphone;} board;
static struct {void *unused;struct {struct {uint32_t token;} pipeline;} recording;struct {struct {bool running;}microphone;} *board;} model;
static struct {struct {struct {uint32_t token;}pipeline;}recording;struct {struct {bool running;}microphone;}*board;} target;
#define product (&target)
static uint32_t now;
static uint32_t HAL_GetTick(void){return now;}
#define CHECK(x) do{if(!(x)){fprintf(stderr,"FAIL line=%d %s\n",__LINE__,#x);return 1;}}while(0)
'''
# Use identical compatible named board type rather than anonymous fake pointer casts.
pre=pre.replace('static struct {struct {bool running;} microphone;} board;','typedef struct {struct {bool running;}microphone;} board_t;\nstatic board_t board;').replace('static struct {void *unused;struct {struct {uint32_t token;} pipeline;} recording;struct {struct {bool running;}microphone;} *board;} model;\n','').replace('struct {struct {bool running;}microphone;}*board;','board_t*board;')
post=r'''
int main(void){target.board=&board;target.recording.pipeline.token=3u;now=100u;
 comp_v11_ble_observe_capture_radio(false,1u,19u);CHECK(capture_radio.token==0u);
 board.microphone.running=true;target.recording.pipeline.token=0u;comp_v11_ble_observe_capture_radio(false,1u,19u);CHECK(capture_radio.token==0u);
 target.recording.pipeline.token=3u;now=1234u;comp_v11_ble_observe_capture_radio(false,7u,19u);CHECK(capture_radio.token==3u && capture_radio.down==1u && capture_radio.up==0u && capture_radio.down_ms==1234u && capture_radio.reason==19u);
 now=2234u;comp_v11_ble_observe_capture_radio(true,8u,0u);CHECK(capture_radio.up==1u && capture_radio.up_ms==2234u && capture_radio.handle==8u && capture_radio.reason==19u);
 board.microphone.running=false;now=3234u;comp_v11_ble_observe_capture_radio(false,8u,22u);CHECK(capture_radio.down==1u && capture_radio.down_ms==1234u);
 board.microphone.running=true;target.recording.pipeline.token=4u;comp_v11_ble_observe_capture_radio(false,9u,22u);CHECK(capture_radio.token==4u && capture_radio.down==1u && capture_radio.up==0u && capture_radio.up_ms==0u);
 capture_radio.down=UINT16_MAX;comp_v11_ble_observe_capture_radio(false,9u,22u);CHECK(capture_radio.down==UINT16_MAX);
 CHECK(board.microphone.running && target.recording.pipeline.token==4u);
 printf("PASS_CAPTURE_RADIO_OBSERVATION exact_source active-token-only/no-radio-command/saturation/pause-excluded size=%zu; actual HCI still NOT_RUN\n",sizeof(capture_radio));return 0;}
'''
p=out/'test.c';p.write_text(pre+block+post,encoding='utf-8');args=['cl.exe','/nologo','/TC','/std:c11','/O2','/W4','/WX','/wd4127','/utf-8',str(p),'/Fe:'+str(out/'test.exe')];cmd=out/'compile.cmd';cmd.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n');p=subprocess.run(['cmd.exe','/d','/c',str(cmd)],cwd=out,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);(out/'build.log').write_text(p.stdout+p.stderr);assert p.returncode==0,(p.stdout+p.stderr)[-3000:]
p=subprocess.run([str(out/'test.exe')],cwd=out,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);(out/'result.log').write_text(p.stdout+p.stderr);assert p.returncode==0,(p.stdout+p.stderr)[-3000:]
r={'result':'PASS_EXACT_C_OBSERVATION_MODEL','output':p.stdout,'sourceSha256':hashlib.sha256((A/'ble/ble_product.c').read_bytes()).hexdigest(),'actualRadio':'NOT_RUN'};(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
