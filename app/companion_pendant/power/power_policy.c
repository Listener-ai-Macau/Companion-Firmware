#include "power_policy.h"

#include <string.h>

#define COMP_POWER_IDLE_MINUTE_MS 60000u

void comp_power_policy_init(comp_power_policy_t *policy)
{
    if (policy == NULL) {
        return;
    }
    memset(policy, 0, sizeof(*policy));
    policy->blockers = COMP_POWER_BLOCKER_BOOT;
}

void comp_power_policy_set_touch_wake_ready(comp_power_policy_t *policy,
                                            bool ready)
{
    if (policy != NULL) {
        policy->touch_wake_ready = ready;
    }
}

void comp_power_policy_set_blocker(comp_power_policy_t *policy,
                                   comp_power_blocker_t blocker,
                                   bool active)
{
    if (policy == NULL || blocker == COMP_POWER_BLOCKER_NONE) {
        return;
    }
    if (active) {
        policy->blockers |= (uint32_t)blocker;
    } else {
        policy->blockers &= ~(uint32_t)blocker;
    }
}

void comp_power_policy_set_button_wake_ready(comp_power_policy_t *policy, bool ready)
{ if (policy != NULL) policy->button_wake_ready=ready; }

bool comp_power_policy_stop_allowed(const comp_power_policy_t *policy)
{
    return policy != NULL && (policy->touch_wake_ready || policy->button_wake_ready) &&
           policy->blockers == COMP_POWER_BLOCKER_NONE;
}
bool comp_power_policy_idle_requested(const comp_power_policy_t *policy)
{
    return policy != NULL && (policy->touch_wake_ready || policy->button_wake_ready) &&
        (policy->blockers & ~(uint32_t)COMP_POWER_BLOCKER_IMU_SETTLING)==0u;
}

bool comp_power_policy_self_test(void)
{
    comp_power_policy_t policy;
    const comp_power_blocker_t blockers[] = {
        COMP_POWER_BLOCKER_MIC_CAPTURE,
        COMP_POWER_BLOCKER_TOUCH_CONTACT,
        COMP_POWER_BLOCKER_MENU_TIMER,
        COMP_POWER_BLOCKER_SCREEN_MAINTENANCE,
        COMP_POWER_BLOCKER_SCREEN_WAIT,
        COMP_POWER_BLOCKER_TOUCH_CONFIRMATION,
        COMP_POWER_BLOCKER_UI_PENDING,
        COMP_POWER_BLOCKER_PLAYBACK,
        COMP_POWER_BLOCKER_BUTTON,
        COMP_POWER_BLOCKER_BATTERY_SAMPLE,
        COMP_POWER_BLOCKER_RECORDING_TRANSFER,
        COMP_POWER_BLOCKER_STORAGE,
        COMP_POWER_BLOCKER_UPDATE,
        COMP_POWER_BLOCKER_BOND_NVM,
        COMP_POWER_BLOCKER_IMU_SETTLING,
    };

    comp_power_policy_init(&policy);
    if (comp_power_policy_stop_allowed(&policy)) {
        return false;
    }
    comp_power_policy_set_touch_wake_ready(&policy, true);
    comp_power_policy_set_blocker(&policy, COMP_POWER_BLOCKER_BOOT, false);
    if (!comp_power_policy_stop_allowed(&policy)) {
        return false;
    }

    for (uint32_t index = 0u; index < sizeof(blockers) / sizeof(blockers[0]); ++index) {
        comp_power_policy_set_blocker(&policy, blockers[index], true);
        if (comp_power_policy_stop_allowed(&policy)) {
            return false;
        }
        comp_power_policy_set_blocker(&policy, blockers[index], false);
        if (!comp_power_policy_stop_allowed(&policy)) {
            return false;
        }
    }

    comp_power_policy_set_touch_wake_ready(&policy, false);
    if (comp_power_policy_stop_allowed(&policy)) return false;
    comp_power_policy_set_button_wake_ready(&policy, true);
    return comp_power_policy_stop_allowed(&policy);
}

void comp_power_idle_settings_init(comp_power_idle_settings_t *settings)
{
    if (settings != NULL) {
        settings->idle_minutes = COMP_POWER_IDLE_MINUTES_DEFAULT;
    }
}

bool comp_power_idle_settings_set_minutes(comp_power_idle_settings_t *settings,
                                          uint8_t minutes)
{
    if (settings == NULL || minutes > COMP_POWER_IDLE_MINUTES_MAX) {
        return false;
    }
    settings->idle_minutes = minutes;
    return true;
}

uint8_t comp_power_idle_settings_minutes(
    const comp_power_idle_settings_t *settings)
{
    return settings == NULL ? COMP_POWER_IDLE_MINUTES_DEFAULT
                            : settings->idle_minutes;
}

uint32_t comp_power_idle_settings_timeout_ms(
    const comp_power_idle_settings_t *settings)
{
    return (uint32_t)comp_power_idle_settings_minutes(settings) *
           COMP_POWER_IDLE_MINUTE_MS;
}

bool comp_power_idle_settings_self_test(void)
{
    comp_power_idle_settings_t settings;

    comp_power_idle_settings_init(&settings);
    if (comp_power_idle_settings_minutes(&settings) !=
            COMP_POWER_IDLE_MINUTES_DEFAULT ||
        comp_power_idle_settings_timeout_ms(&settings) != 180000u) {
        return false;
    }
    if (!comp_power_idle_settings_set_minutes(
            &settings, COMP_POWER_IDLE_MINUTES_DISABLED) ||
        comp_power_idle_settings_timeout_ms(&settings) != 0u) {
        return false;
    }
    if (!comp_power_idle_settings_set_minutes(
            &settings, COMP_POWER_IDLE_MINUTES_MAX) ||
        comp_power_idle_settings_timeout_ms(&settings) != 3600000u) {
        return false;
    }
    return !comp_power_idle_settings_set_minutes(
               &settings, (uint8_t)(COMP_POWER_IDLE_MINUTES_MAX + 1u)) &&
           comp_power_idle_settings_minutes(&settings) ==
               COMP_POWER_IDLE_MINUTES_MAX;
}
