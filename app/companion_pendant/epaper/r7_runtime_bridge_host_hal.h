#ifndef COMPANION_R7_RUNTIME_BRIDGE_HOST_HAL_H
#define COMPANION_R7_RUNTIME_BRIDGE_HOST_HAL_H

#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>

typedef struct { unsigned unused; } SPI_HandleTypeDef;
typedef struct { unsigned unused; } GPIO_TypeDef;
typedef struct {
    uint32_t Pin;
    uint32_t Mode;
    uint32_t Pull;
    uint32_t Speed;
} GPIO_InitTypeDef;

extern GPIO_TypeDef *GPIOA;
extern GPIO_TypeDef *GPIOB;
extern GPIO_TypeDef *GPIOC;
extern SPI_HandleTypeDef hspi2;

#define GPIO_PIN_RESET 0u
#define GPIO_PIN_SET 1u
#define GPIO_PIN_1 0x0001u
#define GPIO_PIN_0 0x0000u
#define GPIO_PIN_5 0x0020u
#define GPIO_PIN_6 0x0040u
#define GPIO_PIN_9 0x0200u
#define GPIO_MODE_OUTPUT_PP 1u
#define GPIO_MODE_INPUT 2u
#define GPIO_NOPULL 0u
#define GPIO_SPEED_FREQ_HIGH 3u
#define GPIO_SPEED_FREQ_LOW 1u

#define __HAL_RCC_GPIOA_CLK_ENABLE() ((void)0)
#define __HAL_RCC_GPIOB_CLK_ENABLE() ((void)0)
#define __HAL_RCC_GPIOC_CLK_ENABLE() ((void)0)
#define __NOP() ((void)0)

uint32_t HAL_GetTick(void);
void HAL_Delay(uint32_t milliseconds);
void HAL_GPIO_WritePin(GPIO_TypeDef *port, uint32_t pin, uint32_t state);
uint32_t HAL_GPIO_ReadPin(GPIO_TypeDef *port, uint32_t pin);
void HAL_GPIO_Init(GPIO_TypeDef *port, GPIO_InitTypeDef *config);
int HAL_SPI_DeInit(SPI_HandleTypeDef *handle);

void comp_epaper_panel_adapter_init_dry_run(comp_epaper_panel_adapter_t *adapter);
void companion_r7_host_set_dc(bool data_mode);
bool companion_r7_host_spi_tx(const uint8_t *data, uint16_t length);
bool companion_r7_runtime_host_validate_movement_trace(
    const uint8_t *commands,
    const uint16_t *data_lengths,
    const uint8_t *data_first_bytes,
    size_t command_count,
    uint32_t transaction_ms,
    uint32_t busy_ms,
    bool busy_asserted,
    bool busy_released);

#endif
