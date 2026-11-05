#ifndef COMPANION_WBA_STOP_H
#define COMPANION_WBA_STOP_H
#include <stdbool.h>
#include <stdint.h>

/* RTC binary timer is LSE / 32 = 1024 Hz. Target ports must restore clocks
 * before returning from enter(), while the IRQ lock remains held. */
#define COMP_WBA_STOP_RTC_HZ 1024u
#define COMP_WBA_STOP_WAKE_MS 20u
typedef struct {
    uint32_t last_ticks, milliseconds;
    uint16_t fraction;
} comp_wba_rtc_clock_t;
void comp_wba_rtc_clock_init(comp_wba_rtc_clock_t *, uint32_t ticks, uint32_t milliseconds);
/* Expected to run at least once per second; invalid/backward time leaves the
 * clock unchanged. Covers awake AND sleeping time, including partial ticks. */
bool comp_wba_rtc_clock_update(comp_wba_rtc_clock_t *, uint32_t ticks);
/* Keep one RTC phase across repeated awake/Stop intervals. Foreground still
 * owns SysTick; never move its value backwards. A long/invalid gap reanchors
 * using the existing bounded stopped-period fallback, not a large RTC jump. */
uint32_t comp_wba_rtc_clock_compensate(comp_wba_rtc_clock_t *,uint32_t ticks,
                                     uint32_t hal_ms,uint32_t stopped_ms);
typedef struct {
    bool (*arm)(void *, uint32_t);
    bool (*disarm)(void *);
    /* Always acquires the lock, including when the last recheck fails. */
    bool (*lock_recheck)(void *);
    void (*unlock)(void *);
    void (*suspend_tick)(void *);
    void (*resume_tick)(void *, uint32_t);
    uint32_t (*rtc_ticks)(void *);
    bool (*enter)(void *);
    void (*watchdog)(void *);
} comp_wba_stop_ports_t;
typedef struct {
    /* Immutable callback table must outlive this state (normally static const).
     * Context is per instance; no callback table is copied into scarce RAM. */
    const comp_wba_stop_ports_t *ports;
    void *context;
    uint32_t completed, aborted, failures, compensated_ms;
    uint16_t fraction;
    bool enabled;
} comp_wba_stop_t;
typedef enum {
    COMP_WBA_STOP_SKIPPED,
    COMP_WBA_STOP_COMPLETED,
    COMP_WBA_STOP_ABORTED,
    COMP_WBA_STOP_FAULT
} comp_wba_stop_result_t;
void comp_wba_stop_init(comp_wba_stop_t *, const comp_wba_stop_ports_t *, void *context, bool enabled);
comp_wba_stop_result_t comp_wba_stop_run(comp_wba_stop_t *, bool eligible);
#endif
