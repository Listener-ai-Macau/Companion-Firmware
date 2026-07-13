#ifndef COMPANION_EPAPER_SCREEN_RUNTIME_H
#define COMPANION_EPAPER_SCREEN_RUNTIME_H

#include "display_queue.h"
#include "expression_state.h"
#include "panel_adapter.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    comp_epaper_expression_state_snapshot_t expression;
    comp_epaper_display_queue_snapshot_t display_queue;
    comp_epaper_panel_adapter_snapshot_t panel;
} comp_epaper_screen_runtime_snapshot_t;

void comp_epaper_screen_runtime_snapshot(
    const comp_epaper_expression_state_t *expression_state,
    const comp_epaper_display_queue_t *display_queue,
    const comp_epaper_panel_adapter_t *panel_adapter,
    comp_epaper_screen_runtime_snapshot_t *out_snapshot);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_SCREEN_RUNTIME_H */
