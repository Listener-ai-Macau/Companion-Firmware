#ifndef COMP_RECORDER_INPUT_H
#define COMP_RECORDER_INPUT_H
#include "wba_button.h"
#include "motion_events.h"

enum { COMP_INPUT_RECORDER,COMP_INPUT_DICTATION,COMP_INPUT_PRESENTATION,COMP_INPUT_POINTER };
enum { COMP_INPUT_FLICK=1u,COMP_INPUT_SHAKE=2u,COMP_INPUT_UNDO=4u,COMP_INPUT_POINTER_V4=8u,COMP_INPUT_POINTER_RAW=16u };
enum { COMP_INPUT_START=1u,COMP_INPUT_STOP=2u,COMP_INPUT_MARK=4u,
       COMP_INPUT_UNDO_LAST=8u,COMP_INPUT_CANCEL=16u,COMP_INPUT_SUBMIT=32u,
       COMP_INPUT_NEXT=64u,COMP_INPUT_PREVIOUS=128u,COMP_INPUT_WAKE=256u,
       COMP_INPUT_CLICK=512u,COMP_INPUT_DOWN=1024u,COMP_INPUT_UP=2048u,COMP_INPUT_OVERFLOW=4096u };
enum { COMP_INPUT_HELD=1u,COMP_INPUT_DETACHED=2u,COMP_INPUT_FINISHED=4u };
/* Aim may be superseded; physical edges must survive until the host ACKs.
 * Eight entries cover four complete presses without borrowing audio memory. */
typedef struct {uint32_t sequence,event_ms;uint16_t events;uint8_t flags,reserved;} comp_pointer_event_t;
typedef struct {
    uint32_t sequence,event_ms,record_token;
    uint32_t flick_sample_ms; /* Pointer mode reuses this as a tap serial. */
    int32_t flick_angle_md;
    uint16_t events;
    uint8_t mode,options,flags,flick_axis;
    comp_pointer_event_t pointer_events[8];
    uint8_t pointer_head,pointer_count;
} comp_recorder_input_t;
_Static_assert(sizeof(comp_recorder_input_t)<=128u,"bounded shared input and reliable pointer edges");
static inline bool comp_input_pointer_v4(const comp_recorder_input_t *s)
{return s->mode==COMP_INPUT_POINTER&&(s->options&COMP_INPUT_POINTER_V4);}
static inline const comp_pointer_event_t *comp_input_pointer_event(const comp_recorder_input_t *s)
{return comp_input_pointer_v4(s)&&s->pointer_count?&s->pointer_events[s->pointer_head]:NULL;}
static inline void comp_input_pointer_ack(comp_recorder_input_t *s,uint32_t sequence)
{
    const comp_pointer_event_t *event=comp_input_pointer_event(s);
    if(event&&event->sequence==sequence){s->pointer_head=(s->pointer_head+1u)&7u;--s->pointer_count;}
}

static inline void comp_input_note(comp_recorder_input_t *s,uint16_t events,uint32_t now)
{
    if(!events)return;
    if(++s->sequence==0u)++s->sequence;
    s->event_ms=now;s->events|=events;
    if(comp_input_pointer_v4(s)) {
        /* A stalled host cannot grow memory or silently leave a drag held.
         * Overflow is an explicit terminal control event, never a fake click. */
        if(s->pointer_count==8u){s->pointer_head=s->pointer_count=0u;events=COMP_INPUT_OVERFLOW|COMP_INPUT_UP;}
        comp_pointer_event_t *event=&s->pointer_events[(s->pointer_head+s->pointer_count)&7u];
        *event=(comp_pointer_event_t){s->sequence,now,events,s->flags,0u};++s->pointer_count;
    }
}
static inline bool comp_input_mode(comp_recorder_input_t *s,uint8_t mode,uint8_t options,
                                    bool capture_owned,bool key_busy)
{
    if(mode>COMP_INPUT_POINTER||(options&~(mode==COMP_INPUT_POINTER?31u:7u))||
       ((options&COMP_INPUT_POINTER_RAW)&&!(options&COMP_INPUT_POINTER_V4))||capture_owned||key_busy)return false;
    s->mode=mode;s->options=options;s->flags=0u;s->record_token=0u;
    s->events=0u;s->flick_angle_md=0;s->flick_sample_ms=0u;s->pointer_head=s->pointer_count=0u;return true;
}
static inline void comp_input_connection(comp_recorder_input_t *s,bool connected)
{
    if(connected)return;
    s->pointer_head=s->pointer_count=0u;
    if(s->mode!=COMP_INPUT_RECORDER&&(s->flags&COMP_INPUT_HELD))s->flags|=COMP_INPUT_DETACHED;
    else {s->mode=COMP_INPUT_RECORDER;s->options=0u;s->record_token=0u;s->events=0u;}
}
static inline uint16_t comp_input_key(comp_recorder_input_t *s,uint8_t key,bool capture_owned)
{
    uint16_t events=0u;
    if(key&COMP_WBA_BUTTON_DOWN) {
        s->flags=(uint8_t)((s->flags&COMP_INPUT_DETACHED)|COMP_INPUT_HELD);
        s->flick_angle_md=0;
        if(s->mode!=COMP_INPUT_POINTER)s->flick_sample_ms=0u;
        if(s->mode==COMP_INPUT_DICTATION&&!capture_owned)events|=COMP_INPUT_START;
        if(comp_input_pointer_v4(s))events|=COMP_INPUT_DOWN;
    }
    if(key&COMP_WBA_BUTTON_UP) {
        if(comp_input_pointer_v4(s))events|=COMP_INPUT_UP;
        if(s->mode==COMP_INPUT_RECORDER)events|=capture_owned?COMP_INPUT_STOP:COMP_INPUT_START;
        else if(s->mode==COMP_INPUT_DICTATION&&!(s->flags&COMP_INPUT_FINISHED)&&
                (s->record_token||(events&COMP_INPUT_START)))events|=COMP_INPUT_STOP;
        s->flags&=(uint8_t)~COMP_INPUT_HELD;
        if(s->flags&COMP_INPUT_DETACHED){s->mode=COMP_INPUT_RECORDER;s->options=0u;}
    }
    return events;
}
static inline uint16_t comp_input_motion(comp_recorder_input_t *s,uint8_t motion,
    const comp_imu_sample_t *sample,uint8_t tilt,bool capture_owned)
{
    if(s->mode==COMP_INPUT_RECORDER)return capture_owned&&(motion&COMP_MOTION_DOUBLE_TAP)?COMP_INPUT_MARK:0u;
    if(s->mode==COMP_INPUT_POINTER) {
        if(motion&COMP_MOTION_DOUBLE_TAP){++s->flick_sample_ms;return comp_input_pointer_v4(s)&&!(s->flags&COMP_INPUT_HELD)?COMP_INPUT_CLICK:0u;}
        return 0u; /* This can never start/stop MIC. */
    }
    if(s->mode==COMP_INPUT_PRESENTATION) {
        if(!(s->flags&COMP_INPUT_HELD)||!(motion&COMP_MOTION_TILT_CHANGED))return 0u;
        return tilt==COMP_MOTION_TILT_RIGHT?COMP_INPUT_NEXT:tilt==COMP_MOTION_TILT_LEFT?COMP_INPUT_PREVIOUS:0u;
    }
    if(!(s->flags&COMP_INPUT_HELD))
        return !capture_owned&&(s->options&COMP_INPUT_UNDO)&&(motion&COMP_MOTION_DOUBLE_TAP)?COMP_INPUT_UNDO_LAST:0u;
    if(!s->record_token||(s->flags&COMP_INPUT_FINISHED))return 0u;
    if((s->options&COMP_INPUT_SHAKE)&&(motion&COMP_MOTION_SHAKE)) {
        s->flags|=COMP_INPUT_FINISHED;return COMP_INPUT_STOP|COMP_INPUT_CANCEL;
    }
    if(!(s->options&COMP_INPUT_FLICK)||!sample)return 0u;
    /* Provisional six-axis flick: coherent angular movement >=12 degrees,
     * gyro >=120dps, with <=100ms samples. No action across a stale gap. */
    uint32_t dt=sample->timestamp_ms-s->flick_sample_ms;
    if(!dt)return 0u;
    s->flick_sample_ms=sample->timestamp_ms;
    unsigned axis=0u;
    int32_t rate=sample->gyro_mdps[0];
    for(unsigned i=1u;i<3u;++i) {
        int32_t v=sample->gyro_mdps[i];
        if((v<0?-v:v)>(rate<0?-rate:rate)){axis=i;rate=v;}
    }
    if(dt>100u||(rate>-120000&&rate<120000)||s->flick_axis!=axis) {
        s->flick_axis=(uint8_t)axis;s->flick_angle_md=0;return 0u;
    }
    int32_t step=rate*(int32_t)dt/1000;
    if((s->flick_angle_md<0)!=(step<0))s->flick_angle_md=0;
    s->flick_angle_md+=step;
    if(s->flick_angle_md<12000&&s->flick_angle_md>-12000)return 0u;
    s->flags|=COMP_INPUT_FINISHED;return COMP_INPUT_STOP|COMP_INPUT_SUBMIT;
}
#endif
