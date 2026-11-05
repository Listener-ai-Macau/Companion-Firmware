#include "display_track_arbiter.h"

static bool time_reached(uint32_t now_ms, uint32_t deadline_ms)
{
    return (int32_t)(now_ms - deadline_ms) >= 0;
}

static uint32_t track_bit(comp_epaper_display_track_id_t track)
{
    return track < 32u ? 1u << track : 0u;
}

void comp_epaper_display_track_ready_mailbox_init(
    comp_epaper_display_track_ready_mailbox_t *mailbox)
{
    if (mailbox != NULL) {
        mailbox->pending_mask = 0u;
    }
}

bool comp_epaper_display_track_ready_mailbox_publish(
    comp_epaper_display_track_ready_mailbox_t *mailbox,
    comp_epaper_display_track_id_t track)
{
    const uint32_t bit = track_bit(track);

    if (mailbox == NULL || bit == 0u) {
        return false;
    }
    mailbox->pending_mask |= bit;
    return true;
}

bool comp_epaper_display_track_ready_mailbox_pending(
    const comp_epaper_display_track_ready_mailbox_t *mailbox,
    comp_epaper_display_track_id_t track)
{
    const uint32_t bit = track_bit(track);

    return mailbox != NULL && bit != 0u &&
           (mailbox->pending_mask & bit) != 0u;
}

bool comp_epaper_display_track_ready_mailbox_consume(
    comp_epaper_display_track_ready_mailbox_t *mailbox,
    comp_epaper_display_track_id_t track)
{
    const uint32_t bit = track_bit(track);

    if (mailbox == NULL || bit == 0u ||
        (mailbox->pending_mask & bit) == 0u) {
        return false;
    }
    mailbox->pending_mask &= ~bit;
    return true;
}

bool comp_epaper_display_track_ready_mailbox_cancel(
    comp_epaper_display_track_ready_mailbox_t *mailbox,
    comp_epaper_display_track_id_t track)
{
    const uint32_t bit = track_bit(track);

    if (mailbox == NULL || bit == 0u) {
        return false;
    }
    mailbox->pending_mask &= ~bit;
    return true;
}

static uint32_t gate_hash(uint32_t seed, uint32_t epoch)
{
    uint32_t value = seed ^ ((epoch + 1u) * 0x9E3779B9u);

    value ^= value >> 16u;
    value *= 0x7FEB352Du;
    value ^= value >> 15u;
    value *= 0x846CA68Bu;
    value ^= value >> 16u;
    return value;
}

static uint32_t gate_interval_ms(
    const comp_epaper_display_presentation_gate_t *gate)
{
    const uint32_t span =
        (uint32_t)gate->maximum_interval_ms -
        (uint32_t)gate->minimum_interval_ms + 1u;

    return (uint32_t)gate->minimum_interval_ms +
           (uint32_t)(((uint64_t)gate_hash(gate->seed, gate->epoch) * span) >>
                      32u);
}

bool comp_epaper_display_track_arbiter_plan(
    uint32_t now_ms,
    const comp_epaper_display_track_candidate_t *candidates,
    size_t candidate_count,
    comp_epaper_display_track_plan_t *out_plan)
{
    size_t selected = candidate_count;

    if (candidates == NULL || out_plan == NULL) {
        return false;
    }
    for (size_t index = 0u; index < candidate_count; ++index) {
        const comp_epaper_display_track_candidate_t *candidate =
            &candidates[index];

        if (!candidate->pending || candidate->in_flight ||
            (candidate->has_deadline &&
             !time_reached(now_ms, candidate->deadline_ms))) {
            continue;
        }
        if (selected == candidate_count ||
            candidate->priority < candidates[selected].priority ||
            (candidate->priority == candidates[selected].priority &&
             candidate->has_deadline &&
             (!candidates[selected].has_deadline ||
              (int32_t)(candidate->deadline_ms -
                        candidates[selected].deadline_ms) < 0))) {
            selected = index;
        }
    }
    if (selected == candidate_count) {
        return false;
    }
    out_plan->primary_id = candidates[selected].id;
    out_plan->track_mask = candidates[selected].id < 32u
                               ? 1u << candidates[selected].id
                               : 0u;
    for (size_t index = 0u; index < candidate_count; ++index) {
        const comp_epaper_display_track_candidate_t *candidate =
            &candidates[index];

        if (index == selected || !candidate->coalescible ||
            candidate->id >= 32u || !candidate->pending ||
            candidate->in_flight ||
            (candidate->has_deadline &&
             !time_reached(now_ms, candidate->deadline_ms))) {
            continue;
        }
        out_plan->track_mask |= 1u << candidate->id;
    }
    return true;
}

bool comp_epaper_display_track_arbiter_select(
    uint32_t now_ms,
    const comp_epaper_display_track_candidate_t *candidates,
    size_t candidate_count,
    comp_epaper_display_track_id_t *out_id)
{
    comp_epaper_display_track_plan_t plan;

    if (out_id == NULL ||
        !comp_epaper_display_track_arbiter_plan(
            now_ms, candidates, candidate_count, &plan)) {
        return false;
    }
    *out_id = plan.primary_id;
    return true;
}

void comp_epaper_display_presentation_gate_init(
    comp_epaper_display_presentation_gate_t *gate,
    uint32_t anchor_ms,
    uint32_t seed,
    uint16_t minimum_interval_ms,
    uint16_t maximum_interval_ms)
{
    if (gate == NULL || minimum_interval_ms == 0u ||
        maximum_interval_ms < minimum_interval_ms) {
        return;
    }
    *gate = (comp_epaper_display_presentation_gate_t){
        .initialized = true,
        .seed = seed,
        .minimum_interval_ms = minimum_interval_ms,
        .maximum_interval_ms = maximum_interval_ms,
    };
    gate->next_due_ms = anchor_ms + gate_interval_ms(gate);
}

bool comp_epaper_display_presentation_gate_due(
    const comp_epaper_display_presentation_gate_t *gate,
    uint32_t now_ms)
{
    return gate != NULL && gate->initialized &&
           time_reached(now_ms, gate->next_due_ms);
}

bool comp_epaper_display_presentation_gate_advance(
    comp_epaper_display_presentation_gate_t *gate,
    uint32_t now_ms)
{
    if (!comp_epaper_display_presentation_gate_due(gate, now_ms)) {
        return false;
    }
    do {
        gate->epoch++;
        gate->next_due_ms += gate_interval_ms(gate);
    } while (time_reached(now_ms, gate->next_due_ms));
    return true;
}

uint32_t comp_epaper_display_joint_deadline_ms(
    uint32_t first_deadline_ms,
    uint32_t second_deadline_ms)
{
    return (int32_t)(first_deadline_ms - second_deadline_ms) >= 0
               ? first_deadline_ms
               : second_deadline_ms;
}

uint32_t comp_epaper_display_joint_deadline_remaining_ms(
    uint32_t now_ms,
    uint32_t first_deadline_ms,
    uint32_t second_deadline_ms)
{
    const uint32_t joint_deadline_ms =
        comp_epaper_display_joint_deadline_ms(first_deadline_ms,
                                               second_deadline_ms);

    return time_reached(now_ms, joint_deadline_ms)
               ? 0u
               : joint_deadline_ms - now_ms;
}

comp_epaper_display_completion_service_t
comp_epaper_display_completion_service(
    comp_epaper_display_track_id_t completed_track,
    bool display_timer_due,
    bool recording_ready)
{
    (void)completed_track;

    if (display_timer_due) {
        return COMP_EPAPER_DISPLAY_COMPLETION_SERVICE_TIMER;
    }
    if (recording_ready) {
        return COMP_EPAPER_DISPLAY_COMPLETION_SERVICE_RECORDING;
    }
    return COMP_EPAPER_DISPLAY_COMPLETION_SERVICE_NONE;
}
