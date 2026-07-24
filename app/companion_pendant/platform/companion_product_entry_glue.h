#ifndef COMPANION_PRODUCT_ENTRY_GLUE_H
#define COMPANION_PRODUCT_ENTRY_GLUE_H

#include <stdbool.h>
#include <stdint.h>

typedef bool (*companion_product_begin_settings_fn)(
    void *, uint32_t, uint64_t, uint64_t, uint32_t, const void *, uint32_t *);
typedef bool (*companion_product_begin_meeting_fn)(void *, uint32_t, uint64_t, uint64_t, const void *);

typedef struct {
    void *context;
    companion_product_begin_settings_fn begin_settings;
    companion_product_begin_meeting_fn begin_meeting;
    uint64_t settings_id;
    uint64_t settings_key;
    uint32_t settings_ack_revision;
    bool settings_terminal;
    bool settings_result;
    uint64_t meeting_id;
    uint64_t meeting_key;
    bool meeting_terminal;
    bool meeting_result;
} companion_product_entry_glue_t;

void companion_product_entry_glue_init(
    companion_product_entry_glue_t *, void *,
    companion_product_begin_settings_fn, companion_product_begin_meeting_fn);

bool companion_product_entry_settings(
    companion_product_entry_glue_t *, uint64_t request_id, uint64_t idempotency_key,
    uint32_t now_ms, uint32_t deadline_ms, uint32_t expected_revision,
    const void *payload, uint32_t *ack_revision, bool *replayed);

bool companion_product_entry_meeting(
    companion_product_entry_glue_t *, uint64_t request_id, uint64_t idempotency_key,
    uint32_t now_ms, uint32_t deadline_ms, const void *payload, bool *replayed);

#endif
