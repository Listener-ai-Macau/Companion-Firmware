#include "companion_segment_audio.h"
#include <stdio.h>

enum { BASE=4096, RESERVED=4096, BYTES=BASE+RESERVED, PAYLOAD=12+42*16 };
typedef struct {
    uint8_t bytes[BYTES];unsigned calls,programs;
    int cut_program,cut_bytes;bool pending;
} media_t;
static media_t media,saved,trial;
static uint8_t payload[PAYLOAD];static unsigned cut_cases;
#define CHECK(x) do {if (!(x)) {fprintf(stderr,"FAIL %u: %s\n",(unsigned)__LINE__,#x);return false;}} while (0)
static comp_segment_result_t read_media(void *v,uint32_t at,uint8_t *p,uint32_t n)
{
    media_t *m=v;m->calls++;
    if (at>BYTES || n>BYTES-at) return COMP_SEG_IO_ERROR;
    if (m->pending) {m->pending=false;return COMP_SEG_PENDING;}
    memcpy(p,m->bytes+at,n);return COMP_SEG_OK;
}
static comp_segment_result_t program_media(void *v,uint32_t at,const uint8_t *p,uint32_t n)
{
    media_t *m=v;m->calls++;
    if (!n || at>BYTES || n>BYTES-at || at/256u!=(at+n-1u)/256u) return COMP_SEG_IO_ERROR;
    if (m->pending) {m->pending=false;return COMP_SEG_PENDING;}
    bool cut=(int)++m->programs==m->cut_program;
    uint32_t count=cut?(uint32_t)m->cut_bytes:n;if (count>n) count=n;
    for (uint32_t i=0u;i<count;i++) {
        if ((m->bytes[at+i]&p[i])!=p[i]) return COMP_SEG_IO_ERROR;
        m->bytes[at+i]&=p[i];
    }
    return cut?COMP_SEG_IO_ERROR:COMP_SEG_OK;
}
static comp_segment_audio_port_t port(media_t *m)
{comp_segment_audio_port_t p={read_media,program_media,m};return p;}
static comp_segment_entry_t entry(void)
{
    comp_segment_entry_t e;memset(&e,0,sizeof(e));e.state=COMP_SEG_WRITING;
    e.extent_offset=0u;e.reserved_bytes=RESERVED;e.started_unix_s=789u;
    e.descriptor.recording_id=9u;e.descriptor.format_epoch=7u;e.descriptor.session_id=6u;
    e.descriptor.segment_index=2u;e.descriptor.sample_offset=640u;e.descriptor.codec=3u;
    for (unsigned i=0u;i<12u;i++) e.descriptor.device_uid[i]=(uint8_t)(i+1u);
    return e;
}
static comp_segment_result_t finish(comp_segment_audio_t *a,media_t *m)
{
    comp_segment_result_t result=COMP_SEG_PENDING;
    for (unsigned i=0u;i<50u && result==COMP_SEG_PENDING;i++) {
        unsigned before=m->calls;result=comp_segment_audio_poll(a);
        if (m->calls-before>1u) return COMP_SEG_BAD_STATE;
    }
    return result;
}
static comp_segment_result_t recover(media_t *m,const comp_segment_entry_t *e,
    uint32_t *bytes,uint32_t *frames,uint32_t *crc,uint8_t sha[32])
{
    uint8_t page[256];comp_segment_audio_recovery_t r={0};comp_segment_audio_port_t p=port(m);
    comp_segment_result_t result=comp_segment_audio_recover_begin(&r,&p,e,BASE,page);
    if (result!=COMP_SEG_PENDING) return result;
    for (unsigned i=0u;i<30u && result==COMP_SEG_PENDING;i++) {
        unsigned before=m->calls;result=comp_segment_audio_recover_poll(&r);
        if (m->calls-before>1u) return COMP_SEG_BAD_STATE;
    }
    if (result==COMP_SEG_OK && !comp_segment_audio_recovered(&r,bytes,frames,crc,sha))
        return COMP_SEG_NOT_FOUND;
    return result;
}
static bool prepare(comp_segment_audio_t *a,comp_segment_entry_t *e,media_t *m,uint8_t page[256])
{
    memset(a,0,sizeof(*a));memset(m,0,sizeof(*m));memset(m->bytes,255,BYTES);
    comp_segment_audio_port_t p=port(m);
    CHECK(comp_segment_audio_prepare_begin(a,&p,e,BASE,page)==COMP_SEG_PENDING);
    CHECK(finish(a,m)==COMP_SEG_OK && a->prepared && a->committed_bytes==0u);
    return true;
}
static void digest(const uint8_t *p,uint32_t bytes,uint8_t out[32])
{companion_sha256_t hash;companion_sha256_init(&hash);companion_sha256_update(&hash,p,bytes);companion_sha256_final(&hash,out);}
static bool normal(void)
{
    uint8_t page[256],sha[32],wanted[32],got_length=0u;uint32_t bytes=0u,frames=0u,crc=0u;
    comp_segment_audio_t a={0};comp_segment_entry_t e=entry();CHECK(prepare(&a,&e,&media,page));
    for (uint32_t at=0u;at<PAYLOAD;) {
        uint8_t n=(uint8_t)(PAYLOAD-at>248u?248u:PAYLOAD-at);
        CHECK(comp_segment_audio_append_begin(&a,payload+at,n)==COMP_SEG_PENDING);
        media.pending=true;uint32_t before=a.committed_bytes;
        CHECK(comp_segment_audio_poll(&a)==COMP_SEG_PENDING && before==a.committed_bytes);
        CHECK(finish(&a,&media)==COMP_SEG_OK);at+=n;
        CHECK(a.committed_bytes==at);
    }
    CHECK(comp_segment_audio_append_begin(&a,payload,1u)==COMP_SEG_BAD_STATE);
    CHECK(recover(&media,&e,&bytes,&frames,&crc,sha)==COMP_SEG_OK);
    digest(payload,PAYLOAD,wanted);
    CHECK(bytes==PAYLOAD && frames==16u && crc==comp_rec_crc(payload,PAYLOAD) && memcmp(sha,wanted,32u)==0);
    comp_segment_audio_port_t p=port(&media);
    CHECK(comp_segment_audio_read_page(&p,&e,BASE,2u,page,&got_length)==COMP_SEG_OK);
    CHECK(got_length==PAYLOAD-496u && memcmp(page,payload+496u,got_length)==0);
    CHECK(comp_segment_audio_capacity(262144u)==253704u);
    saved=media;return true;
}
static bool corruption(void)
{
    uint32_t bytes,frames,crc;uint8_t sha[32];comp_segment_entry_t e=entry();trial=saved;
    trial.bytes[BASE+256+10]^=1u;
    CHECK(recover(&trial,&e,&bytes,&frames,&crc,sha)==COMP_SEG_CORRUPT);
    trial=saved;uint8_t tmp[256];memcpy(tmp,trial.bytes+BASE+256u,256u);
    memcpy(trial.bytes+BASE+256u,trial.bytes+BASE+512u,256u);memcpy(trial.bytes+BASE+512u,tmp,256u);
    CHECK(recover(&trial,&e,&bytes,&frames,&crc,sha)==COMP_SEG_CORRUPT);
    trial=saved;e.descriptor.session_id++;
    CHECK(recover(&trial,&e,&bytes,&frames,&crc,sha)==COMP_SEG_CORRUPT);
    e=entry();trial=saved;memset(trial.bytes+BASE+512u+252u,255,4u);
    CHECK(recover(&trial,&e,&bytes,&frames,&crc,sha)==COMP_SEG_CORRUPT); /* later committed page */
    return true;
}
static bool interrupted(void)
{
    comp_segment_entry_t e=entry();uint8_t page[256],sha[32],wanted[32];uint32_t bytes,frames,crc;
    for (int target=3;target<=4;target++) {
        for (int cut=0;cut<=(target==3?252:4);cut++) {
            comp_segment_audio_t a={0};CHECK(prepare(&a,&e,&trial,page));
            CHECK(comp_segment_audio_append_begin(&a,payload,248u)==COMP_SEG_PENDING);
            trial.cut_program=target;trial.cut_bytes=cut;
            CHECK(finish(&a,&trial)==COMP_SEG_IO_ERROR && a.failed && a.committed_bytes==0u);
            CHECK(comp_segment_audio_append_begin(&a,payload,248u)==COMP_SEG_BAD_STATE);
            comp_segment_result_t r=recover(&trial,&e,&bytes,&frames,&crc,sha);
            if (target==4 && cut==4) {
                /* Error return is uncertain, but the physical full commit is
                 * recoverable after matching provenance/page readback. */
                CHECK(r==COMP_SEG_OK && bytes==12u+42u*5u && frames==5u);
                digest(payload,bytes,wanted);CHECK(memcmp(sha,wanted,32u)==0 && crc==comp_rec_crc(payload,bytes));
            } else CHECK(r==COMP_SEG_NOT_FOUND);
            cut_cases++;
        }
    }
    /* Header-only/partial-first-packet pages do not become empty recordings. */
    comp_segment_audio_t a={0};CHECK(prepare(&a,&e,&trial,page));
    CHECK(comp_segment_audio_append_begin(&a,payload,20u)==COMP_SEG_PENDING);
    CHECK(finish(&a,&trial)==COMP_SEG_OK);
    CHECK(recover(&trial,&e,&bytes,&frames,&crc,sha)==COMP_SEG_NOT_FOUND);
    return true;
}
int main(void)
{
    static const uint8_t header[12]={'C','O','P','1',1u,1u,20u,0u,0x80u,0x3eu,0u,0u};
    memcpy(payload,header,12u);
    for (unsigned f=0u;f<16u;f++) {
        payload[12u+42u*f]=40u;payload[13u+42u*f]=0u;
        for (unsigned i=0u;i<40u;i++) payload[14u+42u*f+i]=(uint8_t)(i+f+1u);
    }
    if (!normal() || !corruption() || !interrupted()) return 1;
    printf("PASS segment physical framing: durable COP1 prefix, identity/page binding, corruption rejected, %u interrupted-program cuts, <=1IO/poll; not board/audio acceptance\n",cut_cases);
    return 0;
}
