"""Byte equality with prior CIN1 plus unchanged-status/publish retry behavior."""
from pathlib import Path
import argparse,subprocess,json,re
from verify_wba_spi_nor_adapter import find_vsdevcmd
pa=argparse.ArgumentParser();pa.add_argument("--output",type=Path,required=True);a=pa.parse_args()
root=Path(__file__).resolve().parents[1];out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
platform=root/"platform/stm32wba55_companion_v11"
old=subprocess.check_output(["git","show","04a7f86:platform/stm32wba55_companion_v11/product_app.c"],cwd=root).decode()
old=old[old.index("void comp_v11_product_input_status("):old.index("size_t comp_v11_product_input_request(")].replace("comp_v11_product_input_status","old_status")
product_source=(platform/"product_app.c").read_text()
request=product_source[product_source.index("size_t comp_v11_product_input_request("):product_source.index("comp_segment_result_t comp_v11_product_recording_bookmark_result(")]
new=product_source[product_source.index("uint16_t comp_v11_product_input_signals("):product_source.index("size_t comp_v11_product_input_request(")]
new=new.replace("void comp_v11_product_input_status(","void actual_status(")
ble=(platform/"ble/ble_product.c").read_text();notify=ble[ble.index("static void input_notify("):ble.index("static void pointer_notify(")]
start=ble.index('    if(e->type==COMPANION_GATT_EVENT_WRITE&&e->char_id==COMPANION_GATT_CHAR_SETTINGS&&',ble.index('static void event('))
end=ble.index('    if(e->type==COMPANION_GATT_EVENT_WRITE&&e->char_id==COMPANION_GATT_CHAR_REPAIR_CONTROL)',start)
actual_event='static void actual_input_event(const companion_gatt_event_t *e){\n'+ble[start:end]+'}\n'

pre=r"""
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
#include "cpu_duty_target.h"
#include "companion_recording_wire.h"
#include "recorder_input.h"
#include "capture_feedback.h"
#define COMP_POWER_BLOCKER_UPDATE 1u
#define COMPANION_GATT_CHAR_SETTINGS 1u
typedef struct {bool owned;uint32_t record_token;} runtime_t;
typedef struct {comp_recorder_input_t input;comp_wba_button_t button;struct {struct {uint32_t blockers;}power;struct {bool running;}microphone;} *board;runtime_t runtime;uint64_t recording_session_id;struct{struct{bool engine_bound;}pipeline;struct{struct{uint32_t bookmark_sequence;}engine;}capture;struct{uint8_t uid[12];uint64_t epoch;}catalog;}recording;} comp_v11_product_app_t;
static comp_capture_feedback_t feedback;
static comp_capture_feedback_t comp_v11_product_capture_feedback(const comp_v11_product_app_t*a,bool updating){(void)a;(void)updating;return feedback;}
static bool comp_runtime_recording_owned(const runtime_t*r){return r->owned;}
static comp_v11_product_app_t *product;
static struct{bool subscribed[3];unsigned rejected_writes;}product_link;
static bool input_client,secured,publication_ok;
static uint8_t input_feedback,input_flags,published[64];
static unsigned builds,publishes;
static uint32_t pointer_event_sequence,pointer_event_sent_ms,now_ms;
static uint32_t HAL_GetTick(void){return now_ms;}
#define COMPANION_GATT_EVENT_WRITE 1u
typedef struct{unsigned type,char_id;const uint8_t *payload;size_t payload_len;} companion_gatt_event_t;
static bool link_ready=true;
static struct{bool active;}pointer_fusion;
static uint32_t pointer_sample_ms;
static float pointer_heading;
static bool comp_v11_update_product_busy(void){return false;}
static unsigned read_cache_updates;
static bool companion_gatt_stm32wb_set_read_value(unsigned id,const uint8_t *p,uint16_t n){(void)p;assert(id==1u&&n==64u);++read_cache_updates;return true;}

"""
post=r"""
static void comp_v11_product_input_status(const comp_v11_product_app_t*a,uint32_t req,uint8_t result,uint8_t p[64]){++builds;actual_status(a,req,result,p);}
static bool publish(void*c,unsigned characteristic,const uint8_t*p,size_t n){(void)c;assert(characteristic==1u&&n==64u);++publishes;memcpy(published,p,n);return publication_ok;}
"""
tests=r"""
int main(void){
 comp_v11_product_app_t app={0};typeof_unused:
 product=&app;
 /* Portable board model only, all packet/control builders below are real. */
 static struct{struct{uint32_t blockers;}power;struct{bool running;}microphone;}board;
 app.board=(void*)&board;
 for(unsigned i=0;i<1000u;++i){
  app.input.flags=(uint8_t)i;app.input.mode=(uint8_t)(i%4u);app.input.options=(uint8_t)(i%8u);
  app.input.sequence=0x12340000u+i;app.input.event_ms=10u*i;app.input.events=(uint16_t)(17u*i);
  board.microphone.running=(i&1u)!=0;board.power.blockers=i%3u;app.runtime.owned=(i&2u)!=0;app.runtime.record_token=i+8u;
  app.recording_session_id=0x1234567800000000ULL+i;app.recording.pipeline.engine_bound=(i&4u)!=0;
  app.recording.capture.engine.bookmark_sequence=i*7u;app.recording.catalog.epoch=0x3344556600000000ULL+i;
  for(unsigned j=0;j<12u;++j)app.recording.catalog.uid[j]=(uint8_t)(i+j);
  feedback.state=(uint8_t)(i%10u);feedback.flags=(uint8_t)(i%8u);
  uint8_t expected[64],actual[64];old_status(&app,i+1u,(uint8_t)(i%3u),expected);actual_status(&app,i+1u,(uint8_t)(i%3u),actual);
  assert(!memcmp(expected,actual,64u));
 }
 uint16_t signals=comp_v11_product_input_signals(&app);
 input_feedback=(uint8_t)(signals>>8);input_flags=(uint8_t)signals;app.input.events=0;
 input_client=secured=product_link.subscribed[1]=true;publication_ok=true;
 for(unsigned i=0;i<10000u;++i)input_notify();assert(!builds&&!publishes);
 app.input.flags^=COMP_INPUT_HELD;input_notify();assert(builds==1u&&publishes==1u&&input_flags==published[7]&&input_feedback==published[23]);
 app.input.events=COMP_INPUT_UNDO_LAST;publication_ok=false;input_notify();
 assert(app.input.events==COMP_INPUT_UNDO_LAST&&builds==2&&publishes==2);
 publication_ok=true;input_notify();assert(!app.input.events&&builds==3&&publishes==3);
 input_notify();assert(builds==3&&publishes==3);
 input_client=false;app.input.events=1;input_notify();assert(builds==3&&app.input.events==1);
 input_client=true;app.runtime.owned=false;app.input=(comp_recorder_input_t){0};
 assert(comp_input_mode(&app.input,COMP_INPUT_POINTER,COMP_INPUT_POINTER_V4,false,false));
 app.input.flags=COMP_INPUT_HELD;comp_input_note(&app.input,COMP_INPUT_DOWN,100u);
 app.input.flags=0u;comp_input_note(&app.input,COMP_INPUT_UP,180u);
 now_ms=200u;input_notify();assert(app.input.pointer_count==2u&&comp_rec_get32(published+12u)==1u);
 assert(comp_rec_get32(published+16u)==100u&&(published[7]&1u)&&published[21]==4u);
 unsigned count=publishes;now_ms=239u;input_notify();assert(publishes==count);
 now_ms=240u;input_notify();assert(publishes==count+1u&&comp_rec_get32(published+12u)==1u);
 uint8_t ack[36]={0},reply[64];memcpy(ack,"CIN1",4u);ack[4]=1u;ack[5]=2u;
 memcpy(ack+12u,app.recording.catalog.uid,12u);comp_rec_put64(ack+24u,app.recording.catalog.epoch);
 comp_rec_put32(ack+8u,1u);comp_rec_put32(ack+32u,comp_rec_crc(ack,32u));
 assert(comp_v11_product_input_request(&app,ack,36u,true,now_ms,reply)==64u&&reply[5]==0u);
 assert(app.input.mode==COMP_INPUT_POINTER&&app.input.pointer_count==1u);
 now_ms=241u;input_notify();assert(comp_rec_get32(published+12u)==2u&&!(published[7]&1u)&&published[21]==8u);
 assert(comp_rec_get32(published+16u)==180u); /* Exact edge, not retry time. */
 assert(comp_v11_product_input_request(&app,ack,36u,false,now_ms,reply)==64u&&app.input.pointer_count==1u);
 ack[12]^=1u;comp_rec_put32(ack+32u,comp_rec_crc(ack,32u));
 assert(!comp_v11_product_input_request(&app,ack,36u,false,now_ms,reply)); /* Wrong recorder cannot consume. */
 ack[12]^=1u;comp_rec_put32(ack+8u,2u);comp_rec_put32(ack+32u,comp_rec_crc(ack,32u));
 assert(comp_v11_product_input_request(&app,ack,36u,false,now_ms,reply)==64u&&!app.input.pointer_count);
 assert(comp_input_mode(&app.input,COMP_INPUT_POINTER,24u,false,false));
 comp_input_note(&app.input,COMP_INPUT_CLICK,300u);app.input.pointer_events[app.input.pointer_head].reserved=0x6Cu;
 now_ms=301u;input_notify();assert(comp_rec_get32(published+36u)==0x6Cu&&comp_rec_get32(published+16u)==300u);
 now_ms=341u;input_notify();assert(comp_rec_get32(published+36u)==0x6Cu); /* Axis/sign survives retry. */
 /* Drive the REAL CIN GATT event branch, not a duplicate reply-policy function. */
 memset(&app.input,0,sizeof(app.input));app.runtime.owned=false;link_ready=true;
 uint8_t wire[36]={0};memcpy(wire,"CIN1",4);wire[4]=1u;
 memcpy(wire+12u,app.recording.catalog.uid,12u);comp_rec_put64(wire+24u,app.recording.catalog.epoch);
 comp_rec_put32(wire+8u,77u);comp_rec_put32(wire+32u,comp_rec_crc(wire,32u));
 companion_gatt_event_t e={COMPANION_GATT_EVENT_WRITE,COMPANION_GATT_CHAR_SETTINGS,wire,36u};
 count=publishes;actual_input_event(&e);
 assert(publishes==count+1u&&comp_rec_get32(published+8u)==77u); /* Query replies remain visible. */
 wire[5]=1u;wire[6]=COMP_INPUT_POINTER;wire[7]=COMP_INPUT_POINTER_V4;
 comp_rec_put32(wire+8u,78u);comp_rec_put32(wire+32u,comp_rec_crc(wire,32u));
 actual_input_event(&e);assert(app.input.mode==COMP_INPUT_POINTER&&publishes==count+2u);
 comp_input_note(&app.input,COMP_INPUT_CLICK,1000u);comp_input_note(&app.input,COMP_INPUT_CLICK,1100u);
 uint32_t head=comp_input_pointer_event(&app.input)->sequence;
 wire[5]=2u;wire[6]=wire[7]=0u;comp_rec_put32(wire+8u,head);comp_rec_put32(wire+32u,comp_rec_crc(wire,32u));
 count=publishes;unsigned cached=read_cache_updates;actual_input_event(&e);
 if(publishes!=count){fputs("FAIL successful ACK generated an unnecessary ACK-of-ACK notification\n",stderr);return 1;}
 assert(app.input.pointer_count==1u&&read_cache_updates==cached+1u);
 now_ms=1101u;input_notify();assert(publishes==count+1u&&comp_rec_get32(published+8u)==0u&&comp_rec_get32(published+12u)!=head);
 count=publishes;actual_input_event(&e);assert(publishes==count&&app.input.pointer_count==1u); /* Retried old ACK cannot consume next edge or create a notification loop. */
 wire[12]^=1u;comp_rec_put32(wire+32u,comp_rec_crc(wire,32u));count=product_link.rejected_writes;
 actual_input_event(&e);assert(product_link.rejected_writes==count+1u&&app.input.pointer_count==1u);
 puts("PASS actual CIN GATT dispatcher: query/mode responses retained; successful/duplicate ACK does not echo; next physical edge alone notifies; wrong peer rejected");
 puts("PASS actual pointer CIN: retry keeps original edge/flags/time, ACK works while busy without mode/MIC command, duplicate/wrong UID cannot consume next edge");
 puts("PASS real CIN1 builders1000 byte-identical packets;10000 idle turns serialize0; held change, sticky event, failed publication retry and subscription preserved. Software only.");
}
""".replace("typeof_unused:","")
model=out/"model.c";model.write_text(re.sub(r"\bfeedback\b","fixture_feedback",pre)+old+new+post+request+notify+actual_event+re.sub(r"\bfeedback\b","fixture_feedback",tests))
app=root/"app/companion_pendant";includes=[platform,app/"recording",app/"power",app/"imu"]
cmd=["cl.exe","/nologo","/TC","/std:c11","/O2","/W4","/WX","/wd4100","/wd4505",*["/I"+str(p)for p in includes],str(model),str(app/"power/wba_button.c"),"/Fe:"+str(out/"test.exe")]
batch=out/"compile.cmd";batch.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n')
for name,cmd in [("compile",["cmd","/d","/c",str(batch)]),("run",[str(out/"test.exe")])]:
 r=subprocess.run(cmd,cwd=out,capture_output=True,text=True,encoding="utf-8",errors="replace");(out/(name+".log")).write_text(r.stdout+r.stderr);print(name,r.returncode,r.stdout+r.stderr);r.check_returncode()
(out/"result.json").write_text(json.dumps({"result":"PASS_CIN1_WIRE_EQUAL_AND_NO_IDLE_CRC","softwareOnly":True})+"\n")
