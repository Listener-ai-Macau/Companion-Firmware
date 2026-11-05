/* Candidate source art goes through the production compositor; this does not
 * mount, impersonate or replace the accepted generation 21 resource bank. */
#include "../companion_renderer.c"
#include "emote_asset_pack.h"
#include <stdlib.h>

typedef struct {const char *input; const char *name;} art_fixture_t;
static bool read_art(void *ctx,const char *id,uint8_t frame[5000])
{
    art_fixture_t *a=ctx;char path[1024];FILE *file=NULL;size_t n;
    const char *name=!strcmp(id,"blink_open")?"calm-rest":
        !strcmp(id,"blink_closed")?"calm-closed":a->name;
    (void)snprintf(path,sizeof(path),"%s/%s.bin",a->input,name);
    if(fopen_s(&file,path,"rb")||!file)return false;
    n=fread(frame,1,5000,file);fclose(file);return n==5000;
}
static bool write_art(const char *out,const char *name,const uint8_t *frame)
{
    char path[1024];FILE *file=NULL;size_t n;
    (void)snprintf(path,sizeof(path),"%s/%s.bin",out,name);
    if(fopen_s(&file,path,"wb")||!file)return false;
    n=fwrite(frame,1,5000,file);fclose(file);return n==5000;
}
static bool verify_pack(const char *pack_path,const char *expected_path)
{
    static uint8_t data[131072];uint8_t actual[5000],expected[5000],scratch[256];
    comp_emote_asset_mount_t mount;comp_asset_store_t store;
    comp_emote_clip_t clips[64];comp_emote_frame_t frames[256];char strings[8192];
    comp_screen_asset_profile_t profile={200,200,25,COMP_SCREEN_PIXEL_FORMAT_MONO_1BPP_WHITE_IS_ONE_MSB};
    FILE *file=NULL,*reference=NULL;size_t size;
    if(fopen_s(&file,pack_path,"rb")||!file)return false;
    size=fread(data,1,sizeof(data),file);if(fgetc(file)!=EOF){fclose(file);return false;}fclose(file);
    if(!comp_asset_store_init_memory(&store,COMP_ASSET_STORAGE_HOST_STREAM,data,size))return false;
    if(comp_emote_asset_pack_mount(&mount,&store,&profile,clips,64,frames,256,strings,sizeof(strings),scratch,sizeof(scratch))!=COMP_EMOTE_ASSET_MOUNT_OK)return false;
    if(!comp_emote_asset_pack_verify_payload(&mount.pack,scratch,sizeof(scratch)))return false;
    if(fopen_s(&reference,expected_path,"rb")||!reference)return false;
    for(size_t i=0;i<mount.catalog.frame_count;++i) {
        if(fread(expected,1,5000,reference)!=5000||
            !comp_emote_asset_pack_read_frame(&mount.pack,&frames[i],actual,sizeof(actual))||
            memcmp(actual,expected,5000)){fclose(reference);return false;}
    }
    if(fgetc(reference)!=EOF){fclose(reference);return false;}fclose(reference);
    /* The candidate is only consumable when its payload CRC also matches. */
    if(!size)return false;
    data[size-1]^=1u;
    if(comp_emote_asset_pack_verify_payload(&mount.pack,scratch,sizeof(scratch)))return false;
    printf("PASS_CANDIDATE_CEMP_DECODE: %zu frames equal source; damaged payload rejected\n",mount.catalog.frame_count);
    return true;
}
int main(int argc,char **argv)
{
    char path[1024],name[96],blink_name[120];FILE *list=NULL;
    art_fixture_t art;comp_runtime_renderer_t renderer;comp_runtime_frame_t f;
    uint8_t source[5000],base[5000],frame[5000];unsigned count=0;
    if(argc!=5)return 2;
    if(!verify_pack(argv[3],argv[4]))return 12;
    art.input=argv[1];art.name=name;
    (void)snprintf(path,sizeof(path),"%s/frames.txt",argv[1]);
    if(fopen_s(&list,path,"r")||!list)return 3;
    while(fgets(name,sizeof(name),list)) {
        name[strcspn(name,"\r\n")]=0;
        memset(&f,0,sizeof(f));f.token=1;f.status_packed=0x8000u|(9u<<8u)|41u|(1u<<16);
        comp_runtime_renderer_init(&renderer,read_art,&art);
        if(!read_art(&art,"face",source))return 4;
        if(!comp_runtime_renderer_render(&renderer,&f,base)||
            !comp_runtime_renderer_complete(&renderer,1,true))return 5;
        if(memcmp(source+400,base+400,4600)||!write_art(argv[2],name,base))return 6;
        /* Every settled family must survive an actual production blink and
         * restore precisely, including a pre-existing playful wink. */
        if(strstr(name,"-rest")) {
            f.token=2;f.kind=COMP_RUNTIME_FRAME_BLINK;f.blink_closed=true;
            if(!comp_runtime_renderer_render(&renderer,&f,frame)||
                !comp_runtime_renderer_complete(&renderer,2,true))return 7;
            (void)snprintf(blink_name,sizeof(blink_name),"%s-blink",name);
            if(!write_art(argv[2],blink_name,frame))return 8;
            f.token=3;f.kind=COMP_RUNTIME_FRAME_BLINK;f.blink_closed=false;
            if(!comp_runtime_renderer_render(&renderer,&f,frame)||
                !comp_runtime_renderer_complete(&renderer,3,true)||memcmp(base,frame,5000))return 9;
            for(unsigned stage=0;stage<4u;++stage) {
                f.token=4u+stage;f.kind=COMP_RUNTIME_FRAME_HOLD;f.hold_bucket=(uint8_t)stage;
                if(!comp_runtime_renderer_render(&renderer,&f,frame)||
                    !comp_runtime_renderer_complete(&renderer,f.token,true)||memcmp(base+400,frame+400,4600))return 10;
            }
        }
        ++count;
    }
    fclose(list);
    printf("PASS_ART_CANDIDATE_COMPOSITION: %u source frames; native pixels, blink restore, hold preserves face; hardware NOT_RUN\n",count);
    return count?0:11;
}
