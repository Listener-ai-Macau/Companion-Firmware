#include "motion_coordinator.h"

#include <stddef.h>
#include <string.h>

#define MOTION_LIVING_SEED 0x4d3c2b1au
#define MOTION_ACTION_BIT(action) (1u << (uint32_t)(action))
#define MOTION_SCENES_ENABLED 0x80u
#define MOTION_SCENE_ID_MASK 0x7fu
#define MOTION_SCENE_LOOK 0xfeu
#define MOTION_SCENE_OTHER_SIDE 0xfdu

#define MOTION_OLD_EPISODE_OFFSET ((4u*sizeof(bool) + \
    sizeof(comp_epaper_motion_family_t)+sizeof(comp_epaper_motion_phase_t)+ \
    sizeof(comp_epaper_motion_action_t)+11u+COMP_EPAPER_MOTION_ACTION_COUNT+3u)&~3u)
_Static_assert(offsetof(comp_epaper_motion_coordinator_t, episode)==MOTION_OLD_EPISODE_OFFSET,
               "scene state must fit original coordinator prefix");
_Static_assert(sizeof(comp_epaper_motion_coordinator_t)==MOTION_OLD_EPISODE_OFFSET + \
    11u*sizeof(uint32_t)+((sizeof(comp_epaper_motion_cancel_reason_t)+3u)&~3u),
               "scene coordinator RAM envelope changed");

typedef struct {
    const comp_epaper_motion_phase_t *phases;
    uint8_t phase_count;
    uint8_t cooldown;
} motion_action_definition_t;

static const comp_epaper_motion_phase_t k_notice_left_phases[] = {
    COMP_EPAPER_MOTION_PHASE_ORIENT,
    COMP_EPAPER_MOTION_PHASE_ANTICIPATE,
    COMP_EPAPER_MOTION_PHASE_ACCENT,
    COMP_EPAPER_MOTION_PHASE_FOLLOW,
    COMP_EPAPER_MOTION_PHASE_SETTLE,
};
static const comp_epaper_motion_phase_t k_notice_right_phases[] = {
    COMP_EPAPER_MOTION_PHASE_ORIENT,
    COMP_EPAPER_MOTION_PHASE_ANTICIPATE,
    COMP_EPAPER_MOTION_PHASE_ACCENT,
    COMP_EPAPER_MOTION_PHASE_FOLLOW,
    COMP_EPAPER_MOTION_PHASE_SETTLE,
};
static const comp_epaper_motion_phase_t k_soften_phases[] = {
    COMP_EPAPER_MOTION_PHASE_ANTICIPATE,
    COMP_EPAPER_MOTION_PHASE_ACCENT,
    COMP_EPAPER_MOTION_PHASE_FOLLOW,
    COMP_EPAPER_MOTION_PHASE_SETTLE,
};
static const comp_epaper_motion_phase_t k_small_breath_phases[] = {
    COMP_EPAPER_MOTION_PHASE_ANTICIPATE,
    COMP_EPAPER_MOTION_PHASE_ACCENT,
    COMP_EPAPER_MOTION_PHASE_FOLLOW,
    COMP_EPAPER_MOTION_PHASE_SETTLE,
};
static const comp_epaper_motion_phase_t k_listen_up_phases[] = {
    COMP_EPAPER_MOTION_PHASE_ORIENT,
    COMP_EPAPER_MOTION_PHASE_ANTICIPATE,
    COMP_EPAPER_MOTION_PHASE_ACCENT,
    COMP_EPAPER_MOTION_PHASE_FOLLOW,
    COMP_EPAPER_MOTION_PHASE_SETTLE,
};
static const comp_epaper_motion_phase_t k_question_phases[] = {
    COMP_EPAPER_MOTION_PHASE_ORIENT,
    COMP_EPAPER_MOTION_PHASE_ANTICIPATE,
    COMP_EPAPER_MOTION_PHASE_ACCENT,
    COMP_EPAPER_MOTION_PHASE_SETTLE,
};
static const comp_epaper_motion_phase_t k_beam_phases[] = {
    COMP_EPAPER_MOTION_PHASE_ANTICIPATE,
    COMP_EPAPER_MOTION_PHASE_ACCENT,
    COMP_EPAPER_MOTION_PHASE_FOLLOW,
    COMP_EPAPER_MOTION_PHASE_SETTLE,
};
static const comp_epaper_motion_phase_t k_tease_grin_phases[] = {
    COMP_EPAPER_MOTION_PHASE_ORIENT,
    COMP_EPAPER_MOTION_PHASE_ACCENT,
    COMP_EPAPER_MOTION_PHASE_FOLLOW,
    COMP_EPAPER_MOTION_PHASE_SETTLE,
};
static const comp_epaper_motion_phase_t k_yawn_phases[] = {
    COMP_EPAPER_MOTION_PHASE_ANTICIPATE,
    COMP_EPAPER_MOTION_PHASE_ACCENT,
    COMP_EPAPER_MOTION_PHASE_FOLLOW,
    COMP_EPAPER_MOTION_PHASE_SETTLE,
};
static const comp_epaper_motion_phase_t k_shy_smile_phases[] = {
    COMP_EPAPER_MOTION_PHASE_ANTICIPATE,
    COMP_EPAPER_MOTION_PHASE_ACCENT,
    COMP_EPAPER_MOTION_PHASE_SETTLE,
};
static const comp_epaper_motion_phase_t k_ponder_phases[] = {
    COMP_EPAPER_MOTION_PHASE_ORIENT,
    COMP_EPAPER_MOTION_PHASE_ANTICIPATE,
    COMP_EPAPER_MOTION_PHASE_ACCENT,
    COMP_EPAPER_MOTION_PHASE_SETTLE,
};
static const comp_epaper_motion_phase_t k_refocus_phases[] = {
    COMP_EPAPER_MOTION_PHASE_ORIENT,
    COMP_EPAPER_MOTION_PHASE_ACCENT,
    COMP_EPAPER_MOTION_PHASE_SETTLE,
};
static const comp_epaper_motion_phase_t k_startle_phases[] = {
    COMP_EPAPER_MOTION_PHASE_ORIENT,
    COMP_EPAPER_MOTION_PHASE_ACCENT,
    COMP_EPAPER_MOTION_PHASE_FOLLOW,
    COMP_EPAPER_MOTION_PHASE_SETTLE,
};

#define ACTION_DEF(phases_value, cooldown_value) \
    { phases_value, (uint8_t)(sizeof(phases_value) / sizeof((phases_value)[0])), cooldown_value }

static const motion_action_definition_t k_action_definitions[COMP_EPAPER_MOTION_ACTION_COUNT] = {
    [COMP_EPAPER_MOTION_ACTION_NOTICE_LEFT] = ACTION_DEF(k_notice_left_phases, 3u),
    [COMP_EPAPER_MOTION_ACTION_NOTICE_RIGHT] = ACTION_DEF(k_notice_right_phases, 3u),
    [COMP_EPAPER_MOTION_ACTION_SOFTEN] = ACTION_DEF(k_soften_phases, 2u),
    [COMP_EPAPER_MOTION_ACTION_SMALL_BREATH] = ACTION_DEF(k_small_breath_phases, 3u),
    [COMP_EPAPER_MOTION_ACTION_LISTEN_UP] = ACTION_DEF(k_listen_up_phases, 4u),
    [COMP_EPAPER_MOTION_ACTION_QUESTION] = ACTION_DEF(k_question_phases, 4u),
    [COMP_EPAPER_MOTION_ACTION_BEAM] = ACTION_DEF(k_beam_phases, 4u),
    [COMP_EPAPER_MOTION_ACTION_TEASE_GRIN] = ACTION_DEF(k_tease_grin_phases, 4u),
    [COMP_EPAPER_MOTION_ACTION_YAWN] = ACTION_DEF(k_yawn_phases, 5u),
    [COMP_EPAPER_MOTION_ACTION_SHY_SMILE] = ACTION_DEF(k_shy_smile_phases, 5u),
    [COMP_EPAPER_MOTION_ACTION_PONDER] = ACTION_DEF(k_ponder_phases, 5u),
    [COMP_EPAPER_MOTION_ACTION_REFOCUS] = ACTION_DEF(k_refocus_phases, 5u),
    [COMP_EPAPER_MOTION_ACTION_STARTLE] = ACTION_DEF(k_startle_phases, 5u),
};

static const uint32_t k_family_action_masks[COMP_EPAPER_MOTION_FAMILY_COUNT] = {
    [COMP_EPAPER_MOTION_FAMILY_CALM] =
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_NOTICE_LEFT) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_NOTICE_RIGHT) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_SOFTEN) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_SMALL_BREATH) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_LISTEN_UP),
    [COMP_EPAPER_MOTION_FAMILY_CURIOUS] =
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_NOTICE_LEFT) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_NOTICE_RIGHT) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_LISTEN_UP) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_QUESTION),
    [COMP_EPAPER_MOTION_FAMILY_DELIGHTED] =
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_NOTICE_LEFT) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_NOTICE_RIGHT) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_SOFTEN) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_BEAM),
    [COMP_EPAPER_MOTION_FAMILY_WARM] =
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_NOTICE_LEFT) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_NOTICE_RIGHT) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_SOFTEN) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_LISTEN_UP),
    [COMP_EPAPER_MOTION_FAMILY_PLAYFUL] =
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_NOTICE_LEFT) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_NOTICE_RIGHT) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_TEASE_GRIN),
    [COMP_EPAPER_MOTION_FAMILY_SLEEPY] =
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_SMALL_BREATH) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_YAWN),
    [COMP_EPAPER_MOTION_FAMILY_BASHFUL] =
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_NOTICE_LEFT) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_NOTICE_RIGHT) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_SOFTEN) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_SHY_SMILE),
    [COMP_EPAPER_MOTION_FAMILY_THOUGHTFUL] =
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_NOTICE_LEFT) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_NOTICE_RIGHT) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_LISTEN_UP) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_PONDER),
    [COMP_EPAPER_MOTION_FAMILY_FOCUSED] =
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_NOTICE_LEFT) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_NOTICE_RIGHT) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_LISTEN_UP) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_REFOCUS),
    [COMP_EPAPER_MOTION_FAMILY_ALERT] =
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_NOTICE_LEFT) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_NOTICE_RIGHT) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_LISTEN_UP) |
        MOTION_ACTION_BIT(COMP_EPAPER_MOTION_ACTION_STARTLE),
};

/* An intent contains one or two complete original actions. Family masks below
 * reject recipes without authored assets; scenes do not manufacture emotion,
 * mouth curves, directional states or new panel commands. LOOK's side is fixed
 * for the scene; OTHER_SIDE deliberately surveys the remaining side. */
typedef struct { uint8_t actions[2], count, weight; } motion_scene_definition_t;
static const motion_scene_definition_t k_scenes[] = {
    {{MOTION_SCENE_LOOK,MOTION_SCENE_OTHER_SIDE},2u,2u}, /* look around */
    {{MOTION_SCENE_LOOK,COMP_EPAPER_MOTION_ACTION_SOFTEN},2u,5u}, /* company */
    {{COMP_EPAPER_MOTION_ACTION_LISTEN_UP,COMP_EPAPER_MOTION_ACTION_SOFTEN},2u,3u},
    {{MOTION_SCENE_LOOK,COMP_EPAPER_MOTION_ACTION_QUESTION},2u,4u},
    {{MOTION_SCENE_LOOK,COMP_EPAPER_MOTION_ACTION_BEAM},2u,4u},
    {{MOTION_SCENE_LOOK,COMP_EPAPER_MOTION_ACTION_TEASE_GRIN},2u,4u},
    {{COMP_EPAPER_MOTION_ACTION_SMALL_BREATH,COMP_EPAPER_MOTION_ACTION_YAWN},2u,3u},
    {{MOTION_SCENE_LOOK,COMP_EPAPER_MOTION_ACTION_SHY_SMILE},2u,4u},
    {{COMP_EPAPER_MOTION_ACTION_LISTEN_UP,COMP_EPAPER_MOTION_ACTION_PONDER},2u,4u},
    {{COMP_EPAPER_MOTION_ACTION_LISTEN_UP,COMP_EPAPER_MOTION_ACTION_REFOCUS},2u,4u},
    {{COMP_EPAPER_MOTION_ACTION_LISTEN_UP,COMP_EPAPER_MOTION_ACTION_STARTLE},2u,3u},
    {{COMP_EPAPER_MOTION_ACTION_SMALL_BREATH,0u},1u,4u}, /* quiet pause */
};

static bool motion_scenes_enabled(const comp_epaper_motion_coordinator_t *c)
{ return (c->scene & MOTION_SCENES_ENABLED)!=0u; }

static const motion_scene_definition_t *motion_scene(
    const comp_epaper_motion_coordinator_t *c)
{
    unsigned id=c->scene & MOTION_SCENE_ID_MASK;
    return id && id<=sizeof(k_scenes)/sizeof(k_scenes[0])?&k_scenes[id-1u]:NULL;
}

static comp_epaper_motion_action_t motion_scene_action(
    const comp_epaper_motion_coordinator_t *c, unsigned scene, unsigned step)
{
    uint8_t action=k_scenes[scene].actions[step];
    if(action==MOTION_SCENE_LOOK || action==MOTION_SCENE_OTHER_SIDE) {
        bool right=(c->variation & 1u)!=0u;
        if(action==MOTION_SCENE_OTHER_SIDE)right=!right;
        return right?COMP_EPAPER_MOTION_ACTION_NOTICE_RIGHT:COMP_EPAPER_MOTION_ACTION_NOTICE_LEFT;
    }
    return (comp_epaper_motion_action_t)action;
}

static const char *const k_family_names[COMP_EPAPER_MOTION_FAMILY_COUNT] = {
    "calm", "curious", "delighted", "warm", "playful",
    "sleepy", "bashful", "thoughtful", "focused", "alert",
};
static const char *const k_action_names[COMP_EPAPER_MOTION_ACTION_COUNT] = {
    "rest", "notice_left", "notice_right", "soften", "small_breath",
    "listen_up", "question", "beam", "tease_grin", "yawn", "shy_smile",
    "ponder", "refocus", "startle",
};

static bool motion_time_reached(uint32_t now_ms, uint32_t deadline_ms)
{
    return (int32_t)(now_ms - deadline_ms) >= 0;
}

static uint32_t motion_advance_absolute_deadline(uint32_t due_ms,
                                                 uint32_t interval_ms,
                                                 uint32_t now_ms)
{
    uint32_t next_ms;

    if (interval_ms == 0u) {
        interval_ms = COMP_EPAPER_MOTION_CADENCE_MS;
    }
    next_ms = due_ms + interval_ms;
    while (motion_time_reached(now_ms, next_ms)) {
        next_ms += interval_ms;
    }
    return next_ms;
}

static uint32_t motion_imul(uint32_t left, uint32_t right)
{
    return left * right;
}

static uint32_t motion_seeded_hash(comp_epaper_motion_family_t family,
                                   int32_t value,
                                   uint32_t channel)
{
    const char *name = comp_epaper_motion_family_name(family);
    uint32_t hash = MOTION_LIVING_SEED ^
                    motion_imul((uint32_t)value + 1u, 2246822519u) ^
                    motion_imul(channel + 1u, 3266489917u);

    while (*name != '\0') {
        hash = motion_imul(hash ^ (uint8_t)*name++, 16777619u);
    }
    hash ^= hash >> 15u;
    hash = motion_imul(hash, 2246822519u);
    hash ^= hash >> 13u;
    return hash;
}

static uint32_t motion_seeded_range(comp_epaper_motion_family_t family,
                                    int32_t value,
                                    uint32_t channel,
                                    uint32_t count)
{
    return count == 0u
               ? 0u
               : (uint32_t)(((uint64_t)motion_seeded_hash(family, value, channel) *
                             (uint64_t)count) >>
                            32u);
}

static uint32_t blink_seeded_hash(int32_t value, uint32_t channel)
{
    static const char name[] = "blink";
    uint32_t hash = MOTION_LIVING_SEED ^
                    motion_imul((uint32_t)value + 1u, 2246822519u) ^
                    motion_imul(channel + 1u, 3266489917u);

    for (size_t index = 0u; name[index] != '\0'; ++index) {
        hash = motion_imul(hash ^ (uint8_t)name[index], 16777619u);
    }
    hash ^= hash >> 15u;
    hash = motion_imul(hash, 2246822519u);
    hash ^= hash >> 13u;
    return hash;
}

static uint8_t blink_interval_commits(
    const comp_epaper_natural_blink_scheduler_t *scheduler,
    uint32_t epoch)
{
    uint32_t index =
        (uint32_t)(((uint64_t)blink_seeded_hash((int32_t)epoch, 3u) *
                    scheduler->interval_count) >>
                   32u);

    return scheduler->interval_commits[index];
}

static uint8_t motion_seeded_variant(comp_epaper_motion_family_t family,
                                     uint32_t salt)
{
    static const uint8_t variants[] = {0u, 1u, 2u, 1u, 0u, 2u, 1u, 2u, 0u, 1u};
    const char *name = comp_epaper_motion_family_name(family);
    uint32_t value = 2166136261u ^ salt;

    while (*name != '\0') {
        value = motion_imul(value ^ (uint8_t)*name++, 16777619u);
    }
    if ((int32_t)value < 0) {
        value = 0u - value;
    }
    return variants[value % (sizeof(variants) / sizeof(variants[0]))];
}

static uint32_t motion_next_token(comp_epaper_motion_coordinator_t *coordinator)
{
    uint32_t token = coordinator->next_token++;

    if (token == 0u) {
        token = coordinator->next_token++;
    }
    if (coordinator->next_token == 0u) {
        coordinator->next_token = 1u;
    }
    return token;
}

static bool motion_action_is_recent(const comp_epaper_motion_coordinator_t *coordinator,
                                    comp_epaper_motion_action_t action,
                                    uint8_t lookback)
{
    uint8_t count = coordinator->recent_action_count;
    uint8_t start = count > lookback ? (uint8_t)(count - lookback) : 0u;

    for (uint8_t index = start; index < count; ++index) {
        if (coordinator->recent_actions[index] == (uint8_t)action) {
            return true;
        }
    }
    return false;
}

static uint8_t motion_action_weight(const comp_epaper_motion_coordinator_t *coordinator,
                                   comp_epaper_motion_action_t action)
{
    static const uint8_t base[COMP_EPAPER_MOTION_ACTION_COUNT]=
        {0u,4u,4u,6u,5u,3u,2u,2u,2u,2u,2u,2u,2u,2u};
    if(coordinator->recent_action_count==0u)return base[action];
    comp_epaper_motion_action_t previous=(comp_epaper_motion_action_t)
        coordinator->recent_actions[coordinator->recent_action_count-1u];
    bool noticed=previous==COMP_EPAPER_MOTION_ACTION_NOTICE_LEFT ||
                 previous==COMP_EPAPER_MOTION_ACTION_NOTICE_RIGHT;
    bool looking=action==COMP_EPAPER_MOTION_ACTION_NOTICE_LEFT ||
                 action==COMP_EPAPER_MOTION_ACTION_NOTICE_RIGHT;
    /* Attention leads to an expression or a soft return. Avoid looking left,
     * then right as unrelated slide changes, without forcing a fixed loop. */
    if(noticed) {
        if(looking)return 1u;
        if(action==COMP_EPAPER_MOTION_ACTION_SOFTEN)return 8u;
        if(action==COMP_EPAPER_MOTION_ACTION_LISTEN_UP ||
           action==COMP_EPAPER_MOTION_ACTION_QUESTION)return 6u;
        return (uint8_t)(base[action]+3u);
    }
    if(previous>=COMP_EPAPER_MOTION_ACTION_QUESTION) {
        if(action==COMP_EPAPER_MOTION_ACTION_SOFTEN)return 9u;
        if(action==COMP_EPAPER_MOTION_ACTION_SMALL_BREATH)return 7u;
    }
    return base[action];
}

static comp_epaper_motion_action_t motion_choose_action(
    const comp_epaper_motion_coordinator_t *coordinator,
    int32_t salt)
{
    comp_epaper_motion_action_t candidates[COMP_EPAPER_MOTION_ACTION_COUNT];
    uint8_t count = 0u;
    uint32_t mask = k_family_action_masks[coordinator->family];

    for (uint32_t action = COMP_EPAPER_MOTION_ACTION_NOTICE_LEFT;
         action < COMP_EPAPER_MOTION_ACTION_COUNT;
         ++action) {
        if ((mask & MOTION_ACTION_BIT(action)) != 0u &&
            coordinator->cooldowns[action] == 0u &&
            !motion_action_is_recent(coordinator,
                                     (comp_epaper_motion_action_t)action,
                                     2u)) {
            candidates[count++] = (comp_epaper_motion_action_t)action;
        }
    }
    if (count == 0u) {
        for (uint32_t action = COMP_EPAPER_MOTION_ACTION_NOTICE_LEFT;
             action < COMP_EPAPER_MOTION_ACTION_COUNT;
             ++action) {
            if ((mask & MOTION_ACTION_BIT(action)) != 0u &&
                !motion_action_is_recent(coordinator,
                                         (comp_epaper_motion_action_t)action,
                                         1u)) {
                candidates[count++] = (comp_epaper_motion_action_t)action;
            }
        }
    }
    if(count==0u)return COMP_EPAPER_MOTION_ACTION_SOFTEN;
    uint32_t total=0u;
    for(uint8_t i=0u;i<count;++i)total+=motion_action_weight(coordinator,candidates[i]);
    uint32_t choice=motion_seeded_range(coordinator->family,salt,35u,total);
    for(uint8_t i=0u;i<count;++i) {
        uint8_t weight=motion_action_weight(coordinator,candidates[i]);
        if(choice<weight)return candidates[i];
        choice-=weight;
    }
    return candidates[count-1u];
}

static bool motion_scene_eligible(const comp_epaper_motion_coordinator_t *c,
                                  unsigned scene, unsigned pass)
{
    if(pass<2u && c->previous_scene==scene+1u)return false;
    for(unsigned step=0u;step<k_scenes[scene].count;++step) {
        comp_epaper_motion_action_t action=motion_scene_action(c,scene,step);
        if(!(k_family_action_masks[c->family]&MOTION_ACTION_BIT(action)))return false;
        /* A whole scene is accepted once. Its continuation does not reselect
         * after the first action has changed the recent-action history. */
        if(pass==0u && (c->cooldowns[action]>1u || motion_action_is_recent(c,action,2u)))
            return false;
    }
    return true;
}

static void motion_choose_scene(comp_epaper_motion_coordinator_t *c)
{
    for(unsigned pass=0u;pass<3u;++pass) {
        uint32_t total=0u;
        for(unsigned i=0u;i<sizeof(k_scenes)/sizeof(k_scenes[0]);++i)
            if(motion_scene_eligible(c,i,pass))total+=k_scenes[i].weight;
        if(!total)continue;
        uint32_t choice=motion_seeded_range(c->family,(int32_t)c->episode,61u,total);
        for(unsigned i=0u;i<sizeof(k_scenes)/sizeof(k_scenes[0]);++i) {
            if(!motion_scene_eligible(c,i,pass))continue;
            if(choice<k_scenes[i].weight) {
                c->scene=(uint8_t)(MOTION_SCENES_ENABLED| (i+1u));
                c->scene_step=0u;return;
            }
            choice-=k_scenes[i].weight;
        }
    }
    /* Every registered family has a survey or quiet-pause recipe. Refuse an
     * unsupported scene rather than request a missing expression resource. */
    c->scene=MOTION_SCENES_ENABLED;c->scene_step=0u;
}

static int32_t motion_action_salt(const comp_epaper_motion_coordinator_t *c)
{ return (int32_t)(c->episode*131u+(motion_scenes_enabled(c)?c->scene_step*977u:0u)); }

static uint8_t motion_phase_dwell(comp_epaper_motion_family_t family,
                                  int32_t salt,
                                  uint8_t action_step,
                                  comp_epaper_motion_phase_t phase)
{
    static const uint8_t minimum[COMP_EPAPER_MOTION_PHASE_COUNT] =
        {1u, 1u, 1u, 2u, 1u, 2u};
    static const uint8_t maximum[COMP_EPAPER_MOTION_PHASE_COUNT] =
        {1u, 3u, 3u, 4u, 4u, 4u};
    uint8_t span = (uint8_t)(maximum[phase] - minimum[phase] + 1u);

    return (uint8_t)(minimum[phase] +
                     motion_seeded_range(family, salt, 40u + action_step, span));
}

static void motion_prepare_episode(comp_epaper_motion_coordinator_t *coordinator)
{
    int32_t salt = (int32_t)(coordinator->episode * 131u);
    uint8_t quiet_commits =
        (uint8_t)(2u + motion_seeded_range(coordinator->family, salt, 31u, 3u));

    if (quiet_commits == coordinator->previous_quiet_commits) {
        quiet_commits = (uint8_t)(2u + ((quiet_commits - 2u + 1u) % 3u));
    }
    coordinator->previous_quiet_commits = quiet_commits;
    coordinator->quiet_commits = quiet_commits;
    coordinator->phrase =
        (uint8_t)motion_seeded_range(coordinator->family, salt, 34u, 3u);
    coordinator->variation =
        motion_seeded_variant(coordinator->family, coordinator->episode * 17u);
    coordinator->phrase = (uint8_t)((coordinator->phrase +
                                     coordinator->variation) %
                                    3u);
    if(motion_scenes_enabled(coordinator))motion_choose_scene(coordinator);
    coordinator->next_phase = COMP_EPAPER_MOTION_PHASE_HOLD;
    coordinator->action = COMP_EPAPER_MOTION_ACTION_REST;
    coordinator->dwell_commits = quiet_commits;
    coordinator->action_step = 0u;
    coordinator->action_phase_count = 0u;
    coordinator->episode_prepared = true;
}

static void motion_prepare_action(comp_epaper_motion_coordinator_t *coordinator)
{
    int32_t salt = motion_action_salt(coordinator);
    const motion_action_definition_t *definition;

    for (uint32_t action = COMP_EPAPER_MOTION_ACTION_NOTICE_LEFT;
         action < COMP_EPAPER_MOTION_ACTION_COUNT;
         ++action) {
        if (coordinator->cooldowns[action] > 0u) {
            coordinator->cooldowns[action]--;
        }
    }
    const motion_scene_definition_t *scene=motion_scene(coordinator);
    coordinator->action = scene && coordinator->scene_step<scene->count ?
        motion_scene_action(coordinator,(coordinator->scene & MOTION_SCENE_ID_MASK)-1u,
                            coordinator->scene_step) : motion_choose_action(coordinator,salt);
    definition = &k_action_definitions[coordinator->action];
    if(!motion_scenes_enabled(coordinator)) {
        coordinator->phrase =
            (uint8_t)motion_seeded_range(coordinator->family, salt, 36u, 3u);
        coordinator->variation =
            motion_seeded_variant(coordinator->family, coordinator->episode * 17u);
        coordinator->phrase = (uint8_t)((coordinator->phrase +
                                         coordinator->variation) % 3u);
    }
    coordinator->action_step = 0u;
    coordinator->action_phase_count = definition->phase_count;
    coordinator->next_phase = definition->phases[0];
    coordinator->dwell_commits =
        motion_phase_dwell(coordinator->family,
                           salt,
                           0u,
                           coordinator->next_phase);
}

static void motion_finish_episode(comp_epaper_motion_coordinator_t *coordinator)
{
    if (coordinator->recent_action_count < 3u) {
        coordinator->recent_actions[coordinator->recent_action_count++] =
            (uint8_t)coordinator->action;
    } else {
        coordinator->recent_actions[0] = coordinator->recent_actions[1];
        coordinator->recent_actions[1] = coordinator->recent_actions[2];
        coordinator->recent_actions[2] = (uint8_t)coordinator->action;
    }
    coordinator->cooldowns[coordinator->action] =
        k_action_definitions[coordinator->action].cooldown;
    const motion_scene_definition_t *scene=motion_scene(coordinator);
    if(scene && ++coordinator->scene_step<scene->count) {
        /* This is reached only from a matching visible SETTLE completion.
         * Keep family/episode/phrase/variation for the entire intention. */
        motion_prepare_action(coordinator);
        return;
    }
    if(scene)coordinator->previous_scene=coordinator->scene & MOTION_SCENE_ID_MASK;
    coordinator->episode++;
    coordinator->episode_prepared = false;
    motion_prepare_episode(coordinator);
}

static void motion_advance_story(comp_epaper_motion_coordinator_t *coordinator)
{
    const motion_action_definition_t *definition;
    int32_t salt;

    if (coordinator->action == COMP_EPAPER_MOTION_ACTION_REST) {
        motion_prepare_action(coordinator);
        return;
    }
    definition = &k_action_definitions[coordinator->action];
    coordinator->action_step++;
    if (coordinator->action_step >= coordinator->action_phase_count) {
        motion_finish_episode(coordinator);
        return;
    }
    salt = motion_action_salt(coordinator);
    coordinator->next_phase = definition->phases[coordinator->action_step];
    /* A phrase and its accent belong to the whole action. Stage envelopes
     * animate it; changing the recipe between stages would change intent. */
    coordinator->dwell_commits =
        motion_phase_dwell(coordinator->family,
                           salt,
                           coordinator->action_step,
                           coordinator->next_phase);
}

const char *comp_epaper_motion_family_name(comp_epaper_motion_family_t family)
{
    return family < COMP_EPAPER_MOTION_FAMILY_COUNT ? k_family_names[family]
                                                    : "calm";
}

const char *comp_epaper_motion_action_name(comp_epaper_motion_action_t action)
{
    return action < COMP_EPAPER_MOTION_ACTION_COUNT ? k_action_names[action]
                                                    : "rest";
}

bool comp_epaper_motion_coordinator_scene_boundary(const comp_epaper_motion_coordinator_t *c)
{
    return c && (!motion_scenes_enabled(c) ||
        (c->scene_step==0u && c->action==COMP_EPAPER_MOTION_ACTION_REST &&
         c->next_phase==COMP_EPAPER_MOTION_PHASE_HOLD));
}

bool comp_epaper_motion_coordinator_enable_scenes(comp_epaper_motion_coordinator_t *c,bool enabled)
{
    if(!c || !c->initialized || c->request_outstanding ||
       c->action!=COMP_EPAPER_MOTION_ACTION_REST)return false;
    c->scene=enabled?MOTION_SCENES_ENABLED:0u;c->scene_step=0u;c->previous_scene=0u;
    motion_prepare_episode(c);return true;
}

bool comp_epaper_motion_coordinator_seed_scene(comp_epaper_motion_coordinator_t *c,uint32_t entropy)
{
    if(!c || !c->initialized || !motion_scenes_enabled(c) ||
       c->request_outstanding || !comp_epaper_motion_coordinator_scene_boundary(c))return false;
    /* Use a hardware-accepted intent seed as the episode salt. The asset ID
     * still uses episode modulo its registered family limit; each bank has
     * all family actions, not only the historical single-action sequence. */
    c->episode=entropy;motion_prepare_episode(c);return true;
}

void comp_epaper_motion_coordinator_init(
    comp_epaper_motion_coordinator_t *coordinator)
{
    if (coordinator == NULL) {
        return;
    }
    memset(coordinator, 0, sizeof(*coordinator));
    coordinator->initialized = true;
    coordinator->next_token = 1u;
    coordinator->family = COMP_EPAPER_MOTION_FAMILY_CALM;
    coordinator->next_phase = COMP_EPAPER_MOTION_PHASE_HOLD;
    coordinator->action = COMP_EPAPER_MOTION_ACTION_REST;
    coordinator->last_cancel_reason = COMP_EPAPER_MOTION_CANCEL_HIGH_PRIORITY;
}

void comp_epaper_motion_coordinator_enter_daily(
    comp_epaper_motion_coordinator_t *coordinator,
    uint32_t now_ms,
    comp_epaper_motion_family_t family)
{
    uint32_t next_token;
    uint32_t issued_requests;
    uint32_t completed_requests;
    uint32_t failed_requests;
    uint32_t cancelled_requests;
    uint32_t stale_completion_count;
    uint8_t previous_entry;
    uint8_t entry_episode;
    uint8_t scene_enabled,previous_scene;

    if (coordinator == NULL || !coordinator->initialized) {
        return;
    }
    next_token = coordinator->next_token;
    issued_requests = coordinator->issued_requests;
    completed_requests = coordinator->completed_requests;
    failed_requests = coordinator->failed_requests;
    cancelled_requests = coordinator->cancelled_requests;
    stale_completion_count = coordinator->stale_completion_count;
    previous_entry = (uint8_t)(coordinator->episode & 7u);
    scene_enabled=coordinator->scene & MOTION_SCENES_ENABLED;
    previous_scene=coordinator->previous_scene;
    memset(coordinator, 0, sizeof(*coordinator));
    coordinator->initialized = true;
    coordinator->next_token = next_token;
    coordinator->issued_requests = issued_requests;
    coordinator->completed_requests = completed_requests;
    coordinator->failed_requests = failed_requests;
    coordinator->cancelled_requests = cancelled_requests;
    coordinator->stale_completion_count = stale_completion_count;
    coordinator->daily_awake = true;
    coordinator->scene=scene_enabled;coordinator->previous_scene=previous_scene;
    coordinator->family =
        family < COMP_EPAPER_MOTION_FAMILY_COUNT
            ? family
            : COMP_EPAPER_MOTION_FAMILY_CALM;
    entry_episode =
        (uint8_t)((completed_requests ^ (next_token - 1u)) & 7u);
    if (completed_requests != 0u && entry_episode == previous_entry) {
        entry_episode = (uint8_t)((entry_episode + 1u) & 7u);
    }
    coordinator->next_request_ms = now_ms;
    coordinator->idle_deadline_ms = now_ms + COMP_EPAPER_MOTION_IDLE_TIMEOUT_MS;
    if(scene_enabled)coordinator->episode=entry_episode;
    motion_prepare_episode(coordinator);
    /* Seek through the authored state machine rather than inventing arbitrary
     * phrase/variation tuples. Every selected entry therefore has a matching
     * source-pack frame and the same action cooldown history as a normal run. */
    while (!scene_enabled && coordinator->episode < entry_episode) {
        motion_prepare_action(coordinator);
        motion_finish_episode(coordinator);
    }
}

void comp_epaper_motion_coordinator_cancel(
    comp_epaper_motion_coordinator_t *coordinator,
    comp_epaper_motion_cancel_reason_t reason)
{
    if (coordinator == NULL || !coordinator->initialized) {
        return;
    }
    if (coordinator->daily_awake || coordinator->request_outstanding) {
        coordinator->cancelled_requests++;
    }
    coordinator->daily_awake = false;
    coordinator->request_outstanding = false;
    coordinator->outstanding_token = 0u;
    coordinator->outstanding_due_ms = 0u;
    coordinator->next_request_ms = 0u;
    coordinator->idle_deadline_ms = 0u;
    coordinator->last_cancel_reason = reason;
    coordinator->scene &= MOTION_SCENES_ENABLED;
    coordinator->scene_step=0u;
}

bool comp_epaper_motion_coordinator_take_request(
    comp_epaper_motion_coordinator_t *coordinator,
    uint32_t now_ms,
    comp_epaper_motion_request_t *out_request)
{
    uint32_t token;

    if (coordinator == NULL || out_request == NULL || !coordinator->initialized ||
        !coordinator->daily_awake || coordinator->request_outstanding ||
        comp_epaper_motion_coordinator_idle_timeout_elapsed(coordinator, now_ms) ||
        !motion_time_reached(now_ms, coordinator->next_request_ms)) {
        return false;
    }
    token = motion_next_token(coordinator);
    coordinator->request_outstanding = true;
    coordinator->outstanding_token = token;
    /* Preserve the authored wall-clock deadline, not the later instant at
     * which the single-BUSY arbiter happened to grant this request a slot.
     * Using now_ms here makes recording-time life inherit waveform/BUSY
     * timing and changes the choreography merely because recording is on.
     * The arbiter gives an overdue BASE request the next eligible slot, so
     * the 3 s outstanding watchdog can safely age from this deadline without
     * reintroducing the old sparse-gate false recovery. */
    coordinator->outstanding_due_ms = coordinator->next_request_ms;
    coordinator->issued_requests++;
    *out_request = (comp_epaper_motion_request_t){
        .token = token,
        .episode = coordinator->episode,
        .family = coordinator->family,
        .phase = coordinator->next_phase,
        .action = coordinator->action,
        .phrase = coordinator->phrase,
        .variation = coordinator->variation,
        .action_step = coordinator->action_step,
        .dwell_commits = coordinator->dwell_commits,
    };
    return true;
}

bool comp_epaper_motion_coordinator_complete_request(
    comp_epaper_motion_coordinator_t *coordinator,
    uint32_t token,
    uint32_t now_ms,
    bool visible)
{
    uint32_t due_ms;

    if (coordinator == NULL || !coordinator->initialized ||
        !coordinator->request_outstanding ||
        coordinator->outstanding_token != token) {
        if (coordinator != NULL && coordinator->initialized) {
            coordinator->stale_completion_count++;
        }
        return false;
    }
    due_ms = coordinator->outstanding_due_ms;
    coordinator->request_outstanding = false;
    coordinator->outstanding_token = 0u;
    coordinator->outstanding_due_ms = 0u;
    if (!coordinator->daily_awake) {
        coordinator->stale_completion_count++;
        return false;
    }
    if (!visible) {
        coordinator->failed_requests++;
        coordinator->next_request_ms = motion_advance_absolute_deadline(
            due_ms, COMP_EPAPER_MOTION_CADENCE_MS, now_ms);
        return true;
    }
    coordinator->completed_requests++;
    {
        uint32_t dwell_ms = (uint32_t)coordinator->dwell_commits *
                            COMP_EPAPER_MOTION_CADENCE_MS;
        if (dwell_ms == 0u) {
            dwell_ms = COMP_EPAPER_MOTION_CADENCE_MS;
        }
        /* r62 accepted behavior: preserve the authored pose sequence and move
         * only its absolute deadline past a late single-BUSY completion. */
        coordinator->next_request_ms = motion_advance_absolute_deadline(
            due_ms, dwell_ms, now_ms);
    }
    motion_advance_story(coordinator);
    return true;
}

static uint32_t motion_visible_dwell(comp_epaper_motion_phase_t phase,
                                     uint8_t commits)
{
    if (commits < COMP_EPAPER_MOTION_DWELL_MIN_COMMITS)
        commits = COMP_EPAPER_MOTION_DWELL_MIN_COMMITS;
    if (commits > COMP_EPAPER_MOTION_DWELL_MAX_COMMITS)
        commits = COMP_EPAPER_MOTION_DWELL_MAX_COMMITS;
    switch (phase) {
    case COMP_EPAPER_MOTION_PHASE_HOLD:
        return (uint32_t)commits * COMP_EPAPER_MOTION_CADENCE_MS;
    case COMP_EPAPER_MOTION_PHASE_ORIENT:
    case COMP_EPAPER_MOTION_PHASE_SETTLE:
        return 80u;
    case COMP_EPAPER_MOTION_PHASE_ACCENT:
        return 160u + (uint32_t)(commits - 1u) * 60u;
    case COMP_EPAPER_MOTION_PHASE_ANTICIPATE:
    case COMP_EPAPER_MOTION_PHASE_FOLLOW:
        return 0u;
    default:
        return COMP_EPAPER_MOTION_CADENCE_MS;
    }
}

bool comp_epaper_motion_coordinator_complete_request_timed(
    comp_epaper_motion_coordinator_t *coordinator,
    uint32_t token,
    uint32_t now_ms,
    bool visible,
    uint32_t requested_ms,
    uint32_t visible_ms)
{
    uint32_t dwell_ms = coordinator == NULL ? 0u :
        motion_visible_dwell(coordinator->next_phase,
                             coordinator->dwell_commits);
    const bool scene_settle=coordinator && motion_scenes_enabled(coordinator) &&
        coordinator->next_phase==COMP_EPAPER_MOTION_PHASE_SETTLE;
    /* Retain the single token check, failure retry and authored story advance.
     * The legacy browser caller keeps its absolute 480ms commit schedule. */
    if (!comp_epaper_motion_coordinator_complete_request(
            coordinator, token, now_ms, visible)) return false;
    if (visible && now_ms - requested_ms < 0x80000000u &&
        now_ms - visible_ms <= now_ms - requested_ms) {
        if(scene_settle && coordinator->action!=COMP_EPAPER_MOTION_ACTION_REST)
            dwell_ms=600u+motion_seeded_range(coordinator->family,
                (int32_t)coordinator->episode,62u+coordinator->scene_step,4u)*200u;
        /* Physical e-paper already spends an activation on each pose. Keep
         * transitional poses back-to-back, give the accent a short readable
         * hold, then pause on the settled face. Credit non-visible paired-RAM
         * synchronization toward the hold; ownership still prevents another
         * pose from starting before this transaction has fully completed.
         * On a slower panel retain orientation, the readable accent and the
         * settled face; retire only the optional anticipate/follow poses.
         * This is a choreography budget, not a panel maximum or a shorter
         * BUSY wait. Failed commits never enter this branch or skip a pose. */
        /* Capacity is time until the driver releases both RAM baselines,
         * not just ink/BUSY time. FW240 traces show ~484ms visible wait plus
         * ~520ms paired sync; that cannot sustain the fast three-pose route.
         * Keep the hold anchored to actual visibility below. */
        if (now_ms-requested_ms>650u) {
            while (coordinator->action!=COMP_EPAPER_MOTION_ACTION_REST &&
                   (coordinator->next_phase==COMP_EPAPER_MOTION_PHASE_ANTICIPATE ||
                    coordinator->next_phase==COMP_EPAPER_MOTION_PHASE_FOLLOW))
                motion_advance_story(coordinator);
        }
        coordinator->next_request_ms = visible_ms + dwell_ms;
    }
    return true;
}

bool comp_epaper_motion_coordinator_idle_timeout_elapsed(
    const comp_epaper_motion_coordinator_t *coordinator,
    uint32_t now_ms)
{
    return coordinator != NULL && coordinator->initialized &&
           coordinator->daily_awake &&
           motion_time_reached(now_ms, coordinator->idle_deadline_ms);
}

void comp_epaper_motion_coordinator_keep_awake(
    comp_epaper_motion_coordinator_t *coordinator,
    uint32_t now_ms)
{
    if (coordinator == NULL || !coordinator->initialized ||
        !coordinator->daily_awake) {
        return;
    }
    coordinator->idle_deadline_ms =
        now_ms + COMP_EPAPER_MOTION_IDLE_TIMEOUT_MS;
}

void comp_epaper_motion_coordinator_snapshot(
    const comp_epaper_motion_coordinator_t *coordinator,
    comp_epaper_motion_snapshot_t *out_snapshot)
{
    if (out_snapshot == NULL) {
        return;
    }
    memset(out_snapshot, 0, sizeof(*out_snapshot));
    if (coordinator == NULL) {
        return;
    }
    *out_snapshot = (comp_epaper_motion_snapshot_t){
        .daily_awake = coordinator->daily_awake,
        .request_outstanding = coordinator->request_outstanding,
        .family = coordinator->family,
        .next_phase = coordinator->next_phase,
        .action = coordinator->action,
        .phrase = coordinator->phrase,
        .variation = coordinator->variation,
        .dwell_commits = coordinator->dwell_commits,
        .episode = coordinator->episode,
        .next_request_ms = coordinator->next_request_ms,
        .idle_deadline_ms = coordinator->idle_deadline_ms,
        .outstanding_token = coordinator->outstanding_token,
        .outstanding_due_ms = coordinator->outstanding_due_ms,
        .issued_requests = coordinator->issued_requests,
        .completed_requests = coordinator->completed_requests,
        .failed_requests = coordinator->failed_requests,
        .cancelled_requests = coordinator->cancelled_requests,
        .stale_completion_count = coordinator->stale_completion_count,
        .last_cancel_reason = coordinator->last_cancel_reason,
    };
}

void comp_epaper_natural_blink_init(
    comp_epaper_natural_blink_scheduler_t *scheduler,
    const comp_epaper_natural_blink_config_t *config)
{
    if (scheduler == NULL || config == NULL || config->cadence_ms == 0u ||
        config->first_interval_commits == 0u ||
        config->interval_count == 0u || config->interval_commits == NULL) {
        return;
    }
    memset(scheduler, 0, sizeof(*scheduler));
    scheduler->cadence_ms = config->cadence_ms;
    scheduler->first_interval_commits = config->first_interval_commits;
    scheduler->interval_count = config->interval_count;
    scheduler->interval_commits = config->interval_commits;
    scheduler->initialized = true;
}

void comp_epaper_natural_blink_enter_daily(
    comp_epaper_natural_blink_scheduler_t *scheduler,
    uint32_t now_ms)
{
    if (scheduler == NULL || !scheduler->initialized) {
        return;
    }
    scheduler->awake = true;
    scheduler->open_pending = false;
    scheduler->open_in_flight = false;
    scheduler->interval_index = 0u;
    scheduler->epoch = 0u;
    scheduler->next_due_ms =
        now_ms + (uint32_t)scheduler->first_interval_commits *
                     scheduler->cadence_ms;
}

void comp_epaper_natural_blink_cancel(
    comp_epaper_natural_blink_scheduler_t *scheduler)
{
    if (scheduler == NULL || !scheduler->initialized) {
        return;
    }
    scheduler->awake = false;
    scheduler->open_pending = false;
    scheduler->open_in_flight = false;
    scheduler->next_due_ms = 0u;
}

uint32_t comp_epaper_natural_blink_remaining_ms(
    const comp_epaper_natural_blink_scheduler_t *scheduler,
    uint32_t now_ms)
{
    if (scheduler == NULL || !scheduler->initialized || !scheduler->awake ||
        scheduler->open_in_flight) {
        return 0u;
    }
    return motion_time_reached(now_ms, scheduler->next_due_ms)
               ? 1u
               : scheduler->next_due_ms - now_ms;
}

bool comp_epaper_natural_blink_take_due(
    comp_epaper_natural_blink_scheduler_t *scheduler,
    uint32_t now_ms,
    comp_epaper_natural_blink_phase_t *out_phase)
{
    if (scheduler == NULL || out_phase == NULL || !scheduler->initialized ||
        !scheduler->awake ||
        !motion_time_reached(now_ms, scheduler->next_due_ms)) {
        return false;
    }
    if (scheduler->open_pending) {
        *out_phase = COMP_EPAPER_NATURAL_BLINK_OPEN;
        scheduler->open_pending = false;
        scheduler->open_in_flight = true;
        scheduler->interval_index =
            (uint8_t)((scheduler->interval_index + 1u) %
                      scheduler->interval_count);
        /* Keep a far-future hold until complete_open arms the sparse table.
         * next_due_ms=0 used to mean "due now" for closed and caused rapid
         * re-blink if open completion was delayed or missed. */
        scheduler->next_due_ms =
            now_ms + (uint32_t)scheduler->first_interval_commits *
                         scheduler->cadence_ms;
        return true;
    }
    *out_phase = COMP_EPAPER_NATURAL_BLINK_CLOSED;
    scheduler->open_pending = true;
    scheduler->epoch++;
    /* The panel commit itself supplies the minimum visible closed interval.
     * Reopen in the first display slot after that commit; an extra authored
     * dwell makes the physical blink look like a prolonged eye closure. */
    scheduler->next_due_ms =
        now_ms + COMP_EPAPER_NATURAL_BLINK_CLOSED_HOLD_MS;
    return true;
}

bool comp_epaper_natural_blink_complete_open(
    comp_epaper_natural_blink_scheduler_t *scheduler,
    uint32_t visible_ms)
{
    uint8_t interval_commits;
    uint32_t gap_ms;

    if (scheduler == NULL || !scheduler->initialized || !scheduler->awake ||
        !scheduler->open_in_flight) {
        return false;
    }
    scheduler->open_in_flight = false;
    interval_commits = blink_interval_commits(
        scheduler, scheduler->epoch + scheduler->interval_index);
    if (interval_commits == 0u) {
        interval_commits = scheduler->first_interval_commits != 0u
                               ? scheduler->first_interval_commits
                               : 1u;
    }
    gap_ms = (uint32_t)interval_commits * scheduler->cadence_ms;
    /* COMP-REQ-628 + owner 2026-08-07: not timer-like / not continuous.
     * Browser table is ~30–46 s; floor 12 s so a failed open/complete path
     * cannot collapse into chatter. */
    if (gap_ms < COMP_EPAPER_NATURAL_BLINK_MIN_INTERVAL_MS) {
        gap_ms = COMP_EPAPER_NATURAL_BLINK_MIN_INTERVAL_MS;
    }
    scheduler->next_due_ms = visible_ms + gap_ms;
    return true;
}
