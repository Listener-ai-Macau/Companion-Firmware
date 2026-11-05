#include "companion_pet_trace.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(void)
{
    comp_runtime_t r={0};comp_runtime_frame_t f={0};
    r.reaction_generation=9u;r.reaction_due_ms=100u;r.touch_contact=true;
    f.kind=COMP_RUNTIME_FRAME_REACTION;f.surface=COMP_SCREEN_SURFACE_HOME;
    f.reaction_generation=9u;f.recording=DENZIC_AUDIO_RECORDING_STATE_IDLE;
    assert(comp_pet_trace_stamp(&r,&f) && f.trace_intent_kind==1u && f.trace_intent_ms==100u);
    r.reaction_due_ms=250u;r.reaction_generation=10u;
    assert(f.trace_intent_ms==100u && f.reaction_generation==9u);
    assert(!comp_pet_trace_stamp(&r,&f));
    r.reaction_generation=9u;r.touch_contact=false;
    f.trace_intent_kind=0u;assert(!comp_pet_trace_stamp(&r,&f));
    f.reaction_reply=true;r.pet.last_input_ms=200u;r.pet.interaction=COMP_PET_HEAD_PAT;
    assert(comp_pet_trace_stamp(&r,&f) && f.trace_intent_kind==2u && f.trace_intent_ms==200u);
    r.pet.interaction=COMP_PET_SHAKE;
    assert(comp_pet_trace_stamp(&r,&f) && f.trace_intent_kind==3u);
    f.kind=COMP_RUNTIME_FRAME_RECORDING_WAVE;f.recording_token=123u;f.recording_elapsed_seconds=77u;
    assert(!comp_pet_trace_stamp(&r,&f) && f.recording_token==123u && f.recording_elapsed_seconds==77u);
    f.kind=COMP_RUNTIME_FRAME_HOLD;f.hold_generation=999u;
    assert(!comp_pet_trace_stamp(&r,&f) && f.hold_generation==999u);
    f.kind=COMP_RUNTIME_FRAME_STATUS;f.update_display=0x1234u;
    assert(!comp_pet_trace_stamp(&r,&f) && f.update_display==0x1234u);
    assert(!comp_pet_trace_activation(100u,50u,500u));
    assert(comp_pet_trace_activation(100u,130u,500u));
    assert(comp_pet_trace_activation(UINT32_MAX-10u,4u,500u));
    assert(!comp_pet_trace_activation(4u,UINT32_MAX-10u,500u));
    printf("PASS: immutable accepted-intent timing, no stale/record/HOLD/OTA union overwrite; wrapping activation ownership. frame=%zu runtime=%zu. Not physical/QM latency.\n",sizeof(f),sizeof(r));
    return 0;
}
