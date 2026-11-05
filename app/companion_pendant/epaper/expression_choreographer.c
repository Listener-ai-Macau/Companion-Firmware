#include "expression_choreographer.h"

#include <stddef.h>
#include <string.h>

static bool profile_is_valid(const comp_expression_rig_profile_t *profile)
{
    return profile != NULL && profile->components != NULL &&
           profile->component_count > 0u && profile->component_count <= 255u;
}

static bool input_is_valid(const comp_expression_rig_choreography_input_t *input)
{
    return input != NULL && input->event < COMP_EXPRESSION_RIG_EVENT_COUNT &&
           input->attention < COMP_EXPRESSION_RIG_ATTENTION_COUNT &&
           input->energy < COMP_EXPRESSION_RIG_ENERGY_COUNT &&
           input->interaction_memory <= 2u &&
           input->phase < COMP_EXPRESSION_RIG_PHASE_COUNT &&
           (!input->has_requested_emotion ||
            input->requested_emotion < COMP_EXPRESSION_RIG_EMOTION_COUNT);
}

bool comp_expression_rig_affect_is_valid(const comp_expression_rig_affect_state_t *affect)
{
    return affect != NULL && affect->valence >= -2 && affect->valence <= 2 &&
           affect->arousal <= 3u && affect->affinity <= 2u &&
           affect->baseline < COMP_EXPRESSION_RIG_EMOTION_COUNT;
}

const char *comp_expression_rig_intent_name(comp_expression_rig_intent_t intent)
{
    switch (intent) {
    case COMP_EXPRESSION_RIG_INTENT_PRESENCE: return "presence";
    case COMP_EXPRESSION_RIG_INTENT_NOTICE: return "notice";
    case COMP_EXPRESSION_RIG_INTENT_CURIOUS_RESPONSE: return "curious_response";
    case COMP_EXPRESSION_RIG_INTENT_WARM_RESPONSE: return "warm_response";
    case COMP_EXPRESSION_RIG_INTENT_PLAYFUL_RESPONSE: return "playful_response";
    case COMP_EXPRESSION_RIG_INTENT_PROCESSING: return "processing";
    case COMP_EXPRESSION_RIG_INTENT_TASK_FOCUS: return "task_focus";
    case COMP_EXPRESSION_RIG_INTENT_ALERT_RESPONSE: return "alert_response";
    default: return "unknown";
    }
}

const char *comp_expression_rig_intent_reason_name(comp_expression_rig_intent_reason_t reason)
{
    switch (reason) {
    case COMP_EXPRESSION_RIG_INTENT_REASON_IDLE_PRESENCE: return "idle_presence";
    case COMP_EXPRESSION_RIG_INTENT_REASON_EVENT_APPRAISAL: return "event_appraisal";
    case COMP_EXPRESSION_RIG_INTENT_REASON_EXPLICIT_REQUEST: return "explicit_request";
    case COMP_EXPRESSION_RIG_INTENT_REASON_ACTIVE_INTENT_HOLD: return "active_intent_hold";
    default: return "unknown";
    }
}

bool comp_expression_rig_behavior_state_is_valid(const comp_expression_rig_behavior_state_t *state)
{
    return state != NULL && comp_expression_rig_affect_is_valid(&state->affect) &&
           state->active_intent < COMP_EXPRESSION_RIG_INTENT_COUNT &&
           state->remaining_hold_steps <= COMP_EXPRESSION_RIG_MIN_INTENT_HOLD_STEPS;
}

static int8_t clamp_valence(int8_t value)
{
    if (value < -2) {
        return -2;
    }
    if (value > 2) {
        return 2;
    }
    return value;
}

static uint8_t clamp_arousal(uint8_t value)
{
    return value > 3u ? 3u : value;
}

static int8_t valence_toward_neutral(int8_t value)
{
    return value > 0 ? (int8_t)(value - 1) : value < 0 ? (int8_t)(value + 1) : 0;
}

bool comp_expression_rig_affect_update(
    const comp_expression_rig_affect_state_t *current,
    const comp_expression_rig_choreography_input_t *input,
    comp_expression_rig_affect_state_t *out_next)
{
    comp_expression_rig_affect_state_t next;

    if (!comp_expression_rig_affect_is_valid(current) || !input_is_valid(input) || out_next == NULL) {
        return false;
    }
    next = *current;
    if (input->interaction_memory > next.affinity) {
        next.affinity = input->interaction_memory;
    }
    switch (input->event) {
    case COMP_EXPRESSION_RIG_EVENT_DAILY_AUTO:
        next.valence = valence_toward_neutral(next.valence);
        if (next.arousal > 1u) {
            --next.arousal;
        }
        if (input->interaction_memory < next.affinity && next.affinity > 0u) {
            --next.affinity;
        }
        break;
    case COMP_EXPRESSION_RIG_EVENT_TOUCH_TAP:
        next.valence = clamp_valence((int8_t)(next.valence + 1));
        if (next.arousal < 2u) {
            next.arousal = 2u;
        }
        break;
    case COMP_EXPRESSION_RIG_EVENT_TOUCH_SWIPE:
        next.valence = clamp_valence((int8_t)(next.valence + 1));
        next.arousal = clamp_arousal((uint8_t)(next.arousal + 1u));
        if (next.arousal < 2u) {
            next.arousal = 2u;
        }
        break;
    case COMP_EXPRESSION_RIG_EVENT_RECORDING_ACTIVE:
        next.valence = valence_toward_neutral(next.valence);
        if (next.arousal < 2u) {
            next.arousal = 2u;
        }
        break;
    case COMP_EXPRESSION_RIG_EVENT_MENU_HOLD:
    case COMP_EXPRESSION_RIG_EVENT_UPGRADE_ACTIVE:
        next.valence = valence_toward_neutral(next.valence);
        if (next.arousal < 1u) {
            next.arousal = 1u;
        }
        break;
    case COMP_EXPRESSION_RIG_EVENT_SLEEP:
        next.arousal = 0u;
        break;
    case COMP_EXPRESSION_RIG_EVENT_WAKE:
        next.arousal = 2u;
        break;
    case COMP_EXPRESSION_RIG_EVENT_CHARGING:
        next.arousal = 0u;
        break;
    case COMP_EXPRESSION_RIG_EVENT_ERROR:
        next.valence = clamp_valence((int8_t)(next.valence - 1));
        next.arousal = 3u;
        break;
    default:
        return false;
    }
    *out_next = next;
    return true;
}

bool comp_expression_rig_affect_target_emotion(
    const comp_expression_rig_affect_state_t *affect,
    const comp_expression_rig_choreography_input_t *input,
    comp_expression_rig_emotion_t *out_emotion)
{
    if (!comp_expression_rig_affect_is_valid(affect) || !input_is_valid(input) || out_emotion == NULL) {
        return false;
    }
    switch (input->event) {
    case COMP_EXPRESSION_RIG_EVENT_RECORDING_ACTIVE:
        *out_emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED;
        return true;
    case COMP_EXPRESSION_RIG_EVENT_MENU_HOLD:
        *out_emotion = COMP_EXPRESSION_RIG_EMOTION_THINKING;
        return true;
    case COMP_EXPRESSION_RIG_EVENT_UPGRADE_ACTIVE:
    case COMP_EXPRESSION_RIG_EVENT_CHARGING:
        *out_emotion = COMP_EXPRESSION_RIG_EMOTION_CALM;
        return true;
    case COMP_EXPRESSION_RIG_EVENT_ERROR:
        *out_emotion = COMP_EXPRESSION_RIG_EMOTION_ALERT;
        return true;
    case COMP_EXPRESSION_RIG_EVENT_SLEEP:
        *out_emotion = COMP_EXPRESSION_RIG_EMOTION_SLEEPY;
        return true;
    case COMP_EXPRESSION_RIG_EVENT_WAKE:
        *out_emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS;
        return true;
    case COMP_EXPRESSION_RIG_EVENT_TOUCH_TAP:
        *out_emotion = affect->affinity >= 2u && affect->valence >= 1
                           ? COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE
                           : COMP_EXPRESSION_RIG_EMOTION_CURIOUS;
        return true;
    case COMP_EXPRESSION_RIG_EVENT_TOUCH_SWIPE:
        if (input->energy == COMP_EXPRESSION_RIG_ENERGY_HIGH && affect->affinity >= 2u &&
            affect->valence >= 0) {
            *out_emotion = COMP_EXPRESSION_RIG_EMOTION_PLAYFUL;
        } else if (affect->affinity >= 2u && affect->valence >= 1) {
            *out_emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE;
        } else {
            *out_emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS;
        }
        return true;
    case COMP_EXPRESSION_RIG_EVENT_DAILY_AUTO:
        if (affect->valence < 0) {
            *out_emotion = affect->arousal >= 2u ? COMP_EXPRESSION_RIG_EMOTION_PUZZLED
                                                  : COMP_EXPRESSION_RIG_EMOTION_CALM;
        } else if (affect->arousal >= 3u) {
            *out_emotion = affect->affinity >= 2u && affect->valence >= 1
                               ? COMP_EXPRESSION_RIG_EMOTION_PLAYFUL
                               : COMP_EXPRESSION_RIG_EMOTION_ANTICIPATORY;
        } else if (affect->valence >= 2 && affect->affinity >= 2u) {
            *out_emotion = COMP_EXPRESSION_RIG_EMOTION_JOYFUL;
        } else if (affect->affinity >= 2u && affect->valence >= 1) {
            *out_emotion = COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE;
        } else if (affect->arousal >= 2u) {
            *out_emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS;
        } else {
            *out_emotion = COMP_EXPRESSION_RIG_EMOTION_CALM;
        }
        return true;
    default:
        return false;
    }
}

bool comp_expression_rig_emotion_transition_allowed(
    comp_expression_rig_emotion_t from,
    comp_expression_rig_emotion_t to)
{
    if (from >= COMP_EXPRESSION_RIG_EMOTION_COUNT || to >= COMP_EXPRESSION_RIG_EMOTION_COUNT || from == to) {
        return false;
    }
    switch (from) {
    case COMP_EXPRESSION_RIG_EMOTION_CALM:
        return to == COMP_EXPRESSION_RIG_EMOTION_CURIOUS || to == COMP_EXPRESSION_RIG_EMOTION_LISTENING ||
               to == COMP_EXPRESSION_RIG_EMOTION_SLEEPY;
    case COMP_EXPRESSION_RIG_EMOTION_CURIOUS:
        return to == COMP_EXPRESSION_RIG_EMOTION_CALM || to == COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE ||
               to == COMP_EXPRESSION_RIG_EMOTION_ANTICIPATORY || to == COMP_EXPRESSION_RIG_EMOTION_PUZZLED ||
               to == COMP_EXPRESSION_RIG_EMOTION_THINKING || to == COMP_EXPRESSION_RIG_EMOTION_ALERT ||
               to == COMP_EXPRESSION_RIG_EMOTION_FOCUSED;
    case COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE:
        return to == COMP_EXPRESSION_RIG_EMOTION_CALM || to == COMP_EXPRESSION_RIG_EMOTION_CURIOUS ||
               to == COMP_EXPRESSION_RIG_EMOTION_JOYFUL || to == COMP_EXPRESSION_RIG_EMOTION_PLAYFUL;
    case COMP_EXPRESSION_RIG_EMOTION_FOCUSED:
        return to == COMP_EXPRESSION_RIG_EMOTION_LISTENING || to == COMP_EXPRESSION_RIG_EMOTION_THINKING ||
               to == COMP_EXPRESSION_RIG_EMOTION_ALERT || to == COMP_EXPRESSION_RIG_EMOTION_CALM;
    case COMP_EXPRESSION_RIG_EMOTION_SLEEPY:
        return to == COMP_EXPRESSION_RIG_EMOTION_CALM;
    case COMP_EXPRESSION_RIG_EMOTION_ALERT:
        return to == COMP_EXPRESSION_RIG_EMOTION_CURIOUS || to == COMP_EXPRESSION_RIG_EMOTION_FOCUSED ||
               to == COMP_EXPRESSION_RIG_EMOTION_ANTICIPATORY || to == COMP_EXPRESSION_RIG_EMOTION_CALM;
    case COMP_EXPRESSION_RIG_EMOTION_JOYFUL:
        return to == COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE || to == COMP_EXPRESSION_RIG_EMOTION_PLAYFUL ||
               to == COMP_EXPRESSION_RIG_EMOTION_ANTICIPATORY || to == COMP_EXPRESSION_RIG_EMOTION_CALM;
    case COMP_EXPRESSION_RIG_EMOTION_PLAYFUL:
        return to == COMP_EXPRESSION_RIG_EMOTION_JOYFUL || to == COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE ||
               to == COMP_EXPRESSION_RIG_EMOTION_CURIOUS || to == COMP_EXPRESSION_RIG_EMOTION_CALM;
    case COMP_EXPRESSION_RIG_EMOTION_ANTICIPATORY:
        return to == COMP_EXPRESSION_RIG_EMOTION_CURIOUS || to == COMP_EXPRESSION_RIG_EMOTION_ALERT ||
               to == COMP_EXPRESSION_RIG_EMOTION_FOCUSED || to == COMP_EXPRESSION_RIG_EMOTION_JOYFUL ||
               to == COMP_EXPRESSION_RIG_EMOTION_CALM;
    case COMP_EXPRESSION_RIG_EMOTION_PUZZLED:
        return to == COMP_EXPRESSION_RIG_EMOTION_CURIOUS || to == COMP_EXPRESSION_RIG_EMOTION_THINKING ||
               to == COMP_EXPRESSION_RIG_EMOTION_ALERT || to == COMP_EXPRESSION_RIG_EMOTION_CALM;
    case COMP_EXPRESSION_RIG_EMOTION_LISTENING:
        return to == COMP_EXPRESSION_RIG_EMOTION_FOCUSED || to == COMP_EXPRESSION_RIG_EMOTION_CURIOUS ||
               to == COMP_EXPRESSION_RIG_EMOTION_CALM;
    case COMP_EXPRESSION_RIG_EMOTION_THINKING:
        return to == COMP_EXPRESSION_RIG_EMOTION_PUZZLED || to == COMP_EXPRESSION_RIG_EMOTION_CURIOUS ||
               to == COMP_EXPRESSION_RIG_EMOTION_FOCUSED || to == COMP_EXPRESSION_RIG_EMOTION_CALM;
    default:
        return false;
    }
}

bool comp_expression_rig_emotion_transition_route(
    comp_expression_rig_emotion_t from,
    comp_expression_rig_emotion_t to,
    comp_expression_rig_emotion_route_t *out_route)
{
    uint8_t queue[COMP_EXPRESSION_RIG_EMOTION_COUNT];
    int8_t parent[COMP_EXPRESSION_RIG_EMOTION_COUNT];
    uint8_t head = 0u;
    uint8_t tail = 0u;
    uint8_t index;
    uint8_t cursor;
    uint8_t reversed[COMP_EXPRESSION_RIG_MAX_EMOTION_ROUTE];
    uint8_t count = 0u;

    if (out_route == NULL || from >= COMP_EXPRESSION_RIG_EMOTION_COUNT || to >= COMP_EXPRESSION_RIG_EMOTION_COUNT) {
        return false;
    }
    memset(out_route, 0, sizeof(*out_route));
    if (from == to) {
        out_route->emotions[0] = from;
        out_route->count = 1u;
        return true;
    }
    for (index = 0u; index < COMP_EXPRESSION_RIG_EMOTION_COUNT; ++index) {
        parent[index] = -1;
    }
    parent[from] = (int8_t)from;
    queue[tail++] = (uint8_t)from;
    while (head < tail && parent[to] == -1) {
        uint8_t current = queue[head++];

        for (index = 0u; index < COMP_EXPRESSION_RIG_EMOTION_COUNT; ++index) {
            if (parent[index] == -1 && comp_expression_rig_emotion_transition_allowed(
                    (comp_expression_rig_emotion_t)current, (comp_expression_rig_emotion_t)index)) {
                parent[index] = (int8_t)current;
                queue[tail++] = index;
                if (index == (uint8_t)to) {
                    break;
                }
            }
        }
    }
    if (parent[to] == -1) {
        return false;
    }
    cursor = (uint8_t)to;
    while (count < COMP_EXPRESSION_RIG_MAX_EMOTION_ROUTE) {
        reversed[count++] = cursor;
        if (cursor == (uint8_t)from) {
            break;
        }
        cursor = (uint8_t)parent[cursor];
    }
    if (count == COMP_EXPRESSION_RIG_MAX_EMOTION_ROUTE && reversed[count - 1u] != (uint8_t)from) {
        return false;
    }
    for (index = 0u; index < count; ++index) {
        out_route->emotions[index] = (comp_expression_rig_emotion_t)reversed[count - index - 1u];
    }
    out_route->count = count;
    return true;
}

static uint8_t event_priority(comp_expression_rig_event_t event)
{
    switch (event) {
    case COMP_EXPRESSION_RIG_EVENT_ERROR: return 100u;
    case COMP_EXPRESSION_RIG_EVENT_RECORDING_ACTIVE:
    case COMP_EXPRESSION_RIG_EVENT_MENU_HOLD:
    case COMP_EXPRESSION_RIG_EVENT_UPGRADE_ACTIVE: return 90u;
    case COMP_EXPRESSION_RIG_EVENT_SLEEP: return 80u;
    case COMP_EXPRESSION_RIG_EVENT_WAKE: return 70u;
    case COMP_EXPRESSION_RIG_EVENT_TOUCH_SWIPE: return 50u;
    case COMP_EXPRESSION_RIG_EVENT_TOUCH_TAP: return 40u;
    case COMP_EXPRESSION_RIG_EVENT_CHARGING: return 30u;
    case COMP_EXPRESSION_RIG_EVENT_DAILY_AUTO: return 0u;
    default: return 0u;
    }
}

static uint8_t intent_priority(comp_expression_rig_intent_t intent)
{
    switch (intent) {
    case COMP_EXPRESSION_RIG_INTENT_ALERT_RESPONSE: return 100u;
    case COMP_EXPRESSION_RIG_INTENT_TASK_FOCUS: return 90u;
    case COMP_EXPRESSION_RIG_INTENT_NOTICE: return 70u;
    case COMP_EXPRESSION_RIG_INTENT_PROCESSING: return 60u;
    case COMP_EXPRESSION_RIG_INTENT_PLAYFUL_RESPONSE: return 50u;
    case COMP_EXPRESSION_RIG_INTENT_WARM_RESPONSE: return 45u;
    case COMP_EXPRESSION_RIG_INTENT_CURIOUS_RESPONSE: return 40u;
    case COMP_EXPRESSION_RIG_INTENT_PRESENCE: return 0u;
    default: return 0u;
    }
}

static comp_expression_rig_intent_t intent_for(
    comp_expression_rig_event_t event,
    comp_expression_rig_emotion_t target)
{
    switch (event) {
    case COMP_EXPRESSION_RIG_EVENT_DAILY_AUTO: return COMP_EXPRESSION_RIG_INTENT_PRESENCE;
    case COMP_EXPRESSION_RIG_EVENT_WAKE: return COMP_EXPRESSION_RIG_INTENT_NOTICE;
    case COMP_EXPRESSION_RIG_EVENT_RECORDING_ACTIVE:
    case COMP_EXPRESSION_RIG_EVENT_MENU_HOLD:
    case COMP_EXPRESSION_RIG_EVENT_UPGRADE_ACTIVE:
    case COMP_EXPRESSION_RIG_EVENT_SLEEP:
    case COMP_EXPRESSION_RIG_EVENT_CHARGING: return COMP_EXPRESSION_RIG_INTENT_TASK_FOCUS;
    case COMP_EXPRESSION_RIG_EVENT_ERROR: return COMP_EXPRESSION_RIG_INTENT_ALERT_RESPONSE;
    case COMP_EXPRESSION_RIG_EVENT_TOUCH_SWIPE:
        return target == COMP_EXPRESSION_RIG_EMOTION_PLAYFUL
                   ? COMP_EXPRESSION_RIG_INTENT_PLAYFUL_RESPONSE
                   : target == COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE
                         ? COMP_EXPRESSION_RIG_INTENT_WARM_RESPONSE
                         : COMP_EXPRESSION_RIG_INTENT_CURIOUS_RESPONSE;
    case COMP_EXPRESSION_RIG_EVENT_TOUCH_TAP:
        return target == COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE
                   ? COMP_EXPRESSION_RIG_INTENT_WARM_RESPONSE
                   : COMP_EXPRESSION_RIG_INTENT_CURIOUS_RESPONSE;
    default:
        return COMP_EXPRESSION_RIG_INTENT_PROCESSING;
    }
}

bool comp_expression_rig_resolve_behavior(
    const comp_expression_rig_behavior_state_t *current,
    const comp_expression_rig_choreography_input_t *input,
    comp_expression_rig_behavior_state_t *out_next,
    comp_expression_rig_behavior_decision_t *out_decision)
{
    comp_expression_rig_behavior_state_t next;
    comp_expression_rig_emotion_t target;
    comp_expression_rig_intent_t intent;
    comp_expression_rig_intent_reason_t reason;
    uint8_t priority;
    uint8_t active_priority;

    if (!comp_expression_rig_behavior_state_is_valid(current) || !input_is_valid(input) ||
        out_next == NULL || out_decision == NULL ||
        !comp_expression_rig_affect_update(&current->affect, input, &next.affect)) {
        return false;
    }
    priority = event_priority(input->event);
    active_priority = intent_priority(current->active_intent);
    next.active_intent = current->active_intent;
    next.remaining_hold_steps = current->remaining_hold_steps;

    if (input->event == COMP_EXPRESSION_RIG_EVENT_DAILY_AUTO) {
        if (next.remaining_hold_steps > 0u) {
            --next.remaining_hold_steps;
        }
        if (next.remaining_hold_steps == 0u) {
            next.active_intent = COMP_EXPRESSION_RIG_INTENT_PRESENCE;
        }
        target = current->affect.baseline;
        intent = COMP_EXPRESSION_RIG_INTENT_PRESENCE;
        reason = COMP_EXPRESSION_RIG_INTENT_REASON_IDLE_PRESENCE;
    } else if (current->remaining_hold_steps > 0u && priority <= active_priority) {
        target = current->affect.baseline;
        intent = current->active_intent;
        reason = COMP_EXPRESSION_RIG_INTENT_REASON_ACTIVE_INTENT_HOLD;
    } else {
        if (input->has_requested_emotion) {
            target = input->requested_emotion;
            reason = COMP_EXPRESSION_RIG_INTENT_REASON_EXPLICIT_REQUEST;
        } else if (!comp_expression_rig_affect_target_emotion(&next.affect, input, &target)) {
            return false;
        } else {
            reason = COMP_EXPRESSION_RIG_INTENT_REASON_EVENT_APPRAISAL;
        }
        intent = intent_for(input->event, target);
        next.affect.baseline = target;
        next.active_intent = intent;
        next.remaining_hold_steps = COMP_EXPRESSION_RIG_MIN_INTENT_HOLD_STEPS;
    }

    if (!comp_expression_rig_emotion_transition_route(current->affect.baseline, target,
                                                       &out_decision->route)) {
        return false;
    }
    out_decision->intent = intent;
    out_decision->reason = reason;
    out_decision->target_emotion = target;
    out_decision->target_attention = input->attention;
    out_decision->event_priority = priority;
    out_decision->cancels_active_intent = current->active_intent != COMP_EXPRESSION_RIG_INTENT_PRESENCE &&
                                         priority > active_priority;
    *out_next = next;
    return true;
}

static bool profile_has_component_id(const comp_expression_rig_profile_t *profile,
                                     uint16_t component_id)
{
    size_t index;

    if (!profile_is_valid(profile) ||
        component_id == COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID) {
        return false;
    }
    for (index = 0u; index < profile->component_count; ++index) {
        if (profile->components[index].component_id == component_id) {
            return true;
        }
    }
    return false;
}

static bool profile_supports_scene(const comp_expression_rig_profile_t *profile,
                                   comp_expression_rig_scene_t scene)
{
    size_t index;

    if (profile == NULL || scene >= COMP_EXPRESSION_RIG_SCENE_COUNT) {
        return false;
    }
    if (profile->registered_poses != NULL && profile->registered_pose_count > 0u) {
        for (index = 0u; index < profile->registered_pose_count; ++index) {
            if (profile->registered_poses[index].scene == scene) {
                return true;
            }
        }
        return false;
    }
    return profile_has_component_id(profile, profile->scene_charm_component[scene]);
}

static comp_expression_rig_attention_t event_attention(
    const comp_expression_rig_choreography_input_t *input,
    comp_expression_rig_attention_t fallback)
{
    return input->attention == COMP_EXPRESSION_RIG_ATTENTION_CENTER
               ? fallback
               : input->attention;
}

static bool write_story_state(const comp_expression_rig_profile_t *profile,
                              const comp_expression_rig_choreography_input_t *input,
                              comp_expression_rig_state_t story_state,
                              comp_expression_rig_state_t *out_state)
{
    comp_expression_rig_state_t effective;
    comp_expression_rig_plan_t plan;

    if (!profile_supports_scene(profile, story_state.scene) ||
        !comp_expression_rig_story_state(&story_state, input->phase, &effective)) {
        return false;
    }
    if (!profile_supports_scene(profile, effective.scene)) {
        return false;
    }
    memset(out_state, 0, sizeof(*out_state));
    out_state->scene = effective.scene;
    out_state->emotion = effective.emotion;
    out_state->attention = effective.attention;
    out_state->energy = effective.energy;
    out_state->interaction_memory = effective.interaction_memory;
    out_state->phase = effective.phase;
    return comp_expression_rig_build_plan(profile, out_state, &plan);
}

const char *comp_expression_rig_event_name(comp_expression_rig_event_t event)
{
    switch (event) {
    case COMP_EXPRESSION_RIG_EVENT_DAILY_AUTO: return "daily_auto";
    case COMP_EXPRESSION_RIG_EVENT_TOUCH_TAP: return "touch_tap";
    case COMP_EXPRESSION_RIG_EVENT_TOUCH_SWIPE: return "touch_swipe";
    case COMP_EXPRESSION_RIG_EVENT_RECORDING_ACTIVE: return "recording_active";
    case COMP_EXPRESSION_RIG_EVENT_MENU_HOLD: return "menu_hold";
    case COMP_EXPRESSION_RIG_EVENT_SLEEP: return "sleep";
    case COMP_EXPRESSION_RIG_EVENT_WAKE: return "wake";
    case COMP_EXPRESSION_RIG_EVENT_CHARGING: return "charging";
    case COMP_EXPRESSION_RIG_EVENT_ERROR: return "error";
    case COMP_EXPRESSION_RIG_EVENT_UPGRADE_ACTIVE: return "upgrade_active";
    default: return "unknown";
    }
}

bool comp_expression_rig_choreograph(
    const comp_expression_rig_profile_t *profile,
    const comp_expression_rig_choreography_input_t *input,
    comp_expression_rig_state_t *out_state)
{
    comp_expression_rig_state_t story_state;

    if (!profile_is_valid(profile) || !input_is_valid(input) || out_state == NULL) {
        return false;
    }

    switch (input->event) {
    case COMP_EXPRESSION_RIG_EVENT_DAILY_AUTO:
        story_state = (comp_expression_rig_state_t){
            .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
            .emotion = input->interaction_memory == 2u ? COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE :
                       input->interaction_memory == 1u ? COMP_EXPRESSION_RIG_EMOTION_CURIOUS :
                                                         COMP_EXPRESSION_RIG_EMOTION_CALM,
            .attention = input->attention,
            .energy = input->energy,
            .interaction_memory = input->interaction_memory,
            .phase = input->phase,
        };
        break;
    case COMP_EXPRESSION_RIG_EVENT_TOUCH_TAP:
        story_state = (comp_expression_rig_state_t){
            /* Touch remains a causal event/intent, but its visual stays in
             * the approved Daily V9 grammar until a distinct complete touch
             * source pose passes its art gate. This prevents the rejected
             * question charm from becoming a hidden fallback face. */
            .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
            .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
            .attention = event_attention(input, COMP_EXPRESSION_RIG_ATTENTION_CENTER),
            .energy = input->energy,
            .interaction_memory = input->interaction_memory,
            .phase = input->phase,
        };
        break;
    case COMP_EXPRESSION_RIG_EVENT_TOUCH_SWIPE:
        story_state = (comp_expression_rig_state_t){
            .scene = COMP_EXPRESSION_RIG_SCENE_SWIPE,
            .emotion = input->interaction_memory == 2u
                            ? COMP_EXPRESSION_RIG_EMOTION_AFFECTIONATE
                            : COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
            .attention = event_attention(input, COMP_EXPRESSION_RIG_ATTENTION_CENTER),
            .energy = input->energy,
            .interaction_memory = input->interaction_memory,
            .phase = input->phase,
        };
        break;
    case COMP_EXPRESSION_RIG_EVENT_RECORDING_ACTIVE:
    case COMP_EXPRESSION_RIG_EVENT_MENU_HOLD:
    case COMP_EXPRESSION_RIG_EVENT_UPGRADE_ACTIVE:
        /* The V18/V19/V20 source poses are not owner-art accepted or bound.
         * Keep affect targets available to product logic, but never borrow a
         * generic scene while a dedicated special expression is unavailable. */
        return false;
    case COMP_EXPRESSION_RIG_EVENT_SLEEP:
        story_state = (comp_expression_rig_state_t){
            .scene = COMP_EXPRESSION_RIG_SCENE_SLEEP,
            .emotion = COMP_EXPRESSION_RIG_EMOTION_SLEEPY,
            .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
            .energy = COMP_EXPRESSION_RIG_ENERGY_LOW,
            .interaction_memory = 0u,
            .phase = input->phase,
        };
        break;
    case COMP_EXPRESSION_RIG_EVENT_WAKE:
        story_state = (comp_expression_rig_state_t){
            .scene = COMP_EXPRESSION_RIG_SCENE_DAILY,
            .emotion = COMP_EXPRESSION_RIG_EMOTION_CURIOUS,
            .attention = event_attention(input, COMP_EXPRESSION_RIG_ATTENTION_UP),
            .energy = COMP_EXPRESSION_RIG_ENERGY_HIGH,
            .interaction_memory = input->interaction_memory,
            .phase = input->phase,
        };
        break;
    case COMP_EXPRESSION_RIG_EVENT_CHARGING:
        story_state = (comp_expression_rig_state_t){
            .scene = COMP_EXPRESSION_RIG_SCENE_CHARGING,
            .emotion = COMP_EXPRESSION_RIG_EMOTION_CALM,
            .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
            .energy = COMP_EXPRESSION_RIG_ENERGY_LOW,
            .interaction_memory = 0u,
            .phase = input->phase,
        };
        break;
    case COMP_EXPRESSION_RIG_EVENT_ERROR:
        story_state = (comp_expression_rig_state_t){
            .scene = COMP_EXPRESSION_RIG_SCENE_ERROR,
            .emotion = COMP_EXPRESSION_RIG_EMOTION_FOCUSED,
            .attention = COMP_EXPRESSION_RIG_ATTENTION_CENTER,
            .energy = COMP_EXPRESSION_RIG_ENERGY_HIGH,
            .interaction_memory = 0u,
            .phase = input->phase,
        };
        break;
    default:
        return false;
    }

    if (input->has_requested_emotion) {
        story_state.emotion = input->requested_emotion;
        /* An explicit emotion request also makes CENTER an intentional gaze,
         * rather than the ordinary event fallback for an unspecified gaze. */
        story_state.attention = input->attention;
    }

    return write_story_state(profile, input, story_state, out_state);
}

bool comp_expression_rig_choreograph_plan(
    const comp_expression_rig_profile_t *profile,
    const comp_expression_rig_choreography_input_t *input,
    comp_expression_rig_plan_t *out_plan)
{
    comp_expression_rig_state_t state;

    if (out_plan == NULL ||
        !comp_expression_rig_choreograph(profile, input, &state)) {
        return false;
    }
    return comp_expression_rig_build_plan(profile, &state, out_plan);
}

bool comp_expression_rig_choreograph_daily_score_plan(
    const comp_expression_rig_profile_t *profile,
    const comp_expression_rig_choreography_input_t *input,
    const comp_expression_rig_performance_score_t *score,
    uint8_t step_index,
    comp_expression_rig_plan_t *out_plan)
{
    comp_expression_rig_choreography_input_t entry_input;
    comp_expression_rig_plan_t entry_plan;

    if (!profile_is_valid(profile) || !input_is_valid(input) || score == NULL || out_plan == NULL ||
        input->event != COMP_EXPRESSION_RIG_EVENT_DAILY_AUTO ||
        input->attention == COMP_EXPRESSION_RIG_ATTENTION_CENTER) {
        return false;
    }
    entry_input = *input;
    entry_input.phase = COMP_EXPRESSION_RIG_PHASE_ENTRY;
    if (!comp_expression_rig_choreograph_plan(profile, &entry_input, &entry_plan)) {
        return false;
    }
    return comp_expression_rig_apply_score_step(profile, &entry_plan, score, step_index, out_plan);
}
