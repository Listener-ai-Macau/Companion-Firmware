#include "spi_nor_stm32wba.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
typedef struct {uint32_t tick,busy_until;unsigned calls,commands;bool selected,wel,pending,fail;} Fake;
static bool cs(void*v,bool active){Fake*f=v;f->selected=active;if(!active&&f->pending){f->pending=false;f->busy_until=f->tick+40u;}return true;}
static bool xfer(void*v,const uint8_t*tx,uint8_t*rx,size_t size,uint32_t timeout){
    Fake*f=v;assert(f->selected&&timeout);f->calls++;
    if(rx){assert(tx&&size==2u&&tx[0]==5u);rx[0]=0;rx[1]=(int32_t)(f->busy_until-f->tick)>0?1u:(f->wel?2u:0u);return true;}
    assert(tx);
    if(size==1u&&tx[0]==6u){f->wel=true;return true;}
    assert(size==4u&&tx[0]==0x20u&&f->wel);f->commands++;f->tick+=5u;
    if(f->fail)return false;
    f->wel=false;f->pending=true;return true;
}
static uint32_t now(void*v){return ((Fake*)v)->tick;}
static void delay(void*v,uint32_t ms){((Fake*)v)->tick+=ms;}
static companion_spi_nor_stm32wba_t make(Fake*f){
    companion_spi_nor_stm32wba_t n={0};n.config.target=COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55;n.config.chip_select=cs;n.config.transfer=xfer;n.config.now_ms=now;n.config.delay_ms=delay;n.config.context=f;n.config.transfer_timeout_ms=200;n.config.sector_erase_timeout_ms=400;n.info.jedec_id=0xef6018;n.info.size_bytes=16777216;n.probed=true;
#if COMPANION_WBA_RECLAIM_TIMING
    n.reclaim_timing.active=true;
#endif
    return n;
}
static void run(uint32_t start,bool slow){
    Fake f={0};f.tick=start;f.busy_until=start;companion_spi_nor_stm32wba_t n=make(&f);
    assert(companion_spi_nor_stm32wba_erase_step(&n,0x4000u,4096u)==COMPANION_SPI_NOR_STM32WBA_PENDING);
    assert(n.erase_started_ms==start+5u&&n.erase_active&&!f.selected&&f.commands==1u);
    if(slow){f.tick+=100u;assert(companion_spi_nor_stm32wba_erase_step(&n,0x4000u,4096u)==0);}
    else {for(unsigned i=0;i<8;i++){f.tick+=5u;assert(companion_spi_nor_stm32wba_erase_step(&n,0x4000u,4096u)==(i==7?0:1));}}
    assert(!n.erase_active&&!f.selected&&f.commands==1u);
#if COMPANION_WBA_RECLAIM_TIMING
    assert(n.reclaim_timing.issued==1u&&n.reclaim_timing.completed==1u&&n.reclaim_timing.bytes==4096u&&n.reclaim_timing.interrupted==0u);
    assert(n.reclaim_timing.erase_elapsed_ms==(slow?101u:41u));
    assert(n.reclaim_timing.busy_lower_ms==(slow?0u:34u));
    assert(n.reclaim_timing.max_poll_gap_ms==(slow?100u:5u));
#endif
    printf("case wrap=%u slow=%u calls=%u commands=%u elapsed=%lu\n",(unsigned)(start!=0),(unsigned)slow,f.calls,f.commands,(unsigned long)(f.tick-start));
}
int main(void){run(0,false);run(UINT32_MAX-20u,false);run(0,true);
    Fake f={0};f.fail=true;companion_spi_nor_stm32wba_t n=make(&f);
    assert(companion_spi_nor_stm32wba_erase_step(&n,0x4000,4096)==COMPANION_SPI_NOR_STM32WBA_ERROR);
    assert(n.erase_active&&n.erase_command_failed&&!f.selected);
#if COMPANION_WBA_RECLAIM_TIMING
    assert(n.reclaim_timing.issued==1u&&n.reclaim_timing.completed==0u&&n.reclaim_timing.interrupted==1u);
#endif
    puts("PASS same physical commands/results; CS-release origin, busy bracket, poll-gap separation, wrap and uncertain owner");return 0;}
