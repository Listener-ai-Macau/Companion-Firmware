#include "spi_nor_stm32wba.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef struct {uint32_t tick,advance_header,advance_payload,timeout[2];unsigned calls,selects;int fail_header,fail_payload,fail_release,selected;} Fake;
static bool select_chip(void *v,bool active){Fake*f=v;f->selects++;if(!active&&f->fail_release)return false;f->selected=active;return true;}
static bool xfer(void *v,const uint8_t *tx,uint8_t *rx,size_t n,uint32_t ms){Fake*f=v;assert(f->selected);assert(f->calls<2);f->timeout[f->calls++]=ms;if(tx){assert(n==4&&tx[0]==3);f->tick+=f->advance_header;return !f->fail_header;}assert(rx);f->tick+=f->advance_payload;memset(rx,0x5a,n);return !f->fail_payload;}
static uint32_t now(void *v){return ((Fake*)v)->tick;}
static void delay(void*v,uint32_t ms){((Fake*)v)->tick+=ms;}
static companion_spi_nor_stm32wba_t init(Fake*f){companion_spi_nor_stm32wba_t n={0};n.config.target=COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55;n.config.chip_select=select_chip;n.config.transfer=xfer;n.config.now_ms=now;n.config.delay_ms=delay;n.config.context=f;n.config.transfer_timeout_ms=200;n.info.jedec_id=0xef6018;n.info.size_bytes=16777216;n.probed=true;return n;}
#define RUN(n,f,len) companion_spi_nor_stm32wba_read_transient(&(n),0x1000,buf,(len),&released)
int main(void){uint8_t buf[512];bool released;Fake f={0};companion_spi_nor_stm32wba_t n=init(&f);
 f.advance_header=2;assert(RUN(n,f,256)==COMPANION_SPI_NOR_STM32WBA_OK&&!released);assert(f.calls==2&&f.timeout[0]==8&&f.timeout[1]==6&&!f.selected&&buf[0]==0x5a);
 memset(&f,0,sizeof(f));n=init(&f);f.advance_header=8;assert(RUN(n,f,256)==COMPANION_SPI_NOR_STM32WBA_ERROR&&released);assert(f.calls==1&&!f.selected);
 memset(&f,0,sizeof(f));n=init(&f);f.fail_header=1;assert(RUN(n,f,256)==COMPANION_SPI_NOR_STM32WBA_ERROR&&!released);assert(f.calls==1&&!f.selected);
 memset(&f,0,sizeof(f));n=init(&f);f.fail_payload=1;assert(RUN(n,f,256)==COMPANION_SPI_NOR_STM32WBA_ERROR&&released&&!f.selected);
 memset(&f,0,sizeof(f));n=init(&f);f.fail_payload=1;f.fail_release=1;assert(RUN(n,f,256)==COMPANION_SPI_NOR_STM32WBA_ERROR&&!released);
 memset(&f,0,sizeof(f));n=init(&f);f.tick=UINT32_MAX-1;f.advance_header=3;assert(RUN(n,f,256)==COMPANION_SPI_NOR_STM32WBA_OK&&!released);assert(f.timeout[1]==5);
 memset(&f,0,sizeof(f));n=init(&f);n.config.transfer_timeout_ms=3;f.advance_header=1;assert(RUN(n,f,256)==COMPANION_SPI_NOR_STM32WBA_OK);assert(f.timeout[0]==3&&f.timeout[1]==2);
 memset(&f,0,sizeof(f));n=init(&f);n.info.jedec_id=0x0b6018;assert(RUN(n,f,256)==COMPANION_SPI_NOR_STM32WBA_OK);assert(f.timeout[0]==200&&f.timeout[1]==200);
 memset(&f,0,sizeof(f));n=init(&f);assert(RUN(n,f,512)==COMPANION_SPI_NOR_STM32WBA_OK);assert(f.timeout[0]==200&&f.timeout[1]==200);
 memset(&f,0,sizeof(f));n=init(&f);n.erase_active=true;assert(RUN(n,f,256)==COMPANION_SPI_NOR_STM32WBA_PENDING);assert(!f.calls&&!f.selects);
 puts("PASS: qualified read shares budget; timeout/release, wrap, original small timeout, unknown part and long read covered");return 0;}
