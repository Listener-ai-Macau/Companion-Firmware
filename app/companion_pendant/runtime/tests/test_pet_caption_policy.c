#include "companion_runtime.h"
#include "companion_pet_caption_policy.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static void phrase(comp_runtime_t *r,uint32_t now)
{
    comp_runtime_init(r,NULL,now);
    r->pet_startup_pending=false;r->pet_discovery_allowed=false;
    comp_pet_behavior_interact(&r->pet,COMP_PET_HEAD_PAT,true,0u,100u,now);
    r->reaction_pending=true;r->reaction_route_count=1u;
    r->reaction_route[0]=COMP_BROWSER_FAMILY_CALM;
    r->reaction_route[1]=COMP_BROWSER_FAMILY_WARM;
    r->reaction_step=1u;r->reaction_zone=COMP_BROWSER_TAP_ZONE_UP;
    r->reaction_pose_phase=1u;r->reaction_pose_count=1u;
    r->reaction_due_ms=now;r->reaction_generation=17u;
}
int main(void)
{
    comp_pet_behavior_t p={0};
    comp_pet_behavior_interact(&p,COMP_PET_HEAD_PAT,true,0u,100u,29999u);
    assert(!p.caption_selected);
    unsigned selected=0u;
    for(uint32_t i=0u;i<120u;++i) {
        comp_pet_behavior_interact(&p,COMP_PET_HEAD_PAT,true,i<<20u,100u,100000u);
        selected+=p.caption_selected?1u:0u;
    }
    assert(selected==10u);
    comp_pet_behavior_interact(&p,COMP_PET_HEAD_PAT,false,0u,100u,100000u);
    assert(!p.caption_selected);
    for(unsigned i=COMP_PET_PICKUP;i<=COMP_PET_INVERTED;++i) {
        comp_pet_behavior_interact(&p,(comp_pet_interaction_t)i,true,0u,100u,100000u);
        assert(!p.caption_selected);
    }
    comp_runtime_t r;comp_runtime_frame_t first,retry,next;
    phrase(&r,100000u);
    assert(comp_runtime_take_frame(&r,100000u,&first) && first.pet_caption);
    assert(comp_runtime_complete_frame(&r,first.token,false,100500u));
    assert(!r.pet.caption_committed && r.pet.caption_visible_ms==0u);
    assert(comp_runtime_take_frame(&r,101000u,&retry) && retry.pet_caption);
    assert(retry.pet_seed==first.pet_seed && retry.reaction_generation==first.reaction_generation);
    assert(comp_runtime_complete_frame_timed(&r,retry.token,true,101700u,101500u));
    assert(r.pet.caption_committed && r.pet.caption_visible_ms==101500u);
    comp_pet_behavior_caption_visible(&r.pet,101900u);
    assert(r.pet.caption_visible_ms==101500u);
    assert(comp_runtime_take_frame(&r,103000u,&next) && !next.pet_caption);
    comp_pet_behavior_interact(&r.pet,COMP_PET_HEAD_PAT,true,0u,100u,191499u);
    assert(!r.pet.caption_selected);
    comp_pet_behavior_interact(&r.pet,COMP_PET_HEAD_PAT,true,0u,100u,191500u);
    assert(r.pet.caption_selected);
    comp_pet_behavior_idle(&r.pet,0u);
    assert(!r.pet.caption_selected && r.pet.caption_visible_ms==101500u);
    phrase(&r,100000u);
    assert(comp_runtime_take_frame(&r,100000u,&first) && first.pet_caption);
    ++r.reaction_generation;
    assert(comp_runtime_complete_frame(&r,first.token,true,100600u));
    assert(!r.pet.caption_committed && r.pet.caption_visible_ms==0u);
    phrase(&r,100000u);r.reaction_step=2u;
    assert(comp_runtime_take_frame(&r,100000u,&first) && !first.pet_caption);
    phrase(&r,100000u);r.reaction_zone=255u;
    assert(comp_runtime_take_frame(&r,100000u,&first) && !first.pet_caption);
    assert(comp_pet_caption_slot(3u,4u)==UINT8_MAX);
    /* The new feature uses four state bytes; flags fit existing padding. */
    assert(sizeof(comp_pet_behavior_t)==32u);
    printf("PASS: sparse stable caption, first beat, no entropy/no speech, visible-only 90s cooldown, failed retry and stale-generation guard. Runtime=%zu frame=%zu. Software only.\n",
        sizeof(r),sizeof(first));
    return 0;
}
