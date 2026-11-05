#ifndef COMPANION_EPAPER_MENU_V5_TARGET_BRIDGE_H
#define COMPANION_EPAPER_MENU_V5_TARGET_BRIDGE_H

#include <stdbool.h>
#include <stdint.h>

#include "menu_v5_navigation.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Target-facing state holder for the four-root contract. This bridge owns no
 * renderer, Flash resource, target HAL, recording, or BLE side effect. A
 * target integration must execute committed actions explicitly and may only
 * select visual resources after their separate owner/camera gates pass. */
typedef struct {
    comp_menu_v5_navigation_t navigation;
    comp_menu_v5_context_t context;
    bool initialized;
} comp_menu_v5_target_bridge_t;

void comp_menu_v5_target_bridge_init(comp_menu_v5_target_bridge_t *bridge,
                                     comp_menu_v5_language_t language);
bool comp_menu_v5_target_bridge_update_context(comp_menu_v5_target_bridge_t *bridge,
                                                const comp_menu_v5_context_t *context);
comp_menu_v5_navigation_result_t comp_menu_v5_target_bridge_tap(
    comp_menu_v5_target_bridge_t *bridge,
    uint16_t x,
    uint16_t y);
comp_menu_v5_navigation_result_t comp_menu_v5_target_bridge_drag(
    comp_menu_v5_target_bridge_t *bridge,
    int16_t finger_delta_y);
comp_menu_v5_navigation_result_t comp_menu_v5_target_bridge_back(
    comp_menu_v5_target_bridge_t *bridge);
bool comp_menu_v5_target_bridge_self_test(void);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_MENU_V5_TARGET_BRIDGE_H */
