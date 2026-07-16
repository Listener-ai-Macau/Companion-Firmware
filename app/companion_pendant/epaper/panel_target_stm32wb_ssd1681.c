#include "panel_target_stm32wb_ssd1681.h"

#include "expression_asset_source.h"
#include "refresh_policy.h"
#include "screen_framebuffer.h"
#include "screen_menu.h"

#include "main.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>

#ifndef COMPANION_EPAPER_SSD1681_CS_GPIO_PORT
#define COMPANION_EPAPER_SSD1681_CS_GPIO_PORT GPIOA
#endif
#ifndef COMPANION_EPAPER_SSD1681_CS_PIN
#define COMPANION_EPAPER_SSD1681_CS_PIN GPIO_PIN_6
#endif
#ifndef COMPANION_EPAPER_SSD1681_DC_GPIO_PORT
#define COMPANION_EPAPER_SSD1681_DC_GPIO_PORT GPIOB
#endif
#ifndef COMPANION_EPAPER_SSD1681_DC_PIN
#define COMPANION_EPAPER_SSD1681_DC_PIN GPIO_PIN_0
#endif
#ifndef COMPANION_EPAPER_SSD1681_RST_GPIO_PORT
#define COMPANION_EPAPER_SSD1681_RST_GPIO_PORT GPIOB
#endif
#ifndef COMPANION_EPAPER_SSD1681_RST_PIN
#define COMPANION_EPAPER_SSD1681_RST_PIN GPIO_PIN_1
#endif
#ifndef COMPANION_EPAPER_SSD1681_HAS_BUSY
#define COMPANION_EPAPER_SSD1681_HAS_BUSY 0
#endif
#ifndef COMPANION_EPAPER_SSD1681_BUSY_GPIO_PORT
#define COMPANION_EPAPER_SSD1681_BUSY_GPIO_PORT GPIOC
#endif
#ifndef COMPANION_EPAPER_SSD1681_BUSY_PIN
#define COMPANION_EPAPER_SSD1681_BUSY_PIN GPIO_PIN_5
#endif
#ifndef COMPANION_EPAPER_SSD1681_DIAGNOSTIC_PATTERN
#define COMPANION_EPAPER_SSD1681_DIAGNOSTIC_PATTERN 0u
#endif
#ifndef COMPANION_EPAPER_SSD1681_DIAGNOSTIC_REPEATS
#define COMPANION_EPAPER_SSD1681_DIAGNOSTIC_REPEATS 1u
#endif
#ifndef COMPANION_EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS
#define COMPANION_EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS 0u
#endif
#ifndef COMPANION_EPAPER_SSD1681_DIAGNOSTIC_PARTIAL
#define COMPANION_EPAPER_SSD1681_DIAGNOSTIC_PARTIAL 0u
#endif
#ifndef COMPANION_EPAPER_SSD1681_WIRE_PROBE
#define COMPANION_EPAPER_SSD1681_WIRE_PROBE 0u
#endif
#ifndef COMPANION_EPAPER_SSD1681_WIRE_PROBE_CYCLES
#define COMPANION_EPAPER_SSD1681_WIRE_PROBE_CYCLES 5u
#endif
#ifndef COMPANION_EPAPER_SSD1681_WIRE_PROBE_DWELL_MS
#define COMPANION_EPAPER_SSD1681_WIRE_PROBE_DWELL_MS 2000u
#endif
#ifndef COMPANION_EPAPER_SSD1681_USE_SOFTWARE_SPI
#define COMPANION_EPAPER_SSD1681_USE_SOFTWARE_SPI 1
#endif
#ifndef COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_DIAGNOSTIC
#define COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_DIAGNOSTIC 0
#endif
#ifndef COMPANION_EPAPER_SSD1681_DIRECT_GPIO_SPI_DIAGNOSTIC
#define COMPANION_EPAPER_SSD1681_DIRECT_GPIO_SPI_DIAGNOSTIC 0
#endif
#ifndef COMPANION_EPAPER_SSD1681_OFFICIAL_FULL_DIAGNOSTIC
#define COMPANION_EPAPER_SSD1681_OFFICIAL_FULL_DIAGNOSTIC 0
#endif
#ifndef COMPANION_EPAPER_SSD1681_VERBOSE_TRACE
#define COMPANION_EPAPER_SSD1681_VERBOSE_TRACE 0
#endif
#ifndef COMPANION_EPAPER_SSD1681_ROTATION_DEGREES
#define COMPANION_EPAPER_SSD1681_ROTATION_DEGREES 0u
#endif
#ifndef COMPANION_EPAPER_SSD1681_MIRROR_X
#define COMPANION_EPAPER_SSD1681_MIRROR_X 1u
#endif

#if COMPANION_EPAPER_SSD1681_ROTATION_DEGREES != 0u && \
    COMPANION_EPAPER_SSD1681_ROTATION_DEGREES != 180u
#error "SSD1681 rotation must be 0 or 180 degrees"
#endif
#if COMPANION_EPAPER_SSD1681_MIRROR_X != 0u && \
    COMPANION_EPAPER_SSD1681_MIRROR_X != 1u
#error "SSD1681 horizontal mirror must be 0 or 1"
#endif
#if COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_DIAGNOSTIC != 0 && \
    COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_DIAGNOSTIC != 1
#error "SSD1681 vendor partial diagnostic must be 0 or 1"
#endif
#if COMPANION_EPAPER_SSD1681_DIRECT_GPIO_SPI_DIAGNOSTIC != 0 && \
    COMPANION_EPAPER_SSD1681_DIRECT_GPIO_SPI_DIAGNOSTIC != 1
#error "SSD1681 direct GPIO SPI diagnostic must be 0 or 1"
#endif
#if COMPANION_EPAPER_SSD1681_OFFICIAL_FULL_DIAGNOSTIC != 0 && \
    COMPANION_EPAPER_SSD1681_OFFICIAL_FULL_DIAGNOSTIC != 1
#error "SSD1681 official full diagnostic must be 0 or 1"
#endif
#if COMPANION_EPAPER_SSD1681_OFFICIAL_FULL_DIAGNOSTIC != 0 && \
    COMPANION_EPAPER_SSD1681_DIAGNOSTIC_PATTERN != 1u && \
    COMPANION_EPAPER_SSD1681_DIAGNOSTIC_PATTERN != 2u
#error "SSD1681 official full diagnostic requires a white or black pattern"
#endif
#if COMPANION_EPAPER_SSD1681_VERBOSE_TRACE != 0 && \
    COMPANION_EPAPER_SSD1681_VERBOSE_TRACE != 1
#error "SSD1681 verbose trace must be 0 or 1"
#endif

#if COMPANION_EPAPER_SSD1681_VERBOSE_TRACE
#define SSD1681_VERBOSE_TRACE(...) printf(__VA_ARGS__)
#else
/* Keep format arguments visible to the compiler, but remove the synchronous
 * UART call and its format strings from optimized production images. */
#define SSD1681_VERBOSE_TRACE(...) do { if (0) { printf(__VA_ARGS__); } } while (0)
#endif

#define SSD1681_WIDTH 200u
#define SSD1681_HEIGHT 200u
#define SSD1681_BYTES_PER_ROW (SSD1681_WIDTH / 8u)
#define SSD1681_FRAME_BYTES (SSD1681_BYTES_PER_ROW * SSD1681_HEIGHT)
/* Good Display's matching STM32 example waits while BUSY is high and proceeds low. */
#define SSD1681_BUSY_READY_LEVEL GPIO_PIN_RESET
#define SSD1681_REFRESH_START_TIMEOUT_MS 100u
#define SSD1681_READY_TIMEOUT_MS 5000u
#define SSD1681_VENDOR_FAST_PROFILE_NAME "good_display_mode1"
#define SSD1681_VENDOR_FAST_TEMPERATURE_LSB 0x64u

extern SPI_HandleTypeDef hspi2;

static uint8_t s_frame[SSD1681_FRAME_BYTES];
static uint8_t s_previous_frame[SSD1681_FRAME_BYTES];
static bool s_previous_frame_valid;
static bool s_controller_initialized;
static uint32_t s_refresh_activation_count;

typedef struct {
    uint8_t x_start_byte;
    uint8_t x_end_byte;
    uint16_t y_start;
    uint16_t y_end;
    bool changed;
} ssd1681_window_t;
typedef struct {
    comp_epaper_expression_asset_source_t *expression_assets;
    comp_epaper_refresh_policy_t refresh_policy;
    companion_epaper_wait_service_fn wait_service;
    void *wait_service_context;
    uint32_t wait_service_next_ms;
    uint16_t wait_service_period_ms;
} ssd1681_target_context_t;

static ssd1681_target_context_t s_target_context;
#if COMPANION_EPAPER_SSD1681_WIRE_PROBE != 0u
static bool s_wire_probe_complete;
#endif

static void ssd1681_service_wait(void)
{
    uint32_t now = HAL_GetTick();

    if (s_target_context.wait_service == NULL ||
        (int32_t)(now - s_target_context.wait_service_next_ms) < 0) {
        return;
    }
    s_target_context.wait_service_next_ms =
        now + s_target_context.wait_service_period_ms;
    s_target_context.wait_service(s_target_context.wait_service_context, now);
}

static void ssd1681_select(bool selected)
{
    HAL_GPIO_WritePin(COMPANION_EPAPER_SSD1681_CS_GPIO_PORT,
                      COMPANION_EPAPER_SSD1681_CS_PIN,
                      selected ? GPIO_PIN_RESET : GPIO_PIN_SET);
}

static const char *ssd1681_spi_transport_name(void)
{
#if COMPANION_EPAPER_SSD1681_USE_SOFTWARE_SPI
#if COMPANION_EPAPER_SSD1681_DIRECT_GPIO_SPI_DIAGNOSTIC
    return "software_direct_bsrr_diagnostic";
#else
    return "software_vendor_edges";
#endif
#else
    return "hardware";
#endif
}

static bool ssd1681_spi_tx(const uint8_t *data, uint16_t length)
{
    if (data == NULL || length == 0u) {
        return true;
    }
#if COMPANION_EPAPER_SSD1681_USE_SOFTWARE_SPI
#if COMPANION_EPAPER_SSD1681_DIRECT_GPIO_SPI_DIAGNOSTIC
    const uint32_t sck_low = (uint32_t)GPIO_PIN_9 << 16u;
    const uint32_t sck_high = GPIO_PIN_9;
    const uint32_t mosi_low = (uint32_t)GPIO_PIN_1 << 16u;
    const uint32_t mosi_high = GPIO_PIN_1;

    /* Diagnostic-only transport A/B: keep the verified CPOL/CPHA edge order,
     * but use the same direct BSRR writes as the vendor's bit-banged example.
     * It can raise the edge rate, so real-panel BUSY and residual evidence are
     * required before this implementation can replace software_vendor_edges. */
    for (uint16_t index = 0u; index < length; ++index) {
        uint8_t value = data[index];
        for (uint8_t bit = 0u; bit < 8u; ++bit) {
            GPIOA->BSRR = sck_low;
            GPIOC->BSRR = (value & 0x80u) != 0u ? mosi_high : mosi_low;
            __NOP();
            __NOP();
            GPIOA->BSRR = sck_high;
            __NOP();
            __NOP();
            value <<= 1u;
        }
    }
    GPIOA->BSRR = sck_low;
    return true;
#else
    for (uint16_t index = 0u; index < length; ++index) {
        uint8_t value = data[index];
        for (uint8_t bit = 0u; bit < 8u; ++bit) {
            HAL_GPIO_WritePin(GPIOA, GPIO_PIN_9, GPIO_PIN_RESET);
            HAL_GPIO_WritePin(GPIOC,
                              GPIO_PIN_1,
                              (value & 0x80u) != 0u ? GPIO_PIN_SET : GPIO_PIN_RESET);
            __NOP();
            __NOP();
            HAL_GPIO_WritePin(GPIOA, GPIO_PIN_9, GPIO_PIN_SET);
            __NOP();
            __NOP();
            value <<= 1u;
        }
    }
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_9, GPIO_PIN_RESET);
    return true;
#endif
#else
    return HAL_SPI_Transmit(&hspi2, (uint8_t *)data, length, 1000u) == HAL_OK;
#endif
}

static bool ssd1681_command(uint8_t command)
{
    HAL_GPIO_WritePin(COMPANION_EPAPER_SSD1681_DC_GPIO_PORT,
                      COMPANION_EPAPER_SSD1681_DC_PIN,
                      GPIO_PIN_RESET);
    ssd1681_select(true);
    bool ok = ssd1681_spi_tx(&command, 1u);
    ssd1681_select(false);
    return ok;
}

static bool ssd1681_data(const uint8_t *data, uint16_t length)
{
    HAL_GPIO_WritePin(COMPANION_EPAPER_SSD1681_DC_GPIO_PORT,
                      COMPANION_EPAPER_SSD1681_DC_PIN,
                      GPIO_PIN_SET);
    ssd1681_select(true);
    bool ok = ssd1681_spi_tx(data, length);
    ssd1681_select(false);
    return ok;
}

static bool ssd1681_command_data(uint8_t command, const uint8_t *data, uint16_t length)
{
    return ssd1681_command(command) && ssd1681_data(data, length);
}

#if !COMPANION_EPAPER_SSD1681_HAS_BUSY
static void ssd1681_observe_refresh_busy(uint32_t duration_ms);
#endif
static int ssd1681_busy_level(void);

static bool ssd1681_wait_ready(uint32_t fallback_delay_ms, uint32_t timeout_ms)
{
#if COMPANION_EPAPER_SSD1681_HAS_BUSY
    (void)fallback_delay_ms;
    uint32_t start = HAL_GetTick();
    int initial_level = ssd1681_busy_level();
    while (HAL_GPIO_ReadPin(COMPANION_EPAPER_SSD1681_BUSY_GPIO_PORT,
                            COMPANION_EPAPER_SSD1681_BUSY_PIN) != SSD1681_BUSY_READY_LEVEL) {
        if ((HAL_GetTick() - start) > timeout_ms) {
            printf("[epaper] ready_wait initial=%d final=%d elapsed_ms=%lu ready=0\r\n",
                   initial_level,
                   ssd1681_busy_level(),
                   (unsigned long)(HAL_GetTick() - start));
            return false;
        }
        ssd1681_service_wait();
        HAL_Delay(1u);
    }
    SSD1681_VERBOSE_TRACE("[epaper] ready_wait initial=%d final=%d elapsed_ms=%lu ready=1\r\n",
           initial_level,
           ssd1681_busy_level(),
           (unsigned long)(HAL_GetTick() - start));
    return true;
#else
    (void)timeout_ms;
    HAL_Delay(fallback_delay_ms);
    return true;
#endif
}

static bool ssd1681_wait_refresh_complete(uint32_t fallback_delay_ms, uint32_t timeout_ms)
{
#if COMPANION_EPAPER_SSD1681_HAS_BUSY
    (void)fallback_delay_ms;
    uint32_t start = HAL_GetTick();
    bool observed_busy = false;

    while ((HAL_GetTick() - start) <= timeout_ms) {
        bool ready = HAL_GPIO_ReadPin(COMPANION_EPAPER_SSD1681_BUSY_GPIO_PORT,
                                      COMPANION_EPAPER_SSD1681_BUSY_PIN) ==
                     SSD1681_BUSY_READY_LEVEL;
        if (!ready) {
            observed_busy = true;
        } else if (observed_busy) {
            return true;
        } else if ((HAL_GetTick() - start) > SSD1681_REFRESH_START_TIMEOUT_MS) {
            return false;
        }
        ssd1681_service_wait();
        HAL_Delay(1u);
    }
    return false;
#else
    (void)timeout_ms;
    ssd1681_observe_refresh_busy(fallback_delay_ms);
    return true;
#endif
}

static int ssd1681_busy_level(void)
{
    return HAL_GPIO_ReadPin(COMPANION_EPAPER_SSD1681_BUSY_GPIO_PORT,
                            COMPANION_EPAPER_SSD1681_BUSY_PIN) == GPIO_PIN_SET ? 1 : 0;
}

#if !COMPANION_EPAPER_SSD1681_HAS_BUSY
static void ssd1681_observe_refresh_busy(uint32_t duration_ms)
{
    uint32_t start = HAL_GetTick();
    int first = ssd1681_busy_level();
    int previous = first;
    uint32_t transitions = 0u;
    uint32_t busy_active_ms = 0u;

    while ((HAL_GetTick() - start) < duration_ms) {
        int level = ssd1681_busy_level();
        if (level != previous) {
            ++transitions;
            previous = level;
        }
        if (level != (SSD1681_BUSY_READY_LEVEL == GPIO_PIN_SET ? 1 : 0)) {
            ++busy_active_ms;
        }
        ssd1681_service_wait();
        HAL_Delay(1u);
    }

    SSD1681_VERBOSE_TRACE("[epaper] busy_observe start=%d end=%d transitions=%lu busy_active_ms=%lu\r\n",
           first,
           ssd1681_busy_level(),
           (unsigned long)transitions,
           (unsigned long)busy_active_ms);
}
#endif

static void ssd1681_gpio_init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();

#if COMPANION_EPAPER_SSD1681_USE_SOFTWARE_SPI
    (void)HAL_SPI_DeInit(&hspi2);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_9, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_1, GPIO_PIN_RESET);

    GPIO_InitStruct.Pin = GPIO_PIN_9;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    GPIO_InitStruct.Pin = GPIO_PIN_1;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);
#endif

    HAL_GPIO_WritePin(COMPANION_EPAPER_SSD1681_CS_GPIO_PORT,
                      COMPANION_EPAPER_SSD1681_CS_PIN,
                      GPIO_PIN_SET);
    HAL_GPIO_WritePin(COMPANION_EPAPER_SSD1681_DC_GPIO_PORT,
                      COMPANION_EPAPER_SSD1681_DC_PIN,
                      GPIO_PIN_SET);
    HAL_GPIO_WritePin(COMPANION_EPAPER_SSD1681_RST_GPIO_PORT,
                      COMPANION_EPAPER_SSD1681_RST_PIN,
                      GPIO_PIN_SET);

    GPIO_InitStruct.Pin = COMPANION_EPAPER_SSD1681_CS_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(COMPANION_EPAPER_SSD1681_CS_GPIO_PORT, &GPIO_InitStruct);

    GPIO_InitStruct.Pin = COMPANION_EPAPER_SSD1681_DC_PIN;
    HAL_GPIO_Init(COMPANION_EPAPER_SSD1681_DC_GPIO_PORT, &GPIO_InitStruct);

    GPIO_InitStruct.Pin = COMPANION_EPAPER_SSD1681_RST_PIN;
    HAL_GPIO_Init(COMPANION_EPAPER_SSD1681_RST_GPIO_PORT, &GPIO_InitStruct);

    GPIO_InitStruct.Pin = COMPANION_EPAPER_SSD1681_BUSY_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(COMPANION_EPAPER_SSD1681_BUSY_GPIO_PORT, &GPIO_InitStruct);
}

#if COMPANION_EPAPER_SSD1681_WIRE_PROBE != 0u
static void ssd1681_wire_probe(void)
{
    GPIO_TypeDef *port;
    uint16_t pin;
    const char *label;
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    ssd1681_gpio_init();

#if COMPANION_EPAPER_SSD1681_WIRE_PROBE == 1u
    port = COMPANION_EPAPER_SSD1681_CS_GPIO_PORT;
    pin = COMPANION_EPAPER_SSD1681_CS_PIN;
    label = "CS P9-T7 PA6";
#elif COMPANION_EPAPER_SSD1681_WIRE_PROBE == 2u
    port = COMPANION_EPAPER_SSD1681_DC_GPIO_PORT;
    pin = COMPANION_EPAPER_SSD1681_DC_PIN;
    label = "DC P9-T6 PB0";
#elif COMPANION_EPAPER_SSD1681_WIRE_PROBE == 3u
    port = COMPANION_EPAPER_SSD1681_RST_GPIO_PORT;
    pin = COMPANION_EPAPER_SSD1681_RST_PIN;
    label = "RES P9-T5 PB1";
#elif COMPANION_EPAPER_SSD1681_WIRE_PROBE == 4u
    (void)HAL_SPI_DeInit(&hspi2);
    port = GPIOA;
    pin = GPIO_PIN_9;
    label = "SCK P8-3 PA9";
#elif COMPANION_EPAPER_SSD1681_WIRE_PROBE == 5u
    (void)HAL_SPI_DeInit(&hspi2);
    port = GPIOC;
    pin = GPIO_PIN_1;
    label = "MOSI P8-6 PC1";
#else
#error "Unsupported COMPANION_EPAPER_SSD1681_WIRE_PROBE"
#endif

    GPIO_InitStruct.Pin = pin;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(port, &GPIO_InitStruct);

    printf("[epaper] wire_probe signal=%s cycles=%u low_high_ms=%lu\\r\\n",
           label,
           (unsigned)COMPANION_EPAPER_SSD1681_WIRE_PROBE_CYCLES,
           (unsigned long)COMPANION_EPAPER_SSD1681_WIRE_PROBE_DWELL_MS);
    for (uint8_t cycle = 1u; cycle <= COMPANION_EPAPER_SSD1681_WIRE_PROBE_CYCLES; ++cycle) {
        HAL_GPIO_WritePin(port, pin, GPIO_PIN_RESET);
        printf("[epaper] wire_probe signal=%s cycle=%u level=0\\r\\n",
               label,
               (unsigned)cycle);
        HAL_Delay(COMPANION_EPAPER_SSD1681_WIRE_PROBE_DWELL_MS);
        HAL_GPIO_WritePin(port, pin, GPIO_PIN_SET);
        printf("[epaper] wire_probe signal=%s cycle=%u level=1\\r\\n",
               label,
               (unsigned)cycle);
        HAL_Delay(COMPANION_EPAPER_SSD1681_WIRE_PROBE_DWELL_MS);
    }
    s_wire_probe_complete = true;
}
#endif

static void ssd1681_reset(void)
{
    HAL_GPIO_WritePin(COMPANION_EPAPER_SSD1681_RST_GPIO_PORT,
                      COMPANION_EPAPER_SSD1681_RST_PIN,
                      GPIO_PIN_RESET);
    HAL_Delay(10u);
    HAL_GPIO_WritePin(COMPANION_EPAPER_SSD1681_RST_GPIO_PORT,
                      COMPANION_EPAPER_SSD1681_RST_PIN,
                      GPIO_PIN_SET);
    HAL_Delay(10u);
    SSD1681_VERBOSE_TRACE("[epaper] reset busy=%d\r\n", ssd1681_busy_level());
}

static bool ssd1681_prepare_vendor_fast_profile(void)
{
    static const uint8_t temperature_sensor[] = {0x80u};
    static const uint8_t load_temperature_mode1[] = {0xB1u};
    static const uint8_t temperature_register[] = {
        SSD1681_VENDOR_FAST_TEMPERATURE_LSB, 0x00u};
    static const uint8_t load_lut_mode1[] = {0x91u};
    bool temperature_sensor_set;
    bool temperature_loaded;
    bool temperature_register_set;
    bool lut_loaded;

    /* Good Display's GDEY0154D67-T03 STM32 sample defines its fast path as
     * the SSD1681 built-in Mode 1 temperature/LUT sequence followed by 0xC7.
     * Sending an update-control byte alone does not select that profile. */
    temperature_sensor_set = ssd1681_command_data(0x18u,
                                                   temperature_sensor,
                                                   sizeof(temperature_sensor));
    temperature_loaded = temperature_sensor_set &&
                         ssd1681_command_data(0x22u,
                                               load_temperature_mode1,
                                               sizeof(load_temperature_mode1)) &&
                         ssd1681_command(0x20u) &&
                         ssd1681_wait_ready(120u, SSD1681_READY_TIMEOUT_MS);
    temperature_register_set = temperature_loaded &&
                               ssd1681_command_data(0x1Au,
                                                     temperature_register,
                                                     sizeof(temperature_register));
    lut_loaded = temperature_register_set &&
                 ssd1681_command_data(0x22u,
                                       load_lut_mode1,
                                       sizeof(load_lut_mode1)) &&
                 ssd1681_command(0x20u) &&
                 ssd1681_wait_ready(120u, SSD1681_READY_TIMEOUT_MS);
    SSD1681_VERBOSE_TRACE("[epaper] fast_profile=%s temp_sensor=%u temp_load=%u temp_reg=0x%02X%02X lut_mode1=%u\r\n",
           SSD1681_VENDOR_FAST_PROFILE_NAME,
           (unsigned)temperature_sensor_set,
           (unsigned)temperature_loaded,
           (unsigned)temperature_register[1],
           (unsigned)temperature_register[0],
           (unsigned)lut_loaded);
    return lut_loaded;
}

static ssd1681_window_t ssd1681_window_full(void)
{
    const ssd1681_window_t window = {
        .x_start_byte = 0u,
        .x_end_byte = SSD1681_BYTES_PER_ROW - 1u,
        .y_start = 0u,
        .y_end = SSD1681_HEIGHT - 1u,
        .changed = true,
    };
    return window;
}

static ssd1681_window_t ssd1681_window_from_difference(void)
{
    ssd1681_window_t window = {
        .x_start_byte = SSD1681_BYTES_PER_ROW - 1u,
        .x_end_byte = 0u,
        .y_start = SSD1681_HEIGHT - 1u,
        .y_end = 0u,
        .changed = false,
    };

    if (!s_previous_frame_valid) {
        return ssd1681_window_full();
    }
    for (uint16_t y = 0u; y < SSD1681_HEIGHT; ++y) {
        const size_t row_offset = (size_t)y * SSD1681_BYTES_PER_ROW;
        for (uint8_t x = 0u; x < SSD1681_BYTES_PER_ROW; ++x) {
            if (s_frame[row_offset + x] == s_previous_frame[row_offset + x]) {
                continue;
            }
            if (!window.changed || x < window.x_start_byte) {
                window.x_start_byte = x;
            }
            if (!window.changed || x > window.x_end_byte) {
                window.x_end_byte = x;
            }
            if (!window.changed || y < window.y_start) {
                window.y_start = y;
            }
            if (!window.changed || y > window.y_end) {
                window.y_end = y;
            }
            window.changed = true;
        }
    }
    return window;
}

static uint32_t ssd1681_window_byte_count(const ssd1681_window_t *window)
{
    if (window == NULL || !window->changed) {
        return 0u;
    }
    return ((uint32_t)window->x_end_byte - window->x_start_byte + 1u) *
           ((uint32_t)window->y_end - window->y_start + 1u);
}

static bool ssd1681_set_window(const ssd1681_window_t *window,
                               bool vendor_sample_partial)
{
    static const uint8_t driver_output[] = {0xC7u, 0x00u, 0x00u};
    static const uint8_t data_entry[] = {0x01u};
    static const uint8_t normal_border[] = {0x05u};
    static const uint8_t vendor_partial_border[] = {0x80u};
    static const uint8_t temperature[] = {0x80u};
    uint16_t controller_y_start;
    uint16_t controller_y_end;
    uint8_t ram_x[2];
    uint8_t ram_y[4];
    uint8_t x_counter[1];
    uint8_t y_counter[2];

    if (window == NULL || !window->changed ||
        window->x_end_byte >= SSD1681_BYTES_PER_ROW ||
        window->y_end >= SSD1681_HEIGHT) {
        return false;
    }
    /* The controller increments X while it counts Y downward. */
    controller_y_start = (SSD1681_HEIGHT - 1u) - window->y_start;
    controller_y_end = (SSD1681_HEIGHT - 1u) - window->y_end;
    ram_x[0] = window->x_start_byte;
    ram_x[1] = window->x_end_byte;
    ram_y[0] = (uint8_t)(controller_y_start & 0xFFu);
    ram_y[1] = (uint8_t)(controller_y_start >> 8u);
    ram_y[2] = (uint8_t)(controller_y_end & 0xFFu);
    ram_y[3] = (uint8_t)(controller_y_end >> 8u);
    x_counter[0] = window->x_start_byte;
    y_counter[0] = (uint8_t)(controller_y_start & 0xFFu);
    y_counter[1] = (uint8_t)(controller_y_start >> 8u);

    /* Match the Good Display GDEY0154D67 reference's descending Y address. */
    return ssd1681_command_data(0x01u, driver_output, sizeof(driver_output)) &&
           ssd1681_command_data(0x11u, data_entry, sizeof(data_entry)) &&
           ssd1681_command_data(0x44u, ram_x, sizeof(ram_x)) &&
           ssd1681_command_data(0x45u, ram_y, sizeof(ram_y)) &&
           ssd1681_command_data(0x3Cu,
                                vendor_sample_partial
                                    ? vendor_partial_border
                                    : normal_border,
                                sizeof(normal_border)) &&
           ssd1681_command_data(0x18u, temperature, sizeof(temperature)) &&
           ssd1681_command_data(0x4Eu, x_counter, sizeof(x_counter)) &&
           ssd1681_command_data(0x4Fu, y_counter, sizeof(y_counter));
}

static void frame_clear_white(void)
{
    memset(s_frame, 0xFF, sizeof(s_frame));
}

static void frame_set_pixel(uint16_t x, uint16_t y, bool black)
{
    if (x >= SSD1681_WIDTH || y >= SSD1681_HEIGHT) {
        return;
    }
    uint32_t index = ((uint32_t)y * SSD1681_BYTES_PER_ROW) + (x / 8u);
    uint8_t mask = (uint8_t)(0x80u >> (x & 7u));
    if (black) {
        s_frame[index] &= (uint8_t)~mask;
    } else {
        s_frame[index] |= mask;
    }
}

static void frame_checkerboard(bool inverted)
{
    frame_clear_white();

    for (uint16_t y = 0u; y < SSD1681_HEIGHT; ++y) {
        for (uint16_t x = 0u; x < SSD1681_WIDTH; ++x) {
            bool black = ((((x / 16u) + (y / 16u)) & 1u) == 0u) != inverted;
            frame_set_pixel(x, y, black);
        }
    }
}

static bool frame_prepare(comp_epaper_expression_asset_source_t *expression_assets,
                          const comp_epaper_display_request_t *request)
{
    char menu_asset_name[32];
    if (COMPANION_EPAPER_SSD1681_DIAGNOSTIC_PATTERN == 1u) {
        frame_clear_white();
        return true;
    } else if (COMPANION_EPAPER_SSD1681_DIAGNOSTIC_PATTERN == 2u) {
        memset(s_frame, 0x00, sizeof(s_frame));
        return true;
    } else if (COMPANION_EPAPER_SSD1681_DIAGNOSTIC_PATTERN == 3u) {
        frame_checkerboard(request != NULL && (request->request_id & 1u) == 0u);
        return true;
    } else if (request != NULL &&
               request->request_kind == COMP_EPAPER_DISPLAY_REQUEST_EXPRESSION &&
               request->asset_frame_valid != 0u &&
               comp_epaper_expression_asset_source_copy_frame_index(
                   expression_assets,
                   request->asset_frame_index,
                   s_frame,
                   sizeof(s_frame))) {
        SSD1681_VERBOSE_TRACE("[epaper] scene=expression name=%s frame_index=%u dirty=%u,%u,%u,%u source=external_flash\r\n",
               comp_epaper_expression_name(
                   (comp_epaper_expression_t)request->expression),
               (unsigned)request->asset_frame_index,
               (unsigned)request->dirty_x,
               (unsigned)request->dirty_y,
               (unsigned)request->dirty_width,
               (unsigned)request->dirty_height);
        return true;
    } else if (request != NULL &&
               request->request_kind == COMP_EPAPER_DISPLAY_REQUEST_EXPRESSION &&
               comp_epaper_expression_asset_source_copy_expression(
                   expression_assets,
                   (comp_epaper_expression_t)request->expression,
                   s_frame,
                   sizeof(s_frame))) {
        SSD1681_VERBOSE_TRACE("[epaper] scene=expression name=%s source=external_flash\r\n",
               comp_epaper_expression_name(
                   (comp_epaper_expression_t)request->expression));
        return true;
    } else if (request != NULL &&
               request->request_kind == COMP_EPAPER_DISPLAY_REQUEST_MENU &&
               comp_screen_menu_asset_name(
                   (comp_screen_menu_view_t)request->menu_view,
                   (comp_screen_menu_language_t)request->menu_language,
                   request->menu_page,
                   menu_asset_name,
                   sizeof(menu_asset_name)) &&
               comp_epaper_expression_asset_source_copy_clip_frame(
                   expression_assets,
                   menu_asset_name,
                   0u,
                   s_frame,
                   sizeof(s_frame)) &&
               comp_screen_menu_render_dynamic(
                   (comp_screen_menu_view_t)request->menu_view,
                   request->menu_flags,
                   request->menu_page,
                   s_frame,
                   sizeof(s_frame),
                   SSD1681_WIDTH,
                   SSD1681_HEIGHT)) {
        SSD1681_VERBOSE_TRACE("[epaper] scene=menu asset=%s source=external_flash flags=0x%02X\r\n",
               menu_asset_name,
               (unsigned)request->menu_flags);
        return true;
    } else if (request != NULL &&
               request->request_kind == COMP_EPAPER_DISPLAY_REQUEST_MENU &&
               comp_screen_menu_render((comp_screen_menu_view_t)request->menu_view,
                                       (comp_screen_menu_language_t)request->menu_language,
                                       request->menu_page,
                                       request->menu_flags,
                                       s_frame,
                                       sizeof(s_frame),
                                       SSD1681_WIDTH,
                                       SSD1681_HEIGHT)) {
        SSD1681_VERBOSE_TRACE("[epaper] scene=menu view=%u language=%u source=rescue_ui flags=0x%02X\r\n",
               (unsigned)request->menu_view,
               (unsigned)request->menu_language,
               (unsigned)request->menu_flags);
        return true;
    }
    SSD1681_VERBOSE_TRACE("[epaper] source=unavailable kind=%u; suppressing visual fallback\r\n",
           request == NULL ? 0xFFu : (unsigned)request->request_kind);
    return false;
}

static uint8_t frame_reverse_bits(uint8_t value)
{
    value = (uint8_t)(((value & 0x55u) << 1u) | ((value >> 1u) & 0x55u));
    value = (uint8_t)(((value & 0x33u) << 2u) | ((value >> 2u) & 0x33u));
    return (uint8_t)((value << 4u) | (value >> 4u));
}

static void frame_apply_target_rotation(void)
{
#if COMPANION_EPAPER_SSD1681_ROTATION_DEGREES == 180u
    for (size_t left = 0u, right = sizeof(s_frame) - 1u; left < right;
         ++left, --right) {
        uint8_t left_value = s_frame[left];
        s_frame[left] = frame_reverse_bits(s_frame[right]);
        s_frame[right] = frame_reverse_bits(left_value);
    }
#endif
}

static void frame_apply_horizontal_mirror(void)
{
#if COMPANION_EPAPER_SSD1681_MIRROR_X != 0u
    for (size_t row = 0u; row < SSD1681_HEIGHT; ++row) {
        size_t left = row * SSD1681_BYTES_PER_ROW;
        size_t right = left + SSD1681_BYTES_PER_ROW - 1u;
        while (left < right) {
            uint8_t left_value = s_frame[left];
            s_frame[left] = frame_reverse_bits(s_frame[right]);
            s_frame[right] = frame_reverse_bits(left_value);
            ++left;
            --right;
        }
        if (left == right) {
            s_frame[left] = frame_reverse_bits(s_frame[left]);
        }
    }
#endif
}

static bool ssd1681_write_plane_region(uint8_t command,
                                       const uint8_t *frame,
                                       const ssd1681_window_t *window)
{
    uint16_t bytes_per_row;

    if (frame == NULL || window == NULL || !window->changed ||
        !ssd1681_command(command)) {
        return false;
    }
    bytes_per_row = (uint16_t)(window->x_end_byte - window->x_start_byte + 1u);
    for (uint16_t y = window->y_start; y <= window->y_end; ++y) {
        const uint8_t *row = frame + ((size_t)y * SSD1681_BYTES_PER_ROW) +
                             window->x_start_byte;
        if (!ssd1681_data(row, bytes_per_row)) {
            return false;
        }
    }
    return true;
}

static bool ssd1681_refresh_display(comp_epaper_refresh_decision_t decision)
{
    const bool vendor_sample_partial =
        decision == COMP_EPAPER_REFRESH_DECISION_PARTIAL &&
        COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_DIAGNOSTIC != 0;
    uint8_t update_control = vendor_sample_partial
                                 ? 0xFFu
                                 : decision == COMP_EPAPER_REFRESH_DECISION_PARTIAL
                                       ? 0xFCu
                                       : decision == COMP_EPAPER_REFRESH_DECISION_FAST
                                             ? 0xC7u
                                             : 0xF7u;
    uint32_t fallback_delay_ms = decision == COMP_EPAPER_REFRESH_DECISION_PARTIAL
                                     ? 650u
                                     : decision == COMP_EPAPER_REFRESH_DECISION_FAST
                                           ? 2400u
                                           : 2500u;
    const char *mode = decision == COMP_EPAPER_REFRESH_DECISION_PARTIAL
                            ? "differential"
                            : decision == COMP_EPAPER_REFRESH_DECISION_FAST
                                  ? "maintenance"
                                  : "full";
    const char *profile = decision == COMP_EPAPER_REFRESH_DECISION_FAST
                              ? SSD1681_VENDOR_FAST_PROFILE_NAME
                              : vendor_sample_partial
                                    ? "good_display_vendor_partial_ab"
                                    : "default";
    const char *expected_visible_flicker =
        decision == COMP_EPAPER_REFRESH_DECISION_PARTIAL
            ? "none"
            : decision == COMP_EPAPER_REFRESH_DECISION_FAST
                  ? "single"
                  : "multiple";
    bool update_control_sent =
        ssd1681_command_data(0x22u, &update_control, sizeof(update_control));
    bool master_activation_sent = update_control_sent && ssd1681_command(0x20u);
    uint32_t activation_count = s_refresh_activation_count;
    if (master_activation_sent) {
        activation_count = ++s_refresh_activation_count;
    }
    uint32_t wait_start = HAL_GetTick();
    bool refresh_complete = master_activation_sent &&
                            ssd1681_wait_refresh_complete(fallback_delay_ms, 5000u);
    SSD1681_VERBOSE_TRACE("[epaper] refresh mode=%s profile=%s control=0x%02X expected_visible_flicker=%s activation_count=%lu busy=%d update=%u activate=%u complete=%u elapsed_ms=%lu\r\n",
           mode,
           profile,
           (unsigned)update_control,
           expected_visible_flicker,
           (unsigned long)activation_count,
           ssd1681_busy_level(),
           (unsigned)update_control_sent,
           (unsigned)master_activation_sent,
           (unsigned)refresh_complete,
           (unsigned long)(HAL_GetTick() - wait_start));
    return refresh_complete;
}

static comp_epaper_panel_result_t ssd1681_refresh(
    void *context,
    const comp_epaper_display_request_t *request,
    comp_epaper_panel_report_t *out_report)
{
    ssd1681_target_context_t *target = (ssd1681_target_context_t *)context;
    if (request == NULL) {
        return COMP_EPAPER_PANEL_RESULT_BAD_ARGUMENT;
    }
    if (target == NULL) {
        return COMP_EPAPER_PANEL_RESULT_BAD_ARGUMENT;
    }

    comp_epaper_refresh_mode_t requested_mode =
        request->refresh_mode <=
                (uint8_t)COMP_EPAPER_REFRESH_MAINTENANCE
            ? (comp_epaper_refresh_mode_t)request->refresh_mode
            : COMP_EPAPER_REFRESH_AUTO;
    comp_epaper_refresh_selection_t selection =
        comp_epaper_refresh_policy_select(&target->refresh_policy, requested_mode);
    bool partial = selection.decision == COMP_EPAPER_REFRESH_DECISION_PARTIAL;
    bool fast = selection.decision == COMP_EPAPER_REFRESH_DECISION_FAST;
    const bool vendor_sample_partial =
        partial && COMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_DIAGNOSTIC != 0;
    const bool official_full_diagnostic =
        !partial && COMPANION_EPAPER_SSD1681_OFFICIAL_FULL_DIAGNOSTIC != 0;
    const uint8_t transfer_plane_count =
        vendor_sample_partial || official_full_diagnostic ? 1u : 2u;
    bool controller_initialization_required = !s_controller_initialized || fast ||
                                             vendor_sample_partial;
    ssd1681_window_t window;
    uint32_t window_bytes;
    uint32_t frame_prepare_start_ms;
    uint32_t frame_prepare_elapsed_ms;
    uint32_t controller_setup_start_ms;
    uint32_t controller_setup_elapsed_ms;
    uint32_t transfer_before_waveform_start_ms;
    uint32_t transfer_before_waveform_elapsed_ms;
    uint32_t transfer_after_waveform_elapsed_ms;
    const char *selected_mode = partial ? "differential" : fast ? "maintenance" : "full";
    SSD1681_VERBOSE_TRACE("[epaper] policy requested=%u selected=%s reason=%u partial_count=%u limit=%u baseline=%u\r\n",
           (unsigned)requested_mode,
           selected_mode,
           (unsigned)selection.reason,
           (unsigned)selection.partial_count_before,
           (unsigned)target->refresh_policy.partial_limit,
           (unsigned)target->refresh_policy.baseline_valid);

#if COMPANION_EPAPER_SSD1681_WIRE_PROBE != 0u
    if (!s_wire_probe_complete) {
        ssd1681_wire_probe();
    }
    return COMP_EPAPER_PANEL_RESULT_DEFERRED_CONTROLLER_UNKNOWN;
#endif

    frame_prepare_start_ms = HAL_GetTick();
    if (!frame_prepare(target->expression_assets, request)) {
        if (out_report != NULL) {
            out_report->request_id = request->request_id;
            out_report->content_crc32 = request->content_crc32;
            out_report->transferred_bytes = 0u;
            out_report->width = SSD1681_WIDTH;
            out_report->height = SSD1681_HEIGHT;
        }
        return COMP_EPAPER_PANEL_RESULT_TRANSPORT_ERROR;
    }
    frame_apply_target_rotation();
    frame_apply_horizontal_mirror();
    frame_prepare_elapsed_ms = HAL_GetTick() - frame_prepare_start_ms;
    window = partial ? ssd1681_window_from_difference() : ssd1681_window_full();
    window_bytes = ssd1681_window_byte_count(&window);
    if (partial && !window.changed) {
        SSD1681_VERBOSE_TRACE("[epaper] differential_skip identical_frame\r\n");
        if (out_report != NULL) {
            out_report->request_id = request->request_id;
            out_report->content_crc32 = request->content_crc32;
            out_report->transferred_bytes = 0u;
            out_report->width = SSD1681_WIDTH;
            out_report->height = SSD1681_HEIGHT;
        }
        return COMP_EPAPER_PANEL_RESULT_OK;
    }

    controller_setup_start_ms = HAL_GetTick();
    ssd1681_gpio_init();
    if (controller_initialization_required) {
        ssd1681_reset();
    }
    SSD1681_VERBOSE_TRACE("[epaper] spi=%s sck=PA9 mosi=PC1\r\n",
           ssd1681_spi_transport_name());

    bool pre_reset_ready = ssd1681_wait_ready(20u, SSD1681_READY_TIMEOUT_MS);
    bool reset_command_sent = controller_initialization_required && !vendor_sample_partial &&
                              pre_reset_ready && ssd1681_command(0x12u);
    SSD1681_VERBOSE_TRACE("[epaper] controller_init=%u soft_reset mode=%s busy=%d pre=%u command=%u\r\n",
           (unsigned)controller_initialization_required,
           partial ? "differential" : fast ? "maintenance" : "full",
           ssd1681_busy_level(),
           (unsigned)pre_reset_ready,
           (unsigned)reset_command_sent);
    bool reset_ready = controller_initialization_required
                            ? vendor_sample_partial
                                  ? pre_reset_ready
                                  : reset_command_sent &&
                                        ssd1681_wait_ready(120u, SSD1681_READY_TIMEOUT_MS)
                            : pre_reset_ready;
    bool fast_profile_loaded = !fast ||
                               (reset_ready && ssd1681_prepare_vendor_fast_profile());
    bool window_set = fast_profile_loaded && reset_ready &&
                      ssd1681_set_window(&window, vendor_sample_partial);
    bool border_set = window_set;
    controller_setup_elapsed_ms = HAL_GetTick() - controller_setup_start_ms;
    SSD1681_VERBOSE_TRACE("[epaper] frame rotation=%u mirror_x=%u width=%u height=%u\r\n",
           (unsigned)COMPANION_EPAPER_SSD1681_ROTATION_DEGREES,
           (unsigned)COMPANION_EPAPER_SSD1681_MIRROR_X,
           (unsigned)SSD1681_WIDTH,
           (unsigned)SSD1681_HEIGHT);
    SSD1681_VERBOSE_TRACE("[epaper] window x_byte=%u..%u y=%u..%u bytes=%lu changed=%u\r\n",
           (unsigned)window.x_start_byte,
           (unsigned)window.x_end_byte,
           (unsigned)window.y_start,
           (unsigned)window.y_end,
           (unsigned long)window_bytes,
           (unsigned)window.changed);
    bool frame_written = false;
    bool baseline_written = false;
    bool display_refreshed = false;
    transfer_before_waveform_start_ms = HAL_GetTick();
    transfer_after_waveform_elapsed_ms = 0u;

    if (partial) {
        /* Differential mode needs the old and new pixels: seed 0x26 from the
         * CPU's last successful framebuffer and 0x24 from the current frame
         * before 0xFC. The next request repeats that pair for its own dirty
         * window, so sending both planes again after the waveform only delays
         * the next touch response. Good Display's matching sample likewise
         * seeds its base map separately from its partial write path. */
        if (vendor_sample_partial) {
            /* Diagnostic-only A/B: match the Good Display sample's partial
             * path, which resets and writes the current region to 0x24 only
             * before 0xFF. The normal product path stays 0xFC old/new. */
            frame_written = window_set && border_set &&
                            ssd1681_write_plane_region(0x24u, s_frame, &window);
        } else {
            frame_written = window_set && border_set &&
                            ssd1681_write_plane_region(0x26u, s_previous_frame, &window) &&
                            ssd1681_write_plane_region(0x24u, s_frame, &window);
        }
        transfer_before_waveform_elapsed_ms =
            HAL_GetTick() - transfer_before_waveform_start_ms;
        display_refreshed = frame_written &&
                            ssd1681_refresh_display(selection.decision);
        /* The CPU copy below becomes the new baseline only after this
         * transaction is known-good. No post-waveform RAM replay is needed. */
        baseline_written = display_refreshed;
    } else {
        if (official_full_diagnostic) {
            /* Production-off recovery A/B: exactly match Good Display's
             * normal full path, which writes 0x24 only before 0xF7. */
            frame_written = window_set && border_set &&
                            ssd1681_write_plane_region(0x24u, s_frame, &window);
            baseline_written = frame_written;
            SSD1681_VERBOSE_TRACE("[epaper] full_write_profile=good_display_official_0x24_only\r\n");
        } else {
            /* Product full and maintenance paths keep their accepted
             * two-plane baseline behavior outside the recovery A/B. */
            baseline_written = window_set && border_set &&
                               ssd1681_write_plane_region(0x26u, s_frame, &window);
            frame_written = baseline_written &&
                            ssd1681_write_plane_region(0x24u, s_frame, &window);
        }
        transfer_before_waveform_elapsed_ms =
            HAL_GetTick() - transfer_before_waveform_start_ms;
        display_refreshed = frame_written &&
                            ssd1681_refresh_display(selection.decision);
    }
    SSD1681_VERBOSE_TRACE("[epaper] timing mode=%s prepare_ms=%lu setup_ms=%lu transfer_before_waveform_ms=%lu transfer_after_waveform_ms=%lu bytes=%lu data_planes=%u spi=%s\r\n",
           selected_mode,
           (unsigned long)frame_prepare_elapsed_ms,
           (unsigned long)controller_setup_elapsed_ms,
           (unsigned long)transfer_before_waveform_elapsed_ms,
           (unsigned long)transfer_after_waveform_elapsed_ms,
           (unsigned long)window_bytes,
           (unsigned)transfer_plane_count,
           ssd1681_spi_transport_name());
    bool ok = pre_reset_ready && reset_ready && fast_profile_loaded && window_set && border_set &&
               frame_written && baseline_written && display_refreshed;
    comp_epaper_refresh_policy_commit(&target->refresh_policy,
                                      selection.decision,
                                      ok);
    SSD1681_VERBOSE_TRACE("[epaper] policy_commit mode=%s ok=%u partial_count=%u baseline=%u\r\n",
           selected_mode,
           (unsigned)ok,
           (unsigned)target->refresh_policy.partial_count,
           (unsigned)target->refresh_policy.baseline_valid);

    if (!ok) {
        s_previous_frame_valid = false;
        s_controller_initialized = false;
        printf("[epaper] fail busy=%d pre=%u reset_cmd=%u reset_ready=%u window=%u border=%u frame=%u baseline=%u refresh=%u\r\n",
               ssd1681_busy_level(),
               (unsigned)pre_reset_ready,
               (unsigned)reset_command_sent,
               (unsigned)reset_ready,
               (unsigned)window_set,
               (unsigned)border_set,
               (unsigned)frame_written,
               (unsigned)baseline_written,
               (unsigned)display_refreshed);
    } else {
        memcpy(s_previous_frame, s_frame, sizeof(s_previous_frame));
        s_previous_frame_valid = true;
        s_controller_initialized = true;
    }

    if (out_report != NULL) {
        out_report->request_id = request->request_id;
        out_report->content_crc32 = request->content_crc32;
        out_report->transferred_bytes = ok ? window_bytes * transfer_plane_count : 0u;
        out_report->width = SSD1681_WIDTH;
        out_report->height = SSD1681_HEIGHT;
    }

    return ok ? COMP_EPAPER_PANEL_RESULT_OK
              : COMP_EPAPER_PANEL_RESULT_TRANSPORT_ERROR;
}

void companion_epaper_panel_stm32wb_ssd1681_init(
    comp_epaper_panel_adapter_t *adapter,
    comp_epaper_expression_asset_source_t *expression_assets)
{
    s_target_context.expression_assets = expression_assets;
    s_previous_frame_valid = false;
    s_controller_initialized = false;
    comp_epaper_refresh_policy_init(&s_target_context.refresh_policy,
                                    COMP_EPAPER_REFRESH_DEFAULT_PARTIAL_LIMIT);
    const comp_epaper_panel_config_t config = {
        .hardware_present = true,
        .controller_known = true,
        .width = SSD1681_WIDTH,
        .height = SSD1681_HEIGHT,
        .controller_name = "SSD1681-GDEY0154D67-T03",
        .refresh = ssd1681_refresh,
        .context = &s_target_context,
    };
    comp_epaper_panel_adapter_init(adapter, &config);

#if COMPANION_EPAPER_SSD1681_DIAGNOSTIC_PATTERN != 0u
    {
        for (uint8_t cycle = 1u;
             cycle <= COMPANION_EPAPER_SSD1681_DIAGNOSTIC_REPEATS;
             ++cycle) {
            const comp_epaper_display_request_t request = {
                .request_id = 0xE0010000u + cycle,
                .request_kind = COMP_EPAPER_DISPLAY_REQUEST_CARD_WRITE,
                .refresh_mode = COMPANION_EPAPER_SSD1681_DIAGNOSTIC_PARTIAL != 0u
                                    ? (cycle == 1u ? COMP_EPAPER_REFRESH_FULL
                                                   : COMP_EPAPER_REFRESH_PARTIAL)
                                    : COMP_EPAPER_REFRESH_FULL,
            };
            comp_epaper_panel_report_t report;
            comp_epaper_panel_result_t result =
                comp_epaper_panel_adapter_refresh_card(adapter, &request, &report);

            SSD1681_VERBOSE_TRACE("[epaper] boot_diag pattern=%u official=%u cycle=%u result=%u bytes=%lu busy=%d\r\n",
                   (unsigned)COMPANION_EPAPER_SSD1681_DIAGNOSTIC_PATTERN,
                   (unsigned)COMPANION_EPAPER_SSD1681_OFFICIAL_FULL_DIAGNOSTIC,
                   (unsigned)cycle,
                   (unsigned)result,
                   (unsigned long)report.transferred_bytes,
                   ssd1681_busy_level());
            if (cycle < COMPANION_EPAPER_SSD1681_DIAGNOSTIC_REPEATS) {
                HAL_Delay(COMPANION_EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS);
            }
        }
    }
#endif
}

void companion_epaper_panel_stm32wb_ssd1681_set_wait_service(
    companion_epaper_wait_service_fn service,
    void *context,
    uint16_t period_ms)
{
    s_target_context.wait_service = service;
    s_target_context.wait_service_context = context;
    s_target_context.wait_service_period_ms = period_ms == 0u ? 1u : period_ms;
    s_target_context.wait_service_next_ms = HAL_GetTick();
}
