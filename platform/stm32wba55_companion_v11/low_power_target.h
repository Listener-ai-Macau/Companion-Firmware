#ifndef COMP_V11_LOW_POWER_TARGET_H
#define COMP_V11_LOW_POWER_TARGET_H
#include "product_app.h"
#ifndef COMPANION_WBA_EXPERIMENTAL_STOP1
#define COMPANION_WBA_EXPERIMENTAL_STOP1 0
#endif
/* Stop1 is build-selected: bounded trials or automatic idle. Both retain
 * the normal audio/storage/input/radio policy and clock restoration. */
#if defined(COMPANION_WBA_BLE_LINKED) && COMPANION_WBA_EXPERIMENTAL_STOP1
/* WBA55 has external IRQs 0..71. Pending enabled interrupts are evidence at
 * this instant, not a claim that one of them uniquely caused the wake. */
#define COMP_V11_STOP_IRQ_WORDS 3u
typedef struct {
    uint32_t pending_enabled[COMP_V11_STOP_IRQ_WORDS];
    uint32_t icsr, exti_rising, exti_falling;
} comp_v11_stop_irq_snapshot_t;
typedef struct {
    comp_v11_stop_irq_snapshot_t before, after;
    bool captured, entered_stop;
} comp_v11_stop_wake_snapshot_t;
const comp_v11_stop_wake_snapshot_t *comp_v11_low_power_wake_snapshot(void);
bool comp_v11_low_power_arm_once(comp_v11_product_app_t *);
/* At most256 actual entries and5s; all original admission gates still apply. */
bool comp_v11_low_power_arm_window(comp_v11_product_app_t *);
uint32_t comp_v11_low_power_wake_flags(void);
/* Engineering first-failure stage; not an elapsed-time or energy receipt. */
uint32_t comp_v11_low_power_stage(void);
extern volatile uint32_t companion_stop1_entries;
#endif
void comp_v11_low_power_init(comp_v11_product_app_t *, bool ble_initialized);
void comp_v11_low_power_idle(comp_v11_product_app_t *);
const char *comp_v11_low_power_identity(void);
void comp_v11_low_power_stats(uint32_t *entries, uint32_t *compensated_ms, uint32_t *failures);
#endif
