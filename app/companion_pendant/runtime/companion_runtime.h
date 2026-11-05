#ifndef COMPANION_PRODUCT_RUNTIME_H
#define COMPANION_PRODUCT_RUNTIME_H
#include "audio_feedback.h"
#include "browser_interaction_runtime.h"
#include "touch_tap_arbiter.h"
#include "screen_menu.h"
#include "screen_lifecycle.h"
#include "motion_coordinator.h"
#include "denzic_audio_recording_v1.h"
#include "ft6336.h"
#include "motion_events.h"
#include "companion_pet_behavior.h"
#include "companion_pet_play.h"

/* One foreground owner. Recording/OTA keep their existing engines and wire
 * formats. This layer arbitrates user intent; it never invents stored audio,
 * transfer completion, time, battery measurements or an available backend. */
typedef enum {
    COMP_RUNTIME_OK, COMP_RUNTIME_UNAVAILABLE, COMP_RUNTIME_BUSY,
    COMP_RUNTIME_BACKEND_FAILED
} comp_runtime_result_t;

typedef enum {
    COMP_RECORD_STOP_NONE=0, COMP_RECORD_STOP_REQUESTED,
    COMP_RECORD_STOP_PREPARE_TIMEOUT, COMP_RECORD_STOP_GATE_NOT_READY,
    COMP_RECORD_STOP_DURATION_LIMIT, COMP_RECORD_STOP_LOW_BATTERY,
    COMP_RECORD_STOP_POWER_UNKNOWN,COMP_RECORD_STOP_SILENCE,COMP_RECORD_STOP_STORAGE_FULL
} comp_runtime_record_stop_reason_t;
typedef enum {
    COMP_RUNTIME_WAKE_NONE=0, COMP_RUNTIME_WAKE_GENERIC,
    COMP_RUNTIME_WAKE_KEY, COMP_RUNTIME_WAKE_TOUCH,
    COMP_RUNTIME_WAKE_PICKUP, COMP_RUNTIME_WAKE_RECORDING
} comp_runtime_wake_source_t;

typedef enum {
    COMP_RUNTIME_MENU_COMPLETE, COMP_RUNTIME_MENU_PENDING,
    COMP_RUNTIME_MENU_UNAVAILABLE, COMP_RUNTIME_MENU_BUSY, COMP_RUNTIME_MENU_FAILED
} comp_runtime_menu_dispatch_t;
typedef enum {
    COMP_RUNTIME_MENU_FEEDBACK_NONE, COMP_RUNTIME_MENU_FEEDBACK_WORKING,
    COMP_RUNTIME_MENU_FEEDBACK_PAIRING, COMP_RUNTIME_MENU_FEEDBACK_CLEARING,
    COMP_RUNTIME_MENU_FEEDBACK_SAVED, COMP_RUNTIME_MENU_FEEDBACK_CLEARED,
    COMP_RUNTIME_MENU_FEEDBACK_RESTORED, COMP_RUNTIME_MENU_FEEDBACK_CONNECTED,
    COMP_RUNTIME_MENU_FEEDBACK_UNAVAILABLE, COMP_RUNTIME_MENU_FEEDBACK_BUSY,
    COMP_RUNTIME_MENU_FEEDBACK_FAILED, COMP_RUNTIME_MENU_FEEDBACK_RETRYING,
    COMP_RUNTIME_MENU_FEEDBACK_TIMEOUT
} comp_runtime_menu_feedback_t;
typedef enum {
    COMP_RUNTIME_FRAME_STATUS, COMP_RUNTIME_FRAME_LIFE,
    COMP_RUNTIME_FRAME_REACTION, COMP_RUNTIME_FRAME_BLINK,
    COMP_RUNTIME_FRAME_HOLD, COMP_RUNTIME_FRAME_RECORDING_WAVE,
    COMP_RUNTIME_FRAME_SLEEP
} comp_runtime_frame_kind_t;

/* Finite original-art phrases; parked sleep has no animation clock. */
enum {
    COMP_RUNTIME_SLEEP_NONE, COMP_RUNTIME_SLEEP_DOZE,
    COMP_RUNTIME_SLEEP_YAWN, COMP_RUNTIME_SLEEP_PARK,
    COMP_RUNTIME_SLEEP_WAKE, COMP_RUNTIME_SLEEP_ATTEND
};

enum {
    COMP_RUNTIME_PET_INPUT_NONE, COMP_RUNTIME_PET_INPUT_TAP,
    COMP_RUNTIME_PET_INPUT_STROKE, COMP_RUNTIME_PET_INPUT_FOLLOW,
    /* Private deferred payload: x=motion flags, y=qualified tilt, ms=observed
     * time. Shares one slot with touch intents; no sample/trajectory queue. */
    COMP_RUNTIME_PET_INPUT_MOTION
};
enum {
    COMP_RUNTIME_UPDATE_NONE, COMP_RUNTIME_UPDATE_RECEIVING,
    COMP_RUNTIME_UPDATE_VERIFYING, COMP_RUNTIME_UPDATE_INSTALLING,
    COMP_RUNTIME_UPDATE_RESTARTING, COMP_RUNTIME_UPDATE_CONFIRMING,
    COMP_RUNTIME_UPDATE_READY, COMP_RUNTIME_UPDATE_FAILED
};
typedef struct {
    uint32_t token, revision, status_packed;
    uint32_t chat_caption_token; /* Immutable bottom-line owner; zero means absent. */
    /* Recording and OTA are exclusive product owners. The immutable frame
     * captures either elapsed seconds or phase(low8)/percent(high8,255 unknown).
     * Sharing this slot adds no resident framebuffer/runtime memory. */
    union { uint32_t recording_elapsed_seconds, update_display, trace_intent_ms; };
    /* Kind-specific owner: wave completion cannot consume another recording;
     * HOLD completion cannot credit a later finger's progress. */
    union { uint32_t recording_token, hold_generation; };
    comp_runtime_frame_kind_t kind;
    comp_screen_surface_t surface;
    comp_browser_family_t family;
    comp_epaper_motion_request_t motion;
    comp_screen_menu_t menu;
    denzic_audio_recording_state_v1_t recording;
    comp_runtime_result_t last_result;
    comp_runtime_menu_feedback_t menu_feedback;
    uint16_t gaze_x, gaze_y, battery_mv; /* Zero means no qualified cell reading. */
    /* HOLD owns this byte while held; a recording frame may instead snapshot
     * its input meter. 0 means unavailable, 1..5 encode zero to four bars. */
    union { uint8_t hold_bucket, recording_input_level; };
    uint8_t orientation, reaction_from, reaction_to, reaction_zone, reaction_step;
    uint32_t reaction_generation;
    uint8_t recording_wave_index;
    uint8_t temporary_quiet_minutes; /* Immutable display snapshot, not a preference. */
    uint8_t reaction_pose_phase; /* 0 arrive, 1 peak, 2 release; semantic step stays stable. */
    uint8_t pet_variant; /* Cosmetic choice remains stable throughout a reply. */
    uint32_t pet_seed;
    uint8_t pet_interaction, pet_intensity;
    /* Compact flags fund the discovery deadline without growing resident
     * runtime state. These are private C frames, not a serialized wire ABI. */
    bool reaction_transition : 1;
    bool reaction_reply : 1;
    bool reaction_expression : 1;
    bool family_clean : 1;
    bool blink_closed : 1;
    bool start_pending : 1;
    bool prepare_pending : 1;
    bool connected : 1;
    bool discovery_hint : 1;
    /* Actual local speaker suppression, not inferred from a BLE connection. */
    bool pet_sound_suppressed : 1;
    bool pet_caption : 1; /* Immutable, rare, first expressive beat only. */
    /* Explicit finite trace only; uses the idle REACTION union above.
     * This stamps software intent acceptance, not physical finger onset. */
    uint8_t trace_intent_kind : 2;
    uint8_t pet_accent : 3; /* Immutable contextual face; same existing beat. */
    uint8_t pet_play_caption : 3; /* Explicit activity/recording cue; one bottom line. */
    bool recording_input_locked : 1; /* Same-recording HOLD; not a menu hold. */
    bool speaker_ornament : 1; /* Recent completed output, immutable for this frame. */
    bool recording_hold_control : 1; /* This frame actually paints the small lock. */
    bool recording_paused : 1; /* Accepted owner remains; microphone is inactive. */
    bool record_saved_notice : 1; /* Same-token backend save, never command acceptance. */
    uint8_t sleep_phase : 3; /* Immutable phrase beat, qualified by generation. */
    uint8_t record_stop_reason : 4; /* Captured with this frame, never live renderer state. */
} comp_runtime_frame_t;
typedef struct {
    comp_speaker_t *speaker;
    void *context;
    bool (*recording_ready)(void *context);
    /* start is called only after the acoustic gate. Return means the command
     * was accepted, NOT that capture or storage finished. Report actual state
     * through recording_update, using the same request token. */
    bool (*recording_control)(void *context, bool start, uint32_t token);
    bool (*menu_action)(void *context, const comp_screen_menu_result_t *action,
                        const comp_screen_menu_t *settings);
    /* Optional two-phase storage preparation. Poll ready() afterward; the
     * start cue and control(true) happen only once preparation finishes. */
    bool (*recording_prepare)(void *context, uint32_t token);
    /* Nonblocking hardware entropy. An unavailable source holds the family;
     * timestamps/display completions must never impersonate entropy. */
    bool (*random_u32)(void *context, uint32_t *value);
    /* A complete return means a verified effect; pending requires the same
     * token in menu_complete. The legacy bool port is synchronous only. */
    comp_runtime_menu_dispatch_t (*menu_action_begin)(void *context,
        const comp_screen_menu_result_t *action, const comp_screen_menu_t *settings,
        uint32_t token);
} comp_runtime_config_t;
typedef struct {
    comp_runtime_config_t config;
    comp_audio_feedback_t audio;
    comp_touch_gesture_state_t gesture;
    comp_touch_tap_arbiter_t taps;
    comp_browser_interaction_runtime_t affect;
    comp_browser_menu_hold_runtime_t hold;
    comp_screen_menu_t menu;
    comp_epaper_motion_coordinator_t life;
    comp_epaper_natural_blink_scheduler_t blink, blink_before_frame;
    comp_runtime_frame_t in_flight;
    comp_screen_surface_t surface, visible_surface;
    comp_screen_menu_view_t visible_menu_view;
    denzic_audio_recording_state_v1_t recording;
    comp_runtime_result_t last_result;
    comp_runtime_menu_feedback_t menu_feedback;
    comp_screen_menu_action_t menu_pending_action;
    uint32_t menu_token;
    uint8_t menu_pending_item; /* UI84 setting: low6 item, high2 previous choice. */
    uint8_t menu_pending_context, menu_feedback_context;
    bool menu_pending : 1;
    bool battery_display_previous : 1;
    bool last_result_from_menu : 1;
    bool menu_pending_retrying : 1;
    bool menu_feedback_seen : 1;
    uint8_t menu_effect_result : 3;
    /* Shared record notice lifecycle: 1/2 saved, 3/4 stop help, pending/visible.
     * Only one can own the bottom line and the existing record notice timer. */
    uint8_t record_saved_state : 3;
    /* A touch begun on recording/saving cannot become a fresh START when
     * the backend finishes before the old ink has been replaced. */
    bool record_touch_start_blocked : 1;
    uint32_t revision, visible_revision, next_token, record_token;
    uint8_t sleep_phase : 3; /* Borrows reaction_due_ms while reactions are cancelled. */
    /* Chat borrows the idle presenter staging/committed strip. No resident
     * text bitmap, font, audio buffer or extra framebuffer is allocated. */
    uint32_t chat_caption_token, chat_visible_token, chat_due_ms;
    uint8_t chat_caption_state, chat_received_rows;
    /* Accepted limit; later preference edits cannot shorten this recording. */
    uint32_t record_limit_seconds;
    uint32_t recording_captured_ms;
    bool recording_capture_clock;
    /* Sticky for this capture: later touch/menu results cannot erase why a
     * preparation was cancelled before the microphone ever started. */
    uint8_t record_stop_reason;
    uint32_t last_activity_ms, retry_display_ms, recording_since_ms, status_packed;
    uint32_t temporary_quiet_started_ms;
    uint8_t temporary_quiet_base_level, temporary_quiet_last_minute;
    union { uint32_t recording_display_second, update_display; };
    /* Preparation and terminal saved-receipt dwell cannot own this clock together. */
    union { uint32_t prepare_since_ms, record_saved_due_ms; };
    uint32_t last_touch_sequence, last_motion_sequence, rejected_commands;
    uint32_t visible_frames, failed_frames, stale_completions;
    uint8_t display_failure_streak;
    bool last_display_activated; /* No-change is not a physical speed sample. */
    uint32_t visible_menu_revision;
    /* Contact owner: MENU uses visible control revision, recording lock uses
     * its recording token. Status-only display completions do not rebind it. */
    uint32_t input_contact_visible_frame;
    uint32_t reaction_generation, reaction_due_ms;
    uint32_t hold_generation; /* Changes only when a new menu hold begins. */
    uint32_t frame_requested_ms, pet_discovery_due_ms;
    /* family_retry_ms also bounds sustained-motion suppression while that
     * flag owns autonomous scheduling; no entropy retry runs during the lease. */
    uint32_t reaction_input_after_ms, family_due_ms, family_retry_ms, autonomous_family_changes;
    comp_browser_family_t reaction_route[COMP_BROWSER_FAMILY_COUNT];
    uint8_t reaction_route_count, reaction_variant, reaction_step, reaction_zone, reaction_after_zone;
    uint8_t reaction_pose_phase, reaction_pose_count;
    uint8_t pet_variant;
    comp_pet_behavior_t pet;
    bool pet_startup_pending : 1;
    bool pet_discovery_allowed : 1;
    bool pet_discovery_visible : 1;
    bool pet_discovery_pending_save : 1;
    uint8_t pet_discovery_save_attempts : 2; /* Max three failures per boot. */
    /* One latest relative up/down/back while the same view is updating.
     * Uses the remaining two bits; never queues coordinates or button taps. */
    uint8_t menu_deferred_swipe : 2;
    uint16_t gaze_x, gaze_y, battery_mv;
    uint8_t orientation; /* low3bits body axis; bit7 sustained-motion lease */
    uint8_t recording_wave_index;
    /* FT6x36 DOWN after CONTACT can start the next tap without an UP report. */
    uint8_t last_touch_event;
    bool frame_outstanding, reaction_pending, start_pending, command_pending, prepare_pending;
    bool stop_pending, touch_sequence_valid, motion_sequence_valid;
    bool touch_contact, drag_contact, hold_enter_requested, connected, quiet, quiet_hours_active;
    bool temporary_quiet_active;
    bool visible_menu_valid, input_contact_eligible;
    comp_screen_surface_t input_contact_surface;
    uint8_t visible_menu_home_page;
    bool capture_active, booted, family_clean;
    /* One latest waiting intent, shared by touch and incidental motion.
     * Touch wins; motion expires after1500ms and cannot cross owner changes.
     * Follow is attention, distinct from tap/stroke; no trajectory queue. */
    uint16_t deferred_pet_x, deferred_pet_y;
    uint32_t deferred_pet_ms; /* Age of waiting intent, not the active phrase. */
    uint8_t deferred_pet_kind;
    /* One head-sweep intent per contact; no trajectory queue or new artwork. */
    uint16_t pet_stroke_anchor_x;
    uint8_t pet_stroke_phase;
    /* Contact ownership: top pull or release-only quick-volume selection. */
    uint8_t quick_contact;
    uint16_t quick_volume_x;
    comp_pet_play_t pet_play;
    /* One pure wave slot after an authored commit; independent of life due. */
    bool recording_wave_due, recording_wave_started;
    /* Updated only on a real LOW_POWER -> HOME transition from an existing
     * input path. Repeated awake activity never fabricates another wake. */
    uint32_t wake_count, last_wake_ms;
    comp_runtime_wake_source_t last_wake_source;
} comp_runtime_t;

void comp_runtime_init(comp_runtime_t *, const comp_runtime_config_t *, uint32_t now_ms);
/* UI only; never controls or confirms an update. Recording retains its slot.
 * Zero clears the temporary OTA scene; unknown progress remains255. */
void comp_runtime_update_progress(comp_runtime_t *, uint16_t phase_percent, uint32_t now_ms);
void comp_runtime_service(comp_runtime_t *, uint32_t now_ms);
void comp_runtime_set_discovery_seen(comp_runtime_t *, bool seen);
/* sequence is incremented only on a NEW acquisition (not on every main-loop
 * poll). Bad reports cancel contact without fabricating a release/tap. */
void comp_runtime_touch(comp_runtime_t *, const comp_ft6336_touch_sample_t *,
                        uint32_t sequence, bool valid, uint32_t now_ms);
/* Current adapter availability loss, separate from report acquisition IDs.
 * Cancels contact/gesture ownership without synthesizing a release or tap.
 * A delayed invalid report must still use comp_runtime_touch's sequence gate. */
void comp_runtime_touch_unavailable(comp_runtime_t *);
void comp_runtime_motion(comp_runtime_t *, uint8_t events, uint8_t orientation,
                         uint32_t sequence, uint32_t now_ms);
/* Tilt is in verified screen coordinates from motion_events, or UNKNOWN.
 * The legacy motion entry supplies UNKNOWN and retains its original inputs. */
void comp_runtime_motion_pose(comp_runtime_t *, uint8_t events, uint8_t orientation,
    uint8_t tilt, uint32_t sequence, uint32_t now_ms);
void comp_runtime_wake(comp_runtime_t *, uint32_t now_ms);
void comp_runtime_wake_from(comp_runtime_t *, uint32_t now_ms,
                            comp_runtime_wake_source_t source);
void comp_runtime_set_connected(comp_runtime_t *, bool connected, uint32_t now_ms);
void comp_runtime_set_quiet(comp_runtime_t *, bool quiet);
void comp_runtime_set_personality(comp_runtime_t *,unsigned type,uint32_t individual_seed);
/* Local time supplied by the existing host clock; no fabricated RTC hour. */
void comp_runtime_local_hour(comp_runtime_t *, bool valid, uint8_t hour);
/* Low 16 clock bits and bit17/upper-byte measured battery match the existing
 * status codec. BLE and unknown-battery policy are owned by this runtime. */
void comp_runtime_status(comp_runtime_t *, uint32_t packed_status);
/* Qualified cell voltage only; 0 means unavailable. Voltage updates do not
 * schedule home/pet refreshes. The power page shows volts when SOC is unknown. */
void comp_runtime_battery_voltage(comp_runtime_t *, uint16_t millivolts);
void comp_runtime_catalog(comp_runtime_t *, uint16_t recording_count, uint16_t used_kib);
comp_runtime_result_t comp_runtime_record(comp_runtime_t *, bool start, uint32_t now_ms);
/* Same asynchronous stop/drain as the user control, with a sticky cause.
 * Repeated accepted requests cannot replace the original stop reason. */
comp_runtime_result_t comp_runtime_record_stop(comp_runtime_t *,comp_runtime_record_stop_reason_t,uint32_t now_ms);
/* Per-recording HOLD, never a global/preference or a microphone pause.
 * The visible recorder control must supply its current token. Local touch
 * and short key respect the lock; explicit remote/long-key STOP does not.
 * Pause/disconnect retain it; a terminal report or accepted new START clears it. */
bool comp_runtime_recording_owned(const comp_runtime_t *);
bool comp_runtime_recording_hold(const comp_runtime_t *);
comp_runtime_result_t comp_runtime_recording_set_hold(comp_runtime_t *,uint32_t token,
    bool locked,uint32_t now_ms);
/* A host's fixed limit overrides the local default for this recording only.
 * Zero retains that default. Rejected requests cannot alter an active limit. */
comp_runtime_result_t comp_runtime_record_start_limited(comp_runtime_t *,
                                                      uint16_t seconds,uint32_t now_ms);
/* Must be called after the backend stopped its DMA on errors/end. capture_active
 * is independent of finalizing storage; no stop cue before capture is off. */
bool comp_runtime_recording_update(comp_runtime_t *, uint32_t token,
    denzic_audio_recording_state_v1_t state, bool capture_active, uint32_t now_ms);
/* Opt-in logical recorder: the capture owner supplies accepted PCM duration.
 * Wall-clock pause gaps never become recorded audio or reset the session. */
bool comp_runtime_recording_captured(comp_runtime_t *, uint32_t token,
                                    uint32_t captured_ms);
bool comp_runtime_menu_complete(comp_runtime_t *, uint32_t token,
    comp_runtime_result_t result, uint32_t now_ms);
bool comp_runtime_menu_retrying(comp_runtime_t *, uint32_t token, bool retrying);
bool comp_runtime_menu_pair_timeout(comp_runtime_t *, uint32_t token, uint32_t now_ms);
bool comp_runtime_take_frame(comp_runtime_t *, uint32_t now_ms, comp_runtime_frame_t *);
bool comp_runtime_complete_frame(comp_runtime_t *, uint32_t token, bool visible, uint32_t now_ms);
/* Report only after the complete display transaction releases its buffers.
 * visible_ms is the earlier BUSY-qualified visibility time, used only for
 * pet dwell/blink cadence. Errors/input/recording keep now_ms. */
bool comp_runtime_complete_frame_timed(comp_runtime_t *, uint32_t token, bool visible,
                                       uint32_t now_ms, uint32_t visible_ms);
/* Explicit per-request activation fact from the presenter. */
bool comp_runtime_complete_frame_observed(comp_runtime_t *, uint32_t token, bool visible,
                                       uint32_t now_ms, uint32_t visible_ms, bool activated);
#endif
