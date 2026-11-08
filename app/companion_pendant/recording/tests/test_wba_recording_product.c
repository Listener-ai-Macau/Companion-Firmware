#include "../wba_recording_product.h"
#define COMP_RADIO_TEST_MAIN product_radio_fixture_main
#include "test_wba_recording_radio.c"
#ifdef COMPANION_RECORDING_SEGMENTED_ONLY
/* Unexecuted V1 fixture helpers are compiled in this shared test translation
 * unit. Product-only tests may never enter that retired initializer. */
bool comp_link_init(comp_link_t *link,const comp_link_config_t *config)
{(void)link;(void)config;assert(!"legacy link fixture entered product-only test");return false;}
#endif

static comp_wba_recording_product_t product_rec;
static unsigned reports;
static uint32_t reported_token;
static denzic_audio_recording_state_v1_t reported_audio;
static bool reported_capture;
static void product_report(void *v,uint32_t token,denzic_audio_recording_state_v1_t state,bool active)
{(void)v;reports++;reported_token=token;reported_audio=state;reported_capture=active;}
static void product_tick(void)
{
    unsigned reads=f.reads,writes=f.writes;f.now+=2u;
    unsigned maximum=(product_rec.pipeline.state==COMP_PIPE_PREPARING||product_rec.pipeline.state==COMP_PIPE_CLEANUP)&&
        !product_rec.capture.engine.microphone_active&&!product_rec.capture.engine.encoder_owned?16u:1u;
    comp_wba_recording_product_poll(&product_rec);
    assert(f.reads-reads<=maximum&&f.writes-writes<=maximum);
}
static void product_bind(void)
{
    comp_wba_pipeline_config_t cfg={0};cfg.microphone=microphone;cfg.now_ms=now;
    cfg.segment_frames=20u;cfg.extent_bytes=4096u;
    assert(comp_wba_recording_product_bind(&product_rec,&nor,0u,24576u,DATA_BASE,65536u,
        49152u,device_uid,7u,&cfg,product_report));
}
static void product_fresh(void)
{
    reset();nor=make();f.automatic_erase=true;mic=false;mic_starts=mic_stops=reports=fail_mic_stops=0u;
    reported_token=0u;reported_capture=false;reported_audio=DENZIC_AUDIO_RECORDING_STATE_IDLE;
    product_bind();
}
static void product_mount(void)
{
    for(unsigned i=0u;i<20000u&&!comp_wba_recording_product_space_current(&product_rec)&&
        comp_wba_recording_product_state(&product_rec)!=COMP_WBA_RECORDING_FAULT;i++)product_tick();
    assert(product_rec.media_ready&&comp_wba_recording_product_space_current(&product_rec));
    assert(!product_rec.ready&&!mic);
}
static void product_refresh_space(void)
{
    for(unsigned i=0u;i<20000u&&!comp_wba_recording_product_space_current(&product_rec);i++)product_tick();
    assert(comp_wba_recording_product_space_current(&product_rec));
}
static void boot_and_ota_gate(void)
{
    product_fresh();uint8_t capability[32];
    assert(!comp_wba_recording_product_capability(&product_rec,capability));
    assert(!comp_wba_recording_product_prepare(&product_rec,101u,1u,0u,91u));
    product_mount();assert(product_rec.space.largest_gap==65536u&&!product_rec.space.reserved_bytes);
    uint32_t physical=0u;unsigned writes=f.writes;
    assert(comp_wba_recording_product_workspace(&product_rec,12288u,&physical)&&physical==DATA_BASE+53248u);
    assert(f.writes==writes&&!mic&&!comp_wba_recording_product_prepare(&product_rec,101u,1u,0u,91u));
    comp_wba_recording_product_lease_result(&product_rec,true);assert(product_rec.ready);
    assert(comp_wba_recording_product_capability(&product_rec,capability)&&!memcmp(capability,"CRV2",4u)&&
        comp_rec_get32(capability+8u)==(255u|256u|(product_rec.pipeline.config.audio_profile?512u:0u)|COMP_REC_V2_CAP_WIDE_SEGMENT_INDEX)
        &&comp_rec_get32(capability+28u)==comp_rec_crc(capability,28u));
    assert(!comp_wba_recording_product_prepare(&product_rec,101u,1u,0u,91u));
    product_refresh_space();assert(product_rec.space.arena_bytes==53248u&&product_rec.space.largest_gap==53248u);
    assert(comp_wba_recording_product_workspace(&product_rec,12288u,&physical)); /* exact WUS2 replay */
    assert(comp_wba_recording_product_workspace(&product_rec,0u,&physical)&&physical==0u);
    product_refresh_space();assert(product_rec.space.arena_bytes==65536u);
    puts("PASS product boot: cooperative mount/old-owner blank proof/recovery precede CRV2 and MIC; exact OTA tail restore/release gates capture; software only");
}
static void refuse_old_owner(void)
{
    product_fresh();f.bytes[49152u+4096u+255u]=0u;
    for(unsigned i=0u;i<2000u&&comp_wba_recording_product_state(&product_rec)!=COMP_WBA_RECORDING_FAULT;i++)product_tick();
    assert(!product_rec.ready&&!product_rec.media_ready&&!mic&&f.writes==0u&&f.erases==0u);
    assert(f.bytes[49152u+4096u+255u]==0u);
    puts("PASS old nonblank catalog: last-sector ownership blocks V2 formatting; no optimistic initialization or erase; software only");
}
static void product_ready_capture(uint64_t session,uint32_t token)
{
    assert(comp_wba_recording_product_prepare(&product_rec,session,1u,0u,token));
    for(unsigned i=0u;i<20000u&&!comp_wba_recording_product_ready(&product_rec,token);i++)product_tick();
    assert(!mic&&comp_wba_recording_product_ready(&product_rec,token));
    assert(!comp_wba_recording_product_control(&product_rec,true,token+1u));
    assert(comp_wba_recording_product_control(&product_rec,true,token));
    assert(mic&&reported_capture&&reported_token==token&&reported_audio==DENZIC_AUDIO_RECORDING_STATE_RECORDING);
}
static comp_segment_entry_t product_entry(unsigned index)
{
    comp_segment_entry_t e={0};unsigned count=0u;
    for(uint8_t i=0u;i<64u;i++)if(product_rec.catalog.slots[i]!=255u) {
        assert(comp_wba_segment_storage_entry(&product_rec.storage,&product_rec.catalog,i,&e)==COMP_SEG_OK);
        if(count++==index)return e;
    }
    assert(false);return e;
}
static void actual_pcm_and_logical_count(void)
{
    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    product_ready_capture(101u,91u);
    for(unsigned block=0u;block<70u;block++) {
        int16_t samples[160];pcm(block,samples);
        assert(!comp_wba_recording_product_pcm(&product_rec,samples,160u,8000u));
        assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
        for(unsigned i=0u;i<160u;i++)product_tick();
    }
    assert(mic&&mic_starts==1u&&!mic_stops&&product_rec.capture.engine.stats.sealed_segments==1u);
    assert(comp_wba_recording_product_control(&product_rec,false,91u));
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)product_tick();
    assert(!mic&&mic_stops==1u&&product_rec.pipeline.state==COMP_PIPE_FINISHED);
    assert(reported_audio==DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY&&!reported_capture);
    product_refresh_space();assert(product_rec.space.used==2u&&product_rec.space.unsynced==2u&&product_rec.space.logical==1u);
    comp_segment_entry_t first=product_entry(0u),second=product_entry(1u);
    assert(first.descriptor.session_id==101u&&second.descriptor.session_id==101u&&
        first.descriptor.segment_index==0u&&second.descriptor.segment_index==1u&&
        first.descriptor.sample_count+second.descriptor.sample_count==11200u);
    /* Test the same product owner, including receiver-confirmed reclaim and
     * the cached logical count after its first physical segment disappears. */
    assert(comp_wba_recording_pipeline_consume(&product_rec.pipeline,&first.descriptor)==COMP_SEG_PENDING);
    for(unsigned i=0u;i<20000u&&comp_wba_recording_pipeline_consume_result(&product_rec.pipeline)==COMP_SEG_PENDING;i++)product_tick();
    assert(comp_wba_recording_pipeline_consume_result(&product_rec.pipeline)==COMP_SEG_OK);
    product_refresh_space();assert(product_rec.space.used==1u&&product_rec.space.logical==1u);
    unsigned writes=f.writes;uint32_t physical;
    assert(!comp_wba_recording_product_workspace(&product_rec,65536u,&physical)&&f.writes==writes);
    assert(comp_wba_recording_pipeline_workspace_snapshot(&product_rec.pipeline,4096u,
        product_rec.space.generation-1u,product_rec.space.highest_end,&physical)==COMP_SEG_STALE_SNAPSHOT);
    uint32_t count_before=product_rec.catalog.generation;
    product_bind();product_mount();assert(product_rec.space.used==1u&&product_rec.space.logical==1u&&
        product_rec.catalog.generation==count_before);
    comp_wba_recording_product_lease_result(&product_rec,true);
    assert(product_entry(0u).descriptor.recording_id==second.descriptor.recording_id);
    puts("PASS actual product ports:16kHz PCM/one Opus owner/two continuous segments/STOP report/consume/reboot; one logical recording after first segment recycled; software only");
}
static void cancel_and_capture_fault(void)
{
    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    assert(comp_wba_recording_product_prepare(&product_rec,102u,1u,0u,92u));
    product_tick();assert(comp_wba_recording_product_control(&product_rec,false,92u));
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)product_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED&&!mic&&!mic_starts&&reported_audio==DENZIC_AUDIO_RECORDING_STATE_CANCELED);
    product_refresh_space();assert(product_rec.space.used==0u);
    product_ready_capture(103u,93u);
    comp_wba_recording_product_fault(&product_rec,COMP_WBA_RECORDING_FAULT_DEADLINE);
    assert(!mic&&product_rec.pipeline.state==COMP_PIPE_FAILED&&product_rec.last_fault==COMP_WBA_RECORDING_FAULT_DEADLINE&&
        reported_audio==DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY&&!reported_capture);
    unsigned writes=f.writes;assert(!comp_wba_recording_product_prepare(&product_rec,104u,1u,0u,94u)&&f.writes==writes);
    assert(product_rec.catalog.slots[0]!=255u); /* no silent loss/retry */
    puts("PASS early cancel and actual deadline fault: no phantom recording, no saved result for failure, uncertain reservation retained; software only");
}
static uint8_t logical_status[80];
static uint16_t logical_status_bytes;
static unsigned logical_publish_attempts,logical_publish_failures;
static bool logical_publish(void *context,companion_gatt_char_id_t id,const uint8_t *p,uint16_t n)
{
    (void)context;
    if(id==COMPANION_GATT_CHAR_MEETING_STATUS) {
        ++logical_publish_attempts;
        if(logical_publish_failures){--logical_publish_failures;return false;}
        assert(n==64u||n==80u);memcpy(logical_status,p,n);logical_status_bytes=n;
        assert(!memcmp(p+28u,n==64u?"CMS2":"CMS3",4u)&&
            comp_rec_get32(p+(n==64u?60u:76u))==comp_rec_crc(p,n==64u?60u:76u));
    }
    return true;
}
static void initial_status_without_subscription(void)
{
    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    memset(&link_owner,0,sizeof(link_owner));memset(logical_status,0,sizeof(logical_status));
    logical_status_bytes=0u;logical_publish_attempts=0u;logical_publish_failures=0u;
    comp_link_config_t cfg={&link_owner.runtime,NULL,NULL,&link_owner.features,logical_publish,NULL};
    assert(comp_link_init_segmented(&link_owner.link,&cfg,&radio,&product_rec.pipeline,248u));
    comp_link_connection(&link_owner.link,true,false,f.now);comp_link_poll(&link_owner.link,f.now);
    assert(!logical_publish_attempts&&!logical_status_bytes&&!mic);
    comp_link_connection(&link_owner.link,true,true,f.now);
    logical_publish_failures=1u;comp_link_poll(&link_owner.link,f.now);
    assert(logical_publish_attempts==1u&&!logical_status_bytes&&link_owner.link.meeting_status_dirty);
    comp_link_poll(&link_owner.link,f.now);
    assert(logical_publish_attempts==2u&&logical_status_bytes==64u&&!link_owner.link.meeting_status_dirty);
    assert(logical_status[0]==1u&&!logical_status[1]&&!logical_status[2]&&
        !memcmp(logical_status+32u,device_uid,12u)&&comp_rec_get64(logical_status+44u)==7u&&
        !comp_rec_get64(logical_status+52u)&&!link_owner.record_calls&&!mic);
    for(unsigned i=0u;i<COMPANION_GATT_CHAR_COUNT;i++)assert(!link_owner.link.subscribed[i]);
    comp_link_connection(&link_owner.link,true,true,f.now);comp_link_poll(&link_owner.link,f.now);
    assert(logical_publish_attempts==2u); /* unchanged link does not flood status */
    comp_link_connection(&link_owner.link,false,false,f.now);
    link_owner.features.meeting.state=2u; /* snapshot sealed while disconnected */
    comp_link_connection(&link_owner.link,true,false,f.now);comp_link_poll(&link_owner.link,f.now);
    assert(logical_publish_attempts==2u);
    comp_link_connection(&link_owner.link,true,true,f.now);comp_link_poll(&link_owner.link,f.now);
    assert(logical_publish_attempts==3u&&logical_status[1]==2u&&!link_owner.record_calls&&!mic);
    puts("READ_STATUS: first protected connection publishes CRC/identity before CCCD/START; failed publication retries; unencrypted/unchanged link does not publish; reconnect refreshes without capture. Software only");
}
static void logical_command(uint8_t wire[52],uint8_t command,uint32_t request,uint64_t session)
{
    memset(wire,0,52u);memcpy(wire,"CMC2",4u);wire[4]=2u;wire[5]=command;wire[6]=2u;
    memcpy(wire+8u,device_uid,12u);comp_rec_put64(wire+20u,7u);comp_rec_put64(wire+28u,session);
    comp_rec_put32(wire+36u,request);comp_rec_put32(wire+40u,101u);
    comp_rec_put32(wire+48u,comp_rec_crc(wire,48u));
}
static void rejected_control_reply_retries(void)
{
    initial_status_without_subscription();
    uint8_t wire[52];logical_command(wire,1u,404u,0u);
    wire[8]^=1u;comp_rec_put32(wire+48u,comp_rec_crc(wire,48u));
    companion_gatt_meeting_status_v1_t before=link_owner.features.meeting;
    logical_publish_failures=2u;
    send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,52u);
    assert(!memcmp(&before,&link_owner.features.meeting,sizeof(before)) && !mic && !link_owner.record_calls);
    comp_link_poll(&link_owner.link,f.now);
    comp_link_poll(&link_owner.link,f.now);
    assert(comp_rec_get32(logical_status+8u)==404u && logical_status[2]==COMPANION_V1_MEETING_ERROR_REJECTED);
    assert(comp_rec_get32(logical_status+60u)==comp_rec_crc(logical_status,60u));
    /* A reply awaiting controller space belongs only to this encrypted link. */
    logical_command(wire,1u,405u,0u);wire[8]^=1u;comp_rec_put32(wire+48u,comp_rec_crc(wire,48u));
    logical_publish_failures=1u;send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,52u);
    comp_link_connection(&link_owner.link,false,false,f.now);
    comp_link_connection(&link_owner.link,true,true,f.now);comp_link_poll(&link_owner.link,f.now);
    assert(comp_rec_get32(logical_status+8u)!=405u && !logical_status[2] && !mic && !link_owner.record_calls);
    puts("REJECT_REPLY: failed controller admission retries the exact command error without altering capture; disconnect drops the old reply. Software only");
}

static void logical_control_across_segments(void)
{
    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    memset(&link_owner,0,sizeof(link_owner));memset(logical_status,0,sizeof(logical_status));
    comp_link_config_t cfg={&link_owner.runtime,NULL,NULL,&link_owner.features,logical_publish,NULL};
    assert(comp_link_init_segmented(&link_owner.link,&cfg,&radio,&product_rec.pipeline,248u));
    comp_link_connection(&link_owner.link,true,true,f.now);subscribe(COMPANION_GATT_CHAR_MEETING_STATUS,true);
    companion_gatt_meeting_control_v1_t old={0};old.schema_version=1u;old.command=1u;old.profile_id=2u;old.request_id=101u;
    send(COMPANION_GATT_CHAR_MEETING_CONTROL,(const uint8_t *)&old,sizeof(old));
    assert(!link_owner.record_calls); /* the product cannot silently accept old unscoped controls */
    uint8_t wire[52];logical_command(wire,1u,101u,0u);
    send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,52u);assert(link_owner.record_calls==1u);
    product_ready_capture(0x100000002ull,link_owner.runtime.record_token);
    link_owner.runtime.command_pending=false;link_owner.runtime.prepare_pending=false;link_owner.runtime.capture_active=true;
    comp_link_poll(&link_owner.link,f.now);
    assert(mic&&!product_rec.capture.engine.stats.accepted_pcm_blocks&&logical_status[1]==0u);
    int16_t first_samples[160];pcm(0u,first_samples);
    assert(comp_wba_recording_product_pcm(&product_rec,first_samples,160u,16000u));
    for(unsigned i=0u;i<100u;i++)product_tick();
    comp_link_poll(&link_owner.link,f.now);uint32_t anchor=comp_rec_get32(logical_status+12u);
    assert(logical_status[1]==1u&&anchor&&comp_rec_get64(logical_status+52u)==0x100000002ull);
    for(unsigned block=1u;block<70u;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
        for(unsigned i=0u;i<100u;i++)product_tick();
    }
    assert(product_rec.capture.engine.active.descriptor.recording_id!=anchor);
    comp_link_poll(&link_owner.link,f.now);
    assert(comp_rec_get32(logical_status+12u)==anchor&&comp_rec_get64(logical_status+52u)==0x100000002ull);
    logical_command(wire,1u,101u,0u);send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,52u);
    assert(link_owner.record_calls==1u&&mic); /* lost START reply cannot start another mic */
    for(unsigned changed=0u;changed<4u;changed++) {
        logical_command(wire,2u,202u,0x100000002ull);
        wire[changed==0u?8u:changed==1u?20u:changed==2u?28u:40u]^=1u;
        comp_rec_put32(wire+48u,comp_rec_crc(wire,48u));
        send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,52u);
        assert(link_owner.record_calls==1u&&mic&&logical_status[2]==COMPANION_V1_MEETING_ERROR_REJECTED);
    }
    logical_command(wire,2u,202u,0x100000002ull);send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,52u);
    assert(link_owner.record_calls==2u&&link_owner.runtime.stop_pending);
    assert(comp_wba_recording_product_control(&product_rec,false,link_owner.runtime.record_token));
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)product_tick();
    assert(!mic&&product_rec.pipeline.state==COMP_PIPE_FINISHED);
    link_owner.runtime.capture_active=false;comp_link_poll(&link_owner.link,f.now);
    assert(logical_status[1]==2u&&!logical_status[2]&&comp_rec_get32(logical_status+12u)==anchor&&
        comp_rec_get64(logical_status+52u)==0x100000002ull);
    puts("PASS WBA logical recorder: real Opus segment cut retains START anchor/session; UID/epoch/session/start mismatch cannot STOP; matching STOP seals the same session; software only");
}
static uint64_t pause_session;
static bool pause_record_hook(comp_runtime_t *runtime,bool start)
{
    if(!start)return comp_wba_recording_product_control(&product_rec,false,runtime->record_token);
    assert(comp_link_recording_timeline_requested(&link_owner.link,runtime->record_token));
    return comp_wba_recording_product_prepare_timeline(&product_rec,pause_session,1u,0u,runtime->record_token,true);
}
static void pause_command(uint8_t wire[56],uint8_t command,uint32_t request,uint32_t sequence,uint64_t session)
{
    uint8_t old[52];logical_command(old,command,request,session);memset(wire,0,56u);memcpy(wire,old,48u);
    memcpy(wire,"CMC3",4u);wire[4]=3u;wire[7]=command==1u?1u:0u;
    if(command==1u)comp_rec_put16(wire+44u,600u);
    comp_rec_put32(wire+48u,sequence);comp_rec_put32(wire+52u,comp_rec_crc(wire,52u));
}
static void pause_control_tick(void)
{
    product_tick();link_owner.runtime.capture_active=mic;
    comp_link_poll(&link_owner.link,f.now);
}
static void pause_control_export(FILE *out,const uint8_t wire[56],bool confirmed,uint32_t *count)
{
    assert(logical_status_bytes==80u&&comp_rec_get32(logical_status+76u)==comp_rec_crc(logical_status,76u));
    uint8_t flag=confirmed?1u:0u;
    assert(fwrite(wire,1u,56u,out)==56u&&fwrite(logical_status,1u,80u,out)==80u&&fwrite(&flag,1u,1u,out)==1u);
    (*count)++;
}
static void pause_controls(const char *path)
{
    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    memset(&link_owner,0,sizeof(link_owner));memset(logical_status,0,sizeof(logical_status));logical_status_bytes=0u;
    comp_link_config_t cfg={&link_owner.runtime,NULL,NULL,&link_owner.features,logical_publish,NULL};
    assert(comp_link_init_segmented(&link_owner.link,&cfg,&radio,&product_rec.pipeline,136u));
    comp_link_connection(&link_owner.link,true,true,f.now);subscribe(COMPANION_GATT_CHAR_MEETING_STATUS,true);
    comp_link_test_record_hook=pause_record_hook;pause_session=0x100000002ull;
    FILE *out=fopen(path,"wb");assert(out);uint8_t header[8]={'C','P','C','3',0u,0u,0u,0u};
    assert(fwrite(header,1u,8u,out)==8u);uint32_t count=0u;uint8_t wire[56];
    pause_command(wire,1u,101u,0u,0u);send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,56u);
    assert(link_owner.record_calls==1u&&!link_owner.link.timeline_prepare&&product_rec.pipeline.pause_timeline);
    assert(comp_link_recording_timeline_requested(&link_owner.link,link_owner.runtime.record_token)); /*local default restored*/
    for(unsigned i=0u;i<10000u&&!comp_wba_recording_product_ready(&product_rec,link_owner.runtime.record_token);i++)product_tick();
    assert(comp_wba_recording_product_control(&product_rec,true,link_owner.runtime.record_token));
    link_owner.runtime.prepare_pending=link_owner.runtime.command_pending=false;pause_control_tick();
    assert(mic&&!product_rec.capture.engine.stats.accepted_pcm_blocks&&logical_status[1]==0u);
    int16_t first_samples[160];pcm(0u,first_samples);
    assert(comp_wba_recording_product_pcm(&product_rec,first_samples,160u,16000u));
    for(unsigned i=0u;i<100u;i++)product_tick();
    pause_control_tick();
    assert(logical_status[1]==1u&&logical_status[64]==1u&&link_owner.link.remote_limit_ms==600000u);
    uint32_t anchor=comp_rec_get32(logical_status+12u);assert(anchor);pause_control_export(out,wire,true,&count);
    for(unsigned block=1u;block<8u;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
        for(unsigned i=0u;i<100u;i++)product_tick();
    }
    pause_command(wire,4u,110u,1u,pause_session);send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,56u);pause_control_tick();
    assert(logical_status[1]==4u&&!mic);pause_control_export(out,wire,false,&count);
    for(unsigned i=0u;i<10000u&&product_rec.capture.engine.state!=COMP_CONT_PAUSED;i++)pause_control_tick();
    assert(logical_status[1]==3u&&comp_rec_get32(logical_status+60u)==1u&&link_owner.link.remote_limit_ms==600000u);
    pause_control_export(out,wire,true,&count);unsigned stops=mic_stops;
    send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,56u);assert(mic_stops==stops&&!mic);
    pause_control_export(out,wire,true,&count);
    for(unsigned changed=0u;changed<4u;changed++) {
        pause_command(wire,5u,120u,2u,pause_session);wire[changed==0u?8u:changed==1u?20u:changed==2u?28u:40u]^=1u;
        comp_rec_put32(wire+52u,comp_rec_crc(wire,52u));send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,56u);
        assert(!mic&&logical_status[2]==COMPANION_V1_MEETING_ERROR_REJECTED&&link_owner.link.meeting_control_sequence==1u);
    }
    pause_command(wire,5u,120u,2u,pause_session);send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,56u);pause_control_tick();
    assert(logical_status[1]==5u&&mic);pause_control_export(out,wire,false,&count);
    for(unsigned i=0u;i<10000u&&product_rec.capture.engine.state!=COMP_CONT_RUNNING;i++)pause_control_tick();
    assert(logical_status[1]==1u&&comp_rec_get32(logical_status+60u)==2u&&comp_rec_get32(logical_status+12u)==anchor);
    pause_control_export(out,wire,true,&count);
    pause_command(wire,4u,110u,1u,pause_session);send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,56u);
    assert(mic&&link_owner.link.meeting_control_sequence==2u&&logical_status[2]==COMPANION_V1_MEETING_ERROR_REJECTED);
    pause_control_export(out,wire,false,&count);
    pause_command(wire,4u,130u,3u,pause_session);send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,56u);
    assert(!mic&&product_rec.capture.engine.state==COMP_CONT_PAUSING);
    unsigned starts=mic_starts;pause_command(wire,2u,140u,4u,pause_session);send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,56u);
    assert(product_rec.pipeline.stop_requested&&link_owner.runtime.stop_pending);pause_control_tick();
    assert(logical_status[1]==6u);pause_control_export(out,wire,false,&count);
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)pause_control_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED&&!mic&&mic_starts==starts&&logical_status[1]==2u);
    assert(comp_rec_get32(logical_status+60u)==4u&&comp_rec_get32(logical_status+12u)==anchor&&
        comp_rec_get64(logical_status+52u)==pause_session);pause_control_export(out,wire,true,&count);
    send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,56u);assert(mic_starts==starts&&!mic);
    /* A second logical recording stops while RESUME is still committing its
     * source event. Accepted real PCM must drain, without a second mic start. */
    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    memset(&link_owner,0,sizeof(link_owner));logical_status_bytes=0u;
    assert(comp_link_init_segmented(&link_owner.link,&cfg,&radio,&product_rec.pipeline,136u));
    comp_link_connection(&link_owner.link,true,true,f.now);subscribe(COMPANION_GATT_CHAR_MEETING_STATUS,true);
    pause_session=0x100000003ull;
    pause_command(wire,1u,101u,0u,0u);send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,56u);
    for(unsigned i=0u;i<10000u&&!comp_wba_recording_product_ready(&product_rec,link_owner.runtime.record_token);i++)product_tick();
    assert(comp_wba_recording_product_control(&product_rec,true,link_owner.runtime.record_token));
    link_owner.runtime.prepare_pending=link_owner.runtime.command_pending=false;pause_control_tick();
    assert(mic&&!product_rec.capture.engine.stats.accepted_pcm_blocks&&logical_status[1]==0u);
    pcm(0u,first_samples);
    assert(comp_wba_recording_product_pcm(&product_rec,first_samples,160u,16000u));
    for(unsigned i=0u;i<100u;i++)product_tick();
    pause_control_tick();
    pause_control_export(out,wire,true,&count);anchor=comp_rec_get32(logical_status+12u);
    for(unsigned block=1u;block<4u;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
        for(unsigned i=0u;i<100u;i++)product_tick();
    }
    pause_command(wire,4u,110u,1u,pause_session);send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,56u);
    for(unsigned i=0u;i<10000u&&product_rec.capture.engine.state!=COMP_CONT_PAUSED;i++)pause_control_tick();
    assert(logical_status[1]==3u);pause_control_export(out,wire,true,&count);
    pause_command(wire,5u,120u,2u,pause_session);send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,56u);
    pause_control_tick();assert(mic&&product_rec.capture.engine.state==COMP_CONT_RESUMING);
    pause_control_export(out,wire,false,&count);starts=mic_starts;
    for(unsigned block=4u;block<6u;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
    }
    pause_command(wire,2u,140u,3u,pause_session);send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,56u);
    assert(product_rec.pipeline.stop_requested);pause_control_tick();
    assert(logical_status[1]==6u);pause_control_export(out,wire,false,&count);
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)pause_control_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED&&!mic&&mic_starts==starts&&logical_status[1]==2u);
    assert(product_rec.capture.engine.stats.accepted_pcm_blocks==6u&&comp_rec_get32(logical_status+20u)==60u&&
        comp_rec_get32(logical_status+12u)==anchor);pause_control_export(out,wire,true,&count);
    uint8_t n[4];comp_rec_put32(n,count);assert(fseek(out,4,SEEK_SET)==0&&fwrite(n,1u,4u,out)==4u&&fclose(out)==0);
    comp_link_test_record_hook=NULL;
    puts("PAUSE_CONTROL: protected CMC3 START selects schema only during actual prepare; CMS3 exact key/sequence and real transitions; duplicate/stale/scope guards; queued STOP during PAUSING and RESUMING seals accepted PCM without MIC restart; captured-duration limit survives pause. Real Opus SOFTWARE ONLY, runtime shim/no board/UI proof");
}
static void local_controls(const char *path)
{
    FILE *out=fopen(path,"wb");assert(out);uint8_t header[8]={'C','L','L','3',16u,0u,0u,0u};
    assert(fwrite(header,1u,8u,out)==8u);
    for(unsigned local=0u;local<2u;++local) {
        product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
        memset(&link_owner,0,sizeof(link_owner));memset(logical_status,0,sizeof(logical_status));logical_status_bytes=0u;
        comp_link_config_t cfg={&link_owner.runtime,NULL,NULL,&link_owner.features,logical_publish,NULL};
        assert(comp_link_init_segmented(&link_owner.link,&cfg,&radio,&product_rec.pipeline,136u));
        comp_link_connection(&link_owner.link,true,true,f.now);subscribe(COMPANION_GATT_CHAR_MEETING_STATUS,true);
        comp_link_test_record_hook=pause_record_hook;pause_session=0x100000010ull+local;
        uint8_t wire[56];pause_command(wire,1u,101u,0u,0u);
        if(local)assert(comp_runtime_record(&link_owner.runtime,true,f.now)==COMP_RUNTIME_OK);
        else send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,56u);
        uint32_t token=link_owner.runtime.record_token;
        for(unsigned i=0u;i<10000u&&!comp_wba_recording_product_ready(&product_rec,token);i++)product_tick();
        assert(comp_wba_recording_product_control(&product_rec,true,token));
        link_owner.runtime.prepare_pending=link_owner.runtime.command_pending=false;pause_control_tick();
        assert(mic&&!product_rec.capture.engine.stats.accepted_pcm_blocks&&logical_status[1]==0u);
        int16_t first_samples[160];pcm(0u,first_samples);
        assert(comp_wba_recording_product_pcm(&product_rec,first_samples,160u,16000u));
        for(unsigned i=0u;i<100u;i++)product_tick();
        pause_control_tick();
        assert(logical_status_bytes==80u&&logical_status[1]==1u&&logical_status[66]==local);
        uint32_t start=link_owner.link.meeting_start_request_id,anchor=comp_rec_get32(logical_status+12u);
        assert(start==(local?token:101u)&&anchor);
        assert(fwrite(logical_status,1u,80u,out)==80u);
        for(unsigned block=1u;block<8u;block++) {
            int16_t samples[160];pcm(block,samples);assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
            for(unsigned i=0u;i<100u;i++)product_tick();
        }
        assert(!comp_wba_recording_product_pause_resume(&product_rec,token+1u));
        assert(comp_wba_recording_product_pause_resume(&product_rec,token));
        assert(!comp_wba_recording_product_pause_resume(&product_rec,token)); /*in flight*/
        comp_link_poll(&link_owner.link,f.now);
        assert(logical_status[1]==4u&&logical_status[65]==4u&&logical_status[66]==1u&&
            comp_rec_get32(logical_status+67u)==start&&comp_rec_get32(logical_status+60u)==1u);
        assert(fwrite(logical_status,1u,80u,out)==80u);
        for(unsigned i=0u;i<10000u&&product_rec.capture.engine.state!=COMP_CONT_PAUSED;i++)pause_control_tick();
        assert(logical_status[1]==3u&&!mic);
        assert(comp_wba_recording_product_set_paused(&product_rec,token,true)&&
            product_rec.capture.engine.command_sequence==1u); /*wired retry does not resume*/
        assert(fwrite(logical_status,1u,80u,out)==80u);
        assert(comp_wba_recording_product_pause_resume(&product_rec,token));
        assert(!comp_wba_recording_product_pause_resume(&product_rec,token));
        comp_link_poll(&link_owner.link,f.now);assert(logical_status[1]==5u&&logical_status[65]==5u);
        assert(fwrite(logical_status,1u,80u,out)==80u);
        for(unsigned i=0u;i<10000u&&product_rec.capture.engine.state!=COMP_CONT_RUNNING;i++)pause_control_tick();
        assert(logical_status[1]==1u&&mic&&comp_rec_get32(logical_status+60u)==2u);
        assert(fwrite(logical_status,1u,80u,out)==80u);
        pause_command(wire,4u,130u,3u,pause_session);comp_rec_put32(wire+40u,start);
        comp_rec_put32(wire+52u,comp_rec_crc(wire,52u));send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,56u);
        for(unsigned i=0u;i<10000u&&product_rec.capture.engine.state!=COMP_CONT_PAUSED;i++)pause_control_tick();
        assert(logical_status[1]==3u&&logical_status[66]==0u&&logical_status[65]==4u&&
            comp_rec_get32(logical_status+60u)==3u);assert(fwrite(logical_status,1u,80u,out)==80u);
        assert(comp_wba_recording_product_pause_resume(&product_rec,token));
        for(unsigned i=0u;i<10000u&&product_rec.capture.engine.state!=COMP_CONT_RUNNING;i++)pause_control_tick();
        assert(logical_status[1]==1u&&logical_status[66]==1u&&comp_rec_get32(logical_status+60u)==4u);
        assert(fwrite(logical_status,1u,80u,out)==80u);
        assert(comp_runtime_record(&link_owner.runtime,false,f.now)==COMP_RUNTIME_OK);
        assert(!comp_wba_recording_product_pause_resume(&product_rec,token));
        for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)pause_control_tick();
        assert(!mic&&logical_status[1]==2u&&logical_status[65]==5u&&logical_status[66]==1u&&
            comp_rec_get32(logical_status+12u)==anchor&&comp_rec_get64(logical_status+52u)==pause_session);
        assert(fwrite(logical_status,1u,80u,out)==80u);
    }
    assert(fclose(out)==0);comp_link_test_record_hook=NULL;
    puts("LOCAL_CONTROL: actual product engine short-press API and real Opus; local/remote START, local PAUSE/RESUME, remote PAUSE, local RESUME and physical STOP retain same original/anchor/sequence; CRC origin never remote ACK. SOFTWARE ONLY/no physical button proof");
}

static void workspace_restart_same_catalogue(void)
{
    product_fresh();product_mount();uint32_t physical=0u;
    assert(comp_wba_recording_product_workspace(&product_rec,12288u,&physical));
    comp_wba_recording_product_lease_result(&product_rec,true);product_refresh_space();
    uint32_t generation=product_rec.catalog.generation;
    unsigned reads=f.reads,writes=f.writes;
    assert(comp_wba_recording_product_workspace(&product_rec,0u,&physical));
    assert(!comp_wba_recording_product_space_current(&product_rec));
    assert(comp_wba_recording_product_catalog_current(&product_rec));
    /* The capacity denominator changed, but the complete extent inventory
     * still describes this exact catalogue generation. A fresh download must
     * not require an unrelated foreground capacity walk between two calls. */
    assert(comp_wba_recording_product_workspace(&product_rec,16384u,&physical));
    assert(physical==DATA_BASE+49152u);
    assert(comp_wba_recording_product_workspace(&product_rec,0u,&physical));
    product_rec.catalog.generation++;
    assert(!comp_wba_recording_product_catalog_current(&product_rec));
    assert(!comp_wba_recording_product_workspace(&product_rec,4096u,&physical));
    product_rec.catalog.generation=generation;
    assert(comp_wba_recording_product_workspace(&product_rec,12288u,&physical));
    assert(comp_wba_recording_product_workspace(&product_rec,0u,&physical));
    assert(f.reads==reads&&f.writes==writes&&!mic);
    product_refresh_space();assert(product_rec.space.arena_bytes==65536u);
    puts("WORKSPACE_RESTART: release/reclaim with unchanged complete catalogue needs no NOR I/O; changed catalogue generation still refuses; capture remains off. SOFTWARE ONLY");
}
static void terminal_cause_status(const char *path)
{
    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    memset(&link_owner,0,sizeof(link_owner));memset(logical_status,0,sizeof(logical_status));logical_status_bytes=0u;
    comp_link_config_t cfg={&link_owner.runtime,NULL,NULL,&link_owner.features,logical_publish,NULL};
    assert(comp_link_init_segmented(&link_owner.link,&cfg,&radio,&product_rec.pipeline,136u));
    comp_link_connection(&link_owner.link,true,true,f.now);subscribe(COMPANION_GATT_CHAR_MEETING_STATUS,true);
    comp_link_test_record_hook=pause_record_hook;pause_session=0x100000002ull;
    uint8_t wire[56];pause_command(wire,1u,101u,0u,0u);
    send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,56u);
    for(unsigned i=0u;i<10000u&&!comp_wba_recording_product_ready(&product_rec,link_owner.runtime.record_token);i++)product_tick();
    assert(comp_wba_recording_product_control(&product_rec,true,link_owner.runtime.record_token));
    link_owner.runtime.prepare_pending=link_owner.runtime.command_pending=false;pause_control_tick();
    assert(logical_status[1]==1u&&!logical_status[71]);
    for(unsigned block=0u;block<8u;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));
        for(unsigned i=0u;i<100u;i++)product_tick();
    }
    link_owner.runtime.record_stop_reason=COMP_RECORD_STOP_LOW_BATTERY;
    assert(comp_wba_recording_product_stop_reason(&product_rec,link_owner.runtime.record_token,COMP_CONT_STOP_LOW_BATTERY));
    pause_control_tick();assert(logical_status[1]==6u);
    /* A late ordinary STOP may not overwrite the core's accepted power cause. */
    assert(comp_wba_recording_product_control(&product_rec,false,link_owner.runtime.record_token));
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)pause_control_tick();
    assert(!mic&&product_rec.pipeline.state==COMP_PIPE_FINISHED&&logical_status[1]==2u);
    assert(logical_status_bytes==80u&&logical_status[71]==COMP_REC_END_LOW_BATTERY);
    assert(logical_status[65]==1u&&!logical_status[66]&&!comp_rec_get32(logical_status+60u));
    comp_segment_entry_t e=product_entry(0u);
    assert((e.descriptor.flags&COMP_REC_V2_END_MASK)==((uint32_t)COMP_REC_END_LOW_BATTERY<<COMP_REC_V2_END_SHIFT));
    FILE *out=fopen(path,"wb");assert(out&&fwrite(logical_status,1u,80u,out)==80u);
    /* A prepared writer with no samples is cancellation, not a saved file. */
    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    memset(&link_owner,0,sizeof(link_owner));logical_status_bytes=0u;
    assert(comp_link_init_segmented(&link_owner.link,&cfg,&radio,&product_rec.pipeline,136u));
    comp_link_connection(&link_owner.link,true,true,f.now);subscribe(COMPANION_GATT_CHAR_MEETING_STATUS,true);
    pause_session=0x100000003ull;pause_command(wire,1u,101u,0u,0u);
    send(COMPANION_GATT_CHAR_MEETING_CONTROL,wire,56u);
    for(unsigned i=0u;i<10000u&&!comp_wba_recording_product_ready(&product_rec,link_owner.runtime.record_token);i++)product_tick();
    link_owner.runtime.record_stop_reason=COMP_RECORD_STOP_POWER_UNKNOWN;
    assert(comp_wba_recording_product_control(&product_rec,false,link_owner.runtime.record_token));
    link_owner.runtime.prepare_pending=link_owner.runtime.command_pending=false;
    for(unsigned i=0u;i<20000u&&product_rec.pipeline.state!=COMP_PIPE_FINISHED;i++)pause_control_tick();
    assert(!mic&&!mic_starts&&product_rec.capture.engine.state==COMP_CONT_CANCELED);
    assert(logical_status[1]==0u&&logical_status[2]==COMPANION_V1_MEETING_ERROR_POWER_UNKNOWN);
    assert(!comp_rec_get32(logical_status+12u)&&!comp_rec_get64(logical_status+52u)&&!logical_status[71]);
    assert(fwrite(logical_status,1u,80u,out)==80u&&fclose(out)==0);
    comp_link_test_record_hook=NULL;
    puts("TERMINAL_CAUSE: production CMS3 and LAST descriptor retain core low-battery cause; no synthetic STOP ACK; zero-PCM cancellation is idle/power-unknown with no original. Real Opus SOFTWARE ONLY/runtime shim/no board proof");
}
static void readonly_blank_warming(void)
{
    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    product_refresh_space();nor.info.jedec_id=UINT32_C(0xef6018);
    /* A dirty original candidate is refused without choosing a different slot,
     * an erase or directory claim: preserve the allocation/wear rotation. */
    f.bytes[DATA_BASE]=0u;unsigned writes=f.writes,erases=f.erases;
    uint32_t generation=product_rec.catalog.generation;
    uint32_t capacity=product_rec.space.largest_gap;
    for(unsigned i=0u;i<1000u && nor.blank_cache.flags!=COMP_NOR_BLANK_KNOWN;++i)
        comp_wba_recording_product_warm_blank(&product_rec,true);
    assert(!nor.blank_cache.flags && product_rec.blank_warm.phase==2u);
    assert(f.writes==writes && f.erases==erases && !mic && !mic_starts &&
        product_rec.catalog.generation==generation && product_rec.space.largest_gap==capacity);
    comp_wba_recording_product_warm_blank(&product_rec,false);
    assert(companion_spi_nor_stm32wba_erase_4k(&nor,DATA_BASE)==COMPANION_SPI_NOR_STM32WBA_OK);
    erases=f.erases;writes=f.writes;
    for(unsigned i=0u;i<1000u && nor.blank_cache.flags!=COMP_NOR_BLANK_KNOWN;++i)
        comp_wba_recording_product_warm_blank(&product_rec,true);
    assert(companion_nor_blank_known(&nor.blank_cache,DATA_BASE,4096u));
    assert(f.writes==writes && f.erases==erases);
    assert(comp_wba_recording_product_prepare(&product_rec,710u,1u,0u,710u));
    for(unsigned i=0u;i<20000u && !comp_wba_recording_product_ready(&product_rec,710u);++i)product_tick();
    assert(comp_wba_recording_product_ready(&product_rec,710u));
    assert(product_rec.pipeline.future.extent_offset==0u);
    assert(f.erases==erases && !mic && !mic_starts);
    assert(nor.blank_cache.flags==0u); /* CSP2 program revoked the old proof. */
    assert(product_rec.capture.engine.encoder_owned);
    assert(comp_wba_recording_product_control(&product_rec,false,710u));
    for(unsigned i=0u;i<20000u && product_rec.pipeline.state!=COMP_PIPE_FINISHED;++i)product_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED && !product_rec.capture.engine.encoder_owned);

    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    product_refresh_space();nor.info.jedec_id=UINT32_C(0xef6018);
    for(unsigned i=0u;i<1000u && nor.blank_cache.flags!=COMP_NOR_BLANK_KNOWN;++i)
        comp_wba_recording_product_warm_blank(&product_rec,true);
    assert(nor.blank_cache.flags==COMP_NOR_BLANK_KNOWN);
    /* A later free-space user changes every candidate. The real driver must
     * revoke its overlapping proof and the normal allocator must really erase. */
    uint8_t zero=0u;
    for(uint32_t offset=0u;offset<65536u;offset+=4096u)
        assert(companion_spi_nor_stm32wba_program(&nor,DATA_BASE+offset,&zero,1u)==COMPANION_SPI_NOR_STM32WBA_OK);
    assert(!nor.blank_cache.flags);erases=f.erases;
    assert(comp_wba_recording_product_prepare(&product_rec,711u,1u,0u,711u));
    for(unsigned i=0u;i<20000u && !comp_wba_recording_product_ready(&product_rec,711u);++i)product_tick();
    printf("WARM_FALLBACK_DIAGNOSTIC state=%u phase=%u failure=%u ready=%u erasedBefore=%u erasedAfter=%u mic=%u poisoned=%u\n",(unsigned)product_rec.pipeline.state,(unsigned)product_rec.pipeline.reserve.phase,(unsigned)product_rec.pipeline.failure,(unsigned)comp_wba_recording_product_ready(&product_rec,711u),erases,f.erases,(unsigned)mic,(unsigned)product_rec.storage.poisoned);
    assert(comp_wba_recording_product_ready(&product_rec,711u) && f.erases>erases && !mic);
    assert(comp_wba_recording_product_control(&product_rec,false,711u));
    for(unsigned i=0u;i<20000u && product_rec.pipeline.state!=COMP_PIPE_FINISHED;++i)product_tick();
    assert(product_rec.pipeline.state==COMP_PIPE_FINISHED && !product_rec.capture.engine.encoder_owned);

    product_fresh();product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    product_refresh_space();nor.info.jedec_id=UINT32_C(0xef6018);
    assert(companion_nor_blank_begin(&nor.blank_cache,nor.info.size_bytes,DATA_BASE,4096u));
    comp_wba_recording_product_warm_blank(&product_rec,false);
    assert(!nor.blank_cache.flags && !mic && !mic_starts);
    assert(companion_nor_blank_begin(&nor.blank_cache,nor.info.size_bytes,DATA_BASE,4096u));
    bool valid_before=product_rec.space.valid;
    product_rec.space.valid=false;writes=f.writes;unsigned reads=f.reads;
    comp_wba_recording_product_warm_blank(&product_rec,true);
    assert(!nor.blank_cache.flags && f.writes==writes && f.reads==reads);
    product_rec.space.valid=valid_before; /* End the explicit transient-loss injection. */
    product_refresh_space();
    for(unsigned i=0u;i<1000u && nor.blank_cache.flags!=COMP_NOR_BLANK_KNOWN;++i)
        comp_wba_recording_product_warm_blank(&product_rec,true);
    assert(nor.blank_cache.flags==COMP_NOR_BLANK_KNOWN);
    uint32_t protected_offset=nor.blank_cache.base-DATA_BASE;
    comp_segment_entry_t owner={0};owner.state=COMP_SEG_WRITING;
    owner.extent_offset=protected_offset;owner.reserved_bytes=4096u;
    owner.descriptor.recording_id=product_rec.catalog.next_id;
    owner.descriptor.format_epoch=7u;owner.descriptor.session_id=8000u;
    owner.descriptor.codec=3u;owner.descriptor.source_mode=1u;
    memcpy(owner.descriptor.device_uid,device_uid,12u);
    comp_segment_result_t result=comp_segment_catalog_put_begin(&product_rec.catalog,&owner);
    for(unsigned i=0u;i<10000u && result==COMP_SEG_PENDING;++i)
        result=comp_wba_segment_storage_catalog_poll(&product_rec.storage,&product_rec.catalog);
    assert(result==COMP_SEG_OK);
    assert(companion_nor_blank_known(&nor.blank_cache,DATA_BASE+protected_offset,4096u));
    product_refresh_space();
    bool admitted=comp_wba_recording_product_prepare(&product_rec,712u,1u,0u,712u);
    if(admitted) {
        for(unsigned i=0u;i<20000u && !comp_wba_recording_product_ready(&product_rec,712u);++i)product_tick();
        assert(comp_wba_recording_product_ready(&product_rec,712u));
        assert(product_rec.pipeline.future.extent_offset!=protected_offset);
        assert(comp_wba_recording_product_control(&product_rec,false,712u));
        for(unsigned i=0u;i<20000u && product_rec.pipeline.state!=COMP_PIPE_FINISHED;++i)product_tick();
        assert(!product_rec.capture.engine.encoder_owned);
    }
    comp_segment_entry_t retained=product_entry(0u);
    assert(retained.state==COMP_SEG_WRITING && retained.extent_offset==protected_offset &&
        retained.descriptor.recording_id==owner.descriptor.recording_id &&
        retained.descriptor.session_id==owner.descriptor.session_id);
    puts("PASS_READONLY_IDLE_WARM real_driver=1 no_erase_or_owner_change=1 same_capacity=1 cached_first_owner=1 program_revokes=1 fallback_physically_erases=1 control_cancels=1");
    puts("PASS_READONLY_IDLE_WARM_OWNERSHIP stale_capacity_cancels=1 physical_FF_proof_never_grants_foreign_owner=1");
}
#ifndef COMP_PRODUCT_TEST_MAIN
#define COMP_PRODUCT_TEST_MAIN main
#endif
int COMP_PRODUCT_TEST_MAIN(int argc,char **arguments)
{
    setvbuf(stdout,NULL,_IONBF,0);
    if(argc==2&&!strcmp(arguments[1],"selected-discard"))return product_radio_fixture_main(argc,arguments);
    if(argc==2&&!strcmp(arguments[1],"wide-index"))return pipeline_fixture_main(argc,arguments);
    if(argc==3&&!strcmp(arguments[1],"terminal-cause")){terminal_cause_status(arguments[2]);return 0;}
    if(argc==2&&!strcmp(arguments[1],"workspace-restart")){workspace_restart_same_catalogue();return 0;}
    if(argc==2&&!strcmp(arguments[1],"initial-status")){initial_status_without_subscription();rejected_control_reply_retries();return 0;}
    if(argc==3&&!strcmp(arguments[1],"local-control")){local_controls(arguments[2]);return 0;}
    if(argc==3&&!strcmp(arguments[1],"pause-control")){pause_controls(arguments[2]);return 0;}
    if(argc==2&&!strcmp(arguments[1],"logical-control")){logical_control_across_segments();return 0;}
    boot_and_ota_gate();readonly_blank_warming();refuse_old_owner();actual_pcm_and_logical_count();cancel_and_capture_fault();
    /* Union and negotiation changes affect the shared radio/V1 dispatcher. */
    char *argv[]={"radio",NULL};assert(product_radio_fixture_main(1,argv)==0);
    printf("product_capture_owner=%zu; hardware/Type continuous follower/OTA speed/10ms qualification NOT_MEASURED\n",sizeof(product_rec));
    return 0;
}
