#ifndef COMPANION_EPAPER_MENU_V5_VIEW_MODEL_H
#define COMPANION_EPAPER_MENU_V5_VIEW_MODEL_H

#include <stdbool.h>
#include <stdint.h>

#include "menu_v5_navigation.h"

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_MENU_V5_VIEW_MODEL_MAX_ROWS 5u

/* Renderer input only. It carries truthful menu behavior and visual roles but
 * cannot choose art, load a resource, access Flash, or execute an action. */
typedef enum {
    COMP_MENU_V5_VIEW_MODEL_TRAILING_NONE = 0u,
    COMP_MENU_V5_VIEW_MODEL_TRAILING_CHEVRON,
    COMP_MENU_V5_VIEW_MODEL_TRAILING_LIVE_STATUS,
    COMP_MENU_V5_VIEW_MODEL_TRAILING_DEFERRED,
    COMP_MENU_V5_VIEW_MODEL_TRAILING_PLANNED,
} comp_menu_v5_view_model_trailing_t;

/* Stable roles allow a later approved v9 menu pack to bind art without
 * re-deciding menu behavior. These are not asset paths. */
typedef enum {
    COMP_MENU_V5_VIEW_MODEL_COMPONENT_NONE = 0u,
    COMP_MENU_V5_VIEW_MODEL_COMPONENT_HEADER_FACE,
    COMP_MENU_V5_VIEW_MODEL_COMPONENT_VOICE_ICON,
    COMP_MENU_V5_VIEW_MODEL_COMPONENT_DEVICE_ICON,
    COMP_MENU_V5_VIEW_MODEL_COMPONENT_CONNECTION_ICON,
    COMP_MENU_V5_VIEW_MODEL_COMPONENT_PREFERENCES_ICON,
    COMP_MENU_V5_VIEW_MODEL_COMPONENT_CHEVRON,
    COMP_MENU_V5_VIEW_MODEL_COMPONENT_LIVE_MARK,
    COMP_MENU_V5_VIEW_MODEL_COMPONENT_DEFERRED_BADGE,
} comp_menu_v5_view_model_component_t;

typedef struct {
    const char *label;
    const char *action_label;
    const char *value_label;
    comp_menu_v5_item_kind_t kind;
    comp_menu_v5_action_t action;
    comp_menu_v5_view_model_trailing_t trailing;
    comp_menu_v5_view_model_component_t leading_component;
    comp_menu_v5_view_model_component_t trailing_component;
    bool is_navigation;
    bool has_live_value;
    bool live_value;
} comp_menu_v5_view_model_row_t;

typedef struct {
    comp_menu_v5_navigation_view_t view;
    comp_menu_v5_root_t root;
    comp_menu_v5_language_t language;
    const char *title;
    bool has_identity_mark;
    comp_menu_v5_view_model_component_t identity_component;
    bool has_back_affordance;
    uint8_t row_count;
    uint16_t scroll_offset_px;
    comp_menu_v5_view_model_row_t rows[COMP_MENU_V5_VIEW_MODEL_MAX_ROWS];
} comp_menu_v5_view_model_t;

bool comp_menu_v5_view_model_build(const comp_menu_v5_navigation_t *navigation,
                                   const comp_menu_v5_context_t *context,
                                   comp_menu_v5_view_model_t *out_model);
bool comp_menu_v5_view_model_self_test(void);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_MENU_V5_VIEW_MODEL_H */
