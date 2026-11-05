#ifndef COMPANION_PET_PLAY_H
#define COMPANION_PET_PLAY_H
#include <stdbool.h>
#include <stdint.h>

/* One explicitly requested three-turn activity. Only qualified visible cue
 * completion accepts an answer. No score, chores, saved state or timer
 * driven animation; the ordinary pet transaction still owns every picture. */
enum { COMP_PET_PLAY_OFF, COMP_PET_PLAY_NEXT, COMP_PET_PLAY_CUE,
       COMP_PET_PLAY_WAIT, COMP_PET_PLAY_REPLY, COMP_PET_PLAY_ENDED,
       COMP_PET_PLAY_ORIENT, COMP_PET_PLAY_AIM };
#define COMP_PET_PLAY_ROUNDS 3u
_Static_assert(COMP_PET_PLAY_ROUNDS*2u<=8u,"pet play phrase exceeds existing byte");
enum { COMP_PET_PLAY_LEFT, COMP_PET_PLAY_RIGHT,
       COMP_PET_PLAY_UP, COMP_PET_PLAY_DOWN };
enum { COMP_PET_PLAY_CAPTION_NONE, COMP_PET_PLAY_CAPTION_CUE,
       COMP_PET_PLAY_CAPTION_RETRY, COMP_PET_PLAY_CAPTION_FOUND,
       COMP_PET_PLAY_CAPTION_ENDED, COMP_PET_PLAY_CAPTION_RECORD_STOP,
       COMP_PET_PLAY_CAPTION_NEXT };
typedef struct {
    uint32_t generation, due_ms;
    uint8_t phase, round, pattern;
    uint8_t answer_contact : 1;
    uint8_t retry_hint : 1;
    uint8_t home_family : 4; /* Pre-activity daily feeling, in the spare nibble. */
} comp_pet_play_t;
/* Three two-bit directions fit the existing byte. Select the complete phrase
 * once; adjacent rounds differ and a failed cue never draws a new pattern. */
static inline uint8_t comp_pet_play_pattern(uint32_t entropy,bool vertical)
{
    const unsigned count=vertical?4u:2u;
    /* Start with an easier-to-read horizontal look. Later turns retain the
     * installed up/down artwork; one phrase still draws its pattern once. */
    unsigned direction=entropy%2u,pattern=direction;
    entropy/=2u;
    for(unsigned round=1u;round<COMP_PET_PLAY_ROUNDS;++round) {
        direction=(direction+1u+entropy%(count-1u))%count;
        entropy/=count-1u;
        pattern|=direction<<(round*2u);
    }
    return (uint8_t)pattern;
}
static inline unsigned comp_pet_play_direction(const comp_pet_play_t *p)
{ return (p->pattern>>(p->round*2u))&3u; }
static inline uint16_t comp_pet_play_target_x(const comp_pet_play_t *p)
{
    const unsigned direction=comp_pet_play_direction(p);
    return direction==COMP_PET_PLAY_LEFT?44u:direction==COMP_PET_PLAY_RIGHT?156u:100u;
}
static inline uint16_t comp_pet_play_target_y(const comp_pet_play_t *p)
{
    const unsigned direction=comp_pet_play_direction(p);
    /* Deliberate UP uses the existing outer authored look (gy0), as LEFT,
     * RIGHT and DOWN already do. The old64 target chose only gy2. */
    return direction==COMP_PET_PLAY_UP?50u:direction==COMP_PET_PLAY_DOWN?140u:100u;
}
static inline bool comp_pet_play_answer(const comp_pet_play_t *p,uint16_t x,uint16_t y)
{
    /* Keep status/recording edges and an ambiguous central/diagonal touch out
     * of the answer zones. A different tap keeps the same visible cue. */
    /* The four visible targets live above the bottom caption. In particular,
     * the lower target must be answerable where it is drawn, without opening
     * the status rail or the bottom recording shortcut corners. */
    if(x<12u || x>188u || y<45u || y>=172u ||
       (y>=156u && (x<76u || x>124u)))return false;
    const int dx=(int)x-100,dy=(int)y-100;
    const unsigned ax=(unsigned)(dx<0?-dx:dx),ay=(unsigned)(dy<0?-dy:dy);
    switch(comp_pet_play_direction(p)) {
    case COMP_PET_PLAY_LEFT:return dx<=-24 && ax>=ay+12u;
    case COMP_PET_PLAY_RIGHT:return dx>=24 && ax>=ay+12u;
    case COMP_PET_PLAY_UP:return dy<=-24 && ay>=ax+12u;
    case COMP_PET_PLAY_DOWN:return dy>=24 && ay>=ax+12u;
    default:return false;
    }
}
#endif
