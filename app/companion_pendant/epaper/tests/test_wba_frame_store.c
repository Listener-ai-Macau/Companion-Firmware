#include "wba_frame_store.h"
#include "ssd1681_wba.h"
#include "screen_presenter_wba.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do{if(!(x)){fprintf(stderr,"FAIL line=%d: %s\n",__LINE__,#x);return 1;}}while(0)
size_t reference_frame_size(const uint8_t frame[5000]);
bool reference_frame_write(comp_wba_frame_store_t *,const uint8_t frame[5000]);
static uint8_t frame[5000],decoded[5000],old[5000],next[5000];
static comp_wba_frame_store_t store,saved;
typedef struct {uint32_t now,busy_until,calls,fail_at,visible,failed;FILE *trace;const uint8_t *image;} fixture_t;
static bool transfer(void *v,bool data,const uint8_t *bytes,uint16_t n)
{
    fixture_t *f=v;uint8_t header[7]={(uint8_t)data,(uint8_t)n,(uint8_t)(n>>8),
        (uint8_t)f->now,(uint8_t)(f->now>>8),(uint8_t)(f->now>>16),(uint8_t)(f->now>>24)};
    ++f->calls;
    if(f->fail_at==f->calls)return false;
    if(f->trace && (fwrite(header,1,sizeof(header),f->trace)!=sizeof(header)||fwrite(bytes,1,n,f->trace)!=n))return false;
    if(!data && n==1u && (bytes[0]==0x12u || bytes[0]==0x20u))f->busy_until=f->now+4u;
    return true;
}
static bool reset(void *v,bool asserted){(void)v;(void)asserted;return true;}
static bool busy(void *v){fixture_t *f=v;return f->now<f->busy_until;}
static uint32_t now(void *v){return ((fixture_t *)v)->now;}
static bool render(void *v,const comp_runtime_frame_t *r,uint8_t *pixels)
{(void)r;memcpy(pixels,((fixture_t *)v)->image,5000u);return true;}
static void complete(void *v,uint32_t token,bool visible,uint32_t tick)
{(void)token;(void)tick;fixture_t *f=v;if(visible)++f->visible;else ++f->failed;}
static comp_ssd1681_wba_config_t config(fixture_t *f)
{
    comp_ssd1681_wba_config_t c={0};c.transfer=transfer;c.set_reset=reset;
    c.is_busy=busy;c.now_ms=now;c.context=f;c.payload_chunk_bytes=64u;c.busy_timeout_ms=5000u;c.partial_limit=255u;return c;
}
static bool drive(comp_ssd1681_wba_t *p,fixture_t *f)
{
    for(unsigned i=0u;i<20000u;++i) {
        if(comp_ssd1681_wba_poll(p)!=COMP_SSD1681_WBA_ACTIVE)return p->status==COMP_SSD1681_WBA_COMPLETE;
        ++f->now;
    }
    return false;
}
static bool flips(uint8_t *data)
{
    for(unsigned y=0u;y<100u;++y)for(unsigned x=0u;x<25u;++x){uint8_t a=data[y*25u+x];data[y*25u+x]=data[(199u-y)*25u+x];data[(199u-y)*25u+x]=a;}
    return true;
}
static int roundtrips(const char *path,unsigned *cases,size_t *maximum)
{
    FILE *input=fopen(path,"rb");CHECK(input);
    while(fread(frame,1,sizeof(frame),input)==sizeof(frame)) {
        for(unsigned flipped=0u;flipped<2u;++flipped) {
            if(flipped)CHECK(flips(frame));
            const size_t n=comp_wba_frame_store_size(frame);if(n>*maximum)*maximum=n;
            CHECK(n<=COMP_WBA_FRAME_STORE_BYTES);CHECK(comp_wba_frame_store_write(&store,frame));
            comp_wba_frame_store_t reference={0};CHECK(n==reference_frame_size(frame));CHECK(reference_frame_write(&reference,frame));CHECK(reference.bit_length==store.bit_length && !memcmp(reference.bytes,store.bytes,n));
            CHECK(comp_wba_frame_store_read(&store,0u,decoded,5000u));CHECK(!memcmp(frame,decoded,5000u));
            for(unsigned j=0u;j<43u;++j) {
                const size_t at=(j*337u+5000u-13u)%5000u;const size_t count=5000u-at<37u?5000u-at:37u;
                CHECK(comp_wba_frame_store_read(&store,at,decoded,count));CHECK(!memcmp(frame+at,decoded,count));
            }
            ++*cases;
        }
    }
    CHECK(!ferror(input));CHECK(fclose(input)==0);return 0;
}
static int wire_trace(const char *path,bool packed)
{
    fixture_t f={0};f.trace=fopen(path,"wb");CHECK(f.trace);
    comp_ssd1681_wba_t p;comp_ssd1681_wba_config_t c=config(&f);CHECK(comp_ssd1681_wba_init(&p,&c));
    memset(old,255u,sizeof(old));for(unsigned y=30u;y<120u;++y)old[y*25u+8u]=0u;
    CHECK(comp_wba_frame_store_write(&store,old));
    if(packed)CHECK(comp_ssd1681_wba_bind_old_store(&p,&store));
    const uint8_t *previous=packed?store.bytes:old;
    CHECK(comp_ssd1681_wba_start_full(&p,previous,old,5000u));CHECK(drive(&p,&f));
    const comp_ssd1681_wba_window_t full={0u,24u,0u,199u};
    for(unsigned kind=0u;kind<5u;++kind) {
        memcpy(next,old,sizeof(next));next[(70u+kind)*25u+9u]^=0x3cu;
        bool started=kind==0u?comp_ssd1681_wba_start_partial_pair(&p,previous,next,5000u,&full):
            kind==1u?comp_ssd1681_wba_start_fast_pair(&p,previous,next,5000u):
            kind==2u?comp_ssd1681_wba_start_blink_open(&p,previous,next,5000u,&full):
            kind==3u?comp_ssd1681_wba_start_recording_partial(&p,previous,next,5000u,&full):
            comp_ssd1681_wba_start_full(&p,previous,next,5000u);
        CHECK(started);CHECK(drive(&p,&f));memcpy(old,next,sizeof(old));CHECK(comp_wba_frame_store_write(&store,old));
    }
    CHECK(fclose(f.trace)==0);return 0;
}
static int presenter_failures(void)
{
    fixture_t f={0};f.image=frame;memset(frame,255u,sizeof(frame));frame[250u]=0x3cu;
    comp_ssd1681_wba_t panel;comp_ssd1681_wba_config_t c=config(&f);CHECK(comp_ssd1681_wba_init(&panel,&c));
    comp_screen_presenter_wba_t p;comp_screen_presenter_wba_config_t pc={0};pc.panel=&panel;
    pc.render=render;pc.complete=complete;pc.context=&f;pc.committed_frame=store.bytes;pc.staging_frame=next;pc.partial_limit=255u;
    CHECK(comp_screen_presenter_wba_init(&p,&pc));comp_runtime_frame_t request={0};request.token=1u;
    CHECK(comp_screen_presenter_wba_submit(&p,&request,f.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    CHECK(drive(&panel,&f));CHECK(comp_screen_presenter_wba_service(&p,f.now)==COMP_SCREEN_PRESENTER_WBA_IDLE);
    CHECK(f.visible==1u && p.committed_valid);CHECK(comp_wba_frame_store_read(&store,0u,old,5000u));CHECK(!memcmp(old,next,5000u));
    saved=store;uint32_t calls=f.calls;uint32_t rng=123u;
    for(unsigned i=0u;i<5000u;++i){rng=1664525u*rng+1013904223u;frame[i]=(uint8_t)(rng>>24);}
    CHECK(comp_wba_frame_store_size(frame)>COMP_WBA_FRAME_STORE_BYTES);
    CHECK(!comp_wba_frame_store_write(&store,frame));CHECK(!memcmp(&store,&saved,sizeof(store)));
    request.token=2u;CHECK(comp_screen_presenter_wba_submit(&p,&request,f.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_COMPLETED);
    CHECK(f.failed==1u && f.calls==calls && p.committed_valid);CHECK(!memcmp(&store,&saved,sizeof(store)));
    memset(frame,255u,sizeof(frame));frame[275u]=0x7fu;request.token=3u;f.fail_at=f.calls+1u;
    CHECK(comp_screen_presenter_wba_submit(&p,&request,f.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
    CHECK(!drive(&panel,&f));CHECK(comp_screen_presenter_wba_service(&p,f.now)==COMP_SCREEN_PRESENTER_WBA_IDLE);
    CHECK(f.failed==2u && !p.committed_valid);CHECK(comp_wba_frame_store_read(&store,0u,decoded,5000u));CHECK(!memcmp(old,decoded,5000u));
    return 0;
}

/* The production presenter object redirects only its old-row reads through
 * this deterministic cost wrapper. The codec/driver are still production C.
 * 1ms per row is an injected scheduling stress, not a measured ARM estimate. */
static fixture_t *cpu_fixture;
static uint32_t cpu_anchor,cpu_yields,cpu_peak;
static bool cpu_reject;
bool timed_frame_read(comp_wba_frame_store_t *p,size_t at,uint8_t *out,size_t n)
{
    if(cpu_fixture)++cpu_fixture->now;
    return comp_wba_frame_store_read(p,at,out,n);
}
static bool cpu_service(void *context)
{
    fixture_t *f=context;uint32_t gap=f->now-cpu_anchor;
    if(gap>cpu_peak)cpu_peak=gap;
    if(gap>10u || cpu_reject)return false;
    ++cpu_yields;f->now+=7u;cpu_anchor=f->now;
    return true;
}
static unsigned encode_calls,encode_reject_at;
static bool encode_service(void *context)
{(void)context;++encode_calls;return !encode_reject_at || encode_calls!=encode_reject_at;}
static int cooperative_cpu(void)
{
    for(unsigned enabled=0u;enabled<2u;++enabled) {
        fixture_t f={0};f.image=frame;memset(frame,255u,sizeof(frame));frame[250u]=0x3cu;
        comp_ssd1681_wba_t panel;comp_ssd1681_wba_config_t c=config(&f);CHECK(comp_ssd1681_wba_init(&panel,&c));
        comp_screen_presenter_wba_t p;comp_screen_presenter_wba_config_t pc={0};pc.panel=&panel;
        pc.render=render;pc.complete=complete;pc.context=&f;pc.committed_frame=store.bytes;pc.staging_frame=next;pc.partial_limit=255u;
        CHECK(comp_screen_presenter_wba_init(&p,&pc));comp_runtime_frame_t r={0};r.token=1u;
        CHECK(comp_screen_presenter_wba_submit(&p,&r,f.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
        CHECK(drive(&panel,&f));CHECK(comp_screen_presenter_wba_service(&p,f.now)==COMP_SCREEN_PRESENTER_WBA_IDLE);
        CHECK(p.committed_valid);saved=store;uint32_t transfers=f.calls;
        frame[500u]^=0x38u;r.token=2u;r.recording=DENZIC_AUDIO_RECORDING_STATE_RECORDING;
        cpu_anchor=f.now;cpu_yields=cpu_peak=0u;cpu_reject=false;cpu_fixture=&f;
        if(enabled)comp_screen_presenter_wba_set_progress(&p,cpu_service);
        CHECK(comp_screen_presenter_wba_submit(&p,&r,f.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED);
        cpu_fixture=NULL;
        if(enabled){CHECK(cpu_yields>=25u && cpu_peak<=8u);CHECK(f.now-cpu_anchor<=10u);}
        else{CHECK(cpu_yields==0u && f.now-cpu_anchor>=200u);}
        CHECK(drive(&panel,&f));cpu_anchor=f.now; /* foreground audio is serviced between physical driver polls, outside this CPU-only stress */
        CHECK(comp_screen_presenter_wba_service(&p,f.now)==COMP_SCREEN_PRESENTER_WBA_IDLE);
        CHECK(f.visible==2u && p.committed_valid);CHECK(comp_wba_frame_store_read(&store,0u,decoded,5000u));CHECK(!memcmp(decoded,next,5000u));
        if(enabled){
            saved=store;transfers=f.calls;cpu_anchor=f.now;cpu_reject=true;r.token=3u;frame[600u]^=1u;
            CHECK(comp_screen_presenter_wba_submit(&p,&r,f.now)==COMP_SCREEN_PRESENTER_WBA_SUBMIT_COMPLETED);
            CHECK(f.calls==transfers && f.failed==1u && p.committed_valid && !memcmp(&saved,&store,sizeof(store)));
        }
    }
    memset(frame,255u,sizeof(frame));frame[250u]=0x31u;CHECK(comp_wba_frame_store_write(&store,frame));saved=store;
    encode_calls=encode_reject_at=0u;size_t n=comp_wba_frame_store_size_progress(frame,encode_service,NULL);CHECK(n==comp_wba_frame_store_size(frame));unsigned first_pass=encode_calls;CHECK(first_pass>15u);
    encode_calls=0u;encode_reject_at=1u;CHECK(!comp_wba_frame_store_write_progress(&store,frame,encode_service,NULL));CHECK(!memcmp(&saved,&store,sizeof(store)));
    encode_calls=0u;encode_reject_at=first_pass+2u;CHECK(!comp_wba_frame_store_write_progress(&store,frame,encode_service,NULL));CHECK(!store.valid && !comp_wba_frame_store_read(&store,0u,decoded,25u));
    encode_calls=encode_reject_at=0u;CHECK(comp_wba_frame_store_write_progress(&store,frame,encode_service,NULL));CHECK(comp_wba_frame_store_read(&store,0u,decoded,5000u));CHECK(!memcmp(frame,decoded,5000u));
    printf("COOPERATIVE_FRAME_CPU model_old_gap_ge200ms new_gap_le8ms codec_injected7ms; deadline10ms retained; abort_no_activation; interrupted_stream_invalid\n");return 0;
}

int main(int argc,char **argv)
{
    CHECK(argc==5);unsigned cases=0u;size_t maximum=0u;CHECK(!cooperative_cpu());
    CHECK(!roundtrips(argv[1],&cases,&maximum));CHECK(!roundtrips(argv[2],&cases,&maximum));
    CHECK(!wire_trace(argv[3],false));CHECK(!wire_trace(argv[4],true));CHECK(!presenter_failures());
    printf("FRAME_STORE_SOFTWARE_OK cases=%u maximum=%zu capacity=%u context=%zu complete_old_bytes_preserved failure_does_not_commit\n",cases,maximum,COMP_WBA_FRAME_STORE_BYTES,sizeof(store));return 0;
}
