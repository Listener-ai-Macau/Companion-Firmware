#ifndef COMPANION_SSD1681_READ_ONLY_CONTROLLER_STATE_H
#define COMPANION_SSD1681_READ_ONLY_CONTROLLER_STATE_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define COMP_SSD1681_CONTROLLER_STATE_GROUPS 3u
#define COMP_SSD1681_CHIP_STATUS_BYTES 1u
#define COMP_SSD1681_DISPLAY_OPTION_BYTES 11u

typedef enum {
    COMP_SSD1681_CONTROLLER_STATE_OK = 0,
    COMP_SSD1681_CONTROLLER_STATE_BAD_ARGUMENT,
    COMP_SSD1681_CONTROLLER_STATE_BAD_LENGTH,
    COMP_SSD1681_CONTROLLER_STATE_INCONSISTENT_CHIP_STATUS,
    COMP_SSD1681_CONTROLLER_STATE_BAD_CHIP_ID,
    COMP_SSD1681_CONTROLLER_STATE_BUSY,
    COMP_SSD1681_CONTROLLER_STATE_INCONSISTENT_DISPLAY_OPTION,
    COMP_SSD1681_CONTROLLER_STATE_ALL_ZERO_DISPLAY_OPTION,
    COMP_SSD1681_CONTROLLER_STATE_ALL_FF_DISPLAY_OPTION,
} comp_ssd1681_controller_state_result_t;

typedef struct {
    uint8_t chip_status;
    uint8_t vcom_otp_selection;
    uint8_t vcom_register;
    uint8_t display_option[5];
    bool ping_pong_enabled;
    uint8_t waveform_version[4];
} comp_ssd1681_controller_state_t;

comp_ssd1681_controller_state_result_t comp_ssd1681_controller_state_decode(
    const uint8_t *chip_status_reads,
    size_t chip_status_read_count,
    const uint8_t *display_option_reads,
    size_t display_option_read_bytes,
    comp_ssd1681_controller_state_t *out_state);

#endif /* COMPANION_SSD1681_READ_ONLY_CONTROLLER_STATE_H */
