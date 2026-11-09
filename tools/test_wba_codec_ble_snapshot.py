"""Exercise real cached codec getter, BLE fields and CRM1 wire framing."""
from pathlib import Path
import argparse,json,subprocess,hashlib
from verify_wba_spi_nor_adapter import find_vsdevcmd
from test_wba_ota_stream_backpressure import function
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[1];platform=root/'platform/stm32wba55_companion_v11';out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
cpu=(platform/'cpu_profile_target.c').read_text();ble=(platform/'ble/ble_product.c').read_text()
getter=function(cpu,'bool comp_v11_cpu_codec_read');fields=function(ble,'static void maintenance_codec_fields')
imu_fields=function(ble,'static void maintenance_imu_fields')
(out/'getter.inc').write_text(getter);(out/'fields.inc').write_text(fields);(out/'imu_fields.inc').write_text(imu_fields)
fixture=r'''
#include "maintenance_protocol.h"
#include "cpu_codec_irq.h"
#include "companion_cpu_stage.h"
#include <assert.h>
#include <stdio.h>
#include "lsm6dso.h"
typedef struct {uint32_t token,bookmark_request,bookmark_sequence;struct {uint32_t accepted_pcm_blocks;}stats;struct {struct {uint64_t session_id;} descriptor;}active;} comp_cont_recording_t;
typedef struct {comp_lsm6dso_t imu;struct {bool running;}microphone;} board_t;
static board_t board;
static struct {struct {bool media_ready;struct {comp_cont_recording_t engine;}capture;}recording;board_t *board;} instance,*product=&instance;
#include "imu_fields.inc"
#if COMPANION_WBA_CPU_RESIDENCE_PROFILE
static struct {bool active;struct {uint32_t clock_errors,order_errors,reference_errors,token;}stats;} residence;
static bool transport_capture;
static struct {uint32_t calls,peak_us,peak_irq_us,peak_hits,peak_misses,peak_admission_flags,peak_admission_next_us,saturations;} codec_cache;
static comp_cpu_codec_irq_t codec_irq;
static struct {uint32_t calls,invalid;} stage_stats[COMP_CPU_STAGE_STORAGE_COUNT];
static uint32_t opus_over_budget[3];
#include "getter.inc"
#include "fields.inc"
#endif
static bool request(uint8_t op,uint32_t nonce,bool bad_crc)
{
    uint8_t wire[16]={0};memcpy(wire,"CRM1",4u);wire[4]=op;
    comp_maint_put32(wire+8u,nonce);comp_maint_put32(wire+12u,companion_crc32(0u,wire,12u));
    if(bad_crc)wire[15]^=1u;uint8_t got=255u;uint32_t id=0u;
    bool ok=comp_maint_request(wire,16u,&got,&id);
    if(ok)assert(got==op && id==nonce);return ok;
}
int main(void)
{
    for(unsigned op=0u;op<=10u;op++)assert(request((uint8_t)op,123u,false));
    assert(!request(11u,123u,false) && !request(31u,123u,false) && !request(39u,123u,false));
    product->board=&board;product->recording.media_ready=true;
    comp_cont_recording_t *r=&product->recording.capture.engine;
    r->token=77u;r->active.descriptor.session_id=UINT64_C(0x1122334455667788);
    r->stats.accepted_pcm_blocks=100u;r->bookmark_request=88u;r->bookmark_sequence=2u;
    board.imu.state=COMP_IMU_READY;board.imu.tap_reads=42u;board.imu.tap_counts=0x00020005u;
    for(uint8_t op=16u;op<=17u;op++) {
        uint8_t w[32];assert(request(op,123u,false)&&!request(op,0u,false)&&!request(op,123u,true));
        comp_maint_response(w,op,COMP_MAINT_OK,123u,0u,0u,0u,0u,0u,0u);
        maintenance_imu_fields(op,w);comp_maint_put32(w+28u,companion_crc32(0u,w,28u));
        assert(w[5]==COMP_MAINT_OK&&w[6]==25u&&w[7]==1u);
        assert(comp_maint_get32(w+12u)==0x55667788u&&comp_maint_get32(w+16u)==0x11223344u);
        assert(comp_maint_get32(w+20u)==(op==16u?42u:88u)&&comp_maint_get32(w+24u)==(op==16u?0x20005u:2u));
        assert(comp_maint_get32(w+28u)==companion_crc32(0u,w,28u));
    }
    uint8_t iw[32]={0};board.microphone.running=true;board.imu.recording_taps=true;
    maintenance_imu_fields(16u,iw);assert(iw[6]==31u&&board.imu.tap_reads==42u&&board.imu.tap_counts==0x20005u);
    r->stats.accepted_pcm_blocks=0u;maintenance_imu_fields(16u,iw);assert(!(iw[6]&16u));
    product->recording.media_ready=false;maintenance_imu_fields(16u,iw);assert(iw[5]==COMP_MAINT_BUSY);
    product->recording.media_ready=true;r->active.descriptor.session_id=0u;maintenance_imu_fields(17u,iw);assert(iw[5]==COMP_MAINT_BUSY);
    r->active.descriptor.session_id=UINT64_C(0x1122334455667788);
    puts("PASS cached IMU scalars: explicit source session, saturated raw counts and durable marks, no mutation/I/O, invalid preparation owner and missing media distinguished");
#if COMPANION_WBA_CPU_RESIDENCE_PROFILE
    uint32_t v[4];uint8_t flags;
    assert(comp_v11_cpu_codec_read(0u,v,&flags) && v[0]==0u && v[3]==0u && flags==5u);
    residence.stats.token=77u;codec_cache.calls=10u;codec_cache.peak_us=6500u;codec_cache.peak_irq_us=1900u;
    codec_cache.peak_hits=20000u;codec_cache.peak_misses=30u;
    codec_cache.peak_admission_flags=0x02010303u;codec_cache.peak_admission_next_us=9000u;
    codec_irq.peak_us=1800u;codec_irq.peak_kind=60u;codec_irq.peak_radio_us=1600u;
    stage_stats[COMP_CPU_STAGE_OPUS].calls=10u;opus_over_budget[1]=1u;
    product->recording.media_ready=true;product->recording.capture.engine.token=77u;
    product->recording.capture.engine.active.descriptor.session_id=UINT64_C(0x1122334455667788);
    const uint32_t expected[7][4]={{77u,6500u,1900u,10u},{77u,20000u,30u,1800u},
        {77u,60u,1600u,300u},{77u,0x02010303u,9000u,0u},{77u,0u,0u,0u},
        {77u,10u,1u,0u},{77u,77u,0x55667788u,0x11223344u}};
    for(unsigned page=0u;page<7u;page++) {
        uint8_t op=(uint8_t)(32u+page),wire[32];assert(request(op,123u,false));
        assert(!request(op,0u,false) && !request(op,123u,true));
        comp_maint_response(wire,op,COMP_MAINT_OK,123u,0u,255u,1u,2u,3u,4u);
        maintenance_codec_fields(op,wire);comp_maint_put32(wire+28u,companion_crc32(0u,wire,28u));
        assert(!memcmp(wire,"CRM1",4u) && wire[4]==op && wire[5]==0u && wire[6]==15u && wire[7]==1u);
        assert(comp_maint_get32(wire+8u)==123u && comp_maint_get32(wire+28u)==companion_crc32(0u,wire,28u));
        for(unsigned i=0u;i<4u;i++)assert(comp_maint_get32(wire+12u+4u*i)==expected[page][i]);
    }
    uint8_t wire[32]={0};residence.active=true;maintenance_codec_fields(32u,wire);
    assert(wire[5]==COMP_MAINT_BUSY && !comp_v11_cpu_codec_read(0u,v,&flags));residence.active=false;
    transport_capture=true;assert(!comp_v11_cpu_codec_read(0u,v,&flags));transport_capture=false;
    product->recording.capture.engine.token=78u;wire[5]=0u;maintenance_codec_fields(38u,wire);assert(wire[5]==COMP_MAINT_BUSY);
    product->recording.capture.engine.token=77u;product->recording.media_ready=false;wire[5]=0u;maintenance_codec_fields(38u,wire);assert(wire[5]==COMP_MAINT_BUSY);
    residence.stats.clock_errors=1u;assert(comp_v11_cpu_codec_read(2u,v,&flags) && flags==3u && v[3]==0u);
    assert(codec_cache.calls==10u && codec_cache.peak_us==6500u && residence.stats.token==77u && opus_over_budget[1]==1u);
    assert(!comp_v11_cpu_codec_read(6u,v,&flags));
    puts("PASS production BLE codec pages: one token/frame/session,IRQ split,admission/errors,busy ownership,nonce/CRC; cached read does not clear or sample; software only");
#else
    for(unsigned op=32u;op<=38u;op++)assert(!request((uint8_t)op,123u,false));
    puts("PASS normal CRM1 unchanged: all optional codec operations rejected; old operations retained");
#endif
    return 0;
}'''
(out/'model.c').write_text(fixture)
results={}
for profile in (0,1):
    folder=out/str(profile);folder.mkdir();exe=folder/'test.exe'
    args=['cl.exe','/nologo','/TC','/std:c11','/O2','/W4','/WX','/wd4127','/utf-8','/DCOMPANION_WBA_CPU_RESIDENCE_PROFILE='+str(profile),
        '/I'+str(out),'/I'+str(platform),'/I'+str(platform/'ble'),'/I'+str(root/'app/companion_pendant/imu'),'/I'+str(root/'app/companion_pendant/storage'),'/I'+str(root/'app/companion_pendant/recording'),str(out/'model.c'),'/Fe:'+str(exe)]
    batch=folder/'compile.cmd';batch.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
    for stage,cmd in [('compile',['cmd.exe','/d','/c',str(batch)]),('run',[str(exe)])]:
        r=subprocess.run(cmd,cwd=folder,capture_output=True,text=True,encoding='utf8',errors='replace');(folder/(stage+'.log')).write_text(r.stdout+r.stderr,encoding='utf8');print(profile,stage,r.returncode,r.stdout+r.stderr,flush=True);r.check_returncode();results[f'{profile}-{stage}']=r.returncode
(out/'result.json').write_text(json.dumps({'softwareOnly':True,'results':results,'getterSha256':hashlib.sha256(getter.encode()).hexdigest(),'fieldsSha256':hashlib.sha256(fields.encode()).hexdigest()},indent=2)+'\n')
