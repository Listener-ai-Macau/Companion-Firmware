#include "r7_runtime_bridge_stm32wb.h"
#include "r7_runtime_bridge_host_hal.h"

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

GPIO_TypeDef g_gpio_a;
GPIO_TypeDef g_gpio_b;
GPIO_TypeDef g_gpio_c;
GPIO_TypeDef *GPIOA = &g_gpio_a;
GPIO_TypeDef *GPIOB = &g_gpio_b;
GPIO_TypeDef *GPIOC = &g_gpio_c;
SPI_HandleTypeDef hspi2;

static uint32_t g_tick;
static bool g_dc_data;
static unsigned g_busy_behavior;
static bool g_refresh_active;
static bool g_busy_asserted;
static bool g_busy_released;
static unsigned g_busy_reads;
static unsigned g_wait_callbacks;
static unsigned g_callbacks_during;
static unsigned g_touch_before;
static unsigned g_touch_after;
static uint8_t g_commands[16];
static uint16_t g_command_data_lengths[16];
static uint8_t g_command_data_first_bytes[16];
static size_t g_command_count;
static unsigned g_data_calls;
static unsigned g_cleanup_26;
static unsigned g_mode2_cf;
static unsigned g_mode2_ff;

static void fail(const char *message)
{
    fprintf(stderr, "FAIL:%s\n", message);
    (void)remove("comp-req-466-r7-runtime-host-pass.marker");
    exit(1);
}

uint32_t HAL_GetTick(void) { return g_tick; }
void HAL_Delay(uint32_t milliseconds)
{
    g_tick += milliseconds;
    if (g_busy_behavior == 3u) g_tick += 481u;
}
void HAL_GPIO_WritePin(GPIO_TypeDef *port, uint32_t pin, uint32_t state)
{
    (void)port;
    if (pin == GPIO_PIN_0) g_dc_data = state == GPIO_PIN_SET;
}
uint32_t HAL_GPIO_ReadPin(GPIO_TypeDef *port, uint32_t pin)
{
    (void)port;
    if (pin != GPIO_PIN_5) return GPIO_PIN_RESET;
    if (!g_refresh_active) return GPIO_PIN_RESET;
    if (g_busy_behavior == 1u) return GPIO_PIN_RESET;
    if (g_busy_reads++ == 0u) {
        g_busy_asserted = true;
        return GPIO_PIN_SET;
    }
    if (g_busy_behavior == 2u) return GPIO_PIN_SET;
    if (g_busy_reads == 2u) return GPIO_PIN_SET;
    g_refresh_active = false;
    g_busy_released = true;
    return GPIO_PIN_RESET;
}
void HAL_GPIO_Init(GPIO_TypeDef *port, GPIO_InitTypeDef *config)
{
    (void)port; (void)config;
}
int HAL_SPI_DeInit(SPI_HandleTypeDef *handle) { (void)handle; return 0; }
void comp_epaper_panel_adapter_init_dry_run(comp_epaper_panel_adapter_t *adapter)
{
    adapter->host_dry_run = 1u;
}
void companion_r7_host_set_dc(bool data_mode) { g_dc_data = data_mode; }
bool companion_r7_host_spi_tx(const uint8_t *data, uint16_t length)
{
    if (!g_dc_data && length == 1u) {
        if (g_command_count < sizeof(g_commands)) {
            g_commands[g_command_count] = data[0];
            g_command_data_lengths[g_command_count] = 0u;
            g_command_data_first_bytes[g_command_count] = 0u;
            ++g_command_count;
        }
        if (data[0] == 0x26u) ++g_cleanup_26;
        if (data[0] == 0x20u) {
            g_refresh_active = true;
            g_busy_reads = 0u;
        }
    } else if (g_dc_data) {
        ++g_data_calls;
        if (g_command_count != 0u) {
            g_command_data_lengths[g_command_count - 1u] = length;
            g_command_data_first_bytes[g_command_count - 1u] = length == 0u ? 0u : data[0];
        }
        if (length == 1u && data[0] == 0xCFu) ++g_mode2_cf;
        if (length == 1u && data[0] == 0xFFu) ++g_mode2_ff;
    }
    return true;
}

static void wait_callback(void *context, uint32_t now_ms)
{
    (void)context; (void)now_ms; ++g_wait_callbacks;
    if (g_refresh_active) ++g_callbacks_during;
}

static void reset_trace(void)
{
    g_command_count = 0u;
    memset(g_command_data_lengths, 0, sizeof(g_command_data_lengths));
    memset(g_command_data_first_bytes, 0, sizeof(g_command_data_first_bytes));
    g_data_calls = 0u;
    g_cleanup_26 = 0u;
    g_mode2_cf = 0u;
    g_mode2_ff = 0u;
    g_busy_reads = 0u;
    g_refresh_active = false;
    g_busy_asserted = false;
    g_busy_released = false;
    g_callbacks_during = 0u;
    g_touch_before = 0u;
    g_touch_after = 0u;
}

static void touch_before(void) { ++g_touch_before; }
static void touch_after(void) { ++g_touch_after; }

static void assert_movement_trace(void)
{
    if (!companion_r7_runtime_host_validate_movement_trace(
            g_commands, g_command_data_lengths, g_command_data_first_bytes,
            g_command_count, 2u, 2u, g_busy_asserted, g_busy_released)) fail("movement trace");
    if (g_data_calls < 7u || g_cleanup_26 != 0u || g_mode2_cf != 1u || g_mode2_ff != 0u ||
        g_callbacks_during == 0u || g_touch_before != 1u || g_touch_after != 1u) fail("movement phases");
}

static void run_bounded(void)
{
    comp_epaper_panel_adapter_t adapter = {0};
    reset_trace();
    companion_r7_runtime_bridge_set_wait_service(wait_callback, NULL, 1u);
    companion_r7_runtime_bridge_init(&adapter);
    for (unsigned frame = 0u; frame < 16u; ++frame) {
        reset_trace();
        touch_before();
        const bool returned = companion_r7_runtime_bridge_service();
        touch_after();
        if (!returned) fail("bounded callback/return");
        assert_movement_trace();
    }
    reset_trace();
    if (!companion_r7_runtime_bridge_service() || g_cleanup_26 != 1u) fail("bounded cleanup");
}

static void run_service_fault(unsigned behavior)
{
    comp_epaper_panel_adapter_t adapter = {0};
    g_busy_behavior = 0u;
    companion_r7_runtime_bridge_init(&adapter);
    reset_trace();
    g_busy_behavior = behavior;
    if (companion_r7_runtime_bridge_service()) fail("fault first call accepted");
    if (companion_r7_runtime_bridge_service()) fail("fault second call accepted");
    g_busy_behavior = 0u;
}

static void run_negative_validator(void)
{
    const uint8_t good[] = {0x3Cu, 0x44u, 0x45u, 0x4Eu, 0x4Fu, 0x24u, 0x22u, 0x20u};
    const uint16_t lengths[] = {1u, 2u, 4u, 1u, 2u, 2610u, 1u, 0u};
    const uint8_t first[] = {0x80u, 4u, 0xADu, 4u, 0xADu, 0u, 0xCFu, 0u};
    uint8_t duplicate[9];
    uint16_t duplicate_lengths[9];
    uint8_t duplicate_first[9];
    memcpy(duplicate, good, sizeof(good));
    memcpy(duplicate_lengths, lengths, sizeof(lengths));
    memcpy(duplicate_first, first, sizeof(first));
    duplicate[8] = 0x20u; duplicate_lengths[8] = 0u; duplicate_first[8] = 0u;
    uint8_t forbidden[8]; memcpy(forbidden, good, sizeof(good)); forbidden[6] = 0x32u;
    if (companion_r7_runtime_host_validate_movement_trace(good, lengths, first, 8u, 481u, 2u, true, true)) fail("481 accepted");
    if (companion_r7_runtime_host_validate_movement_trace(good, lengths, first, 8u, 2u, 601u, true, true)) fail("601 accepted");
    if (companion_r7_runtime_host_validate_movement_trace(good, lengths, first, 8u, 2u, 2u, false, true)) fail("busy assert missing");
    if (companion_r7_runtime_host_validate_movement_trace(good, lengths, first, 8u, 2u, 2u, true, false)) fail("busy release missing");
    if (companion_r7_runtime_host_validate_movement_trace(duplicate, duplicate_lengths, duplicate_first, 9u, 2u, 2u, true, true)) fail("duplicate accepted");
    if (companion_r7_runtime_host_validate_movement_trace(forbidden, lengths, first, 8u, 2u, 2u, true, true)) fail("forbidden accepted");
}

int main(void)
{
#if defined(COMPANION_EPAPER_SSD1681_R7_RUNTIME_CONTINUOUS_DIAGNOSTIC) && \
    COMPANION_EPAPER_SSD1681_R7_RUNTIME_CONTINUOUS_DIAGNOSTIC
    comp_epaper_panel_adapter_t adapter = {0};
    companion_r7_runtime_bridge_set_wait_service(wait_callback, NULL, 1u);
    companion_r7_runtime_bridge_init(&adapter);
    for (unsigned frame = 0u; frame < 17u; ++frame) {
        reset_trace();
        touch_before();
        if (!companion_r7_runtime_bridge_service()) fail("continuous return");
        touch_after();
        assert_movement_trace();
    }
    if (g_cleanup_26 != 0u) fail("continuous frame16 cleanup");
    puts("COMP-REQ-466 host spy PASS continuous=17 cleanup=0 hardware_contact=0");
#else
    run_bounded();
    run_service_fault(3u);
    run_service_fault(1u);
    run_service_fault(2u);
    run_negative_validator();
    puts("COMP-REQ-466 host spy PASS bounded=16 cleanup=1 negative_transaction_481=pass negative_busy_601=pass negative_never_assert=pass negative_never_release=pass negative_duplicate_20=pass negative_forbidden_command=pass terminal_fault_second_call=pass");
#endif
    FILE *marker = fopen("comp-req-466-r7-runtime-host-pass.marker", "wb");
    if (marker == NULL) fail("marker");
    fputs("PASS\n", marker);
    fclose(marker);
    return 0;
}
