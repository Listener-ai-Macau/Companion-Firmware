#include "companion_recording_resource_pack.h"

#include <string.h>

enum {
    HEADER_MAGIC = 0u,
    HEADER_VERSION = 4u,
    HEADER_BYTES = 6u,
    HEADER_TOTAL_BYTES = 8u,
    HEADER_ENTRY_COUNT = 12u,
    HEADER_ENTRIES_OFFSET = 16u,
    HEADER_ENTRIES_BYTES = 20u,
    HEADER_PAYLOAD_OFFSET = 24u,
    HEADER_PAYLOAD_BYTES = 28u,
    HEADER_PAYLOAD_CRC32 = 32u,
    HEADER_ENTRIES_CRC32 = 36u,
    HEADER_CRC32 = 40u,
    HEADER_CRC_INPUT_BYTES = 40u,
};

enum {
    ENTRY_ID = 0u,
    ENTRY_DATA_OFFSET = 4u,
    ENTRY_DATA_BYTES = 8u,
    ENTRY_DATA_CRC32 = 12u,
    ENTRY_AUX0 = 16u,
    ENTRY_AUX1 = 20u,
    ENTRY_FLAGS = 24u,
};

static uint16_t read_le16(const uint8_t *data)
{
    return (uint16_t)data[0] | (uint16_t)((uint16_t)data[1] << 8u);
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
            crc = (crc >> 1u) ^
                  (0xEDB88320u & (uint32_t)-(int32_t)(crc & 1u));
        }
    }
    return crc;
}

static uint32_t crc32_bytes(const uint8_t *data, size_t length)
{
    return crc32_update(0xFFFFFFFFu, data, length) ^ 0xFFFFFFFFu;
}

static bool range_valid(uint32_t size, uint32_t offset, uint32_t length)
{
    return offset <= size && length <= size - offset;
}

static bool expected_entry(const comp_recording_resource_entry_t *entry)
{
    if (entry->id == COMP_RECORDING_RESOURCE_G7_SPEECH_PCM) {
        return entry->data_bytes == COMP_RECORDING_RESOURCE_G7_BYTES &&
               entry->aux0 == COMP_RECORDING_RESOURCE_G7_FRAME_BYTES &&
               entry->aux1 == COMP_RECORDING_RESOURCE_G7_FRAME_COUNT &&
               entry->flags == 0u;
    }
    if (entry->id == COMP_RECORDING_RESOURCE_OPUS16_FIXTURE) {
        return entry->data_bytes == COMP_RECORDING_RESOURCE_OPUS16_BYTES &&
               entry->aux0 == COMP_RECORDING_RESOURCE_OPUS16_DURATION_MS &&
               entry->aux1 == 0u && entry->flags == 0u;
    }
    return false;
}

static int entry_index(const comp_recording_resource_pack_t *pack,
                       comp_recording_resource_id_t id)
{
    for (uint32_t index = 0u;
         index < COMP_RECORDING_RESOURCE_PACK_ENTRY_COUNT;
         ++index) {
        if (pack->entries[index].id == id) {
            return (int)index;
        }
    }
    return -1;
}

comp_recording_resource_mount_result_t comp_recording_resource_pack_mount(
    comp_recording_resource_pack_t *pack,
    const comp_asset_store_t *store)
{
    uint8_t header[COMP_RECORDING_RESOURCE_PACK_HEADER_BYTES];
    uint8_t entries[COMP_RECORDING_RESOURCE_PACK_ENTRY_BYTES *
                    COMP_RECORDING_RESOURCE_PACK_ENTRY_COUNT];

    if (pack == NULL || store == NULL) {
        return COMP_RECORDING_RESOURCE_MOUNT_BAD_ARGUMENT;
    }
    memset(pack, 0, sizeof(*pack));
    if (!comp_asset_store_read(store, 0u, header, sizeof(header))) {
        return COMP_RECORDING_RESOURCE_MOUNT_IO_ERROR;
    }

    uint32_t total_bytes = read_le32(&header[HEADER_TOTAL_BYTES]);
    uint32_t entries_offset = read_le32(&header[HEADER_ENTRIES_OFFSET]);
    uint32_t entries_bytes = read_le32(&header[HEADER_ENTRIES_BYTES]);
    uint32_t payload_offset = read_le32(&header[HEADER_PAYLOAD_OFFSET]);
    uint32_t payload_bytes = read_le32(&header[HEADER_PAYLOAD_BYTES]);
    if (read_le32(&header[HEADER_MAGIC]) != COMP_RECORDING_RESOURCE_PACK_MAGIC ||
        read_le16(&header[HEADER_VERSION]) != COMP_RECORDING_RESOURCE_PACK_VERSION ||
        read_le16(&header[HEADER_BYTES]) !=
            COMP_RECORDING_RESOURCE_PACK_HEADER_BYTES ||
        read_le32(&header[HEADER_ENTRY_COUNT]) !=
            COMP_RECORDING_RESOURCE_PACK_ENTRY_COUNT ||
        entries_bytes != sizeof(entries) ||
        total_bytes > store->size_bytes ||
        !range_valid(total_bytes, entries_offset, entries_bytes) ||
        !range_valid(total_bytes, payload_offset, payload_bytes) ||
        entries_offset < sizeof(header) ||
        payload_offset < entries_offset + entries_bytes ||
        payload_offset + payload_bytes != total_bytes) {
        return COMP_RECORDING_RESOURCE_MOUNT_BAD_HEADER;
    }
    if (crc32_bytes(header, HEADER_CRC_INPUT_BYTES) !=
        read_le32(&header[HEADER_CRC32])) {
        return COMP_RECORDING_RESOURCE_MOUNT_BAD_HEADER_CRC;
    }
    if (!comp_asset_store_read(store, entries_offset, entries, sizeof(entries))) {
        return COMP_RECORDING_RESOURCE_MOUNT_IO_ERROR;
    }
    if (crc32_bytes(entries, sizeof(entries)) !=
        read_le32(&header[HEADER_ENTRIES_CRC32])) {
        return COMP_RECORDING_RESOURCE_MOUNT_BAD_INDEX_CRC;
    }

    for (uint32_t index = 0u;
         index < COMP_RECORDING_RESOURCE_PACK_ENTRY_COUNT;
         ++index) {
        const uint8_t *source =
            &entries[index * COMP_RECORDING_RESOURCE_PACK_ENTRY_BYTES];
        comp_recording_resource_entry_t entry = {
            .id = (comp_recording_resource_id_t)read_le32(&source[ENTRY_ID]),
            .data_offset = read_le32(&source[ENTRY_DATA_OFFSET]),
            .data_bytes = read_le32(&source[ENTRY_DATA_BYTES]),
            .data_crc32 = read_le32(&source[ENTRY_DATA_CRC32]),
            .aux0 = read_le32(&source[ENTRY_AUX0]),
            .aux1 = read_le32(&source[ENTRY_AUX1]),
            .flags = read_le32(&source[ENTRY_FLAGS]),
        };
        if (!expected_entry(&entry) ||
            !range_valid(total_bytes, entry.data_offset, entry.data_bytes) ||
            entry.data_offset < payload_offset ||
            entry.data_offset + entry.data_bytes >
                payload_offset + payload_bytes) {
            return COMP_RECORDING_RESOURCE_MOUNT_BAD_ENTRY;
        }
        for (uint32_t prior = 0u; prior < index; ++prior) {
            if (pack->entries[prior].id == entry.id) {
                return COMP_RECORDING_RESOURCE_MOUNT_BAD_ENTRY;
            }
        }
        pack->entries[index] = entry;
    }

    pack->store = store;
    pack->total_bytes = total_bytes;
    pack->payload_offset = payload_offset;
    pack->payload_bytes = payload_bytes;
    pack->payload_crc32 = read_le32(&header[HEADER_PAYLOAD_CRC32]);
    return COMP_RECORDING_RESOURCE_MOUNT_OK;
}

bool comp_recording_resource_pack_get(
    const comp_recording_resource_pack_t *pack,
    comp_recording_resource_id_t id,
    comp_recording_resource_entry_t *entry)
{
    if (pack == NULL || pack->store == NULL || entry == NULL) {
        return false;
    }
    int index = entry_index(pack, id);
    if (index < 0) {
        return false;
    }
    *entry = pack->entries[index];
    return true;
}

bool comp_recording_resource_pack_verify(
    comp_recording_resource_pack_t *pack,
    comp_recording_resource_id_t id,
    uint8_t *scratch,
    size_t scratch_bytes)
{
    if (pack == NULL || pack->store == NULL ||
        scratch == NULL || scratch_bytes == 0u) {
        return false;
    }
    int index = entry_index(pack, id);
    if (index < 0) {
        return false;
    }
    uint32_t mask = 1u << (uint32_t)index;
    if ((pack->verified_mask & mask) != 0u) {
        return true;
    }

    const comp_recording_resource_entry_t *entry = &pack->entries[index];
    uint32_t consumed = 0u;
    uint32_t crc = 0xFFFFFFFFu;
    while (consumed < entry->data_bytes) {
        size_t chunk = entry->data_bytes - consumed;
        if (chunk > scratch_bytes) {
            chunk = scratch_bytes;
        }
        if (!comp_asset_store_read(pack->store,
                                   entry->data_offset + consumed,
                                   scratch,
                                   chunk)) {
            return false;
        }
        crc = crc32_update(crc, scratch, chunk);
        consumed += (uint32_t)chunk;
    }
    if ((crc ^ 0xFFFFFFFFu) != entry->data_crc32) {
        return false;
    }
    pack->verified_mask |= mask;
    return true;
}

bool comp_recording_resource_pack_verify_all(
    comp_recording_resource_pack_t *pack,
    uint8_t *scratch,
    size_t scratch_bytes)
{
    if (!comp_recording_resource_pack_verify(
            pack, COMP_RECORDING_RESOURCE_G7_SPEECH_PCM,
            scratch, scratch_bytes) ||
        !comp_recording_resource_pack_verify(
            pack, COMP_RECORDING_RESOURCE_OPUS16_FIXTURE,
            scratch, scratch_bytes)) {
        return false;
    }

    uint32_t consumed = 0u;
    uint32_t crc = 0xFFFFFFFFu;
    while (consumed < pack->payload_bytes) {
        size_t chunk = pack->payload_bytes - consumed;
        if (chunk > scratch_bytes) {
            chunk = scratch_bytes;
        }
        if (!comp_asset_store_read(pack->store,
                                   pack->payload_offset + consumed,
                                   scratch,
                                   chunk)) {
            return false;
        }
        crc = crc32_update(crc, scratch, chunk);
        consumed += (uint32_t)chunk;
    }
    return (crc ^ 0xFFFFFFFFu) == pack->payload_crc32;
}

bool comp_recording_resource_pack_read(
    const comp_recording_resource_pack_t *pack,
    comp_recording_resource_id_t id,
    uint32_t offset,
    uint8_t *destination,
    size_t length)
{
    if (pack == NULL || pack->store == NULL || destination == NULL ||
        length > UINT32_MAX) {
        return false;
    }
    int index = entry_index(pack, id);
    if (index < 0 ||
        (pack->verified_mask & (1u << (uint32_t)index)) == 0u) {
        return false;
    }
    const comp_recording_resource_entry_t *entry = &pack->entries[index];
    return range_valid(entry->data_bytes, offset, (uint32_t)length) &&
           comp_asset_store_read(pack->store,
                                 entry->data_offset + offset,
                                 destination,
                                 length);
}

const char *comp_recording_resource_mount_result_name(
    comp_recording_resource_mount_result_t result)
{
    switch (result) {
    case COMP_RECORDING_RESOURCE_MOUNT_OK:
        return "ok";
    case COMP_RECORDING_RESOURCE_MOUNT_BAD_ARGUMENT:
        return "bad_argument";
    case COMP_RECORDING_RESOURCE_MOUNT_IO_ERROR:
        return "io_error";
    case COMP_RECORDING_RESOURCE_MOUNT_BAD_HEADER:
        return "bad_header";
    case COMP_RECORDING_RESOURCE_MOUNT_BAD_HEADER_CRC:
        return "bad_header_crc";
    case COMP_RECORDING_RESOURCE_MOUNT_BAD_INDEX_CRC:
        return "bad_index_crc";
    case COMP_RECORDING_RESOURCE_MOUNT_BAD_ENTRY:
        return "bad_entry";
    default:
        return "unknown";
    }
}
