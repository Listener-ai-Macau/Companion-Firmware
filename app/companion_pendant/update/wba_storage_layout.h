#ifndef COMPANION_WBA_STORAGE_LAYOUT_H
#define COMPANION_WBA_STORAGE_LAYOUT_H

#include <stdint.h>

/* Layout 3: resource-bank size + all remaining dynamic storage on WBA.
 * Old media needs explicit development formatting, never silent migration. */
#define COMP_WBA_NOR_LAYOUT_VERSION 3u
#ifndef COMP_WBA_NOR_TOTAL_BYTES
#define COMP_WBA_NOR_TOTAL_BYTES UINT32_C(0x1000000)
#endif
#define COMP_WBA_NOR_SECTOR_BYTES UINT32_C(0x1000)

#define COMP_WBA_NOR_UI_BASE UINT32_C(0x000000)
#ifndef COMP_WBA_NOR_UI_BYTES
/* Build tools supply the selected bank's actual extent; host/default 1 MiB. */
#define COMP_WBA_NOR_UI_BYTES UINT32_C(0x100000)
#endif
#define COMP_WBA_NOR_DYNAMIC_BASE (COMP_WBA_NOR_UI_BASE + COMP_WBA_NOR_UI_BYTES)
#define COMP_WBA_NOR_DYNAMIC_BYTES (COMP_WBA_NOR_TOTAL_BYTES - COMP_WBA_NOR_DYNAMIC_BASE)

/* Small durable roots/catalogs live inside the dynamic region. The remaining
 * arena belongs to recording until an update claims a bounded tail extent. */
#define COMP_WBA_NOR_SYSTEM_BYTES UINT32_C(0x20000)
#define COMP_WBA_NOR_RECORDING_CATALOG (COMP_WBA_NOR_DYNAMIC_BASE + UINT32_C(0x10000))
#define COMP_WBA_NOR_RECORDING_BASE (COMP_WBA_NOR_DYNAMIC_BASE + COMP_WBA_NOR_SYSTEM_BYTES)
#define COMP_WBA_NOR_RECORDING_DATA_BYTES (COMP_WBA_NOR_DYNAMIC_BYTES - COMP_WBA_NOR_SYSTEM_BYTES)
/* Last two journal sectors are virtual, mapped to RECORDING_CATALOG. */
#define COMP_WBA_NOR_RECORDING_BYTES (COMP_WBA_NOR_RECORDING_DATA_BYTES + UINT32_C(0x2000))
#define COMP_WBA_NOR_RECORDING_END COMP_WBA_NOR_TOTAL_BYTES

#define COMP_WBA_NOR_PREFS_A COMP_WBA_NOR_DYNAMIC_BASE
#define COMP_WBA_NOR_PREFS_B (COMP_WBA_NOR_DYNAMIC_BASE + UINT32_C(0x1000))
#define COMP_WBA_NOR_UPDATE_META_A (COMP_WBA_NOR_DYNAMIC_BASE + UINT32_C(0x2000))
#define COMP_WBA_NOR_UPDATE_META_B (COMP_WBA_NOR_DYNAMIC_BASE + UINT32_C(0x3000))
#define COMP_WBA_NOR_POWER_SETTINGS (COMP_WBA_NOR_DYNAMIC_BASE + UINT32_C(0x4000))
#define COMP_WBA_NOR_RECORDING_IDENTITY_BASE (COMP_WBA_NOR_DYNAMIC_BASE + UINT32_C(0x6000))
#define COMP_WBA_NOR_RECORDING_IDENTITY_BYTES UINT32_C(0x002000)
#define COMP_WBA_NOR_LAYOUT_A (COMP_WBA_NOR_DYNAMIC_BASE + UINT32_C(0x8000))
#define COMP_WBA_NOR_LAYOUT_B (COMP_WBA_NOR_DYNAMIC_BASE + UINT32_C(0x9000))
/* Optional external BLE persistence stays INSIDE the existing metadata area.
 * 0xA000/B000 are confirmed-system receipts and must never be reused. The
 * system layout copier preserves these C000/D000 pages when resources grow. */
#define COMP_WBA_NOR_BOND_A (COMP_WBA_NOR_DYNAMIC_BASE + UINT32_C(0xC000))
#define COMP_WBA_NOR_BOND_B (COMP_WBA_NOR_DYNAMIC_BASE + UINT32_C(0xD000))
/* Permanent provisioning authority: never erased by runtime, OTA or factory
 * writers. E000 was unused in the pinned layout; no recording capacity moves. */
#define COMP_WBA_NOR_BOND_SEAL (COMP_WBA_NOR_DYNAMIC_BASE + UINT32_C(0xE000))
#define COMP_WBA_NOR_BOND_PROTECTED_END (COMP_WBA_NOR_BOND_SEAL + COMP_WBA_NOR_SECTOR_BYTES)
/* Last unused system sector. Preserve it during layout relocation, append
 * only, and never reclaim it for recordings even with logging disabled. */
#define COMP_WBA_NOR_DIAGNOSTIC_BASE (COMP_WBA_NOR_DYNAMIC_BASE + UINT32_C(0xF000))
#define COMP_WBA_NOR_DIAGNOSTIC_BYTES COMP_WBA_NOR_SECTOR_BYTES
#if COMP_WBA_NOR_DIAGNOSTIC_BASE < COMP_WBA_NOR_BOND_PROTECTED_END || \
    COMP_WBA_NOR_DIAGNOSTIC_BASE + COMP_WBA_NOR_DIAGNOSTIC_BYTES != COMP_WBA_NOR_RECORDING_CATALOG
#error "Reset journal overlaps bonds or recording catalog"
#endif
/* Device-owned pet profile/explicit memories use the pre-existing gap between
 * the legacy recording catalog and V2 catalogs. No payload capacity moves.
 * Existing system-layout relocation copies this gap byte-for-byte. */
#define COMP_WBA_NOR_PET_PROFILE_A (COMP_WBA_NOR_DYNAMIC_BASE + UINT32_C(0x12000))
#define COMP_WBA_NOR_PET_PROFILE_B (COMP_WBA_NOR_DYNAMIC_BASE + UINT32_C(0x13000))
#if COMP_WBA_NOR_PET_PROFILE_A != COMP_WBA_NOR_RECORDING_CATALOG + UINT32_C(0x2000) || \
    COMP_WBA_NOR_PET_PROFILE_B != COMP_WBA_NOR_PET_PROFILE_A + COMP_WBA_NOR_SECTOR_BYTES
#error "Pet profile overlaps legacy recording metadata"
#endif
#if COMP_WBA_NOR_BOND_PROTECTED_END > COMP_WBA_NOR_RECORDING_CATALOG
#error "External BLE persistence overlaps recording metadata"
#endif
/* Segmented-directory banks occupy previously unused dynamic metadata pages.
 * V1 still owns its existing catalog until the V2 service is explicitly wired. */
#define COMP_WBA_NOR_SEGMENT_CATALOG_A (COMP_WBA_NOR_DYNAMIC_BASE + UINT32_C(0x14000))
#define COMP_WBA_NOR_SEGMENT_CATALOG_B (COMP_WBA_NOR_DYNAMIC_BASE + UINT32_C(0x1A000))
#define COMP_WBA_NOR_SEGMENT_CATALOG_BANK_BYTES UINT32_C(0x6000)
#if COMP_WBA_NOR_PET_PROFILE_B + COMP_WBA_NOR_SECTOR_BYTES != COMP_WBA_NOR_SEGMENT_CATALOG_A
#error "Pet profile overlaps segmented recording metadata"
#endif

/* Boot-installer LOGICAL windows, not physical NOR partitions. The storage
 * adapter maps them to a durable, on-demand reservation in the shared arena. */
/* Disjoint virtual windows stay disjoint when the static bank grows. */
#define COMP_WBA_NOR_UPDATE_STAGING_BASE UINT32_C(0x10000000)
#define COMP_WBA_NOR_UPDATE_STAGING_BYTES \
    ((COMP_WBA_NOR_UI_BYTES > COMP_WBA_NOR_FIRMWARE_BACKUP_BYTES) ? \
     COMP_WBA_NOR_UI_BYTES : COMP_WBA_NOR_FIRMWARE_BACKUP_BYTES)

#define COMP_WBA_NOR_RESOURCE_BACKUP_BASE UINT32_C(0x20000000)
#define COMP_WBA_NOR_RESOURCE_BACKUP_BYTES COMP_WBA_NOR_UI_BYTES

#define COMP_WBA_NOR_FIRMWARE_BACKUP_BASE UINT32_C(0x30000000)
#define COMP_WBA_NOR_FIRMWARE_BACKUP_BYTES UINT32_C(0x100000)

#if COMP_WBA_NOR_RECORDING_BASE + COMP_WBA_NOR_RECORDING_DATA_BYTES != COMP_WBA_NOR_RECORDING_END
#error "WBA recording layout mismatch"
#endif
#if COMP_WBA_NOR_UI_BYTES + COMP_WBA_NOR_DYNAMIC_BYTES != COMP_WBA_NOR_TOTAL_BYTES
#error "WBA static/dynamic geometry mismatch"
#endif
#if COMP_WBA_NOR_DYNAMIC_BYTES <= COMP_WBA_NOR_SYSTEM_BYTES
#error "WBA dynamic storage has no payload arena"
#endif
#if COMP_WBA_NOR_SEGMENT_CATALOG_A < COMP_WBA_NOR_RECORDING_CATALOG + UINT32_C(0x2000) || \
    COMP_WBA_NOR_SEGMENT_CATALOG_A + COMP_WBA_NOR_SEGMENT_CATALOG_BANK_BYTES != COMP_WBA_NOR_SEGMENT_CATALOG_B || \
    COMP_WBA_NOR_SEGMENT_CATALOG_B + COMP_WBA_NOR_SEGMENT_CATALOG_BANK_BYTES != COMP_WBA_NOR_RECORDING_BASE
#error "WBA segmented directory overlaps an existing root or payload"
#endif

#endif
