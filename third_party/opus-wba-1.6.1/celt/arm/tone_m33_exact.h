/* Exact three-delay covariance for the active CELT16 tone detector.
 * Original signed16 products and modulo32 sums; no analysis/quality changes.
 * Only aligned pairs are loaded as32 bits. delay1 and even delays cover the
 * existing1,2,4,8,16,32 analysis; other alignments/delays keep scalar products.
 */
#ifndef COMPANION_TONE_M33_EXACT_H
#define COMPANION_TONE_M33_EXACT_H
#if !defined(FIXED_POINT) || !defined(__ARM_FEATURE_DSP) || defined(ENABLE_QEXT)
#error This kernel requires the fixed16 ARM DSP profile without QEXT
#endif
#include <stdint.h>
#include <string.h>
#include <arm_acle.h>
_Static_assert(sizeof(opus_val16)==2u,"exact paired signed16 covariance only");
static OPUS_INLINE opus_uint32 comp_m33_tone_pair(const opus_val16*p)
{
    opus_uint32 value;
#if defined(__GNUC__)
    p=(const opus_val16*)__builtin_assume_aligned(p,4);
#endif
    memcpy(&value,p,sizeof(value));return value;
}
static OPUS_INLINE opus_uint32 comp_m33_tone_mac(opus_uint32 a,opus_uint32 b,opus_uint32 c)
{return (opus_uint32)__smlad((int16x2_t)a,(int16x2_t)b,(int32_t)c);}
static OPUS_INLINE void comp_m33_tone_covariance(const opus_val16*x,int len,int delay,
    opus_val32 *out00,opus_val32 *out01,opus_val32 *out02)
{
    opus_uint32 r00=0,r01=0,r02=0;int i=0,count=len-2*delay;
    if(!((uintptr_t)x&3u)) {
        if(delay==1) {
            for(;i+1<count;i+=2) {
                opus_uint32 a=comp_m33_tone_pair(x+i),c=comp_m33_tone_pair(x+i+2);
                opus_uint32 b=(a>>16)|(c<<16);
                r00=comp_m33_tone_mac(a,a,r00);r01=comp_m33_tone_mac(a,b,r01);r02=comp_m33_tone_mac(a,c,r02);
            }
        } else if(delay>0 && !(delay&1)) {
            for(;i+1<count;i+=2) {
                opus_uint32 a=comp_m33_tone_pair(x+i),b=comp_m33_tone_pair(x+i+delay),c=comp_m33_tone_pair(x+i+2*delay);
                r00=comp_m33_tone_mac(a,a,r00);r01=comp_m33_tone_mac(a,b,r01);r02=comp_m33_tone_mac(a,c,r02);
            }
        }
    }
    for(;i<count;++i){r00+=(opus_int32)x[i]*x[i];r01+=(opus_int32)x[i]*x[i+delay];r02+=(opus_int32)x[i]*x[i+2*delay];}
    *out00=(opus_val32)r00;*out01=(opus_val32)r01;*out02=(opus_val32)r02;
}
#endif
