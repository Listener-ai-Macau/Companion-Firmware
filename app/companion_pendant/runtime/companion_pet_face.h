#ifndef COMPANION_PET_FACE_H
#define COMPANION_PET_FACE_H
#include "companion_runtime.h"
uint8_t comp_pet_face_closed(const comp_runtime_frame_t *);
bool comp_pet_face_draw(uint8_t frame[5000],const comp_runtime_frame_t *,
    bool (*progress)(void *),void *context);
#endif
