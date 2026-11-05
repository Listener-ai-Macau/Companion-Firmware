#ifndef COMPANION_RECORDING_RESOURCE_PACK_H
#define COMPANION_RECORDING_RESOURCE_PACK_H

#include "asset_store.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_RECORDING_RESOURCE_PACK_MAGIC 0x50525243u
#define COMP_RECORDING_RESOURCE_PACK_VERSION 1u
#define COMP_RECORDING_RESOURCE_PACK_HEADER_BYTES 64u
#define COMP_RECORDING_RESOURCE_PACK_ENTRY_BYTES 32u
#define COMP_RECORDING_RESOURCE_PACK_ENTRY_COUNT 2u
#define COMP_RECORDING_RESOURCE_EXTERNAL_OFFSET 0x001DC000u
#define COMP_RECORDING_RESOURCE_EXTERNAL_CAPACITY 0x00021000u
#define COMP_RECORDING_RESOURCE_EXTERNAL_LIMIT 0x001FD000u

#define COMP_RECORDING_RESOURCE_G7_FRAME_BYTES 640u
#define COMP_RECORDING_RESOURCE_G7_FRAME_COUNT 175u
#define COMP_RECORDING_RESOURCE_G7_BYTES 112000u
#define COMP_RECORDING_RESOURCE_OPUS16_BYTES 21723u
#define COMP_RECORDING_RESOURCE_OPUS16_DURATION_MS 12000u

typedef enum {
    COMP_RECORDING_RESOURCE_G7_SPEECH_PCM = 1u,
    COMP_RECORDING_RESOURCE_OPUS16_FIXTURE = 2u,
} comp_recording_resource_id_t;

typedef enum {
    COMP_RECORDING_RESOURCE_MOUNT_OK = 0u,
    COMP_RECORDING_RESOURCE_MOUNT_BAD_ARGUMENT,
    COMP_RECORDING_RESOURCE_MOUNT_IO_ERROR,
    COMP_RECORDING_RESOURCE_MOUNT_BAD_HEADER,
    COMP_RECORDING_RESOURCE_MOUNT_BAD_HEADER_CRC,
    COMP_RECORDING_RESOURCE_MOUNT_BAD_INDEX_CRC,
    COMP_RECORDING_RESOURCE_MOUNT_BAD_ENTRY,
} comp_recording_resource_mount_result_t;

typedef struct {
    comp_recording_resource_id_t id;
    uint32_t data_offset;
    uint32_t data_bytes;
    uint32_t data_crc32;
    uint32_t aux0;
    uint32_t aux1;
    uint32_t flags;
} comp_recording_resource_entry_t;

typedef struct {
    const comp_asset_store_t *store;
    uint32_t total_bytes;
    uint32_t payload_offset;
    uint32_t payload_bytes;
    uint32_t payload_crc32;
    uint32_t verified_mask;
    comp_recording_resource_entry_t entries[COMP_RECORDING_RESOURCE_PACK_ENTRY_COUNT];
} comp_recording_resource_pack_t;

comp_recording_resource_mount_result_t comp_recording_resource_pack_mount(
    comp_recording_resource_pack_t *pack,
    const comp_asset_store_t *store);
bool comp_recording_resource_pack_get(
    const comp_recording_resource_pack_t *pack,
    comp_recording_resource_id_t id,
    comp_recording_resource_entry_t *entry);
bool comp_recording_resource_pack_verify(
    comp_recording_resource_pack_t *pack,
    comp_recording_resource_id_t id,
    uint8_t *scratch,
    size_t scratch_bytes);
bool comp_recording_resource_pack_verify_all(
    comp_recording_resource_pack_t *pack,
    uint8_t *scratch,
    size_t scratch_bytes);
bool comp_recording_resource_pack_read(
    const comp_recording_resource_pack_t *pack,
    comp_recording_resource_id_t id,
    uint32_t offset,
    uint8_t *destination,
    size_t length);
const char *comp_recording_resource_mount_result_name(
    comp_recording_resource_mount_result_t result);

#ifdef __cplusplus
}
#endif

#endif
