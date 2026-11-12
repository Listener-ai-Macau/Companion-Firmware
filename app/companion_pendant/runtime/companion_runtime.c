#include "companion_runtime.h"
#if COMPANION_WBA_RESOURCE_PROFILE
#include "companion_wba_resource_contract.h"
#endif
#include "companion_recording_hold_ui.h"
#include "companion_pet_chat.h"
#include "companion_browser_interaction_contract.h"
#include "power_settings_store.h"
#include "companion_pet_gaze.h"
#include "companion_pet_caption_policy.h"
#if COMPANION_WBA_RESOURCE_PROFILE
#include "companion_wba_resource_contract.h"
#endif
#if defined(COMPANION_WBA_SCREEN_ENABLED) && !COMPANION_WBA_SCREEN_ENABLED
#define COMP_RUNTIME_VISUAL 0
#else
#define COMP_RUNTIME_VISUAL 1
#endif
#if COMP_RUNTIME_VISUAL && COMPANION_WBA_RESOURCE_PROFILE && COMPANION_WBA_RESOURCE_GENERATION >= 64u
#define COMP_RUNTIME_PET_MOTION 1
#else
#define COMP_RUNTIME_PET_MOTION 0
#endif
#include <string.h>

#define DISPLAY_RETRY_MS 480u
#define DISPLAY_FAST_RETRIES 2u
#define DISPLAY_FAILURE_STREAK_LIMIT 7u

enum { PET_STROKE_NONE, PET_STROKE_RIGHT, PET_STROKE_LEFT,
       PET_STROKE_READY, PET_STROKE_CONSUMED, PET_STROKE_DISABLED };
#define PET_STROKE_LEG_PX 32u
#define PET_STROKE_RETURN_PX 24u
#define PET_STROKE_MIN_MS 600u
enum { RECORD_NOTICE_NONE, RECORD_NOTICE_SAVED_PENDING, RECORD_NOTICE_SAVED_VISIBLE,
       RECORD_NOTICE_STOP_PENDING, RECORD_NOTICE_STOP_VISIBLE };
/* A quick finger path can finish before a single ink transaction. Let its
 * latest qualified direction read as attention after release, before centre.
 * This is visible dwell, never a faster transaction or an input queue. */
#define PET_GAZE_RELEASE_HOLD_MS 1100u
#define PET_OPTIONAL_REPLY_POSE_BUDGET_MS 350u
#define PET_MOTION_CARRIED 0x80u
#define PET_MOTION_LEASE_MS 8000u
#define PET_DEFERRED_INTENT_MAX_MS 3000u
#define PET_DEFERRED_MOTION_MAX_MS 1500u
enum { QUICK_CONTACT_NONE, QUICK_CONTACT_PULL, QUICK_CONTACT_VOLUME,
       QUICK_CONTACT_CANCELLED, QUICK_CONTACT_RECORD_LOCK, QUICK_CONTACT_RECORD_UNLOCK };

static bool pet_carried(const comp_runtime_t *r)
{ return (r->orientation & PET_MOTION_CARRIED) != 0u; }
static bool pet_motion_intent(const comp_runtime_t *r)
{
#if COMP_PET_PROCEDURAL
    return r->pet.interaction>=COMP_PET_PICKUP && r->pet.interaction<=COMP_PET_INVERTED;
#else
    (void)r;return false;
#endif
}

/* Handling has a distinct landed feeling; posture keeps its original
 * temporary tilt/inversion policy and returns to the accepted daily mood. */
static bool pet_handling_intent(const comp_runtime_t *r)
{
#if COMP_PET_PROCEDURAL
    return r->pet.interaction>=COMP_PET_PICKUP && r->pet.interaction<=COMP_PET_SETTLE;
#else
    (void)r;return false;
#endif
}

static bool reply_pose_available(uint8_t family,uint8_t zone)
{
#if COMPANION_WBA_RESOURCE_PROFILE
#if COMPANION_WBA_RESOURCE_GENERATION == 84u
    /* Both authored arrive/release states must exist in this matched bank.
     * UI84 c0cb8fe4: checked FNV catalog. Bits center/up/down/left/right. */
    static const uint8_t zones[COMP_BROWSER_FAMILY_COUNT]={0u,10u,3u,15u,25u,1u,12u,0u,0u,0u};
    return family<COMP_BROWSER_FAMILY_COUNT && zone<=COMP_BROWSER_TAP_ZONE_RIGHT &&
        (zones[family]&(1u<<zone))!=0u;
#else
    (void)family;(void)zone;return false; /* New banks publish their capability. */
#endif
#else
    (void)family;(void)zone;return true;
#endif
}
static uint8_t reply_pose_count(const comp_runtime_t *r,uint32_t transaction_ms)
{
    if(r->reaction_route_count &&
       (!reply_pose_available((uint8_t)r->reaction_route[1],r->reaction_zone) ||
        (r->reaction_route_count>1u && !reply_pose_available((uint8_t)r->reaction_route[2],r->reaction_after_zone))))return 1u;
    /* An arrival/release pair costs two whole ink transactions. Keep that
     * optional acting only inside this software budget; ordinary slow paper
     * goes directly to its original peak. This is not a panel speed claim. */
    return COMP_RUNTIME_PET_MOTION && r->last_display_activated &&
        transaction_ms<=PET_OPTIONAL_REPLY_POSE_BUDGET_MS &&
        !pet_motion_intent(r) && !r->pet_play.phase?3u:1u;
}

#define PET_TEMPORARY_QUIET_MS (30u * 60000u)
static uint8_t effective_interaction_level(const comp_runtime_t *r)
{
    return r->temporary_quiet_active?COMP_SCREEN_MENU_INTERACTION_QUIET:r->menu.browser.interaction_level;
}
static uint8_t temporary_quiet_minutes(const comp_runtime_t *r,uint32_t now)
{
    const uint32_t elapsed=now-r->temporary_quiet_started_ms;
    return !r->temporary_quiet_active || elapsed>=PET_TEMPORARY_QUIET_MS?0u:
        (uint8_t)((PET_TEMPORARY_QUIET_MS-elapsed+59999u)/60000u);
}
static bool deferred_motion(const comp_runtime_t *r)
{ return r->deferred_pet_kind==COMP_RUNTIME_PET_INPUT_MOTION; }
static uint8_t motion_reply_events(const comp_runtime_t *r,uint8_t events,uint8_t tilt)
{
    if(effective_interaction_level(r)!=COMP_SCREEN_MENU_INTERACTION_QUIET)return events;
    /* Quiet keeps an intentional lift or a qualified spatial look readable,
     * silently. Incidental settling, shaking and inversion need no new show.
     * Carry/touch/foreground and completion gates still own admission. */
    if(events&COMP_MOTION_SHAKE)return 0u;
    if(events&COMP_MOTION_PICKUP)return COMP_MOTION_PICKUP;
    /* The classifier may report settling and a stable tilt together. Keep
     * the qualified look, without turning it into a separate settle show. */
    return (events&COMP_MOTION_TILT_CHANGED) && tilt<=COMP_MOTION_TILT_DOWN?
        COMP_MOTION_TILT_CHANGED:0u;
}
static unsigned motion_priority(uint8_t events)
{
    return (events&COMP_MOTION_SHAKE)?3u:(events&COMP_MOTION_PICKUP)?2u:
        (events&COMP_MOTION_TILT_CHANGED)?1u:0u;
}
#if COMP_RUNTIME_VISUAL
static unsigned active_motion_priority(const comp_runtime_t *r)
{
#if COMP_PET_PROCEDURAL
    return r->pet.interaction==COMP_PET_SHAKE?3u:
        r->pet.interaction==COMP_PET_PICKUP?2u:
        (r->pet.interaction==COMP_PET_TILT || r->pet.interaction==COMP_PET_INVERTED)?1u:0u;
#else
    (void)r;return 0u;
#endif
}
#endif
static void defer_motion(comp_runtime_t *r,uint8_t events,uint8_t tilt,uint32_t now)
{
    /* One latest semantic intention shares the existing deferred slot. Touch
     * intentions always win; settling is already part of a motion response.
     * A lower-priority posture cannot overwrite a fresh deliberate shake. */
    if(!motion_priority(events) ||
       (r->deferred_pet_kind!=COMP_RUNTIME_PET_INPUT_NONE && !deferred_motion(r)))return;
    if(deferred_motion(r) && now-r->deferred_pet_ms<=PET_DEFERRED_MOTION_MAX_MS &&
       motion_priority(events)<motion_priority((uint8_t)r->deferred_pet_x))return;
    r->deferred_pet_kind=COMP_RUNTIME_PET_INPUT_MOTION;
    r->deferred_pet_x=events;r->deferred_pet_y=tilt;r->deferred_pet_ms=now;
}

static void dirty(comp_runtime_t *r) { if (++r->revision == 0u) ++r->revision; }
/* Current menu namespace fits five bits; all accepted pages fit three.
 * Capture request and feedback origins separately: a blocked second action
 * can report BUSY here without moving the first operation's result. */
_Static_assert(COMP_SCREEN_MENU_VIEW_BROWSER_QUICK<32u,"menu context view overflow");
static uint8_t menu_page_context(const comp_screen_menu_t *menu)
{
    if(comp_screen_menu_customer_active()) {
        if((unsigned)menu->view>=COMP_CUSTOMER_CHOICE_BASE &&
           comp_screen_menu_customer_count(menu->view))
            return (uint8_t)(128u+(unsigned)menu->view-COMP_CUSTOMER_CHOICE_BASE);
        if((unsigned)menu->view>=16u && (unsigned)menu->view<32u && menu->home_page<32u) {
            /* Compact disjoint ranges for actual list positions; dividing
             * by four would alias overlapping rows and move late feedback. */
            unsigned context=menu->home_page;
            for(unsigned view=16u;view<(unsigned)menu->view;++view)
                context+=comp_screen_menu_browser_page_count((comp_screen_menu_view_t)view);
            return (uint8_t)context;
        }
        return 255u;
    }
    return (unsigned)menu->view<32u && menu->home_page<8u?
        (uint8_t)((unsigned)menu->view|((unsigned)menu->home_page<<5u)):255u;
}
static uint8_t menu_context(const comp_runtime_t *r){return menu_page_context(&r->menu);}
static comp_runtime_menu_feedback_t pending_menu_feedback(const comp_runtime_t *r)
{
    return r->menu_pending_action==COMP_SCREEN_MENU_ACTION_BROWSER_PAIR ||
        r->menu_pending_action==COMP_SCREEN_MENU_ACTION_PHONE_RECONNECT?
        COMP_RUNTIME_MENU_FEEDBACK_PAIRING:
        r->menu_pending_action==COMP_SCREEN_MENU_ACTION_BROWSER_CLEAR_RECORDINGS?
        (r->menu_pending_retrying?COMP_RUNTIME_MENU_FEEDBACK_RETRYING:COMP_RUNTIME_MENU_FEEDBACK_CLEARING):
        COMP_RUNTIME_MENU_FEEDBACK_WORKING;
}
static void menu_feedback_at(comp_runtime_t *r,comp_runtime_menu_feedback_t value,uint8_t context)
{
    r->menu_feedback=value;r->menu_feedback_context=context;r->menu_feedback_seen=false;
    r->menu_effect_result=value==COMP_RUNTIME_MENU_FEEDBACK_BUSY?COMP_RUNTIME_BUSY:COMP_RUNTIME_OK;
}
static comp_runtime_result_t current_ui_result(const comp_runtime_t *r)
{
    /* Preserve the technical result in runtime/DIAG. A detached settings
     * error must not impersonate a recording failure on a later voice page. */
    if(!r->last_result_from_menu && r->last_result!=COMP_RUNTIME_OK)return r->last_result;
    if(r->surface==COMP_SCREEN_SURFACE_MENU && menu_context(r)==r->menu_feedback_context &&
       r->menu_feedback!=COMP_RUNTIME_MENU_FEEDBACK_NONE)
        return (comp_runtime_result_t)r->menu_effect_result;
    return r->last_result_from_menu?COMP_RUNTIME_OK:r->last_result;
}
static void dismiss_discovery(comp_runtime_t *r)
{
#if COMP_RUNTIME_PET_MOTION
    if(!r->pet_discovery_allowed)return;
    r->pet_discovery_allowed=false;
    /* A failed/unseen hint may be suppressed for this boot, but is never
     * persisted as seen. Input remains its original gesture, not a new tap. */
    if(r->pet_discovery_visible)r->pet_discovery_pending_save=true;
    dirty(r);
#else
    (void)r;
#endif
}
void comp_runtime_set_discovery_seen(comp_runtime_t *r,bool seen)
{
    if(!r)return;
#if COMP_RUNTIME_PET_MOTION
    if(seen) {
        if(r->pet_discovery_allowed)dirty(r);
        r->pet_discovery_allowed=false;r->pet_discovery_pending_save=false;
    } else if(!r->visible_frames && !r->pet_discovery_visible)
        r->pet_discovery_allowed=true;
#else
    (void)seen;
#endif
}
static void choose_reply_variation(comp_runtime_t *r,comp_pet_interaction_t input,uint16_t x,uint32_t now)
{
#if COMP_RUNTIME_PET_MOTION
    dismiss_discovery(r);
    r->pet_startup_pending=false;
    uint32_t value=0;
    bool available=r->config.random_u32 && r->config.random_u32(r->config.context,&value);
    if(available) {
        /* Only accepted input consumes a choice; retries retain this artwork.
         * The next accessory differs without a fixed left/right alternation. */
        r->reaction_variant=(uint8_t)(value>>8);
        r->pet_variant=(uint8_t)((r->pet_variant+1u+value%2u)%3u);
    }
#if COMP_PET_PROCEDURAL
    comp_pet_behavior_interact(&r->pet,input,available,value,x,now);
    comp_pet_behavior_apply_personality(&r->pet);
    comp_pet_behavior_apply_activity(&r->pet,effective_interaction_level(r),x);
#else
    (void)input;(void)x;(void)now;
#endif
#else
    (void)r;(void)input;(void)x;(void)now;
#endif
}
static uint32_t reaction_interval(const comp_runtime_t *r)
{
    comp_power_settings_values_t values;
    comp_power_settings_values_default(&values);
    values.interaction_level=effective_interaction_level(r);
    return comp_power_settings_interaction_interval_ms(&values);
}
static bool reaction_ready(const comp_runtime_t *r,uint32_t now)
{
    return r->reaction_pending && (int32_t)(now-r->reaction_due_ms)>=0 &&
        (!r->reaction_route_count || r->reaction_step!=0u ||
         (int32_t)(now-r->reaction_input_after_ms)>=0);
}
static bool record_busy(const comp_runtime_t *r)
{
    return r->start_pending || r->command_pending || r->capture_active ||
        r->recording == DENZIC_AUDIO_RECORDING_STATE_PENDING_START ||
        r->recording == DENZIC_AUDIO_RECORDING_STATE_RECORDING ||
        r->recording == DENZIC_AUDIO_RECORDING_STATE_STOPPING;
}
static bool visible_menu_matches(const comp_runtime_t *r)
{
    return r->surface == COMP_SCREEN_SURFACE_MENU &&
        r->visible_surface == COMP_SCREEN_SURFACE_MENU &&
        r->visible_menu_valid &&
        r->visible_menu_revision == r->menu.revision &&
        r->visible_menu_view == r->menu.view &&
        r->visible_menu_home_page == r->menu.home_page;
}
static bool menu_controls_ready(const comp_runtime_t *r)
{
    if(!visible_menu_matches(r))return false;
    if(!r->frame_outstanding)return true;
    /* A clock/status repaint of the same controls is not a new menu. New
     * view/page/setting revisions still wait for their own visible commit;
     * an unknown failed image remains disabled by visible_menu_valid. */
    const comp_runtime_frame_t *f=&r->in_flight;
    return f->surface==COMP_SCREEN_SURFACE_MENU &&
        f->menu.revision==r->visible_menu_revision &&
        f->menu.view==r->visible_menu_view && f->menu.home_page==r->visible_menu_home_page;
}
static bool input_contact_ready(const comp_runtime_t *r)
{
    if (!r->input_contact_eligible ||
        r->surface != r->input_contact_surface ||
        r->surface != r->visible_surface) return false;
    if (r->input_contact_surface != COMP_SCREEN_SURFACE_MENU) return true;
    return r->input_contact_visible_frame == r->visible_menu_revision &&
        menu_controls_ready(r);
}
static void pet_reply(comp_runtime_t *r,comp_browser_family_t family,uint32_t now,uint32_t visible_ms)
{
    const unsigned replies[]={COMP_AUDIO_FEEDBACK_TOUCH_CONFIRM,COMP_AUDIO_FEEDBACK_PET_GREETING,
        COMP_AUDIO_FEEDBACK_PET_CONTENT,COMP_AUDIO_FEEDBACK_PET_PLAYFUL,COMP_AUDIO_FEEDBACK_PET_SHY};
    /* One low-priority short sound for the first successfully visible reply.
     * Failed panel attempts and incidental IMU reports never trigger sound. */
    if(record_busy(r) || r->audio.quiet || r->audio.active || r->audio.queue_count ||
       (pet_carried(r) && pet_motion_intent(r)))return;
#if COMP_PET_PROCEDURAL
    /* Discrete posture looks are silent; moving the board is not a greeting. */
    if(r->pet.interaction==COMP_PET_TILT || r->pet.interaction==COMP_PET_INVERTED)return;
#endif
    for(unsigned i=0;i<sizeof(replies)/sizeof(replies[0]);++i)
        if(r->audio.last_accepted_valid[replies[i]] && now-r->audio.last_accepted_ms[replies[i]]<1500u)return;
    comp_audio_feedback_event_t event;
    if(family==COMP_BROWSER_FAMILY_CURIOUS)event=COMP_AUDIO_FEEDBACK_PET_GREETING;
    else if(family==COMP_BROWSER_FAMILY_WARM)event=COMP_AUDIO_FEEDBACK_PET_CONTENT;
    else if(family==COMP_BROWSER_FAMILY_PLAYFUL || family==COMP_BROWSER_FAMILY_DELIGHTED)event=COMP_AUDIO_FEEDBACK_PET_PLAYFUL;
    else if(family==COMP_BROWSER_FAMILY_BASHFUL)event=COMP_AUDIO_FEEDBACK_PET_SHY;
    else return; /* Other authored feelings stay silent, not a menu-confirm beep. */
    (void)comp_audio_feedback_submit_visible_pet(&r->audio,event,visible_ms,now);
}
static void audio_settings(comp_runtime_t *r)
{
    const bool before=r->audio.quiet;
    comp_audio_feedback_set_quiet(&r->audio, r->quiet || r->quiet_hours_active ||
        effective_interaction_level(r) == COMP_SCREEN_MENU_INTERACTION_QUIET);
    /* Quiet policy changes immediately in the audio owner. A sleeping paper
     * face stays parked; wake composes its current quiet/status indicators. */
    if(before!=r->audio.quiet && r->surface!=COMP_SCREEN_SURFACE_LOW_POWER)dirty(r);
}
static void enter_pet_daily(comp_runtime_t *r,uint32_t now,comp_browser_family_t family)
{
    comp_epaper_motion_coordinator_enter_daily(&r->life,now,
        (comp_epaper_motion_family_t)family);
#if COMP_RUNTIME_PET_MOTION && COMP_PET_PROCEDURAL
    /* The already accepted hardware entropy belongs to this intent. Asset
     * episode IDs are bounded by the renderer; no timestamp is random input. */
    (void)comp_epaper_motion_coordinator_seed_scene(&r->life,r->pet.seed);
#endif
}
static void enter_home(comp_runtime_t *r, uint32_t now)
{
    r->sleep_phase=COMP_RUNTIME_SLEEP_NONE;
    r->pet_play.phase=COMP_PET_PLAY_OFF;
    r->quick_contact=QUICK_CONTACT_NONE;
    r->menu_deferred_swipe=0u;
    comp_audio_feedback_cancel_pet(&r->audio);
    r->surface = COMP_SCREEN_SURFACE_HOME;
    r->reaction_pending = false;
    r->reaction_route_count=0u;r->reaction_step=0u;
    r->gaze_x=r->gaze_y=100u;
    r->deferred_pet_kind = COMP_RUNTIME_PET_INPUT_NONE;
    ++r->reaction_generation;
    enter_pet_daily(r,now,r->affect.selected);
    comp_epaper_natural_blink_enter_daily(&r->blink, now);
    dirty(r);
}
/* A new foreground owner retires the old finger's UI intent, not the touch
 * device. Retain acquisition health and quarantine a still-held contact until
 * its real release; it cannot finish an old slider/hold on the new surface. */
static void cancel_control_contact(comp_runtime_t *r)
{
    r->pet_play.phase=COMP_PET_PLAY_OFF;
    const bool held=r->gesture.active || r->gesture.consumed_until_release;
    const comp_touch_gesture_config_t config=r->gesture.config;
    comp_touch_gesture_init(&r->gesture,&config);
    r->gesture.consumed_until_release=held;
    r->touch_contact=held;r->drag_contact=held;r->input_contact_eligible=false;
    comp_touch_tap_arbiter_cancel(&r->taps);
    comp_browser_menu_hold_end(&r->hold);r->hold_enter_requested=false;
    r->menu_deferred_swipe=0u;r->quick_contact=QUICK_CONTACT_NONE;
    r->pet_stroke_phase=PET_STROKE_DISABLED;
    r->deferred_pet_kind=COMP_RUNTIME_PET_INPUT_NONE;
    r->gaze_x=r->gaze_y=100u;
    r->menu.flags &= (uint8_t)~(COMP_SCREEN_MENU_FLAG_PRESS_ACTIVE|COMP_SCREEN_MENU_FLAG_PRESS_ITEM_MASK);
}
static void exit_pet_play(comp_runtime_t *r,uint32_t now)
{
    /* Leaving a short activity returns to the pet, not another feature list.
     * Restore its real pre-game feeling so the question face cannot look
     * like an unanswered round after exit. Quarantine the exit contact and
     * retire queued answers; a picture already in flight keeps its owner. */
    const comp_browser_family_t family=r->pet_play.home_family<COMP_BROWSER_FAMILY_COUNT?
        (comp_browser_family_t)r->pet_play.home_family:COMP_BROWSER_FAMILY_CALM;
    cancel_control_contact(r);
    r->affect.selected=family;
#if COMP_PET_PROCEDURAL
    comp_pet_behavior_idle(&r->pet,r->pet.seed);
#endif
    enter_home(r,now);
}
static void recording_surface(comp_runtime_t *r,uint32_t now)
{
    r->sleep_phase=COMP_RUNTIME_SLEEP_NONE;
    const bool menu=r->surface==COMP_SCREEN_SURFACE_MENU;
    /* Retire only pet emotion cues. The accepted recording-start cue and
     * its existing acoustic gate keep ownership until the speaker stops. */
    comp_audio_feedback_cancel_pet(&r->audio);
    cancel_control_contact(r);
    if(menu)enter_home(r,now);
}
static void enter_menu(comp_runtime_t *r,comp_screen_menu_view_t view)
{
    r->sleep_phase=COMP_RUNTIME_SLEEP_NONE;
    comp_audio_feedback_cancel_pet(&r->audio);
    cancel_control_contact(r);
    r->surface=COMP_SCREEN_SURFACE_MENU;
    r->reaction_pending=false;r->reaction_route_count=0u;r->reaction_step=0u;
    ++r->reaction_generation;
    /* Fresh entry always has a clean navigation session. Settings and the
     * original four-cell recognition contract remain untouched. */
    r->menu.navigation_depth=0u;r->menu.view=COMP_SCREEN_MENU_VIEW_HOME;
    (void)comp_screen_menu_navigate_to(&r->menu,view);
    r->menu.home_scroll_offset_px=0u;
    comp_epaper_motion_coordinator_cancel(&r->life,COMP_EPAPER_MOTION_CANCEL_MENU);
    comp_epaper_natural_blink_cancel(&r->blink);dirty(r);
}
static bool sleep_now(comp_runtime_t *r,uint32_t now)
{
    if (record_busy(r) || r->menu_pending || (r->status_packed&COMP_SCREEN_STATUS_UPDATING)) return false;
    if (r->surface==COMP_SCREEN_SURFACE_LOW_POWER) return true;
    if (r->sleep_phase) return true;
    r->record_saved_state=0u;
    /* A tap waiting for double-tap arbitration belongs to the old awake
     * session; it cannot rewrite the sleep phrase's shared reaction slot. */
    cancel_control_contact(r);
    r->pet_play.phase=COMP_PET_PLAY_OFF;
    r->menu_deferred_swipe=0u;
    r->quick_contact=QUICK_CONTACT_NONE;
    comp_audio_feedback_cancel_pet(&r->audio);
    dismiss_discovery(r);
    /* Stay awake through the two visible lead-in poses. Existing power
     * blockers permit STOP only after the final LOW_POWER page commits. */
    r->surface = COMP_SCREEN_SURFACE_HOME;
    r->sleep_phase=COMP_RUNTIME_SLEEP_DOZE;
    r->reaction_due_ms=now;
    r->pet_startup_pending=false;
    r->reaction_pending = false;
    r->reaction_route_count=0u;
    r->gaze_x=r->gaze_y=100u;
    r->deferred_pet_kind = COMP_RUNTIME_PET_INPUT_NONE;
    ++r->reaction_generation;
    comp_epaper_motion_coordinator_cancel(&r->life, COMP_EPAPER_MOTION_CANCEL_LOW_POWER);
    comp_epaper_natural_blink_cancel(&r->blink);
    comp_browser_menu_hold_end(&r->hold);
    r->hold_enter_requested = false;
#if COMP_PET_PROCEDURAL
    /* Pick the parked original sleep ornament once on entry. Minute/status
     * changes and failed display attempts must not draw another position. */
    uint32_t entropy;
    if(r->config.random_u32 && r->config.random_u32(r->config.context,&entropy))
        r->pet.seed=entropy;
#endif
    dirty(r);
    return true;
}
void comp_runtime_init(comp_runtime_t *r, const comp_runtime_config_t *config, uint32_t now)
{
    comp_audio_feedback_config_t audio = {0};
#if COMP_PET_PROCEDURAL
    /* Port the reviewed P05 wall-clock cadence to the real runtime. Panel
     * completion still owns close/reopen; this is no panel FPS claim. */
    static const uint8_t pet_blink_seconds[]={24u,29u,35u,41u};
    const comp_epaper_natural_blink_config_t blink={1000u,25u,
        (uint8_t)sizeof(pet_blink_seconds),pet_blink_seconds};
#else
    const comp_epaper_natural_blink_config_t blink = {
        COMPANION_BROWSER_BLINK_CADENCE_MS,
        COMPANION_BROWSER_BLINK_FIRST_INTERVAL_COMMITS,
        COMPANION_BROWSER_BLINK_INTERVAL_COUNT, companion_browser_blink_interval_commits};
#endif
    if (!r) return;
    memset(r, 0, sizeof(*r));
    r->menu_pending_context=r->menu_feedback_context=255u;
    if (config) r->config = *config;
    audio.speaker = r->config.speaker;
    comp_audio_feedback_init(&r->audio, &audio);
    if(audio.speaker) (void)comp_speaker_set_pet_voice(audio.speaker,true);
    (void)comp_audio_feedback_set_volume(&r->audio, 25u);
    comp_touch_gesture_init(&r->gesture, NULL);
    r->gesture.config.tap_max_move_px = 24u;
    /* A deliberate follow movement must retire the menu hold. Use the same
     * generous jitter allowance as a tap, rather than nearly a quarter of
     * the display; the three-second duration and visible four beats stay. */
    r->gesture.config.long_press_max_move_px = r->gesture.config.tap_max_move_px;
    r->gesture.config.tap_max_duration_ms = 1100u;
    r->gesture.config.hold_feedback_min_duration_ms = COMPANION_BROWSER_INTERACTION_MENU_HOLD_RECOGNITION_MS;
    r->gesture.config.long_press_min_duration_ms = COMPANION_BROWSER_INTERACTION_MENU_HOLD_MS;
    r->gesture.config.double_tap_max_gap_ms = COMPANION_BROWSER_INTERACTION_DOUBLE_TAP_GAP_MS;
    r->gesture.config.double_tap_max_move_px = COMPANION_BROWSER_INTERACTION_DOUBLE_TAP_MAX_DISTANCE_200;
    comp_touch_tap_arbiter_init(&r->taps, r->gesture.config.double_tap_max_gap_ms);
    comp_browser_interaction_reset(&r->affect);
    comp_screen_menu_init(&r->menu);
    comp_epaper_motion_coordinator_init(&r->life);
#if COMP_RUNTIME_PET_MOTION
    (void)comp_epaper_motion_coordinator_enable_scenes(&r->life,true);
#endif
    comp_epaper_natural_blink_init(&r->blink, &blink);
    r->recording = DENZIC_AUDIO_RECORDING_STATE_IDLE;
    r->gaze_x = r->gaze_y = 100u;
    r->last_activity_ms = now;
    /* retry_display_ms is compared as a wrapping deadline. Zero is not a
     * valid "ready now" sentinel when boot itself occurs above INT32_MAX. */
    r->retry_display_ms = now;
    r->reaction_input_after_ms=now; r->family_retry_ms=now; r->family_due_ms=now+28000u;
    r->booted = true;
#if COMP_RUNTIME_PET_MOTION
    /* Product initialization precedes BLE's RNG pool. First frame acquisition
     * runs after platform initialization; never call that pool prematurely. */
    r->pet_startup_pending=true;
    r->pet_discovery_allowed=true;
#if COMP_PET_PROCEDURAL
    r->pet.life_key=UINT32_MAX;
#endif
#endif
    enter_home(r, now);
}
void comp_runtime_wake_from(comp_runtime_t *r,uint32_t now,comp_runtime_wake_source_t source)
{
    if (!r) return;
    r->last_activity_ms = now;
    if (r->surface == COMP_SCREEN_SURFACE_LOW_POWER) {
        ++r->wake_count;
        r->last_wake_ms=now;
        r->last_wake_source=source;
        /* Wake the pet's mood too; keep the original calm whole face. This
         * changes no sleep deadline, hardware wake source or power policy. */
        if(r->affect.selected==COMP_BROWSER_FAMILY_SLEEPY)
            r->affect.selected=COMP_BROWSER_FAMILY_CALM;
        enter_home(r, now);
        /* Recording starts immediately; ordinary wake earns a short original
         * sleepy-to-calm glance before daily life. No sound or new artwork. */
        if(source!=COMP_RUNTIME_WAKE_RECORDING && !record_busy(r)) {
            r->affect.selected=COMP_BROWSER_FAMILY_CALM;
            r->sleep_phase=COMP_RUNTIME_SLEEP_WAKE;
            r->reaction_due_ms=now;
            r->pet_startup_pending=false;
            comp_epaper_motion_coordinator_cancel(&r->life,COMP_EPAPER_MOTION_CANCEL_LOW_POWER);
            comp_epaper_natural_blink_cancel(&r->blink);
        }
    } else if(r->sleep_phase &&
              (r->sleep_phase<COMP_RUNTIME_SLEEP_WAKE || source==COMP_RUNTIME_WAKE_RECORDING ||
               (source==COMP_RUNTIME_WAKE_TOUCH && r->visible_surface==COMP_SCREEN_SURFACE_HOME))) {
        /* Edge and debounced-key notifications describe the same wake. A
         * repeated KEY/PICKUP/GENERIC wake while awakening is idempotent;
         * only an actual foreground command/contact retires the phrase. */
        /* Real input interrupts dozing/awakening; the immutable old frame may
         * finish, but its generation cannot put the pet back to sleep. */
        enter_home(r,now);
    }
    comp_epaper_motion_coordinator_keep_awake(&r->life, now);
}
void comp_runtime_wake(comp_runtime_t *r,uint32_t now)
{
    comp_runtime_wake_from(r,now,COMP_RUNTIME_WAKE_GENERIC);
}
void comp_runtime_set_quiet(comp_runtime_t *r, bool quiet)
{
    if (r) { r->quiet = quiet; audio_settings(r); }
}
void comp_runtime_set_personality(comp_runtime_t *r,unsigned type,uint32_t seed)
{
#if COMP_RUNTIME_PET_MOTION && COMP_PET_PROCEDURAL
    if(r)comp_pet_behavior_set_personality(&r->pet,type,seed);
#else
    (void)r;(void)type;(void)seed;
#endif
}
void comp_runtime_local_hour(comp_runtime_t *r, bool valid, uint8_t hour)
{
    uint8_t mode;
    if (!r) return;
    mode = r->menu.browser.quiet_hours;
    r->quiet_hours_active = valid && hour < 24u &&
        ((mode == COMP_SCREEN_MENU_QUIET_HOURS_23_07 && (hour >= 23u || hour < 7u)) ||
         (mode == COMP_SCREEN_MENU_QUIET_HOURS_22_08 && (hour >= 22u || hour < 8u)));
    audio_settings(r);
}
void comp_runtime_set_connected(comp_runtime_t *r, bool connected, uint32_t now)
{
    if (!r || r->connected == connected) return;
    r->connected = connected;
    r->menu.browser.link_connected = connected;
    r->menu.flags = comp_screen_menu_with_ble_flag(r->menu.flags, connected);
    /* Automatic radio reconnects are common: keep them visual so their sound
     * cannot be mistaken for the start/end of a meeting. A sleeping face
     * retains its ink; background reconnects do not renew its clock image. */
    (void)now;
    if(r->surface!=COMP_SCREEN_SURFACE_LOW_POWER)dirty(r);
}
void comp_runtime_status(comp_runtime_t *r, uint32_t packed)
{
    if (!r) return;
    packed &= 0xFFFAFFFFu;
    /* A nominal ADC percentage can alternate across a rounding boundary on
     * every five-second sample. Each changed digit otherwise activates the
     * panel even while the pet is asleep; a RAM window is not a scan limit.
     * Hold neighbouring estimates against the last displayed percentage even
     * when the clock changes. The two-point deadband also holds a one-point
     * rebound after a decrease; it is not a claim that cell voltage is
     * monotonic. Qualified charging can rise normally. Power-state changes,
     * real/unknown readings, zero and entry into the low-battery range bypass
     * the deadband. ADC, BAS and the power/OTA guards stay raw. */
    const uint32_t estimated_valid = (1u << 17) | COMP_SCREEN_STATUS_ESTIMATED_BATTERY;
    const unsigned previous = r->status_packed >> 24;
    const unsigned next = packed >> 24;
    const unsigned difference = next > previous ? next - previous : previous - next;
    const uint32_t immediate = COMP_SCREEN_STATUS_EXTERNAL_POWER |
        COMP_SCREEN_STATUS_CHARGING | COMP_SCREEN_STATUS_CHARGER_FAULT;
    const bool low_entry = next < previous && (next == 0u || (previous > 15u && next <= 15u));
    if ((r->status_packed & estimated_valid) == estimated_valid &&
        (packed & estimated_valid) == estimated_valid && previous <= 100u && next <= 100u &&
        difference == 1u && !low_entry && !(packed & COMP_SCREEN_STATUS_CHARGING) &&
        ((r->status_packed ^ packed) & immediate) == 0u)
        packed = (packed & 0x00FFFFFFu) | (previous << 24);
    r->menu.browser.battery_percent=(packed & (1u<<17)) && (packed>>24)<=100u ? (uint8_t)(packed>>24) : 255u;
    if (r->status_packed != packed) {
        const uint32_t changed=r->status_packed^packed;
        const bool low_alert=(packed&(1u<<17)) && next<=15u &&
            (!(r->status_packed&(1u<<17)) || previous>15u || (next==0u && previous!=0u));
        r->status_packed=packed;
        /* A sleeping paper image needs no minute tick or battery digit
         * refresh. Keep the live values for wake and backend guards; only
         * actual external-power/charger/update or low-battery alerts request
         * ink while asleep. Wake already dirties the page with current time.
         * This is a UI policy, not evidence that MCU STOP1 is enabled. */
        if(r->surface!=COMP_SCREEN_SURFACE_LOW_POWER || low_alert ||
           (changed&(immediate|COMP_SCREEN_STATUS_UPDATING))) dirty(r);
    }
    if(r->menu.browser.clock_24_hour)
        comp_runtime_local_hour(r, (packed & 0x8000u) != 0u, (uint8_t)((packed >> 8) & 31u));
}
void comp_runtime_update_progress(comp_runtime_t *r,uint16_t display,uint32_t now)
{
    if(!r || record_busy(r) ||
       ((display&255u)==0u && !(r->status_packed&COMP_SCREEN_STATUS_UPDATING)))return;
    const bool entering=display!=0u && !(r->status_packed&COMP_SCREEN_STATUS_UPDATING);
    if(r->update_display==display && !entering)return;
    r->update_display=display;
    if(entering) {
        cancel_control_contact(r);
        enter_home(r,now);
    }
    dirty(r);
}
void comp_runtime_catalog(comp_runtime_t *r,uint16_t count,uint16_t used_kib)
{
    if(!r || (r->menu.browser.recording_count==count && r->menu.browser.recording_storage_kb==used_kib))return;
    r->menu.browser.recording_count=count;r->menu.browser.recording_storage_kb=used_kib;
    /* Background synchronization may reclaim a saved original while asleep.
     * Keep the live catalog for wake/menu without repainting the sleeping pet. */
    if(r->surface!=COMP_SCREEN_SURFACE_LOW_POWER)dirty(r);
}
void comp_runtime_battery_voltage(comp_runtime_t *r,uint16_t mv)
{
    if(!r)return;
    if(mv<1000u || mv>5000u)mv=0u;
    /* Match the displayed 10 mV precision and avoid ADC noise creating frames. */
    if(mv)mv=(uint16_t)(((mv+5u)/10u)*10u);
    if(r->battery_mv==mv)return;
    bool rail_changed=(r->battery_mv+50u)/100u!=(mv+50u)/100u;
    r->battery_mv=mv;
    if(r->surface!=COMP_SCREEN_SURFACE_LOW_POWER &&
       ((r->menu.browser.battery_percent>100u && rail_changed) ||
        (r->surface==COMP_SCREEN_SURFACE_MENU &&
         r->menu.view==COMP_SCREEN_MENU_VIEW_BROWSER_POWER && r->menu.home_page==0u)))dirty(r);
}
static comp_runtime_result_t reject_result(comp_runtime_t *r, comp_runtime_result_t result, uint32_t now,
                                          bool visible_change)
{
    r->last_result = result;
    r->last_result_from_menu=false;
    ++r->rejected_commands;
    if (!r->capture_active) (void)comp_audio_feedback_submit(&r->audio, COMP_AUDIO_FEEDBACK_ERROR, now);
    if(visible_change)dirty(r);
    return result;
}
static comp_runtime_result_t reject(comp_runtime_t *r,comp_runtime_result_t result,uint32_t now)
{ return reject_result(r,result,now,true); }
static comp_runtime_result_t recording_request(comp_runtime_t *r,bool start,
                                               uint32_t seconds,uint32_t now,uint8_t stop_reason)
{
    comp_audio_feedback_outcome_t unused;
    if (!r) return COMP_RUNTIME_UNAVAILABLE;
    if(!start && r->record_saved_state>=RECORD_NOTICE_STOP_PENDING)
        r->record_saved_state=RECORD_NOTICE_NONE;
    if(!start && record_busy(r) && !r->stop_pending)r->record_stop_reason=stop_reason;
    /* A new recording command owns its own outcome. A previous terminal
     * setting/clear message must not mask a real recording backend failure. */
    if (!r->menu_pending && r->menu_feedback!=COMP_RUNTIME_MENU_FEEDBACK_NONE) {
        r->menu_feedback=COMP_RUNTIME_MENU_FEEDBACK_NONE;
        dirty(r);
    }
    if (!start && r->prepare_pending) {
        r->prepare_pending = false;
        r->command_pending = false;
        if (!r->config.recording_control(r->config.context, false, r->record_token))
            return reject(r, COMP_RUNTIME_BACKEND_FAILED, now);
        r->last_result = COMP_RUNTIME_OK; dirty(r); return COMP_RUNTIME_OK;
    }
    if (!start && r->start_pending) {
        (void)comp_audio_feedback_cancel_recording_start(&r->audio, now);
        (void)comp_audio_feedback_take_recording_start_gate(&r->audio, &unused);
        r->start_pending = false;
        r->command_pending = false;
        if (r->config.recording_prepare &&
            !r->config.recording_control(r->config.context, false, r->record_token))
            return reject(r, COMP_RUNTIME_BACKEND_FAILED, now);
        r->last_result = COMP_RUNTIME_OK;
        dirty(r);
        return COMP_RUNTIME_OK;
    }
    if (start && (record_busy(r) || (r->menu_pending &&
        r->menu_pending_action==COMP_SCREEN_MENU_ACTION_BROWSER_CLEAR_RECORDINGS)))
        return reject(r, COMP_RUNTIME_BUSY, now);
    if (!start && !record_busy(r)) return COMP_RUNTIME_OK;
    if (!r->config.recording_control || !r->config.recording_ready ||
        (start && !r->config.recording_prepare && !r->config.recording_ready(r->config.context)))
        return reject(r, COMP_RUNTIME_UNAVAILABLE, now);
    if (start && r->recording != DENZIC_AUDIO_RECORDING_STATE_IDLE &&
        r->recording != DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY &&
        r->recording != DENZIC_AUDIO_RECORDING_STATE_TRANSFERRED &&
        r->recording != DENZIC_AUDIO_RECORDING_STATE_CANCELED &&
        !(r->recording == DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY && r->config.recording_prepare))
        return reject(r, COMP_RUNTIME_BUSY, now);
    if (start) {
        dismiss_discovery(r);
        r->record_saved_state=0u;
        if (++r->record_token == 0u) ++r->record_token;
        r->record_limit_seconds=seconds;
        r->recording_capture_clock=false;r->recording_captured_ms=0u;
        r->record_stop_reason=COMP_RECORD_STOP_NONE;
        if (r->config.recording_prepare) {
            r->command_pending = true; r->prepare_pending = true; r->prepare_since_ms = now;
            if (!r->config.recording_prepare(r->config.context, r->record_token)) {
                r->command_pending = false; r->prepare_pending = false;
                return reject(r, COMP_RUNTIME_UNAVAILABLE, now);
            }
        } else {
        comp_audio_feedback_submit_result_t result = comp_audio_feedback_submit(
            &r->audio, COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST, now);
        if (result != COMP_AUDIO_FEEDBACK_SUBMIT_ACCEPTED &&
            result != COMP_AUDIO_FEEDBACK_SUBMIT_SUPPRESSED_QUIET)
            return reject(r, COMP_RUNTIME_BUSY, now);
        r->start_pending = true;
        }
        comp_browser_menu_hold_end(&r->hold);
        r->hold_enter_requested = false;
        comp_touch_tap_arbiter_cancel(&r->taps);
        r->reaction_pending = false;
        r->deferred_pet_kind = COMP_RUNTIME_PET_INPUT_NONE;
        ++r->reaction_generation;
        comp_runtime_wake_from(r,now,COMP_RUNTIME_WAKE_RECORDING);
        /* Only an accepted request owns the recording surface. A backend
         * refusal above leaves the current menu and its real outcome intact. */
        recording_surface(r,now);
    } else if (!r->stop_pending) {
        r->stop_pending = true;
        if (!r->config.recording_control(r->config.context, false, r->record_token)) {
            r->stop_pending = false;
            return reject(r, COMP_RUNTIME_BACKEND_FAILED, now);
        }
    } else {
        /* A stop already accepted by the asynchronous backend is idempotent.
         * Do not churn display revisions while an auto-stop condition remains
         * true and capture is draining. */
        r->last_result = COMP_RUNTIME_OK;
        return COMP_RUNTIME_OK;
    }
    r->last_result = COMP_RUNTIME_OK;
    dirty(r);
    return COMP_RUNTIME_OK;
}
comp_runtime_result_t comp_runtime_record(comp_runtime_t *r,bool start,uint32_t now)
{
#ifdef COMPANION_RECORDING_SEGMENTED_ONLY
    /* WBA segmented recordings stop on user request or actual capacity, not
     * an obsolete saved menu timer. Explicit nonzero host limits remain. */
    return recording_request(r,start,0u,now,COMP_RECORD_STOP_REQUESTED);
#else
    return recording_request(r,start,
        r ? (uint32_t)r->menu.browser.recording_limit_minutes*60u : 0u,now,COMP_RECORD_STOP_REQUESTED);
#endif
}
comp_runtime_result_t comp_runtime_record_stop(comp_runtime_t *r,comp_runtime_record_stop_reason_t reason,uint32_t now)
{
    if(reason<=COMP_RECORD_STOP_NONE || reason>COMP_RECORD_STOP_SILENCE)return COMP_RUNTIME_UNAVAILABLE;
    return recording_request(r,false,0u,now,(uint8_t)reason);
}
bool comp_runtime_recording_owned(const comp_runtime_t *r)
{return r && record_busy(r);}
bool comp_runtime_recording_hold(const comp_runtime_t *r)
{(void)r;return false;}
comp_runtime_result_t comp_runtime_recording_set_hold(comp_runtime_t *r,uint32_t token,bool locked,uint32_t now)
{
    if(!r || !token || token!=r->record_token || locked)return COMP_RUNTIME_UNAVAILABLE;
    if(r->recording!=DENZIC_AUDIO_RECORDING_STATE_RECORDING || r->start_pending ||
       r->prepare_pending || r->command_pending || r->stop_pending)return COMP_RUNTIME_BUSY;
    (void)now;
    return COMP_RUNTIME_OK; /* The retired HOLD feature has no mutable state. */
}
comp_runtime_result_t comp_runtime_record_start_limited(comp_runtime_t *r,
                                                      uint16_t seconds,uint32_t now)
{
    if (!seconds) return comp_runtime_record(r,true,now);
    return recording_request(r,true,seconds,now,COMP_RECORD_STOP_NONE);
}
bool comp_runtime_recording_update(comp_runtime_t *r, uint32_t token,
    denzic_audio_recording_state_v1_t state, bool active, uint32_t now)
{
    bool was_active, was_recording;
    if (!r || token == 0u || token != r->record_token || r->start_pending ||
        state > DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY) return false;
    /* Backends must never claim a closed session while capture is still live. */
    if (active && state != DENZIC_AUDIO_RECORDING_STATE_RECORDING &&
        state != DENZIC_AUDIO_RECORDING_STATE_STOPPING) return false;
    was_active = r->capture_active;
    was_recording = r->recording==DENZIC_AUDIO_RECORDING_STATE_RECORDING ||
                    r->recording==DENZIC_AUDIO_RECORDING_STATE_STOPPING;
    if (!comp_audio_feedback_set_recording_active(&r->audio, active)) return false;
    r->capture_active = active;
    r->recording = state;
    if(!active && state==DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY && was_recording) {
        /* This is the backend's sealed-save report for our current token,
         * not STOP acceptance, preparation cancellation or a reconnect query. */
        r->record_saved_state=1u;
    } else if((active && r->record_saved_state<=RECORD_NOTICE_SAVED_VISIBLE) ||
              state==DENZIC_AUDIO_RECORDING_STATE_STOPPING || state==DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY ||
              state==DENZIC_AUDIO_RECORDING_STATE_CANCELED)r->record_saved_state=0u;
    r->command_pending = state == DENZIC_AUDIO_RECORDING_STATE_PENDING_START;
    if(r->surface==COMP_SCREEN_SURFACE_MENU &&
       (active || state==DENZIC_AUDIO_RECORDING_STATE_PENDING_START))
        recording_surface(r,now);
    if (active && !was_active && !was_recording) {
        r->record_saved_state=RECORD_NOTICE_STOP_PENDING;
        r->recording_since_ms = now;
        r->recording_display_second = 0u;
        r->recording_wave_index=0u;
        r->recording_wave_due=true;
        r->recording_wave_started=false;
    }
    if (!active) r->recording_wave_due=false;
    if (!active && state != DENZIC_AUDIO_RECORDING_STATE_PENDING_START &&
        state != DENZIC_AUDIO_RECORDING_STATE_RECORDING &&
        state != DENZIC_AUDIO_RECORDING_STATE_STOPPING) {
        r->stop_pending = false;
    }
    if (state == DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY) {
        r->prepare_pending = false;
        r->last_result = COMP_RUNTIME_BACKEND_FAILED;
        r->last_result_from_menu=false;
        if (!active) (void)comp_audio_feedback_submit(&r->audio, COMP_AUDIO_FEEDBACK_ERROR, now);
    } else if (!active && (r->recording_capture_clock ?
               (was_recording && (state==DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY ||
                                  state==DENZIC_AUDIO_RECORDING_STATE_CANCELED)) :
               (was_active && state!=DENZIC_AUDIO_RECORDING_STATE_RECORDING))) {
        (void)comp_audio_feedback_submit(&r->audio,
            r->record_stop_reason==COMP_RECORD_STOP_STORAGE_FULL?COMP_AUDIO_FEEDBACK_ERROR:
            COMP_AUDIO_FEEDBACK_RECORDING_STOPPED, now);
    }
    if (active) r->menu.flags |= COMP_SCREEN_MENU_FLAG_RECORDING;
    else r->menu.flags &= (uint8_t)~COMP_SCREEN_MENU_FLAG_RECORDING;
    dirty(r);
    return true;
}
bool comp_runtime_recording_captured(comp_runtime_t *r,uint32_t token,uint32_t captured_ms)
{
    if(!r||!token||token!=r->record_token||
       (r->recording_capture_clock&&captured_ms<r->recording_captured_ms))return false;
    r->recording_capture_clock=true;r->recording_captured_ms=captured_ms;
    uint32_t seconds=captured_ms/1000u;
    if(seconds!=r->recording_display_second) {
        r->recording_display_second=seconds;
        if(r->capture_active)r->recording_wave_due=true;
        dirty(r);
    }
    return true;
}
static void begin_reply(comp_runtime_t *r, comp_browser_family_t before,
                        comp_browser_family_t reply, comp_browser_tap_zone_t zone,
                        comp_browser_family_t after, comp_browser_tap_zone_t after_zone,
                        uint32_t now)
{
    /* One or two expressive beats follow the glance, then return to the real
     * affect family. Stored poses never manufacture touch affect evidence. */
#if COMP_PET_PROCEDURAL
    if((r->pet.interaction>=COMP_PET_HEAD_PAT && r->pet.interaction<=COMP_PET_CHIN) ||
       r->pet.interaction==COMP_PET_GREETING) {
        /* Finger following already keeps the last visibly earned feeling.
         * Start this affectionate phrase from that same transient feeling,
         * rather than flashing the underlying daily mood between two looks.
         * This is visual continuity, not another touch score or mood update. */
        before=comp_pet_behavior_attention_family(&r->pet,before,now);
    }
#endif
    comp_audio_feedback_cancel_pet(&r->audio);
    r->reaction_route_count = after==COMP_BROWSER_FAMILY_NONE ? 1u : 2u;
    r->reaction_route[0] = before; r->reaction_route[1] = reply;
    r->reaction_route[2] = after;
    r->reaction_zone=(uint8_t)zone; r->reaction_after_zone=(uint8_t)after_zone;
    r->reaction_step = 0u;
    r->reaction_pose_phase=1u;r->reaction_pose_count=1u;
    r->reaction_due_ms=(int32_t)(now-r->reaction_input_after_ms)>=0?now:r->reaction_input_after_ms;
    ++r->reaction_generation;
    r->reaction_pending = true;
    dirty(r);
}
static bool play_tap(comp_runtime_t *r,uint16_t x,uint16_t y,uint32_t now);
static void react(comp_runtime_t *r, uint16_t x, uint16_t y, uint32_t now)
{
    comp_browser_tap_result_t result;
    if (record_busy(r)) return;
    if(play_tap(r,x,y,now))return;
    if (r->reaction_pending && r->reaction_route_count) {
        /* Finish the visible phrase, including its accessory and return pose.
         * Later taps replace only this pending intent, never the active seed,
         * route or generation. Navigation/capture discard it explicitly. */
        r->deferred_pet_x=x; r->deferred_pet_y=y;
        r->deferred_pet_kind=COMP_RUNTIME_PET_INPUT_TAP;
        r->deferred_pet_ms=now;
        return;
    }
    /* A fresh tap arriving during the settle gap supersedes an older deferred
     * tap too; it must not replay that older contact after this new response. */
    r->deferred_pet_kind=COMP_RUNTIME_PET_INPUT_NONE;
    if (comp_browser_interaction_tap(&r->affect, x, y, now, &result)) {
        comp_pet_interaction_t input=y<90u?COMP_PET_HEAD_PAT:
            x<70u || x>130u?COMP_PET_CHEEK:y<140u?COMP_PET_NOSE:COMP_PET_CHIN;
        choose_reply_variation(r,input,x,now);
        if (result.transition) enter_pet_daily(r,now,result.family_after);
        r->gaze_x = x; r->gaze_y = y;
#if COMP_PET_PROCEDURAL
        begin_reply(r,result.family_before,(comp_browser_family_t)r->pet.first_family,
            (comp_browser_tap_zone_t)r->pet.first_zone,(comp_browser_family_t)r->pet.second_family,
            (comp_browser_tap_zone_t)r->pet.second_zone,now);
#else
        if (y<90u)
            begin_reply(r,result.family_before,COMP_BROWSER_FAMILY_WARM,
                COMP_RUNTIME_PET_MOTION && r->pet_variant==1u ? COMP_BROWSER_TAP_ZONE_LEFT :
                (COMP_RUNTIME_PET_MOTION ? r->pet_variant==2u : (r->reaction_variant&1u)) ? COMP_BROWSER_TAP_ZONE_DOWN : COMP_BROWSER_TAP_ZONE_UP,
                COMP_BROWSER_FAMILY_NONE,COMP_BROWSER_TAP_ZONE_CENTER,now);
        else if (x<70u || x>130u)
            begin_reply(r,result.family_before,COMP_BROWSER_FAMILY_BASHFUL,COMP_BROWSER_TAP_ZONE_DOWN,
                COMP_BROWSER_FAMILY_BASHFUL,COMP_BROWSER_TAP_ZONE_LEFT,now);
        else if (y<140u)
            begin_reply(r,result.family_before,COMP_BROWSER_FAMILY_DELIGHTED,COMP_BROWSER_TAP_ZONE_UP,
                COMP_BROWSER_FAMILY_DELIGHTED,COMP_BROWSER_TAP_ZONE_CENTER,now);
        else
            begin_reply(r,result.family_before,COMP_BROWSER_FAMILY_DELIGHTED,COMP_BROWSER_TAP_ZONE_CENTER,
                COMP_BROWSER_FAMILY_PLAYFUL,
                (r->reaction_variant&1u) ? COMP_BROWSER_TAP_ZONE_LEFT : COMP_BROWSER_TAP_ZONE_RIGHT,now);
#endif
    }
}
static void gaze_reply(comp_runtime_t *r,uint16_t x,uint16_t y,
                       bool starting,uint32_t now)
{
    if(!starting && !r->pet_play.phase && r->reaction_step==0u &&
       r->gaze_x==x && r->gaze_y==y)return;
    /* The direction resource includes this whole authored emotion. Keep it
     * throughout a contact; continuing after a reply retains its last feeling.
     * Attention is transient, not invented tap evidence or a new daily mood. */
    comp_browser_family_t feeling=r->affect.selected;
#if COMP_PET_PROCEDURAL
    if(starting && !r->reaction_route_count)
        feeling=comp_pet_behavior_attention_family(&r->pet,feeling,now);
#endif
    if(r->reaction_route_count)
        feeling=r->reaction_route[r->reaction_route_count];
    else if(!starting)feeling=r->reaction_route[0];
    /* Following changes only the authored direction of the accepted feeling.
     * Calm must keep its own mouth/brows/ornament too; changing it to curious
     * here replaced the entire face merely because a finger started moving. */
    r->reaction_route[0]=feeling;
    r->gaze_x=x;r->gaze_y=y;
    r->reaction_route_count=0u;r->reaction_step=0u;
    r->reaction_due_ms=now;
    ++r->reaction_generation;r->reaction_pending=true;dirty(r);
}
static bool play_tap(comp_runtime_t *r,uint16_t x,uint16_t y,uint32_t now)
{
    if(!r->pet_play.phase)return false;
    if(r->pet_play.phase==COMP_PET_PLAY_ENDED) {
        /* The ended activity owns this return tap. A late answer must not
         * become an affectionate reply that looks like game success. */
        exit_pet_play(r,now);return true;
    }
    /* Early contacts cannot answer a cue still in flight. A contact must
     * have started after the qualified cue, with the normal input owner. */
    if(r->pet_play.phase!=COMP_PET_PLAY_WAIT || !r->pet_play.answer_contact ||
       !input_contact_ready(r))return true;
    if(!comp_pet_play_answer(&r->pet_play,x,y)) {
        /* A nonmatching tap must not silently become a successful-looking
         * ordinary pet reply. Retain the same cue/deadline and offer one
         * gentle hint; repeated taps do not schedule more refreshes. */
        if(!r->pet_play.retry_hint) {r->pet_play.retry_hint=true;dirty(r);}
        return true;
    }
    const comp_browser_family_t before=r->affect.selected;
    choose_reply_variation(r,COMP_PET_GREETING,x,now);
    const bool final=r->pet_play.round+1u==COMP_PET_PLAY_ROUNDS;
    const bool vertical=comp_pet_play_direction(&r->pet_play)>=COMP_PET_PLAY_UP;
    if(final)r->affect.selected=COMP_BROWSER_FAMILY_WARM;
    begin_reply(r,before,final?COMP_BROWSER_FAMILY_WARM:
        vertical?COMP_BROWSER_FAMILY_DELIGHTED:COMP_BROWSER_FAMILY_PLAYFUL,
        final?COMP_BROWSER_TAP_ZONE_DOWN:vertical?COMP_BROWSER_TAP_ZONE_CENTER:
        x<100u?COMP_BROWSER_TAP_ZONE_LEFT:COMP_BROWSER_TAP_ZONE_RIGHT,
        COMP_BROWSER_FAMILY_NONE,COMP_BROWSER_TAP_ZONE_CENTER,now);
    r->pet_play.phase=COMP_PET_PLAY_REPLY;
    r->pet_play.retry_hint=false;
    r->pet_play.generation=r->reaction_generation;
    return true;
}
#if COMP_RUNTIME_VISUAL
static void play_service(comp_runtime_t *r,uint32_t now)
{
    if(!r->pet_play.phase)return;
    if(r->surface!=COMP_SCREEN_SURFACE_HOME || record_busy(r) ||
       (r->status_packed&COMP_SCREEN_STATUS_UPDATING) || pet_carried(r)) {
        r->pet_play.phase=COMP_PET_PLAY_OFF;return;
    }
    /* A casual gaze question waits for the user. Reading the instruction is
     * not a failed answer. Normal idle sleep and explicit foreground owners
     * still retire this activity; it does not renew last_activity_ms. */
    if((r->pet_play.phase!=COMP_PET_PLAY_NEXT && r->pet_play.phase!=COMP_PET_PLAY_AIM) || r->frame_outstanding ||
       r->touch_contact || r->hold.active || r->hold_enter_requested ||
       r->reaction_pending || r->blink.open_pending || r->blink.open_in_flight ||
       (int32_t)(now-r->pet_play.due_ms)<0)return;
    r->deferred_pet_kind=COMP_RUNTIME_PET_INPUT_NONE;
    r->pet_play.retry_hint=false;
    r->affect.selected=COMP_BROWSER_FAMILY_CALM;
    r->reaction_route[0]=COMP_BROWSER_FAMILY_CALM;
#if COMP_PET_PROCEDURAL
    comp_pet_behavior_idle(&r->pet,r->pet.seed);
#endif
    /* Establish the same authored face at centre before showing its side.
     * The visible change is the cue; coordinates alone already map to the
     * outer pose. No new artwork or independent animation timer is used. */
    const bool orient=r->pet_play.phase==COMP_PET_PLAY_NEXT;
    gaze_reply(r,orient?100u:comp_pet_play_target_x(&r->pet_play),
        orient?100u:comp_pet_play_target_y(&r->pet_play),false,now);
    r->pet_play.generation=r->reaction_generation;
    r->pet_play.phase=orient?COMP_PET_PLAY_ORIENT:COMP_PET_PLAY_CUE;
}
#endif
static void release_gaze(comp_runtime_t *r,uint32_t now)
{
    if(r->pet_play.phase)return;
    if(r->deferred_pet_kind==COMP_RUNTIME_PET_INPUT_FOLLOW)
        r->deferred_pet_kind=COMP_RUNTIME_PET_INPUT_NONE;
    if(r->surface!=COMP_SCREEN_SURFACE_HOME || record_busy(r) ||
       r->hold_enter_requested || (r->reaction_pending && r->reaction_route_count))return;
    if(r->gaze_x==100u && r->gaze_y==100u) {
        /* The finger may have brought an already visible gaze home itself.
         * No return frame is needed, but engagement must not expose an old
         * overdue idle blink. Pending/failed poses still wait for visibility. */
        if(r->visible_frames && r->visible_surface==COMP_SCREEN_SURFACE_HOME &&
           !r->frame_outstanding && !r->reaction_pending &&
           !r->blink.open_pending && !r->blink.open_in_flight)
            comp_epaper_natural_blink_enter_daily(&r->blink,now);
        return;
    }
    /* Keep the last look during this readable pause. Only the eventual return
     * frame selects centre; a status update cannot shorten the pause. A newer
     * contact supersedes this target without changing any in-flight image. */
    r->reaction_route_count=0u;r->reaction_step=1u;
    r->reaction_due_ms=now+PET_GAZE_RELEASE_HOLD_MS;
    ++r->reaction_generation;r->reaction_pending=true;
}
static void stroke_reply(comp_runtime_t *r,uint16_t x,comp_browser_tap_zone_t zone,uint32_t now)
{
    if(r->pet_play.phase)return;
    if(record_busy(r) || r->surface!=COMP_SCREEN_SURFACE_HOME)return;
    if(r->reaction_pending && r->reaction_route_count) {
        /* The accepted phrase keeps its seed and poses. Coalesce one latest
         * stroke behind it, without scoring samples as repeated taps. */
        r->deferred_pet_x=x;r->deferred_pet_y=(uint16_t)zone;
        r->deferred_pet_kind=COMP_RUNTIME_PET_INPUT_STROKE;
        r->deferred_pet_ms=now;
        return;
    }
    r->deferred_pet_kind=COMP_RUNTIME_PET_INPUT_NONE;
    choose_reply_variation(r,COMP_PET_HEAD_PAT,x,now);
#if COMP_PET_PROCEDURAL
    /* A qualified sustained forehead sweep can settle into the original
     * comfortable whole-face pose instead of replaying a random light pat.
     * Keep authored soothing/boundary accents and the accepted phrase seed.
     * Dwell is earned only after qualified visibility; no extra frame. */
    if(r->pet.accent==COMP_PET_ACCENT_NONE) {
        /* The original open-eye warm side pose visibly accepts a stroke.
         * A neutral daily face hid that acknowledgement. Keep the light
         * pat's closed-eye smile and the accepted hand side distinct. */
        r->pet.first_family=COMP_BROWSER_FAMILY_WARM;
        r->pet.first_zone=(uint8_t)zone;
        /* Lively may already have selected this same whole-face peek.
         * Do not spend a second panel transaction repeating that image. */
        if(r->pet.second_family==r->pet.first_family &&
           r->pet.second_zone==r->pet.first_zone)
            r->pet.second_family=COMP_BROWSER_FAMILY_NONE;
    }
    r->pet.peak_hold_ms=(uint16_t)(r->pet.peak_hold_ms+900u);
#endif
    r->gaze_x=x;r->gaze_y=60u;
    /* Reuse the original comfortable head-pat pose and existing return beat.
     * Genuine stroking is not single-tap affect evidence. The panel's normal
     * completion/dwell gates still own every step and any optional pose. */
#if COMP_PET_PROCEDURAL
    begin_reply(r,r->affect.selected,(comp_browser_family_t)r->pet.first_family,
        (comp_browser_tap_zone_t)r->pet.first_zone,(comp_browser_family_t)r->pet.second_family,
        (comp_browser_tap_zone_t)r->pet.second_zone,now);
#else
    begin_reply(r,r->affect.selected,COMP_BROWSER_FAMILY_WARM,
        COMP_BROWSER_TAP_ZONE_DOWN,COMP_BROWSER_FAMILY_NONE,
        COMP_BROWSER_TAP_ZONE_CENTER,now);
#endif
}
static void stroke_contact(comp_runtime_t *r,uint16_t x,uint16_t y,
                           bool starting,uint32_t now)
{
    if(starting) { r->pet_stroke_phase=PET_STROKE_NONE;r->pet_stroke_anchor_x=x; }
    if(r->pet_stroke_phase==PET_STROKE_CONSUMED ||
       r->pet_stroke_phase==PET_STROKE_DISABLED)return;
    if(!input_contact_ready(r) || r->surface!=COMP_SCREEN_SURFACE_HOME || r->hold_enter_requested ||
       record_busy(r) || x<40u || x>160u || y<35u || y>=(starting?140u:148u)) {
        /* A natural petting path crosses the visible face, including the
         * eyes near y105, not only the narrow forehead above y96. Keep the
         * status strip and bottom recording shortcuts outside this area;
         * the continuation margin avoids cancelling at its lower edge.
         * Distance/time, single-consumption and menu/recording guards still
         * distinguish a stroke from gaze, tapping and a stationary hold. */
        r->pet_stroke_phase=PET_STROKE_DISABLED;return;
    }
    const int dx=(int)x-(int)r->pet_stroke_anchor_x;
    if(r->pet_stroke_phase==PET_STROKE_NONE) {
        if(dx>=(int)PET_STROKE_LEG_PX) {r->pet_stroke_phase=PET_STROKE_RIGHT;r->pet_stroke_anchor_x=x;}
        else if(dx<=-(int)PET_STROKE_LEG_PX) {r->pet_stroke_phase=PET_STROKE_LEFT;r->pet_stroke_anchor_x=x;}
    } else if(r->pet_stroke_phase==PET_STROKE_RIGHT) {
        if(dx>0)r->pet_stroke_anchor_x=x;
        else if(dx<=-(int)PET_STROKE_RETURN_PX)r->pet_stroke_phase=PET_STROKE_READY;
    } else if(r->pet_stroke_phase==PET_STROKE_LEFT) {
        if(dx<0)r->pet_stroke_anchor_x=x;
        else if(dx>=(int)PET_STROKE_RETURN_PX)r->pet_stroke_phase=PET_STROKE_READY;
    }
    /* A single deliberate forehead sweep is petting too. Accept it while the
     * finger is present, once its distance and duration are earned; no forced
     * reversal or extra release frame. Leaving the forehead disables this
     * contact. Quiet retains its one gentle beat, cooldown and silent audio. */
    if((r->pet_stroke_phase==PET_STROKE_RIGHT || r->pet_stroke_phase==PET_STROKE_LEFT ||
        r->pet_stroke_phase==PET_STROKE_READY) && now-r->gesture.start_ms>=PET_STROKE_MIN_MS) {
        /* Choose from the accepted sweep, not a sample's screen half.
         * Keep it in the existing deferred slot when another phrase owns
         * the panel; a later contact must not change this stroke's side. */
        const comp_browser_tap_zone_t zone=r->pet_stroke_phase==PET_STROKE_LEFT?
            COMP_BROWSER_TAP_ZONE_LEFT:r->pet_stroke_phase==PET_STROKE_RIGHT?
            COMP_BROWSER_TAP_ZONE_RIGHT:x<r->gesture.start_x?
            COMP_BROWSER_TAP_ZONE_LEFT:COMP_BROWSER_TAP_ZONE_RIGHT;
        r->pet_stroke_phase=PET_STROKE_CONSUMED;
        comp_touch_tap_arbiter_cancel(&r->taps);
        comp_browser_menu_hold_end(&r->hold);r->hold_enter_requested=false;
        stroke_reply(r,x,zone,now);
    }
}
static bool menu_result(comp_runtime_t *r, comp_screen_menu_result_t result,
                        uint32_t now,const comp_screen_menu_t *previous)
{
    bool accepted = true;
    bool touch_confirm = true;

    if (!result.changed && result.action == COMP_SCREEN_MENU_ACTION_NONE) {
        return true;
    }
    switch (result.action) {
    case COMP_SCREEN_MENU_ACTION_RECORD_START:
        accepted = comp_runtime_record(r, true, now) == COMP_RUNTIME_OK;
        if (r->capture_active) r->menu.flags |= COMP_SCREEN_MENU_FLAG_RECORDING;
        else r->menu.flags &= (uint8_t)~COMP_SCREEN_MENU_FLAG_RECORDING;
        touch_confirm = false;
        break;
    case COMP_SCREEN_MENU_ACTION_RECORD_STOP:
        accepted = comp_runtime_record(r, false, now) == COMP_RUNTIME_OK;
        if (r->capture_active) r->menu.flags |= COMP_SCREEN_MENU_FLAG_RECORDING;
        else r->menu.flags &= (uint8_t)~COMP_SCREEN_MENU_FLAG_RECORDING;
        touch_confirm = false;
        break;
    case COMP_SCREEN_MENU_ACTION_EXIT_DAILY:
        enter_home(r, now);
        r->last_result = COMP_RUNTIME_OK;
        break;
    case COMP_SCREEN_MENU_ACTION_PET_QUIET_TIMER:
        touch_confirm=false;
        if(record_busy(r) || r->menu_pending || (r->status_packed&COMP_SCREEN_STATUS_UPDATING)) {
            accepted=false;menu_feedback_at(r,COMP_RUNTIME_MENU_FEEDBACK_BUSY,menu_context(r));
            (void)reject(r,COMP_RUNTIME_BUSY,now);r->last_result_from_menu=true;
        } else {
            r->temporary_quiet_active=!r->temporary_quiet_active;
            r->temporary_quiet_started_ms=now;
            r->temporary_quiet_base_level=r->menu.browser.interaction_level;
            r->temporary_quiet_last_minute=r->temporary_quiet_active?30u:0u;
            r->menu_feedback=COMP_RUNTIME_MENU_FEEDBACK_NONE;
            r->last_result=COMP_RUNTIME_OK;r->last_result_from_menu=false;
        }
        break;
    case COMP_SCREEN_MENU_ACTION_PET_PLAY:
    case COMP_SCREEN_MENU_ACTION_PET_GREETING:
        touch_confirm=false;
        if(record_busy(r) || r->menu_pending || (r->status_packed&COMP_SCREEN_STATUS_UPDATING)) {
            accepted=false;menu_feedback_at(r,COMP_RUNTIME_MENU_FEEDBACK_BUSY,menu_context(r));
            (void)reject(r,COMP_RUNTIME_BUSY,now);
            r->last_result_from_menu=true;
        } else {
            const comp_browser_family_t before=r->affect.selected;
            enter_home(r,now);
            if(result.action==COMP_SCREEN_MENU_ACTION_PET_PLAY) {
                uint32_t entropy=r->pet.seed;
                if(r->config.random_u32)(void)r->config.random_u32(r->config.context,&entropy);
                /* Use only authored directions the installed bank declares.
                 * Choose one finite phrase; retries retain the same cue. */
                bool vertical=false;
#if defined(COMPANION_WBA_PET_EMOTION_VERTICAL_V5) && COMPANION_WBA_PET_EMOTION_VERTICAL_V5
                vertical=true;
#endif
                r->pet_play=(comp_pet_play_t){.phase=COMP_PET_PLAY_NEXT,
                    .pattern=comp_pet_play_pattern(entropy,vertical),.due_ms=now,
                    .home_family=(uint8_t)before};
                dismiss_discovery(r);
                r->pet_startup_pending=false;
            } else {
                choose_reply_variation(r,COMP_PET_GREETING,100u,now);
#if COMP_PET_PROCEDURAL
                begin_reply(r,before,(comp_browser_family_t)r->pet.first_family,
                    (comp_browser_tap_zone_t)r->pet.first_zone,(comp_browser_family_t)r->pet.second_family,
                    (comp_browser_tap_zone_t)r->pet.second_zone,now);
#else
                begin_reply(r,before,COMP_BROWSER_FAMILY_CURIOUS,COMP_BROWSER_TAP_ZONE_UP,
                    COMP_BROWSER_FAMILY_WARM,COMP_BROWSER_TAP_ZONE_CENTER,now);
#endif
            }
            r->last_result=COMP_RUNTIME_OK;
        }
        break;
    case COMP_SCREEN_MENU_ACTION_BROWSER_SLEEP_NOW:
        accepted = sleep_now(r,now);
        if (accepted) r->last_result = COMP_RUNTIME_OK;
        else {
            menu_feedback_at(r,COMP_RUNTIME_MENU_FEEDBACK_BUSY,menu_context(r));
            (void)reject(r, COMP_RUNTIME_BUSY, now);
            r->last_result_from_menu=true;
        }
        break;
    case COMP_SCREEN_MENU_ACTION_NONE:
        r->last_result = COMP_RUNTIME_OK;
        r->last_result_from_menu=false;
        if (r->menu_pending)menu_feedback_at(r,pending_menu_feedback(r),r->menu_pending_context);
        else if(r->menu_feedback_seen)r->menu_feedback=COMP_RUNTIME_MENU_FEEDBACK_NONE;
        /* An unseen outcome remains scoped to its origin. It can be read
         * on return, without putting it on this unrelated destination. */
        break;
    default:
        if (r->menu_pending) {
            accepted = false; /* Roll back the second tentative menu revision. */
            if(result.action==COMP_SCREEN_MENU_ACTION_BROWSER_CLEAR_RECORDINGS &&
               r->menu_pending_action==result.action &&
               r->menu_pending_item==result.browser_item &&
               r->menu_pending_context==menu_context(r)) {
                /* This confirmation already owns one asynchronous request.
                 * Keep its clearing/retrying truth instead of replacing it
                 * with BUSY or playing an error for a harmless repeat tap. */
                touch_confirm=false;
                r->last_result=COMP_RUNTIME_OK;
                menu_feedback_at(r,pending_menu_feedback(r),r->menu_pending_context);
                r->last_result_from_menu=true;
            } else {
                if(result.browser_item==COMPANION_BROWSER_MENU_ITEM_STATUS_BAR)
                    r->menu.browser.battery_fill=!r->menu.browser.battery_fill;
                (void)reject(r, COMP_RUNTIME_BUSY, now);
                menu_feedback_at(r,COMP_RUNTIME_MENU_FEEDBACK_BUSY,menu_context(r));
                r->last_result_from_menu=true;
            }
        } else {
            if (++r->menu_token==0u) ++r->menu_token;
            r->menu_pending_action=result.action;
            r->menu_pending_item=result.browser_item;
            if(comp_screen_menu_customer_active() && previous && result.browser_item<64u &&
               (result.action==COMP_SCREEN_MENU_ACTION_BROWSER_SETTING_CHANGED || result.action==COMP_SCREEN_MENU_ACTION_LANGUAGE_CHANGED)) {
                const uint8_t prior=comp_screen_menu_customer_setting_value(previous,result.browser_item);
                /* At most four choices. Borrow the spare two item bits while
                 * this one backend request owns the slot; no state grows. */
                if(prior<4u)r->menu_pending_item=(uint8_t)(result.browser_item|(prior<<6u));
            }
            r->menu_pending_context=menu_context(r);
            r->battery_display_previous=!r->menu.browser.battery_fill;
            r->menu_pending=true;
            r->menu_pending_retrying=false;
            menu_feedback_at(r,pending_menu_feedback(r),r->menu_pending_context);
            comp_runtime_menu_dispatch_t dispatch=r->config.menu_action_begin ?
                r->config.menu_action_begin(r->config.context,&result,&r->menu,r->menu_token) :
                r->config.menu_action && r->config.menu_action(r->config.context,&result,&r->menu) ?
                    COMP_RUNTIME_MENU_COMPLETE : COMP_RUNTIME_MENU_UNAVAILABLE;
            if (dispatch==COMP_RUNTIME_MENU_COMPLETE) {
                (void)comp_runtime_menu_complete(r,r->menu_token,COMP_RUNTIME_OK,now);
            } else if (dispatch==COMP_RUNTIME_MENU_PENDING) {
                r->last_result=COMP_RUNTIME_OK;
                touch_confirm=false;
            } else {
                accepted=false;
                (void)comp_runtime_menu_complete(r,r->menu_token,
                    dispatch==COMP_RUNTIME_MENU_BUSY?COMP_RUNTIME_BUSY:
                    dispatch==COMP_RUNTIME_MENU_UNAVAILABLE?COMP_RUNTIME_UNAVAILABLE:COMP_RUNTIME_BACKEND_FAILED,now);
            }
        }
        break;
    }
    audio_settings(r);
    if (accepted && touch_confirm) {
        (void)comp_audio_feedback_submit(&r->audio,
                                         COMP_AUDIO_FEEDBACK_TOUCH_CONFIRM,
                                         now);
    }
    dirty(r);
    return accepted;
}
bool comp_runtime_menu_complete(comp_runtime_t *r,uint32_t token,
    comp_runtime_result_t result,uint32_t now)
{
    if(!r || !token || !r->menu_pending || token!=r->menu_token || (unsigned)result>COMP_RUNTIME_BACKEND_FAILED)return false;
    const bool here=r->surface==COMP_SCREEN_SURFACE_MENU && menu_context(r)==r->menu_pending_context;
    const bool clear_local_feedback=r->surface==COMP_SCREEN_SURFACE_MENU &&
        menu_context(r)==r->menu_feedback_context && r->menu_feedback!=COMP_RUNTIME_MENU_FEEDBACK_NONE;
    bool appearance_changed=here || clear_local_feedback;
    r->menu_pending=false;
    /* A foreground operation can outlast the idle timeout (pairing permits
     * two minutes). Give its real outcome a normal reading window instead
     * of sleeping before it can land. Background/stale completions do not
     * keep another page awake; the token guard above remains authoritative. */
    if(here)r->last_activity_ms=now;
    r->menu_feedback_context=r->menu_pending_context;
    r->menu_feedback_seen=false;r->menu_effect_result=(uint8_t)result;
    if(result==COMP_RUNTIME_OK) {
        /* Explicit successful mode changes/default reset supersede a timer.
         * Failed/pending writes and unrelated volume changes cannot do so. */
        if(r->menu_pending_action==COMP_SCREEN_MENU_ACTION_BROWSER_RESTORE_DEFAULTS ||
           (r->menu_pending_action==COMP_SCREEN_MENU_ACTION_BROWSER_SETTING_CHANGED &&
            (r->menu_pending_item&63u)==42u)) {
            r->temporary_quiet_active=false;r->temporary_quiet_last_minute=0u;
            audio_settings(r);appearance_changed=true;
        }
        r->last_result=COMP_RUNTIME_OK;
        r->menu_feedback=r->menu_pending_action==COMP_SCREEN_MENU_ACTION_BROWSER_CLEAR_RECORDINGS ? COMP_RUNTIME_MENU_FEEDBACK_CLEARED :
            r->menu_pending_action==COMP_SCREEN_MENU_ACTION_BROWSER_RESTORE_DEFAULTS ? COMP_RUNTIME_MENU_FEEDBACK_RESTORED :
            (r->menu_pending_action==COMP_SCREEN_MENU_ACTION_BROWSER_PAIR || r->menu_pending_action==COMP_SCREEN_MENU_ACTION_PHONE_RECONNECT) ? COMP_RUNTIME_MENU_FEEDBACK_CONNECTED :
            COMP_RUNTIME_MENU_FEEDBACK_SAVED;
    } else {
        if(comp_screen_menu_customer_active() &&
           (r->menu_pending_action==COMP_SCREEN_MENU_ACTION_BROWSER_SETTING_CHANGED ||
            r->menu_pending_action==COMP_SCREEN_MENU_ACTION_LANGUAGE_CHANGED)) {
            if(comp_screen_menu_customer_restore_value(&r->menu,r->menu_pending_item&63u,r->menu_pending_item>>6u))appearance_changed=true;
        } else if(r->menu_pending_item==COMPANION_BROWSER_MENU_ITEM_STATUS_BAR &&
           r->menu.browser.battery_fill!=r->battery_display_previous) {
            r->menu.browser.battery_fill=r->battery_display_previous;
            ++r->menu.revision;
            appearance_changed=true;
        }
        r->menu_feedback=result==COMP_RUNTIME_BUSY?COMP_RUNTIME_MENU_FEEDBACK_BUSY:
            result==COMP_RUNTIME_UNAVAILABLE?COMP_RUNTIME_MENU_FEEDBACK_UNAVAILABLE:COMP_RUNTIME_MENU_FEEDBACK_FAILED;
        (void)reject_result(r,result,now,false);
    }
    r->last_result_from_menu=true;
    if(appearance_changed)dirty(r);
    return true;
}
bool comp_runtime_menu_retrying(comp_runtime_t *r,uint32_t token,bool retrying)
{
    if(!r || !r->menu_pending || token!=r->menu_token ||
       r->menu_pending_action!=COMP_SCREEN_MENU_ACTION_BROWSER_CLEAR_RECORDINGS)return false;
    r->menu_pending_retrying=retrying;
    comp_runtime_menu_feedback_t feedback=pending_menu_feedback(r);
    const bool here=r->surface==COMP_SCREEN_SURFACE_MENU && menu_context(r)==r->menu_pending_context;
    if((here || r->menu_feedback_context==r->menu_pending_context) &&
       (r->menu_feedback!=feedback || r->menu_feedback_context!=r->menu_pending_context)){
        menu_feedback_at(r,feedback,r->menu_pending_context);
        if(here)dirty(r);
    }
    return true;
}
bool comp_runtime_menu_pair_timeout(comp_runtime_t *r,uint32_t token,uint32_t now)
{
    if(!r || (r->menu_pending_action!=COMP_SCREEN_MENU_ACTION_BROWSER_PAIR && r->menu_pending_action!=COMP_SCREEN_MENU_ACTION_PHONE_RECONNECT) ||
       !comp_runtime_menu_complete(r,token,COMP_RUNTIME_BACKEND_FAILED,now))return false;
    r->menu_feedback=COMP_RUNTIME_MENU_FEEDBACK_TIMEOUT;
    return true;
}
static bool corner(uint16_t x, uint16_t y)
{
    return x <= COMPANION_BROWSER_INTERACTION_RECORDING_CORNER_MAX_X_200 &&
        y >= COMPANION_BROWSER_INTERACTION_RECORDING_CORNER_MIN_Y_200;
}
static bool menu_relative_swipe_ready(const comp_runtime_t *r)
{
#if COMPANION_WBA_RESOURCE_PROFILE
    /* The visible page and target are the same view. Navigation is relative;
     * absolute taps still require the exact successfully committed revision.
     * A new visible control revision retires this contact. A clock-only
     * completion retains the exact same controls and may keep the intent. */
    return r->menu.view!=COMP_SCREEN_MENU_VIEW_BROWSER_QUICK &&
        r->surface==COMP_SCREEN_SURFACE_MENU && r->visible_surface==COMP_SCREEN_SURFACE_MENU &&
        r->visible_menu_valid && r->frame_outstanding && !r->menu_pending && !record_busy(r) &&
        r->visible_menu_view==r->menu.view && r->input_contact_surface==COMP_SCREEN_SURFACE_MENU &&
        r->input_contact_visible_frame==r->visible_menu_revision;
#else
    (void)r;return false;
#endif
}
static void gesture(comp_runtime_t *r, const comp_touch_gesture_event_t *e, uint32_t now)
{
    if(comp_runtime_recording_hold(r))return;
    /* The old recording image still owns this contact after backend STOP.
     * Keep menu controls independent; HOME retries are neither START nor petting. */
    if (r->surface==COMP_SCREEN_SURFACE_HOME && !record_busy(r) &&
        (r->record_touch_start_blocked || r->record_saved_state==RECORD_NOTICE_SAVED_PENDING)) return;
    bool edge = e->type == COMP_TOUCH_GESTURE_SWIPE_RIGHT && corner(e->start_x, e->start_y) &&
        (int)e->end_x - (int)e->start_x >= 36 &&
        (e->end_y > e->start_y ? e->end_y - e->start_y : e->start_y - e->end_y) <= 24 && e->duration_ms >= 120u;
    if (!input_contact_ready(r)) {
        /* A fresh contact can wake HOME before its first image is visible.
         * The selected recording shortcut is independent of page controls:
         * retain that deliberate intent from the visible sleep page only.
         * Single taps, stale contacts and menu gestures keep the normal gate. */
        const bool wake_record=r->input_contact_surface==COMP_SCREEN_SURFACE_LOW_POWER &&
            r->surface==COMP_SCREEN_SURFACE_HOME &&
            (r->visible_surface==COMP_SCREEN_SURFACE_LOW_POWER ||
             r->visible_surface==COMP_SCREEN_SURFACE_HOME) &&
            !record_busy(r) && !r->menu_pending && r->quick_contact==QUICK_CONTACT_NONE;
        if(wake_record &&
           ((e->type==COMP_TOUCH_GESTURE_DOUBLE_TAP &&
             r->menu.browser.recording_gesture==COMP_SCREEN_MENU_RECORDING_GESTURE_CORNER_DOUBLE_TAP &&
             corner(r->gesture.last_tap_x,r->gesture.last_tap_y) &&
             corner(e->start_x,e->start_y) && corner(e->end_x,e->end_y)) ||
            (edge && r->menu.browser.recording_gesture==COMP_SCREEN_MENU_RECORDING_GESTURE_EDGE_PULL))) {
            comp_touch_tap_arbiter_cancel(&r->taps);
            r->input_contact_eligible=false;
            (void)comp_runtime_record(r,true,now);
            return;
        }
        if(r->input_contact_eligible && menu_relative_swipe_ready(r) &&
           (e->type==COMP_TOUCH_GESTURE_SWIPE_UP || e->type==COMP_TOUCH_GESTURE_SWIPE_DOWN ||
            e->type==COMP_TOUCH_GESTURE_SWIPE_RIGHT)) {
            r->menu_deferred_swipe=e->type==COMP_TOUCH_GESTURE_SWIPE_UP?1u:
                e->type==COMP_TOUCH_GESTURE_SWIPE_DOWN?2u:3u;
            r->last_activity_ms=now;
        }
        r->input_contact_eligible = false;
        return;
    }
    if(r->quick_contact==QUICK_CONTACT_VOLUME || r->quick_contact==QUICK_CONTACT_CANCELLED)return;
    if(r->quick_contact==QUICK_CONTACT_PULL) {
#if COMPANION_WBA_RESOURCE_PROFILE && COMPANION_WBA_UI_EXTERNAL && COMPANION_WBA_RESOURCE_GENERATION >= 71u
        const int dy=(int)e->end_y-(int)e->start_y;
        const unsigned dx=e->end_x>e->start_x?e->end_x-e->start_x:e->start_x-e->end_x;
        if(e->type==COMP_TOUCH_GESTURE_SWIPE_DOWN && dy>=48 && (unsigned)dy>=dx+24u &&
           r->surface==COMP_SCREEN_SURFACE_HOME && !record_busy(r) && !r->menu_pending) {
            enter_menu(r,COMP_SCREEN_MENU_VIEW_BROWSER_QUICK);
        }
#endif
        return;
    }
    if (r->surface == COMP_SCREEN_SURFACE_MENU) {
        /* A newer immediately actionable operation supersedes a queued page. */
        r->menu_deferred_swipe=0u;
        comp_screen_menu_t before = r->menu;
        /* Menu taps are independent clicks. Do not let HOME's double-tap
         * recognizer swallow a second fast click on the same visible page. */
        r->gesture.tap_pending=false;
        /* One physical contact can commit at most one menu operation. */
        r->input_contact_eligible = false;
        comp_screen_menu_result_t result = (e->type == COMP_TOUCH_GESTURE_TAP ||
            e->type == COMP_TOUCH_GESTURE_DOUBLE_TAP) ?
            comp_screen_menu_tap_contact(&r->menu,e->start_x,e->start_y,e->end_x,e->end_y) :
            comp_screen_menu_gesture(&r->menu, e);
        /* All externally-owned actions are optimistic menu mutations. A
         * rejected record command or setting must not remain visibly applied. */
        if (!menu_result(r, result, now,&before)) {
            r->menu = before;
            audio_settings(r);
        }
        return;
    }
    /* A completed sweep must not become another swipe/tap on release. */
    if(r->pet_stroke_phase==PET_STROKE_CONSUMED)return;
    if (e->type == COMP_TOUCH_GESTURE_DOUBLE_TAP) {
        comp_touch_tap_arbiter_cancel(&r->taps);
        /* Pause releases the microphone but still owns the same recording.
         * Preserve the established double-tap STOP, including while paused. */
        if (record_busy(r)) {
            (void)comp_runtime_record(r, false, now);
            return;
        }
        if (corner(e->end_x, e->end_y) && r->menu.browser.recording_gesture == COMP_SCREEN_MENU_RECORDING_GESTURE_CORNER_DOUBLE_TAP) {
            (void)comp_runtime_record(r, true, now); return;
        }
    }
    if (record_busy(r)) {
        /* A first-use single tap/hold is a request for guidance, never STOP.
         * Keep the established double tap above; no extra button or hot area. */
        if(r->capture_active && !r->stop_pending && !r->record_saved_state &&
           (e->type==COMP_TOUCH_GESTURE_TAP || e->type==COMP_TOUCH_GESTURE_HOLD ||
            e->type==COMP_TOUCH_GESTURE_LONG_PRESS)) {
            r->record_saved_state=RECORD_NOTICE_STOP_PENDING;dirty(r);
        }
        return;
    }
    if (edge && r->menu.browser.recording_gesture == COMP_SCREEN_MENU_RECORDING_GESTURE_EDGE_PULL) {
        (void)comp_runtime_record(r, true, now); return;
    }
    if (e->type == COMP_TOUCH_GESTURE_LONG_PRESS) {
        if(r->hold.active && !r->drag_contact)r->hold_enter_requested=true;
        return;
    }
    if (e->type == COMP_TOUCH_GESTURE_HOLD) return;
    if(r->pet_play.phase && (e->type==COMP_TOUCH_GESTURE_SWIPE_RIGHT ||
                            e->type==COMP_TOUCH_GESTURE_SWIPE_LEFT)) {
        exit_pet_play(r,now);return;
    }
    if (e->type == COMP_TOUCH_GESTURE_TAP && corner(e->end_x, e->end_y))
        comp_touch_tap_arbiter_defer(&r->taps, e->end_x, e->end_y, now);
    else if (e->type == COMP_TOUCH_GESTURE_TAP || e->type == COMP_TOUCH_GESTURE_DOUBLE_TAP) {
        /* A swipe is following attention, not tap evidence or an extra reply.
         * Recording edge-pull and actual menu navigation were handled above. */
        react(r, e->end_x, e->end_y, now);
    }
}
void comp_runtime_touch_unavailable(comp_runtime_t *r)
{
    if (!r) return;
    if(r->pet_play.phase) {
        r->pet_play.phase=COMP_PET_PLAY_OFF;
        r->reaction_pending=false;r->reaction_route_count=0u;r->reaction_step=0u;
        ++r->reaction_generation;r->gaze_x=r->gaze_y=100u;dirty(r);
    }
    r->menu_deferred_swipe=0u;
    r->quick_contact=QUICK_CONTACT_NONE;
    comp_touch_gesture_config_t config = r->gesture.config;
    const bool touch_was_ok =
        (r->menu.flags & COMP_SCREEN_MENU_FLAG_TOUCH_OK) != 0u;
    const bool accepted_hold=r->hold_enter_requested && r->hold.active &&
        r->surface==COMP_SCREEN_SURFACE_HOME && !record_busy(r);
    const bool interrupted_contact=r->touch_contact || r->gesture.active ||
        r->gesture.consumed_until_release;
    comp_touch_gesture_init(&r->gesture, &config);
    /* Lost acquisition cannot prove release. Retire this contact until fresh
     * valid release reports, without keeping a phantom touch blocking sleep. */
    r->gesture.consumed_until_release=interrupted_contact;
    comp_touch_tap_arbiter_cancel(&r->taps);
    /* Acquisition loss invalidates input, not a long press already accepted
     * before the panel completed its final progress picture. */
    if(!accepted_hold) {
        comp_browser_menu_hold_end(&r->hold);r->hold_enter_requested=false;
    }
    r->touch_contact = false; r->drag_contact=false;
    r->pet_stroke_phase=PET_STROKE_DISABLED;
    r->deferred_pet_kind=COMP_RUNTIME_PET_INPUT_NONE;
    if(!r->reaction_route_count && (r->reaction_pending || r->gaze_x!=100u || r->gaze_y!=100u)) {
        r->reaction_pending=false;++r->reaction_generation;
        r->reaction_step=0u;
        r->gaze_x=r->gaze_y=100u;dirty(r);
    }
    r->input_contact_eligible = false;
    r->menu.flags &= (uint8_t)~COMP_SCREEN_MENU_FLAG_TOUCH_OK;
    if (touch_was_ok) dirty(r);
}
/* Consume only a fresh deliberate contact on this recording's visible lock.
 * This runs before ordinary HOLD input suppression so explicit unlock remains
 * reachable. It never dispatches the generic tap/double-tap/menu gestures. */
void comp_runtime_touch(comp_runtime_t *r, const comp_ft6336_touch_sample_t *s,
    uint32_t sequence, bool valid, uint32_t now)
{
    comp_touch_gesture_event_t event = {0};
    bool contact;
    if (!r) return;
    if((r->status_packed&COMP_SCREEN_STATUS_UPDATING) && !record_busy(r))return;
    /* Sequence identifies the acquisition, including an invalid acquisition.
     * A repeated stale report must never cancel a newer live contact. */
    if (r->touch_sequence_valid && sequence == r->last_touch_sequence) return;
    r->touch_sequence_valid = true;
    r->last_touch_sequence = sequence;
    if (!valid || !s || s->touch_count > 1u || s->x >= 200u || s->y >= 200u || s->event == COMP_FT6336_TOUCH_EVENT_RESERVED) {
        comp_runtime_touch_unavailable(r);
        return;
    }
    if ((r->menu.flags & COMP_SCREEN_MENU_FLAG_TOUCH_OK) == 0u) dirty(r);
    r->menu.flags |= COMP_SCREEN_MENU_FLAG_TOUCH_OK;
    contact = s->touch_count == 1u && s->event != COMP_FT6336_TOUCH_EVENT_UP && s->event != COMP_FT6336_TOUCH_EVENT_NONE;
    const bool down_boundary=contact && s->event==COMP_FT6336_TOUCH_EVENT_DOWN &&
        r->last_touch_event==COMP_FT6336_TOUCH_EVENT_CONTACT && r->gesture.active &&
        r->surface==COMP_SCREEN_SURFACE_HOME && r->quick_contact==QUICK_CONTACT_NONE &&
        !r->hold_enter_requested && !comp_runtime_recording_hold(r);
    r->last_touch_event=s->event;
    if(down_boundary) {
        /* The controller's new DOWN is an explicit lifecycle boundary. Use
         * the existing recognizer helper, as the old development board did;
         * never turn repeated DOWN reports or invalid reads into extra taps. */
        if(comp_touch_gesture_restart_contact(&r->gesture,s->x,s->y,now,&event)) {
            gesture(r,&event,now);
            if(event.type==COMP_TOUCH_GESTURE_DOUBLE_TAP)return;
        }
        r->touch_contact=false;r->drag_contact=false;
        comp_browser_menu_hold_end(&r->hold);
    }
    if(comp_runtime_recording_hold(r)) {
        /* Input suppression is not lost touch hardware. Consume only real
         * release debounce while locked; no tap, swipe or STOP can escape. */
        if(contact)r->gesture.consumed_until_release=true;
        (void)comp_touch_gesture_process(&r->gesture,contact,
            s->event==COMP_FT6336_TOUCH_EVENT_UP,s->x,s->y,now,&event);
        r->touch_contact=false;r->drag_contact=false;r->input_contact_eligible=false;
        return;
    }
    if(r->gesture.consumed_until_release && !r->input_contact_eligible) {
        /* Acquisition recovery or a foreground-owner handoff must not reuse
         * the old finger as a fresh DOWN, gaze, slider or recording gesture.
         * Only valid release reports clear the existing debounce quarantine;
         * an already accepted long hold remains owned by its visible frames. */
        (void)comp_touch_gesture_process(&r->gesture,contact,
            s->event==COMP_FT6336_TOUCH_EVENT_UP,s->x,s->y,now,&event);
        r->touch_contact=contact;
        return;
    }
    const bool starting_contact=contact && !r->touch_contact;
    if(starting_contact) {
        dismiss_discovery(r);
        if(deferred_motion(r))r->deferred_pet_kind=COMP_RUNTIME_PET_INPUT_NONE;
        /* A real finger supersedes incidental motion, while an immutable
         * image already in flight still completes under its original token.
         * Never retire an accepted touch/greeting phrase in this path. */
        if(r->surface==COMP_SCREEN_SURFACE_HOME && pet_motion_intent(r) &&
           r->reaction_pending && r->reaction_route_count) {
            comp_audio_feedback_cancel_pet(&r->audio);
            r->reaction_pending=false;r->reaction_route_count=0u;r->reaction_step=0u;
            ++r->reaction_generation;
        }
    }
    if (contact) {
        comp_runtime_wake_from(r,now,COMP_RUNTIME_WAKE_TOUCH);
        if (!r->touch_contact) {
            /* Keep both halves of a double tap tied to what the finger saw.
             * A fresh tap after the saved receipt is visible can START again;
             * no fixed cooldown, extra frame or recording-backend delay. */
            r->record_touch_start_blocked=record_busy(r) ||
                r->record_saved_state==RECORD_NOTICE_SAVED_PENDING ||
                (r->record_touch_start_blocked && r->gesture.tap_pending &&
                 now-r->gesture.last_tap_ms<=r->gesture.config.double_tap_max_gap_ms);
            r->quick_contact=QUICK_CONTACT_NONE;
            r->drag_contact=false;
            r->input_contact_eligible = !r->hold_enter_requested && r->surface == r->visible_surface &&
                (r->surface != COMP_SCREEN_SURFACE_MENU ||
                 menu_controls_ready(r));
            /* Preserve the actually visible sleep origin while wake is in
             * flight. It qualifies only the explicit recording shortcut;
             * it never enables invisible HOME or menu controls. */
            r->input_contact_surface = r->visible_surface==COMP_SCREEN_SURFACE_LOW_POWER?
                COMP_SCREEN_SURFACE_LOW_POWER:r->surface;
            r->input_contact_visible_frame = r->surface==COMP_SCREEN_SURFACE_MENU?
                r->visible_menu_revision:r->visible_frames;
            r->pet_play.answer_contact=r->pet_play.phase==COMP_PET_PLAY_WAIT;
            if(menu_relative_swipe_ready(r))r->input_contact_eligible=true;
#if COMPANION_WBA_RESOURCE_PROFILE && COMPANION_WBA_UI_EXTERNAL && COMPANION_WBA_RESOURCE_GENERATION >= 71u
            if(input_contact_ready(r) && !record_busy(r) && !r->menu_pending) {
                if(r->surface==COMP_SCREEN_SURFACE_HOME && s->x>=COMP_SCREEN_QUICK_PULL_MIN_X &&
                   s->y<=COMP_SCREEN_QUICK_PULL_MAX_Y)
                    r->quick_contact=QUICK_CONTACT_PULL;
                else if(r->surface==COMP_SCREEN_SURFACE_MENU &&
                    r->menu.view==COMP_SCREEN_MENU_VIEW_BROWSER_QUICK && s->x>=12u && s->x<=188u &&
                    s->y>=COMP_SCREEN_QUICK_VOLUME_TOP && s->y<COMP_SCREEN_QUICK_VOLUME_DRAG_BOTTOM)
                    r->quick_contact=QUICK_CONTACT_VOLUME;
            }
#endif
        }
        if (!r->touch_contact && r->surface == COMP_SCREEN_SURFACE_HOME &&
            input_contact_ready(r) && !r->hold_enter_requested && !record_busy(r) &&
            r->quick_contact==QUICK_CONTACT_NONE) {
            if (++r->hold_generation==0u) ++r->hold_generation;
            comp_browser_menu_hold_begin(&r->hold);
        }
    }
    if(contact && r->quick_contact==QUICK_CONTACT_VOLUME) {
        r->quick_volume_x=s->x;
        if(r->touch_contact && (s->y+20u<r->gesture.start_y || s->y>r->gesture.start_y+20u))
            r->quick_contact=QUICK_CONTACT_CANCELLED;
    }
    if(!contact && s->event==COMP_FT6336_TOUCH_EVENT_UP && r->quick_contact==QUICK_CONTACT_VOLUME) {
        if(s->y+20u<r->gesture.start_y || s->y>r->gesture.start_y+20u)
            r->quick_contact=QUICK_CONTACT_CANCELLED;
        else r->quick_volume_x=s->x;
    }
    const bool was_contact=r->touch_contact;
    if (!down_boundary && comp_touch_gesture_process(&r->gesture, contact, s->event == COMP_FT6336_TOUCH_EVENT_UP,
                                   s->x, s->y, now, &event)) gesture(r, &event, now);
#if COMPANION_WBA_RESOURCE_PROFILE
    /* Start a menu page at the same threshold as a horizontal swipe, while
     * the finger is still down. Its release cannot replay it:gesture consumes
     * input_contact_eligible. Pet gestures keep their existing release policy. */
    if (contact && r->surface==COMP_SCREEN_SURFACE_MENU &&
        r->menu.view!=COMP_SCREEN_MENU_VIEW_BROWSER_QUICK && r->input_contact_eligible &&
        (input_contact_ready(r) || menu_relative_swipe_ready(r))) {
        const int delta=(int)s->y-(int)r->gesture.start_y;
        const int across=(int)s->x-(int)r->gesture.start_x;
        const unsigned dy=(unsigned)(delta<0?-delta:delta),dx=(unsigned)(across<0?-across:across);
        /* Menu-only live paging:20px deliberate vertical movement, with
         * dominance/slop. Home gaze, stroking and the3s hold stay unchanged. */
        if (r->gesture.active && dy>=20u && dy>=dx+12u && dy*100u>=dx*140u) {
            event.type=delta<0?COMP_TOUCH_GESTURE_SWIPE_UP:COMP_TOUCH_GESTURE_SWIPE_DOWN;
            event.start_x=r->gesture.start_x;event.start_y=r->gesture.start_y;
            event.end_x=s->x;event.end_y=s->y;
            gesture(r,&event,now);
        }
    }
#endif
    /* Use the existing release debounce for product ownership too. A single
     * empty report must not start a fresh contact or cancel a menu hold. */
    r->touch_contact=contact || r->gesture.active || r->gesture.consumed_until_release;
    const bool released_contact=was_contact && !r->touch_contact;
    if(released_contact)r->last_activity_ms=now;
    if(released_contact && r->quick_contact!=QUICK_CONTACT_NONE) {
        if(r->quick_contact==QUICK_CONTACT_VOLUME && input_contact_ready(r) &&
           r->surface==COMP_SCREEN_SURFACE_MENU && r->menu.view==COMP_SCREEN_MENU_VIEW_BROWSER_QUICK &&
           !record_busy(r))
            (void)menu_result(r,comp_screen_menu_quick_volume(&r->menu,r->quick_volume_x),now,NULL);
        r->quick_contact=QUICK_CONTACT_NONE;r->input_contact_eligible=false;
        r->gesture.tap_pending=false;
    }
    const bool menu_hold=r->surface==COMP_SCREEN_SURFACE_HOME && r->hold.active;
    const uint16_t movement_limit=menu_hold?r->gesture.config.long_press_max_move_px:r->gesture.config.tap_max_move_px;
    if ((!menu_hold && (comp_touch_gesture_is_vertical_drag(&r->gesture) || comp_touch_gesture_is_horizontal_drag(&r->gesture))) ||
        event.type==COMP_TOUCH_GESTURE_SWIPE_LEFT || event.type==COMP_TOUCH_GESTURE_SWIPE_RIGHT ||
        event.type==COMP_TOUCH_GESTURE_SWIPE_UP || event.type==COMP_TOUCH_GESTURE_SWIPE_DOWN ||
        (contact && (r->gesture.max_excursion_x>movement_limit ||
                     r->gesture.max_excursion_y>movement_limit))) r->drag_contact=true;
    if (!r->touch_contact || r->drag_contact) {
        /* A recognized stationary long press owns a pending menu intent.
         * A slow panel must not make release cancel that accepted request.
         * Motion before recognition still cancels the ordinary hold. */
        if(r->drag_contact || !r->hold_enter_requested) {
            comp_browser_menu_hold_end(&r->hold);
            r->hold_enter_requested = false;
        }
    }
    if (!r->touch_contact) r->input_contact_eligible = false;
    /* Recording intent also owns contact-follow and release-to-centre.
     * Backend completion cannot turn the same held finger into petting. */
    if (r->record_touch_start_blocked) return;
    if(contact && !r->pet_play.phase && r->quick_contact==QUICK_CONTACT_NONE)stroke_contact(r,s->x,s->y,starting_contact,now);
    if(released_contact)release_gaze(r,now);
    if (contact && r->input_contact_eligible && r->surface==COMP_SCREEN_SURFACE_HOME &&
        r->quick_contact==QUICK_CONTACT_NONE &&
        !record_busy(r) && !r->pet_play.phase && r->menu.browser.gaze_follow &&
        !r->hold_enter_requested) {
        const bool queued=r->deferred_pet_kind==COMP_RUNTIME_PET_INPUT_FOLLOW;
        const uint16_t old_x=queued?r->deferred_pet_x:r->gaze_x;
        const uint16_t old_y=queued?r->deferred_pet_y:r->gaze_y;
        const uint16_t target_x=comp_pet_gaze_target(old_x,s->x,starting_contact);
        const uint16_t target_y=comp_pet_gaze_target(old_y,s->y,starting_contact);
        if(r->reaction_pending && r->reaction_route_count) {
#if COMP_PET_PROCEDURAL
            if(r->pet_stroke_phase==PET_STROKE_CONSUMED && !r->reaction_step &&
               r->pet.interaction==COMP_PET_HEAD_PAT &&
               r->pet.last_input_ms-r->gesture.start_ms<=now-r->gesture.start_ms &&
               r->deferred_pet_kind!=COMP_RUNTIME_PET_INPUT_STROKE &&
               r->deferred_pet_kind!=COMP_RUNTIME_PET_INPUT_TAP) {
                /* Coordinates still follow this accepted stroke, but they
                 * are not new intentions. Keep its generation so the first
                 * qualified glance can lead into the affectionate reply:
                 * moving a finger during slow ink must not restart that
                 * glance forever. The submitted frame stays immutable, the
                 * next frame takes the latest target, and failures still
                 * cannot advance a beat. New contacts/intents keep their
                 * existing generation and foreground cancellation rules. */
                if(target_x!=r->gaze_x || target_y!=r->gaze_y) {
                    r->gaze_x=target_x;r->gaze_y=target_y;
                    dirty(r);
                }
                if(r->deferred_pet_kind==COMP_RUNTIME_PET_INPUT_FOLLOW)
                    r->deferred_pet_kind=COMP_RUNTIME_PET_INPUT_NONE;
                return;
            }
#endif
            /* A recognized stroke/tap is an accepted intent. Incidental
             * following from this same sample must not replace it. */
            if(r->deferred_pet_kind!=COMP_RUNTIME_PET_INPUT_STROKE &&
               r->deferred_pet_kind!=COMP_RUNTIME_PET_INPUT_TAP &&
               (starting_contact || target_x!=old_x || target_y!=old_y)) {
                r->deferred_pet_x=target_x;r->deferred_pet_y=target_y;
                r->deferred_pet_kind=COMP_RUNTIME_PET_INPUT_FOLLOW;
            }
            /* A new qualified report renews a held finger's unchanged target.
             * Render retries and service ticks never manufacture freshness. */
            if(r->deferred_pet_kind==COMP_RUNTIME_PET_INPUT_FOLLOW)r->deferred_pet_ms=now;
        } else gaze_reply(r,target_x,target_y,starting_contact,now);
    }
}
static void begin_motion_reply(comp_runtime_t *r,uint8_t events,uint8_t tilt,
    uint32_t observed_ms,uint32_t now,comp_browser_family_t before)
{
    if (events & (COMP_MOTION_PICKUP | COMP_MOTION_SHAKE | COMP_MOTION_SETTLED)) {
        const bool settled=(events & (COMP_MOTION_PICKUP | COMP_MOTION_SHAKE))==0u;
        choose_reply_variation(r,settled?COMP_PET_SETTLE:
            (events&COMP_MOTION_SHAKE)?COMP_PET_SHAKE:COMP_PET_PICKUP,100u,observed_ms);
        /* IMU cannot start/stop recordings or manufacture touch affect evidence. */
        /* Pick-up looks up before welcoming; a shake earns a short puzzled
         * look and warm recovery. Actual visibility owns the feeling clock. */
        r->gaze_x = (events & COMP_MOTION_SHAKE) ?
            ((r->reaction_variant&1u) ? 20u : 180u) : 100u;
        r->gaze_y = (settled || (events & COMP_MOTION_SHAKE)) ? 100u : 20u;
#if COMP_PET_PROCEDURAL
        /* A lift changes attention, not the existing feeling. Keep the full
         * face that the caller selected at this safe response boundary, so
         * a recent warm/playful reply is not reset to one generic calm face.
         * The original up pose, readable dwell, return and visibility gates
         * are unchanged. Shake/settle retain their authored emotion changes. */
        if(!settled && !(events&COMP_MOTION_SHAKE))
            comp_pet_behavior_pickup_attention(&r->pet,before);
        begin_reply(r,before,(comp_browser_family_t)r->pet.first_family,
            (comp_browser_tap_zone_t)r->pet.first_zone,(comp_browser_family_t)r->pet.second_family,
            (comp_browser_tap_zone_t)r->pet.second_zone,now);
#else
        if (settled)
            begin_reply(r,before,COMP_BROWSER_FAMILY_WARM,
                COMP_BROWSER_TAP_ZONE_CENTER,COMP_BROWSER_FAMILY_NONE,
                COMP_BROWSER_TAP_ZONE_CENTER,now);
        else if (events & COMP_MOTION_SHAKE)
            begin_reply(r,before,COMP_BROWSER_FAMILY_PLAYFUL,
                (r->reaction_variant&1u) ? COMP_BROWSER_TAP_ZONE_LEFT : COMP_BROWSER_TAP_ZONE_RIGHT,
                COMP_BROWSER_FAMILY_PLAYFUL,COMP_BROWSER_TAP_ZONE_CENTER,now);
        else
            begin_reply(r,before,COMP_BROWSER_FAMILY_CURIOUS,
                (r->reaction_variant&1u) ? COMP_BROWSER_TAP_ZONE_LEFT : COMP_BROWSER_TAP_ZONE_UP,
                COMP_BROWSER_FAMILY_WARM,COMP_BROWSER_TAP_ZONE_CENTER,now);
#endif
    } else if ((events & COMP_MOTION_TILT_CHANGED) && tilt <= COMP_MOTION_TILT_INVERTED) {
        const bool inverted=tilt==COMP_MOTION_TILT_INVERTED;
        const comp_browser_tap_zone_t zone=tilt==COMP_MOTION_TILT_LEFT?COMP_BROWSER_TAP_ZONE_LEFT:
            tilt==COMP_MOTION_TILT_RIGHT?COMP_BROWSER_TAP_ZONE_RIGHT:
            tilt==COMP_MOTION_TILT_UP?COMP_BROWSER_TAP_ZONE_UP:
            tilt==COMP_MOTION_TILT_DOWN?COMP_BROWSER_TAP_ZONE_DOWN:COMP_BROWSER_TAP_ZONE_CENTER;
        choose_reply_variation(r,inverted?COMP_PET_INVERTED:COMP_PET_TILT,100u,observed_ms);
        r->gaze_x=tilt==COMP_MOTION_TILT_LEFT?20u:tilt==COMP_MOTION_TILT_RIGHT?180u:100u;
        r->gaze_y=tilt==COMP_MOTION_TILT_UP?20u:tilt==COMP_MOTION_TILT_DOWN?180u:100u;
#if COMP_PET_PROCEDURAL
        r->pet.first_zone=(uint8_t)zone;
#endif
        /* Ordinary tilt is spatial attention in the existing feeling, not
         * another pick-up question/welcome. Inversion keeps its authored
         * uncertain response. Original full faces and peak timing remain. */
        begin_reply(r,before,inverted?COMP_BROWSER_FAMILY_THOUGHTFUL:
            before,zone,COMP_BROWSER_FAMILY_NONE,COMP_BROWSER_TAP_ZONE_CENTER,now);
#if COMP_PET_PROCEDURAL
        if(!inverted) {
            /* Spatial attention already keeps the same feeling. Spend the
             * next admitted transaction on its complete directional face,
             * rather than a separate glance before that same tilt. The
             * existing in-flight frame, visible peak clock and return still
             * own completion; failures retry this accepted beat unchanged. */
            r->reaction_step=1u;
            r->reaction_pose_phase=1u;r->reaction_pose_count=1u;
        }
#endif
    }
}
void comp_runtime_motion(comp_runtime_t *r, uint8_t events, uint8_t orientation, uint32_t sequence, uint32_t now)
{
    comp_runtime_motion_pose(r,events,orientation,COMP_MOTION_TILT_UNKNOWN,sequence,now);
}
void comp_runtime_motion_pose(comp_runtime_t *r, uint8_t events, uint8_t orientation,
    uint8_t tilt, uint32_t sequence, uint32_t now)
{
    if (!r || (r->motion_sequence_valid && sequence == r->last_motion_sequence)) return;
    r->motion_sequence_valid = true; r->last_motion_sequence = sequence;
    if(r->pet_play.phase && (events&(COMP_MOTION_PICKUP|COMP_MOTION_SHAKE|COMP_MOTION_CARRIED)))
        enter_home(r,now);
    /* OTA owns HOME too. It must not receive sensor-induced pet revisions,
     * a pickup wake, new entropy or a deferred response after it finishes. */
    if(r->status_packed&COMP_SCREEN_STATUS_UPDATING) {
        if(deferred_motion(r))r->deferred_pet_kind=COMP_RUNTIME_PET_INPUT_NONE;
        return;
    }
    if(events & COMP_MOTION_CARRY_ENDED) {
        r->orientation &= 7u;
        r->family_retry_ms=now;
    }
    if(events & COMP_MOTION_CARRIED) {
        if(deferred_motion(r))r->deferred_pet_kind=COMP_RUNTIME_PET_INPUT_NONE;
        r->orientation |= PET_MOTION_CARRIED;
        /* No new autonomous entropy request while this lease is held, so its
         * existing retry deadline can also bound loss of motion reports. */
        r->family_retry_ms=now+PET_MOTION_LEASE_MS;
        if(pet_motion_intent(r)) {
            /* Sustained carrying retires the old motion cue immediately.
             * It must not silence a later explicit head-pat/greeting or
             * replace a finger's current hold/follow. Functional audio is
             * untouched by the existing selective pet cancellation. */
            comp_audio_feedback_cancel_pet(&r->audio);
#if COMP_PET_PROCEDURAL
            if(r->surface==COMP_SCREEN_SURFACE_HOME && !record_busy(r) &&
               r->reaction_pending && r->reaction_route_count &&
               !r->touch_contact && !r->hold.active && !r->hold_enter_requested) {
                /* One silent original centre landing, after any actual
                 * in-flight image finishes. Keep deferred touch intent,
                 * family and accepted seed; do not wake, consume entropy,
                 * reset the panel, or advance a failed/stale completion. */
                comp_pet_behavior_idle(&r->pet,r->pet.seed);
                r->reaction_route[0]=r->affect.selected;
                r->reaction_route_count=0u;r->reaction_step=1u;
                r->reaction_pose_count=r->reaction_pose_phase=1u;
                r->reaction_due_ms=now;r->gaze_x=r->gaze_y=100u;
                ++r->reaction_generation;dirty(r);
            }
#endif
        }
    }
    if ((events & COMP_MOTION_ORIENTATION_CHANGED) && orientation >= 1u && orientation <= 6u) {
        r->orientation = (uint8_t)((r->orientation & PET_MOTION_CARRIED) | orientation);
        if(r->surface!=COMP_SCREEN_SURFACE_LOW_POWER)dirty(r);
    }
    if(pet_carried(r) || r->pet_play.phase)return;
    if(r->sleep_phase && r->surface==COMP_SCREEN_SURFACE_HOME && (events&COMP_MOTION_SHAKE)) {
        r->last_activity_ms=now;enter_home(r,now);
    }
    if (events & COMP_MOTION_PICKUP) comp_runtime_wake_from(r,now,COMP_RUNTIME_WAKE_PICKUP);
    /* Pickup already owns the wake phrase. Incidental tilt/settled reports
     * cannot replace its shared dwell deadline with a hidden reply. */
    if(r->sleep_phase)return;
    if (r->surface != COMP_SCREEN_SURFACE_HOME || record_busy(r)) return;
    const uint8_t response=motion_reply_events(r,events & (COMP_MOTION_PICKUP|COMP_MOTION_SHAKE|
        COMP_MOTION_SETTLED|COMP_MOTION_TILT_CHANGED),tilt);
    if(!response || ((response&COMP_MOTION_TILT_CHANGED) &&
       !(response&(COMP_MOTION_PICKUP|COMP_MOTION_SHAKE|COMP_MOTION_SETTLED)) &&
       tilt>COMP_MOTION_TILT_INVERTED))return;
    /* Explicit touch/holds and their pending tap own the interaction. Do not
     * store sensor movement behind them and surprise the user after release. */
    if(r->touch_contact || r->hold.active || r->hold_enter_requested ||
       r->taps.pending || r->deferred_pet_kind==COMP_RUNTIME_PET_INPUT_TAP ||
       r->deferred_pet_kind==COMP_RUNTIME_PET_INPUT_STROKE ||
       r->deferred_pet_kind==COMP_RUNTIME_PET_INPUT_FOLLOW)return;
    if(r->reaction_pending || deferred_motion(r)) {
        if(!r->reaction_route_count || pet_motion_intent(r))
            defer_motion(r,response,tilt,now);
        return;
    }
    begin_motion_reply(r,response,tilt,now,now,r->affect.selected);
}
void comp_runtime_service(comp_runtime_t *r, uint32_t now)
{
#if COMP_RUNTIME_VISUAL
    comp_touch_tap_arbiter_event_t tap;
#endif
    comp_audio_feedback_outcome_t outcome;
    if (!r) return;
    if(r->temporary_quiet_active) {
        const uint8_t remaining=temporary_quiet_minutes(r,now);
        const bool mode_changed=!r->menu_pending &&
            r->menu.browser.interaction_level!=r->temporary_quiet_base_level;
        if(!remaining || mode_changed) {
            r->temporary_quiet_active=false;r->temporary_quiet_last_minute=0u;
            /* End/start is a different visible intent. Fence a contact which
             * began on the previous timer state rather than restart it. */
            ++r->menu.revision;audio_settings(r);
            if(r->surface!=COMP_SCREEN_SURFACE_LOW_POWER)dirty(r);
        } else if(remaining!=r->temporary_quiet_last_minute) {
            r->temporary_quiet_last_minute=remaining;
            /* Refresh the visible remaining minute through the existing
             * transaction. No sleep wake or independent animation clock. */
            if(r->surface==COMP_SCREEN_SURFACE_HOME ||
               (r->surface==COMP_SCREEN_SURFACE_MENU &&
                r->menu.view==COMP_SCREEN_MENU_VIEW_BROWSER_QUICK))dirty(r);
        }
    }
#if COMP_RUNTIME_VISUAL
    /* A no-screen build has no touch, caption or visual reply producer.
     * Keep recording/audio/quiet/sleep below live, but do not retain the
     * entire deferred touch/reaction graph merely through this poller. */
    comp_pet_chat_service(r,now,record_busy(r) || r->menu_pending);
    if((r->record_saved_state==RECORD_NOTICE_SAVED_VISIBLE ||
        r->record_saved_state==RECORD_NOTICE_STOP_VISIBLE) && (int32_t)(now-r->record_saved_due_ms)>=0)
        r->record_saved_state=0u; /* Retire on the next normal frame, no timer-only refresh. */
    if(r->menu_deferred_swipe) {
        if(r->surface!=COMP_SCREEN_SURFACE_MENU || r->visible_surface!=COMP_SCREEN_SURFACE_MENU ||
           !r->visible_menu_valid || r->visible_menu_view!=r->menu.view ||
           record_busy(r) || r->menu_pending)r->menu_deferred_swipe=0u;
        else if(!r->frame_outstanding && visible_menu_matches(r)) {
            const comp_touch_gesture_event_t page={.type=r->menu_deferred_swipe==1u?
                COMP_TOUCH_GESTURE_SWIPE_UP:r->menu_deferred_swipe==2u?
                COMP_TOUCH_GESTURE_SWIPE_DOWN:COMP_TOUCH_GESTURE_SWIPE_RIGHT};
            r->menu_deferred_swipe=0u;
            const comp_screen_menu_t before=r->menu;
            const comp_screen_menu_result_t result=comp_screen_menu_gesture(&r->menu,&page);
            /* A boundary consumes the intent without a redundant refresh. */
            if((before.revision!=r->menu.revision || result.action!=COMP_SCREEN_MENU_ACTION_NONE) &&
               !menu_result(r,result,now,&before))r->menu=before;
        }
    }
#if COMP_RUNTIME_PET_MOTION
    if(r->pet_discovery_allowed && r->pet_discovery_visible &&
       (int32_t)(now-r->pet_discovery_due_ms)>=0)dismiss_discovery(r);
    if(r->pet_discovery_pending_save && !r->pet_discovery_allowed &&
       (int32_t)(now-r->pet_discovery_due_ms)>=0 &&
       r->surface==COMP_SCREEN_SURFACE_HOME && !record_busy(r) &&
       !r->frame_outstanding && !r->menu_pending && !r->touch_contact) {
        /* Internal action13 is a synchronous, readback-verified preference
         * effect. It is not a visible menu action and never opens a token or
         * substitutes a successful render for a successful storage commit. */
        const comp_screen_menu_result_t seen={.action=COMP_SCREEN_MENU_ACTION_PET_DISCOVERY_SEEN};
        const comp_runtime_menu_dispatch_t saved=r->config.menu_action_begin ?
            r->config.menu_action_begin(r->config.context,&seen,&r->menu,0u):COMP_RUNTIME_MENU_UNAVAILABLE;
        if(saved==COMP_RUNTIME_MENU_COMPLETE)
            r->pet_discovery_pending_save=false;
        else if(saved==COMP_RUNTIME_MENU_BUSY)r->pet_discovery_due_ms=now+5000u;
        else {
            ++r->pet_discovery_save_attempts;
            if(r->pet_discovery_save_attempts>=3u || saved==COMP_RUNTIME_MENU_UNAVAILABLE)
                r->pet_discovery_pending_save=false;
            else r->pet_discovery_due_ms=now+5000u;
        }
    }
#endif
    if(pet_carried(r) && (int32_t)(now-r->family_retry_ms)>=0)
        r->orientation &= 7u;
#endif
    /* A visible pet reply belongs to HOME. A later menu/sleep/recording
     * transition must not let its queued sound follow the user into that
     * different activity; keep functional confirmation/start/stop cues. */
    if (r->surface != COMP_SCREEN_SURFACE_HOME || record_busy(r))
        comp_audio_feedback_cancel_pet(&r->audio);
    comp_audio_feedback_service(&r->audio, now);

    if (r->prepare_pending) {
        const uint32_t prepare_elapsed=now-r->prepare_since_ms;
        if (prepare_elapsed<0x80000000u && prepare_elapsed>120000u) {
            (void)recording_request(r,false,0u,now,COMP_RECORD_STOP_PREPARE_TIMEOUT);
            (void)reject(r, COMP_RUNTIME_BACKEND_FAILED, now);
        } else if (r->config.recording_ready(r->config.context)) {
            comp_audio_feedback_submit_result_t result = comp_audio_feedback_submit(
                &r->audio, COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST, now);
            if (result == COMP_AUDIO_FEEDBACK_SUBMIT_ACCEPTED || result == COMP_AUDIO_FEEDBACK_SUBMIT_SUPPRESSED_QUIET) {
                r->prepare_pending = false; r->start_pending = true; dirty(r);
            }
        }
    }
    if (r->start_pending && comp_audio_feedback_take_recording_start_gate(&r->audio, &outcome)) {
        r->start_pending = false;
        if (!r->config.recording_ready(r->config.context)) {
            r->command_pending = false;
            r->record_stop_reason=COMP_RECORD_STOP_GATE_NOT_READY;
            if (r->config.recording_prepare) (void)r->config.recording_control(r->config.context, false, r->record_token);
            (void)reject(r, COMP_RUNTIME_UNAVAILABLE, now);
        }
        else {
            r->command_pending = true;
            /* Silence all ordinary cues while asynchronous capture startup runs. */
            if (!comp_audio_feedback_set_recording_active(&r->audio, true) ||
                !r->config.recording_control(r->config.context, true, r->record_token)) {
                r->command_pending = false;
                (void)comp_audio_feedback_set_recording_active(&r->audio, false);
                (void)reject(r, COMP_RUNTIME_BACKEND_FAILED, now);
            }
        }
        dirty(r);
    }
#if COMP_RUNTIME_VISUAL
    play_service(r,now);
    if (r->surface == COMP_SCREEN_SURFACE_HOME) comp_epaper_motion_coordinator_keep_awake(&r->life, now);
#endif
    /* control(true) can synchronously report a fresh HAL tick while this
     * service call still holds its earlier tick. A small future start must
     * not wrap into a 49-day duration and stop the capture immediately.
     * All supported recording limits are below the half-counter interval. */
    const uint32_t recording_delta = now - r->recording_since_ms;
    const uint32_t recording_elapsed = r->recording_capture_clock ? r->recording_captured_ms :
        recording_delta < 0x80000000u ? recording_delta : 0u;
    if (r->capture_active && recording_elapsed / 1000u != r->recording_display_second) {
        r->recording_display_second = recording_elapsed / 1000u;
#if COMPANION_WBA_RESOURCE_PROFILE
        /* Guarantee a pure-wave turn when the displayed timer changes.
         * Other accepted frames also compose the next wave phase, and the
         * idle recording fallback is not limited to one update per second. */
        r->recording_wave_due = true;
#endif
        dirty(r);
    }
#if COMP_RUNTIME_VISUAL
    if (comp_touch_tap_arbiter_poll(&r->taps, now, r->gesture.active,
        r->gesture.tap_pending && now - r->gesture.last_tap_ms <= r->gesture.config.double_tap_max_gap_ms, &tap))
        { react(r, tap.x, tap.y, now); }
    if (r->surface!=COMP_SCREEN_SURFACE_HOME || record_busy(r) ||
        (r->status_packed&COMP_SCREEN_STATUS_UPDATING))
        r->deferred_pet_kind=COMP_RUNTIME_PET_INPUT_NONE;
    else if(deferred_motion(r) && (pet_carried(r) || r->touch_contact ||
            r->hold.active || r->hold_enter_requested || r->taps.pending ||
            !motion_reply_events(r,(uint8_t)r->deferred_pet_x,(uint8_t)r->deferred_pet_y) ||
            now-r->deferred_pet_ms>PET_DEFERRED_MOTION_MAX_MS))
        r->deferred_pet_kind=COMP_RUNTIME_PET_INPUT_NONE;
    else if(r->deferred_pet_kind!=COMP_RUNTIME_PET_INPUT_NONE &&
            now-r->deferred_pet_ms>PET_DEFERRED_INTENT_MAX_MS)
        r->deferred_pet_kind=COMP_RUNTIME_PET_INPUT_NONE;
    else if(r->deferred_pet_kind==COMP_RUNTIME_PET_INPUT_FOLLOW &&
            (!r->touch_contact || !input_contact_ready(r) || !r->menu.browser.gaze_follow))
        r->deferred_pet_kind=COMP_RUNTIME_PET_INPUT_NONE;
    else if(deferred_motion(r) && !r->frame_outstanding &&
        !r->blink.open_pending && !r->blink.open_in_flight &&
        (!r->reaction_pending || (pet_motion_intent(r) &&
         motion_priority((uint8_t)r->deferred_pet_x)>active_motion_priority(r) &&
         (int32_t)(now-r->reaction_due_ms)>=0))) {
        const uint8_t tilt=(uint8_t)r->deferred_pet_y;
        const uint8_t events=motion_reply_events(r,(uint8_t)r->deferred_pet_x,tilt);
        const uint32_t observed_ms=r->deferred_pet_ms;
        /* This safe beat boundary follows a successful released transaction.
         * A deliberate shake may replace a pickup/posture after its readable
         * hold; repeated same-priority reports never restart the phrase. */
        const comp_browser_family_t before=r->reaction_pending && r->visible_frames &&
            r->visible_surface==COMP_SCREEN_SURFACE_HOME?r->in_flight.family:r->affect.selected;
        r->deferred_pet_kind=COMP_RUNTIME_PET_INPUT_NONE;
        begin_motion_reply(r,events,tilt,observed_ms,now,before);
    }
    else if (r->deferred_pet_kind!=COMP_RUNTIME_PET_INPUT_NONE && !deferred_motion(r) &&
        !r->reaction_pending && !r->frame_outstanding && !r->hold_enter_requested &&
        (r->deferred_pet_kind==COMP_RUNTIME_PET_INPUT_FOLLOW ||
         (r->deferred_pet_kind==COMP_RUNTIME_PET_INPUT_STROKE && !r->hold.active) ||
         (!r->touch_contact && !r->hold.active))) {
        /* The quiet pause belongs to autonomous life, not an explicit input.
         * begin_reply still keeps the interaction cooldown; a recognized
         * one-per-contact stroke can answer before that finger is released. */
        uint16_t x=r->deferred_pet_x,y=r->deferred_pet_y;
        uint8_t kind=r->deferred_pet_kind;
        r->deferred_pet_kind=COMP_RUNTIME_PET_INPUT_NONE;
        if(kind==COMP_RUNTIME_PET_INPUT_FOLLOW)gaze_reply(r,x,y,false,now);
        else if(kind==COMP_RUNTIME_PET_INPUT_STROKE)stroke_reply(r,x,(comp_browser_tap_zone_t)y,now);
        else react(r,x,y,now);
    }
#endif
    if (r->capture_active && !r->stop_pending &&
        r->record_limit_seconds != 0u &&
        recording_elapsed >= r->record_limit_seconds*1000u)
        (void)recording_request(r,false,0u,now,COMP_RECORD_STOP_DURATION_LIMIT);
    if (!r->sleep_phase && r->surface != COMP_SCREEN_SURFACE_LOW_POWER && !record_busy(r) && !r->touch_contact &&
        r->menu.browser.auto_sleep_minutes != 0u &&
        now - r->last_activity_ms >= (uint32_t)r->menu.browser.auto_sleep_minutes * 60000u) sleep_now(r,now);
}
static void autonomous_family(comp_runtime_t *r,uint32_t now)
{
#if COMP_PET_PROCEDURAL
    const bool quiet=effective_interaction_level(r)==COMP_SCREEN_MENU_INTERACTION_QUIET &&
        !record_busy(r);
    /* Quiet company does not pose an unsolicited question. Retire an idle
     * question only at the existing scene boundary; deliberate gaze, pickup
     * and accepted replies keep their original family and visible interval. */
    const bool quiet_question=quiet && r->affect.selected==COMP_BROWSER_FAMILY_CURIOUS &&
        r->pet.interaction==COMP_PET_IDLE;
#else
    const bool quiet_question=false;
#endif
#if !COMP_PET_PROCEDURAL
    static const uint8_t idle_families[]={COMP_BROWSER_FAMILY_CALM,COMP_BROWSER_FAMILY_CURIOUS,
        COMP_BROWSER_FAMILY_DELIGHTED,COMP_BROWSER_FAMILY_WARM,COMP_BROWSER_FAMILY_PLAYFUL};
    uint8_t pool[sizeof(idle_families)],count=0;
#endif
    uint32_t entropy;
    /* Recording owns its accessory clock, not the pet's autonomous emotion.
     * Keep the accepted daily family/dwell sequence alive during capture. */
    if (pet_carried(r) || !r->config.random_u32 || r->touch_contact || r->reaction_pending ||
        r->blink.open_pending || r->blink.open_in_flight || r->life.request_outstanding ||
        r->life.action!=COMP_EPAPER_MOTION_ACTION_REST || r->life.next_phase!=COMP_EPAPER_MOTION_PHASE_HOLD ||
        !comp_epaper_motion_coordinator_scene_boundary(&r->life) ||
#if COMP_PET_PROCEDURAL
        /* Every mode owns its already-selected landing pause. An overdue
         * daily mood must not replace the reply immediately after it lands. */
        ((int32_t)(now-r->life.next_request_ms)<0) ||
#endif
        (!quiet_question && (int32_t)(now-r->family_due_ms)<0) ||
        (int32_t)(now-r->family_retry_ms)<0) return;
    if (!r->config.random_u32(r->config.context,&entropy)) { r->family_retry_ms=now+500u; return; }
    r->family_due_ms=now+28000u+((entropy>>8)%17u)*1000u;
#if COMP_PET_PROCEDURAL
    r->family_due_ms=now+comp_pet_behavior_personal_gap(&r->pet,r->family_due_ms-now);
    comp_browser_family_t next=comp_pet_behavior_personal_idle(&r->pet,r->affect.selected,entropy);
    if(quiet && next==COMP_BROWSER_FAMILY_CURIOUS)next=COMP_BROWSER_FAMILY_CALM;
    /* The friendly random pool deliberately excludes sleepy. Give the
     * existing sleepy/breath/yawn assets an honest context instead: the last
     * 45s before the user's existing auto-sleep deadline, at this natural
     * scene boundary only. No extra frame, timer, wake or power transition;
     * capture/OTA never acquire a made-up sleepy mood. */
    const uint32_t sleep_after=(uint32_t)r->menu.browser.auto_sleep_minutes*60000u;
    const uint32_t idle=now-r->last_activity_ms;
    if(!record_busy(r) && !(r->status_packed&COMP_SCREEN_STATUS_UPDATING) &&
       sleep_after>=60000u && idle>=sleep_after-45000u && idle<sleep_after)
        next=COMP_BROWSER_FAMILY_SLEEPY;
    /* Staying in this mood must not reset its action history, regenerate the
     * face seed or request a cleanup. The existing story carries on. */
    if(next==r->affect.selected)return;
    r->affect.selected=next;
#else
    /* Idle keeps a companionable mood. The whole expression vocabulary
     * remains available to deliberate interactions and product states. */
    for (uint8_t i=0;i<sizeof(idle_families);++i)
        if (idle_families[i]!=(uint8_t)r->affect.selected) pool[count++]=idle_families[i];
    r->affect.selected=(comp_browser_family_t)pool[entropy%count];
#endif
#if COMP_RUNTIME_PET_MOTION
    r->pet_variant=(uint8_t)((r->pet_variant+1u+(entropy>>16)%2u)%3u);
#if COMP_PET_PROCEDURAL
    comp_pet_behavior_idle(&r->pet,entropy);
#endif
#endif
    enter_pet_daily(r,now,r->affect.selected);
    r->family_clean=true; ++r->autonomous_family_changes;
}
static void startup_variation(comp_runtime_t *r,uint32_t now)
{
#if COMP_RUNTIME_PET_MOTION
    uint32_t value;
    if(pet_carried(r) || !r->pet_startup_pending || !r->config.random_u32 || record_busy(r) ||
        r->surface!=COMP_SCREEN_SURFACE_HOME || r->touch_contact || r->reaction_pending ||
        r->blink.open_pending || r->life.request_outstanding ||
        r->life.action!=COMP_EPAPER_MOTION_ACTION_REST ||
        (int32_t)(now-r->family_retry_ms)<0)return;
    if(!r->config.random_u32(r->config.context,&value)) {r->family_retry_ms=now+500u;return;}
    static const uint8_t welcome[]={COMP_BROWSER_FAMILY_CALM,COMP_BROWSER_FAMILY_CALM,
        COMP_BROWSER_FAMILY_CURIOUS,COMP_BROWSER_FAMILY_WARM,COMP_BROWSER_FAMILY_DELIGHTED};
    r->affect.selected=(comp_browser_family_t)welcome[value%sizeof(welcome)];
    r->pet_variant=(uint8_t)((value>>8)%3u);r->reaction_variant=(uint8_t)(value>>16);
#if COMP_PET_PROCEDURAL
    comp_pet_behavior_idle(&r->pet,value);
#endif
    r->pet_startup_pending=false;
    enter_home(r,now);
    r->family_due_ms=now+28000u+((value>>24)%17u)*1000u;
#else
    (void)r;(void)now;
#endif
}
static bool take_due_pet_frame(comp_runtime_t *r, uint32_t now,
                               comp_runtime_frame_t *frame)
{
    if(r->pet_play.phase)return false;
    comp_epaper_natural_blink_phase_t blink_phase;
    autonomous_family(r,now);
    r->blink_before_frame=r->blink;
    if (!pet_carried(r) && !r->reaction_pending && r->menu.browser.natural_blink &&
        comp_epaper_natural_blink_take_due(&r->blink,now,&blink_phase)) {
        frame->kind=COMP_RUNTIME_FRAME_BLINK;
        frame->blink_closed=blink_phase==COMP_EPAPER_NATURAL_BLINK_CLOSED;
        return true;
    }
    /* Let an accepted phrase land before withholding the next idle action.
     * Pending eye-open completions are handled by the existing take_frame gate. */
    if ((!pet_carried(r) || r->life.action!=COMP_EPAPER_MOTION_ACTION_REST) && !r->reaction_pending &&
        comp_epaper_motion_coordinator_take_request(&r->life,now,&frame->motion)) {
        frame->kind=COMP_RUNTIME_FRAME_LIFE;
        return true;
    }
    return false;
}

bool comp_runtime_take_frame(comp_runtime_t *r, uint32_t now, comp_runtime_frame_t *frame)
{
    comp_runtime_frame_t f = {0};
    comp_browser_menu_hold_event_t held;
    comp_epaper_natural_blink_phase_t blink_phase;
    if (!r || !frame || r->frame_outstanding ||
        r->chat_caption_state==COMP_PET_CHAT_ASSEMBLING ||
        r->chat_caption_state==COMP_PET_CHAT_RESERVING ||
        (int32_t)(now - r->retry_display_ms) < 0) return false;
    const bool updating=(r->status_packed&COMP_SCREEN_STATUS_UPDATING) && !record_busy(r);
    if(!updating && !r->sleep_phase)startup_variation(r,now);
    f.kind = COMP_RUNTIME_FRAME_STATUS;
    if(r->sleep_phase && !updating && !record_busy(r)) {
        if((int32_t)(now-r->reaction_due_ms)<0)return false;
        f.kind=COMP_RUNTIME_FRAME_SLEEP;
        f.sleep_phase=r->sleep_phase;
    } else if(updating) {
        if(r->visible_revision==r->revision)return false;
    } else
    /* Finish an already visible blink before replacing any eye geometry. */
    if (r->surface==COMP_SCREEN_SURFACE_HOME && r->blink.open_pending &&
        (int32_t)(now-r->blink.next_due_ms)>=0) {
        r->blink_before_frame=r->blink;
        if (!comp_epaper_natural_blink_take_due(&r->blink,now,&blink_phase)) return false;
        f.kind=COMP_RUNTIME_FRAME_BLINK; f.blink_closed=false;
    } else if (r->surface == COMP_SCREEN_SURFACE_HOME && r->hold.active &&
        comp_browser_menu_hold_next(&r->hold,
            r->hold_enter_requested?UINT32_MAX:now-r->gesture.start_ms,&held) &&
        (held.bucket+1u<COMPANION_BROWSER_INTERACTION_MENU_HOLD_MILESTONE_COUNT || r->hold_enter_requested)) {
        /* A full indicator promises an accepted gesture. Elapsed display
         * time alone must not fill it while touch recognition is absent. */
        f.kind = COMP_RUNTIME_FRAME_HOLD; f.hold_bucket = held.bucket;
    } else if (r->surface == COMP_SCREEN_SURFACE_HOME && r->capture_active &&
               r->recording_wave_due) {
        /* Preserve the accepted WB fairness rule: a slow BUSY can leave life
         * continuously overdue. Give wave one pure slot before another face
         * request; only a due blink-open/hold may finish first. Never advance
         * the life deadline, blink table, or family on this wave commit. */
        f.kind = COMP_RUNTIME_FRAME_RECORDING_WAVE;
    } else if (r->surface == COMP_SCREEN_SURFACE_HOME && r->blink.open_pending) {
        /* The eyelid owns its whole visible interval. Status and recording
         * may continue, but a life/reaction pose waits for the authored open. */
        if (r->visible_revision != r->revision) f.kind = COMP_RUNTIME_FRAME_STATUS;
        else if (r->capture_active) f.kind = COMP_RUNTIME_FRAME_RECORDING_WAVE;
        else return false;
    } else if (r->visible_revision != r->revision &&
               (r->surface != COMP_SCREEN_SURFACE_HOME || !r->capture_active || r->reaction_pending)) {
        /* During capture every composed wave/life/blink frame already paints
         * the latest timer/status. Spending a separate status slot each
         * second can starve life forever on a 500 ms or slower panel. */
        if (reaction_ready(r,now)) f.kind = COMP_RUNTIME_FRAME_REACTION;
        else if (r->surface==COMP_SCREEN_SURFACE_HOME && r->visible_frames!=0u &&
                 r->visible_surface==COMP_SCREEN_SURFACE_HOME &&
                 !record_busy(r) && !r->touch_contact && !r->reaction_pending &&
                 !r->menu_pending) {
            /* A due idle pose already carries the current status/revision.
             * Compose both in one transaction instead of activating a status
             * frame immediately before an overdue pet frame. Do not wait for
             * a future pose, advance a timer, or consume another random seed.
             * Wake/page changes, input and recording retain their own slots. */
            (void)take_due_pet_frame(r,now,&f);
        }
    } else if (r->surface == COMP_SCREEN_SURFACE_HOME && reaction_ready(r,now)) {
        f.kind = COMP_RUNTIME_FRAME_REACTION;
    } else if (r->surface == COMP_SCREEN_SURFACE_HOME && !r->touch_contact) {
        if (take_due_pet_frame(r,now,&f)) { /* Same authored idle selection. */ }
        else if (r->capture_active) f.kind=COMP_RUNTIME_FRAME_RECORDING_WAVE;
        else return false;
    } else if (r->surface == COMP_SCREEN_SURFACE_HOME && r->capture_active) {
        /* A resting finger still belongs to the recording gesture recognizer;
         * it must not throttle the independent mic/wave to timer ticks. Keep
         * HOME pet reactions suppressed, without adding any refresh clock or
         * bypassing the existing in-flight/retry/capture admission above. */
        f.kind=COMP_RUNTIME_FRAME_RECORDING_WAVE;
    } else return false;
#if COMP_PET_PROCEDURAL
    if(f.kind==COMP_RUNTIME_FRAME_REACTION && r->reaction_route_count && !r->reaction_step &&
       r->pet.interaction>=COMP_PET_HEAD_PAT && r->pet.interaction<=COMP_PET_CHIN &&
       !r->pet_play.phase && r->visible_frames && !r->display_failure_streak &&
       r->visible_surface==COMP_SCREEN_SURFACE_HOME &&
       r->in_flight.kind==COMP_RUNTIME_FRAME_REACTION && !r->in_flight.reaction_reply &&
       r->in_flight.surface==COMP_SCREEN_SURFACE_HOME && !r->in_flight.blink_closed &&
       r->in_flight.family==r->reaction_route[0] &&
       comp_pet_gaze_grid(r->in_flight.gaze_x)==comp_pet_gaze_grid(r->gaze_x) &&
       comp_pet_gaze_grid(r->in_flight.gaze_y)==comp_pet_gaze_grid(r->gaze_y) &&
       r->retry_display_ms-r->gesture.start_ms<=now-r->gesture.start_ms) {
        /* This contact's matching glance has already completed visibly,
         * sometimes while the tap arbiter was still resolving release.
         * Reuse that qualified beat instead of refreshing it a second time.
         * Failed/old/closed-eye frames and motion intentions cannot qualify. */
        r->reaction_pose_count=reply_pose_count(r,r->retry_display_ms-r->frame_requested_ms);
        r->reaction_pose_phase=r->reaction_pose_count==3u?0u:1u;
        r->reaction_step=1u;
    }
#endif
    if (++r->next_token == 0u) ++r->next_token;
    f.token = r->next_token; f.revision = r->revision; f.surface = r->surface;
    if (f.kind != COMP_RUNTIME_FRAME_BLINK)
        f.blink_closed = r->surface == COMP_SCREEN_SURFACE_HOME && r->blink.open_pending;
    f.family = r->affect.selected; f.menu = r->menu; f.recording = r->recording;
    f.temporary_quiet_minutes=temporary_quiet_minutes(r,now);
    f.record_stop_reason=r->record_stop_reason<=COMP_RECORD_STOP_STORAGE_FULL?r->record_stop_reason:COMP_RECORD_STOP_NONE;
    f.start_pending = r->start_pending || r->command_pending;
    f.prepare_pending = r->prepare_pending;
    /* Original recording UI: no touch HOLD control or invisible lock. */
    f.recording_input_locked=false;
    f.recording_hold_control=false;
    f.recording_paused=r->recording==DENZIC_AUDIO_RECORDING_STATE_RECORDING &&
        !r->capture_active && !r->start_pending && !r->command_pending && !r->prepare_pending;
    f.record_saved_notice=r->record_saved_state && r->record_saved_state<=RECORD_NOTICE_SAVED_VISIBLE &&
        f.surface==COMP_SCREEN_SURFACE_HOME &&
        !record_busy(r) && !r->sleep_phase && !r->hold.active && !r->pet_play.phase &&
        r->chat_caption_state!=COMP_PET_CHAT_ASSEMBLING &&
        r->chat_caption_state!=COMP_PET_CHAT_RESERVING &&
        r->chat_caption_state!=COMP_PET_CHAT_PENDING && r->chat_caption_state!=COMP_PET_CHAT_VISIBLE &&
        !(r->status_packed&COMP_SCREEN_STATUS_UPDATING);
    f.last_result = current_ui_result(r); f.connected = r->connected;
    f.menu_feedback = r->surface==COMP_SCREEN_SURFACE_MENU && menu_context(r)==r->menu_feedback_context?
        r->menu_feedback:COMP_RUNTIME_MENU_FEEDBACK_NONE;
    f.gaze_x = r->menu.browser.gaze_follow ? r->gaze_x : 100u;
    f.gaze_y = r->menu.browser.gaze_follow ? r->gaze_y : 100u;
    if(r->pet_play.phase==COMP_PET_PLAY_NEXT || r->pet_play.phase==COMP_PET_PLAY_ORIENT ||
       r->pet_play.phase==COMP_PET_PLAY_AIM) {
        f.gaze_x=f.gaze_y=100u;
        f.family=COMP_BROWSER_FAMILY_CALM;
        if(!r->hold.active)f.pet_play_caption=COMP_PET_PLAY_CAPTION_NEXT;
    }
    else if(r->pet_play.phase==COMP_PET_PLAY_CUE || r->pet_play.phase==COMP_PET_PLAY_WAIT) {
        /* A deliberate activity cue remains directional even when passive
         * finger-follow is disabled. Status retains the same shown face. */
        f.gaze_x=comp_pet_play_target_x(&r->pet_play);
        f.gaze_y=comp_pet_play_target_y(&r->pet_play);
        f.family=COMP_BROWSER_FAMILY_CALM;
        if(!r->hold.active)f.pet_play_caption=r->pet_play.retry_hint?
            COMP_PET_PLAY_CAPTION_RETRY:COMP_PET_PLAY_CAPTION_CUE;
    }
    else if(r->pet_play.phase==COMP_PET_PLAY_REPLY && !r->hold.active)
        f.pet_play_caption=COMP_PET_PLAY_CAPTION_FOUND;
    else if(r->pet_play.phase==COMP_PET_PLAY_ENDED && !r->hold.active)
        f.pet_play_caption=COMP_PET_PLAY_CAPTION_ENDED;
    if(!r->reaction_route_count &&
       ((r->touch_contact && input_contact_ready(r)) ||
        (r->reaction_pending && r->reaction_step==1u && f.kind!=COMP_RUNTIME_FRAME_REACTION)))
        f.family=r->reaction_route[0];
    if(f.kind==COMP_RUNTIME_FRAME_REACTION && !r->reaction_route_count && r->reaction_step==1u)
        f.gaze_x=f.gaze_y=100u;
    f.orientation = r->orientation & 7u;
    f.pet_variant=r->pet_variant;
#if COMP_PET_PROCEDURAL
    if(f.kind==COMP_RUNTIME_FRAME_LIFE && f.motion.action!=COMP_EPAPER_MOTION_ACTION_REST) {
        uint32_t key=f.motion.episode*131u+(uint32_t)f.motion.family*4099u+
            (COMP_RUNTIME_PET_MOTION?0u:(uint32_t)f.motion.action*17u);
        /* A physical scene may contain two original actions, but shares one
         * accepted cosmetic seed throughout. Failed phases and the second
         * action keep that seed; only a new scene may choose a new variant. */
        if(key!=r->pet.life_key) {
            uint32_t value;
            if(r->config.random_u32 && r->config.random_u32(r->config.context,&value))
                comp_pet_behavior_idle(&r->pet,value);
            r->pet.life_key=key;
        }
    }
    f.pet_seed=r->pet.seed;f.pet_interaction=r->pet.interaction;f.pet_intensity=r->pet.intensity;
    f.pet_accent=r->pet.accent;
#endif
    if(f.kind==COMP_RUNTIME_FRAME_HOLD)f.hold_generation=r->hold_generation;
    else f.recording_token=r->record_token;
    if (r->capture_active && f.surface==COMP_SCREEN_SURFACE_HOME &&
        f.recording==DENZIC_AUDIO_RECORDING_STATE_RECORDING && f.kind!=COMP_RUNTIME_FRAME_HOLD) {
        /* Each existing visible slot may carry the next original wave phase.
         * Life/blink/clock keep their own cadence: do not spend a second
         * transaction solely because that slot also changed the face. */
        if (!r->recording_wave_started) f.recording_wave_index=0u;
        else if (r->recording_wave_index<3u)
            f.recording_wave_index=(uint8_t)(r->recording_wave_index+1u);
        else if(r->recording_wave_index==3u)f.recording_wave_index=4u;
        /* The retained bank has sixty subtly different loop phases. One
         * adjacent phase per captured second looked nearly static for a
         * minute. Sample five distinct phases on the same existing second
         * clock; failed transactions still do not advance this index. */
        else f.recording_wave_index=(uint8_t)(4u+(r->recording_wave_index-4u+12u)%60u);
    } else f.recording_wave_index=r->recording_wave_index;
    /* Do not turn a recording-time family boundary into a full-frame Mode-2
     * cleanup. Keep it pending until recording has finished. */
    f.family_clean=r->family_clean && !record_busy(r) && f.surface==COMP_SCREEN_SURFACE_HOME &&
        (f.kind==COMP_RUNTIME_FRAME_LIFE || f.kind==COMP_RUNTIME_FRAME_REACTION);
    f.reaction_generation=r->reaction_generation;
    f.reaction_zone=r->reaction_zone; f.reaction_step=r->reaction_step;
    f.reaction_pose_phase=r->reaction_pose_phase;
    if (r->reaction_pending && r->reaction_route_count>=1u && r->reaction_route_count<=2u) {
        f.reaction_reply=true;
        /* Status updates retain the already visible beat during its hold. */
        if (f.kind!=COMP_RUNTIME_FRAME_REACTION && f.reaction_step) {
            if(r->reaction_pose_count==3u && f.reaction_pose_phase>0u)--f.reaction_pose_phase;
            else {--f.reaction_step;f.reaction_pose_phase=r->reaction_pose_count==3u?2u:1u;}
        }
        if (f.reaction_step<=r->reaction_route_count) f.family=r->reaction_route[f.reaction_step];
        f.reaction_expression=f.reaction_step>=1u && f.reaction_step<=r->reaction_route_count;
#if COMP_PET_PROCEDURAL
        if(f.reaction_expression) {
            f.reaction_from=(uint8_t)r->reaction_route[f.reaction_step-1u];
            f.reaction_to=(uint8_t)(f.reaction_step<r->reaction_route_count?
                r->reaction_route[f.reaction_step+1u]:
                ((r->pet.interaction>=COMP_PET_HEAD_PAT && r->pet.interaction<=COMP_PET_CHIN) ||
                 r->pet.interaction==COMP_PET_GREETING || pet_handling_intent(r))?r->reaction_route[r->reaction_route_count]:r->affect.selected);
        } else if(f.reaction_step>0u) {
            /* The last genuinely visible affectionate peak owns this landing.
             * Return in that whole feeling instead of flashing the pre-touch
             * daily question face. Failed peaks never earn this family. */
            if(pet_handling_intent(r))
                f.family=r->reaction_route[r->reaction_route_count];
            else if((r->pet.interaction>=COMP_PET_HEAD_PAT && r->pet.interaction<=COMP_PET_CHIN) ||
                    r->pet.interaction==COMP_PET_GREETING)
                f.family=comp_pet_behavior_attention_family(&r->pet,f.family,now);
            f.reaction_from=(uint8_t)r->reaction_route[r->reaction_route_count];
            f.reaction_to=(uint8_t)f.family;
        }
#endif
        if (f.reaction_step==2u && r->reaction_route_count==2u) f.reaction_zone=r->reaction_after_zone;
        if (f.reaction_step) {
            if(r->touch_contact && input_contact_ready(r) && r->menu.browser.gaze_follow &&
               !r->hold_enter_requested) {
                if(r->deferred_pet_kind==COMP_RUNTIME_PET_INPUT_FOLLOW &&
                   now-r->deferred_pet_ms<=PET_DEFERRED_INTENT_MAX_MS) {
                    f.gaze_x=r->deferred_pet_x;f.gaze_y=r->deferred_pet_y;
                }
                /* Land in a directional version of the same original feeling.
                 * Closed expressive poses keep their authored eyelids. */
                if(!f.reaction_expression)
                    f.family=r->reaction_route[r->reaction_route_count];
            } else if((r->pet.interaction!=COMP_PET_TILT &&
                       r->pet.interaction!=COMP_PET_PICKUP) || !f.reaction_expression)
                /* Pickup and tilt acknowledge a spatial input. Keep that
                 * accepted direction through the existing expressive hold;
                 * the ordinary return still centres it. Otherwise a warm
                 * pickup glances up once then becomes an unrelated smile. */
                f.gaze_x=f.gaze_y=100u;
        }
    }
    if(f.kind==COMP_RUNTIME_FRAME_SLEEP) {
        f.family=f.sleep_phase<=COMP_RUNTIME_SLEEP_PARK?COMP_BROWSER_FAMILY_SLEEPY:COMP_BROWSER_FAMILY_CALM;
        f.gaze_x=f.gaze_y=100u;
        f.blink_closed=false;f.reaction_reply=false;f.reaction_expression=false;
        f.pet_accent=COMP_PET_ACCENT_NONE;
    }
    f.status_packed = (r->status_packed & ~COMP_SCREEN_STATUS_BATTERY_FILL_ONLY) |
        COMP_SCREEN_STATUS_REQUIRE_MEASURED_BATTERY |
        (r->menu.browser.battery_fill ? COMP_SCREEN_STATUS_BATTERY_FILL_ONLY : 0u) |
        (r->connected ? (1u << 16) : 0u);
    f.battery_mv = r->battery_mv;
    f.speaker_ornament=false;
    f.pet_sound_suppressed=r->audio.quiet || (r->config.speaker &&
        (r->config.speaker->muted || r->config.speaker->volume_percent==0u));
#if COMP_RUNTIME_PET_MOTION
    f.discovery_hint=!r->sleep_phase && r->pet_discovery_allowed && f.surface==COMP_SCREEN_SURFACE_HOME &&
        !record_busy(r) && !r->touch_contact && !r->reaction_pending &&
        !r->hold.active && !r->audio.quiet && current_ui_result(r)==COMP_RUNTIME_OK;
#endif
    /* Snapshot the active owner's union member. A stopped recording's old
     * seconds must not become the OTA phase/percent or its ready expression. */
    if(updating)f.update_display=r->update_display;
    else f.recording_elapsed_seconds = r->recording_display_second;
    if(updating) {
        f.family=(f.update_display&255u)==COMP_RUNTIME_UPDATE_READY?
            COMP_BROWSER_FAMILY_WARM:COMP_BROWSER_FAMILY_THOUGHTFUL;
        f.gaze_x=f.gaze_y=100u;f.blink_closed=false;
        f.reaction_reply=false;f.reaction_expression=false;f.discovery_hint=false;
    }
    if(!updating && f.surface==COMP_SCREEN_SURFACE_HOME && r->capture_active &&
       f.recording==DENZIC_AUDIO_RECORDING_STATE_RECORDING && !r->stop_pending &&
       r->record_saved_state>=RECORD_NOTICE_STOP_PENDING)
        f.pet_play_caption=COMP_PET_PLAY_CAPTION_RECORD_STOP;
#if COMP_PET_PROCEDURAL
    f.pet_caption=r->pet.caption_selected && f.surface==COMP_SCREEN_SURFACE_HOME &&
        f.reaction_reply && f.reaction_expression && f.reaction_step==1u &&
        f.reaction_pose_phase==1u &&
        !record_busy(r) && !updating && !r->pet_play.phase && f.last_result==COMP_RUNTIME_OK &&
        comp_pet_caption_slot((unsigned)f.family,f.reaction_zone)!=UINT8_MAX;
#endif
    if(!r->sleep_phase && f.surface==COMP_SCREEN_SURFACE_HOME && !record_busy(r) && !updating &&
       !r->pet_play.phase && (r->chat_caption_state==COMP_PET_CHAT_PENDING ||
                            r->chat_caption_state==COMP_PET_CHAT_VISIBLE)) {
        f.chat_caption_token=r->chat_caption_token;
        f.pet_caption=false;f.discovery_hint=false;
    }
    if(f.record_saved_notice) { f.pet_caption=false;f.discovery_hint=false; }
    r->frame_requested_ms=now;
    r->in_flight = f; r->frame_outstanding = true; *frame = f;
    return true;
}
bool comp_runtime_complete_frame(comp_runtime_t *r, uint32_t token, bool visible, uint32_t now)
{
    return comp_runtime_complete_frame_timed(r, token, visible, now, now);
}
bool comp_runtime_complete_frame_timed(comp_runtime_t *r, uint32_t token, bool visible,
                                      uint32_t now, uint32_t visible_ms)
{
    return comp_runtime_complete_frame_observed(r,token,visible,now,visible_ms,true);
}
bool comp_runtime_complete_frame_observed(comp_runtime_t *r,uint32_t token,bool visible,
                                      uint32_t now,uint32_t visible_ms,bool activated)
{
    comp_runtime_frame_t *f;
    if (!r) return false;
    if (!r->frame_outstanding || r->in_flight.token != token) { ++r->stale_completions; return false; }
    /* Accept only a visibility time within this request's wrapping interval.
     * Failures/retries/input/audio retain the actual completion time. */
    if (!visible || now - visible_ms > now - r->frame_requested_ms) visible_ms = now;
    f = &r->in_flight; r->frame_outstanding = false;
    r->last_display_activated=visible && activated;
    comp_pet_chat_complete(r,f,visible,visible_ms);
    bool life_completed=false;
    if (f->kind == COMP_RUNTIME_FRAME_LIFE) {
        if (COMP_RUNTIME_PET_MOTION)
            life_completed=comp_epaper_motion_coordinator_complete_request_timed(
                &r->life, f->motion.token, now, visible,
                r->frame_requested_ms, visible_ms);
        else
            life_completed=comp_epaper_motion_coordinator_complete_request(
                &r->life, f->motion.token, now, visible);
    }
    /* Only take_frame can arm these blink flags, and there is one frame in
     * flight. A cancel/re-entry clears both; an old failure must not restore
     * its saved scheduler into a new HOME session. A new gaze intent alone
     * does not cancel the eye-open completion of the same visible blink. */
    if (f->kind == COMP_RUNTIME_FRAME_BLINK && r->surface == f->surface &&
        r->blink.awake && (f->blink_closed?r->blink.open_pending:r->blink.open_in_flight)) {
        if (!visible) r->blink = r->blink_before_frame;
        else if (!f->blink_closed) (void)comp_epaper_natural_blink_complete_open(&r->blink, visible_ms);
    }
    if (!visible) {
        if(r->pet_play.phase)enter_home(r,now);
        if(deferred_motion(r))r->deferred_pet_kind=COMP_RUNTIME_PET_INPUT_NONE;
        r->menu_deferred_swipe=0u;
        /* A failed e-paper update may leave an unknown partial image.  Menu
         * coordinates are unsafe until the exact page is committed again. */
        if (f->surface == COMP_SCREEN_SURFACE_MENU) r->visible_menu_valid = false;
        ++r->failed_frames;
        if (r->display_failure_streak < DISPLAY_FAILURE_STREAK_LIMIT)
            ++r->display_failure_streak;
        /* Keep the original two prompt retries for a transient failure.
         * Persistent failure backs off to 15.36s instead of repeatedly
         * resetting/full-refreshing an unresponsive panel. Do not advance
         * choreography or commit any failed image during the quiet gap. */
        const uint8_t shift = r->display_failure_streak > DISPLAY_FAST_RETRIES
            ? (uint8_t)(r->display_failure_streak - DISPLAY_FAST_RETRIES) : 0u;
        r->retry_display_ms = now + (DISPLAY_RETRY_MS << shift);
        return true;
    }
    r->display_failure_streak = 0u;
    r->retry_display_ms = now;
    ++r->visible_frames;
#if COMP_PET_PROCEDURAL
    if(f->pet_caption && f->reaction_generation==r->reaction_generation)
        comp_pet_behavior_caption_visible(&r->pet,visible_ms);
#endif
    if(f->discovery_hint && !r->pet_discovery_visible) {
        /* The dwell begins only at the qualified optical completion. A hint
         * skipped during its in-flight first frame is persisted only if that
         * exact frame eventually succeeds; a failure cannot mark it seen. */
        r->pet_discovery_visible=true;
        r->pet_discovery_due_ms=visible_ms+6000u;
        if(!r->pet_discovery_allowed)r->pet_discovery_pending_save=true;
    }
    if(f->record_saved_notice && f->recording_token==r->record_token &&
       r->record_saved_state==1u) {
        r->record_saved_state=2u;r->record_saved_due_ms=visible_ms+8000u;
    }
    if(f->pet_play_caption==COMP_PET_PLAY_CAPTION_RECORD_STOP &&
       f->recording_token==r->record_token && r->record_saved_state==RECORD_NOTICE_STOP_PENDING) {
        r->record_saved_state=RECORD_NOTICE_STOP_VISIBLE;r->record_saved_due_ms=visible_ms+8000u;
    }
    if(COMP_RUNTIME_PET_MOTION && life_completed && f->kind==COMP_RUNTIME_FRAME_LIFE &&
       f->motion.phase==COMP_EPAPER_MOTION_PHASE_SETTLE &&
        (r->life.action==COMP_EPAPER_MOTION_ACTION_REST ||
         effective_interaction_level(r)==COMP_SCREEN_MENU_INTERACTION_QUIET) &&
       r->surface==COMP_SCREEN_SURFACE_HOME && !record_busy(r) &&
       !r->touch_contact && !r->reaction_pending) {
        /* Let a completed little story rest. Its already accepted entropy
         * varies the pause without reselecting art, advancing a failed beat,
         * adding a timer refresh, or changing capture-time choreography. */
        const unsigned level=effective_interaction_level(r);
        /* Interaction degree changes a completed story's quiet pause, never
         * the panel deadline or intermediate poses. Standard stays unchanged;
         * even lively retains a readable rest after each whole intention. */
        uint32_t due=visible_ms+2400u+(level==COMP_SCREEN_MENU_INTERACTION_LIVELY?
            ((r->pet.seed>>17u)%5u)*300u:((r->pet.seed>>17u)%9u)*400u);
        /* Quiet lets each completed action settle before the next part of
         * its accepted story. No new frame/timer, failed-beat advancement or
         * recording-time delay; the same entropy still owns the whole story. */
        if(level==COMP_SCREEN_MENU_INTERACTION_QUIET)
            due=visible_ms+9000u+((r->pet.seed>>17u)%9u)*600u;
        if((int32_t)(due-r->life.next_request_ms)>0)r->life.next_request_ms=due;
    }
    r->visible_surface = f->surface; r->visible_revision = f->revision;
    if(f->kind==COMP_RUNTIME_FRAME_SLEEP && f->sleep_phase==r->sleep_phase &&
       f->reaction_generation==r->reaction_generation && f->surface==r->surface) {
        /* The dwell belongs to visible ink, never to a submit or failed BUSY.
         * Yawn is a semantic anchor of this rare finite phrase. A normal
         * non-visible RAM tail must not silently remove it; no catch-up queue. */
        if(f->sleep_phase==COMP_RUNTIME_SLEEP_DOZE) {
            r->sleep_phase=COMP_RUNTIME_SLEEP_YAWN;
            r->reaction_due_ms=visible_ms+900u;
        } else if(f->sleep_phase==COMP_RUNTIME_SLEEP_YAWN) {
            r->sleep_phase=COMP_RUNTIME_SLEEP_PARK;
            r->reaction_due_ms=visible_ms+1100u;
        } else if(f->sleep_phase==COMP_RUNTIME_SLEEP_WAKE) {
            r->sleep_phase=COMP_RUNTIME_SLEEP_ATTEND;
            r->reaction_due_ms=visible_ms+650u;
        } else {
            r->sleep_phase=COMP_RUNTIME_SLEEP_NONE;
            if(f->sleep_phase==COMP_RUNTIME_SLEEP_ATTEND) {
                enter_pet_daily(r,now,r->affect.selected);
                r->life.next_request_ms=visible_ms+1800u;
                r->family_due_ms=visible_ms+28000u;
                comp_epaper_natural_blink_enter_daily(&r->blink,visible_ms);
            }
        }
        if(r->sleep_phase==COMP_RUNTIME_SLEEP_PARK) {
            r->surface=COMP_SCREEN_SURFACE_LOW_POWER;
            dirty(r);
        }
    }
    if (f->surface == COMP_SCREEN_SURFACE_MENU) {
        r->visible_menu_valid = true;
        r->visible_menu_revision = f->menu.revision;
        r->visible_menu_view = f->menu.view;
        r->visible_menu_home_page = f->menu.home_page;
#if COMPANION_WBA_RESOURCE_PROFILE
        /* One optional arrival, then settle. A failed frame retains arrival;
         * a newer screen/action never inherits or clears an old animation. */
        if (r->surface==COMP_SCREEN_SURFACE_MENU &&
            f->revision==r->revision && r->menu.revision==f->menu.revision) {
            /* An optional arrival costs a second complete transaction. At
             * normal e-paper costs, show the final page and scrollbar in one
             * commit. A short status repaint cannot re-enable animation
             * after this menu session has proved slower than 350 ms. */
            r->menu.home_scroll_offset_px=(r->menu.home_scroll_offset_px & COMP_SCREEN_MENU_SCROLL_SLOW) ||
                now-r->frame_requested_ms>350u?
                COMP_SCREEN_MENU_SCROLL_SLOW:0u;
            if (f->menu.home_scroll_offset_px & COMP_SCREEN_MENU_SCROLL_ARRIVAL_MASK) {
                ++r->menu.revision;dirty(r);
            }
        }
#endif
        if(r->surface==COMP_SCREEN_SURFACE_MENU && f->revision==r->revision &&
           menu_context(r)==r->menu_feedback_context &&
           menu_page_context(&f->menu)==r->menu_feedback_context &&
           f->menu_feedback!=COMP_RUNTIME_MENU_FEEDBACK_NONE && f->menu_feedback==r->menu_feedback)
            r->menu_feedback_seen=true;
    } else {
        r->visible_menu_valid = false;
    }
    if (f->family_clean && f->family==r->affect.selected) r->family_clean=false;
    if (f->surface==COMP_SCREEN_SURFACE_HOME &&
        f->recording==DENZIC_AUDIO_RECORDING_STATE_RECORDING && !f->recording_paused &&
        f->kind!=COMP_RUNTIME_FRAME_HOLD && r->capture_active &&
        f->recording_token==r->record_token) {
        r->recording_wave_index=f->recording_wave_index;
        r->recording_wave_started=true;
        /* A slow successful update can span another timer tick. Keep that
         * newer wave due; neither failures nor a prior session consume it. */
        r->recording_wave_due=COMPANION_WBA_RESOURCE_PROFILE &&
            f->recording_elapsed_seconds!=r->recording_display_second;
    } else if (!COMPANION_WBA_RESOURCE_PROFILE && f->surface==COMP_SCREEN_SURFACE_HOME && r->capture_active) {
        r->recording_wave_due=true;
    }
    if (f->kind==COMP_RUNTIME_FRAME_REACTION && f->reaction_reply && f->reaction_step==0u &&
        f->reaction_generation==r->reaction_generation)
        r->reaction_input_after_ms=now+reaction_interval(r);
    if(f->kind==COMP_RUNTIME_FRAME_REACTION && !f->reaction_reply && !f->reaction_step &&
       r->surface==COMP_SCREEN_SURFACE_HOME && !r->touch_contact && r->reaction_pending &&
       !r->reaction_route_count && r->reaction_step==1u) {
        const uint32_t due=visible_ms+PET_GAZE_RELEASE_HOLD_MS;
        if((int32_t)(due-r->reaction_due_ms)>0)r->reaction_due_ms=due;
    }
    if (f->kind==COMP_RUNTIME_FRAME_REACTION && f->reaction_generation==r->reaction_generation) {
        if (f->reaction_reply) {
            bool released_target=false;
            if(f->reaction_expression && f->reaction_pose_phase==1u && f->surface==COMP_SCREEN_SURFACE_HOME) {
#if COMP_PET_PROCEDURAL
                comp_pet_behavior_attention_visible(&r->pet,f->family,visible_ms);
                if(f->reaction_step==1u)comp_pet_behavior_visible(&r->pet,visible_ms);
#endif
                if(f->reaction_step==1u)pet_reply(r,f->family,now,visible_ms);
            }
            if(COMP_RUNTIME_PET_MOTION && f->reaction_step==0u) {
                /* Optional poses consume whole driver slots. The observed
                 * paired-RAM tail can be as long as the visible BUSY wait;
                 * budget from request through released buffers. Readable
                 * holds still begin at qualified visible_ms, not at now. */
                r->reaction_pose_count=reply_pose_count(r,now-r->frame_requested_ms);
                r->reaction_pose_phase=r->reaction_pose_count==3u?0u:1u;
                ++r->reaction_step;
            } else if(r->reaction_pose_count==3u && f->reaction_expression && r->reaction_pose_phase<2u) {
                ++r->reaction_pose_phase;
            } else {
                ++r->reaction_step;
#if COMP_PET_PROCEDURAL
                if(r->reaction_step==2u && r->reaction_route_count==2u &&
                    (r->pet.interaction==COMP_PET_CHEEK || r->pet.interaction==COMP_PET_SHAKE))
                    r->reaction_pose_count=1u;
#endif
                r->reaction_pose_phase=r->reaction_pose_count==3u?0u:1u;
            }
            if (r->reaction_step==r->reaction_route_count+2u) {
#if COMP_PET_PROCEDURAL
                /* Hand this successfully landed positive feeling to daily
                 * life. No extra contact score, draw or refresh is invented;
                 * cancelled/failed returns cannot change the daily family. */
                if(f->surface==COMP_SCREEN_SURFACE_HOME &&
                   (pet_handling_intent(r) ||
                    (((r->pet.interaction>=COMP_PET_HEAD_PAT && r->pet.interaction<=COMP_PET_CHIN) ||
                      r->pet.interaction==COMP_PET_GREETING) &&
                     (f->family==COMP_BROWSER_FAMILY_WARM || f->family==COMP_BROWSER_FAMILY_DELIGHTED ||
                      f->family==COMP_BROWSER_FAMILY_BASHFUL || f->family==COMP_BROWSER_FAMILY_PLAYFUL))))
                    r->affect.selected=f->family;
#endif
                r->reaction_pending=false;
                /* Alternate the next complete reply, not failed attempts or
                 * incidental IMU reports. Reuse the retired route-edge byte. */
                if(!COMP_RUNTIME_PET_MOTION)++r->reaction_variant;
                /* The final original directional face is now visible. Keep
                 * its attention feeling and coordinates; a later contact may
                 * replace only the target. Release during an in-flight return
                 * still earns the same visible pause and centre landing. */
                r->gaze_x=f->gaze_x;r->gaze_y=f->gaze_y;
                r->reaction_route[0]=f->family;r->reaction_route_count=0u;
                r->reaction_step=0u;
                released_target=!r->touch_contact &&
                    (r->gaze_x!=100u || r->gaze_y!=100u);
                if(r->deferred_pet_kind==COMP_RUNTIME_PET_INPUT_FOLLOW &&
                   r->deferred_pet_x==f->gaze_x && r->deferred_pet_y==f->gaze_y)
                    r->deferred_pet_kind=COMP_RUNTIME_PET_INPUT_NONE;
                /* A reply has landed on the selected daily family. Retire
                 * the interrupted life phrase before resuming; continuing
                 * its old accent/follow would jump back to a pre-input pose.
                 * Re-enter only after the final reply visibly succeeds, so
                 * retries keep their route and outstanding life completions
                 * are already resolved. The landing owns its quiet pause. */
                if(COMP_RUNTIME_PET_MOTION && r->surface==COMP_SCREEN_SURFACE_HOME)
                    enter_pet_daily(r,now,r->affect.selected);
#if COMP_PET_PROCEDURAL
                /* One calm landing, with a readable pause chosen from this
                 * accepted phrase's existing seed. No extra image, random
                 * draw or clock-driven refresh is added. */
                if(effective_interaction_level(r)==COMP_SCREEN_MENU_INTERACTION_QUIET)
                    /* A deliberate reply has already supplied the acting.
                     * Give it the same quiet rest as a completed daily scene.
                     * This only gates autonomous life; explicit input remains
                     * under its existing independent admission/priority. */
                    r->life.next_request_ms=visible_ms+9000u+((r->pet.seed>>17u)%9u)*600u;
                else
                    r->life.next_request_ms=visible_ms+1400u+((r->pet.seed>>17u)%5u)*200u;
#else
                r->life.next_request_ms=now+960u;
#endif
                /* Motion may acknowledge handling, but is not fresh affection.
                 * Keep the prior daily deadline: repeated pickup/shake/settle
                 * must not keep an old warm face alive another28s each time.
                 * Mood selection still waits for the existing scene boundary. */
                if(!pet_motion_intent(r))r->family_due_ms=now+28000u;
#if COMP_PET_PROCEDURAL
                /* The interaction already supplied eye acting. Only a
                 * successful final pose rearms the natural blink quiet gap. */
                if(!r->blink.open_pending && !r->blink.open_in_flight)
                    comp_epaper_natural_blink_enter_daily(&r->blink,visible_ms);
#endif
            }
            /* The peak was already visible during non-visible RAM sync.
             * Credit that time instead of adding the same dwell afterward.
             * No next pose can be rendered until transaction completion;
             * failed updates return above and cannot skip a reply beat. */
            if(COMP_RUNTIME_PET_MOTION)
#if COMP_PET_PROCEDURAL
                r->reaction_due_ms=visible_ms+(f->reaction_expression && f->reaction_pose_phase==1u?r->pet.peak_hold_ms:0u);
#else
                r->reaction_due_ms=visible_ms+(f->reaction_expression && f->reaction_pose_phase==1u?160u:0u);
#endif
            else r->reaction_due_ms=now+(r->reaction_step==2u ? 960u :
                r->reaction_step==3u && r->reaction_route_count==2u ? 720u : 480u);
            if(released_target)release_gaze(r,visible_ms);
        } else {
            r->reaction_pending=false;
            if(f->reaction_step==1u && r->surface==COMP_SCREEN_SURFACE_HOME) {
                r->gaze_x=r->gaze_y=100u;
                /* The return starts a new daily phrase, just like a reply's
                 * landing. Keep its accepted intent seed instead of falling
                 * back to the coordinator's counter-derived entry subset. */
                enter_pet_daily(r,now,r->affect.selected);
            }
            /* A qualified gaze target or return is already eye acting. This
             * includes a centre target reached while the finger is still on
             * screen, not only the separately scheduled release-return frame.
             * Preserve an existing visible blink-open obligation. */
            if(!r->blink.open_pending && !r->blink.open_in_flight)
                comp_epaper_natural_blink_enter_daily(&r->blink,visible_ms);
            r->life.next_request_ms=now+960u;
        }
    }
    if(f->kind==COMP_RUNTIME_FRAME_REACTION && r->surface==COMP_SCREEN_SURFACE_HOME &&
       f->reaction_generation==r->pet_play.generation && !r->reaction_pending) {
        if(r->pet_play.phase==COMP_PET_PLAY_ORIENT) {
            r->pet_play.phase=COMP_PET_PLAY_AIM;
            r->pet_play.due_ms=now+480u;
        } else if(r->pet_play.phase==COMP_PET_PLAY_CUE) {
            r->pet_play.phase=COMP_PET_PLAY_WAIT;
            r->pet_play.due_ms=0u;
        } else if(r->pet_play.phase==COMP_PET_PLAY_REPLY) {
            if(++r->pet_play.round>=COMP_PET_PLAY_ROUNDS) {
                enter_home(r,now);r->pet_play.phase=COMP_PET_PLAY_ENDED;
            }
            else {
                r->pet_play.phase=COMP_PET_PLAY_NEXT;
                /* This is an explicitly requested next turn, not autonomous
                 * idle activity. Quiet's long daily pause must not stall it.
                 * The successful reply has already completed visibly; the
                 * normal centre/aim transactions still own each next frame. */
                r->pet_play.due_ms=now+600u;
            }
        }
    }
    if(f->kind==COMP_RUNTIME_FRAME_HOLD && r->surface==COMP_SCREEN_SURFACE_HOME && r->hold.active &&
       f->hold_generation==r->hold_generation)
        (void)comp_browser_menu_hold_commit(&r->hold,f->hold_bucket);
    /* Recognition can precede the slow panel's fourth progress picture.
     * Retain the recognized intent after release, but enter only after all
     * four HOLD pictures have actually committed. Unrelated successful
     * status/life frames must never skip the remaining visible milestones. */
    if(r->surface==COMP_SCREEN_SURFACE_HOME && r->hold_enter_requested &&
       r->hold.active && r->hold.next_milestone >=
           COMPANION_BROWSER_INTERACTION_MENU_HOLD_MILESTONE_COUNT && !record_busy(r)) {
        enter_menu(r,COMP_SCREEN_MENU_VIEW_BROWSER_HOME);
    }
    return true;
}
