#ifndef COMPANION_WBA_UPDATE_SERVICE_H
#define COMPANION_WBA_UPDATE_SERVICE_H

#include "denzic_ota_v1.h"
#include "wba_storage_layout.h"

#include "../core/companion_sha256.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Backward-compatible names inside the new WBA updater only. */
#define COMP_WBA_NOR_ROLLBACK_BASE COMP_WBA_NOR_FIRMWARE_BACKUP_BASE
#define COMP_WBA_NOR_ROLLBACK_BYTES COMP_WBA_NOR_FIRMWARE_BACKUP_BYTES

#define COMP_WBA_UPDATE_MANIFEST_SCHEMA 1u
#define COMP_WBA_UPDATE_TARGET_FAMILY_STM32WBA UINT32_C(0x41425743) /* CWBA */
#include "wba_flash_geometry.h"
#define COMP_WBA_UPDATE_FIRMWARE_FORMAT_RELOCATED_BIN 1u
#define COMP_WBA_UPDATE_FIRMWARE_MAX_BYTES COMP_WBA_BOOT_APP_CAPACITY
#define COMP_WBA_UPDATE_UI_FORMAT_CUOT_V1 1u
#define COMP_WBA_UPDATE_UI_FORMAT_PARTITION_IMAGE_V1 2u
#define COMP_WBA_UPDATE_SHA256_BYTES 32u
#define COMP_WBA_UPDATE_AUTH_MAX_BYTES 64u
#define COMP_WBA_UPDATE_CHECKPOINT_MAGIC UINT32_C(0x31505557) /* WUP1 */

typedef enum {
    COMP_WBA_UPDATE_TARGET_FIRMWARE = 1u,
    COMP_WBA_UPDATE_TARGET_UI_ASSETS = 2u,
} comp_wba_update_target_t;

typedef enum {
    COMP_WBA_UPDATE_IDLE = 0u,
    COMP_WBA_UPDATE_AUTHORIZED = 1u,
    COMP_WBA_UPDATE_RECEIVING = 2u,
    COMP_WBA_UPDATE_VERIFYING = 3u,
    COMP_WBA_UPDATE_VERIFIED = 4u,
    COMP_WBA_UPDATE_ACTIVATING = 5u,
    COMP_WBA_UPDATE_COMPLETE = 6u,
    COMP_WBA_UPDATE_ERROR = 7u,
} comp_wba_update_state_t;

typedef enum {
    COMP_WBA_UPDATE_ERROR_NONE = 0u,
    COMP_WBA_UPDATE_ERROR_ARGUMENT = 1u,
    COMP_WBA_UPDATE_ERROR_TARGET = 2u,
    COMP_WBA_UPDATE_ERROR_ROLLBACK = 3u,
    COMP_WBA_UPDATE_ERROR_UNTRUSTED = 4u,
    COMP_WBA_UPDATE_ERROR_BUSY = 5u,
    COMP_WBA_UPDATE_ERROR_STORAGE = 6u,
    COMP_WBA_UPDATE_ERROR_STREAM_HASH = 7u,
    COMP_WBA_UPDATE_ERROR_READBACK = 8u,
    COMP_WBA_UPDATE_ERROR_READBACK_HASH = 9u,
    COMP_WBA_UPDATE_ERROR_ACTIVATION = 10u,
    COMP_WBA_UPDATE_ERROR_INTERRUPTED = 11u,
    COMP_WBA_UPDATE_ERROR_CHECKPOINT = 12u,
} comp_wba_update_error_t;

typedef enum {
    COMP_WBA_UPDATE_STEP_BUSY = 0u,
    COMP_WBA_UPDATE_STEP_DONE = 1u,
    COMP_WBA_UPDATE_STEP_FAILED = 2u,
} comp_wba_update_step_result_t;

typedef struct {
    uint8_t schema_version;
    uint8_t target;
    uint16_t format_version;
    uint32_t target_family;
    uint32_t board_target;
    uint32_t component_version;
    uint32_t minimum_app_version;
    uint32_t maximum_app_version;
    uint32_t size_bytes;
    uint32_t crc32;
    uint8_t sha256[COMP_WBA_UPDATE_SHA256_BYTES];
} comp_wba_update_manifest_t;

typedef struct {
    uint32_t magic;
    uint32_t sequence;
    uint8_t state;
    uint8_t auth_length;
    uint16_t reserved;
    comp_wba_update_manifest_t manifest;
    uint8_t auth[COMP_WBA_UPDATE_AUTH_MAX_BYTES];
    uint32_t crc32;
} comp_wba_update_checkpoint_t;

typedef struct {
    bool (*activity_idle)(void *context);
    bool (*authorize_manifest)(void *context,
                               const comp_wba_update_manifest_t *manifest,
                               const uint8_t *authentication,
                               uint8_t authentication_length);
    bool (*staging_begin)(void *context, uint32_t size_bytes);
    bool (*staging_write)(void *context, uint32_t offset,
                          const uint8_t *data, size_t length);
    bool (*staging_read)(void *context, uint32_t offset,
                         uint8_t *data, size_t length);
    void (*staging_abort)(void *context);
    comp_wba_update_step_result_t (*activate_step)(
        void *context, const comp_wba_update_manifest_t *manifest,
        const uint8_t *authentication, uint8_t authentication_length,
        uint32_t staging_offset, uint32_t size_bytes,
        uint8_t *scratch, size_t scratch_bytes);
    bool (*checkpoint_load)(void *context,
                            comp_wba_update_checkpoint_t *checkpoint);
    bool (*checkpoint_store)(void *context,
                             const comp_wba_update_checkpoint_t *checkpoint);
    bool (*checkpoint_clear)(void *context);
    void *context;
} comp_wba_update_ports_t;

typedef struct {
    comp_wba_update_ports_t ports;
    uint32_t target_family;
    uint32_t board_target;
    uint32_t current_firmware_version;
    uint32_t current_ui_version;
    uint32_t current_app_version;
    uint32_t staging_capacity;
    uint16_t maximum_chunk_bytes;
    uint16_t default_window_chunks;
} comp_wba_update_config_t;

typedef companion_sha256_t comp_wba_update_sha256_t;

typedef struct {
    comp_wba_update_config_t config;
    denzic_ota_v1_context_t transfer;
    comp_wba_update_manifest_t manifest;
    comp_wba_update_sha256_t stream_hash;
    comp_wba_update_sha256_t readback_hash;
    uint8_t authentication[COMP_WBA_UPDATE_AUTH_MAX_BYTES];
    uint8_t authentication_length;
    uint8_t state;
    uint8_t last_error;
    uint8_t status_flags;
    uint8_t reserved;
    uint32_t checkpoint_sequence;
    uint32_t verify_offset;
    uint32_t received_bytes;
    uint32_t rejected_packets;
    uint32_t activation_steps;
    bool stream_hash_ready;
    bool bootable;
    bool installed;
    bool pending_reboot;
} comp_wba_update_service_t;

typedef struct {
    uint8_t state;
    uint8_t error;
    uint8_t target;
    uint8_t transfer_state;
    uint32_t received_bytes;
    uint32_t expected_bytes;
    uint32_t verify_offset;
    uint32_t component_version;
    bool authenticated;
    bool bootable;
    bool installed;
    bool pending_reboot;
} comp_wba_update_status_t;

bool comp_wba_update_init(comp_wba_update_service_t *service,
                          const comp_wba_update_config_t *config);

/* The authentication bytes are product-defined (for example an Ed25519
 * signature over the canonical manifest). A missing trust callback or empty
 * authentication is always rejected. */
bool comp_wba_update_open(comp_wba_update_service_t *service,
                          const comp_wba_update_manifest_t *manifest,
                          const uint8_t *authentication,
                          uint8_t authentication_length);

bool comp_wba_update_control(comp_wba_update_service_t *service,
                             const uint8_t *packet, size_t packet_bytes);
bool comp_wba_update_data(comp_wba_update_service_t *service,
                          const uint8_t *packet, size_t packet_bytes);
size_t comp_wba_update_transfer_status(const comp_wba_update_service_t *service,
                                       uint8_t *output, size_t output_bytes);

/* Foreground/task context only. The caller lends scratch storage, so this
 * service has no large hidden BSS buffer. Each call performs at most one
 * bounded staging read or one target activation step. */
bool comp_wba_update_poll(comp_wba_update_service_t *service,
                          uint8_t *scratch, size_t scratch_bytes);
void comp_wba_update_abort(comp_wba_update_service_t *service);
comp_wba_update_status_t comp_wba_update_status(
    const comp_wba_update_service_t *service);

uint32_t comp_wba_update_checkpoint_crc32(
    const comp_wba_update_checkpoint_t *checkpoint);
bool comp_wba_update_checkpoint_valid(
    const comp_wba_update_checkpoint_t *checkpoint);

/* Shared fixed-memory SHA-256 used by the resident installer to verify both
 * backup and installed application bytes. */
void comp_wba_update_sha256_init(comp_wba_update_sha256_t *hash);
void comp_wba_update_sha256_update(comp_wba_update_sha256_t *hash,
                                   const uint8_t *data, size_t length);
void comp_wba_update_sha256_final(comp_wba_update_sha256_t *hash,
                                  uint8_t digest[COMP_WBA_UPDATE_SHA256_BYTES]);

#ifdef __cplusplus
}
#endif

#endif
