#include "companion_segment_catalog.h"
#include <stdlib.h>
#define COMP_SEG_TEST_DATA_SECTORS 24
#define main original_allocator_fixture_main
#include "test_companion_segment_reserve.c"
#undef main

static unsigned data_reads,fail_data_read;
static uint32_t last_read_at,last_read_n;
static bool observed_read(void *v,uint32_t at,uint8_t *p,uint32_t n)
{
    last_read_at=at;last_read_n=n;
    if(at>=BASE&&++data_reads==fail_data_read){callbacks++;return false;}
    return read_port(v,at,p,n);
}
static void observed_setup(comp_segment_catalog_t *c)
{setup(c);c->port.read=observed_read;data_reads=fail_data_read=0;last_read_at=last_read_n=0;}
static comp_segment_result_t observed_finish(comp_segment_reserve_t *r)
{
    comp_segment_result_t result=COMP_SEG_PENDING;
    for(unsigned i=0;i<20000&&result==COMP_SEG_PENDING;i++) {
        comp_segment_io_t io;unsigned before=callbacks;
        assert(comp_segment_reserve_next_io(r,&io)==COMP_SEG_OK&&callbacks==before);
        result=comp_segment_reserve_poll(r);assert(callbacks-before<=1);
        if(callbacks!=before&&io.kind==COMP_SEG_IO_READ)assert(last_read_at==io.address&&last_read_n==io.bytes);
    }
    return result;
}
static comp_segment_entry_t fresh(const comp_segment_catalog_t *c,uint32_t session)
{comp_segment_entry_t e=entry(c,session,0,0);e.descriptor.recording_id=0;return e;}
static void blank_extent_needs_no_erase(void)
{
    comp_segment_catalog_t c;observed_setup(&c);comp_segment_entry_t e=fresh(&c,100);comp_segment_reserve_t r={0};
    assert(comp_segment_reserve_begin(&r,&c,&e,8192,0)==COMP_SEG_PENDING);
    assert(observed_finish(&r)==COMP_SEG_OK&&comp_segment_reserve_ready(&r));
    assert(data_reads==32&&erases==0&&r.cursor==8192);
    comp_segment_entry_t persisted;assert(comp_segment_catalog_read(&c,0,&persisted)==COMP_SEG_OK);
    assert(persisted.state==COMP_SEG_WRITING&&persisted.reserved_bytes==8192);
    puts("BLANK: entire8KiB read32 pages once, zero payload erase, durable full WRITING reservation retained before READY");
}
static int dirty_tail_only_erases_its_sector(void)
{
    comp_segment_catalog_t c;observed_setup(&c);comp_segment_entry_t e=fresh(&c,101);comp_segment_reserve_t r={0};
    media[BASE+12288-1]=0;assert(comp_segment_reserve_begin(&r,&c,&e,12288,0)==COMP_SEG_PENDING);
    comp_segment_result_t result=observed_finish(&r);
    if(result!=COMP_SEG_OK||erases!=1||data_reads!=64) {
        fprintf(stderr,"PARTIAL_DIRTY expected1erase/64reads, got result=%d erases=%u reads=%u\n",(int)result,erases,data_reads);
        return 1;
    }
    for(unsigned i=0;i<12288;i++)assert(media[BASE+i]==255);
    observed_setup(&c);e=fresh(&c,102);memset(&r,0,sizeof(r));media[BASE+4095]=0;ignore_erase=true;
    assert(comp_segment_reserve_begin(&r,&c,&e,4096,0)==COMP_SEG_PENDING);
    assert(observed_finish(&r)==COMP_SEG_CORRUPT&&!comp_segment_reserve_ready(&r));
    assert(erases==1&&media[BASE+4095]==0);
    puts("DIRTY: one dirty tail sector erased and fully reread, two blank sectors untouched; ignored erase still fails before READY");
    return 0;
}
static unsigned erased_mask;
static uint32_t bulk_start,bulk_size;
static bool bulk_erase(void *v,uint32_t at,uint32_t n,uint32_t *done)
{
    (void)v;callbacks++;*done=0;
    uint32_t chunk=at%65536u==0u&&n>=65536u?65536u:at%32768u==0u&&n>=32768u?32768u:4096u;
    assert(at>=bulk_start&&at+chunk<=bulk_start+bulk_size);
    if(!erase_pending){erase_pending=true;return true;}
    erase_pending=false;erases++;*done=chunk;memset(media+at,255,chunk);return true;
}
static int dense_runs_retain_bulk_erases(void)
{
    const uint32_t sizes[]={32768u,65536u};
    for(unsigned i=0;i<2;++i) {
        comp_segment_catalog_t c;observed_setup(&c);c.port.erase_step=bulk_erase;
        bulk_start=BASE+16384u;bulk_size=sizes[i];
        memset(media+bulk_start,0,bulk_size);media[bulk_start-1]=0x5A;media[bulk_start+bulk_size]=0xA5;
        comp_segment_entry_t e=fresh(&c,130+i);comp_segment_reserve_t r={0};
        assert(comp_segment_reserve_begin(&r,&c,&e,bulk_size,16384)==COMP_SEG_PENDING);
        comp_segment_result_t result=observed_finish(&r);
        if(result!=COMP_SEG_OK||erases!=1) {
            fprintf(stderr,"DENSE_DIRTY bytes=%lu expected1bulk, got result=%d erases=%u\n",(unsigned long)bulk_size,(int)result,erases);
            return 1;
        }
        for(uint32_t n=0;n<bulk_size;++n)assert(media[bulk_start+n]==255);
        assert(media[bulk_start-1]==0x5A&&media[bulk_start+bulk_size]==0xA5);
    }
    puts("DENSE: contiguous dirty32/64KiB retains one physical bulk command, complete readback and untouched neighbors");
    return 0;
}
static bool mixed_erase(void *v,uint32_t at,uint32_t n,uint32_t *done)
{
    assert(at>=BASE&&at<BASE+12288&&n==4096);
    assert(at!=BASE+4096); /* The proved blank middle sector must be untouched. */
    bool ok=erase_port(v,at,n,done);
    if(ok&&*done)erased_mask|=1u<<((at-BASE)/4096u);
    return ok;
}
static void mixed_sectors_and_partial_restart(void)
{
    comp_segment_catalog_t c,rebooted;observed_setup(&c);erased_mask=0;c.port.erase_step=mixed_erase;
    media[BASE]=0;media[BASE+12287]=0;media[BASE+12288]=0x5A;
    comp_segment_entry_t e=fresh(&c,112);comp_segment_reserve_t r={0};
    assert(comp_segment_reserve_begin(&r,&c,&e,12288,0)==COMP_SEG_PENDING);
    assert(observed_finish(&r)==COMP_SEG_OK&&erases==2&&erased_mask==5&&data_reads==65);
    for(unsigned i=0;i<12288;++i)assert(media[BASE+i]==255);
    assert(media[BASE+12288]==0x5A);

    observed_setup(&c);media[BASE]=0;media[BASE+12287]=0;e=fresh(&c,113);memset(&r,0,sizeof r);
    assert(comp_segment_reserve_begin(&r,&c,&e,12288,0)==COMP_SEG_PENDING);
    for(unsigned i=0;i<2000&&(erases!=1||r.cursor!=256u);++i)assert(comp_segment_reserve_poll(&r)==COMP_SEG_PENDING);
    assert(erases==1&&data_reads==18&&!comp_segment_reserve_ready(&r));
    mount(&rebooted);assert(finish_catalog(&rebooted)==COMP_SEG_OK);
    comp_segment_entry_t persisted;assert(comp_segment_catalog_read(&rebooted,0,&persisted)==COMP_SEG_OK);
    assert(persisted.state==COMP_SEG_WRITING&&persisted.extent_offset==0&&persisted.reserved_bytes==12288);
    comp_segment_entry_t other=fresh(&rebooted,114);comp_segment_reserve_t next={0};
    assert(comp_segment_reserve_begin(&next,&rebooted,&other,4096,0)==COMP_SEG_PENDING);
    assert(finish_reserve(&next)==COMP_SEG_OK&&other.extent_offset==12288&&media[BASE+12287]==0);
    puts("MIXED: only dirty first/tail sectors erased, blank middle and neighbor retained; restart during sector verification retains complete12KiB ownership");
}
static void read_failure_retains_reservation(void)
{
    const unsigned cuts[]={1,16,32};
    for(unsigned i=0;i<3;i++) {
        comp_segment_catalog_t c;observed_setup(&c);comp_segment_entry_t e=fresh(&c,103+i);comp_segment_reserve_t r={0};
        fail_data_read=cuts[i];assert(comp_segment_reserve_begin(&r,&c,&e,8192,0)==COMP_SEG_PENDING);
        assert(observed_finish(&r)==COMP_SEG_IO_ERROR&&erases==0&&!comp_segment_reserve_ready(&r));
        comp_segment_entry_t *taken=NULL;assert(!comp_segment_reserve_take(&r,&taken));
        comp_segment_entry_t persisted;assert(comp_segment_catalog_read(&c,0,&persisted)==COMP_SEG_OK);
        assert(persisted.state==COMP_SEG_WRITING&&persisted.reserved_bytes==8192);
        unsigned before=callbacks;assert(comp_segment_reserve_poll(&r)==COMP_SEG_BAD_STATE&&callbacks==before);
        comp_segment_entry_t fresh_attempt=fresh(&c,120+i);
        assert(comp_segment_reserve_begin(&r,&c,&fresh_attempt,8192,0)==COMP_SEG_BAD_STATE);
    }
    puts("READ_FAILURE: first/middle/last read cannot authorize READY or erase/reuse; persisted full ownership survives");
}
static void interrupted_blank_scan_still_owns_whole_range(void)
{
    comp_segment_catalog_t c,rebooted;observed_setup(&c);comp_segment_entry_t e=fresh(&c,110);comp_segment_reserve_t r={0};
    assert(comp_segment_reserve_begin(&r,&c,&e,8192,0)==COMP_SEG_PENDING);
    for(unsigned i=0;i<2000&&data_reads<7;i++)assert(comp_segment_reserve_poll(&r)==COMP_SEG_PENDING);
    assert(data_reads==7&&!comp_segment_reserve_ready(&r));mount(&rebooted);assert(finish_catalog(&rebooted)==COMP_SEG_OK);
    comp_segment_entry_t persisted;assert(comp_segment_catalog_read(&rebooted,0,&persisted)==COMP_SEG_OK);
    assert(persisted.state==COMP_SEG_WRITING&&persisted.reserved_bytes==8192);
    comp_segment_entry_t other=fresh(&rebooted,111);comp_segment_reserve_t next={0};
    assert(comp_segment_reserve_begin(&next,&rebooted,&other,8192,0)==COMP_SEG_PENDING);
    assert(finish_reserve(&next)==COMP_SEG_OK&&other.extent_offset==8192);
    puts("REBOOT: interrupted precheck does not release partial range; next reservation avoids the whole8KiB");
}
int main(void)
{
#if defined(_MSC_VER)
    _set_error_mode(_OUT_TO_STDERR);
#endif
    assert(original_allocator_fixture_main()==0);blank_extent_needs_no_erase();if(dirty_tail_only_erases_its_sector()||dense_runs_retain_bulk_erases())return 1;mixed_sectors_and_partial_restart();read_failure_retains_reservation();interrupted_blank_scan_still_owns_whole_range();
    puts("BLANK_PRECHECK_SAME_FULL_PROOF_ONE_IO_NO_EXTRA_OWNER_RAM_HOST_ONLY");return 0;
}
