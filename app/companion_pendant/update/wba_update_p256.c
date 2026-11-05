#include "wba_update_p256.h"

bool comp_wba_update_p256_trust_configured(
    const comp_wba_update_p256_trust_t *trust)
{
    uint8_t any = 0u;
    if (trust == NULL || trust->key_id == 0u || trust->public_key_xy == NULL ||
        trust->verify_digest == NULL) return false;
    for (size_t i = 0u; i < COMP_WBA_UPDATE_P256_PUBLIC_KEY_BYTES; ++i)
        any |= trust->public_key_xy[i];
    return any != 0u;
}

bool comp_wba_update_p256_authorize_manifest(
    void *context, const comp_wba_update_manifest_t *manifest,
    const uint8_t *authentication, uint8_t authentication_length)
{
    const comp_wba_update_p256_trust_t *trust = context;
    uint8_t signed_bytes[COMP_WBA_UPDATE_MANIFEST_SIGNED_BYTES];
    uint8_t digest[COMP_WBA_UPDATE_SHA256_BYTES];
    companion_sha256_t hash;
    if (!comp_wba_update_p256_trust_configured(trust) || manifest == NULL ||
        authentication == NULL ||
        authentication_length != COMP_WBA_UPDATE_P256_SIGNATURE_BYTES ||
        !comp_wba_update_manifest_signed_bytes(manifest, trust->key_id,
                                                signed_bytes)) return false;
    /* Direct shared SHA implementation: Boot/package verification does not
     * need to link the legacy download service just for three wrappers. */
    companion_sha256_init(&hash);
    companion_sha256_update(&hash, signed_bytes, sizeof(signed_bytes));
    companion_sha256_final(&hash, digest);
    return trust->verify_digest(trust->verify_context, trust->public_key_xy,
                                digest, authentication);
}
