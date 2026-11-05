#include "companion_gatt_stm32wb.h"
#include "wba_ota_gatt.h"
#include "wba_update_manifest_wire.h"
#include "ble_memory_budget.h"
#include "ble_mtu.h"
#define DIVC(a,b) (((a)+(b)-1u)/(b))
#define MAX(a,b) ((a)>(b)?(a):(b))
#include "ble_bufsize.h"
#include <stdio.h>
#include <string.h>

#define CHECK(x) do {if(!(x)){printf("FAIL %d: %s\n",__LINE__,#x);return 1;}}while(0)
typedef struct {
    uint8_t uuid[16];
    uint16_t size,service;
    uint8_t properties,permissions,events,key,variable;
} declaration_t;
static declaration_t declarations[25],reference[21];
static unsigned services,attributes,chars,callbacks,bad_range;
static unsigned service_records,service_used;
static unsigned reserved_attributes;
static uint8_t long_value[509];static unsigned long_calls,long_notifies;
static bool fail_final;
static bool fail_middle;
static uint32_t *invalidate_generation;
static uint16_t *invalidate_progress;
tBleStatus reference_companion_gatt_stm32wb_init(void);

uint8_t aci_gatt_add_service(uint8_t type,const Service_UUID_t *uuid,uint8_t primary,
                           uint8_t records,uint16_t *handle)
{
    (void)uuid;(void)primary;
    if(type!=UUID_TYPE_128 || service_used>service_records)++bad_range;
    service_records=records;service_used=1u;
    reserved_attributes+=records-1u;
    *handle=(uint16_t)(0x100u+services);++services;return BLE_STATUS_SUCCESS;
}
uint8_t aci_gatt_add_char(uint16_t service,uint8_t type,const Char_UUID_t *uuid,
    uint16_t size,uint8_t properties,uint8_t permissions,uint8_t events,
    uint8_t key,uint8_t variable,uint16_t *handle)
{
    if(type!=UUID_TYPE_128 || chars>=25u)return BLE_STATUS_INVALID_PARAMS;
    unsigned count=2u+((properties&0x01u)!=0u)+((properties&0x30u)!=0u)+((properties&0x80u)!=0u);
    attributes+=count;service_used+=count;
    declaration_t *d=&declarations[chars];memset(d,0,sizeof(*d));
    memcpy(d->uuid,uuid,16u);d->size=size;d->service=service;
    d->properties=properties;d->permissions=permissions;d->events=events;
    d->key=key;d->variable=variable;
    *handle=(uint16_t)(0x200u+3u*chars);++chars;return BLE_STATUS_SUCCESS;
}
uint8_t aci_gatt_update_char_value(uint16_t service,uint16_t handle,uint8_t offset,
    uint8_t size,const uint8_t *bytes)
{(void)service;(void)handle;(void)offset;(void)size;(void)bytes;return BLE_STATUS_SUCCESS;}
void SVCCTL_RegisterSvcHandler(SVCCTL_EvtAckStatus_t (*fn)(void *))
{if(fn)++callbacks;}
void comp_diag_log_record_code(uint16_t code,uint8_t severity,uint32_t a,
    uint32_t b,uint32_t c,uint32_t d)
{(void)code;(void)severity;(void)a;(void)b;(void)c;(void)d;}
static uint8_t workspace[2048];
static void *claim(void *c,size_t n){(void)c;return n<=sizeof(workspace)?workspace:NULL;}
static void release(void *c,void *p){(void)c;(void)p;}
static uint32_t clock_ms(void *c){(void)c;return 0u;}
uint8_t aci_gatt_update_char_value_ext(uint16_t c,uint16_t s,uint16_t h,uint8_t u,
    uint16_t n,uint16_t o,uint8_t b,const uint8_t *p)
{
    (void)s;(void)h;
    if(c!=0x0FFFu||n!=509u||o+b>n)return BLE_STATUS_INVALID_PARAMS;
    ++long_calls;
    if(u && fail_final){fail_final=false;return 0x64u;}
    if(o==480u && fail_middle){fail_middle=false;return 0x64u;}
    memcpy(long_value+o,p,b);if(u)++long_notifies;
    if(invalidate_generation) {
        ++*invalidate_generation;*invalidate_progress=0u;
        invalidate_generation=NULL;invalidate_progress=NULL;
    }
    return BLE_STATUS_SUCCESS;
}
static bool accept(void *context,const uint8_t *bytes,size_t n)
{(void)context;(void)bytes;(void)n;return false;}
static size_t status(void *context,uint8_t *bytes,size_t n)
{(void)context;(void)bytes;(void)n;return 0u;}
bool comp_wba_update_open(comp_wba_update_service_t *s,const comp_wba_update_manifest_t *m,
    const uint8_t *a,uint8_t n)
{(void)s;(void)m;(void)a;(void)n;return false;}

int main(void)
{
    CHECK(reference_companion_gatt_stm32wb_init()==BLE_STATUS_SUCCESS);
    CHECK(services==10u && attributes==62u && chars==21u && callbacks==1u);
    memcpy(reference,declarations,sizeof(reference));
    services=attributes=chars=callbacks=bad_range=service_records=service_used=0u;
    reserved_attributes=0u;
    memset(declarations,0,sizeof(declarations));
    CHECK(companion_gatt_stm32wb_init()==BLE_STATUS_SUCCESS);
    for(unsigned i=0u;i<21u;++i) {
        if(i==6u||i==7u)reference[i].size=509u;
        CHECK(memcmp(&reference[i],&declarations[i],sizeof(reference[i]))==0);
    }
    comp_v11_ota_gatt_ports_t ports={accept,accept,accept,status,NULL,claim,release,clock_ms};
    CHECK(comp_v11_ota_gatt_init(&ports));
    CHECK(!bad_range && service_used<=service_records && chars==25u);
    CHECK(services+2u==COMP_V11_BLE_GATT_SERVICES);
    CHECK(attributes+9u==79u);
    CHECK(reserved_attributes+9u==COMP_V11_BLE_GATT_ATTRIBUTES);
    CHECK(callbacks==COMP_V11_BLE_SERVICE_CALLBACKS);
    uint8_t packet[509];for(unsigned i=0u;i<sizeof(packet);++i)packet[i]=(uint8_t)i;
    fail_final=true;
    CHECK(companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,packet,509u)==0x64u);
    CHECK(long_calls==3u&&!long_notifies);
    CHECK(companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,packet,509u)==BLE_STATUS_SUCCESS);
    CHECK(long_calls==6u&&long_notifies==1u&&!memcmp(packet,long_value,509u));
    uint16_t staged=0u;uint32_t generation=1u;
    long_calls=long_notifies=0u;fail_final=true;
    CHECK(companion_gatt_stm32wb_publish_progress(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,
        packet,509u,&staged,&generation)==0x64u);
    CHECK(staged==480u&&long_calls==3u&&!long_notifies);
    CHECK(companion_gatt_stm32wb_publish_progress(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,
        packet,509u,&staged,&generation)==BLE_STATUS_SUCCESS);
    CHECK(staged==0u&&long_calls==4u&&long_notifies==1u&&!memcmp(packet,long_value,509u));
    long_calls=long_notifies=0u;fail_middle=true;
    CHECK(companion_gatt_stm32wb_publish_progress(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,
        packet,509u,&staged,&generation)==0x64u);
    CHECK(staged==240u&&long_calls==2u&&!long_notifies);
    CHECK(companion_gatt_stm32wb_publish_progress(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,
        packet,509u,&staged,&generation)==BLE_STATUS_SUCCESS);
    CHECK(staged==0u&&long_calls==4u&&long_notifies==1u&&!memcmp(packet,long_value,509u));
    /* Cancel/disconnect invalidation inside ACI cannot restore stale progress
     * or send the remaining pieces after the owner changed its generation. */
    long_calls=long_notifies=0u;invalidate_generation=&generation;invalidate_progress=&staged;
    CHECK(companion_gatt_stm32wb_publish_progress(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,
        packet,509u,&staged,&generation)==BLE_STATUS_INVALID_PARAMS);
    CHECK(generation==2u&&staged==0u&&long_calls==1u&&!long_notifies);
    /* Same allocation now holds a different packet: reset owner progress and
     * stage every byte on its newly selected lane. No pointer-based shortcut. */
    for(unsigned i=0u;i<sizeof(packet);++i)packet[i]^=0x5Au;
    CHECK(companion_gatt_stm32wb_publish_progress(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B,
        packet,509u,&staged,&generation)==BLE_STATUS_SUCCESS);
    CHECK(long_calls==4u&&long_notifies==1u&&!memcmp(packet,long_value,509u));
    CHECK(companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_RECORDING_CONTROL,packet,509u)==BLE_STATUS_INVALID_PARAMS);
    _Static_assert(COMP_V11_BLE_GATT_SERVICES==13u && COMP_V11_BLE_GATT_ATTRIBUTES==80u,"full native service/attribute reservation budget");
    _Static_assert(COMP_V11_BLE_ATT_VALUE_BYTES==4692u && COMPANION_GATT_QUEUE_DEPTH==8u,"complete paired values/retain queue capacity");
    unsigned before_gatt=BLE_TOTAL_BUFFER_SIZE_GATT(100u,13u,3584u);
    unsigned after_gatt=BLE_TOTAL_BUFFER_SIZE_GATT(COMP_V11_BLE_GATT_ATTRIBUTES,
        COMP_V11_BLE_GATT_SERVICES,COMP_V11_BLE_ATT_VALUE_BYTES);
    unsigned before_host=BLE_TOTAL_BUFFER_SIZE(1u,BLE_MBLOCKS_CALC(30u,251u,1u)+16u,0u);
    unsigned after_host=BLE_TOTAL_BUFFER_SIZE(1u,
        BLE_MBLOCKS_CALC(30u,COMP_V11_BLE_ATT_MTU_MAX,1u)+16u,0u);
    CHECK(before_gatt==8208u && after_gatt==8516u && before_host==3160u && after_host==3880u);
    CHECK(after_host+after_gatt==12396u); /* complete paired values, unchanged radio buffers */
    comp_v11_ble_mtu_t mtu;
    comp_v11_ble_mtu_open(&mtu,0u);
    CHECK(mtu.mtu==23u && comp_v11_ble_mtu_value_capacity(&mtu)==20u);
    comp_v11_ble_mtu_requested(&mtu,500u,0u,false);
    CHECK(!comp_v11_ble_mtu_notifications_allowed(&mtu));
    CHECK(comp_v11_ble_mtu_agreed(&mtu,517u,COMP_V11_BLE_ATT_MTU_MAX));
    CHECK(mtu.mtu==512u && comp_v11_ble_mtu_value_capacity(&mtu)==509u);
    CHECK(comp_v11_ble_mtu_notifications_allowed(&mtu));
    comp_v11_ble_mtu_open(&mtu,0u);
    CHECK(comp_v11_ble_mtu_agreed(&mtu,251u,COMP_V11_BLE_ATT_MTU_MAX));
    CHECK(mtu.mtu==251u && comp_v11_ble_mtu_value_capacity(&mtu)==248u);
    comp_v11_ble_mtu_open(&mtu,0u);
    CHECK(comp_v11_ble_mtu_agreed(&mtu,139u,COMP_V11_BLE_ATT_MTU_MAX));
    CHECK(mtu.mtu==139u && comp_v11_ble_mtu_value_capacity(&mtu)==136u);
    puts("PASS_CE_BLE_BUDGET_SOFTWARE_ONLY: long509_final_retry_one_ACI_middle_retry_two_ACI_no_stale_generation; only3003_3004_length509_other19_bitexact, OTA4_kept, services13, attributes80_preserve_reserved_handles, callbacks2, paired_value_pool4692, queue8, host512_fits_recovered_RAM, actual_MTU_min_peer, recording_values509; physical_registration_required");
    return 0;
}
