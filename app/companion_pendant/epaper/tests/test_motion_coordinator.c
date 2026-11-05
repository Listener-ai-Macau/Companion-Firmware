#include "motion_coordinator.h"

#include <stdio.h>

typedef struct {
    comp_epaper_motion_action_t action;
    comp_epaper_motion_phase_t phase;
    uint8_t phrase;
    uint8_t variation;
    uint8_t action_step;
    uint8_t dwell_commits;
} expected_beat_t;

static int require_true(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    return 0;
}

static int take_expected(comp_epaper_motion_coordinator_t *coordinator,
                         uint32_t now_ms,
                         const expected_beat_t *expected,
                         comp_epaper_motion_request_t *request)
{
    if (!comp_epaper_motion_coordinator_take_request(coordinator,
                                                      now_ms,
                                                      request)) {
        fprintf(stderr, "FAIL: expected request at %lu\n", (unsigned long)now_ms);
        return 1;
    }
    if (request->action != expected->action ||
        request->phase != expected->phase ||
        request->phrase != expected->phrase ||
        request->variation != expected->variation ||
        request->action_step != expected->action_step ||
        request->dwell_commits != expected->dwell_commits) {
        fprintf(stderr,
                "FAIL: beat got family=%s action=%s phase=%u phrase=%u variation=%u step=%u dwell=%u\n",
                comp_epaper_motion_family_name(request->family),
                comp_epaper_motion_action_name(request->action),
                (unsigned)request->phase,
                (unsigned)request->phrase,
                (unsigned)request->variation,
                (unsigned)request->action_step,
                (unsigned)request->dwell_commits);
        return 1;
    }
    return 0;
}

static int same_authored_tuple(const comp_epaper_motion_request_t *left,
                               const comp_epaper_motion_request_t *right)
{
    return left->family == right->family &&
           left->action == right->action &&
           left->episode == right->episode &&
           left->phase == right->phase &&
           left->phrase == right->phrase &&
           left->variation == right->variation &&
           left->action_step == right->action_step &&
           left->dwell_commits == right->dwell_commits;
}

int main(void)
{
    /* The accepted intent keeps its phrase/variation for the entire action.
     * Preserve original actions, phases, steps, dwell and deterministic seeds. */
    static const expected_beat_t curious_browser_beats[] = {
        {COMP_EPAPER_MOTION_ACTION_REST, COMP_EPAPER_MOTION_PHASE_HOLD, 1u, 1u, 0u, 3u},
        {COMP_EPAPER_MOTION_ACTION_NOTICE_LEFT, COMP_EPAPER_MOTION_PHASE_ORIENT, 1u, 1u, 0u, 3u},
        {COMP_EPAPER_MOTION_ACTION_NOTICE_LEFT, COMP_EPAPER_MOTION_PHASE_ANTICIPATE, 1u, 1u, 1u, 1u},
        {COMP_EPAPER_MOTION_ACTION_NOTICE_LEFT, COMP_EPAPER_MOTION_PHASE_ACCENT, 1u, 1u, 2u, 3u},
        {COMP_EPAPER_MOTION_ACTION_NOTICE_LEFT, COMP_EPAPER_MOTION_PHASE_FOLLOW, 1u, 1u, 3u, 4u},
        {COMP_EPAPER_MOTION_ACTION_NOTICE_LEFT, COMP_EPAPER_MOTION_PHASE_SETTLE, 1u, 1u, 4u, 2u},
        {COMP_EPAPER_MOTION_ACTION_REST, COMP_EPAPER_MOTION_PHASE_HOLD, 2u, 0u, 0u, 2u},
        {COMP_EPAPER_MOTION_ACTION_LISTEN_UP, COMP_EPAPER_MOTION_PHASE_ORIENT, 0u, 0u, 0u, 1u},
        {COMP_EPAPER_MOTION_ACTION_LISTEN_UP, COMP_EPAPER_MOTION_PHASE_ANTICIPATE, 0u, 0u, 1u, 1u},
        {COMP_EPAPER_MOTION_ACTION_LISTEN_UP, COMP_EPAPER_MOTION_PHASE_ACCENT, 0u, 0u, 2u, 3u},
        {COMP_EPAPER_MOTION_ACTION_LISTEN_UP, COMP_EPAPER_MOTION_PHASE_FOLLOW, 0u, 0u, 3u, 2u},
        {COMP_EPAPER_MOTION_ACTION_LISTEN_UP, COMP_EPAPER_MOTION_PHASE_SETTLE, 0u, 0u, 4u, 4u},
    };
    comp_epaper_motion_coordinator_t coordinator;
    comp_epaper_motion_coordinator_t recording_off;
    comp_epaper_motion_coordinator_t recording_on;
    comp_epaper_motion_coordinator_t seeded_a;
    comp_epaper_motion_coordinator_t seeded_b;
    comp_epaper_motion_snapshot_t snapshot;
    comp_epaper_motion_request_t request;
    comp_epaper_natural_blink_scheduler_t blink;
    comp_epaper_natural_blink_phase_t blink_phase;
    uint32_t now_ms = 1000u;

    comp_epaper_motion_coordinator_init(&coordinator);
    static const uint8_t blink_intervals[] = {11u, 14u, 19u, 12u,
                                              17u, 15u, 13u};
    const comp_epaper_natural_blink_config_t blink_config = {
        .cadence_ms = 480u,
        .first_interval_commits = 9u,
        .interval_count =
            (uint8_t)(sizeof(blink_intervals) / sizeof(blink_intervals[0])),
        .interval_commits = blink_intervals,
    };
    comp_epaper_natural_blink_init(&blink, &blink_config);
    if (require_true(!comp_epaper_motion_coordinator_take_request(
                         &coordinator, now_ms, &request),
                     "inactive coordinator emits no request")) {
        return 1;
    }

    comp_epaper_motion_coordinator_enter_daily(
        &coordinator, now_ms, COMP_EPAPER_MOTION_FAMILY_CURIOUS);
    for (uint32_t index = 0u;
         index < sizeof(curious_browser_beats) / sizeof(curious_browser_beats[0]);
         ++index) {
        uint32_t completion_ms;
        uint32_t deadline;

        if (take_expected(&coordinator,
                          now_ms,
                          &curious_browser_beats[index],
                          &request) ||
            require_true(request.family == COMP_EPAPER_MOTION_FAMILY_CURIOUS,
                         "request carries its stable emotion family") ||
            require_true(!comp_epaper_motion_coordinator_take_request(
                             &coordinator, now_ms, &request),
                         "only one panel request may be outstanding")) {
            return 1;
        }
        completion_ms = now_ms + 300u;
        if (require_true(comp_epaper_motion_coordinator_complete_request(
                             &coordinator,
                             request.token,
                             completion_ms,
                             true),
                         "matching visible completion advances life")) {
            return 1;
        }
        comp_epaper_motion_coordinator_snapshot(&coordinator, &snapshot);
        deadline = snapshot.next_request_ms;
        if (require_true(deadline - now_ms ==
                             curious_browser_beats[index].dwell_commits *
                                 COMP_EPAPER_MOTION_CADENCE_MS,
                         "browser life deadline advances from its own due time") ||
            require_true(deadline - now_ms <=
                             COMP_EPAPER_MOTION_DWELL_MAX_COMMITS *
                                 COMP_EPAPER_MOTION_CADENCE_MS,
                         "every visible change stays below two seconds") ||
            require_true(!comp_epaper_motion_coordinator_take_request(
                             &coordinator, deadline - 1u, &request),
                         "pose remains stable until its authored deadline")) {
            return 1;
        }
        now_ms = deadline;
    }

    comp_epaper_motion_coordinator_cancel(&coordinator,
                                           COMP_EPAPER_MOTION_CANCEL_TOUCH);
    if (require_true(!comp_epaper_motion_coordinator_take_request(
                         &coordinator, now_ms + 100u, &request),
                     "interaction cancellation immediately suppresses life") ||
        require_true(!comp_epaper_motion_coordinator_complete_request(
                         &coordinator, request.token, now_ms + 100u, true),
                     "cancelled completion cannot revive life")) {
        return 1;
    }

    comp_epaper_motion_coordinator_enter_daily(
        &coordinator, 20000u, COMP_EPAPER_MOTION_FAMILY_CALM);
    if (require_true(comp_epaper_motion_coordinator_take_request(
                         &coordinator, 20000u, &request),
                     "daily life resumes after interaction") ||
        require_true(request.family == COMP_EPAPER_MOTION_FAMILY_CALM &&
                         request.action == COMP_EPAPER_MOTION_ACTION_REST,
                     "resume starts a stable quiet episode for the new mood") ||
        require_true(comp_epaper_motion_coordinator_complete_request(
                         &coordinator, request.token, 20300u, false),
                     "failed panel transaction is recorded")) {
        return 1;
    }
    comp_epaper_motion_coordinator_snapshot(&coordinator, &snapshot);
    if (require_true(snapshot.next_request_ms == 20480u,
                     "failed frame retry keeps the absolute browser clock") ||
        require_true(snapshot.failed_requests == 1u,
                     "failure counter records the transaction") ||
        require_true(comp_epaper_motion_coordinator_take_request(
                         &coordinator, snapshot.next_request_ms, &request),
                     "failed frame retries the same life beat")) {
        return 1;
    }

    if (require_true(comp_epaper_motion_coordinator_complete_request(
                         &coordinator, request.token, 22900u, true),
                     "late visible completion is accepted once") ||
        (comp_epaper_motion_coordinator_snapshot(&coordinator, &snapshot),
         require_true(snapshot.next_request_ms > 22900u,
                      "late panel completion leaves no overdue pose backlog")) ||
        require_true((snapshot.next_request_ms - 20480u) %
                         COMP_EPAPER_MOTION_CADENCE_MS == 0u,
                     "late sampling preserves the browser clock phase")) {
        return 1;
    }

    comp_epaper_motion_coordinator_cancel(&coordinator,
                                           COMP_EPAPER_MOTION_CANCEL_LOW_POWER);
    comp_epaper_motion_coordinator_enter_daily(
        &coordinator, 100u, COMP_EPAPER_MOTION_FAMILY_CALM);
    if (require_true(comp_epaper_motion_coordinator_idle_timeout_elapsed(
                         &coordinator,
                         100u + COMP_EPAPER_MOTION_IDLE_TIMEOUT_MS),
                     "low-power deadline is observable") ||
        require_true(!comp_epaper_motion_coordinator_take_request(
                         &coordinator,
                         100u + COMP_EPAPER_MOTION_IDLE_TIMEOUT_MS,
                         &request),
                     "no frame starts at or after low-power deadline")) {
        return 1;
    }

    comp_epaper_motion_coordinator_enter_daily(
        &coordinator, 100u, COMP_EPAPER_MOTION_FAMILY_CALM);
    comp_epaper_motion_coordinator_keep_awake(
        &coordinator, 100u + COMP_EPAPER_MOTION_IDLE_TIMEOUT_MS - 1u);
    if (require_true(!comp_epaper_motion_coordinator_idle_timeout_elapsed(
                         &coordinator,
                         100u + COMP_EPAPER_MOTION_IDLE_TIMEOUT_MS),
                     "authored continuous scheduler renews awake deadline") ||
        require_true(comp_epaper_motion_coordinator_take_request(
                         &coordinator,
                         100u + COMP_EPAPER_MOTION_IDLE_TIMEOUT_MS,
                         &request),
                     "renewed browser scheduler continues emitting life")) {
        return 1;
    }

    comp_epaper_natural_blink_enter_daily(&blink, 1000u);
    if (require_true(
            comp_epaper_natural_blink_remaining_ms(&blink, 1000u) ==
                9u * COMP_EPAPER_MOTION_CADENCE_MS,
            "first browser blink is due after exactly nine commits") ||
        require_true(!comp_epaper_natural_blink_take_due(
                         &blink, 5319u, &blink_phase),
                     "blink does not start before its authored deadline") ||
        require_true(comp_epaper_natural_blink_take_due(
                         &blink, 5320u, &blink_phase) &&
                         blink_phase == COMP_EPAPER_NATURAL_BLINK_CLOSED,
                     "first due phase closes both eyes") ||
        require_true(
            comp_epaper_natural_blink_remaining_ms(&blink, 5320u) ==
                1u,
            "reopen is due in the first slot after the closed commit") ||
        require_true(comp_epaper_natural_blink_take_due(
                         &blink,
                         5320u + COMP_EPAPER_NATURAL_BLINK_CLOSED_HOLD_MS,
                         &blink_phase) &&
                         blink_phase == COMP_EPAPER_NATURAL_BLINK_OPEN,
                     "the first available commit restores the open pose") ||
        require_true(
            comp_epaper_natural_blink_remaining_ms(
                &blink,
                5320u + COMP_EPAPER_NATURAL_BLINK_CLOSED_HOLD_MS) == 0u,
            "the next interval does not start before open becomes visible") ||
        require_true(comp_epaper_natural_blink_complete_open(&blink, 5780u),
                     "visible open completion anchors the next interval") ||
        require_true(
            comp_epaper_natural_blink_remaining_ms(&blink, 5780u) ==
                COMP_EPAPER_NATURAL_BLINK_MIN_INTERVAL_MS,
            "the next browser interval starts at visible open completion")) {
        return 1;
    }
    comp_epaper_natural_blink_cancel(&blink);
    if (require_true(
            comp_epaper_natural_blink_remaining_ms(&blink, 5320u) == 0u,
            "sleep and exclusive surfaces stop the blink clock")) {
        return 1;
    }

    /* A new life entry must not replay the same visible tuple forever. The
     * product chooses among source-pack-authored episodes; different entries
     * diversify action/phrase/variation/dwell while preserving family and all
     * cadence bounds. */
    comp_epaper_motion_coordinator_init(&seeded_a);
    comp_epaper_motion_coordinator_init(&seeded_b);
    seeded_a.completed_requests = 7u;
    seeded_a.next_token = 9u;
    seeded_b.completed_requests = 29u;
    seeded_b.next_token = 31u;
    comp_epaper_motion_coordinator_enter_daily(
        &seeded_a, 30000u, COMP_EPAPER_MOTION_FAMILY_CALM);
    comp_epaper_motion_coordinator_enter_daily(
        &seeded_b, 30000u, COMP_EPAPER_MOTION_FAMILY_CALM);
    now_ms = 30000u;
    {
        uint8_t diverse_beats = 0u;
        comp_epaper_motion_request_t previous_a={0},previous_b={0};
        bool have_previous=false;
        for (uint8_t index = 0u; index < 12u; ++index) {
            comp_epaper_motion_request_t a_request;
            comp_epaper_motion_request_t b_request;
            comp_epaper_motion_snapshot_t a_snapshot;
            comp_epaper_motion_snapshot_t b_snapshot;

            if (require_true(comp_epaper_motion_coordinator_take_request(
                                 &seeded_a, now_ms, &a_request),
                             "seed A emits authored life") ||
                require_true(comp_epaper_motion_coordinator_take_request(
                                 &seeded_b, now_ms, &b_request),
                             "seed B emits authored life")) {
                return 1;
            }
            if (have_previous) {
                if (require_true(previous_a.episode!=a_request.episode ||
                                     previous_a.action!=a_request.action ||
                                     (previous_a.phrase==a_request.phrase && previous_a.variation==a_request.variation),
                                 "seed A retains one recipe throughout an accepted action") ||
                    require_true(previous_b.episode!=b_request.episode ||
                                     previous_b.action!=b_request.action ||
                                     (previous_b.phrase==b_request.phrase && previous_b.variation==b_request.variation),
                                 "seed B retains one recipe throughout an accepted action")) return 1;
            }
            previous_a=a_request;previous_b=b_request;have_previous=true;
            if (a_request.action != b_request.action ||
                a_request.phrase != b_request.phrase ||
                a_request.variation != b_request.variation ||
                a_request.dwell_commits != b_request.dwell_commits) {
                diverse_beats++;
            }
            printf("SEEDED|A|%u|%s|%s|%lu|%u|%u|%u|%u|%u\n",
                   (unsigned)index,
                   comp_epaper_motion_family_name(a_request.family),
                   comp_epaper_motion_action_name(a_request.action),
                   (unsigned long)a_request.episode,
                   (unsigned)a_request.phrase,
                   (unsigned)a_request.phase,
                   (unsigned)a_request.variation,
                   (unsigned)a_request.action_step,
                   (unsigned)a_request.dwell_commits);
            printf("SEEDED|B|%u|%s|%s|%lu|%u|%u|%u|%u|%u\n",
                   (unsigned)index,
                   comp_epaper_motion_family_name(b_request.family),
                   comp_epaper_motion_action_name(b_request.action),
                   (unsigned long)b_request.episode,
                   (unsigned)b_request.phrase,
                   (unsigned)b_request.phase,
                   (unsigned)b_request.variation,
                   (unsigned)b_request.action_step,
                   (unsigned)b_request.dwell_commits);
            if (require_true(a_request.family == COMP_EPAPER_MOTION_FAMILY_CALM &&
                                 b_request.family == COMP_EPAPER_MOTION_FAMILY_CALM,
                             "seed diversity stays inside the committed emotion") ||
                require_true(a_request.dwell_commits >=
                                     COMP_EPAPER_MOTION_DWELL_MIN_COMMITS &&
                                 a_request.dwell_commits <=
                                     COMP_EPAPER_MOTION_DWELL_MAX_COMMITS &&
                                 b_request.dwell_commits >=
                                     COMP_EPAPER_MOTION_DWELL_MIN_COMMITS &&
                                 b_request.dwell_commits <=
                                     COMP_EPAPER_MOTION_DWELL_MAX_COMMITS,
                             "seed diversity preserves authored dwell bounds") ||
                require_true(comp_epaper_motion_coordinator_complete_request(
                                 &seeded_a, a_request.token, now_ms + 300u, true),
                             "seed A visible completion") ||
                require_true(comp_epaper_motion_coordinator_complete_request(
                                 &seeded_b, b_request.token, now_ms + 300u, true),
                             "seed B visible completion")) {
                return 1;
            }
            comp_epaper_motion_coordinator_snapshot(&seeded_a, &a_snapshot);
            comp_epaper_motion_coordinator_snapshot(&seeded_b, &b_snapshot);
            now_ms = a_snapshot.next_request_ms < b_snapshot.next_request_ms
                         ? a_snapshot.next_request_ms
                         : b_snapshot.next_request_ms;
            if (a_snapshot.next_request_ms != b_snapshot.next_request_ms) {
                now_ms = a_snapshot.next_request_ms > b_snapshot.next_request_ms
                             ? a_snapshot.next_request_ms
                             : b_snapshot.next_request_ms;
            }
        }
        if (require_true(diverse_beats >= 4u,
                         "different entry seeds do not replay a fixed rotation")) {
            return 1;
        }
    }

    /* Recording is an independent functional track, not a second face clock.
     * Run sixty authored commits from identical state while the recording-side
     * coordinator receives harmless keep-awake service between commits. The
     * complete face tuple and absolute next deadline must remain identical. */
    comp_epaper_motion_coordinator_init(&recording_off);
    comp_epaper_motion_coordinator_init(&recording_on);
    comp_epaper_motion_coordinator_enter_daily(
        &recording_off, 50000u, COMP_EPAPER_MOTION_FAMILY_CALM);
    comp_epaper_motion_coordinator_enter_daily(
        &recording_on, 50000u, COMP_EPAPER_MOTION_FAMILY_CALM);
    now_ms = 50000u;
    for (uint32_t index = 0u; index < 60u; ++index) {
        comp_epaper_motion_request_t off_request;
        comp_epaper_motion_request_t on_request;
        comp_epaper_motion_snapshot_t off_snapshot;
        comp_epaper_motion_snapshot_t on_snapshot;
        const uint32_t visible_ms = now_ms + 455u;

        comp_epaper_motion_coordinator_keep_awake(
            &recording_on, now_ms + 100u);
        if (require_true(comp_epaper_motion_coordinator_take_request(
                             &recording_off, now_ms, &off_request),
                         "offline authored request is due") ||
            require_true(comp_epaper_motion_coordinator_take_request(
                             &recording_on, now_ms, &on_request),
                         "recording authored request is due") ||
            require_true(same_authored_tuple(&off_request, &on_request),
                         "recording preserves the complete authored tuple") ||
            require_true(comp_epaper_motion_coordinator_complete_request(
                             &recording_off,
                             off_request.token,
                             visible_ms,
                             true),
                         "offline authored request completes") ||
            require_true(comp_epaper_motion_coordinator_complete_request(
                             &recording_on,
                             on_request.token,
                             visible_ms,
                             true),
                         "recording authored request completes")) {
            return 1;
        }
        printf("PAIR|%lu|%s|%s|%lu|%u|%u|%u|%u|%u|"
               "%s|%s|%lu|%u|%u|%u|%u|%u|%lu|%lu\n",
               (unsigned long)index,
               comp_epaper_motion_family_name(off_request.family),
               comp_epaper_motion_action_name(off_request.action),
               (unsigned long)off_request.episode,
               (unsigned)off_request.phrase,
               (unsigned)off_request.phase,
               (unsigned)off_request.variation,
               (unsigned)off_request.action_step,
               (unsigned)off_request.dwell_commits,
               comp_epaper_motion_family_name(on_request.family),
               comp_epaper_motion_action_name(on_request.action),
               (unsigned long)on_request.episode,
               (unsigned)on_request.phrase,
               (unsigned)on_request.phase,
               (unsigned)on_request.variation,
               (unsigned)on_request.action_step,
               (unsigned)on_request.dwell_commits,
               (unsigned long)now_ms,
               (unsigned long)now_ms);
        comp_epaper_motion_coordinator_snapshot(
            &recording_off, &off_snapshot);
        comp_epaper_motion_coordinator_snapshot(
            &recording_on, &on_snapshot);
        if (require_true(off_snapshot.next_request_ms ==
                             on_snapshot.next_request_ms,
                         "recording preserves the absolute life deadline")) {
            return 1;
        }
        now_ms = off_snapshot.next_request_ms;
    }

    printf("MOTION_COORDINATOR_HOST_OK browser_life=recovered_component_v3 clock=absolute_deadline cadence_ms=%u "
           "max_visible_ms=%u natural_blink=browser_seeded_v1 "
           "entry_seed_diversity=pass paired_recording_off_on=60/60\n",
           (unsigned)COMP_EPAPER_MOTION_CADENCE_MS,
           (unsigned)(COMP_EPAPER_MOTION_CADENCE_MS *
                      COMP_EPAPER_MOTION_DWELL_MAX_COMMITS));
    return 0;
}
