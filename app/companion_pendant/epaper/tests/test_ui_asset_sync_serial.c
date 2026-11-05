#include "asset_store.h"
#include "ui_asset_generation.h"
#include "ui_asset_sync_serial.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum {
    FLASH_BYTES = 0x00200000u,
    BASE_PACK_BYTES = 0x00130000u,
    STATIC_OFFSET = 0x001DC000u,
    STATIC_CAPACITY = 0x00021000u,
};

typedef struct {
    uint8_t *flash;
    char output[4096];
    size_t output_length;
    uint32_t write_bytes;
    uint32_t erase_count;
    uint32_t reset_count;
    bool busy;
} fixture_t;

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

static bool flash_read(void *context, uint32_t offset,
                       uint8_t *data, size_t length)
{
    fixture_t *fixture = context;
    if (offset > FLASH_BYTES || length > FLASH_BYTES - offset) {
        return false;
    }
    memcpy(data, fixture->flash + offset, length);
    return true;
}

static bool flash_erase(void *context, uint32_t offset)
{
    fixture_t *fixture = context;
    if ((offset % 4096u) != 0u || offset > FLASH_BYTES - 4096u) {
        return false;
    }
    memset(fixture->flash + offset, 0xFF, 4096u);
    fixture->erase_count++;
    return true;
}

static bool flash_write(void *context, uint32_t offset,
                        const uint8_t *data, size_t length)
{
    fixture_t *fixture = context;
    if (offset > FLASH_BYTES || length > FLASH_BYTES - offset) {
        return false;
    }
    for (size_t index = 0u; index < length; ++index) {
        fixture->flash[offset + index] &= data[index];
    }
    fixture->write_bytes += (uint32_t)length;
    return true;
}

static bool send_output(void *context, const uint8_t *data, size_t length)
{
    fixture_t *fixture = context;
    if (length > sizeof(fixture->output) - fixture->output_length - 1u) {
        return false;
    }
    memcpy(fixture->output + fixture->output_length, data, length);
    fixture->output_length += length;
    fixture->output[fixture->output_length] = '\0';
    return true;
}

static bool is_busy(void *context)
{
    return ((fixture_t *)context)->busy;
}

static void reset_device(void *context)
{
    ((fixture_t *)context)->reset_count++;
}

static void require_true(bool value, const char *message)
{
    if (!value) {
        fprintf(stderr, "FAIL: %s\n", message);
        exit(1);
    }
}

static uint32_t build_manifest(uint8_t *blob)
{
    const uint32_t size =
        COMP_UI_ASSET_MANIFEST_HEADER_BYTES +
        COMP_UI_ASSET_MANIFEST_ENTRY_BYTES;
    memset(blob, 0, size);
    memcpy(blob, "CUIM", 4u);
    write_le16(blob + 4u, COMP_UI_ASSET_GENERATION_FORMAT_VERSION);
    write_le16(blob + 6u, COMP_UI_ASSET_MANIFEST_HEADER_BYTES);
    write_le16(blob + 8u, 1u);
    write_le16(blob + 10u, COMP_UI_ASSET_MANIFEST_ENTRY_BYTES);
    write_le32(blob + 12u, size);
    write_le32(blob + COMP_UI_ASSET_MANIFEST_HEADER_BYTES,
               comp_ui_asset_state_hash("expression_calm"));
    write_le16(blob + COMP_UI_ASSET_MANIFEST_HEADER_BYTES + 4u, 7u);
    write_le16(blob + COMP_UI_ASSET_MANIFEST_HEADER_BYTES + 18u, 480u);
    return size;
}

static void seed_base_cemp(fixture_t *fixture)
{
    uint8_t *header = fixture->flash;
    memcpy(header, "CEMP", 4u);
    write_le16(header + 4u, 1u);
    write_le16(header + 6u, 80u);
    write_le32(header + 8u, BASE_PACK_BYTES);
    write_le32(header + 56u, 0x12345678u);
    write_le32(header + 60u, 0x89ABCDEFu);
}

int main(void)
{
    fixture_t fixture = {0};
    comp_ui_asset_generation_io_t io;
    comp_ui_asset_sync_serial_t sync;
    uint8_t blob[COMP_UI_ASSET_MANIFEST_HEADER_BYTES +
                 COMP_UI_ASSET_MANIFEST_ENTRY_BYTES];
    uint8_t interrupted_blob[312];
    char command[320];
    const char *id =
        "0100000000000000000000000000000000000000000000000000000000000000";
    const char *id2 =
        "0200000000000000000000000000000000000000000000000000000000000000";

    fixture.flash = malloc(FLASH_BYTES);
    require_true(fixture.flash != NULL, "allocate flash");
    memset(fixture.flash, 0xFF, FLASH_BYTES);
    seed_base_cemp(&fixture);
    io = (comp_ui_asset_generation_io_t){
        .read = flash_read,
        .erase_4k = flash_erase,
        .write = flash_write,
        .context = &fixture,
        .partition_size = FLASH_BYTES,
    };
    require_true(comp_ui_asset_sync_serial_init_with_static_region(
                     &sync, &io, send_output, is_busy, reset_device,
                     &fixture, STATIC_OFFSET, STATIC_CAPACITY),
                 "initialize transport");
    require_true(comp_ui_asset_sync_serial_feed(
                     &sync, (const uint8_t *)"UIQ\n", 4u) &&
                     strstr(fixture.output,
                            "QUERY result=ready generation=0") != NULL &&
                     strstr(fixture.output,
                            "base_payload_crc32=12345678") != NULL &&
                     strstr(fixture.output,
                            "blob_size=0 blob_crc32=00000000") != NULL,
                 "query empty flash");

    uint32_t blob_size = build_manifest(blob);
    int bad_command_size = snprintf(
        command, sizeof(command),
        "UIB 0 %u %u 0x%08X 0 %u 0x%08X %s\n",
        BASE_PACK_BYTES + 1u, blob_size, crc32_bytes(blob, blob_size),
        blob_size, crc32_bytes(blob, blob_size), id);
    require_true(
        bad_command_size > 0 &&
            comp_ui_asset_sync_serial_feed(
                &sync, (const uint8_t *)command,
                (size_t)bad_command_size) &&
            strstr(fixture.output, "BEGIN result=base_mismatch") != NULL &&
            fixture.write_bytes == 0u,
        "base CEMP mismatch blocks write");

    int command_size = snprintf(
        command, sizeof(command),
        "UIB 0 %u %u 0x%08X 0 %u 0x%08X %s\n",
        BASE_PACK_BYTES, blob_size, crc32_bytes(blob, blob_size),
        blob_size, crc32_bytes(blob, blob_size), id);
    require_true(command_size > 0 &&
                     (size_t)command_size < sizeof(command) &&
                     comp_ui_asset_sync_serial_feed(
                         &sync, (const uint8_t *)command,
                         (size_t)command_size) &&
                     sync.receiving_blob,
                 "begin transfer");
    for (uint32_t offset = 0u; offset < blob_size; ++offset) {
        require_true(comp_ui_asset_sync_serial_feed(
                         &sync, &blob[offset], 1u),
                     "stream blob");
    }
    require_true(fixture.reset_count == 1u &&
                     strstr(fixture.output,
                            "FINISH result=ok") != NULL,
                 "commit and reset");

    fixture.output_length = 0u;
    fixture.output[0] = '\0';
    require_true(comp_ui_asset_sync_serial_feed(
                     &sync, (const uint8_t *)"UIQ\n", 4u) &&
                     strstr(fixture.output,
                            "QUERY result=ready generation=1") != NULL &&
                     strstr(fixture.output,
                            "blob_size=56 blob_crc32=") != NULL &&
                     strstr(fixture.output,
                            "manifest_size=56 manifest_crc32=") != NULL,
                 "query committed generation");

    memset(interrupted_blob, 0xA5, sizeof(interrupted_blob));
    memcpy(interrupted_blob, blob, blob_size);
    uint32_t writes_before_abort = fixture.write_bytes;
    command_size = snprintf(
        command, sizeof(command),
        "UIB 1 %u %u 0x%08X 0 %u 0x%08X %s\n",
        BASE_PACK_BYTES, (unsigned)sizeof(interrupted_blob),
        crc32_bytes(interrupted_blob, sizeof(interrupted_blob)),
        blob_size, crc32_bytes(blob, blob_size), id2);
    require_true(command_size > 0 &&
                     comp_ui_asset_sync_serial_feed(
                         &sync, (const uint8_t *)command,
                         (size_t)command_size) &&
                     comp_ui_asset_sync_serial_feed(
                         &sync, interrupted_blob, 280u) &&
                     fixture.write_bytes ==
                         writes_before_abort + 256u,
                 "start interrupted transfer");
    comp_ui_asset_sync_serial_abort(&sync);
    fixture.output_length = 0u;
    fixture.output[0] = '\0';
    require_true(comp_ui_asset_sync_serial_feed(
                     &sync, (const uint8_t *)"UIQ\n", 4u) &&
                     strstr(fixture.output,
                            "QUERY result=ready generation=1") != NULL &&
                     fixture.reset_count == 1u,
                 "aborted transfer preserves active generation");

    uint32_t writes = fixture.write_bytes;
    uint32_t erases = fixture.erase_count;
    command_size = snprintf(
        command, sizeof(command),
        "UIB 1 %u %u 0x%08X 0 %u 0x%08X %s\n",
        BASE_PACK_BYTES, blob_size, crc32_bytes(blob, blob_size),
        blob_size, crc32_bytes(blob, blob_size), id);
    require_true(command_size > 0 &&
                     comp_ui_asset_sync_serial_feed(
                         &sync, (const uint8_t *)command,
                         (size_t)command_size) &&
                     fixture.write_bytes == writes &&
                     fixture.erase_count == erases &&
                     strstr(fixture.output,
                            "BEGIN result=already_current") != NULL,
                 "same identity performs zero writes");

    fixture.busy = true;
    command[4] = '1';
    require_true(comp_ui_asset_sync_serial_feed(
                     &sync, (const uint8_t *)command,
                     (size_t)command_size) &&
                     strstr(fixture.output, "BEGIN result=busy") != NULL,
                 "recording busy blocks write");

    fixture.busy = false;
    fixture.output_length = 0u;
    fixture.output[0] = '\0';
    require_true(comp_ui_asset_sync_serial_feed(
                     &sync, (const uint8_t *)"UIRQ\n", 5u) &&
                     strstr(fixture.output,
                            "RESOURCE_QUERY result=ready present=0") != NULL,
                 "query missing static resource");

    uint8_t resource_pack[64] = {0u};
    memcpy(resource_pack, "CRRP", 4u);
    write_le16(resource_pack + 4u, 1u);
    write_le16(resource_pack + 6u, sizeof(resource_pack));
    write_le32(resource_pack + 8u, sizeof(resource_pack));
    uint32_t resource_crc =
        crc32_bytes(resource_pack, sizeof(resource_pack));
    command_size = snprintf(
        command, sizeof(command), "UIRB %u 0x%08X\n",
        (unsigned)sizeof(resource_pack), (unsigned)resource_crc);
    uint32_t resource_writes_before = fixture.write_bytes;
    uint32_t resource_erases_before = fixture.erase_count;
    require_true(command_size > 0 &&
                     comp_ui_asset_sync_serial_feed(
                         &sync, (const uint8_t *)command,
                         (size_t)command_size) &&
                     sync.receiving_blob && sync.receiving_static &&
                     comp_ui_asset_sync_serial_feed(
                         &sync, resource_pack, sizeof(resource_pack)) &&
                     fixture.write_bytes ==
                         resource_writes_before + sizeof(resource_pack) &&
                     fixture.erase_count == resource_erases_before + 1u &&
                     fixture.reset_count == 2u &&
                     strstr(fixture.output,
                            "RESOURCE_FINISH result=ok") != NULL,
                 "write and read back static resource");

    fixture.output_length = 0u;
    fixture.output[0] = '\0';
    require_true(comp_ui_asset_sync_serial_feed(
                     &sync, (const uint8_t *)"UIRQ\n", 5u) &&
                     strstr(fixture.output,
                            "RESOURCE_QUERY result=ready present=1") != NULL,
                 "query current static resource");
    uint32_t resource_writes = fixture.write_bytes;
    uint32_t resource_erases = fixture.erase_count;
    require_true(comp_ui_asset_sync_serial_feed(
                     &sync, (const uint8_t *)command,
                     (size_t)command_size) &&
                     fixture.write_bytes == resource_writes &&
                     fixture.erase_count == resource_erases &&
                     strstr(fixture.output,
                            "RESOURCE_BEGIN result=already_current") != NULL,
                 "same static resource performs zero writes");

    printf("PASS_UI_ASSET_SYNC_SERIAL generation=1 write_bytes=%lu "
           "reset_count=%lu noop_write_bytes=0 "
           "static_noop_write_bytes=0\n",
           (unsigned long)fixture.write_bytes,
           (unsigned long)fixture.reset_count);
    free(fixture.flash);
    return 0;
}
