/* Engineering transaction-core comparison only.
 * Original FW54/74 source SHA256: 2d9f8d4bdf1380ce3e9eeba67efa08a2d798e98f011cc20f0469b952b613e0b3
 * Only passive BUSY/start-delay telemetry is added. Default builds
 * continue compiling ssd1681_wba.c. No new LUT or reset fiction. */
#include "ssd1681_wba.h"

#include <string.h>

#define RESET_HOLD_MS 10u
#define RESET_RELEASE_MS 10u
#define SOFTWARE_RESET_SETTLE_MS 10u
/* The accepted WB55 profile waits 120ms after temperature/LUT activation.
 * A low BUSY sampled immediately after 0x20 can precede its assertion. Keep
 * this as a foreground state, never a delay in the audio capture cycle. */
#define MODE1_PROFILE_SETTLE_MS 120u
#define MODE2_REARM_SETTLE_MS 120u
#define DEFAULT_CHUNK_BYTES 64u
#define MAX_CHUNK_BYTES 512u
#define DEFAULT_BUSY_TIMEOUT_MS 5000u
#define REFRESH_START_TIMEOUT_MS 100u
/* Qualify ready across foreground polls. A short low during an update must
 * not commit the frame or let the next transaction write into a busy panel. */
#define BUSY_READY_STABLE_MS 20u

enum {
    OP_NONE = 0,
    OP_FULL,
    OP_PARTIAL,
    OP_FAST,
    OP_RECORDING,
};

enum {
    ST_IDLE = 0,
    ST_RESET_ASSERT,
    ST_RESET_ASSERT_WAIT,
    ST_RESET_RELEASE,
    ST_RESET_RELEASE_WAIT,
    ST_WAIT_RESET_READY,
    ST_SOFTWARE_RESET,
    ST_WAIT_SOFTWARE_RESET,
    ST_SEQUENCE,
    ST_WAIT_MODE1_TEMP,
    ST_WAIT_MODE1_LUT,
    ST_DATA,
    ST_WAIT_VISIBLE,
    ST_WAIT_REARM,
};

enum {
    SEQ_NONE = 0,
    SEQ_MODE1_TEMP,
    SEQ_MODE1_LUT,
    SEQ_FULL_OLD_WINDOW,
    SEQ_FULL_CURRENT_WINDOW,
    SEQ_FULL_ACTIVATE,
    SEQ_FULL_REBASE_WINDOW,
    SEQ_REARM_MODE2,
    SEQ_PARTIAL_WINDOW,
    SEQ_PARTIAL_ACTIVATE,
    SEQ_RECORDING_WINDOW,
};

enum {
    RECORDING_PHASE_ORDINARY = 0,
    RECORDING_PHASE_OLD,
    RECORDING_PHASE_CURRENT,
    RECORDING_PHASE_POST_CURRENT,
    RECORDING_PHASE_POST_PREVIOUS,
};

typedef struct {
    uint8_t command;
    const uint8_t *data;
    uint8_t size;
} sequence_item_t;

static const uint8_t k_80[] = {0x80u};
static const uint8_t k_b1[] = {0xB1u};
static const uint8_t k_driver[] = {0xC7u, 0x00u, 0x00u};
static const uint8_t k_entry[] = {0x01u};
static const uint8_t k_border_normal[] = {0x05u};
static const uint8_t k_border_partial[] = {0x80u};
/* A cold/maintenance full update loads the actual-temperature Mode-1 waveform.
 * The post-full Mode-2 LUT must use actual temperature too. */
static const uint8_t k_full_update[] = {0xF7u};
static const uint8_t k_cf[] = {0xCFu};
static const uint8_t k_ff[] = {0xFFu};
static const uint8_t k_b9[] = {0xB9u};

static bool time_reached(uint32_t now, uint32_t deadline)
{
    return (int32_t)(now - deadline) >= 0;
}

static uint32_t now_ms(const comp_ssd1681_wba_t *driver)
{
    return driver->config.now_ms(driver->config.context);
}

static void fail(comp_ssd1681_wba_t *driver,
                 comp_ssd1681_wba_error_t error)
{
    /* Preserve the first failing transaction before the presenter's retries
     * replace its stage with WAIT_RESET_READY. Cached observation only. */
    if (driver->stats.first_failure_error == COMP_SSD1681_WBA_ERROR_NONE) {
        const uint32_t tick = now_ms(driver);
        driver->stats.first_failure_ms = tick;
        driver->stats.first_failure_wait_ms = tick - driver->wait_started_ms;
        driver->stats.first_failure_stage = driver->stage;
        driver->stats.first_failure_operation = driver->operation;
        driver->stats.first_failure_sequence = driver->sequence;
        driver->stats.first_failure_error = (uint8_t)error;
        driver->stats.first_failure_busy = driver->config.is_busy(driver->config.context);
    }
    driver->status = COMP_SSD1681_WBA_ERROR;
    driver->error = error;
    driver->baseline_valid = false;
    driver->operation = OP_NONE;
    driver->sequence = SEQ_NONE;
    if (error == COMP_SSD1681_WBA_ERROR_TRANSPORT) {
        driver->stats.transport_errors++;
    } else if (error == COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT) {
        driver->stats.busy_timeouts++;
    }
}

static bool send_bytes(comp_ssd1681_wba_t *driver,
                       bool data,
                       const uint8_t *bytes,
                       uint16_t size)
{
    driver->stats.transfer_calls++;
    driver->stats.transferred_bytes += size;
    if (!driver->config.transfer(driver->config.context, data, bytes, size)) {
        fail(driver, COMP_SSD1681_WBA_ERROR_TRANSPORT);
        return false;
    }
    return true;
}

static bool send_command(comp_ssd1681_wba_t *driver, uint8_t command)
{
    if (!send_bytes(driver, false, &command, 1u)) return false;
    driver->stats.last_command = command;
    driver->stats.last_command_ms = now_ms(driver);
    return true;
}

static void arm_busy_wait(comp_ssd1681_wba_t *driver, uint8_t stage)
{
    driver->stage = stage;
    driver->wait_started_ms = now_ms(driver);
    driver->deadline_ms = driver->wait_started_ms +
                          driver->config.busy_timeout_ms;
    /* 0x20 may assert BUSY before this foreground call returns. Preserve that
     * sample even if another service runs before the next panel poll. */
    driver->busy_observed = driver->config.is_busy(driver->config.context);
    driver->ready_candidate = false;
#if COMP_V11_PANEL_PASSIVE_TRACE
    if (stage == ST_WAIT_VISIBLE) {
        driver->stats.visible_activation_count++;
        driver->stats.visible_started_ms = driver->wait_started_ms;
        driver->stats.visible_first_high_ms = driver->busy_observed ?
            driver->wait_started_ms : UINT32_MAX;
        driver->stats.visible_last_high_ms = driver->stats.visible_first_high_ms;
        driver->stats.visible_high_samples = driver->busy_observed ? 1u : 0u;
        driver->stats.visible_poll_samples = 1u;
    }
#endif
}

static bool stable_ready(comp_ssd1681_wba_t *driver, uint32_t now, bool busy)
{
    if (busy) {
        if (driver->ready_candidate) driver->stats.ready_glitches++;
        driver->ready_candidate = false;
        return false;
    }
    if (!driver->ready_candidate) {
        driver->ready_candidate = true;
        driver->ready_started_ms = now;
    }
    return time_reached(now, driver->ready_started_ms + BUSY_READY_STABLE_MS);
}

static void set_sequence(comp_ssd1681_wba_t *driver, uint8_t sequence)
{
    driver->stage = ST_SEQUENCE;
    driver->sequence = sequence;
    driver->sequence_index = 0u;
    driver->sequence_data_pending = 0u;
}

static void complete_operation(comp_ssd1681_wba_t *driver);

static void prepare_window(comp_ssd1681_wba_t *driver)
{
    const uint16_t controller_y_start =
        (COMP_SSD1681_WBA_HEIGHT - 1u) - driver->window.y_start;
    const uint16_t controller_y_end =
        (COMP_SSD1681_WBA_HEIGHT - 1u) - driver->window.y_end;

    driver->ram_x[0] = driver->window.x_start_byte;
    driver->ram_x[1] = driver->window.x_end_byte;
    driver->ram_y[0] = (uint8_t)controller_y_start;
    driver->ram_y[1] = (uint8_t)(controller_y_start >> 8u);
    driver->ram_y[2] = (uint8_t)controller_y_end;
    driver->ram_y[3] = (uint8_t)(controller_y_end >> 8u);
    driver->x_counter[0] = driver->window.x_start_byte;
    driver->y_counter[0] = (uint8_t)controller_y_start;
    driver->y_counter[1] = (uint8_t)(controller_y_start >> 8u);
}

static bool byte_in_window(const comp_ssd1681_wba_window_t *window,
                           uint8_t x, uint16_t y)
{
    return x >= window->x_start_byte && x <= window->x_end_byte &&
           y >= window->y_start && y <= window->y_end;
}

static bool dirty_bounds(const comp_ssd1681_wba_t *driver,
                         comp_ssd1681_wba_window_t *bounds)
{
    bool found = false;

    for (uint16_t y = 0u; y < COMP_SSD1681_WBA_HEIGHT; ++y) {
        for (uint8_t x = 0u; x < COMP_SSD1681_WBA_BYTES_PER_ROW; ++x) {
            const size_t offset =
                (size_t)y * COMP_SSD1681_WBA_BYTES_PER_ROW + x;
            if (driver->previous_frame[offset] == driver->current_frame[offset]) {
                continue;
            }
            if (!found) {
                *bounds = (comp_ssd1681_wba_window_t){x, x, y, y};
                found = true;
            } else {
                if (x < bounds->x_start_byte) bounds->x_start_byte = x;
                if (x > bounds->x_end_byte) bounds->x_end_byte = x;
                if (y < bounds->y_start) bounds->y_start = y;
                if (y > bounds->y_end) bounds->y_end = y;
            }
        }
    }
    return found;
}

/* Preserve the ordinary partial-refresh coverage contract: use the existing
 * rectangular dirty bounds, split into at most four rectangles around the
 * recording safe window.  This avoids silently changing face/status updates
 * into a new exact-XOR policy. */
static bool next_ordinary_region(comp_ssd1681_wba_t *driver)
{
    comp_ssd1681_wba_window_t dirty = {0u, 0u, 0u, 0u};
    const comp_ssd1681_wba_window_t *recording = &driver->recording_window;

    if (!dirty_bounds(driver, &dirty)) return false;
    while (driver->recording_ordinary_region < 4u) {
        comp_ssd1681_wba_window_t candidate = {0u, 0u, 0u, 0u};
        bool valid = false;

        switch (driver->recording_ordinary_region++) {
        case 0u: /* above */
            if (dirty.y_start < recording->y_start) {
                candidate = dirty;
                candidate.y_end = dirty.y_end < recording->y_start
                    ? dirty.y_end : (uint16_t)(recording->y_start - 1u);
                valid = true;
            }
            break;
        case 1u: /* left, over the recording rows */
            if (dirty.x_start_byte < recording->x_start_byte &&
                dirty.y_start <= recording->y_end &&
                dirty.y_end >= recording->y_start) {
                candidate.x_start_byte = dirty.x_start_byte;
                candidate.x_end_byte = dirty.x_end_byte < recording->x_start_byte
                    ? dirty.x_end_byte
                    : (uint8_t)(recording->x_start_byte - 1u);
                candidate.y_start = dirty.y_start > recording->y_start
                    ? dirty.y_start : recording->y_start;
                candidate.y_end = dirty.y_end < recording->y_end
                    ? dirty.y_end : recording->y_end;
                valid = true;
            }
            break;
        case 2u: /* right, over the recording rows */
            if (dirty.x_end_byte > recording->x_end_byte &&
                dirty.y_start <= recording->y_end &&
                dirty.y_end >= recording->y_start) {
                candidate.x_start_byte = dirty.x_start_byte > recording->x_end_byte
                    ? dirty.x_start_byte
                    : (uint8_t)(recording->x_end_byte + 1u);
                candidate.x_end_byte = dirty.x_end_byte;
                candidate.y_start = dirty.y_start > recording->y_start
                    ? dirty.y_start : recording->y_start;
                candidate.y_end = dirty.y_end < recording->y_end
                    ? dirty.y_end : recording->y_end;
                valid = true;
            }
            break;
        default: /* below */
            if (dirty.y_end > recording->y_end) {
                candidate = dirty;
                candidate.y_start = dirty.y_start > recording->y_end
                    ? dirty.y_start : (uint16_t)(recording->y_end + 1u);
                valid = true;
            }
            break;
        }
        if (valid) {
            driver->window = candidate;
            prepare_window(driver);
            return true;
        }
    }
    return false;
}

/* Find one contiguous changed byte run.  One row per run keeps the transfer
 * exact: unchanged microphone bytes are never swept into a rectangular
 * bounding box just because a nearby waveform byte changed. */
static bool next_recording_run(comp_ssd1681_wba_t *driver)
{
    const bool inside = true;
    uint16_t offset = driver->scan_offset;

    while (offset < COMP_SSD1681_WBA_FRAME_BYTES) {
        const uint16_t y =
            (uint16_t)(offset / COMP_SSD1681_WBA_BYTES_PER_ROW);
        const uint8_t x =
            (uint8_t)(offset % COMP_SSD1681_WBA_BYTES_PER_ROW);
        const bool eligible =
            byte_in_window(&driver->recording_window, x, y) == inside;

        if (eligible && driver->previous_frame[offset] !=
                            driver->current_frame[offset]) {
            uint8_t end = x;
            while (end + 1u < COMP_SSD1681_WBA_BYTES_PER_ROW) {
                const uint8_t candidate = (uint8_t)(end + 1u);
                const uint16_t candidate_offset =
                    (uint16_t)(offset + (candidate - x));
                if (byte_in_window(&driver->recording_window, candidate, y) !=
                        inside ||
                    driver->previous_frame[candidate_offset] ==
                        driver->current_frame[candidate_offset]) {
                    break;
                }
                end = candidate;
            }
            driver->window = (comp_ssd1681_wba_window_t){x, end, y, y};
            driver->scan_offset = (uint16_t)(offset + (end - x) + 1u);
            prepare_window(driver);
            return true;
        }
        offset++;
    }
    driver->scan_offset = offset;
    return false;
}

static void start_next_recording_run(comp_ssd1681_wba_t *driver)
{
    while (!(driver->recording_phase == RECORDING_PHASE_ORDINARY
                 ? next_ordinary_region(driver)
                 : next_recording_run(driver))) {
        if (driver->recording_phase == RECORDING_PHASE_ORDINARY) {
            driver->recording_phase = RECORDING_PHASE_OLD;
        } else if (driver->recording_phase == RECORDING_PHASE_OLD) {
            driver->recording_phase = RECORDING_PHASE_CURRENT;
        } else if (driver->recording_phase == RECORDING_PHASE_CURRENT) {
            set_sequence(driver, SEQ_PARTIAL_ACTIVATE);
            return;
        } else {
            complete_operation(driver);
            return;
        }
        driver->scan_offset = 0u;
    }
    set_sequence(driver, SEQ_RECORDING_WINDOW);
}

static uint8_t sequence_count(uint8_t sequence)
{
    switch (sequence) {
    case SEQ_MODE1_TEMP:
        return 3u;
    case SEQ_FULL_OLD_WINDOW:
    case SEQ_FULL_CURRENT_WINDOW:
    case SEQ_FULL_REBASE_WINDOW:
        return 8u;
    case SEQ_PARTIAL_WINDOW:
    case SEQ_RECORDING_WINDOW:
        return 5u;
    case SEQ_FULL_ACTIVATE:
    case SEQ_PARTIAL_ACTIVATE:
        return 2u;
    case SEQ_REARM_MODE2:
        return 3u;
    default:
        return 0u;
    }
}

static sequence_item_t sequence_item(const comp_ssd1681_wba_t *driver,
                                     uint8_t sequence,
                                     uint8_t index)
{
    sequence_item_t item = {0u, NULL, 0u};

    switch (sequence) {
    case SEQ_MODE1_TEMP: {
        static const sequence_item_t items[] = {
            {0x18u, k_80, sizeof(k_80)},
            {0x22u, k_b1, sizeof(k_b1)},
            {0x20u, NULL, 0u},
        };
        return items[index];
    }
    case SEQ_FULL_OLD_WINDOW:
    case SEQ_FULL_CURRENT_WINDOW:
    case SEQ_FULL_REBASE_WINDOW:
        switch (index) {
        case 0u: item = (sequence_item_t){0x01u, k_driver, sizeof(k_driver)}; break;
        case 1u: item = (sequence_item_t){0x11u, k_entry, sizeof(k_entry)}; break;
        case 2u: item = (sequence_item_t){0x44u, driver->ram_x, sizeof(driver->ram_x)}; break;
        case 3u: item = (sequence_item_t){0x45u, driver->ram_y, sizeof(driver->ram_y)}; break;
        case 4u: item = (sequence_item_t){0x3Cu, k_border_normal, sizeof(k_border_normal)}; break;
        case 5u: item = (sequence_item_t){0x18u, k_80, sizeof(k_80)}; break;
        case 6u: item = (sequence_item_t){0x4Eu, driver->x_counter, sizeof(driver->x_counter)}; break;
        default: item = (sequence_item_t){0x4Fu, driver->y_counter, sizeof(driver->y_counter)}; break;
        }
        return item;
    case SEQ_PARTIAL_WINDOW:
    case SEQ_RECORDING_WINDOW:
        switch (index) {
        case 0u: item = (sequence_item_t){0x3Cu, k_border_partial, sizeof(k_border_partial)}; break;
        case 1u: item = (sequence_item_t){0x44u, driver->ram_x, sizeof(driver->ram_x)}; break;
        case 2u: item = (sequence_item_t){0x45u, driver->ram_y, sizeof(driver->ram_y)}; break;
        case 3u: item = (sequence_item_t){0x4Eu, driver->x_counter, sizeof(driver->x_counter)}; break;
        default: item = (sequence_item_t){0x4Fu, driver->y_counter, sizeof(driver->y_counter)}; break;
        }
        return item;
    case SEQ_FULL_ACTIVATE:
        return index == 0u ? (sequence_item_t){0x22u, k_full_update, sizeof(k_full_update)}
                           : (sequence_item_t){0x20u, NULL, 0u};
    case SEQ_PARTIAL_ACTIVATE:
        /* Restore the accepted family-boundary FF profile: read actual panel
         * temperature and load Mode 2 before this full-window activation.
         * Ordinary life then stays CF on that cached profile. */
        return index == 0u ? (sequence_item_t){0x22u,
                                driver->operation == OP_FAST ? k_ff : k_cf, 1u}
                           : (sequence_item_t){0x20u, NULL, 0u};
    case SEQ_REARM_MODE2: {
        /* SSD1681 0xB9 reads temperature and loads Mode 2 without displaying.
         * Do not force a 100C LUT between the full frame and the first FF. */
        static const sequence_item_t items[] = {
            {0x18u, k_80, sizeof(k_80)},
            {0x22u, k_b9, sizeof(k_b9)},
            {0x20u, NULL, 0u},
        };
        return items[index];
    }
    default:
        return item;
    }
}

static void start_data(comp_ssd1681_wba_t *driver)
{
    driver->stage = ST_DATA;
    driver->data_command_sent = 0u;
    driver->data_y = driver->window.y_start;
    driver->data_x = driver->window.x_start_byte;
}

static void complete_operation(comp_ssd1681_wba_t *driver)
{
    driver->stats.last_completed_ms = now_ms(driver);
    if ((driver->operation == OP_PARTIAL || driver->operation == OP_FAST) &&
        (driver->recording_phase == RECORDING_PHASE_POST_CURRENT ||
         driver->recording_phase == RECORDING_PHASE_POST_PREVIOUS)) {
        driver->stats.completed_paired++;
        if (driver->recording_phase == RECORDING_PHASE_POST_PREVIOUS)
            driver->stats.completed_blink_rebases++;
    }
    if (driver->operation == OP_FULL) {
        driver->baseline_valid = true;
        driver->maintenance_required = false;
        driver->stats.partial_count = 0u;
        driver->stats.completed_full++;
        driver->stats.last_full_ms = driver->stats.last_completed_ms;
        driver->stats.mode2_since_full = 0u;
    } else if (driver->operation==OP_FAST) {
        driver->stats.partial_count=0u;
        driver->maintenance_required=false;
        driver->stats.completed_fast++;
        driver->stats.mode2_since_full++;
    } else {
        if (driver->stats.partial_count < UINT8_MAX) {
            driver->stats.partial_count++;
        }
        driver->maintenance_required =
            driver->config.partial_limit != UINT8_MAX &&
            driver->stats.partial_count >= driver->config.partial_limit;
        driver->stats.completed_partial++;
        driver->stats.mode2_since_full++;
        if (driver->operation == OP_RECORDING) {
            driver->stats.completed_recording++;
        }
    }
    driver->operation = OP_NONE;
    driver->sequence = SEQ_NONE;
    driver->status = COMP_SSD1681_WBA_COMPLETE;
    driver->error = COMP_SSD1681_WBA_ERROR_NONE;
}

static void sequence_complete(comp_ssd1681_wba_t *driver)
{
    switch (driver->sequence) {
    case SEQ_MODE1_TEMP:
        arm_busy_wait(driver, ST_WAIT_MODE1_TEMP);
        break;
    case SEQ_FULL_OLD_WINDOW:
    case SEQ_FULL_CURRENT_WINDOW:
    case SEQ_FULL_REBASE_WINDOW:
    case SEQ_PARTIAL_WINDOW:
    case SEQ_RECORDING_WINDOW:
        start_data(driver);
        break;
    case SEQ_FULL_ACTIVATE:
    case SEQ_PARTIAL_ACTIVATE:
        arm_busy_wait(driver, ST_WAIT_VISIBLE);
        break;
    case SEQ_REARM_MODE2:
        arm_busy_wait(driver, ST_WAIT_REARM);
        break;
    default:
        fail(driver, COMP_SSD1681_WBA_ERROR_CONFIGURATION);
        break;
    }
}

static void poll_sequence(comp_ssd1681_wba_t *driver)
{
    const uint8_t count = sequence_count(driver->sequence);
    sequence_item_t item;

    if (driver->sequence_index >= count) {
        sequence_complete(driver);
        return;
    }
    item = sequence_item(driver, driver->sequence, driver->sequence_index);
    /* These register payloads are at most four bytes. Finish the command and
     * its parameters together, before foreground IMU service can use SPI1.
     * Large frame rows remain separate bounded transfers for audio service. */
    if (!send_command(driver, item.command)) return;
    if (item.size != 0u && !send_bytes(driver, true, item.data, item.size)) return;
    driver->sequence_index++;
    if (driver->sequence_index >= count) {
        sequence_complete(driver);
    }
}

static void data_complete(comp_ssd1681_wba_t *driver)
{
    if (driver->operation == OP_RECORDING) {
        start_next_recording_run(driver);
    } else if (driver->operation == OP_PARTIAL || driver->operation == OP_FAST) {
        if (driver->recording_phase == RECORDING_PHASE_OLD) {
            driver->recording_phase = RECORDING_PHASE_CURRENT;
            set_sequence(driver, SEQ_PARTIAL_WINDOW);
        } else if (driver->recording_phase == RECORDING_PHASE_POST_CURRENT) {
            if (driver->normalize_previous) {
                driver->recording_phase = RECORDING_PHASE_POST_PREVIOUS;
                set_sequence(driver, SEQ_PARTIAL_WINDOW);
            } else complete_operation(driver);
        } else if (driver->recording_phase == RECORDING_PHASE_POST_PREVIOUS) {
            complete_operation(driver);
        } else {
            set_sequence(driver, SEQ_PARTIAL_ACTIVATE);
        }
    } else if (driver->sequence == SEQ_FULL_OLD_WINDOW) {
        set_sequence(driver, SEQ_FULL_CURRENT_WINDOW);
    } else if (driver->sequence == SEQ_FULL_CURRENT_WINDOW) {
        set_sequence(driver, SEQ_FULL_ACTIVATE);
    } else if (driver->sequence == SEQ_FULL_REBASE_WINDOW) {
#if COMP_V11_PANEL_FULL_REFRESH_ONLY
        /* Recovery stays in Mode 1 after the visible refresh and RAM rebase.
         * Do not make a completed full image depend on loading Mode 2. */
        complete_operation(driver);
#else
        set_sequence(driver, SEQ_REARM_MODE2);
#endif
    } else {
        fail(driver, COMP_SSD1681_WBA_ERROR_CONFIGURATION);
    }
}

static void poll_data(comp_ssd1681_wba_t *driver)
{
    const uint8_t command =
        driver->operation == OP_RECORDING
            ? (driver->recording_phase == RECORDING_PHASE_OLD ? 0x26u : 0x24u) :
        (driver->operation == OP_PARTIAL || driver->operation == OP_FAST) ?
            (driver->recording_phase == RECORDING_PHASE_OLD ||
             driver->recording_phase == RECORDING_PHASE_POST_PREVIOUS ? 0x26u : 0x24u) :
        driver->sequence == SEQ_FULL_OLD_WINDOW ? 0x26u :
        driver->sequence == SEQ_FULL_CURRENT_WINDOW ? 0x24u : 0x26u;
    const uint8_t *frame =
        (driver->sequence == SEQ_FULL_OLD_WINDOW ||
         ((driver->operation == OP_RECORDING || driver->operation == OP_PARTIAL ||
           driver->operation == OP_FAST) &&
          driver->recording_phase == RECORDING_PHASE_OLD))
            ? driver->previous_frame
            : driver->current_frame;
    uint16_t remaining;
    uint16_t size;
    size_t offset;

    if (driver->data_command_sent == 0u) {
        if (send_command(driver, command)) {
            driver->data_command_sent = 1u;
        }
        return;
    }
    if (driver->data_y > driver->window.y_end) {
        data_complete(driver);
        return;
    }
    remaining = (uint16_t)(driver->window.x_end_byte - driver->data_x + 1u);
    size = remaining < driver->config.payload_chunk_bytes
               ? remaining
               : driver->config.payload_chunk_bytes;
    offset = (size_t)driver->data_y * COMP_SSD1681_WBA_BYTES_PER_ROW +
             driver->data_x;
    if (!send_bytes(driver, true, &frame[offset], size)) {
        return;
    }
    driver->data_x = (uint8_t)(driver->data_x + size);
    if (driver->data_x > driver->window.x_end_byte) {
        driver->data_y++;
        driver->data_x = driver->window.x_start_byte;
    }
    if (driver->data_y > driver->window.y_end) {
        data_complete(driver);
    }
}

static bool window_valid(const comp_ssd1681_wba_window_t *window)
{
    return window != NULL &&
           window->x_start_byte <= window->x_end_byte &&
           window->x_end_byte < COMP_SSD1681_WBA_BYTES_PER_ROW &&
           window->y_start <= window->y_end &&
           window->y_end < COMP_SSD1681_WBA_HEIGHT;
}

bool comp_ssd1681_wba_init(comp_ssd1681_wba_t *driver,
                           const comp_ssd1681_wba_config_t *config)
{
    if (driver == NULL) {
        return false;
    }
    memset(driver, 0, sizeof(*driver));
    driver->status = COMP_SSD1681_WBA_NOT_READY;
    driver->error = COMP_SSD1681_WBA_ERROR_CONFIGURATION;
    if (config == NULL || config->transfer == NULL ||
        config->is_busy == NULL ||
        config->now_ms == NULL) {
        return false;
    }
    if ((config->reset_mode == COMP_SSD1681_WBA_RESET_HARDWARE &&
         config->set_reset == NULL) ||
        (config->reset_mode == COMP_SSD1681_WBA_RESET_SOFTWARE_ONLY &&
         config->set_reset != NULL) ||
        (config->reset_mode != COMP_SSD1681_WBA_RESET_HARDWARE &&
         config->reset_mode != COMP_SSD1681_WBA_RESET_SOFTWARE_ONLY)) {
        return false;
    }
    driver->config = *config;
    if (driver->config.payload_chunk_bytes == 0u) {
        driver->config.payload_chunk_bytes = DEFAULT_CHUNK_BYTES;
    } else if (driver->config.payload_chunk_bytes > MAX_CHUNK_BYTES) {
        driver->config.payload_chunk_bytes = MAX_CHUNK_BYTES;
    }
    if (driver->config.busy_timeout_ms == 0u) {
        driver->config.busy_timeout_ms = DEFAULT_BUSY_TIMEOUT_MS;
    }
    if (driver->config.partial_limit == 0u) {
        driver->config.partial_limit =
            COMP_SSD1681_WBA_DEFAULT_PARTIAL_LIMIT;
    }
    driver->status = COMP_SSD1681_WBA_IDLE;
    driver->error = COMP_SSD1681_WBA_ERROR_NONE;
    return true;
}

bool comp_ssd1681_wba_start_full(comp_ssd1681_wba_t *driver,
                                 const uint8_t *previous_frame,
                                 const uint8_t *current_frame,
                                 size_t frame_bytes)
{
    if (driver == NULL || driver->status == COMP_SSD1681_WBA_NOT_READY ||
        driver->status == COMP_SSD1681_WBA_ACTIVE) {
        return false;
    }
    if (previous_frame == NULL || current_frame == NULL ||
        frame_bytes != COMP_SSD1681_WBA_FRAME_BYTES) {
        driver->error = COMP_SSD1681_WBA_ERROR_ARGUMENT;
        return false;
    }
    driver->previous_frame = previous_frame;
    driver->current_frame = current_frame;
    driver->window = (comp_ssd1681_wba_window_t){
        0u, COMP_SSD1681_WBA_BYTES_PER_ROW - 1u,
        0u, COMP_SSD1681_WBA_HEIGHT - 1u};
    prepare_window(driver);
    driver->operation = OP_FULL;
    if (driver->config.reset_mode == COMP_SSD1681_WBA_RESET_SOFTWARE_ONLY) {
        /* Supply settling and BUSY readiness precede 0x12. No imaginary
         * hardware reset/power cycle is performed in this mode. */
        driver->deadline_ms = now_ms(driver) + RESET_RELEASE_MS;
        driver->stage = ST_RESET_RELEASE_WAIT;
    } else {
        driver->stage = ST_RESET_ASSERT;
    }
    /* A replacement baseline is not valid until its visible activation,
     * RAM synchronization, and Mode-2 rearm have all completed. */
    driver->baseline_valid = false;
    driver->maintenance_required = false;
    driver->stats.partial_count = 0u;
    driver->status = COMP_SSD1681_WBA_ACTIVE;
    driver->error = COMP_SSD1681_WBA_ERROR_NONE;
    return true;
}

static bool start_mode2(
    comp_ssd1681_wba_t *driver,
    const uint8_t *previous_frame,
    const uint8_t *current_frame,
    size_t frame_bytes,
    const comp_ssd1681_wba_window_t *window, bool fast)
{
    if (driver == NULL || driver->status == COMP_SSD1681_WBA_NOT_READY ||
        driver->status == COMP_SSD1681_WBA_ACTIVE) {
        return false;
    }
    if (!driver->baseline_valid) {
        driver->error = COMP_SSD1681_WBA_ERROR_BASELINE_REQUIRED;
        return false;
    }
    if (driver->maintenance_required && !fast) {
        driver->error = COMP_SSD1681_WBA_ERROR_MAINTENANCE_REQUIRED;
        return false;
    }
    if (current_frame == NULL ||
        frame_bytes != COMP_SSD1681_WBA_FRAME_BYTES ||
        !window_valid(window)) {
        driver->error = COMP_SSD1681_WBA_ERROR_ARGUMENT;
        return false;
    }
    driver->current_frame = current_frame;
    driver->previous_frame = previous_frame;
    driver->normalize_previous = false;
    driver->recording_phase = previous_frame == NULL ? RECORDING_PHASE_ORDINARY :
                                                     RECORDING_PHASE_OLD;
    driver->window = *window;
    prepare_window(driver);
    driver->operation = fast?OP_FAST:OP_PARTIAL;
    arm_busy_wait(driver, ST_WAIT_RESET_READY);
    driver->status = COMP_SSD1681_WBA_ACTIVE;
    driver->error = COMP_SSD1681_WBA_ERROR_NONE;
    return true;
}
bool comp_ssd1681_wba_start_partial(comp_ssd1681_wba_t *driver,
    const uint8_t *frame,size_t bytes,const comp_ssd1681_wba_window_t *window)
{ return start_mode2(driver,NULL,frame,bytes,window,false); }
bool comp_ssd1681_wba_start_partial_pair(comp_ssd1681_wba_t *driver,
    const uint8_t *previous, const uint8_t *current, size_t bytes,
    const comp_ssd1681_wba_window_t *window)
{
    if (previous == NULL) {
        if (driver != NULL) driver->error = COMP_SSD1681_WBA_ERROR_ARGUMENT;
        return false;
    }
    return start_mode2(driver,previous,current,bytes,window,false);
}
bool comp_ssd1681_wba_start_blink_open(comp_ssd1681_wba_t *driver,
    const uint8_t *previous, const uint8_t *current, size_t bytes,
    const comp_ssd1681_wba_window_t *window)
{
    if (!comp_ssd1681_wba_start_partial_pair(driver,previous,current,bytes,window))
        return false;
    driver->normalize_previous = true;
    return true;
}
bool comp_ssd1681_wba_start_fast(comp_ssd1681_wba_t *driver,const uint8_t *frame,size_t bytes)
{
    const comp_ssd1681_wba_window_t window={0,24,0,199};
    return start_mode2(driver,NULL,frame,bytes,&window,true);
}
bool comp_ssd1681_wba_start_fast_pair(comp_ssd1681_wba_t *driver,
    const uint8_t *previous, const uint8_t *current, size_t bytes)
{
    const comp_ssd1681_wba_window_t window = {0,24,0,199};
    if (previous == NULL) {
        if (driver != NULL) driver->error = COMP_SSD1681_WBA_ERROR_ARGUMENT;
        return false;
    }
    return start_mode2(driver,previous,current,bytes,&window,true);
}

bool comp_ssd1681_wba_start_recording_partial(
    comp_ssd1681_wba_t *driver,
    const uint8_t *previous_frame,
    const uint8_t *current_frame,
    size_t frame_bytes,
    const comp_ssd1681_wba_window_t *recording_window)
{
    bool changed = false;

    if (driver == NULL || driver->status == COMP_SSD1681_WBA_NOT_READY ||
        driver->status == COMP_SSD1681_WBA_ACTIVE) {
        return false;
    }
    if (!driver->baseline_valid) {
        driver->error = COMP_SSD1681_WBA_ERROR_BASELINE_REQUIRED;
        return false;
    }
    if (driver->maintenance_required) {
        driver->error = COMP_SSD1681_WBA_ERROR_MAINTENANCE_REQUIRED;
        return false;
    }
    if (previous_frame == NULL || current_frame == NULL ||
        frame_bytes != COMP_SSD1681_WBA_FRAME_BYTES ||
        !window_valid(recording_window)) {
        driver->error = COMP_SSD1681_WBA_ERROR_ARGUMENT;
        return false;
    }
    for (size_t index = 0u; index < frame_bytes; ++index) {
        if (previous_frame[index] != current_frame[index]) {
            changed = true;
            break;
        }
    }
    if (!changed) {
        driver->error = COMP_SSD1681_WBA_ERROR_ARGUMENT;
        return false;
    }

    driver->previous_frame = previous_frame;
    driver->current_frame = current_frame;
    driver->recording_window = *recording_window;
    driver->normalize_previous = false;
    driver->recording_phase = RECORDING_PHASE_ORDINARY;
    driver->recording_ordinary_region = 0u;
    driver->scan_offset = 0u;
    driver->operation = OP_RECORDING;
    arm_busy_wait(driver, ST_WAIT_RESET_READY);
    driver->status = COMP_SSD1681_WBA_ACTIVE;
    driver->error = COMP_SSD1681_WBA_ERROR_NONE;
    return true;
}

comp_ssd1681_wba_status_t comp_ssd1681_wba_poll(
    comp_ssd1681_wba_t *driver)
{
    uint32_t now;
    bool busy;

    if (driver == NULL) return COMP_SSD1681_WBA_NOT_READY;
    if (driver->status == COMP_SSD1681_WBA_NOT_READY) return driver->status;
    now = now_ms(driver);
    busy = driver->config.is_busy(driver->config.context);
    if (driver->busy_sampled && busy != driver->busy_level) {
        driver->stats.last_busy_change_ms = now;
        if (busy && (driver->status == COMP_SSD1681_WBA_IDLE ||
                     driver->status == COMP_SSD1681_WBA_COMPLETE)) {
            driver->stats.idle_busy_edges++;
        }
    }
    driver->busy_sampled = true;
    driver->busy_level = busy;
    if (driver->status != COMP_SSD1681_WBA_ACTIVE) return driver->status;
    switch (driver->stage) {
    case ST_RESET_ASSERT:
        if (!driver->config.set_reset(driver->config.context, true)) {
            fail(driver, COMP_SSD1681_WBA_ERROR_TRANSPORT);
        } else {
            driver->deadline_ms = now + RESET_HOLD_MS;
            driver->stage = ST_RESET_ASSERT_WAIT;
        }
        break;
    case ST_RESET_ASSERT_WAIT:
        if (time_reached(now, driver->deadline_ms)) {
            driver->stage = ST_RESET_RELEASE;
        }
        break;
    case ST_RESET_RELEASE:
        if (!driver->config.set_reset(driver->config.context, false)) {
            fail(driver, COMP_SSD1681_WBA_ERROR_TRANSPORT);
        } else {
            driver->deadline_ms = now + RESET_RELEASE_MS;
            driver->stage = ST_RESET_RELEASE_WAIT;
        }
        break;
    case ST_RESET_RELEASE_WAIT:
        if (time_reached(now, driver->deadline_ms)) {
            arm_busy_wait(driver, ST_WAIT_RESET_READY);
        }
        break;
    case ST_WAIT_RESET_READY:
        if (stable_ready(driver, now, busy)) {
            if (driver->operation == OP_FULL) {
                driver->stage = ST_SOFTWARE_RESET;
            } else if (driver->operation == OP_RECORDING) {
                start_next_recording_run(driver);
            } else {
                set_sequence(driver, SEQ_PARTIAL_WINDOW);
            }
        } else if (time_reached(now, driver->deadline_ms)) {
            fail(driver, COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT);
        }
        break;
    case ST_SOFTWARE_RESET:
        if (send_command(driver, 0x12u)) {
            arm_busy_wait(driver, ST_WAIT_SOFTWARE_RESET);
        }
        break;
    case ST_WAIT_SOFTWARE_RESET:
        /* SSD1681 section 8.1 requires 10ms after 0x12, even when its short
         * BUSY pulse has already ended before the next foreground poll. */
        if (time_reached(now, driver->wait_started_ms + SOFTWARE_RESET_SETTLE_MS) &&
            stable_ready(driver, now, busy)) {
            set_sequence(driver, SEQ_MODE1_TEMP);
        } else if (time_reached(now, driver->deadline_ms)) {
            fail(driver, COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT);
        }
        break;
    case ST_SEQUENCE:
        poll_sequence(driver);
        break;
    case ST_WAIT_MODE1_TEMP:
        if (time_reached(now, driver->wait_started_ms + MODE1_PROFILE_SETTLE_MS) &&
            stable_ready(driver, now, busy)) {
            /* B1 has loaded the actual-temperature Mode-1 LUT. The manual
             * fast profile belongs to the post-full Mode-2 rearm. */
            set_sequence(driver, SEQ_FULL_OLD_WINDOW);
        } else if (time_reached(now, driver->deadline_ms)) {
            fail(driver, COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT);
        }
        break;
    case ST_DATA:
        poll_data(driver);
        break;
    case ST_WAIT_VISIBLE:
#if COMP_V11_PANEL_PASSIVE_TRACE
        driver->stats.visible_poll_samples++;
        if (busy) {
            if (driver->stats.visible_high_samples == 0u)
                driver->stats.visible_first_high_ms = now;
            driver->stats.visible_last_high_ms = now;
            driver->stats.visible_high_samples++;
        }
#endif
        if (busy) {
            if (!driver->busy_observed) {
                const uint32_t start_wait = now - driver->wait_started_ms;
                if (start_wait > driver->stats.max_start_wait_ms)
                    driver->stats.max_start_wait_ms = start_wait;
                if (start_wait >= REFRESH_START_TIMEOUT_MS)
                    driver->stats.delayed_starts++;
            }
            (void)stable_ready(driver, now, true);
            driver->busy_observed = true;
            /* BUSY asserted proves that the visible activation started, but
             * it does not waive the transaction deadline. A stuck panel must
             * release the presenter so independent visual tracks can
             * fail/retry instead of remaining blocked forever. */
            if (time_reached(now, driver->deadline_ms)) {
                fail(driver, COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT);
            }
        } else if (driver->busy_observed) {
            if (!stable_ready(driver, now, false)) {
                if (time_reached(now, driver->deadline_ms))
                    fail(driver, COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT);
            } else if (driver->operation == OP_FULL) {
                driver->stats.last_visible_wait_ms = now - driver->wait_started_ms;
                set_sequence(driver, SEQ_FULL_REBASE_WINDOW);
            } else if (driver->operation == OP_RECORDING) {
                driver->stats.last_visible_wait_ms = now - driver->wait_started_ms;
                driver->recording_phase = RECORDING_PHASE_POST_CURRENT;
                driver->scan_offset = 0u;
                start_next_recording_run(driver);
            } else if (driver->recording_phase == RECORDING_PHASE_CURRENT) {
                driver->stats.last_visible_wait_ms = now - driver->wait_started_ms;
                driver->recording_phase = RECORDING_PHASE_POST_CURRENT;
                set_sequence(driver, SEQ_PARTIAL_WINDOW);
            } else {
                driver->stats.last_visible_wait_ms = now - driver->wait_started_ms;
                complete_operation(driver);
            }
        } else if (time_reached(
                       now,
                       driver->wait_started_ms + REFRESH_START_TIMEOUT_MS)) {
            /* Match the accepted WB55 refresh waiter: a visible 0x20 must
             * produce a BUSY assertion followed by ready. An idle level in
             * the same tick as the command is not completion. */
            fail(driver, COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT);
        } else if (time_reached(now, driver->deadline_ms)) {
            fail(driver, COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT);
        }
        break;
    case ST_WAIT_REARM:
        if (time_reached(now, driver->wait_started_ms + MODE2_REARM_SETTLE_MS) &&
            stable_ready(driver, now, busy)) {
            complete_operation(driver);
        } else if (time_reached(now, driver->deadline_ms)) {
            fail(driver, COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT);
        }
        break;
    default:
        fail(driver, COMP_SSD1681_WBA_ERROR_CONFIGURATION);
        break;
    }
    return driver->status;
}

void comp_ssd1681_wba_cancel(comp_ssd1681_wba_t *driver)
{
    if (driver == NULL || driver->status != COMP_SSD1681_WBA_ACTIVE) {
        return;
    }
    if (driver->config.set_reset != NULL) {
        (void)driver->config.set_reset(driver->config.context, false);
    }
    driver->baseline_valid = false;
    driver->maintenance_required = false;
    driver->operation = OP_NONE;
    driver->sequence = SEQ_NONE;
    driver->status = COMP_SSD1681_WBA_ERROR;
    driver->error = COMP_SSD1681_WBA_ERROR_CANCELLED;
    driver->stats.cancellations++;
}

comp_ssd1681_wba_status_t comp_ssd1681_wba_status(
    const comp_ssd1681_wba_t *driver)
{
    return driver == NULL ? COMP_SSD1681_WBA_NOT_READY : driver->status;
}

comp_ssd1681_wba_error_t comp_ssd1681_wba_error(
    const comp_ssd1681_wba_t *driver)
{
    return driver == NULL ? COMP_SSD1681_WBA_ERROR_CONFIGURATION : driver->error;
}

bool comp_ssd1681_wba_baseline_valid(const comp_ssd1681_wba_t *driver)
{
    return driver != NULL && driver->baseline_valid;
}

bool comp_ssd1681_wba_maintenance_required(
    const comp_ssd1681_wba_t *driver)
{
    return driver != NULL && driver->maintenance_required;
}

void comp_ssd1681_wba_get_stats(const comp_ssd1681_wba_t *driver,
                                 comp_ssd1681_wba_stats_t *stats)
{
    if (stats != NULL) {
        if (driver == NULL) {
            memset(stats, 0, sizeof(*stats));
        } else {
            *stats = driver->stats;
        }
    }
}
