#ifndef COMPANION_PET_GAZE_H
#define COMPANION_PET_GAZE_H
#include <stdint.h>
#include <stdbool.h>

/* Select the existing five authored directions. A 12px central quiet band
 * filters contact jitter without requiring a recognised swipe. Both input
 * coalescing and the renderer use this map, so an unchanged authored target
 * cannot enqueue another e-paper transaction. No new face is synthesised. */
static inline uint8_t comp_pet_gaze_grid(uint16_t coordinate)
{
    const int offset=(int)coordinate-100;
    unsigned step=(unsigned)(offset<0?-offset:offset);
    step=(step+12u)/25u;
    if(step>2u)step=2u;
    return (uint8_t)(offset<0?4u-2u*step:4u+2u*step);
}

/* Keep an accepted authored direction until the finger passes its boundary
 * by 5px. Store the centre of that direction, not a new noisy sample, so the
 * next sample cannot move the boundary itself. Starting contact still chooses
 * its nearest pose immediately; this adds no display timer or intermediate
 * face. The five centres map exactly to the original 0/2/4/6/8 resource keys. */
static inline uint16_t comp_pet_gaze_target(uint16_t accepted, uint16_t sample,
                                           bool starting_contact)
{
    const uint8_t previous=comp_pet_gaze_grid(accepted);
    const uint8_t next=comp_pet_gaze_grid(sample);
    const int centre=50+(int)previous*25/2;
    if (!starting_contact &&
        ((next>previous && (int)sample<=centre+17) ||
         (next<previous && (int)sample>=centre-17))) return (uint16_t)centre;
    return (uint16_t)(50u+(uint16_t)next*25u/2u);
}
#endif
