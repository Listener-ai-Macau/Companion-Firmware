#ifndef COMPANION_PET_PROFILE_STORE_H
#define COMPANION_PET_PROFILE_STORE_H
#include "companion_pet_profile.h"
#define COMP_PET_PROFILE_BANK_BYTES 4096u
#define COMP_PET_PROFILE_PAYLOAD_AT 64u
typedef enum { COMP_PET_STORE_OK,COMP_PET_STORE_INVALID,COMP_PET_STORE_STALE,
    COMP_PET_STORE_BUSY,COMP_PET_STORE_IO,COMP_PET_STORE_UNAVAILABLE,
    COMP_PET_STORE_CLEANUP_PENDING } comp_pet_store_result_t;
typedef struct {
    comp_pet_profile_read_fn read;
    bool (*write)(void *,uint32_t,const uint8_t *,size_t);
    bool (*erase)(void *,uint32_t);
    void *context;
} comp_pet_profile_port_t;
typedef struct {
    comp_pet_profile_port_t port;
    uint8_t uid[12];
    uint32_t generation,length,active_crc,token,expected_crc,received,started_ms,last_progress_ms;
    uint8_t active_bank,writing_bank;
    bool mounted,persisted,writing,cleanup_pending;
} comp_pet_profile_store_t;
/* Mount is read-only, refuses foreign/unknown media, committed corruption and
 * equal-generation ambiguity. Never formats or falls back to revoked notes. */
comp_pet_store_result_t comp_pet_profile_mount(comp_pet_profile_store_t *,
    const comp_pet_profile_port_t *,const uint8_t uid[12]);
comp_pet_store_result_t comp_pet_profile_begin(comp_pet_profile_store_t *,uint32_t expected_generation,
    uint32_t token,uint32_t bytes,uint32_t crc,uint32_t now);
comp_pet_store_result_t comp_pet_profile_append(comp_pet_profile_store_t *,uint32_t token,
    uint32_t offset,const uint8_t *,size_t,uint32_t now);
comp_pet_store_result_t comp_pet_profile_commit(comp_pet_profile_store_t *,uint32_t token,uint32_t now);
bool comp_pet_profile_read(comp_pet_profile_store_t *,uint32_t expected_generation,
    uint32_t offset,uint8_t *,size_t);
void comp_pet_profile_abort(comp_pet_profile_store_t *);
void comp_pet_profile_expire(comp_pet_profile_store_t *,uint32_t now);
comp_pet_store_result_t comp_pet_profile_cleanup(comp_pet_profile_store_t *);
#endif
