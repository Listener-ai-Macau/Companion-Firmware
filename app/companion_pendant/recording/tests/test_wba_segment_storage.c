/* Reuse the already-qualified command model, not its baseline test main.
 * These cases exercise only the NEW recorder adapter/arbitration paths. */
#include "wba_segment_storage.h"
#define main prior_nor_test_main
#include "../../../../tools/fixtures/wba_nor_suspend_test.c"
#undef main

#define DATA_BASE 65536u
#define OTHER_ERASE 98304u
static const uint8_t device_uid[12]={1u,2u,3u,4u,5u,6u,7u,8u,9u,10u,11u,12u};

static comp_segment_result_t catalog_finish(comp_wba_segment_storage_t *s,comp_segment_catalog_t *c)
{
    comp_segment_result_t r=COMP_SEG_PENDING;
    for(unsigned i=0u;i<5000u&&r==COMP_SEG_PENDING;i++){f.now+=2u;r=comp_wba_segment_storage_catalog_poll(s,c);}
    return r;
}
static void mounting_and_reservation(comp_wba_segment_storage_t *s,comp_segment_catalog_t *c,
    comp_segment_entry_t *e,comp_segment_audio_t *w,uint8_t page[256])
{
    comp_segment_port_t port=comp_wba_segment_storage_catalog_port(s);
    assert(comp_segment_catalog_mount_begin(c,&port,0u,24576u,DATA_BASE,65536u,device_uid,7u)==COMP_SEG_PENDING);
    assert(catalog_finish(s,c)==COMP_SEG_UNFORMATTED);
    assert(comp_segment_catalog_format_blank_begin(c)==COMP_SEG_PENDING&&catalog_finish(s,c)==COMP_SEG_OK);
    memset(e,0,sizeof(*e));e->state=COMP_SEG_WRITING;e->descriptor.codec=3u;e->descriptor.source_mode=1u;
    e->descriptor.format_epoch=7u;e->descriptor.session_id=9u;memcpy(e->descriptor.device_uid,device_uid,12u);
    comp_segment_reserve_t reserve={0};
    assert(comp_segment_reserve_begin(&reserve,c,e,4096u,0u)==COMP_SEG_PENDING);
    comp_segment_result_t r=COMP_SEG_PENDING;f.automatic_erase=true;
    for(unsigned i=0u;i<5000u&&r==COMP_SEG_PENDING;i++){f.now+=2u;r=comp_wba_segment_storage_reserve_poll(s,&reserve);}
    assert(r==COMP_SEG_OK);comp_segment_entry_t *owned=NULL;
    assert(comp_segment_reserve_take(&reserve,&owned)&&owned==e);
    comp_segment_audio_port_t audio=comp_wba_segment_storage_audio_port(s);
    assert(comp_segment_audio_prepare_begin(w,&audio,e,DATA_BASE,page)==COMP_SEG_PENDING);
    r=COMP_SEG_PENDING;
    for(unsigned i=0u;i<100u&&r==COMP_SEG_PENDING;i++){f.now+=2u;r=comp_segment_audio_poll(w);}
    assert(r==COMP_SEG_OK&&w->prepared);f.automatic_erase=false;
}
static void begin_other(companion_spi_nor_stm32wba_t *n)
{
    memset(f.bytes+OTHER_ERASE,0,4096u);
    assert(companion_spi_nor_stm32wba_erase_step(n,OTHER_ERASE,4096u)==PENDING);
}
int main(void)
{
    reset();companion_spi_nor_stm32wba_t n=make();comp_wba_segment_storage_t storage;
    assert(comp_wba_segment_storage_init(&storage,&n,0u,24576u,DATA_BASE,65536u));
    comp_segment_catalog_t catalog;comp_segment_entry_t entry;comp_segment_audio_t writer;
    uint8_t page[256],data[248],readback[256];
    for(unsigned i=0u;i<sizeof(data);i++)data[i]=(uint8_t)i;
    mounting_and_reservation(&storage,&catalog,&entry,&writer,page);
    begin_other(&n);unsigned erases=f.erases,writes=f.writes;
    assert(comp_segment_audio_append_begin(&writer,data,sizeof(data))==COMP_SEG_PENDING);
    unsigned phase=writer.phase;uint32_t generation=catalog.generation;
    assert(comp_segment_audio_poll(&writer)==COMP_SEG_PENDING&&writer.phase==phase&&f.writes==writes);
    assert(!storage.poisoned&&n.erase_active&&catalog.mounted&&catalog.generation==generation);
    comp_segment_result_t r=COMP_SEG_PENDING;
    for(unsigned i=0u;i<50u&&r==COMP_SEG_PENDING;i++){f.now+=2u;r=comp_segment_audio_poll(&writer);}
    assert(r==COMP_SEG_OK&&writer.committed_bytes==248u&&n.erase_active&&f.erases==erases);
    assert(companion_spi_nor_stm32wba_erase_is_suspended(&n)&&f.bytes[OTHER_ERASE]==0u);
    comp_segment_audio_port_t audio=comp_wba_segment_storage_audio_port(&storage);uint8_t length=0u;
    assert(comp_segment_audio_read_page(&audio,&entry,DATA_BASE,0u,readback,&length)==COMP_SEG_OK);
    assert(length==248u&&!memcmp(readback,data,sizeof(data)));
    /* The bool catalog callbacks now run only after a pure exact-I/O preview.
     * A pending suspend cannot become fail(c,IO_ERROR) or advance a scan. */
    assert(companion_spi_nor_stm32wba_erase_step(&n,OTHER_ERASE,4096u)==PENDING);
    f.now+=2u;assert(companion_spi_nor_stm32wba_erase_step(&n,OTHER_ERASE,4096u)==PENDING);
    comp_segment_entry_t sealed=entry;sealed.state=COMP_SEG_UNSYNCED;
    sealed.descriptor.encoded_length=sizeof(data);sealed.descriptor.sample_count=320u;
    sealed.descriptor.content_crc32=comp_rec_crc(data,sizeof(data));sealed.descriptor.sync_state=1u;
    sealed.descriptor.flags=COMP_REC_V2_SEALED|COMP_REC_V2_LAST;sealed.descriptor.total_segments=1u;
    companion_sha256_t sha;companion_sha256_init(&sha);companion_sha256_update(&sha,data,sizeof(data));
    companion_sha256_final(&sha,sealed.descriptor.sha256);
    assert(comp_segment_catalog_put_begin(&catalog,&sealed)==COMP_SEG_PENDING);
    comp_segment_catalog_t before=catalog;
    assert(comp_wba_segment_storage_catalog_poll(&storage,&catalog)==COMP_SEG_PENDING);
    assert(!memcmp(&before,&catalog,sizeof(catalog))&&catalog.mounted&&!storage.poisoned);
    assert(catalog_finish(&storage,&catalog)==COMP_SEG_OK&&catalog.visible_mask==1u);
    comp_segment_entry_t found;
    assert(comp_wba_segment_storage_entry(&storage,&catalog,0u,&found)==COMP_SEG_OK&&found.state==COMP_SEG_UNSYNCED);
    /* Natural completion stays latched for its original worker exactly once. */
    /* Erase can naturally complete after resume, before the next suspension
     * request. It cannot normally finish while physically suspended. */
    assert(companion_spi_nor_stm32wba_erase_step(&n,OTHER_ERASE,4096u)==PENDING);
    f.now+=2u;assert(companion_spi_nor_stm32wba_erase_step(&n,OTHER_ERASE,4096u)==PENDING);
    complete(); /* resumed physical erase completes; no recording claim */
    f.now+=2u;
    uint8_t scratch;
    assert(audio.read(audio.context,DATA_BASE,&scratch,1u)==COMP_SEG_PENDING);
    assert(audio.read(audio.context,DATA_BASE,&scratch,1u)==COMP_SEG_OK&&n.erase_active);
    assert(companion_spi_nor_stm32wba_erase_step(&n,OTHER_ERASE,4096u)==OK&&f.erases==erases);
    assert(!n.erase_active);
    /* Adapter capability never reaches the 16KiB gap, settings or resources. */
    unsigned reads=f.reads;
    assert(audio.read(audio.context,49152u,&scratch,1u)==COMP_SEG_BAD_ARGUMENT&&f.reads==reads);
    assert(audio.program(audio.context,DATA_BASE+255u,data,2u)==COMP_SEG_BAD_ARGUMENT);
    /* Transport failure remains explicit and retains both owners. */
    begin_other(&n);f.now+=2u;f.fail_command=0x75;
    sealed.state=COMP_SEG_ACKED;sealed.descriptor.sync_state=2u;
    assert(comp_segment_catalog_ack_begin(&catalog,&sealed)==COMP_SEG_PENDING);before=catalog;
    assert(comp_wba_segment_storage_catalog_poll(&storage,&catalog)==COMP_SEG_IO_ERROR);
    assert(storage.poisoned&&n.erase_active&&!memcmp(&before,&catalog,sizeof(catalog)));
    assert(comp_wba_segment_storage_catalog_poll(&storage,&catalog)==COMP_SEG_BAD_STATE);
    reset();n=make();n.erase_suspend_supported=false;
    assert(!comp_wba_segment_storage_init(&storage,&n,0u,24576u,DATA_BASE,65536u));
    puts("PASS actual NOR recorder adapter software path: prepare/provenance, audio+catalog suspend yield, unchanged pending cursors, exact owner completion, scope and failure guards; no board audio qualification");
    return 0;
}
