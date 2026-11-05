#include "wba_simple_layout.h"
#include <stdio.h>
#define CHECK(x) do { if(!(x)) {fprintf(stderr,"FAIL erase planner line %d: %s\n",__LINE__,#x);return 1;} } while(0)
int main(void)
{
    const uint32_t top=COMP_WBA_NOR_TOTAL_BYTES,sector=4096u;
    CHECK(comp_wba_simple_payload_erase_bytes(0u,65536u,0u)==0u);
    CHECK(comp_wba_simple_payload_erase_bytes(COMP_SIMPLE_PENDING,65536u,0u)==0u);
    CHECK(comp_wba_simple_payload_erase_bytes(top,sector,0u)==0u);
    CHECK(comp_wba_simple_payload_erase_bytes(top-sector,2u*sector,0u)==0u);
    CHECK(comp_wba_simple_payload_erase_bytes(top-sector,sector,sector)==0u);
    CHECK(comp_wba_simple_payload_erase_bytes(top-sector,sector-1u,0u)==0u);
    CHECK(comp_wba_simple_payload_erase_bytes(top-sector+1u,sector,0u)==0u);
    CHECK(comp_wba_simple_payload_erase_bytes(top-65536u,65536u,1u)==0u);
    CHECK(comp_wba_simple_payload_erase_bytes(UINT32_MAX-4095u,8192u,0u)==0u);
    uint32_t cases=0;
    /* Vary BOTH physical phase and final tail. Every planned byte must be
     * owned and erased once; no sector may be skipped before programming. */
    for(uint32_t phase=0;phase<16;phase++)for(uint32_t sectors=1;sectors<=400;sectors++) {
        uint32_t base=COMP_WBA_NOR_RECORDING_BASE+phase*sector,bytes=sectors*sector,offset=0u;
        while(offset<bytes) {
            uint32_t n=comp_wba_simple_payload_erase_bytes(base,bytes,offset);
            CHECK(n==sector||n==65536u);
            CHECK(n<=bytes-offset && base+offset>=base && base+offset+n<=base+bytes);
            CHECK((base+offset)%n==0u);
            if((base+offset)%65536u==0u&&bytes-offset>=65536u)CHECK(n==65536u);
            offset+=n;
        }
        CHECK(offset==bytes);++cases;
    }
    /* Exact current joint-image rounded tail, unlike a relative-aligned mock. */
    uint32_t bytes=(1418996u+4095u)&~4095u,base=top-bytes,offset=0u,n4=0u,n64=0u;
    while(offset<bytes) {
        uint32_t n=comp_wba_simple_payload_erase_bytes(base,bytes,offset);
        CHECK(n!=0u);if(n==65536u)++n64;else ++n4;offset+=n;
    }
    CHECK(n4==11u&&n64==21u&&offset==bytes);
    printf("PASS owned erase planner: %lu physical-phase/tail cases; current claim %lu sectors + %lu blocks, no overerase\n",
           (unsigned long)cases,(unsigned long)n4,(unsigned long)n64);
    return 0;
}
