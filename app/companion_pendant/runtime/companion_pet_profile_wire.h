#ifndef COMPANION_PET_PROFILE_WIRE_H
#define COMPANION_PET_PROFILE_WIRE_H
#include "companion_pet_profile_store.h"
/* Explicit negotiated extension of the existing encrypted SETTINGS value.
 * Ordinary legacy reads/writes stay their original13-byte contract. Product
 * dispatch must verify encryption and idle I/O admission before calling. */
#define COMP_PET_PROFILE_RESPONSE_BYTES 96u
size_t comp_pet_profile_exchange(comp_pet_profile_store_t *,const uint8_t *request,size_t bytes,
    bool admitted,uint32_t now_ms,uint8_t response[COMP_PET_PROFILE_RESPONSE_BYTES]);
#endif
