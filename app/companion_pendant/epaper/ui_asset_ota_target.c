#include "ui_asset_ota_target.h"

#include <string.h>

enum {
    OTA_MAGIC = 0u,
    OTA_VERSION = 4u,
    OTA_HEADER_SIZE = 6u,
    OTA_TARGET = 8u,
    OTA_BUNDLE_SIZE = 12u,
    OTA_BASE_PACK_SIZE = 16u,
    OTA_BASE_PAYLOAD_CRC32 = 20u,
    OTA_BASE_INDEX_CRC32 = 24u,
    OTA_EXPECTED_GENERATION = 28u,
    OTA_BLOB_SIZE = 32u,
    OTA_BLOB_CRC32 = 36u,
    OTA_MANIFEST_OFFSET = 40u,
    OTA_MANIFEST_SIZE = 44u,
    OTA_MANIFEST_CRC32 = 48u,
    OTA_RESOURCE_ID = 52u,
    OTA_PLANNED_BLOB_OFFSET = 84u,
    OTA_FLAGS = 88u,
    OTA_HEADER_CRC32 = 92u,
};

enum {
    CEMP_HEADER_BYTES = 80u,
    CEMP_VERSION = 4u,
    CEMP_DECLARED_HEADER_BYTES = 6u,
    CEMP_TOTAL_SIZE = 8u,
    CEMP_PAYLOAD_CRC32 = 56u,
    CEMP_INDEX_CRC32 = 60u,
};

static uint16_t read_le16(const uint8_t *data)
{
    return (uint16_t)data[0] | ((uint16_t)data[1] << 8u);
}

static uint32_t read_le32(const uint8_t *data)
{
    return (uint32_t)data[0] |
           ((uint32_t)data[1] << 8u) |
           ((uint32_t)data[2] << 16u) |
           ((uint32_t)data[3] << 24u);
}

static uint32_t crc32_update(uint32_t crc, const uint8_t *data, size_t length)
{
    for (size_t index = 0u; index < length; ++index) {
        crc ^= data[index];
        for (uint8_t bit = 0u; bit < 8u; ++bit) {
            uint32_t mask = (uint32_t)-(int32_t)(crc & 1u);
            crc = (crc >> 1u) ^ (0xEDB88320u & mask);
        }
    }
    return crc;
}

static uint32_t crc32_bytes(const uint8_t *data, size_t length)
{
    return crc32_update(0xFFFFFFFFu, data, length) ^ 0xFFFFFFFFu;
}

static bool resource_id_valid(const uint8_t *resource_id)
{
    uint8_t combined = 0u;
    for (size_t index = 0u;
         index < COMP_UI_ASSET_GENERATION_ID_BYTES;
         ++index) {
        combined |= resource_id[index];
    }
    return combined != 0u;
}

static bool io_read_store(void *context, uint32_t offset,
                          uint8_t *data, size_t length)
{
    const comp_ui_asset_generation_io_t *io =
        (const comp_ui_asset_generation_io_t *)context;
    return io != NULL &&
           io->read(io->context, offset, data, length);
}

static uint32_t align_sector(uint32_t value)
{
    return (value + COMP_UI_ASSET_GENERATION_SECTOR_BYTES - 1u) &
           ~(COMP_UI_ASSET_GENERATION_SECTOR_BYTES - 1u);
}

static bool base_identity_matches(
    const comp_ui_asset_generation_io_t *io,
    uint32_t pack_size,
    uint32_t payload_crc32,
    uint32_t index_crc32)
{
    uint8_t header[CEMP_HEADER_BYTES];
    return io->read(io->context, 0u, header, sizeof(header)) &&
           memcmp(header, "CEMP", 4u) == 0 &&
           read_le16(&header[CEMP_VERSION]) == 1u &&
           read_le16(&header[CEMP_DECLARED_HEADER_BYTES]) ==
               CEMP_HEADER_BYTES &&
           read_le32(&header[CEMP_TOTAL_SIZE]) == pack_size &&
           read_le32(&header[CEMP_PAYLOAD_CRC32]) == payload_crc32 &&
           read_le32(&header[CEMP_INDEX_CRC32]) == index_crc32;
}

static bool parse_header(comp_ui_asset_ota_target_t *target)
{
    const uint8_t *header = target->header;
    comp_asset_store_t store;
    comp_ui_asset_generation_t active;
    uint32_t bundle_size = read_le32(&header[OTA_BUNDLE_SIZE]);
    uint32_t base_pack_size = read_le32(&header[OTA_BASE_PACK_SIZE]);
    uint32_t blob_size = read_le32(&header[OTA_BLOB_SIZE]);
    uint32_t manifest_offset = read_le32(&header[OTA_MANIFEST_OFFSET]);
    uint32_t manifest_size = read_le32(&header[OTA_MANIFEST_SIZE]);
    bool have_active;

    if (memcmp(&header[OTA_MAGIC], "CUOT", 4u) != 0 ||
        read_le16(&header[OTA_VERSION]) !=
            COMP_UI_ASSET_OTA_FORMAT_VERSION ||
        read_le16(&header[OTA_HEADER_SIZE]) !=
            COMP_UI_ASSET_OTA_HEADER_BYTES ||
        read_le32(&header[OTA_TARGET]) !=
            COMP_UI_ASSET_OTA_TARGET_UI_GENERATION ||
        bundle_size != target->expected_bundle_bytes ||
        blob_size == 0u ||
        bundle_size != COMP_UI_ASSET_OTA_HEADER_BYTES + blob_size ||
        manifest_offset > blob_size ||
        manifest_size < COMP_UI_ASSET_MANIFEST_HEADER_BYTES ||
        manifest_size > blob_size - manifest_offset ||
        read_le32(&header[OTA_FLAGS]) != 0u ||
        crc32_bytes(header, OTA_HEADER_CRC32) !=
            read_le32(&header[OTA_HEADER_CRC32]) ||
        !resource_id_valid(&header[OTA_RESOURCE_ID]) ||
        !base_identity_matches(
            target->io,
            base_pack_size,
            read_le32(&header[OTA_BASE_PAYLOAD_CRC32]),
            read_le32(&header[OTA_BASE_INDEX_CRC32]))) {
        target->receipt.result = COMP_UI_ASSET_INSTALL_BAD_LAYOUT;
        return false;
    }

    if (!comp_asset_store_init_reader(
            &store,
            COMP_ASSET_STORAGE_EXTERNAL_NOR,
            target->io->partition_size,
            io_read_store,
            (void *)target->io)) {
        target->receipt.result = COMP_UI_ASSET_INSTALL_BAD_LAYOUT;
        return false;
    }
    have_active = comp_ui_asset_generation_mount(&active, &store);
    if ((!have_active ||
         memcmp(active.root.resource_id,
                &header[OTA_RESOURCE_ID],
                COMP_UI_ASSET_GENERATION_ID_BYTES) != 0) &&
        read_le32(&header[OTA_PLANNED_BLOB_OFFSET]) !=
            (have_active ? active.root.arena_next_offset
                         : align_sector(base_pack_size))) {
        target->receipt.result = COMP_UI_ASSET_INSTALL_BAD_LAYOUT;
        return false;
    }

    target->receipt = comp_ui_asset_generation_begin(
        &target->transaction,
        target->io,
        base_pack_size,
        read_le32(&header[OTA_EXPECTED_GENERATION]),
        &header[OTA_RESOURCE_ID],
        blob_size,
        read_le32(&header[OTA_BLOB_CRC32]),
        manifest_offset,
        manifest_size,
        read_le32(&header[OTA_MANIFEST_CRC32]));
    if (target->receipt.result ==
        COMP_UI_ASSET_INSTALL_ALREADY_CURRENT) {
        target->discard_current = true;
    } else if (target->receipt.result != COMP_UI_ASSET_INSTALL_OK) {
        return false;
    }
    target->expected_blob_bytes = blob_size;
    target->expected_blob_crc32 = read_le32(&header[OTA_BLOB_CRC32]);
    target->running_blob_crc32 = 0xFFFFFFFFu;
    target->header_ready = true;
    return true;
}

bool comp_ui_asset_ota_target_init(
    comp_ui_asset_ota_target_t *target,
    const comp_ui_asset_generation_io_t *io)
{
    if (target == NULL || io == NULL || io->read == NULL ||
        io->erase_4k == NULL || io->write == NULL ||
        io->partition_size != 0x00200000u) {
        return false;
    }
    *target = (comp_ui_asset_ota_target_t){.io = io};
    return true;
}

bool comp_ui_asset_ota_target_begin(
    comp_ui_asset_ota_target_t *target,
    uint32_t bundle_bytes)
{
    const comp_ui_asset_generation_io_t *io;
    if (target == NULL || target->io == NULL ||
        bundle_bytes <= COMP_UI_ASSET_OTA_HEADER_BYTES ||
        bundle_bytes > COMP_UI_ASSET_GENERATION_ARENA_END +
                           COMP_UI_ASSET_OTA_HEADER_BYTES) {
        return false;
    }
    io = target->io;
    comp_ui_asset_generation_abort(&target->transaction);
    *target = (comp_ui_asset_ota_target_t){
        .io = io,
        .expected_bundle_bytes = bundle_bytes,
        .active = true,
        .receipt = {
            .result = COMP_UI_ASSET_INSTALL_BAD_ARGUMENT,
        },
    };
    return true;
}

bool comp_ui_asset_ota_target_write(
    comp_ui_asset_ota_target_t *target,
    const uint8_t *data,
    size_t length)
{
    if (target == NULL || !target->active || data == NULL ||
        length == 0u ||
        target->received_bundle_bytes > target->expected_bundle_bytes ||
        length > target->expected_bundle_bytes -
                     target->received_bundle_bytes) {
        return false;
    }

    while (length > 0u) {
        if (!target->header_ready) {
            size_t chunk = COMP_UI_ASSET_OTA_HEADER_BYTES -
                           target->header_bytes;
            if (chunk > length) {
                chunk = length;
            }
            memcpy(target->header + target->header_bytes, data, chunk);
            target->header_bytes = (uint16_t)(target->header_bytes + chunk);
            target->received_bundle_bytes += (uint32_t)chunk;
            data += chunk;
            length -= chunk;
            if (target->header_bytes == COMP_UI_ASSET_OTA_HEADER_BYTES &&
                !parse_header(target)) {
                target->active = false;
                return false;
            }
            continue;
        }

        if (length > target->expected_blob_bytes -
                         target->received_blob_bytes) {
            target->active = false;
            return false;
        }
        if (!target->discard_current &&
            !comp_ui_asset_generation_write(
                &target->transaction, data, length)) {
            target->receipt = target->transaction.receipt;
            target->active = false;
            return false;
        }
        target->running_blob_crc32 = crc32_update(
            target->running_blob_crc32, data, length);
        target->received_blob_bytes += (uint32_t)length;
        target->received_bundle_bytes += (uint32_t)length;
        length = 0u;
    }
    return true;
}

bool comp_ui_asset_ota_target_finish(
    comp_ui_asset_ota_target_t *target)
{
    if (target == NULL || !target->active || !target->header_ready ||
        target->received_bundle_bytes != target->expected_bundle_bytes ||
        target->received_blob_bytes != target->expected_blob_bytes ||
        (target->running_blob_crc32 ^ 0xFFFFFFFFu) !=
            target->expected_blob_crc32) {
        if (target != NULL) {
            comp_ui_asset_generation_abort(&target->transaction);
            target->receipt.result = COMP_UI_ASSET_INSTALL_VERIFY_FAILED;
            target->active = false;
        }
        return false;
    }
    if (!target->discard_current) {
        target->receipt =
            comp_ui_asset_generation_finish(&target->transaction);
    }
    target->active = false;
    return target->receipt.result == COMP_UI_ASSET_INSTALL_OK ||
           target->receipt.result ==
               COMP_UI_ASSET_INSTALL_ALREADY_CURRENT;
}

void comp_ui_asset_ota_target_abort(
    comp_ui_asset_ota_target_t *target)
{
    if (target == NULL) {
        return;
    }
    comp_ui_asset_generation_abort(&target->transaction);
    target->active = false;
}

const comp_ui_asset_install_receipt_t *
comp_ui_asset_ota_target_receipt(
    const comp_ui_asset_ota_target_t *target)
{
    return target == NULL ? NULL : &target->receipt;
}
