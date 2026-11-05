#ifndef COMPANION_EPAPER_UI_ASSET_OTA_TARGET_H
#define COMPANION_EPAPER_UI_ASSET_OTA_TARGET_H

#include "ui_asset_generation.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_UI_ASSET_OTA_FORMAT_VERSION 1u
#define COMP_UI_ASSET_OTA_HEADER_BYTES 96u
#define COMP_UI_ASSET_OTA_TARGET_UI_GENERATION 1u

typedef struct {
    const comp_ui_asset_generation_io_t *io;
    comp_ui_asset_generation_transaction_t transaction;
    comp_ui_asset_install_receipt_t receipt;
    uint8_t header[COMP_UI_ASSET_OTA_HEADER_BYTES];
    uint32_t expected_bundle_bytes;
    uint32_t received_bundle_bytes;
    uint32_t expected_blob_bytes;
    uint32_t received_blob_bytes;
    uint32_t expected_blob_crc32;
    uint32_t running_blob_crc32;
    uint16_t header_bytes;
    bool active;
    bool header_ready;
    bool discard_current;
} comp_ui_asset_ota_target_t;

bool comp_ui_asset_ota_target_init(
    comp_ui_asset_ota_target_t *target,
    const comp_ui_asset_generation_io_t *io);

bool comp_ui_asset_ota_target_begin(
    comp_ui_asset_ota_target_t *target,
    uint32_t bundle_bytes);

bool comp_ui_asset_ota_target_write(
    comp_ui_asset_ota_target_t *target,
    const uint8_t *data,
    size_t length);

bool comp_ui_asset_ota_target_finish(
    comp_ui_asset_ota_target_t *target);

void comp_ui_asset_ota_target_abort(
    comp_ui_asset_ota_target_t *target);

const comp_ui_asset_install_receipt_t *
comp_ui_asset_ota_target_receipt(
    const comp_ui_asset_ota_target_t *target);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_UI_ASSET_OTA_TARGET_H */
