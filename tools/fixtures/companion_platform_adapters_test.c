#include "companion_platform_adapters.h"
#include "companion_gatt_stm32wb.h"
#include "companion_product_entry_glue.h"
#include "companion_product_identity.h"
#include "companion_product_transport.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef struct { uint32_t revision; uint64_t mask; uint32_t side_effects; bool mutate; } device_fixture_t;
static bool caps(void *p,uint64_t id,uint64_t key,uint32_t *r,uint64_t *m) { device_fixture_t *f=p; (void)id;(void)key; *r=f->revision; *m=f->mask; f->side_effects++; return true; }
static bool settings(void *p,uint64_t id,uint64_t key,uint32_t *r) { device_fixture_t *f=p; (void)id;(void)key; *r=f->revision; f->side_effects++; return true; }
static bool write_settings(void *p,uint64_t id,uint64_t key,uint32_t e,uint32_t *a) { device_fixture_t *f=p; (void)id;(void)key; *a=e+1u; if (f->mutate) f->revision=*a; return true; }
static bool invoke(void *p,uint64_t id,uint64_t key,uint32_t command) { device_fixture_t *f=p; (void)id;(void)key;(void)command; f->side_effects++; return true; }
typedef struct { companion_device_control_adapter_t adapter; companion_device_control_transport_t transport; companion_settings_transport_t settings_transport; companion_meeting_transport_t meeting_transport; const void *pending_settings; const void *pending_meeting; uint32_t mutations; uint32_t settings_value; bool meeting_applied; bool fail; } product_fixture_t;
static const char *product_trace_events[16]; static uint32_t product_trace_count;
static void record_product_trace(void *p,const char *event){(void)p;if(product_trace_count<16u)product_trace_events[product_trace_count++]=event;}
static bool product_caps(void *p,uint64_t id,uint64_t key,uint32_t *r,uint64_t *m){product_fixture_t*f=p;(void)id;(void)key;*r=f->settings_transport.revision;*m=0x55u;return true;}
static bool product_read(void *p,uint64_t id,uint64_t key,uint32_t *r){product_fixture_t*f=p;(void)id;(void)key;*r=f->settings_transport.revision;return true;}
static bool product_write(void *p,uint64_t id,uint64_t key,uint32_t expected,uint32_t *ack){product_fixture_t*f=p; companion_gatt_settings_v1_t parsed; printf("trace product_write enter\\n"); if(companion_gatt_parse_settings_v1((const uint8_t *)f->pending_settings,sizeof(parsed),&parsed)!=COMPANION_GATT_PARSE_OK)return false; printf("trace product_write parsed\\n"); uint32_t normalized_value=parsed.display_brightness; f->settings_transport.fail=f->fail; bool ok=companion_settings_transport_apply(&f->settings_transport,0u,id,key,expected,&normalized_value,ack); printf("trace product_write exit=%d\\n",ok?1:0); return ok;}
static bool meeting_apply(void *p,uint64_t id){product_fixture_t*f=p;(void)id;f->meeting_applied=true;return true;}
static bool product_invoke(void *p,uint64_t id,uint64_t key,uint32_t command){product_fixture_t*f=p;(void)command;f->meeting_transport.fail=f->fail;return companion_meeting_transport_apply(&f->meeting_transport,0u,id,key,f->pending_meeting);}
static bool glue_begin_settings(void *p,uint32_t now,uint64_t id,uint64_t key,uint32_t expected,const void *payload,uint32_t *ack){product_fixture_t*f=p;(void)now;printf("trace glue begin\\n");record_product_trace(NULL,"begin");f->pending_settings=payload;bool ok=companion_device_control_write_settings(&f->adapter,id,key,expected,ack);printf("trace glue adapter=%d\\n",ok?1:0);record_product_trace(NULL,"terminal");return ok;}
static bool glue_begin_meeting(void *p,uint32_t now,uint64_t id,uint64_t key,const void *payload){product_fixture_t*f=p;(void)now;record_product_trace(NULL,"begin");f->pending_meeting=payload;bool ok=companion_device_control_invoke_command(&f->adapter,id,key,9u);record_product_trace(NULL,"terminal");return ok;}

typedef struct { uint16_t count; uint32_t offset; uint32_t stop; bool bad_crc; uint8_t mode; } diag_fixture_t;
static uint32_t crc32(const uint8_t *p, size_t n) { uint32_t c=0xffffffffu; for(size_t i=0;i<n;i++){c^=p[i];for(unsigned b=0;b<8;b++)c=(c>>1)^(0xedb88320u&(uint32_t)-(int)(c&1u));} return ~c; }
static bool dcount(void *p,uint16_t *n){*n=((diag_fixture_t*)p)->count;return true;}
static bool dstart(void *p){return ((diag_fixture_t*)p)->mode != 5u;}
static bool dread(void *p,uint32_t expected,uint8_t *out,size_t cap,size_t *len){diag_fixture_t*f=p;if(f->mode==6u)return false;uint16_t n=expected<f->count?1u:0u; if(f->mode==3u)n=0u; size_t bytes=DENZIC_OBSERVABILITY_V1_DIAG_LOG_CHUNK_HEADER_BYTES+n*DENZIC_OBSERVABILITY_V1_DIAG_LOG_EVENT_WIRE_BYTES; if(bytes>cap)return false; memset(out,0,bytes); denzic_diag_log_gatt_v1_encode_chunk_header(out,n,f->offset,0u); if(!f->bad_crc){uint8_t payload[DENZIC_OBSERVABILITY_V1_DIAG_LOG_EVENT_WIRE_BYTES]={0}; uint32_t c=crc32(payload,sizeof(payload)); denzic_diag_log_gatt_v1_encode_chunk_header(out,n,f->offset,c);} *len=bytes; if(f->mode==2u && *len>0u)*len-=1u; return true;}
static bool dstop(void *p){diag_fixture_t*f=p;f->stop++;return f->mode != 7u;}

int main(void) {
    setbuf(stdout, NULL);
    printf("fixture-start\n");
    device_fixture_t df={3u,0x55u,0u,true};
    companion_device_control_transport_t dt={&df,caps,settings,write_settings,invoke};
    companion_device_control_adapter_t da; companion_device_control_adapter_init(&da,&dt);
    uint32_t revision=0, ack=0; uint64_t mask=0;
    assert(companion_device_control_read_capabilities(&da,1u,1u,&revision,&mask));
    assert(companion_device_control_read_settings(&da,2u,2u,&revision));
    assert(companion_device_control_write_settings(&da,3u,3u,revision,&ack) && ack>=revision);
    assert(companion_device_control_invoke_command(&da,4u,4u,9u));
    printf("device-direct-ok\n");
    uint32_t effects=df.side_effects;
    printf("before-duplicate effects=%u\n", (unsigned)effects);
    bool duplicate_ok = companion_device_control_invoke_command(&da,4u,4u,9u);
    printf("after-duplicate ok=%d effects=%u\n", duplicate_ok ? 1 : 0, (unsigned)df.side_effects);
    assert(duplicate_ok);
    assert(df.side_effects==effects);
    uint32_t settings_value=0u; product_fixture_t pf={0};
    df.mutate=false;
    pf.settings_transport=(companion_settings_transport_t){&settings_value,sizeof(settings_value),revision,0u,0u,0u,false,record_product_trace,NULL};
    pf.meeting_transport=(companion_meeting_transport_t){meeting_apply,&pf,0u,0u,false,record_product_trace,NULL};
    pf.transport=(companion_device_control_transport_t){&pf,product_caps,product_read,product_write,product_invoke};
    companion_device_control_adapter_init(&pf.adapter,&pf.transport);
    companion_product_entry_glue_t glue;
    companion_product_entry_glue_init(&glue,&pf,glue_begin_settings,glue_begin_meeting);
    uint32_t product_ack=0u; bool replayed=false;
    uint8_t setting[sizeof(companion_gatt_settings_v1_t)] = {0x01u,0x01u,0x00u,0x00u,0x00u,0x00u,0x9au,0x00u,0x02u,0x86u};
    uint8_t setting2[sizeof(companion_gatt_settings_v1_t)] = {0x01u,0x04u,0x00u,0x00u,0x00u,0x00u,0x6eu,0x2au,0x13u,0xf2u};
    companion_gatt_settings_v1_t parsed_setting, parsed_setting2;
    companion_gatt_parse_result_t parse_a = companion_gatt_parse_settings_v1(setting,sizeof(setting),&parsed_setting);
    companion_gatt_parse_result_t parse_b = companion_gatt_parse_settings_v1(setting2,sizeof(setting2),&parsed_setting2);
    printf("settings-abi sizeof=%zu payload_a=%zu payload_b=%zu parse_a=%d parse_b=%d\\n",
           sizeof(companion_gatt_settings_v1_t), sizeof(setting), sizeof(setting2), parse_a, parse_b);
    assert(parse_a==COMPANION_GATT_PARSE_OK);
    assert(parse_b==COMPANION_GATT_PARSE_OK);
    companion_product_identity_t setting_identity;
    companion_product_identity_t setting2_identity;
    companion_product_identity_t meeting_identity;
    assert(companion_product_identity_derive("companion.settings",0u,setting,sizeof(setting),&setting_identity));
    printf("before-settings-entry\n");
    assert(companion_product_entry_settings(&glue,setting_identity.operation_id,setting_identity.idempotency_key,10u,1000u,
                                            revision,setting,&product_ack,
                                            &replayed));
    printf("identity-settings op=%llu key=%llu legacy=%u\n",(unsigned long long)setting_identity.operation_id,(unsigned long long)setting_identity.idempotency_key,setting_identity.legacy_fnv32);
    assert(!replayed && settings_value==parsed_setting.display_brightness && pf.settings_transport.callback_count==1u);
    assert(product_trace_count >= 5u && strcmp(product_trace_events[0],"begin")==0 && strcmp(product_trace_events[1],"callback")==0 && strcmp(product_trace_events[2],"mutation")==0 && strcmp(product_trace_events[3],"readback")==0 && strcmp(product_trace_events[4],"terminal")==0);
    printf("ordered_trace=begin>callback>mutation>readback>terminal\n");
    printf("after-settings-entry\n");
    printf("trace before duplicate product ack=%u revision=%u callbacks=%u mutations=%u\\n", product_ack, pf.settings_transport.revision, pf.settings_transport.callback_count, pf.settings_transport.mutation_count);
    assert(companion_product_entry_settings(&glue,setting_identity.operation_id,setting_identity.idempotency_key,11u,1000u,
                                            revision,setting,&product_ack,
                                            &replayed));
    printf("trace after duplicate product replay=%d ack=%u callbacks=%u mutations=%u\\n", replayed ? 1 : 0, product_ack, pf.settings_transport.callback_count, pf.settings_transport.mutation_count);
    assert(replayed && pf.settings_transport.mutation_count==1u &&
           pf.settings_transport.callback_count==1u);
    uint32_t revision2=pf.settings_transport.revision;
    assert(companion_product_identity_derive("companion.settings",0u,setting2,sizeof(setting2),&setting2_identity));
    assert(setting_identity.operation_id != setting2_identity.operation_id &&
           setting_identity.idempotency_key != setting2_identity.idempotency_key);
    assert(companion_product_entry_settings(&glue,setting2_identity.operation_id,setting2_identity.idempotency_key,12u,1000u,
                                            revision2,setting2,&product_ack,
                                            &replayed));
    printf("identity-settings2 op=%llu key=%llu legacy=%u\n",(unsigned long long)setting2_identity.operation_id,(unsigned long long)setting2_identity.idempotency_key,setting2_identity.legacy_fnv32);
    assert(!replayed && settings_value==parsed_setting2.display_brightness &&
           pf.settings_transport.mutation_count==2u && product_ack==revision2+1u &&
           pf.settings_transport.last_request_id==setting2_identity.operation_id &&
           pf.settings_transport.last_idempotency_key==setting2_identity.idempotency_key);
    uint32_t capability_revision=0u; uint64_t capability_mask=0u;
    assert(product_caps(&pf,999u,999u,&capability_revision,&capability_mask) &&
           capability_revision==pf.settings_transport.revision && capability_mask==0x55u);
    uint32_t callbacks_before_collision = pf.settings_transport.callback_count;
    printf("before-collision callbacks=%u mutations=%u\n",callbacks_before_collision,pf.settings_transport.mutation_count);
    assert(!companion_product_entry_settings(&glue,setting2_identity.operation_id,setting2_identity.idempotency_key ^ UINT64_C(1),13u,1000u,
                                             revision2,setting2,&product_ack,
                                             &replayed) && !replayed &&
           pf.settings_transport.callback_count==callbacks_before_collision &&
           pf.settings_transport.mutation_count==2u);
    printf("after-collision callbacks=%u mutations=%u\n",pf.settings_transport.callback_count,pf.settings_transport.mutation_count);
    companion_product_identity_t collision_a, collision_b;
    assert(companion_product_identity_derive("companion.settings",0u,setting,sizeof(setting),&collision_a));
    assert(companion_product_identity_derive("companion.settings",0u,setting2,sizeof(setting2),&collision_b));
    printf("legacy-collision a=%u b=%u opdiff=%d keydiff=%d\n",collision_a.legacy_fnv32,collision_b.legacy_fnv32,collision_a.operation_id!=collision_b.operation_id,collision_a.idempotency_key!=collision_b.idempotency_key);
    assert(collision_a.legacy_fnv32 == collision_b.legacy_fnv32 &&
           (collision_a.operation_id != collision_b.operation_id ||
            collision_a.idempotency_key != collision_b.idempotency_key));
    assert(companion_product_identity_derive("companion.meeting",301u,setting,sizeof(setting),&meeting_identity));
    printf("identity-meeting op=%llu key=%llu\n",(unsigned long long)meeting_identity.operation_id,(unsigned long long)meeting_identity.idempotency_key);
    assert(companion_product_entry_meeting(&glue,meeting_identity.operation_id,meeting_identity.idempotency_key,2001u,3000u,
                                           setting,&replayed));
    assert(replayed==false && pf.settings_transport.mutation_count==2u && pf.meeting_applied &&
           pf.meeting_transport.callback_count==1u);
    assert(companion_product_entry_meeting(&glue,meeting_identity.operation_id,meeting_identity.idempotency_key,2002u,3000u,
                                           setting,&replayed) && replayed &&
           pf.meeting_transport.callback_count==1u);
    pf.fail=true;
    uint32_t settings_callbacks_before_failure=pf.settings_transport.callback_count;
    assert(!companion_product_entry_settings(&glue,500u,600u,20u,1000u,
                                             pf.settings_transport.revision,setting2,&product_ack,
                                             &replayed) && !replayed &&
           pf.settings_transport.callback_count==settings_callbacks_before_failure+1u);
    assert(!companion_product_entry_settings(&glue,500u,600u,21u,1000u,
                                             pf.settings_transport.revision,&setting2,&product_ack,
                                             &replayed) && replayed &&
           pf.settings_transport.callback_count==settings_callbacks_before_failure+1u);
    assert(!companion_product_entry_meeting(&glue,700u,800u,20u,1000u,
                                            setting,&replayed) && !replayed &&
           pf.settings_transport.mutation_count==2u &&
           pf.meeting_transport.callback_count==2u &&
           pf.meeting_transport.mutation_count==1u);
    assert(!companion_product_entry_meeting(&glue,700u,800u,21u,1000u,
                                            setting,&replayed) && replayed &&
           pf.meeting_transport.callback_count==2u);
    assert(!companion_product_entry_settings(&glue,103u,203u,0xFFFFFFF0u,0x10u,
                                             revision,setting,&product_ack,
                                             &replayed));
    printf("product-glue-ok\n");
    df.mutate=true;
    companion_platform_device_control_bind(&dt);
    assert(companion_platform_device_control_capabilities_event(10u, 10u, 11u,
                                                                &revision, &mask));
    assert(companion_platform_device_control_settings_event(11u, 12u, 13u,
                                                            revision, &ack));
    assert(companion_platform_device_control_invoke_event(12u, 14u, 15u, 9u));

    diag_fixture_t good={1u,0u,0u,false,0u}; companion_diag_transport_t gt={&good,dcount,dstart,dread,dstop}; companion_diag_result_t gr;
    assert(companion_diag_log_pull(&gt,&gr) && gr.observed_events==1u && gr.stop_calls==1u);
    printf("diag positive observed=%u retained=%u dropped=%u stop=%u\n",gr.observed_events,gr.retained_events,gr.dropped_events,gr.stop_calls);
    diag_fixture_t wrong={1u,1u,0u,false,0u}; companion_diag_transport_t wt={&wrong,dcount,dstart,dread,dstop}; companion_diag_result_t wr;
    assert(!companion_diag_log_pull(&wt,&wr) && wr.offset_failures==1u && wr.stop_calls==1u);
    diag_fixture_t crc={1u,0u,0u,true,0u}; companion_diag_transport_t ct={&crc,dcount,dstart,dread,dstop}; companion_diag_result_t cr; assert(!companion_diag_log_pull(&ct,&cr)&&cr.crc_failures==1u&&cr.stop_calls==1u);
    diag_fixture_t truncated={1u,0u,0u,false,2u}; companion_diag_transport_t tt={&truncated,dcount,dstart,dread,dstop}; companion_diag_result_t tr; assert(!companion_diag_log_pull(&tt,&tr)&&tr.stop_calls==1u);
    diag_fixture_t malformed={1u,0u,0u,false,3u}; companion_diag_transport_t mt={&malformed,dcount,dstart,dread,dstop}; companion_diag_result_t mr; assert(!companion_diag_log_pull(&mt,&mr)&&mr.stop_calls==1u);
    diag_fixture_t transport={1u,0u,0u,false,6u}; companion_diag_transport_t xt={&transport,dcount,dstart,dread,dstop}; companion_diag_result_t xr; assert(!companion_diag_log_pull(&xt,&xr)&&xr.stop_calls==1u);
    diag_fixture_t overflow={COMPANION_PLATFORM_DIAG_EVENT_CAPACITY+1u,0u,0u,false,0u}; companion_diag_transport_t ot={&overflow,dcount,dstart,dread,dstop}; companion_diag_result_t or;
    assert(!companion_diag_log_pull(&ot,&or) && or.overflow && or.dropped_events==1u && or.stop_calls==1u);
    assert(!companion_diag_log_pull(NULL,&or));

    denzic_ota_orchestration_v1_blocker_inputs_t inputs={0}; inputs.battery_valid=true; inputs.battery_percent=50u; inputs.has_update_partition=true;
    companion_ota_manifest_v2_t manifest={2u,COMPANION_OTA_TARGET_STM32WB,"stm32wb_denzic_ota_v1","stm32wb_resident_bootloader_pending_verify",1u,2u};
    companion_ota_admission_result_t ar=companion_ota_manifest_v2_admit(&manifest,&inputs); assert(ar.accepted && !ar.transport_contact && !ar.apply_requested);
    manifest.target=COMPANION_OTA_TARGET_ESP; assert(!companion_ota_manifest_v2_admit(&manifest,&inputs).accepted);
    manifest.target=COMPANION_OTA_TARGET_STM32WB; manifest.rollback_strategy="esp_idf_bootloader_rollback"; assert(!companion_ota_manifest_v2_admit(&manifest,&inputs).accepted);
    printf("adapter_observer begin=%u inflight=%u terminal=%u\n",pf.adapter.begin_count,pf.adapter.inflight_count,pf.adapter.terminal_count);
    printf("device terminal_count=%u side_effects=%u duplicate_replay=1\n",da.terminal_count,df.side_effects);
    printf("ota positive accepted=%u transport_contact=%u apply=%u\n",ar.accepted,ar.transport_contact,ar.apply_requested);
    return 0;
}
