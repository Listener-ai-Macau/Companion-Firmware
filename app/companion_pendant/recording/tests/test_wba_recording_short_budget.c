/* Changed short-budget packet boundaries, retained retries and original byte
 * integrity only. These software ports do not qualify radio performance. */
#define main retained_transfer_fixture_main
#include "test_wba_recording_transfer.c"
#undef main
#include "ble_packet_capacity.h"

int main(void)
{
    fixture_t fixture={0};
    memset(fixture.flash,0xff,sizeof(fixture.flash));
    fixture.heavy_io_allowed=true;
    comp_recording_journal_port_t port={flash_read,flash_program,flash_erase,crc32_port};
    comp_recording_journal_t journal;
    uint8_t original[3000];
    for(unsigned i=0u;i<sizeof(original);++i)original[i]=(uint8_t)(i*17u+3u);
    CHECK(comp_recording_journal_mount(&journal,&port,&fixture,FLASH_BYTES)==COMP_RECORDING_JOURNAL_OK,"mount");
    uint32_t id;
    CHECK(add_finalized(&journal,&fixture,original,sizeof(original),0x20u,&id),"sealed original");
    comp_wba_recording_transfer_config_t config={.journal=&journal,.notify=notify,.heavy_io_allowed=io_allowed,.context=&fixture};
    comp_wba_recording_transfer_t transfer;
    CHECK(comp_wba_recording_transfer_init(&transfer,&config),"init");
    comp_wba_recording_transfer_set_connected(&transfer,true);
    CHECK(comp_wba_recording_transfer_set_value_capacity(&transfer,509u),"actual max ATT value");
    companion_recording_adapter_request_t request={.schema_version=1u,
        .flags=COMP_WBA_RECORDING_TRANSFER_STREAM_ALL_FLAG,.recording_id=id,.requested_length=UINT16_MAX};
    CHECK(comp_wba_recording_transfer_start(&transfer,&request)==COMP_WBA_RECORDING_TRANSFER_OK,"start");
    transfer.compact_payload_limit=489u;
    comp_wba_recording_transfer_poll(&transfer);
    CHECK(transfer.packet_ready && transfer.packet_payload_length==489u,"prepared before budget change");
    uint8_t retained[COMP_WBA_RECORDING_TRANSFER_VALUE_BYTES];
    memcpy(retained,transfer.packet,transfer.packet_length);
    fixture.reject_next_notify=true;
    CHECK(comp_wba_recording_transfer_poll(&transfer)==COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED,"retained backpressure");
    transfer.compact_payload_limit=comp_v11_ble_bulk_compact_capacity(509u,251u,340u,2u,6u,1u);
    CHECK(transfer.compact_payload_limit==434u,"actual short budget limit");
    comp_wba_recording_transfer_poll(&transfer);
    CHECK(fixture.notification_count==1u && fixture.notification_lengths[0]==509u &&
        !memcmp(fixture.notifications[0],retained,509u) && transfer.next_offset==489u,
        "pending old packet immutable, accepted once");
    comp_wba_recording_transfer_poll(&transfer);
    CHECK(transfer.packet_ready && transfer.packet_payload_length==434u && transfer.packet_length==454u,
        "fresh sealed packet uses changed boundary");
    CHECK(drain(&transfer)==0,"complete changed original");
    uint32_t offset=0u;
    for(unsigned i=0u;i<fixture.notification_count;++i) {
        const uint8_t *packet=fixture.notifications[i];
        uint16_t n=get_le16(packet+2u);bool final=(packet[1]&1u)!=0u;
        uint32_t header=final?56u:20u;
        CHECK(get_le32(packet+12u)==offset && n<=sizeof(original)-offset,"exact range");
        CHECK(!memcmp(packet+header,original+offset,n),"same original bytes");
        CHECK(packet_crc(packet,sizeof(original))==get_le32(packet+(final?20u:16u)),"independent packet CRC");
        CHECK(fixture.notification_lengths[i]<=509u,"actual peer bound including final SHA");
        if(i>0u&&!final)CHECK(fixture.notification_lengths[i]==454u,"normal short budget value");
        if(final){uint8_t expected[32];fill_sha(expected,0x20u);CHECK(!memcmp(packet+24u,expected,32u),"final SHA metadata retained");}
        offset+=n;
    }
    CHECK(offset==sizeof(original) && comp_recording_journal_find(&journal,id)->sync_state==COMP_RECORDING_JOURNAL_UNSYNCED,
        "all original bytes, no consume");
    puts("PASS_SHORT_BUDGET_WIRE_RETRY_ORIGINAL_SOFTWARE_ONLY");
    return 0;
}
