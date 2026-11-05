#include "loader.h"
#include "stm32wbaxx_hal.h"
#include "spi_nor_stm32wba.h"
#include "wba_flash_geometry.h"
#include "../spi_polling.h"
#include <string.h>

static SPI_HandleTypeDef spi;
static companion_spi_nor_stm32wba_t nor;
static uint32_t last_cycles, cycle_remainder, milliseconds;

/* The debugger calls exported functions without startup code or IRQs. Do not
 * depend on .bss initialization, SysTick interrupts, HSE, LSE, BLE or the app. */
HAL_StatusTypeDef HAL_InitTick(uint32_t priority) { (void)priority; return HAL_OK; }
uint32_t HAL_GetTick(void)
{
    uint32_t cycles = DWT->CYCCNT, elapsed = cycles - last_cycles;
    uint32_t divisor = SystemCoreClock / 1000u;
    last_cycles = cycles;
    if (!divisor) divisor = 16000u;
    milliseconds += elapsed / divisor;
    cycle_remainder += elapsed % divisor;
    milliseconds += cycle_remainder / divisor; cycle_remainder %= divisor;
    return milliseconds;
}
void HAL_Delay(uint32_t delay)
{
    uint32_t start = HAL_GetTick();
    while (HAL_GetTick() - start < delay) __NOP();
}
static bool select_chip(void *ctx, bool active)
{ (void)ctx; HAL_GPIO_WritePin(GPIOA, GPIO_PIN_8, active ? GPIO_PIN_RESET : GPIO_PIN_SET); return true; }
static bool transfer(void *ctx, const uint8_t *tx, uint8_t *rx, size_t size, uint32_t timeout)
{
    (void)ctx;
    return comp_v11_spi_polling_transfer(&spi, tx, rx, size, timeout);
}
static uint32_t now(void *ctx) { (void)ctx; return HAL_GetTick(); }
static void delay(void *ctx, uint32_t ms) { (void)ctx; HAL_Delay(ms); }
bool factory_hw_init(void)
{
    GPIO_InitTypeDef gpio = {0};
    companion_spi_nor_stm32wba_config_t config = {0};
    __disable_irq();
    if ((DBGMCU->IDCODE & 0xfffu) != 0x492u ||
        *(const uint16_t *)FLASHSIZE_BASE != COMP_WBA_INTERNAL_FLASH_KIB ||
        (FLASH->OPTR & FLASH_OPTR_TZEN) != 0u) return false;
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0u; DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
    last_cycles = cycle_remainder = milliseconds = 0u;
    SystemCoreClockUpdate();
    if (HAL_RCC_DeInit() != HAL_OK) return false;
    SystemCoreClockUpdate();
    memset(&spi, 0, sizeof(spi)); memset(&nor, 0, sizeof(nor));
    __HAL_RCC_GPIOA_CLK_ENABLE(); __HAL_RCC_GPIOB_CLK_ENABLE();
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_8, GPIO_PIN_SET);
    gpio.Pin = GPIO_PIN_8; gpio.Mode = GPIO_MODE_OUTPUT_PP;
    gpio.Pull = GPIO_NOPULL; gpio.Speed = GPIO_SPEED_FREQ_HIGH; HAL_GPIO_Init(GPIOA, &gpio);
    gpio.Pin = GPIO_PIN_0; gpio.Mode = GPIO_MODE_AF_PP; gpio.Alternate = GPIO_AF6_SPI3; HAL_GPIO_Init(GPIOA, &gpio);
    gpio.Pin = GPIO_PIN_8 | GPIO_PIN_9; HAL_GPIO_Init(GPIOB, &gpio);
    __HAL_RCC_SPI3_CONFIG(RCC_SPI3CLKSOURCE_HSI); __HAL_RCC_SPI3_CLK_ENABLE();
    __HAL_RCC_SPI3_FORCE_RESET(); __HAL_RCC_SPI3_RELEASE_RESET();
    spi.Instance = SPI3; spi.Init.Mode = SPI_MODE_MASTER; spi.Init.Direction = SPI_DIRECTION_2LINES;
    spi.Init.DataSize = SPI_DATASIZE_8BIT; spi.Init.CLKPolarity = SPI_POLARITY_LOW; spi.Init.CLKPhase = SPI_PHASE_1EDGE;
    spi.Init.NSS = SPI_NSS_SOFT; spi.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_8;
    spi.Init.FirstBit = SPI_FIRSTBIT_MSB; spi.Init.TIMode = SPI_TIMODE_DISABLE;
    spi.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE; spi.Init.NSSPMode = SPI_NSS_PULSE_DISABLE;
    spi.Init.NSSPolarity = SPI_NSS_POLARITY_LOW; spi.Init.FifoThreshold = SPI_FIFO_THRESHOLD_01DATA;
    spi.Init.MasterKeepIOState = SPI_MASTER_KEEP_IO_STATE_ENABLE;
    if (HAL_SPI_Init(&spi) != HAL_OK) return false;
    config.target = COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55;
    config.chip_select = select_chip; config.transfer = transfer; config.now_ms = now; config.delay_ms = delay;
    config.transfer_timeout_ms = 100u; config.page_program_timeout_ms = 100u; config.sector_erase_timeout_ms = 5000u;
    return companion_spi_nor_stm32wba_init(&nor, &config) &&
        companion_spi_nor_stm32wba_probe(&nor, NULL) == COMPANION_SPI_NOR_STM32WBA_OK &&
        nor.info.manufacturer_id == 0xefu && nor.info.size_bytes == COMP_FACTORY_NOR_BYTES;
}
bool factory_hw_read(uint32_t offset, uint8_t *data, uint32_t size)
{
    /* HAL uses a uint16_t length; CubeProgrammer's buffer can be larger. */
    while (size) {
        /* Keep an already-running product watchdog serviced during long
         * developer format/readback; never disable its safety configuration. */
        IWDG->KR=0xAAAAu;
        uint32_t count = size > 4096u ? 4096u : size;
        if (companion_spi_nor_stm32wba_read(&nor, offset, data, count) != COMPANION_SPI_NOR_STM32WBA_OK) return false;
        offset += count; data += count; size -= count;
    }
    return true;
}
bool factory_hw_write(uint32_t offset, const uint8_t *data, uint32_t size)
{
    if(!factory_mutation_allowed(offset,size))return false;
    while(size) {
        uint32_t n=size>4096u?4096u:size;IWDG->KR=0xAAAAu;
        if(companion_spi_nor_stm32wba_program(&nor,offset,data,n)!=COMPANION_SPI_NOR_STM32WBA_OK)return false;
        offset+=n;data+=n;size-=n;
    }
    return true;
}
bool factory_hw_erase(uint32_t offset)
{ if(!factory_mutation_allowed(offset,4096u))return false;
  IWDG->KR=0xAAAAu;return companion_spi_nor_stm32wba_erase_4k(&nor, offset) == COMPANION_SPI_NOR_STM32WBA_OK; }
