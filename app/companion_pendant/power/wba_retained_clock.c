#include "wba_retained_clock.h"
#include <string.h>
#define MAGIC UINT32_C(0x31544357)
/* Full dates use the same six words/bank. CRC covers the day in word0;
 * legacy records remain valid as UTC-of-day only, never invented dates. */
#define CALENDAR_MAGIC UINT32_C(0xCA1D0000)
#define COMMIT UINT32_C(0xC10CDA7A)
static uint32_t checksum(const uint32_t *words)
{
    uint32_t crc=~0u;
    for (unsigned i=0;i<4;++i) for (unsigned byte=0;byte<4;++byte) {
        crc^=(words[i]>>(byte*8u))&255u;
        for (unsigned bit=0;bit<8;++bit) crc=(crc>>1)^(UINT32_C(0xEDB88320)&(0u-(crc&1u)));
    }
    return ~crc;
}
static bool decode(const uint32_t *r)
{return (r[0]==MAGIC || ((r[0]&UINT32_C(0xFFFF0000))==CALENDAR_MAGIC &&
    (r[0]&65535u)!=65535u)) && r[3]<COMP_WBA_CLOCK_DAY_MS && r[4]==checksum(r) && r[5]==COMMIT;}
void comp_wba_retained_clock_invalidate(comp_wba_retained_clock_t *c)
{
    if (!c) return;
    c->valid=false;c->persisted=false;
    if (c->port.write) {
        (void)c->port.write(c->port.context,5,0);
        (void)c->port.write(c->port.context,11,0);
    }
}
bool comp_wba_retained_clock_now(comp_wba_retained_clock_t *c,uint32_t ticks,uint32_t *utc_ms)
{
    if (!c || !c->valid || !utc_ms) return false;
    uint32_t elapsed=ticks-c->anchor_ticks;
    /* Modular subtraction supports a genuine binary counter wrap; backwards
     * values and stale anchors fail closed. Checkpoint each minute while on. */
    if (elapsed>COMP_WBA_CLOCK_MAX_AGE_TICKS) {comp_wba_retained_clock_invalidate(c);return false;}
    *utc_ms=(c->anchor_utc_ms+(uint32_t)(((uint64_t)elapsed*1000u)/1024u))%COMP_WBA_CLOCK_DAY_MS;
    return true;
}
bool comp_wba_retained_clock_mount(comp_wba_retained_clock_t *c,const comp_wba_clock_port_t *port,
    bool continuous_rtc,uint32_t ticks)
{
    if (!c || !port || !port->read || !port->write) return false;
    memset(c,0,sizeof(*c));c->port=*port;c->anchor_day=UINT16_MAX;
    if (!continuous_rtc) {comp_wba_retained_clock_invalidate(c);return false;}
    for (unsigned b=0;b<2;++b) {
        uint32_t r[6];for(unsigned i=0;i<6;++i) r[i]=port->read(port->context,b*6u+i);
        if(decode(r) && (!c->valid || (int32_t)(r[1]-c->generation)>0)) {
            c->generation=r[1];c->anchor_ticks=r[2];c->anchor_utc_ms=r[3];
            c->anchor_day=r[0]==MAGIC?UINT16_MAX:(uint16_t)r[0];
            c->bank=(uint8_t)b;c->valid=true;c->persisted=true;
        }
    }
    uint32_t ignored;return comp_wba_retained_clock_now(c,ticks,&ignored);
}
static bool save(comp_wba_retained_clock_t *c,uint32_t ticks,uint32_t utc_ms,uint16_t day)
{
    if (!c || !c->port.read || !c->port.write || utc_ms>=COMP_WBA_CLOCK_DAY_MS) return false;
    uint32_t r[6]={day==UINT16_MAX?MAGIC:CALENDAR_MAGIC|day,
        c->generation+1u,ticks,utc_ms,0,COMMIT};r[4]=checksum(r);
    unsigned bank=c->persisted?(c->bank^1u):0u,base=bank*6u;
    /* Destroy target commit first. Power loss at any individual write keeps
     * the other bank intact; publish only after complete readback. */
    if (!c->port.write(c->port.context,base+5u,0)) return false;
    for(unsigned i=0;i<6;++i) if(!c->port.write(c->port.context,base+i,r[i])) return false;
    for(unsigned i=0;i<6;++i) if(c->port.read(c->port.context,base+i)!=r[i]) return false;
    c->generation=r[1];c->anchor_ticks=ticks;c->anchor_utc_ms=utc_ms;
    c->anchor_day=day;
    c->bank=(uint8_t)bank;c->valid=true;c->persisted=true;return true;
}
bool comp_wba_retained_clock_save(comp_wba_retained_clock_t *c,uint32_t ticks,uint32_t utc_ms)
{return save(c,ticks,utc_ms,UINT16_MAX);}
bool comp_wba_retained_clock_save_unix(comp_wba_retained_clock_t *c,uint32_t ticks,
    uint32_t seconds,uint16_t milliseconds)
{
    if(!seconds || milliseconds>=1000u)return false;
    return save(c,ticks,(seconds%86400u)*1000u+milliseconds,(uint16_t)(seconds/86400u));
}
bool comp_wba_retained_clock_now_unix(comp_wba_retained_clock_t *c,uint32_t ticks,
    uint32_t *seconds,uint16_t *milliseconds)
{
    uint32_t utc;
    if(!c || c->anchor_day==UINT16_MAX || !seconds || !milliseconds ||
       !comp_wba_retained_clock_now(c,ticks,&utc))return false;
    uint32_t elapsed_ms=(uint32_t)(((uint64_t)(ticks-c->anchor_ticks)*1000u)/1024u);
    uint64_t value=(uint64_t)c->anchor_day*86400u+(c->anchor_utc_ms+elapsed_ms)/1000u;
    if(value>UINT32_MAX) {comp_wba_retained_clock_invalidate(c);return false;}
    *seconds=(uint32_t)value;*milliseconds=(uint16_t)(utc%1000u);return true;
}
