#ifndef COMPANION_WBA_FLASH_MIGRATION_H
#define COMPANION_WBA_FLASH_MIGRATION_H
#include "wba_shared_pool.h"

/* Lossless V1 -> V2 relocation transaction. This is deliberately separate
 * from V2 activation: imported ownership, a compatible resident boot, and the
 * recording/update adapters must all be ready before a product uses V2. */
#define COMP_WBA_MIGRATION_BOOT_GENERATION 2u
#define COMP_WBA_MIGRATION_ROOT_A UINT32_C(0xF08000)
#define COMP_WBA_MIGRATION_ROOT_B UINT32_C(0xF09000)
#define COMP_WBA_MIGRATION_UI_BACKUP UINT32_C(0xD00000)
#define COMP_WBA_MIGRATION_TAIL_BACKUP UINT32_C(0xF00000)
#define COMP_WBA_MIGRATION_CATALOG_BACKUP UINT32_C(0xF06000)
#define COMP_WBA_MIGRATION_BACKUP_END UINT32_C(0xF0A000)
#define COMP_WBA_V2_RECORDING_RESOURCE_BASE UINT32_C(0x1B0000)
#define COMP_WBA_MIGRATION_WIRE_BYTES 256u

typedef enum {
    COMP_WBA_MIGRATION_BACKUP_UI=1,
    COMP_WBA_MIGRATION_BACKUP_TAIL=2,
    COMP_WBA_MIGRATION_BACKUP_CATALOG=3,
    COMP_WBA_MIGRATION_ANNOUNCE=4,
    COMP_WBA_MIGRATION_MOVE_RECORDING=5,
    COMP_WBA_MIGRATION_MOVE_RESOURCE=6,
    COMP_WBA_MIGRATION_RESTORE_SYSTEM=7,
    COMP_WBA_MIGRATION_RESTORE_CATALOG=8,
    COMP_WBA_MIGRATION_CLEAR_WORKSPACE=9,
    COMP_WBA_MIGRATION_RELOCATED=10,
    COMP_WBA_MIGRATION_IMPORTING=11,
    COMP_WBA_MIGRATION_OWNERSHIP_READY=12
} comp_wba_migration_phase_t;

typedef struct {
    /* Must inspect the actual resident boot identity, idle update/rollback
     * state, supported old catalogs/resources/settings and unassigned space.
     * A UI choice or received package version is not resident boot evidence.
     * Called before first write and before the first destructive V1 change. */
    bool (*authorize)(void *);
    /* Must exclude capture, OTA, resource writes and any other Flash writer
     * for the lifetime of the transaction, including across restart. */
    bool (*exclusive_idle)(void *);
    void *context;
} comp_wba_migration_gate_t;

typedef struct {
    comp_wba_pool_port_t port;
    comp_wba_migration_gate_t gate;
    uint64_t sequence,format_epoch;
    uint32_t active_offset,cursor;
    uint8_t device_uid[12],source_sha256[4][32];
    uint8_t phase,next_slot[4],current_mask;
    bool diagnostic_present,ready,loaded;
} comp_wba_migration_t;

/* Read-only discovery. Unknown/future/foreign/conflicting migration roots
 * fail closed. Partial first-ever roots with no valid peer are protected;
 * no old data has been changed in that case. epoch must be durable CSI1's
 * epoch, or one established by the future compatible boot initializer. */
bool comp_wba_migration_mount(comp_wba_migration_t *,const comp_wba_pool_port_t *,
    const comp_wba_migration_gate_t *,const uint8_t uid[12],uint64_t epoch);
/* Explicit foreground transaction. Never discards an unsynced recording.
 * Only inactive legacy OTA backup space is reused after authorize succeeds. */
bool comp_wba_migration_begin(comp_wba_migration_t *);
/* First-root recovery only: durable epoch and verified unchanged V1 sources
 * reproduce the exact first intent. Finish compatible torn bits without
 * erasing unknown metadata. A valid/foreign/future/later intent is refused. */
bool comp_wba_migration_recover_begin(comp_wba_migration_t *);
/* Caller-owned 4 KiB scratch (not a second persistent recording buffer).
 * At most one data sector is erased per call; root rotation may erase a
 * metadata sector. Commit/repair both roots before a subsequent destructive
 * step. A failed/uncertain operation poisons this object until remount.
 * relocated=true does NOT mean V2 is mounted or safe to activate. */
bool comp_wba_migration_poll(comp_wba_migration_t *,uint8_t *scratch,
    size_t scratch_bytes,bool *relocated);
/* Verify all relocated bytes and retained backup fingerprints, read-only. */
bool comp_wba_migration_verify(comp_wba_migration_t *);
/* Builds exact fixed extents from the verified old catalog, retains a sealed
 * lease for ALL migration backups, and initializes the imported CPL2 roots.
 * Does not enable recording/update writers. Only a future compatible boot
 * and both production adapters may switch OWNERSHIP_READY into ACTIVE. */
bool comp_wba_migration_import_pool(comp_wba_migration_t *,comp_wba_pool_t *);

#endif
