#ifndef COMPANION_EPAPER_PET_PERFORMANCE_H
#define COMPANION_EPAPER_PET_PERFORMANCE_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* A performance is selected by a committed product event. It only progresses
 * when the owning feature submits the next real outcome; it has no timer or
 * refresh loop. The renderer maps resource_family + phase to external-Flash
 * keyframes after the corresponding generated reference is approved. */
typedef enum {
    COMP_PET_PERFORMANCE_SCENE_DAILY_IDLE = 0u,
    COMP_PET_PERFORMANCE_SCENE_DAILY_TAP,
    COMP_PET_PERFORMANCE_SCENE_DAILY_STROKE,
    COMP_PET_PERFORMANCE_SCENE_DAILY_SWIPE_LEFT,
    COMP_PET_PERFORMANCE_SCENE_DAILY_SWIPE_RIGHT,
    COMP_PET_PERFORMANCE_SCENE_DAILY_SWIPE_UP,
    COMP_PET_PERFORMANCE_SCENE_DAILY_SWIPE_DOWN,
    COMP_PET_PERFORMANCE_SCENE_VOICE_LISTENING,
    COMP_PET_PERFORMANCE_SCENE_VOICE_SPEAKING,
    COMP_PET_PERFORMANCE_SCENE_MENU_HOLD,
    COMP_PET_PERFORMANCE_SCENE_MENU_ENTER,
    COMP_PET_PERFORMANCE_SCENE_MENU_OPEN,
    COMP_PET_PERFORMANCE_SCENE_MENU_SELECT,
    COMP_PET_PERFORMANCE_SCENE_MENU_BLOCKED,
    COMP_PET_PERFORMANCE_SCENE_MENU_EXIT,
    COMP_PET_PERFORMANCE_SCENE_RECORDING_START,
    COMP_PET_PERFORMANCE_SCENE_RECORDING_ACTIVE,
    COMP_PET_PERFORMANCE_SCENE_RECORDING_SAVING,
    COMP_PET_PERFORMANCE_SCENE_RECORDING_SAVED,
    COMP_PET_PERFORMANCE_SCENE_RECORDING_ERROR,
    COMP_PET_PERFORMANCE_SCENE_SLEEP_ENTRY,
    COMP_PET_PERFORMANCE_SCENE_DEEP_SLEEP,
    COMP_PET_PERFORMANCE_SCENE_WAKE,
    COMP_PET_PERFORMANCE_SCENE_CHARGE_DETECTED,
    COMP_PET_PERFORMANCE_SCENE_CHARGING,
    COMP_PET_PERFORMANCE_SCENE_CHARGED,
    COMP_PET_PERFORMANCE_SCENE_LOW_BATTERY,
    COMP_PET_PERFORMANCE_SCENE_LINK_PAIRING,
    COMP_PET_PERFORMANCE_SCENE_LINK_CONNECTED,
    COMP_PET_PERFORMANCE_SCENE_LINK_SYNCING,
    COMP_PET_PERFORMANCE_SCENE_LINK_SYNCED,
    COMP_PET_PERFORMANCE_SCENE_LINK_ERROR,
    COMP_PET_PERFORMANCE_SCENE_UPGRADE_OFFER,
    COMP_PET_PERFORMANCE_SCENE_UPGRADE_PREPARE,
    COMP_PET_PERFORMANCE_SCENE_UPGRADE_TRANSFER,
    COMP_PET_PERFORMANCE_SCENE_UPGRADE_VERIFY,
    COMP_PET_PERFORMANCE_SCENE_UPGRADE_RESTART,
    COMP_PET_PERFORMANCE_SCENE_UPGRADE_SUCCESS,
    COMP_PET_PERFORMANCE_SCENE_UPGRADE_ERROR,
    COMP_PET_PERFORMANCE_SCENE_SYSTEM_ERROR,
    COMP_PET_PERFORMANCE_SCENE_COUNT,
} comp_pet_performance_scene_t;

typedef enum {
    COMP_PET_PERFORMANCE_PHASE_ENTRY = 0u,
    COMP_PET_PERFORMANCE_PHASE_SUSTAINED,
    COMP_PET_PERFORMANCE_PHASE_SETTLE,
    COMP_PET_PERFORMANCE_PHASE_EXIT,
    COMP_PET_PERFORMANCE_PHASE_COUNT,
} comp_pet_performance_phase_t;

typedef struct {
    comp_pet_performance_scene_t scene;
    comp_pet_performance_phase_t phase;
    uint8_t priority;
    uint8_t keyframe_index;
    uint8_t keyframe_count;
    uint32_t generation;
    const char *scene_name;
    const char *resource_family;
    const char *phase_name;
} comp_pet_performance_frame_t;

typedef struct {
    comp_pet_performance_scene_t scene;
    comp_pet_performance_phase_t phase;
    uint8_t priority;
    uint32_t generation;
    bool initialized;
} comp_pet_performance_t;

void comp_pet_performance_init(comp_pet_performance_t *performance);
bool comp_pet_performance_scene_is_supported(comp_pet_performance_scene_t scene);
bool comp_pet_performance_phase_is_supported(comp_pet_performance_scene_t scene,
                                              comp_pet_performance_phase_t phase);
const char *comp_pet_performance_scene_name(comp_pet_performance_scene_t scene);
const char *comp_pet_performance_phase_name(comp_pet_performance_phase_t phase);

/* Start a new real scene. A lower-priority scene may only replace another
 * scene in the same product journey, such as recording-active -> saving. */
bool comp_pet_performance_begin(comp_pet_performance_t *performance,
                                comp_pet_performance_scene_t scene,
                                comp_pet_performance_frame_t *out_frame);

/* Explicitly move the active scene forward. This is intentionally not a tick
 * API: e-paper cadence is driven by product outcomes, never a fast loop. */
bool comp_pet_performance_advance(comp_pet_performance_t *performance,
                                  comp_pet_performance_phase_t next_phase,
                                  comp_pet_performance_frame_t *out_frame);

/* Recovery is the only universal path back to daily idle. */
bool comp_pet_performance_recover_to_idle(comp_pet_performance_t *performance,
                                          comp_pet_performance_frame_t *out_frame);
bool comp_pet_performance_current(const comp_pet_performance_t *performance,
                                  comp_pet_performance_frame_t *out_frame);
uint32_t comp_pet_performance_self_test_failure_code(void);
bool comp_pet_performance_self_test(void);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_PET_PERFORMANCE_H */
