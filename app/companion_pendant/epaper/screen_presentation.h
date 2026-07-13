#ifndef COMPANION_EPAPER_SCREEN_PRESENTATION_H
#define COMPANION_EPAPER_SCREEN_PRESENTATION_H

#include "expression_state.h"
#include "screen_menu.h"

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    COMP_SCREEN_PRESENTATION_MENU = 0u,
    COMP_SCREEN_PRESENTATION_EXPRESSION = 1u,
} comp_screen_presentation_mode_t;

typedef enum {
    COMP_SCREEN_PRESENTATION_ACTION_IGNORE = 0u,
    COMP_SCREEN_PRESENTATION_ACTION_SHOW_EXPRESSION = 1u,
    COMP_SCREEN_PRESENTATION_ACTION_RESTORE_MENU = 2u,
} comp_screen_presentation_action_t;

typedef struct {
    comp_screen_presentation_mode_t mode;
    comp_screen_menu_view_t menu_view;
    comp_screen_menu_language_t menu_language;
    comp_epaper_expression_t expression;
    uint8_t menu_flags;
    uint8_t menu_page;
    bool expression_returns_to_menu;
    uint32_t revision;
} comp_screen_presentation_t;

void comp_screen_presentation_init(comp_screen_presentation_t *state);
void comp_screen_presentation_show_menu(comp_screen_presentation_t *state,
                                        comp_screen_menu_view_t view,
                                        uint8_t flags,
                                        comp_screen_menu_language_t language,
                                        uint8_t page);
void comp_screen_presentation_show_expression(
    comp_screen_presentation_t *state,
    comp_epaper_expression_t expression);
void comp_screen_presentation_show_daily(comp_screen_presentation_t *state);
comp_screen_presentation_action_t comp_screen_presentation_apply_product_expression(
    comp_screen_presentation_t *state,
    comp_epaper_expression_t expression);
bool comp_screen_presentation_self_test(void);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_SCREEN_PRESENTATION_H */
