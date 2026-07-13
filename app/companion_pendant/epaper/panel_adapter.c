#include "panel_adapter.h"

#include <string.h>

static const comp_epaper_panel_config_t k_dry_run_config = {
    .hardware_present = false,
    .controller_known = false,
    .width = 0u,
    .height = 0u,
    .controller_name = "unconfigured",
    .refresh = NULL,
    .context = NULL,
};

void comp_epaper_panel_adapter_init(comp_epaper_panel_adapter_t *adapter,
                                    const comp_epaper_panel_config_t *config)
{
    if (adapter == NULL) {
        return;
    }
    memset(adapter, 0, sizeof(*adapter));
    adapter->config = config == NULL ? k_dry_run_config : *config;
    adapter->last_result = COMP_EPAPER_PANEL_RESULT_DEFERRED_NO_PANEL;
}

void comp_epaper_panel_adapter_init_dry_run(comp_epaper_panel_adapter_t *adapter)
{
    comp_epaper_panel_adapter_init(adapter, &k_dry_run_config);
}

comp_epaper_panel_result_t comp_epaper_panel_adapter_refresh_card(
    comp_epaper_panel_adapter_t *adapter,
    const comp_epaper_display_request_t *request,
    comp_epaper_panel_report_t *out_report)
{
    comp_epaper_panel_result_t result = COMP_EPAPER_PANEL_RESULT_BAD_ARGUMENT;
    comp_epaper_panel_report_t target_report;

    if (out_report != NULL) {
        memset(out_report, 0, sizeof(*out_report));
    }
    memset(&target_report, 0, sizeof(target_report));
    if (adapter == NULL || request == NULL) {
        if (adapter != NULL) {
            adapter->last_result = result;
            adapter->last_result_valid = true;
        }
        if (out_report != NULL) {
            out_report->result = result;
        }
        return result;
    }

    adapter->attempted_count++;
    if (!adapter->config.hardware_present) {
        result = COMP_EPAPER_PANEL_RESULT_DEFERRED_NO_PANEL;
        adapter->deferred_count++;
    } else if (!adapter->config.controller_known ||
               adapter->config.width == 0u ||
               adapter->config.height == 0u) {
        result = COMP_EPAPER_PANEL_RESULT_DEFERRED_CONTROLLER_UNKNOWN;
        adapter->deferred_count++;
    } else if (adapter->config.refresh == NULL) {
        result = COMP_EPAPER_PANEL_RESULT_TRANSPORT_ERROR;
        adapter->error_count++;
    } else {
        result = adapter->config.refresh(adapter->config.context,
                                         request,
                                         &target_report);
        if (result == COMP_EPAPER_PANEL_RESULT_OK) {
            adapter->rendered_count++;
        } else if (result == COMP_EPAPER_PANEL_RESULT_DEFERRED_NO_PANEL ||
                   result == COMP_EPAPER_PANEL_RESULT_DEFERRED_CONTROLLER_UNKNOWN) {
            adapter->deferred_count++;
        } else if (result != COMP_EPAPER_PANEL_RESULT_BUSY) {
            adapter->error_count++;
        }
    }
    adapter->last_result = result;
    adapter->last_result_valid = true;

    if (out_report != NULL) {
        *out_report = target_report;
        out_report->result = result;
        out_report->request_id = request->request_id;
        out_report->content_crc32 = request->content_crc32;
        if (result != COMP_EPAPER_PANEL_RESULT_OK) {
            out_report->transferred_bytes = 0u;
        } else if (out_report->transferred_bytes == 0u) {
            out_report->transferred_bytes = (uint32_t)request->payload_len;
        }
        out_report->adapter_attempts = adapter->attempted_count;
        out_report->width = adapter->config.width;
        out_report->height = adapter->config.height;
    }
    return result;
}

uint8_t comp_epaper_panel_adapter_render_state(comp_epaper_panel_result_t result)
{
    switch (result) {
    case COMP_EPAPER_PANEL_RESULT_OK:
        return (uint8_t)COMP_EPAPER_RENDER_STATE_RENDERED;
    case COMP_EPAPER_PANEL_RESULT_BUSY:
        return (uint8_t)COMP_EPAPER_RENDER_STATE_BUSY;
    case COMP_EPAPER_PANEL_RESULT_DEFERRED_NO_PANEL:
    case COMP_EPAPER_PANEL_RESULT_DEFERRED_CONTROLLER_UNKNOWN:
    case COMP_EPAPER_PANEL_RESULT_BAD_ARGUMENT:
    case COMP_EPAPER_PANEL_RESULT_TRANSPORT_ERROR:
    default:
        return (uint8_t)COMP_EPAPER_RENDER_STATE_FAILED;
    }
}

uint8_t comp_epaper_panel_adapter_status_error(comp_epaper_panel_result_t result)
{
    switch (result) {
    case COMP_EPAPER_PANEL_RESULT_OK:
        return 0u;
    case COMP_EPAPER_PANEL_RESULT_DEFERRED_NO_PANEL:
        return 4u;
    case COMP_EPAPER_PANEL_RESULT_DEFERRED_CONTROLLER_UNKNOWN:
        return 5u;
    case COMP_EPAPER_PANEL_RESULT_BAD_ARGUMENT:
        return 6u;
    case COMP_EPAPER_PANEL_RESULT_TRANSPORT_ERROR:
        return 7u;
    case COMP_EPAPER_PANEL_RESULT_BUSY:
        return 8u;
    default:
        return 0x7Fu;
    }
}

void comp_epaper_panel_adapter_snapshot(const comp_epaper_panel_adapter_t *adapter,
                                        comp_epaper_panel_adapter_snapshot_t *out_snapshot)
{
    if (out_snapshot == NULL) {
        return;
    }

    memset(out_snapshot, 0, sizeof(*out_snapshot));
    if (adapter == NULL) {
        return;
    }

    out_snapshot->hardware_present = adapter->config.hardware_present;
    out_snapshot->controller_known = adapter->config.controller_known;
    out_snapshot->refresh_configured = adapter->config.refresh != NULL;
    out_snapshot->last_result_valid = adapter->last_result_valid;
    out_snapshot->width = adapter->config.width;
    out_snapshot->height = adapter->config.height;
    out_snapshot->attempted_count = adapter->attempted_count;
    out_snapshot->rendered_count = adapter->rendered_count;
    out_snapshot->deferred_count = adapter->deferred_count;
    out_snapshot->error_count = adapter->error_count;
    out_snapshot->last_result = adapter->last_result;
}
