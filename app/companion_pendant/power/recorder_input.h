#ifndef COMP_RECORDER_INPUT_H
#define COMP_RECORDER_INPUT_H
#include "wba_button.h"
#include "motion_events.h"

enum { COMP_INPUT_RECORDER,COMP_INPUT_DICTATION,COMP_INPUT_PRESENTATION,COMP_INPUT_POINTER };
enum { COMP_INPUT_FLICK=1u,COMP_INPUT_SHAKE=2u,COMP_INPUT_UNDO=4u };
enum { COMP_INPUT_START=1u,COMP_INPUT_STOP=2u,COMP_INPUT_MARK=4u,
       COMP_INPUT_UNDO_LAST=8u,COMP_INPUT_CANCEL=16u,COMP_INPUT_SUBMIT=32u,
       COMP_INPUT_NEXT=64u,COMP_INPUT_PREVIOUS=128u,COMP_INPUT_WAKE=256u };
enum { COMP_INPUT_HELD=1u,COMP_INPUT_DETACHED=2u,COMP_INPUT_FINISHED=4u };
typedef struct {
    uint32_t sequence,event_ms,record_token;
    uint32_t flick_sample_ms;
    int32_t flick_angle_md;
    uint16_t events;
    uint8_t mode,options,flags,flick_axis;
} comp_recorder_input_t;
_Static_assert(sizeof(comp_recorder_input_t)<=28u,"bounded shared input state");

static inline void comp_input_note(comp_recorder_input_t *s,uint16_t events,uint32_t now)
{
    if(!events)return;
    if(++s->sequence==0u)++s->sequence;
    s->event_ms=now;s->events|=events;
}
static inline bool comp_input_mode(comp_recorder_input_t *s,uint8_t mode,uint8_t options,
                                    bool capture_owned,bool key_busy)
{
    if(mode>COMP_INPUT_POINTER||(options&~7u)||capture_owned||key_busy)return false;
    s->mode=mode;s->options=options;s->flags=0u;s->record_token=0u;
    s->events=0u;s->flick_angle_md=0;s->flick_sample_ms=0u;return true;
}
static inline void comp_input_connection(comp_recorder_input_t *s,bool connected)
{
    if(connected)return;
    if(s->mode==COMP_INPUT_DICTATION&&(s->flags&COMP_INPUT_HELD))s->flags|=COMP_INPUT_DETACHED;
    else {s->mode=COMP_INPUT_RECORDER;s->options=0u;s->record_token=0u;s->events=0u;}
}
static inline uint16_t comp_input_key(comp_recorder_input_t *s,uint8_t key,bool capture_owned)
{
    uint16_t events=0u;
    if(key&COMP_WBA_BUTTON_DOWN) {
        s->flags=(uint8_t)((s->flags&COMP_INPUT_DETACHED)|COMP_INPUT_HELD);
        s->flick_angle_md=0;s->flick_sample_ms=0u;
        if(s->mode==COMP_INPUT_DICTATION&&!capture_owned)events|=COMP_INPUT_START;
    }
    if(key&COMP_WBA_BUTTON_UP) {
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
    if(s->mode==COMP_INPUT_POINTER)return 0u; /* Host owns pointing/clicks; never MIC. */
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
