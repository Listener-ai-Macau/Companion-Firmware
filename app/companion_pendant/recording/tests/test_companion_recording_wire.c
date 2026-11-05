#include "companion_recording_wire.h"
#include <assert.h>
#include <stdio.h>

static void hex(const uint8_t *p, size_t n)
{ putchar('"'); for (size_t i=0u;i<n;i++) printf("%02x",p[i]); putchar('"'); }
int main(void)
{
    /* Synthetic framing fixture; it is not microphone/audio quality evidence. */
    const uint8_t payload[]={0x43,0x4f,0x50,0x31,1,1,20,0,0x80,0x3e,0,0,1,0,0xf8};
    const uint8_t sha[32]=WIRE_FIXTURE_SHA;
    comp_rec_v2_descriptor_t d[3], decoded, invalid;
    comp_rec_v2_page_t decoded_page;
    uint8_t wire[3][COMP_REC_V2_DESCRIPTOR_BYTES], page[248], last[136], legacy[36];
    memset(d,0,sizeof(d));
    for (uint32_t i=0u;i<3u;i++) {
        d[i].recording_id=41u+i; d[i].format_epoch=UINT64_C(0x1122334455667788);
        d[i].session_id=UINT64_C(0x8877665544332211); d[i].segment_index=i;
        d[i].sample_offset=(uint64_t)i*320u; d[i].sample_count=320u;
        d[i].encoded_length=(uint32_t)sizeof(payload); d[i].content_crc32=comp_rec_crc(payload,sizeof(payload));
        memcpy(d[i].sha256,sha,32u); d[i].flags=COMP_REC_V2_SEALED; d[i].codec=3u; d[i].source_mode=1u;
        for (size_t j=0u;j<12u;j++) d[i].device_uid[j]=(uint8_t)(j+1u);
    }
    d[2].flags|=COMP_REC_V2_LAST; d[2].total_segments=3u;
    for (size_t i=0u;i<3u;i++) {
        assert(comp_rec_v2_encode(&d[i],wire[i],sizeof(wire[i])));
        assert(comp_rec_v2_decode(wire[i],sizeof(wire[i]),&decoded));
        assert(memcmp(&d[i],&decoded,sizeof(decoded))==0);
        for (size_t n=0u;n<sizeof(wire[i]);n++) assert(!comp_rec_v2_decode(wire[i],n,&decoded));
    }
    wire[0][60]^=1u; assert(!comp_rec_v2_decode(wire[0],sizeof(wire[0]),&decoded)); wire[0][60]^=1u;
    invalid=d[0]; invalid.format_epoch=0u; assert(!comp_rec_v2_encode(&invalid,page,sizeof(page)));
    invalid=d[0]; invalid.flags=0u; assert(!comp_rec_v2_valid(&invalid));
    invalid=d[0]; invalid.sample_count=640u; assert(!comp_rec_v2_valid(&invalid));
    invalid=d[0]; invalid.sample_offset=UINT64_MAX-255u; assert(!comp_rec_v2_valid(&invalid));
    invalid=d[2]; invalid.total_segments=4u; assert(!comp_rec_v2_valid(&invalid));
    /* A contiguous recording can cross the old 1024-segment boundary. */
    invalid=d[2]; invalid.segment_index=1024u; invalid.total_segments=1025u;
    assert(comp_rec_v2_encode(&invalid,page,sizeof(page)));
    assert(comp_rec_v2_decode(page,COMP_REC_V2_DESCRIPTOR_BYTES,&decoded));
    assert(decoded.segment_index==1024u && decoded.total_segments==1025u);
    invalid.segment_index=UINT32_MAX; invalid.total_segments=0u;
    assert(!comp_rec_v2_valid(&invalid));

    assert(comp_rec_v2_page_encode(9u,17u,0u,3u,d,2u,page,sizeof(page))==sizeof(page));
    assert(comp_rec_v2_page_encode(9u,17u,2u,3u,&d[2],1u,last,sizeof(last))==sizeof(last));
    assert(comp_rec_v2_page_decode(page,sizeof(page),&decoded_page));
    assert(decoded_page.count==2u && decoded_page.total==3u && decoded_page.entries[1].recording_id==42u);
    assert(comp_rec_v2_page_decode(last,sizeof(last),&decoded_page));
    for (size_t n=0u;n<sizeof(page);n++) assert(!comp_rec_v2_page_decode(page,n,&decoded_page));
    page[4]^=1u; assert(!comp_rec_v2_page_decode(page,sizeof(page),&decoded_page)); page[4]^=1u;
    {
        uint8_t untouched[248]; memset(untouched,0xa5,sizeof(untouched));
        assert(comp_rec_v2_page_encode(9u,0u,0u,3u,d,2u,untouched,sizeof(untouched))==0u);
        assert(comp_rec_v2_page_encode(9u,17u,0u,3u,d,3u,untouched,sizeof(untouched))==0u);
        assert(comp_rec_v2_page_encode(9u,17u,3u,3u,d,1u,untouched,sizeof(untouched))==0u);
        assert(!comp_rec_not_uniform(untouched,sizeof(untouched),0xa5u));
    }
    {
        comp_rec_v1_entry_t v1; memset(&v1,0,sizeof(v1));
        v1.recording_id=41u; v1.started_unix_s=1791234567u; v1.duration_ms=20u;
        v1.total_length=(uint32_t)sizeof(payload); v1.content_crc32=comp_rec_crc(payload,sizeof(payload));
        v1.codec=3u; v1.source_mode=1u; memcpy(v1.sha256_prefix,sha,8u);
        legacy[0]=1u; legacy[1]=1u; comp_rec_put16(legacy+2u,COMP_REC_V1_ENTRY_BYTES);
        assert(comp_rec_v1_encode(&v1,legacy+4u,sizeof(legacy)-4u));
    }
    printf("{\"schema\":\"companion.recording-wire.golden.v2\",\"fixtureSource\":\"synthetic-contract-only\",\"payloadHex\":");
    hex(payload,sizeof(payload)); printf(",\"v1Hex\":"); hex(legacy,sizeof(legacy));
    printf(",\"descriptorsHex\":[");
    for (size_t i=0u;i<3u;i++) { if (i!=0u) putchar(','); hex(wire[i],sizeof(wire[i])); }
    printf("],\"pagesHex\":["); hex(page,sizeof(page)); putchar(','); hex(last,sizeof(last)); printf("]}\n");
    return 0;
}
