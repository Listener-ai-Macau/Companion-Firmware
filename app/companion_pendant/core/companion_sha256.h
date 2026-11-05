#ifndef COMPANION_SHA256_H
#define COMPANION_SHA256_H

#include <stddef.h>
#include <stdint.h>
#include <string.h>

/* One implementation for recording receipts and signed-update verification.
 * Contexts are caller-owned; finalizing a checkpoint uses a copy. The context
 * is RAM-only and is never serialized into the recording/OTA metadata.
 * Header-local functions allow standalone native harnesses and boot builds;
 * production LTO folds their identical implementations across consumers. */
typedef struct {
    uint32_t state[8];
    uint64_t bit_count;
    uint8_t block[64];
    uint8_t block_length;
} companion_sha256_t;

static inline uint32_t companion_sha_rotr(uint32_t value, uint8_t bits)
{
    return (value >> bits) | (value << (32u - bits));
}

static inline void companion_sha_process(companion_sha256_t *hash,
                        const uint8_t block[64])
{
    static const uint32_t k[64] = {
        0x428A2F98u,0x71374491u,0xB5C0FBCFu,0xE9B5DBA5u,
        0x3956C25Bu,0x59F111F1u,0x923F82A4u,0xAB1C5ED5u,
        0xD807AA98u,0x12835B01u,0x243185BEu,0x550C7DC3u,
        0x72BE5D74u,0x80DEB1FEu,0x9BDC06A7u,0xC19BF174u,
        0xE49B69C1u,0xEFBE4786u,0x0FC19DC6u,0x240CA1CCu,
        0x2DE92C6Fu,0x4A7484AAu,0x5CB0A9DCu,0x76F988DAu,
        0x983E5152u,0xA831C66Du,0xB00327C8u,0xBF597FC7u,
        0xC6E00BF3u,0xD5A79147u,0x06CA6351u,0x14292967u,
        0x27B70A85u,0x2E1B2138u,0x4D2C6DFCu,0x53380D13u,
        0x650A7354u,0x766A0ABBu,0x81C2C92Eu,0x92722C85u,
        0xA2BFE8A1u,0xA81A664Bu,0xC24B8B70u,0xC76C51A3u,
        0xD192E819u,0xD6990624u,0xF40E3585u,0x106AA070u,
        0x19A4C116u,0x1E376C08u,0x2748774Cu,0x34B0BCB5u,
        0x391C0CB3u,0x4ED8AA4Au,0x5B9CCA4Fu,0x682E6FF3u,
        0x748F82EEu,0x78A5636Fu,0x84C87814u,0x8CC70208u,
        0x90BEFFFAu,0xA4506CEBu,0xBEF9A3F7u,0xC67178F2u,
    };
    uint32_t w[64],a,b,c,d,e,f,g,h;
    for (uint8_t i=0u;i<16u;++i)
        w[i]=((uint32_t)block[i*4u]<<24)|((uint32_t)block[i*4u+1u]<<16)|
             ((uint32_t)block[i*4u+2u]<<8)|block[i*4u+3u];
    for (uint8_t i=16u;i<64u;++i) {
        uint32_t s0=companion_sha_rotr(w[i-15u],7u)^companion_sha_rotr(w[i-15u],18u)^(w[i-15u]>>3u);
        uint32_t s1=companion_sha_rotr(w[i-2u],17u)^companion_sha_rotr(w[i-2u],19u)^(w[i-2u]>>10u);
        w[i]=w[i-16u]+s0+w[i-7u]+s1;
    }
    a=hash->state[0];b=hash->state[1];c=hash->state[2];d=hash->state[3];
    e=hash->state[4];f=hash->state[5];g=hash->state[6];h=hash->state[7];
    for(uint8_t i=0u;i<64u;++i){
        uint32_t x1=companion_sha_rotr(e,6u)^companion_sha_rotr(e,11u)^companion_sha_rotr(e,25u);
        uint32_t t1=h+x1+((e&f)^((~e)&g))+k[i]+w[i];
        uint32_t x0=companion_sha_rotr(a,2u)^companion_sha_rotr(a,13u)^companion_sha_rotr(a,22u);
        uint32_t t2=x0+((a&b)^(a&c)^(b&c));
        h=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;
    }
    hash->state[0]+=a;hash->state[1]+=b;hash->state[2]+=c;hash->state[3]+=d;
    hash->state[4]+=e;hash->state[5]+=f;hash->state[6]+=g;hash->state[7]+=h;
}

static inline void companion_sha256_init(companion_sha256_t *hash)
{
    memset(hash,0,sizeof(*hash));
    hash->state[0]=0x6A09E667u;hash->state[1]=0xBB67AE85u;
    hash->state[2]=0x3C6EF372u;hash->state[3]=0xA54FF53Au;
    hash->state[4]=0x510E527Fu;hash->state[5]=0x9B05688Cu;
    hash->state[6]=0x1F83D9ABu;hash->state[7]=0x5BE0CD19u;
}

static inline void companion_sha256_update(companion_sha256_t *hash,
                                   const uint8_t *data,size_t length)
{
    hash->bit_count+=(uint64_t)length*8u;
    while(length--){
        hash->block[hash->block_length++]=*data++;
        if(hash->block_length==64u){companion_sha_process(hash,hash->block);hash->block_length=0u;}
    }
}

static inline void companion_sha256_final(companion_sha256_t *hash,
                                  uint8_t digest[32])
{
    uint64_t bits=hash->bit_count;
    hash->block[hash->block_length++]=0x80u;
    if(hash->block_length>56u){while(hash->block_length<64u)hash->block[hash->block_length++]=0u;companion_sha_process(hash,hash->block);hash->block_length=0u;}
    while(hash->block_length<56u)hash->block[hash->block_length++]=0u;
    for(int i=7;i>=0;--i)hash->block[hash->block_length++]=(uint8_t)(bits>>((uint32_t)i*8u));
    companion_sha_process(hash,hash->block);
    for(uint8_t i=0u;i<8u;++i){digest[i*4u]=(uint8_t)(hash->state[i]>>24);digest[i*4u+1u]=(uint8_t)(hash->state[i]>>16);digest[i*4u+2u]=(uint8_t)(hash->state[i]>>8);digest[i*4u+3u]=(uint8_t)hash->state[i];}
}

#endif /* COMPANION_SHA256_H */
