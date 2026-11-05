#ifndef COMPANION_V11_SYSTEM_STORAGE_H
#define COMPANION_V11_SYSTEM_STORAGE_H
#include "spi_nor_stm32wba.h"
#include "wba_system_journal.h"

typedef struct {
    companion_spi_nor_stm32wba_t *nor;
    comp_wba_update_p256_trust_t trust;
    bool (*idle)(void *);
    /* Existing recording allocator's exact tail reservation. Exclusive owner
     * is this paired updater; remove the legacy updater before binding it.
     * Zero reconciles this updater's claim; no recording eviction is implicit.
     */
    bool (*workspace_reserve)(void *,uint32_t bytes,uint32_t *base);
    bool (*running_pair_verified)(void *,const uint8_t wire[452]);
    /* Actual immutable destinations may be checked before recording's OTA
     * lease recovery completes. This does not grant final runtime confirmation. */
    bool (*current_pair_verified)(void *,const uint8_t wire[452]);
    void *context;
    uint32_t current_firmware,current_resources,current_static_bytes;
    const uint8_t *current_resource_sha256;
} comp_v11_system_storage_config_t;
typedef struct {
    comp_v11_system_storage_config_t config;
    comp_wba_system_receiver_t receiver;
    comp_wba_system_journal_t journal;
    uint32_t claimed_base,claimed_bytes;
    bool ready,first_retry_pending;
} comp_v11_system_storage_t;
/* Actual SPI NOR driver and existing recording workspace callback. No GATT,
 * internal Flash mutation/reset or implicit old-layout formatting here.
 * Caller must serialize foreground access and provide the current trusted
 * layout. Growing-static coordinator/Boot/GATT integration remains separate.
 */
bool comp_v11_system_storage_init(comp_v11_system_storage_t *,const comp_v11_system_storage_config_t *);
#endif
