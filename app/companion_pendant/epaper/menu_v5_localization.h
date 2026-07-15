#ifndef COMPANION_EPAPER_MENU_V5_LOCALIZATION_H
#define COMPANION_EPAPER_MENU_V5_LOCALIZATION_H

#include <stdbool.h>

#include "menu_v5_contract.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Portable text and selection semantics. Target renderers choose the approved
 * language-specific resource; this layer does not select bitmap assets. */
typedef enum {
    COMP_MENU_V5_LANGUAGE_EN = 0u,
    COMP_MENU_V5_LANGUAGE_ZH_CN = 1u,
    COMP_MENU_V5_LANGUAGE_COUNT = 2u,
} comp_menu_v5_language_t;

const char *comp_menu_v5_text(comp_menu_v5_language_t language,
                              comp_menu_v5_text_key_t key);
bool comp_menu_v5_language_is_valid(comp_menu_v5_language_t language);
const char *comp_menu_v5_language_display_name(comp_menu_v5_language_t language);
const char *comp_menu_v5_action_label(comp_menu_v5_language_t language,
                                      comp_menu_v5_action_t action);
bool comp_menu_v5_toggle_language(comp_menu_v5_language_t current,
                                  comp_menu_v5_language_t *out_next);
bool comp_menu_v5_apply_language_action(comp_menu_v5_action_t action,
                                        comp_menu_v5_language_t current,
                                        comp_menu_v5_language_t *out_next);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_MENU_V5_LOCALIZATION_H */
