#include "companion_segment_catalog.h"
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
static void dirty_tail_uses_original_erase_and_verify(void)
{
    comp_segment_catalog_t c;observed_setup(&c);comp_segment_entry_t e=fresh(&c,101);comp_segment_reserve_t r={0};
    media[BASE+12288-1]=0;assert(comp_segment_reserve_begin(&r,&c,&e,12288,0)==COMP_SEG_PENDING);
    assert(observed_finish(&r)==COMP_SEG_OK&&erases==3&&data_reads==96);
    for(unsigned i=0;i<12288;i++)assert(media[BASE+i]==255);
    observed_setup(&c);e=fresh(&c,102);memset(&r,0,sizeof(r));media[BASE+4095]=0;ignore_erase=true;
    assert(comp_segment_reserve_begin(&r,&c,&e,4096,0)==COMP_SEG_PENDING);
    assert(observed_finish(&r)==COMP_SEG_CORRUPT&&!comp_segment_reserve_ready(&r));
    assert(erases==1&&media[BASE+4095]==0);
    puts("DIRTY: last-byte mismatch triggers full erase and full reread; ignored erase still fails before READY");
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
    assert(original_allocator_fixture_main()==0);blank_extent_needs_no_erase();dirty_tail_uses_original_erase_and_verify();read_failure_retains_reservation();interrupted_blank_scan_still_owns_whole_range();
    puts("BLANK_PRECHECK_SAME_FULL_PROOF_ONE_IO_NO_EXTRA_OWNER_RAM_HOST_ONLY");return 0;
}
