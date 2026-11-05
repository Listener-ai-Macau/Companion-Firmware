#ifndef COMPANION_V11_BATTERY_ADC_H
#define COMPANION_V11_BATTERY_ADC_H

#include "wba_power_monitor.h"

typedef enum {
    COMP_V11_ADC_OK = 0, COMP_V11_ADC_INIT, COMP_V11_ADC_CALIBRATION,
    COMP_V11_ADC_CHANNEL, COMP_V11_ADC_CONVERSION, COMP_V11_ADC_TIMEOUT,
    COMP_V11_ADC_REFERENCE_RANGE, COMP_V11_ADC_UNQUALIFIED
} comp_v11_battery_adc_error_t;

typedef struct {
    uint32_t reference_measurements, reference_ms, battery_measurements, failures;
    uint16_t reference_raw, factory_raw, reference_mv, battery_raw;
    uint16_t reference_min_mv, reference_max_mv;
    uint32_t battery_ms;
    uint16_t battery_input_mv;
    uint8_t error;
    bool reference_valid, battery_input_valid, battery_saturated;
    /* Retain the actual first failure across later successful conversions.
     * These bytes occupy the former tail padding, not another log buffer. */
    uint8_t first_error, first_phase;
    /* First wall-time timeout: status is sampled once before ADC4 reset.
     * ready: 0=not applicable, 1=not ready, 2=ready at observation. */
    uint32_t timeout_at_ms, timeout_elapsed_ms, timeout_service_gap_ms;
    uint8_t timeout_phase, timeout_ready, timeout_valid;
    uint8_t gate_observation; /* Last enable readback; uses former tail padding. */
} comp_v11_battery_adc_stats_t;
_Static_assert(sizeof(comp_v11_battery_adc_stats_t)<=56u,"ADC timeout evidence budget");

/* Fault bit is current health; counters retain historical failures.  Do not
 * clear on begin: begin clears the error before conversion is complete.
 * A configured external path needs its own completed, post-reference sample.
 * Gate faults clear only after a qualified gated sample and gate-off;
 * sample faults clear only on a new valid external sample, never VREF alone.  This never qualifies cell voltage or SOC. */
static inline bool comp_v11_battery_active_fault(bool previous,
    const comp_v11_battery_adc_stats_t *a,const comp_wba_power_monitor_t *m,bool adc_busy)
{
    if (!a || !m) return previous;
    if (m->sample_fault || m->gate_fault || a->error != COMP_V11_ADC_OK)
        return true;
    if (!previous || (!a->failures && !m->sample_errors && !m->gate_errors) || adc_busy || !a->reference_valid ||
        !a->reference_measurements || m->gate_may_be_on ||
        (m->profile.divider_verified && !m->sampling_enabled)) return previous;
    if (m->sampling_enabled) {
        if (!a->battery_input_valid || !a->battery_measurements ||
            (int32_t)(a->battery_ms-a->reference_ms)<0 ||
            (!m->raw_diagnostic && !m->value.voltage_valid)) return previous;
    }
    return false;
}

/* One foreground ADC owner. Internal-reference mode never selects PA5 and
 * requires the caller to keep the external divider switched off. External
 * mode additionally requires an electrically qualified safe profile. */
/* begin/read each advance a bounded step: regulator, calibration and ADC
 * ready waits yield to foreground audio. cancel resets only owned ADC4 and
 * never waits for a conversion. Wall timeout includes deferred audio slots. */
bool comp_v11_battery_adc_begin(const comp_wba_power_profile_t *profile,
                               bool external_battery, uint32_t now);
/* Engineering observation still requires a verified divider whose maximum
 * input fits the ADC range. It never qualifies cell voltage, SOC or OTA. */
bool comp_v11_battery_adc_begin_raw(const comp_wba_power_profile_t *profile,uint32_t now);
comp_wba_adc_result_t comp_v11_battery_adc_read(uint16_t *raw, uint32_t now);
void comp_v11_battery_adc_cancel(void);
bool comp_v11_battery_adc_busy(void);
/* Temporary nominal-divider estimate only; no production qualification. */
bool comp_v11_battery_adc_estimate_ready(uint32_t now);
uint16_t comp_v11_battery_adc_cell_estimate(uint32_t now);
const comp_v11_battery_adc_stats_t *comp_v11_battery_adc_stats(void);
void comp_v11_battery_adc_note_gate(uint8_t observation);

#endif
