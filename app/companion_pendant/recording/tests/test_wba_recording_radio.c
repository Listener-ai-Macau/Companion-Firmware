#include "../wba_recording_radio.h"
#define COMP_BOOT_TEST_MAIN radio_recovery_fixture_main
#include "test_wba_recording_recovery.c"
/* Exercise the real companion_link dispatcher, retaining its existing
 * runtime command model. Its V1 cases are affected by this shared edit. */
#define COMP_LINK_TEST_MAIN radio_legacy_link_fixture_main
#define f radio_legacy_fixture_arg
#include "../../runtime/tests/test_companion_link.c"
#undef f

static fixture_t link_owner;
#define radio (link_owner.link.io.segmented_state)
static uint8_t saved[32768],last_reply[509],retry[509];
static uint16_t last_reply_bytes,retry_bytes;
static companion_gatt_char_id_t last_reply_char,retry_char;
static uint32_t saved_bytes,receipt_count;
static unsigned directory_pages;
static uint64_t directory_starts;
static unsigned blocked, unsubscribed_consume_publish;
static uint16_t test_value_capacity=136u;
static bool radio_publish(void *v,companion_gatt_char_id_t id,const uint8_t *p,uint16_t n)
{
    (void)v;
    if(id!=COMPANION_GATT_CHAR_RECORDING_CONTROL&&id!=COMPANION_GATT_CHAR_RECORDING_LIST&&
       id!=COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL&&id!=COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B&&
       id!=COMPANION_GATT_CHAR_DELETE_PRIVACY)return true;
    assert(n<=test_value_capacity); /* same actual ATT value capacity as radio initialization */
    if(id==COMPANION_GATT_CHAR_RECORDING_LIST)assert(n<=248u); /* directory GATT attribute, unlike the audio lanes */
    if(id==COMPANION_GATT_CHAR_DELETE_PRIVACY && !link_owner.link.subscribed[id]) {
        ++unsubscribed_consume_publish; return true; /* modeled ACI acceptance without a subscriber */
    }
    if(blocked){blocked--;memcpy(retry,p,n);retry_bytes=n;retry_char=id;return false;}
    if(retry_bytes){assert(id==retry_char&&n==retry_bytes&&!memcmp(retry,p,n));retry_bytes=0u;}
    if(id==COMPANION_GATT_CHAR_RECORDING_LIST&&n>=24u&&p[0]==2u){directory_pages++;assert(comp_rec_get32(p+8u)<64u);directory_starts|=UINT64_C(1)<<comp_rec_get32(p+8u);}
    if(id==COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL||id==COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B) {
        assert(n>=20u&&p[0]==1u);bool final=(p[1]&1u)!=0u;
        bool live=radio.config.transfer->snapshot_live;
        uint32_t header=live?24u:(final?56u:20u),bytes=(uint32_t)p[2]|((uint32_t)p[3]<<8u);
        if(live) {
            assert(!final&&p[1]==0u&&comp_rec_get32(p+16u)==radio.io.selected.descriptor.encoded_length);
            uint8_t fields[16];memcpy(fields,p+4u,16u);
            assert(comp_rec_get32(p+20u)==~comp_rec_crc_step(comp_rec_crc_step(UINT32_MAX,fields,16u),p+header,bytes));
        }
        assert(n==header+bytes&&comp_rec_get32(p+12u)==saved_bytes);
        assert(saved_bytes+bytes<=sizeof(saved));memcpy(saved+saved_bytes,p+header,bytes);saved_bytes+=bytes;
    } else {
        memcpy(last_reply,p,n);last_reply_bytes=n;last_reply_char=id;
        if(id==COMPANION_GATT_CHAR_DELETE_PRIVACY&&n==84u)receipt_count++;
    }
    return true;
}
static void radio_tick(void)
{
    unsigned reads=f.reads,writes=f.writes;
    link_owner.runtime.capture_active=mic;
    comp_link_poll(&link_owner.link,f.now);
    assert(f.reads-reads<=1u&&f.writes==writes); /* application alone owns writes */
}
static void send(companion_gatt_char_id_t id,const uint8_t *p,uint16_t n)
{
    companion_gatt_event_t event={0};event_write(&event,id,p,n);comp_link_event(&link_owner.link,&event,f.now);
}
static void subscribe(companion_gatt_char_id_t id,bool enabled)
{
    companion_gatt_event_t event={0};event_notify(&event,enabled?COMPANION_GATT_EVENT_NOTIFY_ENABLED:
        COMPANION_GATT_EVENT_NOTIFY_DISABLED,id);comp_link_event(&link_owner.link,&event,f.now);
}
static void negotiation(uint8_t p[32])
{
    memset(p,0,32u);p[0]=2u;p[1]=0x22u;comp_rec_put32(p+4u,91u);
    memcpy(p+8u,device_uid,12u);comp_rec_put64(p+20u,7u);
    comp_rec_put32(p+28u,comp_rec_crc(p,28u));
}
static void connect_peer(void)
{
    comp_link_connection(&link_owner.link,true,true,f.now);
    subscribe(COMPANION_GATT_CHAR_RECORDING_CONTROL,true);subscribe(COMPANION_GATT_CHAR_RECORDING_LIST,true);
    subscribe(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,true);subscribe(COMPANION_GATT_CHAR_DELETE_PRIVACY,true);
    uint8_t p[32];negotiation(p);send(COMPANION_GATT_CHAR_RECORDING_CONTROL,p,32u);radio_tick();assert(radio.negotiated);
}
static comp_segment_entry_t setup_radio(void)
{
    init();puts("radio setup: NOR/catalog initialized");
    comp_wba_pipeline_config_t cfg=pipeline.config;cfg.segment_frames=20u;
    assert(comp_wba_recording_pipeline_init(&pipeline,&cfg));ready(55u);
    puts("radio setup: initial extent prepared");
    assert(comp_wba_recording_pipeline_start(&pipeline,91u));
    puts("radio setup: capture started");
    for(unsigned block=0u;block<36u;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_cont_recording_pcm(&engine,samples,160u));
        for(unsigned i=0u;i<160u;i++)poll();
    }
    assert(comp_wba_recording_pipeline_stop(&pipeline,91u));
    for(unsigned i=0u;i<10000u&&pipeline.state!=COMP_PIPE_FINISHED;i++)poll();
    assert(pipeline.state==COMP_PIPE_FINISHED);
    puts("radio setup: original capture sealed");
    comp_segment_entry_t original=recovered_entry();assert(original.descriptor.encoded_length==768u);
    memset(&link_owner,0,sizeof(link_owner));memset(&radio,0,sizeof(radio));
    memset(saved,0,sizeof(saved));saved_bytes=receipt_count=blocked=unsubscribed_consume_publish=0u;last_reply_bytes=retry_bytes=0u;
    comp_link_config_t link={&link_owner.runtime,NULL,NULL,&link_owner.features,radio_publish,NULL};
    assert(comp_link_init_segmented(&link_owner.link,&link,&radio,&pipeline,20u));
    puts("radio setup: segmented product link initialized");
    return original;
}
static void calendar_directory_attribute_budget(void)
{
    (void)setup_radio();ready(56u);
    assert(comp_wba_recording_pipeline_start(&pipeline,91u));
    for(unsigned block=0u;block<36u;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_cont_recording_pcm(&engine,samples,160u));
        for(unsigned i=0u;i<160u;i++)poll();
    }
    assert(comp_wba_recording_pipeline_stop(&pipeline,91u));
    for(unsigned i=0u;i<10000u&&pipeline.state!=COMP_PIPE_FINISHED;i++)poll();
    assert(pipeline.state==COMP_PIPE_FINISHED);test_value_capacity=509u;
    assert(comp_wba_recording_radio_set_value_capacity(&radio,509u));connect_peer();
    for(unsigned calendar=0u;calendar<2u;calendar++) {
        uint8_t request[16]={2u,0x20u};request[2]=(uint8_t)calendar;comp_rec_put32(request+8u,71u+calendar);
        last_reply_char=COMPANION_GATT_CHAR_MEETING_STATUS;
        send(COMPANION_GATT_CHAR_RECORDING_CONTROL,request,16u);
        for(unsigned i=0u;i<100u&&last_reply_char!=COMPANION_GATT_CHAR_RECORDING_LIST;i++)radio_tick();
        assert(last_reply_char==COMPANION_GATT_CHAR_RECORDING_LIST&&!comp_wba_recording_radio_busy(&radio));
        assert(last_reply[1]==(calendar?1u:2u)&&last_reply_bytes==(calendar?140u:248u));
        assert(last_reply[2]==(calendar?116u:112u)&&last_reply[3]==0u);
    }
    test_value_capacity=136u;
    test_value_capacity=509u;directory_pages=0u;directory_starts=0u;
    uint8_t stream[16]={2u,0x20u,3u,0u};comp_rec_put32(stream+8u,83u);
    blocked=2u;send(COMPANION_GATT_CHAR_RECORDING_CONTROL,stream,16u);
    for(unsigned i=0u;i<1000u&&comp_wba_recording_radio_busy(&radio);i++)radio_tick();
    assert(!comp_wba_recording_radio_busy(&radio)&&directory_pages==2u&&directory_starts==3u&&!retry_bytes);
    directory_pages=0u;directory_starts=0u;send(COMPANION_GATT_CHAR_RECORDING_CONTROL,stream,16u);
    for(unsigned i=0u;i<1000u&&!directory_pages;i++)radio_tick();assert(directory_pages==1u);
    subscribe(COMPANION_GATT_CHAR_RECORDING_LIST,false);
    for(unsigned i=0u;i<10u;i++)radio_tick();assert(directory_pages==1u&&!comp_wba_recording_radio_busy(&radio));
    subscribe(COMPANION_GATT_CHAR_RECORDING_LIST,true);directory_pages=0u;
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,stream,16u);for(unsigned i=0u;i<1000u&&!directory_pages;i++)radio_tick();assert(directory_pages==1u);
    catalog.generation++;
    for(unsigned i=0u;i<100u&&comp_wba_recording_radio_busy(&radio);i++)radio_tick();
    assert(directory_pages==1u&&last_reply_bytes==16u&&!memcmp(last_reply,"CRE2",4u)&&comp_rec_get32(last_reply+12u)==COMP_SEG_STALE_SNAPSHOT);
    test_value_capacity=136u;
    puts("PASS_CALENDAR_DIRECTORY_WITHIN_EXISTING_248_BYTE_GATT_ATTRIBUTE");
}
static void sealed_request(const comp_segment_entry_t *e,uint32_t offset,uint8_t p[32])
{
    memset(p,0,32u);p[0]=2u;p[1]=0x21u;p[2]=4u;comp_rec_put32(p+4u,e->descriptor.recording_id);
    comp_rec_put64(p+8u,7u);comp_rec_put64(p+16u,e->descriptor.session_id);
    comp_rec_put32(p+24u,e->descriptor.segment_index);comp_rec_put32(p+28u,offset);
}
static void consumption_proof(const comp_segment_entry_t *e,uint8_t p[84])
{
    const comp_rec_v2_descriptor_t *d=&e->descriptor;memset(p,0,84u);memcpy(p,"CRA2",4u);
    comp_rec_put16(p+4u,2u);comp_rec_put16(p+6u,84u);memcpy(p+8u,d->device_uid,12u);
    comp_rec_put64(p+20u,d->format_epoch);comp_rec_put64(p+28u,d->session_id);
    comp_rec_put32(p+36u,d->segment_index);comp_rec_put32(p+40u,d->recording_id);
    comp_rec_put32(p+44u,d->encoded_length);memcpy(p+48u,d->sha256,32u);
    comp_rec_put32(p+80u,comp_rec_crc(p,80u));
}
static void dispatch_security_and_reconnect(void)
{
    puts("radio stage: setup real Opus sealed sample");
    comp_segment_entry_t original=setup_radio();uint8_t p[32];negotiation(p);
    unsigned before=f.writes;uint32_t rejected=link_owner.link.rejected_writes;
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,p,32u);
    assert(link_owner.link.rejected_writes==rejected+1u&&!radio.negotiated&&f.writes==before);
    comp_link_connection(&link_owner.link,true,true,f.now);subscribe(COMPANION_GATT_CHAR_RECORDING_CONTROL,true);
    rejected=link_owner.link.rejected_writes;send(COMPANION_GATT_CHAR_RECORDING_CONTROL,p,32u);
    assert(link_owner.link.rejected_writes==rejected+1u&&!radio.negotiated&&f.writes==before);
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));
    blocked=1u;send(COMPANION_GATT_CHAR_RECORDING_CONTROL,p,32u);
    assert(!comp_wba_recording_radio_set_value_capacity(&radio,248u));
    radio_tick();assert(!radio.negotiated);
    radio_tick();assert(radio.negotiated&&last_reply_bytes==32u&&!memcmp(p,last_reply,32u));
    puts("radio stage: protected negotiation complete");
    comp_link_connection(&link_owner.link,true,true,f.now);
    assert(radio.negotiated); /* duplicate encryption event must not retire the peer */
    subscribe(COMPANION_GATT_CHAR_RECORDING_LIST,true);subscribe(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,true);
    subscribe(COMPANION_GATT_CHAR_DELETE_PRIVACY,true);
    uint8_t directory[16]={2u,0x20u};comp_rec_put32(directory+8u,71u);
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,directory,16u);
    for(unsigned i=0u;i<100u&&last_reply_char!=COMPANION_GATT_CHAR_RECORDING_LIST;i++)radio_tick();
    assert(last_reply_bytes==136u&&last_reply[0]==2u&&comp_rec_get32(last_reply+16u)==71u);
    comp_rec_v2_descriptor_t listed;assert(comp_rec_v2_decode(last_reply+24u,112u,&listed));
    assert(listed.session_id==55u&&listed.recording_id==original.descriptor.recording_id);
    puts("radio stage: directory complete");
    uint8_t expected[768];
    for(unsigned at=0u;at<sizeof(expected);at++)expected[at]=f.bytes[DATA_BASE+original.extent_offset+256u+(at/248u)*256u+at%248u];
    ready(56u);assert(comp_wba_recording_pipeline_start(&pipeline,91u)&&mic);
    sealed_request(&original,0u,p);blocked=1u;send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,p,32u);
    for(unsigned i=0u;i<2000u&&saved_bytes==0u;i++){poll();radio_tick();}
    assert(saved_bytes==116u&&mic&&engine.stats.microphone_starts==1u);
    puts("radio stage: first sealed window during capture");
    comp_link_connection(&link_owner.link,false,false,f.now);
    assert(mic&&!radio.negotiated&&saved_bytes==116u);
    connect_peer();sealed_request(&original,saved_bytes,p);send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,p,32u);
    for(unsigned i=0u;i<3000u&&saved_bytes<sizeof(expected);i++){poll();radio_tick();}
    assert(saved_bytes==sizeof(expected)&&!memcmp(saved,expected,sizeof(expected))&&mic);
    puts("radio stage: resumed sealed upload complete");
    radio_tick(); /* terminal transfer becomes idle for exact consume */
    uint8_t proof[84];consumption_proof(&original,proof);before=f.erases;
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,proof,84u);assert(radio.consume_pending&&f.erases==before);
    comp_link_connection(&link_owner.link,false,false,f.now);assert(mic);
    for(unsigned i=0u;i<10000u&&comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_PENDING;i++)poll();
    assert(comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_OK&&mic&&receipt_count==0u);
    puts("radio stage: accepted physical consume completed offline");
    connect_peer();for(unsigned i=0u;i<8u&&receipt_count==0u;i++)radio_tick();
    assert(receipt_count==1u&&last_reply_bytes==84u&&!memcmp(last_reply,proof,84u));
    before=f.erases;send(COMPANION_GATT_CHAR_DELETE_PRIVACY,proof,84u);
    for(unsigned i=0u;i<8u&&receipt_count<2u;i++)radio_tick();
    assert(receipt_count==2u&&f.erases==before&&mic);
    uint8_t wrong[84];memcpy(wrong,proof,84u);wrong[48]^=1u;comp_rec_put32(wrong+80u,comp_rec_crc(wrong,80u));
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,wrong,84u);
    for(unsigned i=0u;i<1000u&&radio.consume_pending;i++){poll();radio_tick();}
    radio_tick();assert(receipt_count==2u&&f.erases==before&&mic&&!memcmp(last_reply,"CAE2",4u));
    /* A retired selected proof shares RAM with the directory worker. Its
     * descriptor/hash bytes can alias an active=true byte. No live owner
     * may survive this switch; don't mistake those bytes for a busy worker. */
    radio.io.directory.active=true;
    comp_rec_put32(directory+8u,72u);last_reply_char=COMPANION_GATT_CHAR_MEETING_STATUS;
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,directory,16u);
    for(unsigned i=0u;i<100u&&last_reply_char!=COMPANION_GATT_CHAR_RECORDING_LIST;i++)radio_tick();
    assert(last_reply_bytes==24u&&last_reply[0]==2u&&comp_rec_get32(last_reply+16u)==72u&&mic&&f.erases==before);
    subscribe(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,false);assert(radio.negotiated&&mic);
    rejected=link_owner.link.rejected_writes;sealed_request(&original,0u,p);
    send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,p,32u);assert(link_owner.link.rejected_writes==rejected+1u&&mic);
    assert(comp_wba_recording_pipeline_stop(&pipeline,91u));
    for(unsigned i=0u;i<10000u&&pipeline.state!=COMP_PIPE_FINISHED;i++)poll();
    assert(pipeline.state==COMP_PIPE_FINISHED&&!mic);
    puts("PASS V2 production dispatcher/radio model: protected negotiation, immutable backpressure,136B directory, real Opus sealed upload during independent capture, verified-offset reconnect, accepted consume completes offline and exact receipt replay, wrong proof/CCCD refuses without MIC stop; SOFTWARE ONLY");
}

static void disconnected_invalid_consume(bool missing)
{
    comp_segment_entry_t original=setup_radio();
    uint8_t proof[84],wrong[84],before[4096];
    consumption_proof(&original,proof);memcpy(wrong,proof,sizeof(wrong));
    if(missing)comp_rec_put32(wrong+40u,original.descriptor.recording_id+1u);
    else wrong[48]^=1u;
    comp_rec_put32(wrong+80u,comp_rec_crc(wrong,80u));
    memcpy(before,f.bytes+DATA_BASE+original.extent_offset,sizeof(before));
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    unsigned writes=f.writes,erases=f.erases;
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,wrong,sizeof(wrong));
    assert(radio.consume_pending);
    comp_link_connection(&link_owner.link,false,false,f.now);
    radio_tick();assert(radio.consume_pending); /* A live transaction remains owned. */
    for(unsigned i=0u;i<10000u&&comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_PENDING;i++) {
        poll();radio_tick();
    }
    assert(comp_wba_recording_pipeline_consume_result(&pipeline)==(missing?COMP_SEG_NOT_FOUND:COMP_SEG_BAD_ARGUMENT));
    assert(pipeline.state!=COMP_PIPE_FAILED);
    radio_tick();
    assert(!radio.consume_pending&&!comp_wba_recording_radio_busy(&radio));
    assert(!memcmp(before,f.bytes+DATA_BASE+original.extent_offset,sizeof(before)));
    assert(writes==f.writes&&erases==f.erases&&receipt_count==0u);
    connect_peer();
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,proof,sizeof(proof));
    for(unsigned i=0u;i<10000u&&(radio.consume_pending||radio.phase!=0u);i++){poll();radio_tick();}
    assert(receipt_count==1u&&last_reply_bytes==84u&&!memcmp(last_reply,proof,84u));
    puts("PASS_DISCONNECTED_INVALID_CONSUME_RELEASES_WITH_ORIGINAL_PRESERVED_AND_VALID_RETRY; SOFTWARE ONLY");
}

static void disconnected_completed_consume(void)
{
    comp_segment_entry_t original=setup_radio();uint8_t proof[84];
    consumption_proof(&original,proof);
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,proof,sizeof(proof));
    assert(radio.consume_pending);
    comp_link_connection(&link_owner.link,false,false,f.now);
    for(unsigned i=0u;i<10000u&&comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_PENDING;i++){
        poll();radio_tick();
    }
    assert(comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_OK);
    radio_tick();
    assert(!radio.consume_pending&&!comp_wba_recording_radio_busy(&radio)&&receipt_count==0u);
    /* The next recording may start offline while the exact receipt is retained. */
    ready(56u);assert(comp_wba_recording_pipeline_start(&pipeline,91u)&&mic);
    connect_peer();for(unsigned i=0u;i<8u&&receipt_count==0u;i++)radio_tick();
    assert(receipt_count==1u&&last_reply_bytes==84u&&!memcmp(last_reply,proof,84u)&&mic);
    assert(comp_wba_recording_pipeline_stop(&pipeline,91u));
    for(unsigned i=0u;i<10000u&&pipeline.state!=COMP_PIPE_FINISHED;i++)poll();
    assert(pipeline.state==COMP_PIPE_FINISHED&&!mic);
    puts("PASS_DISCONNECTED_COMPLETED_CONSUME_RELEASES_OFFLINE_START_AND_REPLAYS_EXACT_RECEIPT; SOFTWARE ONLY");
}

static void deferred_receipt_without_subscription(void)
{
    comp_segment_entry_t original=setup_radio();uint8_t proof[84],p[32];
    consumption_proof(&original,proof);
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,proof,sizeof(proof));assert(radio.consume_pending);
    comp_link_connection(&link_owner.link,false,false,f.now);
    for(unsigned i=0u;i<10000u&&comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_PENDING;i++){poll();radio_tick();}
    assert(comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_OK);radio_tick();
    assert(radio.consume_replay&&!radio.consume_pending);
    comp_link_connection(&link_owner.link,true,true,f.now);
    subscribe(COMPANION_GATT_CHAR_RECORDING_CONTROL,true);
    subscribe(COMPANION_GATT_CHAR_RECORDING_LIST,true);
    negotiation(p);send(COMPANION_GATT_CHAR_RECORDING_CONTROL,p,32u);radio_tick();assert(radio.negotiated);
    for(unsigned i=0u;i<8u;i++)radio_tick();
    assert(unsubscribed_consume_publish==0u && !comp_wba_recording_radio_busy(&radio));
    /* Other subscribed operations remain usable while the receipt is deferred. */
    uint8_t directory[16]={2u,0x20u};comp_rec_put32(directory+8u,72u);
    last_reply_char=COMPANION_GATT_CHAR_MEETING_STATUS;
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,directory,16u);
    for(unsigned i=0u;i<100u&&last_reply_char!=COMPANION_GATT_CHAR_RECORDING_LIST;i++)radio_tick();
    assert(last_reply_char==COMPANION_GATT_CHAR_RECORDING_LIST && !comp_wba_recording_radio_busy(&radio));
    subscribe(COMPANION_GATT_CHAR_DELETE_PRIVACY,true);
    for(unsigned i=0u;i<8u&&receipt_count==0u;i++)radio_tick();
    assert(receipt_count==1u&&last_reply_bytes==84u&&!memcmp(last_reply,proof,84u));
    puts("PASS_DEFER_RECEIPT_UNTIL_SUBSCRIBED_WITHOUT_BLOCKING; SOFTWARE ONLY");
}

static void unsubscribe_while_consuming(void)
{
    comp_segment_entry_t original=setup_radio();uint8_t proof[84];
    consumption_proof(&original,proof);
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,proof,sizeof(proof));assert(radio.consume_pending);
    subscribe(COMPANION_GATT_CHAR_DELETE_PRIVACY,false);
    for(unsigned i=0u;i<10000u&&comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_PENDING;i++){poll();radio_tick();}
    assert(comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_OK);radio_tick();
    assert(unsubscribed_consume_publish==0u&&radio.consume_replay&&!comp_wba_recording_radio_busy(&radio));
    subscribe(COMPANION_GATT_CHAR_DELETE_PRIVACY,true);
    for(unsigned i=0u;i<8u&&receipt_count==0u;i++)radio_tick();
    assert(receipt_count==1u&&last_reply_bytes==84u&&!memcmp(last_reply,proof,84u));
    puts("PASS_UNSUBSCRIBE_DURING_CONSUME_RELEASES_AND_REPLAYS; SOFTWARE ONLY");
}
static void disconnect_after_receipt_prepared(void)
{
    comp_segment_entry_t original=setup_radio();uint8_t proof[84];
    consumption_proof(&original,proof);
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,proof,sizeof(proof));assert(radio.consume_pending);
    for(unsigned i=0u;i<10000u&&comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_PENDING;i++){poll();}
    assert(comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_OK);
    radio_tick(); /* successful receipt prepared, not yet published */
    assert(radio.pending_bytes==84u&&!radio.consume_pending&&receipt_count==0u);
    comp_link_connection(&link_owner.link,false,false,f.now);
    assert(radio.consume_replay&&!comp_wba_recording_radio_busy(&radio));
    connect_peer();for(unsigned i=0u;i<8u&&receipt_count==0u;i++)radio_tick();
    assert(receipt_count==1u&&last_reply_bytes==84u&&!memcmp(last_reply,proof,84u));
    puts("PASS_DISCONNECT_PREPARED_RECEIPT_REPLAYS; SOFTWARE ONLY");
}

static void unsubscribe_prepared_receipt(void)
{
    comp_segment_entry_t original=setup_radio();uint8_t proof[84];
    consumption_proof(&original,proof);
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,proof,sizeof(proof));assert(radio.consume_pending);
    for(unsigned i=0u;i<10000u&&comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_PENDING;i++)poll();
    assert(comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_OK);radio_tick();
    assert(radio.pending_bytes==84u&&!radio.consume_pending&&receipt_count==0u);
    subscribe(COMPANION_GATT_CHAR_DELETE_PRIVACY,false);
    assert(radio.consume_replay&&!comp_wba_recording_radio_busy(&radio));
    for(unsigned i=0u;i<4u;i++)radio_tick();assert(unsubscribed_consume_publish==0u);
    subscribe(COMPANION_GATT_CHAR_DELETE_PRIVACY,true);
    for(unsigned i=0u;i<8u&&receipt_count==0u;i++)radio_tick();
    assert(receipt_count==1u&&last_reply_bytes==84u&&!memcmp(last_reply,proof,84u));
    puts("PASS_UNSUBSCRIBE_PREPARED_RECEIPT_REPLAYS; SOFTWARE ONLY");
}
static void explicit_retry_supersedes_deferred_receipt(void)
{
    comp_segment_entry_t original=setup_radio();uint8_t proof[84],p[32];
    consumption_proof(&original,proof);
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,proof,sizeof(proof));assert(radio.consume_pending);
    comp_link_connection(&link_owner.link,false,false,f.now);
    for(unsigned i=0u;i<10000u&&comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_PENDING;i++){poll();radio_tick();}
    radio_tick();assert(radio.consume_replay&&!comp_wba_recording_radio_busy(&radio));
    comp_link_connection(&link_owner.link,true,true,f.now);
    subscribe(COMPANION_GATT_CHAR_RECORDING_CONTROL,true);negotiation(p);
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,p,32u);radio_tick();assert(radio.negotiated);
    subscribe(COMPANION_GATT_CHAR_DELETE_PRIVACY,true);
    unsigned erases=f.erases;send(COMPANION_GATT_CHAR_DELETE_PRIVACY,proof,sizeof(proof));
    for(unsigned i=0u;i<10u;i++)radio_tick();
    assert(receipt_count==1u&&!radio.consume_replay&&!comp_wba_recording_radio_busy(&radio));
    assert(last_reply_bytes==84u&&!memcmp(last_reply,proof,84u)&&f.erases==erases);
    puts("PASS_EXPLICIT_RETRY_SUPERSEDES_DEFERRED_RECEIPT_WITHOUT_ERASE; SOFTWARE ONLY");
}

static void disconnected_receipt_then_pipeline_reinit(void)
{
    comp_segment_entry_t original=setup_radio();uint8_t proof[84];
    consumption_proof(&original,proof);
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,proof,sizeof(proof));
    assert(radio.consume_pending);
    comp_link_connection(&link_owner.link,false,false,f.now);
    for(unsigned i=0u;i<10000u&&comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_PENDING;i++){
        poll();radio_tick();
    }
    assert(comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_OK);
    radio_tick();assert(!radio.consume_pending&&radio.consume_replay);
    /* The actual runtime recovery reinitializes the pipeline after a fault.
     * Keep the durable receipt but deliberately lose the volatile cache. */
    comp_wba_pipeline_config_t cfg=pipeline.config;
    assert(comp_wba_recording_pipeline_init(&pipeline,&cfg));
    last_reply_bytes=0u;connect_peer();
    assert(!radio.consume_pending&&!comp_wba_recording_radio_busy(&radio));
    radio_tick();assert(receipt_count==0u);
    /* Type's saved exact proof can still recover the durable receipt. */
    unsigned writes=f.writes,erases=f.erases;
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,proof,sizeof(proof));
    for(unsigned i=0u;i<10000u&&(radio.consume_pending||radio.phase!=0u);i++){poll();radio_tick();}
    assert(receipt_count==1u&&last_reply_bytes==84u&&!memcmp(last_reply,proof,84u));
    assert(writes==f.writes&&erases==f.erases);
    puts("PASS_REINITIALIZED_PIPELINE_REQUIRES_EXACT_REPLAY_WITHOUT_FALSE_RECEIPT; SOFTWARE ONLY");
}
#ifndef COMP_RADIO_TEST_MAIN
#define COMP_RADIO_TEST_MAIN main
#endif
static void capture_pair_tick(void);
static void growing_tail_frames(bool pair)
{
    (void)setup_radio();assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    /* Native Type closes directory lanes before opening payload lanes. This
     * same encrypted peer remains negotiated; a real disconnect still revokes. */
    subscribe(COMPANION_GATT_CHAR_RECORDING_CONTROL,false);subscribe(COMPANION_GATT_CHAR_RECORDING_LIST,false);
    assert(radio.negotiated);
    subscribe(COMPANION_GATT_CHAR_RECORDING_CONTROL,true);subscribe(COMPANION_GATT_CHAR_RECORDING_LIST,true);
    assert(comp_wba_recording_pipeline_begin(&pipeline,56u,COMP_WBA_RECORDING_SOURCE_MIC_SAI,0u,91u)==COMP_SEG_PENDING);
    for(unsigned i=0u;i<5000u&&pipeline.state!=COMP_PIPE_READY;i++)poll();
    assert(pipeline.state==COMP_PIPE_READY&&comp_wba_recording_pipeline_start(&pipeline,91u));
    uint8_t interval[32];negotiation(interval);interval[1]=0x25u;interval[2]=1u;
    comp_rec_put32(interval+28u,comp_rec_crc(interval,28u));
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,interval,32u);
    assert(last_reply_bytes==16u&&!memcmp(last_reply,"CRE2",4u)&&
        comp_rec_get32(last_reply+12u)==COMP_SEG_PENDING&&!radio.interval_token&&mic);
    for(unsigned block=0u;block<16u;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_cont_recording_pcm(&engine,samples,160u));
        for(unsigned i=0u;i<160u;i++)poll();
    }
    uint8_t request[32]={2u,0x23u};comp_rec_put32(request+4u,92u);comp_rec_put64(request+8u,7u);
    comp_rec_put64(request+16u,56u);unsigned writes=f.writes,erases=f.erases;
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,request,32u);radio_tick();
    assert(last_reply_bytes==80u&&!memcmp(last_reply,"CLP2",4u)&&comp_rec_get32(last_reply+68u)==92u);
    assert(comp_rec_get32(last_reply+76u)==comp_rec_crc(last_reply,76u));
    const uint32_t length=comp_rec_get32(last_reply+60u);
    assert(length==222u&&comp_rec_get64(last_reply+52u)==1600u&&engine.writer.committed_bytes>=length&&mic);
    assert(!comp_rec_v2_valid(&radio.io.selected.descriptor));
    uint8_t expected[222];memcpy(expected,f.bytes+DATA_BASE+engine.active.extent_offset+256u,222u);
    subscribe(COMPANION_GATT_CHAR_RECORDING_CONTROL,false);subscribe(COMPANION_GATT_CHAR_RECORDING_LIST,false);
    assert(radio.negotiated&&radio.pull.live);
    sealed_request(&radio.io.selected,0u,request);request[1]=0x24u;
    comp_rec_put64(request+16u,57u);unsigned rejected=link_owner.link.rejected_writes;
    send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,request,32u);assert(link_owner.link.rejected_writes==rejected+1u);
    comp_rec_put64(request+16u,56u);send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,request,32u);
    bool saw_pair=false;
    for(unsigned i=0u;i<1000u&&saved_bytes<length;i++) {
        const bool ready_before=radio.config.transfer->packet_ready;
        const uint32_t before=saved_bytes;
        if(pair)capture_pair_tick();else radio_tick();
        if(!ready_before&&saved_bytes>before)saw_pair=true;
    }
    assert(saved_bytes==length&&!memcmp(expected,saved,length)&&radio.config.transfer->snapshot_live&&mic);
    if(pair)assert(saw_pair);
    assert(f.writes==writes&&f.erases==erases&&receipt_count==0u);
    /* A new snapshot may grow; the previously durable complete prefix stays
     * byte-identical. Disconnect retires it without touching capture or NOR. */
    comp_link_connection(&link_owner.link,false,false,f.now);assert(mic&&!radio.pull.live);
    connect_peer();
    for(unsigned block=0u;block<4u;block++) {
        int16_t samples[160];pcm(block+20u,samples);assert(comp_cont_recording_pcm(&engine,samples,160u));
        for(unsigned i=0u;i<160u;i++)poll();
    }
    memset(request,0,32u);request[0]=2u;request[1]=0x23u;comp_rec_put32(request+4u,93u);
    comp_rec_put64(request+8u,7u);comp_rec_put64(request+16u,56u);
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,request,32u);radio_tick();
    assert(last_reply_bytes==80u&&comp_rec_get32(last_reply+60u)>=length&&mic);
    assert(!memcmp(expected,f.bytes+DATA_BASE+engine.active.extent_offset+256u,length));
    assert(comp_wba_recording_pipeline_stop(&pipeline,91u));
    for(unsigned i=0u;i<10000u&&pipeline.state!=COMP_PIPE_FINISHED;i++)poll();
    assert(pipeline.state==COMP_PIPE_FINISHED&&!mic);
    puts("PASS growing tail: committed complete-frame CLP2, protected session, CRC live packets without FINAL/SHA/ACK, scratch reuse, disconnect keeps capture and later prefix stable; SOFTWARE ONLY");
}
static void interval_tick(void)
{
    static const comp_wba_recording_transfer_budget_t budget={1u,1u,1u};
    unsigned reads=f.reads,writes=f.writes;
    comp_link_poll_with_budget(&link_owner.link,f.now,NULL,NULL,&budget);
    assert(f.reads-reads<=1u&&f.writes==writes);
}
static void export_pause_tail(FILE *output,uint32_t nonce,uint32_t frames)
{
    uint8_t request[32]={2u,0x23u};comp_rec_put32(request+4u,nonce);
    comp_rec_put64(request+8u,7u);comp_rec_put64(request+16u,56u);
    unsigned writes=f.writes,erases=f.erases;saved_bytes=0u;
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,request,32u);radio_tick();
    assert(last_reply_bytes==80u&&!memcmp(last_reply,"CLP2",4u)&&
        last_reply[74]==3u&&!last_reply[75]&&comp_rec_get64(last_reply+52u)==(uint64_t)frames*320u);
    const uint32_t bytes=comp_rec_get32(last_reply+60u);uint8_t count[4];comp_rec_put32(count,bytes);
    assert(comp_rec_get32(last_reply+76u)==comp_rec_crc(last_reply,76u));
    assert(fwrite(last_reply,1u,80u,output)==80u&&fwrite(count,1u,4u,output)==4u);
    assert(!comp_rec_v2_valid(&radio.io.selected.descriptor));
    sealed_request(&radio.io.selected,0u,request);request[1]=0x24u;
    send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,request,32u);
    for(unsigned i=0u;i<3000u&&(saved_bytes<bytes||comp_wba_recording_radio_busy(&radio));i++)radio_tick();
    assert(saved_bytes==bytes&&f.writes==writes&&f.erases==erases&&receipt_count==0u&&
        radio.config.transfer->snapshot_live&&!comp_wba_recording_radio_busy(&radio));
    assert(fwrite(saved,1u,bytes,output)==bytes);
    for(uint32_t at=0u;at<bytes;at++)assert(saved[at]==f.bytes[DATA_BASE+engine.active.extent_offset+256u+
        (at/248u)*256u+at%248u]);
}
static void pause_tail_interop(const char *path)
{
    (void)setup_radio();assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    assert(comp_wba_recording_pipeline_begin_timeline(&pipeline,56u,COMP_WBA_RECORDING_SOURCE_MIC_SAI,0u,91u,true)==COMP_SEG_PENDING);
    for(unsigned i=0u;i<5000u&&pipeline.state!=COMP_PIPE_READY;i++)poll();
    assert(pipeline.state==COMP_PIPE_READY&&comp_wba_recording_pipeline_start(&pipeline,91u));
    assert(!comp_wba_recording_pipeline_pause(&pipeline,92u,1u)&&mic);
    for(unsigned block=0u;block<16u;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_cont_recording_pcm(&engine,samples,160u));
        for(unsigned i=0u;i<160u;i++)poll();
    }
    FILE *output=fopen(path,"wb");assert(output);const uint8_t header[8]={'C','P','T','2',3u,0u,0u,0u};
    assert(fwrite(header,1u,8u,output)==8u);export_pause_tail(output,92u,5u);assert(mic);
    assert(comp_wba_recording_pipeline_pause(&pipeline,91u,1u));
    /* Intermediate transitions may own uncommitted event bytes; never expose
     * them as a stable live prefix, even though capture is already stopped. */
    uint8_t request[32]={2u,0x23u};comp_rec_put32(request+4u,93u);comp_rec_put64(request+8u,7u);comp_rec_put64(request+16u,56u);
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,request,32u);radio_tick();
    assert(last_reply_bytes==16u&&comp_rec_get32(last_reply+12u)==COMP_SEG_PENDING);
    for(unsigned i=0u;i<5000u&&engine.state!=COMP_CONT_PAUSED;i++)poll();
    assert(engine.state==COMP_CONT_PAUSED&&!mic&&engine.codec.frames_encoded==8u&&engine.writer.committed_bytes==744u);
    assert(comp_wba_recording_pipeline_pause(&pipeline,91u,1u)&&!comp_wba_recording_pipeline_resume(&pipeline,91u,1u));
    export_pause_tail(output,94u,8u);assert(!mic);
    const uint32_t started=f.now;f.now+=5000u;
    assert(comp_wba_recording_pipeline_resume(&pipeline,91u,2u)&&mic);
    for(unsigned i=0u;i<5000u&&engine.state!=COMP_CONT_RUNNING;i++)poll();
    assert(engine.state==COMP_CONT_RUNNING&&engine.writer.committed_bytes==992u&&engine.codec.frames_encoded==8u&&f.now-started>=5000u);
    export_pause_tail(output,95u,8u);assert(mic);
    for(unsigned block=0u;block<8u;block++) {
        int16_t samples[160];pcm(block+16u,samples);assert(comp_cont_recording_pcm(&engine,samples,160u));
        for(unsigned i=0u;i<160u;i++)poll();
    }
    assert(comp_wba_recording_pipeline_stop(&pipeline,91u));
    for(unsigned i=0u;i<10000u&&pipeline.state!=COMP_PIPE_FINISHED;i++)poll();
    assert(pipeline.state==COMP_PIPE_FINISHED&&!mic&&mic_starts==3u&&mic_stops==3u);
    comp_segment_entry_t e=engine.closing;uint8_t descriptor[112];
    assert(comp_rec_v2_encode(&e.descriptor,descriptor,sizeof(descriptor))&&e.descriptor.sample_count==12u*320u);
    assert(fwrite(descriptor,1u,sizeof(descriptor),output)==sizeof(descriptor));
    uint8_t count[4];comp_rec_put32(count,e.descriptor.encoded_length);assert(fwrite(count,1u,4u,output)==4u);
    for(uint32_t at=0u;at<e.descriptor.encoded_length;at++) {
        const uint8_t byte=f.bytes[DATA_BASE+e.extent_offset+256u+(at/248u)*256u+at%248u];
        assert(fwrite(&byte,1u,1u,output)==1u);
    }
    assert(fclose(output)==0&&receipt_count==0u&&e.state==COMP_SEG_UNSYNCED);
    puts("PAUSE_TAIL_INTEROP: actual C pipeline/radio framing,5/8/8 captured frames,222/744/992 byte prefixes,5s gap,no CRC/SHA/ACK shortcut; real fixedpointOpus SOFTWARE ONLY");
}
static void finite_batch_interval(void)
{
    comp_segment_entry_t original=setup_radio();
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    uint8_t p[32];negotiation(p);p[1]=0x25u;p[2]=1u;
    p[8]^=1u;comp_rec_put32(p+28u,comp_rec_crc(p,28u));
    uint32_t rejected=link_owner.link.rejected_writes;
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,p,32u);
    assert(link_owner.link.rejected_writes==rejected+1u&&!radio.interval_token);
    p[8]^=1u;comp_rec_put32(p+28u,comp_rec_crc(p,28u));
    unsigned writes=f.writes,erases=f.erases;
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,p,32u);interval_tick();
    assert(last_reply_bytes==32u&&!memcmp(last_reply,p,32u));
    assert(comp_wba_recording_radio_interval_hint(&radio,100u,true));
    assert(comp_wba_recording_radio_interval_hint(&radio,2099u,true));
    assert(!comp_wba_recording_radio_interval_hint(&radio,2100u,true));
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,p,32u);interval_tick();
    assert(comp_wba_recording_radio_interval_hint(&radio,UINT32_MAX-1000u,true));
    assert(comp_wba_recording_radio_interval_hint(&radio,998u,true));
    assert(!comp_wba_recording_radio_interval_hint(&radio,999u,true));
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,p,32u);interval_tick();
    assert(comp_wba_recording_radio_interval_hint(&radio,100u,true));
    uint8_t pull[32];sealed_request(&original,0u,pull);
    send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,pull,32u);
    for(unsigned i=0u;i<1000u&&!saved_bytes;i++) {
        interval_tick();(void)comp_wba_recording_radio_interval_hint(&radio,1800u,true);
    }
    for(unsigned i=0u;i<1000u&&saved_bytes<original.descriptor.encoded_length;i++)interval_tick();
    assert(saved_bytes==original.descriptor.encoded_length);
    interval_tick();assert(comp_wba_recording_radio_interval_hint(&radio,2500u,true));
    p[2]=0u;comp_rec_put32(p+4u,92u);comp_rec_put32(p+28u,comp_rec_crc(p,28u));
    rejected=link_owner.link.rejected_writes;send(COMPANION_GATT_CHAR_RECORDING_CONTROL,p,32u);
    assert(link_owner.link.rejected_writes==rejected+1u&&radio.interval_token==91u);
    comp_rec_put32(p+4u,91u);comp_rec_put32(p+28u,comp_rec_crc(p,28u));
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,p,32u);interval_tick();
    assert(last_reply_bytes==32u&&!memcmp(last_reply,p,32u)&&!radio.interval_token);
    p[2]=1u;comp_rec_put32(p+28u,comp_rec_crc(p,28u));
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,p,32u);interval_tick();
    assert(comp_wba_recording_radio_interval_hint(&radio,3000u,true));
    subscribe(COMPANION_GATT_CHAR_RECORDING_CONTROL,false);
    assert(!radio.interval_token&&radio.negotiated);
    subscribe(COMPANION_GATT_CHAR_RECORDING_CONTROL,true);
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,p,32u);interval_tick();
    assert(!comp_wba_recording_radio_interval_hint(&radio,3000u,false));
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,p,32u);interval_tick();
    comp_link_connection(&link_owner.link,false,false,f.now);
    assert(!radio.interval_token&&!radio.negotiated&&f.writes==writes&&f.erases==erases&&!mic);
    puts("PASS finite encrypted batch interval: exact UID/epoch/token, sealed completion retains hint, stale close refused, idle expiry/wrap, CCCD/cancel/disconnect revoke, no media mutation; SOFTWARE ONLY");
}
static void large_packet_profiles(void)
{
    assert(companion_opus16_rt_workspace_available());
    void *memory=companion_opus16_rt_workspace_borrow(1028u);assert(memory);
    assert(!companion_opus16_rt_workspace_borrow(16u));
    companion_opus16_rt_t encoder={0};
    assert(!companion_opus16_rt_init(&encoder));
    companion_opus16_rt_workspace_release((uint8_t *)memory+1u);
    assert(!companion_opus16_rt_workspace_available());
    companion_opus16_rt_workspace_release(memory);assert(companion_opus16_rt_workspace_available());
    for(unsigned pass=0u;pass<2u;++pass) {
        const uint16_t profile=pass?509u:495u;test_value_capacity=509u;
        comp_segment_entry_t original=setup_radio();
        assert(comp_wba_recording_radio_set_value_capacity(&radio,509u));connect_peer();
        assert(radio.config.transfer->value_capacity==244u); /* zero handshake */
        uint8_t p[32];negotiation(p);comp_rec_put16(p+2u,profile);
        comp_rec_put32(p+28u,comp_rec_crc(p,28u));
        send(COMPANION_GATT_CHAR_RECORDING_CONTROL,p,32u);radio_tick();
        assert(radio.negotiated&&radio.config.transfer->value_capacity==profile);
        sealed_request(&original,0u,p);send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,p,32u);
        blocked=1u;
        for(unsigned i=0u;i<10000u&&comp_wba_recording_radio_busy(&radio);++i)radio_tick();
        assert(saved_bytes==original.descriptor.encoded_length&&saved_bytes==768u&&!retry_bytes);
        assert(radio.config.transfer->stats.notify_backpressure==1u);
        for(unsigned at=0u;at<saved_bytes;++at)
            assert(saved[at]==f.bytes[DATA_BASE+original.extent_offset+256u+(at/248u)*256u+at%248u]);
        assert(radio.config.transfer->stats.packets_notified==2u);
        comp_link_connection(&link_owner.link,false,false,f.now);
        assert(radio.config.transfer->value_capacity==244u&&!radio.negotiated);
    }
    puts("PASS large495/509 negotiated recording: legacy244, cross-page489, immutable retry, exact768 original, disconnect resets profile; Opus/OTA workspace mutually exclusive; SOFTWARE ONLY");
}
static void resume_tick(void)
{
    static const comp_wba_recording_transfer_budget_t one_step={1u,1u,1u};
    const unsigned reads=f.reads,writes=f.writes;
    comp_link_poll_with_budget(&link_owner.link,f.now,NULL,NULL,&one_step);
    assert(f.reads-reads<=1u&&f.writes==writes);
}
static uint32_t capture_pair_clock(void *context)
{
    return *(const uint32_t *)context;
}
static bool capture_pair_pressure_seen;
static bool capture_pair_pressure_after_prepare(void *context)
{
    if(radio.config.transfer->packet_ready) {
        engine.ring_count=1u;capture_pair_pressure_seen=true;
    }
    return comp_wba_recording_radio_read_allowed(context);
}
static void capture_pair_tick(void)
{
    static const comp_wba_recording_transfer_budget_t capture_pair={1u,2u,1u};
    const unsigned reads=f.reads,writes=f.writes;
    link_owner.runtime.capture_active=mic;
    comp_link_poll_with_budget(&link_owner.link,f.now,capture_pair_clock,&f.now,&capture_pair);
    assert(f.reads-reads<=1u&&f.writes==writes);
}
static void capture_pair_sealed(void)
{
    test_value_capacity=136u;comp_segment_entry_t original=setup_radio();
    ready(56u);assert(comp_wba_recording_pipeline_start(&pipeline,91u)&&mic);
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));
    connect_peer();uint8_t p[32];sealed_request(&original,0u,p);
    send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,p,32u);
    capture_pair_pressure_seen=false;
    radio.pull.config.foreground_allowed=capture_pair_pressure_after_prepare;
    for(unsigned i=0u;i<10000u&&!capture_pair_pressure_seen;i++){poll();capture_pair_tick();}
    assert(capture_pair_pressure_seen&&radio.config.transfer->packet_ready&&saved_bytes==0u&&mic);
    engine.ring_count=0u;
    radio.pull.config.foreground_allowed=comp_wba_recording_radio_read_allowed;
    capture_pair_tick();assert(saved_bytes>0u&&mic);
    bool saw_pair=false,checked_pressure=false;
    for(unsigned i=0u;i<10000u&&saved_bytes<original.descriptor.encoded_length;i++) {
        poll();
        comp_wba_recording_transfer_t *t=radio.config.transfer;
        if(t->state==COMP_WBA_RECORDING_TRANSFER_ACTIVE && !checked_pressure && !engine.ring_count) {
            const unsigned reads=f.reads;const uint32_t before=saved_bytes;
            engine.ring_count=1u;capture_pair_tick();engine.ring_count=0u;
            assert(f.reads==reads&&saved_bytes==before&&mic);checked_pressure=true;
        }
        const bool ready_before=t->packet_ready;const uint32_t bytes_before=saved_bytes;
        capture_pair_tick();
        if(!ready_before&&saved_bytes>bytes_before)saw_pair=true;
    }
    assert(checked_pressure&&saw_pair&&mic&&saved_bytes==original.descriptor.encoded_length);
    for(unsigned at=0u;at<saved_bytes;at++)
        assert(saved[at]==f.bytes[DATA_BASE+original.extent_offset+256u+(at/248u)*256u+at%248u]);
    assert(comp_wba_recording_pipeline_stop(&pipeline,91u));
    for(unsigned i=0u;i<10000u&&pipeline.state!=COMP_PIPE_FINISHED;i++)poll();
    assert(pipeline.state==COMP_PIPE_FINISHED&&!mic&&receipt_count==0u);
    puts("PASS_CAPTURE_PAIR_SEALED_EXACT_BYTES_AND_AUDIO_GATE_SOFTWARE_ONLY");
}
static void active_sealed_resume(void)
{
    for(unsigned rewind=0u;rewind<2u;++rewind) {
        test_value_capacity=509u;comp_segment_entry_t original=setup_radio();
        assert(comp_wba_recording_radio_set_value_capacity(&radio,509u));connect_peer();
        uint8_t p[32];negotiation(p);comp_rec_put16(p+2u,509u);
        comp_rec_put32(p+28u,comp_rec_crc(p,28u));
        send(COMPANION_GATT_CHAR_RECORDING_CONTROL,p,32u);resume_tick();
        sealed_request(&original,0u,p);send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,p,32u);
        for(unsigned i=0u;i<10000u&&!saved_bytes;++i)resume_tick();
        assert(saved_bytes==489u&&radio.config.transfer->next_offset==489u);
        blocked=1u;
        for(unsigned i=0u;i<10000u&&radio.config.transfer->state!=COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED;++i)
            resume_tick();
        assert(retry_bytes&&radio.config.transfer->packet_ready);
        radio.config.transfer->notify_staged_bytes=240u;radio.config.transfer->notify_staged_lane=1u;
        const comp_wba_recording_transfer_t before=*radio.config.transfer;
        const comp_wba_segment_pull_t pull_before=radio.pull;
        const unsigned reads=f.reads,writes=f.writes;
        /* Rejected commands must leave the exact packet/prefix and reader
         * untouched, including a different identity or an unsent cursor. */
        for(unsigned invalid=0u;invalid<10u;++invalid) {
            sealed_request(&original,489u,p);
            switch(invalid) {
            case 0u:p[0]=1u;break;
            case 1u:p[1]=0x24u;break;
            case 2u:p[2]=0u;break;
            case 3u:p[3]=1u;break;
            case 4u:comp_rec_put32(p+4u,original.descriptor.recording_id+1u);break;
            case 5u:comp_rec_put64(p+8u,8u);break;
            case 6u:comp_rec_put64(p+16u,original.descriptor.session_id+1u);break;
            case 7u:comp_rec_put32(p+24u,original.descriptor.segment_index+1u);break;
            case 8u:comp_rec_put32(p+28u,490u);break;
            default:comp_rec_put32(p+28u,original.descriptor.encoded_length);break;
            }
            assert(!comp_wba_recording_radio_write(&radio,COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,p,32u,true));
            assert(!memcmp(&before,radio.config.transfer,sizeof(before)));
            assert(!memcmp(&pull_before,&radio.pull,sizeof(pull_before)));
        }
        sealed_request(&original,rewind?0u:489u,p);
        assert(!comp_wba_recording_radio_write(&radio,COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,p,32u,false));
        radio.authenticated=false;
        assert(!comp_wba_recording_radio_write(&radio,COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,p,32u,true));
        radio.authenticated=true;
        assert(!memcmp(&before,radio.config.transfer,sizeof(before)));
        assert(comp_wba_recording_radio_write(&radio,COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,p,32u,true));
        assert(radio.config.transfer->state==COMP_WBA_RECORDING_TRANSFER_IDLE);
        assert(radio.config.transfer->window_generation!=before.window_generation);
        assert(!radio.config.transfer->notify_staged_bytes&&!radio.pull.read_bytes);
        assert(f.reads==reads&&f.writes==writes); /* request itself performs no NOR I/O */
        retry_bytes=0u;if(rewind)saved_bytes=0u;
        for(unsigned i=0u;i<10000u&&comp_wba_recording_radio_busy(&radio);++i)resume_tick();
        assert(saved_bytes==original.descriptor.encoded_length&&saved_bytes==768u);
        for(unsigned at=0u;at<saved_bytes;++at)
            assert(saved[at]==f.bytes[DATA_BASE+original.extent_offset+256u+(at/248u)*256u+at%248u]);
        assert(!comp_wba_recording_radio_busy(&radio)&&!mic&&receipt_count==0u);
    }
    puts("PASS active sealed509 resume from receiver cursor or rewind: exact original, staged generation retired, wrong identities/live/flags/unsent offsets refused without I/O; SOFTWARE ONLY");
}
static void segmented_dual_lane(void)
{
    test_value_capacity=509u;comp_segment_entry_t original=setup_radio();uint8_t p[32];
    assert(comp_wba_recording_radio_set_value_capacity(&radio,509u));connect_peer();
    negotiation(p);comp_rec_put16(p+2u,509u);comp_rec_put32(p+28u,comp_rec_crc(p,28u));
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,p,32u);resume_tick();
    subscribe(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B,true);
    sealed_request(&original,0u,p);send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,p,32u);
    for(unsigned i=0u;i<10000u&&!saved_bytes;++i)resume_tick();
    assert(saved_bytes==489u&&radio.config.transfer->packet_sequence==1u);
    blocked=1u;
    for(unsigned i=0u;i<10000u&&!retry_bytes;++i)resume_tick();
    assert(retry_bytes&&retry_char==COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B);
    for(unsigned i=0u;i<10000u&&comp_wba_recording_radio_busy(&radio);++i)resume_tick();
    assert(saved_bytes==768u&&!retry_bytes&&radio.config.transfer->stats.packets_notified==2u);
    for(unsigned at=0u;at<saved_bytes;++at)
        assert(saved[at]==f.bytes[DATA_BASE+original.extent_offset+256u+(at/248u)*256u+at%248u]);
    /* Optional B retirement falls back on the same logical sequence/data;
     * a new window retains the exact original rather than switching files. */
    saved_bytes=0u;sealed_request(&original,0u,p);send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,p,32u);
    for(unsigned i=0u;i<10000u&&!saved_bytes;++i)resume_tick();
    blocked=1u;for(unsigned i=0u;i<10000u&&!retry_bytes;++i)resume_tick();
    assert(retry_char==COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B);
    subscribe(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL_B,false);retry_bytes=0u;
    blocked=1u;resume_tick();assert(retry_char==COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL);
    for(unsigned i=0u;i<10000u&&comp_wba_recording_radio_busy(&radio);++i)resume_tick();
    assert(saved_bytes==768u&&!retry_bytes&&receipt_count==0u);
    puts("PASS segmented509 optional dual lane: primary first, B odd packet/immutable retry, B retirement falls back without loss or consume; SOFTWARE ONLY");
}
static bool test_discard_random(void *v,uint32_t *out)
{(void)v;static uint32_t n=1u;*out=n++;return true;}
static void discard_product_dispatch(void)
{
    test_value_capacity=136u;comp_segment_entry_t original=setup_radio();uint8_t frame[96];
    assert(original.descriptor.flags&COMP_REC_V2_LAST);
    link_owner.runtime.config.random_u32=test_discard_random;
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();last_reply_bytes=0u;
    memset(frame,0,sizeof(frame));memcpy(frame,"CDS3",4u);frame[4]=COMP_DISCARD_V3_PREVIEW;
    comp_rec_put32(frame+8u,4321u);comp_rec_put32(frame+92u,comp_rec_crc(frame,92u));
    blocked=1u; /* first notification refused, retry must keep identical bytes */
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,frame,96u);
    for(unsigned i=0;i<10000u&&!last_reply_bytes;i++){f.now+=2u;comp_link_poll(&link_owner.link,f.now);}
    assert(last_reply_bytes==96u&&last_reply_char==COMPANION_GATT_CHAR_DELETE_PRIVACY);
    comp_discard_offer_t offer;assert(comp_discard_v3_decode(last_reply,96u,COMP_DISCARD_V3_PREVIEW,0u,&offer));
    assert(offer.oldest_id==original.descriptor.recording_id&&offer.segments==1u);
    assert(comp_discard_v3_encode(frame,COMP_DISCARD_V3_CONFIRM,0u,&offer));
    frame[44]^=2u;comp_rec_put32(frame+92u,comp_rec_crc(frame,92u));
    uint32_t rejected=link_owner.link.rejected_writes;send(COMPANION_GATT_CHAR_DELETE_PRIVACY,frame,96u);
    assert(link_owner.link.rejected_writes==rejected+1u&&!pipeline.discard_exclusive);
    subscribe(COMPANION_GATT_CHAR_DELETE_PRIVACY,false);
    assert(comp_discard_v3_encode(frame,COMP_DISCARD_V3_CONFIRM,0u,&offer));
    rejected=link_owner.link.rejected_writes;send(COMPANION_GATT_CHAR_DELETE_PRIVACY,frame,96u);
    assert(link_owner.link.rejected_writes==rejected+1u&&!pipeline.discard_exclusive);
    subscribe(COMPANION_GATT_CHAR_DELETE_PRIVACY,true);last_reply_bytes=0u;
    memset(frame,0,sizeof(frame));memcpy(frame,"CDS3",4u);frame[4]=COMP_DISCARD_V3_PREVIEW;
    comp_rec_put32(frame+8u,4322u);comp_rec_put32(frame+92u,comp_rec_crc(frame,92u));
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,frame,96u);
    for(unsigned i=0;i<10000u&&!last_reply_bytes;i++){f.now+=2u;comp_link_poll(&link_owner.link,f.now);}
    assert(last_reply_bytes==96u&&comp_discard_v3_decode(last_reply,96u,COMP_DISCARD_V3_PREVIEW,0u,&offer));
    assert(comp_discard_v3_encode(frame,COMP_DISCARD_V3_CONFIRM,0u,&offer));last_reply_bytes=0u;
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,frame,96u);
    assert(radio.discard_running&&pipeline.discard_exclusive);
    uint8_t samepeer[32];negotiation(samepeer);rejected=link_owner.link.rejected_writes;
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,samepeer,32u);
    assert(link_owner.link.rejected_writes==rejected+1u);
    for(unsigned i=0;i<10000u&&!radio.config.transfer->discard_workspace.owner.commit_started;i++){f.now+=2u;comp_link_poll(&link_owner.link,f.now);}
    assert(radio.config.transfer->discard_workspace.owner.commit_started);
    comp_link_connection(&link_owner.link,false,false,f.now);
    comp_link_connection(&link_owner.link,true,true,f.now);
    subscribe(COMPANION_GATT_CHAR_RECORDING_CONTROL,true);subscribe(COMPANION_GATT_CHAR_RECORDING_LIST,true);
    subscribe(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,true);subscribe(COMPANION_GATT_CHAR_DELETE_PRIVACY,true);
    uint8_t reconnect[32];negotiation(reconnect);send(COMPANION_GATT_CHAR_RECORDING_CONTROL,reconnect,32u);
    last_reply_bytes=0u; /* fresh peer cannot inherit old confirmation reply */
    for(unsigned i=0;i<30000u&&radio.discard_running;i++){f.now+=2u;comp_link_poll(&link_owner.link,f.now);}
    assert(!radio.discard_running&&!pipeline.discard_exclusive&&!catalog.legacy_dirty);
    assert(!last_reply_bytes);comp_link_poll(&link_owner.link,f.now);assert(radio.negotiated);
    comp_segment_entry_t e;assert(comp_segment_catalog_read(&catalog,0u,&e)==COMP_SEG_NOT_FOUND);
    assert(comp_segment_catalog_receipt_read(&catalog,0u,&e)==COMP_SEG_NOT_FOUND);
    assert(last_reply_char==COMPANION_GATT_CHAR_RECORDING_CONTROL); /* only fresh negotiation */
    puts("PASS_CDS3_PRODUCT_LINK actual dispatcher preview tamper unsubscribe reconnect exclusive recovery; SOFTWARE ONLY");
}

static void selected_discard_request(uint8_t frame[96],uint32_t request,uint64_t session)
{
    memset(frame,0,96u);memcpy(frame,"CDS3",4u);frame[4]=COMP_DISCARD_V3_PREVIEW;
    comp_rec_put32(frame+8u,request);memcpy(frame+16u,device_uid,12u);
    comp_rec_put64(frame+28u,catalog.epoch);comp_rec_put64(frame+36u,session);
    comp_rec_put32(frame+92u,comp_rec_crc(frame,92u));
}
static void selected_discard_dispatch(void)
{
    test_value_capacity=136u;comp_segment_entry_t original=setup_radio();
    uint8_t untouched[4096];assert(original.reserved_bytes==sizeof(untouched));
    memcpy(untouched,f.bytes+DATA_BASE+original.extent_offset,sizeof(untouched));
    assert(comp_wba_recording_pipeline_begin_timeline(&pipeline,56u,1u,1700000000u,92u,true)==COMP_SEG_PENDING);
    pipeline.pause_timeline=COMP_CONT_TIMELINE_SOURCE_BOUNDARY;
    for(unsigned i=0;i<10000u&&pipeline.state!=COMP_PIPE_READY;i++)poll();
    assert(comp_wba_recording_pipeline_start(&pipeline,92u));
    for(unsigned block=0;block<9u;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_cont_recording_pcm(&engine,samples,160u));
        for(unsigned i=0;i<160u;i++)poll();
    }
    assert(comp_wba_recording_pipeline_stop(&pipeline,92u));
    for(unsigned i=0;i<10000u&&pipeline.state!=COMP_PIPE_FINISHED;i++)poll();
    assert(pipeline.state==COMP_PIPE_FINISHED&&!mic);
    comp_segment_entry_t selected={0};unsigned selected_slot=64u;
    for(uint8_t i=0;i<64u;i++) {
        comp_segment_entry_t entry;
        if(comp_segment_catalog_read(&catalog,i,&entry)==COMP_SEG_OK&&entry.descriptor.session_id==56u)
            {selected=entry;selected_slot=i;}
    }
    printf("selected slot=%u samples=%llu id=%lu previous=%lu state=%u flags=%lu\n",selected_slot,
        (unsigned long long)selected.descriptor.sample_count,(unsigned long)selected.descriptor.recording_id,
        (unsigned long)original.descriptor.recording_id,(unsigned)selected.state,(unsigned long)selected.descriptor.flags);
    /* Descriptor counts encoded20ms frames; CDB1 retains the exact1440 valid
     * source samples. The existing CDS3 frame-alignment check stays strict. */
    assert(engine.stats.accepted_pcm_blocks==9u&&selected_slot<64u&&selected.descriptor.sample_count==1600u&&selected.descriptor.recording_id>original.descriptor.recording_id);
    link_owner.runtime.config.random_u32=test_discard_random;
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    uint8_t frame[96];comp_discard_offer_t offer={0};
    selected_discard_request(frame,7001u,56u);last_reply_bytes=0u;
    unsigned erases=f.erases,writes=f.writes;
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,frame,96u);
    for(unsigned i=0;i<10000u&&!last_reply_bytes;i++){f.now+=2u;comp_link_poll(&link_owner.link,f.now);}
    assert(last_reply_bytes==96u&&comp_discard_v3_decode(last_reply,96u,COMP_DISCARD_V3_PREVIEW,0u,&offer));
    assert(offer.session==56u&&offer.oldest_id==selected.descriptor.recording_id&&offer.samples==1600u&&offer.segments==1u);
    assert(f.erases==erases&&f.writes==writes);
    assert(comp_discard_v3_encode(frame,COMP_DISCARD_V3_CANCEL,0u,&offer));last_reply_bytes=0u;
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,frame,96u);radio_tick();
    assert(last_reply_bytes==96u&&last_reply[4]==COMP_DISCARD_V3_CANCEL&&last_reply[5]==COMP_DISCARD_V3_COMPLETE);
    assert(f.erases==erases&&f.writes==writes&&!pipeline.discard_exclusive);
    selected_discard_request(frame,7002u,999u);last_reply_bytes=0u;
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,frame,96u);
    for(unsigned i=0;i<10000u&&!last_reply_bytes;i++){f.now+=2u;comp_link_poll(&link_owner.link,f.now);}
    assert(last_reply_bytes==16u&&!memcmp(last_reply,"CDX3",4u));
    assert(comp_rec_get32(last_reply+8u)==COMP_SEG_NOT_FOUND&&f.erases==erases&&f.writes==writes);
    selected_discard_request(frame,7003u,56u);frame[16]^=1u;comp_rec_put32(frame+92u,comp_rec_crc(frame,92u));
    uint32_t rejected=link_owner.link.rejected_writes;send(COMPANION_GATT_CHAR_DELETE_PRIVACY,frame,96u);
    assert(link_owner.link.rejected_writes==rejected+1u&&f.erases==erases&&f.writes==writes);
    selected_discard_request(frame,7004u,56u);last_reply_bytes=0u;
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,frame,96u);
    for(unsigned i=0;i<10000u&&!last_reply_bytes;i++){f.now+=2u;comp_link_poll(&link_owner.link,f.now);}
    assert(comp_discard_v3_decode(last_reply,96u,COMP_DISCARD_V3_PREVIEW,0u,&offer));
    assert(comp_discard_v3_encode(frame,COMP_DISCARD_V3_CONFIRM,0u,&offer));last_reply_bytes=0u;
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,frame,96u);
    for(unsigned i=0;i<30000u&&radio.discard_running;i++){f.now+=2u;comp_link_poll(&link_owner.link,f.now);}
    assert(last_reply_bytes==96u&&last_reply[4]==COMP_DISCARD_V3_CONFIRM&&last_reply[5]==COMP_DISCARD_V3_COMPLETE);
    assert(!pipeline.discard_exclusive&&!radio.discard_buffer_owned&&f.erases>erases);
    comp_segment_entry_t after;
    assert(comp_segment_catalog_read(&catalog,(uint8_t)selected_slot,&after)==COMP_SEG_NOT_FOUND);
    assert(!memcmp(untouched,f.bytes+DATA_BASE+original.extent_offset,sizeof(untouched)));
    bool retained=false;
    for(uint8_t i=0;i<64u;i++)if(comp_segment_catalog_read(&catalog,i,&after)==COMP_SEG_OK) {
        assert(after.descriptor.session_id!=56u);
        if(after.descriptor.recording_id==original.descriptor.recording_id) {
            assert(!memcmp(&after.descriptor,&original.descriptor,sizeof(after.descriptor)));retained=true;
        }
    }
    assert(retained&&!storage.poisoned);
    ready(57u);assert(comp_wba_recording_pipeline_start(&pipeline,91u));
    for(unsigned block=0;block<4u;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_cont_recording_pcm(&engine,samples,160u));
        for(unsigned i=0;i<160u;i++)poll();
    }
    assert(comp_wba_recording_pipeline_stop(&pipeline,91u));
    for(unsigned i=0;i<10000u&&pipeline.state!=COMP_PIPE_FINISHED;i++)poll();
    assert(pipeline.state==COMP_PIPE_FINISHED&&!mic&&
        !memcmp(untouched,f.bytes+DATA_BASE+original.extent_offset,sizeof(untouched)));
    puts("PASS_SELECTED_CDS3 actual dispatcher deletes newer chosen session with10ms tail; cancel/absent/wrongUID never erase; older original byte-identical; SOFTWARE ONLY");
}
static void discard_workspace_lifetimes(void)
{
    test_value_capacity=136u;comp_segment_entry_t original=setup_radio();
    link_owner.runtime.config.random_u32=test_discard_random;
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    uint8_t frame[96],request[32];comp_discard_offer_t offer;
    memset(frame,0,sizeof(frame));memcpy(frame,"CDS3",4u);frame[4]=COMP_DISCARD_V3_PREVIEW;
    comp_rec_put32(frame+8u,5001u);comp_rec_put32(frame+92u,comp_rec_crc(frame,92u));
    last_reply_bytes=0u;send(COMPANION_GATT_CHAR_DELETE_PRIVACY,frame,96u);
    assert(radio.discard_buffer_owned&&radio.discard_running);
    negotiation(request);uint32_t rejected=link_owner.link.rejected_writes;
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,request,32u);
    assert(link_owner.link.rejected_writes==rejected+1u);
    for(unsigned i=0;i<10000u&&!last_reply_bytes;i++){f.now+=2u;comp_link_poll(&link_owner.link,f.now);}
    assert(comp_discard_v3_decode(last_reply,96u,COMP_DISCARD_V3_PREVIEW,0u,&offer));
    /* An ordinary operation retires the offered token before reusing packet. */
    negotiation(request);send(COMPANION_GATT_CHAR_RECORDING_CONTROL,request,32u);
    assert(!radio.discard_buffer_owned);last_reply_bytes=0u;radio_tick();
    assert(radio.negotiated&&last_reply_bytes==32u&&!memcmp(last_reply,request,32u));
    assert(comp_discard_v3_encode(frame,COMP_DISCARD_V3_CONFIRM,0u,&offer));
    rejected=link_owner.link.rejected_writes;send(COMPANION_GATT_CHAR_DELETE_PRIVACY,frame,96u);
    assert(link_owner.link.rejected_writes==rejected+1u&&!pipeline.discard_exclusive);
    /* Cancel retains its confirmation over backpressure and releases buffer. */
    memset(frame,0,sizeof(frame));memcpy(frame,"CDS3",4u);frame[4]=COMP_DISCARD_V3_PREVIEW;
    comp_rec_put32(frame+8u,5002u);comp_rec_put32(frame+92u,comp_rec_crc(frame,92u));
    last_reply_bytes=0u;send(COMPANION_GATT_CHAR_DELETE_PRIVACY,frame,96u);
    for(unsigned i=0;i<10000u&&!last_reply_bytes;i++){f.now+=2u;comp_link_poll(&link_owner.link,f.now);}
    assert(comp_discard_v3_decode(last_reply,96u,COMP_DISCARD_V3_PREVIEW,0u,&offer));
    assert(comp_discard_v3_encode(frame,COMP_DISCARD_V3_CANCEL,0u,&offer));last_reply_bytes=0u;blocked=1u;
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,frame,96u);assert(!radio.discard_buffer_owned);
    radio_tick();assert(!last_reply_bytes);radio_tick();
    assert(last_reply_bytes==96u&&comp_discard_v3_decode(last_reply,96u,COMP_DISCARD_V3_CANCEL,COMP_DISCARD_V3_COMPLETE,&offer));
    comp_segment_entry_t entry;assert(comp_segment_catalog_read(&catalog,0u,&entry)==COMP_SEG_OK);
    assert(entry.descriptor.recording_id==original.descriptor.recording_id&&!receipt_count);
    puts("PASS_CDS3_SHARED_BUFFER offer_invalidation cancel_backpressure no_loss; SOFTWARE ONLY");
}

static void discard_release_failure_retains_workspace(bool after_commit,bool unsubscribe_only)
{
    test_value_capacity=136u;comp_segment_entry_t original=setup_radio();
    link_owner.runtime.config.random_u32=test_discard_random;
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    uint8_t frame[96];comp_discard_offer_t offer;
    memset(frame,0,sizeof(frame));memcpy(frame,"CDS3",4u);frame[4]=COMP_DISCARD_V3_PREVIEW;
    comp_rec_put32(frame+8u,6001u);comp_rec_put32(frame+92u,comp_rec_crc(frame,92u));
    last_reply_bytes=0u;send(COMPANION_GATT_CHAR_DELETE_PRIVACY,frame,96u);
    for(unsigned i=0;i<10000u&&!last_reply_bytes;i++){f.now+=2u;comp_link_poll(&link_owner.link,f.now);}
    assert(comp_discard_v3_decode(last_reply,96u,COMP_DISCARD_V3_PREVIEW,0u,&offer));
    assert(comp_discard_v3_encode(frame,COMP_DISCARD_V3_CONFIRM,0u,&offer));
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,frame,96u);
    assert(pipeline.discard_exclusive&&radio.discard_buffer_owned&&radio.config.transfer->discard_workspace.owner.owns);
    assert(!radio.config.transfer->discard_workspace.owner.commit_started);
    if(after_commit) {
        for(unsigned i=0;i<10000u&&!radio.config.transfer->discard_workspace.owner.commit_started;i++){
            f.now+=2u;comp_link_poll(&link_owner.link,f.now);
        }
        assert(radio.config.transfer->discard_workspace.owner.commit_started);
    }
    storage.poisoned=true; /* actual pipeline refuses release while storage fault persists */
    if(unsubscribe_only)subscribe(COMPANION_GATT_CHAR_DELETE_PRIVACY,false);
    else comp_link_connection(&link_owner.link,false,false,f.now);
    assert(pipeline.discard_exclusive&&radio.discard_buffer_owned&&radio.config.transfer->discard_workspace.owner.owns);
    if(!unsubscribe_only)comp_link_connection(&link_owner.link,true,true,f.now);
    subscribe(COMPANION_GATT_CHAR_RECORDING_CONTROL,true);subscribe(COMPANION_GATT_CHAR_DELETE_PRIVACY,true);
    uint8_t request[32];negotiation(request);last_reply_bytes=0u;
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,request,32u);
    radio_tick();radio_tick();
    printf("release diagnosis buffer=%u owns=%u running=%u phase=%u reply=%u negotiated=%u\n",(unsigned)radio.discard_buffer_owned,(unsigned)radio.config.transfer->discard_workspace.owner.owns,(unsigned)radio.discard_running,(unsigned)radio.phase,(unsigned)last_reply_bytes,(unsigned)radio.negotiated);
    assert(pipeline.discard_exclusive&&radio.discard_buffer_owned&&radio.config.transfer->discard_workspace.owner.owns);
    assert(!last_reply_bytes&&!radio.negotiated);
    storage.poisoned=false; /* test-only: verify media still contains same original */
    if(!after_commit) {
        comp_segment_entry_t entry;assert(comp_segment_catalog_read(&catalog,0u,&entry)==COMP_SEG_OK);
        assert(entry.descriptor.recording_id==original.descriptor.recording_id&&!receipt_count);
    }
    puts(after_commit?"PASS_COMMITTED_FAULT_LINK_RETAINS_WORKSPACE; SOFTWARE ONLY":
        "PASS_REFUSED_RELEASE_LINK_RETAINS_WORKSPACE_AND_ORIGINAL; SOFTWARE ONLY");
}

static void directory_read_error_reply(void)
{
    (void)setup_radio();uint8_t request[16]={2u,0x20u};
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    comp_rec_put32(request+8u,71u);last_reply_bytes=0u;
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,request,sizeof(request));
    f.fail_command=3u;
    for(unsigned i=0u;i<100u&&!last_reply_bytes;i++)radio_tick();
    assert(storage.poisoned&&storage.idle_lookup_read_failed&&!comp_wba_recording_radio_busy(&radio)&&
        last_reply_char==COMPANION_GATT_CHAR_RECORDING_LIST&&last_reply_bytes==16u&&
        !memcmp(last_reply,"CRE2",4u)&&comp_rec_get32(last_reply+8u)==71u&&
        comp_rec_get32(last_reply+12u)==COMP_SEG_IO_ERROR);
    puts("PASS_DIRECTORY_READ_ERROR_REPLY_AND_RELEASE; SOFTWARE ONLY");
}
static void consume_read_error_reply(void)
{
    comp_segment_entry_t original=setup_radio();uint8_t proof[84];
    consumption_proof(&original,proof);
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    assert(pipeline.state==COMP_PIPE_FINISHED&&engine.state==COMP_CONT_SEALED);
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,proof,sizeof(proof));assert(radio.consume_pending);
    f.fail_command=3u; /* Next NOR read is the consume lookup, before ACK. */
    for(unsigned i=0u;i<1000u&&comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_PENDING;i++) {
        f.now+=2u;(void)comp_wba_recording_pipeline_poll(&pipeline);
    }
    assert(storage.poisoned && comp_wba_recording_pipeline_consume_idle_read_failed(&pipeline) &&
        comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_IO_ERROR &&
        pipeline.state==COMP_PIPE_FAILED && engine.state==COMP_CONT_SEALED);
    for(unsigned i=0u;i<10u&&comp_wba_recording_radio_busy(&radio);i++)radio_tick();
    assert(!comp_wba_recording_radio_busy(&radio)&&!radio.consume_pending&&!receipt_count &&
        last_reply_char==COMPANION_GATT_CHAR_DELETE_PRIVACY && last_reply_bytes==16u &&
        !memcmp(last_reply,"CAE2",4u) && comp_rec_get32(last_reply+8u)==original.descriptor.recording_id &&
        comp_rec_get32(last_reply+12u)==COMP_SEG_IO_ERROR);
    puts("PASS_CONSUME_READ_ERROR_REPORTS_BEFORE_RECOVERY; SOFTWARE ONLY");
}
static void failed_consume_keeps_pending_owner(void)
{
    comp_segment_entry_t original=setup_radio();uint8_t proof[84],other[84];
    consumption_proof(&original,proof);
    assert(comp_wba_recording_pipeline_consume_wire(&pipeline,proof)==COMP_SEG_PENDING);
    for(unsigned i=0;i<1000u && catalog.pending!=&pipeline.consume;i++) {
        f.now+=2u;(void)comp_wba_recording_pipeline_poll(&pipeline);
    }
    assert(catalog.phase && catalog.pending==&pipeline.consume);
    comp_segment_entry_t saved_owner=pipeline.consume;
    storage.poisoned=true; /* simulate another real NOR transaction failing */
    f.now+=2u;(void)comp_wba_recording_pipeline_poll(&pipeline);
    assert(catalog.phase && catalog.pending==&pipeline.consume);
    assert(comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_BAD_STATE);
    assert(pipeline.state==COMP_PIPE_FAILED);
    memcpy(other,proof,sizeof(other));comp_rec_put32(other+40u,original.descriptor.recording_id+100u);
    comp_rec_put32(other+80u,comp_rec_crc(other,80u));
    comp_segment_result_t retry_result=comp_wba_recording_pipeline_consume_wire(&pipeline,other);
    printf("consume fault retry=%u phase=%u owner_same=%u poisoned=%u\n",(unsigned)retry_result,(unsigned)catalog.phase,
        (unsigned)(memcmp(&saved_owner,&pipeline.consume,sizeof(saved_owner))==0),(unsigned)storage.poisoned);
    assert(retry_result==COMP_SEG_BAD_STATE);
    assert(catalog.pending==&pipeline.consume && !memcmp(&saved_owner,&pipeline.consume,sizeof(saved_owner)));
    /* Even if a fault flag clears, the original catalog transaction is still
     * not settled. Both API shapes must preserve its exact object. */
    storage.poisoned=false;
    pipeline.state=COMP_PIPE_FINISHED; /* hypothetical incomplete recovery */
    assert(comp_wba_recording_pipeline_consume_wire(&pipeline,other)==COMP_SEG_BAD_STATE);
    comp_rec_v2_descriptor_t full=original.descriptor;full.recording_id+=100u;
    assert(comp_rec_v2_valid(&full));
    assert(comp_wba_recording_pipeline_consume(&pipeline,&full)==COMP_SEG_BAD_STATE);
    assert(catalog.pending==&pipeline.consume && !memcmp(&saved_owner,&pipeline.consume,sizeof(saved_owner)));
    puts("PASS_PENDING_CONSUME_OWNER_NOT_OVERWRITTEN; SOFTWARE ONLY");
}

static void consume_fault_stops_active_capture(void)
{
    comp_segment_entry_t original=setup_radio();uint8_t proof[84];consumption_proof(&original,proof);
    ready(56u);assert(comp_wba_recording_pipeline_start(&pipeline,91u)&&mic);
    assert(comp_wba_recording_pipeline_consume_wire(&pipeline,proof)==COMP_SEG_PENDING);
    for(unsigned i=0;i<10000u && catalog.pending!=&pipeline.consume;i++) {
        f.now+=2u;(void)comp_wba_recording_pipeline_poll(&pipeline);
    }
    assert(catalog.phase && catalog.pending==&pipeline.consume && mic);
    storage.poisoned=true;
    for(unsigned i=0;i<100u && pipeline.state!=COMP_PIPE_FAILED;i++) {
        f.now+=2u;(void)comp_wba_recording_pipeline_poll(&pipeline);
    }
    assert(pipeline.state==COMP_PIPE_FAILED&&!mic);
    assert(catalog.pending==&pipeline.consume&&receipt_count==0u);
    puts("PASS_CONSUME_FAULT_STOPS_CAPTURE_WITH_OWNER_PRESERVED; SOFTWARE ONLY");
}

static void fault_stop_retries_transient_failure(void)
{
    (void)setup_radio();ready(56u);assert(comp_wba_recording_pipeline_start(&pipeline,91u)&&mic);
    fail_mic_stops=3u;
    comp_cont_recording_fault(&engine,COMP_SEG_BAD_STATE);
    for(unsigned i=0u;i<100u&&mic;i++) {f.now+=100u;(void)comp_wba_recording_pipeline_poll(&pipeline);}
    printf("fault stop mic=%u engine=%u pipeline=%u failures_left=%u\n",(unsigned)mic,(unsigned)engine.state,(unsigned)pipeline.state,fail_mic_stops);
    assert(!mic&&!engine.microphone_active&&!engine.encoder_owned&&pipeline.state==COMP_PIPE_FAILED);
    assert(mic_stops==2u); /* setup's original stop and this fault stop */
    puts("PASS_FAULT_MIC_STOP_TRANSIENT_RETRY; SOFTWARE ONLY");
}

static void fault_stop_retries_bounded(void)
{
    (void)setup_radio();ready(57u);assert(comp_wba_recording_pipeline_start(&pipeline,91u)&&mic);
    fail_mic_stops=100u;comp_cont_recording_fault(&engine,COMP_SEG_BAD_STATE);
    f.now+=1u;(void)comp_wba_recording_pipeline_poll(&pipeline);
    assert(mic&&pipeline.state==COMP_PIPE_FAILED&&!engine.encoder_owned);
    unsigned reads=f.reads,writes=f.writes,erases=f.erases;
    f.now=UINT32_MAX-50u; /* retry deadline crosses millisecond timer wrap */
    (void)comp_wba_recording_pipeline_poll(&pipeline); /* first guarded retry */
    assert(pipeline.fault_stop_attempts==1u);
    unsigned left=fail_mic_stops;
    for(unsigned i=0;i<20u;i++)(void)comp_wba_recording_pipeline_poll(&pipeline);
    assert(fail_mic_stops==left&&pipeline.fault_stop_attempts==1u);
    for(unsigned i=0;i<20u;i++){f.now+=100u;(void)comp_wba_recording_pipeline_poll(&pipeline);}
    assert(mic&&engine.microphone_active&&pipeline.fault_stop_attempts==3u&&
        pipeline.state==COMP_PIPE_FAILED&&fail_mic_stops==left-2u);
    assert(f.reads==reads&&f.writes==writes&&f.erases==erases);
    puts("PASS_FAULT_MIC_STOP_RETRY_BOUNDED real_failure_not_hidden no_storage_while_running; SOFTWARE ONLY");
}

static void sealed_payload_fault_releases_radio(void)
{
    comp_segment_entry_t original=setup_radio();assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();uint8_t request[32];
    sealed_request(&original,0u,request);send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,request,32u);
    for(unsigned i=0u;i<1000u&&radio.config.transfer->state==COMP_WBA_RECORDING_TRANSFER_IDLE;i++)radio_tick();
    assert(radio.config.transfer->state==COMP_WBA_RECORDING_TRANSFER_ACTIVE && !catalog.phase && !nor.erase_active);
    static uint8_t before[COMP_NOR_FIXTURE_BYTES];memcpy(before,f.bytes,sizeof(before));
    unsigned writes=f.writes,erases=f.erases;f.fail_command=3u;
    for(unsigned i=0u;i<1000u&&comp_wba_recording_radio_busy(&radio);i++)radio_tick();
    assert(!f.fail_command&&storage.poisoned&&storage.idle_lookup_read_failed);
    assert(!comp_wba_recording_radio_busy(&radio)&&radio.config.transfer->state==COMP_WBA_RECORDING_TRANSFER_FAILED);
    assert(f.writes==writes&&f.erases==erases&&!memcmp(before,f.bytes,sizeof(before)));
    puts("PASS_SEALED_PAYLOAD_FAILURE_RELEASES_RADIO; SOFTWARE ONLY");
}

static void transient_sealed_read_during_capture(bool fail_release,bool fail_data)
{
    comp_segment_entry_t original=setup_radio();ready(56u);
    assert(comp_wba_recording_pipeline_start(&pipeline,91u)&&mic);
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    uint8_t request[32];sealed_request(&original,0u,request);
    send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,request,32u);
    for(unsigned i=0u;i<1000u&&radio.config.transfer->state==COMP_WBA_RECORDING_TRANSFER_IDLE;i++)radio_tick();
    assert(radio.config.transfer->state==COMP_WBA_RECORDING_TRANSFER_ACTIVE && !catalog.phase && !nor.erase_active && mic);
    static uint8_t before[COMP_NOR_FIXTURE_BYTES];memcpy(before,f.bytes,sizeof(before));
    unsigned writes=f.writes,erases=f.erases;f.fail_command=fail_data?0u:3u;f.fail_read_data_once=fail_data;f.fail_deassert_once=fail_release;
    for(unsigned i=0u;i<1000u&&comp_wba_recording_radio_busy(&radio);i++)radio_tick();
    assert(!f.fail_command && !f.fail_deassert_once && !f.fail_read_data_once && !comp_wba_recording_radio_busy(&radio) && mic);
    assert(f.writes==writes && f.erases==erases && !memcmp(before,f.bytes,sizeof(before)));
    const bool uncertain=fail_release||!fail_data;
    assert(storage.poisoned==uncertain);
    if(!uncertain) {
        /* Without a new request, the same peer receives the entire immutable
         * segment after a bounded retry of the failed physical page. */
        assert(saved_bytes==original.descriptor.encoded_length&&mic&&!storage.poisoned);
        for(uint32_t at=0u;at<saved_bytes;at++)
            assert(saved[at]==before[DATA_BASE+original.extent_offset+256u+(at/248u)*256u+at%248u]);
        assert(f.writes==writes&&f.erases==erases);
    }
    for(unsigned block=0u;block<32u&&pipeline.state!=COMP_PIPE_FAILED;block++) {
        int16_t samples[160];pcm(block+100u,samples);
        if(!comp_cont_recording_pcm(&engine,samples,160u))break;
        for(unsigned j=0u;j<100u&&pipeline.state!=COMP_PIPE_FAILED;j++){f.now+=2u;(void)comp_wba_recording_pipeline_poll(&pipeline);}
    }
    if(uncertain) {
        for(unsigned i=0u;i<100u&&mic;i++){f.now+=100u;(void)comp_wba_recording_pipeline_poll(&pipeline);}
        assert(pipeline.state==COMP_PIPE_FAILED && !mic && storage.poisoned);
        puts("PASS_UNCERTAIN_HEADER_OR_CS_FAILURE_STOPS_CAPTURE_SOFTWARE_ONLY");
    } else {
        assert(mic && !storage.poisoned && engine.stats.accepted_pcm_blocks==32u);
        assert(comp_wba_recording_pipeline_stop(&pipeline,91u));
        for(unsigned i=0u;i<10000u&&pipeline.state!=COMP_PIPE_FINISHED;i++){f.now+=2u;(void)comp_wba_recording_pipeline_poll(&pipeline);}
        assert(pipeline.state==COMP_PIPE_FINISHED && !mic && !storage.poisoned);
        assert(!memcmp(before+DATA_BASE+original.extent_offset,f.bytes+DATA_BASE+original.extent_offset,original.reserved_bytes));
        comp_segment_entry_t produced={0};bool found=false;
        for(uint8_t i=0u;i<64u&&!found;i++)if(catalog.slots[i]!=255u) {
            comp_segment_entry_t candidate;
            assert(comp_wba_segment_storage_entry(&storage,&catalog,i,&candidate)==COMP_SEG_OK);
            if(candidate.descriptor.session_id==56u){produced=candidate;found=true;}
        }
        assert(found&&produced.state==COMP_SEG_UNSYNCED&&produced.descriptor.sample_count==32u*160u);
        comp_segment_audio_port_t port=comp_wba_segment_storage_audio_port(&storage);
        companion_sha256_t hash;companion_sha256_init(&hash);uint32_t bytes=0u,index=0u;uint8_t data[256],length,digest[32];
        while(bytes<produced.descriptor.encoded_length) {
            assert(comp_segment_audio_read_page(&port,&produced,DATA_BASE,index++,data,&length)==COMP_SEG_OK);
            companion_sha256_update(&hash,data,length);bytes+=length;
        }
        companion_sha256_final(&hash,digest);
        assert(bytes==produced.descriptor.encoded_length&&!memcmp(digest,produced.descriptor.sha256,32u));
        puts("PASS_RELEASED_READ_FAILURE_KEEP_CAPTURE_AND_ORIGINAL_SOFTWARE_ONLY");
    }
}

static void directory_read_during_capture(bool generation_change,bool uncertain_release)
{
    comp_segment_entry_t original=setup_radio();ready(56u);
    assert(comp_wba_recording_pipeline_start(&pipeline,91u)&&mic);
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    uint8_t request[32];sealed_request(&original,0u,request);
    send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,request,32u);
    if(generation_change) {
        for(unsigned i=0u;i<1000u&&radio.config.transfer->state==COMP_WBA_RECORDING_TRANSFER_IDLE;i++)radio_tick();
        assert(radio.config.transfer->state==COMP_WBA_RECORDING_TRANSFER_ACTIVE);
        ++catalog.generation; /* force the real immutable-entry recheck path */
    }
    assert(!catalog.phase&&!nor.erase_active&&mic&&catalog.mounted);
    static uint8_t before[COMP_NOR_FIXTURE_BYTES];memcpy(before,f.bytes,sizeof(before));
    unsigned writes=f.writes,erases=f.erases;
    f.fail_read_data_once=true;f.fail_deassert_once=uncertain_release;
    for(unsigned i=0u;i<1000u&&f.fail_read_data_once;i++)radio_tick();
    assert(!f.fail_read_data_once&&!f.fail_deassert_once);
    if(uncertain_release) {
        for(unsigned i=0u;i<1000u&&comp_wba_recording_radio_busy(&radio);i++)radio_tick();
        assert(storage.poisoned&&storage.idle_lookup_read_failed&&!catalog.mounted&&!comp_wba_recording_radio_busy(&radio));
        for(unsigned i=0u;i<100u&&mic;i++){f.now+=100u;(void)comp_wba_recording_pipeline_poll(&pipeline);}
        assert(pipeline.state==COMP_PIPE_FAILED&&!mic);
        assert(f.writes==writes&&f.erases==erases&&!memcmp(before,f.bytes,sizeof(before)));
        puts("PASS_DIRECTORY_UNCERTAIN_RELEASE_FAILS_CLOSED_SOFTWARE_ONLY");return;
    }
    assert(!storage.poisoned&&catalog.mounted&&mic);
    for(unsigned i=0u;i<5000u&&saved_bytes<original.descriptor.encoded_length;i++)radio_tick();
    assert(saved_bytes==original.descriptor.encoded_length&&mic&&!storage.poisoned&&catalog.mounted);
    for(uint32_t at=0u;at<saved_bytes;at++)
        assert(saved[at]==before[DATA_BASE+original.extent_offset+256u+(at/248u)*256u+at%248u]);
    assert(f.writes==writes&&f.erases==erases);
    for(unsigned block=0u;block<32u;block++) {
        int16_t samples[160];pcm(block+100u,samples);assert(comp_cont_recording_pcm(&engine,samples,160u));
        for(unsigned j=0u;j<100u;j++){f.now+=2u;(void)comp_wba_recording_pipeline_poll(&pipeline);}
    }
    assert(mic&&engine.stats.accepted_pcm_blocks==32u&&comp_wba_recording_pipeline_stop(&pipeline,91u));
    for(unsigned i=0u;i<10000u&&pipeline.state!=COMP_PIPE_FINISHED;i++)poll();
    assert(pipeline.state==COMP_PIPE_FINISHED&&!mic&&!storage.poisoned&&catalog.mounted);
    assert(!memcmp(before+DATA_BASE+original.extent_offset,f.bytes+DATA_BASE+original.extent_offset,original.reserved_bytes));
    puts("PASS_DIRECTORY_RELEASED_FAILURE_RETRIES_AND_PRESERVES_CAPTURE_SOFTWARE_ONLY");
}

static void bounded_directory_read_failure(uint32_t delay)
{
    comp_segment_entry_t original=setup_radio();ready(56u);
    assert(comp_wba_recording_pipeline_start(&pipeline,91u)&&mic);
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    uint8_t request[32];sealed_request(&original,0u,request);
    send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,request,32u);
    unsigned attempts=0u;uint32_t injected_ms=0u;
    do {
        f.fail_read_delay_ms=delay;f.fail_read_data_once=true;
        for(unsigned i=0u;i<1000u&&f.fail_read_data_once;i++)radio_tick();
        assert(!f.fail_read_data_once&&mic&&catalog.mounted&&!storage.poisoned&&saved_bytes==0u);
        ++attempts;
        /* The transport caps a fake delay at the requested timeout. Asking
         * for10ms is not evidence that a10ms timeout actually elapsed. */
        injected_ms+=delay<f.last_read_timeout?delay:f.last_read_timeout;
        assert(attempts<=3u);
        if(!delay && attempts<3u)assert(comp_wba_recording_radio_busy(&radio));
        if(attempts==3u || injected_ms>=10u)assert(!comp_wba_recording_radio_busy(&radio));
    } while(comp_wba_recording_radio_busy(&radio));
    f.fail_read_delay_ms=0u;
    sealed_request(&original,0u,request);send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,request,32u);
    for(unsigned i=0u;i<5000u&&saved_bytes<original.descriptor.encoded_length;i++)radio_tick();
    assert(saved_bytes==original.descriptor.encoded_length&&mic&&catalog.mounted&&!storage.poisoned);
    assert(comp_wba_recording_pipeline_stop(&pipeline,91u));
    for(unsigned i=0u;i<10000u&&pipeline.state!=COMP_PIPE_FINISHED;i++)poll();
    assert(pipeline.state==COMP_PIPE_FINISHED&&!mic);
    puts("PASS_DIRECTORY_BOUNDED_FAILURE_REENTRY_SOFTWARE_ONLY");
}

static void bounded_transient_read_failure(void)
{
    comp_segment_entry_t original=setup_radio();ready(56u);
    assert(comp_wba_recording_pipeline_start(&pipeline,91u)&&mic);
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    uint8_t request[32];sealed_request(&original,0u,request);
    send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,request,32u);
    for(unsigned i=0u;i<1000u&&radio.config.transfer->state==COMP_WBA_RECORDING_TRANSFER_IDLE;i++)radio_tick();
    assert(radio.config.transfer->state==COMP_WBA_RECORDING_TRANSFER_ACTIVE);
    for(unsigned attempt=0u;attempt<3u;attempt++) {
        f.fail_read_data_once=true;
        for(unsigned i=0u;i<1000u&&f.fail_read_data_once;i++)radio_tick();
        assert(!f.fail_read_data_once && !storage.poisoned && mic && saved_bytes==0u);
        if(attempt<2u)assert(comp_wba_recording_radio_busy(&radio));
    }
    assert(!comp_wba_recording_radio_busy(&radio));
    sealed_request(&original,0u,request);send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,request,32u);
    for(unsigned i=0u;i<3000u&&saved_bytes<original.descriptor.encoded_length;i++)radio_tick();
    assert(saved_bytes==original.descriptor.encoded_length && mic && !storage.poisoned);
    assert(comp_wba_recording_pipeline_stop(&pipeline,91u));
    for(unsigned i=0u;i<10000u&&pipeline.state!=COMP_PIPE_FINISHED;i++)poll();
    assert(pipeline.state==COMP_PIPE_FINISHED&&!mic);
    puts("PASS_BOUNDED_READ_RETRIES_AND_EXPLICIT_RECOVERY_SOFTWARE_ONLY");
}

static void timed_read_failure(uint32_t delay,uint32_t initial_ms,bool pair)
{
    comp_segment_entry_t original=setup_radio();ready(56u);
    assert(comp_wba_recording_pipeline_start(&pipeline,91u)&&mic);
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    uint8_t request[32];sealed_request(&original,0u,request);
    send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,request,32u);
    for(unsigned i=0u;i<1000u&&radio.config.transfer->state==COMP_WBA_RECORDING_TRANSFER_IDLE;i++)radio_tick();
    assert(radio.config.transfer->state==COMP_WBA_RECORDING_TRANSFER_ACTIVE);
    uint32_t original_ms=f.now;
    f.now=initial_ms;f.fail_read_delay_ms=delay;f.fail_read_data_once=true;
    for(unsigned i=0u;i<1000u&&f.fail_read_data_once;i++) {
        if(pair)capture_pair_tick();else radio_tick();
    }
    assert(!f.fail_read_data_once&&!storage.poisoned&&mic&&saved_bytes==0u);
    if(delay<10u)assert(comp_wba_recording_radio_busy(&radio));
    else {
        /* The current WBA driver caps each NOR read at 8 ms, even when this
         * fixture asks it to stall for longer. A single capped failure is
         * retryable; inject the next failure to test the cumulative 10 ms
         * budget instead of pretending the first one actually took 10 ms. */
        assert(f.last_read_timeout==8u && f.now-initial_ms==8u &&
               comp_wba_recording_radio_busy(&radio));
        f.fail_read_data_once=true;
        for(unsigned i=0u;i<1000u&&f.fail_read_data_once;i++) {
            if(pair)capture_pair_tick();else radio_tick();
        }
        assert(!f.fail_read_data_once && f.now-initial_ms>=10u && mic);
        assert(!comp_wba_recording_radio_busy(&radio));
        sealed_request(&original,0u,request);send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,request,32u);
    }
    for(unsigned i=0u;i<3000u&&saved_bytes<original.descriptor.encoded_length;i++) {
        if(pair)capture_pair_tick();else radio_tick();
    }
    assert(saved_bytes==original.descriptor.encoded_length&&mic&&!storage.poisoned);
    /* Time jumps above isolate this helper's wrap/boundary arithmetic; restore
     * fixture time before normal pipeline shutdown, not a real-time claim. */
    f.now=original_ms;
    assert(comp_wba_recording_pipeline_stop(&pipeline,91u));
    for(unsigned i=0u;i<10000u&&pipeline.state!=COMP_PIPE_FINISHED;i++)poll();
    assert(pipeline.state==COMP_PIPE_FINISHED&&!mic);
    puts("PASS_TIMED_READ_FAILURE_BOUND_AND_REENTRY_SOFTWARE_ONLY");
}

static void cumulative_read_failure_budget(void)
{
    comp_segment_entry_t original=setup_radio();ready(56u);
    assert(comp_wba_recording_pipeline_start(&pipeline,91u)&&mic);
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    uint8_t request[32];sealed_request(&original,0u,request);
    send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,request,32u);
    for(unsigned i=0u;i<1000u&&radio.config.transfer->state==COMP_WBA_RECORDING_TRANSFER_IDLE;i++)radio_tick();
    assert(radio.config.transfer->state==COMP_WBA_RECORDING_TRANSFER_ACTIVE);
    uint32_t original_ms=f.now;
    for(unsigned attempt=0u;attempt<2u;attempt++) {
        f.fail_read_delay_ms=attempt?4u:6u;f.fail_read_data_once=true;
        for(unsigned i=0u;i<1000u&&f.fail_read_data_once;i++)radio_tick();
        assert(!f.fail_read_data_once&&!storage.poisoned&&mic&&saved_bytes==0u);
        assert(comp_wba_recording_radio_busy(&radio)==(attempt==0u));
    }
    f.now=original_ms;
    assert(comp_wba_recording_pipeline_stop(&pipeline,91u));
    for(unsigned i=0u;i<10000u&&pipeline.state!=COMP_PIPE_FINISHED;i++)poll();
    assert(pipeline.state==COMP_PIPE_FINISHED&&!mic);
    puts("PASS_CUMULATIVE_READ_FAILURE_BUDGET_SOFTWARE_ONLY");
}

static void transient_live_read_during_capture(void)
{
    (void)setup_radio();assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    assert(comp_wba_recording_pipeline_begin(&pipeline,56u,COMP_WBA_RECORDING_SOURCE_MIC_SAI,0u,91u)==COMP_SEG_PENDING);
    for(unsigned i=0u;i<5000u&&pipeline.state!=COMP_PIPE_READY;i++)poll();
    assert(pipeline.state==COMP_PIPE_READY&&comp_wba_recording_pipeline_start(&pipeline,91u));
    for(unsigned block=0u;block<16u;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_cont_recording_pcm(&engine,samples,160u));
        for(unsigned i=0u;i<160u;i++)poll();
    }
    uint8_t request[32]={2u,0x23u};comp_rec_put32(request+4u,92u);comp_rec_put64(request+8u,7u);
    comp_rec_put64(request+16u,56u);send(COMPANION_GATT_CHAR_RECORDING_CONTROL,request,32u);radio_tick();
    assert(last_reply_bytes==80u&&!memcmp(last_reply,"CLP2",4u)&&radio.pull.live&&mic);
    sealed_request(&radio.io.selected,0u,request);request[1]=0x24u;
    send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,request,32u);
    for(unsigned i=0u;i<1000u&&radio.config.transfer->state==COMP_WBA_RECORDING_TRANSFER_IDLE;i++)radio_tick();
    assert(radio.config.transfer->state==COMP_WBA_RECORDING_TRANSFER_ACTIVE&&radio.pull.live&&!nor.erase_active);
    unsigned writes=f.writes,erases=f.erases;f.fail_read_data_once=true;
    for(unsigned i=0u;i<1000u&&comp_wba_recording_radio_busy(&radio);i++)radio_tick();
    assert(!f.fail_read_data_once&&!storage.poisoned&&mic&&saved_bytes>0u&&f.writes==writes&&f.erases==erases);
    for(unsigned block=0u;block<16u;block++) {
        int16_t samples[160];pcm(block+200u,samples);assert(comp_cont_recording_pcm(&engine,samples,160u));
        for(unsigned i=0u;i<160u;i++)poll();
    }
    assert(engine.stats.accepted_pcm_blocks==32u&&comp_wba_recording_pipeline_stop(&pipeline,91u));
    for(unsigned i=0u;i<10000u&&pipeline.state!=COMP_PIPE_FINISHED;i++)poll();
    assert(pipeline.state==COMP_PIPE_FINISHED&&!mic&&!storage.poisoned);
    puts("PASS_PARTIAL_LIVE_READ_FAILURE_KEEP_CAPTURE_SOFTWARE_ONLY");
}

static void partial_cross_page_read_failure(void)
{
    comp_segment_entry_t original=setup_radio();ready(56u);
    assert(comp_wba_recording_pipeline_start(&pipeline,91u)&&mic);
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    uint8_t request[32];saved_bytes=200u;sealed_request(&original,200u,request);
    send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,request,32u);
    for(unsigned i=0u;i<1000u&&radio.config.transfer->state==COMP_WBA_RECORDING_TRANSFER_IDLE;i++)radio_tick();
    for(unsigned i=0u;i<1000u&&!radio.pull.copied;i++)radio_tick();
    assert(radio.pull.copied>0u&&saved_bytes==200u&&!nor.erase_active&&mic);
    unsigned writes=f.writes,erases=f.erases;f.fail_read_data_once=true;
    for(unsigned i=0u;i<1000u&&comp_wba_recording_radio_busy(&radio);i++)radio_tick();
    assert(!f.fail_read_data_once&&!storage.poisoned&&saved_bytes==original.descriptor.encoded_length&&mic&&f.writes==writes&&f.erases==erases);
    for(uint32_t at=200u;at<saved_bytes;at++) {
        uint32_t logical=at;
        assert(saved[at]==f.bytes[DATA_BASE+original.extent_offset+256u+(logical/248u)*256u+logical%248u]);
    }
    int16_t samples[160];pcm(200u,samples);assert(comp_cont_recording_pcm(&engine,samples,160u));
    for(unsigned i=0u;i<160u;i++)poll();
    assert(comp_wba_recording_pipeline_stop(&pipeline,91u));
    for(unsigned i=0u;i<10000u&&pipeline.state!=COMP_PIPE_FINISHED;i++)poll();
    assert(pipeline.state==COMP_PIPE_FINISHED&&!mic&&!storage.poisoned);
    puts("PASS_CROSS_PAGE_FAILURE_RETRIES_EXACT_BYTES_KEEP_CAPTURE_SOFTWARE_ONLY");
}

static void overlap_tick(void)
{
    unsigned reads=f.reads,writes=f.writes;
    const comp_wba_recording_transfer_budget_t single={1u,1u,1u};
    link_owner.runtime.capture_active=mic;
    comp_link_poll_with_budget(&link_owner.link,f.now,NULL,NULL,&single);
    assert(f.reads-reads<=1u&&f.writes==writes);
}
static void consume_pull_overlap(bool legacy,unsigned interruption)
{
    bool disconnect=interruption==1u;
    comp_segment_entry_t first=setup_radio(),next={0};ready(56u);
    assert(comp_wba_recording_pipeline_start(&pipeline,91u));
    for(unsigned block=0u;block<36u;block++) {
        int16_t samples[160];pcm(block+200u,samples);assert(comp_cont_recording_pcm(&engine,samples,160u));
        for(unsigned i=0u;i<160u;i++)poll();
    }
    assert(comp_wba_recording_pipeline_stop(&pipeline,91u));
    for(unsigned i=0u;i<10000u&&pipeline.state!=COMP_PIPE_FINISHED;i++)poll();
    assert(pipeline.state==COMP_PIPE_FINISHED);
    for(uint8_t i=0u;i<64u;i++) {
        comp_segment_entry_t e;comp_segment_result_t result=comp_wba_segment_storage_entry(&storage,&catalog,i,&e);
        assert(result==COMP_SEG_OK||result==COMP_SEG_NOT_FOUND);
        if(result==COMP_SEG_OK&&e.descriptor.recording_id!=first.descriptor.recording_id){next=e;break;}
    }
    assert(next.descriptor.recording_id&&next.descriptor.encoded_length<=sizeof(saved));
    nor.config.transfer_timeout_ms=4u;
    /* This scenario deliberately holds an erase until the other file is
     * delivered. Use the production-sized timeout, not fixture make()'s100ms. */
    nor.config.sector_erase_timeout_ms=30000u;
    assert(comp_wba_segment_storage_reclaim_read_supported(&storage));
    assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    uint8_t request[32],proof[84];negotiation(request);
    if(!legacy) {
        request[3]|=0x80u;comp_rec_put32(request+28u,comp_rec_crc(request,28u));
        send(COMPANION_GATT_CHAR_RECORDING_CONTROL,request,32u);overlap_tick();
        assert(radio.negotiated==3u&&!memcmp(last_reply,request,32u));
    } else assert(radio.negotiated==1u);
    consumption_proof(&first,proof);f.automatic_erase=false;
    send(COMPANION_GATT_CHAR_DELETE_PRIVACY,proof,84u);
    for(unsigned i=0u;i<10000u&&!(nor.erase_active&&comp_segment_catalog_transfer_readable(&catalog));i++){poll();overlap_tick();}
    assert(nor.erase_active&&radio.consume_pending&&receipt_count==0u);
    uint32_t rejected=link_owner.link.rejected_writes;
    sealed_request(&first,0u,request);send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,request,32u);
    assert(link_owner.link.rejected_writes==rejected+1u&&radio.consume_pending&&receipt_count==0u);
    rejected=link_owner.link.rejected_writes;
    sealed_request(&next,0u,request);send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,request,32u);
    if(legacy) {
        assert(link_owner.link.rejected_writes==rejected+1u&&saved_bytes==0u&&receipt_count==0u);
        assert(!comp_link_heavy_io_allowed(&link_owner.link));
    } else {
        assert(link_owner.link.rejected_writes==rejected&&radio.consume_pending);
        assert(comp_link_heavy_io_allowed(&link_owner.link)); /* actual sequencer pump gate */
        blocked=2u;
        for(unsigned i=0u;i<10000u&&saved_bytes<(interruption?100u:next.descriptor.encoded_length);i++){poll();overlap_tick();}
        if(interruption==3u) {
            uint32_t before=link_owner.link.rejected_writes;sealed_request(&next,saved_bytes,request);
            send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,request,32u);assert(link_owner.link.rejected_writes==before);
            for(unsigned i=0u;i<10000u&&saved_bytes<next.descriptor.encoded_length;i++){poll();overlap_tick();}
        }
        if(!(saved_bytes>0u&&nor.erase_active&&radio.consume_pending&&receipt_count==0u))
            fprintf(stderr,"overlap saved=%lu erase=%u pending=%u receipts=%lu radio=%u transfer=%u pull=%u scan=%u catalog=%u consume=%u readable=%u page=%u allowed=%u retry=%u blocked=%u\n",
                (unsigned long)saved_bytes,(unsigned)nor.erase_active,(unsigned)radio.consume_pending,(unsigned long)receipt_count,
                (unsigned)radio.phase,(unsigned)radio.config.transfer->state,(unsigned)radio.pull.phase,(unsigned)radio.pull.scan,
                (unsigned)catalog.phase,(unsigned)pipeline.consume_phase,(unsigned)comp_segment_catalog_transfer_readable(&catalog),
                (unsigned)comp_wba_recording_pipeline_transfer_page_available(&pipeline),(unsigned)comp_wba_recording_radio_read_allowed(&radio),
                (unsigned)retry_bytes,blocked);
        assert(saved_bytes>0u&&nor.erase_active&&radio.consume_pending&&receipt_count==0u);
        assert(interruption==1u||interruption==2u||saved_bytes==next.descriptor.encoded_length);
        for(uint32_t at=0u;at<saved_bytes;at++)assert(saved[at]==f.bytes[DATA_BASE+next.extent_offset+256u+(at/248u)*256u+at%248u]);
    }
    if(disconnect) {
        comp_link_connection(&link_owner.link,false,false,f.now);
        assert(!radio.negotiated&&receipt_count==0u);
    }
    if(interruption==2u) {
        subscribe(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,false);
        assert(radio.consume_pending&&!storage.transfer_read_yield&&receipt_count==0u);
    }
    f.automatic_erase=true;
    for(unsigned i=0u;i<10000u&&comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_PENDING;i++) {
        poll();if(!disconnect)overlap_tick();
    }
    assert(comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_OK&&!nor.erase_active);
    if(disconnect) {
        connect_peer();negotiation(request);request[3]|=0x80u;comp_rec_put32(request+28u,comp_rec_crc(request,28u));
        send(COMPANION_GATT_CHAR_RECORDING_CONTROL,request,32u);overlap_tick();assert(radio.negotiated==3u);
        send(COMPANION_GATT_CHAR_DELETE_PRIVACY,proof,84u);
    }
    for(unsigned i=0u;i<1000u&&receipt_count==0u;i++)overlap_tick();
    assert(receipt_count==1u&&last_reply_bytes==84u&&!memcmp(last_reply,proof,84u));
    if(interruption==1u||interruption==2u) {
        if(interruption==2u)subscribe(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,true);
        sealed_request(&next,saved_bytes,request);send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,request,32u);
        for(unsigned i=0u;i<10000u&&saved_bytes<next.descriptor.encoded_length;i++)overlap_tick();
        assert(saved_bytes==next.descriptor.encoded_length);
    }
    comp_segment_entry_t retained=recovered_entry();assert(retained.descriptor.recording_id==next.descriptor.recording_id);
    assert(!storage.poisoned&&catalog.mounted);
    puts(legacy?"PASS_LEGACY_CONSUME_STAYS_SERIAL":"PASS_OPTIN_DIFFERENT_SEALED_PULL_OVERLAPS_RECLAIM_EXACT_PHYSICAL_RECEIPT_AND_RECONNECT");
}
static comp_segment_entry_t second_lookup_recording(void)
{
    ready(56u);assert(comp_wba_recording_pipeline_start(&pipeline,91u));
    for(unsigned block=0u;block<36u;block++) {
        int16_t samples[160];pcm(block,samples);assert(comp_cont_recording_pcm(&engine,samples,160u));
        for(unsigned i=0u;i<160u;i++)poll();
    }
    assert(comp_wba_recording_pipeline_stop(&pipeline,91u));
    for(unsigned i=0u;i<10000u&&pipeline.state!=COMP_PIPE_FINISHED;i++)poll();
    comp_segment_entry_t e;assert(pipeline.state==COMP_PIPE_FINISHED);
    assert(comp_wba_segment_storage_entry(&storage,&catalog,1u,&e)==COMP_SEG_OK);
    assert(e.descriptor.session_id==56u);return e;
}
static void lookup_tick(void)
{
    const comp_wba_recording_transfer_budget_t one={1u,1u,1u};
    unsigned reads=f.reads,writes=f.writes;
    comp_link_poll_with_budget(&link_owner.link,f.now,NULL,NULL,&one);
    assert(f.reads-reads<=1u&&f.writes==writes);
}
static void lookup_hint_scope(void)
{
    for(unsigned scenario=0u;scenario<5u;scenario++) {
        comp_segment_entry_t original=setup_radio(),target=second_lookup_recording();
        uint8_t untouched[4096];assert(original.reserved_bytes==sizeof(untouched));
        memcpy(untouched,f.bytes+DATA_BASE+original.extent_offset,sizeof(untouched));
        test_value_capacity=136u;assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
        uint8_t request[32],proof[84];sealed_request(&target,0u,request);consumption_proof(&target,proof);
        radio.pull.slot=scenario==1u?0u:scenario==2u?63u:1u;
        send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,request,32u);
        if(scenario==3u)catalog.generation++; /* stale generation retires hint */
        unsigned reads=f.reads;
        for(unsigned i=0u;i<100u&&radio.config.transfer->state==COMP_WBA_RECORDING_TRANSFER_IDLE;i++)lookup_tick();
        assert(radio.config.transfer->state!=COMP_WBA_RECORDING_TRANSFER_IDLE);
        assert(f.reads-reads==(scenario==1u?3u:scenario==2u||scenario==3u?2u:1u));
        for(unsigned i=0u;i<5000u&&comp_wba_recording_radio_busy(&radio);i++)lookup_tick();
        assert(saved_bytes==target.descriptor.encoded_length&&radio.pull.slot==1u);
        if(scenario==4u) {proof[48]^=1u;comp_rec_put32(proof+80u,comp_rec_crc(proof,80u));}
        if(scenario==1u)radio.pull.slot=0u;
        if(scenario==2u)radio.pull.slot=63u;
        send(COMPANION_GATT_CHAR_DELETE_PRIVACY,proof,84u);
        assert(radio.consume_pending&&pipeline.consume_scan==(128u|radio.pull.slot));
        reads=f.reads;unsigned erases=f.erases,writes=f.writes;
        poll();
        while(comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_PENDING&&!catalog.phase)poll();
        assert(f.reads-reads==(scenario==1u?3u:scenario==2u?2u:1u));
        assert(f.erases==erases&&f.writes==writes);
        if(scenario==4u) {
            assert(comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_BAD_ARGUMENT);
            assert(!memcmp(untouched,f.bytes+DATA_BASE+original.extent_offset,sizeof(untouched)));
            continue;
        }
        assert(pipeline.consume_scan==2u);
        /* A replay cannot replace the already accepted owner's cursor. */
        assert(comp_wba_recording_pipeline_consume_wire_hint(&pipeline,proof,0u)==COMP_SEG_PENDING);
        assert(pipeline.consume_scan==2u);
        for(unsigned i=0u;i<10000u&&!receipt_count;i++){poll();lookup_tick();}
        assert(receipt_count==1u&&!memcmp(proof,last_reply,84u));
        assert(!memcmp(untouched,f.bytes+DATA_BASE+original.extent_offset,sizeof(untouched)));
        comp_segment_entry_t retained;assert(comp_wba_segment_storage_entry(&storage,&catalog,0u,&retained)==COMP_SEG_OK);
        assert(retained.descriptor.recording_id==original.descriptor.recording_id);
    }
    puts("PASS_LOOKUP_HINT physical_row_rechecked=1 one_read_hit=1 wrong_empty_stale_fallback=1 consume_one_read=1 duplicate_owner_preserved=1 forged_SHA_no_erase=1 old_audio_unchanged=1");
}
static void directory_hint_scope(void)
{
    for(unsigned older=0;older<2;older++) {
        comp_segment_entry_t original=setup_radio(),latest=second_lookup_recording();
        directory_pages=0u;directory_starts=0u;
        test_value_capacity=509u;assert(comp_wba_recording_radio_set_value_capacity(&radio,509u));connect_peer();
        uint8_t directory[16]={2,0x20,3,0};comp_rec_put32(directory+8,97);
        unsigned writes=f.writes,erases=f.erases;
        send(COMPANION_GATT_CHAR_RECORDING_CONTROL,directory,16);
        for(unsigned i=0;i<1000u&&comp_wba_recording_radio_busy(&radio);i++)radio_tick();
        assert(!comp_wba_recording_radio_busy(&radio)&&directory_pages==2&&radio.pull.slot==1);
        assert(f.writes==writes&&f.erases==erases&&saved_bytes==0);
        uint8_t request[32];sealed_request(older?&original:&latest,0,request);
        unsigned reads=f.reads;send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,request,32);
        for(unsigned i=0;i<100u&&radio.config.transfer->state==COMP_WBA_RECORDING_TRANSFER_IDLE;i++)lookup_tick();
        assert(radio.config.transfer->state!=COMP_WBA_RECORDING_TRANSFER_IDLE);
        assert(f.reads-reads==(older?2u:1u));
        assert(f.writes==writes&&f.erases==erases);
    }
    puts("PASS_DIRECTORY_HINT no_extra_IO=1 no_payload_cache=1 latest_row_rechecked_once=1 older_selection_falls_back=1 no_mutation=1");
}
static void unsupported_overlap_negotiation(void)
{
    (void)setup_radio();assert(comp_wba_recording_radio_set_value_capacity(&radio,136u));connect_peer();
    uint8_t request[32],legacy[32];negotiation(legacy);memcpy(request,legacy,32u);request[3]|=0x80u;
    comp_rec_put32(request+28u,comp_rec_crc(request,28u));nor.info.jedec_id=UINT32_C(0x0b6018);
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,request,32u);radio_tick();
    assert(radio.negotiated==1u&&last_reply_bytes==32u&&!memcmp(last_reply,legacy,32u));
    puts("PASS_UNQUALIFIED_NOR_NORMALIZES_OVERLAP_OPTION_TO_EXPLICIT_LEGACY_ACK");
}
static void range_request(const comp_segment_entry_t *e,uint8_t out[96],uint32_t nonce,
    uint16_t first,uint16_t end,bool query)
{
    comp_range_plan_t plan;uint32_t begin,limit;
    assert(comp_range_plan(e,0u,query?0u:first,query?1u:end,nonce,&plan,&begin,&limit));
    memset(out,0,96u);memcpy(out,"CRG3",4u);comp_rec_put16(out+4u,3u);comp_rec_put16(out+6u,96u);
    memcpy(out+8u,e->descriptor.device_uid,12u);comp_rec_put64(out+20u,e->descriptor.format_epoch);
    comp_rec_put64(out+28u,e->descriptor.session_id);comp_rec_put32(out+36u,e->descriptor.segment_index);
    comp_rec_put32(out+40u,e->descriptor.recording_id);comp_rec_put32(out+44u,nonce);comp_rec_put32(out+52u,plan.descriptor_binding);
    if(!query){
        assert(saved_bytes>=limit);comp_rec_put16(out+48u,first);comp_rec_put16(out+50u,end);
        companion_sha256_t sha;companion_sha256_init(&sha);companion_sha256_update(&sha,saved+begin,limit-begin);
        companion_sha256_final(&sha,out+56u);out[88u]=1u;
    }
    comp_rec_put32(out+92u,comp_rec_crc(out,92u));
}
static void range_reclaim_dispatch(unsigned queued)
{
    init();comp_wba_pipeline_config_t cfg=pipeline.config;cfg.segment_frames=300u;cfg.extent_bytes=16384u;
    assert(comp_wba_recording_pipeline_init(&pipeline,&cfg));ready(55u);
    assert(comp_wba_recording_pipeline_start(&pipeline,91u));
    for(unsigned block=0u;block<400u;block++){
        int16_t samples[160];pcm(block,samples);assert(comp_cont_recording_pcm(&engine,samples,160u));
        for(unsigned i=0u;i<160u;i++)poll();
    }
    assert(comp_wba_recording_pipeline_stop(&pipeline,91u));
    for(unsigned i=0u;i<20000u&&pipeline.state!=COMP_PIPE_FINISHED;i++)poll();
    assert(pipeline.state==COMP_PIPE_FINISHED);comp_segment_entry_t original=recovered_entry();
    assert(original.descriptor.encoded_length>7688u&&original.descriptor.encoded_length<sizeof(saved));
    memset(&link_owner,0,sizeof(link_owner));memset(saved,0,sizeof(saved));
    saved_bytes=receipt_count=blocked=unsubscribed_consume_publish=0u;last_reply_bytes=retry_bytes=0u;
    comp_link_config_t link={&link_owner.runtime,NULL,NULL,&link_owner.features,radio_publish,NULL};
    assert(comp_link_init_segmented(&link_owner.link,&link,&radio,&pipeline,20u));test_value_capacity=509u;
    assert(comp_wba_recording_radio_set_value_capacity(&radio,509u));connect_peer();
    uint8_t negotiation_wire[32];negotiation(negotiation_wire);comp_rec_put16(negotiation_wire+2u,(uint16_t)(queued?0xe1fdu:0xc1fdu));
    comp_rec_put32(negotiation_wire+28u,comp_rec_crc(negotiation_wire,28u));
    send(COMPANION_GATT_CHAR_RECORDING_CONTROL,negotiation_wire,32u);radio_tick();assert(radio.negotiated==(queued?15u:7u));
    uint8_t command[96];range_request(&original,command,501u,0u,0u,true);
    unsigned writes=f.writes,erases=f.erases;send(COMPANION_GATT_CHAR_DELETE_PRIVACY,command,96u);
    for(unsigned i=0u;i<1000u&&radio.range_pending;i++){poll();lookup_tick();}
    assert(!radio.range_pending&&last_reply_bytes==60u&&!memcmp(last_reply,"CRR3",4u));
    assert(comp_rec_get32(last_reply+32u)==501u&&comp_rec_get32(last_reply+36u)==0u&&f.writes==writes&&f.erases==erases);
    uint8_t pull[32];sealed_request(&original,0u,pull);send(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,pull,32u);
    for(unsigned i=0u;i<2000u&&saved_bytes<3720u;i++){poll();lookup_tick();}
    assert(saved_bytes>=3720u&&saved_bytes<original.descriptor.encoded_length);
    /* Queue admission/reply ordering uses the complete real downloaded source.
     * The unqueued scenario below independently covers transfer/erase overlap;
     * neither test claims hardware timing or handset durability. */
    if(queued)for(unsigned i=0u;i<10000u&&saved_bytes<original.descriptor.encoded_length;i++)lookup_tick();
    range_request(&original,command,502u,0u,1u,false);send(COMPANION_GATT_CHAR_DELETE_PRIVACY,command,96u);
    assert(radio.range_pending);uint32_t before=saved_bytes;bool overlap=false;
    if(queued) {
        /* Freeze only consumer scheduling while the genuine receiver drains
         * the already selected original. No fabricated payload or receipt. */
        for(unsigned i=0u;i<1000u&&pipeline.consume.descriptor.encoded_length==0u;i++)poll();
        for(unsigned i=0u;i<10000u&&saved_bytes<original.descriptor.encoded_length;i++)lookup_tick();
        assert(saved_bytes==original.descriptor.encoded_length&&radio.range_pending&&receipt_count==0u);
        uint16_t used=(uint16_t)((((saved_bytes+247u)/248u+1u)*256u+4095u)/4096u);
        range_request(&original,command,503u,1u,used,false);
        uint8_t invalid[96];memcpy(invalid,command,96u);invalid[28]^=1u;comp_rec_put32(invalid+92u,comp_rec_crc(invalid,92u));
        erases=f.erases;send(COMPANION_GATT_CHAR_DELETE_PRIVACY,invalid,96u);
        assert(!radio.range_queue_count&&radio.range_pending&&f.erases==erases);
        if(queued==4u)command[92]^=1u; /* defer full validation, never physical authorization */
        send(COMPANION_GATT_CHAR_DELETE_PRIVACY,command,96u);assert(radio.range_queue_count==1u);
        send(COMPANION_GATT_CHAR_DELETE_PRIVACY,command,96u);assert(radio.range_queue_count==1u); /* no duplicate owner */
        uint8_t whole[84];consumption_proof(&original,whole);send(COMPANION_GATT_CHAR_DELETE_PRIVACY,whole,84u);
        assert(radio.range_queue_count==2u&&receipt_count==0u&&f.erases==erases);
        if(queued==4u){
            for(unsigned i=0u;i<20000u&&comp_wba_recording_radio_busy(&radio);i++){poll();lookup_tick();}
            assert(!radio.range_queue_count&&!radio.range_pending&&receipt_count==0u&&catalog.range_end[0]==1u);
            assert(last_reply_bytes==60u&&comp_rec_get32(last_reply+44u)==COMP_SEG_BAD_ARGUMENT);
            send(COMPANION_GATT_CHAR_DELETE_PRIVACY,whole,84u);
        }else if(queued>=2u) {
            if(queued==2u)comp_link_connection(&link_owner.link,false,false,f.now);
            else subscribe(COMPANION_GATT_CHAR_DELETE_PRIVACY,false);
            assert(radio.range_queue_count==0u);
            for(unsigned i=0u;i<20000u&&comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_PENDING;i++)poll();
            assert(comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_OK&&catalog.range_end[0]==1u&&receipt_count==0u);
            comp_segment_entry_t retained;assert(comp_segment_catalog_read(&catalog,0u,&retained)==COMP_SEG_OK);
            if(queued==2u)connect_peer();else subscribe(COMPANION_GATT_CHAR_DELETE_PRIVACY,true);
            for(unsigned i=0u;i<100u&&radio.range_pending;i++)lookup_tick();
            send(COMPANION_GATT_CHAR_DELETE_PRIVACY,whole,84u);
        }else{
            for(unsigned i=0u;i<20000u&&comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_PENDING;i++)poll();
            assert(comp_wba_recording_pipeline_consume_result(&pipeline)==COMP_SEG_OK);
            blocked=1u;lookup_tick();assert(radio.range_queue_count==2u&&receipt_count==0u);
            lookup_tick();assert(radio.range_queue_count==1u&&radio.range_pending);
        }
        for(unsigned i=0u;i<30000u&&!receipt_count;i++){poll();lookup_tick();}
        assert(receipt_count==1u&&!radio.range_queue_count&&!memcmp(whole,last_reply,84u));
        assert(comp_rec_crc(saved,saved_bytes)==original.descriptor.content_crc32);
        companion_sha256_t digest;uint8_t full[32];companion_sha256_init(&digest);companion_sha256_update(&digest,saved,saved_bytes);companion_sha256_final(&digest,full);
        assert(!memcmp(full,original.descriptor.sha256,32u));
        printf("PASS_QUEUED_RANGE real_original=1 queue_before_physical_reply=1 terminal_after_reclaim=1 exact_source_and_original=1 malformed_or_duplicate_not_queued=1 receipt_backpressure_preserves_queue=1 drop_mode=%u\n",queued);
        return;
    }
    for(unsigned i=0u;i<20000u&&(radio.range_pending||saved_bytes<original.descriptor.encoded_length);i++){
        poll();lookup_tick();if(nor.erase_active&&saved_bytes>before)overlap=true;
    }
    assert(overlap&&!radio.range_pending&&saved_bytes==original.descriptor.encoded_length);
    assert(comp_rec_get32(last_reply+32u)==502u&&comp_rec_get32(last_reply+36u)==502u&&last_reply[42u]==1u);
    assert(comp_rec_crc(saved,saved_bytes)==original.descriptor.content_crc32);
    companion_sha256_t sha;uint8_t hash[32];companion_sha256_init(&sha);companion_sha256_update(&sha,saved,saved_bytes);companion_sha256_final(&sha,hash);
    assert(!memcmp(hash,original.descriptor.sha256,32u));
    uint16_t used=(uint16_t)((((saved_bytes+247u)/248u+1u)*256u+4095u)/4096u);
    range_request(&original,command,503u,1u,used,false);send(COMPANION_GATT_CHAR_DELETE_PRIVACY,command,96u);
    for(unsigned i=0u;i<20000u&&radio.range_pending;i++){poll();lookup_tick();}
    assert(!radio.range_pending&&comp_rec_get32(last_reply+36u)==503u&&last_reply[42u]==used);
    erases=f.erases;uint8_t whole[84];consumption_proof(&original,whole);send(COMPANION_GATT_CHAR_DELETE_PRIVACY,whole,84u);
    for(unsigned i=0u;i<20000u&&!receipt_count;i++){poll();lookup_tick();}
    assert(receipt_count==1u&&f.erases==erases&&!memcmp(whole,last_reply,84u));
    puts("PASS_RANGE_RADIO_DISPATCH authenticated_explicit_opt_in=1 query_no_mutation=1 actual_Opus_CSP2_source=1 transfer_advances_during_physical_erase=1 independent_correlated60B_receipt=1 full_original_CRC_SHA=1 final_CRA2_no_duplicate_erase=1");
}
int COMP_RADIO_TEST_MAIN(int argc,char **argv)
{
    (void)setvbuf(stdout,NULL,_IONBF,0);
    if(argc==2&&!strcmp(argv[1],"range-reclaim")){range_reclaim_dispatch(0u);return 0;}
    if(argc==2&&!strcmp(argv[1],"queued-range")){range_reclaim_dispatch(1u);range_reclaim_dispatch(2u);range_reclaim_dispatch(3u);range_reclaim_dispatch(4u);return 0;}
    if(argc==2&&!strcmp(argv[1],"lookup-hint")){lookup_hint_scope();return 0;}
    if(argc==2&&!strcmp(argv[1],"directory-hint")){directory_hint_scope();return 0;}
    if(argc==2&&!strcmp(argv[1],"consume-pull-overlap")){consume_pull_overlap(true,0u);consume_pull_overlap(false,0u);consume_pull_overlap(false,1u);consume_pull_overlap(false,2u);consume_pull_overlap(false,3u);unsupported_overlap_negotiation();return 0;}
    if(argc==2&&!strcmp(argv[1],"calendar-directory")){calendar_directory_attribute_budget();return 0;}
    if(argc==2&&!strcmp(argv[1],"cross-page-read-failure")){partial_cross_page_read_failure();return 0;}
    if(argc==2&&!strcmp(argv[1],"live-read-active-capture")){transient_live_read_during_capture();return 0;}
    if(argc==2&&!strcmp(argv[1],"sealed-read-active-capture")){transient_sealed_read_during_capture(false,false);transient_sealed_read_during_capture(false,true);transient_sealed_read_during_capture(true,false);bounded_transient_read_failure();timed_read_failure(9u,0u,false);timed_read_failure(10u,0u,false);timed_read_failure(200u,UINT32_MAX-50u,false);timed_read_failure(9u,0u,true);timed_read_failure(10u,0u,true);timed_read_failure(200u,UINT32_MAX-50u,true);cumulative_read_failure_budget();return 0;}
    if(argc==2&&!strcmp(argv[1],"directory-read-active-capture")){directory_read_during_capture(false,false);directory_read_during_capture(true,false);directory_read_during_capture(false,true);bounded_directory_read_failure(0u);bounded_directory_read_failure(10u);return 0;}
    if(argc==2&&!strcmp(argv[1],"sealed-payload-failure")){sealed_payload_fault_releases_radio();return 0;}
    if(argc==2&&!strcmp(argv[1],"disconnected-invalid-consume")){disconnected_invalid_consume(false);disconnected_invalid_consume(true);return 0;}
    if(argc==2&&!strcmp(argv[1],"disconnected-completed-consume")){disconnected_completed_consume();return 0;}
    if(argc==2&&!strcmp(argv[1],"deferred-receipt")){deferred_receipt_without_subscription();unsubscribe_while_consuming();disconnect_after_receipt_prepared();unsubscribe_prepared_receipt();explicit_retry_supersedes_deferred_receipt();return 0;}
    if(argc==2&&!strcmp(argv[1],"reinitialized-consume")){disconnected_receipt_then_pipeline_reinit();return 0;}
    if(argc==2&&!strcmp(argv[1],"mic-stop-retry")){fault_stop_retries_transient_failure();fault_stop_retries_bounded();return 0;}
    if(argc==2&&!strcmp(argv[1],"consume-owner-failure")){directory_read_error_reply();consume_read_error_reply();failed_consume_keeps_pending_owner();consume_fault_stops_active_capture();return 0;}
    if(argc==2&&!strcmp(argv[1],"normal-segmented")){dispatch_security_and_reconnect();growing_tail_frames(false);finite_batch_interval();return 0;}
    if(argc==2&&!strcmp(argv[1],"release-failure")){discard_release_failure_retains_workspace(false,false);discard_release_failure_retains_workspace(false,true);discard_release_failure_retains_workspace(true,false);discard_release_failure_retains_workspace(true,true);return 0;}
    if(argc==2&&!strcmp(argv[1],"discard-workspace")){discard_workspace_lifetimes();return 0;}
    if(argc==2&&!strcmp(argv[1],"discard-cds3")){discard_product_dispatch();return 0;}
    if(argc==2&&!strcmp(argv[1],"selected-discard")){selected_discard_dispatch();discard_product_dispatch();discard_workspace_lifetimes();return 0;}
    if(argc==2&&!strcmp(argv[1],"large-packets")){large_packet_profiles();return 0;}
    if(argc==2&&!strcmp(argv[1],"active-resume")){active_sealed_resume();return 0;}
    if(argc==2&&!strcmp(argv[1],"capture-pair-sealed")){capture_pair_sealed();return 0;}
    if(argc==2&&!strcmp(argv[1],"capture-pair-tail")){growing_tail_frames(true);return 0;}
    if(argc==2&&!strcmp(argv[1],"dual-lane")){segmented_dual_lane();return 0;}
    if(argc==3&&!strcmp(argv[1],"pause-tail")){pause_tail_interop(argv[2]);return 0;}
    int result=radio_legacy_link_fixture_main(argc,argv);if(result)return result;
    dispatch_security_and_reconnect();growing_tail_frames(false);finite_batch_interval();return 0;
}
