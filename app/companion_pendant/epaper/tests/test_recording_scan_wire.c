/* Compare this exact wire trace with the pre-optimization driver, in raw and
 * compressed OLD modes. It checks complete ordinary/wave coverage and cache
 * invalidation across transactions; host clocks do not qualify board timing. */
#include "ssd1681_wba.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define REQUIRE(x) do {if(!(x)){fprintf(stderr,"line=%d %s\n",__LINE__,#x);return 1;}}while(0)
typedef struct {uint32_t now,busy_until;FILE *wire;} fixture_t;
static bool transfer(void *v,bool data,const uint8_t *p,uint16_t n)
{
 fixture_t *f=v;uint8_t h[7]={(uint8_t)data,(uint8_t)n,(uint8_t)(n>>8),
 (uint8_t)f->now,(uint8_t)(f->now>>8),(uint8_t)(f->now>>16),(uint8_t)(f->now>>24)};
 if(fwrite(h,1,sizeof(h),f->wire)!=sizeof(h)||fwrite(p,1,n,f->wire)!=n)return false;
 if(!data&&n==1u&&(p[0]==0x12u||p[0]==0x20u))f->busy_until=f->now+4u;
 return true;
}
static bool reset(void *v,bool on){(void)v;(void)on;return true;}
static bool busy(void *v){fixture_t*f=v;return f->now<f->busy_until;}
static uint32_t now(void*v){return ((fixture_t*)v)->now;}
static bool drive(comp_ssd1681_wba_t*d,fixture_t*f)
{
 for(unsigned i=0;i<20000u;i++,f->now++) {
  if(comp_ssd1681_wba_poll(d)!=COMP_SSD1681_WBA_ACTIVE)return d->status==COMP_SSD1681_WBA_COMPLETE;
 }
 return false;
}
int main(int argc,char **argv)
{
 REQUIRE(argc==3);bool packed=atoi(argv[1])!=0;fixture_t f={0};f.wire=fopen(argv[2],"wb");REQUIRE(f.wire);
 comp_ssd1681_wba_config_t c={0};c.context=&f;c.transfer=transfer;c.set_reset=reset;c.is_busy=busy;c.now_ms=now;
 c.payload_chunk_bytes=64u;c.busy_timeout_ms=5000u;c.partial_limit=255u;
 static uint8_t old[5000],next[5000];static comp_wba_frame_store_t store;comp_ssd1681_wba_t d;
 memset(old,255,sizeof(old));for(unsigned y=30;y<120;y++)old[y*25+8]=0;
 REQUIRE(comp_ssd1681_wba_init(&d,&c));REQUIRE(comp_wba_frame_store_write(&store,old));
 if(packed)REQUIRE(comp_ssd1681_wba_bind_old_store(&d,&store));
 const uint8_t *previous=packed?store.bytes:old;
 REQUIRE(comp_ssd1681_wba_start_full(&d,previous,old,5000));REQUIRE(drive(&d,&f));
 const comp_ssd1681_wba_window_t wave={1,5,100,180};
 for(unsigned tx=0;tx<3;tx++) {
  memcpy(next,old,5000);
  if(tx==0) {next[120*25+2]^=0x3c;next[2*25+20]^=0x55;next[110*25]^=0xf0;next[110*25+24]^=0x0f;next[195*25+10]^=0x7f;}
  else if(tx==1)next[130*25+22]^=0x41;
  else next[150*25+3]^=0x38;
  REQUIRE(comp_ssd1681_wba_start_recording_partial(&d,previous,next,5000,&wave));REQUIRE(drive(&d,&f));
  memcpy(old,next,5000);REQUIRE(comp_wba_frame_store_write(&store,old));
  REQUIRE(!comp_ssd1681_wba_start_recording_partial(&d,previous,old,5000,&wave));
 }
 REQUIRE(fclose(f.wire)==0);puts("RECORDING_SCAN_WIRE_CAPTURED_SOFTWARE_ONLY");return 0;
}
