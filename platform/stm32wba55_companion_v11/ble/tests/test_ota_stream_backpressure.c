/* The generated include contains the actual two production app_ble functions,
 * not a second implementation of their pause/replay policy. Host-only radio
 * and AMM shims let the real GATT ring + DOV1 storage exercise the whole gate. */
#include "wba_ota_gatt.h"
#include "denzic_ota_v1.h"
#include "ble_core.h"
#include "svc_ctl.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "companion_opus16_rt.h"
#define FALSE 0
#define CFG_TASK_HCI_ASYNCH_EVT_ID 0
#define CFG_SEQ_PRIO_0 0
typedef struct node {struct node *next,*prev;} tListNode;
typedef struct {tListNode node;hci_uart_pckt evtserial;unsigned freed;} BleEvtPacket_t;
typedef enum {SVCCTL_UserEvtFlowEnable,SVCCTL_UserEvtFlowDisable} SVCCTL_UserEvtFlowStatus_t;
static tListNode BleAsynchEventQueue;
static bool user_event_flow_paused,scheduled;
static unsigned freed_packets,dispatch_calls,host_progress,added;
static BleEvtPacket_t packets[200];static unsigned packet_count;
static uint16_t handles[4];static uint8_t published[COMP_V11_OTA_STATUS_BYTES];
static SVCCTL_EvtAckStatus_t (*handler)(void *);
static void LST_insert_head(tListNode *h,tListNode *n)
{n->next=h->next;n->prev=h;h->next->prev=n;h->next=n;}
static void LST_insert_tail(tListNode *h,tListNode *n)
{n->prev=h->prev;n->next=h;h->prev->next=n;h->prev=n;}
static bool LST_is_empty(tListNode *h){return h->next==h;}
static void LST_remove_head(tListNode *h,tListNode **n)
{assert(!LST_is_empty(h));*n=h->next;h->next=(*n)->next;h->next->prev=h;}
static void AMM_Free(uint32_t *p)
{BleEvtPacket_t *e=(void*)p;assert(!e->freed);e->freed=1;++freed_packets;}
static void UTIL_SEQ_SetTask(unsigned task,unsigned priority)
{(void)task;(void)priority;scheduled=true;}
static void BleStackCB_Process(void){++host_progress;}
static SVCCTL_UserEvtFlowStatus_t SVCCTL_UserEvtRx(void *p)
{++dispatch_calls;return handler(p)==SVCCTL_EvtAckFlowDisable?SVCCTL_UserEvtFlowDisable:SVCCTL_UserEvtFlowEnable;}
#include "production_user_event_dispatch.inc"
void SVCCTL_RegisterSvcHandler(SVCCTL_EvtAckStatus_t (*f)(void *)){handler=f;}
uint8_t aci_gatt_add_service(uint8_t t,const Service_UUID_t *u,uint8_t p,uint8_t n,uint16_t *h)
{(void)t;(void)u;(void)p;(void)n;*h=1;return 0;}
uint8_t aci_gatt_add_char(uint16_t s,uint8_t t,const Char_UUID_t *u,uint16_t n,uint8_t p,uint8_t a,uint8_t e,uint8_t k,uint8_t v,uint16_t *h)
{(void)s;(void)t;(void)u;(void)n;(void)p;(void)a;(void)e;(void)k;(void)v;assert(added<4);*h=(uint16_t)(10+2*added);handles[added++]=*h;return 0;}
uint8_t aci_gatt_update_char_value(uint16_t s,uint16_t h,uint8_t off,uint8_t n,const uint8_t *b)
{(void)s;(void)off;if(h==handles[2]){assert(n==sizeof(published));memcpy(published,b,n);}return 0;}
static denzic_ota_v1_context_t transfer;
static uint8_t stored[64*491];static unsigned storage_calls,fail_write,expected_size;
static bool borrowed,early_receipt;static void *arena;static uint32_t now;
static uint32_t get32(const uint8_t *b)
{return (uint32_t)b[0]|((uint32_t)b[1]<<8)|((uint32_t)b[2]<<16)|((uint32_t)b[3]<<24);}
static void put32(uint8_t *b,uint32_t v){for(unsigned i=0;i<4;++i)b[i]=(uint8_t)(v>>(8*i));}
static bool begin(void *c,uint32_t n){(void)c;storage_calls=0;return n==expected_size;}
static bool write_data(void *c,const uint8_t *b,size_t n)
{
 (void)c;++storage_calls;
 comp_v11_ota_gatt_poll(); /* NOR progress cannot retire/reuse its own slot. */
 if(get32(published+8)>transfer.bytes_written)early_receipt=true;
 if(storage_calls==fail_write)return false;
 assert(transfer.bytes_written+n<=sizeof(stored));memcpy(stored+transfer.bytes_written,b,n);return true;
}
static bool finish(void *c){(void)c;return true;}
static void abort_write(void *c){(void)c;}
static bool control(void *c,const uint8_t *b,size_t n){(void)c;return denzic_ota_v1_handle_control(&transfer,b,n);}
static bool data(void *c,const uint8_t *b,size_t n){(void)c;return denzic_ota_v1_handle_data(&transfer,b,n);}
static size_t status(void *c,uint8_t *b,size_t n){(void)c;return denzic_ota_v1_encode_status(&transfer,b,n);}
static void *claim(void *c,size_t n)
{(void)c;assert(n==8840);assert(!borrowed);arena=companion_opus16_rt_workspace_borrow(n);assert(arena);borrowed=true;return arena;}
static void release(void *c,void *p){(void)c;assert(borrowed&&p==arena);companion_opus16_rt_workspace_release(p);borrowed=false;arena=NULL;}
static uint32_t clock_ms(void *c){(void)c;return now;}
static void pump(void)
{unsigned turns=0;while(scheduled){scheduled=false;Ble_UserEvtRx();assert(++turns<1000);}}
static void packet(unsigned kind,const uint8_t *bytes,unsigned length,unsigned offset)
{
 assert(length<=245&&packet_count<200);BleEvtPacket_t *p=&packets[packet_count++];
 hci_event_pckt *e=(void*)p->evtserial.data;evt_blecore_aci *v=(void*)e->data;
 aci_gatt_attribute_modified_event_rp0 *a=(void*)v->data;
 e->evt=HCI_VENDOR_SPECIFIC_DEBUG_EVT_CODE;e->plen=(uint8_t)(10u+length);v->ecode=ACI_GATT_ATTRIBUTE_MODIFIED_VSEVT_CODE;
 a->Attr_Handle=(uint16_t)(handles[kind]+1);a->Attr_Data_Length=(uint16_t)length;a->Offset=(uint16_t)offset;memcpy(a->Attr_Data,bytes,length);
 LST_insert_tail(&BleAsynchEventQueue,&p->node);
 if(!user_event_flow_paused)UTIL_SEQ_SetTask(1,0);
}
static void value(unsigned first,unsigned payload)
{
 uint8_t b[509];memset(b,(int)first,sizeof(b));put32(b,first*payload);
 unsigned size=payload+4;
 for(unsigned off=0;off<size;){unsigned n=size-off;if(n>245)n=245;packet(1,b+off,n,off|(off+n<size?0x8000u:0));off+=n;}
}
static void drain(void)
{
 unsigned turns=0;
 while(borrowed||!LST_is_empty(&BleAsynchEventQueue)||scheduled){comp_v11_ota_gatt_poll();pump();assert(++turns<1000);}
 comp_v11_ota_gatt_poll();assert(!user_event_flow_paused);
}
static void start(unsigned payload,unsigned chunks)
{
 assert(!borrowed&&LST_is_empty(&BleAsynchEventQueue));
 packet_count=freed_packets=dispatch_calls=0;memset(packets,0,sizeof(packets));memset(stored,0,sizeof(stored));
 denzic_ota_v1_reset(&transfer);comp_v11_ota_gatt_connection(true);expected_size=payload*chunks;
 uint8_t b[20]={'D','O','V','1',DENZIC_OTA_V1_OP_BEGIN,1};put32(b+8,expected_size);b[12]=(uint8_t)payload;b[13]=(uint8_t)(payload>>8);b[14]=(uint8_t)chunks;
 packet(0,b,sizeof(b),0);pump();drain();assert(transfer.state==DENZIC_OTA_V1_STATE_RECEIVING);
}
int main(void)
{
 BleAsynchEventQueue.next=BleAsynchEventQueue.prev=&BleAsynchEventQueue;
 denzic_ota_v1_storage_driver_t storage={begin,write_data,finish,abort_write};
 denzic_ota_v1_init(&transfer,storage,NULL,505,64);
 comp_v11_ota_gatt_ports_t p={control,data,status,NULL,claim,release,clock_ms,NULL};
 assert(comp_v11_ota_gatt_init(&p));
 for(unsigned payload=215;payload<=491;payload+=276){
  start(payload,64);
  for(unsigned i=0;i<64;++i)value(i,payload);
  pump();assert(user_event_flow_paused&&borrowed);assert(storage_calls==0&&freed_packets<packet_count);
  tListNode *retained=BleAsynchEventQueue.next;unsigned before=dispatch_calls,progress=host_progress;
  for(unsigned i=0;i<20;++i)Ble_UserEvtRx();
  assert(BleAsynchEventQueue.next==retained&&dispatch_calls==before&&host_progress==progress);
  /* One foreground retirement resumes exactly the retained first fragment. */
  comp_v11_ota_gatt_poll();assert(!user_event_flow_paused&&scheduled);pump();assert(BleAsynchEventQueue.next!=retained);
  drain();assert(storage_calls==64&&transfer.bytes_written==expected_size&&get32(published+8)==expected_size);
  assert(freed_packets==packet_count&&!early_receipt);
  for(unsigned i=0;i<64;++i)for(unsigned j=0;j<payload;++j)assert(stored[i*payload+j]==i);
  assert(!memcmp(published+24,"WOC3",4)&&published[32]==64&&published[34]==13&&published[36]==16);
  assert(comp_v11_ota_gatt_timing()->peak_queue==16);
 }
 /* A physical failure stops the durable cursor; queued RAM cannot certify it. */
 start(491,64);fail_write=5;for(unsigned i=0;i<64;++i)value(i,491);pump();drain();
 assert(transfer.state==DENZIC_OTA_V1_STATE_ERROR&&get32(published+8)==4*491&&!early_receipt);fail_write=0;
 /* Disconnect retires the retained old head without another storage call. */
 start(215,64);for(unsigned i=0;i<17;++i)value(i,215);pump();assert(user_event_flow_paused);
 comp_v11_ota_gatt_connection(false);pump();drain();assert(storage_calls==0&&freed_packets==packet_count);
 start(215,1);value(0,215);pump();drain();assert(storage_calls==1&&transfer.bytes_written==215);
 puts("PASS: production dispatch retains/replays exact AMM event, fixed8840B real CE lease,64-command streams with215/491 payloads, long ACI fragments, full queue, bounded resume, NOR failure and disconnect retirement. Hardware/speed NOT_RUN.");return 0;
}
