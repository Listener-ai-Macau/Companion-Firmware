#ifndef COMPANION_EPAPER_SCREEN_GATT_STM32WBA_H
#define COMPANION_EPAPER_SCREEN_GATT_STM32WBA_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMPANION_EPAPER_STM32WBA_GATT_MAX_PAYLOAD_BYTES 248u
#define COMPANION_EPAPER_STM32WBA_EXPRESSION_CARD_SLOT 1u
#define COMPANION_EPAPER_STM32WBA_EXPRESSION_REQUEST_ID_BASE 0xe0000000u
#define COMPANION_EPAPER_STM32WBA_QUIET_HOURS_SLEEPY_FLAG 0x0001u

typedef enum {
    COMPANION_EPAPER_STM32WBA_RENDER_STATE_IDLE = 0,
    COMPANION_EPAPER_STM32WBA_RENDER_STATE_ACCEPTED = 1,
    COMPANION_EPAPER_STM32WBA_RENDER_STATE_RENDERED = 2,
    COMPANION_EPAPER_STM32WBA_RENDER_STATE_FAILED = 3,
    COMPANION_EPAPER_STM32WBA_RENDER_STATE_BUSY = 4,
} companion_epaper_stm32wba_render_state_t;

typedef enum {
    COMPANION_EPAPER_STM32WBA_LAST_ERROR_OK = 0,
    COMPANION_EPAPER_STM32WBA_LAST_ERROR_BAD_ARGUMENT = 1,
    COMPANION_EPAPER_STM32WBA_LAST_ERROR_QUEUE_FULL = 2,
    COMPANION_EPAPER_STM32WBA_LAST_ERROR_PAYLOAD_TOO_LONG = 3,
    COMPANION_EPAPER_STM32WBA_LAST_ERROR_DEFERRED_NO_PANEL = 4,
    COMPANION_EPAPER_STM32WBA_LAST_ERROR_DEFERRED_CONTROLLER_UNKNOWN = 5,
} companion_epaper_stm32wba_last_error_t;

typedef struct {
    uint8_t schema_version;
    uint8_t card_slot;
    uint16_t display_flags;
    uint32_t request_id;
    uint16_t utf8_title_len;
    uint16_t utf8_body_len;
} companion_epaper_stm32wba_card_write_v1_t;

typedef struct {
    uint8_t schema_version;
    uint8_t card_slot;
    uint8_t render_state;
    uint8_t last_error;
    uint32_t request_id;
    uint32_t content_crc32;
    uint32_t refresh_count;
} companion_epaper_stm32wba_card_status_v1_t;

typedef struct {
    uint8_t schema_version;
    uint8_t locale;
    uint16_t flags;
    int16_t time_zone_offset_min;
    uint8_t quiet_hours_start_min;
    uint8_t quiet_hours_end_min;
    uint8_t display_brightness;
    uint8_t recorder_profile_id;
} companion_epaper_stm32wba_settings_v1_t;

typedef void (*companion_epaper_stm32wba_card_write_fn_t)(
    void *context,
    const companion_epaper_stm32wba_card_write_v1_t *request,
    const uint8_t *content,
    uint16_t content_len);

typedef void (*companion_epaper_stm32wba_card_status_fn_t)(
    void *context,
    const companion_epaper_stm32wba_card_status_v1_t *status);

typedef void (*companion_epaper_stm32wba_settings_fn_t)(
    void *context,
    const companion_epaper_stm32wba_settings_v1_t *settings);

typedef void (*companion_epaper_stm32wba_screen_schedule_fn_t)(void *context);

typedef struct {
    companion_epaper_stm32wba_card_write_fn_t handle_card_write;
    companion_epaper_stm32wba_card_status_fn_t publish_card_status;
    companion_epaper_stm32wba_settings_fn_t apply_settings_expression_hint;
    companion_epaper_stm32wba_screen_schedule_fn_t schedule_display_task;
    void *context;
} companion_epaper_stm32wba_screen_gatt_config_t;

typedef struct {
    companion_epaper_stm32wba_screen_gatt_config_t config;
    uint32_t refresh_count;
} companion_epaper_stm32wba_screen_gatt_t;

void companion_epaper_stm32wba_screen_gatt_init(
    companion_epaper_stm32wba_screen_gatt_t *gatt,
    const companion_epaper_stm32wba_screen_gatt_config_t *config);

bool companion_epaper_stm32wba_screen_gatt_ready(
    const companion_epaper_stm32wba_screen_gatt_t *gatt);

bool companion_epaper_stm32wba_settings_wants_sleepy(
    const companion_epaper_stm32wba_settings_v1_t *settings);

bool companion_epaper_stm32wba_is_expression_request_id(uint32_t request_id);

void companion_epaper_stm32wba_screen_gatt_publish_card_status(
    companion_epaper_stm32wba_screen_gatt_t *gatt,
    uint8_t card_slot,
    uint32_t request_id,
    companion_epaper_stm32wba_render_state_t render_state,
    companion_epaper_stm32wba_last_error_t last_error,
    uint32_t content_crc32);

void companion_epaper_stm32wba_screen_gatt_accept_card_write(
    companion_epaper_stm32wba_screen_gatt_t *gatt,
    const companion_epaper_stm32wba_card_write_v1_t *request,
    const uint8_t *content,
    uint16_t content_len,
    uint32_t content_crc32);

void companion_epaper_stm32wba_screen_gatt_handle_settings(
    companion_epaper_stm32wba_screen_gatt_t *gatt,
    const companion_epaper_stm32wba_settings_v1_t *settings);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_SCREEN_GATT_STM32WBA_H */
