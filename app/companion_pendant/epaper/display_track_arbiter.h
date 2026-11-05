#ifndef COMPANION_EPAPER_DISPLAY_TRACK_ARBITER_H
#define COMPANION_EPAPER_DISPLAY_TRACK_ARBITER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef uint8_t comp_epaper_display_track_id_t;

typedef struct {
    comp_epaper_display_track_id_t id;
    uint8_t priority;
    bool pending;
    bool in_flight;
    bool has_deadline;
    uint32_t deadline_ms;
    bool coalescible;
} comp_epaper_display_track_candidate_t;

typedef struct {
    comp_epaper_display_track_id_t primary_id;
    uint32_t track_mask;
} comp_epaper_display_track_plan_t;

typedef struct {
    bool initialized;
    uint32_t seed;
    uint32_t epoch;
    uint32_t next_due_ms;
    uint16_t minimum_interval_ms;
    uint16_t maximum_interval_ms;
} comp_epaper_display_presentation_gate_t;

typedef enum {
    COMP_EPAPER_DISPLAY_COMPLETION_SERVICE_NONE = 0,
    COMP_EPAPER_DISPLAY_COMPLETION_SERVICE_TIMER = 1,
    COMP_EPAPER_DISPLAY_COMPLETION_SERVICE_RECORDING = 2,
} comp_epaper_display_completion_service_t;

/* Durable producer-owned ready bits. A producer publishes before asking the
 * physical display owner for service. The bit is consumed only after that
 * producer successfully enters the serialized display queue, so touch yield,
 * queue contention, and coalesced task notifications cannot lose work. */
typedef struct {
    uint32_t pending_mask;
} comp_epaper_display_track_ready_mailbox_t;

void comp_epaper_display_track_ready_mailbox_init(
    comp_epaper_display_track_ready_mailbox_t *mailbox);
bool comp_epaper_display_track_ready_mailbox_publish(
    comp_epaper_display_track_ready_mailbox_t *mailbox,
    comp_epaper_display_track_id_t track);
bool comp_epaper_display_track_ready_mailbox_pending(
    const comp_epaper_display_track_ready_mailbox_t *mailbox,
    comp_epaper_display_track_id_t track);
bool comp_epaper_display_track_ready_mailbox_consume(
    comp_epaper_display_track_ready_mailbox_t *mailbox,
    comp_epaper_display_track_id_t track);
bool comp_epaper_display_track_ready_mailbox_cancel(
    comp_epaper_display_track_ready_mailbox_t *mailbox,
    comp_epaper_display_track_id_t track);

/* Builds one physical display plan. The primary track owns the transaction;
 * every other due coalescible track contributes its latest snapshot to that
 * same transaction instead of consuming another panel BUSY interval. */
bool comp_epaper_display_track_arbiter_plan(
    uint32_t now_ms,
    const comp_epaper_display_track_candidate_t *candidates,
    size_t candidate_count,
    comp_epaper_display_track_plan_t *out_plan);

/* Selects one producer without mutating any producer state. Lower numeric
 * priority wins; equal priorities choose the most overdue deadline. */
bool comp_epaper_display_track_arbiter_select(
    uint32_t now_ms,
    const comp_epaper_display_track_candidate_t *candidates,
    size_t candidate_count,
    comp_epaper_display_track_id_t *out_id);

/* A presentation gate is an absolute, independently jittered wall-clock.
 * It lets a slow visual track sample its latest logical state without being
 * phase-locked to a faster track sharing the same serial panel. */
void comp_epaper_display_presentation_gate_init(
    comp_epaper_display_presentation_gate_t *gate,
    uint32_t anchor_ms,
    uint32_t seed,
    uint16_t minimum_interval_ms,
    uint16_t maximum_interval_ms);
bool comp_epaper_display_presentation_gate_due(
    const comp_epaper_display_presentation_gate_t *gate,
    uint32_t now_ms);
bool comp_epaper_display_presentation_gate_advance(
    comp_epaper_display_presentation_gate_t *gate,
    uint32_t now_ms);

/* A track guarded by two absolute clocks becomes eligible only after both
 * deadlines. These helpers keep that joint deadline wrap-safe and prevent an
 * already-expired producer clock from turning a later presentation gate into
 * a tight wake loop. */
uint32_t comp_epaper_display_joint_deadline_ms(
    uint32_t first_deadline_ms,
    uint32_t second_deadline_ms);
uint32_t comp_epaper_display_joint_deadline_remaining_ms(
    uint32_t now_ms,
    uint32_t first_deadline_ms,
    uint32_t second_deadline_ms);

/* A completed physical transaction only releases the panel. It never grants
 * its producer permission to advance another logical track. The next service
 * is selected exclusively from independently published due/ready state. */
comp_epaper_display_completion_service_t
comp_epaper_display_completion_service(
    comp_epaper_display_track_id_t completed_track,
    bool display_timer_due,
    bool recording_ready);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_DISPLAY_TRACK_ARBITER_H */
