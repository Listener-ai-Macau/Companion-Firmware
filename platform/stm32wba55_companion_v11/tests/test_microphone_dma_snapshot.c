#include "microphone_hal.h"
#include <stdio.h>
#include <string.h>
#include <assert.h>
#define __DMB() ((void)0)
static uint32_t shared_dma_storage[COMP_V11_MIC_RAW_DMA_BYTES/sizeof(uint32_t)];
static unsigned checks,fail_at;static bool overwrite_after_copy;
static uint8_t *raw_dma_bytes(comp_v11_microphone_hal_t *m){return (uint8_t *)m->raw_dma_words;}
static bool half_is_current(comp_v11_microphone_hal_t *m,const comp_v11_microphone_event_t *e)
{
 ++checks;if(checks==fail_at)return false;
 if(checks==2u&&overwrite_after_copy)memset(raw_dma_bytes(m)+(size_t)e->half*COMP_V11_MIC_RAW_HALF_BYTES,0xA5,COMP_V11_MIC_RAW_HALF_BYTES);
 return true;
}
/* @PRODUCTION_STABLE_HALF_HELPER@ */

typedef struct{int16_t pcm[160];unsigned frames;} output_t;
static bool emit(void *p,const int16_t *v,size_t n,uint32_t rate){output_t *o=p;assert(n==160&&rate==16000);memcpy(o->pcm,v,n*sizeof(*v));++o->frames;return true;}
static void init(comp_v11_microphone_hal_t *m,comp_wba_pdm_capture_t *ref,output_t *out,output_t *expected)
{
 memset(m,0,sizeof(*m));
#if COMPANION_WBA_CE_SHARED_CAPTURE
 m->raw_dma_words=shared_dma_storage;
#else
 (void)shared_dma_storage;
#endif
 memset(out,0,sizeof(*out));memset(expected,0,sizeof(*expected));
 comp_wba_pdm_config_t c={0};c.decimation=96;c.output=COMP_WBA_PDM_OUTPUT_LEFT;c.selected_only=true;c.gain_q15=128u*32768u;c.emit_pcm_frame=emit;c.context=out;
 comp_wba_pdm_capture_init(&m->processing,&c);c.context=expected;comp_wba_pdm_capture_init(ref,&c);assert(comp_wba_pdm_capture_ready(ref));
}
int main(void)
{
 comp_v11_microphone_hal_t m;comp_wba_pdm_capture_t ref;output_t out,expected;uint8_t original[COMP_V11_MIC_RAW_HALF_BYTES];
 uint32_t random=0x4d435533u;unsigned cases=0;
 for(unsigned half=0;half<2;half++)for(unsigned pattern=0;pattern<8;pattern++) {
  init(&m,&ref,&out,&expected);for(size_t i=0;i<sizeof(original);i++){random=random*1664525u+1013904223u;original[i]=(uint8_t)(random>>24);}
  for(unsigned pass=0;pass<3;pass++){
   memcpy(raw_dma_bytes(&m)+(size_t)half*sizeof(original),original,sizeof(original));checks=0;fail_at=0;overwrite_after_copy=true;bool stale=false;
   bool ok=pass==0?comp_wba_pdm_capture_prime(&ref,original,sizeof(original),pass):comp_wba_pdm_capture_ingest(&ref,original,sizeof(original),pass);assert(ok);
   comp_v11_microphone_event_t e={.sequence=pass,.half=(uint8_t)half};assert(process_stable_half(&m,&e,pass==0,&stale)&&!stale&&checks==2);
   assert(out.frames==expected.frames&&!memcmp(out.pcm,expected.pcm,sizeof(out.pcm)));assert(raw_dma_bytes(&m)[(size_t)half*sizeof(original)]==0xA5);++cases;
  }
 }
 for(unsigned fail=1;fail<=2;fail++) {
  init(&m,&ref,&out,&expected);memcpy(raw_dma_bytes(&m),original,sizeof(original));checks=0;fail_at=fail;overwrite_after_copy=false;bool stale=false;comp_v11_microphone_event_t e={.sequence=0,.half=0};
  assert(!process_stable_half(&m,&e,false,&stale)&&stale&&out.frames==0&&m.processing.stats.dma_blocks==0);++cases;
 }
 printf("PASS_STABLE_DMA_SNAPSHOT_SOFTWARE_ONLY cases=%u; real PDM output bit-identical after live raw overwrite following validated full copy; before/after-copy ownership loss rejects with no PCM; no timing/stack/board qualification\n",cases);return 0;
}
