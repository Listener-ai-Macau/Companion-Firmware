#ifndef COMP_V11_PANEL_GPIO_TIMING_H
#define COMP_V11_PANEL_GPIO_TIMING_H
#include <stdint.h>
/* Preserve the verified 98.303712MHz/64-loop nominal hold time across core
 * clock changes, with ceiling rounding. This bounds software delay, not the
 * translated electrical edges. Packet setup also adapts after clock changes. */
#define COMP_V11_PANEL_DELAY_REFERENCE_HZ UINT32_C(98303712)
static inline uint32_t comp_v11_panel_gpio_delay_loops(uint32_t hz)
{
    if(!hz)return 64u;
    return (uint32_t)(((uint64_t)hz*64u+COMP_V11_PANEL_DELAY_REFERENCE_HZ-1u)/COMP_V11_PANEL_DELAY_REFERENCE_HZ);
}
#endif
