#include "menu_v5_action_journey.h"

#include <stddef.h>

bool comp_menu_v5_prepare_selection(comp_menu_v5_root_t root,
                                    uint8_t index,
                                    const comp_menu_v5_context_t *context,
                                    comp_menu_v5_language_t language,
                                    comp_menu_v5_selection_result_t *out_result)
{
    comp_menu_v5_item_t item;
    comp_menu_v5_language_t next_language = language;

    if (out_result == NULL || !comp_menu_v5_language_is_valid(language) ||
        !comp_menu_v5_resolve_item(root, index, context, &item)) {
        return false;
    }

    *out_result = (comp_menu_v5_selection_result_t){
        .item = item,
        .outcome = COMP_MENU_V5_SELECTION_LIVE_DATA,
        .language_after = language,
        .language_changed = false,
        .has_performance_event = false,
        .performance_event = COMP_PET_PERFORMANCE_EVENT_COUNT,
    };
    if (comp_menu_v5_item_is_selectable(&item)) {
        if (item.action == COMP_MENU_V5_ACTION_LANGUAGE &&
            !comp_menu_v5_apply_language_action(item.action, language, &next_language)) {
            return false;
        }
        if (item.action == COMP_MENU_V5_ACTION_LANGUAGE && next_language != language) {
            out_result->language_after = next_language;
            out_result->language_changed = true;
        }
        out_result->outcome = COMP_MENU_V5_SELECTION_ACTION_COMMITTED;
        out_result->has_performance_event = true;
        out_result->performance_event = COMP_PET_PERFORMANCE_EVENT_MENU_SELECT;
    } else if (item.kind == COMP_MENU_V5_ITEM_DEFERRED || item.kind == COMP_MENU_V5_ITEM_PLANNED) {
        out_result->outcome = COMP_MENU_V5_SELECTION_UNAVAILABLE;
        out_result->has_performance_event = true;
        out_result->performance_event = COMP_PET_PERFORMANCE_EVENT_MENU_BLOCKED;
    }
    return true;
}
