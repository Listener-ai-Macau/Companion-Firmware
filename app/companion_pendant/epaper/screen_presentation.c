#include "screen_presentation.h"

void comp_screen_presentation_init(comp_screen_presentation_t *state)
{
    if (state == NULL) {
        return;
    }
    *state = (comp_screen_presentation_t){
        .mode = COMP_SCREEN_PRESENTATION_MENU,
        .menu_view = COMP_SCREEN_MENU_VIEW_HOME,
        .menu_language = COMP_SCREEN_MENU_LANGUAGE_ZH,
        .expression = COMP_EPAPER_EXPRESSION_IDLE,
    };
}

void comp_screen_presentation_show_menu(comp_screen_presentation_t *state,
                                        comp_screen_menu_view_t view,
                                        uint8_t flags,
                                        comp_screen_menu_language_t language,
                                        uint8_t page)
{
    if (state == NULL) {
        return;
    }
    state->mode = COMP_SCREEN_PRESENTATION_MENU;
    state->menu_view = view;
    state->menu_flags = flags;
    state->menu_language = language;
    state->menu_page = page;
    state->revision++;
}

void comp_screen_presentation_show_expression(
    comp_screen_presentation_t *state,
    comp_epaper_expression_t expression)
{
    if (state == NULL || !comp_epaper_expression_is_supported(expression)) {
        return;
    }
    if (state->mode == COMP_SCREEN_PRESENTATION_MENU) {
        state->expression_returns_to_menu = true;
    }
    state->mode = COMP_SCREEN_PRESENTATION_EXPRESSION;
    state->expression = expression;
    state->revision++;
}

void comp_screen_presentation_show_daily(comp_screen_presentation_t *state)
{
    if (state == NULL) {
        return;
    }
    state->mode = COMP_SCREEN_PRESENTATION_EXPRESSION;
    state->expression = COMP_EPAPER_EXPRESSION_IDLE;
    state->expression_returns_to_menu = false;
    state->revision++;
}

comp_screen_presentation_action_t comp_screen_presentation_apply_product_expression(
    comp_screen_presentation_t *state,
    comp_epaper_expression_t expression)
{
    if (state == NULL || !comp_epaper_expression_is_supported(expression)) {
        return COMP_SCREEN_PRESENTATION_ACTION_IGNORE;
    }
    if (expression == COMP_EPAPER_EXPRESSION_IDLE) {
        if (state->mode != COMP_SCREEN_PRESENTATION_EXPRESSION) {
            return COMP_SCREEN_PRESENTATION_ACTION_IGNORE;
        }
        if (!state->expression_returns_to_menu) {
            state->expression = expression;
            state->revision++;
            return COMP_SCREEN_PRESENTATION_ACTION_SHOW_EXPRESSION;
        }
        state->mode = COMP_SCREEN_PRESENTATION_MENU;
        state->expression = expression;
        state->revision++;
        return COMP_SCREEN_PRESENTATION_ACTION_RESTORE_MENU;
    }
    comp_screen_presentation_show_expression(state, expression);
    return COMP_SCREEN_PRESENTATION_ACTION_SHOW_EXPRESSION;
}

bool comp_screen_presentation_self_test(void)
{
    comp_screen_presentation_t state;

    comp_screen_presentation_init(&state);
    if (state.mode != COMP_SCREEN_PRESENTATION_MENU ||
        comp_screen_presentation_apply_product_expression(
            &state, COMP_EPAPER_EXPRESSION_IDLE) !=
            COMP_SCREEN_PRESENTATION_ACTION_IGNORE) {
        return false;
    }
    comp_screen_presentation_show_daily(&state);
    if (state.mode != COMP_SCREEN_PRESENTATION_EXPRESSION ||
        state.expression_returns_to_menu ||
        comp_screen_presentation_apply_product_expression(
            &state, COMP_EPAPER_EXPRESSION_HAPPY) !=
            COMP_SCREEN_PRESENTATION_ACTION_SHOW_EXPRESSION ||
        comp_screen_presentation_apply_product_expression(
            &state, COMP_EPAPER_EXPRESSION_IDLE) !=
            COMP_SCREEN_PRESENTATION_ACTION_SHOW_EXPRESSION ||
        state.mode != COMP_SCREEN_PRESENTATION_EXPRESSION) {
        return false;
    }
    comp_screen_presentation_init(&state);
    comp_screen_presentation_show_menu(&state,
                                       COMP_SCREEN_MENU_VIEW_STATUS,
                                       COMP_SCREEN_MENU_FLAG_TOUCH_OK,
                                       COMP_SCREEN_MENU_LANGUAGE_EN,
                                       1u);
    if (comp_screen_presentation_apply_product_expression(
            &state, COMP_EPAPER_EXPRESSION_RECORDING) !=
            COMP_SCREEN_PRESENTATION_ACTION_SHOW_EXPRESSION ||
        state.mode != COMP_SCREEN_PRESENTATION_EXPRESSION) {
        return false;
    }
    return comp_screen_presentation_apply_product_expression(
               &state, COMP_EPAPER_EXPRESSION_IDLE) ==
               COMP_SCREEN_PRESENTATION_ACTION_RESTORE_MENU &&
           state.mode == COMP_SCREEN_PRESENTATION_MENU &&
           state.menu_view == COMP_SCREEN_MENU_VIEW_STATUS &&
           state.menu_language == COMP_SCREEN_MENU_LANGUAGE_EN &&
           state.menu_page == 1u &&
           state.menu_flags == COMP_SCREEN_MENU_FLAG_TOUCH_OK;
}
