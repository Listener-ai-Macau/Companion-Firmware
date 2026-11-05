#include "wba_recording_pipeline.h"
#define main prior_nor_test_main
#include "../../../../tools/fixtures/wba_nor_suspend_test.c"
#undef main

#define DATA_BASE 65536u
#define FRAMES 10u
static const uint8_t device_uid[12]={1u,2u,3u,4u,5u,6u,7u,8u,9u,10u,11u,12u};
static comp_cont_recording_t engine;
static comp_segment_catalog_t catalog;
static comp_wba_segment_storage_t storage;
static comp_wba_recording_pipeline_t pipeline;
static companion_spi_nor_stm32wba_t nor;
static bool mic;
static unsigned mic_starts,mic_stops,fail_mic_stops;
static uint8_t received[4][1024];
static uint32_t received_bytes[4];
static comp_segment_entry_t reading;
static unsigned read_index;
static bool receiving;

static bool microphone(void *v,bool active)
{(void)v;assert(mic!=active);if(!active&&fail_mic_stops){fail_mic_stops--;return false;}mic=active;if(active)mic_starts++;else mic_stops++;return true;}
static void pcm(unsigned block,int16_t out[160])
{for(unsigned i=0u;i<160u;i++)out[i]=(int16_t)((int)((block*160u+i)%73u)*400-14000);}
static void init(void)
{
    reset();nor=make();f.automatic_erase=true;mic=false;mic_starts=mic_stops=fail_mic_stops=0u;receiving=false;
    memset(received,0,sizeof(received));memset(received_bytes,0,sizeof(received_bytes));
    assert(comp_wba_segment_storage_init(&storage,&nor,0u,24576u,DATA_BASE,65536u));
    comp_segment_port_t port=comp_wba_segment_storage_catalog_port(&storage);
    assert(comp_segment_catalog_mount_begin(&catalog,&port,0u,24576u,DATA_BASE,65536u,device_uid,7u)==COMP_SEG_PENDING);
    comp_segment_result_t r=COMP_SEG_PENDING;
    for(unsigned i=0u;i<5000u&&r==COMP_SEG_PENDING;i++){f.now+=2u;r=comp_wba_segment_storage_catalog_poll(&storage,&catalog);}
    assert(r==COMP_SEG_UNFORMATTED&&comp_segment_catalog_format_blank_begin(&catalog)==COMP_SEG_PENDING);
    r=COMP_SEG_PENDING;
    for(unsigned i=0u;i<1000u&&r==COMP_SEG_PENDING;i++){f.now+=2u;r=comp_wba_segment_storage_catalog_poll(&storage,&catalog);}
    assert(r==COMP_SEG_OK);
    comp_wba_pipeline_config_t cfg={&engine,&catalog,&storage,microphone,now,NULL,FRAMES,4096u};
    assert(comp_wba_recording_pipeline_init(&pipeline,&cfg));
}
static void poll(void)
{
    f.now+=2u;
    assert(comp_wba_recording_pipeline_poll(&pipeline)!=COMP_PIPE_FAILED);
    assert(!storage.poisoned);
}
/* Receiver model verifies real stored logical bytes before proving consumption.
 * It is not the Type file/FS receiver and cannot claim its durability. */
static void receive(void)
{
    if(catalog.phase)return;
    comp_segment_result_t consume=comp_wba_recording_pipeline_consume_result(&pipeline);
    if(consume==COMP_SEG_PENDING)return;
    if(!receiving) {
        for(uint8_t i=0u;i<64u;i++)if(catalog.visible_mask&(UINT64_C(1)<<i)) {
            comp_segment_entry_t entry;comp_segment_result_t r=comp_wba_segment_storage_entry(&storage,&catalog,i,&entry);
            if(r==COMP_SEG_PENDING)return;
            assert(r==COMP_SEG_OK);
            if(entry.state!=COMP_SEG_UNSYNCED)continue;
            assert(entry.descriptor.segment_index<4u);reading=entry;receiving=true;read_index=0u;
            break;
        }
        return;
    }
    uint8_t page[256],length=0u;unsigned segment=reading.descriptor.segment_index;
    comp_segment_audio_port_t port=comp_wba_segment_storage_audio_port(&storage);
    comp_segment_result_t r=comp_segment_audio_read_page(&port,&reading,DATA_BASE,read_index,page,&length);
    if(r==COMP_SEG_PENDING)return;
    assert(r==COMP_SEG_OK&&received_bytes[segment]+length<=sizeof(received[segment]));
    memcpy(received[segment]+received_bytes[segment],page,length);received_bytes[segment]+=length;read_index++;
    if(received_bytes[segment]!=reading.descriptor.encoded_length)return;
    companion_sha256_t hash;uint8_t digest[32];companion_sha256_init(&hash);
    companion_sha256_update(&hash,received[segment],received_bytes[segment]);companion_sha256_final(&hash,digest);
    assert(!memcmp(digest,reading.descriptor.sha256,32u)&&
        comp_rec_crc(received[segment],received_bytes[segment])==reading.descriptor.content_crc32);
    assert(comp_wba_recording_pipeline_consume(&pipeline,&reading.descriptor)==COMP_SEG_PENDING);
    assert(comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_PENDING);receiving=false;
}
static void ready(uint64_t session)
{
    assert(comp_wba_recording_pipeline_begin(&pipeline,session,1u,0u,91u)==COMP_SEG_PENDING);
    for(unsigned i=0u;i<5000u&&pipeline.state!=COMP_PIPE_READY;i++)poll();
    assert(pipeline.state==COMP_PIPE_READY&&!mic);
}
static void continuous(void)
{
    init();ready(55u);assert(comp_wba_recording_pipeline_start(&pipeline,91u));
    assert(!comp_wba_recording_pipeline_start(&pipeline,91u));
    for(unsigned block=0u;block<80u;block++) {
        int16_t samples[160];pcm(block,samples);
        assert(mic&&comp_cont_recording_pcm(&engine,samples,160u));
        for(unsigned i=0u;i<160u;i++){poll();receive();}
    }
    assert(comp_wba_recording_pipeline_stop(&pipeline,91u)&&!mic);
    for(unsigned i=0u;i<10000u&&(pipeline.state!=COMP_PIPE_FINISHED||pipeline.consumed_segments<4u);i++){poll();receive();}
    assert(pipeline.state==COMP_PIPE_FINISHED&&pipeline.consumed_segments==4u);
    assert(mic_starts==1u&&mic_stops==1u&&engine.stats.overflows==0u&&engine.stats.encoded_packets==40u);
    assert(catalog.visible_mask==0u&&!nor.erase_active&&!comp_wba_recording_pipeline_storage_busy(&pipeline));
    for(unsigned i=0u;i<64u;i++)assert(catalog.slots[i]==255u);
    /* Compare to a single uncut encode using the SAME established codec. */
    companion_opus16_rt_t codec;assert(companion_opus16_rt_init_rate_frame(&codec,16000u,20u));
    unsigned segment=0u;size_t at=12u;
    for(unsigned block=0u;block<80u;block++) {
        int16_t samples[160];uint8_t packet[402];pcm(block,samples);
        size_t bytes=companion_opus16_rt_encode(&codec,samples,160u,packet,sizeof(packet),false);
        if(!bytes)continue;
        while(at==received_bytes[segment]){segment++;at=12u;assert(segment<4u);}
        assert(at+bytes<=received_bytes[segment]&&!memcmp(packet,received[segment]+at,bytes));at+=bytes;
    }
    companion_opus16_rt_destroy(&codec);assert(segment==3u&&at==received_bytes[3]);
    puts("PASS pipeline continuous software integration: one mic/real Opus across4 segments, real NOR command adapter, exact receiver proof before4 physical reclaims, future cleanup; no production Type/board proof");
}
/* Exercise actual catalog, encoder and consume paths across the old index
 * ceiling without requiring a physical board or 1025 resident segments. */
static void receive_wide(unsigned *completed,uint32_t *highest)
{
    if(catalog.phase||comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_PENDING)return;
    if(!receiving) {
        for(uint8_t i=0u;i<64u;i++)if(catalog.visible_mask&(UINT64_C(1)<<i)) {
            comp_segment_entry_t entry;comp_segment_result_t r=comp_wba_segment_storage_entry(&storage,&catalog,i,&entry);
            if(r==COMP_SEG_PENDING)return;
            assert(r==COMP_SEG_OK);if(entry.state!=COMP_SEG_UNSYNCED)continue;
            reading=entry;receiving=true;read_index=0u;received_bytes[0]=0u;break;
        }
        return;
    }
    uint8_t page[256],length=0u;comp_segment_audio_port_t port=comp_wba_segment_storage_audio_port(&storage);
    comp_segment_result_t r=comp_segment_audio_read_page(&port,&reading,DATA_BASE,read_index,page,&length);
    if(r==COMP_SEG_PENDING)return;
    assert(r==COMP_SEG_OK&&received_bytes[0]+length<=sizeof(received[0]));
    memcpy(received[0]+received_bytes[0],page,length);received_bytes[0]+=length;read_index++;
    if(received_bytes[0]!=reading.descriptor.encoded_length)return;
    companion_sha256_t hash;uint8_t digest[32];companion_sha256_init(&hash);
    companion_sha256_update(&hash,received[0],received_bytes[0]);companion_sha256_final(&hash,digest);
    assert(!memcmp(digest,reading.descriptor.sha256,32u)&&comp_rec_crc(received[0],received_bytes[0])==reading.descriptor.content_crc32);
    assert(reading.descriptor.segment_index==*completed);
    *highest=reading.descriptor.segment_index;(*completed)++;
    assert(comp_wba_recording_pipeline_consume(&pipeline,&reading.descriptor)==COMP_SEG_PENDING);receiving=false;
}
static void wide_index_recording(void)
{
    init();ready(55u);assert(comp_wba_recording_pipeline_start(&pipeline,91u));
    unsigned completed=0u;uint32_t highest=0u;
    for(unsigned block=0u;block<20540u;block++) {
        int16_t samples[160];pcm(block,samples);assert(mic&&comp_cont_recording_pcm(&engine,samples,160u));
        for(unsigned i=0u;i<160u;i++){poll();receive_wide(&completed,&highest);}
    }
    assert(comp_wba_recording_pipeline_stop(&pipeline,91u)&&!mic);
    for(unsigned i=0u;i<20000u&&(pipeline.state!=COMP_PIPE_FINISHED||catalog.visible_mask!=0u);i++){
        poll();receive_wide(&completed,&highest);
    }
    assert(pipeline.state==COMP_PIPE_FINISHED&&highest>=1024u&&completed>=1025u);
    assert(engine.stats.overflows==0u&&catalog.visible_mask==0u);
    printf("PASS complete production pipeline with %u verified/consumed synthetic segments, highest index %lu; no real board\n",completed,(unsigned long)highest);
}
static void quick_stop(void)
{
    init();
    const unsigned cuts[]={0u,66u,70u,80u,110u};
    for(unsigned i=0u;i<64u&&catalog.bank_serial<2u;i++) {
        ready(100u+i);
        if(i%2u)assert(comp_wba_recording_pipeline_start(&pipeline,91u));
        /* Preparing a future at READY is legal, and still has to be released. */
        for(unsigned step=0u;step<cuts[i%5u];step++)poll();
        assert(comp_wba_recording_pipeline_stop(&pipeline,91u));
        for(unsigned step=0u;step<10000u&&pipeline.state!=COMP_PIPE_FINISHED;step++)poll();
        assert(pipeline.state==COMP_PIPE_FINISHED&&!mic&&!nor.erase_active&&catalog.visible_mask==0u);
        for(unsigned slot=0u;slot<64u;slot++)assert(catalog.slots[slot]==255u);
    }
    assert(catalog.bank_serial>=2u);
    puts("PASS pipeline quick-stop software integration: prepare/start cancellation finishes in-flight future and releases both empty owners acrossGC; no empty recordings");
}
static void peer_failure_and_workspace(void)
{
    init();ready(55u);assert(comp_wba_recording_pipeline_start(&pipeline,91u));
    comp_rec_v2_descriptor_t bogus=engine.active.descriptor;
    bogus.flags=COMP_REC_V2_SEALED|COMP_REC_V2_LAST;bogus.total_segments=1u;bogus.sample_count=320u;
    bogus.encoded_length=54u;bogus.sha256[0]=1u;bogus.sync_state=1u;
    assert(comp_wba_recording_pipeline_consume(&pipeline,&bogus)==COMP_SEG_PENDING);
    for(unsigned i=0u;i<5000u&&comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_PENDING;i++)poll();
    assert(comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_BAD_ARGUMENT&&mic);
    uint32_t physical=999u;
    assert(comp_wba_recording_pipeline_workspace(&pipeline,4096u,&physical)==COMP_SEG_BAD_STATE&&physical==0u);
    /* Rejecting a peer's fabricated sealed proof cannot delete a growing tail
     * or terminate capture. Then normal zero-data STOP remains usable. */
    assert(engine.state==COMP_CONT_RUNNING&&comp_wba_recording_pipeline_stop(&pipeline,91u));
    for(unsigned i=0u;i<10000u&&pipeline.state!=COMP_PIPE_FINISHED;i++)poll();
    assert(pipeline.state==COMP_PIPE_FINISHED&&!mic);
    comp_segment_result_t r=comp_wba_recording_pipeline_workspace(&pipeline,8192u,&physical);
    while(r==COMP_SEG_PENDING)r=comp_wba_recording_pipeline_workspace(&pipeline,8192u,&physical);
    assert(r==COMP_SEG_OK&&physical==DATA_BASE+65536u-8192u&&comp_wba_recording_pipeline_storage_busy(&pipeline));
    assert(comp_wba_recording_pipeline_begin(&pipeline,56u,1u,0u,92u)==COMP_SEG_BAD_STATE);
    assert(comp_wba_recording_pipeline_workspace(&pipeline,4096u,&physical)==COMP_SEG_BAD_STATE);
    assert(comp_wba_recording_pipeline_workspace(&pipeline,0u,&physical)==COMP_SEG_OK&&!comp_wba_recording_pipeline_storage_busy(&pipeline));
    /* A durable unresolved WRITING extent at the tail protects the same pool
     * from OTA as UNSYNCED/ACKED extents; no old V1-empty-catalog shortcut. */
    comp_segment_entry_t protected_entry={0};protected_entry.state=COMP_SEG_WRITING;
    protected_entry.descriptor.recording_id=catalog.next_id;protected_entry.descriptor.session_id=56u;
    protected_entry.descriptor.format_epoch=7u;protected_entry.descriptor.codec=3u;protected_entry.descriptor.source_mode=1u;
    memcpy(protected_entry.descriptor.device_uid,device_uid,12u);protected_entry.extent_offset=61440u;protected_entry.reserved_bytes=4096u;
    assert(comp_segment_catalog_put_begin(&catalog,&protected_entry)==COMP_SEG_PENDING);
    r=COMP_SEG_PENDING;
    while(r==COMP_SEG_PENDING){f.now+=2u;r=comp_wba_segment_storage_catalog_poll(&storage,&catalog);}
    assert(r==COMP_SEG_OK);
    r=comp_wba_recording_pipeline_workspace(&pipeline,8192u,&physical);
    while(r==COMP_SEG_PENDING)r=comp_wba_recording_pipeline_workspace(&pipeline,8192u,&physical);
    assert(r==COMP_SEG_FULL&&physical==0u&&pipeline.workspace_bytes==0u);
    assert(catalog.slots[0]!=255u&&catalog.mounted&&!storage.poisoned);
    puts("PASS new peer/OTA interlocks: invalid proof cannot stop capture or consume tail; temporary dynamic lease blocks START; unresolved V2 tail cannot be borrowed or silently deleted; software only");
}
static void cancel_preparing(void)
{
    init();const unsigned cuts[]={0u,66u,70u,82u,96u};
    for(unsigned i=0u;i<5u;i++) {
        assert(comp_wba_recording_pipeline_begin(&pipeline,100u+i,1u,0u,91u)==COMP_SEG_PENDING);
        for(unsigned j=0u;j<cuts[i];j++)poll();
        assert(comp_wba_recording_pipeline_stop(&pipeline,91u));
        for(unsigned j=0u;j<10000u&&pipeline.state!=COMP_PIPE_FINISHED;j++)poll();
        assert(pipeline.state==COMP_PIPE_FINISHED&&!mic&&mic_starts==0u&&catalog.visible_mask==0u&&!nor.erase_active);
        for(unsigned j=0u;j<64u;j++)assert(catalog.slots[j]==255u);
    }
    puts("PASS canceled preparation at reservation/commit/erase/blank-readback stages: all ownership released after proof, no microphone start and no empty audio; software only");
}
#ifndef COMP_PIPE_TEST_MAIN
#define COMP_PIPE_TEST_MAIN main
#endif
int COMP_PIPE_TEST_MAIN(int argc,char **argv)
{
    if(argc==2&&!strcmp(argv[1],"wide-index")){wide_index_recording();return 0;}
    if(argc==2&&!strcmp(argv[1],"interlocks")){peer_failure_and_workspace();cancel_preparing();return 0;}
    continuous();quick_stop();
    printf("software pipeline context=%zu engine=%zu; MCU load/RAM/energy NOT_MEASURED\n",sizeof(pipeline),sizeof(engine));return 0;
}
