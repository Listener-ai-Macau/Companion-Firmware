#include "expression_state.h"

#include <stddef.h>
#include <string.h>

typedef struct {
    comp_epaper_expression_t expression;
    uint8_t priority;
    const char *name;
    const char *title;
    const char *body;
    const char *footer;
} comp_epaper_expression_def_t;

typedef struct {
    comp_epaper_expression_signal_t signal;
    comp_epaper_expression_t expression;
    bool may_lower_priority;
    const char *reason;
} comp_epaper_expression_signal_def_t;

static const comp_epaper_expression_def_t k_expression_defs[] = {
    {COMP_EPAPER_EXPRESSION_IDLE, 20u, "idle", "Idle", "Soft awake face", "EXPR IDLE"},
    {COMP_EPAPER_EXPRESSION_LISTENING, 60u, "listening", "Listening", "Ears open for the wake path", "EXPR LISTEN"},
    {COMP_EPAPER_EXPRESSION_THINKING, 50u, "thinking", "Thinking", "Processing the last prompt", "EXPR THINK"},
    {COMP_EPAPER_EXPRESSION_SPEAKING, 70u, "speaking", "Speaking", "Response audio is active", "EXPR SPEAK"},
    {COMP_EPAPER_EXPRESSION_HAPPY, 30u, "happy", "Happy", "Positive acknowledgement", "EXPR HAPPY"},
    {COMP_EPAPER_EXPRESSION_SLEEPY, 10u, "sleepy", "Sleepy", "Low attention idle mode", "EXPR SLEEP"},
    {COMP_EPAPER_EXPRESSION_RECORDING, 90u, "recording", "Recording", "Capture indicator stays visible", "EXPR REC"},
    {COMP_EPAPER_EXPRESSION_SYNC_COMPLETE, 40u, "sync_complete", "Synced", "Transfer finished cleanly", "EXPR SYNC"},
    {COMP_EPAPER_EXPRESSION_LOW_BATTERY, 80u, "low_battery", "Battery", "Charge soon", "EXPR LOW"},
    {COMP_EPAPER_EXPRESSION_ERROR, 100u, "error", "Error", "Needs user or host recovery", "EXPR ERROR"},
};

static const comp_epaper_expression_signal_def_t k_signal_defs[] = {
    {COMP_EPAPER_EXPRESSION_SIGNAL_BOOT_IDLE, COMP_EPAPER_EXPRESSION_IDLE, true, "boot/default screen"},
    {COMP_EPAPER_EXPRESSION_SIGNAL_WAKE_ARMED, COMP_EPAPER_EXPRESSION_IDLE, false, "wake word armed"},
    {COMP_EPAPER_EXPRESSION_SIGNAL_WAKE_DISABLED, COMP_EPAPER_EXPRESSION_SLEEPY, false, "wake word disabled"},
    {COMP_EPAPER_EXPRESSION_SIGNAL_WAKE_DETECTED, COMP_EPAPER_EXPRESSION_LISTENING, false, "wake word detected"},
    {COMP_EPAPER_EXPRESSION_SIGNAL_SPEAKER_PROMPT, COMP_EPAPER_EXPRESSION_SPEAKING, false, "speaker prompt accepted"},
    {COMP_EPAPER_EXPRESSION_SIGNAL_SPEAKER_RESULT, COMP_EPAPER_EXPRESSION_HAPPY, true, "speaker prompt completed"},
    {COMP_EPAPER_EXPRESSION_SIGNAL_MEETING_START, COMP_EPAPER_EXPRESSION_RECORDING, false, "meeting capture started"},
    {COMP_EPAPER_EXPRESSION_SIGNAL_MEETING_STOP, COMP_EPAPER_EXPRESSION_THINKING, true, "meeting capture stopped"},
    {COMP_EPAPER_EXPRESSION_SIGNAL_MEETING_FINALIZE, COMP_EPAPER_EXPRESSION_SYNC_COMPLETE, true, "meeting artifact finalized"},
    {COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_START, COMP_EPAPER_EXPRESSION_RECORDING, false, "recording start accepted"},
    {COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_STOP, COMP_EPAPER_EXPRESSION_THINKING, true, "recording stop accepted"},
    {COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_CANCEL, COMP_EPAPER_EXPRESSION_IDLE, true, "recording cancelled"},
    {COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_FINISHED, COMP_EPAPER_EXPRESSION_SYNC_COMPLETE, true, "recording stored for sync"},
    {COMP_EPAPER_EXPRESSION_SIGNAL_LOW_BATTERY, COMP_EPAPER_EXPRESSION_LOW_BATTERY, false, "battery is below threshold"},
    {COMP_EPAPER_EXPRESSION_SIGNAL_RECOVERY, COMP_EPAPER_EXPRESSION_IDLE, true, "recovered to idle"},
    {COMP_EPAPER_EXPRESSION_SIGNAL_ERROR, COMP_EPAPER_EXPRESSION_ERROR, false, "error or rejection"},
    {COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY, COMP_EPAPER_EXPRESSION_SLEEPY, false, "quiet hours or display-off screen setting"},
    {COMP_EPAPER_EXPRESSION_SIGNAL_BATTERY_RECOVERED, COMP_EPAPER_EXPRESSION_IDLE, false, "battery recovered above expression threshold"},
};

static const comp_epaper_expression_def_t *find_expression(comp_epaper_expression_t expression)
{
    for (size_t index = 0u; index < sizeof(k_expression_defs) / sizeof(k_expression_defs[0]); ++index) {
        if (k_expression_defs[index].expression == expression) {
            return &k_expression_defs[index];
        }
    }
    return NULL;
}

static const comp_epaper_expression_signal_def_t *find_signal(comp_epaper_expression_signal_t signal)
{
    for (size_t index = 0u; index < sizeof(k_signal_defs) / sizeof(k_signal_defs[0]); ++index) {
        if (k_signal_defs[index].signal == signal) {
            return &k_signal_defs[index];
        }
    }
    return NULL;
}

static bool can_apply_lower_priority_signal(
    const comp_epaper_expression_state_t *state,
    const comp_epaper_expression_signal_def_t *signal_def)
{
    if (signal_def->signal == COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY &&
        state->current == COMP_EPAPER_EXPRESSION_IDLE) {
        return true;
    }
    if (signal_def->signal == COMP_EPAPER_EXPRESSION_SIGNAL_BATTERY_RECOVERED &&
        state->current == COMP_EPAPER_EXPRESSION_LOW_BATTERY) {
        return true;
    }
    return signal_def->may_lower_priority;
}

static uint32_t fnv1a_u8(uint32_t hash, uint8_t value)
{
    hash ^= value;
    hash *= 16777619u;
    return hash;
}

static uint32_t fnv1a_text(uint32_t hash, const char *text)
{
    if (text == NULL) {
        return hash;
    }
    while (*text != '\0') {
        hash = fnv1a_u8(hash, (uint8_t)*text);
        text++;
    }
    return hash;
}

void comp_epaper_expression_state_init(comp_epaper_expression_state_t *state)
{
    if (state == NULL) {
        return;
    }
    state->current = COMP_EPAPER_EXPRESSION_IDLE;
    state->last_signal = COMP_EPAPER_EXPRESSION_SIGNAL_BOOT_IDLE;
    state->priority = comp_epaper_expression_priority(COMP_EPAPER_EXPRESSION_IDLE);
    state->revision = 0u;
    state->visible_age_ms = 0u;
    state->suppressed_duplicate_count = 0u;
    state->initialized = false;
}

bool comp_epaper_expression_is_supported(comp_epaper_expression_t expression)
{
    return find_expression(expression) != NULL;
}

bool comp_epaper_expression_signal_is_supported(comp_epaper_expression_signal_t signal)
{
    return find_signal(signal) != NULL;
}

const char *comp_epaper_expression_name(comp_epaper_expression_t expression)
{
    const comp_epaper_expression_def_t *def = find_expression(expression);
    return def == NULL ? "unknown" : def->name;
}

uint8_t comp_epaper_expression_priority(comp_epaper_expression_t expression)
{
    const comp_epaper_expression_def_t *def = find_expression(expression);
    return def == NULL ? 0u : def->priority;
}

uint32_t comp_epaper_expression_auto_recover_ms(comp_epaper_expression_t expression)
{
    switch (expression) {
    case COMP_EPAPER_EXPRESSION_LISTENING:
        return COMP_EPAPER_EXPRESSION_AUTO_RECOVER_LISTENING_MS;
    case COMP_EPAPER_EXPRESSION_THINKING:
        return COMP_EPAPER_EXPRESSION_AUTO_RECOVER_THINKING_MS;
    case COMP_EPAPER_EXPRESSION_SPEAKING:
        return COMP_EPAPER_EXPRESSION_AUTO_RECOVER_SPEAKING_MS;
    case COMP_EPAPER_EXPRESSION_HAPPY:
        return COMP_EPAPER_EXPRESSION_AUTO_RECOVER_HAPPY_MS;
    case COMP_EPAPER_EXPRESSION_SYNC_COMPLETE:
        return COMP_EPAPER_EXPRESSION_AUTO_RECOVER_SYNC_COMPLETE_MS;
    default:
        return COMP_EPAPER_EXPRESSION_AUTO_RECOVER_DISABLED_MS;
    }
}

bool comp_epaper_expression_decide(comp_epaper_expression_signal_t signal,
                                   comp_epaper_expression_decision_t *out_decision)
{
    const comp_epaper_expression_signal_def_t *signal_def = find_signal(signal);
    const comp_epaper_expression_def_t *expression_def;
    if (signal_def == NULL || out_decision == NULL) {
        return false;
    }
    expression_def = find_expression(signal_def->expression);
    if (expression_def == NULL) {
        return false;
    }
    out_decision->expression = expression_def->expression;
    out_decision->signal = signal;
    out_decision->priority = expression_def->priority;
    out_decision->name = expression_def->name;
    out_decision->title = expression_def->title;
    out_decision->body = expression_def->body;
    out_decision->footer = expression_def->footer;
    out_decision->reason = signal_def->reason;
    return true;
}

bool comp_epaper_expression_state_apply_signal(
    comp_epaper_expression_state_t *state,
    comp_epaper_expression_signal_t signal,
    comp_epaper_expression_decision_t *out_decision)
{
    comp_epaper_expression_decision_t decision;
    const comp_epaper_expression_signal_def_t *signal_def = find_signal(signal);

    if (state == NULL || out_decision == NULL || signal_def == NULL) {
        return false;
    }
    if (!comp_epaper_expression_decide(signal, &decision)) {
        return false;
    }
    if (signal_def->signal == COMP_EPAPER_EXPRESSION_SIGNAL_BATTERY_RECOVERED &&
        (!state->initialized || state->current != COMP_EPAPER_EXPRESSION_LOW_BATTERY)) {
        return false;
    }
    if (state->initialized && decision.expression == state->current) {
        state->last_signal = signal;
        state->visible_age_ms = 0u;
        state->suppressed_duplicate_count++;
        return false;
    }
    if (state->initialized &&
        decision.priority < state->priority &&
        !can_apply_lower_priority_signal(state, signal_def)) {
        return false;
    }

    state->current = decision.expression;
    state->last_signal = signal;
    state->priority = decision.priority;
    state->revision++;
    state->visible_age_ms = 0u;
    state->initialized = true;
    *out_decision = decision;
    return true;
}

bool comp_epaper_expression_state_tick(
    comp_epaper_expression_state_t *state,
    uint32_t elapsed_ms,
    comp_epaper_expression_decision_t *out_decision)
{
    comp_epaper_expression_decision_t decision;
    uint32_t recover_ms;

    if (state == NULL || out_decision == NULL || !state->initialized) {
        return false;
    }
    if (elapsed_ms > UINT32_MAX - state->visible_age_ms) {
        state->visible_age_ms = UINT32_MAX;
    } else {
        state->visible_age_ms += elapsed_ms;
    }

    recover_ms = comp_epaper_expression_auto_recover_ms(state->current);
    if (recover_ms == COMP_EPAPER_EXPRESSION_AUTO_RECOVER_DISABLED_MS ||
        state->visible_age_ms < recover_ms) {
        return false;
    }
    if (!comp_epaper_expression_decide(COMP_EPAPER_EXPRESSION_SIGNAL_RECOVERY,
                                       &decision)) {
        return false;
    }

    state->current = decision.expression;
    state->last_signal = COMP_EPAPER_EXPRESSION_SIGNAL_RECOVERY;
    state->priority = decision.priority;
    state->revision++;
    state->visible_age_ms = 0u;
    state->initialized = true;
    *out_decision = decision;
    return true;
}

void comp_epaper_expression_state_snapshot(
    const comp_epaper_expression_state_t *state,
    comp_epaper_expression_state_snapshot_t *out_snapshot)
{
    if (out_snapshot == NULL) {
        return;
    }

    memset(out_snapshot, 0, sizeof(*out_snapshot));
    if (state == NULL) {
        return;
    }

    out_snapshot->initialized = state->initialized;
    out_snapshot->current = state->current;
    out_snapshot->last_signal = state->last_signal;
    out_snapshot->priority = state->priority;
    out_snapshot->revision = state->revision;
    out_snapshot->visible_age_ms = state->visible_age_ms;
    out_snapshot->auto_recover_ms = comp_epaper_expression_auto_recover_ms(state->current);
    out_snapshot->suppressed_duplicate_count = state->suppressed_duplicate_count;
}

uint32_t comp_epaper_expression_decision_crc32(
    const comp_epaper_expression_decision_t *decision)
{
    uint32_t hash = 2166136261u;
    if (decision == NULL) {
        return 0u;
    }
    hash = fnv1a_text(hash, decision->name);
    hash = fnv1a_u8(hash, (uint8_t)decision->expression);
    hash = fnv1a_u8(hash, (uint8_t)decision->signal);
    hash = fnv1a_u8(hash, decision->priority);
    return hash == 0u ? 1u : hash;
}
