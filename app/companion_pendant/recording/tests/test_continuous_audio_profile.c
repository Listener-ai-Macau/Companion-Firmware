#include "../companion_continuous_recording.h"
#include "../wba_recording_crc.h"
static bool profile_snapshot(void *,comp_rec_audio_profile_t *);
#define COMP_REC_TEST_AUDIO_PROFILE profile_snapshot
#define main original_continuous_main
#include "test_companion_continuous_recording.c"
#undef main
static bool change_profile;
static bool profile_snapshot(void *v,comp_rec_audio_profile_t *p)
{
    const fixture_t *f=v;memset(p,0,sizeof(*p));p->output=3u;p->filtered_mask=3u;p->gain_q15=32768u;
    p->delay_q8=128;p->right_gain_q15=32768u;p->firmware_version=0x00010200u;p->decimation=96u;
    memset(p->firmware_source,0x5a,20u);memset(p->calibration_sha256,0x83,32u);
    if(change_profile&&f->recorder.active.descriptor.segment_index)p->firmware_source[0]^=1u;
    return true;
}
static comp_segment_result_t preserve_background(void *v)
{
    fixture_t *f=v;if(f->no_next)return COMP_SEG_OK;
    if(f->next_phase==4u)template_entry(f,&f->recorder.active);
    return prepare_step(f);
}
static bool recover(fixture_t *f,const comp_segment_entry_t *e,bool corrupt)
{
    comp_segment_audio_recovery_t r={0};comp_segment_audio_port_t port=audio_port(f);
    /* Recovery owns a WRITING reservation, not a sealed catalog row. Reuse
     * its immutable extent/provenance while retaining e as expected truth. */
    comp_segment_entry_t owned=*e;owned.state=COMP_SEG_WRITING;
    owned.descriptor.sample_count=0u;owned.descriptor.encoded_length=0u;owned.descriptor.flags=0u;
    comp_segment_result_t result=comp_segment_audio_recover_begin(&r,&port,&owned,BASE,f->scratch);
    for(unsigned n=0u;n<1000u&&result==COMP_SEG_PENDING;n++)result=comp_segment_audio_recover_poll(&r);
    if(corrupt){CHECK(result==COMP_SEG_CORRUPT);return true;}
    if(result!=COMP_SEG_OK)fprintf(stderr,"RECOVERY result=%u bytes=%u frames=%u schema=%u header=%u config=%u profile=%u end=%u phase=%u page=%u\n",(unsigned)result,r.bytes,r.frames,r.container_schema,r.header_bytes,(unsigned)r.codec_config_seen,(unsigned)r.audio_profile_seen,(unsigned)r.codec_end_seen,r.phase,r.pages);
    CHECK(result==COMP_SEG_OK);uint32_t bytes,frames,crc;uint8_t sha[32];
    CHECK(comp_segment_audio_recovered(&r,&bytes,&frames,&crc,sha));
    CHECK(bytes==e->descriptor.encoded_length&&(uint64_t)frames*320u==e->descriptor.sample_count);
    CHECK(crc==e->descriptor.content_crc32&&!memcmp(sha,e->descriptor.sha256,32u));return true;
}
static bool run_profile(unsigned blocks,bool pause,const char *output)
{
    fixture_t *f=&fixture;change_profile=false;CHECK(initialize_mode(f,false,COMP_CONT_TIMELINE_AUDIO_PROFILE));
    f->recorder.config.background=preserve_background;int16_t pcm[160];
    for(unsigned b=0u;b<blocks;b++){pcm_block(b,pcm);CHECK(comp_cont_recording_pcm(&f->recorder,pcm,160u));f->now+=10u;CHECK(poll_many(f,80u));}
    if(pause){CHECK(comp_cont_recording_pause(&f->recorder,91u,1u));CHECK(poll_many(f,500u));CHECK(f->recorder.state==COMP_CONT_PAUSED);f->now+=3000u;}
    CHECK(comp_cont_recording_stop(&f->recorder,91u));
    for(unsigned i=0u;i<5000u&&f->recorder.state!=COMP_CONT_SEALED&&f->recorder.state!=COMP_CONT_CANCELED;i++)CHECK(poll_many(f,1u));
    if(!blocks){CHECK(f->recorder.state==COMP_CONT_CANCELED&&f->count==0u);return true;}
    CHECK(f->recorder.state==COMP_CONT_SEALED&&!f->microphone);
    FILE *file=output?fopen(output,"wb"):NULL;if(output)CHECK(file);
    if(file){uint8_t header[8]={'C','M','B','4',0,0,0,0};comp_rec_put32(header+4u,f->count);CHECK(fwrite(header,1,8u,file)==8u);}
    for(unsigned i=0u;i<f->count;i++){
        const comp_segment_entry_t *e=&f->sealed[i];CHECK(recover(f,e,false));uint32_t bytes=0u,index=0u;
        while(bytes<e->descriptor.encoded_length){uint8_t n=0u;comp_segment_audio_port_t port=audio_port(f);CHECK(comp_segment_audio_read_page(&port,e,BASE,index++,f->scratch,&n)==COMP_SEG_OK);CHECK(bytes+n<=MAX_RAW);memcpy(f->raw[i]+bytes,f->scratch,n);bytes+=n;}
        CHECK(f->raw[i][4]==5u&&f->raw[i][7]==15u);comp_rec_audio_profile_t p;
        CHECK(comp_rec_audio_profile_decode(f->raw[i]+44u,bytes-44u,&p));CHECK(p.output==3u&&p.delay_q8==128&&p.firmware_source[0]==0x5au);
        if(file){uint8_t n[4],descriptor[112];comp_rec_put32(n,bytes);CHECK(comp_rec_v2_encode(&e->descriptor,descriptor,sizeof(descriptor)));CHECK(fwrite(n,1,4u,file)==4u&&fwrite(descriptor,1,112u,file)==112u&&fwrite(f->raw[i],1,bytes,file)==bytes);}
    }
    if(file)CHECK(fclose(file)==0);
    /* A valid physical page CRC must not hide invalid processing metadata. */
    const comp_segment_entry_t *e=&f->sealed[0];uint8_t *provenance=f->bytes+BASE+e->extent_offset;uint8_t *page=provenance+256u;
    page[44u+7u]=4u;comp_rec_put32(page+44u+92u,comp_rec_crc(page+44u,92u));
    uint8_t identity[9];comp_rec_put32(identity,comp_rec_get32(provenance+92u));comp_rec_put32(identity+4u,0u);identity[8]=page[252u];
    comp_rec_put32(page+248u,comp_wba_recording_crc32(comp_wba_recording_crc32(0u,identity,9u),page,248u));CHECK(recover(f,e,true));
    printf("PASS_PROFILE_ENGINE blocks=%u segments=%u paused=%u; original header/audio/SHA and recovery bind metadata\n",blocks,f->count,(unsigned)pause);return true;
}
static bool changed_snapshot_fault(void)
{
    fixture_t *f=&fixture;change_profile=false;CHECK(initialize_mode(f,false,COMP_CONT_TIMELINE_AUDIO_PROFILE));f->recorder.config.background=preserve_background;change_profile=true;
    int16_t pcm[160];
    for(unsigned b=0u;b<40u&&f->recorder.state!=COMP_CONT_FAULT;b++){
        pcm_block(b,pcm);CHECK(comp_cont_recording_pcm(&f->recorder,pcm,160u));f->now+=10u;
        for(unsigned i=0u;i<80u&&f->recorder.state!=COMP_CONT_FAULT;i++)comp_cont_recording_poll(&f->recorder);
    }
    CHECK(f->recorder.state==COMP_CONT_FAULT&&!f->microphone&&f->recorder.active.descriptor.segment_index==1u);
    CHECK(f->recorder.writer.committed_bytes==0u);change_profile=false;
    puts("PASS changed session snapshot faults before successor profile/audio becomes durable");return true;
}
static bool profile_geometry(void)
{
    comp_recording_geometry_t old,profile;CHECK(comp_recording_geometry_plan(15695872u,64u,&old));
    CHECK(old.extent_bytes==270336u&&old.segment_frames==6211u);
    CHECK(comp_recording_geometry_plan_profile(15695872u,64u,true,&profile));
    CHECK(comp_recording_required_capacity_profile(profile.segment_frames,true,true)<=comp_segment_audio_capacity(profile.extent_bytes));
    comp_segment_entry_t e={0};e.state=COMP_SEG_WRITING;e.reserved_bytes=old.extent_bytes;e.descriptor.codec=3u;
    e.descriptor.recording_id=1u;e.descriptor.format_epoch=1u;e.descriptor.session_id=1u;memcpy(e.descriptor.device_uid,uid,12u);
    comp_segment_audio_t w={0};w.prepared=true;w.entry=&e;
    comp_cont_config_t cfg={microphone,now_ms,next,seal,cancel,preserve_background,&fixture,old.segment_frames,10u,COMP_CONT_TIMELINE_AUDIO_PROFILE,profile_snapshot};
    comp_cont_recording_t r;change_profile=false;
    CHECK(!comp_cont_recording_init(&r,&cfg,&e,&w,1u));
    cfg.segment_frames=profile.segment_frames;e.reserved_bytes=profile.extent_bytes;
    CHECK(comp_cont_recording_init(&r,&cfg,&e,&w,1u));comp_cont_recording_fault(&r,COMP_SEG_BAD_STATE);
    puts("PASS profile-aware geometry includes exact prelude allowance before claiming a reservation; legacy6211 unchanged");return true;
}
int main(int argc,char **argv)
{
    if(argc==3&&!strcmp(argv[2],"geometry-only"))return profile_geometry()?0:1;
    if(argc==3&&!strcmp(argv[2],"export-only"))return run_profile(40u,false,argv[1])?0:1;
    if(argc!=2 && !(argc==3&&!strcmp(argv[2],"skip-original")))return 2;
    char *old_args[]={argv[0],"source-boundary"};if(argc==2&&original_continuous_main(2,old_args))return 1;
    if(!run_profile(0u,false,NULL)||!run_profile(1u,false,NULL)||!run_profile(4u,true,NULL)||!run_profile(40u,false,argv[1])||!changed_snapshot_fault())return 1;
    puts("PASS_OPTIONAL_SCHEMA5_ENGINE_RECOVERY_SOFTWARE_NOT_PRODUCT_ADAPTER");return 0;
}
