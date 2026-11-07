/* Production catalogue/allocator/adapter/driver over the command-level NOR.
 * This proves ownership and recovery, never electrical erase performance. */
#include "wba_segment_storage.h"
#define COMP_NOR_FIXTURE_BYTES 4194304u
#define main prior_nor_fixture_main
#include "../../../../tools/fixtures/wba_nor_suspend_test.c"
#undef main

enum { BASE=65536, RESERVED=270336, DATA=8*RESERVED+16384,
       PAYLOAD=22610, NORMAL=COMP_REC_V2_SEALED|COMP_REC_V2_LAST|
                    (COMP_REC_END_USER<<COMP_REC_V2_END_SHIFT) };
static const uint8_t uid[12]={1,2,3,4,5,6,7,8,9,10,11,12};
static uint8_t payload[PAYLOAD];
static companion_spi_nor_stm32wba_t make32(void)
{f.sfdp[80]=15;f.sfdp[81]=0x52;return make();}
static comp_segment_result_t finish(comp_wba_segment_storage_t *s,comp_segment_catalog_t *c)
{
    comp_segment_result_t r=COMP_SEG_PENDING;
    for(unsigned i=0;i<20000u&&r==COMP_SEG_PENDING;i++){f.now+=2u;r=comp_wba_segment_storage_catalog_poll(s,c);}
    return r;
}
static void mount(comp_wba_segment_storage_t *s,comp_segment_catalog_t *c)
{
    comp_segment_port_t p=comp_wba_segment_storage_catalog_port(s);
    assert(comp_segment_catalog_mount_begin(c,&p,0,24576,BASE,DATA,uid,7)==COMP_SEG_PENDING);
}
static comp_segment_entry_t entry(comp_segment_catalog_t *c,uint32_t session)
{
    comp_segment_entry_t e={0};e.state=COMP_SEG_WRITING;
    e.descriptor.recording_id=c->next_id;e.descriptor.session_id=session;
    e.descriptor.format_epoch=7;e.descriptor.codec=3;e.descriptor.source_mode=1;
    memcpy(e.descriptor.device_uid,uid,12);return e;
}
static void capabilities_and_owner(void)
{
    reset();companion_spi_nor_stm32wba_t n=make();
    assert(!n.info.erase_32k_supported);
    assert(companion_spi_nor_stm32wba_erase_step(&n,32768,32768)==COMPANION_SPI_NOR_STM32WBA_BAD_PARAM);
    assert(companion_spi_nor_stm32wba_erase_chunk(&n,32768,32768)==4096);
    n=make32();assert(n.info.erase_32k_supported);
    assert(companion_spi_nor_stm32wba_erase_chunk(&n,32768,32768)==32768);
    assert(companion_spi_nor_stm32wba_erase_chunk(&n,0,65536)==65536);
    assert(companion_spi_nor_stm32wba_erase_chunk(&n,4096,65536)==4096);
    memset(f.bytes,0x5a,98304);
    assert(companion_spi_nor_stm32wba_erase_step(&n,32768,32768)==PENDING);
    assert(f.erase_bytes==32768&&f.erases==1&&f.bytes[32768]==0x5a);
    assert(companion_spi_nor_stm32wba_erase_step(&n,32768,4096)==COMPANION_SPI_NOR_STM32WBA_BAD_PARAM);
    suspend(&n);uint8_t b;
    assert(companion_spi_nor_stm32wba_read(&n,0,&b,1)==OK&&b==0x5a);
    assert(!companion_spi_nor_stm32wba_erase_access_ready(&n,32768,1));
    assert(companion_spi_nor_stm32wba_erase_step(&n,32768,32768)==PENDING);
    f.now+=2;assert(companion_spi_nor_stm32wba_erase_step(&n,32768,32768)==PENDING);
    complete();assert(companion_spi_nor_stm32wba_erase_step(&n,32768,32768)==OK);
    assert(f.bytes[32767]==0x5a&&f.bytes[32768]==255&&f.bytes[65535]==255&&f.bytes[65536]==0x5a);
    f.sfdp[81]=0xff;assert(companion_spi_nor_stm32wba_probe(&n,NULL)==OK&&!n.info.erase_32k_supported);
    puts("PASS32 capabilities=SFDP opcode=52 exact_owner=1 suspension=1 neighbors_unchanged=1 reprobe_clears=1");
}
static void placement_capacity(uint32_t old_start,bool next_owner)
{
    unsigned aligned_count=0;
    for(unsigned t=0;t<24u;t++) {
        reset();companion_spi_nor_stm32wba_t n=make32();comp_wba_segment_storage_t s;
        assert(comp_wba_segment_storage_init(&s,&n,0,24576,BASE,DATA));
        comp_segment_catalog_t c;mount(&s,&c);assert(finish(&s,&c)==COMP_SEG_UNFORMATTED);
        assert(comp_segment_catalog_format_blank_begin(&c)==COMP_SEG_PENDING&&finish(&s,&c)==COMP_SEG_OK);
        /* A non-block-aligned existing neighbour remains untouched. */
        comp_segment_entry_t old=entry(&c,1);old.extent_offset=old_start;old.reserved_bytes=4096;
        assert(comp_segment_catalog_put_begin(&c,&old)==COMP_SEG_PENDING&&finish(&s,&c)==COMP_SEG_OK);
        memset(f.bytes+BASE+old_start,0xa5,4096);
        const uint32_t gap_end=next_owner?DATA-8192u:DATA;
        if(next_owner) {
            comp_segment_entry_t next=entry(&c,3);next.extent_offset=gap_end;next.reserved_bytes=4096;
            assert(comp_segment_catalog_put_begin(&c,&next)==COMP_SEG_PENDING&&finish(&s,&c)==COMP_SEG_OK);
            memset(f.bytes+BASE+gap_end,0x6b,4096);
        }
        c.next_id=100u+t;
        comp_segment_entry_t e=entry(&c,2);e.descriptor.recording_id=0;
        comp_segment_reserve_t r={0};assert(comp_segment_reserve_begin_rotated(&r,&c,&e,RESERVED)==COMP_SEG_PENDING);
        comp_segment_result_t result=COMP_SEG_PENDING;
        for(unsigned i=0;i<20000u&&result==COMP_SEG_PENDING;i++)result=comp_wba_segment_storage_reserve_poll(&s,&r);
        const uint32_t gap_start=old_start+4096u;
        assert(result==COMP_SEG_OK&&e.reserved_bytes==RESERVED&&e.extent_offset>=gap_start&&e.extent_offset+RESERVED<=gap_end);
        const uint32_t before=(gap_end-gap_start)/RESERVED;
        const uint32_t after=(e.extent_offset-gap_start)/RESERVED+(gap_end-e.extent_offset-RESERVED)/RESERVED;
        assert(before==after+1u);
        if((BASE+e.extent_offset)%32768u==0u)aligned_count++;
        assert(f.bytes[BASE+old_start]==0xa5&&f.bytes[BASE+old_start+4095u]==0xa5);
        if(next_owner)assert(f.bytes[BASE+gap_end]==0x6b&&f.bytes[BASE+gap_end+4095u]==0x6b);
    }
    printf("PASS32 placement old_start=%u next_owner=%u layouts=24 aligned=%u unchanged_reserved_bytes=1 exact_whole_capacity=1 old_neighbors=1\n",(unsigned)old_start,(unsigned)next_owner,aligned_count);
    assert(aligned_count==24u);
}
static void reclaim_and_power_cut(bool cut)
{
    reset();companion_spi_nor_stm32wba_t n=make32();comp_wba_segment_storage_t s;
    assert(comp_wba_segment_storage_init(&s,&n,0,24576,BASE,DATA));
    comp_segment_catalog_t c;mount(&s,&c);assert(finish(&s,&c)==COMP_SEG_UNFORMATTED);
    assert(comp_segment_catalog_format_blank_begin(&c)==COMP_SEG_PENDING&&finish(&s,&c)==COMP_SEG_OK);
    comp_segment_entry_t e=entry(&c,4);e.descriptor.recording_id=0;
    comp_segment_reserve_t r={0};assert(comp_segment_reserve_begin(&r,&c,&e,RESERVED,0)==COMP_SEG_PENDING);
    comp_segment_result_t result=COMP_SEG_PENDING;
    for(unsigned i=0;i<20000u&&result==COMP_SEG_PENDING;i++)result=comp_wba_segment_storage_reserve_poll(&s,&r);
    assert(result==COMP_SEG_OK);comp_segment_entry_t *owned=NULL;assert(comp_segment_reserve_take(&r,&owned)&&owned==&e);
    comp_segment_audio_port_t ap=comp_wba_segment_storage_audio_port(&s);comp_segment_audio_t a={0};uint8_t page[256];
    assert(comp_segment_audio_prepare_begin(&a,&ap,&e,BASE,page)==COMP_SEG_PENDING);
    do {result=comp_segment_audio_poll(&a);}while(result==COMP_SEG_PENDING);assert(result==COMP_SEG_OK);
    memset(payload,0x37,sizeof(payload));
    for(uint32_t at=0;at<PAYLOAD;) {
        uint8_t count=(uint8_t)(PAYLOAD-at>COMP_SEG_AUDIO_DATA_BYTES?COMP_SEG_AUDIO_DATA_BYTES:PAYLOAD-at);
        assert(comp_segment_audio_append_begin(&a,payload+at,count)==COMP_SEG_PENDING);
        do {result=comp_segment_audio_poll(&a);}while(result==COMP_SEG_PENDING);assert(result==COMP_SEG_OK);at+=count;
    }
    e.state=COMP_SEG_UNSYNCED;e.descriptor.flags=NORMAL;e.descriptor.total_segments=1;e.descriptor.sync_state=1;
    e.descriptor.sample_count=168320;e.descriptor.encoded_length=PAYLOAD;e.descriptor.content_crc32=comp_rec_crc(payload,PAYLOAD);
    companion_sha256_t sha;companion_sha256_init(&sha);companion_sha256_update(&sha,payload,PAYLOAD);companion_sha256_final(&sha,e.descriptor.sha256);
    assert(comp_segment_catalog_put_begin(&c,&e)==COMP_SEG_PENDING&&finish(&s,&c)==COMP_SEG_OK);
    e.state=COMP_SEG_ACKED;e.descriptor.sync_state=2;
    assert(comp_segment_catalog_ack_begin(&c,&e)==COMP_SEG_PENDING&&finish(&s,&c)==COMP_SEG_OK);
    memset(f.bytes+BASE+RESERVED,0xa5,4096);
    assert(comp_segment_catalog_reclaim_begin(&c,&e)==COMP_SEG_PENDING);
    for(unsigned i=0;i<2000u&&!n.erase_active;i++)assert(comp_wba_segment_storage_catalog_poll(&s,&c)==COMP_SEG_PENDING);
    assert(n.erase_active&&n.erase_bytes==32768&&f.erases==1);
    assert(c.phase&&c.pending&&c.pending->descriptor.session_id==4);
    /* Receipt is not exposed before the physical owner finishes. */
    comp_segment_entry_t receipt;
    assert(comp_segment_catalog_receipt_read(&c,0,&receipt)!=COMP_SEG_OK);
    complete();
    if(cut) {
        /* Power loss after physical completion, before any final metadata.
         * The rebooted ERASING row must own the entire original reservation. */
        n=make32();mount(&s,&c);assert(finish(&s,&c)==COMP_SEG_OK);
        assert(comp_segment_catalog_read(&c,0,&e)==COMP_SEG_OK&&e.state==COMP_SEG_ERASING);
        assert(comp_segment_catalog_receipt_read(&c,0,&receipt)!=COMP_SEG_OK);
        f.bytes[BASE+RESERVED-1]=0; /* unknown tail after reboot must not be skipped */
        f.automatic_erase=true;
        assert(comp_segment_catalog_reclaim_begin(&c,&e)==COMP_SEG_PENDING&&finish(&s,&c)==COMP_SEG_OK);
        assert(f.erases>1);
    } else {
        assert(finish(&s,&c)==COMP_SEG_OK&&f.erases==1);
    }
    for(unsigned i=0;i<RESERVED;i++)assert(f.bytes[BASE+i]==255);
    for(unsigned i=0;i<4096;i++)assert(f.bytes[BASE+RESERVED+i]==0xa5);
    mount(&s,&c);assert(finish(&s,&c)==COMP_SEG_OK);
    assert(comp_segment_catalog_receipt_read(&c,0,&receipt)==COMP_SEG_OK&&receipt.descriptor.encoded_length==PAYLOAD);
    printf("PASS32 cut=%u exact_receipt=1 all_owned_blank=1 neighbor=1 remount_receipt=1 erases=%u\n",(unsigned)cut,(unsigned)f.erases);
}
int main(void)
{setvbuf(stdout,NULL,_IONBF,0);capabilities_and_owner();placement_capacity(4096,false);placement_capacity(0,false);placement_capacity(4096,true);placement_capacity(0,true);reclaim_and_power_cut(false);reclaim_and_power_cut(true);return 0;}
