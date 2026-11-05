#include "overlay_commit_scheduler.h"

#include <stdio.h>
#include <stdlib.h>

static void require_true(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        exit(1);
    }
}

int main(void)
{
    comp_epaper_overlay_commit_scheduler_t scheduler;
    comp_epaper_overlay_commit_report_t report = {0};

    comp_epaper_overlay_commit_scheduler_init(&scheduler);
    require_true(!comp_epaper_overlay_commit_scheduler_active(&scheduler),
                 "scheduler starts inactive");
    require_true(comp_epaper_overlay_commit_scheduler_activate(&scheduler),
                 "overlay activation owns one ready slot");
    require_true(comp_epaper_overlay_commit_scheduler_prepare(&scheduler, false),
                 "initial phase is prepared without advancing");
    require_true(comp_epaper_overlay_commit_scheduler_mark_dispatched(
                     &scheduler, 101u, 1000u),
                 "initial overlay request is tracked");
    require_true(!comp_epaper_overlay_commit_scheduler_ready(&scheduler),
                 "BUSY keeps the producer from accumulating requests");
    require_true(!comp_epaper_overlay_commit_scheduler_prepare(&scheduler, true),
                 "a second phase cannot queue behind BUSY");
    require_true(!comp_epaper_overlay_commit_scheduler_complete(
                     &scheduler, 999u, true, 1456u, &report),
                 "an unrelated panel completion cannot release the slot");
    require_true(comp_epaper_overlay_commit_scheduler_complete(
                     &scheduler, 101u, true, 1456u, &report),
                 "matching visible completion releases the next slot");
    require_true(report.request_to_visible_ms == 456u &&
                     report.visible_to_dispatch_ms == 0u &&
                     report.candidate_advanced == 0u,
                 "initial physical timing is reported without a fixed dwell");
    require_true(comp_epaper_overlay_commit_scheduler_ready(&scheduler),
                 "visible completion rearms immediately");

    require_true(comp_epaper_overlay_commit_scheduler_prepare(&scheduler, true),
                 "next waveform phase advances only after visible completion");
    require_true(comp_epaper_overlay_commit_scheduler_mark_dispatched(
                     &scheduler, 102u, 1457u),
                 "first available post-commit slot is accepted");
    require_true(comp_epaper_overlay_commit_scheduler_complete(
                     &scheduler, 102u, false, 1913u, &report),
                 "failed panel transaction returns producer ownership");
    require_true(report.visible_to_dispatch_ms == 1u &&
                     report.candidate_advanced == 1u &&
                     report.visible == 0u,
                 "failure report preserves phase rollback and slot timing");
    require_true(scheduler.visible_commit_count == 1u &&
                     scheduler.failed_commit_count == 1u,
                 "visible and failed commits are counted separately");

    require_true(comp_epaper_overlay_commit_scheduler_prepare(&scheduler, true),
                 "failed phase can be prepared again rather than skipped");
    require_true(comp_epaper_overlay_commit_scheduler_mark_dispatched(
                     &scheduler, 103u, 1914u),
                 "retry remains single-slot");
    comp_epaper_overlay_commit_scheduler_stop(&scheduler);
    require_true(!comp_epaper_overlay_commit_scheduler_complete(
                     &scheduler, 103u, true, 2370u, &report),
                 "stop invalidates an obsolete in-flight overlay completion");
    require_true(!comp_epaper_overlay_commit_scheduler_active(&scheduler),
                 "stop leaves no timed overlay producer active");

    require_true(comp_epaper_overlay_commit_scheduler_activate(&scheduler),
                 "a later recording session can reactivate the scheduler");
    require_true(comp_epaper_overlay_commit_scheduler_prepare(&scheduler, false),
                 "reactivated session prepares its own first phase");
    require_true(comp_epaper_overlay_commit_scheduler_mark_dispatched(
                     &scheduler, 201u, 65000u),
                 "reactivated first phase is dispatched");
    require_true(comp_epaper_overlay_commit_scheduler_complete(
                     &scheduler, 201u, true, 65456u, &report),
                 "reactivated first phase completes visibly");
    require_true(report.request_to_visible_ms == 456u &&
                     report.visible_to_dispatch_ms == 0u,
                 "a new session cannot inherit the prior session gap");

    puts("PASS: overlay commit scheduler");
    return 0;
}
