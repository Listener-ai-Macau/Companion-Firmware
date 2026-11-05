#include "wba_shared_pool.h"
#include "companion_recording_wire.h"
#include "wba_update_service.h"
#include <string.h>

#define BANK_BYTES 8192u
#define SLOTS (BANK_BYTES/COMP_WBA_POOL_WIRE_BYTES)
#define HEAD_BYTES 128u
#define ENTRY_BYTES 72u
#define CRC_OFFSET 1020u
#define CURSOR_CHECKPOINT 65536u
#if UINTPTR_MAX == UINT32_MAX
_Static_assert(sizeof(comp_wba_pool_t)<=96u,"shared pool RAM budget exceeded");
#endif

typedef struct {
    uint64_t sequence,next_id,next_transaction,epoch;
    uint8_t uid[12],count;
} header_t;
typedef struct {
    const comp_wba_pool_lease_t *add,*replace;
    uint8_t add_count,index;
    bool remove;
} patch_t;

static bool io_read(comp_wba_pool_t *p,uint32_t at,uint8_t *out,size_t n)
{
    if(p->port.read(p->port.context,at,out,n))return true;
    p->ready=false;return false;
}
static uint32_t crc_add(uint32_t crc,const uint8_t *p,size_t n)
{
    for(size_t i=0u;i<n;i++) {
        crc^=p[i];
        for(uint8_t b=0u;b<8u;b++)crc=(crc>>1)^((crc&1u)?UINT32_C(0xEDB88320):0u);
    }
    return crc;
}
static bool uid_valid(const uint8_t *uid)
{return uid&&comp_rec_not_uniform(uid,12u,0u)&&comp_rec_not_uniform(uid,12u,255u);}
static void encode_header(const header_t *h,uint8_t wire[HEAD_BYTES])
{
    memset(wire,0,HEAD_BYTES);memcpy(wire,"CPL2",4u);
    comp_rec_put16(wire+4u,2u);comp_rec_put16(wire+6u,COMP_WBA_POOL_WIRE_BYTES);
    comp_rec_put64(wire+8u,h->sequence);comp_rec_put64(wire+16u,h->next_id);
    comp_rec_put64(wire+24u,h->next_transaction);memcpy(wire+32u,h->uid,12u);
    wire[44]=2u;wire[45]=h->count;comp_rec_put64(wire+48u,h->epoch);
    comp_rec_put32(wire+56u,COMP_WBA_V2_POOL_BASE);comp_rec_put32(wire+60u,COMP_WBA_V2_POOL_BYTES);
}
static bool decode_header(const uint8_t *wire,header_t *h)
{
    if(memcmp(wire,"CPL2",4u)||wire[4]!=2u||wire[5]!=0u||wire[6]!=0u||wire[7]!=4u||wire[44]!=2u||
       wire[45]>COMP_WBA_POOL_MAX_LEASES||wire[46]||wire[47]||
       comp_rec_get32(wire+56u)!=COMP_WBA_V2_POOL_BASE||
       comp_rec_get32(wire+60u)!=COMP_WBA_V2_POOL_BYTES||
       comp_rec_not_uniform(wire+64u,HEAD_BYTES-64u,0u))return false;
    h->sequence=comp_rec_get64(wire+8u);h->next_id=comp_rec_get64(wire+16u);
    h->next_transaction=comp_rec_get64(wire+24u);h->epoch=comp_rec_get64(wire+48u);
    memcpy(h->uid,wire+32u,12u);h->count=wire[45];
    return h->sequence&&h->next_id&&h->next_transaction&&h->epoch&&uid_valid(h->uid);
}
static void encode_entry(const comp_wba_pool_lease_t *e,uint8_t wire[ENTRY_BYTES])
{
    memset(wire,0,ENTRY_BYTES);comp_rec_put64(wire,e->id);comp_rec_put64(wire+8u,e->transaction_id);
    comp_rec_put32(wire+16u,e->object_id);comp_rec_put32(wire+20u,e->start);
    comp_rec_put32(wire+24u,e->bytes);comp_rec_put32(wire+28u,e->erase_cursor);
    comp_rec_put32(wire+32u,e->payload_bytes);memcpy(wire+36u,e->sha256,32u);
    wire[68]=e->owner;wire[69]=e->state;
}
static bool decode_entry(const uint8_t wire[ENTRY_BYTES],comp_wba_pool_lease_t *e)
{
    memset(e,0,sizeof(*e));e->id=comp_rec_get64(wire);e->transaction_id=comp_rec_get64(wire+8u);
    e->object_id=comp_rec_get32(wire+16u);e->start=comp_rec_get32(wire+20u);
    e->bytes=comp_rec_get32(wire+24u);e->erase_cursor=comp_rec_get32(wire+28u);
    e->payload_bytes=comp_rec_get32(wire+32u);memcpy(e->sha256,wire+36u,32u);
    e->owner=wire[68];e->state=wire[69];
    if(wire[70]||wire[71]||!e->id||!e->transaction_id||!e->object_id||
       e->owner<COMP_WBA_POOL_RECORDING||e->owner>COMP_WBA_POOL_MIGRATION||
       e->state<COMP_WBA_POOL_RESERVED||e->state>COMP_WBA_POOL_ERASING||
       e->start<COMP_WBA_V2_POOL_BASE||e->start%COMP_WBA_POOL_ERASE_BYTES||
       !e->bytes||e->bytes%COMP_WBA_POOL_ERASE_BYTES||
       e->start-COMP_WBA_V2_POOL_BASE>COMP_WBA_V2_POOL_BYTES||
       e->bytes>COMP_WBA_V2_POOL_BYTES-(e->start-COMP_WBA_V2_POOL_BASE)||
       e->payload_bytes>e->bytes||e->erase_cursor>e->bytes||e->erase_cursor%COMP_WBA_POOL_ERASE_BYTES||
       ((e->state!=COMP_WBA_POOL_PREPARING&&e->state!=COMP_WBA_POOL_ERASING)&&e->erase_cursor)||
       ((e->payload_bytes!=0u)!=comp_rec_not_uniform(e->sha256,32u,0u))||
       (e->state==COMP_WBA_POOL_SEALED&&!e->payload_bytes))return false;
    return true;
}
static bool read_entry(comp_wba_pool_t *p,uint32_t at,uint8_t index,comp_wba_pool_lease_t *e)
{
    uint8_t wire[ENTRY_BYTES];
    return io_read(p,at+HEAD_BYTES+(uint32_t)index*ENTRY_BYTES,wire,sizeof(wire))&&decode_entry(wire,e);
}
static bool overlaps(const comp_wba_pool_lease_t *a,const comp_wba_pool_lease_t *b)
{return a->start<b->start+b->bytes&&b->start<a->start+a->bytes;}
static bool snapshot(comp_wba_pool_t *p,uint32_t at,header_t *h,bool *occupied)
{
    uint8_t wire[HEAD_BYTES];uint32_t crc=UINT32_MAX,expected=0u;
    bool header_ok=false,padding_ok=true;
    *occupied=false;
    for(uint32_t offset=0u;offset<COMP_WBA_POOL_WIRE_BYTES;offset+=HEAD_BYTES) {
        if(!io_read(p,at+offset,wire,sizeof(wire)))return false;
        *occupied|=comp_rec_not_uniform(wire,sizeof(wire),255u);
        if(offset==0u) {
            if(!memcmp(wire,"CPL",3u)&&((wire[3]!=255u&&wire[3]!='2')||
                    (wire[4]!=255u&&wire[4]!=2u)||(wire[44]!=255u&&wire[44]!=2u))) {
                p->ready=false;return false;
            }
            header_ok=decode_header(wire,h);
        }
        const uint32_t bytes=offset+HEAD_BYTES>CRC_OFFSET?CRC_OFFSET-offset:HEAD_BYTES;
        crc=crc_add(crc,wire,bytes);
        if(offset+HEAD_BYTES==COMP_WBA_POOL_WIRE_BYTES)expected=comp_rec_get32(wire+HEAD_BYTES-4u);
        if(header_ok)for(uint32_t i=0u;i<bytes;i++)
            if(offset+i>=HEAD_BYTES+(uint32_t)h->count*ENTRY_BYTES&&wire[i])padding_ok=false;
    }
    if(!header_ok||!padding_ok||(~crc)!=expected)return false;
    for(uint8_t i=0u;i<h->count;i++) {
        comp_wba_pool_lease_t a,b;
        if(!read_entry(p,at,i,&a)||a.id>=h->next_id||a.transaction_id>=h->next_transaction)return false;
        for(uint8_t j=0u;j<i;j++)if(!read_entry(p,at,j,&b)||a.id==b.id||
                (a.owner==b.owner&&a.object_id==b.object_id)||overlaps(&a,&b))return false;
    }
    return true;
}
static bool same_snapshot(comp_wba_pool_t *p,uint32_t a,uint32_t b)
{
    uint8_t x[HEAD_BYTES],y[HEAD_BYTES];
    for(uint32_t i=0u;i<COMP_WBA_POOL_WIRE_BYTES;i+=HEAD_BYTES)
        if(!io_read(p,a+i,x,sizeof(x))||!io_read(p,b+i,y,sizeof(y))||memcmp(x,y,sizeof(x)))return false;
    return true;
}
static bool current(comp_wba_pool_t *p)
{
    header_t h;bool occupied;
    if(!p||!p->ready||!p->loaded)return false;
    if(!snapshot(p,p->active_offset,&h,&occupied)||h.sequence!=p->sequence||
       h.next_id!=p->next_lease_id||h.next_transaction!=p->next_transaction_id||
       h.count!=p->count||h.epoch!=p->format_epoch||memcmp(h.uid,p->device_uid,12u)) {
        p->ready=false;return false;
    }
    /* A second foreground owner can append while the selected old snapshot
     * remains perfectly CRC-valid. Detect newer roots before a stale writer
     * commits a snapshot that would silently lose its peer's reservation. */
    comp_wba_pool_t latest;
    if(!comp_wba_pool_mount(&latest,&p->port,p->device_uid,p->format_epoch)||!latest.loaded||
       latest.sequence!=p->sequence||latest.next_lease_id!=p->next_lease_id||
       latest.next_transaction_id!=p->next_transaction_id||latest.count!=p->count||
       !same_snapshot(p,p->active_offset,latest.active_offset)) {
        p->ready=false;return false;
    }
    memcpy(p->next_slot,latest.next_slot,sizeof(p->next_slot));p->current_mask=latest.current_mask;
    return true;
}
static bool space(comp_wba_pool_t *p)
{
    uint32_t cursor=COMP_WBA_V2_POOL_BASE,free_bytes=0u,largest=0u;
    for(uint8_t step=0u;step<=p->count;step++) {
        uint32_t start=COMP_WBA_V2_POOL_BASE+COMP_WBA_V2_POOL_BYTES,end=start;
        for(uint8_t i=0u;i<p->count;i++) {
            comp_wba_pool_lease_t e;
            if(!read_entry(p,p->active_offset,i,&e))return false;
            if(e.start>=cursor&&e.start<start){start=e.start;end=e.start+e.bytes;}
        }
        uint32_t gap=start-cursor;free_bytes+=gap;if(gap>largest)largest=gap;
        cursor=end;if(cursor==COMP_WBA_V2_POOL_BASE+COMP_WBA_V2_POOL_BYTES)break;
    }
    p->free_bytes=free_bytes;p->largest_extent=largest;return true;
}
bool comp_wba_pool_mount(comp_wba_pool_t *p,const comp_wba_pool_port_t *port,
                         const uint8_t uid[12],uint64_t epoch)
{
    if(!p)return false;
    memset(p,0,sizeof(*p));
    if(!port||!port->read||!port->program||!port->erase||!uid_valid(uid)||!epoch)return false;
    p->port=*port;memcpy(p->device_uid,uid,12u);p->format_epoch=epoch;p->ready=true;
    bool any=false;
    for(uint8_t bank=0u;bank<2u;bank++)for(uint8_t slot=0u;slot<SLOTS;slot++) {
        header_t h;bool occupied=false;
        uint32_t at=COMP_WBA_V2_POOL_META_BASE+(uint32_t)bank*BANK_BYTES+(uint32_t)slot*COMP_WBA_POOL_WIRE_BYTES;
        bool valid=snapshot(p,at,&h,&occupied);
        if(!p->ready)return false;
        if(occupied){any=true;p->next_slot[bank]=(uint8_t)(slot+1u);}
        if(!valid)continue;
        if(memcmp(h.uid,uid,12u)||h.epoch!=epoch)goto bad;
        if(p->loaded) {
            if((h.sequence>p->sequence&&(h.next_id<p->next_lease_id||h.next_transaction<p->next_transaction_id))||
               (h.sequence<p->sequence&&(h.next_id>p->next_lease_id||h.next_transaction>p->next_transaction_id)))goto bad;
            if(h.sequence==p->sequence&&!same_snapshot(p,p->active_offset,at))goto bad;
        }
        if(!p->loaded||h.sequence>p->sequence) {
            p->sequence=h.sequence;p->next_lease_id=h.next_id;p->next_transaction_id=h.next_transaction;
            p->count=h.count;p->active_offset=at;p->loaded=true;p->current_mask=0u;
        }
        if(h.sequence==p->sequence)p->current_mask|=(uint8_t)(1u<<bank);
    }
    if(any&&!p->loaded)goto bad;
    if(p->loaded&&!space(p))goto bad;
    return true;
bad:
    p->ready=false;return false;
}
static bool write_checked(comp_wba_pool_t *p,uint32_t at,const uint8_t *wire,size_t n,uint32_t *crc)
{
    uint8_t readback[HEAD_BYTES];
    if(n>sizeof(readback)||!p->port.program(p->port.context,at,wire,n)||
       !io_read(p,at,readback,n)||memcmp(wire,readback,n)){p->ready=false;return false;}
    if(crc)*crc=crc_add(*crc,wire,n);
    return true;
}
static bool slot_prepare(comp_wba_pool_t *p,uint8_t bank,uint32_t *at)
{
    uint8_t blank[HEAD_BYTES];
    uint32_t base=COMP_WBA_V2_POOL_META_BASE+(uint32_t)bank*BANK_BYTES;
    if(p->next_slot[bank]>=SLOTS) {
        for(uint32_t i=0u;i<BANK_BYTES;i+=COMP_WBA_POOL_ERASE_BYTES)
            if(!p->port.erase(p->port.context,base+i)){p->ready=false;return false;}
        p->next_slot[bank]=0u;
    }
    *at=base+(uint32_t)p->next_slot[bank]*COMP_WBA_POOL_WIRE_BYTES;
    for(uint32_t i=0u;i<COMP_WBA_POOL_WIRE_BYTES;i+=HEAD_BYTES)
        if(!io_read(p,*at+i,blank,sizeof(blank))||comp_rec_not_uniform(blank,sizeof(blank),255u)) {
            p->ready=false;return false;
        }
    return true;
}
static bool patch_entry(comp_wba_pool_t *p,const patch_t *patch,uint8_t index,comp_wba_pool_lease_t *e)
{
    if(patch->add_count&&index>=p->count){*e=patch->add[index-p->count];return true;}
    if(patch->replace&&index==patch->index){*e=*patch->replace;return true;}
    uint8_t old=(uint8_t)(index+((patch->remove&&index>=patch->index)?1u:0u));
    return read_entry(p,p->active_offset,old,e);
}
static bool commit(comp_wba_pool_t *p,const header_t *next,const patch_t *patch)
{
    uint8_t wire[HEAD_BYTES];uint32_t a,b,crc=UINT32_MAX,offset=HEAD_BYTES;
    /* Always write the peer of the selected source first. On rollover the
     * source stays intact until the first complete new root is verified. */
    uint8_t first=p->loaded?(uint8_t)(1u-((p->active_offset-COMP_WBA_V2_POOL_META_BASE)/BANK_BYTES)):0u;
    if(!slot_prepare(p,first,&a))return false;
    encode_header(next,wire);if(!write_checked(p,a,wire,sizeof(wire),&crc))return false;
    for(uint8_t i=0u;i<next->count;i++) {
        comp_wba_pool_lease_t e;
        if(!patch_entry(p,patch,i,&e)){p->ready=false;return false;}
        encode_entry(&e,wire);if(!write_checked(p,a+offset,wire,ENTRY_BYTES,&crc))return false;
        offset+=ENTRY_BYTES;
    }
    memset(wire,0,sizeof(wire));
    while(offset<CRC_OFFSET) {
        uint32_t n=CRC_OFFSET-offset;if(n>HEAD_BYTES)n=HEAD_BYTES;
        if(!write_checked(p,a+offset,wire,n,&crc))return false;
        offset+=n;
    }
    comp_rec_put32(wire,~crc);if(!write_checked(p,a+CRC_OFFSET,wire,4u,NULL))return false;
    header_t checked;bool occupied;
    if(!snapshot(p,a,&checked,&occupied)||checked.sequence!=next->sequence){p->ready=false;return false;}
    uint8_t second=(uint8_t)(first^1u);
    if(!slot_prepare(p,second,&b))return false;
    for(offset=0u;offset<COMP_WBA_POOL_WIRE_BYTES;offset+=HEAD_BYTES)
        if(!io_read(p,a+offset,wire,sizeof(wire))||!write_checked(p,b+offset,wire,sizeof(wire),NULL))return false;
    if(!snapshot(p,b,&checked,&occupied)||!same_snapshot(p,a,b)){p->ready=false;return false;}
    p->next_slot[first]++;p->next_slot[second]++;
    p->sequence=next->sequence;p->next_lease_id=next->next_id;p->next_transaction_id=next->next_transaction;
    p->count=next->count;p->active_offset=a;p->current_mask=3u;p->loaded=true;
    if(!space(p)){p->ready=false;return false;}
    return true;
}
static header_t next_header(const comp_wba_pool_t *p)
{
    header_t h={p->sequence+1u,p->next_lease_id,p->next_transaction_id,p->format_epoch,{0},p->count};
    memcpy(h.uid,p->device_uid,12u);return h;
}
bool comp_wba_pool_initialize_blank(comp_wba_pool_t *p)
{
    uint8_t wire[HEAD_BYTES];
    if(!p||!p->ready||p->loaded)return false;
    for(uint32_t at=COMP_WBA_V2_POOL_BASE;at<COMP_WBA_V2_POOL_BASE+COMP_WBA_V2_POOL_BYTES;at+=HEAD_BYTES)
        if(!io_read(p,at,wire,sizeof(wire))||comp_rec_not_uniform(wire,sizeof(wire),255u))return false;
    header_t h=next_header(p);h.next_id=1u;h.next_transaction=1u;
    const patch_t patch={0};return commit(p,&h,&patch);
}
bool comp_wba_pool_initialize_import(comp_wba_pool_t *p,const comp_wba_pool_port_t *port,
    const uint8_t uid[12],uint64_t epoch,const comp_wba_pool_lease_t *entries,size_t count,
    uint64_t next_id,uint64_t next_transaction)
{
    if(!p)return false;
    memset(p,0,sizeof(*p));
    if(!port||!port->read||!port->program||!port->erase||!uid_valid(uid)||!epoch||
       !entries||!count||count>COMP_WBA_POOL_MAX_LEASES||!next_id||!next_transaction)return false;
    p->port=*port;p->ready=true;memcpy(p->device_uid,uid,12u);p->format_epoch=epoch;
    uint8_t wire[COMP_WBA_POOL_WIRE_BYTES],checked[HEAD_BYTES];
    header_t h={1u,next_id,next_transaction,epoch,{0},(uint8_t)count};memcpy(h.uid,uid,12u);
    memset(wire,0,sizeof(wire));encode_header(&h,wire);
    for(size_t i=0u;i<count;i++) {
        comp_wba_pool_lease_t decoded;uint8_t encoded[ENTRY_BYTES];encode_entry(entries+i,encoded);
        if(!decode_entry(encoded,&decoded)||decoded.id>=next_id||decoded.transaction_id>=next_transaction||
           (decoded.owner!=COMP_WBA_POOL_RECORDING&&decoded.owner!=COMP_WBA_POOL_MIGRATION))goto bad;
        for(size_t j=0u;j<i;j++)if(decoded.id==entries[j].id||overlaps(&decoded,entries+j)||
            (decoded.owner==entries[j].owner&&decoded.object_id==entries[j].object_id))goto bad;
        memcpy(wire+HEAD_BYTES+i*ENTRY_BYTES,encoded,ENTRY_BYTES);
    }
    comp_rec_put32(wire+CRC_OFFSET,comp_rec_crc(wire,CRC_OFFSET));
    /* Validate BOTH complete banks before any write. The only permissible
     * old bits are erased bits or bits from this exact initial snapshot. */
    bool complete=true;
    for(uint8_t bank=0u;bank<2u;bank++) {
      header_t found;bool occupied=false;
      bool valid=snapshot(p,COMP_WBA_V2_POOL_META_BASE+(uint32_t)bank*BANK_BYTES,&found,&occupied);
      if(!p->ready)return false;
      for(uint32_t off=0u;off<BANK_BYTES;off+=HEAD_BYTES) {
        uint32_t at=COMP_WBA_V2_POOL_META_BASE+(uint32_t)bank*BANK_BYTES+off;
        if(!io_read(p,at,checked,sizeof(checked)))return false;
        for(size_t i=0u;i<sizeof(checked);i++) {
            uint8_t expected=off<COMP_WBA_POOL_WIRE_BYTES?wire[off+i]:255u;
            if(valid&&off<COMP_WBA_POOL_WIRE_BYTES&&checked[i]!=expected)goto bad;
            if(checked[i]!=expected)complete=false;
            if((checked[i]&expected)!=expected)goto bad;
        }
      }
    }
    /* No erases: interrupted root writes can be completed monotonically.
     * The migration controller keeps every other writer disabled. */
    if(!complete)for(uint8_t bank=0u;bank<2u;bank++)for(uint32_t off=0u;off<COMP_WBA_POOL_WIRE_BYTES;off+=HEAD_BYTES)
        if(!write_checked(p,COMP_WBA_V2_POOL_META_BASE+(uint32_t)bank*BANK_BYTES+off,wire+off,HEAD_BYTES,NULL))return false;
    if(!comp_wba_pool_mount(p,port,uid,epoch)||p->sequence!=1u||p->current_mask!=3u)return false;
    return true;
bad:
    p->ready=false;return false;
}
static bool find_index(comp_wba_pool_t *p,uint64_t id,uint8_t *index,comp_wba_pool_lease_t *e)
{
    for(uint8_t i=0u;i<p->count;i++) {
        if(!read_entry(p,p->active_offset,i,e)){p->ready=false;return false;}
        if(e->id==id){*index=i;return true;}
    }
    return false;
}
bool comp_wba_pool_find(comp_wba_pool_t *p,uint64_t id,comp_wba_pool_lease_t *e)
{uint8_t index;return e&&current(p)&&find_index(p,id,&index,e);}
static bool first_fit(comp_wba_pool_t *p,const comp_wba_pool_lease_t *extra,uint8_t n,uint32_t bytes,uint32_t *at)
{
    uint32_t cursor=COMP_WBA_V2_POOL_BASE;
    for(uint8_t pass=0u;pass<=(uint8_t)(p->count+n);pass++) {
        uint32_t start=COMP_WBA_V2_POOL_BASE+COMP_WBA_V2_POOL_BYTES,end=start;
        for(uint8_t i=0u;i<(uint8_t)(p->count+n);i++) {
            comp_wba_pool_lease_t e;
            if(i<p->count){if(!read_entry(p,p->active_offset,i,&e))return false;}else e=extra[i-p->count];
            if(e.start>=cursor&&e.start<start){start=e.start;end=e.start+e.bytes;}
        }
        if(bytes<=start-cursor){*at=cursor;return true;}
        cursor=end;if(cursor==COMP_WBA_V2_POOL_BASE+COMP_WBA_V2_POOL_BYTES)break;
    }
    return false;
}
bool comp_wba_pool_reserve(comp_wba_pool_t *p,const comp_wba_pool_request_t *requests,
                           size_t count,comp_wba_pool_lease_t *leases)
{
    comp_wba_pool_lease_t added[COMP_WBA_POOL_MAX_RESERVE];
    if(!requests||!leases||!count||count>COMP_WBA_POOL_MAX_RESERVE||!current(p)||
       count>COMP_WBA_POOL_MAX_LEASES-p->count||p->sequence==UINT64_MAX||
       p->next_transaction_id==UINT64_MAX||count>UINT64_MAX-p->next_lease_id)return false;
    for(uint8_t i=0u;i<(uint8_t)count;i++) {
        const comp_wba_pool_request_t *r=&requests[i];comp_wba_pool_lease_t *e=&added[i];
        if(!r->object_id||!r->bytes||r->bytes>COMP_WBA_V2_POOL_BYTES||r->owner<1u||r->owner>5u||
           r->payload_bytes>r->bytes||((r->payload_bytes!=0u)!=comp_rec_not_uniform(r->sha256,32u,0u)))return false;
        for(uint8_t j=0u;j<(uint8_t)(p->count+i);j++) {
            comp_wba_pool_lease_t existing;
            if(j<p->count){if(!read_entry(p,p->active_offset,j,&existing))return false;}else existing=added[j-p->count];
            if(existing.owner==r->owner&&existing.object_id==r->object_id)return false;
        }
        memset(e,0,sizeof(*e));e->id=p->next_lease_id+i;e->transaction_id=p->next_transaction_id;e->object_id=r->object_id;
        e->bytes=(r->bytes+COMP_WBA_POOL_ERASE_BYTES-1u)&~(COMP_WBA_POOL_ERASE_BYTES-1u);
        e->payload_bytes=r->payload_bytes;memcpy(e->sha256,r->sha256,32u);e->owner=r->owner;e->state=COMP_WBA_POOL_RESERVED;
        if(!first_fit(p,added,i,e->bytes,&e->start))return false;
    }
    header_t next=next_header(p);next.next_id+=count;next.next_transaction++;next.count=(uint8_t)(next.count+count);
    patch_t patch={added,NULL,(uint8_t)count,0u,false};
    if(!commit(p,&next,&patch))return false;
    memcpy(leases,added,count*sizeof(*leases));return true;
}
static bool replace(comp_wba_pool_t *p,uint8_t index,const comp_wba_pool_lease_t *e)
{
    if(p->sequence==UINT64_MAX)return false;
    header_t h=next_header(p);patch_t patch={NULL,e,0u,index,false};return commit(p,&h,&patch);
}
bool comp_wba_pool_prepare(comp_wba_pool_t *p,uint64_t id)
{
    comp_wba_pool_lease_t e;uint8_t index;
    if(!current(p)||!find_index(p,id,&index,&e))return false;
    if(e.state==COMP_WBA_POOL_PREPARING||e.state==COMP_WBA_POOL_WRITING)return true;
    if(e.state!=COMP_WBA_POOL_RESERVED)return false;
    e.state=COMP_WBA_POOL_PREPARING;e.erase_cursor=0u;return replace(p,index,&e);
}
bool comp_wba_pool_poll_erase(comp_wba_pool_t *p,uint64_t id,bool *done)
{
    comp_wba_pool_lease_t e;uint8_t index;uint8_t wire[HEAD_BYTES];
    if(!done||!current(p)||!find_index(p,id,&index,&e))return false;
    *done=false;
    if(e.state==COMP_WBA_POOL_WRITING){*done=true;return true;}
    if(e.state!=COMP_WBA_POOL_PREPARING&&e.state!=COMP_WBA_POOL_ERASING)return false;
    uint32_t cursor=p->pending_id==id?p->pending_cursor:e.erase_cursor;
    if(cursor<e.erase_cursor||cursor>e.bytes)return false;
    if(cursor<e.bytes) {
        if(!p->port.erase(p->port.context,e.start+cursor))return false;
        for(uint32_t i=0u;i<COMP_WBA_POOL_ERASE_BYTES;i+=HEAD_BYTES)
            if(!io_read(p,e.start+cursor+i,wire,sizeof(wire))||comp_rec_not_uniform(wire,sizeof(wire),255u))return false;
        cursor+=COMP_WBA_POOL_ERASE_BYTES;
    }
    if(cursor==e.bytes) {
        bool ok;
        if(e.state==COMP_WBA_POOL_ERASING) {
            if(p->sequence==UINT64_MAX)return false;
            header_t h=next_header(p);h.count--;patch_t patch={NULL,NULL,0u,index,true};ok=commit(p,&h,&patch);
        }else {e.state=COMP_WBA_POOL_WRITING;e.erase_cursor=0u;ok=replace(p,index,&e);}
        if(!ok)return false;
        p->pending_id=0u;p->pending_cursor=0u;*done=true;return true;
    }
    if(cursor-e.erase_cursor>=CURSOR_CHECKPOINT){e.erase_cursor=cursor;if(!replace(p,index,&e))return false;}
    p->pending_id=id;p->pending_cursor=cursor;return true;
}
bool comp_wba_pool_write(comp_wba_pool_t *p,uint64_t id,uint32_t offset,const uint8_t *data,size_t n)
{
    comp_wba_pool_lease_t e;uint8_t index,wire[HEAD_BYTES];
    if(!data||!n||!current(p)||!find_index(p,id,&index,&e)||e.state!=COMP_WBA_POOL_WRITING)return false;
    uint32_t limit=e.payload_bytes?e.payload_bytes:e.bytes;
    if(offset>limit||n>limit-offset)return false;
    if(!p->port.program(p->port.context,e.start+offset,data,n))return false;
    for(size_t i=0u;i<n;i+=sizeof(wire)) {
        size_t length=n-i<sizeof(wire)?n-i:sizeof(wire);
        if(!io_read(p,e.start+offset+(uint32_t)i,wire,length)||memcmp(wire,data+i,length))return false;
    }
    return true;
}
bool comp_wba_pool_seal(comp_wba_pool_t *p,uint64_t id,uint32_t bytes,const uint8_t sha[32])
{
    comp_wba_pool_lease_t e;uint8_t index,wire[HEAD_BYTES],digest[32];comp_wba_update_sha256_t hash;
    if(!sha||!bytes||!comp_rec_not_uniform(sha,32u,0u)||!current(p)||!find_index(p,id,&index,&e))return false;
    if(e.state==COMP_WBA_POOL_SEALED)return e.payload_bytes==bytes&&!memcmp(e.sha256,sha,32u);
    if(e.state!=COMP_WBA_POOL_WRITING||bytes>e.bytes||
       (e.payload_bytes&&(e.payload_bytes!=bytes||memcmp(e.sha256,sha,32u))))return false;
    comp_wba_update_sha256_init(&hash);
    for(uint32_t offset=0u;offset<bytes;offset+=HEAD_BYTES) {
        uint32_t n=bytes-offset;if(n>HEAD_BYTES)n=HEAD_BYTES;
        if(!io_read(p,e.start+offset,wire,n))return false;
        comp_wba_update_sha256_update(&hash,wire,n);
    }
    comp_wba_update_sha256_final(&hash,digest);if(memcmp(digest,sha,32u))return false;
    e.state=COMP_WBA_POOL_SEALED;e.payload_bytes=bytes;memcpy(e.sha256,sha,32u);return replace(p,index,&e);
}
bool comp_wba_pool_retire(comp_wba_pool_t *p,uint64_t id,uint64_t transaction,const uint8_t sha[32])
{
    comp_wba_pool_lease_t e;uint8_t index;
    if(!sha||!current(p)||!find_index(p,id,&index,&e)||transaction!=e.transaction_id||memcmp(sha,e.sha256,32u))return false;
    if(e.state==COMP_WBA_POOL_ERASING)return true;
    e.state=COMP_WBA_POOL_ERASING;e.erase_cursor=0u;
    if(!replace(p,index,&e))return false;
    p->pending_id=0u;p->pending_cursor=0u;return true;
}
