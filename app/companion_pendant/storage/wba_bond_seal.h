#ifndef COMPANION_WBA_BOND_SEAL_H
#define COMPANION_WBA_BOND_SEAL_H
#include "wba_bond_store.h"

/* A permanent, never-erased provisioning state in its own metadata sector.
 * CRC/UID are corruption/ownership checks, not cryptographic authentication,
 * anti-replay or encryption. All external persistence remains DEV-gated.
 * No heap, resident cache, keys or second copy of the host database. */
#define COMP_BOND_SEAL_HEADER_BYTES 48u
typedef enum {
    COMP_BOND_SEAL_BLANK, COMP_BOND_SEAL_NEW_PENDING, COMP_BOND_SEAL_COMPLETE,
    COMP_BOND_SEAL_INVALID, COMP_BOND_SEAL_IO_FAILED, COMP_BOND_SEAL_UNOWNED
} comp_bond_seal_result_t;

comp_bond_seal_result_t comp_bond_seal_inspect(const comp_bond_config_t *,uint32_t);
/* Explicit first-device profile only, and both COMPLETE bond pages must be
 * blank. A torn initial header may be finished by programming the same exact
 * deterministic intent, never erasing. Completed/foreign/noncompatible pages
 * cannot regain first-provision rights. No entropy or host start precedes it. */
comp_bond_seal_result_t comp_bond_seal_begin_new(const comp_bond_config_t *,uint32_t,bool);
/* Call only after the complete first BND1 payload/identity has read back.
 * The monotone phase word is committed BEFORE HOST_BLE_Init/advertisement. */
comp_bond_seal_result_t comp_bond_seal_complete_new(const comp_bond_config_t *,uint32_t);
/* Existing-device bridge only: internal COMMITTED and a complete external
 * current copy supply authority. Blank/torn same migration seal is finished
 * without erasing. The internal NVM may be reclaimed only after this returns
 * COMPLETE and the installer independently reads the seal and both copies. */
comp_bond_seal_result_t comp_bond_seal_complete_migration(const comp_bond_config_t *,uint32_t);
#endif
