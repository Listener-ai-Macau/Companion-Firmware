#define COMP_BOOT_TEST_MAIN recovery_fixture_main
#include "test_wba_recording_recovery.c"
static void init_idle_pipeline(void)
{
    comp_wba_pipeline_config_t cfg={&engine,&catalog,&storage,microphone,now,NULL,FRAMES,4096u};
    assert(comp_wba_recording_pipeline_init(&pipeline,&cfg));
}
/* Exact layout from Type receiver/publish.rs; no receiver FS/radio proof. */
static void type_ack(const comp_rec_v2_descriptor_t *d,uint8_t wire[84])
{
    memset(wire,0,84u);memcpy(wire,"CRA2\x02\x00\x54\x00",8u);
    memcpy(wire+8u,d->device_uid,12u);comp_rec_put64(wire+20u,d->format_epoch);comp_rec_put64(wire+28u,d->session_id);
    comp_rec_put32(wire+36u,d->segment_index);comp_rec_put32(wire+40u,d->recording_id);
    comp_rec_put32(wire+44u,d->encoded_length);memcpy(wire+48u,d->sha256,32u);
    comp_rec_put32(wire+80u,comp_rec_crc(wire,80u));
}
static comp_segment_result_t replay(const comp_rec_v2_descriptor_t *proof)
{
    unsigned writes=f.writes,erases=f.erases;uint8_t request[84],receipt[84];type_ack(proof,request);
    comp_segment_result_t result=comp_wba_recording_pipeline_consume_wire(&pipeline,request);
    assert(result==COMP_SEG_PENDING||result==COMP_SEG_OK);
    for(unsigned i=0u;i<1000u&&comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_PENDING;i++)poll();
    assert(f.writes==writes&&f.erases==erases&&pipeline.consumed_segments==0u&&!mic);
    result=comp_wba_recording_pipeline_consume_result(&pipeline);
    if(result==COMP_SEG_OK)assert(comp_wba_recording_pipeline_receipt(&pipeline,receipt)&&!memcmp(request,receipt,84u));
    else assert(!comp_wba_recording_pipeline_receipt(&pipeline,receipt));
    return result;
}
static void empty_sessions_until_gc(void)
{
    uint32_t serial=catalog.bank_serial;
    for(unsigned i=0u;i<64u&&catalog.bank_serial==serial;i++) {
        ready(100u+i);assert(comp_wba_recording_pipeline_stop(&pipeline,91u));
        for(unsigned j=0u;j<10000u&&pipeline.state!=COMP_PIPE_FINISHED;j++)poll();
        assert(pipeline.state==COMP_PIPE_FINISHED&&!mic&&!catalog.visible_mask);
    }
    assert(catalog.bank_serial==serial+1u);
}
static void lost_reply_across_gc(void)
{
    continuous();comp_rec_v2_descriptor_t proofs[4];
    for(unsigned i=0u;i<4u;i++) {
        comp_rec_v2_descriptor_t *d=&proofs[i];memset(d,0,sizeof(*d));
        d->recording_id=i+1u;d->format_epoch=7u;d->session_id=55u;d->segment_index=i;
        d->sample_offset=(uint64_t)i*3200u;d->sample_count=3200u;d->encoded_length=received_bytes[i];
        d->content_crc32=comp_rec_crc(received[i],received_bytes[i]);d->flags=(uint8_t)(COMP_REC_V2_SEALED|(i==3u?COMP_REC_V2_LAST:0u));
        d->total_segments=i==3u?4u:0u;d->codec=3u;d->source_mode=1u;d->sync_state=1u;memcpy(d->device_uid,device_uid,12u);
        companion_sha256_t hash;companion_sha256_init(&hash);companion_sha256_update(&hash,received[i],received_bytes[i]);
        companion_sha256_final(&hash,d->sha256);assert(comp_rec_v2_valid(d));
    }
    reboot();finish_recovery();init_idle_pipeline();
    assert(replay(&proofs[1])==COMP_SEG_OK);
    comp_rec_v2_descriptor_t wrong=proofs[1];wrong.sha256[0]^=1u;
    assert(replay(&wrong)==COMP_SEG_BAD_ARGUMENT);
    empty_sessions_until_gc();reboot();finish_recovery();init_idle_pipeline();
    for(unsigned i=0u;i<4u;i++)assert(replay(&proofs[i])==COMP_SEG_OK);
    /* A fifth legitimate removal replaces only the oldest receipt. Crash
     * after its commit but before readback/application success reply. */
    ready(77u);assert(comp_wba_recording_pipeline_start(&pipeline,91u));
    for(unsigned block=0u;block<4u;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_cont_recording_pcm(&engine,samples,160u));
        for(unsigned i=0u;i<160u;i++)poll();
    }
    assert(comp_wba_recording_pipeline_stop(&pipeline,91u));
    for(unsigned i=0u;i<10000u&&pipeline.state!=COMP_PIPE_FINISHED;i++)poll();
    comp_segment_entry_t fifth=recovered_entry();
    uint8_t command[84],receipt[84];type_ack(&fifth.descriptor,command);
    command[83]^=1u;unsigned reads=f.reads,writes=f.writes;
    assert(comp_wba_recording_pipeline_consume_wire(&pipeline,command)==COMP_SEG_BAD_ARGUMENT&&f.reads==reads&&f.writes==writes);
    command[83]^=1u;
    assert(comp_wba_recording_pipeline_consume_wire(&pipeline,command)==COMP_SEG_PENDING);bool cut=false;
    assert(!comp_wba_recording_pipeline_receipt(&pipeline,receipt));
    for(unsigned i=0u;i<10000u&&!cut;i++) {
        poll();uint32_t commit=catalog.banks[catalog.bank]+(uint32_t)catalog.target_slot*256u+252u;
        cut=catalog.phase&&catalog.pending_state==0u&&f.bytes[commit]==0u&&f.bytes[commit+1u]==0u&&
            f.bytes[commit+2u]==0u&&f.bytes[commit+3u]==0u;
    }
    assert(cut&&comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_PENDING);
    reboot();finish_recovery();init_idle_pipeline();
    assert(replay(&fifth.descriptor)==COMP_SEG_OK&&replay(&proofs[0])==COMP_SEG_NOT_FOUND);
    for(unsigned i=1u;i<4u;i++)assert(replay(&proofs[i])==COMP_SEG_OK);
    assert(catalog.visible_mask==0u);for(unsigned i=0u;i<64u;i++)assert(catalog.slots[i]==255u);
    assert(replay(&proofs[3])==COMP_SEG_OK); /* same request idempotent in RAM */
    puts("PASS durable lost-consume-reply recovery: four exact length/CRC/SHA/session proofs survive reboot/GC; Type84B CRA2 input and exact receipt only after physical removal; committed removal before application reply replays with no new erase; oldest expires explicitly, no payload ownership retained; software only");
}
int main(void){lost_reply_across_gc();return 0;}
