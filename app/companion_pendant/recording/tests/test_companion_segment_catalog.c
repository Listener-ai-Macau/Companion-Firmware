#include "companion_segment_catalog.h"
#include "wba_segment_discard_preview.h"
#include "wba_segment_discard_worker.h"
#include "wba_recording_recovery.h"
#include "wba_segment_discard_control.h"
#include "wba_segment_discard_wire.h"
#include <stdio.h>
#include <string.h>

enum { BANK=24576, BASE=2*BANK, DATA=65*4096, BYTES=BASE+DATA };
typedef struct {
    uint8_t bytes[BYTES];
    unsigned callbacks, programs, erases, partial_bytes;
    int cut_at, program_cut_at;
    bool erase_pending;
} media_t;
static media_t media, saved, trial;
static const uint8_t uid[12]={1u,2u,3u,4u,5u,6u,7u,8u,9u,10u,11u,12u};
static unsigned cut_cases;
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"FAIL %s:%u: %s\n",__FILE__,(unsigned)__LINE__,#x); return false; } } while (0)

static bool cut(media_t *m)
{ m->callbacks++; return m->cut_at>=0 && m->callbacks==(unsigned)m->cut_at; }
static bool read_media(void *v,uint32_t at,uint8_t *out,uint32_t n)
{
    media_t *m=v;
    if (at>BYTES || n>BYTES-at || cut(m)) return false;
    memcpy(out,m->bytes+at,n); return true;
}
static bool program_media(void *v,uint32_t at,const uint8_t *p,uint32_t n)
{
    media_t *m=v;
    if (at>BASE || n>BASE-at || n==0u || at/256u!=(at+n-1u)/256u) return false;
    bool stop=cut(m);
    stop=stop || (m->program_cut_at>0 && m->programs+1u==(unsigned)m->program_cut_at);
    uint32_t count=stop && m->partial_bytes<n?m->partial_bytes:n;
    for (uint32_t i=0u;i<count;i++) {
        if ((m->bytes[at+i]&p[i])!=p[i]) return false;
        m->bytes[at+i]&=p[i];
    }
    m->programs++; return !stop;
}
static bool erase_media(void *v,uint32_t at,uint32_t remaining,uint32_t *done)
{
    media_t *m=v; *done=0u;
    if (at%4096u!=0u || remaining<4096u || at>BYTES-4096u) return false;
    bool stop=cut(m);
    if (stop) {
        memset(m->bytes+at,255,m->partial_bytes<4096u?m->partial_bytes:4096u);
        return false;
    }
    if (!m->erase_pending) { m->erase_pending=true; return true; }
    m->erase_pending=false; memset(m->bytes+at,255,4096u); m->erases++; *done=4096u;
    return true;
}
static comp_segment_port_t port(media_t *m)
{ comp_segment_port_t p={read_media,program_media,erase_media,m}; return p; }
static comp_segment_result_t finish(comp_segment_catalog_t *c,media_t *m)
{
    comp_segment_result_t result=COMP_SEG_PENDING;
    for (unsigned i=0u;i<20000u && result==COMP_SEG_PENDING;i++) {
        unsigned before=m->callbacks;
        result=comp_segment_catalog_poll(c);
        if (m->callbacks-before>1u) return COMP_SEG_BAD_STATE;
    }
    return result;
}
static comp_segment_result_t mount(comp_segment_catalog_t *c,media_t *m)
{
    comp_segment_port_t p=port(m); m->cut_at=-1; m->program_cut_at=0; m->erase_pending=false;
    if (comp_segment_catalog_mount_begin(c,&p,0u,BANK,BASE,DATA,uid,7u)!=COMP_SEG_PENDING) return COMP_SEG_BAD_ARGUMENT;
    return finish(c,m);
}
static bool initialize(comp_segment_catalog_t *c)
{
    memset(&media,0,sizeof(media)); memset(media.bytes,255,BYTES); media.cut_at=-1;
    CHECK(mount(c,&media)==COMP_SEG_UNFORMATTED);
    CHECK(media.programs==0u && media.erases==0u);
    CHECK(comp_segment_catalog_format_blank_begin(c)==COMP_SEG_PENDING);
    CHECK(finish(c,&media)==COMP_SEG_OK);
    return true;
}
static comp_segment_entry_t reservation(const comp_segment_catalog_t *c,unsigned index)
{
    comp_segment_entry_t e; memset(&e,0,sizeof(e));
    e.state=COMP_SEG_WRITING; e.extent_offset=index*4096u; e.reserved_bytes=4096u;
    e.started_unix_s=123456u;
    e.descriptor.recording_id=c->next_id; e.descriptor.format_epoch=7u;
    e.descriptor.session_id=100u+index; e.descriptor.codec=3u;
    memcpy(e.descriptor.device_uid,uid,12u); return e;
}
static void sealed(comp_segment_entry_t *e)
{
    e->state=COMP_SEG_UNSYNCED; e->descriptor.sync_state=1u;
    e->descriptor.flags=COMP_REC_V2_SEALED; e->descriptor.sample_count=320u;
    e->descriptor.encoded_length=54u; e->descriptor.content_crc32=0x12345678u;
    for (unsigned i=0u;i<32u;i++) e->descriptor.sha256[i]=(uint8_t)(i+1u);
}
static bool add(comp_segment_catalog_t *c,unsigned index)
{
    comp_segment_entry_t e=reservation(c,index);
    CHECK(comp_segment_catalog_put_begin(c,&e)==COMP_SEG_PENDING);
    CHECK(finish(c,&media)==COMP_SEG_OK);
    memset(media.bytes+BASE+e.extent_offset,0x5a,54u); sealed(&e);
    CHECK(comp_segment_catalog_put_begin(c,&e)==COMP_SEG_PENDING);
    CHECK(finish(c,&media)==COMP_SEG_OK);
    return true;
}
static bool basic_directory(void)
{
    comp_segment_catalog_t c,rebooted; comp_segment_entry_t e;
    uint8_t wire[248]; size_t bytes=0u; comp_rec_v2_page_t page;
    CHECK(initialize(&c));
    volatile size_t context_bytes=sizeof(c);
    CHECK(context_bytes<=512u);
    e=reservation(&c,0u);
    CHECK(comp_segment_catalog_put_begin(&c,&e)==COMP_SEG_PENDING);
    CHECK(finish(&c,&media)==COMP_SEG_OK);
    CHECK(comp_segment_catalog_page(&c,c.generation,42u,0u,wire,sizeof(wire),&bytes)==COMP_SEG_OK);
    CHECK(comp_rec_v2_page_decode(wire,bytes,&page) && page.total==0u && page.count==0u);
    sealed(&e); memset(media.bytes+BASE,0x5a,54u);
    CHECK(comp_segment_catalog_put_begin(&c,&e)==COMP_SEG_PENDING && finish(&c,&media)==COMP_SEG_OK);
    for (unsigned i=1u;i<64u;i++) CHECK(add(&c,i));
    CHECK(c.next_id==65u && media.erases>0u && c.bank_serial>1u);
    for (uint32_t start=0u;start<64u;start+=2u) {
        CHECK(comp_segment_catalog_page(&c,c.generation,42u,start,wire,sizeof(wire),&bytes)==COMP_SEG_OK);
        CHECK(bytes==248u && comp_rec_v2_page_decode(wire,bytes,&page));
        CHECK(page.total==64u && page.start==start && page.count==2u);
        CHECK(page.entries[0].recording_id==start+1u && page.entries[1].recording_id==start+2u);
    }
    unsigned programs=media.programs,erases=media.erases;
    e=reservation(&c,0u);
    CHECK(comp_segment_catalog_put_begin(&c,&e)==COMP_SEG_PENDING);
    CHECK(finish(&c,&media)==COMP_SEG_BAD_STATE); /* overlap does not evict */
    CHECK(c.mounted && media.programs==programs && media.erases==erases);
    e=reservation(&c,64u);
    CHECK(comp_segment_catalog_put_begin(&c,&e)==COMP_SEG_PENDING);
    CHECK(finish(&c,&media)==COMP_SEG_FULL && c.mounted);
    CHECK(media.programs==programs && media.erases==erases);
    CHECK(mount(&rebooted,&media)==COMP_SEG_OK && rebooted.next_id==65u);
    CHECK(comp_segment_catalog_read(&rebooted,0u,&e)==COMP_SEG_OK);
    uint32_t snapshot=rebooted.generation;
    e.state=COMP_SEG_ACKED; e.descriptor.sync_state=2u; e.descriptor.sha256[0]^=1u;
    CHECK(comp_segment_catalog_ack_begin(&rebooted,&e)==COMP_SEG_PENDING);
    CHECK(finish(&rebooted,&media)==COMP_SEG_BAD_STATE && rebooted.mounted);
    CHECK(media.programs==programs && media.erases==erases);
    e.descriptor.sha256[0]^=1u;
    CHECK(comp_segment_catalog_ack_begin(&rebooted,&e)==COMP_SEG_PENDING && finish(&rebooted,&media)==COMP_SEG_OK);
    CHECK(comp_segment_catalog_page(&rebooted,snapshot,42u,0u,wire,sizeof(wire),&bytes)==COMP_SEG_STALE_SNAPSHOT && bytes==0u);
    programs=media.programs;
    CHECK(comp_segment_catalog_ack_begin(&rebooted,&e)==COMP_SEG_PENDING && finish(&rebooted,&media)==COMP_SEG_OK);
    CHECK(media.programs==programs); /* duplicate exact ACK is harmless */
    CHECK(comp_segment_catalog_reclaim_begin(&rebooted,&e)==COMP_SEG_PENDING && finish(&rebooted,&media)==COMP_SEG_OK);
    CHECK(comp_segment_catalog_read(&rebooted,0u,&e)==COMP_SEG_NOT_FOUND);
    for (unsigned i=0u;i<4096u;i++) CHECK(media.bytes[BASE+i]==255u);
    CHECK(mount(&c,&media)==COMP_SEG_OK && c.next_id==65u);
    CHECK(add(&c,0u));
    CHECK(comp_segment_catalog_read(&c,0u,&e)==COMP_SEG_OK && e.descriptor.recording_id==65u);
    e.state=COMP_SEG_UNSYNCED; e.descriptor.sync_state=1u;
    CHECK(comp_segment_catalog_reclaim_begin(&c,&e)==COMP_SEG_BAD_ARGUMENT);
    CHECK(comp_segment_catalog_mount_begin(&rebooted,&(comp_segment_port_t){read_media,program_media,erase_media,&media},
        0u,BANK,BASE,DATA,uid,8u)==COMP_SEG_PENDING);
    CHECK(finish(&rebooted,&media)==COMP_SEG_CORRUPT);
    CHECK(comp_segment_catalog_format_blank_begin(&rebooted)==COMP_SEG_BAD_STATE);
    return true;
}

static bool assert_reboot_ownership(media_t *m,unsigned expected_live,uint32_t id,uint8_t allowed_a,uint8_t allowed_b)
{
    comp_segment_catalog_t c; comp_segment_entry_t e;
    CHECK(mount(&c,m)==COMP_SEG_OK);
    unsigned count=0u; bool found=false;
    for (uint8_t i=0u;i<64u;i++) {
        comp_segment_result_t r=comp_segment_catalog_read(&c,i,&e);
        if (r==COMP_SEG_NOT_FOUND) continue;
        CHECK(r==COMP_SEG_OK); count++;
        if (e.descriptor.recording_id==id) {
            CHECK(e.state==allowed_a || e.state==allowed_b); found=true;
        }
    }
    CHECK(count==expected_live && found);
    return true;
}

static bool torn_append(void)
{
    comp_segment_catalog_t c; comp_segment_entry_t e;
    CHECK(initialize(&c)); CHECK(add(&c,0u));
    CHECK(comp_segment_catalog_read(&c,0u,&e)==COMP_SEG_OK);
    e.state=COMP_SEG_ACKED; e.descriptor.sync_state=2u; saved=media;
    /* Cut every prefix of the body and final commit, including a completed
     * program whose host-side completion was lost. Nothing erases payload. */
    for (unsigned prefix=0u;prefix<=252u;prefix++) {
        trial=saved; CHECK(mount(&c,&trial)==COMP_SEG_OK);
        CHECK(comp_segment_catalog_ack_begin(&c,&e)==COMP_SEG_PENDING);
        trial.program_cut_at=(int)(saved.programs+1u); trial.partial_bytes=prefix;
        CHECK(finish(&c,&trial)==COMP_SEG_IO_ERROR);
        CHECK(trial.programs==saved.programs+1u);
        CHECK(assert_reboot_ownership(&trial,1u,1u,COMP_SEG_UNSYNCED,COMP_SEG_ACKED)); cut_cases++;
    }
    for (unsigned prefix=0u;prefix<=4u;prefix++) {
        trial=saved; CHECK(mount(&c,&trial)==COMP_SEG_OK);
        CHECK(comp_segment_catalog_ack_begin(&c,&e)==COMP_SEG_PENDING);
        trial.program_cut_at=(int)(saved.programs+2u); trial.partial_bytes=prefix;
        CHECK(finish(&c,&trial)==COMP_SEG_IO_ERROR && trial.programs==saved.programs+2u);
        CHECK(assert_reboot_ownership(&trial,1u,1u,COMP_SEG_UNSYNCED,COMP_SEG_ACKED)); cut_cases++;
    }
    return true;
}

static bool cut_gc_and_reclaim(void)
{
    comp_segment_catalog_t c,baseline; comp_segment_entry_t e;
    CHECK(initialize(&c));
    /* 47 reserve/seal pairs occupy 94 append pages. The next mutation starts
     * with GC; this exposes root intent, old-bank erase and copied-row cuts. */
    for (unsigned i=0u;i<47u;i++) CHECK(add(&c,i));
    CHECK(c.next_slot==95u);
    CHECK(comp_segment_catalog_read(&c,0u,&e)==COMP_SEG_OK);
    e.state=COMP_SEG_ACKED; e.descriptor.sync_state=2u;
    CHECK(comp_segment_catalog_ack_begin(&c,&e)==COMP_SEG_PENDING && finish(&c,&media)==COMP_SEG_OK);
    CHECK(c.next_slot==96u);
    CHECK(comp_segment_catalog_read(&c,1u,&e)==COMP_SEG_OK);
    e.state=COMP_SEG_ACKED; e.descriptor.sync_state=2u;
    saved=media; baseline=c;
    CHECK(comp_segment_catalog_ack_begin(&c,&e)==COMP_SEG_PENDING);
    unsigned callback_start=media.callbacks;
    CHECK(finish(&c,&media)==COMP_SEG_OK);
    unsigned callbacks=media.callbacks-callback_start;
    for (unsigned at=1u;at<=callbacks;at++) {
        trial=saved; c=baseline; c.port=port(&trial);
        CHECK(comp_segment_catalog_ack_begin(&c,&e)==COMP_SEG_PENDING);
        trial.cut_at=(int)(trial.callbacks+at); trial.partial_bytes=16u;
        CHECK(finish(&c,&trial)==COMP_SEG_IO_ERROR);
        CHECK(assert_reboot_ownership(&trial,47u,2u,COMP_SEG_UNSYNCED,COMP_SEG_ACKED)); cut_cases++;
    }
    /* Reclaim interrupted at any callback retains ACKED/ERASING ownership or
     * removes only physically blank bytes. No partial erase can become free. */
    CHECK(mount(&c,&media)==COMP_SEG_OK);
    CHECK(comp_segment_catalog_read(&c,1u,&e)==COMP_SEG_OK && e.state==COMP_SEG_ACKED);
    saved=media; baseline=c;
    CHECK(comp_segment_catalog_reclaim_begin(&c,&e)==COMP_SEG_PENDING);
    callback_start=media.callbacks;
    CHECK(finish(&c,&media)==COMP_SEG_OK); callbacks=media.callbacks-callback_start;
    for (unsigned at=1u;at<=callbacks;at++) {
        trial=saved; c=baseline; c.port=port(&trial);
        CHECK(comp_segment_catalog_reclaim_begin(&c,&e)==COMP_SEG_PENDING);
        trial.cut_at=(int)(trial.callbacks+at); trial.partial_bytes=16u;
        CHECK(finish(&c,&trial)==COMP_SEG_IO_ERROR);
        CHECK(mount(&c,&trial)==COMP_SEG_OK);
        comp_segment_entry_t loaded;
        comp_segment_result_t r=comp_segment_catalog_read(&c,1u,&loaded);
        if (r==COMP_SEG_NOT_FOUND) {
            for (unsigned i=0u;i<4096u;i++) CHECK(trial.bytes[BASE+4096u+i]==255u);
        } else {
            CHECK(r==COMP_SEG_OK && (loaded.state==COMP_SEG_ACKED || loaded.state==COMP_SEG_ERASING));
            CHECK(comp_segment_catalog_reclaim_begin(&c,&loaded)==COMP_SEG_PENDING && finish(&c,&trial)==COMP_SEG_OK);
            CHECK(comp_segment_catalog_read(&c,1u,&loaded)==COMP_SEG_NOT_FOUND);
        }
        cut_cases++;
    }
    return true;
}

static bool corrupt_and_blank(void)
{
    comp_segment_catalog_t c;
    CHECK(initialize(&c)); CHECK(add(&c,0u));
    media.bytes[256u+12u]^=1u; /* committed row damage, no rollback to empty */
    CHECK(mount(&c,&media)==COMP_SEG_CORRUPT && !c.mounted);
    CHECK(comp_segment_catalog_format_blank_begin(&c)==COMP_SEG_BAD_STATE);
    memset(media.bytes,255,BYTES); media.bytes[BANK+256u+13u]=0u;
    CHECK(mount(&c,&media)==COMP_SEG_CORRUPT);
    CHECK(comp_segment_catalog_format_blank_begin(&c)==COMP_SEG_BAD_STATE);
    memset(media.bytes,255,BYTES); comp_segment_port_t p=port(&media);
    CHECK(comp_segment_catalog_mount_begin(&c,&p,0u,BANK,BASE,DATA,uid,7u)==COMP_SEG_PENDING);
    media.cut_at=(int)(media.callbacks+4u);
    CHECK(finish(&c,&media)==COMP_SEG_IO_ERROR);
    CHECK(comp_segment_catalog_format_blank_begin(&c)==COMP_SEG_BAD_STATE);
    return true;
}

static bool confirmed_discard_cut_matrix(void)
{
    comp_segment_catalog_t c, baseline, recovered; comp_segment_entry_t e, other, loaded;
    CHECK(initialize(&c)); CHECK(add(&c,0u)); CHECK(add(&c,1u));
    CHECK(comp_segment_catalog_read(&c,0u,&e)==COMP_SEG_OK && e.state==COMP_SEG_UNSYNCED);
    CHECK(comp_segment_catalog_read(&c,1u,&other)==COMP_SEG_OK);
    CHECK(comp_segment_catalog_discard_begin(&c,&e,c.generation-1u)==COMP_SEG_STALE_SNAPSHOT);
    comp_segment_entry_t tampered=e;tampered.descriptor.sha256[0]^=1u;
    CHECK(comp_segment_catalog_discard_begin(&c,&tampered,c.generation)==COMP_SEG_PENDING);
    CHECK(finish(&c,&media)==COMP_SEG_BAD_STATE);
    CHECK(comp_segment_catalog_read(&c,0u,&e)==COMP_SEG_OK);
    saved=media;baseline=c;
    CHECK(comp_segment_catalog_discard_begin(&c,&e,c.generation)==COMP_SEG_PENDING);
    unsigned start=media.callbacks;
    CHECK(finish(&c,&media)==COMP_SEG_OK);
    unsigned callbacks=media.callbacks-start;
    CHECK(comp_segment_catalog_read(&c,0u,&loaded)==COMP_SEG_NOT_FOUND);
    CHECK(comp_segment_catalog_receipt_read(&c,0u,&loaded)==COMP_SEG_NOT_FOUND);
    CHECK(comp_segment_catalog_read(&c,1u,&loaded)==COMP_SEG_OK && loaded.descriptor.recording_id==other.descriptor.recording_id);
    for(unsigned i=0;i<4096u;i++)CHECK(media.bytes[BASE+i]==255u);
    const unsigned partials[]={0u,1u,4u,16u,252u,4096u};
    for(unsigned cutat=1u;cutat<=callbacks;cutat++) for(unsigned pi=0;pi<sizeof(partials)/sizeof(partials[0]);pi++) {
        trial=saved;c=baseline;c.port=port(&trial);
        CHECK(comp_segment_catalog_discard_begin(&c,&e,c.generation)==COMP_SEG_PENDING);
        trial.cut_at=(int)(trial.callbacks+cutat);trial.partial_bytes=partials[pi];
        CHECK(finish(&c,&trial)==COMP_SEG_IO_ERROR);
        CHECK(mount(&recovered,&trial)==COMP_SEG_OK);
        comp_segment_result_t rr=comp_segment_catalog_read(&recovered,0u,&loaded);
        if(rr==COMP_SEG_OK && loaded.state==COMP_SEG_UNSYNCED) {
            CHECK(trial.bytes[BASE]==0x5a); /* no committed intent: no loss */
        } else if(rr==COMP_SEG_OK && loaded.state==COMP_SEG_DISCARDING) {
            CHECK(comp_segment_catalog_discard_begin(&recovered,&loaded,recovered.generation)==COMP_SEG_PENDING);
            CHECK(finish(&recovered,&trial)==COMP_SEG_OK);
            CHECK(comp_segment_catalog_read(&recovered,0u,&loaded)==COMP_SEG_NOT_FOUND);
        } else CHECK(rr==COMP_SEG_NOT_FOUND);
        CHECK(comp_segment_catalog_receipt_read(&recovered,0u,&loaded)==COMP_SEG_NOT_FOUND);
        CHECK(comp_segment_catalog_read(&recovered,1u,&loaded)==COMP_SEG_OK && loaded.descriptor.recording_id==other.descriptor.recording_id);
        CHECK(trial.bytes[BASE+4096u]==0x5a);
    }
    printf("PASS_DISCARD_CUT_MATRIX callbacks=%u partial_variants=6 no_sync_receipt=1 other_preserved=1\n",callbacks);
    return true;
}

static comp_segment_result_t preview_read(void *v,comp_segment_catalog_t *c,uint8_t slot,comp_segment_entry_t *e,comp_segment_discard_intent_t *intent)
{(void)v;return comp_segment_catalog_read_intent(c,slot,e,intent);}
static comp_segment_result_t preview_finish(comp_discard_preview_t *p)
{
    comp_segment_result_t r=COMP_SEG_PENDING;
    for(unsigned i=0;i<200u && r==COMP_SEG_PENDING;i++)r=comp_discard_preview_poll(p);
    return r;
}
static bool add_group_segment(comp_segment_catalog_t *c,unsigned physical,uint64_t session,uint32_t segment,bool last)
{
    comp_segment_entry_t e=reservation(c,physical);e.descriptor.session_id=session;
    e.descriptor.segment_index=segment;e.descriptor.sample_offset=(uint64_t)segment*320u;
    CHECK(comp_segment_catalog_put_begin(c,&e)==COMP_SEG_PENDING && finish(c,&media)==COMP_SEG_OK);
    memset(media.bytes+BASE+e.extent_offset,0x5a,54u);sealed(&e);
    if(last){e.descriptor.flags|=COMP_REC_V2_LAST;e.descriptor.total_segments=segment+1u;}
    CHECK(comp_segment_catalog_put_begin(c,&e)==COMP_SEG_PENDING && finish(c,&media)==COMP_SEG_OK);
    return true;
}
static bool grouped_preview(void)
{
    comp_segment_catalog_t c;comp_discard_preview_t p;comp_segment_entry_t writing;
    CHECK(initialize(&c));CHECK(add_group_segment(&c,0u,100u,0u,false));
    CHECK(add_group_segment(&c,1u,200u,0u,true));CHECK(add_group_segment(&c,2u,100u,1u,true));
    CHECK(comp_discard_preview_begin(&p,&c,preview_read,NULL)==COMP_SEG_PENDING);
    CHECK(preview_finish(&p)==COMP_SEG_OK && p.session_id==100u && p.segments==2u &&
          p.encoded_bytes==108u && p.reserved_bytes==8192u && p.sample_count==640u && p.last_index==1u &&
          p.slots==UINT64_C(5) && p.max_id==3u);
    CHECK(comp_discard_preview_begin(&p,&c,preview_read,NULL)==COMP_SEG_PENDING);
    c.generation++;CHECK(comp_discard_preview_poll(&p)==COMP_SEG_STALE_SNAPSHOT);c.generation--;
    writing=reservation(&c,3u);writing.descriptor.session_id=100u;writing.descriptor.segment_index=2u;
    writing.descriptor.sample_offset=640u;
    CHECK(comp_segment_catalog_put_begin(&c,&writing)==COMP_SEG_PENDING && finish(&c,&media)==COMP_SEG_OK);
    CHECK(comp_discard_preview_begin(&p,&c,preview_read,NULL)==COMP_SEG_PENDING);
    CHECK(preview_finish(&p)==COMP_SEG_BAD_STATE); /* never erase a session still writing */
    CHECK(initialize(&c));CHECK(add_group_segment(&c,0u,100u,0u,false));
    CHECK(comp_discard_preview_begin(&p,&c,preview_read,NULL)==COMP_SEG_PENDING);
    CHECK(preview_finish(&p)==COMP_SEG_BAD_STATE); /* no terminal proof */
    puts("PASS_GROUPED_DISCARD_PREVIEW complete_session=1 stale=1 writing=1 missing_terminal=1");return true;
}

static bool whole_session_intent_matrix(void)
{
    comp_segment_discard_intent_t intent={UINT64_C(5),3u},loaded_intent={0};
    comp_segment_catalog_t c, baseline, rebooted;comp_segment_entry_t anchor,loaded;
    CHECK(initialize(&c));CHECK(add_group_segment(&c,0u,100u,0u,false));
    CHECK(add_group_segment(&c,1u,200u,0u,true));CHECK(add_group_segment(&c,2u,100u,1u,true));
    CHECK(comp_segment_catalog_read(&c,0u,&anchor)==COMP_SEG_OK);
    anchor.state=COMP_SEG_SESSION_DISCARD;
    CHECK(comp_segment_catalog_session_discard_begin(&c,&anchor,&intent,c.generation-1u)==COMP_SEG_STALE_SNAPSHOT);
    comp_segment_entry_t wrong=anchor;comp_segment_discard_intent_t wrong_intent={UINT64_C(4),3u};
    CHECK(comp_segment_catalog_session_discard_begin(&c,&wrong,&wrong_intent,c.generation)==COMP_SEG_PENDING);
    CHECK(finish(&c,&media)==COMP_SEG_BAD_ARGUMENT);
    CHECK(comp_segment_catalog_read(&c,0u,&loaded)==COMP_SEG_OK && loaded.state==COMP_SEG_UNSYNCED);
    saved=media;baseline=c;
    CHECK(comp_segment_catalog_session_discard_begin(&c,&anchor,&intent,c.generation)==COMP_SEG_PENDING);
    unsigned start=media.callbacks;CHECK(finish(&c,&media)==COMP_SEG_OK);unsigned callbacks=media.callbacks-start;
    CHECK(mount(&rebooted,&media)==COMP_SEG_OK);
    CHECK(comp_segment_catalog_read_intent(&rebooted,0u,&loaded,&loaded_intent)==COMP_SEG_OK && loaded.state==COMP_SEG_SESSION_DISCARD &&
          loaded_intent.slots==UINT64_C(5) && loaded_intent.max_id==3u);
    for(unsigned cutat=1u;cutat<=callbacks;cutat++) for(unsigned partial=0u;partial<=252u;partial+=partial?248u:4u) {
        trial=saved;c=baseline;c.port=port(&trial);
        CHECK(comp_segment_catalog_session_discard_begin(&c,&anchor,&intent,c.generation)==COMP_SEG_PENDING);
        trial.cut_at=(int)(trial.callbacks+cutat);trial.partial_bytes=partial;
        CHECK(finish(&c,&trial)==COMP_SEG_IO_ERROR);CHECK(mount(&rebooted,&trial)==COMP_SEG_OK);
        CHECK(comp_segment_catalog_read_intent(&rebooted,0u,&loaded,&loaded_intent)==COMP_SEG_OK);
        CHECK(loaded.state==COMP_SEG_UNSYNCED || (loaded.state==COMP_SEG_SESSION_DISCARD &&
              loaded_intent.slots==UINT64_C(5) && loaded_intent.max_id==3u));
        CHECK(trial.bytes[BASE]==0x5a && trial.bytes[BASE+8192u]==0x5a && trial.bytes[BASE+4096u]==0x5a);
        CHECK(comp_segment_catalog_receipt_read(&rebooted,0u,&loaded)==COMP_SEG_NOT_FOUND);
    }
    /* A changed manifest must fail mount rather than silently narrow or widen intent. */
    trial=media;CHECK(mount(&rebooted,&trial)==COMP_SEG_OK);
    trial.bytes[(unsigned)rebooted.bank*BANK+(unsigned)rebooted.slots[0]*256u+148u]^=1u;
    CHECK(mount(&rebooted,&trial)==COMP_SEG_CORRUPT);
    /* A bank switch copies the committed manifest intact. */
    CHECK(mount(&c,&media)==COMP_SEG_OK);unsigned initial_serial=c.bank_serial;
    for(unsigned i=3u;i<52u;i++)CHECK(add(&c,i));
    CHECK(c.bank_serial>initial_serial);CHECK(mount(&rebooted,&media)==COMP_SEG_OK);
    CHECK(comp_segment_catalog_read_intent(&rebooted,0u,&loaded,&loaded_intent)==COMP_SEG_OK && loaded.state==COMP_SEG_SESSION_DISCARD &&
          loaded_intent.slots==UINT64_C(5) && loaded_intent.max_id==3u);
    printf("PASS_SESSION_INTENT callbacks=%u torn_variants=3 corruption=closed gc=preserved\n",callbacks);
    return true;
}

static comp_segment_result_t worker_poll_catalog(void *v,comp_segment_catalog_t *c)
{(void)v;return comp_segment_catalog_poll(c);}
static comp_segment_result_t worker_finish(comp_discard_worker_t *w)
{
    comp_segment_result_t r=COMP_SEG_PENDING;
    for(unsigned i=0;i<50000u && r==COMP_SEG_PENDING;i++)r=comp_discard_worker_poll(w);
    return r;
}
static bool whole_session_worker_cuts(void)
{
    comp_segment_discard_intent_t intent={UINT64_C(5),3u},loaded_intent={0};
    comp_segment_catalog_t c,base,rebooted;comp_segment_entry_t anchor,loaded;comp_discard_worker_t w;
    CHECK(initialize(&c));CHECK(add_group_segment(&c,0u,100u,0u,false));
    CHECK(add_group_segment(&c,1u,200u,0u,true));CHECK(add_group_segment(&c,2u,100u,1u,true));
    CHECK(comp_segment_catalog_read(&c,0u,&anchor)==COMP_SEG_OK);anchor.state=COMP_SEG_SESSION_DISCARD;
    CHECK(comp_segment_catalog_session_discard_begin(&c,&anchor,&intent,c.generation)==COMP_SEG_PENDING && finish(&c,&media)==COMP_SEG_OK);
    CHECK(comp_segment_catalog_read(&c,0u,&anchor)==COMP_SEG_OK);saved=media;base=c;
    comp_segment_entry_t forged=anchor;comp_segment_discard_intent_t forged_intent=intent;forged_intent.slots|=UINT64_C(2);
    CHECK(comp_discard_worker_resume(&w,&c,preview_read,worker_poll_catalog,NULL,0u,&forged,&forged_intent)==COMP_SEG_PENDING);
    CHECK(worker_finish(&w)==COMP_SEG_BAD_STATE); /* re-read persistent marker before touching any member */
    CHECK(comp_segment_catalog_read(&c,1u,&loaded)==COMP_SEG_OK && loaded.descriptor.session_id==200u);
    CHECK(comp_discard_worker_resume(&w,&c,preview_read,worker_poll_catalog,NULL,0u,&anchor,&intent)==COMP_SEG_PENDING);
    c.generation++;CHECK(comp_discard_worker_poll(&w)==COMP_SEG_STALE_SNAPSHOT);c.generation--;
    CHECK(comp_discard_worker_resume(&w,&c,preview_read,worker_poll_catalog,NULL,0u,&anchor,&intent)==COMP_SEG_PENDING);
    unsigned start=media.callbacks;CHECK(worker_finish(&w)==COMP_SEG_OK);unsigned callbacks=media.callbacks-start;
    CHECK(comp_segment_catalog_read(&c,0u,&loaded)==COMP_SEG_NOT_FOUND);
    CHECK(comp_segment_catalog_read(&c,2u,&loaded)==COMP_SEG_NOT_FOUND);
    CHECK(comp_segment_catalog_read(&c,1u,&loaded)==COMP_SEG_OK && loaded.descriptor.session_id==200u);
    CHECK(comp_segment_catalog_receipt_read(&c,0u,&loaded)==COMP_SEG_NOT_FOUND);
    for(unsigned cutat=1u;cutat<=callbacks;cutat++) {
        trial=saved;c=base;c.port=port(&trial);
        CHECK(comp_discard_worker_resume(&w,&c,preview_read,worker_poll_catalog,NULL,0u,&anchor,&intent)==COMP_SEG_PENDING);
        trial.cut_at=(int)(trial.callbacks+cutat);trial.partial_bytes=16u;
        CHECK(worker_finish(&w)==COMP_SEG_IO_ERROR);
        CHECK(mount(&rebooted,&trial)==COMP_SEG_OK);
        comp_segment_result_t r=comp_segment_catalog_read_intent(&rebooted,0u,&loaded,&loaded_intent);
        if(r==COMP_SEG_OK && loaded.state==COMP_SEG_SESSION_DISCARD) {
            CHECK(comp_discard_worker_resume(&w,&rebooted,preview_read,worker_poll_catalog,NULL,0u,&loaded,&loaded_intent)==COMP_SEG_PENDING);
            CHECK(worker_finish(&w)==COMP_SEG_OK);
        } else if(r==COMP_SEG_OK && loaded.state==COMP_SEG_DISCARDING) {
            comp_segment_entry_t absent;
            CHECK(comp_segment_catalog_read(&rebooted,2u,&absent)==COMP_SEG_NOT_FOUND);
            CHECK(comp_segment_catalog_discard_begin(&rebooted,&loaded,rebooted.generation)==COMP_SEG_PENDING);
            CHECK(finish(&rebooted,&trial)==COMP_SEG_OK);
        } else CHECK(r==COMP_SEG_NOT_FOUND);
        CHECK(comp_segment_catalog_read_intent(&rebooted,0u,&loaded,&loaded_intent)==COMP_SEG_NOT_FOUND);
        CHECK(comp_segment_catalog_read(&rebooted,2u,&loaded)==COMP_SEG_NOT_FOUND);
        CHECK(comp_segment_catalog_read(&rebooted,1u,&loaded)==COMP_SEG_OK && loaded.descriptor.session_id==200u);
        CHECK(comp_segment_catalog_receipt_read(&rebooted,0u,&loaded)==COMP_SEG_NOT_FOUND);
        CHECK(trial.bytes[BASE+4096u]==0x5a);
    }
    printf("PASS_SESSION_WORKER callbacks=%u cut_each=1 other_preserved=1 no_sync_receipt=1\n",callbacks);return true;
}

/* Real recovery controller + catalog with modeled NOR adapter. No microphone
 * recovery is exercised by this fixture; any invocation fails closed. */
comp_segment_result_t comp_wba_segment_storage_entry(comp_wba_segment_storage_t *s,comp_segment_catalog_t *c,uint8_t i,comp_segment_entry_t *e)
{(void)s;return comp_segment_catalog_read(c,i,e);}
comp_segment_result_t comp_wba_segment_storage_entry_intent(comp_wba_segment_storage_t *s,comp_segment_catalog_t *c,uint8_t i,comp_segment_entry_t *e,comp_segment_discard_intent_t *intent)
{(void)s;return comp_segment_catalog_read_intent(c,i,e,intent);}
comp_segment_result_t comp_wba_segment_storage_catalog_poll(comp_wba_segment_storage_t *s,comp_segment_catalog_t *c)
{(void)s;return comp_segment_catalog_poll(c);}
comp_segment_audio_port_t comp_wba_segment_storage_audio_port(comp_wba_segment_storage_t *s)
{(void)s;comp_segment_audio_port_t port={0};return port;}
comp_segment_result_t comp_segment_audio_recover_owned_begin(comp_segment_audio_recovery_t *a,const comp_segment_audio_port_t *p,const comp_segment_entry_t *e,uint32_t b,uint8_t *page)
{(void)a;(void)p;(void)e;(void)b;(void)page;return COMP_SEG_BAD_STATE;}
comp_segment_result_t comp_segment_audio_recover_poll(comp_segment_audio_recovery_t *a)
{(void)a;return COMP_SEG_BAD_STATE;}
bool comp_segment_audio_recovery_empty_verified(const comp_segment_audio_recovery_t *a)
{(void)a;return false;}
bool comp_segment_audio_recovered(const comp_segment_audio_recovery_t *a,uint32_t *b,uint32_t *f,uint32_t *c,uint8_t sha[32])
{(void)a;(void)b;(void)f;(void)c;(void)sha;return false;}
static comp_segment_result_t recovery_finish(comp_wba_recording_recovery_t *r)
{
    comp_segment_result_t result=COMP_SEG_PENDING;
    for(unsigned i=0;i<50000u && result==COMP_SEG_PENDING;i++)result=comp_wba_recording_recovery_poll(r);
    return result;
}
static bool automatic_session_recovery(void)
{
    comp_segment_discard_intent_t intent={UINT64_C(5),3u};
    comp_segment_catalog_t c,base;comp_segment_entry_t anchor,entry;
    companion_spi_nor_stm32wba_t nor={0};comp_wba_segment_storage_t storage={0};
    comp_wba_recording_recovery_t recovery;uint8_t page[256];
    storage.nor=&nor;storage.banks[0]=0u;storage.banks[1]=BANK;storage.data_base=BASE;storage.data_bytes=DATA;
    CHECK(initialize(&c));CHECK(add_group_segment(&c,0u,100u,0u,false));
    CHECK(add_group_segment(&c,1u,200u,0u,true));CHECK(add_group_segment(&c,2u,100u,1u,true));
    CHECK(comp_segment_catalog_read(&c,0u,&anchor)==COMP_SEG_OK);anchor.state=COMP_SEG_SESSION_DISCARD;
    CHECK(comp_segment_catalog_session_discard_begin(&c,&anchor,&intent,c.generation)==COMP_SEG_PENDING && finish(&c,&media)==COMP_SEG_OK);
    saved=media;base=c;
    CHECK(comp_wba_recording_recovery_begin(&recovery,&storage,&c,page)==COMP_SEG_PENDING);
    unsigned start=media.callbacks;CHECK(recovery_finish(&recovery)==COMP_SEG_OK && comp_wba_recording_recovery_ready(&recovery));
    unsigned callbacks=media.callbacks-start;
    CHECK(comp_segment_catalog_read(&c,0u,&entry)==COMP_SEG_NOT_FOUND && comp_segment_catalog_read(&c,2u,&entry)==COMP_SEG_NOT_FOUND);
    CHECK(comp_segment_catalog_read(&c,1u,&entry)==COMP_SEG_OK && entry.descriptor.session_id==200u);
    for(unsigned cutat=1u;cutat<=callbacks;cutat++) {
        trial=saved;c=base;c.port=port(&trial);trial.cut_at=(int)(trial.callbacks+cutat);trial.partial_bytes=16u;
        CHECK(comp_wba_recording_recovery_begin(&recovery,&storage,&c,page)==COMP_SEG_PENDING);
        CHECK(recovery_finish(&recovery)==COMP_SEG_IO_ERROR);
        CHECK(mount(&c,&trial)==COMP_SEG_OK);
        CHECK(comp_wba_recording_recovery_begin(&recovery,&storage,&c,page)==COMP_SEG_PENDING);
        CHECK(recovery_finish(&recovery)==COMP_SEG_OK && comp_wba_recording_recovery_ready(&recovery));
        CHECK(comp_segment_catalog_read(&c,0u,&entry)==COMP_SEG_NOT_FOUND && comp_segment_catalog_read(&c,2u,&entry)==COMP_SEG_NOT_FOUND);
        CHECK(comp_segment_catalog_read(&c,1u,&entry)==COMP_SEG_OK && entry.descriptor.session_id==200u);
        CHECK(comp_segment_catalog_receipt_read(&c,0u,&entry)==COMP_SEG_NOT_FOUND);
    }
    printf("PASS_BOOT_SESSION_RECOVERY callbacks=%u cut_each=1 other_preserved=1 no_sync_receipt=1\n",callbacks);return true;
}

typedef struct {bool locked;unsigned acquired,released,random;} control_fixture_t;
static bool control_random(void *v,uint32_t *out)
{control_fixture_t *f=v;*out=++f->random;return true;}
static bool control_acquire(void *v)
{control_fixture_t *f=v;if(f->locked)return false;f->locked=true;f->acquired++;return true;}
static bool control_release(void *v)
{control_fixture_t *f=v;f->locked=false;f->released++;return true;}
static bool control_make_offer(comp_discard_control_t *ctrl,uint32_t now)
{
    for(unsigned i=0;i<200u && !comp_discard_control_offer(ctrl);i++)
        CHECK(comp_discard_control_poll(ctrl,now)==COMP_SEG_PENDING);
    return comp_discard_control_offer(ctrl)!=NULL;
}
static comp_segment_result_t control_finish(comp_discard_control_t *ctrl,uint32_t now)
{
    comp_segment_result_t r=COMP_SEG_PENDING;
    for(unsigned i=0;i<50000u && r==COMP_SEG_PENDING;i++)r=comp_discard_control_poll(ctrl,now);
    return r;
}
static bool whole_session_control(void)
{
    comp_segment_catalog_t c;comp_segment_entry_t entry;comp_discard_control_t ctrl={0};control_fixture_t f={0};
    comp_discard_control_port_t port={control_random,control_acquire,control_release,preview_read,worker_poll_catalog,&f};
    CHECK(initialize(&c));CHECK(add_group_segment(&c,0u,100u,0u,false));
    CHECK(add_group_segment(&c,1u,200u,0u,true));CHECK(add_group_segment(&c,2u,100u,1u,true));
    CHECK(comp_discard_control_begin(&ctrl,&c,&port,9u,33u)==COMP_SEG_PENDING && control_make_offer(&ctrl,100u));
    comp_discard_offer_t offer=*comp_discard_control_offer(&ctrl), forged=offer;forged.slots|=2u;
    CHECK(comp_discard_control_confirm(&ctrl,9u,101u,&forged)==COMP_SEG_BAD_ARGUMENT && !f.locked);
    CHECK(comp_discard_control_confirm(&ctrl,8u,101u,&offer)==COMP_SEG_BAD_ARGUMENT && !f.locked);
    CHECK(comp_discard_control_confirm(&ctrl,9u,60100u,&offer)==COMP_SEG_BAD_ARGUMENT && !f.locked);
    CHECK(comp_discard_control_cancel(&ctrl,9u) && !f.locked);
    CHECK(comp_segment_catalog_read(&c,0u,&entry)==COMP_SEG_OK && entry.state==COMP_SEG_UNSYNCED);
    CHECK(comp_discard_control_begin(&ctrl,&c,&port,9u,34u)==COMP_SEG_PENDING && control_make_offer(&ctrl,200u));
    offer=*comp_discard_control_offer(&ctrl);
    CHECK(comp_discard_control_confirm(&ctrl,9u,201u,&offer)==COMP_SEG_PENDING && f.locked);
    comp_discard_control_disconnect(&ctrl,9u);CHECK(!f.locked && f.acquired==1u && f.released==1u);
    CHECK(comp_segment_catalog_read(&c,0u,&entry)==COMP_SEG_OK && entry.state==COMP_SEG_UNSYNCED);
    CHECK(comp_discard_control_begin(&ctrl,&c,&port,9u,35u)==COMP_SEG_PENDING && control_make_offer(&ctrl,300u));
    offer=*comp_discard_control_offer(&ctrl);
    CHECK(comp_discard_control_confirm(&ctrl,9u,301u,&offer)==COMP_SEG_PENDING && f.locked);
    for(unsigned i=0;i<200u && !ctrl.commit_started;i++)CHECK(comp_discard_control_poll(&ctrl,301u)==COMP_SEG_PENDING);
    CHECK(ctrl.commit_started && !comp_discard_control_cancel(&ctrl,9u));
    comp_discard_control_disconnect(&ctrl,9u);
    CHECK(control_finish(&ctrl,302u)==COMP_SEG_OK && !f.locked && f.acquired==2u && f.released==2u);
    CHECK(comp_segment_catalog_read(&c,0u,&entry)==COMP_SEG_NOT_FOUND && comp_segment_catalog_read(&c,2u,&entry)==COMP_SEG_NOT_FOUND);
    CHECK(comp_segment_catalog_read(&c,1u,&entry)==COMP_SEG_OK && entry.descriptor.session_id==200u);
    CHECK(comp_segment_catalog_receipt_read(&c,0u,&entry)==COMP_SEG_NOT_FOUND);
    /* An uncertain accepted intent retains exclusive ownership for recovery. */
    CHECK(initialize(&c));CHECK(add_group_segment(&c,0u,100u,0u,true));
    memset(&ctrl,0,sizeof(ctrl));memset(&f,0,sizeof(f));
    CHECK(comp_discard_control_begin(&ctrl,&c,&port,9u,36u)==COMP_SEG_PENDING && control_make_offer(&ctrl,400u));
    offer=*comp_discard_control_offer(&ctrl);
    CHECK(comp_discard_control_confirm(&ctrl,9u,401u,&offer)==COMP_SEG_PENDING);
    for(unsigned i=0;i<200u && !ctrl.commit_started;i++)CHECK(comp_discard_control_poll(&ctrl,401u)==COMP_SEG_PENDING);
    CHECK(ctrl.commit_started && f.locked);media.cut_at=(int)(media.callbacks+1u);media.partial_bytes=4u;
    CHECK(control_finish(&ctrl,402u)==COMP_SEG_IO_ERROR && f.locked && f.released==0u);
    CHECK(comp_discard_control_begin(&ctrl,&c,&port,9u,37u)==COMP_SEG_BAD_STATE);
    puts("PASS_SESSION_CONTROL wrong_peer_token_timeout_cancel_disconnect=1 uncertain_commit_retains_owner=1");return true;
}

static bool discard_wire_codec(void)
{
    comp_discard_offer_t a={0},b;uint8_t p[COMP_DISCARD_V3_BYTES];uint32_t request=0u;
    memcpy(a.uid,uid,12u);a.epoch=7u;a.session=100u;a.slots=5u;a.samples=640u;a.generation=9u;
    a.oldest_id=1u;a.max_id=3u;a.segments=2u;a.encoded_bytes=108u;a.reserved_bytes=8192u;
    a.started_unix_s=123456u;a.last_index=1u;a.token[0]=123u;a.token[1]=456u;a.request_id=35u;a.anchor_slot=0u;
    CHECK(comp_discard_v3_encode(p,COMP_DISCARD_V3_PREVIEW,COMP_DISCARD_V3_OFFER,&a));
    CHECK(comp_discard_v3_decode(p,sizeof(p),COMP_DISCARD_V3_PREVIEW,COMP_DISCARD_V3_OFFER,&b));
    CHECK(b.session==100u && b.slots==5u && b.token[1]==456u && b.segments==2u);
    printf("CDS3_OFFER_HEX=");for(unsigned i=0;i<sizeof(p);i++)printf("%02x",p[i]);puts("");
    p[48]^=1u;CHECK(!comp_discard_v3_decode(p,sizeof(p),COMP_DISCARD_V3_PREVIEW,COMP_DISCARD_V3_OFFER,&b));
    CHECK(!comp_discard_v3_decode(p,84u,COMP_DISCARD_V3_PREVIEW,COMP_DISCARD_V3_OFFER,&b));
    memset(p,0,sizeof(p));memcpy(p,"CDS3",4u);p[4]=COMP_DISCARD_V3_PREVIEW;comp_rec_put32(p+8u,35u);
    comp_rec_put32(p+92u,comp_rec_crc(p,92u));CHECK(comp_discard_v3_preview(p,sizeof(p),&request)&&request==35u);
    p[6]=1u;comp_rec_put32(p+92u,comp_rec_crc(p,92u));CHECK(!comp_discard_v3_preview(p,sizeof(p),&request));
    a.segments=3u;CHECK(!comp_discard_v3_encode(p,COMP_DISCARD_V3_PREVIEW,0u,&a));
    puts("PASS_CDS3_WIRE strict_96b=1 old84_rejected=1 tamper=1");return true;
}

static bool save_fixture(const char *path,const media_t *m)
{
    FILE *f=NULL;CHECK(fopen_s(&f,path,"wb")==0 && f!=NULL);
    CHECK(fwrite(m->bytes,1u,BYTES,f)==BYTES);CHECK(fclose(f)==0);return true;
}
static bool legacy_compaction_cuts(void)
{
    comp_segment_discard_intent_t intent={UINT64_C(5),3u};
    comp_segment_catalog_t c,base,rebooted;comp_segment_entry_t anchor,entry;comp_discard_worker_t w;
    companion_spi_nor_stm32wba_t nor={0};comp_wba_segment_storage_t storage={0};
    comp_wba_recording_recovery_t recovery;uint8_t page[256];
    storage.nor=&nor;storage.banks[0]=0u;storage.banks[1]=BANK;storage.data_base=BASE;storage.data_bytes=DATA;
    CHECK(initialize(&c));CHECK(add_group_segment(&c,0u,100u,0u,false));
    CHECK(add_group_segment(&c,1u,200u,0u,true));CHECK(add_group_segment(&c,2u,100u,1u,true));
    CHECK(comp_segment_catalog_read(&c,0u,&anchor)==COMP_SEG_OK);anchor.state=COMP_SEG_SESSION_DISCARD;
    CHECK(comp_segment_catalog_session_discard_begin(&c,&anchor,&intent,c.generation)==COMP_SEG_PENDING && finish(&c,&media)==COMP_SEG_OK);
    CHECK(comp_segment_catalog_compact_legacy_begin(&c)==COMP_SEG_PENDING);
    CHECK(finish(&c,&media)==COMP_SEG_BAD_STATE && c.legacy_dirty); /* no compaction while intent owns data */
    CHECK(comp_segment_catalog_read(&c,0u,&anchor)==COMP_SEG_OK);
    CHECK(comp_discard_worker_resume(&w,&c,preview_read,worker_poll_catalog,NULL,0u,&anchor,&intent)==COMP_SEG_PENDING);
    CHECK(worker_finish(&w)==COMP_SEG_OK && c.legacy_dirty);
    CHECK(save_fixture(".cache/segmented-discard-20261029/candidate/legacy-before.bin",&media));
    saved=media;base=c;
    CHECK(comp_segment_catalog_compact_legacy_begin(&c)==COMP_SEG_PENDING);
    unsigned start=media.callbacks;CHECK(finish(&c,&media)==COMP_SEG_OK && !c.legacy_dirty);
    unsigned callbacks=media.callbacks-start;
    CHECK(mount(&rebooted,&media)==COMP_SEG_OK && !rebooted.legacy_dirty);
    CHECK(save_fixture(".cache/segmented-discard-20261029/candidate/legacy-after.bin",&media));
    for(unsigned cutat=1u;cutat<=callbacks;cutat++) {
        trial=saved;c=base;c.port=port(&trial);trial.cut_at=(int)(trial.callbacks+cutat);trial.partial_bytes=16u;
        CHECK(comp_segment_catalog_compact_legacy_begin(&c)==COMP_SEG_PENDING);
        CHECK(finish(&c,&trial)==COMP_SEG_IO_ERROR);CHECK(mount(&rebooted,&trial)==COMP_SEG_OK);
        CHECK(comp_wba_recording_recovery_begin(&recovery,&storage,&rebooted,page)==COMP_SEG_PENDING);
        CHECK(recovery_finish(&recovery)==COMP_SEG_OK && !rebooted.legacy_dirty);
        CHECK(comp_segment_catalog_read(&rebooted,1u,&entry)==COMP_SEG_OK && entry.descriptor.session_id==200u);
        CHECK(comp_segment_catalog_receipt_read(&rebooted,0u,&entry)==COMP_SEG_NOT_FOUND);
    }
    printf("PASS_LEGACY_COMPACTION callbacks=%u cut_each=1 boot_retry=1\n",callbacks);return true;
}

int main(void)
{
    if (!basic_directory() || !torn_append() || !cut_gc_and_reclaim() || !corrupt_and_blank() || !confirmed_discard_cut_matrix() || !grouped_preview() || !whole_session_intent_matrix() || !whole_session_worker_cuts() || !automatic_session_recovery() || !whole_session_control() || !discard_wire_codec() || !legacy_compaction_cuts()) return 1;
    printf("PASS_SEGMENT_CATALOG capacity=64 ram_context=%u cut_cases=%u poll_io_max=1\n",
           (unsigned)sizeof(comp_segment_catalog_t),cut_cases);
    return 0;
}
