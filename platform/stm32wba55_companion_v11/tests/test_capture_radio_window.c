#include "../capture_radio_window.h"
#include "../capture_encode_window.h"
#include <assert.h>
#include <stdio.h>

int main(void)
{
    comp_capture_radio_window_t w={0};
    assert(comp_capture_radio_window_open(&w,0,true,true,false,UINT32_MAX));
    assert(comp_capture_radio_window_open(&w,0,true,true,false,7001));
    assert(!comp_capture_radio_window_open(&w,0,true,true,false,7000));
    assert(!comp_capture_radio_window_open(&w,5,true,true,false,0));
    assert(comp_capture_radio_window_open(&w,6,true,true,true,UINT32_MAX));
    /* No permanently blocked audio at a connection interval without a gap. */
    assert(!comp_capture_radio_window_open(&w,11,true,true,true,15000));
    assert(comp_capture_radio_window_open(&w,12,true,false,true,0));
    assert(!w.waiting);
    assert(!comp_capture_radio_window_open(&w,13,true,true,true,UINT32_MAX));
    assert(comp_capture_radio_window_open(&w,14,false,true,true,0));
    assert(!w.waiting);
    assert(!comp_capture_radio_window_open(&w,UINT32_MAX-2u,true,true,true,0));
    assert(!comp_capture_radio_window_open(&w,2,true,true,true,0));
    assert(comp_capture_radio_window_open(&w,3,true,true,true,0));
    assert(!comp_capture_radio_window_open(&w,8,true,true,false,100));
    /* The radio event finishing releases admission immediately, without sleep. */
    assert(comp_capture_radio_window_open(&w,8,true,true,false,15000));
    assert(comp_capture_radio_convert_open(false,true,0,2000,1000));
    assert(!comp_capture_radio_convert_open(true,true,UINT32_MAX,1400,1000));
    assert(!comp_capture_radio_convert_open(true,false,3500,1400,1000));
    assert(comp_capture_radio_convert_open(true,false,3501,1400,1000));
    assert(comp_capture_radio_convert_open(true,true,0,1300,1000));
    assert(comp_capture_radio_convert_open(true,true,0,300,1000));
    assert(!comp_capture_radio_convert_open(true,true,0,301,1000));
    assert(comp_capture_radio_convert_open(true,true,0,0,1000));
    assert(comp_capture_radio_convert_open(true,true,0,2001,1000));
    assert(comp_capture_radio_convert_open(true,true,0,1000,0));
    assert(comp_capture_radio_convert_open(true,true,0,1000,UINT32_MAX));
    /* Real DMA boundaries: codec has 2ms, other foreground work retains 4ms.
     * A queued DMA event or unpublished hardware transition always wins. */
    assert(COMP_V11_CAPTURE_ENCODE_GUARD_MS==2u);
    assert(COMP_V11_CAPTURE_IO_GUARD_MS==4u);
    assert(!comp_v11_capture_encode_window_open(768,3840,1,false));
    assert(comp_v11_capture_encode_window_open(769,3840,1,false));
    assert(!comp_v11_capture_guarded_window_open(1536,3840,1,false,4));
    assert(comp_v11_capture_guarded_window_open(1537,3840,1,false,4));
    assert(comp_v11_capture_encode_window_open(4609,3840,0,false));
    assert(!comp_v11_capture_encode_window_open(4609,3840,0,true));
    assert(!comp_v11_capture_encode_window_open(4609,3840,1,false));
    assert(!comp_v11_capture_guarded_window_open(4609,3840,0,false,11));
    puts("capture radio quiet-window boundaries, wrap, query failure and bounded fallback passed");
    return 0;
}
