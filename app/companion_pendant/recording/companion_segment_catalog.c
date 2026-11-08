#include "companion_segment_catalog.h"
#include "companion_range_reclaim.h"

enum {
    IDLE=0, MOUNT_ROOT, MOUNT_BLANK, MOUNT_ROWS, MOUNT_PREVIOUS,
    MOUNT_FIRST, MOUNT_PAIR, MOUNT_RANGE, MOUNT_RANGE_ENTRY,
    PREFLIGHT, COMPACT_SCAN, GC_INTENT_BODY, GC_INTENT_COMMIT, GC_INTENT_VERIFY,
    GC_ERASE, ROOT_BODY, GC_READ,
    GC_BODY, GC_COMMIT, GC_VERIFY, ROOT_COMMIT, ROOT_VERIFY,
    ROW_BODY, ROW_COMMIT, ROW_VERIFY, RECLAIM, PREFLIGHT_KNOWN,
    GC_RANGE_HEADER,GC_RANGE_BODY,GC_RANGE_VERIFY,
    RANGE_PREFLIGHT,RANGE_HEADER_BODY,RANGE_HEADER_COMMIT,RANGE_HEADER_VERIFY,RANGE_RUN,
    OP_NONE=0, OP_PUT=1, OP_ACK=2, OP_RECLAIM=3, OP_FORMAT=4, OP_CANCEL=5, OP_DISCARD=6, OP_SESSION_INTENT=7, OP_COMPACT=8,OP_RANGE=9,
    NO_SLOT=255, ROOT_CRC=60, ROW_CRC=140, INTENT=224, INTENT_COMMIT=248, COMMIT=252
};
static uint32_t reclaim_bytes(const comp_segment_catalog_t *c)
{
    const comp_segment_entry_t *e=c->pending;
    /* A normal user STOP publishes SEALED|LAST|END_USER only after its last
     * accepted page committed. Its reservation proved the entire extent blank;
     * the suffix was never programmed. Erase the provenance plus data prefix,
     * rounded to physical sectors, before the same durable removal/receipt.
     * Incomplete/abnormal/intermediate/discard and rebooted ERASING entries
     * retain a full erase. No cursor or reservation-size change is persisted. */
    if(c->operation==OP_RECLAIM && e->state==COMP_SEG_ACKED &&
       e->descriptor.codec==3u &&
       e->descriptor.flags==(COMP_REC_V2_SEALED|COMP_REC_V2_LAST|
                            (COMP_REC_END_USER<<COMP_REC_V2_END_SHIFT))) {
        uint64_t pages=((uint64_t)e->descriptor.encoded_length+
                        COMP_SEGMENT_PAGE_DATA_BYTES-1u)/COMP_SEGMENT_PAGE_DATA_BYTES;
        uint64_t bytes=(pages+1u)*COMP_SEGMENT_PAGE_BYTES;
        bytes=(bytes+COMP_SEGMENT_SECTOR_BYTES-1u)/COMP_SEGMENT_SECTOR_BYTES*COMP_SEGMENT_SECTOR_BYTES;
        /* New range receivers retire whole32K prefixes. Keep the final
         * normal STOP tail in one32K command too; its unwritten suffix was
         * already proved blank inside this same exclusive reservation.
         * Legacy sub-block frontiers retain their prior sector-exact path. */
        if((c->range_end[c->index]&7u)==0u&&c->reclaim_block_sectors==8u && bytes>=16384u) {
            uint32_t skew=(c->data_base+e->extent_offset)&32767u;
            uint64_t block_end=((bytes+skew+32767u)&~UINT64_C(32767))-skew;
            if(block_end<=e->reserved_bytes)bytes=block_end;
        }
        if(bytes<e->reserved_bytes)return (uint32_t)bytes;
    }
    return e->reserved_bytes;
}
bool comp_segment_catalog_rebase_entry(const comp_segment_entry_t *e,uint32_t old_base,
    uint32_t new_base,uint32_t tail,comp_segment_entry_t *out)
{
    if(!e || !out || e->state<COMP_SEG_WRITING || e->state>COMP_SEG_ERASING ||
        old_base%4096u || new_base%4096u || tail%4096u || e->extent_offset%4096u ||
        !e->reserved_bytes || e->reserved_bytes%4096u ||
        old_base>UINT32_MAX-e->extent_offset)return false;
    uint32_t physical=old_base+e->extent_offset;
    uint32_t provenance=comp_segment_provenance_extent(e);
    if(provenance%4096u || provenance==UINT32_MAX || physical<new_base || physical>tail ||
        e->reserved_bytes>tail-physical)return false;
    comp_segment_entry_t copy=*e;copy.extent_offset=physical-new_base;
    copy.provenance_extent_plus1=provenance+1u;*out=copy;return true;
}

static bool uniform(const uint8_t *p,size_t n,uint8_t value)
{ return !comp_rec_not_uniform(p,n,value); }

static comp_segment_result_t fail(comp_segment_catalog_t *c,comp_segment_result_t r)
{
    c->phase=IDLE; c->operation=OP_NONE; c->pending=NULL;
    c->range_worker=NULL;
    /* A failed write/readback is uncertain, never permission to retry against
     * a stale RAM index. A fresh mount reconstructs durable ownership. */
    if (r==COMP_SEG_IO_ERROR || r==COMP_SEG_CORRUPT) c->mounted=false;
    c->blank_verified=false;
    return r;
}

static unsigned live_count(const comp_segment_catalog_t *c)
{
    unsigned count=0u;
    for (unsigned i=0u;i<COMP_SEGMENT_CAPACITY;i++) if (c->slots[i]!=NO_SLOT) count++;
    for(unsigned i=0u;i<COMP_SEGMENT_RECEIPT_CAPACITY;i++)if(c->receipts[i]!=NO_SLOT)count++;
    return count;
}

static uint32_t address(const comp_segment_catalog_t *c,uint8_t bank,uint8_t slot)
{ return c->banks[bank]+(uint32_t)slot*COMP_SEGMENT_PAGE_BYTES; }

static uint8_t occupied_from(const comp_segment_catalog_t *c,uint8_t index)
{while(index<COMP_SEGMENT_CAPACITY&&c->slots[index]==NO_SLOT)index++;return index;}
static uint8_t gc_from(const comp_segment_catalog_t *c,uint8_t index)
{
    index=occupied_from(c,index);
    while(index<64u+COMP_SEGMENT_RECEIPT_CAPACITY&&index>=64u&&
          c->receipts[(c->receipt_next+index-64u)%COMP_SEGMENT_RECEIPT_CAPACITY]==NO_SLOT)index++;
    return index;
}
static uint8_t gc_slot(const comp_segment_catalog_t *c,uint8_t index)
{return index<64u?c->slots[index]:c->receipts[(c->receipt_next+index-64u)%COMP_SEGMENT_RECEIPT_CAPACITY];}

comp_segment_result_t comp_segment_catalog_entry_io(const comp_segment_catalog_t *c,
    uint8_t index,comp_segment_io_t *io)
{
    if(!c||!io||index>=COMP_SEGMENT_CAPACITY)return COMP_SEG_BAD_ARGUMENT;
    *io=(comp_segment_io_t){0u,0u,COMP_SEG_IO_NONE};
    if(!c->mounted||c->phase!=IDLE)return COMP_SEG_BAD_STATE;
    if(c->slots[index]==NO_SLOT)return COMP_SEG_NOT_FOUND;
    *io=(comp_segment_io_t){address(c,c->bank,c->slots[index]),256u,COMP_SEG_IO_READ};
    return COMP_SEG_OK;
}

bool comp_segment_catalog_transfer_readable(const comp_segment_catalog_t *c)
{
    return c&&c->mounted&&(c->phase==IDLE||
        c->phase==RANGE_RUN||
        (c->phase==RECLAIM&&c->operation==OP_RECLAIM&&c->pending&&
         c->pending_state==COMP_SEG_ERASING));
}
comp_segment_result_t comp_segment_catalog_transfer_entry_io(const comp_segment_catalog_t *c,
    uint8_t index,comp_segment_io_t *io)
{
    if(!c||!io||index>=COMP_SEGMENT_CAPACITY)return COMP_SEG_BAD_ARGUMENT;
    *io=(comp_segment_io_t){0u,0u,COMP_SEG_IO_NONE};
    if(!c->mounted)return COMP_SEG_BAD_STATE;
    if(!comp_segment_catalog_transfer_readable(c))return COMP_SEG_PENDING;
    if(c->slots[index]==NO_SLOT)return COMP_SEG_NOT_FOUND;
    *io=(comp_segment_io_t){address(c,c->bank,c->slots[index]),256u,COMP_SEG_IO_READ};
    return COMP_SEG_OK;
}

comp_segment_result_t comp_segment_catalog_receipt_io(const comp_segment_catalog_t *c,uint8_t index,comp_segment_io_t *io)
{
    if(!c||!io||index>=COMP_SEGMENT_RECEIPT_CAPACITY)return COMP_SEG_BAD_ARGUMENT;
    *io=(comp_segment_io_t){0u,0u,COMP_SEG_IO_NONE};
    if(!c->mounted||c->phase!=IDLE)return COMP_SEG_BAD_STATE;
    if(c->receipts[index]==NO_SLOT)return COMP_SEG_NOT_FOUND;
    *io=(comp_segment_io_t){address(c,c->bank,c->receipts[index]),256u,COMP_SEG_IO_READ};return COMP_SEG_OK;
}

comp_segment_result_t comp_segment_catalog_next_io(const comp_segment_catalog_t *c,comp_segment_io_t *io)
{
    uint8_t index;
    if(!c||!io)return COMP_SEG_BAD_ARGUMENT;
    *io=(comp_segment_io_t){0u,0u,COMP_SEG_IO_NONE};
    switch(c->phase) {
    case IDLE:return c->mounted?COMP_SEG_OK:COMP_SEG_BAD_STATE;
    case MOUNT_ROOT:*io=(comp_segment_io_t){address(c,c->scan,0u),256u,COMP_SEG_IO_READ};break;
    case MOUNT_BLANK:*io=(comp_segment_io_t){address(c,c->scan,c->target_slot),256u,COMP_SEG_IO_READ};break;
    case MOUNT_ROWS:*io=(comp_segment_io_t){address(c,c->bank,c->target_slot),256u,COMP_SEG_IO_READ};break;
    case MOUNT_PREVIOUS:*io=(comp_segment_io_t){address(c,c->bank,c->slots[c->index]),256u,COMP_SEG_IO_READ};break;
    case MOUNT_RANGE:break;
    case MOUNT_RANGE_ENTRY:
        *io=(comp_segment_io_t){address(c,c->bank,c->slots[c->index]),256u,COMP_SEG_IO_READ};break;
    case RANGE_PREFLIGHT:*io=(comp_segment_io_t){address(c,c->bank,c->slots[c->index]),256u,COMP_SEG_IO_READ};break;
    case RANGE_HEADER_BODY:*io=(comp_segment_io_t){address(c,c->bank,c->target_slot),28u,COMP_SEG_IO_PROGRAM};break;
    case RANGE_HEADER_COMMIT:*io=(comp_segment_io_t){address(c,c->bank,c->target_slot)+28u,4u,COMP_SEG_IO_PROGRAM};break;
    case RANGE_HEADER_VERIFY:*io=(comp_segment_io_t){address(c,c->bank,c->target_slot),256u,COMP_SEG_IO_READ};break;
    case RANGE_RUN:return comp_range_reclaim_next_io(c->range_worker,io);
    case GC_RANGE_HEADER:break;
    case GC_RANGE_BODY:*io=(comp_segment_io_t){address(c,(uint8_t)(c->bank^1u),c->copy_slot),252u,COMP_SEG_IO_PROGRAM};break;
    case GC_RANGE_VERIFY:*io=(comp_segment_io_t){address(c,(uint8_t)(c->bank^1u),c->copy_slot),256u,COMP_SEG_IO_READ};break;
    case PREFLIGHT_KNOWN:
        if(c->scan>=64u||c->slots[c->scan]==NO_SLOT)return COMP_SEG_NOT_FOUND;
        *io=(comp_segment_io_t){address(c,c->bank,c->slots[c->scan]),256u,COMP_SEG_IO_READ};break;
    case MOUNT_FIRST:case PREFLIGHT:case COMPACT_SCAN:
        index=occupied_from(c,c->scan);
        if(index<64u)*io=(comp_segment_io_t){address(c,c->bank,c->slots[index]),256u,COMP_SEG_IO_READ};
        break;
    case GC_READ:
        index=gc_from(c,c->scan);
        if(index<64u+COMP_SEGMENT_RECEIPT_CAPACITY)
            *io=(comp_segment_io_t){address(c,c->bank,gc_slot(c,index)),256u,COMP_SEG_IO_READ};
        break;
    case MOUNT_PAIR:
        index=occupied_from(c,c->index);
        if(index<64u)*io=(comp_segment_io_t){address(c,c->bank,c->slots[index]),256u,COMP_SEG_IO_READ};
        break;
    case GC_INTENT_BODY:*io=(comp_segment_io_t){address(c,c->bank,0u)+INTENT,24u,COMP_SEG_IO_PROGRAM};break;
    case GC_INTENT_COMMIT:*io=(comp_segment_io_t){address(c,c->bank,0u)+INTENT_COMMIT,4u,COMP_SEG_IO_PROGRAM};break;
    case GC_INTENT_VERIFY:*io=(comp_segment_io_t){address(c,c->bank,0u),256u,COMP_SEG_IO_READ};break;
    case GC_ERASE:*io=(comp_segment_io_t){c->banks[c->bank^1u]+c->cursor,COMP_SEGMENT_BANK_BYTES-c->cursor,COMP_SEG_IO_ERASE};break;
    case ROOT_BODY:case ROOT_COMMIT:case ROOT_VERIFY:
        *io=(comp_segment_io_t){address(c,c->operation==OP_FORMAT?0u:(uint8_t)(c->bank^1u),0u),256u,COMP_SEG_IO_READ};
        if(c->phase==ROOT_BODY){io->kind=COMP_SEG_IO_PROGRAM;io->bytes=252u;}
        if(c->phase==ROOT_COMMIT){io->kind=COMP_SEG_IO_PROGRAM;io->address+=COMMIT;io->bytes=4u;}
        break;
    case GC_BODY:case GC_COMMIT:case GC_VERIFY:
        *io=(comp_segment_io_t){address(c,(uint8_t)(c->bank^1u),c->copy_slot),256u,COMP_SEG_IO_READ};
        if(c->phase==GC_BODY){io->kind=COMP_SEG_IO_PROGRAM;io->bytes=252u;}
        if(c->phase==GC_COMMIT){io->kind=COMP_SEG_IO_PROGRAM;io->address+=COMMIT;io->bytes=4u;}
        break;
    case ROW_BODY:case ROW_COMMIT:case ROW_VERIFY:
        *io=(comp_segment_io_t){address(c,c->bank,c->target_slot),256u,COMP_SEG_IO_READ};
        if(c->phase==ROW_BODY){io->kind=COMP_SEG_IO_PROGRAM;io->bytes=252u;}
        if(c->phase==ROW_COMMIT){io->kind=COMP_SEG_IO_PROGRAM;io->address+=COMMIT;io->bytes=4u;}
        break;
    case RECLAIM:
        if(!c->pending)return COMP_SEG_BAD_STATE;
        if(c->cursor>=reclaim_bytes(c))return COMP_SEG_BAD_STATE;
        *io=(comp_segment_io_t){c->data_base+c->pending->extent_offset+c->cursor,
                              reclaim_bytes(c)-c->cursor,COMP_SEG_IO_ERASE};break;
    default:return COMP_SEG_BAD_STATE;
    }
    return COMP_SEG_OK;
}

static bool geometry(uint32_t a,uint32_t b,uint32_t base,uint32_t bytes)
{
    if (a%4096u!=0u || b%4096u!=0u || base%4096u!=0u || bytes%4096u!=0u ||
        bytes==0u || a>UINT32_MAX-COMP_SEGMENT_BANK_BYTES ||
        b>UINT32_MAX-COMP_SEGMENT_BANK_BYTES || base>UINT32_MAX-bytes) return false;
    return (a+COMP_SEGMENT_BANK_BYTES<=b || b+COMP_SEGMENT_BANK_BYTES<=a) &&
           (a+COMP_SEGMENT_BANK_BYTES<=base || base+bytes<=a) &&
           (b+COMP_SEGMENT_BANK_BYTES<=base || base+bytes<=b);
}

static bool entry_valid(const comp_segment_catalog_t *c,const comp_segment_entry_t *e,
                        uint8_t state)
{
    const comp_rec_v2_descriptor_t *d=&e->descriptor;
    if (state>COMP_SEG_SESSION_DISCARD || d->recording_id==0u || d->recording_id==UINT32_MAX ||
        d->format_epoch!=c->epoch || memcmp(d->device_uid,c->uid,12u)!=0 ||
        d->session_id==0u || d->segment_index>=COMP_REC_V2_INDEX_EXCLUSIVE_MAX ||
        d->sample_offset%320u!=0u || d->source_mode>2u || d->codec!=3u ||
        e->reserved_bytes==0u || e->reserved_bytes%4096u!=0u ||
        e->extent_offset%4096u!=0u || e->reserved_bytes>UINT32_MAX-e->extent_offset ||
        (state!=0u && (e->extent_offset>c->data_bytes ||
        e->reserved_bytes>c->data_bytes-e->extent_offset))) return false;
    /* A completed-removal receipt is proof only. Resource growth can put its
     * historical extent outside today's data arena; it cannot read/erase it,
     * reserve space or resurrect the removed ID. Keep exact proof fields. */
    if(e->provenance_extent_plus1 && ((e->provenance_extent_plus1-1u)%4096u ||
        e->reserved_bytes>UINT32_MAX-(e->provenance_extent_plus1-1u)))return false;
    if (state==COMP_SEG_WRITING || state==COMP_SEG_CANCELED)
        return d->sample_count==0u && d->encoded_length==0u && d->flags==0u &&
               d->content_crc32==0u && d->total_segments==0u && d->sync_state==0u &&
               uniform(d->sha256,32u,0u);
    return comp_rec_v2_valid(d) && d->encoded_length<=e->reserved_bytes &&
           d->sync_state==((state==COMP_SEG_UNSYNCED || state==COMP_SEG_DISCARDING || state==COMP_SEG_DISCARDED || state==COMP_SEG_SESSION_DISCARD)?1u:2u);
}

static bool same_identity(const comp_segment_entry_t *a,const comp_segment_entry_t *b)
{
    const comp_rec_v2_descriptor_t *x=&a->descriptor,*y=&b->descriptor;
    return x->recording_id==y->recording_id && x->format_epoch==y->format_epoch &&
        x->session_id==y->session_id && x->segment_index==y->segment_index &&
        x->sample_offset==y->sample_offset && x->codec==y->codec &&
        x->source_mode==y->source_mode && memcmp(x->device_uid,y->device_uid,12u)==0 &&
        a->extent_offset==b->extent_offset && a->reserved_bytes==b->reserved_bytes &&
        a->provenance_extent_plus1==b->provenance_extent_plus1 &&
        a->started_unix_s==b->started_unix_s;
}

static bool same_sealed(const comp_segment_entry_t *a,const comp_segment_entry_t *b)
{
    const comp_rec_v2_descriptor_t *x=&a->descriptor,*y=&b->descriptor;
    return same_identity(a,b) && x->sample_count==y->sample_count &&
        x->encoded_length==y->encoded_length && x->content_crc32==y->content_crc32 &&
        x->flags==y->flags && x->total_segments==y->total_segments &&
        memcmp(x->sha256,y->sha256,32u)==0;
}

static bool separate(const comp_segment_entry_t *a,const comp_segment_entry_t *b)
{
    const comp_rec_v2_descriptor_t *x=&a->descriptor,*y=&b->descriptor;
    if (x->recording_id==y->recording_id ||
        !(a->extent_offset+a->reserved_bytes<=b->extent_offset ||
          b->extent_offset+b->reserved_bytes<=a->extent_offset)) return false;
    if (x->session_id!=y->session_id) return true;
    if (x->segment_index==y->segment_index || x->source_mode!=y->source_mode) return false;
    /* A WRITING reservation has zero committed samples. A later sealed range
     * must still begin at or after it, never silently overlap its timeline. */
    if (x->segment_index<y->segment_index)
        return x->sample_offset<=y->sample_offset && x->sample_count<=y->sample_offset-x->sample_offset;
    return y->sample_offset<=x->sample_offset && y->sample_count<=x->sample_offset-y->sample_offset;
}

/* Internal reservation rows share the exact V2 field positions, but WRITING
 * is never passed to the sealed-only public codec or advertised on GATT. */
static void descriptor_encode(const comp_rec_v2_descriptor_t *d,uint8_t *p,uint8_t state)
{
    memset(p,0,112u); memcpy(p,"CRS2",4u); comp_rec_put16(p+4u,2u); comp_rec_put16(p+6u,112u);
    comp_rec_put32(p+8u,d->recording_id); comp_rec_put64(p+12u,d->format_epoch);
    comp_rec_put64(p+20u,d->session_id); comp_rec_put32(p+28u,d->segment_index);
    comp_rec_put64(p+32u,d->sample_offset); comp_rec_put64(p+40u,d->sample_count);
    comp_rec_put32(p+48u,d->encoded_length); comp_rec_put32(p+52u,d->content_crc32);
    memcpy(p+56u,d->sha256,32u); comp_rec_put32(p+88u,d->total_segments);
    p[92]=d->flags; p[93]=d->codec; p[94]=d->source_mode;
    p[95]=(state==COMP_SEG_WRITING || state==COMP_SEG_CANCELED)?0u:((state==COMP_SEG_UNSYNCED || state==COMP_SEG_DISCARDING || state==COMP_SEG_DISCARDED || state==COMP_SEG_SESSION_DISCARD)?1u:2u);
    memcpy(p+96u,d->device_uid,12u); comp_rec_put32(p+108u,comp_rec_crc(p,108u));
}

static bool descriptor_decode(const uint8_t *p,comp_rec_v2_descriptor_t *d)
{
    if (memcmp(p,"CRS2",4u)!=0 || p[4]!=2u || p[5]!=0u || p[6]!=112u || p[7]!=0u ||
        comp_rec_get32(p+108u)!=comp_rec_crc(p,108u)) return false;
    memset(d,0,sizeof(*d)); d->recording_id=comp_rec_get32(p+8u);
    d->format_epoch=comp_rec_get64(p+12u); d->session_id=comp_rec_get64(p+20u);
    d->segment_index=comp_rec_get32(p+28u); d->sample_offset=comp_rec_get64(p+32u);
    d->sample_count=comp_rec_get64(p+40u); d->encoded_length=comp_rec_get32(p+48u);
    d->content_crc32=comp_rec_get32(p+52u); memcpy(d->sha256,p+56u,32u);
    d->total_segments=comp_rec_get32(p+88u); d->flags=p[92]; d->codec=p[93];
    d->source_mode=p[94]; d->sync_state=p[95]; memcpy(d->device_uid,p+96u,12u);
    return true;
}

static bool row_decode(const comp_segment_catalog_t *c,const uint8_t *p,
                       comp_segment_entry_t *e)
{
    if (!uniform(p+COMMIT,4u,0u) || memcmp(p,"CSG2",4u)!=0 || (p[4]!=1u && p[4]!=2u && p[4]!=3u) || p[7]!=0u ||
        p[6]>=COMP_SEGMENT_CAPACITY || comp_rec_get32(p+8u)==0u ||
        comp_rec_get32(p+ROW_CRC)!=comp_rec_crc(p,ROW_CRC)) return false;
    memset(e,0,sizeof(*e)); e->state=p[5]; e->extent_offset=comp_rec_get32(p+12u);
    e->reserved_bytes=comp_rec_get32(p+16u); e->started_unix_s=comp_rec_get32(p+132u);
    e->provenance_extent_plus1=comp_rec_get32(p+136u);
    if(e->state==COMP_SEG_SESSION_DISCARD) {
        if(p[4]!=3u || memcmp(p+144u,"SDI1",4u) || comp_rec_get32(p+160u)!=comp_rec_crc(p+144u,16u) ||
           !uniform(p+164u,COMMIT-164u,255u))return false;
        uint64_t slots=comp_rec_get64(p+148u);uint32_t max_id=comp_rec_get32(p+156u);
        if(!slots || !max_id || !(slots&(UINT64_C(1)<<p[6])) ||
           max_id<comp_rec_get32(p+28u))return false;
    } else if(!uniform(p+144u,COMMIT-144u,255u))return false;
    if ((p[4]==1u && e->provenance_extent_plus1!=0u) || !descriptor_decode(p+20u,&e->descriptor)) return false;
    return entry_valid(c,e,e->state);
}

static void row_encode(comp_segment_catalog_t *c)
{
    uint8_t *p=c->page;
    memset(p,255,256u); memcpy(p,"CSG2",4u); p[4]=(c->pending_state==COMP_SEG_DISCARDING || c->pending_state==COMP_SEG_DISCARDED || c->pending_state==COMP_SEG_SESSION_DISCARD)?3u:2u; p[5]=c->pending_state; p[6]=c->index; p[7]=0u;
    comp_rec_put32(p+8u,c->generation+1u); comp_rec_put32(p+12u,c->pending->extent_offset);
    comp_rec_put32(p+16u,c->pending->reserved_bytes);
    descriptor_encode(&c->pending->descriptor,p+20u,c->pending_state);
    comp_rec_put32(p+132u,c->pending->started_unix_s); comp_rec_put32(p+136u,c->pending->provenance_extent_plus1);
    c->expected_crc=comp_rec_crc(p,ROW_CRC); comp_rec_put32(p+ROW_CRC,c->expected_crc);
    if(c->pending_state==COMP_SEG_SESSION_DISCARD) {
        memcpy(p+144u,"SDI1",4u);comp_rec_put64(p+148u,c->pending_intent->slots);
        comp_rec_put32(p+156u,c->pending_intent->max_id);comp_rec_put32(p+160u,comp_rec_crc(p+144u,16u));
    }
}

static bool intent_valid(const uint8_t *p)
{
    return uniform(p+INTENT_COMMIT,4u,0u) && memcmp(p+INTENT,"GCI2",4u)==0 &&
        comp_rec_get32(p+INTENT+8u)==comp_rec_get32(p+8u) &&
        comp_rec_get32(p+8u)!=UINT32_MAX &&
        comp_rec_get32(p+INTENT+4u)==comp_rec_get32(p+8u)+1u &&
        comp_rec_get32(p+INTENT+12u)==comp_rec_crc(p+INTENT,12u) &&
        uniform(p+INTENT+16u,8u,255u);
}

static bool root_valid(const comp_segment_catalog_t *c,const uint8_t *p)
{
    return uniform(p+COMMIT,4u,0u) && memcmp(p,"CSC2",4u)==0 && p[4]==1u &&
        p[5]==0u && p[6]==COMP_SEGMENT_CAPACITY && p[7]==0u &&
        comp_rec_get32(p+8u)!=0u && comp_rec_get32(p+12u)!=0u &&
        comp_rec_get32(p+16u)!=0u && comp_rec_get32(p+20u)<=COMP_SEGMENT_CAPACITY+COMP_SEGMENT_RECEIPT_CAPACITY &&
        comp_rec_get64(p+24u)==c->epoch && memcmp(p+32u,c->uid,12u)==0 &&
        comp_rec_get32(p+44u)==c->data_base && comp_rec_get32(p+48u)==c->data_bytes &&
        comp_rec_get32(p+52u)==c->banks[0] && comp_rec_get32(p+56u)==c->banks[1] &&
        comp_rec_get32(p+ROOT_CRC)==comp_rec_crc(p,ROOT_CRC) &&
        uniform(p+ROOT_CRC+4u,INTENT-ROOT_CRC-4u,255u) &&
        (!uniform(p+INTENT_COMMIT,4u,0u) || intent_valid(p));
}

static void root_encode(comp_segment_catalog_t *c)
{
    uint8_t *p=c->page;
    memset(p,255,256u); memcpy(p,"CSC2",4u); p[4]=1u; p[5]=0u; p[6]=64u; p[7]=0u;
    comp_rec_put32(p+8u,c->bank_serial+1u); comp_rec_put32(p+12u,c->generation);
    comp_rec_put32(p+16u,c->next_id); comp_rec_put32(p+20u,live_count(c));
    comp_rec_put64(p+24u,c->epoch); memcpy(p+32u,c->uid,12u);
    comp_rec_put32(p+44u,c->data_base); comp_rec_put32(p+48u,c->data_bytes);
    comp_rec_put32(p+52u,c->banks[0]); comp_rec_put32(p+56u,c->banks[1]);
    comp_rec_put32(p+ROOT_CRC,comp_rec_crc(p,ROOT_CRC));
}

static void apply_row(comp_segment_catalog_t *c,uint8_t index,uint8_t slot,uint8_t state)
{
    uint64_t bit=UINT64_C(1)<<index;
    c->slots[index]=(state==0u || state==COMP_SEG_CANCELED || state==COMP_SEG_DISCARDED)?NO_SLOT:slot;
    if (state==COMP_SEG_UNSYNCED || state==COMP_SEG_ACKED) c->visible_mask|=bit;
    else c->visible_mask&=~bit;
    c->range_page=NO_SLOT;
    if(state==COMP_SEG_WRITING||state==0u||state==COMP_SEG_CANCELED||state==COMP_SEG_DISCARDED){
        c->range_id[index]=c->range_binding[index]=c->range_nonce[index]=0u;
        c->range_first[index]=c->range_end[index]=0u;
    }
    if(state==0u) {
        c->receipts[c->receipt_next]=slot;
        c->receipt_next=(uint8_t)((c->receipt_next+1u)%COMP_SEGMENT_RECEIPT_CAPACITY);
    }
}
static void range_overlay(const comp_segment_catalog_t *c,uint8_t index,comp_segment_entry_t *e)
{
    e->range_nonce=c->range_nonce[index];e->range_first=c->range_first[index];
    e->range_end=c->range_pending_slot==index?c->range_first[index]:c->range_end[index];
}
static unsigned range_count(const comp_segment_catalog_t *c)
{
    unsigned n=0u;for(unsigned i=0u;i<64u;i++)if(c->slots[i]!=NO_SLOT&&c->range_nonce[i])n++;
    return n;
}
/* Pure snapshot generation. Every entry came from an identity-validated CRR3
 * record. It never reads audio or consumes more than this metadata page. */
static bool range_snapshot_page(const comp_segment_catalog_t *c,uint8_t *cursor,
    uint32_t serial,uint32_t page_index,uint8_t out[256])
{
    memset(out,255,256u);
    comp_range_journal_snapshot_header_prepare(out,c->uid,c->epoch,serial,page_index);
    memset(out+28u,0,4u);unsigned count=0u;
    while(*cursor<64u&&count<COMP_RANGE_JOURNAL_RECORDS){
        uint8_t slot=(*cursor)++;
        if(c->slots[slot]==NO_SLOT||!c->range_nonce[slot])continue;
        comp_range_plan_t p={c->range_id[slot],c->range_nonce[slot],c->range_binding[slot],
            c->range_first[slot],c->range_end[slot],slot};
        uint8_t *record=out+32u+count*32u;
        if(!comp_range_journal_record_prepare(record,out,(uint8_t)count,&p))return false;
        memset(record+24u,0,8u);count++;
    }
    return count!=0u;
}
bool comp_segment_catalog_range_pending(const comp_segment_catalog_t *c)
{return c&&(c->range_worker||c->range_pending_slot!=NO_SLOT);}

static bool transition(const comp_segment_entry_t *old,const comp_segment_entry_t *next)
{
    if (!same_identity(old,next)) return false;
    if (old->state==COMP_SEG_WRITING && next->state==COMP_SEG_UNSYNCED) return true;
    if (old->state==COMP_SEG_WRITING && next->state==COMP_SEG_CANCELED) return same_sealed(old,next);
    return same_sealed(old,next) &&
        ((old->state==COMP_SEG_UNSYNCED && next->state==COMP_SEG_ACKED) ||
         (old->state==COMP_SEG_ACKED && next->state==COMP_SEG_ERASING) ||
         (old->state==COMP_SEG_UNSYNCED && next->state==COMP_SEG_SESSION_DISCARD) ||
         (old->state==COMP_SEG_SESSION_DISCARD && next->state==COMP_SEG_DISCARDING) ||
         (old->state==COMP_SEG_UNSYNCED && next->state==COMP_SEG_DISCARDING) ||
         (old->state==COMP_SEG_DISCARDING && next->state==COMP_SEG_DISCARDED) ||
         (old->state==COMP_SEG_ERASING && next->state==0u));
}

comp_segment_result_t comp_segment_catalog_mount_begin(comp_segment_catalog_t *c,
    const comp_segment_port_t *port,uint32_t a,uint32_t b,uint32_t base,uint32_t bytes,
    const uint8_t uid[12],uint64_t epoch)
{
    if (c==NULL || port==NULL || port->read==NULL || port->program==NULL ||
        port->erase_step==NULL || uid==NULL || epoch==0u || !geometry(a,b,base,bytes) ||
        uniform(uid,12u,0u) || uniform(uid,12u,255u)) return COMP_SEG_BAD_ARGUMENT;
    memset(c,0,sizeof(*c)); c->port=*port; c->banks[0]=a; c->banks[1]=b;
    c->data_base=base; c->data_bytes=bytes; c->epoch=epoch; memcpy(c->uid,uid,12u);
    memset(c->slots,NO_SLOT,sizeof(c->slots)); c->phase=MOUNT_ROOT;
    memset(c->receipts,NO_SLOT,sizeof(c->receipts));
    c->range_page=c->range_pending_slot=c->range_pending_page=c->range_pending_record=NO_SLOT;
    c->range_snapshot_open=true;
    return COMP_SEG_PENDING;
}

comp_segment_result_t comp_segment_catalog_format_blank_begin(comp_segment_catalog_t *c)
{
    if (c==NULL) return COMP_SEG_BAD_ARGUMENT;
    if (c->phase!=IDLE || c->mounted || !c->blank_verified) return COMP_SEG_BAD_STATE;
    c->blank_verified=false;
    c->operation=OP_FORMAT; c->generation=1u; c->next_id=1u; c->bank=0u;
    c->phase=ROOT_BODY; return COMP_SEG_PENDING;
}

static comp_segment_result_t begin(comp_segment_catalog_t *c,const comp_segment_entry_t *e,uint8_t op)
{
    if (c==NULL || e==NULL) return COMP_SEG_BAD_ARGUMENT;
    if (!c->mounted || c->phase!=IDLE || comp_segment_catalog_range_pending(c)) return COMP_SEG_BAD_STATE;
    if (!entry_valid(c,e,e->state) ||
        (op==OP_PUT && e->state!=COMP_SEG_WRITING && e->state!=COMP_SEG_UNSYNCED) ||
        (op==OP_ACK && e->state!=COMP_SEG_ACKED) ||
        (op==OP_RECLAIM && e->state!=COMP_SEG_ACKED && e->state!=COMP_SEG_ERASING) ||
        (op==OP_CANCEL && e->state!=COMP_SEG_WRITING) ||
        (op==OP_DISCARD && e->state!=COMP_SEG_UNSYNCED && e->state!=COMP_SEG_DISCARDING) ||
        (op==OP_SESSION_INTENT && e->state!=COMP_SEG_SESSION_DISCARD))
        return COMP_SEG_BAD_ARGUMENT;
    if (c->generation==UINT32_MAX || c->bank_serial==UINT32_MAX ||
        ((op==OP_RECLAIM || op==OP_DISCARD) && c->generation==UINT32_MAX-1u &&
         e->state!=COMP_SEG_ERASING && e->state!=COMP_SEG_DISCARDING)) return COMP_SEG_FULL;
    c->pending=e; c->pending_intent=NULL; c->operation=op;
    c->pending_state=op==OP_RECLAIM?COMP_SEG_ERASING:(op==OP_DISCARD?COMP_SEG_DISCARDING:(op==OP_CANCEL?COMP_SEG_CANCELED:e->state));
    c->index=NO_SLOT; c->scan=0u; c->phase=PREFLIGHT; c->cursor=0u;
    return COMP_SEG_PENDING;
}

comp_segment_result_t comp_segment_catalog_put_begin(comp_segment_catalog_t *c,const comp_segment_entry_t *e)
{ return begin(c,e,OP_PUT); }
comp_segment_result_t comp_segment_catalog_ack_begin(comp_segment_catalog_t *c,const comp_segment_entry_t *e)
{ return begin(c,e,OP_ACK); }
comp_segment_result_t comp_segment_catalog_reclaim_begin(comp_segment_catalog_t *c,const comp_segment_entry_t *e)
{ return begin(c,e,OP_RECLAIM); }
static comp_segment_result_t begin_at(comp_segment_catalog_t *c,const comp_segment_entry_t *e,uint8_t op,uint8_t slot)
{
    if(!c||slot>=64u)return COMP_SEG_BAD_ARGUMENT;
    if(!c->mounted||c->phase!=IDLE)return COMP_SEG_BAD_STATE;
    if(c->slots[slot]==NO_SLOT)return COMP_SEG_NOT_FOUND;
    comp_segment_result_t r=begin(c,e,op);
    if(r==COMP_SEG_PENDING){c->scan=slot;c->phase=PREFLIGHT_KNOWN;}
    return r;
}
comp_segment_result_t comp_segment_catalog_ack_at_begin(comp_segment_catalog_t *c,const comp_segment_entry_t *e,uint8_t slot)
{return begin_at(c,e,OP_ACK,slot);}
comp_segment_result_t comp_segment_catalog_reclaim_at_begin(comp_segment_catalog_t *c,const comp_segment_entry_t *e,uint8_t slot)
{return begin_at(c,e,OP_RECLAIM,slot);}
comp_segment_result_t comp_segment_catalog_session_discard_begin(comp_segment_catalog_t *c,const comp_segment_entry_t *e,const comp_segment_discard_intent_t *intent,uint32_t expected_generation)
{
    if(!c || !e || !intent || !intent->slots || !intent->max_id || intent->max_id<e->descriptor.recording_id)return COMP_SEG_BAD_ARGUMENT;
    if(expected_generation!=c->generation)return COMP_SEG_STALE_SNAPSHOT;
    comp_segment_result_t r=begin(c,e,OP_SESSION_INTENT);
    if(r==COMP_SEG_PENDING)c->pending_intent=intent;
    return r;
}
comp_segment_result_t comp_segment_catalog_discard_begin(comp_segment_catalog_t *c,const comp_segment_entry_t *e,uint32_t expected_generation)
{
    if(!c || !e)return COMP_SEG_BAD_ARGUMENT;
    if(expected_generation!=c->generation)return COMP_SEG_STALE_SNAPSHOT;
    return begin(c,e,OP_DISCARD);
}
comp_segment_result_t comp_segment_catalog_cancel_unwritten_begin(comp_segment_catalog_t *c,const comp_segment_entry_t *e)
{ return begin(c,e,OP_CANCEL); }

comp_segment_result_t comp_segment_catalog_compact_legacy_begin(comp_segment_catalog_t *c)
{
    if(!c)return COMP_SEG_BAD_ARGUMENT;
    if(!c->mounted||c->phase||comp_segment_catalog_range_pending(c))return COMP_SEG_BAD_STATE;
    if(!c->legacy_dirty)return COMP_SEG_OK;
    if(c->bank_serial==UINT32_MAX)return COMP_SEG_FULL;
    c->operation=OP_COMPACT;c->scan=0u;c->cursor=0u;c->gc_has_v3=false;c->phase=COMPACT_SCAN;
    return COMP_SEG_PENDING;
}
static void append_or_gc(comp_segment_catalog_t *c)
{
    if (c->next_slot>=COMP_SEGMENT_BANK_PAGES) { c->cursor=0u;c->gc_has_v3=false; c->phase=GC_INTENT_BODY; }
    else { c->target_slot=c->next_slot; c->phase=ROW_BODY; }
}
comp_segment_result_t comp_segment_catalog_range_begin(comp_segment_catalog_t *c,
    struct comp_range_reclaim_s *w,const comp_segment_entry_t *e,uint8_t slot,
    uint16_t first,uint16_t end,uint32_t nonce,const uint8_t sha[32])
{
    comp_range_plan_t plan;uint32_t begin,limit;
    if(!c||!w||!e||!sha||slot>=64u||!comp_range_plan(e,slot,first,end,nonce,&plan,&begin,&limit))
        return COMP_SEG_BAD_ARGUMENT;
    if(!c->mounted)return COMP_SEG_BAD_STATE;
    if(c->range_worker){
        const comp_range_plan_t *p=&c->range_worker->plan;
        return p->recording_id==plan.recording_id&&p->slot==slot&&p->first_sector==first&&p->end_sector==end&&
            p->request_nonce==nonce&&p->descriptor_binding==plan.descriptor_binding?COMP_SEG_PENDING:COMP_SEG_BAD_STATE;
    }
    if(c->phase!=IDLE||c->slots[slot]==NO_SLOT)return COMP_SEG_BAD_STATE;
    if(c->range_pending_slot!=NO_SLOT){
        if(c->range_pending_slot!=slot||c->range_id[slot]!=plan.recording_id||
           c->range_nonce[slot]!=nonce||c->range_first[slot]!=first||c->range_end[slot]!=end||
           c->range_binding[slot]!=plan.descriptor_binding)return COMP_SEG_BAD_STATE;
    }else if(c->range_nonce[slot]&&c->range_nonce[slot]==nonce){
        return c->range_id[slot]==plan.recording_id&&c->range_first[slot]==first&&
            c->range_end[slot]==end&&c->range_binding[slot]==plan.descriptor_binding?COMP_SEG_OK:COMP_SEG_BAD_ARGUMENT;
    }else if(first!=c->range_end[slot])return COMP_SEG_BAD_ARGUMENT;
    uint8_t durable_sha[32];memcpy(durable_sha,sha,32u);
    memset(w,0,sizeof(*w));w->entry=e;w->plan=plan;memcpy(w->expected_sha,durable_sha,32u);
    c->range_worker=w;c->pending=e;c->pending_intent=NULL;c->operation=OP_RANGE;
    c->index=slot;c->pending_state=COMP_SEG_UNSYNCED;c->phase=RANGE_PREFLIGHT;
    return COMP_SEG_PENDING;
}
static comp_segment_result_t range_launch(comp_segment_catalog_t *c,uint8_t page,uint8_t record)
{
    comp_range_reclaim_t *w=c->range_worker;comp_range_plan_t plan=w->plan;
    uint8_t sha[32];memcpy(sha,w->expected_sha,32u);memset(w,0,sizeof(*w));
    comp_segment_result_t r=comp_range_reclaim_begin(w,&c->port,c->pending,c->data_base,
        address(c,c->bank,page),c->bank_serial,page,record,&plan,sha,c->page);
    if(r!=COMP_SEG_PENDING)return fail(c,r);
    c->phase=RANGE_RUN;return r;
}
static void mount_next_page(comp_segment_catalog_t *c)
{
    c->target_slot++;
    if(c->target_slot==COMP_SEGMENT_BANK_PAGES){c->scan=0u;c->phase=MOUNT_FIRST;}
    else c->phase=MOUNT_ROWS;
}

comp_segment_result_t comp_segment_catalog_mount_poll(comp_segment_catalog_t *c)
{
    comp_segment_entry_t e,old;uint8_t scratch[256];
    if(!c)return COMP_SEG_BAD_ARGUMENT;
    switch (c->phase) {
    case IDLE: return c->mounted?COMP_SEG_OK:COMP_SEG_BAD_STATE;
    case MOUNT_ROOT:
        if (!c->port.read(c->port.context,address(c,c->scan,0u),c->page,256u)) return fail(c,COMP_SEG_IO_ERROR);
        if (uniform(c->page,256u,255u)) c->root_blank_mask|=(uint8_t)(1u<<c->scan);
        else if (uniform(c->page+COMMIT,4u,0u)) {
            if (!root_valid(c,c->page)) c->invalid_root_mask|=(uint8_t)(1u<<c->scan);
            else {
                uint32_t serial=comp_rec_get32(c->page+8u);
                if (serial==c->bank_serial) return fail(c,COMP_SEG_CORRUPT);
                if (serial>c->bank_serial) {
                    c->bank=c->scan; c->bank_serial=serial; c->generation=comp_rec_get32(c->page+12u);
                    c->next_id=comp_rec_get32(c->page+16u); c->snapshot_count=(uint8_t)comp_rec_get32(c->page+20u);
                    c->retire_authorized=intent_valid(c->page);
                }
                c->root_valid_mask|=(uint8_t)(1u<<c->scan);
            }
        }
        c->scan++;
        if (c->scan==2u) {
            if (c->root_valid_mask!=0u) {
                uint8_t allowed=c->retire_authorized?(uint8_t)(1u<<(c->bank^1u)):0u;
                if ((c->invalid_root_mask & (uint8_t)~allowed)!=0u) return fail(c,COMP_SEG_CORRUPT);
                c->target_slot=1u; c->next_slot=1u; c->phase=MOUNT_ROWS;
            }
            else if (c->root_blank_mask==3u) { c->scan=0u; c->target_slot=1u; c->phase=MOUNT_BLANK; }
            else return fail(c,COMP_SEG_CORRUPT);
        }
        break;
    case MOUNT_BLANK:
        if (!c->port.read(c->port.context,address(c,c->scan,c->target_slot),c->page,256u)) return fail(c,COMP_SEG_IO_ERROR);
        if (!uniform(c->page,256u,255u)) { c->root_blank_mask=0u; return fail(c,COMP_SEG_CORRUPT); }
        c->target_slot++;
        if (c->target_slot==COMP_SEGMENT_BANK_PAGES) {
            c->scan++; c->target_slot=1u;
            if (c->scan==2u) { c->phase=IDLE; c->blank_verified=true; return COMP_SEG_UNFORMATTED; }
        }
        break;
    case MOUNT_ROWS:
        if (!c->port.read(c->port.context,address(c,c->bank,c->target_slot),c->page,256u)) return fail(c,COMP_SEG_IO_ERROR);
        if (!uniform(c->page,256u,255u)) c->next_slot=(uint8_t)(c->target_slot+1u);
        if(!memcmp(c->page,"CRR3",4u)){
            if(c->target_slot<=c->snapshot_count||!uniform(c->page+224u,32u,255u))return fail(c,COMP_SEG_CORRUPT);
            comp_range_journal_state_t state=comp_range_journal_header_decode(c->page,c->uid,c->epoch,c->bank_serial,c->target_slot);
            if(state==COMP_RANGE_TORN){c->range_page=NO_SLOT;mount_next_page(c);break;}
            if(state!=COMP_RANGE_DONE||c->range_pending_slot!=NO_SLOT)return fail(c,COMP_SEG_CORRUPT);
            bool snapshot=comp_range_journal_is_snapshot(c->page);
            if(snapshot&&!c->range_snapshot_open)return fail(c,COMP_SEG_CORRUPT);
            if(!snapshot)c->range_snapshot_open=false;
            c->range_page=snapshot?NO_SLOT:c->target_slot;c->range_record=0u;c->scan=0u;c->phase=MOUNT_RANGE;break;
        }
        if (c->target_slot<=c->snapshot_count || uniform(c->page+COMMIT,4u,0u)) {
            if(c->range_pending_slot!=NO_SLOT)return fail(c,COMP_SEG_CORRUPT);
            if (!row_decode(c,c->page,&e)) return fail(c,COMP_SEG_CORRUPT);
            if(c->page[4]==3u)c->legacy_dirty=true;
            c->index=c->page[6];
            uint32_t generation=comp_rec_get32(c->page+8u);
            if (c->target_slot<=c->snapshot_count) {
                if ((e.state==COMP_SEG_CANCELED || e.state==COMP_SEG_DISCARDED) || (e.state!=0u&&c->slots[c->index]!=NO_SLOT) || generation!=c->generation ||
                    e.descriptor.recording_id>=c->next_id) return fail(c,COMP_SEG_CORRUPT);
                if(e.state==0u) {
                    /* Snapshot receipts may share a reused logical slot with
                     * a newer live ID. They never change live ownership. */
                    if(++c->pending_state>COMP_SEGMENT_RECEIPT_CAPACITY)return fail(c,COMP_SEG_CORRUPT);
                    c->receipts[c->receipt_next]=c->target_slot;
                    c->receipt_next=(uint8_t)((c->receipt_next+1u)%COMP_SEGMENT_RECEIPT_CAPACITY);
                } else apply_row(c,c->index,c->target_slot,e.state);
            } else {
                c->range_snapshot_open=false;
                if (c->generation==UINT32_MAX || generation!=c->generation+1u) return fail(c,COMP_SEG_CORRUPT);
                if (c->slots[c->index]!=NO_SLOT) { c->phase=MOUNT_PREVIOUS; break; }
                if (e.state!=COMP_SEG_WRITING || e.descriptor.recording_id!=c->next_id) return fail(c,COMP_SEG_CORRUPT);
                c->next_id++; c->generation=generation; apply_row(c,c->index,c->target_slot,e.state);
            }
        } else if (c->target_slot<=c->snapshot_count) return fail(c,COMP_SEG_CORRUPT);
        c->target_slot++;
        if (c->target_slot==COMP_SEGMENT_BANK_PAGES) { c->scan=0u; c->phase=MOUNT_FIRST; }
        break;
    case MOUNT_RANGE:{
        if(c->scan==COMP_RANGE_JOURNAL_RECORDS){mount_next_page(c);break;}
        comp_range_plan_t plan;
        comp_range_journal_state_t state=comp_range_journal_record_decode(c->page+32u+(uint32_t)c->scan*32u,c->page,c->scan,&plan);
        if(state==COMP_RANGE_EMPTY){c->scan++;break;}
        c->range_record=(uint8_t)(c->scan+1u);
        if(state==COMP_RANGE_TORN){
            if(comp_range_journal_is_snapshot(c->page))return fail(c,COMP_SEG_CORRUPT);
            c->scan++;break;
        }
        if((state!=COMP_RANGE_PENDING&&state!=COMP_RANGE_DONE)||c->slots[plan.slot]==NO_SLOT||c->range_pending_slot!=NO_SLOT)
            return fail(c,COMP_SEG_CORRUPT);
        c->index=plan.slot;c->phase=MOUNT_RANGE_ENTRY;break;}
    case MOUNT_RANGE_ENTRY:{
        comp_range_plan_t plan;
        comp_range_journal_state_t state=comp_range_journal_record_decode(c->page+32u+(uint32_t)c->scan*32u,c->page,c->scan,&plan);
        if(!c->port.read(c->port.context,address(c,c->bank,c->slots[c->index]),scratch,256u))return fail(c,COMP_SEG_IO_ERROR);
        if(!row_decode(c,scratch,&e)||scratch[6]!=plan.slot||
           (e.state!=COMP_SEG_UNSYNCED&&e.state!=COMP_SEG_ACKED&&e.state!=COMP_SEG_ERASING))return fail(c,COMP_SEG_CORRUPT);
        bool snapshot=comp_range_journal_is_snapshot(c->page);
        e.state=COMP_SEG_UNSYNCED;e.descriptor.sync_state=1u;
        if(!comp_range_plan_matches(&plan,&e,c->index)||
           (snapshot?(state!=COMP_RANGE_DONE||c->range_nonce[c->index]!=0u):plan.first_sector!=c->range_end[c->index]))
            return fail(c,COMP_SEG_CORRUPT);
        c->range_id[c->index]=plan.recording_id;c->range_binding[c->index]=plan.descriptor_binding;
        c->range_nonce[c->index]=plan.request_nonce;c->range_first[c->index]=plan.first_sector;c->range_end[c->index]=plan.end_sector;
        if(state==COMP_RANGE_PENDING){c->range_pending_slot=c->index;c->range_pending_page=c->target_slot;c->range_pending_record=c->scan;}
        c->scan++;c->phase=MOUNT_RANGE;break;}
    case MOUNT_PREVIOUS:
        if (!c->port.read(c->port.context,address(c,c->bank,c->slots[c->index]),scratch,256u)) return fail(c,COMP_SEG_IO_ERROR);
        if (!row_decode(c,scratch,&old) || !row_decode(c,c->page,&e) || !transition(&old,&e)) return fail(c,COMP_SEG_CORRUPT);
        c->generation++; apply_row(c,c->index,c->target_slot,e.state); c->target_slot++;
        c->phase=c->target_slot==COMP_SEGMENT_BANK_PAGES?MOUNT_FIRST:MOUNT_ROWS;
        if (c->phase==MOUNT_FIRST) c->scan=0u;
        break;
    case MOUNT_FIRST:
        while (c->scan<64u && c->slots[c->scan]==NO_SLOT) c->scan++;
        if (c->scan==64u) { c->mounted=true; c->phase=IDLE; return COMP_SEG_OK; }
        if (!c->port.read(c->port.context,address(c,c->bank,c->slots[c->scan]),c->page,256u)) return fail(c,COMP_SEG_IO_ERROR);
        c->index=(uint8_t)(c->scan+1u); c->phase=MOUNT_PAIR;
        break;
    case MOUNT_PAIR:
        while (c->index<64u && c->slots[c->index]==NO_SLOT) c->index++;
        if (c->index==64u) { c->scan++; c->phase=MOUNT_FIRST; break; }
        if (!c->port.read(c->port.context,address(c,c->bank,c->slots[c->index]),scratch,256u)) return fail(c,COMP_SEG_IO_ERROR);
        if (!row_decode(c,c->page,&e) || !row_decode(c,scratch,&old) || !separate(&e,&old)) return fail(c,COMP_SEG_CORRUPT);
        c->index++;
        break;
    default:return COMP_SEG_BAD_STATE;
    }
    return COMP_SEG_PENDING;
}

comp_segment_result_t comp_segment_catalog_poll(comp_segment_catalog_t *c)
{
    comp_segment_entry_t e,old;
    static const uint8_t committed[4]={0u,0u,0u,0u};
    uint32_t erased=0u;
    if (c==NULL) return COMP_SEG_BAD_ARGUMENT;
    if(c->phase<=MOUNT_RANGE_ENTRY)return comp_segment_catalog_mount_poll(c);
    switch (c->phase) {
    case RANGE_PREFLIGHT:
        if(!c->port.read(c->port.context,address(c,c->bank,c->slots[c->index]),c->page,256u))return fail(c,COMP_SEG_IO_ERROR);
        if(!row_decode(c,c->page,&old)||old.state!=COMP_SEG_UNSYNCED||c->page[6]!=c->index||
           !same_sealed(&old,c->pending))return fail(c,COMP_SEG_BAD_ARGUMENT);
        if(c->range_pending_slot!=NO_SLOT)return range_launch(c,c->range_pending_page,c->range_pending_record);
        if(c->range_page!=NO_SLOT&&c->next_slot==(uint8_t)(c->range_page+1u)&&c->range_record<COMP_RANGE_JOURNAL_RECORDS)
            return range_launch(c,c->range_page,c->range_record);
        if(c->next_slot>=COMP_SEGMENT_BANK_PAGES){c->cursor=0u;c->gc_has_v3=false;c->phase=GC_INTENT_BODY;}
        else{c->target_slot=c->next_slot;c->phase=RANGE_HEADER_BODY;}
        break;
    case RANGE_HEADER_BODY:
        comp_range_journal_header_prepare(c->page,c->uid,c->epoch,c->bank_serial,c->target_slot);
        if(!c->port.program(c->port.context,address(c,c->bank,c->target_slot),c->page,28u))return fail(c,COMP_SEG_IO_ERROR);
        c->phase=RANGE_HEADER_COMMIT;break;
    case RANGE_HEADER_COMMIT:
        if(!c->port.program(c->port.context,address(c,c->bank,c->target_slot)+28u,committed,4u))return fail(c,COMP_SEG_IO_ERROR);
        c->phase=RANGE_HEADER_VERIFY;break;
    case RANGE_HEADER_VERIFY:
        if(!c->port.read(c->port.context,address(c,c->bank,c->target_slot),c->page,256u))return fail(c,COMP_SEG_IO_ERROR);
        if(comp_range_journal_header_decode(c->page,c->uid,c->epoch,c->bank_serial,c->target_slot)!=COMP_RANGE_DONE||
           !uniform(c->page+32u,224u,255u))return fail(c,COMP_SEG_CORRUPT);
        c->range_page=c->target_slot;c->range_record=0u;c->next_slot=(uint8_t)(c->target_slot+1u);
        return range_launch(c,c->range_page,0u);
    case RANGE_RUN:{
        comp_segment_result_t r=comp_range_reclaim_poll(c->range_worker);
        if(r==COMP_SEG_PENDING)return r;
        if(r!=COMP_SEG_OK)return fail(c,r);
        const comp_range_plan_t *plan=&c->range_worker->plan;uint8_t slot=plan->slot;
        c->range_id[slot]=plan->recording_id;c->range_binding[slot]=plan->descriptor_binding;
        c->range_nonce[slot]=plan->request_nonce;c->range_first[slot]=plan->first_sector;c->range_end[slot]=plan->end_sector;
        if(c->range_pending_slot==NO_SLOT)c->range_record++;
        c->range_pending_slot=c->range_pending_page=c->range_pending_record=NO_SLOT;
        c->pending=NULL;c->range_worker=NULL;c->operation=OP_NONE;c->phase=IDLE;return COMP_SEG_OK;}
    case COMPACT_SCAN:
        while(c->scan<64u && c->slots[c->scan]==NO_SLOT)c->scan++;
        if(c->scan==64u){c->cursor=0u;c->phase=GC_INTENT_BODY;break;}
        if(!c->port.read(c->port.context,address(c,c->bank,c->slots[c->scan]),c->page,256u))return fail(c,COMP_SEG_IO_ERROR);
        if(!row_decode(c,c->page,&e))return fail(c,COMP_SEG_CORRUPT);
        if(e.state==COMP_SEG_SESSION_DISCARD||e.state==COMP_SEG_DISCARDING)return fail(c,COMP_SEG_BAD_STATE);
        c->scan++;break;
    case PREFLIGHT_KNOWN:case PREFLIGHT:
        while (c->scan<64u && c->slots[c->scan]==NO_SLOT) c->scan++;
        if (c->scan<64u) {
            if (!c->port.read(c->port.context,address(c,c->bank,c->slots[c->scan]),c->page,256u)) return fail(c,COMP_SEG_IO_ERROR);
            if (!row_decode(c,c->page,&old)) return fail(c,COMP_SEG_CORRUPT);
            if (old.descriptor.recording_id==c->pending->descriptor.recording_id) {
                if (c->index!=NO_SLOT || !same_identity(&old,c->pending)) return fail(c,COMP_SEG_BAD_STATE);
                if (c->operation==OP_PUT) {
                    if (!transition(&old,c->pending)) return fail(c,COMP_SEG_BAD_STATE);
                } else if (!same_sealed(&old,c->pending) ||
                           (c->operation==OP_ACK && old.state!=COMP_SEG_UNSYNCED && old.state!=COMP_SEG_ACKED) ||
                           (c->operation==OP_RECLAIM && old.state!=COMP_SEG_ACKED && old.state!=COMP_SEG_ERASING) ||
                           (c->operation==OP_RECLAIM && old.state!=c->pending->state) ||
                           (c->operation==OP_CANCEL && old.state!=COMP_SEG_WRITING) ||
                           (c->operation==OP_DISCARD && old.state!=COMP_SEG_UNSYNCED && old.state!=COMP_SEG_DISCARDING && old.state!=COMP_SEG_SESSION_DISCARD) ||
                           (c->operation==OP_SESSION_INTENT && old.state!=COMP_SEG_UNSYNCED))
                    return fail(c,COMP_SEG_BAD_STATE);
                if(c->operation==OP_SESSION_INTENT &&
                   (!c->pending_intent || !(c->pending_intent->slots&(UINT64_C(1)<<c->scan))))return fail(c,COMP_SEG_BAD_ARGUMENT);
                c->index=c->scan;
                if ((c->operation==OP_ACK && old.state==COMP_SEG_ACKED) ||
                    (c->operation==OP_RECLAIM && old.state==COMP_SEG_ERASING) ||
                    (c->operation==OP_DISCARD && old.state==COMP_SEG_DISCARDING)) c->cursor=1u;
            } else if (c->phase==PREFLIGHT_KNOWN || !separate(&old,c->pending)) return fail(c,COMP_SEG_BAD_STATE);
            c->scan=c->phase==PREFLIGHT_KNOWN?64u:(uint8_t)(c->scan+1u);
            c->phase=PREFLIGHT;break;
        }
        if (c->index==NO_SLOT) {
            if (c->operation!=OP_PUT || c->pending_state!=COMP_SEG_WRITING) return fail(c,COMP_SEG_NOT_FOUND);
            if (c->pending->descriptor.recording_id!=c->next_id) return fail(c,COMP_SEG_BAD_STATE);
            for (c->index=0u;c->index<64u;c->index++) if (c->slots[c->index]==NO_SLOT) break;
            if (c->index==64u) return fail(c,COMP_SEG_FULL);
        }
        if (c->cursor==1u) {
            c->cursor=0u;
            if (c->operation==OP_ACK) { c->pending=NULL; c->operation=OP_NONE; c->phase=IDLE; return COMP_SEG_OK; }
            c->cursor=c->operation==OP_RECLAIM?(uint32_t)c->range_end[c->index]*4096u:0u;
            if(c->cursor>reclaim_bytes(c))return fail(c,COMP_SEG_CORRUPT);
            if(c->cursor==reclaim_bytes(c)){c->pending_state=0u;append_or_gc(c);}else c->phase=RECLAIM;
        } else append_or_gc(c);
        break;
    case GC_INTENT_BODY:
        /* This marker is in the current root, outside its immutable CRC. It
         * authorizes retirement of only the opposite bank BEFORE erasing it.
         * Otherwise a power cut during an inactive-bank erase could make an
         * obsolete, partly erased root look like fatal current corruption. */
        memset(c->page,255,28u); memcpy(c->page,"GCI2",4u);
        comp_rec_put32(c->page+4u,c->bank_serial+1u); comp_rec_put32(c->page+8u,c->bank_serial);
        comp_rec_put32(c->page+12u,comp_rec_crc(c->page,12u));
        if (!c->port.program(c->port.context,address(c,c->bank,0u)+INTENT,c->page,24u)) return fail(c,COMP_SEG_IO_ERROR);
        c->phase=GC_INTENT_COMMIT;
        break;
    case GC_INTENT_COMMIT:
        if (!c->port.program(c->port.context,address(c,c->bank,0u)+INTENT_COMMIT,committed,4u)) return fail(c,COMP_SEG_IO_ERROR);
        c->phase=GC_INTENT_VERIFY;
        break;
    case GC_INTENT_VERIFY:
        if (!c->port.read(c->port.context,address(c,c->bank,0u),c->page,256u)) return fail(c,COMP_SEG_IO_ERROR);
        if (!root_valid(c,c->page) || !intent_valid(c->page) || comp_rec_get32(c->page+8u)!=c->bank_serial)
            return fail(c,COMP_SEG_CORRUPT);
        c->retire_authorized=true; c->phase=GC_ERASE;
        break;
    case GC_ERASE:
        if (!c->port.erase_step(c->port.context,c->banks[c->bank^1u]+c->cursor,
                              COMP_SEGMENT_BANK_BYTES-c->cursor,&erased)) return fail(c,COMP_SEG_IO_ERROR);
        if (erased%4096u!=0u || erased>COMP_SEGMENT_BANK_BYTES-c->cursor) return fail(c,COMP_SEG_IO_ERROR);
        c->cursor+=erased;
        if (c->cursor==COMP_SEGMENT_BANK_BYTES) c->phase=ROOT_BODY;
        break;
    case ROOT_BODY:
        root_encode(c);
        if (!c->port.program(c->port.context,address(c,c->operation==OP_FORMAT?0u:(uint8_t)(c->bank^1u),0u),c->page,252u))
            return fail(c,COMP_SEG_IO_ERROR);
        c->copy_slot=1u; c->scan=0u;
        c->phase=c->operation==OP_FORMAT?ROOT_COMMIT:GC_READ;
        break;
    case GC_READ:
        c->scan=gc_from(c,c->scan);
        if (c->scan==64u+COMP_SEGMENT_RECEIPT_CAPACITY) {c->scan=0u;c->phase=range_count(c)?GC_RANGE_HEADER:ROOT_COMMIT;break;}
        if (!c->port.read(c->port.context,address(c,c->bank,gc_slot(c,c->scan)),c->page,256u)) return fail(c,COMP_SEG_IO_ERROR);
        if (!row_decode(c,c->page,&e) || (c->scan<64u?(e.state==0u||c->page[6]!=c->scan):e.state!=0u))
            return fail(c,COMP_SEG_CORRUPT);
        if(c->page[4]==3u)c->gc_has_v3=true;
        comp_rec_put32(c->page+8u,c->generation); memset(c->page+COMMIT,255,4u);
        c->expected_crc=comp_rec_crc(c->page,ROW_CRC); comp_rec_put32(c->page+ROW_CRC,c->expected_crc);
        c->phase=GC_BODY;
        break;
    case GC_BODY:
        if (!c->port.program(c->port.context,address(c,(uint8_t)(c->bank^1u),c->copy_slot),c->page,252u)) return fail(c,COMP_SEG_IO_ERROR);
        c->phase=GC_COMMIT;
        break;
    case GC_COMMIT:
        if (!c->port.program(c->port.context,address(c,(uint8_t)(c->bank^1u),c->copy_slot)+COMMIT,committed,4u)) return fail(c,COMP_SEG_IO_ERROR);
        c->phase=GC_VERIFY;
        break;
    case GC_VERIFY:
        if (!c->port.read(c->port.context,address(c,(uint8_t)(c->bank^1u),c->copy_slot),c->page,256u)) return fail(c,COMP_SEG_IO_ERROR);
        if (!row_decode(c,c->page,&e) || (c->scan<64u?(e.state==0u||c->page[6]!=c->scan):e.state!=0u) ||
            comp_rec_get32(c->page+ROW_CRC)!=c->expected_crc)
            return fail(c,COMP_SEG_CORRUPT);
        c->copy_slot++; c->scan++; c->phase=GC_READ;
        break;
    case GC_RANGE_HEADER:
        if(!range_snapshot_page(c,&c->scan,c->bank_serial+1u,c->copy_slot,c->page))return fail(c,COMP_SEG_CORRUPT);
        c->expected_crc=comp_rec_crc(c->page,252u);c->phase=GC_RANGE_BODY;break;
    case GC_RANGE_BODY:
        if(!c->port.program(c->port.context,address(c,(uint8_t)(c->bank^1u),c->copy_slot),c->page,252u))return fail(c,COMP_SEG_IO_ERROR);
        c->phase=GC_RANGE_VERIFY;break;
    case GC_RANGE_VERIFY:
        if(!c->port.read(c->port.context,address(c,(uint8_t)(c->bank^1u),c->copy_slot),c->page,256u))return fail(c,COMP_SEG_IO_ERROR);
        if(comp_rec_crc(c->page,252u)!=c->expected_crc||!uniform(c->page+252u,4u,255u))return fail(c,COMP_SEG_CORRUPT);
        c->copy_slot++;
        while(c->scan<64u&&(c->slots[c->scan]==NO_SLOT||!c->range_nonce[c->scan]))c->scan++;
        c->phase=c->scan<64u?GC_RANGE_HEADER:ROOT_COMMIT;break;
    case ROOT_COMMIT:
        if (!c->port.program(c->port.context,address(c,c->operation==OP_FORMAT?0u:(uint8_t)(c->bank^1u),0u)+COMMIT,committed,4u))
            return fail(c,COMP_SEG_IO_ERROR);
        c->phase=ROOT_VERIFY;
        break;
    case ROOT_VERIFY:
        if (!c->port.read(c->port.context,address(c,c->operation==OP_FORMAT?0u:(uint8_t)(c->bank^1u),0u),c->page,256u))
            return fail(c,COMP_SEG_IO_ERROR);
        if (!root_valid(c,c->page) || comp_rec_get32(c->page+8u)!=c->bank_serial+1u ||
            comp_rec_get32(c->page+12u)!=c->generation || comp_rec_get32(c->page+16u)!=c->next_id ||
            comp_rec_get32(c->page+20u)!=live_count(c)) return fail(c,COMP_SEG_CORRUPT);
        c->bank_serial++;
        if (c->operation==OP_FORMAT) {
            c->mounted=true; c->phase=IDLE; c->operation=OP_NONE; c->root_blank_mask=0u; c->next_slot=1u;
            return COMP_SEG_OK;
        }
        c->bank^=1u; c->next_slot=1u; c->retire_authorized=false;c->legacy_dirty=c->gc_has_v3;
        for (unsigned i=0u;i<64u;i++) if (c->slots[i]!=NO_SLOT) c->slots[i]=c->next_slot++;
        {
            uint8_t prior_receipts[COMP_SEGMENT_RECEIPT_CAPACITY],count=0u;
            memcpy(prior_receipts,c->receipts,sizeof(prior_receipts));memset(c->receipts,NO_SLOT,sizeof(c->receipts));
            for(unsigned i=0u;i<COMP_SEGMENT_RECEIPT_CAPACITY;i++)
                if(prior_receipts[(c->receipt_next+i)%COMP_SEGMENT_RECEIPT_CAPACITY]!=NO_SLOT)c->receipts[count++]=c->next_slot++;
            c->receipt_next=(uint8_t)(count%COMP_SEGMENT_RECEIPT_CAPACITY);
        }
        c->next_slot=c->copy_slot;c->range_page=NO_SLOT;c->range_record=0u;
        if(c->operation==OP_COMPACT) {
            c->pending=NULL;c->operation=OP_NONE;c->phase=IDLE;return COMP_SEG_OK;
        }
        c->target_slot=c->next_slot;c->phase=c->operation==OP_RANGE?RANGE_HEADER_BODY:ROW_BODY;
        break;
    case ROW_BODY:
        row_encode(c);
        if (!c->port.program(c->port.context,address(c,c->bank,c->target_slot),c->page,252u)) return fail(c,COMP_SEG_IO_ERROR);
        c->phase=ROW_COMMIT;
        break;
    case ROW_COMMIT:
        if (!c->port.program(c->port.context,address(c,c->bank,c->target_slot)+COMMIT,committed,4u)) return fail(c,COMP_SEG_IO_ERROR);
        c->phase=ROW_VERIFY;
        break;
    case ROW_VERIFY:
        if (!c->port.read(c->port.context,address(c,c->bank,c->target_slot),c->page,256u)) return fail(c,COMP_SEG_IO_ERROR);
        if (!row_decode(c,c->page,&e) || c->page[6]!=c->index ||
            comp_rec_get32(c->page+ROW_CRC)!=c->expected_crc ||
            comp_rec_get32(c->page+8u)!=c->generation+1u) return fail(c,COMP_SEG_CORRUPT);
        c->generation++; c->next_slot=(uint8_t)(c->target_slot+1u);
        if(c->page[4]==3u)c->legacy_dirty=true;
        if (c->slots[c->index]==NO_SLOT) c->next_id++;
        apply_row(c,c->index,c->target_slot,c->pending_state);
        if ((c->operation==OP_RECLAIM && c->pending_state==COMP_SEG_ERASING) ||
            (c->operation==OP_DISCARD && c->pending_state==COMP_SEG_DISCARDING)) {
            c->cursor=c->operation==OP_RECLAIM?(uint32_t)c->range_end[c->index]*4096u:0u;
            if(c->cursor>reclaim_bytes(c))return fail(c,COMP_SEG_CORRUPT);
            if(c->cursor==reclaim_bytes(c)){c->pending_state=0u;append_or_gc(c);}else c->phase=RECLAIM;
            break; }
        c->pending=NULL; c->operation=OP_NONE; c->phase=IDLE;
        return COMP_SEG_OK;
    case RECLAIM:
        if(c->cursor>=reclaim_bytes(c))return fail(c,COMP_SEG_BAD_STATE);
        if (!c->port.erase_step(c->port.context,c->data_base+c->pending->extent_offset+c->cursor,
                              reclaim_bytes(c)-c->cursor,&erased)) return fail(c,COMP_SEG_IO_ERROR);
        if (erased%4096u!=0u || erased>reclaim_bytes(c)-c->cursor) return fail(c,COMP_SEG_IO_ERROR);
        c->cursor+=erased;
        if (c->cursor==reclaim_bytes(c)) { c->pending_state=c->operation==OP_DISCARD?COMP_SEG_DISCARDED:0u; append_or_gc(c); }
        break;
    default: return fail(c,COMP_SEG_BAD_STATE);
    }
    return COMP_SEG_PENDING;
}

comp_segment_result_t comp_segment_catalog_read_intent(comp_segment_catalog_t *c,uint8_t index,
    comp_segment_entry_t *out,comp_segment_discard_intent_t *intent)
{
    uint8_t page[256]; comp_segment_entry_t e;
    if (c==NULL || out==NULL || index>=64u) return COMP_SEG_BAD_ARGUMENT;
    if (!c->mounted || c->phase!=IDLE) return COMP_SEG_BAD_STATE;
    if (c->slots[index]==NO_SLOT) return COMP_SEG_NOT_FOUND;
    if (!c->port.read(c->port.context,address(c,c->bank,c->slots[index]),page,256u)) return fail(c,COMP_SEG_IO_ERROR);
    if (!row_decode(c,page,&e) || page[6]!=index) return fail(c,COMP_SEG_CORRUPT);
    if(intent) {intent->slots=0u;intent->max_id=0u;
        if(e.state==COMP_SEG_SESSION_DISCARD){intent->slots=comp_rec_get64(page+148u);intent->max_id=comp_rec_get32(page+156u);}}
    range_overlay(c,index,&e);*out=e; return COMP_SEG_OK;
}
comp_segment_result_t comp_segment_catalog_read(comp_segment_catalog_t *c,uint8_t index,comp_segment_entry_t *out)
{return comp_segment_catalog_read_intent(c,index,out,NULL);}
comp_segment_result_t comp_segment_catalog_read_scoped(comp_segment_catalog_t *c,uint8_t index,
    comp_segment_entry_t *out,comp_segment_catalog_scoped_read_fn read,void *context)
{
    uint8_t page[256];comp_segment_entry_t e;
    if(!c||!out||!read||index>=64u)return COMP_SEG_BAD_ARGUMENT;
    if(!c->mounted)return COMP_SEG_BAD_STATE;
    if(!comp_segment_catalog_transfer_readable(c))return COMP_SEG_PENDING;
    if(c->slots[index]==NO_SLOT)return COMP_SEG_NOT_FOUND;
    comp_segment_result_t r=read(context,address(c,c->bank,c->slots[index]),page,sizeof(page));
    if(r==COMP_SEG_PENDING)return r;
    if(r!=COMP_SEG_OK)return fail(c,COMP_SEG_IO_ERROR);
    if(!row_decode(c,page,&e)||page[6]!=index)return fail(c,COMP_SEG_CORRUPT);
    range_overlay(c,index,&e);*out=e;return COMP_SEG_OK;
}

comp_segment_result_t comp_segment_catalog_receipt_read(comp_segment_catalog_t *c,uint8_t index,comp_segment_entry_t *out)
{
    if(!out)return COMP_SEG_BAD_ARGUMENT;
    comp_segment_io_t io;comp_segment_result_t result=comp_segment_catalog_receipt_io(c,index,&io);
    if(result!=COMP_SEG_OK)return result;
    uint8_t page[256];comp_segment_entry_t e;
    if(!c->port.read(c->port.context,io.address,page,256u))return fail(c,COMP_SEG_IO_ERROR);
    if(!row_decode(c,page,&e)||e.state!=0u)return fail(c,COMP_SEG_CORRUPT);
    *out=e;return COMP_SEG_OK;
}

bool comp_segment_catalog_rebase_page(const comp_segment_catalog_t *c,uint32_t a,
    uint32_t b,uint32_t base,uint32_t bytes,uint32_t tail,uint32_t page,uint8_t out[256])
{
    if(!c || !out || page>=2u*COMP_SEGMENT_BANK_PAGES ||
       !geometry(a,b,base,bytes) || tail<base || tail>base+bytes || tail%4096u ||
       (!c->mounted && !c->blank_verified) || c->phase!=IDLE||comp_segment_catalog_range_pending(c))return false;
    memset(out,255,256u);
    if(!c->mounted || page>=COMP_SEGMENT_BANK_PAGES)return true;
    if(page>live_count(c)){
        uint32_t skip=(page-live_count(c)-1u)*COMP_RANGE_JOURNAL_RECORDS;
        if(skip>=range_count(c))return true;
        uint8_t cursor=0u;
        while(cursor<64u&&skip){if(c->slots[cursor]!=NO_SLOT&&c->range_nonce[cursor])skip--;cursor++;}
        return range_snapshot_page(c,&cursor,c->bank_serial+1u,page,out);
    }
    if(c->bank_serial==UINT32_MAX || c->generation==UINT32_MAX)return false;
    if(page==0u) {
        memcpy(out,"CSC2",4u);out[4]=1u;out[5]=0u;out[6]=64u;out[7]=0u;
        comp_rec_put32(out+8u,c->bank_serial+1u);comp_rec_put32(out+12u,c->generation+1u);
        comp_rec_put32(out+16u,c->next_id);comp_rec_put32(out+20u,live_count(c));
        comp_rec_put64(out+24u,c->epoch);memcpy(out+32u,c->uid,12u);
        comp_rec_put32(out+44u,base);comp_rec_put32(out+48u,bytes);
        comp_rec_put32(out+52u,a);comp_rec_put32(out+56u,b);
        comp_rec_put32(out+ROOT_CRC,comp_rec_crc(out,ROOT_CRC));
        memset(out+COMMIT,0,4u);return true;
    }
    uint32_t ordinal=0u;uint8_t selected=NO_SLOT;
    for(uint8_t index=0u;index<64u+COMP_SEGMENT_RECEIPT_CAPACITY;index++) {
        uint8_t slot=gc_slot(c,index);
        if(slot!=NO_SLOT && ++ordinal==page){selected=slot;break;}
    }
    comp_segment_entry_t old,next;
    if(selected==NO_SLOT || !c->port.read(c->port.context,address(c,c->bank,selected),out,256u) ||
       !row_decode(c,out,&old))return false;
    if(old.state!=0u) {
        if(!comp_segment_catalog_rebase_entry(&old,c->data_base,base,tail,&next))return false;
        comp_rec_put32(out+12u,next.extent_offset);
        comp_rec_put32(out+136u,next.provenance_extent_plus1);
    }
    out[4]=2u;comp_rec_put32(out+8u,c->generation+1u);
    comp_rec_put32(out+ROW_CRC,comp_rec_crc(out,ROW_CRC));return true;
}

comp_segment_result_t comp_segment_catalog_page(comp_segment_catalog_t *c,uint32_t snapshot,
    uint32_t nonce,uint32_t start,uint8_t *out,size_t capacity,size_t *out_bytes)
{
    comp_rec_v2_descriptor_t entries[2]; comp_segment_entry_t e;
    uint32_t total=0u,position=0u; uint8_t count=0u;
    if (out_bytes!=NULL) *out_bytes=0u;
    if (c==NULL || out==NULL || out_bytes==NULL || nonce==0u) return COMP_SEG_BAD_ARGUMENT;
    if (!c->mounted || c->phase!=IDLE) return COMP_SEG_BAD_STATE;
    if (snapshot!=c->generation) return COMP_SEG_STALE_SNAPSHOT;
    for (unsigned i=0u;i<64u;i++) if ((c->visible_mask&(UINT64_C(1)<<i))!=0u) total++;
    if (start>total || (total!=0u && start==total) || capacity<24u+(size_t)(total-start>2u?2u:total-start)*112u)
        return COMP_SEG_BAD_ARGUMENT;
    for (uint8_t i=0u;i<64u && count<2u;i++) if ((c->visible_mask&(UINT64_C(1)<<i))!=0u) {
        if (position++<start) continue;
        comp_segment_result_t r=comp_segment_catalog_read(c,i,&e);
        if (r!=COMP_SEG_OK) return r;
        if (e.state!=COMP_SEG_UNSYNCED && e.state!=COMP_SEG_ACKED) return fail(c,COMP_SEG_CORRUPT);
        entries[count++]=e.descriptor;
    }
    *out_bytes=comp_rec_v2_page_encode(snapshot,nonce,start,total,entries,count,out,capacity);
    return *out_bytes!=0u?COMP_SEG_OK:COMP_SEG_BAD_ARGUMENT;
}
