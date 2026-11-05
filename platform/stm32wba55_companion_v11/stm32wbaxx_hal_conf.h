#ifndef STM32WBAXX_HAL_CONF_H
#define STM32WBAXX_HAL_CONF_H
#define HAL_MODULE_ENABLED
#define HAL_CORTEX_MODULE_ENABLED
#define HAL_DMA_MODULE_ENABLED
#define HAL_GPIO_MODULE_ENABLED
#define HAL_RCC_MODULE_ENABLED
#define HAL_PWR_MODULE_ENABLED
#define HAL_FLASH_MODULE_ENABLED
#define HAL_I2C_MODULE_ENABLED
#define HAL_SPI_MODULE_ENABLED
#define HAL_SAI_MODULE_ENABLED
#define HAL_UART_MODULE_ENABLED
#define HAL_ICACHE_MODULE_ENABLED
#define HAL_RNG_MODULE_ENABLED
#define HAL_ADC_MODULE_ENABLED
#ifdef COMPANION_WBA_BLE_LINKED
#define HAL_RTC_MODULE_ENABLED
#define HAL_CRC_MODULE_ENABLED
#define HAL_PKA_MODULE_ENABLED
#endif
#define HSE_VALUE 32000000UL
#define HSI_VALUE 16000000UL
#define LSI_VALUE 32000UL
#define LSE_VALUE 32768UL
#define HSE_STARTUP_TIMEOUT 100UL
#define LSE_STARTUP_TIMEOUT 5000UL
#define EXTERNAL_SAI1_CLOCK_VALUE 0UL
#define VDD_VALUE 1800UL
#define TICK_INT_PRIORITY 0x0FUL
#define USE_RTOS 0U
#define PREFETCH_ENABLE 0U
#define USE_SPI_CRC 0U
#include "stm32wbaxx_hal_rcc.h"
#include "stm32wbaxx_hal_gpio.h"
#include "stm32wbaxx_hal_dma.h"
#include "stm32wbaxx_hal_cortex.h"
#include "stm32wbaxx_hal_flash.h"
#include "stm32wbaxx_hal_pwr.h"
#include "stm32wbaxx_hal_i2c.h"
#include "stm32wbaxx_hal_spi.h"
#include "stm32wbaxx_hal_sai.h"
#include "stm32wbaxx_hal_uart.h"
#include "stm32wbaxx_hal_icache.h"
#include "stm32wbaxx_hal_rng.h"
#include "stm32wbaxx_hal_adc.h"
#ifdef COMPANION_WBA_BLE_LINKED
#include "stm32wbaxx_hal_rtc.h"
#include "stm32wbaxx_hal_crc.h"
#include "stm32wbaxx_hal_pka.h"
#endif
#define assert_param(expr) ((void)0U)
#endif
