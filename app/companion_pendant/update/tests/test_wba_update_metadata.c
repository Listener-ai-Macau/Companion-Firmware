#include "wba_update_metadata.h"
#include "wba_update_manifest_wire.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    uint8_t a[4096],b[4096];
    bool fail_read_a,fail_read_b,fail_erase,fail_write,corrupt_readback;
    size_t partial_erase_bytes,partial_write_bytes;
    unsigned writes;
} fixture_t;

static void require(bool ok,const char *message)
{if(!ok){fprintf(stderr,"FAIL: %s\n",message);exit(1);}}

uint32_t comp_wba_update_wire_crc32(const uint8_t *data,size_t length)
{
    uint32_t crc=UINT32_C(0xFFFFFFFF);
    while(length--){crc^=*data++;for(uint8_t bit=0u;bit<8u;++bit)
        crc=(crc>>1u)^(UINT32_C(0xEDB88320)&(uint32_t)-(int32_t)(crc&1u));}
    return crc^UINT32_C(0xFFFFFFFF);
}
bool comp_wba_update_checkpoint_valid(const comp_wba_update_checkpoint_t *checkpoint)
{return checkpoint!=NULL;}
bool comp_wba_boot_record_valid(const comp_wba_boot_record_t *record)
{return record!=NULL;}

static uint8_t *slot(fixture_t *f,uint32_t offset)
{return offset==0x1000u?f->a:offset==0x2000u?f->b:NULL;}
static bool read_slot(void *context,uint32_t offset,uint8_t *data,size_t length)
{
    fixture_t *f=context;uint8_t *p=slot(f,offset);
    if(!p||length>4096u||(offset==0x1000u&&f->fail_read_a)||
       (offset==0x2000u&&f->fail_read_b))return false;
    memcpy(data,p,length);
    if(f->corrupt_readback&&f->writes)data[0]^=1u;
    return true;
}
static bool erase_slot(void *context,uint32_t offset)
{fixture_t*f=context;uint8_t*p=slot(f,offset);if(!p||f->fail_erase)return false;
 size_t n=f->partial_erase_bytes&&f->partial_erase_bytes<4096u?f->partial_erase_bytes:4096u;
 memset(p,0xff,n);if(n!=4096u){f->partial_erase_bytes=0u;return false;}return true;}
static bool write_slot(void *context,uint32_t offset,const uint8_t *data,size_t length)
{fixture_t*f=context;uint8_t*p=slot(f,offset);if(!p||f->fail_write||length>4096u)return false;
 size_t n=f->partial_write_bytes&&f->partial_write_bytes<length?f->partial_write_bytes:length;
 for(size_t i=0;i<n;++i)p[i]&=data[i];f->writes++;
 if(n!=length){f->partial_write_bytes=0u;return false;}return true;}
static comp_wba_update_metadata_ports_t ports(fixture_t *f)
{comp_wba_update_metadata_ports_t p={read_slot,erase_slot,write_slot,f,0x1000u,0x2000u};return p;}
static void blank(fixture_t *f){memset(f,0,sizeof(*f));memset(f->a,0xff,sizeof(f->a));memset(f->b,0xff,sizeof(f->b));}

int main(void)
{
    fixture_t f;comp_wba_update_metadata_store_t store,reloaded;
    comp_wba_update_metadata_record_t first={0},second={0};
    blank(&f);comp_wba_update_metadata_ports_t p=ports(&f);
    require(comp_wba_update_metadata_mount(&store,&p)&&!store.loaded,"both erased slots mount as new");
    first.checkpoint_valid=0u;first.boot_record_valid=0u;
    require(comp_wba_update_metadata_commit(&store,&p,&first),"first durable commit");
    require(store.loaded&&store.record.sequence==1u,"first sequence committed");
    second=store.record;second.checkpoint_valid=0u;
    require(comp_wba_update_metadata_commit(&store,&p,&second)&&store.record.sequence==2u,"second bank commit");
    require(comp_wba_update_metadata_mount(&reloaded,&p)&&reloaded.loaded&&reloaded.record.sequence==2u,"newest valid bank selected");

    fixture_t baseline=f;
    for(size_t cut=1u;cut<sizeof(comp_wba_update_metadata_record_t);++cut){
        fixture_t torn=baseline;comp_wba_update_metadata_ports_t tp=ports(&torn);
        require(comp_wba_update_metadata_mount(&store,&tp)&&store.record.sequence==2u,
                "partial-write baseline mount");
        torn.partial_write_bytes=cut;
        require(!comp_wba_update_metadata_commit(&store,&tp,&second),
                "partial metadata write rejected");
        torn.partial_write_bytes=0u;
        require(comp_wba_update_metadata_mount(&reloaded,&tp)&&reloaded.loaded&&
                reloaded.record.sequence==2u,
                "previous metadata bank survives every torn record byte");
    }
    {
        static const size_t cuts[]={1u,2u,63u,511u,2048u,4095u};
        for(size_t i=0u;i<sizeof(cuts)/sizeof(cuts[0]);++i){
            fixture_t torn=baseline;comp_wba_update_metadata_ports_t tp=ports(&torn);
            require(comp_wba_update_metadata_mount(&store,&tp)&&store.record.sequence==2u,
                    "partial-erase baseline mount");
            torn.partial_erase_bytes=cuts[i];
            require(!comp_wba_update_metadata_commit(&store,&tp,&second),
                    "partial metadata erase rejected");
            torn.partial_erase_bytes=0u;
            require(comp_wba_update_metadata_mount(&reloaded,&tp)&&reloaded.loaded&&
                    reloaded.record.sequence==2u,
                    "previous metadata bank survives partial sector erase");
        }
    }
    {
        fixture_t lost_ack=baseline;comp_wba_update_metadata_ports_t tp=ports(&lost_ack);
        require(comp_wba_update_metadata_mount(&store,&tp)&&store.record.sequence==2u,
                "readback-loss baseline mount");
        lost_ack.corrupt_readback=true;
        require(!comp_wba_update_metadata_commit(&store,&tp,&second),
                "corrupt commit readback reported");
        lost_ack.corrupt_readback=false;
        require(comp_wba_update_metadata_mount(&reloaded,&tp)&&reloaded.loaded&&
                reloaded.record.sequence==3u,
                "fully persisted metadata remains recoverable after lost acknowledgement");
    }

    comp_wba_update_metadata_store_t before=store;f.fail_write=true;
    require(!comp_wba_update_metadata_commit(&store,&p,&second)&&
            memcmp(&store,&before,sizeof(store))==0,"write failure leaves RAM record and slot unchanged");
    f.fail_write=false;f.corrupt_readback=true;
    require(!comp_wba_update_metadata_commit(&store,&p,&second)&&
            memcmp(&store,&before,sizeof(store))==0,"readback corruption leaves RAM state unchanged");
    f.corrupt_readback=false;

    blank(&f);p=ports(&f);f.a[0]=0u;
    require(!comp_wba_update_metadata_mount(&store,&p),"nonblank invalid page is not treated as empty");
    blank(&f);p=ports(&f);f.fail_read_b=true;
    require(!comp_wba_update_metadata_mount(&store,&p),"either bank read failure fails closed");

    printf("PASS_WBA_UPDATE_METADATA blank_only_empty=1 invalid_fail_closed=1 read_failure_fail_closed=1 newest_sequence=1 commit_rollback=1 torn_write_all_record_bytes=1 partial_erase_boundaries=1 lost_commit_ack_recovered=1\n");
    return 0;
}
