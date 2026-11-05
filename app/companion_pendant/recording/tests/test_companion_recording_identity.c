#include "companion_recording_identity.h"
#include "companion_recording_wire.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    uint8_t bytes[COMP_REC_IDENTITY_BYTES];
    size_t cut;
    int fail_program,fail_erase,fail_read,programs,erases,reads;
    bool lose_ack,corrupt_readback;
} flash_t;
static flash_t flash,baseline;
static const uint8_t uid[12]={1,2,3,4,5,6,7,8,9,10,11,12};
static bool read_flash(void *c,uint32_t offset,uint8_t *out,size_t n)
{
    flash_t *f=c;if(offset>sizeof(f->bytes)||n>sizeof(f->bytes)-offset)return false;
    if(++f->reads==f->fail_read)return false;
    memcpy(out,f->bytes+offset,n);
    if(f->corrupt_readback&&f->programs)out[0]^=1u;
    return true;
}
static bool program_flash(void *c,uint32_t offset,const uint8_t *p,size_t n)
{
    flash_t *f=c;if(offset>sizeof(f->bytes)||n>sizeof(f->bytes)-offset)return false;
    size_t use=n;bool failed=++f->programs==f->fail_program;
    if(failed&&f->cut<use)use=f->cut;
    for(size_t i=0u;i<use;i++){if((f->bytes[offset+i]&p[i])!=p[i])return false;f->bytes[offset+i]&=p[i];}
    return !failed||(!f->lose_ack&&use==n);
}
static bool erase_flash(void *c,uint32_t offset)
{
    flash_t *f=c;if(offset%4096u||offset>sizeof(f->bytes)-4096u)return false;
    bool failed=++f->erases==f->fail_erase;size_t use=failed?f->cut:4096u;
    if(use>4096u)use=4096u;memset(f->bytes+offset,255,use);return !failed;
}
static comp_rec_identity_port_t ports(void)
{return (comp_rec_identity_port_t){read_flash,program_flash,erase_flash,&flash};}
static void fresh(void)
{memset(&flash,0,sizeof(flash));memset(flash.bytes,255,sizeof(flash.bytes));flash.cut=SIZE_MAX;}
static void clear_faults(void)
{flash.fail_program=flash.fail_erase=flash.fail_read=flash.programs=flash.erases=flash.reads=0;flash.lose_ack=flash.corrupt_readback=false;flash.cut=SIZE_MAX;}
static void mount(comp_rec_identity_t *s)
{comp_rec_identity_port_t p=ports();assert(comp_rec_identity_mount(s,&p,uid));}
static uint64_t reserve(comp_rec_identity_t *s,uint32_t id,const uint32_t *live,size_t count)
{uint64_t sid=0u;assert(comp_rec_identity_reserve(s,id,live,count,UINT64_C(0x1122334455667788),&sid));return sid;}
static void fix_crc(uint8_t *p)
{comp_rec_put32(p+156u,comp_rec_crc(p,156u));}
static void logical_sessions(void)
{
    comp_rec_identity_t s,reboot;uint64_t sid=999u;uint32_t ids[7];
    fresh();mount(&s);
    assert(!comp_rec_identity_allocate_session(&s,0u,&sid)&&sid==999u&&flash.programs==0);
    /* All legacy live mappings remain intact while a single logical meeting
     * identity can cover any number of durable segment descriptors. */
    for(uint32_t i=0u;i<7u;i++){ids[i]=i+1u;assert(reserve(&s,ids[i],ids,i)==(uint64_t)i+1u);}
    const uint64_t epoch=s.record.format_epoch;
    for(uint64_t expected=8u;expected<=35u;expected++) {
        assert(comp_rec_identity_allocate_session(&s,0u,&sid)&&sid==expected);
        for(size_t i=0u;i<7u;i++){uint64_t legacy=0u;assert(comp_rec_identity_find(&s,ids[i],&legacy)&&legacy==i+1u);}
        mount(&reboot);assert(reboot.record.next_session_id==expected+1u&&reboot.record.format_epoch==epoch);
        s=reboot;
    }
    baseline=flash;
    /* Both copies of a new logical session use the original crash-safe
     * allocator. Never return uncertain IDs or reuse an already returned ID. */
    for(int bank=1;bank<=2;bank++)for(size_t cut=0u;cut<=160u;cut++) {
        flash=baseline;clear_faults();mount(&s);clear_faults();flash.fail_program=bank;
        flash.cut=cut;flash.lose_ack=true;sid=999u;
        assert(!comp_rec_identity_allocate_session(&s,0u,&sid)&&sid==999u&&!s.ready);
        assert(!comp_rec_identity_allocate_session(&s,0u,&sid));
        clear_faults();mount(&reboot);assert(reboot.record.next_session_id>=36u);
        assert(comp_rec_identity_allocate_session(&reboot,0u,&sid)&&sid>=36u);
        assert(reboot.record.format_epoch==epoch&&reboot.record.count==7u);
    }
    /* The only current copy is never erased first at rollover. */
    fresh();mount(&s);
    for(uint64_t i=1u;i<=16u;i++)assert(comp_rec_identity_allocate_session(&s,1u,&sid)&&sid==i);
    flash.bytes[4096u+15u*256u+156u]^=1u;baseline=flash;
    for(size_t cut=0u;cut<=4096u;cut+=256u) {
        flash=baseline;clear_faults();mount(&s);assert(s.current_copy[0]&&!s.current_copy[1]);
        clear_faults();flash.fail_erase=1;flash.cut=cut;sid=999u;
        assert(!comp_rec_identity_allocate_session(&s,0u,&sid)&&sid==999u&&!s.ready);
        clear_faults();mount(&reboot);assert(reboot.record.next_session_id==17u);
        assert(comp_rec_identity_allocate_session(&reboot,0u,&sid)&&sid==17u);
    }
    /* Shared persistence path still supports a subsequent V1 recording. */
    assert(reserve(&reboot,99u,NULL,0u)==18u);mount(&s);
    assert(comp_rec_identity_find(&s,99u,&sid)&&sid==18u);
    assert(comp_rec_identity_allocate_session(&s,0u,&sid)&&sid==19u);
    flash.fail_read=flash.reads+1;sid=999u;
    assert(!comp_rec_identity_allocate_session(&s,0u,&sid)&&sid==999u&&!s.ready);
    puts("PASS logical-session CSI1 allocation: seven legacy maps preserved, dual-copy readback,322 program cuts/17 rollover cuts, no returned ID reuse; software only");
}
int main(int argc,char **argv)
{
    if(argc==2&&!strcmp(argv[1],"logical")){logical_sessions();return 0;}
    comp_rec_identity_t s,reboot;comp_rec_identity_port_t p;uint64_t sid=999u;
    fresh();mount(&s);assert(!s.loaded&&flash.programs==0&&flash.erases==0);
    assert(!comp_rec_identity_reserve(&s,1u,NULL,0u,0u,&sid)&&sid==999u&&flash.programs==0);
    assert(reserve(&s,1u,NULL,0u)==1u&&s.record.next_session_id==2u&&flash.programs==2&&flash.erases==0);
    mount(&reboot);assert(comp_rec_identity_find(&reboot,1u,&sid)&&sid==1u&&reboot.current_copy[0]&&reboot.current_copy[1]);
    uint32_t live[]={1u};assert(!comp_rec_identity_reserve(&reboot,1u,live,1u,0u,&sid));
    assert(reserve(&reboot,2u,live,1u)==2u);mount(&s);
    assert(comp_rec_identity_find(&s,1u,&sid)&&sid==1u&&comp_rec_identity_find(&s,2u,&sid)&&sid==2u);
    assert(reserve(&s,3u,NULL,0u)==3u);assert(!comp_rec_identity_find(&s,1u,&sid));
    /* Namespace persists over real object reconstruction; no boot entropy reset. */
    mount(&s);uint64_t epoch=s.record.format_epoch;assert(comp_rec_identity_reserve(&s,4u,NULL,0u,999u,&sid)&&sid==4u&&s.record.format_epoch==epoch);
    p=ports();uint8_t other[12];memcpy(other,uid,12u);other[0]^=1u;
    assert(!comp_rec_identity_mount(&reboot,&p,other));
    /* Full mapping protects all seven live physical recordings. */
    fresh();mount(&s);uint32_t ids[7];
    for(uint32_t i=0u;i<7u;i++){ids[i]=i+1u;assert(reserve(&s,ids[i],ids,i)==(uint64_t)i+1u);}
    int before=flash.programs;assert(!comp_rec_identity_reserve(&s,8u,ids,7u,0u,&sid)&&flash.programs==before);
    assert(reserve(&s,8u,ids+1u,6u)==8u&&!comp_rec_identity_find(&s,1u,&sid));
    /* Every byte cut in either copy, including a fully written lost ACK. */
    fresh();mount(&s);assert(reserve(&s,1u,NULL,0u)==1u);baseline=flash;
    for(int bank=1;bank<=2;bank++)for(size_t cut=0u;cut<=160u;cut++) {
        flash=baseline;clear_faults();mount(&s);clear_faults();flash.fail_program=bank;flash.cut=cut;flash.lose_ack=true;
        sid=999u;assert(!comp_rec_identity_reserve(&s,2u,NULL,0u,0u,&sid)&&sid==999u&&!s.ready);
        assert(!comp_rec_identity_reserve(&s,3u,NULL,0u,0u,&sid));
        clear_faults();mount(&reboot);assert(reboot.record.next_session_id>=2u);
        assert(reserve(&reboot,3u,NULL,0u)>=2u); /* no previously returned ID reused */
    }
    /* Post-commit damage of one latest copy must still preserve its issued ID. */
    flash=baseline;clear_faults();mount(&s);assert(reserve(&s,2u,NULL,0u)==2u);
    flash.bytes[256u+156u]^=1u;mount(&reboot);assert(reboot.record.next_session_id==3u);
    assert(reserve(&reboot,3u,NULL,0u)==3u);
    /* At rollover, preserve the only latest valid copy until peer readback. */
    fresh();mount(&s);for(uint32_t i=1u;i<=16u;i++)assert(reserve(&s,i,NULL,0u)==i);
    flash.bytes[4096u+15u*256u+156u]^=1u;baseline=flash;
    for(size_t cut=0u;cut<=4096u;cut+=256u) {
        flash=baseline;clear_faults();mount(&s);assert(s.current_copy[0]&&!s.current_copy[1]);clear_faults();flash.fail_erase=1;flash.cut=cut;
        sid=999u;assert(!comp_rec_identity_reserve(&s,17u,NULL,0u,0u,&sid)&&sid==999u);
        clear_faults();mount(&reboot);assert(reboot.record.next_session_id==17u);
        assert(reserve(&reboot,18u,NULL,0u)==17u);
    }
    /* One read failure or a dishonest success/readback cannot publish an ID. */
    flash=baseline;clear_faults();mount(&s);clear_faults();flash.fail_read=1;sid=999u;
    assert(!comp_rec_identity_reserve(&s,17u,NULL,0u,0u,&sid)&&sid==999u&&!s.ready);
    fresh();mount(&s);flash.corrupt_readback=true;sid=999u;
    assert(!comp_rec_identity_reserve(&s,1u,NULL,0u,1u,&sid)&&sid==999u&&!s.ready);
    /* Unknown nonblank padding and future schema/owner are read-only blockers. */
    fresh();flash.bytes[250]=0u;p=ports();assert(!comp_rec_identity_mount(&s,&p,uid)&&flash.programs==0&&flash.erases==0);
    fresh();mount(&s);assert(reserve(&s,1u,NULL,0u)==1u);
    memcpy(flash.bytes+256u,"CSI2",4u);clear_faults();p=ports();assert(!comp_rec_identity_mount(&reboot,&p,uid)&&flash.programs==0&&flash.erases==0);
    /* CRC-valid conflicting sequence, namespace change and counter regression. */
    fresh();mount(&s);assert(reserve(&s,1u,NULL,0u)==1u);baseline=flash;
    flash.bytes[4096u+48u]^=4u;fix_crc(flash.bytes+4096u);p=ports();assert(!comp_rec_identity_mount(&reboot,&p,uid));
    flash=baseline;flash.bytes[4096u+16u]^=1u;fix_crc(flash.bytes+4096u);assert(!comp_rec_identity_mount(&reboot,&p,uid));
    flash=baseline;comp_rec_put64(flash.bytes+4096u+8u,2u);fix_crc(flash.bytes+4096u);assert(!comp_rec_identity_mount(&reboot,&p,uid));
    /* Counter exhaustion refuses wrap with zero writes. */
    flash=baseline;for(size_t bank=0u;bank<2u;bank++){uint8_t *record=flash.bytes+4096u*bank;comp_rec_put64(record+24u,UINT64_MAX);fix_crc(record);}
    clear_faults();mount(&s);assert(!comp_rec_identity_reserve(&s,2u,NULL,0u,0u,&sid)&&flash.programs==0);
    printf("PASS_RECORDING_IDENTITY_SOFTWARE_ONLY byte_cuts=322 partial_erase_cuts=17 readback_before_id=1 dual_copy_before_return=1 uid_bound=1 monotonic_no_wrap=1 foreign_fail_closed=1\n");
    return 0;
}
