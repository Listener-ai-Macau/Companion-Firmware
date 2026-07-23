#include "refresh_policy.h"

#include <stddef.h>

void comp_epaper_refresh_policy_init(comp_epaper_refresh_policy_t *policy,
                                     uint8_t partial_limit)
{
    if (policy == NULL) {
        return;
    }
    policy->partial_limit = partial_limit == 0u
                                ? COMP_EPAPER_REFRESH_DEFAULT_PARTIAL_LIMIT
                                : partial_limit;
    policy->partial_count = 0u;
    policy->baseline_valid = false;
}

comp_epaper_refresh_selection_t comp_epaper_refresh_policy_select(
    const comp_epaper_refresh_policy_t *policy,
    comp_epaper_refresh_mode_t requested_mode)
{
    comp_epaper_refresh_selection_t selection = {
        .decision = COMP_EPAPER_REFRESH_DECISION_FULL,
        .reason = COMP_EPAPER_REFRESH_REASON_AUTO_DEFAULT_FULL,
        .partial_count_before = policy == NULL ? 0u : policy->partial_count,
    };

    if (requested_mode == COMP_EPAPER_REFRESH_FULL) {
        selection.reason = COMP_EPAPER_REFRESH_REASON_REQUESTED_FULL;
    } else if (requested_mode == COMP_EPAPER_REFRESH_PARTIAL ||
               requested_mode == COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE ||
               requested_mode == COMP_EPAPER_REFRESH_MAINTENANCE) {
        if (policy == NULL || !policy->baseline_valid) {
            selection.reason = COMP_EPAPER_REFRESH_REASON_BASELINE_REQUIRED;
        } else if (requested_mode == COMP_EPAPER_REFRESH_MAINTENANCE) {
            /* Explicit menu boundaries may restore contrast once. Normal
             * touches never schedule this path after a quiet-time delay. */
            selection.decision = COMP_EPAPER_REFRESH_DECISION_FAST;
            selection.reason = COMP_EPAPER_REFRESH_REASON_MAINTENANCE_BOUNDARY;
        } else if (policy->partial_limit != UINT8_MAX &&
                   policy->partial_count >= policy->partial_limit) {
            selection.decision = COMP_EPAPER_REFRESH_DECISION_FAST;
            selection.reason = COMP_EPAPER_REFRESH_REASON_PARTIAL_LIMIT;
        } else {
            selection.decision = COMP_EPAPER_REFRESH_DECISION_PARTIAL;
            selection.reason = COMP_EPAPER_REFRESH_REASON_REQUESTED_PARTIAL;
        }
    }
    return selection;
}

void comp_epaper_refresh_policy_commit(comp_epaper_refresh_policy_t *policy,
                                       comp_epaper_refresh_decision_t decision,
                                       bool succeeded)
{
    if (policy == NULL) {
        return;
    }
    if (!succeeded) {
        policy->baseline_valid = false;
        policy->partial_count = 0u;
    } else if (decision == COMP_EPAPER_REFRESH_DECISION_FULL ||
               decision == COMP_EPAPER_REFRESH_DECISION_FAST) {
        policy->baseline_valid = true;
        policy->partial_count = 0u;
    } else if (policy->partial_count < UINT8_MAX) {
        policy->partial_count++;
    }
}

bool comp_epaper_refresh_policy_self_test(void)
{
    comp_epaper_refresh_policy_t policy;
    comp_epaper_refresh_selection_t selection;

    comp_epaper_refresh_policy_init(&policy, 5u);
    selection = comp_epaper_refresh_policy_select(&policy,
                                                  COMP_EPAPER_REFRESH_PARTIAL);
    if (selection.decision != COMP_EPAPER_REFRESH_DECISION_FULL ||
        selection.reason != COMP_EPAPER_REFRESH_REASON_BASELINE_REQUIRED) {
        return false;
    }
    comp_epaper_refresh_policy_commit(&policy, selection.decision, true);

    for (uint8_t index = 0u; index < 5u; ++index) {
        selection = comp_epaper_refresh_policy_select(&policy,
                                                      COMP_EPAPER_REFRESH_PARTIAL);
        if (selection.decision != COMP_EPAPER_REFRESH_DECISION_PARTIAL ||
            selection.partial_count_before != index) {
            return false;
        }
        comp_epaper_refresh_policy_commit(&policy, selection.decision, true);
    }

    selection = comp_epaper_refresh_policy_select(&policy,
                                                  COMP_EPAPER_REFRESH_PARTIAL);
    if (selection.decision != COMP_EPAPER_REFRESH_DECISION_FAST ||
        selection.reason != COMP_EPAPER_REFRESH_REASON_PARTIAL_LIMIT) {
        return false;
    }
    comp_epaper_refresh_policy_commit(&policy, selection.decision, true);
    if (!policy.baseline_valid || policy.partial_count != 0u) {
        return false;
    }

    comp_epaper_refresh_policy_init(&policy, 5u);
    comp_epaper_refresh_policy_commit(&policy,
                                      COMP_EPAPER_REFRESH_DECISION_FULL,
                                      true);
    for (uint8_t index = 0u; index < policy.partial_limit; ++index) {
        selection = comp_epaper_refresh_policy_select(
            &policy, COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE);
        if (selection.decision != COMP_EPAPER_REFRESH_DECISION_PARTIAL ||
            selection.partial_count_before != index ||
            selection.reason != COMP_EPAPER_REFRESH_REASON_REQUESTED_PARTIAL) {
            return false;
        }
        comp_epaper_refresh_policy_commit(&policy, selection.decision, true);
    }
    selection = comp_epaper_refresh_policy_select(
        &policy, COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE);
    if (selection.decision != COMP_EPAPER_REFRESH_DECISION_FAST ||
        selection.reason != COMP_EPAPER_REFRESH_REASON_PARTIAL_LIMIT) {
        return false;
    }
    comp_epaper_refresh_policy_init(&policy, 5u);
    comp_epaper_refresh_policy_commit(&policy,
                                      COMP_EPAPER_REFRESH_DECISION_FULL,
                                      true);
    selection = comp_epaper_refresh_policy_select(
        &policy, COMP_EPAPER_REFRESH_MAINTENANCE);
    if (selection.decision != COMP_EPAPER_REFRESH_DECISION_FAST ||
        selection.reason != COMP_EPAPER_REFRESH_REASON_MAINTENANCE_BOUNDARY) {
        return false;
    }

    /* UINT8_MAX is reserved for a compile-time visual demo that must never
     * inject an automatic maintenance refresh into its shared score. */
    comp_epaper_refresh_policy_init(&policy, UINT8_MAX);
    comp_epaper_refresh_policy_commit(&policy,
                                      COMP_EPAPER_REFRESH_DECISION_FULL,
                                      true);
    policy.partial_count = UINT8_MAX;
    selection = comp_epaper_refresh_policy_select(
        &policy, COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE);
    return selection.decision == COMP_EPAPER_REFRESH_DECISION_PARTIAL &&
           selection.reason == COMP_EPAPER_REFRESH_REASON_REQUESTED_PARTIAL;
}
