#include "motion_coordinator.h"

#include <stdio.h>

static const char *const k_phase_names[COMP_EPAPER_MOTION_PHASE_COUNT] = {
    "hold", "orient", "anticipate", "accent", "follow", "settle",
};

int main(void)
{
    for (uint32_t family = 0u;
         family < COMP_EPAPER_MOTION_FAMILY_COUNT;
         ++family) {
        comp_epaper_motion_coordinator_t coordinator;
        comp_epaper_motion_request_t request;
        comp_epaper_motion_snapshot_t snapshot;
        uint32_t now_ms = 1000u;
        uint32_t commits = 0u;

        comp_epaper_motion_coordinator_init(&coordinator);
        comp_epaper_motion_coordinator_enter_daily(
            &coordinator,
            now_ms,
            (comp_epaper_motion_family_t)family);
        while (commits < 100u) {
            if (!comp_epaper_motion_coordinator_take_request(
                    &coordinator, now_ms, &request)) {
                fprintf(stderr,
                        "trace stalled family=%lu commits=%lu now_ms=%lu\n",
                        (unsigned long)family,
                        (unsigned long)commits,
                        (unsigned long)now_ms);
                return 1;
            }
            if (request.phase >= COMP_EPAPER_MOTION_PHASE_COUNT) {
                fprintf(stderr, "invalid phase=%u\n", (unsigned)request.phase);
                return 1;
            }
            printf("%s|%s|%lu|%u|%s|%u|%u|%u|life_%s_e%lu_s%u_%s_%s\n",
                   comp_epaper_motion_family_name(request.family),
                   comp_epaper_motion_action_name(request.action),
                   (unsigned long)request.episode,
                   (unsigned)request.phrase,
                   k_phase_names[request.phase],
                   (unsigned)request.variation,
                   (unsigned)request.action_step,
                   (unsigned)request.dwell_commits,
                   comp_epaper_motion_family_name(request.family),
                   (unsigned long)request.episode,
                   (unsigned)request.action_step,
                   comp_epaper_motion_action_name(request.action),
                   k_phase_names[request.phase]);
            commits += request.dwell_commits;
            if (!comp_epaper_motion_coordinator_complete_request(
                    &coordinator, request.token, now_ms + 1u, true)) {
                fprintf(stderr, "completion rejected token=%lu\n",
                        (unsigned long)request.token);
                return 1;
            }
            comp_epaper_motion_coordinator_snapshot(&coordinator, &snapshot);
            now_ms = snapshot.next_request_ms;
        }
    }
    return 0;
}
