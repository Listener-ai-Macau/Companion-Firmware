#include "wba_segment_discard_wire.h"
static bool frame(const uint8_t *p,size_t n,uint8_t op,uint8_t status)
{
    return p&&n==COMP_DISCARD_V3_BYTES&&!memcmp(p,"CDS3",4u)&&p[4]==op&&p[5]==status&&
        comp_rec_get32(p+92u)==comp_rec_crc(p,92u);
}
bool comp_discard_v3_preview(const uint8_t *p,size_t n,uint32_t *request_id)
{
    if(!request_id||!frame(p,n,COMP_DISCARD_V3_PREVIEW,0u)||!comp_rec_get32(p+8u))return false;
    for(unsigned i=6u;i<92u;i++)if((i<8u||i>=12u)&&p[i])return false;
    *request_id=comp_rec_get32(p+8u);return true;
}
bool comp_discard_v3_encode(uint8_t out[COMP_DISCARD_V3_BYTES],uint8_t operation,uint8_t status,const comp_discard_offer_t *o)
{
    if(!out||!o||operation<COMP_DISCARD_V3_PREVIEW||operation>COMP_DISCARD_V3_CANCEL||status>COMP_DISCARD_V3_REFUSED||
       !o->request_id||!o->generation||!o->epoch||!o->session||!o->oldest_id||o->max_id<o->oldest_id||
       !o->segments||o->segments>64u||o->anchor_slot>=64u||!(o->slots&(UINT64_C(1)<<o->anchor_slot))||
       (!o->token[0]&&!o->token[1]))return false;
    if(!comp_rec_not_uniform(o->uid,12u,0u)||!comp_rec_not_uniform(o->uid,12u,255u)||
       !o->samples||o->samples%320u||!o->encoded_bytes||!o->reserved_bytes||o->reserved_bytes%4096u||
       o->last_index>=COMP_REC_V2_INDEX_EXCLUSIVE_MAX)return false;
    unsigned count=0u;for(unsigned i=0u;i<64u;i++)if(o->slots&(UINT64_C(1)<<i))count++;
    if(count!=o->segments)return false;
    memset(out,0,COMP_DISCARD_V3_BYTES);memcpy(out,"CDS3",4u);out[4]=operation;out[5]=status;
    out[6]=o->anchor_slot;out[7]=(uint8_t)o->segments;comp_rec_put32(out+8u,o->request_id);
    comp_rec_put32(out+12u,o->generation);memcpy(out+16u,o->uid,12u);comp_rec_put64(out+28u,o->epoch);
    comp_rec_put64(out+36u,o->session);comp_rec_put64(out+44u,o->slots);comp_rec_put64(out+52u,o->samples);
    comp_rec_put32(out+60u,o->oldest_id);comp_rec_put32(out+64u,o->max_id);comp_rec_put32(out+68u,o->encoded_bytes);
    comp_rec_put32(out+72u,o->reserved_bytes);comp_rec_put32(out+76u,o->started_unix_s);comp_rec_put32(out+80u,o->last_index);
    comp_rec_put32(out+84u,o->token[0]);comp_rec_put32(out+88u,o->token[1]);comp_rec_put32(out+92u,comp_rec_crc(out,92u));return true;
}
bool comp_discard_v3_decode(const uint8_t *p,size_t n,uint8_t operation,uint8_t status,comp_discard_offer_t *o)
{
    if(!o||operation<COMP_DISCARD_V3_PREVIEW||operation>COMP_DISCARD_V3_CANCEL||status>COMP_DISCARD_V3_REFUSED||
       !frame(p,n,operation,status))return false;
    comp_discard_offer_t value={0};value.anchor_slot=p[6];value.segments=p[7];value.request_id=comp_rec_get32(p+8u);
    value.generation=comp_rec_get32(p+12u);memcpy(value.uid,p+16u,12u);value.epoch=comp_rec_get64(p+28u);
    value.session=comp_rec_get64(p+36u);value.slots=comp_rec_get64(p+44u);value.samples=comp_rec_get64(p+52u);
    value.oldest_id=comp_rec_get32(p+60u);value.max_id=comp_rec_get32(p+64u);value.encoded_bytes=comp_rec_get32(p+68u);
    value.reserved_bytes=comp_rec_get32(p+72u);value.started_unix_s=comp_rec_get32(p+76u);value.last_index=comp_rec_get32(p+80u);
    value.token[0]=comp_rec_get32(p+84u);value.token[1]=comp_rec_get32(p+88u);
    uint8_t verify[COMP_DISCARD_V3_BYTES];
    if(!comp_discard_v3_encode(verify,operation,status,&value)||memcmp(verify,p,n))return false;
    *o=value;return true;
}
