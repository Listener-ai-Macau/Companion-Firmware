#ifndef COMPANION_WBA_RECORDING_RADIO_H
#define COMPANION_WBA_RECORDING_RADIO_H
#include "wba_recording_pipeline.h"
#include "wba_segment_directory.h"
#include "wba_segment_pull.h"
#include "companion_gatt_stm32wb.h"
#include "wba_segment_discard_wire.h"

typedef bool (*comp_wba_recording_radio_publish_fn)(void *,companion_gatt_char_id_t,
    const uint8_t *,uint16_t);
typedef struct {
    bool (*random)(void *,uint32_t *);
    bool (*acquire)(void *);
    bool (*release)(void *);
} comp_wba_recording_discard_hooks_t;
typedef struct {
    comp_wba_recording_pipeline_t *pipeline;
    comp_wba_recording_transfer_t *transfer;
    comp_wba_recording_radio_publish_fn publish;
    void *context;
    uint16_t value_capacity; /* actual negotiated ATT value, not LL capacity */
    const comp_wba_recording_discard_hooks_t *discard_hooks;
} comp_wba_recording_radio_config_t;

/* The directory and selected proof have mutually exclusive lifetimes. Reuse
 * the existing transfer packet for replies; the pipeline retains consume
 * ownership independently of this connection. No heap/second audio buffer. */
typedef struct {
    comp_wba_segment_pull_t pull;
    union {comp_wba_segment_directory_t directory;comp_segment_entry_t selected;} io;
    comp_wba_recording_radio_config_t config;
    uint32_t discard_peer;
    bool discard_running,discard_confirming,discard_subscribed,discard_buffer_owned;
    uint32_t interval_token,interval_deadline;
    uint32_t capacity_token; /* full correlated reply remains in idle transfer packet */
    uint16_t selected_value_capacity; /* connection profile; 244B legacy default */
    uint16_t pending_bytes;
    companion_gatt_char_id_t pending_char;
    uint8_t phase;
    bool authenticated,negotiated,consume_pending,consume_replay,consume_subscribed;
} comp_wba_recording_radio_t;

bool comp_wba_recording_radio_init(comp_wba_recording_radio_t *,const comp_wba_recording_radio_config_t *);
/* Actual ATT capacity can be23's20B before negotiation. V2 metadata needs
 *136B; hold the handshake until that capacity is confirmed. Never resize a
 * pending reply or an active data window. */
bool comp_wba_recording_radio_set_value_capacity(comp_wba_recording_radio_t *,uint16_t);
/* Connection loss cancels only transient reads/replies. The pipeline must
 * continue polling accepted ACK/erase work, even while this peer is absent. */
void comp_wba_recording_radio_connection(comp_wba_recording_radio_t *,bool authenticated);
/* CCCD lanes have independent lifetimes inside one authenticated connection.
 * Cancel only work whose notification sink retired; do not revoke its peer. */
void comp_wba_recording_radio_unsubscribe(comp_wba_recording_radio_t *,companion_gatt_char_id_t);
/* Follow the encrypted peer’s actual consume-reply subscription. */
void comp_wba_recording_radio_consume_subscription(comp_wba_recording_radio_t *,bool);
/* Called only for a WRITE from the CURRENT encrypted connection. CCCDs must
 * be active for control/list/pull/consume respectively. Claim V2 commands so
 * malformed V2 cannot fall through to a legacy interpretation. */
bool comp_wba_recording_radio_claims(companion_gatt_char_id_t,const uint8_t *,uint16_t);
bool comp_wba_recording_radio_write(comp_wba_recording_radio_t *,companion_gatt_char_id_t,
    const uint8_t *,uint16_t,bool subscribed);
void comp_wba_recording_radio_poll(comp_wba_recording_radio_t *,
    comp_wba_recording_transfer_clock_fn,void *,const comp_wba_recording_transfer_budget_t *);
bool comp_wba_recording_radio_read_allowed(void *);
bool comp_wba_recording_radio_busy(const comp_wba_recording_radio_t *);
/* Encrypted batch owns only a finite interval hint. No RX filter, sample
 * deadline or access permission changes. Active sealed sends renew it. */
bool comp_wba_recording_radio_interval_hint(comp_wba_recording_radio_t *,uint32_t now,bool allowed);
#endif
