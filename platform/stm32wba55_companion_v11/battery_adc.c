#include "battery_adc.h"
#include "companion_v11_board.h"
#include "stm32wbaxx_hal.h"
#include "stm32wbaxx_ll_adc.h"
#include <string.h>

#define REFERENCE_SAMPLES 4u
#define ANALOG_SWITCH_MASK (SYSCFG_CFGR1_BOOSTEN | SYSCFG_CFGR1_ANASWVDD)

typedef enum { ADC_IDLE, ADC_REGULATOR_WAIT, ADC_CALIBRATION_WAIT,
               ADC_REFERENCE_SETTLE, ADC_ENABLE_WAIT, ADC_REFERENCE_CONVERT,
               ADC_BATTERY_CONFIGURE, ADC_BATTERY_CONVERT,
               ADC_BATTERY_DISABLE_WAIT, ADC_BATTERY_CHANNEL_WAIT,
               ADC_BATTERY_ENABLE_WAIT } adc_phase_t;
static ADC_HandleTypeDef adc;
static comp_v11_battery_adc_stats_t stats;
static adc_phase_t phase;
static uint32_t started_ms, last_service_ms, reference_enabled_ms, reference_sum, switch_before;
static uint8_t reference_count;
static uint16_t minimum_reference_mv;
static bool external_requested, clock_owned;

void comp_v11_battery_adc_cancel(void)
{
    if (clock_owned) {
        /* Sole ADC4 owner: a peripheral reset aborts calibration/conversion
         * without HAL's stop/disable busy loops. SAI/DMA and other peripherals
         * are untouched. Restore the analog-switch setting we borrowed. */
        __HAL_RCC_ADC4_FORCE_RESET();
        __HAL_RCC_ADC4_RELEASE_RESET();
        __HAL_RCC_ADC4_CLK_DISABLE();
        MODIFY_REG(SYSCFG->CFGR1, ANALOG_SWITCH_MASK, switch_before);
    }
    clock_owned = false;
    phase = ADC_IDLE;
}

static bool fail(comp_v11_battery_adc_error_t error)
{
    if (!stats.failures) { stats.first_error=(uint8_t)error; stats.first_phase=(uint8_t)phase; }
    stats.error = (uint8_t)error;
    stats.failures++;
    if (external_requested) stats.battery_input_valid=false;
    comp_v11_battery_adc_cancel();
    return false;
}

static bool channel(uint32_t selected)
{
    ADC_ChannelConfTypeDef config = {0};
    config.Channel = selected;
    config.Rank = ADC_REGULAR_RANK_1;
    config.SamplingTime = ADC_SAMPLINGTIME_COMMON_1;
    return HAL_ADC_ConfigChannel(&adc, &config) == HAL_OK;
}

static bool begin(const comp_wba_power_profile_t *profile,
                  bool external_battery, bool raw_diagnostic, uint32_t now)
{
    if (phase != ADC_IDLE || __get_IPSR() != 0u) return false;
    /* Even a request rejected by qualification belongs to this request,
     * not to the previous reference-only conversion. A failed external
     * attempt invalidates its prior external sample. */
    external_requested = external_battery;
#if COMPANION_WBA_BATTERY_LINEAR_ESTIMATE
    bool estimate=external_battery && raw_diagnostic;
    if (estimate && (!profile || profile->top_ohm!=100000u ||
        profile->bottom_ohm!=68000u || profile->maximum_battery_mv!=4350u ||
        profile->adc_full_scale!=4095u || !comp_v11_battery_adc_estimate_ready(now)))
        return fail(COMP_V11_ADC_UNQUALIFIED);
    if (!estimate && external_battery && (!profile || !profile->divider_verified ||
#else
    if (external_battery && (!profile || !profile->divider_verified ||
#endif
        profile->adc_full_scale != 4095u ||
        !comp_v11_battery_divider_safe(profile->top_ohm,profile->bottom_ohm,
            profile->reference_min_mv,profile->maximum_battery_mv)))
        return fail(COMP_V11_ADC_UNQUALIFIED);
    if (external_battery && !raw_diagnostic &&
        (!comp_wba_power_profile_safe(profile) || profile->adc_full_scale != 4095u))
        return fail(COMP_V11_ADC_UNQUALIFIED);
    /* Keep the last fresh observation while the next conversion is pending.
     * Failed/saturated samples invalidate it, rather than blinking unknown
     * for a few milliseconds every five seconds. */
    stats.reference_valid = false;
    stats.error = COMP_V11_ADC_OK;
    minimum_reference_mv = external_battery ? profile->reference_min_mv : 1620u;
#if COMPANION_WBA_BATTERY_LINEAR_ESTIMATE
    /* 4350*68/168=1761mV nominal; 20mV working headroom, rounded up.
     * This is an engineering estimate policy, not a tolerance qualification.
     * Recheck the reference during this very conversion before selecting PA5. */
    if (estimate) minimum_reference_mv=1782u;
#endif
    reference_count = 0u;
    reference_sum = 0u;
    /* The family factory halfword is at an odd address. Byte reads also work
     * when the core enables unaligned-access trapping. The calibration
     * voltage comes from the pinned CubeWBA definition, never a guessed rail. */
    const volatile uint8_t *factory = (const volatile uint8_t *)VREFINT_CAL_ADDR;
    stats.factory_raw = (uint16_t)((uint16_t)factory[0] |
                                  (uint16_t)((uint16_t)factory[1] << 8u));
    if (stats.factory_raw == 0u || stats.factory_raw >= 4095u)
        return fail(COMP_V11_ADC_CALIBRATION);
    uint32_t kernel_hz = HAL_RCC_GetSysClockFreq();
    if (kernel_hz / 4u < 140000u || kernel_hz / 4u > 55000000u)
        return fail(COMP_V11_ADC_INIT);
    __HAL_RCC_SYSCFG_CLK_ENABLE();
    switch_before = SYSCFG->CFGR1 & ANALOG_SWITCH_MASK;
    /* This board's VDD/VDDA rail is 1.8 V. ST requires the analog-switch
     * booster below 2.4 V. Restore the preceding setting when the ADC stops. */
    HAL_SYSCFG_EnableIOAnalogSwitchBooster();
    __HAL_RCC_ADC_CONFIG(RCC_ADCCLKSOURCE_SYSCLK);
    __HAL_RCC_ADC4_CLK_ENABLE();
    clock_owned = true;
    memset(&adc, 0, sizeof(adc));
    adc.Instance = ADC4;
    adc.Init.ClockPrescaler = ADC_CLOCK_ASYNC_DIV4;
    adc.Init.Resolution = ADC_RESOLUTION_12B;
    adc.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    adc.Init.ScanConvMode = ADC_SCAN_DISABLE;
    adc.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
    adc.Init.NbrOfConversion = 1u;
    adc.Init.ExternalTrigConv = ADC_SOFTWARE_START;
    adc.Init.Overrun = ADC_OVR_DATA_PRESERVED;
    adc.Init.SamplingTimeCommon1 = ADC_SAMPLETIME_814CYCLES_5;
    adc.Init.SamplingTimeCommon2 = ADC_SAMPLETIME_814CYCLES_5;
    adc.Init.TriggerFrequencyMode = ADC_TRIGGER_FREQ_LOW;
    started_ms = now;
    last_service_ms = now;
    /* Do not enter HAL_Init's LDO wait or Calibration_Start's spin loop in a
     * recording slice. The next foreground steps observe readiness once. */
    LL_ADC_ClearFlag_LDORDY(ADC4);
    LL_ADC_EnableInternalRegulator(ADC4);
    phase = ADC_REGULATOR_WAIT;
    return true;
}

bool comp_v11_battery_adc_begin(const comp_wba_power_profile_t *profile,
                               bool external_battery, uint32_t now)
{ return begin(profile, external_battery, false, now); }

bool comp_v11_battery_adc_begin_raw(const comp_wba_power_profile_t *profile,uint32_t now)
{ return begin(profile, true, true, now); }

comp_wba_adc_result_t comp_v11_battery_adc_read(uint16_t *raw, uint32_t now)
{
    if (phase == ADC_IDLE || raw == NULL) return COMP_WBA_ADC_ERROR;
    if (now - started_ms >= COMP_WBA_BATTERY_TRANSACTION_MS) {
        /* Store only the first actual timeout. A ready flag at this late
         * observation does not establish when hardware became ready. */
        if (!stats.timeout_valid) {
            stats.timeout_at_ms = now;
            stats.timeout_elapsed_ms = now - started_ms;
            stats.timeout_service_gap_ms = now - last_service_ms;
            stats.timeout_phase = (uint8_t)phase;
            stats.timeout_ready = (phase == ADC_ENABLE_WAIT && clock_owned) ?
                (LL_ADC_IsActiveFlag_ADRDY(ADC4) ? 2u : 1u) : 0u;
            stats.timeout_valid = 1u;
        }
        (void)fail(COMP_V11_ADC_TIMEOUT);
        return COMP_WBA_ADC_ERROR;
    }
    last_service_ms = now;
    if (phase == ADC_REGULATOR_WAIT) {
        if (!LL_ADC_IsActiveFlag_LDORDY(ADC4)) return COMP_WBA_ADC_PENDING;
        if (!LL_ADC_IsInternalRegulatorEnabled(ADC4) || HAL_ADC_Init(&adc) != HAL_OK) {
            (void)fail(COMP_V11_ADC_INIT);return COMP_WBA_ADC_ERROR;
        }
        /* Init uses no DMA/auto-off. Keep them disabled as required by ST's
         * calibration sequence; do not run its synchronous wait. */
        CLEAR_BIT(ADC4->CFGR1,ADC_CFGR1_DMAEN|ADC_CFGR1_DMACFG);
        CLEAR_BIT(ADC4->PWRR,ADC_PWRR_AUTOFF);
        LL_ADC_StartCalibration(ADC4);
        phase=ADC_CALIBRATION_WAIT;return COMP_WBA_ADC_PENDING;
    }
    if (phase == ADC_CALIBRATION_WAIT) {
        if (LL_ADC_IsCalibrationOnGoing(ADC4)) return COMP_WBA_ADC_PENDING;
        if (!channel(ADC_CHANNEL_VREFINT)) {
            (void)fail(COMP_V11_ADC_CHANNEL);return COMP_WBA_ADC_ERROR;
        }
        reference_enabled_ms=now;phase=ADC_REFERENCE_SETTLE;
        return COMP_WBA_ADC_PENDING;
    }
    if (phase == ADC_REFERENCE_SETTLE) {
        /* Two tick boundaries guarantee at least 1 ms, exceeding the 12 us
         * VREFINT settling time even across a tick edge. Yield, never spin. */
        if (now - reference_enabled_ms < 2u) return COMP_WBA_ADC_PENDING;
        LL_ADC_ClearFlag_ADRDY(ADC4);
        LL_ADC_Enable(ADC4);
        phase = ADC_ENABLE_WAIT;
        return COMP_WBA_ADC_PENDING;
    }
    if (phase == ADC_ENABLE_WAIT) {
        if (!LL_ADC_IsActiveFlag_ADRDY(ADC4)) return COMP_WBA_ADC_PENDING;
        LL_ADC_ClearFlag_EOC(ADC4);LL_ADC_ClearFlag_EOS(ADC4);LL_ADC_ClearFlag_OVR(ADC4);
        LL_ADC_REG_StartConversion(ADC4);
        phase=ADC_REFERENCE_CONVERT;return COMP_WBA_ADC_PENDING;
    }
    if (phase == ADC_BATTERY_CONFIGURE) {
        /* Retain the previously working stop/configure/enable order at the
         * internal-to-external mux boundary, with no HAL busy waits. */
        LL_ADC_Disable(ADC4);
        phase=ADC_BATTERY_DISABLE_WAIT;
        return COMP_WBA_ADC_PENDING;
    }
    if (phase == ADC_BATTERY_DISABLE_WAIT) {
        if(LL_ADC_IsEnabled(ADC4))return COMP_WBA_ADC_PENDING;
        if (!channel(ADC_CHANNEL_4)) {
            (void)fail(COMP_V11_ADC_CHANNEL);
            return COMP_WBA_ADC_ERROR;
        }
        phase=ADC_BATTERY_CHANNEL_WAIT;
        return COMP_WBA_ADC_PENDING;
    }
    if (phase == ADC_BATTERY_CHANNEL_WAIT) {
        /* The configuration turn has already yielded before re-enabling. */
        LL_ADC_ClearFlag_ADRDY(ADC4);
        LL_ADC_Enable(ADC4);
        phase=ADC_BATTERY_ENABLE_WAIT;
        return COMP_WBA_ADC_PENDING;
    }
    if (phase == ADC_BATTERY_ENABLE_WAIT) {
        if(!LL_ADC_IsActiveFlag_ADRDY(ADC4))return COMP_WBA_ADC_PENDING;
        LL_ADC_ClearFlag_EOC(ADC4);LL_ADC_ClearFlag_EOS(ADC4);
        LL_ADC_REG_StartConversion(ADC4);
        phase = ADC_BATTERY_CONVERT;
        return COMP_WBA_ADC_PENDING;
    }
    if (__HAL_ADC_GET_FLAG(&adc, ADC_FLAG_OVR)) {
        (void)fail(COMP_V11_ADC_CONVERSION);
        return COMP_WBA_ADC_ERROR;
    }
    if (!__HAL_ADC_GET_FLAG(&adc, ADC_FLAG_EOC)) return COMP_WBA_ADC_PENDING;
    uint16_t value=LL_ADC_REG_ReadConversionData12(ADC4);
    LL_ADC_ClearFlag_EOC(ADC4);LL_ADC_ClearFlag_EOS(ADC4);
    if (phase == ADC_REFERENCE_CONVERT) {
        if (value == 0u || value >= 4093u) {
            (void)fail(COMP_V11_ADC_REFERENCE_RANGE);
            return COMP_WBA_ADC_ERROR;
        }
        reference_sum += value;
        reference_count++;
        if (reference_count < REFERENCE_SAMPLES) {
            LL_ADC_REG_StartConversion(ADC4);
            return COMP_WBA_ADC_PENDING;
        }
        stats.reference_raw = (uint16_t)((reference_sum + REFERENCE_SAMPLES / 2u) /
                                         REFERENCE_SAMPLES);
        uint32_t reference_mv = ((uint32_t)stats.factory_raw * VREFINT_CAL_VREF +
                                stats.reference_raw / 2u) / stats.reference_raw;
        if (reference_mv < minimum_reference_mv || reference_mv > 3600u) {
            (void)fail(COMP_V11_ADC_REFERENCE_RANGE);
            return COMP_WBA_ADC_ERROR;
        }
        stats.reference_mv = (uint16_t)reference_mv;
        if (!stats.reference_measurements || reference_mv < stats.reference_min_mv)
            stats.reference_min_mv = (uint16_t)reference_mv;
        if (reference_mv > stats.reference_max_mv)
            stats.reference_max_mv = (uint16_t)reference_mv;
        stats.reference_valid = true;
        stats.reference_measurements++;
        stats.reference_ms = now;
        if (external_requested) {
            phase = ADC_BATTERY_CONFIGURE;
            return COMP_WBA_ADC_PENDING;
        }
        *raw = stats.reference_raw;
    } else {
        *raw = value;
        stats.battery_raw = value;
        stats.battery_measurements++;
        stats.battery_ms = now;
        stats.battery_saturated = value >= 4093u;
        stats.battery_input_valid = !stats.battery_saturated;
        stats.battery_input_mv = stats.battery_input_valid ?
            (uint16_t)(((uint32_t)value * stats.reference_mv + 2047u) / 4095u) : 0u;
    }
    comp_v11_battery_adc_cancel();
    return COMP_WBA_ADC_READY;
}

bool comp_v11_battery_adc_busy(void) { return phase != ADC_IDLE; }
const comp_v11_battery_adc_stats_t *comp_v11_battery_adc_stats(void) { return &stats; }
void comp_v11_battery_adc_note_gate(uint8_t observation) { stats.gate_observation=observation; }

#if COMPANION_WBA_BATTERY_LINEAR_ESTIMATE
bool comp_v11_battery_adc_estimate_ready(uint32_t now)
{
    return stats.reference_valid && now-stats.reference_ms<15000u &&
        stats.reference_mv>=1782u && stats.reference_mv<=3600u;
}
uint16_t comp_v11_battery_adc_cell_estimate(uint32_t now)
{
    if (!stats.battery_input_valid || stats.battery_saturated ||
        !stats.battery_measurements || now-stats.battery_ms>=15000u) return 0u;
    uint32_t mv=((uint32_t)stats.battery_input_mv*168u+34u)/68u;
    return mv>=2800u && mv<=4350u ? (uint16_t)mv : 0u;
}
#endif
