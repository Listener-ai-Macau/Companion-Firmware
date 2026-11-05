#ifndef COMPANION_EPAPER_PET_PERFORMANCE_EVENT_BRIDGE_H
#define COMPANION_EPAPER_PET_PERFORMANCE_EVENT_BRIDGE_H

#include <stdbool.h>

#include "expression_state.h"
#include "pet_performance.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Exact product events retain more meaning than a generic visible expression.
 * The bridge deliberately produces only portable scene metadata. It does not
 * choose a bitmap, CEMP resource or target panel refresh. */
typedef enum {
    COMP_PET_PERFORMANCE_EVENT_DAILY_TAP = 0u,
    COMP_PET_PERFORMANCE_EVENT_DAILY_STROKE,
    COMP_PET_PERFORMANCE_EVENT_DAILY_SWIPE_LEFT,
    COMP_PET_PERFORMANCE_EVENT_DAILY_SWIPE_RIGHT,
    COMP_PET_PERFORMANCE_EVENT_DAILY_SWIPE_UP,
    COMP_PET_PERFORMANCE_EVENT_DAILY_SWIPE_DOWN,
    COMP_PET_PERFORMANCE_EVENT_MENU_HOLD,
    COMP_PET_PERFORMANCE_EVENT_MENU_ENTER,
    COMP_PET_PERFORMANCE_EVENT_MENU_OPEN,
    COMP_PET_PERFORMANCE_EVENT_MENU_SELECT,
    COMP_PET_PERFORMANCE_EVENT_MENU_BLOCKED,
    COMP_PET_PERFORMANCE_EVENT_MENU_EXIT,
    COMP_PET_PERFORMANCE_EVENT_SLEEP_ENTRY,
    COMP_PET_PERFORMANCE_EVENT_DEEP_SLEEP,
    COMP_PET_PERFORMANCE_EVENT_WAKE,
    COMP_PET_PERFORMANCE_EVENT_RECORDING_START,
    COMP_PET_PERFORMANCE_EVENT_RECORDING_ACTIVE,
    COMP_PET_PERFORMANCE_EVENT_RECORDING_SAVING,
    COMP_PET_PERFORMANCE_EVENT_RECORDING_SAVED,
    COMP_PET_PERFORMANCE_EVENT_RECORDING_ERROR,
    COMP_PET_PERFORMANCE_EVENT_RECORDING_RECOVER,
    /* Upgrade events are visual replay metadata only until the shared OTA
     * acceptance unfreezes a target adapter. They never execute OTA work. */
    COMP_PET_PERFORMANCE_EVENT_UPGRADE_OFFER,
    COMP_PET_PERFORMANCE_EVENT_UPGRADE_PREPARE,
    COMP_PET_PERFORMANCE_EVENT_UPGRADE_TRANSFER,
    COMP_PET_PERFORMANCE_EVENT_UPGRADE_VERIFY,
    COMP_PET_PERFORMANCE_EVENT_UPGRADE_RESTART,
    COMP_PET_PERFORMANCE_EVENT_UPGRADE_SUCCESS,
    COMP_PET_PERFORMANCE_EVENT_UPGRADE_ERROR,
    COMP_PET_PERFORMANCE_EVENT_UPGRADE_DISMISS,
    COMP_PET_PERFORMANCE_EVENT_RECOVER_TO_IDLE,
    COMP_PET_PERFORMANCE_EVENT_COUNT,
} comp_pet_performance_event_t;

const char *comp_pet_performance_event_name(comp_pet_performance_event_t event);
bool comp_pet_performance_event_is_replay_only(comp_pet_performance_event_t event);
bool comp_pet_performance_apply_event(comp_pet_performance_t *performance,
                                      comp_pet_performance_event_t event,
                                      comp_pet_performance_frame_t *out_frame);

/* Returns false when the generic signal is either unsupported or deliberately
 * underspecified. In particular SPEAKER_RESULT requires the target glue to
 * forward its precise touch/stroke result through apply_event(). */
bool comp_pet_performance_apply_expression_signal(
    comp_pet_performance_t *performance,
    comp_epaper_expression_signal_t signal,
    comp_pet_performance_frame_t *out_frame);

bool comp_pet_performance_event_bridge_self_test(void);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_PET_PERFORMANCE_EVENT_BRIDGE_H */
