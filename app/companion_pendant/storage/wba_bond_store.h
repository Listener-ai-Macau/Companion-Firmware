#ifndef COMPANION_WBA_BOND_STORE_H
#define COMPANION_WBA_BOND_STORE_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Backing storage for the EXISTING BLE RAM cache and device identity, not a
 * second cache or a replacement BLE database. No allocation, key logging or
 * serialization of SDK-private records. A board adapter is still required.
 * CRC/UID detect corruption/wrong media; they are not encryption/authentication.
 */
#define COMP_BOND_BANK_BYTES 4096u
#define COMP_BOND_HEADER_BYTES 40u
#define COMP_BOND_STEP_BYTES 128u
#define COMP_BOND_MAX_BYTES (COMP_BOND_BANK_BYTES-COMP_BOND_HEADER_BYTES)
typedef enum {
    COMP_BOND_IO_OK, COMP_BOND_IO_PENDING, COMP_BOND_IO_ERROR
} comp_bond_io_t;
typedef enum {
    COMP_BOND_READY, COMP_BOND_EMPTY, COMP_BOND_PENDING,
    COMP_BOND_STALE, COMP_BOND_CORRUPT, COMP_BOND_IO_FAILED,
    COMP_BOND_BAD_ARGUMENT
} comp_bond_result_t;
typedef struct {
    bool (*read)(void *,uint32_t,uint8_t *,size_t);
    bool (*program)(void *,uint32_t,const uint8_t *,size_t);
    /* PENDING retains the same physical erase owner. ERROR may be returned
     * only once that owner is retired; uncertain NOR WIP must remain pending. */
    comp_bond_io_t (*erase_step)(void *,uint32_t);
    /* Logical source may join the existing host cache and identity without
     * copying them into a second resident buffer. Foreground calls only. */
    bool (*source_read)(void *,uint32_t,uint8_t *,size_t);
    bool (*restore)(void *,uint32_t,const uint8_t *,size_t);
    uint32_t (*source_revision)(void *);
    void *context;
    uint32_t bank[2],payload_bytes;
    uint8_t uid[12];
} comp_bond_config_t;
typedef struct {
    comp_bond_config_t config;
    uint32_t generation,stored_crc,source_revision,source_crc,offset,verify_crc;
    uint8_t active,target,phase;
    comp_bond_result_t result;
} comp_bond_store_t;

/* Startup-only read/restore, BEFORE starting the host stack. Validates both
 * complete images before choosing one. No valid image + nonblank/foreign
 * media fails closed; never generates keys or clears a peer automatically. */
comp_bond_result_t comp_bond_store_mount(comp_bond_store_t *,const comp_bond_config_t *);
/* The caller explicitly requests persisting its current RAM cache. A changed
 * source revision aborts BEFORE publication and leaves the old bank intact. */
comp_bond_result_t comp_bond_store_begin(comp_bond_store_t *);
/* Startup migration only: a separate durable IMPORTING receipt must already
 * establish these exact banks and the original internal cache as authority.
 * This permits restarting a torn FIRST import, never normal corruption
 * recovery or overwriting an existing committed external image. */
comp_bond_result_t comp_bond_store_import_begin(comp_bond_store_t *);
/* One erase-status step or <=128B program/readback per call. Never discard a
 * pending erase owner when source changes. The adapter/foreground must still
 * coordinate recording, updates, power and NOR deadlines. */
comp_bond_result_t comp_bond_store_step(comp_bond_store_t *);
#endif
