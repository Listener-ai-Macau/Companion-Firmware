#include "wba_segment_directory.h"
#define main prior_nor_test_main
#include "../../../../tools/fixtures/wba_nor_suspend_test.c"
#undef main
static const uint8_t device_uid[12]={1u,2u,3u,4u,5u,6u,7u,8u,9u,10u,11u,12u};
static comp_segment_catalog_t catalog;
static comp_wba_segment_storage_t storage;
static void complete_catalog(void)
{
    comp_segment_result_t r=COMP_SEG_PENDING;
    for(unsigned i=0u;i<5000u&&r==COMP_SEG_PENDING;i++){f.now+=2u;r=comp_wba_segment_storage_catalog_poll(&storage,&catalog);}
    assert(r==COMP_SEG_OK);
}
static void add(comp_segment_entry_t *entry,bool sealed)
{
    memset(entry,0,sizeof(*entry));entry->state=COMP_SEG_WRITING;
    entry->started_unix_s=20001u*86400u-1u;
    entry->descriptor.recording_id=catalog.next_id;entry->descriptor.format_epoch=7u;
    entry->descriptor.session_id=55u;entry->descriptor.segment_index=catalog.next_id-1u;
    entry->descriptor.sample_offset=(uint64_t)entry->descriptor.segment_index*320u;
    entry->descriptor.codec=3u;entry->descriptor.source_mode=1u;memcpy(entry->descriptor.device_uid,device_uid,12u);
    entry->reserved_bytes=4096u;entry->extent_offset=(entry->descriptor.recording_id-1u)*4096u;
    assert(comp_segment_catalog_put_begin(&catalog,entry)==COMP_SEG_PENDING);complete_catalog();
    if(sealed) {
        entry->state=COMP_SEG_UNSYNCED;entry->descriptor.flags=COMP_REC_V2_SEALED;
        entry->descriptor.sample_count=320u;entry->descriptor.encoded_length=54u;
        entry->descriptor.sha256[0]=1u;entry->descriptor.sync_state=1u;
        assert(comp_segment_catalog_put_begin(&catalog,entry)==COMP_SEG_PENDING);complete_catalog();
    }
}
static comp_segment_result_t page(comp_wba_segment_directory_t *p)
{
    comp_segment_result_t r=COMP_SEG_PENDING;
    for(unsigned i=0u;i<1000u&&r==COMP_SEG_PENDING;i++) {
        uint32_t before=f.reads;r=comp_wba_segment_directory_poll(p);
        assert(f.reads-before<=1u);if(r==COMP_SEG_PENDING)assert(!p->bytes);
    }
    return r;
}
int main(int argc,char **argv)
{
    reset();companion_spi_nor_stm32wba_t n=make();
    assert(comp_wba_segment_storage_init(&storage,&n,0u,24576u,65536u,65536u));
    comp_segment_port_t port=comp_wba_segment_storage_catalog_port(&storage);
    assert(comp_segment_catalog_mount_begin(&catalog,&port,0u,24576u,65536u,65536u,device_uid,7u)==COMP_SEG_PENDING);
    comp_segment_result_t r=COMP_SEG_PENDING;
    while(r==COMP_SEG_PENDING)r=comp_wba_segment_storage_catalog_poll(&storage,&catalog);
    assert(r==COMP_SEG_UNFORMATTED&&comp_segment_catalog_format_blank_begin(&catalog)==COMP_SEG_PENDING);complete_catalog();
    uint8_t out[256],request[16]={2u,COMP_SEG_DIRECTORY_COMMAND,0u,0u};comp_rec_put32(request+8u,9u);
    comp_wba_segment_directory_t p={0};comp_rec_v2_page_t decoded={0};
    assert(comp_wba_segment_directory_begin(&p,&storage,&catalog,request,out,sizeof(out))==COMP_SEG_PENDING);
    assert(page(&p)==COMP_SEG_OK&&p.bytes==24u&&comp_rec_v2_page_decode(out,p.bytes,&decoded)&&decoded.total==0u&&decoded.nonce==9u);
    comp_segment_entry_t entry;for(unsigned i=0u;i<3u;i++)add(&entry,true);add(&entry,false);
    assert(comp_wba_segment_directory_begin(&p,&storage,&catalog,request,out,sizeof(out))==COMP_SEG_PENDING);
    assert(page(&p)==COMP_SEG_OK&&p.bytes==248u&&comp_rec_v2_page_decode(out,p.bytes,&decoded));
    assert(decoded.total==3u&&decoded.count==2u&&decoded.start==0u&&decoded.entries[0].recording_id==1u&&decoded.entries[1].recording_id==2u);
    request[2]=1u;
    assert(comp_wba_segment_directory_begin(&p,&storage,&catalog,request,out,139u)==COMP_SEG_BAD_ARGUMENT);
    assert(comp_wba_segment_directory_begin(&p,&storage,&catalog,request,out,140u)==COMP_SEG_PENDING);
    assert(page(&p)==COMP_SEG_OK&&p.bytes==140u&&out[2]==116u&&out[3]==0u&&comp_rec_get32(out+136u)==20001u*86400u-1u);
    assert(comp_wba_segment_directory_begin(&p,&storage,&catalog,request,out,sizeof(out))==COMP_SEG_PENDING);
    assert(page(&p)==COMP_SEG_OK&&p.bytes==256u&&out[1]==2u&&comp_rec_get32(out+252u)==20001u*86400u-1u);
    assert(comp_rec_get32(out+20u)==~comp_rec_crc_step(comp_rec_crc_step(UINT32_MAX,out,20u),out+24u,p.bytes-24u));
    if(argc==2){FILE *file=fopen(argv[1],"wb");assert(file&&fwrite(out,1u,p.bytes,file)==p.bytes&&fclose(file)==0);}
    request[2]=0u;
    const uint16_t smaller[]={136u,182u,244u};
    for(unsigned i=0u;i<3u;i++) {
        assert(comp_wba_segment_directory_begin(&p,&storage,&catalog,request,out,smaller[i])==COMP_SEG_PENDING);
        assert(page(&p)==COMP_SEG_OK&&p.bytes==136u&&comp_rec_v2_page_decode(out,p.bytes,&decoded));
        assert(decoded.total==3u&&decoded.count==1u&&decoded.start==0u&&decoded.entries[0].recording_id==1u);
    }
    assert(comp_wba_segment_directory_begin(&p,&storage,&catalog,request,out,135u)==COMP_SEG_BAD_ARGUMENT);
    uint32_t snapshot=decoded.snapshot;comp_rec_put32(request+4u,snapshot);comp_rec_put32(request+12u,2u);
    assert(comp_wba_segment_directory_begin(&p,&storage,&catalog,request,out,sizeof(out))==COMP_SEG_PENDING);
    assert(page(&p)==COMP_SEG_OK&&comp_rec_v2_page_decode(out,p.bytes,&decoded));
    assert(decoded.total==3u&&decoded.count==1u&&decoded.start==2u&&decoded.entries[0].recording_id==3u);
    /* The open tail is never published or assigned a deletion-ready proof. */
    comp_rec_put32(request+12u,0u);
    assert(comp_wba_segment_directory_begin(&p,&storage,&catalog,request,out,sizeof(out))==COMP_SEG_PENDING);
    assert(comp_wba_segment_directory_poll(&p)==COMP_SEG_PENDING&&!p.bytes&&p.count==1u);
    entry.state=COMP_SEG_UNSYNCED;entry.descriptor.flags=COMP_REC_V2_SEALED|COMP_REC_V2_LAST;
    entry.descriptor.sample_count=320u;entry.descriptor.encoded_length=54u;entry.descriptor.sha256[0]=1u;
    entry.descriptor.sync_state=1u;entry.descriptor.total_segments=4u;
    assert(comp_segment_catalog_put_begin(&catalog,&entry)==COMP_SEG_PENDING);complete_catalog();
    assert(comp_wba_segment_directory_poll(&p)==COMP_SEG_STALE_SNAPSHOT&&!p.bytes);
    assert(comp_wba_segment_directory_begin(&p,&storage,&catalog,request,out,sizeof(out))==COMP_SEG_STALE_SNAPSHOT);
    comp_rec_put32(request+4u,0u);comp_rec_put32(request+12u,1u);
    assert(comp_wba_segment_directory_begin(&p,&storage,&catalog,request,out,sizeof(out))==COMP_SEG_BAD_ARGUMENT);
    /* Opt-in streams retain the existing attribute and one-read slice. */
    comp_rec_put32(request+12u,0u);comp_rec_put32(request+8u,91u);request[2]=3u;
    assert(comp_wba_segment_directory_begin(&p,&storage,&catalog,request,out,248u)==COMP_SEG_PENDING);
    FILE *stream_file=argc>2?fopen(argv[2],"wb"):NULL;if(argc>2)assert(stream_file);
    for(unsigned ordinal=0u;ordinal<4u;ordinal++) {
        assert(!comp_wba_segment_directory_next(&p));
        assert(page(&p)==COMP_SEG_OK&&p.bytes==140u&&out[1]==1u);
        assert(comp_rec_get32(out+8u)==ordinal&&comp_rec_get32(out+12u)==4u&&comp_rec_get32(out+16u)==91u);
        assert(comp_rec_get32(out+32u)==ordinal+1u);
        assert(comp_rec_get32(out+20u)==~comp_rec_crc_step(comp_rec_crc_step(UINT32_MAX,out,20u),out+24u,p.bytes-24u));
        if(stream_file)assert(fwrite(out,1u,p.bytes,stream_file)==p.bytes);
        assert(comp_wba_segment_directory_next(&p)==(ordinal<3u));
    }
    if(stream_file)assert(fclose(stream_file)==0);
    request[2]=2u;
    assert(comp_wba_segment_directory_begin(&p,&storage,&catalog,request,out,248u)==COMP_SEG_PENDING);
    assert(page(&p)==COMP_SEG_OK&&out[1]==2u&&p.bytes==248u&&comp_wba_segment_directory_next(&p));
    catalog.generation++;
    assert(comp_wba_segment_directory_poll(&p)==COMP_SEG_STALE_SNAPSHOT&&!p.bytes&&!comp_wba_segment_directory_next(&p));
    assert(comp_wba_segment_directory_begin(&p,&storage,&catalog,request,out,136u)==COMP_SEG_PENDING);
    assert(page(&p)==COMP_SEG_OK&&p.bytes==136u&&out[1]==1u);
    comp_wba_segment_directory_cancel(&p);assert(!comp_wba_segment_directory_next(&p));
    request[2]=4u;
    assert(comp_wba_segment_directory_begin(&p,&storage,&catalog,request,out,sizeof(out))==COMP_SEG_BAD_ARGUMENT);
    comp_rec_put32(request+12u,0u);comp_rec_put32(request+8u,0u);
    assert(comp_wba_segment_directory_begin(&p,&storage,&catalog,request,out,sizeof(out))==COMP_SEG_BAD_ARGUMENT);
    puts("PASS V2 cooperative GATT directory producer software: negotiated136/182/244/248B value budget,1/2 sealed pages;135B refused; strict nonce/snapshot, hidden growing tail, generation change cannot publish mixed page; capability not enabled");
    return 0;
}
