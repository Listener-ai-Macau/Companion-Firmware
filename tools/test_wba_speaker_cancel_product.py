"""Production late-start gate + real recorder/NOR model; no board access."""
from pathlib import Path
import hashlib
import json
import subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(r"E:/CodexData/Companion/speaker-shutdown-fault-20261030/product-cancel-r3")
APP=ROOT/"app/companion_pendant"
REC=APP/"recording"
NAMES=['wba_recording_radio','wba_segment_pull','wba_segment_directory',
       'wba_recording_transfer','companion_recording_journal','wba_recording_recovery',
       'wba_recording_pipeline','wba_segment_storage','companion_continuous_recording',
       'companion_segment_audio','companion_segment_catalog','companion_segment_reserve',
       'companion_opus16_rt','wba_recording_product','wba_segment_discard_preview',
       'wba_segment_discard_worker','wba_segment_discard_control','wba_segment_discard_wire']

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    code=(ROOT/'platform/stm32wba55_companion_v11/product_app.c').read_text(encoding='utf-8')
    body=code[code.index('static bool recording_control(void *c,bool start,uint32_t token)\n{'):code.index('bool comp_v11_product_recording_bookmark(')]
    fixture=r'''
#define COMP_PRODUCT_TEST_MAIN prior_product_main
#include "test_wba_recording_product.c"
#define COMP_V11_FAULT_SPEAKER_SHUTDOWN 1024u
typedef struct {bool running;} speaker_test_mic;
typedef struct {uint32_t faults;speaker_test_mic microphone;} speaker_test_board;
typedef struct {speaker_test_board *board;bool recording_ready;
 comp_wba_recording_product_t recording;comp_runtime_t runtime;} comp_v11_product_app_t;
static bool recording_power_allowed(comp_v11_product_app_t *a){(void)a;return true;}
static uint32_t HAL_GetTick(void){return f.now;}
bool comp_runtime_recording_update(comp_runtime_t *r,uint32_t token,
 denzic_audio_recording_state_v1_t state,bool capture,uint32_t tick)
{(void)r;(void)token;(void)state;(void)capture;(void)tick;return true;}
'''
    checks=r'''
static void my_tick(comp_v11_product_app_t *a){f.now+=2u;comp_wba_recording_product_poll(&a->recording);}
static void current(comp_v11_product_app_t *a){
 for(unsigned i=0;i<20000u&&!comp_wba_recording_product_space_current(&a->recording);i++)my_tick(a);
 assert(comp_wba_recording_product_space_current(&a->recording));
}
static void done(comp_v11_product_app_t *a){
 for(unsigned i=0;i<20000u&&a->recording.pipeline.state!=COMP_PIPE_FINISHED;i++)my_tick(a);
 assert(a->recording.pipeline.state==COMP_PIPE_FINISHED&&!mic);
 current(a);
}
int main(void){
 product_fresh();speaker_test_board b={0};comp_v11_product_app_t a={0};a.board=&b;a.recording_ready=true;
 comp_wba_pipeline_config_t cfg={0};cfg.microphone=microphone;cfg.now_ms=now;cfg.segment_frames=20u;cfg.extent_bytes=4096u;
 assert(comp_wba_recording_product_bind(&a.recording,&nor,0u,24576u,DATA_BASE,65536u,
  49152u,device_uid,7u,&cfg,product_report));current(&a);
 comp_wba_recording_product_lease_result(&a.recording,true);assert(a.recording.ready);
 assert(comp_wba_recording_product_prepare(&a.recording,101u,1u,0u,91u));
 for(unsigned i=0;i<20000u&&!comp_wba_recording_product_ready(&a.recording,91u);i++)my_tick(&a);
 assert(comp_wba_recording_product_ready(&a.recording,91u)&&recording_control(&a,true,91u));
 for(unsigned block=0;block<8u;block++){int16_t samples[160];pcm(block,samples);
  assert(comp_wba_recording_product_pcm(&a.recording,samples,160u,16000u));
  for(unsigned i=0;i<100u;i++)my_tick(&a);}
 assert(comp_wba_recording_product_control(&a.recording,false,91u));done(&a);
 comp_segment_entry_t original={0};bool found=false;
 for(uint8_t i=0;i<64u;i++)if(a.recording.catalog.slots[i]!=255u){
  assert(comp_wba_segment_storage_entry(&a.recording.storage,&a.recording.catalog,i,&original)==COMP_SEG_OK);
  if(original.state==COMP_SEG_UNSYNCED){found=true;break;}}
 assert(found && original.reserved_bytes<=4096u);uint8_t old[4096];
 memcpy(old,&f.bytes[DATA_BASE+original.extent_offset],original.reserved_bytes);
 unsigned oldstarts=mic_starts;uint64_t visible=a.recording.catalog.visible_mask;
 for(unsigned stage=0;stage<2;stage++){
  uint32_t token=92u+stage;assert(comp_wba_recording_product_prepare(&a.recording,102u+stage,1u,0u,token));
  if(stage){for(unsigned i=0;i<20000u&&!comp_wba_recording_product_ready(&a.recording,token);i++)my_tick(&a);
   assert(comp_wba_recording_product_ready(&a.recording,token));}
  b.faults=COMP_V11_FAULT_SPEAKER_SHUTDOWN;assert(!recording_control(&a,true,token));
  assert(!mic&&mic_starts==oldstarts);done(&a);
  assert(a.recording.catalog.visible_mask==visible);
  assert(!memcmp(old,&f.bytes[DATA_BASE+original.extent_offset],original.reserved_bytes));
  b.faults=0u;
 }
 assert(comp_wba_recording_product_prepare(&a.recording,110u,1u,0u,98u));
 for(unsigned i=0;i<20000u&&!comp_wba_recording_product_ready(&a.recording,98u);i++)my_tick(&a);
 assert(comp_wba_recording_product_ready(&a.recording,98u));
 assert(recording_control(&a,true,98u)&&mic&&mic_starts==oldstarts+1u);
 b.faults=COMP_V11_FAULT_SPEAKER_SHUTDOWN;
 assert(recording_control(&a,false,98u));done(&a);b.faults=0u;
 assert(!memcmp(old,&f.bytes[DATA_BASE+original.extent_offset],original.reserved_bytes));
 puts("PASS production late-start + actual recorder/NOR model: both preparation stages cancel, old audio untouched, next start and fault-time stop succeed");
 return 0;
}
'''
    sdk=OUT/'host-sdk';sdk.mkdir(exist_ok=True)
    (sdk/'ble_types.h').write_text('#include <stdint.h>\ntypedef uint8_t tBleStatus;\n')
    (sdk/'stm32_wpan_common.h').write_text('/* GATT portable model */\n')
    test=OUT/'test.c';test.write_text(fixture+body+checks,encoding='utf-8')
    includes=[sdk,REC/'tests',*[APP/n for n in ['runtime','recording','storage','gatt','v1_features','playback','touch','epaper','imu','power']],ROOT/'third_party/denzic-platform/audio/embedded/c/include',ROOT/'third_party/opus/include']
    sources=[test,APP/'runtime/companion_link.c',*[REC/(n+'.c') for n in NAMES],APP/'storage/spi_nor_stm32wba.c']
    lib=Path(r'C:/Users/Billy/Desktop/Denzic/Companion/Companion-Firmware/.cache/opus-host-fixed/opus.lib')
    exe=OUT/'test.exe';args=['cl.exe','/nologo','/W4','/WX','/wd5287','/wd4100','/std:c11','/TC','/O2','/MD',
        '/DCOMPANION_OPUS16_WBA_LOWDELAY=1','/DCOMPANION_OPUS16_ENCODER_BYTES=65536',
        '/DCOMPANION_RECORDING_SEGMENTED_ONLY=1',*['/I'+str(p) for p in includes],
        *map(str,sources),'/Fe:'+str(exe),'/link',str(lib)]
    cmd=OUT/'compile.cmd';cmd.write_text('@echo off\ncall "'+str(find_vsdevcmd())+
        '" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
    files=[*sources[1:],REC/'tests/test_wba_recording_product.c',ROOT/'platform/stm32wba55_companion_v11/product_app.c',lib]
    (OUT/'source_hashes.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2))
    for command,name in [(['cmd.exe','/d','/c',str(cmd)],'compile.log'),([str(exe)],'result.log')]:
        result=subprocess.run(command,cwd=OUT,text=True,capture_output=True)
        (OUT/name).write_text(result.stdout+result.stderr,encoding='utf-8')
        if result.returncode:raise RuntimeError(f'exit {result.returncode}: {OUT/name}')
    print((OUT/'result.log').read_text(encoding='utf-8').strip())

if __name__=='__main__':main()
