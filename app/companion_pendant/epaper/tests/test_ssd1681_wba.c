#include "ssd1681_wba.h"
#include "refresh_policy.h"

#include <stdio.h>
#include <string.h>

#define REQUIRE(condition)                                                       \
    do {                                                                         \
        if (!(condition)) {                                                       \
            fprintf(stderr, "FAIL:%d: %s\n", __LINE__, #condition);             \
            return 1;                                                            \
        }                                                                        \
    } while (0)

typedef struct {
    uint8_t command;
    uint32_t issued_ms;
    uint8_t data[4];
    uint16_t data_size;
    bool data_seen;
} command_record_t;

typedef struct {
    uint32_t now;
    uint32_t busy_until;
    uint32_t busy_from;
    uint32_t busy_delay_ms;
    uint32_t transfers;
    uint32_t transfers_this_poll;
    uint32_t reset_calls;
    uint32_t reset_asserts;
    uint32_t reset_releases;
    uint32_t fail_transfer_at;
    uint16_t maximum_transfer;
    uint8_t activation_commands;
    uint8_t stick_busy_on_activation;
    bool stuck_busy;
    bool suppress_busy;
    command_record_t commands[96];
    size_t command_count;
} fixture_t;

static bool transfer(void *context, bool data, const uint8_t *bytes, uint16_t size)
{
    fixture_t *fixture = context;

    fixture->transfers++;
    fixture->transfers_this_poll++;
    if (size > fixture->maximum_transfer) {
        fixture->maximum_transfer = size;
    }
    if (fixture->fail_transfer_at != 0u &&
        fixture->transfers == fixture->fail_transfer_at) {
        return false;
    }
    if (!data) {
        command_record_t *record;
        if (bytes == NULL || size != 1u ||
            fixture->command_count >=
                sizeof(fixture->commands) / sizeof(fixture->commands[0])) {
            return false;
        }
        record = &fixture->commands[fixture->command_count++];
        memset(record, 0, sizeof(*record));
        record->command = bytes[0];
        record->issued_ms = fixture->now;
        if (bytes[0] == 0x20u) {
            fixture->activation_commands++;
            if (fixture->stick_busy_on_activation != 0u &&
                fixture->activation_commands ==
                    fixture->stick_busy_on_activation) {
                fixture->stuck_busy = true;
            }
        }
        if (!fixture->suppress_busy &&
            (bytes[0] == 0x20u || bytes[0] == 0x12u)) {
            fixture->busy_from = fixture->now + fixture->busy_delay_ms;
            fixture->busy_until = fixture->busy_from + 2u;
        }
    } else {
        command_record_t *record;
        uint16_t copy;
        if (bytes == NULL || size == 0u || fixture->command_count == 0u) {
            return false;
        }
        record = &fixture->commands[fixture->command_count - 1u];
        if (!record->data_seen) {
            record->data_seen = true;
            record->data_size = size;
            copy = size < sizeof(record->data) ? size : sizeof(record->data);
            memcpy(record->data, bytes, copy);
        }
    }
    return true;
}

static bool set_reset(void *context, bool asserted)
{
    fixture_t *fixture = context;
    fixture->reset_calls++;
    if (asserted) {
        fixture->reset_asserts++;
    } else {
        fixture->reset_releases++;
    }
    return true;
}

static bool is_busy(void *context)
{
    fixture_t *fixture = context;
    return fixture->stuck_busy || (fixture->now >= fixture->busy_from &&
                                   fixture->now < fixture->busy_until);
}

static uint32_t now_ms(void *context)
{
    return ((fixture_t *)context)->now;
}

static comp_ssd1681_wba_config_t config(fixture_t *fixture)
{
    const comp_ssd1681_wba_config_t value = {
        .transfer = transfer,
        .set_reset = set_reset,
        .is_busy = is_busy,
        .now_ms = now_ms,
        .context = fixture,
        .payload_chunk_bytes = 32u,
        .busy_timeout_ms = 200u,
        .partial_limit = 2u,
    };
    return value;
}

static comp_ssd1681_wba_status_t run_to_terminal(comp_ssd1681_wba_t *driver,
                                                  fixture_t *fixture)
{
    for (unsigned count = 0u; count < 4000u; ++count) {
        comp_ssd1681_wba_status_t status;
        fixture->transfers_this_poll = 0u;
        status = comp_ssd1681_wba_poll(driver);
        if (fixture->transfers_this_poll > 1u) {
            return COMP_SSD1681_WBA_ERROR;
        }
        if (status != COMP_SSD1681_WBA_ACTIVE) {
            return status;
        }
        fixture->now++;
    }
    return COMP_SSD1681_WBA_ACTIVE;
}

static bool command_trace_equals(const fixture_t *fixture,
                                 const uint8_t *expected,
                                 size_t expected_count)
{
    if (fixture->command_count != expected_count) {
        fprintf(stderr, "command count %zu != %zu\n",
                fixture->command_count, expected_count);
        return false;
    }
    for (size_t index = 0u; index < expected_count; ++index) {
        if (fixture->commands[index].command != expected[index]) {
            fprintf(stderr, "command[%zu]=%02X expected=%02X\n", index,
                    fixture->commands[index].command, expected[index]);
            return false;
        }
    }
    return true;
}

static size_t command_count(const fixture_t *fixture, uint8_t command)
{
    size_t count = 0u;
    for (size_t index = 0u; index < fixture->command_count; ++index) {
        if (fixture->commands[index].command == command) count++;
    }
    return count;
}

static bool contains_window(const fixture_t *fixture, uint8_t x,
                            uint16_t controller_y)
{
    for (size_t index = 0u; index + 3u < fixture->command_count; ++index) {
        if (fixture->commands[index].command == 0x44u &&
            fixture->commands[index].data[0] == x &&
            fixture->commands[index + 1u].command == 0x45u &&
            fixture->commands[index + 3u].command == 0x4Fu &&
            fixture->commands[index + 3u].data[0] ==
                (uint8_t)controller_y) {
            return true;
        }
    }
    return false;
}

static int test_missing_reset_is_not_ready(void)
{
    fixture_t fixture = {0};
    comp_ssd1681_wba_t driver;
    comp_ssd1681_wba_config_t value = config(&fixture);

    value.set_reset = NULL;
    REQUIRE(!comp_ssd1681_wba_init(&driver, &value));
    REQUIRE(comp_ssd1681_wba_status(&driver) == COMP_SSD1681_WBA_NOT_READY);
    REQUIRE(comp_ssd1681_wba_error(&driver) ==
            COMP_SSD1681_WBA_ERROR_CONFIGURATION);
    REQUIRE(fixture.transfers == 0u);
    return 0;
}

static int test_full_and_partial_trace(void)
{
    static const uint8_t expected_full[] = {
        0x12u,
        0x18u, 0x22u, 0x20u,
        0x1Au, 0x22u, 0x20u,
        0x01u, 0x11u, 0x44u, 0x45u, 0x3Cu, 0x18u, 0x4Eu, 0x4Fu, 0x26u,
        0x01u, 0x11u, 0x44u, 0x45u, 0x3Cu, 0x18u, 0x4Eu, 0x4Fu, 0x24u,
        0x22u, 0x20u,
        0x01u, 0x11u, 0x44u, 0x45u, 0x3Cu, 0x18u, 0x4Eu, 0x4Fu, 0x26u,
        0x22u, 0x20u,
    };
    static const uint8_t expected_partial[] = {
        0x3Cu, 0x44u, 0x45u, 0x4Eu, 0x4Fu, 0x24u, 0x22u, 0x20u,
    };
    uint8_t previous[COMP_SSD1681_WBA_FRAME_BYTES];
    uint8_t current[COMP_SSD1681_WBA_FRAME_BYTES];
    const comp_ssd1681_wba_window_t window = {2u, 3u, 10u, 11u};
    fixture_t fixture = {0};
    comp_ssd1681_wba_t driver;
    comp_ssd1681_wba_stats_t stats;
    comp_ssd1681_wba_config_t value = config(&fixture);

    memset(previous, 0xAA, sizeof(previous));
    memset(current, 0x55, sizeof(current));
    REQUIRE(comp_ssd1681_wba_init(&driver, &value));
    REQUIRE(comp_ssd1681_wba_start_full(&driver, previous, current,
                                         sizeof(current)));
    REQUIRE(run_to_terminal(&driver, &fixture) == COMP_SSD1681_WBA_COMPLETE);
    REQUIRE(fixture.reset_asserts == 1u && fixture.reset_releases == 1u);
    REQUIRE(fixture.maximum_transfer <= 32u);
    REQUIRE(command_trace_equals(&fixture, expected_full,
                                 sizeof(expected_full)));
    /* Recover the whole physical field with the vendor full-update waveform,
     * rather than treating its 100-degree fast C7 profile as a clean full. */
    REQUIRE(fixture.commands[25].command == 0x22u);
    REQUIRE(fixture.commands[25].data[0] == 0xF7u);
    REQUIRE(fixture.commands[36].data[0] == 0x99u);
    REQUIRE(comp_ssd1681_wba_baseline_valid(&driver));
    REQUIRE(!comp_ssd1681_wba_maintenance_required(&driver));
    comp_ssd1681_wba_get_stats(&driver, &stats);
    REQUIRE(stats.completed_full == 1u && stats.partial_count == 0u);

    REQUIRE(comp_ssd1681_wba_start_full(&driver, previous, current,
                                         sizeof(current)));
    REQUIRE(!comp_ssd1681_wba_baseline_valid(&driver));
    comp_ssd1681_wba_cancel(&driver);
    REQUIRE(comp_ssd1681_wba_init(&driver, &value));
    REQUIRE(comp_ssd1681_wba_start_full(&driver, previous, current,
                                         sizeof(current)));
    REQUIRE(run_to_terminal(&driver, &fixture) == COMP_SSD1681_WBA_COMPLETE);

    memset(fixture.commands, 0, sizeof(fixture.commands));
    fixture.command_count = 0u;
    REQUIRE(comp_ssd1681_wba_start_partial(&driver, current,
                                            sizeof(current), &window));
    REQUIRE(run_to_terminal(&driver, &fixture) == COMP_SSD1681_WBA_COMPLETE);
    REQUIRE(command_trace_equals(&fixture, expected_partial,
                                 sizeof(expected_partial)));
    REQUIRE(fixture.commands[0].data[0] == 0x80u);
    REQUIRE(fixture.commands[1].data[0] == 2u &&
            fixture.commands[1].data[1] == 3u);
    REQUIRE(fixture.commands[2].data[0] == 189u &&
            fixture.commands[2].data[1] == 0u &&
            fixture.commands[2].data[2] == 188u &&
            fixture.commands[2].data[3] == 0u);
    REQUIRE(fixture.commands[6].data[0] == 0xCFu);
    REQUIRE(comp_ssd1681_wba_start_partial(&driver, current,
                                            sizeof(current), &window));
    REQUIRE(run_to_terminal(&driver, &fixture) == COMP_SSD1681_WBA_COMPLETE);
    REQUIRE(comp_ssd1681_wba_maintenance_required(&driver));
    REQUIRE(!comp_ssd1681_wba_start_partial(&driver, current,
                                             sizeof(current), &window));
    REQUIRE(comp_ssd1681_wba_error(&driver) ==
            COMP_SSD1681_WBA_ERROR_MAINTENANCE_REQUIRED);
    comp_ssd1681_wba_get_stats(&driver, &stats);
    REQUIRE(stats.completed_partial == 2u && stats.partial_count == 2u);
    fixture.command_count=0u;
    REQUIRE(comp_ssd1681_wba_start_fast(&driver,current,sizeof(current)));
    REQUIRE(run_to_terminal(&driver,&fixture)==COMP_SSD1681_WBA_COMPLETE);
    REQUIRE(command_trace_equals(&fixture,expected_partial,sizeof(expected_partial)));
    REQUIRE(fixture.commands[1].data[0]==0 && fixture.commands[1].data[1]==24);
    REQUIRE(fixture.commands[6].data[0]==0xFFu);
    REQUIRE(!comp_ssd1681_wba_maintenance_required(&driver));
    comp_ssd1681_wba_get_stats(&driver,&stats);
    REQUIRE(stats.completed_fast==1 && stats.partial_count==0 && stats.completed_full==1);
    fixture.command_count=0u;
    REQUIRE(comp_ssd1681_wba_start_partial(&driver,current,sizeof(current),&window));
    REQUIRE(run_to_terminal(&driver,&fixture)==COMP_SSD1681_WBA_COMPLETE);
    REQUIRE(fixture.commands[6].data[0]==0xCFu); /* next operation returns to local */
    return 0;
}

static int test_failures_are_visible_and_invalidate_baseline(void)
{
    uint8_t previous[COMP_SSD1681_WBA_FRAME_BYTES] = {0};
    uint8_t current[COMP_SSD1681_WBA_FRAME_BYTES] = {0};
    fixture_t fixture = {0};
    comp_ssd1681_wba_t driver;
    comp_ssd1681_wba_config_t value = config(&fixture);

    fixture.fail_transfer_at = 1u;
    REQUIRE(comp_ssd1681_wba_init(&driver, &value));
    REQUIRE(comp_ssd1681_wba_start_full(&driver, previous, current,
                                         sizeof(current)));
    REQUIRE(run_to_terminal(&driver, &fixture) == COMP_SSD1681_WBA_ERROR);
    REQUIRE(comp_ssd1681_wba_error(&driver) ==
            COMP_SSD1681_WBA_ERROR_TRANSPORT);
    REQUIRE(!comp_ssd1681_wba_baseline_valid(&driver));

    /* Even if poll is called again while the command tick is unchanged, an
     * idle BUSY input cannot complete a visible activation. This preserves
     * the accepted WB55 busy-edge contract. */
    memset(&fixture, 0, sizeof(fixture));
    value = config(&fixture);
    value.busy_timeout_ms = 200u;
    fixture.suppress_busy = true;
    REQUIRE(comp_ssd1681_wba_init(&driver, &value));
    REQUIRE(comp_ssd1681_wba_start_full(&driver, previous, current,
                                         sizeof(current)));
    REQUIRE(run_to_terminal(&driver, &fixture) == COMP_SSD1681_WBA_ERROR);
    REQUIRE(comp_ssd1681_wba_error(&driver) ==
            COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT);
    REQUIRE(!comp_ssd1681_wba_baseline_valid(&driver));

    memset(&fixture, 0, sizeof(fixture));
    value = config(&fixture);
    value.busy_timeout_ms = 5u;
    fixture.stuck_busy = true;
    REQUIRE(comp_ssd1681_wba_init(&driver, &value));
    REQUIRE(comp_ssd1681_wba_start_full(&driver, previous, current,
                                         sizeof(current)));
    REQUIRE(run_to_terminal(&driver, &fixture) == COMP_SSD1681_WBA_ERROR);
    REQUIRE(comp_ssd1681_wba_error(&driver) ==
            COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT);
    REQUIRE(!comp_ssd1681_wba_baseline_valid(&driver));

    memset(&fixture, 0, sizeof(fixture));
    value = config(&fixture);
    REQUIRE(comp_ssd1681_wba_init(&driver, &value));
    REQUIRE(comp_ssd1681_wba_start_full(&driver, previous, current,
                                         sizeof(current)));
    comp_ssd1681_wba_cancel(&driver);
    REQUIRE(comp_ssd1681_wba_error(&driver) ==
            COMP_SSD1681_WBA_ERROR_CANCELLED);
    REQUIRE(fixture.reset_releases == 1u);
    return 0;
}

static int test_visible_busy_stuck_honors_deadline(void)
{
    uint8_t previous[COMP_SSD1681_WBA_FRAME_BYTES];
    uint8_t current[COMP_SSD1681_WBA_FRAME_BYTES];
    fixture_t fixture = {0};
    comp_ssd1681_wba_t driver;
    comp_ssd1681_wba_stats_t stats;
    comp_ssd1681_wba_config_t value = config(&fixture);

    memset(previous, 0xFF, sizeof(previous));
    memset(current, 0xA5, sizeof(current));
    /* A full operation uses 0x20 for temperature, LUT, then visible F7.
     * Stall only the visible activation so this cannot pass through an
     * earlier ready-wait timeout. */
    fixture.stick_busy_on_activation = 3u;
    REQUIRE(comp_ssd1681_wba_init(&driver, &value));
    REQUIRE(comp_ssd1681_wba_start_full(&driver, previous, current,
                                        sizeof(current)));
    REQUIRE(run_to_terminal(&driver, &fixture) == COMP_SSD1681_WBA_ERROR);
    REQUIRE(comp_ssd1681_wba_error(&driver) ==
            COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT);
    REQUIRE(!comp_ssd1681_wba_baseline_valid(&driver));
    REQUIRE(fixture.activation_commands == 3u);
    comp_ssd1681_wba_get_stats(&driver, &stats);
    REQUIRE(stats.busy_timeouts == 1u);
    REQUIRE(stats.completed_full == 0u);
    return 0;
}

static int test_recording_exact_delta_transaction(void)
{
    uint8_t previous[COMP_SSD1681_WBA_FRAME_BYTES];
    uint8_t current[COMP_SSD1681_WBA_FRAME_BYTES];
    const comp_ssd1681_wba_window_t recording = {
        COMP_SSD1681_WBA_RECORDING_CONTROLLER_X_BYTE_MIN,
        COMP_SSD1681_WBA_RECORDING_CONTROLLER_X_BYTE_MAX,
        COMP_SSD1681_WBA_RECORDING_CONTROLLER_Y_MIN,
        COMP_SSD1681_WBA_RECORDING_CONTROLLER_Y_MAX,
    };
    const uint16_t wave_y =
        COMP_SSD1681_WBA_RECORDING_CONTROLLER_Y_MIN + 1u;
    const uint16_t microphone_y =
        COMP_SSD1681_WBA_RECORDING_CONTROLLER_Y_MIN + 10u;
    const uint16_t below_recording_y =
        COMP_SSD1681_WBA_RECORDING_CONTROLLER_Y_MAX + 1u;
    const uint8_t right_of_recording_x =
        COMP_SSD1681_WBA_RECORDING_CONTROLLER_X_BYTE_MAX + 1u;
    fixture_t fixture = {0};
    comp_ssd1681_wba_t driver;
    comp_ssd1681_wba_stats_t stats;
    comp_ssd1681_wba_config_t value = config(&fixture);

    value.partial_limit = UINT8_MAX;
    memset(previous, 0xFF, sizeof(previous));
    memset(current, 0xFF, sizeof(current));
    REQUIRE(comp_ssd1681_wba_init(&driver, &value));
    REQUIRE(comp_ssd1681_wba_start_full(&driver, previous, current,
                                        sizeof(current)));
    REQUIRE(run_to_terminal(&driver, &fixture) == COMP_SSD1681_WBA_COMPLETE);

    memset(fixture.commands, 0, sizeof(fixture.commands));
    fixture.command_count = 0u;
    fixture.activation_commands = 0u;
    /* Static microphone byte inside the protected recording window. */
    previous[microphone_y * COMP_SSD1681_WBA_BYTES_PER_ROW + 3u] = 0x00u;
    current[microphone_y * COMP_SSD1681_WBA_BYTES_PER_ROW + 3u] = 0x00u;
    /* One changing wave byte and one simultaneous ordinary face byte. */
    previous[wave_y * COMP_SSD1681_WBA_BYTES_PER_ROW + 1u] = 0xF0u;
    current[wave_y * COMP_SSD1681_WBA_BYTES_PER_ROW + 1u] = 0x0Fu;
    current[100u * COMP_SSD1681_WBA_BYTES_PER_ROW + 10u] = 0x7Fu;

    REQUIRE(comp_ssd1681_wba_start_recording_partial(
        &driver, previous, current, sizeof(current), &recording));
    REQUIRE(run_to_terminal(&driver, &fixture) == COMP_SSD1681_WBA_COMPLETE);
    REQUIRE(command_count(&fixture, 0x26u) == 1u);
    REQUIRE(command_count(&fixture, 0x24u) == 4u);
    REQUIRE(command_count(&fixture, 0x20u) == 1u);
    REQUIRE(fixture.activation_commands == 1u);
    REQUIRE(contains_window(&fixture, 1u,
        (COMP_SSD1681_WBA_HEIGHT - 1u) - wave_y));
    REQUIRE(contains_window(&fixture, right_of_recording_x,
        (COMP_SSD1681_WBA_HEIGHT - 1u) - wave_y));
    REQUIRE(contains_window(&fixture, 1u,
        (COMP_SSD1681_WBA_HEIGHT - 1u) - below_recording_y));
    REQUIRE(!contains_window(&fixture, 3u,
        (COMP_SSD1681_WBA_HEIGHT - 1u) - microphone_y));
    comp_ssd1681_wba_get_stats(&driver, &stats);
    REQUIRE(stats.completed_recording == 1u);
    REQUIRE(stats.completed_partial == 1u);

    /* A dirty rectangle wholly to the right is clipped to its original x
     * bounds; splitting must not expand it back to the safe-window edge. */
    memcpy(previous, current, sizeof(previous));
    current[microphone_y * COMP_SSD1681_WBA_BYTES_PER_ROW + 10u] ^= 0x40u;
    memset(fixture.commands, 0, sizeof(fixture.commands));
    fixture.command_count = 0u;
    fixture.activation_commands = 0u;
    REQUIRE(comp_ssd1681_wba_start_recording_partial(
        &driver, previous, current, sizeof(current), &recording));
    REQUIRE(run_to_terminal(&driver, &fixture) == COMP_SSD1681_WBA_COMPLETE);
    REQUIRE(command_count(&fixture, 0x26u) == 0u);
    REQUIRE(command_count(&fixture, 0x24u) == 1u);
    REQUIRE(contains_window(&fixture, 10u,
        (COMP_SSD1681_WBA_HEIGHT - 1u) - microphone_y));
    REQUIRE(!contains_window(&fixture, right_of_recording_x,
        (COMP_SSD1681_WBA_HEIGHT - 1u) - microphone_y));

    /* A transport failure and a visible BUSY timeout both fail closed. */
    memcpy(previous, current, sizeof(previous));
    current[(wave_y + 1u) * COMP_SSD1681_WBA_BYTES_PER_ROW + 1u] ^= 0x80u;
    fixture.fail_transfer_at = fixture.transfers + 1u;
    REQUIRE(comp_ssd1681_wba_start_recording_partial(
        &driver, previous, current, sizeof(current), &recording));
    REQUIRE(run_to_terminal(&driver, &fixture) == COMP_SSD1681_WBA_ERROR);
    REQUIRE(comp_ssd1681_wba_error(&driver) ==
            COMP_SSD1681_WBA_ERROR_TRANSPORT);
    REQUIRE(!comp_ssd1681_wba_baseline_valid(&driver));

    memset(&fixture, 0, sizeof(fixture));
    value = config(&fixture);
    REQUIRE(comp_ssd1681_wba_init(&driver, &value));
    REQUIRE(comp_ssd1681_wba_start_full(&driver, previous, previous,
                                        sizeof(previous)));
    REQUIRE(run_to_terminal(&driver, &fixture) == COMP_SSD1681_WBA_COMPLETE);
    fixture.activation_commands = 0u;
    fixture.stick_busy_on_activation = 1u;
    REQUIRE(comp_ssd1681_wba_start_recording_partial(
        &driver, previous, current, sizeof(current), &recording));
    REQUIRE(run_to_terminal(&driver, &fixture) == COMP_SSD1681_WBA_ERROR);
    REQUIRE(comp_ssd1681_wba_error(&driver) ==
            COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT);
    REQUIRE(fixture.activation_commands == 1u);
    return 0;
}

static int test_explicit_software_reset_and_failure(void)
{
    uint8_t previous[COMP_SSD1681_WBA_FRAME_BYTES];
    uint8_t current[COMP_SSD1681_WBA_FRAME_BYTES];
    const comp_ssd1681_wba_window_t window = {0u, 1u, 0u, 1u};
    fixture_t fixture = {0};
    comp_ssd1681_wba_t driver;
    comp_ssd1681_wba_config_t value = config(&fixture);
    memset(previous, 0xFF, sizeof(previous));
    memset(current, 0xAA, sizeof(current));
    value.reset_mode = COMP_SSD1681_WBA_RESET_SOFTWARE_ONLY;
    /* A dummy or accidentally bound GPIO callback must not mask the mode. */
    REQUIRE(!comp_ssd1681_wba_init(&driver, &value));
    value.set_reset = NULL;
    REQUIRE(comp_ssd1681_wba_init(&driver, &value));
    REQUIRE(comp_ssd1681_wba_start_full(&driver, previous, current, sizeof(current)));
    REQUIRE(run_to_terminal(&driver, &fixture) == COMP_SSD1681_WBA_COMPLETE);
    REQUIRE(fixture.reset_calls == 0u);
    REQUIRE(fixture.commands[0].command == 0x12u);
    REQUIRE(command_count(&fixture, 0x10u) == 0u);
    REQUIRE(comp_ssd1681_wba_baseline_valid(&driver));
    REQUIRE(comp_ssd1681_wba_start_partial(&driver, current, sizeof(current), &window));
    /* Cancellation cannot call a nonexistent RESET endpoint. */
    comp_ssd1681_wba_cancel(&driver);
    REQUIRE(comp_ssd1681_wba_error(&driver) == COMP_SSD1681_WBA_ERROR_CANCELLED);
    REQUIRE(!comp_ssd1681_wba_baseline_valid(&driver));
    REQUIRE(fixture.reset_calls == 0u);
    /* Deep sleep/stuck BUSY cannot be solved by 0x12. Do not send commands
     * while BUSY or pretend that the power switch was exercised. */
    memset(&fixture, 0, sizeof(fixture));
    fixture.stuck_busy = true;
    REQUIRE(comp_ssd1681_wba_init(&driver, &value));
    REQUIRE(comp_ssd1681_wba_start_full(&driver, previous, current, sizeof(current)));
    REQUIRE(run_to_terminal(&driver, &fixture) == COMP_SSD1681_WBA_ERROR);
    REQUIRE(comp_ssd1681_wba_error(&driver) == COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT);
    REQUIRE(fixture.transfers == 0u && fixture.reset_calls == 0u);
    fixture.stuck_busy = false;
    REQUIRE(comp_ssd1681_wba_start_full(&driver, previous, current, sizeof(current)));
    REQUIRE(run_to_terminal(&driver, &fixture) == COMP_SSD1681_WBA_COMPLETE);
    REQUIRE(fixture.reset_calls == 0u && command_count(&fixture, 0x10u) == 0u);
    value.reset_mode = (comp_ssd1681_wba_reset_mode_t)42;
    REQUIRE(!comp_ssd1681_wba_init(&driver, &value));
    return 0;
}

static int test_delayed_busy_profile_settle(void)
{
    uint8_t frame[COMP_SSD1681_WBA_FRAME_BYTES];
    fixture_t fixture = {0};
    comp_ssd1681_wba_t driver;
    comp_ssd1681_wba_config_t value = config(&fixture);
    memset(frame, 0xFF, sizeof(frame));
    fixture.busy_delay_ms = 5u;
    REQUIRE(comp_ssd1681_wba_init(&driver, &value));
    REQUIRE(comp_ssd1681_wba_start_full(&driver, frame, frame, sizeof(frame)));
    REQUIRE(run_to_terminal(&driver, &fixture) == COMP_SSD1681_WBA_COMPLETE);
    unsigned profile_loads = 0u;
    for (size_t i = 1u; i + 1u < fixture.command_count; ++i) {
        if (fixture.commands[i].command == 0x20u &&
            fixture.commands[i-1u].command == 0x22u &&
            (fixture.commands[i-1u].data[0] == 0xB1u ||
             fixture.commands[i-1u].data[0] == 0x91u)) {
            REQUIRE(fixture.commands[i+1u].issued_ms - fixture.commands[i].issued_ms >= 120u);
            ++profile_loads;
        }
    }
    REQUIRE(profile_loads == 2u);
    REQUIRE(fixture.now - fixture.commands[fixture.command_count-1u].issued_ms >= 10u);
    REQUIRE(driver.stats.completed_full == 1u);
    /* A quiet line never qualifies the visible refresh, even after settling. */
    memset(&fixture, 0, sizeof(fixture));
    fixture.suppress_busy = true;
    REQUIRE(comp_ssd1681_wba_init(&driver, &value));
    REQUIRE(comp_ssd1681_wba_start_full(&driver, frame, frame, sizeof(frame)));
    REQUIRE(run_to_terminal(&driver, &fixture) == COMP_SSD1681_WBA_ERROR);
    REQUIRE(driver.stats.completed_full == 0u && !comp_ssd1681_wba_baseline_valid(&driver));
    return 0;
}

int main(void)
{
    if (!comp_epaper_refresh_policy_self_test()) {
        fputs("FAIL: existing refresh policy self-test\n", stderr);
        return 1;
    }
    if (test_missing_reset_is_not_ready() != 0 ||
        test_explicit_software_reset_and_failure() != 0 ||
        test_delayed_busy_profile_settle() != 0 ||
        test_full_and_partial_trace() != 0 ||
        test_failures_are_visible_and_invalidate_baseline() != 0 ||
        test_visible_busy_stuck_honors_deadline() != 0 ||
        test_recording_exact_delta_transaction() != 0) {
        return 1;
    }
    puts("PASS: WBA SSD1681 bounded transactions, recording exact-delta path, "
         "and existing refresh policy");
    return 0;
}
