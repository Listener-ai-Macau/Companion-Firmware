#ifndef COMPANION_POWER_POLICY_H
#define COMPANION_POWER_POLICY_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    COMP_POWER_BLOCKER_NONE = 0u,
    COMP_POWER_BLOCKER_BOOT = 1u << 0,
    COMP_POWER_BLOCKER_MIC_CAPTURE = 1u << 1,
    COMP_POWER_BLOCKER_TOUCH_CONTACT = 1u << 2,
    COMP_POWER_BLOCKER_MENU_TIMER = 1u << 3,
    COMP_POWER_BLOCKER_SCREEN_MAINTENANCE = 1u << 4,
    COMP_POWER_BLOCKER_SCREEN_WAIT = 1u << 5,
} comp_power_blocker_t;

typedef struct {
    uint32_t blockers;
    bool touch_wake_ready;
} comp_power_policy_t;

void comp_power_policy_init(comp_power_policy_t *policy);
void comp_power_policy_set_touch_wake_ready(comp_power_policy_t *policy,
                                            bool ready);
void comp_power_policy_set_blocker(comp_power_policy_t *policy,
                                   comp_power_blocker_t blocker,
                                   bool active);
bool comp_power_policy_stop_allowed(const comp_power_policy_t *policy);
bool comp_power_policy_self_test(void);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_POWER_POLICY_H */
