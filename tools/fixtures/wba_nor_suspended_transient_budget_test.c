#include "spi_nor_stm32wba.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef struct {uint32_t tick,advance,select_advance,timeout[8];unsigned calls,selects;uint8_t sr1,sr2;int fail_call,fail_release,selected;} Fake;
static bool select_chip(void*v,bool active){Fake*f=v;f->selects++;if(active)f->tick+=f->select_advance;if(!active&&f->fail_release)return false;f->selected=active;return true;}
static bool xfer(void*v,const uint8_t*tx,uint8_t*rx,size_t n,uint32_t ms){Fake*f=v;assert(f->selected&&f->calls<8);f->timeout[f->calls++]=ms;f->tick+=f->advance;if((int)f->calls==f->fail_call)return false;if(tx&&rx){assert(n==2&&(tx[0]==5||tx[0]==0x35));rx[0]=0;rx[1]=tx[0]==5?f->sr1:f->sr2;}else if(tx){assert(n==4&&tx[0]==3);}else{assert(rx);memset(rx,0x5a,n);}return true;}
static uint32_t now(void*v){return ((Fake*)v)->tick;}static void delay(void*v,uint32_t ms){((Fake*)v)->tick+=ms;}
static companion_spi_nor_stm32wba_t init(Fake*f){companion_spi_nor_stm32wba_t n={0};n.config.target=COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55;n.config.chip_select=select_chip;n.config.transfer=xfer;n.config.now_ms=now;n.config.delay_ms=delay;n.config.context=f;n.config.transfer_timeout_ms=200;n.info.jedec_id=0xef6018;n.info.size_bytes=16777216;n.probed=true;n.erase_active=true;n.erase_phase=2;n.erase_address=0x4000;n.erase_bytes=4096;f->sr2=0x80;return n;}
#define RUN(n,at) companion_spi_nor_stm32wba_read_transient(&(n),(at),buf,256,&released)
#define RESET() memset(&f,0,sizeof(f));n=init(&f)
int main(void){uint8_t buf[256];bool released;Fake f={0};companion_spi_nor_stm32wba_t n=init(&f);
 f.advance=1;assert(RUN(n,0x1000)==COMPANION_SPI_NOR_STM32WBA_OK&&!released);assert(f.calls==4&&f.timeout[0]==8&&f.timeout[1]==7&&f.timeout[2]==6&&f.timeout[3]==5&&!f.selected&&buf[0]==0x5a&&n.erase_active);
 RESET();f.sr1=1;assert(RUN(n,0x1000)==COMPANION_SPI_NOR_STM32WBA_PENDING&&!released);assert(f.calls==2&&n.erase_active&&!f.selected);
 RESET();f.sr2=0;assert(RUN(n,0x1000)==COMPANION_SPI_NOR_STM32WBA_PENDING&&!released);assert(f.calls==2&&n.erase_active);
 RESET();assert(RUN(n,0x4000)==COMPANION_SPI_NOR_STM32WBA_PENDING&&!released&&!f.calls&&n.erase_active);
 RESET();n.erase_command_failed=true;assert(RUN(n,0x1000)==COMPANION_SPI_NOR_STM32WBA_PENDING&&!f.calls);
 RESET();n.erase_phase=0;assert(RUN(n,0x1000)==COMPANION_SPI_NOR_STM32WBA_PENDING&&!f.calls);
 RESET();n.erase_phase=4;assert(RUN(n,0x1000)==COMPANION_SPI_NOR_STM32WBA_OK&&!released&&f.calls==2&&n.erase_active);
 RESET();f.fail_call=1;assert(RUN(n,0x1000)==COMPANION_SPI_NOR_STM32WBA_ERROR&&!released&&f.calls==1&&!f.selected&&n.erase_active);
 RESET();f.fail_call=4;assert(RUN(n,0x1000)==COMPANION_SPI_NOR_STM32WBA_ERROR&&released&&f.calls==4&&!f.selected&&n.erase_active);
 RESET();f.advance=8;assert(RUN(n,0x1000)==COMPANION_SPI_NOR_STM32WBA_PENDING&&!released&&f.calls==1&&!f.selected&&n.erase_active);
 RESET();f.select_advance=8;f.fail_release=1;assert(RUN(n,0x1000)==COMPANION_SPI_NOR_STM32WBA_ERROR&&!released&&f.calls==0&&f.selected&&n.erase_active);
 RESET();n.info.jedec_id=0x0b6018;assert(RUN(n,0x1000)==COMPANION_SPI_NOR_STM32WBA_PENDING&&!released&&!f.calls&&n.erase_active);
 RESET();f.tick=UINT32_MAX-1;f.advance=1;assert(RUN(n,0x1000)==COMPANION_SPI_NOR_STM32WBA_OK&&f.timeout[3]==5&&n.erase_active);
 puts("PASS: suspended erase preserves owner, checks WIP/SUS, shares bounded status/header/data budget and isolates payload failure");return 0;}
