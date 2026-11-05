#ifndef COMPANION_PET_PROFILE_H
#define COMPANION_PET_PROFILE_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Fictional creative presets, not psychological assessment of the owner.
 * Stable numeric IDs are part of the on-device format. */
#define COMP_PET_PROFILE_TYPES 16u
#define COMP_PET_PROFILE_BODY_MAX 1536u
#define COMP_PET_PROFILE_NOTES_MAX 8u
#define COMP_PET_PROFILE_NOTE_BYTES 160u
#define COMP_PET_PROFILE_NAME_BYTES 48u
typedef struct { uint8_t sociability,curiosity,expressiveness,calmness; } comp_pet_traits_t;
typedef bool (*comp_pet_profile_read_fn)(void *,uint32_t,uint8_t *,size_t);
const char *comp_pet_profile_type(unsigned type);
uint32_t comp_pet_profile_seed(const uint8_t uid[12]);
comp_pet_traits_t comp_pet_profile_traits(unsigned type,uint32_t seed);
/* Canonical little-endian body: schema,type,flags,name lengths,note count,
 * two reserved bytes,individual seed,two reserved u16; names then notes.
 * Note: id/createdUTC/expiryUTC u32, kind/UTF8-length u8,reserved u16,text.
 * Only explicitly confirmed entries are permitted by the host contract.
 * No microphone, library, cloud, automatic extraction or heap ownership. */
bool comp_pet_profile_validate(comp_pet_profile_read_fn,void *,uint32_t bytes);
#endif
