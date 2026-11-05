#include "../wba_recording_recovery.h"
/* Reuse the real-Opus/production-NOR software fixture, not its old test runs. */
#define COMP_PIPE_TEST_MAIN pipeline_fixture_main
#include "test_wba_recording_pipeline.c"

static comp_wba_recording_recovery_t recovery;
static uint8_t recovery_page[256];
static void reboot(void)
{
    /* Simulator-only destruction of the vanished heap. No producer stop,
     * flush/checkpoint, media reset/format or waveform is injected. */
    if(engine.encoder_owned)companion_opus16_rt_destroy(&engine.codec);
    memset(&engine,0,sizeof(engine));memset(&pipeline,0,sizeof(pipeline));mic=false;
    nor=make();
    assert(comp_wba_segment_storage_init(&storage,&nor,0u,24576u,DATA_BASE,65536u));
    comp_segment_port_t port=comp_wba_segment_storage_catalog_port(&storage);
    assert(comp_segment_catalog_mount_begin(&catalog,&port,0u,24576u,DATA_BASE,65536u,device_uid,7u)==COMP_SEG_PENDING);
    comp_segment_result_t result=COMP_SEG_PENDING;
    for(unsigned i=0u;i<10000u&&result==COMP_SEG_PENDING;i++) {
        f.now+=2u;result=comp_wba_segment_storage_catalog_poll(&storage,&catalog);
    }
    assert(result==COMP_SEG_OK);
    assert(comp_wba_recording_recovery_begin(&recovery,&storage,&catalog,recovery_page)==COMP_SEG_PENDING);
}
static void finish_recovery(void)
{
    comp_segment_result_t result=COMP_SEG_PENDING;
    for(unsigned i=0u;i<20000u&&result==COMP_SEG_PENDING;i++) {
        f.now+=2u;result=comp_wba_recording_recovery_poll(&recovery);
    }
    assert(result==COMP_SEG_OK&&!mic&&!storage.poisoned&&!nor.erase_active);
}
static void partial_capture(void)
{
    init();ready(55u);assert(comp_wba_recording_pipeline_start(&pipeline,91u));
    for(unsigned block=0u;block<18u;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_cont_recording_pcm(&engine,samples,160u));
        for(unsigned i=0u;i<160u;i++)poll();
    }
    assert(engine.writer.committed_bytes==248u&&engine.stats.encoded_packets==9u&&catalog.visible_mask==0u);
}
static comp_segment_entry_t recovered_entry(void)
{
    comp_segment_entry_t entry={0};unsigned found=0u;
    for(uint8_t i=0u;i<64u;i++) {
        comp_segment_result_t result=comp_wba_segment_storage_entry(&storage,&catalog,i,&entry);
        assert(result==COMP_SEG_NOT_FOUND||result==COMP_SEG_OK);
        if(result==COMP_SEG_OK){assert(entry.state==COMP_SEG_UNSYNCED);found++;break;}
    }
    assert(found==1u);return entry;
}
static void interrupted_audio(void)
{
    partial_capture();
    uint8_t expected[222];memcpy(expected,f.bytes+DATA_BASE+256u,sizeof(expected));
    reboot();finish_recovery();
    assert(comp_wba_recording_recovery_ready(&recovery)&&recovery.sealed==1u&&recovery.canceled==1u&&recovery.unresolved==0u);
    comp_segment_entry_t entry=recovered_entry();
    assert(entry.descriptor.session_id==55u&&entry.descriptor.segment_index==0u&&entry.descriptor.sample_offset==0u&&
        entry.descriptor.sample_count==1600u&&entry.descriptor.encoded_length==222u&&
        entry.descriptor.flags==(COMP_REC_V2_SEALED|COMP_REC_V2_LAST|COMP_REC_V2_RECOVERED)&&entry.descriptor.total_segments==1u);
    companion_sha256_t hash;uint8_t digest[32];companion_sha256_init(&hash);
    companion_sha256_update(&hash,expected,sizeof(expected));companion_sha256_final(&hash,digest);
    assert(!memcmp(digest,entry.descriptor.sha256,32u)&&comp_rec_crc(expected,sizeof(expected))==entry.descriptor.content_crc32);
    assert(mic_starts==1u&&mic_stops==0u); /* boot cannot create a normal STOP */
    reboot();finish_recovery();
    assert(recovery.sealed==0u&&recovery.canceled==0u&&comp_wba_recording_recovery_ready(&recovery));
    entry=recovered_entry();assert(entry.descriptor.encoded_length==222u);
    puts("PASS boot audio recovery: real Opus committed prefix stops at whole packets, RECOVERED/LAST preserves axis/hash, unused future canceled, repeated mount idempotent; software only");
}
static void interrupted_seal(void)
{
    for(unsigned cut=1u;cut<=2u;cut++) {
        partial_capture();reboot();unsigned writes=f.writes;
        for(unsigned i=0u;i<20000u&&f.writes<writes+cut;i++) {
            f.now+=2u;assert(comp_wba_recording_recovery_poll(&recovery)==COMP_SEG_PENDING);
        }
        assert(f.writes==writes+cut);reboot();finish_recovery();
        comp_segment_entry_t entry=recovered_entry();
        assert(comp_wba_recording_recovery_ready(&recovery)&&entry.descriptor.encoded_length==222u&&
            entry.descriptor.flags==(COMP_REC_V2_SEALED|COMP_REC_V2_LAST|COMP_REC_V2_RECOVERED));
    }
    puts("PASS recovery metadata body/commit restart: no optimistic sealing, original WRITING or verified sealed row selected, exact prefix unchanged; software only");
}
static void roll_power_cut(void)
{
    init();ready(55u);assert(comp_wba_recording_pipeline_start(&pipeline,91u));bool cut=false;
    for(unsigned block=0u;block<36u&&!cut;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_cont_recording_pcm(&engine,samples,160u));
        for(unsigned i=0u;i<160u&&!cut;i++) {
            poll();cut=engine.active.descriptor.segment_index==1u&&engine.writer.committed_bytes>=248u&&engine.closing_pending;
        }
    }
    assert(cut&&engine.closing.descriptor.encoded_length==432u);
}
static void two_writing_tails(void)
{
    for(unsigned corrupt=0u;corrupt<2u;corrupt++) {
        roll_power_cut();
        if(corrupt)f.bytes[DATA_BASE+engine.active.extent_offset+256u+50u]^=1u;
        reboot();finish_recovery();unsigned count=0u;
        for(uint8_t i=0u;i<64u;i++) {
            comp_segment_entry_t entry;
            comp_segment_result_t result=comp_wba_segment_storage_entry(&storage,&catalog,i,&entry);
            if(result==COMP_SEG_NOT_FOUND)continue;
            assert(result==COMP_SEG_OK);count++;
            if(entry.descriptor.segment_index==0u) {
                assert(entry.state==COMP_SEG_UNSYNCED&&entry.descriptor.encoded_length==432u&&
                    entry.descriptor.sample_count==3200u&&entry.descriptor.flags==(COMP_REC_V2_SEALED|COMP_REC_V2_RECOVERED)&&
                    entry.descriptor.total_segments==0u);
            } else {
                assert(entry.descriptor.segment_index==1u&&entry.descriptor.sample_offset==3200u);
                if(corrupt)assert(entry.state==COMP_SEG_WRITING);
                else assert(entry.state==COMP_SEG_UNSYNCED&&entry.descriptor.encoded_length==222u&&
                    entry.descriptor.sample_count==1600u&&entry.descriptor.flags==(COMP_REC_V2_SEALED|COMP_REC_V2_RECOVERED|COMP_REC_V2_LAST)&&
                    entry.descriptor.total_segments==2u);
            }
        }
        assert(count==2u&&recovery.unresolved==corrupt&&comp_wba_recording_recovery_ready(&recovery)==(corrupt==0u));
    }
    puts("PASS interrupted segment handoff: two nonempty WRITING tails recover in original axis; corrupt later tail stays owned and cannot make preceding segment a false LAST; software only");
}
static void unused_preparation(void)
{
    const unsigned cuts[]={66u,70u,76u,82u,90u,96u};
    for(unsigned n=0u;n<sizeof(cuts)/sizeof(cuts[0]);n++) {
        init();assert(comp_wba_recording_pipeline_begin(&pipeline,55u,1u,0u,91u)==COMP_SEG_PENDING);
        for(unsigned i=0u;i<cuts[n];i++)poll();
        reboot();finish_recovery();
        assert(comp_wba_recording_recovery_ready(&recovery)&&!recovery.sealed&&!recovery.unresolved&&!catalog.visible_mask);
        for(unsigned i=0u;i<64u;i++)assert(catalog.slots[i]==255u);
    }
    /* Unrelated stale content underneath a blank provenance is NEVER treated
     * as an empty future merely because no new audio was committed. */
    init();comp_segment_entry_t owned={0};owned.state=COMP_SEG_WRITING;
    owned.descriptor.recording_id=catalog.next_id;owned.descriptor.session_id=55u;
    owned.descriptor.format_epoch=7u;owned.descriptor.codec=3u;owned.descriptor.source_mode=1u;
    memcpy(owned.descriptor.device_uid,device_uid,12u);owned.reserved_bytes=4096u;
    assert(comp_segment_catalog_put_begin(&catalog,&owned)==COMP_SEG_PENDING);
    comp_segment_result_t result=COMP_SEG_PENDING;
    while(result==COMP_SEG_PENDING){f.now+=2u;result=comp_wba_segment_storage_catalog_poll(&storage,&catalog);}
    assert(result==COMP_SEG_OK&&catalog.slots[0]!=255u&&!nor.erase_active);
    /* Before preparation starts; no legitimate in-flight erase may complete
     * over the injected old contents during startup probing. */
    f.bytes[DATA_BASE+1024u]=0xa5u;
    reboot();finish_recovery();
    assert(!comp_wba_recording_recovery_ready(&recovery)&&recovery.unresolved==1u&&catalog.slots[0]!=255u&&
        f.bytes[DATA_BASE+1024u]==0xa5u);
    puts("PASS unused boot reservations: full blank proof releases preparation cuts, stale nonblank content stays owned and blocks healthy capture readiness; software only");
}
static void unfinished_consume(void)
{
    for(unsigned stage=0u;stage<2u;stage++) {
        init();ready(55u);assert(comp_wba_recording_pipeline_start(&pipeline,91u));
        for(unsigned block=0u;block<4u;block++) {
            int16_t samples[160];pcm(block,samples);assert(comp_cont_recording_pcm(&engine,samples,160u));
            for(unsigned i=0u;i<160u;i++)poll();
        }
        assert(comp_wba_recording_pipeline_stop(&pipeline,91u));
        for(unsigned i=0u;i<10000u&&pipeline.state!=COMP_PIPE_FINISHED;i++)poll();
        assert(pipeline.state==COMP_PIPE_FINISHED);comp_segment_entry_t entry=recovered_entry();
        assert(comp_wba_recording_pipeline_consume(&pipeline,&entry.descriptor)==COMP_SEG_PENDING);
        bool cut=false;
        for(unsigned i=0u;i<10000u&&!cut;i++) {
            poll();
            if(stage==0u&&catalog.phase==0u&&pipeline.consume.state==COMP_SEG_ACKED) {
                comp_segment_entry_t actual;
                assert(comp_wba_segment_storage_entry(&storage,&catalog,0u,&actual)==COMP_SEG_OK);
                cut=actual.state==COMP_SEG_ACKED;
            }
            if(stage==1u&&nor.erase_active&&nor.erase_address>=DATA_BASE)cut=true;
        }
        assert(cut);reboot();finish_recovery();
        assert(comp_wba_recording_recovery_ready(&recovery)&&recovery.reclaimed==1u&&catalog.visible_mask==0u);
        for(unsigned i=0u;i<64u;i++)assert(catalog.slots[i]==255u);
        for(unsigned i=0u;i<entry.reserved_bytes;i++)assert(f.bytes[DATA_BASE+entry.extent_offset+i]==255u);
    }
    puts("PASS boot consume continuation: durable ACKED and interrupted ERASING finish original physical range and removal, no new MIC/peer ACK; software only");
}
#ifndef COMP_BOOT_TEST_MAIN
#define COMP_BOOT_TEST_MAIN main
#endif
int COMP_BOOT_TEST_MAIN(void)
{
    interrupted_audio();interrupted_seal();two_writing_tails();unused_preparation();unfinished_consume();return 0;
}
