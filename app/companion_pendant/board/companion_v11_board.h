#ifndef COMPANION_V11_BOARD_H
#define COMPANION_V11_BOARD_H
#include "tca6408.h"

#define COMP_V11_MCU "STM32WBA55CGU6"
#define COMP_V11_REVISION "1.1-2026-09-19"
#define COMP_V11_NOR_BYTES UINT32_C(16777216)
#define COMP_V11_TCA_ADDRESS 0x20u
#define COMP_V11_TCA_INPUTS 0x2Du
#define COMP_V11_TP_INT 0x01u
#define COMP_V11_TP_RESET 0x02u
/* FT6336U Table 3-5 requires at least 300 ms after reset release before
 * reporting points. Leave margin for the assembled board's translator. */
#define COMP_V11_TOUCH_STARTUP_MS 350u
#define COMP_V11_CHARGE_STAT 0x04u
#define COMP_V11_IMU_INT 0x08u
#define COMP_V11_SCREEN_POWER 0x10u
#define COMP_V11_CHARGE_PG 0x20u
#define COMP_V11_AMP_ENABLE 0x40u
#define COMP_V11_BATTERY_ENABLE 0x80u

typedef enum {
    COMP_V11_POWER_OFF, COMP_V11_POWER_SETTLE,
    COMP_V11_TOUCH_RESET_WAIT, COMP_V11_POWER_READY, COMP_V11_POWER_FAULT
} comp_v11_power_state_t;
typedef struct {
    comp_tca6408_t *io;
    comp_v11_power_state_t state;
    uint32_t changed_ms;
    bool switched;
} comp_v11_power_t;
void comp_v11_power_init(comp_v11_power_t *power, comp_tca6408_t *io);
/* Owner-confirmed rework disables the 3V power switch on the current board.
 * Retain touch reset sequencing, do not toggle P4, and reject power-off. */
void comp_v11_power_init_always_on(comp_v11_power_t *power, comp_tca6408_t *io);
bool comp_v11_power_request(comp_v11_power_t *power, bool on, uint32_t now_ms);
void comp_v11_power_poll(comp_v11_power_t *power, uint32_t now_ms);
/* V1.1 68K:68K divider at VDDA=1.8V cannot measure a 4.2V battery.
 * Default sampling stays disabled, even if an ADC read would fit an integer.
 * Board rework/calibrated divider must be explicitly provided by the caller. */
bool comp_v11_battery_divider_safe(uint32_t top_ohm, uint32_t bottom_ohm,
                                  uint16_t vdda_mv, uint16_t max_battery_mv);
bool comp_v11_battery_mv(uint16_t adc, uint16_t adc_full_scale,
                         uint16_t vdda_mv, uint32_t top_ohm,
                         uint32_t bottom_ohm, uint16_t *millivolts);
/* P7 is the active-high divider switch, PA5 remains an analog input.
 * Force the physical latch/direction rather than accepting a cached no-op.
 * Observation bits: latch=1, physical-high=2, read-ok=8. */
bool comp_v11_battery_enable(comp_tca6408_t *, bool enabled, uint8_t *observation);
#endif
