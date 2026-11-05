#ifndef COMPANION_WBA_SYSTEM_RECEIVE_H
#define COMPANION_WBA_SYSTEM_RECEIVE_H
#include "wba_system_wire.h"

#define COMP_WBA_SYSTEM_RECORD_BYTES 488u
#define COMP_WBA_SYSTEM_RECEIVING 1u
#define COMP_WBA_SYSTEM_VERIFYING 2u
#define COMP_WBA_SYSTEM_PAIR_READY 3u
#define COMP_WBA_SYSTEM_RETIRED 4u
#define COMP_WBA_SYSTEM_ALLOCATE_NEW UINT32_MAX
#define COMP_WBA_SYSTEM_MAX_CHUNK_BYTES 509u

typedef struct {
    /* Blank means both journal prefixes were positively read as erased.
     * Unreadable, torn-only, foreign or conflicting metadata is an error.
     * Store returns success only after durable readback; ambiguous failures
     * poison this receiver until a new mount. The port enforces one writer.
     */
    bool (*load)(void *,uint8_t record[COMP_WBA_SYSTEM_RECORD_BYTES],bool *blank);
    bool (*store)(void *,const uint8_t record[COMP_WBA_SYSTEM_RECORD_BYTES]);
    bool (*idle)(void *);
    /* A single RAM/exclusive claim covers BOTH new payloads. This never
     * silently evicts recordings. It must restore exact_base on remount;
     * new allocation uses UINT32_MAX. Keep ambiguous claims until remount.
     * Base/extent validation is repeated before any erase/program.
     */
    bool (*claim)(void *,uint32_t bytes,uint32_t minimum_base,uint32_t exact_base,uint32_t *base);
    bool (*release)(void *,uint32_t base,uint32_t bytes);
    /* Only retire this updater's volatile claim after both journal prefixes
     * were positively read as blank; no erase or other owner's release.
     */
    bool (*reconcile_empty)(void *);
    /* Product coordinator must verify the running app's actual Flash hash
     * AND mounted resource bank's actual hash/generation before returning
     * true. A GATT ACK, version number, UI click or reset is insufficient.
     */
    bool (*running_pair_verified)(void *,const uint8_t wire[COMP_WBA_SYSTEM_WIRE_BYTES]);
    bool (*read)(void *,uint32_t address,uint8_t *,size_t);
    bool (*erase_sector)(void *,uint32_t address);
    bool (*program)(void *,uint32_t address,const uint8_t *,size_t);
    void *context;
} comp_wba_system_receive_ports_t;

typedef struct {
    comp_wba_system_receive_ports_t ports;
    comp_wba_update_p256_trust_t trust;
    uint32_t current_firmware,current_resources,current_static_bytes;
    /* Reusing the same resource generation is permitted only if its exact
     * currently trusted hash matches; a version alone cannot authorize it.
     */
    const uint8_t *current_resource_sha256;
} comp_wba_system_receive_config_t;

typedef struct {
    comp_wba_system_receive_config_t config;
    uint8_t record[COMP_WBA_SYSTEM_RECORD_BYTES];
    companion_sha256_t hash;
    uint32_t received[2],erased_until[2],verify_offset,verify_crc;
    uint8_t verify_component;
    bool mounted,loaded,usable;
} comp_wba_system_receiver_t;

bool comp_wba_system_record_valid(const uint8_t record[COMP_WBA_SYSTEM_RECORD_BYTES]);
bool comp_wba_system_receive_mount(comp_wba_system_receiver_t *,const comp_wba_system_receive_config_t *);
/* Explicit trusted first-intent retry, NOT a blank-media result. The caller
 * already verified a first-only torn hint, signed current receipt, both actual
 * running destinations and layout. No claim/release/write happens here. The
 * store port must authenticate the exact next record against torn media before
 * clearing it. Candidate version/signature/admission still run in begin(). */
bool comp_wba_system_receive_prepare_first_retry(comp_wba_system_receiver_t *,
    const comp_wba_system_receive_config_t *);
bool comp_wba_system_receive_begin(comp_wba_system_receiver_t *,const uint8_t *wire,size_t bytes);
/* Serial component0/1 writes with exact offsets. Duplicate already-written
 * bytes are compared, never counted twice. The borrower supplies >=length
 * distinct scratch for immediate readback; no hidden payload buffer is allocated.
 * Durable offsets advance at 4KiB boundaries or exact component completion.
 * Restart erases only the uncommitted sector before reaccepting its bytes.
 */
bool comp_wba_system_receive_data(comp_wba_system_receiver_t *,const uint8_t bundle_id[32],
    uint8_t component,uint32_t offset,const uint8_t *data,size_t length,
    uint8_t *scratch,size_t scratch_bytes);
/* Both streams must be complete. Each poll reads at most scratch_bytes.
 * PAIR_READY is durable only after BOTH staged SHA256/CRC checks. This is
 * input to the future resident installer, not installed/activated success.
 */
bool comp_wba_system_receive_finish(comp_wba_system_receiver_t *);
bool comp_wba_system_receive_poll(comp_wba_system_receiver_t *,uint8_t *scratch,size_t scratch_bytes);
bool comp_wba_system_receive_cancel(comp_wba_system_receiver_t *,const uint8_t bundle_id[32]);
bool comp_wba_system_receive_confirm(comp_wba_system_receiver_t *,const uint8_t bundle_id[32]);

#endif
