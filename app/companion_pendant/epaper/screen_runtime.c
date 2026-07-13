#include "screen_runtime.h"

#include <string.h>

void comp_epaper_screen_runtime_snapshot(
    const comp_epaper_expression_state_t *expression_state,
    const comp_epaper_display_queue_t *display_queue,
    const comp_epaper_panel_adapter_t *panel_adapter,
    comp_epaper_screen_runtime_snapshot_t *out_snapshot)
{
    if (out_snapshot == NULL) {
        return;
    }

    memset(out_snapshot, 0, sizeof(*out_snapshot));
    comp_epaper_expression_state_snapshot(expression_state,
                                          &out_snapshot->expression);
    comp_epaper_display_queue_snapshot(display_queue,
                                       &out_snapshot->display_queue);
    comp_epaper_panel_adapter_snapshot(panel_adapter, &out_snapshot->panel);
}
