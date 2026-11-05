#include "pet_performance.h"

#include <stddef.h>
#include <string.h>

#define COMP_PET_PERFORMANCE_PHASE_BIT(phase) (1u << (uint8_t)(phase))
#define COMP_PET_PERFORMANCE_PHASES_MOTION \
    (COMP_PET_PERFORMANCE_PHASE_BIT(COMP_PET_PERFORMANCE_PHASE_ENTRY) | \
     COMP_PET_PERFORMANCE_PHASE_BIT(COMP_PET_PERFORMANCE_PHASE_SUSTAINED) | \
     COMP_PET_PERFORMANCE_PHASE_BIT(COMP_PET_PERFORMANCE_PHASE_SETTLE) | \
     COMP_PET_PERFORMANCE_PHASE_BIT(COMP_PET_PERFORMANCE_PHASE_EXIT))
#define COMP_PET_PERFORMANCE_PHASES_STATIC \
    COMP_PET_PERFORMANCE_PHASE_BIT(COMP_PET_PERFORMANCE_PHASE_SUSTAINED)

typedef enum {
    COMP_PET_PERFORMANCE_JOURNEY_DAILY = 0u,
    COMP_PET_PERFORMANCE_JOURNEY_MENU,
    COMP_PET_PERFORMANCE_JOURNEY_RECORDING,
    COMP_PET_PERFORMANCE_JOURNEY_VOICE,
    COMP_PET_PERFORMANCE_JOURNEY_POWER,
    COMP_PET_PERFORMANCE_JOURNEY_LINK,
    COMP_PET_PERFORMANCE_JOURNEY_UPGRADE,
    COMP_PET_PERFORMANCE_JOURNEY_ERROR,
} comp_pet_performance_journey_t;

typedef struct {
    comp_pet_performance_scene_t scene;
    comp_pet_performance_journey_t journey;
    uint8_t priority;
    uint8_t phase_mask;
    uint8_t keyframe_count;
    const char *name;
    const char *resource_family;
} comp_pet_performance_scene_def_t;

static uint32_t s_pet_performance_self_test_failure_code;

static const char *const k_phase_names[COMP_PET_PERFORMANCE_PHASE_COUNT] = {
    "entry",
    "sustained",
    "settle",
    "exit",
};

#define SCENE_MOTION(id, group, rank, label, asset) \
    {id, group, rank, COMP_PET_PERFORMANCE_PHASES_MOTION, 3u, label, asset}
#define SCENE_STATIC(id, group, rank, label, asset) \
    {id, group, rank, COMP_PET_PERFORMANCE_PHASES_STATIC, 1u, label, asset}

static const comp_pet_performance_scene_def_t k_scene_defs[] = {
    SCENE_STATIC(COMP_PET_PERFORMANCE_SCENE_DAILY_IDLE, COMP_PET_PERFORMANCE_JOURNEY_DAILY, 10u, "daily.idle", "daily.idle"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_DAILY_TAP, COMP_PET_PERFORMANCE_JOURNEY_DAILY, 30u, "daily.tap", "daily.tap"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_DAILY_STROKE, COMP_PET_PERFORMANCE_JOURNEY_DAILY, 30u, "daily.stroke", "daily.stroke"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_DAILY_SWIPE_LEFT, COMP_PET_PERFORMANCE_JOURNEY_DAILY, 30u, "daily.swipe_left", "daily.swipe_left"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_DAILY_SWIPE_RIGHT, COMP_PET_PERFORMANCE_JOURNEY_DAILY, 30u, "daily.swipe_right", "daily.swipe_right"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_DAILY_SWIPE_UP, COMP_PET_PERFORMANCE_JOURNEY_DAILY, 30u, "daily.swipe_up", "daily.swipe_up"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_DAILY_SWIPE_DOWN, COMP_PET_PERFORMANCE_JOURNEY_DAILY, 30u, "daily.swipe_down", "daily.swipe_down"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_VOICE_LISTENING, COMP_PET_PERFORMANCE_JOURNEY_VOICE, 70u, "voice.listening", "voice.listening"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_VOICE_SPEAKING, COMP_PET_PERFORMANCE_JOURNEY_VOICE, 65u, "voice.speaking", "voice.speaking"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_MENU_HOLD, COMP_PET_PERFORMANCE_JOURNEY_MENU, 50u, "menu.hold", "menu.hold"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_MENU_ENTER, COMP_PET_PERFORMANCE_JOURNEY_MENU, 55u, "menu.enter", "menu.enter"),
    SCENE_STATIC(COMP_PET_PERFORMANCE_SCENE_MENU_OPEN, COMP_PET_PERFORMANCE_JOURNEY_MENU, 55u, "menu.open", "menu.open"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_MENU_SELECT, COMP_PET_PERFORMANCE_JOURNEY_MENU, 60u, "menu.select", "menu.select"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_MENU_BLOCKED, COMP_PET_PERFORMANCE_JOURNEY_MENU, 60u, "menu.blocked", "menu.blocked"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_MENU_EXIT, COMP_PET_PERFORMANCE_JOURNEY_MENU, 55u, "menu.exit", "menu.exit"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_RECORDING_START, COMP_PET_PERFORMANCE_JOURNEY_RECORDING, 75u, "recording.start", "recording.start"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_RECORDING_ACTIVE, COMP_PET_PERFORMANCE_JOURNEY_RECORDING, 85u, "recording.active", "recording.active"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_RECORDING_SAVING, COMP_PET_PERFORMANCE_JOURNEY_RECORDING, 70u, "recording.saving", "recording.saving"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_RECORDING_SAVED, COMP_PET_PERFORMANCE_JOURNEY_RECORDING, 50u, "recording.saved", "recording.saved"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_RECORDING_ERROR, COMP_PET_PERFORMANCE_JOURNEY_RECORDING, 100u, "recording.error", "recording.error"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_SLEEP_ENTRY, COMP_PET_PERFORMANCE_JOURNEY_POWER, 20u, "power.sleep_entry", "power.sleep_entry"),
    SCENE_STATIC(COMP_PET_PERFORMANCE_SCENE_DEEP_SLEEP, COMP_PET_PERFORMANCE_JOURNEY_POWER, 15u, "power.deep_sleep", "power.deep_sleep"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_WAKE, COMP_PET_PERFORMANCE_JOURNEY_POWER, 45u, "power.wake", "power.wake"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_CHARGE_DETECTED, COMP_PET_PERFORMANCE_JOURNEY_POWER, 65u, "power.charge_detected", "power.charge_detected"),
    SCENE_STATIC(COMP_PET_PERFORMANCE_SCENE_CHARGING, COMP_PET_PERFORMANCE_JOURNEY_POWER, 60u, "power.charging", "power.charging"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_CHARGED, COMP_PET_PERFORMANCE_JOURNEY_POWER, 50u, "power.charged", "power.charged"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_LOW_BATTERY, COMP_PET_PERFORMANCE_JOURNEY_POWER, 90u, "power.low_battery", "power.low_battery"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_LINK_PAIRING, COMP_PET_PERFORMANCE_JOURNEY_LINK, 40u, "link.pairing", "link.pairing"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_LINK_CONNECTED, COMP_PET_PERFORMANCE_JOURNEY_LINK, 40u, "link.connected", "link.connected"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_LINK_SYNCING, COMP_PET_PERFORMANCE_JOURNEY_LINK, 55u, "link.syncing", "link.syncing"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_LINK_SYNCED, COMP_PET_PERFORMANCE_JOURNEY_LINK, 45u, "link.synced", "link.synced"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_LINK_ERROR, COMP_PET_PERFORMANCE_JOURNEY_LINK, 90u, "link.error", "link.error"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_UPGRADE_OFFER, COMP_PET_PERFORMANCE_JOURNEY_UPGRADE, 70u, "upgrade.offer", "upgrade.offer"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_UPGRADE_PREPARE, COMP_PET_PERFORMANCE_JOURNEY_UPGRADE, 80u, "upgrade.prepare", "upgrade.prepare"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_UPGRADE_TRANSFER, COMP_PET_PERFORMANCE_JOURNEY_UPGRADE, 80u, "upgrade.transfer", "upgrade.transfer"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_UPGRADE_VERIFY, COMP_PET_PERFORMANCE_JOURNEY_UPGRADE, 80u, "upgrade.verify", "upgrade.verify"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_UPGRADE_RESTART, COMP_PET_PERFORMANCE_JOURNEY_UPGRADE, 80u, "upgrade.restart", "upgrade.restart"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_UPGRADE_SUCCESS, COMP_PET_PERFORMANCE_JOURNEY_UPGRADE, 60u, "upgrade.success", "upgrade.success"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_UPGRADE_ERROR, COMP_PET_PERFORMANCE_JOURNEY_UPGRADE, 100u, "upgrade.error", "upgrade.error"),
    SCENE_MOTION(COMP_PET_PERFORMANCE_SCENE_SYSTEM_ERROR, COMP_PET_PERFORMANCE_JOURNEY_ERROR, 100u, "system.error", "system.error"),
};

static const comp_pet_performance_scene_def_t *find_scene(comp_pet_performance_scene_t scene)
{
    for (size_t index = 0u; index < sizeof(k_scene_defs) / sizeof(k_scene_defs[0]); ++index) {
        if (k_scene_defs[index].scene == scene) {
            return &k_scene_defs[index];
        }
    }
    return NULL;
}

static uint8_t keyframe_index(const comp_pet_performance_scene_def_t *def,
                              comp_pet_performance_phase_t phase)
{
    if (def == NULL || def->keyframe_count <= 1u) {
        return 0u;
    }
    switch (phase) {
    case COMP_PET_PERFORMANCE_PHASE_ENTRY:
        return 0u;
    case COMP_PET_PERFORMANCE_PHASE_SUSTAINED:
        return 1u;
    case COMP_PET_PERFORMANCE_PHASE_SETTLE:
    case COMP_PET_PERFORMANCE_PHASE_EXIT:
        return 2u;
    default:
        return 0u;
    }
}

static bool phase_transition_is_valid(comp_pet_performance_phase_t current,
                                      comp_pet_performance_phase_t next)
{
    if (current == COMP_PET_PERFORMANCE_PHASE_ENTRY) {
        return next == COMP_PET_PERFORMANCE_PHASE_SUSTAINED ||
               next == COMP_PET_PERFORMANCE_PHASE_SETTLE ||
               next == COMP_PET_PERFORMANCE_PHASE_EXIT;
    }
    if (current == COMP_PET_PERFORMANCE_PHASE_SUSTAINED) {
        return next == COMP_PET_PERFORMANCE_PHASE_SETTLE ||
               next == COMP_PET_PERFORMANCE_PHASE_EXIT;
    }
    return false;
}

static bool scene_can_replace(const comp_pet_performance_t *performance,
                              const comp_pet_performance_scene_def_t *next)
{
    const comp_pet_performance_scene_def_t *current;
    if (performance == NULL || next == NULL || !performance->initialized) {
        return true;
    }
    current = find_scene(performance->scene);
    if (current == NULL || next->priority >= current->priority) {
        return true;
    }
    return next->journey == current->journey;
}

static void write_frame(const comp_pet_performance_t *performance,
                        const comp_pet_performance_scene_def_t *def,
                        comp_pet_performance_frame_t *out_frame)
{
    if (out_frame == NULL) {
        return;
    }
    memset(out_frame, 0, sizeof(*out_frame));
    if (performance == NULL || def == NULL ||
        performance->phase >= COMP_PET_PERFORMANCE_PHASE_COUNT) {
        return;
    }
    out_frame->scene = performance->scene;
    out_frame->phase = performance->phase;
    out_frame->priority = def->priority;
    out_frame->keyframe_index = keyframe_index(def, performance->phase);
    out_frame->keyframe_count = def->keyframe_count;
    out_frame->generation = performance->generation;
    out_frame->scene_name = def->name;
    out_frame->resource_family = def->resource_family;
    out_frame->phase_name = k_phase_names[performance->phase];
}

void comp_pet_performance_init(comp_pet_performance_t *performance)
{
    const comp_pet_performance_scene_def_t *idle;
    if (performance == NULL) {
        return;
    }
    idle = find_scene(COMP_PET_PERFORMANCE_SCENE_DAILY_IDLE);
    memset(performance, 0, sizeof(*performance));
    performance->scene = COMP_PET_PERFORMANCE_SCENE_DAILY_IDLE;
    performance->phase = COMP_PET_PERFORMANCE_PHASE_SUSTAINED;
    performance->priority = idle == NULL ? 0u : idle->priority;
    performance->generation = 1u;
    performance->initialized = idle != NULL;
}

bool comp_pet_performance_scene_is_supported(comp_pet_performance_scene_t scene)
{
    return find_scene(scene) != NULL;
}

bool comp_pet_performance_phase_is_supported(comp_pet_performance_scene_t scene,
                                              comp_pet_performance_phase_t phase)
{
    const comp_pet_performance_scene_def_t *def = find_scene(scene);
    return def != NULL && phase < COMP_PET_PERFORMANCE_PHASE_COUNT &&
           (def->phase_mask & COMP_PET_PERFORMANCE_PHASE_BIT(phase)) != 0u;
}

const char *comp_pet_performance_scene_name(comp_pet_performance_scene_t scene)
{
    const comp_pet_performance_scene_def_t *def = find_scene(scene);
    return def == NULL ? "unknown" : def->name;
}

const char *comp_pet_performance_phase_name(comp_pet_performance_phase_t phase)
{
    return phase < COMP_PET_PERFORMANCE_PHASE_COUNT ? k_phase_names[phase] : "unknown";
}

bool comp_pet_performance_begin(comp_pet_performance_t *performance,
                                comp_pet_performance_scene_t scene,
                                comp_pet_performance_frame_t *out_frame)
{
    const comp_pet_performance_scene_def_t *def = find_scene(scene);
    comp_pet_performance_phase_t initial_phase;
    if (performance == NULL || out_frame == NULL || def == NULL ||
        !scene_can_replace(performance, def)) {
        return false;
    }

    initial_phase = comp_pet_performance_phase_is_supported(
                        scene, COMP_PET_PERFORMANCE_PHASE_ENTRY)
                        ? COMP_PET_PERFORMANCE_PHASE_ENTRY
                        : COMP_PET_PERFORMANCE_PHASE_SUSTAINED;
    performance->scene = scene;
    performance->phase = initial_phase;
    performance->priority = def->priority;
    performance->generation++;
    if (performance->generation == 0u) {
        performance->generation = 1u;
    }
    performance->initialized = true;
    write_frame(performance, def, out_frame);
    return true;
}

bool comp_pet_performance_advance(comp_pet_performance_t *performance,
                                  comp_pet_performance_phase_t next_phase,
                                  comp_pet_performance_frame_t *out_frame)
{
    const comp_pet_performance_scene_def_t *def;
    if (performance == NULL || out_frame == NULL || !performance->initialized ||
        !phase_transition_is_valid(performance->phase, next_phase) ||
        !comp_pet_performance_phase_is_supported(performance->scene, next_phase)) {
        return false;
    }
    def = find_scene(performance->scene);
    if (def == NULL) {
        return false;
    }
    performance->phase = next_phase;
    write_frame(performance, def, out_frame);
    return true;
}

bool comp_pet_performance_recover_to_idle(comp_pet_performance_t *performance,
                                          comp_pet_performance_frame_t *out_frame)
{
    const comp_pet_performance_scene_def_t *idle =
        find_scene(COMP_PET_PERFORMANCE_SCENE_DAILY_IDLE);
    if (performance == NULL || out_frame == NULL || idle == NULL) {
        return false;
    }
    performance->scene = idle->scene;
    performance->phase = COMP_PET_PERFORMANCE_PHASE_SUSTAINED;
    performance->priority = idle->priority;
    performance->generation++;
    if (performance->generation == 0u) {
        performance->generation = 1u;
    }
    performance->initialized = true;
    write_frame(performance, idle, out_frame);
    return true;
}

bool comp_pet_performance_current(const comp_pet_performance_t *performance,
                                  comp_pet_performance_frame_t *out_frame)
{
    const comp_pet_performance_scene_def_t *def;
    if (performance == NULL || out_frame == NULL || !performance->initialized) {
        return false;
    }
    def = find_scene(performance->scene);
    if (def == NULL || !comp_pet_performance_phase_is_supported(performance->scene,
                                                                  performance->phase)) {
        return false;
    }
    write_frame(performance, def, out_frame);
    return true;
}

uint32_t comp_pet_performance_self_test_failure_code(void)
{
    return s_pet_performance_self_test_failure_code;
}

bool comp_pet_performance_self_test(void)
{
    comp_pet_performance_t performance;
    comp_pet_performance_frame_t frame;

    s_pet_performance_self_test_failure_code = 0u;
    comp_pet_performance_init(&performance);
    if (!comp_pet_performance_current(&performance, &frame) || frame.generation != 1u ||
        frame.scene != COMP_PET_PERFORMANCE_SCENE_DAILY_IDLE ||
        frame.phase != COMP_PET_PERFORMANCE_PHASE_SUSTAINED ||
        frame.keyframe_count != 1u || strcmp(frame.resource_family, "daily.idle") != 0) {
        s_pet_performance_self_test_failure_code = 1u;
        return false;
    }
    if (!comp_pet_performance_begin(&performance, COMP_PET_PERFORMANCE_SCENE_DAILY_TAP, &frame) ||
        frame.generation != 2u || frame.phase != COMP_PET_PERFORMANCE_PHASE_ENTRY ||
        frame.keyframe_index != 0u || strcmp(frame.phase_name, "entry") != 0) {
        s_pet_performance_self_test_failure_code = 2u;
        return false;
    }
    if (!comp_pet_performance_advance(&performance, COMP_PET_PERFORMANCE_PHASE_SUSTAINED, &frame) ||
        frame.generation != 2u || frame.keyframe_index != 1u ||
        !comp_pet_performance_advance(&performance, COMP_PET_PERFORMANCE_PHASE_SETTLE, &frame) ||
        frame.keyframe_index != 2u ||
        comp_pet_performance_advance(&performance, COMP_PET_PERFORMANCE_PHASE_EXIT, &frame)) {
        s_pet_performance_self_test_failure_code = 3u;
        return false;
    }
    if (!comp_pet_performance_begin(&performance, COMP_PET_PERFORMANCE_SCENE_RECORDING_START, &frame) ||
        !comp_pet_performance_begin(&performance, COMP_PET_PERFORMANCE_SCENE_RECORDING_ACTIVE, &frame) ||
        comp_pet_performance_begin(&performance, COMP_PET_PERFORMANCE_SCENE_MENU_HOLD, &frame) ||
        !comp_pet_performance_begin(&performance, COMP_PET_PERFORMANCE_SCENE_RECORDING_SAVING, &frame) ||
        !comp_pet_performance_begin(&performance, COMP_PET_PERFORMANCE_SCENE_RECORDING_SAVED, &frame) ||
        strcmp(frame.resource_family, "recording.saved") != 0) {
        s_pet_performance_self_test_failure_code = 4u;
        return false;
    }
    if (!comp_pet_performance_recover_to_idle(&performance, &frame) ||
        !comp_pet_performance_begin(&performance, COMP_PET_PERFORMANCE_SCENE_VOICE_LISTENING, &frame) ||
        strcmp(frame.resource_family, "voice.listening") != 0 ||
        !comp_pet_performance_begin(&performance, COMP_PET_PERFORMANCE_SCENE_VOICE_SPEAKING, &frame) ||
        strcmp(frame.resource_family, "voice.speaking") != 0) {
        s_pet_performance_self_test_failure_code = 5u;
        return false;
    }
    if (!comp_pet_performance_recover_to_idle(&performance, &frame) ||
        frame.scene != COMP_PET_PERFORMANCE_SCENE_DAILY_IDLE ||
        frame.phase != COMP_PET_PERFORMANCE_PHASE_SUSTAINED ||
        !comp_pet_performance_begin(&performance, COMP_PET_PERFORMANCE_SCENE_SLEEP_ENTRY, &frame) ||
        !comp_pet_performance_begin(&performance, COMP_PET_PERFORMANCE_SCENE_DEEP_SLEEP, &frame) ||
        frame.phase != COMP_PET_PERFORMANCE_PHASE_SUSTAINED || frame.keyframe_count != 1u ||
        !comp_pet_performance_begin(&performance, COMP_PET_PERFORMANCE_SCENE_WAKE, &frame)) {
        s_pet_performance_self_test_failure_code = 6u;
        return false;
    }
    if (!comp_pet_performance_begin(&performance, COMP_PET_PERFORMANCE_SCENE_SYSTEM_ERROR, &frame) ||
        comp_pet_performance_begin(&performance, COMP_PET_PERFORMANCE_SCENE_CHARGING, &frame) ||
        !comp_pet_performance_recover_to_idle(&performance, &frame) ||
        comp_pet_performance_phase_is_supported(COMP_PET_PERFORMANCE_SCENE_DEEP_SLEEP,
                                                 COMP_PET_PERFORMANCE_PHASE_ENTRY) ||
        !comp_pet_performance_phase_is_supported(COMP_PET_PERFORMANCE_SCENE_RECORDING_ACTIVE,
                                                  COMP_PET_PERFORMANCE_PHASE_SETTLE) ||
        strcmp(comp_pet_performance_scene_name(COMP_PET_PERFORMANCE_SCENE_MENU_ENTER),
               "menu.enter") != 0 ||
        strcmp(comp_pet_performance_phase_name(COMP_PET_PERFORMANCE_PHASE_EXIT), "exit") != 0) {
        s_pet_performance_self_test_failure_code = 7u;
        return false;
    }
    return true;
}
