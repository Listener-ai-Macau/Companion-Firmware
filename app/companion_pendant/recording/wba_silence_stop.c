#include "wba_silence_stop.h"
#include <string.h>
void comp_wba_silence_stop_init(comp_wba_silence_stop_t *s,bool enabled,bool meeting) {
    memset(s,0,sizeof(*s));s->limit_frames=enabled?(meeting?1500u:500u):0u;
}
bool comp_wba_silence_stop_pcm(comp_wba_silence_stop_t *s,const int16_t *pcm,size_t n) {
    uint32_t mean=0;
    if(!s || !pcm || n!=160u || !s->limit_frames)return false;
    for(size_t i=0;i<n;++i) {int32_t v=pcm[i];mean+=(uint32_t)(v<0?-v:v);}
    mean/=(uint32_t)n;
    /* Hysteresis: arm above about -36 dBFS, count only below -46 dBFS.
     * Ambient noise keeps the meeting running. Hardware gain must be checked
     * before changing these conservative digital thresholds. */
    if(mean>=512u) {
        if(s->audible_frames<50u)++s->audible_frames;
        if(s->audible_frames>=50u)s->armed=true;
        s->quiet_frames=0;
    } else {
        s->audible_frames=0;
        if(mean>=160u)s->quiet_frames=0;
        else if(s->armed && s->quiet_frames<s->limit_frames)++s->quiet_frames;
    }
    return s->armed && s->quiet_frames>=s->limit_frames;
}
