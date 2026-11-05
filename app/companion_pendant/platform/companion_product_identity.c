#include "companion_product_identity.h"

#include <stdbool.h>

static uint64_t hash_domain(const char *domain, uint64_t wire_id,
                            const void *payload, size_t payload_size,
                            uint64_t seed) {
    const uint8_t *bytes = (const uint8_t *)payload;
    uint64_t hash = UINT64_C(1469598103934665603) ^ seed;
    if (domain == NULL || payload == NULL) return 0u;
    for (const uint8_t *p = (const uint8_t *)domain; *p != 0u; ++p) {
        hash ^= *p; hash *= UINT64_C(1099511628211);
    }
    hash ^= (uint8_t)payload_size; hash *= UINT64_C(1099511628211);
    hash ^= (uint8_t)(payload_size >> 8); hash *= UINT64_C(1099511628211);
    for (unsigned shift = 0u; shift < 64u; shift += 8u) {
        hash ^= (uint8_t)(wire_id >> shift); hash *= UINT64_C(1099511628211);
    }
    for (size_t i = 0u; i < payload_size; ++i) {
        hash ^= bytes[i]; hash *= UINT64_C(1099511628211);
    }
    return hash == 0u ? UINT64_C(1) : hash;
}

uint32_t companion_product_identity_legacy_fnv32(const void *payload, size_t size) {
    const uint8_t *bytes = (const uint8_t *)payload;
    uint32_t hash = UINT32_C(2166136261);
    if (payload == NULL) return 0u;
    for (size_t i = 0u; i < size; ++i) {
        hash ^= bytes[i]; hash *= UINT32_C(16777619);
    }
    return hash;
}

bool companion_product_identity_derive(const char *domain, uint64_t wire_id,
                                       const void *payload, size_t payload_size,
                                       companion_product_identity_t *out) {
    if (domain == NULL || payload == NULL || payload_size == 0u || out == NULL) return false;
    out->legacy_fnv32 = companion_product_identity_legacy_fnv32(payload, payload_size);
    out->operation_id = hash_domain(domain, wire_id, payload, payload_size,
                                     UINT64_C(0x6D6574612D6F7021));
    out->idempotency_key = hash_domain(domain, wire_id, payload, payload_size,
                                        UINT64_C(0x6D6574612D6B6579));
    return out->operation_id != out->idempotency_key;
}
