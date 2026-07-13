#ifndef COMPANION_EPAPER_EXPRESSION_STATE_H
#define COMPANION_EPAPER_EXPRESSION_STATE_H

#include <stdbool.h>
#include <stdint.h>

#define COMP_EPAPER_EXPRESSION_AUTO_RECOVER_DISABLED_MS 0u
#define COMP_EPAPER_EXPRESSION_AUTO_RECOVER_LISTENING_MS 10000u
#define COMP_EPAPER_EXPRESSION_AUTO_RECOVER_THINKING_MS 12000u
#define COMP_EPAPER_EXPRESSION_AUTO_RECOVER_SPEAKING_MS 10000u
#define COMP_EPAPER_EXPRESSION_AUTO_RECOVER_HAPPY_MS 6000u
#define COMP_EPAPER_EXPRESSION_AUTO_RECOVER_SYNC_COMPLETE_MS 8000u

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    COMP_EPAPER_EXPRESSION_IDLE = 0,
    COMP_EPAPER_EXPRESSION_LISTENING = 1,
    COMP_EPAPER_EXPRESSION_THINKING = 2,
    COMP_EPAPER_EXPRESSION_SPEAKING = 3,
    COMP_EPAPER_EXPRESSION_HAPPY = 4,
    COMP_EPAPER_EXPRESSION_SLEEPY = 5,
    COMP_EPAPER_EXPRESSION_RECORDING = 6,
    COMP_EPAPER_EXPRESSION_SYNC_COMPLETE = 7,
    COMP_EPAPER_EXPRESSION_LOW_BATTERY = 8,
    COMP_EPAPER_EXPRESSION_ERROR = 9,
    COMP_EPAPER_EXPRESSION_COUNT = 10,
} comp_epaper_expression_t;

typedef enum {
    COMP_EPAPER_EXPRESSION_SIGNAL_BOOT_IDLE = 0,
    COMP_EPAPER_EXPRESSION_SIGNAL_WAKE_ARMED = 1,
    COMP_EPAPER_EXPRESSION_SIGNAL_WAKE_DISABLED = 2,
    COMP_EPAPER_EXPRESSION_SIGNAL_WAKE_DETECTED = 3,
    COMP_EPAPER_EXPRESSION_SIGNAL_SPEAKER_PROMPT = 4,
    COMP_EPAPER_EXPRESSION_SIGNAL_SPEAKER_RESULT = 5,
    COMP_EPAPER_EXPRESSION_SIGNAL_MEETING_START = 6,
    COMP_EPAPER_EXPRESSION_SIGNAL_MEETING_STOP = 7,
    COMP_EPAPER_EXPRESSION_SIGNAL_MEETING_FINALIZE = 8,
    COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_START = 9,
    COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_STOP = 10,
    COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_CANCEL = 11,
    COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_FINISHED = 12,
    COMP_EPAPER_EXPRESSION_SIGNAL_LOW_BATTERY = 13,
    COMP_EPAPER_EXPRESSION_SIGNAL_RECOVERY = 14,
    COMP_EPAPER_EXPRESSION_SIGNAL_ERROR = 15,
    COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY = 16,
    COMP_EPAPER_EXPRESSION_SIGNAL_BATTERY_RECOVERED = 17,
    COMP_EPAPER_EXPRESSION_SIGNAL_COUNT = 18,
} comp_epaper_expression_signal_t;

typedef struct {
    comp_epaper_expression_t expression;
    comp_epaper_expression_signal_t signal;
    uint8_t priority;
    const char *name;
    const char *title;
    const char *body;
    const char *footer;
    const char *reason;
} comp_epaper_expression_decision_t;

typedef struct {
    comp_epaper_expression_t current;
    comp_epaper_expression_signal_t last_signal;
    uint8_t priority;
    uint32_t revision;
    uint32_t visible_age_ms;
    uint32_t suppressed_duplicate_count;
    bool initialized;
} comp_epaper_expression_state_t;

typedef struct {
    bool initialized;
    comp_epaper_expression_t current;
    comp_epaper_expression_signal_t last_signal;
    uint8_t priority;
    uint32_t revision;
    uint32_t visible_age_ms;
    uint32_t auto_recover_ms;
    uint32_t suppressed_duplicate_count;
} comp_epaper_expression_state_snapshot_t;

void comp_epaper_expression_state_init(comp_epaper_expression_state_t *state);

bool comp_epaper_expression_is_supported(comp_epaper_expression_t expression);
bool comp_epaper_expression_signal_is_supported(comp_epaper_expression_signal_t signal);
const char *comp_epaper_expression_name(comp_epaper_expression_t expression);
uint8_t comp_epaper_expression_priority(comp_epaper_expression_t expression);
uint32_t comp_epaper_expression_auto_recover_ms(comp_epaper_expression_t expression);

bool comp_epaper_expression_decide(comp_epaper_expression_signal_t signal,
                                   comp_epaper_expression_decision_t *out_decision);
bool comp_epaper_expression_state_apply_signal(
    comp_epaper_expression_state_t *state,
    comp_epaper_expression_signal_t signal,
    comp_epaper_expression_decision_t *out_decision);
bool comp_epaper_expression_state_tick(
    comp_epaper_expression_state_t *state,
    uint32_t elapsed_ms,
    comp_epaper_expression_decision_t *out_decision);
void comp_epaper_expression_state_snapshot(
    const comp_epaper_expression_state_t *state,
    comp_epaper_expression_state_snapshot_t *out_snapshot);

uint32_t comp_epaper_expression_decision_crc32(
    const comp_epaper_expression_decision_t *decision);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_EXPRESSION_STATE_H */
