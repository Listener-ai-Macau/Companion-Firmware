#include "companion_pet_chat.h"

void comp_pet_chat_cancel(comp_runtime_t *r,bool failed)
{
    if(!r || !r->chat_caption_token)return;
    r->chat_caption_state=failed?COMP_PET_CHAT_FAILED:COMP_PET_CHAT_CANCELLED;
    r->chat_visible_token=0u;r->chat_received_rows=0u;
    ++r->revision;
}
void comp_pet_chat_service(comp_runtime_t *r,uint32_t now,bool busy)
{
    if(!r || (r->chat_caption_state!=COMP_PET_CHAT_RESERVING &&
       (r->chat_caption_state<COMP_PET_CHAT_ASSEMBLING ||
        r->chat_caption_state>COMP_PET_CHAT_VISIBLE)))return;
    if(busy || r->surface!=COMP_SCREEN_SURFACE_HOME || r->pet_play.phase ||
       (r->chat_caption_state==COMP_PET_CHAT_RESERVING &&
        (r->touch_contact || r->hold.active)) ||
       (r->status_packed&COMP_SCREEN_STATUS_UPDATING)) {
        comp_pet_chat_cancel(r,false);return;
    }
    if((int32_t)(now-r->chat_due_ms)>=0)comp_pet_chat_cancel(r,false);
}
void comp_pet_chat_complete(comp_runtime_t *r,const comp_runtime_frame_t *f,
                            bool visible,uint32_t visible_ms)
{
    if(!r || !f || !f->chat_caption_token ||
       f->chat_caption_token!=r->chat_caption_token ||
       (r->chat_caption_state!=COMP_PET_CHAT_PENDING &&
        r->chat_caption_state!=COMP_PET_CHAT_VISIBLE))return;
    if(r->surface!=COMP_SCREEN_SURFACE_HOME || f->surface!=COMP_SCREEN_SURFACE_HOME ||
       r->capture_active || r->prepare_pending || r->start_pending || r->command_pending ||
       r->stop_pending || r->menu_pending || r->pet_play.phase ||
       (r->status_packed&COMP_SCREEN_STATUS_UPDATING)) {
        comp_pet_chat_cancel(r,false);return;
    }
    if(!visible) {comp_pet_chat_cancel(r,true);return;}
    /* The user gets fifteen seconds of actual visibility. Retries or ordinary
     * pet/status refreshes do not extend this lifetime or acknowledge it early. */
    if(r->chat_caption_state==COMP_PET_CHAT_PENDING)r->chat_due_ms=visible_ms+15000u;
    r->chat_caption_state=COMP_PET_CHAT_VISIBLE;
    r->chat_visible_token=f->chat_caption_token;
}
