#ifndef COMPANION_EPAPER_UI_ASSET_SYNC_SERIAL_H
#define COMPANION_EPAPER_UI_ASSET_SYNC_SERIAL_H

#include "ui_asset_generation.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_UI_ASSET_SYNC_LINE_BYTES 224u
#define COMP_UI_ASSET_SYNC_WRITE_BUFFER_BYTES 256u

typedef bool (*comp_ui_asset_sync_send_fn_t)(
    void *context, const uint8_t *data, size_t length);
typedef bool (*comp_ui_asset_sync_busy_fn_t)(void *context);
typedef void (*comp_ui_asset_sync_reset_fn_t)(void *context);

typedef struct {
    const comp_ui_asset_generation_io_t *io;
    comp_ui_asset_sync_send_fn_t send;
    comp_ui_asset_sync_busy_fn_t busy;
    comp_ui_asset_sync_reset_fn_t reset;
    void *context;
    comp_ui_asset_generation_transaction_t transaction;
    uint8_t line[COMP_UI_ASSET_SYNC_LINE_BYTES];
    uint8_t write_buffer[COMP_UI_ASSET_SYNC_WRITE_BUFFER_BYTES];
    uint32_t binary_remaining;
    uint32_t static_offset;
    uint32_t static_capacity;
    uint32_t static_expected_bytes;
    uint32_t static_expected_crc32;
    uint32_t static_bytes_written;
    uint32_t static_stream_crc32;
    uint32_t static_sectors_erased;
    uint16_t line_length;
    uint16_t write_buffer_length;
    bool receiving_blob;
    bool receiving_static;
} comp_ui_asset_sync_serial_t;

bool comp_ui_asset_sync_serial_init(
    comp_ui_asset_sync_serial_t *sync,
    const comp_ui_asset_generation_io_t *io,
    comp_ui_asset_sync_send_fn_t send,
    comp_ui_asset_sync_busy_fn_t busy,
    comp_ui_asset_sync_reset_fn_t reset,
    void *context);

bool comp_ui_asset_sync_serial_init_with_static_region(
    comp_ui_asset_sync_serial_t *sync,
    const comp_ui_asset_generation_io_t *io,
    comp_ui_asset_sync_send_fn_t send,
    comp_ui_asset_sync_busy_fn_t busy,
    comp_ui_asset_sync_reset_fn_t reset,
    void *context,
    uint32_t static_offset,
    uint32_t static_capacity);

bool comp_ui_asset_sync_serial_feed(
    comp_ui_asset_sync_serial_t *sync,
    const uint8_t *data,
    size_t length);

void comp_ui_asset_sync_serial_abort(comp_ui_asset_sync_serial_t *sync);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_UI_ASSET_SYNC_SERIAL_H */
