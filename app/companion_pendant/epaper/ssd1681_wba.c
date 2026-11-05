/* SSD1681 product transaction cadence restored from FW54/74 and observed
 * on the current board in FW114. Keep command/data CS packets separate,
 * one register per foreground poll, and capture RAM packets within one row.
 * Idle full-width RAM can stream across row wraps within its configured
 * packet budget; narrower windows retain row-sized packets.
 * No C0 preactivation or active readback; visible BUSY assertion and stable
 * ready remain mandatory. Legacy optional batching/register/probe callbacks
 * are retained in the configuration layout but are not used here. An optional
 * platform policy permits one cooperative software-reset/Mode2 recovery
 * after an unobserved start, inside the original total deadline and gate.
 * Recording recovery uses the same bounded paired-frame rebuild; its normal
 * sparse-run scan is bypassed only until that one transaction completes.
 */
#include "ssd1681_wba.h"

#if COMP_V11_PANEL_STAGED_MODE2_POWER || COMP_V11_PANEL_SENSE_POWER ||     COMP_V11_PANEL_STUCK_BUSY_AUDIT || COMP_V11_PANEL_START_RETRY ||     COMP_V11_PANEL_WINDOW_REPAIR || COMP_V11_PANEL_STATUS_GATE ||     COMP_V11_PANEL_STARTUP_READBACK
#error "Production SSD1681 uses the restored write-only cadence; disable legacy diagnostic profiles."
#endif

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
#if COMP_V11_PANEL_VENDOR_QUICK_FULL
    OP_VENDOR_QUICK_FULL,
#endif
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
    ST_RECOVER_MODE2_RESET,
#if COMP_V11_PANEL_VENDOR_QUICK_FULL
    ST_VENDOR_LUT,
#endif
    ST_RECORDING_BOUNDS,
    ST_RECORDING_SCAN,
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
    SEQ_RECOVER_MODE2_SETUP,
    SEQ_RECORDING_ACTIVATE_WINDOW,
    SEQ_PARTIAL_CURSOR,
    SEQ_FULL_REBASE_CURRENT_WINDOW,
#if COMP_V11_PANEL_VENDOR_QUICK_FULL
    SEQ_VENDOR_FULL_SETUP,
    SEQ_VENDOR_CURSOR,
#endif
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

#if COMP_V11_PANEL_VENDOR_QUICK_FULL
/* Verbatim active LUT_DATA from the supplied EPAPER.c, file SHA256
 * 7EE1F8D5184B7883D1CADF745B724A6C12915E74F82641E4CB31764B07CD9896.
 * LUT SHA256 F83EA7360CFFF04FE9D004A75858A46213CBD710AAA2F0C4A62597E3EA176D15.
 * Bytes0..152 go to R32;153..158 bind R3F/R03/R04/R2C. The commented
 * alternative is intentionally absent. No guessed voltage/timing changes. */
static const uint8_t k_vendor_quick_lut[159] = {
    0xAAu,0x80u,0x55u,0x40u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,
    0x54u,0x10u,0xA8u,0x20u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,
    0xAAu,0x80u,0x55u,0x40u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,
    0x54u,0x10u,0xA8u,0x20u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,
    0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,
    0x05u,0x05u,0x00u,0x05u,0x05u,0x00u,0x00u,0x03u,0x02u,0x00u,0x00u,0x00u,
    0x00u,0x00u,0x05u,0x05u,0x00u,0x05u,0x05u,0x00u,0x00u,0x03u,0x02u,0x00u,
    0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,
    0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,
    0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,
    0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,
    0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,
    0x22u,0x22u,0x22u,0x22u,0x22u,0x22u,0x00u,0x00u,0x00u,0x22u,0x17u,0x41u,
    0xA8u,0x32u,0x58u,
};
static const uint8_t k_c7[] = {0xC7u};
#endif

static bool mode1_operation(const comp_ssd1681_wba_t *driver)
{
    return driver->operation == OP_FULL
#if COMP_V11_PANEL_VENDOR_QUICK_FULL
        || driver->operation == OP_VENDOR_QUICK_FULL
#endif
        ;
}

static bool time_reached(uint32_t now, uint32_t deadline)
{
    return (int32_t)(now - deadline) >= 0;
}

static uint32_t now_ms(const comp_ssd1681_wba_t *driver)
{
    return driver->config.now_ms(driver->config.context);
}

static uint8_t stop_busy_edges(comp_ssd1681_wba_t *driver)
{
#if COMP_V11_PANEL_PASSIVE_TRACE
    if (driver->config.take_busy_edges) {
        const uint8_t edges = driver->config.take_busy_edges(
            driver->config.context, COMP_SSD1681_WBA_BUSY_EDGES_STOP);
        if (driver->stage == ST_WAIT_VISIBLE || driver->stage == ST_RECOVER_MODE2_RESET)
            driver->stats.visible_edge_flags |= edges;
        return edges;
    }
#else
    (void)driver;
#endif
    return 0u;
}

static void sample_busy_edges(comp_ssd1681_wba_t *driver)
{
#if COMP_V11_PANEL_PASSIVE_TRACE
    if (driver->config.take_busy_edges) {
        const uint8_t edges = driver->config.take_busy_edges(
            driver->config.context, COMP_SSD1681_WBA_BUSY_EDGES_SAMPLE);
        if (driver->stage == ST_WAIT_RESET_READY &&
            driver->stats.first_failure_error == COMP_SSD1681_WBA_ERROR_NONE) {
            driver->stats.first_ready_edge_flags |= edges;
            if ((edges & 1u) != 0u) driver->stats.first_ready_rise_samples++;
        }
        if (driver->stage == ST_WAIT_VISIBLE || driver->stage == ST_RECOVER_MODE2_RESET)
            driver->stats.visible_edge_flags |= edges;
        /* A latched rise vetoes sampled ready even when the pin has returned
         * low before this poll. It never proves a visible refresh started.
         * Restart the existing quiet interval; keep its original deadline. */
        if ((edges & 1u) != 0u) {
            if (driver->ready_candidate) driver->stats.ready_glitches++;
            driver->ready_candidate = false;
        }
    }
#else
    (void)driver;
#endif
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
    stop_busy_edges(driver);
    driver->ready_candidate = false;
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

static bool read_previous(comp_ssd1681_wba_t *driver,const uint8_t *frame,
                           size_t offset,uint8_t *out,size_t count)
{
#if COMP_WBA_PACKED_OLD_FRAME
    if(driver->old_store && frame==driver->old_store->bytes)
        return comp_wba_frame_store_read(driver->old_store,offset,out,count);
#else
    (void)driver;
#endif
    memcpy(out,frame+offset,count);return true;
}
bool comp_ssd1681_wba_read_frame(comp_ssd1681_wba_t *driver,const uint8_t *frame,
    size_t at,uint8_t *out,size_t bytes)
{
    return driver && frame && out && at<=COMP_SSD1681_WBA_FRAME_BYTES &&
        bytes<=COMP_SSD1681_WBA_FRAME_BYTES-at && read_previous(driver,frame,at,out,bytes);
}
#if COMP_WBA_PACKED_OLD_FRAME
bool comp_ssd1681_wba_bind_old_store(comp_ssd1681_wba_t *driver,comp_wba_frame_store_t *store)
{
    if(!driver || !store || driver->status==COMP_SSD1681_WBA_ACTIVE)return false;
    driver->old_store=store;return true;
}
#endif
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
    if (driver->activation_repairing)
        driver->deadline_ms = driver->activation_deadline_ms;
    /* 0x20 may assert BUSY before this foreground call returns. Preserve that
     * sample even if another service runs before the next panel poll. */
    driver->busy_observed = driver->config.is_busy(driver->config.context);
    driver->ready_candidate = false;
#if COMP_V11_PANEL_PASSIVE_TRACE
    if (stage == ST_WAIT_RESET_READY) {
        if (driver->config.take_busy_edges)
            (void)driver->config.take_busy_edges(driver->config.context,
                COMP_SSD1681_WBA_BUSY_EDGES_ARM);
        if (driver->stats.first_failure_error == COMP_SSD1681_WBA_ERROR_NONE) {
            driver->stats.first_ready_started_ms = driver->wait_started_ms;
            driver->stats.first_ready_last_poll_ms = driver->wait_started_ms;
            driver->stats.first_ready_samples = 1u;
            driver->stats.first_ready_high_samples = driver->busy_observed ? 1u : 0u;
            driver->stats.first_ready_max_poll_gap_ms = 0u;
            driver->stats.first_ready_max_quiet_ms = 0u;
            driver->stats.first_ready_rise_samples = 0u;
            driver->stats.first_ready_edge_flags = 0u;
        }
    }
    if (stage == ST_WAIT_VISIBLE) {
        driver->stats.visible_activation_count++;
        driver->stats.visible_started_ms = driver->wait_started_ms;
        driver->stats.visible_first_high_ms = driver->busy_observed ?
            driver->wait_started_ms : UINT32_MAX;
        driver->stats.visible_last_high_ms = driver->stats.visible_first_high_ms;
        driver->stats.visible_high_samples = driver->busy_observed ? 1u : 0u;
        driver->stats.visible_poll_samples = 1u;
        driver->stats.visible_last_poll_ms = driver->wait_started_ms;
        driver->stats.visible_max_poll_gap_ms = 0u;
        driver->stats.visible_edges_available = driver->config.take_busy_edges != NULL;
        if (driver->config.take_busy_edges)
            driver->stats.visible_edge_flags |= driver->config.take_busy_edges(
                driver->config.context, COMP_SSD1681_WBA_BUSY_EDGES_SAMPLE);
        if(driver->activation_repairing && driver->activation_retried)
            driver->stats.recovery_activation_ms=driver->wait_started_ms;
    }
#endif
}

static bool sampled_ready(comp_ssd1681_wba_t *driver, uint32_t now, bool busy)
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
#if COMP_V11_PANEL_PASSIVE_TRACE
    const uint32_t quiet_ms = now - driver->ready_started_ms;
    if (driver->status == COMP_SSD1681_WBA_ACTIVE &&
        driver->stage == ST_WAIT_RESET_READY &&
        driver->stats.first_failure_error == COMP_SSD1681_WBA_ERROR_NONE &&
        quiet_ms > driver->stats.first_ready_max_quiet_ms)
        driver->stats.first_ready_max_quiet_ms = quiet_ms;
#endif
    return time_reached(now, driver->ready_started_ms + BUSY_READY_STABLE_MS);
}

static bool stable_ready(comp_ssd1681_wba_t *driver, uint32_t now, bool busy)
{
    /* Also sample after command callbacks, before their pending parameters.
     * This covers a short rise between command and data in the same poll. */
    sample_busy_edges(driver);
    return sampled_ready(driver, now, busy);
}

static bool paired_mode2(const comp_ssd1681_wba_t *driver)
{
    return driver->operation == OP_PARTIAL || driver->operation == OP_FAST ||
           (driver->operation == OP_RECORDING && driver->activation_repairing);
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

static bool dirty_bounds(comp_ssd1681_wba_t *driver,
                         comp_ssd1681_wba_window_t *bounds)
{
    bool found = false;

    uint8_t old_row[COMP_SSD1681_WBA_BYTES_PER_ROW];
    if(driver->operation==OP_RECORDING && driver->recording_dirty_valid) {
        *bounds=driver->recording_dirty_bounds;return true;
    }
    for (uint16_t y = 0u; y < COMP_SSD1681_WBA_HEIGHT; ++y) {
        /* Decode one whole old row once. Calling the Huffman/delta reader
         * for every byte repeats validation/division/copy5000 times. */
        if(!read_previous(driver,driver->previous_frame,
            (size_t)y*COMP_SSD1681_WBA_BYTES_PER_ROW,old_row,sizeof(old_row))) {
            fail(driver,COMP_SSD1681_WBA_ERROR_ARGUMENT);return false;
        }
        for (uint8_t x = 0u; x < COMP_SSD1681_WBA_BYTES_PER_ROW; ++x) {
            const size_t offset =
                (size_t)y * COMP_SSD1681_WBA_BYTES_PER_ROW + x;
            const uint8_t old=old_row[x];
            if(driver->status==COMP_SSD1681_WBA_ERROR)return false;
            if (old == driver->current_frame[offset]) {
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
    if(found && driver->operation==OP_RECORDING) {
        driver->recording_dirty_bounds=*bounds;driver->recording_dirty_valid=true;
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

    if(driver->recording_ordinary_region>=4u)return false;
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
static uint8_t next_recording_run(comp_ssd1681_wba_t *driver)
{
    const bool inside = true;
    uint16_t offset = driver->scan_offset;
    uint16_t loaded_y=UINT16_MAX;
    uint8_t old_row[COMP_SSD1681_WBA_BYTES_PER_ROW];

    while (offset < COMP_SSD1681_WBA_FRAME_BYTES) {
        const uint16_t y =
            (uint16_t)(offset / COMP_SSD1681_WBA_BYTES_PER_ROW);
        const uint8_t x =
            (uint8_t)(offset % COMP_SSD1681_WBA_BYTES_PER_ROW);
        const bool eligible =
            byte_in_window(&driver->recording_window, x, y) == inside;

        if(eligible && loaded_y!=y) {
            /* One decoded row per dispatch, including a long unchanged tail.
             * Retain the exact byte cursor so audio can run between rows. */
            if(loaded_y!=UINT16_MAX) {driver->scan_offset=offset;return 2u;}
            if(!read_previous(driver,driver->previous_frame,
                (size_t)y*COMP_SSD1681_WBA_BYTES_PER_ROW,old_row,sizeof(old_row))) {
                fail(driver,COMP_SSD1681_WBA_ERROR_ARGUMENT);return false;
            }
            loaded_y=y;
        }
        const uint8_t old=eligible?old_row[x]:0u;
        if(driver->status==COMP_SSD1681_WBA_ERROR)return false;
        if (eligible && old !=
                            driver->current_frame[offset]) {
            uint8_t end = x;
            while (end + 1u < COMP_SSD1681_WBA_BYTES_PER_ROW) {
                const uint8_t candidate = (uint8_t)(end + 1u);
                const uint16_t candidate_offset =
                    (uint16_t)(offset + (candidate - x));
                if (byte_in_window(&driver->recording_window, candidate, y) !=
                        inside ||
                    old_row[candidate] == driver->current_frame[candidate_offset]) {
                    break;
                }
                end = candidate;
            }
            driver->window = (comp_ssd1681_wba_window_t){x, end, y, y};
            if(driver->status==COMP_SSD1681_WBA_ERROR)return false;
            driver->scan_offset = (uint16_t)(offset + (end - x) + 1u);
            prepare_window(driver);
            return true;
        }
        offset++;
    }
    driver->scan_offset = offset;
    return false;
}

/* Rebase every region touched by this activation in both RAM planes.
 * Keep the ordinary rectangles outside the recording window and the exact
 * changed-byte runs inside it. Each window/row still yields to capture. */
static uint8_t next_recording_region(comp_ssd1681_wba_t *driver)
{
    if (driver->recording_phase == RECORDING_PHASE_ORDINARY)
        return next_ordinary_region(driver);
    if ((driver->recording_phase == RECORDING_PHASE_POST_CURRENT ||
         driver->recording_phase == RECORDING_PHASE_POST_PREVIOUS) &&
        driver->recording_ordinary_region < 4u && next_ordinary_region(driver))
        return true;
    return next_recording_run(driver);
}

/* Recording diff discovery is CPU work, not an SPI packet. Schedule it as
 * foreground slices too; a late changed row must not scan/decode the whole
 * packed frame before servicing microphone DMA. No new frame or RAM arena. */
static void start_next_recording_run(comp_ssd1681_wba_t *driver)
{driver->stage=ST_RECORDING_SCAN;}
static void poll_recording_bounds(comp_ssd1681_wba_t *driver)
{
    const uint16_t y=(uint16_t)(driver->scan_offset/COMP_SSD1681_WBA_BYTES_PER_ROW);
    uint8_t row[COMP_SSD1681_WBA_BYTES_PER_ROW];
    if(y>=COMP_SSD1681_WBA_HEIGHT) {
        if(driver->recording_dirty_bounds.x_start_byte>driver->recording_dirty_bounds.x_end_byte) {
            fail(driver,COMP_SSD1681_WBA_ERROR_ARGUMENT);return;
        }
        driver->recording_dirty_valid=true;driver->scan_offset=0u;
        start_next_recording_run(driver);return;
    }
    if(!read_previous(driver,driver->previous_frame,driver->scan_offset,row,sizeof(row))) {
        fail(driver,COMP_SSD1681_WBA_ERROR_ARGUMENT);return;
    }
    comp_ssd1681_wba_window_t *b=&driver->recording_dirty_bounds;
    for(uint8_t x=0u;x<COMP_SSD1681_WBA_BYTES_PER_ROW;++x) {
        if(row[x]==driver->current_frame[driver->scan_offset+x])continue;
        if(x<b->x_start_byte)b->x_start_byte=x;
        if(x>b->x_end_byte)b->x_end_byte=x;
        if(y<b->y_start)b->y_start=y;
        if(y>b->y_end)b->y_end=y;
    }
    driver->scan_offset=(uint16_t)(driver->scan_offset+sizeof(row));
}

static void poll_recording_run(comp_ssd1681_wba_t *driver)
{
    const uint8_t result=next_recording_region(driver);
    if(result==2u)return;
    if(result==0u) {
        if(driver->status==COMP_SSD1681_WBA_ERROR)return;
        if (driver->recording_phase == RECORDING_PHASE_ORDINARY) {
            driver->recording_phase = RECORDING_PHASE_OLD;
        } else if (driver->recording_phase == RECORDING_PHASE_OLD) {
            driver->recording_phase = RECORDING_PHASE_CURRENT;
        } else if (driver->recording_phase == RECORDING_PHASE_CURRENT) {
            /* Each sparse write changes the controller's RAM area. Restore
             * the union of this frame's changes before activation, including
             * face/status rectangles outside the recording overlay. The last
             * one-row run must not become the refresh area for the whole
             * transaction. This sequence only sets registers, never RAM or
             * another visible activation. */
            if (!dirty_bounds(driver, &driver->window)) {
                fail(driver, COMP_SSD1681_WBA_ERROR_ARGUMENT);
                return;
            }
            prepare_window(driver);
            set_sequence(driver, SEQ_RECORDING_ACTIVATE_WINDOW);
            return;
        } else if (driver->recording_phase == RECORDING_PHASE_POST_CURRENT) {
            driver->recording_phase = RECORDING_PHASE_POST_PREVIOUS;
            driver->recording_ordinary_region = 0u;
        } else {
            complete_operation(driver);
            return;
        }
        driver->scan_offset = 0u;
        return;
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
    case SEQ_FULL_REBASE_CURRENT_WINDOW:
        return 8u;
    case SEQ_PARTIAL_WINDOW:
    case SEQ_RECORDING_ACTIVATE_WINDOW:
        return 6u;
    case SEQ_RECORDING_WINDOW:
    case SEQ_RECOVER_MODE2_SETUP:
        return 5u;
    case SEQ_FULL_ACTIVATE:
    case SEQ_PARTIAL_ACTIVATE:
    case SEQ_PARTIAL_CURSOR:
#if COMP_V11_PANEL_VENDOR_QUICK_FULL
    case SEQ_VENDOR_CURSOR:
#endif
        return 2u;
    case SEQ_REARM_MODE2:
        return 3u;
#if COMP_V11_PANEL_VENDOR_QUICK_FULL
    case SEQ_VENDOR_FULL_SETUP:
        return 9u;
#endif
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
#if COMP_V11_PANEL_VENDOR_QUICK_FULL
    case SEQ_VENDOR_FULL_SETUP:
        /* EPD_HW_Init_LUT geometry/border, then its four literal tail
         * register bindings. R32 and the two RAM counters follow separately. */
        switch (index) {
        case 0u: return (sequence_item_t){0x01u, k_driver, sizeof(k_driver)};
        case 1u: return (sequence_item_t){0x11u, k_entry, sizeof(k_entry)};
        case 2u: return (sequence_item_t){0x44u, driver->ram_x, sizeof(driver->ram_x)};
        case 3u: return (sequence_item_t){0x45u, driver->ram_y, sizeof(driver->ram_y)};
        case 4u: return (sequence_item_t){0x3Cu, k_border_normal, sizeof(k_border_normal)};
        case 5u: return (sequence_item_t){0x3Fu, &k_vendor_quick_lut[153], 1u};
        case 6u: return (sequence_item_t){0x03u, &k_vendor_quick_lut[154], 1u};
        case 7u: return (sequence_item_t){0x04u, &k_vendor_quick_lut[155], 3u};
        default: return (sequence_item_t){0x2Cu, &k_vendor_quick_lut[158], 1u};
        }
#endif
    case SEQ_MODE1_TEMP: {
        static const sequence_item_t items[] = {
            {0x18u, k_80, sizeof(k_80)},
            {0x22u, k_b1, sizeof(k_b1)},
            {0x20u, NULL, 0u},
        };
        return items[index];
    }
    case SEQ_PARTIAL_CURSOR:
#if COMP_V11_PANEL_VENDOR_QUICK_FULL
    case SEQ_VENDOR_CURSOR:
#endif
        /* The preceding RAM plane used this exact area and entry direction.
         * Only the address counters advanced. Rewind both counters before
         * writing the other plane; do not reprogram unchanged window/border
         * registers or remove any OLD/CURRENT/post-sync frame bytes. */
        return index == 0u
            ? (sequence_item_t){0x4Eu, driver->x_counter, sizeof(driver->x_counter)}
            : (sequence_item_t){0x4Fu, driver->y_counter, sizeof(driver->y_counter)};
    case SEQ_FULL_OLD_WINDOW:
    case SEQ_FULL_CURRENT_WINDOW:
    case SEQ_FULL_REBASE_WINDOW:
    case SEQ_FULL_REBASE_CURRENT_WINDOW:
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
    case SEQ_RECORDING_ACTIVATE_WINDOW:
        /* Every ordinary Mode2 RAM window carries its own entry direction.
         * Keep X-increment/Y-decrement consistent with prepare_window and
         * the accepted row mapping, rather than inheriting only the boot
         * setting. This is an addressing guard, not a waveform change or
         * a claim that the translated electrical bus is reliable. Normal
         * sparse recording retains its existing five-register cadence. */
        if (index == 0u)
            return (sequence_item_t){0x11u, k_entry, sizeof(k_entry)};
        index--;
        /* fall through */
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
#if COMP_V11_PANEL_VENDOR_QUICK_FULL
        if (driver->operation == OP_VENDOR_QUICK_FULL)
            return index == 0u ? (sequence_item_t){0x22u, k_c7, sizeof(k_c7)}
                               : (sequence_item_t){0x20u, NULL, 0u};
#endif
        return index == 0u ? (sequence_item_t){0x22u, k_full_update, sizeof(k_full_update)}
                           : (sequence_item_t){0x20u, NULL, 0u};
    case SEQ_PARTIAL_ACTIVATE:
        /* Good Display's GDEY0154D67 EPD_Part_Update uses FF on every
         * ordinary partial activation. Reload actual temperature and Mode2
         * here instead of relying on the earlier B9/cached CF profile.
         * FF includes the same analog/clock shutdown as CF, so this does
         * not adopt the FC retained-power policy used by GxEPD2. Keep the
         * recording transaction and its recovery CF path unchanged. */
        return index == 0u ? (sequence_item_t){0x22u,
                                driver->operation == OP_RECORDING ? k_cf : k_ff, 1u}
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
    case SEQ_RECOVER_MODE2_SETUP: {
        static const sequence_item_t items[] = {
            {0x01u, k_driver, sizeof(k_driver)},
            {0x11u, k_entry, sizeof(k_entry)},
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
    const uint8_t final_edges = stop_busy_edges(driver);
    /* STOP drains a final latch after this poll's ready check. A rise there
     * still vetoes the commit, even if BUSY is low again. Keep the immutable
     * buffers and original deadline, re-arm observation and qualify ready
     * again without sending any more RAM bytes or another activation. */
    if ((final_edges & 1u) != 0u ||
        driver->config.is_busy(driver->config.context)) {
        driver->ready_candidate = false;
        driver->stats.ready_glitches++;
#if COMP_V11_PANEL_PASSIVE_TRACE
        if (driver->config.take_busy_edges)
            (void)driver->config.take_busy_edges(driver->config.context,
                COMP_SSD1681_WBA_BUSY_EDGES_ARM);
#endif
        return;
    }
    driver->stats.last_completed_ms = now_ms(driver);
    if (driver->operation == OP_PARTIAL || driver->operation == OP_FAST) {
        /* The hardware RAM window was expanded only after BUSY completed.
         * Retain the actual visible window for the completion observation.
         * recording_window is otherwise unused by these two operations. */
        driver->window = driver->recording_window;
        prepare_window(driver);
    }
    if (driver->activation_retried) {
        driver->stats.activation_recoveries++;
        driver->stats.activation_recovery_last_ms = driver->stats.last_completed_ms -
            (driver->activation_deadline_ms - driver->config.busy_timeout_ms);
    }
    driver->activation_repairing = false;
    if ((driver->operation == OP_PARTIAL || driver->operation == OP_FAST ||
         (driver->operation == OP_RECORDING && driver->activation_retried)) &&
        (driver->recording_phase == RECORDING_PHASE_POST_CURRENT ||
         driver->recording_phase == RECORDING_PHASE_POST_PREVIOUS)) {
        driver->stats.completed_paired++;
        if (driver->recording_phase == RECORDING_PHASE_POST_PREVIOUS &&
            driver->normalize_previous)
            driver->stats.completed_blink_rebases++;
    }
    if (mode1_operation(driver)) {
        driver->baseline_valid = true;
        driver->maintenance_required = false;
        driver->stats.partial_count = 0u;
        driver->stats.completed_full++;
        /* Supplier quick-full is not proof of the normal cleaning waveform.
         * Keep eligibility for the independent settled F7 clean intact. */
        if (driver->operation == OP_FULL) {
            driver->stats.last_full_ms = driver->stats.last_completed_ms;
            driver->stats.mode2_since_full = 0u;
        } else {
            driver->stats.mode2_since_full++;
        }
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
#if COMP_V11_PANEL_VENDOR_QUICK_FULL
    case SEQ_VENDOR_FULL_SETUP:
        driver->stage = ST_VENDOR_LUT;
        driver->data_command_sent = 0u;
        driver->data_x = 0u; /* RAM is not being transferred during LUT load. */
        break;
    case SEQ_VENDOR_CURSOR:
        driver->sequence = SEQ_FULL_CURRENT_WINDOW;
        start_data(driver);
        break;
#endif
    case SEQ_MODE1_TEMP:
        arm_busy_wait(driver, ST_WAIT_MODE1_TEMP);
        break;
    case SEQ_FULL_OLD_WINDOW:
    case SEQ_FULL_CURRENT_WINDOW:
    case SEQ_FULL_REBASE_WINDOW:
    case SEQ_FULL_REBASE_CURRENT_WINDOW:
    case SEQ_PARTIAL_WINDOW:
    case SEQ_PARTIAL_CURSOR:
    case SEQ_RECORDING_WINDOW:
        start_data(driver);
        break;
    case SEQ_RECORDING_ACTIVATE_WINDOW:
        set_sequence(driver, SEQ_PARTIAL_ACTIVATE);
        break;
    case SEQ_FULL_ACTIVATE:
    case SEQ_PARTIAL_ACTIVATE:
        arm_busy_wait(driver, ST_WAIT_VISIBLE);
        break;
    case SEQ_REARM_MODE2:
    case SEQ_RECOVER_MODE2_SETUP:
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
    /* Keep the normal command/parameter cadence in one foreground poll.
     * BUSY can change between the two transfer callbacks. Retain a sent
     * command while waiting for its parameters; never repeat it or write
     * through BUSY. The existing sequence deadline remains in force. */
    if (driver->sequence_data_pending == 0u) {
#if COMP_V11_PANEL_PASSIVE_TRACE
    if (item.command == 0x20u &&
        (driver->sequence == SEQ_FULL_ACTIVATE || driver->sequence == SEQ_PARTIAL_ACTIVATE)) {
        /* Discard reset/LUT/RAM-phase edges before the actual activation.
         * The edge latch is sampled independently of the BUSY level gate. */
        driver->stats.visible_edge_flags = 0u;
        if (driver->config.take_busy_edges)
            (void)driver->config.take_busy_edges(driver->config.context,
                COMP_SSD1681_WBA_BUSY_EDGES_ARM);
    }
#endif
        if (!send_command(driver, item.command)) return;
        driver->sequence_data_pending = item.size != 0u;
    }
    if (driver->sequence_data_pending != 0u) {
        if (!stable_ready(driver, now_ms(driver),
                          driver->config.is_busy(driver->config.context))) return;
        if (!send_bytes(driver, true, item.data, item.size)) return;
        driver->sequence_data_pending = 0u;
    }
    driver->sequence_index++;
    if (driver->sequence_index >= count) {
        sequence_complete(driver);
    }
}

static void data_complete(comp_ssd1681_wba_t *driver)
{
    if (driver->operation == OP_RECORDING && !driver->activation_repairing) {
        start_next_recording_run(driver);
    } else if (paired_mode2(driver)) {
        if (driver->recording_phase == RECORDING_PHASE_OLD) {
            driver->recording_phase = RECORDING_PHASE_CURRENT;
            set_sequence(driver, SEQ_PARTIAL_CURSOR);
        } else if (driver->recording_phase == RECORDING_PHASE_POST_CURRENT) {
            /* Mode-2 RAM is the baseline for the next activation, including
             * pixels outside its next window. Normalize it for every frame,
             * not only authored blink-open. No second activation is sent. */
            driver->recording_phase = RECORDING_PHASE_POST_PREVIOUS;
            set_sequence(driver, SEQ_PARTIAL_CURSOR);
        } else if (driver->recording_phase == RECORDING_PHASE_POST_PREVIOUS) {
            complete_operation(driver);
        } else {
            set_sequence(driver, SEQ_PARTIAL_ACTIVATE);
        }
    } else if (driver->sequence == SEQ_FULL_OLD_WINDOW) {
        set_sequence(driver, SEQ_FULL_CURRENT_WINDOW);
    } else if (driver->sequence == SEQ_FULL_CURRENT_WINDOW) {
        set_sequence(driver, SEQ_FULL_ACTIVATE);
    } else if (driver->sequence == SEQ_FULL_REBASE_CURRENT_WINDOW) {
        set_sequence(driver, SEQ_FULL_REBASE_WINDOW);
    } else if (driver->sequence == SEQ_FULL_REBASE_WINDOW) {
#if COMP_V11_PANEL_VENDOR_QUICK_FULL
        if (driver->operation == OP_VENDOR_QUICK_FULL) {
            /* Both RAM planes now equal the visible image. The software
             * binding leaves B9 pending until a real Mode2 request, so a
             * static C7 image is not immediately switched to another LUT.
             * Hardware-reset restoration retains its existing eager path. */
            complete_operation(driver);
            return;
        }
#endif
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
        driver->operation == OP_RECORDING && !driver->activation_repairing
            ? (driver->recording_phase == RECORDING_PHASE_OLD ||
               driver->recording_phase == RECORDING_PHASE_POST_PREVIOUS ? 0x26u : 0x24u) :
        paired_mode2(driver) ?
            (driver->recording_phase == RECORDING_PHASE_OLD ||
             driver->recording_phase == RECORDING_PHASE_POST_PREVIOUS ? 0x26u : 0x24u) :
        driver->sequence == SEQ_FULL_OLD_WINDOW ? 0x26u :
        (driver->sequence == SEQ_FULL_CURRENT_WINDOW ||
         driver->sequence == SEQ_FULL_REBASE_CURRENT_WINDOW) ? 0x24u : 0x26u;
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
    bool contiguous_idle;

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
    offset = (size_t)driver->data_y * COMP_SSD1681_WBA_BYTES_PER_ROW +
             driver->data_x;
    /* With the full byte width, the controller's row wrap and the immutable
     * framebuffer stride are identical. Use the already configured packet
     * budget only under the existing idle/audio/platform admission callback.
     * A narrow window has gaps in the source bitmap; capture keeps its old
     * row boundary even during a recovery rebuild. No extra staging buffer,
     * address command, waveform or shorter ready/deadline is introduced. */
    contiguous_idle = driver->window.x_start_byte == 0u &&
        driver->window.x_end_byte == COMP_SSD1681_WBA_BYTES_PER_ROW - 1u &&
        driver->operation != OP_RECORDING &&
        driver->config.allow_mode2_recovery != NULL &&
        driver->config.allow_mode2_recovery(driver->config.context);
    remaining = contiguous_idle
        ? (uint16_t)(((size_t)driver->window.y_end + 1u) *
                     COMP_SSD1681_WBA_BYTES_PER_ROW - offset)
        : (uint16_t)(driver->window.x_end_byte - driver->data_x + 1u);
    size = remaining < driver->config.payload_chunk_bytes
               ? remaining
               : driver->config.payload_chunk_bytes;
#if COMP_WBA_PACKED_OLD_FRAME
    uint8_t restored[MAX_CHUNK_BYTES];
    const bool packed=driver->old_store && frame==driver->old_store->bytes;
    if(packed && !read_previous(driver,frame,offset,restored,size)) {
        fail(driver,COMP_SSD1681_WBA_ERROR_ARGUMENT);return;
    }
    const uint8_t *payload=packed?restored:frame+offset;
#else
    const uint8_t *payload=frame+offset;
#endif
    if (!send_bytes(driver, true, payload, size)) {
        return;
    }
    if (contiguous_idle) {
        offset += size;
        driver->data_y = (uint16_t)(offset / COMP_SSD1681_WBA_BYTES_PER_ROW);
        driver->data_x = (uint8_t)(offset % COMP_SSD1681_WBA_BYTES_PER_ROW);
    } else {
        driver->data_x = (uint8_t)(driver->data_x + size);
        if (driver->data_x > driver->window.x_end_byte) {
            driver->data_y++;
            driver->data_x = driver->window.x_start_byte;
        }
    }
    /* Finish this RAM phase on the next poll, after the shared ready guard
     * has also checked any rise latched during the final transfer callback.
     * Keep the buffers locked; do not send another RAM packet/activation. */
}

static bool window_valid(const comp_ssd1681_wba_window_t *window)
{
    return window != NULL &&
           window->x_start_byte <= window->x_end_byte &&
           window->x_end_byte < COMP_SSD1681_WBA_BYTES_PER_ROW &&
           window->y_start <= window->y_end &&
           window->y_end < COMP_SSD1681_WBA_HEIGHT;
}

static bool window_contains_frame_delta(comp_ssd1681_wba_t *driver,const uint8_t *previous,
                                        const uint8_t *current,
                                        const comp_ssd1681_wba_window_t *window)
{
    /* A paired local write may represent a complete new image only when
     * every changed byte lies inside that window. Otherwise a full post-sync
     * would install pixels that were never staged for the visible update.
     * The complete immutable frames remain the source of truth. */
    for (uint16_t y = 0u; y < COMP_SSD1681_WBA_HEIGHT; ++y) {
        const size_t row = (size_t)y * COMP_SSD1681_WBA_BYTES_PER_ROW;
        uint8_t old_row[COMP_SSD1681_WBA_BYTES_PER_ROW];
        if(!read_previous(driver,previous,row,old_row,sizeof(old_row)))return false;
        if (y < window->y_start || y > window->y_end) {
            if (memcmp(old_row, current + row,
                       COMP_SSD1681_WBA_BYTES_PER_ROW) != 0) return false;
        } else {
            const size_t right = (size_t)window->x_end_byte + 1u;
            if (memcmp(old_row, current + row,
                       window->x_start_byte) != 0 ||
                memcmp(old_row + right, current + row + right,
                       COMP_SSD1681_WBA_BYTES_PER_ROW - right) != 0) return false;
        }
    }
    return true;
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
#if COMP_V11_PANEL_VENDOR_QUICK_FULL
    /* Owner:all full-frame entries prefer the supplier's fast full waveform.
     * This includes startup, the button, recovery and periodic cleaning, but
     * needs its explicit hardware/software reset binding and profile. Never
     * bypass visibility/rebase/rearm or shorten BUSY to imitate quick full. */
    driver->operation = comp_ssd1681_wba_vendor_quick_full_available(driver)?
        OP_VENDOR_QUICK_FULL:OP_FULL;
#else
    driver->operation = OP_FULL;
#endif
    driver->normalize_previous = false;
    driver->mode2_rearm_pending = false;
    driver->activation_retried = false;
    driver->activation_retry_checked = false;
    driver->activation_repairing = false;
    if (driver->config.reset_mode == COMP_SSD1681_WBA_RESET_SOFTWARE_ONLY) {
        /* Supply settling and BUSY readiness precede 0x12. No imaginary
         * hardware reset/power cycle is performed in this mode. */
        driver->deadline_ms = now_ms(driver) + RESET_RELEASE_MS;
        driver->stage = ST_RESET_RELEASE_WAIT;
    } else {
        driver->stage = ST_RESET_ASSERT;
    }
    /* A replacement baseline is not valid until visibility and both RAM
     * planes are synchronized. A deferred Mode2 rearm is a separate gate
     * inside the next transaction, never permission to activate its CF/FF. */
    driver->baseline_valid = false;
    driver->maintenance_required = false;
    driver->stats.partial_count = 0u;
    driver->status = COMP_SSD1681_WBA_ACTIVE;
    driver->error = COMP_SSD1681_WBA_ERROR_NONE;
    return true;
}

bool comp_ssd1681_wba_start_flashing_full(comp_ssd1681_wba_t *driver,
    const uint8_t *previous_frame,const uint8_t *current_frame,size_t frame_bytes)
{
    if (!comp_ssd1681_wba_start_full(driver,previous_frame,current_frame,frame_bytes))
        return false;
    /* Explicit physical double click requests the existing F7 Mode1 route,
     * even when generic full entries prefer the supplier C7 quick route. */
    driver->operation=OP_FULL;
    return true;
}

bool comp_ssd1681_wba_vendor_quick_full_available(const comp_ssd1681_wba_t *driver)
{
#if COMP_V11_PANEL_VENDOR_QUICK_FULL
    return driver != NULL && driver->status != COMP_SSD1681_WBA_NOT_READY &&
        ((driver->config.reset_mode == COMP_SSD1681_WBA_RESET_HARDWARE &&
          driver->config.set_reset != NULL)
#if COMP_V11_PANEL_VENDOR_QUICK_SOFTWARE_RESET
         || driver->config.reset_mode == COMP_SSD1681_WBA_RESET_SOFTWARE_ONLY
#endif
        );
#else
    (void)driver;
    return false;
#endif
}

bool comp_ssd1681_wba_start_vendor_quick_full(comp_ssd1681_wba_t *driver,
    const uint8_t *previous_frame, const uint8_t *current_frame, size_t frame_bytes)
{
#if COMP_V11_PANEL_VENDOR_QUICK_FULL
    if (!comp_ssd1681_wba_vendor_quick_full_available(driver)) return false;
    if (!comp_ssd1681_wba_start_full(driver, previous_frame, current_frame, frame_bytes))
        return false;
    driver->operation = OP_VENDOR_QUICK_FULL;
    return true;
#else
    (void)driver; (void)previous_frame; (void)current_frame; (void)frame_bytes;
    return false;
#endif
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
        !window_valid(window) ||
        (previous_frame != NULL &&
         !window_contains_frame_delta(driver,previous_frame, current_frame, window))) {
        driver->error = COMP_SSD1681_WBA_ERROR_ARGUMENT;
        return false;
    }
    driver->current_frame = current_frame;
    driver->previous_frame = previous_frame;
    driver->normalize_previous = false;
    driver->recording_phase = previous_frame == NULL ? RECORDING_PHASE_ORDINARY :
                                                     RECORDING_PHASE_OLD;
    driver->window = *window;
    /* Stage a complete old/new pair for the first paired Mode2 after F7,
     * in addition to normalizing both planes AFTER visible activation. The
     * Owner observed a stable F7-static picture and fading after motion;
     * rebuilding the first input pair isolates that addressing/history
     * dependency. This is a candidate repair, not optical qualification.
     * Validate the caller's delta window above before widening it. Keep FF,
     * one activation, row-sized audio yields and later local windows. The
     * recording sparse path never enters this function. */
    if (!fast && previous_frame != NULL && driver->stats.mode2_since_full == 0u)
        driver->window = (comp_ssd1681_wba_window_t){0u,24u,0u,199u};
    prepare_window(driver);
    driver->operation = fast?OP_FAST:OP_PARTIAL;
    driver->activation_retried = false;
    driver->activation_retry_checked = false;
    driver->activation_repairing = false;
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
    uint8_t old_row[COMP_SSD1681_WBA_BYTES_PER_ROW];
    for(size_t at=0u;at<frame_bytes;at+=sizeof(old_row)) {
        if(!read_previous(driver,previous_frame,at,old_row,sizeof(old_row))) {
            fail(driver,COMP_SSD1681_WBA_ERROR_ARGUMENT);return false;
        }
        if(driver->status==COMP_SSD1681_WBA_ERROR)return false;
        if(memcmp(old_row,current_frame+at,sizeof(old_row))) {changed=true;break;}
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
    driver->recording_dirty_valid = false;
    driver->scan_offset = 0u;
    driver->operation = OP_RECORDING;
    driver->activation_retried = false;
    driver->activation_retry_checked = false;
    driver->activation_repairing = false;
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
    if (driver->status == COMP_SSD1681_WBA_ERROR) {
        /* Filter recovery admission before consuming/rendering another frame.
         * ERROR has stopped EXTI observation: these are foreground samples,
         * not a claim of continuous or latched-edge qualification. Keep IMR
         * masked while waiting. The admitted transaction still arms its own
         * original edge-qualified 20ms gate before any SPI command. */
        (void)sampled_ready(driver, now, busy);
        return driver->status;
    }
    if (driver->status != COMP_SSD1681_WBA_ACTIVE) return driver->status;
    sample_busy_edges(driver);
    if (driver->activation_repairing &&
        time_reached(now, driver->activation_deadline_ms)) {
        fail(driver, COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT);
        return driver->status;
    }
#if COMP_V11_PANEL_PASSIVE_TRACE
    if (driver->stage == ST_WAIT_RESET_READY &&
        driver->stats.first_failure_error == COMP_SSD1681_WBA_ERROR_NONE) {
        const uint32_t gap = now - driver->stats.first_ready_last_poll_ms;
        driver->stats.first_ready_last_poll_ms = now;
        if (gap > driver->stats.first_ready_max_poll_gap_ms)
            driver->stats.first_ready_max_poll_gap_ms = gap;
        driver->stats.first_ready_samples++;
        if (busy) driver->stats.first_ready_high_samples++;
    }
    if (driver->stage == ST_WAIT_VISIBLE || driver->stage == ST_RECOVER_MODE2_RESET) {
        const uint32_t gap = now - driver->stats.visible_last_poll_ms;
        driver->stats.visible_last_poll_ms = now;
        if (gap > driver->stats.visible_max_poll_gap_ms)
            driver->stats.visible_max_poll_gap_ms = gap;
        driver->stats.visible_poll_samples++;
        if (busy) {
            if (driver->stats.visible_high_samples == 0u)
                driver->stats.visible_first_high_ms = now;
            driver->stats.visible_last_high_ms = now;
            driver->stats.visible_high_samples++;
        }
    }
#endif
    /* An unexpected BUSY assertion between foreground RAM/register packets
     * must stop writes immediately. Start/end waits alone do not protect the
     * gaps between rows. Resume only after the existing stable-ready filter;
     * keep the armed deadline so a stuck signal cannot strand the presenter.
     * This is a sampled guard, not a claim of continuous electrical capture. */
    /* Ready may change after ST_WAIT_RESET_READY advances to the separate
     * software-reset poll. Recheck 0x12 like the other command writes; a
     * prior ready sample cannot authorize a command while BUSY is high. */
    /* The missed-start reset also qualifies low here. Its high-BUSY branch
     * remains available below so a late original activation wins the handoff. */
    if ((driver->stage == ST_SOFTWARE_RESET ||
         driver->stage == ST_SEQUENCE || driver->stage == ST_DATA ||
#if COMP_V11_PANEL_VENDOR_QUICK_FULL
         driver->stage == ST_VENDOR_LUT ||
#endif
         (driver->stage == ST_RECOVER_MODE2_RESET && !busy)) &&
        !stable_ready(driver, now, busy)) {
        if (time_reached(now, driver->deadline_ms))
            fail(driver, COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT);
        return driver->status;
    }
    switch (driver->stage) {
    case ST_RESET_ASSERT:
        if (!driver->config.set_reset(driver->config.context, true)) {
            fail(driver, COMP_SSD1681_WBA_ERROR_TRANSPORT);
        } else {
            driver->deadline_ms = now + RESET_HOLD_MS;
#if COMP_V11_PANEL_VENDOR_QUICK_FULL
            if (driver->operation == OP_VENDOR_QUICK_FULL && !driver->normalize_previous)
                driver->deadline_ms = now + 100u; /* Supplier LUT initializer. */
#endif
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
#if COMP_V11_PANEL_VENDOR_QUICK_FULL
            if (driver->operation == OP_VENDOR_QUICK_FULL && !driver->normalize_previous)
                driver->deadline_ms = now + 100u;
#endif
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
#if COMP_V11_PANEL_VENDOR_QUICK_FULL
            if (driver->operation == OP_VENDOR_QUICK_FULL && driver->normalize_previous) {
                /* This is the hardware-reset tail. The explicit software
                 * path restores OTP directly after the visible C7, without
                 * another parameter reset against a just-settled image. */
                set_sequence(driver, SEQ_RECOVER_MODE2_SETUP);
            } else
#endif
            if (mode1_operation(driver)) {
                driver->stage = ST_SOFTWARE_RESET;
            } else if (driver->mode2_rearm_pending) {
                /* Includes recording CF, which does not load OTP itself.
                 * Keep the requested immutable pair locked while B9 and
                 * its normal settle/ready gate run before any RAM write. */
                set_sequence(driver, SEQ_RECOVER_MODE2_SETUP);
            } else if (driver->operation == OP_RECORDING) {
                driver->scan_offset=0u;
                driver->recording_dirty_bounds=(comp_ssd1681_wba_window_t){24u,0u,199u,0u};
                driver->stage=ST_RECORDING_BOUNDS;
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
            set_sequence(driver, driver->activation_repairing ?
                         SEQ_RECOVER_MODE2_SETUP : SEQ_MODE1_TEMP);
#if COMP_V11_PANEL_VENDOR_QUICK_FULL
            if (driver->operation == OP_VENDOR_QUICK_FULL)
                set_sequence(driver, driver->normalize_previous?
                    SEQ_RECOVER_MODE2_SETUP:SEQ_VENDOR_FULL_SETUP);
#endif
        } else if (time_reached(now, driver->deadline_ms)) {
            fail(driver, COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT);
        }
        break;
    case ST_RECORDING_BOUNDS:
        poll_recording_bounds(driver);
        break;
    case ST_RECORDING_SCAN:
        poll_recording_run(driver);
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
#if COMP_V11_PANEL_VENDOR_QUICK_FULL
    case ST_VENDOR_LUT:
        /* The supplier sends one byte per CS packet. Yield after every
         * byte and retain the common stable-ready/deadline guard, rather
         * than blocking audio for the entire 153-byte LUT transfer. */
        if (driver->data_command_sent == 0u) {
            if (send_command(driver, 0x32u)) driver->data_command_sent = 1u;
        } else if (driver->data_x < 153u) {
            if (send_bytes(driver, true, &k_vendor_quick_lut[driver->data_x], 1u))
                driver->data_x++;
        } else {
            driver->recording_phase = RECORDING_PHASE_CURRENT;
            set_sequence(driver, SEQ_VENDOR_CURSOR);
        }
        break;
#endif
    case ST_WAIT_VISIBLE:
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
                break;
            }
            /* Record BUSY-qualified visibility separately from the later RAM-sync
             * completion. Buffers and baseline remain locked until that sync
             * (and full-update Mode2 rearm) also succeed. */
            /* Keep the ready veto armed through the post-refresh RAM sync.
             * Completion/failure/cancel release it after the final write. */
            driver->stats.last_visible_completed_ms = now;
            driver->stats.last_visible_wait_ms = now - driver->wait_started_ms;
#if COMP_V11_PANEL_VENDOR_QUICK_FULL
            if (driver->operation == OP_VENDOR_QUICK_FULL) {
                /* Isolate the still-open white-to-gray defect: leave the
                 * just-visible software-bound C7 LUT untouched while idle.
                 * Synchronize both RAM planes now, but defer OTP/B9 to the
                 * next actual Mode2 request. This is not optical proof or
                 * a reset substitute; hardware-reset restoration is intact. */
                driver->normalize_previous = true;
                if(driver->config.reset_mode == COMP_SSD1681_WBA_RESET_SOFTWARE_ONLY) {
                    driver->mode2_rearm_pending = true;
                    set_sequence(driver, SEQ_FULL_REBASE_CURRENT_WINDOW);
                } else driver->stage = ST_RESET_ASSERT;
            } else
#endif
            if (driver->operation == OP_FULL) {
                /* A successful F7 proves visibility, not the contents of the
                 * two RAM planes after the controller's Mode1 sequence.
                 * Match ordinary partial completion: explicitly normalize
                 * CURRENT24 and OLD26 to the same immutable full target before
                 * B9/another Mode2 activation. No second display activation,
                 * LUT or voltage change; each poll still writes one row.
                 * This repairs the baseline invariant, not optical proof. */
                set_sequence(driver, SEQ_FULL_REBASE_CURRENT_WINDOW);
            } else if (driver->operation == OP_RECORDING && !driver->activation_repairing) {
                driver->recording_phase = RECORDING_PHASE_POST_CURRENT;
                driver->recording_ordinary_region = 0u;
                driver->scan_offset = 0u;
                start_next_recording_run(driver);
            } else if (paired_mode2(driver)) {
#if COMP_V11_PANEL_PASSIVE_TRACE
                if(driver->activation_repairing && driver->activation_retried)
                    driver->stats.recovery_ready_ms=now;
#endif
                if (driver->operation == OP_PARTIAL || driver->operation == OP_FAST)
                    driver->recording_window = driver->window;
                /* After a qualified Mode2 baseline, rewrite both RAM planes
                 * over the SAME byte window staged before this activation.
                 * start_mode2 checked that all changes are contained there;
                 * outside it, the complete old/new images are identical.
                 * This follows the local write/refresh/write-again topology
                 * of GxEPD2_154_D67, while retaining our FF, separate CS, row
                 * cadence, BUSY gate and current24/current26 order. It is RAM
                 * transfer reduction, not a smaller electrical scan or an
                 * optical qualification. Keep full normalization on the
                 * FIRST Mode2 after F7, fast baselines, and recovery; capture
                 * uses its existing sparse branch above. */
                if (driver->operation != OP_PARTIAL ||
                    driver->stats.mode2_since_full == 0u ||
                    driver->activation_repairing)
                    driver->window = (comp_ssd1681_wba_window_t){0u,24u,0u,199u};
                prepare_window(driver);
                driver->recording_phase = RECORDING_PHASE_POST_CURRENT;
                set_sequence(driver, SEQ_PARTIAL_WINDOW);
            } else {
                complete_operation(driver);
            }
        } else if (time_reached(
                       now,
                       driver->wait_started_ms + REFRESH_START_TIMEOUT_MS)) {
            if (!driver->activation_retry_checked) {
                driver->activation_retry_checked = true;
                driver->stats.activation_start_misses++;
#if COMP_V11_PANEL_PASSIVE_TRACE
                driver->stats.missed_started_ms=driver->wait_started_ms;
                driver->stats.missed_at_ms=now;
                driver->stats.missed_poll_samples=driver->stats.visible_poll_samples;
                driver->stats.missed_high_samples=driver->stats.visible_high_samples;
                driver->stats.missed_edge_flags=driver->stats.visible_edge_flags;
                driver->stats.missed_max_poll_gap_ms=driver->stats.visible_max_poll_gap_ms;
                driver->stats.missed_window=driver->window;
                driver->stats.missed_operation=driver->operation;
                driver->stats.missed_phase=driver->recording_phase;
                driver->stats.recovery_reset_ms=0u;
                driver->stats.recovery_profile_ms=0u;
                driver->stats.recovery_activation_ms=0u;
                driver->stats.recovery_ready_ms=0u;
#endif
                if ((driver->operation == OP_PARTIAL || driver->operation == OP_FAST ||
                     driver->operation == OP_RECORDING) &&
                    driver->previous_frame != NULL &&
                    !time_reached(now, driver->deadline_ms) &&
                    driver->config.allow_mode2_recovery != NULL &&
                    driver->config.allow_mode2_recovery(driver->config.context)) {
                    driver->activation_deadline_ms = driver->deadline_ms;
                    driver->activation_repairing = true;
                    driver->stage = ST_RECOVER_MODE2_RESET;
                    break;
                }
            }
            /* The 100ms missed-start marker is not the transaction deadline
             * for ANY activation. If the one existing Mode2 recovery has
             * been used or is not admitted, retain the immutable pair and
             * observe the current activation until its already armed limit.
             * Recovery keeps that original limit; never grant a new one.
             * This waiting branch sends no reset, RAM or extra activation.
             * Only sampled BUSY high -> stable low can advance visibility;
             * an absent BUSY at the real deadline fails without a commit. */
            if (!time_reached(now, driver->deadline_ms)) break;
            fail(driver, COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT);
        } else if (time_reached(now, driver->deadline_ms)) {
            fail(driver, COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT);
        }
        break;
    case ST_RECOVER_MODE2_RESET:
        if (busy) {
            /* A late original activation wins before any reset is sent. */
            const uint32_t start_wait = now - driver->wait_started_ms;
            if (start_wait > driver->stats.max_start_wait_ms)
                driver->stats.max_start_wait_ms = start_wait;
            if (start_wait >= REFRESH_START_TIMEOUT_MS) driver->stats.delayed_starts++;
            driver->busy_observed = true;
            driver->ready_candidate = false;
            driver->activation_repairing = false;
            driver->stage = ST_WAIT_VISIBLE;
        } else if (time_reached(now, driver->deadline_ms) ||
                   driver->config.allow_mode2_recovery == NULL ||
                   !driver->config.allow_mode2_recovery(driver->config.context)) {
            fail(driver, COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT);
        } else if (send_command(driver, 0x12u)) {
            /* The shared entry guard has qualified sampled stable-ready.
             * Keep the original activation deadline and single retry. */
            driver->activation_retried = true;
            driver->stats.activation_retries++;
            driver->activation_gate_next_ms = now_ms(driver);
#if COMP_V11_PANEL_PASSIVE_TRACE
            driver->stats.recovery_reset_ms=driver->activation_gate_next_ms;
#endif
            /* Software reset preserves RAM, but rebuild both complete planes
             * from the immutable last-committed/current frames so no stale
             * outside-window comparison can create extra marks. CF/FF keeps
             * the differential waveform; this is not a Mode1 flash update. */
            driver->window = (comp_ssd1681_wba_window_t){0u,24u,0u,199u};
            prepare_window(driver);
            driver->recording_phase = RECORDING_PHASE_OLD;
            arm_busy_wait(driver, ST_WAIT_SOFTWARE_RESET);
        }
        break;
    case ST_WAIT_REARM:
        if (time_reached(now, driver->wait_started_ms + MODE2_REARM_SETTLE_MS) &&
            stable_ready(driver, now, busy)) {
            if (driver->activation_repairing) {
#if COMP_V11_PANEL_PASSIVE_TRACE
                driver->stats.recovery_profile_ms=now;
#endif
                set_sequence(driver, SEQ_PARTIAL_WINDOW);
            }
#if COMP_V11_PANEL_VENDOR_QUICK_FULL
            else if (driver->operation == OP_VENDOR_QUICK_FULL) {
                set_sequence(driver, SEQ_FULL_REBASE_CURRENT_WINDOW);
            }
#endif
            else if (driver->mode2_rearm_pending) {
                driver->mode2_rearm_pending = false;
                if (driver->operation == OP_RECORDING)
                    start_next_recording_run(driver);
                else set_sequence(driver, SEQ_PARTIAL_WINDOW);
            }
            else complete_operation(driver);
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

bool comp_ssd1681_wba_recording_active(const comp_ssd1681_wba_t *driver)
{
    return driver != NULL && driver->status == COMP_SSD1681_WBA_ACTIVE &&
           driver->operation == OP_RECORDING;
}

bool comp_ssd1681_wba_ram_write_pending(const comp_ssd1681_wba_t *driver)
{
    return driver != NULL && driver->status == COMP_SSD1681_WBA_ACTIVE &&
           driver->stage == ST_DATA;
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
    stop_busy_edges(driver);
    driver->ready_candidate = false;
    driver->error = COMP_SSD1681_WBA_ERROR_CANCELLED;
    driver->stats.cancellations++;
}

comp_ssd1681_wba_status_t comp_ssd1681_wba_status(
    const comp_ssd1681_wba_t *driver)
{
    return driver == NULL ? COMP_SSD1681_WBA_NOT_READY : driver->status;
}

bool comp_ssd1681_wba_recovery_ready(const comp_ssd1681_wba_t *driver)
{
    /* A fresh high vetoes a cached quiet interval. A fresh low cannot create
     * one: only ERROR polls advance the sampled filter. Calling this from a
     * diagnostic snapshot therefore cannot arm EXTI or admit a single low. */
    return driver != NULL && driver->status == COMP_SSD1681_WBA_ERROR &&
        driver->ready_candidate &&
        !driver->config.is_busy(driver->config.context) &&
        time_reached(now_ms(driver), driver->ready_started_ms + BUSY_READY_STABLE_MS);
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
