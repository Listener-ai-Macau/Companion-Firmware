#include "companion_pet_behavior.h"
#include "companion_pet_profile.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(void)
{
    uint32_t signatures[16];
    for(unsigned type=0;type<16u;type++) {
        comp_pet_behavior_t p={0};comp_pet_behavior_set_personality(&p,type,0x12345678u);
        uint32_t hash=2166136261u,holds=0u,two=0u;
        for(uint32_t entropy=1u;entropy<=4096u;entropy++) {
            memset(&p,0,sizeof(p));comp_pet_behavior_set_personality(&p,type,0x12345678u);
            comp_pet_behavior_interact(&p,COMP_PET_HEAD_PAT,true,entropy,100u,40000u);
            uint8_t original_family=p.first_family,original_zone=p.first_zone;
            comp_pet_behavior_apply_personality(&p);
            assert(p.first_family==original_family && p.first_zone==original_zone);
            assert(p.peak_hold_ms>=800u && p.peak_hold_ms<4000u);
            holds+=p.peak_hold_ms;two+=p.second_family!=COMP_BROWSER_FAMILY_NONE;
            comp_pet_behavior_t quiet=p;comp_pet_behavior_apply_activity(&quiet,0u,100u);
            assert(quiet.second_family==COMP_BROWSER_FAMILY_NONE);
            unsigned family=(unsigned)comp_pet_behavior_personal_idle(&p,COMP_BROWSER_FAMILY_CALM,entropy);
            assert(family<COMP_BROWSER_FAMILY_COUNT && family!=COMP_BROWSER_FAMILY_SLEEPY);
            hash=(hash^family)*16777619u;
        }
        signatures[type]=hash^holds^two;
        for(unsigned prior=0;prior<type;prior++)assert(signatures[prior]!=signatures[type]);
        assert(comp_pet_behavior_personal_gap(&p,28000u)>=28000u);
        assert(comp_pet_behavior_personal_gap(&p,UINT32_MAX)==UINT32_MAX);
        comp_pet_behavior_interact(&p,COMP_PET_SHAKE,true,99u,100u,50000u);
        comp_pet_behavior_t shake=p;comp_pet_behavior_apply_personality(&p);
        assert(!memcmp(&p,&shake,sizeof(p)));
    }
    comp_pet_behavior_t legacy={0};
    assert(comp_pet_behavior_personal_gap(&legacy,28000u)==28000u);
    for(uint32_t n=0u;n<100u;n++)assert(comp_pet_behavior_personal_idle(&legacy,COMP_BROWSER_FAMILY_CALM,n)==
        comp_pet_behavior_idle_family(COMP_BROWSER_FAMILY_CALM,n));
    puts("16 distinct deterministic behavior distributions; original first poses, quiet priority, shake and baseline cadence preserved");
    puts("PASS_PERSONALITY_BEHAVIOR_ONLY_NO_PHYSICAL_OR_FULL_RUNTIME_ACCEPTANCE");return 0;
}
