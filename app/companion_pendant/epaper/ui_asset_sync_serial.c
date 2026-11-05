#include "ui_asset_sync_serial.h"

#include "asset_store.h"

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#define CEMP_HEADER_BYTES 80u
#define STATIC_PACK_HEADER_BYTES 64u

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

static uint32_t crc32_update(uint32_t crc,
                             const uint8_t *data,
                             size_t length)
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

static bool send_bytes(comp_ui_asset_sync_serial_t *sync,
                       const uint8_t *data,
                       size_t length)
{
    return sync != NULL && sync->send != NULL &&
           sync->send(sync->context, data, length);
}

static bool send_text(comp_ui_asset_sync_serial_t *sync,
                      const char *format,
                      ...)
{
    char buffer[512];
    va_list arguments;
    int length;

    va_start(arguments, format);
    length = vsnprintf(buffer, sizeof(buffer), format, arguments);
    va_end(arguments);
    return length > 0 && (size_t)length < sizeof(buffer) &&
           send_bytes(sync, (const uint8_t *)buffer, (size_t)length);
}

static uint8_t hex_nibble(uint8_t value)
{
    if (value >= (uint8_t)'0' && value <= (uint8_t)'9') {
        return (uint8_t)(value - (uint8_t)'0');
    }
    if (value >= (uint8_t)'a' && value <= (uint8_t)'f') {
        return (uint8_t)(value - (uint8_t)'a' + 10u);
    }
    if (value >= (uint8_t)'A' && value <= (uint8_t)'F') {
        return (uint8_t)(value - (uint8_t)'A' + 10u);
    }
    return 0xFFu;
}

static bool parse_u32(const char *text, uint32_t *value)
{
    uint32_t parsed = 0u;
    uint32_t base = 10u;
    size_t index = 0u;

    if (text == NULL || value == NULL || text[0] == '\0') {
        return false;
    }
    if (text[0] == '0' && (text[1] == 'x' || text[1] == 'X')) {
        base = 16u;
        index = 2u;
        if (text[index] == '\0') {
            return false;
        }
    }
    for (; text[index] != '\0'; ++index) {
        uint8_t digit = hex_nibble((uint8_t)text[index]);
        if (digit == 0xFFu || digit >= base ||
            parsed > (UINT32_MAX - digit) / base) {
            return false;
        }
        parsed = parsed * base + digit;
    }
    *value = parsed;
    return true;
}

static bool parse_resource_id(
    const char *text,
    uint8_t resource_id[COMP_UI_ASSET_GENERATION_ID_BYTES])
{
    if (text == NULL || strlen(text) !=
                            COMP_UI_ASSET_GENERATION_ID_BYTES * 2u) {
        return false;
    }
    for (size_t index = 0u;
         index < COMP_UI_ASSET_GENERATION_ID_BYTES;
         ++index) {
        uint8_t high = hex_nibble((uint8_t)text[index * 2u]);
        uint8_t low = hex_nibble((uint8_t)text[index * 2u + 1u]);
        if (high == 0xFFu || low == 0xFFu) {
            return false;
        }
        resource_id[index] = (uint8_t)((high << 4u) | low);
    }
    return true;
}

static void format_resource_id(
    const uint8_t resource_id[COMP_UI_ASSET_GENERATION_ID_BYTES],
    char output[COMP_UI_ASSET_GENERATION_ID_BYTES * 2u + 1u])
{
    static const char hex[] = "0123456789ABCDEF";
    for (size_t index = 0u;
         index < COMP_UI_ASSET_GENERATION_ID_BYTES;
         ++index) {
        output[index * 2u] = hex[resource_id[index] >> 4u];
        output[index * 2u + 1u] = hex[resource_id[index] & 0x0Fu];
    }
    output[COMP_UI_ASSET_GENERATION_ID_BYTES * 2u] = '\0';
}

static bool read_base_identity(
    const comp_ui_asset_sync_serial_t *sync,
    uint32_t *total_size,
    uint32_t *payload_crc32,
    uint32_t *index_crc32)
{
    uint8_t header[CEMP_HEADER_BYTES];
    if (sync == NULL || total_size == NULL || payload_crc32 == NULL ||
        index_crc32 == NULL ||
        !sync->io->read(sync->io->context, 0u, header, sizeof(header)) ||
        memcmp(header, "CEMP", 4u) != 0 ||
        read_le16(header + 4u) != 1u ||
        read_le16(header + 6u) != CEMP_HEADER_BYTES) {
        return false;
    }
    *total_size = read_le32(header + 8u);
    *payload_crc32 = read_le32(header + 56u);
    *index_crc32 = read_le32(header + 60u);
    return *total_size >= CEMP_HEADER_BYTES &&
           *total_size < COMP_UI_ASSET_GENERATION_ARENA_END;
}

static bool static_region_configured(
    const comp_ui_asset_sync_serial_t *sync)
{
    return sync != NULL && sync->static_capacity != 0u &&
           sync->static_offset >= COMP_UI_ASSET_GENERATION_ARENA_END &&
           sync->static_offset <= sync->io->partition_size &&
           sync->static_capacity <=
               sync->io->partition_size - sync->static_offset;
}

static bool static_pack_identity(
    const comp_ui_asset_sync_serial_t *sync,
    uint32_t *pack_bytes,
    uint32_t *pack_crc32)
{
    uint8_t header[STATIC_PACK_HEADER_BYTES];
    uint8_t scratch[COMP_UI_ASSET_SYNC_WRITE_BUFFER_BYTES];
    if (!static_region_configured(sync) ||
        pack_bytes == NULL || pack_crc32 == NULL ||
        !sync->io->read(sync->io->context,
                        sync->static_offset,
                        header,
                        sizeof(header)) ||
        memcmp(header, "CRRP", 4u) != 0 ||
        read_le16(header + 4u) != 1u ||
        read_le16(header + 6u) != STATIC_PACK_HEADER_BYTES) {
        return false;
    }
    uint32_t total = read_le32(header + 8u);
    if (total < STATIC_PACK_HEADER_BYTES ||
        total > sync->static_capacity) {
        return false;
    }

    uint32_t consumed = 0u;
    uint32_t crc = 0xFFFFFFFFu;
    while (consumed < total) {
        size_t chunk = total - consumed;
        if (chunk > sizeof(scratch)) {
            chunk = sizeof(scratch);
        }
        if (!sync->io->read(sync->io->context,
                            sync->static_offset + consumed,
                            scratch,
                            chunk)) {
            return false;
        }
        crc = crc32_update(crc, scratch, chunk);
        consumed += (uint32_t)chunk;
    }
    *pack_bytes = total;
    *pack_crc32 = crc ^ 0xFFFFFFFFu;
    return true;
}

static bool query_static_pack(comp_ui_asset_sync_serial_t *sync)
{
    uint32_t pack_bytes = 0u;
    uint32_t pack_crc32 = 0u;
    if (!static_region_configured(sync)) {
        return send_text(
            sync, "~UI_SYNC:RESOURCE_QUERY result=unavailable\r\n");
    }
    if (!static_pack_identity(sync, &pack_bytes, &pack_crc32)) {
        return send_text(
            sync,
            "~UI_SYNC:RESOURCE_QUERY result=ready present=0 "
            "offset=%lu capacity=%lu\r\n",
            (unsigned long)sync->static_offset,
            (unsigned long)sync->static_capacity);
    }
    return send_text(
        sync,
        "~UI_SYNC:RESOURCE_QUERY result=ready present=1 "
        "offset=%lu capacity=%lu pack_bytes=%lu crc32=%08lX\r\n",
        (unsigned long)sync->static_offset,
        (unsigned long)sync->static_capacity,
        (unsigned long)pack_bytes,
        (unsigned long)pack_crc32);
}

static bool query_generation(comp_ui_asset_sync_serial_t *sync)
{
    comp_asset_store_t store;
    comp_ui_asset_generation_t generation;
    char resource_id[COMP_UI_ASSET_GENERATION_ID_BYTES * 2u + 1u];
    uint8_t empty_id[COMP_UI_ASSET_GENERATION_ID_BYTES] = {0u};
    bool mounted;
    uint32_t base_pack_size;
    uint32_t base_payload_crc32;
    uint32_t base_index_crc32;

    if (!read_base_identity(sync,
                            &base_pack_size,
                            &base_payload_crc32,
                            &base_index_crc32)) {
        return send_text(sync, "~UI_SYNC:QUERY result=base_invalid\r\n");
    }
    if (!comp_asset_store_init_reader(
            &store,
            COMP_ASSET_STORAGE_EXTERNAL_NOR,
            sync->io->partition_size,
            sync->io->read,
            sync->io->context)) {
        return send_text(sync, "~UI_SYNC:QUERY result=io_error\r\n");
    }
    mounted = comp_ui_asset_generation_mount(&generation, &store);
    format_resource_id(mounted ? generation.root.resource_id : empty_id,
                       resource_id);
    return send_text(
        sync,
        "~UI_SYNC:QUERY result=ready generation=%lu resource_id=%s "
        "base_pack_size=%lu base_payload_crc32=%08lX "
        "base_index_crc32=%08lX arena_next=%lu partition_size=%lu "
        "blob_offset=%lu blob_size=%lu blob_crc32=%08lX "
        "manifest_size=%lu manifest_crc32=%08lX root_offset=%lu\r\n",
        (unsigned long)(mounted ? generation.root.generation : 0u),
        resource_id,
        (unsigned long)base_pack_size,
        (unsigned long)base_payload_crc32,
        (unsigned long)base_index_crc32,
        (unsigned long)(mounted ? generation.root.arena_next_offset : 0u),
        (unsigned long)sync->io->partition_size,
        (unsigned long)(mounted ? generation.root.blob_offset : 0u),
        (unsigned long)(mounted ? generation.root.blob_size : 0u),
        (unsigned long)(mounted ? generation.root.blob_crc32 : 0u),
        (unsigned long)(mounted ? generation.root.manifest_size : 0u),
        (unsigned long)(mounted ? generation.root.manifest_crc32 : 0u),
        (unsigned long)(mounted ? generation.root.root_offset : 0u));
}

static void send_receipt(
    comp_ui_asset_sync_serial_t *sync,
    const char *phase,
    const comp_ui_asset_install_receipt_t *receipt)
{
    (void)send_text(
        sync,
        "~UI_SYNC:%s result=%s previous_generation=%lu "
        "active_generation=%lu blob_offset=%lu blob_bytes_written=%lu "
        "root_bytes_written=%lu sectors_erased=%lu\r\n",
        phase,
        comp_ui_asset_install_result_name(receipt->result),
        (unsigned long)receipt->previous_generation,
        (unsigned long)receipt->active_generation,
        (unsigned long)receipt->blob_offset,
        (unsigned long)receipt->blob_bytes_written,
        (unsigned long)receipt->root_bytes_written,
        (unsigned long)receipt->sectors_erased);
}

void comp_ui_asset_sync_serial_abort(comp_ui_asset_sync_serial_t *sync)
{
    if (sync == NULL) {
        return;
    }
    comp_ui_asset_generation_abort(&sync->transaction);
    sync->binary_remaining = 0u;
    sync->write_buffer_length = 0u;
    sync->receiving_blob = false;
    sync->receiving_static = false;
    sync->static_expected_bytes = 0u;
    sync->static_expected_crc32 = 0u;
    sync->static_bytes_written = 0u;
    sync->static_stream_crc32 = 0u;
    sync->static_sectors_erased = 0u;
}

static bool flush_write_buffer(comp_ui_asset_sync_serial_t *sync)
{
    if (sync->write_buffer_length == 0u) {
        return true;
    }
    if (sync->receiving_static) {
        if (!sync->io->write(
                sync->io->context,
                sync->static_offset + sync->static_bytes_written,
                sync->write_buffer,
                sync->write_buffer_length)) {
            comp_ui_asset_sync_serial_abort(sync);
            (void)send_text(
                sync,
                "~UI_SYNC:RESOURCE_FINISH result=write_failed\r\n");
            return false;
        }
        sync->static_stream_crc32 = crc32_update(
            sync->static_stream_crc32,
            sync->write_buffer,
            sync->write_buffer_length);
        sync->static_bytes_written += sync->write_buffer_length;
        sync->write_buffer_length = 0u;
        (void)send_text(
            sync,
            "~UI_SYNC:RESOURCE_CHUNK received=%lu remaining=%lu\r\n",
            (unsigned long)sync->static_bytes_written,
            (unsigned long)sync->binary_remaining);
        return true;
    }
    if (!comp_ui_asset_generation_write(
            &sync->transaction,
            sync->write_buffer,
            sync->write_buffer_length)) {
        comp_ui_asset_sync_serial_abort(sync);
        (void)send_text(sync,
                        "~UI_SYNC:FINISH result=write_failed\r\n");
        return false;
    }
    sync->write_buffer_length = 0u;
    (void)send_text(
        sync,
        "~UI_SYNC:CHUNK received=%lu remaining=%lu\r\n",
        (unsigned long)sync->transaction.bytes_written,
        (unsigned long)sync->binary_remaining);
    return true;
}

static bool finish_blob(comp_ui_asset_sync_serial_t *sync)
{
    comp_ui_asset_install_receipt_t receipt;
    if (!flush_write_buffer(sync)) {
        return false;
    }
    if (sync->receiving_static) {
        uint32_t expected_bytes = sync->static_expected_bytes;
        uint32_t expected_crc32 = sync->static_expected_crc32;
        uint32_t written = sync->static_bytes_written;
        uint32_t sectors = sync->static_sectors_erased;
        uint32_t stream_crc32 = sync->static_stream_crc32 ^ 0xFFFFFFFFu;
        uint32_t readback_bytes = 0u;
        uint32_t readback_crc32 = 0u;
        bool ok = written == expected_bytes &&
                  stream_crc32 == expected_crc32 &&
                  static_pack_identity(
                      sync, &readback_bytes, &readback_crc32) &&
                  readback_bytes == expected_bytes &&
                  readback_crc32 == expected_crc32;
        sync->receiving_blob = false;
        sync->receiving_static = false;
        (void)send_text(
            sync,
            "~UI_SYNC:RESOURCE_FINISH result=%s pack_bytes=%lu "
            "crc32=%08lX readback_crc32=%08lX "
            "bytes_written=%lu sectors_erased=%lu\r\n",
            ok ? "ok" : "verify_failed",
            (unsigned long)expected_bytes,
            (unsigned long)expected_crc32,
            (unsigned long)readback_crc32,
            (unsigned long)written,
            (unsigned long)sectors);
        if (ok && sync->reset != NULL) {
            sync->reset(sync->context);
        }
        return ok;
    }
    receipt = comp_ui_asset_generation_finish(&sync->transaction);
    sync->receiving_blob = false;
    send_receipt(sync, "FINISH", &receipt);
    if (receipt.result == COMP_UI_ASSET_INSTALL_OK &&
        sync->reset != NULL) {
        sync->reset(sync->context);
    }
    return receipt.result == COMP_UI_ASSET_INSTALL_OK;
}

static size_t split_fields(char *line, char **fields, size_t capacity)
{
    size_t count = 0u;
    char *cursor = line;
    while (*cursor != '\0' && count < capacity) {
        while (*cursor == ' ') {
            ++cursor;
        }
        if (*cursor == '\0') {
            break;
        }
        fields[count++] = cursor;
        while (*cursor != '\0' && *cursor != ' ') {
            ++cursor;
        }
        if (*cursor != '\0') {
            *cursor++ = '\0';
        }
    }
    return count;
}

static bool begin_blob(comp_ui_asset_sync_serial_t *sync,
                       char *line)
{
    char *fields[9];
    uint32_t values[7];
    uint8_t resource_id[COMP_UI_ASSET_GENERATION_ID_BYTES];
    comp_ui_asset_install_receipt_t receipt;
    uint32_t base_pack_size;
    uint32_t base_payload_crc32;
    uint32_t base_index_crc32;

    if (split_fields(line, fields, 9u) != 9u ||
        strcmp(fields[0], "UIB") != 0) {
        return send_text(sync, "~UI_SYNC:BEGIN result=bad_command\r\n");
    }
    for (size_t index = 0u; index < 7u; ++index) {
        if (!parse_u32(fields[index + 1u], &values[index])) {
            return send_text(sync, "~UI_SYNC:BEGIN result=bad_argument\r\n");
        }
    }
    if (!parse_resource_id(fields[8], resource_id)) {
        return send_text(sync, "~UI_SYNC:BEGIN result=bad_resource_id\r\n");
    }
    if (!read_base_identity(sync,
                            &base_pack_size,
                            &base_payload_crc32,
                            &base_index_crc32) ||
        values[1] != base_pack_size) {
        return send_text(sync, "~UI_SYNC:BEGIN result=base_mismatch\r\n");
    }
    if (sync->busy != NULL && sync->busy(sync->context)) {
        return send_text(sync, "~UI_SYNC:BEGIN result=busy\r\n");
    }
    receipt = comp_ui_asset_generation_begin(
        &sync->transaction,
        sync->io,
        values[1],
        values[0],
        resource_id,
        values[2],
        values[3],
        values[4],
        values[5],
        values[6]);
    send_receipt(sync, "BEGIN", &receipt);
    if (receipt.result != COMP_UI_ASSET_INSTALL_OK) {
        return receipt.result == COMP_UI_ASSET_INSTALL_ALREADY_CURRENT;
    }
    sync->binary_remaining = values[2];
    sync->write_buffer_length = 0u;
    sync->receiving_blob = true;
    return true;
}

static bool begin_static_pack(comp_ui_asset_sync_serial_t *sync,
                              char *line)
{
    char *fields[3];
    uint32_t pack_bytes;
    uint32_t pack_crc32;
    uint32_t current_bytes = 0u;
    uint32_t current_crc32 = 0u;

    if (split_fields(line, fields, 3u) != 3u ||
        strcmp(fields[0], "UIRB") != 0) {
        return send_text(
            sync, "~UI_SYNC:RESOURCE_BEGIN result=bad_command\r\n");
    }
    if (!parse_u32(fields[1], &pack_bytes) ||
        !parse_u32(fields[2], &pack_crc32) ||
        pack_bytes < STATIC_PACK_HEADER_BYTES ||
        !static_region_configured(sync) ||
        pack_bytes > sync->static_capacity) {
        return send_text(
            sync, "~UI_SYNC:RESOURCE_BEGIN result=bad_argument\r\n");
    }
    if (sync->busy != NULL && sync->busy(sync->context)) {
        return send_text(
            sync, "~UI_SYNC:RESOURCE_BEGIN result=busy\r\n");
    }
    if (static_pack_identity(sync, &current_bytes, &current_crc32) &&
        current_bytes == pack_bytes && current_crc32 == pack_crc32) {
        return send_text(
            sync,
            "~UI_SYNC:RESOURCE_BEGIN result=already_current "
            "pack_bytes=%lu crc32=%08lX bytes_written=0 "
            "sectors_erased=0\r\n",
            (unsigned long)pack_bytes,
            (unsigned long)pack_crc32);
    }

    uint32_t sectors =
        (pack_bytes + COMP_UI_ASSET_GENERATION_SECTOR_BYTES - 1u) /
        COMP_UI_ASSET_GENERATION_SECTOR_BYTES;
    for (uint32_t sector = 0u; sector < sectors; ++sector) {
        if (!sync->io->erase_4k(
                sync->io->context,
                sync->static_offset +
                    sector * COMP_UI_ASSET_GENERATION_SECTOR_BYTES)) {
            return send_text(
                sync,
                "~UI_SYNC:RESOURCE_BEGIN result=erase_failed "
                "sector=%lu\r\n",
                (unsigned long)sector);
        }
    }
    sync->static_expected_bytes = pack_bytes;
    sync->static_expected_crc32 = pack_crc32;
    sync->static_bytes_written = 0u;
    sync->static_stream_crc32 = 0xFFFFFFFFu;
    sync->static_sectors_erased = sectors;
    sync->binary_remaining = pack_bytes;
    sync->write_buffer_length = 0u;
    sync->receiving_blob = true;
    sync->receiving_static = true;
    return send_text(
        sync,
        "~UI_SYNC:RESOURCE_BEGIN result=ok offset=%lu "
        "pack_bytes=%lu crc32=%08lX sectors_erased=%lu\r\n",
        (unsigned long)sync->static_offset,
        (unsigned long)pack_bytes,
        (unsigned long)pack_crc32,
        (unsigned long)sectors);
}

static bool handle_line(comp_ui_asset_sync_serial_t *sync)
{
    bool result;
    sync->line[sync->line_length] = '\0';
    if (strcmp((char *)sync->line, "UIQ") == 0) {
        result = query_generation(sync);
    } else if (strcmp((char *)sync->line, "UIRQ") == 0) {
        result = query_static_pack(sync);
    } else if (strcmp((char *)sync->line, "UIA") == 0) {
        comp_ui_asset_sync_serial_abort(sync);
        result = send_text(sync, "~UI_SYNC:ABORT result=ok\r\n");
    } else if (strncmp((char *)sync->line, "UIRB ", 5u) == 0) {
        result = begin_static_pack(sync, (char *)sync->line);
    } else {
        result = begin_blob(sync, (char *)sync->line);
    }
    sync->line_length = 0u;
    return result;
}

bool comp_ui_asset_sync_serial_init(
    comp_ui_asset_sync_serial_t *sync,
    const comp_ui_asset_generation_io_t *io,
    comp_ui_asset_sync_send_fn_t send,
    comp_ui_asset_sync_busy_fn_t busy,
    comp_ui_asset_sync_reset_fn_t reset,
    void *context)
{
    return comp_ui_asset_sync_serial_init_with_static_region(
        sync, io, send, busy, reset, context, 0u, 0u);
}

bool comp_ui_asset_sync_serial_init_with_static_region(
    comp_ui_asset_sync_serial_t *sync,
    const comp_ui_asset_generation_io_t *io,
    comp_ui_asset_sync_send_fn_t send,
    comp_ui_asset_sync_busy_fn_t busy,
    comp_ui_asset_sync_reset_fn_t reset,
    void *context,
    uint32_t static_offset,
    uint32_t static_capacity)
{
    if (sync == NULL || io == NULL || io->read == NULL ||
        io->erase_4k == NULL || io->write == NULL ||
        io->partition_size <
            COMP_UI_ASSET_GENERATION_ROOT_B_OFFSET +
                COMP_UI_ASSET_GENERATION_SECTOR_BYTES ||
        send == NULL ||
        ((static_offset != 0u || static_capacity != 0u) &&
         (static_offset < COMP_UI_ASSET_GENERATION_ARENA_END ||
          static_offset > COMP_UI_ASSET_GENERATION_ROOT_A_OFFSET ||
          static_capacity >
              COMP_UI_ASSET_GENERATION_ROOT_A_OFFSET - static_offset))) {
        return false;
    }
    *sync = (comp_ui_asset_sync_serial_t){
        .io = io,
        .send = send,
        .busy = busy,
        .reset = reset,
        .context = context,
        .static_offset = static_offset,
        .static_capacity = static_capacity,
    };
    return true;
}

bool comp_ui_asset_sync_serial_feed(
    comp_ui_asset_sync_serial_t *sync,
    const uint8_t *data,
    size_t length)
{
    if (sync == NULL || data == NULL) {
        return false;
    }
    while (length > 0u) {
        if (sync->receiving_blob) {
            size_t capacity =
                sizeof(sync->write_buffer) - sync->write_buffer_length;
            size_t chunk = length;
            if (chunk > capacity) {
                chunk = capacity;
            }
            if (chunk > sync->binary_remaining) {
                chunk = sync->binary_remaining;
            }
            memcpy(sync->write_buffer + sync->write_buffer_length,
                   data, chunk);
            sync->write_buffer_length =
                (uint16_t)(sync->write_buffer_length + chunk);
            sync->binary_remaining -= (uint32_t)chunk;
            data += chunk;
            length -= chunk;
            if (sync->write_buffer_length == sizeof(sync->write_buffer) &&
                !flush_write_buffer(sync)) {
                return false;
            }
            if (sync->binary_remaining == 0u &&
                !finish_blob(sync)) {
                return false;
            }
            continue;
        }

        uint8_t byte = *data++;
        length--;
        if (byte == '\r') {
            continue;
        }
        if (byte == '\n') {
            if (sync->line_length == 0u) {
                continue;
            }
            if (!handle_line(sync)) {
                return false;
            }
            continue;
        }
        if (sync->line_length >= sizeof(sync->line) - 1u) {
            sync->line_length = 0u;
            (void)send_text(sync,
                            "~UI_SYNC:COMMAND result=line_too_long\r\n");
            return false;
        }
        sync->line[sync->line_length++] = byte;
    }
    return true;
}
