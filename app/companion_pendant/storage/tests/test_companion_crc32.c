#include "companion_crc32.h"
#include "../../recording/wba_recording_crc.h"
#include <stdio.h>
#include <string.h>

/* Independent original reflected bit implementation, including nonzero
 * finalized streaming seeds. Never used as the production implementation. */
static uint32_t reference(uint32_t seed,const uint8_t *p,size_t n)
{
    uint32_t c=seed^UINT32_MAX;
    for(size_t i=0;i<n;++i){c^=p[i];for(unsigned b=0;b<8u;++b)c=(c>>1u)^((c&1u)?UINT32_C(0xedb88320):0u);}
    return c^UINT32_MAX;
}
int main(void)
{
    uint8_t data[5000];uint32_t x=UINT32_C(0xa17e089d);unsigned cases=0;
    const uint32_t seeds[]={0u,1u,UINT32_MAX,UINT32_C(0xdeadbeef)};
    if(companion_crc32(0u,(const uint8_t*)"123456789",9u)!=UINT32_C(0xcbf43926))return 1;
    for(unsigned pattern=0;pattern<4u;++pattern){
        for(size_t i=0;i<sizeof(data);++i){x^=x<<13u;x^=x>>17u;x^=x<<5u;data[i]=pattern==0?0u:pattern==1?255u:pattern==2?(uint8_t)i:(uint8_t)x;}
        for(unsigned s=0;s<4u;++s)for(size_t n=0;n<=sizeof(data);n+=(n<32u?1u:137u)){
            uint32_t want=reference(seeds[s],data,n),got=companion_crc32(seeds[s],data,n);
            if(got!=want||comp_wba_recording_crc32(seeds[s],data,(uint32_t)n)!=want)return 2;
            for(size_t step=1;step<=256u;step*=4u){uint32_t stream=seeds[s];for(size_t at=0;at<n;){size_t k=n-at<step?n-at:step;stream=companion_crc32(stream,data+at,k);at+=k;}if(stream!=want)return 3;}
            ++cases;
        }
        if(companion_crc32(0u,data,sizeof(data))!=reference(0u,data,sizeof(data)))return 4;
        uint32_t original=companion_crc32(0u,data,sizeof(data));data[237]^=4u;if(original==companion_crc32(0u,data,sizeof(data)))return 5;
    }
    printf("CRC exact bit reference, recorder wrapper, seeded chunking and corruption PASS cases=%u\n",cases);
    return 0;
}
