#ifndef COMPANION_RECORDING_GATT_PRODUCT_H
#define COMPANION_RECORDING_GATT_PRODUCT_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define COMPANION_RECORDING_HOST_CAPACITY 4096u
#define COMPANION_RECORDING_WAV_HEADER_BYTES 44u
#define COMPANION_RECORDING_GATT_MAX_PAYLOAD_BYTES 248u

typedef struct {
  uint8_t schema_version;
  uint8_t flags;
  uint16_t requested_length;
  uint32_t recording_id;
  uint32_t byte_offset;
  uint32_t host_resume_token;
} companion_recording_chunk_request_t;

typedef struct {
  uint32_t recording_id;
  uint32_t total_length;
  uint32_t content_crc32;
  uint8_t sha256[32];
} companion_recording_product_metadata_t;

typedef struct {
  uint32_t recording_id;
  uint32_t sequence;
  uint32_t offset;
  uint32_t total_length;
  uint32_t packet_crc32;
  uint16_t payload_length;
  bool final_packet;
  uint8_t final_sha256[32];
} companion_recording_product_chunk_t;

typedef struct {
  void *context;
  bool (*parse_chunk_request)(const uint8_t *, uint16_t,
                              companion_recording_chunk_request_t *);
  bool (*metadata)(void *, companion_recording_product_metadata_t *);
  bool (*chunk)(void *, uint32_t, uint32_t, uint16_t, uint8_t *, uint16_t,
                companion_recording_product_chunk_t *);
  bool (*stop)(void *);
} companion_recording_product_source_t;

typedef struct {
  uint32_t list_reads;
  uint32_t chunk_reads;
  uint32_t bytes_retained;
  uint32_t dropped;
  uint32_t stop_calls;
  uint32_t cleanup_calls;
  uint32_t expected_sequence;
  uint32_t expected_offset;
  uint8_t pcm[COMPANION_RECORDING_HOST_CAPACITY];
  uint32_t pcm_length;
  uint8_t wav[COMPANION_RECORDING_HOST_CAPACITY + COMPANION_RECORDING_WAV_HEADER_BYTES];
  uint32_t wav_length;
  uint8_t sha256[32];
} companion_recording_product_observation_t;

typedef enum {
  COMPANION_RECORDING_PRODUCT_OK = 0,
  COMPANION_RECORDING_PRODUCT_BAD_REQUEST,
  COMPANION_RECORDING_PRODUCT_CAPACITY,
  COMPANION_RECORDING_PRODUCT_PROTOCOL,
  COMPANION_RECORDING_PRODUCT_CRC,
  COMPANION_RECORDING_PRODUCT_SHA,
  COMPANION_RECORDING_PRODUCT_SOURCE,
} companion_recording_product_result_t;

companion_recording_product_result_t companion_recording_product_pull(
    const uint8_t *chunk_request, uint16_t request_length,
    companion_recording_product_source_t *source,
    companion_recording_product_observation_t *observation);

#endif
