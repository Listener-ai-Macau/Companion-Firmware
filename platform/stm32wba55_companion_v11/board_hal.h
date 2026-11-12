#ifndef COMPANION_V11_BOARD_HAL_H
#define COMPANION_V11_BOARD_HAL_H
#ifndef COMPANION_WBA_SCREEN_ENABLED
#define COMPANION_WBA_SCREEN_ENABLED 1
#endif
#include "stm32wbaxx_hal.h"
#include "companion_v11_board.h"
#include "lsm6dso.h"
#include "motion_events.h"
#include "speaker_playback.h"
#include "spi_nor_stm32wba.h"
#include "companion_v11_services.h"
#include "power_policy.h"
#include "touch_target_stm32wba_ft6336.h"
#include "microphone_hal.h"
#include "companion_recording_audio_profile.h"
#include "ssd1681_wba.h"
#include "wake_events.h"
#include "wba_button.h"
#if defined(COMPANION_WBA_EXPERIMENTAL_STOP1) && COMPANION_WBA_EXPERIMENTAL_STOP1
bool comp_v11_hal_debug_stop_available(void);
bool comp_v11_hal_debug_stop_arm(void);
void comp_v11_hal_debug_stop_disarm(void);
bool comp_v11_hal_debug_stop_rx_pending(void);
#endif
#include "wba_power_monitor.h"

#ifndef COMP_V11_PANEL_EXCLUSIVE_SPI
#define COMP_V11_PANEL_EXCLUSIVE_SPI 0
#endif
#ifndef COMP_V11_PANEL_DEFER_IMU_START
#define COMP_V11_PANEL_DEFER_IMU_START 0
#endif
#ifndef COMP_V11_SHARED_SPI_GPIO
#define COMP_V11_SHARED_SPI_GPIO 0
#endif
#if COMP_V11_SHARED_SPI_GPIO && !COMP_V11_PANEL_SOFTWARE_SPI
#error "Shared GPIO SPI requires the panel software transport"
#endif
#ifndef COMP_V11_PANEL_ISOLATION_REFRESHES
#define COMP_V11_PANEL_ISOLATION_REFRESHES 1u
#endif
#define COMP_V11_PANEL_ISOLATION_TIMEOUT_MS 20000u
#if COMP_V11_PANEL_DEFER_IMU_START && (!COMP_V11_PANEL_EXCLUSIVE_SPI || !COMP_V11_PANEL_SOFTWARE_SPI)
#error "Panel startup isolation requires exclusive software SPI"
#endif

/* Public state for product-task integration and SWD inspection. Touch IRQs
 * transfer bytes only; decoding and product state mutation stay foreground. */
typedef struct {
    comp_tca6408_t io;
    comp_v11_power_t display_power;
    comp_lsm6dso_t imu;
    comp_imu_sample_t imu_sample;
    comp_motion_events_t motion;
    comp_speaker_t speaker;
    companion_spi_nor_stm32wba_t nor;
    companion_v1_features_t features;
    comp_v11_services_t services;
    comp_power_policy_t power;
    comp_wba_power_monitor_t power_monitor;
    companion_touch_ft6336_stm32wba_t touch;
    comp_ft6336_touch_sample_t touch_sample;
    comp_v11_microphone_hal_t microphone;
    comp_ssd1681_wba_t panel;
    comp_v11_wake_events_t wake_events;
    comp_ssd1681_wba_reset_fn_t panel_reset;
    void *panel_reset_context;
    comp_wba_pdm_pcm_frame_fn_t pcm_sink;
    void *pcm_sink_context;
    /* Latest PCM already belongs to microphone.processing.pcm_frame. */
    uint32_t pcm_frames, microphone_max_poll_ms, motion_event_ms;
    uint8_t motion_event_flags;
    uint32_t faults, imu_poll_ms, input_poll_ms, sample_events;
    uint32_t key_wake_events, key_wake_last_ms;
    bool key_wake_pending;
    uint8_t expander_inputs, touch_chip_id;
    bool audio_clock_ready, lse_ready, speaker_ready, playback_active, touch_ack, touch_attempted, rng_ready, touch_stop_read;
    bool wake_irq_ready, idle_peripherals, power_sampling_inhibited;
    uint32_t touch_retry_ms, touch_retry_count, touch_i2c_error;
    uint8_t touch_init_stage, touch_i2c_status, touch_read_leg;
    uint32_t touch_last_contact_ms, touch_down_count;
    uint16_t touch_last_x, touch_last_y;
    uint32_t touch_reset_count;
    uint8_t touch_reset_phase;
    bool input_taps_requested; /* Desktop undo only; shared IMU, no second driver. */
    bool input_pointer_requested;
    /* Cached from ordinary expander input reads, including the physical P1
     * reset output. This is not the translated JP3-side voltage. */
    uint8_t expander_raw_inputs;
    bool expander_input_valid;
    uint8_t touch_scan_next, touch_scan_count, touch_scan_errors;
    uint32_t touch_scan_ack[4];
} comp_v11_hal_t;
enum {
    COMP_V11_FAULT_CLOCK = 1u, COMP_V11_FAULT_IO = 2u,
    COMP_V11_FAULT_IMU = 4u, COMP_V11_FAULT_NOR = 8u,
    COMP_V11_FAULT_AUDIO = 16u, COMP_V11_FAULT_TOUCH = 32u, COMP_V11_FAULT_LSE = 64u,
    COMP_V11_FAULT_MICROPHONE = 128u, COMP_V11_FAULT_PANEL = 256u,
    COMP_V11_FAULT_BATTERY = 512u,
    /* Current unconfirmed shutdown; AUDIO remains sticky after recovery. */
    COMP_V11_FAULT_SPEAKER_SHUTDOWN = 1024u
};
bool comp_v11_hal_init(comp_v11_hal_t *board);
/* End the finite startup NOR progress-watchdog window before BLE/main-loop
 * operation. Does not skip journal blank checks or change Flash contents. */
void comp_v11_hal_storage_init_complete(void);
void comp_v11_hal_poll(comp_v11_hal_t *board);
/* Foreground audio progress without polling shared display/input buses. */
void comp_v11_hal_speaker_poll(comp_v11_hal_t *board);
/* Explicit idle SOUND diagnosis only. Observe expander before/after enable
 * and the first nonzero PCM block; report after playback has stopped. Does
 * not change volume, clocks, GPIO, amplifier policy or panel transactions. */
bool comp_v11_hal_speaker_diagnostic_arm(comp_v11_hal_t *board);
void comp_v11_hal_speaker_diagnostic_report(comp_v11_hal_t *board);
void comp_v11_hal_log(const char *message);
/* Poll one byte from JP6 RX without waiting. This is observation-only and is
 * deliberately not a control/bootloader channel. */
bool comp_v11_hal_debug_read(uint8_t *byte);
bool comp_v11_hal_debug_write(const char *message);
bool comp_v11_hal_key_pressed(void);
/* Nonblocking; missing entropy holds the current expression family. */
bool comp_v11_hal_random_u32(comp_v11_hal_t *board,uint32_t *value);
bool comp_v11_hal_device_uid(uint8_t uid[12]);
/* Before START only; voice0 may use the explicit measured build candidate,
 * meeting1 stays original LEFT. Running/invalid changes refuse atomically. */
bool comp_v11_hal_microphone_profile(comp_v11_hal_t *board,uint8_t profile,bool allow_directional);
/* Pure selected-processing snapshot; no serial, ADC or storage access. */
bool comp_v11_hal_microphone_audio_profile(const comp_v11_hal_t *,uint8_t,comp_rec_audio_profile_t *);
bool comp_v11_hal_microphone_enable(comp_v11_hal_t *board, bool enabled);
/* Explicit probe build only: finite pair correlation from last ordinary take.
 * Caller must already satisfy the normal diagnostic idle gate. No audio start. */
void comp_v11_hal_dual_mic_report(const comp_v11_hal_t *board,uint32_t record_token);
#if COMPANION_WBA_DUAL_PAIR_CAPTURE
/* Single foreground observer lease; bind/retire only with the DMA stopped.
 * NULL retirement requires the matching context; no observer can be stolen. */
bool comp_v11_hal_set_pair_sink(comp_v11_hal_t *,comp_wba_pdm_pair_frame_fn_t,void *);
#endif
/* Reduce sensor power only after the product runtime has committed its
 * low-power surface. Pickup remains available through accel-only sampling. */
bool comp_v11_hal_set_idle_peripherals(comp_v11_hal_t *board, bool idle);
/* Engineering qualification API, not a BLE command. Call before audio starts.
 * Default 68K:68K / 1.8V profile is deliberately NOT qualified for sampling. */
bool comp_v11_hal_configure_power(comp_v11_hal_t *, const comp_wba_power_profile_t *);
/* Set before capture starts. NULL retains the latest frame in diagnostic RAM;
 * a product sink must copy into its codec=3 PCM ring and signal backpressure. */
bool comp_v11_hal_set_pcm_sink(comp_v11_hal_t *board, comp_wba_pdm_pcm_frame_fn_t sink, void *context);
/* Bind only after the actual RESET control endpoint is established and display
 * power is READY. All panel starts/polls and IMU accesses share this foreground
 * actor; a future RTOS port must retain one SPI owner. NULL disables the panel.
 * NULL disables hardware-reset mode, never inventing a successful refresh. */
bool comp_v11_hal_bind_panel_reset(comp_v11_hal_t *board,
                                    comp_ssd1681_wba_reset_fn_t reset, void *context);
/* Current assembled-board configuration: 3V switch disabled, no RESET IO.
 * This enables a bounded software-reset attempt, not physical qualification.
 * The panel must stay powered; deep sleep cannot be exited in this mode. */
bool comp_v11_hal_bind_panel_software_reset(comp_v11_hal_t *board);
/* Panel transactions use the same owner as IMU; caller must provide a known
 * panel controller/reset sequence before using these lower-level operations. */
bool comp_v11_hal_panel_transfer(bool data, const uint8_t *bytes, uint16_t size);
bool comp_v11_hal_panel_busy(void);
bool comp_v11_hal_take_key_wake(comp_v11_hal_t *board);
comp_wba_button_edges_t comp_v11_hal_take_key_edges(comp_v11_hal_t *board);
/* Engineering software-SPI build only: one foreground idle audit after a
 * complete full frame. Reads status/options and both RAM planes; no display
 * activation, reset, image write, NOR command or audio is issued. */
bool comp_v11_hal_panel_audit(const uint8_t *expected, uint16_t size);
/* Opt-in failure observation only; never qualifies a frame as visible. */
void comp_v11_hal_panel_failure_diagnostic(comp_v11_hal_t *board);
bool comp_v11_hal_touch_read(uint8_t addr, uint8_t reg, uint8_t *data, uint16_t size);
/* Existing safe diagnostic output path only; reads cached state/GPIO levels,
 * does not send I2C commands or reset the touch/display. */
bool comp_v11_hal_touch_diagnostic(const comp_v11_hal_t *board);
uint32_t comp_v11_hal_nor_sck_hz(void);
/* On-demand capture failure localization. No UART or radio I/O in the measured
 * path; latest worst full HAL call is retained with contiguous phase times.
 * order: speaker, PDM, panel, IMU, touch completion, inputs, power, statuses. */
#include "companion_codec_profile.h"
#define COMP_V11_CAPTURE_HAL_PHASES 8u
typedef struct {
    uint32_t calls,peak_total_ms;
    uint32_t peak_ms[COMP_V11_CAPTURE_HAL_PHASES];
    uint32_t worst_ms[COMP_V11_CAPTURE_HAL_PHASES];
} comp_v11_capture_hal_timing_t;
const comp_v11_capture_hal_timing_t *comp_v11_hal_capture_timing(void);

bool comp_v11_hal_touch_pending(void);
#endif
