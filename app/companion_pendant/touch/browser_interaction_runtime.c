#include "browser_interaction_runtime.h"

#include <stddef.h>
#include <string.h>

#include "companion_browser_interaction_contract.h"

static const char *const k_family_names[COMP_BROWSER_FAMILY_COUNT] = {
    "calm",
    "curious",
    "delighted",
    "warm",
    "playful",
    "sleepy",
    "bashful",
    "thoughtful",
    "focused",
    "alert",
};

static uint8_t bounded_add(uint8_t value, uint8_t add, uint8_t limit)
{
  const uint16_t sum = (uint16_t)value + add;
  return (uint8_t)(sum > limit ? limit : sum);
}

static uint8_t bounded_sub(uint8_t value, uint8_t subtract)
{
  return value > subtract ? (uint8_t)(value - subtract) : 0u;
}

static void decay_memory(
    comp_browser_interaction_runtime_t *runtime,
    uint32_t now_ms)
{
  uint32_t units;

  if (!runtime->last_emotion_update_valid)
  {
    return;
  }
  units = (now_ms - runtime->last_emotion_update_ms) / 8000u;
  if (units == 0u)
  {
    return;
  }
  if (units > 255u)
  {
    units = 255u;
  }
  runtime->arousal = bounded_sub(runtime->arousal, (uint8_t)units);
  runtime->surprise = bounded_sub(
      runtime->surprise,
      (uint8_t)(units > 127u ? 255u : units * 2u));
  runtime->curiosity = bounded_sub(runtime->curiosity, (uint8_t)units);
  runtime->focus = bounded_sub(runtime->focus, (uint8_t)(units / 2u));
  runtime->valence = bounded_sub(runtime->valence, (uint8_t)(units / 3u));
  runtime->fatigue = bounded_add(runtime->fatigue, (uint8_t)units, 8u);
  runtime->last_emotion_update_ms += units * 8000u;
}

static uint8_t pointer_zone(uint16_t x, uint16_t y)
{
  uint8_t column = (uint8_t)(((uint32_t)x * 3u) / 200u);
  uint8_t row = (uint8_t)(((uint32_t)y * 3u) / 200u);
  if (column > 2u)
  {
    column = 2u;
  }
  if (row > 2u)
  {
    row = 2u;
  }
  return (uint8_t)(row * 3u + column);
}

static comp_browser_tap_zone_t local_zone(uint16_t x, uint16_t y)
{
  if (y < COMPANION_BROWSER_INTERACTION_ZONE_UP_Y_200)
  {
    return COMP_BROWSER_TAP_ZONE_UP;
  }
  if (y > COMPANION_BROWSER_INTERACTION_ZONE_DOWN_Y_200)
  {
    return COMP_BROWSER_TAP_ZONE_DOWN;
  }
  if (x < COMPANION_BROWSER_INTERACTION_ZONE_LEFT_X_200)
  {
    return COMP_BROWSER_TAP_ZONE_LEFT;
  }
  if (x > COMPANION_BROWSER_INTERACTION_ZONE_RIGHT_X_200)
  {
    return COMP_BROWSER_TAP_ZONE_RIGHT;
  }
  return COMP_BROWSER_TAP_ZONE_CENTER;
}

static void score_single_tap(
    const comp_browser_interaction_runtime_t *runtime,
    uint16_t x,
    uint16_t y,
    int16_t scores[COMP_BROWSER_FAMILY_COUNT])
{
  const bool edge = x < 50u || x > 150u || y > 144u;
  const bool upper = y < 60u;
  const bool center = x > 68u && x < 132u && y > 60u && y < 144u;
  uint8_t index;

  scores[COMP_BROWSER_FAMILY_CALM] =
      50 + (runtime->arousal < 3u ? (int16_t)(3u - runtime->arousal) * 10 : 0);
  scores[COMP_BROWSER_FAMILY_CURIOUS] =
      (int16_t)runtime->curiosity * 28 + (int16_t)runtime->surprise * 9;
  scores[COMP_BROWSER_FAMILY_DELIGHTED] =
      (int16_t)runtime->valence * 23 + (int16_t)runtime->arousal * 17;
  scores[COMP_BROWSER_FAMILY_WARM] =
      (int16_t)runtime->affinity * 25 + (int16_t)runtime->valence * 20;
  scores[COMP_BROWSER_FAMILY_PLAYFUL] =
      (int16_t)runtime->arousal * 27 + (int16_t)runtime->valence * 9 +
      (int16_t)runtime->teases * 20;
  scores[COMP_BROWSER_FAMILY_SLEEPY] =
      (int16_t)runtime->fatigue * 30 - (int16_t)runtime->arousal * 14;
  scores[COMP_BROWSER_FAMILY_BASHFUL] =
      (int16_t)runtime->affinity * 20 + (int16_t)runtime->surprise * 13 +
      (edge ? 50 : 0);
  scores[COMP_BROWSER_FAMILY_THOUGHTFUL] =
      (int16_t)runtime->curiosity * 20 + (int16_t)runtime->focus * 27 -
      (int16_t)runtime->arousal * 5;
  scores[COMP_BROWSER_FAMILY_FOCUSED] =
      (int16_t)runtime->focus * 31 + (int16_t)runtime->curiosity * 7;
  scores[COMP_BROWSER_FAMILY_ALERT] =
      (int16_t)runtime->surprise * 31 + (int16_t)runtime->arousal * 11 +
      (upper && edge ? 40 : 0);

  if (upper)
  {
    scores[COMP_BROWSER_FAMILY_CURIOUS] += 80;
    if (runtime->focus >= 3u)
    {
      scores[COMP_BROWSER_FAMILY_THOUGHTFUL] += 70;
    }
    if (runtime->arousal >= 4u)
    {
      scores[COMP_BROWSER_FAMILY_ALERT] += 80;
    }
  }
  if (center)
  {
    scores[COMP_BROWSER_FAMILY_WARM] += 70;
    if (runtime->affinity >= 3u)
    {
      scores[COMP_BROWSER_FAMILY_BASHFUL] += 60;
    }
    if (runtime->focus >= 4u)
    {
      scores[COMP_BROWSER_FAMILY_FOCUSED] += 70;
    }
    if (runtime->valence >= 5u && runtime->arousal >= 4u)
    {
      scores[COMP_BROWSER_FAMILY_DELIGHTED] += 80;
    }
  }
  if (edge)
  {
    scores[COMP_BROWSER_FAMILY_BASHFUL] += 40;
  }
  for (index = 0u; index < 3u; ++index)
  {
    if (runtime->recent[index] < COMP_BROWSER_FAMILY_COUNT)
    {
      scores[runtime->recent[index]] -= index == 0u ? 70 : 30;
    }
  }
  if (runtime->selected < COMP_BROWSER_FAMILY_COUNT)
  {
    scores[runtime->selected] -= 30;
  }
}

static comp_browser_family_t best_family(
    const int16_t scores[COMP_BROWSER_FAMILY_COUNT])
{
  comp_browser_family_t best = COMP_BROWSER_FAMILY_CALM;
  comp_browser_family_t candidate;

  for (candidate = COMP_BROWSER_FAMILY_CURIOUS;
       candidate < COMP_BROWSER_FAMILY_COUNT;
       candidate = (comp_browser_family_t)(candidate + 1))
  {
    if (scores[candidate] > scores[best] ||
        (scores[candidate] == scores[best] &&
         strcmp(k_family_names[candidate], k_family_names[best]) < 0))
    {
      best = candidate;
    }
  }
  return best;
}

static void remember_family(
    comp_browser_interaction_runtime_t *runtime,
    comp_browser_family_t family)
{
  comp_browser_family_t next[3] = {
      family,
      COMP_BROWSER_FAMILY_NONE,
      COMP_BROWSER_FAMILY_NONE,
  };
  uint8_t source;
  uint8_t target = 1u;

  for (source = 0u; source < 3u && target < 3u; ++source)
  {
    if (runtime->recent[source] != family)
    {
      next[target++] = runtime->recent[source];
    }
  }
  memcpy(runtime->recent, next, sizeof(next));
}

void comp_browser_interaction_reset(
    comp_browser_interaction_runtime_t *runtime)
{
  if (runtime == NULL)
  {
    return;
  }
  memset(runtime, 0, sizeof(*runtime));
  runtime->selected = COMP_BROWSER_FAMILY_CALM;
  runtime->recent[0] = COMP_BROWSER_FAMILY_CALM;
  runtime->recent[1] = COMP_BROWSER_FAMILY_NONE;
  runtime->recent[2] = COMP_BROWSER_FAMILY_NONE;
}

bool comp_browser_interaction_tap(
    comp_browser_interaction_runtime_t *runtime,
    uint16_t x,
    uint16_t y,
    uint32_t now_ms,
    comp_browser_tap_result_t *result)
{
  int16_t scores[COMP_BROWSER_FAMILY_COUNT];
  uint8_t zone;
  bool new_zone;
  comp_browser_family_t target;

  if (runtime == NULL || result == NULL)
  {
    return false;
  }
  if (x > 200u)
  {
    x = 200u;
  }
  if (y > 200u)
  {
    y = 200u;
  }
  decay_memory(runtime, now_ms);
  zone = pointer_zone(x, y);
  new_zone = !runtime->last_zone_valid || runtime->last_zone != zone;
  runtime->arousal = bounded_add(runtime->arousal, 1u, 6u);
  runtime->surprise = bounded_add(
      runtime->surprise, new_zone ? 2u : 0u, 6u);
  runtime->curiosity = bounded_add(
      runtime->curiosity, y < 60u || new_zone ? 2u : 1u, 8u);
  runtime->focus = bounded_add(runtime->focus, new_zone ? 0u : 2u, 8u);
  if (x > 60u && x < 140u && y > 60u && y < 150u)
  {
    runtime->affinity = bounded_add(runtime->affinity, 1u, 8u);
    runtime->valence = bounded_add(runtime->valence, 1u, 8u);
  }
  runtime->fatigue = bounded_sub(runtime->fatigue, 2u);
  runtime->last_zone = zone;
  runtime->last_zone_valid = true;
  runtime->last_emotion_update_ms = now_ms;
  runtime->last_emotion_update_valid = true;
  runtime->taps = bounded_add(runtime->taps, 1u, 255u);

  score_single_tap(runtime, x, y, scores);
  target = best_family(scores);
  remember_family(runtime, target);

  runtime->single_tap_evidence =
      runtime->last_tap_valid &&
              now_ms - runtime->last_tap_ms <=
                  COMPANION_BROWSER_INTERACTION_EVIDENCE_WINDOW_MS
          ? bounded_add(runtime->single_tap_evidence, 1u, 255u)
          : 1u;
  runtime->last_tap_ms = now_ms;
  runtime->last_tap_valid = true;

  result->family_before = runtime->selected;
  result->target = target;
  result->local_zone = local_zone(x, y);
  result->transition =
      runtime->single_tap_evidence >=
          COMPANION_BROWSER_INTERACTION_SWITCH_THRESHOLD &&
      target != runtime->selected;
  if (result->transition)
  {
    runtime->single_tap_evidence = 0u;
    runtime->selected = target;
  }
  result->family_after = runtime->selected;
  result->evidence_after = runtime->single_tap_evidence;
  return true;
}

bool comp_browser_interaction_shortest_route(
    comp_browser_family_t source,
    comp_browser_family_t target,
    comp_browser_family_t *route,
    uint8_t route_capacity,
    uint8_t *route_count)
{
  comp_browser_family_t queue[COMP_BROWSER_FAMILY_COUNT];
  comp_browser_family_t previous[COMP_BROWSER_FAMILY_COUNT];
  comp_browser_family_t reversed[COMP_BROWSER_FAMILY_COUNT];
  uint8_t queue_read = 0u;
  uint8_t queue_write = 0u;
  uint8_t count = 0u;
  comp_browser_family_t current;
  comp_browser_family_t candidate;

  if (route == NULL || route_count == NULL ||
      source >= COMP_BROWSER_FAMILY_COUNT ||
      target >= COMP_BROWSER_FAMILY_COUNT ||
      route_capacity == 0u)
  {
    return false;
  }
  for (candidate = COMP_BROWSER_FAMILY_CALM;
       candidate < COMP_BROWSER_FAMILY_COUNT;
       candidate = (comp_browser_family_t)(candidate + 1))
  {
    previous[candidate] = COMP_BROWSER_FAMILY_NONE;
  }
  queue[queue_write++] = source;
  previous[source] = source;
  while (queue_read < queue_write)
  {
    current = queue[queue_read++];
    if (current == target)
    {
      break;
    }
    for (candidate = COMP_BROWSER_FAMILY_CALM;
         candidate < COMP_BROWSER_FAMILY_COUNT;
         candidate = (comp_browser_family_t)(candidate + 1))
    {
      if ((companion_browser_affect_graph[current] &
           (uint16_t)(1u << (unsigned)candidate)) != 0u &&
          previous[candidate] == COMP_BROWSER_FAMILY_NONE)
      {
        previous[candidate] = current;
        queue[queue_write++] = candidate;
      }
    }
  }
  if (previous[target] == COMP_BROWSER_FAMILY_NONE)
  {
    return false;
  }
  current = target;
  do
  {
    if (count >= COMP_BROWSER_FAMILY_COUNT)
    {
      return false;
    }
    reversed[count++] = current;
    if (current == source)
    {
      break;
    }
    current = previous[current];
  } while (true);
  if (count > route_capacity)
  {
    return false;
  }
  for (queue_read = 0u; queue_read < count; ++queue_read)
  {
    route[queue_read] = reversed[count - queue_read - 1u];
  }
  *route_count = count;
  return true;
}

bool comp_browser_interaction_verify_contract_trace(uint8_t *failed_step)
{
  comp_browser_interaction_runtime_t runtime;
  comp_browser_tap_result_t result;
  uint8_t index;

  comp_browser_interaction_reset(&runtime);
  for (index = 0u;
       index < COMPANION_BROWSER_INTERACTION_TRACE_COUNT;
       ++index)
  {
    const companion_browser_interaction_trace_step_t *const expected =
        &companion_browser_interaction_trace[index];
    if (!comp_browser_interaction_tap(
            &runtime,
            expected->x,
            expected->y,
            (uint32_t)index * 100u,
            &result) ||
        result.target != (comp_browser_family_t)expected->target_family ||
        result.family_after !=
            (comp_browser_family_t)expected->family_after ||
        result.transition != (expected->transition != 0u) ||
        result.evidence_after != expected->evidence_after)
    {
      if (failed_step != NULL)
      {
        *failed_step = index;
      }
      return false;
    }
    if (result.transition)
    {
      comp_browser_family_t route[COMP_BROWSER_FAMILY_COUNT];
      uint8_t route_count = 0u;
      uint8_t edge;
      if (!comp_browser_interaction_shortest_route(
              result.family_before,
              result.family_after,
              route,
              COMP_BROWSER_FAMILY_COUNT,
              &route_count) ||
          route_count < 2u)
      {
        if (failed_step != NULL)
        {
          *failed_step = index;
        }
        return false;
      }
      for (edge = 0u; edge + 1u < route_count; ++edge)
      {
        if ((companion_browser_affect_graph[route[edge]] &
             (uint16_t)(1u << (unsigned)route[edge + 1u])) == 0u)
        {
          if (failed_step != NULL)
          {
            *failed_step = index;
          }
          return false;
        }
      }
    }
  }
  if (failed_step != NULL)
  {
    *failed_step = UINT8_MAX;
  }
  return true;
}

void comp_browser_menu_hold_begin(comp_browser_menu_hold_runtime_t *runtime)
{
  if (runtime == NULL)
  {
    return;
  }
  runtime->next_milestone = 0u;
  runtime->active = true;
}

void comp_browser_menu_hold_end(comp_browser_menu_hold_runtime_t *runtime)
{
  if (runtime == NULL)
  {
    return;
  }
  runtime->next_milestone = 0u;
  runtime->active = false;
}

bool comp_browser_menu_hold_next(
    const comp_browser_menu_hold_runtime_t *runtime,
    uint32_t elapsed_ms,
    comp_browser_menu_hold_event_t *event)
{
  const companion_browser_menu_hold_milestone_t *milestone;

  if (runtime == NULL || event == NULL || !runtime->active ||
      runtime->next_milestone >=
          COMPANION_BROWSER_INTERACTION_MENU_HOLD_MILESTONE_COUNT)
  {
    return false;
  }
  milestone = &companion_browser_menu_hold_milestones[
      runtime->next_milestone];
  if (elapsed_ms < milestone->held_ms)
  {
    return false;
  }
  event->bucket = runtime->next_milestone;
  event->held_ms = milestone->held_ms;
  event->state_id = milestone->state_id;
  return true;
}

bool comp_browser_menu_hold_commit(
    comp_browser_menu_hold_runtime_t *runtime,
    uint8_t bucket)
{
  if (runtime == NULL || !runtime->active ||
      bucket != runtime->next_milestone ||
      bucket >= COMPANION_BROWSER_INTERACTION_MENU_HOLD_MILESTONE_COUNT)
  {
    return false;
  }
  runtime->next_milestone++;
  return true;
}

bool comp_browser_menu_hold_verify_replay(
    uint16_t cycles,
    uint16_t *failed_cycle,
    uint8_t *failed_bucket)
{
  comp_browser_menu_hold_runtime_t runtime = {0};
  comp_browser_menu_hold_event_t event;
  uint16_t cycle;
  uint8_t bucket;

  for (cycle = 0u; cycle < cycles; ++cycle)
  {
    comp_browser_menu_hold_begin(&runtime);
    for (bucket = 0u;
         bucket < COMPANION_BROWSER_INTERACTION_MENU_HOLD_MILESTONE_COUNT;
         ++bucket)
    {
      const companion_browser_menu_hold_milestone_t *const expected =
          &companion_browser_menu_hold_milestones[bucket];
      if ((expected->held_ms != 0u &&
           comp_browser_menu_hold_next(
               &runtime, expected->held_ms - 1u, &event)) ||
          !comp_browser_menu_hold_next(
              &runtime, expected->held_ms, &event) ||
          event.bucket != bucket || event.held_ms != expected->held_ms ||
          event.state_id == NULL ||
          strcmp(event.state_id, expected->state_id) != 0 ||
          !comp_browser_menu_hold_commit(&runtime, event.bucket))
      {
        if (failed_cycle != NULL) *failed_cycle = cycle;
        if (failed_bucket != NULL) *failed_bucket = bucket;
        return false;
      }
    }
    if (comp_browser_menu_hold_next(&runtime, UINT32_MAX, &event))
    {
      if (failed_cycle != NULL) *failed_cycle = cycle;
      if (failed_bucket != NULL) *failed_bucket = bucket;
      return false;
    }
    comp_browser_menu_hold_end(&runtime);
    for (uint8_t cancel_after = 0u;
         cancel_after <
             COMPANION_BROWSER_INTERACTION_MENU_HOLD_MILESTONE_COUNT;
         ++cancel_after)
    {
      comp_browser_menu_hold_begin(&runtime);
      for (bucket = 0u; bucket <= cancel_after; ++bucket)
      {
        const companion_browser_menu_hold_milestone_t *const expected =
            &companion_browser_menu_hold_milestones[bucket];
        if (!comp_browser_menu_hold_next(
                &runtime, expected->held_ms, &event) ||
            event.bucket != bucket ||
            !comp_browser_menu_hold_commit(&runtime, event.bucket))
        {
          if (failed_cycle != NULL) *failed_cycle = cycle;
          if (failed_bucket != NULL) *failed_bucket =
              (uint8_t)(COMPANION_BROWSER_INTERACTION_MENU_HOLD_MILESTONE_COUNT +
                        cancel_after);
          return false;
        }
      }
      comp_browser_menu_hold_end(&runtime);
      if (runtime.active || runtime.next_milestone != 0u ||
          comp_browser_menu_hold_next(&runtime, UINT32_MAX, &event) ||
          comp_browser_menu_hold_commit(&runtime, 0u))
      {
        if (failed_cycle != NULL) *failed_cycle = cycle;
        if (failed_bucket != NULL) *failed_bucket =
            (uint8_t)(COMPANION_BROWSER_INTERACTION_MENU_HOLD_MILESTONE_COUNT +
                      cancel_after);
        return false;
      }
    }
  }
  if (failed_cycle != NULL) *failed_cycle = UINT16_MAX;
  if (failed_bucket != NULL) *failed_bucket = UINT8_MAX;
  return true;
}

const char *comp_browser_family_name(comp_browser_family_t family)
{
  return family < COMP_BROWSER_FAMILY_COUNT ? k_family_names[family] : "invalid";
}

const char *comp_browser_tap_zone_name(comp_browser_tap_zone_t zone)
{
  static const char *const k_zone_names[] = {
      "center", "up", "down", "left", "right",
  };
  return zone <= COMP_BROWSER_TAP_ZONE_RIGHT ? k_zone_names[zone] : "center";
}
