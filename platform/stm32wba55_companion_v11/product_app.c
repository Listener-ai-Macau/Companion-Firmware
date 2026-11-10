#include "companion_recording_geometry.h"
#include "companion_cpu_stage.h"
#include "companion_opus16_rt.h"
#include "product_app.h"
#if COMPANION_WBA_DUAL_PAIR_CAPTURE
#include "dual_mic_capture.h"
#endif
#include "cpu_profile_target.h"
#include "capture_encode_window.h"
#include "companion_pet_trace.h"
#include "companion_pet_chat.h"
#include "battery_adc.h"
#include "companion_browser_interaction_contract.h"
#include "wba_storage_layout.h"
#include "wba_workspace_layout.h"
#include "wba_recording_crc.h"
#include <stdio.h>
#include <string.h>
#ifdef COMPANION_WBA_BLE_LINKED
#include "ble_product.h"
#include "clock_target.h"
#include "update_product.h"
#include "wba_ota_gatt.h"
#endif
#define RECORDING_BASE COMP_WBA_NOR_RECORDING_BASE
bool comp_v11_product_committed_read(comp_v11_product_app_t *app,size_t at,uint8_t *out,size_t n)
{
    return COMPANION_WBA_SCREEN_ENABLED && app && app->board && comp_ssd1681_wba_read_frame(&app->board->panel,app->panel_committed,at,out,n);
}
uint32_t comp_v11_product_committed_crc(comp_v11_product_app_t *app)
{
    if(!COMPANION_WBA_SCREEN_ENABLED)return 0u;
    uint8_t row[25];uint32_t crc=0u;
    for(size_t at=0u;at<5000u;at+=sizeof(row)) {
        if(!comp_v11_product_committed_read(app,at,row,sizeof(row)))return 0u;
        crc=comp_wba_recording_crc32(crc,row,sizeof(row));
    }
    return crc;
}
#define PREFERENCES_BASE COMP_WBA_NOR_PREFS_A
#ifndef COMPANION_SCREEN_MANUAL_REFRESH_KEY
/* Owner's current screen-debug firmware: each idle HOME short release can
 * replay the accepted bitmap without a host arm command. Keep this policy
 * explicit so the temporary button assignment can be removed at delivery. */
#define COMPANION_SCREEN_MANUAL_REFRESH_KEY 1
#endif
#ifndef COMP_V11_PANEL_STARTUP_READBACK
/* The fitted interface has not produced a valid controller readback. Keep
 * SDIN write-only in normal product operation; opt in only for diagnosis. */
#define COMP_V11_PANEL_STARTUP_READBACK 0
#endif
#if COMP_V11_PANEL_SOFTWARE_SPI && COMP_V11_PANEL_STARTUP_READBACK
static bool panel_audit_done;
#endif

void comp_v11_product_download_timing(bool enabled)
{
    /* V2 reads use the segmented storage owner. Legacy journal-read timing
     * has no observations here; do not reserve state or invent samples. */
    (void)enabled;
}
comp_v11_download_read_timing_t comp_v11_product_download_read_timing(void)
{ const comp_v11_download_read_timing_t empty={0};return empty; }
bool comp_v11_product_update_workspace(void *context,uint32_t bytes,uint32_t *physical)
{
    comp_v11_product_app_t *app=context;
#if COMPANION_WBA_DUAL_PAIR_CAPTURE
    if(comp_v11_dual_pair_owned(app))return false; /* Never release/reuse another owner's tail. */
#endif
    return app&&app->storage_layout_ready&&!app->board->microphone.running&&!app->pet_profile.writing&&
        comp_wba_recording_product_update_workspace(&app->recording,bytes,physical);
}
void comp_v11_product_recording_lease_result(comp_v11_product_app_t *app,bool ok)
{
    if(!app)return;
    comp_wba_recording_product_lease_result(&app->recording,ok);
    app->recording_ready=app->recording.ready;
}
static uint32_t recording_now(void *c) { (void)c; return HAL_GetTick(); }
static bool microphone_control(void *c,bool enabled)
{
    comp_v11_product_app_t *app=c;
    if(enabled && !app->board->microphone.running) {
        /* Most recent PDM run, including a failed/unavailable optional IMU.
         * Pauses restart this scope; the logical bookmark sequence persists. */
        app->board->imu.tap_reads=0u;app->board->imu.tap_counts=0u;
    }
    if(enabled && !app->board->microphone.running &&
       !comp_v11_hal_microphone_profile(app->board,app->capture_profile,
           app->recording.pipeline.pause_timeline==COMP_CONT_TIMELINE_AUDIO_PROFILE))return false;
    if (enabled) comp_v11_microphone_hal_fault_baseline(&app->board->microphone,&app->capture_baseline);
    if (!comp_v11_hal_microphone_enable(app->board,enabled)) return false;
    /* Sample only while the actual recorder owns the microphone. The meter
     * observes accepted PCM and never changes, stops or gates the recording. */
    comp_v11_product_recording_level_enable(app,enabled);
    /* A start gate can enable capture late in product_app_poll().  Anchor the
     * first deadline window at the actual mic start instead of charging work
     * that happened earlier in that iteration. */
    if (enabled) {
        comp_v11_cpu_capture_begin(app->runtime.record_token);
        app->capture_cycle_started_ms=HAL_GetTick();
        app->capture_started_ms=app->capture_cycle_started_ms;
        comp_wba_recording_level_reset(&app->recording_level,
            app->board->microphone.processing.stats.saturated_samples);
        comp_wba_silence_stop_init(&app->silence,app->preferences.values.policy.silent_auto_stop,
                                 app->capture_profile==1u);
        app->silence_stop_requested=false;
    }
    return true;
}
#if COMPANION_WBA_AUDIO_PROFILE
static bool recording_audio_profile(void *context,comp_rec_audio_profile_t *out)
{
    const comp_v11_product_app_t *app=context;
    return app && comp_v11_hal_microphone_audio_profile(app->board,app->capture_profile,out);
}
#endif
static bool recording_pcm(void *c,const int16_t *pcm,size_t count,uint32_t rate)
{
    comp_v11_product_app_t *app=c;
    if(!comp_wba_recording_product_pcm(&app->recording,pcm,count,rate))return false;
    if(app->recording_level_enabled)comp_wba_recording_level_pcm(&app->recording_level,pcm,count,
        app->board->microphone.processing.stats.saturated_samples,HAL_GetTick());
    if(comp_wba_silence_stop_pcm(&app->silence,pcm,count))app->silence_stop_requested=true;
    return true;
}
void comp_v11_product_recording_level_enable(comp_v11_product_app_t *app,bool enabled)
{
    if(!app||!app->board||app->recording_level_enabled==enabled)return;
    comp_wba_recording_level_reset(&app->recording_level,
        app->board->microphone.processing.stats.saturated_samples);
    app->recording_level_enabled=enabled;
}
bool comp_v11_product_recording_level(const comp_v11_product_app_t *app,uint32_t now_ms,
    comp_wba_recording_level_snapshot_t *out)
{
    return app&&app->board&&comp_wba_recording_level_snapshot(&app->recording_level,
        app->recording_level_enabled&&app->board->microphone.running&&app->runtime.capture_active&&
        app->recording.pipeline.state==COMP_PIPE_RECORDING,now_ms,out);
}
static void recording_catalog(comp_v11_product_app_t *app)
{
    if(!comp_wba_recording_product_space_current(&app->recording))return;
    const comp_wba_recording_space_t *s=&app->recording.space;
    comp_runtime_catalog(&app->runtime,s->logical,(uint16_t)((s->encoded_bytes+1023u)/1024u));
}
static void recording_capture_clock(comp_v11_product_app_t *app)
{
    const comp_wba_recording_pipeline_t *p=&app->recording.pipeline;
    if(!p->engine_bound||!p->pause_timeline)return;
    uint64_t elapsed=(uint64_t)app->recording.capture.engine.stats.accepted_pcm_blocks*10u;
    (void)comp_runtime_recording_captured(&app->runtime,p->token,
        elapsed>UINT32_MAX?UINT32_MAX:(uint32_t)elapsed);
}
static void recording_report(void *c,uint32_t token,denzic_audio_recording_state_v1_t state,bool active)
{
    comp_v11_product_app_t *app=c;
    if(token&&token==app->runtime.record_token&&!active&&
       state==DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY&&
       app->recording.pipeline.state==COMP_PIPE_FAILED&&app->recording.pipeline.engine_bound)
        app->recording_fault_recovery_pending=true;
    recording_catalog(app);
    recording_capture_clock(app);
    if(!active&&(state==DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY ||
       state==DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY || state==DENZIC_AUDIO_RECORDING_STATE_CANCELED))
        comp_v11_cpu_capture_end(token);
    /* Only the current sealed recording can report a full-storage stop.
     * The recording remains TRANSFER_READY so its saved audio stays usable. */
    if(!active && state==DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY &&
       token==app->runtime.record_token && token==app->recording.pipeline.token &&
       !app->runtime.start_pending && app->recording.pipeline.engine_bound &&
       (app->runtime.recording==DENZIC_AUDIO_RECORDING_STATE_RECORDING ||
        app->runtime.recording==DENZIC_AUDIO_RECORDING_STATE_STOPPING) &&
       app->recording.capture.engine.stop_reason==COMP_CONT_STOP_FULL)
        app->runtime.record_stop_reason=COMP_RECORD_STOP_STORAGE_FULL;
    (void)comp_runtime_recording_update(&app->runtime,token,state,active,HAL_GetTick());
}
static bool capture_deadline_check(comp_v11_product_app_t *app,uint8_t site)
{
    if(!app->recording.media_ready||!app->recording.capture.engine.microphone_active)return true;
    uint32_t elapsed=HAL_GetTick()-app->capture_cycle_started_ms;
    if(elapsed>app->max_capture_foreground_ms)app->max_capture_foreground_ms=elapsed;
    if(elapsed<=10u)return true;
    if(!app->capture_deadline_faults)app->capture_deadline_site=site;
    ++app->capture_deadline_faults;
    comp_wba_recording_product_fault(&app->recording,COMP_WBA_RECORDING_FAULT_DEADLINE);
    return false;
}
static void capture_validate_body(comp_v11_product_app_t *app)
{
    if(app->recording.media_ready && app->recording.pipeline.engine_bound &&
       app->recording.capture.engine.microphone_active &&
       !comp_v11_microphone_hal_fault_baseline_matches(&app->board->microphone,&app->capture_baseline))
        comp_wba_recording_product_fault(&app->recording,COMP_WBA_RECORDING_FAULT_PLATFORM_CAPTURE);
}
static void capture_validate(comp_v11_product_app_t *app)
{
    comp_cpu_stage_span_t cpu=comp_cpu_detail_begin();
    capture_validate_body(app);
    comp_cpu_detail_end(COMP_CPU_STAGE_VALIDATE,cpu,true);
}
static bool recording_encode_window(void *context,bool microphone_active,uint8_t queued_pcm)
{
    comp_v11_product_app_t *app=context;
    if(microphone_active && !comp_v11_microphone_hal_encode_window(&app->board->microphone))return false;
#ifdef COMPANION_WBA_BLE_LINKED
    /* The core calls this at every actual encode, also after capture stops.
     * Only active capture with30ms queued PCM bypasses radio courtesy. */
    if(!comp_v11_ble_capture_encode_window(!microphone_active || queued_pcm<3u))return false;
#if COMPANION_WBA_CPU_RESIDENCE_PROFILE
    uint32_t flags,next_us;comp_v11_ble_capture_admission_observed(&flags,&next_us);
    comp_cpu_codec_admission(flags|((uint32_t)queued_pcm<<16u),next_us);
#endif
#else
    (void)queued_pcm;
#endif
    return true;
}
static bool recording_work_poll(comp_v11_product_app_t *app,uint32_t elapsed_ms,bool converted)
{
    const bool staging=comp_wba_recording_product_pcm_staging_pending(&app->recording);
    /* Never append a full non-preemptible encode to a PDM conversion. A
     * first PCM half is only bounded RAM staging and retains its old gate. */
    if((converted && !staging) || !comp_v11_capture_work_window_open(elapsed_ms,staging,
        staging || comp_v11_microphone_hal_encode_window(&app->board->microphone)))return false;
    uint32_t before=app->recording.capture.engine.stats.encoded_packets;
    if(staging)(void)comp_wba_recording_product_stage_pcm_half(&app->recording);
    else comp_wba_recording_product_poll(&app->recording);
    return app->recording.pipeline.engine_bound &&
        app->recording.capture.engine.stats.encoded_packets!=before;
}
static bool capture_progress_body(comp_v11_product_app_t *app,uint8_t origin)
{
    if(!app->recording.media_ready||!app->recording.capture.engine.microphone_active) {
        if(app->board->playback_active)comp_v11_hal_speaker_poll(app->board);
        return true;
    }
    if(!capture_deadline_check(app,origin))return false;
    app->capture_cycle_started_ms=HAL_GetTick();
    uint32_t started=HAL_GetTick();
    comp_v11_microphone_poll_result_t polled=comp_v11_microphone_hal_poll(&app->board->microphone);
    if(polled==COMP_V11_MIC_POLL_ERROR)app->board->faults|=COMP_V11_FAULT_MICROPHONE;
    uint32_t elapsed=HAL_GetTick()-started;
    if(elapsed>app->board->microphone_max_poll_ms)app->board->microphone_max_poll_ms=elapsed;
    capture_validate(app);
    /* The low-clock full encode reaches 8 ms. Conversion and full encoding
     * need separate dispatches; PCM staging still uses its bounded RAM step.
     * Never discard samples or lengthen the hard service deadline. */
    bool encoded=recording_work_poll(app,elapsed,polled!=COMP_V11_MIC_POLL_IDLE);
    if(!capture_deadline_check(app,2u))return false;
    app->capture_cycle_started_ms=HAL_GetTick();
    if(encoded && app->board->microphone.running) {
        /* A half may have completed during Opus. Copy/convert it now,
         * before returning to SPI/UI work; never recursively encode here.
         * Both slices retain the normal hard deadline and fault comparison. */
        uint32_t after_encode=HAL_GetTick();
        if(comp_v11_microphone_hal_poll(&app->board->microphone)==COMP_V11_MIC_POLL_ERROR)
            app->board->faults|=COMP_V11_FAULT_MICROPHONE;
        uint32_t poll_ms=HAL_GetTick()-after_encode;
        if(poll_ms>app->board->microphone_max_poll_ms)app->board->microphone_max_poll_ms=poll_ms;
        capture_validate(app);
        if(!capture_deadline_check(app,3u))return false;
        app->capture_cycle_started_ms=HAL_GetTick();
    }
    return app->recording.pipeline.state!=COMP_PIPE_FAILED;
}
static bool capture_progress(comp_v11_product_app_t *app,uint8_t origin)
{
    comp_cpu_stage_span_t cpu=comp_cpu_detail_begin();
    bool ok=capture_progress_body(app,origin);
    comp_cpu_detail_end(COMP_CPU_STAGE_CAPTURE_PROGRESS,cpu,true);
    return ok;
}
static bool render_io_progress(comp_v11_product_app_t *app,uint8_t origin)
{
    if(!capture_progress(app,origin))return false;
#ifdef COMPANION_WBA_BLE_LINKED
    if(!app->board->microphone.running) {
        comp_v11_ble_transfer_progress();
        comp_v11_ble_idle_background_progress();
    }
#endif
    return true;
}
static bool resource_read(void *c,uint32_t offset,uint8_t *data,size_t length)
{
    comp_v11_product_app_t *app=c;
    if(!app || !data || offset>app->resource_partition.size_bytes ||
       length>app->resource_partition.size_bytes-offset)return false;
    if(app->recording.storage.poisoned && app->resource_partition.nor &&
       app->recording.storage.nor==app->resource_partition.nor)return false;
    /* End each NOR transaction before servicing audio: one SPI owner, no
     * recursive UI or control work. When stopped, feed only the authorized
     * sealed transfer. Keep the existing cache, bytes and CRC checks. */
    if(!render_io_progress(app,30u))return false;
    for(size_t done=0u;done<length;) {
        size_t count=length-done;if(count>256u)count=256u;
        companion_spi_nor_stm32wba_t *nor=app->resource_partition.nor;
        if(app->board && app->board->microphone.running && app->recording.media_ready &&
           app->recording.pipeline.engine_bound && app->recording.capture.engine.microphone_active && nor &&
           nor->config.target==COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55 &&
           nor->info.jedec_id==UINT32_C(0xef6018) && nor->config.transfer_timeout_ms) {
            /* One timed read, no speculative retry: if a resource fetch
             * fails, abandon this render rather than holding capture behind
             * the ordinary long SPI timeout. No partial bytes are accepted. */
            bool released=false;
            uint32_t address=app->resource_partition.base_address+offset+(uint32_t)done;
            companion_spi_nor_stm32wba_status_t result=
                companion_spi_nor_stm32wba_read_transient(nor,address,data+done,count,&released);
            if(result!=COMPANION_SPI_NOR_STM32WBA_OK) {
                if(result==COMPANION_SPI_NOR_STM32WBA_PENDING || released)
                    (void)render_io_progress(app,31u);
                else if(app->recording.storage.nor==nor) {
                    /* An uncertain select/header/release can leave the shared
                     * bus active. Do not issue more NOR work under capture. */
                    app->recording.storage.poisoned=true;
                    comp_wba_recording_product_fault(&app->recording,COMP_WBA_RECORDING_FAULT_STORAGE_IO);
                }
                return false;
            }
        } else if(!companion_spi_nor_stm32wba_partition_read(&app->resource_partition,
                offset+(uint32_t)done,data+done,count))return false;
        done+=count;
        if(!render_io_progress(app,31u))return false;
    }
    return true;
}
static bool identity_erase(void *c,uint32_t offset)
{return companion_spi_nor_stm32wba_partition_erase_4k(c,offset)==COMPANION_SPI_NOR_STM32WBA_OK;}
static bool identity_write(void *c,uint32_t offset,const uint8_t *data,size_t bytes)
{return companion_spi_nor_stm32wba_partition_program(c,offset,data,bytes)==COMPANION_SPI_NOR_STM32WBA_OK;}
static bool identity_mount(comp_v11_product_app_t *app)
{
    uint8_t uid[12];
    const comp_rec_identity_port_t port={companion_spi_nor_stm32wba_partition_read,
        identity_write,identity_erase,&app->recording_identity_partition};
    return comp_v11_hal_device_uid(uid)&&comp_rec_identity_mount(&app->recording_identity,&port,uid);
}
static void identity_entropy_poll(comp_v11_product_app_t *app)
{
    uint32_t word;
    if(!app->recording_identity.ready||app->recording_identity.loaded||app->identity_entropy_words>=2u||
       app->board->microphone.running)return;
    if(comp_v11_hal_random_u32(app->board,&word)){
        app->identity_entropy|=(uint64_t)word<<(32u*app->identity_entropy_words);
        app->identity_entropy_words++;
        if(app->identity_entropy_words==2u&&!app->identity_entropy)app->identity_entropy_words=0u;
    }
}
static bool recording_prepare(void *,uint32_t);
static void recording_namespace_poll(comp_v11_product_app_t *app)
{
    if(!app->storage_layout_ready||app->runtime.config.recording_prepare!=recording_prepare||
       app->recording.boot_phase)return;
    if(!app->recording_identity.ready)return;
    if(!app->recording_identity.loaded) {
        if(app->identity_entropy_words!=2u)return;
        /* Establish CSI1's random namespace through its durable allocator.
         * One legal allocation gap on first creation, never a tick-based ID. */
        uint64_t bootstrap;
        if(!comp_rec_identity_allocate_session(&app->recording_identity,app->identity_entropy,&bootstrap)) {
            app->storage_layout_ready=false;return;
        }
    }
    comp_wba_pipeline_config_t cfg={0};
    cfg.microphone=microphone_control;cfg.now_ms=recording_now;cfg.context=app;
    cfg.encode_window=recording_encode_window;
#if COMPANION_WBA_AUDIO_PROFILE
    cfg.audio_profile=recording_audio_profile;
#endif
    /* Derive aligned extents from the actual arena. Fixed256KiB/120s
     * stranded the final224KiB and stopped an otherwise empty offline ring
     * at118 minutes. Existing entries keep their own immutable reservations. */
    comp_recording_geometry_t geometry;
    if(!comp_recording_geometry_plan_profile(COMP_WBA_NOR_RECORDING_DATA_BYTES,
                                    COMP_SEGMENT_CAPACITY,cfg.audio_profile!=NULL,&geometry))return;
    cfg.segment_frames=geometry.segment_frames;cfg.extent_bytes=geometry.extent_bytes;
    if(!comp_wba_recording_product_bind(&app->recording,&app->board->nor,
        COMP_WBA_NOR_SEGMENT_CATALOG_A,COMP_WBA_NOR_SEGMENT_CATALOG_B,RECORDING_BASE,
        COMP_WBA_NOR_RECORDING_DATA_BYTES,COMP_WBA_NOR_RECORDING_CATALOG,
        app->recording_identity.record.device_uid,app->recording_identity.record.format_epoch,&cfg,recording_report)||
       !comp_v11_hal_set_pcm_sink(app->board,recording_pcm,app))app->storage_layout_ready=false;
}
static void recording_boot_retry_poll(comp_v11_product_app_t *app,uint32_t now)
{
    if(!app)return;
    if(app->recording_link_retry&&!comp_wba_recording_product_idle_retry_exhausted(&app->recording))
        app->recording_link_retry=false;
    if((!app->recording_link_retry&&!comp_wba_recording_product_boot_retry_pending(&app->recording))||
       !app->board||!app->storage_layout_ready||app->pet_profile.writing||
       app->board->microphone.running||app->board->playback_active||app->runtime.menu_pending||
       app->runtime.prepare_pending||app->runtime.start_pending||app->runtime.command_pending||
       !companion_opus16_rt_workspace_available())return;
#if COMPANION_WBA_DUAL_PAIR_CAPTURE
    if(comp_v11_dual_pair_owned(app))return;
#endif
#ifdef COMPANION_WBA_BLE_LINKED
    if(!comp_v11_ble_recording_recovery_idle())return;
#endif
    if(app->recording_link_retry) {
        app->recording_link_retry=false;
        (void)comp_wba_recording_product_retry_idle_explicit(&app->recording,now);
    } else (void)comp_wba_recording_product_boot_retry(&app->recording,now);
}
void comp_v11_product_recording_link_change(comp_v11_product_app_t *app,bool connected,bool new_secure)
{
    if(!app)return;
    if(!connected)app->recording_link_retry=false;
    else if(new_secure&&comp_wba_recording_product_idle_retry_exhausted(&app->recording))
        app->recording_link_retry=true;
}
static bool recording_power_allowed(comp_v11_product_app_t *app)
{
    comp_wba_power_monitor_t *m=&app->board->power_monitor;
    uint32_t now=HAL_GetTick();
    if(comp_wba_power_monitor_recording_allowed(m,now))return true;
    app->runtime.record_stop_reason=m->recording_power_blocked ||
        (comp_wba_power_recording_limits_safe(&m->profile) &&
         comp_wba_power_monitor_snapshot(m,now).voltage_valid) ?
        COMP_RECORD_STOP_LOW_BATTERY:COMP_RECORD_STOP_POWER_UNKNOWN;
    return false;
}
static bool recording_recovery_idle(comp_v11_product_app_t *app)
{
    if(!app||!app->board||!comp_wba_recording_product_capture_available(&app->recording)||app->pet_profile.writing||app->runtime.menu_pending||
       app->runtime.capture_active||app->runtime.command_pending||app->runtime.prepare_pending||
       app->runtime.start_pending||app->runtime.stop_pending||app->board->microphone.running||
       app->board->playback_active||!companion_opus16_rt_workspace_available())return false;
#ifdef COMPANION_WBA_BLE_LINKED
    if(!comp_v11_ble_recording_recovery_idle())return false;
#endif
    return true;
}
bool comp_v11_product_recording_recover(comp_v11_product_app_t *app)
{
    if(!recording_recovery_idle(app)||!comp_wba_recording_product_recoverable(&app->recording))return false;
    app->recording_fault_recovery_pending=false;
    return comp_wba_recording_product_recover_begin(&app->recording);
}
static void recording_fault_recovery_poll(comp_v11_product_app_t *app)
{
    /* This event comes from a real failed capture, never a status read. Wait
     * for existing audio/NOR/radio owners, then reuse the ordinary bounded
     * recovery once. No microphone start, session allocation, forced lease
     * release or endless physical-status retry belongs to this transition. */
    if(!comp_wba_recording_product_capture_available(&app->recording)||
       app->recording.pipeline.state!=COMP_PIPE_FAILED) {
        app->recording_fault_recovery_pending=false;return;
    }
    (void)comp_v11_product_recording_recover(app);
}
static bool recording_prepare(void *c,uint32_t token)
{
    comp_v11_product_app_t *app=c;
    uint64_t session_id;
    if (!token || !app->board->microphone.initialized ||
        (app->board->faults & COMP_V11_FAULT_SPEAKER_SHUTDOWN) != 0u || app->pet_profile.writing) return false;
    if(!recording_power_allowed(app))return false;
#ifdef COMPANION_WBA_BLE_LINKED
    /* Unsent read-ahead still has its NOR original. Return the temporary idle
     * lease before this START checks/claims the same real codec/DMA arena. */
    comp_v11_ble_release_transfer_workspace();
#endif
    if(!comp_wba_recording_product_capture_available(&app->recording)) {
        /* A fresh START may retry only the exhausted read-only idle fault.
         * The ordinary recovery gate prevents any other NOR/audio owner from
         * being retired; boot or damaged-root failures remain unavailable. */
        if(!app->storage_layout_ready||app->runtime.menu_pending||app->board->microphone.running||
           app->board->playback_active||!companion_opus16_rt_workspace_available())return false;
#if COMPANION_WBA_DUAL_PAIR_CAPTURE
        if(comp_v11_dual_pair_owned(app))return false;
#endif
#ifdef COMPANION_WBA_BLE_LINKED
        if(!comp_v11_ble_recording_recovery_idle())return false;
#endif
        return comp_wba_recording_product_retry_idle_explicit(&app->recording,HAL_GetTick());
    }
    if(app->recording.pipeline.state==COMP_PIPE_FAILED) {
        /* An explicit START may own recovery before its stopped-fault event
         * is serviced. Status reads never request it; keep the same DMA,
         * playback, radio and WUS2 ownership as ordinary recovery. */
        if(app->board->microphone.running||app->board->playback_active||
           !companion_opus16_rt_workspace_available())return false;
#ifdef COMPANION_WBA_BLE_LINKED
        if(!comp_v11_ble_recording_recovery_idle())return false;
#endif
        return comp_wba_recording_product_recover_begin(&app->recording);
    }
#ifdef COMPANION_WBA_BLE_LINKED
    if(comp_v11_ble_storage_busy() || !companion_opus16_rt_workspace_available())return false;
#endif
    if (app->board->nor.erase_active) {
        if(!comp_wba_recording_pipeline_primed(&app->recording.pipeline))return false;
        /* CSI1 identity persistence is synchronous and must not race an idle
         * erase. Accept this explicit request; the foreground settles that
         * one chunk before recording_is_ready allocates its real identity. */
        app->recording_session_id=0u;return true;
    }
    comp_wba_pipeline_state_t state=app->recording.pipeline.state;
    if(state!=COMP_PIPE_IDLE&&state!=COMP_PIPE_FINISHED)return false;
    if(!comp_wba_recording_product_capture_prepare_available(&app->recording))return false;
    if(!app->recording_identity.ready||!app->recording_identity.loaded) {
        app->recording.last_fault=COMP_WBA_RECORDING_FAULT_STORAGE_IO;return false;
    }
    app->recording_session_id=0u;
    bool timeline=true;
#ifdef COMPANION_WBA_BLE_LINKED
    timeline=comp_v11_ble_recording_timeline_requested(token);
#endif
    const uint8_t profile=app->preferences.values.policy.recorder_profile;
    const bool provenance=timeline && app->recording.pipeline.config.audio_profile!=NULL;
    if(profile>1u || !comp_v11_hal_microphone_profile(app->board,profile,provenance))return false;
    if(provenance) {
        comp_rec_audio_profile_t check;
        if(!comp_v11_hal_microphone_audio_profile(app->board,profile,&check))return false;
    }
    /* Validate the actual microphone/profile before consuming a durable
     * session identity. A rejected profile cannot burn IDs or NOR writes. */
    if(!comp_rec_identity_allocate_session(&app->recording_identity,app->identity_entropy,&session_id)) {
        app->recording.last_fault=COMP_WBA_RECORDING_FAULT_STORAGE_IO;return false;
    }
    const uint8_t previous_profile=app->capture_profile;app->capture_profile=profile;
    /* Capture the UTC date once, before prepare. Later host clock changes
     * never rewrite the session anchor or its sample-based timeline. */
    const uint32_t started_unix=comp_clock_unix(&app->clock,HAL_GetTick());
    const bool accepted=provenance?
        comp_wba_recording_product_prepare_audio_profile(&app->recording,session_id,1u,started_unix,token):
        timeline?comp_wba_recording_product_prepare_bookmarked(&app->recording,session_id,1u,started_unix,token):
        comp_wba_recording_product_prepare_timeline(&app->recording,session_id,1u,started_unix,token,false);
    if(!accepted){app->capture_profile=previous_profile;return false;}
    app->recording_session_id=session_id;return true;
}
static bool recording_is_ready(void *c)
{
    comp_v11_product_app_t *app=c;
    if(app->runtime.prepare_pending&&!comp_wba_recording_product_capture_available(&app->recording)&&
       comp_wba_recording_product_state(&app->recording)==COMP_WBA_RECORDING_FAULT) {
        (void)comp_runtime_recording_update(&app->runtime,app->runtime.record_token,
            DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY,false,HAL_GetTick());
        return false;
    }
    /* A recovered fault or accepted idle-erase handoff has no new identity.
     * Re-enter only for this still-pending explicit START. Cancellation never
     * creates a session and the synchronous identity writer sees idle NOR. */
    if(app->runtime.prepare_pending && comp_wba_recording_product_capture_available(&app->recording) &&
        (app->recording.pipeline.state==COMP_PIPE_IDLE||app->recording.pipeline.state==COMP_PIPE_FINISHED) &&
        (app->recording.last_fault||!app->recording_session_id) && !app->board->nor.erase_active &&
       !recording_prepare(c,app->runtime.record_token)) {
        /* Recovery has completed, but the one requested prepare failed.
         * End this request rather than polling it again and repeatedly
         * allocating durable identities; a new START is explicit. */
        (void)comp_runtime_recording_update(&app->runtime,app->runtime.record_token,
            DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY,false,HAL_GetTick());
    }
    return comp_wba_recording_product_ready(&app->recording,app->runtime.record_token);
}

bool comp_v11_product_recording_capacity(const comp_v11_product_app_t *app,
                                        companion_recording_capacity_v1_t *value)
{
    if (!value) return false;
    memset(value,0,sizeof(*value));
    value->tag=COMPANION_RECORDING_CAPACITY_GEOMETRY_TAG;
    value->layout_version=COMP_WBA_NOR_LAYOUT_VERSION;value->max_entries=COMP_SEGMENT_CAPACITY;
    if (!app || !comp_wba_recording_product_capture_available(&app->recording)) return false;
    /* CCQ2 reuses these two existing wire words for explicit geometry.
     * The116-byte status/CRV2 tail, layout and actual space counters stay put. */
    value->bytes_per_second=app->recording.pipeline.config.segment_frames;
    value->reserve_headroom=app->recording.pipeline.config.extent_bytes;
    const comp_wba_recording_space_t *space=&app->recording.space;
    bool current=comp_wba_recording_product_space_current(&app->recording);
    value->flags=current?COMPANION_RECORDING_CAPACITY_VALID:0u;
    /* The existing CDS3 worker is bound by comp_link_init_segmented. Loss
     * approval remains separate from a receiver's durable-copy consume. */
    if(current)value->flags|=COMPANION_RECORDING_CAPACITY_CONFIRMED_DISCARD;
    if (app->runtime.capture_active || app->runtime.prepare_pending ||
        app->runtime.start_pending || app->runtime.command_pending ||
        !current || space->allocation_uncertain ||
        comp_wba_recording_pipeline_storage_busy(&app->recording.pipeline))
        value->flags|=COMPANION_RECORDING_CAPACITY_BUSY;
#ifdef COMPANION_WBA_BLE_LINKED
    if (comp_v11_ble_storage_busy())value->flags|=COMPANION_RECORDING_CAPACITY_BUSY;
#endif
    value->catalog_generation=app->recording.catalog.generation;
    value->data_bytes=app->recording.catalog.data_bytes-app->recording.pipeline.workspace_bytes;
    if(current) {
        value->free_bytes=space->arena_bytes-space->reserved_bytes;value->largest_free_extent=space->largest_gap;
        value->protected_bytes=space->reserved_bytes-space->consumed_bytes;value->consumed_bytes=space->consumed_bytes;
        _Static_assert(COMP_SEGMENT_CAPACITY<=UINT8_MAX,"capacity counts fit wire fields");
        value->used_entries=(uint8_t)space->used;value->unsynced_entries=(uint8_t)space->unsynced;
        value->writing_entries=(uint8_t)space->writing;value->consumed_entries=(uint8_t)space->consumed;
    }
    value->local_limit_seconds=0u; /* WBA local recording has no configured time limit. */
    return true;
}
comp_capture_feedback_t comp_v11_product_capture_feedback(const comp_v11_product_app_t *app,bool updating)
{
    comp_capture_feedback_t out={0};
    if(!app||!app->board)return out;
    const comp_wba_recording_product_t *product=&app->recording;
    const comp_wba_recording_pipeline_t *pipeline=&product->pipeline;
    const bool microphone=app->board->microphone.running;
    if(microphone)out.flags|=COMP_CAPTURE_MIC_RUNNING;
    if(updating){out.state=COMP_CAPTURE_UPDATING;return out;}
    if(!comp_wba_recording_product_capture_available(product)) {
        out.state=comp_wba_recording_product_state(product)==COMP_WBA_RECORDING_FAULT?
            COMP_CAPTURE_ERROR:COMP_CAPTURE_PREPARING;
        return out; /* The recovery union is not a live recording engine. */
    }
    const comp_cont_recording_t *engine=pipeline->engine_bound?&product->capture.engine:NULL;
    if(pipeline->state==COMP_PIPE_FAILED||(engine&&engine->state==COMP_CONT_FAULT)) {
        const bool full=(pipeline->state==COMP_PIPE_FAILED&&pipeline->failure==COMP_SEG_FULL)||
            (engine&&engine->state==COMP_CONT_FAULT&&engine->failure==COMP_SEG_FULL);
        out.state=full?COMP_CAPTURE_FULL:COMP_CAPTURE_ERROR;
        if(full)out.full_reason=COMP_CAPTURE_FULL_ALLOCATION;
        return out;
    }
    if(engine&&engine->bookmark_request&&engine->state!=COMP_CONT_CANCELED&&engine->state!=COMP_CONT_CANCELING) {
        out.bookmark_request=engine->bookmark_request;
        const comp_segment_result_t result=comp_wba_recording_product_bookmark_result(
            product,pipeline->token,engine->bookmark_request);
        if(result==COMP_SEG_PENDING)out.flags|=COMP_CAPTURE_MARK_PENDING;
        else if(result==COMP_SEG_OK)out.flags|=COMP_CAPTURE_MARK_CONFIRMED;
    }
    if(pipeline->state==COMP_PIPE_STOPPING||pipeline->state==COMP_PIPE_CLEANUP||
       (pipeline->stop_requested&&pipeline->state!=COMP_PIPE_FINISHED)||
       (engine&&(engine->state==COMP_CONT_STOPPING||engine->state==COMP_CONT_ENDING_PAUSE||
                 engine->state==COMP_CONT_CANCELING||
                 (engine->state==COMP_CONT_SEALED&&(pipeline->state!=COMP_PIPE_FINISHED||
                                                   microphone||product->catalog.phase))))) {
        out.state=COMP_CAPTURE_SAVING;return out;
    }
    if(app->runtime.prepare_pending||app->runtime.start_pending||
       pipeline->state==COMP_PIPE_PREPARING||pipeline->state==COMP_PIPE_READY) {
        out.state=COMP_CAPTURE_PREPARING;return out;
    }
    if(pipeline->state==COMP_PIPE_RECORDING&&engine) {
        if(engine->state==COMP_CONT_PAUSED&&!microphone)out.state=COMP_CAPTURE_PAUSED;
        else if(engine->state==COMP_CONT_PAUSE_PENDING||engine->state==COMP_CONT_PAUSING)
            out.state=COMP_CAPTURE_PAUSING;
        else if(engine->state==COMP_CONT_RESUMING)out.state=COMP_CAPTURE_RESUMING;
        else out.state=engine->state==COMP_CONT_RUNNING&&microphone&&engine->microphone_active&&engine->stats.accepted_pcm_blocks?
            COMP_CAPTURE_RECORDING:COMP_CAPTURE_PREPARING;
        return out;
    }
    if(pipeline->state==COMP_PIPE_FINISHED&&engine&&engine->state==COMP_CONT_SEALED&&
       !microphone&&!product->catalog.phase) {
        out.flags|=COMP_CAPTURE_ORIGINAL_SAVED;
        out.state=COMP_CAPTURE_SAVED;
        if(engine->stop_reason==COMP_CONT_STOP_FULL)out.full_reason|=COMP_CAPTURE_FULL_STOP;
    } else out.state=COMP_CAPTURE_IDLE;
    companion_recording_capacity_v1_t capacity;
    if(comp_v11_product_recording_capacity(app,&capacity)&&
       (capacity.flags&(COMPANION_RECORDING_CAPACITY_VALID|COMPANION_RECORDING_CAPACITY_BUSY))==
            COMPANION_RECORDING_CAPACITY_VALID) {
        out.flags|=COMP_CAPTURE_CAPACITY_KNOWN;
        if(capacity.unsynced_entries)out.flags|=COMP_CAPTURE_UNSYNCED;
        /* Use the existing geometry-qualified scan, not total free bytes or
         * an invented minutes-left estimate. ACKED bytes remain occupied. */
        if(!product->space.allocatable_segments) {
            out.full_reason|=COMP_CAPTURE_FULL_NO_SEGMENTS;
            if(capacity.used_entries>=capacity.max_entries)out.full_reason|=COMP_CAPTURE_FULL_SLOTS;
            if(capacity.reserve_headroom&&capacity.largest_free_extent<capacity.reserve_headroom)
                out.full_reason|=COMP_CAPTURE_FULL_EXTENT;
        }
    }
    if(out.full_reason&COMP_CAPTURE_FULL_NO_SEGMENTS)out.state=COMP_CAPTURE_FULL;
    return out;
}
static bool recording_control(void *c,bool start,uint32_t token)
{
    comp_v11_product_app_t *app=c;
    if(!start&&token==app->runtime.record_token&&
       !app->recording_session_id&&!app->board->microphone.running&&
       (app->recording.pipeline.state==COMP_PIPE_IDLE||app->recording.pipeline.state==COMP_PIPE_FINISHED))
        return comp_runtime_recording_update(&app->runtime,token,
            DENZIC_AUDIO_RECORDING_STATE_CANCELED,false,HAL_GetTick());
    if(!start&&token==app->runtime.record_token&&
       comp_wba_recording_product_recovering(&app->recording)&&
       !app->recording.pipeline.engine_bound&&!app->board->microphone.running)
        return comp_runtime_recording_update(&app->runtime,token,
            DENZIC_AUDIO_RECORDING_STATE_CANCELED,false,HAL_GetTick());
    if(start && (!recording_power_allowed(app) ||
       (app->board->faults & COMP_V11_FAULT_SPEAKER_SHUTDOWN) != 0u)) {
        /* Release the prepared reservation through its ordinary async cancel.
         * Denying the late start must not strand an open prepared writer. */
        if(comp_wba_recording_product_capture_available(&app->recording))(void)comp_wba_recording_product_control(&app->recording,false,token);
        return false;
    }
    if(!comp_wba_recording_product_capture_available(&app->recording))return false;
    if(!start) {
        /* Recovery has no new writer/microphone to STOP. Cancel the pending
         * intent while its already-owned validation finishes in foreground.
         * Do not turn an unfinished/corrupt old prefix into a saved result. */
        if(token==app->runtime.record_token && app->recording.last_fault &&
           !app->recording.pipeline.engine_bound && !app->board->microphone.running &&
           comp_wba_recording_product_state(&app->recording)!=COMP_WBA_RECORDING_FAULT)
            return comp_runtime_recording_update(&app->runtime,token,
                DENZIC_AUDIO_RECORDING_STATE_CANCELED,false,HAL_GetTick());
        comp_cont_stop_t why=app->runtime.record_stop_reason==COMP_RECORD_STOP_LOW_BATTERY?COMP_CONT_STOP_LOW_BATTERY:
            app->runtime.record_stop_reason==COMP_RECORD_STOP_DURATION_LIMIT?COMP_CONT_STOP_LIMIT:
            app->runtime.record_stop_reason==COMP_RECORD_STOP_SILENCE?COMP_CONT_STOP_SILENCE:COMP_CONT_STOP_USER;
        return comp_wba_recording_product_stop_reason(&app->recording,token,why);
    }
    return comp_wba_recording_product_control(&app->recording,true,token);
}
bool comp_v11_product_recording_bookmark(comp_v11_product_app_t *app,uint32_t token,uint32_t request)
{
    return app&&comp_wba_recording_product_capture_available(&app->recording)&&!comp_runtime_recording_hold(&app->runtime)&&
        token==app->runtime.record_token&&comp_wba_recording_product_bookmark(&app->recording,token,request);
}
static void recording_local_bookmark(comp_v11_product_app_t *app)
{
    uint32_t request=app->recording.capture.engine.bookmark_request+1u;
    if(!request)request=1u;
    (void)comp_v11_product_recording_bookmark(app,app->runtime.record_token,request);
}
static void recording_input_apply(comp_v11_product_app_t *app,uint16_t events,uint32_t now)
{
    comp_recorder_input_t *s=&app->input;
    if(events&COMP_INPUT_START) {
        if(comp_runtime_record(&app->runtime,true,now)==COMP_RUNTIME_OK)s->record_token=app->runtime.record_token;
        else events&=(uint16_t)~(COMP_INPUT_START|COMP_INPUT_STOP|COMP_INPUT_SUBMIT);
    }
    if(events&COMP_INPUT_STOP) {
        const bool owned=s->mode!=COMP_INPUT_DICTATION&&!(s->flags&COMP_INPUT_DETACHED);
        if((owned||s->record_token==app->runtime.record_token)&&comp_runtime_recording_owned(&app->runtime))
            (void)comp_runtime_record(&app->runtime,false,now);
        else events&=(uint16_t)~(COMP_INPUT_STOP|COMP_INPUT_SUBMIT);
    }
    if(events&COMP_INPUT_MARK) {
        if(app->board->microphone.running&&app->runtime.recording==DENZIC_AUDIO_RECORDING_STATE_RECORDING)
            recording_local_bookmark(app);
        else events&=(uint16_t)~COMP_INPUT_MARK;
    }
    comp_input_note(s,events,now);
    if(s->mode==COMP_INPUT_RECORDER&&!(s->flags&COMP_INPUT_HELD))s->flags=0u;
}
void comp_v11_product_input_status(const comp_v11_product_app_t *app,uint32_t request,
    uint8_t result,uint8_t response[64])
{
    const comp_recorder_input_t *s=&app->input;
    const bool updating=(app->board->power.blockers&COMP_POWER_BLOCKER_UPDATE)!=0u;
    const comp_capture_feedback_t feedback=comp_v11_product_capture_feedback(app,updating);
    memset(response,0,64u);memcpy(response,"CIN1",4u);
    response[4]=1u;response[5]=result;response[6]=s->mode;
    response[7]=(uint8_t)((s->flags&COMP_INPUT_HELD?1u:0u)|
        (app->board->microphone.running?2u:0u)|(comp_runtime_recording_owned(&app->runtime)?4u:0u)|
        (feedback.flags&COMP_CAPTURE_MARK_PENDING?8u:0u)|(feedback.flags&COMP_CAPTURE_MARK_CONFIRMED?16u:0u));
    comp_rec_put32(response+8u,request);comp_rec_put32(response+12u,s->sequence);
    comp_rec_put32(response+16u,s->event_ms);
    response[20]=(uint8_t)s->events;response[21]=(uint8_t)(s->events>>8u);
    response[22]=s->options;response[23]=feedback.state;
    comp_rec_put32(response+24u,app->runtime.record_token);
    comp_rec_put64(response+28u,app->recording_session_id);
    comp_rec_put32(response+36u,app->recording.pipeline.engine_bound?
        app->recording.capture.engine.bookmark_sequence:0u);
    memcpy(response+40u,app->recording.catalog.uid,12u);
    comp_rec_put64(response+52u,app->recording.catalog.epoch);
    comp_rec_put32(response+60u,comp_rec_crc(response,60u));
}
size_t comp_v11_product_input_request(comp_v11_product_app_t *app,const uint8_t *p,size_t n,
    bool busy,uint32_t now,uint8_t response[64])
{
    (void)now;
    if(!app||!p||n!=36u||memcmp(p,"CIN1",4u)||p[4]!=1u||p[5]>1u||
       !comp_rec_get32(p+8u)||memcmp(p+12u,app->recording.catalog.uid,12u)||
       comp_rec_get64(p+24u)!=app->recording.catalog.epoch||comp_rec_get32(p+32u)!=comp_rec_crc(p,32u))return 0u;
    uint8_t result=0u;
    if(p[5]) {
        if(p[6]>COMP_INPUT_PRESENTATION||(p[7]&~7u))result=2u;
        else if(busy||!comp_input_mode(&app->input,p[6],p[7],
            comp_runtime_recording_owned(&app->runtime),comp_wba_button_busy(&app->button)))result=1u;
    } else if(p[6]||p[7])result=2u;
    comp_v11_product_input_status(app,comp_rec_get32(p+8u),result,response);return 64u;
}
comp_segment_result_t comp_v11_product_recording_bookmark_result(const comp_v11_product_app_t *app,uint32_t token,uint32_t request)
{
    if(!app||!comp_wba_recording_product_capture_available(&app->recording)||token!=app->runtime.record_token)return COMP_SEG_BAD_STATE;
    return comp_wba_recording_product_bookmark_result(&app->recording,token,request);
}
static bool runtime_random(void *c,uint32_t *value)
{
    comp_v11_product_app_t *app=c;
    return app!=NULL && comp_v11_hal_random_u32(app->board,value);
}
#if COMPANION_WBA_SCREEN_ENABLED
static bool render(void *context,const comp_runtime_frame_t *request,uint8_t frame[5000])
{
    comp_v11_product_app_t *app=context;
    return app->assets_ready && comp_v11_product_render_pet_caption(app,request,frame);
}
static bool render_progress(void *context)
{ return render_io_progress((comp_v11_product_app_t *)context,32u); }
static bool presenter_cpu_progress(void *context)
{return render_io_progress((comp_v11_product_app_t *)context,33u);}
static bool render_opens_eyes(void *context)
{ return ((comp_v11_product_app_t *)context)->renderer.pending_opens_eyes; }
static void complete(void *context,uint32_t token,bool visible,uint32_t now)
{
    comp_v11_product_app_t *app=context;
#if COMP_V11_PANEL_PASSIVE_TRACE
    static uint32_t traced_activation;
    const comp_ssd1681_wba_stats_t *trace=&app->board->panel.stats;
    if (trace->visible_activation_count != traced_activation &&
        app->board->panel.status != COMP_SSD1681_WBA_ACTIVE) {
        traced_activation=trace->visible_activation_count;
        /* Emit after the transaction, only in an idle-audio diagnostic image.
         * No-change completions have no new activation and emit no event.
         * Bound this to the first 32 activations; no new SPI reads or IRQs. */
        if ((traced_activation<=32u ||
             (app->panel_debug_trace_until_ms!=0u &&
              (int32_t)(app->panel_debug_trace_until_ms-now)>0)) &&
            !app->board->microphone.running &&
            !app->board->playback_active && !app->runtime.prepare_pending &&
            !app->runtime.start_pending && !app->runtime.command_pending) {
            const comp_runtime_frame_t *f=&app->presenter.request;
            const comp_ssd1681_wba_window_t *w=&app->board->panel.window;
            char line[512];
            (void)snprintf(line,sizeof(line),
                "PANEL15 activation n=%lu outcome=%s decision=%u kind=%u blink=%u phase=%u window=%u,%u,%u,%u start_ms=%lu first_high_ms=%lu last_high_ms=%lu high_samples=%lu polls=%lu edges_valid=%u edges=%u poll_gap_ms=%lu visible_ms=%lu post_ms=%lu now=%lu\r\n",
                (unsigned long)traced_activation,visible?"completed":"failed",
                (unsigned)app->presenter.selection.decision,(unsigned)f->kind,
                (unsigned)f->blink_closed,(unsigned)(f->kind==COMP_RUNTIME_FRAME_HOLD?f->hold_bucket:f->motion.phase),
                (unsigned)w->x_start_byte,(unsigned)w->x_end_byte,
                (unsigned)w->y_start,(unsigned)w->y_end,
                (unsigned long)trace->visible_started_ms,
                (unsigned long)trace->visible_first_high_ms,
                (unsigned long)trace->visible_last_high_ms,
                (unsigned long)trace->visible_high_samples,
                (unsigned long)trace->visible_poll_samples,
                (unsigned)trace->visible_edges_available,(unsigned)trace->visible_edge_flags,
                (unsigned long)trace->visible_max_poll_gap_ms,
                (unsigned long)(visible?app->presenter.visible_completed_ms:0u),
                (unsigned long)(visible?trace->last_completed_ms-app->presenter.visible_completed_ms:0u),
                (unsigned long)now);
            comp_v11_hal_log(line);
            if (app->panel_debug_trace_until_ms!=0u &&
                (int32_t)(app->panel_debug_trace_until_ms-now)>0) {
                (void)snprintf(line,sizeof(line),
                    "PANEL19 frame n=%lu token=%lu valid=%u crc32=%08lx now=%lu\r\n",
                    (unsigned long)traced_activation,(unsigned long)token,
                    (unsigned)app->presenter.committed_valid,
                    (unsigned long)comp_v11_product_committed_crc(app),
                    (unsigned long)now);
                comp_v11_hal_log(line);
            }
        }
    }
    {
        static uint32_t traced_miss;
        if(trace->activation_start_misses!=traced_miss &&
           app->board->panel.status!=COMP_SSD1681_WBA_ACTIVE) {
            traced_miss=trace->activation_start_misses;
            if(traced_miss<=32u && !app->board->microphone.running &&
               !app->board->playback_active && !app->runtime.prepare_pending &&
               !app->runtime.start_pending && !app->runtime.command_pending) {
                const comp_runtime_frame_t *f=&app->presenter.request;
                const comp_ssd1681_wba_window_t *w=&trace->missed_window;
                char line[512];
                (void)snprintf(line,sizeof(line),
                    "PANEL18 recovery seq=%lu outcome=%s kind=%u blink=%u phase=%u op=%u ram_phase=%u original_window=%u,%u,%u,%u start_ms=%lu miss_ms=%lu polls=%lu high_samples=%lu edges=%u poll_gap_ms=%lu reset_ms=%lu profile_ms=%lu activate_ms=%lu ready_ms=%lu done_ms=%lu\r\n",
                    (unsigned long)traced_miss,visible?"completed":"failed",
                    (unsigned)f->kind,(unsigned)f->blink_closed,(unsigned)f->motion.phase,
                    (unsigned)trace->missed_operation,(unsigned)trace->missed_phase,
                    (unsigned)w->x_start_byte,(unsigned)w->x_end_byte,
                    (unsigned)w->y_start,(unsigned)w->y_end,
                    (unsigned long)trace->missed_started_ms,(unsigned long)trace->missed_at_ms,
                    (unsigned long)trace->missed_poll_samples,(unsigned long)trace->missed_high_samples,
                    (unsigned)trace->missed_edge_flags,(unsigned long)trace->missed_max_poll_gap_ms,
                    (unsigned long)trace->recovery_reset_ms,(unsigned long)trace->recovery_profile_ms,
                    (unsigned long)trace->recovery_activation_ms,(unsigned long)trace->recovery_ready_ms,
                    (unsigned long)now);
                comp_v11_hal_log(line);
            }
        }
    }
#endif
    /* An explicit, finite trace reports only a captured first intention.
     * Emit after the driver transaction, never inside I2C/IRQ/BUSY polling.
     * Failed and no-change outcomes stay distinct; software intent timing
     * alone does not qualify input/optical latency or QM17. */
    const comp_runtime_frame_t *observed=&app->presenter.request;
    if(observed->token==token && observed->trace_intent_kind!=0u &&
       app->panel_debug_trace_until_ms!=0u &&
       (int32_t)(app->panel_debug_trace_until_ms-now)>0 &&
       app->board->panel.status!=COMP_SSD1681_WBA_ACTIVE &&
       !app->board->microphone.running && !app->board->playback_active &&
       !app->runtime.prepare_pending && !app->runtime.start_pending &&
       !app->runtime.command_pending && !app->runtime.capture_active) {
        const comp_ssd1681_wba_stats_t *s=&app->board->panel.stats;
        const uint32_t requested=app->runtime.frame_requested_ms;
        const bool activation=comp_pet_trace_activation(requested,s->visible_started_ms,now);
        char line[256];
        (void)snprintf(line,sizeof(line),
            "PETTRACE token=%lu gen=%lu source=%u intent_ms=%lu request_ms=%lu activation=%u start_ms=%lu visible=%u visible_ms=%lu release_ms=%lu x=%u y=%u\r\n",
            (unsigned long)token,(unsigned long)observed->reaction_generation,
            (unsigned)observed->trace_intent_kind,(unsigned long)observed->trace_intent_ms,
            (unsigned long)requested,(unsigned)activation,
            (unsigned long)(activation?s->visible_started_ms:0u),(unsigned)visible,
            (unsigned long)(visible?app->presenter.visible_completed_ms:0u),
            (unsigned long)now,(unsigned)observed->gaze_x,(unsigned)observed->gaze_y);
        comp_v11_hal_log(line);
    }
    if(!visible && app->board->panel.error==COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT &&
        !app->board->microphone.running && !app->board->playback_active) {
        const comp_runtime_frame_t *f=&app->presenter.request;
        const comp_ssd1681_wba_window_t *w=&app->board->panel.window;
        char line[192];
        (void)snprintf(line,sizeof(line),
            "PANEL4 timeout kind=%u family=%u clean=%u blink=%u opens=%u action=%u phase=%u window=%u,%u,%u,%u seed=%08lX now=%lu wait=%lu\r\n",
            (unsigned)f->kind,(unsigned)f->family,(unsigned)f->family_clean,(unsigned)f->blink_closed,
            (unsigned)app->renderer.pending_opens_eyes,(unsigned)f->motion.action,(unsigned)f->motion.phase,
            (unsigned)w->x_start_byte,(unsigned)w->x_end_byte,(unsigned)w->y_start,(unsigned)w->y_end,
            (unsigned long)f->pet_seed,(unsigned long)now,
            (unsigned long)(HAL_GetTick()-app->board->panel.wait_started_ms));
        comp_v11_hal_log(line);
        comp_v11_hal_panel_failure_diagnostic(app->board);
    }
    (void)comp_runtime_renderer_complete(&app->renderer,token,visible);
    /* Diagnostic TX takes real foreground time. Optional choreography budgets
     * include that cost; qualified panel-visible time stays unchanged. */
    const uint8_t previous_chat_state=app->runtime.chat_caption_state;
    (void)comp_runtime_complete_frame_observed(&app->runtime,token,visible,HAL_GetTick(),
                                           app->presenter.visible_completed_ms,app->presenter.request_activated);
#ifdef COMPANION_WBA_BLE_LINKED
    if(previous_chat_state!=app->runtime.chat_caption_state)comp_v11_ble_pet_caption_changed();
#else
    (void)previous_chat_state;
#endif
}
#endif
static bool settings_write(void *c,uint32_t offset,const uint8_t *data,size_t length)
{
    return companion_spi_nor_stm32wba_partition_program(c,offset,data,length)==COMPANION_SPI_NOR_STM32WBA_OK;
}
static bool settings_erase(void *c)
{
    return companion_spi_nor_stm32wba_partition_erase_4k(c,0)==COMPANION_SPI_NOR_STM32WBA_OK;
}
static bool preferences_erase(void *c,uint32_t offset)
{ return companion_spi_nor_stm32wba_partition_erase_4k(c,offset)==COMPANION_SPI_NOR_STM32WBA_OK; }
static void apply_pet_profile(comp_v11_product_app_t *app)
{
    uint8_t h[16];uint32_t seed=comp_pet_profile_seed(app->pet_profile.uid);
    unsigned type=seed%16u;
    if(app->pet_profile.persisted && comp_pet_profile_read(&app->pet_profile,
        app->pet_profile.generation,0u,h,16u)) {
        type=h[1];seed=(uint32_t)h[8]|((uint32_t)h[9]<<8)|((uint32_t)h[10]<<16)|((uint32_t)h[11]<<24);
    }
    comp_runtime_set_personality(&app->runtime,type,seed);
}
static void mount_pet_profile(comp_v11_product_app_t *app)
{
    uint8_t uid[12];
    if(!app->storage_layout_ready || !comp_v11_hal_device_uid(uid) ||
       !companion_spi_nor_stm32wba_partition_init(&app->pet_profile_partition,&app->board->nor,
           COMP_WBA_NOR_PET_PROFILE_A,8192u))return;
    comp_pet_profile_port_t p={companion_spi_nor_stm32wba_partition_read,
        settings_write,preferences_erase,&app->pet_profile_partition};
    if(comp_pet_profile_mount(&app->pet_profile,&p,uid)==COMP_PET_STORE_OK)apply_pet_profile(app);
}
size_t comp_v11_product_pet_profile(comp_v11_product_app_t *app,const uint8_t *request,size_t n,
    bool other_busy,uint32_t now,uint8_t response[96])
{
    if(!app || !request || n<16u)return 0u;
    const comp_runtime_t *r=&app->runtime;
    const comp_wba_recording_pipeline_t *p=&app->recording.pipeline;
    bool idle=app->storage_layout_ready && app->recording_ready && !other_busy &&
        !app->board->microphone.running && !app->board->playback_active && !app->board->nor.erase_active &&
        !r->capture_active && !r->prepare_pending && !r->command_pending && !r->start_pending &&
        r->chat_caption_state!=COMP_PET_CHAT_ASSEMBLING && r->chat_caption_state!=COMP_PET_CHAT_PENDING &&
        r->chat_caption_state!=COMP_PET_CHAT_RESERVING &&
        !r->menu_pending && (p->state==COMP_PIPE_IDLE || p->state==COMP_PIPE_FINISHED);
    /* A write/readback error may have left a durable commit. Only an explicit
     * new INFO performs a read-only remount; never reset/format/replay a write. */
    if(idle && request[4]==0u && !app->pet_profile.mounted)mount_pet_profile(app);
    size_t result=comp_pet_profile_exchange(&app->pet_profile,request,n,idle,now,response);
    if(result && app->pet_profile.mounted &&
       (request[4]==0u || (request[4]==4u &&
        (response[5]==COMP_PET_STORE_OK || response[5]==COMP_PET_STORE_CLEANUP_PENDING))))apply_pet_profile(app);
    return result;
}
static void apply_preferences(comp_v11_product_app_t *app)
{
    const comp_preferences_values_t *v=&app->preferences.values;
    const comp_power_settings_values_t *p=&v->policy;
    comp_screen_menu_browser_state_t *b=&app->runtime.menu.browser;
    b->silent_auto_stop=p->silent_auto_stop;b->auto_reconnect=p->auto_reconnect;b->clock_24_hour=p->clock_24_hour;
    b->gaze_follow=p->gaze_follow;b->natural_blink=p->natural_blink;b->auto_sleep_minutes=p->idle_minutes;
    b->recording_limit_minutes=p->recording_limit_minutes;b->recorder_profile=p->recorder_profile;
    b->interaction_level=p->interaction_level;b->quiet_hours=p->quiet_hours;b->recording_gesture=p->recording_gesture;
    b->time_zone_offset_minutes=p->time_zone_offset_minutes;app->runtime.menu.language=(comp_screen_menu_language_t)v->locale;
    b->battery_fill=v->battery_fill;
    /* Reflect the persisted master mute in the existing volume row. Quiet
     * hours and the Quiet interaction mode retain their separate priority. */
    b->pet_volume=v->quiet_enabled?0u:v->volume;
    b->pet_muted=v->quiet_enabled || v->volume==0u;
    comp_runtime_set_discovery_seen(&app->runtime,v->pet_discovery_seen);
    (void)comp_motion_events_set_packed_axes(&app->board->motion,v->imu_screen_axes);
    (void)comp_audio_feedback_set_volume(&app->runtime.audio,v->volume);
    comp_runtime_set_quiet(&app->runtime,v->quiet_enabled);
#ifdef COMPANION_WBA_BLE_LINKED
    comp_v11_ble_apply_preferences(v);
    comp_v11_ble_settings_changed();
#endif
    /* Stored preferences still apply to every backend immediately. The
     * parked sleep image waits for wake or a real power/update alert. */
    if(app->runtime.surface!=COMP_SCREEN_SURFACE_LOW_POWER)++app->runtime.revision;
    ++app->runtime.menu.revision;
}
static bool save_preferences_record(comp_v11_product_app_t *app,const comp_preferences_values_t *v)
{
    if(!app || !app->settings_ready || app->board->microphone.running || app->board->nor.erase_active ||
       app->runtime.command_pending || app->runtime.start_pending || app->runtime.prepare_pending ||
       comp_wba_recording_product_recovering(&app->recording))return false;
#ifdef COMPANION_WBA_BLE_LINKED
    if(comp_v11_ble_storage_busy() || !companion_opus16_rt_workspace_available())return false;
#endif
    return comp_preferences_save(&app->preferences,v);
}
bool comp_v11_product_save_preferences(comp_v11_product_app_t *app,const comp_preferences_values_t *v)
{
    if(!save_preferences_record(app,v))return false;
    apply_preferences(app);return true;
}
bool comp_v11_product_restore_defaults(comp_v11_product_app_t *app)
{
    if(!app)return false;
    comp_preferences_values_t values;comp_preferences_defaults(&values);
    values.imu_screen_axes=app->preferences.values.imu_screen_axes;
    return comp_v11_product_save_preferences(app,&values);
}
bool comp_v11_product_apply_imu_axes(comp_v11_product_app_t *app,uint8_t packed)
{
    if (!app || !app->board || !comp_imu_screen_axes_valid(packed) ||
        (packed != 0u && (app->board->faults & COMP_V11_FAULT_IMU))) return false;
    comp_preferences_values_t values=app->preferences.values;
    values.imu_screen_axes=packed;
    return comp_v11_product_save_preferences(app,&values);
}
void comp_v11_product_settings(const comp_v11_product_app_t *app,uint8_t out[13])
{
    const comp_preferences_values_t *v=&app->preferences.values;
    comp_clock_t clock=app->clock;
    memset(out,0,13);out[0]=1;out[1]=v->locale;out[2]=v->quiet_enabled?1u:0u;
    out[4]=(uint8_t)v->policy.time_zone_offset_minutes;out[5]=(uint8_t)((uint16_t)v->policy.time_zone_offset_minutes>>8);
    if(v->policy.quiet_hours==0) {out[6]=23;out[7]=7;}
    else if(v->policy.quiet_hours==1) {out[6]=22;out[7]=8;}
    out[9]=v->policy.recorder_profile;
    comp_clock_poll(&clock,HAL_GetTick());
    if(clock.valid) {
        out[10]=(uint8_t)((clock.utc_seconds/3600u)%24u);
        out[11]=(uint8_t)((clock.utc_seconds/60u)%60u);
        out[12]=(uint8_t)(clock.utc_seconds%60u);
    } else out[10]=out[11]=out[12]=255u;
}
void comp_v11_product_calendar_settings(const comp_v11_product_app_t *app,uint8_t out[17])
{
    comp_v11_product_settings(app,out);
    const uint32_t seconds=comp_clock_unix(&app->clock,HAL_GetTick());
    for(unsigned i=0;i<4u;++i)out[13u+i]=(uint8_t)(seconds>>(i*8u));
}
bool comp_v11_product_apply_settings(comp_v11_product_app_t *app,const uint8_t *bytes,size_t n)
{
    comp_preferences_values_t v;
    if(!app || !bytes || (n!=10u && n!=13u && n!=17u) || bytes[0]!=1u || bytes[1]>2u ||
       bytes[2]>1u || bytes[3]!=0u || bytes[8]!=0u || bytes[9]>1u)return false;
    if(n>=13u && (bytes[10]>23u || bytes[11]>59u || bytes[12]>59u))return false;
    uint32_t seconds=0u;
    if(n==17u) {
        for(unsigned i=0;i<4u;++i)seconds|=(uint32_t)bytes[13u+i]<<(i*8u);
        if(!seconds || seconds%86400u!=(uint32_t)bytes[10]*3600u+
                (uint32_t)bytes[11]*60u+bytes[12])return false;
    }
    v=app->preferences.values;v.locale=bytes[1];v.policy.recorder_profile=bytes[9];
    v.quiet_enabled=bytes[2]!=0u;
    v.policy.time_zone_offset_minutes=(int16_t)((uint16_t)bytes[4]|((uint16_t)bytes[5]<<8));
    if(bytes[6]==0 && bytes[7]==0)v.policy.quiet_hours=2;
    else if(bytes[6]==23 && bytes[7]==7)v.policy.quiet_hours=0;
    else if(bytes[6]==22 && bytes[7]==8)v.policy.quiet_hours=1;
    else return false;
    /* Type may reconnect to sync the clock during a meeting. Clock-only
     * writes touch no NOR and do not interrupt capture. */
    if(memcmp(&v,&app->preferences.values,sizeof(v))!=0 &&
       !comp_v11_product_save_preferences(app,&v))return false;
    if(n>=13u) {
        if(n==17u)(void)comp_clock_sync_unix(&app->clock,seconds,HAL_GetTick());
        else (void)comp_clock_sync(&app->clock,bytes[10],bytes[11],bytes[12],HAL_GetTick());
#ifdef COMPANION_WBA_BLE_LINKED
        comp_v11_clock_checkpoint(&app->clock);
#endif
    }
    return true;
}
/* Every accepted menu action has a device backend and persistent settings. */
static bool local_setting(void *context,const comp_screen_menu_result_t *action,const comp_screen_menu_t *settings)
{
    comp_v11_product_app_t *app=context;
    comp_preferences_values_t values;
    if (!app || app->board->microphone.running || app->runtime.command_pending || app->runtime.start_pending) return false;
    if(!app->settings_ready)return false;
    values=app->preferences.values;
    if(action->action==COMP_SCREEN_MENU_ACTION_PET_DISCOVERY_SEEN) {
        values.pet_discovery_seen=true;
        if(!save_preferences_record(app,&values))return false;
        /* Saving a seen marker must not reapply radio/motion/audio settings
         * or produce an incidental status/page refresh. */
        comp_runtime_set_discovery_seen(&app->runtime,true);return true;
    }
    if(action->action==COMP_SCREEN_MENU_ACTION_PET_VOLUME_SET ||
       action->action==COMP_SCREEN_MENU_ACTION_PET_MUTE_TOGGLE) {
        if(action->action==COMP_SCREEN_MENU_ACTION_PET_VOLUME_SET) {
            if(action->browser_kind>100u || action->browser_kind%25u)return false;
            /* Zero is mute; retain the nonzero preset for a later unmute. */
            values.quiet_enabled=action->browser_kind==0u;
            if(action->browser_kind)values.volume=action->browser_kind;
        } else {
            const bool unmute=values.quiet_enabled || values.volume==0u;
            values.quiet_enabled=!unmute;
            if(unmute && values.volume==0u)values.volume=25u;
        }
        return comp_v11_product_save_preferences(app,&values);
    }
    if(action->action==COMP_SCREEN_MENU_ACTION_PET_VOLUME_NEXT) {
        /* The displayed 0% advances to25 even if a remote master mute kept
         * an older nonzero preset. An explicit volume choice can unmute. */
        values.volume=values.quiet_enabled?25u:
            values.volume>=100u?0u:(uint8_t)((values.volume/25u+1u)*25u);
        values.quiet_enabled=values.volume==0u;
        return comp_v11_product_save_preferences(app,&values);
    }
    if(action->action==COMP_SCREEN_MENU_ACTION_LANGUAGE_CHANGED) {
        values.locale=(uint8_t)settings->language;return comp_v11_product_save_preferences(app,&values);
    }
    if(action->action==COMP_SCREEN_MENU_ACTION_BROWSER_RESTORE_DEFAULTS) {
        return comp_v11_product_restore_defaults(app);
    }
#ifdef COMPANION_WBA_BLE_LINKED
    if(action->action!=COMP_SCREEN_MENU_ACTION_BROWSER_SETTING_CHANGED)
        return comp_v11_ble_menu(action->action);
#endif
    if (action->action!=COMP_SCREEN_MENU_ACTION_BROWSER_SETTING_CHANGED) return false;
    switch (action->browser_item) {
    case COMPANION_BROWSER_MENU_ITEM_GAZE_FOLLOW:
    case COMPANION_BROWSER_MENU_ITEM_NATURAL_BLINK:
    case COMPANION_BROWSER_MENU_ITEM_AUTO_SLEEP:
    case COMPANION_BROWSER_MENU_ITEM_RECORDING_LIMIT:
    case COMPANION_BROWSER_MENU_ITEM_INTERACTION_LEVEL:
    case COMPANION_BROWSER_MENU_ITEM_RECORDING_GESTURE:
    case COMPANION_BROWSER_MENU_ITEM_QUIET_HOURS:
    case COMPANION_BROWSER_MENU_ITEM_AUTO_RECONNECT:
    case COMPANION_BROWSER_MENU_ITEM_CLOCK_FORMAT:
    case COMPANION_BROWSER_MENU_ITEM_TIME_ZONE:
    case COMPANION_BROWSER_MENU_ITEM_RECORDER_PROFILE:
    case COMPANION_BROWSER_MENU_ITEM_AUTO_STOP:
    case COMPANION_BROWSER_MENU_ITEM_STATUS_BAR:
        break;
    default: return false;
    }
    values.policy.gaze_follow=settings->browser.gaze_follow;
    values.policy.natural_blink=settings->browser.natural_blink;
    values.policy.idle_minutes=settings->browser.auto_sleep_minutes;
    values.policy.recording_limit_minutes=settings->browser.recording_limit_minutes;
    values.policy.interaction_level=settings->browser.interaction_level;
    values.policy.recording_gesture=settings->browser.recording_gesture;
    values.policy.quiet_hours=settings->browser.quiet_hours;
    values.policy.silent_auto_stop=settings->browser.silent_auto_stop;
    values.policy.auto_reconnect=settings->browser.auto_reconnect;
    values.policy.clock_24_hour=settings->browser.clock_24_hour;
    values.policy.time_zone_offset_minutes=settings->browser.time_zone_offset_minutes;
    values.policy.recorder_profile=settings->browser.recorder_profile;
    values.battery_fill=settings->browser.battery_fill;
    return comp_v11_product_save_preferences(app,&values);
}
static comp_runtime_menu_dispatch_t local_action_begin(void *context,
    const comp_screen_menu_result_t *action,const comp_screen_menu_t *settings,uint32_t token)
{
    comp_v11_product_app_t *app=context;
    if(!app || !app->settings_ready)return COMP_RUNTIME_MENU_UNAVAILABLE;
    if(app->board->microphone.running || app->runtime.command_pending || app->runtime.start_pending || app->runtime.prepare_pending)
        return COMP_RUNTIME_MENU_BUSY;
    if(app->board->nor.erase_active)return COMP_RUNTIME_MENU_BUSY;
#ifdef COMPANION_WBA_BLE_LINKED
    if((action->action==COMP_SCREEN_MENU_ACTION_PET_DISCOVERY_SEEN ||
        action->action==COMP_SCREEN_MENU_ACTION_PET_VOLUME_NEXT ||
        action->action==COMP_SCREEN_MENU_ACTION_PET_VOLUME_SET ||
        action->action==COMP_SCREEN_MENU_ACTION_PET_MUTE_TOGGLE ||
        action->action==COMP_SCREEN_MENU_ACTION_LANGUAGE_CHANGED ||
        action->action==COMP_SCREEN_MENU_ACTION_BROWSER_RESTORE_DEFAULTS ||
        action->action==COMP_SCREEN_MENU_ACTION_BROWSER_SETTING_CHANGED) &&
       (comp_v11_ble_storage_busy() || !companion_opus16_rt_workspace_available()))
        return COMP_RUNTIME_MENU_BUSY;
    if(action->action!=COMP_SCREEN_MENU_ACTION_LANGUAGE_CHANGED &&
       action->action!=COMP_SCREEN_MENU_ACTION_PET_DISCOVERY_SEEN &&
       action->action!=COMP_SCREEN_MENU_ACTION_PET_VOLUME_NEXT &&
        action->action!=COMP_SCREEN_MENU_ACTION_PET_VOLUME_SET &&
        action->action!=COMP_SCREEN_MENU_ACTION_PET_MUTE_TOGGLE &&
       action->action!=COMP_SCREEN_MENU_ACTION_BROWSER_RESTORE_DEFAULTS &&
       action->action!=COMP_SCREEN_MENU_ACTION_BROWSER_SETTING_CHANGED)
        return comp_v11_ble_menu_begin(action->action,token);
#else
    (void)token;
#endif
    return local_setting(context,action,settings)?COMP_RUNTIME_MENU_COMPLETE:COMP_RUNTIME_MENU_FAILED;
}
void comp_v11_product_app_init(comp_v11_product_app_t *app,comp_v11_hal_t *board,const comp_runtime_config_t *ports)
{
    comp_runtime_config_t runtime={0};
    companion_screen_assets_stm32wba_config_t assets;
#if COMPANION_WBA_SCREEN_ENABLED
    comp_screen_presenter_wba_config_t presenter;
#endif
    comp_power_settings_port_t settings;
    if (!app || !board) return;
#if COMP_V11_PANEL_SOFTWARE_SPI && COMP_V11_PANEL_STARTUP_READBACK
    panel_audit_done = false;
#endif
    memset(app,0,sizeof(*app)); app->board=board;
#if COMP_WBA_PACKED_OLD_FRAME && COMPANION_WBA_SCREEN_ENABLED
    app->panel_committed=app->panel_committed_storage.bytes;
#endif
    comp_wba_button_init(&app->button,comp_v11_hal_key_pressed(),HAL_GetTick());
    if(!COMPANION_WBA_SCREEN_ENABLED)(void)comp_v11_hal_take_key_edges(board);
    comp_preferences_defaults(&app->preferences.values);
    if (ports) runtime=*ports;
    else {
        runtime.context=app; runtime.menu_action_begin=local_action_begin;
        runtime.recording_prepare=recording_prepare; runtime.recording_ready=recording_is_ready;
        runtime.recording_control=recording_control; runtime.random_u32=runtime_random;
    }
    runtime.speaker=board->speaker_ready?&board->speaker:NULL;
    comp_runtime_init(&app->runtime,&runtime,HAL_GetTick());
    /* Inactivity auto-stop is opt-in, never the default for a meeting. */
    app->runtime.menu.browser.silent_auto_stop=false;
    companion_spi_nor_stm32wba_partition_t whole;
    app->storage_layout_ready=companion_spi_nor_stm32wba_partition_init(&whole,&board->nor,0u,COMP_WBA_NOR_TOTAL_BYTES)&&
        comp_wba_workspace_layout_valid(companion_spi_nor_stm32wba_partition_read,&whole);
    settings=(comp_power_settings_port_t){companion_spi_nor_stm32wba_partition_read,
        settings_write,settings_erase,&app->settings_partition};
    if (app->storage_layout_ready && companion_spi_nor_stm32wba_partition_init(&app->settings_partition,&board->nor,COMP_WBA_NOR_POWER_SETTINGS,4096u) &&
        comp_power_settings_store_mount(&app->settings,&settings)==COMP_POWER_SETTINGS_OK) {
        const comp_power_settings_values_t *v=&app->settings.values;
        app->runtime.menu.browser.gaze_follow=v->gaze_follow;
        app->runtime.menu.browser.natural_blink=v->natural_blink;
        app->runtime.menu.browser.auto_sleep_minutes=v->idle_minutes;
        app->runtime.menu.browser.recording_limit_minutes=v->recording_limit_minutes;
        app->runtime.menu.browser.interaction_level=v->interaction_level;
        app->runtime.menu.browser.recording_gesture=v->recording_gesture;
        app->runtime.menu.browser.quiet_hours=v->quiet_hours;
        comp_runtime_set_quiet(&app->runtime,false);
    }
    /* Namespace ownership is checked before any recording/prefs initialization.
     * Reserved bytes with an unknown/failed root are never silently erased. */
    if(app->storage_layout_ready)app->storage_layout_ready=companion_spi_nor_stm32wba_partition_init(
        &app->recording_identity_partition,&board->nor,COMP_WBA_NOR_RECORDING_IDENTITY_BASE,
        COMP_WBA_NOR_RECORDING_IDENTITY_BYTES)&&identity_mount(app);
    comp_preferences_port_t prefs={companion_spi_nor_stm32wba_partition_read,settings_write,preferences_erase,&app->preferences_partition};
    if(app->storage_layout_ready && companion_spi_nor_stm32wba_partition_init(&app->preferences_partition,&board->nor,PREFERENCES_BASE,8192u) &&
       comp_preferences_mount(&app->preferences,&prefs)) {
        app->settings_ready=true;
        if(!app->preferences.persisted && app->settings.generation) {
            comp_preferences_values_t migrated=app->preferences.values;migrated.policy=app->settings.values;
            (void)comp_preferences_save(&app->preferences,&migrated);
        }
        apply_preferences(app);
    }
    mount_pet_profile(app); /* Read-only. Does not claim unknown occupied media. */
    /* Foreground boot polls mount/recover the segmented catalog. Capture and
     * CRV2 remain unavailable until the existing WUS2 lease is reconciled. */
    if(!ports)recording_namespace_poll(app);
#if COMPANION_WBA_SCREEN_ENABLED
    comp_runtime_renderer_init(&app->renderer,comp_runtime_resources_read,&app->resources);
    comp_runtime_renderer_set_ui_reader(&app->renderer,comp_runtime_resources_read_ui);
    comp_runtime_renderer_set_progress(&app->renderer,render_progress,app);
#endif
    companion_screen_assets_stm32wba_init(&app->asset_reader);
    /* Static bank extent comes from its build profile; system data follows it. */
    assets=(companion_screen_assets_stm32wba_config_t){COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA55,
        COMP_WBA_NOR_UI_BYTES,resource_read,app};
    if (companion_spi_nor_stm32wba_partition_init(&app->resource_partition,&board->nor,0,COMP_WBA_NOR_UI_BYTES) &&
        companion_screen_assets_stm32wba_bind(&app->asset_reader,&app->asset_store,&assets)) {
#if COMPANION_WBA_SCREEN_ENABLED
        (void)companion_screen_assets_stm32wba_set_cache(&app->asset_reader,app->asset_cache,sizeof(app->asset_cache));
#endif
        /* Capture retains the same resource identity/CRC mount through direct
         * bounded NOR reads, without a resident display-only read cache. */
        app->assets_ready=comp_runtime_resources_mount(&app->resources,&app->asset_store);
    }
#if COMPANION_WBA_SCREEN_ENABLED
    presenter=(comp_screen_presenter_wba_config_t){&board->panel,render,complete,app,
        app->panel_committed,app->panel_staging,UINT8_MAX,render_opens_eyes};
    (void)comp_screen_presenter_wba_init(&app->presenter,&presenter);
    comp_screen_presenter_wba_set_progress(&app->presenter,presenter_cpu_progress);
#else
    app->presenter.status=COMP_SCREEN_PRESENTER_WBA_NOT_READY;
#endif
}
static void imu_wake_activity(comp_v11_product_app_t *app,uint32_t now)
{
    const comp_lsm6dso_t *imu=&app->board->imu;
    if(imu->wake_sequence==app->last_imu_wake_sequence)return;
    app->last_imu_wake_sequence=imu->wake_sequence;
    if(imu->state==COMP_IMU_READY && (imu->wake_source&COMP_LSM6DSO_WAKE_DETECTED) && now-imu->reset_ms<250u)
    {
        comp_runtime_wake_from(&app->runtime,now,COMP_RUNTIME_WAKE_MOTION);
        comp_input_note(&app->input,COMP_INPUT_WAKE,now);
    }
}
bool comp_v11_product_update_idle_policy(comp_v11_product_app_t *app)
{
    if (!app || !app->board) return false;
    comp_runtime_t *r=&app->runtime; comp_power_policy_t *p=&app->board->power;
    bool audio_pending=r->prepare_pending || r->start_pending || r->command_pending ||
        r->capture_active || r->stop_pending || app->board->microphone.running ||
        comp_wba_recording_product_recovering(&app->recording) ||
        (!app->recording_ready&&comp_wba_recording_product_state(&app->recording)==COMP_WBA_RECORDING_PREPARING) ||
        (app->recording.media_ready&&comp_wba_recording_pipeline_storage_busy(&app->recording.pipeline));
    comp_power_policy_set_blocker(p,COMP_POWER_BLOCKER_MIC_CAPTURE,audio_pending);
    comp_power_policy_set_blocker(p,COMP_POWER_BLOCKER_PLAYBACK,
        app->board->playback_active || app->board->services.find_active ||
        comp_audio_feedback_busy(&r->audio));
    comp_power_policy_set_blocker(p,COMP_POWER_BLOCKER_TOUCH_CONTACT,r->touch_contact);
    comp_power_policy_set_blocker(p,COMP_POWER_BLOCKER_TOUCH_CONFIRMATION,
        r->taps.pending || r->gesture.tap_pending || comp_v11_hal_touch_pending());
    comp_power_policy_set_blocker(p,COMP_POWER_BLOCKER_BUTTON,comp_wba_button_busy(&app->button));
    /* An unavailable display cannot confirm a visible sleep frame. Retain
     * the user's real inactivity timer and every audio/storage/input vote. */
    bool unavailable=!COMPANION_WBA_SCREEN_ENABLED || !app->assets_ready || app->presenter.status==COMP_SCREEN_PRESENTER_WBA_NOT_READY ||
        comp_ssd1681_wba_status(&app->board->panel)==COMP_SSD1681_WBA_ERROR;
    bool idle= r->menu.browser.auto_sleep_minutes!=0u &&
        HAL_GetTick()-r->last_activity_ms >= (uint32_t)r->menu.browser.auto_sleep_minutes*60000u;
    comp_power_policy_set_blocker(p,COMP_POWER_BLOCKER_MENU_TIMER,
        unavailable ? !idle : r->surface!=COMP_SCREEN_SURFACE_LOW_POWER);
    comp_power_policy_set_blocker(p,COMP_POWER_BLOCKER_UI_PENDING,unavailable ? !idle :
        (r->frame_outstanding || r->visible_revision!=r->revision || r->visible_surface!=COMP_SCREEN_SURFACE_LOW_POWER));
    comp_power_policy_set_blocker(p,COMP_POWER_BLOCKER_SCREEN_WAIT,
        (!unavailable && app->presenter.status==COMP_SCREEN_PRESENTER_WBA_ACTIVE) ||
        comp_ssd1681_wba_status(&app->board->panel)==COMP_SSD1681_WBA_ACTIVE);
    comp_power_policy_set_blocker(p,COMP_POWER_BLOCKER_BATTERY_SAMPLE,
        comp_wba_power_monitor_busy(&app->board->power_monitor));
    return comp_power_policy_idle_requested(p);
}
static void capture_phase_duration(comp_v11_product_app_t *app,uint32_t started,uint32_t *maximum)
{
    if(!app->recording.media_ready||!app->recording.capture.engine.microphone_active)return;
    /* A late start belongs only to the portion after the mic actually starts. */
    if((int32_t)(started-app->capture_started_ms)<0)started=app->capture_started_ms;
    uint32_t elapsed=HAL_GetTick()-started;
    if(elapsed>*maximum)*maximum=elapsed;
}
/* The observation path borrows only the screen, never recorder/radio state.
 * Screen BUSY is allowed while one queued press waits for its transaction;
 * all actual recording/transfer/update/storage work cancels the observation. */
static bool panel_key_safe(const comp_v11_product_app_t *app)
{
    const comp_v11_hal_t *b=app->board;
    const comp_runtime_t *r=&app->runtime;
    return app->assets_ready && b->display_power.state==COMP_V11_POWER_READY &&
        !b->nor.erase_active && !b->microphone.running && !b->playback_active &&
        !r->prepare_pending && !r->start_pending && !r->command_pending &&
        !r->capture_active && !r->stop_pending &&
        r->surface==COMP_SCREEN_SURFACE_HOME && r->visible_surface==COMP_SCREEN_SURFACE_HOME &&
        (b->power.blockers & (COMP_POWER_BLOCKER_MIC_CAPTURE |
         COMP_POWER_BLOCKER_RECORDING_TRANSFER | COMP_POWER_BLOCKER_STORAGE |
         COMP_POWER_BLOCKER_UPDATE | COMP_POWER_BLOCKER_BOND_NVM |
         COMP_POWER_BLOCKER_PLAYBACK))==0u;
}

bool comp_v11_product_panel_debug_key(comp_v11_product_app_t *app,bool enabled,uint32_t now)
{
    if (!app) return false;
    if (!enabled) {
        if (app->panel_debug_catch_until_ms!=0u) {
            app->panel_debug_catch_until_ms=0u;
            app->panel_debug_catch_reply=4u;
        }
        app->panel_debug_key_until_ms=0u;
        if (app->panel_debug_replay_state!=0u) app->panel_debug_hold_until_ms=0u;
        app->panel_debug_replay_state=0u;
        return true;
    }
    if (!panel_key_safe(app) || app->runtime.touch_contact || comp_wba_button_busy(&app->button) ||
        app->panel_debug_replay_state!=0u || !app->presenter.committed_valid) return false;
    app->panel_debug_key_until_ms=now+120000u;
    app->panel_debug_same_partial=0u;
    app->panel_debug_replay_reply=1u;
    return true;
}

static bool panel_debug_queue_frozen(comp_v11_product_app_t *app,uint32_t now,
                                     uint8_t mode)
{
    if (!app || !panel_key_safe(app) || app->runtime.touch_contact ||
        comp_wba_button_busy(&app->button) ||
        app->panel_debug_catch_until_ms!=0u || app->panel_debug_catch_reply!=0u ||
        (app->panel_debug_replay_state!=0u && app->panel_debug_replay_state!=3u) ||
        !app->presenter.committed_valid) return false;
    /* State3 is a completed-picture observation, not a pending transaction.
     * Preserve that freeze while admitting the explicitly requested next
     * experiment. RUN would allow a normal pet frame between F7 and SAME.
     * Queued/active replay remains rejected; product operations still cancel. */
    app->panel_debug_key_until_ms=0u;
    app->panel_debug_same_partial=mode; /* 0 physical key, 1 SAME, 2 BASE */
    app->panel_debug_replay_id++;
    app->panel_debug_replay_state=1u;
    app->panel_debug_hold_until_ms=now+30000u;
    app->panel_debug_replay_reply=2u;
    return true;
}

bool comp_v11_product_panel_debug_same(comp_v11_product_app_t *app,uint32_t now)
{ return panel_debug_queue_frozen(app,now,1u); }

bool comp_v11_product_panel_debug_base(comp_v11_product_app_t *app,uint32_t now)
{ return panel_debug_queue_frozen(app,now,2u); }

bool comp_v11_product_panel_debug_catch(comp_v11_product_app_t *app,uint32_t now)
{
    if (!app || !panel_key_safe(app) || app->runtime.touch_contact ||
        comp_wba_button_busy(&app->button) || app->panel_debug_key_until_ms!=0u ||
        app->panel_debug_replay_state!=0u || app->panel_debug_hold_until_ms!=0u ||
        app->panel_debug_catch_until_ms!=0u || app->panel_debug_catch_reply!=0u)
        return false;
    /* A current ERROR baseline is not replayed. The normal presenter may
     * recover under its existing policy; a NEW failed completion ends this
     * one observation. An already completed old full cannot trigger it. */
    app->panel_debug_catch_full_count=app->board->panel.stats.completed_full;
    app->panel_debug_catch_failures=app->presenter.stats.failed_completions;
    app->panel_debug_catch_until_ms=now+30000u;
    app->panel_debug_catch_reply=1u;
    return true;
}

static void panel_full_observation_poll(comp_v11_product_app_t *app,uint32_t now)
{
    if (app->panel_debug_catch_until_ms==0u) return;
    uint8_t reply=0u;
    if (!panel_key_safe(app) || app->runtime.touch_contact ||
        comp_wba_button_busy(&app->button) || app->panel_debug_key_until_ms!=0u ||
        app->panel_debug_replay_state!=0u || app->panel_debug_hold_until_ms!=0u)
        reply=4u;
    else if (app->presenter.stats.failed_completions!=app->panel_debug_catch_failures)
        reply=5u;
    else if ((int32_t)(now-app->panel_debug_catch_until_ms)>=0)
        reply=3u;
    else if (app->board->panel.stats.completed_full!=app->panel_debug_catch_full_count) {
        if (app->board->panel.status!=COMP_SSD1681_WBA_COMPLETE ||
            app->board->panel.error!=COMP_SSD1681_WBA_ERROR_NONE ||
            app->presenter.status!=COMP_SCREEN_PRESENTER_WBA_IDLE ||
            !app->presenter.committed_valid || !app->presenter.committed_surface_valid ||
            app->presenter.committed_surface!=COMP_SCREEN_SURFACE_HOME)
            reply=5u;
        else {
            /* This runs immediately after presenter service, BEFORE normal
             * take_frame/submit in the SAME poll. A host HOLD sent after the
             * completion log can be too late to exclude the next pet frame.
             * Borrow only the existing finite hold and existing 5000B image. */
            app->panel_debug_hold_until_ms=now+30000u;
            reply=2u;
        }
    }
    if (reply!=0u) {
        app->panel_debug_catch_until_ms=0u;
        app->panel_debug_catch_reply=reply;
    }
}

static void panel_key_observation_poll(comp_v11_product_app_t *app,uint32_t now)
{
    if (app->panel_debug_key_until_ms!=0u &&
        (int32_t)(now-app->panel_debug_key_until_ms)>=0) {
        app->panel_debug_key_until_ms=0u;
        if (app->panel_debug_replay_state==0u) app->panel_debug_replay_reply=6u;
    }
    if ((app->panel_debug_key_until_ms!=0u || app->panel_debug_replay_state!=0u) && !panel_key_safe(app)) {
        (void)comp_v11_product_panel_debug_key(app,false,now);
        app->panel_debug_replay_reply=7u;
        return;
    }
    if (app->panel_debug_replay_state==1u) {
        if ((int32_t)(now-app->panel_debug_hold_until_ms)>=0) {
            app->panel_debug_replay_state=0u;app->panel_debug_hold_until_ms=0u;
            app->panel_debug_replay_reply=5u; /* No delayed automatic retry. */
        } else if (app->presenter.status==COMP_SCREEN_PRESENTER_WBA_IDLE &&
                   !comp_v11_hal_panel_busy() &&
                   (app->board->power.blockers & COMP_POWER_BLOCKER_BATTERY_SAMPLE)==0u) {
            const bool started=app->panel_debug_same_partial==1u?
                comp_screen_presenter_wba_debug_replay_same_partial(&app->presenter,now):
                app->panel_debug_same_partial==0u?
                comp_screen_presenter_wba_debug_replay_quick_full(&app->presenter,now):
                app->panel_debug_same_partial==3u?
                comp_screen_presenter_wba_debug_replay_flashing_full(&app->presenter,now):
                comp_screen_presenter_wba_debug_replay_baseline(&app->presenter,now);
            if (started) {
                app->panel_debug_replay_state=2u;
                app->panel_debug_hold_until_ms=now+30000u;
                app->panel_debug_replay_reply=3u;
            } else {
                app->panel_debug_replay_state=(app->panel_debug_same_partial==0u || app->panel_debug_same_partial==3u)?0u:3u;
                app->panel_debug_hold_until_ms=(app->panel_debug_same_partial==0u || app->panel_debug_same_partial==3u)?0u:now+12000u;
                app->panel_debug_replay_reply=5u;
            }
        }
    } else if (app->panel_debug_replay_state==2u && app->presenter.status==COMP_SCREEN_PRESENTER_WBA_IDLE) {
        /* Both physical full-refresh keys resume normally after real completion.
         * Only explicit BASE/SAME observations retain their finite pause. */
        app->panel_debug_replay_state=(app->panel_debug_same_partial==0u || app->panel_debug_same_partial==3u)?0u:3u;
        app->panel_debug_hold_until_ms=(app->panel_debug_same_partial==0u || app->panel_debug_same_partial==3u)?0u:now+12000u;
        app->panel_debug_replay_reply=app->presenter.committed_valid?4u:5u;
    } else if (app->panel_debug_replay_state==3u &&
               (int32_t)(now-app->panel_debug_hold_until_ms)>=0) {
        app->panel_debug_replay_state=0u;app->panel_debug_hold_until_ms=0u;
    }
}

void comp_v11_product_app_poll(comp_v11_product_app_t *app)
{
#if COMPANION_WBA_DUAL_PAIR_CAPTURE
    if(comp_v11_dual_pair_owned(app)) {
        comp_v11_dual_pair_poll(app);
#ifdef COMPANION_WBA_BLE_LINKED
        comp_v11_ble_poll(); /* Existing stack stays serviced; no radio mode change. */
#endif
        return; /* Engineering window owns the idle PCM ring; no UI/NOR writer. */
    }
#endif
#if COMPANION_WBA_SCREEN_ENABLED
    comp_runtime_frame_t frame;
#endif
    uint32_t now=HAL_GetTick();
    if(app->pet_profile.writing)comp_pet_profile_expire(&app->pet_profile,now);
    comp_v11_hal_t *board=app->board;
    bool was_sleeping=COMPANION_WBA_SCREEN_ENABLED && app->runtime.surface==COMP_SCREEN_SURFACE_LOW_POWER;
    /* Include time between foreground calls; only an actual audio service or
     * mic start resets the deadline anchor. Long resource reads yield below. */
    (void)capture_deadline_check(app,4u);
    app->capture_cycle_started_ms=now;
    identity_entropy_poll(app);
    recording_namespace_poll(app);
    if(app->recording_fault_recovery_pending)recording_fault_recovery_poll(app);
    recording_boot_retry_poll(app,now);
#ifdef COMPANION_WBA_BLE_LINKED
    comp_v11_clock_poll(&app->clock,now,!board->microphone.running &&
        !app->runtime.command_pending && !app->runtime.start_pending);
#endif
    /* Quiet hours use the true local 24h clock even when display uses 12h. */
    comp_runtime_local_hour(&app->runtime,app->clock.valid,
        comp_clock_local_hour(&app->clock,app->runtime.menu.browser.time_zone_offset_minutes,now));
    board->services.playback_inhibited=board->microphone.running || app->runtime.start_pending ||
        app->runtime.command_pending || app->runtime.audio.quiet ||
        (board->power.blockers & COMP_POWER_BLOCKER_UPDATE) != 0u ||
        comp_audio_feedback_busy(&app->runtime.audio);
    board->power_sampling_inhibited=app->runtime.prepare_pending || app->runtime.start_pending ||
        app->runtime.command_pending;
    board->input_taps_requested=app->input.mode==COMP_INPUT_DICTATION&&
        (app->input.options&COMP_INPUT_UNDO)!=0u;
    if(board->microphone.running)(void)capture_progress(app,20u);
    uint32_t phase_started=HAL_GetTick();
#if defined(COMPANION_WBA_BLE_LINKED) && defined(__arm__)
    uint8_t wall_hal=comp_v11_ota_gatt_wall_context(COMP_OTA_WALL_PRODUCT_HAL);
#endif
    comp_cpu_stage_span_t bulk_hal=comp_v11_cpu_transfer_stage_begin();
    comp_v11_hal_poll(board);
    comp_v11_cpu_transfer_stage_end(COMP_BULK_CPU_HAL,bulk_hal);
#if defined(COMPANION_WBA_BLE_LINKED) && defined(__arm__)
    (void)comp_v11_ota_gatt_wall_context(wall_hal);
#endif
    capture_phase_duration(app,phase_started,&app->max_capture_hal_ms);
    phase_started=HAL_GetTick();
#if defined(COMPANION_WBA_BLE_LINKED) && defined(__arm__)
    uint8_t wall_recorder=comp_v11_ota_gatt_wall_context(COMP_OTA_WALL_PRODUCT_RECORDER);
#endif
    if (app->recording.boot_phase) {
        capture_validate(app);
        if(!app->recording.media_ready||!app->recording.capture.engine.microphone_active)
            comp_wba_recording_product_poll(&app->recording);
        /* A full encode owns a fresh checked capture checkpoint below.
         * Do not append it to the HAL/input time already spent this turn.
         * The first PCM half remains a bounded RAM-only staging operation. */
        else if(comp_wba_recording_product_pcm_staging_pending(&app->recording))
            (void)recording_work_poll(app,HAL_GetTick()-app->capture_cycle_started_ms,true);
        if(app->silence_stop_requested) {
            app->silence_stop_requested=false;
            if(app->runtime.capture_active)(void)comp_runtime_record_stop(&app->runtime,COMP_RECORD_STOP_SILENCE,HAL_GetTick());
        }
    }
    /* Runtime remount can change readiness without a new lease callback.
     * Publish it before BLE/update admission checks on this foreground turn. */
    app->recording_ready=app->recording.ready;
    if(!board->microphone.running) {
        bool prime_allowed=!board->playback_active&&!app->runtime.capture_active&&
            !app->runtime.prepare_pending&&!app->runtime.start_pending&&
            !app->runtime.command_pending&&!app->runtime.stop_pending&&
            companion_opus16_rt_workspace_available();
#ifdef COMPANION_WBA_BLE_LINKED
        prime_allowed=prime_allowed&&!comp_v11_ble_storage_busy()&&comp_v11_ble_recording_recovery_idle();
#endif
        comp_wba_recording_product_prime(&app->recording,prime_allowed);
    }
#if defined(COMPANION_WBA_BLE_LINKED) && defined(__arm__)
    (void)comp_v11_ota_gatt_wall_context(wall_recorder);
#endif
    capture_phase_duration(app,phase_started,&app->max_capture_recorder_ms);
    /* PDM conversion can consume the early 2ms dispatch slot at a lower
     * core clock. Service the existing capture checkpoint BEFORE radio/UI
     * work rather than waiting until their DMA admission window has closed.
     * This reuses the normal microphone/deadline/DMA gates; no longer slice,
     * extra PCM queue, skipped sample or reduced codec quality is admitted. */
    (void)capture_progress(app,21u);
    (void)capture_deadline_check(app,5u);
    app->capture_cycle_started_ms=HAL_GetTick();
#ifdef COMPANION_WBA_BLE_LINKED
    /* Drain captured PCM first; radio work is included in the same measured
     * foreground deadline as encoding, display and inputs. */
    phase_started=HAL_GetTick();
#if defined(__arm__)
    uint8_t wall_previous=comp_v11_ota_gatt_wall_context(COMP_OTA_WALL_BLE_OTHER);
#endif
    {
        /* Capture-only service observation. Start/normal drain run outside
         * this span; an inactive begin never acquires a later owner. */
        comp_cpu_stage_span_t cpu_service=(board->microphone.running||comp_cpu_bulk_owned())?
            comp_cpu_detail_begin():(comp_cpu_stage_span_t){0};
    comp_v11_ble_poll();
        comp_cpu_detail_end(COMP_CPU_STAGE_BLE_SERVICE,cpu_service,true);
    }
#if defined(__arm__)
    (void)comp_v11_ota_gatt_wall_context(wall_previous);
#endif
    capture_phase_duration(app,phase_started,&app->max_capture_ble_ms);
#endif
    /* BLE ACK/delete and resumed erase can change the journal without a new
     * recorder callback. Refresh the tiny catalog snapshot after radio work. */
    if(comp_wba_recording_product_readable(&app->recording))recording_catalog(app);
    /* Directory I/O may advance the foreground clock. Touch owns the
     * higher-priority input slot and must start from its actual dispatch
     * time, including in builds without the BLE port. */
    now=HAL_GetTick();
#if COMPANION_WBA_SCREEN_ENABLED
    if (board->touch.read_count!=app->last_touch_count) {
        app->last_touch_count=board->touch.read_count;
        comp_runtime_touch(&app->runtime,&board->touch_sample,board->touch.read_count,board->touch_ack,now);
    } else if (!board->touch_ack && (app->runtime.touch_contact ||
        (app->runtime.menu.flags & COMP_SCREEN_MENU_FLAG_TOUCH_OK))) {
        /* Failed reads do not advance the HAL's successful-report counter.
         * Availability loss must not be discarded as that report's duplicate,
         * or leave a phantom finger/hold blocking idle behavior and sleep. */
        comp_runtime_touch_unavailable(&app->runtime);
    }
#endif
    /* A touch/menu callback can synchronously save/read back preferences.
     * Recheck age after it returns so old motion and battery/reference
     * data cannot inherit the earlier, still-fresh dispatch timestamp. */
    now=HAL_GetTick();
    imu_wake_activity(app,now);
    if (board->motion_event_flags && board->motion_event_ms!=app->last_motion_ms) {
        app->last_motion_ms=board->motion_event_ms;
        /* The HAL's event latch survives a long foreground/bus pause.
         * Consume it once, but do not turn an expired pickup into a late
         * wake/reply or renew carrying from an old heartbeat. Match the
         * existing services.motion_flags 250ms freshness contract using
         * the actual post-input clock, rather than the HAL/radio entry tick. */
        if(now-board->motion_event_ms<250u) {
            /* Both local inputs use the same durable mark path. A tap never
             * starts/stops capture, and an idle/pre-START latch cannot become
             * a mark in the next session. Consume each HAL event only once. */
            uint8_t input_motion=board->motion_event_flags;
            if((int32_t)(board->motion_event_ms-app->capture_started_ms)<0)
                input_motion&=127u;
            recording_input_apply(app,comp_input_motion(&app->input,input_motion,&board->imu_sample,
                board->motion.tilt,comp_runtime_recording_owned(&app->runtime)),now);
            uint8_t pose=(uint8_t)(board->motion_event_flags&~COMP_MOTION_DOUBLE_TAP);
            if(pose)comp_runtime_motion_pose(&app->runtime,pose,board->motion.orientation,
                board->motion.tilt,board->motion_event_ms,now);
        }
    }
    if(app->input.mode==COMP_INPUT_DICTATION&&now-board->imu_sample.timestamp_ms<100u)
        recording_input_apply(app,comp_input_motion(&app->input,0u,&board->imu_sample,
            board->motion.tilt,comp_runtime_recording_owned(&app->runtime)),now);
    comp_wba_power_snapshot_t power=comp_wba_power_monitor_snapshot(&board->power_monitor,now);
    comp_wba_power_monitor_recording_guard(&board->power_monitor,now);
    if(board->power_monitor.recording_power_blocked && comp_runtime_recording_owned(&app->runtime))
        (void)comp_runtime_record_stop(&app->runtime,COMP_RECORD_STOP_LOW_BATTERY,now);
    uint32_t status=comp_clock_status(&app->clock,app->runtime.menu.browser.time_zone_offset_minutes,
        app->runtime.menu.browser.clock_24_hour,now);
    uint16_t cell_mv=power.voltage_valid?power.millivolts:0u;
    if (power.percent_valid) status|=(1u<<17)|((uint32_t)power.percent<<24);
#if COMPANION_WBA_BATTERY_LINEAR_ESTIMATE
    if(!power.percent_valid && board->power_monitor.raw_diagnostic) {
        cell_mv=comp_v11_battery_adc_cell_estimate(now);
        if(cell_mv) {
            /* Listener product estimate, explicitly authorized by Owner.
             * This is display-only: power snapshot/BAS/OTA stay unqualified. */
            uint32_t pct=cell_mv<=2850u?0u:cell_mv>=4150u?100u:
                ((uint32_t)(cell_mv-2850u)*100u+650u)/1300u;
            status|=(1u<<17)|COMP_SCREEN_STATUS_ESTIMATED_BATTERY|(pct<<24);
        }
    }
#endif
    if (power.charger_valid && power.charger_present) status|=COMP_SCREEN_STATUS_EXTERNAL_POWER;
    if (power.charger_valid && power.charge_state==COMP_WBA_CHARGE_CHARGING)
        status|=COMP_SCREEN_STATUS_CHARGING;
    if (power.charge_state==COMP_WBA_CHARGE_FAULT) status|=COMP_SCREEN_STATUS_CHARGER_FAULT;
    uint16_t update_display=0u;
#ifdef COMPANION_WBA_BLE_LINKED
    update_display=comp_v11_update_product_screen_status();
#endif
    if (update_display || (board->power.blockers & COMP_POWER_BLOCKER_UPDATE)) status|=COMP_SCREEN_STATUS_UPDATING;
    comp_runtime_update_progress(&app->runtime,update_display,now);
    comp_runtime_status(&app->runtime,status);
    comp_runtime_battery_voltage(&app->runtime,cell_mv);
    /* A transient touch ACK must not shorten the deadline for the current
     * idle interval. Sleep now retains the visible pet, and the physical key
     * and pickup wake paths remain independent of touch availability. */
    app->runtime.menu.browser.auto_sleep_minutes = app->preferences.values.policy.idle_minutes;
    /* HAL/radio work may have captured a falling edge after poll entry.
     * Classify its current level before waking changes the surface, so the
     * first complete sleeping press remains wake-only even when held. Take
     * the saved edge before reading the level; a later edge remains pending
     * for the next poll, where the debounce path still sees sleeping. */
    const bool key_edge = comp_v11_hal_take_key_wake(board);
    comp_wba_button_edges_t key_edges={0};
    const bool recorder_key=!COMPANION_WBA_SCREEN_ENABLED||app->input.mode!=COMP_INPUT_RECORDER;
    if(recorder_key)key_edges=comp_v11_hal_take_key_edges(board);
    const bool pressed=COMPANION_WBA_SCREEN_ENABLED?comp_v11_hal_key_pressed():key_edges.raw_pressed;
    now=HAL_GetTick();
    /* Classify a physical gesture by its logical owner. Transient playback,
     * storage or display readiness still gates the actual refresh below,
     * but must not cancel a legitimate long key halfway through its hold. */
    const bool double_refresh = COMPANION_WBA_SCREEN_ENABLED && COMPANION_SCREEN_MANUAL_REFRESH_KEY &&
        !comp_runtime_recording_owned(&app->runtime) &&
        app->runtime.surface==COMP_SCREEN_SURFACE_HOME && !app->runtime.menu_pending &&
        (app->runtime.status_packed&COMP_SCREEN_STATUS_UPDATING)==0u;
    (void)pressed;(void)double_refresh;(void)was_sleeping; /* Screen-only branch may fold away. */
    uint8_t key=!recorder_key?
        comp_wba_button_poll_with_hold(&app->button,pressed,was_sleeping,double_refresh,700u,now):
        comp_wba_button_poll_transitions(&app->button,&key_edges,now);
    if ((key & COMP_WBA_BUTTON_WAKE) || key_edge)
        comp_runtime_wake_from(&app->runtime,now,COMP_RUNTIME_WAKE_KEY);
    if(recorder_key) {
#ifdef COMPANION_WBA_BLE_LINKED
        /* A deliberate idle key press also authorizes the normal first-pair
         * window before its UP starts recording. IMU wake never opens pairing. */
        if((key&COMP_WBA_BUTTON_DOWN)&&app->input.mode==COMP_INPUT_RECORDER&&
           !comp_runtime_recording_owned(&app->runtime)&&!comp_v11_ble_linked())
            (void)comp_v11_ble_menu(COMP_SCREEN_MENU_ACTION_BROWSER_PAIR);
#endif
        recording_input_apply(app,comp_input_key(&app->input,key,comp_runtime_recording_owned(&app->runtime)),now);
    }
    if ((key & (COMP_WBA_BUTTON_CONFIRM|COMP_WBA_BUTTON_DOUBLE_CONFIRM)) && !comp_runtime_recording_hold(&app->runtime)) {
        if(!COMPANION_WBA_SCREEN_ENABLED) {
            if(comp_runtime_recording_owned(&app->runtime)) {
                /* The recorder key marks a moment, never silently pauses the
                 * microphone. Reuse the durable schema3/5 timeline and its
                 * monotonic nonce; no beep is injected into a live recording.
                 * Accepted is pending until the existing NOR writer commits. */
                recording_local_bookmark(app);
            } else {
#ifdef COMPANION_WBA_BLE_LINKED
                /* Short idle press wakes/advertises for the app. An existing
                 * link stays connected; an offline device reuses the normal
                 * finite pairing window, preserving all bonds and recordings. */
                bool accepted=comp_v11_ble_linked() ||
                    comp_v11_ble_menu(COMP_SCREEN_MENU_ACTION_BROWSER_PAIR);
                (void)comp_audio_feedback_submit(&app->runtime.audio,
                    accepted?COMP_AUDIO_FEEDBACK_TOUCH_CONFIRM:COMP_AUDIO_FEEDBACK_ERROR,now);
#endif
            }
        } else if(app->recording.pipeline.state==COMP_PIPE_RECORDING) {
            (void)comp_wba_recording_product_pause_resume(&app->recording,app->runtime.record_token);
        } else {
        const bool manual_refresh = COMPANION_SCREEN_MANUAL_REFRESH_KEY &&
            panel_key_safe(app);
        const bool service_armed = app->panel_debug_key_until_ms!=0u &&
            (int32_t)(app->panel_debug_key_until_ms-now)>0;
        if (manual_refresh || service_armed) {
            if (panel_key_safe(app) && (app->panel_debug_replay_state==0u ||
                                      app->panel_debug_replay_state==3u)) {
                app->panel_debug_replay_id++;
                app->panel_debug_same_partial=(key & COMP_WBA_BUTTON_DOUBLE_CONFIRM)?3u:0u;
                app->panel_debug_replay_state=1u;
                app->panel_debug_hold_until_ms=now+30000u;
                app->panel_debug_replay_reply=2u;
            }
            /* A new press during completed-picture observation starts one
             * new replay. While queued/active, presses are coalesced rather
             * than piling up flashes behind an unfinished transaction. */
        } else (void)comp_audio_feedback_submit(&app->runtime.audio,COMP_AUDIO_FEEDBACK_TOUCH_CONFIRM,now);
        }
    }
    if (key & COMP_WBA_BUTTON_RECORD_TOGGLE) {
        (void)comp_v11_product_panel_debug_key(app,false,now);
        /* Long key is the emergency STOP even while HOLD/PAUSED owns the
         * original. HOLD only suppresses short-key and touch actions. */
        (void)comp_runtime_record(&app->runtime,!comp_runtime_recording_owned(&app->runtime),now);
    }
    if(board->microphone.running) {
        (void)capture_progress(app,22u);
#ifdef COMPANION_WBA_BLE_LINKED
        comp_v11_ble_live_follow_progress();
#endif
    }
    phase_started=HAL_GetTick();
    recording_capture_clock(app);
    const uint8_t previous_chat_state=app->runtime.chat_caption_state;
#if defined(COMPANION_WBA_BLE_LINKED) && defined(__arm__)
    uint8_t wall_runtime=comp_v11_ota_gatt_wall_context(COMP_OTA_WALL_PRODUCT_RUNTIME);
#endif
    {
        /* Capture-only service observation. Start/normal drain run outside
         * this span; an inactive begin never acquires a later owner. */
        comp_cpu_stage_span_t cpu_service=(board->microphone.running||comp_cpu_bulk_owned())?
            comp_cpu_detail_begin():(comp_cpu_stage_span_t){0};
    comp_runtime_service(&app->runtime,now);
        comp_cpu_detail_end(COMP_CPU_STAGE_RUNTIME_SERVICE,cpu_service,true);
    }
#if defined(COMPANION_WBA_BLE_LINKED) && defined(__arm__)
    (void)comp_v11_ota_gatt_wall_context(wall_runtime);
#endif
#ifdef COMPANION_WBA_BLE_LINKED
    if(previous_chat_state!=app->runtime.chat_caption_state)comp_v11_ble_pet_caption_changed();
#else
    (void)previous_chat_state;
#endif
    capture_phase_duration(app,phase_started,&app->max_capture_runtime_ms);
    if(board->microphone.running)(void)capture_progress(app,23u);
    phase_started=HAL_GetTick();
#if defined(COMPANION_WBA_BLE_LINKED) && defined(__arm__)
    uint8_t wall_presenter=comp_v11_ota_gatt_wall_context(COMP_OTA_WALL_PRODUCT_PRESENTER);
#endif
    {
        /* Capture-only service observation. Start/normal drain run outside
         * this span; an inactive begin never acquires a later owner. */
        comp_cpu_stage_span_t cpu_service=(board->microphone.running||comp_cpu_bulk_owned())?
            comp_cpu_detail_begin():(comp_cpu_stage_span_t){0};
    if(COMPANION_WBA_SCREEN_ENABLED) {
        (void)comp_screen_presenter_wba_service(&app->presenter,now);
        panel_full_observation_poll(app,HAL_GetTick());
        panel_key_observation_poll(app,HAL_GetTick());
    }
        comp_cpu_detail_end(COMP_CPU_STAGE_PRESENTER_SERVICE,cpu_service,true);
    }
#if defined(COMPANION_WBA_BLE_LINKED) && defined(__arm__)
    (void)comp_v11_ota_gatt_wall_context(wall_presenter);
#endif
    capture_phase_duration(app,phase_started,&app->max_capture_presenter_ms);
    if(board->microphone.running)(void)capture_progress(app,24u);
    phase_started=HAL_GetTick();
#if COMP_V11_PANEL_SOFTWARE_SPI && COMP_V11_PANEL_STARTUP_READBACK
    /* Capture a stable, completed full frame before the next renderer submit.
     * This engineering observation does not run during audio or start capture. */
    if (COMPANION_WBA_SCREEN_ENABLED && !panel_audit_done && board->panel.stats.completed_full != 0u &&
        board->panel.status == COMP_SSD1681_WBA_COMPLETE &&
        board->display_power.state == COMP_V11_POWER_READY &&
        !board->microphone.running && !board->playback_active &&
        !comp_v11_hal_panel_busy()) {
        panel_audit_done = true;
#if COMP_WBA_PACKED_OLD_FRAME && COMPANION_WBA_SCREEN_ENABLED
        if(comp_wba_frame_store_read(&app->panel_committed_storage,0u,app->panel_staging,5000u))
            (void)comp_v11_hal_panel_audit(app->panel_staging,5000u);
#else
        (void)comp_v11_hal_panel_audit(app->panel_committed, sizeof(app->panel_committed));
#endif
    }
#endif
    /* A UART freeze is finite and relinquishes immediately to real audio,
     * transfer, storage, OTA or pairing work. It never cancels an accepted
     * display transaction or fabricates an interaction/completion. */
    if (app->panel_debug_hold_until_ms!=0u &&
        ((int32_t)(app->panel_debug_hold_until_ms-HAL_GetTick())<=0 ||
         board->microphone.running || board->playback_active ||
         app->runtime.prepare_pending || app->runtime.start_pending ||
         app->runtime.command_pending || app->runtime.capture_active || app->runtime.stop_pending ||
         (board->power.blockers & (COMP_POWER_BLOCKER_MIC_CAPTURE |
          COMP_POWER_BLOCKER_RECORDING_TRANSFER | COMP_POWER_BLOCKER_STORAGE |
          COMP_POWER_BLOCKER_UPDATE | COMP_POWER_BLOCKER_BOND_NVM))!=0u))
        app->panel_debug_hold_until_ms=0u;
#if defined(COMPANION_WBA_BLE_LINKED) && defined(__arm__)
    uint8_t wall_render=comp_v11_ota_gatt_wall_context(COMP_OTA_WALL_PRODUCT_RENDER);
#endif
    /* Rendering reads/decodes the same NOR and cannot run the OTA storage
     * worker recursively. During DATA, keep the last physical image and the
     * latest runtime intent instead of repeatedly starving durable credits.
     * Already accepted panel transactions are still serviced above; no token
     * is taken or completed here. Error/abort/FINISH releases bulk ownership,
     * so the existing presenter resumes with the latest real state.
     * Type continues reporting the actual durable byte progress throughout. */
    {
        /* Capture-only service observation. Start/normal drain run outside
         * this span; an inactive begin never acquires a later owner. */
        comp_cpu_stage_span_t cpu_service=(board->microphone.running||comp_cpu_bulk_owned())?
            comp_cpu_detail_begin():(comp_cpu_stage_span_t){0};
#if COMPANION_WBA_SCREEN_ENABLED
    bool new_frame_allowed=true;
#ifdef COMPANION_WBA_BLE_LINKED
    new_frame_allowed=!comp_v11_update_product_bulk_transfer();
#endif
    if (COMPANION_WBA_SCREEN_ENABLED && new_frame_allowed && app->panel_debug_hold_until_ms==0u && app->assets_ready &&
        !board->nor.erase_active && board->display_power.state == COMP_V11_POWER_READY &&
        board->panel.status != COMP_SSD1681_WBA_NOT_READY &&
        comp_screen_presenter_wba_ready_for_frame(&app->presenter,now) &&
        comp_runtime_take_frame(&app->runtime,now,&frame)) {
        if(frame.kind!=COMP_RUNTIME_FRAME_HOLD &&
           frame.recording==DENZIC_AUDIO_RECORDING_STATE_RECORDING && !frame.recording_paused) {
            comp_wba_recording_level_snapshot_t level;
            if(comp_v11_product_recording_level(app,now,&level))
                frame.recording_input_level=comp_wba_recording_level_bars(level.sampled_mean);
        }
        if(app->panel_debug_trace_until_ms!=0u &&
           (int32_t)(app->panel_debug_trace_until_ms-now)>0)
            (void)comp_pet_trace_stamp(&app->runtime,&frame);
        comp_screen_presenter_wba_submit_result_t result=comp_screen_presenter_wba_submit(&app->presenter,&frame,now);
        if (result==COMP_SCREEN_PRESENTER_WBA_SUBMIT_BUSY || result==COMP_SCREEN_PRESENTER_WBA_SUBMIT_BAD_ARGUMENT)
            complete(app,frame.token,false,now);
    }
#endif
        comp_cpu_detail_end(COMP_CPU_STAGE_RENDER_SERVICE,cpu_service,true);
    }
#if defined(COMPANION_WBA_BLE_LINKED) && defined(__arm__)
    (void)comp_v11_ota_gatt_wall_context(wall_render);
#endif
    capture_phase_duration(app,phase_started,&app->max_capture_render_ms);
    if(board->microphone.running)(void)capture_progress(app,26u);
    /* The visible low-power product state has a real peripheral effect even
     * while CubeWBA STOP remains disabled: gyro off, accel 12.5 Hz low-power.
     * Any active audio or panel transaction makes the board API defer entry. */
    (void)comp_v11_hal_set_idle_peripherals(board,comp_v11_product_update_idle_policy(app));
    (void)capture_progress(app,25u);
}
