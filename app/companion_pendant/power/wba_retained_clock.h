#ifndef COMP_WBA_RETAINED_CLOCK_H
#define COMP_WBA_RETAINED_CLOCK_H
#include <stdbool.h>
#include <stdint.h>
/* Two six-word records in RTC backup registers, never NOR/flash. The target
 * must reserve these words separately from the wireless timer's BKP0..2. */
#define COMP_WBA_CLOCK_WORDS 12u
#define COMP_WBA_CLOCK_DAY_MS 86400000u
#define COMP_WBA_CLOCK_MAX_AGE_TICKS (24u*60u*60u*1024u)
typedef struct {
    void *context;
    uint32_t (*read)(void *,unsigned);
    bool (*write)(void *,unsigned,uint32_t);
} comp_wba_clock_port_t;
typedef struct {
    comp_wba_clock_port_t port;
    uint32_t generation, anchor_ticks, anchor_utc_ms;
    uint16_t anchor_day; /* Unix day; UINT16_MAX means legacy date unknown. */
    uint8_t bank;
    bool valid, persisted;
} comp_wba_retained_clock_t;
bool comp_wba_retained_clock_mount(comp_wba_retained_clock_t *,const comp_wba_clock_port_t *,
    bool continuous_rtc,uint32_t rtc_ticks);
bool comp_wba_retained_clock_save(comp_wba_retained_clock_t *,uint32_t rtc_ticks,uint32_t utc_ms);
bool comp_wba_retained_clock_now(comp_wba_retained_clock_t *,uint32_t rtc_ticks,uint32_t *utc_ms);
bool comp_wba_retained_clock_save_unix(comp_wba_retained_clock_t *,uint32_t rtc_ticks,
    uint32_t unix_seconds,uint16_t milliseconds);
bool comp_wba_retained_clock_now_unix(comp_wba_retained_clock_t *,uint32_t rtc_ticks,
    uint32_t *unix_seconds,uint16_t *milliseconds);
void comp_wba_retained_clock_invalidate(comp_wba_retained_clock_t *);
#endif
