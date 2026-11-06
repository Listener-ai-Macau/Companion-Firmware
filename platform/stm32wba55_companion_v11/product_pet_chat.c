#include "product_app.h"
#include "companion_pet_chat.h"
#include <string.h>
#ifdef COMPANION_WBA_BLE_LINKED
#include "ble/ble_product.h"
#endif

static uint32_t get32(const uint8_t *p)
{return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static void put32(uint8_t *p,uint32_t v)
{for(unsigned i=0;i<4u;++i)p[i]=(uint8_t)(v>>(8u*i));}
static uint32_t crc32(const uint8_t *p,size_t n)
{
    uint32_t crc=~0u;
    while(n--) {crc^=*p++;for(unsigned bit=0;bit<8u;++bit)crc=(crc>>1)^((crc&1u)?0xEDB88320u:0u);}
    return ~crc;
}
/* PCS1 byte5 reports the existing admission gates, not optical failure.
 * Byte7 high nibble2 also supports bounded reservation BEGIN (PCP1 op5).
 * Low two bits are
 * the actual surface. The original state/token/visible fields stay unchanged. */
enum { BLOCK_ASSETS=1u, BLOCK_RECORDING=2u, BLOCK_SURFACE=4u,
       BLOCK_CONTACT=8u, BLOCK_FRAME=16u, BLOCK_PRESENTER=32u,
       BLOCK_UPDATING=64u, BLOCK_LINK_STORAGE=128u };
static uint8_t idle_blocks(const comp_v11_product_app_t *app)
{
    const comp_runtime_t *r=&app->runtime;
    uint8_t blocked=0u;
    if(!app->assets_ready || !app->board)blocked|=BLOCK_ASSETS;
    if((app->board && app->board->microphone.running) || r->capture_active ||
       r->prepare_pending || r->start_pending || r->stop_pending || r->command_pending ||
       r->recording==DENZIC_AUDIO_RECORDING_STATE_PENDING_START ||
       r->recording==DENZIC_AUDIO_RECORDING_STATE_RECORDING ||
       r->recording==DENZIC_AUDIO_RECORDING_STATE_STOPPING)blocked|=BLOCK_RECORDING;
    if(r->menu_pending || r->surface!=COMP_SCREEN_SURFACE_HOME || r->pet_play.phase)
        blocked|=BLOCK_SURFACE;
    if(r->touch_contact || r->hold.active)blocked|=BLOCK_CONTACT;
    if(r->frame_outstanding)blocked|=BLOCK_FRAME;
    if(r->status_packed&COMP_SCREEN_STATUS_UPDATING)blocked|=BLOCK_UPDATING;
#ifdef COMPANION_WBA_BLE_LINKED
    if(!comp_v11_ble_secured() || comp_v11_ble_storage_busy())blocked|=BLOCK_LINK_STORAGE;
#endif
    return blocked;
}
static bool idle(const comp_v11_product_app_t *app)
{return idle_blocks(app)==0u;}
bool comp_v11_product_pet_caption(comp_v11_product_app_t *app,const uint8_t *p,size_t n,uint32_t now)
{
    if(!COMPANION_WBA_SCREEN_ENABLED || !app || !p || n<12u || memcmp(p,"PCP1",4u))return false;
    const uint32_t token=get32(p+8u);
    comp_runtime_t *r=&app->runtime;
    if(!token || p[7]!=0u)return false;
    if(p[4]==4u) {
        if(n!=12u || p[5] || p[6] || token!=r->chat_caption_token)return false;
        comp_pet_chat_cancel(r,false);return true;
    }
    if(p[4]==5u) {
        if(n!=12u || p[5] || p[6])return false;
        /* Only an existing frame/presenter may drain under this reservation.
         * No staging pixels are touched until both owners have released them.
         * Foreground operations keep their original priority. */
        if(idle_blocks(app)&(uint8_t)~BLOCK_FRAME) {
            if(token==r->chat_caption_token &&
               r->chat_caption_state==COMP_PET_CHAT_RESERVING)
                comp_pet_chat_cancel(r,false);
            return false;
        }
        if(token==r->chat_caption_token &&
           r->chat_caption_state==COMP_PET_CHAT_RESERVING) {
            if((int32_t)(now-r->chat_due_ms)>=0) {
                comp_pet_chat_cancel(r,false);return false;
            }
        } else {
            if(token==r->chat_caption_token &&
               r->chat_caption_state>=COMP_PET_CHAT_ASSEMBLING &&
               r->chat_caption_state<=COMP_PET_CHAT_VISIBLE)return true;
            r->chat_caption_token=token;r->chat_visible_token=0u;
            r->chat_received_rows=0u;r->chat_caption_state=COMP_PET_CHAT_RESERVING;
            r->chat_due_ms=now+3000u;
        }
        /* Repeated polls never renew the reservation. The original assembly
         * budget starts only once the old frame is genuinely complete. */
        if(!r->frame_outstanding &&
           comp_screen_presenter_wba_ready_for_frame(&app->presenter,now)) {
            r->chat_caption_state=COMP_PET_CHAT_ASSEMBLING;
            r->chat_due_ms=now+2000u;
        }
        return true;
    }
    if(!idle(app))return false;
    uint8_t *strip=app->panel_staging+COMP_REPLY_TEXT_Y*25u;
    if(p[4]==1u) {
        if(n!=12u || p[5] || p[6] ||
           !comp_screen_presenter_wba_ready_for_frame(&app->presenter,now))return false;
        if(token==r->chat_caption_token && r->chat_caption_state>=COMP_PET_CHAT_ASSEMBLING &&
           r->chat_caption_state<=COMP_PET_CHAT_VISIBLE)return true;
        r->chat_caption_token=token;r->chat_visible_token=0u;
        r->chat_received_rows=0u;r->chat_caption_state=COMP_PET_CHAT_ASSEMBLING;
        r->chat_due_ms=now+2000u;return true;
    }
    if(token!=r->chat_caption_token || r->chat_caption_state!=COMP_PET_CHAT_ASSEMBLING ||
       (int32_t)(now-r->chat_due_ms)>=0)return false;
    if(p[4]==2u) {
        const unsigned start=p[5],count=p[6];
        if(!count || start!=r->chat_received_rows || start+count>COMP_PET_CHAT_ROWS ||
           n!=12u+count*COMP_PET_CHAT_STRIDE)return false;
        for(unsigned row=0;row<count;++row) {
            const uint8_t *line=p+12u+row*25u;
            /* Pixels outside the existing x12..187 caption region are white. */
            if(line[0]!=255u || (line[1]&0xF0u)!=0xF0u ||
               (line[23]&0x0Fu)!=0x0Fu || line[24]!=255u)return false;
        }
        memcpy(strip+start*25u,p+12u,count*25u);
        r->chat_received_rows=(uint8_t)(start+count);return true;
    }
    if(p[4]==3u) {
        if(n!=16u || p[5] || p[6] || r->chat_received_rows!=COMP_PET_CHAT_ROWS ||
           crc32(strip,COMP_PET_CHAT_BYTES)!=get32(p+12u))return false;
        r->chat_caption_state=COMP_PET_CHAT_PENDING;r->chat_due_ms=now+10000u;
        ++r->revision;return true;
    }
    return false;
}
void comp_v11_product_pet_caption_status(const comp_v11_product_app_t *app,uint8_t out[16])
{
    memset(out,0,16u);memcpy(out,"PCS1",4u);
    if(!COMPANION_WBA_SCREEN_ENABLED){out[5]=BLOCK_ASSETS;return;}
    if(!app)return;
    const comp_runtime_t *r=&app->runtime;
    out[4]=r->chat_caption_state;out[6]=r->chat_received_rows;
    out[5]=idle_blocks(app);
    if(app->assets_ready && app->board &&
       !comp_screen_presenter_wba_ready_for_frame(&app->presenter,HAL_GetTick()))
        out[5]|=BLOCK_PRESENTER;
    out[7]=(uint8_t)(0x20u|((unsigned)r->surface&3u));
    put32(out+8u,r->chat_caption_token);put32(out+12u,r->chat_visible_token);
}
bool comp_v11_product_render_pet_caption(comp_v11_product_app_t *app,
    const comp_runtime_frame_t *request,uint8_t frame[5000])
{
#if !COMPANION_WBA_SCREEN_ENABLED
    (void)app;(void)request;(void)frame;return false;
#else
    if(!request->chat_caption_token)
        return comp_runtime_renderer_render(&app->renderer,request,frame);
    /* Preserve only one small strip on this call's stack while composing the
     * new original face. The presenter buffers remain their sole owners. */
    uint8_t strip[COMP_PET_CHAT_BYTES];
    comp_runtime_t *r=&app->runtime;
    if(request->chat_caption_token!=r->chat_caption_token)return false;
    if(r->chat_caption_state==COMP_PET_CHAT_PENDING)
        memcpy(strip,frame+COMP_REPLY_TEXT_Y*25u,sizeof(strip));
    else if(r->chat_caption_state==COMP_PET_CHAT_VISIBLE &&
            r->chat_visible_token==request->chat_caption_token) {
        if(!comp_v11_product_committed_read(app,COMP_REPLY_TEXT_Y*25u,strip,sizeof(strip)))return false;
    } else return false;
    if(!comp_runtime_renderer_render(&app->renderer,request,frame))return false;
    memcpy(frame+COMP_REPLY_TEXT_Y*25u,strip,sizeof(strip));return true;
#endif
}
