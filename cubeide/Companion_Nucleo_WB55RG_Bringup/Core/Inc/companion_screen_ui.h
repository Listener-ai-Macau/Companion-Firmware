#ifndef COMPANION_SCREEN_UI_H
#define COMPANION_SCREEN_UI_H

#include "screen_menu.h"
#include "expression_state.h"

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

void Companion_Screen_MenuRequest(comp_screen_menu_view_t view,
                                  uint8_t flags,
                                  comp_screen_menu_language_t language,
                                  uint8_t home_page);
bool Companion_Screen_MenuRequestClean(comp_screen_menu_view_t view,
                                       uint8_t flags,
                                       comp_screen_menu_language_t language,
                                       uint8_t home_page);
bool Companion_Screen_MenuMaintenance(void);
bool Companion_Screen_ExpressionMaintenance(void);
bool Companion_Screen_ExpressionPreview(comp_epaper_expression_t expression);
/* Production-off V9 panel-path comparator; normal product builds reject it. */
bool Companion_Screen_V9ManualStepDiagnosticAdvance(void);
bool Companion_Screen_EnterLowPowerIdle(void);
bool Companion_Screen_ShowDaily(void);
bool Companion_Screen_ShowDailyClean(void);
bool Companion_Screen_DailyExpression(comp_epaper_expression_t expression,
                                      const char *reason);
bool Companion_Screen_DailyExpressionSignal(
    comp_epaper_expression_signal_t signal,
    const char *reason);
bool Companion_Screen_DailyTap(void);
bool Companion_Screen_DailyTapAt(uint16_t x, uint16_t y);
bool Companion_Screen_DailyStrokeAt(uint16_t start_x,
                                    uint16_t start_y,
                                    uint16_t end_x,
                                    uint16_t end_y,
                                    uint32_t duration_ms);
/* Dedicated compile-time Rig demo only; normal product builds fail closed. */
bool Companion_Screen_PlayDailyRigDemo(void);
/* Production-off V22 bridge demo only; normal product builds never bind it. */
bool Companion_Screen_PlayV22EmotionBridgeDemo(void);
bool Companion_Screen_BallMotionDiagnosticStart(void);
bool Companion_Screen_BallMotionDiagnosticIsActive(void);
bool Companion_Screen_IsReady(void);
bool Companion_Screen_IsMenuVisible(void);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_SCREEN_UI_H */
