#include "companion_preferences.h"
#include "imu_screen_axes.h"
#include <string.h>
_Static_assert(sizeof(comp_preferences_values_t) == 44u, "preferences RAM envelope changed");
#if UINTPTR_MAX == UINT32_MAX
_Static_assert(sizeof(comp_preferences_t) == 68u, "preferences store RAM envelope changed");
#endif
#define PREF_MAGIC 0x31505743u
#define PREF_COMMIT 0x54494D43u
static uint32_t u32(const uint8_t *p) {return p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static void put(uint8_t *p,uint32_t n) {for(unsigned i=0;i<4;++i)p[i]=(uint8_t)(n>>(i*8u));}
static uint32_t crc(const uint8_t *p,size_t n) {
    uint32_t c=~0u;
    while(n--) {c^=*p++;for(unsigned b=0;b<8;++b)c=(c>>1)^(0xEDB88320u&(0u-(c&1u)));}
    return ~c;
}
void comp_preferences_defaults(comp_preferences_values_t *v) {
    memset(v,0,sizeof(*v));comp_power_settings_values_default(&v->policy);
    v->policy.silent_auto_stop=false;v->policy.recorder_profile=1u;
    v->volume=25u;v->radio_enabled=true;
    v->name_length=(uint8_t)COMP_PREFS_DEFAULT_NAME_BYTES;
    memcpy(v->name,COMP_PREFS_DEFAULT_NAME,COMP_PREFS_DEFAULT_NAME_BYTES);
}
bool comp_preferences_valid(const comp_preferences_values_t *v) {
    comp_power_settings_values_t p;
    if(!v || v->locale>2u || v->volume>100u || v->name_length==0u ||
       v->name_length>COMP_PREFS_NAME_BYTES || v->policy.time_zone_offset_minutes < -720 ||
       v->policy.time_zone_offset_minutes>840 || !comp_imu_screen_axes_valid(v->imu_screen_axes))return false;
    p=v->policy;p.time_zone_offset_minutes=0;
    if(!comp_power_settings_values_valid(&p))return false;
    for(unsigned i=0;i<v->name_length;++i) {
        uint8_t c=v->name[i];
        if(c<32u || c>126u || c=='"' || c=='\'' || c==';' || c=='=' || c=='\\')return false;
    }
    return true;
}
static void encode(uint8_t r[64],const comp_preferences_values_t *v,uint32_t generation) {
    const comp_power_settings_values_t *p=&v->policy;
    memset(r,0,64);put(r,PREF_MAGIC);put(r+4,generation);r[8]=1;
    r[9]=v->locale;r[10]=v->volume;r[11]=v->name_length;
    r[12]=(uint8_t)((p->silent_auto_stop?1u:0u)|(p->auto_reconnect?2u:0u)|(p->clock_24_hour?4u:0u)|
        (p->gaze_follow?8u:0u)|(p->natural_blink?16u:0u)|(v->radio_enabled?32u:0u)|(v->quiet_enabled?64u:0u));
    r[13]=v->battery_fill?1u:0u; /* Legacy records reserved zero: numeric. */
    r[14]=(uint8_t)p->time_zone_offset_minutes;r[15]=(uint8_t)((uint16_t)p->time_zone_offset_minutes>>8);
    r[16]=p->idle_minutes;r[17]=p->recording_limit_minutes;r[18]=p->recorder_profile;
    r[19]=p->interaction_level;r[20]=p->quiet_hours;r[21]=p->recording_gesture;
    r[22]=v->imu_screen_axes;r[23]=v->imu_screen_axes?1u:0u;
    memcpy(r+24,v->name,v->name_length);
    r[48]=v->pet_discovery_seen?1u:0u; /* Legacy reserved zero: not shown. */
    put(r+56,crc(r,56));put(r+60,PREF_COMMIT);
}
static bool decode(const uint8_t r[64],comp_preferences_values_t *v) {
    if(u32(r)!=PREF_MAGIC || r[8]!=1 || u32(r+60)!=PREF_COMMIT ||
       u32(r+56)!=crc(r,56) || (r[12]&0x80u) || r[13]>1u || r[48]>1u ||
       (r[23]==0u ? r[22]!=0u : r[23]!=1u || r[22]==0u || !comp_imu_screen_axes_valid(r[22])))return false;
    comp_preferences_defaults(v);v->locale=r[9];v->volume=r[10];v->name_length=r[11];
    v->radio_enabled=(r[12]&32u)!=0;v->policy.silent_auto_stop=(r[12]&1u)!=0;
    v->quiet_enabled=(r[12]&64u)!=0;
    v->battery_fill=r[13]!=0u;
    v->imu_screen_axes=r[22]; /* Legacy zero extension leaves tilt disabled. */
    v->pet_discovery_seen=r[48]!=0u;
    v->policy.auto_reconnect=(r[12]&2u)!=0;v->policy.clock_24_hour=(r[12]&4u)!=0;
    v->policy.gaze_follow=(r[12]&8u)!=0;v->policy.natural_blink=(r[12]&16u)!=0;
    v->policy.time_zone_offset_minutes=(int16_t)((uint16_t)r[14]|((uint16_t)r[15]<<8));
    v->policy.idle_minutes=r[16];v->policy.recording_limit_minutes=r[17];v->policy.recorder_profile=r[18];
    v->policy.interaction_level=r[19];v->policy.quiet_hours=r[20];v->policy.recording_gesture=r[21];
    memcpy(v->name,r+24,COMP_PREFS_NAME_BYTES);return comp_preferences_valid(v);
}
uint32_t comp_preferences_fingerprint(const comp_preferences_values_t *v)
{
    uint8_t encoded[64];
    if(!comp_preferences_valid(v))return 0u;
    encode(encoded,v,0u);return u32(encoded+56u);
}
bool comp_preferences_are_defaults(const comp_preferences_values_t *v)
{
    uint8_t current[64],expected[64];comp_preferences_values_t defaults;
    if(!comp_preferences_valid(v))return false;
    comp_preferences_defaults(&defaults);
    /* Board mounting is calibration, not a user's restorable preference. */
    defaults.imu_screen_axes=v->imu_screen_axes;
    encode(current,v,0u);encode(expected,&defaults,0u);
    return memcmp(current,expected,sizeof(current))==0;
}
bool comp_preferences_mount(comp_preferences_t *s,const comp_preferences_port_t *port) {
    uint8_t r[64],used[2]={0};comp_preferences_values_t value;
    if(!s || !port || !port->read || !port->write || !port->erase)return false;
    memset(s,0,sizeof(*s));s->port=*port;comp_preferences_defaults(&s->values);
    for(unsigned b=0;b<2;++b)for(unsigned n=0;n<64;++n) {
        bool erased=true;
        if(!port->read(port->context,b*4096u+n*64u,r,64))return false;
        for(unsigned i=0;i<64;++i)if(r[i]!=255u)erased=false;
        if(!erased)used[b]=(uint8_t)(n+1u);
        if(decode(r,&value) && (!s->persisted || (int32_t)(u32(r+4)-s->generation)>0)) {
            s->persisted=true;s->generation=u32(r+4);s->bank=(uint8_t)b;s->values=value;
        }
    }
    s->next_slot=used[s->bank];s->mounted=true;return true;
}
bool comp_preferences_save(comp_preferences_t *s,const comp_preferences_values_t *v) {
    uint8_t r[64],old[64],verify[64],bank,slot;comp_preferences_values_t checked;
    if(!s || !s->mounted || !comp_preferences_valid(v))return false;
    encode(r,v,s->generation+1u);encode(old,&s->values,s->generation+1u);
    /* A commit may already exist even if its write result or readback failed.
     * Reasserting the previous value must append too, not report a no-op. */
    if(s->persisted && !s->append_uncertain && memcmp(r,old,64)==0)return true;
    bank=s->bank;slot=s->next_slot;
    if(slot>=64u) {bank^=1u;slot=0u;if(!s->port.erase(s->port.context,bank*4096u))return false;}
    uint32_t offset=(uint32_t)bank*4096u+(uint32_t)slot*64u;
    /* A torn append is occupied. Never reprogram it on retry. The old bank
     * survives every failure before the new commit is verified. */
    if(bank==s->bank)s->next_slot=(uint8_t)(slot+1u);
    /* Reserve this sequence before I/O. A verified later choice must outrank
     * an earlier commit whose readback failed, even without a reboot/remount.
     * Values stay at the last verified setting on every failure. */
    ++s->generation;s->append_uncertain=true;
    if(!s->port.write(s->port.context,offset,r,60) ||
       !s->port.write(s->port.context,offset+60u,r+60,4) ||
       !s->port.read(s->port.context,offset,verify,64) || memcmp(r,verify,64) || !decode(verify,&checked))return false;
    s->values=*v;s->bank=bank;s->next_slot=(uint8_t)(slot+1u);s->persisted=true;s->append_uncertain=false;return true;
}
void comp_clock_poll(comp_clock_t *c,uint32_t now) {
    if(!c)return;
    if(c->valid) {uint64_t ms=(uint64_t)(now-c->tick)+c->milliseconds;
        uint64_t seconds=(uint64_t)c->utc_seconds+ms/1000u;
        if(c->calendar_valid && seconds>UINT32_MAX) {c->valid=false;c->calendar_valid=false;}
        else c->utc_seconds=c->calendar_valid?(uint32_t)seconds:(uint32_t)(seconds%86400u);
        c->milliseconds=(uint16_t)(ms%1000u);}
    c->tick=now;
}
bool comp_clock_sync(comp_clock_t *c,uint8_t h,uint8_t m,uint8_t s,uint32_t now) {
    if(!c || h>23u || m>59u || s>59u)return false;
    c->utc_seconds=(uint32_t)h*3600u+(uint32_t)m*60u+s;c->milliseconds=0;c->tick=now;
    c->valid=true;c->calendar_valid=false;return true;
}
bool comp_clock_sync_unix(comp_clock_t *c,uint32_t seconds,uint32_t now) {
    if(!c || !seconds)return false;
    c->utc_seconds=seconds;c->milliseconds=0;c->tick=now;
    c->valid=true;c->calendar_valid=true;return true;
}
uint32_t comp_clock_unix(const comp_clock_t *c,uint32_t now) {
    if(!c || !c->valid || !c->calendar_valid)return 0u;
    comp_clock_t copy=*c;comp_clock_poll(&copy,now);
    return copy.valid?copy.utc_seconds:0u;
}
static uint32_t local_seconds(comp_clock_t *c,int16_t zone,uint32_t now) {
    comp_clock_poll(c,now);int32_t seconds=(int32_t)(c->utc_seconds%86400u)+(int32_t)zone*60;
    return (uint32_t)((seconds+86400)%86400);
}
uint8_t comp_clock_local_hour(comp_clock_t *c,int16_t zone,uint32_t now) {
    return (uint8_t)(local_seconds(c,zone,now)/3600u);
}
uint32_t comp_clock_status(comp_clock_t *c,int16_t zone,bool clock24,uint32_t now) {
    if(!c || !c->valid)return 0u;
    uint32_t local=local_seconds(c,zone,now),hour=local/3600u;
    if(!clock24) {hour%=12u;if(!hour)hour=12u;}
    return 0x8000u|(hour<<8)|((local/60u)%60u);
}
