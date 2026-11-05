#include "../storage/companion_crc32.h"
#include "ui_asset_generation.h"

#include <string.h>

#define ROOT_MAGIC_0 'C'
#define ROOT_MAGIC_1 'U'
#define ROOT_MAGIC_2 'I'
#define ROOT_MAGIC_3 'R'
#define MANIFEST_MAGIC_0 'C'
#define MANIFEST_MAGIC_1 'U'
#define MANIFEST_MAGIC_2 'I'
#define MANIFEST_MAGIC_3 'M'

enum {
    ROOT_MAGIC = 0u,
    ROOT_VERSION = 4u,
    ROOT_HEADER_BYTES = 6u,
    ROOT_GENERATION = 8u,
    ROOT_BASE_PACK_SIZE = 12u,
    ROOT_BLOB_OFFSET = 16u,
    ROOT_BLOB_SIZE = 20u,
    ROOT_BLOB_CRC32 = 24u,
    ROOT_MANIFEST_OFFSET = 28u,
    ROOT_MANIFEST_SIZE = 32u,
    ROOT_MANIFEST_CRC32 = 36u,
    ROOT_ARENA_NEXT = 40u,
    ROOT_RESOURCE_ID = 44u,
    ROOT_CRC32 = 124u,
};

enum {
    MANIFEST_MAGIC = 0u,
    MANIFEST_VERSION = 4u,
    MANIFEST_HEADER_SIZE = 6u,
    MANIFEST_ENTRY_COUNT = 8u,
    MANIFEST_ENTRY_SIZE = 10u,
    MANIFEST_TOTAL_SIZE = 12u,
    MANIFEST_ENTRIES = COMP_UI_ASSET_MANIFEST_HEADER_BYTES,
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

static uint32_t crc32_update(uint32_t crc,const uint8_t *data,size_t length)
{return companion_crc32(crc^UINT32_MAX,data,length)^UINT32_MAX;}

static uint32_t crc32_bytes(const uint8_t *data, size_t length)
{
    return crc32_update(0xFFFFFFFFu, data, length) ^ 0xFFFFFFFFu;
}

static bool range_valid(uint32_t size, uint32_t offset, uint32_t length)
{
    return offset <= size && length <= size - offset;
}

static uint32_t align_sector(uint32_t value)
{
    const uint32_t mask = COMP_UI_ASSET_GENERATION_SECTOR_BYTES - 1u;
    return (value + mask) & ~mask;
}

static bool resource_id_equal(const uint8_t *left, const uint8_t *right)
{
    return memcmp(left, right, COMP_UI_ASSET_GENERATION_ID_BYTES) == 0;
}

uint32_t comp_ui_asset_state_hash(const char *state_id)
{
    uint32_t hash = 0x811C9DC5u;
    if (state_id == NULL) {
        return 0u;
    }
    while (*state_id != '\0') {
        hash = (hash ^ (uint8_t)*state_id++) * 0x01000193u;
    }
    return hash;
}

static bool read_root(const comp_asset_store_t *store,
                      uint32_t offset,
                      comp_ui_asset_generation_root_t *root)
{
    uint8_t bytes[COMP_UI_ASSET_GENERATION_ROOT_BYTES];
    uint32_t manifest_absolute;

    if (store == NULL || root == NULL ||
        !range_valid(store->size_bytes, offset, sizeof(bytes)) ||
        !comp_asset_store_read(store, offset, bytes, sizeof(bytes)) ||
        bytes[ROOT_MAGIC] != ROOT_MAGIC_0 ||
        bytes[ROOT_MAGIC + 1u] != ROOT_MAGIC_1 ||
        bytes[ROOT_MAGIC + 2u] != ROOT_MAGIC_2 ||
        bytes[ROOT_MAGIC + 3u] != ROOT_MAGIC_3 ||
        read_le16(&bytes[ROOT_VERSION]) !=
            COMP_UI_ASSET_GENERATION_FORMAT_VERSION ||
        read_le16(&bytes[ROOT_HEADER_BYTES]) != sizeof(bytes) ||
        crc32_bytes(bytes, ROOT_CRC32) != read_le32(&bytes[ROOT_CRC32])) {
        return false;
    }

    *root = (comp_ui_asset_generation_root_t){
        .generation = read_le32(&bytes[ROOT_GENERATION]),
        .root_offset = offset,
        .base_pack_size = read_le32(&bytes[ROOT_BASE_PACK_SIZE]),
        .blob_offset = read_le32(&bytes[ROOT_BLOB_OFFSET]),
        .blob_size = read_le32(&bytes[ROOT_BLOB_SIZE]),
        .blob_crc32 = read_le32(&bytes[ROOT_BLOB_CRC32]),
        .manifest_offset = read_le32(&bytes[ROOT_MANIFEST_OFFSET]),
        .manifest_size = read_le32(&bytes[ROOT_MANIFEST_SIZE]),
        .manifest_crc32 = read_le32(&bytes[ROOT_MANIFEST_CRC32]),
        .arena_next_offset = read_le32(&bytes[ROOT_ARENA_NEXT]),
    };
    memcpy(root->resource_id, &bytes[ROOT_RESOURCE_ID],
           sizeof(root->resource_id));
    manifest_absolute = root->blob_offset + root->manifest_offset;
    return root->generation != 0u &&
           root->base_pack_size <= root->blob_offset &&
           root->blob_offset < COMP_UI_ASSET_GENERATION_ARENA_END &&
           range_valid(COMP_UI_ASSET_GENERATION_ARENA_END,
                       root->blob_offset, root->blob_size) &&
           range_valid(root->blob_size,
                       root->manifest_offset, root->manifest_size) &&
           range_valid(store->size_bytes,
                       manifest_absolute, root->manifest_size) &&
           root->arena_next_offset == align_sector(
               root->blob_offset + root->blob_size) &&
           root->arena_next_offset <= COMP_UI_ASSET_GENERATION_ARENA_END;
}

static bool verify_store_crc(const comp_asset_store_t *store,
                             uint32_t offset,
                             uint32_t length,
                             uint32_t expected_crc)
{
    uint8_t scratch[256];
    uint32_t consumed = 0u;
    uint32_t crc = 0xFFFFFFFFu;

    while (consumed < length) {
        uint32_t chunk = length - consumed;
        if (chunk > sizeof(scratch)) {
            chunk = sizeof(scratch);
        }
        if (!comp_asset_store_read(store, offset + consumed, scratch, chunk)) {
            return false;
        }
        crc = crc32_update(crc, scratch, chunk);
        consumed += chunk;
    }
    return (crc ^ 0xFFFFFFFFu) == expected_crc;
}

static bool read_entry(const comp_ui_asset_generation_t *generation,
                       uint16_t index,
                       comp_ui_asset_generation_entry_t *entry);

static bool validate_manifest(comp_ui_asset_generation_t *generation)
{
    uint8_t header[COMP_UI_ASSET_MANIFEST_HEADER_BYTES];
    uint32_t absolute =
        generation->root.blob_offset + generation->root.manifest_offset;
    uint16_t count;

    if (!verify_store_crc(generation->store,
                          generation->root.blob_offset,
                          generation->root.blob_size,
                          generation->root.blob_crc32) ||
        !verify_store_crc(generation->store,
                          absolute,
                          generation->root.manifest_size,
                          generation->root.manifest_crc32) ||
        !comp_asset_store_read(generation->store,
                               absolute, header, sizeof(header)) ||
        header[MANIFEST_MAGIC] != MANIFEST_MAGIC_0 ||
        header[MANIFEST_MAGIC + 1u] != MANIFEST_MAGIC_1 ||
        header[MANIFEST_MAGIC + 2u] != MANIFEST_MAGIC_2 ||
        header[MANIFEST_MAGIC + 3u] != MANIFEST_MAGIC_3 ||
        read_le16(&header[MANIFEST_VERSION]) !=
            COMP_UI_ASSET_GENERATION_FORMAT_VERSION ||
        read_le16(&header[MANIFEST_HEADER_SIZE]) != sizeof(header) ||
        read_le16(&header[MANIFEST_ENTRY_SIZE]) !=
            COMP_UI_ASSET_MANIFEST_ENTRY_BYTES ||
        read_le32(&header[MANIFEST_TOTAL_SIZE]) !=
            generation->root.manifest_size) {
        return false;
    }
    count = read_le16(&header[MANIFEST_ENTRY_COUNT]);
    if ((uint32_t)count * COMP_UI_ASSET_MANIFEST_ENTRY_BYTES >
        generation->root.manifest_size - sizeof(header)) {
        return false;
    }
    generation->entry_count = count;
    for (uint16_t index = 0u; index < count; ++index) {
        comp_ui_asset_generation_entry_t entry;
        comp_ui_asset_generation_entry_t previous;
        uint16_t encoding;
        if (!read_entry(generation, index, &entry) ||
            (index > 0u &&
             (!read_entry(generation, (uint16_t)(index - 1u), &previous) ||
              previous.state_hash >= entry.state_hash)) ||
            entry.duration_ms == 0u) {
            return false;
        }
        encoding = entry.flags &
                   (COMP_UI_ASSET_ENTRY_OVERRIDE_RAW_1BPP |
                    COMP_UI_ASSET_ENTRY_OVERRIDE_PACKBITS_1BPP |
                    COMP_UI_ASSET_ENTRY_XOR_PATCH_1BPP);
        if ((entry.flags & ~(
                 COMP_UI_ASSET_ENTRY_OVERRIDE_RAW_1BPP |
                 COMP_UI_ASSET_ENTRY_OVERRIDE_PACKBITS_1BPP |
                 COMP_UI_ASSET_ENTRY_XOR_PATCH_1BPP)) != 0u ||
            (encoding != 0u &&
             encoding != COMP_UI_ASSET_ENTRY_OVERRIDE_RAW_1BPP &&
             encoding != COMP_UI_ASSET_ENTRY_OVERRIDE_PACKBITS_1BPP &&
             encoding != COMP_UI_ASSET_ENTRY_XOR_PATCH_1BPP)) {
            return false;
        }
        if (encoding == 0u) {
            if (entry.base_frame_index == UINT16_MAX ||
                entry.payload_offset != 0u ||
                entry.payload_size != 0u ||
                entry.payload_crc32 != 0u) {
                return false;
            }
        } else if (
            ((encoding == COMP_UI_ASSET_ENTRY_XOR_PATCH_1BPP) !=
             (entry.base_frame_index != UINT16_MAX)) ||
            entry.payload_size == 0u ||
            entry.payload_offset < generation->root.base_pack_size ||
            !range_valid(COMP_UI_ASSET_GENERATION_ARENA_END,
                         entry.payload_offset,
                         entry.payload_size) ||
            (encoding == COMP_UI_ASSET_ENTRY_OVERRIDE_RAW_1BPP &&
             entry.payload_size != 5000u)) {
            return false;
        }
    }
    return true;
}

static bool mount_root(comp_ui_asset_generation_t *generation,
                       const comp_asset_store_t *store,
                       const comp_ui_asset_generation_root_t *root)
{
    *generation = (comp_ui_asset_generation_t){
        .store = store,
        .root = *root,
    };
    if (!validate_manifest(generation)) {
        *generation = (comp_ui_asset_generation_t){.store = store};
        return false;
    }
    generation->mounted = true;
    return true;
}

bool comp_ui_asset_generation_mount(
    comp_ui_asset_generation_t *generation,
    const comp_asset_store_t *store)
{
    comp_ui_asset_generation_root_t root_a;
    comp_ui_asset_generation_root_t root_b;
    bool have_a;
    bool have_b;

    if (generation == NULL || store == NULL ||
        store->size_bytes < COMP_UI_ASSET_GENERATION_ROOT_B_OFFSET +
                                COMP_UI_ASSET_GENERATION_SECTOR_BYTES) {
        return false;
    }
    *generation = (comp_ui_asset_generation_t){.store = store};
    have_a = read_root(store, COMP_UI_ASSET_GENERATION_ROOT_A_OFFSET, &root_a);
    have_b = read_root(store, COMP_UI_ASSET_GENERATION_ROOT_B_OFFSET, &root_b);
    if (!have_a && !have_b) {
        return false;
    }
    if (have_a && have_b) {
        const comp_ui_asset_generation_root_t *newer =
            root_b.generation > root_a.generation ? &root_b : &root_a;
        const comp_ui_asset_generation_root_t *older =
            newer == &root_b ? &root_a : &root_b;
        return mount_root(generation, store, newer) ||
               mount_root(generation, store, older);
    }
    return mount_root(generation, store, have_a ? &root_a : &root_b);
}

static bool read_entry(const comp_ui_asset_generation_t *generation,
                       uint16_t index,
                       comp_ui_asset_generation_entry_t *entry)
{
    uint8_t bytes[COMP_UI_ASSET_MANIFEST_ENTRY_BYTES];
    uint32_t offset;

    if (generation == NULL || entry == NULL ||
        index >= generation->entry_count) {
        return false;
    }
    offset = generation->root.blob_offset +
             generation->root.manifest_offset +
             MANIFEST_ENTRIES +
             (uint32_t)index * sizeof(bytes);
    if (!comp_asset_store_read(generation->store,
                               offset, bytes, sizeof(bytes))) {
        return false;
    }
    *entry = (comp_ui_asset_generation_entry_t){
        .state_hash = read_le32(&bytes[0]),
        .base_frame_index = read_le16(&bytes[4]),
        .flags = read_le16(&bytes[6]),
        .frame_crc32 = read_le32(&bytes[8]),
        .payload_offset = read_le32(&bytes[12]),
        .payload_size = read_le16(&bytes[16]),
        .duration_ms = read_le16(&bytes[18]),
        .payload_crc32 = read_le32(&bytes[20]),
    };
    return true;
}

bool comp_ui_asset_generation_find(
    const comp_ui_asset_generation_t *generation,
    uint32_t state_hash,
    comp_ui_asset_generation_entry_t *entry)
{
    uint16_t low = 0u;
    uint16_t high;

    if (generation == NULL || !generation->mounted || entry == NULL) {
        return false;
    }
    high = generation->entry_count;
    while (low < high) {
        uint16_t middle = (uint16_t)(low + (uint16_t)((high - low) / 2u));
        comp_ui_asset_generation_entry_t candidate;
        if (!read_entry(generation, middle, &candidate)) {
            return false;
        }
        if (candidate.state_hash < state_hash) {
            low = (uint16_t)(middle + 1u);
        } else {
            high = middle;
        }
    }
    if (low >= generation->entry_count || !read_entry(generation, low, entry) ||
        entry->state_hash != state_hash) {
        return false;
    }
    return true;
}

bool comp_ui_asset_generation_read_override(
    const comp_ui_asset_generation_t *generation,
    const comp_ui_asset_generation_entry_t *entry,
    uint8_t *destination,
    size_t destination_size)
{
    uint32_t absolute;
    uint16_t encoding;

    if (generation == NULL || !generation->mounted || entry == NULL ||
        destination == NULL ||
        entry->payload_size == 0u ||
        destination_size < 5000u ||
        !range_valid(COMP_UI_ASSET_GENERATION_ARENA_END,
                     entry->payload_offset, entry->payload_size) ||
        entry->payload_offset < generation->root.base_pack_size) {
        return false;
    }
    encoding = entry->flags &
               (COMP_UI_ASSET_ENTRY_OVERRIDE_RAW_1BPP |
                COMP_UI_ASSET_ENTRY_OVERRIDE_PACKBITS_1BPP |
                COMP_UI_ASSET_ENTRY_XOR_PATCH_1BPP);
    if (encoding != COMP_UI_ASSET_ENTRY_OVERRIDE_RAW_1BPP &&
        encoding != COMP_UI_ASSET_ENTRY_OVERRIDE_PACKBITS_1BPP &&
        encoding != COMP_UI_ASSET_ENTRY_XOR_PATCH_1BPP) {
        return false;
    }
    absolute = entry->payload_offset;
    if (encoding == COMP_UI_ASSET_ENTRY_XOR_PATCH_1BPP) {
        uint8_t scratch[64];
        uint32_t consumed = 0u;
        uint32_t payload_crc = 0xFFFFFFFFu;
        uint32_t previous_end = 0u;
        while (consumed < entry->payload_size) {
            uint8_t header[3];
            uint32_t offset;
            uint32_t count;
            uint32_t applied = 0u;
            if (entry->payload_size - consumed < sizeof(header) ||
                !comp_asset_store_read(generation->store,
                                       absolute + consumed,
                                       header,
                                       sizeof(header))) {
                return false;
            }
            payload_crc = crc32_update(payload_crc, header, sizeof(header));
            consumed += sizeof(header);
            offset = read_le16(header);
            count = header[2];
            if (count == 0u || offset < previous_end ||
                offset > 5000u || count > 5000u - offset ||
                count > entry->payload_size - consumed) {
                return false;
            }
            while (applied < count) {
                uint32_t chunk = count - applied;
                if (chunk > sizeof(scratch)) {
                    chunk = sizeof(scratch);
                }
                if (!comp_asset_store_read(generation->store,
                                           absolute + consumed,
                                           scratch,
                                           chunk)) {
                    return false;
                }
                payload_crc = crc32_update(payload_crc, scratch, chunk);
                for (uint32_t index = 0u; index < chunk; ++index) {
                    destination[offset + applied + index] ^= scratch[index];
                }
                consumed += chunk;
                applied += chunk;
            }
            previous_end = offset + count;
        }
        return consumed == entry->payload_size &&
               (payload_crc ^ 0xFFFFFFFFu) == entry->payload_crc32 &&
               crc32_bytes(destination, 5000u) == entry->frame_crc32;
    }
    if (encoding == COMP_UI_ASSET_ENTRY_OVERRIDE_RAW_1BPP) {
        return entry->payload_size == 5000u &&
               comp_asset_store_read(generation->store,
                                     absolute,
                                     destination,
                                     entry->payload_size) &&
               crc32_bytes(destination, entry->payload_size) ==
                   entry->frame_crc32;
    }

    uint32_t consumed = 0u;
    uint32_t written = 0u;
    uint32_t payload_crc = 0xFFFFFFFFu;
    while (consumed < entry->payload_size && written < 5000u) {
        uint8_t control;
        if (!comp_asset_store_read(generation->store,
                                   absolute + consumed, &control, 1u)) {
            return false;
        }
        payload_crc = crc32_update(payload_crc, &control, 1u);
        consumed++;
        if (control <= 127u) {
            uint32_t count = (uint32_t)control + 1u;
            if (count > entry->payload_size - consumed ||
                count > 5000u - written ||
                !comp_asset_store_read(generation->store,
                                       absolute + consumed,
                                       destination + written,
                                       count)) {
                return false;
            }
            payload_crc =
                crc32_update(payload_crc, destination + written, count);
            consumed += count;
            written += count;
        } else if (control >= 129u) {
            uint8_t value;
            uint32_t count = 257u - (uint32_t)control;
            if (consumed >= entry->payload_size ||
                count > 5000u - written ||
                !comp_asset_store_read(generation->store,
                                       absolute + consumed, &value, 1u)) {
                return false;
            }
            payload_crc = crc32_update(payload_crc, &value, 1u);
            consumed++;
            memset(destination + written, value, count);
            written += count;
        }
    }
    return consumed == entry->payload_size && written == 5000u &&
           (payload_crc ^ 0xFFFFFFFFu) == entry->payload_crc32 &&
           crc32_bytes(destination, 5000u) == entry->frame_crc32;
}

bool comp_ui_asset_generation_apply_xor_region(
    const comp_ui_asset_generation_t *generation,
    const comp_ui_asset_generation_entry_t *entry,
    uint8_t *destination,
    size_t destination_size,
    uint16_t frame_stride,
    uint16_t x_byte,
    uint16_t y,
    uint16_t width_bytes,
    uint16_t height,
    uint8_t *payload_scratch,
    size_t payload_scratch_size)
{
    uint32_t consumed = 0u;
    uint32_t previous_end = 0u;

    if (generation == NULL || !generation->mounted || entry == NULL ||
        destination == NULL || frame_stride == 0u || width_bytes == 0u ||
        height == 0u || payload_scratch == NULL ||
        (entry->flags & COMP_UI_ASSET_ENTRY_XOR_PATCH_1BPP) == 0u ||
        entry->payload_size == 0u ||
        entry->payload_size > payload_scratch_size ||
        x_byte + width_bytes > frame_stride ||
        (size_t)(y + height) * frame_stride > destination_size ||
        !range_valid(COMP_UI_ASSET_GENERATION_ARENA_END,
                     entry->payload_offset,
                     entry->payload_size) ||
        entry->payload_offset < generation->root.base_pack_size ||
        !comp_asset_store_read(generation->store,
                               entry->payload_offset,
                               payload_scratch,
                               entry->payload_size) ||
        crc32_bytes(payload_scratch, entry->payload_size) !=
            entry->payload_crc32) {
        return false;
    }

    while (consumed < entry->payload_size) {
        uint32_t offset;
        uint32_t count;
        if (entry->payload_size - consumed < 3u) {
            return false;
        }
        offset = read_le16(payload_scratch + consumed);
        count = payload_scratch[consumed + 2u];
        consumed += 3u;
        if (count == 0u || offset < previous_end ||
            offset > 5000u || count > 5000u - offset ||
            count > entry->payload_size - consumed) {
            return false;
        }
        for (uint32_t index = 0u; index < count; ++index) {
            const uint32_t frame_offset = offset + index;
            const uint32_t row = frame_offset / frame_stride;
            const uint32_t column = frame_offset % frame_stride;
            if (row >= y && row < (uint32_t)y + height &&
                column >= x_byte &&
                column < (uint32_t)x_byte + width_bytes) {
                destination[frame_offset] ^=
                    payload_scratch[consumed + index];
            }
        }
        consumed += count;
        previous_end = offset + count;
    }
    return consumed == entry->payload_size;
}

static bool io_crc(const comp_ui_asset_generation_io_t *io,
                   uint32_t offset,
                   uint32_t length,
                   uint32_t expected)
{
    uint8_t scratch[256];
    uint32_t crc = 0xFFFFFFFFu;
    uint32_t consumed = 0u;

    while (consumed < length) {
        uint32_t chunk = length - consumed;
        if (chunk > sizeof(scratch)) {
            chunk = sizeof(scratch);
        }
        if (!io->read(io->context, offset + consumed, scratch, chunk)) {
            return false;
        }
        crc = crc32_update(crc, scratch, chunk);
        consumed += chunk;
    }
    return (crc ^ 0xFFFFFFFFu) == expected;
}

static bool io_read_store(void *context,
                          uint32_t offset,
                          uint8_t *data,
                          size_t length)
{
    const comp_ui_asset_generation_io_t *io =
        (const comp_ui_asset_generation_io_t *)context;
    return io->read(io->context, offset, data, length);
}

static void encode_root(uint8_t bytes[COMP_UI_ASSET_GENERATION_ROOT_BYTES],
                        const comp_ui_asset_generation_root_t *root)
{
    memset(bytes, 0, COMP_UI_ASSET_GENERATION_ROOT_BYTES);
    bytes[0] = ROOT_MAGIC_0;
    bytes[1] = ROOT_MAGIC_1;
    bytes[2] = ROOT_MAGIC_2;
    bytes[3] = ROOT_MAGIC_3;
    write_le16(&bytes[ROOT_VERSION],
               COMP_UI_ASSET_GENERATION_FORMAT_VERSION);
    write_le16(&bytes[ROOT_HEADER_BYTES],
               COMP_UI_ASSET_GENERATION_ROOT_BYTES);
    write_le32(&bytes[ROOT_GENERATION], root->generation);
    write_le32(&bytes[ROOT_BASE_PACK_SIZE], root->base_pack_size);
    write_le32(&bytes[ROOT_BLOB_OFFSET], root->blob_offset);
    write_le32(&bytes[ROOT_BLOB_SIZE], root->blob_size);
    write_le32(&bytes[ROOT_BLOB_CRC32], root->blob_crc32);
    write_le32(&bytes[ROOT_MANIFEST_OFFSET], root->manifest_offset);
    write_le32(&bytes[ROOT_MANIFEST_SIZE], root->manifest_size);
    write_le32(&bytes[ROOT_MANIFEST_CRC32], root->manifest_crc32);
    write_le32(&bytes[ROOT_ARENA_NEXT], root->arena_next_offset);
    memcpy(&bytes[ROOT_RESOURCE_ID], root->resource_id,
           COMP_UI_ASSET_GENERATION_ID_BYTES);
    write_le32(&bytes[ROOT_CRC32], crc32_bytes(bytes, ROOT_CRC32));
}

comp_ui_asset_install_receipt_t comp_ui_asset_generation_begin(
    comp_ui_asset_generation_transaction_t *transaction,
    const comp_ui_asset_generation_io_t *io,
    uint32_t base_pack_size,
    uint32_t expected_active_generation,
    const uint8_t resource_id[COMP_UI_ASSET_GENERATION_ID_BYTES],
    uint32_t blob_size,
    uint32_t blob_crc32,
    uint32_t manifest_offset,
    uint32_t manifest_size,
    uint32_t manifest_crc32)
{
    comp_ui_asset_install_receipt_t receipt = {
        .result = COMP_UI_ASSET_INSTALL_BAD_ARGUMENT,
    };
    comp_asset_store_t store;
    comp_ui_asset_generation_t active;
    bool have_active;
    uint32_t blob_offset;

    if (transaction == NULL || io == NULL || io->read == NULL ||
        io->erase_4k == NULL ||
        io->write == NULL || resource_id == NULL ||
        blob_size == 0u || manifest_size < COMP_UI_ASSET_MANIFEST_HEADER_BYTES ||
        !range_valid(blob_size, manifest_offset, manifest_size) ||
        io->partition_size <
            COMP_UI_ASSET_GENERATION_ROOT_B_OFFSET +
                COMP_UI_ASSET_GENERATION_SECTOR_BYTES ||
        base_pack_size == 0u ||
        base_pack_size >= COMP_UI_ASSET_GENERATION_ARENA_END) {
        return receipt;
    }
    *transaction = (comp_ui_asset_generation_transaction_t){0};
    if (!comp_asset_store_init_reader(&store,
                                      COMP_ASSET_STORAGE_EXTERNAL_NOR,
                                      io->partition_size,
                                      io_read_store,
                                      (void *)io)) {
        return receipt;
    }
    have_active = comp_ui_asset_generation_mount(&active, &store);
    receipt.previous_generation = have_active ? active.root.generation : 0u;
    receipt.active_generation = receipt.previous_generation;
    if (receipt.previous_generation != expected_active_generation) {
        receipt.result = COMP_UI_ASSET_INSTALL_STALE_GENERATION;
        return receipt;
    }
    if (have_active &&
        resource_id_equal(active.root.resource_id, resource_id)) {
        receipt.result = COMP_UI_ASSET_INSTALL_ALREADY_CURRENT;
        return receipt;
    }

    blob_offset = have_active
                      ? active.root.arena_next_offset
                      : align_sector(base_pack_size);
    if (blob_offset >= COMP_UI_ASSET_GENERATION_ARENA_END ||
        !range_valid(COMP_UI_ASSET_GENERATION_ARENA_END,
                     blob_offset, blob_size)) {
        receipt.result = COMP_UI_ASSET_INSTALL_NO_SPACE;
        return receipt;
    }
    receipt.blob_offset = blob_offset;
    for (uint32_t offset = 0u; offset < align_sector(blob_size);
         offset += COMP_UI_ASSET_GENERATION_SECTOR_BYTES) {
        if (!io->erase_4k(io->context, blob_offset + offset)) {
            receipt.result = COMP_UI_ASSET_INSTALL_ERASE_FAILED;
            return receipt;
        }
        receipt.sectors_erased++;
    }
    uint32_t inactive_root =
        have_active &&
                active.root.root_offset ==
                    COMP_UI_ASSET_GENERATION_ROOT_A_OFFSET
            ? COMP_UI_ASSET_GENERATION_ROOT_B_OFFSET
            : COMP_UI_ASSET_GENERATION_ROOT_A_OFFSET;
    transaction->next_root = (comp_ui_asset_generation_root_t){
        .generation = receipt.previous_generation + 1u,
        .root_offset = inactive_root,
        .base_pack_size = base_pack_size,
        .blob_offset = blob_offset,
        .blob_size = blob_size,
        .blob_crc32 = blob_crc32,
        .manifest_offset = manifest_offset,
        .manifest_size = manifest_size,
        .manifest_crc32 = manifest_crc32,
        .arena_next_offset = align_sector(blob_offset + blob_size),
    };
    memcpy(transaction->next_root.resource_id, resource_id,
           sizeof(transaction->next_root.resource_id));
    transaction->io = io;
    transaction->receipt = receipt;
    transaction->expected_blob_crc32 = blob_crc32;
    transaction->running_blob_crc32 = 0xFFFFFFFFu;
    transaction->active = true;
    transaction->receipt.result = COMP_UI_ASSET_INSTALL_OK;
    return transaction->receipt;
}

bool comp_ui_asset_generation_write(
    comp_ui_asset_generation_transaction_t *transaction,
    const uint8_t *data,
    size_t length)
{
    if (transaction == NULL || !transaction->active || data == NULL ||
        length == 0u ||
        transaction->bytes_written > transaction->next_root.blob_size ||
        length > transaction->next_root.blob_size -
                     transaction->bytes_written) {
        return false;
    }
    if (!transaction->io->write(
            transaction->io->context,
            transaction->next_root.blob_offset + transaction->bytes_written,
            data,
            length)) {
        transaction->receipt.result = COMP_UI_ASSET_INSTALL_WRITE_FAILED;
        transaction->active = false;
        return false;
    }
    transaction->running_blob_crc32 =
        crc32_update(transaction->running_blob_crc32, data, length);
    transaction->bytes_written += (uint32_t)length;
    transaction->receipt.blob_bytes_written += (uint32_t)length;
    return true;
}

comp_ui_asset_install_receipt_t comp_ui_asset_generation_finish(
    comp_ui_asset_generation_transaction_t *transaction)
{
    uint8_t root_bytes[COMP_UI_ASSET_GENERATION_ROOT_BYTES];
    uint32_t inactive_root;
    comp_asset_store_t store;
    comp_ui_asset_generation_t candidate;

    if (transaction == NULL || !transaction->active) {
        return transaction == NULL
                   ? (comp_ui_asset_install_receipt_t){
                         .result = COMP_UI_ASSET_INSTALL_BAD_ARGUMENT}
                   : transaction->receipt;
    }
    if (transaction->bytes_written != transaction->next_root.blob_size ||
        (transaction->running_blob_crc32 ^ 0xFFFFFFFFu) !=
            transaction->expected_blob_crc32 ||
        !io_crc(transaction->io,
                transaction->next_root.blob_offset,
                transaction->next_root.blob_size,
                transaction->expected_blob_crc32) ||
        !io_crc(transaction->io,
                transaction->next_root.blob_offset +
                    transaction->next_root.manifest_offset,
                transaction->next_root.manifest_size,
                transaction->next_root.manifest_crc32)) {
        transaction->receipt.result = COMP_UI_ASSET_INSTALL_VERIFY_FAILED;
        transaction->active = false;
        return transaction->receipt;
    }
    if (!comp_asset_store_init_reader(
            &store,
            COMP_ASSET_STORAGE_EXTERNAL_NOR,
            transaction->io->partition_size,
            io_read_store,
            (void *)transaction->io) ||
        !mount_root(
            &candidate, &store, &transaction->next_root)) {
        transaction->receipt.result = COMP_UI_ASSET_INSTALL_BAD_LAYOUT;
        transaction->active = false;
        return transaction->receipt;
    }
    inactive_root = transaction->next_root.root_offset;
    encode_root(root_bytes, &transaction->next_root);
    if (!transaction->io->erase_4k(transaction->io->context,
                                   inactive_root)) {
        transaction->receipt.result =
            COMP_UI_ASSET_INSTALL_ROOT_COMMIT_FAILED;
        transaction->active = false;
        return transaction->receipt;
    }
    transaction->receipt.sectors_erased++;
    if (!transaction->io->write(transaction->io->context, inactive_root,
                                root_bytes, sizeof(root_bytes)) ||
        !io_crc(transaction->io, inactive_root, sizeof(root_bytes),
                crc32_bytes(root_bytes, sizeof(root_bytes)))) {
        transaction->receipt.result =
            COMP_UI_ASSET_INSTALL_ROOT_COMMIT_FAILED;
        transaction->active = false;
        return transaction->receipt;
    }
    transaction->receipt.root_bytes_written = sizeof(root_bytes);
    transaction->receipt.active_generation =
        transaction->next_root.generation;
    transaction->receipt.result = COMP_UI_ASSET_INSTALL_OK;
    transaction->active = false;
    return transaction->receipt;
}

void comp_ui_asset_generation_abort(
    comp_ui_asset_generation_transaction_t *transaction)
{
    if (transaction != NULL) {
        transaction->active = false;
    }
}

comp_ui_asset_install_receipt_t comp_ui_asset_generation_install(
    const comp_ui_asset_generation_io_t *io,
    uint32_t base_pack_size,
    uint32_t expected_active_generation,
    const uint8_t resource_id[COMP_UI_ASSET_GENERATION_ID_BYTES],
    const uint8_t *blob,
    uint32_t blob_size,
    uint32_t manifest_offset,
    uint32_t manifest_size)
{
    if (blob == NULL || manifest_offset > blob_size ||
        manifest_size > blob_size - manifest_offset) {
        return (comp_ui_asset_install_receipt_t){
            .result = COMP_UI_ASSET_INSTALL_BAD_ARGUMENT};
    }
    comp_ui_asset_generation_transaction_t transaction;
    comp_ui_asset_install_receipt_t receipt =
        comp_ui_asset_generation_begin(
            &transaction,
            io,
            base_pack_size,
            expected_active_generation,
            resource_id,
            blob_size,
            crc32_bytes(blob, blob_size),
            manifest_offset,
            manifest_size,
            crc32_bytes(blob + manifest_offset, manifest_size));
    if (receipt.result != COMP_UI_ASSET_INSTALL_OK) {
        return receipt;
    }
    if (!comp_ui_asset_generation_write(&transaction, blob, blob_size)) {
        return transaction.receipt;
    }
    return comp_ui_asset_generation_finish(&transaction);
}

const char *comp_ui_asset_install_result_name(
    comp_ui_asset_install_result_t result)
{
    switch (result) {
    case COMP_UI_ASSET_INSTALL_OK: return "ok";
    case COMP_UI_ASSET_INSTALL_ALREADY_CURRENT: return "already_current";
    case COMP_UI_ASSET_INSTALL_BAD_ARGUMENT: return "bad_argument";
    case COMP_UI_ASSET_INSTALL_BAD_LAYOUT: return "bad_layout";
    case COMP_UI_ASSET_INSTALL_STALE_GENERATION: return "stale_generation";
    case COMP_UI_ASSET_INSTALL_NO_SPACE: return "no_space";
    case COMP_UI_ASSET_INSTALL_ERASE_FAILED: return "erase_failed";
    case COMP_UI_ASSET_INSTALL_WRITE_FAILED: return "write_failed";
    case COMP_UI_ASSET_INSTALL_VERIFY_FAILED: return "verify_failed";
    case COMP_UI_ASSET_INSTALL_ROOT_COMMIT_FAILED: return "root_commit_failed";
    default: return "unknown";
    }
}
