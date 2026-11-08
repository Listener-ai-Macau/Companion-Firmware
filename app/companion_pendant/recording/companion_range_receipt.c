#include "companion_range_receipt.h"
#include "wba_recording_crc.h"

_Static_assert(COMP_SEGMENT_PAGE_BYTES==256u && COMP_SEGMENT_SECTOR_BYTES==4096u,
               "CRR3 is bound to256B pages/4096B sectors");
/* Keep the legacy CSG2 page commit at252 erased. Resident Boot skips these
 * extension pages, while still validating every original row/generation. */
_Static_assert(32u+COMP_RANGE_JOURNAL_RECORDS*32u==224u,"legacy commit remains FF");

static bool all(const uint8_t *p,uint32_t bytes,uint8_t value)
{return !comp_rec_not_uniform(p,bytes,value);}
static uint16_t get16(const uint8_t *p)
{return (uint16_t)((uint16_t)p[0]|((uint16_t)p[1]<<8u));}
static uint32_t descriptor_binding(const comp_segment_entry_t *entry)
{
    uint8_t wire[COMP_REC_V2_DESCRIPTOR_BYTES];
    comp_rec_v2_descriptor_t normalized=entry->descriptor;normalized.sync_state=2u;
    if(!comp_rec_v2_encode(&normalized,wire,sizeof(wire)))return 0u;
    return comp_wba_recording_crc32(0u,wire,sizeof(wire));
}
static bool plan_fields(const comp_range_plan_t *p)
{
    return p && p->slot<COMP_SEGMENT_CAPACITY && p->recording_id &&
        p->request_nonce && p->end_sector>p->first_sector;
}
bool comp_range_plan(const comp_segment_entry_t *entry,uint8_t slot,
    uint16_t first,uint16_t end,uint32_t nonce,comp_range_plan_t *plan,
    uint32_t *encoded_begin,uint32_t *encoded_end)
{
    if(!entry||!plan||!encoded_begin||!encoded_end||slot>=COMP_SEGMENT_CAPACITY||
       entry->state!=COMP_SEG_UNSYNCED||!comp_rec_v2_valid(&entry->descriptor)||
       !entry->descriptor.recording_id||!entry->descriptor.encoded_length||
       !nonce||end<=first||entry->reserved_bytes%4096u||
       (uint32_t)end>entry->reserved_bytes/4096u)return false;
    uint64_t begin=first?((uint64_t)first*16u-1u)*COMP_SEGMENT_PAGE_DATA_BYTES:0u;
    uint64_t limit=((uint64_t)end*16u-1u)*COMP_SEGMENT_PAGE_DATA_BYTES;
    uint64_t pages=((uint64_t)entry->descriptor.encoded_length+
        COMP_SEGMENT_PAGE_DATA_BYTES-1u)/COMP_SEGMENT_PAGE_DATA_BYTES;
    uint64_t used_sectors=((pages+1u)*256u+4095u)/4096u;
    if(end>used_sectors||begin>=entry->descriptor.encoded_length)return false;
    if(limit>entry->descriptor.encoded_length)limit=entry->descriptor.encoded_length;
    if(limit<=begin||limit>UINT32_MAX)return false;
    *plan=(comp_range_plan_t){entry->descriptor.recording_id,nonce,descriptor_binding(entry),first,end,slot};
    *encoded_begin=(uint32_t)begin;*encoded_end=(uint32_t)limit;return true;
}
bool comp_range_plan_matches(const comp_range_plan_t *p,const comp_segment_entry_t *entry,uint8_t slot)
{
    comp_range_plan_t expected;uint32_t begin,end;
    return plan_fields(p)&&entry&&p->slot==slot&&
        comp_range_plan(entry,slot,p->first_sector,p->end_sector,p->request_nonce,&expected,&begin,&end)&&
        expected.recording_id==p->recording_id&&expected.descriptor_binding==p->descriptor_binding;
}
void comp_range_journal_header_prepare(uint8_t p[32],const uint8_t uid[12],
    uint64_t epoch,uint32_t serial,uint32_t index)
{
    memset(p,255,32u);memcpy(p,"CRR3",4u);comp_rec_put16(p+4u,1u);comp_rec_put16(p+6u,32u);
    comp_rec_put64(p+8u,epoch);comp_rec_put32(p+16u,serial);comp_rec_put32(p+20u,index);
    uint32_t seed=comp_wba_recording_crc32(0u,uid,12u);
    comp_rec_put32(p+24u,comp_wba_recording_crc32(seed,p,24u));
}
void comp_range_journal_snapshot_header_prepare(uint8_t p[32],const uint8_t uid[12],
    uint64_t epoch,uint32_t serial,uint32_t index)
{
    comp_range_journal_header_prepare(p,uid,epoch,serial,index);comp_rec_put16(p+4u,2u);
    uint32_t seed=comp_wba_recording_crc32(0u,uid,12u);
    comp_rec_put32(p+24u,comp_wba_recording_crc32(seed,p,24u));
}
bool comp_range_journal_is_snapshot(const uint8_t p[32])
{return p&&get16(p+4u)==2u;}
comp_range_journal_state_t comp_range_journal_header_decode(const uint8_t p[32],
    const uint8_t uid[12],uint64_t epoch,uint32_t serial,uint32_t index)
{
    if(!p||!uid)return COMP_RANGE_INVALID;
    if(all(p,32u,255u))return COMP_RANGE_EMPTY;
    if(!all(p+28u,4u,0u))return COMP_RANGE_TORN;
    uint32_t seed=comp_wba_recording_crc32(0u,uid,12u);
    if(!epoch||memcmp(p,"CRR3",4u)||(get16(p+4u)!=1u&&get16(p+4u)!=2u)||get16(p+6u)!=32u||
       comp_rec_get64(p+8u)!=epoch||comp_rec_get32(p+16u)!=serial||
       comp_rec_get32(p+20u)!=index||
       comp_rec_get32(p+24u)!=comp_wba_recording_crc32(seed,p,24u))return COMP_RANGE_INVALID;
    return COMP_RANGE_DONE;
}
static uint32_t record_crc(const uint8_t header[32],uint8_t index,const uint8_t record[32])
{
    uint32_t seed=comp_wba_recording_crc32(comp_rec_get32(header+24u),&index,1u);
    return comp_wba_recording_crc32(seed,record,20u);
}
bool comp_range_journal_record_prepare(uint8_t p[32],const uint8_t header[32],
    uint8_t index,const comp_range_plan_t *plan)
{
    if(!p||!header||index>=COMP_RANGE_JOURNAL_RECORDS||!plan_fields(plan)||
       memcmp(header,"CRR3",4u)||!all(header+28u,4u,0u))return false;
    memset(p,255,32u);comp_rec_put32(p,plan->recording_id);p[4]=plan->slot;p[5]=1u;
    comp_rec_put16(p+8u,plan->first_sector);comp_rec_put16(p+10u,plan->end_sector);
    comp_rec_put32(p+12u,plan->request_nonce);comp_rec_put32(p+16u,plan->descriptor_binding);
    comp_rec_put32(p+20u,record_crc(header,index,p));return true;
}
comp_range_journal_state_t comp_range_journal_record_decode(const uint8_t p[32],
    const uint8_t header[32],uint8_t index,comp_range_plan_t *out)
{
    if(!p||!header||!out||index>=COMP_RANGE_JOURNAL_RECORDS)return COMP_RANGE_INVALID;
    if(all(p,32u,255u))return COMP_RANGE_EMPTY;
    if(!all(p+28u,4u,0u))return COMP_RANGE_TORN;
    comp_range_plan_t plan={comp_rec_get32(p),comp_rec_get32(p+12u),comp_rec_get32(p+16u),
        get16(p+8u),get16(p+10u),p[4]};
    if(memcmp(header,"CRR3",4u)||!all(header+28u,4u,0u)||p[5]!=1u||p[6]!=255u||p[7]!=255u||
       !plan_fields(&plan)||comp_rec_get32(p+20u)!=record_crc(header,index,p))return COMP_RANGE_INVALID;
    *out=plan;
    return all(p+24u,4u,0u)?COMP_RANGE_DONE:COMP_RANGE_PENDING;
}
