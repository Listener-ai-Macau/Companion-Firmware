#include "companion_segment_reserve.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#ifndef COMP_SEG_TEST_DATA_SECTORS
#define COMP_SEG_TEST_DATA_SECTORS 16
#endif
enum { BANK=24576, BASE=2*BANK, DATA=COMP_SEG_TEST_DATA_SECTORS*4096, BYTES=BASE+DATA };
static uint8_t media[BYTES];
static unsigned callbacks, erases, programs;
static bool erase_pending, ignore_erase, fail_erase;
static const uint8_t uid[12]={1,2,3,4,5,6,7,8,9,10,11,12};
static bool read_port(void *c,uint32_t at,uint8_t *out,uint32_t n)
{ (void)c;callbacks++;assert(at<=BYTES && n<=BYTES-at);memcpy(out,media+at,n);return true; }
static bool program_port(void *c,uint32_t at,const uint8_t *p,uint32_t n)
{
    (void)c;callbacks++;programs++;assert(at+n<=BASE && n && at/256==(at+n-1)/256);
    for(uint32_t i=0;i<n;i++){assert((media[at+i]&p[i])==p[i]);media[at+i]&=p[i];}return true;
}
static bool erase_port(void *c,uint32_t at,uint32_t bytes,uint32_t *done)
{
    (void)c;callbacks++;*done=0;assert(at%4096==0 && bytes>=4096 && at+4096<=BYTES);
    if(fail_erase){fail_erase=false;return false;}
    if(!erase_pending){erase_pending=true;return true;}
    erase_pending=false;erases++;*done=4096;
    if(!ignore_erase)memset(media+at,255,4096);return true;
}
static comp_segment_result_t finish_catalog(comp_segment_catalog_t *c)
{
    comp_segment_result_t result=COMP_SEG_PENDING;
    for(unsigned i=0;i<20000 && result==COMP_SEG_PENDING;i++){
        unsigned before=callbacks;result=comp_segment_catalog_poll(c);assert(callbacks-before<=1);
    }return result;
}
static void mount(comp_segment_catalog_t *c)
{
    comp_segment_port_t port={read_port,program_port,erase_port,NULL};
    assert(comp_segment_catalog_mount_begin(c,&port,0,BANK,BASE,DATA,uid,7)==COMP_SEG_PENDING);
}
static void setup(comp_segment_catalog_t *c)
{
    memset(media,255,sizeof(media));callbacks=erases=programs=0;erase_pending=ignore_erase=fail_erase=false;
    mount(c);assert(finish_catalog(c)==COMP_SEG_UNFORMATTED);
    assert(comp_segment_catalog_format_blank_begin(c)==COMP_SEG_PENDING);
    assert(finish_catalog(c)==COMP_SEG_OK);
}
static comp_segment_entry_t entry(const comp_segment_catalog_t *c,uint32_t session,uint32_t off,uint32_t n)
{
    comp_segment_entry_t e={0};e.state=COMP_SEG_WRITING;e.extent_offset=off;e.reserved_bytes=n;
    e.descriptor.recording_id=c->next_id;e.descriptor.format_epoch=7;e.descriptor.session_id=session;
    e.descriptor.codec=3;memcpy(e.descriptor.device_uid,uid,12);return e;
}
static void put(comp_segment_catalog_t *c,comp_segment_entry_t *e)
{
    assert(comp_segment_catalog_put_begin(c,e)==COMP_SEG_PENDING);
    assert(finish_catalog(c)==COMP_SEG_OK);
}
static comp_segment_result_t finish_reserve(comp_segment_reserve_t *r)
{
    comp_segment_result_t result=COMP_SEG_PENDING;
    for(unsigned i=0;i<20000 && result==COMP_SEG_PENDING;i++) {
        unsigned before=callbacks;result=comp_segment_reserve_poll(r);assert(callbacks-before<=1);
    }return result;
}
static void gaps_and_ownership(void)
{
    comp_segment_catalog_t c;setup(&c);
    comp_segment_entry_t protected=entry(&c,10,4096,8192);put(&c,&protected);
    memset(media+BASE+4096,0xA5,8192);memset(media+BASE+12288,0x00,8192);
    comp_segment_entry_t e=entry(&c,20,0,0);e.descriptor.recording_id=0;
    comp_segment_reserve_t r={0};
    assert(comp_segment_reserve_begin(&r,&c,&e,8192,0)==COMP_SEG_PENDING);
    assert(finish_reserve(&r)==COMP_SEG_OK && comp_segment_reserve_ready(&r));
    assert(e.extent_offset==12288 && e.reserved_bytes==8192 && e.descriptor.recording_id==2);
    assert(erases==2 && media[BASE+4096]==0xA5 && media[BASE+12288]==255);
    comp_segment_entry_t *taken=NULL;assert(comp_segment_reserve_take(&r,&taken) && taken==&e);
    comp_segment_entry_t next=entry(&c,30,0,0);next.descriptor.recording_id=0;
    assert(comp_segment_reserve_begin(&r,&c,&next,4096,DATA-4096)==COMP_SEG_PENDING);
    assert(finish_reserve(&r)==COMP_SEG_OK && next.extent_offset==DATA-4096);
    puts("PASS allocator: full WRITING extent protected, gap/ring hint chosen, physical blank verification precedes handoff");
}
static void pending_reboot_and_wrap(void)
{
    comp_segment_catalog_t c,rebooted;setup(&c);
    comp_segment_entry_t e=entry(&c,40,0,0);e.descriptor.recording_id=0;
    comp_segment_reserve_t r={0};memset(media+BASE,0xAA,4096);
    assert(comp_segment_reserve_begin(&r,&c,&e,8192,DATA-4096)==COMP_SEG_PENDING);
    while(!erase_pending) {unsigned before=callbacks;assert(comp_segment_reserve_poll(&r)==COMP_SEG_PENDING);assert(callbacks-before<=1);}
    assert(!comp_segment_reserve_ready(&r) && r.cursor==0 && e.extent_offset==0);
    /* A restart finds the durable WRITING reservation even if no erase has
     * completed. Its entire future audio range remains unavailable. */
    erase_pending=false;mount(&rebooted);assert(finish_catalog(&rebooted)==COMP_SEG_OK);
    comp_segment_entry_t persisted;assert(comp_segment_catalog_read(&rebooted,0,&persisted)==COMP_SEG_OK);
    assert(persisted.state==COMP_SEG_WRITING && persisted.reserved_bytes==8192);
    assert(finish_reserve(&r)==COMP_SEG_OK);
    puts("PASS pending/restart: cursor waits for actual erase, wrapping is bounded, durable reservation survives before PCM");
}
static void full_and_failed_erase(void)
{
    comp_segment_catalog_t c;setup(&c);
    comp_segment_entry_t old=entry(&c,50,0,DATA);put(&c,&old);
    unsigned initial=programs;
    comp_segment_entry_t e=entry(&c,60,0,0);e.descriptor.recording_id=0;
    comp_segment_reserve_t r={0};
    assert(comp_segment_reserve_begin(&r,&c,&e,4096,4096)==COMP_SEG_PENDING);
    assert(finish_reserve(&r)==COMP_SEG_FULL && erases==0 && programs==initial);
    setup(&c);memset(&r,0,sizeof(r));e=entry(&c,70,0,0);e.descriptor.recording_id=0;
    memset(media+BASE,0xAA,4096);ignore_erase=true;
    assert(comp_segment_reserve_begin(&r,&c,&e,4096,0)==COMP_SEG_PENDING);
    assert(finish_reserve(&r)==COMP_SEG_CORRUPT && !comp_segment_reserve_ready(&r));
    comp_segment_entry_t persisted;assert(comp_segment_catalog_read(&c,0,&persisted)==COMP_SEG_OK);
    assert(persisted.state==COMP_SEG_WRITING && media[BASE]==0xAA);
    comp_segment_entry_t *taken=NULL;assert(!comp_segment_reserve_take(&r,&taken));
    puts("PASS full/failure: no unsynced eviction, ignored erase caught, failed reservation cannot be silently reused");
}
static void snapshot_restart(void)
{
    comp_segment_catalog_t c;setup(&c);
    comp_segment_entry_t e=entry(&c,80,0,0);e.descriptor.recording_id=0;
    comp_segment_reserve_t r={0};
    assert(comp_segment_reserve_begin(&r,&c,&e,4096,0)==COMP_SEG_PENDING);
    assert(comp_segment_reserve_poll(&r)==COMP_SEG_PENDING);
    comp_segment_entry_t other=entry(&c,90,0,4096);put(&c,&other);
    assert(finish_reserve(&r)==COMP_SEG_OK && e.extent_offset==4096 && e.descriptor.recording_id==2);
    printf("PASS generation changed during scan: no overlap; bounded context=%zu\n",sizeof(r));
}
int main(void)
{ gaps_and_ownership();pending_reboot_and_wrap();full_and_failed_erase();snapshot_restart();return 0; }
