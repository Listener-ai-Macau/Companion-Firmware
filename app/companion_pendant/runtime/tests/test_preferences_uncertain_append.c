#include "companion_preferences.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){printf("FAIL line=%d %s\n",__LINE__,#x);return 1;}}while(0)
enum { FAULT_NONE,FAULT_READ,FAULT_READ_CORRUPT,FAULT_COMMIT_RESULT };
typedef struct {uint8_t bytes[8192];unsigned writes;int budget;unsigned armed,read_fault;} flash_t;
static bool rd(void *c,uint32_t at,uint8_t *out,size_t n)
{
 flash_t *f=c;if(at>8192u||n>8192u-at)return false;
 if(f->read_fault==FAULT_READ){f->read_fault=0;return false;}
 memcpy(out,f->bytes+at,n);
 if(f->read_fault==FAULT_READ_CORRUPT){f->read_fault=0;if(n)out[0]^=1u;}
 return true;
}
static bool wr(void *c,uint32_t at,const uint8_t *in,size_t n)
{
 flash_t *f=c;if(at>8192u||n>8192u-at)return false;++f->writes;
 for(size_t i=0;i<n;++i){if(f->budget==0)return false;if(f->budget>0)--f->budget;
  if((f->bytes[at+i]&in[i])!=in[i])return false;f->bytes[at+i]&=in[i];}
 if(at%64u==60u&&n==4u&&f->armed){const unsigned fault=f->armed;f->armed=0;
  if(fault==FAULT_COMMIT_RESULT)return false;f->read_fault=fault;}
 return true;
}
static bool er(void *c,uint32_t at)
{flash_t *f=c;if(at!=0u&&at!=4096u)return false;memset(f->bytes+at,255,4096);return true;}
static void blank(flash_t *f){memset(f,0,sizeof(*f));memset(f->bytes,255,sizeof(f->bytes));f->budget=-1;}
static uint32_t crc(const uint8_t *p,size_t n)
{uint32_t x=~0u;while(n--){x^=*p++;for(unsigned b=0;b<8u;++b)x=(x>>1)^(0xedb88320u&(0u-(x&1u)));}return ~x;}
static void put32(uint8_t *p,uint32_t v){for(unsigned i=0;i<4u;++i)p[i]=(uint8_t)(v>>(i*8u));}
static int uncertain_then_other_choice(unsigned fault,bool restore_old,bool wrap)
{
 flash_t f;comp_preferences_t s,reboot;blank(&f);const comp_preferences_port_t port={rd,wr,er,&f};
 CHECK(comp_preferences_mount(&s,&port));CHECK(comp_preferences_save(&s,&s.values));
 if(wrap){put32(f.bytes+4,UINT32_MAX-1u);put32(f.bytes+56,crc(f.bytes,56));CHECK(comp_preferences_mount(&s,&port));}
 const uint32_t sequence=s.generation;comp_preferences_values_t v=s.values;v.volume=50u;f.armed=fault;
 CHECK(!comp_preferences_save(&s,&v));CHECK(s.values.volume==25u);
 if(restore_old)CHECK(comp_preferences_save(&s,&s.values));
 else {v=s.values;v.volume=75u;CHECK(comp_preferences_save(&s,&v));}
 CHECK(comp_preferences_mount(&reboot,&port));
 printf("fault=%u restore_old=%u wrap=%u runtime=%u reboot=%u seq_before=%lu seq_after=%lu\n",fault,(unsigned)restore_old,(unsigned)wrap,(unsigned)s.values.volume,(unsigned)reboot.values.volume,(unsigned long)sequence,(unsigned long)s.generation);
 CHECK(reboot.values.volume==(restore_old?25u:75u));
 CHECK(s.generation==sequence+2u&&reboot.generation==s.generation);
 const unsigned before=f.writes;CHECK(comp_preferences_save(&s,&s.values));CHECK(f.writes==before);
 return 0;
}
static int partial_then_retry_and_rollover(void)
{
 flash_t f;comp_preferences_t s,reboot;blank(&f);const comp_preferences_port_t port={rd,wr,er,&f};
 CHECK(comp_preferences_mount(&s,&port));CHECK(comp_preferences_save(&s,&s.values));
 comp_preferences_values_t v=s.values;v.volume=50u;f.budget=23;
 CHECK(!comp_preferences_save(&s,&v));f.budget=-1;
 CHECK(comp_preferences_mount(&reboot,&port));CHECK(reboot.values.volume==25u);
 v.volume=75u;CHECK(comp_preferences_save(&s,&v));CHECK(comp_preferences_mount(&reboot,&port));CHECK(reboot.values.volume==75u);
 while(s.next_slot<64u){v=s.values;v.volume=v.volume==25u?50u:25u;CHECK(comp_preferences_save(&s,&v));}
 const uint32_t sequence=s.generation;v=s.values;v.volume=75u;f.armed=FAULT_READ;
 CHECK(!comp_preferences_save(&s,&v));v=s.values;v.volume=100u;CHECK(comp_preferences_save(&s,&v));
 CHECK(comp_preferences_mount(&reboot,&port));CHECK(reboot.values.volume==100u&&reboot.generation==sequence+2u);
 puts("PASS_PARTIAL_APPEND_RETRY_AND_UNCERTAIN_ROLLOVER");return 0;
}
static int uncertain_last_slot_crosses_bank(unsigned original_bank)
{
 flash_t f;comp_preferences_t s,reboot;blank(&f);const comp_preferences_port_t port={rd,wr,er,&f};
 CHECK(comp_preferences_mount(&s,&port));CHECK(comp_preferences_save(&s,&s.values));
 const unsigned count=original_bank?127u:63u;
 for(unsigned i=1u;i<count;++i){comp_preferences_values_t next=s.values;next.volume=next.volume==25u?50u:25u;CHECK(comp_preferences_save(&s,&next));}
 CHECK(s.bank==original_bank&&s.next_slot==63u);
 const uint32_t sequence=s.generation;comp_preferences_values_t v=s.values;v.volume=75u;f.armed=FAULT_READ;
 CHECK(!comp_preferences_save(&s,&v));CHECK(s.next_slot==64u);
 v=s.values;v.volume=100u;CHECK(comp_preferences_save(&s,&v));
 CHECK(s.bank==(original_bank^1u));CHECK(comp_preferences_mount(&reboot,&port));
 CHECK(reboot.values.volume==100u&&reboot.generation==sequence+2u);
 printf("PASS_UNCERTAIN_LAST_SLOT_BANK_%u_TO_%u\n",original_bank,original_bank^1u);return 0;
}
int main(void)
{
 for(unsigned fault=FAULT_READ;fault<=FAULT_COMMIT_RESULT;++fault)
  for(unsigned restore=0;restore<2u;++restore)
   for(unsigned wrap=0;wrap<2u;++wrap)if(uncertain_then_other_choice(fault,restore!=0u,wrap!=0u))return 1;
 if(partial_then_retry_and_rollover()||uncertain_last_slot_crosses_bank(0u)||uncertain_last_slot_crosses_bank(1u))return 1;
 printf("PASS_PREFERENCES_UNCERTAIN_APPEND_RECOVERY_SOFTWARE_ONLY store_bytes=%u\n",(unsigned)sizeof(comp_preferences_t));return 0;
}
