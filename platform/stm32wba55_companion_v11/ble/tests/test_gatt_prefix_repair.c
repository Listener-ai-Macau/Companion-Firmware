#include "companion_gatt_stm32wb.h"
#include "ble_core.h"
#include "svc_ctl.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){printf("FAIL line%d: %s\n",__LINE__,#x);return 1;}}while(0)
static uint8_t stored[512];
static unsigned calls,notifies,next_handle=0x200u;
static unsigned pre_resources,notify_resources;
void comp_v11_ble_observe_aci_resource_origin(bool notify,const uint32_t *generation)
{if(generation){if(notify)++notify_resources;else ++pre_resources;}}
static uint16_t offsets[8];
static bool write_prefix,fail_commit,fail_second;
static uint32_t *cancel_generation;
static uint16_t *cancel_progress;
uint8_t aci_gatt_add_service(uint8_t t,const Service_UUID_t *u,uint8_t p,uint8_t n,uint16_t *h)
{(void)t;(void)u;(void)p;(void)n;*h=0x100u;return BLE_STATUS_SUCCESS;}
uint8_t aci_gatt_add_char(uint16_t s,uint8_t t,const Char_UUID_t *u,uint16_t n,
    uint8_t p,uint8_t a,uint8_t e,uint8_t k,uint8_t v,uint16_t *h)
{(void)s;(void)t;(void)u;(void)n;(void)p;(void)a;(void)e;(void)k;(void)v;*h=(uint16_t)next_handle;next_handle+=3u;return BLE_STATUS_SUCCESS;}
void SVCCTL_RegisterSvcHandler(SVCCTL_EvtAckStatus_t (*f)(void *)){(void)f;}
void comp_diag_log_record_code(uint16_t c,uint8_t s,uint32_t a,uint32_t b,uint32_t d,uint32_t e)
{(void)c;(void)s;(void)a;(void)b;(void)d;(void)e;}
uint8_t aci_gatt_update_char_value(uint16_t s,uint16_t h,uint8_t o,uint8_t n,const uint8_t *p)
{(void)s;(void)h;memcpy(stored+o,p,n);++notifies;return BLE_STATUS_SUCCESS;}
uint8_t aci_gatt_update_char_value_ext(uint16_t c,uint16_t s,uint16_t h,uint8_t u,
    uint16_t n,uint16_t o,uint8_t b,const uint8_t *p)
{
    (void)s;(void)h;
    if(c!=0x0FFFu || n>509u || o+b>n || calls>=8u)return BLE_STATUS_INVALID_PARAMS;
    offsets[calls++]=o;
    if(u && fail_commit){fail_commit=false;return BLE_STATUS_INSUFFICIENT_RESOURCES;}
    if(o==480u && fail_second){fail_second=false;return BLE_STATUS_INSUFFICIENT_RESOURCES;}
    memcpy(stored+o,p,b);
    if(write_prefix && !u){write_prefix=false;memset(stored,0,32u);stored[0]=2u;stored[1]=0x21u;}
    if(u)++notifies;
    if(cancel_generation){++*cancel_generation;*cancel_progress=0u;cancel_generation=NULL;cancel_progress=NULL;}
    return BLE_STATUS_SUCCESS;
}
static void reset(void){calls=notifies=pre_resources=notify_resources=0u;memset(stored,0,sizeof(stored));memset(offsets,0,sizeof(offsets));write_prefix=fail_commit=fail_second=false;}
int main(void)
{
    CHECK(companion_gatt_stm32wb_init()==BLE_STATUS_SUCCESS);
    uint8_t packet[509];for(unsigned x=0u;x<509u;++x)packet[x]=(uint8_t)(x*23u+1u);packet[0]=1u;
    uint16_t progress=0u;uint32_t generation=1u;
    const uint16_t lengths[]={249u,470u,495u,509u};
    for(unsigned x=0u;x<4u;++x){
        reset();write_prefix=true;
        CHECK(companion_gatt_stm32wb_publish_progress(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,packet,lengths[x],&progress,&generation)==BLE_STATUS_SUCCESS);
        CHECK(progress==0u && notifies==1u && calls==(lengths[x]+239u)/240u);
        CHECK(offsets[calls-1u]==0u && !memcmp(stored,packet,lengths[x]));
    }
    reset();write_prefix=true;fail_commit=true;
    CHECK(companion_gatt_stm32wb_publish_progress(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,packet,509u,&progress,&generation)==BLE_STATUS_INSUFFICIENT_RESOURCES);
    CHECK(progress==480u && calls==3u && notifies==0u && notify_resources==1u && pre_resources==0u);
    CHECK(companion_gatt_stm32wb_publish_progress(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,packet,509u,&progress,&generation)==BLE_STATUS_SUCCESS);
    CHECK(progress==0u && calls==4u && notifies==1u && offsets[3]==0u && !memcmp(stored,packet,509u));
    reset();write_prefix=true;fail_second=true;
    CHECK(companion_gatt_stm32wb_publish_progress(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B,packet,509u,&progress,&generation)==BLE_STATUS_INSUFFICIENT_RESOURCES);
    CHECK(progress==240u && calls==2u && notifies==0u && notify_resources==0u && pre_resources==1u);
    CHECK(companion_gatt_stm32wb_publish_progress(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B,packet,509u,&progress,&generation)==BLE_STATUS_SUCCESS);
    CHECK(progress==0u && calls==4u && notifies==1u && !memcmp(stored,packet,509u));
    reset();cancel_generation=&generation;cancel_progress=&progress;
    CHECK(companion_gatt_stm32wb_publish_progress(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,packet,509u,&progress,&generation)==BLE_STATUS_INVALID_PARAMS);
    CHECK(generation==2u && progress==0u && calls==1u && notifies==0u && !pre_resources && !notify_resources);
    puts("PASS_PREFIX_REPAIR_SOFTWARE_ONLY: short_same_attribute_write_repaired final_prefix_pool_retry tail_pool_retry both_lanes generation_guard same_ACI_count; physical_cause_and_recovery_NOT_PROVEN");
    return 0;
}
