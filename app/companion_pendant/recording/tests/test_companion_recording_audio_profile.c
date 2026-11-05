#include "../companion_recording_audio_profile.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do{if(!(x)){fprintf(stderr,"FAIL %d: %s\n",__LINE__,#x);return 1;}}while(0)
static void seal(uint8_t wire[96]){comp_rec_put32(wire+92u,comp_rec_crc(wire,92u));}
int main(int argc,char **argv)
{
    comp_rec_audio_profile_t p={0},decoded={0};uint8_t wire[96],bad[96];
    p.output=3u;p.filtered_mask=3u;p.gain_q15=32768u;p.delay_q8=128;p.right_gain_q15=32768u;
    p.firmware_version=0x00010200u;p.decimation=96u;
    memset(p.firmware_source,0x5a,20u);memset(p.calibration_sha256,0x83,32u);
    CHECK(comp_rec_audio_profile_encode(&p,wire));CHECK(comp_rec_audio_profile_decode(wire,96u,&decoded));
    CHECK(decoded.output==3u&&decoded.delay_q8==128&&decoded.firmware_version==p.firmware_version);
    for(unsigned i=0;i<96u;i++)for(unsigned bit=0;bit<8u;bit++) {
        memcpy(bad,wire,96u);bad[i]^=(uint8_t)(1u<<bit);CHECK(!comp_rec_audio_profile_decode(bad,96u,&decoded));
    }
    for(unsigned n=0;n<96u;n++)CHECK(!comp_rec_audio_profile_decode(wire,n,&decoded));
    unsigned offsets[]={7u,8u,9u,10u,11u,80u,82u,83u,84u,86u};
    unsigned values[]={4u,1u,1u,8u,1u,65u,2u,2u,2u,1u};
    for(unsigned i=0;i<sizeof(offsets)/sizeof(offsets[0]);i++){
        memcpy(bad,wire,96u);bad[offsets[i]]=(uint8_t)values[i];seal(bad);CHECK(!comp_rec_audio_profile_decode(bad,96u,&decoded));
    }
    memcpy(bad,wire,96u);memset(bad+24u,0,20u);seal(bad);CHECK(!comp_rec_audio_profile_decode(bad,96u,&decoded));
    memcpy(bad,wire,96u);memset(bad+44u,0,32u);seal(bad);CHECK(!comp_rec_audio_profile_decode(bad,96u,&decoded));
    memcpy(bad,wire,96u);comp_rec_put32(bad+12u,0u);seal(bad);CHECK(!comp_rec_audio_profile_decode(bad,96u,&decoded));
    memcpy(bad,wire,96u);comp_rec_put32(bad+76u,8000u);seal(bad);CHECK(!comp_rec_audio_profile_decode(bad,96u,&decoded));
    p.output=0u;p.filtered_mask=1u;p.delay_q8=0;memset(p.calibration_sha256,0,32u);
    CHECK(comp_rec_audio_profile_valid(&p));p.recorder_profile=1u;CHECK(comp_rec_audio_profile_valid(&p));
    p.inversion_flags=4u;CHECK(!comp_rec_audio_profile_valid(&p));
    CHECK(argc==2);FILE *file=fopen(argv[1],"wb");CHECK(file);CHECK(fwrite(wire,1,96u,file)==96u);CHECK(fclose(file)==0);
    puts("PASS_APM1_C_SOFTWARE_ONLY: exact96B golden, all single-bit/short inputs refused, canonical parameter/source/calibration guards, old baseline represented without invented calibration");return 0;
}
