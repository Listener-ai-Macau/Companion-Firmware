#include "diag_flash_journal.h"
#include "companion_crc32.h"
#include <string.h>
#define RECORD_BYTES 64u
#define MAGIC UINT32_C(0x314C4443) /* CDL1 */
#define COMMIT UINT32_C(0xC04D17ED)
static uint32_t get32(const uint8_t *p)
{return(uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static void put32(uint8_t *p,uint32_t v)
{p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);p[2]=(uint8_t)(v>>16);p[3]=(uint8_t)(v>>24);}
static bool blank(const uint8_t *p)
{for(unsigned i=0u;i<RECORD_BYTES;++i)if(p[i]!=255u)return false;return true;}
static bool decode(const uint8_t *p,comp_diag_flash_data_t *d)
{
    if(get32(p)!=MAGIC||get32(p+60u)!=COMMIT||get32(p+56u)!=companion_crc32(0u,p,56u))return false;
    for(unsigned i=0u;i<COMP_DJ_WORDS;++i)d->word[i]=get32(p+8u+4u*i);
    return true;
}
comp_diag_flash_result_t comp_diag_flash_journal(const comp_diag_flash_ports_t *p,
    const comp_diag_flash_data_t *data,comp_diag_flash_visit_fn visit,void *context)
{
    comp_diag_flash_result_t r={0};uint8_t raw[RECORD_BYTES];
    uint32_t last=UINT32_MAX,seq=0u;
    if(!p||!p->read||!p->bytes||p->bytes%RECORD_BYTES||p->base>UINT32_MAX-p->bytes)return r;
    for(uint32_t off=0u;off<p->bytes;off+=RECORD_BYTES) {
        comp_diag_flash_data_t d;
        if(!p->read(p->context,p->base+off,raw,sizeof(raw)))return r;
        if(blank(raw))continue;
        last=off;
        if(decode(raw,&d)) {
            uint32_t s=get32(raw+4u);if(s>seq)seq=s;++r.valid;
            if(visit)visit(context,s,&d);
        } else if(get32(raw)!=MAGIC) {
            /* An interrupted own record is occupied. Other data is never
             * claimed, programmed or erased, including a partial header. */
            return r;
        }
    }
    r.scanned=true;r.sequence=seq;
    uint32_t next=last==UINT32_MAX?0u:last+RECORD_BYTES;
    if(!data||!p->program||next>=p->bytes||seq==UINT32_MAX)return r;
    memset(raw,255,sizeof(raw));put32(raw,MAGIC);put32(raw+4u,seq+1u);
    for(unsigned i=0u;i<COMP_DJ_WORDS;++i)put32(raw+8u+4u*i,data->word[i]);
    put32(raw+56u,companion_crc32(0u,raw,56u));
    const uint32_t at=p->base+next;
    if(!p->program(p->context,at,raw,60u))return r;
    uint8_t check[RECORD_BYTES];
    if(!p->read(p->context,at,check,60u)||memcmp(raw,check,60u))return r;
    put32(raw+60u,COMMIT);
    if(!p->program(p->context,at+60u,raw+60u,4u)||
       !p->read(p->context,at,check,sizeof(check))||memcmp(raw,check,sizeof(check)))return r;
    r.appended=true;++r.valid;r.sequence=seq+1u;return r;
}
