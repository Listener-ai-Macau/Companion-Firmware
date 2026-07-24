#ifndef COMPANION_PRODUCT_IDENTITY_H
#define COMPANION_PRODUCT_IDENTITY_H

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

typedef struct {
    uint64_t operation_id;
    uint64_t idempotency_key;
    uint32_t legacy_fnv32;
} companion_product_identity_t;

uint32_t companion_product_identity_legacy_fnv32(const void *, size_t);
bool companion_product_identity_derive(const char *, uint64_t, const void *, size_t,
                                       companion_product_identity_t *);

#endif
