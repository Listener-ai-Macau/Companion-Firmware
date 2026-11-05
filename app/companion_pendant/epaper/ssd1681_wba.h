#ifndef COMPANION_EPAPER_SSD1681_WBA_H
#define COMPANION_EPAPER_SSD1681_WBA_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "wba_frame_store.h"

#ifndef COMP_V11_PANEL_FULL_REFRESH_ONLY
#define COMP_V11_PANEL_FULL_REFRESH_ONLY 0
#endif

/* Source-bound supplier full-frame LUT. Hardware and explicitly experimental
 * software-reset bindings are distinct; neither implies optical qualification. */
#ifndef COMP_V11_PANEL_VENDOR_QUICK_FULL
#define COMP_V11_PANEL_VENDOR_QUICK_FULL 0
#endif
#ifndef COMP_V11_PANEL_VENDOR_QUICK_SOFTWARE_RESET
#define COMP_V11_PANEL_VENDOR_QUICK_SOFTWARE_RESET 0
#endif

#ifndef COMP_V11_PANEL_STAGED_MODE2_POWER
#define COMP_V11_PANEL_STAGED_MODE2_POWER 0
#endif
#ifndef COMP_V11_PANEL_SENSE_POWER
#define COMP_V11_PANEL_SENSE_POWER 0
#endif
#ifndef COMP_V11_PANEL_STUCK_BUSY_AUDIT
#define COMP_V11_PANEL_STUCK_BUSY_AUDIT 0
#endif
#ifndef COMP_V11_PANEL_START_RETRY
#define COMP_V11_PANEL_START_RETRY 0
#endif
#ifndef COMP_V11_PANEL_WINDOW_REPAIR
#define COMP_V11_PANEL_WINDOW_REPAIR 0
#endif
#ifndef COMP_V11_PANEL_STATUS_GATE
#define COMP_V11_PANEL_STATUS_GATE 0
#endif
#ifndef COMP_V11_PANEL_PASSIVE_TRACE
#define COMP_V11_PANEL_PASSIVE_TRACE 0
#endif

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_SSD1681_WBA_WIDTH 200u
#define COMP_SSD1681_WBA_HEIGHT 200u
#define COMP_SSD1681_WBA_BYTES_PER_ROW 25u
#define COMP_SSD1681_WBA_FRAME_BYTES 5000u
#define COMP_SSD1681_WBA_DEFAULT_PARTIAL_LIMIT 64u

/* Recovered recording overlay bounds in the native 200x200 top-left
 * coordinate system. The presenter flips rows for the controller. */
#define COMP_SSD1681_WBA_RECORDING_X_MIN 2u
#define COMP_SSD1681_WBA_RECORDING_X_MAX 41u
#define COMP_SSD1681_WBA_RECORDING_Y_MIN 156u
#define COMP_SSD1681_WBA_RECORDING_Y_MAX 179u
#define COMP_SSD1681_WBA_RECORDING_CONTROLLER_X_BYTE_MIN \
    (COMP_SSD1681_WBA_RECORDING_X_MIN / 8u)
#define COMP_SSD1681_WBA_RECORDING_CONTROLLER_X_BYTE_MAX \
    (COMP_SSD1681_WBA_RECORDING_X_MAX / 8u)
#define COMP_SSD1681_WBA_RECORDING_CONTROLLER_Y_MIN \
    ((COMP_SSD1681_WBA_HEIGHT - 1u) - COMP_SSD1681_WBA_RECORDING_Y_MAX)
#define COMP_SSD1681_WBA_RECORDING_CONTROLLER_Y_MAX \
    ((COMP_SSD1681_WBA_HEIGHT - 1u) - COMP_SSD1681_WBA_RECORDING_Y_MIN)

typedef bool (*comp_ssd1681_wba_transfer_fn_t)(void *context,
                                                bool data,
                                                const uint8_t *bytes,
                                                uint16_t size);
typedef bool (*comp_ssd1681_wba_reset_fn_t)(void *context, bool asserted);
typedef bool (*comp_ssd1681_wba_busy_fn_t)(void *context);
typedef uint32_t (*comp_ssd1681_wba_now_ms_fn_t)(void *context);

typedef enum {
    /* Default keeps the existing requirement for a real RESET endpoint. */
    COMP_SSD1681_WBA_RESET_HARDWARE = 0,
    /* Explicit bring-up path for a powered, responsive controller. This
     * cannot wake deep sleep or recover a held RES#/stuck BUSY signal. */
    COMP_SSD1681_WBA_RESET_SOFTWARE_ONLY,
} comp_ssd1681_wba_reset_mode_t;

typedef enum {
    COMP_SSD1681_WBA_NOT_READY = 0,
    COMP_SSD1681_WBA_IDLE,
    COMP_SSD1681_WBA_ACTIVE,
    COMP_SSD1681_WBA_COMPLETE,
    COMP_SSD1681_WBA_ERROR,
} comp_ssd1681_wba_status_t;

typedef enum {
    COMP_SSD1681_WBA_ERROR_NONE = 0,
    COMP_SSD1681_WBA_ERROR_CONFIGURATION,
    COMP_SSD1681_WBA_ERROR_ARGUMENT,
    COMP_SSD1681_WBA_ERROR_TRANSPORT,
    COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT,
    COMP_SSD1681_WBA_ERROR_CANCELLED,
    COMP_SSD1681_WBA_ERROR_BASELINE_REQUIRED,
    COMP_SSD1681_WBA_ERROR_MAINTENANCE_REQUIRED,
} comp_ssd1681_wba_error_t;

typedef enum {
    COMP_SSD1681_WBA_OBSERVE_RESET_READY = 0,
    COMP_SSD1681_WBA_OBSERVE_MODE1_READY,
    COMP_SSD1681_WBA_OBSERVE_MODE2_READY,
    COMP_SSD1681_WBA_OBSERVE_PARTIAL_READY,
    COMP_SSD1681_WBA_OBSERVE_MODE2_POWER_CHECKED,
    COMP_SSD1681_WBA_OBSERVE_STUCK_START,
} comp_ssd1681_wba_observe_point_t;

typedef enum {
    COMP_SSD1681_WBA_RETRY_DENIED = 0,
    COMP_SSD1681_WBA_RETRY_RAM_MATCHED,
    COMP_SSD1681_WBA_RETRY_RAM_REWRITE,
} comp_ssd1681_wba_retry_check_t;

typedef struct {
    uint8_t x_start_byte;
    uint8_t x_end_byte;
    uint16_t y_start;
    uint16_t y_end;
} comp_ssd1681_wba_window_t;

#if COMP_V11_PANEL_PASSIVE_TRACE
typedef enum {
    COMP_SSD1681_WBA_BUSY_EDGES_SAMPLE = 0,
    COMP_SSD1681_WBA_BUSY_EDGES_ARM,
    COMP_SSD1681_WBA_BUSY_EDGES_STOP,
} comp_ssd1681_wba_busy_edges_action_t;
#endif

typedef struct {
    comp_ssd1681_wba_transfer_fn_t transfer;
    comp_ssd1681_wba_reset_fn_t set_reset;
    comp_ssd1681_wba_busy_fn_t is_busy;
    comp_ssd1681_wba_now_ms_fn_t now_ms;
    void *context;
    uint16_t payload_chunk_bytes;
    uint16_t busy_timeout_ms;
    uint8_t partial_limit;
    comp_ssd1681_wba_reset_mode_t reset_mode;
    /* Legacy engineering slots retained for source/layout compatibility.
     * The production driver always sends row-bounded data and separate CS
     * command/data packets; it does not invoke either optimization. */
    bool (*allow_row_batching)(void *context);
    /* Legacy register packet hook; not invoked by the production driver. */
    bool (*transfer_register)(void *context, uint8_t command,
                              const uint8_t *parameters, uint8_t size);
    /* Optional bounded engineering observation after qualified ready. It
     * must leave RAM addressing suitable for the following full-window
     * setup. Observations never qualify a visible refresh or its baseline. */
    void (*observe_ready)(void *context,
                          comp_ssd1681_wba_observe_point_t point);
    /* Optional ready-only status read for the staged Mode-2 power audit and
     * a bounded, non-recording pre-activation communication qualification.
     * Readback does not replace the visible BUSY assertion/completion gate. */
    bool (*read_status)(void *context, uint8_t *status);
    /* Optional ready-only recovery check after an unobserved visible start.
     * Must verify internal ready and old/current RAM samples, restore RAM
     * addressing, and reject capture/playback. Never qualifies completion. */
    comp_ssd1681_wba_retry_check_t (*check_activation_retry)(void *context);
    /* Optional policy for starting one cooperative software-reset/Mode2
     * recovery after 100ms with no observed BUSY. Requires immutable paired
     * full frames; completion still needs BUSY high, stable low and RAM sync.
     * Reject playback/unsafe contexts. Capture may be allowed only for the
     * recording operation with per-poll command/row service preserved. */
    bool (*allow_mode2_recovery)(void *context);
#if COMP_V11_PANEL_PASSIVE_TRACE
    /* Optional diagnostic latches only: bit0 rising, bit1 falling. ARM
     * discards old flags, SAMPLE drains, STOP drains then disables latching.
     * No ISR or SPI access; these flags NEVER qualify visible completion. */
    uint8_t (*take_busy_edges)(void *context,
                              comp_ssd1681_wba_busy_edges_action_t action);
#endif
} comp_ssd1681_wba_config_t;

typedef struct {
    uint32_t transfer_calls;
    uint32_t transferred_bytes;
    uint32_t completed_full;
    uint32_t completed_partial;
    uint32_t completed_fast;
    uint32_t completed_recording;
    uint32_t transport_errors;
    uint32_t busy_timeouts;
    uint32_t cancellations;
    uint8_t partial_count;
    uint32_t first_failure_ms, first_failure_wait_ms;
    uint8_t first_failure_stage, first_failure_operation;
    uint8_t first_failure_sequence, first_failure_error;
    bool first_failure_busy;
    uint32_t last_command_ms, last_completed_ms, last_visible_wait_ms;
    /* BUSY high then stable low; successful transaction completion remains
     * separate because post-refresh RAM synchronization may still fail. */
    uint32_t last_visible_completed_ms;
    uint32_t last_busy_change_ms, ready_glitches, idle_busy_edges;
    uint32_t completed_paired;
    uint32_t completed_blink_rebases;
    uint32_t mode2_since_full, last_full_ms;
    uint32_t max_start_wait_ms, delayed_starts;
    uint8_t last_command;
    uint32_t mode2_power_checks;
    uint8_t mode2_power_status, mode2_power_busy_mask;
    bool mode2_power_status_valid;
    uint32_t activation_start_misses, activation_retries, activation_recoveries;
    uint32_t activation_recovery_last_ms;
    uint32_t activation_ram_rewrites;
    uint32_t activation_gate_checks, activation_gate_invalid;
    uint32_t activation_gate_qualified, activation_gate_timeouts;
    uint32_t activation_gate_max_wait_ms;
    uint8_t activation_gate_last_status;
#if COMP_V11_PANEL_PASSIVE_TRACE
    /* Initial ready gate of the first failed transaction, frozen with the
     * first failure. Foreground samples and coalesced latches are not a
     * continuous electrical measurement or an authorization to write. */
    uint32_t first_ready_started_ms, first_ready_last_poll_ms;
    uint32_t first_ready_samples, first_ready_high_samples;
    uint32_t first_ready_max_poll_gap_ms, first_ready_max_quiet_ms;
    uint32_t first_ready_rise_samples;
    uint8_t first_ready_edge_flags;
    /* Foreground levels and coalesced edge flags. These do not authorize completion and
     * neither prove continuous high duration nor count electrical pulses. */
    uint32_t visible_activation_count, visible_started_ms;
    uint32_t visible_first_high_ms, visible_last_high_ms;
    uint32_t visible_high_samples, visible_poll_samples;
    uint32_t visible_last_poll_ms, visible_max_poll_gap_ms, missed_max_poll_gap_ms;
    uint8_t visible_edge_flags, missed_edge_flags;
    bool visible_edges_available;
    /* Preserve the original miss before recovery replaces its window and
     * visible samples. Timestamps observe existing stages; no bus probing. */
    uint32_t missed_started_ms, missed_at_ms, missed_poll_samples, missed_high_samples;
    comp_ssd1681_wba_window_t missed_window;
    uint8_t missed_operation, missed_phase;
    uint32_t recovery_reset_ms, recovery_profile_ms;
    uint32_t recovery_activation_ms, recovery_ready_ms;
#endif
} comp_ssd1681_wba_stats_t;

/* Public so callers can allocate it statically. Fields after config/stats are
 * driver-owned and must not be modified. */
typedef struct {
    comp_ssd1681_wba_config_t config;
    comp_ssd1681_wba_stats_t stats;
    comp_ssd1681_wba_status_t status;
    comp_ssd1681_wba_error_t error;
    const uint8_t *previous_frame;
#if COMP_WBA_PACKED_OLD_FRAME
    comp_wba_frame_store_t *old_store;
#endif
    const uint8_t *current_frame;
    comp_ssd1681_wba_window_t window;
    /* Capture bounds; ordinary/fast preserve the visible window here when
     * a first-after-full or recovery post-sync expands RAM writes to200x200. */
    comp_ssd1681_wba_window_t recording_window;
    /* Old/current remain immutable for this transaction. Reuse its full dirty
     * bounds across ordinary rectangles and both post-sync planes. */
    comp_ssd1681_wba_window_t recording_dirty_bounds;
    bool recording_dirty_valid;
    uint32_t deadline_ms;
    uint32_t wait_started_ms;
    uint32_t ready_started_ms;
    uint16_t data_y;
    uint16_t scan_offset;
    uint8_t data_x;
    uint8_t stage;
    uint8_t operation;
    uint8_t sequence;
    uint8_t sequence_index;
    uint8_t sequence_data_pending;
    uint8_t data_command_sent;
    uint8_t recording_phase;
    uint8_t recording_ordinary_region;
    uint8_t ram_x[2];
    uint8_t ram_y[4];
    uint8_t x_counter[1];
    uint8_t y_counter[2];
    bool baseline_valid;
    bool maintenance_required;
    bool busy_observed;
    bool ready_candidate, busy_sampled, busy_level;
    bool normalize_previous;
    uint8_t power_busy_mask;
    bool activation_retried, activation_retry_checked;
    bool activation_repairing;
    /* A synchronized C7 image may rest without loading a different LUT.
     * The next Mode2 transaction must qualify this rearm before any RAM or
     * activation, including the recording-specific CF path. */
    bool mode2_rearm_pending;
    uint32_t activation_deadline_ms;
    uint32_t activation_gate_next_ms;
} comp_ssd1681_wba_t;

/* Hardware mode requires a real RESET callback. Software-only mode requires
 * no callback and an always-powered controller; it never sends deep sleep.
 * Successful configuration is not evidence of a responding physical panel. */
bool comp_ssd1681_wba_init(comp_ssd1681_wba_t *driver,
                           const comp_ssd1681_wba_config_t *config);
/* Read logical controller bytes from either immutable representation. */
bool comp_ssd1681_wba_read_frame(comp_ssd1681_wba_t *,const uint8_t *,size_t,uint8_t *,size_t);
#if COMP_WBA_PACKED_OLD_FRAME
bool comp_ssd1681_wba_bind_old_store(comp_ssd1681_wba_t *,comp_wba_frame_store_t *);
#endif

/* Frame pointers must remain valid and unchanged until poll reports COMPLETE
 * or ERROR. The full path uses the accepted old/current dual-plane topology. */
bool comp_ssd1681_wba_start_full(comp_ssd1681_wba_t *driver,
                                 const uint8_t *previous_frame,
                                 const uint8_t *current_frame,
                                 size_t frame_bytes);

/* Distinct from Mode2 start_fast_pair: literal supplier 159-byte LUT, one
 * current 5000-byte plane and C7 activation. Requires the explicit build
 * profile and a real hardware-reset callback. Rejects unavailable hardware
 * before altering the baseline or sending SPI; caller may retain its existing
 * navigation policy. No temperature-range or optical qualification implied. */
/* Explicit normal flashing Mode1 full update; preserve the common BUSY,
 * reset and complete old/current RAM synchronization transaction. */
bool comp_ssd1681_wba_start_flashing_full(comp_ssd1681_wba_t *driver,
    const uint8_t *previous_frame,const uint8_t *current_frame,size_t frame_bytes);
bool comp_ssd1681_wba_vendor_quick_full_available(const comp_ssd1681_wba_t *driver);
bool comp_ssd1681_wba_start_vendor_quick_full(comp_ssd1681_wba_t *driver,
    const uint8_t *previous_frame, const uint8_t *current_frame, size_t frame_bytes);

/* current_frame is a complete 25-byte-stride controller-coordinate frame.
 * The byte-aligned window selects the rows and columns transferred. */
bool comp_ssd1681_wba_start_partial(
    comp_ssd1681_wba_t *driver,
    const uint8_t *current_frame,
    size_t frame_bytes,
    const comp_ssd1681_wba_window_t *window);

/* Product animation carries the last physically committed frame explicitly:
 * previous->0x26, current->0x24, one Mode-2 activation, then current->0x24
 * and current->0x26 over the SAME local RAM window without another activation.
 * All complete-frame differences MUST be contained in the supplied window;
 * otherwise the request is rejected before any transfer. First-after-full,
 * fast and recovery transactions retain full200x200 post-normalization.
 * Commit only after both planes represent the complete new image. Optical
 * equivalence of local post-sync still needs physical qualification. */
bool comp_ssd1681_wba_start_partial_pair(
    comp_ssd1681_wba_t *driver, const uint8_t *previous_frame,
    const uint8_t *current_frame, size_t frame_bytes,
    const comp_ssd1681_wba_window_t *window);

/* Authored blink-open uses the same guarded dual-RAM sync as other Mode2
 * frames, retaining the separate completed_blink_rebases counter. No synthetic
 * white rows or expanded visible window. One activation only. */
bool comp_ssd1681_wba_start_blink_open(
    comp_ssd1681_wba_t *driver, const uint8_t *previous_frame,
    const uint8_t *current_frame, size_t frame_bytes,
    const comp_ssd1681_wba_window_t *window);

/* Recording-specific Mode-2 transaction.  The ordinary dirty rectangle is
 * split around recording_window and initially written to 0x24. Changed byte
 * runs inside the window are written previous->0x26 and current->0x24, then
 * the union of all changed regions is restored as the RAM area and activated
 * once with 0xCF/BUSY. This includes face/status changes outside the recording
 * overlay; the final sparse write run is not the activation area. Afterward
 * both the ordinary rectangles and
 * exact changed runs are synchronized current->0x24 and current->0x26 without
 * another activation. Unchanged bytes inside the recording window (including
 * a static microphone glyph) are not transferred. */
bool comp_ssd1681_wba_start_recording_partial(
    comp_ssd1681_wba_t *driver,
    const uint8_t *previous_frame,
    const uint8_t *current_frame,
    size_t frame_bytes,
    const comp_ssd1681_wba_window_t *recording_window);

/* Family-boundary update: full-frame actual-temperature Mode-2 0xFF, one visible
 * activation, no reset/Mode-1/rearm. Requires an established baseline. */
bool comp_ssd1681_wba_start_fast(comp_ssd1681_wba_t *driver,
    const uint8_t *current_frame, size_t frame_bytes);
bool comp_ssd1681_wba_start_fast_pair(comp_ssd1681_wba_t *driver,
    const uint8_t *previous_frame, const uint8_t *current_frame,
    size_t frame_bytes);

/* Task-context only. Each call transfers one frame chunk or one short register
 * command with at most four parameter bytes (two bounded transfer callbacks).
 * RAM/register stages pause on sampled BUSY and require stable-ready before
 * resuming; an unexpected stuck BUSY expires against the existing deadline.
 * Do not call from an ISR. */
comp_ssd1681_wba_status_t comp_ssd1681_wba_poll(
    comp_ssd1681_wba_t *driver);
void comp_ssd1681_wba_cancel(comp_ssd1681_wba_t *driver);

/* No IO. True only while a RAM command/row can be serviced by the next
 * bounded poll. BUSY, reset settling and register-sequence stages are false.
 * The foreground owner must still honor capture/playback priority. */
bool comp_ssd1681_wba_ram_write_pending(const comp_ssd1681_wba_t *driver);
/* No IO. Allows the platform recovery policy to distinguish the bounded
 * recording transaction from an ordinary frame overlapping capture start. */
bool comp_ssd1681_wba_recording_active(const comp_ssd1681_wba_t *driver);

comp_ssd1681_wba_status_t comp_ssd1681_wba_status(
    const comp_ssd1681_wba_t *driver);
/* ERROR recovery admission after foreground low samples span20ms. Reads the
 * cached filter, time and BUSY input; no SPI, RESET or EXTI changes. This is
 * not electrical/latched proof: the started transaction independently keeps
 * its original edge-qualified ready gate before sending any command. */
bool comp_ssd1681_wba_recovery_ready(const comp_ssd1681_wba_t *driver);
comp_ssd1681_wba_error_t comp_ssd1681_wba_error(
    const comp_ssd1681_wba_t *driver);
bool comp_ssd1681_wba_baseline_valid(const comp_ssd1681_wba_t *driver);
bool comp_ssd1681_wba_maintenance_required(
    const comp_ssd1681_wba_t *driver);
void comp_ssd1681_wba_get_stats(const comp_ssd1681_wba_t *driver,
                                 comp_ssd1681_wba_stats_t *stats);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_SSD1681_WBA_H */
