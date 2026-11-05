#include "wba_recording_service.h"
#include "wba_recording_transfer.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

_Static_assert(COMP_WBA_RECORDING_PACKET_BYTES ==
                   COMPANION_OPUS16_MAX_PACKET + 2u,
               "recording service keeps exactly one bounded COP1 packet");

#define FLASH_BYTES (128u * 1024u)

typedef struct {
    uint8_t bytes[FLASH_BYTES];
    uint32_t now_ms;
    bool mic_active;
    bool read_allowed;
    bool reject_notify;
    bool invalid_packet;
    bool final_seen;
    uint32_t received_bytes;
    uint32_t packets;
    uint8_t received[16384];
    uint8_t final_sha[32];
    uint8_t wire[32768];
    uint32_t wire_bytes;
    comp_wba_recording_service_t *service;
} fixture_t;

static uint32_t le32(const uint8_t *p)
{ return (uint32_t)p[0]|((uint32_t)p[1]<<8u)|((uint32_t)p[2]<<16u)|((uint32_t)p[3]<<24u); }

static bool flash_read(void *ctx, uint32_t off, uint8_t *dst, uint32_t len)
{
    fixture_t *f = ctx;
    if (dst == NULL || off > FLASH_BYTES || len > FLASH_BYTES - off) return false;
    memcpy(dst, &f->bytes[off], len);
    return true;
}

static bool flash_program(void *ctx, uint32_t off, const uint8_t *src,
                          uint32_t len)
{
    fixture_t *f = ctx;
    if (src == NULL || off > FLASH_BYTES || len > FLASH_BYTES - off) return false;
    for (uint32_t i = 0u; i < len; ++i) {
        if ((f->bytes[off + i] & src[i]) != src[i]) return false;
        f->bytes[off + i] &= src[i];
    }
    return true;
}

static bool flash_erase(void *ctx, uint32_t off, uint32_t len)
{
    fixture_t *f = ctx;
    if (off > FLASH_BYTES || len > FLASH_BYTES - off ||
        (off % 4096u) != 0u || (len % 4096u) != 0u) return false;
    memset(&f->bytes[off], 0xFF, len);
    return true;
}

static uint32_t crc32_port(uint32_t seed, const uint8_t *data, uint32_t len)
{
    uint32_t crc = seed ^ 0xFFFFFFFFu;
    for (uint32_t i = 0u; i < len; ++i) {
        uint32_t value = (crc ^ data[i]) & 0xFFu;
        for (uint32_t bit = 0u; bit < 8u; ++bit) {
            value = (value >> 1) ^
                (0xEDB88320u & (uint32_t)(-(int32_t)(value & 1u)));
        }
        crc = (crc >> 8) ^ value;
    }
    return crc ^ 0xFFFFFFFFu;
}

static bool mic(void *ctx, bool enabled)
{
    ((fixture_t *)ctx)->mic_active = enabled;
    return true;
}

static uint32_t now_ms(void *ctx) { return ((fixture_t *)ctx)->now_ms; }
static void report(void *ctx, uint32_t token,
                   denzic_audio_recording_state_v1_t state, bool active)
{ (void)ctx; (void)token; (void)state; (void)active; }

static bool live(void *ctx,uint32_t id,comp_recording_journal_entry_t *entry)
{
    fixture_t *f=ctx;
    return comp_wba_recording_service_live_entry(f->service,entry) && entry->recording_id==id;
}
static bool heavy(void *ctx) { return !((fixture_t *)ctx)->mic_active; }
static bool readable(void *ctx) { return ((fixture_t *)ctx)->read_allowed; }
static bool notify(void *ctx,const uint8_t *packet,uint16_t size)
{
    fixture_t *f=ctx;
    uint32_t n=(uint32_t)packet[2]|((uint32_t)packet[3]<<8u),offset=le32(packet+12);
    uint32_t header=(packet[1]&1u)?56u:24u;
    if(f->reject_notify) {f->reject_notify=false;return false;}
    if(size!=header+n || offset!=f->received_bytes || n>192u ||
       offset+n>sizeof(f->received) || le32(packet+16)<offset+n ||
       crc32_port(crc32_port(0u,packet+4,16u),packet+header,n)!=le32(packet+20) ||
       f->wire_bytes+2u+size>sizeof(f->wire)) {
        f->invalid_packet=true;return false;
    }
    f->wire[f->wire_bytes++]=(uint8_t)size;f->wire[f->wire_bytes++]=(uint8_t)(size>>8u);
    memcpy(f->wire+f->wire_bytes,packet,size);f->wire_bytes+=size;
    memcpy(f->received+offset,packet+header,n);f->received_bytes+=n;++f->packets;
    if(packet[1]&1u) {f->final_seen=true;memcpy(f->final_sha,packet+24,32);}
    return true;
}
static int export_file(const char *base,const char *suffix,const void *bytes,size_t length)
{
    char path[1024];FILE *file;
    if(snprintf(path,sizeof(path),"%s%s",base,suffix)<0)return 0;
    file=fopen(path,"wb");
    if(file==NULL)return 0;
    size_t written=fwrite(bytes,1,length,file);
    return fclose(file)==0 && written==length;
}

static int fail(const char *message)
{
    fprintf(stderr, "FAIL_REAL_OPUS %s\n", message);
    return 2;
}

static bool short_packet_buffer_preserves_frame(void)
{
    companion_opus16_rt_t codec;
    int16_t pcm[COMPANION_OPUS16_FRAME_SAMPLES];
    uint8_t short_packet[COMPANION_OPUS16_MAX_PACKET + 1u];
    uint8_t packet[COMP_WBA_RECORDING_PACKET_BYTES];

    memset(&codec, 0, sizeof(codec));
    memset(pcm, 0, sizeof(pcm));
    memset(short_packet, 0xA5, sizeof(short_packet));
    if (!companion_opus16_rt_init(&codec)) return false;
    if (companion_opus16_rt_encode(&codec, pcm,
                                   COMPANION_OPUS16_FRAME_SAMPLES,
                                   short_packet, sizeof(short_packet), false) != 0u ||
        codec.pcm_fill != COMPANION_OPUS16_FRAME_SAMPLES ||
        codec.frames_encoded != 0u) {
        companion_opus16_rt_destroy(&codec);
        return false;
    }
    for (size_t i = 0u; i < sizeof(short_packet); ++i) {
        if (short_packet[i] != 0xA5u) {
            companion_opus16_rt_destroy(&codec);
            return false;
        }
    }
    const size_t encoded = companion_opus16_rt_flush(
        &codec, packet, sizeof(packet));
    const bool preserved = encoded > 2u && encoded <= sizeof(packet) &&
                           codec.pcm_fill == 0u && codec.frames_encoded == 1u;
    companion_opus16_rt_destroy(&codec);
    return preserved;
}

int main(int argc, char **argv)
{
    fixture_t fixture;
    comp_recording_journal_t journal;
    comp_recording_journal_port_t port = {
        flash_read, flash_program, flash_erase, crc32_port
    };
    comp_wba_recording_service_t service;
    comp_wba_recording_service_config_t config;
    comp_wba_recording_transfer_t transfer;
    comp_wba_recording_transfer_config_t transfer_config;
    companion_recording_adapter_request_t request={0};
    uint8_t list[248];
    uint32_t first_prefix=0u;
    bool disconnected=false,backpressure=false,prefix_exported=false;
    const comp_recording_journal_entry_t *entry;
    FILE *file;
    int16_t pcm[160];

    if (argc != 2) return fail("output path required");
    if (!short_packet_buffer_preserves_frame()) {
        return fail("short packet buffer advanced or lost a codec frame");
    }
    memset(&fixture, 0, sizeof(fixture));
    memset(fixture.bytes, 0xFF, sizeof(fixture.bytes));
    if (comp_recording_journal_mount(&journal, &port, &fixture,
                                     FLASH_BYTES) !=
        COMP_RECORDING_JOURNAL_OK) return fail("mount");
    memset(&config, 0, sizeof(config));
    config.journal = &journal;
    config.partition_base_address = COMP_WBA_RECORDING_MIN_PARTITION_BASE;
    config.reserve_bytes = 16u * 1024u;
    config.mic_control = mic;
    config.now_ms = now_ms;
    config.report = report;
    config.context = &fixture;
    config.foreground_budget_ms = 10u;
    fixture.service=&service;fixture.read_allowed=true;
    transfer_config=(comp_wba_recording_transfer_config_t){&journal,notify,heavy,&fixture,live,readable};
    if (!comp_wba_recording_service_init(&service, &config) ||
        !comp_wba_recording_service_prepare_port(&service, 101u)) {
        return fail("init/prepare");
    }
    if(!comp_wba_recording_transfer_init(&transfer,&transfer_config))return fail("transfer init");
    comp_wba_recording_transfer_set_connected(&transfer,true);
    if(comp_wba_recording_transfer_build_list(&transfer,list,sizeof(list))!=4u || list[1]!=0u)
        return fail("uncommitted preparation exposed in list");
    for (uint32_t guard = 0u;
         service.state != COMP_WBA_RECORDING_READY && guard < 16u; ++guard) {
        (void)comp_wba_recording_service_poll(&service);
    }
    if (!comp_wba_recording_service_control_port(&service, true, 101u)) {
        return fail("start");
    }
    /* Deterministic multi-tone-like signal.  This is a codec self-test input,
     * never presented as microphone evidence. */
    for (uint32_t half = 0u; half < 400u; ++half) {
        for (uint32_t i = 0u; i < 160u; ++i) {
            const uint32_t phase = (half * 160u + i) % 160u;
            pcm[i] = phase < 80u ? (int16_t)(phase * 180) :
                                   (int16_t)((159u - phase) * 180);
        }
        if (!comp_wba_recording_service_pcm(&service, pcm, 160u, 16000u)) {
            return fail("pcm rejected");
        }
        for (uint32_t work = 0u; service.ring_count != 0u && work < 4u; ++work) {
            (void)comp_wba_recording_service_poll(&service);
        }
        if (service.state != COMP_WBA_RECORDING_CAPTURING) {
            return fail("capture fault");
        }
        (void)comp_wba_recording_service_poll(&service);
        comp_recording_journal_entry_t prefix;
        if(comp_wba_recording_service_live_entry(&service,&prefix)) {
            const comp_recording_journal_entry_t *stored=comp_wba_recording_service_entry(&service);
            if(prefix.total_length!=service.committed_bytes || prefix.total_length>service.stats.committed_bytes ||
               stored->total_length!=0u || stored->sync_state!=COMP_RECORDING_JOURNAL_WRITING)
                return fail("live snapshot altered durable journal or exposed RAM stage");
            if(comp_wba_recording_transfer_build_list(&transfer,list,sizeof(list))!=36u ||
               list[17]!=1u || le32(list+20)!=prefix.total_length)
                return fail("Type live wire prefix is absent");
            if(!first_prefix)first_prefix=prefix.total_length;
            if((transfer.state==COMP_WBA_RECORDING_TRANSFER_IDLE ||
                transfer.state==COMP_WBA_RECORDING_TRANSFER_COMPLETE) &&
               prefix.total_length>fixture.received_bytes) {
                request.schema_version=1u;request.flags=4u;request.recording_id=prefix.recording_id;
                request.byte_offset=fixture.received_bytes;
                if(comp_wba_recording_transfer_start(&transfer,&request)!=COMP_WBA_RECORDING_TRANSFER_OK)
                    return fail("live window start");
            }
            if(!backpressure && transfer.state==COMP_WBA_RECORDING_TRANSFER_ACTIVE) {
                (void)comp_wba_recording_transfer_poll(&transfer); /* read only */
                uint32_t prior=fixture.received_bytes;
                fixture.read_allowed=false;
                (void)comp_wba_recording_transfer_poll(&transfer);
                if(fixture.received_bytes!=prior || transfer.next_offset!=prior)
                    return fail("capture budget did not defer a prepared notification");
                fixture.read_allowed=true;fixture.reject_notify=true;
                (void)comp_wba_recording_transfer_poll(&transfer);
                if(transfer.state!=COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED || transfer.next_offset!=prior)
                    return fail("notification backpressure advanced offset");
                backpressure=true;
            }
            for(unsigned step=0;step<2u;++step)(void)comp_wba_recording_transfer_poll(&transfer);
            if(fixture.invalid_packet || fixture.final_seen ||
               memcmp(fixture.received,fixture.bytes+prefix.payload_offset,fixture.received_bytes)!=0)
                return fail("live chunk CRC/content/final semantics");
            if(!disconnected && fixture.received_bytes>=384u) {
                uint32_t cursor=fixture.received_bytes;
                comp_wba_recording_transfer_set_connected(&transfer,false);
                if(!fixture.mic_active || service.state!=COMP_WBA_RECORDING_CAPTURING)
                    return fail("disconnect interrupted capture");
                comp_wba_recording_transfer_set_connected(&transfer,true);
                request.byte_offset=cursor;
                if(prefix.total_length>cursor &&
                   comp_wba_recording_transfer_start(&transfer,&request)!=COMP_WBA_RECORDING_TRANSFER_OK)
                    return fail("absolute-offset live resume");
                disconnected=true;
            }
            if(!prefix_exported && fixture.received_bytes>=1024u) {
                if(!export_file(argv[1],".prefix.cop1",fixture.received,fixture.received_bytes) ||
                   !export_file(argv[1],".live-wire.bin",fixture.wire,fixture.wire_bytes) ||
                   !export_file(argv[1],".active-list.bin",list,36u))return fail("live artifacts");
                prefix_exported=true;
            }
        }
    }
    if(!backpressure || !disconnected || !prefix_exported || service.committed_bytes<=first_prefix)
        return fail("live progress/interruptions untested");
    if(comp_wba_recording_transfer_acknowledge(&transfer,service.entry.recording_id,
        fixture.received_bytes,fixture.final_sha)==COMP_WBA_RECORDING_TRANSFER_OK)
        return fail("active recording acknowledged");
    /* Freeze a live window, then finalize while it is in flight. It must keep
     * its prefix size and never acquire a finalized-file SHA or final flag. */
    comp_wba_recording_transfer_cancel(&transfer);fixture.received_bytes=0u;request.byte_offset=0u;
    if(comp_wba_recording_transfer_start(&transfer,&request)!=COMP_WBA_RECORDING_TRANSFER_OK)
        return fail("last live snapshot");
    uint32_t frozen=transfer.snapshot_length;
    if (!comp_wba_recording_service_control_port(&service, false, 101u)) {
        return fail("stop");
    }
    for (uint32_t guard = 0u;
         service.state != COMP_WBA_RECORDING_TRANSFER_READY && guard < 64u;
         ++guard) {
        (void)comp_wba_recording_service_poll(&service);
    }
    entry = comp_wba_recording_service_entry(&service);
    if (service.state != COMP_WBA_RECORDING_TRANSFER_READY || entry == NULL ||
        entry->sync_state != COMP_RECORDING_JOURNAL_UNSYNCED ||
        entry->codec != 3u || entry->duration_ms != 4000u ||
        memcmp(&fixture.bytes[entry->payload_offset], "COP1", 4u) != 0) {
        return fail("final metadata");
    }
    for(unsigned guard=0;guard<200u && transfer.state!=COMP_WBA_RECORDING_TRANSFER_COMPLETE;++guard)
        (void)comp_wba_recording_transfer_poll(&transfer);
    if(fixture.received_bytes!=frozen || fixture.final_seen || fixture.invalid_packet)
        return fail("finalize changed the in-flight live snapshot");
    if(comp_wba_recording_transfer_build_list(&transfer,list,sizeof(list))!=36u || list[17]!=0u)
        return fail("Type finalized wire UNSYNCED must be 0");
    if(!export_file(argv[1],".final-list.bin",list,36u))return fail("final list artifact");
    fixture.received_bytes=0u;fixture.wire_bytes=0u;request.byte_offset=0u;
    if(comp_wba_recording_transfer_start(&transfer,&request)!=COMP_WBA_RECORDING_TRANSFER_OK)
        return fail("final pull");
    for(unsigned guard=0;guard<200u && transfer.state!=COMP_WBA_RECORDING_TRANSFER_COMPLETE;++guard)
        (void)comp_wba_recording_transfer_poll(&transfer);
    if(fixture.received_bytes!=entry->total_length || !fixture.final_seen || fixture.invalid_packet ||
       memcmp(fixture.received,fixture.bytes+entry->payload_offset,entry->total_length)!=0 ||
       memcmp(fixture.final_sha,entry->sha256,32)!=0)return fail("final pull bytes/SHA");
    if(!export_file(argv[1],".wire.bin",fixture.wire,fixture.wire_bytes))return fail("wire export");
    file = fopen(argv[1], "wb");
    if (file == NULL || fwrite(&fixture.bytes[entry->payload_offset], 1u,
                               entry->total_length, file) !=
                            entry->total_length || fclose(file) != 0) {
        return fail("write artifact");
    }
    printf("PASS_WBA_RECORDING_SERVICE_REAL_OPUS bytes=%lu duration_ms=%lu sha256=",
           (unsigned long)entry->total_length,
           (unsigned long)entry->duration_ms);
    for (uint32_t i = 0u; i < 32u; ++i) printf("%02x", entry->sha256[i]);
    printf("\n");
    return 0;
}
