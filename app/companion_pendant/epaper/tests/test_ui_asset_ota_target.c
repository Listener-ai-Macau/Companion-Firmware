#include "asset_store.h"
#include "ui_asset_generation.h"
#include "ui_asset_ota_target.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum {
    FLASH_BYTES = 0x00200000u,
    BASE_PACK_BYTES = 0x00001000u,
    MANIFEST_BYTES =
        COMP_UI_ASSET_MANIFEST_HEADER_BYTES +
        COMP_UI_ASSET_MANIFEST_ENTRY_BYTES,
};

#define BASE_PAYLOAD_CRC32 UINT32_C(0x12345678)
#define BASE_INDEX_CRC32 UINT32_C(0x89ABCDEF)

typedef struct {
    uint8_t *bytes;
    uint32_t erase_count;
    uint32_t write_bytes;
} fake_flash_t;

static void require_true(bool value, const char *message)
{
    if (!value) {
        fprintf(stderr, "FAIL: %s\n", message);
        exit(1);
    }
}

static uint32_t crc32_bytes(const uint8_t *data, size_t length)
{
    uint32_t crc = 0xFFFFFFFFu;
    for (size_t index = 0u; index < length; ++index) {
        crc ^= data[index];
        for (uint8_t bit = 0u; bit < 8u; ++bit) {
            uint32_t mask = (uint32_t)-(int32_t)(crc & 1u);
            crc = (crc >> 1u) ^ (0xEDB88320u & mask);
        }
    }
    return crc ^ 0xFFFFFFFFu;
}

static void write_le16(uint8_t *data, uint16_t value)
{
    data[0] = (uint8_t)value;
    data[1] = (uint8_t)(value >> 8u);
}

static void write_le32(uint8_t *data, uint32_t value)
{
    data[0] = (uint8_t)value;
    data[1] = (uint8_t)(value >> 8u);
    data[2] = (uint8_t)(value >> 16u);
    data[3] = (uint8_t)(value >> 24u);
}

static bool fake_read(void *context, uint32_t offset,
                      uint8_t *data, size_t length)
{
    fake_flash_t *flash = (fake_flash_t *)context;
    if (offset > FLASH_BYTES || length > FLASH_BYTES - offset) {
        return false;
    }
    memcpy(data, flash->bytes + offset, length);
    return true;
}

static bool fake_erase(void *context, uint32_t offset)
{
    fake_flash_t *flash = (fake_flash_t *)context;
    if ((offset % COMP_UI_ASSET_GENERATION_SECTOR_BYTES) != 0u ||
        offset > FLASH_BYTES - COMP_UI_ASSET_GENERATION_SECTOR_BYTES) {
        return false;
    }
    memset(flash->bytes + offset, 0xFF,
           COMP_UI_ASSET_GENERATION_SECTOR_BYTES);
    flash->erase_count++;
    return true;
}

static bool fake_write(void *context, uint32_t offset,
                       const uint8_t *data, size_t length)
{
    fake_flash_t *flash = (fake_flash_t *)context;
    if (offset > FLASH_BYTES || length > FLASH_BYTES - offset) {
        return false;
    }
    for (size_t index = 0u; index < length; ++index) {
        flash->bytes[offset + index] &= data[index];
    }
    flash->write_bytes += (uint32_t)length;
    return true;
}

static void build_manifest(uint8_t blob[MANIFEST_BYTES])
{
    memset(blob, 0, MANIFEST_BYTES);
    memcpy(blob, "CUIM", 4u);
    write_le16(blob + 4u, COMP_UI_ASSET_GENERATION_FORMAT_VERSION);
    write_le16(blob + 6u, COMP_UI_ASSET_MANIFEST_HEADER_BYTES);
    write_le16(blob + 8u, 1u);
    write_le16(blob + 10u, COMP_UI_ASSET_MANIFEST_ENTRY_BYTES);
    write_le32(blob + 12u, MANIFEST_BYTES);
    uint8_t *entry = blob + COMP_UI_ASSET_MANIFEST_HEADER_BYTES;
    write_le32(entry + 0u, comp_ui_asset_state_hash("expression_calm"));
    write_le16(entry + 4u, 0u);
    write_le16(entry + 6u, 0u);
    write_le32(entry + 8u, 0x01020304u);
    write_le16(entry + 18u, 500u);
}

static uint32_t build_bundle(
    uint8_t *bundle,
    const uint8_t resource_id[COMP_UI_ASSET_GENERATION_ID_BYTES],
    uint32_t expected_generation,
    uint32_t base_payload_crc32,
    uint32_t advertised_blob_crc32)
{
    uint8_t blob[MANIFEST_BYTES];
    build_manifest(blob);
    memset(bundle, 0, COMP_UI_ASSET_OTA_HEADER_BYTES + sizeof(blob));
    memcpy(bundle, "CUOT", 4u);
    write_le16(bundle + 4u, COMP_UI_ASSET_OTA_FORMAT_VERSION);
    write_le16(bundle + 6u, COMP_UI_ASSET_OTA_HEADER_BYTES);
    write_le32(bundle + 8u, COMP_UI_ASSET_OTA_TARGET_UI_GENERATION);
    write_le32(bundle + 12u,
               COMP_UI_ASSET_OTA_HEADER_BYTES + sizeof(blob));
    write_le32(bundle + 16u, BASE_PACK_BYTES);
    write_le32(bundle + 20u, base_payload_crc32);
    write_le32(bundle + 24u, BASE_INDEX_CRC32);
    write_le32(bundle + 28u, expected_generation);
    write_le32(bundle + 32u, sizeof(blob));
    write_le32(bundle + 36u,
               advertised_blob_crc32 == 0u
                   ? crc32_bytes(blob, sizeof(blob))
                   : advertised_blob_crc32);
    write_le32(bundle + 40u, 0u);
    write_le32(bundle + 44u, sizeof(blob));
    write_le32(bundle + 48u, crc32_bytes(blob, sizeof(blob)));
    memcpy(bundle + 52u, resource_id,
           COMP_UI_ASSET_GENERATION_ID_BYTES);
    write_le32(bundle + 84u,
               expected_generation == 0u
                   ? BASE_PACK_BYTES
                   : BASE_PACK_BYTES +
                         COMP_UI_ASSET_GENERATION_SECTOR_BYTES);
    write_le32(bundle + 92u, crc32_bytes(bundle, 92u));
    memcpy(bundle + COMP_UI_ASSET_OTA_HEADER_BYTES, blob, sizeof(blob));
    return COMP_UI_ASSET_OTA_HEADER_BYTES + sizeof(blob);
}

static bool send_fragmented(
    comp_ui_asset_ota_target_t *target,
    const uint8_t *bundle,
    uint32_t bundle_size)
{
    uint32_t consumed = 0u;
    while (consumed < bundle_size) {
        uint32_t chunk = bundle_size - consumed;
        if (chunk > 17u) {
            chunk = 17u;
        }
        if (!comp_ui_asset_ota_target_write(
                target, bundle + consumed, chunk)) {
            return false;
        }
        consumed += chunk;
    }
    return true;
}

static uint32_t mounted_generation(fake_flash_t *flash)
{
    comp_asset_store_t store;
    comp_ui_asset_generation_t mounted;
    require_true(comp_asset_store_init_reader(
                     &store, COMP_ASSET_STORAGE_EXTERNAL_NOR,
                     FLASH_BYTES, fake_read, flash),
                 "initialize store");
    if (!comp_ui_asset_generation_mount(&mounted, &store)) {
        return 0u;
    }
    return mounted.root.generation;
}

int main(void)
{
    fake_flash_t flash = {0};
    comp_ui_asset_generation_io_t io;
    comp_ui_asset_ota_target_t target;
    uint8_t bundle[COMP_UI_ASSET_OTA_HEADER_BYTES + MANIFEST_BYTES];
    uint8_t id1[COMP_UI_ASSET_GENERATION_ID_BYTES] = {1u};
    uint8_t id2[COMP_UI_ASSET_GENERATION_ID_BYTES] = {2u};

    flash.bytes = malloc(FLASH_BYTES);
    require_true(flash.bytes != NULL, "allocate fake Flash");
    memset(flash.bytes, 0xFF, FLASH_BYTES);
    memcpy(flash.bytes, "CEMP", 4u);
    write_le16(flash.bytes + 4u, 1u);
    write_le16(flash.bytes + 6u, 80u);
    write_le32(flash.bytes + 8u, BASE_PACK_BYTES);
    write_le32(flash.bytes + 56u, BASE_PAYLOAD_CRC32);
    write_le32(flash.bytes + 60u, BASE_INDEX_CRC32);
    io = (comp_ui_asset_generation_io_t){
        .read = fake_read,
        .erase_4k = fake_erase,
        .write = fake_write,
        .context = &flash,
        .partition_size = FLASH_BYTES,
    };

    require_true(comp_ui_asset_ota_target_init(&target, &io),
                 "initialize exact 2 MiB target");
    uint32_t bundle_size = build_bundle(
        bundle, id1, 0u, BASE_PAYLOAD_CRC32, 0u);
    require_true(comp_ui_asset_ota_target_begin(&target, bundle_size) &&
                     send_fragmented(&target, bundle, bundle_size) &&
                     comp_ui_asset_ota_target_finish(&target) &&
                     mounted_generation(&flash) == 1u,
                 "fragmented resource OTA commits generation one");

    uint32_t writes_before_noop = flash.write_bytes;
    uint32_t erases_before_noop = flash.erase_count;
    bundle_size = build_bundle(
        bundle, id1, 1u, BASE_PAYLOAD_CRC32, 0u);
    require_true(comp_ui_asset_ota_target_begin(&target, bundle_size) &&
                     send_fragmented(&target, bundle, bundle_size) &&
                     comp_ui_asset_ota_target_finish(&target) &&
                     target.receipt.result ==
                         COMP_UI_ASSET_INSTALL_ALREADY_CURRENT &&
                     flash.write_bytes == writes_before_noop &&
                     flash.erase_count == erases_before_noop,
                 "same resource OTA performs zero Flash writes");

    bundle_size = build_bundle(
        bundle, id2, 1u, BASE_PAYLOAD_CRC32, 0x01020304u);
    require_true(comp_ui_asset_ota_target_begin(&target, bundle_size) &&
                     send_fragmented(&target, bundle, bundle_size) &&
                     !comp_ui_asset_ota_target_finish(&target) &&
                     mounted_generation(&flash) == 1u,
                 "blob CRC failure preserves generation one");

    bundle_size = build_bundle(
        bundle, id2, 1u, BASE_PAYLOAD_CRC32 ^ 1u, 0u);
    uint32_t writes_before_base_mismatch = flash.write_bytes;
    require_true(comp_ui_asset_ota_target_begin(&target, bundle_size) &&
                     !send_fragmented(&target, bundle, bundle_size) &&
                     flash.write_bytes == writes_before_base_mismatch &&
                     mounted_generation(&flash) == 1u,
                 "wrong CEMP base identity is rejected before writing");

    bundle_size = build_bundle(
        bundle, id2, 1u, BASE_PAYLOAD_CRC32, 0u);
    write_le32(bundle + 84u,
               BASE_PACK_BYTES +
                   2u * COMP_UI_ASSET_GENERATION_SECTOR_BYTES);
    write_le32(bundle + 92u, crc32_bytes(bundle, 92u));
    uint32_t erases_before_offset_mismatch = flash.erase_count;
    require_true(comp_ui_asset_ota_target_begin(&target, bundle_size) &&
                     !send_fragmented(&target, bundle, bundle_size) &&
                     flash.erase_count == erases_before_offset_mismatch &&
                     mounted_generation(&flash) == 1u,
                 "wrong planned blob offset is rejected before erase");

    bundle_size = build_bundle(
        bundle, id2, 1u, BASE_PAYLOAD_CRC32, 0u);
    require_true(comp_ui_asset_ota_target_begin(&target, bundle_size) &&
                     comp_ui_asset_ota_target_write(
                         &target, bundle,
                         COMP_UI_ASSET_OTA_HEADER_BYTES + 7u),
                 "interrupted resource OTA starts");
    comp_ui_asset_ota_target_abort(&target);
    require_true(mounted_generation(&flash) == 1u,
                 "abort preserves generation one");

    comp_ui_asset_generation_io_t oversized = io;
    oversized.partition_size++;
    require_true(!comp_ui_asset_ota_target_init(&target, &oversized),
                 "target rejects a partition wider than 2 MiB");

    printf("PASS_UI_ASSET_OTA_TARGET generation=1 "
           "noop_write_bytes=0 base_mismatch_write_bytes=0 "
           "offset_mismatch_erase_count=0 crc_preserved=1 "
           "abort_preserved=1 partition_bytes=%u\n",
           FLASH_BYTES);
    free(flash.bytes);
    return 0;
}
