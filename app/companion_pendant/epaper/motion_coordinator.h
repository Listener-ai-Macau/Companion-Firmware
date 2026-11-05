#ifndef COMPANION_EPAPER_MOTION_COORDINATOR_H
#define COMPANION_EPAPER_MOTION_COORDINATOR_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* This is the browser's visible e-paper commit clock. A pose may be held for
 * several commits, but the next visible beat stays below the 2 s ceiling. */
#define COMP_EPAPER_MOTION_CADENCE_MS 480u
/* One display slot after close is enough; keep non-zero so next_due is never
 * left at an ambiguous zero that other code treats as "always due". */
#define COMP_EPAPER_NATURAL_BLINK_CLOSED_HOLD_MS 1u
#define COMP_EPAPER_NATURAL_BLINK_MIN_INTERVAL_MS 12000u
#define COMP_EPAPER_MOTION_DWELL_MIN_COMMITS 1u
#define COMP_EPAPER_MOTION_DWELL_MAX_COMMITS 4u
#define COMP_EPAPER_MOTION_IDLE_TIMEOUT_MS 180000u

typedef enum {
    COMP_EPAPER_MOTION_PHASE_HOLD = 0u,
    COMP_EPAPER_MOTION_PHASE_ORIENT = 1u,
    COMP_EPAPER_MOTION_PHASE_ANTICIPATE = 2u,
    COMP_EPAPER_MOTION_PHASE_ACCENT = 3u,
    COMP_EPAPER_MOTION_PHASE_FOLLOW = 4u,
    COMP_EPAPER_MOTION_PHASE_SETTLE = 5u,
    COMP_EPAPER_MOTION_PHASE_COUNT = 6u,
} comp_epaper_motion_phase_t;

typedef enum {
    COMP_EPAPER_MOTION_FAMILY_CALM = 0u,
    COMP_EPAPER_MOTION_FAMILY_CURIOUS = 1u,
    COMP_EPAPER_MOTION_FAMILY_DELIGHTED = 2u,
    COMP_EPAPER_MOTION_FAMILY_WARM = 3u,
    COMP_EPAPER_MOTION_FAMILY_PLAYFUL = 4u,
    COMP_EPAPER_MOTION_FAMILY_SLEEPY = 5u,
    COMP_EPAPER_MOTION_FAMILY_BASHFUL = 6u,
    COMP_EPAPER_MOTION_FAMILY_THOUGHTFUL = 7u,
    COMP_EPAPER_MOTION_FAMILY_FOCUSED = 8u,
    COMP_EPAPER_MOTION_FAMILY_ALERT = 9u,
    COMP_EPAPER_MOTION_FAMILY_COUNT = 10u,
} comp_epaper_motion_family_t;

typedef enum {
    COMP_EPAPER_MOTION_ACTION_REST = 0u,
    COMP_EPAPER_MOTION_ACTION_NOTICE_LEFT = 1u,
    COMP_EPAPER_MOTION_ACTION_NOTICE_RIGHT = 2u,
    COMP_EPAPER_MOTION_ACTION_SOFTEN = 3u,
    COMP_EPAPER_MOTION_ACTION_SMALL_BREATH = 4u,
    COMP_EPAPER_MOTION_ACTION_LISTEN_UP = 5u,
    COMP_EPAPER_MOTION_ACTION_QUESTION = 6u,
    COMP_EPAPER_MOTION_ACTION_BEAM = 7u,
    COMP_EPAPER_MOTION_ACTION_TEASE_GRIN = 8u,
    COMP_EPAPER_MOTION_ACTION_YAWN = 9u,
    COMP_EPAPER_MOTION_ACTION_SHY_SMILE = 10u,
    COMP_EPAPER_MOTION_ACTION_PONDER = 11u,
    COMP_EPAPER_MOTION_ACTION_REFOCUS = 12u,
    COMP_EPAPER_MOTION_ACTION_STARTLE = 13u,
    COMP_EPAPER_MOTION_ACTION_COUNT = 14u,
} comp_epaper_motion_action_t;

typedef enum {
    COMP_EPAPER_MOTION_CANCEL_TOUCH = 0u,
    COMP_EPAPER_MOTION_CANCEL_MENU = 1u,
    COMP_EPAPER_MOTION_CANCEL_RECORDING = 2u,
    COMP_EPAPER_MOTION_CANCEL_LOW_POWER = 3u,
    COMP_EPAPER_MOTION_CANCEL_ERROR = 4u,
    COMP_EPAPER_MOTION_CANCEL_HIGH_PRIORITY = 5u,
} comp_epaper_motion_cancel_reason_t;

typedef struct {
    uint32_t token;
    uint32_t episode;
    comp_epaper_motion_family_t family;
    comp_epaper_motion_phase_t phase;
    comp_epaper_motion_action_t action;
    uint8_t phrase;
    uint8_t variation;
    uint8_t action_step;
    uint8_t dwell_commits;
} comp_epaper_motion_request_t;

typedef enum {
    COMP_EPAPER_NATURAL_BLINK_CLOSED = 0u,
    COMP_EPAPER_NATURAL_BLINK_OPEN = 1u,
} comp_epaper_natural_blink_phase_t;

typedef struct {
    uint16_t cadence_ms;
    uint8_t first_interval_commits;
    uint8_t interval_count;
    const uint8_t *interval_commits;
} comp_epaper_natural_blink_config_t;

typedef struct {
    bool initialized;
    bool awake;
    bool open_pending;
    bool open_in_flight;
    uint8_t interval_index;
    uint8_t first_interval_commits;
    uint8_t interval_count;
    uint16_t cadence_ms;
    const uint8_t *interval_commits;
    uint32_t epoch;
    uint32_t next_due_ms;
} comp_epaper_natural_blink_scheduler_t;

typedef struct {
    bool initialized : 1;
    bool daily_awake : 1;
    bool request_outstanding : 1;
    bool episode_prepared : 1;
    comp_epaper_motion_family_t family;
    comp_epaper_motion_phase_t next_phase;
    comp_epaper_motion_action_t action;
    uint8_t phrase;
    uint8_t variation;
    uint8_t dwell_commits;
    uint8_t action_step;
    uint8_t action_phase_count;
    uint8_t quiet_commits;
    uint8_t previous_quiet_commits;
    uint8_t recent_actions[3];
    uint8_t recent_action_count;
    uint8_t cooldowns[COMP_EPAPER_MOTION_ACTION_COUNT];
    /* Compact flags fund these three bytes on the target's one-byte-enum ABI;
     * native four-byte enums already had alignment space. Bit7 enables the
     * product-only stream; zero retains legacy behavior, no extra buffer. */
    uint8_t scene, scene_step, previous_scene;
    uint32_t episode;
    uint32_t next_request_ms;
    uint32_t outstanding_due_ms;
    uint32_t idle_deadline_ms;
    uint32_t outstanding_token;
    uint32_t next_token;
    uint32_t issued_requests;
    uint32_t completed_requests;
    uint32_t failed_requests;
    uint32_t cancelled_requests;
    uint32_t stale_completion_count;
    comp_epaper_motion_cancel_reason_t last_cancel_reason;
} comp_epaper_motion_coordinator_t;

typedef struct {
    bool daily_awake;
    bool request_outstanding;
    comp_epaper_motion_family_t family;
    comp_epaper_motion_phase_t next_phase;
    comp_epaper_motion_action_t action;
    uint8_t phrase;
    uint8_t variation;
    uint8_t dwell_commits;
    uint32_t episode;
    uint32_t next_request_ms;
    uint32_t idle_deadline_ms;
    uint32_t outstanding_token;
    uint32_t outstanding_due_ms;
    uint32_t issued_requests;
    uint32_t completed_requests;
    uint32_t failed_requests;
    uint32_t cancelled_requests;
    uint32_t stale_completion_count;
    comp_epaper_motion_cancel_reason_t last_cancel_reason;
} comp_epaper_motion_snapshot_t;

void comp_epaper_motion_coordinator_init(
    comp_epaper_motion_coordinator_t *coordinator);

/* Start the browser-parity daily life stream for one stable emotion family.
 * Family changes are applied only when daily motion is entered again. */
void comp_epaper_motion_coordinator_enter_daily(
    comp_epaper_motion_coordinator_t *coordinator,
    uint32_t now_ms,
    comp_epaper_motion_family_t family);

/* Opt in only on the UI64+ physical product path. Configuration/entropy may
 * change at a scene boundary with no outstanding request, never mid-phrase.
 * All scene actions refer to the existing family/action/episode asset bank. */
bool comp_epaper_motion_coordinator_enable_scenes(
    comp_epaper_motion_coordinator_t *coordinator, bool enabled);
bool comp_epaper_motion_coordinator_seed_scene(
    comp_epaper_motion_coordinator_t *coordinator, uint32_t entropy);
bool comp_epaper_motion_coordinator_scene_boundary(
    const comp_epaper_motion_coordinator_t *coordinator);

const char *comp_epaper_motion_family_name(comp_epaper_motion_family_t family);
const char *comp_epaper_motion_action_name(comp_epaper_motion_action_t action);

void comp_epaper_motion_coordinator_cancel(
    comp_epaper_motion_coordinator_t *coordinator,
    comp_epaper_motion_cancel_reason_t reason);

bool comp_epaper_motion_coordinator_take_request(
    comp_epaper_motion_coordinator_t *coordinator,
    uint32_t now_ms,
    comp_epaper_motion_request_t *out_request);

/* Only the matching panel-completion callback may advance the story. A failed
 * transaction retries the same phase after the normal dwell interval. */
bool comp_epaper_motion_coordinator_complete_request(
    comp_epaper_motion_coordinator_t *coordinator,
    uint32_t token,
    uint32_t now_ms,
    bool visible);

/* Physical-panel timing: requested_ms/visible_ms/now_ms must share one wrapping
 * clock. Only a matching successful completion with a visibility timestamp
 * inside its request may use short transition/peak holds. Post-visible RAM
 * synchronization counts toward the hold, without releasing frame ownership.
 * Failure and invalid timestamps retain the legacy retry/absolute schedule.
 * No new pose, randomness, panel command or static allocation is introduced. */
bool comp_epaper_motion_coordinator_complete_request_timed(
    comp_epaper_motion_coordinator_t *coordinator,
    uint32_t token,
    uint32_t now_ms,
    bool visible,
    uint32_t requested_ms,
    uint32_t visible_ms);

bool comp_epaper_motion_coordinator_idle_timeout_elapsed(
    const comp_epaper_motion_coordinator_t *coordinator,
    uint32_t now_ms);

/* Refresh the awake deadline only when the authored product scheduler is
 * explicitly continuous. Sleep remains a separate product transition. */
void comp_epaper_motion_coordinator_keep_awake(
    comp_epaper_motion_coordinator_t *coordinator,
    uint32_t now_ms);

void comp_epaper_motion_coordinator_snapshot(
    const comp_epaper_motion_coordinator_t *coordinator,
    comp_epaper_motion_snapshot_t *out_snapshot);

void comp_epaper_natural_blink_init(
    comp_epaper_natural_blink_scheduler_t *scheduler,
    const comp_epaper_natural_blink_config_t *config);
void comp_epaper_natural_blink_enter_daily(
    comp_epaper_natural_blink_scheduler_t *scheduler,
    uint32_t now_ms);
void comp_epaper_natural_blink_cancel(
    comp_epaper_natural_blink_scheduler_t *scheduler);
uint32_t comp_epaper_natural_blink_remaining_ms(
    const comp_epaper_natural_blink_scheduler_t *scheduler,
    uint32_t now_ms);
bool comp_epaper_natural_blink_take_due(
    comp_epaper_natural_blink_scheduler_t *scheduler,
    uint32_t now_ms,
    comp_epaper_natural_blink_phase_t *out_phase);
bool comp_epaper_natural_blink_complete_open(
    comp_epaper_natural_blink_scheduler_t *scheduler,
    uint32_t visible_ms);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_MOTION_COORDINATOR_H */
