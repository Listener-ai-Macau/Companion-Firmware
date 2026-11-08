#include "companion_range_reclaim.h"
#include <stdio.h>

enum {BASE=4096,RESERVED=12288,TOTAL=BASE+RESERVED+4096,PAYLOAD=9000};
static uint8_t media[TOTAL],snapshot[TOTAL],payload[PAYLOAD],scratch[256];
static comp_segment_entry_t entry;
static comp_range_plan_t plan;
static uint8_t proof[32];
static unsigned calls,erases,polls,zero_pending;
static bool ignore_erase,fail_done_verify;
static comp_segment_io_t preview;
#define CHECK(x) do{if(!(x)){fprintf(stderr,"FAIL %u %s\n",(unsigned)__LINE__,#x);return false;}}while(0)
static bool rd(void *v,uint32_t at,uint8_t *p,uint32_t n)
{
    (void)v;calls++;
    if(at>TOTAL||n>TOTAL-at)return false;
    if(fail_done_verify&&at==32u&&n==32u&&!comp_rec_not_uniform(media+56u,4u,0u))return false;
    memcpy(p,media+at,n);return true;
}
static bool program(void *v,uint32_t at,const uint8_t *p,uint32_t n)
{
    (void)v;calls++;
    if(!n||at>TOTAL||n>TOTAL-at||at/256u!=(at+n-1u)/256u)return false;
    for(uint32_t i=0;i<n;i++)if((media[at+i]&p[i])!=p[i])return false;
    for(uint32_t i=0;i<n;i++)media[at+i]&=p[i];
    return true;
}
static bool erase(void *v,uint32_t at,uint32_t n,uint32_t *done)
{
    (void)v;calls++;
    if(preview.kind!=COMP_SEG_IO_ERASE||preview.address!=at||preview.bytes!=n||
       at%4096u||n<4096u||at<BASE+4096u||at>BASE+RESERVED-4096u)return false;
    if(zero_pending){zero_pending--;*done=0u;return true;}
    if(!ignore_erase)memset(media+at,255,4096u);
    erases++;*done=4096u;return true;
}
static comp_segment_result_t audio_rd(void *v,uint32_t at,uint8_t *p,uint32_t n)
{return rd(v,at,p,n)?COMP_SEG_OK:COMP_SEG_IO_ERROR;}
static comp_segment_result_t audio_program(void *v,uint32_t at,const uint8_t *p,uint32_t n)
{return program(v,at,p,n)?COMP_SEG_OK:COMP_SEG_IO_ERROR;}
static comp_segment_result_t tick(comp_range_reclaim_t *w)
{
    unsigned before=calls;comp_segment_result_t r=comp_range_reclaim_next_io(w,&preview);
    if(r!=COMP_SEG_OK&&r!=COMP_SEG_PENDING)return r;
    r=comp_range_reclaim_poll(w);polls++;
    return calls-before<=1u?r:COMP_SEG_BAD_STATE;
}
static comp_segment_result_t finish(comp_range_reclaim_t *w)
{
    comp_segment_result_t r=COMP_SEG_PENDING;
    for(unsigned i=0;i<2000u&&r==COMP_SEG_PENDING;i++)r=tick(w);
    return r;
}
static bool setup(void)
{
    memset(media,255,sizeof(media));memset(&entry,0,sizeof(entry));
    entry.state=COMP_SEG_WRITING;entry.reserved_bytes=RESERVED;entry.started_unix_s=1794100000u;
    entry.descriptor.recording_id=353u;entry.descriptor.format_epoch=7u;entry.descriptor.session_id=353u;
    entry.descriptor.codec=3u;for(unsigned i=0;i<12u;i++)entry.descriptor.device_uid[i]=(uint8_t)(i+1u);
    const comp_segment_audio_port_t ap={audio_rd,audio_program,NULL};comp_segment_audio_t a={0};
    CHECK(comp_segment_audio_prepare_begin(&a,&ap,&entry,BASE,scratch)==COMP_SEG_PENDING);
    comp_segment_result_t r=COMP_SEG_PENDING;
    for(unsigned i=0;i<20u&&r==COMP_SEG_PENDING;i++)r=comp_segment_audio_poll(&a);
    CHECK(r==COMP_SEG_OK);
    for(unsigned at=0;at<PAYLOAD;){
        uint8_t n=(uint8_t)(PAYLOAD-at>248u?248u:PAYLOAD-at);
        CHECK(comp_segment_audio_append_begin(&a,payload+at,n)==COMP_SEG_PENDING);
        r=COMP_SEG_PENDING;for(unsigned i=0;i<20u&&r==COMP_SEG_PENDING;i++)r=comp_segment_audio_poll(&a);
        CHECK(r==COMP_SEG_OK);at+=n;
    }
    entry.state=COMP_SEG_UNSYNCED;entry.descriptor.sync_state=1u;
    entry.descriptor.encoded_length=PAYLOAD;entry.descriptor.sample_count=16000u;
    entry.descriptor.flags=COMP_REC_V2_SEALED|COMP_REC_V2_LAST;entry.descriptor.total_segments=1u;
    entry.descriptor.content_crc32=comp_rec_crc(payload,PAYLOAD);
    companion_sha256_t sha;companion_sha256_init(&sha);companion_sha256_update(&sha,payload,PAYLOAD);
    companion_sha256_final(&sha,entry.descriptor.sha256);
    comp_range_journal_header_prepare(media,entry.descriptor.device_uid,7u,1u,1u);
    memset(media+28u,0,4u);memset(media+BASE+RESERVED,0x5a,4096u);
    uint32_t begin,end;
    CHECK(comp_range_plan(&entry,0u,1u,3u,1234u,&plan,&begin,&end));
    CHECK(begin==3720u&&end==PAYLOAD);
    companion_sha256_init(&sha);companion_sha256_update(&sha,payload+begin,end-begin);companion_sha256_final(&sha,proof);
    memcpy(snapshot,media,sizeof(media));calls=erases=polls=zero_pending=0u;
    ignore_erase=fail_done_verify=false;return true;
}
static comp_segment_result_t begin(comp_range_reclaim_t *w,const uint8_t *hash)
{
    const comp_segment_port_t p={rd,program,erase,NULL};
    return comp_range_reclaim_begin(w,&p,&entry,BASE,0u,1u,1u,0u,&plan,hash,scratch);
}
static bool preserved(void)
{
    CHECK(!memcmp(media+BASE,snapshot+BASE,4096u)); /* provenance/first source range */
    CHECK(!memcmp(media+BASE+RESERVED,snapshot+BASE+RESERVED,4096u));
    CHECK(!memcmp(media+64u,snapshot+64u,192u)); /* six other journal records */
    return true;
}
static bool ordinary_and_replay(void)
{
    CHECK(setup());comp_range_reclaim_t w={0};
    CHECK(begin(&w,proof)==COMP_SEG_PENDING&&calls==0u);
    zero_pending=3u;CHECK(finish(&w)==COMP_SEG_OK&&erases==2u&&preserved());
    CHECK(!comp_rec_not_uniform(media+BASE+4096u,8192u,255u));
    comp_range_plan_t decoded;
    CHECK(comp_range_journal_record_decode(media+32u,media,0u,&decoded)==COMP_RANGE_DONE);
    unsigned old=erases;memset(&w,0,sizeof(w));CHECK(begin(&w,proof)==COMP_SEG_PENDING&&finish(&w)==COMP_SEG_OK&&erases==old);
    puts("PASS_RANGE_RECLAIM exact_range_SHA=1 real_CSP2_CRC=1 physical_blank_before_DONE=1 one_IO_per_poll=1 pending_no_cursor_advance=1 replay_no_erase=1 neighboring_data_unchanged=1");
    return true;
}
static bool refusal_and_failures(void)
{
    CHECK(setup());comp_range_reclaim_t w={0};uint8_t bad[32];memcpy(bad,proof,32u);bad[0]^=1u;
    CHECK(begin(&w,bad)==COMP_SEG_PENDING&&finish(&w)==COMP_SEG_BAD_ARGUMENT&&erases==0u);
    CHECK(!memcmp(media,snapshot,sizeof(media)));
    CHECK(setup());memset(&w,0,sizeof(w));media[BASE+4096u+20u]^=1u;
    CHECK(begin(&w,proof)==COMP_SEG_PENDING&&finish(&w)==COMP_SEG_CORRUPT&&erases==0u);
    CHECK(setup());memset(&w,0,sizeof(w));media[24u]^=1u;
    CHECK(begin(&w,proof)==COMP_SEG_PENDING&&finish(&w)==COMP_SEG_CORRUPT&&erases==0u);
    CHECK(setup());memset(&w,0,sizeof(w));ignore_erase=true;
    CHECK(begin(&w,proof)==COMP_SEG_PENDING&&finish(&w)==COMP_SEG_CORRUPT);
    comp_range_plan_t decoded;CHECK(comp_range_journal_record_decode(media+32u,media,0u,&decoded)==COMP_RANGE_PENDING);
    CHECK(setup());memset(&w,0,sizeof(w));fail_done_verify=true;
    CHECK(begin(&w,proof)==COMP_SEG_PENDING&&finish(&w)==COMP_SEG_IO_ERROR);
    fail_done_verify=false;memset(&w,0,sizeof(w));CHECK(begin(&w,proof)==COMP_SEG_PENDING&&finish(&w)==COMP_SEG_OK);
    puts("PASS_RANGE_REFUSALS wrong_SHA_and_page_CRC_no_erase=1 foreign_journal_no_erase=1 ignored_physical_command_no_DONE=1 lost_final_read_reconciled=1");
    return true;
}
static bool power_loss(void)
{
    CHECK(setup());comp_range_reclaim_t w={0};CHECK(begin(&w,proof)==COMP_SEG_PENDING&&finish(&w)==COMP_SEG_OK);
    unsigned steps=polls;
    for(unsigned cut=0;cut<=steps;cut++){
        CHECK(setup());memset(&w,0,sizeof(w));CHECK(begin(&w,proof)==COMP_SEG_PENDING);
        for(unsigned i=0;i<cut;i++)CHECK(tick(&w)==(i+1u==steps?COMP_SEG_OK:COMP_SEG_PENDING));
        comp_range_plan_t decoded;
        comp_range_journal_state_t state=comp_range_journal_record_decode(media+32u,media,0u,&decoded);
        unsigned old=erases;memset(&w,0,sizeof(w));CHECK(begin(&w,proof)==COMP_SEG_PENDING);
        comp_segment_result_t r=finish(&w);
        if(state==COMP_RANGE_TORN)CHECK(r==COMP_SEG_CORRUPT&&erases==old&&old==0u);
        else CHECK(r==COMP_SEG_OK&&!comp_rec_not_uniform(media+BASE+4096u,8192u,255u));
        CHECK(preserved());
    }
    CHECK(setup());memset(&w,0,sizeof(w));CHECK(begin(&w,proof)==COMP_SEG_PENDING&&finish(&w)==COMP_SEG_OK);
    media[56u]=255u; /* torn DONE word must replay, never optimistic success */
    memset(&w,0,sizeof(w));CHECK(begin(&w,proof)==COMP_SEG_PENDING&&finish(&w)==COMP_SEG_OK&&erases==4u);
    printf("PASS_RANGE_POWER_LOSS cuts=%u uncommitted_never_erases=1 committed_intent_resumes=1 torn_DONE_replays=1 no_early_complete=1\n",steps+1u);
    return true;
}
int main(void)
{
    for(unsigned i=0;i<PAYLOAD;i++)payload[i]=(uint8_t)(i*37u+13u);
    return ordinary_and_replay()&&refusal_and_failures()&&power_loss()?0:1;
}
