#include "companion_pet_behavior.h"
#include "companion_pet_profile.h"
#if COMP_PET_PROCEDURAL
#define PET_VISIBLE_FEELING 0x80u
#define PET_COMFORT_WINDOW_MS 20000u
#define PET_ATTENTION_AFTERGLOW_MS 8000u
#define PET_TOUCH_EYE_QUIET_MS 12000u
#define PET_CAPTION_BOOT_QUIET_MS 30000u
#define PET_CAPTION_QUIET_MS 90000u
#define PET_ATTENTION_FAMILY_MASK 15u
#define PET_VISIBLE_PAT_ZONE_MASK 0x70u
_Static_assert(COMP_BROWSER_FAMILY_COUNT<16u,"visible feeling family exceeds private nibble");
_Static_assert(COMP_BROWSER_TAP_ZONE_DOWN<8u,"visible pat zone exceeds private three bits");
void comp_pet_behavior_caption_visible(comp_pet_behavior_t *p,uint32_t visible_ms)
{
    if(p->caption_selected && !p->caption_committed) {
        p->caption_visible_ms=visible_ms;p->caption_committed=true;
    }
}
void comp_pet_behavior_attention_visible(comp_pet_behavior_t *p,
    comp_browser_family_t family,uint32_t visible_ms)
{
    /* Remember the feeling actually shown, including a second reply peak.
     * Posture/shake/idle are not affection and retire a previous afterglow. */
    if((p->interaction>=COMP_PET_HEAD_PAT && p->interaction<=COMP_PET_CHIN) ||
       p->interaction==COMP_PET_GREETING) {
        if((unsigned)family<COMP_BROWSER_FAMILY_COUNT) {
            p->attention_family_code=(uint8_t)((p->attention_family_code&PET_VISIBLE_PAT_ZONE_MASK)|((unsigned)family+1u));
            p->attention_visible_ms=visible_ms;
            return;
        }
    }
    p->attention_family_code&=PET_VISIBLE_PAT_ZONE_MASK;
}
comp_browser_family_t comp_pet_behavior_attention_family(const comp_pet_behavior_t *p,
    comp_browser_family_t fallback,uint32_t now)
{
    const unsigned family=p?(p->attention_family_code&PET_ATTENTION_FAMILY_MASK):0u;
    if(!family || family>COMP_BROWSER_FAMILY_COUNT ||
       now-p->attention_visible_ms>=PET_ATTENTION_AFTERGLOW_MS)return fallback;
    return (comp_browser_family_t)(family-1u);
}
void comp_pet_behavior_visible(comp_pet_behavior_t *p, uint32_t visible_ms)
{
    const bool shaken=p->last_interaction==(COMP_PET_SHAKE|PET_VISIBLE_FEELING) &&
        visible_ms-p->attention_visible_ms<PET_COMFORT_WINDOW_MS;
    /* Incidental posture does not consume a genuinely visible dizzy feeling.
     * A touch which never reaches this visible peak cannot consume it either. */
    if(shaken && (p->interaction==COMP_PET_SETTLE || p->interaction==COMP_PET_TILT ||
                  p->interaction==COMP_PET_INVERTED))return;
    p->repetitions=p->pending_repetitions;
    p->last_interaction=(uint8_t)(p->interaction|
        (p->interaction==COMP_PET_SHAKE?PET_VISIBLE_FEELING:0u));
    if(p->interaction==COMP_PET_HEAD_PAT)
        p->attention_family_code=(uint8_t)((p->attention_family_code&PET_ATTENTION_FAMILY_MASK)|
            ((p->first_zone&7u)<<4u));
    /* Affection's afterglow is already stamped with its actual shown family.
     * Motion needs a first-peak time without inventing an affection family. */
    if(!((p->interaction>=COMP_PET_HEAD_PAT && p->interaction<=COMP_PET_CHIN) ||
         p->interaction==COMP_PET_GREETING))p->attention_visible_ms=visible_ms;
}
void comp_pet_behavior_idle(comp_pet_behavior_t *p,uint32_t entropy)
{
    p->seed=entropy^p->character_seed;p->interaction=COMP_PET_IDLE;p->intensity=38u;
    p->caption_selected=false;p->caption_committed=false;
    p->accent=COMP_PET_ACCENT_NONE;
}
void comp_pet_behavior_set_personality(comp_pet_behavior_t *p,unsigned type,uint32_t seed)
{
    if(!p || type>=16u || !seed)return;
    p->personality_code=(uint8_t)(type+1u);p->character_seed=seed;
    /* Do not replace an in-flight expression, gaze, mouth or accepted seed. */
}
uint32_t comp_pet_behavior_personal_gap(const comp_pet_behavior_t *p,uint32_t baseline)
{
    if(!p || !p->personality_code)return baseline;
    comp_pet_traits_t v=comp_pet_profile_traits(p->personality_code-1u,p->character_seed);
    unsigned percent=110u+v.calmness/2u-v.sociability/4u;
    if(percent<100u)percent=100u;
    return baseline<=UINT32_MAX/percent?baseline*percent/100u:baseline;
}
comp_browser_family_t comp_pet_behavior_personal_idle(const comp_pet_behavior_t *p,
    comp_browser_family_t current,uint32_t entropy)
{
    if(!p || !p->personality_code)return comp_pet_behavior_idle_family(current,entropy);
    comp_pet_traits_t v=comp_pet_profile_traits(p->personality_code-1u,p->character_seed);
    static const uint8_t families[]={COMP_BROWSER_FAMILY_CALM,COMP_BROWSER_FAMILY_CURIOUS,
        COMP_BROWSER_FAMILY_DELIGHTED,COMP_BROWSER_FAMILY_WARM,COMP_BROWSER_FAMILY_PLAYFUL,
        COMP_BROWSER_FAMILY_THOUGHTFUL,COMP_BROWSER_FAMILY_FOCUSED};
    /* Preserve emotional inertia. Personality biases authored choices rather
     * than drawing new faces, flashing more often or creating negative moods. */
    uint16_t weight[7]={(uint16_t)(60u+v.calmness),(uint16_t)(40u+v.curiosity),
        (uint16_t)(40u+v.expressiveness+v.sociability/2u),(uint16_t)(40u+v.sociability+v.expressiveness/2u),
        (uint16_t)(30u+v.expressiveness+(100u-v.calmness)/2u),
        (uint16_t)(130u-v.expressiveness),(uint16_t)(40u+v.calmness+(100u-v.sociability)/3u)};
    uint32_t total=0u;
    for(unsigned i=0;i<7u;i++){if(families[i]==(uint8_t)current)weight[i]=(uint16_t)(weight[i]*3u);total+=weight[i];}
    uint32_t choice=(entropy^p->character_seed)%total;
    for(unsigned i=0;i<7u;i++){if(choice<weight[i])return (comp_browser_family_t)families[i];choice-=weight[i];}
    return COMP_BROWSER_FAMILY_CALM;
}
static void single_affection_peak(comp_pet_behavior_t *p)
{
    /* A shortened cheek reply keeps its authored side peek. Keeping only
     * the closed-eye lead-in made a quiet pet's acknowledgement look like
     * an idle blink. Preserve the existing one-peak budget and dwell. */
    if(p->interaction==COMP_PET_CHEEK &&
       p->second_family==COMP_BROWSER_FAMILY_BASHFUL &&
       (p->second_zone==COMP_BROWSER_TAP_ZONE_LEFT ||
        p->second_zone==COMP_BROWSER_TAP_ZONE_RIGHT)) {
        p->first_family=p->second_family;
        p->first_zone=p->second_zone;
    }
    p->second_family=COMP_BROWSER_FAMILY_NONE;
}
void comp_pet_behavior_apply_personality(comp_pet_behavior_t *p)
{
    if(!p || !p->personality_code || p->accent!=COMP_PET_ACCENT_NONE ||
       p->interaction<COMP_PET_HEAD_PAT || p->interaction>COMP_PET_CHIN)return;
    comp_pet_traits_t v=comp_pet_profile_traits(p->personality_code-1u,p->character_seed);
    if(v.sociability<50u && p->seed%100u>=v.sociability)single_affection_peak(p);
    if(v.expressiveness>=60u && p->interaction==COMP_PET_HEAD_PAT &&
       p->second_family==COMP_BROWSER_FAMILY_NONE && ((p->seed>>9u)&3u)==0u) {
        p->second_family=COMP_BROWSER_FAMILY_WARM;p->second_zone=COMP_BROWSER_TAP_ZONE_CENTER;
        if(p->first_family==p->second_family && p->first_zone==p->second_zone)
            p->second_family=COMP_BROWSER_FAMILY_NONE;
    }
    unsigned extra=v.calmness*3u;
    p->peak_hold_ms=(uint16_t)(p->peak_hold_ms+extra);
}
comp_browser_family_t comp_pet_behavior_idle_family(comp_browser_family_t current,
    uint32_t entropy)
{
    static const uint8_t families[]={COMP_BROWSER_FAMILY_CALM,COMP_BROWSER_FAMILY_CURIOUS,
        COMP_BROWSER_FAMILY_DELIGHTED,COMP_BROWSER_FAMILY_WARM,COMP_BROWSER_FAMILY_PLAYFUL,
        COMP_BROWSER_FAMILY_THOUGHTFUL,COMP_BROWSER_FAMILY_FOCUSED};
    /* Mood has inertia. A decision may keep the same feeling while the daily
     * choreography continues; warmth is not abruptly exchanged for mischief. */
    static const uint8_t weights[7][7]={
        {40u,22u,4u,18u,3u,8u,5u}, {20u,38u,6u,14u,8u,9u,5u},
        {16u,10u,40u,24u,6u,2u,2u}, {22u,10u,12u,43u,5u,5u,3u},
        {14u,24u,10u,18u,28u,4u,2u}, {24u,18u,2u,10u,2u,32u,12u},
        {26u,14u,2u,12u,2u,12u,32u}};
    uint8_t row=0u;
    for(uint8_t i=0u;i<7u;++i)if(families[i]==(uint8_t)current)row=i;
    uint32_t choice=entropy%100u;
    for(uint8_t i=0u;i<7u;++i) {
        if(choice<weights[row][i])return (comp_browser_family_t)families[i];
        choice-=weights[row][i];
    }
    return COMP_BROWSER_FAMILY_CALM;
}
static bool reply_closes_eyes(uint8_t family,uint8_t zone)
{
    /* Existing whole-face peak resources; never redraw their eyelids. */
    return (family==COMP_BROWSER_FAMILY_WARM &&
            (zone==COMP_BROWSER_TAP_ZONE_UP || zone==COMP_BROWSER_TAP_ZONE_DOWN)) ||
           (family==COMP_BROWSER_FAMILY_DELIGHTED && zone==COMP_BROWSER_TAP_ZONE_CENTER) ||
           (family==COMP_BROWSER_FAMILY_BASHFUL && zone==COMP_BROWSER_TAP_ZONE_DOWN) ||
           (family==COMP_BROWSER_FAMILY_PLAYFUL &&
            (zone==COMP_BROWSER_TAP_ZONE_LEFT || zone==COMP_BROWSER_TAP_ZONE_RIGHT));
}
static uint8_t open_reply_zone(uint8_t family,uint8_t zone,uint16_t x)
{
    if(!reply_closes_eyes(family,zone))return zone;
    if(family==COMP_BROWSER_FAMILY_BASHFUL)
        return x<100u?COMP_BROWSER_TAP_ZONE_LEFT:COMP_BROWSER_TAP_ZONE_RIGHT;
    /* Keep the original smile when eyes must stay open. The up pose has
     * a round surprised mouth; down is the authored open-eye smile. */
    return family==COMP_BROWSER_FAMILY_DELIGHTED?
        COMP_BROWSER_TAP_ZONE_DOWN:COMP_BROWSER_TAP_ZONE_CENTER;
}
void comp_pet_behavior_pickup_attention(comp_pet_behavior_t *p,comp_browser_family_t family)
{
    if(p->interaction!=COMP_PET_PICKUP)return;
    p->first_family=(uint8_t)family;
    p->first_zone=open_reply_zone(p->first_family,p->first_zone,100u);
}
void comp_pet_behavior_interact(comp_pet_behavior_t *p,comp_pet_interaction_t input,
    bool available,uint32_t entropy,uint16_t x,uint32_t now)
{
    const bool shaken = p->last_interaction == (COMP_PET_SHAKE | PET_VISIBLE_FEELING) &&
        now - p->attention_visible_ms < PET_COMFORT_WINDOW_MS;
    const bool soothe = shaken && input == COMP_PET_HEAD_PAT;
    const bool recent_pat = input == COMP_PET_HEAD_PAT &&
        (p->last_interaction & 0x7fu) == COMP_PET_HEAD_PAT &&
        now - p->attention_visible_ms < 15000u;
    const uint8_t previous_pat_zone=(p->attention_family_code>>4u)&7u;
    /* The existing afterglow stamp belongs to a genuinely visible affection
     * peak. Frequent contacts should stay attentive, not replay closed eyes.
     * Failed/cancelled candidates never refresh this quiet interval. */
    const bool recent_affection=(p->attention_family_code&PET_ATTENTION_FAMILY_MASK)!=0u &&
        now-p->attention_visible_ms<PET_TOUCH_EYE_QUIET_MS;
    if(available)p->seed=entropy^p->character_seed;
    /* Choose once for the entire accepted intention, using actual entropy.
     * Tracking, posture and routine idle never narrate themselves. Most touch
     * replies stay wordless; the occasional first expressive beat may speak.
     * No fresh entropy means no newly selected caption, not repeated speech. */
    const bool affectionate=(input>=COMP_PET_HEAD_PAT && input<=COMP_PET_CHIN) ||
        input==COMP_PET_GREETING;
    p->caption_selected=available && affectionate && ((entropy>>20u)%12u)==0u &&
        (p->caption_visible_ms?now-p->caption_visible_ms>=PET_CAPTION_QUIET_MS:
            now>=PET_CAPTION_BOOT_QUIET_MS);
    p->caption_committed=false;
    uint8_t repetitions=0u;
    if((p->last_interaction & 0x7fu)==(uint8_t)input && now-p->attention_visible_ms<15000u)
        repetitions=p->repetitions<3u?(uint8_t)(p->repetitions+1u):3u;
    p->pending_repetitions=repetitions;
    p->interaction=(uint8_t)input;
    p->accent=COMP_PET_ACCENT_NONE;
    /* Trace the accepted input separately. Visible history changes only in
     * the matching first-peak completion, not on a render or cancelled input. */
    p->last_input_ms=now;
    p->intensity=(uint8_t)(58u+(p->seed>>5)%13u+repetitions*6u);
    /* Dwell starts at qualified visibility, never at render submission.
     * Give the small expression time to read on paper before settling. */
    p->peak_hold_ms=(uint16_t)(700u+(p->seed>>13)%401u);
    p->second_family=COMP_BROWSER_FAMILY_NONE;
    p->first_zone=p->second_zone=COMP_BROWSER_TAP_ZONE_CENTER;
    switch(input) {
    case COMP_PET_HEAD_PAT:
        p->first_family=COMP_BROWSER_FAMILY_WARM;
        /* A side glance follows the side of this pat; the mirrored original
         * poses are both retained. Repeated pats can still earn the relaxed
         * down pose. The choice belongs to this whole accepted interaction. */
        /* One accepted pat can be a glance, a quiet smile, a relaxed down
         * look or the original up response. Frequent pats settle instead of
         * repeating the same up/down performance. Keep the entire old face. */
        const uint8_t pat=(uint8_t)((p->seed>>3u)&3u);
        p->first_zone=repetitions>=2u?
            ((p->seed>>4u)&1u?COMP_BROWSER_TAP_ZONE_DOWN:COMP_BROWSER_TAP_ZONE_CENTER):
            pat==0u?(x<100u?COMP_BROWSER_TAP_ZONE_LEFT:COMP_BROWSER_TAP_ZONE_RIGHT):
            pat==1u?COMP_BROWSER_TAP_ZONE_CENTER:
            pat==2u?COMP_BROWSER_TAP_ZONE_DOWN:COMP_BROWSER_TAP_ZONE_UP;
        /* Repeated affection settles into the original quiet smile/relaxed
         * eyelids. Avoid replaying the exact preceding head-pat pose, even
         * when the newly accepted entropy chooses it again. This decision is
         * made once per intent; retries retain its whole face and timing. */
        if(recent_pat && p->first_zone==previous_pat_zone)
            p->first_zone=previous_pat_zone==COMP_BROWSER_TAP_ZONE_CENTER?
                COMP_BROWSER_TAP_ZONE_DOWN:COMP_BROWSER_TAP_ZONE_CENTER;
        if(repetitions>=2u)p->accent=COMP_PET_ACCENT_RELIEVED;
        p->peak_hold_ms=(uint16_t)(p->peak_hold_ms+repetitions*35u);
        if(!recent_affection && !soothe) {
            /* A first pat must read as being felt even when the daily face
             * is already warm. Use the retained relaxed whole-eye pose;
             * recent affection keeps the open-eye quiet filter below. */
            p->first_zone=(p->seed&1u)?COMP_BROWSER_TAP_ZONE_UP:COMP_BROWSER_TAP_ZONE_DOWN;
            p->peak_hold_ms=(uint16_t)(1100u+(p->seed>>13)%401u);
        }
        if (soothe) {
            p->accent=COMP_PET_ACCENT_RELIEVED;
            p->first_zone=COMP_BROWSER_TAP_ZONE_CENTER;
            p->second_family=COMP_BROWSER_FAMILY_WARM;
            p->second_zone=COMP_BROWSER_TAP_ZONE_DOWN;
            p->intensity=58u;
            p->peak_hold_ms=(uint16_t)(1000u+(p->seed>>13)%401u);
        }
        break;
    case COMP_PET_CHEEK:
        p->first_family=p->second_family=COMP_BROWSER_FAMILY_BASHFUL;
        p->first_zone=COMP_BROWSER_TAP_ZONE_DOWN;
        /* Choose the existing left/right peek asset itself. The old seed bit
         * only changed cosmetic variation; it did not choose a gaze resource. */
        p->second_zone=x<100u?COMP_BROWSER_TAP_ZONE_LEFT:COMP_BROWSER_TAP_ZONE_RIGHT;
        /* The cheek that was touched decides the direction of the peek. */
        p->seed=(p->seed&~1u)|(x<100u?1u:0u);
        /* A brief original peek sometimes answers on its own. Other cheek
         * contacts retain the authored down-then-peek phrase. No extra beat. */
        if (((p->seed>>4u)&3u)==0u) {
            p->first_zone=p->second_zone;
            p->second_family=COMP_BROWSER_FAMILY_NONE;
        }
        break;
    case COMP_PET_NOSE:
        /* A fourth recent boop gets one gentle protest and warm recovery.
         * No ongoing grudge, penalty or autonomous unhappy mood. */
        if(repetitions>=3u) {
            p->accent=COMP_PET_ACCENT_PROTEST;
            p->first_family=COMP_BROWSER_FAMILY_THOUGHTFUL;
            p->first_zone=COMP_BROWSER_TAP_ZONE_CENTER;
            p->second_family=COMP_BROWSER_FAMILY_WARM;
            p->intensity=58u;
            break;
        }
        /* A sequence of accepted boops earns a mild questioning look, then
         * warmth. It is neither irritation nor a random negative idle mood.
         * Existing curious/warm whole faces are the resource-safe fallback;
         * the generated accent changes only this same first peak. */
        if(repetitions>=2u) {
            p->accent=COMP_PET_ACCENT_PUZZLED;
            p->first_family=COMP_BROWSER_FAMILY_CURIOUS;
            p->first_zone=COMP_BROWSER_TAP_ZONE_UP;
            p->second_family=COMP_BROWSER_FAMILY_WARM;
            p->intensity=58u;
            break;
        }
        /* Welcome a first boop with the familiar heart and open smile.
         * Reserve questions for repeated boops above. Keep the original
         * whole faces, accepted seed and existing two-peak budget. */
        if ((p->seed>>3)%4u==0u) {
            p->first_family=COMP_BROWSER_FAMILY_WARM;
            p->first_zone=COMP_BROWSER_TAP_ZONE_CENTER;
            p->second_family=COMP_BROWSER_FAMILY_DELIGHTED;
        } else if ((p->seed>>3)%4u==1u) {
            /* One accepted poke can earn an original single-eye wink before
             * the familiar smile. Pick its side once for this whole response;
             * use the existing two-route budget, not an extra blink timer. */
            p->first_family=COMP_BROWSER_FAMILY_PLAYFUL;
            p->first_zone=(p->seed&1u)?COMP_BROWSER_TAP_ZONE_LEFT:COMP_BROWSER_TAP_ZONE_RIGHT;
            p->second_family=COMP_BROWSER_FAMILY_DELIGHTED;
        } else {
            p->first_family=COMP_BROWSER_FAMILY_DELIGHTED;
            p->first_zone=(p->seed&1u)?COMP_BROWSER_TAP_ZONE_DOWN:COMP_BROWSER_TAP_ZONE_CENTER;
        }
        break;
    case COMP_PET_CHIN:
        p->first_family=COMP_BROWSER_FAMILY_DELIGHTED;p->first_zone=COMP_BROWSER_TAP_ZONE_CENTER;
        /* Repeated chin affection earns one pleased, quietly proud accent.
         * It shares the existing single-peak route, with no invented game
         * win, extra refresh or timer. Old banks keep their delighted face. */
        if(repetitions>=2u)p->accent=COMP_PET_ACCENT_PROUD;
        /* Repeated chin affection settles into the existing quiet smile.
         * Keep the first replies unchanged; no extra pose or refresh. */
        if(repetitions<2u && p->seed%3u) {
            p->second_family=COMP_BROWSER_FAMILY_PLAYFUL;
            p->second_zone=(p->seed&1u)?COMP_BROWSER_TAP_ZONE_LEFT:COMP_BROWSER_TAP_ZONE_RIGHT;
        }
        break;
    case COMP_PET_GREETING: /* Deliberate menu intent, not a sensor event. */
        /* A deliberate hello uses the retained warm side-look and centre
         * smile; reserve the questioning face for actual curiosity. */
        p->first_family=COMP_BROWSER_FAMILY_WARM;
        p->first_zone=(p->seed&1u)?COMP_BROWSER_TAP_ZONE_LEFT:COMP_BROWSER_TAP_ZONE_RIGHT;
        p->second_family=COMP_BROWSER_FAMILY_WARM;
        break;
    case COMP_PET_PICKUP:
        /* Look toward the holder with the original calm up pose. A lift
         * acknowledges attention without asking an unexplained question or
         * awarding the heart reserved for deliberate affection. */
        p->first_family=COMP_BROWSER_FAMILY_CALM;p->first_zone=COMP_BROWSER_TAP_ZONE_UP;
        p->second_family=COMP_BROWSER_FAMILY_NONE;
        p->peak_hold_ms=(uint16_t)(1200u+(p->seed>>13)%401u);
        break;
    case COMP_PET_SHAKE:
        /* Use the original puzzled whole face, then soften and centre. New
         * generated dizzy artwork is a separate candidate, not a curve edit. */
        p->first_family=COMP_BROWSER_FAMILY_THOUGHTFUL;
        p->second_family=COMP_BROWSER_FAMILY_CALM;
        p->first_zone=(p->seed&1u)?COMP_BROWSER_TAP_ZONE_LEFT:COMP_BROWSER_TAP_ZONE_RIGHT;
        p->intensity=58u;
        /* Let the existing dizzy face be noticed before recovery. A fresh
         * touch can still supersede this motion phrase and soothe it. */
        p->peak_hold_ms=(uint16_t)(2300u+(p->seed>>13)%401u);
        break;
    case COMP_PET_SETTLE:
        /* Settling resumes quiet company with the retained calm whole face.
         * Reserve hearts and the warm smile for deliberate affection. */
        p->first_family=COMP_BROWSER_FAMILY_CALM;
        p->intensity=58u;
        break;
    case COMP_PET_TILT:
        p->first_family=COMP_BROWSER_FAMILY_CURIOUS;
        p->intensity=58u;
        break;
    case COMP_PET_INVERTED:
        /* A short uncertain look for an actual qualified inversion. The old
         * thoughtful whole face remains the safe fallback without V2 art. */
        p->accent=COMP_PET_ACCENT_NERVOUS;
        p->first_family=COMP_BROWSER_FAMILY_THOUGHTFUL;
        p->intensity=58u;
        break;
    default:p->first_family=COMP_BROWSER_FAMILY_CALM;break;
    }
    if(affectionate) {
        if(recent_affection) {
            /* The proud accent is itself an authored wink. It stays available
             * after a quiet gap, rather than closing an eye on every chin tap. */
            if(p->accent==COMP_PET_ACCENT_PROUD)p->accent=COMP_PET_ACCENT_NONE;
            p->first_zone=open_reply_zone(p->first_family,p->first_zone,x);
        }
        const bool first_closed=p->accent==COMP_PET_ACCENT_PROUD ||
            reply_closes_eyes(p->first_family,p->first_zone);
        if(recent_affection || first_closed)
            p->second_zone=open_reply_zone(p->second_family,p->second_zone,x);
        if(input==COMP_PET_HEAD_PAT && recent_pat && p->first_zone==previous_pat_zone) {
            /* Compare the final authored pose after the open-eye filter.
             * Centre/down alternatives can both collapse to centre there.
             * An original open side glance keeps repeated pats distinct
             * without replaying closed eyes or drawing a different face. */
            const bool central=x>=90u && x<=110u;
            const uint32_t choice=p->seed^(p->seed>>11u)^(p->seed>>21u);
            if(previous_pat_zone==COMP_BROWSER_TAP_ZONE_CENTER)
                p->first_zone=(x<90u || (central && (choice&1u)))?
                    COMP_BROWSER_TAP_ZONE_LEFT:COMP_BROWSER_TAP_ZONE_RIGHT;
            else if(central && ((choice>>1u)&1u))
                p->first_zone=previous_pat_zone==COMP_BROWSER_TAP_ZONE_LEFT?
                    COMP_BROWSER_TAP_ZONE_RIGHT:COMP_BROWSER_TAP_ZONE_LEFT;
            else p->first_zone=COMP_BROWSER_TAP_ZONE_CENTER;
        }
        /* A quiet cheek reply can become the same original peek twice.
         * Keep the single pose instead of spending another identical beat. */
        if(recent_affection && p->accent==COMP_PET_ACCENT_NONE &&
           p->second_family==p->first_family && p->second_zone==p->first_zone)
            p->second_family=COMP_BROWSER_FAMILY_NONE;
    }
}
void comp_pet_behavior_apply_activity(comp_pet_behavior_t *p,unsigned level,uint16_t x)
{
    /* One original look-up acknowledges a deliberate lift even in Quiet.
     * Keep its readable hold, omit the extra welcome peak, and let the
     * existing quiet audio policy suppress sound. */
    if(level==0u && p->interaction==COMP_PET_PICKUP) {
        p->second_family=COMP_BROWSER_FAMILY_NONE;
        return;
    }
    /* Reuse the authored complete affection poses and the existing two-peak
     * budget. Never rewrite a shake/soothing response, a boundary accent or
     * a held gaze. The accepted choice survives retries without new entropy. */
    if(p->interaction<COMP_PET_HEAD_PAT || p->interaction>COMP_PET_CHIN ||
       p->accent!=COMP_PET_ACCENT_NONE)return;
    if(level==0u) {
        single_affection_peak(p);
        p->peak_hold_ms=(uint16_t)(p->peak_hold_ms+450u);
    } else if(level==2u && p->interaction==COMP_PET_HEAD_PAT &&
              p->second_family==COMP_BROWSER_FAMILY_NONE) {
        /* A lively pat follows its familiar warm reply with an open-eye
         * peek toward the touched side; retain the original whole-face style. */
        p->second_family=COMP_BROWSER_FAMILY_WARM;
        p->second_zone=x<100u?COMP_BROWSER_TAP_ZONE_LEFT:COMP_BROWSER_TAP_ZONE_RIGHT;
        if(p->first_zone==p->second_zone)p->second_zone=COMP_BROWSER_TAP_ZONE_CENTER;
    }
}
#endif
