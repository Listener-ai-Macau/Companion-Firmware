#include "wba_simple_package.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

/* Actual production decoder/hash/canonical authorization path with a narrow
 * digest-verifier mock. This is NOT physical PKA/signature qualification. */
static uint8_t file[COMP_WBA_SIMPLE_HEADER_BYTES+96u+8192u],xy[64]={1u};
static uint8_t expected_digest[32];
static unsigned signature_calls,read_calls;
static bool signature_allowed=true;
static comp_wba_simple_limits_t limits={0x57424143u,0x08008000u,475136u,8192u,16777216u,131072u};
static void put32(uint8_t *p,uint32_t v)
{for(unsigned i=0u;i<4u;++i)p[i]=(uint8_t)(v>>(8u*i));}
static bool verify(void *c,const uint8_t *key,const uint8_t *digest,const uint8_t *sig)
{
    (void)c;signature_calls++;
    assert(key==xy&&sig[0]==0x5au);
    assert(!memcmp(digest,expected_digest,32u));
    return signature_allowed;
}
static bool read_file(void *c,uint32_t at,uint8_t *p,size_t n)
{
    size_t size=*(const size_t*)c;read_calls++;
    if(at>size||n>size-at)return false;
    memcpy(p,file+at,n);return true;
}
static void package(uint32_t stack_pointer)
{
    memset(file,0,sizeof(file));
    uint8_t *d=file+144u;memcpy(d,"CUP3",4u);d[4]=3u;d[6]=32u;
    put32(d+8u,500u);put32(d+12u,72u);put32(d+16u,96u);
    put32(d+20u,8192u);put32(d+24u,8192u);put32(d+28u,limits.app_address);
    for(size_t i=176u;i<sizeof(file);++i)file[i]=(uint8_t)(i%251u);
    put32(file+176u,stack_pointer);put32(file+180u,0x08008009u);
    comp_wba_update_manifest_t m={0};m.schema_version=1u;m.target=1u;m.format_version=3u;
    m.target_family=COMP_WBA_UPDATE_TARGET_FAMILY_STM32WBA;m.board_target=limits.board_target;
    m.component_version=500u;m.size_bytes=(uint32_t)sizeof(file)-144u;
    m.crc32=comp_wba_update_wire_crc32(file+144u,sizeof(file)-144u);
    companion_sha256_t hash;companion_sha256_init(&hash);
    companion_sha256_update(&hash,file+144u,sizeof(file)-144u);companion_sha256_final(&hash,m.sha256);
    uint8_t sig[64]={0x5au};assert(comp_wba_update_manifest_wire_encode(&m,0x44455631u,sig,file));
    companion_sha256_init(&hash);companion_sha256_update(&hash,file,76u);
    companion_sha256_final(&hash,expected_digest);
}
int main(void)
{
#if defined(STM32WBA25xx)
    package(0x20018000u);
#else
    package(0x20020000u);
#endif
    comp_wba_simple_package_t p;
    assert(comp_wba_simple_package_open(&p,file,176u,&limits));
    assert(p.app_bytes==96u&&p.resource_bytes==8192u&&p.resource_version==72u);
    assert(comp_wba_simple_package_newer(&p,499u,71u));
    assert(!comp_wba_simple_package_newer(&p,500u,71u));
    assert(!comp_wba_simple_package_newer(&p,499u,73u));
    uint8_t scratch[256];size_t size=sizeof(file);
    comp_wba_update_p256_trust_t trust={0x44455631u,xy,verify,NULL};
    assert(comp_wba_simple_package_verify(&p,&limits,&trust,read_file,&size,scratch,sizeof(scratch)));
    assert(signature_calls==1u&&read_calls>1u);
    signature_allowed=false;read_calls=0u;
    assert(!comp_wba_simple_package_verify(&p,&limits,&trust,read_file,&size,scratch,sizeof(scratch)));
    assert(read_calls==0u);signature_allowed=true;
    file[500u]^=1u;
    assert(!comp_wba_simple_package_verify(&p,&limits,&trust,read_file,&size,scratch,sizeof(scratch)));
    file[500u]^=1u;size--;
    assert(!comp_wba_simple_package_verify(&p,&limits,&trust,read_file,&size,scratch,sizeof(scratch)));size++;
    comp_wba_simple_limits_t other=limits;other.board_target++;
    assert(!comp_wba_simple_package_open(&p,file,176u,&other));
    other=limits;other.static_bytes+=4096u;
    assert(!comp_wba_simple_package_open(&p,file,176u,&other));
    assert(!comp_wba_simple_package_open(&p,file,175u,&limits));
    file[140u]^=1u;assert(!comp_wba_simple_package_open(&p,file,176u,&limits));
    file[140u]^=1u;
    assert(comp_wba_simple_package_open(&p,file,176u,&limits));
    p.app_bytes++;
    assert(!comp_wba_simple_package_verify(&p,&limits,&trust,read_file,&size,scratch,sizeof(scratch)));
    /* Verify actual chip bounds with a newly authenticated payload each time.
     * The old WBA55 check rejects part of WBA25 SRAM1 and admits its absent
     * upper SRAM2; neither invalid vector may reach an erasing boot adapter. */
#if defined(STM32WBA25xx)
    package(0x20008008u);assert(comp_wba_simple_package_open(&p,file,176u,&limits));
    assert(comp_wba_simple_package_verify(&p,&limits,&trust,read_file,&size,scratch,sizeof(scratch)));
    package(0x20018008u);assert(comp_wba_simple_package_open(&p,file,176u,&limits));
    assert(!comp_wba_simple_package_verify(&p,&limits,&trust,read_file,&size,scratch,sizeof(scratch)));
#else
    package(0x20008008u);assert(comp_wba_simple_package_open(&p,file,176u,&limits));
    assert(!comp_wba_simple_package_verify(&p,&limits,&trust,read_file,&size,scratch,sizeof(scratch)));
    package(0x20020000u);assert(comp_wba_simple_package_open(&p,file,176u,&limits));
    assert(comp_wba_simple_package_verify(&p,&limits,&trust,read_file,&size,scratch,sizeof(scratch)));
#endif
    puts("SIMPLE_PACKAGE_DECODE_HASH_AND_GATE_PASSED_HOST_ONLY");return 0;
}
