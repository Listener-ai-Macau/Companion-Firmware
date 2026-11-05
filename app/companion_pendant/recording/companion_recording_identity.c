#include "companion_recording_identity.h"
#include "companion_recording_wire.h"
#include <string.h>

#define SLOTS (COMP_REC_IDENTITY_BANK_BYTES/COMP_REC_IDENTITY_SLOT_BYTES)

static bool valid_uid(const uint8_t uid[12])
{return uid&&comp_rec_not_uniform(uid,12u,0u)&&comp_rec_not_uniform(uid,12u,255u);}
static bool valid(const comp_rec_identity_record_t *r)
{
    if(!r->sequence||!r->format_epoch||!r->next_session_id||r->count>COMP_REC_IDENTITY_MAPS||!valid_uid(r->device_uid))return false;
    for(size_t i=0u;i<r->count;i++) {
        if(!r->maps[i].recording_id||!r->maps[i].session_id||r->maps[i].session_id>=r->next_session_id)return false;
        for(size_t j=0u;j<i;j++)if(r->maps[i].recording_id==r->maps[j].recording_id||r->maps[i].session_id==r->maps[j].session_id)return false;
    }
    return true;
}
static bool encode(const comp_rec_identity_record_t *r,uint8_t p[COMP_REC_IDENTITY_WIRE_BYTES])
{
    if(!valid(r))return false;
    memset(p,0,COMP_REC_IDENTITY_WIRE_BYTES);memcpy(p,"CSI1",4u);comp_rec_put16(p+4u,1u);comp_rec_put16(p+6u,COMP_REC_IDENTITY_WIRE_BYTES);
    comp_rec_put64(p+8u,r->sequence);comp_rec_put64(p+16u,r->format_epoch);comp_rec_put64(p+24u,r->next_session_id);
    memcpy(p+32u,r->device_uid,12u);p[44]=1u;p[45]=r->count;
    for(size_t i=0u;i<r->count;i++){comp_rec_put32(p+48u+12u*i,r->maps[i].recording_id);comp_rec_put64(p+52u+12u*i,r->maps[i].session_id);}
    comp_rec_put32(p+156u,comp_rec_crc(p,156u));return true;
}
static bool decode(const uint8_t p[COMP_REC_IDENTITY_SLOT_BYTES],comp_rec_identity_record_t *r)
{
    if(memcmp(p,"CSI1",4u)||p[4]!=1u||p[5]!=0u||p[6]!=COMP_REC_IDENTITY_WIRE_BYTES||p[7]!=0u||p[44]!=1u||p[45]>COMP_REC_IDENTITY_MAPS||
       p[46]!=0u||p[47]!=0u||comp_rec_get32(p+156u)!=comp_rec_crc(p,156u)||
       comp_rec_not_uniform(p+160u,96u,255u))return false;
    for(size_t i=48u+(size_t)p[45]*12u;i<156u;i++)if(p[i]!=0u)return false;
    memset(r,0,sizeof(*r));r->sequence=comp_rec_get64(p+8u);r->format_epoch=comp_rec_get64(p+16u);r->next_session_id=comp_rec_get64(p+24u);
    memcpy(r->device_uid,p+32u,12u);r->count=p[45];
    for(size_t i=0u;i<r->count;i++){r->maps[i].recording_id=comp_rec_get32(p+48u+12u*i);r->maps[i].session_id=comp_rec_get64(p+52u+12u*i);}
    return valid(r);
}
bool comp_rec_identity_mount(comp_rec_identity_t *s,const comp_rec_identity_port_t *port,const uint8_t uid[12])
{
    uint8_t p[COMP_REC_IDENTITY_SLOT_BYTES],selected[COMP_REC_IDENTITY_WIRE_BYTES];
    comp_rec_identity_record_t r;bool occupied=false;
    if(!s)return false;
    memset(s,0,sizeof(*s));
    if(!port||!port->read||!port->program||!port->erase||!valid_uid(uid))return false;
    s->port=*port;memcpy(s->record.device_uid,uid,12u);
    for(uint8_t bank=0u;bank<2u;bank++)for(uint8_t slot=0u;slot<SLOTS;slot++) {
        if(!port->read(port->context,(uint32_t)bank*COMP_REC_IDENTITY_BANK_BYTES+(uint32_t)slot*COMP_REC_IDENTITY_SLOT_BYTES,p,sizeof(p)))return false;
        if(!comp_rec_not_uniform(p,sizeof(p),255u))continue;
        occupied=true;s->next_slot[bank]=(uint8_t)(slot+1u);
        /* Future CSI namespaces cannot be silently interpreted as old data. */
        if(!memcmp(p,"CSI",3u)&&((p[3]!=255u&&p[3]!='1')||(p[4]!=255u&&p[4]!=1u)||(p[44]!=255u&&p[44]!=1u)))return false;
        if(!decode(p,&r))continue;
        if(memcmp(r.device_uid,uid,12u))return false;
        if(s->loaded) {
            if(r.format_epoch!=s->record.format_epoch)return false;
            if(r.sequence==s->record.sequence&&memcmp(selected,p,sizeof(selected)))return false;
            if((r.sequence>s->record.sequence&&r.next_session_id<=s->record.next_session_id)||
               (r.sequence<s->record.sequence&&r.next_session_id>=s->record.next_session_id))return false;
        }
        if(!s->loaded||r.sequence>s->record.sequence){s->record=r;memcpy(selected,p,sizeof(selected));s->loaded=true;s->current_copy[0]=s->current_copy[1]=false;}
        if(r.sequence==s->record.sequence)s->current_copy[bank]=true;
    }
    if(occupied&&!s->loaded)return false;
    s->ready=true;return true;
}
static bool live(const uint32_t *ids,size_t count,uint32_t id)
{for(size_t i=0u;i<count;i++)if(ids[i]==id)return true;return false;}
bool comp_rec_identity_find(const comp_rec_identity_t *s,uint32_t id,uint64_t *session)
{
    if(!s||!s->ready||!s->loaded||!id||!session)return false;
    for(size_t i=0u;i<s->record.count;i++)if(s->record.maps[i].recording_id==id){*session=s->record.maps[i].session_id;return true;}
    return false;
}
static bool persist(comp_rec_identity_t *s,const comp_rec_identity_record_t *next,uint64_t *session)
{
    uint8_t p[COMP_REC_IDENTITY_WIRE_BYTES],verify[COMP_REC_IDENTITY_SLOT_BYTES];
    if(!encode(next,p))return false;
    /* Write the bank that lacks the current namespace first. If both have a
     * copy, either order is safe. During rollover the peer remains intact. */
    uint8_t first=(s->current_copy[0]&&!s->current_copy[1])?1u:0u;
    for(uint8_t index=0u;index<2u;index++) {
        uint8_t bank=(uint8_t)(first^index);
        if(s->next_slot[bank]>=SLOTS) {
            if(!s->port.erase(s->port.context,(uint32_t)bank*COMP_REC_IDENTITY_BANK_BYTES))goto uncertain;
            s->next_slot[bank]=0u;
        }
        uint32_t offset=(uint32_t)bank*COMP_REC_IDENTITY_BANK_BYTES+(uint32_t)s->next_slot[bank]*COMP_REC_IDENTITY_SLOT_BYTES;
        if(!s->port.read(s->port.context,offset,verify,sizeof(verify))||comp_rec_not_uniform(verify,sizeof(verify),255u)||
           !s->port.program(s->port.context,offset,p,sizeof(p))||!s->port.read(s->port.context,offset,verify,sizeof(verify))||
           memcmp(p,verify,sizeof(p))||comp_rec_not_uniform(verify+160u,96u,255u))goto uncertain;
        s->next_slot[bank]++;
    }
    s->record=*next;s->loaded=true;s->current_copy[0]=s->current_copy[1]=true;*session=next->next_session_id-1u;return true;
uncertain:
    s->ready=false;return false;
}
bool comp_rec_identity_reserve(comp_rec_identity_t *s,uint32_t id,
    const uint32_t *ids,size_t count,uint64_t epoch,uint64_t *session)
{
    comp_rec_identity_record_t next;
    if(!s||!s->ready||!session||!id||count>COMP_REC_IDENTITY_MAPS||(count&&!ids)||live(ids,count,id))return false;
    for(size_t i=0u;i<count;i++){if(!ids[i])return false;for(size_t j=0u;j<i;j++)if(ids[i]==ids[j])return false;}
    if(!s->loaded&&!epoch)return false;
    next=s->record;
    if(!s->loaded){next.format_epoch=epoch;next.next_session_id=1u;}
    if(next.next_session_id==UINT64_MAX||next.sequence==UINT64_MAX)return false;
    next.count=0u;memset(next.maps,0,sizeof(next.maps));
    for(size_t i=0u;i<s->record.count;i++)if(live(ids,count,s->record.maps[i].recording_id))next.maps[next.count++]=s->record.maps[i];
    if(next.count==COMP_REC_IDENTITY_MAPS)return false;
    next.maps[next.count++]=(comp_rec_identity_map_t){id,next.next_session_id};
    next.next_session_id++;next.sequence++;
    return persist(s,&next,session);
}
bool comp_rec_identity_allocate_session(comp_rec_identity_t *s,uint64_t epoch,uint64_t *session)
{
    comp_rec_identity_record_t next;
    if(!s||!s->ready||!session||(!s->loaded&&!epoch))return false;
    next=s->record;
    if(!s->loaded){next.format_epoch=epoch;next.next_session_id=1u;}
    if(next.next_session_id==UINT64_MAX||next.sequence==UINT64_MAX)return false;
    next.next_session_id++;next.sequence++;
    return persist(s,&next,session);
}
