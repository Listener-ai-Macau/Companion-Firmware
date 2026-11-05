#ifndef COMP_V11_OTA_GATT_H
#define COMP_V11_OTA_GATT_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#define COMP_V11_OTA_CONTROL_BYTES 40u
/* New NOR-only geometry adds an explicit target to the protected receipt.
 * Legacy installed devices retain their exact56-byte WSI3 contract. */
#if defined(COMP_WBA_INTERNAL_NVM_KIB) && COMP_WBA_INTERNAL_NVM_KIB == 0u
#define COMP_V11_OTA_TARGET_BOUND_IDENTITY 1
#define COMP_V11_OTA_IDENTITY_BYTES 60u
#else
#define COMP_V11_OTA_TARGET_BOUND_IDENTITY 0
#define COMP_V11_OTA_IDENTITY_BYTES 56u
#endif
#define COMP_V11_OTA_VALUE_BYTES 509u
#define COMP_V11_OTA_FILE_BYTES (COMP_V11_OTA_VALUE_BYTES-4u)
/* Durable checkpoints and physical RAM have independent lifetimes. A long
 * stream starts with16 maximum-size slots plus one ordered control slot.
 * An accepted BEGIN packs smaller values into the same byte lease; its
 * protected receipt advertises the actual generation-bound slot count. Queue
 * capacity is enforced by host device credits, not OS write completion.
 * Saturation fails this OTA in foreground; it never pauses global HCI flow. */
#define COMP_V11_OTA_QUEUE_CHUNKS 16u
#define COMP_V11_OTA_MAX_QUEUE_CHUNKS 64u
#define COMP_V11_OTA_WINDOW_CHUNKS 64u
/* WOC5 retains WOC4 durable fields and appends current BLK1 metadata. */
#define COMP_V11_OTA_STATUS_BYTES 64u
typedef struct {
    bool (*control)(void *,const uint8_t *,size_t);
    bool (*data)(void *,const uint8_t *,size_t);
    size_t (*status)(void *,uint8_t *,size_t);
    void *context;
    /* Foreground serialized lease. Live/paused encoder cannot lend its arena.
     * Queued writes and a partial ACI event retain the lease until retired. */
    void *(*workspace_claim)(void *,size_t);
    void (*workspace_release)(void *,void *);
    uint32_t (*now_ms)(void *);
    void (*connection)(void *,bool encrypted);
} comp_v11_ota_gatt_ports_t;
/* Callback-to-worker residence and call elapsed times can overlap. They are
 * queue/service boundaries, not RF airtime or an additive wall-clock ledger. */
typedef struct {
    uint32_t received,processed,queue_us,queue_max_us,data_us,data_max_us;
    uint32_t status_calls,status_us,status_max_us,status_skips,peak_queue,overflow;
} comp_v11_ota_gatt_timing_t;
const comp_v11_ota_gatt_timing_t *comp_v11_ota_gatt_timing(void);
/* Payload notification ACI outcomes only. Local readable-value updates are
 * excluded. Counts/time do not represent peer delivery or durable receipt. */
typedef struct {
    uint32_t notify_calls,not_accepted,owner_invalidations,last_status,max_us,flags;
    uint32_t partial_data_notifies;
} comp_v11_ota_publish_diagnostics_t;
const comp_v11_ota_publish_diagnostics_t *comp_v11_ota_gatt_publish_diagnostics(void);
/* Mutually exclusive device wall time: first COMPLETE DATA enqueue through
 * first foreground status observing the whole file durable, before its ACI
 * publication. EMPTY/READY describe complete-command availability, not RF/CPU.
 * Nested event delivery cannot replace DATA or STATUS with READY. 36 bytes;
 * no payload copy, hot UART output or additional controller command. */
typedef struct {
    uint32_t empty_us,ready_us,data_us,status_us,other_us,span_us;
    uint32_t start_us,last_us;
    uint8_t phase,started,running,invalid;
} comp_v11_ota_phase_timing_t;
const comp_v11_ota_phase_timing_t *comp_v11_ota_gatt_phase_timing(void);
/* Diagnostic wall contexts, not CPU utilization or RF attribution. Each
 * EMPTY/READY row adds exactly to its original parent, without changing
 * admission, processing order, status, clocks or the payload timer. Nested
 * callers restore their previous context; no resident payload is added. */
enum {COMP_OTA_WALL_OUTSIDE,COMP_OTA_WALL_UPDATE_OTHER,COMP_OTA_WALL_GATT_OTHER,
      COMP_OTA_WALL_SEQ_RUN,COMP_OTA_WALL_BLE_OTHER,COMP_OTA_WALL_PRODUCT_OTHER,
      COMP_OTA_WALL_PRODUCT_HAL,COMP_OTA_WALL_PRODUCT_RECORDER,
      COMP_OTA_WALL_PRODUCT_RUNTIME,COMP_OTA_WALL_PRODUCT_PRESENTER,
      COMP_OTA_WALL_PRODUCT_RENDER,COMP_OTA_WALL_CONTEXT_COUNT};
typedef struct {uint32_t empty_us[COMP_OTA_WALL_CONTEXT_COUNT],ready_us[COMP_OTA_WALL_CONTEXT_COUNT];uint32_t ready_yields;uint8_t context;} comp_v11_ota_wall_context_t;
void comp_v11_ota_gatt_wall_note_ready_yield(void);
uint8_t comp_v11_ota_gatt_wall_context(uint8_t context);
const comp_v11_ota_wall_context_t *comp_v11_ota_gatt_wall_context_timing(void);

bool comp_v11_ota_gatt_init(const comp_v11_ota_gatt_ports_t *);
void comp_v11_ota_gatt_connection(bool encrypted);
/* Complete queued commands and a deferred overrun abort are runnable now.
 * Partial writes, an in-progress callback and ACI resource retries still wait
 * for their existing events/deadlines; this query performs no work. */
bool comp_v11_ota_gatt_foreground_pending(void);
/* WSI3: actual running App/UI versions, static extent, outstanding workspace,
 * ready flag, signed installed payload SHA. Read-only, never a host ACK. */
void comp_v11_ota_gatt_identity(const uint8_t identity[COMP_V11_OTA_IDENTITY_BYTES]);
/* At most one queued command per foreground poll; no NOR or signature work
 * inside the radio event callback. Status becomes visible after the ordered
 * window drains, so a host acknowledgement never outruns its queued SYNC. */
void comp_v11_ota_gatt_poll(void);
/* Product foreground only: preserve the ordinary single-command poll, then
 * optionally one additional COMPLETE DATA. Never cross a control fence or
 * connection epoch, never append after the first command takes >=4ms.
 * At most two commands; existing NOR cooperative radio pumping stays active. */
void comp_v11_ota_gatt_poll_slice(void);
/* Storage-worker-only same-page lookahead. It neither admits nor retires the
 * next command; the active worker pins both slots across nested radio events. */
size_t comp_v11_ota_gatt_copy_following_data(uint32_t expected_offset,
    uint32_t expected_size,uint16_t maximum_payload,uint8_t *out,size_t capacity);
#endif
