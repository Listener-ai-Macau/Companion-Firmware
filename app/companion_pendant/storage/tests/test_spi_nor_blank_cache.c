#include "../spi_nor_blank_cache.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(void)
{
    companion_nor_blank_cache_t c={0};uint8_t p[256];memset(p,255,sizeof(p));
    assert(sizeof(c)==16u);
    assert(!companion_nor_blank_known(&c,4096,512));
    assert(companion_nor_blank_begin(&c,8192,4096,512));
    companion_nor_blank_observe(&c,4096,p,256,true);
    assert(!companion_nor_blank_known(&c,4096,256));
    companion_nor_blank_observe(&c,4352,p,256,true);
    assert(companion_nor_blank_known(&c,4096,512));
    assert(companion_nor_blank_known(&c,4352,256));
    assert(!companion_nor_blank_known(&c,4095,512));
    assert(!companion_nor_blank_known(&c,4096,513));
    companion_nor_blank_invalidate(&c,0,4096); /* touching edge is disjoint */
    companion_nor_blank_invalidate(&c,4608,3584);
    assert(companion_nor_blank_known(&c,4096,512));
    companion_nor_blank_invalidate(&c,4095,2); /* uncertain write invalidates */
    assert(!companion_nor_blank_known(&c,4096,512));
    assert(companion_nor_blank_begin(&c,8192,4096,512));
    companion_nor_blank_observe(&c,4096,p,256,true);
    companion_nor_blank_invalidate(&c,4096,1);
    companion_nor_blank_observe(&c,4352,p,256,true);
    assert(!companion_nor_blank_known(&c,4096,512));
    assert(companion_nor_blank_begin(&c,8192,4096,512));
    companion_nor_blank_observe(&c,4352,p,256,true); /* missing first page */
    assert(!c.flags);
    assert(companion_nor_blank_begin(&c,8192,4096,256));
    companion_nor_blank_observe(&c,4096,p,256,false);
    assert(!c.flags);
    assert(companion_nor_blank_begin(&c,8192,4096,256));
    p[255]=0;companion_nor_blank_observe(&c,4096,p,256,true);assert(!c.flags);
    p[255]=255;
    assert(companion_nor_blank_begin(&c,UINT32_MAX,UINT32_MAX-255u,255));
    companion_nor_blank_observe(&c,UINT32_MAX-255u,p,255,true);
    assert(companion_nor_blank_known(&c,UINT32_MAX-255u,255));
    assert(!companion_nor_blank_known(&c,UINT32_MAX,1));
    companion_nor_blank_invalidate(&c,0,SIZE_MAX);assert(!c.flags);
    assert(!companion_nor_blank_begin(&c,8192,8192,1));
    assert(!companion_nor_blank_begin(&c,8192,4096,UINT32_MAX));
    assert(!companion_nor_blank_begin(&c,8192,4096,0));
    memset(&c,0,sizeof(c));assert(!companion_nor_blank_known(&c,4096,256));
    puts("whole-range readback, interruptions, writes, erases, endpoints and reset invalidate correctly");
    return 0;
}
