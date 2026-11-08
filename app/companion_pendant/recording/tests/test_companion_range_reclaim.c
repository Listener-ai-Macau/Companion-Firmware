#include "companion_range_reclaim.h"
#include <stdio.h>

enum {BANK=24576,BASE=2*BANK,RESERVED=12288,TOTAL=BASE+RESERVED+8192,PAYLOAD=9000};
static uint8_t media[TOTAL],snapshot[TOTAL],payload[PAYLOAD],scratch[256];
static comp_segment_entry_t entry;
static comp_range_plan_t plan;
static uint8_t proof[32];
static unsigned calls,erases,polls,zero_pending,metadata_erases;
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
       at%4096u||n<4096u||at>TOTAL-4096u)return false;
    if(zero_pending){zero_pending--;*done=0u;return true;}
    if(!ignore_erase)memset(media+at,255,4096u);
    if(at<BASE)metadata_erases++;else erases++;*done=4096u;return true;
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
    memcpy(snapshot,media,sizeof(media));calls=erases=polls=zero_pending=metadata_erases=0u;
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
static bool first_sector_overlap(void)
{
    CHECK(setup());uint32_t first,last;
    CHECK(comp_range_plan(&entry,0u,0u,1u,1235u,&plan,&first,&last));
    CHECK(first==0u&&last==3720u);
    companion_sha256_t sha;companion_sha256_init(&sha);companion_sha256_update(&sha,payload,last);
    companion_sha256_final(&sha,proof);comp_range_reclaim_t w={0};
    CHECK(begin(&w,proof)==COMP_SEG_PENDING&&finish(&w)==COMP_SEG_OK&&erases==1u);
    CHECK(!comp_rec_not_uniform(media+BASE,4096u,255u));
    CHECK(!memcmp(media+BASE+4096u,snapshot+BASE+4096u,RESERVED));
    // Tail pages remain independently readable from sealed catalogue identity
    // after the original CSP2 provenance sector has physically gone.
    const comp_segment_audio_port_t port={audio_rd,NULL,NULL};uint8_t length=0u;
    CHECK(comp_segment_audio_read_page(&port,&entry,BASE,15u,scratch,&length)==COMP_SEG_OK);
    CHECK(length==248u&&!memcmp(scratch,payload+3720u,248u));
    puts("PASS_RANGE_FIRST_SECTOR physical_provenance_sector_reclaimed=1 exact_first3720_audio_SHA=1 untouched_tail_still_CSP2_CRC_readable=1 no_artificial_first_sector_delay=1");
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
static comp_segment_result_t catalog_tick(comp_segment_catalog_t *c)
{
    unsigned before=calls;
    if(comp_segment_catalog_next_io(c,&preview)!=COMP_SEG_OK)return COMP_SEG_BAD_STATE;
    comp_segment_result_t r=comp_segment_catalog_poll(c);
    return calls-before<=1u?r:COMP_SEG_BAD_STATE;
}
static comp_segment_result_t catalog_finish(comp_segment_catalog_t *c)
{
    comp_segment_result_t r=COMP_SEG_PENDING;
    for(unsigned i=0;i<20000u&&r==COMP_SEG_PENDING;i++)r=catalog_tick(c);
    return r;
}
static comp_segment_result_t mount_catalog(comp_segment_catalog_t *c)
{
    const comp_segment_port_t port={rd,program,erase,NULL};
    comp_segment_result_t r=comp_segment_catalog_mount_begin(c,&port,0u,BANK,BASE,TOTAL-BASE,entry.descriptor.device_uid,7u);
    return r==COMP_SEG_PENDING?catalog_finish(c):r;
}
static bool catalog_setup(comp_segment_catalog_t *c)
{
    CHECK(setup());memset(media,255,BASE);
    CHECK(mount_catalog(c)==COMP_SEG_UNFORMATTED);
    CHECK(comp_segment_catalog_format_blank_begin(c)==COMP_SEG_PENDING&&catalog_finish(c)==COMP_SEG_OK);
    comp_segment_entry_t writing=entry;writing.state=COMP_SEG_WRITING;
    writing.descriptor.recording_id=c->next_id;entry.descriptor.recording_id=c->next_id;
    // Recreate the real CSP2 source with this catalogue's monotonic identity.
    memset(media+BASE,255,RESERVED);comp_segment_audio_t a={0};
    const comp_segment_audio_port_t ap={audio_rd,audio_program,NULL};
    writing.descriptor.sample_count=0u;writing.descriptor.encoded_length=0u;writing.descriptor.flags=0u;
    writing.descriptor.content_crc32=0u;writing.descriptor.total_segments=0u;writing.descriptor.sync_state=0u;
    memset(writing.descriptor.sha256,0,32u);
    CHECK(comp_segment_catalog_put_begin(c,&writing)==COMP_SEG_PENDING&&catalog_finish(c)==COMP_SEG_OK);
    CHECK(comp_segment_audio_prepare_begin(&a,&ap,&writing,BASE,scratch)==COMP_SEG_PENDING);
    comp_segment_result_t r=COMP_SEG_PENDING;for(unsigned i=0;i<20u&&r==COMP_SEG_PENDING;i++)r=comp_segment_audio_poll(&a);CHECK(r==COMP_SEG_OK);
    for(unsigned at=0;at<PAYLOAD;){uint8_t n=(uint8_t)(PAYLOAD-at>248u?248u:PAYLOAD-at);
        CHECK(comp_segment_audio_append_begin(&a,payload+at,n)==COMP_SEG_PENDING);r=COMP_SEG_PENDING;
        for(unsigned i=0;i<20u&&r==COMP_SEG_PENDING;i++)r=comp_segment_audio_poll(&a);
        CHECK(r==COMP_SEG_OK);at+=n;}
    CHECK(comp_segment_catalog_put_begin(c,&entry)==COMP_SEG_PENDING&&catalog_finish(c)==COMP_SEG_OK);
    erases=metadata_erases=0u;return true;
}
static bool catalog_range(comp_segment_catalog_t *c,comp_range_reclaim_t *w,uint16_t first,uint16_t end,uint32_t nonce)
{
    uint32_t begin,limit;comp_range_plan_t p;
    CHECK(comp_range_plan(&entry,0u,first,end,nonce,&p,&begin,&limit));
    companion_sha256_t sha;companion_sha256_init(&sha);companion_sha256_update(&sha,payload+begin,limit-begin);companion_sha256_final(&sha,proof);
    CHECK(comp_segment_catalog_range_begin(c,w,&entry,0u,first,end,nonce,proof)==COMP_SEG_PENDING);
    return true;
}
static bool catalog_integrated(void)
{
    comp_segment_catalog_t c,rebooted;comp_range_reclaim_t w={0};comp_segment_entry_t saved,receipt;
    CHECK(catalog_setup(&c));uint32_t generation=c.generation;
    CHECK(catalog_range(&c,&w,0u,1u,101u)&&catalog_finish(&c)==COMP_SEG_OK&&erases==1u);
    CHECK(c.generation==generation&&comp_segment_catalog_read(&c,0u,&saved)==COMP_SEG_OK&&saved.range_end==1u);
    CHECK(mount_catalog(&rebooted)==COMP_SEG_OK&&comp_segment_catalog_read(&rebooted,0u,&saved)==COMP_SEG_OK);
    CHECK(saved.range_end==1u&&saved.range_nonce==101u&&!comp_segment_catalog_range_pending(&rebooted));
    FILE *legacy=fopen("range-catalog-after-range.bin","wb");CHECK(legacy&&fwrite(media,1u,sizeof(media),legacy)==sizeof(media));CHECK(fclose(legacy)==0);
    CHECK(comp_segment_catalog_range_begin(&rebooted,&w,&saved,0u,0u,1u,101u,proof)==COMP_SEG_OK&&erases==1u);
    entry=saved;CHECK(catalog_range(&rebooted,&w,1u,3u,102u)&&catalog_finish(&rebooted)==COMP_SEG_OK&&erases==3u);
    CHECK(comp_segment_catalog_read(&rebooted,0u,&saved)==COMP_SEG_OK&&saved.range_end==3u);
    saved.state=COMP_SEG_ACKED;saved.descriptor.sync_state=2u;
    CHECK(comp_segment_catalog_ack_at_begin(&rebooted,&saved,0u)==COMP_SEG_PENDING&&catalog_finish(&rebooted)==COMP_SEG_OK);
    CHECK(comp_segment_catalog_reclaim_at_begin(&rebooted,&saved,0u)==COMP_SEG_PENDING&&catalog_finish(&rebooted)==COMP_SEG_OK);
    CHECK(erases==3u); /* no second erase of ranges already durably DONE */
    CHECK(mount_catalog(&c)==COMP_SEG_OK&&comp_segment_catalog_receipt_read(&c,0u,&receipt)==COMP_SEG_OK);
    CHECK(receipt.state==0u&&receipt.descriptor.encoded_length==PAYLOAD&&!memcmp(receipt.descriptor.sha256,entry.descriptor.sha256,32u));
    puts("PASS_RANGE_CATALOG actual_directory_begin_mount_replay=1 original_generation_and_receipt_unchanged=1 final_consume_no_duplicate_physical_erase=1");
    return true;
}
static bool catalog_interrupted(void)
{
    comp_segment_catalog_t c,rebooted;comp_range_reclaim_t w={0};comp_segment_entry_t saved;
    CHECK(catalog_setup(&c)&&catalog_range(&c,&w,0u,1u,201u));
    for(unsigned i=0;i<2000u&&!erases;i++)CHECK(catalog_tick(&c)==COMP_SEG_PENDING);
    CHECK(erases==1u&&mount_catalog(&rebooted)==COMP_SEG_OK&&comp_segment_catalog_range_pending(&rebooted));
    CHECK(comp_segment_catalog_read(&rebooted,0u,&saved)==COMP_SEG_OK&&saved.range_end==0u);
    CHECK(comp_segment_catalog_range_begin(&rebooted,&w,&saved,0u,0u,1u,202u,proof)==COMP_SEG_BAD_STATE);
    CHECK(comp_segment_catalog_range_begin(&rebooted,&w,&saved,0u,0u,1u,201u,proof)==COMP_SEG_PENDING&&catalog_finish(&rebooted)==COMP_SEG_OK);
    CHECK(erases==2u&&!comp_segment_catalog_range_pending(&rebooted));
    CHECK(mount_catalog(&c)==COMP_SEG_OK&&comp_segment_catalog_read(&c,0u,&saved)==COMP_SEG_OK&&saved.range_end==1u);
    puts("PASS_RANGE_CATALOG_INTERRUPTED durable_pending_range_mounted=1 wrong_nonce_no_erase=1 exact_range_replayed_after_provenance_erased=1");return true;
}
static bool catalog_gc_and_rebase(void)
{
    comp_segment_catalog_t c,rebooted;comp_range_reclaim_t w={0};comp_segment_entry_t dummy,saved;
    CHECK(catalog_setup(&c)&&catalog_range(&c,&w,0u,1u,301u)&&catalog_finish(&c)==COMP_SEG_OK);
    uint32_t serial=c.bank_serial;
    for(unsigned count=0;count<100u&&c.bank_serial==serial;count++){
        memset(&dummy,0,sizeof(dummy));dummy.state=COMP_SEG_WRITING;dummy.extent_offset=RESERVED+4096u;dummy.reserved_bytes=4096u;
        dummy.descriptor.device_uid[0]=0u;memcpy(dummy.descriptor.device_uid,entry.descriptor.device_uid,12u);
        dummy.descriptor.recording_id=c.next_id;dummy.descriptor.format_epoch=7u;dummy.descriptor.session_id=c.next_id+1000u;dummy.descriptor.codec=3u;
        CHECK(comp_segment_catalog_put_begin(&c,&dummy)==COMP_SEG_PENDING&&catalog_finish(&c)==COMP_SEG_OK);
        CHECK(comp_segment_catalog_cancel_unwritten_begin(&c,&dummy)==COMP_SEG_PENDING&&catalog_finish(&c)==COMP_SEG_OK);
    }
    CHECK(c.bank_serial==serial+1u&&metadata_erases==BANK/4096u&&erases==1u);
    CHECK(mount_catalog(&rebooted)==COMP_SEG_OK&&comp_segment_catalog_read(&rebooted,0u,&saved)==COMP_SEG_OK&&saved.range_end==1u);
    CHECK(saved.range_nonce==301u);
    // Canonical OTA metadata snapshot includes the same compact frontier;
    // each generated page still performs at most one ordinary row read.
    static uint8_t canonical[BASE];
    for(unsigned i=0;i<BASE/256u;i++){
        unsigned before=calls;CHECK(comp_segment_catalog_rebase_page(&rebooted,0u,BANK,BASE,TOTAL-BASE,TOTAL,i,canonical+i*256u));
        CHECK(calls-before<=1u);
    }
    memcpy(media,canonical,BASE);
    CHECK(mount_catalog(&c)==COMP_SEG_OK&&comp_segment_catalog_read(&c,0u,&saved)==COMP_SEG_OK&&saved.range_end==1u&&saved.range_nonce==301u);
    FILE *legacy=fopen("range-catalog-after-rebase.bin","wb");CHECK(legacy&&fwrite(media,1u,sizeof(media),legacy)==sizeof(media));CHECK(fclose(legacy)==0);
    entry=saved;CHECK(catalog_range(&c,&w,1u,2u,302u)&&catalog_finish(&c)==COMP_SEG_OK&&erases==2u);
    puts("PASS_RANGE_CATALOG_GC_OTA compact_frontier_preserved=1 metadata_only_GC=1 canonical_rebase_retains_original_proof=1 physical_tail_resumes=1");
    return true;
}
int main(void)
{
    for(unsigned i=0;i<PAYLOAD;i++)payload[i]=(uint8_t)(i*37u+13u);
    return ordinary_and_replay()&&refusal_and_failures()&&power_loss()&&first_sector_overlap()&&
        catalog_integrated()&&catalog_interrupted()&&catalog_gc_and_rebase()?0:1;
}
