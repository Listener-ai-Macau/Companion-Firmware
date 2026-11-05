#include "ssd1681_read_only_controller_state.h"

#include <string.h>

comp_ssd1681_controller_state_result_t comp_ssd1681_controller_state_decode(
    const uint8_t *chip_status_reads,
    size_t chip_status_read_count,
    const uint8_t *display_option_reads,
    size_t display_option_read_bytes,
    comp_ssd1681_controller_state_t *out_state)
{
    const size_t expected_display_bytes =
        COMP_SSD1681_CONTROLLER_STATE_GROUPS * COMP_SSD1681_DISPLAY_OPTION_BYTES;
    bool all_zero = true;
    bool all_ff = true;

    if (chip_status_reads == NULL || display_option_reads == NULL || out_state == NULL) {
        return COMP_SSD1681_CONTROLLER_STATE_BAD_ARGUMENT;
    }
    if (chip_status_read_count != COMP_SSD1681_CONTROLLER_STATE_GROUPS ||
        display_option_read_bytes != expected_display_bytes) {
        return COMP_SSD1681_CONTROLLER_STATE_BAD_LENGTH;
    }
    for (size_t group = 1u; group < COMP_SSD1681_CONTROLLER_STATE_GROUPS; ++group) {
        if (chip_status_reads[group] != chip_status_reads[0u]) {
            return COMP_SSD1681_CONTROLLER_STATE_INCONSISTENT_CHIP_STATUS;
        }
    }
    if ((chip_status_reads[0u] & 0x03u) != 0x01u) {
        return COMP_SSD1681_CONTROLLER_STATE_BAD_CHIP_ID;
    }
    if ((chip_status_reads[0u] & 0x04u) != 0u) {
        return COMP_SSD1681_CONTROLLER_STATE_BUSY;
    }
    for (size_t group = 1u; group < COMP_SSD1681_CONTROLLER_STATE_GROUPS; ++group) {
        if (memcmp(&display_option_reads[group * COMP_SSD1681_DISPLAY_OPTION_BYTES],
                   display_option_reads,
                   COMP_SSD1681_DISPLAY_OPTION_BYTES) != 0) {
            return COMP_SSD1681_CONTROLLER_STATE_INCONSISTENT_DISPLAY_OPTION;
        }
    }
    for (size_t index = 0u; index < COMP_SSD1681_DISPLAY_OPTION_BYTES; ++index) {
        all_zero = all_zero && display_option_reads[index] == 0x00u;
        all_ff = all_ff && display_option_reads[index] == 0xFFu;
    }
    if (all_zero) {
        return COMP_SSD1681_CONTROLLER_STATE_ALL_ZERO_DISPLAY_OPTION;
    }
    if (all_ff) {
        return COMP_SSD1681_CONTROLLER_STATE_ALL_FF_DISPLAY_OPTION;
    }

    memset(out_state, 0, sizeof(*out_state));
    out_state->chip_status = chip_status_reads[0u];
    out_state->vcom_otp_selection = display_option_reads[0u];
    out_state->vcom_register = display_option_reads[1u];
    memcpy(out_state->display_option, &display_option_reads[2u], sizeof(out_state->display_option));
    out_state->ping_pong_enabled = (display_option_reads[6u] & 0x40u) != 0u;
    memcpy(out_state->waveform_version,
           &display_option_reads[7u],
           sizeof(out_state->waveform_version));
    return COMP_SSD1681_CONTROLLER_STATE_OK;
}
