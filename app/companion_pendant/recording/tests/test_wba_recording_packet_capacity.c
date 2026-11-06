/* Reuse storage/CRC ports for affected ATT sizing, retained retries and raw
 * integrity. These software ports do not exercise controller fragmentation. */
#define main retained_transfer_fixture_main
#include "test_wba_recording_transfer.c"
#undef main
#include "ble_packet_capacity.h"
#include "ble_mtu.h"

/* The real segmented NOR port can yield halfway through a large packet.
 * Its destination, offset and byte count must stay fixed until READ_OK. */
static const uint8_t *split_source;
static const comp_recording_journal_t *split_journal;
static struct {uint8_t *out;uint32_t id,offset,bytes;bool pending;} split_read;
static bool split_metadata(void *context,uint32_t id,comp_recording_journal_entry_t *out)
{
    (void)context;
    const comp_recording_journal_entry_t *entry=comp_recording_journal_find(split_journal,id);
    if(!entry)return false;
    *out=*entry;return true;
}
static comp_wba_transfer_read_result_t split_backend_read(void *context,uint32_t id,
    uint32_t offset,uint8_t *out,uint32_t bytes)
{
    (void)context;
    if(!split_read.pending){
        split_read.out=out;split_read.id=id;split_read.offset=offset;split_read.bytes=bytes;split_read.pending=true;
        memcpy(out,split_source+offset,bytes/2u);return COMP_WBA_TRANSFER_READ_WAIT;
    }
    if(split_read.out!=out||split_read.id!=id||split_read.offset!=offset||split_read.bytes!=bytes)
        return COMP_WBA_TRANSFER_READ_ERROR;
    memcpy(out+bytes/2u,split_source+offset+bytes/2u,bytes-bytes/2u);
    split_read.pending=false;return COMP_WBA_TRANSFER_READ_OK;
}

int main(void)
{
    comp_v11_ble_mtu_t att;
    comp_v11_ble_mtu_open(&att,UINT32_MAX-499u);
    CHECK(att.mtu==23u && comp_v11_ble_mtu_value_capacity(&att)==20u,"default until actual exchange event");
    CHECK(comp_v11_ble_mtu_notifications_allowed(&att),"default bearer may notify before exchange request");
    CHECK(!comp_v11_ble_mtu_due(&att,UINT32_MAX,true,true) &&
          comp_v11_ble_mtu_due(&att,0u,true,true),"MTU delay handles wrapped zero deadline");
    CHECK(!comp_v11_ble_mtu_due(&att,1u,false,true) &&
          !comp_v11_ble_mtu_due(&att,1u,true,false),"authorization and foreground slot required");
    comp_v11_ble_mtu_requested(&att,0u,0x93u,true);
    CHECK(!comp_v11_ble_mtu_due(&att,999u,true,true) &&
          comp_v11_ble_mtu_due(&att,1000u,true,true),"busy command gets one delayed retry");
    comp_v11_ble_mtu_requested(&att,1000u,0u,false);
    CHECK(!comp_v11_ble_mtu_notifications_allowed(&att),"accepted exchange holds notifications without consuming prepared bytes");
    CHECK(att.mtu==23u && !comp_v11_ble_mtu_due(&att,9000u,true,true),"accepted request is not negotiated or repeatedly sent");
    CHECK(!comp_v11_ble_mtu_agreed(&att,22u,251u) && att.mtu==23u,"bad exchange value rejected");
    CHECK(comp_v11_ble_mtu_agreed(&att,517u,251u) &&
          att.mtu==251u && comp_v11_ble_mtu_value_capacity(&att)==248u,"larger peer agrees local maximum");
    CHECK(comp_v11_ble_mtu_notifications_allowed(&att),"actual exchange response releases notifications");
    comp_v11_ble_mtu_open(&att,0u);
    comp_v11_ble_mtu_requested(&att,500u,0x93u,true);
    comp_v11_ble_mtu_requested(&att,1500u,0x93u,true);
    CHECK(!comp_v11_ble_mtu_due(&att,50000u,true,true),"two transient rejections cannot become a per-file loop");
    comp_v11_ble_mtu_open(&att,0u);
    comp_v11_ble_mtu_requested(&att,500u,0x0cu,false);
    CHECK(!comp_v11_ble_mtu_due(&att,50000u,true,true),"unsupported exchange is not retried");
    comp_v11_ble_mtu_open(&att,0u);
    comp_v11_ble_mtu_requested(&att,500u,0u,false);
    CHECK(!comp_v11_ble_mtu_refused(&att,0u) && !comp_v11_ble_mtu_notifications_allowed(&att),"success cannot masquerade as exchange response");
    CHECK(comp_v11_ble_mtu_refused(&att,6u) && comp_v11_ble_mtu_notifications_allowed(&att) && att.mtu==23u &&
          !comp_v11_ble_mtu_due(&att,50000u,true,true),"peer refusal restores default bearer without another exchange");
    CHECK(comp_v11_ble_mtu_agreed(&att,139u,251u) && comp_v11_ble_mtu_value_capacity(&att)==136u,"actual smaller peer accepted");
    CHECK(comp_v11_ble_single_ll_compact_capacity(251u,340u,2u)==43u,"diagnostic340us single-PDU estimate");
    CHECK(comp_v11_ble_single_ll_compact_capacity(251u,965u,2u)==199u,"diagnostic965us single-PDU estimate");
    CHECK(comp_v11_ble_single_ll_compact_capacity(251u,1590u,2u)==224u,"diagnostic full2M PDU");
    CHECK(comp_v11_ble_single_ll_compact_capacity(80u,965u,2u)==53u,"diagnostic octets also constrain one PDU");
    CHECK(comp_v11_ble_single_ll_compact_capacity(0u,0u,0u)==0u &&
          comp_v11_ble_single_ll_compact_capacity(27u,328u,1u)==0u &&
          comp_v11_ble_single_ll_compact_capacity(251u,2120u,1u)==224u,"unknown versus actual1M airtime");
    CHECK(comp_v11_ble_compact_capacity(248u)==228u &&
          comp_v11_ble_compact_capacity(509u)==489u &&
          comp_v11_ble_compact_capacity(136u)==116u &&
          comp_v11_ble_compact_capacity(20u)==0u,"ATT bound independent of single-PDU estimate");
    fixture_t fixture;
    memset(&fixture,0,sizeof(fixture));
    memset(fixture.flash,0xff,sizeof(fixture.flash));
    fixture.heavy_io_allowed=true;
    comp_recording_journal_port_t port={flash_read,flash_program,flash_erase,crc32_port};
    comp_recording_journal_t journal;
    uint8_t original[1000];
    for(unsigned i=0u;i<sizeof(original);++i)original[i]=(uint8_t)(i*17u+3u);
    CHECK(comp_recording_journal_mount(&journal,&port,&fixture,FLASH_BYTES)==COMP_RECORDING_JOURNAL_OK,"mount");
    uint32_t id;
    CHECK(add_finalized(&journal,&fixture,original,sizeof(original),0x20u,&id),"sealed original");
    comp_wba_recording_transfer_config_t config={.journal=&journal,.notify=notify,.heavy_io_allowed=io_allowed,.context=&fixture};
    comp_wba_recording_transfer_t transfer;
    CHECK(comp_wba_recording_transfer_init(&transfer,&config),"init");
    comp_wba_recording_transfer_set_connected(&transfer,true);
    companion_recording_adapter_request_t request={.schema_version=1u,
        .flags=COMP_WBA_RECORDING_TRANSFER_STREAM_ALL_FLAG,.recording_id=id,.requested_length=UINT16_MAX};
    CHECK(comp_wba_recording_transfer_start(&transfer,&request)==COMP_WBA_RECORDING_TRANSFER_OK,"start");
    transfer.compact_payload_limit=199u;
    comp_wba_recording_transfer_poll(&transfer);
    CHECK(transfer.packet_ready && transfer.packet_payload_length==199u,"first packet fits negotiated capacity");
    uint8_t retained[COMP_WBA_RECORDING_TRANSFER_VALUE_BYTES];
    memcpy(retained,transfer.packet,transfer.packet_length);
    fixture.reject_next_notify=true;
    CHECK(comp_wba_recording_transfer_poll(&transfer)==COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED,"retain failed notify");
    transfer.compact_payload_limit=43u;
    comp_wba_recording_transfer_poll(&transfer);
    CHECK(fixture.notification_count==1u && memcmp(fixture.notifications[0],retained,219u)==0 &&
          transfer.next_offset==199u,"capacity change cannot rewrite cached retry or advance twice");
    comp_wba_recording_transfer_poll(&transfer);
    CHECK(transfer.packet_payload_length==43u,"next fresh packet applies lower capacity");
    comp_wba_recording_transfer_poll(&transfer);
    transfer.compact_payload_limit=199u;
    CHECK(drain(&transfer)==0,"finish adaptive original");
    uint32_t offset=0u;
    for(unsigned i=0u;i<fixture.notification_count;++i) {
        const uint8_t *packet=fixture.notifications[i];
        uint16_t length=get_le16(packet+2u);
        bool final=(packet[1]&1u)!=0u;
        uint32_t header=final?56u:20u;
        CHECK(get_le32(packet+12u)==offset && packet_crc(packet,sizeof(original))==get_le32(packet+(final?20u:16u)),"offset and independent CRC");
        CHECK(memcmp(packet+header,original+offset,length)==0,"same original bytes despite changed packet boundaries");
        if(final) {uint8_t expected[32];fill_sha(expected,0x20u);CHECK(memcmp(packet+24u,expected,32u)==0,"final SHA retained");}
        offset+=length;
    }
    CHECK(offset==sizeof(original) && comp_recording_journal_find(&journal,id)->sync_state==COMP_RECORDING_JOURNAL_UNSYNCED,"all bytes retained, no consume");
    const uint16_t capacities[]={136u,244u,248u};
    for(unsigned cap=0u;cap<sizeof(capacities)/sizeof(capacities[0]);cap++) {
        fixture.notification_count=0u;
        comp_wba_recording_transfer_set_connected(&transfer,false);
        comp_wba_recording_transfer_set_connected(&transfer,true);
        CHECK(comp_wba_recording_transfer_set_value_capacity(&transfer,capacities[cap]),"set actual ATT value between windows");
        request.byte_offset=0u;transfer.compact_payload_limit=224u;
        CHECK(comp_wba_recording_transfer_start(&transfer,&request)==COMP_WBA_RECORDING_TRANSFER_OK,"start MTU-bounded original");
        CHECK(!comp_wba_recording_transfer_set_value_capacity(&transfer,136u==capacities[cap]?244u:136u),"cannot resize active retry window");
        CHECK(drain(&transfer)==0,"complete smaller and maximum MTU");
        offset=0u;
        for(unsigned i=0u;i<fixture.notification_count;i++) {
            const uint8_t *packet=fixture.notifications[i];bool final=(packet[1]&1u)!=0u;
            uint32_t header=final?56u:20u;uint16_t n=get_le16(packet+2u);
            CHECK(fixture.notification_lengths[i]<=capacities[cap],"normal AND final notifications obey actual MTU");
            CHECK(get_le32(packet+12u)==offset && memcmp(packet+header,original+offset,n)==0 &&
                  packet_crc(packet,sizeof(original))==get_le32(packet+(final?20u:16u)),"byte offsets and CRC survive MTU negotiation");
            if(final){uint8_t expected[32];fill_sha(expected,0x20u);CHECK(!memcmp(packet+24u,expected,32u),"final SHA survives smaller MTU");}
            offset+=n;
        }
        CHECK(offset==sizeof(original),"no file byte lost to packet resizing");
    }
    comp_wba_recording_transfer_set_connected(&transfer,false);
    comp_wba_recording_transfer_set_connected(&transfer,true);
    CHECK(comp_wba_recording_transfer_set_value_capacity(&transfer,20u),"keep truthful default capacity");
    uint32_t reads_before=fixture.read_calls;
    CHECK(comp_wba_recording_transfer_start(&transfer,&request)==COMP_WBA_RECORDING_TRANSFER_BAD_STATE &&
          fixture.read_calls==reads_before,"unnegotiated 23B MTU cannot enter payload I/O");
    CHECK(comp_wba_recording_transfer_set_value_capacity(&transfer,248u),"restore qualified capacity before next window");
    fixture.notification_count=0u;
    comp_wba_recording_transfer_set_connected(&transfer,false);
    comp_wba_recording_transfer_set_connected(&transfer,true);
    request.byte_offset=231u;
    transfer.compact_payload_limit=199u;
    CHECK(comp_wba_recording_transfer_start(&transfer,&request)==COMP_WBA_RECORDING_TRANSFER_OK && drain(&transfer)==0,"resume at byte offset independent of packet size");
    CHECK(get_le32(fixture.notifications[0]+12u)==231u &&
          memcmp(fixture.notifications[0]+20u,original+231u,199u)==0,"unaligned resumed original");
    /* Same sealed original under a short LL budget must retain the normal ATT
     * reference packet. Then a genuinely smaller ATT bearer must limit each
     * notification, including its larger final SHA header. No consumption. */
    for(unsigned pass=0u;pass<2u;++pass) {
        uint16_t value_bytes=pass==0u?248u:136u;
        fixture.notification_count=0u;
        comp_wba_recording_transfer_set_connected(&transfer,false);
        comp_wba_recording_transfer_set_connected(&transfer,true);
        CHECK(comp_wba_recording_transfer_set_value_capacity(&transfer,value_bytes),"actual ATT capacity");
        request.byte_offset=0u;
        transfer.compact_payload_limit=comp_v11_ble_compact_capacity(value_bytes);
        CHECK(comp_wba_recording_transfer_start(&transfer,&request)==COMP_WBA_RECORDING_TRANSFER_OK,"reference same sealed original");
        comp_wba_recording_transfer_poll(&transfer);
        CHECK(transfer.packet_payload_length==(pass==0u?224u:116u),"ATT chooses application size, not short LL estimate");
        fixture.reject_next_notify=true;
        CHECK(comp_wba_recording_transfer_poll(&transfer)==COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED &&
              transfer.next_offset==0u,"reference backpressure preserves byte cursor");
        CHECK(drain(&transfer)==0,"reference complete without missing original");
        CHECK(fixture.notification_count==(pass==0u?5u:9u),"same bytes require fewer host notifications at normal ATT size");
        offset=0u;
        for(unsigned i=0u;i<fixture.notification_count;++i) {
            const uint8_t *packet=fixture.notifications[i];
            uint16_t length=get_le16(packet+2u);
            bool final=(packet[1]&1u)!=0u;
            uint32_t header=final?56u:20u;
            CHECK(fixture.notification_lengths[i]<=value_bytes &&
                  get_le32(packet+12u)==offset && get_le32(packet+8u)==i &&
                  packet_crc(packet,sizeof(original))==get_le32(packet+(final?20u:16u)),"actual ATT bound, contiguous sequence and independentCRC");
            CHECK(memcmp(packet+header,original+offset,length)==0,"reference raw bytes unchanged");
            if(final) {uint8_t expected[32];fill_sha(expected,0x20u);CHECK(memcmp(packet+24u,expected,32u)==0,"reference finalSHA unchanged");}
            offset+=length;
        }
        CHECK(offset==sizeof(original) && comp_recording_journal_find(&journal,id)->sync_state==COMP_RECORDING_JOURNAL_UNSYNCED,"reference receipt does not consume original");
    }
    fixture.notification_count=0u;split_source=original;split_journal=&journal;memset(&split_read,0,sizeof(split_read));
    config.journal=NULL;
    const comp_wba_recording_transfer_backend_t split_backend={split_metadata,split_backend_read};
    CHECK(comp_wba_recording_transfer_init_backend(&transfer,&config,&split_backend),"asynchronous segmented port");
    comp_wba_recording_transfer_set_connected(&transfer,true);
    CHECK(comp_wba_recording_transfer_set_value_capacity(&transfer,509u),"actual large ATT value");
    transfer.compact_payload_limit=489u;request.byte_offset=0u;
    CHECK(comp_wba_recording_transfer_start(&transfer,&request)==COMP_WBA_RECORDING_TRANSFER_OK,"start split NOR read");
    CHECK(comp_wba_recording_transfer_poll(&transfer)==COMP_WBA_RECORDING_TRANSFER_ACTIVE&&split_read.pending&&!transfer.packet_ready,"first NOR slice yields");
    transfer.compact_payload_limit=475u;
    CHECK(comp_wba_recording_transfer_poll(&transfer)==COMP_WBA_RECORDING_TRANSFER_ACTIVE&&transfer.packet_ready&&transfer.packet_payload_length==489u,
          "capacity update must preserve a partially read packet's byte count and destination");
    comp_wba_recording_transfer_poll(&transfer);
    CHECK(transfer.next_offset==489u,"publish the unchanged assembled packet once");
    comp_wba_recording_transfer_poll(&transfer);
    CHECK(split_read.pending&&split_read.bytes==475u,"next packet adopts the new measured capacity");
    CHECK(drain(&transfer)==0,"complete dynamic capacity change without reconnect");
    offset=0u;
    for(unsigned i=0u;i<fixture.notification_count;++i){
        const uint8_t *packet=fixture.notifications[i];uint16_t n=get_le16(packet+2u);bool final=(packet[1]&1u)!=0u;
        CHECK(get_le32(packet+12u)==offset&&get_le32(packet+8u)==i&&packet_crc(packet,sizeof(original))==get_le32(packet+(final?20u:16u)),"split read retains offset, sequence and CRC");
        CHECK(!memcmp(packet+(final?56u:20u),original+offset,n),"split read original unchanged");offset+=n;
    }
    CHECK(offset==sizeof(original)&&transfer.stats.storage_errors==0u,"no I/O fault or lost bytes from radio negotiation");
    puts("PASS_ATT_REFERENCE_PAYLOAD_CRC_RETRY_AND_BYTE_RESUME_SOFTWARE_ONLY_NO_RADIO_FRAGMENTATION_OR_SPEED_PROOF");
    return 0;
}
