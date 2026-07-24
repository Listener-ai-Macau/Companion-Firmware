#include "companion_product_transport.h"
#include <string.h>
bool companion_settings_transport_apply(void *context, uint32_t now_ms, uint64_t request_id, uint64_t idempotency_key, uint32_t expected_revision, const void *payload, uint32_t *ack)
{
  companion_settings_transport_t *t = context; (void)now_ms;
  if (!t) return false;
  t->callback_count++; t->last_request_id = request_id; t->last_idempotency_key = idempotency_key; if (t->trace) t->trace(t->trace_context, "callback");
  if (!payload || !ack || !t->current || !t->size || t->fail || expected_revision != t->revision) return false;
  memcpy(t->current, payload, t->size); t->revision++; t->mutation_count++; if (t->trace) t->trace(t->trace_context, "mutation");
  t->readback_count++; if (t->trace) t->trace(t->trace_context, "readback");
  if (memcmp(t->current, payload, t->size) != 0) return false; *ack = t->revision; return true;
}
bool companion_meeting_transport_apply(void *context, uint32_t now_ms, uint64_t request_id, uint64_t idempotency_key, const void *payload)
{
  companion_meeting_transport_t *t = context; (void)now_ms; (void)payload;
  if (!t) return false; t->callback_count++; t->last_request_id = request_id; t->last_idempotency_key = idempotency_key; if (t->trace) t->trace(t->trace_context, "callback");
  if (!t->apply || t->fail) return false;
  if (!t->apply(t->apply_context, request_id)) return false; t->mutation_count++; if (t->trace) t->trace(t->trace_context, "mutation"); return true;
}
