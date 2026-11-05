#include "emote_asset_pack.h"

#include <string.h>

#define PACK_MAGIC_0 'C'
#define PACK_MAGIC_1 'E'
#define PACK_MAGIC_2 'M'
#define PACK_MAGIC_3 'P'

enum {
    HEADER_MAGIC = 0u,
    HEADER_VERSION = 4u,
    HEADER_SIZE = 6u,
    HEADER_TOTAL_SIZE = 8u,
    HEADER_REVISION = 12u,
    HEADER_PRIORITY = 16u,
    HEADER_FLAGS = 18u,
    HEADER_WIDTH = 20u,
    HEADER_HEIGHT = 22u,
    HEADER_STRIDE = 24u,
    HEADER_PIXEL_FORMAT = 26u,
    HEADER_FRAME_ENCODING = 27u,
    HEADER_CLIP_COUNT = 28u,
    HEADER_FRAME_COUNT = 30u,
    HEADER_CLIP_TABLE = 32u,
    HEADER_FRAME_TABLE = 36u,
    HEADER_STRING_TABLE = 40u,
    HEADER_STRING_SIZE = 44u,
    HEADER_PAYLOAD = 48u,
    HEADER_PAYLOAD_SIZE = 52u,
    HEADER_PAYLOAD_CRC32 = 56u,
    HEADER_INDEX_CRC32 = 60u,
    HEADER_PACK_NAME = 64u,
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

static void write_le16(uint8_t *data, uint16_t value)
{
    data[0] = (uint8_t)value;
    data[1] = (uint8_t)(value >> 8);
}

static void write_le32(uint8_t *data, uint32_t value)
{
    data[0] = (uint8_t)value;
    data[1] = (uint8_t)(value >> 8);
    data[2] = (uint8_t)(value >> 16);
    data[3] = (uint8_t)(value >> 24);
}

static bool range_is_valid(uint32_t size_bytes, uint32_t offset, uint32_t length)
{
    return offset <= size_bytes && length <= (size_bytes - offset);
}

static uint32_t frame_output_size(const comp_emote_asset_pack_t *pack)
{
    return pack == NULL ? 0u :
           (uint32_t)pack->profile.stride_bytes * pack->profile.height;
}

static uint32_t crc32_update(uint32_t crc, const uint8_t *data, size_t length)
{
    for (size_t index = 0u; index < length; ++index) {
        crc ^= data[index];
        for (uint8_t bit = 0u; bit < 8u; ++bit) {
            uint32_t mask = (uint32_t)-(int32_t)(crc & 1u);
            crc = (crc >> 1) ^ (0xEDB88320u & mask);
        }
    }
    return crc;
}

static bool verify_store_crc(const comp_asset_store_t *store,
                             uint32_t offset,
                             uint32_t length,
                             uint32_t expected_crc,
                             uint8_t *scratch,
                             size_t scratch_size)
{
    uint32_t consumed = 0u;
    uint32_t crc = 0xFFFFFFFFu;

    if (store == NULL || scratch == NULL || scratch_size == 0u) {
        return false;
    }
    while (consumed < length) {
        size_t chunk = length - consumed;
        if (chunk > scratch_size) {
            chunk = scratch_size;
        }
        if (!comp_asset_store_read(store, offset + consumed, scratch, chunk)) {
            return false;
        }
        crc = crc32_update(crc, scratch, chunk);
        consumed += (uint32_t)chunk;
    }
    return (crc ^ 0xFFFFFFFFu) == expected_crc;
}

static bool verify_store_bytes(const comp_asset_store_t *store,
                               uint32_t offset,
                               const uint8_t *expected,
                               size_t length,
                               uint8_t *scratch,
                               size_t scratch_size)
{
    size_t consumed = 0u;

    if (store == NULL || expected == NULL || scratch == NULL || scratch_size == 0u) {
        return false;
    }
    while (consumed < length) {
        size_t chunk = length - consumed;
        if (chunk > scratch_size) {
            chunk = scratch_size;
        }
        if (!comp_asset_store_read(store,
                                   offset + (uint32_t)consumed,
                                   scratch,
                                   chunk) ||
            memcmp(scratch, &expected[consumed], chunk) != 0) {
            return false;
        }
        consumed += chunk;
    }
    return true;
}

static bool string_is_valid(const char *strings, size_t string_size, uint32_t offset)
{
    return strings != NULL && offset < string_size &&
           memchr(&strings[offset], '\0', string_size - offset) != NULL;
}

bool comp_screen_asset_profile_validate(const comp_screen_asset_profile_t *profile)
{
    if (profile == NULL || profile->width == 0u || profile->height == 0u ||
        profile->pixel_format != COMP_SCREEN_PIXEL_FORMAT_MONO_1BPP_WHITE_IS_ONE_MSB) {
        return false;
    }
    return profile->stride_bytes >= (uint16_t)((profile->width + 7u) / 8u);
}

bool comp_screen_asset_profile_matches(const comp_screen_asset_profile_t *candidate,
                                       const comp_screen_asset_profile_t *target)
{
    return comp_screen_asset_profile_validate(candidate) &&
           comp_screen_asset_profile_validate(target) &&
           candidate->width == target->width &&
           candidate->height == target->height &&
           candidate->stride_bytes == target->stride_bytes &&
           candidate->pixel_format == target->pixel_format;
}

bool comp_emote_asset_pack_validate(const comp_emote_asset_pack_t *pack)
{
    if (pack == NULL || pack->name == NULL || pack->name[0] == '\0' ||
        pack->format_version != COMP_EMOTE_ASSET_PACK_FORMAT_VERSION ||
        !comp_screen_asset_profile_validate(&pack->profile) ||
        (pack->frame_encoding != COMP_EMOTE_FRAME_ENCODING_RAW_FULL_FRAME &&
         pack->frame_encoding != COMP_EMOTE_FRAME_ENCODING_PACKBITS) ||
        pack->payload_size == 0u || !pack->has_payload_crc32 ||
        pack->catalog == NULL || !comp_emote_catalog_validate(pack->catalog) ||
        pack->store == NULL ||
        !range_is_valid(pack->store->size_bytes, pack->payload_offset, pack->payload_size)) {
        return false;
    }

    for (size_t index = 0u; index < pack->catalog->frame_count; ++index) {
        const comp_emote_frame_t *frame = &pack->catalog->frames[index];
        if (!range_is_valid(pack->payload_size, frame->data_offset, frame->data_size)) {
            return false;
        }
        if ((frame->dirty_width != 0u || frame->dirty_height != 0u) &&
            (frame->dirty_width == 0u || frame->dirty_height == 0u ||
             frame->dirty_x >= pack->profile.width ||
             frame->dirty_y >= pack->profile.height ||
             frame->dirty_width > (uint16_t)(pack->profile.width - frame->dirty_x) ||
             frame->dirty_height > (uint16_t)(pack->profile.height - frame->dirty_y))) {
            return false;
        }
        if (pack->frame_encoding == COMP_EMOTE_FRAME_ENCODING_RAW_FULL_FRAME &&
            frame->data_size != (uint32_t)pack->profile.stride_bytes * pack->profile.height) {
            return false;
        }
    }
    return true;
}

const comp_emote_asset_pack_t *comp_emote_asset_pack_select(
    const comp_emote_asset_pack_t *packs,
    size_t pack_count,
    const comp_screen_asset_profile_t *target)
{
    const comp_emote_asset_pack_t *selected = NULL;

    if (packs == NULL || !comp_screen_asset_profile_validate(target)) {
        return NULL;
    }
    for (size_t index = 0u; index < pack_count; ++index) {
        const comp_emote_asset_pack_t *candidate = &packs[index];
        if (!comp_emote_asset_pack_validate(candidate) ||
            !comp_screen_asset_profile_matches(&candidate->profile, target)) {
            continue;
        }
        if (selected == NULL || candidate->priority > selected->priority ||
            (candidate->priority == selected->priority &&
             candidate->revision > selected->revision)) {
            selected = candidate;
        }
    }
    return selected;
}

typedef struct {
    const comp_asset_store_t *store;
    uint32_t offset;
    uint32_t size;
    uint32_t consumed;
    uint8_t cache[128];
    uint16_t cache_offset;
    uint16_t cache_size;
} packbits_reader_t;

static bool packbits_reader_read(packbits_reader_t *reader,
                                 uint8_t *destination,
                                 uint32_t length)
{
    if (reader == NULL || destination == NULL || length > reader->size - reader->consumed) {
        return false;
    }
    while (length > 0u) {
        uint32_t available;
        uint32_t chunk;

        if (reader->cache_offset >= reader->cache_size) {
            uint32_t remaining = reader->size - reader->consumed;
            uint32_t load = remaining > sizeof(reader->cache)
                                ? sizeof(reader->cache)
                                : remaining;
            if (load == 0u ||
                !comp_asset_store_read(reader->store,
                                       reader->offset + reader->consumed,
                                       reader->cache,
                                       load)) {
                return false;
            }
            reader->cache_offset = 0u;
            reader->cache_size = (uint16_t)load;
        }
        available = (uint32_t)reader->cache_size - reader->cache_offset;
        chunk = length < available ? length : available;
        memcpy(destination, &reader->cache[reader->cache_offset], chunk);
        destination += chunk;
        reader->cache_offset = (uint16_t)(reader->cache_offset + chunk);
        reader->consumed += chunk;
        length -= chunk;
    }
    return true;
}

static bool packbits_decode_frame(const comp_emote_asset_pack_t *pack,
                                  const comp_emote_frame_t *frame,
                                  uint8_t *destination,
                                  uint32_t output_size)
{
    packbits_reader_t reader;
    uint32_t written = 0u;

    if (pack == NULL || frame == NULL || destination == NULL ||
        frame->data_size == 0u || output_size == 0u) {
        return false;
    }
    reader = (packbits_reader_t){
        .store = pack->store,
        .offset = pack->payload_offset + frame->data_offset,
        .size = frame->data_size,
    };
    while (reader.consumed < reader.size) {
        uint8_t control;
        uint32_t count;

        if (!packbits_reader_read(&reader, &control, 1u)) {
            return false;
        }
        if (control <= 127u) {
            count = (uint32_t)control + 1u;
            if (count > output_size - written ||
                !packbits_reader_read(&reader, &destination[written], count)) {
                return false;
            }
            written += count;
        } else if (control != 128u) {
            uint8_t value;
            count = 257u - control;
            if (count > output_size - written ||
                !packbits_reader_read(&reader, &value, 1u)) {
                return false;
            }
            memset(&destination[written], value, count);
            written += count;
        } else {
            return false;
        }
    }
    return written == output_size;
}

bool comp_emote_asset_pack_read_frame(const comp_emote_asset_pack_t *pack,
                                      const comp_emote_frame_t *frame,
                                      uint8_t *destination,
                                      size_t destination_size)
{
    uint32_t output_size;

    /*
     * The pack is fully validated when it is selected/mounted and when the
     * expression source is initialized. Re-running catalog validation here is
     * quadratic in clip count because it also checks duplicate names; the
     * browser catalog has about 1000 clips, which added roughly one second to
     * every frame. Keep the hot path bounded to the pack and selected frame.
     */
    if (pack == NULL || frame == NULL || destination == NULL ||
        pack->format_version != COMP_EMOTE_ASSET_PACK_FORMAT_VERSION ||
        !comp_screen_asset_profile_validate(&pack->profile) ||
        (pack->frame_encoding != COMP_EMOTE_FRAME_ENCODING_RAW_FULL_FRAME &&
         pack->frame_encoding != COMP_EMOTE_FRAME_ENCODING_PACKBITS) ||
        pack->payload_size == 0u || !pack->has_payload_crc32 ||
        pack->catalog == NULL || pack->catalog->frames == NULL ||
        pack->catalog->frame_count == 0u || pack->store == NULL ||
        !range_is_valid(pack->store->size_bytes,
                        pack->payload_offset,
                        pack->payload_size) ||
        frame < pack->catalog->frames ||
        frame >= pack->catalog->frames + pack->catalog->frame_count ||
        !range_is_valid(pack->payload_size,
                        frame->data_offset,
                        frame->data_size)) {
        return false;
    }
    output_size = frame_output_size(pack);
    if (destination_size < output_size) {
        return false;
    }
    if (pack->override_frame == frame && pack->override_read != NULL) {
        return pack->override_read(pack->override_context,
                                   destination,
                                   destination_size);
    }
    if (pack->override_first_frame != NULL &&
        pack->override_range_read != NULL &&
        frame >= pack->override_first_frame &&
        frame < pack->override_first_frame + pack->override_frame_count) {
        return pack->override_range_read(
            pack->override_range_context,
            (uint16_t)(frame - pack->override_first_frame),
            destination,
            destination_size);
    }
    if (!range_is_valid(pack->payload_size,
                        frame->data_offset, frame->data_size)) {
        return false;
    }
    if (pack->frame_encoding == COMP_EMOTE_FRAME_ENCODING_RAW_FULL_FRAME) {
        return frame->data_size == output_size &&
               comp_asset_store_read(pack->store,
                                     pack->payload_offset + frame->data_offset,
                                     destination,
                                     frame->data_size);
    }
    return packbits_decode_frame(pack, frame, destination, output_size);
}

bool comp_emote_asset_pack_set_frame_override(
    comp_emote_asset_pack_t *pack,
    const comp_emote_frame_t *frame,
    comp_emote_asset_override_read_fn_t read,
    void *context)
{
    if (!comp_emote_asset_pack_validate(pack) || frame == NULL ||
        read == NULL || pack->catalog == NULL ||
        frame < pack->catalog->frames ||
        frame >= pack->catalog->frames + pack->catalog->frame_count) {
        return false;
    }
    pack->override_frame = frame;
    pack->override_read = read;
    pack->override_context = context;
    return true;
}

bool comp_emote_asset_pack_set_frame_override_range(
    comp_emote_asset_pack_t *pack,
    const comp_emote_frame_t *first_frame,
    uint16_t frame_count,
    comp_emote_asset_override_range_read_fn_t read,
    void *context)
{
    if (!comp_emote_asset_pack_validate(pack) || first_frame == NULL ||
        frame_count == 0u || read == NULL || pack->catalog == NULL ||
        first_frame < pack->catalog->frames ||
        first_frame >= pack->catalog->frames + pack->catalog->frame_count ||
        frame_count > (uint16_t)(
            pack->catalog->frames + pack->catalog->frame_count - first_frame)) {
        return false;
    }
    pack->override_first_frame = first_frame;
    pack->override_frame_count = frame_count;
    pack->override_range_read = read;
    pack->override_range_context = context;
    return true;
}

bool comp_emote_asset_pack_verify_payload(const comp_emote_asset_pack_t *pack,
                                          uint8_t *scratch,
                                          size_t scratch_size)
{
    uint32_t offset = 0u;
    uint32_t crc = 0xFFFFFFFFu;

    if (!comp_emote_asset_pack_validate(pack) || scratch == NULL || scratch_size == 0u) {
        return false;
    }
    while (offset < pack->payload_size) {
        size_t chunk = pack->payload_size - offset;
        if (chunk > scratch_size) {
            chunk = scratch_size;
        }
        if (!comp_asset_store_read(pack->store,
                                   pack->payload_offset + offset,
                                   scratch,
                                   chunk)) {
            return false;
        }
        crc = crc32_update(crc, scratch, chunk);
        offset += (uint32_t)chunk;
    }
    return (crc ^ 0xFFFFFFFFu) == pack->payload_crc32;
}

const char *comp_emote_asset_mount_result_name(comp_emote_asset_mount_result_t result)
{
    switch (result) {
    case COMP_EMOTE_ASSET_MOUNT_OK: return "ok";
    case COMP_EMOTE_ASSET_MOUNT_BAD_ARGUMENT: return "bad_argument";
    case COMP_EMOTE_ASSET_MOUNT_IO_ERROR: return "io_error";
    case COMP_EMOTE_ASSET_MOUNT_BAD_MAGIC: return "bad_magic";
    case COMP_EMOTE_ASSET_MOUNT_UNSUPPORTED_VERSION: return "unsupported_version";
    case COMP_EMOTE_ASSET_MOUNT_BAD_LAYOUT: return "bad_layout";
    case COMP_EMOTE_ASSET_MOUNT_PROFILE_MISMATCH: return "profile_mismatch";
    case COMP_EMOTE_ASSET_MOUNT_CAPACITY_EXCEEDED: return "capacity_exceeded";
    case COMP_EMOTE_ASSET_MOUNT_INDEX_CRC_MISMATCH: return "index_crc_mismatch";
    case COMP_EMOTE_ASSET_MOUNT_PAYLOAD_CRC_MISMATCH: return "payload_crc_mismatch";
    case COMP_EMOTE_ASSET_MOUNT_BAD_CATALOG: return "bad_catalog";
    case COMP_EMOTE_ASSET_MOUNT_INACTIVE_BY_POLICY: return "inactive_by_policy";
    case COMP_EMOTE_ASSET_MOUNT_REJECTED_BY_POLICY: return "rejected_by_policy";
    default: return "unknown";
    }
}

static comp_emote_asset_mount_result_t comp_emote_asset_pack_mount_internal(
    comp_emote_asset_mount_t *mount,
    const comp_asset_store_t *store,
    const comp_screen_asset_profile_t *target,
    const comp_emote_clip_t *clips,
    size_t clip_capacity,
    const comp_emote_frame_t *frames,
    size_t frame_capacity,
    const char *strings,
    size_t string_capacity,
    uint8_t *scratch,
    size_t scratch_size,
    bool strings_preloaded,
    bool clips_preloaded,
    bool frames_preloaded)
{
    uint8_t header[COMP_EMOTE_ASSET_PACK_HEADER_BYTES];
    uint8_t entry[COMP_EMOTE_ASSET_PACK_FRAME_ENTRY_BYTES];
    comp_screen_asset_profile_t profile;
    uint16_t version;
    uint16_t header_size;
    uint16_t clip_count;
    uint16_t frame_count;
    uint32_t total_size;
    uint32_t clip_offset;
    uint32_t frame_offset;
    uint32_t string_offset;
    uint32_t string_size;
    uint32_t payload_offset;
    uint32_t payload_size;
    uint32_t expected_clip_offset;
    uint32_t expected_frame_offset;
    uint32_t expected_string_offset;
    uint32_t expected_payload_offset;
    uint32_t pack_name_offset;

    if (mount == NULL || store == NULL || target == NULL || clips == NULL ||
        frames == NULL || strings == NULL || scratch == NULL || scratch_size == 0u ||
        !comp_screen_asset_profile_validate(target)) {
        return COMP_EMOTE_ASSET_MOUNT_BAD_ARGUMENT;
    }
    memset(mount, 0, sizeof(*mount));
    if (!comp_asset_store_read(store, 0u, header, sizeof(header))) {
        return COMP_EMOTE_ASSET_MOUNT_IO_ERROR;
    }
    if (header[HEADER_MAGIC] != PACK_MAGIC_0 || header[HEADER_MAGIC + 1u] != PACK_MAGIC_1 ||
        header[HEADER_MAGIC + 2u] != PACK_MAGIC_2 || header[HEADER_MAGIC + 3u] != PACK_MAGIC_3) {
        return COMP_EMOTE_ASSET_MOUNT_BAD_MAGIC;
    }
    version = read_le16(&header[HEADER_VERSION]);
    if (version != COMP_EMOTE_ASSET_PACK_FORMAT_VERSION) {
        return COMP_EMOTE_ASSET_MOUNT_UNSUPPORTED_VERSION;
    }

    header_size = read_le16(&header[HEADER_SIZE]);
    total_size = read_le32(&header[HEADER_TOTAL_SIZE]);
    clip_count = read_le16(&header[HEADER_CLIP_COUNT]);
    frame_count = read_le16(&header[HEADER_FRAME_COUNT]);
    clip_offset = read_le32(&header[HEADER_CLIP_TABLE]);
    frame_offset = read_le32(&header[HEADER_FRAME_TABLE]);
    string_offset = read_le32(&header[HEADER_STRING_TABLE]);
    string_size = read_le32(&header[HEADER_STRING_SIZE]);
    payload_offset = read_le32(&header[HEADER_PAYLOAD]);
    payload_size = read_le32(&header[HEADER_PAYLOAD_SIZE]);
    pack_name_offset = read_le32(&header[HEADER_PACK_NAME]);

    expected_clip_offset = COMP_EMOTE_ASSET_PACK_HEADER_BYTES;
    expected_frame_offset = expected_clip_offset +
                            (uint32_t)clip_count * COMP_EMOTE_ASSET_PACK_CLIP_ENTRY_BYTES;
    expected_string_offset = expected_frame_offset +
                             (uint32_t)frame_count * COMP_EMOTE_ASSET_PACK_FRAME_ENTRY_BYTES;
    if (string_size > UINT32_MAX - expected_string_offset) {
        return COMP_EMOTE_ASSET_MOUNT_BAD_LAYOUT;
    }
    expected_payload_offset = expected_string_offset + string_size;
    if (payload_size > UINT32_MAX - payload_offset) {
        return COMP_EMOTE_ASSET_MOUNT_BAD_LAYOUT;
    }
    if (header_size != COMP_EMOTE_ASSET_PACK_HEADER_BYTES || clip_count == 0u ||
        frame_count == 0u || string_size == 0u || payload_size == 0u ||
        clip_offset != expected_clip_offset || frame_offset != expected_frame_offset ||
        string_offset != expected_string_offset || payload_offset != expected_payload_offset ||
        total_size != payload_offset + payload_size || total_size > store->size_bytes) {
        return COMP_EMOTE_ASSET_MOUNT_BAD_LAYOUT;
    }
    if (clip_count > clip_capacity || frame_count > frame_capacity ||
        string_size > string_capacity ||
        (strings_preloaded && string_size != string_capacity)) {
        return COMP_EMOTE_ASSET_MOUNT_CAPACITY_EXCEEDED;
    }

    profile = (comp_screen_asset_profile_t){
        .width = read_le16(&header[HEADER_WIDTH]),
        .height = read_le16(&header[HEADER_HEIGHT]),
        .stride_bytes = read_le16(&header[HEADER_STRIDE]),
        .pixel_format = (comp_screen_pixel_format_t)header[HEADER_PIXEL_FORMAT],
    };
    if (!comp_screen_asset_profile_matches(&profile, target)) {
        return COMP_EMOTE_ASSET_MOUNT_PROFILE_MISMATCH;
    }
    if (!verify_store_crc(store,
                          clip_offset,
                          payload_offset - clip_offset,
                          read_le32(&header[HEADER_INDEX_CRC32]),
                          scratch,
                          scratch_size)) {
        return COMP_EMOTE_ASSET_MOUNT_INDEX_CRC_MISMATCH;
    }
    if (strings_preloaded) {
        if (!verify_store_bytes(store,
                                string_offset,
                                (const uint8_t *)strings,
                                string_size,
                                scratch,
                                scratch_size)) {
            return COMP_EMOTE_ASSET_MOUNT_INDEX_CRC_MISMATCH;
        }
    } else if (!comp_asset_store_read(store,
                                      string_offset,
                                      (uint8_t *)(uintptr_t)strings,
                                      string_size)) {
        return COMP_EMOTE_ASSET_MOUNT_IO_ERROR;
    }
    if (!string_is_valid(strings, string_size, pack_name_offset)) {
        return COMP_EMOTE_ASSET_MOUNT_BAD_CATALOG;
    }

    for (uint16_t index = 0u; index < clip_count; ++index) {
        uint32_t offset = clip_offset +
                          (uint32_t)index * COMP_EMOTE_ASSET_PACK_CLIP_ENTRY_BYTES;
        if (!comp_asset_store_read(store, offset, entry,
                                   COMP_EMOTE_ASSET_PACK_CLIP_ENTRY_BYTES)) {
            return COMP_EMOTE_ASSET_MOUNT_IO_ERROR;
        }
        uint32_t name_offset = read_le32(&entry[0]);
        if (!string_is_valid(strings, string_size, name_offset)) {
            return COMP_EMOTE_ASSET_MOUNT_BAD_CATALOG;
        }
        const comp_emote_clip_t decoded = {
            .name = &strings[name_offset],
            .first_frame = read_le16(&entry[4]),
            .frame_count = read_le16(&entry[6]),
            .loop_start = read_le16(&entry[8]),
            .loop_end = read_le16(&entry[10]),
        };
        if (clips_preloaded) {
            const comp_emote_clip_t *expected = &clips[index];
            if (expected->name == NULL ||
                strcmp(expected->name, decoded.name) != 0 ||
                expected->first_frame != decoded.first_frame ||
                expected->frame_count != decoded.frame_count ||
                expected->loop_start != decoded.loop_start ||
                expected->loop_end != decoded.loop_end) {
                return COMP_EMOTE_ASSET_MOUNT_BAD_CATALOG;
            }
        } else {
            ((comp_emote_clip_t *)(uintptr_t)clips)[index] = decoded;
        }
    }
    for (uint16_t index = 0u; index < frame_count; ++index) {
        uint32_t offset = frame_offset +
                          (uint32_t)index * COMP_EMOTE_ASSET_PACK_FRAME_ENTRY_BYTES;
        if (!comp_asset_store_read(store, offset, entry, sizeof(entry))) {
            return COMP_EMOTE_ASSET_MOUNT_IO_ERROR;
        }
        const uint32_t data_size = read_le32(&entry[4]);
        if (data_size > UINT16_MAX) {
            return COMP_EMOTE_ASSET_MOUNT_BAD_CATALOG;
        }
        const comp_emote_frame_t decoded = {
            .data_offset = read_le32(&entry[0]),
            .data_size = (uint16_t)data_size,
            .duration_ms = read_le16(&entry[8]),
            .dirty_x = read_le16(&entry[10]),
            .dirty_y = read_le16(&entry[12]),
            .dirty_width = read_le16(&entry[14]),
            .dirty_height = read_le16(&entry[16]),
        };
        if (frames_preloaded) {
            const comp_emote_frame_t *expected = &frames[index];
            if (expected->data_offset != decoded.data_offset ||
                expected->data_size != decoded.data_size ||
                expected->duration_ms != decoded.duration_ms ||
                expected->dirty_x != decoded.dirty_x ||
                expected->dirty_y != decoded.dirty_y ||
                expected->dirty_width != decoded.dirty_width ||
                expected->dirty_height != decoded.dirty_height) {
                return COMP_EMOTE_ASSET_MOUNT_BAD_CATALOG;
            }
        } else {
            ((comp_emote_frame_t *)(uintptr_t)frames)[index] = decoded;
        }
    }

    mount->catalog = (comp_emote_catalog_t){
        .clips = clips,
        .clip_count = clip_count,
        .frames = frames,
        .frame_count = frame_count,
    };
    mount->pack = (comp_emote_asset_pack_t){
        .name = &strings[pack_name_offset],
        .format_version = version,
        .priority = read_le16(&header[HEADER_PRIORITY]),
        .revision = read_le32(&header[HEADER_REVISION]),
        .profile = profile,
        .frame_encoding = (comp_emote_frame_encoding_t)header[HEADER_FRAME_ENCODING],
        .payload_offset = payload_offset,
        .payload_size = payload_size,
        .payload_crc32 = read_le32(&header[HEADER_PAYLOAD_CRC32]),
        .has_payload_crc32 = true,
        .catalog = &mount->catalog,
        .store = store,
    };
    if (!comp_emote_asset_pack_validate(&mount->pack)) {
        memset(mount, 0, sizeof(*mount));
        return COMP_EMOTE_ASSET_MOUNT_BAD_CATALOG;
    }
    if (!comp_emote_asset_pack_verify_payload(&mount->pack, scratch, scratch_size)) {
        memset(mount, 0, sizeof(*mount));
        return COMP_EMOTE_ASSET_MOUNT_PAYLOAD_CRC_MISMATCH;
    }
    return COMP_EMOTE_ASSET_MOUNT_OK;
}

comp_emote_asset_mount_result_t comp_emote_asset_pack_mount(
    comp_emote_asset_mount_t *mount,
    const comp_asset_store_t *store,
    const comp_screen_asset_profile_t *target,
    comp_emote_clip_t *clips,
    size_t clip_capacity,
    comp_emote_frame_t *frames,
    size_t frame_capacity,
    char *strings,
    size_t string_capacity,
    uint8_t *scratch,
    size_t scratch_size)
{
    return comp_emote_asset_pack_mount_internal(
        mount, store, target, clips, clip_capacity, frames, frame_capacity,
        strings, string_capacity, scratch, scratch_size, false, false, false);
}

comp_emote_asset_mount_result_t comp_emote_asset_pack_mount_preloaded_strings(
    comp_emote_asset_mount_t *mount,
    const comp_asset_store_t *store,
    const comp_screen_asset_profile_t *target,
    comp_emote_clip_t *clips,
    size_t clip_capacity,
    comp_emote_frame_t *frames,
    size_t frame_capacity,
    const char *strings,
    size_t string_size,
    uint8_t *scratch,
    size_t scratch_size)
{
    return comp_emote_asset_pack_mount_internal(
        mount, store, target, clips, clip_capacity, frames, frame_capacity,
        strings, string_size, scratch, scratch_size, true, false, false);
}

comp_emote_asset_mount_result_t comp_emote_asset_pack_mount_preloaded_index(
    comp_emote_asset_mount_t *mount,
    const comp_asset_store_t *store,
    const comp_screen_asset_profile_t *target,
    const comp_emote_clip_t *clips,
    size_t clip_capacity,
    comp_emote_frame_t *frames,
    size_t frame_capacity,
    const char *strings,
    size_t string_size,
    uint8_t *scratch,
    size_t scratch_size)
{
    return comp_emote_asset_pack_mount_internal(
        mount, store, target, clips, clip_capacity, frames, frame_capacity,
        strings, string_size, scratch, scratch_size, true, true, false);
}

comp_emote_asset_mount_result_t comp_emote_asset_pack_mount_preloaded_catalog(
    comp_emote_asset_mount_t *mount,
    const comp_asset_store_t *store,
    const comp_screen_asset_profile_t *target,
    const comp_emote_clip_t *clips,
    size_t clip_capacity,
    const comp_emote_frame_t *frames,
    size_t frame_capacity,
    const char *strings,
    size_t string_size,
    uint8_t *scratch,
    size_t scratch_size)
{
    return comp_emote_asset_pack_mount_internal(
        mount, store, target, clips, clip_capacity, frames, frame_capacity,
        strings, string_size, scratch, scratch_size, true, true, true);
}

bool comp_emote_asset_pack_self_test(void)
{
    static const uint8_t bytes[] = {0xAAu, 0xFEu, 0x11u, 0x00u, 0x22u};
    static const uint8_t expected_output[] = {0x11u, 0x11u, 0x11u, 0x22u};
    static const comp_emote_frame_t frames[] = {
        {.data_offset = 0u, .data_size = 4u, .duration_ms = 250u,
         .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
    };
    static const comp_emote_clip_t clips[] = {
        {.name = "future", .first_frame = 0u, .frame_count = 1u},
    };
    static const comp_emote_catalog_t catalog = {
        .clips = clips, .clip_count = 1u, .frames = frames, .frame_count = 1u,
    };
    comp_asset_store_t store;
    comp_emote_asset_pack_t packs[2];
    comp_screen_asset_profile_t target = {
        .width = 32u,
        .height = 1u,
        .stride_bytes = 4u,
        .pixel_format = COMP_SCREEN_PIXEL_FORMAT_MONO_1BPP_WHITE_IS_ONE_MSB,
    };
    uint8_t output[4] = {0u};
    uint8_t scratch[3];
    uint32_t encoded_crc = crc32_update(0xFFFFFFFFu, &bytes[1], 4u) ^ 0xFFFFFFFFu;

    if (!comp_asset_store_init_memory(&store,
                                      COMP_ASSET_STORAGE_EXTERNAL_NOR,
                                      bytes,
                                      sizeof(bytes))) {
        return false;
    }
    packs[0] = (comp_emote_asset_pack_t){
        .name = "future-low",
        .format_version = COMP_EMOTE_ASSET_PACK_FORMAT_VERSION,
        .priority = 1u,
        .revision = 1u,
        .profile = target,
        .frame_encoding = COMP_EMOTE_FRAME_ENCODING_PACKBITS,
        .payload_offset = 1u,
        .payload_size = 4u,
        .payload_crc32 = encoded_crc,
        .has_payload_crc32 = true,
        .catalog = &catalog,
        .store = &store,
    };
    packs[1] = packs[0];
    packs[1].name = "future-new";
    packs[1].revision = 2u;

    const comp_emote_asset_pack_t *selected =
        comp_emote_asset_pack_select(packs, 2u, &target);
    if (selected != &packs[1] ||
        !comp_emote_asset_pack_read_frame(selected, &frames[0], output, sizeof(output)) ||
        memcmp(output, expected_output, sizeof(output)) != 0 ||
        !comp_emote_asset_pack_verify_payload(selected, scratch, sizeof(scratch))) {
        return false;
    }
    target.width = 200u;
    if (comp_emote_asset_pack_select(packs, 2u, &target) != NULL) {
        return false;
    }

    enum { TEST_PACK_SIZE = COMP_EMOTE_ASSET_PACK_HEADER_BYTES +
                            COMP_EMOTE_ASSET_PACK_CLIP_ENTRY_BYTES +
                            COMP_EMOTE_ASSET_PACK_FRAME_ENTRY_BYTES + 12u + 4u };
    uint8_t binary[TEST_PACK_SIZE];
    memset(binary, 0, sizeof(binary));
    binary[0] = PACK_MAGIC_0;
    binary[1] = PACK_MAGIC_1;
    binary[2] = PACK_MAGIC_2;
    binary[3] = PACK_MAGIC_3;
    write_le16(&binary[HEADER_VERSION], COMP_EMOTE_ASSET_PACK_FORMAT_VERSION);
    write_le16(&binary[HEADER_SIZE], COMP_EMOTE_ASSET_PACK_HEADER_BYTES);
    write_le32(&binary[HEADER_TOTAL_SIZE], sizeof(binary));
    write_le32(&binary[HEADER_REVISION], 7u);
    write_le16(&binary[HEADER_PRIORITY], 3u);
    write_le16(&binary[HEADER_WIDTH], 32u);
    write_le16(&binary[HEADER_HEIGHT], 1u);
    write_le16(&binary[HEADER_STRIDE], 4u);
    binary[HEADER_PIXEL_FORMAT] = COMP_SCREEN_PIXEL_FORMAT_MONO_1BPP_WHITE_IS_ONE_MSB;
    binary[HEADER_FRAME_ENCODING] = COMP_EMOTE_FRAME_ENCODING_PACKBITS;
    write_le16(&binary[HEADER_CLIP_COUNT], 1u);
    write_le16(&binary[HEADER_FRAME_COUNT], 1u);
    uint32_t test_clip_offset = COMP_EMOTE_ASSET_PACK_HEADER_BYTES;
    uint32_t test_frame_offset = test_clip_offset + COMP_EMOTE_ASSET_PACK_CLIP_ENTRY_BYTES;
    uint32_t test_string_offset = test_frame_offset + COMP_EMOTE_ASSET_PACK_FRAME_ENTRY_BYTES;
    uint32_t test_payload_offset = test_string_offset + 12u;
    write_le32(&binary[HEADER_CLIP_TABLE], test_clip_offset);
    write_le32(&binary[HEADER_FRAME_TABLE], test_frame_offset);
    write_le32(&binary[HEADER_STRING_TABLE], test_string_offset);
    write_le32(&binary[HEADER_STRING_SIZE], 12u);
    write_le32(&binary[HEADER_PAYLOAD], test_payload_offset);
    write_le32(&binary[HEADER_PAYLOAD_SIZE], 4u);
    write_le32(&binary[HEADER_PACK_NAME], 0u);
    write_le32(&binary[test_clip_offset], 5u);
    write_le16(&binary[test_clip_offset + 4u], 0u);
    write_le16(&binary[test_clip_offset + 6u], 1u);
    write_le32(&binary[test_frame_offset], 0u);
    write_le32(&binary[test_frame_offset + 4u], 4u);
    write_le16(&binary[test_frame_offset + 8u], 250u);
    write_le16(&binary[test_frame_offset + 10u], 0u);
    write_le16(&binary[test_frame_offset + 12u], 0u);
    write_le16(&binary[test_frame_offset + 14u], 0u);
    write_le16(&binary[test_frame_offset + 16u], 0u);
    memcpy(&binary[test_string_offset], "pack\0face\0\0", 12u);
    memcpy(&binary[test_payload_offset], &bytes[1], 4u);
    uint32_t index_crc = crc32_update(0xFFFFFFFFu,
                                      &binary[test_clip_offset],
                                      test_payload_offset - test_clip_offset) ^ 0xFFFFFFFFu;
    write_le32(&binary[HEADER_INDEX_CRC32], index_crc);
    write_le32(&binary[HEADER_PAYLOAD_CRC32], encoded_crc);

    comp_asset_store_t binary_store;
    comp_emote_asset_mount_t mounted;
    comp_emote_clip_t mounted_clips[1];
    comp_emote_frame_t mounted_frames[1];
    char mounted_strings[12];
    static const char preloaded_strings[12] = "pack\0face\0\0";
    static const comp_emote_clip_t preloaded_clips[1] = {
        {.name = "face", .first_frame = 0u, .frame_count = 1u},
    };
    static const comp_emote_frame_t preloaded_frames[1] = {
        {.data_offset = 0u, .data_size = 4u, .duration_ms = 250u,
         .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
    };
    comp_emote_frame_t mismatched_frame = preloaded_frames[0];
    target.width = 32u;
    if (!comp_asset_store_init_memory(&binary_store,
                                      COMP_ASSET_STORAGE_EXTERNAL_NOR,
                                      binary,
                                      sizeof(binary)) ||
        comp_emote_asset_pack_mount(&mounted,
                                    &binary_store,
                                    &target,
                                    mounted_clips,
                                    1u,
                                    mounted_frames,
                                    1u,
                                    mounted_strings,
                                    sizeof(mounted_strings),
                                    scratch,
                                    sizeof(scratch)) != COMP_EMOTE_ASSET_MOUNT_OK ||
        strcmp(mounted.pack.name, "pack") != 0 ||
        strcmp(mounted.catalog.clips[0].name, "face") != 0 ||
        !comp_emote_asset_pack_read_frame(&mounted.pack,
                                          &mounted.catalog.frames[0],
                                          output,
                                          sizeof(output)) ||
        memcmp(output, expected_output, sizeof(output)) != 0) {
        return false;
    }
    if (comp_emote_asset_pack_mount_preloaded_catalog(
            &mounted,
            &binary_store,
            &target,
            preloaded_clips,
            1u,
            preloaded_frames,
            1u,
            preloaded_strings,
            sizeof(preloaded_strings),
            scratch,
            sizeof(scratch)) != COMP_EMOTE_ASSET_MOUNT_OK) {
        return false;
    }
    mismatched_frame.duration_ms++;
    if (comp_emote_asset_pack_mount_preloaded_catalog(
            &mounted,
            &binary_store,
            &target,
            preloaded_clips,
            1u,
            &mismatched_frame,
            1u,
            preloaded_strings,
            sizeof(preloaded_strings),
            scratch,
            sizeof(scratch)) != COMP_EMOTE_ASSET_MOUNT_BAD_CATALOG) {
        return false;
    }
    return true;
}
