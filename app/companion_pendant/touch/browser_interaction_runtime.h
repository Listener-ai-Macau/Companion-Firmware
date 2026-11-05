#ifndef COMPANION_BROWSER_INTERACTION_RUNTIME_H
#define COMPANION_BROWSER_INTERACTION_RUNTIME_H

#include <stdbool.h>
#include <stdint.h>

typedef enum {
  COMP_BROWSER_FAMILY_CALM = 0u,
  COMP_BROWSER_FAMILY_CURIOUS,
  COMP_BROWSER_FAMILY_DELIGHTED,
  COMP_BROWSER_FAMILY_WARM,
  COMP_BROWSER_FAMILY_PLAYFUL,
  COMP_BROWSER_FAMILY_SLEEPY,
  COMP_BROWSER_FAMILY_BASHFUL,
  COMP_BROWSER_FAMILY_THOUGHTFUL,
  COMP_BROWSER_FAMILY_FOCUSED,
  COMP_BROWSER_FAMILY_ALERT,
  COMP_BROWSER_FAMILY_COUNT,
  COMP_BROWSER_FAMILY_NONE = 0xFFu,
} comp_browser_family_t;

typedef enum {
  COMP_BROWSER_TAP_ZONE_CENTER = 0u,
  COMP_BROWSER_TAP_ZONE_UP,
  COMP_BROWSER_TAP_ZONE_DOWN,
  COMP_BROWSER_TAP_ZONE_LEFT,
  COMP_BROWSER_TAP_ZONE_RIGHT,
} comp_browser_tap_zone_t;

typedef struct {
  uint8_t affinity;
  uint8_t arousal;
  uint8_t curiosity;
  uint8_t surprise;
  uint8_t focus;
  uint8_t fatigue;
  uint8_t valence;
  uint8_t taps;
  uint8_t teases;
  uint8_t single_tap_evidence;
  uint8_t last_zone;
  comp_browser_family_t selected;
  comp_browser_family_t recent[3];
  uint32_t last_tap_ms;
  uint32_t last_emotion_update_ms;
  bool last_tap_valid;
  bool last_zone_valid;
  bool last_emotion_update_valid;
} comp_browser_interaction_runtime_t;

typedef struct {
  comp_browser_family_t family_before;
  comp_browser_family_t target;
  comp_browser_family_t family_after;
  comp_browser_tap_zone_t local_zone;
  uint8_t evidence_after;
  bool transition;
} comp_browser_tap_result_t;

typedef struct {
  uint8_t next_milestone;
  bool active;
} comp_browser_menu_hold_runtime_t;

typedef struct {
  uint8_t bucket;
  uint16_t held_ms;
  const char *state_id;
} comp_browser_menu_hold_event_t;

void comp_browser_interaction_reset(
    comp_browser_interaction_runtime_t *runtime);

bool comp_browser_interaction_tap(
    comp_browser_interaction_runtime_t *runtime,
    uint16_t x,
    uint16_t y,
    uint32_t now_ms,
    comp_browser_tap_result_t *result);

bool comp_browser_interaction_shortest_route(
    comp_browser_family_t source,
    comp_browser_family_t target,
    comp_browser_family_t *route,
    uint8_t route_capacity,
    uint8_t *route_count);

bool comp_browser_interaction_verify_contract_trace(uint8_t *failed_step);

void comp_browser_menu_hold_begin(comp_browser_menu_hold_runtime_t *runtime);
void comp_browser_menu_hold_end(comp_browser_menu_hold_runtime_t *runtime);
bool comp_browser_menu_hold_next(
    const comp_browser_menu_hold_runtime_t *runtime,
    uint32_t elapsed_ms,
    comp_browser_menu_hold_event_t *event);
bool comp_browser_menu_hold_commit(
    comp_browser_menu_hold_runtime_t *runtime,
    uint8_t bucket);
bool comp_browser_menu_hold_verify_replay(
    uint16_t cycles,
    uint16_t *failed_cycle,
    uint8_t *failed_bucket);

const char *comp_browser_family_name(comp_browser_family_t family);
const char *comp_browser_tap_zone_name(comp_browser_tap_zone_t zone);

#endif
