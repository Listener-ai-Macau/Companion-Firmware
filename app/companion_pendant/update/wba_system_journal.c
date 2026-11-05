#include "wba_system_journal.h"
#include <string.h>
#define SLOT_BYTES 512u
#define SECTOR_BYTES 4096u
#define SLOTS 8u
static uint64_t sequence(const uint8_t *p)
{
    uint64_t n=0u;
    for(unsigned i=0u;i<8u;i++)n|=(uint64_t)p[8u+i]<<(8u*i);
    return n;
}
static bool erased(const uint8_t *p,size_t n)
{while(n--)if(*p++!=255u)return false;return true;}
static uint32_t address(const comp_wba_system_journal_t *j,unsigned sector,unsigned slot)
{return j->ports.dynamic_base+8192u+sector*SECTOR_BYTES+slot*SLOT_BYTES;}
static bool own_prefix(const uint8_t *p)
{
    /* A interrupted NOR program may clear only a subset of intended zero bits.
     * Such partial WSR2 prefixes remain torn, not positive blank or legacy data.
     */
    const uint8_t magic[4]={'W','S','R','2'};
    for(unsigned i=0u;i<4u;i++)if((p[i]&magic[i])!=magic[i])return false;
    return true;
}
static bool fail(comp_wba_system_journal_t *j)
{j->usable=false;return false;}
static bool ports_valid(const comp_wba_system_journal_ports_t *p)
{
    return p && p->read && p->program && p->erase_sector &&
        p->dynamic_base>=8192u && !(p->dynamic_base%SECTOR_BYTES) &&
        p->dynamic_base<=COMP_WBA_NOR_TOTAL_BYTES-COMP_WBA_NOR_SYSTEM_BYTES;
}
bool comp_wba_system_journal_first_torn(const comp_wba_system_journal_ports_t *p)
{
    uint8_t slot[SLOT_BYTES];
    const uint8_t header[16]={'W','S','R','2',1u,COMP_WBA_SYSTEM_RECEIVING,0u,0u,1u};
    if(!ports_valid(p))return false;
    for(unsigned n=0u;n<2u*SLOTS;n++) {
        if(!p->read(p->context,p->dynamic_base+8192u+n*SLOT_BYTES,slot,sizeof(slot)))return false;
        if(n) {if(!erased(slot,sizeof(slot)))return false;continue;}
        if(erased(slot,sizeof(slot)) || comp_wba_system_record_valid(slot) ||
           !erased(slot+488u,24u))return false;
        for(unsigned i=0u;i<sizeof(header);i++)if((slot[i]&header[i])!=header[i])return false;
    }
    return true;
}
bool comp_wba_system_journal_restart_first(comp_wba_system_journal_t *j,const uint8_t expected[488])
{
    uint8_t slot[SLOT_BYTES],record[488];bool blank;
    if(!j || !expected || !comp_wba_system_record_valid(expected) ||
       expected[5]!=COMP_WBA_SYSTEM_RECEIVING || sequence(expected)!=1u ||
       memcmp(expected+20u,"\0\0\0\0\0\0\0\0",8u) ||
       !comp_wba_system_journal_first_torn(&j->ports) ||
       !j->ports.read(j->ports.context,address(j,0u,0u),slot,sizeof(slot)))return false;
    for(unsigned i=0u;i<488u;i++)if((slot[i]&expected[i])!=expected[i])return false;
    if(!j->ports.erase_sector(j->ports.context,address(j,0u,0u)))return fail(j);
    return comp_wba_system_journal_mount(j,&j->ports,record,&blank) && blank;
}
bool comp_wba_system_journal_mount(comp_wba_system_journal_t *j,
    const comp_wba_system_journal_ports_t *ports,uint8_t record[488],bool *blank)
{
    uint8_t slot[SLOT_BYTES],touched[2]={0u,0u},positions[16];
    uint64_t seen[16];unsigned seen_count=0u;bool found=false,all_blank=true;
    if(!j || !ports_valid(ports) || !record || !blank)return false;
    comp_wba_system_journal_ports_t copy=*ports;
    memset(j,0,sizeof(*j));j->ports=copy;memset(record,0,488u);*blank=false;
    for(unsigned sector=0u;sector<2u;sector++)for(unsigned n=0u;n<SLOTS;n++){
        if(!copy.read(copy.context,address(j,sector,n),slot,sizeof(slot)))return false;
        if(erased(slot,sizeof(slot)))continue;
        all_blank=false;touched[sector]=(uint8_t)(n+1u);
        if(!own_prefix(slot) || !erased(slot+488u,24u))return false;
        if(!comp_wba_system_record_valid(slot))continue;
        uint64_t current=sequence(slot);
        for(unsigned k=0u;k<seen_count;k++)if(seen[k]==current){
            uint8_t compare[32];
            uint32_t prior=address(j,positions[k]/SLOTS,positions[k]%SLOTS);
            for(unsigned offset=0u;offset<488u;offset+=sizeof(compare)){
                size_t bytes=488u-offset<sizeof(compare)?488u-offset:sizeof(compare);
                if(!copy.read(copy.context,prior+offset,compare,bytes) ||
                    memcmp(compare,slot+offset,bytes))return false;
            }
        }
        seen[seen_count]=current;positions[seen_count++]=(uint8_t)(sector*SLOTS+n);
        if(!found || current>=j->sequence){
            memcpy(record,slot,488u);j->sequence=current;j->sector=(uint8_t)sector;found=true;
        }
    }
    j->scanned=true;
    if(!found && !all_blank)return false;
    *blank=!found;j->next_slot=touched[j->sector];j->mounted=j->usable=true;
    return true;
}
bool comp_wba_system_journal_store(comp_wba_system_journal_t *j,const uint8_t record[488])
{
    uint8_t verify[SLOT_BYTES];
    if(!j || !j->mounted || !j->usable || !record || j->sequence==UINT64_MAX ||
       !comp_wba_system_record_valid(record) || sequence(record)!=j->sequence+1u)return false;
    unsigned sector=j->sector,slot=j->next_slot;
    if(slot>SLOTS)return fail(j);
    if(slot==SLOTS){
        sector^=1u;slot=0u;
        if(!j->ports.erase_sector(j->ports.context,address(j,sector,0u)))return fail(j);
    }
    uint32_t at=address(j,sector,slot);
    if(!j->ports.read(j->ports.context,at,verify,sizeof(verify)) || !erased(verify,sizeof(verify)) ||
       !j->ports.program(j->ports.context,at,record,488u) ||
       !j->ports.read(j->ports.context,at,verify,sizeof(verify)) ||
       memcmp(record,verify,488u) || !erased(verify+488u,24u) ||
       !comp_wba_system_record_valid(verify))return fail(j);
    j->sequence=sequence(record);j->sector=(uint8_t)sector;j->next_slot=(uint8_t)(slot+1u);
    return true;
}
