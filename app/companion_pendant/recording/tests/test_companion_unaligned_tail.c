#define COMP_PREFIX_TEST_BASE (65536+28672)
#define COMP_PREFIX_TEST_PAYLOAD 43442
#define main legacy_prefix_fixture_main
#include "test_companion_segment_reclaim_prefix.c"
#undef main
static uint32_t erased_at[80],erased_bytes[80];
static unsigned erased_count;
static bool block_erase(void *v,uint32_t at,uint32_t n,uint32_t *done)
{
    (void)v;calls++;
    if(at!=preview_address||n!=preview_bytes||at%4096u||n<4096u)return false;
    uint32_t amount=at%32768u==0u&&n>=32768u?32768u:4096u;
    if(at>BYTES||amount>BYTES-at||erased_count>=80u)return false;
    erased_at[erased_count]=at;erased_bytes[erased_count++]=amount;
    memset(media+at,255,amount);erases++;*done=amount;return true;
}
static bool begin(comp_segment_catalog_t *c,comp_segment_entry_t *e)
{
    CHECK(prepare(c,e,NORMAL_FLAGS,true));
    c->reclaim_block_sectors=8u;c->port.erase_step=block_erase;erased_count=0;
    CHECK(comp_segment_catalog_reclaim_at_begin(c,e,0u)==COMP_SEG_PENDING);return true;
}
static bool same_unaligned_physical_geometry(void)
{
    comp_segment_catalog_t c;comp_segment_entry_t e,receipt;
    CHECK(begin(&c,&e)&&finish(&c)==COMP_SEG_OK);
    CHECK(erased_count==3u&&erased_at[0]==BASE&&erased_bytes[0]==4096u);
    CHECK(erased_at[1]==BASE+4096u&&erased_bytes[1]==32768u);
    CHECK(erased_at[2]==BASE+36864u&&erased_bytes[2]==32768u);
    CHECK(all_blank(BASE,RESERVED));
    for(unsigned i=0;i<4096u;i++)CHECK(media[BASE+RESERVED+i]==0x5au);
    CHECK(comp_segment_catalog_receipt_read(&c,0,&receipt)==COMP_SEG_OK);
    CHECK(receipt.state==0&&receipt.descriptor.encoded_length==PAYLOAD&&!memcmp(receipt.descriptor.sha256,e.descriptor.sha256,32));
    puts("PASS_UNALIGNED_WHOLE_TAIL same_43442B_base_residue28672=1 one4K_two32K_commands=1 original_receipt=1 exclusive_neighbor_unchanged=1");return true;
}
static bool interrupted_unaligned_tail(void)
{
    comp_segment_catalog_t c,rebooted;comp_segment_entry_t e,receipt;
    CHECK(begin(&c,&e));
    for(unsigned i=0;i<20000&&erased_count<2u;i++)CHECK(poll(&c)==COMP_SEG_PENDING);
    CHECK(erased_count==2u&&mount(&rebooted)==COMP_SEG_OK);
    CHECK(comp_segment_catalog_read(&rebooted,0,&e)==COMP_SEG_OK&&e.state==COMP_SEG_ERASING);
    CHECK(comp_segment_catalog_receipt_read(&rebooted,0,&receipt)==COMP_SEG_NOT_FOUND);
    media[BASE+RESERVED-1u]=0u;
    rebooted.reclaim_block_sectors=8u;rebooted.port.erase_step=block_erase;
    CHECK(comp_segment_catalog_reclaim_at_begin(&rebooted,&e,0)==COMP_SEG_PENDING&&finish(&rebooted)==COMP_SEG_OK);
    CHECK(all_blank(BASE,RESERVED));
    for(unsigned i=0;i<4096u;i++)CHECK(media[BASE+RESERVED+i]==0x5au);
    CHECK(comp_segment_catalog_receipt_read(&rebooted,0,&receipt)==COMP_SEG_OK);
    puts("PASS_UNALIGNED_TAIL_REBOOT no_early_receipt=1 uncertain_suffix_full_cleanup=1 neighbor_unchanged=1");return true;
}
int main(void)
{memset(payload,0x37,sizeof(payload));return same_unaligned_physical_geometry()&&interrupted_unaligned_tail()?0:1;}
