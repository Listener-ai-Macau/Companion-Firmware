#ifndef COMPANION_PET_CHAT_H
#define COMPANION_PET_CHAT_H
#include "companion_runtime.h"
#include "companion_reply_layout.h"
enum { COMP_PET_CHAT_IDLE, COMP_PET_CHAT_ASSEMBLING, COMP_PET_CHAT_PENDING,
       COMP_PET_CHAT_VISIBLE, COMP_PET_CHAT_FAILED, COMP_PET_CHAT_CANCELLED,
       COMP_PET_CHAT_RESERVING };
#define COMP_PET_CHAT_ROWS COMP_REPLY_TEXT_HEIGHT
#define COMP_PET_CHAT_STRIDE 25u
#define COMP_PET_CHAT_BYTES (COMP_PET_CHAT_ROWS*COMP_PET_CHAT_STRIDE)
void comp_pet_chat_cancel(comp_runtime_t *,bool failed);
void comp_pet_chat_service(comp_runtime_t *,uint32_t now,bool foreground_busy);
void comp_pet_chat_complete(comp_runtime_t *,const comp_runtime_frame_t *,bool visible,uint32_t visible_ms);
#endif
