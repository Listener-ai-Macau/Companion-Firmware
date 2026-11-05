#include "ssd1681_read_only_controller_state.h"

#include <stdio.h>
#include <string.h>

static int expect_result(const char *name,
                         const uint8_t *chips,
                         size_t chip_count,
                         const uint8_t *options,
                         size_t option_bytes,
                         comp_ssd1681_controller_state_result_t expected)
{
    comp_ssd1681_controller_state_t state;
    comp_ssd1681_controller_state_result_t actual =
        comp_ssd1681_controller_state_decode(chips,
                                             chip_count,
                                             options,
                                             option_bytes,
                                             &state);
    if (actual != expected) {
        fprintf(stderr, "%s: expected %d, got %d\n", name, (int)expected, (int)actual);
        return 1;
    }
    return 0;
}

int main(void)
{
    uint8_t chips[3] = {0x01u, 0x01u, 0x01u};
    const uint8_t sample[11] = {
        0x12u, 0x34u, 0x01u, 0x02u, 0x03u, 0x04u, 0x45u, 0x56u, 0x57u, 0x58u, 0x59u,
    };
    uint8_t options[33];
    comp_ssd1681_controller_state_t state;
    int failures = 0;

    for (size_t group = 0u; group < 3u; ++group) {
        memcpy(&options[group * 11u], sample, sizeof(sample));
    }
    failures += expect_result("valid", chips, 3u, options, 33u,
                              COMP_SSD1681_CONTROLLER_STATE_OK);
    if (comp_ssd1681_controller_state_decode(chips, 3u, options, 33u, &state) !=
            COMP_SSD1681_CONTROLLER_STATE_OK ||
        !state.ping_pong_enabled || state.vcom_otp_selection != 0x12u ||
        state.vcom_register != 0x34u || state.waveform_version[3] != 0x59u) {
        fprintf(stderr, "decoded fields mismatch\n");
        failures++;
    }
    failures += expect_result("short", chips, 3u, options, 32u,
                              COMP_SSD1681_CONTROLLER_STATE_BAD_LENGTH);
    failures += expect_result("long", chips, 3u, options, 34u,
                              COMP_SSD1681_CONTROLLER_STATE_BAD_LENGTH);
    options[11u] ^= 0x01u;
    failures += expect_result("inconsistent", chips, 3u, options, 33u,
                              COMP_SSD1681_CONTROLLER_STATE_INCONSISTENT_DISPLAY_OPTION);
    options[11u] ^= 0x01u;
    chips[0u] = chips[1u] = chips[2u] = 0x02u;
    failures += expect_result("bad_id", chips, 3u, options, 33u,
                              COMP_SSD1681_CONTROLLER_STATE_BAD_CHIP_ID);
    chips[0u] = chips[1u] = chips[2u] = 0x05u;
    failures += expect_result("busy", chips, 3u, options, 33u,
                              COMP_SSD1681_CONTROLLER_STATE_BUSY);
    chips[0u] = chips[1u] = chips[2u] = 0x01u;
    memset(options, 0x00, sizeof(options));
    failures += expect_result("all00", chips, 3u, options, 33u,
                              COMP_SSD1681_CONTROLLER_STATE_ALL_ZERO_DISPLAY_OPTION);
    memset(options, 0xFF, sizeof(options));
    failures += expect_result("allff", chips, 3u, options, 33u,
                              COMP_SSD1681_CONTROLLER_STATE_ALL_FF_DISPLAY_OPTION);
    chips[2u] = 0x09u;
    failures += expect_result("chip_inconsistent", chips, 3u, options, 33u,
                              COMP_SSD1681_CONTROLLER_STATE_INCONSISTENT_CHIP_STATUS);

    if (failures != 0) {
        return 1;
    }
    puts("PASS: SSD1681 read-only controller-state decoder negative matrix");
    return 0;
}
