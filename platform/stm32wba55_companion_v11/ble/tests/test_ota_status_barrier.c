/* Actual GATT queue + DOV1 engine: an exact status remains a storage barrier
 * without a redundant SYNC. Radio/Flash hardware and speed are not tested. */
#include "wba_ota_gatt.h"
#include "denzic_ota_v1.h"
#include "ble_core.h"
#include "svc_ctl.h"
#include <stdio.h>
#include <string.h>
#if COMPANION_WBA_CE_SHARED_CAPTURE
#include "companion_opus16_rt.h"
#endif
#define CHECK(x) do {if(!(x)){printf("FAIL %d: %s\n",__LINE__,#x);return 1;}}while(0)
static SVCCTL_EvtAckStatus_t (*callback)(void *);
static denzic_ota_v1_context_t transfer;
static uint16_t handles[4];
static unsigned added,storage_writes,fail_write,finish_calls,control_calls;
static unsigned status_writes,status_attempts,status_busy,nested_status;
static uint32_t now=100u;
static uint8_t status_extra[24];
static uint8_t published[COMP_V11_OTA_STATUS_BYTES],stored[7680];
#if COMPANION_WBA_CE_SHARED_CAPTURE
static void *arena_pointer;
#else
static union {uint64_t alignment;uint8_t bytes[24576];} arena;
#endif
static bool borrowed,early_receipt;
void SVCCTL_ResumeUserEventFlow(void) {}
void SVCCTL_RegisterSvcHandler(SVCCTL_EvtAckStatus_t (*f)(void *)){callback=f;}
uint8_t aci_gatt_add_service(uint8_t t,const Service_UUID_t *u,uint8_t p,uint8_t n,uint16_t *h)
{(void)t;(void)u;(void)p;(void)n;*h=1;return 0;}
uint8_t aci_gatt_add_char(uint16_t s,uint8_t t,const Char_UUID_t *u,uint16_t n,uint8_t p,uint8_t a,uint8_t e,uint8_t k,uint8_t v,uint16_t *h)
{(void)s;(void)t;(void)u;(void)n;(void)p;(void)a;(void)e;(void)k;(void)v;
 if(added>=4u)return 1;*h=(uint16_t)(10u+2u*added);handles[added++]=*h;return 0;}
uint8_t aci_gatt_update_char_value(uint16_t s,uint16_t h,uint8_t off,uint8_t n,const uint8_t *b)
{
 (void)s;(void)off;
 if(h==handles[2]&&n==sizeof(published)) {
    ++status_attempts;now+=2u;if(status_busy){--status_busy;return 1;}
    if(nested_status){nested_status=0;comp_v11_ota_gatt_connection(false);comp_v11_ota_gatt_connection(true);}
    ++status_writes;memcpy(published,b,n);
 }
 return 0;
}
uint8_t aci_gatt_update_char_value_ext(uint16_t c,uint16_t s,uint16_t h,uint8_t u,uint16_t size,uint16_t off,uint8_t n,const uint8_t *b)
{(void)c;(void)u;(void)size;return aci_gatt_update_char_value(s,h,(uint8_t)off,n,b);}
static uint32_t get32(const uint8_t *b)
{return (uint32_t)b[0]|((uint32_t)b[1]<<8)|((uint32_t)b[2]<<16)|((uint32_t)b[3]<<24);}
static void put32(uint8_t *b,uint32_t value)
{for(unsigned i=0;i<4u;++i)b[i]=(uint8_t)(value>>(8u*i));}
static bool begin(void *c,uint32_t size)
{(void)c;storage_writes=0;return size==sizeof(stored);}
static bool write(void *c,const uint8_t *b,size_t n)
{
    (void)c;++storage_writes;
    if(get32(published+8)>transfer.bytes_written)early_receipt=true;
    /* Nested foreground progress cannot publish an in-flight write. */
    comp_v11_ota_gatt_poll();
    if(get32(published+8)>transfer.bytes_written)early_receipt=true;
    if(fail_write==storage_writes)return false;
    if(transfer.bytes_written+n>sizeof(stored))return false;
    memcpy(stored+transfer.bytes_written,b,n);return true;
}
static bool finish(void *c){(void)c;++finish_calls;return true;}
static void abort_write(void *c){(void)c;}
static bool control(void *c,const uint8_t *b,size_t n)
{(void)c;++control_calls;return denzic_ota_v1_handle_control(&transfer,b,n);}
static bool data(void *c,const uint8_t *b,size_t n)
{(void)c;bool ok=denzic_ota_v1_handle_data(&transfer,b,n);now+=3u;return ok;}
static size_t status(void *c,uint8_t *b,size_t n)
{(void)c;size_t size=denzic_ota_v1_encode_status(&transfer,b,n);if(size){b[7]|=0x80u;for(unsigned i=0;i<24u;++i)b[i]^=status_extra[i];}return size;}
static void *claim(void *c,size_t n)
{
 (void)c;if(borrowed)return NULL;
#if COMPANION_WBA_CE_SHARED_CAPTURE
 arena_pointer=companion_opus16_rt_workspace_borrow(n);if(!arena_pointer)return NULL;
 borrowed=true;return arena_pointer;
#else
 if(n>sizeof(arena.bytes))return NULL;borrowed=true;return arena.bytes;
#endif
}
static void release(void *c,void *p)
{
 (void)c;
#if COMPANION_WBA_CE_SHARED_CAPTURE
 if(p==arena_pointer){companion_opus16_rt_workspace_release(p);borrowed=false;arena_pointer=NULL;}
#else
 if(p==arena.bytes)borrowed=false;
#endif
}
static uint32_t clock_ms(void *c){(void)c;return now;}
static void packet(unsigned kind,const uint8_t *bytes,uint16_t length)
{
    hci_uart_pckt p={0};hci_event_pckt *e=(void*)p.data;evt_blecore_aci *v=(void*)e->data;
    aci_gatt_attribute_modified_event_rp0 *a=(void*)v->data;
    e->evt=HCI_VENDOR_SPECIFIC_DEBUG_EVT_CODE;e->plen=(uint8_t)(10u+length);
    v->ecode=ACI_GATT_ATTRIBUTE_MODIFIED_VSEVT_CODE;a->Attr_Handle=(uint16_t)(handles[kind]+1u);
    a->Attr_Data_Length=length;a->Offset=0;memcpy(a->Attr_Data,bytes,length);(void)callback(&p);
}
static void begin_packet(void)
{
    uint8_t b[20]={'D','O','V','1',DENZIC_OTA_V1_OP_BEGIN,1};
    put32(b+8,sizeof(stored));b[12]=240;b[14]=16;
    packet(0,b,sizeof(b));comp_v11_ota_gatt_poll();
}
static void window(unsigned first)
{
    for(unsigned i=0;i<16u;++i){uint8_t b[244];memset(b,(int)(first+i),sizeof(b));
        put32(b,(first+i)*240u);packet(1,b,sizeof(b));}
}
int main(void)
{
#if COMPANION_WBA_CE_SHARED_CAPTURE
    const size_t capacity=COMPANION_CE_ENCODER_STATE_BYTES+COMPANION_CE_DMA_BYTES;
    CHECK(!companion_opus16_rt_workspace_borrow(0u));
    CHECK(!companion_opus16_rt_workspace_borrow(capacity+1u));
    uint8_t *whole=companion_opus16_rt_workspace_borrow(capacity);CHECK(whole);
    whole[capacity-1u]=0x5au;
    CHECK(!companion_opus16_rt_dma_claim(&whole));
    companion_opus16_rt_workspace_release(whole);
    CHECK(companion_opus16_rt_dma_claim(&whole));
    CHECK(!companion_opus16_rt_workspace_borrow(8840u));
    companion_opus16_rt_dma_release(&whole);
#endif
    denzic_ota_v1_storage_driver_t storage={begin,write,finish,abort_write};
    denzic_ota_v1_init(&transfer,storage,NULL,505,16);
    comp_v11_ota_gatt_ports_t p={control,data,status,NULL,claim,release,clock_ms,NULL};
    CHECK(comp_v11_ota_gatt_init(&p));comp_v11_ota_gatt_connection(true);begin_packet();
    CHECK(transfer.state==DENZIC_OTA_V1_STATE_RECEIVING&&control_calls==1u);
    unsigned before=status_writes;
    for(unsigned i=0;i<1000u;++i)comp_v11_ota_gatt_poll();
    CHECK(status_writes==before&&comp_v11_ota_gatt_timing()->status_skips==1000u);
    /* Receiving is the old gap: exact changes in every field must publish,
     * identical loops must not issue more ACI commands. */
    for(unsigned byte=0;byte<24u;++byte) {
        status_extra[byte]=1u;comp_v11_ota_gatt_poll();CHECK(status_writes==before+1u);
        comp_v11_ota_gatt_poll();CHECK(status_writes==before+1u);
        status_extra[byte]=0u;comp_v11_ota_gatt_poll();CHECK(status_writes==before+2u);before=status_writes;
    }
    comp_v11_ota_gatt_connection(true);status_busy=1u;
    unsigned attempts=status_attempts;comp_v11_ota_gatt_poll();CHECK(status_attempts==attempts+1u&&status_writes==before);
    comp_v11_ota_gatt_poll();CHECK(status_writes==before+1u);before=status_writes;
    comp_v11_ota_gatt_connection(true);nested_status=1u;
    comp_v11_ota_gatt_poll();comp_v11_ota_gatt_poll();CHECK(status_writes==before+2u);
    window(0);CHECK(borrowed&&get32(published+8)==0);
    for(unsigned i=0;i<15u;++i){comp_v11_ota_gatt_poll();CHECK(get32(published+8)==0&&borrowed);}
    comp_v11_ota_gatt_poll();CHECK(!borrowed&&get32(published+8)==3840u&&storage_writes==16u);
    CHECK(!early_receipt&&control_calls==1u&&finish_calls==0u);
    window(16);
    for(unsigned i=0;i<16u;++i)comp_v11_ota_gatt_poll();
    CHECK(get32(published+8)==sizeof(stored)&&control_calls==1u&&finish_calls==0u);
    const comp_v11_ota_gatt_timing_t *timing=comp_v11_ota_gatt_timing();
    CHECK(timing->received==32u&&timing->processed==32u&&timing->peak_queue==16u);
    CHECK(timing->data_us==96000u&&timing->data_max_us==3000u&&timing->queue_max_us>=45000u&&!timing->overflow);
    for(unsigned i=0;i<32u;++i)for(unsigned j=0;j<240u;++j)CHECK(stored[i*240u+j]==i);
    uint8_t done[20]={'D','O','V','1',DENZIC_OTA_V1_OP_FINISH,1};
    packet(0,done,sizeof(done));comp_v11_ota_gatt_poll();
    CHECK(finish_calls==1u&&published[5]==DENZIC_OTA_V1_STATE_COMPLETE);
    before=status_writes;for(unsigned i=0;i<1000u;++i)comp_v11_ota_gatt_poll();CHECK(status_writes==before);
    /* A failed physical write cannot be advanced by an empty queue/read. */
    denzic_ota_v1_reset(&transfer);begin_packet();fail_write=5u;window(0);
    for(unsigned i=0;i<16u;++i)comp_v11_ota_gatt_poll();
    CHECK(!borrowed&&published[5]==DENZIC_OTA_V1_STATE_ERROR);
    CHECK(get32(published+8)==960u&&transfer.bytes_written==960u);
    before=status_writes;for(unsigned i=0;i<1000u;++i)comp_v11_ota_gatt_poll();CHECK(status_writes==before);
    /* Disconnect drops queued DATA; the old window is never published as full. */
    fail_write=0;denzic_ota_v1_reset(&transfer);begin_packet();window(0);
    for(unsigned i=0;i<4u;++i)comp_v11_ota_gatt_poll();
    comp_v11_ota_gatt_connection(false);CHECK(!borrowed);
    comp_v11_ota_gatt_poll();CHECK(get32(published+8)==960u);
    CHECK(!early_receipt&&finish_calls==1u);
    puts("PASS: actual GATT+DOV1 exact receiving/complete/error receipt cache, every changing field, failed/nested ACI invalidation, queue/service timing, two16x240 durable windows, write failure/disconnect/FINISH. Hardware/speed NOT_RUN.");
    return 0;
}
