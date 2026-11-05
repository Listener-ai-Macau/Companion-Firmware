#include "wba_update_service.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define PAYLOAD_BYTES 37u
#define FAMILY UINT32_C(0x57424155)
#define BOARD UINT32_C(0x56313100)

typedef struct {
    uint8_t staging[256];
    comp_wba_update_checkpoint_t checkpoint;
    bool have_checkpoint;
    bool idle;
    bool trust;
    bool corrupt_read;
    bool fail_activation;
    uint32_t begin_calls,write_calls,abort_calls,activation_calls;
} fixture_t;

static void require(bool ok,const char *message)
{
    if(!ok){fprintf(stderr,"FAIL: %s\n",message);exit(1);}
}

static bool idle(void *context){return ((fixture_t*)context)->idle;}
static bool authorize(void *context,const comp_wba_update_manifest_t *manifest,
                      const uint8_t *auth,uint8_t auth_length)
{
    fixture_t *f=context;
    return f->trust&&manifest!=NULL&&auth_length==4u&&memcmp(auth,"SIG1",4u)==0;
}
static bool begin(void *context,uint32_t size)
{
    fixture_t *f=context;f->begin_calls++;
    if(size>sizeof(f->staging))return false;
    memset(f->staging,0xff,sizeof(f->staging));return true;
}
static bool write(void *context,uint32_t offset,const uint8_t *data,size_t length)
{
    fixture_t *f=context;f->write_calls++;
    if(offset>sizeof(f->staging)||length>sizeof(f->staging)-offset)return false;
    memcpy(f->staging+offset,data,length);return true;
}
static bool read(void *context,uint32_t offset,uint8_t *data,size_t length)
{
    fixture_t *f=context;
    if(offset>sizeof(f->staging)||length>sizeof(f->staging)-offset)return false;
    memcpy(data,f->staging+offset,length);
    if(f->corrupt_read&&offset<=12u&&12u<offset+length)data[12u-offset]^=1u;
    return true;
}
static void abort_staging(void *context){((fixture_t*)context)->abort_calls++;}
static comp_wba_update_step_result_t activate(
    void *context,const comp_wba_update_manifest_t *manifest,
    const uint8_t *authentication,uint8_t authentication_length,
    uint32_t staging_offset,uint32_t size,uint8_t *scratch,size_t scratch_bytes)
{
    fixture_t *f=context;(void)scratch;(void)scratch_bytes;
    require(authentication_length==4u&&memcmp(authentication,"SIG1",4u)==0,"activation receives authenticated envelope");
    require(staging_offset==COMP_WBA_NOR_UPDATE_STAGING_BASE,"staging offset contract");
    require(size==manifest->size_bytes,"activation size contract");
    f->activation_calls++;
    if(f->fail_activation)return COMP_WBA_UPDATE_STEP_FAILED;
    return f->activation_calls<2u?COMP_WBA_UPDATE_STEP_BUSY:COMP_WBA_UPDATE_STEP_DONE;
}
static bool cp_load(void *context,comp_wba_update_checkpoint_t *cp)
{fixture_t*f=context;if(!f->have_checkpoint)return false;*cp=f->checkpoint;return true;}
static bool cp_store(void *context,const comp_wba_update_checkpoint_t *cp)
{fixture_t*f=context;f->checkpoint=*cp;f->have_checkpoint=true;return true;}
static bool cp_clear(void *context){((fixture_t*)context)->have_checkpoint=false;return true;}

static comp_wba_update_config_t config(fixture_t *f)
{
    comp_wba_update_config_t c={0};
    c.ports=(comp_wba_update_ports_t){idle,authorize,begin,write,read,abort_staging,
                                      activate,cp_load,cp_store,cp_clear,f};
    c.target_family=FAMILY;c.board_target=BOARD;c.current_firmware_version=7u;
    c.current_ui_version=20u;c.current_app_version=7u;
    c.staging_capacity=sizeof(f->staging);c.maximum_chunk_bytes=16u;
    c.default_window_chunks=8u;return c;
}

static comp_wba_update_manifest_t manifest(uint8_t target)
{
    static const uint8_t digest[32]={
        0x53,0x76,0xea,0x8f,0xef,0x17,0xe5,0x9c,
        0xfd,0x86,0xe5,0x7c,0x74,0xe4,0x3f,0xfd,
        0x60,0x75,0xca,0x5c,0x7c,0x00,0x10,0x8e,
        0xe6,0xdd,0x9d,0x23,0xe2,0xdf,0x39,0xa0};
    comp_wba_update_manifest_t m={0};m.schema_version=1u;m.target=target;
    m.format_version=1u;m.target_family=FAMILY;m.board_target=BOARD;
    m.component_version=target==COMP_WBA_UPDATE_TARGET_FIRMWARE?8u:21u;
    m.minimum_app_version=7u;m.maximum_app_version=7u;m.size_bytes=PAYLOAD_BYTES;
    m.crc32=UINT32_C(0xfc7aa72e);memcpy(m.sha256,digest,sizeof(digest));return m;
}

static void put16(uint8_t *p,uint16_t v){p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);}
static void put32(uint8_t *p,uint32_t v){p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);p[2]=(uint8_t)(v>>16);p[3]=(uint8_t)(v>>24);}
static void control(uint8_t p[20],uint8_t op,const comp_wba_update_manifest_t *m)
{memset(p,0,20);memcpy(p,"DOV1",4);p[4]=op;p[5]=1u;if(m){put32(p+8,m->size_bytes);put16(p+12,16u);put16(p+14,8u);put32(p+16,m->crc32);}}
static size_t data_packet(uint8_t *p,uint32_t offset,const uint8_t *data,size_t length)
{put32(p,offset);memcpy(p+4,data,length);return length+4u;}

static void receive(comp_wba_update_service_t *s,const comp_wba_update_manifest_t *m,
                    const uint8_t payload[PAYLOAD_BYTES])
{
    uint8_t ctl[20],packet[20];control(ctl,DENZIC_OTA_V1_OP_BEGIN,m);
    require(comp_wba_update_control(s,ctl,sizeof(ctl)),"BEGIN accepted");
    require(comp_wba_update_data(s,packet,data_packet(packet,0u,payload,16u)),"chunk zero");
    require(comp_wba_update_data(s,packet,data_packet(packet,0u,payload,16u)),"duplicate chunk idempotent");
    require(!comp_wba_update_data(s,packet,data_packet(packet,20u,payload+20u,4u)),"gap rejected");
    require(comp_wba_update_data(s,packet,data_packet(packet,16u,payload+16u,16u)),"chunk one");
    require(comp_wba_update_data(s,packet,data_packet(packet,32u,payload+32u,5u)),"tail");
    control(ctl,DENZIC_OTA_V1_OP_FINISH,m);
    require(comp_wba_update_control(s,ctl,sizeof(ctl)),"FINISH transfer accepted");
}

static void poll_complete(comp_wba_update_service_t *s)
{
    uint8_t scratch[7];unsigned guard=0u;
    while(comp_wba_update_status(s).state!=COMP_WBA_UPDATE_COMPLETE&&
          comp_wba_update_status(s).state!=COMP_WBA_UPDATE_ERROR&&guard++<100u)
        (void)comp_wba_update_poll(s,scratch,sizeof(scratch));
    require(guard<100u,"bounded completion");
}

int main(void)
{
    uint8_t payload[PAYLOAD_BYTES];for(uint8_t i=0u;i<PAYLOAD_BYTES;++i)payload[i]=(uint8_t)(i+1u);
    fixture_t f={0};f.idle=true;f.trust=true;
    comp_wba_update_service_t s;comp_wba_update_config_t c=config(&f);
    comp_wba_update_manifest_t fw=manifest(COMP_WBA_UPDATE_TARGET_FIRMWARE);
    require(comp_wba_update_init(&s,&c),"init");
    require(comp_wba_update_open(&s,&fw,(const uint8_t*)"SIG1",4u),"trusted firmware open");
    receive(&s,&fw,payload);
    comp_wba_update_manifest_t replacement=fw;replacement.component_version=9u;
    require(!comp_wba_update_open(&s,&replacement,(const uint8_t*)"SIG1",4u)&&
            comp_wba_update_status(&s).state==COMP_WBA_UPDATE_VERIFYING,
            "verification cannot be replaced by another manifest");
    uint8_t wire_status[32];size_t wire_status_bytes=comp_wba_update_transfer_status(&s,wire_status,sizeof(wire_status));
    require(wire_status_bytes>6u&&wire_status[5]==DENZIC_OTA_V1_STATE_ERASING,
            "DOV1 does not publish COMPLETE before readback and durable activation");
    require(!comp_wba_update_status(&s).bootable,"transfer complete is not bootable");
    poll_complete(&s);
    wire_status_bytes=comp_wba_update_transfer_status(&s,wire_status,sizeof(wire_status));
    require(wire_status_bytes>6u&&wire_status[5]==DENZIC_OTA_V1_STATE_COMPLETE,
            "DOV1 COMPLETE means durable boot candidate exists");
    require(!comp_wba_update_open(&s,&replacement,(const uint8_t*)"SIG1",4u)&&
            comp_wba_update_status(&s).state==COMP_WBA_UPDATE_COMPLETE,
            "durable candidate cannot be replaced before reboot/confirmation");
    require(comp_wba_update_status(&s).bootable&&f.activation_calls==2u,"bootable only after activation target done");

    fixture_t bad={0};bad.idle=true;bad.trust=true;c=config(&bad);
    require(comp_wba_update_init(&s,&c),"bad-case init");
    comp_wba_update_manifest_t wrong=fw;wrong.board_target^=1u;
    require(!comp_wba_update_open(&s,&wrong,(const uint8_t*)"SIG1",4u)&&bad.begin_calls==0u,"wrong board rejected before erase");
    wrong=fw;wrong.component_version=7u;
    require(!comp_wba_update_open(&s,&wrong,(const uint8_t*)"SIG1",4u),"downgrade rejected");
    wrong=fw;bad.trust=false;
    require(!comp_wba_update_open(&s,&wrong,(const uint8_t*)"SIG1",4u),"untrusted manifest rejected");

    fixture_t corrupt={0};corrupt.idle=true;corrupt.trust=true;c=config(&corrupt);
    require(comp_wba_update_init(&s,&c)&&comp_wba_update_open(&s,&fw,(const uint8_t*)"SIG1",4u),"corrupt init/open");
    receive(&s,&fw,payload);corrupt.corrupt_read=true;poll_complete(&s);
    require(comp_wba_update_status(&s).state==COMP_WBA_UPDATE_ERROR&&
            comp_wba_update_status(&s).error==COMP_WBA_UPDATE_ERROR_READBACK_HASH&&corrupt.activation_calls==0u,"readback corruption never activates");

    fixture_t cut={0};cut.idle=true;cut.trust=true;c=config(&cut);
    require(comp_wba_update_init(&s,&c)&&comp_wba_update_open(&s,&fw,(const uint8_t*)"SIG1",4u),"cut init/open");
    uint8_t ctl[20],packet[20];control(ctl,DENZIC_OTA_V1_OP_BEGIN,&fw);
    require(comp_wba_update_control(&s,ctl,sizeof(ctl))&&
            comp_wba_update_data(&s,packet,data_packet(packet,0u,payload,16u)),"partial transfer before power cut");
    comp_wba_update_service_t rebooted;require(comp_wba_update_init(&rebooted,&c),"reboot mount");
    require(comp_wba_update_status(&rebooted).error==COMP_WBA_UPDATE_ERROR_INTERRUPTED&&
            cut.abort_calls==1u&&cut.activation_calls==0u,"power cut discards unverified candidate");

    fixture_t resume={0};resume.idle=true;resume.trust=true;c=config(&resume);
    require(comp_wba_update_init(&s,&c)&&comp_wba_update_open(&s,&fw,(const uint8_t*)"SIG1",4u),"verified resume init");
    receive(&s,&fw,payload);uint8_t scratch[64];
    while(comp_wba_update_status(&s).state==COMP_WBA_UPDATE_VERIFYING)
        require(comp_wba_update_poll(&s,scratch,sizeof(scratch)),"verify before cut");
    require(comp_wba_update_status(&s).state==COMP_WBA_UPDATE_VERIFIED,"verified checkpoint exists");
    resume.activation_calls=0u;require(comp_wba_update_init(&rebooted,&c),"restore verified checkpoint");
    poll_complete(&rebooted);
    require(comp_wba_update_status(&rebooted).bootable,"verified candidate reverified after reboot then activates");

    fixture_t ui={0};ui.idle=true;ui.trust=true;c=config(&ui);
    comp_wba_update_manifest_t assets=manifest(COMP_WBA_UPDATE_TARGET_UI_ASSETS);
    assets.format_version=COMP_WBA_UPDATE_UI_FORMAT_PARTITION_IMAGE_V1;
    comp_wba_update_manifest_t legacy_assets=assets;legacy_assets.format_version=COMP_WBA_UPDATE_UI_FORMAT_CUOT_V1;
    require(comp_wba_update_init(&s,&c),"asset init");
    require(!comp_wba_update_open(&s,&legacy_assets,(const uint8_t*)"SIG1",4u),"legacy CUOT blob rejected before full transfer");
    require(comp_wba_update_open(&s,&assets,(const uint8_t*)"SIG1",4u),"asset open");
    receive(&s,&assets,payload);poll_complete(&s);
    require(!comp_wba_update_status(&s).installed&&!comp_wba_update_status(&s).bootable&&comp_wba_update_status(&s).pending_reboot,"asset candidate durable but not installed before mount confirmation");

    fixture_t af={0};af.idle=true;af.trust=true;af.fail_activation=true;c=config(&af);
    require(comp_wba_update_init(&s,&c)&&comp_wba_update_open(&s,&fw,(const uint8_t*)"SIG1",4u),"activation failure open");
    receive(&s,&fw,payload);poll_complete(&s);
    require(!comp_wba_update_status(&s).bootable&&comp_wba_update_status(&s).error==COMP_WBA_UPDATE_ERROR_ACTIVATION,"activation failure remains nonbootable");
    wire_status_bytes=comp_wba_update_transfer_status(&s,wire_status,sizeof(wire_status));
    require(wire_status_bytes>6u&&wire_status[5]==DENZIC_OTA_V1_STATE_ERROR,
            "service failure overrides transport COMPLETE");

    printf("PASS_WBA_UPDATE_SERVICE power_cut_safe=1 readback_sha256=1 target_gate=1 trust_gate=1 downgrade_gate=1 dov1_complete_after_durable_candidate=1 bootable_after_activation_only=1 layout_recording_end=%08lX staging=%08lX+%08lX resource_backup=%08lX+%08lX firmware_backup=%08lX+%08lX\n",
           (unsigned long)(COMP_WBA_NOR_RECORDING_BASE+COMP_WBA_NOR_RECORDING_BYTES),
           (unsigned long)COMP_WBA_NOR_UPDATE_STAGING_BASE,(unsigned long)COMP_WBA_NOR_UPDATE_STAGING_BYTES,
           (unsigned long)COMP_WBA_NOR_RESOURCE_BACKUP_BASE,(unsigned long)COMP_WBA_NOR_RESOURCE_BACKUP_BYTES,
           (unsigned long)COMP_WBA_NOR_FIRMWARE_BACKUP_BASE,(unsigned long)COMP_WBA_NOR_FIRMWARE_BACKUP_BYTES);
    return 0;
}
