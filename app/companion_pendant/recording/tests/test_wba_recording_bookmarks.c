/* Production recorder/NOR/Opus software model, never physical-board evidence. */
#define COMP_CAPACITY_TEST_MAIN prior_pause_capacity_fixture_main
#include "test_wba_recording_pause_capacity.c"

static void marked_start(void)
{
    reset();nor=make();f.automatic_erase=true;mic=false;mic_starts=mic_stops=reports=0u;
    comp_wba_pipeline_config_t cfg={0};cfg.microphone=microphone;cfg.now_ms=now;
    cfg.segment_frames=6000u;cfg.extent_bytes=262144u;
    assert(comp_wba_recording_product_bind(&product_rec,&nor,0u,24576u,DATA_BASE,786432u,
        49152u,device_uid,7u,&cfg,product_report));
    product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
    assert(comp_wba_recording_product_prepare_bookmarked(&product_rec,101u,1u,0u,91u));
    for(unsigned i=0u;i<20000u&&!comp_wba_recording_product_ready(&product_rec,91u);i++)product_tick();
    assert(comp_wba_recording_product_ready(&product_rec,91u)&&comp_wba_recording_product_control(&product_rec,true,91u));
    blocks=0u;
}
static void tail_bookmark_boundary(bool pending)
{
    static comp_wba_recording_radio_t reader;
    static comp_wba_recording_transfer_t tx;
    if(pending) {
        memset(&tx,0,sizeof(tx));
        comp_wba_recording_radio_config_t cfg={&product_rec.pipeline,&tx,radio_publish,NULL,136u};
        assert(comp_wba_recording_radio_init(&reader,&cfg));
        comp_wba_recording_radio_connection(&reader,true);
        uint8_t hello[32];negotiation(hello);
        assert(comp_wba_recording_radio_write(&reader,COMPANION_GATT_CHAR_RECORDING_CONTROL,hello,32u,true));
        comp_wba_recording_radio_poll(&reader,NULL,NULL,NULL);
        /* The metadata guard, not an unrelated busy writer, must refuse it. */
        assert(reader.negotiated&&!product_rec.capture.engine.writer.phase&&
            comp_wba_recording_radio_read_allowed(&reader));
    }
    uint8_t request[32]={2u,0x23u};comp_rec_put32(request+4u,pending?800u:801u);
    comp_rec_put64(request+8u,7u);comp_rec_put64(request+16u,101u);
    assert(comp_wba_recording_radio_write(&reader,COMPANION_GATT_CHAR_RECORDING_CONTROL,request,32u,true));
    comp_wba_recording_radio_poll(&reader,NULL,NULL,NULL);
    if(pending)assert(last_reply_bytes==16u&&!memcmp(last_reply,"CRE2",4u)&&comp_rec_get32(last_reply+12u)==COMP_SEG_PENDING);
    else assert(last_reply_bytes==80u&&!memcmp(last_reply,"CLP2",4u)&&last_reply[74u]==15u&&!last_reply[75u]);
}
static void mark(uint32_t nonce)
{
    comp_cont_recording_t *r=&product_rec.capture.engine;uint32_t control=r->command_sequence;
    assert(!comp_wba_recording_product_bookmark(&product_rec,92u,nonce));
    assert(comp_wba_recording_product_bookmark(&product_rec,91u,nonce));
    assert(comp_wba_recording_product_bookmark(&product_rec,91u,nonce));
    assert(comp_wba_recording_product_bookmark_result(&product_rec,91u,nonce)==COMP_SEG_PENDING);
    if(nonce==100u)tail_bookmark_boundary(true);
    assert(!comp_wba_recording_product_bookmark(&product_rec,91u,nonce+1u));
    for(unsigned i=0u;i<20000u&&comp_wba_recording_product_bookmark_result(&product_rec,91u,nonce)==COMP_SEG_PENDING;i++)product_tick();
    assert(comp_wba_recording_product_bookmark_result(&product_rec,91u,nonce)==COMP_SEG_OK);
    if(nonce==100u)tail_bookmark_boundary(false);
    assert(r->command_sequence==control&&!r->stats.overflows&&!r->stats.budget_failures);
    assert(comp_wba_recording_product_bookmark(&product_rec,91u,nonce));
    assert(!comp_wba_recording_product_bookmark(&product_rec,91u,nonce-1u));
}
static size_t verify_marked(const comp_segment_entry_t *e,size_t *audio_at,unsigned *marks,unsigned *controls)
{
    comp_segment_audio_port_t port=comp_wba_segment_storage_audio_port(&product_rec.storage);size_t bytes=0u;
    for(uint32_t page=0u;bytes<e->descriptor.encoded_length;page++) {
        uint8_t raw[256],length=0u;comp_segment_result_t result;
        do {f.now+=2u;result=comp_segment_audio_read_page(&port,e,DATA_BASE,page,raw,&length);}while(result==COMP_SEG_PENDING);
        assert(result==COMP_SEG_OK&&bytes+length<=sizeof(actual_raw));memcpy(actual_raw+bytes,raw,length);bytes+=length;
    }
    assert(bytes==e->descriptor.encoded_length&&actual_raw[4]==4u&&actual_raw[7]==7u);
    companion_sha256_t h;uint8_t digest[32];companion_sha256_init(&h);companion_sha256_update(&h,actual_raw,bytes);companion_sha256_final(&h,digest);
    assert(!memcmp(digest,e->descriptor.sha256,32u)&&comp_rec_crc(actual_raw,bytes)==e->descriptor.content_crc32);
    size_t frames=0u;
    for(size_t at=12u;at<bytes;) {
        if(actual_raw[at]==255u){at++;continue;}
        if(!actual_raw[at]) {
            if(!memcmp(actual_raw+at+2u,"CDB1",4u)) {
                comp_rec_codec_boundary_t boundary={0};
                assert(comp_rec_codec_boundary_decode(actual_raw+at,bytes-at,&boundary));
                if(boundary.kind==COMP_REC_CODEC_CONFIG)assert(at==12u&&boundary.encoded_samples==e->descriptor.sample_offset);
                else assert(at%248u==0u&&boundary.valid_source_samples==(uint64_t)blocks*160u&&
                    boundary.encoded_samples==((uint64_t)*audio_at/42u+1u)*320u);
                at+=32u;continue;
            }
            comp_rec_timeline_event_t event={0};assert(comp_rec_timeline_decode(actual_raw+at,bytes-at,&event));
            assert(at%248u==0u&&event.sample_offset==e->descriptor.sample_offset+frames*320u);
            if(event.kind==COMP_REC_TIMELINE_BOOKMARK){(*marks)++;assert(event.sequence==*marks);}
            else {(*controls)++;assert(event.sequence==*controls);}
            at+=32u;continue;
        }
        assert(at+42u<=bytes&&*audio_at+42u<=expected_bytes&&!memcmp(actual_raw+at,expected_audio+*audio_at,42u));
        at+=42u;*audio_at+=42u;frames++;
    }
    assert(frames*320u==e->descriptor.sample_count);
    comp_segment_entry_t writing=*e;writing.state=COMP_SEG_WRITING;
    writing.descriptor.sample_count=0u;writing.descriptor.encoded_length=0u;
    writing.descriptor.sample_count=writing.descriptor.encoded_length=0u;
    writing.descriptor.flags=writing.descriptor.sync_state=0u;writing.descriptor.total_segments=0u;
    comp_segment_audio_recovery_t recovered={0};uint8_t page[256];
    assert(comp_segment_audio_recover_begin(&recovered,&port,&writing,DATA_BASE,page)==COMP_SEG_PENDING);
    comp_segment_result_t result=COMP_SEG_PENDING;
    for(unsigned i=0u;i<10000u&&result==COMP_SEG_PENDING;i++){f.now+=2u;result=comp_segment_audio_recover_poll(&recovered);}
    uint32_t n=0u,count=0u,crc=0u;
    assert(result==COMP_SEG_OK&&comp_segment_audio_recovered(&recovered,&n,&count,&crc,digest));
    assert(n==bytes&&count==frames&&crc==e->descriptor.content_crc32&&!memcmp(digest,e->descriptor.sha256,32u));
    return bytes;
}
static void exact_reference(void)
{
    companion_opus16_rt_t encoder;assert(companion_opus16_rt_init_rate_frame(&encoder,16000u,20u));
    expected_bytes=0u;int16_t samples[160];uint8_t packet[402];
    for(unsigned i=0u;i<blocks;i++) {
        pcm(i,samples);size_t n=companion_opus16_rt_encode(&encoder,samples,160u,packet,sizeof(packet),false);
        assert(expected_bytes+n<=sizeof(expected_audio));memcpy(expected_audio+expected_bytes,packet,n);expected_bytes+=n;
    }
    size_t n=companion_opus16_rt_finish_exact(&encoder,packet,sizeof(packet));assert(n==42u);
    assert(expected_bytes+n<=sizeof(expected_audio));memcpy(expected_audio+expected_bytes,packet,n);expected_bytes+=n;
    companion_opus16_rt_destroy(&encoder);
}
static void marks_pause_stop(void)
{
    marked_start();audio_frames(4u);mark(100u);change_pause(true);mark(101u);change_pause(false);audio_frames(4u);
    assert(comp_wba_recording_product_bookmark(&product_rec,91u,102u));finish();exact_reference();
    assert(comp_wba_recording_product_bookmark_result(&product_rec,91u,102u)==COMP_SEG_OK);
    comp_segment_entry_t e=product_entry(0u);size_t at=0u;unsigned marks=0u,controls=0u;
    (void)verify_marked(&e,&at,&marks,&controls);
    assert(at==expected_bytes&&marks==3u&&controls==2u&&mic_starts==2u&&mic_stops==2u);
    puts("PASS offline marks:independent nonce/sequence,durable result,paused mark,STOP drains pending mark,unchanged Opus and recovery; software only");
}
static void queued_pcm_and_shortened_roll(const char *output)
{
    marked_start();comp_cont_recording_t *r=&product_rec.capture.engine;
    for(unsigned i=0u;i<7u;i++){int16_t samples[160];pcm(blocks++,samples);assert(comp_wba_recording_product_pcm(&product_rec,samples,160u,16000u));}
    mark(200u);audio_frames(1u);
    for(unsigned i=1u;i<16u;i++){audio_frames(4u);mark(200u+i);}
    uint32_t limit=r->active_frame_limit;assert(limit<6000u);
    while(r->active.descriptor.segment_index==0u)audio_frames(1u);
    assert(r->active.descriptor.sample_offset==(uint64_t)limit*320u);audio_frames(4u);mark(216u);finish();exact_reference();
    comp_segment_entry_t ds[2]={product_entry(0u),product_entry(1u)};
    assert(ds[1].descriptor.sample_offset==ds[0].descriptor.sample_count&&ds[1].descriptor.flags&COMP_REC_V2_LAST);
    FILE *file=fopen(output,"wb");assert(file);assert(fwrite("CMB4",1u,4u,file)==4u);
    uint8_t size[4];comp_rec_put32(size,2u);assert(fwrite(size,1u,4u,file)==4u);
    size_t at=0u;unsigned marks=0u,controls=0u;
    for(unsigned i=0u;i<2u;i++) {
        size_t bytes=verify_marked(&ds[i],&at,&marks,&controls);uint8_t wire[112];assert(comp_rec_v2_encode(&ds[i].descriptor,wire,sizeof(wire)));
        comp_rec_put32(size,(uint32_t)bytes);assert(fwrite(size,1u,4u,file)==4u);
        assert(fwrite(wire,1u,sizeof(wire),file)==sizeof(wire));assert(fwrite(actual_raw,1u,bytes,file)==bytes);
    }
    const uint8_t header[12]={'C','O','P','1',1u,1u,20u,0u,0x80u,0x3eu,0u,0u};
    comp_rec_put32(size,(uint32_t)expected_bytes+12u);assert(fwrite(size,1u,4u,file)==4u);
    assert(fwrite(header,1u,sizeof(header),file)==sizeof(header));assert(fwrite(expected_audio,1u,expected_bytes,file)==expected_bytes);assert(!fclose(file));
    assert(at==expected_bytes&&marks==17u&&!controls&&r->bookmark_sequence==17u);
    assert(!r->stats.overflows&&!r->stats.budget_failures&&mic_starts==1u&&mic_stops==1u);
    printf("PASS offline marks:queued PCM/half packet,17marks across shortened %u-frame segment,exact successor/recovery,uncut Opus bytes,CMB3 fixture; software only\n",limit);
}
int main(int argc,char **argv)
{
    assert(argc==2);marks_pause_stop();queued_pcm_and_shortened_roll(argv[1]);return 0;
}
