#include "power_policy.h"

#include <stdio.h>

static int fail(const char *message)
{
    fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

int main(void)
{
    comp_power_idle_settings_t settings;

    if (!comp_power_policy_self_test() || !comp_power_idle_settings_self_test()) {
        return fail("portable policy self-test");
    }

    comp_power_idle_settings_init(&settings);
    if (comp_power_idle_settings_minutes(&settings) !=
            COMP_POWER_IDLE_MINUTES_DEFAULT ||
        comp_power_idle_settings_timeout_ms(&settings) != 180000u) {
        return fail("three-minute default");
    }

    if (!comp_power_idle_settings_set_minutes(&settings, 5u) ||
        comp_power_idle_settings_timeout_ms(&settings) != 300000u) {
        return fail("five-minute selection");
    }

    if (comp_power_idle_settings_set_minutes(
            &settings, (uint8_t)(COMP_POWER_IDLE_MINUTES_MAX + 1u)) ||
        comp_power_idle_settings_minutes(&settings) != 5u) {
        return fail("invalid selection preserves setting");
    }

    if (!comp_power_idle_settings_set_minutes(
            &settings, COMP_POWER_IDLE_MINUTES_DISABLED) ||
        comp_power_idle_settings_timeout_ms(&settings) != 0u) {
        return fail("disabled selection");
    }

    printf("PASS: power idle default=3m configurable=0..%um\n",
           (unsigned)COMP_POWER_IDLE_MINUTES_MAX);
    return 0;
}
