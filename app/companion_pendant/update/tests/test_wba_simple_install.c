#include "wba_simple_install.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

/* Failure injection exercises the actual installer. The signature callback
 * is a digest mock: this does not qualify physical PKA or power recovery. */
#define UI 8192u
#define META 16384u
#define NOR 65536u
#define APP 9008u
#define STAGE 32768u
#define RETAINED 24576u
#define FILE_BYTES (176u+APP+UI)
static uint8_t nor[NOR],flash[16384],file[FILE_BYTES],old_header[176],key[64]={1};
static uint8_t digests[2][32];
static unsigned mutations,fail_at;
static bool signature_allowed=true;
static comp_wba_simple_install_config_t config;
static void put32(uint8_t *p,uint32_t v)
{for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(v>>(8*i));}
static bool verify(void *c,const uint8_t *k,const uint8_t *d,const uint8_t *s)
{(void)c;return signature_allowed&&k==key&&s[0]<2u&&!memcmp(d,digests[s[0]],32);}
static bool mutation(void){return ++mutations!=fail_at;}
static bool nr(void*c,uint32_t at,uint8_t*p,size_t n)
{(void)c;if(at>NOR||n>NOR-at)return false;memcpy(p,nor+at,n);return true;}
static bool ne(void*c,uint32_t at)
{(void)c;assert(!(at%4096)&&at<=NOR-4096);if(!mutation())return false;memset(nor+at,255,4096);return true;}
static bool nw(void*c,uint32_t at,const uint8_t*p,size_t n)
{(void)c;assert(at<=NOR&&n<=NOR-at);if(!mutation())return false;for(size_t i=0;i<n;i++){assert((nor[at+i]&p[i])==p[i]);nor[at+i]&=p[i];}return true;}
static bool fr(void*c,uint32_t at,uint8_t*p,size_t n)
{(void)c;at-=0x08008000u;if(at>sizeof(flash)||n>sizeof(flash)-at)return false;memcpy(p,flash+at,n);return true;}
static bool fe(void*c,uint32_t at)
{(void)c;at-=0x08008000u;assert(!(at%config.flash_page_bytes)&&at<=sizeof(flash)-config.flash_page_bytes);if(!mutation())return false;memset(flash+at,255,config.flash_page_bytes);return true;}
static bool fw(void*c,uint32_t at,const uint8_t*p,size_t n)
{(void)c;at-=0x08008000u;assert(!(at%16)&&at<=sizeof(flash)&&n<=sizeof(flash)-at);if(!mutation())return false;for(size_t i=0;i<n;i++){assert((flash[at+i]&p[i])==p[i]);flash[at+i]&=p[i];}return true;}
static void make_file(unsigned index)
{
    memset(file,0,sizeof(file));uint8_t*d=file+144;
    memcpy(d,"CUP3",4);d[4]=3;d[6]=32;
    put32(d+8,500u+index);put32(d+12,72u+index);put32(d+16,APP);
    put32(d+20,UI);put32(d+24,UI);put32(d+28,0x08008000u);
    for(size_t i=176;i<sizeof(file);i++)file[i]=(uint8_t)((i+index)%251);
    put32(file+176,0x20020000u);put32(file+180,0x08008009u);
    comp_wba_update_manifest_t m={0};m.schema_version=1;m.target=1;m.format_version=3;
    m.target_family=COMP_WBA_UPDATE_TARGET_FAMILY_STM32WBA;m.board_target=0x57424143u;
    m.component_version=500u+index;m.size_bytes=sizeof(file)-144u;
    m.crc32=comp_wba_update_wire_crc32(file+144,sizeof(file)-144);
    companion_sha256_t h;companion_sha256_init(&h);companion_sha256_update(&h,file+144,sizeof(file)-144);companion_sha256_final(&h,m.sha256);
    uint8_t sig[64]={0};sig[0]=(uint8_t)index;
    assert(comp_wba_update_manifest_wire_encode(&m,0x44455631u,sig,file));
    companion_sha256_init(&h);companion_sha256_update(&h,file,76);companion_sha256_final(&h,digests[index]);
}
static void initial(void)
{
    memset(nor,255,sizeof(nor));memset(flash,255,sizeof(flash));
    config=(comp_wba_simple_install_config_t){0};
    config.limits=(comp_wba_simple_limits_t){0x57424143u,0x08008000u,sizeof(flash),UI,NOR,META};
    config.trust=(comp_wba_update_p256_trust_t){0x44455631u,key,verify,NULL};
    config.ports=(comp_wba_simple_install_ports_t){nr,ne,nw,fr,fe,fw,NULL,NULL};
    config.current[0]=UI;config.current[1]=UI+4096;config.pending=UI+8192;
    config.flash_page_bytes=8192;config.minimum_app=500;config.minimum_resources=72;
    make_file(0);memcpy(old_header,file,176);
    memcpy(flash,file+176,APP);memcpy(nor,file+176+APP,UI);
    assert(comp_wba_simple_current_record(nor+config.current[0],file));
    mutations=fail_at=0;signature_allowed=true;
}
static void pending(void)
{
    make_file(1);memcpy(nor+STAGE,file,sizeof(file));
    assert(comp_wba_simple_pending_record(nor+config.pending,STAGE,sizeof(file),file));
}
static comp_wba_simple_boot_result_t run(void)
{
    /* Odd capacity also covers quadword alignment at each copy boundary. */
    uint8_t scratch[513];comp_wba_simple_boot_error_t error;
    return comp_wba_simple_boot_run(&config,scratch,sizeof(scratch),&error);
}
static void populate_retained(void)
{
    /* An occupied old recording extent sits outside the staging tail and
     * all metadata/static regions. Its content is unrelated to the update. */
    for(unsigned i=0u;i<4096u;i++)nor[RETAINED+i]=(uint8_t)(i*29u+7u);
}
static void assert_retained(void)
{
    for(unsigned i=0u;i<4096u;i++)assert(nor[RETAINED+i]==(uint8_t)(i*29u+7u));
}
int main(void)
{
    initial();assert(run()==COMP_SIMPLE_BOOT_CURRENT&&mutations==0);
    pending();signature_allowed=false;assert(run()==COMP_SIMPLE_BOOT_RECOVERY&&mutations==0);
    signature_allowed=true;nor[STAGE+200]^=1;
    assert(run()==COMP_SIMPLE_BOOT_CURRENT&&mutations==1);
    assert(!memcmp(old_header,nor+config.current[0]+12,176));
    initial();pending();populate_retained();assert(run()==COMP_SIMPLE_BOOT_INSTALLED);
    unsigned total=mutations;assert(!memcmp(flash,file+176,APP)&&!memcmp(nor,file+176+APP,UI));
    assert(!memcmp(nor+STAGE,file,sizeof(file)));assert_retained();assert(run()==COMP_SIMPLE_BOOT_CURRENT);
    /* Cut every mutating operation once, then re-enter with the same retained
     * package and metadata. No old image restore and no page journal. */
    for(unsigned cut=1;cut<=total;cut++) {
        initial();pending();populate_retained();fail_at=cut;assert(run()==COMP_SIMPLE_BOOT_RECOVERY);assert_retained();
        fail_at=0;assert(run()==COMP_SIMPLE_BOOT_INSTALLED);
        assert(!memcmp(flash,file+176,APP)&&!memcmp(nor,file+176+APP,UI));
        assert_retained();assert(run()==COMP_SIMPLE_BOOT_CURRENT);assert_retained();
    }
    initial();pending();nor[config.pending+192]^=1;
    assert(run()==COMP_SIMPLE_BOOT_CURRENT&&mutations==1);
    initial();pending();fail_at=2;assert(run()==COMP_SIMPLE_BOOT_RECOVERY);
    fail_at=0;nor[STAGE+200]^=1;mutations=0;
    assert(run()==COMP_SIMPLE_BOOT_RECOVERY&&mutations==0);
    initial();config.limits.metadata_bytes=0xffffffffu;
    assert(run()==COMP_SIMPLE_BOOT_RECOVERY&&mutations==0);
    /* The next target has smaller internal erase pages. This is a host
     * geometry model, not a target HAL or real WBA25 qualification. */
    initial();config.flash_page_bytes=4096u;pending();populate_retained();
#if defined(COMP_WBA_SIMPLE_ALLOW_4K_INTERNAL_FLASH) && COMP_WBA_SIMPLE_ALLOW_4K_INTERNAL_FLASH
    assert(run()==COMP_SIMPLE_BOOT_INSTALLED);unsigned small_total=mutations;
    assert(!memcmp(flash,file+176,APP)&&!memcmp(nor,file+176+APP,UI));
    assert_retained();assert(run()==COMP_SIMPLE_BOOT_CURRENT);
    for(unsigned cut=1u;cut<=small_total;++cut) {
        initial();config.flash_page_bytes=4096u;pending();populate_retained();fail_at=cut;
        assert(run()==COMP_SIMPLE_BOOT_RECOVERY);assert_retained();
        fail_at=0u;assert(run()==COMP_SIMPLE_BOOT_INSTALLED);
        assert(!memcmp(flash,file+176,APP)&&!memcmp(nor,file+176+APP,UI));
        assert_retained();assert(run()==COMP_SIMPLE_BOOT_CURRENT);
    }
    initial();config.flash_page_bytes=4096u;config.limits.app_address+=2048u;
    assert(run()==COMP_SIMPLE_BOOT_RECOVERY&&mutations==0u);
    initial();config.flash_page_bytes=4096u;config.limits.app_capacity-=2048u;
    assert(run()==COMP_SIMPLE_BOOT_RECOVERY&&mutations==0u);
    initial();config.flash_page_bytes=0u;
    assert(run()==COMP_SIMPLE_BOOT_RECOVERY&&mutations==0u);
    initial();config.flash_page_bytes=2048u;
    assert(run()==COMP_SIMPLE_BOOT_RECOVERY&&mutations==0u);
    printf("WBA25_PAGE_GEOMETRY_%u_INTERRUPTION_POINTS_HOST_ONLY\n",small_total);
#else
    assert(run()==COMP_SIMPLE_BOOT_RECOVERY&&mutations==0u);assert_retained();
#endif
    printf("SIMPLE_INSTALL_AUTH_BEFORE_ERASE_AND_%u_INTERRUPTION_POINTS_HOST_ONLY\n",total);
    return 0;
}
