#include "r7_runtime_bridge_stm32wb.h"
#if defined(COMPANION_VISUAL_ASSET_PACK_ENABLE) && COMPANION_VISUAL_ASSET_PACK_ENABLE
#include "companion_visual_runtime_adapter.h"
#endif

#include "companion_r7_locked_v9_frames.h"
#if defined(COMPANION_R7_RUNTIME_HOST_TEST) && COMPANION_R7_RUNTIME_HOST_TEST
#include "r7_runtime_bridge_host_hal.h"
#else
#include "main.h"
#endif

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

#ifndef COMPANION_EPAPER_SSD1681_HAS_BUSY
#define COMPANION_EPAPER_SSD1681_HAS_BUSY 0
#endif
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
#ifndef COMPANION_EPAPER_SSD1681_BUSY_GPIO_PORT
#define COMPANION_EPAPER_SSD1681_BUSY_GPIO_PORT GPIOC
#endif
#ifndef COMPANION_EPAPER_SSD1681_BUSY_PIN
#define COMPANION_EPAPER_SSD1681_BUSY_PIN GPIO_PIN_5
#endif
#ifndef SSD1681_READY_TIMEOUT_MS
#define SSD1681_READY_TIMEOUT_MS 600u
#endif
#ifndef COMPANION_EPAPER_SSD1681_R7_RUNTIME_CONTINUOUS_DIAGNOSTIC
#define COMPANION_EPAPER_SSD1681_R7_RUNTIME_CONTINUOUS_DIAGNOSTIC 0
#endif

extern SPI_HandleTypeDef hspi2;

static companion_r7_runtime_wait_service_fn s_wait_service;
static void *s_wait_context;
static uint16_t s_wait_period_ms;
static uint32_t s_next_wait_ms;
static uint8_t s_next_frame;
static uint32_t s_previous_start_ms;
static bool s_cadence_valid;
static bool s_ready;
static bool s_cleanup_pending;
static bool s_complete;
static bool s_terminal_fault;
static uint32_t s_visual_activation_start_ms;
static uint32_t s_visual_last_busy_ms;
static uint32_t s_visual_last_transaction_ms;
static uint32_t s_visual_activation_count;
static uint32_t s_visual_previous_start_ms;
static bool s_visual_cadence_valid;
static bool s_visual_fault;
static bool s_visual_burst_active;
static bool s_visual_closed;

static bool bridge_exit_cleanup(void);

static void bridge_wait_service(void)
{
    const uint32_t now = HAL_GetTick();
    if (s_wait_service == NULL ||
        (int32_t)(now - s_next_wait_ms) < 0) {
        return;
    }
    s_next_wait_ms = now + s_wait_period_ms;
    s_wait_service(s_wait_context, now);
}

static void bridge_select(bool selected)
{
    HAL_GPIO_WritePin(COMPANION_EPAPER_SSD1681_CS_GPIO_PORT,
                      COMPANION_EPAPER_SSD1681_CS_PIN,
                      selected ? GPIO_PIN_RESET : GPIO_PIN_SET);
}

static bool bridge_spi_tx(const uint8_t *data, uint16_t length)
{
    if (data == NULL || length == 0u) {
        return true;
    }
#if defined(COMPANION_R7_RUNTIME_HOST_TEST) && COMPANION_R7_RUNTIME_HOST_TEST
    return companion_r7_host_spi_tx(data, length);
#else
    for (uint16_t index = 0u; index < length; ++index) {
        uint8_t value = data[index];
        for (uint8_t bit = 0u; bit < 8u; ++bit) {
            HAL_GPIO_WritePin(GPIOA, GPIO_PIN_9, GPIO_PIN_RESET);
            HAL_GPIO_WritePin(GPIOC, GPIO_PIN_1,
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
}

static bool bridge_command(uint8_t command)
{
    HAL_GPIO_WritePin(COMPANION_EPAPER_SSD1681_DC_GPIO_PORT,
                      COMPANION_EPAPER_SSD1681_DC_PIN, GPIO_PIN_RESET);
#if defined(COMPANION_R7_RUNTIME_HOST_TEST) && COMPANION_R7_RUNTIME_HOST_TEST
    companion_r7_host_set_dc(false);
#endif
    bridge_select(true);
    const bool ok = bridge_spi_tx(&command, 1u);
    bridge_select(false);
    return ok;
}

static bool bridge_data(const uint8_t *data, uint16_t length)
{
    HAL_GPIO_WritePin(COMPANION_EPAPER_SSD1681_DC_GPIO_PORT,
                      COMPANION_EPAPER_SSD1681_DC_PIN, GPIO_PIN_SET);
#if defined(COMPANION_R7_RUNTIME_HOST_TEST) && COMPANION_R7_RUNTIME_HOST_TEST
    companion_r7_host_set_dc(true);
#endif
    bridge_select(true);
    const bool ok = bridge_spi_tx(data, length);
    bridge_select(false);
    return ok;
}

static bool bridge_command_data(uint8_t command,
                                const uint8_t *data,
                                uint16_t length)
{
    return bridge_command(command) && bridge_data(data, length);
}

static bool bridge_wait_ready(uint32_t timeout_ms)
{
#if COMPANION_EPAPER_SSD1681_HAS_BUSY
    const uint32_t start = HAL_GetTick();
    while (HAL_GPIO_ReadPin(COMPANION_EPAPER_SSD1681_BUSY_GPIO_PORT,
                            COMPANION_EPAPER_SSD1681_BUSY_PIN) != GPIO_PIN_RESET) {
        if (HAL_GetTick() - start > timeout_ms) return false;
        bridge_wait_service();
        HAL_Delay(1u);
    }
#else
    (void)timeout_ms;
#endif
    return true;
}

static bool bridge_wait_refresh(uint32_t *busy_ms)
{
    const uint32_t start = HAL_GetTick();
#if COMPANION_EPAPER_SSD1681_HAS_BUSY
    bool observed_busy = false;
    while (HAL_GetTick() - start <= 600u) {
        const bool ready = HAL_GPIO_ReadPin(COMPANION_EPAPER_SSD1681_BUSY_GPIO_PORT,
                                            COMPANION_EPAPER_SSD1681_BUSY_PIN) == GPIO_PIN_RESET;
        if (!ready) observed_busy = true;
        if (ready && observed_busy) break;
        bridge_wait_service();
        HAL_Delay(1u);
    }
#else
    while (HAL_GetTick() - start < 443u) {
        bridge_wait_service();
        HAL_Delay(1u);
    }
#endif
    *busy_ms = HAL_GetTick() - start;
    return *busy_ms <= 600u;
}

bool companion_r7_runtime_bridge_visual_transport(void *context,
                                                   uint8_t command,
                                                   const uint8_t *data,
                                                   uint16_t length)
{
    (void)context;
    if (s_visual_closed || s_visual_fault) return false;
    if (command == 0x3Cu) {
        s_visual_activation_start_ms = HAL_GetTick();
        if (s_visual_cadence_valid && s_visual_burst_active) {
            const uint32_t delta = s_visual_activation_start_ms -
                                   s_visual_previous_start_ms;
            if (delta == 0u || delta > 480u) {
                s_visual_fault = true;
                return false;
            }
        }
        s_visual_burst_active = true;
    }
    if (command == 0x20u) {
        uint32_t busy_ms = 0u;
        const bool command_ok = bridge_command(command);
        const bool ok = command_ok && bridge_wait_refresh(&busy_ms);
        s_visual_last_busy_ms = busy_ms;
        s_visual_last_transaction_ms = HAL_GetTick() - s_visual_activation_start_ms;
        if (!ok || s_visual_last_transaction_ms > 480u || busy_ms > 600u) {
            s_visual_fault = true;
            return false;
        }
        s_visual_previous_start_ms = s_visual_activation_start_ms;
        s_visual_cadence_valid = true;
        s_visual_activation_count++;
        return ok;
    }
    if (!bridge_command_data(command, data, length)) {
        s_visual_fault = true;
        return false;
    }
    return true;
}

uint32_t companion_r7_runtime_bridge_last_busy_ms(void)
{
    return s_visual_last_busy_ms;
}

uint32_t companion_r7_runtime_bridge_last_transaction_ms(void)
{
    return s_visual_last_transaction_ms;
}

bool companion_r7_runtime_bridge_visual_faulted(void)
{
    return s_visual_fault;
}

bool companion_r7_runtime_bridge_visual_closed(void)
{
    return s_visual_closed;
}

void companion_r7_runtime_bridge_visual_set_burst_active(bool active)
{
    if (!active) s_visual_cadence_valid = false;
    s_visual_burst_active = active;
}

uint32_t companion_r7_runtime_bridge_visual_activation_count(void)
{
    return s_visual_activation_count;
}

static void bridge_gpio_init(void)
{
    GPIO_InitTypeDef gpio = {0};
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    (void)HAL_SPI_DeInit(&hspi2);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_9, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_1, GPIO_PIN_RESET);
    gpio.Pin = GPIO_PIN_9;
    gpio.Mode = GPIO_MODE_OUTPUT_PP;
    gpio.Pull = GPIO_NOPULL;
    gpio.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(GPIOA, &gpio);
    gpio.Pin = GPIO_PIN_1;
    HAL_GPIO_Init(GPIOC, &gpio);
    HAL_GPIO_WritePin(COMPANION_EPAPER_SSD1681_CS_GPIO_PORT,
                      COMPANION_EPAPER_SSD1681_CS_PIN, GPIO_PIN_SET);
    HAL_GPIO_WritePin(COMPANION_EPAPER_SSD1681_DC_GPIO_PORT,
                      COMPANION_EPAPER_SSD1681_DC_PIN, GPIO_PIN_SET);
    HAL_GPIO_WritePin(COMPANION_EPAPER_SSD1681_RST_GPIO_PORT,
                      COMPANION_EPAPER_SSD1681_RST_PIN, GPIO_PIN_SET);
    gpio.Pin = COMPANION_EPAPER_SSD1681_CS_PIN;
    HAL_GPIO_Init(COMPANION_EPAPER_SSD1681_CS_GPIO_PORT, &gpio);
    gpio.Pin = COMPANION_EPAPER_SSD1681_DC_PIN;
    HAL_GPIO_Init(COMPANION_EPAPER_SSD1681_DC_GPIO_PORT, &gpio);
    gpio.Pin = COMPANION_EPAPER_SSD1681_RST_PIN;
    HAL_GPIO_Init(COMPANION_EPAPER_SSD1681_RST_GPIO_PORT, &gpio);
    gpio.Pin = COMPANION_EPAPER_SSD1681_BUSY_PIN;
    gpio.Mode = GPIO_MODE_INPUT;
    gpio.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(COMPANION_EPAPER_SSD1681_BUSY_GPIO_PORT, &gpio);
}

static bool bridge_window(uint8_t x_start,
                          uint8_t x_end,
                          uint16_t y_start,
                          uint16_t y_end)
{
    const uint16_t controller_start = 199u - y_start;
    const uint16_t controller_end = 199u - y_end;
    const uint8_t ram_x[] = {x_start, x_end};
    const uint8_t ram_y[] = {(uint8_t)controller_start, 0u,
                             (uint8_t)controller_end, 0u};
    const uint8_t x_counter[] = {x_start};
    const uint8_t y_counter[] = {(uint8_t)controller_start, 0u};
    const uint8_t border[] = {0x80u};
    return bridge_command_data(0x3Cu, border, 1u) &&
           bridge_command_data(0x44u, ram_x, 2u) &&
           bridge_command_data(0x45u, ram_y, 4u) &&
           bridge_command_data(0x4Eu, x_counter, 1u) &&
           bridge_command_data(0x4Fu, y_counter, 2u);
}

static bool bridge_reset(void)
{
    HAL_GPIO_WritePin(COMPANION_EPAPER_SSD1681_RST_GPIO_PORT,
                      COMPANION_EPAPER_SSD1681_RST_PIN, GPIO_PIN_RESET);
    HAL_Delay(10u);
    HAL_GPIO_WritePin(COMPANION_EPAPER_SSD1681_RST_GPIO_PORT,
                      COMPANION_EPAPER_SSD1681_RST_PIN, GPIO_PIN_SET);
    HAL_Delay(10u);
    return bridge_wait_ready(SSD1681_READY_TIMEOUT_MS);
}

void companion_r7_runtime_bridge_init(comp_epaper_panel_adapter_t *adapter)
{
    const uint8_t baseline_mode2[] = {0xFFu};
#if defined(COMPANION_VISUAL_ASSET_PACK_ENABLE) && COMPANION_VISUAL_ASSET_PACK_ENABLE
    uint8_t visual_baseline[5000];
#endif
    s_next_frame = 0u;
    s_cadence_valid = false;
    s_ready = false;
    s_cleanup_pending = false;
    s_complete = false;
    s_terminal_fault = false;
    s_visual_activation_count = 0u;
    s_visual_previous_start_ms = 0u;
    s_visual_cadence_valid = false;
    s_visual_fault = false;
    s_visual_burst_active = false;
    s_visual_closed = false;
    comp_epaper_panel_adapter_init_dry_run(adapter);
    bridge_gpio_init();
#if defined(COMPANION_VISUAL_ASSET_PACK_ENABLE) && COMPANION_VISUAL_ASSET_PACK_ENABLE
    const bool baseline_ready = companion_visual_runtime_copy_panel_frame(
        COMPANION_VISUAL_STATE_CENTERED_REST, visual_baseline,
        sizeof(visual_baseline));
#else
    const bool baseline_ready = true;
#endif
    const bool ok = baseline_ready && bridge_reset() &&
                    bridge_window(0u, 24u, 0u, 199u) &&
                    bridge_command(0x24u) &&
#if defined(COMPANION_VISUAL_ASSET_PACK_ENABLE) && COMPANION_VISUAL_ASSET_PACK_ENABLE
                    bridge_data(visual_baseline, 5000u) &&
#else
                    bridge_data(companion_r7_locked_v9_baseline_frame, 5000u) &&
#endif
                    bridge_command_data(0x22u, baseline_mode2, 1u) &&
                    bridge_command(0x20u);
    uint32_t busy_ms = 0u;
    const bool displayed = ok && bridge_wait_refresh(&busy_ms);
    s_ready = displayed;
    printf("[epaper] r7_runtime metadata=frame16 baseline5000 corridor2610 x4-21 y26-170 controller_y173-29 mode2=official cleanup=single_flash production=0 init_returns=1 baseline_busy_ms=%lu result=%s\r\n",
           (unsigned long)busy_ms, displayed ? "ok" : "no_go");
}

bool companion_r7_runtime_bridge_service(void)
{
    if (s_terminal_fault || !s_ready) return false;
    if (s_complete) return true;
    if (s_next_frame < COMPANION_R7_LOCKED_V9_FRAME_COUNT) {
        const uint32_t start = HAL_GetTick();
        const uint8_t previous = s_next_frame == 0u ? 15u : (uint8_t)(s_next_frame - 1u);
        const bool ready = bridge_wait_ready(SSD1681_READY_TIMEOUT_MS);
        const bool window_ok = ready && bridge_window(4u, 21u, 26u, 170u);
        const bool write_ok = window_ok && bridge_command(0x24u) &&
                              bridge_data(companion_r7_locked_v9_payloads[s_next_frame], 2610u);
        const uint32_t busy_start = HAL_GetTick();
        const uint8_t mode2[] = {0xCFu};
        const bool activation_ok = write_ok &&
                                   bridge_command_data(0x22u, mode2, 1u) &&
                                   bridge_command(0x20u);
        uint32_t busy_ms = 0u;
        const bool ok = activation_ok && bridge_wait_refresh(&busy_ms);
        const uint32_t movement_start = start;
        const uint32_t delta = s_cadence_valid ? movement_start - s_previous_start_ms : 0u;
        const uint32_t transaction_ms = HAL_GetTick() - start;
        printf("[epaper] r7_runtime phase=q index=%u previous=%u current=%u ready=%u t=%lu b=%lu d=%lu result=%s\r\n",
               (unsigned)s_next_frame + 1u, (unsigned)previous + 1u,
               (unsigned)s_next_frame + 1u, ready ? 1u : 0u,
               (unsigned long)transaction_ms, (unsigned long)busy_ms,
               (unsigned long)delta, ok ? "ok" : "no_go");
        if (!ok || transaction_ms > 480u || busy_ms > 600u ||
            (s_cadence_valid && (delta == 0u || delta > 480u))) {
            s_ready = false;
            s_terminal_fault = true;
            printf("[epaper] r7_runtime terminal_fault=1 result=no_go\r\n");
            return false;
        }
        s_previous_start_ms = movement_start;
        s_cadence_valid = true;
        ++s_next_frame;
        if (s_next_frame == COMPANION_R7_LOCKED_V9_FRAME_COUNT) {
#if COMPANION_EPAPER_SSD1681_R7_RUNTIME_CONTINUOUS_DIAGNOSTIC
            printf("[epaper] r7_runtime qualification=16 result=ok continuous=1 cleanup=external\r\n");
            s_next_frame = 0u;
#else
            s_cleanup_pending = true;
#endif
        }
        (void)busy_start;
        return true;
    }
    if (s_cleanup_pending) return bridge_exit_cleanup();
    return true;
}

static bool bridge_exit_cleanup(void)
{
    s_visual_closed = true;
    const uint8_t white_mode2[] = {0xFFu};
    const bool ok = bridge_reset() && bridge_window(0u, 24u, 0u, 199u) &&
                    bridge_command(0x24u) && bridge_data(companion_r7_locked_v9_baseline_frame, 5000u) &&
                    bridge_command(0x26u) && bridge_data(companion_r7_locked_v9_baseline_frame, 5000u) &&
                    bridge_command_data(0x22u, white_mode2, 1u) && bridge_command(0x20u);
    uint32_t busy_ms = 0u;
    const bool clean = ok && bridge_wait_refresh(&busy_ms);
    printf("[epaper] r7_runtime cleanup=single_flash_white writes_24=1 writes_26=1 busy_ms=%lu result=%s\r\n",
           (unsigned long)busy_ms, clean ? "ok" : "no_go");
    s_cleanup_pending = false;
    s_complete = clean;
    if (!clean) s_terminal_fault = true;
    return clean;
}

bool companion_r7_runtime_bridge_exit_cleanup(void)
{
    return bridge_exit_cleanup();
}

void companion_r7_runtime_bridge_set_wait_service(
    companion_r7_runtime_wait_service_fn service,
    void *context,
    uint16_t period_ms)
{
    s_wait_service = service;
    s_wait_context = context;
    s_wait_period_ms = period_ms == 0u ? 1u : period_ms;
    s_next_wait_ms = HAL_GetTick();
}

#if defined(COMPANION_R7_RUNTIME_HOST_TEST) && COMPANION_R7_RUNTIME_HOST_TEST
bool companion_r7_runtime_host_validate_movement_trace(
    const uint8_t *commands,
    const uint16_t *data_lengths,
    const uint8_t *data_first_bytes,
    size_t command_count,
    uint32_t transaction_ms,
    uint32_t busy_ms,
    bool busy_asserted,
    bool busy_released)
{
    static const uint8_t expected_commands[] = {
        0x3Cu, 0x44u, 0x45u, 0x4Eu, 0x4Fu, 0x24u, 0x22u, 0x20u};
    static const uint16_t expected_lengths[] = {1u, 2u, 4u, 1u, 2u, 2610u, 1u, 0u};
    static const uint8_t expected_first_bytes[] = {0x80u, 4u, 0xADu, 4u, 0xADu, 0u, 0xCFu, 0u};
    if (commands == NULL || data_lengths == NULL || data_first_bytes == NULL ||
        command_count != sizeof(expected_commands) || transaction_ms > 480u ||
        busy_ms > 600u || !busy_asserted || !busy_released) return false;
    for (size_t index = 0u; index < command_count; ++index) {
        if (commands[index] != expected_commands[index] ||
            data_lengths[index] != expected_lengths[index] ||
            (index != 5u && expected_lengths[index] != 0u &&
             data_first_bytes[index] != expected_first_bytes[index])) return false;
    }
    return true;
}
#endif
