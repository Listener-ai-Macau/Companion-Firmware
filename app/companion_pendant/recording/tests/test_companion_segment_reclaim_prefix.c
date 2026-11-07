#include "companion_segment_audio.h"
#include <stdio.h>

enum { BANK=24576, BASE=2*BANK, RESERVED=270336, DATA=RESERVED+4096,
       BYTES=BASE+DATA, PAYLOAD=22610, PREFIX_ERASE=24576,
       NORMAL_FLAGS=COMP_REC_V2_SEALED|COMP_REC_V2_LAST|(COMP_REC_END_USER<<COMP_REC_V2_END_SHIFT) };
static uint8_t media[BYTES],payload[PAYLOAD];
static unsigned calls,erases;
static uint32_t preview_address,preview_bytes;
static const uint8_t uid[12]={1,2,3,4,5,6,7,8,9,10,11,12};
#define CHECK(x) do {if(!(x)){fprintf(stderr,"FAIL %u %s\n",(unsigned)__LINE__,#x);return false;}}while(0)
static bool read_media(void *v,uint32_t at,uint8_t *p,uint32_t n)
{(void)v;calls++;if(at>BYTES||n>BYTES-at)return false;memcpy(p,media+at,n);return true;}
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
int main(void)
{memset(payload,0x37,sizeof(payload));return normal_and_fallbacks()&&interrupted_reclaim()?0:1;}
