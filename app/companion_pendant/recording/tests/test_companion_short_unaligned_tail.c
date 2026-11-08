#ifndef COMP_PREFIX_TEST_BASE
#define COMP_PREFIX_TEST_BASE (65536+4096)
#endif
#define COMP_PREFIX_TEST_PAYLOAD 22362
#define main legacy_prefix_fixture_main
#include "test_companion_segment_reclaim_prefix.c"
#undef main
static unsigned small_commands,block_commands;
static bool block_erase(void *v,uint32_t at,uint32_t n,uint32_t *done)
{
    (void)v;calls++;
    if(at!=preview_address||n!=preview_bytes||at%4096u||n<4096u)return false;
    uint32_t amount=at%32768u==0u&&n>=32768u?32768u:4096u;
    if(at<BASE||at+amount>BASE+RESERVED)return false;
    if(amount==4096u)small_commands++;else block_commands++;
    memset(media+at,255,amount);erases++;*done=amount;return true;
}
static bool setup(comp_segment_catalog_t *c,comp_segment_entry_t *e)
{
    CHECK(prepare(c,e,NORMAL_FLAGS,true));c->reclaim_block_sectors=8u;c->port.erase_step=block_erase;
    memset(media+BASE-4096u,0xa5,4096u);small_commands=block_commands=0;
    CHECK(comp_segment_catalog_reclaim_at_begin(c,e,0u)==COMP_SEG_PENDING);return true;
}
static bool neighbors(void)
{
    for(unsigned i=0;i<4096u;i++)CHECK(media[BASE-4096u+i]==0xa5u&&media[BASE+RESERVED+i]==0x5au);
    return true;
}
static bool no_empty_alignment_sector(void)
{
    comp_segment_catalog_t c;comp_segment_entry_t e,receipt;
    CHECK(setup(&c,&e)&&finish(&c)==COMP_SEG_OK);
    printf("SHORT_UNALIGNED actual22362B skew=%u small=%u block=%u reserved=%u\n",BASE%32768u,small_commands,block_commands,RESERVED);
    CHECK(small_commands==6u&&block_commands==0u&&erases==6u);
    CHECK(all_blank(BASE,RESERVED)&&neighbors());
    CHECK(comp_segment_catalog_receipt_read(&c,0,&receipt)==COMP_SEG_OK&&receipt.reserved_bytes==RESERVED);
    CHECK(receipt.descriptor.encoded_length==PAYLOAD&&!memcmp(receipt.descriptor.sha256,e.descriptor.sha256,32u));
    return true;
}
static bool interrupted_remains_full_owner(void)
{
    comp_segment_catalog_t c,rebooted;comp_segment_entry_t e,receipt;
    CHECK(setup(&c,&e));for(unsigned i=0;i<20000u&&!erases;i++)CHECK(poll(&c)==COMP_SEG_PENDING);
    CHECK(erases==1u&&mount(&rebooted)==COMP_SEG_OK);
    CHECK(comp_segment_catalog_read(&rebooted,0,&e)==COMP_SEG_OK&&e.state==COMP_SEG_ERASING);
    CHECK(comp_segment_catalog_receipt_read(&rebooted,0,&receipt)==COMP_SEG_NOT_FOUND);
    media[BASE+RESERVED-1u]=0u;rebooted.reclaim_block_sectors=8u;rebooted.port.erase_step=block_erase;
    CHECK(comp_segment_catalog_reclaim_at_begin(&rebooted,&e,0u)==COMP_SEG_PENDING&&finish(&rebooted)==COMP_SEG_OK);
    CHECK(all_blank(BASE,RESERVED)&&neighbors());
    CHECK(comp_segment_catalog_receipt_read(&rebooted,0,&receipt)==COMP_SEG_OK);
    return true;
}
int main(void)
{
    memset(payload,0x37,sizeof(payload));if(!no_empty_alignment_sector()||!interrupted_remains_full_owner())return 1;
    puts("PASS actual short/unaligned geometry: six necessary4K erases, zero useless boundary sector; full original/receipt/reservation unchanged; both neighbors and full-owner reboot recovery preserved. No hardware timing claim.");return 0;
}
