#include "comp_req_616_canonical_runner.h"

#include "expression_asset_source.h"
#include "main.h"
#include "panel_adapter.h"
#include "panel_target_stm32wb.h"
#include "panel_target_stm32wb_ssd1681.h"

#include "../../../.cache/validation/comp-req-616-upper-sync/generated/comp_req_616_canonical_frames.h"

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define COMP_REQ_616_TRACE_RING_CAPACITY 64u
#define COMP_REQ_616_REQUEST_BASE 0x61600000u

typedef struct {
    uint32_t cycle;
    uint16_t frame;
    uint16_t dwell_commits;
    uint32_t transferred_bytes;
    uint8_t x_start_byte;
    uint8_t x_end_byte;
    uint16_t y_start;
    uint16_t y_end;
    uint32_t transaction_elapsed_ms;
    uint32_t busy_elapsed_ms;
    uint8_t control;
    uint8_t activation_count;
    uint8_t source_reset_count;
} comp_req_616_trace_record_t;

static comp_epaper_expression_asset_source_t s_source;
static comp_epaper_panel_adapter_t s_adapter;
/* The isolated score needs two 5000-byte working frames.  Keep one in the
 * unused tail of the existing BLE shared mailbox so the default production
 * image's RAM1 budget remains unchanged; this path is opt-in and diagnostic.
 */
static uint8_t s_previous_frame[COMP_REQ_616_FRAME_BYTES]
    __attribute__((section("MB_MEM2"), aligned(4)));
static uint8_t s_current_frame[COMP_REQ_616_FRAME_BYTES];
static comp_req_616_trace_record_t s_trace_ring[COMP_REQ_616_TRACE_RING_CAPACITY];
static uint16_t s_next_frame;
static uint32_t s_next_due_ms;
static uint32_t s_cycle_count;
static uint16_t s_trace_ring_write;
static uint16_t s_trace_ring_count;
static size_t s_packed_offset;
static size_t s_decoded_bytes;
static bool s_initialized;
static bool s_started;
static bool s_cleanup_done;
static bool s_complete;
static bool s_faulted;
static bool s_stop_requested;
static bool s_partial_limit_bound;
static uint32_t s_baseline_full_count;
static uint32_t s_normal_partial_count;
static uint32_t s_auto_maintenance_count;
static uint32_t s_explicit_cleanup_count;
static char s_host_stop_command[20];
static uint8_t s_host_stop_command_length;

static bool decode_frame_from(size_t *packed_offset, uint8_t *destination)
{
    size_t output = 0u;
    if (destination == NULL) {
        return false;
    }
    while (output < COMP_REQ_616_FRAME_BYTES) {
        uint8_t control;
        size_t length;
        if (packed_offset == NULL || *packed_offset >= COMP_REQ_616_COMPRESSED_BYTES) {
            return false;
        }
        control = comp_req_616_packed_payload[(*packed_offset)++];
        length = (size_t)(control & 0x7Fu) + 1u;
        if ((control & 0x80u) != 0u) {
            uint8_t value;
            if (*packed_offset >= COMP_REQ_616_COMPRESSED_BYTES ||
                output + length > COMP_REQ_616_FRAME_BYTES) {
                return false;
            }
            value = comp_req_616_packed_payload[(*packed_offset)++];
            memset(&destination[output], value, length);
            output += length;
        } else {
            if (*packed_offset + length > COMP_REQ_616_COMPRESSED_BYTES ||
                output + length > COMP_REQ_616_FRAME_BYTES) {
                return false;
            }
            memcpy(&destination[output],
                   &comp_req_616_packed_payload[*packed_offset], length);
            *packed_offset += length;
            output += length;
        }
    }
    return output == COMP_REQ_616_FRAME_BYTES;
}

static bool decode_next_frame(uint8_t *destination)
{
    const bool result = decode_frame_from(&s_packed_offset, destination);
    if (result) {
        s_decoded_bytes += COMP_REQ_616_FRAME_BYTES;
    }
    return result;
}

static void record_trace(uint16_t frame, uint16_t dwell_commits,
                         const companion_epaper_cached_mode2_report_t *report)
{
    comp_req_616_trace_record_t *record = &s_trace_ring[s_trace_ring_write];
    record->cycle = s_cycle_count;
    record->frame = frame;
    record->dwell_commits = dwell_commits;
    record->transferred_bytes = report == NULL ? 0u : report->transferred_bytes;
    record->x_start_byte = report == NULL ? 0u : report->x_start_byte;
    record->x_end_byte = report == NULL ? 0u : report->x_end_byte;
    record->y_start = report == NULL ? 0u : report->y_start;
    record->y_end = report == NULL ? 0u : report->y_end;
    record->transaction_elapsed_ms =
        report == NULL ? 0u : report->transaction_elapsed_ms;
    record->busy_elapsed_ms = report == NULL ? 0u : report->busy_elapsed_ms;
    record->control = report == NULL ? 0u : report->control;
    record->activation_count = report == NULL ? 0u : report->activation_count;
    record->source_reset_count = report == NULL ? 0u : report->source_reset_count;
    s_trace_ring_write = (uint16_t)((s_trace_ring_write + 1u) %
                                    COMP_REQ_616_TRACE_RING_CAPACITY);
    if (s_trace_ring_count < COMP_REQ_616_TRACE_RING_CAPACITY) {
        s_trace_ring_count++;
    }
}

static bool canonical_frame_provider(void *context, uint16_t frame_index,
                                     uint8_t *destination, size_t destination_size)
{
    uint8_t skipped[COMP_REQ_616_FRAME_BYTES];
    size_t cursor = 0u;
    uint16_t index;
    (void)context;
    if (destination == NULL || destination_size < COMP_REQ_616_FRAME_BYTES ||
        frame_index >= COMP_REQ_616_FRAME_COUNT) {
        return false;
    }
    for (index = 0u; index < frame_index; ++index) {
        if (!decode_frame_from(&cursor, skipped)) {
            return false;
        }
    }
    /* The isolated source is native row-major MSB-first 1=white. */
    return decode_frame_from(&cursor, destination);
}

static bool cleanup_white(const char *reason)
{
    companion_epaper_cached_mode2_report_t report;
    bool result;
    if (s_cleanup_done) {
        return !s_faulted;
    }
    s_explicit_cleanup_count++;
    memset(&report, 0, sizeof(report));
    memset(s_current_frame, 0xFF, sizeof(s_current_frame));
    result = companion_epaper_panel_stm32wb_ssd1681_comp_req_611_full_0xff(
        s_current_frame, sizeof(s_current_frame), &report);
    s_cleanup_done = true;
    printf("[comp-req-616] cleanup=single_fast_white reason=%s result=%u window=%u-%u,%u-%u bytes=%lu transaction_ms=%lu busy_ms=%lu control=0x%02X activation=%u source_reset=%u explicit_cleanup=%lu\r\n",
           reason == NULL ? "unknown" : reason, (unsigned)result,
           (unsigned)report.x_start_byte, (unsigned)report.x_end_byte,
           (unsigned)report.y_start, (unsigned)report.y_end,
           (unsigned long)report.transferred_bytes,
           (unsigned long)report.transaction_elapsed_ms,
           (unsigned long)report.busy_elapsed_ms, (unsigned)report.control,
           (unsigned)report.activation_count,
           (unsigned)report.source_reset_count,
           (unsigned long)s_explicit_cleanup_count);
    if (!result || report.control != 0xFFu || report.activation_count != 1u ||
        report.source_reset_count != 0u) {
        s_faulted = true;
        return false;
    }
    return true;
}

void comp_req_616_canonical_runner_init(void)
{
    memset(s_previous_frame, 0xFF, sizeof(s_previous_frame));
    memset(s_current_frame, 0xFF, sizeof(s_current_frame));
    s_next_frame = 0u;
    s_next_due_ms = HAL_GetTick();
    s_cycle_count = 0u;
    s_trace_ring_write = 0u;
    s_trace_ring_count = 0u;
    s_packed_offset = 0u;
    s_decoded_bytes = 0u;
    s_started = false;
    s_cleanup_done = false;
    s_complete = false;
    s_faulted = false;
    s_stop_requested = false;
    s_partial_limit_bound = false;
    s_baseline_full_count = 0u;
    s_normal_partial_count = 0u;
    s_auto_maintenance_count = 0u;
    s_explicit_cleanup_count = 0u;
    memset(s_host_stop_command, 0, sizeof(s_host_stop_command));
    s_host_stop_command_length = 0u;
    s_initialized = comp_epaper_expression_asset_source_init_frame_provider(
        &s_source, canonical_frame_provider, NULL);
    if (s_initialized) {
        const bool panel_prepared =
            companion_epaper_panel_stm32wb_ssd1681_comp_req_616_prepare();
        if (panel_prepared) {
            companion_epaper_panel_stm32wb_ssd1681_init(&s_adapter, &s_source);
            s_partial_limit_bound =
                companion_epaper_panel_stm32wb_set_temporary_partial_limit(UINT8_MAX);
        } else {
            s_initialized = false;
        }
    }
    printf("[comp-req-616] init=%u partial_limit=%u bound=%u baseline_full_expected=1 auto_maintenance=0 explicit_cleanup=1 pixel_format=row_major_msb_first_1_is_white frames=%u bytes=%u cadence_ms=%u page_sha256=ECCC8D27A31209150B9EEBF8AB25CEB08708B32BBA00541E033C8378E5B77E73 payload_sha256=087654306CFC0ECA07BEE9F270DAF72C0DB269E3CF39C6D4D6098BB96EA137DC packed_bytes=%u\r\n",
           s_initialized ? 1u : 0u, (unsigned)UINT8_MAX,
           s_partial_limit_bound ? 1u : 0u, (unsigned)COMP_REQ_616_FRAME_COUNT,
           (unsigned)COMP_REQ_616_FRAME_BYTES,
           (unsigned)COMP_REQ_616_FRAME_CADENCE_MS,
           (unsigned)COMP_REQ_616_COMPRESSED_BYTES);
    if (!s_initialized || !s_partial_limit_bound) {
        s_faulted = true;
    }
}

bool comp_req_616_canonical_runner_service(void)
{
    companion_epaper_cached_mode2_report_t report;
    bool result;
    uint32_t now;
    uint32_t start_ms;
    uint32_t dwell_ms;
#if COMPANION_EPAPER_SSD1681_COMP_REQ_616_CANONICAL_SYNC
    /* The COMP-REQ-621 local face re-white transfers 2772 bytes per frame;
     * its measured transaction remains inside the 480 ms frame cadence. */
    const uint32_t transaction_limit_ms = 480u;
#else
    const uint32_t transaction_limit_ms = s_next_frame == 0u ? 480u : 470u;
#endif

    if (!s_initialized || s_faulted || s_cleanup_done) {
        return false;
    }
    if (s_stop_requested) {
        s_complete = true;
        return cleanup_white("operator_stop");
    }
    now = HAL_GetTick();
    if ((int32_t)(now - s_next_due_ms) < 0) {
        return false;
    }
    start_ms = now;
    if (s_next_frame == 0u && s_cycle_count != 0u) {
        s_packed_offset = 0u;
        s_decoded_bytes = 0u;
    }
    if (!decode_next_frame(s_current_frame)) {
        s_faulted = true;
        (void)cleanup_white("decode_fault");
        return false;
    }
    memset(&report, 0, sizeof(report));
    if (!s_started) {
        result = companion_epaper_panel_stm32wb_ssd1681_comp_req_611_full_0xff(
            s_current_frame, sizeof(s_current_frame), &report);
    } else {
        result = companion_epaper_panel_stm32wb_ssd1681_cached_mode2_diff(
            s_previous_frame, s_current_frame, sizeof(s_current_frame), false,
            &report);
    }
    dwell_ms = (uint32_t)comp_req_616_dwell_commits[s_next_frame] *
               COMP_REQ_616_FRAME_CADENCE_MS;
    printf("[comp-req-616] frame=%u id=%s sha256=%s order=%u dwell_commits=%u dwell_ms=%lu window=%u-%u,%u-%u changed=%u bytes=%lu transaction_ms=%lu busy_ms=%lu control=0x%02X activation=%u source_reset=%u result=%u transport=%s\r\n",
           (unsigned)s_next_frame, comp_req_616_frame_ids[s_next_frame],
           comp_req_616_frame_sha256[s_next_frame], (unsigned)s_next_frame,
           (unsigned)comp_req_616_dwell_commits[s_next_frame],
           (unsigned long)dwell_ms, (unsigned)report.x_start_byte,
           (unsigned)report.x_end_byte, (unsigned)report.y_start,
           (unsigned)report.y_end, report.changed ? 1u : 0u,
           (unsigned long)report.transferred_bytes,
           (unsigned long)report.transaction_elapsed_ms,
           (unsigned long)report.busy_elapsed_ms, (unsigned)report.control,
           (unsigned)report.activation_count,
           (unsigned)report.source_reset_count, result ? 0u : 1u,
           s_started ? "cached_mode2_0xcf_face_rewhite" : "baseline_full_0xff");
    if (!result || report.source_reset_count != 0u ||
        report.activation_count != ((s_started && !report.changed) ? 0u : 1u) ||
        report.control != (s_started ? 0xCFu : 0xFFu) ||
        report.transaction_elapsed_ms > transaction_limit_ms || report.busy_elapsed_ms > 600u ||
        (!report.changed && (report.transferred_bytes != 0u ||
                             report.transaction_elapsed_ms != 0u ||
                             report.busy_elapsed_ms != 0u))) {
        s_faulted = true;
        (void)cleanup_white("frame_fault");
        return false;
    }
    if (s_started) {
        s_normal_partial_count++;
    } else {
        s_baseline_full_count++;
    }
    record_trace(s_next_frame, comp_req_616_dwell_commits[s_next_frame], &report);
    memcpy(s_previous_frame, s_current_frame, sizeof(s_previous_frame));
    s_started = true;
    s_next_frame++;
    if (s_next_frame == COMP_REQ_616_FRAME_COUNT) {
        s_next_frame = 0u;
        s_cycle_count++;
        if (!s_complete) {
            s_complete = true;
            printf("[comp-req-616] observation_ready cycles=%lu frames=%u baseline_full=%lu normal_partial=%lu auto_maintenance=%lu explicit_cleanup=%lu ring_capacity=%u ring_count=%u decoded_bytes=%lu continue=1\r\n",
                   (unsigned long)s_cycle_count, (unsigned)COMP_REQ_616_FRAME_COUNT,
                   (unsigned long)s_baseline_full_count,
                   (unsigned long)s_normal_partial_count,
                   (unsigned long)s_auto_maintenance_count,
                   (unsigned long)s_explicit_cleanup_count,
                   (unsigned)COMP_REQ_616_TRACE_RING_CAPACITY,
                   (unsigned)s_trace_ring_count, (unsigned long)s_decoded_bytes);
        }
    }
    s_next_due_ms = start_ms + dwell_ms;
    return true;
}

bool comp_req_616_canonical_runner_is_complete(void) { return s_complete; }
bool comp_req_616_canonical_runner_faulted(void) { return s_faulted; }
void comp_req_616_canonical_runner_request_stop(void) { s_stop_requested = true; }

bool comp_req_616_canonical_runner_accept_host_byte(uint8_t byte)
{
    static const char command[] = "COMP_REQ_616_STOP";
    if (byte == '\r') {
        return false;
    }
    if (byte == '\n') {
        const bool matched = s_host_stop_command_length == sizeof(command) - 1u &&
                             memcmp(s_host_stop_command, command,
                                    sizeof(command) - 1u) == 0;
        s_host_stop_command_length = 0u;
        memset(s_host_stop_command, 0, sizeof(s_host_stop_command));
        if (matched) {
            comp_req_616_canonical_runner_request_stop();
        }
        return matched;
    }
    if (s_host_stop_command_length >= sizeof(s_host_stop_command) - 1u) {
        s_host_stop_command_length = 0u;
        memset(s_host_stop_command, 0, sizeof(s_host_stop_command));
        return false;
    }
    s_host_stop_command[s_host_stop_command_length++] = (char)byte;
    return false;
}
