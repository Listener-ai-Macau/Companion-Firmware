#include "companion_resources.h"
#include "companion_wba_resource_contract.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint32_t crc(const uint8_t *p,size_t n)
{uint32_t c=UINT32_MAX;while(n--){c^=*p++;for(unsigned k=0;k<8;k++)c=(c>>1)^((c&1u)?UINT32_C(0xEDB88320):0u);}return c^UINT32_MAX;}
int main(int argc,char **argv)
{
    if(argc!=3)return 1;
    FILE *f=fopen(argv[1],"rb"),*s=fopen(argv[2],"r");if(!f||!s)return 2;
    uint8_t *image=malloc(COMP_WBA_NOR_UI_BYTES+1u);if(!image)return 3;
    if(fread(image,1u,COMP_WBA_NOR_UI_BYTES+1u,f)!=COMP_WBA_NOR_UI_BYTES)return 4;fclose(f);
    comp_asset_store_t store;comp_runtime_resources_t r;uint8_t pixels[5000];char name[192];unsigned count=0u;
    if(!comp_asset_store_init_memory(&store,COMP_ASSET_STORAGE_HOST_STREAM,image,COMP_WBA_NOR_UI_BYTES)||
       !comp_runtime_resources_mount(&r,&store))return 5;
    while(fgets(name,sizeof(name),s)) {
        name[strcspn(name,"\r\n")]=0;if(!name[0])continue;
        if(!comp_runtime_resources_read(&r,name,pixels))return 6;count++;
    }
    fclose(s);if(count!=COMPANION_WBA_RESOURCE_STATE_COUNT)return 7;
    uint8_t *root=image+COMP_UI_ASSET_GENERATION_ROOT_A_OFFSET;root[44u]^=1u;
    uint32_t c=crc(root,124u);memcpy(root+124u,&c,4u);
    if(comp_runtime_resources_mount(&r,&store))return 8;
    free(image);printf("PASS_COMPACT_RESOURCES states=%u resource_identity_rejected=1\n",count);return 0;
}
