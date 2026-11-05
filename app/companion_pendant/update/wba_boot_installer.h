#ifndef COMPANION_WBA_BOOT_INSTALLER_H
#define COMPANION_WBA_BOOT_INSTALLER_H

#include "wba_update_service.h"

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_WBA_BOOT_INTERNAL_BYTES COMP_WBA_BOOT_APP_OFFSET
#define COMP_WBA_BOOT_RECORD_MAGIC UINT32_C(0x31544257) /* WBT1 */

typedef enum {
    COMP_WBA_BOOT_EMPTY = 0u,
    COMP_WBA_BOOT_CANDIDATE_READY = 1u,
    COMP_WBA_BOOT_BACKUP_VALID = 2u,
    COMP_WBA_BOOT_INSTALLING = 3u,
    COMP_WBA_BOOT_TRIAL_READY = 4u,
    COMP_WBA_BOOT_AWAIT_CONFIRM = 5u,
    COMP_WBA_BOOT_CONFIRMED = 6u,
    COMP_WBA_BOOT_ROLLBACK = 7u,
    COMP_WBA_BOOT_ROLLED_BACK = 8u,
    COMP_WBA_BOOT_FAILED = 9u,
} comp_wba_boot_phase_t;

typedef enum {
    COMP_WBA_BOOT_ACTION_NONE = 0u,
    COMP_WBA_BOOT_ACTION_WORK = 1u,
    COMP_WBA_BOOT_ACTION_BOOT_APP = 2u,
    COMP_WBA_BOOT_ACTION_RECOVERY = 3u,
} comp_wba_boot_action_t;

typedef struct {
    uint32_t magic;
    uint32_t sequence;
    uint8_t phase;
    uint8_t auth_length;
    uint16_t reserved;
    /* Confirmed component floors are carried in every candidate record so the
     * resident bootloader does not rely on its own (possibly older) build
     * version for anti-rollback decisions. */
    uint32_t installed_firmware_version;
    uint32_t installed_ui_version;
    comp_wba_update_manifest_t candidate;
    uint8_t authentication[COMP_WBA_UPDATE_AUTH_MAX_BYTES];
    uint32_t previous_version;
    uint32_t previous_size;
    uint8_t previous_sha256[COMP_WBA_UPDATE_SHA256_BYTES];
    uint32_t crc32;
} comp_wba_boot_record_t;

typedef struct {
    bool (*authorize_manifest)(void *context,
                               const comp_wba_update_manifest_t *manifest,
                               const uint8_t *authentication,
                               uint8_t authentication_length);
    bool (*nor_read)(void *context,uint32_t offset,uint8_t *data,size_t length);
    bool (*nor_erase_4k)(void *context,uint32_t offset);
    bool (*nor_write)(void *context,uint32_t offset,
                      const uint8_t *data,size_t length);
    bool (*flash_read)(void *context,uint32_t address,uint8_t *data,size_t length);
    bool (*flash_erase_page)(void *context,uint32_t address);
    bool (*flash_write)(void *context,uint32_t address,
                        const uint8_t *data,size_t length);
    bool (*metadata_load)(void *context,comp_wba_boot_record_t *record);
    bool (*metadata_store)(void *context,const comp_wba_boot_record_t *record);
    void *context;
} comp_wba_boot_ports_t;

typedef struct {
    comp_wba_boot_ports_t ports;
    uint32_t target_family;
    uint32_t board_target;
    uint32_t flash_base;
    uint32_t flash_page_bytes;
    uint32_t sram_base;
    uint32_t sram_bytes;
    uint32_t installed_version;
    uint32_t installed_ui_version;
    uint32_t installed_image_size;
} comp_wba_boot_config_t;

typedef struct {
    comp_wba_boot_config_t config;
    comp_wba_boot_record_t record;
    /* COPY and readback verification run in separate foreground phases.
     * Finalize the source digest before handing this workspace to VERIFY.
     * The running app also borrows it for trial-image confirmation; it never
     * executes resident-boot copying while that confirmation is in progress. */
    union {
        comp_wba_update_sha256_t source_hash;
        comp_wba_update_sha256_t verify_hash;
    };
    uint32_t cursor;
    uint8_t operation;
    uint8_t action;
    bool bootloader_context;
    bool loaded;
} comp_wba_boot_installer_t;

bool comp_wba_boot_record_valid(const comp_wba_boot_record_t *record);
bool comp_wba_boot_init(comp_wba_boot_installer_t *installer,
                        const comp_wba_boot_config_t *config,
                        bool bootloader_context);

/* Application-side activation adapter. It only publishes an authenticated,
 * verified staging candidate to the atomic boot metadata. It never erases the
 * running application. */
comp_wba_update_step_result_t comp_wba_boot_activate_step(
    void *context,const comp_wba_update_manifest_t *manifest,
    const uint8_t *authentication,uint8_t authentication_length,
    uint32_t staging_offset,uint32_t size_bytes,
    uint8_t *scratch,size_t scratch_bytes);

/* Resident-bootloader foreground step. One call erases at most one page or
 * copies/verifies at most scratch_bytes. */
comp_wba_boot_action_t comp_wba_boot_poll(comp_wba_boot_installer_t *installer,
                                          uint8_t *scratch,
                                          size_t scratch_bytes);

/* Called by the relocated application only after its POST and required
 * peripherals are ready. For a UI image the caller must first mount and
 * validate the new resource generation. An unconfirmed target is restored on
 * the next boot. Confirmation is persisted before success returns. */
bool comp_wba_boot_confirm(comp_wba_boot_installer_t *installer,
                           uint32_t running_version,
                           const uint8_t running_sha256[32]);

#ifdef __cplusplus
}
#endif

#endif
