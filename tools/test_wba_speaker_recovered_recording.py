"""Production speaker failure/recovery joined to the actual recorder/NOR model."""
from pathlib import Path
import subprocess

from test_wba_speaker_cancel_product import APP, NAMES, REC, ROOT
from verify_wba_spi_nor_adapter import find_vsdevcmd

OUT = Path(r"E:/CodexData/Companion/speaker-shutdown-fault-20261030/recovered-recording-r2")


def literal(src, marker):
    return src.split(marker, 1)[1].split("'''", 1)[0]


def section(src, start, end):
    return src[src.index(start):src.index(end)]


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    board = (ROOT / 'platform/stm32wba55_companion_v11/board_hal.c').read_text(encoding='utf8')
    product = (ROOT / 'platform/stm32wba55_companion_v11/product_app.c').read_text(encoding='utf8')
    speaker_test = (ROOT / 'tools/test_wba_speaker_shutdown_recovery.py').read_text(encoding='utf8')
    product_test = (ROOT / 'tools/test_wba_speaker_cancel_product.py').read_text(encoding='utf8')
    speaker = literal(speaker_test, "fixture = r'''")
    speaker = speaker.replace('speaker_submit_started_ms,now;', 'speaker_submit_started_ms;')
    speaker = speaker.replace('static uint32_t HAL_GetTick(void){return now;}',
                              'static uint32_t HAL_GetTick(void){return f.now;}')
    product_fixture = literal(product_test, "fixture=r'''").lstrip('\n')
    product_fixture = product_fixture.replace('#define COMP_V11_FAULT_SPEAKER_SHUTDOWN 1024u\n', '')
    product_fixture = product_fixture.replace('typedef struct {bool running;} speaker_test_mic;\n'
        'typedef struct {uint32_t faults;speaker_test_mic microphone;} speaker_test_board;\n',
        'typedef comp_v11_hal_t speaker_test_board;\n')
    product_fixture = product_fixture.replace('static uint32_t HAL_GetTick(void){return f.now;}\n', '')
    # The recorder fixture must precede the board fixture so HAL_GetTick sees f.
    recorder_include = '#define COMP_PRODUCT_TEST_MAIN prior_product_main\n#include "test_wba_recording_product.c"\n'
    assert product_fixture.startswith(recorder_include)
    product_fixture = product_fixture[len(recorder_include):]
    parts = [recorder_include, speaker, product_fixture,
        section(board, 'static bool amp(', 'static bool submit('),
        section(board, 'static void activity(', 'static bool speaker_init('),
        section(board, 'void comp_v11_hal_speaker_poll(', '#if defined(__GNUC__)\n__attribute__((section(".sram1.bss")'),
        section(product, 'static bool recording_control(void *c,bool start,uint32_t token)\n{',
                'bool comp_v11_product_recording_bookmark(')]
    checks = r'''
static void my_tick(comp_v11_product_app_t *a){f.now+=2u;comp_wba_recording_product_poll(&a->recording);}
static void wait_current(comp_v11_product_app_t *a){
 for(unsigned i=0;i<20000u&&!comp_wba_recording_product_space_current(&a->recording);i++)my_tick(a);
 assert(comp_wba_recording_product_space_current(&a->recording));}
static void finish_record(comp_v11_product_app_t *a){
 for(unsigned i=0;i<20000u&&a->recording.pipeline.state!=COMP_PIPE_FINISHED;i++)my_tick(a);
 assert(a->recording.pipeline.state==COMP_PIPE_FINISHED&&!mic);wait_current(a);}
static void prepare(comp_v11_product_app_t *a,uint32_t token){
 assert(comp_wba_recording_product_prepare(&a->recording,100u+token,1u,0u,token));
 for(unsigned i=0;i<20000u&&!comp_wba_recording_product_ready(&a->recording,token);i++)my_tick(a);
 assert(comp_wba_recording_product_ready(&a->recording,token));}
int main(void){
 product_fresh();comp_v11_hal_t b={0};comp_v11_product_app_t a={0};a.board=&b;a.recording_ready=true;
 comp_wba_pipeline_config_t cfg={0};cfg.microphone=microphone;cfg.now_ms=now;cfg.segment_frames=20u;cfg.extent_bytes=4096u;
 assert(comp_wba_recording_product_bind(&a.recording,&nor,0u,24576u,DATA_BASE,65536u,49152u,device_uid,7u,&cfg,product_report));
 wait_current(&a);comp_wba_recording_product_lease_result(&a.recording,true);assert(a.recording.ready);
 prepare(&a,91u);assert(recording_control(&a,true,91u));
 for(unsigned block=0;block<8u;block++){int16_t samples[160];pcm(block,samples);
  assert(comp_wba_recording_product_pcm(&a.recording,samples,160u,16000u));for(unsigned i=0;i<100u;i++)my_tick(&a);}
 assert(comp_wba_recording_product_control(&a.recording,false,91u));finish_record(&a);
 comp_segment_entry_t original={0};bool found=false;
 for(uint8_t i=0;i<64u;i++)if(a.recording.catalog.slots[i]!=255u){
  assert(comp_wba_segment_storage_entry(&a.recording.storage,&a.recording.catalog,i,&original)==COMP_SEG_OK);
  if(original.state==COMP_SEG_UNSYNCED){found=true;break;}}
 assert(found && original.reserved_bytes<=4096u);uint8_t old[4096];
 memcpy(old,&f.bytes[DATA_BASE+original.extent_offset],original.reserved_bytes);
 assert(comp_tca6408_init(&b.io,read_io,write_io,&b,0x20u,0x03u,0u));b.io.admit_write=admit;
 comp_speaker_config_t sc={amp,submit,activity,&b};comp_speaker_init(&b.speaker,&sc);
 assert(comp_speaker_play_cue(&b.speaker,COMP_SPEAKER_CUE_CONFIRM)==COMP_SPEAKER_OK);
 assert(comp_speaker_service(&b.speaker));
 failed_write=1;drop_write=1;comp_speaker_tx_complete(&b.speaker,false);
 assert(!b.io.ready && (b.faults&COMP_V11_FAULT_SPEAKER_SHUTDOWN));
 prepare(&a,92u);assert(!recording_control(&a,true,92u));finish_record(&a);assert(!mic);
 failed_write=drop_write=0;f.now+=1000u;irq_line_enabled=1;comp_v11_hal_speaker_poll(&b);
 assert(b.io.ready && !(b.faults&COMP_V11_FAULT_SPEAKER_SHUTDOWN) && !b.playback_active);
 comp_audio_feedback_t feedback;comp_audio_feedback_config_t fc={&b.speaker,NULL,&b,150u,1500u};
 comp_audio_feedback_init(&feedback,&fc);
 assert(comp_audio_feedback_submit(&feedback,COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST,f.now)==COMP_AUDIO_FEEDBACK_SUBMIT_ACCEPTED);
 comp_audio_feedback_service(&feedback,f.now);comp_audio_feedback_outcome_t outcome;
 assert(comp_audio_feedback_take_recording_start_gate(&feedback,&outcome));
 assert(outcome==COMP_AUDIO_FEEDBACK_OUTCOME_FAILED);
 assert(comp_audio_feedback_set_recording_active(&feedback,true));
 prepare(&a,93u);assert(recording_control(&a,true,93u)&&mic);
 for(unsigned block=0;block<8u;block++){int16_t samples[160];pcm(block,samples);
  assert(comp_wba_recording_product_pcm(&a.recording,samples,160u,16000u));for(unsigned i=0;i<100u;i++)my_tick(&a);}
 assert(recording_control(&a,false,93u));finish_record(&a);
 assert(!memcmp(old,&f.bytes[DATA_BASE+original.extent_offset],original.reserved_bytes));
 puts("PASS actual speaker/feedback + recorder/Opus/NOR: fault rejects, recovery permits recording, protected old audio unchanged");
 return 0;
}
'''
    test = OUT/'test.c'; test.write_text(''.join(parts)+checks,encoding='utf8')
    sdk=OUT/'host-sdk';sdk.mkdir();(sdk/'ble_types.h').write_text('#include <stdint.h>\ntypedef uint8_t tBleStatus;\n')
    (sdk/'stm32_wpan_common.h').write_text('/* model */\n')
    includes=[sdk,REC/'tests',*[APP/n for n in ['runtime','recording','storage','gatt','v1_features','playback','touch','epaper','imu','power','board']],ROOT/'third_party/denzic-platform/audio/embedded/c/include',ROOT/'third_party/opus/include']
    sources=[test,APP/'runtime/companion_link.c',*[REC/(n+'.c') for n in NAMES],APP/'storage/spi_nor_stm32wba.c',APP/'playback/speaker_playback.c',APP/'playback/audio_feedback.c',APP/'board/tca6408.c']
    lib=Path(r'C:/Users/Billy/Desktop/Denzic/Companion/Companion-Firmware/.cache/opus-host-fixed/opus.lib')
    exe=OUT/'test.exe';args=['cl.exe','/nologo','/W4','/WX','/wd5287','/wd4100','/std:c11','/TC','/O2','/MD',
       '/DCOMPANION_OPUS16_WBA_LOWDELAY=1','/DCOMPANION_OPUS16_ENCODER_BYTES=65536','/DCOMPANION_RECORDING_SEGMENTED_ONLY=1',
       *['/I'+str(p) for p in includes],*map(str,sources),'/Fe:'+str(exe),'/link',str(lib)]
    cmd=OUT/'compile.cmd';cmd.write_text('@echo off\ncall "'+str(find_vsdevcmd())+
       '" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
    for command,name in [(['cmd.exe','/d','/c',str(cmd)],'compile.log'),([str(exe)],'result.log')]:
        result=subprocess.run(command,cwd=OUT,text=True,capture_output=True)
        (OUT/name).write_text(result.stdout+result.stderr,encoding='utf8')
        if result.returncode:raise RuntimeError(f'exit {result.returncode}: {OUT/name}')
    print((OUT/'result.log').read_text(encoding='utf8').strip())


if __name__ == '__main__': main()
