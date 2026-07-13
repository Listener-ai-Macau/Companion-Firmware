#ifndef COMPANION_EPAPER_PANEL_ADAPTER_H
#define COMPANION_EPAPER_PANEL_ADAPTER_H

#include "display_queue.h"

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    COMP_EPAPER_PANEL_RESULT_OK = 0,
    COMP_EPAPER_PANEL_RESULT_DEFERRED_NO_PANEL = 1,
    COMP_EPAPER_PANEL_RESULT_DEFERRED_CONTROLLER_UNKNOWN = 2,
    COMP_EPAPER_PANEL_RESULT_BAD_ARGUMENT = 3,
    COMP_EPAPER_PANEL_RESULT_TRANSPORT_ERROR = 4,
    COMP_EPAPER_PANEL_RESULT_BUSY = 5,
} comp_epaper_panel_result_t;

typedef struct {
    comp_epaper_panel_result_t result;
    uint32_t request_id;
    uint32_t content_crc32;
    uint32_t transferred_bytes;
    uint32_t adapter_attempts;
    uint16_t width;
    uint16_t height;
} comp_epaper_panel_report_t;

typedef comp_epaper_panel_result_t (*comp_epaper_panel_refresh_fn_t)(
    void *context,
    const comp_epaper_display_request_t *request,
    comp_epaper_panel_report_t *out_report);

typedef struct {
    bool hardware_present;
    bool controller_known;
    uint16_t width;
    uint16_t height;
    const char *controller_name;
    comp_epaper_panel_refresh_fn_t refresh;
    void *context;
} comp_epaper_panel_config_t;

typedef struct {
    comp_epaper_panel_config_t config;
    uint32_t attempted_count;
    uint32_t rendered_count;
    uint32_t deferred_count;
    uint32_t error_count;
    comp_epaper_panel_result_t last_result;
    bool last_result_valid;
} comp_epaper_panel_adapter_t;

typedef struct {
    bool hardware_present;
    bool controller_known;
    bool refresh_configured;
    bool last_result_valid;
    uint16_t width;
    uint16_t height;
    uint32_t attempted_count;
    uint32_t rendered_count;
    uint32_t deferred_count;
    uint32_t error_count;
    comp_epaper_panel_result_t last_result;
} comp_epaper_panel_adapter_snapshot_t;

void comp_epaper_panel_adapter_init(comp_epaper_panel_adapter_t *adapter,
                                    const comp_epaper_panel_config_t *config);
void comp_epaper_panel_adapter_init_dry_run(comp_epaper_panel_adapter_t *adapter);

comp_epaper_panel_result_t comp_epaper_panel_adapter_refresh_card(
    comp_epaper_panel_adapter_t *adapter,
    const comp_epaper_display_request_t *request,
    comp_epaper_panel_report_t *out_report);

uint8_t comp_epaper_panel_adapter_render_state(comp_epaper_panel_result_t result);
uint8_t comp_epaper_panel_adapter_status_error(comp_epaper_panel_result_t result);
void comp_epaper_panel_adapter_snapshot(const comp_epaper_panel_adapter_t *adapter,
                                        comp_epaper_panel_adapter_snapshot_t *out_snapshot);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_PANEL_ADAPTER_H */
