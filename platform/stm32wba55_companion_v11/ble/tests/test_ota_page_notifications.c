/* Production GATT + DOV1 + real CE arena. Radio and NOR are host shims;
 * this establishes credit/durability/overrun invariants, never RF speed. */
#include "wba_ota_gatt.h"
#include "ota_page_stream.h"
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
static bool cccd,borrowed,early_receipt;static void *arena;static uint32_t now;
static uint8_t stored[2u*1024u*1024u],programmed[2u*1024u*1024u],reference[2u*1024u*1024u];
static bool page_mode,no_lookahead;
static uint32_t physical_prefix,program_operations,program_failure;
static unsigned prefetch_calls,prefetch_bytes;
static FILE *wire_transcript;
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
 if(status_busy){--status_busy;return BLE_STATUS_INSUFFICIENT_RESOURCES;}
 memcpy(published,b,n);
 if(cccd&&notify){memcpy(latest,b,n);++notifications;if(wire_transcript)assert(fwrite(b,1,n,wire_transcript)==n);}
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
static bool page_prepare(void*c,uint32_t at){(void)c;return at<expected;}
static bool page_program(void*c,uint32_t at,const uint8_t*p,size_t n)
{
 (void)c;++program_operations;
 assert(n&&n<=256u-(at&255u)&&at<=expected&&n<=expected-at);
 if(program_operations==program_failure)return false;
 for(size_t i=0;i<n;++i){assert(!programmed[at+i]);programmed[at+i]=1u;stored[at+i]=p[i];}
 return true;
}
static size_t page_following(void*c,uint32_t at,uint8_t*p,size_t n)
{
 (void)c;if(no_lookahead)return 0u;
 size_t k=comp_v11_ota_gatt_copy_following_data(at,transfer.expected_size,transfer.chunk_payload_bytes,p,n);
 if(k){++prefetch_calls;prefetch_bytes+=(unsigned)k;}return k;
}
static bool begin(void *c,uint32_t size)
{
 (void)c;storage_calls=0;
 if(page_mode){physical_prefix=program_operations=0;prefetch_calls=prefetch_bytes=0;memset(stored,0xFF,sizeof(stored));memset(programmed,0,sizeof(programmed));}
 return size==expected;
}
static bool write_data(void *c,const uint8_t *b,size_t n)
{
 (void)c;++storage_calls;comp_v11_ota_gatt_poll();
 if(get32(published+8)>transfer.bytes_written)early_receipt=true;
 if(nested_overrun){nested_overrun=0;for(unsigned i=0;i<17;++i)value((i+1)*215,215,i+1);comp_v11_ota_gatt_poll();assert(borrowed);}
 if(storage_calls==fail_write)return false;
 assert(transfer.bytes_written+n<=sizeof(stored));
 if(page_mode){const comp_ota_page_ports_t p={NULL,page_prepare,page_program,page_following};return comp_ota_page_stream_write(&p,&physical_prefix,transfer.bytes_written,b,n,expected);}
 memcpy(stored+transfer.bytes_written,b,n);return true;
}
static bool finish(void *c){(void)c;return true;}
static void abort_write(void *c){(void)c;++abort_calls;}
static bool control(void *c,const uint8_t *b,size_t n){(void)c;return denzic_ota_v1_handle_control(&transfer,b,n);}
static bool data(void *c,const uint8_t *b,size_t n){(void)c;return denzic_ota_v1_handle_data(&transfer,b,n);}
static size_t status(void *c,uint8_t *b,size_t n){(void)c;return denzic_ota_v1_encode_status(&transfer,b,n);}
static void *claim(void *c,size_t n){(void)c;assert(!borrowed&&n==8840);arena=companion_opus16_rt_workspace_borrow(n);assert(arena);borrowed=true;return arena;}
static void release(void *c,void *p){(void)c;assert(borrowed&&p==arena);companion_opus16_rt_workspace_release(p);borrowed=false;arena=NULL;}
static uint32_t clock_ms(void *c){(void)c;return now;}
static void start(unsigned payload,unsigned size)
{
 assert(!borrowed);expected=size;memset(stored,0,sizeof(stored));
 uint8_t abort[20]={'D','O','V','1',DENZIC_OTA_V1_OP_ABORT,1};packet(0,abort,20,0);comp_v11_ota_gatt_poll();
 uint8_t b[20]={'D','O','V','1',DENZIC_OTA_V1_OP_BEGIN,1};put32(b+8,size);b[12]=(uint8_t)payload;b[13]=(uint8_t)(payload>>8);b[14]=64;
 packet(0,b,20,0);comp_v11_ota_gatt_poll();assert(transfer.state==DENZIC_OTA_V1_STATE_RECEIVING);
 assert(!memcmp(published+24,"WOC5",4)&&!memcmp(published+44,"BLK1",4)&&published[48]==0&&published[34]==53&&published[36]==16&&get32(published+40)!=0);
}
int main(int argc,char **argv)
{
 if(argc==2||argc==3){
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
  * packets stay owned while the next eight refill the actual16-slot arena. */
 assert(storage_calls==8&&!early_receipt&&get32(published+8)==8*215);
 for(unsigned i=16;i<24;++i)value(i*215,215,i);
 while(borrowed)comp_v11_ota_gatt_poll();
 assert(storage_calls==24&&get32(published+8)==24*215&&!early_receipt);
 puts("WOC4_BUSY_RING committed_before_refill=8 pending_before_refill=8 refill=8 max_physical=16 local_completion_credit=0");
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
   if(admitted-retired==16){
    unsigned before=notifications;status_busy=1;
    unsigned polls=0;
    while(notifications==before&&polls<16){comp_v11_ota_gatt_poll();++polls;}
    assert(notifications>before&&polls<16&&borrowed); /* retry without whole-ring drain */
    assert(get32(latest+40)==generation);retired=get32(latest+8)/payload;
   }
   unsigned length=expected-offset;if(length>payload)length=payload;
   value(offset,length,admitted);offset+=length;++admitted;
   assert(admitted-retired<=16);
  }
  while(borrowed)comp_v11_ota_gatt_poll();assert(get32(published+8)==expected&&storage_calls==65&&!early_receipt);
  for(unsigned i=0;i<64;++i)for(unsigned j=0;j<payload;++j)assert(stored[i*payload+j]==i);
  for(unsigned j=0;j<17;++j)assert(stored[64*payload+j]==64);
  assert(notifications>=8&&notifications<=10);assert(comp_v11_ota_gatt_timing()->peak_queue==16);
  uint8_t done[20]={'D','O','V','1',DENZIC_OTA_V1_OP_FINISH,1};packet(0,done,20,0);comp_v11_ota_gatt_poll();assert(published[5]==DENZIC_OTA_V1_STATE_COMPLETE);
 }
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
 start(215,64*215);unsigned before=abort_calls;for(unsigned i=0;i<17;++i)value(i*215,215,i);
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

 /* Same production GATT/core writer plus the production page stream. The
  * immutable next DATA remains pinned, no prewritten future byte is ACKed. */
 page_mode=true;comp_v11_ota_gatt_connection(true);
 start(466,932);value(0,466,0x31);value(466,466,0x62);
 comp_v11_ota_gatt_poll();assert(transfer.bytes_written==466&&physical_prefix==512&&get32(published+8)<=466);
 for(unsigned i=0;i<512;++i)assert(programmed[i]&&stored[i]==(i<466?0x31:0x62));
 comp_v11_ota_gatt_poll();assert(transfer.bytes_written==932&&physical_prefix==932&&!borrowed&&program_operations==4);
 /* A SYNC fence prevents lookahead, including though later DATA is present. */
 start(466,932);value(0,466,0x31);
 uint8_t sync[20]={'D','O','V','1',DENZIC_OTA_V1_OP_SYNC,1};packet(0,sync,20,0);value(466,466,0x62);
 comp_v11_ota_gatt_poll();assert(physical_prefix==466&&!programmed[466]&&prefetch_bytes==0);
 while(borrowed)comp_v11_ota_gatt_poll();assert(transfer.bytes_written==932);
 /* An invalid following offset must never prewrite its payload. */
 start(466,932);value(0,466,0x31);value(467,465,0x62);comp_v11_ota_gatt_poll();
 assert(physical_prefix==466&&!programmed[466]);while(borrowed)comp_v11_ota_gatt_poll();assert(transfer.bytes_written==466);
 /* A physical failure after one page cannot acknowledge the current value. */
 start(466,932);program_failure=2;value(0,466,0x31);value(466,466,0x62);comp_v11_ota_gatt_poll();
 assert(transfer.bytes_written==0&&physical_prefix==256&&published[5]==DENZIC_OTA_V1_STATE_ERROR&&get32(published+8)==0);
 while(borrowed)comp_v11_ota_gatt_poll();program_failure=0;
 /* After retry/reset, the owner's new erase clears all prewritten state. */
 start(466,932);assert(physical_prefix==0&&!programmed[0]);
 value(0,466,0x31);value(466,466,0x62);while(borrowed)comp_v11_ota_gatt_poll();assert(transfer.bytes_written==932);
 if(argc==3){
  FILE *image=NULL;
#ifdef _MSC_VER
  assert(fopen_s(&image,argv[2],"rb")==0);
#else
  image=fopen(argv[2],"rb");
#endif
  assert(image);size_t bytes=fread(reference,1,sizeof(reference),image);assert(!ferror(image)&&feof(image)&&bytes>0&&bytes<sizeof(reference));assert(fclose(image)==0);
  for(unsigned mode=0;mode<2;++mode){
   no_lookahead=mode!=0;start(466,(unsigned)bytes);uint32_t submitted=0;
   while(submitted<bytes&&submitted<16u*466u){unsigned k=(unsigned)(bytes-submitted);if(k>466)k=466;
    uint8_t b[509];put32(b,submitted);memcpy(b+4,reference+submitted,k);
    for(unsigned off=0;off<k+4u;){unsigned n=k+4u-off;if(n>245)n=245;packet(1,b+off,n,off+n<k+4u?off|0x8000u:off);off+=n;}submitted+=k;}
   while(borrowed){
    uint32_t packet_before=transfer.bytes_written;comp_v11_ota_gatt_poll();assert(transfer.bytes_written>=packet_before&&get32(published+8)<=transfer.bytes_written);
    assert(!memcmp(stored,reference,transfer.bytes_written));
    if(submitted<bytes){unsigned k=(unsigned)(bytes-submitted);if(k>466)k=466;
     uint8_t b[509];put32(b,submitted);memcpy(b+4,reference+submitted,k);
     for(unsigned off=0;off<k+4u;){unsigned n=k+4u-off;if(n>245)n=245;packet(1,b+off,n,off+n<k+4u?off|0x8000u:off);off+=n;}submitted+=k;}
   }
   assert(transfer.bytes_written==bytes&&physical_prefix==bytes&&!memcmp(stored,reference,bytes));
   printf("PAGE_STREAM file_bytes=%u lookahead=%u physical_programs=%u prefetch_calls=%u prefetch_bytes=%u ack=%u\n",(unsigned)bytes,(unsigned)!no_lookahead,(unsigned)program_operations,prefetch_calls,prefetch_bytes,(unsigned)transfer.bytes_written);
   if(!no_lookahead)assert(program_operations==(bytes+255u)/256u);
   else assert(program_operations>(bytes+255u)/256u);
  }
 }
 if(wire_transcript){assert(!ferror(wire_transcript));assert(fclose(wire_transcript)==0);wire_transcript=NULL;}
 puts("PASS: production page-stream same-page prewrite/pinned-next/no-early-ACK/no-double-byte-program/control-fence/wrong-offset/write-failure/fresh-owner plus production GATT+DOV1 WOC5/64B/BEGIN token, explicit unknown BLK1 without a controller, committed credit before DATA ring empties, ordered-control fence, bounded notification quantum/busy retry, true16-slot credit streams215/491 with65 packets/short tail, fail-closed overflow/nested pointer retention/write failure/disconnect, no global HCI pause. Hardware/speed NOT_RUN.");return 0;
}
