#ifndef COMP_WBA_SILENCE_STOP_H
#define COMP_WBA_SILENCE_STOP_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
/* Optional acoustic inactivity detector, not speech recognition. Default off.
 * 10 ms PCM frames; a continuous 500 ms audible run arms the timer. Initial
 * silence or isolated impacts never stop a recording. */
typedef struct { uint32_t quiet_frames,limit_frames; uint16_t audible_frames; bool armed; } comp_wba_silence_stop_t;
void comp_wba_silence_stop_init(comp_wba_silence_stop_t *,bool enabled,bool meeting);
bool comp_wba_silence_stop_pcm(comp_wba_silence_stop_t *,const int16_t *,size_t);
#endif
