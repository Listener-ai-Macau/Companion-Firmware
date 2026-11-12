"""Exercise production quiet-pointer dispatch, including urgent wake/producer work."""
from pathlib import Path
import argparse,subprocess,json,hashlib
from verify_wba_spi_nor_adapter import find_vsdevcmd
parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True);a=parser.parse_args()
root=Path(__file__).resolve().parents[1];out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
src=(root/"platform/stm32wba55_companion_v11/product_app.c").read_text()
begin=src.index("static bool product_service_due(");end=src.index("void comp_v11_product_app_poll(",begin)
helper=src[begin:end];poll=src[end:]
start=poll.index("    uint32_t now=HAL_GetTick();");finish=poll.index("    app->pointer_service_due_ms=now+5u;")+len("    app->pointer_service_due_ms=now+5u;")
dispatch=poll[start:finish]
prefix=r"""#include <stdint.h>
#include <stdbool.h>
#include <assert.h>
#include <stdio.h>
#define COMPANION_WBA_BLE_LINKED 1
#define COMP_INPUT_POINTER 3u
typedef struct { bool busy; } pipeline_t;
typedef struct { struct {bool running;} microphone;bool playback_active,speaker;uint32_t imu_poll_ms;struct{uint32_t pending,key_pending;}wake_events;} comp_v11_hal_t;
typedef struct {comp_v11_hal_t *board;struct{uint8_t mode;}input;uint32_t pointer_service_due_ms;struct{bool writing;}pet_profile;struct{bool audio,prepare_pending,start_pending,command_pending,stop_pending,capture_active;}runtime;struct{bool ready;pipeline_t pipeline;}recording;} comp_v11_product_app_t;
static bool ota,ble,update,nvm,start_from_ble;static uint32_t tick;static unsigned full,ble_only;
static comp_v11_product_app_t *callback_app;
static uint32_t HAL_GetTick(void){return tick;}
static bool comp_wba_recording_pipeline_storage_busy(const pipeline_t*p){return p->busy;}
static bool comp_v11_ota_gatt_foreground_pending(void){return ota;}
static bool comp_v11_ble_foreground_pending(void){return ble;}
static void comp_v11_ble_poll(void){++ble_only;ble=false;if(start_from_ble)callback_app->runtime.start_pending=true;}
static bool comp_v11_update_product_busy(void){return update;}
static bool comp_v11_ble_nvm_busy(void){return nvm;}
static bool comp_speaker_active(const bool *active){return *active;}
static bool comp_audio_feedback_busy(const bool *active){return *active;}
"""
tests=r"""
int main(void){
 comp_v11_hal_t board={0};comp_v11_product_app_t app={0};app.board=&board;app.input.mode=3;app.recording.ready=true;
 for(tick=0;tick<100;++tick)dispatch(&app);
#if COMPANION_WBA_SCREEN_ENABLED
 assert(full==100);
#else
 assert(full==20);
 app.pointer_service_due_ms=200;tick=101;board.imu_poll_ms=tick;
 board.wake_events.pending=1;assert(product_service_due(&app,tick));board.wake_events.pending=0;
 board.wake_events.key_pending=1;assert(product_service_due(&app,tick));board.wake_events.key_pending=0;
 board.microphone.running=true;for(unsigned i=0;i<20;++i)assert(product_service_due(&app,tick));board.microphone.running=false;
 board.playback_active=true;assert(product_service_due(&app,tick));board.playback_active=false;
 bool *urgent[]={&app.runtime.prepare_pending,&app.runtime.start_pending,&app.runtime.command_pending,&app.runtime.stop_pending,&app.runtime.capture_active,&app.runtime.audio,&board.speaker,&app.recording.pipeline.busy,&app.pet_profile.writing,&ota,&update,&nvm};
 for(unsigned i=0;i<sizeof(urgent)/sizeof(urgent[0]);++i){*urgent[i]=true;assert(product_service_due(&app,tick));*urgent[i]=false;}
 app.recording.ready=false;assert(product_service_due(&app,tick));app.recording.ready=true;
 assert(!product_service_due(&app,tick));
 callback_app=&app;unsigned previous_full=full;
 ble=true;dispatch(&app);assert(ble_only==1u&&full==previous_full);
 ble=true;start_from_ble=true;dispatch(&app);assert(ble_only==2u&&full==previous_full+1u);
 app.runtime.start_pending=false;start_from_ble=false;app.pointer_service_due_ms=200;
 for(unsigned mode=0;mode<4u;++mode){app.input.mode=(uint8_t)mode;assert(!product_service_due(&app,tick));}
 app.input.mode=3;
 app.pointer_service_due_ms=200;board.imu_poll_ms=100;assert(!product_service_due(&app,109));assert(product_service_due(&app,110));
 app.pointer_service_due_ms=3;board.imu_poll_ms=UINT32_MAX-1u;assert(!product_service_due(&app,UINT32_MAX-1u));assert(product_service_due(&app,3));
#endif
 puts("PASS production quiet-pointer cadence: quiet5ms without empty BLE polls; physical wake, capture/playback, control, boot, storage/update/NVM/queued-BLE immediate; independent10ms sensor, recorder/display cadence and wrap retained. Software-only.");
}
"""
model=out/"model.c";model.write_text(prefix+helper+"static void dispatch(comp_v11_product_app_t *app){\n"+dispatch+"\nif(now-app->board->imu_poll_ms>=10u)app->board->imu_poll_ms=now;\n++full; }\n"+tests)
results={}
for screen in [0,1]:
 args=["cl.exe","/nologo","/TC","/std:c11","/O2","/W4","/WX","/wd4127","/wd4100","/wd4505","/utf-8","/DCOMPANION_WBA_SCREEN_ENABLED="+str(screen),str(model),"/Fe:"+str(out/("test"+str(screen)+".exe"))]
 batch=out/("compile"+str(screen)+".cmd");batch.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
 for stage,cmd in [("compile",["cmd","/d","/c",str(batch)]),("run",[str(out/("test"+str(screen)+".exe"))])]:
  r=subprocess.run(cmd,cwd=out,capture_output=True,text=True,encoding="utf-8",errors="replace");(out/(str(screen)+"-"+stage+".log")).write_text(r.stdout+r.stderr);print(screen,stage,r.returncode,r.stdout+r.stderr);r.check_returncode()
 results[str(screen)]="PASS"
(out/"result.json").write_text(json.dumps({"softwareOnly":True,"results":results,"productionHelperSha256":hashlib.sha256(helper.encode()).hexdigest(),"productionDispatchSha256":hashlib.sha256(dispatch.encode()).hexdigest()},indent=2)+"\n")
