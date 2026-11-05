/* Native visual fixture: compile the production compositor, including its
 * private status-rail painter. The retained V45 face is a provenance-labelled
 * art fixture, never a substitute generation-21 resource installation. */
#include "../companion_renderer.c"
#include <stdlib.h>
typedef struct { const char *input; const char *face; } fixture_t;
static bool fixture_read(void *ctx,const char *id,uint8_t frame[5000])
{
    fixture_t *s=ctx; char path[1024]; FILE *file=NULL; size_t n;
    const char *name=!strcmp(id,"blink_open")?"blink_open":!strcmp(id,"blink_closed")?"blink_closed":s->face;
    if(strstr(id,"recording_timeline"))return false; /* Exact wave assets are not available. */
    (void)snprintf(path,sizeof(path),"%s/%s.bin",s->input,name);
    if(fopen_s(&file,path,"rb") || !file)return false;
    n=fread(frame,1,5000,file); fclose(file); return n==5000;
}
static int save(const char *out,const char *name,const uint8_t frame[5000])
{
    char path[1024]; FILE *file=NULL; size_t n;
    (void)snprintf(path,sizeof(path),"%s/%s.bin",out,name);
    if(fopen_s(&file,path,"wb") || !file)return 1;
    n=fwrite(frame,1,5000,file); fclose(file); return n!=5000;
}
int main(int argc,char **argv)
{
    const char *families[]={"calm","curious","delighted","warm","playful","sleepy","bashful","thoughtful","focused","alert"};
    const char *cues[]={"idle","preparing","recording","saving","saved","sync","error","unavailable"};
    uint8_t frame[5000],base[5000]; char name[96];
    fixture_t fixture; comp_runtime_renderer_t renderer; comp_runtime_frame_t f;
    if(argc!=3)return 2;
    fixture.input=argv[1];
    for(unsigned family=0;family<10u;++family) {
        fixture.face=families[family]; memset(&f,0,sizeof(f));
        f.token=1; f.family=(comp_browser_family_t)family;
        f.status_packed=0x8000u | (9u<<8u) | 41u | (1u<<16);
        comp_runtime_renderer_init(&renderer,fixture_read,&fixture);
        if(!comp_runtime_renderer_render(&renderer,&f,base) || !comp_runtime_renderer_complete(&renderer,1,true))return 3;
        (void)snprintf(name,sizeof(name),"family-%s",families[family]);
        if(save(argv[2],name,base))return 4;
        f.token=2;f.kind=COMP_RUNTIME_FRAME_BLINK;f.blink_closed=true;
        if(!comp_runtime_renderer_render(&renderer,&f,frame) || !comp_runtime_renderer_complete(&renderer,2,true))return 16;
        for(unsigned eye=0;eye<2u;++eye) {
            eye_box_t original,closed;
            if(!eye_body(base,eye,&original)||!eye_body(frame,eye,&closed))return 17;
            /* A source fixture with open eyes must lose its tall black body. */
            if(original.area && closed.area>=original.area/2u)return 18;
        }
        (void)snprintf(name,sizeof(name),"family-%s-blink",families[family]);
        if(save(argv[2],name,frame))return 19;
        f.blink_closed=false;f.kind=COMP_RUNTIME_FRAME_STATUS;
        if(family!=1u)continue;
        for(unsigned cue=0;cue<8u;++cue) {
            memcpy(frame,base,5000); f.prepare_pending=cue==1u; f.recording_elapsed_seconds=83;
            f.last_result=cue==7u?COMP_RUNTIME_UNAVAILABLE:COMP_RUNTIME_OK;
            f.recording=cue==2u?DENZIC_AUDIO_RECORDING_STATE_RECORDING:
                cue==3u?DENZIC_AUDIO_RECORDING_STATE_STOPPING:
                cue==4u?DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY:
                cue==5u?DENZIC_AUDIO_RECORDING_STATE_TRANSFER_ACTIVE:
                cue==6u?DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY:DENZIC_AUDIO_RECORDING_STATE_IDLE;
            if(!status(&f,frame))return 5; /* Status-only samples do not fabricate wave art. */
            (void)snprintf(name,sizeof(name),"cue-%s",cues[cue]); if(save(argv[2],name,frame))return 6;
        }
        f.last_result=COMP_RUNTIME_OK;f.recording=DENZIC_AUDIO_RECORDING_STATE_IDLE;
        for(unsigned bucket=0;bucket<4u;++bucket) {
            f.token=10u+bucket;f.kind=COMP_RUNTIME_FRAME_HOLD;f.hold_bucket=(uint8_t)bucket;
            if(!comp_runtime_renderer_render(&renderer,&f,frame) || !comp_runtime_renderer_complete(&renderer,f.token,true))return 7;
            if(memcmp(frame+400,base+400,4600))return 8;
            (void)snprintf(name,sizeof(name),"hold-%u",bucket);if(save(argv[2],name,frame))return 9;
        }
        f.token=20;f.kind=COMP_RUNTIME_FRAME_BLINK;f.blink_closed=true;
        if(!comp_runtime_renderer_render(&renderer,&f,frame) || !comp_runtime_renderer_complete(&renderer,20,true))return 10;
        if(save(argv[2],"blink-closed",frame))return 11;
        f.token=21;f.kind=COMP_RUNTIME_FRAME_STATUS;f.status_packed++;
        if(!comp_runtime_renderer_render(&renderer,&f,frame) || !comp_runtime_renderer_complete(&renderer,21,true))return 12;
        if(save(argv[2],"blink-clock-update",frame))return 13;
        f.token=22;f.kind=COMP_RUNTIME_FRAME_BLINK;f.blink_closed=false;
        if(!comp_runtime_renderer_render(&renderer,&f,frame) || !comp_runtime_renderer_complete(&renderer,22,true))return 14;
        if(save(argv[2],"blink-open",frame))return 15;
    }
    puts("PASS_NATIVE_VISUAL_FIXTURES: production rail and compositor, retained V45 pixels; generation21 and hardware NOT_RUN");
    return 0;
}
