#include "wba_ota_gatt.h"
#include "ble_link_budget.h"
#ifdef COMPANION_WBA_BLE_LINKED
#include "app_common.h"
#include "board_hal.h"
#include "ble_product.h"
#include "update_product.h"
#include <stdio.h>
#endif
#include "ble_core.h"
#include "svc_ctl.h"
#include "wba_update_manifest_wire.h"
#include <string.h>
#define QUEUE_DEPTH (COMP_V11_OTA_QUEUE_CHUNKS+1u)
static comp_v11_ota_gatt_ports_t ports;
static uint16_t service,handles[4];
static bool secured;
static uint8_t head,count;
/* One extra CCCD and status epoch need GATT storage. Reuse CE SRAM1 for
 * the existing identity receipt; no payload/window allocation is added. */
static uint8_t receipt[COMP_V11_OTA_IDENTITY_BYTES]
#if COMPANION_WBA_CE_SHARED_CAPTURE && defined(__GNUC__)
    __attribute__((section(".sram1.bss"),aligned(8)))
#endif
    ;
static uint8_t receipt_length;
static bool receipt_pending;
/* Exact bytes, not a lossy checksum: suppress repeated ACI status writes in
 * RECEIVING/COMPLETE/ERROR too. Keep this small snapshot in CE SRAM1 rather
 * than consuming its almost-full SRAM2. No second payload/window buffer. */
static struct {
    comp_v11_ota_gatt_timing_t timing;
    uint32_t generation,notified_prefix;
    uint8_t status[COMP_V11_OTA_STATUS_BYTES],length;
    bool valid,active,reported,overrun_pending,overrun_latched,notify_valid;
} observation
#if COMPANION_WBA_CE_SHARED_CAPTURE && defined(__GNUC__)
    __attribute__((section(".sram1.bss"),aligned(8)))
#endif
    ;
_Static_assert(sizeof(observation)<=112u+COMP_V11_LINK_BUDGET_BYTES,"bounded CE receipt/timing snapshot");
typedef struct {uint32_t queued_us;uint8_t kind;uint16_t length;} command_t;
_Static_assert(sizeof(command_t)==8u,"OTA command header layout");
#define COMMAND_MAX_STRIDE ((8u+COMP_V11_OTA_VALUE_BYTES+3u)&~3u)
#define QUEUE_BYTES (QUEUE_DEPTH*COMMAND_MAX_STRIDE)
/* Reuse the same8840-byte lease. Only an accepted BEGIN can choose a new
 * stride, after its old control slot and all fragments have retired. */
static uint16_t command_stride=COMMAND_MAX_STRIDE;
static uint8_t queue_depth=QUEUE_DEPTH;
static bool geometry_pending;
#if COMPANION_WBA_CE_SHARED_CAPTURE
#include "companion_opus16_rt.h"
_Static_assert(QUEUE_BYTES<=COMPANION_CE_ENCODER_STATE_BYTES+COMPANION_CE_DMA_BYTES,
               "OTA queue must fit the actual exclusively borrowed CE arena");
#endif
static bool assembling;
static bool processing;
static command_t *queue;
static command_t *queue_at(unsigned index)
{return (command_t*)((uint8_t*)queue+index*command_stride);}
static uint8_t *queue_bytes(unsigned index)
{return (uint8_t*)(queue_at(index)+1);}
static const uint8_t *command_bytes(const command_t *p)
{return (const uint8_t*)(p+1);}
static bool begin_queue_geometry(const uint8_t status[24])
{
    if(!geometry_pending)return true;
    if(queue||count||assembling||processing)return false;
    uint16_t payload=(uint16_t)((uint16_t)status[16]|((uint16_t)status[17]<<8u));
    if(status[5]!=DENZIC_OTA_V1_STATE_RECEIVING||status[6]||!payload||payload>COMP_V11_OTA_FILE_BYTES)
        return false;
    unsigned bytes=payload+4u;
    if(bytes<COMP_V11_OTA_CONTROL_BYTES)bytes=COMP_V11_OTA_CONTROL_BYTES;
    command_stride=(uint16_t)((8u+bytes+3u)&~3u);
    unsigned depth=QUEUE_BYTES/command_stride;
    if(depth>COMP_V11_OTA_MAX_QUEUE_CHUNKS+1u)depth=COMP_V11_OTA_MAX_QUEUE_CHUNKS+1u;
    queue_depth=(uint8_t)depth;geometry_pending=false;return true;
}
/* Separate SRAM2 observation, never grow the tight SRAM1 receipt or borrow
 * a payload slot. No extra ACI/NOR call, timestamp read, hot UART or retry. */
static comp_v11_ota_publish_diagnostics_t publish_diagnostics;
_Static_assert(sizeof(publish_diagnostics)==28u,"bounded notification outcome observation");
static void publish_diagnostics_reset(void)
{memset(&publish_diagnostics,0,sizeof(publish_diagnostics));publish_diagnostics.last_status=0xFFu;}
static void publish_counter(uint32_t *sum)
{if(*sum==UINT32_MAX)publish_diagnostics.flags|=1u;else ++*sum;}
const comp_v11_ota_publish_diagnostics_t *comp_v11_ota_gatt_publish_diagnostics(void)
{return &publish_diagnostics;}
static uint32_t partial_started;
static uint32_t connection_epoch;
enum {PHASE_EMPTY,PHASE_READY,PHASE_DATA,PHASE_STATUS,PHASE_OTHER};
/* SRAM2 retains448 bytes of static gap in the parent CE build. Keep this
 * separate from the almost-full SRAM1 receipt; ARM map must confirm the36B. */
static comp_v11_ota_phase_timing_t phase_timing;
static comp_v11_ota_wall_context_t wall_context;
_Static_assert(sizeof(wall_context)==96u,"bounded CE EMPTY/READY context ledger");
static uint32_t clock_us(void);

_Static_assert(sizeof(phase_timing)==36u,"bounded CE wall ledger");
static void phase_change(unsigned next,uint32_t stamp)
{
    if(!phase_timing.running)return;
    uint32_t elapsed=stamp-phase_timing.last_us;
    uint32_t *sum=phase_timing.phase==PHASE_EMPTY?&phase_timing.empty_us:
        (phase_timing.phase==PHASE_READY?&phase_timing.ready_us:
        (phase_timing.phase==PHASE_DATA?&phase_timing.data_us:
        (phase_timing.phase==PHASE_STATUS?&phase_timing.status_us:&phase_timing.other_us)));
    if(elapsed>UINT32_MAX-*sum){phase_timing.invalid=5u;phase_timing.running=0u;return;}
    *sum+=elapsed;
    if(phase_timing.phase==PHASE_EMPTY)wall_context.empty_us[wall_context.context]+=elapsed;
    else if(phase_timing.phase==PHASE_READY)wall_context.ready_us[wall_context.context]+=elapsed;
    phase_timing.last_us=stamp;phase_timing.phase=(uint8_t)next;
}
uint8_t comp_v11_ota_gatt_wall_context(uint8_t context)
{
    uint8_t previous=wall_context.context;
    if(context>=COMP_OTA_WALL_CONTEXT_COUNT) {
        if(phase_timing.running){phase_timing.invalid=6u;phase_timing.running=0u;}
        return previous;
    }
    if(context!=previous) {
        if(phase_timing.running)phase_change(phase_timing.phase,clock_us());
        wall_context.context=context;
    }
    return previous;
}
void comp_v11_ota_gatt_wall_note_ready_yield(void)
{
    if(phase_timing.running && phase_timing.phase==PHASE_READY && wall_context.ready_yields!=UINT32_MAX)
        ++wall_context.ready_yields;
}
const comp_v11_ota_wall_context_t *comp_v11_ota_gatt_wall_context_timing(void)
{return &wall_context;}
static void phase_stop(uint32_t stamp,uint8_t invalid)
{
    if(!phase_timing.running)return;
    phase_change(PHASE_OTHER,stamp);
    phase_timing.span_us=stamp-phase_timing.start_us;
    phase_timing.running=0u;
    if(invalid)phase_timing.invalid=invalid;
}
static void phase_available(uint32_t stamp)
{phase_change(count?PHASE_READY:PHASE_EMPTY,stamp);}
const comp_v11_ota_phase_timing_t *comp_v11_ota_gatt_phase_timing(void)
{return &phase_timing;}
static void release_if_empty(void)
{
    if(queue && !count && !assembling && !processing) {
        ports.workspace_release(ports.context,queue);queue=NULL;head=0u;
    }
}
static void discard_partial(void)
{assembling=false;partial_started=0u;release_if_empty();}
/* The hardware path uses the same microsecond clock as existing upload
 * observations. Native queue checks have only their provided ms clock. */
static uint32_t clock_us(void)
{
#ifdef COMPANION_WBA_BLE_LINKED
    return comp_v11_ble_observe_us();
#else
    return ports.now_ms(ports.context)*1000u;
#endif
}
static void add_time(uint32_t *sum,uint32_t value)
{if(value>UINT32_MAX-*sum)observation.timing.overflow=1u;else *sum+=value;}
const comp_v11_ota_gatt_timing_t *comp_v11_ota_gatt_timing(void)
{return &observation.timing;}
static void report_timing(void)
{
#ifdef COMPANION_WBA_BLE_LINKED
    char line[224];const comp_v11_ota_gatt_timing_t *t=&observation.timing;
    int n=snprintf(line,sizeof(line),"OTA2 rx=%lu processed=%lu queue_us=%lu queue_max_us=%lu data_us=%lu data_max_us=%lu peak=%lu overflow=%lu\r\n",
        (unsigned long)t->received,(unsigned long)t->processed,(unsigned long)t->queue_us,
        (unsigned long)t->queue_max_us,(unsigned long)t->data_us,(unsigned long)t->data_max_us,
        (unsigned long)t->peak_queue,(unsigned long)t->overflow);
    if(n>0&&(unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),"OTA3 status_calls=%lu status_us=%lu status_max_us=%lu status_skips=%lu\r\n",
        (unsigned long)t->status_calls,(unsigned long)t->status_us,
        (unsigned long)t->status_max_us,(unsigned long)t->status_skips);
    if(n>0&&(unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    const comp_v11_ota_publish_diagnostics_t *pub=&publish_diagnostics;
    n=snprintf(line,sizeof(line),"OTA13 scope=payload_notify generation=%lu calls=%lu not_accepted=%lu owner_invalid=%lu last_status=%lu max_us=%lu flags=%lu\r\n",
        (unsigned long)observation.generation,(unsigned long)pub->notify_calls,
        (unsigned long)pub->not_accepted,(unsigned long)pub->owner_invalidations,
        (unsigned long)pub->last_status,(unsigned long)pub->max_us,(unsigned long)pub->flags);
    if(n>0&&(unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    const comp_v11_update_diagnostics_t *io=comp_v11_update_product_diagnostics();
    n=snprintf(line,sizeof(line),"OTA14 scope=durable_credit_while_next_DATA_partial accepted=%lu\r\n",
        (unsigned long)pub->partial_data_notifies);
    if(n>0&&(unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),"OTA4 quantum_ms=1 scope=payload_pending program_n=%lu program_ms=%lu erase4_n=%lu erase4_ms=%lu erase64_n=%lu erase64_ms=%lu flags=%lu\r\n",
        (unsigned long)io->program_calls,(unsigned long)io->program_ms,
        (unsigned long)io->erase4_calls,(unsigned long)io->erase4_ms,
        (unsigned long)io->erase64_calls,(unsigned long)io->erase64_ms,(unsigned long)io->io_flags);
    if(n>0&&(unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    const comp_v11_update_program_diagnostics_t *program=comp_v11_update_program_diagnostics();
    n=snprintf(line,sizeof(line),"OTA11 scope=program_wall us=%lu spi_us=%lu progress_us=%lu spi_n=%lu progress_n=%lu flags=%lu\r\n",
        (unsigned long)program->program_us,(unsigned long)program->program_spi_us,
        (unsigned long)program->program_progress_us,(unsigned long)program->program_spi_calls,
        (unsigned long)program->program_progress_calls,(unsigned long)program->program_observe_flags);
    if(n>0&&(unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),"OTA12 scope=data_prepare prepare_us=%lu suspend_us=%lu\r\n",
        (unsigned long)program->data_prepare_us,(unsigned long)program->data_suspend_us);
    if(n>0&&(unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    const comp_v11_ota_phase_timing_t *p=&phase_timing;
    n=snprintf(line,sizeof(line),"OTA5 scope=first_complete_to_full_durable span_us=%lu empty_us=%lu ready_us=%lu data_us=%lu status_us=%lu other_us=%lu started=%u running=%u invalid=%u\r\n",
        (unsigned long)p->span_us,(unsigned long)p->empty_us,(unsigned long)p->ready_us,
        (unsigned long)p->data_us,(unsigned long)p->status_us,(unsigned long)p->other_us,
        (unsigned)p->started,(unsigned)p->running,(unsigned)p->invalid);
    if(n>0&&(unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    const comp_v11_ota_wall_context_t *w=&wall_context;
    n=snprintf(line,sizeof(line),"OTA6 schema=3 scope=ready_context outside_us=%lu update_other_us=%lu gatt_other_us=%lu seq_run_us=%lu ble_other_us=%lu product_other_us=%lu parent_us=%lu\r\n",
        (unsigned long)w->ready_us[0],(unsigned long)w->ready_us[1],(unsigned long)w->ready_us[2],
        (unsigned long)w->ready_us[3],(unsigned long)w->ready_us[4],(unsigned long)w->ready_us[5],(unsigned long)p->ready_us);
    if(n>0&&(unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),"OTA7 schema=3 scope=empty_context outside_us=%lu update_other_us=%lu gatt_other_us=%lu seq_run_us=%lu ble_other_us=%lu product_other_us=%lu parent_us=%lu\r\n",
        (unsigned long)w->empty_us[0],(unsigned long)w->empty_us[1],(unsigned long)w->empty_us[2],
        (unsigned long)w->empty_us[3],(unsigned long)w->empty_us[4],(unsigned long)w->empty_us[5],(unsigned long)p->empty_us);
    if(n>0&&(unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),"OTA8 scope=outer_ready_yield count=%lu\r\n",(unsigned long)w->ready_yields);
    if(n>0&&(unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),"OTA9 schema=3 scope=ready_product hal_us=%lu recorder_us=%lu runtime_us=%lu presenter_us=%lu render_us=%lu\r\n",
        (unsigned long)w->ready_us[6],(unsigned long)w->ready_us[7],(unsigned long)w->ready_us[8],(unsigned long)w->ready_us[9],(unsigned long)w->ready_us[10]);
    if(n>0&&(unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),"OTA10 schema=3 scope=empty_product hal_us=%lu recorder_us=%lu runtime_us=%lu presenter_us=%lu render_us=%lu\r\n",
        (unsigned long)w->empty_us[6],(unsigned long)w->empty_us[7],(unsigned long)w->empty_us[8],(unsigned long)w->empty_us[9],(unsigned long)w->empty_us[10]);
    if(n>0&&(unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
#endif
}
/* UUID bytes are little endian as required by the ST ACI API. DOV1 UUIDs
 * remain unchanged; the WBA sibling reports the running signed package identity. */
static const uint8_t uuids[5][16]={
 {0x06,0x3b,0x98,0x64,0xfa,0xad,0x29,0x95,0x7f,0x4c,0x9c,0xf0,0x97,0xf5,0x55,0x1b},
 {0x3c,0x53,0x88,0x37,0x46,0x66,0x80,0x81,0x92,0x43,0x4d,0xc6,0x29,0x5e,0x6c,0x20},
 {0x12,0x7e,0x9a,0x0a,0xe9,0xe5,0xe4,0xab,0xd1,0x4b,0x02,0x61,0xfb,0xb0,0xc4,0xfb},
 {0x89,0xb4,0x1d,0xfe,0xeb,0xcc,0xd6,0xb0,0x50,0x46,0x41,0x7c,0x4a,0x54,0x71,0xe5},
 {0x8a,0xb4,0x1d,0xfe,0xeb,0xcc,0xd6,0xb0,0x50,0x46,0x41,0x7c,0x4a,0x54,0x71,0xe5}
};
static bool initialized(uint8_t status, unsigned stage)
{
    if(status==BLE_STATUS_SUCCESS)return true;
#ifdef COMPANION_WBA_BLE_LINKED
    /* One cold failure identifies the actual ACI call; no status polling or
     * UART work is added to the transfer/capture path. Stage 0 is the service,
     * 1..4 are control/data/status/signed-manifest characteristics. */
    char line[64];
    (void)snprintf(line,sizeof(line),"OTA1 INIT_FAIL stage=%u status=%02x\r\n",stage,(unsigned)status);
    (void)comp_v11_hal_debug_write(line);
#else
    (void)stage;
#endif
    return false;
}
static void rx_fragment_shape(uint8_t stage,uint8_t why,const hci_event_pckt *e,
    const aci_gatt_attribute_modified_event_rp0 *a)
{
#ifdef COMPANION_WBA_BLE_LINKED
    if(a->Attr_Data_Length>244u || a->Offset)
        comp_v11_ble_rx_shape_trace(stage,why,4u,e->evt,(uint16_t)e->plen+3u,0u,
            e->plen,a->Attr_Handle,a->Offset,a->Attr_Data_Length);
#else
    (void)stage;(void)why;(void)e;(void)a;
#endif
}
static SVCCTL_EvtAckStatus_t event(void *packet)
{
    if(!packet)return SVCCTL_EvtNotAck;
    hci_event_pckt *e=(void*)((hci_uart_pckt*)packet)->data;
    if(e->evt!=HCI_VENDOR_SPECIFIC_DEBUG_EVT_CODE || e->plen<2u)return SVCCTL_EvtNotAck;
    evt_blecore_aci *v=(void*)e->data;
    if(v->ecode!=ACI_GATT_ATTRIBUTE_MODIFIED_VSEVT_CODE ||
       e->plen<2u+offsetof(aci_gatt_attribute_modified_event_rp0,Attr_Data))return SVCCTL_EvtNotAck;
    aci_gatt_attribute_modified_event_rp0 *a=(void*)v->data;
    /* The stack owns CCCD state. Republish an unchanged receipt after a
     * descriptor change so a newly subscribed owner receives its own snapshot. */
    if(a->Attr_Handle==handles[2]+2u) {
        observation.valid=false;observation.notify_valid=false;return SVCCTL_EvtAckFlowEnable;
    }
    unsigned kind;
    for(kind=0;kind<4u;++kind)if(a->Attr_Handle==handles[kind]+1u)break;
    if(kind==4u)return SVCCTL_EvtNotAck;
    rx_fragment_shape(35u,(uint8_t)(kind|(secured?0x80u:0u)),e,a);
    if(!secured || kind>=2u)return SVCCTL_EvtAckFlowEnable;
    if(kind==1u && (observation.overrun_pending || observation.overrun_latched))
        return SVCCTL_EvtAckFlowEnable;
    const uint16_t offset=(uint16_t)(a->Offset&0x7FFFu);
    const bool more=(a->Offset&0x8000u)!=0u;
    const uint16_t length=a->Attr_Data_Length;
    const uint16_t data_capacity=(uint16_t)(command_stride-sizeof(command_t));
    const uint16_t limit=kind==1u?(data_capacity<COMP_V11_OTA_VALUE_BYTES?data_capacity:COMP_V11_OTA_VALUE_BYTES):COMP_V11_OTA_CONTROL_BYTES;
    if(!length || length>245u || length>e->plen-2u-
       offsetof(aci_gatt_attribute_modified_event_rp0,Attr_Data) ||
       offset>limit || length>limit-offset || ((offset||more)&&kind!=1u&&kind!=3u)) {
        uint8_t why=(uint8_t)((!length?1u:0u)|(length>245u?2u:0u)|
            (length>e->plen-2u-offsetof(aci_gatt_attribute_modified_event_rp0,Attr_Data)?4u:0u)|
            (offset>limit?8u:0u)|(length>limit-offset?16u:0u)|
            (((offset||more)&&kind!=1u&&kind!=3u)?32u:0u));
        rx_fragment_shape(36u,why,e,a);
        discard_partial();return SVCCTL_EvtAckFlowEnable;
    }
    /* WBA HCI emits long attribute writes as ordered fragments. Offset bit15
     * is MORE, never a stored-file offset. Only the final complete value is
     * offered to DOV1; a gap, restart, disconnect or timeout retires partials. */
    if(!offset) {
        discard_partial();
        /* A compliant credit sender cannot exceed this ring. A peer that
         * does exceed it aborts ONLY this OTA, outside the HCI callback.
         * Global event delivery and disconnect processing remain runnable. */
        if(count>=(kind==1u?queue_depth-1u:queue_depth)) {
            observation.overrun_pending=true;return SVCCTL_EvtAckFlowEnable;
        }
        if(!queue)queue=ports.workspace_claim(ports.context,QUEUE_BYTES);
        if(!queue)return SVCCTL_EvtAckFlowEnable;
        unsigned tail=(head+count)%queue_depth;
        (*queue_at(tail)).kind=(uint8_t)kind;(*queue_at(tail)).length=0u;
        assembling=true;partial_started=ports.now_ms(ports.context);
    }
    if(!assembling || !queue)return SVCCTL_EvtAckFlowEnable;
    unsigned tail=(head+count)%queue_depth;
    if((*queue_at(tail)).kind!=kind || (*queue_at(tail)).length!=offset) {
        rx_fragment_shape(37u,1u,e,a);
        discard_partial();return SVCCTL_EvtAckFlowEnable;
    }
    memcpy(queue_bytes(tail)+offset,a->Attr_Data,length);
    (*queue_at(tail)).length=(uint16_t)(offset+length);
    if(!more) {
        rx_fragment_shape(38u,0u,e,a);
        (*queue_at(tail)).queued_us=clock_us();assembling=false;partial_started=0u;++count;
        if(observation.active&&kind==1u) {
            add_time(&observation.timing.received,1u);
            if(count>observation.timing.peak_queue)observation.timing.peak_queue=count;
            if(!phase_timing.started) {
                phase_timing.start_us=(*queue_at(tail)).queued_us;
                phase_timing.last_us=(*queue_at(tail)).queued_us;
                phase_timing.phase=PHASE_READY;phase_timing.started=1u;phase_timing.running=1u;
            } else if(!processing&&phase_timing.phase!=PHASE_STATUS)
                phase_available((*queue_at(tail)).queued_us);
        }
    }
    /* Admission into RAM is not a durable receipt. The status below is
     * published only after ordered physical writes drain. */
    return SVCCTL_EvtAckFlowEnable;
}
bool comp_v11_ota_gatt_init(const comp_v11_ota_gatt_ports_t *p)
{
    if(!p || !p->control || !p->data || !p->status ||
       !p->workspace_claim || !p->workspace_release || !p->now_ms)return false;
    ports=*p;queue=NULL;assembling=false;processing=false;partial_started=0u;head=0;count=0;secured=false;receipt_pending=false;
    memset(&observation,0,sizeof(observation));
    publish_diagnostics_reset();
    memset(&phase_timing,0,sizeof(phase_timing));
    connection_epoch=0u;command_stride=COMMAND_MAX_STRIDE;queue_depth=QUEUE_DEPTH;geometry_pending=false;
    if(!initialized(aci_gatt_add_service(UUID_TYPE_128,(const Service_UUID_t*)uuids[0],PRIMARY_SERVICE,10,&service),0u))return false;
    for(unsigned i=0;i<4u;++i) {
        uint8_t properties=i==2u?(CHAR_PROP_READ|CHAR_PROP_NOTIFY):(i==3u?CHAR_PROP_READ:CHAR_PROP_WRITE);
        if(i==1u)properties|=CHAR_PROP_WRITE_WITHOUT_RESP;
        uint8_t permissions=(i>=2u?ATTR_PERMISSION_ENCRY_READ:ATTR_PERMISSION_ENCRY_WRITE);
        
        /* Only DATA can be pipelined. Manifest/control keep ATT responses;
         * WOC4 binds durable notifications to this BEGIN generation. */
        uint16_t size=i==0u?COMP_V11_OTA_CONTROL_BYTES:(i==1u?COMP_V11_OTA_VALUE_BYTES:(i==2u?COMP_V11_OTA_STATUS_BYTES:COMP_V11_OTA_IDENTITY_BYTES));
        if(!initialized(aci_gatt_add_char(service,UUID_TYPE_128,(const Char_UUID_t*)uuids[i+1u],size,
             properties,permissions,i>=2u?GATT_DONT_NOTIFY_EVENTS:GATT_NOTIFY_ATTRIBUTE_WRITE,
             16,1,&handles[i]),i+1u))return false;
    }
    SVCCTL_RegisterSvcHandler(event);return true;
}
void comp_v11_ota_gatt_connection(bool encrypted)
{
    ++connection_epoch;
    if(!encrypted)phase_stop(clock_us(),2u);
    secured=encrypted;
    if(ports.connection)ports.connection(ports.context,encrypted);
    observation.valid=false;observation.notify_valid=false;
    if(!encrypted) {
        geometry_pending=false;
        /* Pending commands belong to the old connection. A storage callback
         * already in progress still owns its bytes, even if it dispatched
         * disconnect/re-encryption while servicing the controller. */
        count=processing?1u:0u;
        discard_partial();
        if(!processing)head=0;
        receipt_pending=receipt_length!=0u;
    }
}
bool comp_v11_ota_gatt_foreground_pending(void)
{
    return service && !processing &&
        (observation.overrun_pending || (secured && count));
}
size_t comp_v11_ota_gatt_copy_following_data(uint32_t expected_offset,
    uint32_t expected_size,uint16_t maximum_payload,uint8_t *out,size_t capacity)
{
    if(!processing||!secured||!queue||count<2u||!out||!capacity||
       observation.overrun_pending||observation.overrun_latched)return 0u;
    const command_t *current=&(*queue_at(head)),*next=&(*queue_at((head+1u)%queue_depth));
    if(current->kind!=1u||current->length<=4u)return 0u;
    uint32_t begin=(uint32_t)command_bytes(current)[0]|((uint32_t)command_bytes(current)[1]<<8u)|
        ((uint32_t)command_bytes(current)[2]<<16u)|((uint32_t)command_bytes(current)[3]<<24u);
    size_t current_bytes=current->length-4u;
    if(begin>expected_size||current_bytes>expected_size-begin||
       current_bytes>maximum_payload||begin+current_bytes!=expected_offset)return 0u;
    if(next->kind!=1u||next->length<=4u)return 0u;
    uint32_t offset=(uint32_t)command_bytes(next)[0]|((uint32_t)command_bytes(next)[1]<<8u)|
        ((uint32_t)command_bytes(next)[2]<<16u)|((uint32_t)command_bytes(next)[3]<<24u);
    size_t n=next->length-4u;
    if(offset!=expected_offset||offset>expected_size||n>expected_size-offset||n>maximum_payload)return 0u;
    if(n>capacity)n=capacity;
    memcpy(out,command_bytes(next)+4u,n);return n;
}

static void ota_gatt_poll_owned(void)
{
    uint8_t status[COMP_V11_OTA_STATUS_BYTES];
    if(!service || processing)return;
    /* Link loss ends RECEIVING without a COMPLETE/ERROR status publication.
     * Retire its existing ledger once here, before a queued successor BEGIN
     * clears it. Never format UART in the HCI/security callback or while a
     * storage callback still owns an active command. invalid=2 means this is
     * a failed/incomplete payload, not a successful durable boundary. */
    if(observation.active && !observation.reported && phase_timing.started &&
       !phase_timing.running && phase_timing.invalid==2u) {
        observation.reported=true;report_timing();
    }
    if(observation.overrun_pending) {
        phase_stop(clock_us(),3u);
        /* No NOR or abort callback can run in HCI delivery. Keep the lease
         * while abort unwinds; nested DATA sees the latched fault and cannot
         * enqueue into, release or re-use an active storage pointer. */
        observation.overrun_pending=false;observation.overrun_latched=true;
        observation.valid=false;count=0u;assembling=false;partial_started=0u;head=0u;
        const uint8_t abort_command[20]={'D','O','V','1',DENZIC_OTA_V1_OP_ABORT,1u};
        processing=true;(void)ports.control(ports.context,abort_command,sizeof(abort_command));processing=false;
        release_if_empty();
    }
    if(assembling && (uint32_t)(ports.now_ms(ports.context)-partial_started)>=1000u)discard_partial();
    if(secured && count && !processing) {
        unsigned slot=head;processing=true;
        observation.valid=false;
        bool accepted=false;
        bool data_command=(*queue_at(slot)).kind==1u;
        if((*queue_at(slot)).kind==0u&&(*queue_at(slot)).length>=20u&&
           !memcmp(queue_bytes(slot),"DOV1",4u)&&queue_bytes(slot)[4]==DENZIC_OTA_V1_OP_BEGIN) {
            memset(&observation.timing,0,sizeof(observation.timing));
            publish_diagnostics_reset();
            memset(&phase_timing,0,sizeof(phase_timing));
            memset(wall_context.empty_us,0,sizeof(wall_context.empty_us));
            memset(wall_context.ready_us,0,sizeof(wall_context.ready_us));
            wall_context.ready_yields=0u;
            /* Keep the current nested execution context across BEGIN. */
            observation.active=true;observation.reported=false;
        }
        uint32_t start=data_command&&observation.active?clock_us():0u;
        if(phase_timing.running) {
            if(data_command)phase_change(PHASE_DATA,start);
            else {
                phase_change(PHASE_OTHER,clock_us());
                if((*queue_at(slot)).kind==0u&&(*queue_at(slot)).length>=20u&&
                   !memcmp(queue_bytes(slot),"DOV1",4u)&&queue_bytes(slot)[4]==DENZIC_OTA_V1_OP_ABORT)
                    phase_stop(clock_us(),4u);
            }
        }
        if(data_command&&observation.active) {
            uint32_t elapsed=start-(*queue_at(slot)).queued_us;
            add_time(&observation.timing.queue_us,elapsed);
            if(elapsed>observation.timing.queue_max_us)observation.timing.queue_max_us=elapsed;
        }
        if(queue_at(slot)->kind==0u)accepted=ports.control(ports.context,queue_bytes(slot),queue_at(slot)->length);
        else if(queue_at(slot)->kind==1u)accepted=ports.data(ports.context,queue_bytes(slot),queue_at(slot)->length);
        if(data_command&&observation.active) {
            uint32_t elapsed=clock_us()-start;
            add_time(&observation.timing.processed,1u);add_time(&observation.timing.data_us,elapsed);
            if(elapsed>observation.timing.data_max_us)observation.timing.data_max_us=elapsed;
        }
        if(accepted && (*queue_at(slot)).kind==0u && (*queue_at(slot)).length>=20u &&
           !memcmp(queue_bytes(slot),"DOV1",4u)) {
            if(queue_bytes(slot)[4]==DENZIC_OTA_V1_OP_BEGIN) {
                if(++observation.generation==0u)++observation.generation;
                observation.overrun_latched=false;observation.notify_valid=false;geometry_pending=true;
            } else if(queue_bytes(slot)[4]==DENZIC_OTA_V1_OP_ABORT)
                observation.overrun_latched=false;
        }
        processing=false;
        head=(uint8_t)((head+1u)%queue_depth);--count;
        release_if_empty();
        if(phase_timing.running)phase_available(clock_us());
    }
    if(receipt_pending && aci_gatt_update_char_value(service,handles[3],0,receipt_length,receipt)==BLE_STATUS_SUCCESS)
        receipt_pending=false;
    /* Publish durable DATA credits while more DATA is pending: requiring the
     * entire physical ring to empty starves a correctly credit-bound sender.
     * An ordered control/manifest remains a fence, including a SYNC after the
     * final DATA. A partial NEXT DATA owns its separate tail slot but cannot
     * invalidate an earlier durable prefix. Do not hold those credits until
     * its final HCI fragment arrives. Active storage, BEGIN geometry and an
     * ordered control still fence publication; partial bytes are never used
     * to derive the prefix or free a slot. */
    if(processing || observation.overrun_pending)return;
    if(assembling && (geometry_pending || !queue ||
        queue_at((head+count)%queue_depth)->kind!=1u))return;
    for(unsigned i=0u;i<count;++i)
        if((*queue_at((head+i)%queue_depth)).kind!=1u)return;
    size_t size=ports.status(ports.context,status,sizeof(status));
    if(size==24u) {
        if(geometry_pending && !begin_queue_geometry(status)) {
            /* No geometry is changed while an old slot is owned. A peer
             * sending DATA before the BEGIN receipt fails this OTA only. */
            geometry_pending=false;observation.overrun_pending=true;return;
        }
        if(observation.overrun_latched) {
            status[5]=DENZIC_OTA_V1_STATE_ERROR;status[6]=DENZIC_OTA_V1_ERROR_STORAGE_WRITE;
        }
        memcpy(status+24u,"WOC5",4u);
        status[28]=(uint8_t)(COMP_V11_OTA_FILE_BYTES&0xFFu);status[29]=(uint8_t)(COMP_V11_OTA_FILE_BYTES>>8);
        status[30]=(uint8_t)(COMP_V11_OTA_VALUE_BYTES&0xFFu);status[31]=(uint8_t)(COMP_V11_OTA_VALUE_BYTES>>8);
        status[32]=(uint8_t)COMP_V11_OTA_WINDOW_CHUNKS;status[33]=0u;
        status[34]=53u;status[35]=0u; /* 21 + bit32: guaranteed64-chunk window-end durable notify */
        status[36]=(uint8_t)(queue_depth-1u);status[37]=0u;
        status[38]=0u;status[39]=0u; /* reserved, must be zero */
        for(unsigned i=0;i<4u;++i)status[40u+i]=(uint8_t)(observation.generation>>(8u*i));
#ifdef COMPANION_WBA_BLE_LINKED
        comp_v11_ble_link_budget(status+44u);
#else
        /* Native contract checks have no controller: explicitly unknown. */
        comp_v11_ble_link_budget_encode(status+44u,NULL);
#endif
        size=COMP_V11_OTA_STATUS_BYTES;
    }
    if(size && size<=sizeof(status)) {
        if(observation.valid&&observation.length==size&&!memcmp(observation.status,status,size)) {
            if(observation.active)add_time(&observation.timing.status_skips,1u);
            return;
        }
        const uint32_t prefix=(uint32_t)status[8]|((uint32_t)status[9]<<8u)|
            ((uint32_t)status[10]<<16u)|((uint32_t)status[11]<<24u);
        const uint32_t expected=(uint32_t)status[12]|((uint32_t)status[13]<<8u)|
            ((uint32_t)status[14]<<16u)|((uint32_t)status[15]<<24u);
        const uint32_t payload=(uint32_t)status[16]|((uint32_t)status[17]<<8u);
        const uint32_t written=(uint32_t)status[20]|((uint32_t)status[21]<<8u)|
            ((uint32_t)status[22]<<16u)|((uint32_t)status[23]<<24u);
        if(phase_timing.running) {
            if(status[5]==DENZIC_OTA_V1_STATE_ERROR)phase_stop(clock_us(),1u);
            else if(expected&&prefix==expected&&written&&
                    (status[5]==DENZIC_OTA_V1_STATE_RECEIVING||status[5]==DENZIC_OTA_V1_STATE_COMPLETE))
                phase_stop(clock_us(),0u);
        }
        /* A transient busy result may shift the bounded credit cadence.
         * This explicit contract guarantees the durable64-chunk boundary
         * anyway; a failed ACI publication remains invalid and retries even
         * when no further DATA arrives. No credit precedes the NOR write. */
        const bool window_end=prefix && status[5]==DENZIC_OTA_V1_STATE_RECEIVING &&
            written && (written%COMP_V11_OTA_WINDOW_CHUNKS)==0u;
        /* A small physical arena must return its already durable credit
         * before half the sender window is retired. Keep the established
         *8-packet maximum for larger packed arenas; no extra payload slot or
         * early storage acknowledgement. Firmware/host still share WOC5/64. */
        uint32_t credit_quantum=((uint32_t)queue_depth-1u)/4u;
        if(credit_quantum==0u)credit_quantum=1u;
        if(credit_quantum>8u)credit_quantum=8u;
        const bool notify=secured && (!observation.notify_valid ||
            status[5]!=DENZIC_OTA_V1_STATE_RECEIVING || prefix==expected || window_end ||
            (prefix>=observation.notified_prefix && prefix-observation.notified_prefix>=credit_quantum*payload));
        /* Keep bounded radio batching. A busy DATA ring publishes only
         * a real credit notification, not an ACI command for every write.
         * Do not cache an unpublished prefix: the empty-ring READ must still
         * receive its exact current durable value. */
        if(count && !notify)return;
        /* Arm before ACI: a nested disconnect/re-encryption must invalidate
         * this receipt even if the outer command then reports success. */
        memcpy(observation.status,status,size);observation.length=(uint8_t)size;observation.valid=true;
        uint32_t start=observation.active?clock_us():0u;
        phase_change(PHASE_STATUS,start);
        /* Local READ always sees the newest durable prefix. The official EXT
         * call suppresses radio notifications for sub-quantum progress rather
         * than making the readable value stale or sending one per packet. */
        const uint32_t publish_epoch=connection_epoch,publish_generation=observation.generation;
        const bool observe_notify=notify && status[5]==DENZIC_OTA_V1_STATE_RECEIVING && prefix && expected;
        const bool partial_data_notify=observe_notify && assembling;
        bool observation_owner_entered=false;
        uint8_t result=aci_gatt_update_char_value_ext(0x0FFFu,service,handles[2],notify?1u:0u,
                (uint16_t)size,0u,(uint8_t)size,status);
        /* A nested security/CCCD/BEGIN callback invalidates this publication.
         * Its success belongs to the old owner, never the new subscriber's
         * durable-credit baseline. Leave the invalidation for the next poll. */
        if(publish_epoch==connection_epoch && publish_generation==observation.generation && observation.valid) {
            observation_owner_entered=true;
            if(result!=BLE_STATUS_SUCCESS)observation.valid=false;
            else if(notify) {observation.notified_prefix=prefix;observation.notify_valid=true;}
        }
        if(observation.active) {
            uint32_t end=clock_us();
            uint32_t elapsed=end-start;
            /* A nested BEGIN resets this observation too. Do not attribute an
             * old command to its successor; security/CCCD invalidation within
             * the same BEGIN is reported separately from ACI rejection. */
            if(observe_notify && publish_generation==observation.generation) {
                publish_counter(&publish_diagnostics.notify_calls);
                if(result!=BLE_STATUS_SUCCESS)publish_counter(&publish_diagnostics.not_accepted);
                if(!observation_owner_entered)publish_counter(&publish_diagnostics.owner_invalidations);
                if(partial_data_notify && result==BLE_STATUS_SUCCESS && observation_owner_entered)
                    publish_counter(&publish_diagnostics.partial_data_notifies);
                publish_diagnostics.last_status=result;
                if(elapsed>publish_diagnostics.max_us)publish_diagnostics.max_us=elapsed;
            }
            phase_available(end);
            add_time(&observation.timing.status_calls,1u);add_time(&observation.timing.status_us,elapsed);
            if(elapsed>observation.timing.status_max_us)observation.timing.status_max_us=elapsed;
            /* Emit only after payload service has ended, never per packet. */
            if(!observation.reported&&size>=6u&&
               (status[5]==DENZIC_OTA_V1_STATE_COMPLETE||status[5]==DENZIC_OTA_V1_STATE_ERROR)) {
                observation.reported=true;report_timing();
            }
        }
    }
}
void comp_v11_ota_gatt_poll(void)
{
    if(!service||processing)return;
    uint8_t previous=comp_v11_ota_gatt_wall_context(COMP_OTA_WALL_GATT_OTHER);
    ota_gatt_poll_owned();
    (void)comp_v11_ota_gatt_wall_context(previous);
}
void comp_v11_ota_gatt_poll_slice(void)
{
    if(!service||processing)return;
    const uint32_t started=ports.now_ms(ports.context),epoch=connection_epoch;
    const bool first_data=secured&&queue&&count&&(*queue_at(head)).kind==1u;
    comp_v11_ota_gatt_poll();
    /* READY2.155s in the actual528 ledger includes a whole product turn
     * between each DATA. Amortize only one such turn; an erase/slow command
     * returns immediately instead of adding more foreground latency.
     * A nested disconnect/re-encryption cannot borrow the old owner's slot. */
    if(first_data&&epoch==connection_epoch&&secured&&!processing&&queue&&count&&
       (*queue_at(head)).kind==1u&&!observation.overrun_pending&&!observation.overrun_latched&&
       observation.active&&observation.length>=24u&&
       observation.status[5]==DENZIC_OTA_V1_STATE_RECEIVING&&
       (uint32_t)(ports.now_ms(ports.context)-started)<4u)
        comp_v11_ota_gatt_poll();
}
void comp_v11_ota_gatt_identity(const uint8_t proof[COMP_V11_OTA_IDENTITY_BYTES])
{
    if(proof&&(receipt_length!=COMP_V11_OTA_IDENTITY_BYTES||memcmp(receipt,proof,COMP_V11_OTA_IDENTITY_BYTES))) {
        memcpy(receipt,proof,COMP_V11_OTA_IDENTITY_BYTES);receipt_length=COMP_V11_OTA_IDENTITY_BYTES;receipt_pending=true;
    }
}
