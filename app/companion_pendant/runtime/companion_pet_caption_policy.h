#ifndef COMPANION_PET_CAPTION_POLICY_H
#define COMPANION_PET_CAPTION_POLICY_H
#include <stdint.h>
/* Existing UI71 authored bitmap rows. Selection and rendering share this
 * lookup so a wordless pose never consumes the visible speech cooldown.
 * No new artwork, translation, extra animation phase or panel transaction. */
static inline uint8_t comp_pet_caption_slot(unsigned family,unsigned zone)
{
    static const uint8_t slots[][3]={
        {1u,1u,0u},{1u,3u,0u},{3u,0u,1u},{4u,4u,2u},{4u,3u,2u},{4u,0u,3u},
        {3u,1u,4u},{3u,2u,5u},{3u,3u,11u},{6u,2u,6u},{6u,3u,7u},
        {2u,1u,8u},{2u,0u,9u},{5u,0u,10u}};
    for(unsigned i=0u;i<sizeof(slots)/sizeof(slots[0]);++i)
        if(slots[i][0]==family && slots[i][1]==zone)return slots[i][2];
    return UINT8_MAX;
}
#endif
