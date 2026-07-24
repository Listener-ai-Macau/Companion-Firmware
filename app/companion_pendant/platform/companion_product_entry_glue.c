#include "companion_product_entry_glue.h"

#include <string.h>

static bool expired(uint32_t now_ms, uint32_t deadline_ms)
{
  return deadline_ms != 0u && (int32_t)(now_ms - deadline_ms) > 0;
}

void companion_product_entry_glue_init(
    companion_product_entry_glue_t *glue, void *context,
    companion_product_begin_settings_fn begin_settings,
    companion_product_begin_meeting_fn begin_meeting)
{
  if (glue == NULL) return;
  memset(glue, 0, sizeof(*glue));
  glue->context = context;
  glue->begin_settings = begin_settings;
  glue->begin_meeting = begin_meeting;
}

bool companion_product_entry_settings(
    companion_product_entry_glue_t *glue, uint64_t request_id,
    uint64_t idempotency_key, uint32_t now_ms, uint32_t deadline_ms,
    uint32_t expected_revision, const void *payload, uint32_t *ack_revision,
    bool *replayed)
{
  uint32_t ack = 0u;
  if (replayed != NULL) *replayed = false;
  if (glue == NULL || payload == NULL || ack_revision == NULL ||
      request_id == 0u || glue->begin_settings == NULL) return false;
  if (glue->settings_terminal && glue->settings_id == request_id &&
      glue->settings_key == idempotency_key) {
    if (replayed != NULL) *replayed = true;
    *ack_revision = glue->settings_ack_revision;
    return glue->settings_result;
  }
  if (glue->settings_terminal && glue->settings_id == request_id) return false;
  if (expired(now_ms, deadline_ms)) {
    glue->settings_id = request_id; glue->settings_key = idempotency_key;
    glue->settings_terminal = true; glue->settings_result = false;
    return false;
  }
  if (!glue->begin_settings(glue->context, now_ms, request_id,
                            idempotency_key, expected_revision, payload, &ack)) {
    glue->settings_id = request_id; glue->settings_key = idempotency_key;
    glue->settings_terminal = true; glue->settings_result = false;
    return false;
  }
  glue->settings_id = request_id;
  glue->settings_key = idempotency_key;
  glue->settings_ack_revision = ack;
  glue->settings_terminal = true;
  glue->settings_result = true;
  *ack_revision = ack;
  return true;
}

bool companion_product_entry_meeting(
    companion_product_entry_glue_t *glue, uint64_t request_id,
    uint64_t idempotency_key, uint32_t now_ms, uint32_t deadline_ms,
    const void *payload, bool *replayed)
{
  if (replayed != NULL) *replayed = false;
  if (glue == NULL || payload == NULL || request_id == 0u ||
      glue->begin_meeting == NULL) return false;
  if (glue->meeting_terminal && glue->meeting_id == request_id &&
      glue->meeting_key == idempotency_key) {
    if (replayed != NULL) *replayed = true;
    return glue->meeting_result;
  }
  if (glue->meeting_terminal && glue->meeting_id == request_id) return false;
  if (expired(now_ms, deadline_ms)) {
    glue->meeting_id = request_id; glue->meeting_key = idempotency_key;
    glue->meeting_terminal = true; glue->meeting_result = false;
    return false;
  }
  if (!glue->begin_meeting(glue->context, now_ms, request_id,
                           idempotency_key, payload)) {
    glue->meeting_id = request_id; glue->meeting_key = idempotency_key;
    glue->meeting_terminal = true; glue->meeting_result = false;
    return false;
  }
  glue->meeting_id = request_id;
  glue->meeting_key = idempotency_key;
  glue->meeting_terminal = true;
  glue->meeting_result = true;
  return true;
}
