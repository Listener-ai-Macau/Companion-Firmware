#include "wba_ota_gatt.h"
#include "ble_core.h"
#include "svc_ctl.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){printf("FAIL line=%d %s\n",__LINE__,#x);return 1;}}while(0)
static SVCCTL_EvtAckStatus_t (*handler)(void *);
static uint16_t handles[4];
static unsigned added,processed,aborts,receipt_busy,nested_ready;
static bool borrowed,ble_ready;
static uint32_t now;
static union {uint64_t alignment;uint8_t bytes[10240];} arena;
/* The exact production idle predicate is compiled below. Only unrelated
 * display fields and the separate sequencer query are represented here. */
typedef struct {struct {bool running;} microphone;bool playback_active;unsigned panel;} board_t;
typedef struct {bool prepare_pending,start_pending,command_pending,capture_active,stop_pending;} runtime_t;
typedef struct {board_t *board;runtime_t runtime;} comp_v11_product_app_t;
static bool comp_ssd1681_wba_ram_write_pending(const unsigned *panel){(void)panel;return false;}
static bool comp_v11_ble_foreground_pending(void){return ble_ready;}
#define COMPANION_WBA_BLE_LINKED 1
#include "production_foreground_pending.inc"
void SVCCTL_RegisterSvcHandler(SVCCTL_EvtAckStatus_t (*f)(void *)){handler=f;}
uint8_t aci_gatt_add_service(uint8_t a,const Service_UUID_t *b,uint8_t c,uint8_t d,uint16_t *h)
{(void)a;(void)b;(void)c;(void)d;*h=1;return 0;}
uint8_t aci_gatt_add_char(uint16_t a,uint8_t b,const Char_UUID_t *c,uint16_t d,uint8_t e,uint8_t f,uint8_t g,uint8_t h,uint8_t i,uint16_t *out)
{(void)a;(void)b;(void)c;(void)d;(void)e;(void)f;(void)g;(void)h;(void)i;if(added>=4)return 1;*out=(uint16_t)(10+3*added);handles[added++]=*out;return 0;}
uint8_t aci_gatt_update_char_value(uint16_t a,uint16_t b,uint8_t c,uint8_t d,const uint8_t *e)
{(void)a;(void)c;(void)d;(void)e;if(b==handles[3]&&receipt_busy){--receipt_busy;return 1;}return 0;}
uint8_t aci_gatt_update_char_value_ext(uint16_t a,uint16_t b,uint16_t c,uint8_t d,uint16_t e,uint16_t f,uint8_t g,const uint8_t *h)
{(void)a;(void)b;(void)c;(void)d;(void)e;(void)f;(void)g;(void)h;return 0;}
static void *claim(void *c,size_t n){(void)c;if(borrowed||n>sizeof(arena.bytes))return NULL;borrowed=true;return arena.bytes;}
static void release(void *c,void *p){(void)c;if(p==arena.bytes)borrowed=false;}
static uint32_t clock_ms(void *c){(void)c;return now;}
static bool control(void *c,const uint8_t *p,size_t n)
{(void)c;if(foreground_pending(NULL))++nested_ready;if(n==20&&p[4]==4)++aborts;return true;}
static bool data(void *c,const uint8_t *p,size_t n)
{(void)c;(void)p;if(foreground_pending(NULL))++nested_ready;if(n==219)++processed;return true;}
static size_t status(void *c,uint8_t *p,size_t n)
{(void)c;if(n<24)return 0;memset(p,0,24);memcpy(p,"DOV1",4);p[4]=1;p[16]=0xf9;p[17]=1;p[18]=64;return 24;}
static void packet(unsigned kind,uint16_t offset,unsigned length)
{
    hci_uart_pckt p={0};hci_event_pckt *e=(void*)p.data;evt_blecore_aci *v=(void*)e->data;
    aci_gatt_attribute_modified_event_rp0 *a=(void*)v->data;
    e->evt=HCI_VENDOR_SPECIFIC_DEBUG_EVT_CODE;e->plen=(uint8_t)(10+length);
    v->ecode=ACI_GATT_ATTRIBUTE_MODIFIED_VSEVT_CODE;a->Attr_Handle=handles[kind]+1;
    a->Offset=offset;a->Attr_Data_Length=(uint16_t)length;memset(a->Attr_Data,0xa5,length);(void)handler(&p);
}
int main(void)
{
    comp_v11_ota_gatt_ports_t p={control,data,status,NULL,claim,release,clock_ms,NULL};
    CHECK(comp_v11_ota_gatt_init(&p));comp_v11_ota_gatt_connection(true);
    CHECK(!foreground_pending(NULL));
    packet(1,0x8000,100);CHECK(!foreground_pending(NULL));
    packet(1,100,119);CHECK(foreground_pending(NULL)==EXPECT_OTA_READY);
    comp_v11_ota_gatt_poll();CHECK(processed==1&&!borrowed&&!foreground_pending(NULL));
    for(unsigned i=0;i<16;++i)packet(1,0,219);
    for(unsigned i=0;i<16;++i){CHECK(foreground_pending(NULL)==EXPECT_OTA_READY);comp_v11_ota_gatt_poll();CHECK(processed==i+2);}
    CHECK(!foreground_pending(NULL)&&!borrowed&&!nested_ready);
    packet(1,0,219);comp_v11_ota_gatt_connection(false);CHECK(!foreground_pending(NULL)&&!borrowed);
    comp_v11_ota_gatt_connection(true);
    for(unsigned i=0;i<17;++i)packet(1,0,219);
    comp_v11_ota_gatt_connection(false);CHECK(foreground_pending(NULL)==EXPECT_OTA_READY);
    comp_v11_ota_gatt_poll();CHECK(!foreground_pending(NULL)&&!borrowed&&!nested_ready);
    uint8_t identity[56]={0};receipt_busy=1;comp_v11_ota_gatt_identity(identity);
    CHECK(!foreground_pending(NULL));comp_v11_ota_gatt_poll();CHECK(!foreground_pending(NULL));
    ble_ready=true;CHECK(foreground_pending(NULL));ble_ready=false;
    printf("queued_work_visible=%d completed_data=17 partial_spin=0 nested_spin=0 drained_spin=0 disconnected_spin=0 receipt_retry_spin=0 separate_ble_ready=1\n",EXPECT_OTA_READY);
    return 0;
}
