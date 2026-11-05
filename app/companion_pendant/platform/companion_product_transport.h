#ifndef COMPANION_PRODUCT_TRANSPORT_H
#define COMPANION_PRODUCT_TRANSPORT_H
#include <stdbool.h>
#include <stdint.h>
typedef void (*companion_product_trace_fn)(void *, const char *);
typedef struct { void *current; uint32_t size; uint32_t revision; uint32_t callback_count; uint32_t mutation_count; uint32_t readback_count; bool fail; companion_product_trace_fn trace; void *trace_context; uint64_t last_request_id; uint64_t last_idempotency_key; } companion_settings_transport_t;
bool companion_settings_transport_apply(void *, uint32_t, uint64_t, uint64_t, uint32_t, const void *, uint32_t *);
typedef bool (*companion_meeting_apply_fn)(void *, uint64_t);
typedef struct { companion_meeting_apply_fn apply; void *apply_context; uint32_t callback_count; uint32_t mutation_count; bool fail; companion_product_trace_fn trace; void *trace_context; uint64_t last_request_id; uint64_t last_idempotency_key; } companion_meeting_transport_t;
bool companion_meeting_transport_apply(void *, uint32_t, uint64_t, uint64_t, const void *);
#endif
