#ifndef COMPANION_WBA_UPDATE_MANIFEST_WIRE_H
#define COMPANION_WBA_UPDATE_MANIFEST_WIRE_H

#include "wba_update_service.h"

#ifdef __cplusplus
extern "C" {
#endif

/* WUM1 is written once, with response, before the unchanged DOV1 BEGIN.
 * All integers are little endian. The P-256 signature is raw big-endian
 * r || s over SHA-256(bytes[0..75]). The final CRC covers bytes[0..139]. */
#define COMP_WBA_UPDATE_MANIFEST_WIRE_BYTES 144u
#define COMP_WBA_UPDATE_MANIFEST_SIGNED_BYTES 76u
#define COMP_WBA_UPDATE_P256_SIGNATURE_BYTES 64u
#define COMP_WBA_UPDATE_P256_PUBLIC_KEY_BYTES 64u
#define COMP_WBA_UPDATE_SIGNATURE_P256_SHA256 1u

typedef struct {
    comp_wba_update_manifest_t manifest;
    uint32_t key_id;
    uint8_t signature[COMP_WBA_UPDATE_P256_SIGNATURE_BYTES];
} comp_wba_update_manifest_envelope_t;

uint32_t comp_wba_update_wire_crc32(const uint8_t *data, size_t length);

bool comp_wba_update_manifest_signed_bytes(
    const comp_wba_update_manifest_t *manifest, uint32_t key_id,
    uint8_t output[COMP_WBA_UPDATE_MANIFEST_SIGNED_BYTES]);

bool comp_wba_update_manifest_wire_encode(
    const comp_wba_update_manifest_t *manifest, uint32_t key_id,
    const uint8_t signature[COMP_WBA_UPDATE_P256_SIGNATURE_BYTES],
    uint8_t output[COMP_WBA_UPDATE_MANIFEST_WIRE_BYTES]);

bool comp_wba_update_manifest_wire_decode(
    const uint8_t *wire, size_t wire_bytes,
    comp_wba_update_manifest_envelope_t *envelope);

/* GATT integration entry: structural/key-id checks happen before the regular
 * update service invokes its configured trust callback. */
bool comp_wba_update_open_wire(comp_wba_update_service_t *service,
                               const uint8_t *wire, size_t wire_bytes,
                               uint32_t expected_key_id);

#ifdef __cplusplus
}
#endif

#endif
