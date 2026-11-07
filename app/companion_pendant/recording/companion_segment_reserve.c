#include "companion_segment_reserve.h"
enum { FREE=0, SEARCH, COMMIT, ERASE, VERIFY, READY, FAILED, CHECK_BLANK, CANCEL_COMMIT, CANCELED };

comp_segment_result_t comp_segment_reserve_next_io(const comp_segment_reserve_t *r,comp_segment_io_t *io)
{
    if(!r||!r->catalog||!r->entry||!io)return COMP_SEG_BAD_ARGUMENT;
    const comp_segment_catalog_t *c=r->catalog;
    *io=(comp_segment_io_t){0u,0u,COMP_SEG_IO_NONE};
    if(!c->mounted||r->phase==FREE||r->phase==FAILED)return COMP_SEG_BAD_STATE;
    if(r->phase==READY||r->phase==CANCELED)return COMP_SEG_OK;
    if(r->phase==COMMIT||r->phase==CANCEL_COMMIT)return comp_segment_catalog_next_io(c,io);
    if(c->phase)return COMP_SEG_OK; /* unrelated transaction; worker yields */
    if(r->phase==SEARCH) {
        uint32_t candidate=r->generation!=c->generation?r->hint:r->candidate;
        uint8_t scan=r->generation!=c->generation?0u:r->scan;
        if(candidate>c->data_bytes||r->bytes>c->data_bytes-candidate||scan>=64u)return COMP_SEG_OK;
        comp_segment_result_t result=comp_segment_catalog_entry_io(c,scan,io);
        return result==COMP_SEG_NOT_FOUND?COMP_SEG_OK:result;
    }
    *io=(comp_segment_io_t){c->data_base+r->candidate+r->cursor,
        r->phase==ERASE?r->bytes-r->cursor:COMP_SEGMENT_PAGE_BYTES,
        r->phase==ERASE?COMP_SEG_IO_ERASE:COMP_SEG_IO_READ};
    return (r->phase==ERASE||r->phase==VERIFY||r->phase==CHECK_BLANK)?COMP_SEG_OK:COMP_SEG_BAD_STATE;
}

static comp_segment_result_t failed(comp_segment_reserve_t *r,comp_segment_result_t why)
{ r->phase=FAILED;return why; }

comp_segment_result_t comp_segment_reserve_set_search_hint(comp_segment_reserve_t *r,uint32_t hint)
{
    if(!r||!r->catalog||!r->entry)return COMP_SEG_BAD_ARGUMENT;
    if(r->phase!=SEARCH||r->scan||r->cursor||r->wrapped||r->candidate!=r->hint||r->entry->descriptor.recording_id||
       r->generation!=r->catalog->generation)return COMP_SEG_BAD_STATE;
    if(hint>=r->catalog->data_bytes||hint%COMP_SEGMENT_SECTOR_BYTES)return COMP_SEG_BAD_ARGUMENT;
    r->hint=hint;r->candidate=hint;return COMP_SEG_OK;
}

comp_segment_result_t comp_segment_reserve_cancel_poll(comp_segment_reserve_t *r)
{
    if(!r||!r->catalog||!r->entry)return COMP_SEG_BAD_ARGUMENT;
    comp_segment_catalog_t *c=r->catalog;
    if(!c->mounted||r->phase==FREE||r->phase==FAILED)return COMP_SEG_BAD_STATE;
    if(r->phase==CANCELED)return COMP_SEG_OK;
    if(r->phase==COMMIT||r->phase==CANCEL_COMMIT) {
        if(!c->phase||c->pending!=r->entry)return failed(r,COMP_SEG_BAD_STATE);
        comp_segment_result_t result=comp_segment_catalog_poll(c);
        if(result==COMP_SEG_PENDING)return result;
        if(result!=COMP_SEG_OK)return failed(r,result);
        if(r->phase==CANCEL_COMMIT){r->phase=CANCELED;return COMP_SEG_OK;}
        r->phase=CHECK_BLANK;r->cursor=0u;return COMP_SEG_PENDING;
    }
    if(r->phase==SEARCH&&!r->entry->descriptor.recording_id){r->phase=CANCELED;return COMP_SEG_OK;}
    if(c->phase)return COMP_SEG_PENDING;
    if(r->phase!=CHECK_BLANK&&r->phase!=ERASE&&r->phase!=VERIFY&&r->phase!=READY)
        return failed(r,COMP_SEG_BAD_STATE);
    /* The adapter has retired any owned physical erase. This live allocator
     * never handed the extent to a writer; dirty old bytes are not new audio.
     * Keep the durable WRITING owner until its exact tombstone commits. */
    comp_segment_result_t result=comp_segment_catalog_cancel_unwritten_begin(c,r->entry);
    if(result!=COMP_SEG_PENDING)return failed(r,result);
    r->phase=CANCEL_COMMIT;return result;
}

comp_segment_result_t comp_segment_reserve_begin(comp_segment_reserve_t *r,
    comp_segment_catalog_t *c,comp_segment_entry_t *e,uint32_t bytes,uint32_t hint)
{
    if (!r || !c || !e || !c->mounted || !bytes || bytes%4096u ||
        bytes>c->data_bytes || hint>=c->data_bytes || hint%4096u ||
        e->descriptor.recording_id || e->state!=COMP_SEG_WRITING)
        return COMP_SEG_BAD_ARGUMENT;
    /* A caller must finish or recover an earlier reservation, not reinitialize
     * this live worker to forget an in-flight erase or uncertain commit. */
    if (r->phase!=FREE) return COMP_SEG_BAD_STATE;
    memset(r,0,sizeof(*r)); r->catalog=c;r->entry=e;r->bytes=bytes;r->hint=hint;
    r->candidate=hint;r->generation=c->generation;r->phase=SEARCH;
    return COMP_SEG_PENDING;
}

comp_segment_result_t comp_segment_reserve_begin_rotated(comp_segment_reserve_t *r,
    comp_segment_catalog_t *c,comp_segment_entry_t *e,uint32_t bytes)
{
    if(!c || !c->data_bytes || c->data_bytes%COMP_SEGMENT_SECTOR_BYTES)
        return COMP_SEG_BAD_ARGUMENT;
    /* Monotonic persistent IDs distribute even short sessions and persist
     * across reset; mixing avoids a fixed stride when each session reserves
     * multiple segments. This is not a physical wear counter. */
    uint32_t x=c->next_id;
    x^=x>>16; x*=0x7feb352du; x^=x>>15; x*=0x846ca68bu; x^=x>>16;
    uint32_t hint=(x%(c->data_bytes/COMP_SEGMENT_SECTOR_BYTES))*COMP_SEGMENT_SECTOR_BYTES;
    comp_segment_result_t result=comp_segment_reserve_begin(r,c,e,bytes,hint);
    if(result==COMP_SEG_PENDING)r->align_to_gap=true;
    return result;
}

static bool move_candidate(comp_segment_reserve_t *r,uint32_t next)
{
    comp_segment_catalog_t *c=r->catalog;
    if (next>c->data_bytes || r->bytes>c->data_bytes-next) {
        if (r->wrapped || r->hint==0u) return false;
        r->wrapped=true;next=0u;
    }
    if (r->wrapped && next>=r->hint) return false;
    r->candidate=next;r->scan=0u;r->cursor=0u;return true;
}

comp_segment_result_t comp_segment_reserve_poll_scoped(comp_segment_reserve_t *r,
    comp_segment_catalog_scoped_read_fn read,void *context)
{
    if (!r || !r->catalog || !r->entry) return COMP_SEG_BAD_ARGUMENT;
    comp_segment_catalog_t *c=r->catalog;
    if (!c->mounted) return failed(r,COMP_SEG_BAD_STATE);
    if (r->phase==READY) return COMP_SEG_OK;
    if (r->phase==FAILED || r->phase==FREE) return COMP_SEG_BAD_STATE;
    if (r->phase==COMMIT) {
        comp_segment_result_t result=comp_segment_catalog_poll(c);
        if (result==COMP_SEG_PENDING) return result;
        if (result!=COMP_SEG_OK) return failed(r,result);
        r->phase=CHECK_BLANK;r->cursor=0u;return COMP_SEG_PENDING;
    }
    if (c->phase!=0u) return COMP_SEG_PENDING;
    if (r->phase==SEARCH) {
        /* Consumptions/reservations can complete during a search. Restart it
         * against the changed generation before choosing a physical range. */
        if (r->generation!=c->generation) {
            r->generation=c->generation;r->candidate=r->hint;r->wrapped=false;r->scan=0u;r->cursor=0u;
        }
        if (r->candidate>c->data_bytes || r->bytes>c->data_bytes-r->candidate) {
            if (!move_candidate(r,c->data_bytes)) return failed(r,COMP_SEG_FULL);
            return COMP_SEG_PENDING;
        }
        if (r->scan<COMP_SEGMENT_CAPACITY) {
            comp_segment_entry_t existing;
            comp_segment_result_t result=read?comp_segment_catalog_read_scoped(c,r->scan,&existing,read,context):
                comp_segment_catalog_read(c,r->scan,&existing);
            if(result==COMP_SEG_PENDING)return result;
            r->scan++;
            if (result==COMP_SEG_NOT_FOUND) return COMP_SEG_PENDING;
            if (result!=COMP_SEG_OK) return failed(r,result);
            uint32_t existing_end=existing.extent_offset+existing.reserved_bytes;
            if (r->align_to_gap && existing_end<=r->candidate && existing_end>r->cursor)
                r->cursor=existing_end;
            if (r->candidate<existing_end &&
                existing.extent_offset<r->candidate+r->bytes) {
                if (!move_candidate(r,existing.extent_offset+existing.reserved_bytes))
                    return failed(r,COMP_SEG_FULL);
            }
            return COMP_SEG_PENDING;
        }
        /* SEARCH reuses cursor as the preceding occupied end. ERASE and VERIFY
         * reset it before their first I/O; no additional SRAM state is needed. */
        if(r->align_to_gap) {
            r->candidate=r->cursor+((r->candidate-r->cursor)/r->bytes)*r->bytes;
            /* Choose an earlier whole slot in this SAME proven free gap.
             * Slot boundaries preserve its exact whole-extent capacity. Small
             * or fragmented gaps keep the original placement and 4K fallback.
             * Eight sector-aligned strides exhaust all possible 32K residues. */
            if(r->bytes>=32768u) {
                uint32_t aligned=r->candidate;
                for(unsigned i=0u;i<8u && (c->data_base+aligned)%32768u &&
                    aligned-r->cursor>=r->bytes;i++)aligned-=r->bytes;
                if((c->data_base+aligned)%32768u==0u)r->candidate=aligned;
            }
        }
        r->entry->extent_offset=r->candidate;r->entry->reserved_bytes=r->bytes;
        r->entry->descriptor.recording_id=c->next_id;
        comp_segment_result_t result=comp_segment_catalog_put_begin(c,r->entry);
        if (result!=COMP_SEG_PENDING) return failed(r,result);
        r->phase=COMMIT;return COMP_SEG_PENDING;
    }
    if (r->phase==CHECK_BLANK) {
        /* Durable WRITING already protects the complete range. Prove every
         * byte blank before skipping erase; a dirty byte takes the original
         * full erase and verification path. Read failure is never success. */
        if(read) {
            comp_segment_result_t result=read(context,c->data_base+r->candidate+r->cursor,c->page,COMP_SEGMENT_PAGE_BYTES);
            if(result==COMP_SEG_PENDING)return result;
            if(result!=COMP_SEG_OK)return failed(r,result);
        } else if (!c->port.read(c->port.context,c->data_base+r->candidate+r->cursor,
                                 c->page,COMP_SEGMENT_PAGE_BYTES)) return failed(r,COMP_SEG_IO_ERROR);
        if (comp_rec_not_uniform(c->page,COMP_SEGMENT_PAGE_BYTES,255u)) {
            r->phase=ERASE;r->cursor=0u;return COMP_SEG_PENDING;
        }
        r->cursor+=COMP_SEGMENT_PAGE_BYTES;
        if (r->cursor==r->bytes) {r->phase=READY;return COMP_SEG_OK;}
        return COMP_SEG_PENDING;
    }
    if (r->phase==ERASE) {
        uint32_t erased=0u,remaining=r->bytes-r->cursor;
        if (!c->port.erase_step(c->port.context,c->data_base+r->candidate+r->cursor,
                                remaining,&erased)) return failed(r,COMP_SEG_IO_ERROR);
        if (erased%4096u || erased>remaining) return failed(r,COMP_SEG_CORRUPT);
        r->cursor+=erased;
        if (r->cursor==r->bytes) {r->phase=VERIFY;r->cursor=0u;}
        return COMP_SEG_PENDING;
    }
    if (r->phase==VERIFY) {
        /* Reuse idle catalog scratch; no additional 256-byte RAM buffer.
         * Full-range verification also catches protected/ignored erase commands
         * that completed without modifying NOR; WIP=0 alone is not blank data. */
        if(read) {
            comp_segment_result_t result=read(context,c->data_base+r->candidate+r->cursor,c->page,COMP_SEGMENT_PAGE_BYTES);
            if(result==COMP_SEG_PENDING)return result;
            if(result!=COMP_SEG_OK)return failed(r,result);
        } else if (!c->port.read(c->port.context,c->data_base+r->candidate+r->cursor,
                                 c->page,COMP_SEGMENT_PAGE_BYTES)) return failed(r,COMP_SEG_IO_ERROR);
        if (comp_rec_not_uniform(c->page,COMP_SEGMENT_PAGE_BYTES,255u))
            return failed(r,COMP_SEG_CORRUPT);
        r->cursor+=COMP_SEGMENT_PAGE_BYTES;
        if (r->cursor==r->bytes) {r->phase=READY;return COMP_SEG_OK;}
        return COMP_SEG_PENDING;
    }
    return failed(r,COMP_SEG_BAD_STATE);
}

comp_segment_result_t comp_segment_reserve_poll(comp_segment_reserve_t *r)
{return comp_segment_reserve_poll_scoped(r,NULL,NULL);}

bool comp_segment_reserve_ready(const comp_segment_reserve_t *r)
{ return r && r->phase==READY && r->catalog && r->catalog->mounted; }

bool comp_segment_reserve_take(comp_segment_reserve_t *r,comp_segment_entry_t **out)
{
    if (!out || !comp_segment_reserve_ready(r)) return false;
    *out=r->entry;memset(r,0,sizeof(*r));return true;
}
