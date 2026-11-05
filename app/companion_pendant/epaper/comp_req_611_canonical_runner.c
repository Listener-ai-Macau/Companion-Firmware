#include "comp_req_611_canonical_runner.h"

#include "expression_asset_source.h"
#include "expression_state.h"
#include "main.h"
#include "panel_adapter.h"
#include "panel_target_stm32wb.h"
#include "panel_target_stm32wb_ssd1681.h"

#include "../../../.cache/validation/comp-req-611-canonical-sync/generated/comp_req_611_canonical_frames.h"

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define COMP_REQ_611_WHITE_FRAME_INDEX COMP_REQ_611_FRAME_COUNT
#define COMP_REQ_611_REQUEST_BASE 0x61100000u
#define COMP_REQ_611_TRACE_RING_CAPACITY 64u

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
} comp_req_611_trace_record_t;

static comp_epaper_expression_asset_source_t s_source;
static comp_epaper_panel_adapter_t s_adapter;
static uint8_t s_white_frame[COMP_REQ_611_FRAME_BYTES];
static comp_req_611_trace_record_t
    s_trace_ring[COMP_REQ_611_TRACE_RING_CAPACITY];
static uint16_t s_next_frame;
static uint32_t s_next_due_ms;
static uint32_t s_cycle_count;
static uint16_t s_trace_ring_write;
static uint16_t s_trace_ring_count;
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

static void record_trace(uint16_t frame, uint16_t dwell_commits,
                         const companion_epaper_cached_mode2_report_t *report)
{
    comp_req_611_trace_record_t *record = &s_trace_ring[s_trace_ring_write];
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
    s_trace_ring_write =
        (uint16_t)((s_trace_ring_write + 1u) % COMP_REQ_611_TRACE_RING_CAPACITY);
    if (s_trace_ring_count < COMP_REQ_611_TRACE_RING_CAPACITY) {
        s_trace_ring_count++;
    }
}

static bool canonical_frame_provider(void *context, uint16_t frame_index,
                                     uint8_t *destination, size_t destination_size)
{
    (void)context;
    if (destination == NULL || destination_size < COMP_REQ_611_FRAME_BYTES) {
        return false;
    }
    if (frame_index < COMP_REQ_611_FRAME_COUNT) {
        /* Native payload bytes are copied unchanged: no redraw, inversion, or
         * lower-side feature remapping is allowed in this adapter. */
        memcpy(destination, comp_req_611_canonical_frames[frame_index],
               COMP_REQ_611_FRAME_BYTES);
        return true;
    }
    if (frame_index == COMP_REQ_611_WHITE_FRAME_INDEX) {
        memcpy(destination, s_white_frame, COMP_REQ_611_FRAME_BYTES);
        return true;
    }
    return false;
}

static void make_request(comp_epaper_display_request_t *request,
                         uint16_t frame_index,
                         comp_epaper_refresh_mode_t refresh_mode)
{
    memset(request, 0, sizeof(*request));
    request->request_id = COMP_REQ_611_REQUEST_BASE + frame_index;
    request->content_crc32 = COMP_REQ_611_REQUEST_BASE + frame_index;
    request->request_kind = (uint8_t)COMP_EPAPER_DISPLAY_REQUEST_EXPRESSION;
    request->expression = (uint8_t)COMP_EPAPER_EXPRESSION_IDLE;
    request->expression_signal = (uint8_t)COMP_EPAPER_EXPRESSION_SIGNAL_BOOT_IDLE;
    request->refresh_mode = (uint8_t)refresh_mode;
    request->asset_frame_valid = 1u;
    request->asset_frame_index = frame_index;
    request->dirty_width = 200u;
    request->dirty_height = 200u;
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
    result = companion_epaper_panel_stm32wb_ssd1681_comp_req_611_full_0xff(
        s_white_frame, sizeof(s_white_frame), &report);
    s_cleanup_done = true;
    printf("[comp-req-611] cleanup=single_fast_white reason=%s result=%u window=%u-%u,%u-%u bytes=%lu transaction_ms=%lu busy_ms=%lu control=0x%02X activation=%u source_reset=%u explicit_cleanup=%lu\r\n",
           reason == NULL ? "unknown" : reason, (unsigned)result,
           (unsigned)report.x_start_byte, (unsigned)report.x_end_byte,
           (unsigned)report.y_start, (unsigned)report.y_end,
           (unsigned long)report.transferred_bytes,
           (unsigned long)report.transaction_elapsed_ms,
           (unsigned long)report.busy_elapsed_ms,
           (unsigned)report.control, (unsigned)report.activation_count,
           (unsigned)report.source_reset_count,
           (unsigned long)s_explicit_cleanup_count);
    if (!result || report.control != 0xFFu || report.activation_count != 1u) {
        s_faulted = true;
        return false;
    }
    return true;
}

void comp_req_611_canonical_runner_init(void)
{
    memset(s_white_frame, 0xFF, sizeof(s_white_frame));
    s_next_frame = 0u;
    s_next_due_ms = HAL_GetTick();
    s_cycle_count = 0u;
    s_trace_ring_write = 0u;
    s_trace_ring_count = 0u;
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
        companion_epaper_panel_stm32wb_ssd1681_init(&s_adapter, &s_source);
        /* The ordinary panel init has a finite partial limit. This isolated
         * score owns cadence and must not inherit automatic maintenance flashes. */
        s_partial_limit_bound =
            companion_epaper_panel_stm32wb_set_temporary_partial_limit(UINT8_MAX);
    }
    printf("[comp-req-611] init=%u partial_limit=%u bound=%u baseline_full_expected=1 auto_maintenance=0 explicit_cleanup=1 pixel_format=row_major_msb_first_1_is_white frames=%u bytes=%u cadence_ms=%u page_sha256=3B9C4B2D0D16964DBD64A68B804AA6AB3404237539F44C21F3FEFD0B32A1AA22 payload_sha256=5411FB50BC61BF3DC73EB7D0746C6C0E4DB56F7D552B6796BB3B7F6ED59AD5AD\r\n",
           s_initialized ? 1u : 0u, (unsigned)UINT8_MAX,
           s_partial_limit_bound ? 1u : 0u,
           (unsigned)COMP_REQ_611_FRAME_COUNT,
           (unsigned)COMP_REQ_611_FRAME_BYTES,
           (unsigned)COMP_REQ_611_FRAME_CADENCE_MS);
    if (!s_initialized || !s_partial_limit_bound) {
        s_faulted = true;
    }
}

bool comp_req_611_canonical_runner_service(void)
{
    companion_epaper_cached_mode2_report_t mode2_report;
    bool result;
    uint32_t now;
    uint32_t start_ms;
    uint32_t dwell_ms;

    if (!s_initialized || s_faulted || s_cleanup_done) {
        return false;
    }
    if (s_stop_requested) {
        s_complete = true;
        return cleanup_white("operator_stop");
    }
    now = HAL_GetTick();
    if ((int32_t)(now - s_next_due_ms) < 0) {
        /* This is the dwell gate: no request and no refresh are issued. */
        return false;
    }

    start_ms = now;
    memset(&mode2_report, 0, sizeof(mode2_report));
    if (!s_started) {
        result = companion_epaper_panel_stm32wb_ssd1681_comp_req_611_full_0xff(
            comp_req_611_canonical_frames[s_next_frame],
            COMP_REQ_611_FRAME_BYTES, &mode2_report);
    } else {
        const uint16_t previous_frame =
            (uint16_t)((s_next_frame + COMP_REQ_611_FRAME_COUNT - 1u) %
                       COMP_REQ_611_FRAME_COUNT);
        result = companion_epaper_panel_stm32wb_ssd1681_cached_mode2_diff(
                     comp_req_611_canonical_frames[previous_frame],
                     comp_req_611_canonical_frames[s_next_frame],
                     COMP_REQ_611_FRAME_BYTES, false, &mode2_report)
                      ? true
                      : false;
    }
    dwell_ms = (uint32_t)comp_req_611_dwell_commits[s_next_frame] *
               COMP_REQ_611_FRAME_CADENCE_MS;
    if (s_cycle_count == 0u || s_started) {
        printf("[comp-req-611] frame=%u id=%s sha256=%s order=%u dwell_commits=%u dwell_ms=%lu window=%u-%u,%u-%u changed=%u bytes=%lu transaction_ms=%lu busy_ms=%lu control=0x%02X activation=%u source_reset=%u result=%u transport=%s\r\n",
               (unsigned)s_next_frame, comp_req_611_frame_ids[s_next_frame],
               comp_req_611_frame_sha256[s_next_frame], (unsigned)s_next_frame,
               (unsigned)comp_req_611_dwell_commits[s_next_frame],
               (unsigned long)dwell_ms,
               (unsigned)mode2_report.x_start_byte,
               (unsigned)mode2_report.x_end_byte,
               (unsigned)mode2_report.y_start,
               (unsigned)mode2_report.y_end,
               mode2_report.changed ? 1u : 0u,
               (unsigned long)mode2_report.transferred_bytes,
               (unsigned long)mode2_report.transaction_elapsed_ms,
               (unsigned long)mode2_report.busy_elapsed_ms,
               (unsigned)mode2_report.control,
               (unsigned)mode2_report.activation_count,
               (unsigned)mode2_report.source_reset_count,
               result ? 0u : 1u,
               s_started ? "cached_mode2_0xcf_dynamic_diff" : "baseline_full_0xff");
    }
    if (!result) {
        s_faulted = true;
        (void)cleanup_white("frame_fault");
        return false;
    }
    if (s_started) {
        s_normal_partial_count++;
    } else {
        s_baseline_full_count++;
    }
    record_trace(s_next_frame, comp_req_611_dwell_commits[s_next_frame],
                 &mode2_report);
    s_started = true;
    s_next_frame++;
    if (s_next_frame == COMP_REQ_611_FRAME_COUNT) {
        s_next_frame = 0u;
        s_cycle_count++;
        if (!s_complete) {
            s_complete = true;
            printf("[comp-req-611] observation_ready cycles=%lu frames=%u baseline_full=%lu normal_partial=%lu auto_maintenance=%lu explicit_cleanup=%lu ring_capacity=%u ring_count=%u continue=1\r\n",
                   (unsigned long)s_cycle_count,
                   (unsigned)COMP_REQ_611_FRAME_COUNT,
                   (unsigned long)s_baseline_full_count,
                   (unsigned long)s_normal_partial_count,
                   (unsigned long)s_auto_maintenance_count,
                   (unsigned long)s_explicit_cleanup_count,
                   (unsigned)COMP_REQ_611_TRACE_RING_CAPACITY,
                   (unsigned)s_trace_ring_count);
        }
    }
    s_next_due_ms = start_ms + dwell_ms;
    return true;
}

bool comp_req_611_canonical_runner_is_complete(void) { return s_complete; }
bool comp_req_611_canonical_runner_faulted(void) { return s_faulted; }
void comp_req_611_canonical_runner_request_stop(void) { s_stop_requested = true; }

bool comp_req_611_canonical_runner_accept_host_byte(uint8_t byte)
{
    static const char command[] = "COMP_REQ_611_STOP";
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
            comp_req_611_canonical_runner_request_stop();
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
