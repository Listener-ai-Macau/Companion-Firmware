#include "spi_nor_stm32wba.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef struct {uint32_t tick, advance, limit[8]; int selected,calls,commands,fail_release,fail_call; uint8_t sr1,sr2;} Fake;
static bool cs(void *v,bool active){Fake*f=v;if(!active&&f->fail_release)return false;f->selected=active;return true;}
static bool xfer(void*v,const uint8_t*tx,uint8_t*rx,size_t size,uint32_t timeout){Fake*f=v;assert(f->selected&&f->calls<8);f->limit[f->calls++]=timeout;f->tick+=f->advance<=timeout?f->advance:timeout;if(f->fail_call==f->calls||f->advance>timeout)return false;if(tx&&rx){assert(size==2);rx[0]=0;rx[1]=tx[0]==5?f->sr1:f->sr2;}else if(tx){assert(size==1&&(tx[0]==0x75||tx[0]==0x7a));f->commands++;}return true;}
static uint32_t now(void*v){return ((Fake*)v)->tick;}
static void wait(void*v,uint32_t ms){((Fake*)v)->tick+=ms;}
static companion_spi_nor_stm32wba_t init(Fake*f){companion_spi_nor_stm32wba_t n={0};n.config.target=COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55;n.config.chip_select=cs;n.config.transfer=xfer;n.config.now_ms=now;n.config.delay_ms=wait;n.config.context=f;n.config.transfer_timeout_ms=200;n.info.jedec_id=0xef6018;n.info.size_bytes=16777216;n.probed=true;n.erase_active=true;n.erase_suspend_supported=true;n.erase_phase=0;n.erase_address=0x4000;n.erase_bytes=4096;n.resume_guard_ms=1;n.suspend_wait_ms=1;f->tick=2;f->sr1=1;return n;}
#define RESET() memset(&f,0,sizeof(f));n=init(&f)
#define STEP() companion_spi_nor_stm32wba_erase_suspend_step_bounded(&n,8)
int main(void){Fake f={0};companion_spi_nor_stm32wba_t n=init(&f);f.advance=50;assert(STEP()==COMPANION_SPI_NOR_STM32WBA_ERROR&&f.limit[0]==8&&f.tick==10&&n.erase_active&&!f.selected&&n.erase_phase==0);
 RESET();f.advance=1;assert(STEP()==COMPANION_SPI_NOR_STM32WBA_PENDING&&f.calls==3&&f.limit[0]==8&&f.limit[1]==7&&f.limit[2]==6&&f.commands==1&&n.erase_phase==1&&n.erase_active&&!f.selected);
 assert(n.erase_phase_started_ms==f.tick); /* guard begins after the command leaves the bus */
 n.suspend_wait_ms=2;f.tick++;{int calls=f.calls;assert(STEP()==COMPANION_SPI_NOR_STM32WBA_PENDING&&f.calls==calls);}
 RESET();f.advance=4;assert(STEP()==COMPANION_SPI_NOR_STM32WBA_PENDING&&f.calls==2&&f.commands==0&&n.erase_phase==0&&n.erase_active&&!f.selected);
 RESET();f.advance=1;f.fail_call=2;assert(STEP()==COMPANION_SPI_NOR_STM32WBA_ERROR&&n.erase_phase==0&&n.erase_active&&!f.selected&&f.commands==0);
 RESET();f.tick=UINT32_MAX-2;f.advance=1;assert(STEP()==COMPANION_SPI_NOR_STM32WBA_PENDING&&f.limit[0]==8&&f.limit[1]==7&&f.limit[2]==6&&f.commands==1&&n.erase_phase==1);
 RESET();n.config.transfer_timeout_ms=3;f.advance=1;assert(STEP()==COMPANION_SPI_NOR_STM32WBA_PENDING&&f.limit[0]==3&&f.limit[1]==2&&f.limit[2]==1&&f.commands==1);
 RESET();f.advance=1;f.fail_call=3;assert(STEP()==COMPANION_SPI_NOR_STM32WBA_ERROR&&n.erase_phase==1&&n.erase_active&&!f.selected);
 RESET();f.fail_release=1;assert(STEP()==COMPANION_SPI_NOR_STM32WBA_ERROR&&n.erase_active&&n.erase_phase==0);
 RESET();n.erase_phase=1;n.erase_phase_started_ms=0;f.sr1=0;f.sr2=0x80;assert(STEP()==COMPANION_SPI_NOR_STM32WBA_OK&&n.erase_active&&n.erase_phase==2);
 RESET();n.erase_phase=3;n.erase_phase_started_ms=0;n.erase_pause_started_ms=0;f.sr1=1;f.sr2=0;assert(STEP()==COMPANION_SPI_NOR_STM32WBA_PENDING&&n.erase_active&&n.erase_phase==0&&f.commands==0);
 RESET();n.erase_phase=3;n.erase_phase_started_ms=0;f.sr2=0x80;assert(STEP()==COMPANION_SPI_NOR_STM32WBA_ERROR&&n.erase_active&&n.erase_phase==2);
 RESET();f.sr1=0;assert(STEP()==COMPANION_SPI_NOR_STM32WBA_OK&&n.erase_active&&n.erase_phase==4);
 RESET();n.erase_phase=4;n.erase_command_failed=true;assert(STEP()==COMPANION_SPI_NOR_STM32WBA_ERROR&&n.erase_active&&f.calls==0);
 RESET();f.advance=1;assert(companion_spi_nor_stm32wba_erase_suspend_step(&n)==COMPANION_SPI_NOR_STM32WBA_PENDING);assert(n.erase_phase_started_ms==f.tick);
 RESET();n.erase_phase=2;f.sr1=0;f.sr2=0x80;f.advance=1;assert(companion_spi_nor_stm32wba_erase_resume_step(&n)==COMPANION_SPI_NOR_STM32WBA_PENDING);assert(n.erase_phase_started_ms==f.tick&&n.erase_run_since_ms==f.tick);
 puts("PASS bounded erase gate: shared tick budget, no unissued suspend, uncertain command stays owned, resume and suspend phases, released/uncertain CS");return 0;}

