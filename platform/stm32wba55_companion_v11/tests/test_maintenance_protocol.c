#include "../ble/maintenance_protocol.h"
#include <assert.h>
#include <stdio.h>
int main(void)
{
    uint8_t p[16]={0},operation=255u,response[32];uint32_t nonce=0u;
    memcpy(p,"CRM1",4u);comp_maint_put32(p+8u,91u);
    for(unsigned op=0u;op<=COMP_MAINT_AUDIO_SERVICE;op++) {
        p[4]=(uint8_t)op;comp_maint_put32(p+12u,companion_crc32(0u,p,12u));
        assert(comp_maint_request(p,16u,&operation,&nonce)&&operation==op&&nonce==91u);
        for(uint16_t n=0u;n<16u;n++)assert(!comp_maint_request(p,n,&operation,&nonce));
        for(unsigned at=0u;at<16u;at++){p[at]^=0x80u;assert(!comp_maint_request(p,16u,&operation,&nonce));p[at]^=0x80u;}
    }
    p[4]=COMP_MAINT_AUDIO_SERVICE+1u;comp_maint_put32(p+12u,companion_crc32(0u,p,12u));
    assert(!comp_maint_request(p,16u,&operation,&nonce));p[4]=COMP_MAINT_QUERY;
    p[5]=1u;comp_maint_put32(p+12u,companion_crc32(0u,p,12u));assert(!comp_maint_request(p,16u,&operation,&nonce));
    p[5]=0u;comp_maint_put32(p+8u,0u);comp_maint_put32(p+12u,companion_crc32(0u,p,12u));assert(!comp_maint_request(p,16u,&operation,&nonce));
    comp_maint_response(response,COMP_MAINT_DEFAULTS,COMP_MAINT_OK,91u,15u,2u,7u,0x12345678u,9u,91u);
    assert(!memcmp(response,"CRM1",4u)&&response[4]==2u&&response[5]==0u&&response[6]==15u&&response[7]==2u);
    assert(comp_maint_get32(response+8u)==91u&&comp_maint_get32(response+12u)==7u&&
        comp_maint_get32(response+16u)==0x12345678u&&comp_maint_get32(response+20u)==9u&&
        comp_maint_get32(response+28u)==companion_crc32(0u,response,28u));
    response[6]=0u;
    comp_maint_timing16(response,20u,0u,false,0u);
    assert(response[20]==255u&&response[21]==255u&&response[6]==0u);
    comp_maint_timing16(response,22u,1u,true,UINT32_MAX);
    assert(response[22]==255u&&response[23]==255u&&response[6]==0u);
    comp_maint_timing16(response,24u,2u,true,3u);
    assert(response[24]==3u&&response[25]==0u&&response[6]==4u);
    comp_maint_timing16(response,26u,3u,true,65534u);
    assert(response[26]==254u&&response[27]==255u&&response[6]==12u);
    puts("PASS maintenance framing: exact command/nonce/CRC/length/reserved bytes; existing32B attribute; absent/overflow timing never valid zero");return 0;
}
