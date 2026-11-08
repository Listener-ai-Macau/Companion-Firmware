#include "companion_range_reclaim.h"

enum {JOURNAL=1,HASH,INTENT_BODY,INTENT_VERIFY,INTENT_COMMIT,INTENT_DURABLE,
      ERASE,ERASE_VERIFY,DONE_PROGRAM,DONE_VERIFY,TERMINAL};
static const uint8_t zero[4]={0u,0u,0u,0u};
static uint32_t record_address(const comp_range_reclaim_t *w)
{return w->journal_address+32u+(uint32_t)w->record_index*32u;}
static bool same_plan(const comp_range_plan_t *a,const comp_range_plan_t *b)
{
    return a->recording_id==b->recording_id&&a->request_nonce==b->request_nonce&&
        a->descriptor_binding==b->descriptor_binding&&a->first_sector==b->first_sector&&
        a->end_sector==b->end_sector&&a->slot==b->slot;
}
static comp_segment_result_t terminal(comp_range_reclaim_t *w,comp_segment_result_t r)
{w->phase=TERMINAL;w->result=r;return r;}
static bool outside(uint32_t at,uint32_t bytes,uint32_t base,uint32_t size)
{return at+bytes<=base||base+size<=at;}
comp_segment_result_t comp_range_reclaim_begin(comp_range_reclaim_t *w,
    const comp_segment_port_t *port,const comp_segment_entry_t *e,uint32_t base,
    uint32_t journal,uint32_t serial,uint32_t page,uint8_t index,
    const comp_range_plan_t *plan,const uint8_t proof[32],uint8_t scratch[256])
{
    uint32_t begin,end;
    comp_range_plan_t expected;
    if(!w||!port||!port->read||!port->program||!port->erase_step||!e||!plan||!proof||!scratch||
       index>=COMP_RANGE_JOURNAL_RECORDS||journal%256u||journal>UINT32_MAX-256u||
       base%4096u||base>UINT32_MAX-e->extent_offset||
       e->reserved_bytes>UINT32_MAX-base-e->extent_offset||
       !outside(journal,256u,base+e->extent_offset,e->reserved_bytes)||
       !comp_range_plan(e,plan->slot,plan->first_sector,plan->end_sector,
                        plan->request_nonce,&expected,&begin,&end)||!same_plan(plan,&expected))
        return COMP_SEG_BAD_ARGUMENT;
    if(w->phase)return COMP_SEG_BAD_STATE; /* no abandonment of a live owner */
    memset(w,0,sizeof(*w));w->port=*port;w->entry=e;w->plan=*plan;w->data_base=base;
    w->journal_address=journal;w->bank_serial=serial;w->page_index=page;w->record_index=index;
    w->encoded_begin=begin;w->encoded_end=end;w->hash_cursor=begin;w->scratch=scratch;
    memcpy(w->expected_sha,proof,32u);w->phase=JOURNAL;w->result=COMP_SEG_PENDING;
    return COMP_SEG_PENDING;
}
comp_segment_result_t comp_range_reclaim_next_io(const comp_range_reclaim_t *w,comp_segment_io_t *io)
{
    if(!w||!io||!w->phase)return COMP_SEG_BAD_ARGUMENT;
    *io=(comp_segment_io_t){0u,0u,COMP_SEG_IO_NONE};
    uint32_t at=record_address(w);
    switch(w->phase){
    case JOURNAL:*io=(comp_segment_io_t){w->journal_address,256u,COMP_SEG_IO_READ};break;
    case HASH:*io=(comp_segment_io_t){w->data_base+w->entry->extent_offset+
        (1u+w->hash_cursor/248u)*256u,256u,COMP_SEG_IO_READ};break;
    case INTENT_BODY:*io=(comp_segment_io_t){at,24u,COMP_SEG_IO_PROGRAM};break;
    case INTENT_VERIFY:case INTENT_DURABLE:case DONE_VERIFY:
        *io=(comp_segment_io_t){at,32u,COMP_SEG_IO_READ};break;
    case INTENT_COMMIT:*io=(comp_segment_io_t){at+28u,4u,COMP_SEG_IO_PROGRAM};break;
    case ERASE:*io=(comp_segment_io_t){w->data_base+w->entry->extent_offset+w->erase_cursor,
        (uint32_t)w->plan.end_sector*4096u-w->erase_cursor,COMP_SEG_IO_ERASE};break;
    case ERASE_VERIFY:*io=(comp_segment_io_t){w->data_base+w->entry->extent_offset+w->erase_cursor,
        256u,COMP_SEG_IO_READ};break;
    case DONE_PROGRAM:*io=(comp_segment_io_t){at+24u,4u,COMP_SEG_IO_PROGRAM};break;
    case TERMINAL:return w->result;
    default:return COMP_SEG_BAD_STATE;
    }
    return COMP_SEG_OK;
}
static comp_segment_result_t audio_read(void *v,uint32_t at,uint8_t *p,uint32_t n)
{
    comp_range_reclaim_t *w=v;
    return w->port.read(w->port.context,at,p,n)?COMP_SEG_OK:COMP_SEG_IO_ERROR;
}
static void start_erase(comp_range_reclaim_t *w)
{w->erase_cursor=(uint32_t)w->plan.first_sector*4096u;w->phase=ERASE;}
comp_segment_result_t comp_range_reclaim_poll(comp_range_reclaim_t *w)
{
    comp_segment_io_t io;
    if(!w||!w->phase)return COMP_SEG_BAD_ARGUMENT;
    if(w->phase==TERMINAL)return w->result;
    if(!comp_range_plan_matches(&w->plan,w->entry,w->plan.slot))return terminal(w,COMP_SEG_BAD_STATE);
    if(comp_range_reclaim_next_io(w,&io)!=COMP_SEG_OK)return terminal(w,COMP_SEG_BAD_STATE);
    comp_range_plan_t decoded;
    comp_range_journal_state_t state;
    uint32_t done=0u;
    switch(w->phase){
    case JOURNAL:
        if(!w->port.read(w->port.context,io.address,w->scratch,io.bytes))return terminal(w,COMP_SEG_IO_ERROR);
        if(comp_range_journal_header_decode(w->scratch,w->entry->descriptor.device_uid,
            w->entry->descriptor.format_epoch,w->bank_serial,w->page_index)!=COMP_RANGE_DONE)
            return terminal(w,COMP_SEG_CORRUPT);
        memcpy(w->header,w->scratch,32u);
        state=comp_range_journal_record_decode(w->scratch+32u+(uint32_t)w->record_index*32u,
            w->header,w->record_index,&decoded);
        if(state==COMP_RANGE_EMPTY){companion_sha256_init(&w->sha);w->phase=HASH;break;}
        if((state!=COMP_RANGE_PENDING&&state!=COMP_RANGE_DONE)||!same_plan(&decoded,&w->plan))
            return terminal(w,COMP_SEG_CORRUPT);
        if(state==COMP_RANGE_DONE)return terminal(w,COMP_SEG_OK); /* exact durable replay */
        start_erase(w);break; /* committed intent already authorized this range */
    case HASH:{
        const comp_segment_audio_port_t port={audio_read,NULL,w};uint8_t length=0u;
        comp_segment_result_t r=comp_segment_audio_read_page(&port,w->entry,w->data_base,
            w->hash_cursor/248u,w->scratch,&length);
        if(r!=COMP_SEG_OK)return terminal(w,r);
        const uint32_t left=w->encoded_end-w->hash_cursor;
        const uint32_t take=left<248u?left:248u;
        if(length!=take)return terminal(w,COMP_SEG_CORRUPT);
        companion_sha256_update(&w->sha,w->scratch,take);w->hash_cursor+=take;
        if(w->hash_cursor==w->encoded_end){
            uint8_t actual[32];companion_sha256_final(&w->sha,actual);
            if(memcmp(actual,w->expected_sha,32u))return terminal(w,COMP_SEG_BAD_ARGUMENT);
            if(!comp_range_journal_record_prepare(w->record,w->header,w->record_index,&w->plan))
                return terminal(w,COMP_SEG_BAD_STATE);
            w->phase=INTENT_BODY;
        }
        break;}
    case INTENT_BODY:
        if(!w->port.program(w->port.context,io.address,w->record,io.bytes))return terminal(w,COMP_SEG_IO_ERROR);
        w->phase=INTENT_VERIFY;break;
    case INTENT_VERIFY:
        if(!w->port.read(w->port.context,io.address,w->scratch,io.bytes))return terminal(w,COMP_SEG_IO_ERROR);
        if(memcmp(w->scratch,w->record,32u))return terminal(w,COMP_SEG_CORRUPT);
        w->phase=INTENT_COMMIT;break;
    case INTENT_COMMIT:case DONE_PROGRAM:
        if(!w->port.program(w->port.context,io.address,zero,4u))return terminal(w,COMP_SEG_IO_ERROR);
        w->phase=w->phase==INTENT_COMMIT?INTENT_DURABLE:DONE_VERIFY;break;
    case INTENT_DURABLE:case DONE_VERIFY:
        if(!w->port.read(w->port.context,io.address,w->scratch,io.bytes))return terminal(w,COMP_SEG_IO_ERROR);
        state=comp_range_journal_record_decode(w->scratch,w->header,w->record_index,&decoded);
        if(state!=(w->phase==INTENT_DURABLE?COMP_RANGE_PENDING:COMP_RANGE_DONE)||!same_plan(&decoded,&w->plan))
            return terminal(w,COMP_SEG_CORRUPT);
        if(w->phase==DONE_VERIFY)return terminal(w,COMP_SEG_OK);
        start_erase(w);break;
    case ERASE:
        if(!w->port.erase_step(w->port.context,io.address,io.bytes,&done))return terminal(w,COMP_SEG_IO_ERROR);
        if(done%4096u||done>io.bytes)return terminal(w,COMP_SEG_CORRUPT);
        if(done){w->verify_end=w->erase_cursor+done;w->phase=ERASE_VERIFY;}
        break;
    case ERASE_VERIFY:
        if(!w->port.read(w->port.context,io.address,w->scratch,io.bytes))return terminal(w,COMP_SEG_IO_ERROR);
        if(comp_rec_not_uniform(w->scratch,256u,255u))return terminal(w,COMP_SEG_CORRUPT);
        w->erase_cursor+=256u;
        if(w->erase_cursor==w->verify_end)w->phase=
            w->erase_cursor==(uint32_t)w->plan.end_sector*4096u?DONE_PROGRAM:ERASE;
        break;
    default:return terminal(w,COMP_SEG_BAD_STATE);
    }
    return COMP_SEG_PENDING;
}
