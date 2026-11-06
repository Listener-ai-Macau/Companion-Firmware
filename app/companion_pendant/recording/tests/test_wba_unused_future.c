/* Live ownership/cancellation regression; no hardware timing claim. */
#define COMP_PRODUCT_TEST_MAIN unused_future_fixture_main
#include "test_wba_recording_product.c"

static comp_segment_result_t (*saved_read)(void *,uint32_t,uint8_t *,uint32_t);
static unsigned tail_reads;
static bool occupied(const comp_segment_catalog_t *c)
{for(unsigned i=0u;i<COMP_SEGMENT_CAPACITY;++i)if(c->slots[i]!=255u)return true;return false;}
static uint32_t audio_start;
static comp_segment_result_t count_read(void *v,uint32_t at,uint8_t *p,uint32_t n)
{if(at>=audio_start)tail_reads++;return saved_read(v,at,p,n);}
static comp_segment_entry_t template_entry(void)
{
    comp_segment_entry_t e={0};e.state=COMP_SEG_WRITING;e.descriptor.codec=3u;
    e.descriptor.format_epoch=7u;e.descriptor.session_id=900u;memcpy(e.descriptor.device_uid,device_uid,12u);
    return e;
}
static void reserve_ready(comp_segment_reserve_t *r,comp_segment_entry_t *e,uint32_t bytes)
{
    assert(comp_segment_reserve_begin(r,&catalog,e,bytes,0u)==COMP_SEG_PENDING);
    comp_segment_result_t result=COMP_SEG_PENDING;
    for(unsigned i=0u;i<20000u&&result==COMP_SEG_PENDING;++i){f.now+=2u;result=comp_wba_segment_storage_reserve_poll(&storage,r);}
    assert(result==COMP_SEG_OK);
}
static void fresh_writer(comp_segment_audio_t *w,comp_segment_entry_t *e,uint8_t page[256])
{
    comp_segment_reserve_t r={0};reserve_ready(&r,e,4096u);
    comp_segment_entry_t *owned=NULL;assert(comp_segment_reserve_take(&r,&owned)&&owned==e);
    comp_segment_audio_port_t port=comp_wba_segment_storage_audio_port(&storage);
    assert(comp_segment_audio_prepare_begin(w,&port,e,DATA_BASE,page)==COMP_SEG_PENDING);
    comp_segment_result_t result=COMP_SEG_PENDING;
    for(unsigned i=0u;i<100u&&result==COMP_SEG_PENDING;++i){f.now+=2u;result=comp_segment_audio_poll(w);}
    assert(result==COMP_SEG_OK);audio_start=DATA_BASE+e->extent_offset+256u;
    saved_read=w->port.read;w->port.read=count_read;tail_reads=0u;
}
static comp_segment_result_t finish_cancel(comp_segment_reserve_t *r)
{
    comp_segment_result_t result=COMP_SEG_PENDING;
    for(unsigned i=0u;i<10000u&&result==COMP_SEG_PENDING;++i){f.now+=2u;result=comp_wba_segment_storage_reserve_cancel_poll(&storage,r);}
    return result;
}
static void prepared_cancellation(void)
{
    init();comp_segment_entry_t e=template_entry();comp_segment_audio_t w={0};uint8_t page[256];
    fresh_writer(&w,&e,page);unsigned erases=f.erases;
    w.claimed=true;assert(comp_segment_audio_cancel_fresh_begin(&w,&catalog)==COMP_SEG_BAD_STATE);w.claimed=false;
    assert(comp_segment_audio_cancel_fresh_begin(&w,&catalog)==COMP_SEG_PENDING);
    comp_segment_result_t result=COMP_SEG_PENDING;
    for(unsigned i=0u;i<1000u&&result==COMP_SEG_PENDING;++i){f.now+=2u;result=comp_wba_segment_storage_cancel_poll(&storage,&w);}
    assert(result==COMP_SEG_OK&&w.canceled&&tail_reads==0u&&f.erases==erases&&!occupied(&catalog));
    /* Default cancellation/reboot still detect an unexpected later page. */
    init();e=template_entry();memset(&w,0,sizeof(w));fresh_writer(&w,&e,page);
    f.bytes[audio_start+512u]=0u;
    comp_segment_audio_recovery_t recovered={0};comp_segment_audio_port_t port=comp_wba_segment_storage_audio_port(&storage);
    assert(comp_segment_audio_recover_owned_begin(&recovered,&port,&e,DATA_BASE,page)==COMP_SEG_PENDING);
    result=COMP_SEG_PENDING;
    for(unsigned i=0u;i<100u&&result==COMP_SEG_PENDING;++i)result=comp_segment_audio_recover_poll(&recovered);
    assert(result==COMP_SEG_CORRUPT&&!comp_segment_audio_recovery_empty_verified(&recovered));
    assert(comp_segment_audio_cancel_begin(&w,&catalog)==COMP_SEG_PENDING);result=COMP_SEG_PENDING;
    for(unsigned i=0u;i<100u&&result==COMP_SEG_PENDING;++i)result=comp_segment_audio_poll(&w);
    assert(result==COMP_SEG_CORRUPT&&w.failed&&tail_reads>0u&&occupied(&catalog));
    init();e=template_entry();memset(&w,0,sizeof(w));fresh_writer(&w,&e,page);
    f.bytes[DATA_BASE+e.extent_offset+20u]^=1u;
    assert(comp_segment_audio_cancel_fresh_begin(&w,&catalog)==COMP_SEG_PENDING);
    assert(comp_segment_audio_poll(&w)==COMP_SEG_CORRUPT&&occupied(&catalog));
    puts("PASS fresh unused writer: no second tail scan/erase; claimed writer refused; mismatched provenance and generic/reboot dirty-tail checks retained");
}
static void reservation_cancellation(void)
{
    init();comp_segment_entry_t e=template_entry();comp_segment_reserve_t r={0};
    assert(comp_segment_reserve_begin(&r,&catalog,&e,8192u,0u)==COMP_SEG_PENDING);
    unsigned reads=f.reads,writes=f.writes,erases=f.erases;
    assert(finish_cancel(&r)==COMP_SEG_OK&&!e.descriptor.recording_id&&f.reads==reads&&f.writes==writes&&f.erases==erases);
    init();e=template_entry();memset(&r,0,sizeof(r));memset(f.bytes+DATA_BASE,0x5au,8192u);
    assert(comp_segment_reserve_begin(&r,&catalog,&e,8192u,0u)==COMP_SEG_PENDING);
    while(!catalog.phase){f.now+=2u;assert(comp_wba_segment_storage_reserve_poll(&storage,&r)==COMP_SEG_PENDING);}
    assert(catalog.pending==&e);
    assert(finish_cancel(&r)==COMP_SEG_OK&&!catalog.phase&&!occupied(&catalog)&&!nor.erase_active&&f.erases==0u);
    for(unsigned i=0u;i<8192u;++i)assert(f.bytes[DATA_BASE+i]==0x5au);
    /* An already accepted physical command must finish; no second chunk. */
    init();e=template_entry();memset(&r,0,sizeof(r));memset(f.bytes+DATA_BASE,0x6bu,8192u);f.automatic_erase=false;
    assert(comp_segment_reserve_begin(&r,&catalog,&e,8192u,0u)==COMP_SEG_PENDING);
    for(unsigned i=0u;i<1000u&&!nor.erase_active;++i){f.now+=2u;assert(comp_wba_segment_storage_reserve_poll(&storage,&r)==COMP_SEG_PENDING);}
    assert(nor.erase_active&&nor.erase_address==DATA_BASE&&nor.erase_bytes==4096u);
    erases=f.erases;f.now+=2u;assert(comp_wba_segment_storage_reserve_cancel_poll(&storage,&r)==COMP_SEG_PENDING&&nor.erase_active&&occupied(&catalog));
    complete();assert(finish_cancel(&r)==COMP_SEG_OK&&!nor.erase_active&&!occupied(&catalog)&&f.erases==erases);
    for(unsigned i=4096u;i<8192u;++i)assert(f.bytes[DATA_BASE+i]==0x6bu);
    /* Unknown failed media cannot be retired as a harmless cancellation. */
    init();e=template_entry();memset(&r,0,sizeof(r));memset(f.bytes+DATA_BASE,0x6bu,8192u);f.automatic_erase=false;
    assert(comp_segment_reserve_begin(&r,&catalog,&e,8192u,0u)==COMP_SEG_PENDING);
    for(unsigned i=0u;i<1000u&&!nor.erase_active;++i){f.now+=2u;assert(comp_wba_segment_storage_reserve_poll(&storage,&r)==COMP_SEG_PENDING);}
    f.fail_command=5u;f.now+=2u;assert(comp_wba_segment_storage_reserve_cancel_poll(&storage,&r)==COMP_SEG_IO_ERROR);
    assert(storage.poisoned&&nor.erase_active&&occupied(&catalog));
    assert(comp_wba_segment_storage_reserve_cancel_poll(&storage,&r)==COMP_SEG_BAD_STATE&&occupied(&catalog));
    puts("PASS live reserve cancel: search and pending commit retire without data erase; only exact in-flight chunk settles; next dirty chunk untouched; failed owner retained");
}
static void hint_still_validates(void)
{
    init();comp_segment_entry_t old=template_entry();comp_segment_reserve_t first={0};reserve_ready(&first,&old,8192u);
    comp_segment_entry_t *owned=NULL;assert(comp_segment_reserve_take(&first,&owned));
    memset(f.bytes+DATA_BASE+old.extent_offset,0x71u,old.reserved_bytes);
    comp_segment_entry_t e=template_entry();e.descriptor.session_id++;comp_segment_reserve_t r={0};
    assert(comp_segment_reserve_begin_rotated(&r,&catalog,&e,4096u)==COMP_SEG_PENDING);
    assert(comp_segment_reserve_set_search_hint(&r,old.extent_offset)==COMP_SEG_OK);
    assert(comp_wba_segment_storage_reserve_poll(&storage,&r)==COMP_SEG_PENDING);
    assert(comp_segment_reserve_set_search_hint(&r,0u)==COMP_SEG_BAD_STATE);
    comp_segment_result_t result=COMP_SEG_PENDING;
    for(unsigned i=0u;i<10000u&&result==COMP_SEG_PENDING;++i){f.now+=2u;result=comp_wba_segment_storage_reserve_poll(&storage,&r);}
    assert(result==COMP_SEG_OK&&e.extent_offset>=old.extent_offset+old.reserved_bytes);
    for(unsigned i=0u;i<old.reserved_bytes;++i)assert(f.bytes[DATA_BASE+old.extent_offset+i]==0x71u);
    puts("PASS search hint is advisory only: occupied original remains protected and a live search cannot be rewound");
}
static void catalog_gc_during_cancellation(void)
{
    init();comp_segment_entry_t e=template_entry();comp_segment_reserve_t r={0};reserve_ready(&r,&e,4096u);
    /* Fill the real append bank using distinct reserve/cancel transactions.
     * The cancellation must finish the actual GC erase/commit owner. */
    comp_segment_entry_t other={0};bool kept=false;
    while(catalog.next_slot<COMP_SEGMENT_BANK_BYTES/256u) {
        other=template_entry();other.descriptor.session_id++;
        comp_segment_reserve_t next={0};
        assert(comp_segment_reserve_begin(&next,&catalog,&other,4096u,4096u)==COMP_SEG_PENDING);
        comp_segment_result_t result=COMP_SEG_PENDING;
        for(unsigned i=0u;i<2000u&&result==COMP_SEG_PENDING;++i){f.now+=2u;result=comp_wba_segment_storage_reserve_poll(&storage,&next);}
        assert(result==COMP_SEG_OK);
        if(catalog.next_slot==COMP_SEGMENT_BANK_BYTES/256u){kept=true;break;}
        assert(finish_cancel(&next)==COMP_SEG_OK);
    }
    assert(finish_cancel(&r)==COMP_SEG_OK&&!catalog.phase&&!nor.erase_active&&occupied(&catalog)==kept);
    comp_segment_catalog_t rebooted;comp_segment_port_t port=comp_wba_segment_storage_catalog_port(&storage);
    assert(comp_segment_catalog_mount_begin(&rebooted,&port,0u,24576u,DATA_BASE,65536u,device_uid,7u)==COMP_SEG_PENDING);
    comp_segment_result_t result=COMP_SEG_PENDING;
    for(unsigned i=0u;i<2000u&&result==COMP_SEG_PENDING;++i){f.now+=2u;result=comp_wba_segment_storage_catalog_poll(&storage,&rebooted);}
    assert(result==COMP_SEG_OK&&occupied(&rebooted)==kept);
    for(uint8_t i=0u;i<COMP_SEGMENT_CAPACITY;++i)if(rebooted.slots[i]!=255u) {
        comp_segment_entry_t found;assert(comp_wba_segment_storage_entry(&storage,&rebooted,i,&found)==COMP_SEG_OK);
        assert(kept&&found.descriptor.recording_id==other.descriptor.recording_id);
    }
    puts("PASS cancellation with real append-bank GC: erase/commit owner finishes and reboot sees durable removal");
}
int main(void)
{prepared_cancellation();reservation_cancellation();hint_still_validates();catalog_gc_during_cancellation();return 0;}
