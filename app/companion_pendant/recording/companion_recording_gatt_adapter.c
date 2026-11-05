#include "companion_recording_gatt_adapter.h"
#include <string.h>

typedef struct { uint8_t schema_version; uint8_t count; uint16_t entry_bytes; } list_header_t;
typedef struct { uint32_t recording_id; uint32_t started_unix_s; uint32_t duration_ms; uint8_t codec; uint8_t sync_state; uint8_t source_mode; uint8_t reserved; uint32_t total_length; uint8_t sha256_prefix[8]; uint32_t content_crc32; } list_entry_t;

size_t companion_recording_adapter_build_list(bool has_metadata, const companion_recording_adapter_metadata_t *m, uint8_t *out, size_t capacity) {
  size_t total = sizeof(list_header_t) + (has_metadata ? sizeof(list_entry_t) : 0u);
  if (out == NULL || capacity < total || (has_metadata && m == NULL)) return 0u;
  list_header_t h = {1u, has_metadata ? 1u : 0u, has_metadata ? (uint16_t)sizeof(list_entry_t) : 0u};
  memcpy(out, &h, sizeof(h));
  if (has_metadata) { list_entry_t e; memset(&e, 0, sizeof(e)); e.recording_id=m->recording_id;e.started_unix_s=m->started_unix_s;e.duration_ms=m->duration_ms;e.codec=m->codec;e.sync_state=m->sync_state;e.source_mode=m->source_mode;e.total_length=m->total_length;memcpy(e.sha256_prefix,m->sha256,8u);e.content_crc32=m->content_crc32;memcpy(out+sizeof(h),&e,sizeof(e)); }
  return total;
}

bool companion_recording_adapter_build_chunk(const companion_recording_adapter_request_t *r, companion_recording_adapter_chunk_fn read_chunk, void *context, uint8_t *out, size_t capacity, size_t *out_length) {
  if (r == NULL || read_chunk == NULL || out == NULL || out_length == NULL || capacity < sizeof(companion_recording_adapter_header_t)) return false;
  companion_recording_adapter_header_t h; memset(&h, 0, sizeof(h)); h.schema_version=1u;h.recording_id=r->recording_id;h.byte_offset=r->byte_offset;
  uint16_t payload_capacity=(uint16_t)(capacity-sizeof(h)); uint16_t requested=r->requested_length;if(requested>payload_capacity)requested=payload_capacity;
  companion_recording_adapter_chunk_t c; memset(&c, 0, sizeof(c)); bool ok=read_chunk(context,r->recording_id,r->byte_offset,requested,out+sizeof(h),payload_capacity,&c);
  if (ok) { h.flags=c.final_packet?COMPANION_RECORDING_ADAPTER_FINAL_FLAG:0u;h.payload_length=c.payload_length;h.recording_id=c.recording_id;h.packet_sequence=c.packet_sequence;h.byte_offset=c.byte_offset;h.total_length=c.total_length;h.packet_crc32=c.packet_crc32;memcpy(h.final_sha256,c.final_sha256,sizeof(h.final_sha256)); }
  else { h.flags=COMPANION_RECORDING_ADAPTER_ERROR_FLAG;h.packet_crc32=c.error_code; }
  memcpy(out,&h,sizeof(h));*out_length=sizeof(h)+(ok?h.payload_length:0u);return true;
}
