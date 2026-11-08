#include "../capture_radio_window.h"
#include <assert.h>
#include <stdio.h>

int main(void)
{
    comp_capture_radio_window_t w={0};
    assert(comp_capture_radio_window_open(&w,0,true,true,false,UINT32_MAX));
    assert(comp_capture_radio_window_open(&w,0,true,true,false,5501));
    assert(!comp_capture_radio_window_open(&w,0,true,true,false,5500));
    assert(!comp_capture_radio_window_open(&w,5,true,true,false,0));
    assert(comp_capture_radio_window_open(&w,6,true,true,true,UINT32_MAX));
    /* No permanently blocked audio at a connection interval without a gap. */
    assert(!comp_capture_radio_window_open(&w,7,true,true,true,15000));
    assert(comp_capture_radio_window_open(&w,8,true,false,true,0));
    assert(!w.waiting);
    assert(!comp_capture_radio_window_open(&w,9,true,true,true,UINT32_MAX));
    assert(comp_capture_radio_window_open(&w,10,false,true,true,0));
    assert(!w.waiting);
    assert(!comp_capture_radio_window_open(&w,UINT32_MAX-2u,true,true,true,0));
    assert(!comp_capture_radio_window_open(&w,2,true,true,true,0));
    assert(comp_capture_radio_window_open(&w,3,true,true,true,0));
    assert(!comp_capture_radio_window_open(&w,4,true,true,false,100));
    /* The radio event finishing releases admission immediately, without sleep. */
    assert(comp_capture_radio_window_open(&w,4,true,true,false,15000));
    puts("capture radio quiet-window boundaries, wrap, query failure and bounded fallback passed");
    return 0;
}
