#include "screen_presenter_wba.h"

#include <stddef.h>
#include <string.h>

#if defined(__GNUC__)
#define COMP_PRESENTER_POLICY __attribute__((optimize("Os"),noinline))
#define COMP_PRESENTER_PIXELS __attribute__((optimize("O3"),noinline))
#else
#define COMP_PRESENTER_POLICY
#define COMP_PRESENTER_PIXELS
#endif

/* Continuous pet motion stays on differential Mode2. A periodic full
 * maintenance request is eligible only at a settled family boundary after
 * five minutes and192 completed updates; never interrupt a blink/recording.
 * Count from the last completed full transaction, including supplier C7.
 * This is cadence control, not qualification of C7 as an optical clean. */
#define GHOST_CLEAN_MIN_MS 300000u
#define GHOST_CLEAN_UPDATE_LIMIT 192u
/* Initial navigation policy: count changed pixels, not the bounding box of
 * distant tiny changes. This is software selection, not a faster scan claim. */
#define MENU_LARGE_CHANGE_PIXELS (COMP_SSD1681_WBA_WIDTH * COMP_SSD1681_WBA_HEIGHT / 16u)

static bool clean_boundary(const comp_screen_presenter_wba_t *presenter,
                           const comp_runtime_frame_t *request,
                           uint32_t now_ms)
{
    const bool recorder_settled =
        request->recording == DENZIC_AUDIO_RECORDING_STATE_IDLE ||
        request->recording == DENZIC_AUDIO_RECORDING_STATE_CANCELED ||
        request->recording == DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY ||
        request->recording == DENZIC_AUDIO_RECORDING_STATE_TRANSFERRED;
    /* Use an existing autonomous family boundary, never a touch reaction,
     * blink or capture frame. Mode-2 fast updates do not clear the accumulated
     * count: they still use the differential waveform. */
    return request->surface == COMP_SCREEN_SURFACE_HOME && request->family_clean &&
        request->kind == COMP_RUNTIME_FRAME_LIFE && !request->blink_closed &&
        !request->start_pending && !request->prepare_pending && recorder_settled &&
        !presenter->committed_recording_active &&
        presenter->full_cadence_updates >= GHOST_CLEAN_UPDATE_LIMIT &&
        now_ms - presenter->full_cadence_ms >= GHOST_CLEAN_MIN_MS;
}

static bool config_valid(const comp_screen_presenter_wba_config_t *config)
{
    return config != NULL && config->panel != NULL &&
           config->render != NULL && config->complete != NULL &&
           config->committed_frame != NULL && config->staging_frame != NULL &&
           config->committed_frame != config->staging_frame;
}

/* The accepted WB product maps browser rows to controller rows with a vertical
 * row flip only. V1.1 keeps this mapping until physical-panel validation can
 * confirm or revise it; no rotation or horizontal mirror is introduced here. */
static void COMP_PRESENTER_PIXELS apply_accepted_row_mapping(uint8_t *frame)
{
    uint8_t row[COMP_SSD1681_WBA_BYTES_PER_ROW];

    for (uint16_t top = 0u; top < COMP_SSD1681_WBA_HEIGHT / 2u; ++top) {
        const uint16_t bottom =
            (uint16_t)(COMP_SSD1681_WBA_HEIGHT - 1u - top);
        uint8_t *top_row =
            &frame[(size_t)top * COMP_SSD1681_WBA_BYTES_PER_ROW];
        uint8_t *bottom_row =
            &frame[(size_t)bottom * COMP_SSD1681_WBA_BYTES_PER_ROW];
        memcpy(row, top_row, sizeof(row));
        memcpy(top_row, bottom_row, sizeof(row));
        memcpy(bottom_row, row, sizeof(row));
    }
}

static bool old_read(comp_screen_presenter_wba_t *p,size_t at,uint8_t *out,size_t bytes)
{
#if COMP_WBA_PACKED_OLD_FRAME
    return comp_wba_frame_store_read((comp_wba_frame_store_t *)(void *)p->config.committed_frame,at,out,bytes);
#else
    memcpy(out,p->config.committed_frame+at,bytes);return true;
#endif
}
void comp_screen_presenter_wba_set_progress(comp_screen_presenter_wba_t *p,bool (*progress)(void *))
{if(p)p->progress=progress;}
static bool cpu_progress(comp_screen_presenter_wba_t *p)
{return !p->progress || p->progress(p->config.context);}
static bool store_current(comp_screen_presenter_wba_t *p)
{
#if COMP_WBA_PACKED_OLD_FRAME
    return comp_wba_frame_store_write_progress((comp_wba_frame_store_t *)(void *)p->config.committed_frame,p->config.staging_frame,p->progress,p->config.context);
#else
    memcpy(p->config.committed_frame,p->config.staging_frame,COMP_SSD1681_WBA_FRAME_BYTES);return true;
#endif
}
static uint16_t COMP_PRESENTER_PIXELS find_dirty_window(comp_screen_presenter_wba_t *presenter,
                              const uint8_t *current,
                              comp_ssd1681_wba_window_t *window,bool *interrupted)
{
    uint8_t x_start = COMP_SSD1681_WBA_BYTES_PER_ROW;
    uint8_t x_end = 0u;
    uint16_t y_start = COMP_SSD1681_WBA_HEIGHT;
    uint16_t y_end = 0u;
    bool found = false;
    uint16_t changed_pixels = 0u;

    for (uint16_t y = 0u; y < COMP_SSD1681_WBA_HEIGHT; ++y) {
        if(!(y&7u) && !cpu_progress(presenter)){*interrupted=true;return UINT16_MAX;}
        uint8_t old_row[COMP_SSD1681_WBA_BYTES_PER_ROW];
        if(!old_read(presenter,(size_t)y*COMP_SSD1681_WBA_BYTES_PER_ROW,old_row,sizeof(old_row)))return UINT16_MAX;
        for (uint8_t x = 0u; x < COMP_SSD1681_WBA_BYTES_PER_ROW; ++x) {
            const size_t offset =
                (size_t)y * COMP_SSD1681_WBA_BYTES_PER_ROW + x;
            uint8_t delta = old_row[x] ^ current[offset];
            if (delta == 0u) {
                continue;
            }
            delta = (uint8_t)(delta - ((delta >> 1u) & 0x55u));
            delta = (uint8_t)((delta & 0x33u) + ((delta >> 2u) & 0x33u));
            changed_pixels += (uint16_t)((delta + (delta >> 4u)) & 0x0Fu);
            if (!found || x < x_start) x_start = x;
            if (!found || x > x_end) x_end = x;
            if (!found || y < y_start) y_start = y;
            if (!found || y > y_end) y_end = y;
            found = true;
        }
    }
    if (found && window != NULL) {
        *window = (comp_ssd1681_wba_window_t){x_start, x_end, y_start, y_end};
    }
    return changed_pixels;
}

static bool recording_active(const comp_runtime_frame_t *request)
{
    return request->recording == DENZIC_AUDIO_RECORDING_STATE_RECORDING;
}

static comp_epaper_refresh_mode_t requested_mode(
    const comp_screen_presenter_wba_t *presenter,
    const comp_runtime_frame_t *request,
    uint16_t changed_pixels)
{
    if (presenter->committed_surface_valid &&
        (request->surface == COMP_SCREEN_SURFACE_MENU ||
         presenter->committed_surface == COMP_SCREEN_SURFACE_MENU) &&
        changed_pixels >= MENU_LARGE_CHANGE_PIXELS &&
        !recording_active(request) && !presenter->committed_recording_active) {
        /* Menu entry/exit/navigation is not itself a reason to flash. Large
         * real bitmap changes use C7; small digits, presses and transitions
         * follow the same dirty-window path as the pet. Capture wins. */
        return COMP_EPAPER_REFRESH_MAINTENANCE;
    }
    /* A new expression family changes pixels on the same canvas. Select its
     * actual old/current dirty window, just like a blink or gaze change;
     * the family label alone must not expand the RAM write area to200x200.
     * The independent settled-boundary clean below retains periodic Mode1
     * maintenance, including an identical landing that is genuinely due. */
    return COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE;
}

static void complete_request(comp_screen_presenter_wba_t *presenter,
                             bool visible,
                             uint32_t now_ms)
{
    const uint32_t token = presenter->request.token;

    presenter->status = COMP_SCREEN_PRESENTER_WBA_IDLE;
    if (visible) {
        presenter->stats.visible_completions++;
    } else {
        presenter->stats.failed_completions++;
    }
    /* Token zero is reserved for an explicitly admitted committed-bitmap
     * debug replay. It must not complete/advance an unrelated runtime beat. */
    if (token != 0u)
        presenter->config.complete(presenter->config.context, token, visible,
                                   now_ms);
}

bool comp_screen_presenter_wba_init(
    comp_screen_presenter_wba_t *presenter,
    const comp_screen_presenter_wba_config_t *config)
{
    if (presenter == NULL) return false;
    memset(presenter, 0, sizeof(*presenter));
    presenter->status = COMP_SCREEN_PRESENTER_WBA_NOT_READY;
    if (!config_valid(config)) return false;
    presenter->config = *config;
#if COMP_WBA_PACKED_OLD_FRAME
    if(!comp_ssd1681_wba_bind_old_store(config->panel,(comp_wba_frame_store_t *)(void *)config->committed_frame))return false;
#endif
    comp_epaper_refresh_policy_init(&presenter->refresh_policy,
                                    config->partial_limit);
    presenter->status = COMP_SCREEN_PRESENTER_WBA_IDLE;
    return true;
}

bool comp_screen_presenter_wba_ready_for_frame(
    const comp_screen_presenter_wba_t *presenter, uint32_t now_ms)
{
    if (presenter == NULL ||
        presenter->status != COMP_SCREEN_PRESENTER_WBA_IDLE) return false;
    const comp_ssd1681_wba_t *panel = presenter->config.panel;
    if (comp_ssd1681_wba_status(panel) != COMP_SSD1681_WBA_ERROR) return true;
    /* A failed transaction has no known RAM baseline. Do not consume/render
     * another request on one transient low: ERROR polls must first span the
     * existing20ms sampled quiet interval. The admitted transaction retains
     * its independent latched-edge gate before any SPI command. */
    if (!comp_ssd1681_wba_recovery_ready(panel)) return false;
    return !presenter->recovery_full_guard_armed ||
        (int32_t)(now_ms - presenter->recovery_full_not_before_ms) >= 0;
}

comp_screen_presenter_wba_submit_result_t COMP_PRESENTER_POLICY comp_screen_presenter_wba_submit(
    comp_screen_presenter_wba_t *presenter,
    const comp_runtime_frame_t *request,
    uint32_t now_ms)
{
    comp_epaper_refresh_mode_t mode;
    bool start_ok;
    bool maintenance_due;

    if (presenter == NULL || request == NULL || request->token == 0u ||
        presenter->status == COMP_SCREEN_PRESENTER_WBA_NOT_READY) {
        return COMP_SCREEN_PRESENTER_WBA_SUBMIT_BAD_ARGUMENT;
    }
    if (!comp_screen_presenter_wba_ready_for_frame(presenter, now_ms)) {
        presenter->stats.busy_rejections++;
        return COMP_SCREEN_PRESENTER_WBA_SUBMIT_BUSY;
    }

    presenter->stats.submitted++;
    presenter->request_activated=false;
    presenter->request = *request;
    /* Synchronous no-change completions have no new physical activation.
     * Never borrow a previous transaction's visibility timestamp. */
    presenter->visible_completed_ms = now_ms;
    presenter->status = COMP_SCREEN_PRESENTER_WBA_ACTIVE;
    memset(presenter->config.staging_frame, 0xFF,
           COMP_SSD1681_WBA_FRAME_BYTES);
    if (!presenter->config.render(presenter->config.context,
                                  &presenter->request,
                                  presenter->config.staging_frame)) {
        presenter->stats.render_failures++;
        complete_request(presenter, false, now_ms);
        return COMP_SCREEN_PRESENTER_WBA_SUBMIT_COMPLETED;
    }
    presenter->stats.rendered++;
    if(!cpu_progress(presenter)) {
        complete_request(presenter,false,now_ms);return COMP_SCREEN_PRESENTER_WBA_SUBMIT_COMPLETED;
    }
    apply_accepted_row_mapping(presenter->config.staging_frame);
#if COMP_WBA_PACKED_OLD_FRAME
    const size_t packed_size=comp_wba_frame_store_size_progress(presenter->config.staging_frame,presenter->progress,presenter->config.context);
    if(!packed_size || packed_size>COMP_WBA_FRAME_STORE_BYTES) {
        presenter->stats.render_failures++;complete_request(presenter,false,now_ms);
        return COMP_SCREEN_PRESENTER_WBA_SUBMIT_COMPLETED;
    }
#endif

    bool interrupted=false;
    const uint16_t changed_pixels = presenter->committed_valid
        ? find_dirty_window(presenter,
                            presenter->config.staging_frame,
                            &presenter->dirty_window,&interrupted) : 0u;
    if(changed_pixels==UINT16_MAX) {
        if(!interrupted)presenter->committed_valid=false;
        complete_request(presenter,false,now_ms);return COMP_SCREEN_PRESENTER_WBA_SUBMIT_COMPLETED;
    }
    if(!cpu_progress(presenter)) {
        complete_request(presenter,false,now_ms);return COMP_SCREEN_PRESENTER_WBA_SUBMIT_COMPLETED;
    }
    mode = requested_mode(presenter, request, changed_pixels);
    maintenance_due = clean_boundary(presenter, request, now_ms);
    /* A repeated family landing with identical pixels needs no activation.
     * Preserve an actually due maintenance clean, even on an identical frame. */
    if (presenter->committed_valid &&
        comp_ssd1681_wba_baseline_valid(presenter->config.panel) &&
        (mode == COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE ||
         mode == COMP_EPAPER_REFRESH_MAINTENANCE) &&
        !maintenance_due &&
        changed_pixels == 0u) {
        presenter->stats.no_change_completions++;
        presenter->committed_surface = request->surface;
        presenter->committed_menu_view = request->menu.view;
        presenter->committed_surface_valid = true;
        presenter->committed_recording_active = recording_active(request);
        complete_request(presenter, true, now_ms);
        return COMP_SCREEN_PRESENTER_WBA_SUBMIT_COMPLETED;
    }

    presenter->selection = comp_epaper_refresh_policy_select(
        &presenter->refresh_policy, mode);
    if (!presenter->committed_valid ||
        !comp_ssd1681_wba_baseline_valid(presenter->config.panel)) {
        presenter->selection.decision = COMP_EPAPER_REFRESH_DECISION_FULL;
        presenter->selection.reason =
            COMP_EPAPER_REFRESH_REASON_BASELINE_REQUIRED;
    } else if (maintenance_due) {
        presenter->selection.decision = COMP_EPAPER_REFRESH_DECISION_FULL;
        presenter->selection.reason = COMP_EPAPER_REFRESH_REASON_GHOST_MAINTENANCE;
#if COMP_V11_PANEL_VENDOR_QUICK_FULL && !COMP_V11_PANEL_FULL_REFRESH_ONLY
    } else if (mode == COMP_EPAPER_REFRESH_MAINTENANCE &&
               comp_ssd1681_wba_vendor_quick_full_available(presenter->config.panel)) {
        /* This is a real Mode1 update, not just a larger Mode2 RAM window. */
        presenter->selection.decision = COMP_EPAPER_REFRESH_DECISION_FULL;
        presenter->selection.reason = COMP_EPAPER_REFRESH_REASON_REQUESTED_FULL;
#endif
    } else if (presenter->selection.decision ==
                   COMP_EPAPER_REFRESH_DECISION_PARTIAL &&
               comp_ssd1681_wba_maintenance_required(
                   presenter->config.panel)) {
        presenter->selection.decision = COMP_EPAPER_REFRESH_DECISION_FAST;
        presenter->selection.reason = COMP_EPAPER_REFRESH_REASON_PARTIAL_LIMIT;
    }

#if COMP_V11_PANEL_FULL_REFRESH_ONLY
    /* The recovery candidate deliberately never enters Mode 2. All accepted
     * requests still render through the same real staging/committed buffers. */
    presenter->selection.decision = COMP_EPAPER_REFRESH_DECISION_FULL;
    presenter->selection.reason = COMP_EPAPER_REFRESH_REASON_REQUESTED_FULL;
#endif

    if (presenter->selection.decision ==
        COMP_EPAPER_REFRESH_DECISION_PARTIAL) {
        const comp_ssd1681_wba_window_t recording_window = {
            COMP_SSD1681_WBA_RECORDING_CONTROLLER_X_BYTE_MIN,
            COMP_SSD1681_WBA_RECORDING_CONTROLLER_X_BYTE_MAX,
            COMP_SSD1681_WBA_RECORDING_CONTROLLER_Y_MIN,
            COMP_SSD1681_WBA_RECORDING_CONTROLLER_Y_MAX,
        };
        const bool recording_transition =
            recording_active(request) || presenter->committed_recording_active;

        if (recording_transition) {
            start_ok = comp_ssd1681_wba_start_recording_partial(
                presenter->config.panel, presenter->config.committed_frame,
                presenter->config.staging_frame,
                COMP_SSD1681_WBA_FRAME_BYTES, &recording_window);
            if (start_ok) presenter->stats.recording_started++;
        } else {
            /* Authored winks/laughter and natural blinks share the existing
             * post-BUSY old-plane normalization when eyes reopen. The render
             * observation follows the committed pose, including status holds. */
            if ((request->kind == COMP_RUNTIME_FRAME_BLINK && !request->blink_closed) ||
                (presenter->config.opens_eyes && presenter->config.opens_eyes(presenter->config.context)))
                start_ok = comp_ssd1681_wba_start_blink_open(
                    presenter->config.panel, presenter->config.committed_frame,
                    presenter->config.staging_frame,
                    COMP_SSD1681_WBA_FRAME_BYTES, &presenter->dirty_window);
            else start_ok = comp_ssd1681_wba_start_partial_pair(
                    presenter->config.panel, presenter->config.committed_frame,
                    presenter->config.staging_frame,
                    COMP_SSD1681_WBA_FRAME_BYTES, &presenter->dirty_window);
            if (start_ok) presenter->stats.partial_started++;
        }
    } else if (presenter->selection.decision == COMP_EPAPER_REFRESH_DECISION_FAST) {
        start_ok=comp_ssd1681_wba_start_fast_pair(presenter->config.panel,
            presenter->config.committed_frame,
            presenter->config.staging_frame,COMP_SSD1681_WBA_FRAME_BYTES);
        if (start_ok) presenter->stats.fast_started++;
    } else {
        const bool recovering =
            comp_ssd1681_wba_status(presenter->config.panel) == COMP_SSD1681_WBA_ERROR;
        if (!presenter->committed_valid) {
            /* No physical old image is known after startup/recovery. Seed
             * both RAM planes with the same full target, as the supplier's
             * EPD_SetRAMValue_BaseMap does before its F7 baseline refresh.
             * An inverted target is not an observed old image. Keep validity
             * false until the full BUSY, RAM rebase and Mode2 rearm finish;
             * this copy never authorizes a partial activation by itself. */
            if(!store_current(presenter)) {
                complete_request(presenter,false,now_ms);return COMP_SCREEN_PRESENTER_WBA_SUBMIT_COMPLETED;
            }
        }
#if COMP_V11_PANEL_VENDOR_QUICK_FULL && !COMP_V11_PANEL_FULL_REFRESH_ONLY
        if (mode == COMP_EPAPER_REFRESH_MAINTENANCE && !maintenance_due &&
            presenter->committed_valid &&
            comp_ssd1681_wba_baseline_valid(presenter->config.panel) &&
            comp_ssd1681_wba_vendor_quick_full_available(presenter->config.panel)) {
            start_ok = comp_ssd1681_wba_start_vendor_quick_full(
                presenter->config.panel, presenter->config.committed_frame,
                presenter->config.staging_frame, COMP_SSD1681_WBA_FRAME_BYTES);
        } else
#endif
        start_ok = comp_ssd1681_wba_start_full(
            presenter->config.panel, presenter->config.committed_frame,
            presenter->config.staging_frame,
            COMP_SSD1681_WBA_FRAME_BYTES);
        if (start_ok) presenter->stats.full_started++;
        if (start_ok && recovering) {
            /* A full can succeed while the next local activation still
             * fails. Its success must not reopen an immediate flashing loop.
             * Keep the guard independent of runtime's success/failure streak. */
            presenter->recovery_full_guard_armed = true;
            presenter->recovery_full_not_before_ms =
                now_ms + COMP_SCREEN_PRESENTER_WBA_RECOVERY_FULL_MIN_MS;
            presenter->stats.recovery_full_started++;
        }
    }
    if (!start_ok) {
        if (!comp_ssd1681_wba_baseline_valid(presenter->config.panel)) {
            presenter->committed_valid = false;
            comp_epaper_refresh_policy_commit(&presenter->refresh_policy,
                                               presenter->selection.decision,
                                               false);
        }
        complete_request(presenter, false, now_ms);
        return COMP_SCREEN_PRESENTER_WBA_SUBMIT_COMPLETED;
    }
    presenter->request_activated=true;
    return COMP_SCREEN_PRESENTER_WBA_SUBMIT_ACCEPTED;
}

comp_screen_presenter_wba_status_t comp_screen_presenter_wba_service(
    comp_screen_presenter_wba_t *presenter,
    uint32_t now_ms)
{
    comp_ssd1681_wba_status_t panel_status;

    if (presenter == NULL) return COMP_SCREEN_PRESENTER_WBA_NOT_READY;
    if (presenter->status != COMP_SCREEN_PRESENTER_WBA_ACTIVE) {
        return presenter->status;
    }

    panel_status = comp_ssd1681_wba_status(presenter->config.panel);
    if (panel_status == COMP_SSD1681_WBA_ACTIVE) {
        return presenter->status;
    }
    if (panel_status == COMP_SSD1681_WBA_COMPLETE) {
        presenter->visible_completed_ms =
            presenter->config.panel->stats.last_visible_completed_ms;
        if(!store_current(presenter)) {
            presenter->committed_valid=false;presenter->committed_surface_valid=false;
            complete_request(presenter,false,now_ms);return presenter->status;
        }
        presenter->committed_valid = true;
        presenter->committed_surface = presenter->request.surface;
        presenter->committed_menu_view = presenter->request.menu.view;
        presenter->committed_surface_valid = true;
        presenter->committed_recording_active =
            recording_active(&presenter->request);
        /* Only a qualified completed transaction advances this schedule.
         * C7 must restart the maintenance interval or every later settled
         * family can request another full after the first192 updates.
         * Keep the driver's F7/Mode2 history independent: neither a C7 nor
         * this scheduling counter proves that pale/gray ink was repaired.
         * Failed and no-change requests never reach this accounting. */
        if (presenter->selection.decision == COMP_EPAPER_REFRESH_DECISION_FULL) {
            presenter->full_cadence_ms =
                presenter->config.panel->stats.last_completed_ms;
            presenter->full_cadence_updates = 0u;
        } else if (presenter->full_cadence_updates < GHOST_CLEAN_UPDATE_LIMIT) {
            presenter->full_cadence_updates++;
        }
        comp_epaper_refresh_policy_commit(&presenter->refresh_policy,
                                           presenter->selection.decision,
                                           true);
        complete_request(presenter, true, now_ms);
    } else {
        presenter->committed_valid = false;
        presenter->committed_surface_valid = false;
        presenter->committed_recording_active = false;
        comp_epaper_refresh_policy_commit(&presenter->refresh_policy,
                                           presenter->selection.decision,
                                           false);
        complete_request(presenter, false, now_ms);
    }
    return presenter->status;
}

void comp_screen_presenter_wba_get_stats(
    const comp_screen_presenter_wba_t *presenter,
    comp_screen_presenter_wba_stats_t *stats)
{
    if (presenter != NULL && stats != NULL) *stats = presenter->stats;
}

static bool debug_replay_full(comp_screen_presenter_wba_t *presenter,
                              uint32_t now_ms,uint8_t mode)
{
    if (presenter == NULL || presenter->status != COMP_SCREEN_PRESENTER_WBA_IDLE ||
        !presenter->committed_valid || !presenter->committed_surface_valid ||
        presenter->committed_surface != COMP_SCREEN_SURFACE_HOME ||
        presenter->committed_recording_active ||
        comp_ssd1681_wba_status(presenter->config.panel) == COMP_SSD1681_WBA_ACTIVE ||
        comp_ssd1681_wba_status(presenter->config.panel) == COMP_SSD1681_WBA_ERROR ||
        !comp_ssd1681_wba_baseline_valid(presenter->config.panel)) return false;
    if(mode==1u && !comp_ssd1681_wba_vendor_quick_full_available(presenter->config.panel))return false;
    /* Both buffers are already in controller row order. Do not flip, render,
     * randomize, or allocate another 5000-byte picture during observation. */
    if(!old_read(presenter,0u,presenter->config.staging_frame,COMP_SSD1681_WBA_FRAME_BYTES))return false;
    const bool started=mode==1u?comp_ssd1681_wba_start_vendor_quick_full(presenter->config.panel,
            presenter->config.committed_frame,presenter->config.staging_frame,COMP_SSD1681_WBA_FRAME_BYTES):
        mode==2u?comp_ssd1681_wba_start_flashing_full(presenter->config.panel,
            presenter->config.committed_frame,presenter->config.staging_frame,COMP_SSD1681_WBA_FRAME_BYTES):
        comp_ssd1681_wba_start_full(presenter->config.panel,
            presenter->config.committed_frame,presenter->config.staging_frame,COMP_SSD1681_WBA_FRAME_BYTES);
    if(!started)return false;
    presenter->request.token = 0u;
    presenter->selection.decision = COMP_EPAPER_REFRESH_DECISION_FULL;
    presenter->selection.reason = COMP_EPAPER_REFRESH_REASON_REQUESTED_FULL;
    presenter->dirty_window = (comp_ssd1681_wba_window_t){0u,24u,0u,199u};
    presenter->committed_valid = false;
    presenter->visible_completed_ms = now_ms;
    presenter->stats.full_started++;
    presenter->status = COMP_SCREEN_PRESENTER_WBA_ACTIVE;
    return true;
}

bool comp_screen_presenter_wba_debug_replay_baseline(
    comp_screen_presenter_wba_t *presenter,uint32_t now_ms)
{return debug_replay_full(presenter,now_ms,0u);}

bool comp_screen_presenter_wba_debug_replay_quick_full(
    comp_screen_presenter_wba_t *presenter,uint32_t now_ms)
{return debug_replay_full(presenter,now_ms,1u);}

bool comp_screen_presenter_wba_debug_replay_flashing_full(
    comp_screen_presenter_wba_t *presenter,uint32_t now_ms)
{return debug_replay_full(presenter,now_ms,2u);}

bool comp_screen_presenter_wba_debug_replay_same_partial(
    comp_screen_presenter_wba_t *presenter, uint32_t now_ms)
{
#if COMP_V11_PANEL_FULL_REFRESH_ONLY
    (void)presenter;
    (void)now_ms;
    return false;
#else
    const comp_ssd1681_wba_window_t window = {0u,24u,0u,199u};
    if (presenter == NULL || presenter->status != COMP_SCREEN_PRESENTER_WBA_IDLE ||
        !presenter->committed_valid || !presenter->committed_surface_valid ||
        presenter->committed_surface != COMP_SCREEN_SURFACE_HOME ||
        presenter->committed_recording_active ||
        comp_ssd1681_wba_status(presenter->config.panel) == COMP_SSD1681_WBA_ACTIVE ||
        comp_ssd1681_wba_status(presenter->config.panel) == COMP_SSD1681_WBA_ERROR ||
        !comp_ssd1681_wba_baseline_valid(presenter->config.panel) ||
        comp_ssd1681_wba_maintenance_required(presenter->config.panel)) return false;
    if(!old_read(presenter,0u,presenter->config.staging_frame,COMP_SSD1681_WBA_FRAME_BYTES))return false;
    /* A same-image activation intentionally bypasses only the presenter's
     * no-change shortcut. The original FF/BUSY/full-pair post-sync transaction
     * remains intact. This diagnostic does not qualify the ink contrast. */
    if (!comp_ssd1681_wba_start_partial_pair(presenter->config.panel,
            presenter->config.committed_frame, presenter->config.staging_frame,
            COMP_SSD1681_WBA_FRAME_BYTES, &window)) return false;
    presenter->request.token = 0u;
    presenter->selection.decision = COMP_EPAPER_REFRESH_DECISION_PARTIAL;
    presenter->selection.reason = COMP_EPAPER_REFRESH_REASON_REQUESTED_PARTIAL;
    presenter->dirty_window = window;
    presenter->committed_valid = false;
    presenter->visible_completed_ms = now_ms;
    presenter->stats.partial_started++;
    presenter->status = COMP_SCREEN_PRESENTER_WBA_ACTIVE;
    return true;
#endif
}
