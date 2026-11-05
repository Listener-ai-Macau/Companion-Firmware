#include "wba_workspace_layout.h"
#include <string.h>
static uint32_t get32(const uint8_t *p)
{return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static bool valid(const uint8_t p[64],uint32_t bytes)
{
    uint32_t crc=UINT32_MAX;
    for(size_t n=0;n<60u;n++){crc^=p[n];for(uint8_t k=0;k<8u;k++)crc=(crc>>1)^((crc&1u)?UINT32_C(0xEDB88320):0u);}
    return !memcmp(p,"CFL3",4u)&&get32(p+4u)==3u&&get32(p+8u)==64u&&
        get32(p+12u)==bytes&&get32(p+16u)==bytes&&
        get32(p+20u)==bytes+0x10000u&&get32(p+24u)==bytes+COMP_WBA_NOR_SYSTEM_BYTES&&
        get32(p+28u)==COMP_WBA_NOR_TOTAL_BYTES-bytes-COMP_WBA_NOR_SYSTEM_BYTES&&get32(p+60u)==(crc^UINT32_MAX);
}
bool comp_wba_workspace_layout_valid(comp_wba_layout_read_fn read,void *context)
{return comp_wba_workspace_layout_valid_at(read,context,COMP_WBA_NOR_UI_BYTES);}
bool comp_wba_workspace_layout_valid_at(comp_wba_layout_read_fn read,void *context,uint32_t bytes)
{
    uint8_t a[64],b[64];
    if(!read||bytes<8192u||bytes%4096u||bytes>COMP_WBA_NOR_TOTAL_BYTES-COMP_WBA_NOR_SYSTEM_BYTES||
       !read(context,bytes+0x8000u,a,sizeof(a))||
       !read(context,bytes+0x9000u,b,sizeof(b)))return false;
    bool av=valid(a,bytes),bv=valid(b,bytes);
    if(av&&bv)return !memcmp(a,b,sizeof(a));
    return av||bv;
}
