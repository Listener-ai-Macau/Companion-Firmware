#include "companion_segment_catalog.h"
#include <stdio.h>
#include <string.h>
enum {BANK=24576, BASE=2*BANK, DATA=65*4096, BYTES=BASE+DATA};
static uint8_t media[BYTES];static const uint8_t uid[12]={1,2,3,4,5,6,7,8,9,10,11,12};
static bool read_media(void *ctx,uint32_t at,uint8_t *out,uint32_t n)
{(void)ctx;if(at>BYTES||n>BYTES-at)return false;memcpy(out,media+at,n);return true;}
static bool program_media(void *ctx,uint32_t at,const uint8_t *p,uint32_t n)
{(void)ctx;(void)at;(void)p;(void)n;return false;}
static bool erase_media(void *ctx,uint32_t at,uint32_t n,uint32_t *done)
{(void)ctx;(void)at;(void)n;*done=0u;return false;}
static comp_segment_result_t load(const char *path,comp_segment_catalog_t *c)
{
    FILE *f=NULL;if(fopen_s(&f,path,"rb")!=0||!f)return COMP_SEG_IO_ERROR;
    size_t n=fread(media,1u,sizeof(media),f);fclose(f);if(n!=sizeof(media))return COMP_SEG_IO_ERROR;
    comp_segment_port_t p={read_media,program_media,erase_media,NULL};
    comp_segment_result_t r=comp_segment_catalog_mount_begin(c,&p,0u,BANK,BASE,DATA,uid,7u);
    for(unsigned i=0;i<20000u&&r==COMP_SEG_PENDING;i++)r=comp_segment_catalog_mount_poll(c);
    return r;
}
int main(void)
{
    comp_segment_catalog_t c;comp_segment_entry_t entry;
    comp_segment_result_t before=load(".cache/segmented-discard-20261029/candidate/legacy-before.bin",&c);
    comp_segment_result_t after=load(".cache/segmented-discard-20261029/candidate/legacy-after.bin",&c);
    if(before!=COMP_SEG_CORRUPT||after!=COMP_SEG_OK||comp_segment_catalog_read(&c,1u,&entry)!=COMP_SEG_OK||entry.descriptor.session_id!=200u) {
        printf("FAIL old reader before=%u after=%u\n",(unsigned)before,(unsigned)after);return 1;
    }
    printf("PASS_761_READER before=reject after=accept survivor=200\n");return 0;
}
