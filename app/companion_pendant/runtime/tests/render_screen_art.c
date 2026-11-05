/* Host exporter of the very same 200x200/5000-byte framebuffer consumed by
 * the display. Candidate source art is explicit; no generation-21 fallback.
 * Browser PNGs are lossless encodings of these bytes, never a CSS composite. */
#include "../companion_renderer.c"
#include "emote_asset_pack.h"
#include <stdlib.h>

typedef struct { const char *input, *name; unsigned wave; } candidate_t;
static bool load(const char *dir,const char *name,uint8_t *frame)
{
    char path[1024]; FILE *file=NULL; size_t n; int tail;
    (void)snprintf(path,sizeof(path),"%s/%s.bin",dir,name);
    if(fopen_s(&file,path,"rb")||!file)return false;
    n=fread(frame,1,5000,file);tail=fgetc(file);fclose(file);
    return n==5000 && tail==EOF;
}
static bool source(void *ctx,const char *id,uint8_t *frame)
{
    candidate_t *c=ctx;char name[64];
    if(!strcmp(id,"blink_open"))return load(c->input,"blink_open",frame);
    if(!strcmp(id,"blink_closed"))return load(c->input,"blink_closed",frame);
    if(!strncmp(id,"recording_timeline_",19)) {
        (void)snprintf(name,sizeof(name),"candidate-wave-%u",c->wave);
        return load(c->input,name,frame);
    }
    return load(c->input,c->name,frame);
}
static bool save(const char *dir,const char *name,const uint8_t *frame)
{
    char path[1024];FILE *file=NULL;size_t n;
    (void)snprintf(path,sizeof(path),"%s/%s.bin",dir,name);
    if(fopen_s(&file,path,"wb")||!file)return false;
    n=fwrite(frame,1,5000,file);fclose(file);return n==5000;
}
static bool decode_pack(const char *pack_path,const char *expected_path)
{
    /* Host-only capacity, independent of the MCU's mount descriptors. */
    static uint8_t data[4194304];static comp_emote_clip_t clips[4096];
    static comp_emote_frame_t frames[4096];static char strings[262144];
    uint8_t actual[5000],expected[5000],scratch[256];
    comp_emote_asset_mount_t mount;comp_asset_store_t store;
    comp_screen_asset_profile_t profile={200,200,25,COMP_SCREEN_PIXEL_FORMAT_MONO_1BPP_WHITE_IS_ONE_MSB};
    FILE *file=NULL,*reference=NULL;size_t size;
    if(fopen_s(&file,pack_path,"rb")||!file)return false;
    size=fread(data,1,sizeof(data),file);
    if(fgetc(file)!=EOF){fclose(file);return false;}fclose(file);
    if(!size||!comp_asset_store_init_memory(&store,COMP_ASSET_STORAGE_HOST_STREAM,data,size))return false;
    if(comp_emote_asset_pack_mount(&mount,&store,&profile,clips,4096,frames,4096,
        strings,sizeof(strings),scratch,sizeof(scratch))!=COMP_EMOTE_ASSET_MOUNT_OK)return false;
    if(!comp_emote_asset_pack_verify_payload(&mount.pack,scratch,sizeof(scratch)))return false;
    if(fopen_s(&reference,expected_path,"rb")||!reference)return false;
    for(size_t i=0;i<mount.catalog.frame_count;++i) {
        if(fread(expected,1,5000,reference)!=5000||
           !comp_emote_asset_pack_read_frame(&mount.pack,&frames[i],actual,sizeof(actual))||
           memcmp(expected,actual,5000)){fclose(reference);return false;}
    }
    if(fgetc(reference)!=EOF){fclose(reference);return false;}fclose(reference);
    data[size-1]^=1u;
    if(comp_emote_asset_pack_verify_payload(&mount.pack,scratch,sizeof(scratch)))return false;
    printf("PASS_SCREEN_ART_CEMP_PIXELS: %zu complete frames match; corrupt payload rejected\n",mount.catalog.frame_count);
    return true;
}
int main(int argc,char **argv)
{
    char path[1024],row[256],name[128];FILE *list=NULL;
    unsigned family,cue,closed,wave,count=0;uint8_t frame[5000],base[5000],input[5000];
    candidate_t c;comp_runtime_renderer_t renderer;comp_runtime_frame_t f;
    if(argc==4&&!strcmp(argv[1],"--verify"))return decode_pack(argv[2],argv[3])?0:20;
    if(argc!=3)return 2;
    c.input=argv[1];c.name=name;
    (void)snprintf(path,sizeof(path),"%s/frames.txt",argv[1]);
    if(fopen_s(&list,path,"r")||!list)return 3;
    while(fgets(row,sizeof(row),list)) {
        if(sscanf_s(row,"%127s %u %u %u %u",name,(unsigned)sizeof(name),&family,&cue,&closed,&wave)!=5)return 4;
        memset(&f,0,sizeof(f));c.wave=wave;f.token=1;f.family=(comp_browser_family_t)family;
        f.status_packed=0x8000u|(9u<<8u)|41u|(1u<<16);
        f.recording_elapsed_seconds=83;f.prepare_pending=cue==1;
        f.recording=cue==2?DENZIC_AUDIO_RECORDING_STATE_RECORDING:
            cue==3?DENZIC_AUDIO_RECORDING_STATE_STOPPING:
            cue==4?DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY:
            cue==5?DENZIC_AUDIO_RECORDING_STATE_TRANSFER_ACTIVE:
            cue==6?DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY:DENZIC_AUDIO_RECORDING_STATE_IDLE;
        f.last_result=cue==7?COMP_RUNTIME_UNAVAILABLE:COMP_RUNTIME_OK;
        if(!load(c.input,name,input))return 5;
        /* Fail on a candidate that would be erased by the real wave window. */
        if(cue==2)for(unsigned y=172;y<196;++y)for(unsigned x=2;x<42;++x)
            if(!pixel(input,x,y))return 6;
        comp_runtime_renderer_init(&renderer,source,&c);
        if(!comp_runtime_renderer_render(&renderer,&f,base)||
           !comp_runtime_renderer_complete(&renderer,1,true))return 7;
        memcpy(frame,base,5000);
        if(closed) {
            f.token=2;f.kind=COMP_RUNTIME_FRAME_BLINK;f.blink_closed=true;
            if(!comp_runtime_renderer_render(&renderer,&f,frame)||
               !comp_runtime_renderer_complete(&renderer,2,true))return 8;
            if(!save(argv[2],name,frame))return 9;
            f.token=3;f.blink_closed=false;
            if(!comp_runtime_renderer_render(&renderer,&f,frame)||
               !comp_runtime_renderer_complete(&renderer,3,true)||memcmp(base,frame,5000))return 10;
        } else if(!save(argv[2],name,frame))return 11;
        ++count;
    }
    fclose(list);
    printf("PASS_SCREEN_ART_EXPORT: %u complete candidate framebuffers; blink restores exact scene; hardware NOT_RUN\n",count);
    return count?0:12;
}
