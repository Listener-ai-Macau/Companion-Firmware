#ifndef COMPANION_RECORDING_IDENTITY_H
#define COMPANION_RECORDING_IDENTITY_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* CSI1: two independent 4KiB banks, 16 append slots each. The V1 mapping
 * remains byte-compatible; segmented capture stores its session in each
 * durable descriptor instead of expanding this seven-entry legacy mapping.
 * UID-bound random format epoch + monotonic session IDs, never boot/tick IDs.
 * Both new copies are read back before an ID is returned to the recorder. */
#define COMP_REC_IDENTITY_BANK_BYTES 4096u
#define COMP_REC_IDENTITY_BYTES 8192u
#define COMP_REC_IDENTITY_WIRE_BYTES 160u
#define COMP_REC_IDENTITY_SLOT_BYTES 256u
#define COMP_REC_IDENTITY_MAPS 7u

typedef struct {
    bool (*read)(void *,uint32_t,uint8_t *,size_t);
    bool (*program)(void *,uint32_t,const uint8_t *,size_t);
    bool (*erase)(void *,uint32_t);
    void *context;
} comp_rec_identity_port_t;
typedef struct {uint32_t recording_id;uint64_t session_id;} comp_rec_identity_map_t;
typedef struct {
    uint64_t sequence,format_epoch,next_session_id;
    uint8_t device_uid[12],count;
    comp_rec_identity_map_t maps[COMP_REC_IDENTITY_MAPS];
} comp_rec_identity_record_t;
typedef struct {
    comp_rec_identity_port_t port;
    comp_rec_identity_record_t record;
    uint8_t next_slot[2];
    bool ready,loaded,current_copy[2];
} comp_rec_identity_t;

/* Read-only: scan whole banks, reject foreign UID/format, nonblank media with
 * no valid root, conflicting equal sequences, and identity regression.
 * Failed write/readback poisons the object until an explicit remount. */
bool comp_rec_identity_mount(comp_rec_identity_t *,const comp_rec_identity_port_t *,const uint8_t uid[12]);
/* live_ids is the current physical catalog. Remove only mappings whose IDs
 * really left that catalog. Never assign an existing live recording a new
 * session. bootstrap_epoch must be hardware entropy only on first creation;
 * it is ignored once a durable namespace exists. Allocation gaps are legal. */
bool comp_rec_identity_reserve(comp_rec_identity_t *,uint32_t recording_id,
    const uint32_t *live_ids,size_t live_count,uint64_t bootstrap_epoch,uint64_t *session_id);
bool comp_rec_identity_find(const comp_rec_identity_t *,uint32_t recording_id,uint64_t *session_id);
/* One allocation per logical recording, before enabling the microphone.
 * Retains all existing V1 maps and the established random format epoch.
 * Both copies are read back before return; failed/uncertain allocation leaves
 * the output unchanged and requires remount. Gaps are legal, reuse is not.
 * Subsequent segment reservations copy this ID into their owned descriptors;
 * neither segment rollover nor BLE reconnection allocates another session. */
bool comp_rec_identity_allocate_session(comp_rec_identity_t *,uint64_t bootstrap_epoch,
    uint64_t *session_id);
#endif
