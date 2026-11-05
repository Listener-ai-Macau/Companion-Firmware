#include "comp_req_609_canonical_runner.h"

#include "expression_asset_source.h"
#include "expression_state.h"
#include "main.h"
#include "panel_adapter.h"
#include "panel_target_stm32wb_ssd1681.h"

#include "../../../.cache/validation/comp-req-609-canonical-sync/generated/comp_req_609_canonical_frames.h"

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define COMP_REQ_609_WHITE_FRAME_INDEX COMP_REQ_609_FRAME_COUNT
#define COMP_REQ_609_REQUEST_BASE 0x60900000u

static comp_epaper_expression_asset_source_t s_source;
static comp_epaper_panel_adapter_t s_adapter;
static uint8_t s_white_frame[COMP_REQ_609_FRAME_BYTES];
static uint16_t s_next_frame;
static uint32_t s_next_due_ms;
static bool s_initialized;
static bool s_started;
static bool s_cleanup_done;
static bool s_complete;
static bool s_faulted;

static bool canonical_frame_provider(void *context, uint16_t frame_index,
                                     uint8_t *destination, size_t destination_size)
{
    (void)context;
    if (destination == NULL || destination_size < COMP_REQ_609_FRAME_BYTES) {
        return false;
    }
    if (frame_index < COMP_REQ_609_FRAME_COUNT) {
        memcpy(destination, comp_req_609_canonical_frames[frame_index],
               COMP_REQ_609_FRAME_BYTES);
        return true;
    }
    if (frame_index == COMP_REQ_609_WHITE_FRAME_INDEX) {
        memcpy(destination, s_white_frame, COMP_REQ_609_FRAME_BYTES);
        return true;
    }
    return false;
}

static void make_request(comp_epaper_display_request_t *request,
                         uint16_t frame_index,
                         comp_epaper_refresh_mode_t refresh_mode)
{
    memset(request, 0, sizeof(*request));
    request->request_id = COMP_REQ_609_REQUEST_BASE + frame_index;
    request->content_crc32 = COMP_REQ_609_REQUEST_BASE + frame_index;
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
    comp_epaper_display_request_t request;
    comp_epaper_panel_report_t report;
    comp_epaper_panel_result_t result;
    if (s_cleanup_done) {
        return !s_faulted;
    }
    make_request(&request, COMP_REQ_609_WHITE_FRAME_INDEX,
                 COMP_EPAPER_REFRESH_MAINTENANCE);
    result = comp_epaper_panel_adapter_refresh_card(&s_adapter, &request, &report);
    s_cleanup_done = true;
    printf("[comp-req-609] cleanup=single_fast_white reason=%s result=%u bytes=%lu attempts=%lu\r\n",
           reason == NULL ? "unknown" : reason, (unsigned)result,
           (unsigned long)report.transferred_bytes,
           (unsigned long)report.adapter_attempts);
    if (result != COMP_EPAPER_PANEL_RESULT_OK) {
        s_faulted = true;
        return false;
    }
    return true;
}

void comp_req_609_canonical_runner_init(void)
{
    memset(s_white_frame, 0xFF, sizeof(s_white_frame));
    s_next_frame = 0u;
    s_next_due_ms = HAL_GetTick();
    s_started = false;
    s_cleanup_done = false;
    s_complete = false;
    s_faulted = false;
    s_initialized = comp_epaper_expression_asset_source_init_frame_provider(
        &s_source, canonical_frame_provider, NULL);
    if (s_initialized) {
        companion_epaper_panel_stm32wb_ssd1681_init(&s_adapter, &s_source);
    }
    printf("[comp-req-609] init=%u source=canonical_frame_provider frames=%u bytes=%u cadence_ms=%u page_sha256=B47FC91BCFC7F746012CCFCE4DDF50C34215347A4944E63FA9A348A0901FC5FF payload_sha256=5C0D18DB7F7A9452309475D3DEE3AE1412ABA385946BF333C7A0CB0F0DBB0E07\r\n",
           s_initialized ? 1u : 0u, (unsigned)COMP_REQ_609_FRAME_COUNT,
           (unsigned)COMP_REQ_609_FRAME_BYTES,
           (unsigned)COMP_REQ_609_FRAME_CADENCE_MS);
    if (!s_initialized) {
        s_faulted = true;
    }
}

bool comp_req_609_canonical_runner_service(void)
{
    comp_epaper_display_request_t request;
    comp_epaper_panel_report_t report;
    comp_epaper_panel_result_t result;
    uint32_t now;
    uint32_t start_ms;
    if (!s_initialized || s_faulted || s_complete) {
        return false;
    }
    now = HAL_GetTick();
    if ((int32_t)(now - s_next_due_ms) < 0) {
        return false;
    }
    start_ms = now;
    make_request(&request, s_next_frame,
                 s_started ? COMP_EPAPER_REFRESH_PARTIAL : COMP_EPAPER_REFRESH_FULL);
    result = comp_epaper_panel_adapter_refresh_card(&s_adapter, &request, &report);
    printf("[comp-req-609] frame=%u id=%s sha256=%s order=%u dwell_commits=1 cadence_ms=%u elapsed_ms=%lu result=%u bytes=%lu\r\n",
           (unsigned)s_next_frame, comp_req_609_frame_ids[s_next_frame],
           comp_req_609_frame_sha256[s_next_frame], (unsigned)s_next_frame,
           (unsigned)COMP_REQ_609_FRAME_CADENCE_MS,
           (unsigned long)(HAL_GetTick() - start_ms), (unsigned)result,
           (unsigned long)report.transferred_bytes);
    if (result != COMP_EPAPER_PANEL_RESULT_OK) {
        s_faulted = true;
        (void)cleanup_white("frame_fault");
        return false;
    }
    s_started = true;
    s_next_frame++;
    s_next_due_ms = start_ms + COMP_REQ_609_FRAME_CADENCE_MS;
    if (s_next_frame == COMP_REQ_609_FRAME_COUNT) {
        (void)cleanup_white("replay_exit");
        s_complete = !s_faulted;
    }
    return true;
}

bool comp_req_609_canonical_runner_is_complete(void) { return s_complete; }
bool comp_req_609_canonical_runner_faulted(void) { return s_faulted; }
