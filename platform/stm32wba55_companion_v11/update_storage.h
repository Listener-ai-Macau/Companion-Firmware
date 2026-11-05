#ifndef COMPANION_V11_UPDATE_STORAGE_H
#define COMPANION_V11_UPDATE_STORAGE_H

#include "spi_nor_stm32wba.h"
#include "wba_boot_installer.h"
#include "wba_update_manifest_wire.h"
#include "wba_update_metadata.h"
#include "wba_update_p256_hal.h"

#define COMP_V11_UPDATE_METADATA_MAGIC COMP_WBA_UPDATE_METADATA_MAGIC
typedef comp_wba_update_metadata_record_t comp_v11_update_metadata_t;

typedef struct {
    companion_spi_nor_stm32wba_t *nor;
    PKA_HandleTypeDef *hpka;
    bool (*pka_acquire)(void *context);
    void (*pka_release)(void *context);
    bool (*activity_idle)(void *context);
    /* App-only recording allocator: RAM reservation, exact tail, no eviction.
     * Claim is committed to WUS2 before any NOR erase/write. Boot remounts it.
     * Mandatory for app setup; resident boot uses the durable mapped extent.
     * A zero claim must reconcile release even if WUS2 is already free.
     * Ambiguous metadata writes retain the claim until an explicit remount. */
    bool (*workspace_reserve)(void *context,uint32_t bytes,uint32_t *physical_base);
    bool (*flash_read)(void *context,uint32_t address,uint8_t *data,size_t length);
    bool (*flash_erase_page)(void *context,uint32_t address);
    bool (*flash_write)(void *context,uint32_t address,const uint8_t *data,size_t length);
    void *context;
    const uint8_t *public_key_xy;
    uint32_t key_id;
    uint32_t pka_timeout_ms;
    uint32_t current_firmware_version;
    uint32_t current_ui_version;
    uint32_t current_app_version;
    uint32_t installed_image_size;
    uint32_t flash_base;
    uint32_t flash_page_bytes;
    uint32_t sram_base;
    uint32_t sram_bytes;
    uint16_t maximum_chunk_bytes;
    uint16_t default_window_chunks;
} comp_v11_update_storage_config_t;

typedef struct {
    comp_v11_update_storage_config_t config;
    comp_wba_update_p256_hal_t pka;
    comp_wba_update_p256_trust_t trust;
    comp_wba_update_service_t service;
    comp_wba_boot_installer_t installer;
    comp_wba_update_metadata_store_t metadata;
    uint8_t manifest_receipt[8];
    uint32_t next_staging_erase;
    /* Trial-image confirmation uses installer.verify_hash, whose resident
     * boot copy/verify phases cannot run in the application context. */
    uint32_t confirm_offset;
    uint32_t confirm_version;
    bool manifest_accepted;
    bool confirm_pending;
    bool confirm_failed;
    bool ready;
} comp_v11_update_storage_t;

/* Application facade. All calls are foreground/task-only. Staging sectors are
 * erased lazily at the first sequential DOV1 write, avoiding a multi-second
 * erase inside the manifest GATT request. */
bool comp_v11_update_storage_init(comp_v11_update_storage_t *storage,
                                  const comp_v11_update_storage_config_t *config);
bool comp_v11_update_storage_open_wire(comp_v11_update_storage_t *storage,
                                       const uint8_t *wire,size_t wire_bytes);
/* WMA1 || LE32(CRC32(WUM1 bytes 0..139)); distinct from the writable
 * attribute value and produced only after structural and P-256 acceptance. */
size_t comp_v11_update_storage_manifest_receipt(const comp_v11_update_storage_t *storage,
                                                uint8_t *output,size_t capacity);
bool comp_v11_update_storage_control(comp_v11_update_storage_t *storage,
                                     const uint8_t *packet,size_t packet_bytes);
bool comp_v11_update_storage_data(comp_v11_update_storage_t *storage,
                                  const uint8_t *packet,size_t packet_bytes);
size_t comp_v11_update_storage_transfer_status(const comp_v11_update_storage_t *storage,
                                               uint8_t *output,size_t capacity);
bool comp_v11_update_storage_poll(comp_v11_update_storage_t *storage,
                                  uint8_t *scratch,size_t scratch_bytes);
comp_wba_update_status_t comp_v11_update_storage_status(const comp_v11_update_storage_t *storage);

/* For firmware call only after POST/NOR/BLE main-loop readiness. For resources
 * call only after the newly installed UI partition mounts with the signed
 * version. Absence of panel RESET is not a confirmation prerequisite. */
bool comp_v11_update_storage_request_confirm(comp_v11_update_storage_t *storage,
                                             uint32_t version);

/* Resident-boot facade uses the same NOR/meta callbacks and trust anchor. */
bool comp_v11_update_boot_init(comp_v11_update_storage_t *storage,
                               const comp_v11_update_storage_config_t *config);
comp_wba_boot_action_t comp_v11_update_boot_poll(comp_v11_update_storage_t *storage,
                                                 uint8_t *scratch,size_t scratch_bytes);

#endif
