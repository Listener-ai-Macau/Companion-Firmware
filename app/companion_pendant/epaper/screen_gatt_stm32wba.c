#include "screen_gatt_stm32wba.h"

#include <string.h>

void companion_epaper_stm32wba_screen_gatt_init(
    companion_epaper_stm32wba_screen_gatt_t *gatt,
    const companion_epaper_stm32wba_screen_gatt_config_t *config)
{
    if (gatt == NULL) {
        return;
    }
    memset(gatt, 0, sizeof(*gatt));
    if (config != NULL) {
        gatt->config = *config;
    }
}

bool companion_epaper_stm32wba_screen_gatt_ready(
    const companion_epaper_stm32wba_screen_gatt_t *gatt)
{
    return gatt != NULL &&
           gatt->config.handle_card_write != NULL &&
           gatt->config.publish_card_status != NULL &&
           gatt->config.apply_settings_expression_hint != NULL &&
           gatt->config.schedule_display_task != NULL;
}

bool companion_epaper_stm32wba_settings_wants_sleepy(
    const companion_epaper_stm32wba_settings_v1_t *settings)
{
    return settings != NULL &&
           (settings->display_brightness == 0u ||
            (settings->flags & COMPANION_EPAPER_STM32WBA_QUIET_HOURS_SLEEPY_FLAG) != 0u);
}

bool companion_epaper_stm32wba_is_expression_request_id(uint32_t request_id)
{
    return (request_id & 0xf0000000u) ==
           COMPANION_EPAPER_STM32WBA_EXPRESSION_REQUEST_ID_BASE;
}

void companion_epaper_stm32wba_screen_gatt_publish_card_status(
    companion_epaper_stm32wba_screen_gatt_t *gatt,
    uint8_t card_slot,
    uint32_t request_id,
    companion_epaper_stm32wba_render_state_t render_state,
    companion_epaper_stm32wba_last_error_t last_error,
    uint32_t content_crc32)
{
    if (gatt == NULL || gatt->config.publish_card_status == NULL) {
        return;
    }

    companion_epaper_stm32wba_card_status_v1_t status = {
        .schema_version = 1u,
        .card_slot = card_slot,
        .render_state = (uint8_t)render_state,
        .last_error = (uint8_t)last_error,
        .request_id = request_id,
        .content_crc32 = content_crc32,
        .refresh_count = ++gatt->refresh_count,
    };
    gatt->config.publish_card_status(gatt->config.context, &status);
}

void companion_epaper_stm32wba_screen_gatt_accept_card_write(
    companion_epaper_stm32wba_screen_gatt_t *gatt,
    const companion_epaper_stm32wba_card_write_v1_t *request,
    const uint8_t *content,
    uint16_t content_len,
    uint32_t content_crc32)
{
    if (gatt == NULL || request == NULL || gatt->config.handle_card_write == NULL) {
        return;
    }
    gatt->config.handle_card_write(gatt->config.context,
                                   request,
                                   content,
                                   content_len);
    companion_epaper_stm32wba_screen_gatt_publish_card_status(
        gatt,
        request->card_slot,
        request->request_id,
        COMPANION_EPAPER_STM32WBA_RENDER_STATE_ACCEPTED,
        COMPANION_EPAPER_STM32WBA_LAST_ERROR_OK,
        content_crc32);
    if (gatt->config.schedule_display_task != NULL) {
        gatt->config.schedule_display_task(gatt->config.context);
    }
}

void companion_epaper_stm32wba_screen_gatt_handle_settings(
    companion_epaper_stm32wba_screen_gatt_t *gatt,
    const companion_epaper_stm32wba_settings_v1_t *settings)
{
    if (gatt == NULL || settings == NULL ||
        gatt->config.apply_settings_expression_hint == NULL) {
        return;
    }
    gatt->config.apply_settings_expression_hint(gatt->config.context,
                                                settings);
    if (gatt->config.schedule_display_task != NULL) {
        gatt->config.schedule_display_task(gatt->config.context);
    }
}
