#ifndef COMPANION_WBA_SEGMENT_PULL_H
#define COMPANION_WBA_SEGMENT_PULL_H
#include "wba_segment_storage.h"
#include "wba_recording_transfer.h"

/* Negotiated V2 sealed pull request32B: schema2/command21/flags4/reserved0;
 * recording ID u32@4, epoch u64@8, session u64@16, segment index u32@24,
 * logical COP1 offset u32@28. Flag4 streams remaining bytes;0 one window.
 * Once exact metadata is selected, existing V1 compact224/finalSHA framing is
 * reused, bound to this negotiated epoch/session. Do not advertise V2 until
 * the complete GATT/Type/recovery/consumption binding exists. */
#define COMP_SEG_PULL_REQUEST_BYTES 32u
#define COMP_SEG_PULL_COMMAND 0x21u
typedef struct {
    comp_wba_segment_storage_t *storage;
    comp_segment_catalog_t *catalog;
    comp_wba_recording_transfer_t *transfer; /* existing packet/radio owner */
    comp_segment_entry_t *selected; /* exclusive caller-owned descriptor */
    uint8_t *page; /* borrowed256B scratch for ONE read/copy slice only */
    bool (*foreground_allowed)(void *);
    bool (*page_available)(void *);
    comp_wba_recording_transfer_notify_fn notify;
    void *context;
} comp_wba_segment_pull_config_t;
typedef struct {
    comp_wba_segment_pull_config_t config;
    companion_recording_adapter_request_t request;
    uint64_t session;
    uint32_t segment_index,generation,read_offset,read_bytes;
    uint8_t *read_destination;
    uint16_t copied;
    uint8_t scan,slot,phase,read_retries,read_retry_elapsed_ms;
    bool live;
    comp_segment_result_t result;
} comp_wba_segment_pull_t;

bool comp_wba_segment_pull_init(comp_wba_segment_pull_t *,const comp_wba_segment_pull_config_t *);
/* Only a verified/encrypted V2 peer with matching actual UID/epoch enables
 * reads. false disconnect cancels transient work only; no MIC or NOR mutation. */
bool comp_wba_segment_pull_peer(comp_wba_segment_pull_t *,const uint8_t uid[12],uint64_t epoch,bool authenticated_v2);
comp_segment_result_t comp_wba_segment_pull_begin(comp_wba_segment_pull_t *,const uint8_t request[32]);
/* One lookup/read/arbitration/notify step; bounded bulk wrapper may use the
 * existing transfer poll_budget AFTER selection. No growing-tail ACK. */
comp_segment_result_t comp_wba_segment_pull_poll(comp_wba_segment_pull_t *);
/* Select only: no payload read/notification. The product sequencer retains
 * sole ownership of stopped bulk sending and its existing75KiB/s baseline. */
comp_segment_result_t comp_wba_segment_pull_select_poll(comp_wba_segment_pull_t *);
void comp_wba_segment_pull_cancel(comp_wba_segment_pull_t *);
/* Freeze only the readback-committed complete COP1 frames of the owned
 * WRITING tail. This is NOT a sealed descriptor or a consume proof.
 * CLP2 flags@74:1 legacy schema1;3 schema2 with real timeline records.
 * Schema2 encoded bytes include events/padding; sample_count never does. */
bool comp_wba_segment_pull_tail(comp_wba_segment_pull_t *,const comp_segment_entry_t *,uint32_t committed);
/* Stable schema2 RUNNING/PAUSED only: all counted events/padding must already
 * be committed. No flash scan, no extra buffer and no growing-tail ACK. */
bool comp_wba_segment_pull_tail_timeline(comp_wba_segment_pull_t *,const comp_segment_entry_t *,
    uint32_t committed,uint32_t committed_non_audio_bytes);
#endif
