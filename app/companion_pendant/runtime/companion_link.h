#ifndef COMPANION_PRODUCT_LINK_H
#define COMPANION_PRODUCT_LINK_H
#include "companion_runtime.h"
#include "wba_recording_service.h"
#include "wba_recording_transfer.h"
#include "wba_recording_radio.h"
#include "companion_gatt_stm32wb.h"
#include "companion_v1_features.h"
#ifndef COMPANION_WBA_APP_VERSION
#define COMPANION_WBA_APP_VERSION 0x00010114u
#endif
#ifndef COMPANION_WBA_BUILD_ID
#define COMPANION_WBA_BUILD_ID 0x20261004u
#endif
#ifndef COMPANION_WBA_BOARD_ID
#define COMPANION_WBA_BOARD_ID 0x57424155u
#endif
typedef bool (*comp_link_publish_fn)(void *,companion_gatt_char_id_t,const uint8_t *,uint16_t);
typedef struct {
    comp_runtime_t *runtime;
    comp_wba_recording_service_t *recorder;
    comp_recording_journal_t *journal;
    companion_v1_features_t *features;
    comp_link_publish_fn publish;
    void *context;
} comp_link_config_t;
typedef struct {
    companion_gatt_delete_privacy_v1_t response;
    uint32_t recording_id,cursor,retry_ms;
    comp_recording_journal_result_t last_result;
    /* Explicit retry state keeps a wrapped zero deadline distinct from idle. */
    bool active,complete,response_pending,retry_pending,receipt_valid;
} comp_link_reclaim_t;
typedef struct {
    companion_recording_discard_v2_t offer;
    uint32_t issued_ms;
    bool offered,accepted,connection_valid;
} comp_link_discard_t;
typedef struct {
    comp_link_config_t config;
    comp_wba_recording_transfer_t transfer;
    comp_wba_recording_radio_t *segmented;
    bool connected,encrypted,subscribed[COMPANION_GATT_CHAR_COUNT];
    bool maintenance;
    uint32_t next_status_ms,remote_limit_ms;
#ifndef COMPANION_RECORDING_SEGMENTED_ONLY
    uint32_t last_catalog_generation;
#endif
    uint32_t remote_record_token;
    uint32_t meeting_start_request_id;
    uint32_t meeting_record_token;
    uint32_t meeting_control_sequence;
    uint16_t meeting_max_seconds;
    uint8_t last_recording_state;
    uint8_t meeting_command;
    bool meeting_status_dirty;
    bool meeting_extended,meeting_timeline;
    uint8_t timeline_prepare; /*0 local/default,1 legacy,2 CMC3 plain,3 CMC3 timeline*/
    uint32_t rejected_writes,publish_failures;
    /* Product V2 retires the V1 reclaim/offer workers. They never coexist;
     * reuse their RAM for the actual negotiated segmented radio owner. */
    union {
        struct {comp_link_reclaim_t reclaim;comp_link_discard_t discard;} legacy;
        comp_wba_recording_radio_t segmented_state;
    } io;
} comp_link_t;
bool comp_link_init(comp_link_t *,const comp_link_config_t *);
/* Replaces the legacy journal/reader binding. Caller supplies one mounted,
 * recovered pipeline and static radio state, never a second capture owner.
 * A full product also binds logical recording control and status capability;
 * this initializer does not advertise CRV2 on its own. */
bool comp_link_init_segmented(comp_link_t *,const comp_link_config_t *,
    comp_wba_recording_radio_t *,comp_wba_recording_pipeline_t *,uint16_t value_capacity);
/* Local starts use a pause timeline; validated legacy/plain remote starts
 * retain their explicitly selected format only during synchronous prepare. */
bool comp_link_recording_timeline_requested(const comp_link_t *,uint32_t token);
void comp_link_connection(comp_link_t *,bool connected,bool encrypted,uint32_t now);
void comp_link_event(comp_link_t *,const companion_gatt_event_t *,uint32_t now);
void comp_link_poll(comp_link_t *,uint32_t now);
void comp_link_poll_with_clock(comp_link_t *,uint32_t now,
    comp_wba_recording_transfer_clock_fn clock,void *clock_context);
void comp_link_poll_with_budget(comp_link_t *,uint32_t now,
    comp_wba_recording_transfer_clock_fn clock,void *clock_context,
    const comp_wba_recording_transfer_budget_t *budget);
bool comp_link_heavy_io_allowed(void *context);
bool comp_link_discard_all_confirmed(comp_link_t *);
#endif
