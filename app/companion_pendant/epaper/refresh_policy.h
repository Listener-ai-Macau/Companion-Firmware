#ifndef COMPANION_EPAPER_REFRESH_POLICY_H
#define COMPANION_EPAPER_REFRESH_POLICY_H

#include "display_queue.h"

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_EPAPER_REFRESH_DEFAULT_PARTIAL_LIMIT 5u

typedef enum {
    COMP_EPAPER_REFRESH_DECISION_FULL = 0,
    COMP_EPAPER_REFRESH_DECISION_PARTIAL = 1,
    COMP_EPAPER_REFRESH_DECISION_FAST = 2,
} comp_epaper_refresh_decision_t;

typedef enum {
    COMP_EPAPER_REFRESH_REASON_REQUESTED_FULL = 0,
    COMP_EPAPER_REFRESH_REASON_REQUESTED_PARTIAL = 1,
    COMP_EPAPER_REFRESH_REASON_AUTO_DEFAULT_FULL = 2,
    COMP_EPAPER_REFRESH_REASON_BASELINE_REQUIRED = 3,
    COMP_EPAPER_REFRESH_REASON_PARTIAL_LIMIT = 4,
    COMP_EPAPER_REFRESH_REASON_MAINTENANCE_BOUNDARY = 5,
} comp_epaper_refresh_reason_t;

typedef struct {
    uint8_t partial_limit;
    uint8_t partial_count;
    bool baseline_valid;
} comp_epaper_refresh_policy_t;

typedef struct {
    comp_epaper_refresh_decision_t decision;
    comp_epaper_refresh_reason_t reason;
    uint8_t partial_count_before;
} comp_epaper_refresh_selection_t;

void comp_epaper_refresh_policy_init(comp_epaper_refresh_policy_t *policy,
                                     uint8_t partial_limit);
comp_epaper_refresh_selection_t comp_epaper_refresh_policy_select(
    const comp_epaper_refresh_policy_t *policy,
    comp_epaper_refresh_mode_t requested_mode);
void comp_epaper_refresh_policy_commit(comp_epaper_refresh_policy_t *policy,
                                       comp_epaper_refresh_decision_t decision,
                                       bool succeeded);
bool comp_epaper_refresh_policy_self_test(void);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_REFRESH_POLICY_H */
