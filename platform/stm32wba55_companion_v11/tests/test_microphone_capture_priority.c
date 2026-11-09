#include "microphone_hal.h"
#include "capture_radio_window.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static uint32_t tick_us,irq_mask;
static unsigned frames;
#define __get_PRIMASK() (irq_mask)
#define __disable_irq() ((void)(irq_mask=1u))
#define __set_PRIMASK(v) ((void)(irq_mask=(v)))
#define __DMB() ((void)0)
#define __HAL_DMA_GET_COUNTER(d) ((d)->counter)
uint32_t HAL_GetTick(void){return tick_us/1000u;}
typedef uint32_t comp_cpu_stage_span_t;
static comp_cpu_stage_span_t comp_cpu_stage_begin(void){return 0;}
static void comp_cpu_stage_end(unsigned s,comp_cpu_stage_span_t t,bool ok){(void)s;(void)t;(void)ok;}
#define COMP_CPU_STAGE_PDM 0u
bool comp_v11_microphone_hal_stop(comp_v11_microphone_hal_t *m){m->running=false;return true;}
static bool half_is_current(comp_v11_microphone_hal_t *m,const comp_v11_microphone_event_t *e)
{(void)m;(void)e;return tick_us<10000u;}
static bool pop_event(comp_v11_microphone_hal_t *m,comp_v11_microphone_event_t *e)
{if(m->event_tail==m->event_head)return false;*e=m->events[m->event_tail++];return true;}
static bool process_stable_half(comp_v11_microphone_hal_t *m,const comp_v11_microphone_event_t *e,bool priming,bool *stale)
{(void)m;(void)e;(void)stale;tick_us+=2000u;if(!priming)++frames;return true;}
static bool busy_radio(uint32_t remaining,uint32_t half)
{
#ifdef OLD_RADIO_CONVERT_GATE
 return comp_capture_radio_convert_open(true,true,0u,remaining,half);
#else
 (void)remaining;(void)half;assert(!"audio snapshot must not defer to radio");return false;
#endif
}
/* @PRODUCTION_POLL@ */
int main(void)
{
 comp_v11_microphone_hal_t m={0};m.running=m.initialized=true;
 m.event_head=1u;m.events[0].sequence=42u;m.events[0].half=1u;
#ifdef OLD_RADIO_CONVERT_GATE
 m.conversion_window=busy_radio;
#else
 (void)busy_radio;
#endif
 /* The completed half has3.2ms left. One permitted4ms foreground slice
  * would overwrite it even though the foreground's8ms metric still passes.
  * Take/copy this real event before yielding to that slice. */
 tick_us=6800u;m.dma.counter=(uint32_t)(COMP_V11_MIC_RAW_HALF_BYTES*132u/100u);
 comp_v11_microphone_poll_result_t first=microphone_hal_poll_body(&m);
 if(first==COMP_V11_MIC_POLL_IDLE){tick_us+=4000u;(void)microphone_hal_poll_body(&m);}
 printf("first=%u frames=%u stale=%lu elapsed_us=%lu\n",first,frames,(unsigned long)m.stale_dma_halves,(unsigned long)tick_us);
 assert(first==COMP_V11_MIC_POLL_PROCESSED&&frames==1u&&!m.stale_dma_halves);
 /* Genuine already-overwritten events still fail; never hide a missing block. */
 m.event_tail=0u;tick_us=10001u;
 assert(microphone_hal_poll_body(&m)==COMP_V11_MIC_POLL_DROPPED&&m.stale_dma_halves==1u&&frames==1u);
 puts("PASS_CAPTURE_BEFORE_RADIO_SOFTWARE_ONLY actual HAL poll; bounded dispatch cannot defer completed DMA; genuine stale still rejected. Not physical timing qualification.");
 return 0;
}
