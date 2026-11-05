#ifndef COMPANION_WBA_POWER_MONITOR_H
#define COMPANION_WBA_POWER_MONITOR_H
#include <stdbool.h>
#include <stdint.h>

/* Wall time includes yields to the10ms capture owner; no polling call may
 * wait this long on the CPU. Shared by the target ADC and monitor timeout. */
#define COMP_WBA_BATTERY_TRANSACTION_MS 250u

typedef enum { COMP_WBA_POWER_DEFER, COMP_WBA_POWER_SERVICE, COMP_WBA_POWER_CANCEL } comp_wba_power_poll_action_t;
/* A missed audio slot defers the current conversion; only a real operation
 * exclusion cancels it. Repeated false/cancel would starve every ADC sample. */
static inline comp_wba_power_poll_action_t comp_wba_power_poll_action(bool excluded,
    bool capturing,bool dma_window,uint32_t foreground_ms)
{
    if(excluded)return COMP_WBA_POWER_CANCEL;
    if(capturing && (!dma_window || foreground_ms>1u))return COMP_WBA_POWER_DEFER;
    return COMP_WBA_POWER_SERVICE;
}

/* BQ25170 PG/STAT are open drain. A high STAT is NOT proof of full charge.
 * No cell chemistry, divider rework, pullup or ADC reference is assumed. */
typedef enum {
    COMP_WBA_CHARGE_UNKNOWN, COMP_WBA_CHARGE_CHARGING,
    COMP_WBA_CHARGE_POWERED_IDLE, COMP_WBA_CHARGE_DISCHARGING,
    COMP_WBA_CHARGE_FAULT
} comp_wba_charge_state_t;
typedef struct { uint16_t millivolts; uint8_t percent; } comp_wba_soc_point_t;
typedef struct {
    uint32_t top_ohm, bottom_ohm;
    uint16_t reference_mv, reference_min_mv, maximum_battery_mv;
    uint16_t minimum_battery_mv, minimum_update_mv, adc_full_scale;
    /* Optional measured cell curve, ascending in voltage AND percentage.
     * It and this profile must outlive the monitor; no guessed stock curve. */
    const comp_wba_soc_point_t *soc_points;
    uint8_t soc_point_count;
    bool divider_verified, reference_verified, charger_pullups_verified;
    /* Explicit measured end-of-recording reserve and recovery hysteresis.
     * Zero/unqualified defaults never turn a display estimate into protection. */
    uint16_t recording_stop_mv, recording_resume_mv;
    bool recording_limits_verified;
} comp_wba_power_profile_t;
typedef enum { COMP_WBA_ADC_PENDING, COMP_WBA_ADC_READY, COMP_WBA_ADC_ERROR } comp_wba_adc_result_t;
typedef struct {
    bool (*gate)(void *, bool);
    bool (*start)(void *);
    comp_wba_adc_result_t (*read)(void *, uint16_t *);
    void (*cancel)(void *);
    void *context;
} comp_wba_power_ports_t;
typedef struct {
    uint16_t millivolts;
    uint8_t percent, charge_state;
    bool voltage_valid, percent_valid, charger_valid, charger_present;
} comp_wba_power_snapshot_t;
typedef enum { COMP_WBA_BAT_IDLE, COMP_WBA_BAT_SETTLE, COMP_WBA_BAT_CONVERT, COMP_WBA_BAT_CLEANUP } comp_wba_battery_phase_t;
typedef struct {
    comp_wba_power_profile_t profile;
    comp_wba_power_ports_t ports;
    comp_wba_power_snapshot_t value;
    uint32_t adc_since_ms, next_sample_ms, voltage_ms;
    uint32_t input_ms, pg_since_ms, stat_since_ms, stat_edge_ms;
    uint32_t sample_errors, gate_errors;
    uint8_t blink_edges;
    comp_wba_battery_phase_t phase;
    bool sampling_enabled, raw_diagnostic, input_seen, pg_high, stat_high, gate_may_be_on, capture_gate;
    /* Current external-sample health; sample_errors remains historical. */
    bool sample_fault;
    /* Gate recovery requires a later qualified on/sample/off cycle. */
    bool gate_fault, gate_sample_verified;
    uint32_t recording_sample_ms;
    uint8_t recording_low_samples, recording_recovery_samples;
    bool recording_sample_seen, recording_power_blocked;
} comp_wba_power_monitor_t;
/* Input freshness remains 100 ms. When charger inputs are qualified, give
 * recording-mode polling enough margin for ordinary scheduler jitter so the
 * 120 ms PG and 2 s STAT debounce can converge. Unqualified boards retain
 * the existing low-overhead cadence and never report a charger state. */
static inline uint32_t comp_wba_power_monitor_input_period_ms(
    const comp_wba_power_monitor_t *m, bool recording, bool touch_active)
{
    if (!recording || touch_active) return 20u;
    return m && m->profile.charger_pullups_verified ? 50u : 100u;
}
enum {
    COMP_WBA_OTA_POWER_UNKNOWN = 1u << 2,
    COMP_WBA_OTA_POWER_LOW = 1u << 3,
    COMP_WBA_OTA_CHARGER_FAULT = 1u << 4
};
bool comp_wba_power_profile_safe(const comp_wba_power_profile_t *);
void comp_wba_power_monitor_init(comp_wba_power_monitor_t *, const comp_wba_power_profile_t *,
                                 const comp_wba_power_ports_t *, uint32_t now);
/* Explicit engineering opt-in: reuse gated sampling without treating the
 * raw ADC observation as qualified cell voltage, SOC or OTA power. The
 * verified physical divider must keep the maximum battery voltage within
 * the ADC conversion range. GPIO FT tolerance does not qualify an active ADC. */
bool comp_wba_power_monitor_enable_raw(comp_wba_power_monitor_t *);
/* Called for each NEW TCA input sample, never from an interrupt. PG/STAT
 * parameters are the physical HIGH levels, not logical charging flags. */
void comp_wba_power_monitor_inputs(comp_wba_power_monitor_t *, bool valid,
                                   bool pg_high, bool stat_high, uint32_t now);
/* At most one gate/ADC operation per call; settles without HAL_Delay.
 * Audio/preparation can deny sampling; cleanup still shuts the divider off. */
void comp_wba_power_monitor_poll(comp_wba_power_monitor_t *, bool sampling_allowed, uint32_t now);
comp_wba_power_snapshot_t comp_wba_power_monitor_snapshot(const comp_wba_power_monitor_t *, uint32_t now);
bool comp_wba_power_monitor_busy(const comp_wba_power_monitor_t *);
bool comp_wba_power_recording_limits_safe(const comp_wba_power_profile_t *);
/* Only distinct, fresh, qualified cell observations advance this latch.
 * No I/O, counter reset on an unknown gap; an established block survives it.
 * Two samples at the existing 5s cadence need a measured shutdown reserve. */
void comp_wba_power_monitor_recording_guard(comp_wba_power_monitor_t *,uint32_t now);
bool comp_wba_power_monitor_recording_allowed(const comp_wba_power_monitor_t *,uint32_t now);
/* Acquire/release outside actual microphone deadlines. Electrically qualified
 * capture keeps a single divider lease so its sample steps never write I2C.
 * Unknown/raw profiles close pending sample gates and retain no capture lease. */
bool comp_wba_power_monitor_prepare_capture(comp_wba_power_monitor_t *,uint32_t now);
void comp_wba_power_monitor_release_capture(comp_wba_power_monitor_t *,uint32_t now);
uint16_t comp_wba_power_monitor_ota_blockers(const comp_wba_power_monitor_t *, uint32_t now);
#endif
