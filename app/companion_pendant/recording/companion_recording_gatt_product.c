#include "companion_recording_gatt_product.h"

#include <string.h>

static uint32_t crc32(const uint8_t *data, size_t length) {
  uint32_t value = 0xffffffffu;
  for (size_t i = 0u; i < length; ++i) {
    value ^= data[i];
    for (uint32_t bit = 0u; bit < 8u; ++bit)
      value = (value >> 1u) ^ (0xedb88320u & (uint32_t)-(int)(value & 1u));
  }
  return ~value;
}

static void wav_header(uint8_t *out, uint32_t pcm_length) {
  memset(out, 0, COMPANION_RECORDING_WAV_HEADER_BYTES);
  memcpy(out, "RIFF", 4); memcpy(out + 8, "WAVEfmt ", 8);
  out[4] = (uint8_t)((pcm_length + 36u) & 0xffu);
  out[5] = (uint8_t)((pcm_length + 36u) >> 8u);
  out[6] = (uint8_t)((pcm_length + 36u) >> 16u);
  out[7] = (uint8_t)((pcm_length + 36u) >> 24u);
  out[16] = 16u; out[20] = 1u; out[22] = 1u;
  out[24] = 0x80u; out[25] = 0x3eu; out[28] = 0x00u; out[29] = 0x7du;
  out[32] = 2u; out[34] = 16u; memcpy(out + 36, "data", 4);
  out[40] = (uint8_t)(pcm_length & 0xffu);
  out[41] = (uint8_t)(pcm_length >> 8u);
  out[42] = (uint8_t)(pcm_length >> 16u);
  out[43] = (uint8_t)(pcm_length >> 24u);
}

companion_recording_product_result_t companion_recording_product_pull(
    const uint8_t *chunk_request, uint16_t request_length,
    companion_recording_product_source_t *source,
    companion_recording_product_observation_t *observation) {
  companion_recording_chunk_request_t request;
  companion_recording_product_metadata_t metadata;
  companion_recording_product_result_t result = COMPANION_RECORDING_PRODUCT_SOURCE;
  if (chunk_request == NULL || source == NULL || observation == NULL ||
      source->parse_chunk_request == NULL || source->metadata == NULL ||
      source->chunk == NULL || source->stop == NULL ||
      !source->parse_chunk_request(chunk_request, request_length, &request))
    return COMPANION_RECORDING_PRODUCT_BAD_REQUEST;
  memset(observation, 0, sizeof(*observation));
  observation->expected_sequence = 0u;
  observation->expected_offset = request.byte_offset;
  if (!source->metadata(source->context, &metadata)) goto cleanup;
  observation->list_reads = 1u;
  if (metadata.total_length > COMPANION_RECORDING_HOST_CAPACITY ||
      metadata.recording_id != request.recording_id || request.byte_offset != 0u) {
    result = COMPANION_RECORDING_PRODUCT_CAPACITY; goto cleanup;
  }
  while (observation->pcm_length < metadata.total_length) {
    uint8_t payload[COMPANION_RECORDING_GATT_MAX_PAYLOAD_BYTES];
    companion_recording_product_chunk_t chunk;
    uint16_t requested = (uint16_t)(metadata.total_length - observation->pcm_length);
    if (requested > (uint16_t)sizeof(payload)) requested = (uint16_t)sizeof(payload);
    if (!source->chunk(source->context, metadata.recording_id, observation->pcm_length,
                       requested, payload, (uint16_t)sizeof(payload), &chunk)) goto cleanup;
    observation->chunk_reads++;
    if (chunk.recording_id != metadata.recording_id || chunk.sequence != observation->expected_sequence ||
        chunk.offset != observation->pcm_length || chunk.total_length != metadata.total_length ||
        chunk.payload_length == 0u || chunk.payload_length > requested ||
        observation->pcm_length + chunk.payload_length > sizeof(observation->pcm)) {
      result = COMPANION_RECORDING_PRODUCT_PROTOCOL; goto cleanup;
    }
    if (crc32(payload, chunk.payload_length) != chunk.packet_crc32) {
      result = COMPANION_RECORDING_PRODUCT_CRC; goto cleanup;
    }
    memcpy(observation->pcm + observation->pcm_length, payload, chunk.payload_length);
    observation->pcm_length += chunk.payload_length;
    observation->bytes_retained = observation->pcm_length;
    observation->expected_sequence++;
    observation->expected_offset = observation->pcm_length;
    if (chunk.final_packet && observation->pcm_length != metadata.total_length) {
      result = COMPANION_RECORDING_PRODUCT_PROTOCOL; goto cleanup;
    }
  }
  if (crc32(observation->pcm, observation->pcm_length) != metadata.content_crc32) {
    result = COMPANION_RECORDING_PRODUCT_CRC; goto cleanup;
  }
  wav_header(observation->wav, observation->pcm_length);
  memcpy(observation->wav + COMPANION_RECORDING_WAV_HEADER_BYTES, observation->pcm,
         observation->pcm_length);
  observation->wav_length = observation->pcm_length + COMPANION_RECORDING_WAV_HEADER_BYTES;
  memcpy(observation->sha256, metadata.sha256, sizeof(observation->sha256));
  result = COMPANION_RECORDING_PRODUCT_OK;
cleanup:
  observation->stop_calls++;
  if (!source->stop(source->context)) result = COMPANION_RECORDING_PRODUCT_SOURCE;
  observation->cleanup_calls++;
  return result;
}
