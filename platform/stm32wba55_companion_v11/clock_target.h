#ifndef COMP_V11_CLOCK_TARGET_H
#define COMP_V11_CLOCK_TARGET_H
#include "companion_preferences.h"
/* Call before HAL_RTC_Init to detect a restarted/reconfigured RTC domain. */
bool comp_v11_clock_domain_continuous(void);
void comp_v11_clock_restore(comp_clock_t *,bool continuous);
void comp_v11_clock_checkpoint(comp_clock_t *);
void comp_v11_clock_poll(comp_clock_t *,uint32_t now,bool allow_checkpoint);
#endif
