#include "wba_segment_directory.h"

static comp_segment_result_t finish(comp_wba_segment_directory_t *p,comp_segment_result_t result)
{p->result=result;p->active=false;if(result!=COMP_SEG_OK)p->bytes=0u;return result;}
comp_segment_result_t comp_wba_segment_directory_begin(comp_wba_segment_directory_t *p,
    comp_wba_segment_storage_t *s,comp_segment_catalog_t *c,const uint8_t request[16],uint8_t *out,uint16_t capacity)
{
    if(!p||!s||!c||!request||!out||capacity<24u||request[0]!=2u||
       request[1]!=COMP_SEG_DIRECTORY_COMMAND||request[2]>1u||request[3]||!comp_rec_get32(request+8u))
        return COMP_SEG_BAD_ARGUMENT;
    if(p->active||!c->mounted||c->port.context!=s)return COMP_SEG_BAD_STATE;
    uint32_t snapshot=comp_rec_get32(request+4u),start=comp_rec_get32(request+12u);
    if(!snapshot&&start)return COMP_SEG_BAD_ARGUMENT;
    if(snapshot&&snapshot!=c->generation)return COMP_SEG_STALE_SNAPSHOT;
    uint32_t total=0u;for(unsigned i=0u;i<64u;i++)if(c->visible_mask&(UINT64_C(1)<<i))total++;
    if(start>total||(total&&start==total))return COMP_SEG_BAD_ARGUMENT;
    uint8_t target=(uint8_t)(total-start>2u?2u:total-start);
    /* The GATT owner supplies the negotiated ATT value budget, not just the
     * allocated buffer. MTU247/value244 cannot carry two112B descriptors.
     * A single136B page still advances the exact same snapshot/cursor. */
    uint16_t row_bytes=request[2]?116u:112u;
    uint16_t fits=(uint16_t)((capacity-24u)/row_bytes);
    if(target&& !fits)return COMP_SEG_BAD_ARGUMENT;
    if(fits<target)target=(uint8_t)fits;
    memset(p,0,sizeof(*p));p->catalog=c;p->storage=s;p->output=out;p->capacity=capacity;
    p->snapshot=snapshot?snapshot:c->generation;p->nonce=comp_rec_get32(request+8u);
    p->start=start;p->total=total;p->target=target;p->active=true;p->result=COMP_SEG_PENDING;
    p->calendar=request[2]!=0u;
    memset(out,0,24u);return COMP_SEG_PENDING;
}
comp_segment_result_t comp_wba_segment_directory_poll(comp_wba_segment_directory_t *p)
{
    if(!p)return COMP_SEG_BAD_ARGUMENT;
    if(!p->active)return p->result;
    comp_segment_catalog_t *c=p->catalog;
    if(!c->mounted)return finish(p,COMP_SEG_BAD_STATE);
    if(c->generation!=p->snapshot)return finish(p,COMP_SEG_STALE_SNAPSHOT);
    if(c->phase)return COMP_SEG_PENDING;
    if(p->count<p->target) {
        uint32_t position=0u;uint8_t index=0u;
        for(;index<64u;index++)if(c->visible_mask&(UINT64_C(1)<<index)) {
            if(position++==p->start+p->count)break;
        }
        if(index==64u)return finish(p,COMP_SEG_CORRUPT);
        comp_segment_entry_t entry;
        comp_segment_result_t r=comp_wba_segment_storage_entry(p->storage,c,index,&entry);
        if(r==COMP_SEG_PENDING)return r;
        if(r!=COMP_SEG_OK)return finish(p,r);
        uint8_t *row=p->output+24u+(uint32_t)p->count*(p->calendar?116u:112u);
        if((entry.state!=COMP_SEG_UNSYNCED&&entry.state!=COMP_SEG_ACKED)||
           !comp_rec_v2_encode(&entry.descriptor,row,112u))
            return finish(p,COMP_SEG_CORRUPT);
        if(p->calendar)comp_rec_put32(row+112u,entry.started_unix_s);
        p->count++;return COMP_SEG_PENDING;
    }
    uint8_t *out=p->output;
    const uint16_t row_bytes=p->calendar?116u:112u;
    out[0]=2u;out[1]=p->count;comp_rec_put16(out+2u,row_bytes);
    comp_rec_put32(out+4u,p->snapshot);comp_rec_put32(out+8u,p->start);
    comp_rec_put32(out+12u,p->total);comp_rec_put32(out+16u,p->nonce);
    p->bytes=(uint16_t)(24u+(uint16_t)p->count*row_bytes);
    comp_rec_put32(out+20u,~comp_rec_crc_step(comp_rec_crc_step(UINT32_MAX,out,20u),out+24u,p->bytes-24u));
    return finish(p,COMP_SEG_OK);
}
void comp_wba_segment_directory_cancel(comp_wba_segment_directory_t *p)
{if(p){p->active=false;p->bytes=0u;p->result=COMP_SEG_BAD_STATE;}}
