#include "diag_flash_journal.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#define BASE 4096u
#define BYTES 4096u
static uint8_t nor[12288];
static unsigned programs,visits;
static int cut=-1;
static bool bad_read,corrupt_write,lost_commit_ack;
static uint32_t last_seq;
static comp_diag_flash_data_t last_data;
static bool read_mem(void *c,uint32_t at,uint8_t *p,size_t n)
{(void)c;assert(at>=BASE&&at+n<=BASE+BYTES);if(bad_read)return false;memcpy(p,nor+at,n);return true;}
static bool program_mem(void *c,uint32_t at,const uint8_t *p,size_t n)
{
    (void)c;assert(at>=BASE&&at+n<=BASE+BYTES);++programs;
    size_t count=cut>=0&&(size_t)cut<n?(size_t)cut:n;
    for(size_t i=0;i<count;++i){assert((nor[at+i]&p[i])==p[i]);nor[at+i]&=p[i];}
    if(corrupt_write&&count)nor[at+count-1u]^=1u;
    if(lost_commit_ack&&n==4u)return false;
    return count==n;
}
static void visit(void *c,uint32_t seq,const comp_diag_flash_data_t *d)
{(void)c;++visits;last_seq=seq;last_data=*d;}
static void fresh(void)
{
    memset(nor,0xA5,sizeof(nor));memset(nor+BASE,255,BYTES);
    programs=visits=0u;cut=-1;bad_read=corrupt_write=lost_commit_ack=false;
}
static void neighbors(void)
{for(unsigned i=0u;i<BASE;++i)assert(nor[i]==0xA5u&&nor[BASE+BYTES+i]==0xA5u);}
int main(void)
{
    comp_diag_flash_ports_t p={read_mem,program_mem,NULL,BASE,BYTES};
    comp_diag_flash_data_t data={{66664u,0x1200u,12345u,2u,0x123u,1u,0x08012345u,0x08011234u,3u,4u,5u,6u}};
    fresh();comp_diag_flash_result_t r=comp_diag_flash_journal(&p,&data,NULL,NULL);
    assert(r.scanned&&r.appended&&r.valid==1u&&r.sequence==1u&&programs==2u);
    r=comp_diag_flash_journal(&p,NULL,visit,NULL);
    assert(r.scanned&&!r.appended&&visits==1u&&last_seq==1u&&!memcmp(&data,&last_data,sizeof(data)));
    for(unsigned i=1u;i<64u;++i){r=comp_diag_flash_journal(&p,&data,NULL,NULL);assert(r.appended&&r.sequence==i+1u);}
    unsigned before=programs;r=comp_diag_flash_journal(&p,&data,NULL,NULL);
    assert(r.scanned&&!r.appended&&r.valid==64u&&programs==before);neighbors();
    /* Every partial body write is preserved. Subsequent boots either skip
     * the occupied own slot or stop at an unidentifiable partial header. */
    for(int n=0;n<60;++n) {
        fresh();cut=n;r=comp_diag_flash_journal(&p,&data,NULL,NULL);assert(!r.appended);
        uint8_t partial[64];memcpy(partial,nor+BASE,64u);cut=-1;
        r=comp_diag_flash_journal(&p,&data,NULL,NULL);
        if(n==0)assert(r.appended);
        else {assert(!memcmp(partial,nor+BASE,64u));if(n>=4)assert(r.appended);else assert(!r.scanned);}
        neighbors();
    }
    fresh();lost_commit_ack=true;r=comp_diag_flash_journal(&p,&data,NULL,NULL);assert(!r.appended);
    lost_commit_ack=false;r=comp_diag_flash_journal(&p,&data,NULL,NULL);assert(r.appended&&r.valid==2u&&r.sequence==2u);
    fresh();nor[BASE+511u]=0u;uint8_t saved[BYTES];memcpy(saved,nor+BASE,BYTES);
    r=comp_diag_flash_journal(&p,&data,NULL,NULL);assert(!r.scanned&&!r.appended&&!programs&&!memcmp(saved,nor+BASE,BYTES));
    fresh();bad_read=true;r=comp_diag_flash_journal(&p,&data,NULL,NULL);assert(!r.scanned&&!programs);
    fresh();corrupt_write=true;r=comp_diag_flash_journal(&p,&data,NULL,NULL);assert(r.scanned&&!r.appended&&programs==1u);
    for(unsigned i=60u;i<64u;++i)assert(nor[BASE+i]==255u);neighbors();
    puts("PASS: bounded external journal, full media, 60 body power cuts, lost commit acknowledgement, foreign data, read/write failure; no erase or neighboring writes");
    return 0;
}
