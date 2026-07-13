#ifndef STM32WBXX_HAL_CONF_H
#define STM32WBXX_HAL_CONF_H

#define HAL_MODULE_ENABLED
#define HAL_CORTEX_MODULE_ENABLED
#define HAL_DMA_MODULE_ENABLED
#define HAL_EXTI_MODULE_ENABLED
#define HAL_FLASH_MODULE_ENABLED
#define HAL_GPIO_MODULE_ENABLED
#define HAL_HSEM_MODULE_ENABLED
#define HAL_I2C_MODULE_ENABLED
#define HAL_IPCC_MODULE_ENABLED
#define HAL_PWR_MODULE_ENABLED
#define HAL_QSPI_MODULE_ENABLED
#define HAL_RCC_MODULE_ENABLED
#define HAL_RNG_MODULE_ENABLED
#define HAL_RTC_MODULE_ENABLED
#define HAL_SAI_MODULE_ENABLED
#define HAL_SPI_MODULE_ENABLED
#define HAL_UART_MODULE_ENABLED

#define HSE_VALUE               32000000U
#define HSE_STARTUP_TIMEOUT     100U
#define LSE_VALUE               32768U
#define LSE_STARTUP_TIMEOUT     5000U
#define HSI_VALUE               16000000U
#define HSI48_VALUE             48000000U
#define MSI_VALUE               4000000U
#define LSI_VALUE               32000U
#define EXTERNAL_SAI1_CLOCK_VALUE 2097000U
#define VDD_VALUE               3300U
#define TICK_INT_PRIORITY       0U
#define USE_RTOS                0U
#define PREFETCH_ENABLE         0U
#define INSTRUCTION_CACHE_ENABLE 1U
#define DATA_CACHE_ENABLE       1U

#ifdef HAL_RCC_MODULE_ENABLED
#include "stm32wbxx_hal_rcc.h"
#endif
#ifdef HAL_GPIO_MODULE_ENABLED
#include "stm32wbxx_hal_gpio.h"
#endif
#ifdef HAL_HSEM_MODULE_ENABLED
#include "stm32wbxx_hal_hsem.h"
#endif
#ifdef HAL_IPCC_MODULE_ENABLED
#include "stm32wbxx_hal_ipcc.h"
#endif
#ifdef HAL_DMA_MODULE_ENABLED
#include "stm32wbxx_hal_dma.h"
#endif
#ifdef HAL_I2C_MODULE_ENABLED
#include "stm32wbxx_hal_i2c.h"
#endif
#ifdef HAL_EXTI_MODULE_ENABLED
#include "stm32wbxx_hal_exti.h"
#endif
#ifdef HAL_CORTEX_MODULE_ENABLED
#include "stm32wbxx_hal_cortex.h"
#endif
#ifdef HAL_PWR_MODULE_ENABLED
#include "stm32wbxx_hal_pwr.h"
#endif
#ifdef HAL_FLASH_MODULE_ENABLED
#include "stm32wbxx_hal_flash.h"
#endif
#ifdef HAL_QSPI_MODULE_ENABLED
#include "stm32wbxx_hal_qspi.h"
#endif
#ifdef HAL_RNG_MODULE_ENABLED
#include "stm32wbxx_hal_rng.h"
#endif
#ifdef HAL_RTC_MODULE_ENABLED
#include "stm32wbxx_hal_rtc.h"
#endif
#ifdef HAL_SAI_MODULE_ENABLED
#include "stm32wbxx_hal_sai.h"
#endif
#ifdef HAL_SPI_MODULE_ENABLED
#include "stm32wbxx_hal_spi.h"
#endif
#ifdef HAL_UART_MODULE_ENABLED
#include "stm32wbxx_hal_uart.h"
#endif

#define assert_param(expr) ((void)0U)

#endif /* STM32WBXX_HAL_CONF_H */
