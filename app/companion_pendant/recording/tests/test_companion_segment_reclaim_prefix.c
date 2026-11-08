#include "companion_segment_audio.h"
#include <stdio.h>

#ifndef COMP_PREFIX_TEST_BASE
#define COMP_PREFIX_TEST_BASE 49152
#endif
#ifndef COMP_PREFIX_TEST_PAYLOAD
#define COMP_PREFIX_TEST_PAYLOAD 22610
#endif
enum { BANK=24576, BASE=COMP_PREFIX_TEST_BASE, RESERVED=270336, DATA=RESERVED+8192,
       BYTES=BASE+DATA, PAYLOAD=COMP_PREFIX_TEST_PAYLOAD,
       PREFIX_ERASE=((((PAYLOAD+247)/248+1)*256+4095)/4096)*4096,
       NORMAL_FLAGS=COMP_REC_V2_SEALED|COMP_REC_V2_LAST|(COMP_REC_END_USER<<COMP_REC_V2_END_SHIFT) };
static uint8_t media[BYTES],payload[PAYLOAD];
static unsigned calls,erases;
static unsigned fail_read_call;
static uint32_t preview_address,preview_bytes;
static const uint8_t uid[12]={1,2,3,4,5,6,7,8,9,10,11,12};
#define CHECK(x) do {if(!(x)){fprintf(stderr,"FAIL %u %s\n",(unsigned)__LINE__,#x);return false;}}while(0)
static bool read_media(void *v,uint32_t at,uint8_t *p,uint32_t n)
{(void)v;calls++;if(calls==fail_read_call||at>BYTES||n>BYTES-at)return false;memcpy(p,media+at,n);return true;}
static bool program_media(void *v,uint32_t at,const uint8_t *p,uint32_t n)
{
    (void)v;calls++;if(!n||at>BYTES||n>BYTES-at||at/256u!=(at+n-1u)/256u)return false;
    for(uint32_t i=0;i<n;i++){if((media[at+i]&p[i])!=p[i])return false;media[at+i]&=p[i];}
    return true;
}
static bool erase_media(void *v,uint32_t at,uint32_t n,uint32_t *done)
{
    (void)v;calls++;if(at!=preview_address||n!=preview_bytes||at%4096u||n<4096u||at>BYTES-4096u)return false;
    memset(media+at,255,4096);erases++;*done=4096;return true;
}
static comp_segment_result_t read_audio(void *v,uint32_t at,uint8_t *p,uint32_t n)
{return read_media(v,at,p,n)?COMP_SEG_OK:COMP_SEG_IO_ERROR;}
static comp_segment_result_t program_audio(void *v,uint32_t at,const uint8_t *p,uint32_t n)
{return program_media(v,at,p,n)?COMP_SEG_OK:COMP_SEG_IO_ERROR;}
static comp_segment_result_t poll(comp_segment_catalog_t *c)
{
    comp_segment_io_t io;if(comp_segment_catalog_next_io(c,&io)!=COMP_SEG_OK)return COMP_SEG_BAD_STATE;
    preview_address=io.address;preview_bytes=io.bytes;unsigned before=calls;
    comp_segment_result_t r=comp_segment_catalog_poll(c);
    return calls-before<=1u?r:COMP_SEG_BAD_STATE;
}
static comp_segment_result_t finish(comp_segment_catalog_t *c)
{comp_segment_result_t r=COMP_SEG_PENDING;for(unsigned i=0;i<20000u&&r==COMP_SEG_PENDING;i++)r=poll(c);return r;}
static comp_segment_result_t mount(comp_segment_catalog_t *c)
{
    const comp_segment_port_t p={read_media,program_media,erase_media,NULL};
    comp_segment_result_t r=comp_segment_catalog_mount_begin(c,&p,0,BANK,BASE,DATA,uid,7);
    return r==COMP_SEG_PENDING?finish(c):r;
}
static bool all_blank(uint32_t at,uint32_t n)
{for(uint32_t i=0;i<n;i++)if(media[at+i]!=255u)return false;return true;}
static bool audio_finish(comp_segment_audio_t *a)
{
    comp_segment_result_t r=COMP_SEG_PENDING;
    for(unsigned i=0;i<50u&&r==COMP_SEG_PENDING;i++){unsigned before=calls;r=comp_segment_audio_poll(a);CHECK(calls-before<=1u);}
    CHECK(r==COMP_SEG_OK);return true;
}
static bool prepare(comp_segment_catalog_t *c,comp_segment_entry_t *e,uint8_t flags,bool acknowledged)
{
    memset(media,255,sizeof(media));calls=erases=0;
    CHECK(mount(c)==COMP_SEG_UNFORMATTED);
    CHECK(comp_segment_catalog_format_blank_begin(c)==COMP_SEG_PENDING&&finish(c)==COMP_SEG_OK);
    memset(e,0,sizeof(*e));e->state=COMP_SEG_WRITING;e->reserved_bytes=RESERVED;e->started_unix_s=123456;
    e->descriptor.recording_id=c->next_id;e->descriptor.session_id=123;e->descriptor.format_epoch=7;e->descriptor.codec=3;
    memcpy(e->descriptor.device_uid,uid,12);
    CHECK(comp_segment_catalog_put_begin(c,e)==COMP_SEG_PENDING&&finish(c)==COMP_SEG_OK);
    comp_segment_audio_t a={0};uint8_t page[256];const comp_segment_audio_port_t p={read_audio,program_audio,NULL};
    CHECK(comp_segment_audio_prepare_begin(&a,&p,e,BASE,page)==COMP_SEG_PENDING&&audio_finish(&a));
    for(uint32_t at=0;at<PAYLOAD;){uint8_t n=(uint8_t)(PAYLOAD-at>COMP_SEG_AUDIO_DATA_BYTES?COMP_SEG_AUDIO_DATA_BYTES:PAYLOAD-at);
        CHECK(comp_segment_audio_append_begin(&a,payload+at,n)==COMP_SEG_PENDING&&audio_finish(&a));at+=n;}
    CHECK(a.committed_bytes==PAYLOAD&&all_blank(BASE+PREFIX_ERASE,RESERVED-PREFIX_ERASE));
    e->state=COMP_SEG_UNSYNCED;e->descriptor.sync_state=1;e->descriptor.flags=flags;e->descriptor.sample_count=168320;
    e->descriptor.encoded_length=PAYLOAD;e->descriptor.content_crc32=comp_rec_crc(payload,PAYLOAD);
    if(flags&COMP_REC_V2_LAST)e->descriptor.total_segments=1;
    companion_sha256_t sha;companion_sha256_init(&sha);companion_sha256_update(&sha,payload,PAYLOAD);companion_sha256_final(&sha,e->descriptor.sha256);
    CHECK(comp_segment_catalog_put_begin(c,e)==COMP_SEG_PENDING&&finish(c)==COMP_SEG_OK);
    if(acknowledged){e->state=COMP_SEG_ACKED;e->descriptor.sync_state=2;
        CHECK(comp_segment_catalog_ack_begin(c,e)==COMP_SEG_PENDING&&finish(c)==COMP_SEG_OK);}
    memset(media+BASE+RESERVED,0x5a,4096);return true;
}
static bool normal_and_fallbacks(void)
{
    const uint8_t flags[]={NORMAL_FLAGS,COMP_REC_V2_SEALED,
        NORMAL_FLAGS|COMP_REC_V2_RECOVERED,
        COMP_REC_V2_SEALED|COMP_REC_V2_LAST|(COMP_REC_END_FULL<<COMP_REC_V2_END_SHIFT),
        COMP_REC_V2_SEALED|COMP_REC_V2_LAST};
    for(unsigned k=0;k<sizeof(flags);k++){
        comp_segment_catalog_t c,rebooted;comp_segment_entry_t e,receipt;
        CHECK(prepare(&c,&e,flags[k],true));
        if(k)media[BASE+RESERVED-1]=0; /* uncertain/incomplete suffix must be erased */
        CHECK(comp_segment_catalog_reclaim_begin(&c,&e)==COMP_SEG_PENDING&&finish(&c)==COMP_SEG_OK);
        CHECK(erases==(k?RESERVED:PREFIX_ERASE)/4096u&&all_blank(BASE,RESERVED));
        for(unsigned j=0;j<4096;j++)CHECK(media[BASE+RESERVED+j]==0x5a);
        CHECK(comp_segment_catalog_read(&c,0,&receipt)==COMP_SEG_NOT_FOUND);
        CHECK(mount(&rebooted)==COMP_SEG_OK&&comp_segment_catalog_receipt_read(&rebooted,0,&receipt)==COMP_SEG_OK);
        CHECK(receipt.descriptor.encoded_length==PAYLOAD&&receipt.reserved_bytes==RESERVED&&receipt.state==0);
    }
    comp_segment_catalog_t c;comp_segment_entry_t e;
    CHECK(prepare(&c,&e,flags[0],false));media[BASE+RESERVED-1]=0;
    CHECK(comp_segment_catalog_discard_begin(&c,&e,c.generation)==COMP_SEG_PENDING&&finish(&c)==COMP_SEG_OK);
    CHECK(erases==RESERVED/4096u&&all_blank(BASE,RESERVED));
    puts("PASS_PREFIX_RECLAIM real_CSP2=1 short_sectors=6 full_sectors=66 entire_extent_blank=1 neighbor_unchanged=1 incomplete_intermediate_discard_full=1 exact_receipt=1");return true;
}
static bool interrupted_reclaim(void)
{
    comp_segment_catalog_t c,rebooted;comp_segment_entry_t e,loaded,receipt;
    CHECK(prepare(&c,&e,NORMAL_FLAGS,true));
    CHECK(comp_segment_catalog_reclaim_begin(&c,&e)==COMP_SEG_PENDING);
    for(unsigned i=0;i<20000u&&!erases;i++)CHECK(poll(&c)==COMP_SEG_PENDING);
    CHECK(erases==1u); /* power removed here: metadata must still own all space */
    CHECK(mount(&rebooted)==COMP_SEG_OK&&comp_segment_catalog_read(&rebooted,0,&loaded)==COMP_SEG_OK);
    CHECK(loaded.state==COMP_SEG_ERASING&&comp_segment_catalog_receipt_read(&rebooted,0,&receipt)==COMP_SEG_NOT_FOUND);
    media[BASE+RESERVED-1]=0;
    CHECK(comp_segment_catalog_reclaim_begin(&rebooted,&e)==COMP_SEG_PENDING&&finish(&rebooted)==COMP_SEG_BAD_STATE);
    CHECK(mount(&rebooted)==COMP_SEG_OK);
    CHECK(comp_segment_catalog_reclaim_begin(&rebooted,&loaded)==COMP_SEG_PENDING&&finish(&rebooted)==COMP_SEG_OK);
    CHECK(erases==1u+RESERVED/4096u&&all_blank(BASE,RESERVED));
    CHECK(comp_segment_catalog_receipt_read(&rebooted,0,&receipt)==COMP_SEG_OK&&receipt.state==0);
    puts("PASS_INTERRUPTED_PREFIX_RECLAIM erasing_persisted=1 no_early_receipt=1 stale_acked_rejected=1 reboot_full_erase=1 poll_io_max=1");return true;
}
static bool known_slot_scope_and_gc(void)
{
    comp_segment_catalog_t c;comp_segment_entry_t e,other,dummy,receipt,bad;
    CHECK(prepare(&c,&e,NORMAL_FLAGS,false));
    memset(&other,0,sizeof(other));other.state=COMP_SEG_WRITING;other.extent_offset=RESERVED;other.reserved_bytes=4096;
    other.descriptor=e.descriptor;other.descriptor.recording_id=c.next_id;other.descriptor.session_id=999;
    other.descriptor.sample_count=0;other.descriptor.encoded_length=0;other.descriptor.flags=0;
    other.descriptor.total_segments=0;other.descriptor.sync_state=0;other.descriptor.content_crc32=0;memset(other.descriptor.sha256,0,32);
    CHECK(comp_segment_catalog_put_begin(&c,&other)==COMP_SEG_PENDING&&finish(&c)==COMP_SEG_OK);
    other.state=COMP_SEG_UNSYNCED;other.descriptor.sample_count=320;other.descriptor.encoded_length=54;
    other.descriptor.flags=COMP_REC_V2_SEALED;other.descriptor.sync_state=1;other.descriptor.content_crc32=123;memset(other.descriptor.sha256,1,32);
    CHECK(comp_segment_catalog_put_begin(&c,&other)==COMP_SEG_PENDING&&finish(&c)==COMP_SEG_OK);
    while(c.next_slot<95u){
        dummy=other;dummy.state=COMP_SEG_WRITING;dummy.extent_offset=RESERVED+4096;dummy.descriptor.recording_id=c.next_id;
        dummy.descriptor.session_id=c.next_id+1000u;dummy.descriptor.sample_count=0;dummy.descriptor.encoded_length=0;
        dummy.descriptor.flags=0;dummy.descriptor.sync_state=0;dummy.descriptor.content_crc32=0;memset(dummy.descriptor.sha256,0,32);
        CHECK(all_blank(BASE+dummy.extent_offset,4096));
        CHECK(comp_segment_catalog_put_begin(&c,&dummy)==COMP_SEG_PENDING&&finish(&c)==COMP_SEG_OK);
        CHECK(comp_segment_catalog_cancel_unwritten_begin(&c,&dummy)==COMP_SEG_PENDING&&finish(&c)==COMP_SEG_OK);
    }
    CHECK(c.next_slot==95u);e.state=COMP_SEG_ACKED;e.descriptor.sync_state=2;
    CHECK(comp_segment_catalog_ack_at_begin(&c,&e,2)==COMP_SEG_NOT_FOUND);
    CHECK(comp_segment_catalog_ack_at_begin(&c,&e,1)==COMP_SEG_PENDING&&finish(&c)==COMP_SEG_BAD_STATE);
    CHECK(erases==0u&&mount(&c)==COMP_SEG_OK);
    bad=e;bad.descriptor.sha256[0]^=1u;
    CHECK(comp_segment_catalog_ack_at_begin(&c,&bad,0)==COMP_SEG_PENDING&&finish(&c)==COMP_SEG_BAD_STATE);
    CHECK(erases==0u&&mount(&c)==COMP_SEG_OK);
    CHECK(comp_segment_catalog_ack_at_begin(&c,&e,0)==COMP_SEG_PENDING);
    unsigned before=calls;CHECK(poll(&c)==COMP_SEG_PENDING&&calls-before==1u);
    CHECK(c.scan==64u&&finish(&c)==COMP_SEG_OK&&c.next_slot==96u);
    CHECK(comp_segment_catalog_reclaim_at_begin(&c,&e,0)==COMP_SEG_PENDING);fail_read_call=calls+1;
    CHECK(poll(&c)==COMP_SEG_IO_ERROR&&erases==0u);fail_read_call=0;
    CHECK(mount(&c)==COMP_SEG_OK&&comp_segment_catalog_read(&c,0,&receipt)==COMP_SEG_OK&&receipt.state==COMP_SEG_ACKED);
    CHECK(comp_segment_catalog_reclaim_at_begin(&c,&e,0)==COMP_SEG_PENDING&&finish(&c)==COMP_SEG_OK);
    CHECK(erases==(BANK+PREFIX_ERASE)/4096u&&all_blank(BASE,RESERVED));
    CHECK(comp_segment_catalog_read(&c,1,&receipt)==COMP_SEG_OK&&receipt.descriptor.recording_id==other.descriptor.recording_id);
    for(unsigned i=0;i<4096;i++)CHECK(media[BASE+RESERVED+i]==0x5a);
    CHECK(comp_segment_catalog_receipt_read(&c,0,&receipt)==COMP_SEG_OK&&receipt.state==0);
    puts("PASS_KNOWN_SLOT exact_target_read=1 no_unrelated_scan=1 wrong_slot_sha_refused=1 failed_read_no_erase=1 logical_slot_survives_GC=1 other_owner_unchanged=1");return true;
}
int main(void)
{memset(payload,0x37,sizeof(payload));return normal_and_fallbacks()&&interrupted_reclaim()&&known_slot_scope_and_gc()?0:1;}
