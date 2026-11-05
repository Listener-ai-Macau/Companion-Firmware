#include "companion_resources.h"
#include "companion_wba_resource_contract.h"
#include "companion_browser_interaction_contract.h"
#include "companion_renderer.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint32_t crc32(const uint8_t *data,size_t n)
{
    uint32_t c=0xffffffffu;
    while(n--){c^=*data++;for(unsigned b=0;b<8;b++)c=(c>>1)^((c&1u)?0xedb88320u:0u);}
    return c^0xffffffffu;
}
static uint8_t *load(const char *path,size_t *size)
{
    FILE *f=fopen(path,"rb");uint8_t *p;long n;
    if(!f)return NULL;if(fseek(f,0,SEEK_END)||((n=ftell(f))<1)||fseek(f,0,SEEK_SET)){fclose(f);return NULL;}
    p=(uint8_t*)malloc((size_t)n);if(!p||fread(p,1,(size_t)n,f)!=(size_t)n){free(p);fclose(f);return NULL;}
    fclose(f);*size=(size_t)n;return p;
}
int main(int argc,char **argv)
{
    size_t size=0;uint8_t *image,*bad;FILE *states;char id[160];uint8_t frame[5000];unsigned count=0;
    comp_asset_store_t store;comp_runtime_resources_t resources;
    if(argc!=3||(image=load(argv[1],&size))==NULL||(states=fopen(argv[2],"r"))==NULL)return 2;
    if(!comp_asset_store_init_memory(&store,COMP_ASSET_STORAGE_HOST_STREAM,image,size)||
       !comp_runtime_resources_mount(&resources,&store))return 3;
    while(fgets(id,sizeof(id),states)){
        id[strcspn(id,"\r\n")]=0;if(!id[0])continue;
        memset(frame,0,sizeof(frame));if(!comp_runtime_resources_read(&resources,id,frame))return 4;
        ++count;
    }
    fclose(states);
    if(count!=COMPANION_WBA_RESOURCE_STATE_COUNT)return 5;
    if(!comp_runtime_resources_read(&resources,"expression_sleepy_v0_0_hold",frame))return 6;
    {uint8_t calm[5000];if(!comp_runtime_resources_read(&resources,"expression_calm_v0_0_hold",calm)||!memcmp(calm,frame,sizeof(calm)))return 7;}
    if(comp_runtime_resources_read(&resources,"state_that_does_not_exist",frame))return 8;
    /* Real resource mount -> production renderer path, including dynamically
     * formatted default/gaze/wave/menu requests. */
    {
        comp_screen_menu_t language_menu;
        comp_screen_menu_init(&language_menu);
        comp_screen_menu_navigate_to(&language_menu,COMP_SCREEN_MENU_VIEW_BROWSER_LANGUAGE);
        const uint16_t language_rows[3]={137u,69u,103u};
        const unsigned language_values[3]={2u,1u,0u};
        for(unsigned i=0;i<3u;++i) {
            comp_screen_menu_result_t chosen=comp_screen_menu_tap(&language_menu,40u,language_rows[i]);
            if(chosen.action!=COMP_SCREEN_MENU_ACTION_LANGUAGE_CHANGED ||
               (unsigned)language_menu.language!=language_values[i])return 15;
        }
        comp_screen_menu_t paged;
        comp_screen_menu_init(&paged);
        comp_screen_menu_navigate_to(&paged,COMP_SCREEN_MENU_VIEW_BROWSER_VOICE);
        /* At the slop threshold and across a long stroke, exactly one page
         * is selected. No four-row legacy offset can leak into WBA. */
        if(!comp_screen_menu_browser_drag_from(&paged,0u,-12,12u,40u).changed || paged.home_page!=4u)return 18;
        if(comp_screen_menu_browser_drag_from(&paged,4u,-170,12u,40u).changed)return 18;
        if(!comp_screen_menu_browser_drag_from(&paged,4u,170,12u,40u).changed || paged.home_page!=0u)return 18;
        if(comp_screen_menu_browser_drag_from(&paged,0u,-11,12u,40u).changed || paged.home_page!=0u)return 18;
        paged.home_page=4u;
        if(comp_screen_menu_tap(&paged,100u,170u).changed || comp_screen_menu_tap(&paged,100u,190u).changed)return 18;
        comp_runtime_renderer_t renderer;comp_runtime_frame_t f={0};
        comp_runtime_renderer_init(&renderer,comp_runtime_resources_read,&resources);
        for(unsigned family=0;family<COMP_BROWSER_FAMILY_COUNT;++family){
            f=(comp_runtime_frame_t){0};f.token=family+1u;f.family=(comp_browser_family_t)family;
            f.gaze_x=f.gaze_y=100u;if(!comp_runtime_renderer_render(&renderer,&f,frame)||!comp_runtime_renderer_complete(&renderer,f.token,true))return 11;
            /* Unused rail pixels stay dark on the approved home surface. */
            if(frame[0]!=0u || frame[24]!=0u)return 16;
            f.token+=20u;f.kind=COMP_RUNTIME_FRAME_REACTION;f.gaze_x=199u;f.gaze_y=0u;
            if(!comp_runtime_renderer_render(&renderer,&f,frame)||!comp_runtime_renderer_complete(&renderer,f.token,true))return 12;
        }
        f.token=100u;f.kind=COMP_RUNTIME_FRAME_RECORDING_WAVE;f.recording=DENZIC_AUDIO_RECORDING_STATE_RECORDING;f.recording_wave_index=63u;
        if(!comp_runtime_renderer_render(&renderer,&f,frame)||!comp_runtime_renderer_complete(&renderer,f.token,true))return 13;
        for(unsigned locale=0;locale<3u;++locale)for(unsigned screen=0;screen<COMPANION_BROWSER_MENU_SCREEN_COUNT;++screen){
            f=(comp_runtime_frame_t){0};f.token=200u+screen+locale*20u;f.family=COMP_BROWSER_FAMILY_CALM;f.surface=COMP_SCREEN_SURFACE_MENU;
            f.menu.view=(comp_screen_menu_view_t)(COMP_SCREEN_MENU_VIEW_BROWSER_HOME+screen);f.menu.language=(comp_screen_menu_language_t)locale;
            if(!comp_runtime_renderer_render(&renderer,&f,frame)||!comp_runtime_renderer_complete(&renderer,f.token,true))return 14;
            /* Menu-only white rail keeps the same live cue positions. */
            if(frame[0]!=0xFFu || frame[24]!=0xFFu)return 17;
        }
    }
    bad=(uint8_t*)malloc(size);if(!bad)return 9;memcpy(bad,image,size);
    bad[COMP_UI_ASSET_GENERATION_ROOT_A_OFFSET+44u]^=1u;
    {uint32_t c=crc32(&bad[COMP_UI_ASSET_GENERATION_ROOT_A_OFFSET],124u);memcpy(&bad[COMP_UI_ASSET_GENERATION_ROOT_A_OFFSET+124u],&c,4u);}
    if(!comp_asset_store_init_memory(&store,COMP_ASSET_STORAGE_HOST_STREAM,bad,size)||
       comp_runtime_resources_mount(&resources,&store))return 10;
    free(bad);free(image);
    printf("PASS_WBA_PRODUCT_RESOURCES states=%u renderer_roundtrip=1\n",count);return 0;
}
