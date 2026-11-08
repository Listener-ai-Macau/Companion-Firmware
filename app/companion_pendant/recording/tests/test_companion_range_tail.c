#define COMP_PREFIX_TEST_BASE 65536
#define COMP_PREFIX_TEST_PAYLOAD 40000
#define main legacy_prefix_fixture_main
#include "test_companion_segment_reclaim_prefix.c"
#undef main
#include "companion_range_reclaim.h"

static uint32_t erased_at[128],erased_bytes[128];
static unsigned erased_count;
static bool block_erase(void *v,uint32_t at,uint32_t n,uint32_t *done)
{
    (void)v;calls++;
    if(at!=preview_address||n!=preview_bytes||at%4096u||n<4096u)return false;
    uint32_t amount=at%32768u==0u&&n>=32768u?32768u:4096u;
    if(at>BYTES||amount>BYTES-at||erased_count>=128u)return false;
    erased_at[erased_count]=at;erased_bytes[erased_count++]=amount;
    memset(media+at,255,amount);erases++;*done=amount;return true;
}
static bool prepare_range(comp_segment_catalog_t *c,comp_segment_entry_t *e,
                          comp_range_reclaim_t *worker,uint16_t end)
{
    CHECK(prepare(c,e,NORMAL_FLAGS,false));
    c->reclaim_block_sectors=8u;c->port.erase_step=block_erase;erased_count=0u;
    uint32_t limit=((uint32_t)end*16u-1u)*248u;
    uint8_t sha[32];companion_sha256_t hash;
    companion_sha256_init(&hash);companion_sha256_update(&hash,payload,limit);companion_sha256_final(&hash,sha);
    memset(worker,0,sizeof(*worker));
    CHECK(comp_segment_catalog_range_begin(c,worker,e,0u,0u,end,701u,sha)==COMP_SEG_PENDING);
    CHECK(finish(c)==COMP_SEG_OK&&erased_count==1u);
    return true;
}
static bool begin_tail(comp_segment_catalog_t *c,comp_segment_entry_t *e)
{
    CHECK(comp_segment_catalog_read(c,0u,e)==COMP_SEG_OK);
    e->state=COMP_SEG_ACKED;e->descriptor.sync_state=2u;
    CHECK(comp_segment_catalog_ack_at_begin(c,e,0u)==COMP_SEG_PENDING&&finish(c)==COMP_SEG_OK);
    CHECK(comp_segment_catalog_reclaim_at_begin(c,e,0u)==COMP_SEG_PENDING);
    return true;
}
static bool normal_tail(void)
{
    comp_segment_catalog_t c,rebooted;comp_segment_entry_t e,receipt;comp_range_reclaim_t worker;
    CHECK(prepare_range(&c,&e,&worker,8u));
    CHECK(erased_at[0]==BASE&&erased_bytes[0]==32768u&&!all_blank(BASE+32768u,8192u));
    // Durable full-block proof survives restart. Original tail is still read
    // from its real CSP2 page after provenance and the first block are gone.
    CHECK(mount(&rebooted)==COMP_SEG_OK);rebooted.reclaim_block_sectors=8u;rebooted.port.erase_step=block_erase;
    CHECK(comp_segment_catalog_read(&rebooted,0u,&e)==COMP_SEG_OK&&e.range_end==8u);
    const comp_segment_audio_port_t port={read_audio,program_audio,NULL};uint8_t page[256],length=0u;
    CHECK(comp_segment_audio_read_page(&port,&e,BASE,127u,page,&length)==COMP_SEG_OK&&length==248u);
    CHECK(!memcmp(page,payload+31500u,248u));
    CHECK(begin_tail(&rebooted,&e)&&finish(&rebooted)==COMP_SEG_OK);
    CHECK(erased_count==2u&&erased_at[1]==BASE+32768u&&erased_bytes[1]==32768u);
    CHECK(all_blank(BASE,RESERVED));
    for(unsigned i=0u;i<4096u;i++)CHECK(media[BASE+RESERVED+i]==0x5au);
    CHECK(comp_segment_catalog_receipt_read(&rebooted,0u,&receipt)==COMP_SEG_OK&&receipt.state==0u);
    CHECK(receipt.descriptor.encoded_length==PAYLOAD&&!memcmp(receipt.descriptor.sha256,e.descriptor.sha256,32u));
    puts("PASS_RANGE_TAIL real_CSP2_after_prefix_erase=1 durable_frontier_reboot=1 final_tail_one32K_erase=1 no_duplicate_prefix_erase=1 exact_original_receipt=1 neighbor_unchanged=1");return true;
}
static bool interrupted_tail(void)
{
    comp_segment_catalog_t c,rebooted;comp_segment_entry_t e,receipt;comp_range_reclaim_t worker;
    CHECK(prepare_range(&c,&e,&worker,8u)&&begin_tail(&c,&e));
    for(unsigned i=0u;i<20000u&&erased_count<2u;i++)CHECK(poll(&c)==COMP_SEG_PENDING);
    CHECK(erased_count==2u&&mount(&rebooted)==COMP_SEG_OK);
    rebooted.reclaim_block_sectors=8u;rebooted.port.erase_step=block_erase;
    CHECK(comp_segment_catalog_read(&rebooted,0u,&e)==COMP_SEG_OK&&e.state==COMP_SEG_ERASING&&e.range_end==8u);
    CHECK(comp_segment_catalog_receipt_read(&rebooted,0u,&receipt)==COMP_SEG_NOT_FOUND);
    media[BASE+RESERVED-1u]=0u; // uncertain rebooted suffix retains full cleanup
    CHECK(comp_segment_catalog_reclaim_at_begin(&rebooted,&e,0u)==COMP_SEG_PENDING&&finish(&rebooted)==COMP_SEG_OK);
    for(unsigned i=2u;i<erased_count;i++)CHECK(erased_at[i]>=BASE+32768u);
    CHECK(all_blank(BASE,RESERVED)&&comp_segment_catalog_receipt_read(&rebooted,0u,&receipt)==COMP_SEG_OK);
    for(unsigned i=0u;i<4096u;i++)CHECK(media[BASE+RESERVED+i]==0x5au);
    puts("PASS_RANGE_TAIL_POWER_CUT no_early_receipt=1 persisted_prefix_not_reerased=1 uncertain_suffix_fully_erased=1");return true;
}
static bool legacy_sector_frontier(void)
{
    comp_segment_catalog_t c;comp_segment_entry_t e;comp_range_reclaim_t worker;
    CHECK(prepare_range(&c,&e,&worker,1u)&&begin_tail(&c,&e)&&finish(&c)==COMP_SEG_OK);
    CHECK(erased_count==PREFIX_ERASE/4096u);
    for(unsigned i=0u;i<erased_count;i++)CHECK(erased_bytes[i]==4096u);
    CHECK(all_blank(BASE,RESERVED));
    puts("PASS_RANGE_TAIL_LEGACY subblock_frontier_keeps_sector_exact_path=1");return true;
}
int main(void)
{memset(payload,0x37,sizeof(payload));return normal_tail()&&interrupted_tail()&&legacy_sector_frontier()?0:1;}
