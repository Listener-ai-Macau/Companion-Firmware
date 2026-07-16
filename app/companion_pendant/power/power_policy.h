#ifndef COMPANION_POWER_POLICY_H
#define COMPANION_POWER_POLICY_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_POWER_IDLE_MINUTES_DISABLED 0u
#define COMP_POWER_IDLE_MINUTES_DEFAULT 3u
#define COMP_POWER_IDLE_MINUTES_MAX 60u

typedef enum {
    COMP_POWER_BLOCKER_NONE = 0u,
    COMP_POWER_BLOCKER_BOOT = 1u << 0,
    COMP_POWER_BLOCKER_MIC_CAPTURE = 1u << 1,
    COMP_POWER_BLOCKER_TOUCH_CONTACT = 1u << 2,
    COMP_POWER_BLOCKER_MENU_TIMER = 1u << 3,
    COMP_POWER_BLOCKER_SCREEN_MAINTENANCE = 1u << 4,
    COMP_POWER_BLOCKER_SCREEN_WAIT = 1u << 5,
    /* Keep the MCU awake only through the bounded first-tap decision window.
     * A confirmed daily double tap must not be stranded in Stop. */
    COMP_POWER_BLOCKER_TOUCH_CONFIRMATION = 1u << 6,
} comp_power_blocker_t;

typedef struct {
    uint32_t blockers;
    bool touch_wake_ready;
} comp_power_policy_t;

typedef struct {
    uint8_t idle_minutes;
} comp_power_idle_settings_t;

void comp_power_policy_init(comp_power_policy_t *policy);
void comp_power_policy_set_touch_wake_ready(comp_power_policy_t *policy,
                                            bool ready);
void comp_power_policy_set_blocker(comp_power_policy_t *policy,
                                   comp_power_blocker_t blocker,
                                   bool active);
bool comp_power_policy_stop_allowed(const comp_power_policy_t *policy);
bool comp_power_policy_self_test(void);

void comp_power_idle_settings_init(comp_power_idle_settings_t *settings);
bool comp_power_idle_settings_set_minutes(comp_power_idle_settings_t *settings,
                                          uint8_t minutes);
uint8_t comp_power_idle_settings_minutes(
    const comp_power_idle_settings_t *settings);
uint32_t comp_power_idle_settings_timeout_ms(
    const comp_power_idle_settings_t *settings);
bool comp_power_idle_settings_self_test(void);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_POWER_POLICY_H */
