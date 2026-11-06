#ifndef COMP_V11_MAINTENANCE_PROTOCOL_H
#define COMP_V11_MAINTENANCE_PROTOCOL_H
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include "companion_crc32.h"
enum { COMP_MAINT_QUERY=0,COMP_MAINT_PAIR_WINDOW=1,COMP_MAINT_DEFAULTS=2,COMP_MAINT_CLEAR_BONDS=3,
       COMP_MAINT_BLE_DIAGNOSTICS=4,COMP_MAINT_MEMORY=5,COMP_MAINT_AUDIO_TIMING=6,
       COMP_MAINT_AUDIO_FAULTS=7,COMP_MAINT_AUDIO_SERVICE=8,COMP_MAINT_CPU_DUTY=9 };
enum { COMP_MAINT_OK=0,COMP_MAINT_PENDING=1,COMP_MAINT_BUSY=2,COMP_MAINT_INVALID=3,COMP_MAINT_FAILED=4 };
static inline uint32_t comp_maint_get32(const uint8_t *p)
{return (uint32_t)p[0]|((uint32_t)p[1]<<8u)|((uint32_t)p[2]<<16u)|((uint32_t)p[3]<<24u);}
static inline void comp_maint_put32(uint8_t *p,uint32_t n)
{for(unsigned i=0u;i<4u;i++)p[i]=(uint8_t)(n>>(8u*i));}
/* Existing encrypted4003 characteristic. No new GATT service or database. */
static inline bool comp_maint_request(const uint8_t *p,uint16_t n,uint8_t *operation,uint32_t *request)
{
    if(!p||!operation||!request||n!=16u||memcmp(p,"CRM1",4u)||p[4]>COMP_MAINT_CPU_DUTY||
       p[5]||p[6]||p[7]||!comp_maint_get32(p+8u)||
       companion_crc32(0u,p,12u)!=comp_maint_get32(p+12u))return false;
    *operation=p[4];*request=comp_maint_get32(p+8u);return true;
}
/* Operation4 alone returns cached BLE scalars in the existing32B reply:
 * byte6 radio/advertising/pair-window/linked/allowed/secured bits0..5;
 * bit6 last failed pairing retained, bit7 last unsecured link was admitted;
 * byte7 last host error; bytes12..15 last failed pairing status/reason (or
 * latest result if no failure), last unsecured disconnect (FF if none),
 * last encryption status;16..19 pair-window remaining ms;20..23 seen/failed
 * LE completion counts (u16 each);24..27 bond-lost/rebond counts (saturated
 * u16 each). Nonce/header/CRC stay identical. No addresses, keys or payload.
 * Operations0..3 retain their original preference/bond response fields. */
/* Operations5..8: same nonce/CRC/header, byte7=1 (scalar schema).
 * 5 idle-only: flags sampled/guard/low bits0..2; u32 at12 stack reserve,
 *   16 sticky minimum free,20 core Hz,24 uptime ms. No scan during capture.
 * 6 cached: flags encodeP95/peak,PDM P95/peak valid bits0..3,media/running
 *   bits4..5; u32 at12 encode samples,16 PDM samples; u16 at20/22/24/26
 *   encodeP95/peak and PDM P95/peak conservative upper milliseconds.
 *   Invalid/overflow timing=FFFF with its validity bit clear, never a zero.
 * 7 cached: flags initialized/running bits0..1; u32 at12 overflows,16 stale,
 *   20 rejected,24 deadline faults. No resets or capture commands.
 * 8 cached: same flags plus mediaReady bit2; u32 at12 processed DMA halves,
 *   16 error IRQs,20 worst capture foreground ms,24 max microphone poll ms.
 * These are observations since the counters' existing lifecycle reset, not
 * CPU utilization, instantaneous timing or physical power measurements. */
/* FW66699+: operation6 alone uses byte7=2 and the same four u16 fields are
 * conservative upper microseconds. Others retain schema1. FFFF/valid-mask
 * rules unchanged; clients must check the schema before interpreting units. */
/* Operation9 CPU snapshot. Schema1 (FW700) used masked-WFI/DWT; no useful
 * bound was observed on the sample. Schema2 (FW701+) uses RTC wall time and
 * TIM2 Run-only clocks (TIM2SMEN=0), retaining ordinary WFI and all IRQ time.
 * Flags enabled/active/recording/valid bits0..3. Valid requires completed
 * one-second windows and no clock/order errors. Schema2 adds2200us busy
 * per window for RTC endpoint/snapshot/counter uncertainty. A valid100%
 * bound fails95%; it is not an unmeasured0% result.
 * u32 at12 windows,16 peak busy upper microseconds per1000000us,20 errors,
 * 24 observed gated gaps. Disabled/unmeasured never zero/pass. No reset. */
static inline void comp_maint_timing16(uint8_t p[32],unsigned at,unsigned bit,
    bool valid,uint32_t value)
{
    if(!valid||value>=UINT16_MAX)value=UINT16_MAX;
    else p[6]|=(uint8_t)(1u<<bit);
    p[at]=(uint8_t)value;p[at+1u]=(uint8_t)(value>>8u);
}
static inline void comp_maint_response(uint8_t p[32],uint8_t operation,uint8_t result,uint32_t request,
    uint8_t flags,uint8_t bonds,uint32_t preferences_generation,uint32_t preferences_crc,
    uint32_t bonds_generation,uint32_t last_request)
{
    memset(p,0,32u);memcpy(p,"CRM1",4u);p[4]=operation;p[5]=result;p[6]=flags;p[7]=bonds;
    comp_maint_put32(p+8u,request);comp_maint_put32(p+12u,preferences_generation);
    comp_maint_put32(p+16u,preferences_crc);comp_maint_put32(p+20u,bonds_generation);
    comp_maint_put32(p+24u,last_request);comp_maint_put32(p+28u,companion_crc32(0u,p,28u));
}
#endif
