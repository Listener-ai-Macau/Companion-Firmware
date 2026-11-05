#ifndef WBA_SEGMENT_DISCARD_CONTROL_H
#define WBA_SEGMENT_DISCARD_CONTROL_H
#include "wba_segment_discard_worker.h"
/* The server creates token from its hardware RNG. No destructive action is
 * accepted without a fresh offer on the same authenticated connection. */
typedef struct {
    uint8_t uid[12];uint64_t epoch,session,slots,samples;
    uint32_t generation,oldest_id,max_id,segments,encoded_bytes,reserved_bytes,started_unix_s,last_index;
    uint32_t token[2],request_id;uint8_t anchor_slot;
} comp_discard_offer_t;
typedef struct {
    bool (*random_u32)(void *,uint32_t *);
    bool (*acquire)(void *); /* recorder, OTA, transfer and catalog exclusive */
    bool (*release)(void *);
    comp_discard_entry_fn read;comp_discard_poll_fn poll;void *context;
} comp_discard_control_port_t;
typedef struct {
    comp_segment_catalog_t *catalog;comp_discard_control_port_t port;
    /* Preview/recheck ends before committed worker begins. */
    union {comp_discard_preview_t preview;comp_discard_worker_t worker;};
    comp_discard_offer_t offer;uint32_t peer,issued_ms;uint8_t phase;
    bool connected,owns,commit_started;comp_segment_result_t result;
} comp_discard_control_t;
/* Zero-initialize the control object before its first begin. */
comp_segment_result_t comp_discard_control_begin(comp_discard_control_t *,comp_segment_catalog_t *,
    const comp_discard_control_port_t *,uint32_t peer,uint32_t request_id);
comp_segment_result_t comp_discard_control_poll(comp_discard_control_t *,uint32_t now_ms);
/* Only expose this offer on the original encrypted peer. */
const comp_discard_offer_t *comp_discard_control_offer(const comp_discard_control_t *);
comp_segment_result_t comp_discard_control_confirm(comp_discard_control_t *,uint32_t peer,
    uint32_t now_ms,const comp_discard_offer_t *);
bool comp_discard_control_cancel(comp_discard_control_t *,uint32_t peer);
void comp_discard_control_disconnect(comp_discard_control_t *,uint32_t peer);
#endif
