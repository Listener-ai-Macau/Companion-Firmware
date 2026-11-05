/* Digital codec conformance only. No microphone, target timing or ASR evidence. */
#include "companion_opus16_rt.h"
#include "companion_silk_live_fast.h"
#include "opus.h"
#include <stdio.h>
#include <stdlib.h>

static int16_t sample(unsigned kind,unsigned index,uint32_t *random)
{
    int value=0;
    *random=*random*UINT32_C(1664525)+UINT32_C(1013904223);
    switch(kind){
    case 0: value=0;break;
    case 1: value=((int)(index%89u)-44)*22;break;
    case 2: value=((int)(index%73u)-36)*350+((int)(index%29u)-14)*120;break;
    case 3: value=(int)(*random>>16)-32768;break;
    case 4: value=index%1600u<100u?30000:0;break;
    default: value=index%2u?32767:-32768;break;
    }
    return (int16_t)value;
}

int main(int argc,char **argv)
{
    if(argc!=2)return 2;
    FILE *file=fopen(argv[1],"wb");if(!file)return 3;
    unsigned total=0u;
    for(unsigned rate=0u;rate<2u;++rate){
        for(unsigned fast=0u;fast<2u;++fast){
            for(unsigned pattern=0u;pattern<6u;++pattern){
                companion_opus16_rt_t encoder={0};int16_t pcm[320];uint8_t packet[512];
                uint32_t random=UINT32_C(0x17ad7291);
                companion_silk_live_fast_set((int)fast);
                if(!companion_opus16_rt_init_rate_frame(&encoder,rate?8000u:16000u,rate?40u:20u)){
                    fprintf(stderr,"encoder init failed: rate=%u fast=%u pattern=%u encoder_bytes=%d\n",
                            rate?8000u:16000u,fast,pattern,opus_encoder_get_size(1));
                    return 4;
                }
                for(unsigned frame=0u;frame<120u;++frame){
                    for(unsigned n=0u;n<320u;++n)pcm[n]=sample(pattern,frame*320u+n,&random);
                    size_t bytes=companion_opus16_rt_encode(&encoder,pcm,320u,packet,sizeof(packet),frame==0u);
                    if(bytes==0u||encoder.frames_encoded!=frame+1u||fwrite(packet,1,bytes,file)!=bytes)return 5;
                    ++total;
                }
                companion_opus16_rt_destroy(&encoder);
            }
        }
    }
    if(fclose(file)!=0||total!=2880u)return 6;
    printf("PASS_DIGITAL_CODEC frames=%u rates=16000/20ms,8000/40ms fast_modes=0,1 patterns=6\n",total);
    return 0;
}
