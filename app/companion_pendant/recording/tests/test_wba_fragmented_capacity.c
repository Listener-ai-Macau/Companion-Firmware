#define COMP_PROFILE_FULL_NO_MAIN 1
#include "test_wba_profile_full_recovery.c"
static bool fragmented_record_hook(comp_runtime_t *runtime,bool start)
{
 if(!start)return comp_wba_recording_product_control(&product_rec,false,runtime->record_token);
 return comp_wba_recording_product_prepare_audio_profile(&product_rec,803u,1u,0u,runtime->record_token);
}
int main(void) {
 setvbuf(stdout,NULL,_IONBF,0);_set_error_mode(_OUT_TO_STDERR);_set_abort_behavior(0,_WRITE_ABORT_MSG|_CALL_REPORTFAULT);
 reset();nor=make();f.automatic_erase=true;mic=false;mic_starts=mic_stops=reports=0u;
 nor.config.wait_progress=wait_progress;nor.config.transfer=status_transfer;
 comp_wba_pipeline_config_t cfg={0};cfg.microphone=microphone;cfg.now_ms=now;cfg.segment_frames=SEGMENT_FRAMES;cfg.extent_bytes=EXTENT_BYTES;cfg.audio_profile=snapshot;
 assert(comp_wba_recording_product_bind(&product_rec,&nor,0u,24576u,DATA_BASE,3u*EXTENT_BYTES,49152u,device_uid,7u,&cfg,product_report));
 product_mount();comp_wba_recording_product_lease_result(&product_rec,true);
 profile_start(801u,91u);for(unsigned i=0u;i<8u;i++)block(i);assert(comp_wba_recording_product_control(&product_rec,false,91u));settle();
 comp_segment_entry_t first=product_entry(0u);
 profile_start(802u,92u);for(unsigned i=0u;i<8u;i++)block(i);assert(comp_wba_recording_product_control(&product_rec,false,92u));settle();
 comp_segment_entry_t middle=product_entry(1u);assert(first.extent_offset==0u&&middle.extent_offset==EXTENT_BYTES);
 memcpy(retained_extent,f.bytes+DATA_BASE+middle.extent_offset,EXTENT_BYTES);consume(&first);
 assert(product_rec.space.used==1u&&product_rec.space.unsynced==1u&&product_rec.space.largest_gap==EXTENT_BYTES&&product_rec.space.reserved_bytes==EXTENT_BYTES);
 assert(product_rec.space.allocatable_segments==2u);
 product_rec.pipeline.config.extent_bytes=2u*EXTENT_BYTES;memset(&product_rec.space,0,sizeof(product_rec.space));product_refresh_space();
 assert(product_rec.space.allocatable_segments==0u); /* Total free is two extents, but neither gap fits. */
 product_rec.pipeline.config.extent_bytes=EXTENT_BYTES;memset(&product_rec.space,0,sizeof(product_rec.space));product_refresh_space();
 assert(product_rec.space.allocatable_segments==2u);
 uint32_t physical=0u;assert(comp_wba_recording_product_workspace(&product_rec,EXTENT_BYTES,&physical));
 product_refresh_space();assert(product_rec.space.allocatable_segments==1u);
 assert(comp_wba_recording_product_workspace(&product_rec,0u,&physical));product_refresh_space();assert(product_rec.space.allocatable_segments==2u);

 /* Exercise the encrypted negotiated radio query and stale START fence using
  * the same production product/space snapshot, without a board or Type UI. */
 memset(&link_owner,0,sizeof(link_owner));last_reply_bytes=retry_bytes=0u;blocked=0u;
 comp_link_config_t link={&link_owner.runtime,NULL,NULL,&link_owner.features,radio_publish,NULL};
 assert(comp_link_init_segmented(&link_owner.link,&link,&radio,&product_rec.pipeline,136u));connect_peer();
 uint8_t request[32]={2u,0x26u};comp_rec_put32(request+4u,901u);memcpy(request+8u,device_uid,12u);
 comp_rec_put64(request+20u,7u);comp_rec_put32(request+28u,comp_rec_crc(request,28u));
 last_reply_bytes=0u;request[28]^=1u;send(COMPANION_GATT_CHAR_RECORDING_CONTROL,request,32u);radio_tick();
 assert(!last_reply_bytes&&!radio.capacity_token);request[28]^=1u;
 send(COMPANION_GATT_CHAR_RECORDING_CONTROL,request,32u);radio_tick();
 assert(last_reply_bytes==32u&&!memcmp(last_reply,"CSN1",4u)&&comp_rec_get32(last_reply+4u)==901u&&
        comp_rec_get32(last_reply+8u)==product_rec.catalog.generation&&last_reply[12]==2u&&
        !memcmp(last_reply+16u,device_uid,12u)&&comp_rec_get32(last_reply+28u)==comp_rec_crc(last_reply,28u));
 /* A temporary BLE scheduling block must not clear the START fence. */
 assert(!comp_wba_recording_radio_interval_hint(&radio,123u,false));
 assert(radio.capacity_token==901u);
 FILE *wire_file=fopen("capacity-wire.bin","wb");assert(wire_file&&fwrite(last_reply,1u,32u,wire_file)==32u&&!fclose(wire_file));
 /* A generation change must reject only this bound START before microphone or
  * catalog mutation. The old status/capability wire bytes stay untouched. */
 uint8_t saved_reply[32];memcpy(saved_reply,radio.config.transfer->packet,32u);
 unsigned old_starts=mic_starts,old_writes=f.writes;
 radio.config.transfer->packet[0]^=1u; /* shared packet reused/corrupt */
 uint32_t saved_generation=product_rec.catalog.generation;
 uint8_t startwire[56]={0};memcpy(startwire,"CMC3",4u);startwire[4]=3u;startwire[5]=1u;
 startwire[6]=2u;startwire[7]=1u;memcpy(startwire+8u,device_uid,12u);comp_rec_put64(startwire+20u,7u);
 comp_rec_put32(startwire+36u,901u);comp_rec_put32(startwire+40u,901u);comp_rec_put16(startwire+44u,200u);
 comp_rec_put32(startwire+52u,comp_rec_crc(startwire,52u));send(COMPANION_GATT_CHAR_MEETING_CONTROL,startwire,56u);
 assert(!mic&&mic_starts==old_starts&&f.writes==old_writes&&radio.capacity_token==901u);
 memcpy(radio.config.transfer->packet,saved_reply,32u);++product_rec.catalog.generation;
 send(COMPANION_GATT_CHAR_MEETING_CONTROL,startwire,56u);
 assert(!mic&&mic_starts==old_starts&&f.writes==old_writes&&radio.capacity_token==901u);
 send(COMPANION_GATT_CHAR_MEETING_CONTROL,startwire,56u);
 assert(!mic&&mic_starts==old_starts&&f.writes==old_writes&&radio.capacity_token==901u);
 uint8_t oldwire[52]={0};memcpy(oldwire,"CMC2",4u);oldwire[4]=2u;oldwire[5]=1u;oldwire[6]=2u;
 memcpy(oldwire+8u,device_uid,12u);comp_rec_put64(oldwire+20u,7u);comp_rec_put32(oldwire+36u,901u);
 comp_rec_put32(oldwire+40u,901u);comp_rec_put16(oldwire+44u,200u);comp_rec_put32(oldwire+48u,comp_rec_crc(oldwire,48u));
 send(COMPANION_GATT_CHAR_MEETING_CONTROL,oldwire,52u);
 assert(!mic&&mic_starts==old_starts&&f.writes==old_writes&&radio.capacity_token==901u);
 product_rec.catalog.generation=saved_generation;
 comp_link_test_record_hook=fragmented_record_hook;send(COMPANION_GATT_CHAR_MEETING_CONTROL,startwire,56u);
 assert(link_owner.record_calls==1u&&!radio.capacity_token);
 for(unsigned i=0u;i<20000u&&!comp_wba_recording_product_ready(&product_rec,link_owner.runtime.record_token);++i)product_tick();
 assert(comp_wba_recording_product_ready(&product_rec,link_owner.runtime.record_token));
 assert(comp_wba_recording_product_control(&product_rec,true,link_owner.runtime.record_token));
 comp_link_test_record_hook=NULL;
 unchanged_retained(&middle);printf("CAPACITY free=%u largest=%u segment=%u frames=%u used=%u\n",2u*EXTENT_BYTES,product_rec.space.largest_gap,EXTENT_BYTES,SEGMENT_FRAMES,product_rec.space.used);
 unsigned accepted=0u;while(mic&&accepted<4u*SEGMENT_FRAMES+32u)block(accepted++);assert(!mic);settle();
 assert(product_rec.capture.engine.stop_reason==COMP_CONT_STOP_FULL&&product_rec.space.used==3u);assert(product_rec.space.allocatable_segments==0u);unchanged_retained(&middle);
 unsigned n=0u;comp_segment_entry_t e[2];for(uint8_t i=0u;i<64u;i++)if(product_rec.catalog.slots[i]!=255u){comp_segment_entry_t x;assert(comp_wba_segment_storage_entry(&product_rec.storage,&product_rec.catalog,i,&x)==COMP_SEG_OK);if(x.descriptor.session_id==803u){assert(x.descriptor.segment_index<2u);e[x.descriptor.segment_index]=x;n++;}}
 assert(n==2u&&e[0].extent_offset==0u&&e[1].extent_offset==2u*EXTENT_BYTES);uint64_t samples=0u;unsigned ends=0u;inspect(&e[0],&samples,&ends,accepted);inspect(&e[1],&samples,&ends,accepted);
 assert(ends==1u&&samples==(uint64_t)accepted*160u+320u);
 /* Corrupt only the host NOR fixture: a CRC-valid owner crosses another
  * owner's boundary. The new count must be refused, not over-advertised. */
 uint8_t slot=255u;for(uint8_t i=0u;i<64u;i++)if(product_rec.catalog.slots[i]!=255u){
   comp_segment_entry_t item;assert(comp_wba_segment_storage_entry(&product_rec.storage,&product_rec.catalog,i,&item)==COMP_SEG_OK);
   if(item.descriptor.recording_id==middle.descriptor.recording_id)slot=i;}
 assert(slot!=255u);comp_segment_io_t io;assert(comp_segment_catalog_entry_io(&product_rec.catalog,slot,&io)==COMP_SEG_OK);
 uint8_t saved_row[256];memcpy(saved_row,f.bytes+io.address,256u);
 comp_rec_put32(f.bytes+io.address+12u,EXTENT_BYTES-4096u);
 comp_rec_put32(f.bytes+io.address+140u,comp_rec_crc(f.bytes+io.address,140u));
 memset(&product_rec.space,0,sizeof(product_rec.space));product_refresh_space();assert(product_rec.space.allocation_uncertain);
 uint32_t generation=0u;uint8_t slots=0u;
 assert(!product_rec.pipeline.config.capacity_snapshot(&product_rec.pipeline,&generation,&slots));
 memcpy(f.bytes+io.address,saved_row,256u);memset(&product_rec.space,0,sizeof(product_rec.space));product_refresh_space();
 assert(!product_rec.space.allocation_uncertain);
 /* CRC-valid duplicate and contained owners must be rejected too, including
  * when the nested extent ends before the earlier selected cursor. */
 comp_rec_put32(f.bytes+io.address+12u,0u);
 comp_rec_put32(f.bytes+io.address+140u,comp_rec_crc(f.bytes+io.address,140u));
 memset(&product_rec.space,0,sizeof(product_rec.space));product_refresh_space();
 assert(product_rec.space.allocation_uncertain);
 assert(!product_rec.pipeline.config.capacity_snapshot(&product_rec.pipeline,&generation,&slots));
 memcpy(f.bytes+io.address,saved_row,256u);
 comp_rec_put32(f.bytes+io.address+12u,4096u);comp_rec_put32(f.bytes+io.address+16u,4096u);
 comp_rec_put32(f.bytes+io.address+140u,comp_rec_crc(f.bytes+io.address,140u));
 memset(&product_rec.space,0,sizeof(product_rec.space));product_refresh_space();
 assert(product_rec.space.allocation_uncertain);
 assert(!product_rec.pipeline.config.capacity_snapshot(&product_rec.pipeline,&generation,&slots));
 memcpy(f.bytes+io.address,saved_row,256u);memset(&product_rec.space,0,sizeof(product_rec.space));
 product_refresh_space();assert(!product_rec.space.allocation_uncertain);
 radio.capacity_token=901u;comp_wba_recording_radio_connection(&radio,false);
 assert(!radio.capacity_token); /* Disconnect retires the old session fence. */
 printf("PASS_FIRMWARE_FRAGMENTED_TWO_SEGMENTS accepted=%u offsets=%u,%u retained=unchanged\n",accepted,e[0].extent_offset,e[1].extent_offset);return 0;
}
