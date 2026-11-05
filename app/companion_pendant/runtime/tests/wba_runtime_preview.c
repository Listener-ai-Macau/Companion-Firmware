/* Host adapter only. The production coordinator, resources and renderer are
 * linked unchanged. Touch, recording backend, entropy and panel completion
 * below are explicit simulated peripherals, never physical acceptance. */
#include "companion_runtime.h"
#include "companion_renderer.h"
#include "companion_reply_layout.h"
#include "companion_resources.h"
#include <stdio.h>
#include <string.h>

#ifdef _WIN32
#define API __declspec(dllexport)
#else
#define API
#endif

static comp_runtime_t runtime;
static comp_runtime_renderer_t renderer;
static comp_runtime_resources_t resources;
static comp_asset_store_t store;
static comp_speaker_t speaker;
static comp_runtime_frame_t pending, visible;
static uint8_t staging[5000], pixels[5000];
static uint32_t tick, panel_due, panel_ms=350, dma_due, entropy_value;
static uint32_t sequence, version, failures, missing, life_count, wave_count, blink_count;
static uint32_t backend_due, backend_token, recording_count, auto_release;
static uint32_t menu_action_calls, last_menu_action;
static uint32_t menu_mode,menu_delay,menu_due,menu_backend_token;
static uint16_t contact_x, contact_y;
static unsigned backend_phase, requested_family=255u, swipe_step;
static unsigned requested_pose_family=255u, requested_pose_zone;
static uint32_t swipe_due;
static bool mounted, panel_pending, fail_next, contact, backend_ready, amplifier;
static char last_state[160], missing_state[160], snapshot[4096];

static bool amp(void *context,bool enabled)
{ (void)context;amplifier=enabled;return true; }
static bool transmit(void *context,const int16_t *pcm,size_t frames)
{ (void)context;(void)pcm;dma_due=tick+4u;return frames==COMP_SPEAKER_BLOCK_FRAMES; }
static void audio_activity(void *context,bool active)
{ (void)context;(void)active; }
static bool ready(void *context) { (void)context;return backend_ready; }
static bool prepare(void *context,uint32_t token)
{ (void)context;backend_ready=false;backend_phase=1;backend_due=tick+600u;backend_token=token;return true; }
static bool record(void *context,bool start,uint32_t token)
{
    (void)context;backend_token=token;
    if(start) {
        if(amplifier || comp_speaker_active(&speaker))return false;
        backend_phase=2;backend_due=tick+80u;
    } else if(runtime.capture_active) {
        backend_phase=3;backend_due=tick+80u;
    } else {backend_phase=0;backend_ready=true;}
    return true;
}
static bool menu_action(void *context,const comp_screen_menu_result_t *action,const comp_screen_menu_t *menu)
{
    (void)context;(void)menu;
    ++menu_action_calls;last_menu_action=(uint32_t)action->action;
    if(action->action==COMP_SCREEN_MENU_ACTION_BROWSER_CLEAR_RECORDINGS) {
        recording_count=0;comp_runtime_catalog(&runtime,0,0);
    }
    return true; /* simulated settings backend; never persisted to a device */
}
static comp_runtime_menu_dispatch_t menu_begin(void *context,const comp_screen_menu_result_t *action,
    const comp_screen_menu_t *menu,uint32_t token)
{
    if(!menu_mode)return menu_action(context,action,menu)?COMP_RUNTIME_MENU_COMPLETE:COMP_RUNTIME_MENU_FAILED;
    ++menu_action_calls;last_menu_action=(uint32_t)action->action;
    if(menu_mode==3u)return COMP_RUNTIME_MENU_FAILED;
    menu_backend_token=token;menu_due=tick+menu_delay;
    return COMP_RUNTIME_MENU_PENDING;
}
API void cp_menu_backend(unsigned mode,unsigned delay_ms)
{
    if(mode<=5u && delay_ms<=120000u){menu_mode=mode;menu_delay=delay_ms;}
}
API int cp_menu_complete(unsigned token,unsigned result)
{
    if(result>COMP_RUNTIME_BACKEND_FAILED)return 0;
    if(!comp_runtime_menu_complete(&runtime,token,(comp_runtime_result_t)result,tick))return 0;
    if(result==COMP_RUNTIME_OK && runtime.menu_pending_action==COMP_SCREEN_MENU_ACTION_BROWSER_CLEAR_RECORDINGS) {
        recording_count=0;comp_runtime_catalog(&runtime,0,0);
    }
    return 1;
}
static bool random_value(void *context,uint32_t *value)
{
    (void)context;entropy_value^=entropy_value<<13;entropy_value^=entropy_value>>17;
    entropy_value^=entropy_value<<5;*value=entropy_value;return true;
}
static bool read_state(void *context,const char *name,uint8_t frame[5000])
{
    (void)snprintf(last_state,sizeof(last_state),"%s",name);
    if(comp_runtime_resources_read(context,name,frame))return true;
    missing++;(void)snprintf(missing_state,sizeof(missing_state),"%s",name);return false;
}
static void touch_sample(bool down,uint16_t x,uint16_t y)
{
    comp_ft6336_touch_sample_t sample={(uint8_t)(down?1:0),
        down?COMP_FT6336_TOUCH_EVENT_CONTACT:COMP_FT6336_TOUCH_EVENT_UP,0,x,y};
    comp_runtime_touch(&runtime,&sample,++sequence,true,tick);
}
API int cp_init(const uint8_t *image,uint32_t bytes,uint32_t seed)
{
    comp_speaker_config_t sc={amp,transmit,audio_activity,NULL};
    comp_runtime_config_t rc={&speaker,NULL,ready,record,menu_action,prepare,random_value,menu_begin};
    tick=panel_due=dma_due=sequence=version=failures=missing=life_count=wave_count=blink_count=0;
    backend_due=backend_token=recording_count=auto_release=swipe_due=0;
    menu_action_calls=last_menu_action=0;
    menu_mode=menu_delay=menu_due=menu_backend_token=0;
    backend_phase=swipe_step=0;requested_family=255u;panel_ms=350;
    requested_pose_family=255u;requested_pose_zone=0u;
    contact_x=contact_y=100u;
    panel_pending=fail_next=contact=amplifier=false;backend_ready=true;entropy_value=seed?seed:1;
    memset(&pending,0,sizeof(pending));memset(&visible,0,sizeof(visible));
    memset(pixels,0xFF,sizeof(pixels));last_state[0]=missing_state[0]=0;
    mounted=comp_asset_store_init_memory(&store,COMP_ASSET_STORAGE_HOST_STREAM,image,bytes) &&
        comp_runtime_resources_mount(&resources,&store);
    comp_speaker_init(&speaker,&sc);comp_runtime_init(&runtime,&rc,0);
    comp_runtime_renderer_init(&renderer,read_state,&resources);
    comp_runtime_renderer_set_ui_reader(&renderer,comp_runtime_resources_read_ui);
    return mounted?1:0;
}
API void cp_touch(unsigned down,unsigned x,unsigned y)
{
    if(x>=200u||y>=200u)return;
    auto_release=0;swipe_step=0;contact=down!=0;contact_x=(uint16_t)x;contact_y=(uint16_t)y;
    touch_sample(contact,contact_x,contact_y);
}
API void cp_clock(unsigned hour,unsigned minute)
{
    if(hour<24u&&minute<60u)comp_runtime_status(&runtime,0x8000u|(hour<<8u)|minute);
}
/* Explicit host-supplied power/OTA state, routed through the same runtime
 * status interface as product_app. Never a real ADC/charger measurement. */
API void cp_power_state(unsigned mv,unsigned percent,unsigned flags)
{
    uint32_t packed=runtime.status_packed & 0x0001FFFFu;
    if(percent<=100u)packed|=(1u<<17)|COMP_SCREEN_STATUS_ESTIMATED_BATTERY|((uint32_t)percent<<24);
    packed|=flags & (COMP_SCREEN_STATUS_CHARGING|COMP_SCREEN_STATUS_CHARGER_FAULT|COMP_SCREEN_STATUS_UPDATING);
    comp_runtime_status(&runtime,packed);
    comp_runtime_battery_voltage(&runtime,(uint16_t)mv);
}
/* Host-only locale selection for the rendered artwork; no saved device setting. */
API void cp_language(unsigned language)
{
    if(language<3u) {
        runtime.menu.language=(comp_screen_menu_language_t)language;
        ++runtime.menu.revision;++runtime.revision;
    }
}
API void cp_cancel(void)
{
    contact=false;auto_release=0;swipe_step=0;
    comp_runtime_touch(&runtime,NULL,++sequence,false,tick);
}
API void cp_panel(unsigned latency_ms,unsigned fail)
{ if(latency_ms>=20u&&latency_ms<=2000u)panel_ms=latency_ms;fail_next=fail!=0; }
API void cp_family(unsigned family)
{ if(family<COMP_BROWSER_FAMILY_COUNT)requested_family=family; }
/* Host-only art inspection. This does not assert a real touch/IMU report or
 * alter affinity; the image still uses the production resource/renderer. */
API void cp_pose(unsigned family,unsigned zone)
{ if(family<COMP_BROWSER_FAMILY_COUNT && zone<=COMP_BROWSER_TAP_ZONE_RIGHT) {
    requested_pose_family=family;requested_pose_zone=zone;
} }
API int cp_action(unsigned action)
{
    switch(action) {
    case 1:return comp_runtime_record(&runtime,true,tick)==COMP_RUNTIME_OK;
    case 2:return comp_runtime_record(&runtime,false,tick)==COMP_RUNTIME_OK;
    case 3:comp_runtime_motion(&runtime,COMP_MOTION_PICKUP,1,++sequence,tick);return 1;
    case 4:comp_runtime_set_connected(&runtime,!runtime.connected,tick);return 1;
    case 5:contact=true;contact_x=contact_y=100;auto_release=tick+5000u;touch_sample(true,100,100);return 1;
    case 6:contact=true;contact_x=45;contact_y=100;swipe_step=1;swipe_due=tick+60u;touch_sample(true,45,100);return 1;
    case 7:contact=true;contact_x=contact_y=100;auto_release=tick+100u;touch_sample(true,100,100);return 1;
    case 8:comp_runtime_motion(&runtime,COMP_MOTION_SHAKE,1,++sequence,tick);return 1;
    default:return 0;
    }
}
API void cp_step(uint32_t now)
{
    if(menu_backend_token) {
        if(menu_mode==5u)(void)comp_runtime_menu_retrying(&runtime,menu_backend_token,true);
        if((int32_t)(now-menu_due)>=0) {
            tick=now;
            if(menu_mode==4u)(void)comp_runtime_menu_pair_timeout(&runtime,menu_backend_token,tick);
            else (void)cp_menu_complete(menu_backend_token,menu_mode==2u?COMP_RUNTIME_BACKEND_FAILED:COMP_RUNTIME_OK);
            menu_backend_token=0u;
        }
    }
    tick=now;
    if(!mounted)return;
    if(backend_phase && (int32_t)(tick-backend_due)>=0) {
        unsigned phase=backend_phase;backend_phase=0;
        if(phase==1)backend_ready=true;
        else if(phase==2)(void)comp_runtime_recording_update(&runtime,backend_token,DENZIC_AUDIO_RECORDING_STATE_RECORDING,true,tick);
        else if(phase==3) {
            (void)comp_runtime_recording_update(&runtime,backend_token,DENZIC_AUDIO_RECORDING_STATE_STOPPING,false,tick);
            backend_phase=4;backend_due=tick+700u;
        } else {
            ++recording_count;comp_runtime_catalog(&runtime,(uint16_t)recording_count,(uint16_t)(recording_count*8u));
            (void)comp_runtime_recording_update(&runtime,backend_token,DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY,false,tick);
        }
    }
    if(swipe_step && (int32_t)(tick-swipe_due)>=0) {
        contact_x=(uint16_t)(45u+swipe_step*30u);swipe_due=tick+60u;
        if(++swipe_step==5u) {contact=false;swipe_step=0;touch_sample(false,contact_x,contact_y);}
    }
    if(contact && auto_release && (int32_t)(tick-auto_release)>=0) {
        contact=false;auto_release=0;touch_sample(false,contact_x,contact_y);
    }
    /* The real controller is polled while released too. Its zero-contact
     * reports complete release debounce after a consumed long press/swipe. */
    touch_sample(contact,contact_x,contact_y);
    if(speaker.tx_pending && (int32_t)(tick-dma_due)>=0)comp_speaker_tx_complete(&speaker,true);
    comp_runtime_service(&runtime,tick);
    if(panel_pending && (int32_t)(tick-panel_due)>=0) {
        bool ok=!fail_next;fail_next=false;panel_pending=false;
        (void)comp_runtime_renderer_complete(&renderer,pending.token,ok);
        (void)comp_runtime_complete_frame(&runtime,pending.token,ok,tick);
        if(ok) {
            memcpy(pixels,staging,5000);visible=pending;++version;
            if(pending.kind==COMP_RUNTIME_FRAME_LIFE)++life_count;
            if(pending.kind==COMP_RUNTIME_FRAME_RECORDING_WAVE)++wave_count;
            if(pending.kind==COMP_RUNTIME_FRAME_BLINK)++blink_count;
        } else ++failures;
    }
    if(!panel_pending && requested_family<COMP_BROWSER_FAMILY_COUNT && !runtime.capture_active) {
        /* Explicit art-inspection input, not autonomous behavior. All following
         * movement/transition timing is still the production coordinator. */
        runtime.affect.selected=(comp_browser_family_t)requested_family;
        runtime.reaction_pending=false;runtime.family_clean=true;
        runtime.family_due_ms=tick+16000u;runtime.family_retry_ms=tick;
        comp_epaper_motion_coordinator_enter_daily(&runtime.life,tick,(comp_epaper_motion_family_t)requested_family);
        comp_epaper_natural_blink_enter_daily(&runtime.blink,tick);
        ++runtime.revision;requested_family=255u;
    }
    if(!panel_pending && requested_pose_family<COMP_BROWSER_FAMILY_COUNT && !runtime.capture_active) {
        runtime.reaction_route_count=1u;
        runtime.reaction_route[0]=runtime.affect.selected;
        runtime.reaction_route[1]=(comp_browser_family_t)requested_pose_family;
        runtime.reaction_route[2]=COMP_BROWSER_FAMILY_NONE;
        runtime.reaction_zone=(uint8_t)requested_pose_zone;
        runtime.reaction_after_zone=COMP_BROWSER_TAP_ZONE_CENTER;
        runtime.reaction_step=1u;runtime.reaction_pending=true;runtime.reaction_due_ms=tick;
        runtime.reaction_pose_phase=1u;runtime.reaction_pose_count=1u;
        runtime.gaze_x=runtime.gaze_y=100u;
        ++runtime.reaction_generation;requested_pose_family=255u;
    }
    if(!panel_pending && comp_runtime_take_frame(&runtime,tick,&pending)) {
        if(comp_runtime_renderer_render(&renderer,&pending,staging)) {panel_pending=true;panel_due=tick+panel_ms;}
        else {(void)comp_runtime_complete_frame(&runtime,pending.token,false,tick);++failures;}
    }
}
API const uint8_t *cp_frame(void) {return pixels;}
API const char *cp_snapshot(void)
{
    (void)snprintf(snapshot,sizeof(snapshot),
        "{\"mounted\":%s,\"nowMs\":%lu,\"version\":%lu,\"family\":\"%s\",\"targetFamily\":\"%s\","
        "\"surface\":%u,\"menuView\":%u,\"menuPage\":%u,\"language\":%u,\"recording\":%u,\"capturing\":%s,"
        "\"preparing\":%s,\"elapsedSeconds\":%lu,\"connected\":%s,\"panelPending\":%s,\"panelLatencyMs\":%lu,"
        "\"replyTextSlot\":[%u,%u,%u,%u],\"visibleKind\":%u,\"reply\":%s,\"replyStep\":%u,\"replyExpression\":%s,\"replyZone\":%u,\"replyPosePhase\":%u,\"replyPoseCount\":%u,\"petVariant\":%u,\"replyPending\":%s,\"eyesClosedMask\":%u,\"blinkClosed\":%s,\"waveIndex\":%u,\"lifeCommits\":%lu,\"waveCommits\":%lu,\"blinkCommits\":%lu,"
        "\"petSeed\":%lu,\"petInteraction\":%u,\"petIntensity\":%u,\"petRepetitions\":%u,\"petPeakHoldMs\":%u,"
        "\"failures\":%lu,\"missingStates\":%lu,\"lastState\":\"%s\",\"missingState\":\"%s\","
        "\"lifeDueMs\":%lu,\"blinkDueMs\":%lu,\"familyDueMs\":%lu,\"familyChanges\":%lu,\"recordingCount\":%lu,"
        "\"menuActionCalls\":%lu,\"lastMenuAction\":%lu,\"menuPending\":%s,\"menuToken\":%lu,\"menuFeedback\":%u,\"visibleMenuFeedback\":%u,\"deferredPetTap\":%s,\"reactionGeneration\":%lu,\"strokePhase\":%u,\"deferredPetStroke\":%s,"
        "\"deferredPetKind\":%u,\"gazeX\":%u,\"gazeY\":%u,\"visibleGazeX\":%u,\"visibleGazeY\":%u,\"touchContact\":%s,"
        "\"visibleAction\":\"%s\",\"visiblePhase\":%u,\"visibleEpisode\":%lu,"
        "\"playPhase\":%u,\"playRound\":%u,\"playDirection\":%u,\"playRetry\":%s,\"visiblePlayCaption\":%u,"
        "\"runtimeBytes\":%u,\"frameBytes\":%u,\"playBytes\":%u,\"interactionLevel\":%u,"
        "\"savedNotice\":%s,\"savedNoticeState\":%u,\"savedNoticeDueMs\":%lu,\"recordToken\":%lu}",
        mounted?"true":"false",(unsigned long)tick,(unsigned long)version,comp_browser_family_name(visible.family),
        comp_browser_family_name(runtime.affect.selected),(unsigned)visible.surface,(unsigned)runtime.menu.view,
        (unsigned)runtime.menu.home_page,(unsigned)runtime.menu.language,(unsigned)runtime.recording,runtime.capture_active?"true":"false",
        (runtime.prepare_pending||runtime.start_pending||runtime.command_pending)?"true":"false",(unsigned long)runtime.recording_display_second,runtime.connected?"true":"false",
        panel_pending?"true":"false",(unsigned long)panel_ms,
        COMP_REPLY_TEXT_X,COMP_REPLY_TEXT_Y,COMP_REPLY_TEXT_WIDTH,COMP_REPLY_TEXT_HEIGHT,(unsigned)visible.kind,
        visible.reaction_reply?"true":"false",(unsigned)visible.reaction_step,
        visible.reaction_expression?"true":"false",(unsigned)visible.reaction_zone,
        (unsigned)visible.reaction_pose_phase,(unsigned)runtime.reaction_pose_count,(unsigned)visible.pet_variant,runtime.reaction_pending?"true":"false",
        (unsigned)renderer.visible_eye_closed_mask,visible.blink_closed?"true":"false",
        (unsigned)visible.recording_wave_index,(unsigned long)life_count,(unsigned long)wave_count,(unsigned long)blink_count,
        (unsigned long)visible.pet_seed,(unsigned)visible.pet_interaction,(unsigned)visible.pet_intensity,
        (unsigned)runtime.pet.repetitions,(unsigned)runtime.pet.peak_hold_ms,
        (unsigned long)failures,(unsigned long)missing,last_state,missing_state,(unsigned long)runtime.life.next_request_ms,
        (unsigned long)runtime.blink.next_due_ms,(unsigned long)runtime.family_due_ms,(unsigned long)runtime.autonomous_family_changes,
        (unsigned long)recording_count,(unsigned long)menu_action_calls,(unsigned long)last_menu_action,
        runtime.menu_pending?"true":"false",(unsigned long)runtime.menu_token,(unsigned)runtime.menu_feedback,(unsigned)visible.menu_feedback,
        runtime.deferred_pet_kind!=COMP_RUNTIME_PET_INPUT_NONE?"true":"false",(unsigned long)runtime.reaction_generation,
        (unsigned)runtime.pet_stroke_phase,runtime.deferred_pet_kind==COMP_RUNTIME_PET_INPUT_STROKE?"true":"false",
        (unsigned)runtime.deferred_pet_kind,(unsigned)runtime.gaze_x,(unsigned)runtime.gaze_y,
        (unsigned)visible.gaze_x,(unsigned)visible.gaze_y,runtime.touch_contact?"true":"false",
        comp_epaper_motion_action_name(visible.motion.action),(unsigned)visible.motion.phase,
        (unsigned long)visible.motion.episode,(unsigned)runtime.pet_play.phase,(unsigned)runtime.pet_play.round,
        comp_pet_play_direction(&runtime.pet_play),runtime.pet_play.retry_hint?"true":"false",
        (unsigned)visible.pet_play_caption,(unsigned)sizeof(runtime),(unsigned)sizeof(visible),(unsigned)sizeof(runtime.pet_play),
        (unsigned)runtime.menu.browser.interaction_level,visible.record_saved_notice?"true":"false",
        (unsigned)runtime.record_saved_state,(unsigned long)runtime.record_saved_due_ms,(unsigned long)runtime.record_token);
    return snapshot;
}
