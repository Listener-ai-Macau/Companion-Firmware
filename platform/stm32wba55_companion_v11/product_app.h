#ifndef COMPANION_V11_PRODUCT_APP_H
#define COMPANION_V11_PRODUCT_APP_H
#include "board_hal.h"
#include "companion_runtime.h"
#include "companion_renderer.h"
#include "companion_resources.h"
#include "screen_assets_stm32wba.h"
#include "screen_presenter_wba.h"
#include "power_settings_store.h"
#include "wba_recording_product.h"
#include "companion_recording_identity.h"
#include "companion_preferences.h"
#include "capture_feedback.h"
#include "companion_pet_profile_wire.h"
#include "wba_silence_stop.h"
#include "wba_recording_level.h"
#include "wba_button.h"
#include "recorder_input.h"
typedef struct {
    comp_v11_hal_t *board;
    comp_runtime_t runtime;
#if COMPANION_WBA_SCREEN_ENABLED
    comp_runtime_renderer_t renderer;
#endif
    comp_runtime_resources_t resources;
    comp_screen_presenter_wba_t presenter;
    companion_spi_nor_stm32wba_partition_t resource_partition;
    companion_screen_assets_stm32wba_t asset_reader;
    comp_asset_store_t asset_store;
    comp_power_settings_store_t settings;
    comp_preferences_t preferences;
    comp_pet_profile_store_t pet_profile;
    companion_spi_nor_stm32wba_partition_t pet_profile_partition;
    comp_clock_t clock;
    comp_wba_silence_stop_t silence;
    comp_wba_recording_level_t recording_level;
    bool recording_level_enabled;
    companion_spi_nor_stm32wba_partition_t preferences_partition;
    companion_spi_nor_stm32wba_partition_t settings_partition;
    companion_spi_nor_stm32wba_partition_t recording_identity_partition;
    comp_rec_identity_t recording_identity;
    /* Hardware bootstrap entropy retires once CSI1 is loaded. Subsequent
     * allocations use its durable epoch/counter and reuse this session RAM. */
    union {uint64_t identity_entropy,recording_session_id;};
    comp_wba_recording_product_t recording;
    comp_v11_microphone_fault_baseline_t capture_baseline;
#if COMPANION_WBA_SCREEN_ENABLED
    uint8_t asset_cache[256];
#endif
#if !COMPANION_WBA_SCREEN_ENABLED
    uint8_t panel_committed[1];
#elif COMP_WBA_PACKED_OLD_FRAME
    comp_wba_frame_store_t panel_committed_storage;
    uint8_t *panel_committed;
#else
    uint8_t panel_committed[5000];
#endif
    uint8_t panel_staging[COMPANION_WBA_SCREEN_ENABLED ? 5000 : 1];
    comp_wba_button_t button;
    comp_recorder_input_t input;
    uint32_t last_touch_count, last_motion_ms;
    /* Physical UART service only: finite display hold/trace, never capture.
     * Holding stops new presenter submits; active transactions still finish. */
    uint32_t panel_debug_hold_until_ms, panel_debug_trace_until_ms;
    /* Opt-in, finite physical-key baseline replay. No bitmap allocation. */
    uint32_t panel_debug_key_until_ms, panel_debug_replay_id;
    uint8_t panel_debug_replay_state, panel_debug_replay_reply, panel_debug_same_partial;
    /* Explicit service-port one-shot: catch the next completed normal full
     * before this foreground pass can submit another frame. No auto refresh. */
    uint32_t panel_debug_catch_until_ms, panel_debug_catch_full_count;
    uint32_t panel_debug_catch_failures;
    uint8_t panel_debug_catch_reply;
    uint8_t last_imu_wake_sequence;
    /* Maximum unserviced capture interval, including each indivisible task.
     * Resource reads may yield to audio without changing rendered pixels. */
    uint32_t capture_started_ms, capture_cycle_started_ms, max_capture_foreground_ms, capture_deadline_faults;
    uint32_t pointer_service_due_ms;
    uint32_t max_capture_hal_ms,max_capture_recorder_ms,max_capture_ble_ms;
    uint32_t max_capture_runtime_ms,max_capture_presenter_ms,max_capture_render_ms;
    bool assets_ready, settings_ready, recording_ready;
    bool storage_layout_ready, silence_stop_requested,recording_link_retry;
    /* One actual stopped-fault event may recover its existing durable prefix. */
    bool recording_fault_recovery_pending;
    uint8_t identity_entropy_words;
    /* First real capture-deadline failure location; no live UART logging. */
    uint8_t capture_deadline_site;
    /* Snapshot at accepted prepare; START/resume never reread mutable settings. */
    uint8_t capture_profile;
} comp_v11_product_app_t;
/* NULL ports binds real WBA PCM -> continuous Opus/COP1 -> segmented pool.
 * External product ports can override coordination. BLE/OTA still require
 * the product target. This never promotes diagnostic PCM to a saved meeting. */
void comp_v11_product_app_init(comp_v11_product_app_t *, comp_v11_hal_t *, const comp_runtime_config_t *ports);
void comp_v11_product_app_poll(comp_v11_product_app_t *);
/* A real consumer opts in; reset on change and require a fresh output window. */
void comp_v11_product_recording_level_enable(comp_v11_product_app_t *,bool enabled);
/* Valid only while capture is active and the final-output window is fresh. */
bool comp_v11_product_recording_level(const comp_v11_product_app_t *,uint32_t now_ms,
                                      comp_wba_recording_level_snapshot_t *);
/* Explicit service retry after automatic stopped-fault recovery was refused.
 * True means accepted, not saved/finished. No START, identity allocation,
 * forced lease release, erase, reset or automatic retry. Poll normally. */
bool comp_v11_product_recording_recover(comp_v11_product_app_t *);
/* Queue at most one bounded idle-storage recovery on a newly secured link.
 * Disconnect only cancels an unstarted request; it never stops recording. */
void comp_v11_product_recording_link_change(comp_v11_product_app_t *,bool connected,bool new_secure);
/* Current visible token and monotonic nonzero UI request. Acceptance is
 * pending; poll the durable result before showing a saved mark. */
bool comp_v11_product_recording_bookmark(comp_v11_product_app_t *,uint32_t token,uint32_t request);
comp_segment_result_t comp_v11_product_recording_bookmark_result(const comp_v11_product_app_t *,uint32_t token,uint32_t request);
/* PCP1 uses the existing encrypted card characteristic, not settings or OTA.
 * Only an idle HOME presenter may lend its staging strip for ordered rows. */
bool comp_v11_product_pet_caption(comp_v11_product_app_t *,const uint8_t *,size_t,uint32_t);
void comp_v11_product_pet_caption_status(const comp_v11_product_app_t *,uint8_t out[16]);
bool comp_v11_product_render_pet_caption(comp_v11_product_app_t *,const comp_runtime_frame_t *,uint8_t frame[5000]);
bool comp_v11_product_committed_read(comp_v11_product_app_t *,size_t,uint8_t *,size_t);
uint32_t comp_v11_product_committed_crc(comp_v11_product_app_t *);
typedef struct { uint32_t calls,total_ms,max_ms; } comp_v11_download_read_timing_t;
/* Legacy journal timing has no observations with the segmented storage port;
 * this compatibility getter returns zero calls, never a measured read cost. */
void comp_v11_product_download_timing(bool enabled);
comp_v11_download_read_timing_t comp_v11_product_download_read_timing(void);
bool comp_v11_product_recording_capacity(const comp_v11_product_app_t *,
                                       companion_recording_capacity_v1_t *);
/* No flash/radio access, recording command, resident queue or sleep blocker.
 * updating comes from the existing OTA owner, not a requested UI action. */
comp_capture_feedback_t comp_v11_product_capture_feedback(const comp_v11_product_app_t *,bool updating);
/* CIN1 on the existing encrypted settings characteristic. Mode is scoped to
 * the connected host, has no flash preference, and cannot change mid-press. */
size_t comp_v11_product_input_request(comp_v11_product_app_t *,const uint8_t *,size_t,
    bool busy,uint32_t now,uint8_t response[64]);
uint16_t comp_v11_product_input_signals(const comp_v11_product_app_t *);
void comp_v11_product_input_status(const comp_v11_product_app_t *,uint32_t request,
    uint8_t result,uint8_t response[64]);
/* OTA owns a durable tail reservation; zero releases it. No implicit loss. */
bool comp_v11_product_update_workspace(void *,uint32_t,uint32_t *);
/* WUS2 mount/lease result, before capture becomes available. */
void comp_v11_product_recording_lease_result(comp_v11_product_app_t *,bool);
/* Shared foreground policy; a sleep surface must have really committed.
 * BLE owns transfer/update/NVM blockers, which this function preserves. */
bool comp_v11_product_update_idle_policy(comp_v11_product_app_t *);
bool comp_v11_product_apply_settings(comp_v11_product_app_t *,const uint8_t *,size_t);
/* Settings v1 prefix (10 bytes) followed by actual UTC H/M/S. Unknown clock
 * uses FF/FF/FF so a successful GATT write cannot invent clock evidence. */
void comp_v11_product_settings(const comp_v11_product_app_t *,uint8_t out[13]);
/* Legacy first13 bytes plus LE Unix seconds; zero means unknown date. */
void comp_v11_product_calendar_settings(const comp_v11_product_app_t *,uint8_t out[17]);
bool comp_v11_product_save_preferences(comp_v11_product_app_t *,const comp_preferences_values_t *);
/* Restores preferences only; recordings, paired peers, UTC and calibration stay owned by their stores. */
bool comp_v11_product_restore_defaults(comp_v11_product_app_t *);
/* Explicit encrypted PMP1, idle storage admission and generation-checked data.
 * No recording/library ingestion or speech is enabled by this interface. */
size_t comp_v11_product_pet_profile(comp_v11_product_app_t *,const uint8_t *,size_t,
    bool other_storage_busy,uint32_t now,uint8_t response[96]);
/* Physical service: validated mounting map only. Save/readback must succeed
 * before applying. Does not zero sensors, wake/reset or qualify any frame. */
bool comp_v11_product_apply_imu_axes(comp_v11_product_app_t *,uint8_t packed);
#if COMPANION_WBA_IMU_RAW_UART
bool comp_v11_product_imu_uart(comp_v11_product_app_t *,bool enabled,uint32_t now);
#endif
/* EPD KEY arms for 120 seconds; EPD RUN exits. Normal startup is unarmed. */
bool comp_v11_product_panel_debug_key(comp_v11_product_app_t *,bool enabled,uint32_t now_ms);
/* EPD SAME admits one frozen, same-bitmap normal partial; no automatic replay. */
bool comp_v11_product_panel_debug_same(comp_v11_product_app_t *,uint32_t now_ms);
/* EPD BASE admits one frozen F7 baseline. SAME may follow during completed
 * observation without RUN or an intervening pet frame. Neither auto-retries. */
bool comp_v11_product_panel_debug_base(comp_v11_product_app_t *,uint32_t now_ms);
/* EPD CATCH waits at most 30s for an actual full completion and freezes its
 * committed HOME bitmap. It never requests/retries a full or partial update. */
bool comp_v11_product_panel_debug_catch(comp_v11_product_app_t *,uint32_t now_ms);
#endif
