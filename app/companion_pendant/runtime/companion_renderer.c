#include "companion_renderer.h"
#include "companion_recording_hold_ui.h"
#include "companion_pet_face.h"
#include "companion_pet_gaze.h"
#include "companion_pet_caption_policy.h"
#include "companion_browser_interaction_contract.h"
#include "screen_framebuffer.h"
#include "ssd1681_wba.h"
#include "companion_bitmap_stream.h"
#if COMPANION_WBA_RESOURCE_PROFILE
#include "generated/companion_recording_reason_labels.h"
#endif
#if COMPANION_WBA_UI_EXTERNAL
#include "companion_wba_external_ui.h"
typedef const comp_wba_external_bitmap_t *comp_bitmap_ref_t;
#define COMP_BITMAP_REF(value) (&(value))
#else
typedef const uint8_t *comp_bitmap_ref_t;
#define COMP_BITMAP_REF(value) (value)
#if COMPANION_WBA_RECORDING_UI_PACKED
#include "companion_wba_recording_ui_packed.h"
#else
#include "companion_wba_live_menu_values.h"
#endif
#endif
#if COMPANION_WBA_RESOURCE_PROFILE
#include "companion_wba_resource_contract.h"
#if COMPANION_WBA_RESOURCE_GENERATION >= 84u
#include "companion_wba_customer_ui.h"
#endif
#include "companion_wba_menu_geometry.h"
#include "companion_resources.h"
#include "wba_storage_layout.h"
#if defined(COMPANION_WBA_PET_CHARMS_V1) && COMPANION_WBA_PET_CHARMS_V1
#include "companion_pet_charm_catalog.h"
#endif
#if !COMPANION_WBA_UI_EXTERNAL || COMPANION_WBA_RESOURCE_GENERATION < 69u
#include "companion_battery_display_labels.h"
#endif
#if !COMPANION_WBA_RECORDING_UI_PACKED && !COMPANION_WBA_UI_EXTERNAL
#include "companion_wba_menu_feedback.h"
#endif
#if COMPANION_WBA_RESOURCE_GENERATION >= 63u
#if !COMPANION_WBA_RECORDING_UI_PACKED && !COMPANION_WBA_UI_EXTERNAL
#include "companion_pet_reply_captions.h"
#endif
#endif
#if COMPANION_WBA_RESOURCE_GENERATION >= 64u
#include "generated/companion_pet_gesture_help_labels.h"
#if !COMPANION_WBA_UI_EXTERNAL || COMPANION_WBA_RESOURCE_GENERATION < 69u
#include "companion_pet_discovery_caption.h"
#include "companion_pet_help_labels.h"
#endif
#if !COMPANION_WBA_UI_EXTERNAL
#include "companion_pet_variations.h"
#endif
#endif
_Static_assert(COMP_RUNTIME_MENU_FEEDBACK_TIMEOUT+1u==COMP_WBA_MENU_FEEDBACK_COUNT,
    "menu feedback enum/atlas mismatch");
#endif
#if !(COMPANION_WBA_RESOURCE_PROFILE && COMPANION_WBA_UI_EXTERNAL && COMPANION_WBA_RESOURCE_GENERATION >= 84u)
#include "generated/companion_pet_play_labels.h"
#endif
#include <stdio.h>
#include <string.h>
#if COMP_RUNTIME_WBA_FACE_REFERENCES && COMPANION_WBA_RESOURCE_GENERATION < 70u
#error "Face references require the original authored70+ external bank"
#endif
/* Text/menu composition stays small; pixel decode and capture yields retain
 * their existing optimized implementation. */
#if defined(__GNUC__)
#define COMP_RENDER_UI_SMALL __attribute__((optimize("Os"),noinline))
#else
#define COMP_RENDER_UI_SMALL
#endif
static const char *const phases[] = {"hold","orient","anticipate","accent","follow","settle"};
static bool progress(comp_runtime_renderer_t *r)
{ return r->progress == NULL || r->progress(r->progress_context); }
void comp_runtime_renderer_init(comp_runtime_renderer_t *r, comp_runtime_read_state_fn read, void *context)
{
    if (!r) return;
    memset(r,0,sizeof(*r)); r->read_state=read; r->context=context;
}
void comp_runtime_renderer_set_progress(comp_runtime_renderer_t *r,
    comp_runtime_render_progress_fn callback, void *context)
{
    if (!r) return;
    r->progress=callback; r->progress_context=context;
}
void comp_runtime_renderer_set_ui_reader(comp_runtime_renderer_t *r,comp_runtime_read_ui_fn callback)
{
#if COMPANION_WBA_UI_EXTERNAL
    if(r)r->read_ui=callback;
#else
    (void)r;(void)callback;
#endif
}
static bool state(comp_runtime_renderer_t *r, const char *id, uint8_t *dest)
{ return progress(r) && r->read_state && id && r->read_state(r->context,id,dest) && progress(r); }

/* Lossless RAM cache only: authored pixels, resource format and controller
 * old/new frames do not change. Write only the pending cache before submit;
 * a failed render/refresh cannot overwrite the visible clean face. */
#if COMP_PET_PROCEDURAL
static int attention_axis(uint16_t target)
{
    if(target>200u)return 0;
    int distance=(int)target-100;
    if(distance>80)distance=80;
    if(distance< -80)distance= -80;
    return distance*6/80;
}
/* One rigid, bounded placement of the complete authored face group. The
 * upper ornament docks/status and lower caption are outside this band.
 * Read from the original raster once; never move individual eyes/mouth or
 * accumulate offsets across status, blink, retry or cache reload. */
static bool attention_shift(comp_runtime_renderer_t *r,uint8_t *frame,int dx,int dy)
{
    const unsigned first=66u,rows=108u;
    if(!dx && !dy)return true;
    if(dx< -6 || dx>6 || dy< -6 || dy>6 || !progress(r))return false;
    /* Refuse clipping instead of trimming any original ink at the boundary. */
    for(unsigned y=0u;y<rows;++y) {
        if((y&7u)==0u && !progress(r))return false;
        const uint8_t *line=frame+(first+y)*25u;
        if((dy>0 && y>=rows-(unsigned)dy) || (dy<0 && y<(unsigned)-dy))
            for(unsigned b=0u;b<25u;++b)if(line[b]!=255u)return false;
        if(dx>0 && (line[24]&((1u<<dx)-1u))!=((1u<<dx)-1u))return false;
        if(dx<0 && (line[0]&(255u<<(8+dx)))!=(255u&(255u<<(8+dx))))return false;
    }
    if(dy>0) {
        memmove(frame+(first+(unsigned)dy)*25u,frame+first*25u,(rows-(unsigned)dy)*25u);
        memset(frame+first*25u,255,(unsigned)dy*25u);
    } else if(dy<0) {
        memmove(frame+first*25u,frame+(first+(unsigned)-dy)*25u,(rows-(unsigned)-dy)*25u);
        memset(frame+(first+rows-(unsigned)-dy)*25u,255,(unsigned)-dy*25u);
    }
    if(dx)for(unsigned y=0u;y<rows;++y) {
        if((y&3u)==0u && !progress(r))return false;
        uint8_t *line=frame+(first+y)*25u;
        if(dx>0)for(int b=24;b>=0;--b)
            line[b]=(uint8_t)((line[b]>>dx)|((b?line[b-1]:255u)<<(8-dx)));
        else for(unsigned b=0u;b<25u;++b)
            line[b]=(uint8_t)((line[b]<<-dx)|((b<24u?line[b+1]:255u)>>(8+dx)));
    }
    return progress(r);
}
#endif
#if !COMP_RUNTIME_WBA_FACE_REFERENCES
static bool face_cache_store(comp_runtime_renderer_t *r,uint8_t *cache,
    uint16_t *bytes,const uint8_t *frame)
{
    *bytes=0u;
#if COMPANION_WBA_RESOURCE_PROFILE
    unsigned at=0u,out=0u;
    while(at<5000u) {
        if(!progress(r))return false;
        unsigned run=1u;
        while(at+run<5000u && run<128u && frame[at+run]==frame[at])++run;
        if(run>=3u) {
            if(out+2u>COMP_RUNTIME_FACE_CACHE_BYTES)return false;
            cache[out++]=(uint8_t)(257u-run);cache[out++]=frame[at];at+=run;
        } else {
            const unsigned first=at;at+=run;
            while(at<5000u && at-first<128u) {
                run=1u;
                while(at+run<5000u && run<128u && frame[at+run]==frame[at])++run;
                if(run>=3u)break;
                const unsigned room=128u-(at-first);at+=run<room?run:room;
            }
            const unsigned count=at-first;
            if(out+1u+count>COMP_RUNTIME_FACE_CACHE_BYTES)return false;
            cache[out++]=(uint8_t)(count-1u);memcpy(cache+out,frame+first,count);out+=count;
        }
    }
    *bytes=(uint16_t)out;
#else
    (void)r;memcpy(cache,frame,5000u);*bytes=5000u;
#endif
    return true;
}
#else
static bool face_reference_store(uint8_t *cache,uint16_t *bytes,const char *id,int dx,int dy)
{
    const unsigned prefix=(dx || dy)?3u:0u;
    size_t n=strlen(id)+1u+prefix;
    if(n>COMP_RUNTIME_FACE_REFERENCE_BYTES)return false;
    if(prefix) {cache[0]='~';cache[1]=(uint8_t)('g'+dx);cache[2]=(uint8_t)('g'+dy);}
    memcpy(cache+prefix,id,n-prefix);*bytes=(uint16_t)n;return true;
}
#endif
static bool face_cache_load(comp_runtime_renderer_t *r,const uint8_t *cache,
    uint16_t bytes,uint8_t *frame)
{
#if COMP_RUNTIME_WBA_FACE_REFERENCES
    if(!bytes || bytes>COMP_RUNTIME_FACE_REFERENCE_BYTES || cache[bytes-1u]!=0u)return false;
    const unsigned prefix=cache[0]=='~'?3u:0u;
    if(prefix && (bytes<=prefix || cache[1]<'a' || cache[1]>'m' ||
        cache[2]<'a' || cache[2]>'m'))return false;
    if(strlen((const char*)cache+prefix)+1u+prefix!=bytes ||
       !state(r,(const char*)cache+prefix,frame))return false;
    return !prefix || attention_shift(r,frame,(int)cache[1]-'g',(int)cache[2]-'g');
#elif COMPANION_WBA_RESOURCE_PROFILE
    unsigned at=0u,out=0u;
    if(!bytes || bytes>COMP_RUNTIME_FACE_CACHE_BYTES)return false;
    while(at<bytes && out<5000u) {
        if(!progress(r))return false;
        const unsigned control=cache[at++];
        if(control==128u)return false;
        const unsigned count=control<128u?control+1u:257u-control;
        if(count>5000u-out)return false;
        if(control<128u) {
            if(count>bytes-at)return false;
            memcpy(frame+out,cache+at,count);at+=count;
        } else {
            if(at>=bytes)return false;
            memset(frame+out,cache[at++],count);
        }
        out+=count;
    }
    return out==5000u && at==bytes;
#else
    (void)r;if(bytes!=5000u)return false;memcpy(frame,cache,5000u);return true;
#endif
}
/* A native closed-eye raster is temporarily cached while the only render
 * workspace is restored to the visible clean face. Seek by source byte;
 * adjacent pixels reuse one decoded run, without a third frame or tile. */
#if !COMP_RUNTIME_WBA_FACE_REFERENCES
typedef struct {uint16_t at,first,end,literal;uint8_t value;bool repeat;} face_cache_cursor_t;
static bool face_cache_byte(const uint8_t *cache,uint16_t bytes,
    face_cache_cursor_t *cursor,unsigned index,uint8_t *value)
{
    if(index>=5000u)return false;
#if COMPANION_WBA_RESOURCE_PROFILE
    if(!bytes || bytes>COMP_RUNTIME_FACE_CACHE_BYTES)return false;
    if(index<cursor->first)memset(cursor,0,sizeof(*cursor));
    while(index>=cursor->end) {
        if(cursor->at>=bytes)return false;
        const unsigned control=cache[cursor->at++];
        if(control==128u)return false;
        const unsigned count=control<128u?control+1u:257u-control;
        cursor->first=cursor->end;
        if(count>5000u-cursor->end)return false;
        cursor->end=(uint16_t)(cursor->end+count);
        cursor->repeat=control>=129u;
        if(cursor->repeat) {
            if(cursor->at>=bytes)return false;
            cursor->value=cache[cursor->at++];
        } else {
            if(count>(unsigned)bytes-cursor->at)return false;
            cursor->literal=cursor->at;cursor->at=(uint16_t)(cursor->at+count);
        }
    }
    *value=cursor->repeat?cursor->value:cache[cursor->literal+index-cursor->first];
#else
    (void)cursor;if(bytes!=5000u)return false;*value=cache[index];
#endif
    return true;
}
#endif /* byte-seek is only used by bitmap caches */
static uint8_t pose_eyes_closed(const comp_runtime_frame_t *f)
{
#if COMP_PET_PROCEDURAL
    return comp_pet_face_closed(f);
#else
    if (f->family==COMP_BROWSER_FAMILY_SLEEPY) return 3u;
#if COMPANION_WBA_RESOURCE_PROFILE && COMPANION_WBA_RESOURCE_GENERATION >= 60u
    if (f->kind==COMP_RUNTIME_FRAME_REACTION && f->reaction_expression) {
#if COMPANION_WBA_RESOURCE_GENERATION >= 64u
        if(f->reaction_pose_phase!=1u)return 0u;
        if(f->family==COMP_BROWSER_FAMILY_BASHFUL && f->reaction_zone==COMP_BROWSER_TAP_ZONE_LEFT)return 0u;
#endif
        if (f->family==COMP_BROWSER_FAMILY_WARM && f->reaction_zone==COMP_BROWSER_TAP_ZONE_UP) return 3u;
#if COMPANION_WBA_RESOURCE_GENERATION >= 62u
        if (f->family==COMP_BROWSER_FAMILY_PLAYFUL && f->reaction_zone==COMP_BROWSER_TAP_ZONE_RIGHT) return 2u;
        if ((f->family==COMP_BROWSER_FAMILY_DELIGHTED && f->reaction_zone==COMP_BROWSER_TAP_ZONE_CENTER) ||
            (f->family==COMP_BROWSER_FAMILY_BASHFUL && f->reaction_zone==COMP_BROWSER_TAP_ZONE_DOWN)) return 3u;
#if COMPANION_WBA_RESOURCE_GENERATION >= 63u
        if (f->family==COMP_BROWSER_FAMILY_PLAYFUL && f->reaction_zone==COMP_BROWSER_TAP_ZONE_LEFT) return 1u;
        if (f->family==COMP_BROWSER_FAMILY_WARM && f->reaction_zone==COMP_BROWSER_TAP_ZONE_DOWN) return 3u;
        if (f->family==COMP_BROWSER_FAMILY_BASHFUL && f->reaction_zone==COMP_BROWSER_TAP_ZONE_LEFT) return 2u;
#endif
#endif
    }
#endif
    return 0u;
#endif
}
#if COMP_PET_PROCEDURAL && defined(COMPANION_WBA_PET_EMOTION_DIRECTIONS_V4) && COMPANION_WBA_PET_EMOTION_DIRECTIONS_V4
static const char *pet_accent_direction(const comp_runtime_frame_t *f)
{
#if defined(COMPANION_WBA_PET_EMOTION_VERTICAL_V5) && COMPANION_WBA_PET_EMOTION_VERTICAL_V5
    const int x=(int)f->gaze_x-100,y=(int)f->gaze_y-100;
    if((y<0?-y:y)>(x<0?-x:x)) {
        if(f->gaze_y<88u)return "up";
        if(f->gaze_y>112u)return "down";
    }
#endif
    return f->gaze_x<88u?"left":f->gaze_x>112u?"right":NULL;
}
#endif
static const char *pet_pointer_state(const comp_runtime_frame_t *f,
    char *name, size_t name_size)
{
    const uint8_t gx=comp_pet_gaze_grid(f->gaze_x),gy=comp_pet_gaze_grid(f->gaze_y);
#if COMP_PET_PROCEDURAL && defined(COMPANION_WBA_PET_CALM_DOWN_V7) && COMPANION_WBA_PET_CALM_DOWN_V7
    /* One reviewed whole face replaces only the far-down calm pointer pose.
     * Keep every other authored direction/family and existing blink route. */
    if(f->family==COMP_BROWSER_FAMILY_CALM && !f->blink_closed && gx==4u && gy==8u)
        return "pet_gaze_calm_down";
#endif
    return companion_browser_pointer_state_id_format(
        name,name_size,(uint8_t)f->family,gx,gy);
}
static bool face(comp_runtime_renderer_t *r, const comp_runtime_frame_t *f,uint8_t *frame)
{
    char name[112]; const char *id = name;
    int attention_x=0,attention_y=0;
    r->pending_base_eye_closed_mask=pose_eyes_closed(f);
    r->pending_pet_seed=f->pet_seed;r->pending_pet_variant=(uint8_t)(f->pet_variant&3u);
    r->pending_pet_float=0;
#if COMP_PET_PROCEDURAL
    if(f->kind==COMP_RUNTIME_FRAME_REACTION && f->reaction_reply &&
       !f->reaction_expression && f->reaction_step==0u &&
       f->pet_interaction==COMP_PET_HEAD_PAT && f->pet_accent==COMP_PET_ACCENT_NONE &&
       r->base_valid && r->base_family==f->family && (r->base_pet_variant>>2u)==0u) {
        /* The first look still belongs to the face the finger just touched.
         * Keep its visible ornament while following; a newly accepted intent
         * must not jump the sparkle across the face before its reply appears.
         * The expressive beat uses its own accepted seed/ornament unchanged.
         * Only successful completion can update this committed base. */
        r->pending_pet_seed=r->base_pet_seed;
        r->pending_pet_variant=r->base_pet_variant;
        r->pending_pet_float=r->base_pet_float;
    }
#endif
#if COMP_PET_PROCEDURAL
    if(f->kind==COMP_RUNTIME_FRAME_REACTION && f->reaction_expression) {
        if(f->reaction_pose_phase>2u)return false;
        static const int8_t first[]={0,-1,-2},second[]={-2,-1,0};
        r->pending_pet_float=(f->reaction_step==1u?first:second)[f->reaction_pose_phase];
    } else if(f->kind==COMP_RUNTIME_FRAME_LIFE && f->motion.action!=COMP_EPAPER_MOTION_ACTION_REST) {
        if(f->motion.phase>=COMP_EPAPER_MOTION_PHASE_COUNT)return false;
        static const int8_t float_phase[]={0,0,-1,-2,-1,0};
        r->pending_pet_float=float_phase[f->motion.phase];
    }
#endif
#if COMP_PET_PROCEDURAL && defined(COMPANION_WBA_PET_PROUD_ACCENT_V3) && COMPANION_WBA_PET_PROUD_ACCENT_V3
    /* Keep one authored emotional face throughout the existing first beat.
     * Optional arrive/release poses must not swap its mouth/eyes back to the
     * fallback family around the peak. Float, dwell and visible-peak history
     * still follow the existing runtime; this adds no panel transaction. */
    if(f->kind==COMP_RUNTIME_FRAME_REACTION && f->reaction_reply &&
       f->reaction_expression && f->reaction_step==1u &&
       !f->blink_closed &&
       f->pet_accent==COMP_PET_ACCENT_PROUD) {
        id="pet_emotion_proud";
#if defined(COMPANION_WBA_PET_EMOTION_DIRECTIONS_V4) && COMPANION_WBA_PET_EMOTION_DIRECTIONS_V4
        const char *direction=pet_accent_direction(f);
        if(direction) {
            (void)snprintf(name,sizeof(name),"pet_emotion_proud_%s",direction);id=name;
        }
#endif
#if defined(COMPANION_WBA_PET_EMOTION_SOFT_V6) && COMPANION_WBA_PET_EMOTION_SOFT_V6
        if(f->reaction_pose_phase!=1u) {
            /* The matched bank has all five authored gaze directions.
             * Replace only an existing optional pose, never add a refresh. */
            (void)snprintf(name,sizeof(name),"pet_emotion_proud%s%s_soft",
                direction?"_":"",direction?direction:"");id=name;
        }
#endif
        r->pending_base_eye_closed_mask=1u; /* Authored left wink. */
        r->pending_pet_variant|=(uint8_t)(COMP_PET_ACCENT_PROUD<<2u);
    } else
#endif
#if COMP_PET_PROCEDURAL && defined(COMPANION_WBA_PET_EMOTION_ACCENTS_V2) && COMPANION_WBA_PET_EMOTION_ACCENTS_V2
    /* V2 adds distinct emotional categories. Dejected has no autonomous
     * trigger: it is reserved for a future explicit semantic emotion input.
     * Never advertise this capability until all three states exist. */
    if(f->kind==COMP_RUNTIME_FRAME_REACTION && f->reaction_reply &&
       f->reaction_expression && f->reaction_step==1u &&
       !f->blink_closed &&
       f->pet_accent>=COMP_PET_ACCENT_DEJECTED && f->pet_accent<=COMP_PET_ACCENT_NERVOUS) {
        static const char *const emotions[]={"pet_emotion_dejected",
            "pet_emotion_protest","pet_emotion_nervous"};
        id=emotions[f->pet_accent-COMP_PET_ACCENT_DEJECTED];
#if defined(COMPANION_WBA_PET_EMOTION_DIRECTIONS_V4) && COMPANION_WBA_PET_EMOTION_DIRECTIONS_V4
        /* Select a complete authored face through arrive/peak/release;
         * status/blink/retry load its committed clean base. */
        const char *direction=pet_accent_direction(f);
        if(direction) {
            (void)snprintf(name,sizeof(name),"%s_%s",id,direction);
            id=name;
        }
#endif
#if defined(COMPANION_WBA_PET_EMOTION_SOFT_V6) && COMPANION_WBA_PET_EMOTION_SOFT_V6
        if(f->reaction_pose_phase!=1u) {
            (void)snprintf(name,sizeof(name),"%s%s%s_soft",
                emotions[f->pet_accent-COMP_PET_ACCENT_DEJECTED],
                direction?"_":"",direction?direction:"");id=name;
        }
#endif
        r->pending_base_eye_closed_mask=0u;
        r->pending_pet_variant|=(uint8_t)(f->pet_accent<<2u);
    } else
#endif
#if COMP_PET_PROCEDURAL && defined(COMPANION_WBA_PET_CONTEXT_ACCENTS_V1) && COMPANION_WBA_PET_CONTEXT_ACCENTS_V1
    /* The resource builder may advertise this only after all three complete
     * authored rasters are actually in the matched resource bank. Old banks
     * retain the existing family routes; no missing-state fallback is hidden.
     * Replace one peak, never add a panel transaction or move its timing. */
    if(f->kind==COMP_RUNTIME_FRAME_REACTION && f->reaction_reply &&
       f->reaction_expression && f->reaction_step==1u &&
       f->reaction_pose_phase==1u && !f->blink_closed &&
       f->pet_accent>=COMP_PET_ACCENT_ANTICIPATING && f->pet_accent<=COMP_PET_ACCENT_RELIEVED) {
        static const char *const accents[]={"pet_context_anticipating",
            "pet_context_puzzled","pet_context_relieved"};
        id=accents[f->pet_accent-COMP_PET_ACCENT_ANTICIPATING];
        /* These whole faces have open/half-open eyes, even when their warm
         * fallback pose is closed. Keep cached/visible eye state truthful. */
        r->pending_base_eye_closed_mask=0u;
    } else
#endif
#if COMP_PET_PROCEDURAL && COMPANION_WBA_RESOURCE_GENERATION >= 70u
    /* One authored whole-face accent; all other families and beats keep
     * their original resources. Never assemble new eyes from curves. */
    if(f->kind==COMP_RUNTIME_FRAME_REACTION && f->reaction_reply &&
       f->reaction_expression && f->reaction_step==1u &&
       f->reaction_pose_phase==1u && f->pet_interaction==COMP_PET_SHAKE)
        id="pet_shake_dizzy";
    else
#endif
#if COMP_PET_PROCEDURAL && defined(COMPANION_WBA_PET_ATTENTIVE_V8) && COMPANION_WBA_PET_ATTENTIVE_V8
    /* An existing calm, centred acknowledgement may gently lift one brow.
     * The accepted intent seed selects it once; status/retry keep its cached
     * whole face. Directional looks and every expressive peak remain their
     * original faces. This replaces step zero, never adds a display beat. */
    if(f->kind==COMP_RUNTIME_FRAME_REACTION && f->reaction_reply &&
       !f->reaction_expression && f->reaction_step==0u &&
       f->family==COMP_BROWSER_FAMILY_CALM && !f->blink_closed &&
       ((f->pet_interaction>=COMP_PET_HEAD_PAT && f->pet_interaction<=COMP_PET_CHIN) ||
        f->pet_interaction==COMP_PET_GREETING) &&
       comp_pet_gaze_grid(f->gaze_x)==4u && comp_pet_gaze_grid(f->gaze_y)==4u &&
       (f->pet_seed&1u))
        id="pet_attention_calm";
    else
#endif
    if(f->kind==COMP_RUNTIME_FRAME_SLEEP) {
        /* Whole authored UI67 poses from the existing bank. No new eyelids,
         * mouth curves, mirrored ornaments or additional image resources. */
        static const char *const sleep_ids[]={NULL,
            "life_sleepy_e0_s0_yawn_anticipate",
            "life_sleepy_e0_s1_yawn_accent",
            "expression_sleepy_v0_0_hold",
            "tap_edge_sleepy_calm_center_anticipate",
            "pointer_follow_calm_gx4_gy4"};
        if(!f->sleep_phase || f->sleep_phase>COMP_RUNTIME_SLEEP_ATTEND)return false;
        id=sleep_ids[f->sleep_phase];
        r->pending_base_eye_closed_mask=f->sleep_phase<=COMP_RUNTIME_SLEEP_PARK?3u:0u;
    } else if (f->kind == COMP_RUNTIME_FRAME_LIFE) {
        uint8_t limit=companion_browser_life_episode_limit((uint8_t)f->motion.family);
        if (!limit || f->motion.phase >= COMP_EPAPER_MOTION_PHASE_COUNT) return false;
        (void)snprintf(name,sizeof(name),"life_%s_e%lu_s%u_%s_%s",
            comp_epaper_motion_family_name(f->motion.family),(unsigned long)(f->motion.episode % limit),
            (unsigned)f->motion.action_step,comp_epaper_motion_action_name(f->motion.action),phases[f->motion.phase]);
    } else if (f->kind == COMP_RUNTIME_FRAME_REACTION) {
        if (f->reaction_reply && f->reaction_expression) {
            bool tilted=false;
            comp_browser_tap_zone_t motion_zone=(comp_browser_tap_zone_t)f->reaction_zone;
#if defined(COMPANION_WBA_PET_TILT_POSES_V1) && COMPANION_WBA_PET_TILT_POSES_V1
            /* Reuse the reviewed whole-face lean for a side cheek peek as
             * well as an IMU tilt. A shortened cheek phrase must read through
             * its face, rather than only the heart shared with a head pat.
             * Keep the existing peak, mouth, ornaments and cached identity. */
            tilted=(f->pet_interaction==COMP_PET_TILT && f->gaze_x!=100u) ||
                (f->pet_interaction==COMP_PET_CHEEK &&
                 f->family==COMP_BROWSER_FAMILY_BASHFUL &&
                 f->reaction_pose_phase==1u && !f->blink_closed &&
                 (f->reaction_zone==COMP_BROWSER_TAP_ZONE_LEFT ||
                  f->reaction_zone==COMP_BROWSER_TAP_ZONE_RIGHT));
            /* The retained whole-face lean makes a lift readable after its
             * first upward glance. This is the pet's own head gesture, not a
             * claim about IMU roll or holder location. Choose once from the
             * accepted seed, keep the current feeling and existing beat. */
            if(f->pet_interaction==COMP_PET_PICKUP && !f->blink_closed) {
                tilted=true;
                motion_zone=(f->pet_seed&1u)?COMP_BROWSER_TAP_ZONE_LEFT:COMP_BROWSER_TAP_ZONE_RIGHT;
            }
#endif
            /* Use an existing complete directional face only for open beats.
             * Never cut/repaint eyes into a different mouth, move a closed
             * eyelid as a pupil, or add a separate display transaction. */
            if(f->pet_interaction==COMP_PET_TILT ? !tilted :
                (!tilted && !r->pending_base_eye_closed_mask &&
                 (f->gaze_x!=100u || f->gaze_y!=100u))) {
                id=pet_pointer_state(f,name,sizeof(name));
            } else {
#if COMPANION_WBA_RESOURCE_PROFILE && COMPANION_WBA_RESOURCE_GENERATION >= 64u
            const char *motion_phase=tilted?phases[COMP_EPAPER_MOTION_PHASE_HOLD]:
                f->reaction_pose_phase==1u?NULL:
                f->reaction_pose_phase==0u?"arrive":"release";
            if(motion_phase)
                (void)snprintf(name,sizeof(name),"pet_motion_%s_%s_%s",comp_browser_family_name(f->family),
                    comp_browser_tap_zone_name(motion_zone),
                    motion_phase);
            else
#endif
            (void)snprintf(name,sizeof(name),"tap_local_%s_%s",comp_browser_family_name(f->family),
                comp_browser_tap_zone_name((comp_browser_tap_zone_t)f->reaction_zone));
            }
        }
        else id=pet_pointer_state(f,name,sizeof(name));
    } else if (r->base_valid && r->base_family == f->family) {
        r->pending_base_eye_closed_mask=r->base_eye_closed_mask;
        r->pending_pet_seed=r->base_pet_seed;r->pending_pet_variant=r->base_pet_variant;
        r->pending_pet_float=r->base_pet_float;
        if(!face_cache_load(r,r->base,r->base_bytes,frame))return false;
        memcpy(r->pending_base,r->base,r->base_bytes);r->pending_base_bytes=r->base_bytes;
        return true;
    } else {
        (void)snprintf(name,sizeof(name),"expression_%s_v0_0_hold",comp_browser_family_name(f->family));
    }
    if(!state(r,id,frame))return false;
#if COMP_PET_PROCEDURAL
    /* Spatial attention has a small coherent lean. Affection, pickup,
     * authored closed eyes and ordinary life retain their exact placement.
     * This uses the same accepted frame and original whole-face raster. */
    if(f->kind==COMP_RUNTIME_FRAME_REACTION && !r->pending_base_eye_closed_mask &&
       (!f->reaction_reply || f->pet_interaction==COMP_PET_TILT) &&
       (!strncmp(id,"pointer_follow_",15u) || !strcmp(id,"pet_gaze_calm_down"))) {
        attention_x=attention_axis(f->gaze_x);attention_y=attention_axis(f->gaze_y);
        if(!attention_shift(r,frame,attention_x,attention_y))return false;
    }
    if(!comp_pet_face_draw(frame,f,r->progress,r->progress_context))return false;
#endif
#if COMP_RUNTIME_WBA_FACE_REFERENCES
    /* Keep placement with the immutable original identity, so cached status
     * and natural blink reopen the same complete face without drift. */
    return face_reference_store(r->pending_base,&r->pending_base_bytes,id,attention_x,attention_y);
#else
    return face_cache_store(r,r->pending_base,&r->pending_base_bytes,frame);
#endif
}
static bool pixel(const uint8_t *frame, unsigned x, unsigned y)
{ return (frame[y*25u+x/8u] & (0x80u >> (x%8u))) != 0; }
static void paint(uint8_t *dest, unsigned x, unsigned y, bool white)
{
    uint8_t mask=(uint8_t)(0x80u >> (x%8u)); unsigned i=y*25u+x/8u;
    dest[i]=(uint8_t)((dest[i] & (uint8_t)~mask) | (white?mask:0u));
}
#if COMPANION_WBA_UI_EXTERNAL
static bool external_bitmap_at(comp_runtime_renderer_t *r,comp_bitmap_ref_t ref,
    uint8_t *data,size_t capacity,uint32_t flags)
{
    if(!r || !r->read_ui || !ref || !ref->bytes || ref->bytes>capacity ||
       !progress(r) || !r->read_ui(r->context,flags|ref->offset,data,ref->bytes) || !progress(r))return false;
    uint32_t crc=0xFFFFFFFFu;
    for(unsigned i=0;i<ref->bytes;++i) {
        crc^=data[i];
        for(unsigned b=0;b<8u;++b)crc=(crc>>1u)^((crc&1u)?0xEDB88320u:0u);
    }
    return (crc^0xFFFFFFFFu)==ref->crc32;
}
static bool external_bitmap(comp_runtime_renderer_t *r,comp_bitmap_ref_t ref,
    uint8_t *data,size_t capacity)
{return external_bitmap_at(r,ref,data,capacity,0u);}
#endif
static bool bitmap_paint_source(comp_runtime_renderer_t *r,uint8_t *frame,
    comp_bitmap_ref_t bitmap,unsigned stride,unsigned width,unsigned height,
    unsigned left,unsigned top,uint32_t flags)
{
#if COMPANION_WBA_UI_EXTERNAL
    /* At most one small glyph on the stack, never a persistent atlas or an
     * extra full frame. The normal NOR reader retains audio checkpoints. */
    uint8_t bytes[COMP_WBA_EXTERNAL_MAX_GLYPH_BYTES];
    if(!external_bitmap_at(r,bitmap,bytes,sizeof(bytes),flags))return false;
    const uint8_t *end=bytes+bitmap->bytes;
    comp_bitmap_stream_t stream={bytes,0u,0u};
#else
    (void)flags;
    comp_bitmap_stream_t stream={bitmap,0u,0u};
#endif
    if(!frame || !width || !height || width>stride*8u || left>200u || width>200u-left ||
       top>200u || height>200u-top)return false;
    for(unsigned y=0u;y<height;++y) {
        if(r && (y&3u)==0u && !progress(r))return false;
        for(unsigned column=0u;column<stride;++column) {
#if COMPANION_WBA_UI_EXTERNAL
            if(!stream.remaining && stream.next>=end)return false;
            if(!stream.remaining && !(*stream.next&128u) &&
               (size_t)(end-stream.next)<(size_t)(*stream.next+2u))return false;
            if(stream.remaining && !stream.white && stream.next>=end)return false;
#endif
            const uint8_t byte=comp_bitmap_stream_byte(&stream);
            for(unsigned bit=0u;bit<8u && column*8u+bit<width;++bit)
                if(!(byte&(0x80u>>bit)))paint(frame,left+column*8u+bit,top+y,false);
        }
    }
#if COMPANION_WBA_UI_EXTERNAL
    return !stream.remaining && stream.next==end;
#else
    return true;
#endif
}
static bool bitmap_paint(comp_runtime_renderer_t *r,uint8_t *frame,
    comp_bitmap_ref_t bitmap,unsigned stride,unsigned width,unsigned height,unsigned left,unsigned top)
{return bitmap_paint_source(r,frame,bitmap,stride,width,height,left,top,0u);}
#if COMPANION_WBA_RESOURCE_PROFILE && COMPANION_WBA_RESOURCE_GENERATION >= 64u
#if COMP_PET_PROCEDURAL
/* Two bounded integer shears give the small authored star a gentle tilt.
 * Every source ink pixel is retained; no trigonometry, sprite scratch,
 * extra frame or fresh random choice is needed. This is not a new face. */
static int pet_accessory_eighth(int value)
{ return value>=0?(value+4)/8:-((-value+4)/8); }
static void pet_accessory_turn(int x,int y,int cx,int cy,int turn,int *tx,int *ty)
{
    *tx=x-pet_accessory_eighth(turn*(y-cy));
    *ty=y+pet_accessory_eighth(turn*(*tx-cx));
}
#endif
static bool pet_accessory_clear(comp_runtime_renderer_t *r,uint8_t *frame,bool mobile)
{
    for(unsigned y=20u;y<=64u;++y) {
        if((y&3u)==0u && !progress(r))return false;
        uint8_t *row=frame+y*25u;
        if(mobile) {
            row[0]|=0x0fu;memset(row+1,0xff,10u);row[11]|=0xfeu;
        }
        row[13]|=0x3fu;memset(row+14,0xff,10u);row[24]|=0xf8u;
    }
    return true;
}
static bool pet_accessory(comp_runtime_renderer_t *r,const comp_runtime_frame_t *f,uint8_t *frame)
{
    const bool sleeping=f->surface==COMP_SCREEN_SURFACE_LOW_POWER;
    const bool play_target=f->surface==COMP_SCREEN_SURFACE_HOME &&
        (f->pet_play_caption==COMP_PET_PLAY_CAPTION_CUE ||
         f->pet_play_caption==COMP_PET_PLAY_CAPTION_RETRY);
    const unsigned family=play_target?COMP_BROWSER_FAMILY_CALM:sleeping?COMP_BROWSER_FAMILY_SLEEPY:
        (unsigned)(r->pending_base_valid?r->pending_family:r->base_family);
    unsigned variant=f->pet_variant&3u;
    unsigned accent=0u,charm=0u;
    int dx=0,dy=0;
    bool mobile=false,left=false;
#if COMP_PET_PROCEDURAL
    const unsigned ornament=r->pending_base_valid?r->pending_pet_variant:r->base_pet_variant;
    variant=sleeping?(f->pet_seed%COMP_PET_VARIATION_COUNT):(ornament&3u);
    accent=sleeping?COMP_PET_ACCENT_NONE:((ornament>>2u)&7u);
    const uint32_t seed=sleeping?f->pet_seed:
        (r->pending_base_valid?r->pending_pet_seed:r->base_pet_seed);
    const int lift=sleeping?0:(r->pending_base_valid?r->pending_pet_float:r->base_pet_float);
    mobile=f->surface==COMP_SCREEN_SURFACE_HOME || sleeping;
    /* The accepted intention owns its dock. Status/blink and retries reuse
     * the pending/committed seed; no random draw or animation clock here.
     * Translate the whole ornament, never mirror a heart, note or question. */
    left=mobile && ((seed>>21u)&1u)!=0u;
    dx=(int)((seed>>23u)%5u)-2+(left?-104:0);
    dy=(int)((seed>>28u)%3u)-1+lift;
    if(mobile)dx+=(left?-lift:lift)/2;
#endif
    /* Use one existing calm sparkle as the shared object of attention.
     * Its authored shape is not regenerated, and a retry keeps its place. */
    if(play_target) {variant=0u;accent=COMP_PET_ACCENT_NONE;}
    if(family>=10u || variant>=COMP_PET_VARIATION_COUNT)return false;
    /* The accent belongs to the whole face that was actually selected.
     * Never infer it from a newer status request or an unavailable raster. */
    if(accent==COMP_PET_ACCENT_DEJECTED || accent==COMP_PET_ACCENT_NERVOUS)
        return pet_accessory_clear(r,frame,mobile);
#if COMP_PET_PROCEDURAL && defined(COMPANION_WBA_PET_CHARMS_V1) && COMPANION_WBA_PET_CHARMS_V1
    if(accent==COMP_PET_ACCENT_PROTEST)charm=COMP_PET_CHARM_PUFF;
    else if(!play_target && accent==COMP_PET_ACCENT_NONE && ((seed>>18u)&7u)==0u) {
        /* Most intentions keep their original motif. A chosen variation is
         * stable across this reply, status, blink and failed submissions. */
        if(family==COMP_BROWSER_FAMILY_CALM && variant==2u)charm=COMP_PET_CHARM_SPROUT;
        else if(family==COMP_BROWSER_FAMILY_DELIGHTED && variant==2u)charm=COMP_PET_CHARM_NOTE;
        else if((family==COMP_BROWSER_FAMILY_WARM || family==COMP_BROWSER_FAMILY_BASHFUL) && variant==1u)
            charm=COMP_PET_CHARM_HEARTS;
        else if((family==COMP_BROWSER_FAMILY_WARM || family==COMP_BROWSER_FAMILY_PLAYFUL) && variant==2u)
            charm=COMP_PET_CHARM_FLOWER;
    }
#endif
    const uint8_t *spans;
    unsigned count;
#if COMPANION_WBA_UI_EXTERNAL
    const comp_wba_external_bitmap_t *ref=&comp_pet_accessory_spans[family][variant];
#if COMP_PET_PROCEDURAL && defined(COMPANION_WBA_PET_CHARMS_V1) && COMPANION_WBA_PET_CHARMS_V1
    if(charm>COMP_PET_CHARM_COUNT)return false;
    if(charm)ref=&comp_pet_charms[charm-1u];
#endif
    uint8_t ink[COMP_WBA_EXTERNAL_MAX_ACCESSORY_BYTES];
    if(ref->bytes%3u || !external_bitmap(r,ref,ink,sizeof(ink)))return false;
    spans=ink;count=ref->bytes/3u;
#else
    const uint16_t *range=comp_pet_accessory_ranges[family][variant];
    if(!range[1])return false;
    spans=comp_pet_accessory_spans[range[0]];count=range[1];
#endif
    if(!count)return false;
    int x0=200,x1=-1,y0=200,y1=-1;
    for(unsigned i=0;i<count;++i) {
        if((i&15u)==0u && !progress(r))return false;
        const uint8_t *span=spans+3u*i;
        const int end=(int)span[0]+span[2]-1;
        /* Source art is authored in the original face-free right dock.
         * Clamp a whole valid glyph instead of cropping its petals/outline. */
        if(!span[2] || span[0]<112u || end>190 || span[1]<20u || span[1]>64u)return false;
        if(span[0]<x0)x0=span[0];
        if(end>x1)x1=end;
        if(span[1]<y0)y0=span[1];
        if(span[1]>y1)y1=span[1];
    }
#if COMP_PET_PROCEDURAL
    const int cx=(x0+x1)/2,cy=(y0+y1)/2;
    int turn=0;
    bool turnable=!charm && (family==COMP_BROWSER_FAMILY_DELIGHTED || family==COMP_BROWSER_FAMILY_PLAYFUL);
#if defined(COMPANION_WBA_PET_CHARMS_V1) && COMPANION_WBA_PET_CHARMS_V1
    turnable=turnable || charm==COMP_PET_CHARM_FLOWER;
#endif
    if(mobile && turnable) {
        int amount=lift<0?-lift:0;
        if(amount>2)amount=2;
        turn=((seed>>22u)&1u)?amount:-amount;
    }
    if(turn) {
        /* Endpoint extrema suffice for each monotone sheared source run.
         * Reduce the tilt if a wide two-star cluster would leave its dock;
         * fall back to the complete upright ornament, never cut its edges. */
        for(;;) {
            int ax0=200,ax1=-1,ay0=200,ay1=-1;
            for(unsigned i=0;i<count;++i) {
                if((i&15u)==0u && !progress(r))return false;
                const uint8_t *span=spans+3u*i;
                for(unsigned endpoint=0u;endpoint<2u;++endpoint) {
                    int x,y;
                    pet_accessory_turn((int)span[0]+(endpoint?(int)span[2]-1:0),
                        span[1],cx,cy,turn,&x,&y);
                    if(x<ax0)ax0=x;
                    if(x>ax1)ax1=x;
                    if(y<ay0)ay0=y;
                    if(y>ay1)ay1=y;
                }
            }
            if(ax1-ax0<=90 && ay1-ay0<=44) {
                x0=ax0;x1=ax1;y0=ay0;y1=ay1;break;
            }
            turn+=turn>0?-1:1;
            if(!turn)break;
        }
    }
#endif
    if(play_target) {
        /* The four existing answer regions remain unchanged. Move the
         * complete small sparkle into their face-free centres, on the same
         * qualified cue frame. No independent timer or redraw is added. */
        const unsigned direction=f->gaze_x<100u?0u:f->gaze_x>100u?1u:
            f->gaze_y<100u?2u:3u;
        const int target_x=direction==0u?20:direction==1u?180:100;
        const int target_y=direction<2u?110:direction==2u?52:166;
        if(x1-x0>17 || y1-y0>15)return false;
        dx=target_x-(x0+x1)/2;dy=target_y-(y0+y1)/2;
        if(x0+dx<4 || x1+dx>196 || y0+dy<20 || y1+dy>=174)return false;
    } else {
        const int dock_left=left?4:106,dock_right=left?94:196;
        if(dx<dock_left-x0)dx=dock_left-x0;
        if(dx>dock_right-x1)dx=dock_right-x1;
        if(dy<20-y0)dy=20-y0;
        if(dy>64-y1)dy=64-y1;
    }
    /* Restore both face-free docks from the clean face on a home frame.
     * Byte masks keep the status rail, brows and the centre gap untouched;
     * no extra framebuffer or panel transaction is introduced. Sleep selects
     * a left/right original sleepy glyph once, with no timed motion. */
    if(!pet_accessory_clear(r,frame,mobile))return false;
    for(unsigned i=0;i<count;++i) {
        if((i&15u)==0u && !progress(r))return false;
        const uint8_t *span=spans+3u*i;
        for(unsigned x=span[0];x<(unsigned)span[0]+span[2];++x) {
            int tx=(int)x,ty=span[1];
#if COMP_PET_PROCEDURAL
            if(turn)pet_accessory_turn(tx,ty,cx,cy,turn,&tx,&ty);
#endif
            paint(frame,(unsigned)(tx+dx),(unsigned)(ty+dy),false);
        }
    }
    return true;
}
#endif
#if COMPANION_WBA_RESOURCE_PROFILE && COMPANION_WBA_RESOURCE_GENERATION >= 63u
static bool COMP_RENDER_UI_SMALL local_reply_caption(comp_runtime_renderer_t *r,const comp_runtime_frame_t *f,uint8_t *frame)
{
    _Static_assert(COMP_PET_REPLY_CAPTION_HEIGHT<=COMP_REPLY_TEXT_HEIGHT,
        "authored reply exceeds the bottom line");
    _Static_assert(COMP_PET_REPLY_CAPTION_WIDTH<=COMP_REPLY_TEXT_WIDTH,
        "authored reply exceeds the bottom width");
    if(!f->pet_caption || f->surface!=COMP_SCREEN_SURFACE_HOME || !f->reaction_reply || !f->reaction_expression ||
        f->start_pending || f->prepare_pending ||
        (f->recording!=DENZIC_AUDIO_RECORDING_STATE_IDLE && f->recording!=DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY)) return true;
    unsigned locale=(unsigned)f->menu.language;
    if(locale>=3u)return false;
    const uint8_t slot=comp_pet_caption_slot((unsigned)f->family,f->reaction_zone);
    if(slot!=UINT8_MAX) {
        if(slot>=COMP_PET_REPLY_CAPTION_COUNT)return false;
        comp_bitmap_ref_t bitmap=COMP_BITMAP_REF(comp_pet_reply_captions[locale][slot]);
        if(!bitmap_paint(r,frame,bitmap,COMP_PET_REPLY_CAPTION_STRIDE,
            COMP_PET_REPLY_CAPTION_WIDTH,COMP_PET_REPLY_CAPTION_HEIGHT,
            COMP_REPLY_TEXT_X+(COMP_REPLY_TEXT_WIDTH-COMP_PET_REPLY_CAPTION_WIDTH)/2u,
            COMP_REPLY_TEXT_Y))return false;
    }
    return true;
}
#endif
#if COMPANION_WBA_RESOURCE_PROFILE && COMPANION_WBA_RESOURCE_GENERATION >= 64u
static bool pet_gesture_label(comp_runtime_renderer_t *r,unsigned locale,unsigned label,
                              uint8_t *frame,unsigned left,unsigned top)
{
    if(locale>=3u || label>=COMP_PET_GESTURE_HELP_COUNT)return false;
    comp_bitmap_stream_t stream={.next=comp_pet_gesture_help_bits+
        comp_pet_gesture_help_offsets[locale][label]};
    for(unsigned y=0u;y<COMP_PET_GESTURE_HELP_HEIGHT;++y) {
        if(!progress(r))return false;
        for(unsigned byte=0u;byte<COMP_PET_GESTURE_HELP_STRIDE;++byte) {
            const uint8_t bits=comp_bitmap_stream_byte(&stream);
            for(unsigned bit=0u;bit<8u;++bit)
                if(!(bits&(0x80u>>bit)))paint(frame,left+byte*8u+bit,top+y,false);
        }
    }
    return true;
}
#if COMPANION_WBA_RESOURCE_GENERATION >= 84u
static bool COMP_RENDER_UI_SMALL customer_word(comp_runtime_renderer_t *,const comp_runtime_frame_t *,
    uint8_t *,unsigned,int,int,int);
static bool customer_short_word(comp_runtime_renderer_t *,const comp_runtime_frame_t *,uint8_t *,unsigned,int,int);
static bool customer_quiet_duration(comp_runtime_renderer_t *,const comp_runtime_frame_t *,uint8_t *,int,int);
#endif
static bool discovery_caption(comp_runtime_renderer_t *r,const comp_runtime_frame_t *f,uint8_t *frame)
{
    _Static_assert(COMP_PET_GESTURE_HELP_WIDTH<=COMP_REPLY_TEXT_WIDTH &&
        COMP_PET_GESTURE_HELP_HEIGHT<=COMP_REPLY_TEXT_HEIGHT,"discovery exceeds bottom line");
    if(!f->discovery_hint)return true;
    /* The first-use line teaches the hidden recording shortcut, using the
     * same authored label as Help and the gesture actually enabled. It keeps
     * the existing visible deadline and adds no recurring caption or frame. */
#if COMPANION_WBA_UI_EXTERNAL && COMPANION_WBA_RESOURCE_GENERATION >= 84u
    /* Reuse the one existing six-second first-use line, with both essential
     * entry gestures. No extra frame, timer, permanent text or face change. */
    const unsigned label=f->menu.browser.recording_gesture==COMP_SCREEN_MENU_RECORDING_GESTURE_EDGE_PULL?
        COMP_CUSTOM_INTRO_PULL:COMP_CUSTOM_HOLD_MENU;
    return f->surface==COMP_SCREEN_SURFACE_HOME &&
        customer_word(r,f,frame,label,100,180,2);
#else
    const unsigned label=f->menu.browser.recording_gesture==COMP_SCREEN_MENU_RECORDING_GESTURE_EDGE_PULL?
        COMP_PET_GESTURE_HELP_EDGE_RECORD:COMP_PET_GESTURE_HELP_CORNER_RECORD;
    return f->surface==COMP_SCREEN_SURFACE_HOME && pet_gesture_label(r,(unsigned)f->menu.language,
        label,frame,COMP_REPLY_TEXT_X+(COMP_REPLY_TEXT_WIDTH-COMP_PET_GESTURE_HELP_WIDTH)/2u,COMP_REPLY_TEXT_Y);
#endif
}
static bool pet_help_label(comp_runtime_renderer_t *r,unsigned locale,unsigned label,
                           uint8_t *frame,unsigned left,unsigned top)
{
    if(locale>=3u || label>=COMP_PET_HELP_LABELS)return false;
#if COMPANION_WBA_UI_EXTERNAL && COMPANION_WBA_RESOURCE_GENERATION >= 69u
    return bitmap_paint(r,frame,&comp_pet_help_labels[locale][label],
        COMP_PET_HELP_STRIDE,COMP_PET_HELP_WIDTH,COMP_PET_HELP_HEIGHT,left,top);
#else
    comp_bitmap_stream_t stream={.next=comp_pet_help_bits+comp_pet_help_offsets[locale][label]};
    for(unsigned y=0u;y<COMP_PET_HELP_HEIGHT;++y) {
        if(!progress(r))return false;
        for(unsigned byte=0u;byte<COMP_PET_HELP_STRIDE;++byte) {
            const uint8_t bits=comp_bitmap_stream_byte(&stream);
            for(unsigned bit=0u;bit<8u;++bit)
                if(!(bits&(0x80u>>bit)))paint(frame,left+byte*8u+bit,top+y,false);
        }
    }
    return true;
#endif
}
#endif
typedef struct { uint16_t area; uint8_t left,top,right,bottom,parent; } eye_box_t;
static uint8_t eye_root(eye_box_t *labels,uint8_t n)
{ while(labels[n].parent!=n) { n=labels[n].parent; } return n; }
/* Bounded connected components separate the eye body from its brow/cheek.
 * Projection-only bounds join a lowered brow to the eye; fixed calm rectangles
 * leave the lower half of curious/warm eyes visible. No heap or frame scratch. */
static bool eye_body(comp_runtime_renderer_t *r,const uint8_t *frame,unsigned eye,eye_box_t *out)
{
    eye_box_t labels[128]={{0}}; uint8_t rows[2][77]={{0}},count=0;
    const unsigned origin=eye?101u:24u;
    memset(out,0,sizeof(*out));
    for(unsigned y=44;y<172u;++y) {
        /* Four connected-component scans run for one blink. Previously all
         * 38,400 pixels could execute without the NOR reader's audio yields. */
        if ((y&3u)==0u && !progress(r)) return false;
        uint8_t *row=rows[y&1u],*prior=rows[(y&1u)^1u]; memset(row,0,77);
        for(unsigned p=1;p<=75u;++p) {
            unsigned x=origin+p-1u; uint8_t id=0;
            uint8_t near[4]={row[p-1u],prior[p-1u],prior[p],prior[p+1u]};
            if(pixel(frame,x,y))continue;
            for(unsigned k=0;k<4u;++k) if(near[k]) {
                uint8_t other=eye_root(labels,near[k]);
                if(!id)id=other;
                else if(other!=id) {uint8_t low=id<other?id:other,high=id>other?id:other;labels[high].parent=low;id=low;}
            }
            if(!id) {
                if(count==127u)return false;
                id=++count;labels[id].parent=id;
                labels[id].left=labels[id].right=(uint8_t)x;
                labels[id].top=labels[id].bottom=(uint8_t)y;
            }
            row[p]=id;++labels[id].area;
            if(x<labels[id].left)labels[id].left=(uint8_t)x;
            if(x>labels[id].right)labels[id].right=(uint8_t)x;
            if(y<labels[id].top)labels[id].top=(uint8_t)y;
            if(y>labels[id].bottom)labels[id].bottom=(uint8_t)y;
        }
    }
    for(unsigned i=count;i>0u;--i) {
        if ((i&15u)==0u && !progress(r)) return false;
        uint8_t root=eye_root(labels,(uint8_t)i);eye_box_t *a=&labels[i],*b=&labels[root];
        if(root!=i) {
            b->area=(uint16_t)(b->area+a->area);
            if(a->left<b->left)b->left=a->left;
            if(a->right>b->right)b->right=a->right;
            if(a->top<b->top)b->top=a->top;
            if(a->bottom>b->bottom)b->bottom=a->bottom;
        } else if(a->area>=80u && a->right-a->left>=9 && a->bottom-a->top>=11 &&
            a->left>origin && a->right<origin+74u && a->top>44u && a->bottom<171u && a->area>out->area) *out=*a;
    }
    return true;
}
/* The registered closed eyelid remains the artwork source. Align its anchor
 * to the committed eye body, erase that whole body, then composite the small
 * eyelid layer. A new family never inherits calm's eye position or height. */
static bool blink(comp_runtime_renderer_t *r, uint8_t *frame)
{
    eye_box_t source[2],target[2],glyph[2];
#if COMP_RUNTIME_WBA_FACE_REFERENCES
    uint8_t glyph_bits[2][COMP_RUNTIME_BLINK_GLYPH_BYTES];
    memset(glyph_bits,0,sizeof(glyph_bits));
#endif
    if(!state(r,"blink_open",frame))return false;
    for(unsigned e=0;e<2u;++e)
        if(!eye_body(r,frame,e,&source[e]) || !source[e].area)return false;
    if(!face_cache_load(r,r->base,r->base_bytes,frame))return false;
    for(unsigned e=0;e<2u;++e)
        if(!eye_body(r,frame,e,&target[e]))return false;
    if(!state(r,"blink_closed",frame))return false;
    for(unsigned e=0;e<2u;++e) {
        eye_box_t *g=&glyph[e];memset(g,0,sizeof(*g));g->left=g->top=200;
        for(unsigned y=source[e].top;y<=source[e].bottom;++y) {
            if ((y&3u)==0u && !progress(r)) return false;
            for(unsigned x=source[e].left;x<=source[e].right;++x)
            if(!pixel(frame,x,y)) {
                ++g->area;
                if(x<g->left)g->left=(uint8_t)x;
                if(x>g->right)g->right=(uint8_t)x;
                if(y<g->top)g->top=(uint8_t)y;
                if(y>g->bottom)g->bottom=(uint8_t)y;
            }
        }
        if(!g->area || g->area*2u>=source[e].area ||
            (g->bottom-g->top+1u)*2u>source[e].bottom-source[e].top+3u)return false;
    }
#if COMP_RUNTIME_WBA_FACE_REFERENCES
    /* Preserve only the two original closed glyphs while restoring the face.
     * Bounds are checked before modifying any committed identity. */
    for(unsigned e=0;e<2u;++e) {
        const eye_box_t *g=&glyph[e];
        const unsigned width=g->right-g->left+1u,height=g->bottom-g->top+1u;
        if(width*height>COMP_RUNTIME_BLINK_GLYPH_BYTES*8u)return false;
        for(unsigned y=0;y<height;++y) {
            if(!progress(r))return false;
            for(unsigned x=0;x<width;++x)if(!pixel(frame,g->left+x,g->top+y)) {
                unsigned bit=y*width+x;glyph_bits[e][bit/8u]|=(uint8_t)(0x80u>>(bit%8u));
            }
        }
    }
    if(!face_cache_load(r,r->base,r->base_bytes,frame))return false;
#else
    if(!face_cache_store(r,r->pending_base,&r->pending_base_bytes,frame) ||
       !face_cache_load(r,r->base,r->base_bytes,frame))return false;
    face_cache_cursor_t cursor={0};
#endif
    for(unsigned e=0;e<2u;++e) if(target[e].area) {
        const eye_box_t *s=&source[e],*t=&target[e],*g=&glyph[e];
        unsigned sw=s->right-s->left+1u,sh=s->bottom-s->top+1u,tw=t->right-t->left+1u,th=t->bottom-t->top+1u;
        unsigned gw=g->right-g->left+1u,gh=g->bottom-g->top+1u;
        unsigned width=(gw*tw+sw/2u)/sw,height=gh<th/2u?gh:th/2u;
        unsigned left=t->left+(tw-width)/2u;
        unsigned center=((g->top-s->top)*2u+gh)*th/(sh*2u);
        unsigned top=t->top+(center>height/2u?center-height/2u:0u);
        if(!width || !height || top+height>t->bottom+1u)return false;
        for(unsigned y=t->top;y<=t->bottom;++y) {
            if ((y&3u)==0u && !progress(r)) return false;
            for(unsigned x=t->left;x<=t->right;++x)paint(frame,x,y,true);
        }
        for(unsigned y=0;y<height;++y) {
            if((y&3u)==0u && !progress(r))return false;
            for(unsigned x=0;x<width;++x) {
                const unsigned sx=g->left+x*gw/width,sy=g->top+y*gh/height;
#if COMP_RUNTIME_WBA_FACE_REFERENCES
                const unsigned bit=(sy-g->top)*gw+sx-g->left;
                if(glyph_bits[e][bit/8u]&(uint8_t)(0x80u>>(bit%8u)))paint(frame,left+x,top+y,false);
#else
                uint8_t value;
                if(!face_cache_byte(r->pending_base,r->pending_base_bytes,&cursor,sy*25u+sx/8u,&value))return false;
                if(!(value&(0x80u>>(sx%8u))))paint(frame,left+x,top+y,false);
#endif
            }
        }
    }
    return true;
}
/* Keep the menu/status helpers out of the O3 resource decode hot path.
 * CE has a 512 KiB Flash budget; capture and asset decoding retain O3. */
static bool COMP_RENDER_UI_SMALL status_rail(const comp_runtime_frame_t *f, uint8_t *frame)
{
    /* A qualified cell voltage is useful before a cell-specific SOC curve
     * exists. Keep the unknown-fill dash; voltage must not invent charge. */
    if(!comp_screen_menu_render_status_bar(f->status_packed |
        COMP_SCREEN_STATUS_REQUIRE_MEASURED_BATTERY,frame,5000,200,200))return false;
#if !COMPANION_WBA_BATTERY_LINEAR_ESTIMATE
    if(!((f->status_packed&(1u<<17)) && (f->status_packed>>24u)<=100u) &&
       f->battery_mv>=1000u && f->battery_mv<=5000u) {
        unsigned tenths=(f->battery_mv+50u)/100u;
        char value[5]={(char)('0'+tenths/10u),'.',(char)('0'+tenths%10u),'V',0};
        /* A voltage-only reading also belongs inside the battery outline.
         * Leave the empty fill and truthful BLE/charge cues alone. */
        if(!comp_screen_menu_render_battery_reading(value,frame,5000,200,200))return false;
    }
#endif
    return true;
}
static bool COMP_RENDER_UI_SMALL status(const comp_runtime_frame_t *f, uint8_t *frame)
{
    /* All cues share an 11x11 pixel grid and a one-pixel stroke. Their black
     * ink stays inside the existing 16px status rail: the face never moves to
     * make room for a translated label or a long operation name. */
    static const uint16_t wait_icon[11]={0x7FC,0x404,0x208,0x110,0x0A0,0x040,0x0A0,0x110,0x208,0x404,0x7FC};
    static const uint16_t save_icon[11]={0x040,0x040,0x040,0x150,0x0E0,0x040,0,0x404,0x404,0x7FC,0};
    static const uint16_t saved_icon[11]={0,0,0x008,0x018,0x030,0x460,0x6C0,0x380,0x100,0,0};
    static const uint16_t sync_icon[11]={0,0x1F8,0x308,0x508,0x400,0,0x004,0x414,0x418,0x3F0,0};
    static const uint16_t error_icon[11]={0x0E0,0x110,0x208,0x444,0x444,0x444,0x404,0x444,0x208,0x110,0x0E0};
    static const uint16_t unavailable_icon[11]={0x0E0,0x110,0x208,0x404,0x404,0x7FC,0x404,0x404,0x208,0x110,0x0E0};
    static const uint16_t pause_icon[11]={0,0,0x330,0x330,0x330,0x330,0x330,0x330,0x330,0,0};
    static const uint16_t record_icon[11]={0,0,0x0E0,0x1F0,0x3F8,0x3F8,0x3F8,0x1F0,0x0E0,0,0};
    static const uint16_t muted_icon[11]={0,0,0x010,0x030,0x3D5,0x252,0x3D5,0x030,0x010,0,0};
    comp_screen_framebuffer_t fb; char text[16]={0}; const uint16_t *icon=NULL;
    int16_t icon_x=COMP_SCREEN_STATUS_CONTEXT_CENTER_X-5;
    if (!status_rail(f,frame) ||
        !comp_screen_framebuffer_init(&fb,frame,5000,200,200)) return false;
    if ((f->status_packed & COMP_SCREEN_STATUS_UPDATING) &&
               f->recording!=DENZIC_AUDIO_RECORDING_STATE_RECORDING) {
        const unsigned phase=f->update_display&255u,pct=(f->update_display>>8)&255u;
        if(phase==COMP_RUNTIME_UPDATE_RECEIVING) {
            comp_screen_framebuffer_stroke_rect(&fb,70,5,44,7,1,true);
            if(pct<=100u) {
                comp_screen_framebuffer_fill_rect(&fb,72,7,(uint16_t)(pct*40u/100u),3,true);
                (void)snprintf(text,sizeof(text),"%u%%",pct);
            } else memcpy(text,"--%",4u);
            comp_screen_framebuffer_draw_text(&fb,118,5,text,1,true);
            icon=save_icon;icon_x=54;
        } else {
            static const char *const labels[]={"UPDATE","UPDATE","CHECK","INSTALL","RESTART","CHECK","DONE","ERROR"};
            const char *label=labels[phase<8u?phase:0u];
            comp_screen_framebuffer_draw_text(&fb,(int16_t)(COMP_SCREEN_STATUS_CONTEXT_CENTER_X-(int)strlen(label)*3),5,label,1,true);
        }
    } else if (f->recording==DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY) icon=error_icon;
    else if (f->last_result != COMP_RUNTIME_OK) icon=f->last_result==COMP_RUNTIME_UNAVAILABLE?unavailable_icon:
        f->last_result==COMP_RUNTIME_BUSY?wait_icon:error_icon;
    else if (f->prepare_pending || f->start_pending || f->recording==DENZIC_AUDIO_RECORDING_STATE_PENDING_START) icon=wait_icon;
    else if (f->recording==DENZIC_AUDIO_RECORDING_STATE_STOPPING) icon=save_icon;
    else if (f->recording==DENZIC_AUDIO_RECORDING_STATE_RECORDING) {
        uint32_t seconds=f->recording_elapsed_seconds;
        icon=f->recording_paused?pause_icon:record_icon; icon_x=78;
        if(f->kind!=COMP_RUNTIME_FRAME_HOLD && !f->recording_paused &&
           f->recording_input_level>=1u && f->recording_input_level<=5u) {
            /* The sampled PCM level uses the existing status refresh. It
             * represents all input, including background noise. */
            comp_screen_framebuffer_draw_text(&fb,44,5,"IN",1,true);
            comp_screen_framebuffer_draw_line(&fb,59,12,73,12,true);
            for(unsigned i=0;i<(unsigned)f->recording_input_level-1u;++i) {
                const uint16_t h=(uint16_t)(2u+2u*i);
                comp_screen_framebuffer_fill_rect(&fb,(int16_t)(59u+4u*i),
                    (int16_t)(12u-h),2u,h,true);
            }
        }
        if(seconds<6000u)
            (void)snprintf(text,sizeof(text),"%02lu:%02lu",(unsigned long)(seconds/60u),(unsigned long)(seconds%60u));
        else if(seconds<360000u)
            (void)snprintf(text,sizeof(text),"%02lu:%02lu:%02lu",(unsigned long)(seconds/3600u),
                (unsigned long)((seconds/60u)%60u),(unsigned long)(seconds%60u));
        else
            (void)snprintf(text,sizeof(text),"%luH",(unsigned long)(seconds/3600u));
        comp_screen_framebuffer_draw_text(&fb,94,5,text,1,true);
    } else if(f->recording==DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY &&
              f->record_stop_reason==COMP_RECORD_STOP_STORAGE_FULL) {
        icon=error_icon;icon_x=78;
        comp_screen_framebuffer_draw_text(&fb,94,5,"FULL",1,true);
    } else if(f->kind==COMP_RUNTIME_FRAME_HOLD) {
        /* Keep the original four cells and recognition timing, in one fixed
         * central slot. Other low-priority pet/status marks cannot shift it. */
        for(unsigned i=0;i<4u;++i) {
            const int16_t x=(int16_t)(COMP_SCREEN_STATUS_CONTEXT_CENTER_X-15+i*8u);
            comp_screen_framebuffer_stroke_rect(&fb,x,5,6,6,1,true);
            if(i<=f->hold_bucket)comp_screen_framebuffer_fill_rect(&fb,x+2,7,2,2,true);
        }
    } else if (f->recording==DENZIC_AUDIO_RECORDING_STATE_TRANSFER_ACTIVE) icon=sync_icon;
    else if(f->surface==COMP_SCREEN_SURFACE_MENU) {
        /* The existing scrollbar already communicates menu position.
         * Keep time/link/battery, without a duplicate central page number. */
    } else if (f->recording==DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY) icon=saved_icon;
    else if(f->surface==COMP_SCREEN_SURFACE_HOME && f->pet_sound_suppressed) {
        icon=muted_icon;
        if(f->temporary_quiet_minutes) {
            /* Reuse the existing mute mark and status digits. The remaining
             * minutes distinguish temporary quiet without opening Quick. */
            (void)snprintf(text,sizeof(text),"%uM",(unsigned)f->temporary_quiet_minutes);
            icon_x=(int16_t)(COMP_SCREEN_STATUS_CONTEXT_CENTER_X-(11+4+(int)strlen(text)*6)/2);
            comp_screen_framebuffer_draw_text(&fb,(int16_t)(icon_x+15),5,text,1,true);
        }
    }
    if(icon) for(unsigned y=0;y<11u;++y) for(unsigned x=0;x<11u;++x)
        if(icon[y]&(0x400u>>x)) comp_screen_framebuffer_set_pixel(&fb,(int16_t)(icon_x+x),(int16_t)(2u+y),true);
    return true;
}
#if COMPANION_WBA_RESOURCE_PROFILE
static bool COMP_RENDER_UI_SMALL menu_feedback(comp_runtime_renderer_t *r,const comp_runtime_frame_t *f,uint8_t frame[5000])
{
    const unsigned feedback=(unsigned)f->menu_feedback;
    if(!feedback)return true;
    if(feedback>=COMP_WBA_MENU_FEEDBACK_COUNT || (unsigned)f->menu.language>COMP_SCREEN_MENU_LANGUAGE_ZH_TW)return false;
    const unsigned locale=(unsigned)f->menu.language;
    const bool confirm=f->menu.view==COMP_SCREEN_MENU_VIEW_BROWSER_CLEAR_RECORDINGS ||
        f->menu.view==COMP_SCREEN_MENU_VIEW_BROWSER_RESTORE_DEFAULTS;
    const int top=confirm?142:186;
    const unsigned width=comp_wba_menu_feedback_advance[locale][feedback];
    const int left=100-(int)width/2;
    comp_bitmap_ref_t glyph=COMP_BITMAP_REF(comp_wba_menu_feedback[locale][feedback]);
    comp_screen_framebuffer_t fb;
    if(!comp_screen_framebuffer_init(&fb,frame,5000,200,200))return false;
    comp_screen_framebuffer_fill_rect(&fb,12,(int16_t)top,176,confirm?18:14,false);
    return bitmap_paint(r,frame,glyph,COMP_WBA_MENU_FEEDBACK_STRIDE,
        width,COMP_WBA_MENU_FEEDBACK_HEIGHT,(unsigned)left,(unsigned)top);
}
static bool COMP_RENDER_UI_SMALL menu_number_at(comp_runtime_renderer_t *r,comp_screen_framebuffer_t *fb,int x,int y,int width,const char *value,bool clock)
{
    int left=x,limit=x+width;
    unsigned height=clock?12u:COMP_WBA_LIVE_VALUE_HEIGHT;
    unsigned glyph_width=clock?12u:16u;
    if(!clock) {
        int advance=0;
        for(const char *p=value;*p;++p) {
            const char *found=strchr(comp_wba_value_chars,*p);
            advance+=found?comp_wba_value_advance[found-comp_wba_value_chars]:6;
        }
        if(advance<=width)left=x+width-advance;
    }
    comp_screen_framebuffer_fill_rect(fb,(int16_t)x,(int16_t)y,(uint16_t)width,(uint16_t)height,false);
    for(;*value && left<limit;++value) {
        if((*value=='V' || *value=='~') && !clock) {
            const char glyph[2]={*value,0};
            comp_screen_framebuffer_draw_text(fb,(int16_t)left,(int16_t)(y+4),glyph,1,true);
            left+=6;continue;
        }
        const char *found=strchr(comp_wba_value_chars,*value);
        if(!found){left+=6;continue;}
#if COMPANION_WBA_UI_EXTERNAL
        comp_bitmap_ref_t glyph=clock?&comp_wba_clock_digits[found-comp_wba_value_chars]:&comp_wba_value_digits[found-comp_wba_value_chars];
        const unsigned visible=(unsigned)(limit-left)<glyph_width?(unsigned)(limit-left):glyph_width;
        if(!bitmap_paint(r,fb->data,glyph,2u,visible,height,(unsigned)left,(unsigned)y))return false;
#else
        (void)r;
        const uint8_t *glyph=clock?comp_wba_clock_digits[found-comp_wba_value_chars]:comp_wba_value_digits[found-comp_wba_value_chars];
        for(unsigned row=0;row<height;++row)for(unsigned column=0;column<glyph_width;++column)
            if(left+(int)column<limit && !(glyph[row*2u+column/8u]&(0x80u>>(column%8u))))
                comp_screen_framebuffer_set_pixel(fb,(int16_t)(left+(int)column),(int16_t)(y+(int)row),true);
#endif
        left+=clock?comp_wba_clock_advance[found-comp_wba_value_chars]:comp_wba_value_advance[found-comp_wba_value_chars];
    }
    return true;
}
static bool menu_number(comp_runtime_renderer_t *r,comp_screen_framebuffer_t *fb,int y,const char *value)
{ return menu_number_at(r,fb,COMP_WBA_MENU_VALUE_LEFT,y,COMP_WBA_MENU_VALUE_WIDTH,value,false); }
/* Only the standard mounted resource reader defines this context type.
 * Custom/native readers have no measured bank identity or extent; leave
 * their fields unknown instead of casting an arbitrary callback context. */
static const comp_runtime_resources_t *mounted_menu_resources(const comp_runtime_renderer_t *r)
{
    if(r->read_state!=comp_runtime_resources_read || !r->context)return NULL;
    const comp_runtime_resources_t *resources=r->context;
    return resources->ready && resources->generation.mounted && resources->store &&
        resources->store->storage_class==COMP_ASSET_STORAGE_EXTERNAL_NOR?resources:NULL;
}
#if COMPANION_WBA_RESOURCE_GENERATION >= 64u
#if COMPANION_WBA_UI_EXTERNAL && COMPANION_WBA_RESOURCE_GENERATION >= 84u
static bool customer_glyph(comp_runtime_renderer_t *r,unsigned locale,unsigned index,
    comp_wba_external_bitmap_t *glyph,unsigned *width);
#endif
static bool pet_play_label(comp_runtime_renderer_t *r,unsigned locale,unsigned label,
                            uint8_t *frame,unsigned left,unsigned top)
{
#if COMPANION_WBA_UI_EXTERNAL && COMPANION_WBA_RESOURCE_GENERATION >= 84u
    if(locale>=3u || label>=COMP_CUSTOMER_PLAY_LABEL_COUNT || left>40u || top>182u)return false;
    for(unsigned half=0u;half<2u;++half) {
        comp_wba_external_bitmap_t glyph;unsigned width;
        if(!customer_glyph(r,locale,COMP_CUSTOMER_PLAY_FIRST+label*2u+half,&glyph,&width) || width!=160u ||
           !bitmap_paint_source(r,frame,&glyph,20u,160u,9u,left,top+half*9u,COMP_CUSTOMER_BITMAP_FLAG))return false;
    }
    return true;
#else
    if(locale>=3u || label>=COMP_PET_PLAY_LABEL_COUNT || left>=200u || top>182u)return false;
    comp_bitmap_stream_t stream={.next=comp_pet_play_label_bits+comp_pet_play_label_offsets[locale][label]};
    for(unsigned y=0u;y<18u;++y) {
        if(!progress(r))return false;
        for(unsigned byte=0u;byte<20u;++byte) {
            const uint8_t bits=comp_bitmap_stream_byte(&stream);
            for(unsigned bit=0u;bit<8u;++bit)
                if(!(bits&(0x80u>>bit))) {
                    if(left+byte*8u+bit>=200u)return false;
                    paint(frame,left+byte*8u+bit,top+y,false);
                }
        }
    }
    return true;
#endif
}
static void pet_help_press(comp_screen_framebuffer_t *fb,const comp_screen_menu_t *menu,
                           unsigned index,int y,unsigned height)
{
    if((menu->flags&COMP_SCREEN_MENU_FLAG_PRESS_ACTIVE) &&
       ((menu->flags&COMP_SCREEN_MENU_FLAG_PRESS_ITEM_MASK)>>COMP_SCREEN_MENU_FLAG_PRESS_ITEM_SHIFT)==index)
        comp_screen_framebuffer_stroke_rect(fb,12,(int16_t)y,176,(uint16_t)height,1,true);
}
static bool pet_gesture_help(comp_runtime_renderer_t *r,const comp_runtime_frame_t *f,uint8_t *frame)
{
    /* Four short instructions share the old read-only help area. The three
     * action hit regions below it retain their existing geometry/ownership. */
    const unsigned labels[4]={
        f->menu.browser.gaze_follow?COMP_PET_GESTURE_HELP_FOLLOW:COMP_PET_GESTURE_HELP_TOUCH,
        COMP_PET_GESTURE_HELP_MENU,
        f->menu.browser.recording_gesture==COMP_SCREEN_MENU_RECORDING_GESTURE_EDGE_PULL?
            COMP_PET_GESTURE_HELP_EDGE_RECORD:COMP_PET_GESTURE_HELP_CORNER_RECORD,
#if COMPANION_WBA_UI_EXTERNAL && COMPANION_WBA_RESOURCE_GENERATION >= 71u
        COMP_PET_GESTURE_HELP_QUICK
#else
        COMP_PET_GESTURE_HELP_SHAKE
#endif
    };
    const unsigned locale=(unsigned)f->menu.language;
    _Static_assert(COMP_PET_GESTURE_HELP_WIDTH+16u<=200u,"gesture help exceeds screen width");
    _Static_assert(48u+3u*14u+COMP_PET_GESTURE_HELP_HEIGHT<=106u,
        "gesture instructions must not overlap help action targets");
    for(unsigned row=0u;row<4u;++row)
        if(!pet_gesture_label(r,locale,labels[row],frame,16u,48u+row*14u))return false;
    return true;
}
#if COMPANION_WBA_UI_EXTERNAL && COMPANION_WBA_RESOURCE_GENERATION >= 84u
static bool customer_menu_header(comp_runtime_renderer_t *r,const comp_runtime_frame_t *f,
    uint8_t *frame,comp_screen_framebuffer_t *fb);
#endif
static bool COMP_RENDER_UI_SMALL pet_help(comp_runtime_renderer_t *r,const comp_runtime_frame_t *f,uint8_t *frame)
{
    char volume[5];comp_screen_framebuffer_t fb;
    const unsigned locale=(unsigned)f->menu.language;
    if(!comp_screen_framebuffer_init(&fb,frame,5000,200,200))return false;
#if COMPANION_WBA_UI_EXTERNAL && COMPANION_WBA_RESOURCE_GENERATION >= 84u
    /* UI84 retires the old menu rasters. Help keeps its original content and
     * hit regions, but obtains the same live header as the customer menus. */
    if(!customer_menu_header(r,f,frame,&fb))return false;
#else
    char id[96];
    /* Reuse the original interaction header/return affordance. New help has
     * no atlas screen index, so it must not reach the generated row catalog. */
    if(!companion_browser_menu_state_id_format(id,sizeof(id),(uint8_t)locale,8u,0u,255u,0u,0u) ||
       !state(r,id,frame))return false;
    comp_screen_framebuffer_fill_rect(&fb,0,45,200,155,false);
#endif
    if(!pet_gesture_help(r,f,frame) ||
       !pet_help_label(r,locale,2u,frame,16u,109u) ||
       !pet_play_label(r,locale,0u,frame,16u,137u) ||
       !pet_help_label(r,locale,3u,frame,16u,164u))return false;
    /* Instructions above are read-only. The pet actions and explicit sound
     * controls below are destinations, with the same navigation chevron.
     * Their original hit regions and visible-completion gate stay intact. */
    comp_screen_framebuffer_draw_line(&fb,16,105,184,105,true);
#if COMPANION_WBA_UI_EXTERNAL && COMPANION_WBA_RESOURCE_GENERATION >= 71u
    const unsigned destinations=3u;
#else
    const unsigned destinations=2u;
#endif
    for(unsigned i=0u;i<destinations;++i) {
        const int y=117+(int)i*28;
        comp_screen_framebuffer_draw_line(&fb,177,(int16_t)(y-4),181,(int16_t)y,true);
        comp_screen_framebuffer_draw_line(&fb,181,(int16_t)y,177,(int16_t)(y+4),true);
    }
    (void)snprintf(volume,sizeof(volume),"%u%%",(unsigned)f->menu.browser.pet_volume);
#if COMPANION_WBA_UI_EXTERNAL && COMPANION_WBA_RESOURCE_GENERATION >= 71u
    if(!menu_number_at(r,&fb,121,164,48,volume,false))return false;
#else
    if(!menu_number_at(r,&fb,136,164,48,volume,false))return false;
#endif
    for(unsigned i=0u;i<3u;++i)pet_help_press(&fb,&f->menu,i,106+(int)i*28,24u);
    return true;
}
#if COMPANION_WBA_UI_EXTERNAL && COMPANION_WBA_RESOURCE_GENERATION >= 71u
static bool quick_label(comp_runtime_renderer_t *r,unsigned locale,unsigned label,
                         uint8_t *frame,unsigned left,unsigned top)
{
    return locale<3u && label<COMP_WBA_QUICK_LABEL_COUNT &&
        bitmap_paint(r,frame,&comp_wba_quick_labels[locale][label],COMP_WBA_QUICK_LABEL_STRIDE,
            COMP_WBA_QUICK_LABEL_WIDTH,COMP_WBA_QUICK_LABEL_HEIGHT,left,top);
}
/* Small 1-bit controls; no extra bitmap, framebuffer or animation clock. */
static void COMP_RENDER_UI_SMALL quick_disc(comp_screen_framebuffer_t *fb,int x,int y,int radius,bool black)
{
    for(int dy=-radius;dy<=radius;++dy)
        for(int dx=-radius;dx<=radius;++dx)
            if(dx*dx+dy*dy<=radius*radius)
                comp_screen_framebuffer_set_pixel(fb,(int16_t)(x+dx),(int16_t)(y+dy),black);
}
static void COMP_RENDER_UI_SMALL quick_mute_switch(comp_screen_framebuffer_t *fb,bool muted)
{
    comp_screen_framebuffer_fill_rect(fb,161,135,16,15,true);
    quick_disc(fb,161,142,7,true);quick_disc(fb,176,142,7,true);
    if(!muted) {
        comp_screen_framebuffer_fill_rect(fb,161,136,16,13,false);
        quick_disc(fb,161,142,6,false);quick_disc(fb,176,142,6,false);
    }
    quick_disc(fb,muted?176:161,142,4,!muted);
}
static bool COMP_RENDER_UI_SMALL quick_controls(comp_runtime_renderer_t *r,const comp_runtime_frame_t *f,uint8_t *frame)
{
    comp_screen_framebuffer_t fb;char value[5];const unsigned locale=(unsigned)f->menu.language;
    if(!comp_screen_framebuffer_init(&fb,frame,5000u,200u,200u))return false;
    comp_screen_framebuffer_clear(&fb,false);
    /* Original authored Quick title now covers volume, quiet interaction and
     * recording. Keep all existing atlas bytes and original face artwork. */
    if(!quick_label(r,locale,0u,frame,locale==0u?82u:86u,27u))return false;
    if(
       !customer_word(r,f,frame,COMP_CUSTOM_MANUAL,16u,134u,0) ||
       !quick_label(r,locale,1u,frame,locale==0u?64u:44u,134u) ||
       !pet_play_label(r,locale,3u,frame,16u,164u))return false;
#if COMPANION_WBA_RESOURCE_GENERATION >= 84u
    const unsigned level=f->menu.browser.interaction_level;
    const unsigned current=level==COMP_SCREEN_MENU_INTERACTION_QUIET?COMP_CUSTOM_QUIET:
        level==COMP_SCREEN_MENU_INTERACTION_LIVELY?COMP_CUSTOM_LIVELY:COMP_CUSTOM_STANDARD;
    if(f->temporary_quiet_minutes) {
        if(!customer_quiet_duration(r,f,frame,16,111))return false;
    } else if(!customer_word(r,f,frame,current,16,111,0))return false;
    comp_screen_framebuffer_draw_line(&fb,176,115,181,119,true);
    comp_screen_framebuffer_draw_line(&fb,181,119,176,123,true);
#endif
    /* Upward return affordance and a single settled, native-size panel. */
    comp_screen_framebuffer_draw_line(&fb,17,36,23,30,true);
    comp_screen_framebuffer_draw_line(&fb,23,30,29,36,true);
    /* Full-menu access stays visible without occupying the primary record row. */
    for(int y=28;y<=38;y+=5)comp_screen_framebuffer_draw_line(&fb,164,(int16_t)y,180,(int16_t)y,true);
    /* Show the effective sound state instead of a misleading stored-volume
     * percentage. The slider and manual switch keep their independent saved
     * values; changing them does not silently disable the quiet policy. */
#if COMPANION_WBA_RESOURCE_GENERATION >= 84u
    if(f->temporary_quiet_minutes) {
        if(!customer_short_word(r,f,frame,COMP_CUSTOM_QUIET,16,54))return false;
        (void)snprintf(value,sizeof(value),"%u",(unsigned)f->temporary_quiet_minutes);
        if(!menu_number_at(r,&fb,132,54,24,value,false))return false;
        comp_screen_framebuffer_draw_text(&fb,162,59,"MIN",1u,true);
    } else if(f->pet_sound_suppressed) {
        if(level==COMP_SCREEN_MENU_INTERACTION_QUIET) {
            if(!customer_word(r,f,frame,COMP_CUSTOM_QUIET,16,54,0))return false;
        } else if(f->menu.browser.pet_muted) {
            if(!customer_word(r,f,frame,COMP_CUSTOM_MANUAL,16,54,0) ||
               !quick_label(r,locale,1u,frame,locale==0u?64u:44u,54u))return false;
        } else if(!quick_label(r,locale,1u,frame,16u,54u))return false;
    } else
#endif
    {
        if(!pet_help_label(r,locale,3u,frame,16u,54u))return false;
        (void)snprintf(value,sizeof(value),"%u%%",(unsigned)f->menu.browser.pet_volume);
        if(!menu_number_at(r,&fb,132,54,52,value,false))return false;
    }
    comp_screen_framebuffer_draw_line(&fb,16,80,184,80,true);
    const unsigned volume=f->menu.browser.pet_volume>100u?100u:f->menu.browser.pet_volume;
    const int thumb=COMP_SCREEN_QUICK_VOLUME_LEFT+(int)(volume*168u/100u);
    if(volume)comp_screen_framebuffer_fill_rect(&fb,16,79,(uint16_t)(thumb-16),2,true);
    for(unsigned stop=0;stop<5u;++stop) {
        const int x=COMP_SCREEN_QUICK_VOLUME_LEFT+(int)(stop*42u);
        comp_screen_framebuffer_draw_line(&fb,(int16_t)x,86,(int16_t)x,88,true);
        (void)snprintf(value,sizeof(value),"%u",stop*25u);
        comp_screen_framebuffer_draw_text(&fb,(int16_t)(x-(int)comp_screen_framebuffer_text_width(value,1u)/2),94,value,1,true);
    }
    quick_disc(&fb,thumb,80,5,false);quick_disc(&fb,thumb,80,4,true);
    quick_mute_switch(&fb,f->menu.browser.pet_muted);
    comp_screen_framebuffer_draw_line(&fb,176,168,181,173,true);
    comp_screen_framebuffer_draw_line(&fb,181,173,176,178,true);
    return true;
}
#endif
#endif
static bool COMP_RENDER_UI_SMALL menu_confirmation_count(comp_runtime_renderer_t *r,comp_screen_framebuffer_t *fb,const char *value)
{
    int width=0;
    for(const char *p=value;*p;++p)
        if(*p>='0' && *p<='9')width+=comp_wba_count_advance[*p-'0'];
    int left=100-width/2;
    comp_screen_framebuffer_fill_rect(fb,16,COMP_WBA_CONFIRM_COUNT_TOP,168,COMP_WBA_COUNT_HEIGHT,false);
    for(;*value;++value) {
        if(*value<'0' || *value>'9')continue;
#if COMPANION_WBA_UI_EXTERNAL
        if(!bitmap_paint(r,fb->data,&comp_wba_count_digits[*value-'0'],COMP_WBA_COUNT_STRIDE,
            COMP_WBA_COUNT_WIDTH,COMP_WBA_COUNT_HEIGHT,(unsigned)left,COMP_WBA_CONFIRM_COUNT_TOP))return false;
#else
        (void)r;
        const uint8_t *glyph=comp_wba_count_digits[*value-'0'];
        for(unsigned row=0;row<COMP_WBA_COUNT_HEIGHT;++row)
            for(unsigned column=0;column<COMP_WBA_COUNT_WIDTH;++column)
                if(!(glyph[row*COMP_WBA_COUNT_STRIDE+column/8u]&(0x80u>>(column%8u))))
                    comp_screen_framebuffer_set_pixel(fb,(int16_t)(left+(int)column),
                        (int16_t)(COMP_WBA_CONFIRM_COUNT_TOP+row),true);
#endif
        left+=comp_wba_count_advance[*value-'0'];
    }
    return true;
}
#endif
#if COMPANION_WBA_RESOURCE_PROFILE
static bool COMP_RENDER_UI_SMALL menu_priority_rows(const comp_screen_menu_t *menu,uint8_t *frame)
{
    if(menu->home_page || (menu->view!=COMP_SCREEN_MENU_VIEW_BROWSER_VOICE &&
                          menu->view!=COMP_SCREEN_MENU_VIEW_BROWSER_DISPLAY))return true;
    /* Reorder the original localized raster rows in place, one byte per
     * cycle. The same logical->source map owns hit testing; no new bitmap,
     * font, framebuffer or row-sized RAM allocation is needed. */
    const unsigned base=COMP_WBA_MENU_ROW_TOP*25u,stride=COMP_WBA_MENU_ROW_HEIGHT*25u;
    for(unsigned byte=0u;byte<stride;++byte) {
        unsigned visited=0u;
        for(unsigned start=0u;start<4u;++start) {
            if(visited&(1u<<start))continue;
            const uint8_t saved=frame[base+start*stride+byte];
            unsigned row=start;
            do {
                const unsigned source=comp_screen_menu_source_row(menu->view,(uint8_t)row);
                if(source>=4u)return false;
                visited|=1u<<row;
                frame[base+row*stride+byte]=source==start?saved:frame[base+source*stride+byte];
                row=source;
            } while(row!=start);
        }
    }
    return true;
}
#endif
#if COMPANION_WBA_RESOURCE_PROFILE
/* Values 0..10 remain the unchanged UI80 recording-state atlas. Only
 * explicit backend reasons or the pause snapshot add local text; no percentage
 * implies a stop cause.
 * A terminal low-power result says "Battery too low", because that same cause
 * can also refuse a start. It must never claim a new file was saved. */
static unsigned recording_value(const comp_runtime_frame_t *f)
{
    unsigned value=(unsigned)f->recording;
    if(value>8u)return 9u;
    if(f->prepare_pending || f->start_pending)return 1u;
    if(f->recording==DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY)return 8u;
    /* The logical session remains RECORDING while its microphone is paused.
     * Use the same immutable pause snapshot as the status rail. */
    if(f->recording==DENZIC_AUDIO_RECORDING_STATE_RECORDING && f->recording_paused)return 14u;
    if(f->recording!=DENZIC_AUDIO_RECORDING_STATE_RECORDING) {
        if(f->record_stop_reason==COMP_RECORD_STOP_LOW_BATTERY)
            return f->recording==DENZIC_AUDIO_RECORDING_STATE_STOPPING?12u:11u;
        if(f->record_stop_reason==COMP_RECORD_STOP_POWER_UNKNOWN &&
           f->recording!=DENZIC_AUDIO_RECORDING_STATE_STOPPING)return 13u;
    }
    if(!value && f->last_result!=COMP_RUNTIME_OK &&
       f->menu_feedback==COMP_RUNTIME_MENU_FEEDBACK_NONE)
        value=f->last_result==COMP_RUNTIME_UNAVAILABLE?9u:f->last_result==COMP_RUNTIME_BUSY?10u:8u;
    return value;
}
static bool recording_reason_label(comp_runtime_renderer_t *r,uint8_t *frame,
    unsigned locale,unsigned label,unsigned left,unsigned top)
{
    if(locale>=3u || label>=COMP_RECORD_REASON_LABEL_COUNT || top>186u)return false;
    const unsigned width=comp_record_reason_widths[locale][label];
    if(left+width>200u)return false;
#if COMPANION_WBA_UI_EXTERNAL && defined(COMP_WBA_EXTERNAL_RECORD_REASON)
    return bitmap_paint(r,frame,&comp_record_reason_external[locale][label],
        COMP_RECORD_REASON_LABEL_STRIDE,width,COMP_RECORD_REASON_LABEL_HEIGHT,left,top);
#else
    comp_bitmap_stream_t stream={.next=comp_record_reason_bits+comp_record_reason_offsets[locale][label]};
    for(unsigned y=0u;y<COMP_RECORD_REASON_LABEL_HEIGHT;++y) {
        if(!progress(r))return false;
        for(unsigned byte=0u;byte<COMP_RECORD_REASON_LABEL_STRIDE;++byte) {
            const uint8_t bits=comp_bitmap_stream_byte(&stream);
            for(unsigned bit=0u;bit<8u && byte*8u+bit<width;++bit)
                if(!(bits&(0x80u>>bit)))paint(frame,left+byte*8u+bit,top+y,false);
        }
    }
    return true;
#endif
}
#endif
static bool COMP_RENDER_UI_SMALL menu_catalog(comp_runtime_renderer_t *r,const comp_runtime_frame_t *f,uint8_t *frame)
{
    const comp_screen_menu_t *menu=&f->menu;
    comp_screen_framebuffer_t fb;char value[12];
#if COMPANION_WBA_RESOURCE_PROFILE
    if(menu->view==COMP_SCREEN_MENU_VIEW_BROWSER_ABOUT) {
        if(!comp_screen_framebuffer_init(&fb,frame,5000,200,200))return false;
        const comp_runtime_resources_t *resources=mounted_menu_resources(r);
        for(unsigned row=1u;row<=2u;++row) {
            const int y=COMP_WBA_MENU_ROW_TOP+((int)row-(int)menu->home_page)*(int)COMP_WBA_MENU_ROW_HEIGHT;
            if(y<(int)COMP_WBA_MENU_ROW_TOP || y>=(int)COMP_WBA_MENU_BODY_BOTTOM)continue;
            memcpy(value,"--",3u);
            if(row==1u) {
#if defined(COMPANION_WBA_APP_VERSION) && COMPANION_WBA_APP_VERSION >= 0x010100u && COMPANION_WBA_APP_VERSION < 0x020000u
                /* This product's retained 1.1 release series is base+counter.
                 * Releases above255 carry into the next byte; decoding the
                 * low byte as a semantic patch would mislabel FW329 as73. */
                (void)snprintf(value,sizeof(value),"1.1.%u",(unsigned)(COMPANION_WBA_APP_VERSION-0x010100u));
#endif
            } else if(resources)
                (void)snprintf(value,sizeof(value),"%lu",(unsigned long)resources->generation.root.generation);
            if(!menu_number(r,&fb,y+COMP_WBA_MENU_VALUE_TOP,value))return false;
        }
    }
    if(menu->view==COMP_SCREEN_MENU_VIEW_BROWSER_STORAGE) {
        if(!comp_screen_framebuffer_init(&fb,frame,5000,200,200))return false;
        const comp_runtime_resources_t *resources=mounted_menu_resources(r);
        /* These are maximum matched-layout extents, not current free bytes.
         * Metadata is excluded from the recording/update shared payload. */
        for(unsigned row=4u;row<=6u;row+=2u) {
            const int y=COMP_WBA_MENU_ROW_TOP+((int)row-(int)menu->home_page)*(int)COMP_WBA_MENU_ROW_HEIGHT;
            if(y<(int)COMP_WBA_MENU_ROW_TOP || y>=(int)COMP_WBA_MENU_BODY_BOTTOM)continue;
            memcpy(value,"--",3u);
            if(resources && resources->store->size_bytes==COMP_WBA_NOR_UI_BYTES) {
                const uint32_t bytes=row==4u?COMP_WBA_NOR_RECORDING_DATA_BYTES:resources->store->size_bytes;
                (void)snprintf(value,sizeof(value),"%lu KB",(unsigned long)(bytes/1024u));
            }
            if(row==4u && menu->language==COMP_SCREEN_MENU_LANGUAGE_EN) {
                /* Reuse the already decoded native label without rerasterizing
                 * or scaling it. A live capacity is wider than old "8 MiB";
                 * give English the same two-line row as recording status. */
                for(unsigned py=0u;py<14u;++py)
                    memmove(frame+((unsigned)y+1u+py)*25u+2u,
                        frame+((unsigned)y+COMP_WBA_MENU_VALUE_TOP+py)*25u+2u,17u);
                comp_screen_framebuffer_fill_rect(&fb,152,(int16_t)(y+1),32,14,false);
                comp_screen_framebuffer_fill_rect(&fb,16,(int16_t)(y+15),168,19,false);
                if(!menu_number_at(r,&fb,16,y+COMP_WBA_MENU_STACK_VALUE_TOP,168,value,false))return false;
            } else if(!menu_number(r,&fb,y+COMP_WBA_MENU_VALUE_TOP,value))return false;
        }
    }
#if COMPANION_WBA_RESOURCE_GENERATION >= 64u
    if(menu->view==COMP_SCREEN_MENU_VIEW_BROWSER_INTERACTION && menu->home_page==4u) {
        if(!comp_screen_framebuffer_init(&fb,frame,5000,200,200) ||
           !pet_help_label(r,(unsigned)menu->language,4u,frame,16u,128u))return false;
        pet_help_press(&fb,menu,6u,120,34u);
    }
#endif
    if(menu->view==COMP_SCREEN_MENU_VIEW_BROWSER_DISPLAY && menu->home_page==0u) {
        const unsigned locale=(unsigned)menu->language;
        const unsigned choice=menu->browser.battery_fill?2u:1u;
        const int y=COMP_WBA_MENU_ROW_TOP+COMP_WBA_MENU_ROW_HEIGHT;
        if(locale>2u || !comp_screen_framebuffer_init(&fb,frame,5000,200,200))return false;
        /* Replace only the old static status-bar row. Existing resource
         * IDs, clock options, page geometry and navigation stay compatible. */
        comp_screen_framebuffer_fill_rect(&fb,12,(int16_t)y,176,34,false);
        for(unsigned item=0;item<2u;++item) {
            const unsigned index=item?choice:0u;
            const unsigned width=comp_battery_display_widths[locale][index];
            const unsigned left=item?168u-width:16u;
#if COMPANION_WBA_UI_EXTERNAL && COMPANION_WBA_RESOURCE_GENERATION >= 69u
            if(!bitmap_paint(r,frame,&comp_battery_display_labels[locale][index],9u,
                width,14u,left,(unsigned)y+COMP_WBA_MENU_VALUE_TOP))return false;
#else
            const uint8_t *bits=comp_battery_display_labels[locale][index];
            for(unsigned row=0;row<14u;++row)for(unsigned col=0;col<width;++col)
                if(!(bits[row*9u+col/8u]&(0x80u>>(col%8u))))
                    comp_screen_framebuffer_set_pixel(&fb,(int16_t)(left+col),
                        (int16_t)(y+COMP_WBA_MENU_VALUE_TOP+row),true);
#endif
        }
        comp_screen_framebuffer_draw_line(&fb,179,(int16_t)(y+11),179,(int16_t)(y+23),true);
        comp_screen_framebuffer_draw_line(&fb,176,(int16_t)(y+14),179,(int16_t)(y+11),true);
        comp_screen_framebuffer_draw_line(&fb,179,(int16_t)(y+11),182,(int16_t)(y+14),true);
        comp_screen_framebuffer_draw_line(&fb,176,(int16_t)(y+20),179,(int16_t)(y+23),true);
        comp_screen_framebuffer_draw_line(&fb,179,(int16_t)(y+23),182,(int16_t)(y+20),true);
    }
    if(menu->view==COMP_SCREEN_MENU_VIEW_BROWSER_CLEAR_RECORDINGS) {
        if(!comp_screen_framebuffer_init(&fb,frame,5000,200,200))return false;
        (void)snprintf(value,sizeof(value),"%u",(unsigned)menu->browser.recording_count);
        return menu_confirmation_count(r,&fb,value);
    }
    if(menu->home_page==0 && (menu->view==COMP_SCREEN_MENU_VIEW_BROWSER_VOICE ||
                              menu->view==COMP_SCREEN_MENU_VIEW_BROWSER_POWER)) {
        if(!comp_screen_framebuffer_init(&fb,frame,5000,200,200))return false;
        if(menu->view==COMP_SCREEN_MENU_VIEW_BROWSER_VOICE) {
            const int top=COMP_WBA_MENU_ROW_TOP;
            comp_screen_framebuffer_fill_rect(&fb,12,(int16_t)top,164,34,false);
            if(!pet_play_label(r,(unsigned)menu->language,
                (menu->flags&COMP_SCREEN_MENU_FLAG_RECORDING)?2u:3u,
                frame,16u,(unsigned)top+8u))return false;
        }
        if(menu->view==COMP_SCREEN_MENU_VIEW_BROWSER_POWER) {
            unsigned percent=f->status_packed>>24u;
            if((f->status_packed&(1u<<17)) && percent<=100u) {
                (void)snprintf(value,sizeof(value),(f->status_packed&COMP_SCREEN_STATUS_ESTIMATED_BATTERY)?"~%u%%":"%u%%",percent);
                if(!menu_number(r,&fb,COMP_WBA_MENU_ROW_TOP+COMP_WBA_MENU_VALUE_TOP,value))return false;
            } else if(f->battery_mv>=1000u && f->battery_mv<=5000u) {
                (void)snprintf(value,sizeof(value),"%u.%02uV",
                    (unsigned)(f->battery_mv/1000u),(unsigned)((f->battery_mv%1000u)/10u));
                if(!menu_number(r,&fb,COMP_WBA_MENU_ROW_TOP+COMP_WBA_MENU_VALUE_TOP,value))return false;
            } else if(!menu_number(r,&fb,COMP_WBA_MENU_ROW_TOP+COMP_WBA_MENU_VALUE_TOP,"--"))return false;
            if(f->battery_mv>=1000u && f->battery_mv<=5000u) {
                unsigned mv=f->battery_mv;
                const char volts[7]={'~',(char)('0'+mv/1000u),'.',
                    (char)('0'+mv/100u%10u),(char)('0'+mv/10u%10u),'V',0};
                const char *shown=volts+((f->status_packed&COMP_SCREEN_STATUS_ESTIMATED_BATTERY)?0u:1u);
                comp_screen_framebuffer_draw_text(&fb,
                    (int16_t)(184u-strlen(shown)*6u),
                    COMP_WBA_MENU_ROW_TOP+COMP_WBA_MENU_ROW_HEIGHT-9u,shown,1u,true);
            }
            /* Replace the authored unknown charge field only from live,
             * qualified feedback. Powered idle is a plug, never "full". */
            const int16_t y=COMP_WBA_MENU_ROW_TOP+COMP_WBA_MENU_ROW_HEIGHT+COMP_WBA_MENU_VALUE_TOP;
            comp_screen_framebuffer_fill_rect(&fb,100,y,84,14,false);
            if(f->status_packed&COMP_SCREEN_STATUS_CHARGER_FAULT)
                comp_screen_framebuffer_draw_text(&fb,178,(int16_t)(y+3),"!",1,true);
            else if(f->status_packed&COMP_SCREEN_STATUS_CHARGING) {
                comp_screen_framebuffer_draw_line(&fb,183,y,178,(int16_t)(y+5),true);
                comp_screen_framebuffer_draw_line(&fb,178,(int16_t)(y+5),183,(int16_t)(y+5),true);
                comp_screen_framebuffer_draw_line(&fb,183,(int16_t)(y+5),179,(int16_t)(y+10),true);
            } else if(f->status_packed&COMP_SCREEN_STATUS_EXTERNAL_POWER) {
                comp_screen_framebuffer_draw_line(&fb,179,y,179,(int16_t)(y+2),true);
                comp_screen_framebuffer_draw_line(&fb,182,y,182,(int16_t)(y+2),true);
                comp_screen_framebuffer_stroke_rect(&fb,178,(int16_t)(y+2),6,5,1,true);
                comp_screen_framebuffer_draw_line(&fb,181,(int16_t)(y+7),181,(int16_t)(y+10),true);
            } else comp_screen_framebuffer_draw_text(&fb,172,(int16_t)(y+3),"--",1,true);
        } else {
            const unsigned index=recording_value(f);
            if((unsigned)menu->language>COMP_SCREEN_MENU_LANGUAGE_ZH_TW)return false;
            const unsigned locale=(unsigned)menu->language;
            const bool stacked=menu->language==COMP_SCREEN_MENU_LANGUAGE_EN;
            const unsigned field_left=stacked?COMP_WBA_MENU_STACK_VALUE_LEFT:COMP_WBA_MENU_VALUE_LEFT;
            const unsigned field_width=stacked?COMP_WBA_MENU_STACK_VALUE_WIDTH:COMP_WBA_MENU_VALUE_WIDTH;
            const int16_t value_y=(int16_t)(COMP_WBA_MENU_ROW_TOP+COMP_WBA_MENU_ROW_HEIGHT+
                (stacked?COMP_WBA_MENU_STACK_VALUE_TOP:COMP_WBA_MENU_VALUE_TOP));
            const unsigned glyph_width=index<11u?comp_wba_live_value_advance[locale][index]:
                comp_record_reason_widths[locale][index-11u];
            if(glyph_width>field_width)return false;
            const unsigned glyph_left=stacked?field_left:field_left+field_width-glyph_width;
            comp_screen_framebuffer_fill_rect(&fb,(int16_t)field_left,value_y,
                (uint16_t)field_width,COMP_WBA_LIVE_VALUE_HEIGHT,false);
            if(index>=11u) {
                if(!recording_reason_label(r,frame,locale,index-11u,glyph_left,(unsigned)value_y))return false;
            } else {
                comp_bitmap_ref_t glyph=COMP_BITMAP_REF(comp_wba_live_values[locale][index]);
                if(!bitmap_paint(r,frame,glyph,COMP_WBA_LIVE_VALUE_STRIDE,
                    glyph_width,COMP_WBA_LIVE_VALUE_HEIGHT,glyph_left,(unsigned)value_y))return false;
            }
        }
    }
#endif
    if(menu->view!=COMP_SCREEN_MENU_VIEW_BROWSER_STORAGE &&
       menu->view!=COMP_SCREEN_MENU_VIEW_BROWSER_CLEAR_RECORDINGS)return true;
    if(!comp_screen_framebuffer_init(&fb,frame,5000,200,200))return false;
    /* WBA uses its generated row geometry; WB retains the accepted catalog
     * overlay. Preserve uint16 KiB and follow the actual scrolled row. */
    for(unsigned row=0;row<2u;++row) {
#if COMPANION_WBA_RESOURCE_PROFILE
        int y=COMP_WBA_MENU_ROW_TOP+((int)row-(int)menu->home_page)*(int)COMP_WBA_MENU_ROW_HEIGHT;
        if(y<(int)COMP_WBA_MENU_ROW_TOP || y>=(int)COMP_WBA_MENU_BODY_BOTTOM ||
           (row && menu->view!=COMP_SCREEN_MENU_VIEW_BROWSER_STORAGE))continue;
#else
        int y=45+((int)row-(int)menu->home_page)*40;
        if(y<45 || y>=200 || (row && menu->view!=COMP_SCREEN_MENU_VIEW_BROWSER_STORAGE))continue;
#endif
#if COMPANION_WBA_RESOURCE_PROFILE
        if(!row) (void)snprintf(value,sizeof(value),"%u",(unsigned)menu->browser.recording_count);
        else (void)snprintf(value,sizeof(value),"%u KB",(unsigned)menu->browser.recording_storage_kb);
        if(!menu_number(r,&fb,y+COMP_WBA_MENU_VALUE_TOP,value))return false;
#else
        if(!row) {
            (void)snprintf(value,sizeof(value),"%u",(unsigned)menu->browser.recording_count);
            comp_screen_framebuffer_fill_rect(&fb,168,(int16_t)(y+3),9,11,false);
            comp_screen_framebuffer_draw_text(&fb,170,(int16_t)(y+5),value,1,true);
        } else {
            (void)snprintf(value,sizeof(value),"%uKB",(unsigned)menu->browser.recording_storage_kb);
            comp_screen_framebuffer_fill_rect(&fb,124,(int16_t)(y+1),70,16,false);
            comp_screen_framebuffer_draw_text(&fb,(int16_t)(194-(int)strlen(value)*6),(int16_t)(y+5),value,1,true);
        }
#endif
    }
    return true;
}

#if COMPANION_WBA_RESOURCE_PROFILE
static void COMP_RENDER_UI_SMALL menu_scroll(const comp_screen_menu_t *menu,uint8_t *frame)
{
    comp_screen_framebuffer_t fb;
    const unsigned pages=comp_screen_menu_browser_page_count(menu->view);
    if(pages<2u || !comp_screen_framebuffer_init(&fb,frame,5000,200,200))return;
    const unsigned arrival=menu->home_scroll_offset_px & COMP_SCREEN_MENU_SCROLL_ARRIVAL_MASK;
    if(arrival) {
        /* One12px native arrival, never synthetic high-rate interpolation.
         * Header/feedback stay fixed, and moving contents are not hittable. */
        const unsigned top=46u,bottom=188u,step=12u;
        if(arrival==1u) {
            memmove(frame+(top+step)*25u,frame+top*25u,(bottom-top-step)*25u);
            memset(frame+top*25u,255u,step*25u);
        } else {
            memmove(frame+top*25u,frame+(top+step)*25u,(bottom-top-step)*25u);
            memset(frame+(bottom-step)*25u,255u,step*25u);
        }
    }
    /* Customer lists retain overlapping context. Rail position follows
     * the actual first row; thumb size represents four visible rows. */
    comp_screen_framebuffer_fill_rect(&fb,72,190,56,10,false);
    comp_screen_framebuffer_fill_rect(&fb,193,46,7,142,false);
    const bool customer=comp_screen_menu_customer_active();
    const unsigned height=customer?512u/(pages+3u):128u/pages;
    unsigned position=(customer?menu->home_page:menu->home_page/4u)*2u;
    if(arrival==1u && position) --position;
    else if(arrival==2u) ++position;
    if(position>(pages-1u)*2u)position=(pages-1u)*2u;
    const unsigned y=52u+position*(128u-height)/((pages-1u)*2u);
    comp_screen_framebuffer_draw_line(&fb,196,52,196,179,true);
    comp_screen_framebuffer_fill_rect(&fb,194,(int16_t)y,4,(uint16_t)height,true);
}
#endif
#include "customer_menu_renderer.h"
#if COMPANION_WBA_RESOURCE_PROFILE && COMPANION_WBA_UI_EXTERNAL && COMPANION_WBA_RESOURCE_GENERATION >= 84u
#include "generated/companion_storage_full_labels.h"
static void storage_full_label(comp_screen_framebuffer_t *fb,uint8_t *frame,unsigned locale)
{
    if(locale==COMP_SCREEN_MENU_LANGUAGE_ZH || locale==COMP_SCREEN_MENU_LANGUAGE_ZH_TW) {
        const uint8_t *glyph=comp_storage_full_labels[locale==COMP_SCREEN_MENU_LANGUAGE_ZH_TW?1u:0u];
        for(unsigned y=0u;y<16u;++y)for(unsigned x=0u;x<32u;++x)
            if(!(glyph[y*4u+x/8u]&(0x80u>>(x%8u))))paint(frame,104u+x,180u+y,false);
    } else comp_screen_framebuffer_draw_text(fb,104,180,"FULL",2,true);
}
#endif
bool comp_runtime_renderer_render(void *context, const comp_runtime_frame_t *f, uint8_t frame[5000])
{
    enum {
        WAVE_X_BEGIN = COMP_SSD1681_WBA_RECORDING_X_MIN,
        WAVE_X_END = COMP_SSD1681_WBA_RECORDING_X_MAX + 1u,
        WAVE_SOURCE_Y = 156u,
        WAVE_DEST_Y = COMP_SSD1681_WBA_RECORDING_Y_MIN,
        WAVE_HEIGHT = COMP_SSD1681_WBA_RECORDING_Y_MAX - COMP_SSD1681_WBA_RECORDING_Y_MIN + 1u,
        WAVE_ROW_BYTES = 6u
    };
    comp_runtime_renderer_t *r=context;
    uint8_t wave_pixels[WAVE_HEIGHT][WAVE_ROW_BYTES];
    const bool wave_visible=f && f->surface==COMP_SCREEN_SURFACE_HOME &&
        f->recording==DENZIC_AUDIO_RECORDING_STATE_RECORDING;
    const bool speaker_visible=false; /* Owner: cues do not imply speech. */
    if (!r || !f || !frame || f->token==0 || r->pending || f->family >= COMP_BROWSER_FAMILY_COUNT) return false;
    if (!progress(r)) return false;
    r->pending_base_valid=false;
    r->pending_opens_eyes=false;
    r->pending_eye_closed_mask=0u;
    /* Retain the recovered native-position overlay separately from the face.
     * White is transparent: removing or changing the wave restores the clean
     * base, without erasing a cheek that shares its rectangular bounds. */
    if(wave_visible || speaker_visible) {
        char wave[32];
        if(speaker_visible)memcpy(wave,"speaker_original",sizeof("speaker_original"));
        else (void)snprintf(wave,sizeof(wave),"recording_timeline_%02u",(unsigned)(f->recording_wave_index%64u));
        if(!state(r,wave,frame))return false;
        for(unsigned y=0;y<WAVE_HEIGHT;++y)
            memcpy(wave_pixels[y],&frame[(y+WAVE_SOURCE_Y)*25u+(speaker_visible?19u:0u)],WAVE_ROW_BYTES);
    }
    if(f->kind==COMP_RUNTIME_FRAME_SLEEP) {
        if(!face(r,f,frame))return false;
        r->pending_base_valid=true;r->pending_family=f->family;
        r->pending_eye_closed_mask=r->pending_base_eye_closed_mask;
    } else if (f->surface==COMP_SCREEN_SURFACE_LOW_POWER) {
        /* Park the accepted pet with closed eyelids. Sleep cancels animation
         * in the runtime; clearing all ink only makes a healthy device look
         * broken and is not needed to retain an e-paper image. Keep this
         * transient eyelid out of the clean base used on the next wake. */
        if(r->base_valid) {
            if(!blink(r,frame))return false;
            r->pending_eye_closed_mask=3u;
        } else {
            /* Sleep can precede the first successful home commit. Use the
             * existing authored sleepy family rather than an empty fallback. */
            comp_runtime_frame_t sleeping=*f;
            sleeping.kind=COMP_RUNTIME_FRAME_STATUS;
            sleeping.family=COMP_BROWSER_FAMILY_SLEEPY;
            if(!face(r,&sleeping,frame))return false;
            r->pending_base_valid=true;
            r->pending_family=sleeping.family;
            r->pending_eye_closed_mask=r->pending_base_eye_closed_mask;
        }
    } else if(f->surface==COMP_SCREEN_SURFACE_HOME && (f->status_packed&COMP_SCREEN_STATUS_UPDATING)) {
        /* Reuse one original thoughtful/warm whole face. No spinner, random
         * mouth or new artwork; only real progress/stage updates request ink. */
        if(r->base_valid && r->base_family==f->family) {
            if(!face_cache_load(r,r->base,r->base_bytes,frame))return false;
            r->pending_eye_closed_mask=r->base_eye_closed_mask;
        } else {
            if(!face(r,f,frame))return false;
            r->pending_base_valid=true;r->pending_family=f->family;
            r->pending_eye_closed_mask=r->pending_base_eye_closed_mask;
        }
    } else if (f->surface==COMP_SCREEN_SURFACE_MENU) {
        char id[96];
#if COMPANION_WBA_RESOURCE_PROFILE && COMPANION_WBA_UI_EXTERNAL && COMPANION_WBA_RESOURCE_GENERATION >= 84u
        if(f->menu.view!=COMP_SCREEN_MENU_VIEW_BROWSER_QUICK && f->menu.view!=COMP_SCREEN_MENU_VIEW_BROWSER_PET_HELP &&
           f->menu.view!=COMP_SCREEN_MENU_VIEW_BROWSER_CLEAR_RECORDINGS && f->menu.view!=COMP_SCREEN_MENU_VIEW_BROWSER_RESTORE_DEFAULTS) {
            if(!customer_menu_render(r,f,frame))return false;
        } else
#endif
#if COMPANION_WBA_RESOURCE_PROFILE && COMPANION_WBA_RESOURCE_GENERATION >= 64u
#if COMPANION_WBA_UI_EXTERNAL && COMPANION_WBA_RESOURCE_GENERATION >= 71u
        if(f->menu.view==COMP_SCREEN_MENU_VIEW_BROWSER_QUICK) {
            if(!quick_controls(r,f,frame))return false;
        } else
#endif
        if(f->menu.view==COMP_SCREEN_MENU_VIEW_BROWSER_PET_HELP) {
            if(!pet_help(r,f,frame))return false;
        } else
#endif
        if (!comp_screen_menu_is_browser_view(f->menu.view) ||
            !companion_browser_menu_state_id_format(id,sizeof(id),(uint8_t)f->menu.language,
                (uint8_t)(f->menu.view-COMP_SCREEN_MENU_VIEW_BROWSER_HOME),f->menu.home_page,255,0,
                comp_screen_menu_browser_variant(&f->menu)) || !state(r,id,frame) ||
#if COMPANION_WBA_RESOURCE_PROFILE
                !menu_priority_rows(&f->menu,frame) ||
#endif
                !menu_catalog(r,f,frame)) return false;
#if COMPANION_WBA_RESOURCE_PROFILE
        menu_scroll(&f->menu,frame);
#endif
    } else if (f->kind==COMP_RUNTIME_FRAME_HOLD) {
        if (f->hold_bucket >= COMPANION_BROWSER_INTERACTION_MENU_HOLD_MILESTONE_COUNT) return false;
        if(r->base_valid) {
            if(!face_cache_load(r,r->base,r->base_bytes,frame))return false;
            r->pending_eye_closed_mask=r->base_eye_closed_mask;
        } else {
            if(!face(r,f,frame))return false;
            r->pending_eye_closed_mask=r->pending_base_eye_closed_mask; }
    } else if (f->kind==COMP_RUNTIME_FRAME_BLINK) {
        if (!r->base_valid) return false;
        if(!face_cache_load(r,r->base,r->base_bytes,frame))return false;
        r->pending_eye_closed_mask=r->base_eye_closed_mask;
    } else if (r->base_valid && (f->kind==COMP_RUNTIME_FRAME_STATUS || f->kind==COMP_RUNTIME_FRAME_RECORDING_WAVE)) {
        /* Status/wave clocks never reveal a target family before its authored
         * reaction/life frame has visibly committed. */
        if(!face_cache_load(r,r->base,r->base_bytes,frame))return false;
        r->pending_eye_closed_mask=r->base_eye_closed_mask;
    } else {
        if (!face(r,f,frame)) return false;
        r->pending_base_valid=true; r->pending_family=f->family;
        r->pending_eye_closed_mask=r->pending_base_eye_closed_mask;
    }
    if(f->surface==COMP_SCREEN_SURFACE_HOME && f->blink_closed &&
        (r->pending_base_valid || !r->base_valid || !blink(r,frame))) return false;
    if(f->surface==COMP_SCREEN_SURFACE_HOME && f->blink_closed) r->pending_eye_closed_mask=3u;
    r->pending_opens_eyes=f->surface==COMP_SCREEN_SURFACE_HOME &&
        (r->visible_eye_closed_mask & (uint8_t)~r->pending_eye_closed_mask)!=0u;
    if (wave_visible || speaker_visible) {
        const unsigned left=speaker_visible?159u:WAVE_X_BEGIN;
        const unsigned right=speaker_visible?198u:WAVE_X_END;
        const unsigned first_byte=speaker_visible?19u:0u;
        for(unsigned y=0;y<WAVE_HEIGHT;++y)for(unsigned x=left;x<right;++x) {
            unsigned i=(y+WAVE_DEST_Y)*25u+x/8u; uint8_t mask=(uint8_t)(0x80u>>(x%8u));
            frame[i] &= (uint8_t)(wave_pixels[y][x/8u-first_byte] | (uint8_t)~mask);
        }
    }
    if (!status(f,frame)) return false;
#if COMPANION_WBA_RESOURCE_PROFILE && COMPANION_WBA_RESOURCE_GENERATION >= 64u
    if((f->surface==COMP_SCREEN_SURFACE_HOME || f->surface==COMP_SCREEN_SURFACE_LOW_POWER) &&
       !pet_accessory(r,f,frame))return false;
#endif
#if COMPANION_WBA_RESOURCE_PROFILE && COMPANION_WBA_RESOURCE_GENERATION >= 63u
    /* Text is a transient overlay; it never enters the clean committed face. */
    if(!local_reply_caption(r,f,frame))return false;
#endif
#if COMPANION_WBA_RESOURCE_PROFILE && COMPANION_WBA_RESOURCE_GENERATION >= 64u
    if(!discovery_caption(r,f,frame))return false;
    if(f->pet_play_caption && f->surface==COMP_SCREEN_SURFACE_HOME) {
        comp_screen_framebuffer_t fb;
        if(!comp_screen_framebuffer_init(&fb,frame,5000u,200u,200u))return false;
        comp_screen_framebuffer_fill_rect(&fb,12,174,176,26,false);
        const unsigned label=f->pet_play_caption==COMP_PET_PLAY_CAPTION_RETRY?4u:
            f->pet_play_caption==COMP_PET_PLAY_CAPTION_FOUND?5u:
            f->pet_play_caption==COMP_PET_PLAY_CAPTION_ENDED?6u:
            f->pet_play_caption==COMP_PET_PLAY_CAPTION_RECORD_STOP?2u:
            f->pet_play_caption==COMP_PET_PLAY_CAPTION_NEXT?7u:1u;
        if(!pet_play_label(r,(unsigned)f->menu.language,label,frame,20u,178u))return false;
        /* The original sparkle in pet_accessory carries the target. Keep
         * the face and one object; do not add arrows, answer boxes or a
         * second retry hint that competes with the pet. */
    }
#endif
#if COMPANION_WBA_RESOURCE_PROFILE
    if(f->record_saved_notice && f->surface==COMP_SCREEN_SURFACE_HOME) {
#if COMPANION_WBA_UI_EXTERNAL && COMPANION_WBA_RESOURCE_GENERATION >= 84u
        comp_screen_framebuffer_t fb;
        if(!comp_screen_framebuffer_init(&fb,frame,5000u,200u,200u))return false;
        comp_screen_framebuffer_fill_rect(&fb,12,174,176,26,false);
        if(f->record_stop_reason==COMP_RECORD_STOP_STORAGE_FULL) {
            if(!customer_word(r,f,frame,COMP_CUSTOM_STORAGE,65,180,2))return false;
            storage_full_label(&fb,frame,(unsigned)f->menu.language);
        } else if(!customer_word(r,f,frame,COMP_CUSTOM_SAVED_PC,100,180,2))return false;
#endif
    }
    if(f->kind==COMP_RUNTIME_FRAME_HOLD && f->surface==COMP_SCREEN_SURFACE_HOME) {
#if COMPANION_WBA_UI_EXTERNAL && COMPANION_WBA_RESOURCE_GENERATION >= 84u
        /* The existing four qualified progress frames carry their own cue.
         * No shorter hold, extra panel activation or permanent home caption. */
        comp_screen_framebuffer_t fb;
        if(!comp_screen_framebuffer_init(&fb,frame,5000u,200u,200u))return false;
        comp_screen_framebuffer_fill_rect(&fb,12,174,176,26,false);
        if(!customer_word(r,f,frame,COMP_CUSTOM_MENU,100,180,2))return false;
#endif
    }
    if (f->surface == COMP_SCREEN_SURFACE_MENU) {
        /* Menu-only readable clock uses the existing small numeric atlas.
         * Its 32px field ends before the hold milestones at x=38. Unknown
         * time remains --:--; the validated packed clock is the same source. */
        comp_screen_framebuffer_t fb;char clock[6];
        if(!comp_screen_framebuffer_init(&fb,frame,5000,200,200))return false;
        if(f->status_packed&0x8000u)
            (void)snprintf(clock,sizeof(clock),"%02u:%02u",
                (unsigned)((f->status_packed>>8u)&31u),(unsigned)(f->status_packed&63u));
        else memcpy(clock,"--:--",6);
        if(!menu_number_at(r,&fb,6,3,32,clock,true) || !menu_feedback(r,f,frame))return false;
    }
#endif
    r->token=f->token; r->pending=true;
    return true;
}
bool comp_runtime_renderer_complete(comp_runtime_renderer_t *r, uint32_t token, bool visible)
{
    if (!r || !r->pending || token != r->token) return false;
    if (visible && r->pending_base_valid) {
        memcpy(r->base,r->pending_base,r->pending_base_bytes);
        r->base_bytes=r->pending_base_bytes;r->base_valid=true;r->base_family=r->pending_family;
        r->base_eye_closed_mask=r->pending_base_eye_closed_mask;
        r->base_pet_seed=r->pending_pet_seed;r->base_pet_variant=r->pending_pet_variant;
        r->base_pet_float=r->pending_pet_float;
    }
    if (visible) r->visible_eye_closed_mask=r->pending_eye_closed_mask;
    r->pending=false; r->pending_base_valid=false; r->pending_opens_eyes=false;
    return true;
}

