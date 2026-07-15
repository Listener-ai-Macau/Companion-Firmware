#ifndef COMPANION_EPAPER_MENU_V5_ACTION_JOURNEY_H
#define COMPANION_EPAPER_MENU_V5_ACTION_JOURNEY_H

#include <stdbool.h>
#include <stdint.h>

#include "menu_v5_contract.h"
#include "menu_v5_localization.h"
#include "pet_performance_event_bridge.h"

#ifdef __cplusplus
extern "C" {
#endif

/* This reports a committed menu decision. It deliberately does not start
 * recording, BLE work, storage, rendering, or any target-specific operation. */
typedef enum {
    COMP_MENU_V5_SELECTION_ACTION_COMMITTED = 0u,
    COMP_MENU_V5_SELECTION_LIVE_DATA,
    COMP_MENU_V5_SELECTION_UNAVAILABLE,
} comp_menu_v5_selection_outcome_t;

typedef struct {
    comp_menu_v5_item_t item;
    comp_menu_v5_selection_outcome_t outcome;
    comp_menu_v5_language_t language_after;
    bool language_changed;
    bool has_performance_event;
    comp_pet_performance_event_t performance_event;
} comp_menu_v5_selection_result_t;

bool comp_menu_v5_prepare_selection(comp_menu_v5_root_t root,
                                    uint8_t index,
                                    const comp_menu_v5_context_t *context,
                                    comp_menu_v5_language_t language,
                                    comp_menu_v5_selection_result_t *out_result);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_MENU_V5_ACTION_JOURNEY_H */
