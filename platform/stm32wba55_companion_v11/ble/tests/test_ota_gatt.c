#include "wba_ota_gatt.h"
#include "ble_core.h"
#include "svc_ctl.h"
#include "wba_update_manifest_wire.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){printf("FAIL %d: %s\n",__LINE__,#x);return 1;}}while(0)
static SVCCTL_EvtAckStatus_t (*callback)(void *);
static uint16_t handles[4],lengths[4];static uint8_t props[4],perms[4],values[4][248];
static unsigned added,controls,data_count,manifests,receipt_busy;static bool authorize;
static union {uint64_t alignment;uint8_t bytes[24576];} workspace;
static bool borrowed,encoder_busy;static uint32_t now;static uint16_t data_bytes;static uint8_t received[509];
static unsigned nested_data;
static unsigned status_attempts,status_writes,status_busy,nested_status;
static uint8_t status_extra[24];
static void packet(unsigned kind,const uint8_t *bytes,uint16_t length,uint16_t offset,bool truncate);
static void *claim(void *c,size_t n) {(void)c;if(borrowed||encoder_busy||n>sizeof(workspace.bytes))return NULL;borrowed=true;return workspace.bytes;}
static void release(void *c,void *p) {(void)c;if(p==workspace.bytes)borrowed=false;}
static uint32_t clock_ms(void *c) {(void)c;return now;}
void SVCCTL_RegisterSvcHandler(SVCCTL_EvtAckStatus_t (*f)(void *)){callback=f;}
uint8_t aci_gatt_add_service(uint8_t t,const Service_UUID_t *u,uint8_t p,uint8_t n,uint16_t *h)
{(void)t;(void)p;if(u->bytes[0]!=6 || n!=9)return 1;*h=1;return 0;}
uint8_t aci_gatt_add_char(uint16_t s,uint8_t t,const Char_UUID_t *u,uint16_t n,uint8_t p,uint8_t a,uint8_t e,uint8_t k,uint8_t v,uint16_t *h)
{(void)s;(void)t;(void)u;(void)e;(void)v;if(added>=4 || k!=16)return 1;
 *h=(uint16_t)(10+2*added);handles[added]=*h;props[added]=p;perms[added]=a;lengths[added]=n;++added;return 0;}
uint8_t aci_gatt_update_char_value(uint16_t s,uint16_t h,uint8_t off,uint8_t n,const uint8_t *b)
{(void)s;if(h==handles[3] && receipt_busy){--receipt_busy;return 1;}
 if(h==handles[2]) {
    ++status_attempts;if(status_busy){--status_busy;return 1;}
    if(nested_status){nested_status=0;comp_v11_ota_gatt_connection(false);comp_v11_ota_gatt_connection(true);}
    ++status_writes;
 }
 for(unsigned i=0;i<4;++i)if(handles[i]==h && off==0 && n<=248){memcpy(values[i],b,n);lengths[i]=n;return 0;}return 1;}
static bool manifest(void *c,const uint8_t *b,size_t n) {(void)c;(void)b;++manifests;return authorize && n==144;}
static bool control(void *c,const uint8_t *b,size_t n) {(void)c;(void)b;(void)n;++controls;return true;}
static bool data(void *c,const uint8_t *b,size_t n) {
    (void)c;
    if(nested_data) {
        uint8_t next[244];unsigned action=nested_data;nested_data=0u;
        if(action==2u) {comp_v11_ota_gatt_connection(false);comp_v11_ota_gatt_connection(true);}
        /* Nested polling cannot retire the active slot twice. */
        comp_v11_ota_gatt_poll();
        memset(next,0xA7,sizeof(next));packet(1,next,244,0,false);
    }
    data_bytes=(uint16_t)n;memcpy(received,b,n);++data_count;return true;
}
static size_t status(void *c,uint8_t *b,size_t n) {
    (void)c;if(n<24)return 0;memset(b,0,24);memcpy(b,"DOV1",4);b[4]=1;
    b[5]=DENZIC_OTA_V1_STATE_IDLE;b[8]=(uint8_t)data_count;
    b[16]=COMP_V11_OTA_FILE_BYTES&0xFFu;b[17]=COMP_V11_OTA_FILE_BYTES>>8;
    b[18]=COMP_V11_OTA_WINDOW_CHUNKS;
    for(unsigned i=0;i<24u;++i)b[i]^=status_extra[i];return 24;
}
/* Only wire encoding/CRC is linked here. Signature/boot tests use the real
 * verifier in the separate update suite. */
bool comp_wba_update_open(comp_wba_update_service_t *s,const comp_wba_update_manifest_t *m,const uint8_t *a,uint8_t n)
{(void)s;(void)m;(void)a;(void)n;return false;}
static void packet(unsigned kind,const uint8_t *bytes,uint16_t length,uint16_t offset,bool truncate)
{
    hci_uart_pckt p={0};hci_event_pckt *e=(void*)p.data;evt_blecore_aci *v=(void*)e->data;
    aci_gatt_attribute_modified_event_rp0 *a=(void*)v->data;
    e->evt=HCI_VENDOR_SPECIFIC_DEBUG_EVT_CODE;e->plen=(uint8_t)(10u+length-(truncate?1u:0u));
    v->ecode=ACI_GATT_ATTRIBUTE_MODIFIED_VSEVT_CODE;a->Attr_Handle=(uint16_t)(handles[kind]+1u);
    a->Attr_Data_Length=length;a->Offset=offset;memcpy(a->Attr_Data,bytes,length);(void)callback(&p);
}
int main(void)
{
    comp_v11_ota_gatt_ports_t p={manifest,control,data,status,NULL,claim,release,clock_ms};uint8_t wire[509]={0};
    CHECK(comp_v11_ota_gatt_init(&p) && added==4 && callback);
    CHECK(props[1]==(CHAR_PROP_WRITE|CHAR_PROP_WRITE_WITHOUT_RESP) && lengths[1]==509);
    CHECK((perms[3]&(ATTR_PERMISSION_ENCRY_READ|ATTR_PERMISSION_ENCRY_WRITE))==(ATTR_PERMISSION_ENCRY_READ|ATTR_PERMISSION_ENCRY_WRITE));
    /* No OTA work:1000 foreground turns must not submit1000 identical ACI
     * commands. Changed geometry and every other wire byte remain visible. */
    comp_v11_ota_gatt_poll();unsigned before=status_writes;
    for(unsigned i=0;i<1000u;++i)comp_v11_ota_gatt_poll();
    CHECK(status_writes==before && before==1u);
    for(unsigned byte=0;byte<24u;++byte) {
        status_extra[byte]=1u;comp_v11_ota_gatt_poll();CHECK(status_writes==before+1u);
        status_extra[byte]=0u;comp_v11_ota_gatt_poll();CHECK(status_writes==before+2u);before=status_writes;
    }
    comp_v11_ota_gatt_connection(true);status_busy=1u;
    unsigned attempts=status_attempts;comp_v11_ota_gatt_poll();CHECK(status_attempts==attempts+1u && status_writes==before);
    comp_v11_ota_gatt_poll();CHECK(status_writes==before+1u);before=status_writes;
    /* A disconnect dispatched inside ACI cannot be overwritten by success
     * returned to the outer call. The next owner still republishes. */
    comp_v11_ota_gatt_connection(true);nested_status=1u;
    comp_v11_ota_gatt_poll();comp_v11_ota_gatt_poll();CHECK(status_writes==before+2u);
    before=status_writes;packet(0,wire,20,0,false);comp_v11_ota_gatt_poll();
    CHECK(status_writes==before+1u && controls==1u);controls=0u;
    comp_v11_ota_gatt_connection(false);
    packet(3,wire,144,0,false);comp_v11_ota_gatt_poll();CHECK(manifests==0);
    comp_v11_ota_gatt_connection(true);authorize=false;
    packet(3,wire,144,0,false);comp_v11_ota_gatt_poll();CHECK(manifests==1 && lengths[3]==1 && values[3][0]==0);
    authorize=true;memset(values[3],0,sizeof(values[3]));packet(3,wire,144,0,false);
    CHECK(memcmp(values[3],"WMA1",4)!=0);comp_v11_ota_gatt_poll();
    CHECK(manifests==2 && lengths[3]==8 && memcmp(values[3],"WMA1",4)==0);
    memset(values[3],0,sizeof(values[3]));receipt_busy=1u;
    packet(3,wire,144,0,false);comp_v11_ota_gatt_poll();CHECK(memcmp(values[3],"WMA1",4)!=0);
    comp_v11_ota_gatt_poll();CHECK(memcmp(values[3],"WMA1",4)==0 && manifests==3u);
    uint32_t crc=comp_wba_update_wire_crc32(wire,140);CHECK(memcmp(values[3]+4,&crc,4)==0);
    packet(1,wire,244,0,false);packet(0,wire,20,0,false);packet(1,wire,244,0,false);
    comp_v11_ota_gatt_poll();CHECK(data_count==1 && controls==0);
    comp_v11_ota_gatt_poll();CHECK(controls==1);comp_v11_ota_gatt_poll();CHECK(data_count==2);
    packet(1,wire,244,1,false);packet(1,wire,244,0,true);comp_v11_ota_gatt_poll();CHECK(data_count==2);
    packet(1,wire,244,0,false);comp_v11_ota_gatt_connection(false);comp_v11_ota_gatt_connection(true);
    comp_v11_ota_gatt_poll();CHECK(data_count==2 && lengths[3]==1);
    /* One advertised window cannot crowd out its ordered SYNC. Do not
     * publish the end-of-data receipt while that control is still queued. */
    unsigned first=data_count,control_start=controls;
    uint8_t published=values[2][8];
    for(unsigned i=0;i<COMP_V11_OTA_WINDOW_CHUNKS;++i)packet(1,wire,244,0,false);
    packet(1,wire,244,0,false); /* excess DATA is not stored */
    packet(0,wire,20,0,false); /* reserved slot accepts SYNC */
    CHECK(borrowed);
    for(unsigned i=0;i<COMP_V11_OTA_WINDOW_CHUNKS;++i) {
        comp_v11_ota_gatt_poll();CHECK(data_count==first+i+1u);
        CHECK(controls==control_start && values[2][8]==published && borrowed);
    }
    comp_v11_ota_gatt_poll();CHECK(controls==control_start+1u && !borrowed);
    CHECK(data_count==first+COMP_V11_OTA_WINDOW_CHUNKS && values[2][8]==data_count);
    for(unsigned i=0u;i<sizeof(wire);++i)wire[i]=(uint8_t)i;
    unsigned previous=data_count;
    packet(1,wire,245,0x8000u,false);comp_v11_ota_gatt_poll();CHECK(data_count==previous&&borrowed);
    packet(1,wire+245,245,0x8000u+245u,false);comp_v11_ota_gatt_poll();CHECK(data_count==previous&&borrowed);
    packet(1,wire+490,19,490,false);comp_v11_ota_gatt_poll();
    CHECK(data_count==previous+1u&&data_bytes==509u&&!memcmp(received,wire,509u)&&!borrowed);
    previous=data_count;packet(1,wire,245,0x8000u,false);packet(1,wire+245,20,246,false);
    comp_v11_ota_gatt_poll();CHECK(data_count==previous&&!borrowed);
    packet(1,wire,245,0x8000u,false);now+=1000u;comp_v11_ota_gatt_poll();CHECK(!borrowed&&data_count==previous);
    encoder_busy=true;packet(1,wire,244,0,false);comp_v11_ota_gatt_poll();CHECK(!borrowed&&data_count==previous);encoder_busy=false;
    packet(1,wire,245,0x8000u,false);comp_v11_ota_gatt_connection(false);comp_v11_ota_gatt_connection(true);
    packet(1,wire+245,20,245,false);comp_v11_ota_gatt_poll();CHECK(!borrowed&&data_count==previous);
    /* A NOR/controller callback may dispatch the next event before the
     * current data pointer has finished being consumed. Its slot and arena
     * must stay owned until the storage callback actually returns. */
    for(unsigned action=1u;action<=2u;++action) {
        previous=data_count;nested_data=action;packet(1,wire,244,0,false);comp_v11_ota_gatt_poll();
        CHECK(data_count==previous+1u && data_bytes==244u && !memcmp(received,wire,244u) && borrowed);
        comp_v11_ota_gatt_poll();CHECK(data_count==previous+2u && received[0]==0xA7u && !borrowed);
    }
    CHECK(lengths[2]==36&&!memcmp(values[2]+24,"WOC2",4));
    CHECK(values[2][32]==16 && values[2][33]==0 && values[2][34]==1 && values[2][35]==0);
    puts("PASS_WBA_OTA_GATT_HOST_ONLY: exact idle receipt suppresses1000 redundant ACI calls; every byte/geometry change, failure retry, nested disconnect, queued command, bounded16 DATA plus SYNC, durable window barrier, leased arena and secure manifest; speed/hardware NOT_RUN");return 0;
}
