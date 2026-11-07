/* Explicit synthetic upload fixture, generated with the production media codec.
 * Host-only. Never linked into app/boot/resources or represented as microphone
 * evidence. The caller controls the narrowly bounded developer NOR writes. */
#include "companion_segment_audio.h"
#include "wba_storage_layout.h"
#include <stdio.h>
#include <stdlib.h>

static uint8_t media[COMP_WBA_NOR_TOTAL_BYTES];
static uint8_t payload[2u*1024u*1024u];
#define REQUIRE(x) do {if(!(x)){fprintf(stderr,"fixture failure line%u: %s\n",(unsigned)__LINE__,#x);exit(1);}}while(0)
static bool rd(void *ctx,uint32_t at,uint8_t *p,uint32_t n)
{(void)ctx;if(at>sizeof(media)||n>sizeof(media)-at)return false;memcpy(p,media+at,n);return true;}
static bool wr(void *ctx,uint32_t at,const uint8_t *p,uint32_t n)
{
    (void)ctx;if(at>sizeof(media)||n>sizeof(media)-at||at/256u!=(at+n-1u)/256u)return false;
    for(uint32_t i=0u;i<n;i++)if((media[at+i]&p[i])!=p[i])return false;
    for(uint32_t i=0u;i<n;i++)media[at+i]&=p[i];return true;
}
static bool erase(void *ctx,uint32_t at,uint32_t n,uint32_t *done)
{(void)ctx;if(at%4096u||n<4096u||at>sizeof(media)-4096u)return false;memset(media+at,255,4096u);*done=4096u;return true;}
static comp_segment_result_t ar(void *c,uint32_t a,uint8_t *p,uint32_t n)
{return rd(c,a,p,n)?COMP_SEG_OK:COMP_SEG_IO_ERROR;}
static comp_segment_result_t aw(void *c,uint32_t a,const uint8_t *p,uint32_t n)
{return wr(c,a,p,n)?COMP_SEG_OK:COMP_SEG_IO_ERROR;}
static comp_segment_result_t finish(comp_segment_catalog_t *c,comp_segment_result_t r)
{for(unsigned i=0u;i<200000u&&r==COMP_SEG_PENDING;i++)r=comp_segment_catalog_poll(c);return r;}
static void audio_finish(comp_segment_audio_t *a)
{comp_segment_result_t r=COMP_SEG_PENDING;for(unsigned i=0u;i<10u&&r==COMP_SEG_PENDING;i++)r=comp_segment_audio_poll(a);REQUIRE(r==COMP_SEG_OK);}
static void save(const char *path,const uint8_t *p,uint32_t n)
{FILE *f=fopen(path,"wb");REQUIRE(f);REQUIRE(fwrite(p,1u,n,f)==n);REQUIRE(fclose(f)==0);}
int main(int argc,char **argv)
{
    REQUIRE(argc==8); /* payload, catalog, framed audio, epoch, uid, id, session */
    FILE *f=fopen(argv[1],"rb");REQUIRE(f);REQUIRE(fread(payload,1u,sizeof(payload),f)==sizeof(payload));REQUIRE(fgetc(f)==EOF);REQUIRE(fclose(f)==0);
    REQUIRE(memcmp(payload,"COP1\x02\x01\x14\x01\x80\x3e\x00\x00",12u)==0);
    uint64_t epoch=strtoull(argv[4],NULL,16),session=strtoull(argv[7],NULL,16);
    uint32_t id=(uint32_t)strtoul(argv[6],NULL,10);uint8_t uid[12];REQUIRE(strlen(argv[5])==24u);
    for(unsigned i=0u;i<12u;i++){char hex[3]={argv[5][i*2u],argv[5][i*2u+1u],0};uid[i]=(uint8_t)strtoul(hex,NULL,16);}
    memset(media,255,sizeof(media));comp_segment_catalog_t c;comp_segment_port_t cp={rd,wr,erase,NULL,0u};
    REQUIRE(finish(&c,comp_segment_catalog_mount_begin(&c,&cp,COMP_WBA_NOR_SEGMENT_CATALOG_A,
        COMP_WBA_NOR_SEGMENT_CATALOG_B,COMP_WBA_NOR_RECORDING_BASE,COMP_WBA_NOR_RECORDING_DATA_BYTES,uid,epoch))==COMP_SEG_UNFORMATTED);
    comp_segment_result_t format=comp_segment_catalog_format_blank_begin(&c);
    REQUIRE(format==COMP_SEG_PENDING);
    /* A distinct development ID avoids reusing old captured recording keys.
     * Both developer banks are replaced together; persistent epoch/allocator,
     * settings, layout roots, pairing NVM and static resources are untouched. */
    c.next_id=id; /* Persist the starting ID in the root before its first write. */
    REQUIRE(finish(&c,format)==COMP_SEG_OK);
    comp_segment_entry_t e={0};e.state=COMP_SEG_WRITING;e.descriptor.recording_id=id;
    e.descriptor.format_epoch=epoch;e.descriptor.session_id=session;e.descriptor.codec=3u;
    e.descriptor.source_mode=2u;memcpy(e.descriptor.device_uid,uid,12u);
    uint32_t pages=((uint32_t)sizeof(payload)+247u)/248u;
    e.reserved_bytes=((pages+1u)*256u+4095u)&~4095u;
    REQUIRE(finish(&c,comp_segment_catalog_put_begin(&c,&e))==COMP_SEG_OK);
    uint8_t scratch[256];comp_segment_audio_t a={0};comp_segment_audio_port_t ap={ar,aw,NULL};
    REQUIRE(comp_segment_audio_prepare_begin(&a,&ap,&e,COMP_WBA_NOR_RECORDING_BASE,scratch)==COMP_SEG_PENDING);audio_finish(&a);
    for(uint32_t offset=0u;offset<sizeof(payload);){uint8_t n=(uint8_t)(sizeof(payload)-offset>248u?248u:sizeof(payload)-offset);
        REQUIRE(comp_segment_audio_append_begin(&a,payload+offset,n)==COMP_SEG_PENDING);audio_finish(&a);offset+=n;}
    comp_segment_audio_recovery_t recovery={0};
    comp_segment_result_t r=comp_segment_audio_recover_begin(&recovery,&ap,&e,COMP_WBA_NOR_RECORDING_BASE,scratch);
    for(unsigned i=0u;i<200000u&&r==COMP_SEG_PENDING;i++)r=comp_segment_audio_recover_poll(&recovery);
    uint32_t bytes,frames,crc;uint8_t hash[32];REQUIRE(r==COMP_SEG_OK);
    REQUIRE(comp_segment_audio_recovered(&recovery,&bytes,&frames,&crc,hash));
    REQUIRE(bytes==sizeof(payload)&&frames==49931u&&crc==comp_rec_crc(payload,sizeof(payload)));
    e.state=COMP_SEG_UNSYNCED;e.descriptor.encoded_length=bytes;e.descriptor.sample_count=(uint64_t)frames*320u;
    e.descriptor.content_crc32=crc;memcpy(e.descriptor.sha256,hash,32u);e.descriptor.flags=COMP_REC_V2_SEALED|COMP_REC_V2_LAST;
    e.descriptor.total_segments=1u;e.descriptor.sync_state=1u;
    REQUIRE(finish(&c,comp_segment_catalog_put_begin(&c,&e))==COMP_SEG_OK);
    comp_segment_catalog_t mounted;REQUIRE(finish(&mounted,comp_segment_catalog_mount_begin(&mounted,&cp,c.banks[0],c.banks[1],c.data_base,c.data_bytes,uid,epoch))==COMP_SEG_OK);
    comp_segment_entry_t got;REQUIRE(comp_segment_catalog_read(&mounted,0u,&got)==COMP_SEG_OK);
    REQUIRE(got.descriptor.recording_id==id&&got.descriptor.encoded_length==sizeof(payload)&&memcmp(got.descriptor.sha256,hash,32u)==0&&mounted.next_id==id+1u);
    uint8_t descriptor[112];REQUIRE(comp_rec_v2_encode(&got.descriptor,descriptor,sizeof(descriptor)));
    save(argv[2],media+COMP_WBA_NOR_SEGMENT_CATALOG_A,2u*COMP_SEGMENT_BANK_BYTES);
    save(argv[3],media+COMP_WBA_NOR_RECORDING_BASE,e.reserved_bytes);
    printf("{\"result\":\"SYNTHETIC_PRODUCTION_MEDIA_IMAGE_BUILT_HOST_ONLY\",\"recordingId\":%u,\"payloadBytes\":%u,\"frames\":%u,\"reservedBytes\":%u,\"catalogBase\":%u,\"dataBase\":%u,\"nextId\":%u}\n",
        id,bytes,frames,e.reserved_bytes,c.banks[0],c.data_base,mounted.next_id);return 0;
}
