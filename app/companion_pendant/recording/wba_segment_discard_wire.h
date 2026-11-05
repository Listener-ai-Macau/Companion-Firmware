#ifndef WBA_SEGMENT_DISCARD_WIRE_H
#define WBA_SEGMENT_DISCARD_WIRE_H
#include "wba_segment_discard_control.h"
#define COMP_DISCARD_V3_BYTES 96u
enum {COMP_DISCARD_V3_PREVIEW=1,COMP_DISCARD_V3_CONFIRM=2,COMP_DISCARD_V3_CANCEL=3};
enum {COMP_DISCARD_V3_OFFER=0,COMP_DISCARD_V3_PENDING=1,COMP_DISCARD_V3_COMPLETE=2,COMP_DISCARD_V3_REFUSED=3};
/* No native struct on wire; control value fits existing 96-byte characteristic. */
bool comp_discard_v3_preview(const uint8_t *,size_t,uint32_t *request_id);
bool comp_discard_v3_encode(uint8_t out[COMP_DISCARD_V3_BYTES],uint8_t operation,uint8_t status,const comp_discard_offer_t *);
bool comp_discard_v3_decode(const uint8_t *,size_t,uint8_t operation,uint8_t status,comp_discard_offer_t *);
#endif
