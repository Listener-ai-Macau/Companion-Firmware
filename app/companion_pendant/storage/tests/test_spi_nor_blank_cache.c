#include "../spi_nor_blank_cache.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static uint8_t page[256];
static void sector(companion_nor_blank_cache_t *c,uint32_t at)
{for(unsigned i=0u;i<16u;++i)companion_nor_blank_observe(c,at+i*256u,page,256u,true);}
int main(void)
{
 companion_nor_blank_cache_t c={0};memset(page,255,sizeof(page));
 assert(sizeof(c)==28u);
 assert(!companion_nor_blank_begin(&c,16384,4097,4096));
 assert(!companion_nor_blank_begin(&c,16384,4096,4097));
 assert(!companion_nor_blank_begin(&c,16384,4096,UINT32_MAX));
 assert(!companion_nor_blank_begin(&c,16384,4096,0));
 assert(!companion_nor_blank_begin(&c,UINT32_MAX,0,97u*4096u));
 assert(companion_nor_blank_begin(&c,16384,4096,12288));
 page[255]=0;companion_nor_blank_observe(&c,4096,page,256,true);page[255]=255;
 assert(c.read_bytes==4096&&!companion_nor_blank_known(&c,4096,1));
 companion_nor_blank_observe(&c,8192,page,256,true);
 assert(!companion_nor_blank_known(&c,8192,256));
 for(unsigned i=1u;i<16u;++i)companion_nor_blank_observe(&c,8192+i*256u,page,256,true);
 sector(&c,12288);
 assert(c.flags==COMP_NOR_BLANK_KNOWN&&c.read_bytes==12288);
 assert(companion_nor_blank_known(&c,8192,8192));
 assert(!companion_nor_blank_known(&c,4096,12288));
 companion_nor_blank_invalidate(&c,0,4096);
 assert(companion_nor_blank_known(&c,8192,8192));
 companion_nor_blank_invalidate(&c,4096,4096);
 assert(companion_nor_blank_known(&c,8192,8192));
 companion_nor_blank_invalidate(&c,8192,1);
 assert(!companion_nor_blank_known(&c,8192,1)&&companion_nor_blank_known(&c,12288,4096));
 assert(!companion_nor_blank_known(&c,12287,2));
 companion_nor_blank_invalidate(&c,16383,SIZE_MAX);
 assert(!companion_nor_blank_known(&c,12288,4096));
 assert(companion_nor_blank_begin(&c,16384,4096,8192));
 sector(&c,4096);companion_nor_blank_observe(&c,8192,page,256,true);
 companion_nor_blank_invalidate(&c,8192,1);sector(&c,8192);
 assert(companion_nor_blank_known(&c,4096,4096)&&!companion_nor_blank_known(&c,8192,4096));
 assert(companion_nor_blank_begin(&c,16384,4096,4096));
 companion_nor_blank_observe(&c,4352,page,256,true);assert(!c.flags);
 assert(companion_nor_blank_begin(&c,16384,4096,4096));
 companion_nor_blank_observe(&c,4096,page,256,false);assert(!c.flags);
 assert(companion_nor_blank_begin(&c,16384,4096,4096));
 companion_nor_blank_observe(&c,4096,page,0,true);assert(!companion_nor_blank_known(&c,4096,1));
 c.flags=0;assert(!companion_nor_blank_known(&c,4096,1));
 assert(companion_nor_blank_begin(&c,96u*4096u,0,96u*4096u));
 page[0]=0;
 for(unsigned i=0u;i<95u;++i)companion_nor_blank_observe(&c,i*4096u,page,256u,true);
 page[0]=255;sector(&c,95u*4096u);
 assert(companion_nor_blank_count(&c)==1u && companion_nor_blank_known(&c,95u*4096u,4096u));
 companion_nor_blank_invalidate(&c,96u*4096u-1u,SIZE_MAX);assert(companion_nor_blank_count(&c)==0u);
 puts("PASS sector proofs: full physical FF reads, dirty holes, local invalidation, interrupted scan, missing/error reads, bounds and probe/reset");
 return 0;
}
