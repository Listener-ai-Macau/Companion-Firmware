#include "expression_rig_asset_pack.h"

#include <string.h>

#define PACK_MAGIC_0 'C'
#define PACK_MAGIC_1 'R'
#define PACK_MAGIC_2 'I'
#define PACK_MAGIC_3 'G'

enum {
    HEADER_MAGIC = 0u,
    HEADER_VERSION = 4u,
    HEADER_SIZE = 6u,
    HEADER_TOTAL_SIZE = 8u,
    HEADER_REVISION = 12u,
    HEADER_WIDTH = 16u,
    HEADER_HEIGHT = 18u,
    HEADER_STRIDE = 20u,
    HEADER_PIXEL_FORMAT = 22u,
    HEADER_SAFE_INSET = 23u,
    HEADER_COMPONENT_COUNT = 24u,
    HEADER_INDEX_OFFSET = 28u,
    HEADER_DATA_OFFSET = 32u,
    HEADER_PAYLOAD_CRC32 = 36u,
    HEADER_INDEX_CRC32 = 40u,
    HEADER_SOURCE_SHA256 = 44u,
    INDEX_COMPONENT_ID = 0u,
    INDEX_WIDTH = 2u,
    INDEX_HEIGHT = 4u,
    INDEX_STRIDE = 6u,
    INDEX_DATA_OFFSET = 8u,
    INDEX_DATA_SIZE = 12u,
};

static uint16_t read_le16(const uint8_t *data)
{
    return (uint16_t)data[0] | ((uint16_t)data[1] << 8);
}

static uint32_t read_le32(const uint8_t *data)
{
    return (uint32_t)data[0] |
           ((uint32_t)data[1] << 8) |
           ((uint32_t)data[2] << 16) |
           ((uint32_t)data[3] << 24);
}

static bool range_is_valid(uint32_t size_bytes, uint32_t offset, uint32_t length)
{
    return offset <= size_bytes && length <= size_bytes - offset;
}

static uint32_t crc32_update(uint32_t crc, const uint8_t *data, size_t length)
{
    size_t index;

    for (index = 0u; index < length; ++index) {
        uint8_t bit;

        crc ^= data[index];
        for (bit = 0u; bit < 8u; ++bit) {
            uint32_t mask = (uint32_t)-(int32_t)(crc & 1u);

            crc = (crc >> 1) ^ (0xEDB88320u & mask);
        }
    }
    return crc;
}

static bool canvas_is_valid(const comp_expression_rig_canvas_t *canvas)
{
    return canvas != NULL && canvas->width > 0u && canvas->height > 0u &&
           canvas->stride_bytes >= (uint16_t)((canvas->width + 7u) / 8u);
}

static const comp_expression_rig_asset_index_entry_t *find_component(
    const comp_expression_rig_asset_pack_t *pack,
    uint16_t component_id)
{
    uint16_t index;

    if (pack == NULL || pack->store == NULL) {
        return NULL;
    }
    for (index = 0u; index < pack->component_count; ++index) {
        if (pack->components[index].component_id == component_id) {
            return &pack->components[index];
        }
    }
    return NULL;
}

const char *comp_expression_rig_asset_mount_result_name(
    comp_expression_rig_asset_mount_result_t result)
{
    switch (result) {
    case COMP_EXPRESSION_RIG_ASSET_MOUNT_OK: return "ok";
    case COMP_EXPRESSION_RIG_ASSET_MOUNT_BAD_ARGUMENT: return "bad_argument";
    case COMP_EXPRESSION_RIG_ASSET_MOUNT_STORAGE_NOT_EXTERNAL: return "storage_not_external";
    case COMP_EXPRESSION_RIG_ASSET_MOUNT_IO_ERROR: return "io_error";
    case COMP_EXPRESSION_RIG_ASSET_MOUNT_BAD_MAGIC: return "bad_magic";
    case COMP_EXPRESSION_RIG_ASSET_MOUNT_UNSUPPORTED_VERSION: return "unsupported_version";
    case COMP_EXPRESSION_RIG_ASSET_MOUNT_BAD_LAYOUT: return "bad_layout";
    case COMP_EXPRESSION_RIG_ASSET_MOUNT_PROFILE_MISMATCH: return "profile_mismatch";
    case COMP_EXPRESSION_RIG_ASSET_MOUNT_INDEX_CRC_MISMATCH: return "index_crc_mismatch";
    case COMP_EXPRESSION_RIG_ASSET_MOUNT_PAYLOAD_CRC_MISMATCH: return "payload_crc_mismatch";
    default: return "unknown";
    }
}

comp_expression_rig_asset_mount_result_t comp_expression_rig_asset_pack_mount(
    comp_expression_rig_asset_pack_t *pack,
    const comp_asset_store_t *store,
    const comp_expression_rig_canvas_t *target)
{
    uint8_t header[COMP_EXPRESSION_RIG_ASSET_PACK_HEADER_BYTES];
    uint8_t entry[COMP_EXPRESSION_RIG_ASSET_PACK_INDEX_ENTRY_BYTES];
    uint16_t component_count;
    uint16_t index;
    uint16_t version;
    uint16_t header_size;
    uint32_t total_size;
    uint32_t index_offset;
    uint32_t data_offset;
    uint32_t expected_data_offset;
    uint32_t index_crc = 0xFFFFFFFFu;
    uint32_t previous_data_end = 0u;

    if (pack == NULL || store == NULL || !canvas_is_valid(target)) {
        return COMP_EXPRESSION_RIG_ASSET_MOUNT_BAD_ARGUMENT;
    }
    memset(pack, 0, sizeof(*pack));
    if (store->storage_class != COMP_ASSET_STORAGE_EXTERNAL_NOR) {
        return COMP_EXPRESSION_RIG_ASSET_MOUNT_STORAGE_NOT_EXTERNAL;
    }
    if (!comp_asset_store_read(store, 0u, header, sizeof(header))) {
        return COMP_EXPRESSION_RIG_ASSET_MOUNT_IO_ERROR;
    }
    if (header[HEADER_MAGIC] != PACK_MAGIC_0 || header[HEADER_MAGIC + 1u] != PACK_MAGIC_1 ||
        header[HEADER_MAGIC + 2u] != PACK_MAGIC_2 || header[HEADER_MAGIC + 3u] != PACK_MAGIC_3) {
        return COMP_EXPRESSION_RIG_ASSET_MOUNT_BAD_MAGIC;
    }
    version = read_le16(&header[HEADER_VERSION]);
    if (version != COMP_EXPRESSION_RIG_ASSET_PACK_FORMAT_VERSION) {
        return COMP_EXPRESSION_RIG_ASSET_MOUNT_UNSUPPORTED_VERSION;
    }
    header_size = read_le16(&header[HEADER_SIZE]);
    total_size = read_le32(&header[HEADER_TOTAL_SIZE]);
    component_count = read_le16(&header[HEADER_COMPONENT_COUNT]);
    index_offset = read_le32(&header[HEADER_INDEX_OFFSET]);
    data_offset = read_le32(&header[HEADER_DATA_OFFSET]);
    if (header_size != COMP_EXPRESSION_RIG_ASSET_PACK_HEADER_BYTES || total_size != store->size_bytes ||
        component_count == 0u || component_count > COMP_EXPRESSION_RIG_ASSET_PACK_MAX_COMPONENTS ||
        index_offset != COMP_EXPRESSION_RIG_ASSET_PACK_HEADER_BYTES ||
        component_count > (UINT32_MAX - index_offset) / COMP_EXPRESSION_RIG_ASSET_PACK_INDEX_ENTRY_BYTES) {
        return COMP_EXPRESSION_RIG_ASSET_MOUNT_BAD_LAYOUT;
    }
    expected_data_offset = index_offset +
        (uint32_t)component_count * COMP_EXPRESSION_RIG_ASSET_PACK_INDEX_ENTRY_BYTES;
    if (data_offset != expected_data_offset || !range_is_valid(total_size, index_offset,
        (uint32_t)component_count * COMP_EXPRESSION_RIG_ASSET_PACK_INDEX_ENTRY_BYTES) ||
        data_offset > total_size || read_le16(&header[HEADER_WIDTH]) != target->width ||
        read_le16(&header[HEADER_HEIGHT]) != target->height ||
        read_le16(&header[HEADER_STRIDE]) != target->stride_bytes ||
        header[HEADER_PIXEL_FORMAT] != 1u || header[HEADER_SAFE_INSET] < 4u) {
        return COMP_EXPRESSION_RIG_ASSET_MOUNT_PROFILE_MISMATCH;
    }

    for (index = 0u; index < component_count; ++index) {
        comp_expression_rig_asset_index_entry_t *destination = &pack->components[index];
        uint32_t component_offset;
        uint32_t component_size;
        uint16_t component_width;
        uint16_t component_height;
        uint16_t component_stride;
        uint16_t earlier;
        uint32_t entry_offset = index_offset +
            (uint32_t)index * COMP_EXPRESSION_RIG_ASSET_PACK_INDEX_ENTRY_BYTES;

        if (!comp_asset_store_read(store, entry_offset, entry, sizeof(entry))) {
            return COMP_EXPRESSION_RIG_ASSET_MOUNT_IO_ERROR;
        }
        index_crc = crc32_update(index_crc, entry, sizeof(entry));
        component_width = read_le16(&entry[INDEX_WIDTH]);
        component_height = read_le16(&entry[INDEX_HEIGHT]);
        component_stride = read_le16(&entry[INDEX_STRIDE]);
        component_offset = read_le32(&entry[INDEX_DATA_OFFSET]);
        component_size = read_le32(&entry[INDEX_DATA_SIZE]);
        if (read_le16(&entry[INDEX_COMPONENT_ID]) == COMP_EXPRESSION_RIG_INVALID_COMPONENT_ID ||
            component_width == 0u || component_height == 0u ||
            component_stride < (uint16_t)((component_width + 7u) / 8u) ||
            component_size != (uint32_t)component_stride * component_height ||
            component_offset < data_offset || !range_is_valid(total_size, component_offset, component_size) ||
            (index > 0u && component_offset < previous_data_end)) {
            return COMP_EXPRESSION_RIG_ASSET_MOUNT_BAD_LAYOUT;
        }
        for (earlier = 0u; earlier < index; ++earlier) {
            if (pack->components[earlier].component_id == read_le16(&entry[INDEX_COMPONENT_ID])) {
                return COMP_EXPRESSION_RIG_ASSET_MOUNT_BAD_LAYOUT;
            }
        }
        *destination = (comp_expression_rig_asset_index_entry_t){
            .component_id = read_le16(&entry[INDEX_COMPONENT_ID]),
            .mask = {
                .width = component_width,
                .height = component_height,
                .stride_bytes = component_stride,
                .data_size = component_size,
            },
            .data_offset = component_offset,
            .data_size = component_size,
        };
        previous_data_end = component_offset + component_size;
    }
    if ((index_crc ^ 0xFFFFFFFFu) != read_le32(&header[HEADER_INDEX_CRC32]) ||
        previous_data_end != total_size) {
        return COMP_EXPRESSION_RIG_ASSET_MOUNT_INDEX_CRC_MISMATCH;
    }
    *pack = (comp_expression_rig_asset_pack_t){
        .store = store,
        .canvas = *target,
        .revision = read_le32(&header[HEADER_REVISION]),
        .safe_inset_px = header[HEADER_SAFE_INSET],
        .component_count = component_count,
        .data_offset = data_offset,
        .payload_crc32 = read_le32(&header[HEADER_PAYLOAD_CRC32]),
    };
    memcpy(pack->source_sha256, &header[HEADER_SOURCE_SHA256], sizeof(pack->source_sha256));
    for (index = 0u; index < component_count; ++index) {
        if (!comp_asset_store_read(store,
                                   index_offset + (uint32_t)index * COMP_EXPRESSION_RIG_ASSET_PACK_INDEX_ENTRY_BYTES,
                                   entry,
                                   sizeof(entry))) {
            memset(pack, 0, sizeof(*pack));
            return COMP_EXPRESSION_RIG_ASSET_MOUNT_IO_ERROR;
        }
        pack->components[index] = (comp_expression_rig_asset_index_entry_t){
            .component_id = read_le16(&entry[INDEX_COMPONENT_ID]),
            .mask = {
                .width = read_le16(&entry[INDEX_WIDTH]),
                .height = read_le16(&entry[INDEX_HEIGHT]),
                .stride_bytes = read_le16(&entry[INDEX_STRIDE]),
                .data_size = read_le32(&entry[INDEX_DATA_SIZE]),
            },
            .data_offset = read_le32(&entry[INDEX_DATA_OFFSET]),
            .data_size = read_le32(&entry[INDEX_DATA_SIZE]),
        };
    }
    return COMP_EXPRESSION_RIG_ASSET_MOUNT_OK;
}

bool comp_expression_rig_asset_pack_verify_payload(
    const comp_expression_rig_asset_pack_t *pack,
    uint8_t *scratch,
    size_t scratch_size)
{
    uint32_t offset;
    uint32_t crc = 0xFFFFFFFFu;

    if (pack == NULL || pack->store == NULL || pack->data_offset >= pack->store->size_bytes ||
        scratch == NULL || scratch_size == 0u) {
        return false;
    }
    offset = pack->data_offset;
    while (offset < pack->store->size_bytes) {
        size_t length = pack->store->size_bytes - offset;

        if (length > scratch_size) {
            length = scratch_size;
        }
        if (!comp_asset_store_read(pack->store, offset, scratch, length)) {
            return false;
        }
        crc = crc32_update(crc, scratch, length);
        offset += (uint32_t)length;
    }
    return (crc ^ 0xFFFFFFFFu) == pack->payload_crc32;
}

bool comp_expression_rig_asset_pack_read_component(
    void *context,
    uint16_t component_id,
    uint8_t *destination,
    size_t destination_size,
    comp_expression_rig_component_mask_info_t *out_info)
{
    const comp_expression_rig_asset_pack_t *pack =
        (const comp_expression_rig_asset_pack_t *)context;
    const comp_expression_rig_asset_index_entry_t *entry = find_component(pack, component_id);

    if (entry == NULL || destination == NULL || out_info == NULL || destination_size < entry->data_size) {
        return false;
    }
    if (!comp_asset_store_read(pack->store, entry->data_offset, destination, entry->data_size)) {
        return false;
    }
    *out_info = entry->mask;
    return true;
}
