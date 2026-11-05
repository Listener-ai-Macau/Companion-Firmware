#define _CRT_SECURE_NO_WARNINGS
#define COMP_DMIC_CAPTURE_HOST_TEST 1
#define COMPANION_WBA_BLE_LINKED 1
#include "dual_mic_capture_test_platform.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#undef assert
#define assert(condition) do {if(!(condition)){fprintf(stderr,"FAIL line%u: %s\n",__LINE__,#condition);exit(1);}}while(0)
#include "../dual_mic_capture.c"

static comp_v11_product_app_t app;static comp_v11_hal_t board;
static uint8_t media[1024u*1024u];
static comp_wba_pdm_pair_frame_fn_t observer;static void *observer_context;
static uint32_t tick,last_frame,random_word,programs,reads,erases,starts,stops,irqs,io_this_poll,wait_calls;
static unsigned entropy_available=1000000u;static bool entropy_unhealthy;
static unsigned source_frames;static bool linked,updating,borrowed,space_blocked,stop_fails,program_fails,read_corrupt,wip_fails;
static unsigned fault_mode;
static bool stop_fault,restore_mono_fails;
static uint32_t capture_io_ms;
static FILE *dump_file;
static comp_v11_product_app_t *product=&app;
static struct {struct {bool consume_pending;} *segmented;}product_link;
static bool local_clear_pending;
static bool comp_wba_recording_pipeline_page_available(const void *p){(void)p;return true;}
#include "pair_storage_guard_expression.inc"
#include "pair_foreground_guard_expression.inc"
uint32_t HAL_GetTick(void){return tick;}
bool comp_v11_ble_linked(void){return linked;}
bool comp_v11_update_product_busy(void){return updating;}
bool companion_opus16_rt_workspace_available(void){return !borrowed;}
bool comp_v11_hal_device_uid(uint8_t uid[12]){memset(uid,0x22,12u);return true;}
void comp_v11_ble_console_idle_progress(void){if(!entropy_unhealthy&&entropy_available<1u)entropy_available=1u;}
bool comp_v11_hal_random_u32(comp_v11_hal_t *b,uint32_t *v){(void)b;if(entropy_unhealthy||!entropy_available)return false;--entropy_available;*v=++random_word;return true;}
void comp_power_policy_set_blocker(comp_power_policy_t *p,uint32_t mask,bool set)
{if(set)p->blockers|=mask;else p->blockers&=~mask;}
static bool original(void *c,const int16_t *s,size_t n,uint32_t r)
{return c==&app&&s&&n==160u&&r==16000u;}
bool comp_v11_hal_set_pcm_sink(comp_v11_hal_t *b,comp_wba_pdm_pcm_frame_fn_t fn,void *c)
{if(b->microphone.running||(restore_mono_fails&&fn==original))return false;b->pcm_sink=fn;b->pcm_sink_context=c;return true;}
bool comp_v11_hal_set_pair_sink(comp_v11_hal_t *b,comp_wba_pdm_pair_frame_fn_t fn,void *c)
{if(b->microphone.running||(fn&&observer)||(!fn&&observer_context!=c))return false;observer=fn;observer_context=fn?c:NULL;return true;}
bool comp_v11_hal_microphone_enable(comp_v11_hal_t *b,bool enable)
{
 if(enable){assert(!b->microphone.running&&app.recording.pipeline.workspace_bytes&&observer);starts++;last_frame=tick;source_frames=0;}
 else {stops++;if(stop_fails)return false;if(stop_fault)b->microphone.error_irqs++;}
 b->microphone.running=enable;return true;
}
void comp_v11_microphone_hal_get_stats(comp_v11_microphone_hal_t *m,comp_v11_microphone_stats_t *s)
{memset(s,0,sizeof(*s));s->stale_dma_halves=m->stale_dma_halves;s->event_queue_overflows=m->event_queue_overflows;
 s->processing_rejections=m->processing_rejections;s->error_irqs=m->error_irqs;s->processing=m->processing.stats;}
bool comp_v11_microphone_hal_capture_matches(const comp_v11_microphone_hal_t *m,const comp_v11_microphone_stats_t *s)
{return m->running&&m->stale_dma_halves==s->stale_dma_halves&&m->event_queue_overflows==s->event_queue_overflows&&m->processing_rejections==s->processing_rejections&&m->error_irqs==s->error_irqs;}
comp_v11_microphone_poll_result_t comp_v11_microphone_hal_poll(comp_v11_microphone_hal_t *m)
{
 if(!m->running||tick-last_frame<10u)return COMP_V11_MIC_POLL_IDLE;
 last_frame=tick;
 if(fault_mode&&source_frames==8u){
  if(fault_mode==1u)m->stale_dma_halves++;
  if(fault_mode==2u)m->processing.stats.missing_dma_blocks++;
  if(fault_mode==3u)m->processing.stats.pcm_frames_rejected++;
  if(fault_mode==4u)tick+=11u;
 }
 int16_t mono[160],pairs[320];
 for(unsigned i=0;i<160u;++i){mono[i]=(int16_t)((source_frames*160u+i)%2000u);pairs[2u*i]=mono[i];pairs[2u*i+1u]=(int16_t)(-mono[i]-1);}
 assert(board.pcm_sink(board.pcm_sink_context,mono,160u,16000u));
 m->processing.stats.last_dma_sequence=4u+source_frames;
 m->processing.stats.pcm_frames_emitted++;m->processing.stats.pcm_samples_generated+=160u;
 observer(observer_context,pairs,160u,16000u);source_frames++;irqs++;return COMP_V11_MIC_POLL_PROCESSED;
}
bool comp_wba_recording_product_workspace(void *p,uint32_t bytes,uint32_t *base)
{
 (void)p;if(board.microphone.running||board.nor.erase_active||space_blocked)return false;
 if(bytes){if(app.recording.pipeline.workspace_bytes&&app.recording.pipeline.workspace_bytes!=bytes)return false;*base=(uint32_t)sizeof(media)-bytes;}
 else *base=0u;
 app.recording.pipeline.workspace_bytes=bytes;return true;
}
static void access(uint32_t address,size_t n)
{
 assert(app.recording.pipeline.workspace_bytes&&address>=sizeof(media)-app.recording.pipeline.workspace_bytes&&
  address<=sizeof(media)&&n<=sizeof(media)-address);io_this_poll++;
}
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_erase_step(companion_spi_nor_stm32wba_t *n,uint32_t a,uint32_t bytes)
{
 assert(!board.microphone.running&&bytes==4096u);access(a,bytes);
 if(!n->erase_active){n->erase_active=true;n->erase_address=a;n->erase_bytes=bytes;return COMPANION_SPI_NOR_STM32WBA_PENDING;}
 assert(a==n->erase_address&&bytes==n->erase_bytes);memset(media+a,255u,bytes);n->erase_active=false;erases++;return COMPANION_SPI_NOR_STM32WBA_OK;
}
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_erase_finish_poll(companion_spi_nor_stm32wba_t *n,uint32_t a,uint32_t bytes)
{assert(n->erase_active);return companion_spi_nor_stm32wba_erase_step(n,a,bytes);}
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_wait_ready(companion_spi_nor_stm32wba_t *n,uint32_t timeout)
{(void)n;(void)timeout;assert(!board.microphone.running);wait_calls++;return wip_fails?COMPANION_SPI_NOR_STM32WBA_ERROR:COMPANION_SPI_NOR_STM32WBA_OK;}
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_read(companion_spi_nor_stm32wba_t *n,uint32_t a,uint8_t *p,size_t length)
{(void)n;assert(length<=256u);access(a,length);reads++;memcpy(p,media+a,length);if(read_corrupt&&(board.microphone.running||(active&&active->stream.end_sent)))p[0]^=1u;if(board.microphone.running)tick+=capture_io_ms;return COMPANION_SPI_NOR_STM32WBA_OK;}
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_program(companion_spi_nor_stm32wba_t *n,uint32_t a,const uint8_t *p,size_t length)
{(void)n;access(a,length);assert(length&&length<=256u&&a/256u==(a+(uint32_t)length-1u)/256u);programs++;
 for(size_t i=0;i<length;++i){assert(media[a+i]==255u);media[a+i]&=p[i];}
 if(board.microphone.running)tick+=capture_io_ms;
 return program_fails&&board.microphone.running?COMPANION_SPI_NOR_STM32WBA_ERROR:COMPANION_SPI_NOR_STM32WBA_OK;}
void comp_v11_hal_dual_mic_report(const comp_v11_hal_t *b,uint32_t token)
{assert(!b->microphone.running&&token);}
void comp_v11_hal_log(const char *line)
{
 assert(!board.microphone.running); /* All actual UART operations must be capture-off. */
 if(dump_file){assert(fputs(line,dump_file)>=0);}
}
static void command(const char *s,bool idle)
{while(*s)comp_v11_dual_pair_accept((uint8_t)*s++);comp_v11_dual_pair_accept('\r');comp_v11_dual_pair_accept('\n');comp_v11_dual_pair_command(&app,idle);}
static void step(void)
{if(!pair_service_foreground_pending())tick++;io_this_poll=0u;comp_v11_dual_pair_poll(&app);refresh_storage_blocker();assert(io_this_poll<=1u);
 assert(!active||(board.power.blockers&COMP_POWER_BLOCKER_STORAGE)!=0u);}
static void reset(void)
{
 entropy_available=1000000u;entropy_unhealthy=false;active=NULL;observer=NULL;observer_context=NULL;command_match=0;command_invalid=0;command_candidates=31u;command_pending=0;
 memset(&app,0,sizeof(app));memset(&board,0,sizeof(board));memset(media,0xA5,sizeof(media));
 tick=last_frame=random_word=programs=reads=erases=starts=stops=irqs=capture_io_ms=wait_calls=0u;source_frames=0u;
 linked=updating=borrowed=space_blocked=stop_fails=program_fails=read_corrupt=wip_fails=stop_fault=restore_mono_fails=false;fault_mode=0u;
 app.board=&board;app.storage_layout_ready=app.recording_ready=app.recording.ready=app.recording.media_ready=true;
 board.pcm_sink=original;board.pcm_sink_context=&app;board.nor.config.page_program_timeout_ms=10u;
}
static void to_capture(void)
{command("DPAIR START",true);assert(active);for(unsigned n=0;n<5000u&&active->state!=PAIR_CAPTURE;++n)step();assert(active->state==PAIR_CAPTURE&&board.microphone.running);}
static void finish(void)
{for(unsigned n=0;n<10000u&&active->state!=PAIR_READY&&active->state!=PAIR_FAILED&&active->state!=PAIR_STOP_FAILED;++n)step();}
static void released(void)
{command("DPAIR RELEASE",false);for(unsigned n=0;n<10u&&active;++n)step();assert(!active&&!app.recording.pipeline.workspace_bytes&&!board.microphone.running&&!observer);
 assert(board.pcm_sink==original&&board.pcm_sink_context==&app&&board.power.blockers==0u&&!board.power_sampling_inhibited&&!board.services.playback_inhibited);}
int main(int argc,char **argv)
{
 if(argc!=3)return 2;
 /* Actual704 guard11 regression: only one admitted random word is ready.
  * Refill is available in later foreground turns, never within two reads. */
 reset();entropy_available=1u;command("DPAIR START",true);
 if(!active){puts("REPRO_ACTUAL704_SECOND_ENTROPY_WORD_REJECTS_BEFORE_CAPTURE");return 17;}
 for(unsigned n=0;n<5000u&&active->state!=PAIR_CAPTURE;++n)step();assert(active->state==PAIR_CAPTURE);finish();assert(active->state==PAIR_READY&&random_word==2u);released();
 reset();entropy_available=0u;entropy_unhealthy=true;command("DPAIR START",true);
 assert(active&&!starts&&!erases&&!programs);
 for(unsigned i=0;i<110u&&active->state!=PAIR_FAILED;++i)step();
 assert(active->state==PAIR_FAILED&&active->error==ERR_START&&!starts&&!erases&&!programs);released();
 reset();entropy_available=0u;command("DPAIR START",true);command("DPAIR RELEASE",false);step();
 assert(!active&&!starts&&!erases&&!programs&&!app.recording.pipeline.workspace_bytes);
 reset();to_capture();finish();assert(active->state==PAIR_READY&&!active->error);
 assert(active->offset==PAIR_BYTES&&source_frames==200u&&starts==1u&&stops==1u&&irqs==200u);
 for(size_t i=0;i<active->base;++i)assert(media[i]==0xA5u); /* Existing data never touched. */
 FILE *raw=fopen(argv[1],"wb");assert(raw);assert(fwrite(media+active->base,1u,active->offset,raw)==active->offset);assert(fclose(raw)==0);
 uint32_t writes=programs;dump_file=fopen(argv[2],"wb");assert(dump_file);command("DPAIR DUMP",false);
 for(unsigned n=0;n<10000u&&active->state==PAIR_DUMP;++n)step();assert(active->state==PAIR_READY&&programs==writes);
 assert(fclose(dump_file)==0);dump_file=NULL;released();
 /* Model a bounded2ms NOR operation plus foreground scheduling. This is a
  * scheduling regression from the actual queue-overflow failure, not a
  * measurement or claim that the physical NOR always takes exactly2ms. */
 reset();to_capture();capture_io_ms=2u;finish();assert(active->state==PAIR_READY&&!active->error&&source_frames==200u);released();
 reset();to_capture();capture_io_ms=3u;finish();assert(active->state==PAIR_READY&&!active->error&&source_frames==200u);released();
 /* Busy inputs never reserve, record, erase or queue a later start. */
 for(unsigned n=0;n<6u;++n){reset();if(n==0)linked=true;if(n==1)updating=true;if(n==2)borrowed=true;
  if(n==3)space_blocked=true;if(n==4)app.runtime.capture_active=true;
  command("DPAIR START",n!=5u);assert(!active&&!starts&&!erases&&!programs&&!app.recording.pipeline.workspace_bytes);
  linked=updating=borrowed=space_blocked=false;step();assert(!active);}
 /* Capture errors, uncertain writes and mismatched readback stop, retain the
  * reservation and never publish clean terminal audio or retry a program. */
 for(unsigned n=1;n<=6u;++n){reset();to_capture();if(n<=4u)fault_mode=n;if(n==5u)program_fails=true;if(n==6u)read_corrupt=true;
  finish();assert(active->state==PAIR_FAILED&&!board.microphone.running&&app.recording.pipeline.workspace_bytes);
  assert(n==6u||!active->stream.end_sent);writes=programs;for(unsigned j=0;j<10u;++j)step();assert(programs==writes);released();}
 reset();to_capture();stop_fails=true;fault_mode=1u;finish();assert(active->state==PAIR_STOP_FAILED&&board.microphone.running);
 command("DPAIR RELEASE",false);for(unsigned n=0;n<5u;++n)step();assert(active&&app.recording.pipeline.workspace_bytes&&board.microphone.running);
 /* A transient failed stop must eventually restore normal ownership, with
  * no writes or release while the microphone may still be active. */
 reset();to_capture();stop_fails=true;fault_mode=1u;finish();assert(active->state==PAIR_STOP_FAILED);
 uint32_t initial_stops=stops;writes=programs;for(unsigned n=0;n<99u;++n)step();
 assert(stops==initial_stops&&programs==writes&&board.microphone.running&&active->bound);
 stop_fails=false;step();assert(active->state==PAIR_FAILED&&!board.microphone.running&&active->error==ERR_STOP);
 assert(programs==writes&&app.recording.pipeline.workspace_bytes);released();
 /* Persistent failure has a finite retry budget and does not lose ownership. */
 reset();to_capture();stop_fails=true;fault_mode=1u;finish();initial_stops=stops;
 for(unsigned n=0;n<1000u;++n)step();assert(stops==initial_stops+3u&&active->state==PAIR_STOP_FAILED&&board.microphone.running&&active->bound);
 stop_fails=false;command("DPAIR RELEASE",false);for(unsigned n=0;n<150u&&active;++n)step();assert(!active&&!board.microphone.running&&!observer&&board.pcm_sink==original&&!app.recording.pipeline.workspace_bytes);
 /* Deadlines remain correct over the 32-bit millisecond counter wrap. */
 reset();to_capture();tick=0xfffffff0u;stop_fails=true;command("DPAIR RELEASE",false);step();
 assert(active&&active->state==PAIR_STOP_FAILED&&board.microphone.running);initial_stops=stops;
 for(unsigned n=0;n<99u;++n)step();assert(stops==initial_stops);
 stop_fails=false;for(unsigned n=0;n<10u&&active;++n)step();assert(!active&&!board.microphone.running&&!observer);
 /* A partial callback restore must not try to detach its observer twice. */
 reset();to_capture();restore_mono_fails=true;command("DPAIR RELEASE",false);step();
 assert(active&&active->state==PAIR_STOP_FAILED&&!board.microphone.running&&active->pair_unbound&&active->bound&&!observer);
 restore_mono_fails=false;for(unsigned n=0;n<150u&&active;++n)step();assert(!active&&board.pcm_sink==original&&!app.recording.pipeline.workspace_bytes);
 /* Independent next fixture, not a production recovery/reset workaround. */
 reset();to_capture();finish();wip_fails=true;command("DPAIR RELEASE",false);step();assert(active&&app.recording.pipeline.workspace_bytes);
 /* A transient NOR-ready failure must not strand the finished diagnostic
  * forever after the caller already asked for release. */
 reset();to_capture();finish();wip_fails=true;command("DPAIR RELEASE",false);step();
 assert(active&&active->error==ERR_RELEASE&&app.recording.pipeline.workspace_bytes);
 wip_fails=false;for(unsigned n=0;n<500u&&active;++n)step();
 assert(!active&&!app.recording.pipeline.workspace_bytes&&!board.microphone.running&&board.pcm_sink==original);
 /* Persistent NOR-not-ready or ownership refusal stays bounded and keeps
  * the exact reservation. A later explicit release starts a fresh cycle. */
 for(unsigned m=0;m<2u;++m){reset();to_capture();finish();
  if(m==0u)wip_fails=true;else space_blocked=true;writes=programs;
  command("DPAIR RELEASE",false);for(unsigned n=0;n<1000u;++n)step();
  assert(active&&active->state==PAIR_FAILED&&active->error==ERR_RELEASE&&!active->release_requested&&wait_calls==3u);
  assert(app.recording.pipeline.workspace_bytes&&programs==writes&&board.pcm_sink==original);
  wip_fails=space_blocked=false;command("DPAIR RELEASE",false);step();assert(!active&&wait_calls==4u&&!app.recording.pipeline.workspace_bytes);}
 /* Retry deadlines survive the millisecond tick wrap. */
 reset();to_capture();finish();tick=0xfffffff0u;wip_fails=true;command("DPAIR RELEASE",false);step();
 assert(active&&wait_calls==1u);wip_fails=false;for(unsigned n=0;n<99u;++n)step();assert(active&&wait_calls==1u);
 for(unsigned n=0;n<5u&&active;++n)step();assert(!active&&wait_calls==2u);
 reset();to_capture();stop_fault=true;finish();assert(active->state==PAIR_FAILED&&active->error==ERR_SOURCE&&active->stream.faults&&!board.microphone.running);released();
 reset();to_capture();tick+=120001u;step();step();assert(!active&&!board.microphone.running&&!app.recording.pipeline.workspace_bytes);
 reset();command("DPAIR START suffix",true);assert(!active);command("DPAIR START",true);assert(active&&active->state==PAIR_ERASE);
 for(unsigned n=0;n<8u&&!board.nor.erase_active;++n)step();assert(board.nor.erase_active);command("DPAIR RELEASE",false);for(unsigned n=0;n<5u&&active;++n)step();assert(!active&&!board.nor.erase_active&&!starts);
 puts("PASS actual target capture controller: bounded ownership, readback, fault/stop/release/expiry, no callback UART; software ports only");return 0;
}
