#include "wba_shared_pool.h"
#include "companion_recording_wire.h"
#include "wba_update_service.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define NOR_BYTES 0x1000000u
#define META COMP_WBA_V2_POOL_META_BASE
#define META_END (META+COMP_WBA_V2_POOL_META_BYTES)
#define CHECK(x) do {if(!(x)){fprintf(stderr,"FAIL_SHARED_POOL line=%d %s\n",__LINE__,#x);exit(2);}}while(0)
static uint8_t *nor,uid[12]={1,2,3,4,5,6,7,8,9,10,11,12};
static int64_t program_cut=-1,erase_cut=-1;
static uint32_t programs,payload_erases;
static bool read_fail,dishonest_erase;
static bool read_nor(void *c,uint32_t at,uint8_t *out,size_t n)
{(void)c;if(read_fail||at>NOR_BYTES||n>NOR_BYTES-at)return false;memcpy(out,nor+at,n);return true;}
static bool program_nor(void *c,uint32_t at,const uint8_t *data,size_t n)
{
    (void)c;programs++;
    if(at>NOR_BYTES||n>NOR_BYTES-at)return false;
    size_t written=n;
    if(at>=META&&at<META_END&&program_cut>=0&&(uint64_t)program_cut<n)written=(size_t)program_cut;
    for(size_t i=0u;i<written;i++){if((nor[at+i]&data[i])!=data[i])return false;nor[at+i]&=data[i];}
    if(at>=META&&at<META_END&&program_cut>=0){program_cut-=(int64_t)written;if(program_cut==0)return false;}
    return written==n;
}
static bool erase_nor(void *c,uint32_t at)
{
    (void)c;if(at%4096u||at>NOR_BYTES-4096u)return false;
    if(at>=COMP_WBA_V2_POOL_BASE)payload_erases++;
    size_t n=4096u;
    if(at>=META&&at<META_END&&erase_cut>=0&&(uint64_t)erase_cut<n)n=(size_t)erase_cut;
    if(dishonest_erase&&at>=COMP_WBA_V2_POOL_BASE)n=2048u;
    memset(nor+at,255,n);
    if(at>=META&&at<META_END&&erase_cut>=0){erase_cut-=(int64_t)n;if(erase_cut==0)return false;}
    return true;
}
static const comp_wba_pool_port_t port={read_nor,program_nor,erase_nor,NULL};
static void reset(void)
{memset(nor,255,NOR_BYTES);program_cut=erase_cut=-1;read_fail=dishonest_erase=false;programs=payload_erases=0u;}
static void mounted(comp_wba_pool_t *p)
{CHECK(comp_wba_pool_mount(p,&port,uid,UINT64_C(0xA1B2C3D405060708)));}
static comp_wba_pool_request_t request(uint32_t object,uint32_t bytes,uint8_t owner)
{comp_wba_pool_request_t r={0};r.object_id=object;r.bytes=bytes;r.owner=owner;return r;}
static comp_wba_pool_lease_t reserve(comp_wba_pool_t *p,uint32_t object,uint32_t bytes)
{comp_wba_pool_request_t r=request(object,bytes,COMP_WBA_POOL_RECORDING);comp_wba_pool_lease_t e;CHECK(comp_wba_pool_reserve(p,&r,1u,&e));return e;}
static void digest(const uint8_t *data,size_t n,uint8_t sha[32])
{comp_wba_update_sha256_t h;comp_wba_update_sha256_init(&h);comp_wba_update_sha256_update(&h,data,n);comp_wba_update_sha256_final(&h,sha);}
static void erase_until_done(comp_wba_pool_t *p,uint64_t id)
{
    bool done=false;
    for(uint32_t i=0u;!done&&i<4096u;i++) {
        uint32_t before=payload_erases;CHECK(comp_wba_pool_poll_erase(p,id,&done));CHECK(payload_erases-before<=1u);
    }
    CHECK(done);
}
static void positive(void)
{
    reset();comp_wba_pool_t p,reboot;mounted(&p);CHECK(p.ready&&!p.loaded&&programs==0u);
    nor[COMP_WBA_V2_POOL_BASE+12u]=0xAAu;
    CHECK(!comp_wba_pool_initialize_blank(&p)&&programs==0u);nor[COMP_WBA_V2_POOL_BASE+12u]=255u;
    CHECK(comp_wba_pool_initialize_blank(&p)&&p.loaded&&p.current_mask==3u);
    CHECK(p.free_bytes==COMP_WBA_V2_POOL_BYTES&&p.largest_extent==COMP_WBA_V2_POOL_BYTES);
    comp_wba_pool_lease_t a=reserve(&p,10u,81920u),b;
    CHECK(a.id==1u&&a.transaction_id==1u&&a.start==COMP_WBA_V2_POOL_BASE);
    uint32_t remaining=p.free_bytes,old_programs=programs;
    uint8_t data[1000],sha[32],wrong[32];for(size_t i=0u;i<sizeof(data);i++)data[i]=(uint8_t)(i*19u);digest(data,sizeof(data),sha);
    CHECK(!comp_wba_pool_write(&p,a.id,0u,data,sizeof(data))&&programs==old_programs);
    CHECK(comp_wba_pool_prepare(&p,a.id));bool done=false;
    CHECK(comp_wba_pool_poll_erase(&p,a.id,&done)&&!done);
    CHECK(comp_wba_pool_find(&p,a.id,&b)&&b.state==COMP_WBA_POOL_PREPARING&&b.erase_cursor==0u);
    mounted(&reboot);CHECK(reboot.free_bytes==remaining);p=reboot;
    erase_until_done(&p,a.id);CHECK(comp_wba_pool_find(&p,a.id,&b)&&b.state==COMP_WBA_POOL_WRITING);
    CHECK(comp_wba_pool_write(&p,a.id,0u,data,sizeof(data)));
    CHECK(!comp_wba_pool_write(&p,a.id,a.bytes-2u,data,3u));
    memcpy(wrong,sha,32u);wrong[0]^=1u;
    CHECK(!comp_wba_pool_seal(&p,a.id,sizeof(data),wrong));
    CHECK(comp_wba_pool_find(&p,a.id,&b)&&b.state==COMP_WBA_POOL_WRITING);
    CHECK(comp_wba_pool_seal(&p,a.id,sizeof(data),sha));CHECK(comp_wba_pool_seal(&p,a.id,sizeof(data),sha));
    CHECK(!comp_wba_pool_write(&p,a.id,0u,data,1u)&&!comp_wba_pool_prepare(&p,a.id));
    CHECK(!comp_wba_pool_retire(&p,a.id,a.transaction_id+1u,sha));
    CHECK(!comp_wba_pool_retire(&p,a.id,a.transaction_id,wrong));
    comp_wba_pool_request_t group[3]={request(77u,8192u,COMP_WBA_POOL_UPDATE),request(77u,4096u,COMP_WBA_POOL_FIRMWARE_BACKUP),request(77u,4096u,COMP_WBA_POOL_RESOURCE_BACKUP)};
    comp_wba_pool_lease_t leases[3];CHECK(comp_wba_pool_reserve(&p,group,3u,leases));
    CHECK(leases[0].transaction_id==leases[1].transaction_id&&leases[1].transaction_id==leases[2].transaction_id);
    CHECK(leases[0].start==a.start+a.bytes&&leases[1].start==leases[0].start+leases[0].bytes);
    CHECK(!comp_wba_pool_reserve(&p,group,3u,leases));
    CHECK(comp_wba_pool_retire(&p,a.id,a.transaction_id,sha));CHECK(p.free_bytes==remaining-16384u);
    CHECK(comp_wba_pool_poll_erase(&p,a.id,&done)&&!done);
    uint32_t protected_free=p.free_bytes;mounted(&reboot);p=reboot;CHECK(p.free_bytes==protected_free);
    CHECK(comp_wba_pool_find(&p,a.id,&b)&&b.state==COMP_WBA_POOL_ERASING);
    erase_until_done(&p,a.id);CHECK(!comp_wba_pool_find(&p,a.id,&b));
    CHECK(p.free_bytes==COMP_WBA_V2_POOL_BYTES-16384u);
    b=reserve(&p,30u,81920u);CHECK(b.start==a.start&&b.id>a.id);
    CHECK(!memcmp(nor+leases[0].start,"\xff\xff\xff\xff",4u));
    /* Expected signed-update digest cannot be changed during sealing. */
    group[0]=request(78u,4096u,COMP_WBA_POOL_UPDATE);group[0].payload_bytes=sizeof(data);memcpy(group[0].sha256,sha,32u);
    CHECK(comp_wba_pool_reserve(&p,group,1u,leases));CHECK(comp_wba_pool_prepare(&p,leases[0].id));erase_until_done(&p,leases[0].id);
    CHECK(comp_wba_pool_write(&p,leases[0].id,0u,data,sizeof(data)));
    CHECK(!comp_wba_pool_seal(&p,leases[0].id,sizeof(data),wrong));CHECK(comp_wba_pool_seal(&p,leases[0].id,sizeof(data),sha));
    /* Partial/dishonest payload erase never advances the durable cursor/free. */
    CHECK(comp_wba_pool_retire(&p,leases[0].id,leases[0].transaction_id,sha));
    memset(nor+leases[0].start,0,4096u);dishonest_erase=true;protected_free=p.free_bytes;
    CHECK(!comp_wba_pool_poll_erase(&p,leases[0].id,&done)&&!done&&p.free_bytes==protected_free);
    CHECK(comp_wba_pool_find(&p,leases[0].id,&b)&&b.erase_cursor==0u);dishonest_erase=false;erase_until_done(&p,leases[0].id);
}
static void program_faults(void)
{
    reset();comp_wba_pool_t p,reboot;mounted(&p);CHECK(comp_wba_pool_initialize_blank(&p));
    comp_wba_pool_lease_t issued=reserve(&p,10u,4096u);
    uint8_t saved[COMP_WBA_V2_POOL_META_BYTES];memcpy(saved,nor+META,sizeof(saved));
    for(uint32_t bank=0u;bank<2u;bank++)for(uint32_t cut=0u;cut<=COMP_WBA_POOL_WIRE_BYTES;cut++) {
        memcpy(nor+META,saved,sizeof(saved));program_cut=-1;mounted(&p);
        comp_wba_pool_request_t r=request(20u,4096u,COMP_WBA_POOL_RECORDING);comp_wba_pool_lease_t out={0};out.id=99u;
        program_cut=(int64_t)(bank*COMP_WBA_POOL_WIRE_BYTES+cut);
        CHECK(!comp_wba_pool_reserve(&p,&r,1u,&out)&&out.id==99u&&!p.ready);
        uint32_t writes=programs;CHECK(!comp_wba_pool_reserve(&p,&r,1u,&out)&&programs==writes);
        program_cut=-1;mounted(&reboot);CHECK(comp_wba_pool_find(&reboot,issued.id,&out)&&out.object_id==10u);
        comp_wba_pool_lease_t next=reserve(&reboot,30u,4096u);CHECK(next.id>issued.id&&reboot.current_mask==3u);
    }
}
static void erase_faults(void)
{
    reset();comp_wba_pool_t p,reboot;mounted(&p);CHECK(comp_wba_pool_initialize_blank(&p));
    comp_wba_pool_lease_t issued=reserve(&p,10u,4096u);
    for(uint32_t i=0u;i<6u;i++)(void)reserve(&p,20u+i,4096u);
    CHECK(p.next_slot[0]==8u&&p.next_slot[1]==8u);
    uint8_t saved[COMP_WBA_V2_POOL_META_BYTES];memcpy(saved,nor+META,sizeof(saved));
    for(uint32_t bank=0u;bank<2u;bank++)for(uint32_t cut=0u;cut<=8192u;cut+=128u) {
        memcpy(nor+META,saved,sizeof(saved));erase_cut=-1;mounted(&p);comp_wba_pool_lease_t out={0};out.id=99u;
        comp_wba_pool_request_t r=request(40u,4096u,COMP_WBA_POOL_RECORDING);erase_cut=(int64_t)(bank*8192u+cut);
        CHECK(!comp_wba_pool_reserve(&p,&r,1u,&out)&&out.id==99u&&!p.ready);erase_cut=-1;
        mounted(&reboot);CHECK(comp_wba_pool_find(&reboot,issued.id,&out)&&out.object_id==10u);
        comp_wba_pool_lease_t next=reserve(&reboot,50u,4096u);CHECK(next.id>issued.id);
    }
    /* A single damaged latest copy cannot cause the sole peer to be erased. */
    memcpy(nor+META,saved,sizeof(saved));mounted(&p);
    uint32_t corrupt=p.active_offset;uint64_t counter=p.next_lease_id;nor[corrupt+1020u]^=1u;mounted(&reboot);
    CHECK(reboot.next_lease_id==counter);comp_wba_pool_lease_t e=reserve(&reboot,80u,4096u);CHECK(e.id==counter);
}
static void negative(void)
{
    /* CRC-valid old roots are not a license for two independent writers to
     * overwrite each other's reservations. A stale object must remount. */
    reset();comp_wba_pool_t live,stale;mounted(&live);CHECK(comp_wba_pool_initialize_blank(&live));mounted(&stale);
    (void)reserve(&live,99u,4096u);uint32_t stale_before=programs;
    comp_wba_pool_request_t stale_request=request(100u,4096u,COMP_WBA_POOL_RECORDING);comp_wba_pool_lease_t stale_lease;
    CHECK(!comp_wba_pool_reserve(&stale,&stale_request,1u,&stale_lease)&&!stale.ready&&programs==stale_before);
    reset();comp_wba_pool_t p;mounted(&p);nor[META]=0x42u;uint32_t crc=comp_rec_crc(nor+META,COMP_WBA_V2_POOL_META_BYTES);
    CHECK(!comp_wba_pool_mount(&p,&port,uid,UINT64_C(0xA1B2C3D405060708)));
    CHECK(crc==comp_rec_crc(nor+META,COMP_WBA_V2_POOL_META_BYTES)&&programs==0u);
    reset();mounted(&p);CHECK(comp_wba_pool_initialize_blank(&p));uint32_t bytes=COMP_WBA_V2_POOL_BYTES;
    (void)reserve(&p,10u,bytes);comp_wba_pool_request_t r=request(20u,4096u,COMP_WBA_POOL_RECORDING);comp_wba_pool_lease_t e;
    uint32_t before=programs;CHECK(!comp_wba_pool_reserve(&p,&r,1u,&e)&&programs==before&&p.free_bytes==0u);
    uint8_t alien[12];memcpy(alien,uid,12u);alien[0]^=1u;
    CHECK(!comp_wba_pool_mount(&p,&port,alien,UINT64_C(0xA1B2C3D405060708)));
    CHECK(!comp_wba_pool_mount(&p,&port,uid,1u));
    reset();memcpy(nor+META,"CPL3",4u);CHECK(!comp_wba_pool_mount(&p,&port,uid,1u)&&programs==0u);
    reset();CHECK(comp_wba_v2_layout_absent(&port));memcpy(nor+COMP_WBA_V2_LAYOUT_A,"CFL2",4u);
    CHECK(!comp_wba_v2_layout_absent(&port));read_fail=true;CHECK(!comp_wba_v2_layout_absent(&port));
    reset();mounted(&p);CHECK(comp_wba_pool_initialize_blank(&p));(void)reserve(&p,10u,4096u);
    nor[p.active_offset+128u+20u]^=1u;before=programs;
    CHECK(!comp_wba_pool_reserve(&p,&r,1u,&e)&&!p.ready&&programs==before);
    /* Metadata count/lease limit is independent from payload capacity. */
    reset();mounted(&p);CHECK(comp_wba_pool_initialize_blank(&p));for(uint32_t i=0u;i<12u;i++)(void)reserve(&p,i+1u,4096u);
    before=programs;CHECK(!comp_wba_pool_reserve(&p,&r,1u,&e)&&programs==before);
    /* Counter exhaustion cannot wrap into a previously issued lease. */
    for(uint32_t counter=8u;counter<=24u;counter+=8u) {
        reset();mounted(&p);CHECK(comp_wba_pool_initialize_blank(&p));
        for(uint8_t bank=0u;bank<2u;bank++) {
            uint8_t *wire=nor+META+(uint32_t)bank*8192u;comp_rec_put64(wire+counter,UINT64_MAX);
            comp_rec_put32(wire+1020u,comp_rec_crc(wire,1020u));
        }
        mounted(&p);before=programs;CHECK(!comp_wba_pool_reserve(&p,&r,1u,&e)&&programs==before);
    }
    /* CRC-valid split brain is an error; never select a convenient twin. */
    reset();mounted(&p);CHECK(comp_wba_pool_initialize_blank(&p));
    uint8_t *wire=nor+META+8192u;comp_rec_put64(wire+16u,2u);comp_rec_put32(wire+1020u,comp_rec_crc(wire,1020u));
    before=programs;CHECK(!comp_wba_pool_mount(&p,&port,uid,UINT64_C(0xA1B2C3D405060708))&&programs==before);
}
int main(void)
{
    nor=malloc(NOR_BYTES);CHECK(nor!=NULL);positive();program_faults();erase_faults();negative();
    printf("PASS_SHARED_POOL_SOFTWARE_ONLY metadata_byte_cuts=2050 metadata_erase_cuts=130 "
           "one_payload_sector_per_poll=1 durable_free_only=1 hash_before_seal=1 "
           "atomic_three_leases=1 foreign_fail_closed=1 pool_object_bytes=%zu\n",sizeof(comp_wba_pool_t));
    free(nor);return 0;
}
