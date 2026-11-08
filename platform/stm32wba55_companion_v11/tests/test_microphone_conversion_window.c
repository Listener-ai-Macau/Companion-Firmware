#include "microphone_hal.h"
#include "capture_radio_window.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static uint32_t fake_primask,expected_mask,next_us;
static unsigned calls;
static bool current=true,busy,valid=true;
#define __get_PRIMASK() (fake_primask)
#define __disable_irq() ((void)(fake_primask=1u))
#define __set_PRIMASK(v) ((void)(fake_primask=(v)))
#define __DMB() ((void)0)
#define __HAL_DMA_GET_COUNTER(d) ((d)->counter)
static bool half_is_current(comp_v11_microphone_hal_t *m,const comp_v11_microphone_event_t *e)
{ assert(m && e->sequence==42u && fake_primask==expected_mask);return current; }
/* @PRODUCTION_CONVERSION_WINDOW@ */
static bool admit(uint32_t remaining,uint32_t half)
{ ++calls;assert(fake_primask==expected_mask);return comp_capture_radio_convert_open(valid,busy,next_us,remaining,half); }
int main(void)
{
    comp_v11_microphone_hal_t m;memset(&m,0,sizeof(m));
    m.running=true;m.initialized=true;m.conversion_window=admit;
    m.event_head=1u;m.events[0].sequence=42u;m.events[0].half=0u;
    m.dma.counter=7000u;busy=true;next_us=0u;
    assert(!conversion_window_open(&m));
    assert(m.event_tail==0u && m.event_head==1u && m.events[0].sequence==42u && calls==1u);
    m.dma.counter=4993u;assert(!conversion_window_open(&m));
    m.dma.counter=4992u;assert(conversion_window_open(&m)); /*3ms DMA urgency*/
    m.dma.counter=7000u;busy=false;next_us=3501u;
    assert(conversion_window_open(&m));
    unsigned before=calls;current=false;busy=true;next_us=0u;
    assert(conversion_window_open(&m) && calls==before); /*original stale accounting wins*/
    current=true;m.startup_halves_remaining=2u;
    assert(conversion_window_open(&m) && calls==before);
    m.startup_halves_remaining=1u;assert(!conversion_window_open(&m));
    before=calls;m.event_head=m.event_tail;assert(conversion_window_open(&m) && calls==before);
    m.event_head=1u;valid=false;assert(conversion_window_open(&m));
    valid=true;fake_primask=expected_mask=1u;busy=false;next_us=3501u;
    assert(conversion_window_open(&m) && fake_primask==1u);
    fake_primask=expected_mask=0u;m.conversion_window=NULL;busy=true;next_us=0u;
    assert(conversion_window_open(&m) && fake_primask==0u);
    assert(m.event_tail==0u && m.event_head==1u && m.events[0].sequence==42u);
    puts("actual HAL admission retains DMA event, respects3ms urgency, stale faults, priming, no-query fallback and original IRQ mask");
    return 0;
}
