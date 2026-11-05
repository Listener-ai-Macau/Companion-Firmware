#ifndef COMPANION_WBA_UPDATE_P256_H
#define COMPANION_WBA_UPDATE_P256_H

#include "wba_update_manifest_wire.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef bool (*comp_wba_update_p256_verify_digest_fn)(
    void *context,
    const uint8_t public_key_xy[COMP_WBA_UPDATE_P256_PUBLIC_KEY_BYTES],
    const uint8_t digest[COMP_WBA_UPDATE_SHA256_BYTES],
    const uint8_t signature[COMP_WBA_UPDATE_P256_SIGNATURE_BYTES]);

/* The public key is a build-time trust anchor: big-endian X || Y, 64 bytes.
 * Production must provide a nonzero key_id, the key bytes, and a verifier.
 * Leaving any field absent is an intentional fail-closed NOT_READY state. */
typedef struct {
    uint32_t key_id;
    const uint8_t *public_key_xy;
    comp_wba_update_p256_verify_digest_fn verify_digest;
    void *verify_context;
} comp_wba_update_p256_trust_t;

bool comp_wba_update_p256_trust_configured(
    const comp_wba_update_p256_trust_t *trust);

/* Matches comp_wba_update_ports_t.authorize_manifest. The service/bootloader
 * wrapper passes a comp_wba_update_p256_trust_t as context. */
bool comp_wba_update_p256_authorize_manifest(
    void *context, const comp_wba_update_manifest_t *manifest,
    const uint8_t *authentication, uint8_t authentication_length);

#ifdef __cplusplus
}
#endif

#endif
