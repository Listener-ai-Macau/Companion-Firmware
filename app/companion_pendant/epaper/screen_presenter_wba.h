#ifndef COMPANION_SCREEN_PRESENTER_WBA_H
#define COMPANION_SCREEN_PRESENTER_WBA_H

#include "refresh_policy.h"
#include "ssd1681_wba.h"
#include "../runtime/companion_runtime.h"

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_SCREEN_PRESENTER_WBA_RECOVERY_FULL_MIN_MS 60000u

typedef bool (*comp_screen_presenter_wba_render_fn_t)(
    void *context,
    const comp_runtime_frame_t *request,
    uint8_t frame[COMP_SSD1681_WBA_FRAME_BYTES]);

typedef void (*comp_screen_presenter_wba_complete_fn_t)(
    void *context,
    uint32_t token,
    bool visible,
    uint32_t now_ms);

typedef enum {
    COMP_SCREEN_PRESENTER_WBA_IDLE = 0,
    COMP_SCREEN_PRESENTER_WBA_ACTIVE,
    COMP_SCREEN_PRESENTER_WBA_NOT_READY,
} comp_screen_presenter_wba_status_t;

typedef enum {
    COMP_SCREEN_PRESENTER_WBA_SUBMIT_BAD_ARGUMENT = 0,
    COMP_SCREEN_PRESENTER_WBA_SUBMIT_BUSY,
    COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED,
    /* The request was consumed and completion was called synchronously. */
    COMP_SCREEN_PRESENTER_WBA_SUBMIT_COMPLETED,
} comp_screen_presenter_wba_submit_result_t;

typedef struct {
    comp_ssd1681_wba_t *panel;
    comp_screen_presenter_wba_render_fn_t render;
    comp_screen_presenter_wba_complete_fn_t complete;
    void *context;
    /* Distinct caller-owned storage, retained in flight. With
     * COMP_WBA_PACKED_OLD_FRAME, committed_frame points at the FIRST bytes of
     * a comp_wba_frame_store_t; staging_frame remains the full5000B bitmap. */
    uint8_t *committed_frame;
    uint8_t *staging_frame;
    uint8_t partial_limit;
    /* Optional renderer observation for authored wink/closed-eye reopening.
     * Consulted after render, before starting the existing partial waveform. */
    bool (*opens_eyes)(void *context);
} comp_screen_presenter_wba_config_t;

typedef struct {
    uint32_t submitted;
    uint32_t rendered;
    uint32_t render_failures;
    uint32_t no_change_completions;
    uint32_t full_started;
    uint32_t fast_started;
    uint32_t partial_started;
    uint32_t recording_started;
    uint32_t visible_completions;
    uint32_t failed_completions;
    uint32_t busy_rejections;
    uint32_t recovery_full_started;
} comp_screen_presenter_wba_stats_t;

/* Public for static allocation. Treat fields after config as presenter-owned. */
typedef struct {
    comp_screen_presenter_wba_config_t config;
    comp_epaper_refresh_policy_t refresh_policy;
    comp_screen_presenter_wba_stats_t stats;
    comp_runtime_frame_t request;
    comp_epaper_refresh_selection_t selection;
    comp_ssd1681_wba_window_t dirty_window;
    comp_screen_presenter_wba_status_t status;
    comp_screen_surface_t committed_surface;
    comp_screen_menu_view_t committed_menu_view;
    bool committed_valid;
    bool committed_surface_valid;
    bool committed_recording_active;
    /* Observation for motion dwell only. The completion callback still runs
     * at transaction completion, after immutable frame buffers are released. */
    uint32_t visible_completed_ms;
    /* Retained across a successful recovery full. Only a failed panel is
     * held; healthy partial updates and requested page boundaries stay live. */
    uint32_t recovery_full_not_before_ms;
    bool recovery_full_guard_armed;
    /* Scheduling only, independent of the driver's F7/OTP history. A
     * successful supplier C7 restarts the five-minute/192-update interval;
     * FAST, partial, failed and no-change requests never reset it. */
    uint8_t full_cadence_updates;
    bool request_activated; /* Exact fact; false for synchronous no-change. */
    uint32_t full_cadence_ms;
    /* Foreground-only CPU work yield; never recursively advances this presenter. */
    bool (*progress)(void *context);
} comp_screen_presenter_wba_t;
void comp_screen_presenter_wba_set_progress(comp_screen_presenter_wba_t *,bool (*)(void *));

bool comp_screen_presenter_wba_init(
    comp_screen_presenter_wba_t *presenter,
    const comp_screen_presenter_wba_config_t *config);

/* Observation only, with a wrapping deadline. Check before taking a runtime
 * frame so a recovery quiet gap neither consumes a request nor reports a
 * fabricated display failure. No panel I/O or blocking delay is performed. */
bool comp_screen_presenter_wba_ready_for_frame(
    const comp_screen_presenter_wba_t *presenter, uint32_t now_ms);

/* Copies the immutable runtime snapshot before rendering. For a valid request,
 * ACCEPTED or COMPLETED consumes it and guarantees one completion callback.
 * BAD_ARGUMENT and BUSY do not consume it and do not call completion. */
comp_screen_presenter_wba_submit_result_t comp_screen_presenter_wba_submit(
    comp_screen_presenter_wba_t *presenter,
    const comp_runtime_frame_t *request,
    uint32_t now_ms);

/* Observation only: the board owner advances comp_ssd1681_wba_poll once per
 * foreground cycle. This function never polls the panel or performs I/O. */
comp_screen_presenter_wba_status_t comp_screen_presenter_wba_service(
    comp_screen_presenter_wba_t *presenter,
    uint32_t now_ms);

void comp_screen_presenter_wba_get_stats(
    const comp_screen_presenter_wba_t *presenter,
    comp_screen_presenter_wba_stats_t *stats);

/* Explicit service-port observation only. Replay the immutable committed
 * bitmap through the same software-reset/F7/two-plane baseline as startup.
 * Caller admits only idle HOME, blocks normal submissions, and keeps audio/
 * transfer/update guards. No new runtime token or fabricated motion beat. */
bool comp_screen_presenter_wba_debug_replay_baseline(
    comp_screen_presenter_wba_t *presenter, uint32_t now_ms);

/* Physical debug key: replay the same accepted picture using the existing
 * qualified vendor quick-full transaction; never fall back to a partial. */
bool comp_screen_presenter_wba_debug_replay_quick_full(
    comp_screen_presenter_wba_t *presenter,uint32_t now_ms);

/* Physical double click: the existing normal flashing full transaction. */
bool comp_screen_presenter_wba_debug_replay_flashing_full(
    comp_screen_presenter_wba_t *presenter,uint32_t now_ms);

/* Explicit service-only contrast isolation: one normal paired Mode2 update
 * with OLD == CURRENT == the immutable committed bitmap. No render, reset,
 * waveform substitution, maintenance promotion or runtime beat. The caller
 * must hold new submissions and preserve recording/transfer priority. */
bool comp_screen_presenter_wba_debug_replay_same_partial(
    comp_screen_presenter_wba_t *presenter, uint32_t now_ms);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_SCREEN_PRESENTER_WBA_H */
