/* Read-only wired OTA tail admission, using the product's exact media parsers.
 * Input contains CSI1 banks and CSG2 banks only; no audio or bond keys. */
#include "companion_recording_identity.h"
#include "companion_segment_catalog.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned char identity[8192],catalog[49152];
static unsigned mutations;
static uint32_t catalog_base;
static bool id_read(void *v,uint32_t at,uint8_t *p,size_t n)
{(void)v;if(at>sizeof(identity)||n>sizeof(identity)-at)return false;memcpy(p,identity+at,n);return true;}
static bool id_write(void *v,uint32_t at,const uint8_t *p,size_t n)
{(void)v;(void)at;(void)p;(void)n;mutations++;return false;}
static bool id_erase(void *v,uint32_t at)
{(void)v;(void)at;mutations++;return false;}
static bool cat_read(void *v,uint32_t at,uint8_t *p,uint32_t n)
{(void)v;if(at<catalog_base)return false;at-=catalog_base;if(at>sizeof(catalog)||n>sizeof(catalog)-at)return false;memcpy(p,catalog+at,n);return true;}
static bool cat_write(void *v,uint32_t at,const uint8_t *p,uint32_t n)
{(void)v;(void)at;(void)p;(void)n;mutations++;return false;}
static bool cat_erase(void *v,uint32_t at,uint32_t n,uint32_t *done)
{(void)v;(void)at;(void)n;(void)done;mutations++;return false;}
static int load(const char *path,unsigned char *p,size_t n)
{FILE *f=fopen(path,"rb");if(!f)return 0;int ok=fread(p,1,n,f)==n&&fgetc(f)==EOF;fclose(f);return ok;}
int main(int argc,char **argv)
{
    uint8_t uid[12];unsigned v;uint32_t base,bytes,tail;
    if(argc!=7||strlen(argv[3])!=24u)return 2;
    for(unsigned i=0;i<12u;i++){if(sscanf(argv[3]+2u*i,"%2x",&v)!=1)return 2;uid[i]=(uint8_t)v;}
    base=(uint32_t)strtoul(argv[4],NULL,0);bytes=(uint32_t)strtoul(argv[5],NULL,0);tail=(uint32_t)strtoul(argv[6],NULL,0);
    if(base%4096u||bytes%4096u||tail%4096u||base<sizeof(catalog)||base>16777216u||bytes!=16777216u-base||tail<base||tail>=base+bytes)return 3;
    if(!load(argv[1],identity,sizeof(identity))||!load(argv[2],catalog,sizeof(catalog)))return 4;
    comp_rec_identity_t id;comp_rec_identity_port_t ip={id_read,id_write,id_erase,NULL};
    if(!comp_rec_identity_mount(&id,&ip,uid)||!id.ready||!id.loaded)return 5;
    /* Keep the exact physical addresses encoded in both committed roots.
     * The bounded callback never permits a read of audio. */
    catalog_base=base-(uint32_t)sizeof(catalog);
    comp_segment_catalog_t c;comp_segment_port_t cp={cat_read,cat_write,cat_erase,NULL,0u};
    comp_segment_result_t r=comp_segment_catalog_mount_begin(&c,&cp,catalog_base,catalog_base+24576u,base,bytes,uid,id.record.format_epoch);
    unsigned polls=0;
    while(r==COMP_SEG_PENDING&&++polls<20000u)r=comp_segment_catalog_mount_poll(&c);
    if(r!=COMP_SEG_OK||!c.mounted||mutations)return 6;
    uint32_t highest=base,count=0;bool overlap=false;
    printf("{\"entries\":[");
    for(uint8_t i=0;i<64u;i++){
        comp_segment_entry_t e;r=comp_segment_catalog_read(&c,i,&e);
        if(r==COMP_SEG_NOT_FOUND)continue;
        if(r!=COMP_SEG_OK||e.extent_offset>bytes||e.reserved_bytes>bytes-e.extent_offset)return 7;
        uint32_t end=base+e.extent_offset+e.reserved_bytes;
        if(end>tail)overlap=true;
        if(end>highest)highest=end;
        printf("%s{\"start\":%u,\"end\":%u,\"state\":%u}",count?",":"",base+e.extent_offset,end,e.state);
        count++;
    }
    if(mutations)return 9;
    printf("],\"result\":\"PASS_READ_ONLY_CATALOG\",\"owners\":%u,\"highestEnd\":%u,\"tailBase\":%u,\"tailOverlaps\":%s,\"generation\":%u,\"mutations\":0}\n",count,highest,tail,overlap?"true":"false",c.generation);
    return 0;
}
