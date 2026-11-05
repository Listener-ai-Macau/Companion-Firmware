#ifndef COMPANION_WBA_SHARED_POOL_H
#define COMPANION_WBA_SHARED_POOL_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Versioned target geometry. These do not change the mounted V1 addresses. */
#define COMP_WBA_V2_RESOURCE_BYTES UINT32_C(0x1F0000)
#define COMP_WBA_V2_SYSTEM_BASE COMP_WBA_V2_RESOURCE_BYTES
#define COMP_WBA_V2_LAYOUT_A UINT32_C(0x1F8000)
#define COMP_WBA_V2_LAYOUT_B UINT32_C(0x1F9000)
#define COMP_WBA_V2_CATALOG_BASE UINT32_C(0x200000)
#define COMP_WBA_V2_POOL_META_BASE UINT32_C(0x202000)
#define COMP_WBA_V2_POOL_META_BYTES UINT32_C(0x4000)
#define COMP_WBA_V2_POOL_BASE UINT32_C(0x210000)
#define COMP_WBA_V2_POOL_BYTES UINT32_C(0xDF0000)
#define COMP_WBA_POOL_MAX_LEASES 12u
#define COMP_WBA_POOL_MAX_RESERVE 3u
#define COMP_WBA_POOL_WIRE_BYTES 1024u
#define COMP_WBA_POOL_ERASE_BYTES 4096u

typedef enum {
    COMP_WBA_POOL_RECORDING=1, COMP_WBA_POOL_UPDATE=2,
    COMP_WBA_POOL_FIRMWARE_BACKUP=3, COMP_WBA_POOL_RESOURCE_BACKUP=4,
    COMP_WBA_POOL_MIGRATION=5
} comp_wba_pool_owner_t;
typedef enum {
    COMP_WBA_POOL_RESERVED=1, COMP_WBA_POOL_PREPARING=2,
    COMP_WBA_POOL_WRITING=3, COMP_WBA_POOL_SEALED=4, COMP_WBA_POOL_ERASING=5
} comp_wba_pool_state_t;
typedef struct {
    bool (*read)(void *,uint32_t,uint8_t *,size_t);
    bool (*program)(void *,uint32_t,const uint8_t *,size_t);
    bool (*erase)(void *,uint32_t);
    void *context;
} comp_wba_pool_port_t;
typedef struct {
    uint64_t id,transaction_id;
    uint32_t object_id,start,bytes,erase_cursor,payload_bytes;
    uint8_t sha256[32],owner,state;
} comp_wba_pool_lease_t;
typedef struct {
    uint32_t object_id,bytes,payload_bytes;
    uint8_t sha256[32],owner;
} comp_wba_pool_request_t;
/* Snapshot entries stay in NOR, not in a second RAM catalog. All mutation,
 * lookup and payload verification APIs are foreground, capture-off operations.
 * cached free/largest values can be read without SPI during capture. */
typedef struct {
    comp_wba_pool_port_t port;
    uint64_t sequence,next_lease_id,next_transaction_id,format_epoch;
    uint64_t pending_id;
    uint32_t active_offset,pending_cursor,free_bytes,largest_extent;
    uint8_t device_uid[12],next_slot[2],current_mask,count;
    bool ready,loaded;
} comp_wba_pool_t;

/* Detect future layout ownership before any V1 writer initializes. Read errors
 * are errors, never evidence of blank media. This does not activate V2. */
bool comp_wba_v2_layout_absent(const comp_wba_pool_port_t *);
/* Read-only; blank metadata is uninitialized. Nonblank invalid, unsupported,
 * foreign or conflicting roots remain protected. */
bool comp_wba_pool_mount(comp_wba_pool_t *,const comp_wba_pool_port_t *,
                         const uint8_t uid[12],uint64_t format_epoch);
/* Explicit empty-media initializer: verifies ALL pool bytes are erased before
 * writing roots. Never use it as an old-data migration or factory reset. */
bool comp_wba_pool_initialize_blank(comp_wba_pool_t *);
/* Called ONLY after a durable CFL IMPORTING intent verified the moved V1
 * payloads/catalog and blank metadata workspace. Deterministic initial roots
 * can finish a compatible torn program without erasing metadata or payload.
 * Any foreign/different snapshot or occupied unused slot is rejected. */
bool comp_wba_pool_initialize_import(comp_wba_pool_t *,const comp_wba_pool_port_t *,
    const uint8_t uid[12],uint64_t epoch,const comp_wba_pool_lease_t *,size_t count,
    uint64_t next_id,uint64_t next_transaction);
bool comp_wba_pool_find(comp_wba_pool_t *,uint64_t id,comp_wba_pool_lease_t *);
/* Atomic one-to-three reservations share a transaction; no implicit eviction. */
bool comp_wba_pool_reserve(comp_wba_pool_t *,const comp_wba_pool_request_t *,
                           size_t count,comp_wba_pool_lease_t *leases);
bool comp_wba_pool_prepare(comp_wba_pool_t *,uint64_t id);
/* Erases at most one payload sector; metadata append can rotate banks.
 * Verify erase before cursor checkpoint. Interrupted
 * preparation/retirement resumes conservatively. done only follows durable
 * WRITING/removal, never physical erase alone. */
bool comp_wba_pool_poll_erase(comp_wba_pool_t *,uint64_t id,bool *done);
/* Write must stay in the exact WRITING lease; no metadata/system/other owner. */
bool comp_wba_pool_write(comp_wba_pool_t *,uint64_t id,uint32_t offset,
                         const uint8_t *,size_t);
/* Verify actual NOR bytes with SHA256 before sealing. CRC is only metadata
 * damage detection; authorization of update/ACK/loss belongs to the caller. */
bool comp_wba_pool_seal(comp_wba_pool_t *,uint64_t id,uint32_t bytes,
                        const uint8_t sha256[32]);
bool comp_wba_pool_retire(comp_wba_pool_t *,uint64_t id,
                          uint64_t transaction_id,const uint8_t sha256[32]);
#endif
