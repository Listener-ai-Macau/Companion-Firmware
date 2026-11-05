#include "update_boot_target.h"
#include "panel_boot_idle.h"
#include "wba_simple_install.h"
#include "wba_simple_layout.h"
#include "boot_receipt.h"

#include "stm32wbaxx_ll_iwdg.h"
#include "stm32wbaxx_ll_rcc.h"

#include <string.h>

#ifndef COMP_WBA_DEV_INSTALL_CUT_WINDOW_MS
#define COMP_WBA_DEV_INSTALL_CUT_WINDOW_MS 0u
#endif
#if COMP_WBA_DEV_INSTALL_CUT_WINDOW_MS > 60000u
#error "Development installation cut window must be bounded to 60 seconds"
#endif

static SPI_HandleTypeDef boot_spi;
static PKA_HandleTypeDef boot_pka;
static RNG_HandleTypeDef boot_rng;
static companion_spi_nor_stm32wba_t boot_nor;
static comp_wba_update_p256_hal_t boot_verifier;
static UART_HandleTypeDef boot_uart;
static bool boot_uart_ready;

static void boot_debug_init(void)
{
    GPIO_InitTypeDef gpio={0};
    __HAL_RCC_GPIOA_CLK_ENABLE();
    gpio.Pin=GPIO_PIN_1|GPIO_PIN_2;gpio.Mode=GPIO_MODE_AF_PP;
    gpio.Pull=GPIO_PULLUP;gpio.Speed=GPIO_SPEED_FREQ_HIGH;gpio.Alternate=GPIO_AF8_LPUART1;
    HAL_GPIO_Init(GPIOA,&gpio);
    __HAL_RCC_LPUART1_CONFIG(RCC_LPUART1CLKSOURCE_HSI);__HAL_RCC_LPUART1_CLK_ENABLE();
    boot_uart.Instance=LPUART1;boot_uart.Init.BaudRate=115200;
    boot_uart.Init.WordLength=UART_WORDLENGTH_8B;boot_uart.Init.StopBits=UART_STOPBITS_1;
    boot_uart.Init.Parity=UART_PARITY_NONE;boot_uart.Init.Mode=UART_MODE_TX_RX;
    boot_uart.Init.HwFlowCtl=UART_HWCONTROL_NONE;boot_uart.Init.ClockPrescaler=UART_PRESCALER_DIV1;
    boot_uart_ready=HAL_UART_Init(&boot_uart)==HAL_OK;
}
static void boot_log(const char *line)
{
    if(boot_uart_ready)(void)HAL_UART_Transmit(&boot_uart,(const uint8_t*)line,(uint16_t)strlen(line),20u);
}
static void boot_hex(uint32_t value)
{
    char text[11]="00000000\r\n";
    for(unsigned i=0u;i<8u;i++)text[i]="0123456789abcdef"[(value>>(28u-4u*i))&15u];
    boot_log(text);
}
void comp_wba_simple_verify_failure(uint32_t stage)
{boot_log("BOOT3 verify_failure=");boot_hex(stage);}
void comp_wba_update_p256_hal_trace(uint32_t stage,uint32_t status,uint32_t error)
{
    /* Successful UART output changes PKA spacing. Keep the qualified boot
     * path quiet; emit only a concrete HAL/point/signature failure. */
    if((stage==4u || stage==6u)?status!=0u:status==HAL_OK)return;
    boot_log("PKA stage=");boot_hex(stage);boot_log("PKA status=");boot_hex(status);
    if(error){boot_log("PKA error=");boot_hex(error);}
}
static bool chip_select(void *context,bool active)
{(void)context;HAL_GPIO_WritePin(GPIOA,GPIO_PIN_8,active?GPIO_PIN_RESET:GPIO_PIN_SET);return true;}
static bool transfer(void *context,const uint8_t *tx,uint8_t *rx,size_t length,uint32_t timeout)
{
    (void)context;
    if(!length||length>UINT16_MAX||(tx==NULL&&rx==NULL))return false;
    if(tx&&rx)return HAL_SPI_TransmitReceive(&boot_spi,(uint8_t*)tx,rx,(uint16_t)length,timeout)==HAL_OK;
    if(tx)return HAL_SPI_Transmit(&boot_spi,(uint8_t*)tx,(uint16_t)length,timeout)==HAL_OK;
    memset(rx,0xff,length);return HAL_SPI_TransmitReceive(&boot_spi,rx,rx,(uint16_t)length,timeout)==HAL_OK;
}
static uint32_t now_ms(void *context){(void)context;return HAL_GetTick();}
static void delay_ms(void *context,uint32_t ms){(void)context;HAL_Delay(ms);}

static bool pka_acquire(void *context)
{
    (void)context;
    /* RM0493 28.7.2: INITOK needs a clocked, initialized RNG. Boot runs
     * before the BLE entropy owner; the reset LSE selection and RNGEN=0
     * cannot be inherited as a usable entropy source. HSI16 is Boot's
     * running system clock. Use the pinned HAL conditioning/health checks,
     * including its bounded timeout, before enabling PKA. */
    __HAL_RCC_RNG_CONFIG(RCC_RNGCLKSOURCE_HSI);
    __HAL_RCC_RNG_CLK_ENABLE();
    boot_rng.Instance=RNG;
    boot_rng.Init.ClockErrorDetection=RNG_CED_ENABLE;
    if(HAL_RNG_Init(&boot_rng)!=HAL_OK){
        boot_log("BOOT0 failure=pka_rng_init\r\n");
        (void)HAL_RNG_DeInit(&boot_rng);
        __HAL_RCC_RNG_CLK_DISABLE();
        return false;
    }
    __HAL_RCC_PKA_CLK_ENABLE();
    boot_pka.Instance=PKA;boot_pka.State=HAL_PKA_STATE_RESET;
    return true;
}
static void pka_release(void *context)
{
    (void)context;
    __HAL_RCC_PKA_CLK_DISABLE();
    (void)HAL_RNG_DeInit(&boot_rng);
    __HAL_RCC_RNG_CLK_DISABLE();
}
static bool flash_read(void *context,uint32_t address,uint8_t *data,size_t length)
{(void)context;if(address<FLASH_BASE||address-FLASH_BASE>FLASH_SIZE||length>FLASH_SIZE-(address-FLASH_BASE))return false;memcpy(data,(const void*)address,length);return true;}
static bool flash_erase(void *context,uint32_t address)
{
    FLASH_EraseInitTypeDef erase={0};uint32_t error=0;HAL_StatusTypeDef result;(void)context;
    if(address<FLASH_BASE+COMP_WBA_BOOT_APP_OFFSET||address>=FLASH_BASE+COMP_WBA_BOOT_NVM_OFFSET||address%FLASH_PAGE_SIZE)return false;
    erase.TypeErase=FLASH_TYPEERASE_PAGES;erase.Page=((address-FLASH_BASE)%FLASH_BANK_SIZE)/FLASH_PAGE_SIZE;erase.NbPages=1u;
#if defined(FLASH_DBANK_SUPPORT)
    erase.Banks=(address-FLASH_BASE)>=FLASH_BANK_SIZE?FLASH_BANK_2:FLASH_BANK_1;
#endif
    if(HAL_FLASH_Unlock()!=HAL_OK)return false;
    result=HAL_FLASHEx_Erase(&erase,&error);
    (void)HAL_FLASH_Lock();
#if COMP_WBA_DEV_INSTALL_CUT_WINDOW_MS > 0u
    /* Explicit development build only. The installer calls flash_erase only
     * AFTER full candidate authentication. Pause after an actual first-page
     * erase, so the operator can cut physical power at a known invalid-App
     * point. No reset is injected and the signed candidate/pending are kept.
     * Re-entry may pause once again, then resumes the ordinary full install. */
    if(result==HAL_OK && address==FLASH_BASE+COMP_WBA_BOOT_APP_OFFSET) {
        boot_log("BOOT3 phase=first_app_page_erased physical_cut_window_ms=");
        boot_hex(COMP_WBA_DEV_INSTALL_CUT_WINDOW_MS);
        uint32_t started=HAL_GetTick();
        while(HAL_GetTick()-started<COMP_WBA_DEV_INSTALL_CUT_WINDOW_MS) {
            LL_IWDG_ReloadCounter(IWDG);HAL_Delay(10u);
        }
        boot_log("BOOT3 phase=physical_cut_window_ended\r\n");
    }
#endif
    return result==HAL_OK;
}
static bool flash_write(void *context,uint32_t address,const uint8_t *data,size_t length)
{
    uint32_t words[4];HAL_StatusTypeDef result=HAL_OK;(void)context;
    if(!data||!length||address<FLASH_BASE+COMP_WBA_BOOT_APP_OFFSET||address%16u||
       address-FLASH_BASE>COMP_WBA_BOOT_NVM_OFFSET||length>COMP_WBA_BOOT_NVM_OFFSET-(address-FLASH_BASE))return false;
    if(HAL_FLASH_Unlock()!=HAL_OK)return false;
    for(size_t offset=0u;offset<length;offset+=16u){size_t n=length-offset<16u?length-offset:16u;
        memset(words,0xff,sizeof(words));memcpy(words,data+offset,n);
        if(HAL_FLASH_Program(FLASH_TYPEPROGRAM_QUADWORD,address+(uint32_t)offset,(uint32_t)words)!=HAL_OK||
           memcmp((const void*)(address+(uint32_t)offset),words,sizeof(words))!=0){result=HAL_ERROR;break;}}
    (void)HAL_FLASH_Lock();return result==HAL_OK;
}

static bool boot_storage_hardware_init(void)
{
    GPIO_InitTypeDef gpio={0};companion_spi_nor_stm32wba_config_t nor={0};
    __HAL_RCC_GPIOA_CLK_ENABLE();__HAL_RCC_GPIOB_CLK_ENABLE();
    HAL_GPIO_WritePin(GPIOA,GPIO_PIN_8,GPIO_PIN_SET);
    gpio.Pin=GPIO_PIN_8;gpio.Mode=GPIO_MODE_OUTPUT_PP;gpio.Pull=GPIO_NOPULL;gpio.Speed=GPIO_SPEED_FREQ_HIGH;HAL_GPIO_Init(GPIOA,&gpio);
    gpio.Pin=GPIO_PIN_0;gpio.Mode=GPIO_MODE_AF_PP;gpio.Alternate=GPIO_AF6_SPI3;HAL_GPIO_Init(GPIOA,&gpio);
    gpio.Pin=GPIO_PIN_8|GPIO_PIN_9;gpio.Mode=GPIO_MODE_AF_PP;gpio.Alternate=GPIO_AF6_SPI3;HAL_GPIO_Init(GPIOB,&gpio);
    __HAL_RCC_SPI3_CONFIG(RCC_SPI3CLKSOURCE_HSI);__HAL_RCC_SPI3_CLK_ENABLE();
    boot_spi.Instance=SPI3;boot_spi.Init.Mode=SPI_MODE_MASTER;boot_spi.Init.Direction=SPI_DIRECTION_2LINES;
    boot_spi.Init.DataSize=SPI_DATASIZE_8BIT;boot_spi.Init.CLKPolarity=SPI_POLARITY_LOW;boot_spi.Init.CLKPhase=SPI_PHASE_1EDGE;
    boot_spi.Init.NSS=SPI_NSS_SOFT;boot_spi.Init.BaudRatePrescaler=SPI_BAUDRATEPRESCALER_8;boot_spi.Init.FirstBit=SPI_FIRSTBIT_MSB;
    boot_spi.Init.TIMode=SPI_TIMODE_DISABLE;boot_spi.Init.CRCCalculation=SPI_CRCCALCULATION_DISABLE;boot_spi.Init.NSSPMode=SPI_NSS_PULSE_DISABLE;
    boot_spi.Init.NSSPolarity=SPI_NSS_POLARITY_LOW;boot_spi.Init.FifoThreshold=SPI_FIFO_THRESHOLD_01DATA;boot_spi.Init.MasterKeepIOState=SPI_MASTER_KEEP_IO_STATE_ENABLE;
    if(HAL_SPI_Init(&boot_spi)!=HAL_OK)return false;
    nor.target=COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55;nor.chip_select=chip_select;nor.transfer=transfer;nor.now_ms=now_ms;nor.delay_ms=delay_ms;
    nor.transfer_timeout_ms=20u;nor.page_program_timeout_ms=20u;nor.sector_erase_timeout_ms=5000u;
    if(!companion_spi_nor_stm32wba_init(&boot_nor,&nor))return false;
    /* A cold supply must not turn one early JEDEC miss into an unobservable
     * permanent halt. Retry only this read, then let the running watchdog
     * recover. Update/layout/authentication checks are never bypassed. */
    for(unsigned attempt=0u;attempt<3u;++attempt){
        if(companion_spi_nor_stm32wba_probe(&boot_nor,NULL)==COMPANION_SPI_NOR_STM32WBA_OK&&
           boot_nor.info.size_bytes==COMP_WBA_NOR_TOTAL_BYTES)return true;
        HAL_Delay(10u);
    }
    return false;
}

static bool watchdog_start(void)
{
    RCC_OscInitTypeDef oscillator={0};uint32_t started;
    /* BDCR is write-protected after reset. HAL performs the bounded PWR/DBP
     * handshake before enabling LSI1; a bare LL LSI2 write was ignored on the
     * first CE board. LSI1 is sufficient for IWDG, independent of radio timing. */
    oscillator.OscillatorType=RCC_OSCILLATORTYPE_LSI;
    oscillator.LSIState=RCC_LSI1_ON;oscillator.LSIDiv=RCC_LSI_DIV1;
    if(HAL_RCC_OscConfig(&oscillator)!=HAL_OK)return false;
    /* Follow the HAL IWDG sequence: start its clock before waiting for PR/RLR
     * synchronization. Keep failure bounded and never bypass boot recovery. */
    LL_IWDG_Enable(IWDG);
    LL_IWDG_EnableWriteAccess(IWDG);LL_IWDG_SetPrescaler(IWDG,LL_IWDG_PRESCALER_256);LL_IWDG_SetReloadCounter(IWDG,4095u);
    started=HAL_GetTick();
    while(LL_IWDG_IsReady(IWDG)!=1u)if(HAL_GetTick()-started>100u)return false;
    LL_IWDG_ReloadCounter(IWDG);return true;
}
static void watchdog_feed(void){LL_IWDG_ReloadCounter(IWDG);}
static void keep_alive(void *c){(void)c;watchdog_feed();}
static bool nor_read(void*c,uint32_t at,uint8_t*p,size_t n)
{(void)c;return companion_spi_nor_stm32wba_read(&boot_nor,at,p,n)==COMPANION_SPI_NOR_STM32WBA_OK;}
static bool nor_program(void*c,uint32_t at,const uint8_t*p,size_t n)
{(void)c;return companion_spi_nor_stm32wba_program(&boot_nor,at,p,n)==COMPANION_SPI_NOR_STM32WBA_OK;}
static bool nor_erase(void*c,uint32_t at)
{(void)c;return companion_spi_nor_stm32wba_erase_4k(&boot_nor,at)==COMPANION_SPI_NOR_STM32WBA_OK;}
static bool jump_app(void)
{
    uint32_t *vectors=(uint32_t*)(FLASH_BASE+COMP_WBA_BOOT_APP_OFFSET);uint32_t sp=vectors[0],reset=vectors[1];
    if(!comp_wba_sram_stack_pointer_valid(sp)||(reset&1u)==0u||
       (reset&~1u)<FLASH_BASE+COMP_WBA_BOOT_APP_OFFSET||
       (reset&~1u)>=FLASH_BASE+COMP_WBA_BOOT_NVM_OFFSET)return false;
    boot_log("BOOT0 phase=jump_app\r\n");
    if(boot_uart_ready && HAL_UART_DeInit(&boot_uart)!=HAL_OK)return false;
    boot_uart_ready=false;
    if(HAL_SPI_DeInit(&boot_spi)!=HAL_OK||HAL_RCC_DeInit()!=HAL_OK)return false;
    __disable_irq();SysTick->CTRL=0u;SysTick->LOAD=0u;SysTick->VAL=0u;
    for(size_t i=0u;i<sizeof(NVIC->ICER)/sizeof(NVIC->ICER[0]);++i){NVIC->ICER[i]=UINT32_MAX;NVIC->ICPR[i]=UINT32_MAX;}
    SCB->VTOR=FLASH_BASE+COMP_WBA_BOOT_APP_OFFSET;__DSB();__ISB();
    __set_CONTROL(0u);__DSB();__ISB();
    /* MSP must be the final C-visible state change: branching in the same asm
     * prevents the compiler from touching the old frame after the stack swap. */
    __asm volatile("msr msp,%0\n cpsie i\n bx %1"::"r"(sp),"r"(reset):"memory");
    __builtin_unreachable();
}

bool comp_v11_update_boot_target_run(const comp_v11_update_boot_target_config_t *config)
{
    uint8_t scratch[512];
    if(!config||!config->public_key_xy||!config->key_id||
       *(const uint16_t *)FLASHSIZE_BASE!=COMP_WBA_INTERNAL_FLASH_KIB||HAL_Init()!=HAL_OK)return false;
    comp_v11_panel_boot_idle();
    boot_debug_init();boot_log("BOOT0 phase=early_init\r\n");
    /* Start before the first external bus transaction. The former ordering
     * could enter update_boot_main's fail-closed wait without any watchdog
     * or UART evidence when external Flash was not ready at power-on. */
    if(!watchdog_start()){boot_log("BOOT0 failure=watchdog_init\r\n");return false;}
    /* Invalidate any previous handoff before storage/authentication work.
     * These three registers are not RTC time or ST wireless timer state. */
    __HAL_RCC_PWR_CLK_ENABLE();__HAL_RCC_RTCAPB_CLK_ENABLE();
    HAL_PWR_EnableBkUpAccess();
    TAMP->BKP16R=0u;
    const volatile uint32_t *entry=(const volatile uint32_t *)COMP_WBA_APP_ADDRESS;
    const bool entry_erased=entry[0]==UINT32_MAX && entry[1]==UINT32_MAX;
    boot_log("BOOT0 phase=watchdog_ready\r\n");
    if(!boot_storage_hardware_init()){boot_log("BOOT0 failure=storage_hardware\r\n");return false;}
    boot_log("BOOT0 phase=storage_hardware_ready\r\n");
    boot_verifier=(comp_wba_update_p256_hal_t){&boot_pka,pka_acquire,pka_release,NULL,250u};
    comp_wba_update_p256_trust_t trust={config->key_id,config->public_key_xy,
        comp_wba_update_p256_hal_verify_digest,&boot_verifier};
    comp_wba_simple_install_config_t install={0};
    install.limits=(comp_wba_simple_limits_t){COMP_WBA_UPDATE_BOARD_COMPANION_V11,
        COMP_WBA_APP_ADDRESS,COMP_WBA_BOOT_APP_CAPACITY,COMP_WBA_NOR_UI_BYTES,
        COMP_WBA_NOR_TOTAL_BYTES,COMP_WBA_NOR_SYSTEM_BYTES};
    install.trust=trust;
    install.ports=(comp_wba_simple_install_ports_t){nor_read,nor_erase,nor_program,
        flash_read,flash_erase,flash_write,keep_alive,NULL};
    install.current[0]=COMP_SIMPLE_CURRENT_A;install.current[1]=COMP_SIMPLE_CURRENT_B;
    install.pending=COMP_SIMPLE_PENDING;install.flash_page_bytes=FLASH_PAGE_SIZE;
    install.minimum_app=config->installed_version;
    comp_wba_simple_boot_error_t error;
    comp_wba_simple_boot_result_t result=comp_wba_simple_boot_run(&install,scratch,sizeof(scratch),&error);
    if(result==COMP_SIMPLE_BOOT_CURRENT || result==COMP_SIMPLE_BOOT_INSTALLED) {
        boot_log(result==COMP_SIMPLE_BOOT_INSTALLED?"BOOT3 phase=installed_new_package\r\n":"BOOT3 phase=current_package\r\n");
        uint32_t route=result==COMP_SIMPLE_BOOT_CURRENT?COMP_V11_BOOT_ROUTE_CURRENT:
            entry_erased?COMP_V11_BOOT_ROUTE_REINSTALLED_ERASED_ENTRY:COMP_V11_BOOT_ROUTE_INSTALLED;
        comp_v11_boot_receipt_publish(&TAMP->BKP16R,route,entry[1]);
        __DSB();
        watchdog_feed();return jump_app();
    }
    boot_log("BOOT3 recovery_error=");boot_hex((uint32_t)error);
    return false;
}
