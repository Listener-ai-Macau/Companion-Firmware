
#define main prior_suite_main
#include "test_system_storage.c"
#undef main
#include "wba_system_confirmed.h"
static uint8_t current_wire[452],current_digests[96];
static bool both_verify(void *ctx,const uint8_t xy[64],const uint8_t h[32],const uint8_t sig[64]) {
 if(verify(ctx,xy,h,sig))return true;
 if(memcmp(xy,pub,64u))return false;
 const unsigned at[3]={384u,172u,316u};
 for(unsigned i=0;i<3;i++)if(!memcmp(h,current_digests+32u*i,32u))return !memcmp(sig,current_wire+at[i],64u);
 return false;
}
static bool current_running(void*c,const uint8_t*w){(void)c;return running_pair&&!memcmp(w,current_wire,452u);}
static bool provision_current(comp_v11_system_storage_config_t*c) {
 comp_wba_system_confirmed_t receipt;bool blank;
 comp_wba_system_confirmed_ports_t cp={anchor_read,anchor_program,anchor_erase,keep_alive,current_running,NULL,c->trust};
 return comp_wba_system_confirmed_mount(&receipt,&cp,8192u,&blank)&&blank&&comp_wba_system_confirmed_store(&receipt,current_wire);
}
int main(int argc,char **argv) {
 CHECK(argc==6 && file(argv[1],descriptor,452u)&&file(argv[2],pub,64u)&&file(argv[3],digests,96u)&&file(argv[4],current_wire,452u)&&file(argv[5],current_digests,96u));
 memory=malloc(COMP_WBA_NOR_TOTAL_BYTES);CHECK(memory);
 comp_v11_system_storage_config_t c=config();c.trust.verify_digest=both_verify;c.current_pair_verified=current_running;
 unsigned repaired=0,rejected=0;
 for(unsigned mode=0;mode<11u;mode++) {
  comp_v11_system_storage_t s,restart;
  CHECK(reset());running_pair=true;CHECK(provision_current(&c));
  CHECK(comp_v11_system_storage_init(&s,&c));
  fail_program_at=mode==10u?META+256u:META;cut_program=mode==10u?17u:73u;
  CHECK(!comp_wba_system_receive_begin(&s.receiver,descriptor,452u));
  unsigned before=erase_count;uint8_t protected_byte=memory[BASE];
  if(mode==1u)running_pair=false;
  if(mode==2u)memory[META+512u]=0u;
  if(mode==3u)memory[META+500u]=0u;
  if(mode==4u)memory[META+8u]=0u; /* incompatible seq1 */
  if(mode==5u)memory[8192u+COMP_WBA_SYSTEM_CONFIRMED_A+20u]^=1u;
  if(mode==6u)fail_read_at=META+512u;
  bool mounted=comp_v11_system_storage_init(&restart,&c);
  if(mode>=1u && mode<=6u){CHECK(!mounted && erase_count==before);rejected++;continue;}
  CHECK(mounted && restart.first_retry_pending && !restart.receiver.loaded && !restart.journal.usable);
  CHECK(erase_count==before && memory[BASE]==protected_byte);
  if(mode==7u) { /* normal version/signature gate still before any erase */
   CHECK(!comp_wba_system_receive_begin(&restart.receiver,current_wire,452u)&&erase_count==before);rejected++;continue;
  }
  if(mode==8u) {protected_end=BASE+1u;CHECK(!comp_wba_system_receive_begin(&restart.receiver,descriptor,452u)&&erase_count==before);rejected++;continue;}
  if(mode==9u) {memory[META+32u]=0u;CHECK(!comp_wba_system_receive_begin(&restart.receiver,descriptor,452u)&&erase_count==before);rejected++;continue;}
  CHECK(comp_wba_system_receive_begin(&restart.receiver,descriptor,452u));
  CHECK(!restart.first_retry_pending && restart.receiver.loaded && restart.journal.usable && restart.journal.sequence==1u && erase_count==before+1u);
  CHECK(!memcmp(restart.receiver.record+32u,descriptor,452u)&&claimed_bytes==EXTENT&&memory[BASE]==protected_byte);
  comp_v11_system_storage_t again;CHECK(comp_v11_system_storage_init(&again,&c)&&again.receiver.loaded&&!again.first_retry_pending&&again.receiver.received[0]==0u);repaired++;
 }
 free(memory);printf("FIRST_RECEIVE_RETRY_SOFTWARE_ONLY repaired=%u rejected=%u no_payload_or_current_destination_write actual_SPI_NOR_source fake_Hardware_verifier_and_destination_coordinator\n",repaired,rejected);return 0;
}
