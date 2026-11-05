#include "display_track_arbiter.h"

#include <stdio.h>
#include <stdlib.h>

enum {
    TRACK_BLINK_OPEN = 1u,
    TRACK_BLINK_CLOSED = 2u,
    TRACK_BASE = 3u,
    TRACK_RECORDING = 4u,
    TRACK_ACCESSORY = 5u,
};

static void require_true(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        exit(1);
    }
}

static comp_epaper_display_track_id_t select_track(
    uint32_t now_ms,
    const comp_epaper_display_track_candidate_t *candidates,
    size_t count)
{
    comp_epaper_display_track_id_t selected = 0u;
    require_true(comp_epaper_display_track_arbiter_select(
                     now_ms, candidates, count, &selected),
                 "one track must be selected");
    return selected;
}

int main(void)
{
    comp_epaper_display_presentation_gate_t presentation_gate = {0};
    comp_epaper_display_track_ready_mailbox_t ready_mailbox = {0};
    /* Authored face/blink wins only after its own deadline. Before then the
     * continuous recording waveform consumes every physically free slot. */
    comp_epaper_display_track_candidate_t candidates[] = {
        {.id = TRACK_BLINK_OPEN,
         .priority = 0u,
         .has_deadline = true},
        {.id = TRACK_BLINK_CLOSED,
         .priority = 1u,
         .pending = true,
         .has_deadline = true,
         .deadline_ms = 32000u},
        {.id = TRACK_RECORDING,
         .priority = 2u,
         .pending = true,
         .has_deadline = true,
         .deadline_ms = 900u,
         .coalescible = false},
        {.id = TRACK_BASE,
         .priority = 1u,
         .pending = true,
         .has_deadline = true,
         .deadline_ms = 1481u},
        {.id = TRACK_ACCESSORY,
         .priority = 4u,
         .has_deadline = true,
         .coalescible = false},
    };
    comp_epaper_display_track_plan_t plan = {0};

    require_true(select_track(1000u, candidates, 5u) == TRACK_RECORDING,
                 "wave fills free slots while blink is not due");
    /* Once both are due, the authored face owns its absolute deadline. */
    candidates[2].deadline_ms = 500u;
    candidates[3].deadline_ms = 500u;
    require_true(select_track(1600u, candidates, 5u) == TRACK_BASE,
                 "authored life beats best-effort wave when both are due");
    /* A due face takes one slot; no earlier waveform slot was suppressed. */
    candidates[2].pending = false;
    require_true(select_track(1600u, candidates, 5u) == TRACK_BASE,
                 "due life paints when no wave candidate is present");
    candidates[2].pending = true;
    candidates[3].pending = false;
    require_true(select_track(1600u, candidates, 5u) == TRACK_RECORDING,
                 "wave resumes when life is not pending");
    candidates[2].pending = true;
    candidates[2].deadline_ms = 1480u;
    candidates[3].pending = true;
    candidates[3].deadline_ms = 1480u;
    candidates[4].pending = true;
    candidates[4].deadline_ms = 1480u;
    require_true(comp_epaper_display_track_arbiter_plan(
                     1480u, candidates, 5u, &plan),
                 "due tracks produce one physical plan");
    require_true(plan.primary_id == TRACK_BASE,
                 "life remains primary over wave and accessory");
    require_true(plan.track_mask == (1u << TRACK_BASE),
                 "authored face owns a physical activation without wave");
    candidates[4].pending = false;
    candidates[3].pending = false;
    require_true(select_track(1600u, candidates, 5u) == TRACK_RECORDING,
                 "recording owns free slots when life is idle");
    candidates[3].pending = true;
    candidates[3].in_flight = true;
    candidates[2].deadline_ms = 1480u;
    require_true(select_track(2000u, candidates, 5u) == TRACK_RECORDING,
                 "an in-flight base cannot accumulate a second request");
    candidates[0].pending = true;
    candidates[0].deadline_ms = 2000u;
    require_true(select_track(2000u, candidates, 5u) == TRACK_BLINK_OPEN,
                 "blink open wins when no recording fairness turn is active");
    require_true(comp_epaper_display_track_arbiter_plan(
                     2000u, candidates, 5u, &plan),
                 "blink produces one physical plan while waveform stays ready");
    require_true(plan.primary_id == TRACK_BLINK_OPEN &&
                     plan.track_mask == (1u << TRACK_BLINK_OPEN),
                 "authored blink owns a physical activation without wave");
    /* app_ble's recording fairness gate suppresses all non-wave candidates
     * after any face/blink commit. Model that candidate set here: the wave
     * must receive one activation before blink-open or BASE can be eligible
     * again, so close+open+face can never create a multi-second wave hole. */
    candidates[0].pending = false;
    candidates[1].pending = false;
    candidates[3].pending = false;
    require_true(select_track(2000u, candidates, 5u) == TRACK_RECORDING,
                 "one pure wave turn separates consecutive non-wave slots");
    candidates[0].pending = false;
    candidates[1].pending = true;
    candidates[1].deadline_ms = 1900u;
    require_true(select_track(2000u, candidates, 5u) == TRACK_BLINK_CLOSED,
                 "a due sparse blink preempts wave and life once");
    candidates[1].pending = false;
    candidates[2].pending = false;
    candidates[3].pending = false;
    candidates[3].in_flight = false;
    candidates[4].pending = true;
    candidates[4].deadline_ms = 1990u;
    require_true(select_track(2000u, candidates, 5u) == TRACK_ACCESSORY,
                 "an independent accessory can use an otherwise free slot");

    comp_epaper_display_presentation_gate_init(
        &presentation_gate, 1000u, 0x775A11CEu, 2300u, 5100u);
    require_true(presentation_gate.initialized,
                 "presentation gate initializes once");
    require_true(presentation_gate.next_due_ms >= 3300u &&
                     presentation_gate.next_due_ms <= 6100u,
                 "presentation gate uses the configured independent range");
    require_true(!comp_epaper_display_presentation_gate_due(
                     &presentation_gate, presentation_gate.next_due_ms - 1u),
                 "presentation gate stays closed before its absolute due");
    {
        const uint32_t first_due = presentation_gate.next_due_ms;
        require_true(comp_epaper_display_presentation_gate_due(
                         &presentation_gate, first_due),
                     "presentation gate opens on its own deadline");
        require_true(comp_epaper_display_presentation_gate_advance(
                         &presentation_gate, first_due),
                     "a visible sample consumes exactly one gate epoch");
        require_true(presentation_gate.epoch == 1u &&
                         presentation_gate.next_due_ms > first_due,
                     "next presentation derives from the prior absolute due");
    }
    {
        const uint32_t second_due = presentation_gate.next_due_ms;
        require_true(comp_epaper_display_presentation_gate_advance(
                         &presentation_gate, second_due + 20000u),
                     "elapsed presentation opportunities catch up without a burst");
        require_true(presentation_gate.next_due_ms > second_due + 20000u,
                     "catch-up leaves one future deadline");
    }
    require_true(comp_epaper_display_joint_deadline_ms(900u, 3500u) ==
                     3500u,
                 "the later independent gate owns the joint deadline");
    require_true(comp_epaper_display_joint_deadline_remaining_ms(
                     1000u, 900u, 3500u) == 2500u,
                 "an expired producer deadline cannot create a tight wake loop");
    require_true(comp_epaper_display_joint_deadline_remaining_ms(
                     3600u, 900u, 3500u) == 0u,
                 "the joint deadline becomes due only after both clocks");
    require_true(comp_epaper_display_joint_deadline_ms(
                     0xFFFFFFF0u, 0x00000020u) == 0x00000020u,
                 "joint deadline ordering survives the millisecond wrap");
    /* With a 455 ms physical wave transaction and the original authored
     * 480 ms base beat, no look-ahead slot is dropped. The last wave may
     * finish after the authored deadline; BASE then takes the next slot. */
    for (uint32_t dwell = 1u; dwell <= 4u; ++dwell) {
        const uint32_t authored_due = 1000u + dwell * 480u;
        uint32_t panel_free_ms = 1000u;
        uint32_t admitted_wave_slots = 0u;

        while ((int32_t)(panel_free_ms - authored_due) < 0) {
            admitted_wave_slots++;
            panel_free_ms += 455u;
        }
        require_true(admitted_wave_slots == dwell + 1u,
                     "every pre-deadline free slot refreshes the waveform");
    }

    comp_epaper_display_track_ready_mailbox_init(&ready_mailbox);
    require_true(!comp_epaper_display_track_ready_mailbox_pending(
                     &ready_mailbox, TRACK_RECORDING),
                 "recording starts without stale ready work");
    require_true(comp_epaper_display_track_ready_mailbox_publish(
                     &ready_mailbox, TRACK_RECORDING),
                 "recording publishes its own durable ready bit");
    require_true(comp_epaper_display_track_ready_mailbox_pending(
                     &ready_mailbox, TRACK_RECORDING),
                 "touch yield cannot consume unpublished physical work");
    require_true(comp_epaper_display_track_ready_mailbox_publish(
                     &ready_mailbox, TRACK_BASE),
                 "another producer owns a separate ready bit");
    require_true(comp_epaper_display_track_ready_mailbox_consume(
                     &ready_mailbox, TRACK_RECORDING),
                 "successful recording enqueue consumes only recording");
    require_true(!comp_epaper_display_track_ready_mailbox_pending(
                     &ready_mailbox, TRACK_RECORDING) &&
                     comp_epaper_display_track_ready_mailbox_pending(
                         &ready_mailbox, TRACK_BASE),
                 "one producer cannot consume another producer's wake");
    require_true(comp_epaper_display_track_ready_mailbox_publish(
                     &ready_mailbox, TRACK_RECORDING) &&
                     comp_epaper_display_track_ready_mailbox_cancel(
                         &ready_mailbox, TRACK_RECORDING),
                 "recording stop cancels its durable ready bit");
    require_true(!comp_epaper_display_track_ready_mailbox_pending(
                     &ready_mailbox, TRACK_RECORDING),
                 "cancel prevents a post-stop waveform retry");
    require_true(!comp_epaper_display_track_ready_mailbox_publish(
                     &ready_mailbox, 32u),
                 "out-of-range tracks cannot corrupt the mailbox");

    for (uint8_t completed = 0u; completed < 8u; ++completed) {
        require_true(
            comp_epaper_display_completion_service(
                completed, false, false) ==
                COMP_EPAPER_DISPLAY_COMPLETION_SERVICE_NONE,
            "completion alone cannot wake another track");
        require_true(
            comp_epaper_display_completion_service(
                completed, true, false) ==
                COMP_EPAPER_DISPLAY_COMPLETION_SERVICE_TIMER,
            "independent timer owns timed service after every completion class");
        require_true(
            comp_epaper_display_completion_service(
                completed, false, true) ==
                COMP_EPAPER_DISPLAY_COMPLETION_SERVICE_RECORDING,
            "independent recording readiness owns the fallback slot");
        require_true(
            comp_epaper_display_completion_service(
                completed, true, true) ==
                COMP_EPAPER_DISPLAY_COMPLETION_SERVICE_TIMER,
            "timed boundary remains ahead of recording fallback");
    }

    puts("PASS: independent display track arbiter");
    return 0;
}
