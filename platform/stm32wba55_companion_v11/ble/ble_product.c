#include "../reset_witness.h"
#if COMPANION_WBA_EXPERIMENTAL_STOP1
#include "../low_power_target.h"
#endif
#include "ble_product.h"
#if COMPANION_WBA_DUAL_PAIR_CAPTURE
#include "dual_mic_capture.h"
#endif
#include "../cpu_profile_target.h"
#include "imu_pointer_wire.h"
#include "imu_fusion.h"
#include "ll_sys_if.h"
#include "clock_target.h"
#include "main.h"
#include "app_entry.h"
#include "hw.h"
#include "stm32_seq.h"
#include "companion_gatt_stm32wb.h"
#include "linklayer_plat.h"
#include "pka_ctrl.h"
#include "companion_link.h"
#include "companion_ble_name.h"
#include "diag_log_export.h"
#include "update_product.h"
#include "wba_ota_gatt.h"
#include "companion_browser_interaction_contract.h"
#include "companion_pet_chat.h"
#include "ble_tx_gate.h"
#include "ble_gate_observation.h"
#include "ble_credit_wakeup.h"
#include "maintenance_protocol.h"
#include "../memory_target.h"
#include "ble_radio_activity_profile.h"
#include "ble_route_observation.h" /* existing clock/atomic helpers; no route instance */
#include "ble_residence_profile.h"
#include "../capture_radio_window.h"
#include "ll_intf.h"
#if COMPANION_WBA_ACL_READINESS_PROFILE
#include "ble_acl_readiness_profile.h"
#include "mem_intf.h" /* shared BLE RAM requires alignment-safe accesses */
static comp_acl_ready_t acl_readiness;
#endif
#include "ble_dispatch_profile.h"
#include "ble_tx_pump.h"
#include "companion_cpu_stage.h"
/* The unproven FW311 one-LL-tail policy is withdrawn. */
#include <string.h>
#include <stdio.h>

RTC_HandleTypeDef hrtc;
static comp_v11_product_app_t *product;
static bool linked,secured,link_ready;
static bool input_client;
static uint8_t input_feedback,input_flags;
static uint32_t pointer_sample_ms,pointer_sequence;
static float pointer_heading;
static uint32_t pointer_event_sequence,pointer_event_sent_ms;
static comp_imu_fusion_t pointer_fusion;

/* CAPTURE_RADIO_MODEL_BEGIN */
#if COMPANION_WBA_CPU_RESIDENCE_PROFILE
static struct {uint32_t token,down_ms,up_ms;uint16_t down,up,handle;uint8_t reason;} capture_radio;
_Static_assert(sizeof(capture_radio)<=20u,"bounded capture-radio observation");
#endif
void comp_v11_ble_observe_capture_radio(bool connected,uint16_t handle,uint8_t reason)
{
#if COMPANION_WBA_CPU_RESIDENCE_PROFILE
    if(!product || !product->board->microphone.running || !product->recording.pipeline.token)return;
    uint32_t token=product->recording.pipeline.token;
    if(capture_radio.token!=token){memset(&capture_radio,0,sizeof(capture_radio));capture_radio.token=token;}
    capture_radio.handle=handle;
    if(connected){if(capture_radio.up!=UINT16_MAX)++capture_radio.up;capture_radio.up_ms=HAL_GetTick();}
    else {if(capture_radio.down!=UINT16_MAX)++capture_radio.down;capture_radio.down_ms=HAL_GetTick();capture_radio.reason=reason;}
#else
    (void)connected;(void)handle;(void)reason;
#endif
}
/* CAPTURE_RADIO_MODEL_END */

static comp_link_t product_link;
static companion_ble_name_state_t names
#if COMPANION_WBA_CE_SHARED_CAPTURE && defined(__GNUC__)
    __attribute__((section(".sram1.bss"),aligned(8)))
#endif
    ;
static bool local_clear_pending;
static struct {
    uint32_t request_id,failures_before;
    uint8_t operation,result;
    bool pending,notify;
} maintenance;
static uint32_t local_clear_token,local_pair_token,local_pair_deadline;
static uint32_t secure_generation,local_pair_generation;
static uint8_t last_record_state=255u;
static uint8_t last_record_fault=255u;
static uint32_t last_dropped_pcm_frames;
static volatile uint32_t fatal_error;
static uint32_t sequencer_started_ms;
static uint8_t sequencer_depth;
static bool sequencer_yielded;
static comp_v11_ble_tx_gate_t notify_gate
#if COMPANION_WBA_CE_SHARED_CAPTURE && defined(__GNUC__)
    __attribute__((section(".sram1.bss"),aligned(8)))
#endif
    ;
static comp_v11_ble_gate_observation_t gate_observation;
static comp_v11_ble_credit_wakeup_t credit_wakeup;
static comp_ble_radio_activity_profile_t radio_activity_profile;
static uint32_t notify_staged_retries;
static comp_v11_ble_tx_pump_t notify_pump;
static uint32_t notify_resource_failures;
static uint32_t notify_busy_failures,notify_completion_events;
static uint32_t notify_pool_events,notify_timed_retries;
static uint32_t notify_in_call_pool_events;
static volatile bool download_timing_enabled;
static struct {uint32_t total_us,calls;} nor_read
#if COMPANION_WBA_CE_SHARED_CAPTURE && defined(__GNUC__)
    __attribute__((section(".sram1.bss"),aligned(8)))
#endif
    ;
static comp_v11_residence_profile_t route_observation;
static comp_v11_dispatch_profile_t dispatch_observation
#if COMPANION_WBA_CE_SHARED_CAPTURE && defined(__GNUC__)
    __attribute__((section(".sram1.bss"),aligned(8)))
#endif
    ;
static comp_v11_download_read_timing_t download_notify_timing;
static comp_v11_download_read_timing_t download_read_timing;
/* Foreground backend slices while capture is actually active. These are
 * elapsed times, including interrupts and WAIT slices, not SPI-only times.
 * Kept separately because the existing download profile is sealed-only. */
static struct {uint32_t calls,max_us,at_least_5ms,at_least_10ms,errors;} capture_read_timing
#if COMPANION_WBA_CE_SHARED_CAPTURE && defined(__GNUC__)
    __attribute__((section(".sram1.bss"),aligned(8)))
#endif
    ;
static const comp_wba_recording_transfer_backend_t *download_read_backend;
static bool sealed_transfer_work(void);
uint32_t comp_v11_ble_observe_us(void)
{
    if(HAL_GetTickFreq()==HAL_TICK_FREQ_1KHZ)for(unsigned tries=0u;tries<4u;++tries) {
        uint32_t tick=HAL_GetTick(),load=SysTick->LOAD,value=SysTick->VAL;
        bool pending=(SCB->ICSR&SCB_ICSR_PENDSTSET_Msk)!=0u;
        uint32_t after=HAL_GetTick(),value_after=SysTick->VAL;
        if(comp_v11_ble_micro_consistent(tick,after,load,value,value_after))
            return comp_v11_ble_micro_stamp(tick,load,value,pending);
    }
    (void)route_add(&route_observation.clock_fallbacks,1u);return HAL_GetTick()*1000u;
}
/* Prior four-phase/SPI-overlap profile is preserved in343 evidence. */
void comp_v11_ble_observe_aci_resource_origin(bool notify,const uint32_t *generation)
{
    if(download_timing_enabled && generation==&product_link.transfer.window_generation)
        comp_gate_observation_origin(&gate_observation,notify);
}
static void observe_gate_close(unsigned reason)
{
    if(download_timing_enabled && (gate_observation.flags&GATE_OBS_ACTIVE))
        comp_gate_observation_close(&gate_observation,reason,comp_v11_ble_observe_us());
}
static void observe_gate_open(void)
{comp_gate_observation_open(&gate_observation,comp_v11_ble_observe_us());}
void comp_v11_ble_observe_radio_state(bool active)
{
 uint32_t mask=__get_PRIMASK();__disable_irq();
 if(download_timing_enabled)comp_radio_activity_observe(&radio_activity_profile,active,comp_v11_ble_observe_us());
 if(!active && download_timing_enabled)
  comp_gate_observation_radio_end(&gate_observation,residence_depth(&route_observation),
      (route_observation.flags&RES_API)!=0u);
 comp_residence_radio(&route_observation,active);__set_PRIMASK(mask);
}
void comp_v11_ble_observe_pool_callback(uint32_t entered_ms){(void)entered_ms;}
void comp_v11_ble_observe_route_ready(uint8_t job)
{
    if(job<1u || job>2u)return;
    uint32_t mask=__get_PRIMASK();__disable_irq();
    if(download_timing_enabled)comp_dispatch_ready(&dispatch_observation.job[job-1u],comp_v11_ble_observe_us());
    __set_PRIMASK(mask);
}
void comp_v11_ble_observe_route_run(uint8_t job)
{
    if(job<1u || job>2u)return;
    uint32_t mask=__get_PRIMASK();__disable_irq();
    if(download_timing_enabled)comp_dispatch_run(&dispatch_observation.job[job-1u],comp_v11_ble_observe_us());
    __set_PRIMASK(mask);
}
void comp_v11_ble_observe_completion_enqueued(uint16_t h){(void)h;}
void comp_v11_ble_observe_completion_dispatched(uint16_t h){(void)h;}
void comp_v11_ble_observe_ll_send(uint16_t h,bool begin,bool success)
{
 uint32_t mask=__get_PRIMASK();__disable_irq();
 if(begin)comp_residence_send_begin(&route_observation,h,comp_v11_ble_observe_us());
 else comp_residence_send_end(&route_observation,h,success);
 __set_PRIMASK(mask);
}
#if COMPANION_WBA_ACL_READINESS_PROFILE
static bool acl_radio_known_off(void)
{return (route_observation.flags&(RES_RADIO_KNOWN|RES_RADIO_ON))==RES_RADIO_KNOWN;}
void comp_v11_ble_acl_admission_begin(uint16_t h,const uint8_t *data,uint16_t bytes,uint8_t flags)
{
 if(!download_timing_enabled || !sealed_transfer_work())return;
 if(acl_readiness.count==ACL_READY_ROWS && !acl_readiness.tracking)return;
 /* The LL allocator returns shared radio RAM (0x48028xxx), not ordinary
  * SRAM. GCC may coalesce byte expressions into unaligned LDR/LDRH. Copy
  * only the metadata through ST's alignment-safe routine before parsing;
  * neither descriptor nor data is retained after the original LL call.
  * Continuations use their length only and are never dereferenced. */
 uint32_t metadata[7];
 if(data && (flags&1u) && bytes>=27u) {
  ble_memcpy(metadata,data,27u);
  data=(const uint8_t *)metadata;
 }
 uint32_t mask=__get_PRIMASK();__disable_irq();
 comp_acl_ready_begin(&acl_readiness,h,comp_v11_ble_connection(),product_link.transfer.recording_id,
     data,bytes,flags,route_observation.radio_starts,acl_radio_known_off());
 __set_PRIMASK(mask);
}
void comp_v11_ble_acl_admission_end(bool success)
{
 if(!download_timing_enabled)return;
 uint32_t mask=__get_PRIMASK();__disable_irq();
 comp_acl_ready_end(&acl_readiness,success,route_observation.radio_starts,acl_radio_known_off());
 __set_PRIMASK(mask);
}
#endif
uint16_t comp_v11_ble_observe_ll_handle(void)
{return (route_observation.flags&RES_HANDLE)?(uint16_t)route_observation.handle:UINT16_MAX;}
void comp_v11_ble_observe_ll_completed(uint32_t packets,bool valid)
{
 uint32_t mask=__get_PRIMASK();__disable_irq();
 comp_residence_completed(&route_observation,packets,comp_v11_ble_observe_us(),valid);__set_PRIMASK(mask);
}
void comp_v11_ble_observe_ll_disconnect(uint16_t h)
{
 uint32_t mask=__get_PRIMASK();__disable_irq();comp_residence_disconnect(&route_observation,h);__set_PRIMASK(mask);
}
uint32_t comp_v11_ble_observe_spi_page(bool begin)
{
 (void)begin;uint32_t mask=__get_PRIMASK();__disable_irq();uint32_t now=comp_v11_ble_observe_us();__set_PRIMASK(mask);return now;
}
bool comp_v11_ble_observe_backend_read_active(void)
{return (nor_read.calls&0x40000000u)!=0u;}
void comp_v11_ble_observe_nor_read(uint32_t elapsed)
{
    /* Eight bytes total; bit30 is the backend scope, bit31 marks overflow.
     * Retain the original bool layout; never wrap a sum or count. */
    if(nor_read.calls&0x80000000u)return;
    if((nor_read.calls&0x3fffffffu)==0x3fffffffu || elapsed>UINT32_MAX-nor_read.total_us) {
        nor_read.calls|=0x80000000u;return;
    }
    ++nor_read.calls;nor_read.total_us+=elapsed;
}
static void start_download_observation(void)
{
    if(download_timing_enabled)return;
    nor_read.total_us=nor_read.calls=0u;
    memset(&download_notify_timing,0,sizeof(download_notify_timing));
    memset(&download_read_timing,0,sizeof(download_read_timing));
    uint32_t mask=__get_PRIMASK();__disable_irq();
    memset(&dispatch_observation,0,sizeof(dispatch_observation));
    comp_gate_observation_start(&gate_observation);
    comp_credit_wakeup_reset(&credit_wakeup,product_link.transfer.window_generation);
    comp_radio_activity_reset(&radio_activity_profile);
    comp_residence_start(&route_observation,comp_v11_ble_observe_us());
    if(!comp_v11_ble_report_callback_bound())route_observation.flags|=RES_UNBOUND;
#if COMPANION_WBA_ACL_READINESS_PROFILE
    memset(&acl_readiness,0,sizeof(acl_readiness));
#endif
    download_timing_enabled=true;
    __set_PRIMASK(mask);
    comp_v11_product_download_timing(true);
    comp_v11_cpu_transfer_begin(product_link.transfer.window_generation);
}
/* Observe the existing V2 backend in place, without another page/packet,
 * Flash access or retry. Its WAIT slices include the real segmented read,
 * page verification and copy. HAL ticks include interrupts; this is elapsed
 * backend time, not CPU cycles and not a transfer-speed denominator. */
static bool observed_metadata(void *context,uint32_t id,comp_recording_journal_entry_t *entry)
{
    return download_read_backend->metadata(context,id,entry);
}
static comp_wba_transfer_read_result_t observed_read(
    void *context,uint32_t id,uint32_t offset,uint8_t *bytes,uint32_t length)
{
    if(sealed_transfer_work())start_download_observation();
    const bool measuring=download_timing_enabled;
    const bool capture=product && product->board->microphone.running;
    const uint32_t started=(measuring||capture)?comp_v11_ble_observe_us():0u;
    comp_cpu_stage_span_t cpu_read=comp_v11_cpu_transfer_stage_begin();
    if(measuring)nor_read.calls|=0x40000000u;
    comp_wba_transfer_read_result_t result=download_read_backend->read(context,id,offset,bytes,length);
    nor_read.calls&=~0x40000000u;
    comp_v11_cpu_transfer_stage_end(COMP_BULK_CPU_READ,cpu_read);
    if(capture) {
        const uint32_t elapsed=comp_v11_ble_observe_us()-started;
        if(capture_read_timing.calls!=UINT32_MAX)++capture_read_timing.calls;
        if(elapsed>capture_read_timing.max_us)capture_read_timing.max_us=elapsed;
        if(elapsed>=5000u && capture_read_timing.at_least_5ms!=UINT32_MAX)++capture_read_timing.at_least_5ms;
        if(elapsed>=10000u && capture_read_timing.at_least_10ms!=UINT32_MAX)++capture_read_timing.at_least_10ms;
        if(result==COMP_WBA_TRANSFER_READ_ERROR && capture_read_timing.errors!=UINT32_MAX)++capture_read_timing.errors;
    }
    if(measuring) {
        uint32_t elapsed=comp_v11_ble_observe_us()-started;
        ++download_read_timing.calls;download_read_timing.total_ms+=elapsed;
        if(elapsed>download_read_timing.max_ms)download_read_timing.max_ms=elapsed;
    }
    return result;
}
static const comp_wba_recording_transfer_backend_t observed_backend={observed_metadata,observed_read};
static bool sealed_transfer_work(void)
{
    return product && link_ready && !fatal_error && linked && secured &&
        !product->board->microphone.running && !product_link.transfer.snapshot_live &&
        (product_link.transfer.state==COMP_WBA_RECORDING_TRANSFER_ACTIVE ||
         product_link.transfer.state==COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED);
}
bool comp_v11_ble_blocking_diagnostic_busy(void)
{
    if(sealed_transfer_work())return true;
    const comp_wba_recording_radio_t *radio=product_link.segmented;
    if(!radio || !linked || !secured || !radio->authenticated || !radio->negotiated ||
       !radio->interval_token)return false;
    /* Unlike interval_hint, observation does not change the deadline. The
     * existing two-second expiry keeps a dead host from hiding logs forever. */
    return !radio->interval_deadline || (int32_t)(HAL_GetTick()-radio->interval_deadline)<0;
}
static bool sealed_capture_transfer(void)
{
    return product && product->board->microphone.running &&
        product_link.transfer.connected && !product_link.transfer.snapshot_live &&
        (product_link.transfer.state==COMP_WBA_RECORDING_TRANSFER_ACTIVE ||
         product_link.transfer.state==COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED);
}
static bool sealed_during_capture_ready(void)
{
    comp_wba_recording_radio_t *radio=product_link.segmented;
    /* A segment that already sealed, including the backlog after reconnect,
     * is not a growing tail. Send it with the stopped-file pump while the
     * microphone is between PCM slices. The one-packet foreground pair stays
     * on the live snapshot only. This does not request a connection interval. */
    return link_ready && !fatal_error && linked && secured &&
        sealed_capture_transfer() && !product_link.maintenance &&
        !comp_v11_ble_nvm_busy() && radio &&
        comp_v11_ble_tx_gate_ready(&notify_gate,HAL_GetTick()) &&
        comp_wba_recording_radio_read_allowed(radio);
}
static const comp_wba_recording_transfer_budget_t *transfer_budget(void)
{
    static const comp_wba_recording_transfer_budget_t waiting = {0u,0u,0u};
    static const comp_wba_recording_transfer_budget_t capturing = {1u,2u,1u};
    if(sealed_capture_transfer())return &waiting;
    if(product&&product->board->microphone.running)
        return comp_v11_ble_tx_gate_ready(&notify_gate,HAL_GetTick())?&capturing:&waiting;
    /* Sealed sending has one owner: the bounded sequencer task. Live capture
     * keeps its existing foreground step and audio/NOR ownership policy. */
    if(!product_link.transfer.snapshot_live ||
       !comp_v11_ble_tx_gate_ready(&notify_gate,HAL_GetTick()))return &waiting;
    return NULL;
}
static uint32_t diagnostic_clock(void *context) {(void)context;return HAL_GetTick();}
static bool sealed_transfer_allowed(void)
{
    return sealed_during_capture_ready() || (sealed_transfer_work() &&
        !comp_v11_ble_nvm_busy() && comp_link_heavy_io_allowed(&product_link));
}
/* The measured LL ready-to-run tail reaches3ms at equal priority. Keep
 * LL/host/HCI at priority0; sealed file preparation is priority1, so any
 * already-ready radio work runs before another bounded NOR/publish turn.
 * Capture stays outside this task and keeps its10ms foreground deadline. */
static void schedule_sealed_transfer(void)
{
    /* A queued public controller report is only a retry hint. The SDK has
     * had a normal host turn; the original GATT API still decides credit.
     * No GATT call is made here or in the controller/host callbacks. */
    if(comp_credit_wakeup_take(&credit_wakeup,product_link.transfer.window_generation,
            linked&&secured&&sealed_transfer_allowed(),notify_gate.waiting,notify_gate.in_call)) {
        observe_gate_close(2u);
        comp_v11_ble_tx_gate_available(&notify_gate);
    }
    comp_v11_ble_tx_pump_schedule(&product_link.transfer,&notify_gate,
        sealed_transfer_allowed(),HAL_GetTick(),1u<<CFG_TASK_SEND_NOTIF_ID,CFG_SEQ_PRIO_1);
}
void comp_v11_ble_controller_progress_hint(void)
{
    if(linked&&secured&&sealed_transfer_work()&&notify_gate.waiting)
        comp_credit_wakeup_note(&credit_wakeup,product_link.transfer.window_generation);
}
void comp_v11_ble_host_cycle_completed(void)
{
    comp_credit_wakeup_host_cycle(&credit_wakeup);
    schedule_sealed_transfer();
}
static void send_sealed_transfer(void)
{
    if(product_link.segmented)
        (void)comp_wba_recording_radio_set_value_capacity(product_link.segmented,comp_v11_ble_value_capacity());
    product_link.transfer.compact_payload_limit=comp_v11_ble_recording_capacity();
    bool allowed=sealed_transfer_allowed();
    comp_v11_ble_tx_pump_poll(&notify_pump,&product_link.transfer,&notify_gate,
        allowed,sequencer_depth,diagnostic_clock,NULL,
        1u<<CFG_TASK_SEND_NOTIF_ID,CFG_SEQ_PRIO_1);
}
static void run_foreground_tasks(uint32_t tasks)
{
    comp_cpu_stage_span_t cpu_sequence=product&&(product->board->microphone.running||comp_cpu_bulk_owned())?
        comp_cpu_detail_begin():(comp_cpu_stage_span_t){0};
    if(sequencer_yielded) {UTIL_SEQ_ResumeTask(UTIL_SEQ_DEFAULT);sequencer_yielded=false;}
    schedule_sealed_transfer();
    sequencer_started_ms=HAL_GetTick();
    notify_pump.foreground_run=true;
    uint8_t wall_previous=comp_v11_ota_gatt_wall_context(COMP_OTA_WALL_SEQ_RUN);
    UTIL_SEQ_Run(tasks);
    (void)comp_v11_ota_gatt_wall_context(wall_previous);
    notify_pump.foreground_run=false;
    comp_cpu_detail_end(COMP_CPU_STAGE_BLE_SEQUENCER,cpu_sequence,true);
}

static bool stack_writes_allowed(void)
{
    return product && !(product->board->microphone.running ||
        product->recording.pipeline.discard_exclusive ||
        comp_wba_recording_product_recovering(&product->recording) ||
        product->runtime.command_pending || product->runtime.start_pending ||
        (comp_v11_update_product_busy() && !comp_v11_update_product_reboot_pending()));
}
static bool advertising_commands_allowed(void)
{
    if(!product || product->runtime.command_pending || product->runtime.start_pending ||
       comp_v11_update_product_busy() ||
       comp_v11_ble_nvm_control_blocked(product->board->microphone.running))return false;
    if(!product->board->microphone.running)return true;
    /* An offline microphone must not suppress its own reconnect advertising.
     * Keep Flash/NVM and throughput reconfiguration under the stricter gate.
     * Admit one GAP/HCI step only after audio service, away from the next DMA
     * boundary; the existing hard 10ms capture deadline still applies. */
    return HAL_GetTick()-product->capture_cycle_started_ms<=2u &&
        comp_v11_microphone_hal_io_window(&product->board->microphone);
}
#if COMPANION_WBA_CPU_DUTY_OBSERVER
static bool foreground_pending_body(void)
#else
bool comp_v11_ble_foreground_pending(void)
#endif
{
    if(!product || fatal_error)return false;
    /* PauseTask hides pending bits from IsSchedulableTask. One more ordinary
     * poll resumes the time-bounded sequencer; an empty run clears this flag. */
    if(sequencer_yielded)return true;
    uint32_t tasks=UTIL_SEQ_DEFAULT;
    if(!stack_writes_allowed())tasks&=~(1u<<CFG_TASK_FLASH_MANAGER);
    /* The SDK checks ALL requested bits, so query one permitted task at a
     * time. No command, notification, Flash access or dispatch in this query. */
    _Static_assert(CFG_TASK_NBR>0 && CFG_TASK_NBR<=32,"configured sequencer bitmap fits");
    for(unsigned bit=0u;bit<(unsigned)CFG_TASK_NBR;++bit) {
        uint32_t task=1u<<bit;
        if((tasks&task) && UTIL_SEQ_IsSchedulableTask(task))return true;
    }
    return sealed_transfer_work() && !comp_v11_ble_nvm_busy() &&
        comp_link_heavy_io_allowed(&product_link) &&
        comp_v11_ble_tx_gate_ready(&notify_gate,HAL_GetTick());
}
#if COMPANION_WBA_CPU_DUTY_OBSERVER
bool comp_v11_ble_foreground_pending(void)
{
    comp_cpu_duty_span_t span=comp_cpu_duty_span_begin();
    bool ready=foreground_pending_body();
    comp_cpu_duty_span_end(COMP_DUTY_READY,span);return ready;
}
#endif
extern void (*radio_callback)(void);
extern void (*low_isr_callback)(void);
extern volatile uint8_t radio_sw_low_isr_is_running_high_prio;

#if defined(__GNUC__)
__attribute__((noinline,noipa))
#endif
void Error_Handler(void)
{
#if defined(__GNUC__)
    comp_v11_reset_witness_failure(6u,(uint32_t)(uintptr_t)__builtin_return_address(0),1u);
#endif
    /* Upstream invokes this on violated initialization/crypto invariants.
     * Returning would let the stack continue with invalid state. */
    fatal_error=1u;
    /* Main-context initialization failures can still identify their stage.
     * IRQ-context failures deliberately do not block on UART and require SWD. */
#if COMPANION_WBA_EXPERIMENTAL_STOP1
    /* Failure-only engineering evidence. Do not add UART work to an IRQ or
     * to the normal capture/radio hot path. The original fault stays fatal. */
    if (__get_IPSR()==0u) {
        char line[112];
        (void)snprintf(line,sizeof(line),
            "BOOT1 FATAL phase=ble stop_stage=%lu stop_entries=%lu caller=%08lX\r\n",
            (unsigned long)comp_v11_low_power_stage(),
            (unsigned long)companion_stop1_entries,
            (unsigned long)(uintptr_t)__builtin_return_address(0));
        (void)comp_v11_hal_debug_write(line);
    }
#else
    (void)comp_v11_hal_debug_write("BOOT1 FATAL phase=ble\r\n");
#endif
    __disable_irq();
    for(;;)__WFI();
}
/* CONSOLE_IDLE_RNG_PROGRESS_BEGIN */
void comp_v11_ble_console_idle_progress(void)
{
    /* Large synchronous diagnostic snapshots can starve the sequenced RNG
     * producer while radio IRQs keep consuming its32-word pool. Service only
     * that existing producer, with its mutex/health checks, between UART
     * writes. Never dispatch ACI/product tasks recursively or enter capture. */
    if(__get_IPSR()!=0u || !product || !product->board || fatal_error ||
       product->board->microphone.running || !comp_v11_ble_host_ready())return;
    (void)HW_RNG_Process();
}
/* CONSOLE_IDLE_RNG_PROGRESS_END */
bool comp_v11_ble_linked(void) { return linked; }
bool comp_v11_ble_secured(void) { return secured; }
static bool capture_radio_remaining(uint32_t *next_us,bool *busy)
{
    bool valid=linked && ll_intf_le_get_remaining_time_for_next_event(next_us)==0u;
    *busy=(route_observation.flags&RES_RADIO_ON)!=0u ||
        NVIC_GetPendingIRQ(RADIO_INTR_NUM)!=0u ||
        NVIC_GetPendingIRQ(RADIO_SW_LOW_INTR_NUM)!=0u;
    return valid;
}
#if COMPANION_WBA_CPU_RESIDENCE_PROFILE
static uint32_t codec_admission_flags,codec_admission_next_us;
void comp_v11_ble_capture_admission_observed(uint32_t *flags,uint32_t *next_radio_us)
{*flags=codec_admission_flags;*next_radio_us=codec_admission_next_us;}
#endif
bool comp_v11_ble_capture_encode_window(bool pending)
{
    static comp_capture_radio_window_t wait;
    uint32_t next_us=0u;bool busy=false;
    bool valid=pending && capture_radio_remaining(&next_us,&busy);
    bool allowed=comp_capture_radio_window_open(&wait,HAL_GetTick(),pending,valid,busy,next_us);
#if COMPANION_WBA_CPU_RESIDENCE_PROFILE
    if(allowed) {
        /* No extra controller reads or timing/admission changes. Reason1
         * bypass,2 missing query,3 observed quiet gap,4 bounded timeout. */
        uint32_t reason=!pending?1u:!valid?2u:!busy&&next_us>7000u?3u:4u;
        codec_admission_flags=(pending?1u:0u)|(valid?2u:0u)|(busy?4u:0u)|(reason<<8u);
        codec_admission_next_us=next_us;
    }
#endif
    return allowed;
}
uint32_t comp_v11_ble_fatal_error(void) { return fatal_error; }
void RTC_IRQHandler(void) {
    comp_v11_cpu_irq_enter(false); HAL_RTC_AlarmIRQHandler(&hrtc); HAL_RTCEx_SSRUIRQHandler(&hrtc); 
    comp_v11_cpu_irq_exit();
}
void RADIO_IRQHandler(void)
{
    comp_v11_cpu_irq_enter(false);
    if(radio_callback)radio_callback();
    LL_RCC_RADIO_DisableSleepTimerClock(); __ISB();

    comp_v11_cpu_irq_exit();
}
void HASH_IRQHandler(void)
{
    comp_v11_cpu_irq_enter(false);
    NVIC_DisableIRQ(RADIO_SW_LOW_INTR_NUM);
    if(low_isr_callback)low_isr_callback();
    if(radio_sw_low_isr_is_running_high_prio) {
        HAL_NVIC_SetPriority(RADIO_SW_LOW_INTR_NUM,RADIO_INTR_PRIO_LOW,0);
        radio_sw_low_isr_is_running_high_prio=0;
    }
    NVIC_EnableIRQ(RADIO_SW_LOW_INTR_NUM);

    comp_v11_cpu_irq_exit();
}
void PKA_IRQHandler(void)
{
    comp_v11_cpu_irq_enter(false);
    if(LL_PKA_IsActiveFlag_PROCEND(PKA)) { LL_PKA_ClearFlag_PROCEND(PKA);PKACTRL_EndOfProcessCb(); }

    comp_v11_cpu_irq_exit();
}
void UTIL_SEQ_PreTask(uint32_t id)
{
    if(id==CFG_TASK_BLE_HOST){comp_v11_ble_observe_route_run(1u);}
    if(id==CFG_TASK_LINK_LAYER){comp_v11_ble_observe_route_run(2u);}
    ++sequencer_depth;
}
void UTIL_SEQ_PostTask(uint32_t id)
{
    (void)id;
    if(sequencer_depth)--sequencer_depth;
    /* Yield only after the owned outer task returns. ACI may also WaitEvt
     * from outside our Run; that dispatch must retain its semaphore tasks. */
    if(notify_pump.foreground_run && !sequencer_depth && product &&
       (product->board->microphone.running || sealed_transfer_work() ||
        companion_gatt_stm32wb_has_pending() ||
        comp_v11_ota_gatt_foreground_pending()) &&
       HAL_GetTick()-sequencer_started_ms>=2u) {
        /* A complete queued OTA command is a foreground consumer too.
         * Preserve the existing outer-task/owned-Run guard and quantum:
         * never pause a nested ACI WaitEvt or the active NOR consumer. */
        UTIL_SEQ_PauseTask(UTIL_SEQ_DEFAULT);sequencer_yielded=true;
        comp_v11_ota_gatt_wall_note_ready_yield();
    }
}
void comp_v11_ble_link(bool connected,bool encrypted)
{
    const bool new_secure=connected&&encrypted&&(!linked||!secured);
    if(download_timing_enabled && (linked!=connected || secured!=(connected&&encrypted))){
        uint32_t mask=__get_PRIMASK();__disable_irq();
        route_observation.flags|=RES_LINK_CHANGE|RES_INVALID;
        __set_PRIMASK(mask);
    }
    if(connected && encrypted && (!linked || !secured))++secure_generation;
    if(!connected || !linked){
        comp_credit_wakeup_disarm(&credit_wakeup);
        observe_gate_close(0u);comp_v11_ble_tx_gate_available(&notify_gate);
    }
    linked=connected; secured=connected&&encrypted;
    if(!secured){
        #if COMPANION_WBA_CPU_DUTY_OBSERVER
        comp_cpu_duty_end(0u,false); /* Never retires a recording-owned scope. */
        #endif
        input_client=false;input_feedback=input_flags=255u;
        pointer_sample_ms=pointer_sequence=0u;
        pointer_heading=0.0f;pointer_event_sequence=0u;
        pointer_fusion.active=false;
    }
    /* Queue only; the product foreground owner performs any NOR operation. */
    if(product) {
        comp_v11_product_recording_link_change(product,secured,new_secure);
        comp_input_connection(&product->input,secured);
    }
    if(!connected && product) {
        comp_pet_profile_abort(&product->pet_profile);
        comp_v11_ble_settings_changed(); /* Retire private PMP1 readback bytes. */
    }
    comp_v11_ota_gatt_connection(secured);
    /* Normal host cleanup follows the qualified visible acknowledgement.
     * Keep that reply for its visible lifetime; incomplete transfers cancel. */
    if(!connected && product &&
       (product->runtime.chat_caption_state==COMP_PET_CHAT_ASSEMBLING ||
        product->runtime.chat_caption_state==COMP_PET_CHAT_RESERVING ||
        product->runtime.chat_caption_state==COMP_PET_CHAT_PENDING))
        comp_pet_chat_cancel(&product->runtime,false);
    if(!connected)(void)companion_gatt_stm32wb_drain(NULL,NULL);
    if(product&&link_ready)comp_link_connection(&product_link,linked,secured,HAL_GetTick());
    if(!connected) {names.pending_valid=false;names.pending_len=0;}
    comp_diag_log_record_code(COMP_DIAG_EVT_BLE_CONNECTION,COMP_DIAG_SEV_INFO,connected,encrypted,0,0);
}
/* Fixed control events use the existing RAM ring, never UART/audio loops.
 * arg0=request_id and arg1=recording_id correlate with Type control_trace. */
static bool reclaim_trace_request(const uint8_t *value,uint16_t length,
                                  companion_gatt_delete_privacy_v1_t *request)
{
    if(!value || length!=sizeof(*request) || value[0]!=1u || value[1]!=1u)return false;
    memcpy(request,value,sizeof(*request));return true;
}
static uint32_t reclaim_trace_state(void)
{
    return (uint32_t)linked|((uint32_t)secured<<1u)|
        ((uint32_t)(product_link.segmented&&product_link.segmented->consume_pending)<<2u)|
        ((uint32_t)product_link.maintenance<<5u)|
        ((uint32_t)(product && product->board->playback_active)<<6u)|
        ((uint32_t)(product && product->runtime.capture_active)<<7u)|
        ((uint32_t)product_link.subscribed[COMPANION_GATT_CHAR_DELETE_PRIVACY]<<8u)|
        ((uint32_t)product_link.transfer.state<<16u)|
        ((uint32_t)(product?comp_wba_recording_product_state(&product->recording):255u)<<24u);
}
static uint16_t device_fault_bitmap(const comp_v11_product_app_t *app)
{
    uint16_t faults=(uint16_t)app->board->faults;
    if(comp_wba_recording_product_tail_retained(&app->recording))
        faults|=COMPANION_GATT_FAULT_RECORDING_TAIL_UNRESOLVED;
    return faults;
}
static bool publish(void *context,companion_gatt_char_id_t id,const uint8_t *value,uint16_t length)
{
    (void)context;
    if(!comp_v11_ble_notifications_allowed())return false;
    if(id==COMPANION_GATT_CHAR_MEETING_STATUS) {
        comp_cpu_stage_span_t cpu_meeting=product&&product->board->microphone.running?
            comp_cpu_detail_begin():(comp_cpu_stage_span_t){0};
        tBleStatus result=companion_gatt_stm32wb_publish(id,value,length);
        comp_cpu_detail_end(COMP_CPU_STAGE_MEETING_ACI,cpu_meeting,true);
        return result==BLE_STATUS_SUCCESS;
    }
    bool recording_chunk=id==COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL ||
        id==COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B;
    if(recording_chunk && length>comp_v11_ble_value_capacity())return false;
    /* A full SDK TX pool has no room for this prepared packet. Keep the
     * transfer cursor unchanged until ST reports free space; the timeout is
     * only a recovery path for a missed event, not the normal pacing clock. */
    if(recording_chunk && notify_gate.waiting) {
        if(!comp_v11_ble_tx_gate_ready(&notify_gate,HAL_GetTick()))return false;
        ++notify_timed_retries;
        observe_gate_close(3u);
    }
    if(id==COMPANION_GATT_CHAR_OTA_READINESS) {
        companion_gatt_ota_readiness_v1_t readiness;
        comp_v11_update_product_readiness(&readiness);
        return companion_gatt_stm32wb_publish(id,(uint8_t*)&readiness,sizeof(readiness))==BLE_STATUS_SUCCESS;
    }
    if(id==COMPANION_GATT_CHAR_DEVICE_STATUS && length==sizeof(companion_gatt_device_status_v1_t) && product) {
        companion_gatt_device_status_v1_wba_capacity_t status={0};
        memcpy(&status.identity.base,value,sizeof(status.identity.base));
        status.identity.base.fault_bitmap=device_fault_bitmap(product);
        status.identity.mcu_uid_word0=HAL_GetUIDw0();
        status.identity.mcu_uid_word1=HAL_GetUIDw1();
        status.identity.mcu_uid_word2=HAL_GetUIDw2();
        status.identity.ui_generation=product->assets_ready ? product->resources.generation.root.generation : 0u;
        (void)comp_v11_product_recording_capacity(product,&status.capacity);
        _Static_assert(sizeof(companion_gatt_device_status_v1_wba_capacity_t)==84u,
                       "V1 WBA capacity wire prefix");
        _Static_assert(sizeof(companion_gatt_device_status_v1_wba_recording_t)==116u,
                       "V2 WBA capability attribute length");
        uint8_t extended[sizeof(companion_gatt_device_status_v1_wba_recording_t)];memcpy(extended,&status,sizeof(status));
        uint16_t bytes=(uint16_t)sizeof(status);
        if(link_ready&&comp_wba_recording_product_capability(&product->recording,extended+sizeof(status)))bytes=(uint16_t)sizeof(extended);
        return companion_gatt_stm32wb_publish(id,extended,bytes)==BLE_STATUS_SUCCESS;
    }
    if(id==COMPANION_GATT_CHAR_BATTERY_CHARGE && product) {
        comp_wba_power_snapshot_t v=comp_wba_power_monitor_snapshot(&product->board->power_monitor,HAL_GetTick());
        companion_gatt_battery_charge_v1_t battery={.schema_version=1,.percent=v.percent,
            .charge_state=v.charge_state,.charger_present=v.charger_valid ? (uint8_t)v.charger_present : 255u,
            .millivolts=v.millivolts,.temperature_c_x10=INT16_MIN};
        return companion_gatt_stm32wb_publish(id,(uint8_t*)&battery,sizeof(battery))==BLE_STATUS_SUCCESS;
    }
    bool data_timing=recording_chunk && download_timing_enabled && value==product_link.transfer.packet &&
        product_link.transfer.packet_ready && length==product_link.transfer.packet_length;

    uint32_t started=data_timing?comp_v11_ble_observe_us():0u;
    comp_cpu_stage_span_t cpu_publish=data_timing?comp_v11_cpu_transfer_stage_begin():(comp_cpu_stage_span_t){0};
    if(recording_chunk)observe_gate_close(0u);
    if(recording_chunk)comp_v11_ble_tx_gate_begin(&notify_gate,HAL_GetTick(),
        sealed_transfer_work() ? comp_v11_ble_connection_interval() : 0u);
    tBleStatus status;
    if(recording_chunk && value==product_link.transfer.packet &&
       product_link.transfer.packet_ready && length==product_link.transfer.packet_length) {
        uint8_t lane=(uint8_t)((uint8_t)id+1u);
        if(product_link.transfer.notify_staged_lane!=lane) {
            product_link.transfer.notify_staged_bytes=0u;
            product_link.transfer.notify_staged_lane=lane;
        }
        if(product_link.transfer.notify_staged_bytes)++notify_staged_retries;
        status=companion_gatt_stm32wb_publish_progress(id,value,length,
            &product_link.transfer.notify_staged_bytes,&product_link.transfer.window_generation);
    } else {
        /* A protocol reply on either recording characteristic may replace
         * its local attribute. Rebuild any later pending packet from zero. */
        if(recording_chunk) {
            product_link.transfer.notify_staged_bytes=0u;
            product_link.transfer.notify_staged_lane=0u;
        }
        status=companion_gatt_stm32wb_publish(id,value,length);
    }
    comp_v11_cpu_transfer_stage_end(COMP_BULK_CPU_PUBLISH,cpu_publish);
    if(data_timing && download_timing_enabled) {
        uint32_t elapsed=comp_v11_ble_observe_us()-started;
        ++download_notify_timing.calls;download_notify_timing.total_ms+=elapsed;
        if(elapsed>download_notify_timing.max_ms)download_notify_timing.max_ms=elapsed;
    }
    if(recording_chunk) {
        if(data_timing)
            comp_credit_wakeup_result(&credit_wakeup,product_link.transfer.window_generation,
                status==BLE_STATUS_SUCCESS,
                status==BLE_STATUS_INSUFFICIENT_RESOURCES||status==BLE_STATUS_BUSY);
        /* WBA also returns BUSY while this attribute's prior notification is
         * in flight. Both official events wake the same bounded retry owner. */
        comp_v11_ble_tx_gate_end(&notify_gate,status==BLE_STATUS_INSUFFICIENT_RESOURCES || status==BLE_STATUS_BUSY);
        if(download_timing_enabled && notify_gate.waiting)observe_gate_open();
        if(status==BLE_STATUS_INSUFFICIENT_RESOURCES)++notify_resource_failures;
        if(status==BLE_STATUS_BUSY)++notify_busy_failures;
    }
    if(id==COMPANION_GATT_CHAR_DELETE_PRIVACY && status==BLE_STATUS_SUCCESS) {
        if(length==84u&&!memcmp(value,"CRA2\x02\x00\x54\x00",8u)) {
            uint32_t rid=(uint32_t)value[40]|((uint32_t)value[41]<<8u)|
                ((uint32_t)value[42]<<16u)|((uint32_t)value[43]<<24u);
            comp_diag_log_record_code(COMP_DIAG_EVT_GATT_SEGMENT_CONSUME_REPLY,
                COMP_DIAG_SEV_INFO,rid,0u,reclaim_trace_state(),0u);
        } else if(length==16u&&!memcmp(value,"CAE2\x02\x00\x10\x00",8u)) {
            uint32_t rid=(uint32_t)value[8]|((uint32_t)value[9]<<8u)|
                ((uint32_t)value[10]<<16u)|((uint32_t)value[11]<<24u);
            uint32_t reason=(uint32_t)value[12]|((uint32_t)value[13]<<8u)|
                ((uint32_t)value[14]<<16u)|((uint32_t)value[15]<<24u);
            comp_diag_log_record_code(COMP_DIAG_EVT_GATT_SEGMENT_CONSUME_REPLY,
                COMP_DIAG_SEV_WARN,rid,reason,reclaim_trace_state(),0u);
        }
        companion_gatt_delete_privacy_v1_t request;
        if(reclaim_trace_request(value,length,&request))
            comp_diag_log_record_code(COMP_DIAG_EVT_GATT_RECLAIM_REPLY,COMP_DIAG_SEV_INFO,
                request.request_id,request.recording_id,request.flags,reclaim_trace_state());
    }
    return status==BLE_STATUS_SUCCESS;
}
void comp_v11_ble_tx_pool_available(void)
{
    ++notify_pool_events;
    observe_gate_close(1u);
    if(notify_gate.in_call)++notify_in_call_pool_events;
    comp_v11_ble_tx_gate_available(&notify_gate);
    schedule_sealed_transfer();
}
uint32_t comp_v11_ble_tx_pool_events(void) {return notify_pool_events;}
void comp_v11_ble_recording_notification_complete(void)
{
    if(!linked || !secured)return;
    ++notify_completion_events;
    observe_gate_close(2u);
    comp_v11_ble_tx_gate_available(&notify_gate);
    /* Do not publish or advance the immutable packet from an HCI callback.
     * Nested ACI dispatch is still excluded by the existing foreground pump. */
    schedule_sealed_transfer();
}
uint32_t comp_v11_ble_tx_timed_retries(void) {return notify_timed_retries;}
void comp_v11_ble_download_timing_diagnostic(void)
{
#if COMPANION_WBA_VERBOSE_BLE_DIAGNOSTICS
    uint32_t observation_mask=__get_PRIMASK();__disable_irq();
    comp_v11_download_read_timing_t read=download_read_timing;
    const comp_v11_residence_profile_t v=route_observation;
    const comp_v11_dispatch_profile_t dispatch=dispatch_observation;
    const comp_v11_ble_gate_observation_t gate_profile=gate_observation;
    const comp_ble_radio_activity_profile_t activity=radio_activity_profile;
    __set_PRIMASK(observation_mask);
    char line[160];
    int n=snprintf(line,sizeof(line),
        "CAPREAD schema=1 scope=backend_capture calls=%lu max_us=%lu ge5ms=%lu ge10ms=%lu errors=%lu\r\n",
        (unsigned long)capture_read_timing.calls,(unsigned long)capture_read_timing.max_us,
        (unsigned long)capture_read_timing.at_least_5ms,(unsigned long)capture_read_timing.at_least_10ms,
        (unsigned long)capture_read_timing.errors);
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),
        "XFER1 read_steps=%lu read_us=%lu read_max_us=%lu notify=%lu notify_us=%lu notify_max_us=%lu\r\n",
        (unsigned long)read.calls,(unsigned long)read.total_ms,(unsigned long)read.max_ms,
        (unsigned long)download_notify_timing.calls,(unsigned long)download_notify_timing.total_ms,
        (unsigned long)download_notify_timing.max_ms);
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),"XFER2 pool_in_call=%lu retry_delay_ms=%lu staged_retry=%lu busy=%lu complete=%lu\r\n",
        (unsigned long)notify_in_call_pool_events,
        (unsigned long)notify_gate.retry_delay_ms,(unsigned long)notify_staged_retries,
        (unsigned long)notify_busy_failures,(unsigned long)notify_completion_events);
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),"XFER4 wait_ms=0 windows=0 active=0 measured=0\r\n");
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),"XFER5 residence_schema=1 accepted=%lu completed=%lu begin=%u end=%u flags=%lu hook_bound=%u\r\n",
        (unsigned long)v.accepted,(unsigned long)v.completed,(unsigned)((v.handle>>16u)&255u),
        (unsigned)((v.handle>>24u)&255u),(unsigned long)(v.flags&RES_ERRORS),(unsigned)comp_v11_ble_report_callback_bound());
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),"XFER6 residence_schema=1 samples=%lu total_us=%lu max_us=%lu reports=%lu radio_starts=%lu zero_starts=%lu\r\n",
        (unsigned long)v.residence_samples,(unsigned long)v.residence_us,(unsigned long)v.residence_max_us,
        (unsigned long)v.reports,(unsigned long)v.radio_starts,(unsigned long)v.radio_empty);
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    /* Only the existing post-payload diagnostic, never an active IRQ log.
     * bins: <3000,3000..5499,5500..6999,>=7000us. No sum with RF/host time. */
    n=snprintf(line,sizeof(line),"RADACT schema=1 min_us=%lu max_us=%lu n=%u,%u,%u,%u flags=%u pending=%u\r\n",
        (unsigned long)activity.min_us,(unsigned long)activity.max_us,
        activity.bins[0],activity.bins[1],activity.bins[2],activity.bins[3],activity.flags,activity.active);
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    uint16_t acl_bytes=0u;uint8_t acl_packets=0u;
    uint8_t acl_status=comp_v11_ble_controller_buffer_size(&acl_bytes,&acl_packets);
    n=snprintf(line,sizeof(line),"XFER7 controller_buffer_schema=1 status=%u packet_bytes=%u packets=%u\r\n",
        acl_status,acl_bytes,acl_packets);
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    uint32_t failures[3];comp_v11_ble_ll_failure_snapshot(failures);
    n=snprintf(line,sizeof(line),"LLSEND1 schema=1 count=%lu first=%08lx last=%08lx saturated=%u\r\n",
        (unsigned long)failures[0],(unsigned long)failures[1],(unsigned long)failures[2],
        (unsigned)(failures[0]==UINT32_MAX));
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),"LLSEND2 schema=1 pending_cancelled=%lu\r\n",
        (unsigned long)comp_v11_ble_pending_acl_released());
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),"SPIRD schema=1 calls=%lu total_us=%lu overflow=%u sck_hz=%lu bytes_per_call=256\r\n",
        (unsigned long)(nor_read.calls&0x3fffffffu),(unsigned long)nor_read.total_us,
        (unsigned)((nor_read.calls&0x80000000u)!=0u),(unsigned long)comp_v11_hal_nor_sck_hz());
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),"XFER9 gate_schema=2 pool_us=%lu complete_us=%lu timer_us=%lu pool=%u complete=%u timer=%u flags=%u\r\n",
        (unsigned long)gate_profile.wait_us[0],(unsigned long)gate_profile.wait_us[1],
        (unsigned long)gate_profile.wait_us[2],gate_profile.wakes[0],gate_profile.wakes[1],
        gate_profile.wakes[2],gate_profile.flags);
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),"XFER8 span_us=%lu clock_fallbacks=%lu systick_load=%lu tick_step_ms=%u\r\n",
        (unsigned long)v.span_us,(unsigned long)v.clock_fallbacks,
        (unsigned long)SysTick->LOAD,(unsigned)HAL_GetTickFreq());
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),"XFER10 gate_schema=2 stage=%u commit=%u radio_pending=%u radio_empty=%u\r\n",
        (unsigned)(gate_profile.origins&65535u),(unsigned)(gate_profile.origins>>16u),
        (unsigned)(gate_profile.radio_ends&65535u),(unsigned)(gate_profile.radio_ends>>16u));
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),"CREDITWAKE schema=1 wake=%u accepted=%u resource=%u pending=%u attempt=%u\r\n",
        credit_wakeup.wakes,credit_wakeup.accepted,credit_wakeup.resource,
        (unsigned)credit_wakeup.pending,(unsigned)credit_wakeup.attempting);
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    /* Post-payload numeric summary only. Pending at the end is censored;
     * per-task totals overlap other work and are not a wall partition. */
    for(unsigned job=0u;job<2u;++job) {
        const comp_v11_dispatch_slot_t *d=&dispatch.job[job];
        n=snprintf(line,sizeof(line),"XFER11 task=%u n=%lu us=%lu max=%lu coal=%lu unpaired=%lu flags=%lu\r\n",
            job+1u,(unsigned long)d->count,(unsigned long)d->total_us,(unsigned long)d->max_us,
            (unsigned long)d->coalesced,(unsigned long)d->unpaired,(unsigned long)d->flags);
        if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    }
    /* Existing pinned SDK lightweight profile: maxima since boot, NOT an
     * ACL close reason or per-transfer/RF timing. No reset, active-path hook,
     * command, new resident state or UART output during payload work.
     * The actual SDK getter computes a mean without a zero-count guard;
     * skip it if DIV_0_TRP is enabled rather than alter fault policy. Its
     * mean is deliberately not published: sample count/overflow are unknown.
     * The pinned getter exposes hardware timer steps, not qualified us. */
    uint32_t sdk_exec=0u,sdk_drift=0u,sdk_mean_unused=0u;
    uint8_t sdk_read=0u;
    observation_mask=__get_PRIMASK();__disable_irq();
    if(!download_timing_enabled && v.radio_starts &&
       !(SCB->CCR&SCB_CCR_DIV_0_TRP_Msk)) {
        ll_sys_get_ble_profile_statistics(&sdk_exec,&sdk_drift,&sdk_mean_unused,0u);
        sdk_read=1u;
    }
    __set_PRIMASK(observation_mask);
    n=snprintf(line,sizeof(line),"SDKMAX schema=2 boot_scope=1 read=%u exec_ticks=%lu drift_ticks=%lu unit=ll_hw_step count_known=0\r\n",
        sdk_read,(unsigned long)sdk_exec,(unsigned long)sdk_drift);
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
#if COMPANION_WBA_CPU_RESIDENCE_PROFILE
    n=snprintf(line,sizeof(line),"RADIOM1 token=%lu down=%u up=%u down_ms=%lu up_ms=%lu capture_active_only=1 hci=1\r\n",
        (unsigned long)capture_radio.token,(unsigned)capture_radio.down,(unsigned)capture_radio.up,
        (unsigned long)capture_radio.down_ms,(unsigned long)capture_radio.up_ms);
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),"RADIOM2 token=%lu handle=%u reason=%u\r\n",
        (unsigned long)capture_radio.token,(unsigned)capture_radio.handle,(unsigned)capture_radio.reason);
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
#endif
#if COMPANION_WBA_ACL_READINESS_PROFILE
    /* Only this existing post-payload summary; never print in an ACL/IRQ path. */
    if(!download_timing_enabled){
        n=snprintf(line,sizeof(line),"ACLREADYS schema=4 rows=%u starts=%u continuations=%u unbounded=%u errors=%u\r\n",
            acl_readiness.count,acl_readiness.starts,acl_readiness.continuations,acl_readiness.unbounded,acl_readiness.errors);
        if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    }
    if(!download_timing_enabled)for(unsigned i=0u;i<acl_readiness.count;++i){
        n=snprintf(line,sizeof(line),"ACLREADY schema=4 offset=%lu flags=%u parts=%u errors=%u\r\n",
            (unsigned long)acl_readiness.offsets[i],acl_readiness.flags[i],acl_readiness.parts[i],acl_readiness.errors);
        if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    }
#endif
#else
    char line[160];
    int n;
    (void)comp_v11_hal_debug_write("XFER details=disabled verbose_ble_diagnostics=0\r\n");
#endif
    const comp_wba_recording_transfer_t *t=&product_link.transfer;
    n=snprintf(line,sizeof(line),
        "XFER3 state=%u result=%u id=%lu next=%lu remaining=%lu ready=%u staged=%u gate=%u allowed=%u\r\n",
        (unsigned)t->state,(unsigned)t->last_result,(unsigned long)t->recording_id,
        (unsigned long)t->next_offset,(unsigned long)t->remaining,(unsigned)t->packet_ready,
        (unsigned)t->notify_staged_bytes,(unsigned)notify_gate.waiting,
        (unsigned)sealed_transfer_allowed());
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    if(product_link.segmented) {
        const comp_wba_segment_pull_t *p=&product_link.segmented->pull;
        n=snprintf(line,sizeof(line),"PREFETCH id=%lu packets=%lu erase_packets=%lu fills=%lu leased=%u\r\n",
            (unsigned long)t->recording_id,(unsigned long)p->cache_hits,
            (unsigned long)p->cache_erase_hits,(unsigned long)p->cache_pages,(unsigned)(p->cache!=NULL));
        if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    }
}
static void publish_settings(void)
{
    uint8_t value[17];comp_v11_product_calendar_settings(product,value);
    (void)publish(NULL,COMPANION_GATT_CHAR_SETTINGS,value,sizeof(value));
}
void comp_v11_ble_pet_caption_changed(void)
{
    /* The caption capability is readable before the cooperative recorder
     * dispatcher binds. init publishes it once the GATT host is ready;
     * requiring link_ready there leaves the initial value empty forever. */
    if(product && !fatal_error && comp_v11_ble_host_ready()) {
        uint8_t value[16];comp_v11_product_pet_caption_status(product,value);
        (void)publish(NULL,COMPANION_GATT_CHAR_E_PAPER_CARD_STATUS,value,sizeof(value));
    }
}
void comp_v11_ble_settings_changed(void)
{
    /* apply_preferences also runs before the stack has been initialized.
     * This is a value refresh after a verified save, not a periodic timer. */
    if(product && !fatal_error && comp_v11_ble_host_ready())publish_settings();
}
static bool rename_device(void *context,const uint8_t *name,uint8_t length)
{
    comp_preferences_values_t v=product->preferences.values;(void)context;
    if(length>COMP_PREFS_NAME_BYTES)return false;
    v.name_length=length;memset(v.name,0,sizeof(v.name));memcpy(v.name,name,length);
    return comp_v11_product_save_preferences(product,&v);
}
static void publish_name(void)
{
    names.active_len=product->preferences.values.name_length;
    memcpy(names.active,product->preferences.values.name,names.active_len);
    companion_gatt_ble_name_config_v1_t value;companion_ble_name_get_config(&names,&value);
    value.max_len=COMP_PREFS_NAME_BYTES;
    (void)publish(NULL,COMPANION_GATT_CHAR_BLE_NAME_CONFIG,(uint8_t*)&value,sizeof(value));
}
static void *transfer_cache_acquire(void *context,uint32_t bytes)
{
    (void)context;
    if(!product||product->board->microphone.running||product->runtime.capture_active||
       product->runtime.prepare_pending||product->runtime.start_pending||comp_v11_update_product_busy())return NULL;
    return companion_opus16_rt_workspace_borrow(bytes);
}
static void transfer_cache_release(void *context,void *memory)
{(void)context;companion_opus16_rt_workspace_release(memory);}
static const comp_wba_segment_pull_cache_ports_t transfer_cache_ports={transfer_cache_acquire,transfer_cache_release,NULL};
void comp_v11_ble_release_transfer_workspace(void)
{
    if(link_ready&&product_link.segmented)
        comp_wba_segment_pull_cache_release(&product_link.segmented->pull);
}
bool comp_v11_ble_recording_recovery_idle(void)
{
    return product && !local_clear_pending && !comp_v11_update_product_busy() &&
        !product->pet_profile.writing &&
#if COMPANION_WBA_DUAL_PAIR_CAPTURE
        !comp_v11_dual_pair_owned(product) &&
#endif
        !comp_v11_ble_nvm_busy() && !comp_wba_recording_radio_busy(product_link.segmented) &&
        !(product_link.segmented&&product_link.segmented->interval_token) &&
        product_link.transfer.state!=COMP_WBA_RECORDING_TRANSFER_ACTIVE &&
        product_link.transfer.state!=COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED;
}
bool comp_v11_ble_storage_busy(void)
{
    return (comp_v11_ble_menu_blockers()&0x3cu)!=0u;
}
uint8_t comp_v11_ble_menu_blockers(void)
{
    return (uint8_t)((unsigned)!product | (unsigned)!comp_v11_ble_host_ready()<<1u |
        (unsigned)!link_ready<<2u | (unsigned)(local_clear_pending || (product&&product->pet_profile.writing)
#if COMPANION_WBA_DUAL_PAIR_CAPTURE
            || comp_v11_dual_pair_owned(product)
#endif
        )<<3u |
        (unsigned)comp_v11_update_product_busy()<<4u |
        (unsigned)(product_link.segmented&&product_link.segmented->consume_pending)<<5u);
}
bool comp_v11_ble_recording_timeline_requested(uint32_t token)
{return link_ready&&comp_link_recording_timeline_requested(&product_link,token);}
static bool diagnostics_busy(void)
{
    if(!product)return true;
#if COMPANION_WBA_DUAL_PAIR_CAPTURE
    if(comp_v11_dual_pair_owned(product))return true;
#endif
    bool transfer_busy=
        product_link.transfer.state==COMP_WBA_RECORDING_TRANSFER_ACTIVE ||
        product_link.transfer.state==COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED;
    return comp_diag_log_export_should_defer(comp_v11_update_product_busy(),
        local_clear_pending || !comp_link_heavy_io_allowed(&product_link),
        transfer_busy,product->board->playback_active);
}
static bool maintenance_idle(void)
{
    return product&&link_ready&&product->settings_ready&&
        !product->board->microphone.running&&!product->board->playback_active&&
        !product->board->nor.erase_active&&!product->runtime.capture_active&&
        !product->runtime.prepare_pending&&!product->runtime.command_pending&&!product->runtime.start_pending&&
        !comp_wba_recording_product_recovering(&product->recording)&&
        comp_v11_ble_recording_recovery_idle();
}
static void maintenance_storage_fields(const companion_spi_nor_stm32wba_t *n,
    const comp_wba_recording_pipeline_t *p,uint8_t response[32])
{
    const comp_segment_entry_t *e=&p->consume;
    const bool known=e->reserved_bytes&&e->descriptor.recording_id;
    response[6]=(uint8_t)((unsigned)n->probed|(unsigned)n->erase_suspend_supported<<1u|
        (unsigned)n->info.erase_32k_supported<<2u|(unsigned)n->erase_active<<3u|
        (unsigned)n->erase_command_failed<<4u|(unsigned)known<<5u|
        (unsigned)(p->config.catalog->reclaim_block_sectors==8u)<<6u);
    response[7]=2u;
    comp_maint_put32(response+12u,known?p->config.catalog->data_base+e->extent_offset:0u);
    comp_maint_put32(response+16u,n->erase_address);
    comp_maint_put32(response+20u,known?e->reserved_bytes:0u);
    response[24]=(uint8_t)(n->erase_bytes/4096u);response[25]=p->consume_phase;
    response[26]=n->erase_phase;response[27]=known?e->descriptor.flags:0u;
}
static void maintenance_imu_fields(uint8_t operation,uint8_t response[32])
{
    const comp_lsm6dso_t *imu=&product->board->imu;
    const comp_cont_recording_t *r=&product->recording.capture.engine;
    const uint64_t session=r->active.descriptor.session_id;
    response[7]=1u;
    if(!product->recording.media_ready || !r->token || !session) {
        response[5]=COMP_MAINT_BUSY;response[6]=0u;return;
    }
    response[6]=(uint8_t)((unsigned)(imu->state==COMP_IMU_READY)|
        (unsigned)product->board->microphone.running<<1u|(unsigned)imu->recording_taps<<2u|
        (unsigned)(imu->tap_reads!=0u)<<3u|(unsigned)(r->stats.accepted_pcm_blocks!=0u)<<4u);
    comp_maint_put32(response+12u,(uint32_t)session);comp_maint_put32(response+16u,(uint32_t)(session>>32u));
    comp_maint_put32(response+20u,operation==COMP_MAINT_IMU_TAPS?imu->tap_reads:r->bookmark_request);
    comp_maint_put32(response+24u,operation==COMP_MAINT_IMU_TAPS?imu->tap_counts:r->bookmark_sequence);
}
static void maintenance_imu_power_fields(uint8_t response[32])
{
    const comp_lsm6dso_t *imu=&product->board->imu;
    response[7]=1u;
    response[6]=(uint8_t)((unsigned)(imu->state==COMP_IMU_READY)|
        (unsigned)imu->idle_accel_only<<1u|(unsigned)imu->recording_taps<<2u|
        (unsigned)((imu->wake_source&COMP_LSM6DSO_WAKE_ARMED)!=0u)<<3u|
        (unsigned)imu->event_irq_pending<<4u|(unsigned)comp_lsm6dso_idle_settling(imu)<<5u);
    comp_maint_put32(response+12u,imu->samples);comp_maint_put32(response+16u,imu->errors);
    comp_maint_put32(response+20u,(uint32_t)imu->wake_sequence|((uint32_t)imu->wake_source<<8u)|
        ((uint32_t)imu->state<<16u)|((uint32_t)imu->recovery_attempts<<24u));
    comp_maint_put32(response+24u,imu->reset_ms);
}
#if COMPANION_WBA_CPU_RESIDENCE_PROFILE
static void maintenance_codec_fields(uint8_t operation,uint8_t response[32])
{
    uint32_t values[4];uint8_t flags;
    const uint8_t page=(uint8_t)(operation-COMP_MAINT_CODEC_FIRST);
    response[7]=1u;
    if(page>6u || !comp_v11_cpu_codec_read(page==6u?0u:page,values,&flags)) {
        response[5]=COMP_MAINT_BUSY;response[6]=0u;return;
    }
    if(page==6u) {
        /* Bind the cached profile token to the actual latest logical source,
         * not to a host nonce or a different completed recording. */
        const comp_cont_recording_t *r=&product->recording.capture.engine;
        if(!product->recording.media_ready || r->token!=values[0]) {
            response[5]=COMP_MAINT_BUSY;response[6]=0u;return;
        }
        values[1]=r->token;values[2]=(uint32_t)r->active.descriptor.session_id;
        values[3]=(uint32_t)(r->active.descriptor.session_id>>32u);
    }
    response[6]=flags;
    for(unsigned i=0u;i<4u;i++)comp_maint_put32(response+12u+4u*i,values[i]);
}
#endif
static void maintenance_runtime_fields(uint8_t operation,uint8_t response[32])
{
#if COMPANION_WBA_CPU_DUTY_OBSERVER
    if(operation==COMP_MAINT_CPU_BEGIN||operation==COMP_MAINT_CPU_END)operation=COMP_MAINT_CPU_DUTY;
#endif
    response[6]=0u;response[7]=1u;
    if(operation==COMP_MAINT_IMU_POWER){maintenance_imu_power_fields(response);return;}
    if(operation==COMP_MAINT_IMU_TAPS || operation==COMP_MAINT_IMU_MARKS) {
        maintenance_imu_fields(operation,response);return;
    }
#if COMPANION_WBA_CPU_RESIDENCE_PROFILE
    if(operation>=COMP_MAINT_CODEC_FIRST && operation<=COMP_MAINT_CODEC_LAST) {
        maintenance_codec_fields(operation,response);return;
    }
#endif
    if(operation==COMP_MAINT_STORAGE){maintenance_storage_fields(&product->board->nor,&product->recording.pipeline,response);return;}
    if(operation==COMP_MAINT_CPU_DUTY){
        comp_cpu_duty_snapshot_t s=comp_cpu_duty_snapshot();
        response[7]=3u; /* same bound, first invalid reason and actual WFI count */
        bool valid=s.enabled&&s.windows&&!s.invalid;
        response[6]=(uint8_t)((unsigned)s.enabled|(unsigned)s.active<<1u|
            (unsigned)s.recording<<2u|(unsigned)valid<<3u|(unsigned)s.invalid_reason<<4u);
        comp_maint_put32(response+12u,s.windows);
        comp_maint_put32(response+16u,s.peak_busy_upper_us);
        comp_maint_put32(response+20u,s.invalid);
        comp_maint_put32(response+24u,s.waits);return;
    }
    if(operation==COMP_MAINT_MEMORY) {
        const comp_v11_memory_stats_t *s=comp_v11_memory_observe();
        response[6]=(uint8_t)((unsigned)s->stack.sampled|
            (unsigned)s->stack.guard_failed<<1u|(unsigned)s->stack.low_latched<<2u);
        comp_maint_put32(response+12u,s->stack_reserved_bytes);
        comp_maint_put32(response+16u,s->stack.minimum_free_bytes);
        comp_maint_put32(response+20u,SystemCoreClock);
        comp_maint_put32(response+24u,HAL_GetTick());
        return;
    }
    const comp_v11_microphone_hal_t *mic=&product->board->microphone;
    if(operation==COMP_MAINT_AUDIO_TIMING) {
        response[7]=2u; /* precise conservative upper microseconds */
        const comp_duration_stats_t *encode=&product->recording.capture.engine.stats.encoding_duration;
        const comp_duration_stats_t *pdm=&mic->pdm_duration;
        bool media=product->recording.media_ready;
        uint32_t value=0u;bool valid;
        response[6]=(uint8_t)((unsigned)media<<4u|(unsigned)mic->running<<5u);
        comp_maint_put32(response+12u,media?encode->samples:0u);
        comp_maint_put32(response+16u,pdm->samples);
        valid=media&&comp_duration_stats_percentile_upper_us(encode,95u,&value);
        comp_maint_timing16(response,20u,0u,valid,value);
        valid=media&&comp_duration_stats_peak_upper_us(encode,&value);
        comp_maint_timing16(response,22u,1u,valid,value);
        valid=comp_duration_stats_percentile_upper_us(pdm,95u,&value);
        comp_maint_timing16(response,24u,2u,valid,value);
        valid=comp_duration_stats_peak_upper_us(pdm,&value);
        comp_maint_timing16(response,26u,3u,valid,value);
        return;
    }
    comp_v11_microphone_stats_t s;
    comp_v11_microphone_hal_get_stats(mic,&s);
    response[6]=(uint8_t)((unsigned)s.initialized|(unsigned)s.running<<1u);
    if(operation==COMP_MAINT_AUDIO_FAULTS) {
        comp_maint_put32(response+12u,s.event_queue_overflows);
        comp_maint_put32(response+16u,s.stale_dma_halves);
        comp_maint_put32(response+20u,s.processing_rejections);
        comp_maint_put32(response+24u,product->capture_deadline_faults);
    } else {
        response[6]|=(uint8_t)((unsigned)product->recording.media_ready<<2u);
        comp_maint_put32(response+12u,s.processed_dma_halves);
        comp_maint_put32(response+16u,s.error_irqs);
        comp_maint_put32(response+20u,product->max_capture_foreground_ms);
        comp_maint_put32(response+24u,product->board->microphone_max_poll_ms);
    }
}
static bool maintenance_reply(uint8_t operation,uint8_t result,uint32_t request)
{
    /* A later accepted START may have changed ownership after this read
     * request was queued. Recheck at the actual scan, including retries. */
    if(operation==COMP_MAINT_MEMORY&&result==COMP_MAINT_OK&&!maintenance_idle())result=COMP_MAINT_BUSY;
    uint8_t response[32],bonds=255u,flags=0u;
    if(operation<COMP_MAINT_BLE_DIAGNOSTICS) {
        if(product->preferences.persisted)flags|=1u;
        if(comp_preferences_are_defaults(&product->preferences.values))flags|=2u;
        if(maintenance_idle()&&comp_v11_ble_bond_count(&bonds))flags|=4u;
        if(product->preferences.values.radio_enabled)flags|=8u;
    }
    comp_maint_response(response,operation,result,request,flags,bonds,product->preferences.generation,
        comp_preferences_fingerprint(&product->preferences.values),comp_v11_ble_bond_generation(),maintenance.request_id);
    if(operation>=COMP_MAINT_BLE_DIAGNOSTICS&&result==COMP_MAINT_OK) {
        if(operation==COMP_MAINT_BLE_DIAGNOSTICS)comp_v11_ble_maintenance_diagnostics(response);
        else maintenance_runtime_fields(operation,response);
        comp_maint_put32(response+28u,companion_crc32(0u,response,28u));
    }
    return publish(NULL,COMPANION_GATT_CHAR_REPAIR_CONTROL,response,sizeof(response));
}
static void maintenance_request(const companion_gatt_event_t *e)
{
    uint8_t operation;uint32_t request;
    if(!secured||!product_link.subscribed[COMPANION_GATT_CHAR_REPAIR_CONTROL]||
       !comp_maint_request(e->payload,e->payload_len,&operation,&request)) {
        ++product_link.rejected_writes;return;
    }
    if(maintenance.pending) {
        (void)maintenance_reply(operation,maintenance.request_id==request&&maintenance.operation==operation?
            COMP_MAINT_PENDING:COMP_MAINT_BUSY,request);return;
    }
    maintenance.request_id=request;maintenance.operation=operation;maintenance.notify=true;
    maintenance.result=COMP_MAINT_BUSY;
    /* Read-only cached scalars remain useful during recording/storage work.
     * Keep the existing queued-reply owner and secured subscription checks. */
    if(operation==COMP_MAINT_BLE_DIAGNOSTICS){maintenance.result=COMP_MAINT_OK;return;}
#if COMPANION_WBA_CPU_DUTY_OBSERVER
    if(operation==COMP_MAINT_CPU_BEGIN||operation==COMP_MAINT_CPU_END) {
        comp_cpu_duty_snapshot_t s=comp_cpu_duty_snapshot();
        if(s.recording&&s.active)return;
        if(operation==COMP_MAINT_CPU_BEGIN) {
            if(s.active||!maintenance_idle()||product->input.mode!=COMP_INPUT_RECORDER)return;
            comp_cpu_duty_begin(request,false);
        } else comp_cpu_duty_end(0u,false);
        s=comp_cpu_duty_snapshot();
        maintenance.result=s.enabled&&!s.invalid?COMP_MAINT_OK:COMP_MAINT_FAILED;
        return;
    }
#endif
    if(operation>=COMP_MAINT_MEMORY) {
        /* Only a stack scan needs a stopped/idle owner; cached audio scalars
         * remain readable without pausing capture or erasing/resetting state. */
        if(operation!=COMP_MAINT_MEMORY||maintenance_idle())maintenance.result=COMP_MAINT_OK;
        return;
    }
    if(!maintenance_idle())return;
    maintenance.result=COMP_MAINT_FAILED;
    if(operation==COMP_MAINT_QUERY)maintenance.result=COMP_MAINT_OK;
    else if(operation==COMP_MAINT_PAIR_WINDOW) {
        if(comp_v11_ble_open_pairing_window())maintenance.result=COMP_MAINT_OK;
    } else if(operation==COMP_MAINT_DEFAULTS) {
        if(comp_v11_product_restore_defaults(product)) {
            maintenance.result=COMP_MAINT_OK;publish_settings();publish_name();
        }
    } else if(operation==COMP_MAINT_CLEAR_BONDS) {
        maintenance.failures_before=comp_v11_ble_bond_failures();
        if(comp_v11_ble_clear_bonds()) {maintenance.pending=true;maintenance.result=COMP_MAINT_PENDING;}
    }
}
static void maintenance_poll(void)
{
    if(maintenance.pending) {
        if(comp_v11_ble_bond_failures()!=maintenance.failures_before) {
            maintenance.result=COMP_MAINT_FAILED;maintenance.pending=false;maintenance.notify=true;
        } else if(!comp_v11_ble_nvm_busy()) {
            uint8_t count=255u;
            maintenance.result=comp_v11_ble_bond_count(&count)&&count==0u?COMP_MAINT_OK:COMP_MAINT_FAILED;
            maintenance.pending=false;maintenance.notify=true;
        }
    }
    if(maintenance.notify&&secured&&product_link.subscribed[COMPANION_GATT_CHAR_REPAIR_CONTROL]&&
       maintenance_reply(maintenance.operation,maintenance.result,maintenance.request_id))maintenance.notify=false;
}
static bool can_update_storage_mount(bool ota_owner)
{
#if COMPANION_WBA_DUAL_PAIR_CAPTURE
    if(comp_v11_dual_pair_owned(product))return false;
#endif
    if(!product || !product->storage_layout_ready || !product->recording.media_ready || product->pet_profile.writing)return false;
    const comp_runtime_t *r=&product->runtime;
    const comp_wba_recording_pipeline_t *p=&product->recording.pipeline;
    return
#if COMPANION_WBA_EXTERNAL_BOND_STORE
        /* The initial OTA admission cannot overtake a NOR metadata writer.
         * Once OTA owns the operation, later queued NVM changes defer to its
         * existing reboot-durable phase rather than deadlocking the payload. */
        (ota_owner || comp_wba_recording_product_boot_retry_owned(&product->recording) || !comp_v11_ble_nvm_busy()) &&
#endif
        !product->board->microphone.running && !product->board->playback_active &&
        !r->capture_active && !r->prepare_pending && !r->command_pending && !r->start_pending && !r->menu_pending &&
        !(product_link.segmented&&product_link.segmented->consume_pending) && !local_clear_pending &&
        product_link.transfer.state!=COMP_WBA_RECORDING_TRANSFER_ACTIVE &&
        product_link.transfer.state!=COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED &&
        (p->state==COMP_PIPE_IDLE||p->state==COMP_PIPE_FINISHED)&&!p->config.catalog->phase&&
        !p->config.storage->poisoned&&(!product->board->nor.erase_active||
            (ota_owner&&comp_v11_update_product_owns_erase()))&&
        /* Own-tail release changes free capacity, not the extent inventory.
         * The workspace allocator checks its boundary against that inventory. */
        (p->workspace_bytes||comp_wba_recording_product_catalog_current(&product->recording));
}
bool comp_v11_ble_can_update_storage_mount(void)
{return can_update_storage_mount(false);}
bool comp_v11_ble_can_continue_update(void)
{return product&&((product->recording_ready&&product->recording.ready)||
    (comp_wba_recording_product_salvaging(&product->recording)&&comp_wba_recording_product_update_available(&product->recording)))&&can_update_storage_mount(true);}
bool comp_v11_ble_can_update(void)
{ return product&&((product->recording_ready&&product->recording.ready)||
    (comp_wba_recording_product_salvaging(&product->recording)&&comp_wba_recording_product_update_available(&product->recording)))&&comp_v11_ble_can_update_storage_mount(); }
bool comp_v11_ble_menu(comp_screen_menu_action_t action)
{
    comp_preferences_values_t v;
    if(comp_v11_ble_menu_blockers())return false;
    v=product->preferences.values;
    switch(action) {
    case COMP_SCREEN_MENU_ACTION_PHONE_RECONNECT:return comp_v11_ble_reconnect(false);
    case COMP_SCREEN_MENU_ACTION_BROWSER_PAIR:
        if(!v.radio_enabled) {v.radio_enabled=true;if(!comp_v11_product_save_preferences(product,&v))return false;}
        return comp_v11_ble_reconnect(true);
    case COMP_SCREEN_MENU_ACTION_BROWSER_CONNECTION_TOGGLE:
        v.radio_enabled=!v.radio_enabled;return comp_v11_product_save_preferences(product,&v);
    case COMP_SCREEN_MENU_ACTION_BROWSER_RESET_NAME:
        if(!rename_device(NULL,(const uint8_t*)COMP_PREFS_DEFAULT_NAME,COMP_PREFS_DEFAULT_NAME_BYTES))return false;
        companion_ble_name_init(&names);names.active_len=COMP_PREFS_DEFAULT_NAME_BYTES;
        memcpy(names.active,COMP_PREFS_DEFAULT_NAME,COMP_PREFS_DEFAULT_NAME_BYTES);publish_name();return true;
    case COMP_SCREEN_MENU_ACTION_BROWSER_CLEAR_RECORDINGS:
        if(!comp_link_discard_all_confirmed(&product_link))return false;
        local_clear_pending=true;return true;
    default:return false;
    }
}
comp_runtime_menu_dispatch_t comp_v11_ble_menu_begin(comp_screen_menu_action_t action,uint32_t token)
{
    if(!product || !comp_v11_ble_host_ready())return COMP_RUNTIME_MENU_UNAVAILABLE;
    if(comp_v11_ble_storage_busy())return COMP_RUNTIME_MENU_BUSY;
    uint32_t generation=secure_generation;
    if(!comp_v11_ble_menu(action))return COMP_RUNTIME_MENU_FAILED;
    if(action==COMP_SCREEN_MENU_ACTION_BROWSER_CLEAR_RECORDINGS) {
        local_clear_token=token;
        return COMP_RUNTIME_MENU_PENDING;
    }
    if(action==COMP_SCREEN_MENU_ACTION_BROWSER_PAIR || action==COMP_SCREEN_MENU_ACTION_PHONE_RECONNECT) {
        local_pair_token=token;local_pair_generation=generation;
        local_pair_deadline=HAL_GetTick()+120000u;
        return COMP_RUNTIME_MENU_PENDING;
    }
    /* Name/radio preferences have finished the verified persistent save.
     * This reports saved settings, never a fabricated physical connection. */
    return COMP_RUNTIME_MENU_COMPLETE;
}
static void menu_completions(uint32_t now)
{
    if(local_clear_pending) {
        if(product_link.segmented&&product_link.segmented->consume_pending) {
            (void)comp_runtime_menu_retrying(&product->runtime,local_clear_token,
                comp_wba_recording_pipeline_consume_result(&product->recording.pipeline)!=COMP_SEG_PENDING);
        } else {
            local_clear_pending=false;
            (void)comp_runtime_menu_complete(&product->runtime,local_clear_token,COMP_RUNTIME_OK,now);
            local_clear_token=0u;
        }
    }
    if(local_pair_token) {
        if(linked && secured && secure_generation!=local_pair_generation) {
            (void)comp_runtime_menu_complete(&product->runtime,local_pair_token,COMP_RUNTIME_OK,now);
            local_pair_token=0u;
        } else if(fatal_error || !product->preferences.values.radio_enabled) {
            (void)comp_runtime_menu_complete(&product->runtime,local_pair_token,COMP_RUNTIME_UNAVAILABLE,now);
            local_pair_token=0u;
        } else if((int32_t)(now-local_pair_deadline)>=0) {
            (void)comp_runtime_menu_pair_timeout(&product->runtime,local_pair_token,now);
            local_pair_token=0u;
        }
    }
}
static void event(const companion_gatt_event_t *e,void *context)
{
    if(!e || !product)return;
    if(e->type==COMPANION_GATT_EVENT_WRITE&&e->char_id==COMPANION_GATT_CHAR_SETTINGS&&
       e->payload_len>=4u&&!memcmp(e->payload,"CIN1",4u)) {
        if(!secured){++product_link.rejected_writes;return;}
        uint8_t response[64];
        size_t n=comp_v11_product_input_request(product,e->payload,e->payload_len,
            comp_v11_update_product_busy()||!link_ready,HAL_GetTick(),response);
        if(!n){++product_link.rejected_writes;return;}
        if(e->payload_len>=7u&&e->payload[5]==1u&&response[5]==0u&&response[6]==COMP_INPUT_POINTER){
            pointer_fusion.active=false;pointer_sample_ms=0u;pointer_heading=0.0f;pointer_event_sequence=0u;
        }
        input_client=true;
        (void)companion_gatt_stm32wb_set_read_value(COMPANION_GATT_CHAR_SETTINGS,response,(uint16_t)n);
        /* Pointer ACK is one-way. Echoing another64B notification for every
         * ACK/retry competes with live CIM samples and is ignored by the host.
         * Keep query/mode/error replies; input_notify sends the next actual
         * queued edge with request0 after the acknowledged head is removed. */
        if(product_link.subscribed[COMPANION_GATT_CHAR_SETTINGS]&&
           (e->payload[5]!=2u||response[5]!=0u))
            (void)publish(NULL,COMPANION_GATT_CHAR_SETTINGS,response,(uint16_t)n);
        return;
    }
    if(e->type==COMPANION_GATT_EVENT_WRITE&&e->char_id==COMPANION_GATT_CHAR_REPAIR_CONTROL) {
        maintenance_request(e);return;
    }
    if(e->type==COMPANION_GATT_EVENT_WRITE && e->char_id==COMPANION_GATT_CHAR_SETTINGS &&
       e->payload_len>=4u && !memcmp(e->payload,"PMP1",4u)) {
        if(!secured) {++product_link.rejected_writes;return;}
        uint8_t response[96];
        bool busy=!link_ready || local_clear_pending || comp_v11_update_product_busy() ||
            comp_v11_ble_nvm_busy() ||
            (product_link.segmented&&product_link.segmented->consume_pending) ||
            product_link.transfer.state==COMP_WBA_RECORDING_TRANSFER_ACTIVE ||
            product_link.transfer.state==COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED;
        size_t n=comp_v11_product_pet_profile(product,e->payload,e->payload_len,busy,HAL_GetTick(),response);
        if(!n || response[5]!=COMP_PET_STORE_OK)++product_link.rejected_writes;
        if(n && e->payload[4]==7u && response[5]==COMP_PET_STORE_OK)publish_settings();
        else if(n)(void)companion_gatt_stm32wb_set_read_value(COMPANION_GATT_CHAR_SETTINGS,response,(uint16_t)n);
        return;
    }
    if(e->type==COMPANION_GATT_EVENT_WRITE &&
       e->char_id==COMPANION_GATT_CHAR_E_PAPER_CARD_WRITE &&
       e->payload_len>=4u && !memcmp(e->payload,"PCP1",4u)) {
        if(!secured || !comp_v11_product_pet_caption(product,e->payload,e->payload_len,HAL_GetTick()))
            ++product_link.rejected_writes;
        comp_v11_ble_pet_caption_changed();return;
    }
    companion_gatt_delete_privacy_v1_t traced_request={0};
    bool trace=e->type==COMPANION_GATT_EVENT_WRITE &&
        e->char_id==COMPANION_GATT_CHAR_DELETE_PRIVACY &&
        reclaim_trace_request(e->payload,e->payload_len,&traced_request);
    uint32_t rejected_before=product_link.rejected_writes;
    if(trace)comp_diag_log_record_code(COMP_DIAG_EVT_GATT_RECLAIM_DISPATCH,COMP_DIAG_SEV_INFO,
        traced_request.request_id,traced_request.recording_id,e->payload_len,reclaim_trace_state());
    if(!secured || e->type!=COMPANION_GATT_EVENT_WRITE) {
        comp_link_event(context,e,HAL_GetTick());
        if(trace)comp_diag_log_record_code(COMP_DIAG_EVT_GATT_RECLAIM_RETURN,COMP_DIAG_SEV_WARN,
            traced_request.request_id,traced_request.recording_id,
            product_link.rejected_writes-rejected_before,reclaim_trace_state());
        return;
    }
    if(comp_v11_update_product_busy() &&
       (e->char_id==COMPANION_GATT_CHAR_SETTINGS || e->char_id==COMPANION_GATT_CHAR_BLE_NAME_CONFIG)) {
        ++product_link.rejected_writes;publish_settings();publish_name();return;
    }
    if(e->char_id==COMPANION_GATT_CHAR_SETTINGS) {
        bool accepted=comp_v11_product_apply_settings(product,e->payload,e->payload_len);
        if(!accepted)++product_link.rejected_writes;
        publish_settings();return;
    }
    if(e->char_id==COMPANION_GATT_CHAR_BLE_NAME_CONFIG) {
        companion_gatt_ble_name_config_v1_t request;
        if(companion_gatt_parse_ble_name_config_v1(e->payload,e->payload_len,&request)!=COMPANION_GATT_PARSE_OK ||
           request.name_len>COMP_PREFS_NAME_BYTES) {++product_link.rejected_writes;return;}
        /* WBA changes GAP's value immediately and the next advertising name.
         * It need not interrupt an encrypted connection to rename. */
        companion_ble_name_set_connection(&names,false,!comp_link_heavy_io_allowed(&product_link));
        companion_ble_name_result_t result=companion_ble_name_handle(&names,&request,0,rename_device,NULL);
        request.status=(uint8_t)result;request.max_len=COMP_PREFS_NAME_BYTES;
        request.name_len=names.active_len;memcpy(request.name,names.active,names.active_len);
        (void)publish(NULL,e->char_id,(uint8_t*)&request,sizeof(request));return;
    }
    if(e->char_id==COMPANION_GATT_CHAR_DIAGNOSTICS_LOG_PULL) {
        companion_gatt_diag_log_pull_v1_t request={0};
        comp_diag_log_export_packet_t packet;size_t size=0u;bool sent=false;
        bool subscribed=product_link.subscribed[e->char_id];
        if(e->payload_len==sizeof(request))memcpy(&request,e->payload,sizeof(request));
        if(e->payload_len!=sizeof(request) || request.schema_version!=1u) {
            ++product_link.rejected_writes;
            if(subscribed && comp_diag_log_export_build_status(
                   request.cursor,COMP_DIAG_LOG_EXPORT_FLAG_INVALID_REQUEST,&packet,&size))
                sent=publish(NULL,e->char_id,(uint8_t*)&packet,(uint16_t)size);
        } else if(diagnostics_busy()) {
            if(subscribed && comp_diag_log_export_build_status(
                   request.cursor,COMP_DIAG_LOG_EXPORT_FLAG_BUSY,&packet,&size))
                sent=publish(NULL,e->char_id,(uint8_t*)&packet,(uint16_t)size);
        } else {
            comp_diag_log_export_request_t query={request.cursor,request.source_mask,request.severity_mask,request.max_events,request.max_bytes};
            if(subscribed && comp_diag_log_export_build(&query,&packet,&size))
                sent=publish(NULL,e->char_id,(uint8_t*)&packet,(uint16_t)size);
        }
        comp_diag_log_record_code(COMP_DIAG_EVT_GATT_LOG_EXPORT_REQUEST,
            sent?COMP_DIAG_SEV_INFO:COMP_DIAG_SEV_WARN,request.cursor,
            size>=COMP_DIAG_LOG_EXPORT_HEADER_BYTES?packet.event_count:0u,
            size>=COMP_DIAG_LOG_EXPORT_HEADER_BYTES?packet.flags:0u,subscribed);
        return;
    }
    const bool segment_trace=e->char_id==COMPANION_GATT_CHAR_DELETE_PRIVACY &&
        e->payload_len==84u&&!memcmp(e->payload,"CRA2\x02\x00\x54\x00",8u);
    uint32_t segment_id=0u;
    if(segment_trace) {
        const uint8_t *p=e->payload;
        segment_id=(uint32_t)p[40]|((uint32_t)p[41]<<8u)|((uint32_t)p[42]<<16u)|((uint32_t)p[43]<<24u);
    }
    comp_link_event(context,e,HAL_GetTick());
    if(segment_trace)comp_diag_log_record_code(COMP_DIAG_EVT_GATT_SEGMENT_CONSUME_DISPATCH,
        product_link.rejected_writes!=rejected_before?COMP_DIAG_SEV_WARN:COMP_DIAG_SEV_INFO,
        segment_id,product_link.rejected_writes-rejected_before,reclaim_trace_state(),0u);
    if(trace)comp_diag_log_record_code(COMP_DIAG_EVT_GATT_RECLAIM_RETURN,
        product_link.rejected_writes!=rejected_before?COMP_DIAG_SEV_WARN:COMP_DIAG_SEV_INFO,
        traced_request.request_id,traced_request.recording_id,
        product_link.rejected_writes-rejected_before,reclaim_trace_state());
}
bool comp_v11_ble_init(comp_v11_product_app_t *app)
{
    RTC_PrivilegeStateTypeDef privilege={0};
    RCC_PeriphCLKInitTypeDef clock={0};
    if(!app || !app->board || (app->board->faults&(COMP_V11_FAULT_CLOCK|COMP_V11_FAULT_LSE))) return false;
    product=app;link_ready=false;
    comp_diag_log_init();comp_diag_log_set_clock(diagnostic_clock,NULL);
    comp_diag_log_record_code(COMP_DIAG_EVT_BOOT_INIT_RESULT,COMP_DIAG_SEV_INFO,app->board->faults,
        app->recording_ready,app->assets_ready,app->storage_layout_ready);
    companion_ble_name_init(&names);names.active_len=app->preferences.values.name_length;
    memcpy(names.active,app->preferences.values.name,names.active_len);
    comp_v11_ble_apply_preferences(&app->preferences.values);
    clock.PeriphClockSelection=RCC_PERIPHCLK_RADIOST;
    clock.RadioSlpTimClockSelection=RCC_RADIOSTCLKSOURCE_LSE;
    if(HAL_RCCEx_PeriphCLKConfig(&clock)!=HAL_OK)return false;
    /* Preserve the binary wireless timebase across reset. User time is a
     * checked UTC-of-day anchor in separate backup registers, not calendar
     * mode or a replacement of ST's timer/alarm ownership. */
    HAL_PWR_EnableBkUpAccess();
    __HAL_RCC_RTCAPB_CLK_ENABLE();
    bool continuous_clock=comp_v11_clock_domain_continuous();
    __HAL_RCC_RTC_CONFIG(RCC_RTCCLKSOURCE_LSE);
    hrtc.Instance=RTC; hrtc.Init.AsynchPrediv=31;
    hrtc.Init.OutPut=RTC_OUTPUT_DISABLE; hrtc.Init.BinMode=RTC_BINARY_ONLY;
    hrtc.Init.OutPutPolarity=RTC_OUTPUT_POLARITY_HIGH;
    hrtc.Init.OutPutType=RTC_OUTPUT_TYPE_OPENDRAIN;
    if(HAL_RTC_Init(&hrtc)!=HAL_OK || HAL_RTCEx_PrivilegeModeSet(&hrtc,&privilege)!=HAL_OK ||
       HAL_RTCEx_SetSSRU_IT(&hrtc)!=HAL_OK)return false;
    if(!comp_v11_clock_domain_continuous())return false;
    HAL_NVIC_SetPriority(RTC_IRQn,5,0);HAL_NVIC_EnableIRQ(RTC_IRQn);
    __HAL_RCC_CRC_CLK_ENABLE();
    /* Board clock has already set the immutable PLL. CFG_SCM_SUPPORTED=0
     * prevents the radio clock manager from replacing the audio clock. */
    comp_v11_ble_bond_media_bind(&app->board->nor);
    (void)MX_APPE_Init(NULL);
    comp_v11_clock_restore(&app->clock,continuous_clock);
    if(!fatal_error && comp_v11_ble_host_ready()) {
        UTIL_SEQ_RegTask(1u<<CFG_TASK_SEND_NOTIF_ID,UTIL_SEQ_RFU,send_sealed_transfer);
        if(!comp_v11_update_product_init(app))return false;
        comp_v11_ble_pet_caption_changed();
        publish_settings();publish_name();
        /* Type may read public identity before pairing finishes. Initialize
         * these values now; private values remain behind the encryption gate. */
        companion_gatt_device_status_v1_t device={1,0,0,COMPANION_WBA_APP_VERSION,COMPANION_WBA_BUILD_ID,COMPANION_WBA_BOARD_ID,HAL_GetTick()};
        companion_gatt_battery_charge_v1_t battery={1,255,0,0,0,0};
        companion_gatt_ota_readiness_v1_t ota={1,0,0,255,0,0xFFFFu,0,0,{0}};
        return publish(NULL,COMPANION_GATT_CHAR_DEVICE_STATUS,(uint8_t*)&device,sizeof(device)) &&
            publish(NULL,COMPANION_GATT_CHAR_BATTERY_CHARGE,(uint8_t*)&battery,sizeof(battery)) &&
            publish(NULL,COMPANION_GATT_CHAR_OTA_READINESS,(uint8_t*)&ota,sizeof(ota));
    }
    return false;
}
void comp_v11_ble_live_follow_progress(void)
{
    /* Sealed sending owns a normal foreground slice after PCM/codec
     * service. Never suspend the codec to run NOR/GATT on a side stack.
     * Radio IRQs remain enabled and the stopped-file pump is unchanged. */
    if(__get_IPSR()!=0u || !product || sequencer_depth || notify_pump.dispatching ||
       notify_gate.in_call || !sealed_during_capture_ready() ||
       (uint32_t)(HAL_GetTick()-product->capture_cycle_started_ms)>=7u)return;
    const uint32_t radio=(1u<<CFG_TASK_BLE_HOST)|(1u<<CFG_TASK_LINK_LAYER)|
        (1u<<CFG_TASK_HCI_ASYNCH_EVT_ID)|(1u<<CFG_TASK_SEND_NOTIF_ID);
    run_foreground_tasks(radio);
}
void comp_v11_ble_transfer_progress(void)
{
    if(sequencer_depth || !sealed_transfer_work() || comp_v11_ble_nvm_busy())return;
    /* Called with the shared NOR chip deselected. Only stack background work
     * and the already authorized sealed transfer can run inside rendering.
     * Control writes stay queued for the normal foreground owner. */
    run_foreground_tasks(UTIL_SEQ_DEFAULT & ~(1u<<CFG_TASK_FLASH_MANAGER));
}
void comp_v11_ble_idle_background_progress(void)
{
    if(!product || sequencer_depth || !comp_v11_ble_host_ready() ||
       product->board->microphone.running || sealed_transfer_work())return;
    /* Long paired-image hashes must not starve the true entropy refill task
     * while the radio consumes random words in interrupts. Never dispatch a
     * NOR writer or the file pump inside a caller's read/verification owner. */
    run_foreground_tasks(UTIL_SEQ_DEFAULT & ~(1u<<CFG_TASK_FLASH_MANAGER) &
        ~(1u<<CFG_TASK_SEND_NOTIF_ID));
}
uint32_t comp_v11_ble_transfer_backpressure(void)
{
    /* Count actual SDK resource failures, not cheap polls of the wait gate. */
    return notify_resource_failures;
}
static void input_notify(void)
{
    if(!input_client||!secured||!product_link.subscribed[COMPANION_GATT_CHAR_SETTINGS])return;
    /* Compare the two notification signals before serializing/CRC'ing64B.
     * Events remain sticky until publish succeeds; a changed packet updates
     * the cache from its actual contents, not this earlier observation. */
    const uint16_t signals=comp_v11_product_input_signals(product);
    const comp_pointer_event_t *edge=comp_input_pointer_event(&product->input);
    const uint32_t now=HAL_GetTick();
    if(edge){if(edge->sequence==pointer_event_sequence&&now-pointer_event_sent_ms<40u)return;}
    else if(!product->input.events&&input_feedback==(uint8_t)(signals>>8u)&&input_flags==(uint8_t)signals)return;
    uint8_t response[64];comp_v11_product_input_status(product,0u,0u,response);
    if(publish(NULL,COMPANION_GATT_CHAR_SETTINGS,response,sizeof(response))) {
        product->input.events=0u;input_feedback=response[23];input_flags=response[7];
        if(edge){pointer_event_sequence=edge->sequence;pointer_event_sent_ms=now;}
    }
}
static void pointer_notify(void)
{
    if(product->input.mode!=COMP_INPUT_POINTER){pointer_fusion.active=false;return;}
    if(!input_client||!secured||product->input.mode!=COMP_INPUT_POINTER||
       !product_link.subscribed[COMPANION_GATT_CHAR_SETTINGS]||
       comp_runtime_recording_owned(&product->runtime)||comp_v11_update_product_busy())return;
    const uint32_t now=HAL_GetTick();
    const comp_lsm6dso_t *imu=&product->board->imu;
    const comp_imu_sample_t *sample=&product->board->imu_sample;
    if(imu->state!=COMP_IMU_READY||imu->idle_accel_only||now-sample->timestamp_ms>100u||
       sample->timestamp_ms==pointer_sample_ms)return;
    comp_imu_fused_sample_t fused;
    comp_cpu_duty_span_t pointer_span=comp_cpu_duty_span_begin();
    comp_cpu_duty_span_t fusion_span=comp_cpu_duty_span_begin();
    bool updated=comp_imu_fusion_update(&pointer_fusion,sample,&fused);
    comp_cpu_duty_span_end(COMP_DUTY_FUSION,fusion_span);
    if(!updated){comp_cpu_duty_span_end(COMP_DUTY_POINTER_SEND,pointer_span);return;}
    uint8_t packet[40];uint16_t packet_bytes=32u;
    if(++pointer_sequence==0u)++pointer_sequence;
    const float yaw=comp_imu_pointer_yaw(&fused);
    pointer_heading=comp_imu_pointer_heading(pointer_heading,yaw,pointer_sample_ms?sample->timestamp_ms-pointer_sample_ms:0u);
    if(product->input.options&COMP_INPUT_POINTER_CONTACT){
        comp_imu_pointer_contact_packet(&fused,sample,pointer_sequence,
            (product->input.flags&COMP_INPUT_HELD)!=0u,(uint8_t)product->input.flick_sample_ms,packet);
        packet_bytes=40u;
    }else if(product->input.options&COMP_INPUT_POINTER_RAW)comp_imu_pointer_pack(sample->timestamp_ms,pointer_sequence,
        (product->input.flags&COMP_INPUT_HELD)!=0u,(uint8_t)product->input.flick_sample_ms,
        5u,fused.ready,sample->accel_mg,sample->gyro_mdps,packet);
    else if(comp_input_pointer_v4(&product->input)&&!(product->input.options&COMP_INPUT_POINTER_FUSED_RATES))comp_imu_pointer_aim_packet(&fused,pointer_sequence,
        (product->input.flags&COMP_INPUT_HELD)!=0u,(uint8_t)product->input.flick_sample_ms,pointer_heading,yaw,packet);
    else comp_imu_pointer_fused_packet(&fused,pointer_sequence,
        (product->input.flags&COMP_INPUT_HELD)!=0u,(uint8_t)product->input.flick_sample_ms,packet);
    pointer_sample_ms=sample->timestamp_ms;
    /* One current sample, no retry queue: failed delivery is superseded by
     * the next sample, with the original sensor timestamp and button level. */
    (void)publish(NULL,COMPANION_GATT_CHAR_SETTINGS,packet,packet_bytes);
    comp_cpu_duty_span_end(COMP_DUTY_POINTER_SEND,pointer_span);
}
#if COMPANION_WBA_CPU_DUTY_OBSERVER
static void ble_poll_body(void)
#else
void comp_v11_ble_poll(void)
#endif
{
    uint32_t tasks=UTIL_SEQ_DEFAULT;
    bool writes_allowed;
    if(!product)return;
    if(link_ready&&!sealed_transfer_work())comp_v11_ble_release_transfer_workspace();
    if(fatal_error){menu_completions(HAL_GetTick());return;}
    writes_allowed=stack_writes_allowed();
    if(!writes_allowed)
        tasks &= ~(1u<<CFG_TASK_FLASH_MANAGER);
    comp_cpu_duty_span_t nvm_span=comp_cpu_duty_span_begin();
    comp_v11_ble_nvm_poll(HAL_GetTick(),writes_allowed);
    comp_cpu_duty_span_end(COMP_DUTY_NVM,nvm_span);
    comp_cpu_duty_span_t seq_span=comp_cpu_duty_span_begin();
    run_foreground_tasks(tasks);
    comp_cpu_duty_span_end(COMP_DUTY_SEQ,seq_span);
    comp_v11_ble_advertise_poll(HAL_GetTick(),advertising_commands_allowed());
    if(comp_v11_ble_host_ready()) {
        /* Stack initialization is independent of the cooperative media boot.
         * Bind the sole V2 dispatcher only after recovery and WUS2 reconcile. */
        if(!link_ready&&comp_wba_recording_product_readable(&product->recording)) {
            comp_link_config_t config={&product->runtime,NULL,NULL,&product->board->features,publish,product};
            link_ready=comp_link_init_segmented(&product_link,&config,&product_link.io.segmented_state,
                &product->recording.pipeline,comp_v11_ble_value_capacity());
            if(link_ready) {
                comp_wba_segment_pull_cache_bind(&product_link.segmented->pull,&transfer_cache_ports);
                download_read_backend=product_link.transfer.backend;
                product_link.transfer.backend=&observed_backend;
                comp_link_connection(&product_link,linked,secured,HAL_GetTick());
            }
        }
        if(!link_ready){comp_v11_update_product_poll();return;}
        /* NVM/Flash mutations keep writes_allowed's existing stricter gate.
         * Controller-only negotiation may run in an admitted OTA receive
         * window; manifest/hash/install/trial are not bulk payload work. */
        bool interval_hint=comp_wba_recording_radio_interval_hint(product_link.segmented,
            HAL_GetTick(),writes_allowed&&linked&&secured);
        const bool update_busy=comp_v11_update_product_busy();
        /* Existing OTA ownership may include its own erase or deferred NVM.
         * Use the same continuation gate as the data path; initial admission
         * remains strict, and all non-OTA owners still block controller work. */
        const bool update_idle=update_busy&&comp_v11_ble_can_continue_update();
        const bool ota_bulk=comp_v11_update_product_bulk_transfer();
        const comp_v11_ble_bulk_direction_t bulk_direction=ota_bulk?
            COMP_V11_BLE_BULK_HOST_TO_DEVICE:(sealed_transfer_work()||interval_hint)?
            COMP_V11_BLE_BULK_DEVICE_TO_HOST:COMP_V11_BLE_BULK_NONE;
        const bool pointer_hint=input_client&&secured&&product->input.mode==COMP_INPUT_POINTER;
        comp_v11_ble_bulk_profile(bulk_direction,interval_hint||ota_bulk||pointer_hint,
            writes_allowed||(ota_bulk&&update_idle),
            !product->board->microphone.running&&(!update_busy||update_idle));
        product_link.maintenance=comp_v11_update_product_busy();
        (void)comp_wba_recording_radio_set_value_capacity(product_link.segmented,comp_v11_ble_value_capacity());
        product_link.transfer.compact_payload_limit=comp_v11_ble_recording_capacity();
        (void)companion_gatt_stm32wb_drain(event,&product_link);
        maintenance_poll();
        input_notify();
        pointer_notify();
        bool measuring=sealed_transfer_work();
        if(measuring)start_download_observation();
        if(!measuring && download_timing_enabled) {
            uint32_t mask=__get_PRIMASK();__disable_irq();
            observe_gate_close(0u);
            comp_residence_end(&route_observation,comp_v11_ble_observe_us());
            download_timing_enabled=false;__set_PRIMASK(mask);
            comp_v11_cpu_transfer_end();
        }
        if(!measuring)observe_gate_close(0u);
        download_timing_enabled=measuring;
        comp_v11_product_download_timing(measuring);
        {
            comp_cpu_stage_span_t cpu_link=(product->board->microphone.running||comp_cpu_bulk_owned())?
                comp_cpu_detail_begin():(comp_cpu_stage_span_t){0};
            const bool consume_before=product_link.segmented&&product_link.segmented->consume_pending;
            comp_link_poll_with_budget(&product_link,HAL_GetTick(),diagnostic_clock,NULL,transfer_budget());
            if(consume_before&&product_link.segmented&&!product_link.segmented->consume_pending) {
                const comp_wba_recording_radio_t *r=product_link.segmented;
                comp_segment_result_t result=comp_wba_recording_pipeline_consume_result(r->config.pipeline);
                comp_diag_log_record_code(COMP_DIAG_EVT_GATT_SEGMENT_CONSUME_TERMINAL,
                    result==COMP_SEG_OK?COMP_DIAG_SEV_INFO:COMP_DIAG_SEV_WARN,
                    r->config.pipeline->consume.descriptor.recording_id,(uint32_t)result,
                    reclaim_trace_state(),(uint32_t)r->consume_replay);
            }
            comp_cpu_detail_end(COMP_CPU_STAGE_BLE_LINK,cpu_link,true);
        }
        schedule_sealed_transfer();
        comp_cpu_duty_span_t update_span=comp_cpu_duty_span_begin();
        comp_v11_update_product_poll();
        comp_cpu_duty_span_end(COMP_DUTY_UPDATE,update_span);
        comp_power_policy_set_blocker(&product->board->power,COMP_POWER_BLOCKER_RECORDING_TRANSFER,
            product_link.transfer.state==COMP_WBA_RECORDING_TRANSFER_ACTIVE ||
            product_link.transfer.state==COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED);
        comp_power_policy_set_blocker(&product->board->power,COMP_POWER_BLOCKER_STORAGE,
            (product_link.segmented&&product_link.segmented->consume_pending)||local_clear_pending||
            product->pet_profile.writing||product->board->nor.erase_active||
#if COMPANION_WBA_DUAL_PAIR_CAPTURE
            comp_v11_dual_pair_owned(product)||
#endif
            !comp_wba_recording_pipeline_page_available(&product->recording.pipeline));
        comp_power_policy_set_blocker(&product->board->power,COMP_POWER_BLOCKER_UPDATE,
            comp_v11_update_product_busy());
        comp_power_policy_set_blocker(&product->board->power,COMP_POWER_BLOCKER_BOND_NVM,
            comp_v11_ble_nvm_busy());
        const comp_cont_recording_t *recorder=&product->recording.capture.engine;
        uint8_t record_state=comp_wba_recording_product_state(&product->recording);
        uint8_t record_fault=product->recording.last_fault;
        if(last_record_state!=record_state) {
            uint8_t previous=last_record_state;
            last_record_state=record_state;
            comp_diag_log_record_code(COMP_DIAG_EVT_RECORDING_FSM_TRANSITION,COMP_DIAG_SEV_INFO,
                previous,record_state,record_fault,product->recording.pipeline.token);
            if(record_state==COMP_WBA_RECORDING_CAPTURING)
                comp_diag_log_record_code(COMP_DIAG_EVT_MICROPHONE_CAPTURE_START,COMP_DIAG_SEV_INFO,
                    product->recording.pipeline.token,recorder->active.descriptor.recording_id,
                    product->capture_started_ms,0u);
            if(record_state==COMP_WBA_RECORDING_TRANSFER_READY)
                comp_diag_log_record_code(COMP_DIAG_EVT_RECORDING_FSM_SESSION_FINISHED,COMP_DIAG_SEV_INFO,
                    recorder->active.descriptor.recording_id,recorder->stats.accepted_pcm_blocks*10u,
                    recorder->stats.durable_bytes,recorder->stats.encoded_packets);
            if(record_state==COMP_WBA_RECORDING_FAULT)
                comp_diag_log_record_code(COMP_DIAG_EVT_RECORDING_FSM_ERROR,COMP_DIAG_SEV_ERROR,
                    record_fault,product->recording.pipeline.token,product->capture_deadline_faults,
                    product->recording.media_ready?recorder->stats.budget_failures:0u);
            if(previous==COMP_WBA_RECORDING_FAULT && record_state!=COMP_WBA_RECORDING_FAULT &&
               !comp_wba_recording_product_salvaging(&product->recording))
                comp_diag_log_record_code(COMP_DIAG_EVT_RECORDING_FSM_RECOVERY,COMP_DIAG_SEV_INFO,
                    last_record_fault,record_state,product->recording.pipeline.token,0u);
        }
        /* Recovery owns the engine union until media_ready. Do not interpret
         * its cursors as capture statistics or emit wraparound drop counts. */
        if(!product->recording.media_ready||!product->recording.pipeline.engine_bound)
            last_dropped_pcm_frames=0u;
        else if(recorder->stats.overflows!=last_dropped_pcm_frames) {
            uint32_t delta=recorder->stats.overflows-last_dropped_pcm_frames;
            last_dropped_pcm_frames=recorder->stats.overflows;
            comp_diag_log_record_code(COMP_DIAG_EVT_MICROPHONE_CAPTURE_DROP,COMP_DIAG_SEV_WARN,
                delta,last_dropped_pcm_frames,product->capture_deadline_faults,
                product->max_capture_foreground_ms);
        }
        last_record_fault=record_fault;
    }
    menu_completions(HAL_GetTick());
}
#if COMPANION_WBA_CPU_DUTY_OBSERVER
void comp_v11_ble_poll(void)
{
    comp_cpu_duty_span_t span=comp_cpu_duty_span_begin();
    ble_poll_body();
    comp_cpu_duty_span_end(COMP_DUTY_BLE,span);
}
#endif
