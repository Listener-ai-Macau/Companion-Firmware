#include "wba_recording_pipeline.h"
#include <stdio.h>
#define CHECK(x) do{if(!(x)){printf("FAIL line %u\n",(unsigned)__LINE__);return 1;}}while(0)
comp_segment_result_t comp_segment_reserve_begin_rotated(comp_segment_reserve_t *r,comp_segment_catalog_t *c,comp_segment_entry_t *e,uint32_t bytes)
{(void)r;(void)c;(void)e;(void)bytes;return COMP_SEG_PENDING;}
int main(void)
{
    comp_wba_recording_pipeline_t p={0};comp_segment_catalog_t c={0};comp_wba_segment_storage_t s={0};
    companion_spi_nor_stm32wba_t n={0};comp_cont_recording_t rec={0};uint32_t addr=77u;
    c.mounted=true;c.epoch=1u;c.generation=1u;c.data_bytes=8192u;s.nor=&n;
    p.config.catalog=&c;p.config.storage=&s;p.config.recording=&rec;p.state=COMP_PIPE_IDLE;
    CHECK(comp_wba_recording_pipeline_discard_acquire(&p));CHECK(comp_wba_recording_pipeline_storage_busy(&p));
    CHECK(!comp_wba_recording_pipeline_page_available(&p));CHECK(!comp_wba_recording_pipeline_discard_acquire(&p));
    CHECK(comp_wba_recording_pipeline_begin(&p,1u,0u,0u,1u)==COMP_SEG_BAD_STATE);
    CHECK(comp_wba_recording_pipeline_workspace_snapshot(&p,4096u,1u,0u,&addr)==COMP_SEG_BAD_STATE && addr==0u);
    uint8_t wire[84]={0};memcpy(wire,"CRA2",4u);comp_rec_put16(wire+4u,2u);comp_rec_put16(wire+6u,84u);
    comp_rec_put64(wire+20u,1u);comp_rec_put64(wire+28u,1u);comp_rec_put32(wire+40u,1u);
    comp_rec_put32(wire+44u,54u);wire[48]=1u;comp_rec_put32(wire+80u,comp_rec_crc(wire,80u));
    CHECK(comp_wba_recording_pipeline_consume_wire(&p,wire)==COMP_SEG_BAD_STATE);
    c.phase=1u;comp_wba_recording_pipeline_discard_release(&p);CHECK(p.discard_exclusive);
    c.phase=0u;s.poisoned=true;comp_wba_recording_pipeline_discard_release(&p);CHECK(p.discard_exclusive);
    s.poisoned=false;n.erase_active=true;comp_wba_recording_pipeline_discard_release(&p);CHECK(p.discard_exclusive);
    n.erase_active=false;comp_wba_recording_pipeline_discard_release(&p);CHECK(!p.discard_exclusive);
    rec.microphone_active=true;CHECK(!comp_wba_recording_pipeline_discard_acquire(&p));rec.microphone_active=false;
    p.workspace_bytes=4096u;CHECK(!comp_wba_recording_pipeline_discard_acquire(&p));
    puts("PASS_DISCARD_EXCLUSIVE actual_pipeline guards=recording,ota,consume,page,poison,erase");return 0;
}
