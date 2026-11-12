/* Production GATT + DOV1 + real CE arena. Radio and NOR are host shims;
 * this establishes credit/durability/overrun invariants, never RF speed. */
#include "wba_ota_gatt.h"
#include "denzic_ota_v1.h"
#include "companion_opus16_rt.h"
#include "ble_core.h"
#include "svc_ctl.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static SVCCTL_EvtAckStatus_t (*callback)(void *);
static denzic_ota_v1_context_t transfer;
static uint16_t handles[4];static unsigned added;
static uint8_t published[COMP_V11_OTA_STATUS_BYTES],latest[COMP_V11_OTA_STATUS_BYTES];
static unsigned expected,storage_calls,abort_calls,notifications,status_busy,fail_write;
static unsigned nested_overrun,global_resumes;
static unsigned status_owner_action;
static bool finish_partial_in_status;
static bool cccd,borrowed,early_receipt;static void *arena;static uint32_t now;
static uint8_t stored[64*491+17];
static FILE *wire_transcript;
static unsigned phase_data_ms,phase_status_ms,phase_nested_offset,phase_status_offset;
static bool slice_new_connection;
static unsigned slice_control_calls;
static unsigned status_builds;
static void value(unsigned offset,unsigned n,unsigned marker);
static void packet(unsigned kind,const uint8_t *bytes,unsigned length,unsigned offset);
static uint32_t get32(const uint8_t *b)
{return (uint32_t)b[0]|((uint32_t)b[1]<<8)|((uint32_t)b[2]<<16)|((uint32_t)b[3]<<24);}
static void put32(uint8_t *b,uint32_t v){for(unsigned i=0;i<4;++i)b[i]=(uint8_t)(v>>(i*8));}
void SVCCTL_RegisterSvcHandler(SVCCTL_EvtAckStatus_t (*f)(void *)){callback=f;}
void SVCCTL_ResumeUserEventFlow(void){++global_resumes;assert(0&&"OTA must never pause/resume global HCI delivery");}
uint8_t aci_gatt_add_service(uint8_t t,const Service_UUID_t *u,uint8_t p,uint8_t n,uint16_t *h)
{(void)t;(void)u;(void)p;assert(n==10);*h=1;return 0;}
uint8_t aci_gatt_add_char(uint16_t s,uint8_t t,const Char_UUID_t *u,uint16_t n,uint8_t p,uint8_t a,uint8_t e,uint8_t k,uint8_t v,uint16_t *h)
{(void)s;(void)t;(void)u;(void)a;(void)e;(void)k;(void)v;assert(added<4);
 if(added==2)assert(n==COMP_V11_OTA_STATUS_BYTES&&p==(CHAR_PROP_READ|CHAR_PROP_NOTIFY));
 *h=(uint16_t)(10+2*added);handles[added++]=*h;return 0;}
static uint8_t update_value(uint16_t s,uint16_t h,uint8_t off,uint8_t n,const uint8_t *b,bool notify)
{
 (void)s;(void)off;if(h!=handles[2])return 0;assert(n==COMP_V11_OTA_STATUS_BYTES);
 now+=phase_status_ms;
 if(status_busy){--status_busy;return BLE_STATUS_INSUFFICIENT_RESOURCES;}
 if(phase_status_offset) {
  unsigned offset=phase_status_offset;phase_status_offset=0;value(offset,215,2);
  assert(comp_v11_ota_gatt_phase_timing()->phase==3u); /* ACI owns nested receive time */
 }
 if(notify && finish_partial_in_status) {
  uint8_t tail[470];memset(tail,5,sizeof(tail));put32(tail,4u*466u);
  finish_partial_in_status=false;packet(1,tail+245,225,245);
 }
 memcpy(published,b,n);
 if(cccd&&notify){memcpy(latest,b,n);++notifications;if(wire_transcript)assert(fwrite(b,1,n,wire_transcript)==n);}
 /* The SDK may dispatch security/CCCD callbacks inside the ACI wait.
  * This is only an event-order injection, not a fake durable write. */
 if(notify && status_owner_action) {
  unsigned action=status_owner_action;status_owner_action=0;
  if(action==1u)comp_v11_ota_gatt_connection(true);
  else {uint8_t on[2]={1,0};packet(4,on,2,0);}
 }
 return 0;
}
uint8_t aci_gatt_update_char_value(uint16_t s,uint16_t h,uint8_t off,uint8_t n,const uint8_t *b)
{return update_value(s,h,off,n,b,true);}
uint8_t aci_gatt_update_char_value_ext(uint16_t c,uint16_t s,uint16_t h,uint8_t u,uint16_t size,uint16_t off,uint8_t n,const uint8_t *b)
{assert(c==0x0FFFu&&size==COMP_V11_OTA_STATUS_BYTES&&off==0);return update_value(s,h,(uint8_t)off,n,b,u!=0);}
static void packet(unsigned kind,const uint8_t *bytes,unsigned length,unsigned offset)
{
 hci_uart_pckt p={0};hci_event_pckt *e=(void*)p.data;evt_blecore_aci *v=(void*)e->data;
 aci_gatt_attribute_modified_event_rp0 *a=(void*)v->data;assert(length<=245);
 e->evt=HCI_VENDOR_SPECIFIC_DEBUG_EVT_CODE;e->plen=(uint8_t)(10+length);v->ecode=ACI_GATT_ATTRIBUTE_MODIFIED_VSEVT_CODE;
 a->Attr_Handle=(uint16_t)(handles[kind==4?2:kind]+(kind==4?2:1));a->Attr_Data_Length=(uint16_t)length;a->Offset=(uint16_t)offset;memcpy(a->Attr_Data,bytes,length);
 assert(callback(&p)==SVCCTL_EvtAckFlowEnable); /* even a malicious excess packet cannot freeze global events */
}
static void value(unsigned offset,unsigned n,unsigned marker)
{
 uint8_t b[509];assert(n<=505);memset(b,(int)marker,sizeof(b));put32(b,offset);unsigned size=n+4;
 for(unsigned off=0;off<size;){unsigned length=size-off;if(length>245)length=245;packet(1,b+off,length,length+off<size?off|0x8000u:off);off+=length;}
}
static bool begin(void *c,uint32_t size){(void)c;storage_calls=0;return size==expected;}
static bool write_data(void *c,const uint8_t *b,size_t n)
{
 (void)c;++storage_calls;comp_v11_ota_gatt_poll();
 if(slice_new_connection) {
  slice_new_connection=false;comp_v11_ota_gatt_connection(false);comp_v11_ota_gatt_connection(true);
  value(215,215,2);comp_v11_ota_gatt_poll_slice(); /* cannot reenter the active worker */
 }
 if(phase_data_ms) {
  ++now;
  if(phase_nested_offset) {
   unsigned offset=phase_nested_offset;phase_nested_offset=0;
   value(offset,215,3);comp_v11_ota_gatt_poll();
   assert(comp_v11_ota_gatt_phase_timing()->phase==2u); /* nested DATA stays DATA */
  }
  now+=phase_data_ms-1u;
 }
 if(get32(published+8)>transfer.bytes_written)early_receipt=true;
 if(nested_overrun){nested_overrun=0;for(unsigned i=0;i<=(unsigned)published[36];++i)value((i+1)*215,215,i+1);comp_v11_ota_gatt_poll();assert(borrowed);}
 if(storage_calls==fail_write)return false;
 assert(transfer.bytes_written+n<=sizeof(stored));memcpy(stored+transfer.bytes_written,b,n);return true;
}
static bool finish(void *c){(void)c;return true;}
static void abort_write(void *c){(void)c;++abort_calls;}
static bool control(void *c,const uint8_t *b,size_t n){(void)c;++slice_control_calls;return denzic_ota_v1_handle_control(&transfer,b,n);}
static bool data(void *c,const uint8_t *b,size_t n){(void)c;return denzic_ota_v1_handle_data(&transfer,b,n);}
static size_t status(void *c,uint8_t *b,size_t n){(void)c;++status_builds;return denzic_ota_v1_encode_status(&transfer,b,n);}
static void *claim(void *c,size_t n){(void)c;assert(!borrowed&&n==8840);arena=companion_opus16_rt_workspace_borrow(n);assert(arena);borrowed=true;return arena;}
static void release(void *c,void *p){(void)c;assert(borrowed&&p==arena);companion_opus16_rt_workspace_release(p);borrowed=false;arena=NULL;}
static uint32_t clock_ms(void *c){(void)c;return now;}
static void start(unsigned payload,unsigned size)
{
 assert(!borrowed);expected=size;memset(stored,0,sizeof(stored));
 uint8_t abort[20]={'D','O','V','1',DENZIC_OTA_V1_OP_ABORT,1};packet(0,abort,20,0);comp_v11_ota_gatt_poll();
 uint8_t b[20]={'D','O','V','1',DENZIC_OTA_V1_OP_BEGIN,1};put32(b+8,size);b[12]=(uint8_t)payload;b[13]=(uint8_t)(payload>>8);b[14]=64;
 packet(0,b,20,0);comp_v11_ota_gatt_poll();assert(transfer.state==DENZIC_OTA_V1_STATE_RECEIVING);
 assert(!memcmp(published+24,"WOC5",4)&&!memcmp(published+44,"BLK1",4)&&published[48]==0&&published[34]==53&&get32(published+40)!=0);
}
static void check_phase_wall_ledger(void)
{
 const comp_v11_ota_phase_timing_t *t=comp_v11_ota_gatt_phase_timing();
 start(215,4*215);phase_data_ms=2;phase_status_ms=1;
 now=100;value(0,215,1);now=103;comp_v11_ota_gatt_poll();assert(now==106);
 now=110;value(215,215,2);phase_nested_offset=430;
 now=114;comp_v11_ota_gatt_poll();assert(now==116&&borrowed);
 now=119;comp_v11_ota_gatt_poll();assert(now==122&&!borrowed);
 now=127;value(645,215,4);now=129;comp_v11_ota_gatt_poll();
 assert(now==132&&t->started&&!t->running&&!t->invalid&&t->span_us==31000);
 assert(t->ready_us==12000&&t->data_us==8000&&t->status_us==2000&&t->empty_us==9000&&t->other_us==0);
 assert(t->span_us==t->ready_us+t->data_us+t->status_us+t->empty_us+t->other_us);
 /* Publishing the final receipt and waiting for FINISH are outside this
  * explicit first-complete-to-full-durable boundary, not silently omitted. */
 now+=100;comp_v11_ota_gatt_poll();assert(t->span_us==31000);
 start(215,430);phase_status_ms=3;phase_status_offset=215;
 now=200;value(0,215,1);now=201;comp_v11_ota_gatt_poll();assert(now==206&&borrowed);
 now=210;comp_v11_ota_gatt_poll();assert(now==215);
 assert(t->span_us==12000&&t->ready_us==5000&&t->data_us==4000&&t->status_us==3000&&!t->empty_us&&!t->invalid);
 phase_status_ms=0;
 /* A partial long value cannot start the complete-command ledger. */
 start(466,466);uint8_t b[470];memset(b,3,sizeof(b));put32(b,0);
 now=500;packet(1,b,245,0x8000u);assert(!t->started);
 now=504;packet(1,b+245,225,245);assert(t->started&&t->start_us==504000);
 now=509;comp_v11_ota_gatt_poll();assert(t->span_us==7000&&t->ready_us==5000&&t->data_us==2000&&!t->invalid);
 /* The 32-bit microsecond clock may wrap inside a short OTA. */
 start(215,215);now=UINT32_MAX/1000u-1u;value(0,215,1);
 now+=10;comp_v11_ota_gatt_poll();assert(t->span_us==12000&&t->ready_us==10000&&t->data_us==2000&&!t->invalid);
 /* Failed storage and disconnect are explicitly invalid, never complete. */
 start(215,215);now=1000;value(0,215,1);fail_write=1;now=1001;comp_v11_ota_gatt_poll();
 assert(t->started&&!t->running&&t->invalid==1u);fail_write=0;
 start(215,215);now=1020;value(0,215,1);now=1023;comp_v11_ota_gatt_connection(false);
 assert(!t->running&&t->invalid==2u&&t->span_us==3000&&t->ready_us==3000);
 comp_v11_ota_gatt_connection(true);phase_data_ms=0;
 puts("OTA_PHASE_LEDGER exclusive31ms ready12/data8/status2/empty9 nested_data nested_status partial_start clock_wrap errors_excluded");
}
static void check_packed_geometry_boundaries(void)
{
 /* Padding in the maximum stride is not an extension of the wire limit.
  * A fragmented512B value must retire its lease, then accept a valid509B. */
 start(505,505);uint8_t oversized[512];memset(oversized,7,sizeof(oversized));put32(oversized,0);
 packet(1,oversized,245,0x8000u);packet(1,oversized+245,245,0x8000u|245u);
 packet(1,oversized+490,22,490);comp_v11_ota_gatt_poll();assert(!borrowed&&storage_calls==0);
 value(0,505,3);comp_v11_ota_gatt_poll();assert(!borrowed&&transfer.bytes_written==505&&storage_calls==1);
 /* Grow and shrink the same real arena across fresh BEGINs. Reserve the
  * ordered SYNC slot even when every advertised DATA slot is occupied. */
 const unsigned payloads[]={240,215,491,505,215};
 const unsigned slots[]={34,37,16,16,37};
 for(unsigned j=0;j<sizeof(payloads)/sizeof(payloads[0]);++j) {
  unsigned n=payloads[j],cap=slots[j];start(n,cap*n+17);assert(published[36]==cap);
  for(unsigned i=0;i<cap;++i)value(i*n,n,i);
  uint8_t sync[20]={'D','O','V','1',DENZIC_OTA_V1_OP_SYNC,1};packet(0,sync,20,0);
  while(borrowed)comp_v11_ota_gatt_poll();assert(storage_calls==cap&&transfer.bytes_written==cap*n&&!early_receipt);
  for(unsigned i=0;i<cap;++i)for(unsigned k=0;k<n;++k)assert(stored[i*n+k]==i);
 }
 /* DATA arriving before BEGIN's new geometry receipt cannot be relocated
  * under an owned old slot. Fail this transfer, keep global delivery live. */
 start(215,430);unsigned before=abort_calls;
 uint8_t b[20]={'D','O','V','1',DENZIC_OTA_V1_OP_BEGIN,1};put32(b+8,430);b[12]=249;b[13]=1;b[14]=64;
 packet(0,b,20,0);value(0,215,1);comp_v11_ota_gatt_poll();
 assert(borrowed&&storage_calls==0);comp_v11_ota_gatt_poll();
 assert(!borrowed&&storage_calls==0&&abort_calls==before+1&&published[5]==DENZIC_OTA_V1_STATE_ERROR);
 start(505,505);value(0,505,4);comp_v11_ota_gatt_poll();assert(transfer.bytes_written==505&&!borrowed);
 puts("PACKED_GEOMETRY malformed512_rejected valid509 recovery grow_shrink reserved_SYNC premature_DATA_abort");
}
static void check_bounded_foreground_slice(void)
{
 phase_data_ms=1;phase_status_ms=0;
 start(215,860);now=2000;
 for(unsigned i=0;i<4;++i)value(i*215,215,i+1);
 comp_v11_ota_gatt_poll_slice();assert(storage_calls==2&&borrowed&&now==2002);
 comp_v11_ota_gatt_poll_slice();assert(storage_calls==4&&!borrowed&&now==2004);
 start(215,430);now=2100;phase_data_ms=4;value(0,215,1);value(215,215,2);
 comp_v11_ota_gatt_poll_slice();assert(storage_calls==1&&borrowed&&now==2104);
 comp_v11_ota_gatt_poll();assert(storage_calls==2&&!borrowed);
 phase_data_ms=1;start(215,430);now=2200;value(0,215,1);
 uint8_t sync[20]={'D','O','V','1',DENZIC_OTA_V1_OP_SYNC,1};packet(0,sync,20,0);value(215,215,2);
 unsigned before_control=slice_control_calls;
 comp_v11_ota_gatt_poll_slice();assert(storage_calls==1&&borrowed&&get32(published+8)==0&&slice_control_calls==before_control);
 comp_v11_ota_gatt_poll();assert(storage_calls==1&&transfer.bytes_written==215&&slice_control_calls==before_control+1);
 comp_v11_ota_gatt_poll_slice();assert(storage_calls==2&&!borrowed);
 start(215,430);now=2300;value(0,215,1);value(215,215,2);fail_write=1;
 comp_v11_ota_gatt_poll_slice();assert(storage_calls==1&&borrowed&&transfer.state==DENZIC_OTA_V1_STATE_ERROR);
 while(borrowed)comp_v11_ota_gatt_poll();fail_write=0;
 start(215,430);now=2400;value(0,215,1);value(215,215,2);slice_new_connection=true;
 comp_v11_ota_gatt_poll_slice();assert(storage_calls==1&&borrowed); /* old queued DATA discarded; new epoch not serviced */
 comp_v11_ota_gatt_poll();assert(storage_calls==2&&!borrowed);
 start(215,430);now=UINT32_MAX-1u;value(0,215,1);value(215,215,2);
 comp_v11_ota_gatt_poll_slice();assert(storage_calls==2&&!borrowed&&now==0u);
 phase_data_ms=0;
 puts("OTA_BOUNDED_SLICE max2 slow_first_ge4ms_yields control_fence error_stops disconnect_epoch nested_worker ms_wrap");
}
static bool check_partial_data_does_not_hold_durable_credit(void)
{
 /* Four completed writes return four durable credits while the fifth
  * long GATT value is still incomplete. Its slot remains owned. */
 for(unsigned nested=0; nested<2; ++nested) {
  start(466,8u*466u);notifications=0;
  for(unsigned i=0;i<4;++i)value(i*466u,466u,i+1u);
  uint8_t fifth[470];memset(fifth,5,sizeof(fifth));put32(fifth,4u*466u);
  packet(1,fifth,245,0x8000u);
  finish_partial_in_status=nested!=0;
  for(unsigned i=0;i<4;++i)comp_v11_ota_gatt_poll();
  if(notifications!=1 || get32(latest+8)!=4u*466u ||
     transfer.bytes_written!=4u*466u || !borrowed) {
   printf("PARTIAL_DATA_HOLDS_DURABLE_CREDIT nested=%u notifications=%u durable=%u notified=%u retained=%u\n",
    nested,notifications,transfer.bytes_written,get32(latest+8),(unsigned)borrowed);
   return false;
  }
  assert(storage_calls==4 && !early_receipt);
  if(!nested)packet(1,fifth+245,225,245);
  assert(!finish_partial_in_status);
  comp_v11_ota_gatt_poll();
  assert(!borrowed && storage_calls==5 && transfer.bytes_written==5u*466u);
  for(unsigned i=0;i<5;++i)for(unsigned j=0;j<466;++j)assert(stored[i*466u+j]==i+1u);
 }
 /* A timed-out partial value is discarded, never credited or written. */
 start(466,8u*466u);notifications=0;
 for(unsigned i=0;i<4;++i)value(i*466u,466u,i+1u);
 uint8_t fifth[245]={0};put32(fifth,4u*466u);packet(1,fifth,245,0x8000u);
 for(unsigned i=0;i<4;++i)comp_v11_ota_gatt_poll();
 assert(notifications==1 && borrowed && transfer.bytes_written==4u*466u);
 now+=1000;comp_v11_ota_gatt_poll();
 assert(!borrowed && storage_calls==4 && notifications==1 && transfer.bytes_written==4u*466u);
 puts("PARTIAL_DATA_CREDIT durable4_before_fifth_complete; nested_completion_retains_slot; timeout_never_credited");
 return true;
}
int main(int argc,char **argv)
{
 if(argc==2){
#ifdef _MSC_VER
  assert(fopen_s(&wire_transcript,argv[1],"wb")==0);
#else
  wire_transcript=fopen(argv[1],"wb");
#endif
  assert(wire_transcript);
 }else assert(argc==1);
 denzic_ota_v1_storage_driver_t storage={begin,write_data,finish,abort_write};denzic_ota_v1_init(&transfer,storage,NULL,505,64);
 comp_v11_ota_gatt_ports_t ports={control,data,status,NULL,claim,release,clock_ms,NULL};assert(comp_v11_ota_gatt_init(&ports));comp_v11_ota_gatt_connection(true);
 comp_v11_ota_gatt_poll();assert(!notifications);uint8_t on[2]={1,0};cccd=true;packet(4,on,2,0);comp_v11_ota_gatt_poll();assert(notifications==1);
 unsigned builds_before=status_builds;
 for(unsigned i=0u;i<10000u;++i)comp_v11_ota_gatt_poll();
 assert(status_builds==builds_before);
 /* A mount/error transition outside a queued callback refreshes immediately.
  * Rejected ACI publication retries, even without a successor command. */
 transfer.last_error=DENZIC_OTA_V1_ERROR_STORAGE_BEGIN;
 comp_v11_ota_gatt_status_changed();status_busy=1u;
 comp_v11_ota_gatt_poll();assert(status_builds==builds_before+1u);
 comp_v11_ota_gatt_poll();assert(status_builds==builds_before+2u&&published[6]==transfer.last_error);
 transfer.last_error=0u;comp_v11_ota_gatt_status_changed();comp_v11_ota_gatt_poll();
 puts("OTA_IDLE_STATUS unchanged10000_build0 asynchronous_refresh failed_publish_retry");
 if(!check_partial_data_does_not_hold_durable_credit())return 57;
 check_phase_wall_ledger();
 check_bounded_foreground_slice();
 check_packed_geometry_boundaries();
 /* Same real Opus arena, no allocation growth:215-byte values must admit
  *37 packets before durable receipts are required;491-byte values stay16. */
 start(215,64*215);
 if(published[36]!=37u){printf("PACKED_QUEUE_NOT_ACTIVE slots=%u expected=37\n",published[36]);return 56;}
 for(unsigned i=0;i<37u;++i)value(i*215u,215u,i);
 assert(borrowed&&comp_v11_ota_gatt_timing()->peak_queue==37u);
 while(borrowed)comp_v11_ota_gatt_poll();
 assert(transfer.bytes_written==37u*215u&&!early_receipt);
 puts("PACKED_QUEUE actual8840-byte CE lease:215B=37 slots, max payload keeps16; no early durable credit");
 /* A publication begun under the old notification owner must not suppress
  * the first credit for the owner established inside that call. Existing
  * tests counted READ value updates; here the actual notify flag matters. */
 for(unsigned action=1u;action<=2u;++action) {
  start(215,64*215);notifications=0;
  for(unsigned i=0;i<7;++i){value(i*215,215,i);comp_v11_ota_gatt_poll();}
  status_owner_action=action;value(7*215,215,7);comp_v11_ota_gatt_poll();
  assert(!status_owner_action&&!borrowed&&transfer.bytes_written==8*215);
  unsigned before=notifications;comp_v11_ota_gatt_poll();
  if(notifications!=before+1 || get32(latest+8)!=8*215) {
   printf("STALE_NOTIFY_OWNER action=%u committed=%u before=%u after=%u local_prefix=%u notified_prefix=%u\n",
    action,transfer.bytes_written,before,notifications,get32(published+8),get32(latest+8));return 55;
  }
  comp_v11_ota_gatt_poll();assert(notifications==before+1); /* one repair, no storm */
#ifdef TEST_PUBLISH_OBSERVER
  const comp_v11_ota_publish_diagnostics_t *pub=comp_v11_ota_gatt_publish_diagnostics();
  assert(pub->notify_calls==2u && pub->owner_invalidations==1u && pub->not_accepted==0u && !pub->flags);
#endif
 }
 puts("OTA_NOTIFY_OWNER security_refresh_and_CCCD_during_ACI: fresh_durable_notification_once");
 /* A physical-credit sender must refill before the DATA ring empties.
  * This is a regression reproducer: the previous empty-ring gate has eight
  * committed writes here but no notification, so it returns42 explicitly. */
 start(215,64*215);notifications=0;
 for(unsigned i=0;i<16;++i)value(i*215,215,i);
 for(unsigned i=0;i<8;++i)comp_v11_ota_gatt_poll();
 if(!notifications || get32(latest+8)!=8*215 || !borrowed) {
  printf("QUEUE_BUSY_CREDIT_MISSING committed_packets=%u notified_bytes=%u notifications=%u ring_owned=%u\n",
      storage_calls,get32(latest+8),notifications,(unsigned)borrowed);return 42;
 }
 /* The returned credit is only the committed prefix. Eight remaining
  * packets stay owned while the next eight refill the same byte arena. */
 assert(storage_calls==8&&!early_receipt&&get32(published+8)==8*215);
 for(unsigned i=16;i<24;++i)value(i*215,215,i);
 while(borrowed)comp_v11_ota_gatt_poll();
 assert(storage_calls==24&&get32(published+8)==24*215&&!early_receipt);
 puts("WOC4_BUSY_RING committed_before_refill=8 pending_before_refill=8 refill=8 local_completion_credit=0");
 /* Ordered control still fences a full-window receipt even though DATA
  * before it has already committed. Its reserved slot is retained. */
 start(215,64*215);notifications=0;
 for(unsigned i=0;i<16;++i)value(i*215,215,i);
 {uint8_t sync[20]={'D','O','V','1',DENZIC_OTA_V1_OP_SYNC,1};packet(0,sync,20,0);}
 for(unsigned i=0;i<16;++i){comp_v11_ota_gatt_poll();assert(!notifications&&get32(published+8)==0&&borrowed);}
 comp_v11_ota_gatt_poll();assert(!borrowed&&notifications==1&&get32(published+8)==16*215);
 uint32_t last_generation=0;
 for(unsigned payload=215;payload<=491;payload+=276){
  start(payload,64*payload+17);uint32_t generation=get32(published+40);assert(generation!=last_generation);last_generation=generation;
  unsigned offset=0,admitted=0,retired=0;notifications=0;
  while(offset<expected){
   if(admitted-retired==published[36]){
    unsigned before=notifications;status_busy=1;
    unsigned polls=0;
    while(notifications==before&&polls<16){comp_v11_ota_gatt_poll();++polls;}
    assert(notifications>before&&polls<16&&borrowed);
    assert(polls<=(payload==215u?9u:5u)); /* retry without whole-ring drain */
    assert(get32(latest+40)==generation);retired=get32(latest+8)/payload;
   }
   unsigned length=expected-offset;if(length>payload)length=payload;
   value(offset,length,admitted);offset+=length;++admitted;
   assert(admitted-retired<=published[36]);
  }
  while(borrowed)comp_v11_ota_gatt_poll();assert(get32(published+8)==expected&&storage_calls==65&&!early_receipt);
  for(unsigned i=0;i<64;++i)for(unsigned j=0;j<payload;++j)assert(stored[i*payload+j]==i);
  for(unsigned j=0;j<17;++j)assert(stored[64*payload+j]==64);
  if(payload==215u)assert(notifications>=8u&&notifications<=10u);
  /* One injected ACI busy per refill shifts four to five durable packets. */
  else assert(notifications>=13u&&notifications<=18u);assert(comp_v11_ota_gatt_timing()->peak_queue==published[36]);
  uint8_t done[20]={'D','O','V','1',DENZIC_OTA_V1_OP_FINISH,1};packet(0,done,20,0);comp_v11_ota_gatt_poll();assert(published[5]==DENZIC_OTA_V1_STATE_COMPLETE);
 }
 /* Current466B/17-credit arena: an actual durable quarter-window must
  * notify before the old8-packet threshold, including while the ring is busy.
  * Test an ACI-busy fourth write as well: no false baseline or early receipt. */
 for(unsigned busy=0u;busy<2u;++busy) {
  start(466,64*466);notifications=0;assert(published[36]==17u);
#ifdef TEST_PUBLISH_OBSERVER
  const comp_v11_ota_publish_diagnostics_t *pub=comp_v11_ota_gatt_publish_diagnostics();
  assert(pub->notify_calls==0u && pub->not_accepted==0u && pub->owner_invalidations==0u && pub->last_status==255u);
#endif
  for(unsigned i=0u;i<17u;++i)value(i*466u,466u,i);
  for(unsigned i=0u;i<3u;++i){comp_v11_ota_gatt_poll();assert(!notifications&&!early_receipt);}
  if(busy)status_busy=1u;
  comp_v11_ota_gatt_poll();assert(transfer.bytes_written==4u*466u&&!early_receipt&&borrowed);
  if(busy){assert(!notifications);comp_v11_ota_gatt_poll();}
  if(notifications!=1u||get32(latest+8)!=(4u+busy)*466u) {
   printf("SMALL_ARENA_CREDIT_TOO_LATE busy=%u committed=%u notifications=%u prefix=%u\n",busy,transfer.bytes_written,notifications,get32(latest+8));return 57;
  }
#ifdef TEST_PUBLISH_OBSERVER
  assert(pub->notify_calls==1u+busy && pub->not_accepted==busy && pub->owner_invalidations==0u && pub->last_status==0u && !pub->flags);
#endif
  unsigned retired=get32(latest+8)/466u;
  for(unsigned i=17u;i<17u+retired;++i)value(i*466u,466u,i);
  while(borrowed)comp_v11_ota_gatt_poll();
  assert(storage_calls==17u+retired&&!early_receipt&&transfer.bytes_written==(17u+retired)*466u);
 }
 puts("SMALL_ARENA_CREDIT durable4_of17 busy_retry_next_prefix bounded_refill_no_early_ACK");
 /* A naturally empty ring after each packet must not create one radio
  * status notification per packet. Local uncached READ still sees every write. */
 start(215,64*215);notifications=0;
 for(unsigned i=0;i<16;++i){value(i*215,215,i);comp_v11_ota_gatt_poll();
  assert(get32(published+8)==(i+1)*215);assert(notifications==(i+1)/8);}
 comp_v11_ota_gatt_connection(false);comp_v11_ota_gatt_poll();comp_v11_ota_gatt_connection(true);
 /* Explicit bit32 now guarantees64 even after the usual cadence shifted
  * to9,17,...57. Also fail the boundary's first ACI attempt: the empty
  * ring must retry without needing the next blocked DATA window. */
 start(215,64*215+17);notifications=0;status_busy=1;
 {
  const unsigned bursts[]={9,8,8,8,8,8,8,7};unsigned offset=0;
  for(unsigned group=0;group<sizeof(bursts)/sizeof(bursts[0]);++group) {
   for(unsigned i=0;i<bursts[group];++i){value(offset,215,group);offset+=215;}
   for(unsigned i=0;i<bursts[group];++i){
    if(group+1u==sizeof(bursts)/sizeof(bursts[0])&&i+1u==bursts[group])status_busy=1;
    comp_v11_ota_gatt_poll();
   }
  }
  assert(offset==64*215&&transfer.bytes_written==64*215&&get32(latest+8)==57*215);
  assert(notifications==7&&!borrowed);
  comp_v11_ota_gatt_poll();
  assert(get32(published+8)==64*215&&get32(latest+8)==64*215&&notifications==8);
  puts("WOC4_WINDOW_END_GUARANTEED durable_packets=64 latest_notified_packets=64 empty_ring_busy_retry=1 capability=53");
 }
 /* Out-of-contract peers cannot hold disconnect/host events hostage. The
  * worker aborts all queued payload before any write, then exposes ERROR. */
 start(215,64*215);unsigned before=abort_calls;for(unsigned i=0;i<=(unsigned)published[36];++i)value(i*215,215,i);
 assert(borrowed&&storage_calls==0);comp_v11_ota_gatt_poll();
 assert(!borrowed&&abort_calls==before+1&&storage_calls==0&&published[5]==DENZIC_OTA_V1_STATE_ERROR&&published[6]==DENZIC_OTA_V1_ERROR_STORAGE_WRITE);
 value(0,215,0);comp_v11_ota_gatt_poll();assert(!borrowed&&storage_calls==0);
 /* A late overflow inside physical work cannot release/reuse its pointer. */
 start(215,64*215);nested_overrun=1;value(0,215,0);comp_v11_ota_gatt_poll();assert(borrowed&&storage_calls==1);
 comp_v11_ota_gatt_poll();assert(!borrowed&&published[5]==DENZIC_OTA_V1_STATE_ERROR);
 /* Real write failures never become a full-prefix notification. */
 start(215,64*215);fail_write=5;for(unsigned i=0;i<16;++i)value(i*215,215,i);
 while(borrowed)comp_v11_ota_gatt_poll();assert(published[5]==DENZIC_OTA_V1_STATE_ERROR&&get32(published+8)==4*215);fail_write=0;
 /* Explicit fresh BEGIN has a distinct token even for exactly the same file. */
 uint32_t old=get32(published+40);start(215,64*215);assert(get32(published+40)!=old);
 value(0,215,0);comp_v11_ota_gatt_connection(false);comp_v11_ota_gatt_poll();assert(!borrowed&&!global_resumes);
 if(wire_transcript){assert(!ferror(wire_transcript));assert(fclose(wire_transcript)==0);wire_transcript=NULL;}
 puts("PASS: production GATT+DOV1 WOC5/64B/BEGIN token, explicit unknown BLK1 without a controller, committed credit before DATA ring empties, ordered-control fence, bounded notification quantum/busy retry, negotiated37/16-slot credit streams215/491 with65 packets/short tail, geometry boundaries, fail-closed overflow/nested pointer retention/write failure/disconnect, no global HCI pause. Hardware/speed NOT_RUN.");return 0;
}
