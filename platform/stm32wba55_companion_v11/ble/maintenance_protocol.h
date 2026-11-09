#ifndef COMP_V11_MAINTENANCE_PROTOCOL_H
#define COMP_V11_MAINTENANCE_PROTOCOL_H
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include "companion_crc32.h"
enum { COMP_MAINT_QUERY=0,COMP_MAINT_PAIR_WINDOW=1,COMP_MAINT_DEFAULTS=2,COMP_MAINT_CLEAR_BONDS=3,
       COMP_MAINT_BLE_DIAGNOSTICS=4,COMP_MAINT_MEMORY=5,COMP_MAINT_AUDIO_TIMING=6,
        COMP_MAINT_AUDIO_FAULTS=7,COMP_MAINT_AUDIO_SERVICE=8,COMP_MAINT_CPU_DUTY=9,COMP_MAINT_STORAGE=10,
        COMP_MAINT_IMU_TAPS=16,COMP_MAINT_IMU_MARKS=17 };
enum { COMP_MAINT_OK=0,COMP_MAINT_PENDING=1,COMP_MAINT_BUSY=2,COMP_MAINT_INVALID=3,COMP_MAINT_FAILED=4 };
#if defined(COMPANION_WBA_CPU_RESIDENCE_PROFILE) && COMPANION_WBA_CPU_RESIDENCE_PROFILE
/* Engineering-only cached pages on the existing encrypted characteristic.
 * Normal builds reject these operations; no product protocol/owner changes. */
enum {COMP_MAINT_CODEC_FIRST=32,COMP_MAINT_CODEC_LAST=38};
#endif
static inline bool comp_maint_operation_supported(uint8_t operation)
{
#if defined(COMPANION_WBA_CPU_RESIDENCE_PROFILE) && COMPANION_WBA_CPU_RESIDENCE_PROFILE
    if(operation>=COMP_MAINT_CODEC_FIRST && operation<=COMP_MAINT_CODEC_LAST)return true;
#endif
    return operation<=COMP_MAINT_STORAGE || operation==COMP_MAINT_IMU_TAPS || operation==COMP_MAINT_IMU_MARKS;
}
static inline uint32_t comp_maint_get32(const uint8_t *p)
{return (uint32_t)p[0]|((uint32_t)p[1]<<8u)|((uint32_t)p[2]<<16u)|((uint32_t)p[3]<<24u);}
static inline void comp_maint_put32(uint8_t *p,uint32_t n)
{for(unsigned i=0u;i<4u;i++)p[i]=(uint8_t)(n>>(8u*i));}
/* Existing encrypted4003 characteristic. No new GATT service or database. */
static inline bool comp_maint_request(const uint8_t *p,uint16_t n,uint8_t *operation,uint32_t *request)
{
    if(!p||!operation||!request||n!=16u||memcmp(p,"CRM1",4u)||!comp_maint_operation_supported(p[4])||
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
 * 24 observed gated gaps. FW702 schema3 instead puts actual WFI entries at24,
 * first invalid reason in flags4..7:1 foreign timer/IRQ,2 RTC domain,3 timer
 * configuration,4 slow snapshot,5 late sample,6 stuck counter,7 conversion,
 * 8 excess active span,9 debug freeze,10 clock setup. Bound/validity unchanged;
 * a fault is never silently turned into a valid sample. No reset. */
/* Operation10 reads existing NOR/consume scalars only, schema2. Flags0..4:
 * probed,suspend-qualified,32K-qualified,erase-active,command-failed; bit5
 * consume target known, bit6 catalog port32K-qualified. u32 at12 consume
 * physical start (zero if unknown),16 most recent erase address,20 owned
 * reserve bytes (zero if unknown); byte24 last erase size/4096 (0/1/8/16),
 * byte25 consume phase,26 erase phase,27 known consume descriptor flags. No NOR I/O or new
 * state. Last erase attribution still requires exact target containment;
 * inactive cached facts alone do not measure elapsed time or prove ownership. */
/* 16/17 cached IMU recorder scalars, schema1; no sensor/flash I/O, clearing or
 * recording command. First two u32 are current logical session low/high.
 * Flags: IMU ready, mic running,417Hz tap mode, tap read seen, valid PCM owner.
 * 16: last PDM-run TAP_SRC read count and saturated SINGLE low16/DOUBLE high16.
 * 17: current logical bookmark request and durable bookmark sequence.
 * Tap counters reset at each actual microphone admission (also resume), not
 * on these reads or STOP; bookmark sequence retains the whole logical source.
 * During new preparation before first PCM, owner-valid is clear. This avoids
 * interpreting the1Hz/250ms motion-status latch as a complete event history. */
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
