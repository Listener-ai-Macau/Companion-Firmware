#ifndef COMPANION_PET_TRACE_H
#define COMPANION_PET_TRACE_H
#include "companion_runtime.h"
/* Snapshot before submit; completion must never borrow the later live finger
 * or a later intention's timestamp. Existing private frame padding/idle union
 * carry this observation, with no event queue or resident framebuffer. */
static inline bool comp_pet_trace_stamp(const comp_runtime_t *r,comp_runtime_frame_t *f)
{
    if(f->kind!=COMP_RUNTIME_FRAME_REACTION || f->surface!=COMP_SCREEN_SURFACE_HOME ||
       f->reaction_step!=0u || f->start_pending || f->prepare_pending ||
       (f->recording!=DENZIC_AUDIO_RECORDING_STATE_IDLE &&
        f->recording!=DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY) ||
       f->reaction_generation!=r->reaction_generation)return false;
    if(!f->reaction_reply) {
        if(!r->touch_contact)return false; /* Exclude timed release-to-centre. */
        f->trace_intent_ms=r->reaction_due_ms;f->trace_intent_kind=1u;
    } else {
#if COMP_PET_PROCEDURAL
        f->trace_intent_ms=r->pet.last_input_ms;
        f->trace_intent_kind=r->pet.interaction>=COMP_PET_PICKUP &&
            r->pet.interaction<=COMP_PET_INVERTED?3u:2u;
#else
        return false;
#endif
    }
    return true;
}
/* An old/no-change activation cannot impersonate this request's panel work.
 * A wrapping interval is measured only for its actual live request. */
static inline bool comp_pet_trace_activation(uint32_t requested,uint32_t started,uint32_t done)
{ return done-started<=done-requested; }
#endif
