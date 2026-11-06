#include "reset_witness.h"
#include "diag_flash_target.h"
#include "companion_crc32.h"
#if defined(COMPANION_OPUS_FAST_MEMORY) && COMPANION_OPUS_FAST_MEMORY
#include "companion_opus_memory.h"
#endif
#include "product_app.h"
#if COMPANION_WBA_DUAL_PAIR_CAPTURE
#include "dual_mic_capture.h"
#endif
#include "cpu_profile_target.h"
#include "companion_cpu_stage.h"
#include "diagnostic_console.h"
#include "diag_log.h"
#include "recording_gap_probe.h"
#include "companion_link.h"
#include "low_power_target.h"
#include "memory_target.h"
#include "battery_adc.h"
#ifndef COMPANION_WBA_PERIODIC_DIAGNOSTICS
#define COMPANION_WBA_PERIODIC_DIAGNOSTICS 0
#endif
#include "wba_recording_crc.h"
#include "panel_boot_idle.h"
#include "boot_receipt.h"
#include <stdio.h>
#ifdef COMPANION_WBA_BLE_LINKED
#include "ble_product.h"
#include "update_product.h"
#include "wba_ota_gatt.h"
#include "stm32wbaxx_ll_iwdg.h"
#endif

/* No board is flashed by the build. This identity distinguishes software
 * coordination from BLE/recording/physical product acceptance. */
comp_v11_hal_t companion_v11;
#if COMP_WBA_INTERNAL_FLASH_KIB == 512u
/* The large product object fits SRAM1 together with initialized data. Keep
 * it out of the CE hole; remaining BSS and the existing stack use SRAM2. */
comp_v11_product_app_t companion_app __attribute__((section(".sram1.bss"),aligned(8)));
#else
comp_v11_product_app_t companion_app;
#endif
/* Service/diagnostic dispatch favors code size. Audio DMA/IRQs and capture
 * codec/PDM remain in their original translation units and optimization. */
#if defined(__GNUC__)
#pragma GCC optimize ("Oz")
#endif

#ifdef COMPANION_WBA_BLE_LINKED
static comp_recording_gap_probe_t recording_gap_probe_state;
static void recording_gap_probe_poll(void)
{
    const comp_wba_recording_pipeline_t *pipeline=&companion_app.recording.pipeline;
    const comp_cont_recording_t *engine=&companion_app.recording.capture.engine;
    const bool recording_active=companion_app.recording.media_ready &&
        pipeline->state==COMP_PIPE_RECORDING &&
        engine->active.descriptor.source_mode==COMP_WBA_RECORDING_SOURCE_MIC_SAI;
    comp_recording_gap_probe_event_t event;
    if(comp_recording_gap_probe_step(&recording_gap_probe_state,HAL_GetTick(),
            engine->active.descriptor.recording_id,recording_active,
            companion_v11.microphone.running,comp_v11_ble_linked(),
            companion_v11.microphone.processed_dma_halves,&event)) {
        /* RAM-only evidence. Export happens later over GATT after capture;
         * no UART output, polling wait, flash write, or per-frame logging. */
        comp_diag_log_record_code(event.code,COMP_DIAG_SEV_INFO,
            event.arg0,event.arg1,event.arg2,event.arg3);
    }
}
#endif
static bool diagnostic_write(void *context,const char *line)
{
    (void)context;
    return comp_v11_hal_debug_write(line);
}
static void diagnostic_swd_pins(void)
{
    char line[192];
    /* UART remains usable when SWD cannot attach. Observe the actual pin
     * mux through that independent path; never change pin modes, reset the
     * target or enable debug/low-power settings to manufacture a good result. */
    const uint32_t mode=GPIOA->MODER, alternate=GPIOA->AFR[1], pull=GPIOA->PUPDR;
    (void)snprintf(line,sizeof(line),
        "SWD1 pa13_mode=%u pa13_af=%u pa13_pull=%u pa14_mode=%u pa14_af=%u pa14_pull=%u debug=%08lX sleepdeep=%u low_power=%s\r\n",
        (unsigned)((mode>>26u)&3u),(unsigned)((alternate>>20u)&15u),
        (unsigned)((pull>>26u)&3u),(unsigned)((mode>>28u)&3u),
        (unsigned)((alternate>>24u)&15u),(unsigned)((pull>>28u)&3u),
        (unsigned long)DBGMCU->SCR,(unsigned)((SCB->SCR&SCB_SCR_SLEEPDEEP_Msk)!=0u),
        comp_v11_low_power_identity());
    (void)diagnostic_write(NULL,line);
    (void)snprintf(line,sizeof(line),"SCREEN1 enabled=%u\r\n",(unsigned)COMPANION_WBA_SCREEN_ENABLED);
    (void)diagnostic_write(NULL,line);
    (void)snprintf(line,sizeof(line),"BUTTON1 max_hold_ms=%u last_event=%u raw=%u pressed=%u consumed=%u wake_only=%u double=%u runtime_result=%u rejected=%lu\r\n",
        (unsigned)companion_app.button.max_hold_ms,(unsigned)companion_app.button.last_event,
        (unsigned)companion_app.button.raw,(unsigned)companion_app.button.pressed,
        (unsigned)companion_app.button.consumed,(unsigned)companion_app.button.wake_only,
        (unsigned)companion_app.button.double_enabled,(unsigned)companion_app.runtime.last_result,
        (unsigned long)companion_app.runtime.rejected_commands);
    (void)diagnostic_write(NULL,line);
    (void)snprintf(line,sizeof(line),"BUTTON2 hold_ms=%u marks=%lu mark_request=%lu mark_pending=%u\r\n",
        COMPANION_WBA_SCREEN_ENABLED?700u:1000u,
        (unsigned long)companion_app.recording.capture.engine.bookmark_sequence,
        (unsigned long)companion_app.recording.capture.engine.bookmark_request,
        (unsigned)companion_app.recording.capture.engine.bookmark_phase);
    (void)diagnostic_write(NULL,line);
    (void)snprintf(line,sizeof(line),"BUTTON3 down_edges=%lu up_edges=%lu down_ms=%lu up_ms=%lu\r\n",
        (unsigned long)companion_v11.wake_events.key_falling_count,
        (unsigned long)companion_v11.wake_events.key_rising_count,
        (unsigned long)companion_v11.wake_events.key_down_ms,
        (unsigned long)companion_v11.wake_events.key_up_ms);
    (void)diagnostic_write(NULL,line);
    (void)snprintf(line,sizeof(line),"BATPATH1 pa5_mode=%u gate_on=%02X io=%02X input_age=%lu pg=%u stat=%u seen=%u\r\n",
        (unsigned)((mode>>10u)&3u),
        (unsigned)comp_v11_battery_adc_stats()->gate_observation,
        (unsigned)companion_v11.expander_raw_inputs,
        (unsigned long)(HAL_GetTick()-companion_v11.power_monitor.input_ms),
        (unsigned)companion_v11.power_monitor.pg_high,
        (unsigned)companion_v11.power_monitor.stat_high,
        (unsigned)companion_v11.power_monitor.input_seen);
    (void)diagnostic_write(NULL,line);
#if defined(COMPANION_WBA_BLE_LINKED) && COMPANION_WBA_EXPERIMENTAL_STOP1
    uint32_t entries,ms,failures; comp_v11_low_power_stats(&entries,&ms,&failures);
    (void)snprintf(line,sizeof(line),"POWER1 entries=%lu compensated_ms=%lu failures=%lu wake_flags=%lu\r\n",
        (unsigned long)entries,(unsigned long)ms,(unsigned long)failures,
        (unsigned long)comp_v11_low_power_wake_flags());
    (void)diagnostic_write(NULL,line);
    const comp_v11_stop_wake_snapshot_t *wake=comp_v11_low_power_wake_snapshot();
    for (unsigned i=0; i<2u; ++i) {
        const comp_v11_stop_irq_snapshot_t *irq=i?&wake->after:&wake->before;
        (void)snprintf(line,sizeof(line),
            "POWER1_IRQ point=%s valid=%u entered=%u nvic=%08lX,%08lX,%08lX icsr=%08lX exti_r=%08lX exti_f=%08lX\r\n",
            i?"after":"before",(unsigned)wake->captured,(unsigned)wake->entered_stop,
            (unsigned long)irq->pending_enabled[0],(unsigned long)irq->pending_enabled[1],
            (unsigned long)irq->pending_enabled[2],(unsigned long)irq->icsr,
            (unsigned long)irq->exti_rising,(unsigned long)irq->exti_falling);
        (void)diagnostic_write(NULL,line);
    }
#endif
}
static comp_v11_diag_activity_t diagnostic_activity(bool for_pairing,bool *fault_quiescent)
{
    const uint32_t blockers=companion_v11.power.blockers;
    bool recording_transfer=(blockers&COMP_POWER_BLOCKER_RECORDING_TRANSFER)!=0u;
#ifdef COMPANION_WBA_BLE_LINKED
    /* A COMPLETE transfer means accepted by the local stack, not received by
     * Type. Do not spend~400ms on a blocking snapshot over its queued tail or
     * inter-file batch gap. Pending queries remain queued until real release. */
    recording_transfer=recording_transfer || comp_v11_ble_blocking_diagnostic_busy();
#endif
    /* A FAILED pipeline keeps its reservations locked, but no longer moves
     * data. A poisoned adapter also freezes any retained catalogue phase;
     * read-only diagnostics may inspect it while the real mic and owned NOR
     * erase are stopped. Recovery independently qualifies physical status. */
    const bool stopped_fault=!for_pairing &&
        companion_app.recording.pipeline.state==COMP_PIPE_FAILED &&
        companion_app.recording.media_ready && companion_app.recording.pipeline.engine_bound &&
        !companion_app.recording.capture.engine.microphone_active &&
        !companion_v11.microphone.running && !companion_v11.nor.erase_active &&
        (!companion_app.recording.catalog.phase || companion_app.recording.storage.poisoned);
    const comp_v11_diag_activity_t activity={
        .ui_pending=(blockers&COMP_POWER_BLOCKER_UI_PENDING)!=0u,
        .microphone_capture=(blockers&COMP_POWER_BLOCKER_MIC_CAPTURE)!=0u && !stopped_fault,
        .screen_maintenance=(blockers&COMP_POWER_BLOCKER_SCREEN_MAINTENANCE)!=0u,
        /* A presenter submit can start a transaction after HAL updated the
         * sleep blockers. Use its current state before blocking UART output. */
        .screen_wait=(blockers&COMP_POWER_BLOCKER_SCREEN_WAIT)!=0u ||
                     companion_v11.panel.status==COMP_SSD1681_WBA_ACTIVE,
        .playback=(blockers&COMP_POWER_BLOCKER_PLAYBACK)!=0u,
        .battery_sample=(blockers&COMP_POWER_BLOCKER_BATTERY_SAMPLE)!=0u,
        .recording_transfer=recording_transfer,
        .storage=((blockers&COMP_POWER_BLOCKER_STORAGE)!=0u && !stopped_fault)
#if COMPANION_WBA_DUAL_PAIR_CAPTURE
            || comp_v11_dual_pair_owned(&companion_app)
#endif
            ,
        .update=(blockers&COMP_POWER_BLOCKER_UPDATE)!=0u,
        .bond_nvm=(blockers&COMP_POWER_BLOCKER_BOND_NVM)!=0u,
        .playback_active=companion_v11.playback_active,
        .microphone_running=companion_v11.microphone.running,
        .runtime_prepare=companion_app.runtime.prepare_pending,
        .runtime_start=companion_app.runtime.start_pending,
        .runtime_command=companion_app.runtime.command_pending,
        .runtime_capture=companion_app.runtime.capture_active,
        .runtime_stop=companion_app.runtime.stop_pending,
    };
    if(fault_quiescent)*fault_quiescent=stopped_fault;
    return activity;
}
static uint32_t diagnostic_output_blockers(bool for_pairing)
{
    const comp_v11_diag_activity_t activity=diagnostic_activity(for_pairing,NULL);
    return for_pairing ? comp_v11_diag_console_pairing_blockers(&activity) :
                         (uint32_t)!comp_v11_diag_console_output_safe(&activity);
}
static bool diagnostic_fault_output_safe(void)
{
    bool quiescent=false;
    const comp_v11_diag_activity_t activity=diagnostic_activity(false,&quiescent);
    return companion_app.recording.media_ready && companion_app.recording.pipeline.engine_bound &&
        comp_v11_diag_console_fault_output_safe(&activity,quiescent);
}
static void diagnostic_record_queue(void)
{
    const comp_wba_recording_pipeline_t *p=&companion_app.recording.pipeline;
    const comp_cont_recording_t *r=&companion_app.recording.capture.engine;
    const comp_v11_diag_record_queue_t s={
        .token=p->token,.engine_bound=p->engine_bound,.state=(uint8_t)r->state,
        .microphone_active=r->microphone_active,.pcm_blocks=r->stats.accepted_pcm_blocks,
        .encoded_packets=r->stats.encoded_packets,.durable_bytes=r->stats.durable_bytes,
        .queue_peak=r->stats.max_ring_depth,.overflows=r->stats.overflows,
        .budget_failures=r->stats.budget_failures,.pcm_fill=r->codec.pcm_fill,
        .stage_bytes=r->stage_length,.queue_depth=r->ring_count,
        .queue_slots=COMP_CONT_PCM_SLOTS,.writer_phase=r->writer.phase,
    };
    (void)comp_v11_diag_console_emit_record_queue(&s,diagnostic_write,NULL);
}
static void diagnostic_capture_feedback(void)
{
#if !COMPANION_WBA_SCREEN_ENABLED
    bool updating=false;
#ifdef COMPANION_WBA_BLE_LINKED
    updating=comp_v11_update_product_busy();
#endif
    const comp_capture_feedback_t feedback=comp_v11_product_capture_feedback(&companion_app,updating);
    char line[96];
    (void)snprintf(line,sizeof(line),"CAPTURE1 state=%u flags=%u full_reason=%u mark_request=%lu\r\n",
        feedback.state,feedback.flags,feedback.full_reason,(unsigned long)feedback.bookmark_request);
    (void)diagnostic_write(NULL,line);
#endif
}
static void diagnostic_record_fault(void)
{
    const comp_wba_recording_pipeline_t *p=&companion_app.recording.pipeline;
    const comp_cont_recording_t *r=&companion_app.recording.capture.engine;
    comp_v11_microphone_stats_t mic;
    comp_v11_microphone_hal_get_stats(&companion_v11.microphone,&mic);
    const comp_runtime_t *rt=&companion_app.runtime;
    const comp_v11_diag_record_fault_t s={
        .token=p->token,.core_hz=HAL_RCC_GetSysClockFreq(),.blockers=companion_v11.power.blockers,
        .deadline=companion_app.capture_deadline_faults,.foreground_ms=companion_app.max_capture_foreground_ms,
        .budget_failures=r->stats.budget_failures,.max_poll_ms=r->stats.max_poll_ms,
        .pcm_blocks=r->stats.accepted_pcm_blocks,.encoded_packets=r->stats.encoded_packets,
        .stale=mic.stale_dma_halves,.overflows=mic.event_queue_overflows,
        .rejections=mic.processing_rejections,.irq_errors=mic.error_irqs,
        .runtime_flags=(uint16_t)((unsigned)rt->prepare_pending | (unsigned)rt->start_pending<<1u |
            (unsigned)rt->command_pending<<2u | (unsigned)rt->capture_active<<3u | (unsigned)rt->stop_pending<<4u),
        .pipeline=(uint8_t)p->state,.failure=(uint8_t)p->failure,.record_fault=companion_app.recording.last_fault,
        .engine=(uint8_t)r->state,.engine_failure=(uint8_t)r->failure,.queue_depth=r->ring_count,
        .catalog_phase=companion_app.recording.catalog.phase,.future_phase=p->future_phase,.consume_phase=p->consume_phase,
    };
    (void)comp_v11_diag_console_emit_record_fault(&s,diagnostic_write,NULL);
    const comp_v11_memory_stats_t *memory_stats=comp_v11_memory_observe();
    /* Only after actual stopped-fault admission, never in a live audio loop.
     * Site1=checkpoint entry,2=after work,3=post-encode DMA,
     * 4=product entry,5=before BLE. Original timing/protection is unchanged. */
    char line[256];
    (void)snprintf(line,sizeof(line),
        "RFAIL2 DEADLINE token=%lu site=%u hal_max_ms=%lu recorder_max_ms=%lu ble_max_ms=%lu runtime_max_ms=%lu presenter_max_ms=%lu render_max_ms=%lu stack_min=%lu stack_guard=%u stack_low=%u\r\n",
        (unsigned long)p->token,(unsigned)companion_app.capture_deadline_site,
        (unsigned long)companion_app.max_capture_hal_ms,
        (unsigned long)companion_app.max_capture_recorder_ms,
        (unsigned long)companion_app.max_capture_ble_ms,
        (unsigned long)companion_app.max_capture_runtime_ms,
        (unsigned long)companion_app.max_capture_presenter_ms,
        (unsigned long)companion_app.max_capture_render_ms,
        (unsigned long)memory_stats->stack.minimum_free_bytes,
        (unsigned)memory_stats->stack.guard_failed,(unsigned)memory_stats->stack.low_latched);
    (void)comp_v11_hal_debug_write(line);
    diagnostic_capture_feedback();
    diagnostic_record_queue();
    comp_v11_cpu_emit();
}
static bool diagnostic_output_safe(bool for_pairing)
{ return diagnostic_output_blockers(for_pairing)==0u; }
/* Service-port scene capture reads the committed controller-order bitmap.
 * No SPI reads, register changes, reset, full refresh or extra image buffer.
 * One UART row per foreground pass; every pass rechecks actual operation
 * guards. Capture is invalidated instead of stitching changing frames. */
typedef struct {
    uint32_t id, revision, crc, activation;
    uint16_t row;
    uint8_t reply;
    bool hold_reply, dumping;
    uint8_t sound_reply;
} panel_debug_uart_t;

static void panel_debug_status(void)
{
    char line[256];
    const comp_ssd1681_wba_t *p=&companion_v11.panel;
    (void)snprintf(line,sizeof(line),
        "EPDDBG STATUS uptime_ms=%lu surface=%u rev=%lu hold=%u driver=%u stage=%u op=%u ram_phase=%u busy=%u blocks=%08lx speaker=%u pending=%u submitted=%lu completed=%lu\r\n",
        (unsigned long)HAL_GetTick(),(unsigned)companion_app.runtime.visible_surface,
        (unsigned long)companion_app.runtime.visible_revision,
        (unsigned)(companion_app.panel_debug_hold_until_ms!=0u),
        (unsigned)p->status,(unsigned)p->stage,(unsigned)p->operation,
        (unsigned)p->recording_phase,(unsigned)comp_v11_hal_panel_busy(),
        (unsigned long)companion_v11.power.blockers,
        (unsigned)companion_v11.speaker.state,(unsigned)companion_v11.speaker.tx_pending,
        (unsigned long)companion_v11.speaker.submitted_blocks,
        (unsigned long)companion_v11.speaker.completed_blocks);
    comp_v11_hal_log(line);
}

static void panel_debug_pins(void)
{
    char line[256],uid[25];
    const uint32_t words[3]={HAL_GetUIDw0(),HAL_GetUIDw1(),HAL_GetUIDw2()};
    static const char hex[]="0123456789abcdef";
    for(unsigned word=0;word<3u;++word) for(unsigned byte=0;byte<4u;++byte) {
        const uint8_t value=(uint8_t)(words[word]>>(byte*8u));
        const unsigned offset=(word*4u+byte)*2u;
        uid[offset]=hex[value>>4u];uid[offset+1u]=hex[value&15u];
    }
    uid[24]='\0';
    /* One read of each register; no pin reconfiguration, latch clear, SPI,
     * reset or power action. Current digital input is distinct from EXTI. */
    const uint32_t mode=GPIOA->MODER,pull=GPIOA->PUPDR,input=GPIOA->IDR;
    const uint32_t bmode=GPIOB->MODER,binput=GPIOB->IDR;
    const int count=snprintf(line,sizeof(line),
        "EPDDBG PINS fw=%08lx uid=%s uptime_ms=%lu busy=%u mode=%u pull=%u af=%u clk=%u exti_port=%u dc_mode=%u dc_level=%u cs_mode=%u cs_level=%u driver=%u stage=%u calls=%lu\r\n",
        (unsigned long)COMPANION_WBA_APP_VERSION,uid,(unsigned long)HAL_GetTick(),
        (unsigned)((input>>12u)&1u),(unsigned)((mode>>24u)&3u),(unsigned)((pull>>24u)&3u),
        (unsigned)((GPIOA->AFR[1]>>16u)&15u),(unsigned)((RCC->AHB2ENR&RCC_AHB2ENR_GPIOAEN)!=0u),
        (unsigned)(EXTI->EXTICR[3]&15u),(unsigned)((mode>>22u)&3u),(unsigned)((input>>11u)&1u),
        (unsigned)(bmode&3u),(unsigned)(binput&1u),(unsigned)companion_v11.panel.status,
        (unsigned)companion_v11.panel.stage,(unsigned long)companion_v11.panel.stats.transfer_calls);
    if(count>0 && (size_t)count<sizeof(line))comp_v11_hal_log(line);
    else comp_v11_hal_log("EPDDBG PINS REJECTED output_length\r\n");
}

static void panel_debug_service(panel_debug_uart_t *d,comp_v11_diag_panel_command_t command)
{
    uint32_t tick=HAL_GetTick();
    bool service_safe=diagnostic_output_safe(true);
    bool stable=service_safe && diagnostic_output_safe(false) &&
        companion_app.presenter.status==COMP_SCREEN_PRESENTER_WBA_IDLE;
    char line[256];
    const uint8_t sound_cue=comp_v11_diag_sound_cue(command);
    if(sound_cue!=255u) {
        if(d->sound_reply)return;
        /* Consume once; no delayed cue after recording/OTA becomes idle.
         * Uses the installed generator and current user's sound settings. */
        const bool allowed=service_safe && !d->dumping && !d->sound_reply &&
            companion_v11.speaker_ready && !companion_app.runtime.audio.quiet &&
            !comp_audio_feedback_busy(&companion_app.runtime.audio) &&
            companion_v11.speaker.volume_percent>0u && !companion_v11.speaker.muted;
        d->sound_reply=allowed && comp_v11_hal_speaker_diagnostic_arm(&companion_v11) &&
            comp_speaker_play_cue(&companion_v11.speaker,
            (comp_speaker_cue_t)sound_cue)==COMP_SPEAKER_OK?1u:2u;
        return; /* Never print UART while starting/playing the sound. */
    }
    if(d->sound_reply && service_safe && !comp_speaker_active(&companion_v11.speaker)) {
        const char *reply=d->sound_reply==1u && companion_v11.speaker.last_error==COMP_SPEAKER_OK?
            "SOUND1 COMPLETE\r\n":"SOUND1 FAILED\r\n";
        d->sound_reply=0u;comp_v11_hal_log(reply);
        comp_v11_hal_speaker_diagnostic_report(&companion_v11);
        panel_debug_status();return;
    }
    if(!COMPANION_WBA_SCREEN_ENABLED)return;
    if(command!=COMP_V11_DIAG_PANEL_NONE) {
        if(command==COMP_V11_DIAG_PANEL_RUN) {
            companion_app.panel_debug_hold_until_ms=0u;
            (void)comp_v11_product_panel_debug_key(&companion_app,false,tick);
            companion_app.panel_debug_replay_reply=0u;
            d->dumping=false;d->hold_reply=false;d->reply=1u;
        } else if(!service_safe) {
            d->reply=2u;
        } else if(command==COMP_V11_DIAG_PANEL_HOLD) {
            companion_app.panel_debug_hold_until_ms=tick+30000u;
            d->dumping=false;d->hold_reply=true;
        } else if(command==COMP_V11_DIAG_PANEL_TRACE) {
            companion_app.panel_debug_trace_until_ms=tick+30000u;d->reply=3u;
        } else if(command==COMP_V11_DIAG_PANEL_STATUS) {
            panel_debug_status();return;
        } else if(command==COMP_V11_DIAG_PANEL_PINS) {
            /* UART output must not delay a currently sampled startup/update.
             * A failed driver can still report the live pin configuration. */
            if(companion_v11.panel.status==COMP_SSD1681_WBA_ACTIVE) d->reply=2u;
            else { panel_debug_pins();return; }
        } else if(command==COMP_V11_DIAG_PANEL_KEY) {
            if(d->dumping || !comp_v11_product_panel_debug_key(&companion_app,true,tick)) d->reply=2u;
        } else if(command==COMP_V11_DIAG_PANEL_SAME) {
            if(d->dumping || !comp_v11_product_panel_debug_same(&companion_app,tick)) d->reply=2u;
        } else if(command==COMP_V11_DIAG_PANEL_BASE) {
            if(d->dumping || !comp_v11_product_panel_debug_base(&companion_app,tick)) d->reply=2u;
        } else if(command==COMP_V11_DIAG_PANEL_CATCH) {
            if(d->dumping || !comp_v11_product_panel_debug_catch(&companion_app,tick)) d->reply=2u;
        } else if(command==COMP_V11_DIAG_PANEL_SNAP) {
            if(!stable || companion_app.panel_debug_hold_until_ms==0u ||
                !companion_app.presenter.committed_valid) d->reply=4u;
            else {
                d->id++;d->revision=companion_app.runtime.visible_revision;
                d->activation=companion_v11.panel.stats.visible_activation_count;
                d->crc=comp_v11_product_committed_crc(&companion_app);
                d->row=0u;d->dumping=true;
                (void)snprintf(line,sizeof(line),
                    "EPDDBG FRAME BEGIN id=%lu fw=%08lx rev=%lu activation=%lu width=200 height=200 stride=25 order=controller_flip_y crc32=%08lx uptime_ms=%lu\r\n",
                    (unsigned long)d->id,(unsigned long)COMPANION_WBA_APP_VERSION,
                    (unsigned long)d->revision,(unsigned long)d->activation,
                    (unsigned long)d->crc,(unsigned long)tick);
                comp_v11_hal_log(line);return;
            }
        }
    }
    if(d->dumping && (!service_safe || companion_app.panel_debug_hold_until_ms==0u)) {
        d->dumping=false;d->reply=5u;
    }
    if(d->hold_reply && companion_app.panel_debug_hold_until_ms==0u) {
        d->hold_reply=false;d->reply=5u;
    }
    if(!service_safe)return;
    if (companion_app.panel_debug_catch_reply!=0u) {
        static const char *const replies[]={"", "ARMED window_ms=30000", "COMPLETE observe_ms=30000", "EXPIRED no_refresh=1", "CANCELLED product_operation", "FAILED no_retry=1"};
        uint8_t reply=companion_app.panel_debug_catch_reply;
        companion_app.panel_debug_catch_reply=0u;
        if (reply==2u && (!stable || companion_app.panel_debug_hold_until_ms==0u ||
            (int32_t)(tick-companion_app.panel_debug_hold_until_ms)>=0 ||
            !companion_app.presenter.committed_valid ||
            companion_app.runtime.surface!=COMP_SCREEN_SURFACE_HOME ||
            companion_app.runtime.visible_surface!=COMP_SCREEN_SURFACE_HOME))
            reply=4u; /* Do not emit a delayed COMPLETE after losing the freeze. */
        if(reply<sizeof(replies)/sizeof(replies[0])) {
            (void)snprintf(line,sizeof(line),
                "EPDDBG CATCH %s uptime_ms=%lu activation=%lu full_count=%lu failures=%lu hold_until_ms=%lu\r\n",
                replies[reply],(unsigned long)tick,
                (unsigned long)companion_v11.panel.stats.visible_activation_count,
                (unsigned long)companion_v11.panel.stats.completed_full,
                (unsigned long)companion_app.presenter.stats.failed_completions,
                (unsigned long)companion_app.panel_debug_hold_until_ms);
            comp_v11_hal_log(line);return;
        }
    }
    if (companion_app.panel_debug_replay_reply!=0u) {
        static const char *const replay_replies[]={"", "ARMED window_ms=120000", "QUEUED", "STARTED configured_full_same_image=1", "COMPLETE observe_ms=12000", "FAILED no_retry=1", "EXPIRED", "CANCELLED product_operation"};
        uint8_t reply=companion_app.panel_debug_replay_reply;
        companion_app.panel_debug_replay_reply=0u;
        if(reply<sizeof(replay_replies)/sizeof(replay_replies[0])) {
            const uint8_t mode=companion_app.panel_debug_same_partial;
            const bool same=mode==1u;
            const char *description=replay_replies[reply];
            if(reply==3u)description=same?"STARTED baseline=FF_same_image":
                mode==0u?"STARTED vendor_quick_full=1":
                mode==3u?"STARTED flashing_full=1":description;
            if((mode==0u || mode==3u) && reply==4u)description="COMPLETE observe_ms=0";
            (void)snprintf(line,sizeof(line),
                "EPDDBG %s %s id=%lu uptime_ms=%lu activation=%lu last_visible_ms=%lu hold_until_ms=%lu\r\n",
                same?"SAME":mode==2u?"BASE":mode==3u?"FLASH":"KEY",description,
                (unsigned long)companion_app.panel_debug_replay_id,
                (unsigned long)tick,(unsigned long)companion_v11.panel.stats.visible_activation_count,
                (unsigned long)companion_v11.panel.stats.last_visible_completed_ms,
                (unsigned long)companion_app.panel_debug_hold_until_ms);
            comp_v11_hal_log(line);return;
        }
    }
    if(d->reply!=0u) {
        static const char *const replies[]={"", "RUN", "REJECTED busy", "TRACE window_ms=30000", "REJECTED need_stable_hold", "FRAME ABORT reason=operation_or_hold_changed"};
        (void)snprintf(line,sizeof(line),"EPDDBG %s\r\n",replies[d->reply]);
        d->reply=0u;comp_v11_hal_log(line);return;
    }
    if(d->hold_reply && stable) {
        d->hold_reply=false;
        (void)snprintf(line,sizeof(line),"EPDDBG HOLD ready=1 until_ms=%lu activation=%lu rev=%lu\r\n",
            (unsigned long)companion_app.panel_debug_hold_until_ms,
            (unsigned long)companion_v11.panel.stats.visible_activation_count,
            (unsigned long)companion_app.runtime.visible_revision);
        comp_v11_hal_log(line);return;
    }
    if(!d->dumping)return;
    if(!stable || companion_app.panel_debug_hold_until_ms==0u ||
       !companion_app.presenter.committed_valid ||
       d->revision!=companion_app.runtime.visible_revision ||
       d->activation!=companion_v11.panel.stats.visible_activation_count) {
        d->dumping=false;
        (void)snprintf(line,sizeof(line),"EPDDBG FRAME ABORT id=%lu reason=scene_changed_or_busy\r\n",(unsigned long)d->id);
        comp_v11_hal_log(line);return;
    }
    if(d->row<200u) {
        static const char hex[]="0123456789abcdef";
        int n=snprintf(line,sizeof(line),"EPDDBG ROW id=%lu y=%u data=",(unsigned long)d->id,(unsigned)d->row);
        uint8_t row[25];
        if(!comp_v11_product_committed_read(&companion_app,(size_t)d->row*25u,row,sizeof(row))) {
            d->dumping=false;comp_v11_hal_log("EPDDBG FRAME ABORT reason=old_frame_read\r\n");return;
        }
        for(uint8_t i=0u;i<25u;++i) {line[n++]=hex[row[i]>>4u];line[n++]=hex[row[i]&15u];}
        line[n++]='\r';line[n++]='\n';line[n]='\0';
        comp_v11_hal_log(line);d->row++;return;
    }
    uint32_t crc=comp_v11_product_committed_crc(&companion_app);
    (void)snprintf(line,sizeof(line),"EPDDBG FRAME %s id=%lu rows=200 crc32=%08lx\r\n",
        crc==d->crc?"END":"ABORT",(unsigned long)d->id,(unsigned long)crc);
    d->dumping=false;comp_v11_hal_log(line);
}

#if COMPANION_WBA_CPU_RESIDENCE_PROFILE
__attribute__((noinline,noclone,optimize("Os"))) static uint32_t crc_reference_bits(uint32_t seed,const uint8_t *data,size_t n)
{
    uint32_t crc=seed^UINT32_MAX;
    for(size_t i=0;i<n;++i){crc^=data[i];for(unsigned bit=0;bit<8u;++bit)crc=(crc>>1u)^((crc&1u)?UINT32_C(0xEDB88320):0u);}
    return crc^UINT32_MAX;
}
__attribute__((noinline,noclone,optimize("Os"))) static uint32_t crc_fast_profile(uint32_t seed,const uint8_t *data,size_t n)
{return companion_crc32(seed,data,n);}
static void crc_idle_reference_once(void)
{
    static bool done;
    if(done || !COMPANION_WBA_SCREEN_ENABLED || companion_v11.microphone.running)return;
    done=true;
    const uint8_t *frame=companion_app.panel_staging;
    uint32_t old_crc=0u,new_crc=0u,t=HAL_GetTick();
    for(unsigned i=0;i<4u;++i)old_crc=crc_reference_bits(old_crc,frame,5000u);
    uint32_t old_ms=HAL_GetTick()-t;t=HAL_GetTick();
    for(unsigned i=0;i<4u;++i)new_crc=crc_fast_profile(new_crc,frame,5000u);
    uint32_t new_ms=HAL_GetTick()-t;
    char line[160];(void)snprintf(line,sizeof(line),
        "RCRC1 idle_only=1 bytes=5000 repeats=4 old_ms=%lu fast_ms=%lu equal=%u tick_us=1000\r\n",
        (unsigned long)old_ms,(unsigned long)new_ms,(unsigned)(old_crc==new_crc));
    (void)comp_v11_hal_debug_write(line);
}
#endif
static void diagnostic_emit_body(comp_v11_diag_console_t *console,uint32_t reset_flags,uint8_t boot_route,
                            bool ble_initialized,comp_v11_diag_reason_t reason,bool battery_only)
{
#if COMPANION_WBA_CPU_RESIDENCE_PROFILE
    if(reason==COMP_V11_DIAG_QUERY)crc_idle_reference_once();
#endif
    uint32_t tick=HAL_GetTick();
    uint32_t uid_words[3]={HAL_GetUIDw0(),HAL_GetUIDw1(),HAL_GetUIDw2()};
    comp_v11_diag_snapshot_t s={0};
    comp_v11_microphone_stats_t mic={0};
    comp_wba_power_snapshot_t power=comp_wba_power_monitor_snapshot(&companion_v11.power_monitor,tick);
    comp_v11_microphone_hal_get_stats(&companion_v11.microphone,&mic);
    const comp_v11_memory_stats_t *memory_stats=comp_v11_memory_observe();
    s.firmware_version=COMPANION_WBA_APP_VERSION;s.build_id=COMPANION_WBA_BUILD_ID;
    s.board_id=COMPANION_WBA_BOARD_ID;s.uptime_ms=tick;
    for(unsigned word=0;word<3u;++word)
        for(unsigned byte=0;byte<4u;++byte)
            s.uid[word*4u+byte]=(uint8_t)(uid_words[word]>>(byte*8u));
    s.ui_generation=companion_app.assets_ready?companion_app.resources.generation.root.generation:0u;
    s.reset_flags=reset_flags;s.iwdg_reset=(reset_flags&RCC_RESET_FLAG_IWDG)!=0u;
    s.faults=companion_v11.faults;
    s.ram_gap=memory_stats->static_gap_bytes;s.stack_min_free=memory_stats->stack.minimum_free_bytes;
    s.stack_low=memory_stats->stack.low_latched;s.stack_guard=memory_stats->stack.guard_failed;
    /* Configured protocol is distinct from rendered/failed BUSY-qualified
     * completions below, and does not imply a hardware RESET endpoint. */
    s.panel_bound=companion_v11.panel.status!=COMP_SSD1681_WBA_NOT_READY;
    s.assets_ready=companion_app.assets_ready;
    s.panel_status=(uint8_t)companion_v11.panel.status;s.panel_error=(uint8_t)companion_v11.panel.error;
    s.presenter_status=(uint8_t)companion_app.presenter.status;
    s.panel_rendered=companion_app.presenter.stats.visible_completions;
    s.panel_failed=companion_app.presenter.stats.failed_completions;
    s.panel_stage=companion_v11.panel.stage;s.panel_busy=comp_v11_hal_panel_busy();
    s.panel_transfer_calls=companion_v11.panel.stats.transfer_calls;
    s.panel_busy_timeouts=companion_v11.panel.stats.busy_timeouts;
    s.nor_jedec=companion_v11.nor.info.jedec_id;s.nor_size=companion_v11.nor.info.size_bytes;
    s.nor_suspend_qualified=companion_v11.nor.erase_suspend_supported;
    s.nor_erase_active=companion_v11.nor.erase_active;
    s.nor_erase_suspended=companion_spi_nor_stm32wba_erase_is_suspended(&companion_v11.nor);
    s.nor_suspend_wait_ms=companion_v11.nor.suspend_wait_ms;
    s.nor_resume_guard_ms=companion_v11.nor.resume_guard_ms;
    s.nor_sfdp_dw12=companion_v11.nor.info.sfdp_suspend_parameters;
    s.nor_sfdp_dw13=companion_v11.nor.info.sfdp_suspend_instructions;
    s.nor_sfdp_bfp_dwords=companion_v11.nor.info.sfdp_bfp_dwords;
    s.storage_layout_ready=companion_app.storage_layout_ready;s.recording_ready=companion_app.recording_ready;
    s.recording_state=comp_wba_recording_product_state(&companion_app.recording);
    s.recording_fault=companion_app.recording.last_fault;
    s.recording_committed=companion_app.recording.media_ready?companion_app.recording.capture.engine.stats.durable_bytes:0u;
    s.microphone_initialized=mic.initialized;s.microphone_running=mic.running;
    s.microphone_hal_error=mic.last_hal_error;s.microphone_error_irqs=mic.error_irqs;
    s.microphone_stale=mic.stale_dma_halves;s.microphone_overflows=mic.event_queue_overflows;
    s.microphone_rejections=mic.processing_rejections;s.microphone_frames=mic.processed_dma_halves;
    s.capture_deadline_faults=companion_app.capture_deadline_faults;
    s.capture_foreground_ms=companion_app.max_capture_foreground_ms;
    s.capture_hal_ms=companion_app.max_capture_hal_ms;s.capture_recorder_ms=companion_app.max_capture_recorder_ms;
    s.capture_ble_ms=companion_app.max_capture_ble_ms;s.capture_runtime_ms=companion_app.max_capture_runtime_ms;
    s.capture_presenter_ms=companion_app.max_capture_presenter_ms;s.capture_render_ms=companion_app.max_capture_render_ms;
    s.microphone_poll_ms=companion_v11.microphone_max_poll_ms;
    const comp_duration_stats_t *pdm=&companion_v11.microphone.pdm_duration;
    s.timing_microphone_starts=mic.starts;
    if(companion_app.recording.media_ready) {
        const comp_duration_stats_t *encode=&companion_app.recording.capture.engine.stats.encoding_duration;
        s.timing_recording_id=companion_app.recording.capture.engine.active.descriptor.recording_id;
        s.encode_timing_samples=encode->samples;
        s.encode_timing_valid=comp_duration_stats_percentile_upper_ms(encode,95u,&s.encode_p95_upper_ms);
        (void)comp_duration_stats_peak_upper_ms(encode,&s.encode_peak_upper_ms);
    }
    s.pdm_timing_samples=pdm->samples;
    s.pdm_timing_valid=comp_duration_stats_percentile_upper_ms(pdm,95u,&s.pdm_p95_upper_ms);
    (void)comp_duration_stats_peak_upper_ms(pdm,&s.pdm_peak_upper_ms);
    s.speaker_ready=companion_v11.speaker_ready;
#ifdef COMPANION_WBA_BLE_LINKED
    s.ble_compiled=true;s.ble_initialized=ble_initialized;s.ble_host_ready=comp_v11_ble_host_ready();
    s.ble_host_error=comp_v11_ble_host_error();s.ble_connection=comp_v11_ble_connection();
    s.ble_linked=comp_v11_ble_linked();s.ble_secured=comp_v11_ble_secured();
    s.ble_fatal=comp_v11_ble_fatal_error();
    const comp_v11_ble_security_stats_t *security=comp_v11_ble_security_stats();
    s.ble_bond_lost=security->bond_lost_events;s.ble_rebond_attempts=security->rebond_attempts;
    s.ble_pairing_status=security->pairing_status;s.ble_pairing_reason=security->pairing_reason;
#else
    (void)ble_initialized;
    s.ble_connection=0xFFFFu;
#endif
    s.battery_adc_enabled=companion_v11.power_monitor.sampling_enabled;
    const comp_v11_battery_adc_stats_t *adc=comp_v11_battery_adc_stats();
    const comp_wba_power_profile_t *profile=&companion_v11.power_monitor.profile;
    s.battery_reference_raw=adc->reference_raw;s.battery_factory_raw=adc->factory_raw;
    s.battery_reference_mv=adc->reference_mv;s.battery_reference_valid=adc->reference_valid;
    s.battery_reference_age_ms=adc->reference_valid?tick-adc->reference_ms:UINT32_MAX;
    s.battery_reference_samples=adc->reference_measurements;s.battery_adc_failures=adc->failures;
    s.battery_adc_raw=adc->battery_raw;s.battery_adc_samples=adc->battery_measurements;
    s.battery_reference_min_mv=adc->reference_min_mv;
    s.battery_reference_max_mv=adc->reference_max_mv;
    s.battery_adc_error=adc->error;
    s.battery_raw_mode=companion_v11.power_monitor.raw_diagnostic;
    s.battery_sample_age_ms=adc->battery_measurements?tick-adc->battery_ms:UINT32_MAX;
    s.battery_input_valid=adc->battery_input_valid && s.battery_sample_age_ms<15000u;
    s.battery_input_mv=s.battery_input_valid?adc->battery_input_mv:0u;
    s.battery_saturated=adc->battery_saturated && s.battery_sample_age_ms<15000u;
    s.battery_divider_safe=comp_v11_battery_divider_safe(profile->top_ohm,profile->bottom_ohm,
        profile->reference_min_mv,profile->maximum_battery_mv);
    s.battery_divider_verified=profile->divider_verified;s.battery_reference_verified=profile->reference_verified;
    s.battery_top_ohm=profile->top_ohm;s.battery_bottom_ohm=profile->bottom_ohm;
    s.battery_maximum_mv=profile->maximum_battery_mv;
    s.battery_reference_floor_mv=profile->reference_min_mv;
    s.charger_pullups_verified=profile->charger_pullups_verified;
    s.battery_soc_curve_verified=profile->soc_point_count>=2u;
    s.battery_sample_errors=companion_v11.power_monitor.sample_errors;
    s.battery_gate_errors=companion_v11.power_monitor.gate_errors;
    s.voltage_valid=power.voltage_valid;s.percent_valid=power.percent_valid;
    s.charger_valid=power.charger_valid;s.charger_present=power.charger_present;
    s.battery_mv=power.millivolts;s.battery_percent=power.percent;s.charge_state=power.charge_state;
    s.ota_power_blockers=comp_wba_power_monitor_ota_blockers(&companion_v11.power_monitor,tick);
    s.sleep_blockers=companion_v11.power.blockers;
    if(battery_only) {
        comp_v11_diag_console_emit_battery(&s,diagnostic_write,NULL);
        return;
    }
    comp_v11_diag_console_emit(console,&s,reason,diagnostic_write,NULL);
    const comp_v11_capture_hal_timing_t *hal=comp_v11_hal_capture_timing();
    char timing_line[224];
    (void)snprintf(timing_line,sizeof(timing_line),"BOOT4 schema=1 route=%u\r\n",(unsigned)boot_route);
    (void)diagnostic_write(NULL,timing_line);
    (void)snprintf(timing_line,sizeof(timing_line),
        "HALCAP schema=1 calls=%lu total_ms=%lu speaker=%lu pdm=%lu panel=%lu imu=%lu touch=%lu inputs=%lu power=%lu statuses=%lu\r\n",
        (unsigned long)hal->calls,(unsigned long)hal->peak_total_ms,
        (unsigned long)hal->worst_ms[0],(unsigned long)hal->worst_ms[1],
        (unsigned long)hal->worst_ms[2],(unsigned long)hal->worst_ms[3],
        (unsigned long)hal->worst_ms[4],(unsigned long)hal->worst_ms[5],
        (unsigned long)hal->worst_ms[6],(unsigned long)hal->worst_ms[7]);
    (void)diagnostic_write(NULL,timing_line);
    (void)snprintf(timing_line,sizeof(timing_line),"PDM3 output=%u processed_mask=%u inactive_stats=unavailable\r\n",
        (unsigned)companion_v11.microphone.processing.config.output,
        (unsigned)comp_wba_pdm_capture_channel_mask(&companion_v11.microphone.processing));
    (void)diagnostic_write(NULL,timing_line);
    comp_v11_hal_dual_mic_report(&companion_v11,companion_app.runtime.record_token);
    const comp_runtime_t *rctl=&companion_app.runtime;
    (void)snprintf(timing_line,sizeof(timing_line),
        "RCTL1 schema=1 token=%lu state=%u stop_reason=%u result=%u prepare=%u prepare_ms=%lu pipeline=%u core=%u stop_requested=%u\r\n",
        (unsigned long)rctl->record_token,(unsigned)rctl->recording,
        (unsigned)rctl->record_stop_reason,(unsigned)rctl->last_result,(unsigned)rctl->prepare_pending,
        (unsigned long)rctl->prepare_since_ms,(unsigned)companion_app.recording.pipeline.state,
        companion_app.recording.media_ready?(unsigned)companion_app.recording.capture.engine.state:0u,
        (unsigned)companion_app.recording.pipeline.stop_requested);
    (void)diagnostic_write(NULL,timing_line);
#if defined(COMPANION_WBA_CODEC_PROFILE) && COMPANION_WBA_CODEC_PROFILE
    const companion_codec_profile_t *codec=companion_codec_profile_get();
    (void)snprintf(timing_line,sizeof(timing_line),
        "CODEC1 calls=%lu invalid=%lu clock_fallbacks=%lu total_hi=%lu total_lo=%lu peak_us=%lu\r\n",
        (unsigned long)codec->calls,(unsigned long)codec->invalid,(unsigned long)codec->clock_fallbacks,
        (unsigned long)(codec->total_us>>32u),(unsigned long)codec->total_us,(unsigned long)codec->peak_total_us);
    (void)diagnostic_write(NULL,timing_line);
    for(unsigned phase=0;phase<COMP_CODEC_PHASES;++phase) {
        (void)snprintf(timing_line,sizeof(timing_line),
            "CODEC1 phase=%u total_hi=%lu total_lo=%lu peak_us=%lu worst_us=%lu\r\n",phase,
            (unsigned long)(codec->phase_total_us[phase]>>32u),(unsigned long)codec->phase_total_us[phase],(unsigned long)codec->phase_peak_us[phase],
            (unsigned long)codec->worst_us[phase]);
        (void)diagnostic_write(NULL,timing_line);
    }
#if defined(COMPANION_OPUS_FAST_MEMORY) && COMPANION_OPUS_FAST_MEMORY
    const companion_opus_memory_count_t *memory_ops=companion_opus_memory_counts();
    for(unsigned kind=0;kind<3u;++kind) {
        (void)snprintf(timing_line,sizeof(timing_line),
            "OPMEM kind=%u calls_hi=%lu calls_lo=%lu bytes_hi=%lu bytes_lo=%lu\r\n",kind,
            (unsigned long)(memory_ops[kind].calls>>32u),(unsigned long)memory_ops[kind].calls,
            (unsigned long)(memory_ops[kind].bytes>>32u),(unsigned long)memory_ops[kind].bytes);
        (void)diagnostic_write(NULL,timing_line);
    }
#endif

#endif

#ifdef COMPANION_WBA_BLE_LINKED
    {
        char line[192];
        const comp_v11_update_diagnostics_t *d=comp_v11_update_product_diagnostics();
        (void)snprintf(line,sizeof(line),
            "OTA3 manifest_attempts=%lu manifest_stage=%lu pka_failure_stage=%lu pka_failure_status=%lu pka_failure_error=%lu pka_failures=%lu\r\n",
            (unsigned long)d->manifest_attempts,(unsigned long)d->manifest_stage,
            (unsigned long)d->pka_failure_stage,(unsigned long)d->pka_failure_status,
            (unsigned long)d->pka_failure_error,(unsigned long)d->pka_failures);
        (void)diagnostic_write(NULL,line);
    }
#endif
    if(companion_app.recording.media_ready) {
        char line[80];
        (void)snprintf(line,sizeof(line),"CODEC1 last_encode_error=%d\r\n",
            (int)companion_app.recording.capture.engine.codec.last_encode_error);
        (void)diagnostic_write(NULL,line);
    }
    diagnostic_capture_feedback();
    diagnostic_record_queue();
    comp_v11_cpu_emit();
    diagnostic_swd_pins();
    {
        char line[160];
        const comp_runtime_t *r=&companion_app.runtime;
        /* Source is recorded by the accepted input path at the transition;
         * generic callers remain explicitly unknown, never guessed from GPIO. */
        (void)snprintf(line,sizeof(line),
            "UI2 wakes=%lu source=%u wake_ms=%lu motion_flags=%u motion_ms=%lu orientation=%u\r\n",
            (unsigned long)r->wake_count,(unsigned)r->last_wake_source,
            (unsigned long)r->last_wake_ms,(unsigned)companion_v11.motion_event_flags,
            (unsigned long)companion_v11.motion_event_ms,(unsigned)companion_v11.motion.orientation);
        (void)diagnostic_write(NULL,line);
        /* Use the already-acquired sample, never a diagnostic SPI read. Axis
         * mapping can be established without trusting a frozen picture. */
        const comp_imu_sample_t *imu=&companion_v11.imu_sample;
        (void)snprintf(line,sizeof(line),
            "IMU2 ms=%lu age_ms=%lu n=%lu ax=%d ay=%d az=%d tilt=%u axes=%02x carry=%u movement_ms=%u\r\n",
            (unsigned long)imu->timestamp_ms,
            (unsigned long)(companion_v11.imu.samples?HAL_GetTick()-imu->timestamp_ms:0xffffffffu),
            (unsigned long)companion_v11.imu.samples,
            (int)imu->accel_mg[0],(int)imu->accel_mg[1],(int)imu->accel_mg[2],
            (unsigned)companion_v11.motion.tilt,(unsigned)companion_v11.motion.screen_axes,
            (unsigned)companion_v11.motion.carried,(unsigned)companion_v11.motion.movement_ms);
        (void)diagnostic_write(NULL,line);
    }
    {
        char line[256];
        const comp_runtime_t *r=&companion_app.runtime;
        uint32_t ink_pixels=0u;
        const bool committed=companion_app.presenter.committed_surface_valid;
        /* Read only the last BUSY-qualified committed framebuffer. This
         * observes intent/retained ink without SPI reads or synthetic input;
         * diagnostic_output_safe already excludes audio and panel activity. */
        if(committed)for(unsigned at=0u;at<5000u;at+=25u) {
            uint8_t row[25];
            if(!comp_v11_product_committed_read(&companion_app,at,row,sizeof(row)))break;
            for(unsigned i=0u;i<sizeof(row);++i) {
                uint8_t ink=(uint8_t)~row[i];
                ink=(uint8_t)((ink&0x55u)+((ink>>1u)&0x55u));
                ink=(uint8_t)((ink&0x33u)+((ink>>2u)&0x33u));
                ink_pixels+=(uint32_t)((ink+(ink>>4u))&0x0Fu);
            }
        }
        (void)snprintf(line,sizeof(line),
            "UI1 surface=%u visible_surface=%u revision=%lu visible_revision=%lu outstanding=%u idle_ms=%lu idle_minutes=%u touch_contact=%u key_debounced=%u committed_valid=%u ink_pixels=%lu\r\n",
            (unsigned)r->surface,(unsigned)r->visible_surface,
            (unsigned long)r->revision,(unsigned long)r->visible_revision,
            (unsigned)r->frame_outstanding,(unsigned long)(tick-r->last_activity_ms),
            (unsigned)r->menu.browser.auto_sleep_minutes,(unsigned)r->touch_contact,
            (unsigned)companion_app.button.pressed,(unsigned)committed,
            (unsigned long)ink_pixels);
        (void)diagnostic_write(NULL,line);
        if(companion_app.board && !companion_app.board->microphone.running) {
            const comp_v11_battery_adc_stats_t *b=comp_v11_battery_adc_stats();
            const unsigned pct=(r->status_packed&(1u<<17)) && (r->status_packed>>24u)<=100u?
                r->status_packed>>24u:255u;
            (void)snprintf(line,sizeof(line),
                "BUI1 ui_pct=%u cell_mv=%u est=%u age_ms=%lu fill=%u hint_seen=%u hint_pending=%u hint_fail=%u\r\n",
                pct,(unsigned)r->battery_mv,
                (unsigned)(pct<=100u && (r->status_packed&COMP_SCREEN_STATUS_ESTIMATED_BATTERY)!=0u),
                (unsigned long)(b->battery_measurements?tick-b->battery_ms:UINT32_MAX),
                (unsigned)r->menu.browser.battery_fill,
                (unsigned)companion_app.preferences.values.pet_discovery_seen,
                (unsigned)r->pet_discovery_pending_save,(unsigned)r->pet_discovery_save_attempts);
            (void)diagnostic_write(NULL,line);
            if(r->surface==COMP_SCREEN_SURFACE_MENU) {
                (void)snprintf(line,sizeof(line),
                    "MUI1 view=%u page=%u visible_view=%u visible_page=%u pending=%u request_ctx=%u feedback_ctx=%u feedback=%u result=%u menu_result=%u effect=%u seen=%u\r\n",
                    (unsigned)r->menu.view,(unsigned)r->menu.home_page,
                    (unsigned)r->visible_menu_view,(unsigned)r->visible_menu_home_page,
                    (unsigned)r->menu_pending,(unsigned)r->menu_pending_context,
                    (unsigned)r->menu_feedback_context,(unsigned)r->menu_feedback,
                    (unsigned)r->last_result,(unsigned)r->last_result_from_menu,
                    (unsigned)r->menu_effect_result,(unsigned)r->menu_feedback_seen);
                (void)diagnostic_write(NULL,line);
            }
        }
    }
#if COMP_V11_PANEL_LOW_SLEW || COMP_V11_PANEL_PASSIVE_TRACE
    {
        char line[256];
        const uint32_t mode_a=GPIOA->MODER, mode_b=GPIOB->MODER;
        const uint32_t speed_a=GPIOA->OSPEEDR, speed_b=GPIOB->OSPEEDR;
        const uint32_t type_a=GPIOA->OTYPER, type_b=GPIOB->OTYPER;
        (void)snprintf(line,sizeof(line),
            "PANEL16 gpio low_slew=%u dc_mode=%u mosi_mode=%u cs_mode=%u sck_mode=%u dc_speed=%u mosi_speed=%u cs_speed=%u sck_speed=%u dc_od=%u mosi_od=%u cs_od=%u sck_od=%u\r\n",
            (unsigned)COMP_V11_PANEL_LOW_SLEW,
            (unsigned)((mode_a>>22u)&3u),(unsigned)((mode_a>>30u)&3u),
            (unsigned)(mode_b&3u),(unsigned)((mode_b>>8u)&3u),
            (unsigned)((speed_a>>22u)&3u),(unsigned)((speed_a>>30u)&3u),
            (unsigned)(speed_b&3u),(unsigned)((speed_b>>8u)&3u),
            (unsigned)((type_a>>11u)&1u),(unsigned)((type_a>>15u)&1u),
            (unsigned)(type_b&1u),(unsigned)((type_b>>4u)&1u));
        (void)diagnostic_write(NULL,line);
    }
#endif
    {
        char line[160];
        const comp_ssd1681_wba_stats_t *p=&companion_v11.panel.stats;
        (void)snprintf(line,sizeof(line),
            "PANEL17 mode2_recovery misses=%lu retries=%lu recovered=%lu last_retry_ms=%lu recovery_ms=%lu\r\n",
            (unsigned long)p->activation_start_misses,
            (unsigned long)p->activation_retries,
            (unsigned long)p->activation_recoveries,
            (unsigned long)companion_v11.panel.activation_gate_next_ms,
            (unsigned long)p->activation_recovery_last_ms);
        (void)diagnostic_write(NULL,line);
    }
    {
        char line[192];
        const comp_screen_presenter_wba_t *presenter=&companion_app.presenter;
        (void)snprintf(line,sizeof(line),
            "PANEL14 recovery_full started=%lu guard=%u held=%u min_ms=%u next_ms=%lu now=%lu\r\n",
            (unsigned long)presenter->stats.recovery_full_started,
            (unsigned)presenter->recovery_full_guard_armed,
            (unsigned)(presenter->status==COMP_SCREEN_PRESENTER_WBA_IDLE &&
                !comp_screen_presenter_wba_ready_for_frame(presenter,tick)),
            (unsigned)COMP_SCREEN_PRESENTER_WBA_RECOVERY_FULL_MIN_MS,
            (unsigned long)presenter->recovery_full_not_before_ms,
            (unsigned long)tick);
        (void)diagnostic_write(NULL,line);
    }
    (void)comp_v11_hal_touch_diagnostic(&companion_v11);
#ifdef COMPANION_WBA_BLE_LINKED
    comp_v11_ble_transport_diagnostic();
#endif
}
static void diagnostic_emit(comp_v11_diag_console_t *console,uint32_t reset_flags,uint8_t boot_route,
                            bool ble_initialized,comp_v11_diag_reason_t reason,bool battery_only)
{
    comp_v11_reset_witness_begin(1u);
    diagnostic_emit_body(console,reset_flags,boot_route,ble_initialized,reason,battery_only);
    if (!battery_only) {
        /* Cached evidence only, under the existing full-report safety gate.
         * Never print from a failing ADC/recording slice. */
        const comp_v11_battery_adc_stats_t *adc=comp_v11_battery_adc_stats();
        char line[128];
        (void)snprintf(line,sizeof(line),"ADCFAIL1 failures=%lu first_error=%u first_phase=%u current_error=%u\r\n",
            (unsigned long)adc->failures,(unsigned)adc->first_error,
            (unsigned)adc->first_phase,(unsigned)adc->error);
        (void)diagnostic_write(NULL,line);
        if (adc->timeout_valid) {
            (void)snprintf(line,sizeof(line),"ADCFAIL2 at_ms=%lu elapsed_ms=%lu service_gap_ms=%lu phase=%u ready=%u\r\n",
                (unsigned long)adc->timeout_at_ms,(unsigned long)adc->timeout_elapsed_ms,
                (unsigned long)adc->timeout_service_gap_ms,(unsigned)adc->timeout_phase,
                (unsigned)adc->timeout_ready);
            (void)diagnostic_write(NULL,line);
        }
    }
    comp_v11_reset_witness_end();
}
int main(void)
{
    uint32_t logged=0,reset_flags=RCC->CSR&RCC_RESET_FLAG_ALL;
    /* Read only, before clock/RTC setup can reset backup-domain contents.
     * Keep one byte in main's existing lifetime, not new static BSS. */
    const bool receipt_clock_was_enabled=__HAL_RCC_RTCAPB_IS_CLK_ENABLED();
    __HAL_RCC_RTCAPB_CLK_ENABLE();
    const comp_v11_reset_witness_t previous_reset=comp_v11_reset_witness_read();
#if COMP_V11_DIAG_FLASH_ENABLED
    const comp_diag_flash_data_t previous_journal=comp_v11_diag_flash_snapshot();
#endif
    const uint8_t boot_route=comp_v11_boot_receipt_read(&TAMP->BKP16R,
        *(const uint32_t *)(SCB->VTOR+4u));
    if(!receipt_clock_was_enabled)__HAL_RCC_RTCAPB_CLK_DISABLE();
    comp_v11_diag_console_t diagnostic;
    panel_debug_uart_t panel_debug={0};
    bool ble_initialized=false;
    bool pair_reply_pending=false, pair_window_opened=false;
    uint32_t pair_blockers=0u;
    uint32_t pair_battery_deadline=0u;
    uint8_t pair_menu_blockers=0u;
    _Static_assert(COMP_RUNTIME_BACKEND_FAILED<4u,"UART request result packing");
    uint8_t imu_reply=0u,record_reply=0u,reconnect_reply=0u;
    uint32_t record_reply_token=0u;
    __HAL_RCC_CLEAR_RESET_FLAGS();
    comp_v11_diag_console_init(&diagnostic);
    (void)comp_v11_hal_init(&companion_v11);
#ifdef COMPANION_WBA_BLE_LINKED
    /* Resident boot leaves its watchdog running through trial/normal boot. */
    LL_IWDG_ReloadCounter(IWDG);
#endif
    comp_v11_hal_log("BOOT1 phase=pre_storage\r\n");
    comp_v11_product_app_init(&companion_app,&companion_v11,NULL);
    comp_v11_hal_storage_init_complete();
    comp_v11_hal_log("BOOT1 phase=post_storage\r\n");
#if COMP_V11_DIAG_FLASH_ENABLED
    comp_v11_diag_flash_boot(&companion_v11,reset_flags,&previous_journal);
#endif
#ifdef COMPANION_WBA_BLE_LINKED
    comp_v11_hal_log("BOOT1 phase=pre_ble\r\n");
    ble_initialized=comp_v11_ble_init(&companion_app);
    comp_v11_low_power_init(&companion_app,ble_initialized);
#if COMP_V11_DIAG_FLASH_ENABLED
    if(ble_initialized)comp_v11_diag_flash_replay(&companion_v11);
#endif
#else
    comp_v11_low_power_init(&companion_app,false);
#endif
    comp_v11_reset_witness_emit(previous_reset,reset_flags);
    diagnostic_emit(&diagnostic,reset_flags,boot_route,ble_initialized,COMP_V11_DIAG_BOOT,false);
    for (;;) {
#ifdef COMPANION_WBA_BLE_LINKED
        LL_IWDG_ReloadCounter(IWDG);
#endif
        uint32_t tick=HAL_GetTick();
#if COMP_V11_DIAG_FLASH_ENABLED
        comp_v11_diag_flash_heartbeat(&companion_app,tick,0u);
#endif
        uint8_t byte;
        for(unsigned i=0;i<8u && comp_v11_hal_debug_read(&byte);++i) {
#if COMPANION_WBA_DUAL_PAIR_CAPTURE
            comp_v11_dual_pair_accept(byte);
#endif
            comp_v11_diag_console_accept(&diagnostic,byte);
        }
#if COMPANION_WBA_DUAL_PAIR_CAPTURE
        /* START uses the normal one-shot idle gate. Busy requests never queue
         * behind a recording/OTA. Later commands only affect this own lease. */
        comp_v11_dual_pair_command(&companion_app,diagnostic_output_safe(true)&&!panel_debug.dumping);
#endif
#if defined(COMPANION_WBA_BLE_LINKED) && defined(__arm__)
        uint8_t wall_previous=comp_v11_ota_gatt_wall_context(COMP_OTA_WALL_PRODUCT_OTHER);
#endif
        comp_cpu_stage_span_t bulk_product=comp_v11_cpu_transfer_stage_begin();
#if COMP_V11_DIAG_FLASH_ENABLED
        comp_v11_diag_flash_heartbeat(&companion_app,HAL_GetTick(),1u);
#endif
        comp_v11_product_app_poll(&companion_app);
#if COMP_V11_DIAG_FLASH_ENABLED
        comp_v11_diag_flash_heartbeat(&companion_app,HAL_GetTick(),2u);
#endif
        comp_v11_cpu_transfer_stage_end(COMP_BULK_CPU_PRODUCT,bulk_product);
#ifdef COMPANION_WBA_BLE_LINKED
        recording_gap_probe_poll();
#endif
#if defined(COMPANION_WBA_BLE_LINKED) && defined(__arm__)
        (void)comp_v11_ota_gatt_wall_context(wall_previous);
#endif
        /* Outside product_app: normal capture completion retires its CPU
         * owner inside that app, before this scope starts. START is still a
         * queued product request; an inactive/old span cannot own a new token.
         * Preserve all original diagnostic/control guards and work order. */
        comp_cpu_stage_span_t cpu_main_services=comp_cpu_detail_begin();
        panel_debug_service(&panel_debug,comp_v11_diag_console_take_panel(&diagnostic));
        bool safe=diagnostic_output_safe(false) && !panel_debug.dumping;
        bool pairing_safe=diagnostic_output_safe(true);
        comp_v11_diag_record_command_t record_command=comp_v11_diag_console_take_record(&diagnostic);
        if(record_command!=COMP_V11_DIAG_RECORD_NONE) {
            /* Local wired service uses the real product runtime/encoder/NOR.
             * START is never queued behind another owner. STOP must remain
             * available during capture, preparation, draining or maintenance.
             * Store only the latest request outcome, not a command queue.
             * Blocking UART formatting/transmit waits until audio/transfer idle. */
            comp_runtime_result_t result=COMP_RUNTIME_BUSY;
#if defined(COMPANION_WBA_BLE_LINKED) && COMPANION_WBA_EXPERIMENTAL_STOP1
            if(record_command==COMP_V11_DIAG_RECORD_STOP1_ONCE) {
                result=pairing_safe&&!panel_debug.dumping&&comp_v11_low_power_arm_once(&companion_app)?
                    COMP_RUNTIME_OK:COMP_RUNTIME_BUSY;
            } else if(record_command==COMP_V11_DIAG_RECORD_STOP1_WINDOW) {
                result=pairing_safe&&!panel_debug.dumping&&comp_v11_low_power_arm_window(&companion_app)?
                    COMP_RUNTIME_OK:COMP_RUNTIME_BUSY;
            } else
#endif
            if(record_command==COMP_V11_DIAG_RECORD_CACHE_OFF_NEXT) {
                result=pairing_safe&&!panel_debug.dumping&&comp_v11_cpu_arm_cache_off_trial()?COMP_RUNTIME_OK:COMP_RUNTIME_BUSY;
            } else if(record_command==COMP_V11_DIAG_RECORD_RECOVER) {
                /* This narrow stopped-fault admission does not enable START,
                 * pairing or general control through the storage blocker. */
                result=!panel_debug.dumping&&diagnostic_fault_output_safe()&&
                    comp_v11_product_recording_recover(&companion_app)?COMP_RUNTIME_OK:COMP_RUNTIME_BUSY;
            } else if(record_command==COMP_V11_DIAG_RECORD_MARK) {
                uint32_t nonce=HAL_GetTick();if(!nonce)nonce=1u;
                result=comp_v11_product_recording_bookmark(&companion_app,companion_app.runtime.record_token,nonce)?
                    COMP_RUNTIME_OK:COMP_RUNTIME_BUSY; /* Accepted, not yet durable. */
            } else if(record_command==COMP_V11_DIAG_RECORD_PAUSE || record_command==COMP_V11_DIAG_RECORD_RESUME) {
                /* Bounded engine transition only. No formatting, display,
                 * microphone restart or new recording while audio is live. */
                result=comp_wba_recording_product_set_paused(&companion_app.recording,
                    companion_app.runtime.record_token,record_command==COMP_V11_DIAG_RECORD_PAUSE)?
                    COMP_RUNTIME_OK:COMP_RUNTIME_BUSY;
            } else if(record_command==COMP_V11_DIAG_RECORD_STOP || (pairing_safe && !panel_debug.dumping))
                result=comp_runtime_record(&companion_app.runtime,
                    record_command==COMP_V11_DIAG_RECORD_START,HAL_GetTick());
            record_reply=(uint8_t)((unsigned)record_command*4u+(unsigned)result);
            record_reply_token=companion_app.runtime.record_token;
            /* The accepted request may have changed audio/ownership guards. */
            safe=diagnostic_output_safe(false) && !panel_debug.dumping;
            pairing_safe=diagnostic_output_safe(true);
        }
        if(record_reply && !panel_debug.dumping && (pairing_safe ||
           (record_reply/4u==COMP_V11_DIAG_RECORD_RECOVER&&diagnostic_fault_output_safe()))) {
            char line[160];
            (void)snprintf(line,sizeof(line),
                "REC1 command=%s request_result=%u token=%lu runtime_state=%u mic_running=%u request_only=1\r\n",
                record_reply/4u==COMP_V11_DIAG_RECORD_START?"START":
                record_reply/4u==COMP_V11_DIAG_RECORD_STOP?"STOP":
                record_reply/4u==COMP_V11_DIAG_RECORD_PAUSE?"PAUSE":
                record_reply/4u==COMP_V11_DIAG_RECORD_RESUME?"RESUME":
                record_reply/4u==COMP_V11_DIAG_RECORD_MARK?"MARK":
#if defined(COMPANION_WBA_BLE_LINKED) && COMPANION_WBA_EXPERIMENTAL_STOP1
                record_reply/4u==COMP_V11_DIAG_RECORD_STOP1_ONCE?"STOP1_ONCE":
                record_reply/4u==COMP_V11_DIAG_RECORD_STOP1_WINDOW?"STOP1_WINDOW":
#endif
                record_reply/4u==COMP_V11_DIAG_RECORD_CACHE_OFF_NEXT?"CACHE_OFF_NEXT":"RECOVER",
                (unsigned)(record_reply%4u),(unsigned long)record_reply_token,
                (unsigned)companion_app.runtime.recording,
                (unsigned)companion_v11.microphone.running);
            record_reply=0u;comp_v11_hal_log(line);
        }
        uint8_t imu_command,imu_axes;
        if(comp_v11_diag_console_take_imu(&diagnostic,&imu_command,&imu_axes)) {
            /* Consume once. A busy request is rejected, never kept until
             * a later meeting/transfer ends. Only readback-verified NOR
             * preferences may install a map; no direct RAM/pin pokes. */
            const bool valid=imu_command==2u || (imu_axes!=0u && comp_imu_screen_axes_valid(imu_axes));
            imu_reply=safe && valid && comp_v11_product_apply_imu_axes(&companion_app,imu_axes)?1u:2u;
        }
        if(imu_reply && pairing_safe && !panel_debug.dumping) {
            char line[128];
            (void)snprintf(line,sizeof(line),
                "IMU1 MAP %s axes=%02x generation=%lu persisted=%u\r\n",
                imu_reply==1u?"SAVED":"REJECTED",
                (unsigned)companion_app.preferences.values.imu_screen_axes,
                (unsigned long)companion_app.preferences.generation,
                (unsigned)companion_app.preferences.persisted);
            imu_reply=0u;comp_v11_hal_log(line);
        }
        if(comp_v11_diag_console_take_reconnect(&diagnostic)) {
            /* Same local menu recovery, without granting a new pairing
             * window. Reject once while busy/linked; never defer the action
             * until another capture or transfer has finished. */
            bool accepted=false;
#ifdef COMPANION_WBA_BLE_LINKED
            if(pairing_safe && !panel_debug.dumping && ble_initialized && !comp_v11_ble_linked())
                accepted=comp_v11_ble_menu(COMP_SCREEN_MENU_ACTION_PHONE_RECONNECT);
#endif
            reconnect_reply=accepted?1u:2u;
        }
        if(reconnect_reply && pairing_safe && !panel_debug.dumping) {
            comp_v11_hal_log(reconnect_reply==1u?
                "BLE1 RECONNECT_REQUESTED pairing_window_changed=0\r\n":
                "BLE1 RECONNECT_REJECTED busy_linked_or_not_ready\r\n");
            reconnect_reply=0u;
        }
        const uint32_t pair_request_blockers=diagnostic_output_blockers(true);
        if(comp_v11_diag_console_take_pair_guarded(&diagnostic,HAL_GetTick(),
                pair_request_blockers,&pair_battery_deadline)) {
            /* This physical service-port request uses the same window as the
             * local menu. It cannot interrupt capture/transfer/update or erase
             * bonds, and does not grant access to unencrypted GATT data. */
            pair_window_opened=false;
            pair_blockers=pair_request_blockers;
            /* Preserve the actual decision even if a busy guard clears
             * before the deferred reply. Protected work is never queued. */
            pair_menu_blockers=0u;
#ifdef COMPANION_WBA_BLE_LINKED
            if(!ble_initialized)pair_blockers|=UINT32_C(0x40000000);
            pair_menu_blockers=comp_v11_ble_menu_blockers();
            if(!pair_blockers && !pair_menu_blockers)
                pair_window_opened=comp_v11_ble_menu(COMP_SCREEN_MENU_ACTION_BROWSER_PAIR);
#else
            pair_blockers|=UINT32_C(0x40000000);
#endif
            pair_reply_pending=true;
        }
        if(pair_reply_pending && pairing_safe) {
            pair_reply_pending=false;
            char line[144];
            (void)snprintf(line,sizeof(line),
                "PAIR1 %s window_ms=%lu guards=%08lx menu=%02x action_failed=%u\r\n",
                pair_window_opened?"OPEN":"REJECTED",
                (unsigned long)(pair_window_opened?120000u:0u),
                (unsigned long)pair_blockers,(unsigned)pair_menu_blockers,
                (unsigned)(!pair_window_opened && !pair_blockers && !pair_menu_blockers));
            comp_v11_hal_log(line);
        }
        if(comp_v11_diag_console_take_battery(&diagnostic,pairing_safe && !panel_debug.dumping)) {
            /* Cached values only: no ADC start, gate change or panel command.
             * The single bounded line can report during panel BUSY, while all
             * capture/playback/storage/transfer/update exclusions still apply. */
            diagnostic_emit(&diagnostic,reset_flags,boot_route,ble_initialized,COMP_V11_DIAG_QUERY,true);
        } else if(diagnostic.query_pending && !panel_debug.dumping && diagnostic_fault_output_safe()) {
            /* Cached fault data only. Do not wait forever for a failed screen
             * or logical recorder reservation, and never authorize any work. */
            (void)comp_v11_diag_console_take_query(&diagnostic,true);
            logged=tick;
            diagnostic_record_fault();
        } else if(comp_v11_diag_console_take_query(&diagnostic,safe)) {
            logged=tick;
#if COMP_V11_DIAG_FLASH_ENABLED
            comp_v11_diag_flash_dump(&companion_v11);
#endif
            diagnostic_emit(&diagnostic,reset_flags,boot_route,ble_initialized,COMP_V11_DIAG_QUERY,false);
        } else if (COMPANION_WBA_PERIODIC_DIAGNOSTICS && tick-logged>=10000u && safe &&
#ifdef COMPANION_WBA_BLE_LINKED
                   /* A full unsolicited snapshot is now ~11KiB/1s at115200.
                    * During a connection it can starve foreground ATT/CCCD
                    * dispatch past a control deadline even with no bulk data.
                    * Defer it until physical disconnect; explicit diagnostics
                    * retain their existing request and safety gates above. */
                   !comp_v11_ble_linked() &&
#endif
                   comp_v11_diag_periodic_allowed(tick,companion_app.panel_debug_trace_until_ms)) {
            logged=tick;
            diagnostic_emit(&diagnostic,reset_flags,boot_route,ble_initialized,COMP_V11_DIAG_PERIODIC,false);
        }
        comp_cpu_detail_end(COMP_CPU_STAGE_MAIN_SERVICES,cpu_main_services,true);
        comp_v11_cpu_poll();
        comp_v11_low_power_idle(&companion_app);
    }
}
