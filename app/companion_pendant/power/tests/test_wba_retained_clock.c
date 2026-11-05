#include "wba_retained_clock.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do { if (!(x)) { printf("FAIL line %d: %s\n",__LINE__,#x);return 1; } } while (0)
typedef struct {uint32_t words[COMP_WBA_CLOCK_WORDS];int fail_after,writes;} fake_t;
static uint32_t rd(void *p,unsigned i){return ((fake_t *)p)->words[i];}
static bool wr(void *p,unsigned i,uint32_t v){fake_t *f=p;if(f->fail_after>=0 && f->writes++>=f->fail_after)return false;f->words[i]=v;return true;}
int main(void)
{
    fake_t f={{0},-1,0};comp_wba_clock_port_t port={&f,rd,wr};
    comp_wba_retained_clock_t a,b;uint32_t t;
    CHECK(!comp_wba_retained_clock_mount(&a,&port,false,0));
    CHECK(comp_wba_retained_clock_save(&a,UINT32_MAX-511u,COMP_WBA_CLOCK_DAY_MS-500u));
    CHECK(comp_wba_retained_clock_now(&a,512u,&t) && t==500u);
    CHECK(comp_wba_retained_clock_mount(&b,&port,true,512u));
    CHECK(comp_wba_retained_clock_now(&b,1536u,&t) && t==1500u);
    CHECK(!comp_wba_retained_clock_save(&b,10,COMP_WBA_CLOCK_DAY_MS));
    fake_t before=f;
    /* Every torn write of a newer bank leaves the previous validated anchor
     * usable on a simulated reboot, including sequence/counter wrap. */
    for(int cut=0;cut<7;++cut) {
        f=before;f.fail_after=cut;f.writes=0;
        CHECK(!comp_wba_retained_clock_save(&b,2048,9999));
        f.fail_after=-1;
        CHECK(comp_wba_retained_clock_mount(&b,&port,true,512));
        CHECK(comp_wba_retained_clock_now(&b,512,&t) && t==500);
    }
    f=before;
    CHECK(comp_wba_retained_clock_mount(&b,&port,true,512));
    CHECK(comp_wba_retained_clock_save(&b,512,10000));
    f.words[b.bank*6u+3u]^=1;
    CHECK(comp_wba_retained_clock_mount(&b,&port,true,512));
    CHECK(comp_wba_retained_clock_now(&b,512,&t) && t==500);
    CHECK(!comp_wba_retained_clock_mount(&b,&port,false,512));
    CHECK(!comp_wba_retained_clock_mount(&b,&port,true,512));
    CHECK(comp_wba_retained_clock_save(&b,5000,12000));
    CHECK(!comp_wba_retained_clock_now(&b,4999,&t));
    CHECK(!comp_wba_retained_clock_mount(&a,&port,true,5000));
    CHECK(comp_wba_retained_clock_save(&b,100,12000));
    CHECK(!comp_wba_retained_clock_now(&b,101+COMP_WBA_CLOCK_MAX_AGE_TICKS,&t));
    CHECK(comp_wba_retained_clock_save(&b,100,12000));
    uint32_t seconds;uint16_t millis;
    CHECK(!comp_wba_retained_clock_now_unix(&b,100,&seconds,&millis));
    const uint32_t midnight=20001u*86400u;
    CHECK(comp_wba_retained_clock_save_unix(&b,UINT32_MAX-511u,midnight-1u,500u));
    CHECK(comp_wba_retained_clock_now_unix(&b,512u,&seconds,&millis) && seconds==midnight && millis==500u);
    CHECK(comp_wba_retained_clock_mount(&a,&port,true,512u));
    CHECK(comp_wba_retained_clock_now_unix(&a,1536u,&seconds,&millis) && seconds==midnight+1u && millis==500u);
    before=f;
    for(int cut=0;cut<7;++cut) {
        f=before;f.fail_after=cut;f.writes=0;
        CHECK(!comp_wba_retained_clock_save_unix(&a,2048u,midnight+100u,0));
        f.fail_after=-1;CHECK(comp_wba_retained_clock_mount(&a,&port,true,512u));
        CHECK(comp_wba_retained_clock_now_unix(&a,512u,&seconds,&millis) && seconds==midnight && millis==500u);
    }
    f=before;CHECK(comp_wba_retained_clock_mount(&a,&port,true,512u));
    CHECK(comp_wba_retained_clock_save_unix(&a,512u,midnight+100u,0));
    f.words[a.bank*6u]^=1u; /* day is CRC protected, not just time-of-day */
    CHECK(comp_wba_retained_clock_mount(&a,&port,true,512u));
    CHECK(comp_wba_retained_clock_now_unix(&a,512u,&seconds,&millis) && seconds==midnight && millis==500u);
    CHECK(comp_wba_retained_clock_save_unix(&a,100u,UINT32_MAX,0));
    CHECK(!comp_wba_retained_clock_now_unix(&a,1124u,&seconds,&millis));
    CHECK(!comp_wba_retained_clock_save_unix(&a,10u,0,0));
    CHECK(!comp_wba_retained_clock_save_unix(&a,10u,midnight,1000u));
    puts("PASS RTC anchor: reset, midnight/counter wrap, torn writes, CRC fallback, domain loss, backward/stale rejection");
    puts("PASS calendar: legacy unknown, full date midnight/reset/counter wrap, torn date writes, date CRC fallback and Unix overflow");return 0;
}
