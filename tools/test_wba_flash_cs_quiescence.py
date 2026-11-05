"""Exercise the real board's NOR CS release against stalled SPI conditions."""
from pathlib import Path
import argparse, hashlib, json, subprocess
from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd
ROOT=Path(__file__).resolve().parents[1]
PRELUDE=r"""
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <assert.h>
#include "spi_nor_stm32wba.h"
#define GPIO_PIN_8 0x100u
#define GPIO_PIN_SET 1u
#define GPIO_PIN_RESET 0u
#define HAL_SPI_STATE_READY 1u
#define HAL_SPI_STATE_BUSY 2u
#define HAL_UNLOCKED 0u
#define HAL_LOCKED 1u
#define SPI_CR1_SPE 1u
#define SPI_CFG1_TXDMAEN 2u
#define SPI_CFG1_RXDMAEN 4u
typedef struct {uint32_t CR1,CFG1;} SPI_TypeDef;
typedef struct {SPI_TypeDef *Instance;uint32_t State,Lock;} SPI_HandleTypeDef;
typedef struct {uint32_t MODER,OTYPER,ODR;} GPIO_TypeDef;
static SPI_TypeDef flash_regs;
#define SPI3 (&flash_regs)
static SPI_HandleTypeDef spi_flash={&flash_regs,HAL_SPI_STATE_READY,HAL_UNLOCKED};
static GPIO_TypeDef pins={1u << 16,0,0};
#define GPIOA (&pins)
static bool fail_latch;
static void HAL_GPIO_WritePin(GPIO_TypeDef *p,uint32_t pin,uint32_t state)
{if(state==GPIO_PIN_SET){if(!fail_latch)p->ODR|=pin;}else p->ODR&=~pin;}
"""
TEST=r"""
static bool fail_payload, leave_spi_busy;
static bool xfer(void *p,const uint8_t *tx,uint8_t *rx,size_t n,uint32_t timeout)
{(void)p;(void)n;(void)timeout;if(tx)return true;assert(rx);if(fail_payload){if(leave_spi_busy)spi_flash.State=HAL_SPI_STATE_BUSY;return false;}return true;}
static uint32_t now(void *p){(void)p;return 0;}
static void delay(void *p,uint32_t ms){(void)p;(void)ms;}
static companion_spi_nor_stm32wba_t make_nor(void)
{
 companion_spi_nor_stm32wba_t n={0};n.config.target=COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55;
 n.config.chip_select=flash_cs;n.config.transfer=xfer;n.config.now_ms=now;n.config.delay_ms=delay;
 n.config.transfer_timeout_ms=200;n.info.jedec_id=0xef6018;n.info.size_bytes=16777216;n.probed=true;return n;
}
int main(void){
 pins.ODR=GPIO_PIN_8;spi_flash.State=HAL_SPI_STATE_BUSY;
 assert(!flash_cs(0,true));assert(pins.ODR&GPIO_PIN_8); /* never select a busy bus */
 spi_flash.State=HAL_SPI_STATE_READY;
 assert(flash_cs(0,true));assert(!(pins.ODR&GPIO_PIN_8));
 assert(flash_cs(0,false));assert(pins.ODR&GPIO_PIN_8);
 spi_flash.State=HAL_SPI_STATE_BUSY;assert(!flash_cs(0,false));spi_flash.State=HAL_SPI_STATE_READY;
 spi_flash.Lock=HAL_LOCKED;assert(!flash_cs(0,false));spi_flash.Lock=HAL_UNLOCKED;
 flash_regs.CR1=SPI_CR1_SPE;assert(!flash_cs(0,false));flash_regs.CR1=0;
 flash_regs.CFG1=SPI_CFG1_TXDMAEN;assert(!flash_cs(0,false));flash_regs.CFG1=SPI_CFG1_RXDMAEN;assert(!flash_cs(0,false));flash_regs.CFG1=0;
 pins.MODER=0;assert(!flash_cs(0,false));pins.MODER=1u<<16;
 pins.OTYPER=GPIO_PIN_8;assert(!flash_cs(0,false));pins.OTYPER=0;
 pins.ODR=0;fail_latch=true;assert(!flash_cs(0,false));fail_latch=false;
 assert(flash_cs(0,false));
 companion_spi_nor_stm32wba_t n=make_nor();uint8_t data[16];bool released=false;
 fail_payload=true;leave_spi_busy=false;
 assert(companion_spi_nor_stm32wba_read_transient(&n,0x1000,data,sizeof(data),&released)==COMPANION_SPI_NOR_STM32WBA_ERROR && released);
 leave_spi_busy=true;released=true;
 assert(companion_spi_nor_stm32wba_read_transient(&n,0x1000,data,sizeof(data),&released)==COMPANION_SPI_NOR_STM32WBA_ERROR && !released);
 assert(spi_flash.State==HAL_SPI_STATE_BUSY); /* no fake reset to manufacture safety */
 puts("PASS_CS_RELEASE_AND_REAL_NOR_RETRY_QUALIFICATION_SOFTWARE_MODEL");return 0;
}
"""
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
 p=ROOT/'platform/stm32wba55_companion_v11/board_hal.c';text=p.read_text();begin=text.index('static bool flash_cs(');end=text.index('\nstatic bool flash_transfer(',begin);body=text[begin:end]
 source=out/'actual_flash_cs.c';source.write_text(PRELUDE+body+TEST,encoding='utf8');exe=out/'test.exe';storage=ROOT/'app/companion_pendant/storage';cmd=['cl.exe','/nologo','/TC','/std:c11','/O2','/W4','/WX','/I'+str(storage),'/I'+str(ROOT/'app/companion_pendant/recording'),str(source),str(storage/'spi_nor_stm32wba.c'),'/Fe:'+str(exe)]
 script=out/'build.cmd';script.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n')
 run(['cmd.exe','/d','/c',str(script)],out,out/'test.log');result=run([str(exe)],out,out/'test.log')
 (out/'result.json').write_text(json.dumps({'result':result.strip(),'boardSourceSha256':hashlib.sha256(p.read_bytes()).hexdigest(),'hardware':False,'scope':'Production CS and NOR retry classification with simulated SPI registers and GPIO latch; not a physical bus test'},indent=2)+'\n');print(result,end='')
if __name__=='__main__':main()
