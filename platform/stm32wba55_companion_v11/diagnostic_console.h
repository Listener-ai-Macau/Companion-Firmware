#ifndef COMPANION_V11_DIAGNOSTIC_CONSOLE_H
#define COMPANION_V11_DIAGNOSTIC_CONSOLE_H

#include <stdbool.h>
#include <stdint.h>

/* Reuse the existing finite EPD TRACE lease. Bulk periodic snapshots block
 * foreground input for roughly400ms, so defer them while observing an actual
 * interaction. Explicit before/after queries retain the normal safety gate.
 * No new resident queue, extra timer, DMA ownership or continuous trace. */
static inline bool comp_v11_diag_periodic_allowed(uint32_t now,uint32_t trace_until)
{ return trace_until==0u || (int32_t)(trace_until-now)<=0; }

typedef enum {
    COMP_V11_DIAG_BOOT = 0,
    COMP_V11_DIAG_PERIODIC,
    COMP_V11_DIAG_QUERY,
} comp_v11_diag_reason_t;

typedef enum {
    COMP_V11_DIAG_PANEL_NONE = 0,
    COMP_V11_DIAG_PANEL_HOLD,
    COMP_V11_DIAG_PANEL_RUN,
    COMP_V11_DIAG_PANEL_SNAP,
    COMP_V11_DIAG_PANEL_TRACE,
    COMP_V11_DIAG_PANEL_STATUS,
    COMP_V11_DIAG_PANEL_KEY,
    COMP_V11_DIAG_PANEL_SAME,
    COMP_V11_DIAG_PANEL_BASE,
    COMP_V11_DIAG_PANEL_CATCH,
    COMP_V11_DIAG_PANEL_PINS,
    COMP_V11_DIAG_PANEL_SOUND,
    COMP_V11_DIAG_PANEL_SOUND_GREETING, COMP_V11_DIAG_PANEL_SOUND_CONTENT,
    COMP_V11_DIAG_PANEL_SOUND_PLAYFUL, COMP_V11_DIAG_PANEL_SOUND_SHY,
    COMP_V11_DIAG_PANEL_SOUND_REFERENCE_1K, COMP_V11_DIAG_PANEL_SOUND_REFERENCE_1500,
    COMP_V11_DIAG_PANEL_SOUND_REFERENCE_2K,
} comp_v11_diag_panel_command_t;

/* Existing SOUND remains confirm0; explicit pet IDs4..7 use the same
 * current-volume, quiet/capture/protected-operation admission in main. */
static inline uint8_t comp_v11_diag_sound_cue(comp_v11_diag_panel_command_t command)
{
    if(command==COMP_V11_DIAG_PANEL_SOUND)return 0u;
    if(command>=COMP_V11_DIAG_PANEL_SOUND_GREETING && command<=COMP_V11_DIAG_PANEL_SOUND_SHY)
        return (uint8_t)(4u+(unsigned)command-(unsigned)COMP_V11_DIAG_PANEL_SOUND_GREETING);
    if(command>=COMP_V11_DIAG_PANEL_SOUND_REFERENCE_1K && command<=COMP_V11_DIAG_PANEL_SOUND_REFERENCE_2K)
        return (uint8_t)(8u+(unsigned)command-(unsigned)COMP_V11_DIAG_PANEL_SOUND_REFERENCE_1K);
    return 255u;
}


typedef enum {
    COMP_V11_DIAG_RECORD_NONE=0, COMP_V11_DIAG_RECORD_START, COMP_V11_DIAG_RECORD_STOP,
    COMP_V11_DIAG_RECORD_PAUSE, COMP_V11_DIAG_RECORD_RESUME, COMP_V11_DIAG_RECORD_MARK,
    COMP_V11_DIAG_RECORD_RECOVER, COMP_V11_DIAG_RECORD_CACHE_OFF_NEXT
#if defined(COMPANION_WBA_BLE_LINKED) && COMPANION_WBA_EXPERIMENTAL_STOP1
    , COMP_V11_DIAG_RECORD_STOP1_ONCE, COMP_V11_DIAG_RECORD_STOP1_WINDOW
#endif
} comp_v11_diag_record_command_t;

typedef struct {
    uint32_t sequence, command_candidates;
    bool query_pending;
    bool pair_pending, command_invalid, battery_pending, reconnect_pending;
    uint8_t command_match, panel_command;
    uint8_t imu_candidate_axes,imu_axes,imu_command,record_command;
} comp_v11_diag_console_t;

typedef struct {
    /* UI_PENDING only means that a normal visible surface blocks sleep. It is
     * deliberately accepted here because a read-only UART query does not
     * compete with display I/O. */
    bool ui_pending;
    bool microphone_capture, screen_maintenance, screen_wait, playback;
    bool battery_sample, recording_transfer, storage, update, bond_nvm;
    bool playback_active, microphone_running;
    bool runtime_prepare, runtime_start, runtime_command, runtime_capture, runtime_stop;
} comp_v11_diag_activity_t;

typedef struct {
    uint32_t firmware_version, build_id, board_id, uptime_ms;
    uint8_t uid[12];
    uint32_t ui_generation;
    uint32_t reset_flags, faults;
    bool iwdg_reset;
    uint32_t ram_gap, stack_min_free;
    bool stack_low, stack_guard;

    bool panel_bound, assets_ready;
    uint8_t panel_status, panel_error, presenter_status;
    uint32_t panel_rendered, panel_failed;
    uint8_t panel_stage;
    bool panel_busy;
    uint32_t panel_transfer_calls, panel_busy_timeouts;

    uint32_t nor_jedec, nor_size, recording_committed;
    bool storage_layout_ready, recording_ready;
    uint8_t recording_state, recording_fault;
    bool nor_suspend_qualified, nor_erase_active, nor_erase_suspended;
    uint8_t nor_suspend_wait_ms, nor_resume_guard_ms;
    uint32_t nor_sfdp_dw12, nor_sfdp_dw13;
    uint8_t nor_sfdp_bfp_dwords;

    bool microphone_initialized, microphone_running, speaker_ready;
    uint32_t microphone_hal_error, microphone_error_irqs;
    uint32_t microphone_stale, microphone_overflows, microphone_rejections;
    uint32_t microphone_frames, capture_deadline_faults;
    uint32_t capture_foreground_ms, capture_hal_ms, capture_recorder_ms, capture_ble_ms;
    uint32_t capture_runtime_ms, capture_presenter_ms, capture_render_ms, microphone_poll_ms;
    uint32_t encode_timing_samples, encode_p95_upper_ms, encode_peak_upper_ms;
    uint32_t pdm_timing_samples, pdm_p95_upper_ms, pdm_peak_upper_ms;
    uint32_t timing_recording_id, timing_microphone_starts;
    bool encode_timing_valid, pdm_timing_valid;
    uint32_t battery_reference_age_ms, battery_reference_samples, battery_adc_failures;
    uint32_t battery_sample_errors, battery_gate_errors, battery_adc_samples;
    uint16_t battery_reference_raw, battery_factory_raw, battery_reference_mv, battery_adc_raw;
    uint16_t battery_reference_min_mv, battery_reference_max_mv;
    uint8_t battery_adc_error;
    bool battery_reference_valid, battery_divider_safe, battery_divider_verified, battery_reference_verified;
    uint32_t battery_sample_age_ms;
    uint16_t battery_input_mv;
    bool battery_raw_mode, battery_input_valid, battery_saturated;
    uint32_t battery_top_ohm, battery_bottom_ohm;
    uint16_t battery_maximum_mv, battery_reference_floor_mv;
    bool charger_pullups_verified, battery_soc_curve_verified;

    bool ble_compiled, ble_initialized, ble_host_ready, ble_linked, ble_secured;
    uint8_t ble_host_error;
    uint16_t ble_connection;
    uint32_t ble_fatal;
    uint32_t ble_bond_lost, ble_rebond_attempts;
    uint8_t ble_pairing_status, ble_pairing_reason;

    bool battery_adc_enabled, voltage_valid, percent_valid;
    bool charger_valid, charger_present;
    uint16_t battery_mv, ota_power_blockers;
    uint8_t battery_percent, charge_state;
    uint32_t sleep_blockers;
} comp_v11_diag_snapshot_t;

typedef bool (*comp_v11_diag_write_fn_t)(void *context, const char *line);

comp_v11_diag_panel_command_t comp_v11_diag_console_take_panel(comp_v11_diag_console_t *);

void comp_v11_diag_console_init(comp_v11_diag_console_t *console);
/* '?' reads status; exact 'BATTERY\n' reads one short cached power line.
 * Exact physical UART line 'PAIR\n' requests the normal
 * bounded pairing window; IMU MAP XX/CLEAR installs a validated persistent
 * mounting map under product-idle guards. REC START/REC STOP submit the same
 * runtime request as the local record button, never a separate recorder.
 * No deletion, bootloader or permissions command exists. */
void comp_v11_diag_console_accept(comp_v11_diag_console_t *console, uint8_t byte);
bool comp_v11_diag_console_take_query(comp_v11_diag_console_t *console, bool output_safe);
/* Caller consumes once and rejects protected product work immediately.
 * The guarded variant may finish only an in-flight short battery sample,
 * bounded to250ms (+1ms tick sentinel); never queues behind recording or OTA. */
bool comp_v11_diag_console_take_pair(comp_v11_diag_console_t *console);
bool comp_v11_diag_console_take_pair_guarded(comp_v11_diag_console_t *,uint32_t now,
                                            uint32_t blockers,uint32_t *battery_deadline);
/* Exact BLE RECONNECT: consume once, existing bonded reconnect only. Caller
 * rejects an active link or busy product; never opens a pairing window. */
bool comp_v11_diag_console_take_reconnect(comp_v11_diag_console_t *console);
/* Latest exact wired request, consumed once even when rejected. Replies are
 * deferred while capture/transfer owns the foreground; no later queued start. */
comp_v11_diag_record_command_t comp_v11_diag_console_take_record(comp_v11_diag_console_t *);
bool comp_v11_diag_console_take_battery(comp_v11_diag_console_t *,bool output_safe);
/* Exact physical-service IMU MAP XX or IMU CLEAR. Caller consumes once and
 * rejects when busy; no deferred write after a later product operation. */
bool comp_v11_diag_console_take_imu(comp_v11_diag_console_t *,uint8_t *command,uint8_t *axes);
void comp_v11_diag_console_emit_battery(const comp_v11_diag_snapshot_t *,
                                       comp_v11_diag_write_fn_t,void *context);
bool comp_v11_diag_console_output_safe(const comp_v11_diag_activity_t *activity);
/* Only a physically stopped FAILED recording may use this compact response.
 * The caller proves NOR/catalog quiescence. Logical reservations/runtime flags
 * and panel BUSY remain untouched; this never admits controls or a full dump. */
bool comp_v11_diag_console_fault_output_safe(const comp_v11_diag_activity_t *,bool stopped_fault);
typedef struct {
    uint32_t token,core_hz,blockers,deadline,foreground_ms,budget_failures,max_poll_ms;
    uint32_t pcm_blocks,encoded_packets,stale,overflows,rejections,irq_errors;
    uint16_t runtime_flags;
    uint8_t pipeline,failure,record_fault,engine,engine_failure,queue_depth;
    uint8_t catalog_phase,future_phase,consume_phase;
} comp_v11_diag_record_fault_t;
bool comp_v11_diag_console_emit_record_fault(const comp_v11_diag_record_fault_t *,
                                            comp_v11_diag_write_fn_t,void *context);
/* Existing engine counters, emitted only under the normal safe-output gate.
 * Queue slots count10ms PCM blocks; pending PCM/encoded/storage work are
 * separate. No time/latency or dropped-sample count is inferred from packets. */
typedef struct {
    uint32_t token,pcm_blocks,encoded_packets,durable_bytes,queue_peak,overflows,budget_failures;
    uint16_t pcm_fill,stage_bytes;
    uint8_t state,queue_depth,queue_slots,writer_phase;
    bool engine_bound,microphone_active;
} comp_v11_diag_record_queue_t;
bool comp_v11_diag_console_emit_record_queue(const comp_v11_diag_record_queue_t *,
                                            comp_v11_diag_write_fn_t,void *context);
/* Decision-time reason mask for a rejected wired PAIR. Bits0..13 follow
 * mic capture, playback, battery, transfer, storage, update, bond NVM,
 * active playback, running mic, prepare/start/command/capture/stop.
 * Bit31 means missing activity. Screen BUSY/maintenance and UI are not
 * pairing blockers. The mask and admission use the same predicate. */
uint32_t comp_v11_diag_console_pairing_blockers(const comp_v11_diag_activity_t *activity);
/* A short physical service command may run during an asynchronous screen
 * wait. Capture, storage, transport, playback and update still reject it. */
bool comp_v11_diag_console_pairing_safe(const comp_v11_diag_activity_t *activity);
void comp_v11_diag_console_emit(comp_v11_diag_console_t *console,
                                const comp_v11_diag_snapshot_t *snapshot,
                                comp_v11_diag_reason_t reason,
                                comp_v11_diag_write_fn_t write,
                                void *context);

#endif
