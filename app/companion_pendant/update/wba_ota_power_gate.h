#ifndef COMPANION_WBA_OTA_POWER_GATE_H
#define COMPANION_WBA_OTA_POWER_GATE_H
#include "wba_power_monitor.h"

/* Owner 2026-10-15: temporary board-development admission only. The normal
 * build stays strict; raw battery/charger observations and all other admission
 * gates remain unchanged. A development package must disclose this option. */
#ifndef COMPANION_WBA_OTA_DEV_IGNORE_POWER
#define COMPANION_WBA_OTA_DEV_IGNORE_POWER 0
#endif
#if COMPANION_WBA_OTA_DEV_IGNORE_POWER != 0 && COMPANION_WBA_OTA_DEV_IGNORE_POWER != 1
#error COMPANION_WBA_OTA_DEV_IGNORE_POWER_must_be_zero_or_one
#endif
static inline uint16_t comp_wba_ota_admission_power_blockers(
    const comp_wba_power_monitor_t *monitor,uint32_t now)
{
#if COMPANION_WBA_OTA_DEV_IGNORE_POWER
    (void)monitor;(void)now;return 0u;
#else
    return comp_wba_power_monitor_ota_blockers(monitor,now);
#endif
}
#endif
