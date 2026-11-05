#include "companion_preferences.h"
#include "wba_silence_stop.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){printf("FAIL %d %s\n",__LINE__,#x);return 1;}}while(0)
typedef struct {uint8_t bytes[8192];int budget;bool erase_fail;} flash_t;
static bool rd(void *c,uint32_t a,uint8_t *p,size_t n) {flash_t *f=c;if(a>8192 || n>8192-a)return false;memcpy(p,f->bytes+a,n);return true;}
static bool wr(void *c,uint32_t a,const uint8_t *p,size_t n) {
    flash_t *f=c;if(a>8192 || n>8192-a)return false;
    for(size_t i=0;i<n;++i){if(f->budget==0)return false;if(f->budget>0)--f->budget;
        if((f->bytes[a+i]&p[i])!=p[i])return false;f->bytes[a+i]&=p[i];}return true;
}
static bool er(void *c,uint32_t a) {flash_t *f=c;if(a!=0 && a!=4096)return false;
    memset(f->bytes+a,255,f->erase_fail?2048:4096);return !f->erase_fail;}
int main(void) {
    flash_t f,baseline;comp_preferences_t store,reboot;comp_preferences_values_t v;
    comp_preferences_port_t p={rd,wr,er,&f};memset(&f,255,sizeof(f));f.budget=-1;f.erase_fail=false;
    CHECK(comp_preferences_mount(&store,&p));CHECK(!store.persisted && store.values.volume==25);
    CHECK(comp_preferences_are_defaults(&store.values));
    uint32_t default_crc=comp_preferences_fingerprint(&store.values);
    v=store.values;v.volume=26u;CHECK(!comp_preferences_are_defaults(&v)&&comp_preferences_fingerprint(&v)!=default_crc);
    v=store.values;v.imu_screen_axes=0x99u;CHECK(comp_preferences_are_defaults(&v)&&comp_preferences_fingerprint(&v)!=default_crc);
    CHECK(store.values.name_length==COMP_PREFS_DEFAULT_NAME_BYTES &&
        !memcmp(store.values.name,COMP_PREFS_DEFAULT_NAME,COMP_PREFS_DEFAULT_NAME_BYTES));
    v=store.values;v.name_length=9u;memcpy(v.name,"Companion",9u);
    CHECK(comp_preferences_save(&store,&v) && comp_preferences_mount(&reboot,&p));
    CHECK(reboot.values.name_length==9u && !memcmp(reboot.values.name,"Companion",9u));
    v=reboot.values;v.name_length=10u;memcpy(v.name,"Owner Unit",10u);
    CHECK(comp_preferences_save(&store,&v) && comp_preferences_mount(&reboot,&p));
    CHECK(reboot.values.name_length==10u && !memcmp(reboot.values.name,"Owner Unit",10u));
    memset(&f,255,sizeof(f));f.budget=-1;f.erase_fail=false;CHECK(comp_preferences_mount(&store,&p));
    CHECK(store.values.policy.recording_limit_minutes==0u); /* blank device: no arbitrary 30-minute stop */
    CHECK(comp_preferences_save(&store,&store.values));
    v=store.values;v.policy.recording_limit_minutes=30u;CHECK(comp_preferences_save(&store,&v));
    CHECK(comp_preferences_mount(&reboot,&p));CHECK(reboot.values.policy.recording_limit_minutes==30u);
    v.policy.recording_limit_minutes=0u;CHECK(comp_preferences_save(&store,&v));
    memset(&f,255,sizeof(f));f.budget=-1;f.erase_fail=false;CHECK(comp_preferences_mount(&store,&p));
    CHECK(comp_preferences_save(&store,&store.values));
    for(unsigned i=1;i<64;++i) {v=store.values;v.volume=(uint8_t)i;CHECK(comp_preferences_save(&store,&v));}
    CHECK(store.next_slot==64 && store.bank==0);baseline=f;
    for(int cut=0;cut<=64;++cut) {
        f=baseline;f.budget=cut;CHECK(comp_preferences_mount(&store,&p));v=store.values;
        v.volume=99;v.locale=2;v.policy.time_zone_offset_minutes=345;
        bool saved=comp_preferences_save(&store,&v);
        f.budget=-1;CHECK(comp_preferences_mount(&reboot,&p));
        CHECK(reboot.persisted && (reboot.values.volume==63 || reboot.values.volume==99));
        CHECK((cut==64)==saved);CHECK(saved?reboot.values.locale==2:reboot.values.locale==0);
        CHECK(comp_preferences_save(&reboot,&v));CHECK(comp_preferences_mount(&store,&p));CHECK(store.values.volume==99);
    }
    f=baseline;f.erase_fail=true;CHECK(comp_preferences_mount(&store,&p));v=store.values;v.volume=88;
    CHECK(!comp_preferences_save(&store,&v));f.erase_fail=false;CHECK(comp_preferences_mount(&reboot,&p));CHECK(reboot.values.volume==63);
    /* Failed append consumes its slot; retry cannot program over torn NOR. */
    f=baseline;f.budget=-1;CHECK(comp_preferences_mount(&store,&p));CHECK(comp_preferences_save(&store,&v));
    f.budget=23;v.locale=1;CHECK(!comp_preferences_save(&store,&v));f.budget=-1;
    CHECK(comp_preferences_save(&store,&v));CHECK(comp_preferences_mount(&reboot,&p));CHECK(reboot.values.locale==1);
    /* Old EN/ZH records still load; the added Traditional locale survives a
     * successful append/reboot, while an unknown wire value changes nothing. */
    v.locale=2;CHECK(comp_preferences_save(&reboot,&v));
    CHECK(comp_preferences_mount(&store,&p));CHECK(store.values.locale==2);
    v.locale=3;CHECK(!comp_preferences_save(&store,&v));
    CHECK(comp_preferences_mount(&reboot,&p));CHECK(reboot.values.locale==2);
    v.locale=2;
    v.quiet_enabled=true;
    CHECK(comp_preferences_save(&reboot,&v));CHECK(comp_preferences_mount(&store,&p));CHECK(store.values.quiet_enabled);
    v.policy.time_zone_offset_minutes=841;CHECK(!comp_preferences_save(&reboot,&v));
    comp_clock_t clock={0};CHECK(comp_clock_status(&clock,480,true,0)==0);
    CHECK(comp_clock_sync(&clock,23,59,59,0xFFFFFF00u));comp_clock_poll(&clock,0x2E8u);
    CHECK(clock.utc_seconds==0 && clock.milliseconds==0);
    CHECK(comp_clock_local_hour(&clock,-300,0x2E8u)==19);
    CHECK(comp_clock_status(&clock,345,true,0x2E8u)==(0x8000u|(5u<<8)|45u));
    CHECK(comp_clock_status(&clock,0,false,0x2E8u)==(0x8000u|(12u<<8)));
    CHECK(!comp_clock_sync(&clock,24,0,0,10) && clock.utc_seconds==0);
    const uint32_t midnight=20001u*86400u;
    CHECK(comp_clock_sync_unix(&clock,midnight-1u,0xFFFFFF00u));
    CHECK(comp_clock_unix(&clock,0x2E8u)==midnight && clock.utc_seconds==midnight-1u);
    comp_clock_poll(&clock,0x2E8u);CHECK(clock.calendar_valid && clock.utc_seconds==midnight);
    CHECK(comp_clock_local_hour(&clock,-300,0x2E8u)==19u && comp_clock_unix(&clock,0x2E8u)==midnight);
    CHECK(comp_clock_sync_unix(&clock,midnight-100u,0x2E8u)); /* host backstep */
    CHECK(comp_clock_unix(&clock,0x2E8u)==midnight-100u);
    CHECK(comp_clock_sync(&clock,12,0,0,0x2E8u) && !clock.calendar_valid && comp_clock_unix(&clock,0x2E8u)==0u);
    CHECK(!comp_clock_sync_unix(&clock,0,10u));
    CHECK(comp_clock_sync_unix(&clock,UINT32_MAX,0));
    comp_clock_poll(&clock,1000u);CHECK(!clock.valid && !clock.calendar_valid);
    _Static_assert(sizeof(comp_clock_t)==12u,"calendar flag must fit existing clock padding");
    v=reboot.values;v.name[0]=0x80u;CHECK(!comp_preferences_valid(&v));
    int16_t pcm[160]={0};comp_wba_silence_stop_t silence;
    comp_wba_silence_stop_init(&silence,true,true);
    for(unsigned i=0;i<3000;++i)CHECK(!comp_wba_silence_stop_pcm(&silence,pcm,160));
    for(unsigned i=0;i<160;++i)pcm[i]=800;
    CHECK(!comp_wba_silence_stop_pcm(&silence,pcm,160));
    memset(pcm,0,sizeof(pcm));
    for(unsigned i=0;i<1600;++i)CHECK(!comp_wba_silence_stop_pcm(&silence,pcm,160));
    for(unsigned i=0;i<160;++i)pcm[i]=800;
    for(unsigned i=0;i<50;++i)CHECK(!comp_wba_silence_stop_pcm(&silence,pcm,160));
    memset(pcm,0,sizeof(pcm));
    for(unsigned i=0;i<1499;++i)CHECK(!comp_wba_silence_stop_pcm(&silence,pcm,160));
    CHECK(comp_wba_silence_stop_pcm(&silence,pcm,160));
    comp_wba_silence_stop_init(&silence,false,false);
    for(unsigned i=0;i<4000;++i)CHECK(!comp_wba_silence_stop_pcm(&silence,pcm,160));
    puts("PASS_PREFERENCES: every torn rollover boundary, partial erase, append retry, persistence, timezone/clock wrap");return 0;
}
