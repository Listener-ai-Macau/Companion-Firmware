#include "asset_store.h"
#include "ui_asset_generation.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum {
    FLASH_BYTES = 0x00200000u,
    BASE_PACK_BYTES = 0x00130000u,
    RAW_FRAME_BYTES = 5000u,
};

typedef struct {
    uint8_t *bytes;
    uint32_t erase_count;
    uint32_t write_bytes;
    bool fail_root_write;
} fake_flash_t;

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
    if (offset > FLASH_BYTES || length > FLASH_BYTES - offset ||
        (flash->fail_root_write &&
         (offset == COMP_UI_ASSET_GENERATION_ROOT_A_OFFSET ||
          offset == COMP_UI_ASSET_GENERATION_ROOT_B_OFFSET))) {
        return false;
    }
    for (size_t index = 0u; index < length; ++index) {
        flash->bytes[offset + index] &= data[index];
    }
    flash->write_bytes += (uint32_t)length;
    return true;
}

static void require_true(bool value, const char *message)
{
    if (!value) {
        fprintf(stderr, "FAIL: %s\n", message);
        exit(1);
    }
}

static uint32_t build_blob(uint8_t *blob,
                           uint32_t blob_offset,
                           uint8_t frame_fill,
                           uint32_t state_hash)
{
    const uint32_t manifest_size =
        COMP_UI_ASSET_MANIFEST_HEADER_BYTES +
        COMP_UI_ASSET_MANIFEST_ENTRY_BYTES;
    uint8_t *encoded = blob + manifest_size;
    uint32_t encoded_size = 0u;
    uint32_t remaining = RAW_FRAME_BYTES;
    while (remaining > 0u) {
        uint32_t count = remaining > 128u ? 128u : remaining;
        encoded[encoded_size++] = (uint8_t)(257u - count);
        encoded[encoded_size++] = frame_fill;
        remaining -= count;
    }
    const uint32_t blob_size = manifest_size + encoded_size;
    memset(blob, 0, blob_size);
    memcpy(blob, "CUIM", 4u);
    write_le16(blob + 4u, COMP_UI_ASSET_GENERATION_FORMAT_VERSION);
    write_le16(blob + 6u, COMP_UI_ASSET_MANIFEST_HEADER_BYTES);
    write_le16(blob + 8u, 1u);
    write_le16(blob + 10u, COMP_UI_ASSET_MANIFEST_ENTRY_BYTES);
    write_le32(blob + 12u, manifest_size);
    uint8_t *entry = blob + COMP_UI_ASSET_MANIFEST_HEADER_BYTES;
    write_le32(entry + 0u, state_hash);
    write_le16(entry + 4u, UINT16_MAX);
    write_le16(entry + 6u, COMP_UI_ASSET_ENTRY_OVERRIDE_PACKBITS_1BPP);
    remaining = RAW_FRAME_BYTES;
    encoded_size = 0u;
    while (remaining > 0u) {
        uint32_t count = remaining > 128u ? 128u : remaining;
        encoded[encoded_size++] = (uint8_t)(257u - count);
        encoded[encoded_size++] = frame_fill;
        remaining -= count;
    }
    uint8_t raw[RAW_FRAME_BYTES];
    memset(raw, frame_fill, sizeof(raw));
    write_le32(entry + 8u, crc32_bytes(raw, sizeof(raw)));
    write_le32(entry + 12u, blob_offset + manifest_size);
    write_le16(entry + 16u, (uint16_t)encoded_size);
    write_le16(entry + 18u, 500u);
    write_le32(entry + 20u, crc32_bytes(encoded, encoded_size));
    return blob_size;
}

static uint32_t build_xor_blob(uint8_t *blob,
                               uint32_t blob_offset,
                               uint32_t state_hash)
{
    const uint32_t manifest_size =
        COMP_UI_ASSET_MANIFEST_HEADER_BYTES +
        COMP_UI_ASSET_MANIFEST_ENTRY_BYTES;
    uint8_t *encoded = blob + manifest_size;
    uint8_t expected[RAW_FRAME_BYTES];
    uint32_t encoded_size = 0u;
    memset(expected, 0x55, sizeof(expected));

    write_le16(encoded + encoded_size, 12u);
    encoded[encoded_size + 2u] = 3u;
    encoded[encoded_size + 3u] = 0x01u;
    encoded[encoded_size + 4u] = 0x02u;
    encoded[encoded_size + 5u] = 0x04u;
    encoded_size += 6u;
    expected[12] ^= 0x01u;
    expected[13] ^= 0x02u;
    expected[14] ^= 0x04u;

    write_le16(encoded + encoded_size, 4998u);
    encoded[encoded_size + 2u] = 2u;
    encoded[encoded_size + 3u] = 0x80u;
    encoded[encoded_size + 4u] = 0x40u;
    encoded_size += 5u;
    expected[4998] ^= 0x80u;
    expected[4999] ^= 0x40u;

    memset(blob, 0, manifest_size);
    memcpy(blob, "CUIM", 4u);
    write_le16(blob + 4u, COMP_UI_ASSET_GENERATION_FORMAT_VERSION);
    write_le16(blob + 6u, COMP_UI_ASSET_MANIFEST_HEADER_BYTES);
    write_le16(blob + 8u, 1u);
    write_le16(blob + 10u, COMP_UI_ASSET_MANIFEST_ENTRY_BYTES);
    write_le32(blob + 12u, manifest_size);
    uint8_t *entry = blob + COMP_UI_ASSET_MANIFEST_HEADER_BYTES;
    write_le32(entry + 0u, state_hash);
    write_le16(entry + 4u, 7u);
    write_le16(entry + 6u, COMP_UI_ASSET_ENTRY_XOR_PATCH_1BPP);
    write_le32(entry + 8u, crc32_bytes(expected, sizeof(expected)));
    write_le32(entry + 12u, blob_offset + manifest_size);
    write_le16(entry + 16u, (uint16_t)encoded_size);
    write_le16(entry + 18u, 500u);
    write_le32(entry + 20u, crc32_bytes(encoded, encoded_size));
    return manifest_size + encoded_size;
}

int main(void)
{
    fake_flash_t flash = {0};
    comp_ui_asset_generation_io_t io;
    comp_asset_store_t store;
    comp_ui_asset_generation_t mounted = {0};
    comp_ui_asset_generation_entry_t entry;
    uint8_t *blob = malloc(
        COMP_UI_ASSET_MANIFEST_HEADER_BYTES +
        COMP_UI_ASSET_MANIFEST_ENTRY_BYTES + RAW_FRAME_BYTES);
    uint8_t *frame = malloc(RAW_FRAME_BYTES);
    uint8_t id1[COMP_UI_ASSET_GENERATION_ID_BYTES] = {1u};
    uint8_t id2[COMP_UI_ASSET_GENERATION_ID_BYTES] = {2u};
    uint8_t id3[COMP_UI_ASSET_GENERATION_ID_BYTES] = {3u};
    uint8_t id4[COMP_UI_ASSET_GENERATION_ID_BYTES] = {4u};
    const uint32_t state_hash = comp_ui_asset_state_hash("expression_calm");

    flash.bytes = malloc(FLASH_BYTES);
    require_true(flash.bytes != NULL && blob != NULL && frame != NULL,
                 "allocate fake flash");
    memset(flash.bytes, 0xFF, FLASH_BYTES);
    io = (comp_ui_asset_generation_io_t){
        .read = fake_read,
        .erase_4k = fake_erase,
        .write = fake_write,
        .context = &flash,
        .partition_size = FLASH_BYTES,
    };

    uint32_t blob_size = build_blob(blob, BASE_PACK_BYTES, 0xA5u, state_hash);
    comp_ui_asset_install_receipt_t first =
        comp_ui_asset_generation_install(
            &io, BASE_PACK_BYTES, 0u, id1, blob, blob_size,
            0u, COMP_UI_ASSET_MANIFEST_HEADER_BYTES +
                    COMP_UI_ASSET_MANIFEST_ENTRY_BYTES);
    require_true(first.result == COMP_UI_ASSET_INSTALL_OK &&
                     first.active_generation == 1u &&
                     first.blob_bytes_written == blob_size &&
                     first.root_bytes_written ==
                         COMP_UI_ASSET_GENERATION_ROOT_BYTES,
                 "first generation commits");
    require_true(comp_asset_store_init_reader(
                     &store, COMP_ASSET_STORAGE_EXTERNAL_NOR,
                     FLASH_BYTES, fake_read, &flash) &&
                     comp_ui_asset_generation_mount(&mounted, &store) &&
                     mounted.root.generation == 1u &&
                     comp_ui_asset_generation_find(
                         &mounted, state_hash, &entry) &&
                     comp_ui_asset_generation_read_override(
                         &mounted, &entry, frame, RAW_FRAME_BYTES) &&
                     frame[0] == 0xA5u &&
                     frame[RAW_FRAME_BYTES - 1u] == 0xA5u,
                 "mounted generation returns exact raw frame");

    uint32_t writes_before_noop = flash.write_bytes;
    uint32_t erases_before_noop = flash.erase_count;
    comp_ui_asset_install_receipt_t noop =
        comp_ui_asset_generation_install(
            &io, BASE_PACK_BYTES, 1u, id1, blob, blob_size,
            0u, COMP_UI_ASSET_MANIFEST_HEADER_BYTES +
                    COMP_UI_ASSET_MANIFEST_ENTRY_BYTES);
    require_true(noop.result == COMP_UI_ASSET_INSTALL_ALREADY_CURRENT &&
                     noop.blob_bytes_written == 0u &&
                     noop.root_bytes_written == 0u &&
                     flash.write_bytes == writes_before_noop &&
                     flash.erase_count == erases_before_noop,
                 "same resource performs zero writes and zero erases");

    uint32_t second_blob_offset =
        (first.blob_offset + blob_size +
         COMP_UI_ASSET_GENERATION_SECTOR_BYTES - 1u) &
        ~(COMP_UI_ASSET_GENERATION_SECTOR_BYTES - 1u);
    blob_size = build_blob(blob, second_blob_offset, 0x3Cu, state_hash);
    flash.fail_root_write = true;
    comp_ui_asset_install_receipt_t interrupted =
        comp_ui_asset_generation_install(
            &io, BASE_PACK_BYTES, 1u, id2, blob, blob_size,
            0u, COMP_UI_ASSET_MANIFEST_HEADER_BYTES +
                    COMP_UI_ASSET_MANIFEST_ENTRY_BYTES);
    require_true(
        interrupted.result == COMP_UI_ASSET_INSTALL_ROOT_COMMIT_FAILED &&
            comp_ui_asset_generation_mount(&mounted, &store) &&
            mounted.root.generation == 1u &&
            comp_ui_asset_generation_find(&mounted, state_hash, &entry) &&
            comp_ui_asset_generation_read_override(
                &mounted, &entry, frame, RAW_FRAME_BYTES) &&
            frame[0] == 0xA5u,
        "failed root commit preserves previous generation");

    flash.fail_root_write = false;
    comp_ui_asset_generation_transaction_t transaction = {0};
    const uint32_t manifest_size =
        COMP_UI_ASSET_MANIFEST_HEADER_BYTES +
        COMP_UI_ASSET_MANIFEST_ENTRY_BYTES;
    comp_ui_asset_install_receipt_t begin =
        comp_ui_asset_generation_begin(
            &transaction, &io, BASE_PACK_BYTES, 1u, id2,
            blob_size, crc32_bytes(blob, blob_size),
            0u, manifest_size, crc32_bytes(blob, manifest_size));
    require_true(begin.result == COMP_UI_ASSET_INSTALL_OK,
                 "streaming generation begins");
    uint32_t streamed = 0u;
    while (streamed < blob_size) {
        uint32_t chunk = blob_size - streamed;
        if (chunk > 37u) {
            chunk = 37u;
        }
        require_true(comp_ui_asset_generation_write(
                         &transaction, blob + streamed, chunk),
                     "streaming chunk writes");
        streamed += chunk;
    }
    comp_ui_asset_install_receipt_t second =
        comp_ui_asset_generation_finish(&transaction);
    require_true(second.result == COMP_UI_ASSET_INSTALL_OK &&
                     second.active_generation == 2u &&
                     second.blob_offset > first.blob_offset &&
                     comp_ui_asset_generation_mount(&mounted, &store) &&
                     mounted.root.generation == 2u &&
                     comp_ui_asset_generation_find(
                         &mounted, state_hash, &entry) &&
                     comp_ui_asset_generation_read_override(
                         &mounted, &entry, frame, RAW_FRAME_BYTES) &&
                     frame[0] == 0x3Cu,
                 "second generation activates only after root commit");

    flash.bytes[second.blob_offset] ^= 0x01u;
    require_true(comp_ui_asset_generation_mount(&mounted, &store) &&
                     mounted.root.generation == 1u,
                 "corrupt newer blob falls back to older valid root");
    flash.bytes[second.blob_offset] ^= 0x01u;
    require_true(comp_ui_asset_generation_mount(&mounted, &store) &&
                     mounted.root.generation == 2u,
                 "restored newer blob mounts");

    uint32_t third_blob_offset =
        (second.blob_offset + blob_size +
         COMP_UI_ASSET_GENERATION_SECTOR_BYTES - 1u) &
        ~(COMP_UI_ASSET_GENERATION_SECTOR_BYTES - 1u);
    blob_size = build_blob(blob, third_blob_offset, 0x7Eu, state_hash);
    comp_ui_asset_generation_transaction_t corrupt_transaction = {0};
    comp_ui_asset_install_receipt_t corrupt_begin =
        comp_ui_asset_generation_begin(
            &corrupt_transaction, &io, BASE_PACK_BYTES, 2u, id3,
            blob_size, crc32_bytes(blob, blob_size) ^ 0x00000001u,
            0u, manifest_size, crc32_bytes(blob, manifest_size));
    require_true(
        corrupt_begin.result == COMP_UI_ASSET_INSTALL_OK &&
            comp_ui_asset_generation_write(
                &corrupt_transaction, blob, blob_size),
        "CRC fault transaction receives the complete blob");
    comp_ui_asset_install_receipt_t corrupt_finish =
        comp_ui_asset_generation_finish(&corrupt_transaction);
    require_true(
        corrupt_finish.result == COMP_UI_ASSET_INSTALL_VERIFY_FAILED &&
            comp_ui_asset_generation_mount(&mounted, &store) &&
            mounted.root.generation == 2u &&
            comp_ui_asset_generation_find(&mounted, state_hash, &entry) &&
            comp_ui_asset_generation_read_override(
                &mounted, &entry, frame, RAW_FRAME_BYTES) &&
            frame[0] == 0x3Cu,
        "CRC mismatch rejects activation and preserves generation two");

    blob_size = build_xor_blob(blob, third_blob_offset, state_hash);
    comp_ui_asset_install_receipt_t patched =
        comp_ui_asset_generation_install(
            &io, BASE_PACK_BYTES, 2u, id3, blob, blob_size,
            0u, manifest_size);
    require_true(
        patched.result == COMP_UI_ASSET_INSTALL_OK &&
            patched.active_generation == 3u &&
            comp_ui_asset_generation_mount(&mounted, &store) &&
            comp_ui_asset_generation_find(&mounted, state_hash, &entry),
        "XOR patch generation mounts");
    memset(frame, 0x55, RAW_FRAME_BYTES);
    require_true(
        comp_ui_asset_generation_read_override(
            &mounted, &entry, frame, RAW_FRAME_BYTES) &&
            frame[12] == 0x54u && frame[13] == 0x57u &&
            frame[14] == 0x51u && frame[4998] == 0xD5u &&
            frame[4999] == 0x15u,
        "XOR patch composes exact final frame");
    flash.bytes[entry.payload_offset + 3u] ^= 0x01u;
    memset(frame, 0x55, RAW_FRAME_BYTES);
    require_true(
        !comp_ui_asset_generation_read_override(
            &mounted, &entry, frame, RAW_FRAME_BYTES),
        "corrupt XOR patch is rejected by payload or final CRC");
    flash.bytes[entry.payload_offset + 3u] ^= 0x01u;

    write_le16(blob + COMP_UI_ASSET_MANIFEST_HEADER_BYTES + 6u,
               COMP_UI_ASSET_ENTRY_OVERRIDE_RAW_1BPP |
                   COMP_UI_ASSET_ENTRY_OVERRIDE_PACKBITS_1BPP);
    comp_ui_asset_install_receipt_t malformed =
        comp_ui_asset_generation_install(
            &io, BASE_PACK_BYTES, 3u, id4, blob, blob_size,
            0u, manifest_size);
    require_true(malformed.result == COMP_UI_ASSET_INSTALL_BAD_LAYOUT &&
                     comp_ui_asset_generation_mount(&mounted, &store) &&
                     mounted.root.generation == 3u,
                 "semantic manifest failure preserves active generation");

    printf("PASS_UI_ASSET_GENERATION generation=%lu noop_write_bytes=0 "
           "rollback_generation=1 crc_preserved=2 "
           "xor_patch_generation=3 malformed_preserved=3 frame_bytes=%u\n",
           (unsigned long)mounted.root.generation,
           RAW_FRAME_BYTES);
    free(frame);
    free(blob);
    free(flash.bytes);
    return 0;
}
