#ifndef COMPANION_RECORDING_GATT_ADAPTER_H
#define COMPANION_RECORDING_GATT_ADAPTER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define COMPANION_RECORDING_ADAPTER_SHA256_BYTES 32u
#define COMPANION_RECORDING_ADAPTER_MAX_PAYLOAD 248u
#define COMPANION_RECORDING_ADAPTER_FINAL_FLAG 0x01u
#define COMPANION_RECORDING_ADAPTER_ERROR_FLAG 0x80u

#pragma pack(push, 1)
typedef struct { uint8_t schema_version; uint8_t flags; uint16_t requested_length; uint32_t recording_id; uint32_t byte_offset; uint32_t host_resume_token; } companion_recording_adapter_request_t;
typedef struct { uint8_t schema_version; uint8_t flags; uint16_t payload_length; uint32_t recording_id; uint32_t packet_sequence; uint32_t byte_offset; uint32_t total_length; uint32_t packet_crc32; uint8_t final_sha256[COMPANION_RECORDING_ADAPTER_SHA256_BYTES]; } companion_recording_adapter_header_t;
typedef struct { uint32_t recording_id; uint32_t started_unix_s; uint32_t duration_ms; uint8_t codec; uint8_t sync_state; uint8_t source_mode; uint8_t reserved; uint32_t total_length; uint8_t sha256[COMPANION_RECORDING_ADAPTER_SHA256_BYTES]; uint32_t content_crc32; } companion_recording_adapter_metadata_t;
#pragma pack(pop)

typedef struct { uint32_t recording_id; uint32_t packet_sequence; uint32_t byte_offset; uint32_t total_length; uint32_t packet_crc32; uint32_t error_code; uint16_t payload_length; bool final_packet; uint8_t final_sha256[COMPANION_RECORDING_ADAPTER_SHA256_BYTES]; } companion_recording_adapter_chunk_t;
_Static_assert(sizeof(companion_recording_adapter_request_t) == 16u, "recording request wire layout drift");
_Static_assert(sizeof(companion_recording_adapter_header_t) == 56u, "recording chunk header wire layout drift");
typedef bool (*companion_recording_adapter_metadata_fn)(void *, companion_recording_adapter_metadata_t *);
typedef bool (*companion_recording_adapter_chunk_fn)(void *, uint32_t, uint32_t, uint16_t, uint8_t *, uint16_t, companion_recording_adapter_chunk_t *);

size_t companion_recording_adapter_build_list(bool has_metadata, const companion_recording_adapter_metadata_t *metadata, uint8_t *out, size_t capacity);
bool companion_recording_adapter_build_chunk(const companion_recording_adapter_request_t *request, companion_recording_adapter_chunk_fn read_chunk, void *context, uint8_t *out, size_t capacity, size_t *out_length);

#endif
