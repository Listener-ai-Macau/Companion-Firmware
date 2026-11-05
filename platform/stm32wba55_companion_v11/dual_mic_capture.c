/* Finite explicit diagnostic. Normal mono Opus/recording identities and
 * protocols are not changed. No callback I/O, permanent partition, heap,
 * second encoder or live-UART PCM dump. Files are volatile engineering
 * windows: reboot does not recover or advertise them as normal recordings. */
#ifdef COMP_DMIC_CAPTURE_HOST_TEST
#include "dual_mic_capture_test_platform.h"
#else
#include "dual_mic_capture.h"
#include "companion_opus16_rt.h"
#include "ble_product.h"
#include "update_product.h"
#endif
#include "wba_dual_mic_pair_stream.h"
#include <stdio.h>
#include <string.h>

enum { PAIR_ERASE=1,PAIR_VERIFY,PAIR_HEADER,PAIR_CAPTURE,PAIR_DRAIN,
       PAIR_READY,PAIR_DUMP,PAIR_FAILED,PAIR_STOP_FAILED,PAIR_FINAL_VERIFY };
enum { ERR_NONE=0,ERR_SOURCE,ERR_DEADLINE,ERR_MEDIA,ERR_START,ERR_STOP,
       ERR_TIMEOUT,ERR_CANCELED,ERR_RELEASE };
#define PAIR_BLOCKS 200u
#define PAIR_BYTES (80u+664u*PAIR_BLOCKS+48u)
#define PAIR_LEASE_BYTES ((PAIR_BYTES+4095u)&~4095u)
typedef struct {
    comp_dmic_stream_t stream;
    uint8_t queue[2u*COMP_DMIC_STREAM_PACKET_BYTES],scratch[256];
    comp_v11_microphone_stats_t baseline;
    comp_v11_product_app_t *app;
    comp_wba_pdm_pcm_frame_fn_t old_sink;
    void *old_sink_context;
    uint64_t pdm_bad;
    uint32_t base,erase_cursor,verify_cursor,offset,dump_cursor;
    uint32_t programmed_crc,readback_crc;
    uint32_t started,last_service,max_service_ms,token,capture_id,expires,stop_retry_due,release_retry_due;
    uint16_t packet_cursor;
    uint8_t state,error,stop_retry_count,release_retry_count;
    bool stop_requested,release_requested,bound,pair_unbound,reported,old_sampling,old_playback,identity_ready;
} pair_capture_t;
/* No additional resident PCM queue. Alignment is established inside the
 * unused ring; the workspace gate prevents a new engine from initializing it. */
_Static_assert(sizeof(pair_capture_t)+7u<=sizeof(((comp_cont_recording_t *)0)->pcm),
               "finite pair capture must fit the existing idle PCM ring");
static pair_capture_t *active;
static uint8_t command_match,command_candidates=31u,command_invalid,command_pending;
static const uint8_t image_source[20]=COMPANION_DMIC_CAPTURE_SOURCE_BYTES;

bool comp_v11_dual_pair_owned(const comp_v11_product_app_t *app)
{return active&&active->app==app;}
bool comp_v11_dual_pair_foreground_pending(const comp_v11_product_app_t *app)
{
    /* Pending PCM is runnable foreground work. Do not pay one WFI/tick gap
     * for each page while samples are already waiting in this finite queue.
     * An empty queue, NOR erase, stopped failure and normal product retain
     * their previous idle policy. DMA/IRQs and BLE still run every turn. */
    const pair_capture_t *c=active;
    return c&&c->app==app&&!c->release_requested&&c->state==PAIR_CAPTURE&&c->stream.queued!=0u;
}
void comp_v11_dual_pair_accept(uint8_t byte)
{
    static const char *const commands[]={"DPAIR START","DPAIR STOP","DPAIR STATUS","DPAIR DUMP","DPAIR RELEASE"};
    if(byte=='?'){command_match=0;command_candidates=31u;command_invalid=0;return;}
    if(byte=='\n'){
        if(!command_invalid)for(unsigned i=0;i<5u;++i)
            if((command_candidates&(1u<<i))&&commands[i][command_match]=='\0')command_pending=(uint8_t)(i+1u);
        command_match=0;command_candidates=31u;command_invalid=0;return;
    }
    uint8_t candidates=0;
    for(unsigned i=0;i<5u;++i)if((command_candidates&(1u<<i))&&
        (byte=='\r'?commands[i][command_match]=='\0':
         commands[i][command_match]!='\0'&&commands[i][command_match]==(char)byte))candidates|=(uint8_t)(1u<<i);
    if(!candidates)command_invalid=1u;
    command_candidates=candidates;if(byte!='\r'&&!command_invalid)command_match++;
}
static uint64_t bad_pdm(const comp_v11_hal_t *b)
{
    const comp_wba_pdm_stats_t *s=&b->microphone.processing.stats;
    return s->missing_dma_blocks+s->reordered_dma_blocks+s->invalid_dma_blocks+s->pcm_frames_rejected;
}
static bool accept_mono(void *context,const int16_t *pcm,size_t count,uint32_t rate)
{(void)context;return pcm&&count==160u&&rate==16000u;}
static void accept_pair(void *context,const int16_t *pcm,size_t count,uint32_t rate)
{
    pair_capture_t *c=context;comp_v11_hal_t *b=c->app->board;
    if(c!=active||c->state!=PAIR_CAPTURE)return;
    if(bad_pdm(b)!=c->pdm_bad||!comp_v11_microphone_hal_capture_matches(&b->microphone,&c->baseline))
        comp_dmic_stream_invalidate(&c->stream);
    /* Current P639 hardware sequence discards0..2, primes3, retains4 onward.
     * DMA sequence is the physical position; callback count cannot hide gaps. */
    uint64_t first=(uint64_t)b->microphone.processing.stats.last_dma_sequence*160u;
    (void)comp_dmic_stream_push(&c->stream,pcm,count,rate,first);
}
static void status(pair_capture_t *c)
{
    if(c->app->board->microphone.running||comp_v11_ble_linked())return;
    char line[224];
    (void)snprintf(line,sizeof(line),
        "DPAIR STATE state=%u error=%u capture=%lu token=%lu blocks=%lu bytes=%lu faults=%lu max_service_ms=%lu synthetic=0 engineering_window=1\r\n",
        (unsigned)c->state,(unsigned)c->error,(unsigned long)c->capture_id,(unsigned long)c->token,
        (unsigned long)c->stream.blocks,(unsigned long)c->offset,(unsigned long)c->stream.faults,(unsigned long)c->max_service_ms);
    comp_v11_hal_log(line);
    const comp_wba_pdm_stats_t *p=&c->app->board->microphone.processing.stats;
    const comp_v11_microphone_hal_t *m=&c->app->board->microphone;
    (void)snprintf(line,sizeof(line),
        "DPAIR FAULTS missing=%lu reordered=%lu invalid=%lu rejected=%lu stale=%lu overflow=%lu irq=%lu deadline=%u\r\n",
        (unsigned long)(p->missing_dma_blocks-c->baseline.processing.missing_dma_blocks),
        (unsigned long)(p->reordered_dma_blocks-c->baseline.processing.reordered_dma_blocks),
        (unsigned long)(p->invalid_dma_blocks-c->baseline.processing.invalid_dma_blocks),
        (unsigned long)(p->pcm_frames_rejected-c->baseline.processing.pcm_frames_rejected),
        (unsigned long)(m->stale_dma_halves-c->baseline.stale_dma_halves),
        (unsigned long)(m->event_queue_overflows-c->baseline.event_queue_overflows),
        (unsigned long)(m->error_irqs-c->baseline.error_irqs),(unsigned)(c->error==ERR_DEADLINE));
    comp_v11_hal_log(line);
}
static void stop_failed(pair_capture_t *c)
{
    if(c->state!=PAIR_STOP_FAILED){c->stop_retry_count=0u;c->stop_retry_due=HAL_GetTick()+100u;}
    c->error=ERR_STOP;c->state=PAIR_STOP_FAILED;
}
static void restore_sinks(pair_capture_t *c)
{
    if(!c->bound||c->app->board->microphone.running)return;
    if(!c->pair_unbound)
        c->pair_unbound=comp_v11_hal_set_pair_sink(c->app->board,NULL,c);
    if(c->pair_unbound&&comp_v11_hal_set_pcm_sink(c->app->board,c->old_sink,c->old_sink_context))
        c->bound=false;
    else stop_failed(c);
}
static bool stop_capture(pair_capture_t *c,bool valid)
{
    comp_v11_hal_t *b=c->app->board;
    if(b->microphone.running&&!comp_v11_hal_microphone_enable(b,false)){
        stop_failed(c);return false;
    }
    if(valid&&(bad_pdm(b)!=c->pdm_bad||
       b->microphone.stale_dma_halves!=c->baseline.stale_dma_halves||
       b->microphone.event_queue_overflows!=c->baseline.event_queue_overflows||
       b->microphone.processing_rejections!=c->baseline.processing_rejections||
       b->microphone.error_irqs!=c->baseline.error_irqs)){
        valid=false;c->error=ERR_SOURCE;comp_dmic_stream_invalidate(&c->stream);
    }
    if(c->identity_ready)(void)comp_dmic_stream_finish(&c->stream,valid);
    restore_sinks(c);return c->state!=PAIR_STOP_FAILED;
}
static void fail(pair_capture_t *c,uint8_t reason)
{
    if(!c->error)c->error=reason;
    if(c->identity_ready)comp_dmic_stream_invalidate(&c->stream);
    if(stop_capture(c,false))c->state=PAIR_FAILED;
}
static bool begin(comp_v11_product_app_t *app,uint32_t *guard)
{
    *guard=1u;if(active||!app||!app->board)return false;
    *guard=2u;if(!app->storage_layout_ready||!app->recording_ready||!app->recording.ready||!app->recording.media_ready)return false;
    *guard=3u;if(!companion_opus16_rt_workspace_available())return false;
    *guard=4u;if(app->recording.pipeline.workspace_bytes||app->recording.pipeline.workspace_requested)return false;
    *guard=5u;if(app->recording.capture.engine.microphone_active||app->recording.capture.engine.encoder_owned)return false;
    *guard=6u;if(app->board->microphone.running||app->board->playback_active||comp_v11_ble_linked())return false;
    *guard=7u;if(comp_v11_update_product_busy()||app->pet_profile.writing)return false;
    *guard=8u;if(app->runtime.prepare_pending||app->runtime.start_pending||app->runtime.command_pending||app->runtime.capture_active||app->runtime.stop_pending)return false;
    uint8_t uid[12];uint32_t base;
    *guard=9u;if(!comp_v11_hal_device_uid(uid))return false;
    *guard=12u;if(!comp_wba_recording_product_workspace(&app->recording,PAIR_LEASE_BYTES,&base))return false;
    uintptr_t address=(uintptr_t)app->recording.capture.engine.pcm;
    pair_capture_t *c=(pair_capture_t *)((address+7u)&~(uintptr_t)7u);
    memset(c,0,sizeof(*c));c->app=app;c->base=base;c->state=PAIR_ERASE;c->started=HAL_GetTick();
    c->expires=HAL_GetTick()+120000u;
    c->old_sampling=app->board->power_sampling_inhibited;c->old_playback=app->board->services.playback_inhibited;
    active=c;app->board->power_sampling_inhibited=true;app->board->services.playback_inhibited=true;
    comp_power_policy_set_blocker(&app->board->power,COMP_POWER_BLOCKER_STORAGE,true);
    *guard=0u;status(c);return true;
}
static void release(pair_capture_t *c)
{
    comp_v11_hal_t *b=c->app->board;
    if(b->microphone.running||c->bound||c->state==PAIR_STOP_FAILED)return;
    if(b->nor.erase_active){
        (void)companion_spi_nor_stm32wba_erase_finish_poll(&b->nor,b->nor.erase_address,b->nor.erase_bytes);
        return; /* Never resume, reset or abandon another erase owner. */
    }
    if((int32_t)(HAL_GetTick()-c->release_retry_due)<0)return;
    /* A timed-out program is not a free device. Retire real WIP before
     * handing the temporary extent to recording/OTA; never retry its write. */
    uint32_t unused;
    if(companion_spi_nor_stm32wba_wait_ready(&b->nor,b->nor.config.page_program_timeout_ms)!=COMPANION_SPI_NOR_STM32WBA_OK||
       !comp_wba_recording_product_workspace(&c->app->recording,0u,&unused)){
        c->error=ERR_RELEASE;c->state=PAIR_FAILED;status(c);
        /* Keep the exact extent reserved while NOR readiness/ownership is
         * uncertain. Retry only a few times; a later explicit RELEASE can
         * initiate another bounded cycle after a persistent fault. */
        ++c->release_retry_count;c->release_retry_due=HAL_GetTick()+100u;
        if(c->release_retry_count>=3u)c->release_requested=false;
        return;
    }
    c->release_requested=false;
    b->power_sampling_inhibited=c->old_sampling;b->services.playback_inhibited=c->old_playback;
    comp_power_policy_set_blocker(&b->power,COMP_POWER_BLOCKER_STORAGE,false);
    active=NULL;comp_v11_hal_log("DPAIR RELEASED mic=0 workspace=0\r\n");
}
void comp_v11_dual_pair_command(comp_v11_product_app_t *app,bool normal_idle)
{
    uint8_t command=command_pending;command_pending=0u;if(!command)return;
    if(command==1u){
        uint32_t reason=14u;
        if(!normal_idle||!begin(app,&reason)){
            if(normal_idle&&!app->board->microphone.running){
                char line[128];(void)snprintf(line,sizeof(line),"DPAIR REJECTED guard=%lu workspace=%lu requested=%lu\r\n",
                    (unsigned long)reason,(unsigned long)app->recording.pipeline.workspace_bytes,
                    (unsigned long)app->recording.pipeline.workspace_requested);comp_v11_hal_log(line);
            }
        }
        return;
    }
    pair_capture_t *c=active;
    if(!c||c->app!=app){if(normal_idle)comp_v11_hal_log("DPAIR IDLE\r\n");return;}
    if(command==2u)c->stop_requested=true;
    if(command==3u)status(c);
    if(command==4u&&!app->board->microphone.running&&(c->state==PAIR_READY||c->state==PAIR_FAILED)&&!app->board->nor.erase_active){
        c->dump_cursor=0u;c->state=PAIR_DUMP;
    }
    if(command==5u){
        c->stop_requested=true;c->release_requested=true;
        c->release_retry_count=0u;c->release_retry_due=HAL_GetTick();
        /* An explicit later release permits one more bounded recovery cycle. */
        if(c->state==PAIR_STOP_FAILED){c->stop_retry_count=0u;c->stop_retry_due=HAL_GetTick()+100u;}
    }
}
static bool drain_one(pair_capture_t *c)
{
    const uint8_t *bytes;size_t count;
    if(!comp_dmic_stream_peek(&c->stream,&bytes,&count))return true;
    if(c->packet_cursor>=count||c->offset>PAIR_BYTES){fail(c,ERR_MEDIA);return false;}
    size_t remaining=count-c->packet_cursor;
    size_t n=256u-(c->offset&255u);if(n>remaining)n=remaining;
    if(n>PAIR_BYTES-c->offset){fail(c,ERR_MEDIA);return false;}
    companion_spi_nor_stm32wba_t *nor=&c->app->board->nor;
    /* The port returns only after page-program WIP retires. Keep the two
     * finite PCM slots moving; per-page immediate READ doubled the real-time
     * operation count and overflowed them on the actual board. Read EVERY
     * persisted byte after DMA stops, before READY or a clean dump is legal. */
    if(companion_spi_nor_stm32wba_program(nor,c->base+c->offset,bytes+c->packet_cursor,n)!=COMPANION_SPI_NOR_STM32WBA_OK){
        fail(c,ERR_MEDIA);return false;
    }
    c->programmed_crc=comp_dmic_crc(c->programmed_crc,bytes+c->packet_cursor,n);
    c->offset+=(uint32_t)n;c->packet_cursor=(uint16_t)(c->packet_cursor+n);
    if(c->packet_cursor==count){(void)comp_dmic_stream_consume(&c->stream);c->packet_cursor=0u;}
    return true;
}
static void dump_one(pair_capture_t *c)
{
    if(c->app->board->microphone.running||comp_v11_ble_linked())return;
    char line[128];size_t n=c->offset-c->dump_cursor;if(n>32u)n=32u;
    if(!n){
        (void)snprintf(line,sizeof(line),"DPAIR END bytes=%lu error=%u\r\n",(unsigned long)c->offset,(unsigned)c->error);
        comp_v11_hal_log(line);c->state=c->error?PAIR_FAILED:PAIR_READY;return;
    }
    if(companion_spi_nor_stm32wba_read(&c->app->board->nor,c->base+c->dump_cursor,c->scratch,n)!=COMPANION_SPI_NOR_STM32WBA_OK){fail(c,ERR_MEDIA);return;}
    int at=snprintf(line,sizeof(line),"DPAIR DATA offset=%lu hex=",(unsigned long)c->dump_cursor);
    static const char hex[]="0123456789abcdef";
    for(size_t i=0;i<n;++i){line[at++]=hex[c->scratch[i]>>4];line[at++]=hex[c->scratch[i]&15u];}
    line[at++]='\r';line[at++]='\n';line[at]='\0';comp_v11_hal_log(line);c->dump_cursor+=(uint32_t)n;
}
void comp_v11_dual_pair_poll(comp_v11_product_app_t *app)
{
    pair_capture_t *c=active;if(!c||c->app!=app)return;
    comp_v11_hal_t *b=app->board;uint32_t now=HAL_GetTick();
    if(c->state==PAIR_STOP_FAILED){
        /* No capture is publishable after a failed stop. Keep the shared
         * workspace until the real HAL confirms the DMA is quiescent and
         * both callbacks are restored. Do not retry in a tight poll loop. */
        if(c->identity_ready)comp_dmic_stream_invalidate(&c->stream);
        if(c->stop_retry_count<3u&&(int32_t)(now-c->stop_retry_due)>=0){
            ++c->stop_retry_count;c->stop_retry_due=now+100u;
            if(b->microphone.running&&!comp_v11_hal_microphone_enable(b,false))return;
            restore_sinks(c);
            if(!c->bound)c->state=PAIR_FAILED;
        }
        return;
    }
    if(c->release_requested){
        if(c->state!=PAIR_READY&&c->state!=PAIR_FAILED&&c->state!=PAIR_DUMP){
            if(!stop_capture(c,false))return;
            c->state=PAIR_FAILED;c->error=ERR_CANCELED;
        }
        release(c);return;
    }
    if((int32_t)(now-c->expires)>=0&&c->state!=PAIR_FAILED){
        fail(c,ERR_TIMEOUT);c->release_requested=true;
        c->release_retry_count=0u;c->release_retry_due=HAL_GetTick();return;
    }
    if(comp_v11_ble_linked()||comp_v11_update_product_busy()){
        if(c->state!=PAIR_READY&&c->state!=PAIR_FAILED&&c->state!=PAIR_DUMP)fail(c,ERR_CANCELED);
        return; /* No radio changes or ownership transfer. */
    }
    if(c->stop_requested&&c->state!=PAIR_CAPTURE&&c->state!=PAIR_DRAIN&&c->state!=PAIR_READY&&c->state!=PAIR_FAILED&&c->state!=PAIR_DUMP){
        fail(c,ERR_CANCELED);return;
    }
    if(c->state==PAIR_ERASE){
        if(!c->identity_ready){
            /* The shared BLE entropy consumer is nonblocking and preserves
             * its reserve. Back-to-back reads can consume the last admitted
             * word before the sequenced producer refills. Keep this one
             * explicit job pending, service one word per foreground turn,
             * and never erase or start a microphone without both real IDs. */
            if(now-c->started>=100u){fail(c,ERR_START);return;}
#ifdef COMPANION_WBA_BLE_LINKED
            comp_v11_ble_console_idle_progress();
#endif
            uint32_t value=0u;
            if(!c->token){
                if(comp_v11_hal_random_u32(b,&value)&&value)c->token=value;
                return;
            }
            if(!c->capture_id){
                if(comp_v11_hal_random_u32(b,&value)&&value)c->capture_id=value;
                return;
            }
            uint8_t uid[12];
            if(!comp_v11_hal_device_uid(uid)||
               !comp_dmic_stream_begin(&c->stream,c->queue,2u,uid,image_source,
                   c->capture_id,c->token,640u,PAIR_BLOCKS,false)){
                fail(c,ERR_START);return;
            }
            c->identity_ready=true;
            return;
        }
        companion_spi_nor_stm32wba_status_t r=companion_spi_nor_stm32wba_erase_step(&b->nor,c->base+c->erase_cursor,4096u);
        if(r==COMPANION_SPI_NOR_STM32WBA_OK){c->erase_cursor+=4096u;if(c->erase_cursor==PAIR_LEASE_BYTES)c->state=PAIR_VERIFY;}
        else if(r!=COMPANION_SPI_NOR_STM32WBA_PENDING)fail(c,ERR_MEDIA);
        return;
    }
    if(c->state==PAIR_VERIFY){
        if(companion_spi_nor_stm32wba_read(&b->nor,c->base+c->verify_cursor,c->scratch,256u)!=COMPANION_SPI_NOR_STM32WBA_OK){fail(c,ERR_MEDIA);return;}
        for(unsigned i=0;i<256u;++i)if(c->scratch[i]!=255u){fail(c,ERR_MEDIA);return;}
        c->verify_cursor+=256u;if(c->verify_cursor==PAIR_LEASE_BYTES)c->state=PAIR_HEADER;return;
    }
    if(c->state==PAIR_HEADER){
        if(!drain_one(c)||!c->stream.header_sent)return;
        c->old_sink=b->pcm_sink;c->old_sink_context=b->pcm_sink_context;
        if(!comp_v11_hal_set_pcm_sink(b,accept_mono,c)){fail(c,ERR_START);return;}
        if(!comp_v11_hal_set_pair_sink(b,accept_pair,c)){
            (void)comp_v11_hal_set_pcm_sink(b,c->old_sink,c->old_sink_context);fail(c,ERR_START);return;
        }
        c->bound=true;c->state=PAIR_CAPTURE;
        if(!comp_v11_hal_microphone_enable(b,true)){fail(c,ERR_START);return;}
        comp_v11_microphone_hal_get_stats(&b->microphone,&c->baseline);c->pdm_bad=bad_pdm(b);
        c->started=c->last_service=HAL_GetTick();return;
    }
    if(c->state==PAIR_CAPTURE){
        uint32_t elapsed=now-c->last_service;
        if(elapsed>c->max_service_ms)c->max_service_ms=elapsed;
        if(elapsed>10u){fail(c,ERR_DEADLINE);return;}
        comp_v11_microphone_poll_result_t polled=comp_v11_microphone_hal_poll(&b->microphone);
        uint32_t completed=HAL_GetTick(),service=completed-c->last_service;
        if(service>c->max_service_ms)c->max_service_ms=service;
        if(service>10u){fail(c,ERR_DEADLINE);return;}
        c->last_service=completed;
        bool ok=polled!=COMP_V11_MIC_POLL_ERROR&&bad_pdm(b)==c->pdm_bad&&
            comp_v11_microphone_hal_capture_matches(&b->microphone,&c->baseline);
        if(!ok||c->stream.faults){fail(c,ERR_SOURCE);return;}
        if(HAL_GetTick()-c->started>3000u){fail(c,ERR_TIMEOUT);return;}
        if(c->stop_requested||c->stream.blocks==PAIR_BLOCKS){
            if(!stop_capture(c,true))return;
            c->state=PAIR_DRAIN;
        }
        /* One program OR readback, never an erase or UART call. DMA pending
         * always gets the next poll; the normal10ms failure gate stays hard. */
        if(!drain_one(c))return;
        if(b->microphone.running&&HAL_GetTick()-c->last_service>10u){fail(c,ERR_DEADLINE);return;}
        return;
    }
    if(c->state==PAIR_DRAIN){
        if(!drain_one(c))return;
        if(c->stream.end_sent){c->state=PAIR_FINAL_VERIFY;c->verify_cursor=0u;c->readback_crc=0u;}
        return;
    }
    if(c->state==PAIR_FINAL_VERIFY){
        if(b->microphone.running){fail(c,ERR_SOURCE);return;}
        size_t n=c->offset-c->verify_cursor;if(n>sizeof(c->scratch))n=sizeof(c->scratch);
        if(n){
            if(companion_spi_nor_stm32wba_read(&b->nor,c->base+c->verify_cursor,c->scratch,n)!=COMPANION_SPI_NOR_STM32WBA_OK){fail(c,ERR_MEDIA);return;}
            c->readback_crc=comp_dmic_crc(c->readback_crc,c->scratch,n);c->verify_cursor+=(uint32_t)n;return;
        }
        if(c->readback_crc!=c->programmed_crc){fail(c,ERR_MEDIA);return;}
        c->state=c->error?PAIR_FAILED:PAIR_READY;status(c);comp_v11_hal_dual_mic_report(b,c->token);c->reported=true;
        return;
    }
    if(c->state==PAIR_DUMP){dump_one(c);return;}
    if(c->state==PAIR_FAILED&&!c->reported&&!b->microphone.running&&!b->nor.erase_active){status(c);c->reported=true;}
}
