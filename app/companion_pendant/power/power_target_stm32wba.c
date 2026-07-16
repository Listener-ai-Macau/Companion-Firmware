#include "power_target_stm32wba.h"

#include <string.h>

const char *comp_power_stm32wba_target_name(comp_power_stm32wba_target_t target)
{
    switch (target) {
    case COMP_POWER_STM32WBA_TARGET_WBA55:
        return "WBA55";
    case COMP_POWER_STM32WBA_TARGET_WBA65:
        return "WBA65";
    default:
        return "WBA";
    }
}

void comp_power_stm32wba_init(comp_power_stm32wba_t *target,
                              const comp_power_stm32wba_config_t *config)
{
    if (target == NULL) {
        return;
    }
    memset(target, 0, sizeof(*target));
    comp_power_idle_settings_init(&target->idle_settings);
    if (config != NULL) {
        target->config = *config;
    }
}

bool comp_power_stm32wba_ready(const comp_power_stm32wba_t *target)
{
    return target != NULL &&
           (target->config.target == COMP_POWER_STM32WBA_TARGET_WBA55 ||
            target->config.target == COMP_POWER_STM32WBA_TARGET_WBA65) &&
           target->config.configure_touch_wake != NULL &&
           target->config.set_stop_allowed != NULL;
}

bool comp_power_stm32wba_prepare_touch_wake(comp_power_stm32wba_t *target,
                                            comp_power_policy_t *policy)
{
    bool configured;

    if (!comp_power_stm32wba_ready(target) || policy == NULL) {
        return false;
    }
    configured = target->config.configure_touch_wake(target->config.context);
    target->touch_wake_configured = configured;
    comp_power_policy_set_touch_wake_ready(policy, configured);
    if (!configured) {
        (void)target->config.set_stop_allowed(target->config.context, false);
        target->stop_state_applied = true;
        target->last_stop_allowed = false;
        target->last_apply_succeeded = false;
    }
    return configured;
}

bool comp_power_stm32wba_apply_policy(comp_power_stm32wba_t *target,
                                      comp_power_policy_t *policy)
{
    bool requested;
    bool applied;

    if (!comp_power_stm32wba_ready(target) || policy == NULL) {
        return false;
    }
    requested = comp_power_policy_stop_allowed(policy);
    if (target->stop_state_applied && target->last_stop_allowed == requested) {
        return target->last_apply_succeeded;
    }

    applied = target->config.set_stop_allowed(target->config.context, requested);
    target->stop_state_applied = true;
    target->last_stop_allowed = requested;
    target->last_apply_succeeded = applied;
    if (!applied && requested) {
        comp_power_policy_set_touch_wake_ready(policy, false);
        (void)target->config.set_stop_allowed(target->config.context, false);
        target->last_stop_allowed = false;
    }
    return applied;
}

typedef struct {
    bool touch_wake_result;
    bool set_stop_result;
    bool last_stop_allowed;
    uint32_t configure_calls;
    uint32_t set_stop_calls;
} comp_power_stm32wba_self_test_context_t;

static bool self_test_configure_touch_wake(void *context)
{
    comp_power_stm32wba_self_test_context_t *test = context;

    test->configure_calls++;
    return test->touch_wake_result;
}

static bool self_test_set_stop_allowed(void *context, bool allowed)
{
    comp_power_stm32wba_self_test_context_t *test = context;

    test->set_stop_calls++;
    test->last_stop_allowed = allowed;
    return test->set_stop_result;
}

bool comp_power_stm32wba_self_test(void)
{
    comp_power_stm32wba_t target;
    comp_power_policy_t policy;
    comp_power_stm32wba_self_test_context_t test = {
        .touch_wake_result = true,
        .set_stop_result = true,
    };
    const comp_power_stm32wba_config_t config = {
        .target = COMP_POWER_STM32WBA_TARGET_WBA55,
        .configure_touch_wake = self_test_configure_touch_wake,
        .set_stop_allowed = self_test_set_stop_allowed,
        .context = &test,
    };

    comp_power_stm32wba_init(&target, &config);
    comp_power_policy_init(&policy);
    if (comp_power_idle_settings_timeout_ms(&target.idle_settings) != 180000u ||
        !comp_power_stm32wba_prepare_touch_wake(&target, &policy) ||
        test.configure_calls != 1u ||
        !comp_power_stm32wba_apply_policy(&target, &policy) ||
        test.last_stop_allowed) {
        return false;
    }

    comp_power_policy_set_blocker(&policy, COMP_POWER_BLOCKER_BOOT, false);
    if (!comp_power_stm32wba_apply_policy(&target, &policy) ||
        !test.last_stop_allowed) {
        return false;
    }
    comp_power_policy_set_blocker(&policy, COMP_POWER_BLOCKER_MIC_CAPTURE, true);
    if (!comp_power_stm32wba_apply_policy(&target, &policy) ||
        test.last_stop_allowed) {
        return false;
    }

    test.touch_wake_result = false;
    target.stop_state_applied = false;
    if (comp_power_stm32wba_prepare_touch_wake(&target, &policy) ||
        comp_power_policy_stop_allowed(&policy) || test.last_stop_allowed) {
        return false;
    }
    return test.set_stop_calls >= 4u;
}
