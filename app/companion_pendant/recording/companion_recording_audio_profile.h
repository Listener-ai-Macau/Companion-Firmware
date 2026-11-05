#ifndef COMPANION_RECORDING_AUDIO_PROFILE_H
#define COMPANION_RECORDING_AUDIO_PROFILE_H
#include "companion_recording_wire.h"
#define COMP_REC_AUDIO_PROFILE_SCHEMA 5u
#define COMP_REC_AUDIO_PROFILE_BYTES 96u

/* APM1 is an immutable per-segment prelude after schema5's CDB1 CONFIG.
 * CRC is framing, not authentication. The descriptor's complete original
 * SHA binds this prelude and audio to UID/epoch/session/sample positions.
 * Source/calibration identities describe provenance, never acoustic success. */
typedef struct {
    uint32_t gain_q15,firmware_version;
    int16_t delay_q8;
    uint16_t right_gain_q15,decimation;
    uint8_t output,recorder_profile,filtered_mask,inversion_flags,layout,bit_order;
    uint8_t firmware_source[20],calibration_sha256[32];
} comp_rec_audio_profile_t;
static inline bool comp_rec_audio_profile_nonzero(const uint8_t *p,size_t n)
{uint8_t value=0u;for(size_t i=0u;i<n;i++)value|=p[i];return value!=0u;}
static inline bool comp_rec_audio_profile_valid(const comp_rec_audio_profile_t *p)
{
    if(!p || p->output>3u || p->recorder_profile>1u || !p->filtered_mask || p->filtered_mask>3u ||
       p->inversion_flags>7u || !p->gain_q15 || p->gain_q15>128u*32768u ||
       !p->firmware_version || !comp_rec_audio_profile_nonzero(p->firmware_source,20u) ||
       (p->decimation!=64u&&p->decimation!=96u&&p->decimation!=128u) || p->layout>1u || p->bit_order>1u)return false;
    const uint8_t required=p->output==0u?1u:p->output==1u?2u:3u;
    if((p->filtered_mask&required)!=required)return false;
    const bool calibration=comp_rec_audio_profile_nonzero(p->calibration_sha256,32u);
    if(p->output==3u)return p->recorder_profile==0u && calibration &&
        p->delay_q8>=-2048 && p->delay_q8<=2048 && p->right_gain_q15>=16384u;
    return !calibration && p->delay_q8==0 && p->right_gain_q15==32768u && !(p->inversion_flags&4u);
}
static inline bool comp_rec_audio_profile_encode(const comp_rec_audio_profile_t *p,uint8_t wire[96])
{
    if(!wire || !comp_rec_audio_profile_valid(p))return false;
    memset(wire,0,96u);memcpy(wire+2u,"APM1",4u);wire[6]=1u;
    wire[7]=p->output;wire[8]=p->recorder_profile;wire[9]=p->filtered_mask;wire[10]=p->inversion_flags;
    comp_rec_put32(wire+12u,p->gain_q15);comp_rec_put16(wire+16u,(uint16_t)p->delay_q8);
    comp_rec_put16(wire+18u,p->right_gain_q15);comp_rec_put32(wire+20u,p->firmware_version);
    memcpy(wire+24u,p->firmware_source,20u);memcpy(wire+44u,p->calibration_sha256,32u);
    comp_rec_put32(wire+76u,16000u);comp_rec_put16(wire+80u,p->decimation);
    wire[82]=p->layout;wire[83]=p->bit_order;comp_rec_put16(wire+84u,1u);
    comp_rec_put32(wire+92u,comp_rec_crc(wire,92u));return true;
}
static inline bool comp_rec_audio_profile_decode(const uint8_t *wire,size_t n,comp_rec_audio_profile_t *out)
{
    if(!wire || !out || n<96u || wire[0] || wire[1] || memcmp(wire+2u,"APM1",4u) || wire[6]!=1u || wire[11] ||
       comp_rec_get32(wire+76u)!=16000u || wire[84]!=1u || wire[85] ||
       comp_rec_get32(wire+92u)!=comp_rec_crc(wire,92u))return false;
    for(size_t i=86u;i<92u;i++)if(wire[i])return false;
    comp_rec_audio_profile_t p={0};
    p.output=wire[7];p.recorder_profile=wire[8];p.filtered_mask=wire[9];p.inversion_flags=wire[10];
    p.gain_q15=comp_rec_get32(wire+12u);p.firmware_version=comp_rec_get32(wire+20u);
    int32_t delay=(int32_t)((uint16_t)wire[16]|((uint16_t)wire[17]<<8u));
    p.delay_q8=(int16_t)(delay>=32768?delay-65536:delay);
    p.right_gain_q15=(uint16_t)((uint16_t)wire[18]|((uint16_t)wire[19]<<8u));
    p.decimation=(uint16_t)((uint16_t)wire[80]|((uint16_t)wire[81]<<8u));p.layout=wire[82];p.bit_order=wire[83];
    memcpy(p.firmware_source,wire+24u,20u);memcpy(p.calibration_sha256,wire+44u,32u);
    if(!comp_rec_audio_profile_valid(&p))return false;
    *out=p;return true;
}
#endif
