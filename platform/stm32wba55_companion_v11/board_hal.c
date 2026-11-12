#include "reset_witness.h"
#include "companion_cpu_stage.h"
#include "board_hal.h"
#if !COMPANION_WBA_SCREEN_ENABLED
#undef COMP_V11_PANEL_DEFER_IMU_START
#define COMP_V11_PANEL_DEFER_IMU_START 0
#endif
#include "cpu_profile_target.h"
#include "panel_gpio_timing.h"
#if defined(COMPANION_WBA_CODEC_PROFILE) && COMPANION_WBA_CODEC_PROFILE
#include "ble_micro_observation.h"
#endif
#include "panel_boot_idle.h"
#include "wba_board_power_profile.h"
#include "wba_dual_mic_probe.h"
#include "wba_microphone_profile.h"
#include "wba_microphone_profile_snapshot.h"
#if COMPANION_WBA_AUDIO_PROFILE
#include "wba_recording_audio_identity.h"
#endif
#ifndef COMPANION_WBA_DUAL_MIC_PROBE
#define COMPANION_WBA_DUAL_MIC_PROBE 0
#endif
#ifndef COMPANION_WBA_DUAL_PAIR_CAPTURE
#define COMPANION_WBA_DUAL_PAIR_CAPTURE 0
#endif
#include "battery_adc.h"
#include "spi_polling.h"
#if COMPANION_WBA_RESOURCE_PROFILE
#include "companion_wba_resource_contract.h"
#endif
#include <string.h>
#include <stdio.h>
#ifndef COMP_V11_PANEL_IDLE_CLOCK_DIVIDER
#define COMP_V11_PANEL_IDLE_CLOCK_DIVIDER 1u
#endif
#ifndef COMPANION_WBA_BATTERY_RAW_DIAGNOSTIC
#define COMPANION_WBA_BATTERY_RAW_DIAGNOSTIC 0
#endif
#ifdef COMPANION_WBA_BLE_LINKED
#include "stm32wbaxx_ll_iwdg.h"
#include "ble/ble_product.h"
#endif

#ifndef COMPANION_WBA_MICROPHONE_GAIN_Q15
#define COMPANION_WBA_MICROPHONE_GAIN_Q15 COMP_WBA_PDM_GAIN_Q15_ONE
#endif
_Static_assert(COMPANION_WBA_MICROPHONE_GAIN_Q15 > 0u &&
               COMPANION_WBA_MICROPHONE_GAIN_Q15 <= COMP_WBA_PDM_GAIN_Q15_MAX,
               "microphone gain must fit the bounded PDM processing range");

/* Pin/AF mapping checked against 2026-09-19 PDF sheets 1-4 and ST's
 * STM32WBA55CGUx.xml / GPIO-STM32WBAx_gpio_v1_0_Modes.xml. */
static I2C_HandleTypeDef i2c_io, i2c_touch;
/* Transport storage only; gesture state is committed in the foreground. */
static struct {
    uint32_t deadline_ms;
    uint8_t report[COMP_FT6336_TOUCH_REPORT_BYTES], selector;
    volatile uint8_t phase, start_status;
} touch_rx;
static SPI_HandleTypeDef spi_shared, spi_flash;
static UART_HandleTypeDef debug_uart;
static SAI_HandleTypeDef sai_speaker;
static DMA_HandleTypeDef dma_speaker;
static RNG_HandleTypeDef family_rng;
static bool battery_reference_pending;
static uint32_t battery_reference_next_ms;
static volatile uint8_t speaker_completion;
static volatile uint8_t speaker_prefilled;
static uint32_t speaker_submit_started_ms;
#define SPEAKER_SHUTDOWN_RETRY_MS 1000u
/* Each block is4ms at16kHz. A lost DMA completion must fail and release
 * playback, never hold diagnostics/display power forever or fake success. */
#define SPEAKER_DMA_DEADLINE_MS 100u
static bool spi_owned, uart_ready;
/* STOP1_UART_LEASE_BEGIN */

#if defined(COMPANION_WBA_EXPERIMENTAL_STOP1) && COMPANION_WBA_EXPERIMENTAL_STOP1
static bool debug_stop_owned;
/* WBA's RXNE wake needs no address-match setup. The pinned HAL's
 * StopModeWakeUpSourceConfig(READDATA_NONEMPTY) only cycles UE and waits
 * for REACK; doing that at boot changes the ordinary polling UART even
 * when this experiment is unarmed. Observe the initialized receiver here;
 * lease UESM/RXNEIE only inside the final masked Stop1 transaction. */
bool comp_v11_hal_debug_stop_available(void)
{ return uart_ready && (debug_uart.Instance->ISR&USART_ISR_REACK)!=0u; }
/* The WBA UART has RXNE/RXFNE wake, not the WUF/WUFIE registers present
 * on other STM32 families. Lease only its otherwise-unused IRQ. The outer
 * Stop1 critical section and SDK LPM both preserve PRIMASK=1 until after
 * clocks are restored and this lease is removed. No ISR reads the FIFO. */
void comp_v11_hal_debug_stop_disarm(void)
{
    if (!debug_stop_owned) return;
    NVIC_DisableIRQ(LPUART1_IRQn);
    CLEAR_BIT(debug_uart.Instance->CR1,USART_CR1_RXNEIE_RXFNEIE|USART_CR1_UESM);
    NVIC_ClearPendingIRQ(LPUART1_IRQn);
    debug_stop_owned=false;
}
bool comp_v11_hal_debug_stop_arm(void)
{
    const uint32_t busy=USART_ISR_BUSY|USART_ISR_RXNE_RXFNE|USART_ISR_ORE|
        USART_ISR_FE|USART_ISR_NE|USART_ISR_PE;
    if (__get_IPSR()!=0u || __get_PRIMASK()!=1u || !comp_v11_hal_debug_stop_available() ||
        debug_stop_owned || NVIC_GetEnableIRQ(LPUART1_IRQn) || NVIC_GetPendingIRQ(LPUART1_IRQn) ||
        (debug_uart.Instance->CR1&(USART_CR1_RXNEIE_RXFNEIE|USART_CR1_UESM)) ||
        !(debug_uart.Instance->ISR&USART_ISR_TC) || (debug_uart.Instance->ISR&busy)) return false;
    if (HAL_UARTEx_EnableStopMode(&debug_uart)!=HAL_OK) return false;
    debug_stop_owned=true;
    SET_BIT(debug_uart.Instance->CR1,USART_CR1_RXNEIE_RXFNEIE);
    NVIC_EnableIRQ(LPUART1_IRQn);
    __DSB();
    if (debug_uart.Instance->ISR&busy) {
        comp_v11_hal_debug_stop_disarm(); return false;
    }
    return true;
}
/* Observation only: RXNE is deliberately left for the normal poll parser. */
bool comp_v11_hal_debug_stop_rx_pending(void)
{ return debug_stop_owned && (debug_uart.Instance->ISR&USART_ISR_RXNE_RXFNE)!=0u; }
#endif
/* STOP1_UART_LEASE_END */

static bool imu_start_pending;
static comp_v11_hal_t *active_board;
static bool startup_storage_active;
static uint32_t startup_storage_started;
#if COMP_V11_PANEL_SOFTWARE_SPI
static bool panel_gpio_active, panel_gpio_reading;
static uint32_t panel_gpio_delay_clock_hz,panel_gpio_delay_waits;
#if COMP_V11_SHARED_SPI_GPIO
static bool imu_gpio_transfer(uint8_t reg, uint8_t *rx, const uint8_t *tx, size_t n);
#else
static void panel_gpio_to_hardware(void);
#endif
#endif
#if COMP_V11_PANEL_SOFTWARE_SPI && COMP_V11_PANEL_STARTUP_READBACK
static uint32_t panel_busy_rises, panel_busy_falls;
static uint32_t panel_busy_rise_ms, panel_busy_fall_ms;
static uint32_t panel_busy_bus_edges, panel_busy_quiet_edges;
static void panel_ready_observation(void *context,
                                    comp_ssd1681_wba_observe_point_t point);
#if COMP_V11_PANEL_SENSE_POWER || COMP_V11_PANEL_START_RETRY
static bool panel_read_ready_status(void *context, uint8_t *status);
#endif
#if COMP_V11_PANEL_START_RETRY
static comp_ssd1681_wba_retry_check_t panel_check_activation_retry(void *context);
#endif
static void panel_busy_trace(bool during_bus)
{
    if(!COMPANION_WBA_SCREEN_ENABLED)return;
    /* Coalesced hardware edge flags avoid an interrupt storm changing the
     * timing under investigation. Counts are sampled intervals with edges,
     * not total pulses or measured high durations. Never qualify a refresh
     * using these diagnostic flags. */
    const bool rise = __HAL_GPIO_EXTI_GET_RISING_IT(GPIO_PIN_12) != 0u;
    const bool fall = __HAL_GPIO_EXTI_GET_FALLING_IT(GPIO_PIN_12) != 0u;
    if (!rise && !fall) return;
    const uint32_t tick = HAL_GetTick();
    if (rise) { panel_busy_rises++; panel_busy_rise_ms = tick; }
    if (fall) { panel_busy_falls++; panel_busy_fall_ms = tick; }
    if (during_bus) panel_busy_bus_edges++;
    else panel_busy_quiet_edges++;
    __HAL_GPIO_EXTI_CLEAR_IT(GPIO_PIN_12);
}
#else
static inline void panel_busy_trace(bool during_bus) { (void)during_bus; }
#endif
#if COMP_V11_PANEL_PASSIVE_TRACE
static uint8_t panel_take_busy_edges(void *context,
                                    comp_ssd1681_wba_busy_edges_action_t action)
{
    (void)context;
    if (action != COMP_SSD1681_WBA_BUSY_EDGES_SAMPLE)
        CLEAR_BIT(EXTI->IMR1, GPIO_PIN_12);
    const bool rise = __HAL_GPIO_EXTI_GET_RISING_IT(GPIO_PIN_12) != 0u;
    const bool fall = __HAL_GPIO_EXTI_GET_FALLING_IT(GPIO_PIN_12) != 0u;
    /* RM0493 rev7 section 19.4/table139: IMR=0 does NOT latch RPR/FPR.
     * Keep NVIC12 disabled; unmask IMR only for an active panel transaction,
     * where the existing panel-active policy already prevents Stop1.
     * Clear only flags actually read;
     * preserve an opposite edge arriving between this read and clear. The
     * bitmask means at least one edge, not a pulse count or high duration.
     * A rising bit can veto ready; it cannot establish visible completion. */
    if (rise) __HAL_GPIO_EXTI_CLEAR_RISING_IT(GPIO_PIN_12);
    if (fall) __HAL_GPIO_EXTI_CLEAR_FALLING_IT(GPIO_PIN_12);
    if (action == COMP_SSD1681_WBA_BUSY_EDGES_ARM) {
        HAL_NVIC_ClearPendingIRQ(EXTI12_IRQn);
        SET_BIT(EXTI->IMR1, GPIO_PIN_12);
        return 0u;
    }
    if (action == COMP_SSD1681_WBA_BUSY_EDGES_STOP)
        HAL_NVIC_ClearPendingIRQ(EXTI12_IRQn);
    return (uint8_t)((rise ? 1u : 0u) | (fall ? 2u : 0u));
}
#endif
static bool panel_holds_shared_bus(const comp_v11_hal_t *b)
{
#if COMP_V11_PANEL_EXCLUSIVE_SPI
    /* Keep the IMU enabled, but defer its SPI access for the complete panel
     * transaction, including RAM packets and visible BUSY qualification.
     * Do not advance imu_poll_ms while deferred: the next released poll
     * samples immediately. Audio, BLE and I2C continue in the foreground. */
    return b != NULL && b->panel.status == COMP_SSD1681_WBA_ACTIVE;
#else
    (void)b;
    return false;
#endif
}
/* Owner: 10kHz is temporary until hardware is repaired for 100kHz. A five-byte
 * report needs about 7.2ms on the wire at 10kHz. Blocking setup is idle-only;
 * ordinary reports use IRQ transport, below audio DMA priority. */
#ifndef COMP_V11_TOUCH_I2C_TIMING
#define COMP_V11_TOUCH_I2C_TIMING 0x70215D69u
#endif
#define TOUCH_I2C_TIMEOUT_MS 12u
#define TOUCH_REPORT_DEADLINE_MS 30u
#define TOUCH_RETRY_MS 1000u

static bool battery_gate(void *context, bool enabled)
{
    comp_v11_hal_t *b=context;
    uint8_t observation=0u;
    if(!b||__get_IPSR()!=0u)return false;
    bool ok=comp_v11_battery_enable(&b->io,enabled,&observation);
    if(enabled)comp_v11_battery_adc_note_gate((uint8_t)(observation|
        (((GPIOA->MODER>>(5u*2u))&3u)<<4u)));
    return ok;
}
static bool battery_start(void *context)
{
    comp_v11_hal_t *b=context;
    if (!b || (b->microphone.running&&!b->power_monitor.capture_gate) || b->playback_active) return false;
    return b->power_monitor.raw_diagnostic ? comp_v11_battery_adc_begin_raw(&b->power_monitor.profile,HAL_GetTick()) :
        comp_v11_battery_adc_begin(&b->power_monitor.profile,true,HAL_GetTick());
}
static comp_wba_adc_result_t battery_read(void *context, uint16_t *raw)
{
    comp_v11_hal_t *b=context;
    comp_wba_adc_result_t result=comp_v11_battery_adc_read(raw,HAL_GetTick());
    const comp_v11_battery_adc_stats_t *adc=comp_v11_battery_adc_stats();
    if(result==COMP_WBA_ADC_READY && b && !b->microphone.running) {
        uint8_t input;
        if(b->io.read(b->io.context,b->io.address,0u,&input))
            comp_v11_battery_adc_note_gate((uint8_t)(adc->gate_observation|0x40u|
                ((input&COMP_V11_BATTERY_ENABLE)?0x80u:0u)));
    }
    if(result==COMP_WBA_ADC_READY && b && adc->reference_valid)
        b->power_monitor.profile.reference_mv=adc->reference_mv;
    return result;
}
static void battery_cancel(void *context)
{ (void)context; comp_v11_battery_adc_cancel(); }
static bool battery_capture_prepare(comp_v11_hal_t *b)
{
    return comp_wba_power_monitor_prepare_capture(&b->power_monitor,HAL_GetTick());
}
static void battery_capture_release(comp_v11_hal_t *b)
{
    comp_wba_power_monitor_release_capture(&b->power_monitor,HAL_GetTick());
}
bool comp_v11_hal_configure_power(comp_v11_hal_t *b, const comp_wba_power_profile_t *profile)
{
    const comp_wba_power_ports_t ports={battery_gate,battery_start,battery_read,battery_cancel,b};
    if (!b || !profile || b->microphone.running || b->playback_active ||
        comp_wba_power_monitor_busy(&b->power_monitor) || __get_IPSR()!=0u) return false;
    battery_cancel(b);
    comp_wba_power_monitor_init(&b->power_monitor,profile,&ports,HAL_GetTick());
    if (profile->adc_full_scale!=4095u)b->power_monitor.sampling_enabled=false;
#if COMPANION_WBA_BATTERY_RAW_DIAGNOSTIC
    /* Engineering mode also requires a verified, in-range physical divider.
     * FT_a GPIO tolerance does not apply to an active analog ADC input. */
    if (!b->power_monitor.sampling_enabled)
        (void)comp_wba_power_monitor_enable_raw(&b->power_monitor);
#endif
    /* Periodic internal-reference observations keep the external divider off.
     * They neither qualify unknown resistors nor unlock OTA. */
    battery_reference_pending=!b->power_monitor.sampling_enabled;
    battery_reference_next_ms=HAL_GetTick();
    if (profile->divider_verified && !b->power_monitor.sampling_enabled) b->faults|=COMP_V11_FAULT_BATTERY;
    return !b->power_monitor.gate_may_be_on &&
        (!profile->divider_verified || b->power_monitor.sampling_enabled);
}

static void battery_reference_poll(comp_v11_hal_t *b,bool allowed,uint32_t now)
{
#if COMPANION_WBA_BATTERY_LINEAR_ESTIMATE
    if(b->power_monitor.sampling_enabled && !b->power_monitor.raw_diagnostic)return;
#else
    if(b->power_monitor.sampling_enabled)return;
#endif
    if(!allowed) {
        if(comp_v11_battery_adc_busy()) {
            battery_cancel(b);
            battery_reference_pending=true;
        }
        return;
    }
    if(b->power_monitor.gate_may_be_on || comp_wba_power_monitor_busy(&b->power_monitor))return;
    if((battery_reference_pending || (int32_t)(now-battery_reference_next_ms)>=0) &&
       !comp_v11_battery_adc_busy()) {
        battery_reference_pending=false;
        battery_reference_next_ms=now+5000u;
        (void)comp_v11_battery_adc_begin(&b->power_monitor.profile,false,now);
        return;
    }
    if(comp_v11_battery_adc_busy()) {
        uint16_t internal_raw;
        (void)comp_v11_battery_adc_read(&internal_raw,now);
    }
}

/* Exactly one ADC/monitor step; the caller controls the DMA window and budget.
 * Moving an already-owned ADC ahead of optional display/IO work gives a
 * pending conversion a bounded chance to finish without starting a new one. */
static void battery_service_one_step(comp_v11_hal_t *b)
{
    bool reference_only=b->microphone.running&&!b->power_monitor.capture_gate;
#if COMPANION_WBA_BATTERY_LINEAR_ESTIMATE
    if(b->power_monitor.raw_diagnostic && b->power_monitor.phase==COMP_WBA_BAT_IDLE &&
       (comp_v11_battery_adc_busy()||!comp_v11_battery_adc_estimate_ready(HAL_GetTick())))reference_only=true;
#endif
    if(reference_only||!b->power_monitor.sampling_enabled)
        battery_reference_poll(b,true,HAL_GetTick());
    else comp_wba_power_monitor_poll(&b->power_monitor,true,HAL_GetTick());
}

static void gpio(GPIO_TypeDef *port, uint32_t pins, uint32_t mode, uint32_t pull, uint32_t af)
{
    GPIO_InitTypeDef init = {0};
    init.Pin = pins; init.Mode = mode; init.Pull = pull;
    init.Speed = GPIO_SPEED_FREQ_HIGH; init.Alternate = af;
    HAL_GPIO_Init(port, &init);
}
static bool power_clock_prepare(void)
{
    /* These HAL power routines do not enable the peripheral clock. The
     * resident boot's oscillator helper restores it to its previous state. */
    __HAL_RCC_PWR_CLK_ENABLE();
    return HAL_PWREx_ConfigSupply(PWR_SMPS_SUPPLY) == HAL_OK &&
           HAL_PWREx_ControlVoltageScaling(PWR_REGULATOR_VOLTAGE_SCALE1) == HAL_OK;
}
static bool clocks(void)
{
    RCC_OscInitTypeDef osc = {0}; RCC_ClkInitTypeDef clk = {0};
#ifdef COMPANION_WBA_BLE_LINKED
    /* ST OTP HSE trim must be applied before HSE becomes the PLL/SAI source. */
    extern void MX_APPE_Config(void);
    MX_APPE_Config();
#endif
    if (!power_clock_prepare()) { return false; }
    osc.OscillatorType = RCC_OSCILLATORTYPE_HSI | RCC_OSCILLATORTYPE_HSE;
    osc.HSEState = RCC_HSE_ON; osc.HSEDiv = RCC_HSE_DIV1;
    osc.HSIState = RCC_HSI_ON; osc.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
    /* One immutable audio kernel for both blocks: 32MHz / 8 *
     * (61 + 3603/8192) / 5 = 49.151855MHz (-2.95ppm nominal).
     * Block B MCKDIV=12 -> 16kHz I2S; block A can independently decimate PDM.
     * CPU R output is 61.43982MHz; immutable <=64MHz trial;
     * audio start/stop never changes this shared PLL. */
    osc.PLL1.PLLState = RCC_PLL_ON; osc.PLL1.PLLSource = RCC_PLLSOURCE_HSE;
    osc.PLL1.PLLM = 8; osc.PLL1.PLLN = 61; osc.PLL1.PLLP = 5;
    osc.PLL1.PLLQ = 5; osc.PLL1.PLLR = 4; osc.PLL1.PLLFractional = 3603;
    if (HAL_RCC_OscConfig(&osc) != HAL_OK) { return false; }
    clk.ClockType = RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_PCLK1 |
                    RCC_CLOCKTYPE_PCLK2 | RCC_CLOCKTYPE_PCLK7 | RCC_CLOCKTYPE_HCLK5;
    clk.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK; clk.AHBCLKDivider = RCC_SYSCLK_DIV1;
    clk.APB1CLKDivider = RCC_HCLK_DIV1; clk.APB2CLKDivider = RCC_HCLK_DIV1;
    clk.APB7CLKDivider = RCC_HCLK_DIV1; clk.AHB5_PLL1_CLKDivider = RCC_SYSCLK_PLL1_DIV2;
    clk.AHB5_HSEHSI_CLKDivider = RCC_SYSCLK_HSEHSI_DIV1;
    /* CubeWBA LL_SetFlashLatency(): VOS1, 32 < HCLK <= 64MHz uses
     * one wait state, not the 3WS required by the original98MHz profile.
     * HAL handles latency ordering around the frequency switch. AHB5 DIV2
     * stays30.71991MHz, below its32MHz bus maximum; audio PLL is unchanged. */
    if (HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_1) != HAL_OK) { return false; }
    __HAL_RCC_PLL1CLKOUT_ENABLE(RCC_PLL1_PCLK);
    __HAL_RCC_SAI1_CONFIG(RCC_SAI1CLKSOURCE_PLL1P);
    return true;
}
static void pins(void)
{
    __HAL_RCC_GPIOA_CLK_ENABLE(); __HAL_RCC_GPIOB_CLK_ENABLE(); __HAL_RCC_GPIOC_CLK_ENABLE();
    /* Preserve the boot helper's data-idle DC latch explicitly, alongside
     * inactive CS. RESET exists only for the expander (PB12). */
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_8 | GPIO_PIN_11, GPIO_PIN_SET);
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0 | GPIO_PIN_15, GPIO_PIN_SET);
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_RESET);
    gpio(GPIOA, GPIO_PIN_8 | GPIO_PIN_11, GPIO_MODE_OUTPUT_PP, GPIO_NOPULL, 0);
    gpio(GPIOB, GPIO_PIN_0 | GPIO_PIN_12 | GPIO_PIN_15, GPIO_MODE_OUTPUT_PP, GPIO_NOPULL, 0);
#if COMP_V11_PANEL_PASSIVE_TRACE || (COMP_V11_PANEL_SOFTWARE_SPI && COMP_V11_PANEL_STARTUP_READBACK)
    HAL_NVIC_DisableIRQ(EXTI12_IRQn);
    gpio(GPIOA, GPIO_PIN_12, COMPANION_WBA_SCREEN_ENABLED ? GPIO_MODE_IT_RISING_FALLING : GPIO_MODE_ANALOG, GPIO_NOPULL, 0);
    /* Disabled until a visible activation; NVIC12/event delivery stays off. */
    CLEAR_BIT(EXTI->IMR1, GPIO_PIN_12);
    CLEAR_BIT(EXTI->EMR1, GPIO_PIN_12);
#else
    gpio(GPIOA, GPIO_PIN_12, GPIO_MODE_INPUT, GPIO_NOPULL, 0);
#endif
    gpio(GPIOB, GPIO_PIN_14, GPIO_MODE_IT_RISING_FALLING, GPIO_PULLUP, 0);
    gpio(GPIOC, GPIO_PIN_13, GPIO_MODE_IT_FALLING, GPIO_PULLUP, 0);
    gpio(GPIOA, GPIO_PIN_5, GPIO_MODE_ANALOG, GPIO_NOPULL, 0); /* ADC gate remains low */
    gpio(GPIOA, GPIO_PIN_6 | GPIO_PIN_7, GPIO_MODE_AF_OD, GPIO_NOPULL, GPIO_AF4_I2C3);
    gpio(GPIOB, GPIO_PIN_1 | GPIO_PIN_2, COMPANION_WBA_SCREEN_ENABLED ? GPIO_MODE_AF_OD : GPIO_MODE_ANALOG, GPIO_NOPULL, GPIO_AF4_I2C1);
#if COMP_V11_PANEL_DEFER_IMU_START || COMP_V11_SHARED_SPI_GPIO
    /* Keep the boot helper's clock/data GPIO idle until the first panel
     * attempt terminates. SPI1 is initialized, but sends no IMU traffic and
     * does not take over these pins before this isolated startup attempt. */
#if COMP_V11_SHARED_SPI_GPIO
    gpio(GPIOB, GPIO_PIN_3, GPIO_MODE_INPUT, GPIO_NOPULL, 0);
#else
    gpio(GPIOB, GPIO_PIN_3, GPIO_MODE_AF_PP, GPIO_NOPULL, GPIO_AF5_SPI1);
#endif
    panel_gpio_active = true;
#else
    gpio(GPIOA, GPIO_PIN_15, GPIO_MODE_AF_PP, GPIO_NOPULL, GPIO_AF5_SPI1);
    gpio(GPIOB, GPIO_PIN_3 | GPIO_PIN_4, GPIO_MODE_AF_PP, GPIO_NOPULL, GPIO_AF5_SPI1);
#endif
    gpio(GPIOA, GPIO_PIN_0, GPIO_MODE_AF_PP, GPIO_NOPULL, GPIO_AF6_SPI3);
    gpio(GPIOB, GPIO_PIN_8 | GPIO_PIN_9, GPIO_MODE_AF_PP, GPIO_NOPULL, GPIO_AF6_SPI3);
    gpio(GPIOA, GPIO_PIN_1 | GPIO_PIN_2, GPIO_MODE_AF_PP, GPIO_PULLUP, GPIO_AF8_LPUART1);
    gpio(GPIOB, GPIO_PIN_5 | GPIO_PIN_6 | GPIO_PIN_7, GPIO_MODE_AF_PP, GPIO_NOPULL, GPIO_AF13_SAI1);
    gpio(GPIOA, GPIO_PIN_9 | GPIO_PIN_10, GPIO_MODE_AF_PP, GPIO_NOPULL, GPIO_AF3_SAI1);
    comp_v11_panel_gpio_slew();
}
static void wake_irqs_enable(comp_v11_hal_t *b)
{
    /* Clear boot-time edges before enabling. PC13 only wakes the foreground;
     * reading TCA6408 inputs later identifies touch, IMU or power source. */
    __HAL_GPIO_EXTI_CLEAR_IT(GPIO_PIN_13);
    __HAL_GPIO_EXTI_CLEAR_IT(GPIO_PIN_14);
#if COMP_V11_PANEL_PASSIVE_TRACE || (COMP_V11_PANEL_SOFTWARE_SPI && COMP_V11_PANEL_STARTUP_READBACK)
    __HAL_GPIO_EXTI_CLEAR_IT(GPIO_PIN_12);
    HAL_NVIC_DisableIRQ(EXTI12_IRQn);
    HAL_NVIC_ClearPendingIRQ(EXTI12_IRQn);
#endif
    HAL_NVIC_SetPriority(EXTI13_IRQn, 4, 0);
    HAL_NVIC_SetPriority(EXTI14_IRQn, 4, 0);
    HAL_NVIC_EnableIRQ(EXTI13_IRQn);
    HAL_NVIC_EnableIRQ(EXTI14_IRQn);
    b->wake_irq_ready = true;
}
static bool lse_probe(void)
{
    RCC_OscInitTypeDef osc = {0};
    HAL_PWR_EnableBkUpAccess();
    __HAL_RCC_LSEDRIVE_CONFIG(RCC_LSEDRIVE_MEDIUMLOW);
    osc.OscillatorType = RCC_OSCILLATORTYPE_LSE; osc.LSEState = RCC_LSE_ON;
    return HAL_RCC_OscConfig(&osc) == HAL_OK;
}
static bool rng_init(void)
{
    /* HSI16 is already enabled and does not change with audio start/stop. */
    __HAL_RCC_RNG_CONFIG(RCC_RNGCLKSOURCE_HSI);
    __HAL_RCC_RNG_CLK_ENABLE();
    family_rng.Instance=RNG;
    family_rng.Init.ClockErrorDetection=RNG_CED_ENABLE;
    return HAL_RNG_Init(&family_rng)==HAL_OK;
}
bool comp_v11_hal_random_u32(comp_v11_hal_t *board,uint32_t *value)
{
#ifdef COMPANION_WBA_BLE_LINKED
    extern bool comp_v11_ble_entropy(uint32_t *value);
    return board && value && comp_v11_ble_entropy(value);
#else
    uint32_t status;
    if (!board || !value || !board->rng_ready) return false;
    status=READ_REG(RNG->SR);
    if (status & (RNG_SR_SECS | RNG_SR_CECS | RNG_SR_SEIS | RNG_SR_CEIS)) {
        board->rng_ready=false; return false;
    }
    if (!(status&RNG_SR_DRDY)) return false;
    *value=READ_REG(RNG->DR);
    return true;
#endif
}
bool comp_v11_hal_device_uid(uint8_t uid[12])
{
    uint32_t words[3]={HAL_GetUIDw0(),HAL_GetUIDw1(),HAL_GetUIDw2()};
    uint8_t any=0u,not_ff=0u;
    if(!uid)return false;
    for(size_t i=0u;i<12u;i++){
        uid[i]=(uint8_t)(words[i/4u]>>(8u*(i%4u)));
        any|=uid[i];not_ff|=(uint8_t)(uid[i]^255u);
    }
    return any!=0u&&not_ff!=0u;
}
static bool i2c_init(I2C_HandleTypeDef *bus, I2C_TypeDef *instance)
{
    bus->Instance = instance;
    /* Fixed HSI16 kernel. Temporary touch target approximately 10kHz:
     * prescaler=7, SCLH=93/SCLL=105, SCLDEL=2 (1.5us), SDADEL=1.
     * The setup allowance covers a standard-mode 1us rise plus 250ns data
     * setup; actual edges still depend on the TXS0104E and PCB loading.
     * IO-expander I2C3 keeps its existing 100kHz timing. Recovery uses this
     * same initializer, so a touch retry cannot restore the former clock. */
    bus->Init.Timing = instance == I2C1 ? COMP_V11_TOUCH_I2C_TIMING : 0x10422529u;
    bus->Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    bus->Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
    bus->Init.OwnAddress2Masks = I2C_OA2_NOMASK;
    bus->Init.GeneralCallMode = I2C_GENERALCALL_DISABLE; bus->Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
    const bool ready = HAL_I2C_Init(bus) == HAL_OK && HAL_I2CEx_ConfigAnalogFilter(bus, I2C_ANALOGFILTER_ENABLE) == HAL_OK &&
                       HAL_I2CEx_ConfigDigitalFilter(bus, 0) == HAL_OK;
    if (ready && instance == I2C1) {
        HAL_NVIC_SetPriority(I2C1_EV_IRQn, 3, 0);
        HAL_NVIC_SetPriority(I2C1_ER_IRQn, 3, 0);
        HAL_NVIC_ClearPendingIRQ(I2C1_EV_IRQn);
        HAL_NVIC_ClearPendingIRQ(I2C1_ER_IRQn);
        HAL_NVIC_EnableIRQ(I2C1_EV_IRQn);
        HAL_NVIC_EnableIRQ(I2C1_ER_IRQn);
    }
    return ready;
}
static bool spi_init(SPI_HandleTypeDef *bus, SPI_TypeDef *instance)
{
    bus->Instance = instance; bus->Init.Mode = SPI_MODE_MASTER;
    bus->Init.Direction = SPI_DIRECTION_2LINES; bus->Init.DataSize = SPI_DATASIZE_8BIT;
    bus->Init.CLKPolarity = SPI_POLARITY_LOW; bus->Init.CLKPhase = SPI_PHASE_1EDGE;
    bus->Init.NSS = SPI_NSS_SOFT;
    /* NOR has its own fixed HSI16 kernel. HSI/2 gives 8MHz and shortens the
     * existing bounded page transactions; the reader still checks every page
     * and releases its shared scratch after each slice. Panel/IMU SPI1 and
     * the conservative recovery bootloader keep their clocks. No PLL, DMA,
     * extra buffering or longer foreground transaction is introduced. */
    bus->Init.BaudRatePrescaler = instance == SPI1 ? SPI_BAUDRATEPRESCALER_64 : SPI_BAUDRATEPRESCALER_2;
    bus->Init.FirstBit = SPI_FIRSTBIT_MSB; bus->Init.TIMode = SPI_TIMODE_DISABLE;
    bus->Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
    bus->Init.NSSPMode = SPI_NSS_PULSE_DISABLE; bus->Init.NSSPolarity = SPI_NSS_POLARITY_LOW;
    bus->Init.FifoThreshold = SPI_FIFO_THRESHOLD_01DATA;
    bus->Init.MasterKeepIOState = SPI_MASTER_KEEP_IO_STATE_ENABLE;
    return HAL_SPI_Init(bus) == HAL_OK;
}
static bool transfer(SPI_HandleTypeDef *bus, const uint8_t *tx, uint8_t *rx, size_t n, uint32_t timeout)
{
#ifdef COMPANION_WBA_BLE_LINKED
    /* Only actual 256-byte physical pages inside the synchronous upload
     * backend. Mount, journal, screen, writes and live capture stay unobserved.
     * Elapsed includes IRQs, HAL polling and dummy preparation, not pure wire. */
    bool measuring=bus==&spi_flash && tx==NULL && rx!=NULL && n==256u &&
        comp_v11_ble_observe_backend_read_active();
    uint32_t started=measuring?comp_v11_ble_observe_spi_page(true):0u;
#endif
    bool ok=comp_v11_spi_polling_transfer(bus, tx, rx, n, timeout);
#ifdef COMPANION_WBA_BLE_LINKED
    if(measuring)comp_v11_ble_observe_nor_read(comp_v11_ble_observe_spi_page(false)-started);
#endif
    return ok;
}
uint32_t comp_v11_hal_nor_sck_hz(void)
{
    /* Register-derived configured clock, not a physical SCK measurement. */
    uint32_t divisor=2u<<((spi_flash.Instance->CFG1&SPI_CFG1_MBR_Msk)>>SPI_CFG1_MBR_Pos);
    return HAL_RCCEx_GetPeriphCLKFreq(RCC_PERIPHCLK_SPI3)/divisor;
}
static bool imu_transfer(uint8_t reg, uint8_t *rx, const uint8_t *tx, size_t n)
{
    bool ok;
    if (spi_owned || __get_IPSR() != 0u || imu_start_pending ||
        panel_holds_shared_bus(active_board)) { return false; }
    panel_busy_trace(false);
    spi_owned = true;
    comp_cpu_duty_span_t span=comp_cpu_duty_span_begin();
    reg = rx != NULL ? (uint8_t)(reg | 0x80u) : reg;
#if COMP_V11_SHARED_SPI_GPIO
    ok = imu_gpio_transfer(reg, rx, tx, n);
#else
#if COMP_V11_PANEL_SOFTWARE_SPI
    /* Restore AF5 only when the IMU actually takes the shared bus. */
    panel_gpio_to_hardware();
#endif
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0, GPIO_PIN_SET);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_11, GPIO_PIN_SET);
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_15, GPIO_PIN_RESET);
    const uint32_t timeout=active_board&&active_board->microphone.running?1u:10u;
    ok = transfer(&spi_shared, &reg, NULL, 1, timeout) && transfer(&spi_shared, tx, rx, n, timeout);
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_15, GPIO_PIN_SET);
#endif
    panel_busy_trace(true);
    comp_cpu_duty_span_end(COMP_DUTY_IMU_GPIO,span);
    spi_owned = false; return ok;
}
static bool imu_read(void *p, uint8_t reg, uint8_t *data, size_t n)
{ (void)p; return imu_transfer(reg, data, NULL, n); }
static bool imu_write(void *p, uint8_t reg, const uint8_t *data, size_t n)
{ (void)p; return imu_transfer(reg, NULL, data, n); }
static bool io_bus_idle(void)
{
    /* The pinned WBA HAL waits up to 25 ms for BUSY before using its caller
     * timeout. I2C3 has one foreground owner; no queued transfer may hide
     * behind that wait or run a tick-based transaction from an ISR. */
    return __get_IPSR() == 0u && i2c_io.Instance != NULL &&
        HAL_I2C_GetState(&i2c_io) == HAL_I2C_STATE_READY &&
        __HAL_I2C_GET_FLAG(&i2c_io, I2C_FLAG_BUSY) != SET;
}
static bool io_admit_write(void *context)
{
    (void)context;
    return io_bus_idle();
}
static uint32_t io_timeout(const comp_v11_hal_t *b)
{
    /* One byte at the existing 100 kHz fits within 1 ms. During capture a
     * failed transaction must not spend the full 10 ms PCM half-period.
     * HAL uses integer ticks with a strict > comparison, so this is a
     * caller budget, not a claim of a hard 1 ms wall-time deadline. */
    return b != NULL && b->microphone.running ? 1u : 10u;
}
static bool io_read(void *p, uint8_t addr, uint8_t reg, uint8_t *data)
{
    comp_v11_hal_t *b = p;
    const bool ok = data != NULL && io_bus_idle() &&
        HAL_I2C_Mem_Read(&i2c_io, (uint16_t)(addr << 1), reg,
                        I2C_MEMADD_SIZE_8BIT, data, 1, io_timeout(b)) == HAL_OK;
    if (b != NULL && reg == 0u) {
        b->expander_input_valid = ok;
        if (ok) b->expander_raw_inputs = *data;
        if(ok && (b->imu.recording_taps || b->imu.idle_accel_only) && (*data&COMP_V11_IMU_INT))
            b->imu.event_irq_pending=true;
    }
    return ok;
}
static bool io_write(void *p, uint8_t addr, uint8_t reg, uint8_t data)
{
    const comp_v11_hal_t *b = p;
    return io_bus_idle() && HAL_I2C_Mem_Write(&i2c_io,
        (uint16_t)(addr << 1), reg, I2C_MEMADD_SIZE_8BIT, &data, 1,
        io_timeout(b)) == HAL_OK;
}
static bool io_sample_inputs(comp_v11_hal_t *b)
{
    const bool ok = comp_tca6408_sample(&b->io, &b->expander_inputs);
    /* faults describes current peripheral health, as for IMU/touch. Only a
     * new successful input transfer with a trusted output shadow can retire
     * an IO fault. An entered-write failure keeps ready=false and cannot be
     * healed by sampling. Keep the driver's cumulative error evidence. */
    if (ok && b->io.ready) b->faults &= ~COMP_V11_FAULT_IO;
    else b->faults |= COMP_V11_FAULT_IO;
    return ok;
}
static bool touch_bus_idle(comp_v11_hal_t *b)
{
    /* HAL Mem_Read/Mem_Write use a separate fixed BUSY wait before their
     * caller timeout. A stalled touch bus must not enter that wait during
     * capture or an interactive frame. The foreground owns this I2C bus. */
    if (i2c_touch.Instance == NULL || HAL_I2C_GetState(&i2c_touch) != HAL_I2C_STATE_READY ||
        __HAL_I2C_GET_FLAG(&i2c_touch, I2C_FLAG_BUSY) == SET) {
        b->touch_i2c_status = (uint8_t)HAL_BUSY;
        b->touch_i2c_error = HAL_I2C_GetError(&i2c_touch);
        return false;
    }
    return true;
}
static bool touch_probe(void *p, uint8_t addr)
{
    comp_v11_hal_t *b = p;
    uint8_t identity_byte;
    if (b == NULL || b->display_power.state != COMP_V11_POWER_READY || __get_IPSR() != 0u) return false;
    if (!touch_bus_idle(b)) return false;
    /* A normal identity-register read also preserves a specific ACK error;
     * this HAL's address-only IsDeviceReady labels exhausted NACK trials as
     * TIMEOUT, which obscures the physical communication failure. */
    b->touch_stop_read=false;
    if (comp_v11_hal_touch_read(addr,COMP_FT6336_IDENTITY_REGISTER,&identity_byte,1u)) return true;
    /* Saved address discovery saw 0x38 ACK while register reads still failed.
     * Try a STOP-separated register selector/read only for that responding
     * device, during the existing idle-only initialization window. */
    if (b->microphone.running || b->playback_active || !touch_bus_idle(b) ||
        HAL_I2C_IsDeviceReady(&i2c_touch,(uint16_t)(addr<<1),1u,TOUCH_I2C_TIMEOUT_MS)!=HAL_OK) return false;
    b->touch_stop_read=true;
    const bool ok=comp_v11_hal_touch_read(addr,COMP_FT6336_IDENTITY_REGISTER,&identity_byte,1u);
    if (!ok) b->touch_stop_read=false;
    return ok;
}
static bool touch_read(void *p, uint8_t addr, uint8_t reg, uint8_t *data, uint16_t size)
{ (void)p; return comp_v11_hal_touch_read(addr, reg, data, size); }
static bool touch_write(void *p, uint8_t addr, uint8_t reg, const uint8_t *data, uint16_t size)
{
    comp_v11_hal_t *b = p;
    HAL_StatusTypeDef status;
    if (b == NULL || b->display_power.state != COMP_V11_POWER_READY || __get_IPSR() != 0) { return false; }
    if (!touch_bus_idle(b)) return false;
    status = HAL_I2C_Mem_Write(&i2c_touch, (uint16_t)(addr << 1), reg, I2C_MEMADD_SIZE_8BIT,
                              (uint8_t *)data, size, TOUCH_I2C_TIMEOUT_MS);
    b->touch_i2c_status = (uint8_t)status;
    b->touch_i2c_error = HAL_I2C_GetError(&i2c_touch);
    return status == HAL_OK;
}
static bool touch_initialize(comp_v11_hal_t *b)
{
    /* Recovery happens outside capture/playback. Keep the adapter's counters
     * and configuration ports, so read_count never resets under the UI. */
    b->touch_init_stage = 1u;
    if (!touch_bus_idle(b)) {
        /* Reinitialize only this MCU peripheral on an electrically idle bus.
         * Held-low wires remain a reported fault, without GPIO clock/reset
         * pulses or changes to the panel, expander, audio, or Flash buses. */
        if (HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_2) != GPIO_PIN_SET ||
            HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_1) != GPIO_PIN_SET) return false;
        if (i2c_touch.Instance != NULL && HAL_I2C_DeInit(&i2c_touch) != HAL_OK) return false;
        if (!i2c_init(&i2c_touch, I2C1) || !touch_bus_idle(b)) return false;
    }
    if (!companion_touch_ft6336_stm32wba_probe(&b->touch)) return false;
    b->touch_init_stage = 2u;
    if (!companion_touch_ft6336_stm32wba_read_identity(&b->touch)) return false;
    b->touch_chip_id = b->touch.identity.chip_id;
    b->touch_init_stage = 3u;
    if (!companion_touch_ft6336_stm32wba_configure_interrupt(&b->touch)) return false;
    b->touch_init_stage = 4u;
    if (!companion_touch_ft6336_stm32wba_configure_runtime_tuning(&b->touch)) return false;
    b->touch_init_stage = 5u;
    return true;
}
bool comp_v11_hal_touch_pending(void) { return touch_rx.phase != 0u; }
static void touch_report_failed(comp_v11_hal_t *b, uint32_t tick, HAL_StatusTypeDef status)
{
    /* Stop this MCU transfer only, without wire pulses or device resets.
     * Existing idle-only recovery owns later peripheral reinitialization. */
    HAL_NVIC_DisableIRQ(I2C1_EV_IRQn); HAL_NVIC_DisableIRQ(I2C1_ER_IRQn);
    b->touch_i2c_error = HAL_I2C_GetError(&i2c_touch);
    b->touch_i2c_status = (uint8_t)status;
    (void)HAL_I2C_DeInit(&i2c_touch);
    HAL_NVIC_ClearPendingIRQ(I2C1_EV_IRQn); HAL_NVIC_ClearPendingIRQ(I2C1_ER_IRQn);
    touch_rx.phase = 0u;
    b->touch.error_count++;
    b->touch.detected = false;
    b->touch.identity_attempted = b->touch.identity_valid = false;
    b->touch.interrupt_mode_attempted = b->touch.interrupt_mode_valid = false;
    b->touch.runtime_tuning_attempted = b->touch.runtime_tuning_valid = false;
    b->touch_ack = b->touch_attempted = false;
    b->touch_retry_ms = tick + TOUCH_RETRY_MS;
    comp_power_policy_set_touch_wake_ready(&b->power, false);
    memset(&b->touch_sample, 0, sizeof(b->touch_sample));
    b->faults |= COMP_V11_FAULT_TOUCH;
}
static void touch_report_start(comp_v11_hal_t *b, uint32_t tick)
{
    if (touch_rx.phase != 0u) return;
    if (!touch_bus_idle(b)) { touch_report_failed(b,tick,HAL_BUSY); return; }
    touch_rx.deadline_ms = tick + TOUCH_REPORT_DEADLINE_MS;
    touch_rx.selector = COMP_FT6336_TOUCH_REPORT_REGISTER;
    touch_rx.start_status = (uint8_t)HAL_OK;
    b->touch_read_leg = b->touch_stop_read ? 1u : 0u;
    touch_rx.phase = b->touch_stop_read ? 1u : 2u;
    const HAL_StatusTypeDef status = b->touch_stop_read ?
        HAL_I2C_Master_Transmit_IT(&i2c_touch,(uint16_t)(b->touch.address_7bit<<1),&touch_rx.selector,1u) :
        HAL_I2C_Mem_Read_IT(&i2c_touch,(uint16_t)(b->touch.address_7bit<<1),COMP_FT6336_TOUCH_REPORT_REGISTER,
                          I2C_MEMADD_SIZE_8BIT,touch_rx.report,sizeof(touch_rx.report));
    if (status != HAL_OK) touch_report_failed(b,tick,status);
}
static void touch_report_complete(comp_v11_hal_t *b, uint32_t tick)
{
    if (touch_rx.phase == 0u) return;
    if (touch_rx.phase == 3u || HAL_I2C_GetError(&i2c_touch) != HAL_I2C_ERROR_NONE) {
        touch_report_failed(b,tick,HAL_ERROR); return;
    }
    if (touch_rx.phase == 2u && HAL_I2C_GetState(&i2c_touch) == HAL_I2C_STATE_READY) {
        comp_ft6336_touch_sample_t sample;
        if (!comp_ft6336_decode_touch_report(touch_rx.report,&sample) ||
            (sample.touch_count != 0u && (sample.x >= 200u || sample.y >= 200u))) {
            touch_report_failed(b,tick,HAL_ERROR); return;
        }
        touch_rx.phase = 0u;
        b->touch_i2c_status = (uint8_t)HAL_OK;
        b->touch_i2c_error = HAL_I2C_ERROR_NONE;
        b->touch.read_count++;
        if (sample.touch_count != 0u) {
            if (b->touch_sample.touch_count == 0u) b->touch_down_count++;
            b->touch_last_contact_ms = tick;
            b->touch_last_x = sample.x; b->touch_last_y = sample.y;
        }
        b->touch_sample = sample;
    } else if ((int32_t)(tick-touch_rx.deadline_ms) >= 0) touch_report_failed(b,tick,HAL_TIMEOUT);
}
static void touch_discovery_step(comp_v11_hal_t *b)
{
    /* One address-only transaction after an idle failed FT probe. Complete
     * one pass per boot, excluding reserved/general-call addresses. Never
     * write registers or treat another ACK as an FT6336 touch report. The
     * caller excludes all capture/playback/storage/transfer/update work. */
    if (b->touch_init_stage != 1u || b->touch_scan_next > 0x77u || !touch_bus_idle(b)) return;
    if (b->touch_scan_next == 0u) b->touch_scan_next = 0x08u;
    const uint8_t address = b->touch_scan_next++;
    const uint8_t saved_status = b->touch_i2c_status;
    const uint32_t saved_error = b->touch_i2c_error;
    const HAL_StatusTypeDef status = HAL_I2C_IsDeviceReady(
        &i2c_touch, (uint16_t)(address << 1u), 1u, TOUCH_I2C_TIMEOUT_MS);
    ++b->touch_scan_count;
    if (status == HAL_OK) b->touch_scan_ack[address / 32u] |= UINT32_C(1) << (address % 32u);
    else if (status != HAL_TIMEOUT && HAL_I2C_GetError(&i2c_touch) != HAL_I2C_ERROR_AF)
        ++b->touch_scan_errors;
    b->touch_i2c_status = saved_status;
    b->touch_i2c_error = saved_error;
}
static bool touch_recovery_ready(comp_v11_hal_t *b, uint32_t tick)
{
    /* Only TCA P1 is TP_RST. It is separate from the unconnected EPD_RES.
     * The caller excludes capture/playback/storage/transfer/update/NVM work.
     * Never reset the expander or toggle the always-on 3V rail. */
    if (b->touch_reset_phase == 1u) {
        if (!comp_tca6408_update(&b->io, COMP_V11_TP_RESET, COMP_V11_TP_RESET)) {
            b->faults |= COMP_V11_FAULT_IO;
            b->touch_retry_ms = tick + TOUCH_RETRY_MS;
            return false;
        }
        b->touch_reset_phase = 2u;
        b->touch_retry_ms = tick + COMP_V11_TOUCH_STARTUP_MS;
        return false;
    }
    if (b->touch_reset_phase == 2u) {
        b->touch_reset_phase = 0u;
        return true;
    }
    if (b->touch_retry_count != 0u && b->touch_retry_count % 8u == 0u) {
        if (!comp_tca6408_update(&b->io, COMP_V11_TP_RESET, 0u)) {
            b->faults |= COMP_V11_FAULT_IO;
            b->touch_retry_ms = tick + TOUCH_RETRY_MS;
            return false;
        }
        b->touch_reset_count++;
        b->touch_reset_phase = 1u;
        b->touch_retry_ms = tick + 20u;
        return false;
    }
    return true;
}
static bool flash_cs(void *p, bool active)
{
    (void)p;
    const bool spi_idle = spi_flash.Instance == SPI3 && spi_flash.State == HAL_SPI_STATE_READY &&
        spi_flash.Lock == HAL_UNLOCKED && (SPI3->CR1 & SPI_CR1_SPE) == 0u &&
        (SPI3->CFG1 & (SPI_CFG1_TXDMAEN | SPI_CFG1_RXDMAEN)) == 0u;
    const bool gpio_output = (GPIOA->MODER & (3u << 16u)) == (1u << 16u) &&
        (GPIOA->OTYPER & GPIO_PIN_8) == 0u;
    if (active) {
        /* Never select the NOR into a transfer already owned by someone else. */
        if (!spi_idle || !gpio_output || !(GPIOA->ODR & GPIO_PIN_8)) return false;
        HAL_GPIO_WritePin(GPIOA, GPIO_PIN_8, GPIO_PIN_RESET);
        return (GPIOA->ODR & GPIO_PIN_8) == 0u;
    }
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_8, GPIO_PIN_SET);
    /* The GPIO output latch is not a physical NOR-pin measurement. */
    return spi_idle && gpio_output && (GPIOA->ODR & GPIO_PIN_8) != 0u;
}
static bool flash_transfer(void *p, const uint8_t *tx, uint8_t *rx, size_t n, uint32_t timeout)
{
    bool ok = transfer(&spi_flash, tx, rx, n, timeout);
#ifdef COMPANION_WBA_BLE_LINKED
    /* A blank journal must be checked in full before formatting. At HSI/16
     * its 8MiB read exceeds the boot watchdog period. Only successful bounded
     * foreground IO during this finite startup phase earns a reload; normal
     * operation remains supervised by the main loop. Never feed from an ISR,
     * a failed transfer, or an indefinitely repeated startup operation. */
    if (ok && n != 0u && p == active_board && startup_storage_active &&
        __get_IPSR() == 0u && HAL_GetTick() - startup_storage_started < 180000u) {
        LL_IWDG_ReloadCounter(IWDG);
    }
#else
    (void)p;
#endif
    return ok;
}
void comp_v11_hal_storage_init_complete(void)
{ startup_storage_active = false; }
static uint32_t now(void *p) { (void)p; return HAL_GetTick(); }
static void delay(void *p, uint32_t ms) { (void)p; HAL_Delay(ms); }
/* On-demand SOUND observation. No UART/I2C in the DMA ISR; no activity when
 * unarmed. Kept outside the product/recording state and never a success gate. */
static volatile uint8_t speaker_probe[8];
static volatile uint16_t speaker_probe_peak;
static uint8_t speaker_probe_io(comp_v11_hal_t *b, volatile uint8_t *out)
{
    static const uint8_t registers[3]={0u,1u,3u};
    uint8_t valid=0u;
    for(unsigned i=0u;i<3u;++i) {
        uint8_t value=0u;
        if(b->io.read && b->io.read(b->io.context,b->io.address,registers[i],&value)) {
            out[i]=value;valid|=(uint8_t)(1u<<i);
        }
    }
    return valid;
}
bool comp_v11_hal_speaker_diagnostic_arm(comp_v11_hal_t *b)
{
    if(!b || __get_IPSR()!=0u || b->microphone.running ||
       comp_speaker_active(&b->speaker) || !b->speaker_ready || !b->io.ready)
        return false;
    speaker_probe[7]=0u;speaker_probe_peak=0u;
    for(unsigned i=0u;i<7u;++i)speaker_probe[i]=0u;
    speaker_probe[0]=speaker_probe_io(b,&speaker_probe[1]);
    __DMB();speaker_probe[7]=1u;
    return true;
}
void comp_v11_hal_speaker_diagnostic_report(comp_v11_hal_t *b)
{
    if(!b || __get_IPSR()!=0u || b->microphone.running ||
       comp_speaker_active(&b->speaker) || !b->speaker_ready || !b->io.ready ||
       !sai_speaker.Instance || speaker_probe[7]==0u)return;
    speaker_probe[7]=0u;__DMB();
    uint8_t off[3]={0u};uint8_t valid=speaker_probe_io(b,off);
    char line[384];
    (void)snprintf(line,sizeof(line),
        "SOUND2 valid=%02X before=%02X,%02X,%02X on=%02X,%02X,%02X off=%02X,%02X,%02X off_valid=%X pcm_peak=%u vol=%u mute=%u core=%lu pb_mode=%08lX pb_af=%08lX sai_cr1=%08lX sai_frcr=%08lX sai_slot=%08lX sai_error=%08lX\r\n",
        (unsigned)speaker_probe[0],(unsigned)speaker_probe[1],(unsigned)speaker_probe[2],
        (unsigned)speaker_probe[3],(unsigned)speaker_probe[4],(unsigned)speaker_probe[5],
        (unsigned)speaker_probe[6],(unsigned)off[0],(unsigned)off[1],(unsigned)off[2],
        (unsigned)valid,(unsigned)speaker_probe_peak,(unsigned)b->speaker.volume_percent,
        (unsigned)b->speaker.muted,(unsigned long)SystemCoreClock,
        (unsigned long)GPIOB->MODER,(unsigned long)GPIOB->AFR[0],
        (unsigned long)sai_speaker.Instance->CR1,(unsigned long)sai_speaker.Instance->FRCR,
        (unsigned long)sai_speaker.Instance->SLOTR,(unsigned long)sai_speaker.ErrorCode);
    comp_v11_hal_log(line);
}
static bool amp(void *p, bool enabled)
{
    comp_v11_hal_t *b = p;
    if (!b || __get_IPSR() != 0u) { return false; }
    bool stopped = true;
    if (!enabled && sai_speaker.Instance != NULL) {
        /* Shut down this block even if the expander loses its ACK. Do not
         * reset shared SAI1 clocks or the microphone's block A. */
        stopped = HAL_SAI_DMAStop(&sai_speaker) == HAL_OK;
        __DMB();
        stopped = stopped && dma_speaker.Instance != NULL &&
            (dma_speaker.Instance->CCR & DMA_CCR_EN) == 0u &&
            (sai_speaker.Instance->CR1 & (SAI_xCR1_SAIEN | SAI_xCR1_DMAEN)) == 0u;
        speaker_completion = 0;
        speaker_prefilled = 0;
    }
    const bool ok=comp_tca6408_update(&b->io, COMP_V11_AMP_ENABLE, enabled ? COMP_V11_AMP_ENABLE : 0);
    if (!enabled) {
        if (!stopped || !ok) {
            b->faults |= COMP_V11_FAULT_AUDIO | COMP_V11_FAULT_SPEAKER_SHUTDOWN;
            /* No live transfer remains in the FAULT state: reuse its deadline. */
            speaker_submit_started_ms = HAL_GetTick();
        } else b->faults &= ~COMP_V11_FAULT_SPEAKER_SHUTDOWN;
    }
    if(enabled && speaker_probe[7]==1u) {
        speaker_probe[0]|=(uint8_t)(speaker_probe_io(b,&speaker_probe[4])<<3u);
        __DMB();speaker_probe[7]=2u;
    }
    return ok && stopped;
}
static bool submit(void *p, const int16_t *pcm, size_t frames)
{
    comp_v11_hal_t *b = p;
    if (!b || !pcm || !b->speaker_ready || frames > COMP_SPEAKER_BLOCK_FRAMES || frames == 0) { return false; }
    /* Normal CubeWBA DMA completion leaves SAI clocks running with DMA and
     * error IRQs disabled. An empty idle FIFO can latch UDR before re-arm.
     * Clear only that idle flag; never clear a reported or active error. */
    if(sai_speaker.State!=HAL_SAI_STATE_READY || sai_speaker.ErrorCode!=HAL_SAI_ERROR_NONE ||
       (sai_speaker.Instance->CR1&SAI_xCR1_DMAEN)!=0u)return false;
    __HAL_SAI_CLEAR_FLAG(&sai_speaker,SAI_FLAG_OVRUDR);
    if (HAL_SAI_Transmit_DMA(&sai_speaker, (uint8_t *)pcm, (uint16_t)(frames * 2u)) != HAL_OK)
        return false;
    speaker_submit_started_ms=HAL_GetTick();
    return true;
}
static void activity(void *p, bool active)
{
    comp_v11_hal_t *b = p; active = active || (b->faults & COMP_V11_FAULT_SPEAKER_SHUTDOWN) != 0u;
    b->playback_active = active;
    comp_power_policy_set_blocker(&b->power, COMP_POWER_BLOCKER_PLAYBACK, active);
}
static bool speaker_init(void)
{
    __HAL_RCC_SAI1_CLK_ENABLE(); __HAL_RCC_GPDMA1_CLK_ENABLE();
    dma_speaker.Instance = GPDMA1_Channel0;
    dma_speaker.Init.Request = GPDMA1_REQUEST_SAI1_B;
    dma_speaker.Init.BlkHWRequest = DMA_BREQ_SINGLE_BURST;
    dma_speaker.Init.Direction = DMA_MEMORY_TO_PERIPH;
    dma_speaker.Init.SrcInc = DMA_SINC_INCREMENTED; dma_speaker.Init.DestInc = DMA_DINC_FIXED;
    dma_speaker.Init.SrcDataWidth = DMA_SRC_DATAWIDTH_HALFWORD; dma_speaker.Init.DestDataWidth = DMA_DEST_DATAWIDTH_HALFWORD;
    dma_speaker.Init.Priority = DMA_HIGH_PRIORITY;
    dma_speaker.Init.SrcBurstLength = 1; dma_speaker.Init.DestBurstLength = 1;
    dma_speaker.Init.TransferAllocatedPort = DMA_SRC_ALLOCATED_PORT0 | DMA_DEST_ALLOCATED_PORT0;
    dma_speaker.Init.TransferEventMode = DMA_TCEM_BLOCK_TRANSFER; dma_speaker.Init.Mode = DMA_NORMAL;
    if (HAL_DMA_Init(&dma_speaker) != HAL_OK) { return false; }
    sai_speaker.Instance = SAI1_Block_B;
    sai_speaker.Init.AudioMode = SAI_MODEMASTER_TX; sai_speaker.Init.Synchro = SAI_ASYNCHRONOUS;
    sai_speaker.Init.SynchroExt = SAI_SYNCEXT_DISABLE; sai_speaker.Init.OutputDrive = SAI_OUTPUTDRIVE_ENABLE;
    sai_speaker.Init.NoDivider = SAI_MASTERDIVIDER_ENABLE; sai_speaker.Init.FIFOThreshold = SAI_FIFOTHRESHOLD_HF;
    sai_speaker.Init.AudioFrequency = SAI_AUDIO_FREQUENCY_MCKDIV; sai_speaker.Init.Mckdiv = 12;
    sai_speaker.Init.MckOverSampling = SAI_MCK_OVERSAMPLING_DISABLE;
    sai_speaker.Init.MonoStereoMode = SAI_STEREOMODE; sai_speaker.Init.CompandingMode = SAI_NOCOMPANDING;
    sai_speaker.Init.TriState = SAI_OUTPUT_NOTRELEASED; sai_speaker.Init.MckOutput = SAI_MCK_OUTPUT_DISABLE;
    __HAL_LINKDMA(&sai_speaker, hdmatx, dma_speaker);
    if (HAL_SAI_InitProtocol(&sai_speaker, SAI_I2S_STANDARD, SAI_PROTOCOL_DATASIZE_16BIT, 2) != HAL_OK) { return false; }
    HAL_NVIC_SetPriority(GPDMA1_Channel0_IRQn, 2, 0); HAL_NVIC_EnableIRQ(GPDMA1_Channel0_IRQn);
    HAL_NVIC_SetPriority(SAI1_IRQn, 2, 0); HAL_NVIC_EnableIRQ(SAI1_IRQn);
    return true;
}
static bool pcm_frame(void *context, const int16_t *samples, size_t count, uint32_t sample_rate)
{
    comp_v11_hal_t *b = context;
    if (count != COMP_WBA_PDM_PCM_FRAME_SAMPLES || sample_rate != 16000u) { return false; }
    if (b->pcm_sink != NULL) { return b->pcm_sink(b->pcm_sink_context, samples, count, sample_rate); }
    /* The PDM converter retains the frame; no second unconsumed copy. */
    b->pcm_frames++;
    return true;
}
bool comp_v11_hal_set_pcm_sink(comp_v11_hal_t *b, comp_wba_pdm_pcm_frame_fn_t sink, void *context)
{
    if (b == NULL || b->microphone.running) { return false; }
    b->pcm_sink = sink; b->pcm_sink_context = context; return true;
}
#if COMPANION_WBA_DUAL_MIC_PROBE
static int16_t dual_pair_frame[2u*COMP_WBA_PDM_PCM_FRAME_SAMPLES];
static comp_wba_dual_mic_probe_t dual_probe;
static void microphone_pair_frame(void *,const int16_t *,size_t,uint32_t);
#if COMPANION_WBA_DUAL_PAIR_CAPTURE
static comp_wba_pdm_pair_frame_fn_t finite_pair_sink;
static void *finite_pair_context;
bool comp_v11_hal_set_pair_sink(comp_v11_hal_t *b,comp_wba_pdm_pair_frame_fn_t sink,void *context)
{
    if(!b||b->microphone.running||!comp_wba_pdm_capture_ready(&b->microphone.processing)||
        (sink&&finite_pair_sink)||(!sink&&finite_pair_context!=context))return false;
    /* Pair capability is not a permanent recording observer. Only the finite
     * pair owner needs right-channel filtering/interleaving and correlation.
     * Change the whole observer tuple while stopped, before stream priming;
     * ordinary LEFT stays bit-identical and BEAMFORM still filters both. */
    comp_wba_pdm_config_t *cfg=&b->microphone.processing.config;
    cfg->observe_pair_frame=sink?microphone_pair_frame:NULL;
    cfg->pair_pcm_storage=sink?dual_pair_frame:NULL;
    cfg->pair_pcm_capacity=sink?2u*COMP_WBA_PDM_PCM_FRAME_SAMPLES:0u;
    cfg->selected_only=!sink&&cfg->output<COMP_WBA_PDM_OUTPUT_MIX;
    finite_pair_sink=sink;finite_pair_context=sink?context:NULL;return true;
}
#endif
static uint64_t dual_probe_failure_baseline;
static uint64_t dual_probe_failures(const comp_v11_hal_t *b)
{
    const comp_wba_pdm_stats_t *s=&b->microphone.processing.stats;
    return s->missing_dma_blocks+s->reordered_dma_blocks+s->invalid_dma_blocks+s->pcm_frames_rejected;
}
static void microphone_pair_frame(void *context,const int16_t *pairs,size_t frames,uint32_t rate)
{
    comp_v11_hal_t *b=context;
    if(rate!=16000u||frames!=160u||dual_probe_failures(b)!=dual_probe_failure_baseline)
        comp_wba_dual_probe_invalidate(&dual_probe);
    comp_wba_dual_probe_add(&dual_probe,pairs,frames);
#if COMPANION_WBA_DUAL_PAIR_CAPTURE
    if(finite_pair_sink)finite_pair_sink(finite_pair_context,pairs,frames,rate);
#endif
}
#endif
void comp_v11_hal_dual_mic_report(const comp_v11_hal_t *b,uint32_t token)
{
#if COMPANION_WBA_DUAL_MIC_PROBE
    if(!b||b->microphone.running)return; /* Never format or transmit in capture. */
    if(dual_probe_failures(b)!=dual_probe_failure_baseline)comp_wba_dual_probe_invalidate(&dual_probe);
    char line[224];
    (void)snprintf(line,sizeof(line),"DMIC1 schema=1 token=%lu samples=%lu count=%lu invalid=%u clip_l=%lu clip_r=%lu ls_hi=%ld ls_lo=%lu lss_hi=%lu lss_lo=%lu\r\n",
        (unsigned long)token,(unsigned long)dual_probe.samples,(unsigned long)dual_probe.count,
        (unsigned)dual_probe.invalid,(unsigned long)dual_probe.clipped_left,(unsigned long)dual_probe.clipped_right,
        (long)(int32_t)((uint64_t)dual_probe.left_sum>>32),(unsigned long)(uint32_t)dual_probe.left_sum,
        (unsigned long)(dual_probe.left_square>>32),(unsigned long)(uint32_t)dual_probe.left_square);
    comp_v11_hal_log(line);
    for(int lag=-COMP_WBA_DUAL_PROBE_LAG;lag<=COMP_WBA_DUAL_PROBE_LAG;++lag){
        unsigned k=(unsigned)(lag+COMP_WBA_DUAL_PROBE_LAG);
        (void)snprintf(line,sizeof(line),"DMIC1 lag=%d rs_hi=%ld rs_lo=%lu rss_hi=%lu rss_lo=%lu cross_hi=%ld cross_lo=%lu\r\n",lag,
            (long)(int32_t)((uint64_t)dual_probe.right_sum[k]>>32),(unsigned long)(uint32_t)dual_probe.right_sum[k],
            (unsigned long)(dual_probe.right_square[k]>>32),(unsigned long)(uint32_t)dual_probe.right_square[k],
            (long)(int32_t)((uint64_t)dual_probe.cross[k]>>32),(unsigned long)(uint32_t)dual_probe.cross[k]);
        comp_v11_hal_log(line);
    }
#else
    (void)b;(void)token;
#endif
}
bool comp_v11_hal_microphone_profile(comp_v11_hal_t *b,uint8_t profile,bool allow_directional)
{
    if(!b || !b->microphone.initialized || b->microphone.running)return false;
#if defined(COMPANION_WBA_DUAL_MIC_DELAY_Q8)
    const comp_wba_dual_mic_config_t measured={COMPANION_WBA_DUAL_MIC_DELAY_Q8,
        COMPANION_WBA_DUAL_MIC_RIGHT_GAIN_Q15,COMPANION_WBA_DUAL_MIC_INVERT_RIGHT != 0};
#if COMPANION_WBA_AUDIO_PROFILE
    const uint8_t calibration_uid[12]=COMP_WBA_AUDIO_CALIBRATION_UID_BYTES;
    uint8_t uid[12];
    allow_directional=allow_directional && COMP_WBA_AUDIO_CALIBRATION_PRESENT &&
        comp_v11_hal_device_uid(uid) && memcmp(uid,calibration_uid,12u)==0;
#endif
    return comp_wba_microphone_profile_select(&b->microphone.processing,false,profile,allow_directional?&measured:NULL);
#else
    (void)allow_directional;
    return comp_wba_microphone_profile_select(&b->microphone.processing,false,profile,NULL);
#endif
}
bool comp_v11_hal_microphone_audio_profile(const comp_v11_hal_t *b,uint8_t profile,comp_rec_audio_profile_t *out)
{
#if COMPANION_WBA_AUDIO_PROFILE
    static const uint8_t source[20]=COMP_WBA_AUDIO_SOURCE_BYTES;
    static const uint8_t calibration[32]=COMP_WBA_AUDIO_CALIBRATION_SHA_BYTES;
    return b && b->microphone.initialized && comp_wba_microphone_profile_snapshot(&b->microphone.processing,
        profile,COMPANION_WBA_APP_VERSION,source,calibration,out);
#else
    (void)b;(void)profile;(void)out;return false;
#endif
}
bool comp_v11_hal_microphone_enable(comp_v11_hal_t *b, bool enabled)
{
    bool ok;
    if (b == NULL) { return false; }
    if (enabled && b->microphone.running) { return true; }
    if (enabled && (b->faults & COMP_V11_FAULT_SPEAKER_SHUTDOWN) != 0u) { return false; }
#if COMPANION_WBA_DUAL_MIC_PROBE
    if(enabled){
        comp_wba_dual_probe_reset(&dual_probe);
        comp_wba_dual_probe_invalidate(&dual_probe); /* Failed start cannot reuse a previous take. */
    }
#endif
    if(enabled && !battery_capture_prepare(b)) {b->faults|=COMP_V11_FAULT_BATTERY;return false;}
    /* Optional gestures configure before PDM starts, never reset/configure the
     * shared SPI sensor in live capture. Missing IMU must not lose a recording. */
    if(enabled && b->imu.state==COMP_IMU_READY && !panel_holds_shared_bus(b) &&
       !comp_lsm6dso_set_pointer(&b->imu,false))b->faults|=COMP_V11_FAULT_IMU;
    if(enabled && b->imu.state==COMP_IMU_READY && !panel_holds_shared_bus(b) &&
       !comp_lsm6dso_set_recording_taps(&b->imu,true))b->faults|=COMP_V11_FAULT_IMU;
    ok = enabled ? comp_v11_microphone_hal_start(&b->microphone) : comp_v11_microphone_hal_stop(&b->microphone);
    if(!b->microphone.running && b->imu.state==COMP_IMU_READY && !panel_holds_shared_bus(b) &&
       !comp_lsm6dso_set_recording_taps(&b->imu,false))b->faults|=COMP_V11_FAULT_IMU;
#if COMPANION_WBA_DUAL_MIC_PROBE
    if(enabled&&ok){
        dual_probe_failure_baseline=dual_probe_failures(b);
        /* No observer means not measured, never silent/healthy second mic. */
        dual_probe.invalid=b->microphone.processing.config.observe_pair_frame?0u:1u;
    }
#endif
    if(!b->microphone.running)battery_capture_release(b);
    comp_power_policy_set_blocker(&b->power, COMP_POWER_BLOCKER_MIC_CAPTURE, b->microphone.running);
    comp_power_policy_set_blocker(&b->power,COMP_POWER_BLOCKER_BATTERY_SAMPLE,
        comp_wba_power_monitor_busy(&b->power_monitor)||comp_v11_battery_adc_busy());
    if (!ok) { b->faults |= COMP_V11_FAULT_MICROPHONE; }
    return ok;
}
bool comp_v11_hal_set_idle_peripherals(comp_v11_hal_t *b, bool idle)
{
    if (b == NULL) { return false; }
    if (imu_start_pending || b->imu.state != COMP_IMU_READY) {
        b->idle_peripherals = false;
        return false;
    }
    if (panel_holds_shared_bus(b)) { return false; }
    if (idle && (!comp_power_policy_idle_requested(&b->power) || b->microphone.running || b->playback_active ||
        comp_ssd1681_wba_status(&b->panel) == COMP_SSD1681_WBA_ACTIVE)) {
        return false;
    }
    if (b->idle_peripherals == idle && b->imu.idle_accel_only == idle) { return true; }
    if (!comp_lsm6dso_set_idle(&b->imu, idle,HAL_GetTick())) {
        b->faults |= COMP_V11_FAULT_IMU;
        b->idle_peripherals = false;
        return false;
    }
    b->idle_peripherals = idle;
    comp_power_policy_set_blocker(&b->power,COMP_POWER_BLOCKER_IMU_SETTLING,comp_lsm6dso_idle_settling(&b->imu));
    return true;
}
static bool panel_transfer(void *context, bool data, const uint8_t *bytes, uint16_t size)
{ (void)context; return comp_v11_hal_panel_transfer(data, bytes, size); }
static bool panel_busy(void *context)
{ (void)context; return comp_v11_hal_panel_busy(); }
static bool panel_allow_mode2_recovery(void *context)
{
    const comp_v11_hal_t *b = context;
    /* OP_RECORDING already services capture between every bounded row and
     * register poll, including the existing full-frame fallback. Keep that
     * same limit for one Mode2 paired rebuild. Ordinary frames overlapping
     * microphone start remain denied, as do playback/prepare/unsafe contexts. */
    return b != NULL && b == active_board && __get_IPSR() == 0u && !spi_owned &&
        (!b->microphone.running || comp_ssd1681_wba_recording_active(&b->panel)) &&
        !b->playback_active && !b->power_sampling_inhibited &&
        b->display_power.state == COMP_V11_POWER_READY;
}
static bool panel_reset(void *context, bool asserted)
{
    comp_v11_hal_t *b = context;
    return b->display_power.state == COMP_V11_POWER_READY && __get_IPSR() == 0u &&
           b->panel_reset != NULL && b->panel_reset(b->panel_reset_context, asserted);
}
static bool bind_panel(comp_v11_hal_t *b, comp_ssd1681_wba_reset_fn_t reset,
                       void *context, comp_ssd1681_wba_reset_mode_t mode)
{
    comp_ssd1681_wba_config_t config;
    if (!COMPANION_WBA_SCREEN_ENABLED || b == NULL || comp_ssd1681_wba_status(&b->panel) == COMP_SSD1681_WBA_ACTIVE ||
        (reset != NULL && b->display_power.state != COMP_V11_POWER_READY)) { return false; }
    b->panel_reset = reset; b->panel_reset_context = context;
    config = (comp_ssd1681_wba_config_t){
        .transfer = panel_transfer, .set_reset = reset != NULL ? panel_reset : NULL,
        .is_busy = panel_busy, .now_ms = now, .context = b,
        .payload_chunk_bytes = 128, .busy_timeout_ms = 5000,
        .partial_limit = UINT8_MAX, .reset_mode = mode
    };
    config.allow_mode2_recovery = panel_allow_mode2_recovery;
#if COMP_V11_PANEL_PASSIVE_TRACE
    config.take_busy_edges = panel_take_busy_edges;
#endif
    /* The restored production driver never consumes the legacy batching or
     * single-CS register callbacks. Leave their ABI slots zero; binding dead
     * functions would still retain them in the nearly full Flash image. */
#if COMP_V11_PANEL_SOFTWARE_SPI && COMP_V11_PANEL_STARTUP_READBACK
    config.observe_ready=panel_ready_observation;
#if COMP_V11_PANEL_SENSE_POWER || COMP_V11_PANEL_STATUS_GATE
    config.read_status=panel_read_ready_status;
#endif
#if COMP_V11_PANEL_START_RETRY
    config.check_activation_retry=panel_check_activation_retry;
#endif
#endif
    return comp_ssd1681_wba_init(&b->panel, &config);
}
bool comp_v11_hal_bind_panel_reset(comp_v11_hal_t *b,
                                    comp_ssd1681_wba_reset_fn_t reset, void *context)
{
    return bind_panel(b, reset, context, COMP_SSD1681_WBA_RESET_HARDWARE);
}
bool comp_v11_hal_bind_panel_software_reset(comp_v11_hal_t *b)
{
    return bind_panel(b, NULL, NULL, COMP_SSD1681_WBA_RESET_SOFTWARE_ONLY);
}
bool comp_v11_hal_init(comp_v11_hal_t *b)
{
    companion_spi_nor_stm32wba_config_t flash_config = {0};
    comp_speaker_config_t speaker_config = {amp, submit, activity, b};
    companion_touch_ft6336_stm32wba_config_t touch_config = {
        COMPANION_TOUCH_FT6336_STM32WBA_TARGET_WBA55, touch_probe, touch_read, touch_write, b
    };
    const comp_wba_pdm_config_t mic_config = {
        .layout = COMP_WBA_PDM_LAYOUT_LEFT_RIGHT_BYTES, .bit_order = COMP_WBA_PDM_MSB_FIRST,
        .decimation = COMP_V11_MIC_DECIMATION,
        /* Directional output is selected only by a prepared voice session.
         * Boot, meeting and finite independent-pair diagnostics stay LEFT. */
        .output = COMP_WBA_PDM_OUTPUT_LEFT,
        .selected_only = !COMPANION_WBA_DUAL_MIC_PROBE || COMPANION_WBA_DUAL_PAIR_CAPTURE,
        .gain_q15 = COMPANION_WBA_MICROPHONE_GAIN_Q15,
#if COMPANION_WBA_DUAL_MIC_PROBE && !COMPANION_WBA_DUAL_PAIR_CAPTURE
        /* Standalone diagnostic builds still explicitly request this probe.
         * Normal pair-capable builds bind it only through set_pair_sink. */
        .observe_pair_frame = microphone_pair_frame,
        .pair_pcm_storage = dual_pair_frame, .pair_pcm_capacity = 2u*COMP_WBA_PDM_PCM_FRAME_SAMPLES,
#endif
        .emit_pcm_frame = pcm_frame, .context = b
    }; /* First-board probe must validate raw order; keep channels separate until then. */
    if (b == NULL) { return false; }
    memset(b, 0, sizeof(*b)); active_board = b; HAL_Init();
    spi_owned = false;
    imu_start_pending = false;
#if COMP_V11_PANEL_SOFTWARE_SPI
    panel_gpio_active = false;
    panel_gpio_reading = false;
#endif
    comp_v11_panel_boot_idle();
    startup_storage_started = HAL_GetTick(); startup_storage_active = true;
    comp_v11_wake_events_init(&b->wake_events);
    comp_power_policy_init(&b->power);
    companion_v1_features_init(&b->features, HAL_GetTick());
    b->audio_clock_ready = clocks(); if (!b->audio_clock_ready) { b->faults |= COMP_V11_FAULT_CLOCK; }
    b->lse_ready = lse_probe(); if (!b->lse_ready) { b->faults |= COMP_V11_FAULT_LSE; }
    b->rng_ready = rng_init();
    pins();
    (void)HAL_ICACHE_ConfigAssociativityMode(ICACHE_1WAY);
    (void)HAL_ICACHE_Enable();
    __HAL_RCC_LPUART1_CONFIG(RCC_LPUART1CLKSOURCE_HSI); __HAL_RCC_LPUART1_CLK_ENABLE();
    debug_uart.Instance = LPUART1; debug_uart.Init.BaudRate = 115200;
    debug_uart.Init.WordLength = UART_WORDLENGTH_8B; debug_uart.Init.StopBits = UART_STOPBITS_1;
    debug_uart.Init.Parity = UART_PARITY_NONE; debug_uart.Init.Mode = UART_MODE_TX_RX;
    debug_uart.Init.HwFlowCtl = UART_HWCONTROL_NONE; debug_uart.Init.ClockPrescaler = UART_PRESCALER_DIV1;
    /* Buffer short physical service commands while the foreground renders or
     * handles BLE. Single-byte RX without FIFO loses a pasted PAIR line. */
    uart_ready = HAL_UART_Init(&debug_uart) == HAL_OK &&
        HAL_UARTEx_SetRxFifoThreshold(&debug_uart, UART_RXFIFO_THRESHOLD_1_8) == HAL_OK &&
        HAL_UARTEx_EnableFifoMode(&debug_uart) == HAL_OK;

    __HAL_RCC_I2C3_CONFIG(RCC_I2C3CLKSOURCE_HSI); __HAL_RCC_I2C1_CONFIG(RCC_I2C1CLKSOURCE_HSI);
    __HAL_RCC_I2C3_CLK_ENABLE();
    if(COMPANION_WBA_SCREEN_ENABLED)__HAL_RCC_I2C1_CLK_ENABLE();
    if (!i2c_init(&i2c_io, I2C3) || (COMPANION_WBA_SCREEN_ENABLED && !i2c_init(&i2c_touch, I2C1))) { b->faults |= COMP_V11_FAULT_IO; }
    HAL_Delay(1); HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_SET); HAL_Delay(1);
    const uint8_t io_inputs=COMPANION_WBA_SCREEN_ENABLED ? COMP_V11_TCA_INPUTS :
        (COMP_V11_TCA_INPUTS & ~COMP_V11_TP_INT);
    if (!comp_tca6408_init(&b->io, io_read, io_write, b, COMP_V11_TCA_ADDRESS, io_inputs, 0)) {
        b->faults |= COMP_V11_FAULT_IO;
    }
    /* Every output owner, including display power, shares this preflight.
     * io_write still rechecks the bus; an entered write failure stays locked. */
    b->io.admit_write = io_admit_write;
    wake_irqs_enable(b);
    comp_power_policy_set_button_wake_ready(&b->power,b->wake_irq_ready);
    (void)comp_v11_hal_configure_power(b,&comp_v11_qualified_power);
    /* The schematic has a P4-controlled 3V rail, but owner confirms its switch
     * is disabled on this assembled board. Keep the rail on and use 0x12;
     * never pretend the touch RESET signal also resets the EPD. */
    comp_v11_power_init_always_on(&b->display_power, &b->io);
    if(COMPANION_WBA_SCREEN_ENABLED) {
    (void)comp_v11_hal_bind_panel_software_reset(b);
    companion_touch_ft6336_stm32wba_init(&b->touch, &touch_config);
    if (!comp_v11_power_request(&b->display_power, true, HAL_GetTick())) { b->faults |= COMP_V11_FAULT_IO; }
    }
    __HAL_RCC_SPI3_CONFIG(RCC_SPI3CLKSOURCE_HSI);
    __HAL_RCC_SPI1_CLK_ENABLE(); __HAL_RCC_SPI3_CLK_ENABLE();
    if (!spi_init(&spi_shared, SPI1)) {
        b->faults |= COMP_V11_FAULT_IMU;
    } else {
#if COMP_V11_PANEL_DEFER_IMU_START
        imu_start_pending = true;
#else
        if (!comp_lsm6dso_start(&b->imu, imu_read, imu_write, b, HAL_GetTick())) {
            b->faults |= COMP_V11_FAULT_IMU;
        }
#endif
    }
    comp_motion_events_init(&b->motion);
    flash_config.target = COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55;
    flash_config.chip_select = flash_cs; flash_config.transfer = flash_transfer;
    flash_config.now_ms = now; flash_config.delay_ms = delay; flash_config.context = b;
    if (!spi_init(&spi_flash, SPI3) || !companion_spi_nor_stm32wba_init(&b->nor, &flash_config) ||
        companion_spi_nor_stm32wba_probe(&b->nor, NULL) != COMPANION_SPI_NOR_STM32WBA_OK ||
        b->nor.info.size_bytes != COMP_V11_NOR_BYTES) { b->faults |= COMP_V11_FAULT_NOR; }
    b->speaker_ready = b->audio_clock_ready && b->io.ready && speaker_init();
    comp_speaker_init(&b->speaker, &speaker_config);
    if (!b->speaker_ready) { b->faults |= COMP_V11_FAULT_AUDIO; }
    comp_v11_services_bind(&b->services, &b->features, &b->speaker, b->speaker_ready, &b->imu, &b->imu_sample);
    if (!b->audio_clock_ready || !comp_v11_microphone_hal_init(&b->microphone, &mic_config)) {
        b->faults |= COMP_V11_FAULT_MICROPHONE;
    }
    comp_power_policy_set_blocker(&b->power, COMP_POWER_BLOCKER_BOOT, false);
    return b->faults == 0;
}
void comp_v11_hal_speaker_poll(comp_v11_hal_t *b)
{
    uint32_t primask=__get_PRIMASK();uint8_t completion;
    __disable_irq();completion=speaker_completion;speaker_completion=0;
    __set_PRIMASK(primask);
    if(completion!=0u)comp_speaker_tx_complete(&b->speaker,completion==1u);
    else if(b->speaker.tx_pending &&
            HAL_GetTick()-speaker_submit_started_ms>=SPEAKER_DMA_DEADLINE_MS) {
        /* Existing failure callback stops block B DMA/amplifier and clears
         * activity. Microphone block A and shared SAI clocks are untouched. */
        b->faults|=COMP_V11_FAULT_AUDIO;
        comp_speaker_tx_complete(&b->speaker,false);
    }
    (void)comp_speaker_service(&b->speaker);
    /* Failed writes invalidate the output shadow. A read-only reconciliation
     * may restore it only when configuration and every other owner's latch
     * still match: a chip reset or unrelated changed output remains a fault. */
    if ((b->faults & COMP_V11_FAULT_SPEAKER_SHUTDOWN) != 0u && !b->microphone.running &&
        (b->power.blockers & (COMP_POWER_BLOCKER_MIC_CAPTURE | COMP_POWER_BLOCKER_STORAGE |
         COMP_POWER_BLOCKER_UPDATE | COMP_POWER_BLOCKER_RECORDING_TRANSFER |
         COMP_POWER_BLOCKER_BOND_NVM)) == 0u &&
        HAL_GetTick() - speaker_submit_started_ms >= SPEAKER_SHUTDOWN_RETRY_MS) {
        if (!b->io.ready) {
            uint8_t configuration, polarity, output;
            speaker_submit_started_ms = HAL_GetTick();
            if (b->io.read == NULL ||
                !b->io.read(b->io.context, b->io.address, 3u, &configuration) ||
                !b->io.read(b->io.context, b->io.address, 2u, &polarity) ||
                !b->io.read(b->io.context, b->io.address, 1u, &output) ||
                configuration != b->io.inputs || polarity != 0u ||
                ((output ^ b->io.outputs) & (0xffu ^ COMP_V11_AMP_ENABLE)) != 0u) return;
            b->io.outputs = output;
            b->io.ready = true;
        }
        /* Cube's SAI stop changes the handle to READY even when DMA abort
         * times out. A later stop will then skip that channel. Reinitialize
         * only the speaker DMA channel, and only after block B and its DMA
         * request have actually stopped. Never reset the shared SAI clock. */
        if (sai_speaker.Instance != NULL && dma_speaker.Instance != NULL &&
            (sai_speaker.Instance->CR1 & (SAI_xCR1_SAIEN | SAI_xCR1_DMAEN)) == 0u &&
            (dma_speaker.Instance->CCR & DMA_CCR_EN) != 0u) {
            const uint32_t irq_enabled = NVIC_GetEnableIRQ(GPDMA1_Channel0_IRQn);
            HAL_NVIC_DisableIRQ(GPDMA1_Channel0_IRQn);
            const bool dma_recovered = HAL_DMA_Init(&dma_speaker) == HAL_OK &&
                (dma_speaker.Instance->CCR & DMA_CCR_EN) == 0u;
            if (dma_recovered) {
                __HAL_DMA_CLEAR_FLAG(&dma_speaker, DMA_FLAG_TC | DMA_FLAG_HT |
                    DMA_FLAG_DTE | DMA_FLAG_ULE | DMA_FLAG_USE | DMA_FLAG_SUSP | DMA_FLAG_TO);
                HAL_NVIC_ClearPendingIRQ(GPDMA1_Channel0_IRQn);
            }
            if (irq_enabled != 0u) HAL_NVIC_EnableIRQ(GPDMA1_Channel0_IRQn);
            if (!dma_recovered) {
                speaker_submit_started_ms = HAL_GetTick();
                return;
            }
        }
        if (amp(b, false)) activity(b, false);
    }
}
#if defined(__GNUC__)
__attribute__((section(".sram1.bss"),aligned(8)))
#endif
static comp_v11_capture_hal_timing_t capture_hal_timing;
const comp_v11_capture_hal_timing_t *comp_v11_hal_capture_timing(void)
{return &capture_hal_timing;}
static uint32_t capture_hal_phase(uint32_t started,uint32_t *duration)
{
    uint32_t now=HAL_GetTick();*duration=now-started;return now;
}
static void imu_poll_with_recovery(comp_v11_hal_t *b, uint32_t tick)
{
    comp_power_policy_set_blocker(&b->power,COMP_POWER_BLOCKER_IMU_SETTLING,comp_lsm6dso_idle_settling(&b->imu));
    const bool recovery_allowed = !b->microphone.running && !b->playback_active &&
        !b->power_sampling_inhibited &&
        (b->power.blockers & (COMP_POWER_BLOCKER_MIC_CAPTURE | COMP_POWER_BLOCKER_PLAYBACK |
            COMP_POWER_BLOCKER_STORAGE | COMP_POWER_BLOCKER_UPDATE |
            COMP_POWER_BLOCKER_RECORDING_TRANSFER | COMP_POWER_BLOCKER_BOND_NVM)) == 0u;
    if (b->imu.state == COMP_IMU_FAULT) {
        b->faults |= COMP_V11_FAULT_IMU;
        b->idle_peripherals = false;
        b->sample_events = 0u;
        b->motion_event_flags = 0u;
        if (recovery_allowed && comp_lsm6dso_recover(&b->imu, tick)) {
            /* The reset returns to run mode. Preserve mounting calibration,
             * but discard pre-fault motion history instead of replaying a
             * pickup/shake from the first sample after a recovery gap. */
            const uint8_t axes = b->motion.screen_axes;
            comp_motion_events_init(&b->motion);
            (void)comp_motion_events_set_packed_axes(&b->motion, axes);
        }
        return;
    }
    /* A recording may begin between reset and the next poll. Defer the
     * recovery configuration burst too, not just the initial reset write. */
    if (b->imu.recovery_attempts != 0u && !recovery_allowed) return;
    if(recovery_allowed&&b->imu.state==COMP_IMU_READY&&b->imu.pointer_mode!=b->input_pointer_requested)
        (void)comp_lsm6dso_set_pointer(&b->imu,b->input_pointer_requested);
    if(recovery_allowed&&b->imu.state==COMP_IMU_READY&&
       b->imu.recording_taps!=b->input_taps_requested)
        (void)comp_lsm6dso_set_recording_taps(&b->imu,b->input_taps_requested);
    const comp_imu_poll_t result = comp_lsm6dso_poll(&b->imu, tick, &b->imu_sample);
    comp_power_policy_set_blocker(&b->power,COMP_POWER_BLOCKER_IMU_SETTLING,comp_lsm6dso_idle_settling(&b->imu));
    if (result == COMP_IMU_SAMPLE) {
        /* Only a real sample establishes recovery; READY alone does not. */
        b->faults &= ~COMP_V11_FAULT_IMU;
        uint8_t events = comp_motion_events_update(&b->motion, &b->imu_sample);
        if((b->imu.tap_source&COMP_LSM6DSO_DOUBLE_TAP)==COMP_LSM6DSO_DOUBLE_TAP)
            events|=COMP_MOTION_DOUBLE_TAP;
        b->sample_events |= events;
        if (events != 0u) { b->motion_event_flags = events; b->motion_event_ms = tick; }
    } else if (result == COMP_IMU_IO_ERROR) {
        b->faults |= COMP_V11_FAULT_IMU;
        b->idle_peripherals = false;
        b->sample_events = 0u;
        b->motion_event_flags = 0u;
    }
}
void comp_v11_hal_poll(comp_v11_hal_t *b)
{
    const bool measure=b->microphone.running;
    uint32_t phase_started=measure?HAL_GetTick():0u;
    const uint32_t poll_started=phase_started;
    uint32_t phase_ms[COMP_V11_CAPTURE_HAL_PHASES]={0};
    uint32_t tick = HAL_GetTick(), primask, wake_flags;
    if(COMPANION_WBA_SCREEN_ENABLED)panel_busy_trace(false);
    primask = __get_PRIMASK(); __disable_irq();
    wake_flags = comp_v11_wake_events_take_critical(&b->wake_events);
    __set_PRIMASK(primask);
    /* Keep wake ownership separate from Capture's timestamped key latch:
     * a full physical press may end before the next foreground sample. */
    if ((wake_flags & COMP_V11_WAKE_KEY_FALLING) != 0u) {
        b->key_wake_pending = true;
        b->key_wake_events++;
        b->key_wake_last_ms = tick;
    }
    comp_v11_hal_speaker_poll(b);
    if(measure)phase_started=capture_hal_phase(phase_started,&phase_ms[0]);
    if (b->microphone.initialized) {
        uint32_t started = HAL_GetTick();
        if (comp_v11_microphone_hal_poll(&b->microphone) == COMP_V11_MIC_POLL_ERROR) {
            b->faults |= COMP_V11_FAULT_MICROPHONE;
        }
        uint32_t elapsed = HAL_GetTick() - started;
        if (elapsed > b->microphone_max_poll_ms) { b->microphone_max_poll_ms = elapsed; }
        comp_power_policy_set_blocker(&b->power, COMP_POWER_BLOCKER_MIC_CAPTURE, b->microphone.running);
    }
    if(measure)phase_started=capture_hal_phase(phase_started,&phase_ms[1]);
    /* Only advance a conversion already in progress. Capture still wins: use
     * the same real DMA-window and <=1ms foreground gates as the old slot.
     * Never start an ADC, gate transaction, or second step in this early slot. */
    bool battery_serviced_early=false;
    if(b->microphone.running && comp_v11_battery_adc_busy() &&
       (!b->power_monitor.capture_gate || !b->power_monitor.sampling_enabled ||
        b->power_monitor.phase==COMP_WBA_BAT_CONVERT
#if COMPANION_WBA_BATTERY_LINEAR_ESTIMATE
        || (b->power_monitor.raw_diagnostic && b->power_monitor.phase==COMP_WBA_BAT_IDLE)
#endif
       ) &&
       comp_wba_power_poll_action(b->playback_active||b->power_sampling_inhibited,true,
          comp_v11_microphone_hal_io_window(&b->microphone),
          HAL_GetTick()-poll_started)==COMP_WBA_POWER_SERVICE) {
        battery_service_one_step(b);battery_serviced_early=true;
    }
    if(COMPANION_WBA_SCREEN_ENABLED)comp_v11_power_poll(&b->display_power, tick);
    if (COMPANION_WBA_SCREEN_ENABLED && comp_ssd1681_wba_poll(&b->panel) == COMP_SSD1681_WBA_ERROR) {
        b->faults |= COMP_V11_FAULT_PANEL;
    }
    comp_power_policy_set_blocker(&b->power, COMP_POWER_BLOCKER_SCREEN_WAIT,
        comp_ssd1681_wba_status(&b->panel) == COMP_SSD1681_WBA_ACTIVE);
    if(measure)phase_started=capture_hal_phase(phase_started,&phase_ms[2]);
    comp_cpu_stage_span_t cpu_inputs=comp_cpu_detail_begin();
#if COMP_V11_PANEL_DEFER_IMU_START
    const uint32_t startup_refreshes = b->panel.stats.completed_full +
        b->panel.stats.completed_partial + b->panel.stats.completed_fast;
    if (imu_start_pending && !b->microphone.running && !b->playback_active &&
        b->panel.status != COMP_SSD1681_WBA_ACTIVE &&
        (b->panel.status == COMP_SSD1681_WBA_ERROR ||
         startup_refreshes >= COMP_V11_PANEL_ISOLATION_REFRESHES ||
         tick - startup_storage_started >= COMP_V11_PANEL_ISOLATION_TIMEOUT_MS)) {
        /* Release after success OR failure, so an unavailable panel does not
         * permanently disable pickup sensing. The driver retains its error;
         * neither this release nor any probe counts as a visible frame. */
        char line[128];
        imu_start_pending = false;
        const bool started = comp_lsm6dso_start(&b->imu, imu_read, imu_write, b, HAL_GetTick());
        if (!started) b->faults |= COMP_V11_FAULT_IMU;
        (void)snprintf(line, sizeof(line),
            "PANEL7 imu_release panel_status=%u refreshes=%lu target=%u imu_started=%u now=%lu\r\n",
            (unsigned)b->panel.status, (unsigned long)startup_refreshes,
            (unsigned)COMP_V11_PANEL_ISOLATION_REFRESHES,
            (unsigned)started, (unsigned long)HAL_GetTick());
        (void)comp_v11_hal_debug_write(line);
        /* Do not poll RESET_WAIT with the earlier tick captured before start:
         * unsigned subtraction would misreport a 100ms reset timeout. */
        tick = HAL_GetTick();
    }
#endif
    if (!imu_start_pending && !panel_holds_shared_bus(b) &&
        ((wake_flags & COMP_V11_WAKE_TCA_FALLING) != 0u || tick - b->imu_poll_ms >= 10u)) {
        b->imu_poll_ms = tick;
        imu_poll_with_recovery(b, tick);
    }
    if(measure)phase_started=capture_hal_phase(phase_started,&phase_ms[3]);
    if(COMPANION_WBA_SCREEN_ENABLED)touch_report_complete(b,tick);
    if(measure)phase_started=capture_hal_phase(phase_started,&phase_ms[4]);
    /* Preserve the existing low-overhead recording cadence on unqualified
     * boards. Qualified charger inputs need margin within their 100 ms
     * freshness window; touch and expander edges keep their old cadence. */
    const uint32_t input_period = comp_wba_power_monitor_input_period_ms(
        &b->power_monitor, b->microphone.running, b->touch_sample.touch_count != 0u);
    if ((wake_flags & COMP_V11_WAKE_TCA_FALLING) != 0u || tick - b->input_poll_ms >= input_period) {
        bool io_sample_ok;

        b->input_poll_ms = tick;
        io_sample_ok = io_sample_inputs(b);
        comp_wba_power_monitor_inputs(&b->power_monitor,io_sample_ok,
            (b->expander_inputs & COMP_V11_CHARGE_PG)!=0u,
            (b->expander_inputs & COMP_V11_CHARGE_STAT)!=0u,tick);
        if (COMPANION_WBA_SCREEN_ENABLED && b->display_power.state == COMP_V11_POWER_READY) {
            if (!b->touch_ack && !b->microphone.running && !b->playback_active &&
                (b->power.blockers & (COMP_POWER_BLOCKER_STORAGE | COMP_POWER_BLOCKER_RECORDING_TRANSFER |
                                      COMP_POWER_BLOCKER_UPDATE | COMP_POWER_BLOCKER_BOND_NVM)) == 0u &&
                (b->touch_retry_ms == 0u || (int32_t)(tick - b->touch_retry_ms) >= 0) &&
                touch_recovery_ready(b, tick)) {
                b->touch_attempted = true;
                b->touch_retry_count++;
                b->touch_ack = touch_initialize(b);
                if (!b->touch_ack) {
                    touch_discovery_step(b);
                    b->touch_attempted = false;
                    b->touch_retry_ms = tick + TOUCH_RETRY_MS;
                    memset(&b->touch_sample, 0, sizeof(b->touch_sample));
                    b->faults |= COMP_V11_FAULT_TOUCH;
                } else {
                    b->touch_retry_ms = 0u;
                    b->faults &= ~COMP_V11_FAULT_TOUCH;
                }
            }
            /* Idle initialization performs several slow register exchanges.
             * Arm from the actual launch time, not the poll's pre-init tick. */
            if (b->touch_ack) touch_report_start(b,HAL_GetTick());
        } else {
            b->touch_ack = false;
            b->touch_attempted = false;
            b->touch_reset_phase = 0u;
            comp_power_policy_set_touch_wake_ready(&b->power, false);
            memset(&b->touch_sample, 0, sizeof(b->touch_sample));
        }
        comp_power_policy_set_touch_wake_ready(&b->power,
            io_sample_ok && b->io.ready && b->touch_ack && b->wake_irq_ready);
    }
    if(measure)phase_started=capture_hal_phase(phase_started,&phase_ms[5]);
    b->services.motion_flags = tick - b->motion_event_ms < 250u ? b->motion_event_flags : 0;
    const comp_wba_power_poll_action_t power_action=comp_wba_power_poll_action(
        b->playback_active||b->power_sampling_inhibited,b->microphone.running,
        !b->microphone.running||comp_v11_microphone_hal_io_window(&b->microphone),
        b->microphone.running?HAL_GetTick()-poll_started:0u);
    if(power_action==COMP_WBA_POWER_CANCEL) {
        comp_wba_power_monitor_poll(&b->power_monitor,false,HAL_GetTick());
        battery_reference_poll(b,false,HAL_GetTick());
    } else if(power_action==COMP_WBA_POWER_SERVICE && !battery_serviced_early) {
        /* A qualified capture borrows P7 without I2C. Raw/unknown profiles
         * retain internal VREF diagnostics only during capture. */
        battery_service_one_step(b);
    }
    comp_power_policy_set_blocker(&b->power,COMP_POWER_BLOCKER_BATTERY_SAMPLE,
        comp_wba_power_monitor_busy(&b->power_monitor)||comp_v11_battery_adc_busy());
    if(comp_v11_battery_active_fault((b->faults & COMP_V11_FAULT_BATTERY)!=0u,
        comp_v11_battery_adc_stats(),&b->power_monitor,comp_v11_battery_adc_busy()))
        b->faults|=COMP_V11_FAULT_BATTERY;
    else b->faults&=~COMP_V11_FAULT_BATTERY;
    if(measure)phase_started=capture_hal_phase(phase_started,&phase_ms[6]);
    (void)companion_v1_features_refresh_peripherals(&b->features, tick);
    comp_cpu_detail_end(COMP_CPU_STAGE_HAL_INPUTS,cpu_inputs,true);
    if(measure) {
        uint32_t end=capture_hal_phase(phase_started,&phase_ms[7]);
        uint32_t total=end-poll_started;
        if(capture_hal_timing.calls!=UINT32_MAX)++capture_hal_timing.calls;
        for(unsigned i=0;i<COMP_V11_CAPTURE_HAL_PHASES;++i)
            if(phase_ms[i]>capture_hal_timing.peak_ms[i])capture_hal_timing.peak_ms[i]=phase_ms[i];
        if(total>capture_hal_timing.peak_total_ms) {
            capture_hal_timing.peak_total_ms=total;
            memcpy(capture_hal_timing.worst_ms,phase_ms,sizeof(phase_ms));
        }
    }
}
#if COMP_V11_PANEL_SOFTWARE_SPI
/* WBA AF5 is PB4=SCK and PA15=MOSI, unlike the WB55 development board.
 * Keep software GPIO between panel packets; restore AF5 before IMU CS. */
static void __attribute__((noinline)) panel_gpio_delay(void)
{
    uint32_t cycles = panel_gpio_delay_waits;
#if COMP_V11_PANEL_IDLE_CLOCK_DIVIDER > 1u
    /* A communication-margin candidate for the failing translated panel bus.
     * Capture/playback and idle IMU transactions keep the original clock.
     * No interrupt is masked and each foreground RAM packet remains bounded. */
    if (active_board != NULL &&
        active_board->panel.status == COMP_SSD1681_WBA_ACTIVE &&
        !active_board->microphone.running && !active_board->playback_active)
        cycles *= COMP_V11_PANEL_IDLE_CLOCK_DIVIDER;
#endif
    /* Keep the zero check outside the bottom-tested loop. Under -Os a
     * top-tested dynamic countdown also retains a second branch. The final
     * ARM ELF must contain the verified NOP/SUBS/BNE loop body. */
    if (cycles == 0u) return;
    do { __NOP(); } while (--cycles != 0u);
}
/* GPIO_DELAY_CACHE_MODEL_BEGIN */
static void panel_gpio_refresh_delay(void)
{
    const uint32_t hz=SystemCoreClock;
    if(hz!=panel_gpio_delay_clock_hz || !panel_gpio_delay_waits) {
        panel_gpio_delay_waits=comp_v11_panel_gpio_delay_loops(hz);
        panel_gpio_delay_clock_hz=hz;
    }
}
/* GPIO_DELAY_CACHE_MODEL_END */
static void panel_gpio_begin(void)
{
    /* Initialize before the first edge, outside the bit loop. This also
     * covers shared GPIO IMU transactions and later core clock changes. */
    panel_gpio_refresh_delay();
    panel_busy_trace(false);
    /* Both slaves must be deselected before changing the shared clock's pin
     * mux. CS crosses a different translator from SCK/DC on this board. */
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0 | GPIO_PIN_15, GPIO_PIN_SET);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_11, GPIO_PIN_SET);
    panel_gpio_delay();
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_4, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_15, GPIO_PIN_RESET);
    if (!panel_gpio_active) {
        __HAL_SPI_DISABLE(&spi_shared);
        gpio(GPIOB, GPIO_PIN_4, GPIO_MODE_OUTPUT_PP, GPIO_NOPULL, 0);
        gpio(GPIOA, GPIO_PIN_15, GPIO_MODE_OUTPUT_PP, GPIO_NOPULL, 0);
        comp_v11_panel_gpio_slew();
        panel_gpio_active = true;
    }
}
static void panel_gpio_end(void)
{
    /* Close the mode-0 clock while selected, then retain the shared GPIO mux.
     * GPIO register ordering does not prove the translated electrical edges. */
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_4, GPIO_PIN_RESET);
    panel_gpio_delay();
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0, GPIO_PIN_SET);
    panel_gpio_delay();
    /* Park DC at data between transfers, including IMU clock activity. */
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_11, GPIO_PIN_SET);
    if (panel_gpio_reading) {
        gpio(GPIOA, GPIO_PIN_15, GPIO_MODE_OUTPUT_PP, GPIO_NOPULL, 0);
        comp_v11_panel_gpio_slew();
        panel_gpio_reading = false;
    }
    panel_busy_trace(true);
}
#if !COMP_V11_SHARED_SPI_GPIO
static void panel_gpio_to_hardware(void)
{
    if (!panel_gpio_active) return;
    /* Both slaves remain deselected through the mux handoff. The panel's
     * DC is parked at data, and its previous byte has already closed. */
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0 | GPIO_PIN_15, GPIO_PIN_SET);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_11, GPIO_PIN_SET);
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_4, GPIO_PIN_RESET);
    panel_gpio_delay();
    gpio(GPIOA, GPIO_PIN_15, GPIO_MODE_AF_PP, GPIO_NOPULL, GPIO_AF5_SPI1);
    gpio(GPIOB, GPIO_PIN_4, GPIO_MODE_AF_PP, GPIO_NOPULL, GPIO_AF5_SPI1);
    panel_gpio_delay();
    panel_gpio_active = false;
    panel_busy_trace(true);
}
#endif
static void panel_gpio_send(uint8_t byte)
{
    for (uint8_t bit = 0; bit < 8u; ++bit) {
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_4, GPIO_PIN_RESET);
        HAL_GPIO_WritePin(GPIOA, GPIO_PIN_15, (byte & 0x80u) ? GPIO_PIN_SET : GPIO_PIN_RESET);
        panel_gpio_delay();
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_4, GPIO_PIN_SET);
        panel_gpio_delay();
        byte <<= 1u;
    }
}
static uint8_t panel_gpio_receive(void)
{
    uint8_t byte = 0;
    for (uint8_t bit = 0; bit < 8u; ++bit) {
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_4, GPIO_PIN_RESET);
        panel_gpio_delay();
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_4, GPIO_PIN_SET);
        panel_gpio_delay();
        byte = (uint8_t)((byte << 1u) |
            (HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_15) == GPIO_PIN_SET ? 1u : 0u));
    }
    return byte;
}
#if COMP_V11_SHARED_SPI_GPIO
static uint8_t imu_gpio_exchange(uint8_t output)
{
    uint8_t input = 0u;
    /* Same mode-0 clock/data GPIO as the panel. IMU replies on PB3 rather
     * than the panel's bidirectional PA15, so MOSI stays an output. */
    for (uint8_t bit = 0u; bit < 8u; ++bit) {
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_4, GPIO_PIN_RESET);
        HAL_GPIO_WritePin(GPIOA, GPIO_PIN_15,
            (output & 0x80u) != 0u ? GPIO_PIN_SET : GPIO_PIN_RESET);
        panel_gpio_delay();
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_4, GPIO_PIN_SET);
        panel_gpio_delay();
        input = (uint8_t)((input << 1u) |
            (HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_3) == GPIO_PIN_SET ? 1u : 0u));
        output <<= 1u;
    }
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_4, GPIO_PIN_RESET);
    panel_gpio_delay();
    return input;
}
static bool imu_gpio_transfer(uint8_t reg, uint8_t *rx, const uint8_t *tx, size_t n)
{
    if (n == 0u || n > 32u || (rx == NULL && tx == NULL)) return false;
    panel_gpio_begin(); /* Both CS high, DC high, clock/data claimed as GPIO. */
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_15, GPIO_PIN_RESET);
    panel_gpio_delay();
    (void)imu_gpio_exchange(reg);
    for (size_t i = 0u; i < n; ++i) {
        const uint8_t value = imu_gpio_exchange(tx != NULL ? tx[i] : 0xFFu);
        if (rx != NULL) rx[i] = value;
    }
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_15, GPIO_PIN_SET);
    panel_gpio_delay();
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_15, GPIO_PIN_RESET);
    return true;
}
#endif
static void panel_gpio_read_begin(uint8_t command)
{
    panel_gpio_begin();
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_15, GPIO_PIN_SET);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_11, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0, GPIO_PIN_RESET);
    panel_gpio_send(command); /* Hold clock high through the SDIN turnaround. */
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_11, GPIO_PIN_SET);
    gpio(GPIOA, GPIO_PIN_15, GPIO_MODE_INPUT, GPIO_NOPULL, 0);
    panel_gpio_reading = true;
}
#if COMP_V11_PANEL_STARTUP_READBACK
static bool panel_probe_register(uint8_t command, const uint8_t *data, uint8_t size)
{
    /* Probe only at a ready checkpoint. Retain a guard on each packet so a
     * late BUSY assertion stops the probe instead of interrupting the chip. */
    if (comp_v11_hal_panel_busy()) return false;
    return comp_v11_hal_panel_transfer(false, &command, 1u) &&
        (size == 0u || (!comp_v11_hal_panel_busy() &&
                       comp_v11_hal_panel_transfer(true, data, size)));
}
#if COMP_V11_PANEL_SENSE_POWER || COMP_V11_PANEL_START_RETRY
static bool panel_read_ready_status(void *context, uint8_t *status)
{
    uint8_t values[3] = {0u, 0u, 0u};
    comp_v11_hal_t *b = context;
    if (status == NULL || b == NULL || b != active_board ||
        __get_IPSR() != 0u || spi_owned || b->microphone.running ||
        b->playback_active || b->display_power.state != COMP_V11_POWER_READY)
        return false;
    for (uint8_t i = 0u; i < 3u; ++i) {
        if (comp_v11_hal_panel_busy()) return false;
        spi_owned = true;
        panel_gpio_read_begin(0x2Fu);
        values[i] = panel_gpio_receive();
        panel_gpio_end();
        spi_owned = false;
    }
    *status = values[0];
    return values[0] == values[1] && values[1] == values[2] &&
        (values[0] & 0x07u) == 0x01u && !comp_v11_hal_panel_busy();
}
#endif
#if COMP_V11_PANEL_START_RETRY
static comp_ssd1681_wba_retry_check_t panel_check_activation_retry(void *context)
{
    comp_v11_hal_t *b = context;
    uint8_t before = 0u, after = 0u;
    uint16_t sampled = 0u, different = 0u, unstable = 0u, mismatch[2] = {0u, 0u};
    uint16_t first_bad[2] = {UINT16_MAX, UINT16_MAX};
    uint8_t first_actual[2] = {0u, 0u}, first_expected[2] = {0u, 0u};
    uint8_t row_bytes[COMP_SSD1681_WBA_BYTES_PER_ROW];
    char line[256];
    if (b == NULL || b != active_board || __get_IPSR() != 0u || spi_owned ||
        b->microphone.running || b->playback_active ||
        b->display_power.state != COMP_V11_POWER_READY ||
        b->panel.status != COMP_SSD1681_WBA_ACTIVE ||
        b->panel.previous_frame == NULL || b->panel.current_frame == NULL)
        return COMP_SSD1681_WBA_RETRY_DENIED;
    comp_ssd1681_wba_t *p = &b->panel;
    const comp_ssd1681_wba_window_t *w = &p->window;
    const bool ready_before = panel_read_ready_status(b, &before);
    bool ok = ready_before;
    uint16_t best_row = w->y_start, best_difference = 0u;
    /* Pick a changed row as well as both window boundaries. All-white samples
     * cannot qualify a retry. Each of at most 150 RAM bytes is read twice
     * from the same address; unstable readback cannot authorize a rewrite.
     * No frame buffer, waveform load or power-sensing command is used. */
    if (ok) {
        for (uint16_t y = w->y_start; y <= w->y_end; ++y) {
            uint16_t count = 0u;
            uint8_t old_row[COMP_SSD1681_WBA_BYTES_PER_ROW];
            if(!comp_ssd1681_wba_read_frame(p,p->previous_frame,(size_t)y*COMP_SSD1681_WBA_BYTES_PER_ROW,old_row,sizeof(old_row))) {
                ok=false;break;
            }
            for (uint8_t x = w->x_start_byte; x <= w->x_end_byte; ++x) {
                const size_t offset = (size_t)y * COMP_SSD1681_WBA_BYTES_PER_ROW + x;
                count += old_row[x] != p->current_frame[offset];
            }
            if (count > best_difference) { best_difference = count; best_row = y; }
        }
    }
    const uint16_t rows[3] = {w->y_start, best_row, w->y_end};
    for (uint8_t plane = 0u; plane < 2u && ok; ++plane) {
        /* 0x41 selects the RAM read plane: zero is BW/current, one is old. */
        const uint8_t *expected = plane == 0u ? p->current_frame : p->previous_frame;
        ok = panel_probe_register(0x44u, p->ram_x, sizeof(p->ram_x)) &&
             panel_probe_register(0x45u, p->ram_y, sizeof(p->ram_y)) &&
             panel_probe_register(0x41u, &plane, 1u);
        for (uint8_t row = 0u; row < 3u && ok; ++row) {
            if ((row > 0u && rows[row] == rows[0]) ||
                (row > 1u && rows[row] == rows[1])) continue;
            const uint16_t controller_y = COMP_SSD1681_WBA_HEIGHT - 1u - rows[row];
            uint8_t expected_row[COMP_SSD1681_WBA_BYTES_PER_ROW],old_row[COMP_SSD1681_WBA_BYTES_PER_ROW];
            const size_t base=(size_t)rows[row]*COMP_SSD1681_WBA_BYTES_PER_ROW;
            if(!comp_ssd1681_wba_read_frame(p,expected,base,expected_row,sizeof(expected_row)) ||
                !comp_ssd1681_wba_read_frame(p,p->previous_frame,base,old_row,sizeof(old_row))) {ok=false;break;}
            const uint8_t y_counter[2] = {(uint8_t)controller_y,
                                         (uint8_t)(controller_y >> 8u)};
            ok = panel_probe_register(0x4Eu, p->x_counter, sizeof(p->x_counter)) &&
                 panel_probe_register(0x4Fu, y_counter, sizeof(y_counter)) &&
                 !comp_v11_hal_panel_busy();
            if (!ok) break;
            spi_owned = true;
            panel_gpio_read_begin(0x27u);
            (void)panel_gpio_receive(); /* RAM read dummy byte. */
            for (uint8_t x = w->x_start_byte; x <= w->x_end_byte; ++x) {
                const size_t offset = (size_t)rows[row] * COMP_SSD1681_WBA_BYTES_PER_ROW + x;
                const uint8_t value = panel_gpio_receive();
                row_bytes[x - w->x_start_byte] = value;
                if (value != expected_row[x]) {
                    mismatch[plane]++;
                    if (first_bad[plane] == UINT16_MAX) {
                        first_bad[plane] = (uint16_t)offset;
                        first_actual[plane] = value;
                        first_expected[plane] = expected_row[x];
                    }
                }
                sampled++;
                if (plane == 0u)
                    different += old_row[x] != p->current_frame[offset];
            }
            panel_gpio_end();
            spi_owned = false;
            ok = panel_probe_register(0x4Eu, p->x_counter, sizeof(p->x_counter)) &&
                 panel_probe_register(0x4Fu, y_counter, sizeof(y_counter)) &&
                 !comp_v11_hal_panel_busy();
            if (!ok) break;
            spi_owned = true;
            panel_gpio_read_begin(0x27u);
            (void)panel_gpio_receive();
            for (uint8_t x = w->x_start_byte; x <= w->x_end_byte; ++x)
                unstable += panel_gpio_receive() != row_bytes[x - w->x_start_byte];
            panel_gpio_end();
            spi_owned = false;
            ok = !comp_v11_hal_panel_busy();
        }
    }
    const uint8_t current_plane = 0u;
    /* Restore the intended cursor even when a sample disagrees. A late BUSY
     * stops these ready-only writes and prevents activation recovery. */
    const bool restored = ready_before &&
        panel_probe_register(0x41u, &current_plane, 1u) &&
        panel_probe_register(0x4Eu, p->x_counter, sizeof(p->x_counter)) &&
        panel_probe_register(0x4Fu, p->y_counter, sizeof(p->y_counter));
    const bool ready_after = restored && panel_read_ready_status(b, &after);
    const bool reliable = ok && restored && ready_after && different != 0u && unstable == 0u;
    const bool qualified = reliable &&
        mismatch[0] == 0u && mismatch[1] == 0u;
    (void)snprintf(line, sizeof(line),
        "PANEL10 start_probe op=%u ready_before=%u ready_after=%u status=%02X,%02X sample_bytes=%u changed=%u current_mismatch=%u old_mismatch=%u restored=%u raw_busy=%u retry_qualified=%u now=%lu\r\n",
        (unsigned)p->operation, (unsigned)ready_before, (unsigned)ready_after,
        (unsigned)before, (unsigned)after, (unsigned)sampled, (unsigned)different,
        (unsigned)mismatch[0], (unsigned)mismatch[1], (unsigned)restored,
        (unsigned)comp_v11_hal_panel_busy(), (unsigned)qualified,
        (unsigned long)HAL_GetTick());
    (void)comp_v11_hal_debug_write(line);
    (void)snprintf(line, sizeof(line),
        "PANEL12 ram_detail stable=%u unstable=%u repair=%u current_offset=%u current_actual=%02X current_expected=%02X old_offset=%u old_actual=%02X old_expected=%02X\r\n",
        (unsigned)(ok && unstable == 0u), (unsigned)unstable,
        (unsigned)(reliable && !qualified && COMP_V11_PANEL_WINDOW_REPAIR),
        (unsigned)first_bad[0], (unsigned)first_actual[0], (unsigned)first_expected[0],
        (unsigned)first_bad[1], (unsigned)first_actual[1], (unsigned)first_expected[1]);
    (void)comp_v11_hal_debug_write(line);
    if (qualified) return COMP_SSD1681_WBA_RETRY_RAM_MATCHED;
#if COMP_V11_PANEL_WINDOW_REPAIR
    if (reliable) return COMP_SSD1681_WBA_RETRY_RAM_REWRITE;
#endif
    return COMP_SSD1681_WBA_RETRY_DENIED;
}
#endif
#if COMP_V11_PANEL_SENSE_POWER
static void panel_power_observation(const comp_ssd1681_wba_stats_t *s)
{
    char line[192];
    const bool qualified = s->mode2_power_status_valid &&
        s->mode2_power_busy_mask == 7u;
    (void)snprintf(line, sizeof(line),
        "PANEL8 mode2_power checks=%lu status=%02X read_valid=%u busy_mask=%u sensor_qualified=%u vci_floor_mv=2300 vci_low=%u hv_not_ready=%u\r\n",
        (unsigned long)s->mode2_power_checks, (unsigned)s->mode2_power_status,
        (unsigned)s->mode2_power_status_valid, (unsigned)s->mode2_power_busy_mask,
        (unsigned)qualified, (unsigned)((s->mode2_power_status & 0x10u) != 0u),
        (unsigned)((s->mode2_power_status & 0x20u) != 0u));
    (void)comp_v11_hal_debug_write(line);
}
#endif
#if COMP_V11_PANEL_STUCK_BUSY_AUDIT
static uint8_t panel_busy_sample_mask(void)
{
    uint8_t mask = 0u;
    for (uint8_t i = 0u; i < 8u; ++i) {
        if (comp_v11_hal_panel_busy()) mask |= (uint8_t)(1u << i);
        panel_gpio_delay();
    }
    return mask;
}
static void panel_stuck_start_observation(comp_v11_hal_t *b)
{
    static bool done;
    const uint32_t pull_mask = 3u << 24u;
    uint8_t status[3] = {0u, 0u, 0u}, before_reads = 0u, after_reads = 0u;
    char line[240];
    if (done || b->panel.stats.transfer_calls != 0u || !comp_v11_hal_panel_busy())
        return;
    done = true;
    const uint32_t original_pull = GPIOA->PUPDR & pull_mask;
    const unsigned raw_before = (unsigned)comp_v11_hal_panel_busy();
    /* Only weak input pulls change. PA12 never becomes an output. A strong
     * high under both pulls does not by itself identify the external source. */
    MODIFY_REG(GPIOA->PUPDR, pull_mask, 2u << 24u);
    for (uint8_t i = 0u; i < 32u; ++i) panel_gpio_delay();
    const uint8_t pull_down = panel_busy_sample_mask();
    MODIFY_REG(GPIOA->PUPDR, pull_mask, 1u << 24u);
    for (uint8_t i = 0u; i < 32u; ++i) panel_gpio_delay();
    const uint8_t pull_up = panel_busy_sample_mask();
    MODIFY_REG(GPIOA->PUPDR, pull_mask, original_pull);
    for (uint8_t i = 0u; i < 32u; ++i) panel_gpio_delay();
    const unsigned raw_restored = (unsigned)comp_v11_hal_panel_busy();
    /* Bounded engineering exception: the installer requires a confirmed
     * nonvisible 0x15 hang in the previous firmware, and this boot has waited
     * five seconds without sending a panel command. SSD1681 normally forbids
     * commands while BUSY. These three read-only 0x2F attempts may be ignored
     * or perturb the fault, so log raw BUSY around each attempt. Never use
     * their result to bypass the driver's visible BUSY high/low qualification.
     * No reset, RAM, voltage, activation or OTP command is sent here. */
    for (uint8_t i = 0u; i < 3u; ++i) {
        if (comp_v11_hal_panel_busy()) before_reads |= (uint8_t)(1u << i);
        spi_owned = true;
        panel_gpio_read_begin(0x2Fu);
        status[i] = panel_gpio_receive();
        panel_gpio_end();
        spi_owned = false;
        if (comp_v11_hal_panel_busy()) after_reads |= (uint8_t)(1u << i);
    }
    const bool valid = status[0] == status[1] && status[1] == status[2] &&
        (status[0] & 0xC8u) == 0u && (status[0] & 0x03u) == 0x01u;
    (void)snprintf(line, sizeof(line),
        "PANEL9 stuck_start raw_before=%u pull_down=%02X pull_up=%02X raw_restored=%u status=%02X,%02X,%02X read_valid=%u raw_read_before=%u raw_read_after=%u ic_busy=%u now=%lu\r\n",
        raw_before, (unsigned)pull_down, (unsigned)pull_up, raw_restored,
        (unsigned)status[0], (unsigned)status[1], (unsigned)status[2],
        (unsigned)valid, (unsigned)before_reads, (unsigned)after_reads,
        valid ? (unsigned)((status[0] & 0x04u) != 0u) : 255u,
        (unsigned long)HAL_GetTick());
    (void)comp_v11_hal_debug_write(line);
}
#endif
static void panel_ready_observation(void *context,
                                    comp_ssd1681_wba_observe_point_t point)
{
    static uint8_t attempts, mode2_observations, partial_observations;
    static bool observing_attempt;
    static const uint8_t patterns[2][8] = {
        {0xA5u, 0x5Au, 0x00u, 0xFFu, 0x81u, 0x7Eu, 0x3Cu, 0xC3u},
        {0x96u, 0x69u, 0xF0u, 0x0Fu, 0x18u, 0xE7u, 0x55u, 0xAAu},
    };
    comp_v11_hal_t *b = context;
    uint8_t status[3] = {0u, 0u, 0u}, read_mask = 0u;
    char line[176];
    if (b == NULL || b != active_board || __get_IPSR() != 0u || spi_owned ||
        b->microphone.running || b->playback_active ||
        b->display_power.state != COMP_V11_POWER_READY ||
        b->panel.status != COMP_SSD1681_WBA_ACTIVE)
        return;
#if COMP_V11_PANEL_STUCK_BUSY_AUDIT
    if (point == COMP_SSD1681_WBA_OBSERVE_STUCK_START) {
        panel_stuck_start_observation(b);
        return;
    }
#endif
#if COMP_V11_PANEL_SENSE_POWER
    if (point == COMP_SSD1681_WBA_OBSERVE_MODE2_POWER_CHECKED) {
        if (b->panel.stats.mode2_power_checks <= 4u)
            panel_power_observation(&b->panel.stats);
        return;
    }
#endif
    uint8_t observation = attempts;
    if (point == COMP_SSD1681_WBA_OBSERVE_RESET_READY) {
        observing_attempt = false;
        if (attempts >= 2u || b->panel.stats.completed_full != 0u) return;
        attempts++;
        observation = attempts;
        observing_attempt = true;
    } else if (point == COMP_SSD1681_WBA_OBSERVE_MODE1_READY) {
        if (!observing_attempt) return;
        observing_attempt = false;
    } else if (point == COMP_SSD1681_WBA_OBSERVE_MODE2_READY) {
        if (mode2_observations >= 2u) return;
        observation = ++mode2_observations;
    } else if (point == COMP_SSD1681_WBA_OBSERVE_PARTIAL_READY) {
        if (partial_observations >= 2u) return;
        observation = ++partial_observations;
    } else {
        return;
    }
    for (uint8_t i = 0u; i < 3u && !comp_v11_hal_panel_busy(); ++i) {
        spi_owned = true;
        panel_gpio_read_begin(0x2Fu);
        status[i] = panel_gpio_receive();
        panel_gpio_end();
        spi_owned = false;
        read_mask |= (uint8_t)(1u << i);
    }
    const bool valid = read_mask == 7u && status[0] == status[1] &&
        status[1] == status[2] && (status[0] & 0x07u) == 0x01u;
    (void)snprintf(line, sizeof(line),
        "PANEL6 point=%u attempt=%u isolated=%u imu_deferred=%u status=%02X,%02X,%02X valid=%u raw_busy=%u cmd=%02X now=%lu\r\n",
        (unsigned)point, (unsigned)observation, (unsigned)COMP_V11_PANEL_EXCLUSIVE_SPI,
        (unsigned)imu_start_pending,
        (unsigned)status[0], (unsigned)status[1], (unsigned)status[2],
        (unsigned)valid, (unsigned)comp_v11_hal_panel_busy(),
        (unsigned)b->panel.stats.last_command, (unsigned long)HAL_GetTick());
    (void)comp_v11_hal_debug_write(line);
    if (!valid || point != COMP_SSD1681_WBA_OBSERVE_MODE1_READY) return;

    /* An eight-byte write/read challenge in each RAM plane establishes that
     * commands, addresses and data reached the controller before activation.
     * No 0x20 is sent here. The normal full path subsequently overwrites both
     * complete planes and re-establishes its own window/counters. */
    uint8_t mismatches[2] = {0u, 0u}, completed = 0u;
    static const uint8_t entry[] = {1u}, ram_x[] = {0u, 24u};
    static const uint8_t ram_y[] = {199u, 0u, 0u, 0u};
    static const uint8_t x[] = {0u}, y[] = {199u, 0u};
    bool ok = panel_probe_register(0x11u, entry, sizeof(entry)) &&
        panel_probe_register(0x44u, ram_x, sizeof(ram_x)) &&
        panel_probe_register(0x45u, ram_y, sizeof(ram_y));
    for (uint8_t plane = 0u; ok && plane < 2u; ++plane) {
        const uint8_t command = plane == 0u ? 0x24u : 0x26u;
        ok = panel_probe_register(0x4Eu, x, sizeof(x)) &&
            panel_probe_register(0x4Fu, y, sizeof(y)) &&
            panel_probe_register(command, patterns[plane], sizeof(patterns[plane])) &&
            panel_probe_register(0x4Eu, x, sizeof(x)) &&
            panel_probe_register(0x4Fu, y, sizeof(y)) &&
            panel_probe_register(0x41u, &plane, 1u);
        if (!ok || comp_v11_hal_panel_busy()) break;
        spi_owned = true;
        panel_gpio_read_begin(0x27u);
        (void)panel_gpio_receive(); /* SSD1681: first RAM byte is dummy. */
        uint8_t read_bytes = 0u;
        while (read_bytes < sizeof(patterns[plane]) && !comp_v11_hal_panel_busy()) {
            mismatches[plane] += panel_gpio_receive() != patterns[plane][read_bytes];
            read_bytes++;
        }
        panel_gpio_end();
        spi_owned = false;
        if (read_bytes != sizeof(patterns[plane])) { ok = false; break; }
        completed |= (uint8_t)(1u << plane);
    }
    const uint8_t bw_plane = 0u;
    const bool restored = panel_probe_register(0x41u, &bw_plane, 1u);
    (void)snprintf(line, sizeof(line),
        "PANEL6 ram_probe bytes=8 planes=%u bw_mismatch=%u old_mismatch=%u restored=%u transport_confirmed=%u\r\n",
        (unsigned)completed, (unsigned)mismatches[0], (unsigned)mismatches[1],
        (unsigned)restored, (unsigned)(ok && completed == 3u && restored &&
            mismatches[0] == 0u && mismatches[1] == 0u));
    (void)comp_v11_hal_debug_write(line);
}
#endif
#endif
static bool panel_transfer_body(bool data, const uint8_t *bytes, uint16_t n)
{
    bool ok;
    if (bytes == NULL || n == 0u || spi_owned || __get_IPSR() != 0u || active_board == NULL ||
        active_board->display_power.state != COMP_V11_POWER_READY) { return false; }
    spi_owned = true;
#if COMP_V11_PANEL_SOFTWARE_SPI
    panel_gpio_begin();
#endif
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_15, GPIO_PIN_SET);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_11, data ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0, GPIO_PIN_RESET);
#if COMP_V11_PANEL_SOFTWARE_SPI
    panel_gpio_delay();
    for (uint16_t i = 0; i < n; ++i) { panel_gpio_send(bytes[i]); }
    panel_gpio_end(); ok = true;
#else
    ok = transfer(&spi_shared, bytes, NULL, n, 20);
#endif
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0, GPIO_PIN_SET); spi_owned = false; return ok;
}
bool comp_v11_hal_panel_transfer(bool data,const uint8_t *bytes,uint16_t n)
{
    comp_cpu_stage_span_t cpu=comp_cpu_detail_begin();
    bool ok=panel_transfer_body(data,bytes,n);
    comp_cpu_detail_panel_end(cpu,ok,n);
    return ok;
}
bool comp_v11_hal_panel_audit(const uint8_t *expected, uint16_t size)
{
#if COMP_V11_PANEL_SOFTWARE_SPI
    uint8_t status[3], options[11];
    uint32_t mismatch[2] = {0, 0}, digest[2] = {2166136261u, 2166136261u};
    char line[192], option_hex[23];
    if (expected == NULL || size != COMP_SSD1681_WBA_FRAME_BYTES || spi_owned ||
        __get_IPSR() != 0u || active_board == NULL || active_board->microphone.running ||
        active_board->playback_active || comp_v11_hal_panel_busy() ||
        active_board->display_power.state != COMP_V11_POWER_READY ||
        active_board->panel.status != COMP_SSD1681_WBA_COMPLETE) return false;
    for (uint8_t i = 0; i < 3u; ++i) {
        spi_owned = true; panel_gpio_read_begin(0x2Fu);
        status[i] = panel_gpio_receive(); panel_gpio_end(); spi_owned = false;
    }
    spi_owned = true; panel_gpio_read_begin(0x2Du);
    for (uint8_t i = 0; i < sizeof(options); ++i) { options[i] = panel_gpio_receive(); }
    panel_gpio_end(); spi_owned = false;
    for (uint8_t i = 0; i < sizeof(options); ++i) {
        (void)snprintf(option_hex + i * 2u, 3u, "%02X", (unsigned)options[i]);
    }
    const bool id_valid = status[0] == status[1] && status[1] == status[2] &&
        (status[0] & 0x07u) == 0x01u;
    (void)snprintf(line, sizeof(line), "PANEL1 bus=software status=%02X,%02X,%02X id_valid=%u options=%s\r\n",
        (unsigned)status[0], (unsigned)status[1], (unsigned)status[2], (unsigned)id_valid, option_hex);
    (void)comp_v11_hal_debug_write(line);
    if (!id_valid) return false; /* An all-00/FF wire read cannot prove RAM contents. */
    for (uint8_t plane = 0; plane < 2u; ++plane) {
        static const uint8_t ram_x[] = {0, 24}, ram_y[] = {199, 0, 0, 0};
        static const uint8_t x[] = {0}, y[] = {199, 0};
        bool ok = comp_v11_hal_panel_transfer(false, (const uint8_t[]){0x44}, 1) &&
            comp_v11_hal_panel_transfer(true, ram_x, sizeof(ram_x)) &&
            comp_v11_hal_panel_transfer(false, (const uint8_t[]){0x45}, 1) &&
            comp_v11_hal_panel_transfer(true, ram_y, sizeof(ram_y)) &&
            comp_v11_hal_panel_transfer(false, (const uint8_t[]){0x4E}, 1) &&
            comp_v11_hal_panel_transfer(true, x, sizeof(x)) &&
            comp_v11_hal_panel_transfer(false, (const uint8_t[]){0x4F}, 1) &&
            comp_v11_hal_panel_transfer(true, y, sizeof(y)) &&
            comp_v11_hal_panel_transfer(false, (const uint8_t[]){0x41}, 1) &&
            comp_v11_hal_panel_transfer(true, &plane, 1);
        if (!ok) return false;
        spi_owned = true; panel_gpio_read_begin(0x27u);
        (void)panel_gpio_receive(); /* SSD1681 RAM read starts with one dummy byte. */
        for (uint16_t i = 0; i < size; ++i) {
            uint8_t byte = panel_gpio_receive();
            mismatch[plane] += byte != expected[i];
            digest[plane] = (digest[plane] ^ byte) * 16777619u;
        }
        panel_gpio_end(); spi_owned = false;
    }
    (void)snprintf(line, sizeof(line), "PANEL1 ram_bytes=%u bw_mismatch=%lu old_mismatch=%lu bw_fnv=%08lX old_fnv=%08lX\r\n",
        (unsigned)size, (unsigned long)mismatch[0], (unsigned long)mismatch[1],
        (unsigned long)digest[0], (unsigned long)digest[1]);
    (void)comp_v11_hal_debug_write(line);
    return mismatch[0] == 0u && mismatch[1] == 0u;
#else
    (void)expected; (void)size; return false;
#endif
}
bool comp_v11_hal_panel_busy(void) { return HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_12) == GPIO_PIN_SET; }
#if COMP_V11_PANEL_STATUS_GATE
static void panel_status_gate_diagnostic(const comp_ssd1681_wba_stats_t *s)
{
    char line[192];
    (void)snprintf(line, sizeof(line),
        "PANEL13 activation_gate checks=%lu invalid=%lu qualified=%lu timeouts=%lu wait_max_ms=%lu status=%02X\r\n",
        (unsigned long)s->activation_gate_checks,
        (unsigned long)s->activation_gate_invalid,
        (unsigned long)s->activation_gate_qualified,
        (unsigned long)s->activation_gate_timeouts,
        (unsigned long)s->activation_gate_max_wait_ms,
        (unsigned)s->activation_gate_last_status);
    (void)comp_v11_hal_debug_write(line);
}
#endif
void comp_v11_hal_panel_failure_diagnostic(comp_v11_hal_t *b)
{
#if COMP_V11_PANEL_SOFTWARE_SPI && COMP_V11_PANEL_STARTUP_READBACK
    uint32_t rises, falls, rise_ms, fall_ms, bus_edges, quiet_edges;
    uint8_t status[3] = {0u, 0u, 0u};
    bool sampled = false;
    char line[320];
    if (b == NULL || b != active_board || __get_IPSR() != 0u ||
        b->microphone.running || b->playback_active || spi_owned ||
        b->panel.status != COMP_SSD1681_WBA_ERROR) return;
    /* Preserve the cached raw edge observation before the diagnostic SPI
     * read. This observation never changes driver completion or readiness. */
    panel_busy_trace(false);
    rises = panel_busy_rises; falls = panel_busy_falls;
    rise_ms = panel_busy_rise_ms; fall_ms = panel_busy_fall_ms;
    bus_edges = panel_busy_bus_edges; quiet_edges = panel_busy_quiet_edges;
    const bool raw_busy = comp_v11_hal_panel_busy();
    if (!raw_busy && b->display_power.state == COMP_V11_POWER_READY) {
        for (uint8_t i = 0u; i < 3u && !comp_v11_hal_panel_busy(); ++i) {
            spi_owned = true;
            panel_gpio_read_begin(0x2Fu);
            status[i] = panel_gpio_receive();
            panel_gpio_end();
            spi_owned = false;
            sampled = i == 2u;
        }
    }
    const bool valid = sampled && (status[0] & 0x03u) == 0x01u &&
        (status[1] & 0x03u) == 0x01u && (status[2] & 0x03u) == 0x01u;
    (void)snprintf(line, sizeof(line),
        "PANEL5 edge_mode=latched cmd=%02X cmd_ms=%lu raw_busy=%u pin_mode=%lu rise_samples=%lu fall_samples=%lu rise_sample_ms=%lu fall_sample_ms=%lu bus_edges=%lu quiet_edges=%lu status=%02X,%02X,%02X valid=%u io_out=%02X\r\n",
        (unsigned)b->panel.stats.last_command, (unsigned long)b->panel.stats.last_command_ms,
        (unsigned)raw_busy, (unsigned long)((GPIOA->MODER >> 24u) & 3u),
        (unsigned long)rises, (unsigned long)falls, (unsigned long)rise_ms,
        (unsigned long)fall_ms, (unsigned long)bus_edges, (unsigned long)quiet_edges,
        (unsigned)status[0], (unsigned)status[1], (unsigned)status[2],
        (unsigned)valid, (unsigned)b->io.outputs);
    (void)comp_v11_hal_debug_write(line);
#if COMP_V11_PANEL_STATUS_GATE
    panel_status_gate_diagnostic(&b->panel.stats);
#endif
#else
    (void)b;
#endif
}
bool comp_v11_hal_touch_read(uint8_t addr, uint8_t reg, uint8_t *data, uint16_t n)
{
    HAL_StatusTypeDef status;
    if (active_board == NULL || active_board->display_power.state != COMP_V11_POWER_READY ||
        data == NULL || n == 0u || __get_IPSR() != 0u) { return false; }
    if (!touch_bus_idle(active_board)) return false;
    active_board->touch_read_leg=0u;
    if (active_board->touch_stop_read) {
        const uint32_t started=HAL_GetTick();
        active_board->touch_read_leg=1u;
        status=HAL_I2C_Master_Transmit(&i2c_touch,(uint16_t)(addr<<1),&reg,1u,TOUCH_I2C_TIMEOUT_MS);
        if (status==HAL_OK) {
            /* FT6336U requires >=4.7 us bus-free between STOP and START.
             * At WBA55's <=100 MHz, even the NOPs alone exceed that minimum. */
            for (volatile unsigned gap=0;gap<640u;++gap) __NOP();
            const uint32_t elapsed=HAL_GetTick()-started;
            active_board->touch_read_leg=2u;
            if (elapsed>=TOUCH_I2C_TIMEOUT_MS) status=HAL_TIMEOUT;
            else if (!touch_bus_idle(active_board)) status=HAL_BUSY;
            else status=HAL_I2C_Master_Receive(&i2c_touch,(uint16_t)(addr<<1),data,n,TOUCH_I2C_TIMEOUT_MS-elapsed);
        }
    } else status = HAL_I2C_Mem_Read(&i2c_touch, (uint16_t)(addr << 1), reg, I2C_MEMADD_SIZE_8BIT,
                                   data, n, TOUCH_I2C_TIMEOUT_MS);
    active_board->touch_i2c_status = (uint8_t)status;
    active_board->touch_i2c_error = HAL_I2C_GetError(&i2c_touch);
    return status == HAL_OK;
}
bool comp_v11_hal_touch_diagnostic(const comp_v11_hal_t *b)
{
    char line[384];
    if (b == NULL || __get_IPSR() != 0u || b->microphone.running || b->playback_active) return false;
    (void)snprintf(line, sizeof(line),
        "TOUCH1 ack=%u stage=%u probes=%lu retries=%lu reads=%lu errors=%lu hal=%u i2c_error=%08lX rst_cmd=%u scl=%u sda=%u id_a3=%02X fw_a6=%02X id_a8=%02X contacts=%u x=%u y=%u downs=%lu last_ms=%lu last_x=%u last_y=%u resets=%lu reset_phase=%u\r\n",
        (unsigned)b->touch_ack, (unsigned)b->touch_init_stage,
        (unsigned long)b->touch.probe_count, (unsigned long)b->touch_retry_count,
        (unsigned long)b->touch.read_count, (unsigned long)b->touch.error_count,
        (unsigned)b->touch_i2c_status, (unsigned long)b->touch_i2c_error,
        (unsigned)((b->io.outputs & COMP_V11_TP_RESET) != 0u),
        (unsigned)(HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_2) == GPIO_PIN_SET),
        (unsigned)(HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_1) == GPIO_PIN_SET),
        (unsigned)b->touch.identity.cipher, (unsigned)b->touch.identity.firmware_id,
        (unsigned)b->touch.identity.chip_id, (unsigned)b->touch_sample.touch_count,
        (unsigned)b->touch_sample.x, (unsigned)b->touch_sample.y,
        (unsigned long)b->touch_down_count, (unsigned long)b->touch_last_contact_ms,
        (unsigned)b->touch_last_x, (unsigned)b->touch_last_y,
        (unsigned long)b->touch_reset_count, (unsigned)b->touch_reset_phase);
    const bool touch_written = comp_v11_hal_debug_write(line);
    (void)snprintf(line, sizeof(line),
        "TOUCH2 tca_valid=%u rst_tca=%u scan_count=%u scan_next=%02X scan_errors=%u ack_00_1f=%08lX ack_20_3f=%08lX ack_40_5f=%08lX ack_60_7f=%08lX stop_read=%u read_leg=%u\r\n",
        (unsigned)b->expander_input_valid,
        (unsigned)((b->expander_raw_inputs & COMP_V11_TP_RESET) != 0u),
        (unsigned)b->touch_scan_count, (unsigned)b->touch_scan_next,
        (unsigned)b->touch_scan_errors,
        (unsigned long)b->touch_scan_ack[0], (unsigned long)b->touch_scan_ack[1],
        (unsigned long)b->touch_scan_ack[2], (unsigned long)b->touch_scan_ack[3],
        (unsigned)b->touch_stop_read,(unsigned)b->touch_read_leg);
    const bool discovery_written = comp_v11_hal_debug_write(line);
    /* Idle diagnostic only: expose actual HAL clock tree, never log per frame. */
    (void)snprintf(line, sizeof(line),
        "CLOCK1 core_hz=%lu sysclk_hz=%lu hclk5_hz=%lu sai_hz=%lu\r\n",
        (unsigned long)SystemCoreClock, (unsigned long)HAL_RCC_GetSysClockFreq(),
        (unsigned long)HAL_RCC_GetHCLK5Freq(),
        (unsigned long)HAL_RCCEx_GetPeriphCLKFreq(RCC_PERIPHCLK_SAI1));
    (void)comp_v11_hal_debug_write(line);
    (void)snprintf(line,sizeof(line),
        "CLOCK2 flash_ws=%lu voltage_scale=%lu hclk_hz=%lu\r\n",
        (unsigned long)__HAL_FLASH_GET_LATENCY(),
        (unsigned long)HAL_PWREx_GetVoltageRange(),
        (unsigned long)HAL_RCC_GetHCLKFreq());
    (void)comp_v11_hal_debug_write(line);
    (void)snprintf(line,sizeof(line),
        "CLOCK3 icache_enabled=%u icache_ways=%u panel_software=%u panel_delay_loops=%lu idle_divider=%u\r\n",
        (unsigned)((ICACHE->CR&ICACHE_CR_EN)!=0u),
        (unsigned)((ICACHE->CR&ICACHE_CR_WAYSEL)?2u:1u),
        (unsigned)COMP_V11_PANEL_SOFTWARE_SPI,
#if COMP_V11_PANEL_SOFTWARE_SPI
        (unsigned long)panel_gpio_delay_waits,
#else
        0ul,
#endif
        (unsigned)COMP_V11_PANEL_IDLE_CLOCK_DIVIDER);
    (void)comp_v11_hal_debug_write(line);
    const comp_ssd1681_wba_stats_t *s = &b->panel.stats;
    (void)snprintf(line,sizeof(line),"PANELIO1 boot_scope=1 calls=%lu transferred_bytes=%lu\r\n",
        (unsigned long)s->transfer_calls,(unsigned long)s->transferred_bytes);
    (void)comp_v11_hal_debug_write(line);
    (void)snprintf(line, sizeof(line),
        "PANEL2 full=%lu partial=%lu fast=%lu recording=%lu first_error=%u first_stage=%u first_op=%u first_seq=%u first_busy=%u first_ms=%lu first_wait_ms=%lu\r\n",
        (unsigned long)s->completed_full, (unsigned long)s->completed_partial,
        (unsigned long)s->completed_fast, (unsigned long)s->completed_recording,
        (unsigned)s->first_failure_error, (unsigned)s->first_failure_stage,
        (unsigned)s->first_failure_operation, (unsigned)s->first_failure_sequence,
        (unsigned)s->first_failure_busy, (unsigned long)s->first_failure_ms,
        (unsigned long)s->first_failure_wait_ms);
    const bool panel_written = comp_v11_hal_debug_write(line);
#if COMP_V11_PANEL_PASSIVE_TRACE
    /* Cached first-gate evidence only, emitted by the existing idle logger.
     * No SPI, dense sampling, pin change or output during an active wait. */
    (void)snprintf(line, sizeof(line),
        "PANEL20 first_ready start_ms=%lu last_poll_ms=%lu samples=%lu high=%lu max_gap_ms=%lu max_quiet_ms=%lu rise_samples=%lu edges=%u\r\n",
        (unsigned long)s->first_ready_started_ms,
        (unsigned long)s->first_ready_last_poll_ms,
        (unsigned long)s->first_ready_samples,
        (unsigned long)s->first_ready_high_samples,
        (unsigned long)s->first_ready_max_poll_gap_ms,
        (unsigned long)s->first_ready_max_quiet_ms,
        (unsigned long)s->first_ready_rise_samples,
        (unsigned)s->first_ready_edge_flags);
    (void)comp_v11_hal_debug_write(line);
#endif
#if COMP_V11_PANEL_START_RETRY
    (void)snprintf(line, sizeof(line),
        "PANEL11 start_recovery misses=%lu retries=%lu completed=%lu ram_rewrites=%lu\r\n",
        (unsigned long)s->activation_start_misses,
        (unsigned long)s->activation_retries,
        (unsigned long)s->activation_recoveries,
        (unsigned long)s->activation_ram_rewrites);
    (void)comp_v11_hal_debug_write(line);
#endif
#if COMP_V11_PANEL_SOFTWARE_SPI && COMP_V11_PANEL_STARTUP_READBACK && COMP_V11_PANEL_SENSE_POWER
    panel_power_observation(s);
#endif
#if COMP_V11_PANEL_STATUS_GATE
    panel_status_gate_diagnostic(s);
#endif
    (void)snprintf(line, sizeof(line),
        "PANEL3 last_cmd=%02X cmd_ms=%lu complete_ms=%lu visible_wait_ms=%lu busy_edge_ms=%lu ready_glitches=%lu idle_busy_edges=%lu paired=%lu blink_rebases=%lu since_full=%lu full_ms=%lu start_max_ms=%lu delayed_starts=%lu\r\n",
        (unsigned)s->last_command, (unsigned long)s->last_command_ms,
        (unsigned long)s->last_completed_ms, (unsigned long)s->last_visible_wait_ms,
        (unsigned long)s->last_busy_change_ms, (unsigned long)s->ready_glitches,
        (unsigned long)s->idle_busy_edges, (unsigned long)s->completed_paired,
        (unsigned long)s->completed_blink_rebases,
        (unsigned long)s->mode2_since_full, (unsigned long)s->last_full_ms,
        (unsigned long)s->max_start_wait_ms, (unsigned long)s->delayed_starts);
    const bool timing_written = comp_v11_hal_debug_write(line);
    (void)snprintf(line, sizeof(line),
        "INPUT1 key_wakes=%lu last_ms=%lu raw_pressed=%u pending=%u\r\n",
        (unsigned long)b->key_wake_events, (unsigned long)b->key_wake_last_ms,
        (unsigned)comp_v11_hal_key_pressed(), (unsigned)b->key_wake_pending);
    return comp_v11_hal_debug_write(line) && timing_written && panel_written && touch_written && discovery_written;
}
bool comp_v11_hal_take_key_wake(comp_v11_hal_t *b)
{
    if (b == NULL) return false;
    const bool pending = b->key_wake_pending;
    b->key_wake_pending = false;
    return pending;
}
comp_wba_button_edges_t comp_v11_hal_take_key_edges(comp_v11_hal_t *b)
{
    comp_wba_button_edges_t edge={0};
    if(!b)return edge;
    uint32_t primask=__get_PRIMASK();__disable_irq();
    edge.down_ms=b->wake_events.key_down_ms;edge.up_ms=b->wake_events.key_up_ms;
    edge.flags=(uint8_t)((b->wake_events.key_pending>>1u)&3u);
    edge.raw_pressed=comp_v11_hal_key_pressed();b->wake_events.key_pending=0u;
    __set_PRIMASK(primask);return edge;
}
void comp_v11_hal_log(const char *message)
{ (void)comp_v11_hal_debug_write(message); }
#if COMPANION_WBA_IMU_RAW_UART
static uint8_t imu_uart_packet[32];
bool comp_v11_hal_debug_raw(const uint8_t *data,uint16_t length)
{
    if(!uart_ready||length!=sizeof(imu_uart_packet)||debug_uart.gState!=HAL_UART_STATE_READY)return false;
    memcpy(imu_uart_packet,data,length);
    HAL_NVIC_SetPriority(LPUART1_IRQn,6u,0u);HAL_NVIC_EnableIRQ(LPUART1_IRQn);
    return HAL_UART_Transmit_IT(&debug_uart,imu_uart_packet,length)==HAL_OK;
}
void LPUART1_IRQHandler(void){HAL_UART_IRQHandler(&debug_uart);}
void HAL_UART_TxCpltCallback(UART_HandleTypeDef *uart)
{if(uart==&debug_uart)HAL_NVIC_DisableIRQ(LPUART1_IRQn);}
#endif
bool comp_v11_hal_debug_write(const char *message)
{
    size_t length;
    if (!uart_ready || message == NULL || __get_IPSR() != 0u) return false;
    length=strlen(message);
#ifdef COMPANION_WBA_BLE_LINKED
    comp_v11_ble_console_idle_progress();
#endif
    comp_v11_reset_witness_uart_begin(message);
    const bool ok=length<=UINT16_MAX && HAL_UART_Transmit(&debug_uart,(const uint8_t*)message,(uint16_t)length,40u)==HAL_OK;
    comp_v11_reset_witness_uart_end();
#ifdef COMPANION_WBA_BLE_LINKED
    comp_v11_ble_console_idle_progress();
#endif
    return ok;
}
bool comp_v11_hal_debug_read(uint8_t *byte)
{
    if (!uart_ready || byte == NULL || __get_IPSR() != 0u) return false;
    if ((debug_uart.Instance->ISR & (UART_FLAG_ORE | UART_FLAG_FE | UART_FLAG_NE | UART_FLAG_PE)) != 0u) {
        __HAL_UART_CLEAR_FLAG(&debug_uart, UART_CLEAR_OREF | UART_CLEAR_FEF | UART_CLEAR_NEF | UART_CLEAR_PEF);
        /* Invalidates the command line until its newline: missing/noisy bytes
         * must not turn a malformed line into a valid pairing request. */
        *byte = 0u;
        return true;
    }
    if (__HAL_UART_GET_FLAG(&debug_uart, UART_FLAG_RXNE) == RESET) return false;
    return HAL_UART_Receive(&debug_uart, byte, 1u, 0u) == HAL_OK;
}
bool comp_v11_hal_key_pressed(void) { return HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_14) == GPIO_PIN_RESET; }
#if defined(COMPANION_WBA_CODEC_PROFILE) && COMPANION_WBA_CODEC_PROFILE
static struct {
    companion_codec_profile_t stats;
    uint32_t current[COMP_CODEC_PHASES], start, previous;
    unsigned phase;
    bool active;
} codec_wall __attribute__((section(".sram1.bss"),aligned(8)));
static bool codec_stamp(uint32_t *out)
{
    if (HAL_GetTickFreq()==HAL_TICK_FREQ_1KHZ) for(unsigned i=0;i<4u;++i) {
        uint32_t t=HAL_GetTick(),load=SysTick->LOAD,value=SysTick->VAL;
        bool pending=(SCB->ICSR&SCB_ICSR_PENDSTSET_Msk)!=0u;
        uint32_t after=HAL_GetTick(),v2=SysTick->VAL;
        if(comp_v11_ble_micro_consistent(t,after,load,value,v2)) {
            *out=comp_v11_ble_micro_stamp(t,load,value,pending);return true;
        }
    }
    ++codec_wall.stats.clock_fallbacks;return false;
}
void companion_codec_profile_begin(void)
{
    if(codec_wall.active)++codec_wall.stats.invalid;
    memset(codec_wall.current,0,sizeof(codec_wall.current));
    codec_wall.phase=0u;codec_wall.active=codec_stamp(&codec_wall.start);
    codec_wall.previous=codec_wall.start;
    if(!codec_wall.active)++codec_wall.stats.invalid;
}
void companion_codec_profile_mark(unsigned phase)
{
    uint32_t at;
    if(!codec_wall.active)return;
    if(phase!=codec_wall.phase+1u || phase>COMP_CODEC_PHASES || !codec_stamp(&at) ||
       at-codec_wall.previous>100000u) {
        ++codec_wall.stats.invalid;codec_wall.active=false;return;
    }
    codec_wall.current[codec_wall.phase]=at-codec_wall.previous;
    codec_wall.previous=at;codec_wall.phase=phase;
}
void companion_codec_profile_end(void)
{
    companion_codec_profile_mark(COMP_CODEC_PHASES);
    if(!codec_wall.active)return;
    companion_codec_profile_t *s=&codec_wall.stats;
    uint32_t total=codec_wall.previous-codec_wall.start;
    ++s->calls;s->total_us+=total;
    for(unsigned i=0;i<COMP_CODEC_PHASES;++i) {
        s->phase_total_us[i]+=codec_wall.current[i];
        if(codec_wall.current[i]>s->phase_peak_us[i])s->phase_peak_us[i]=codec_wall.current[i];
    }
    if(total>s->peak_total_us) {
        s->peak_total_us=total;memcpy(s->worst_us,codec_wall.current,sizeof(s->worst_us));
    }
    codec_wall.active=false;
}
const companion_codec_profile_t *companion_codec_profile_get(void)
{return &codec_wall.stats;}
#endif

void SysTick_Handler(void) {
#if COMPANION_WBA_CPU_RESIDENCE_PROFILE
    uint32_t cpu_mask=__get_PRIMASK();__disable_irq();
    comp_v11_cpu_irq_enter(true);
    HAL_IncTick();__set_PRIMASK(cpu_mask);
    comp_v11_cpu_irq_exit();
#else
    HAL_IncTick();
#endif
}
void EXTI13_IRQHandler(void) {
    comp_v11_cpu_irq_enter(false); HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_13); 
    comp_v11_cpu_irq_exit();
}
void EXTI14_IRQHandler(void) {
    comp_v11_cpu_irq_enter(false); HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_14); 
    comp_v11_cpu_irq_exit();
}
void HAL_GPIO_EXTI_Falling_Callback(uint16_t pin)
{
    if (active_board == NULL) { return; }
    if (pin == GPIO_PIN_13) {
        comp_v11_wake_events_note_isr(&active_board->wake_events,
                                      COMP_V11_WAKE_TCA_FALLING);
    } else if (pin == GPIO_PIN_14) {
        comp_v11_wake_events_note_key_isr(&active_board->wake_events,
                                      COMP_V11_WAKE_KEY_FALLING,HAL_GetTick());
    }
}
void HAL_GPIO_EXTI_Rising_Callback(uint16_t pin)
{
    if (active_board != NULL && pin == GPIO_PIN_14) {
        comp_v11_wake_events_note_key_isr(&active_board->wake_events,
                                      COMP_V11_WAKE_KEY_RISING,HAL_GetTick());
    }
}
void GPDMA1_Channel0_IRQHandler(void) {
    comp_v11_cpu_irq_enter(false); HAL_DMA_IRQHandler(&dma_speaker); 
    comp_v11_cpu_irq_exit();
}
void I2C1_EV_IRQHandler(void) {
    comp_v11_cpu_irq_enter(false); HAL_I2C_EV_IRQHandler(&i2c_touch); 
    comp_v11_cpu_irq_exit();
}
void I2C1_ER_IRQHandler(void) {
    comp_v11_cpu_irq_enter(false); HAL_I2C_ER_IRQHandler(&i2c_touch); 
    comp_v11_cpu_irq_exit();
}
void HAL_I2C_MasterTxCpltCallback(I2C_HandleTypeDef *bus)
{
    if (bus != &i2c_touch || touch_rx.phase != 1u) return;
    /* STOP-separated selector requires at least 4.7us bus-free. This bounded
     * transport-only gap is the existing board gap; no gesture work in IRQ. */
    for (volatile unsigned gap=0;gap<640u;++gap) __NOP();
    touch_rx.phase = 2u;
    touch_rx.start_status = (uint8_t)HAL_I2C_Master_Receive_IT(bus,
        (uint16_t)(COMP_FT6336_I2C_ADDRESS_7BIT<<1),touch_rx.report,sizeof(touch_rx.report));
    if (touch_rx.start_status != (uint8_t)HAL_OK) touch_rx.phase = 3u;
}
void GPDMA1_Channel1_IRQHandler(void)
{
    comp_v11_cpu_irq_enter(false); if (active_board != NULL) { comp_v11_microphone_hal_dma_irq(&active_board->microphone); } 
    comp_v11_cpu_irq_exit();
}
void SAI1_IRQHandler(void)
{
    comp_v11_cpu_irq_enter(false);
    if (sai_speaker.Instance != NULL) { HAL_SAI_IRQHandler(&sai_speaker); }
    if (active_board != NULL) { comp_v11_microphone_hal_sai_irq(&active_board->microphone); }

    comp_v11_cpu_irq_exit();
}
void HAL_SAI_TxCpltCallback(SAI_HandleTypeDef *sai)
{
    if (sai != &sai_speaker || speaker_completion==2u) return;
    comp_speaker_t *speaker=active_board?&active_board->speaker:NULL;
    const uint8_t next=speaker_prefilled;speaker_prefilled=0u;
    if (speaker && !active_board->microphone.running &&
        comp_speaker_cue_advance(speaker,next)) {
        if(speaker_probe[7]==2u) {
            uint16_t peak=0u;
            for(unsigned i=0u;i<COMP_SPEAKER_BLOCK_FRAMES*2u;++i) {
                int32_t value=speaker->tx_stereo[i];
                if(value<0)value=-value;
                if((uint32_t)value>peak)peak=(uint16_t)value;
            }
            if(peak) {speaker_probe_peak=peak;__DMB();speaker_probe[7]=3u;}
        }
        /* Cube normal-mode completion has retired this DMA and disabled its
         * SAI request/error IRQs, but leaves the serializer/FIFO running.
         * Re-arm the prepared block immediately. No synthesis, I2C, waits,
         * clock changes or amplifier operations in this completion ISR. */
        if (sai->State==HAL_SAI_STATE_READY && sai->ErrorCode==HAL_SAI_ERROR_NONE &&
            (sai->Instance->SR&SAI_FLAG_OVRUDR)==0u &&
            HAL_DMA_Start_IT(sai->hdmatx,(uint32_t)speaker->tx_stereo,
                (uint32_t)&sai->Instance->DR,sizeof(speaker->tx_stereo))==HAL_OK) {
            sai->pBuffPtr=(uint8_t *)speaker->tx_stereo;
            sai->XferSize=COMP_SPEAKER_BLOCK_FRAMES*2u;sai->XferCount=sai->XferSize;
            sai->State=HAL_SAI_STATE_BUSY_TX;
            __HAL_SAI_ENABLE_IT(sai,SAI_IT_OVRUDR|SAI_IT_WCKCFG);
            __DMB();sai->Instance->CR1|=SAI_xCR1_DMAEN;
            ++speaker->submitted_blocks;speaker_submit_started_ms=HAL_GetTick();
            return;
        }
        /* A real underrun/re-arm error is terminal, not silently cleared.
         * Foreground handles the amplifier's expander-backed shutdown. */
        speaker_completion=2u;
    } else {__DMB();speaker_completion=1u;}
}
void HAL_SAI_TxHalfCpltCallback(SAI_HandleTypeDef *sai)
{
    if (sai==&sai_speaker && speaker_completion!=2u && active_board &&
        !active_board->microphone.running)
        speaker_prefilled=comp_speaker_cue_prefill(&active_board->speaker);
}
void HAL_SAI_RxHalfCpltCallback(SAI_HandleTypeDef *sai)
{ if (active_board != NULL) { (void)comp_v11_microphone_hal_on_rx_half(&active_board->microphone, sai); } }
void HAL_SAI_RxCpltCallback(SAI_HandleTypeDef *sai)
{ if (active_board != NULL) { (void)comp_v11_microphone_hal_on_rx_complete(&active_board->microphone, sai); } }
void HAL_SAI_ErrorCallback(SAI_HandleTypeDef *sai)
{
    if (active_board != NULL && comp_v11_microphone_hal_on_error(&active_board->microphone, sai)) { return; }
    if (sai == &sai_speaker) { speaker_completion = 2; }
}
